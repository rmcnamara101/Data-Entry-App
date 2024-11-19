# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
from database import DatabaseManager, process_folder
from flask import Flask, jsonify, send_file
from database import DatabaseManager
import pandas as pd
import io
import sqlite3

# Import your backend processing modules
from RequestFormProcessor import RequestFormProcessor

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/process-form', methods=['POST'])
def process_form():
    # Check if the request has the file part
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected for uploading'}), 400

    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Process the file using your existing backend code
        try:
            processor = RequestFormProcessor(file_path)
            extracted_data = processor.process_form()

            # You can also handle saving data to the database here

            return jsonify({'message': 'Form processed successfully', 'data': extracted_data}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    return jsonify({'error': 'File processing failed'}), 500

app = Flask(__name__)

@app.route('/api/folder-stats', methods=['POST'])
def get_folder_stats():
    data = request.json
    db = DatabaseManager()
    stats = db.get_folder_stats(data['folder_path'])
    return jsonify(stats)

@app.route('/api/process-folder', methods=['POST'])
def process_images():
    data = request.json
    stats = process_folder(data['folder_path'])
    return jsonify(stats)


app = Flask(__name__)
db = DatabaseManager()

@app.route('/api/patient-records', methods=['GET'])
def get_patient_records():
    session = db.Session()
    records = session.query(db.PatientRecord).all()
    records_data = [{
        'id': record.id,
        'patient_name': record.patient_name,
        'patient_id': record.patient_id,
        'scan_date': record.scan_date.isoformat(),
        'file_path': record.file_path,
        'ocr_confidence': record.ocr_confidence
    } for record in records]
    session.close()
    return jsonify({'records': records_data})

@app.route('/api/export-records', methods=['GET'])
def export_records():
    session = db.Session()
    records = session.query(db.PatientRecord).all()
    
    df = pd.DataFrame([{
        'Patient ID': record.patient_id,
        'Patient Name': record.patient_name,
        'Scan Date': record.scan_date,
        'File Path': record.file_path,
        'OCR Confidence': record.ocr_confidence
    } for record in records])
    
    output = io.BytesIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    session.close()
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name='patient_records.csv'
    )

@app.route('/api/backup-database', methods=['POST'])
def backup_database():
    try:
        import shutil
        from datetime import datetime
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f'backups/pathology_records_{timestamp}.db'
        
        # Ensure backups directory exists
        os.makedirs('backups', exist_ok=True)
        
        # Copy the database file
        shutil.copy2('pathology_records.db', backup_path)
        
        return jsonify({'success': True, 'backup_path': backup_path})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/optimize-database', methods=['POST'])
def optimize_database():
    try:
        # Connect to the database
        conn = sqlite3.connect('pathology_records.db')
        cursor = conn.cursor()
        
        # Run VACUUM to optimize the database
        cursor.execute('VACUUM')
        
        # Run ANALYZE to update statistics
        cursor.execute('ANALYZE')
        
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)