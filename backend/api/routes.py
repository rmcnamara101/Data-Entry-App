from fastapi import FastAPI, File, UploadFile, Form, Response
from backend.not_using.ImagePreprocessor import ImagePreprocessor
import json
import cv2
import numpy as np

app = FastAPI()

@app.post("/api/process-image")
async def process_image(
    image: UploadFile = File(...),
    params: str = Form(...)
):
    params_dict = json.loads(params)
    
    # Read image
    image_data = await image.read()
    nparr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # Process image using your existing ImagePreprocessor
    processor = ImagePreprocessor()
    processed = processor.process_image(
        img,
        threshold=params_dict['threshold'],
        min_contour_area=params_dict['minContourArea']
    )
    
    # Return processed image
    success, encoded_img = cv2.imencode('.PNG', processed)
    return Response(content=encoded_img.tobytes(), media_type="image/png")