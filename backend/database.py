# database.py

import logging
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config import config_manager  # Ensure config.py is correctly imported
from sqlalchemy.dialects.postgresql import JSON

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
    file_path = Column(String)
    ocr_confidence = Column(Float)
    sex = Column(String)
    needs_manual_review = Column(Boolean, default=False)
    error_details = Column(JSON, nullable=True)
    field_regions = Column(JSON, nullable=True)  # New column for field regions


class DatabaseManager:
    def __init__(self, db_url=None):
        """
        Initializes the DatabaseManager with the provided database URL.
        If no URL is provided, it defaults to the one specified in config.json.
        
        Args:
            db_url (str, optional): The database connection URI. Defaults to None.
        """
        if db_url is None:
            db_url = config_manager.get('DATABASE_URI', 'sqlite:///pathology_records.db')
        
        # Log the database URI being used
        logging.info(f"Using database at: {db_url}")
        
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
    
    def add_record(self, patient_info, file_path, ocr_confidence=None, validation_errors=None):
        """
        Adds a new patient record to the database.

        Args:
            patient_info (dict): Dictionary containing patient information.
            file_path (str): Path to the processed file.
            ocr_confidence (float, optional): OCR confidence score. Defaults to None.
            validation_errors (dict, optional): Validation errors, if any.
        """
        session = self.Session()
        try:
            logging.debug(f"Adding patient record with info: {patient_info}")

            # Parse date_of_birth if it's a string
            date_of_birth = patient_info.get('date_of_birth')
            if isinstance(date_of_birth, str):
                try:
                    date_of_birth = datetime.strptime(date_of_birth, '%d/%m/%Y')
                except ValueError:
                    logging.warning(f"Invalid date_of_birth format: {date_of_birth}")
                    date_of_birth = None

            # Determine if the record needs manual review
            needs_manual_review = bool(validation_errors)

            # Create a new PatientRecord instance
            new_record = PatientRecord(
                request_date=patient_info.get('request_date'),
                request_number=patient_info.get('request_number'),
                given_names=patient_info.get('given_names'),
                surname=patient_info.get('surname'),
                address=patient_info.get('address'),
                suburb=patient_info.get('suburb'),
                state=patient_info.get('state'),
                postcode=patient_info.get('postcode'),
                home_phone=patient_info.get('home_phone_number'),
                mobile_phone=patient_info.get('mobile_phone_number'),
                medicare_number=patient_info.get('medicare_number'),
                medicare_position=patient_info.get('medicare_position'),
                provider_number=patient_info.get('provider_number'),
                date_of_birth=date_of_birth,
                scan_date=datetime.utcnow(),
                file_path=file_path,
                ocr_confidence=ocr_confidence,
                sex=patient_info.get('sex'),
                needs_manual_review=needs_manual_review,
                error_details=validation_errors,  # Store validation errors
                field_regions=patient_info.get('field_regions')  # Store field regions
            )

            # Add the record to the session and commit it
            session.add(new_record)
            session.commit()
            logging.debug(f"Added patient record: {new_record}")

        except Exception as e:
            # Rollback the transaction in case of error
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
                    'name': record.name,
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