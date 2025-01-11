# Writing the `SettingsPage` class
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog
from PyQt5.QtCore import Qt
import subprocess
import sys


class SettingsPage(QWidget):
    """
    A page for application settings, including access to tools like the Field Editor.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        header = QLabel("Settings")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(header)

        field_editor_button = QPushButton("Launch Field Editor")
        field_editor_button.setToolTip("Open the Field Editor tool.")
        field_editor_button.clicked.connect(self.launch_field_editor)
        layout.addWidget(field_editor_button)

        field_editor_button = QPushButton("Launch Anchor Editor")
        field_editor_button.setToolTip("Open the Anchor Editor tool.")
        field_editor_button.clicked.connect(self.launch_anchor_editor)
        layout.addWidget(field_editor_button)

        placeholder = QLabel("Additional settings can go here.")
        placeholder.setAlignment(Qt.AlignCenter)
        layout.addWidget(placeholder)

        layout.addStretch()
        self.setLayout(layout)


    def launch_field_editor(self):
        """
        Launches the Field Editor tool as a separate process.
        """
        config_path = "/Users/rileymcnamara/CODE/2024/Data-Entry-App/backend/form_scanning/configs/field_config.json"
        field_editor_path = "/Users/rileymcnamara/CODE/2024/Data-Entry-App/frontend/pages/settings/field_editor.py"

        # Use sys.executable to get the current Python interpreter path
        python_executable = sys.executable
        subprocess.Popen([python_executable, field_editor_path, config_path], shell=False)

    def launch_anchor_editor(self):
        """
        Launches the Anchor Tool as a separate process.
        """
        anchor_editor_path = "/Users/rileymcnamara/CODE/2024/Data-Entry-App/frontend/pages/settings/anchor_editor.py"

        python_executable = sys.executable
        subprocess.Popen([python_executable, anchor_editor_path], shell=False)