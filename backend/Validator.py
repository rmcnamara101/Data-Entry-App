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
        
        print(phone_number)
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
        print("Starting validation...")  # Debug

        if "medicare_number" in data:
            print(f"Validating Medicare Number: {data.get('medicare_number')}")  # Debug
            if data["medicare_number"] is None or not Validator.is_valid_medicare_number(data["medicare_number"][0]):
                errors["medicare_number"] = "Invalid Medicare Number format."

        if "home_phone_number" in data:
            print(f"Validating Home Phone Number: {data.get('home_phone_number')}")  # Debug
            if data["home_phone_number"] is None or not Validator.is_valid_phone_number(data["home_phone_number"][0]):
                errors["home_phone_number"] = "Invalid Home Phone Number format."

        if "mobile_phone_number" in data:
            print(f"Validating Mobile Phone Number: {data.get('mobile_phone_number')}")  # Debug
            if data["mobile_phone_number"] is None or not Validator.is_valid_phone_number(data["mobile_phone_number"][0]):
                errors["mobile_phone_number"] = "Invalid Mobile Phone Number format."

        if "provider_number" in data:
            print(f"Validating Provider Number: {data.get('provider_number')}")  # Debug
            if data["provider_number"] is None or not Validator.is_valid_provider_number(data["provider_number"][0]):
                errors["provider_number"] = "Invalid Provider Number format."

        if "date_of_birth" in data:
            print(f"Validating Date of Birth: {data.get('date_of_birth')}")  # Debug
            if data["date_of_birth"] is None or not Validator.is_valid_date(data["date_of_birth"][0]):
                errors["date_of_birth"] = "Invalid Date of Birth format."

        if "request_date" in data:
            print(f"Validating Request Date: {data.get('request_date')}")  # Debug
            if data["request_date"] is None or not Validator.is_valid_date(data["request_date"][0]):
                errors["request_date"] = "Invalid Request Date format."

        print(f"Validation errors: {errors}")  # Debug
        return errors

