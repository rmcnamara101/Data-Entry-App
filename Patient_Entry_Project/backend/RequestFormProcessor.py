from dataclasses import dataclass
from typing import Optional, Any, Dict, Tuple
import cv2
import numpy as np
from config import FIELD_REGIONS, MEDICARE_RELATIVE_OFFSETS
from TextProcessor import TextProcessor
import re
from MedicareAnchorDetector import * 
from RequestFormPreparer import RequestFormPreparer

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
        'l': '1',
        # Add other misreads as needed
    },
    # Define misreads for other fields if necessary
}

class RequestFormProcessor:
    def __init__(self, image_path: str, debug_mode=False) -> None:
        """
        Initializes the RequestFormProcessor with the preprocessed form image and field configurations.

        Args:
            processed_form: The preprocessed form image as a NumPy array.
            debug_mode: If True, enables debugging features.
        """
        self.form_preparer = RequestFormPreparer(image_path)
        self.requestform = self.form_preparer.prepare_form()
        self.field_regions = FIELD_REGIONS  # Load from config.py
        self.debug_mode = debug_mode
        self.information = {field: None for field in self.field_regions.keys()}
        self.textprocessor = TextProcessor()
        self.medicare_detector = MedicareDetector(debug_mode=debug_mode)

    def process_form(self) -> Dict[str, Any]:
        """
        Processes all fields in the form using defined configurations in FIELD_REGIONS.

        Returns:
            Dict[str, Any]: Extracted and processed information from the form.
        """
         # Step 1: Try using the Medicare anchor method
        medicare_anchor = self.medicare_detector.find_medicare_number(self.requestform)

        if medicare_anchor:
            if self.debug_mode:
                print(f"Medicare anchor detected: {medicare_anchor}")
            self._process_fields_using_anchor(medicare_anchor)
        else:
            if self.debug_mode:
                print("Medicare anchor not detected. Falling back to manual regions.")
            self._process_fields_using_manual_regions()

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
            self.information["Phone Number"] = phone_numbers[0] if phone_numbers else None

        # 4. Address Parsing
        if self.information.get("Address"):
            address_parts = self._split_address(self.information["Address"])
            self.information.update(address_parts)

        # 5. Doctor Provider Number
        if self.information.get("Doctor Information"):
            doctor_info = self.information["Doctor Information"]

            # Take the last 8 characters as the provider number
            provider_number = doctor_info[-8:]

            # Validate the provider number format
            if re.match(r'^[A-Za-z0-9]{8}$', provider_number):
                self.information["Provider Number"] = provider_number
            else:
                # If validation fails, set Provider Number to None or handle accordingly
                self.information["Provider Number"] = None

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

        # Extract postcode (assumed to be the last 4 digits)
        match = re.search(r'(\d{4})$', full_address.strip())
        if match:
            postcode = match.group(1)
            address_components["Postcode"] = postcode

            # Remove postcode from the full address
            full_address = full_address[:match.start()].strip()

            # Map postcode to state
            postcode_to_state = {
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
            state = postcode_to_state.get(postcode[0], "NSW")
            address_components["State"] = state
        else:
            # Handle cases where postcode is missing
            pass

        # Define street types
        street_types = [
            'Street', 'St', 'Road', 'Rd', 'Avenue', 'Ave', 'Drive', 'Dr',
            'Boulevard', 'Blvd', 'Lane', 'Ln', 'Terrace', 'Terr', 'Place',
            'Pl', 'Court', 'Ct'
        ]

        # Tokenize the address
        tokens = full_address.split()

        # Initialize index
        street_type_index = None

        # Find the index of the street type
        for i, token in enumerate(tokens):
            clean_token = token.strip(",.").capitalize()
            if clean_token in street_types:
                street_type_index = i
                break

        if street_type_index is not None:
            # Address includes tokens up to and including the street type
            address_components["Address"] = ' '.join(tokens[:street_type_index + 1])
            # Suburb is the remaining tokens
            address_components["Suburb"] = ' '.join(tokens[street_type_index + 1:])
        else:
            # If no street type is found, make a reasonable assumption
            # For example, the first two tokens are the address, rest is suburb
            address_components["Address"] = ' '.join(tokens[:2])
            address_components["Suburb"] = ' '.join(tokens[2:])

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
            # Insert spaces before capital letters only, excluding the first character
            text = re.sub(r'(?<!^)(?=[A-Z])', ' ', text)
            # Normalize multiple spaces to a single space
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
    
    def _process_fields_using_anchor(self, medicare_anchor: MedicareAnchor) -> None:
        """
        Processes fields based on the detected Medicare anchor using relative positions.
        Visualizes the bounding boxes for debugging.

        Args:
            medicare_anchor: The detected Medicare anchor object containing its bounding box.
        """
        anchor_x, anchor_y, _, _ = medicare_anchor.bounding_box

        visualized_form = self.requestform.copy()

        for field_name, (rel_x, rel_y, field_width, field_height) in MEDICARE_RELATIVE_OFFSETS.items():
            region_x1 = anchor_x + rel_x
            region_y1 = anchor_y - rel_y
            region_x2 = region_x1 + field_width
            region_y2 = region_y1 + field_height

            # Draw the bounding box on the visualized form
            cv2.rectangle(
                visualized_form, (region_x1, region_y1), (region_x2, region_y2), (0, 255, 0), 2
            )
            cv2.putText(
                visualized_form,
                field_name,
                (region_x1, region_y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1,
            )

            # Extract the text from the region
            region = self.requestform[region_y1:region_y2, region_x1:region_x2]
            text, confidence = self.textprocessor.extract_text(region)

            if self.debug_mode:
                print(f"Field: {field_name}, Region: ({region_x1}, {region_y1}, {region_x2}, {region_y2}), "
                    f"Text: '{text}', Confidence: {confidence}")

            # Clean and validate the extracted text
            self.information[field_name] = self._clean_text(field_name, text)

        # Show the visualized regions
        if self.debug_mode:
            cv2.imwrite("field_regions_debug.png", visualized_form)
            print("Debug image saved as 'field_regions_debug.png'")

    def _process_fields_using_manual_regions(self) -> None:
        """
        Processes fields using manually defined regions as a fallback.
        """
        for field_name, field_region in self.field_regions.items():
            self.information[field_name] = self._extract_field(field_region)    
