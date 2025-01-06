from typing import Dict, Any
from dataclasses import dataclass, fields
import logging
import cv2
from datetime import datetime
from backend.FormImagePreparer import FormImagePreparer
from backend.FieldExtractor import FieldExtractor
from backend.DataPostProcessor import DataPostProcessor
from backend.Validator import Validator
from backend.database import DatabaseManager
from backend.MedicareAnchorDetector import MedicareDetector
from backend.constants import OCR_CONFIGS
from pyzbar.pyzbar import decode

import numpy as np
from typing import List, Optional, Tuple
import re

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
    mobile_phone_number: Optional[FieldData] = None
    home_phone_number: Optional[FieldData] = None
    medicare_number: Optional[FieldData] = None
    medicare_position: Optional[FieldData] = None
    provider_number: Optional[FieldData] = None
    sex: Optional[FieldData] = None  # Added sex field as requested

class RequestFormProcessor:
    def __init__(self, image_path: str, debug_mode: bool = False) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)

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
            "mobile_phone_number": None,
            "home_phone_number": None,
            "medicare_number": None,
            "medicare_position": None,
            "provider_number": None,
            "ocr_confidence": None,
            "phone_number": None,  # If combined phone field exists
            "doctor_information": None  # If we need this for provider_number extraction
        }

        self.cropped_image = self.form_preparer.prepare_form()
        self.field_extractor = FieldExtractor(self.cropped_image, debug_mode)

    def process_form(self) -> Dict[str, Any]:
        """
        Processes the request form to extract, clean, validate, and store data.
        Returns a dictionary with processed data and validation errors,
        as well as a ProcessedForm object.
        """
        try:
            print("Starting form processing...")
            form_image = self.cropped_image
            print("Form image loaded.")

            # Step 1: get request number
            print("Adding request number...")
            self._add_request_number(self.image_path)
            print("Request number added.")

            # Step 2: extract information from the form
            print("Finding Medicare anchor...")
            medicare_anchor = self.medicare_anchor_detector.find_medicare_number(form_image)

            if medicare_anchor:
                print(f"Medicare anchor found: {medicare_anchor}")
                # Extract fields using the anchor
                raw_data = self.field_extractor.extract_fields_using_anchor(medicare_anchor)
                raw_data["medicare_number"] = (medicare_anchor.text, medicare_anchor.confidence, medicare_anchor.bounding_box)
                print(f"Fields extracted using Medicare anchor: {raw_data}")
            else:
                print("No Medicare anchor found. Extracting fields using manual regions.")
                raw_data = self.field_extractor.extract_fields_using_manual_regions()
                print(f"Fields extracted using manual regions: {raw_data}")

            print("Raw data extraction complete.")

            # Step 3: Clean and post-process extracted data
            print("Cleaning and processing extracted data...")
            for field, (value, confidence, region) in raw_data.items():
                print(f"Processing field: {field}")
                cleaned_value = self.data_post_processor.clean_text(field, value)
                self.information[field] = (cleaned_value, confidence, region)
                print(f"Field {field} cleaned. Value: {cleaned_value}, Confidence: {confidence}, Region: {region}")

            print("Derived fields post-processing...")
            # Step 4: Perform additional post-processing (including provider number, phone, Medicare, etc.)
            self._post_process_derived_fields()

            print("Overwriting received date with current processing time...")
            # Overwrite received_date with current processing time (ignore OCR extracted value)
            now_str = datetime.now().strftime('%d/%m/%Y')
            self.information["received_date"] = (now_str, 100, None)  # Confidence 100, no bbox since generated
            print(f"Received date set to {now_str}.")

            # Step 5: Validate the cleaned data
            print("Validating processed data...")
            validation_errors = self.validator.validate_data(self.information)
            print(f"Validation errors: {validation_errors}")

            # Convert self.information into a ProcessedForm
            print("Creating processed form object...")
            processed_form = self._create_processed_form()
            print("Processed form object created.")

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
        home_data = self.information.get("home_phone_number")
        mobile_data = self.information.get("mobile_phone_number")
        phone_data = self.information.get("phone_number")

        if (not home_data or not home_data[0]) and (not mobile_data or not mobile_data[0]) and phone_data and phone_data[0]:
            phone_str = phone_data[0]
            ph_confidence = phone_data[1]
            ph_bbox = phone_data[2]

            # Normalize spaces
            phone_str_no_spaces = re.sub(r'\s+', '', phone_str)  
            phone_numbers = self.data_post_processor.process_phone_numbers(phone_str_no_spaces)

            if phone_numbers["home_phone_number"] or phone_numbers["mobile_phone_number"]:
                # Labeled numbers found
                if phone_numbers["home_phone_number"]:
                    self.information["home_phone_number"] = (phone_numbers["home_phone_number"], ph_confidence, ph_bbox)
                if phone_numbers["mobile_phone_number"]:
                    self.information["mobile_phone_number"] = (phone_numbers["mobile_phone_number"], ph_confidence, ph_bbox)
            else:
                # No labeled matches found, try unlabeled approach
                single_numbers = re.findall(r'\d+', phone_str_no_spaces)
                if len(single_numbers) == 1:
                    # Single unlabeled number
                    number = single_numbers[0]
                    if number.startswith("04"):
                        self.information["mobile_phone_number"] = (number, ph_confidence, ph_bbox)
                    else:
                        self.information["home_phone_number"] = (number, ph_confidence, ph_bbox)
                elif len(single_numbers) == 2:
                    # Two unlabeled numbers
                    self.information["mobile_phone_number"] = (single_numbers[0], ph_confidence, ph_bbox)
                    self.information["home_phone_number"] = (single_numbers[1], ph_confidence, ph_bbox)
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
            mobile_phone_number=self._field_to_fielddata("mobile_phone_number"),
            home_phone_number=self._field_to_fielddata("home_phone_number"),
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
