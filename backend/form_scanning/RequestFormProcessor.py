from typing import Dict, Any
from dataclasses import dataclass, fields
import logging
import cv2
from datetime import datetime
from backend.form_scanning.FormImagePreparer import FormImagePreparer
from backend.form_scanning.FieldExtractor import FieldExtractor
from backend.form_scanning.DataPostProcessor import DataPostProcessor
from backend.form_scanning.Validator import Validator
from backend.database.database import DatabaseManager
from backend.form_scanning.MedicareAnchorDetector import MedicareDetector
from backend.constants import OCR_CONFIGS
from pyzbar.pyzbar import decode

import numpy as np
from typing import List, Optional, Tuple
import re
import os
import json
import torch
from detectron2.config import get_cfg
from detectron2.engine import DefaultPredictor

@dataclass
class FieldData:
    value: Optional[str]
    confidence: Optional[int]
    bounding_box: Optional[Tuple[int, int, int, int]]

@dataclass
class ProcessedForm:
    image_path: Optional[str] = None
    request_number: Optional[FieldData] = None
    request_date: Optional[FieldData] = None
    # collection_date removed as requested
    received_date: Optional[FieldData] = None
    surname: Optional[FieldData] = None
    given_name: Optional[FieldData] = None
    address: Optional[FieldData] = None
    suburb: Optional[FieldData] = None
    postcode: Optional[FieldData] = None
    state: Optional[FieldData] = None
    date_of_birth: Optional[FieldData] = None
    mobile_phone: Optional[FieldData] = None
    home_phone: Optional[FieldData] = None
    medicare_number: Optional[FieldData] = None
    medicare_position: Optional[FieldData] = None
    provider_number: Optional[FieldData] = None
    sex: Optional[FieldData] = None  # Added sex field as requested

class ModelManager:
    """Singleton class to manage the model instance and configuration."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
            cls._instance.predictor = None
            cls._instance.cfg = None
        return cls._instance
    
    def initialize_model(self, config_path: str, weights_path: str, use_gpu: bool = True):
        """Initialize the model with the given configuration."""
        if self.predictor is None:
            cfg = get_cfg()
            cfg.merge_from_file(config_path)
            cfg.MODEL.WEIGHTS = weights_path
            cfg.MODEL.WEIGHTS_ONLY = True
            
            if use_gpu and torch.cuda.is_available():
                cfg.MODEL.DEVICE = "cuda"
                if torch.cuda.get_device_capability()[0] >= 7:
                    cfg.MODEL.FP16_ENABLED = True
            else:
                cfg.MODEL.DEVICE = "cpu"
                if cv2.ocl.haveOpenCL():
                    cv2.ocl.setUseOpenCL(True)
            
            self.predictor = DefaultPredictor(cfg)
            self.cfg = cfg
    
    def get_predictor(self):
        return self.predictor, self.cfg
    
class BatchRequestFormProcessor:
    """Handles batch processing of multiple forms."""
    def __init__(self, model_config_path: str, model_weights_path: str, field_config_path: str, debug_mode: bool = False):
        self.debug_mode = debug_mode
        self.field_config = load_field_config(field_config_path)
        
        # Initialize model manager
        self.model_manager = ModelManager()
        self.model_manager.initialize_model(model_config_path, model_weights_path)
        
        # Initialize components that can be shared across forms
        self.data_post_processor = DataPostProcessor(debug_mode)
        self.validator = Validator()

    def process_batch(self, image_paths: List[str], batch_size: int = 4) -> Dict[str, Dict]:
        """Process multiple forms in batches."""
        results = {}
        
        # Process images in batches
        for i in range(0, len(image_paths), batch_size):
            batch_paths = image_paths[i:i + batch_size]
            batch_results = self._process_batch(batch_paths)
            results.update(batch_results)
        
        return results

    def _process_batch(self, image_paths: List[str]) -> Dict[str, Dict]:
        """Process a single batch of forms."""
        predictor, cfg = self.model_manager.get_predictor()
        batch_results = {}
        
        # Prepare all images in batch
        prepared_images = []
        for path in image_paths:
            form_preparer = FormImagePreparer(self.debug_mode)
            form_preparer.image_path = path
            prepared_images.append((path, form_preparer.prepare_form()))
        
        # Extract fields for all images in batch
        with torch.no_grad():
            for path, prepared_image in prepared_images:
                processor = SingleFormProcessor(
                    path,
                    prepared_image,
                    predictor,
                    cfg,
                    self.field_config,
                    self.data_post_processor,
                    self.validator,
                    self.debug_mode
                )
                result = processor.process_form()
                batch_results[os.path.basename(path)] = result
        
        return batch_results

class SingleFormProcessor:
    """Processes a single form using shared resources."""
    def __init__(
        self,
        image_path: str,
        prepared_image: np.ndarray,
        predictor: DefaultPredictor,
        cfg: get_cfg,
        field_config: dict,
        data_post_processor: DataPostProcessor,
        validator: Validator,
        debug_mode: bool = False
    ):
        self.image_path = image_path
        self.prepared_image = prepared_image
        self.predictor = predictor
        self.cfg = cfg
        self.field_config = field_config
        self.data_post_processor = data_post_processor
        self.validator = validator
        self.debug_mode = debug_mode
        
        self.information = {
            "request_number": None,
            "request_date": None,
            "received_date": None,
            "surname": None,
            "given_names": None,
            "sex": None,
            "address": None,
            "suburb": None,
            "postcode": None,
            "state": None,
            "date_of_birth": None,
            "mobile_phone": None,
            "home_phone": None,
            "medicare_number": None,
            "medicare_position": None,
            "provider_number": None,
            "ocr_confidence": None,
            "phone_number": None,
            "doctor_information": None
        }

    def process_form(self) -> Dict[str, Any]:
        """Process a single form using the shared predictor."""
        try:
            # Extract fields using the shared predictor
            field_extractor = FieldExtractor(self.prepared_image, self.field_config, self.debug_mode)
            extracted_fields = field_extractor.extract_field_info(self.predictor)
            
            # Map extracted fields
            self._map_extracted_fields(extracted_fields)
            
            # Post-process fields
            self._post_process_derived_fields()
            
            # Add request number from barcode
            self._add_request_number(self.image_path)
            
            # Set received date
            now_str = datetime.now().strftime('%d/%m/%Y')
            self.information["received_date"] = (now_str, 100, None)
            
            # Validate data
            validation_errors = self.validator.validate_data(self.information)
            
            # Create processed form
            processed_form = self._create_processed_form()
            
            return {
                "data": processed_form,
                "validation_errors": validation_errors
            }
            
        except Exception as e:
            logging.error(f"Error processing form {self.image_path}: {str(e)}")
            raise



    def _post_process_derived_fields(self):
        """
        Perform additional transformations using DataPostProcessor methods.
        """
        # --- Address Splitting ---
        if self.information.get("address") and self.information["address"] and self.information["address"][0]:
            full_address = self.information["address"][0]
            address_components = self.data_post_processor.split_address(full_address)

            addr_confidence = self.information["address"][1]
            addr_bbox = self.information["address"][2]

            if address_components["address"]:
                self.information["address"] = (address_components["address"], addr_confidence, addr_bbox)
            if address_components["suburb"]:
                self.information["suburb"] = (address_components["suburb"], addr_confidence, addr_bbox)
            if address_components["postcode"]:
                self.information["postcode"] = (address_components["postcode"], addr_confidence, addr_bbox)
            if address_components["state"]:
                self.information["state"] = (address_components["state"], addr_confidence, addr_bbox)
    
        # --- Medicare Number and Position ---
        if self.information.get("medicare_number") and self.information["medicare_number"] and self.information["medicare_number"][0]:
            medicare_full = self.information["medicare_number"][0]
            med_confidence = self.information["medicare_number"][1]
            med_bbox = self.information["medicare_number"][2]

            parts = medicare_full.split('/')
            if len(parts) == 2 and len(parts[0]) == 10 and len(parts[1]) == 1:
                med_number = parts[0]
                med_position = parts[1]
                self.information["medicare_number"] = (med_number, med_confidence, med_bbox)
                self.information["medicare_position"] = (med_position, med_confidence, med_bbox)

        # --- Provider Number ---
        if ((not self.information.get("provider_number") or not self.information["provider_number"] or not self.information["provider_number"][0])
            and self.information.get("doctor_information") and self.information["doctor_information"] and self.information["doctor_information"][0]):
            # Derive provider_number from doctor_information
            doc_info_val = self.information["doctor_information"][0]
            doc_conf = self.information["doctor_information"][1]
            doc_bbox = self.information["doctor_information"][2]

            provider_extracted = doc_info_val[-8:].upper()
            provider_extracted = re.sub(r'[^A-Z0-9]', '', provider_extracted)
            self.information["provider_number"] = (provider_extracted, doc_conf, doc_bbox)
        else:
            # Provider number exists, clean it according to the rules
            if self.information.get("provider_number") and self.information["provider_number"] and self.information["provider_number"][0]:
                prov_val = self.information["provider_number"][0]
                prov_conf = self.information["provider_number"][1]
                prov_bbox = self.information["provider_number"][2]

                provider_extracted = prov_val[-8:].upper()
                provider_extracted = re.sub(r'[^A-Z0-9]', '', provider_extracted)
                self.information["provider_number"] = (provider_extracted, prov_conf, prov_bbox)

        # --- Phone Numbers ---
        home_data = self.information.get("home_phone")
        mobile_data = self.information.get("mobile_phone")
        phone_data = self.information.get("phone_number")

        if (not home_data or not home_data[0]) and (not mobile_data or not mobile_data[0]) and phone_data and phone_data[0]:
            phone_str = phone_data[0]
            ph_confidence = phone_data[1]
            ph_bbox = phone_data[2]

            # Normalize spaces
            phone_str_no_spaces = re.sub(r'\s+', '', phone_str)  
            phone_numbers = self.data_post_processor.process_phone_numbers(phone_str_no_spaces)

            if phone_numbers["home_phone"] or phone_numbers["mobile_phone"]:
                # Labeled numbers found
                if phone_numbers["home_phone"]:
                    self.information["home_phone"] = (phone_numbers["home_phone"], ph_confidence, ph_bbox)
                if phone_numbers["mobile_phone"]:
                    self.information["mobile_phone"] = (phone_numbers["mobile_phone"], ph_confidence, ph_bbox)
            else:
                # No labeled matches found, try unlabeled approach
                single_numbers = re.findall(r'\d+', phone_str_no_spaces)
                if len(single_numbers) == 1:
                    # Single unlabeled number
                    number = single_numbers[0]
                    if number.startswith("04"):
                        self.information["mobile_phone"] = (number, ph_confidence, ph_bbox)
                    else:
                        self.information["home_phone"] = (number, ph_confidence, ph_bbox)
                elif len(single_numbers) == 2:
                    # Two unlabeled numbers
                    self.information["mobile_phone"] = (single_numbers[0], ph_confidence, ph_bbox)
                    self.information["home_phone"] = (single_numbers[1], ph_confidence, ph_bbox)
                # If more than 2 or none, no further action.

        # The received_date is overwritten in process_form to current time, so no need to parse it here.

    def _field_to_fielddata(self, field_name: str) -> Optional[FieldData]:
        """
        Converts a field from self.information to FieldData.
        """
        data = self.information[field_name]
        if not data or len(data) < 3:
            return None
        value, confidence, bbox = data
        if value is None:
            return None
        return FieldData(value=value, confidence=confidence, bounding_box=bbox)

    def _create_processed_form(self) -> ProcessedForm:
        """
        Create a ProcessedForm dataclass instance from self.information.
        """
        return ProcessedForm(
            image_path=self.image_path,
            request_number=self._field_to_fielddata("request_number"),
            request_date=self._field_to_fielddata("request_date"),
            received_date=self._field_to_fielddata("received_date"),
            surname=self._field_to_fielddata("surname"),
            given_name=self._field_to_fielddata("given_names"),
            address=self._field_to_fielddata("address"),
            suburb=self._field_to_fielddata("suburb"),
            postcode=self._field_to_fielddata("postcode"),
            state=self._field_to_fielddata("state"),
            date_of_birth=self._field_to_fielddata("date_of_birth"),
            mobile_phone=self._field_to_fielddata("mobile_phone"),
            home_phone=self._field_to_fielddata("home_phone"),
            medicare_number=self._field_to_fielddata("medicare_number"),
            medicare_position=self._field_to_fielddata("medicare_position"),
            provider_number=self._field_to_fielddata("provider_number"),
            sex=self._field_to_fielddata("sex")
        )

    def _add_request_number(self, image: str) -> List[str]:
        """
        Function to read barcodes from an image.
        """
        img = cv2.imread(image)
        detectedBarcodes = decode(img) 
        
        if not detectedBarcodes:
            return None
        
        decoded_data = []
        for barcode in detectedBarcodes:
            if barcode.data:
                decoded_data.append(barcode.data.decode('utf-8'))

        if decoded_data:
            for d in decoded_data:
                if self.validator.is_valid_request_number(d):
                    self.information["request_number"] = (d, 100, None)
                    break
        else:
            self.information["request_number"] = None

    def print_information(self) -> None:
        """
        Prints the information extracted from the form.
        """
        for key, value in self.information.items():
            print(f"{key}: {value}")

    def get_ocr(self) -> float:
        ocr = 0
        
        for i, field in enumerate(self.information):
            if self.information[field] is not None:
                ocr += self.information[field][1]
                i += 1

        ocr /= i + 1
        return ocr


def load_field_config(config_path: str) -> dict:
    with open(config_path, 'r') as config_file:
        return json.load(config_file)
