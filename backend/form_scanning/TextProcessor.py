import re
import pytesseract
import cv2
import numpy as np
from typing import Any, Tuple, Union, Dict

class TextProcessor:
    def __init__(self):
        self.ocr_result = None
        # Verify Tesseract is working
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            print(f"Tesseract initialization error: {e}")
            print("Please ensure Tesseract is properly installed")

    def extract_text(
        self,
        image: Any,
        lang: str = "eng",
        psm: int = 6,
        config: Union[str, Dict, None] = None
    ) -> Tuple[str, float]:
        """
        Extracts text from an image using Tesseract OCR with customizable parameters.

        Args:
            image (Any): Image to process (BGR, RGB, or Grayscale).
            lang (str): Language for OCR.
            psm (int): Page Segmentation Mode.
            config (str or dict, optional): 
                - If string, treated as extra Tesseract command-line flags (unchanged from before).  
                - If dict, may contain:
                    {
                      "tesseract_config": "<extra Tesseract flags>",
                      "threshold_type": "otsu" | "binary" | "binary_inv" | "adaptive_gaussian" | "adaptive_mean",
                      "threshold_value": <int>,
                      "block_size": <int>,
                      "c_val": <int>
                    }
                - If None, no special config is used.

        Returns:
            Tuple[str, float]: Extracted text and approximate confidence score.
        """

        # 1. Handle config for thresholding vs. Tesseract flags
        threshold_type = "otsu"
        threshold_value = 128
        block_size = 21
        c_val = 5
        tesseract_flags = ""

        if config is None:
            # No thresholding, no extra Tesseract config
            tesseract_flags = ""
        elif isinstance(config, str):
            # Old style: a string for Tesseract
            tesseract_flags = config
        elif isinstance(config, dict):
            # If there's a separate Tesseract config key
            tesseract_flags = config.get("tesseract_config", "")

            # If threshold_type is provided, we do thresholding
            if "threshold_type" in config:
                threshold_type = config["threshold_type"]
                threshold_value = config.get("threshold_value", 128)
                block_size = config.get("block_size", 21)
                c_val = config.get("c_val", 5)

        # 2. If threshold_type is not None, apply threshold
        if threshold_type is not None:
            image = self._apply_threshold(
                image,
                threshold_type,
                threshold_value,
                block_size,
                c_val
            )

        # 3. Build the final Tesseract config string
        #    --psm X, -l <lang>, --oem 3 are always included
        custom_config = f"{tesseract_flags} --psm {psm} -l {lang} --oem 3".strip()

        # 4. Perform OCR
        self.ocr_result = pytesseract.image_to_data(
            image,
            config=custom_config,
            output_type=pytesseract.Output.DICT
        )

        # 5. Combine recognized words into a single string
        text = " ".join(self.ocr_result["text"]).strip()

        # 6. Compute approximate confidence
        #    (Ignore entries with conf == -1 or blank text)
        confidences = []
        for c, t in zip(self.ocr_result["conf"], self.ocr_result["text"]):
            t = t.strip()
            if t and c >= 0:  # c is already an int, so just compare numerically
                confidences.append(c)
        confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return text, confidence

    def get_ocr_result(self):
        """
        Returns the most recent OCR result dictionary produced by extract_text().
        """
        return self.ocr_result

    def _apply_threshold(
        self,
        image: np.ndarray,
        threshold_type: str,
        threshold_value: int,
        block_size: int,
        c_val: int
    ) -> np.ndarray:
        """
        Applies different thresholding methods to an input image and returns the thresholded result.

        Args:
            image (np.ndarray): Image on which to apply thresholding.
            threshold_type (str): One of ["binary", "binary_inv", "otsu", "adaptive_gaussian", "adaptive_mean"].
            threshold_value (int): Threshold value (0–255) for simple binary thresholds.
            block_size (int): Block size for adaptive thresholding (odd number).
            c_val (int): Constant subtracted from the mean or weighted mean in adaptive thresholding.

        Returns:
            np.ndarray: Thresholded image.
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3 and image.shape[2] == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        if threshold_type == "binary":
            _, thresh = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)
        elif threshold_type == "binary_inv":
            _, thresh = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY_INV)
        elif threshold_type == "otsu":
            # Otsu automatically finds the best threshold
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        elif threshold_type == "adaptive_gaussian":
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, block_size, c_val
            )
        elif threshold_type == "adaptive_mean":
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                cv2.THRESH_BINARY, block_size, c_val
            )
        else:
            # Default fallback
            _, thresh = cv2.threshold(gray, threshold_value, 255, cv2.THRESH_BINARY)

        return thresh
