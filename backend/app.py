# app.py

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import pandas as pd
import io
import sqlite3
from datetime import datetime
import shutil
import logging

# Configure logging based on config
from config import config_manager

logging.basicConfig(
    level=config_manager.get('LOG_LEVEL', 'DEBUG'),
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)

from database import DatabaseManager, PatientRecord  # Removed 'process_folder'
from FolderProcessor import process_folder  # Correct import from folderprocessor.py

app = Flask(__name__)
CORS(app)

# Retrieve settings from config
UPLOAD_FOLDER = config_manager.get('UPLOAD_FOLDER', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DATABASE = config_manager.get('DATABASE_URI', 'sqlite:///database.db')
BACKUP_FOLDER = config_manager.get('BACKUP_FOLDER', 'backups')

db = DatabaseManager(db_url=DATABASE)

def init_db():
    # SQLAlchemy handles table creation
    db.engine.connect()
    db.engine.dispose()

init_db()

def serialize_record(record):
    return {
        'id': record.id,
        'request_date': record.request_date.isoformat() if record.request_date else None,
        'request_number': record.request_number or "Not Found",
        'given_names': record.given_names or "Not Found",
        'surname': record.surname or "Not Found",
        'name': record.name or "Not Found",
        'address': record.address or "Not Found",
        'suburb': record.suburb or "Not Found",
        'state': record.state or "Not Found",
        'postcode': record.postcode or "Not Found",
        'home_phone': record.home_phone or "Not Found",
        'mobile_phone': record.mobile_phone or "Not Found",
        'medicare_number': record.medicare_number or "Not Found",
        'medicare_position': record.medicare_position or "Not Found",
        'doctor_information': record.doctor_information or "Not Found",
        'provider_number': record.provider_number or "Not Found",
        'date_of_birth': record.date_of_birth.isoformat() if record.date_of_birth else None,
        'scan_date': record.scan_date.isoformat() if record.scan_date else None,
        'file_path': record.file_path or "Not Found",
        'ocr_confidence': record.ocr_confidence or 0.0
    }

@app.route('/api/patient-records', methods=['GET'])
def get_patient_records():
    try:
        session = db.Session()
        records = session.query(PatientRecord).all()
        session.close()
        serialized_records = [serialize_record(record) for record in records]
        return jsonify({'records': serialized_records}), 200
    except Exception as e:
        logging.error(f"Error fetching patient records: {str(e)}")
        return jsonify({'message': 'Internal Server Error'}), 500

@app.route('/api/routes', methods=['GET'])
def list_routes():
    from flask import url_for
    import urllib
    output = []
    for rule in app.url_map.iter_rules():
        options = {}
        for arg in rule.arguments:
            options[arg] = "[{0}]".format(arg)
        methods = ','.join(rule.methods)
        try:
            url = url_for(rule.endpoint, **options)
        except:
            url = None
        line = urllib.parse.unquote("{:50s} {:20s} {}".format(rule.endpoint, methods, url))
        output.append(line)
    return jsonify({'routes': output}), 200

@app.route('/api/export-records', methods=['GET'])
def export_records():
    try:
        db = DatabaseManager(db_url=DATABASE)
        records = db.get_all_patient_records()
        df = pd.DataFrame([{
            'ID': record.id,
            'Request Number': record.request_number,
            'Name': f"{record.given_names} {record.surname}",  # Corrected field
            'Date of Birth': record.date_of_birth.isoformat() if record.date_of_birth else None,
            'OCR Confidence': record.ocr_confidence
        } for record in records])

        output = io.BytesIO()
        df.to_csv(output, index=False)
        output.seek(0)

        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name='patient_records.csv'
        )
    except Exception as e:
        logging.error(f"Error exporting records: {str(e)}")
        return jsonify({'message': 'Internal Server Error'}), 500

@app.route('/api/backup-database', methods=['POST'])
def backup_database():
    try:
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(BACKUP_FOLDER, f'pathology_records_{timestamp}.db')

        # Ensure backups directory exists
        os.makedirs(BACKUP_FOLDER, exist_ok=True)

        # Copy the database file
        db_file_path = DATABASE.replace('sqlite:///', '')
        shutil.copy2(db_file_path, backup_path)

        return jsonify({'success': True, 'backup_path': backup_path}), 200
    except Exception as e:
        logging.error(f"Error backing up database: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/optimize-database', methods=['POST'])
def optimize_database():
    try:
        # Connect to the database
        db_file_path = DATABASE.replace('sqlite:///', '')
        conn = sqlite3.connect(db_file_path)
        cursor = conn.cursor()

        # Run VACUUM to optimize the database
        cursor.execute('VACUUM')

        # Run ANALYZE to update statistics
        cursor.execute('ANALYZE')

        conn.close()
        return jsonify({'success': True}), 200
    except Exception as e:
        logging.error(f"Error optimizing database: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scan-default-folder', methods=['POST'])
def scan_default_folder():
    default_folder = config_manager.get('DEFAULT_SCAN_FOLDER', '/default/path/to/scan')
    try:
        logging.info(f"Scanning default folder: {default_folder}")
        stats = process_folder(default_folder)
        logging.info(f"Scan completed successfully: {stats}")
        return jsonify(stats), 200
    except Exception as e:
        logging.error(f"Error scanning default folder: {e}")
        return jsonify({'message': str(e)}), 500

@app.route('/api/set-default-folder', methods=['POST'])
def set_default_folder():
    try:
        data = request.get_json()
        new_default_folder = data.get('default_folder')
        
        if not new_default_folder:
            return jsonify({'message': 'Default folder path not provided.'}), 400
        
        # Optionally, validate the path exists
        if not os.path.exists(new_default_folder):
            return jsonify({'message': 'Provided folder path does not exist.'}), 400
        
        # Update the configuration
        config_manager.set('DEFAULT_SCAN_FOLDER', new_default_folder)
        
        logging.info(f"Default scan folder updated to: {new_default_folder}")
        return jsonify({'success': True, 'default_folder': new_default_folder}), 200
    
    except Exception as e:
        logging.error(f"Error setting default folder: {e}")
        return jsonify({'message': f'Error setting default folder: {str(e)}'}), 500

@app.route('/api/scan-new-folder', methods=['POST'])
def scan_new_folder():
    try:
        # Check if files were uploaded
        if 'files[]' not in request.files:
            logging.error("No files part in the request")
            return jsonify({'message': 'No files uploaded'}), 400

        files = request.files.getlist('files[]')
        relative_paths = request.form.getlist('relative_paths[]')
        base_folder_path = request.form.get('folder_path')

        if not files or not base_folder_path:
            logging.error("No files or folder path provided")
            return jsonify({'message': 'No files or folder path provided'}), 400

        # Create temporary directory structure and save files
        temp_base_path = os.path.join(config_manager.get('UPLOAD_FOLDER', 'uploads'), base_folder_path)
        os.makedirs(temp_base_path, exist_ok=True)

        processed_files = 0
        for file, rel_path in zip(files, relative_paths):
            if file.filename:
                # Create the full path maintaining the folder structure
                full_path = os.path.join(config_manager.get('UPLOAD_FOLDER', 'uploads'), rel_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                
                # Save the file
                file.save(full_path)
                processed_files += 1
                logging.info(f"Saved file: {full_path}")

        # Process the uploaded folder
        stats = process_folder(temp_base_path)
        stats['processed_files'] = processed_files

        logging.info(f"Scan completed successfully: {stats}")
        return jsonify(stats), 200

    except Exception as e:
        logging.error(f"Error processing uploaded files: {str(e)}")
        return jsonify({'message': f'Error processing files: {str(e)}'}), 500

    finally:
        # Clean up temporary files (optional)
        try:
            temp_uploads_path = config_manager.get('UPLOAD_FOLDER', 'uploads')
            if os.path.exists(temp_uploads_path):
                shutil.rmtree(temp_uploads_path)
        except Exception as cleanup_error:
            logging.error(f"Error cleaning up temporary files: {str(cleanup_error)}")

@app.route('/api/default-folder', methods=['GET'])
def get_default_folder():
    try:
        current_default = config_manager.get('DEFAULT_SCAN_FOLDER', '/default/path/to/scan')
        return jsonify({'default_folder': current_default}), 200
    except Exception as e:
        logging.error(f"Error fetching default folder: {e}")
        return jsonify({'message': 'Internal Server Error'}), 500
    
@app.route('/api/clear-database', methods=['POST'])
def clear_database():
    try:
        # Optional: Implement authentication/authorization checks here

        session = db.Session()
        deleted_records = session.query(PatientRecord).delete()
        session.commit()
        logging.info(f"Database cleared: {deleted_records} records deleted.")
        return jsonify({'success': True, 'deleted_records': deleted_records}), 200
    except Exception as e:
        session.rollback()
        logging.error(f"Error clearing database: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        session.close()

if __name__ == '__main__':
    app.run(debug=True)