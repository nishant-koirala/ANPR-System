#!/usr/bin/env python3
"""
NEPALI ANPR - Automatic Number Plate Recognition System
Main application entry point
"""

import sys
import os
import cv2
import numpy as np
from datetime import datetime
from collections import defaultdict

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.dirname(__file__))

from PyQt5.QtWidgets import QApplication, QTableWidgetItem, QLabel
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from src.ui.main_window import PlateDetectorDashboard
from config.settings import (DEBUG_OCR_VERBOSE, DEBUG_SAVE_IMAGES, MIN_DETECTIONS_FOR_FINAL, 
                             CONFIDENCE_THRESHOLD_FINAL, IMMEDIATE_FINALIZATION_THRESHOLD)
from src.threading.frame_worker import FrameWorker

class ANPRApplication(PlateDetectorDashboard):
    """Main ANPR Application extending the UI"""

    # Signal to request background processing of a frame
    frameRequested = pyqtSignal(object, int, bool, str, bool)

    def __init__(self):
        super().__init__()

        # Initialize background worker thread (Phase 1)
        self.worker_thread = QThread(self)
        self.worker = FrameWorker()
        self.worker.moveToThread(self.worker_thread)

        # Wire signals
        self.frameRequested.connect(self.worker.process_frame)
        self.worker.sig_frameProcessed.connect(self.on_worker_frame_processed)
        self.worker.sig_error.connect(self.on_worker_error)
        # Connect tracker type change from UI to worker slot for runtime switching
        try:
            self.trackerTypeChanged.connect(self.worker.set_tracker_type)
        except Exception:
            pass

        self.worker_thread.start()

        # Pass debug directory to worker if available
        if hasattr(self, 'debug_dir'):
            try:
                self.worker.set_debug_dir(self.debug_dir)
            except Exception:
                pass

    def process_frame(self, frame_or_path, preview=False):
        """Enqueue frame for processing in the worker (keeps UI responsive)."""
        try:
            # Support both in-memory frames and file paths
            if isinstance(frame_or_path, np.ndarray):
                frame = frame_or_path
            else:
                frame = cv2.imread(frame_or_path)
            if frame is None or (hasattr(frame, 'size') and frame.size == 0):
                return

            # Emit to worker
            self.frameRequested.emit(frame, self.frame_counter, self.hide_bboxes, self.license_format, bool(preview))
        except Exception as e:
            print(f"process_frame enqueue error: {e}")

    def on_worker_frame_processed(self, result):
        """Handle processed frame results on the UI thread."""
        try:
            show_img = result.get('frame', None)
            tracks = result.get('tracks', [])
            plates = result.get('plates', [])
            preview = result.get('preview', False)

            vehicles_with_plates = set()

            # Map and register vehicle IDs
            for item in tracks:
                try:
                    x1, y1, x2, y2, sort_id = item
                    sort_id = int(sort_id)
                    if sort_id not in self.vehicle_id_map:
                        self.vehicle_id_map[sort_id] = len(self.vehicle_id_map) + 1
                    continuous_id = self.vehicle_id_map[sort_id]
                    self.unique_vehicles.add(continuous_id)
                except Exception:
                    continue

            # Process each plate OCR result
            for p in plates:
                try:
                    sort_id = int(p['sort_id'])
                    abs_px1, abs_py1, abs_px2, abs_py2 = p['abs_bbox']
                    plate_img = p['plate_img']
                    plate_text = p['text']
                    ocr_confidence = p['confidence']

                    continuous_id = self.vehicle_id_map.get(sort_id, sort_id)

                    is_valid = plate_text is not None
                    if DEBUG_OCR_VERBOSE:
                        print(f"DEBUG: OCR result for vehicle {continuous_id}: text='{plate_text}', confidence={ocr_confidence}")
                    print(f"DEBUG MAIN: Vehicle {continuous_id} - OCR returned: text='{plate_text}', conf={ocr_confidence}")

                    self.add_plate_to_preview(plate_img, continuous_id, plate_text, ocr_confidence, is_valid)

                    if is_valid:
                        self.valid_plates_count += 1
                    else:
                        self.missed_plates_count += 1

                    if plate_text is not None:
                        # Candidate/finalization logic remains unchanged
                        self.add_plate_candidate(continuous_id, plate_text, ocr_confidence if ocr_confidence is not None else 0.0)
                        final_plate_info = self.get_final_plate_for_vehicle(continuous_id)

                        if final_plate_info:
                            final_plate_text = final_plate_info['text']
                            final_confidence = final_plate_info['confidence']

                            clean_text = final_plate_text.replace(' ', '').replace('\n', '')
                            if self.license_format == 'format1':
                                expected_lengths = {7}
                            elif self.license_format == 'format2':
                                expected_lengths = {6}
                            else:
                                expected_lengths = {6, 7}

                            if len(clean_text) in expected_lengths and final_confidence >= IMMEDIATE_FINALIZATION_THRESHOLD:
                                plate_info = {
                                    'text': final_plate_text,
                                    'confidence': final_confidence,
                                    'bbox': [abs_px1, abs_py1, abs_px2, abs_py2],
                                    'timestamp': datetime.now()
                                }

                                self.detected_plates.append(plate_info)
                                self.add_detection_to_table(continuous_id, final_plate_text, final_confidence, plate_img)
                                vehicles_with_plates.add(continuous_id)

                                if (show_img is not None) and (not self.hide_bboxes):
                                    cv2.putText(show_img, f"{final_plate_text} ({final_confidence:.2f})",
                                                (abs_px1, max(0, abs_py1-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                except Exception:
                    continue

            # Draw vehicle bounding boxes for vehicles with finalized plates
            if (show_img is not None) and (not self.hide_bboxes):
                for item in tracks:
                    try:
                        x1, y1, x2, y2, sort_id = item
                        sort_id = int(sort_id)
                        continuous_id = self.vehicle_id_map.get(sort_id, sort_id)
                        if continuous_id in vehicles_with_plates:
                            cv2.rectangle(show_img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                            if continuous_id in self.vehicle_final_plates:
                                plate_text = self.vehicle_final_plates[continuous_id]['text']
                                cv2.putText(show_img, f"Vehicle {continuous_id}: {plate_text}",
                                            (int(x1), max(0, int(y1)-10)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    except Exception:
                        continue

            # Cache detections for smooth playback
            self.cached_detections = []
            for item in tracks:
                try:
                    x1, y1, x2, y2, sort_id = item
                    sort_id = int(sort_id)
                    continuous_id = self.vehicle_id_map.get(sort_id, sort_id)
                    self.cached_detections.append([x1, y1, x2, y2, continuous_id, 'Vehicle'])
                except Exception:
                    continue

            # Update counters and dashboard
            self.total_tracked = len(self.vehicle_id_map)
            self.unique_plates_detected = len(self.plate_ownership)
            self.update_vehicle_counter()
            self.update_dashboard_cards()

            # Show processed frame if requested
            if preview and (show_img is not None):
                self.show_plain_frame(show_img)
        except Exception as e:
            print(f"on_worker_frame_processed error: {e}")

    def on_worker_error(self, msg: str):
        try:
            print(msg)
        except Exception:
            pass
    
    def add_plate_candidate(self, vehicle_id, plate_text, confidence):
        """Add plate candidate for vehicle"""
        # Check if plate is already owned by another vehicle
        if plate_text in self.plate_ownership:
            existing_owner = self.plate_ownership[plate_text]
            if existing_owner != vehicle_id:
                existing_confidence = self.vehicle_final_plates.get(existing_owner, {}).get('confidence', 0)
                if confidence > existing_confidence + 0.1:
                    self.remove_plate_from_vehicle(existing_owner, plate_text)
                    self.plate_ownership[plate_text] = vehicle_id
                else:
                    return
        
        # Add to candidates
        candidates = self.vehicle_plate_candidates[vehicle_id]
        
        # Update existing or add new candidate
        for i, (existing_plate, existing_conf, count) in enumerate(candidates):
            if existing_plate == plate_text:
                new_conf = max(existing_conf, confidence)
                candidates[i] = (plate_text, new_conf, count + 1)
                return
        
        candidates.append((plate_text, confidence, 1))
        candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
        self.vehicle_plate_candidates[vehicle_id] = candidates[:5]
    
    def get_final_plate_for_vehicle(self, vehicle_id):
        """Get final plate assignment for vehicle"""
        if vehicle_id in self.vehicle_final_plates:
            return self.vehicle_final_plates[vehicle_id]
        
        candidates = self.vehicle_plate_candidates[vehicle_id]
        if not candidates:
            return None
        
        # Check for finalization
        for plate_text, confidence, count in candidates:
            if count >= self.min_detections_for_final and confidence >= self.confidence_threshold_final:
                final_info = {
                    'text': plate_text,
                    'confidence': confidence,
                    'detection_count': count,
                    'finalized': True
                }
                
                self.vehicle_final_plates[vehicle_id] = final_info
                self.plate_ownership[plate_text] = vehicle_id
                return final_info
        
        # Immediate finalization for good detections
        if candidates:
            best_candidate = candidates[0]
            if best_candidate[1] >= IMMEDIATE_FINALIZATION_THRESHOLD:
                final_info = {
                    'text': best_candidate[0],
                    'confidence': best_candidate[1],
                    'detection_count': best_candidate[2],
                    'finalized': True
                }
                
                self.vehicle_final_plates[vehicle_id] = final_info
                self.plate_ownership[best_candidate[0]] = vehicle_id
                return final_info
        
        return None
    
    def remove_plate_from_vehicle(self, vehicle_id, plate_text):
        """Remove plate assignment from vehicle"""
        if vehicle_id in self.vehicle_final_plates:
            if self.vehicle_final_plates[vehicle_id]['text'] == plate_text:
                del self.vehicle_final_plates[vehicle_id]
        
        candidates = self.vehicle_plate_candidates[vehicle_id]
        self.vehicle_plate_candidates[vehicle_id] = [
            (p, c, count) for p, c, count in candidates if p != plate_text
        ]
    
    def add_detection_to_table(self, track_id, plate_text, confidence, plate_img):
        """Add detection to the results table with cropped plate image"""
        now = datetime.now()
        date_str = now.strftime("%Y/%m/%d")
        time_str = now.strftime("%H:%M:%S")
        
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setRowHeight(row, 80)  # Set height for image
        
        # Column 0: Serial number
        self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        
        # Column 1: Plate image
        plate_label = QLabel()
        try:
            # Convert plate image to QPixmap
            plate_rgb = cv2.cvtColor(plate_img, cv2.COLOR_BGR2RGB)
            h, w, ch = plate_rgb.shape
            bytes_per_line = ch * w
            qt_img = QImage(plate_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            plate_pixmap = QPixmap.fromImage(qt_img).scaled(100, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            plate_label.setPixmap(plate_pixmap)
            plate_label.setAlignment(Qt.AlignCenter)
            self.table.setCellWidget(row, 1, plate_label)
        except Exception as e:
            print(f"Error adding plate image to table: {e}")
            self.table.setItem(row, 1, QTableWidgetItem("Image Error"))
        
        # Other columns
        self.table.setItem(row, 2, QTableWidgetItem(f"{plate_text} (V{track_id})"))
        self.table.setItem(row, 3, QTableWidgetItem("Visitor"))
        self.table.setItem(row, 4, QTableWidgetItem(date_str))
        self.table.setItem(row, 5, QTableWidgetItem(time_str))
        self.table.setItem(row, 6, QTableWidgetItem(f"Entry Gate (Conf: {confidence:.2f})"))

    def update_vehicle_counter(self):
        """Update vehicle counter display"""
        finalized_count = len([v for v in self.vehicle_final_plates.values() if v.get('finalized', False)])
        total_tracked = len(self.vehicle_id_map)
        unique_plates = len(self.plate_ownership)
        
        self.vehicle_counter_label.setText(
            f"Vehicles with Readable Plates: {finalized_count} | Total Tracked: {total_tracked} | Unique Plates: {unique_plates}"
        )

    def closeEvent(self, event):
        """Ensure background worker is stopped before base cleanup."""
        try:
            if hasattr(self, 'worker_thread') and self.worker_thread is not None:
                self.worker_thread.quit()
                self.worker_thread.wait(5000)
        except Exception as e:
            print(f"Worker thread shutdown error: {e}")
        super().closeEvent(event)

def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    
    # Create and show main window
    anpr_app = ANPRApplication()
    anpr_app.show()
    
    # Start event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
