# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os

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

if __name__ == '__main__':
    app.run(debug=True)