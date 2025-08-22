import os
import urllib.request
from PyQt5.QtWidgets import QMessageBox

def download_model(model_name, save_dir, parent_widget=None):
    """Download YOLO model if not present locally.
    
    Args:
        model_name (str): Name of the model file to download
        save_dir (str): Directory to save the model
        parent_widget (QWidget, optional): Parent widget for dialogs
        
    Returns:
        bool: True if download successful or model already exists, False otherwise
    """
    # Ensure save directory exists
    os.makedirs(save_dir, exist_ok=True)
    
    # Model URL mapping
    model_urls = {
        "yolov8n.pt": "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt",
        "yolov8s.pt": "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8s.pt",
        "yolov8m.pt": "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8m.pt",
        "yolov8l.pt": "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8l.pt",
        "yolov8x.pt": "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8x.pt",
    }
    
    model_path = os.path.join(save_dir, model_name)
    
    # Check if model already exists
    if os.path.exists(model_path):
        return True
    
    # Get model URL
    if model_name not in model_urls:
        QMessageBox.critical(parent_widget, "Download Error", f"Model {model_name} not supported for download.")
        return False
    
    model_url = model_urls[model_name]
    
    try:
        # Download with progress
        urllib.request.urlretrieve(model_url, model_path)
        return True
    except Exception as e:
        QMessageBox.critical(parent_widget, "Download Error", f"Failed to download model: {str(e)}")
        return False