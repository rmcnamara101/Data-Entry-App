from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QMessageBox, QDialog, QScrollArea, QSplitter,
    QGridLayout
)
from PyQt5.QtGui import QFont, QImage, QPixmap
from PyQt5.QtCore import Qt

from datetime import datetime
import cv2

# Import DatabaseManager and FIELD_REGIONS from your backend
from backend.database import DatabaseManager, PatientRecord
from backend.utils import FIELD_REGIONS


class ValidationPage(QWidget):
    """
    Page for reviewing and correcting validation errors in database entries.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()  # Or pass a DB URL
        self.db_table = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Table to list entries with validation errors
        self.db_table = QTableWidget()
        self.db_table.setColumnCount(4)  # Add a column for the Edit button
        self.db_table.setHorizontalHeaderLabels([
            "ID", "Request Number", "Surname", "Action"
        ])
        self.db_table.verticalHeader().setVisible(False)
        self.db_table.setAlternatingRowColors(True)

        # Button row
        button_layout = QHBoxLayout()

        refresh_button = QPushButton("Refresh")
        refresh_button.setFont(QFont("Arial", 11))
        refresh_button.clicked.connect(self.load_entries)

        workflow_button = QPushButton("Start Workflow")
        workflow_button.setFont(QFont("Arial", 11))
        workflow_button.clicked.connect(self.start_workflow_mode)
        button_layout.addWidget(workflow_button)


        button_layout.addWidget(refresh_button)

        layout.addLayout(button_layout)
        layout.addWidget(self.db_table)
        self.setLayout(layout)

        # Load validation errors initially
        self.load_entries()

    def load_entries(self):
        """
        Load entries with validation errors into the table.
        """
        session = self.db_manager.Session()
        try:
            flagged_entries = self.db_manager.get_flagged_entries()

            # Filter out entries with no validation errors
            flagged_entries = [record for record in flagged_entries if record.get('validation_errors')]

            self.db_table.setRowCount(len(flagged_entries))
            for row_idx, record in enumerate(flagged_entries):
                self.db_table.setItem(row_idx, 0, QTableWidgetItem(str(record['id'])))
                self.db_table.setItem(row_idx, 1, QTableWidgetItem(record['request_number'] or ""))
                self.db_table.setItem(row_idx, 2, QTableWidgetItem(record['surname'] or ""))

                # Add Edit button in the last column
                edit_button = QPushButton("Edit")
                edit_button.setFont(QFont("Arial", 10))
                edit_button.clicked.connect(lambda _, r=row_idx: self.edit_entry(r))
                self.db_table.setCellWidget(row_idx, 3, edit_button)
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Error fetching flagged entries: {e}")
        finally:
            session.close()

    def edit_entry(self, row):
        """
        Open a dialog to edit the selected entry.
        """
        entry_id = self.db_table.item(row, 0).text()
        session = self.db_manager.Session()
        try:
            record = session.query(PatientRecord).filter(PatientRecord.id == entry_id).one()
            dialog = EditEntryDialog(record, self)
            if dialog.exec_():
                # Reload entries after saving changes
                self.load_entries()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load entry for editing: {e}")
        finally:
            session.close()

    def start_workflow_mode(self):
        session = self.db_manager.Session()
        try:
            flagged_entries = session.query(PatientRecord).filter(
                PatientRecord.needs_manual_review == True
            ).all()  # Fetch all flagged entries as objects

            if not flagged_entries:
                QMessageBox.information(self, "No Entries", "No validation errors to review.")
                return

            workflow_dialog = WorkflowDialog(flagged_entries, self.db_manager, self)
            workflow_dialog.exec_()

            # Reload entries after completing the workflow
            self.load_entries()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start workflow mode: {e}")
        finally:
            session.close()





class EditEntryDialog(QDialog):
    """
    Dialog for reviewing and correcting flagged fields in a database entry.
    """
    def __init__(self, record, parent=None):
        super().__init__(parent)
        self.record = record
        self.db_manager = parent.db_manager
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"Edit Flagged Fields - ID: {self.record.id}")

        # Create a scrollable widget
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)

        # Editable fields for flagged entries
        self.fields = {}
        self.field_images = {}

        flagged_fields = self.record.error_details  # Assume error_details is a dict of flagged fields
        for field, error_detail in flagged_fields.items():
            field_label = QLabel(field.replace('_', ' ').capitalize())
            field_label.setFont(QFont("Arial", 10))

            field_input = QLineEdit(getattr(self.record, field, "") or "")
            self.fields[field] = field_input

            content_layout.addWidget(field_label)
            content_layout.addWidget(field_input)

            if field in FIELD_REGIONS:
                field_image = self._get_field_image(field)
                if field_image is not None:
                    image_label = QLabel()
                    image_label.setPixmap(field_image)
                    image_label.setScaledContents(True)
                    content_layout.addWidget(image_label)
                    self.field_images[field] = image_label

        # Buttons
        button_layout = QHBoxLayout()

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_changes)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)

        content_layout.addLayout(button_layout)

        scroll_area.setWidget(content_widget)

        # Add scrollable area to the dialog
        layout = QVBoxLayout(self)
        layout.addWidget(scroll_area)
        self.setLayout(layout)

    def _get_field_image(self, field_name):
        """
        Extracts the field area image using the bounding box.

        Args:
            field_name (str): The name of the field.

        Returns:
            QPixmap: The cropped field area as a QPixmap for display, or None if extraction fails.
        """
        try:
            field_region = FIELD_REGIONS.get(field_name)
            if not field_region:
                raise ValueError(f"No region defined for field: {field_name}")

            bbox = field_region.coordinates
            if not bbox:
                raise ValueError(f"No bounding box available for field: {field_name}")

            file_path = self.record.image_path  # Extract the file path from the record
            if not file_path:
                raise ValueError("File path is missing in the record.")

            form_image = cv2.imread(file_path)
            if form_image is None:
                raise ValueError(f"Failed to load image from file path: {file_path}")

            x1, y1, x2, y2 = bbox
            cropped_image = form_image[y1:y2, x1:x2]
            if cropped_image.size == 0:
                raise ValueError(f"Cropped image is empty for bounding box {bbox}")

            cropped_image_rgb = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2RGB)
            height, width, channel = cropped_image_rgb.shape
            bytes_per_line = 3 * width

            q_image = QImage(cropped_image_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888)
            return QPixmap.fromImage(q_image)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to extract field image for {field_name}: {e}")
            return None





    def save_changes(self):
        """
        Save changes to flagged fields in the database.
        """
        session = self.db_manager.Session()
        try:
            updated_errors = {}

            for field, input_widget in self.fields.items():
                new_value = input_widget.text()

                # Convert date strings back to datetime if necessary
                if field in ["date_of_birth", "request_date"] and new_value:
                    try:
                        new_value = datetime.strptime(new_value, '%Y-%m-%d')  # Adjust format as needed
                    except ValueError:
                        QMessageBox.critical(self, "Error", f"Invalid date format for {field}. Use YYYY-MM-DD.")
                        return

                setattr(self.record, field, new_value if new_value else None)

                # Remove resolved fields from error_details
                if self.record.error_details.get(field):
                    if not new_value:  # Keep validation error if the field is still invalid
                        updated_errors[field] = self.record.error_details[field]

            # Update error_details in the record
            self.record.error_details = updated_errors if updated_errors else None
            self.record.needs_manual_review = bool(updated_errors)

            session.merge(self.record)
            session.commit()
            QMessageBox.information(self, "Success", "Changes saved successfully.")
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save changes: {e}")
        finally:
            session.close()

from PyQt5.QtCore import Qt

class WorkflowDialog(QDialog):
    """
    Dialog for reviewing and correcting flagged entries in a workflow mode,
    with an image displayed to the left of the entry fields.
    """
    def __init__(self, flagged_entries, db_manager, parent=None):
        super().__init__(parent)
        self.flagged_entries = flagged_entries  # List of flagged entries
        self.db_manager = db_manager
        self.current_index = 0  # Start with the first entry
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Validation Workflow")
        self.setMinimumSize(1200, 800)

        # Main layout
        layout = QVBoxLayout(self)

        # Progress display
        self.progress_label = QLabel(f"Entry {self.current_index + 1} of {len(self.flagged_entries)}")
        self.progress_label.setFont(QFont("Arial", 12))
        layout.addWidget(self.progress_label)

        # Splitter for content area
        splitter = QSplitter(self)
        splitter.setOrientation(Qt.Horizontal)

        # Image area
        self.image_label = QLabel()
        self.image_label.setFixedSize(600, 800)
        self.image_label.setScaledContents(True)

        image_container = QWidget()
        image_layout = QVBoxLayout(image_container)
        image_layout.addWidget(self.image_label)
        image_layout.addStretch()
        splitter.addWidget(image_container)

        # Form area
        self.fields = {}
        self.form_layout = QGridLayout()

        self.fields_widget = QWidget()
        self.fields_widget.setLayout(self.form_layout)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.fields_widget)
        splitter.addWidget(self.scroll_area)

        splitter.setSizes([600, 800])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        layout.addWidget(splitter)

        # Navigation button
        nav_layout = QHBoxLayout()

        self.save_and_next_button = QPushButton("Save and Next")
        self.save_and_next_button.clicked.connect(self.save_and_next_entry)

        nav_layout.addWidget(self.save_and_next_button)

        layout.addLayout(nav_layout)
        self.setLayout(layout)
        self.load_entry()

    def load_entry(self):
        """
        Load the current entry into the form and display the associated image.
        """
        # Clear existing fields
        for i in reversed(range(self.form_layout.count())):
            widget = self.form_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        entry = self.flagged_entries[self.current_index]

        # Update progress
        self.progress_label.setText(f"Entry {self.current_index + 1} of {len(self.flagged_entries)}")

        # Display image
        image_path = entry.image_path
        if image_path:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                self.image_label.setPixmap(pixmap)
            else:
                self.image_label.setText("Image not found")
        else:
            self.image_label.setText("No image available")

        self.fields = {}
        row = 0
        for field, error_detail in (entry.error_details or {}).items():
            field_label = QLabel(field.replace('_', ' ').capitalize())
            field_label.setFont(QFont("Arial", 10))

            # Convert datetime to string if necessary
            value = getattr(entry, field, "")
            if isinstance(value, datetime):
                value = value.strftime('%d/%m/%Y')  # Adjust format as needed

            field_input = QLineEdit(value or "")
            self.fields[field] = field_input

            self.form_layout.addWidget(field_label, row, 0)
            self.form_layout.addWidget(field_input, row, 1)

            if field == "request_date":
                today_button = QPushButton("Today")
                today_button.setFixedWidth(80)
                today_button.setFocusPolicy(Qt.TabFocus)
                today_button.clicked.connect(lambda _, f=field_input: self.set_today_date(f))
                self.form_layout.addWidget(today_button, row, 2)

            row += 1

        # Set focus to the first input field
        if self.fields:
            next(iter(self.fields.values())).setFocus()


    def set_today_date(self, field_input):
        """
        Set today's date in the specified field.
        """
        today = datetime.now().strftime('%d/%m/%Y')  # Adjust format as needed
        field_input.setText(today)

    def save_and_next_entry(self):
        """
        Save changes to the current entry and move to the next entry.
        """
        session = self.db_manager.Session()
        try:
            entry = self.flagged_entries[self.current_index]
            record = session.query(PatientRecord).filter(PatientRecord.id == entry.id).one()

            updated_errors = {}

            for field, input_widget in self.fields.items():
                new_value = input_widget.text()

                if field in ["date_of_birth", "request_date"] and new_value:
                    try:
                        new_value = datetime.strptime(new_value, '%d/%m/%Y')
                    except ValueError:
                        QMessageBox.critical(self, "Error", f"Invalid date format for {field}. Use DD/MM/YYYY.")
                        return

                setattr(record, field, new_value if new_value else None)

                if field in record.error_details:
                    if not new_value:
                        updated_errors[field] = record.error_details[field]
                    else:
                        record.error_details.pop(field, None)

            record.error_details = updated_errors if updated_errors else None
            record.needs_manual_review = bool(updated_errors)

            session.merge(record)
            session.commit()

            self.flagged_entries[self.current_index] = record

            if self.current_index < len(self.flagged_entries) - 1:
                self.current_index += 1
                self.load_entry()
            else:
                QMessageBox.information(self, "Done", "No more entries to review.")
                self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save changes: {e}")
        finally:
            session.close()

    def keyPressEvent(self, event):
        """
        Handle key presses for navigation and interaction.
        """
        focused_widget = self.focusWidget()
        if isinstance(focused_widget, QPushButton) and focused_widget.text() == "Today":
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                focused_widget.click()  # Trigger the button's action
                return
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.save_and_next_entry()
        elif event.key() == Qt.Key_Tab:
            self.focusNextChild()
        else:
            super().keyPressEvent(event)
