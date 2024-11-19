from dataclasses import dataclass
from typing import Optional, Any, Dict, Tuple, List
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
    "Home Phone Number": r"[^0-9]",      # Allow digits only
    "Mobile Phone Number": r"[^0-9]",    # Allow digits only
    "Address": r"[^A-Za-z0-9\s]",   # Allow letters, numbers, and spaces
    "Doctor Information": r"[^A-Za-z0-9]",  # Allow letters and numbers
    "Request Number": r"[^A-Za-z0-9]",      # Allow letters and digits
    "Given Name(s)": r"[^A-Za-z\s]",        # Allow letters and spaces (modified to exclude quotes)
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
        self.textprocessor = TextProcessor()
        self.medicare_detector = MedicareDetector(debug_mode=debug_mode)
        self.information = {
            "Request Number": None,
            "Request Date": None,
            "Given Names": None,
            "Surname": None,
            "Date of Birth": None,
            "Medicare Number": None,
            "Medicare Position": None,
            "Home Phone Number": None,
            "Mobile Phone Number": None,
            "Address": None,
            "Suburb": None,
            "Postcode": None,
            "State": None,
            "Doctor Information": None,
            "Provider Number": None,
            "OCR Confidence": None  # New field for overall OCR confidence
        }

    def process_form(self) -> Dict[str, Any]:
        """
        Processes all fields in the form using defined configurations in FIELD_REGIONS.

        Returns:
            Dict[str, Any]: Extracted and processed information from the form.
        """
        # Initialize a list to collect individual field confidences
        field_confidences = []

        # Step 1: Try using the Medicare anchor method
        medicare_anchor = self.medicare_detector.find_medicare_number(self.requestform)

        if medicare_anchor:
            if self.debug_mode:
                print(f"Medicare anchor detected: {medicare_anchor}")
            self._process_fields_using_anchor(medicare_anchor, field_confidences)
        else:
            if self.debug_mode:
                print("Medicare anchor not detected. Falling back to manual regions.")
            self._process_fields_using_manual_regions(field_confidences)

        # Post-processing specific fields

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

        # 3. Phone Number Cleanup and Assignment
        home_phone, mobile_phone = self._process_phone_numbers()
        self.information["Home Phone Number"] = home_phone
        self.information["Mobile Phone Number"] = mobile_phone

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

        # 6. Given Names Cleanup
        if self.information.get("Given Names"):
            given_names = self.information["Given Names"]
            # Remove any text within quotes to extract the primary given name
            given_names = re.sub(r'\".*?\"', '', given_names).strip()
            self.information["Given Names"] = given_names

        # 7. Calculate Overall OCR Confidence
        if field_confidences:
            overall_confidence = sum(field_confidences) / len(field_confidences)
            self.information["OCR Confidence"] = round(overall_confidence, 2)
        else:
            self.information["OCR Confidence"] = None

        validation_errors = {}

        # Validate Medicare Number
        medicare_number = self.information.get("Medicare Number")
        if medicare_number:
            if not self.is_valid_medicare_number(medicare_number):
                validation_errors["Medicare Number"] = "Invalid Medicare Number format."

        # Validate Phone Numbers
        home_phone = self.information.get("Home Phone Number")
        mobile_phone = self.information.get("Mobile Phone Number")
        if home_phone:
            if not self.is_valid_phone_number(home_phone):
                validation_errors["Home Phone Number"] = "Invalid Home Phone Number format."
        if mobile_phone:
            if not self.is_valid_phone_number(mobile_phone):
                validation_errors["Mobile Phone Number"] = "Invalid Mobile Phone Number format."

        # Validate Request Number
        request_number = self.information.get("Request Number")
        if request_number:
            if not self.is_valid_request_number(request_number):
                validation_errors["Request Number"] = "Invalid Request Number format."

        # Validate Overall OCR Confidence
        if self.information["OCR Confidence"] is not None:
            if self.information["OCR Confidence"] < 70.0:  # Threshold can be adjusted
                validation_errors["OCR Confidence"] = "Overall OCR confidence is low."

        

        return {
            "data": self.information,
            "validation_errors": validation_errors
        }

    def _extract_field(self, field_region) -> Optional[Tuple[str, float]]:
        """
        Extracts and validates text from a specific field region.

        Args:
            field_region: The FieldRegion object defining the region and validation.

        Returns:
            Extracted and validated text along with its confidence, or (None, 0.0) if validation fails.
        """
        # Get the image region
        region = self._get_region(field_region.coordinates)

        # Extract text using TextProcessor
        text, confidence = self.textprocessor.extract_text(region)

        # Debugging extracted text
        if self.debug_mode:
            print(f"Raw text for {field_region.name}: {text} (Confidence: {confidence})")

        # Clean extracted text
        text = self._clean_text(field_region.name, text)

        # Validate text if a pattern is defined
        if field_region.validation_pattern and not self._validate_text(field_region.validation_pattern, text):
            if self.debug_mode:
                print(f"Validation failed for {field_region.name}: {text}")
            return (None, 0.0)

        return (text.strip(), confidence)

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
        elif field_name in ["Home Phone Number", "Mobile Phone Number"]:
            text = re.sub(r'\D+', '', text)  # Remove non-digit characters
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

    def _process_fields_using_anchor(self, medicare_anchor: MedicareAnchor, field_confidences: List[float]) -> None:
        """
        Processes fields based on the detected Medicare anchor using relative positions.
        Visualizes the bounding boxes for debugging.

        Args:
            medicare_anchor: The detected Medicare anchor object containing its bounding box.
            field_confidences: List to collect individual field confidences.
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
            cleaned_text = self._clean_text(field_name, text)
            self.information[field_name] = cleaned_text
            field_confidences.append(confidence)

        # Show the visualized regions
        if self.debug_mode:
            cv2.imwrite("field_regions_debug.png", visualized_form)
            print("Debug image saved as 'field_regions_debug.png'")

    def _process_fields_using_manual_regions(self, field_confidences: List[float]) -> None:
        """
        Processes fields using manually defined regions as a fallback.

        Args:
            field_confidences: List to collect individual field confidences.
        """
        for field_name, field_region in self.field_regions.items():
            text, confidence = self._extract_field(field_region)
            self.information[field_name] = text
            field_confidences.append(confidence)

    def _process_phone_numbers(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Processes the 'Phone Number' field to extract and assign Home and Mobile phone numbers.

        Returns:
            A tuple containing (home_phone, mobile_phone)
        """
        phone_field = self.information.get("Phone Number")
        home_phone = None
        mobile_phone = None

        if phone_field:
            # Split the phone field by common separators
            phone_entries = re.split(r'\n|/', phone_field)
            phone_entries = [entry.strip() for entry in phone_entries if entry.strip()]

            for entry in phone_entries:
                # Check for labels (H) or (M)
                match = re.match(r'(\d{10})\s*\(?([HMhm]?)\)?', entry)
                if match:
                    number = match.group(1)
                    label = match.group(2).upper()

                    if label == 'H':
                        home_phone = number
                    elif label == 'M':
                        mobile_phone = number
                    else:
                        # If no label, assign based on availability
                        if not home_phone:
                            home_phone = number
                        elif not mobile_phone:
                            mobile_phone = number
                        else:
                            # If both are already assigned and the numbers are identical, skip
                            if number != home_phone and number != mobile_phone:
                                # Decide how to handle additional numbers; for now, skip
                                pass

            # Handle cases with only one number without labels
            if not home_phone and phone_entries:
                home_phone = phone_entries[0]
                if len(phone_entries) > 1:
                    mobile_phone = phone_entries[1]
        
        return home_phone, mobile_phone

    def is_valid_medicare_number(self, medicare_number: str) -> bool:
        # Medicare number should be 10 digits followed by a '/' and a digit
        return bool(re.match(r'^\d{10}/\d$', medicare_number))

    def is_valid_phone_number(self, phone_number: str) -> bool:
        # Phone number should be 10 digits
        return bool(re.match(r'^\d{10}$', phone_number))

    def is_valid_request_number(self, request_number: str) -> bool:
        # Request number should match '24H' followed by 5 digits
        return bool(re.match(r'^24H\d{5}$', request_number))