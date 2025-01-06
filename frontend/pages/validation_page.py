from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QTableWidget, QTableWidgetItem, QMessageBox, QDialog
)
from PyQt5.QtGui import QFont, QImage, QPixmap

from PyQt5.QtCore import Qt

# Import DatabaseManager from your backend
from backend.database import DatabaseManager, PatientRecord
from datetime import datetime
import cv2
from backend.utils import FIELD_REGIONS


class ValidationPage(QWidget):
    """
    Page for reviewing and correcting validation errors in database entries.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = DatabaseManager()  # or pass a DB URL
        self.db_table = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Table to list entries with validation errors
        self.db_table = QTableWidget()
        self.db_table.setColumnCount(4)
        self.db_table.setHorizontalHeaderLabels([
            "ID", "Request Number", "Surname", "Validation Errors"
        ])
        self.db_table.verticalHeader().setVisible(False)
        self.db_table.setAlternatingRowColors(True)
        self.db_table.cellDoubleClicked.connect(self.edit_entry)  # Double-click to edit entry

        # Button row
        button_layout = QHBoxLayout()

        refresh_button = QPushButton("Refresh")
        refresh_button.setFont(QFont("Arial", 11))
        refresh_button.clicked.connect(self.load_entries)

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

            self.db_table.setRowCount(len(flagged_entries))
            for row_idx, record in enumerate(flagged_entries):
                self.db_table.setItem(row_idx, 0, QTableWidgetItem(str(record['id'])))
                self.db_table.setItem(row_idx, 1, QTableWidgetItem(record['request_number'] or ""))
                self.db_table.setItem(row_idx, 2, QTableWidgetItem(record['surname'] or ""))
                self.db_table.setItem(row_idx, 3, QTableWidgetItem(str(record['validation_errors'] or "")))
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Error fetching flagged entries: {e}")
        finally:
            session.close()

    def edit_entry(self, row, column):
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
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)

        # Editable fields for flagged entries
        self.fields = {}
        self.field_images = {}

        flagged_fields = self.record.error_details  # Assume error_details is a dict of flagged fields
        for field, error_detail in flagged_fields.items():
            field_label = QLabel(field.replace('_', ' ').capitalize())
            field_label.setFont(QFont("Arial", 10))

            field_input = QLineEdit(getattr(self.record, field) or "")
            self.fields[field] = field_input

            layout.addWidget(field_label)
            layout.addWidget(field_input)

            # Add field area image if bounding box is available
            bbox = FIELD_REGIONS[field].coordinates
            if bbox:
                field_image_label = QLabel(f"{field} Image:")
                field_image_label.setFont(QFont("Arial", 9))
                layout.addWidget(field_image_label)

                field_image = self._get_field_image(bbox)
                if field_image is not None:
                    pixmap = QPixmap.fromImage(field_image)
                    image_label = QLabel()
                    image_label.setPixmap(pixmap)
                    image_label.setScaledContents(True)
                    layout.addWidget(image_label)
                    self.field_images[field] = image_label

        # Buttons
        button_layout = QHBoxLayout()

        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_changes)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def _get_field_image(self, bbox):
        """
        Extracts the field area image using the bounding box.

        Args:
            bbox (tuple): Bounding box coordinates (x1, y1, x2, y2).

        Returns:
            QImage: The cropped field area as a QImage for display.
        """
        try:
            x1, y1, x2, y2 = bbox
            print(self.record.image_path)
            form_image = cv2.imread(self.record)  # Read form image from file path
            cropped_image = form_image[y1:y2, x1:x2]

            # Convert to QImage for PyQt display
            cropped_image_rgb = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2RGB)
            height, width, channel = cropped_image_rgb.shape
            bytes_per_line = 3 * width
            q_image = QPixmap.fromImage(QImage(cropped_image_rgb.data, width, height, bytes_per_line, QImage.Format_RGB888))
            return q_image
        except Exception as e:

            return None

    def save_changes(self):
        """
        Save changes to flagged fields in the database.
        """
        session = self.db_manager.Session()
        try:
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

            session.merge(self.record)
            session.commit()
            QMessageBox.information(self, "Success", "Changes saved successfully.")
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save changes: {e}")
        finally:
            session.close()