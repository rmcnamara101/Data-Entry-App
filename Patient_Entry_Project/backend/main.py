from RequestFormProcessor import *
from RequestFormPreparer import *
from BatchProcessor import *
import os
from TextProcessor import *

if __name__ == "__main__":

    image_path = 'Patient_Entry_Project/scanned_forms/SKM_C224e24111620340_0001.jpg'

    preparer = RequestFormPreparer(image_path)

    prepared = preparer.prepare_form()

    processor = RequestFormProcessor(prepared)
    print(processor.process_form())
  
    pass