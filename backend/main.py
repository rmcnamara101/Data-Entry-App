# Description: Main entry point for the application. 
import logging
from logging_config import setup_logging

def main():

    setup_logging(
        log_level=logging.DEBUG,      # Set to DEBUG for detailed logs
        log_to_file=True,             # Enable file logging
        log_file_path="logs/app.log"  # Log file path
    )

    # Import other modules after logging is configured
    from RequestFormProcessor import RequestFormProcessor

    file_path = '/Users/rileymcnamara/CODE/2024/Data-Entry-App/test_scan_folder/SKM_C224e24111620340_0001.jpg'

    processor = RequestFormProcessor(file_path, debug_mode=True)
    processor.process_form()
    print(processor.get_data())

if __name__ == '__main__':
    main()
