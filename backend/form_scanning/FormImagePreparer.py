import cv2
import numpy as np
from typing import Tuple
from dataclasses import dataclass

class FormImagePreparer:
    def __init__(self, debug_mode: bool = False) -> None:
        pass

    def _load_image(self, image_path: str) -> np.ndarray:
        image = cv2.imread(image_path)
        if image is None:
            raise FileNotFoundError(f"Could not load image at {image_path}")
        return image

    def prepare_form(self, file_path, target_size: Tuple[int, int] = (1024, 768)) -> np.ndarray:
        img = self._load_image(file_path)

        cropped_image = self.crop_to_content(img)
        prepared_image = self.scale_image(cropped_image, target_size)        
        return prepared_image

    def crop_to_content(self, image: np.ndarray) -> np.ndarray:
        """
        Crops the image to its content area using contours. Focuses on minimal processing to avoid
        interfering with OCR accuracy.
        
        Args:
            image (np.ndarray): Input image to crop.

        Returns:
            np.ndarray: Cropped image containing the main content.
        """
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Otsu thresholding for basic binarization
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Find external contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            # If no contours are found, return the original image
            print("No significant contours found. Returning original image.")
            return image

        # Compute the bounding rectangle for all contours
        all_contours = np.vstack(contours)
        x, y, w, h = cv2.boundingRect(all_contours)

        # Add padding to ensure no content is cropped too tightly
        padding = 20
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(image.shape[1] - x, w + 2 * padding)
        h = min(image.shape[0] - y, h + 2 * padding)

        # Crop the image
        cropped_image = image[y:y + h, x:x + w]

        # Debug visualization
        #if self.debug_mode:
        #    debug_image = image.copy()
        #    cv2.rectangle(debug_image, (x, y), (x + w, y + h), (0, 255, 0), 2)
        #    cv2.imshow("Cropped Region", debug_image)
        #    cv2.waitKey(0)

        return cropped_image


    def scale_image(self, image: np.ndarray, target_size: Tuple[int, int],
                    interpolation: int = cv2.INTER_AREA) -> np.ndarray:
        return cv2.resize(image, target_size, interpolation=interpolation)