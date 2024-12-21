    Main script to test the RequestFormProcessor.
import os
import sys
import pandas as pd
from typing import List
from datetime import datetime
from RequestFormProcessor import RequestFormProcessor, ProcessedForm

# Assuming you've imported or defined RequestFormProcessor, ProcessedForm, and FieldData
# from the provided code

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_experiment.py <path_to_image_folder>")
        sys.exit(1)

    image_folder = sys.argv[1]

    if not os.path.isdir(image_folder):
        print(f"Error: {image_folder} is not a valid directory.")
        sys.exit(1)

    # Collect results in a list of dictionaries, each corresponding to one image
    results = []

    # Valid image extensions (add or remove as needed)
    valid_extensions = {'.png', '.jpg', '.jpeg', '.tif', '.tiff'}

    # Iterate over all files in the folder
    for filename in os.listdir(image_folder):
        file_path = os.path.join(image_folder, filename)
        # Check if file is an image
        if not os.path.isfile(file_path):
            continue
        ext = os.path.splitext(filename)[1].lower()
        if ext not in valid_extensions:
            continue
        
        print(f"Processing: {filename}")

        try:
            processor = RequestFormProcessor(file_path, debug_mode=False)
            result = processor.process_form()
            processed_form = result["data"]  # This should be a ProcessedForm instance
            validation_errors = result["validation_errors"]

            # Extract fields from ProcessedForm into a dict
            # We can create a standardized dictionary for each image
            record = {"image_filename": filename}
            
            # Extract each field from ProcessedForm
            # For each FieldData attribute, store the value, confidence, and bounding box as needed.
            # Adjust field names according to what you have in ProcessedForm.
            fields = [
                "request_number", "request_date", "received_date",
                "surname", "given_name", "sex", "address", "suburb", 
                "postcode", "state", "date_of_birth", "mobile_phone_number",
                "home_phone_number", "medicare_number", "medicare_position", "provider_number"
            ]

            for f in fields:
                field_data = getattr(processed_form, f, None)
                if field_data is not None:
                    record[f"{f}_value"] = field_data.value
                    record[f"{f}_confidence"] = field_data.confidence
                    record[f"{f}_bbox"] = field_data.bounding_box
                else:
                    record[f"{f}_value"] = None
                    record[f"{f}_confidence"] = None
                    record[f"{f}_bbox"] = None

            # Add validation errors
            # Assuming validation_errors is a dict of field: list_of_errors or field: error_message
            # If it's not, adjust accordingly.
            for field_name, errors in validation_errors.items():
                # Combine all errors into a single string for that field
                if isinstance(errors, list):
                    errors_str = "; ".join(errors)
                else:
                    errors_str = str(errors)
                record[f"{field_name}_errors"] = errors_str

            results.append(record)

        except Exception as e:
            print(f"Error processing {filename}: {e}")

    # Once we have all results, convert to a DataFrame and write to Excel
    df = pd.DataFrame(results)

    # Generate an output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"form_processing_results_{timestamp}.xlsx"
    df.to_excel(output_filename, index=False)
    print(f"Results saved to {output_filename}")

if __name__ == "__main__":
    main()
