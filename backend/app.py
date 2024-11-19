# backend/app.py
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

# Configure logging
logging.basicConfig(level=logging.DEBUG)

from database import DatabaseManager, PatientRecord, process_folder
from RequestFormProcessor import RequestFormProcessor

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db = DatabaseManager()
# Database setup
DATABASE = 'database.db'

def init_db():
    # SQLAlchemy handles table creation
    db.engine.connect()
    db.engine.dispose()

init_db()


def save_csv_to_db(csv_file):
    try:
        with open(csv_file, 'r', encoding='utf-8') as file:
            headers = file.readline().strip().split(',')
            for line in file:
                values = line.strip().split(',')
                record = dict(zip(headers, values))
                # Parse date_of_birth to datetime object
                date_of_birth = datetime.strptime(record.get('date_of_birth'), '%Y-%m-%d') if record.get('date_of_birth') else None
                ocr_confidence = float(record.get('ocr_confidence')) if record.get('ocr_confidence') else None
                db.add_patient_record({
                    'request_number': record.get('request_number'),
                    'name': record.get('name'),
                    'date_of_birth': date_of_birth,
                    'ocr_confidence': ocr_confidence
                })
    except Exception as e:
        logging.error(f"Error saving CSV to DB: {str(e)}")
        raise e

def get_folder_stats(folder_path):
    stats = db.get_folder_stats(folder_path)
    return stats

@app.route('/api/patient-records', methods=['GET'])
def get_patient_records():
    try:
        db = DatabaseManager()
        session = db.Session()
        records = session.query(PatientRecord).all()
        session.close()
        serialized_records = [serialize_record(record) for record in records]
        return jsonify({'records': serialized_records}), 200
    except Exception as e:
        logging.error(f"Error fetching patient records: {str(e)}")
        return jsonify({'message': 'Internal Server Error'}), 500

def serialize_record(record):
    return {
        'id': record.id,
        'request_number': record.request_number,
        'name': record.name,
        'date_of_birth': record.date_of_birth.isoformat() if record.date_of_birth else None,
        'ocr_confidence': record.ocr_confidence
    }

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
        records = db.get_all_patient_records()
        df = pd.DataFrame([{
            'ID': record.id,
            'Request Number': record.request_number,
            'Name': record.name,
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
        backup_path = f'backups/pathology_records_{timestamp}.db'

        # Ensure backups directory exists
        os.makedirs('backups', exist_ok=True)

        # Copy the database file
        shutil.copy2(DATABASE, backup_path)

        return jsonify({'success': True, 'backup_path': backup_path})
    except Exception as e:
        logging.error(f"Error backing up database: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/optimize-database', methods=['POST'])
def optimize_database():
    try:
        # Connect to the database
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        # Run VACUUM to optimize the database
        cursor.execute('VACUUM')

        # Run ANALYZE to update statistics
        cursor.execute('ANALYZE')

        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Error optimizing database: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    
@app.route('/api/scan-default-folder', methods=['POST'])
def scan_default_folder():
    default_folder = '/Users/rileymcnamara/CODE/2024/Data-Entry-App/test_scan_folder'  # Update this to your default folder path
    try:
        stats = process_folder(default_folder)
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500


@app.route('/api/scan-new-folder', methods=['POST'])
def scan_new_folder():
    data = request.json
    folder_path = data.get('folder_path')

    if not folder_path or not os.path.exists(folder_path):
        return jsonify({'message': 'Invalid folder path'}), 400

    try:
        stats = process_folder(folder_path)
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)