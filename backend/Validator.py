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
        return bool(re.match(r'^\d{10}$', medicare_number))

    @staticmethod
    def is_valid_phone_number(phone_number: str) -> bool:
        """
        Validates the phone number format.

        Args:
            phone_number (str): The phone number to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
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

        if "medicare_number" in data:
            if not Validator.is_valid_medicare_number(data["medicare_number"]):
                errors["medicare_number"] = "Invalid Medicare Number format."

        if "home_phone_number" in data:
            if not Validator.is_valid_phone_number(data["home_phone_number"]):
                errors["home_phone_number"] = "Invalid Home Phone Number format."

        if "mobile_phone_number" in data:
            if not Validator.is_valid_phone_number(data["mobile_phone_number"]):
                errors["mobile_phone_number"] = "Invalid Mobile Phone Number format."

        if "request_number" in data:
            if not Validator.is_valid_request_number(data["request_number"]):
                errors["request_number"] = "Invalid Request Number format."

        if "provider_number" in data:
            if not Validator.is_valid_provider_number(data["provider_number"]):
                errors["provider_number"] = "Invalid Provider Number format."

        if "date_of_birth" in data:
            if not Validator.is_valid_date(data["date_of_birth"]):
                errors["date_of_birth"] = "Invalid Date of Birth format."

        if "request_date" in data:
            if not Validator.is_valid_date(data["request_date"]):
                errors["request_date"] = "Invalid Request Date format."

        return errors
