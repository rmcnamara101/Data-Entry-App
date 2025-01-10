import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '/Users/rileymcnamara/CODE/2024/Data-Entry-App/' )))

import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QVBoxLayout, QPushButton, QFileDialog, QWidget, QLabel, QGraphicsItem, QGraphicsEllipseItem,
    QGraphicsSimpleTextItem
)
from PyQt5.QtGui import QPixmap, QPen, QBrush, QPen
from PyQt5.QtCore import Qt, QRectF, QPointF
from backend.form_scanning.MedicareAnchorDetector import MedicareAnchorDetector, MedicareDetector
from backend.form_scanning.TextProcessor import TextProcessor
import cv2



class FieldEditor(QMainWindow):
    def __init__(self, config_path):
        super().__init__()
        self.config_path = config_path
        self.config = self.load_config(config_path)
        self.image_path = None
        self.field_items = {}
        self.anchor_point = None
        self.is_anchor_set = False
        self.labels = []
        self.anchor_visual = None  # To store the visual anchor rectangle
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Field Region Editor")
        self.setGeometry(100, 100, 1200, 800)

        # Main layout
        layout = QVBoxLayout()

        # Graphics View and Scene
        self.graphics_view = QGraphicsView(self)
        self.scene = QGraphicsScene(self)
        self.graphics_view.setScene(self.scene)
        layout.addWidget(self.graphics_view)

        # Buttons
        self.load_image_btn = QPushButton("Load Image", self)
        self.load_image_btn.clicked.connect(self.load_image)
        layout.addWidget(self.load_image_btn)

        self.set_anchor_btn = QPushButton("Set Anchor Point", self)
        self.set_anchor_btn.clicked.connect(self.set_anchor_mode)
        layout.addWidget(self.set_anchor_btn)

        self.find_anchor_btn = QPushButton("Find Medicare Anchor", self)
        self.find_anchor_btn.clicked.connect(self.find_medicare_anchor)
        layout.addWidget(self.find_anchor_btn)

        self.save_config_btn = QPushButton("Save Config", self)
        self.save_config_btn.clicked.connect(self.save_config)
        layout.addWidget(self.save_config_btn)

        # Instructions
        self.instructions = QLabel("Instructions:\n1. Load an image.\n2. Find Medicare Anchor or Set Anchor Point.\n3. Adjust relative boxes.\n4. Save the configuration.")
        layout.addWidget(self.instructions)

        # Set central widget
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def load_config(self, path):
        try:
            with open(path, 'r') as file:
                return json.load(file)
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return {}

    def load_image(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Image File", "", "Images (*.png *.jpg *.jpeg *.tiff)")
        if file_name:
            self.image_path = file_name
            self.scene.clear()  # Clear the previous scene
            self.labels.clear()  # Clear labels
            self.image_path = file_name
            self.anchor_point = None
            self.is_anchor_set = False
            self.field_items.clear()
            
            # Load and add the image to the scene
            image = QPixmap(file_name)
            pixmap_item = self.scene.addPixmap(image)
            
            # Fit the view to the image
            self.graphics_view.fitInView(pixmap_item, Qt.KeepAspectRatio)


    def set_anchor_mode(self):
        if not self.image_path:
            print("Load an image first.")
            return

        # Clear existing boxes and labels
        for item in self.field_items.values():
            self.scene.removeItem(item)
        for label in self.labels:
            self.scene.removeItem(label)

        self.field_items.clear()
        self.labels.clear()

        # Reset anchor state
        self.anchor_point = None
        self.is_anchor_set = False

        # Enable setting anchor point
        self.graphics_view.setCursor(Qt.CrossCursor)
        self.graphics_view.mousePressEvent = self.set_anchor_point



    def set_anchor_point(self, event):
        if self.is_anchor_set:  # Prevent resetting the anchor
            return

        if event.button() == Qt.LeftButton:
            # Translate mouse click position to scene coordinates
            scene_pos = self.graphics_view.mapToScene(event.pos())
            self.anchor_point = QPointF(scene_pos.x(), scene_pos.y())
            print(f"Anchor set at: {self.anchor_point}")
            self.is_anchor_set = True

            # Display relative boxes
            self.graphics_view.setCursor(Qt.ArrowCursor)
            self.display_relative_boxes()

    def display_relative_boxes(self):
        if not self.anchor_point or "relative_offsets" not in self.config:
            print("Anchor point not set or configuration missing.")
            return

        # Clear previous items
        for item in self.field_items.values():
            self.scene.removeItem(item)
        for label in self.labels:
            self.scene.removeItem(label)

        self.field_items.clear()
        self.labels.clear()

        # Create and display boxes
        anchor_x, anchor_y = self.anchor_point.x(), self.anchor_point.y()
        for field_name, offset in self.config["relative_offsets"].items():
            rel_x, rel_y, width, height = offset
            x = anchor_x + rel_x
            y = anchor_y - rel_y

            rect = QRectF(x, y, width, height)
            rect_item = ResizableRectItem(rect, field_name)
            self.scene.addItem(rect_item)
            self.field_items[field_name] = rect_item

            # Store the label reference
            self.labels.append(rect_item.label)

    def save_config(self):
        if not self.field_items:
            print("No fields to save.")
            return

        # Ensure the config has a "relative_offsets" section
        if "relative_offsets" not in self.config:
            self.config["relative_offsets"] = {}

        # Update configuration with current rectangle positions
        for field_name, item in self.field_items.items():
            # Get the current position and size of the rectangle
            rect = item.rect()

            # Calculate relative offsets
            relative_x = int(rect.x() - self.anchor_point.x())  # Relative X
            relative_y = int(self.anchor_point.y() - rect.y())  # Relative Y
            width = int(rect.width())
            height = int(rect.height())

            # Update the config
            self.config["relative_offsets"][field_name] = [relative_x, relative_y, width, height]

            old_value = self.config["relative_offsets"][field_name]
            print(f"OLD {field_name} = {old_value}")
            print(f"NEW {field_name} = {[relative_x, relative_y, width, height]}")


        # Save the updated config to the file
        try:
            with open(self.config_path, 'w') as file:
                json.dump(self.config, file, indent=4)
            print(f"Configuration saved successfully at {self.config_path}")
        except Exception as e:
            print(f"Error saving configuration: {e}")




    def find_medicare_anchor(self):
        if not self.image_path:
            print("Load an image first.")
            return

        # Safely clear existing anchor visuals if any
        if self.anchor_visual:
            try:
                self.scene.removeItem(self.anchor_visual)
            except RuntimeError:
                print("Anchor visual was already deleted.")
            finally:
                self.anchor_visual = None

        if hasattr(self, 'search_region_visual') and self.search_region_visual:
            try:
                self.scene.removeItem(self.search_region_visual)
            except RuntimeError:
                print("Search region visual was already deleted.")
            finally:
                self.search_region_visual = None

        # Load the image and detect the Medicare anchor
        detector = MedicareDetector(debug_mode=True)
        image = cv2.imread(self.image_path)

        # Display the target search region
        x1, y1, x2, y2 = self.config["anchors"]["medicare_number"]["region"]
        search_rect = QRectF(x1, y1, x2 - x1, y2 - y1)
        search_region_visual = QGraphicsRectItem(search_rect)
        search_region_visual.setPen(QPen(Qt.blue, 2, Qt.DashLine))  # Dashed blue rectangle
        self.scene.addItem(search_region_visual)
        self.search_region_visual = search_region_visual

        # Find the Medicare anchor
        medicare_anchor = detector.find_medicare_number(image)

        if not medicare_anchor:
            print("Medicare anchor not found.")
            return

        # Display the detected anchor
        x1, y1, x2, y2 = medicare_anchor.bounding_box
        anchor_rect = QRectF(x1, y1, x2 - x1, y2 - y1)
        rect_item = QGraphicsRectItem(anchor_rect)
        rect_item.setPen(QPen(Qt.green, 2))  # Green rectangle to highlight the anchor
        self.scene.addItem(rect_item)
        self.anchor_visual = rect_item  # Store reference to the visual anchor
        print(f"Medicare anchor detected at: {medicare_anchor.bounding_box}")






class ResizableRectItem(QGraphicsRectItem):
    HANDLE_SIZE = 10

    def __init__(self, rect, field_name):
        super().__init__(rect)
        self.field_name = field_name
        self.setPen(QPen(Qt.red, 2))
        self.setBrush(QBrush(Qt.transparent))
        self.setFlags(
            QGraphicsItem.ItemIsMovable |
            QGraphicsItem.ItemIsSelectable |
            QGraphicsItem.ItemSendsGeometryChanges
        )
        
        self.active_handle = None
        self.initial_rect = None
        self.initial_pos = None
        self.dragging = False

        # Label
        self.label = QGraphicsSimpleTextItem(field_name, self)
        self.update_label_position()

        # Create handles
        self.handles = {}
        handle_positions = ["top_left", "top_right", "bottom_left", "bottom_right"]
        for pos in handle_positions:
            handle = self._create_handle()
            self.handles[pos] = handle
        self.update_handles()

    def _create_handle(self):
        handle = QGraphicsEllipseItem(0, 0, self.HANDLE_SIZE, self.HANDLE_SIZE, self)
        handle.setBrush(QBrush(Qt.blue))
        handle.setPen(QPen(Qt.darkBlue))
        handle.setZValue(1)
        return handle

    def update_label_position(self):
        self.label.setPos(0, -20)

    def update_handles(self):
        rect = self.rect()
        offset = self.HANDLE_SIZE / 2
        
        # Position handles at corners
        self.handles["top_left"].setPos(rect.left() - offset, rect.top() - offset)
        self.handles["top_right"].setPos(rect.right() - offset, rect.top() - offset)
        self.handles["bottom_left"].setPos(rect.left() - offset, rect.bottom() - offset)
        self.handles["bottom_right"].setPos(rect.right() - offset, rect.bottom() - offset)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            # Check if we clicked on a handle
            for name, handle in self.handles.items():
                if handle.contains(handle.mapFromParent(pos)):
                    self.active_handle = name
                    self.initial_rect = self.rect()
                    self.initial_pos = pos
                    self.dragging = True
                    event.accept()
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging and self.active_handle:
            pos = event.pos()
            delta = pos - self.initial_pos
            new_rect = QRectF(self.initial_rect)

            # Update rectangle based on handle being dragged
            if self.active_handle == "top_left":
                new_rect.setTopLeft(new_rect.topLeft() + delta)
            elif self.active_handle == "top_right":
                new_rect.setTopRight(new_rect.topRight() + delta)
            elif self.active_handle == "bottom_left":
                new_rect.setBottomLeft(new_rect.bottomLeft() + delta)
            elif self.active_handle == "bottom_right":
                new_rect.setBottomRight(new_rect.bottomRight() + delta)

            # Apply the new rectangle if it's valid
            if new_rect.width() >= self.HANDLE_SIZE and new_rect.height() >= self.HANDLE_SIZE:
                self.prepareGeometryChange()  # Important: notify the scene about upcoming geometry change
                self.setRect(new_rect.normalized())
                self.update_handles()
                self.update()  # Force a visual update
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.active_handle = None
            self.initial_rect = None
            self.initial_pos = None
            self.update()  # Ensure final visual update
        super().mouseReleaseEvent(event)
        print("Rect after release:", self.rect())

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            self.update_handles()
            self.update_label_position()
        return super().itemChange(change, value)

    def paint(self, painter, option, widget=None):
        # Draw the main rectangle
        super().paint(painter, option, widget)
        # Force update of handles and label positions
        self.update_handles()
        self.update_label_position()

    
# Main application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    config_path = "/Users/rileymcnamara/CODE/2024/Data-Entry-App/backend/form_scanning/configs/field_config.json"
    editor = FieldEditor(config_path)
    editor.show()
    sys.exit(app.exec_())
