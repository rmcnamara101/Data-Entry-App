from typing import Dict, Any
from dataclasses import dataclass, fields
import logging
import cv2
from datetime import datetime
from backend.form_scanning.FormImagePreparer import FormImagePreparer
from backend.form_scanning.FieldExtractor import FieldExtractor
from backend.form_scanning.DataPostProcessor import DataPostProcessor
from backend.form_scanning.Validator import Validator
from backend.database.database import DatabaseManager
from backend.form_scanning.MedicareAnchorDetector import MedicareDetector
from backend.constants import OCR_CONFIGS
from pyzbar.pyzbar import decode

import numpy as np
from typing import List, Optional, Tuple
import re
import os
import json

@dataclass
class FieldData:
    value: Optional[str]
    confidence: Optional[int]
    bounding_box: Optional[Tuple[int, int, int, int]]

@dataclass
class ProcessedForm:
    image_path: Optional[str] = None
    request_number: Optional[FieldData] = None
    request_date: Optional[FieldData] = None
    # collection_date removed as requested
    received_date: Optional[FieldData] = None
    surname: Optional[FieldData] = None
    given_name: Optional[FieldData] = None
    address: Optional[FieldData] = None
    suburb: Optional[FieldData] = None
    postcode: Optional[FieldData] = None
    state: Optional[FieldData] = None
    date_of_birth: Optional[FieldData] = None
    mobile_phone: Optional[FieldData] = None
    home_phone: Optional[FieldData] = None
    medicare_number: Optional[FieldData] = None
    medicare_position: Optional[FieldData] = None
    provider_number: Optional[FieldData] = None
    sex: Optional[FieldData] = None  # Added sex field as requested

class RequestFormProcessor:
    def __init__(self, image_path: str, config_path: str, debug_mode: bool = False) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)

        self.config = load_field_config(config_path)
        print(self.config)
        self.image_path = image_path
        self.debug_mode = debug_mode

        # Initialize components
        self.form_preparer = FormImagePreparer(image_path, debug_mode)
        self.data_post_processor = DataPostProcessor(debug_mode)
        self.validator = Validator()
        self.medicare_anchor_detector = MedicareDetector(debug_mode=self.debug_mode)

        # Each field stored as (value, confidence, bounding_box) after cleaning
        self.information = {
            "request_number": None,
            "request_date": None,
            # "collection_date": None,  # Removed as requested
            "received_date": None,
            "surname": None,
            "given_names": None,
            "sex": None,  # Added sex field
            "address": None,
            "suburb": None,
            "postcode": None,
            "state": None,
            "date_of_birth": None,
            "mobile_phone": None,
            "home_phone": None,
            "medicare_number": None,
            "medicare_position": None,
            "provider_number": None,
            "ocr_confidence": None,
            "phone_number": None,  # If combined phone field exists
            "doctor_information": None  # If we need this for provider_number extraction
        }

        self.cropped_image = self.form_preparer.prepare_form()
        self.field_extractor = FieldExtractor(self.cropped_image, self.config, debug_mode)

    def process_form(self) -> Dict[str, Any]:
        """
        Processes the request form to extract, clean, validate, and store data.
        Returns a dictionary with processed data and validation errors,
        as well as a ProcessedForm object.
        """
        try:
            form_image = self.cropped_image

            # Detect Medicare anchor
            medicare_anchor = self.medicare_anchor_detector.find_medicare_number(form_image)

            if not medicare_anchor:
                raise ValueError("No valid Medicare anchor detected. Ensure the form alignment and quality.")

            # Extract fields based on anchor
            raw_data = self.field_extractor.extract_fields_using_anchor(medicare_anchor)
            raw_data["medicare_number"] = (medicare_anchor.text, medicare_anchor.confidence, medicare_anchor.bounding_box)

            for field, (value, confidence, region) in raw_data.items():
                cleaned_value = self.data_post_processor.clean_text(field, value)
                self.information[field] = (cleaned_value, confidence, region)

            self._post_process_derived_fields()

            now_str = datetime.now().strftime('%d/%m/%Y')
            self.information["received_date"] = (now_str, 100, None)  # Confidence 100, no bbox since generated

            validation_errors = self.validator.validate_data(self.information)

            processed_form = self._create_processed_form()

            return {
                "data": processed_form,
                "validation_errors": validation_errors
            }

        except Exception as e:
            print(f"An error occurred while processing the form: {e}")
            self.logger.error(f"An error occurred while processing the form: {e}")
            raise



    def _post_process_derived_fields(self):
        """
        Perform additional transformations using DataPostProcessor methods.
        """
        # --- Address Splitting ---
        if self.information.get("address") and self.information["address"] and self.information["address"][0]:
            full_address = self.information["address"][0]
            address_components = self.data_post_processor.split_address(full_address)

            addr_confidence = self.information["address"][1]
            addr_bbox = self.information["address"][2]

            if address_components["address"]:
                self.information["address"] = (address_components["address"], addr_confidence, addr_bbox)
            if address_components["suburb"]:
                self.information["suburb"] = (address_components["suburb"], addr_confidence, addr_bbox)
            if address_components["postcode"]:
                self.information["postcode"] = (address_components["postcode"], addr_confidence, addr_bbox)
            if address_components["state"]:
                self.information["state"] = (address_components["state"], addr_confidence, addr_bbox)
    
        # --- Medicare Number and Position ---
        if self.information.get("medicare_number") and self.information["medicare_number"] and self.information["medicare_number"][0]:
            medicare_full = self.information["medicare_number"][0]
            med_confidence = self.information["medicare_number"][1]
            med_bbox = self.information["medicare_number"][2]

            parts = medicare_full.split('/')
            if len(parts) == 2 and len(parts[0]) == 10 and len(parts[1]) == 1:
                med_number = parts[0]
                med_position = parts[1]
                self.information["medicare_number"] = (med_number, med_confidence, med_bbox)
                self.information["medicare_position"] = (med_position, med_confidence, med_bbox)

        # --- Provider Number ---
        if ((not self.information.get("provider_number") or not self.information["provider_number"] or not self.information["provider_number"][0])
            and self.information.get("doctor_information") and self.information["doctor_information"] and self.information["doctor_information"][0]):
            # Derive provider_number from doctor_information
            doc_info_val = self.information["doctor_information"][0]
            doc_conf = self.information["doctor_information"][1]
            doc_bbox = self.information["doctor_information"][2]

            provider_extracted = doc_info_val[-8:].upper()
            provider_extracted = re.sub(r'[^A-Z0-9]', '', provider_extracted)
            self.information["provider_number"] = (provider_extracted, doc_conf, doc_bbox)
        else:
            # Provider number exists, clean it according to the rules
            if self.information.get("provider_number") and self.information["provider_number"] and self.information["provider_number"][0]:
                prov_val = self.information["provider_number"][0]
                prov_conf = self.information["provider_number"][1]
                prov_bbox = self.information["provider_number"][2]

                provider_extracted = prov_val[-8:].upper()
                provider_extracted = re.sub(r'[^A-Z0-9]', '', provider_extracted)
                self.information["provider_number"] = (provider_extracted, prov_conf, prov_bbox)

        # --- Phone Numbers ---
        home_data = self.information.get("home_phone")
        mobile_data = self.information.get("mobile_phone")
        phone_data = self.information.get("phone_number")

        if (not home_data or not home_data[0]) and (not mobile_data or not mobile_data[0]) and phone_data and phone_data[0]:
            phone_str = phone_data[0]
            ph_confidence = phone_data[1]
            ph_bbox = phone_data[2]

            # Normalize spaces
            phone_str_no_spaces = re.sub(r'\s+', '', phone_str)  
            phone_numbers = self.data_post_processor.process_phone_numbers(phone_str_no_spaces)

            if phone_numbers["home_phone"] or phone_numbers["mobile_phone"]:
                # Labeled numbers found
                if phone_numbers["home_phone"]:
                    self.information["home_phone"] = (phone_numbers["home_phone"], ph_confidence, ph_bbox)
                if phone_numbers["mobile_phone"]:
                    self.information["mobile_phone"] = (phone_numbers["mobile_phone"], ph_confidence, ph_bbox)
            else:
                # No labeled matches found, try unlabeled approach
                single_numbers = re.findall(r'\d+', phone_str_no_spaces)
                if len(single_numbers) == 1:
                    # Single unlabeled number
                    number = single_numbers[0]
                    if number.startswith("04"):
                        self.information["mobile_phone"] = (number, ph_confidence, ph_bbox)
                    else:
                        self.information["home_phone"] = (number, ph_confidence, ph_bbox)
                elif len(single_numbers) == 2:
                    # Two unlabeled numbers
                    self.information["mobile_phone"] = (single_numbers[0], ph_confidence, ph_bbox)
                    self.information["home_phone"] = (single_numbers[1], ph_confidence, ph_bbox)
                # If more than 2 or none, no further action.

        # The received_date is overwritten in process_form to current time, so no need to parse it here.

    def _field_to_fielddata(self, field_name: str) -> Optional[FieldData]:
        """
        Converts a field from self.information to FieldData.
        """
        data = self.information[field_name]
        if not data or len(data) < 3:
            return None
        value, confidence, bbox = data
        if value is None:
            return None
        return FieldData(value=value, confidence=confidence, bounding_box=bbox)

    def _create_processed_form(self) -> ProcessedForm:
        """
        Create a ProcessedForm dataclass instance from self.information.
        """
        return ProcessedForm(
            image_path=self.image_path,
            request_number=self._field_to_fielddata("request_number"),
            request_date=self._field_to_fielddata("request_date"),
            received_date=self._field_to_fielddata("received_date"),
            surname=self._field_to_fielddata("surname"),
            given_name=self._field_to_fielddata("given_names"),
            address=self._field_to_fielddata("address"),
            suburb=self._field_to_fielddata("suburb"),
            postcode=self._field_to_fielddata("postcode"),
            state=self._field_to_fielddata("state"),
            date_of_birth=self._field_to_fielddata("date_of_birth"),
            mobile_phone=self._field_to_fielddata("mobile_phone"),
            home_phone=self._field_to_fielddata("home_phone"),
            medicare_number=self._field_to_fielddata("medicare_number"),
            medicare_position=self._field_to_fielddata("medicare_position"),
            provider_number=self._field_to_fielddata("provider_number"),
            sex=self._field_to_fielddata("sex")
        )

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
            if barcode.data:
                decoded_data.append(barcode.data.decode('utf-8'))

        if decoded_data:
            for d in decoded_data:
                if self.validator.is_valid_request_number(d):
                    self.information["request_number"] = (d, 100, None)
                    break
        else:
            self.information["request_number"] = None

    def print_information(self) -> None:
        """
        Prints the information extracted from the form.
        """
        for key, value in self.information.items():
            print(f"{key}: {value}")

    def get_ocr(self) -> float:
        ocr = 0
        
        for i, field in enumerate(self.information):
            if self.information[field] is not None:
                ocr += self.information[field][1]
                i += 1

        ocr /= i + 1
        return ocr


def load_field_config(config_path: str) -> dict:
    with open(config_path, 'r') as config_file:
        return json.load(config_file)
