from typing import Tuple, Optional
from dataclasses import dataclass

@dataclass
class FieldRegion:
    name: str
    coordinates: Tuple[int, int, int, int]
    validation_pattern: Optional[str] = None
    preprocessing_mode: str = 'default'
    primary_field: Optional[str] = None

# Define all fields in one place
FIELD_REGIONS = {
    "given_names": FieldRegion("given_names", (280, 97, 470, 172), r'^[A-Za-z\s\-\']+$', 'text'),
    "surname": FieldRegion("surname", (24, 96, 166, 151), r'^[A-Za-z\s\-\']+$', 'text'),
    "date_of_birth": FieldRegion("Date of Birth", (655, 95, 788, 152), r'^\d{2}[/-]\d{2}[/-]\d{4}$', 'date'),
    "medicare_number": FieldRegion("Medicare Number", (540, 15, 788, 98), None, 'numbers'),
    "medicare_position": FieldRegion("Medicare Position", (540, 15, 788, 98), None, 'numbers', primary_field="medicare_number"),
    "phone_number": FieldRegion("Phone Number", (666, 149, 949, 292), None, 'numbers'),
    "mobile_phone": FieldRegion("Mobile Phone", (666, 149, 949, 292), None, 'numbers', primary_field="phone_number"),
    "home_phone": FieldRegion("Home Phone", (666, 149, 949, 292), None, 'numbers', primary_field="phone_number"),
    "address": FieldRegion("Address", (39, 145, 212, 213), None, 'text'),
    "suburb": FieldRegion("Suburb", (39, 145, 212, 213), None, 'text', primary_field="address"),
    "postcode": FieldRegion("Postcode", (39, 145, 212, 213), None, 'text', primary_field="address"),
    "state": FieldRegion("State", (39, 145, 212, 213), None, 'text', primary_field="address"),
    "doctor_information": FieldRegion("Doctor Information", (466, 538, 864, 684), None, 'text'),
    "sex": FieldRegion("Sex", (617, 80, 828, 128), r'^[MFU]$', 'text'),
    "request_date": FieldRegion("Request Date", (666, 450, 949, 629)),
    "provider_number": FieldRegion("Provider Number", (466, 538, 864, 684), None, 'numbers', primary_field="doctor_information")
}




MEDICARE_RELATIVE_OFFSETS = {
    # Field: (x1, y1, width, height)
    "date_of_birth": (126, -65, 150, 30),  # Corrected height
    "given_names": (-239, -65, 200, 30),  # Corrected width and height
    "surname": (-498, -62, 200, 40),  # Corrected width and height
    "address": (-504, -104, 300, 70),  # Corrected width and height
    "doctor_information": (-22, -516, 357, 130),  # Corrected dimensions
    "phone_number": (123, -116, 200, 60),  # Adjusted width and height
    "request_date": (154, -431, 200, 30),  # Adjusted dimensions
    "sex": (77, -65, 40, 30),  # Adjusted dimensions
}