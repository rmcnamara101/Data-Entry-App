import re
import pytesseract
import cv2
import numpy as np

class TextProcessor:
    def __init__(self):
        # Verify Tesseract is working
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            print(f"Tesseract initialization error: {e}")
            print("Please ensure Tesseract is properly installed")
            
    def debug_image(self, image):
        """
        Debug image processing steps and save intermediate results.
        
        Args:
            image (np.ndarray): Input image
        """
        # Save original image
        cv2.imwrite('debug_1_original.png', image)
        
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        cv2.imwrite('debug_2_grayscale.png', gray)
        
        # Scale up image (sometimes helps with OCR)
        scaled = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        cv2.imwrite('debug_3_scaled.png', scaled)
        
        # Apply different preprocessing techniques
        # 1. Basic thresholding
        _, binary = cv2.threshold(scaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        cv2.imwrite('debug_4_binary.png', binary)
        
        # 2. Adaptive thresholding
        adaptive = cv2.adaptiveThreshold(scaled, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                        cv2.THRESH_BINARY, 11, 2)
        cv2.imwrite('debug_5_adaptive.png', adaptive)
        
        # Try OCR on different preprocessed versions
        results = []
        images = {
            'original': gray,
            'scaled': scaled,
            'binary': binary,
            'adaptive': adaptive
        }
        
        #custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789/'
        
        #print("\nOCR Results for different preprocessing methods:")
        for name, img in images.items():
            try:
                text = pytesseract.image_to_string(img).strip()
                data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                confidence = np.mean([conf for conf in data['conf'] if conf != -1]) if any(conf != -1 for conf in data['conf']) else -1
                
                results.append((name, text, confidence))
                #print(f"{name:10}: '{text}' (Confidence: {confidence:.1f})")
            except Exception as e:
                string = f"Error processing {name}: {e}"
        
        return results
            
    def extract_text(self, region_image, psm=6):
        """
        Extract text from a given image region with improved preprocessing.
        
        Args:
            region_image (np.ndarray): Cropped image of the field region.
        
        Returns:
            tuple: Extracted text and confidence score.
        """

        custom_config = f'--psm {psm}'
        # Ensure image is properly loaded
        if region_image is None or region_image.size == 0:
            print("Error: Empty or invalid image")
            return "", -1
            
        try:
            # Scale up image
            scaled = cv2.resize(region_image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            
            # Convert to grayscale if needed
            if len(scaled.shape) == 3:
                gray = cv2.cvtColor(scaled, cv2.COLOR_BGR2GRAY)
            else:
                gray = scaled
                
            # Apply OTSU's thresholding
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Configure Tesseract
            #custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789/'
            
            # Perform OCR with verbose output
            #print("\nAttempting OCR...")
            data = pytesseract.image_to_data(binary, output_type=pytesseract.Output.DICT, config=custom_config)
            
            # Print detailed OCR data
            #print("\nRaw OCR output:")
            #for i in range(len(data['text'])):
                #if data['conf'][i] != -1:  # Skip empty results
                    #print(f"Word: '{data['text'][i]}', Confidence: {data['conf'][i]}")
            
            # Filter and process results
            valid_indices = [i for i, conf in enumerate(data['conf']) if conf != -1 and data['text'][i].strip()]
            
            if not valid_indices:
                print("No valid text detected")
                return "", -1
                
            text = "".join(data['text'][i].strip() for i in valid_indices)
            confidence = sum(data['conf'][i] for i in valid_indices) / len(valid_indices)
            
            #print(f"\nFinal result: '{text}' with confidence {confidence:.1f}")
            return text, confidence
            
        except Exception as e:
            #print(f"Error during text extraction: {e}")
            return "", -1
