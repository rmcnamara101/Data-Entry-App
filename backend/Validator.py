import re
from datetime import datetime

class Validator:
    """
    Provides validation utilities for extracted data fields.
    """

    @staticmethod
    def is_valid_medicare_number(medicare_number: str) -> bool:
        """
        Validates the Medicare number format.

        Args:
            medicare_number (str): The Medicare number to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
        if medicare_number is None:
            return False
        return bool(re.match(r'^\d{10}$', medicare_number))
    
    @staticmethod
    def is_valid_medicare_position(medicare_position: str) -> bool:
        """
        Validates the Medicare position format.

        Args:
            medicare_position (str): The Medicare position to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
        if medicare_position is None:
            return False
        return bool(re.match(r'^[1-9]$', medicare_position))

    @staticmethod
    def is_valid_phone_number(phone_number: str) -> bool:
        """
        Validates the phone number format.

        Args:
            phone_number (str): The phone number to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
        if phone_number is None:
            return False
    
        return bool(re.match(r'^\d{10}$', phone_number))

    @staticmethod
    def is_valid_request_number(request_number: str) -> bool:
        """
        Validates the request number format.

        Args:
            request_number (str): The request number to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
        if request_number is None:
            return False
        return bool(re.match(r'^24H\d{5}$', request_number))

    @staticmethod
    def is_valid_provider_number(provider_number: str) -> bool:
        """
        Validates the provider number format.

        Args:
            provider_number (str): The provider number to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
        if provider_number is None:
            return False
        return bool(re.match(r'^[A-Za-z0-9]{8}$', provider_number))

    @staticmethod
    def is_valid_date(date_str: str, date_format: str = '%d/%m/%Y') -> bool:
        """
        Validates if a date string matches the expected format.

        Args:
            date_str (str): The date string to validate.
            date_format (str): The expected date format. Default is '%d/%m/%Y'.

        Returns:
            bool: True if valid, False otherwise.
        """
        if date_str is None:
            return False
        try:
            datetime.strptime(date_str, date_format)
            return True
        except ValueError:
            return False

    @staticmethod
    def validate_data(data: dict) -> dict:
        """
        Validates a dictionary of extracted data fields.

        Args:
            data (dict): The dictionary of data fields to validate.

        Returns:
            dict: A dictionary containing validation results (field: error message or None).
        """
        errors = {}

        # Validate OCR confidence for individual fields
        for field, value in data.items():
            if value is not None and len(value) > 1:  # Ensure value is a tuple with confidence
                field_value, confidence, _ = value
                if confidence < 70:
                    errors[field] = f"OCR confidence for '{field}' is too low: {confidence}. Must be at least 70."

        # Field-specific validation logic
        if "medicare_number" in data:
            if data["medicare_number"] is None or not Validator.is_valid_medicare_number(data["medicare_number"][0]):
                errors["medicare_number"] = "Invalid Medicare Number format."

        if "mobile_phone" in data:
            if data["mobile_phone"] is None or not Validator.is_valid_phone_number(data["mobile_phone"][0]):
                errors["mobile_phone"] = "Invalid Mobile Phone Number format."

        if "provider_number" in data:
            if data["provider_number"] is None or not Validator.is_valid_provider_number(data["provider_number"][0]):
                errors["provider_number"] = "Invalid Provider Number format."

        if "date_of_birth" in data:
            if data["date_of_birth"] is None or not Validator.is_valid_date(data["date_of_birth"][0]):
                errors["date_of_birth"] = "Invalid Date of Birth format."

        if "request_date" in data:
            if data["request_date"] is None or not Validator.is_valid_date(data["request_date"][0]):
                errors["request_date"] = "Invalid Request Date format."

        if "medicare_position" in data:
            if data["medicare_position"] is None or not Validator.is_valid_medicare_position(data["medicare_position"][0]):
                errors["medicare_position"] = "Invalid Medicare Position format."

        return errors
