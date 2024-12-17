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

class MedicareAnchorDetector:
    def __init__(self, target_region, window_size, step_size, text_processor, medicare_pattern, debug_mode: bool = False):
        self.target_region = target_region
        self.window_size = window_size
        self.step_size = step_size
        self.text_processor = text_processor
        self.medicare_pattern = medicare_pattern
        self.debug_mode = debug_mode

    def find_medicare_number(self, image) -> Optional[MedicareAnchor]:
        x1, y1, x2, y2 = self.target_region
        target_area = image[y1:y2, x1:x2]

        if self.debug_mode:
            print(f"Target region: {self.target_region}, shape: {target_area.shape}")

        if target_area.size == 0:
            if self.debug_mode:
                print("Error: Target area is empty. Check target_region coordinates.")
            return None

        try:
            windows = np.lib.stride_tricks.sliding_window_view(
                target_area, 
                (self.window_size[1], self.window_size[0], target_area.shape[2])
            )[::self.step_size, ::self.step_size]
        except ValueError as e:
            if self.debug_mode:
                print(f"Error creating sliding windows: {e}")
            return None

        if self.debug_mode:
            print(f"Windows shape: {windows.shape}")

        best_match = None
        highest_confidence = 80 # Minimum confidence threshold

        for i in range(windows.shape[0]):
            for j in range(windows.shape[1]):
                window = windows[i, j, 0]
                if self.debug_mode:
                    print(f"Window ({i}, {j}) shape: {window.shape}")

                try:
                    window_rgb = cv2.cvtColor(window, cv2.COLOR_BGR2RGB)
                except cv2.error as e:
                    if self.debug_mode:
                        print(f"Color conversion error for window ({i}, {j}): {e}")
                    continue

                window_rgb = window_rgb.astype(np.uint8)
                lang = "eng"
                psm = 6
                text, confidence = self.text_processor.extract_text(window_rgb, lang, psm)

                if self.debug_mode:
                    print(f"Extracted text: '{text}', Confidence: {confidence}")

                cleaned_text = re.sub(r'[^0-9/]', '', text)

                if re.match(self.medicare_pattern, cleaned_text) and confidence > highest_confidence:
                    highest_confidence = confidence
                    best_match = MedicareAnchor(
                        text=cleaned_text,
                        confidence=confidence,
                        bounding_box=(
                            x1 + j * self.step_size,
                            y1 + i * self.step_size,
                            x1 + j * self.step_size + self.window_size[0],
                            y1 + i * self.step_size + self.window_size[1]
                        )
                    )

                    if self.debug_mode:
                        print(f"New best match: {best_match}")

        if self.debug_mode:
            if best_match:
                print(f"Best match: {best_match}")
            else:
                print("No valid Medicare number found.")

        return best_match


class MedicareDetector:
    def __init__(self, debug_mode: bool = True):
        self.debug_mode = debug_mode
        self.text_processor = TextProcessor()
        self.medicare_pattern = r"^\d{10}\s*/\s*\d$"
        
        # Define the exact region where Medicare number should be
        self.target_region = (531, 15, 798, 98)  # (x1, y1, x2, y2)
        
        # Define window parameters
        self.window_size = (140, 20)  # Width and height of scanning window
        self.step_size = 25  # Pixels to move each step

    def find_medicare_number(self, image) -> Optional[MedicareAnchor]:
        detector = MedicareAnchorDetector(
            target_region=self.target_region,
            window_size=self.window_size,
            step_size=self.step_size,
            text_processor=self.text_processor,
            medicare_pattern=self.medicare_pattern,
            debug_mode=self.debug_mode
        )
        return detector.find_medicare_number(image)

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