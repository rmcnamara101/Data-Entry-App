import cv2
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import Tuple
from backend.FormImagePreparer import RequestFormPreparer


@dataclass
class ImageAdjustments:
    brightness: int = 50
    contrast: int = 50
    threshold: int = 128

class ImagePreprocessor:
    @staticmethod
    def binarize_image(image: np.ndarray, threshold: int) -> np.ndarray:
        """
        Convert image to binary using the given threshold.
        
        Args:
            image: Input image in BGR format
            threshold: Threshold value for binarization
            
        Returns:
            Binary image
        """
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary_image = cv2.threshold(gray_image, threshold, 255, cv2.THRESH_BINARY)
        return binary_image

    @staticmethod
    def adjust_brightness_contrast(
        image: np.ndarray, 
        brightness: int = 0, 
        contrast: int = 0
    ) -> np.ndarray:
        """
        Adjust brightness and contrast of the image.
        
        Args:
            image: Input image
            brightness: Brightness value (0-100)
            contrast: Contrast value (0-100)
            
        Returns:
            Adjusted image
        """
        brightness = int((brightness - 50) * 2.55)
        contrast = int((contrast - 50) * 2.55)

        if contrast != 0:
            factor = 127 * (1 + contrast / 127) / (127 * (1 - contrast / 127))
            image = cv2.addWeighted(image, factor, image, 0, brightness - factor * 127)
        else:
            image = cv2.add(image, brightness)
        
        return np.clip(image, 0, 255).astype(np.uint8)

class ImageVisualizer:
    def __init__(self, window_name: str = "Image Visualizer"):
        self.window_name = window_name
        self.adjustments = ImageAdjustments()
        
    def _create_window(self) -> None:
        """Create window and trackbars."""
        cv2.namedWindow(self.window_name)
        
        # Add trackbars
        cv2.createTrackbar('Brightness', self.window_name, self.adjustments.brightness, 100, lambda x: None)
        cv2.createTrackbar('Contrast', self.window_name, self.adjustments.contrast, 100, lambda x: None)
        cv2.createTrackbar('Threshold', self.window_name, self.adjustments.threshold, 255, lambda x: None)
    
    def _get_trackbar_values(self) -> Tuple[int, int, int]:
        """Get current values from trackbars."""
        brightness = cv2.getTrackbarPos('Brightness', self.window_name)
        contrast = cv2.getTrackbarPos('Contrast', self.window_name)
        threshold = cv2.getTrackbarPos('Threshold', self.window_name)
        return brightness, contrast, threshold
    
    def _overlay_text(self, image: np.ndarray, values: Tuple[int, int, int]) -> np.ndarray:
        """Overlay adjustment values on the image."""
        brightness, contrast, threshold = values
        font = cv2.FONT_HERSHEY_SIMPLEX
        color = (0, 255, 0)
        thickness = 2
        
        text_params = [
            (f'Brightness: {brightness}', (10, 30)),
            (f'Contrast: {contrast}', (10, 60)),
            (f'Threshold: {threshold}', (10, 90))
        ]
        
        for text, position in text_params:
            cv2.putText(image, text, position, font, 0.8, color, thickness)
        
        return image

    def process_image(self, image: np.ndarray) -> np.ndarray:
        """Process the image with current adjustment values."""
        brightness, contrast, threshold = self._get_trackbar_values()
        
        # Only process if values have changed from default
        if brightness == 50 and contrast == 50 and threshold == 128:
            return image.copy()
        
        adjusted = ImagePreprocessor.adjust_brightness_contrast(image, brightness, contrast)
        binary = ImagePreprocessor.binarize_image(adjusted, threshold)
        return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

    def visualize(self, image: np.ndarray) -> None:
        """
        Main visualization loop.
        
        Args:
            image: Input image to visualize
        """
        self._create_window()
        
        while True:
            # Process image and overlay text
            display_image = self.process_image(image)
            display_image = self._overlay_text(display_image, self._get_trackbar_values())
            
            # Display the image
            cv2.imshow(self.window_name, display_image)
            
            # Check for 'q' key to quit
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        cv2.destroyAllWindows()

def main():
    # Load and process image
    image_path = 'scanned_forms/Screenshot 2024-11-17 at 10.52.12 PM.png'
  
    preparer = RequestFormPreparer(image_path)
    prepared_form = preparer.prepare_form()
    
    # Create visualizer and start processing
    visualizer = ImageVisualizer()
    visualizer.visualize(prepared_form)

if __name__ == "__main__":
    main()