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
    Class to detect a Medicare number anchor in a given image.
    More robust approach with pre-/post-processing to handle
    whitespace, misread slash, extra spurious digits, etc.
    """
    def __init__(
        self,
        target_region: Tuple[int, int, int, int],
        text_processor: TextProcessor,
        medicare_pattern: str,
        debug_mode: bool = False
    ):
        """
        Args:
            target_region (Tuple[int, int, int, int]): The (x1, y1, x2, y2) coords
                in the image where the Medicare number is expected.
            text_processor (TextProcessor): The text processor (e.g. Tesseract) object.
            medicare_pattern (str): Regex pattern for validating Medicare numbers.
            debug_mode (bool): Debug logging if True.
        """
        self.target_region = target_region
        self.text_processor = text_processor
        self.medicare_pattern = medicare_pattern
        self.debug_mode = debug_mode

        # Threshold params (you can tweak or add new ones if needed)
        self.threshold_value = 150
        self.threshold = True

    def find_medicare_number(self, image) -> Optional[MedicareAnchor]:
        """
        Main method to locate Medicare number in the specified target region.
        Applies thresholding, extracts text, and tries to parse a valid
        Medicare number via regex. Returns the best match if found.
        """
        x1, y1, x2, y2 = self.target_region

        # 1. Create a masked image to limit Tesseract’s attention to target region
        masked_image = self.create_masked_image(image, (x1, y1, x2, y2))
        gray_masked = cv2.cvtColor(masked_image, cv2.COLOR_BGR2GRAY)

        # 2. Apply thresholding (OTSU or fixed)
        if self.threshold:
            # OTSU automatically picks best threshold ignoring self.threshold_value
            _, final_masked = cv2.threshold(
                gray_masked, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
        else:
            # Fixed threshold at self.threshold_value
            _, final_masked = cv2.threshold(
                gray_masked, self.threshold_value, 255, cv2.THRESH_BINARY
            )

        # 3. Extract text from the masked region
        text, confidence = self.text_processor.extract_text(
            final_masked,
            lang="eng",
            psm=7
        )
        if self.debug_mode:
            print(f"[DEBUG] Extracted raw text: '{text}' (conf={confidence:.2f})")

        # 4. Retrieve detailed OCR data (words & bounding boxes)
        ocr_data = self.text_processor.get_ocr_result()
        if self.debug_mode:
            print("[DEBUG] Searching through OCR data for potential Medicare matches...")

        texts = ocr_data.get('text', [])
        confs = ocr_data.get('conf', [])
        lefts = ocr_data.get('left', [])
        tops = ocr_data.get('top', [])
        widths = ocr_data.get('width', [])
        heights = ocr_data.get('height', [])

        highest_conf_match = None

        # 5. Iterate all recognized words
        for i, word in enumerate(texts):
            # Basic sanity checks
            if not word or not isinstance(word, str):
                continue

            # Convert confidence to float or set to -1 if invalid
            conf_val = confs[i]
            word_conf = self._parse_confidence(conf_val)
            if word_conf < 0:
                # Ignore negative or invalid confidence entries
                continue

            original_word = word.strip()

            # --- Step A: pre-clean the recognized chunk ---
            # Remove or fix known noise, e.g. stray punctuation except digits, slash, or spaces
            # (We keep slash so we can do slash-checks. We keep digits. We allow spaces, then trim later.)
            # Because Tesseract can inject artifacts, we can remove e.g. alpha letters or random punctuation:
            pre_clean = re.sub(r"[^0-9/\s]", "", original_word)

            # Trim excessive whitespace
            pre_clean = pre_clean.strip()

            # --- Step B: handle potential slash misreads (like '7') if needed ---
            corrected_candidates = self._generate_slash_candidates(pre_clean)

            # --- Step C: try each candidate to see if it matches the pattern ---
            matched_text = None
            for candidate in corrected_candidates:
                # Remove intermediate spaces before final pattern match
                candidate_no_space = re.sub(r"\s+", "", candidate)
                if re.match(self.medicare_pattern, candidate_no_space):
                    matched_text = candidate_no_space
                    break

            if not matched_text:
                # No valid match among slash-corrected candidates
                continue

            # If matched, compute bounding box for the matched substring
            # We'll base it on the final matched_text (which has no spaces).
            # The bounding box is trickier if we changed chars (7->/).
            # For simplicity, we’ll treat the bounding box as the entire word recognized by Tesseract.
            # If you need extremely precise bounding boxes for the substring, see below.
            left = lefts[i]
            top = tops[i]
            width = widths[i]
            height = heights[i]

            anchor = MedicareAnchor(
                text=matched_text,
                confidence=word_conf,
                bounding_box=(left, top, left + width, top + height)
            )

            # Update highest confidence match
            if not highest_conf_match or word_conf > highest_conf_match.confidence:
                highest_conf_match = anchor

        if highest_conf_match and self.debug_mode:
            print(f"[DEBUG] Found Medicare anchor: {highest_conf_match}")

        if not highest_conf_match and self.debug_mode:
            print("[DEBUG] No valid Medicare number found in OCR data.")

        return highest_conf_match

    def create_masked_image(self, image, region: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Creates a white mask over the entire image except for the specified region.

        Args:
            region (Tuple[int, int, int, int]): (x1, y1, x2, y2) coordinates.
        Returns:
            np.ndarray: Masked image with only the region visible.
        """
        x1, y1, x2, y2 = region
        
        # Create a white mask
        mask = np.full_like(image, 255, dtype=np.uint8)
        
        # Copy the region of interest
        mask[y1:y2, x1:x2] = image[y1:y2, x1:x2]
        return mask

    @staticmethod
    def _parse_confidence(conf_val) -> float:
        """
        Converts Tesseract 'conf' to float. If invalid or -1, returns -1.
        """
        if isinstance(conf_val, int):
            return float(conf_val) if conf_val >= 0 else -1
        elif isinstance(conf_val, str) and conf_val.isdigit():
            return float(conf_val)
        return -1

    def _generate_slash_candidates(self, text: str) -> list:
        """
        Given a recognized text chunk (digits, slash, spaces),
        generate candidate variations for slash vs '7' or other near-misreads
        and return them all. The first candidate is the original text itself.

        Example:
            Input: '1234567890 7 1'
            Output: ['1234567890 7 1', '1234567890 / 1']
            (plus potentially other small variations if you want to check '1' vs 'I' etc.)

        Customize or expand with additional heuristics as you see fit.
        """
        candidates = [text]  # start with the original text

        # If we suspect '7' might be slash, create an alt candidate
        if "7" in text:
            alt = text.replace("7", "/")
            if alt != text:
                candidates.append(alt)

        # Add more specialized logic if needed. For instance:
        #   - Sometimes slash might come out as '1' or 'l' (the letter L)
        #   - ...
        # For now we’ll keep it simple.

        return candidates


class MedicareDetector:
    """
    A higher-level class that uses MedicareAnchorDetector to find Medicare anchors
    and optionally visualize the results.
    """
    def __init__(self, debug_mode: bool = True):
        self.debug_mode = debug_mode
        self.text_processor = TextProcessor()

        # More tolerant pattern:
        #  - Exactly 10 digits, optional spaces or slash, then final digit
        #  - The slash can have optional whitespace on either side
        #  e.g. '1234567890/1' or '1234567890 / 1'
        self.medicare_pattern = r"^\d{10}\s*/\s*\d$"

        # Define the region where the Medicare number is expected
        # Adjust as needed for your layout
        self.target_region = (531, 0, 804, 80)  # (x1, y1, x2, y2)

    def find_medicare_number(self, image) -> Optional[MedicareAnchor]:
        """
        Orchestrates detection by instantiating MedicareAnchorDetector
        and calling its find_medicare_number() method.
        """
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
            (0, 255, 255), 2
        )
        
        if medicare_anchor:
            # Draw the detected bounding box in green
            x1, y1, x2, y2 = medicare_anchor.bounding_box
            cv2.rectangle(vis_image, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Overlay text annotation
            text = f"Medicare: {medicare_anchor.text} ({medicare_anchor.confidence:.1f}%)"
            cv2.putText(
                vis_image, text, 
                (x1, y1 - 10), 
                cv2.FONT_HERSHEY_SIMPLEX, 
                0.5, 
                (0, 255, 0), 
                2
            )
        
        return vis_image
