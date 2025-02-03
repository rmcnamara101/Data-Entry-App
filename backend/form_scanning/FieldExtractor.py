from typing import Dict, Tuple, Optional, Any
import numpy as np
import cv2
from backend.form_scanning.TextProcessor import TextProcessor
from backend.constants import OCR_CONFIGS
from backend.form_scanning.RequestFormProcessor import FieldData

class FieldExtractor:
    def __init__(self, form_image: np.ndarray, config: dict, debug_mode: bool = False) -> None:
        """
        Initializes the FieldExtractor with the form image and configuration.
        
        Args:
            form_image (np.ndarray): The preprocessed form image.
            config (dict): Configuration for field regions.
            debug_mode (bool): Enable debug mode for visualizations.
        """
        self.form_image = form_image
        self.config = config
        self.debug_mode = debug_mode
        self.text_processor = TextProcessor()
        extractor = FieldExtractor(self.form_image, self.config, self.debug_mode)

    def extract_field_info(self, fields_dict: Dict[str, Any]) -> Dict[str, Any]:
        extracted_fields = {}
        for field_name, extracted_field in fields_dict.items():
            # Extract bounding box from the ExtractedField
            bounding_box = extracted_field.bounding_box
            x1, y1, x2, y2 = bounding_box
            masked_image = self._create_masked_image((x1, y1, x2, y2))

            # Get OCR configuration for the field
            ocr_config = self.config["ocr_configs"].get(field_name, self.config["ocr_configs"]["default"])
            field_value, confidence = self.text_processor.extract_text(
                masked_image,
                lang=ocr_config["lang"],
                psm=ocr_config["psm"]
            )

            # Store FieldData instance
            extracted_fields[field_name] = FieldData(
                value=field_value.strip() if field_value else None,
                confidence=confidence,
                bounding_box=bounding_box
            )
        return extracted_fields

    def _create_masked_image(self, region: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Creates a white mask over the entire image except for the specified region.

        Args:
            region (Tuple[int, int, int, int]): Region coordinates (x1, y1, x2, y2).

        Returns:
            np.ndarray: Masked image with only the region visible.
        """
        x1, y1, x2, y2 = region
        mask = np.full_like(self.form_image, 255, dtype=np.uint8)
        mask[y1:y2, x1:x2] = self.form_image[y1:y2, x1:x2]
        return mask
