# pages/home_page.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class HomePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
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

        self.setLayout(layout)
