#!/usr/bin/env python3

import argparse
import cv2
import numpy as np
import sys

# Update this import as needed to point to your actual MedicareDetector implementation
from backend.form_scanning.MedicareAnchorDetector import MedicareDetector

def main():
    parser = argparse.ArgumentParser(description="Experiment with thresholding and run MedicareDetector.")
    parser.add_argument("image_path", help="Path to the image you want to test")
    parser.add_argument("--threshold_value", type=int, default=128, help="Threshold value (0-255)")
    parser.add_argument(
        "--threshold_type", 
        choices=["binary", "binary_inv", "otsu", "adaptive_gaussian", "adaptive_mean"], 
        default="binary", 
        help="Type of threshold to apply"
    )
    parser.add_argument("--debug_mode", action="store_true", help="Enable debug mode in MedicareDetector")
    args = parser.parse_args()

    # 1. Load the image
    image = cv2.imread(args.image_path)
    if image is None:
        print(f"Error: Could not read image at {args.image_path}")
        sys.exit(1)

    # 2. Convert to grayscale (Tesseract typically works better on grayscale/binary)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 3. Apply thresholding based on user choice
    if args.threshold_type == "binary":
        _, thresh = cv2.threshold(gray, args.threshold_value, 255, cv2.THRESH_BINARY)
    elif args.threshold_type == "binary_inv":
        _, thresh = cv2.threshold(gray, args.threshold_value, 255, cv2.THRESH_BINARY_INV)
    elif args.threshold_type == "otsu":
        # Otsu ignores the --threshold_value; it calculates best threshold itself
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    elif args.threshold_type == "adaptive_gaussian":
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 5
        )
    elif args.threshold_type == "adaptive_mean":
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 21, 5
        )
    else:
        # Fallback in case something goes wrong
        _, thresh = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)

    # 4. Show thresholded image (press any key to continue)
    cv2.imshow("Thresholded Image", thresh)
    cv2.waitKey(0)

    # 5. Initialize your MedicareDetector with debug_mode
    detector = MedicareDetector(debug_mode=args.debug_mode)

    # 6. Attempt to find the Medicare number on the thresholded image
    #    (Note: if your code expects a color image, you could pass the original color image,
    #     but do your OCR on `thresh`. Adjust as appropriate.)
    medicare_anchor = detector.find_medicare_number(thresh)

    if medicare_anchor:
        print("[INFO] Medicare Anchor found:", medicare_anchor)
    else:
        print("[INFO] No Medicare Anchor found.")

    # 7. Optionally visualize the detection result (on the original color image)
    result_image = detector.visualize_result(image, medicare_anchor)
    cv2.imshow("Medicare Detection Result", result_image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
