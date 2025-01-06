# pages/database_page.py

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QHBoxLayout
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

# Import DatabaseManager from your backend
from backend.database import DatabaseManager, PatientRecord


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
        self.db_table.setColumnCount(5)
        self.db_table.setHorizontalHeaderLabels([
            "ID", "Request Number", "Given Names", "Surname", "Needs Review?"
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
            # This returns a list of tuples, each with (id, request_number, given_names, surname, needs_manual_review)
            results = session.query(
                PatientRecord.id,
                PatientRecord.request_number,
                PatientRecord.given_names,
                PatientRecord.surname,
                PatientRecord.needs_manual_review
            ).all()

            self.populate_table(results)
        except Exception as e:
            QMessageBox.critical(self, "DB Error", f"Error fetching records: {e}")
        finally:
            session.close()


    def load_flagged(self):
        """
        Only load records that need manual review.
        """
        flagged_entries = self.db_manager.get_flagged_entries()
        # flagged_entries is a list of dict like:
        # [ { 'id':..., 'request_number':..., 'given_names':..., 'surname':..., ...}, ...]
        # We can adapt populate_table to handle dict or re-map as needed
        # Let’s convert them to a format our populate_table can handle
        results = []
        for f in flagged_entries:
            results.append((f["id"], f["request_number"], f["given_names"], f["surname"], True))

        self.populate_table(results)

    def populate_table(self, rows):
        """
        Fill the table with the given row data.
        Each row is a tuple or list: (id, request_number, given_names, surname, needs_manual_review)
        """
        self.db_table.setRowCount(len(rows))
        for row_idx, row_data in enumerate(rows):
            # row_data is like (1, 'REQ001', 'John', 'Doe', 0/1 or True/False)
            self.db_table.setItem(row_idx, 0, QTableWidgetItem(str(row_data[0]) or ""))
            self.db_table.setItem(row_idx, 1, QTableWidgetItem(str(row_data[1]) or ""))
            self.db_table.setItem(row_idx, 2, QTableWidgetItem(str(row_data[2]) or ""))
            self.db_table.setItem(row_idx, 3, QTableWidgetItem(str(row_data[3]) or ""))

            # Convert boolean into "Yes"/"No"
            needs_review = row_data[4]
            if isinstance(needs_review, bool):
                nr_text = "Yes" if needs_review else "No"
            else:
                # If it's an int 0/1
                nr_text = "Yes" if needs_review else "No"

            self.db_table.setItem(row_idx, 4, QTableWidgetItem(nr_text))
