import cv2
import numpy as np
from MedicareAnchorDetector import MedicareDetector  # Ensure this class handles anchor detection
from TextProcessor import TextProcessor  # Ensure this class is used for OCR

def calculate_relative_offsets(image_path: str, debug_mode: bool = True):
    """
    Detects the Medicare anchor and calculates its bounding box dimensions and position.

    Args:
        image_path (str): Path to the form image.
        debug_mode (bool): If True, enables debugging and visualization.

    Returns:
        None
    """
    # Load the image
    image = cv2.imread(image_path)
    if image is None:
        print("Error: Could not load image.")
        return

    # Initialize Medicare anchor detector
    detector = MedicareDetector(debug_mode=debug_mode)

    # Find Medicare anchor
    medicare_anchor = detector.find_medicare_number(image)
    if not medicare_anchor:
        print("Medicare number not found.")
        return
    print(medicare_anchor.text)
    # Medicare anchor bounding box and position
    anchor_x1, anchor_y1, anchor_x2, anchor_y2 = medicare_anchor.bounding_box
    anchor_width = anchor_x2 - anchor_x1
    anchor_height = anchor_y2 - anchor_y1

    print(f"Medicare Anchor Detected:")
    print(f" - Position: (x1: {anchor_x1}, y1: {anchor_y1}, x2: {anchor_x2}, y2: {anchor_y2})")
    print(f" - Dimensions: Width = {anchor_width}px, Height = {anchor_height}px")

    # Visualize the bounding box on the image
    if debug_mode:
        annotated_image = image.copy()
        cv2.rectangle(
            annotated_image, 
            (anchor_x1, anchor_y1), 
            (anchor_x2, anchor_y2), 
            (0, 255, 0), 
            2
        )
        cv2.putText(
            annotated_image, 
            "Medicare Anchor", 
            (anchor_x1, anchor_y1 - 10), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.5, 
            (0, 255, 0), 
            1
        )
        cv2.imshow("Medicare Anchor Detection", annotated_image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    # Calculate relative offsets
    print("\nRelative Offset Calculation:")
    print("Use these bounding box dimensions to calculate offsets for other fields:")
    print("1. Measure the x and y offset relative to the top-left corner of the anchor.")
    print("2. Use the width and height as reference dimensions for other fields.")

# Example usage
if __name__ == "__main__":
    # Replace with your form image path
    form_image_path = "Patient_Entry_Project/scanned_forms/prepared_form.jpg"
    calculate_relative_offsets(form_image_path)