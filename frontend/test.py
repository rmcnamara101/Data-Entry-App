from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QTableWidget, QTableWidgetItem, QTextEdit, QProgressBar,
    QFrame, QStackedWidget, QMessageBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QPalette, QColor, QFont, QIcon
import sys
import os

class PathologyLabApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pathology Lab Data Entry System")
        self.setMinimumSize(1200, 800)
        self.init_ui()

    def init_ui(self):
        self.set_high_contrast_palette()

        # Main Layout
        main_layout = QHBoxLayout()
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Sidebar Navigation
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)

        # Stacked Widget for Main Sections
        self.stacked_widget = QStackedWidget()

        # 1) HOME PAGE
        home_page = self.create_home_page()
        self.stacked_widget.addWidget(home_page)

        # 2) FILE SCANNER
        scanner_page = self.create_scanner_page()
        self.stacked_widget.addWidget(scanner_page)

        # 3) DATABASE VIEW
        database_page = self.create_database_page()
        self.stacked_widget.addWidget(database_page)

        # 4) VALIDATION
        validation_page = self.create_validation_page()
        self.stacked_widget.addWidget(validation_page)

        # 5) DATA ENTRY EXECUTION
        execution_page = self.create_execution_page()
        self.stacked_widget.addWidget(execution_page)

        main_layout.addWidget(self.stacked_widget)

        # By default, show the Home page
        self.stacked_widget.setCurrentIndex(0)

    def set_high_contrast_palette(self):
        """
        Apply a high-contrast, laboratory-friendly color palette.
        """
        palette = QPalette()

        # --- Background / Window ---
        # A near-white background for high contrast with text
        palette.setColor(QPalette.Window, QColor("#F8FAFC"))

        # --- Text ---
        # Use a very dark gray or black for maximum legibility
        palette.setColor(QPalette.WindowText, QColor("#1C1C1C"))
        
        # Base (e.g. text edit background)
        palette.setColor(QPalette.Base, QColor("#FFFFFF"))
        palette.setColor(QPalette.AlternateBase, QColor("#EBEBEB"))

        # --- Buttons ---
        # We'll keep a lighter background, but styling in stylesheets
        # will ensure strong contrast for text.
        palette.setColor(QPalette.Button, QColor("#FFFFFF"))
        palette.setColor(QPalette.ButtonText, QColor("#1C1C1C"))

        # --- Highlights ---
        # Bold navy highlight for selection
        palette.setColor(QPalette.Highlight, QColor("#0B2C4B"))
        palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))

        self.setPalette(palette)

    def create_sidebar(self):
        """
        Create a vertical navigation sidebar with an added 'Home' button.
        """
        sidebar = QFrame()
        sidebar.setFrameShape(QFrame.StyledPanel)
        sidebar.setFixedWidth(220)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(20)

        # Sidebar Title (or Lab Logo placeholder)
        title_label = QLabel("PathLab")
        title_font = QFont("Arial", 18, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        btn_font = QFont("Arial", 12)
        buttons = [
            ("Home", "home", lambda: self.stacked_widget.setCurrentIndex(0)),
            ("File Scanner", "folder-open", lambda: self.stacked_widget.setCurrentIndex(1)),
            ("Database View", "database", lambda: self.stacked_widget.setCurrentIndex(2)),
            ("Validation", "check-circle", lambda: self.stacked_widget.setCurrentIndex(3)),
            ("Data Entry", "play-circle", lambda: self.stacked_widget.setCurrentIndex(4)),
        ]

        for label, icon, handler in buttons:
            button = QPushButton(f"  {label}")
            button.setFont(btn_font)
            # If icon is unavailable on the system, you may use a local icon path
            button.setIcon(QIcon.fromTheme(icon))
            button.setIconSize(QSize(20, 20))

            button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    background-color: #FFFFFF; 
                    color: #1C1C1C;
                    padding: 8px 20px;
                    border: 1px solid #0B2C4B;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #DDE7F0; /* Lightened background for hover */
                }
                QPushButton:pressed {
                    background-color: #BACFE0; /* Slightly darker on press */
                }
            """)
            button.clicked.connect(handler)
            layout.addWidget(button)

        layout.addStretch()  # Push buttons to the top

        return sidebar

    def create_home_page(self):
        """
        Creates a home page with a welcome message, possible branding, and
        quick navigation options.
        """
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)

        welcome_label = QLabel("Welcome to the Pathology Lab System")
        welcome_label.setFont(QFont("Arial", 20, QFont.Bold))
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_label.setStyleSheet("color: #1C1C1C;")

        sub_label = QLabel(
            "Here you can scan documents, view the database, validate data, "
            "and perform data entry procedures.\n\n"
            "Choose an option from the sidebar to get started."
        )
        sub_label.setFont(QFont("Arial", 14))
        sub_label.setAlignment(Qt.AlignCenter)
        sub_label.setWordWrap(True)
        sub_label.setStyleSheet("color: #1C1C1C;")

        layout.addStretch()
        layout.addWidget(welcome_label)
        layout.addWidget(sub_label)
        layout.addStretch()

        return page

    def create_scanner_page(self):
        """
        Create the File Scanner page.
        """
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Folder Selection
        folder_layout = QHBoxLayout()
        self.folder_label = QLabel("No folder selected")
        self.folder_label.setFont(QFont("Arial", 11))
        self.folder_label.setStyleSheet("color: #1C1C1C;")
        
        folder_button = QPushButton("Select Folder")
        folder_button.setFont(QFont("Arial", 11))
        folder_button.setStyleSheet("""
            QPushButton {
                background-color: #0B2C4B; 
                color: white; 
                padding: 6px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1B3C5D;
            }
            QPushButton:pressed {
                background-color: #0A2540;
            }
        """)
        folder_button.clicked.connect(self.select_folder)
        folder_layout.addWidget(self.folder_label)
        folder_layout.addWidget(folder_button)

        # File Table
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(5)
        self.file_table.setHorizontalHeaderLabels([
            "Filename", "Request Number", "Patient Name", "Medicare Number", "Status"
        ])
        self.file_table.verticalHeader().setVisible(False)
        self.file_table.setAlternatingRowColors(True)
        self.file_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #1B3C5D;
            }
            QTableWidget::item {
                color: #1C1C1C;
            }
            QHeaderView::section {
                background-color: #0B2C4B;
                color: white;
            }
        """)

        layout.addLayout(folder_layout)
        layout.addWidget(self.file_table)
        return page

    def create_database_page(self):
        """
        Create the Database View page.
        """
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Database Table
        self.db_table = QTableWidget()
        self.db_table.setColumnCount(8)
        self.db_table.setHorizontalHeaderLabels([
            "Request Number", "Given Names", "Surname", "Medicare Number",
            "Date of Birth", "Address", "Phone", "Needs Review"
        ])
        self.db_table.verticalHeader().setVisible(False)
        self.db_table.setAlternatingRowColors(True)
        self.db_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #1B3C5D;
            }
            QTableWidget::item {
                color: #1C1C1C;
            }
            QHeaderView::section {
                background-color: #0B2C4B;
                color: white;
            }
        """)

        # Refresh Button
        refresh_button = QPushButton("Refresh Database")
        refresh_button.setFont(QFont("Arial", 11))
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #0B2C4B; 
                color: white; 
                padding: 6px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1B3C5D;
            }
            QPushButton:pressed {
                background-color: #0A2540;
            }
        """)
        refresh_button.clicked.connect(self.refresh_database)

        layout.addWidget(refresh_button)
        layout.addWidget(self.db_table)
        return page

    def create_validation_page(self):
        """
        Create the Validation page.
        """
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Validation Text
        self.validation_text = QTextEdit()
        self.validation_text.setReadOnly(True)
        self.validation_text.setStyleSheet("color: #1C1C1C;")

        # Flagged Entries Table
        self.flagged_table = QTableWidget()
        self.flagged_table.setColumnCount(4)
        self.flagged_table.setHorizontalHeaderLabels([
            "Request Number", "Patient Name", "Error Details", "Actions"
        ])
        self.flagged_table.verticalHeader().setVisible(False)
        self.flagged_table.setAlternatingRowColors(True)
        self.flagged_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #1B3C5D;
            }
            QTableWidget::item {
                color: #1C1C1C;
            }
            QHeaderView::section {
                background-color: #0B2C4B;
                color: white;
            }
        """)

        layout.addWidget(self.validation_text)
        layout.addWidget(self.flagged_table)
        return page

    def create_execution_page(self):
        """
        Create the Data Entry Execution page.
        """
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                text-align: center;
                height: 24px;
                color: #1C1C1C;
                background-color: #FFFFFF;
            }
            QProgressBar::chunk {
                background-color: #0B2C4B;
            }
        """)

        # Execution Status
        self.execution_status = QTextEdit()
        self.execution_status.setReadOnly(True)
        self.execution_status.setStyleSheet("color: #1C1C1C;")

        # Execution Controls
        controls_layout = QHBoxLayout()

        start_button = QPushButton("Start Data Entry")
        start_button.setFont(QFont("Arial", 11))
        start_button.setStyleSheet("""
            QPushButton {
                background-color: #0B2C4B; 
                color: white; 
                padding: 6px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1B3C5D;
            }
            QPushButton:pressed {
                background-color: #0A2540;
            }
        """)
        start_button.clicked.connect(self.start_data_entry)

        stop_button = QPushButton("Stop Data Entry")
        stop_button.setFont(QFont("Arial", 11))
        stop_button.setStyleSheet("""
            QPushButton {
                background-color: #0B2C4B; 
                color: white; 
                padding: 6px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1B3C5D;
            }
            QPushButton:pressed {
                background-color: #0A2540;
            }
        """)
        stop_button.clicked.connect(self.stop_data_entry)

        controls_layout.addWidget(start_button)
        controls_layout.addWidget(stop_button)

        layout.addWidget(self.progress_bar)
        layout.addWidget(self.execution_status)
        layout.addLayout(controls_layout)
        return page

    # ------------------- BUTTON HANDLERS ------------------- #
    def select_folder(self):
        """
        Select a folder and update the file scanner label.
        """
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.folder_label.setText(folder)

    def refresh_database(self):
        """
        Refresh the database view.
        """
        QMessageBox.information(self, "Refresh Database", "Refreshing database...")

    def start_data_entry(self):
        """
        Start the data entry process.
        """
        QMessageBox.information(self, "Start Data Entry", "Starting data entry process...")

    def stop_data_entry(self):
        """
        Stop the data entry process.
        """
        QMessageBox.information(self, "Stop Data Entry", "Stopping data entry process...")

# ------------------- MAIN ENTRY POINT ------------------- #
def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = PathologyLabApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
