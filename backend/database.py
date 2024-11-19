import os
import sqlite3
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class PatientRecord(Base):
    __tablename__ = 'patient_records'

    id = Column(Integer, primary_key=True)
    patient_name = Column(String)
    patient_id = Column(String)
    scan_date = Column(DateTime, default=datetime.utcnow)
    file_path = Column(String)
    ocr_confidence = Column(Float)

class DatabaseManager:
    def __init__(self, db_path='pathology_records.db'):
        self.engine = create_engine(f'sqlite:///{db_path}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def add_patient_record(self, patient_name, patient_id, file_path, ocr_confidence=None):
        session = self.Session()
        new_record = PatientRecord(
            patient_name=patient_name,
            patient_id=patient_id,
            file_path=file_path,
            ocr_confidence=ocr_confidence
        )
        session.add(new_record)
        session.commit()
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
                patient_name=patient_info['name'],
                patient_id=patient_info['id'],
                file_path=file_path,
                ocr_confidence=patient_info.get('confidence', None)
            )
    
    return stats