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
    "Request Number": FieldRegion("Request Number", (775, 30, 1006, 125), None, 'numbers'),
    "Given Name(s)": FieldRegion("Given Name(s)", (280, 97, 470, 172), r'^[A-Za-z\s\-\']+$', 'text'),
    "Surname": FieldRegion("Surname", (24, 96, 166, 151), r'^[A-Za-z\s\-\']+$', 'text'),
    "Date of Birth": FieldRegion("Date of Birth", (655, 95, 788, 152), r'^\d{2}[/-]\d{2}[/-]\d{4}$', 'date'),
    "Medicare Number": FieldRegion("Medicare Number", (540, 15, 788, 98), None, 'numbers'),
    "Phone Number": FieldRegion("Phone Number", (666, 149, 949, 292), None, 'numbers'),
    "Address": FieldRegion("Address", (39, 145, 212, 213), None, 'text'),
    "Doctor Information": FieldRegion("Doctor Information", (466, 538, 864, 684), None, 'text')
}