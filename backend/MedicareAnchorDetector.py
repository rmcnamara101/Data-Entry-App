from dataclasses import dataclass
from typing import Optional, Tuple
import cv2
import re
from TextProcessor import TextProcessor
import numpy as np

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
        # Extract target region using NumPy slicing
        x1, y1, x2, y2 = self.target_region
        target_area = image[y1:y2, x1:x2]

        # Create sliding windows using NumPy's efficient view
        h, w = target_area.shape[:2]
        windows = np.lib.stride_tricks.sliding_window_view(
            target_area, 
            (self.window_size[1], self.window_size[0], target_area.shape[2])
        )[::self.step_size, ::self.step_size]

        # Vectorize processing
        best_match = None
        highest_confidence = 80

        for i in range(windows.shape[0]):
            for j in range(windows.shape[1]):
                window = windows[i, j]
                text, confidence = self.text_processor.extract_text(window)
                
                # Your existing matching logic
                text = re.sub(r'[^0-9/]', '', text)
                if (re.match(self.medicare_pattern, text) and 
                    confidence > highest_confidence):
                    
                    highest_confidence = confidence
                    best_match = MedicareAnchor(
                        text=text,
                        confidence=confidence,
                        bounding_box=(
                            x1 + j * self.step_size,
                            y1 + i * self.step_size,
                            x1 + j * self.step_size + self.window_size[0],
                            y1 + i * self.step_size + self.window_size[1]
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