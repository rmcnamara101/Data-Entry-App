# Description: Main entry point for the application. 
import logging
from logging_config import setup_logging
import numpy as np
from RequestFormPreparer import RequestFormPreparer
import cv2

def main():

    # Set up logging
    setup_logging()
    logger = logging.getLogger(__name__)
    file_path = '/Users/rileymcnamara/CODE/2024/DATA-ENTRY-APP/test_scan_folder/SKM_C224e24111620340_0001.jpg'
    preparer = RequestFormPreparer(file_path, debug_mode=True)
    img = preparer.prepare_form()
    cv2.imwrite('Users/rileymcnamara/CODE/2024/DATA-ENTRY-APP/prepare_test.jpg', img)
    

if __name__ == '__main__':
    main()
