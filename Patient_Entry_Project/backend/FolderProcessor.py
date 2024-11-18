import logging
import os
import csv
from RequestFormPreparer import RequestFormPreparer
from RequestFormProcessor import RequestFormProcessor

def process_folder(folder_path: str, output_csv: str):
    results = []

    if not os.path.exists(folder_path):
        logging.error(f"Folder not found: {folder_path}")
        print(f"Error: Folder not found: {folder_path}")
        return

    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)

        # Debug: Check each file
        print(f"Found file: {file_name}")
        if not file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff')):
            logging.info(f"Skipped non-image file: {file_name}")
            print(f"Skipped non-image file: {file_name}")
            continue

        try:
            print(f"Processing file: {file_name}")
            processor = RequestFormProcessor(file_path)
            results.append(processor.process_form())
            print(f"Successfully processed: {file_name}")
        except Exception as e:
            logging.error(f"Error processing file {file_name}: {e}")
            print(f"Error processing file {file_name}: {e}")

    save_results_to_csv(results, output_csv)
    print("Folder processing complete.")
    
def save_results_to_csv(results: list, output_csv: str):
    if not results:
        print("No results to save.")
        return

    # Collect all unique keys across all dictionaries
    all_fieldnames = set()
    for result in results:
        all_fieldnames.update(result.keys())

    # Convert to a sorted list to ensure consistent field order
    fieldnames = sorted(all_fieldnames)

    # Fill missing keys in each dictionary
    for result in results:
        for key in fieldnames:
            if key not in result:
                result[key] = None  # Or use an empty string '' if preferred

    # Write results to CSV
    with open(output_csv, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)