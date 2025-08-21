import numpy as np
import torch
from ultralytics import YOLO
from config import settings

class VehicleDetector:
    def __init__(self, device='cuda', model_path=None):
        self.device = device
        # Use provided model_path or get from settings
        self.model_path = model_path or getattr(settings, 'VEHICLE_MODEL_PATH', 'yolov8m.pt')
        self.model = YOLO(self.model_path)
        
        if device == 'cuda' and torch.cuda.is_available():
            self.model.to(device)
    
    def reload_model(self, model_path=None, device=None, progress_callback=None):
        """Reload model with new path or device"""
        if model_path:
            self.model_path = model_path
        if device:
            self.device = device
        
        print(f"Downloading/Loading vehicle model: {self.model_path}")
        if progress_callback:
            progress_callback(f"Loading model: {self.model_path}")
        
        try:
            # YOLO will automatically download if model doesn't exist
            self.model = YOLO(self.model_path, verbose=True)  # Enable verbose for download progress
            print(f"Successfully loaded model: {self.model_path}")
            if progress_callback:
                progress_callback(f"Model loaded: {self.model_path}")
            
            if self.device == 'cuda' and torch.cuda.is_available():
                print(f"Moving model to {self.device}")
                self.model.to(self.device)
                if progress_callback:
                    progress_callback(f"Model ready on {self.device}")
        except Exception as e:
            error_msg = f"Failed to load model {self.model_path}: {e}"
            print(error_msg)
            if progress_callback:
                progress_callback(error_msg)
            raise
    
    def detect_vehicles(self, frame):
        """Detect vehicles in frame using YOLOv8"""
        # Get current settings dynamically
        model_verbose = getattr(settings, 'MODEL_VERBOSE', False)
        model_image_size = getattr(settings, 'MODEL_IMAGE_SIZE', 640)
        vehicle_confidence_threshold = getattr(settings, 'VEHICLE_CONFIDENCE_THRESHOLD', 0.15)
        vehicle_classes = getattr(settings, 'VEHICLE_CLASSES', {2: 0.4, 3: 0.25, 5: 0.4, 7: 0.4, 1: 0.3})
        
        results = self.model(frame, verbose=model_verbose, device=self.device, imgsz=model_image_size, conf=vehicle_confidence_threshold)
        detections = []
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    
                    # Use class-specific confidence thresholds
                    if cls in vehicle_classes and conf >= vehicle_classes[cls]:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        detections.append([x1, y1, x2, y2, conf])
        
        return np.array(detections) if detections else np.empty((0, 5))
    
