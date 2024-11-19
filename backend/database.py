# database.py

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging
from datetime import datetime
from config import config_manager  # Ensure config.py is correctly imported

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
    doctor_information = Column(String)
    provider_number = Column(String)
    date_of_birth = Column(DateTime)
    scan_date = Column(DateTime, default=datetime.utcnow)
    file_path = Column(String)
    ocr_confidence = Column(Float)

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
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def add_patient_record(self, patient_info, file_path, ocr_confidence=None):
        """
        Adds a new patient record to the database.
        
        Args:
            patient_info (dict): Dictionary containing patient information.
            file_path (str): Path to the processed file.
            ocr_confidence (float, optional): OCR confidence score. Defaults to None.
        """
        session = self.Session()
        try:
            new_record = PatientRecord(
                request_date=patient_info.get('request_date'),
                request_number=patient_info.get('request_number'),
                given_names=patient_info.get('given_names'),
                surname=patient_info.get('surname'),
                address=patient_info.get('address'),
                suburb=patient_info.get('suburb'),
                state=patient_info.get('state'),
                postcode=patient_info.get('postcode'),
                home_phone=patient_info.get('home_phone'),
                mobile_phone=patient_info.get('mobile_phone'),
                medicare_number=patient_info.get('medicare_number'),
                medicare_position=patient_info.get('medicare_position'),
                doctor_information=patient_info.get('doctor_information'),
                provider_number=patient_info.get('provider_number'),
                date_of_birth=patient_info.get('date_of_birth'),
                scan_date=datetime.utcnow(),
                file_path=file_path,
                ocr_confidence=ocr_confidence,
            )
            session.add(new_record)
            session.commit()
            logging.debug(f"Added patient record: {new_record}")
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