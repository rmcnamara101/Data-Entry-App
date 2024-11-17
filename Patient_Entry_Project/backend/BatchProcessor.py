import os
from RequestFormPreparer import RequestFormPreparer
from RequestFormProcessor import RequestFormProcessor
from config import FIELD_REGIONS

class BatchProcessor:
    def __init__(self, folder_path):
        self.folder_path = folder_path

    def process_folder(self):
        results = []
        for file_name in os.listdir(self.folder_path):
            file_path = os.path.join(self.folder_path, file_name)
            if file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                preparer = RequestFormPreparer(file_path)
                prepared_image = preparer.prepare_form()
                processor = RequestFormProcessor(FIELD_REGIONS)
                results.append(processor.process_form(prepared_image))
        return results