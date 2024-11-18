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
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply adaptive thresholding to binarize the image
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
            cv2.THRESH_BINARY_INV, blockSize=15, C=10
        )

        # Dilate to merge text regions
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        dilated = cv2.dilate(thresh, kernel, iterations=1)

        # Find contours
        contours, _ = cv2.findContours(
            dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            print("No text regions found. Returning original image.")
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
            # Draw the bounding box on the image for visualization
            debug_image = image.copy()
            cv2.rectangle(debug_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.imshow('Cropped Form', debug_image)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

        # Crop and return the image
        cropped_image = image[y:y + h, x:x + w]

        return cropped_image

    def scale_image(self, image: np.ndarray, target_size: Tuple[int, int],
                    interpolation: int = cv2.INTER_AREA) -> np.ndarray:
        return cv2.resize(image, target_size, interpolation=interpolation)