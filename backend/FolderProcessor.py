# folderprocessor.py

from database import DatabaseManager
from RequestFormProcessor import RequestFormProcessor
from config import config_manager
import os
import logging
from datetime import datetime

def process_folder(folder_path):
    """
    Processes image files in the specified folder, extracts patient data using OCR,
    and adds records to the database.
    
    Args:
        folder_path (str): Path to the folder containing image files.
    
    Returns:
        dict: Statistics about the processing (total_images, records_added).
    
    Raises:
        RuntimeError: If folder processing fails.
    """
    db = DatabaseManager(db_url=config_manager.get('DATABASE_URI', 'sqlite:///pathology_records.db'))
    records_added = 0
    total_files = 0

    try:
        logging.info(f"Starting folder processing: {folder_path}")
        if not os.path.exists(folder_path):
            logging.error(f"Folder does not exist: {folder_path}")
            raise FileNotFoundError(f"Folder does not exist: {folder_path}")

        for file_name in os.listdir(folder_path):
            if file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff')):
                total_files += 1
                file_path = os.path.join(folder_path, file_name)

                logging.info(f"Processing file: {file_name}")

                try:
                    processor = RequestFormProcessor(file_path)
                    processed_data = processor.process_form()

                    if processed_data['data']:
                        records_added += 1
                        logging.debug(f"Record added for file: {file_name}")
                    else:
                        logging.warning(f"No valid data found in file: {file_name}")
                except Exception as e:
                    logging.error(f"Error processing file {file_name}: {e}")

        stats = {'folder_path': folder_path, 'total_images': total_files, 'records_added': records_added}
        logging.info(f"Folder processing complete. Total files: {total_files}, Records added: {records_added}")
        return stats

    except Exception as e:
        logging.error(f"Error in process_folder: {e}")
        raise RuntimeError(f"Failed to process folder: {e}")