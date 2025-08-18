import numpy as np
import torch
from ultralytics import YOLO
from config.settings import VEHICLE_MODEL_PATH, VEHICLE_CLASSES, VEHICLE_CONFIDENCE_THRESHOLD, MODEL_IMAGE_SIZE, MODEL_VERBOSE

class VehicleDetector:
    def __init__(self, device='cuda'):
        self.device = device
        self.model = YOLO(VEHICLE_MODEL_PATH)
        
        if device == 'cuda' and torch.cuda.is_available():
            self.model.to(device)
    
    def detect_vehicles(self, frame):
        """Detect vehicles in frame using YOLOv8"""
        results = self.model(frame, verbose=MODEL_VERBOSE, device=self.device, imgsz=MODEL_IMAGE_SIZE, conf=VEHICLE_CONFIDENCE_THRESHOLD)
        detections = []
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    
                    # Use class-specific confidence thresholds
                    if cls in VEHICLE_CLASSES and conf >= VEHICLE_CLASSES[cls]:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        detections.append([x1, y1, x2, y2, conf])
        
        return np.array(detections) if detections else np.empty((0, 5))
