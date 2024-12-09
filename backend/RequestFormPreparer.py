import cv2
import numpy as np
from typing import Tuple
from dataclasses import dataclass

class RequestFormPreparer:
    def __init__(self, image_path: str, debug_mode: bool = False) -> None:
        self.image_path = image_path
        self.image = self._load_image(image_path)
        self.debug_mode = debug_mode

    def _load_image(self, image_path: str) -> np.ndarray:
        image = cv2.imread(image_path)
        if image is None:
            raise FileNotFoundError(f"Could not load image at {image_path}")
        return image

    def prepare_form(self, target_size: Tuple[int, int] = (1024, 768)) -> np.ndarray:
        cropped_image = self.crop_to_content(self.image)
        prepared_image = self.scale_image(cropped_image, target_size)        
        return prepared_image

    def crop_to_content(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Attempt 1: Otsu thresholding
        # This often works well for documents with clear text.
        _, otsu_thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        contours, _ = cv2.findContours(otsu_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            # Attempt 2: Adaptive Thresholding (as before)
            adaptive_thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                cv2.THRESH_BINARY_INV, blockSize=15, C=10
            )

            contours, _ = cv2.findContours(adaptive_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            # Attempt 3: Use morphological operations to highlight text regions further
            # For example, try a morphological top-hat to isolate bright text on darker backgrounds
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            tophat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)
            _, morph_thresh = cv2.threshold(tophat, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            contours, _ = cv2.findContours(morph_thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            # No text regions found with these methods
            print("No text regions found after multiple attempts. Returning original image.")
            return image

        # Compute the bounding rectangle of all contours
        all_contours = np.vstack(contours)
        x, y, w, h = cv2.boundingRect(all_contours)

        # Add padding
        padding = 20
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(image.shape[1] - x, w + 2 * padding)
        h = min(image.shape[0] - y, h + 2 * padding)

        if self.debug_mode:
            debug_image = image.copy()
            cv2.rectangle(debug_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.imshow('Cropped Form', debug_image)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        cropped_image = image[y:y + h, x:x + w]
        return cropped_image

    def scale_image(self, image: np.ndarray, target_size: Tuple[int, int],
                    interpolation: int = cv2.INTER_AREA) -> np.ndarray:
        return cv2.resize(image, target_size, interpolation=interpolation)