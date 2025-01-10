# folderprocessor.py

from backend.database.database import DatabaseManager
from backend.form_scanning.RequestFormProcessor import RequestFormProcessor
import os
import logging
from datetime import datetime

def process_folder(folder_path, progress_callback=None):
    """
    Processes image files in the specified folder, extracts patient data using OCR,
    and adds records to the database, while updating progress via a callback.

    Args:
        folder_path (str): Path to the folder containing image files.
        progress_callback (callable, optional): Function to update progress. Receives an integer (0-100).

    Returns:
        dict: Statistics about the processing (total_images, records_added).
    
    Raises:
        RuntimeError: If folder processing fails.
    """
    db = DatabaseManager()
    records_added = 0
    total_files = 0
    processed_files = 0

    try:
        logging.info(f"Starting folder processing: {folder_path}")
        if not os.path.exists(folder_path):
            logging.error(f"Folder does not exist: {folder_path}")
            raise FileNotFoundError(f"Folder does not exist: {folder_path}")

        # Get all valid image files in the folder
        image_files = [
            file_name for file_name in os.listdir(folder_path)
            if file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff'))
        ]
        total_files = len(image_files)

        if total_files == 0:
            logging.warning(f"No image files found in folder: {folder_path}")
            return {'folder_path': folder_path, 'total_images': 0, 'records_added': 0}

        # Process each file
        for idx, file_name in enumerate(image_files):
            file_path = os.path.join(folder_path, file_name)
            logging.info(f"Processing file: {file_name}")

            try:
                processor = RequestFormProcessor(file_path, '/Users/rileymcnamara/CODE/2024/Data-Entry-App/backend/form_scanning/configs/field_config.json')
                processed_data = processor.process_form()

                if processed_data['data']:
                    db.add_record(processed_data['data'], processed_data['validation_errors'], processor.get_ocr())
                    records_added += 1
                    logging.debug(f"Record added for file: {file_name}")
                else:
                    logging.warning(f"No valid data found in file: {file_name}")
            except Exception as e:
                logging.error(f"Error processing file {file_name}: {e}")

            processed_files += 1

            # Update progress via callback if provided
            if progress_callback:
                progress = int((processed_files / total_files) * 100)
                progress_callback.emit(progress)  # Use emit here

        stats = {
            'folder_path': folder_path,
            'total_images': total_files,
            'records_added': records_added
        }
        logging.info(f"Folder processing complete. Total files: {total_files}, Records added: {records_added}")
        return stats

    except Exception as e:
        logging.error(f"Error in process_folder: {e}")
        raise RuntimeError(f"Failed to process folder: {e}")
