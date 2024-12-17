import logging
from RequestFormProcessor import RequestFormProcessor
from TextProcessor import TextProcessor
import cv2

def main(image_path: str, debug_mode: bool = False):
    """
    Main script to test the RequestFormProcessor.

    Args:
        image_path (str): Path to the input image.
        debug_mode (bool): Enables debug logging if True.
    """
    # Configure logging
    logging.basicConfig(level=logging.DEBUG if debug_mode else logging.INFO)

    try:
        # Initialize the form processor
        processor = RequestFormProcessor(image_path, debug_mode)
        text_processor = TextProcessor()
        cropped = processor.cropped_image
        cv2.imwrite('test_scan_folder/crop_test.jpg', cropped)
        img_region = cropped[90:112, 39:204]

        text = text_processor.extract_text(img_region, 'eng', 7)
        print(text)

        

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    debug_mode = True
    image_path = 'test_scan_folder/SKM_C224e24111620340_0001.jpg'
    main(image_path, debug_mode)
