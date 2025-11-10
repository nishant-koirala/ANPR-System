"""
Two-Stage Character Recognition Module
Uses YOLO for character segmentation and CNN for classification
"""

import os
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import transforms
from PIL import Image
from ultralytics import YOLO
import json

from config.settings import (
    TWO_STAGE_YOLO_MODEL, TWO_STAGE_CNN_MODEL, TWO_STAGE_LABELS_FILE,
    TWO_STAGE_CONF_THRESHOLD, TWO_STAGE_ROW_TOLERANCE, DEBUG_OCR_VERBOSE
)


class NepaliCharacterCNN(nn.Module):
    """CNN model for Nepali character classification (New Training Model)"""
    
    def __init__(self, num_classes):
        super(NepaliCharacterCNN, self).__init__()
        self.conv1 = nn.Conv2d(3, 6, 5)
        self.pool = nn.MaxPool2d(2, 2)
        self.conv2 = nn.Conv2d(6, 16, 5)
        self.fc1 = nn.Linear(16 * 5 * 5, 120)
        self.fc2 = nn.Linear(120, 84)
        self.fc3 = nn.Linear(84, num_classes)

    def forward(self, x):
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = torch.flatten(x, 1)
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        x = self.fc3(x)
        return x


class CharacterRecognizer:
    """Two-stage character recognition using YOLO + CNN"""
    
    def __init__(self):
        """Initialize YOLO and CNN models"""
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Load class labels
        try:
            with open(TWO_STAGE_LABELS_FILE, 'r', encoding='utf-8') as f:
                self.class_names = json.load(f)
            if DEBUG_OCR_VERBOSE:
                print(f"Loaded {len(self.class_names)} character classes")
        except Exception as e:
            print(f"Error loading labels file: {e}")
            self.class_names = []
        
        # Load YOLO model for character segmentation
        try:
            if os.path.exists(TWO_STAGE_YOLO_MODEL):
                self.yolo_model = YOLO(TWO_STAGE_YOLO_MODEL)
                if DEBUG_OCR_VERBOSE:
                    print(f"Loaded YOLO model from {TWO_STAGE_YOLO_MODEL}")
            else:
                print(f"YOLO model not found at {TWO_STAGE_YOLO_MODEL}")
                self.yolo_model = None
        except Exception as e:
            print(f"Error loading YOLO model: {e}")
            self.yolo_model = None
        
        # Load CNN model for character classification
        try:
            if os.path.exists(TWO_STAGE_CNN_MODEL) and len(self.class_names) > 0:
                self.cnn_model = NepaliCharacterCNN(num_classes=len(self.class_names)).to(self.device)
                self.cnn_model.load_state_dict(torch.load(TWO_STAGE_CNN_MODEL, map_location=self.device))
                self.cnn_model.eval()
                if DEBUG_OCR_VERBOSE:
                    print(f"Loaded CNN model from {TWO_STAGE_CNN_MODEL}")
            else:
                print(f"CNN model not found at {TWO_STAGE_CNN_MODEL}")
                self.cnn_model = None
        except Exception as e:
            print(f"Error loading CNN model: {e}")
            self.cnn_model = None
        
        # Image preprocessing transform (32x32 for new model)
        self.transform = transforms.Compose([
            transforms.Resize((32, 32)),
            transforms.ToTensor(),
            transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
        ])
        
        self.initialized = (self.yolo_model is not None and 
                           self.cnn_model is not None and 
                           len(self.class_names) > 0)
    
    def is_available(self):
        """Check if the recognizer is properly initialized"""
        return self.initialized
    
    def sort_boxes_strict(self, boxes, row_tol=None):
        """
        Sort bounding boxes in reading order (top-left to bottom-left)
        Groups boxes into rows and sorts left-to-right within each row
        """
        if row_tol is None:
            row_tol = TWO_STAGE_ROW_TOLERANCE
            
        if len(boxes) == 0:
            return []
        
        boxes = np.array(boxes)
        # Calculate y-center for each box
        y_centers = (boxes[:, 1] + boxes[:, 3]) / 2
        # Sort by y-center initially
        sorted_idx = np.argsort(y_centers)
        boxes = boxes[sorted_idx]
        
        # Group into rows based on y-center proximity
        rows = []
        current_row = [boxes[0]]
        
        for box in boxes[1:]:
            box_y_center = (box[1] + box[3]) / 2
            row_y_center = (current_row[0][1] + current_row[0][3]) / 2
            
            if abs(box_y_center - row_y_center) <= row_tol:
                current_row.append(box)
            else:
                # Sort current row by x-coordinate (left to right)
                current_row = sorted(current_row, key=lambda b: b[0])
                rows.append(current_row)
                current_row = [box]
        
        # Don't forget the last row
        current_row = sorted(current_row, key=lambda b: b[0])
        rows.append(current_row)
        
        # Flatten rows back to single list
        sorted_boxes = [b.tolist() for row in rows for b in row]
        return sorted_boxes
    
    def recognize_characters(self, plate_image):
        """
        Recognize characters from a plate image using two-stage pipeline
        
        Args:
            plate_image: OpenCV image (BGR format) of the license plate
            
        Returns:
            tuple: (recognized_text, confidence_score) or (None, None) if failed
        """
        if not self.initialized:
            if DEBUG_OCR_VERBOSE:
                print("Two-stage recognizer not initialized")
            return None, None
        
        try:
            # Check image validity
            if plate_image is None or plate_image.size == 0:
                if DEBUG_OCR_VERBOSE:
                    print("Invalid plate image")
                return None, None
            
            if DEBUG_OCR_VERBOSE:
                print(f"Processing plate image of size {plate_image.shape}")
            
            # Stage 1: Detect characters using YOLO
            if DEBUG_OCR_VERBOSE:
                print(f"Running YOLO character detection with conf={TWO_STAGE_CONF_THRESHOLD}")
            
            results = self.yolo_model.predict(
                source=plate_image,
                conf=TWO_STAGE_CONF_THRESHOLD,
                save=False,
                verbose=False
            )
            
            if len(results) == 0 or len(results[0].boxes) == 0:
                if DEBUG_OCR_VERBOSE:
                    print("No characters detected by YOLO - try lowering TWO_STAGE_CONF_THRESHOLD")
                return None, None
            
            # Extract bounding boxes
            boxes = results[0].boxes.xyxy.cpu().numpy()
            boxes = [list(map(int, b)) for b in boxes]
            
            if DEBUG_OCR_VERBOSE:
                print(f"YOLO detected {len(boxes)} character boxes")
            
            # Sort boxes in reading order
            sorted_boxes = self.sort_boxes_strict(boxes)
            
            # Stage 2: Classify each character using CNN
            recognized_chars = []
            confidences = []
            
            for i, box in enumerate(sorted_boxes):
                x1, y1, x2, y2 = box
                
                # Crop character region
                cropped = plate_image[y1:y2, x1:x2]
                
                if cropped.size == 0:
                    if DEBUG_OCR_VERBOSE:
                        print(f"Empty crop for box {i}")
                    continue
                
                # Convert to PIL Image and preprocess
                pil_img = Image.fromarray(cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)).convert("RGB")
                x_tensor = self.transform(pil_img).unsqueeze(0).to(self.device)
                
                # Classify character
                with torch.no_grad():
                    output = self.cnn_model(x_tensor)
                    # Get softmax probabilities for confidence
                    probs = F.softmax(output, dim=1)
                    confidence, pred_idx = torch.max(probs, dim=1)
                    pred_idx = pred_idx.item()
                    confidence = confidence.item()
                    
                    if pred_idx < len(self.class_names):
                        pred_char = self.class_names[pred_idx]
                        recognized_chars.append(pred_char)
                        confidences.append(confidence)
                        
                        if DEBUG_OCR_VERBOSE:
                            print(f"Character {i}: '{pred_char}' (confidence: {confidence:.3f})")
            
            if len(recognized_chars) == 0:
                if DEBUG_OCR_VERBOSE:
                    print("No characters recognized")
                return None, None
            
            # Combine characters into plate text
            plate_text = ''.join(recognized_chars)
            
            # Calculate average confidence
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            if DEBUG_OCR_VERBOSE:
                print(f"Recognized plate: '{plate_text}' (avg confidence: {avg_confidence:.3f})")
            
            return plate_text, avg_confidence
            
        except Exception as e:
            if DEBUG_OCR_VERBOSE:
                print(f"Error in two-stage recognition: {e}")
            import traceback
            traceback.print_exc()
            return None, None
