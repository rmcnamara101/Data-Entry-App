# constants.py

ALLOWED_CHARACTERS = {
    "medicare_number": r"[^0-9/]",
    "home_phone_number": r"[^0-9]",
    "mobile_phone_number": r"[^0-9]",
    "address": r"[^A-Za-z0-9\s]",
    "doctor_information": r"[^A-Za-z0-9]",
    "request_number": r"[^A-Za-z0-9]",
    "given_names": r"[^A-Za-z\s]",
}

COMMON_MISREADS = {
    "doctor_information": {'§': '5', '$': '5', 'O': '0', 'l': '1'},
}

POSTCODE_TO_STATE = {
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

STREET_TYPES = [
    "Street", "St", "Road", "Rd", "Avenue", "Ave", "Drive", "Dr",
    "Boulevard", "Blvd", "Lane", "Ln", "Terrace", "Terr", "Place",
    "Pl", "Court", "Ct",
]

OCR_CONFIGS = {
            "medicare_number": 6 ,
            "home_phone_number": 6,
            "mobile_phone_number": 7,
            "address": 6,
            "given_names": 6,
            "surname": 6,
            "sex": 10,
        }