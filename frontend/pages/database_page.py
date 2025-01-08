from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QHBoxLayout, QDialog, QLabel, QLineEdit, QFormLayout, QDialogButtonBox
)
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import Qt
import os

# Import DatabaseManager from your backend
from backend.database.database import DatabaseManager, PatientRecord


class EditDialog(QDialog):
    def __init__(self, record, parent=None):
        super().__init__(parent)
        self.record = record
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Edit Record")
        self.setMinimumSize(1200, 600)  # Increase dialog size for better spacing
        main_layout = QHBoxLayout()

        # Left side: Image display
        image_layout = QVBoxLayout()
        img_label = QLabel()
        img_label.setAlignment(Qt.AlignCenter)
        if self.record.get("image_path") and os.path.exists(self.record["image_path"]):
            pixmap = QPixmap(self.record["image_path"])
            img_label.setPixmap(pixmap.scaled(600, 450, Qt.KeepAspectRatio))  # Larger image size
        else:
            img_label.setText("Image not available")
            img_label.setAlignment(Qt.AlignCenter)
        image_layout.addWidget(img_label)
        main_layout.addLayout(image_layout)

        # Right side: Field information
        fields_layout = QFormLayout()
        self.fields = {}

        for key, value in self.record.items():
            if key != "image_path":  # Skip the image_path field
                line_edit = QLineEdit(str(value) if value else "")
                self.fields[key] = line_edit
                fields_layout.addRow(key.replace("_", " ").capitalize() + ":", line_edit)

        # Add fields layout to the main layout
        right_layout = QVBoxLayout()
        right_layout.addLayout(fields_layout)
        right_layout.addStretch()  # Push the fields to the top
        main_layout.addLayout(right_layout)

        # Add Save/Cancel buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        right_layout.addWidget(buttons)

        self.setLayout(main_layout)

    def get_updated_record(self):
        """
        Retrieve updated values from the dialog fields.
        """
        updated_record = {key: field.text() for key, field in self.fields.items()}
        return updated_record




class DatabasePage(QWidget):
    """
    Display records from the 'patient_records' table (via DatabaseManager).
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

        # Table
        self.db_table = QTableWidget()
        self.db_table.setColumnCount(9)  # Updated for additional fields
        self.db_table.setHorizontalHeaderLabels([
            "ID", "Request Number", "Given Names", "Surname", "Mobile Phone", 
            "Provider Number", "Medicare Number", "Medicare Position", "Edit"
        ])
        self.db_table.verticalHeader().setVisible(False)
        self.db_table.setAlternatingRowColors(True)

        # Button row
        button_layout = QHBoxLayout()

        refresh_button = QPushButton("Refresh")
        refresh_button.setFont(QFont("Arial", 11))
        refresh_button.clicked.connect(self.load_records)

        flagged_button = QPushButton("Show Flagged Only")
        flagged_button.setFont(QFont("Arial", 11))
        flagged_button.clicked.connect(self.load_flagged)

        button_layout.addWidget(refresh_button)
        button_layout.addWidget(flagged_button)

        layout.addLayout(button_layout)
        layout.addWidget(self.db_table)
        self.setLayout(layout)

        # Load all records initially
        self.load_records()

    def load_records(self):
        session = self.db_manager.Session()
        try:
            # Query records with new fields
            results = session.query(
                PatientRecord.id,
                PatientRecord.request_number,
                PatientRecord.given_names,
                PatientRecord.surname,
                PatientRecord.mobile_phone,
                PatientRecord.provider_number,
                PatientRecord.medicare_number,
                PatientRecord.medicare_position
            ).all()

            self.populate_table(results)
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Error fetching records: {e}")
        finally:
            session.close()

    def populate_table(self, rows):
        """
        Fill the table with the given row data.
        Each row is a tuple or list: (id, request_number, given_names, surname, mobile_phone, provider_number, medicare_number, position)
        """
        self.db_table.setRowCount(len(rows))
        for row_idx, row_data in enumerate(rows):
            for col_idx, value in enumerate(row_data):
                self.db_table.setItem(row_idx, col_idx, QTableWidgetItem(str(value) if value else ""))

            # Add Edit button
            edit_button = QPushButton("Edit")
            edit_button.clicked.connect(lambda _, r=row_data: self.open_edit_dialog(r))
            self.db_table.setCellWidget(row_idx, len(row_data), edit_button)

    def open_edit_dialog(self, record_data):
        """
        Open the edit dialog for a record.
        """
        # Build the record dictionary dynamically, including the correct image path
        session = self.db_manager.Session()
        try:
            patient_record = session.query(PatientRecord).get(record_data[0])  # Fetch the record by ID
            record_dict = {
                "id": patient_record.id,
                "request_number": patient_record.request_number,
                "given_names": patient_record.given_names,
                "surname": patient_record.surname,
                "mobile_phone": patient_record.mobile_phone,
                "provider_number": patient_record.provider_number,
                "medicare_number": patient_record.medicare_number,
                "medicare_position": patient_record.medicare_position,
                "image_path": patient_record.image_path  # Use the actual image path from the database
            }
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to fetch patient record: {e}")
            return
        finally:
            session.close()

        dialog = EditDialog(record_dict, self)
        if dialog.exec_() == QDialog.Accepted:
            updated_record = dialog.get_updated_record()
            self.save_record(updated_record)


    def save_record(self, updated_record):
        """
        Save the updated record to the database.
        """
        session = self.db_manager.Session()
        try:
            record = session.query(PatientRecord).get(updated_record["id"])
            for key, value in updated_record.items():
                if key != "id" and hasattr(record, key):
                    setattr(record, key, value)
            session.commit()
            QMessageBox.information(self, "Success", "Record updated successfully!")
            self.load_records()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update record: {e}")
        finally:
            session.close()

    def load_flagged(self):
        """
        Only load records that need manual review.
        """
        session = self.db_manager.Session()
        try:
            # Query flagged records
            results = session.query(
                PatientRecord.id,
                PatientRecord.request_number,
                PatientRecord.given_names,
                PatientRecord.surname,
                PatientRecord.mobile_phone,
                PatientRecord.provider_number,
                PatientRecord.medicare_number,
                PatientRecord.medicare_position
            ).filter(PatientRecord.needs_manual_review == True).all()

            self.populate_table(results)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load flagged records: {e}")
        finally:
            session.close()

