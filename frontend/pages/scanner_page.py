from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QFileDialog, QProgressBar
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal

# Import your backend function
from backend.FolderProcessor import process_folder
import os

class FolderProcessorThread(QThread):
    """
    A QThread to handle folder processing and send updates to the progress bar.
    """
    progress_updated = pyqtSignal(int)
    processing_done = pyqtSignal(dict)

    def __init__(self, folder_path):
        super().__init__()
        self.folder_path = folder_path

    def run(self):
        stats = process_folder(self.folder_path, self.progress_updated)
        self.processing_done.emit(stats)

class ScannerPage(QWidget):
    """
    This page handles folder scanning and automatically adds records to the DB
    (via process_folder).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.folder_label = None
        self.file_table = None
        self.stats_label = None
        self.progress_bar = None
        self.init_ui()
        self.processor_thread = None

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Folder Selection Layout
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel("No folder selected")
        self.folder_label.setFont(QFont("Arial", 11))

        folder_button = QPushButton("Select Folder")
        folder_button.setFont(QFont("Arial", 11))
        folder_button.clicked.connect(self.select_folder)

        folder_layout.addWidget(self.folder_label)
        folder_layout.addWidget(folder_button)

        # File Table
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(2)
        self.file_table.setHorizontalHeaderLabels(["File Name", "Status"])
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.setAlternatingRowColors(True)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)

        # Stats Label (to show "X images processed, Y records added")
        self.stats_label = QLabel("")
        self.stats_label.setFont(QFont("Arial", 10))

        layout.addLayout(folder_layout)
        layout.addWidget(self.file_table)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.stats_label)

        self.setLayout(layout)

    def select_folder(self):
        """
        Handler for 'Select Folder' button. Calls process_folder in your backend,
        updates the table and stats label.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.folder_label.setText(folder)
            self.start_processing(folder)

    def start_processing(self, folder_path):
        """
        Starts the folder processing in a separate thread and connects signals for updates.
        """
        self.processor_thread = FolderProcessorThread(folder_path)
        self.processor_thread.progress_updated.connect(self.update_progress)
        self.processor_thread.processing_done.connect(self.on_processing_done)
        self.processor_thread.start()

    def update_progress(self, value):
        """
        Updates the progress bar.
        """
        self.progress_bar.setValue(value)

    def on_processing_done(self, stats):
        """
        Handles the completion of folder processing.
        """
        total = stats.get("total_images", 0)
        added = stats.get("records_added", 0)

        # Show stats in a label
        self.stats_label.setText(
            f"Processed: {total} image(s). New records: {added}."
        )
        self.progress_bar.setValue(100)
        self.populate_table(stats.get("folder_path", ""), total)

    def populate_table(self, folder_path, total_count):
        """
        Populate the file table with the list of processed files.
        """
        images = []
        for f in os.listdir(folder_path):
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".tiff")):
                images.append(f)

        self.file_table.setRowCount(len(images))
        for row_idx, filename in enumerate(images):
            self.file_table.setItem(row_idx, 0, QTableWidgetItem(filename))
            self.file_table.setItem(row_idx, 1, QTableWidgetItem("Processed"))
