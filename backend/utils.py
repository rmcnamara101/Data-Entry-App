from typing import Tuple, Optional
from dataclasses import dataclass

@dataclass
class FieldRegion:
    name: str
    coordinates: Tuple[int, int, int, int]
    validation_pattern: Optional[str] = None
    preprocessing_mode: str = 'default'

# Define all fields in one place
FIELD_REGIONS = {
    "request_number": FieldRegion("request_number", (775, 30, 1006, 125), None, 'numbers'),
    "given_names": FieldRegion("given_names", (280, 97, 470, 172), r'^[A-Za-z\s\-\']+$', 'text'),
    "surname": FieldRegion("surname", (24, 96, 166, 151), r'^[A-Za-z\s\-\']+$', 'text'),
    "date_of_birth": FieldRegion("Date of Birth", (655, 95, 788, 152), r'^\d{2}[/-]\d{2}[/-]\d{4}$', 'date'),
    "medicare_number": FieldRegion("Medicare Number", (540, 15, 788, 98), None, 'numbers'),
    "Phone Number": FieldRegion("Phone Number", (666, 149, 949, 292), None, 'numbers'),
    "address": FieldRegion("Address", (39, 145, 212, 213), None, 'text'),
    "doctor_information": FieldRegion("Doctor Information", (466, 538, 864, 684), None, 'text')
}

MEDICARE_RELATIVE_OFFSETS = {
    "Date of Birth": (126, -75, 150, 20),  # Corrected height
    "Given Name(s)": (-239, -75, 200, 20),  # Corrected width and height
    "Surname": (-504, -75, 200, 20),  # Corrected width and height
    "Address": (-504, -114, 300, 60),  # Corrected width and height
    "Doctor Information": (-22, -526, 357, 120),  # Corrected dimensions
    "Phone Number": (123, -116, 200, 40),  # Adjusted width and height
    "Request Date": (154, -451, 200, 20),  # Adjusted dimensions
    "Sex": (77, -75, 40, 20),  # Adjusted dimensions
}