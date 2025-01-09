import os
import sys
from backend.form_scanning.RequestFormProcessor import RequestFormProcessor


if __name__ == "__main__":
    file_path = '/Users/rileymcnamara/CODE/2024/Data-Entry-App/test_scan_folder/SKM_C224e24111620340_0001.jpg'
    config_path = '/Users/rileymcnamara/CODE/2024/Data-Entry-App/backend/form_scanning/configs/field_config.json'
    processor = RequestFormProcessor(file_path, config_path)
    processed_data = processor.process_form()
    print(processed_data)