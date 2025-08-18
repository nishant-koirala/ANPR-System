import numpy as np
import torch
from ultralytics import YOLO
from config.settings import PLATE_MODEL_PATH, PLATE_CONFIDENCE_THRESHOLD, DEBUG_OCR_VERBOSE, MODEL_IMAGE_SIZE, MODEL_VERBOSE

class PlateDetector:
    def __init__(self, device='cuda'):
        self.device = device
        self.model = YOLO(PLATE_MODEL_PATH)
        
        if device == 'cuda' and torch.cuda.is_available():
            self.model.to(device)
    
    def detect_plates_in_roi(self, roi_image):
        """Detect license plates in a region of interest"""
        plate_results = self.model(roi_image, verbose=MODEL_VERBOSE, device=self.device, imgsz=MODEL_IMAGE_SIZE, conf=PLATE_CONFIDENCE_THRESHOLD)
        plate_detections = []
        
        for result in plate_results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    conf = box.conf[0].cpu().numpy()
                    plate_detections.append([x1, y1, x2, y2, conf])
        
        # Debug output
        if len(plate_detections) > 0 and DEBUG_OCR_VERBOSE:
            print(f"DEBUG: Found {len(plate_detections)} plate detections with confidences: {[d[4] for d in plate_detections]}")
        
        return plate_detections
