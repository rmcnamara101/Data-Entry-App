# RequestFormProcessor.py

from typing import Optional, Any, Dict, Tuple, List
from datetime import datetime
import re
import logging

import cv2
import numpy as np
from pyzbar import pyzbar

from utils import FIELD_REGIONS, MEDICARE_RELATIVE_OFFSETS
from TextProcessor import TextProcessor
from MedicareAnchorDetector import MedicareDetector
from FormImagePreparer import FormImagePreparer
from database import DatabaseManager

# Define allowed characters for each field
ALLOWED_CHARACTERS = {
    "medicare_number": r"[^0-9/]",  # Allow digits and slash
    "home_phone_number": r"[^0-9]",  # Allow digits only
    "mobile_phone_number": r"[^0-9]",  # Allow digits only
    "address": r"[^A-Za-z0-9\s]",  # Allow letters, numbers, and spaces
    "doctor_information": r"[^A-Za-z0-9]",  # Allow letters and numbers
    "request_number": r"[^A-Za-z0-9]",  # Allow letters and digits
    "given_names": r"[^A-Za-z\s]",  # Allow letters and spaces
    # Add other fields as needed
}

# Define common OCR misreads for each field
COMMON_MISREADS = {
    "doctor_information": {
        '§': '5',
        '$': '5',
        'O': '0',
        'l': '1',
        # Add other misreads as needed
    },
    # Define misreads for other fields if necessary
}

# Mapping of postcode first digit to state
POSTCODE_TO_STATE = {
    "2": "NSW",
    "3": "VIC",
    "4": "QLD",
    "5": "SA",
    "6": "WA",
    "7": "TAS",
    "8": "NT",
    "0": "NT",
    "9": "ACT",
}

# Define street types for address parsing
STREET_TYPES = [
    'Street', 'St', 'Road', 'Rd', 'Avenue', 'Ave', 'Drive', 'Dr',
    'Boulevard', 'Blvd', 'Lane', 'Ln', 'Terrace', 'Terr', 'Place',
    'Pl', 'Court', 'Ct'
]


class RequestFormProcessor:
    def __init__(self, image_path: str, debug_mode: bool = False) -> None:
        """
        Initializes the RequestFormProcessor with the preprocessed form image and field configurations.

        Args:
            image_path (str): The path to the image file.
            debug_mode (bool): If True, enables debugging features.
        """
        # Obtain a logger for this class
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)

        # Initialize other attributes
        self.original_image = cv2.imread(image_path)
        if self.original_image is None:
            self.logger.error(f"Failed to read image from path: {image_path}")
            raise FileNotFoundError(f"Image not found at path: {image_path}")
        self.image_path = image_path
        self.form_preparer = FormImagePreparer(image_path)
        self.requestform = self.form_preparer.prepare_form()
        self.field_regions = FIELD_REGIONS
        self.debug_mode = debug_mode
        self.textprocessor = TextProcessor()
        self.medicare_detector = MedicareDetector(debug_mode=debug_mode)
        self.information = {
            "request_number": None,
            "request_date": None,
            "given_names": None,
            "surname": None,
            "name": None,
            "date_of_birth": None,
            "medicare_number": None,
            "medicare_position": None,
            "home_phone_number": None,
            "mobile_phone_number": None,
            "address": None,
            "suburb": None,
            "postcode": None,
            "state": None,
            "doctor_information": None,
            "provider_number": None,
            "ocr_confidence": None,
            "phone_number": None
        }

        self.db_manager = DatabaseManager()

    @staticmethod
    def _to_snake_case(name: str) -> str:
        """
        Converts a field name to snake_case.

        Args:
            name (str): The field name to convert.

        Returns:
            str: The snake_case version of the field name.
        """
        name = name.lower()
        name = re.sub(r'\s+', '_', name)
        name = re.sub(r'\W+', '', name)
        return name

    def process_form(self) -> Dict[str, Any]:
        """
        Processes all fields in the form using defined configurations in FIELD_REGIONS.

        Returns:
            Dict[str, Any]: Extracted and processed information from the form.
        """
        field_confidences = []
        bounding_boxes = []

        request_number = self._extract_barcode(self.original_image)
        if request_number and re.match(r'^24H\d{5}$', request_number):
            self.information["request_number"] = request_number
            self.logger.debug(f"Valid request number extracted from barcode: {request_number}")
        else:
            self.information["request_number"] = None
            if request_number:
                self.logger.warning(f"Invalid request number format extracted from barcode: {request_number}")
            else:
                self.logger.debug("No valid request number extracted from barcode.")

        # Step 1: Try using the Medicare anchor method
        medicare_anchor = self.medicare_detector.find_medicare_number(self.requestform)

        if medicare_anchor:
            self.logger.debug(f"Medicare anchor detected: {medicare_anchor}")
            bounding_boxes = self._process_fields_using_anchor(medicare_anchor, field_confidences)
            medicare_extraction = medicare_anchor.text
            self.information["medicare_number"] = medicare_extraction[:10]
            self.information["medicare_position"] = medicare_extraction[-1]
        else:
            self.logger.debug("Medicare anchor not detected. Falling back to manual regions.")
            bounding_boxes = self._process_fields_using_manual_regions(field_confidences)

        # Apply the background mask based on collected bounding boxes
        if bounding_boxes:
            masked_image = self._apply_background_mask(bounding_boxes)
            self.logger.debug("Background mask applied to the image.")
        else:
            self.logger.warning("No bounding boxes found. Skipping background masking.")
            masked_image = self.requestform  # Proceed with the original image if no boxes found

        # Post-processing specific fields using the masked image
        self._post_process_fields(masked_image)

        # Calculate Overall OCR Confidence
        self._calculate_ocr_confidence(field_confidences)

        # Validate Extracted Information
        validation_errors = self._validate_information()

        self._save_to_database(validation_errors)

        return {
            "data": self.information,
            "validation_errors": validation_errors
        }

    def _apply_background_mask(self, bounding_boxes: List[Tuple[int, int, int, int]]) -> np.ndarray:
        """
        Applies a mask to the image, creating a white background with only the specified bounding box regions visible.

        Args:
            bounding_boxes (List[Tuple[int, int, int, int]]): List of bounding box coordinates as (x1, y1, x2, y2).

        Returns:
            np.ndarray: Masked image with a white background and only the bounding box regions visible.
        """
        # Create a blank white image with the same dimensions as the original
        masked_image = np.full_like(self.requestform, 255)

        # Iterate through the bounding boxes and copy the original image content into the masked image
        for x1, y1, x2, y2 in bounding_boxes:
            roi = self.requestform[y1:y2, x1:x2]
            masked_image[y1:y2, x1:x2] = roi

        if self.debug_mode:
            cv2.imwrite("masked_form.png", masked_image)
            self.logger.debug("Masked image saved as 'masked_form.png'")

        return masked_image

    def _process_fields_using_anchor(self, medicare_anchor: Any, field_confidences: List[float]) -> List[Tuple[int, int, int, int]]:
        """
        Processes fields based on the detected Medicare anchor using relative positions.
        Visualizes the bounding boxes for debugging.

        Args:
            medicare_anchor: The detected Medicare anchor object containing its bounding box.
            field_confidences (List[float]): List to collect individual field confidences.

        Returns:
            List[Tuple[int, int, int, int]]: List of bounding box coordinates.
        """
        
        anchor_x, anchor_y, _, _ = medicare_anchor.bounding_box
        visualized_form = self.requestform.copy()
        bounding_boxes = []

        for field_name, (rel_x, rel_y, field_width, field_height) in MEDICARE_RELATIVE_OFFSETS.items():
            region = self._calculate_relative_region(anchor_x, anchor_y, rel_x, rel_y, field_width, field_height)
            x1, y1, x2, y2 = region
            bounding_boxes.append(region)

            field_value, confidence = self.read_region(region, field_name)

            if field_value is not None:
                snake_case_field = self._to_snake_case(field_name)
                self.information[snake_case_field] = field_value
                self.logger.debug(f"Field '{field_name}' extracted: {field_value} (Confidence: {confidence})")
            else:
                self.logger.warning(f"Failed to extract or validate field '{field_name}'.")

            field_confidences.append(confidence)

            if self.debug_mode:
                self._draw_bounding_box(visualized_form, region, field_name)

        if self.debug_mode:
            cv2.imwrite("field_regions_debug.png", visualized_form)
            self.logger.debug("Debug image saved as 'field_regions_debug.png'")

        return bounding_boxes

    def _process_fields_using_manual_regions(self, field_confidences: List[float]) -> List[Tuple[int, int, int, int]]:
        """
        Processes fields using manually defined regions as a fallback.

        Args:
            field_confidences (List[float]): List to collect individual field confidences.

        Returns:
            List[Tuple[int, int, int, int]]: List of bounding box coordinates.
        """
        visualized_form = self.requestform.copy()
        bounding_boxes = []

        for field_name, field_region in self.field_regions.items():
            region = field_region.coordinates  # Assuming coordinates are (x1, y1, x2, y2)
            bounding_boxes.append(region)

            field_value, confidence = self.read_region(region, field_name)
            snake_case_field = self._to_snake_case(field_name)
            self.information[snake_case_field] = field_value
            field_confidences.append(confidence)

            if self.debug_mode:
                self._draw_bounding_box(visualized_form, region, field_name)
                self.logger.debug(f"Field '{field_name}' extracted: '{field_value}' (Confidence: {confidence})")

        if self.debug_mode:
            cv2.imwrite("manual_field_regions_debug.png", visualized_form)
            self.logger.debug("Debug image saved as 'manual_field_regions_debug.png'")

        return bounding_boxes

    def read_region(self, region_coords: Tuple[int, int, int, int], field_name: str) -> Tuple[Optional[str], float]:
        """
        Masks out the background except for the specified region, applies padding around the region,
        and extracts text from the cropped and masked image.

        Args:
            region_coords (Tuple[int, int, int, int]): Coordinates of the region as (x1, y1, x2, y2).
            field_name (str): Name of the field being processed.

        Returns:
            Tuple[Optional[str], float]: Extracted text and its confidence score.
        """
        # Unpack region coordinates
        x1, y1, x2, y2 = region_coords

        # Define padding (adjust as needed for optimal OCR performance)
        padding = 50  # Pixels to pad around the region
        padded_x1 = max(0, x1 - padding)
        padded_y1 = max(0, y1 - padding)
        padded_x2 = min(self.requestform.shape[1], x2 + padding)
        padded_y2 = min(self.requestform.shape[0], y2 + padding)

        # Step 1: Create a blank white image
        masked_image = np.full_like(self.requestform, 255)

        # Step 2: Copy the specified region from the original image to the masked image
        roi = self.requestform[y1:y2, x1:x2]
        masked_image[y1:y2, x1:x2] = roi

        # Step 3: Crop the padded region from the masked image
        cropped_image = masked_image[padded_y1:padded_y2, padded_x1:padded_x2]

        # Optional: Save the preprocessed region for debugging
        if self.debug_mode:
            cv2.imwrite(f"preprocessed_{field_name}.png", cropped_image)
            self.logger.debug(f"Preprocessed image for field '{field_name}' saved as 'preprocessed_{field_name}.png'")

        # Step 4: Extract text using the text processor
        if field_name in ["given_names", "surname", "date_of_birth", "medicare_number", "request_date"]:
            text, confidence = self.textprocessor.extract_text(cropped_image, psm=7)
        elif field_name == 'sex':
            text, confidence = self.textprocessor.extract_text(cropped_image, psm=10)
        else:
            text, confidence = self.textprocessor.extract_text(cropped_image, psm=6)

        # Clean the extracted text
        cleaned_text = self._clean_text(self._to_snake_case(field_name), text)

        return cleaned_text, confidence

    def _post_process_fields(self, masked_image: np.ndarray):
        """
        Handles post-processing of specific fields after initial extraction.

        Args:
            masked_image (np.ndarray): The image with background masked out.
        """

        # Process Phone Numbers
        home_phone, mobile_phone = self._process_phone_numbers()
        self.information["home_phone_number"] = home_phone
        self.information["mobile_phone_number"] = mobile_phone
        self.logger.debug(f"Processed phone numbers - Home: {home_phone}, Mobile: {mobile_phone}")

        # Parse Address
        if self.information.get("address"):
            address_parts = self._split_address(self.information["address"])
            self.information.update(address_parts)
            self.logger.debug(f"Parsed address into components: {address_parts}")

        # Extract Provider Number
        self._extract_provider_number()

        # Cleanup Given Names
        self._cleanup_given_names()

        # Map Total Name
        self._map_total_name()

        # Parse Date of Birth
        self._parse_date(self.information["date_of_birth"], "date_of_birth")

        # Parse Request Date
        self._parse_date(self.information["request_date"], "request_date")

        # Parse Sex Field
        self._parse_sex_field()

    def _extract_barcode(self, image: np.ndarray) -> Optional[str]:
        """
        Extracts and decodes the barcode from the form.

        Args:
            image (np.ndarray): The preprocessed image with background masked out.

        Returns:
            Optional[str]: The decoded barcode data if successful, else None.
        """
        barcodes = pyzbar.decode(image)

        self.logger.debug(f"Detected {len(barcodes)} barcodes in the barcode region.")

        for barcode in barcodes:
            barcode_data = barcode.data.decode('utf-8').strip()
            barcode_type = barcode.type
            self.logger.debug(f"Barcode detected: {barcode_data} (Type: {barcode_type})")

            if re.match(r'^24H\d{5}$', barcode_data):
                self.logger.debug(f"Valid barcode data found: {barcode_data}")
                return barcode_data
            else:
                self.logger.warning(f"Invalid barcode format detected: {barcode_data}")

        self.logger.debug("No valid barcode data found.")
        return None

    def get_data(self) -> Dict[str, Any]:
        """Returns the extracted information."""
        self.logger.debug("Returning extracted data.")
        return self.information

    def _calculate_relative_region(self, anchor_x: int, anchor_y: int, rel_x: int, rel_y: int,
                                   width: int, height: int) -> Tuple[int, int, int, int]:
        """
        Calculates the absolute region coordinates based on relative offsets.

        Args:
            anchor_x (int): X-coordinate of the anchor.
            anchor_y (int): Y-coordinate of the anchor.
            rel_x (int): Relative X offset.
            rel_y (int): Relative Y offset.
            width (int): Width of the field region.
            height (int): Height of the field region.

        Returns:
            Tuple[int, int, int, int]: (x1, y1, x2, y2) coordinates of the region.
        """
        x1 = anchor_x + rel_x
        y1 = anchor_y - rel_y
        x2 = x1 + width
        y2 = y1 + height
        self.logger.debug(f"Calculated relative region: ({x1}, {y1}, {x2}, {y2})")
        return x1, y1, x2, y2

    def _clean_text(self, field_name: str, text: str) -> str:
        """
        Cleans the extracted text by correcting misreads and applying character restrictions.

        Args:
            field_name (str): The name of the field.
            text (str): The extracted text.

        Returns:
            str: The cleaned text.
        """
        text = self._correct_misreadings(field_name, text)

        # Apply character whitelist
        if field_name in ALLOWED_CHARACTERS:
            pattern = ALLOWED_CHARACTERS[field_name]
            text = re.sub(pattern, '', text)

        # Additional field-specific cleaning
        if field_name == "medicare_number":
            text = re.sub(r'\s+', '', text)
        elif field_name in ["home_phone_number", "mobile_phone_number"]:
            text = re.sub(r'\D+', '', text)
        elif field_name == "address":
            text = re.sub(r'(?<!^)(?=[A-Z])', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
        elif field_name == "request_number":
            text = re.sub(r'\s+', '', text)
            match = re.search(r'24H\d{5}', text)
            if match:
                text = match.group(0)
        elif field_name in ["given_names", "surname", "name"]:
            # Allow letters, spaces, and common punctuation in names
            text = re.sub(r'[^A-Za-z\s\-\'\.]', '', text)
            text = re.sub(r'\s+', ' ', text).strip()

        self.logger.debug(f"Cleaned text for field '{field_name}': '{text}'")
        return text.strip()

    def _correct_misreadings(self, field_name: str, text: str) -> str:
        """
        Corrects common OCR misreadings based on field-specific rules.

        Args:
            field_name (str): The name of the field.
            text (str): The text to correct.

        Returns:
            str: The corrected text.
        """
        misreads = COMMON_MISREADS.get(field_name, {})
        for wrong_char, correct_char in misreads.items():
            text_before = text
            text = text.replace(wrong_char, correct_char)
            if text_before != text:
                self.logger.debug(f"Corrected misread '{wrong_char}' to '{correct_char}' in field '{field_name}'")
        return text

    def _validate_information(self) -> Dict[str, str]:
        """
        Validates the extracted information and returns any validation errors.

        Ensures that all vital fields are checked for correctness.
        """
        validation_errors = {}

        # Define required fields
        required_fields = [
            "given_names",
            "surname",
            "date_of_birth",
            "request_date",
            "medicare_number",
            "request_number",
            "provider_number",
        ]

        # Check for missing required fields
        for field in required_fields:
            value = self.information.get(field)
            if not value:
                validation_errors[field] = f"{field.replace('_', ' ').title()} is required."
                self.logger.error(f"Missing required field: {field.replace('_', ' ').title()}")

        # Validate Medicare Number
        medicare_number = self.information.get("medicare_number")
        if medicare_number and not self.is_valid_medicare_number(medicare_number):
            validation_errors["medicare_number"] = "Invalid Medicare Number format."
            self.logger.error(f"Medicare number validation failed: {medicare_number}")

        # Validate Phone Numbers
        for phone_type in ["home_phone_number", "mobile_phone_number"]:
            phone = self.information.get(phone_type)
            if phone and not self.is_valid_phone_number(phone):
                validation_errors[phone_type] = f"Invalid {phone_type.replace('_', ' ').title()} format."
                self.logger.error(f"{phone_type.replace('_', ' ').title()} validation failed: {phone}")

        # Validate Request Number
        request_number = self.information.get("request_number")
        if request_number and not self.is_valid_request_number(request_number):
            validation_errors["request_number"] = "Invalid Request Number format."
            self.logger.error(f"Request number validation failed: {request_number}")

        # Validate Provider Number
        provider_number = self.information.get("provider_number")
        if provider_number and not self.is_valid_provider_number(provider_number):
            validation_errors["provider_number"] = "Invalid Provider Number format."
            self.logger.error(f"Provider number validation failed: {provider_number}")

        # Validate Date Fields
        for date_field in ["date_of_birth", "request_date"]:
            date_value = self.information.get(date_field)
            if date_value and not self.is_valid_date(date_value):
                validation_errors[date_field] = f"Invalid {date_field.replace('_', ' ').title()} format."
                self.logger.error(f"{date_field.replace('_', ' ').title()} validation failed: {date_value}")

        # Validate Overall OCR Confidence
        ocr_confidence = self.information.get("ocr_confidence")
        if ocr_confidence is not None and ocr_confidence < 70.0:
            validation_errors["ocr_confidence"] = "Overall OCR confidence is low."
            self.logger.warning(f"Overall OCR confidence is low: {ocr_confidence}")

        return validation_errors if validation_errors else None

    def _calculate_ocr_confidence(self, field_confidences: List[float]):
        """Calculates the overall OCR confidence."""
        if field_confidences:
            overall_confidence = sum(field_confidences) / len(field_confidences)
            self.information["ocr_confidence"] = round(overall_confidence, 2)
            self.logger.debug(f"Overall OCR confidence calculated: {self.information['ocr_confidence']}")
        else:
            self.information["ocr_confidence"] = None
            self.logger.warning("No field confidences available to calculate overall OCR confidence.")

    def _extract_provider_number(self):
        """Extracts and validates the provider number from doctor information."""
        doctor_info = self.information.get("doctor_information")
        if doctor_info:
            provider_number = doctor_info[-8:]
            if re.match(r'^[A-Za-z0-9]{8}$', provider_number):
                self.information["provider_number"] = provider_number
                self.logger.debug(f"Provider number extracted: {provider_number}")
            else:
                self.information["provider_number"] = None
                self.logger.warning(f"Invalid provider number format: {provider_number}")

    def _cleanup_given_names(self):
        """
        Cleans up the given names by removing quoted text.
        """
        given_names = self.information.get("given_names")

        for i in range(len(given_names)):
            if given_names[i] == "'" or given_names[i] == '"':
                break
        given_names = given_names[:i]
        return given_names

    def _map_total_name(self):
        """Maps the total name field or constructs it from given names and surname."""
        if self.information.get("total_name"):
            self.information["name"] = self.information.pop("total_name")
            self.logger.debug(f"Total name mapped from 'total_name' field: {self.information['name']}")
        elif self.information.get("given_names") and self.information.get("surname"):
            self.information["name"] = f"{self.information['given_names']} {self.information['surname']}"
            self.logger.debug(f"Total name constructed from given names and surname: {self.information['name']}")
        else:
            self.information["name"] = None
            self.logger.warning("Insufficient data to construct the total name.")

    def _parse_date(self, date: str, field_name: str):
        """Parses the date of birth field into a datetime object."""
        date_str = date
        if date_str:
            try:
                dob = datetime.strptime(date_str, '%d/%m/%Y')
                self.information[field_name] = dob
                self.logger.debug(f"Date of birth parsed successfully: {dob}")
            except ValueError:
                self.information[field_name] = None
                self.logger.warning(f"Invalid date of birth format: {date_str}")

    def _parse_sex_field(self):
        """Parses the sex field and sets it to 'U' if not valid."""
        sex = self.information.get('sex')
        if sex not in ['M', 'F', 'U']:
            self.information['sex'] = 'U'
            self.logger.debug(f"Sex field set to 'U' due to invalid value: {sex}")

    def _find_street_type_index(self, tokens: List[str]) -> Optional[int]:
        """
        Finds the index of the street type in the address tokens.

        Args:
            tokens (List[str]): Tokenized address.

        Returns:
            Optional[int]: Index of the street type or None if not found.
        """
        for i, token in enumerate(tokens):
            clean_token = token.strip(",.").capitalize()
            if clean_token in STREET_TYPES:
                self.logger.debug(f"Found street type '{clean_token}' at index {i}")
                return i
        self.logger.debug("No street type found in address tokens.")
        return None

    def _split_address(self, full_address: str) -> Dict[str, Any]:
        """
        Splits the address into components: Address, Suburb, Postcode, and State.

        Args:
            full_address (str): The full address string extracted from the form.

        Returns:
            Dict[str, Any]: A dictionary with separate address components.
        """
        address_components = {"address": None, "suburb": None, "postcode": None, "state": None}

        # Extract postcode (assumed to be the last 4 digits)
        match = re.search(r'(\d{4})$', full_address.strip())
        if match:
            postcode = match.group(1)
            address_components["postcode"] = postcode
            full_address = full_address[:match.start()].strip()
            self.logger.debug(f"Extracted postcode: {postcode}")

            state = POSTCODE_TO_STATE.get(postcode[0], "NSW")
            address_components["state"] = state
            self.logger.debug(f"Mapped postcode to state: {state}")
        else:
            self.logger.warning("Postcode not found in the address.")

        # Tokenize the address
        tokens = full_address.split()
        street_type_index = self._find_street_type_index(tokens)

        if street_type_index is not None:
            address_components["address"] = ' '.join(tokens[:street_type_index + 1])
            address_components["suburb"] = ' '.join(tokens[street_type_index + 1:])
            self.logger.debug(f"Address split based on street type: Address='{address_components['address']}', Suburb='{address_components['suburb']}'")
        else:
            # Fallback if no street type found
            address_components["address"] = ' '.join(tokens[:2]) if len(tokens) >= 2 else full_address
            address_components["suburb"] = ' '.join(tokens[2:]) if len(tokens) > 2 else None
            self.logger.debug(f"Address split without street type: Address='{address_components['address']}', Suburb='{address_components['suburb']}'")

        return address_components
    
    def _process_phone_numbers(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Processes the 'phone_number' field to extract and assign Home and Mobile phone numbers.

        Handles cases where:
        1. Single phone number is provided.
        2. Two phone numbers are concatenated and labeled with (H) and (M).
        3. Other mixed or unexpected formats.

        Returns:
            Tuple[Optional[str], Optional[str]]: (home_phone, mobile_phone)
        """
        phone_field = self.information.get("phone_number")
        home_phone, mobile_phone = None, None

        if not phone_field:
            self.logger.debug("No phone number field found to process.")
            return home_phone, mobile_phone

        # Use regex to find all phone numbers and their labels
        phone_matches = re.findall(r'(\d+)\((H|M)\)', phone_field)
        self.logger.debug(f"Extracted phone matches: {phone_matches}")

        for number, label in phone_matches:
            # Normalize the number by removing unwanted characters
            number = re.sub(r'[^\d+]', '', number).strip()

            # Normalize mobile numbers starting with +614 to 04
            if number.startswith('+614'):
                number = '0' + number[4:]

            if label.upper() == 'H':
                # Assign to home_phone
                if not home_phone:
                    home_phone = number
                    self.logger.debug(f"Assigned '{number}' as Home phone based on label '(H)'.")
                else:
                    self.logger.warning(f"Multiple Home numbers detected. Existing: '{home_phone}', New: '{number}'. Ignoring new Home number.")
            elif label.upper() == 'M':
                # Assign to mobile_phone
                if not mobile_phone:
                    mobile_phone = number
                    self.logger.debug(f"Assigned '{number}' as Mobile phone based on label '(M)'.")
                else:
                    self.logger.warning(f"Multiple Mobile numbers detected. Existing: '{mobile_phone}', New: '{number}'. Ignoring new Mobile number.")

        # Log final assignments
        self.logger.debug(f"Final assignment - Home Phone: {home_phone}, Mobile Phone: {mobile_phone}")

        return home_phone, mobile_phone

    def is_valid_medicare_number(self, medicare_number: str) -> bool:
        """
        Validates the Medicare number format.

        Args:
            medicare_number (str): The Medicare number to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
        is_valid = bool(re.match(r'^\d{10}$', medicare_number))
        self.logger.debug(f"Medicare number validation for '{medicare_number}': {'Passed' if is_valid else 'Failed'}")
        return is_valid

    def is_valid_phone_number(self, phone_number: str) -> bool:
        """
        Validates the phone number format.

        Args:
            phone_number (str): The phone number to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
        is_valid = bool(re.match(r'^\d{10}$', phone_number))
        self.logger.debug(f"Phone number validation for '{phone_number}': {'Passed' if is_valid else 'Failed'}")
        return is_valid

    def is_valid_request_number(self, request_number: str) -> bool:
        """
        Validates the request number format.

        Args:
            request_number (str): The request number to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
        is_valid = bool(re.match(r'^24H\d{5}$', request_number))
        self.logger.debug(f"Request number validation for '{request_number}': {'Passed' if is_valid else 'Failed'}")
        return is_valid

    def is_valid_provider_number(self, provider_number: str) -> bool:
        """
        Validates the provider number format.

        Args:
            provider_number (str): The provider number to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
        is_valid = bool(re.match(r'^[A-Za-z0-9]{8}$', provider_number))
        self.logger.debug(f"Provider number validation for '{provider_number}': {'Passed' if is_valid else 'Failed'}")
        return is_valid

    def is_valid_date(self, date: datetime) -> bool:
        if type(date) is not datetime:
            return False
        else:
            return True
            

    def _draw_bounding_box(self, image: np.ndarray, region: Tuple[int, int, int, int], label: str) -> None:
        """
        Draws a bounding box and label on the image for debugging.

        Args:
            image (np.ndarray): The image to draw on.
            region (Tuple[int, int, int, int]): (x1, y1, x2, y2) coordinates.
            label (str): Label to put near the bounding box.
        """
        x1, y1, x2, y2 = region
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(image, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        self.logger.debug(f"Drew bounding box for field '{label}' at region ({x1}, {y1}, {x2}, {y2})")

    def _save_to_database(self, validation_errors: Dict[str, str]):
        """
        Saves the extracted data to the database, including any validation errors.

        Args:
            validation_errors (Dict[str, str]): Validation errors from processing.
        """
        file_path = self.image_path  # Use the image path as the file path
        ocr_confidence = self.information.get("ocr_confidence")

        # Save the data to the database
        try:
            self.db_manager.add_patient_record(
                patient_info=self.information,
                file_path=file_path,
                ocr_confidence=ocr_confidence,
                validation_errors=validation_errors
            )
            self.logger.info(f"Data saved to database for file: {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to save data to database: {e}")

if __name__ == '__main__':
    import argparse
    import os
    import sys
    import pandas as pd

    parser = argparse.ArgumentParser(description="Batch test RequestFormProcessor on a folder of images and export results to Excel.")
    parser.add_argument("folder_path", help="Path to the folder containing input images")
    parser.add_argument("--output_excel", default="form_test_results.xlsx", help="Output Excel file to save the results.")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode.")
    args = parser.parse_args()

    # Validate the input folder
    if not os.path.isdir(args.folder_path):
        print(f"Error: The folder '{args.folder_path}' does not exist or is not a directory.")
        sys.exit(1)

    # Prepare a list to store result dictionaries for each file
    results = []

    # Process each file in the provided folder
    for filename in os.listdir(args.folder_path):
        input_path = os.path.join(args.folder_path, filename)

        # Skip directories and non-image files by attempting to read as image
        if not os.path.isfile(input_path):
            continue

        # Attempt to load image (quick check)
        test_image = cv2.imread(input_path)
        if test_image is None:
            # Not a valid image file
            continue

        # Process the form
        try:
            processor = RequestFormProcessor(input_path, debug_mode=args.debug)
            result = processor.process_form()  # returns {"data": {...}, "validation_errors": {...} or None}
            data = result["data"]
            validation_errors = result["validation_errors"]

            # Flatten validation_errors into a string if they exist
            if validation_errors is not None:
                error_summary = "; ".join([f"{k}: {v}" for k, v in validation_errors.items()])
            else:
                error_summary = ""

            # Collect results in a single dictionary
            record = {
                "filename": filename,
                "ocr_confidence": data.get("ocr_confidence", None),
                "validation_errors": error_summary
            }

            # Include all extracted fields from data
            for field, value in data.items():
                if field not in record:  # Avoid overwriting keys like 'ocr_confidence'
                    record[field] = value

            results.append(record)

        except Exception as e:
            # If any file fails to process for some reason, record it
            results.append({
                "filename": filename,
                "ocr_confidence": None,
                "validation_errors": f"Processing failed: {str(e)}"
            })

    # Convert results to a DataFrame and save to Excel
    df = pd.DataFrame(results)
    df.to_excel(args.output_excel, index=False)
    print(f"Results saved to {args.output_excel}")

    # Compute some summary statistics
    total_forms = len(df)
    successful_forms = df[df["validation_errors"] == ""].shape[0]
    failed_forms = total_forms - successful_forms
    avg_confidence = df["ocr_confidence"].mean() if "ocr_confidence" in df.columns and not df["ocr_confidence"].isnull().all() else None

    print("Summary Statistics:")
    print(f"Total forms processed: {total_forms}")
    print(f"Successful forms (no validation errors): {successful_forms}")
    print(f"Forms with validation errors: {failed_forms}")
    if avg_confidence is not None:
        print(f"Average OCR Confidence: {avg_confidence:.2f}")
    else:
        print("No OCR Confidence data available.")