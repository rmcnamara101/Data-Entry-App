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
from RequestFormPreparer import RequestFormPreparer

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

        self.form_preparer = RequestFormPreparer(image_path)
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

        # Step 1: Try using the Medicare anchor method
        medicare_anchor = self.medicare_detector.find_medicare_number(self.requestform)

        if medicare_anchor:
            self.logger.debug(f"Medicare anchor detected: {medicare_anchor}")
            bounding_boxes = self._process_fields_using_anchor(medicare_anchor, field_confidences)
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

        return {
            "data": self.information,
            "validation_errors": validation_errors
        }

    def _apply_background_mask(self, bounding_boxes: List[Tuple[int, int, int, int]]) -> np.ndarray:
        """
        Applies a mask to the image, blacking out all areas except the specified bounding boxes.

        Args:
            bounding_boxes (List[Tuple[int, int, int, int]]): List of bounding box coordinates as (x1, y1, x2, y2).

        Returns:
            np.ndarray: Masked image with background blacked out.
        """
        # Create a black mask
        mask = np.zeros_like(self.requestform)

        # Fill the bounding box regions with white
        for (x1, y1, x2, y2) in bounding_boxes:
            cv2.rectangle(mask, (x1, y1), (x2, y2), (255, 255, 255), -1)

        # Apply the mask to the original image
        masked_image = cv2.bitwise_and(self.requestform, mask)

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

        request_number = self._extract_barcode(self.requestform)
        if request_number and re.match(r'^24H\d{5}$', request_number):
            self.information["request_number"] = request_number
            self.logger.debug(f"Valid request number extracted from barcode: {request_number}")
        else:
            self.information["request_number"] = None
            if request_number:
                self.logger.warning(f"Invalid request number format extracted from barcode: {request_number}")
            else:
                self.logger.debug("No valid request number extracted from barcode.")

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
        Masks out the background except for the specified region, extracts text from it, and returns the text.

        Args:
            region_coords (Tuple[int, int, int, int]): Coordinates of the region as (x1, y1, x2, y2).
            field_name (str): Name of the field being processed.

        Returns:
            Tuple[Optional[str], float]: Extracted text and its confidence score.
        """
        # Unpack region coordinates
        x1, y1, x2, y2 = region_coords

        # Step 1: Create a mask that retains only the specified region
        mask = np.zeros_like(self.requestform)
        cv2.rectangle(mask, (x1, y1), (x2, y2), (255, 255, 255), -1)

        # Step 2: Apply the mask to the original image to isolate the region
        masked_region = cv2.bitwise_and(self.requestform, mask)

        # No cropping to preserve full image resolution

        # Step 3: Preprocess the masked image for better OCR results
        #gray_region = cv2.cvtColor(masked_region, cv2.COLOR_BGR2GRAY)
        #_, thresh_region = cv2.threshold(gray_region, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Optional: Save the preprocessed region for debugging
        if self.debug_mode:
            cv2.imwrite(f"preprocessed_{field_name}.png", masked_region)
            self.logger.debug(f"Preprocessed image for field '{field_name}' saved as 'preprocessed_{field_name}.png'")

        # Step 4: Extract text using the text processor
        if field_name in ["given_names", "surname", "phone_number", "date_of_birth", "medicare_number", "request_date"]:
            text, confidence = self.textprocessor.extract_text(masked_region, psm=7)
        elif field_name == 'sex':
            text, confidence = self.textprocessor.extract_text(masked_region, psm=10)
        else:
            text, confidence = self.textprocessor.extract_text(masked_region, psm=6)


        # Step 5: Clean the extracted text based on field-specific rules
        cleaned_text = self._clean_text(self._to_snake_case(field_name), text)

        return cleaned_text, confidence

    def _post_process_fields(self, masked_image: np.ndarray):
        """
        Handles post-processing of specific fields after initial extraction.

        Args:
            masked_image (np.ndarray): The image with background masked out.
        """

        # Split Medicare Number
        self._split_medicare_number()

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
        self._parse_date_of_birth()

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
        """Validates the extracted information and returns any validation errors."""
        validation_errors = {}

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

        # Validate Overall OCR Confidence
        ocr_confidence = self.information.get("ocr_confidence")
        if ocr_confidence is not None and ocr_confidence < 70.0:
            validation_errors["ocr_confidence"] = "Overall OCR confidence is low."
            self.logger.warning(f"Overall OCR confidence is low: {ocr_confidence}")

        return validation_errors

    def _calculate_ocr_confidence(self, field_confidences: List[float]):
        """Calculates the overall OCR confidence."""
        if field_confidences:
            overall_confidence = sum(field_confidences) / len(field_confidences)
            self.information["ocr_confidence"] = round(overall_confidence, 2)
            self.logger.debug(f"Overall OCR confidence calculated: {self.information['ocr_confidence']}")
        else:
            self.information["ocr_confidence"] = None
            self.logger.warning("No field confidences available to calculate overall OCR confidence.")

    def _split_medicare_number(self):
        """Splits the Medicare number into number and position."""
        medicare_num = self.information.get("medicare_number")
        if medicare_num:
            match = re.match(r'^(\d{10})/(\d)$', medicare_num)
            if match:
                self.information["medicare_number"] = match.group(1)
                self.information["medicare_position"] = match.group(2)
                self.logger.debug(f"Medicare number split - Number: {match.group(1)}, Position: {match.group(2)}")
            else:
                self.logger.warning(f"Medicare number format invalid: {medicare_num}")

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
        """Cleans up the given names by removing quoted text."""
        given_names = self.information.get("given_names")
        if given_names:
            cleaned_names = re.sub(r'\".*?\"', '', given_names).strip()
            self.information["given_names"] = cleaned_names
            self.logger.debug(f"Given names cleaned: {cleaned_names}")

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

    def _parse_date_of_birth(self):
        """Parses the date of birth field into a datetime object."""
        dob_str = self.information.get("date_of_birth")
        if dob_str:
            try:
                dob = datetime.strptime(dob_str, '%d/%m/%Y')
                self.information["date_of_birth"] = dob
                self.logger.debug(f"Date of birth parsed successfully: {dob}")
            except ValueError:
                self.information["date_of_birth"] = None
                self.logger.warning(f"Invalid date of birth format: {dob_str}")

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

        The phone numbers can be in various formats:
        1. Single phone number.
        2. Two phone numbers, either labeled with (H) and (M) or distinguished by their format.

        Returns:
            Tuple[Optional[str], Optional[str]]: (home_phone, mobile_phone)
        """
        phone_field = self.information.get("phone_number")
        home_phone, mobile_phone = None, None

        if not phone_field:
            self.logger.debug("No phone number field found to process.")
            return home_phone, mobile_phone

        # Split the phone_field by common delimiters
        phone_entries = re.split(r'\n|/', phone_field)
        phone_entries = [entry.strip() for entry in phone_entries if entry.strip()]
        self.logger.debug(f"Phone entries found: {phone_entries}")

        # Temporary storage for identified phone numbers
        temp_home = None
        temp_mobile = None

        for entry in phone_entries:
            # Check for labels (H) or (M)
            label_match = re.search(r'\((H|M)\)', entry, re.IGNORECASE)
            if label_match:
                label = label_match.group(1).upper()
                # Remove the label from the entry to isolate the number
                number = re.sub(r'\(H\)|\(M\)', '', entry, flags=re.IGNORECASE).strip()
                # Clean the number by removing non-digit characters except '+'
                number = re.sub(r'[^\d+]', '', number)

                # Normalize mobile numbers starting with +614 to 04
                if number.startswith('+614'):
                    number = '0' + number[4:]

                if label == 'H':
                    # Assign to home_phone
                    if not temp_home:
                        temp_home = number
                        self.logger.debug(f"Assigned '{number}' as Home phone based on label '(H)'.")
                    else:
                        self.logger.warning(f"Multiple Home numbers detected. Existing: '{temp_home}', New: '{number}'. Ignoring new Home number.")
                elif label == 'M':
                    # Assign to mobile_phone
                    if not temp_mobile:
                        temp_mobile = number
                        self.logger.debug(f"Assigned '{number}' as Mobile phone based on label '(M)'.")
                    else:
                        self.logger.warning(f"Multiple Mobile numbers detected. Existing: '{temp_mobile}', New: '{number}'. Ignoring new Mobile number.")
            else:
                # No labels; determine based on number format
                number = re.sub(r'[^\d+]', '', entry).strip()

                # Normalize mobile numbers starting with +614 to 04
                if number.startswith('+614'):
                    number = '0' + number[4:]

                # Determine if the number is Mobile or Home
                if re.match(r'^04\d{8}$', number):
                    # Mobile number
                    if not temp_mobile:
                        temp_mobile = number
                        self.logger.debug(f"Assigned '{number}' as Mobile phone based on format (starts with '04' and 10 digits).")
                    else:
                        # Check if it's another mobile number
                        if re.match(r'^04\d{8}$', number):
                            self.logger.debug(f"Detected second Mobile number '{number}'. Ignoring as per requirements.")
                            continue  # Ignore additional mobile numbers
                elif re.match(r'^\d{8}$', number):
                    # Home number
                    if not temp_home:
                        temp_home = number
                        self.logger.debug(f"Assigned '{number}' as Home phone based on format (8 digits).")
                    else:
                        self.logger.warning(f"Multiple Home numbers detected. Existing: '{temp_home}', New: '{number}'. Ignoring new Home number.")
                else:
                    # Ambiguous format; attempt to classify
                    if re.match(r'^04\d{8}$', number):
                        # Mobile number
                        if not temp_mobile:
                            temp_mobile = number
                            self.logger.debug(f"Assigned '{number}' as Mobile phone based on format (starts with '04' and 10 digits).")
                    elif re.match(r'^\d{10}$', number):
                        # Could be Mobile starting with '0X' where X != 4 or other Mobile formats
                        # Assuming mobile numbers are 10 digits long
                        if not temp_mobile:
                            temp_mobile = number
                            self.logger.debug(f"Assigned '{number}' as Mobile phone based on 10-digit format.")
                    elif re.match(r'^\d{7,9}$', number):
                        # Likely a Home number
                        if not temp_home:
                            temp_home = number
                            self.logger.debug(f"Assigned '{number}' as Home phone based on length ({len(number)} digits).")
                    else:
                        self.logger.warning(f"Unable to classify phone number '{number}'. Ignoring.")
                        continue  # Unable to classify

        # Assign the temporary variables to the return variables
        home_phone = temp_home
        mobile_phone = temp_mobile

        # Final assignment based on the processed numbers
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
        is_valid = bool(re.match(r'^\d{10}/\d$', medicare_number))
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