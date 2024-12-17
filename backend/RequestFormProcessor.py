from typing import Dict, Any
import logging
import cv2
from FormImagePreparer import FormImagePreparer
from FieldExtractor import FieldExtractor
from DataPostProcessor import DataPostProcessor
from Validator import Validator
from database import DatabaseManager
from MedicareAnchorDetector import MedicareDetector
from constants import OCR_CONFIGS
from pyzbar.pyzbar import decode

import numpy as np
from typing import List

class RequestFormProcessor:
    def __init__(self, image_path: str, debug_mode: bool = False) -> None:
        """
        Initializes the RequestFormProcessor with the required modules.

        Args:
            image_path (str): The path to the image file.
            debug_mode (bool): If True, enables debugging features.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)

        self.image_path = image_path
        self.debug_mode = debug_mode

        # Initialize components
        self.form_preparer = FormImagePreparer(image_path, debug_mode)
        self.data_post_processor = DataPostProcessor(debug_mode)
        self.validator = Validator()
        self.db_manager = DatabaseManager()
        self.medicare_anchor_detector = MedicareDetector()

        # Placeholder for processed information
        self.information = {
            "request_number": None,
            "request_date": None,
            "collection_date": None,
            "received_date": None,
            "surname": None,
            "given_name": None,
            "address": None,
            "suburb": None,
            "postcode": None,
            "state": None,
            "date_of_birth": None,
            "mobile_phone_number": None,
            "home_phone_number": None,
            "medicare_number": None,
            "medicare_position": None,
            "provider_number": None,
            "ocr_confidence": None

        }

        self.cropped_image = self.form_preparer.prepare_form()
        self.field_extractor = FieldExtractor(self.cropped_image, debug_mode)

    def process_form(self) -> Dict[str, Any]:
        """
        Processes the request form to extract, clean, validate, and store data.

        Returns:
            Dict[str, Any]: Processed data, validation errors, and field regions.
        """
        try:
    
            form_image = self.cropped_image

            # Step 1: get request number
            self._add_request_number(self.image_path)
            
            # Step 2: extract information from the form 
            # Use anchor-based extraction if Medicare anchor is found, otherwise fallback to manual
            medicare_anchor = self.medicare_anchor_detector.find_medicare_number(form_image)
            if medicare_anchor:
                raw_data = self.field_extractor.extract_fields_using_anchors(medicare_anchor)
                self.logger.debug(f"Medicare anchor found at: {medicare_anchor.bounding_box}")
            else:
                raw_data = self.field_extractor.extract_fields_using_manual_regions()
                self.logger.debug("No Medicare anchor found. Using manual regions for extraction.")

            self.logger.debug(f"Raw extracted data: {raw_data}")

            # Step 3: Clean and post-process extracted data
            self.logger.info("Cleaning and processing extracted data...")
            field_regions = {}  # To store field regions
            for field, (value, confidence, region) in raw_data.items():
                # Clean the extracted value
                cleaned_value = self.data_post_processor.clean_text(field, value)
                self.information[field] = cleaned_value

                # Store the region for this field
                field_regions[field] = region

            # Store the regions in the information dictionary
            self.information["field_regions"] = field_regions
            self.logger.debug(f"Field regions: {field_regions}")

            # Step 4: Validate the cleaned data
            self.logger.info("Validating processed data...")
            validation_errors = self.validator.validate_data(self.information)

            # Step 5: Save the results to the database
            self.logger.info("Saving results to the database...")
            self.db_manager.add_patient_record(
                patient_info=self.information,
                file_path=self.image_path,
                ocr_confidence=self.information.get("ocr_confidence"),
                validation_errors=validation_errors
            )

            return {
                "data": self.information,
                "validation_errors": validation_errors
            }

        except Exception as e:
            self.logger.error(f"An error occurred while processing the form: {e}")
            raise

    def _add_request_number(self, image: np.array) -> List[str]: 
        """
        Function to read barcodes from an image.
        """
        img = cv2.imread(image) 
        
        detectedBarcodes = decode(img) 
        
        if not detectedBarcodes: 
            return None
        decoded_data = []
        for barcode in detectedBarcodes:
            if barcode.data:  # Ensure there's valid data
                decoded_data.append(barcode.data.decode('utf-8'))  # Decode bytes to string

        if detectedBarcodes:
            for i in range(len(detectedBarcodes)):
                if self.validator.is_valid_request_number(detectedBarcodes[i]):
                    self.information["request_number"] = detectedBarcodes[i]
                    break

        else:
            self.information["request_number"] = None