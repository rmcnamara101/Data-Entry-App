from dataclasses import dataclass
from typing import Optional, Tuple
import cv2
import re
from TextProcessor import TextProcessor

@dataclass
class MedicareAnchor:
    text: str
    confidence: float
    bounding_box: Tuple[int, int, int, int]

class MedicareDetector:
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.text_processor = TextProcessor()
        self.medicare_pattern = r"^\d{10}/\d$"
        
        # Define the exact region where Medicare number should be
        self.target_region = (531, 15, 798, 98)  # (x1, y1, x2, y2)
        
        # Define window parameters
        self.window_size = (120, 25)  # Width and height of scanning window
        self.step_size = 10  # Pixels to move each step

    def find_medicare_number(self, image) -> Optional[MedicareAnchor]:
        """
        Find Medicare number within the specified region of the preprocessed image.
        """
        # Extract the target region
        x1, y1, x2, y2 = self.target_region
        target_area = image[y1:y2, x1:x2]
        
        if target_area is None or target_area.size == 0:
            print("Error: Invalid target region")
            return None
        
        best_match = None
        highest_confidence = 80  # Minimum confidence threshold
        
        # Sliding window within the target area
        area_height, area_width = target_area.shape[:2]
        
        for y in range(0, area_height - self.window_size[1], self.step_size):
            for x in range(0, area_width - self.window_size[0], self.step_size):
                # Extract window
                window = target_area[y:y + self.window_size[1], 
                                   x:x + self.window_size[0]]
                
                # Perform OCR
                text, confidence = self.text_processor.extract_text(window)
                
                # Clean the text (remove any non-digit/slash characters)
                text = re.sub(r'[^0-9/]', '', text)
                
                if self.debug_mode:
                    print(f"Window at ({x},{y}): '{text}' [Confidence: {confidence}]")
                
                # Check if text matches Medicare pattern
                if (re.match(self.medicare_pattern, text) and 
                    confidence > highest_confidence):
                    
                    highest_confidence = confidence
                    # Calculate coordinates in original image space
                    best_match = MedicareAnchor(
                        text=text,
                        confidence=confidence,
                        bounding_box=(
                            x1 + x,                    # Global x1
                            y1 + y,                    # Global y1
                            x1 + x + self.window_size[0],  # Global x2
                            y1 + y + self.window_size[1]   # Global y2
                        )
                    )
        
        return best_match

    def visualize_result(self, image, medicare_anchor: Optional[MedicareAnchor]):
        """
        Visualize the detection result.
        """
        vis_image = image.copy()
        
        # Draw the target region
        cv2.rectangle(vis_image, 
                     (self.target_region[0], self.target_region[1]),
                     (self.target_region[2], self.target_region[3]),
                     (0, 255, 255), 1)  # Yellow for target region
        
        if medicare_anchor:
            # Draw the detected medicare number region
            x1, y1, x2, y2 = medicare_anchor.bounding_box
            cv2.rectangle(vis_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Add text annotation
            text = f"Medicare: {medicare_anchor.text} ({medicare_anchor.confidence:.1f}%)"
            cv2.putText(vis_image, text, (x1, y1-5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return vis_image