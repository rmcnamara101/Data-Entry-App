import re
import pytesseract
import cv2
import numpy as np
from typing import Any, Tuple 

class TextProcessor:
    def __init__(self):
        # Verify Tesseract is working
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            print(f"Tesseract initialization error: {e}")
            print("Please ensure Tesseract is properly installed")
            
    def extract_text(self, image: Any, lang: str = "eng", psm: int = 6) -> Tuple[str, float]:
        """
        Extracts text from an image using Tesseract OCR with customizable parameters.

        Args:
            image (Any): Image to process.
            lang (str): Language for OCR.
            psm (int): Page Segmentation Mode.
            **kwargs (Any): Additional Tesseract configurations.

        Returns:
            Tuple[str, float]: Extracted text and confidence score.
        """
        # Prepare OCR configuration
        custom_config = f"--psm {psm} -l {lang} --oem 3"

        # Perform OCR
        ocr_result = pytesseract.image_to_data(image, config=custom_config, output_type=pytesseract.Output.DICT)
        text = " ".join(ocr_result["text"]).strip()
        confidences = [int(c) for c, t in zip(ocr_result["conf"], ocr_result["text"]) if t.strip() and int(c) >= 0]
        confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return text, confidence
            