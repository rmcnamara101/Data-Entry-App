# FieldExtractor.py
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from TextProcessor import TextProcessor
from utils import MEDICARE_RELATIVE_OFFSETS, FIELD_REGIONS
from constants import OCR_CONFIGS


class FieldExtractor:
    def __init__(self, form_image: np.ndarray, debug_mode: bool = False) -> None:
        """
        Initializes the FieldExtractor with the form image and text processor.

        Args:
            form_image (np.ndarray): The preprocessed form image.
            debug_mode (bool): Enable debug mode for visualizations.
        """
        self.form_image = form_image
        self.debug_mode = debug_mode
        self.text_processor = TextProcessor()

    def extract_fields_using_anchor(self, medicare_anchor: Any) -> Dict[str, Tuple[Optional[str], float, Tuple[int, int, int, int]]]:
        """
        Extracts fields relative to a Medicare anchor.

        Returns:
            Dict[str, Tuple[Optional[str], float, Tuple[int, int, int, int]]]: Field value, confidence, and region (bounding box).
        """
        extracted_fields = {}
        anchor_x, anchor_y, _, _ = medicare_anchor.bounding_box

        for field_name, (rel_x, rel_y, field_width, field_height) in MEDICARE_RELATIVE_OFFSETS.items():
            x1 = anchor_x + rel_x
            y1 = anchor_y - rel_y
            x2 = x1 + field_width
            y2 = y1 + field_height
            cropped_region = self.form_image[y1:y2, x1:x2]

            lang ='eng'
            psm = OCR_CONFIGS.get(field_name, 3)
            field_value, confidence = self.text_processor.extract_text(cropped_region, lang, psm)
            # Add the bounding box to the result
            extracted_fields[field_name] = (field_value, confidence, (x1, y1, x2, y2))

        return extracted_fields


    def extract_fields_using_manual_regions(self) -> Dict[str, Tuple[Optional[str], float]]:
        """
        Extracts fields using predefined manual regions.

        Returns:
            Dict[str, Tuple[Optional[str], float]]: Extracted field values and their confidence scores.
        """
        extracted_fields = {}

        for field_name, field_region in FIELD_REGIONS.items():
            # Access field_region attributes instead of subscripting
            x1, y1, x2, y2 = field_region.coordinates  # Assuming 'coordinates' is an attribute
            cropped_region = self.form_image[y1:y2, x1:x2]

            lang ='eng'
            psm = OCR_CONFIGS.get(field_name, 3)
            field_value, confidence = self.text_processor.extract_text(cropped_region, lang, psm)

            extracted_fields[field_name] = (field_value, confidence, (x1, y1, x2, y2))

        return extracted_fields

