"""

Request Form Scaler

Created by Riley McNamara 15/11/24

The aim of this program is to prepare an image for the request form processor.
Adjust the levels of the image to optimise for extracting printed information.


"""

import cv2
import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass

@dataclass
class ColorRange:
    """
    Defines HSV color range for border detection
    """
    lower: np.ndarray
    upper: np.ndarray

class RequestFormPreparer:
    """
    A class to prepare scanned request forms for information extraction.
    Handles image preprocessing including border detection, cropping, and enhancement.
    """

    COLOR_RANGES = {
        'blue': ColorRange(
            lower=np.array([80, 5, 80]),
            upper=np.array([100, 30, 255])
        ),
        'black': ColorRange(
            lower=np.array([0, 0, 0]),
            upper=np.array([180, 255, 30])
        )
    }

    def __init__(self, image_path: str) -> None:
        """
        Initialize the RequestFormPreparer with an image path.

        Args:
            image_path (str): Path to the image file
        
        Raises:
            FileNotFoundError: If the image file doesn't exist
            ValueError: If the image can't be read properly
        """
        self.image_path = image_path
        self.image = self._load_image(image_path)
        
    def _load_image(self, image_path: str) -> np.ndarray:
        """
        Safely load an image file.
        
        Args:
            image_path (str): Path to the image file
            
        Returns:
            np.ndarray: Loaded image
            
        Raises:
            FileNotFoundError: If the image file doesn't exist
            ValueError: If the image can't be read properly
        """
        image = cv2.imread(image_path)
        if image is None:
            raise FileNotFoundError(f"Could not load image at {image_path}")
        return image

    def prepare_form(self, 
                    target_size: Tuple[int, int] = (1024, 768),
                    border_color: str = 'blue') -> np.ndarray:
        """
        Process the form image through the complete preparation pipeline.

        Args:
            target_size (Tuple[int, int]): Desired output image size
            border_color (str): Color of the form border to detect
            saturation_boost (int): Amount to boost saturation (0-255)

        Returns:
            np.ndarray: Processed image
            
        Raises:
            ValueError: If border_color is not supported
        """
        if border_color not in self.COLOR_RANGES:
            raise ValueError(f"Unsupported border color. Supported colors: {list(self.COLOR_RANGES.keys())}")

        # Process image through pipeline
        cropped_image = self.crop_to_border(self.image, border_color)
        prepared_image = self.scale_image(cropped_image, target_size)
        
        return prepared_image

    def crop_to_border(self, 
                      image: np.ndarray, 
                      border_color: str,
                      min_contour_area: float = 1000.0) -> np.ndarray:
        """
        Crop the image to the detected border of specified color.

        Args:
            image (np.ndarray): Input image
            border_color (str): Color of border to detect
            min_contour_area (float): Minimum area for valid border detection

        Returns:
            np.ndarray: Cropped image
        """
        # Convert to HSV color space
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Get color range for specified border
        color_range = self.COLOR_RANGES[border_color]
        
        # Create mask for the specified color
        mask = cv2.inRange(hsv_image, color_range.lower, color_range.upper)
        
        # Apply morphological operations to clean up the mask
        kernel = np.ones((3,3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            print(f"No {border_color} border found. Returning original image.")
            return image

        # Find the largest contour above minimum area
        valid_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_contour_area]
        if not valid_contours:
            print(f"No valid {border_color} border found. Returning original image.")
            return image
            
        largest_contour = max(valid_contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        # Add small padding to avoid cutting off border
        padding = 5
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(image.shape[1] - x, w + 2*padding)
        h = min(image.shape[0] - y, h + 2*padding)
        
        return image[y:y+h, x:x+w]


    def scale_image(self, 
                   image: np.ndarray, 
                   target_size: Tuple[int, int],
                   interpolation: int = cv2.INTER_AREA) -> np.ndarray:
        """
        Scale the image to the target size.

        Args:
            image (np.ndarray): Input image
            target_size (Tuple[int, int]): Desired output size (width, height)
            interpolation (int): OpenCV interpolation method

        Returns:
            np.ndarray: Resized image
        """
        return cv2.resize(image, target_size, interpolation=interpolation)