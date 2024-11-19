import os
import sqlite3
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging

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
    def __init__(self, db_path='pathology_records.db'):
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def add_patient_record(self, patient_info, file_path, ocr_confidence=None):
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
                file_path=file_path,
                ocr_confidence=ocr_confidence,
                date_of_birth=patient_info.get('date_of_birth')
            )
            session.add(new_record)
            session.commit()
        except Exception as e:
            session.rollback()
            logging.error(f"Error adding patient record: {e}")
            raise
        finally:
            session.close()

    def get_folder_stats(self, folder_path):
        image_extensions = ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']
        images = [f for f in os.listdir(folder_path) if os.path.splitext(f)[1].lower() in image_extensions]
        
        return {
            'total_images': len(images),
            'processed_images': self.count_processed_images(folder_path),
            'folder_path': folder_path
        }

    def count_processed_images(self, folder_path):
        session = self.Session()
        processed_count = session.query(PatientRecord).filter(
            PatientRecord.file_path.like(f'{folder_path}%')
        ).count()
        session.close()
        return processed_count

def process_folder(folder_path):
    from RequestFormProcessor import RequestFormProcessor  # Your existing image processing module
    
    db = DatabaseManager()
    stats = db.get_folder_stats(folder_path)
    
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            file_path = os.path.join(folder_path, filename)
            processor = RequestFormProcessor(file_path)
            
            # Process image and extract patient details
            patient_info = processor.process_form()
            
            # Save to database
            db.add_patient_record(
                patient_info=patient_info,
                file_path=file_path,
                ocr_confidence=patient_info.get('ocr_confidence', None)
            )
    
    return stats