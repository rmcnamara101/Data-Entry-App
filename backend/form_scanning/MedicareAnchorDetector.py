from dataclasses import dataclass
from typing import Optional, Tuple
import cv2
import re
import numpy as np
from backend.form_scanning.TextProcessor import TextProcessor

@dataclass
class MedicareAnchor:
    """
    Data class to store Medicare number anchor information.
    """
    text: str
    confidence: float
    bounding_box: Tuple[int, int, int, int]

class MedicareAnchorDetector:
    """
    Class to detect Medicare number anchor in a given image.
    """
    def __init__(self, target_region, text_processor, medicare_pattern, debug_mode: bool = False):
        self.target_region = target_region
        self.text_processor = text_processor
        self.medicare_pattern = medicare_pattern
        self.debug_mode = debug_mode

        self.threshold_value = 150
        self.threshold = True

    def find_medicare_number(self, image) -> Optional[MedicareAnchor]:
        """
        Finds a Medicare number anchor within the given image.
        Returns a MedicareAnchor if found, otherwise None.
        """
        x1, y1, x2, y2 = self.target_region

        # 1. Create a masked image so the rest of the image is white
        masked_image = self.create_masked_image(image, (x1, y1, x2, y2))
        gray_masked = cv2.cvtColor(masked_image, cv2.COLOR_BGR2GRAY)

        if self.threshold:
            # OTSU automatically determines best threshold,
            # ignoring self.threshold_value
            _, final_masked = cv2.threshold(
                gray_masked, 0, 255, 
                cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
        else:
            # Fixed threshold at self.threshold_value
            final_masked = gray_masked.copy()
        
        # 2. Extract text and confidence from the masked image
        #    - Adjust psm/config as needed. For example, pass a dict if you want thresholding:
        #      config_dict = {
        #          "tesseract_config": "-c tessedit_char_whitelist=0123456789/",
        #          "threshold_type": "otsu"
        #      }
        #      text, confidence = self.text_processor.extract_text(masked_image, lang="eng", psm=7, config=config_dict)
        text, confidence = self.text_processor.extract_text(
            final_masked, 
            lang="eng", 
            psm=7
        )
        if self.debug_mode:
            print(f"Extracted text: '{text}', Confidence: {confidence}")

        # 3. Parse the detailed OCR results (words + bounding boxes)
        ocr_data = self.text_processor.get_ocr_result()
        if self.debug_mode:
            print("Searching through OCR data for Medicare pattern...")

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

            # --- Updated confidence parsing to handle integer or string ---
            conf_val = confs[i]
            if isinstance(conf_val, int):
                word_conf = float(conf_val) if conf_val >= 0 else -1
            elif isinstance(conf_val, str) and conf_val.isdigit():
                word_conf = float(conf_val)
            else:
                # If empty string or something invalid
                word_conf = -1

            # Clean this word of anything not 0-9 or slash
            cleaned_word = re.sub(r'[^0-9/]', '', word_str)

            # Check if it matches the Medicare pattern
            if re.match(self.medicare_pattern, cleaned_word):
                left = lefts[i]
                top = tops[i]
                width = widths[i]
                height = heights[i]

                # In the recognized text, find the substring indices
                original_cleaned = re.sub(r'[^0-9/]', '', word_str)
                start_idx = original_cleaned.find(cleaned_word)
                
                if start_idx != -1 and len(original_cleaned) >= len(cleaned_word):
                    end_idx = start_idx + len(cleaned_word)
                    char_width = width / max(len(original_cleaned), 1)
                    
                    # Adjust bounding box for just the matched substring
                    sub_left = left + int(start_idx * char_width)
                    sub_width = int((end_idx - start_idx) * char_width)

                    # Create the anchor with bounding box in full-image coords
                    anchor = MedicareAnchor(
                        text=cleaned_word,
                        confidence=word_conf,
                        bounding_box=(
                            sub_left,
                            top,
                            sub_left + sub_width,
                            top + height
                        )
                    )

                    # Track highest-confidence match if multiple appear
                    if not highest_conf_match or word_conf > highest_conf_match.confidence:
                        highest_conf_match = anchor

        if highest_conf_match:
            if self.debug_mode:
                print(f"Found Medicare number in OCR data: {highest_conf_match}")
            return highest_conf_match

        if self.debug_mode:
            print("No valid Medicare number found.")
        return None
    
    def create_masked_image(self, image, region: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Creates a white mask over the entire image except for the specified region.
        
        Args:
            region (Tuple[int, int, int, int]): Region coordinates (x1, y1, x2, y2).
        Returns:
            np.ndarray: Masked image with only the region visible.
        """
        x1, y1, x2, y2 = region
        
        # Create a white mask the same size as the original image
        mask = np.full_like(image, 255, dtype=np.uint8)
        
        # Copy the region of interest
        mask[y1:y2, x1:x2] = image[y1:y2, x1:x2]
        
        return mask


class MedicareDetector:
    """
    A higher-level class that uses MedicareAnchorDetector to find Medicare anchors,
    then optionally visualize the results.
    """
    def __init__(self, debug_mode: bool = True):
        self.debug_mode = debug_mode
        self.text_processor = TextProcessor()
        self.medicare_pattern = r"^\d{10}\s*/\s*\d$"
        
        # Define the region where the Medicare number is expected
        self.target_region = (531, 0, 804, 80)  # (x1, y1, x2, y2)

    def find_medicare_number(self, image) -> Optional[MedicareAnchor]:
        detector = MedicareAnchorDetector(
            target_region=self.target_region,
            text_processor=self.text_processor,
            medicare_pattern=self.medicare_pattern,
            debug_mode=self.debug_mode
        )
        return detector.find_medicare_number(image)

    def visualize_result(self, image, medicare_anchor: Optional[MedicareAnchor]):
        """
        Draws the target region and the detected Medicare anchor on a copy of the image.
        Returns the annotated image.
        """
        vis_image = image.copy()
        
        # Draw the target region in yellow
        cv2.rectangle(
            vis_image, 
            (self.target_region[0], self.target_region[1]),
            (self.target_region[2], self.target_region[3]),
            (0, 255, 255), 1
        )
        
        if medicare_anchor:
            # Draw the detected bounding box in green
            x1, y1, x2, y2 = medicare_anchor.bounding_box
            cv2.rectangle(vis_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Overlay text annotation
            text = f"Medicare: {medicare_anchor.text} ({medicare_anchor.confidence:.1f}%)"
            cv2.putText(
                vis_image, text, 
                (x1, y1 - 5), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.5, 
                (0, 255, 0), 
                2
            )
        
        return vis_image
