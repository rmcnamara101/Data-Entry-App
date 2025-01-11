import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '/Users/rileymcnamara/CODE/2024/Data-Entry-App/' )))

from dataclasses import asdict
from pathlib import Path
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QSpinBox, QCheckBox, QPushButton, QFileDialog,
    QTextEdit, QTabWidget, QGroupBox, QScrollArea, QMessageBox,
    QSlider
)
from PyQt5.QtCore import Qt, QRect
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen
import cv2
import numpy as np
from typing import Optional, Dict

from backend.form_scanning.TextProcessor import TextProcessor
from backend.form_scanning.MedicareAnchorDetector import MedicareAnchorDetector, MedicareDetector, MedicareAnchor

class ConfigPanel(QWidget):
    """Configuration panel for Medicare Anchor Finder parameters."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Target Region Group
        region_group = QGroupBox("Target Region")
        region_layout = QHBoxLayout()
        
        self.region_inputs = {}
        for coord in ['x1', 'y1', 'x2', 'y2']:
            coord_layout = QVBoxLayout()
            label = QLabel(coord)
            spinbox = QSpinBox()
            spinbox.setRange(0, 2000)
            spinbox.setToolTip(f"Enter {coord} coordinate of target region")
            self.region_inputs[coord] = spinbox
            coord_layout.addWidget(label)
            coord_layout.addWidget(spinbox)
            region_layout.addLayout(coord_layout)
            
        region_group.setLayout(region_layout)
        layout.addWidget(region_group)
        
        # Medicare Pattern
        pattern_group = QGroupBox("Medicare Pattern")
        pattern_layout = QVBoxLayout()
        self.pattern_input = QLineEdit()
        self.pattern_input.setToolTip("Enter regex pattern for Medicare number detection")
        pattern_layout.addWidget(self.pattern_input)
        pattern_group.setLayout(pattern_layout)
        layout.addWidget(pattern_group)
        
        # Debug Mode
        debug_group = QGroupBox("Debug Settings")
        debug_layout = QVBoxLayout()
        self.debug_checkbox = QCheckBox("Enable Debug Mode")
        self.debug_checkbox.setToolTip("Toggle detailed debug logging")
        debug_layout.addWidget(self.debug_checkbox)
        debug_group.setLayout(debug_layout)
        layout.addWidget(debug_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save Config")
        self.load_button = QPushButton("Load Config")
        self.reset_button = QPushButton("Reset to Defaults")
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.reset_button)
        layout.addLayout(button_layout)
        
        layout.addStretch()
        self.setLayout(layout)
        
        # Set default values
        self.reset_to_defaults()
        
    def reset_to_defaults(self):
        """Reset all configuration parameters to default values."""
        default_region = (531, 0, 804, 98)
        for coord, value in zip(['x1', 'y1', 'x2', 'y2'], default_region):
            self.region_inputs[coord].setValue(value)
        self.pattern_input.setText(r"^\d{10}\s*/\s*\d$")
        self.debug_checkbox.setChecked(True)
        
    def get_config(self) -> Dict:
        """Get current configuration as dictionary."""
        return {
            'target_region': (
                self.region_inputs['x1'].value(),
                self.region_inputs['y1'].value(),
                self.region_inputs['x2'].value(),
                self.region_inputs['y2'].value()
            ),
            'medicare_pattern': self.pattern_input.text(),
            'debug_mode': self.debug_checkbox.isChecked()
        }
        
    def load_config(self, config: Dict):
        """Load configuration from dictionary."""
        region = config.get('target_region', (531, 0, 804, 98))
        for coord, value in zip(['x1', 'y1', 'x2', 'y2'], region):
            self.region_inputs[coord].setValue(value)
        self.pattern_input.setText(config.get('medicare_pattern', r"^\d{10}\s*/\s*\d$"))
        self.debug_checkbox.setChecked(config.get('debug_mode', True))

class ImageViewer(QWidget):
    """Widget for displaying and visualizing processed images."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.image = None
        self.medicare_anchor = None
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Image display
        self.image_label = QLabel()
        self.image_label.setMinimumSize(1024, 768)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.image_label)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        # Controls
        controls_layout = QHBoxLayout()
        self.load_button = QPushButton("Load Image")
        controls_layout.addWidget(self.load_button)
        layout.addLayout(controls_layout)
        
        self.setLayout(layout)
        
    def update_image(self, image: np.ndarray, target_region: tuple, medicare_anchor: Optional[MedicareAnchor] = None):
        """Update displayed image with visualization overlays."""
        if image is None:
            return
            
        self.image = image.copy()
        self.medicare_anchor = medicare_anchor
        
        # Draw target region
        cv2.rectangle(
            self.image,
            (target_region[0], target_region[1]),
            (target_region[2], target_region[3]),
            (0, 255, 255),
            2
        )
        
        # Draw Medicare anchor if detected
        if medicare_anchor:
            x1, y1, x2, y2 = medicare_anchor.bounding_box
            cv2.rectangle(
                self.image,
                (x1, y1),
                (x2, y2),
                (0, 255, 0),
                2
            )
            
            # Add text annotation
            text = f"Medicare: {medicare_anchor.text} ({medicare_anchor.confidence:.1f}%)"
            cv2.putText(
                self.image,
                text,
                (x1, y1-5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2
            )
        
        # Convert to QImage and display
        height, width, channel = self.image.shape
        bytes_per_line = 3 * width
        q_image = QImage(
            self.image.data,
            width,
            height,
            bytes_per_line,
            QImage.Format.Format_RGB888
        ).rgbSwapped()
        
        self.image_label.setPixmap(QPixmap.fromImage(q_image))

class DebugLogPanel(QWidget):
    """Panel for displaying debug logs and processing information."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        self.clear_button = QPushButton("Clear Logs")
        self.clear_button.clicked.connect(self.clear_logs)
        layout.addWidget(self.clear_button)
        
        self.setLayout(layout)
        
    def append_log(self, message: str):
        """Append message to debug log."""
        self.log_text.append(message)
        
    def clear_logs(self):
        """Clear all debug logs."""
        self.log_text.clear()

class MedicareFinderGUI(QMainWindow):
    """Main window for Medicare Anchor Finder GUI tool."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.current_image = None
        self.medicare_detector = None
        
    def init_ui(self):
        self.setWindowTitle('Medicare Anchor Finder Tool')
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout()
        
        # Left panel for configuration
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        self.config_panel = ConfigPanel()
        left_layout.addWidget(self.config_panel)
        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(400)
        
        # Right panel with tabs
        right_panel = QTabWidget()
        
        # Image viewer tab
        self.image_viewer = ImageViewer()
        right_panel.addTab(self.image_viewer, "Visualization")
        
        # Debug log tab
        self.debug_log = DebugLogPanel()
        right_panel.addTab(self.debug_log, "Debug Logs")
        
        # Add panels to main layout
        layout.addWidget(left_panel)
        layout.addWidget(right_panel)
        
        central_widget.setLayout(layout)
        
        # Connect signals
        self.config_panel.save_button.clicked.connect(self.save_config)
        self.config_panel.load_button.clicked.connect(self.load_config)
        self.config_panel.reset_button.clicked.connect(self.reset_config)
        self.image_viewer.load_button.clicked.connect(self.load_image)
        
        # Connect configuration change signals
        for spinbox in self.config_panel.region_inputs.values():
            spinbox.valueChanged.connect(self.process_image)
        self.config_panel.pattern_input.textChanged.connect(self.process_image)
        self.config_panel.debug_checkbox.stateChanged.connect(self.process_image)
        
    def load_image(self):
        """Load an image file for processing."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open Image File",
            "",
            "Images (*.png *.jpg *.jpeg)"
        )
        
        if file_name:
            self.current_image = cv2.imread(file_name)
            if self.current_image is not None:
                self.process_image()
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Failed to load image file."
                )
    
    def process_image(self):
        """Process current image with current configuration."""
        if self.current_image is None:
            return
            
        config = self.config_panel.get_config()
        
        # Create detector with current configuration
        self.medicare_detector = MedicareDetector(debug_mode=config['debug_mode'])
        self.medicare_detector.target_region = config['target_region']
        self.medicare_detector.medicare_pattern = config['medicare_pattern']
        
        # Process image
        medicare_anchor = self.medicare_detector.find_medicare_number(self.current_image)
        
        # Update visualization
        self.image_viewer.update_image(
            self.current_image,
            config['target_region'],
            medicare_anchor
        )
        
        # Update debug log
        if config['debug_mode']:
            self.debug_log.append_log(
                f"\n--- Processing with configuration ---\n"
                f"Target Region: {config['target_region']}\n"
                f"Medicare Pattern: {config['medicare_pattern']}\n"
                f"Result: {medicare_anchor}\n"
            )
    
    def save_config(self):
        """Save current configuration to file."""
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save Configuration",
            "",
            "JSON Files (*.json)"
        )
        
        if file_name:
            config = self.config_panel.get_config()
            try:
                with open(file_name, 'w') as f:
                    json.dump(config, f, indent=4)
                QMessageBox.information(
                    self,
                    "Success",
                    "Configuration saved successfully."
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to save configuration: {str(e)}"
                )
    
    def load_config(self):
        """Load configuration from file."""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Load Configuration",
            "",
            "JSON Files (*.json)"
        )
        
        if file_name:
            try:
                with open(file_name, 'r') as f:
                    config = json.load(f)
                self.config_panel.load_config(config)
                self.process_image()
                QMessageBox.information(
                    self,
                    "Success",
                    "Configuration loaded successfully."
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to load configuration: {str(e)}"
                )
    
    def reset_config(self):
        """Reset configuration to default values."""
        self.config_panel.reset_to_defaults()
        self.process_image()

def main():
    app = QApplication(sys.argv)
    window = MedicareFinderGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()