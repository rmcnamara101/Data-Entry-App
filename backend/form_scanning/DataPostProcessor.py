from typing import Dict, Any, Optional
from datetime import datetime
import re
from backend.constants import ALLOWED_CHARACTERS, COMMON_MISREADS, POSTCODE_TO_STATE, STREET_TYPES

class DataPostProcessor:
    def __init__(self, debug_mode: bool = False) -> None:
        self.debug_mode = debug_mode

    def clean_text(self, field_name: str, text: str) -> str:
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
        elif field_name in ["home_phone", "mobile_phone"]:
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

        if self.debug_mode:
            print(f"Cleaned text for field '{field_name}': '{text}'")

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
            text = text.replace(wrong_char, correct_char)
        return text

    def split_address(self, full_address: str) -> Dict[str, Optional[str]]:
        """
        Splits the address into components: Address, Suburb, Postcode, and State.

        Args:
            full_address (str): The full address string extracted from the form.

        Returns:
            Dict[str, Optional[str]]: A dictionary with separate address components.
        """
        address_components = {"address": None, "suburb": None, "postcode": None, "state": None}

        # Extract postcode (assumed to be the last 4 digits)
        match = re.search(r'(\d{4})$', full_address.strip())
        if match:
            postcode = match.group(1)
            address_components["postcode"] = postcode
            full_address = full_address[:match.start()].strip()

            state = POSTCODE_TO_STATE.get(postcode[0], "Unknown")
            address_components["state"] = state

        # Tokenize the address
        tokens = full_address.split()
        street_type_index = self._find_street_type_index(tokens)

        if street_type_index is not None:
            address_components["address"] = ' '.join(tokens[:street_type_index + 1])
            address_components["suburb"] = ' '.join(tokens[street_type_index + 1:])
        else:
            # Fallback if no street type found
            address_components["address"] = ' '.join(tokens[:2]) if len(tokens) >= 2 else full_address
            address_components["suburb"] = ' '.join(tokens[2:]) if len(tokens) > 2 else None

        return address_components

    def _find_street_type_index(self, tokens: list) -> Optional[int]:
        """
        Finds the index of the street type in the address tokens.

        Args:
            tokens (list): Tokenized address.

        Returns:
            Optional[int]: Index of the street type or None if not found.
        """
        for i, token in enumerate(tokens):
            clean_token = token.strip(",.").capitalize()
            if clean_token in STREET_TYPES:
                return i
        return None

    def parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parses a date string into a datetime object.

        Args:
            date_str (str): The date string to parse.

        Returns:
            Optional[datetime]: The parsed datetime object or None if invalid.
        """
        try:
            return datetime.strptime(date_str, '%d/%m/%Y')
        except ValueError:
            return None

    def process_phone_numbers(self, phone_field: str) -> Dict[str, Optional[str]]:
        """
        Processes the 'phone_number' field to extract Home and Mobile phone numbers.

        Args:
            phone_field (str): The concatenated phone number field.

        Returns:
            Dict[str, Optional[str]]: Extracted home and mobile phone numbers.
        """
        phone_numbers = {"home_phone": None, "mobile_phone": None}

        if not phone_field:
            return phone_numbers

        # Use regex to find all phone numbers and their labels
        phone_matches = re.findall(r'(\d+)\((H|M)\)', phone_field)

        for number, label in phone_matches:
            number = re.sub(r'[^\d+]', '', number).strip()
            if label.upper() == 'H':
                phone_numbers["home_phone"] = number
            elif label.upper() == 'M':
                phone_numbers["mobile_phone"] = number

        return phone_numbers
