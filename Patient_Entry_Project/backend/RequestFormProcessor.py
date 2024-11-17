from dataclasses import dataclass
from typing import Optional, Any, Dict, Tuple
import cv2
import numpy as np
from config import FIELD_REGIONS  # Import the FIELD_REGIONS
from TextProcessor import TextProcessor
import re


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
            match = re.match(r'^(\d{9})/(\d)$', medicare_num)
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
            match = re.search(r'\b\w{8}\b$', doctor_info.strip())  # Last 8-character word
            self.information["Provider Number"] = match.group(0) if match else None

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
        """
        Cleans and normalizes extracted text based on the field.

        Args:
            field_name: The name of the field being processed.
            text: The raw extracted text.

        Returns:
            Cleaned text.
        """
        if field_name == "Medicare Number":
            # Remove unexpected characters and spaces
            text = re.sub(r'[^0-9/]', '', text)  # Keep only digits and '/'
            text = re.sub(r'\s+', '', text)  # Remove extra spaces

        elif field_name == "Phone Number":
            # Normalize phone numbers (split concatenated numbers)
            text = re.sub(r'\(H\)|\(M\)', '', text)  # Remove (H) and (M)
            text = re.sub(r'\D', '', text)  # Remove all non-digit characters
            if len(text) > 10:  # If multiple numbers, separate them
                text = f"{text[:10]} / {text[10:]}"

        elif field_name == "Address":
            # Add spaces before capital letters and numbers if missing
            text = re.sub(r'(?<=[a-zA-Z])(?=[A-Z0-9])', ' ', text)  # Add space between words
            text = re.sub(r'\s+', ' ', text)  # Normalize spaces

        elif field_name == "Doctor Information":
            # Extract only the last line for provider number
            lines = text.strip().split('\n')
            if lines:
                text = lines[-1]  # Assume provider number is on the last line
            text = re.sub(r'[^\w]', '', text)  # Remove special characters

        elif field_name == "Request Number":
            # Clean and ensure format like "24Hxxxxx"
            text = re.sub(r'\s+', '', text)  # Remove spaces
            match = re.search(r'24H\d{5}', text)
            if match:
                text = match.group(0)

        # General cleaning: Remove trailing spaces and extra newlines
        text = text.strip()
        return text