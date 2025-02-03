import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '/Users/rileymcnamara/CODE/2024/Data-Entry-App/' )))

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QStackedWidget, QHBoxLayout, QFrame,
    QVBoxLayout, QPushButton, QMenuBar, QStatusBar, QAction
)
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QIcon, QFont

# Import each page from your `pages/` folder
from frontend.pages.home_page import HomePage
from frontend.pages.scanner_page import ScannerPage
from frontend.pages.database_page import DatabasePage
from frontend.pages.validation_page import ValidationPage
from frontend.pages.execution_page import ExecutionPage
from frontend.pages.settings_page import SettingsPage  # New import


class MainWindow(QMainWindow):
    """
    The main application window, which manages:
    - A sidebar for navigation.
    - A QStackedWidget for switching between pages.
    - A menu bar and status bar for common application actions.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pathology Lab Data Entry System")
        self.setMinimumSize(1200, 800)

        # QStackedWidget to hold page widgets
        self.stacked_widget = QStackedWidget()

        # Set up the central layout for the main window
        self.init_layout()

        # Create the menu bar and status bar
        self.init_menu_bar()
        self.init_status_bar()

        # By default, show the Home page (index 0 in the stacked widget)
        self.stacked_widget.setCurrentIndex(0)

    def init_layout(self):
        """
        Builds the main layout, which includes a sidebar (QFrame)
        and the QStackedWidget containing the different pages.
        """
        # Create a central widget with a horizontal layout
        central_widget = QWidget()
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # Sidebar
        sidebar = self.create_sidebar()
        main_layout.addWidget(sidebar)

        # Add pages to the stacked widget
        self.init_pages()
        main_layout.addWidget(self.stacked_widget)

    def init_menu_bar(self):
        """
        Create a simple menu bar with a 'File' menu for demonstration.
        """
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        file_menu = menu_bar.addMenu("&File")

        # Example: Exit action
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def init_status_bar(self):
        """
        Create a status bar to show brief messages.
        """
        status_bar = QStatusBar(self)
        status_bar.showMessage("Ready")
        self.setStatusBar(status_bar)

    def init_pages(self):
        """
        Instantiate each page and add it to the QStackedWidget.
        The order here matches the indexes we use in the sidebar buttons.
        """
        self.stacked_widget.addWidget(HomePage(self))       # index 0
        self.stacked_widget.addWidget(ScannerPage(self))    # index 1
        self.stacked_widget.addWidget(DatabasePage(self))   # index 2
        self.stacked_widget.addWidget(ValidationPage(self)) # index 3
        self.stacked_widget.addWidget(ExecutionPage(self))  # index 4
        self.stacked_widget.addWidget(SettingsPage(self))   # index 5

    def create_sidebar(self):
        """
        Create a vertical navigation sidebar.
        Each button switches the stacked widget to a particular page.
        """
        sidebar = QFrame()
        sidebar.setFixedWidth(220)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(20)

        # Sidebar Title
        title_label = QPushButton("PathLab")
        # Using a QPushButton to style it similarly to other nav buttons, 
        # but it's effectively just a label. If you prefer, use QLabel.
        title_label.setFont(QFont("Arial", 18, QFont.Bold))
        title_label.setEnabled(False)  # Make it non-clickable
        layout.addWidget(title_label)

        # Each tuple: (Button text, Icon name, page index)
        nav_buttons = [
            ("Home", "home", 0),
            ("File Scanner", "folder-open", 1),
            ("Database View", "database", 2),
            ("Validation", "check-circle", 3),
            ("Data Entry", "play-circle", 4),
            ("Settings", "settings", 5),  # New button
        ]

        for text, icon_name, page_idx in nav_buttons:
            btn = QPushButton(f"  {text}")
            btn.setFont(QFont("Arial", 12))
            # If your OS supports themed icons, QIcon.fromTheme might work
            # Alternatively, load icons from your resources
            btn.setIcon(QIcon.fromTheme(icon_name))
            btn.setIconSize(QSize(20, 20))
            # Connect the button to a function that switches pages
            btn.clicked.connect(lambda _, i=page_idx: self.switch_page(i))

            layout.addWidget(btn)

        layout.addStretch()  # pushes the buttons to the top

        return sidebar

    def switch_page(self, index):
        """
        Switch the QStackedWidget to a particular page (by index).
        """
        self.stacked_widget.setCurrentIndex(index)


# OPTIONAL:
# If you'd like to run just this file for testing (without `main.py`):
# you can put a quick test harness here.
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())
