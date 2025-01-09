# FieldExtractor.py
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from backend.form_scanning.TextProcessor import TextProcessor
from backend.utils import MEDICARE_RELATIVE_OFFSETS, FIELD_REGIONS
from backend.constants import OCR_CONFIGS
import cv2

class FieldExtractor:
    def __init__(self, form_image: np.ndarray, config: dict, debug_mode: bool = False) -> None:
        """
        Initializes the FieldExtractor with the form image and configuration.

        Args:
            form_image (np.ndarray): The preprocessed form image.
            config (dict): Configuration for anchors and field offsets.
            debug_mode (bool): Enable debug mode for visualizations.
        """
        self.form_image = form_image
        self.config = config
        self.debug_mode = debug_mode
        self.text_processor = TextProcessor()

    def extract_fields_using_anchor(self, medicare_anchor: Any) -> Dict[str, Tuple[Optional[str], float, Tuple[int, int, int, int]]]:
        """
        Extracts fields relative to a Medicare anchor using configuration.

        Returns:
            Dict[str, Tuple[Optional[str], float, Tuple[int, int, int, int]]]: Field value, confidence, and region (bounding box).
        """
        extracted_fields = {}
        anchor_x, anchor_y, _, _ = medicare_anchor.bounding_box

        for field_name, offset in self.config["relative_offsets"].items():
            rel_x, rel_y, field_width, field_height = offset
            x1 = anchor_x + rel_x
            y1 = anchor_y - rel_y
            x2 = x1 + field_width
            y2 = y1 + field_height

            cropped_region = self.form_image[y1:y2, x1:x2]
            ocr_config = self.config["ocr_configs"].get(field_name, self.config["ocr_configs"]["default"])
            field_value, confidence = self.text_processor.extract_text(
                cropped_region,
                lang=ocr_config["lang"],
                psm=ocr_config["psm"]
            )
            extracted_fields[field_name] = (field_value, confidence, (x1, y1, x2, y2))

        return extracted_fields

