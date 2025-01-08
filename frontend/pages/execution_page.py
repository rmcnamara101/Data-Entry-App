from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, QPushButton, QTextEdit,
    QFileDialog, QLabel, QTableWidget, QTableWidgetItem, QCheckBox, QHeaderView, QMessageBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from backend.database.database import DatabaseManager, PatientRecord
from backend.data_entry.ProtocolExecutor import ProtocolExecutor

class ExecutionPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.protocol_path = None
        self.db_manager = DatabaseManager()
        self.progress_bar = None
        self.execution_status = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Protocol Selection
        protocol_layout = QHBoxLayout()
        protocol_label = QLabel("Selected Protocol:")
        self.protocol_display = QLabel("No file selected")
        protocol_button = QPushButton("Select Protocol JSON")
        protocol_button.clicked.connect(self.select_protocol_file)

        protocol_layout.addWidget(protocol_label)
        protocol_layout.addWidget(self.protocol_display)
        protocol_layout.addWidget(protocol_button)

        # Database Entry Selection
        db_layout = QVBoxLayout()
        db_label = QLabel("Select Database Entries:")
        db_label.setFont(QFont("Arial", 11))

        self.entry_table = QTableWidget()
        self.entry_table.setColumnCount(3)
        self.entry_table.setHorizontalHeaderLabels(["Request Number", "Surname", "Request Date"])
        self.entry_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.entry_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.entry_table.setSelectionMode(QTableWidget.MultiSelection)

        select_all_checkbox = QCheckBox("Select All")
        select_all_checkbox.stateChanged.connect(self.toggle_select_all)

        db_layout.addWidget(db_label)
        db_layout.addWidget(self.entry_table)
        db_layout.addWidget(select_all_checkbox)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)

        # Execution Status
        self.execution_status = QTextEdit()
        self.execution_status.setReadOnly(True)

        # Execution Controls
        controls_layout = QHBoxLayout()

        start_button = QPushButton("Start Data Entry")
        start_button.setFont(QFont("Arial", 11))
        start_button.clicked.connect(self.start_data_entry)

        stop_button = QPushButton("Stop Data Entry")
        stop_button.setFont(QFont("Arial", 11))
        stop_button.clicked.connect(self.stop_data_entry)

        controls_layout.addWidget(start_button)
        controls_layout.addWidget(stop_button)

        # Combine Layouts
        layout.addLayout(protocol_layout)
        layout.addLayout(db_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.execution_status)
        layout.addLayout(controls_layout)
        self.setLayout(layout)

        # Load database entries initially
        self.load_database_entries()

    def select_protocol_file(self):
        """
        Open a file dialog to select a protocol JSON file.
        """
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Protocol JSON", "", "JSON Files (*.json);;All Files (*)", options=options)
        if file_path:
            self.protocol_path = file_path
            self.protocol_display.setText(file_path)

    def load_database_entries(self):
        """
        Load entries from the database into the table.
        """
        session = self.db_manager.Session()
        try:
            records = session.query(
                PatientRecord.request_number,
                PatientRecord.surname,
                PatientRecord.request_date
            ).all()
            self.populate_entry_table(records)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load database entries: {e}")
        finally:
            session.close()

    def populate_entry_table(self, records):
        """
        Populate the table with database records.
        """
        self.entry_table.setRowCount(len(records))
        for row_idx, record in enumerate(records):
            for col_idx, value in enumerate(record):
                self.entry_table.setItem(row_idx, col_idx, QTableWidgetItem(str(value)))

    def toggle_select_all(self, state):
        """
        Select or deselect all rows in the entry table.
        """
        for row in range(self.entry_table.rowCount()):
            self.entry_table.selectRow(row) if state == Qt.Checked else self.entry_table.clearSelection()

    def start_data_entry(self):
        """
        Handler for 'Start Data Entry' button.
        """
        if not self.protocol_path:
            self.append_log("Please select a protocol file.")
            return

        selected_rows = self.entry_table.selectionModel().selectedRows()
        if not selected_rows:
            self.append_log("No entries selected. Please select entries to proceed.")
            return

        session = self.db_manager.Session()
        try:
            selected_entries = [
                session.query(PatientRecord).filter_by(request_number=self.entry_table.item(row.row(), 0).text()).first()
                for row in selected_rows
            ]

            executor = ProtocolExecutor(self.protocol_path)
            executor.execute_for_multiple_records(selected_entries)
            self.append_log("Data entry completed successfully.")
        except Exception as e:
            self.append_log(f"Error during execution: {e}")
        finally:
            session.close()

    def stop_data_entry(self):
        """
        Handler for 'Stop Data Entry' button.
        """
        self.append_log("Data entry stopped by user.")
        self.progress_bar.setValue(0)

    def append_log(self, message):
        """
        Append a message to the execution log.
        """
        self.execution_status.append(message)
