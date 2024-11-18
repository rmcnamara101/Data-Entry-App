# backend/app.py
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing

@app.route('/process', methods=['POST'])
def process_form():
    data = request.get_json()
    # Process data using your existing backend code
    # For example, call your RequestFormProcessor here
    response = {'message': 'Data processed successfully'}
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)