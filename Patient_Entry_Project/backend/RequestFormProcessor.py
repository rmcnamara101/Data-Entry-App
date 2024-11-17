from dataclasses import dataclass
from typing import Optional, Any, Dict, Tuple
import cv2
import numpy as np
from config import FIELD_REGIONS  # Import the FIELD_REGIONS
from TextProcessor import TextProcessor
import re

# Define allowed characters for each field
allowed_characters = {
    "Medicare Number": r"[^0-9/]",  # Allow digits and slash
    "Phone Number": r"[^0-9]",      # Allow digits only
    "Address": r"[^A-Za-z0-9\s]",   # Allow letters, numbers, and spaces
    "Doctor Information": r"[^A-Za-z0-9]",  # Allow letters and numbers
    "Request Number": r"[^A-Za-z0-9]",      # Allow letters and digits
    # Add other fields as needed
}

# Define common OCR misreads for each field
common_misreads = {
    "Doctor Information": {
        '§': '5',
        '$': '5',
        'O': '0',
        'I': '1',
        'l': '1',
        'B': '8',
        # Add other misreads as needed
    },
    # Define misreads for other fields if necessary
}

class RequestFormProcessor:
    def __init__(self, processed_form: np.ndarray, debug_mode=False) -> None:
        """
        Initializes the RequestFormProcessor with the preprocessed form image and field configurations.

        Args:
            processed_form: The preprocessed form image as a NumPy array.
            debug_mode: If True, enables debugging features.
        """
        self.requestform = processed_form
        self.field_regions = FIELD_REGIONS  # Load from config.py
        self.debug_mode = debug_mode
        self.information = {field: None for field in self.field_regions.keys()}
        self.textprocessor = TextProcessor()

    def process_form(self) -> Dict[str, Any]:
        """
        Processes all fields in the form using defined configurations in FIELD_REGIONS.

        Returns:
            Dict[str, Any]: Extracted and processed information from the form.
        """
        for field_name, field_region in self.field_regions.items():
            self.information[field_name] = self._extract_field(field_region)

        # Process specific fields
        # 1. Request Number Fix
        if self.information.get("Request Number"):
            request_number = self.information["Request Number"]
            match = re.match(r'^24H\d{5}$', request_number)
            if match:
                self.information["Request Number"] = match.group(0)
            else:
                self.information["Request Number"] = None

        # 2. Medicare Number Split
        if self.information.get("Medicare Number"):
            medicare_num = self.information["Medicare Number"]
            match = re.match(r'^(\d{10})/(\d)$', medicare_num)
            if match:
                self.information["Medicare Number"] = match.group(1)
                self.information["Medicare Position"] = match.group(2)

        # 3. Phone Number Cleanup
        if self.information.get("Phone Number"):
            phone_numbers = re.findall(r'\d{10}', self.information["Phone Number"])
            self.information["Phone Number"] = " / ".join(phone_numbers[:2])  # Keep first two numbers

        # 4. Address Parsing
        if self.information.get("Address"):
            address_parts = self._split_address(self.information["Address"])
            self.information.update(address_parts)

        # 5. Doctor Provider Number
        if self.information.get("Doctor Information"):
            doctor_info = self.information["Doctor Information"]

            result = doctor_info[-1:-8]
            self.information["Provider Number"] = result

        return self.information

    def _extract_field(self, field_region) -> Optional[str]:
        """
        Extracts and validates text from a specific field region.

        Args:
            field_region: The FieldRegion object defining the region and validation.

        Returns:
            Extracted and validated text, or None if validation fails.
        """
        # Get the image region
        region = self._get_region(field_region.coordinates)

        # Extract text using TextProcessor
        text, confidence = self.textprocessor.extract_text(region)

        # Debugging extracted text
        if self.debug_mode:
            print(f"Raw text for {field_region.name}: {text}")

        # Clean extracted text
        text = self._clean_text(field_region.name, text)

        # Validate text if a pattern is defined
        if field_region.validation_pattern and not self._validate_text(field_region.validation_pattern, text):
            if self.debug_mode:
                print(f"Validation failed for {field_region.name}: {text}")
            return None

        return text.strip()

    def _get_region(self, coordinates: Tuple[int, int, int, int]) -> np.ndarray:
        """
        Extracts a region from the form image based on coordinates.

        Args:
            coordinates: (x1, y1, x2, y2) coordinates of the field region.

        Returns:
            Extracted image region as a NumPy array.
        """
        x1, y1, x2, y2 = coordinates
        return self.requestform[y1:y2, x1:x2]

    def _validate_text(self, pattern: str, text: str) -> bool:
        """
        Validates extracted text against a regular expression.

        Args:
            pattern: The regex pattern to validate against.
            text: The text to validate.

        Returns:
            True if the text matches the pattern, False otherwise.
        """
        return bool(re.match(pattern, text))
    
    def _split_address(self, full_address: str) -> Dict[str, Any]:
        """
        Splits the address into components: Address, Suburb, Postcode, and State.

        Args:
            full_address: The full address string extracted from the form.

        Returns:
            Dict[str, Any]: A dictionary with separate address components.
        """
        address_components = {"Address": None, "Suburb": None, "Postcode": None, "State": None}

        # Extract postcode (last 4 digits) and remaining address
        match = re.match(r'^(.*)\s(\d{4})$', full_address.strip())
        if not match:
            return address_components

        raw_address, postcode = match.groups()
        address_components["Postcode"] = postcode

        # Correct state mapping
        postcode_to_state = {
            "2": "NSW",  # NSW postcodes
            "3": "VIC",  # VIC postcodes
            "4": "QLD",  # QLD postcodes
            "5": "SA",   # SA postcodes
            "6": "WA",   # WA postcodes
            "7": "TAS",  # TAS postcodes
            "8": "NT",   # NT postcodes
            "9": "ACT",  # ACT postcodes
        }
        state = postcode_to_state.get(postcode[0], "NSW")  # Default to NSW if not found
        address_components["State"] = state

        # Split remaining address into street and suburb
        parts = raw_address.rsplit(' ', 1)
        if len(parts) == 2:
            address_components["Address"], address_components["Suburb"] = parts
        else:
            address_components["Address"] = raw_address

        return address_components
    
    def _clean_text(self, field_name: str, text: str) -> str:
        # Correct common misreads
        text = self._correct_misreadings(field_name, text)

        # Apply character whitelist
        if field_name in allowed_characters:
            pattern = allowed_characters[field_name]
            text = re.sub(pattern, '', text)

        # Additional cleaning per field
        if field_name == "Medicare Number":
            text = re.sub(r'\s+', '', text)
        elif field_name == "Phone Number":
            if len(text) > 10:
                text = f"{text[:10]} / {text[10:]}"
        elif field_name == "Address":
            text = re.sub(r'(?<!^)(?=[A-Z0-9])', ' ', text)
            text = re.sub(r'\s+', ' ', text).strip()
        elif field_name == "Doctor Information":
            # No need to insert spaces if we're extracting the Provider Number directly
            pass
        elif field_name == "Request Number":
            text = re.sub(r'\s+', '', text)
            match = re.search(r'24H\d{5}', text)
            if match:
                text = match.group(0)

        return text.strip()
    
    def _correct_misreadings(self, field_name: str, text: str) -> str:
        if field_name in common_misreads:
            misreads = common_misreads[field_name]
            for wrong_char, correct_char in misreads.items():
                text = text.replace(wrong_char, correct_char)
        return text