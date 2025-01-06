from dataclasses import dataclass
from typing import Optional, Tuple
import cv2
import re
import numpy as np
from backend.TextProcessor import TextProcessor

@dataclass
class MedicareAnchor:
    text: str
    confidence: float
    bounding_box: Tuple[int, int, int, int]

class MedicareAnchorDetector:
    def __init__(self, target_region, text_processor, medicare_pattern, debug_mode: bool = False):
        self.target_region = target_region
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

        # Convert to RGB for OCR
        try:
            target_area_rgb = cv2.cvtColor(target_area, cv2.COLOR_BGR2RGB)
        except cv2.error as e:
            if self.debug_mode:
                print(f"Color conversion error: {e}")
            return None

        # Extract text and confidence from the entire target area
        text, confidence = self.text_processor.extract_text(target_area_rgb, lang="eng", psm=6)
        if self.debug_mode:
            print(f"Extracted text: '{text}', Confidence: {confidence}")

        # Clean the text to just digits and '/'
        cleaned_text = re.sub(r'[^0-9/]', '', text)

        # If text directly matches the pattern and confidence is good enough, we can return the entire region
        if re.match(self.medicare_pattern, cleaned_text) and confidence > 80:
            if self.debug_mode:
                print("Found Medicare number directly from combined OCR output.")
            return MedicareAnchor(
                text=cleaned_text,
                confidence=confidence,
                bounding_box=(x1, y1, x2, y2)
            )

        # If not found directly, parse the detailed OCR results
        ocr_data = self.text_processor.get_ocr_result()
        if self.debug_mode:
            print("Searching through OCR data for Medicare pattern...")

        # ocr_data keys: 'text', 'conf', 'left', 'top', 'width', 'height'
        texts = ocr_data.get('text', [])
        confs = ocr_data.get('conf', [])
        lefts = ocr_data.get('left', [])
        tops = ocr_data.get('top', [])
        widths = ocr_data.get('width', [])
        heights = ocr_data.get('height', [])

        highest_conf_match = None

        for i, word in enumerate(texts):
            word_str = word.strip()
            if not word_str:
                continue

            # Convert confidence to a float
            word_conf_str = confs[i]
            try:
                word_conf = float(word_conf_str) if word_conf_str != '' else -1
            except ValueError:
                word_conf = -1

            # Clean this word
            cleaned_word = re.sub(r'[^0-9/]', '', word_str)

            # Check if this word matches the Medicare pattern
            if re.match(self.medicare_pattern, cleaned_word) and word_conf > 80:
                # Found a good match, now we make sure bounding box is tight.
                # If cleaned_word is exactly the recognized word after cleaning, just use the entire box.
                # If not, find substring indices in the original word_str.

                left = lefts[i]
                top = tops[i]
                width = widths[i]
                height = heights[i]

                # Default bounding box from OCR word-level data
                sub_left = left
                sub_width = width

                # If the recognized word contains the Medicare number plus extra chars,
                # find the exact substring and scale.
                # For example, if word_str = "ABC1234567890/1XYZ" and cleaned_word = "1234567890/1",
                # find start and end indices in the original word_str.
                
                # The cleaned_word might have lost non-digit chars, so we attempt to find the cleaned_word
                # inside a stripped-down version of word_str that also only has digits and '/'.
                original_cleaned = re.sub(r'[^0-9/]', '', word_str)
                
                # Find substring indices
                start_idx = original_cleaned.find(cleaned_word)
                if start_idx != -1 and len(original_cleaned) >= len(cleaned_word):
                    end_idx = start_idx + len(cleaned_word)
                    # Approximate character width
                    char_width = width / max(len(original_cleaned), 1)
                    sub_left = left + int(start_idx * char_width)
                    sub_width = int((end_idx - start_idx) * char_width)

                # Create a MedicareAnchor with a tighter bounding box
                anchor = MedicareAnchor(
                    text=cleaned_word,
                    confidence=word_conf,
                    bounding_box=(x1 + sub_left, y1 + top, x1 + sub_left + sub_width, y1 + top + height)
                )

                # Keep track of the highest confidence match if multiple words match
                if not highest_conf_match or word_conf > highest_conf_match.confidence:
                    highest_conf_match = anchor

        if highest_conf_match:
            if self.debug_mode:
                print(f"Found Medicare number in OCR data: {highest_conf_match}")
            return highest_conf_match

        if self.debug_mode:
            print("No valid Medicare number found.")

        return None


class MedicareDetector:
    def __init__(self, debug_mode: bool = True):
        self.debug_mode = debug_mode
        self.text_processor = TextProcessor()
        self.medicare_pattern = r"^\d{10}\s*/\s*\d$"
        
        # Define the exact region where Medicare number should be
        self.target_region = (531, 15, 798, 98)  # (x1, y1, x2, y2)

    def find_medicare_number(self, image) -> Optional[MedicareAnchor]:
        detector = MedicareAnchorDetector(
            target_region=self.target_region,
            text_processor=self.text_processor,
            medicare_pattern=self.medicare_pattern,
            debug_mode=self.debug_mode
        )
        return detector.find_medicare_number(image)

    def visualize_result(self, image, medicare_anchor: Optional[MedicareAnchor]):
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
