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

        # Pick one of the style options here:
        #   option1: Modern Blue
        #   option2: Soft Pastel
        #   option3: Dark Theme
        self.apply_style("option1")

        self.init_ui()

    def init_ui(self):
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

    # ------------------- STYLE OPTIONS ------------------- #
    def apply_style(self, option="option1"):
        """
        Switch between different design options.
        option1: Modern Blue
        option2: Soft Pastel
        option3: Dark Theme
        """
        if option == "option1":
            self.set_modern_blue_palette()
        elif option == "option2":
            self.set_soft_pastel_palette()
        elif option == "option3":
            self.set_dark_theme_palette()
        else:
            self.set_modern_blue_palette()  # fallback

    def set_modern_blue_palette(self):
        """
        A crisp, modern palette with bright backgrounds and navy highlights.
        """
        palette = QPalette()

        # --- Background / Window ---
        palette.setColor(QPalette.Window, QColor("#F0F4F8"))
        # --- Text ---
        palette.setColor(QPalette.WindowText, QColor("#0A0A0A"))
        # --- Base (for text edits, etc.) ---
        palette.setColor(QPalette.Base, QColor("#FFFFFF"))
        palette.setColor(QPalette.AlternateBase, QColor("#E8ECF1"))
        # --- Buttons ---
        palette.setColor(QPalette.Button, QColor("#FFFFFF"))
        palette.setColor(QPalette.ButtonText, QColor("#0A0A0A"))
        # --- Highlights ---
        palette.setColor(QPalette.Highlight, QColor("#1D4F8C"))
        palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))

        self.setPalette(palette)
        # Optional: set a global Fusion style
        QApplication.setStyle("Fusion")

    def set_soft_pastel_palette(self):
        """
        A softer pastel palette with gentle highlights and minimal contrast.
        """
        palette = QPalette()

        # --- Background / Window ---
        palette.setColor(QPalette.Window, QColor("#FFFDFC"))  # Off-white
        # --- Text ---
        palette.setColor(QPalette.WindowText, QColor("#403C3C"))
        # --- Base ---
        palette.setColor(QPalette.Base, QColor("#FFFFFF"))
        palette.setColor(QPalette.AlternateBase, QColor("#FAF3F3"))
        # --- Buttons ---
        palette.setColor(QPalette.Button, QColor("#FEEAE6"))
        palette.setColor(QPalette.ButtonText, QColor("#5C5757"))
        # --- Highlights ---
        palette.setColor(QPalette.Highlight, QColor("#F9B7AA"))
        palette.setColor(QPalette.HighlightedText, QColor("#3F3F3F"))

        self.setPalette(palette)
        QApplication.setStyle("Fusion")

    def set_dark_theme_palette(self):
        """
        A dark theme palette for low-light environments or to reduce eye strain.
        """
        palette = QPalette()

        # --- Background / Window ---
        palette.setColor(QPalette.Window, QColor("#2C2C2C"))
        # --- Text ---
        palette.setColor(QPalette.WindowText, QColor("#E5E5E5"))
        # --- Base ---
        palette.setColor(QPalette.Base, QColor("#3C3C3C"))
        palette.setColor(QPalette.AlternateBase, QColor("#474747"))
        # --- Buttons ---
        palette.setColor(QPalette.Button, QColor("#3C3C3C"))
        palette.setColor(QPalette.ButtonText, QColor("#E5E5E5"))
        # --- Highlights ---
        palette.setColor(QPalette.Highlight, QColor("#5596E6"))
        palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))

        self.setPalette(palette)
        QApplication.setStyle("Fusion")

    # ------------------- SIDEBAR ------------------- #
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
            button.setIcon(QIcon.fromTheme(icon))
            button.setIconSize(QSize(20, 20))

            # Notice: styleSheet uses placeholders for color so it adapts to the palette
            button.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px 20px;
                    border: 1px solid palette(Highlight);
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: palette(AlternateBase);
                }
                QPushButton:pressed {
                    background-color: palette(Highlight);
                    color: palette(HighlightedText);
                }
            """)
            button.clicked.connect(handler)
            layout.addWidget(button)

        layout.addStretch()  # Push buttons to the top

        return sidebar

    # ------------------- PAGES ------------------- #
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

        sub_label = QLabel(
            "Here you can scan documents, view the database, validate data, "
            "and perform data entry procedures.\n\n"
            "Choose an option from the sidebar to get started."
        )
        sub_label.setFont(QFont("Arial", 14))
        sub_label.setAlignment(Qt.AlignCenter)
        sub_label.setWordWrap(True)

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

        folder_button = QPushButton("Select Folder")
        folder_button.setFont(QFont("Arial", 11))
        folder_button.setStyleSheet("""
            QPushButton {
                background-color: palette(Highlight); 
                color: palette(HighlightedText); 
                padding: 6px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: palette(Highlight).lighter(110);
            }
            QPushButton:pressed {
                background-color: palette(Highlight).darker(110);
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
                gridline-color: palette(Shadow);
            }
            QTableWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background-color: palette(Highlight);
                color: palette(HighlightedText);
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
                gridline-color: palette(Shadow);
            }
            QTableWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background-color: palette(Highlight);
                color: palette(HighlightedText);
            }
        """)

        # Refresh Button
        refresh_button = QPushButton("Refresh Database")
        refresh_button.setFont(QFont("Arial", 11))
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: palette(Highlight); 
                color: palette(HighlightedText); 
                padding: 6px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: palette(Highlight).lighter(110);
            }
            QPushButton:pressed {
                background-color: palette(Highlight).darker(110);
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
                gridline-color: palette(Shadow);
            }
            QTableWidget::item {
                padding: 4px;
            }
            QHeaderView::section {
                background-color: palette(Highlight);
                color: palette(HighlightedText);
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
            }
            QProgressBar::chunk {
                background-color: palette(Highlight);
            }
        """)

        # Execution Status
        self.execution_status = QTextEdit()
        self.execution_status.setReadOnly(True)

        # Execution Controls
        controls_layout = QHBoxLayout()

        start_button = QPushButton("Start Data Entry")
        start_button.setFont(QFont("Arial", 11))
        start_button.setStyleSheet("""
            QPushButton {
                background-color: palette(Highlight); 
                color: palette(HighlightedText); 
                padding: 6px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: palette(Highlight).lighter(110);
            }
            QPushButton:pressed {
                background-color: palette(Highlight).darker(110);
            }
        """)
        start_button.clicked.connect(self.start_data_entry)

        stop_button = QPushButton("Stop Data Entry")
        stop_button.setFont(QFont("Arial", 11))
        stop_button.setStyleSheet("""
            QPushButton {
                background-color: palette(Highlight); 
                color: palette(HighlightedText); 
                padding: 6px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: palette(Highlight).lighter(110);
            }
            QPushButton:pressed {
                background-color: palette(Highlight).darker(110);
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

    # Create the main window
    window = PathologyLabApp()
    # Possibly remove other set_*_palette() calls in PathologyLabApp.__init__
    # so that only apply_style controls the final palette.

    # Force the Fusion style if you want a consistent cross-platform baseline
    QApplication.setStyle("Fusion")

    # Now pick your style
    window.apply_style("option2")  # or "option1" / "option3"

    # Show window
    window.show()
    sys.exit(app.exec_())



if __name__ == "__main__":
    main()
