# database.py

import logging
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON
import numpy as np

Base = declarative_base()

class PatientRecord(Base):
    __tablename__ = 'patient_records'

    id = Column(Integer, primary_key=True)
    request_date = Column(DateTime)
    request_number = Column(String)
    given_names = Column(String)
    surname = Column(String)
    address = Column(String)
    suburb = Column(String)
    state = Column(String)
    postcode = Column(String)
    home_phone = Column(String)
    mobile_phone = Column(String)
    medicare_number = Column(String)
    medicare_position = Column(String)
    provider_number = Column(String)
    date_of_birth = Column(DateTime)
    scan_date = Column(DateTime, default=datetime.utcnow)
    ocr_confidence = Column(Float)
    sex = Column(String)
    needs_manual_review = Column(Boolean, default=False)
    error_details = Column(JSON, nullable=True)
    image_path = Column(String)


class DatabaseManager:
    def __init__(self, db_url=None):
        """
        Initializes the DatabaseManager with the provided database URL.
        If no URL is provided, it defaults to the one specified in config.json.
        
        Args:
            db_url (str, optional): The database connection URI. Defaults to None.
        """
        if not db_url:
            db_url = 'sqlite:///pathology_records.db'
        
        # Log the database URI being used
        logging.info(f"Using database at: {db_url}")
        
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def add_record(self, patient_info, validation_errors, ocr_confidence=None):
        """
        Adds a new patient record to the database, ensuring data integrity and logging.

        Args:
            patient_info (ProcessedForm): Custom data structure containing patient information.
            validation_errors (dict, optional): Validation errors, if any.
            ocr_confidence (float, optional): OCR confidence score.

        Raises:
            Exception: Rethrows any exception for higher-level handling.
        """
        def get_field_value(field, field_type=None):
            """
            Safely extract the value from a field, handling None and specific types.

            Args:
                field: The field to extract.
                field_type: Expected type (e.g., 'datetime') for special handling.

            Returns:
                Extracted value or None.
            """
            value = field.value if field and hasattr(field, 'value') else None

            if field_type == 'datetime' and isinstance(value, str):
                try:
                    return datetime.strptime(value, '%d/%m/%Y')  # Adjust format if needed
                except ValueError:
                    return None
            if field_type == 'image_path':
                return patient_info.image_path

            return value

        session = self.Session()
        try:
            logging.debug(f"Patient info: {patient_info}")

            # Parse date_of_birth safely
            date_of_birth = get_field_value(patient_info.date_of_birth)
            if isinstance(date_of_birth, str):
                try:
                    date_of_birth = datetime.strptime(date_of_birth, '%d/%m/%Y')
                except ValueError:
                    logging.warning(f"Invalid date_of_birth format: {date_of_birth}")
                    date_of_birth = None

            # Check for duplicates based on request_number
            request_number = get_field_value(patient_info.request_number)
            if not request_number:
                logging.warning("Request number is missing; skipping record.")
                return  # Skip insertion if request_number is not available

            existing_record = session.query(PatientRecord).filter(
                PatientRecord.request_number == request_number
            ).first()

            if existing_record:
                logging.warning(f"Duplicate record detected for request_number: {request_number}")
                return  # Skip duplicate insertion

            # Create a new PatientRecord instance
            new_record = PatientRecord(
                request_date=get_field_value(patient_info.request_date, field_type='datetime'),
                request_number=get_field_value(patient_info.request_number),
                given_names=get_field_value(patient_info.given_name),
                surname=get_field_value(patient_info.surname),
                address=get_field_value(patient_info.address),
                suburb=get_field_value(patient_info.suburb),
                state=get_field_value(patient_info.state),
                postcode=get_field_value(patient_info.postcode),
                home_phone=get_field_value(patient_info.home_phone),
                mobile_phone=get_field_value(patient_info.mobile_phone),
                medicare_number=get_field_value(patient_info.medicare_number),
                medicare_position=get_field_value(patient_info.medicare_position),
                provider_number=get_field_value(patient_info.provider_number),
                date_of_birth=get_field_value(patient_info.date_of_birth, field_type='datetime'),
                scan_date=datetime.utcnow(),
                ocr_confidence=ocr_confidence,
                sex=get_field_value(patient_info.sex),
                needs_manual_review=bool(validation_errors),
                error_details=validation_errors,
                image_path=get_field_value(patient_info.image_path, "image_path")
            )


            session.add(new_record)
            session.commit()
            logging.info(f"Successfully added patient record: {new_record.id}")

        except Exception as e:
            session.rollback()
            logging.error(f"Error adding patient record: {e}")
            raise
        finally:
            session.close()

    def get_folder_stats(self, folder_path):
        """
        Retrieves statistics about the folder processing.
        
        Args:
            folder_path (str): Path to the folder.
        
        Returns:
            dict: Dictionary containing total_images, records_added, and status.
        """
        session = self.Session()
        try:
            total_images = session.query(PatientRecord).filter(PatientRecord.file_path.like(f'{folder_path}%')).count()
            records_added = total_images  # Assuming one record per image
            return {
                'total_images': total_images,
                'records_added': records_added,
                'status': 'success'
            }
        except Exception as e:
            logging.error(f"Error getting folder stats: {e}")
            raise
        finally:
            session.close()

    def count_processed_images(self, folder_path):
        """
        Counts the number of processed images in the given folder.
        
        Args:
            folder_path (str): Path to the folder.
        
        Returns:
            int: Number of processed images.
        """
        session = self.Session()
        try:
            processed_count = session.query(PatientRecord).filter(
                PatientRecord.file_path.like(f'{folder_path}%')
            ).count()
            return processed_count
        except Exception as e:
            logging.error(f"Error counting processed images: {e}")
            raise
        finally:
            session.close()

    def get_flagged_entries(self):
        """
        Retrieves all patient records that need manual review.

        Returns:
            list: A list of dictionaries containing flagged patient records.
        """
        session = self.Session()
        try:
            flagged_records = session.query(PatientRecord).filter(
                PatientRecord.needs_manual_review == True
            ).all()

            # Convert records to dictionaries
            flagged_entries = []
            for record in flagged_records:
                entry = {
                    'id': record.id,
                    'request_number': record.request_number,
                    'given_names': record.given_names,
                    'surname': record.surname,
                    'validation_errors': record.error_details,
                    # Add other fields as needed
                }
                flagged_entries.append(entry)

            return flagged_entries
        except Exception as e:
            logging.error(f"Error fetching flagged entries: {e}")
            raise
        finally:
            session.close()