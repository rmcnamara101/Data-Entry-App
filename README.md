# Data Entry Application

This project is a robust data entry system that processes forms to extract, clean, validate, and store data in a database. The application is designed to handle large-scale processing of image-based request forms, making it ideal for use cases such as healthcare or administrative document processing.

## Features

- **OCR-Based Data Extraction**: Utilizes Tesseract OCR for extracting textual data from form images.
- **Field Extraction**: Identifies specific fields on forms using anchor-based or manual extraction techniques.
- **Validation**: Ensures data integrity with customizable validation rules.
- **Database Integration**: Saves processed data into a database for future retrieval and reporting.
- **Batch Processing**: Processes entire folders of form images in one go.
- **Debug Mode**: Provides detailed logs and visualizations for troubleshooting.

## Project Structure

### Core Modules

1. **FormImagePreparer**:
   Prepares images for OCR by performing tasks like resizing, binarization, and alignment.

2. **FieldExtractor**:
   Extracts text from specific regions on the form, either using manual region definitions or anchors like Medicare numbers.

3. **TextProcessor**:
   Handles OCR operations using Tesseract and cleans extracted text for further processing.

4. **Validator**:
   Validates extracted data against predefined rules to ensure correctness.

5. **DataPostProcessor**:
   Cleans and formats data to ensure consistency before saving to the database.

6. **DatabaseManager**:
   Manages interactions with the database, including adding records and querying data.

7. **MedicareAnchorDetector**:
   Uses sliding window techniques to detect and validate Medicare numbers within specified regions of the form.

8. **RequestFormProcessor**:
   Coordinates the entire form processing workflow, including image preparation, field extraction, data cleaning, validation, and database insertion.

9. **FolderProcessor**:
   Automates the batch processing of forms in a folder, generating statistics for processed and stored records.

### Supporting Files

- **constants.py**: Contains configuration constants such as OCR settings and predefined regions.
- **config.py**: Manages application configurations like database connection strings.

## Installation

### Prerequisites

- Python 3.8+
- Tesseract OCR
- Required Python libraries (listed in `requirements.txt`)

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up the database:
   ```bash
   python manage.py migrate
   ```

4. Ensure Tesseract is installed and available in the system PATH.

## Usage

### Processing a Single Form

Use the `RequestFormProcessor` to process a single form:
```python
from RequestFormProcessor import RequestFormProcessor

processor = RequestFormProcessor("path/to/form/image.png", debug_mode=True)
result = processor.process_form()
print(result)
```

### Batch Processing

Use the `FolderProcessor` to process an entire folder of forms:
```python
from FolderProcessor import process_folder

stats = process_folder("path/to/folder")
print(stats)
```

### Debug Mode
Enable debug mode to visualize the OCR process and log detailed information:
```python
processor = RequestFormProcessor("path/to/form/image.png", debug_mode=True)
```

## Contributing

Contributions are welcome! Please follow the standard fork-and-pull model:

1. Fork the repository.
2. Create a feature branch.
3. Commit your changes.
4. Push to your fork and submit a pull request.

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgments

- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) for OCR capabilities.
- Python community for their amazing libraries and tools.

---

This README provides an overview of the application's capabilities and how to get started. For more details, refer to the module-specific documentation or the code comments.

