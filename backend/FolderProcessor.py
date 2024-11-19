from database import DatabaseManager, PatientRecord
from RequestFormProcessor import RequestFormProcessor
import os
import logging
import csv
from datetime import datetime


from database import DatabaseManager, PatientRecord
from RequestFormProcessor import RequestFormProcessor
import os
import logging
from datetime import datetime


def process_folder(folder_path):
    db = DatabaseManager()
    session = db.Session()
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
                        record = PatientRecord(
                            request_date=processed_data['data'].get('Request Date', datetime.utcnow()),
                            request_number=processed_data['data'].get('Request Number', "Not Found"),
                            given_names=processed_data['data'].get('Given Names', "Not Found"),
                            surname=processed_data['data'].get('Surname', "Not Found"),
                            address=processed_data['data'].get('Address', "Not Found"),
                            suburb=processed_data['data'].get('Suburb', "Not Found"),
                            state=processed_data['data'].get('State', "Not Found"),
                            postcode=processed_data['data'].get('Postcode', "Not Found"),
                            home_phone=processed_data['data'].get('Home Phone', "Not Found"),
                            mobile_phone=processed_data['data'].get('Mobile Phone', "Not Found"),
                            medicare_number=processed_data['data'].get('Medicare Number', "Not Found"),
                            medicare_position=processed_data['data'].get('Medicare Position', "Not Found"),
                            doctor_information=processed_data['data'].get('Doctor Information', "Not Found"),
                            provider_number=processed_data['data'].get('Provider Number', "Not Found"),
                            date_of_birth=processed_data['data'].get('Date of Birth'),
                            scan_date=datetime.utcnow(),
                            file_path=file_path,
                            ocr_confidence=processed_data['data'].get('OCR Confidence', 0.0),
                        )
                        session.add(record)
                        records_added += 1
                    else:
                        logging.warning(f"No valid data found in file: {file_name}")
                except Exception as e:
                    logging.error(f"Error processing file {file_name}: {e}")

        session.commit()
        logging.info(f"Folder processing complete. Total files: {total_files}, Records added: {records_added}")
        return {'folder_path': folder_path, 'total_images': total_files, 'records_added': records_added}

    except Exception as e:
        logging.error(f"Error in process_folder: {e}")
        session.rollback()
        raise RuntimeError(f"Failed to process folder: {e}")

    finally:
        session.close()


def save_results_to_csv(results, output_csv):
    if not results:
        logging.info("No results to save.")
        return

    fieldnames = sorted(set().union(*(d.keys() for d in results)))
    with open(output_csv, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)