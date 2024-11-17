import logging
import os
import csv


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
            #preparer = RequestFormPreparer(file_path)
            #form = preparer.prepare_form()
            #processor = RequestFormProcessor(form)
            #result = processor.process_form()
            #results.append(result)
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

    headers = results[0].keys()
    with open(output_csv, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(results)