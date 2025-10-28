#!/usr/bin/env python3
"""
NEPALI ANPR - Automatic Number Plate Recognition System
Main application entry point
"""

import sys
import os
# Set the environment variable for Ultralytics to use the models/ directory
os.environ['ULTRALYTICS_HOME'] = os.path.join(os.path.dirname(__file__), 'models')

import cv2
import numpy as np
from datetime import datetime
from collections import defaultdict

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
sys.path.append(os.path.dirname(__file__))

from PyQt5.QtWidgets import QApplication, QTableWidgetItem, QLabel, QMessageBox
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from src.ui.main_window import PlateDetectorDashboard
from config.settings import (DEBUG_OCR_VERBOSE, DEBUG_SAVE_IMAGES, MIN_DETECTIONS_FOR_FINAL, 
                             CONFIDENCE_THRESHOLD_FINAL, IMMEDIATE_FINALIZATION_THRESHOLD)
from src.threading.frame_worker import FrameWorker

# Database imports
try:
    from src.db import Database, get_database
    from src.db.toggle_manager import ToggleManager
    DATABASE_AVAILABLE = True
except ImportError as e:
    print(f"Database not available: {e}")
    DATABASE_AVAILABLE = False

class ANPRApplication(PlateDetectorDashboard):
    """Main ANPR Application extending the UI"""

    # Signal to request background processing of a frame
    frameRequested = pyqtSignal(object, int, bool, str, bool)
    # Signal to request graceful stop of background worker
    stopRequested = pyqtSignal()
    # Signal to request vehicle model reload in worker
    reloadRequested = pyqtSignal(str)

    def __init__(self, auth_manager=None):
        super().__init__(auth_manager=auth_manager)

        # Initialize database and toggle manager
        self.db = get_database()
        # 30 second cooldown with 80% similarity matching for EXIT
        self.toggle_manager = ToggleManager(
            database=self.db, 
            cooldown_minutes=0.5,
            exit_similarity_threshold=0.8
        )
        self.camera_id = None
        self.init_database()

        # Initialize background worker thread (Phase 1)
        self.worker_thread = QThread(self)
        self.worker = FrameWorker()
        self.worker.moveToThread(self.worker_thread)

        # Wire signals
        self.frameRequested.connect(self.worker.process_frame)
        self.worker.sig_frameProcessed.connect(self.on_worker_frame_processed)
        self.worker.sig_error.connect(self.on_worker_error)
        # Model reload wiring
        self.reloadRequested.connect(self.worker.reload_vehicle_model)
        self.worker.sig_reloadProgress.connect(self.on_worker_reload_progress)
        self.worker.sig_reloadFinished.connect(self.on_worker_reload_finished)
        # Connect tracker type change from UI to worker slot for runtime switching
        try:
            self.trackerTypeChanged.connect(self.worker.set_tracker_type)
        except Exception:
            pass
        # Stop request signal to ensure stop() runs in worker thread
        try:
            self.stopRequested.connect(self.worker.stop)
        except Exception:
            pass

        self.worker_thread.start()

        # Pass debug directory to worker if available
        if hasattr(self, 'debug_dir'):
            try:
                self.worker.set_debug_dir(self.debug_dir)
            except Exception:
                pass

    def init_database(self):
        """Initialize database connection and components"""
        if not DATABASE_AVAILABLE:
            print("Database components not available - running without database logging")
            return
        
        try:
            self.db = get_database()
            self.db.create_tables()
            
            # Initialize toggle manager with reasonable settings
            self.toggle_manager = ToggleManager(
                database=self.db,
                min_confidence=0.7,  # Only log plates with 70%+ confidence
                cooldown_minutes=2    # 2-minute cooldown between same plate detections
            )
            
            # Get or create default camera
            self.camera_id = self.db.get_or_create_camera("MAIN_CAM", "Video Processing")
            
            # Note: RBAC authentication is handled by auth_manager passed to __init__
            # No need for separate simple_auth
            
            print(f"✅ Database initialized - Camera ID: {self.camera_id}")
            
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            self.db = None
            self.toggle_manager = None
            self.camera_id = None
            self.simple_auth = None

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
                                expected_lengths = {4, 7}  # Allow 4-digit partial plates
                            elif self.license_format == 'format2':
                                expected_lengths = {4, 6}  # Allow 4-digit partial plates
                            else:
                                expected_lengths = {4, 6, 7}  # Allow partial and full plates

                            print(f"DEBUG FINALIZATION: plate='{final_plate_text}', clean='{clean_text}', len={len(clean_text)}, conf={final_confidence}, expected_lens={expected_lengths}")
                            print(f"DEBUG: Length check: {len(clean_text)} in {expected_lengths} = {len(clean_text) in expected_lengths}")
                            print(f"DEBUG: Confidence check: {final_confidence} >= {IMMEDIATE_FINALIZATION_THRESHOLD} = {final_confidence >= IMMEDIATE_FINALIZATION_THRESHOLD}")
                            
                            if len(clean_text) in expected_lengths and final_confidence >= IMMEDIATE_FINALIZATION_THRESHOLD:
                                print(f"DEBUG: FINALIZATION PASSED - Logging to database: {final_plate_text}")
                                print(f"DEBUG: About to create plate_info and add to detected_plates")
                                plate_info = {
                                    'text': final_plate_text,
                                    'confidence': final_confidence,
                                    'bbox': [abs_px1, abs_py1, abs_px2, abs_py2],
                                    'timestamp': datetime.now()
                                }

                                self.detected_plates.append(plate_info)
                                self.add_detection_to_table(continuous_id, final_plate_text, final_confidence, plate_img)
                                vehicles_with_plates.add(continuous_id)
                                
                                # Add vehicle to log display
                                try:
                                    self.add_vehicle_to_log(continuous_id, final_plate_text, plate_img, "PRESENT")
                                except Exception as e:
                                    print(f"Error adding vehicle to log display: {e}")
                                
                                print(f"DEBUG: About to start database logging for {final_plate_text}")
                                # Log to database with image data
                                try:
                                    image_data = p.get('image_data', {})
                                    print(f"DEBUG: Calling log_detection_to_database for {final_plate_text}")
                                    print(f"DEBUG: image_data keys: {list(image_data.keys()) if image_data else 'None'}")
                                    self.log_detection_to_database(final_plate_text, final_confidence, 
                                                                  f"frame_{self.frame_counter}", 
                                                                  [abs_px1, abs_py1, abs_px2, abs_py2],
                                                                  image_data)
                                    print(f"DEBUG: Database logging completed for {final_plate_text}")
                                except Exception as e:
                                    print(f"DEBUG: Exception in database logging: {e}")
                                    import traceback
                                    traceback.print_exc()
                            else:
                                print(f"DEBUG: FINALIZATION FAILED - len check: {len(clean_text) in expected_lengths}, conf check: {final_confidence >= IMMEDIATE_FINALIZATION_THRESHOLD}")

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

            # Cache ALL vehicle detections for smooth playback (not just finalized ones)
            self.cached_detections = []
            for item in tracks:
                try:
                    x1, y1, x2, y2, sort_id = item
                    sort_id = int(sort_id)
                    continuous_id = self.vehicle_id_map.get(sort_id, sort_id)
                    # Show all tracked vehicles, highlight finalized ones differently
                    label = f'Vehicle {continuous_id}'
                    if continuous_id in vehicles_with_plates and continuous_id in self.vehicle_final_plates:
                        label += f': {self.vehicle_final_plates[continuous_id]["text"]}'
                    self.cached_detections.append([x1, y1, x2, y2, continuous_id, label])
                except Exception:
                    continue

            # Update counters and dashboard
            self.total_tracked = len(self.vehicle_id_map)
            self.unique_plates_detected = len(self.plate_ownership)
            self.update_vehicle_counter()
            self.update_dashboard_cards()

            # Show processed frame if requested
            if preview and (show_img is not None):
                pass  # UI counters already updated above

        except Exception as e:
            print(f"on_worker_frame_processed error: {e}")

    def log_detection_to_database(self, plate_text, confidence, source, bbox_coords, image_data=None):
        """Log detection to database using toggle manager"""
        print(f"DEBUG: log_detection_to_database called with plate={plate_text}, conf={confidence}")
        
        if not DATABASE_AVAILABLE:
            print(f"DEBUG: DATABASE_AVAILABLE is False")
            return
        if not self.db:
            print(f"DEBUG: self.db is None")
            return
        if not self.toggle_manager:
            print(f"DEBUG: self.toggle_manager is None")
            return
            
        try:
            print(f"DEBUG: Calling add_raw_log for {plate_text}")
            # First, log raw detection with image data
            raw_id = self.db.add_raw_log(
                camera_id=self.camera_id,
                frame_id=source,
                plate_text=plate_text,
                confidence=confidence,
                bbox_coords=bbox_coords,
                image_data=image_data
            )
            print(f"DEBUG: add_raw_log returned raw_id={raw_id}")
            
            print(f"DEBUG: Calling log_vehicle_detection for {plate_text}")
            # Then, process with toggle manager for intelligent entry/exit logging
            log_id = self.toggle_manager.log_vehicle_detection(
                plate_text=plate_text,
                confidence=confidence,
                raw_log_id=raw_id,
                camera_id=self.camera_id,
                session_id=f"video_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                image_data=image_data
            )
            print(f"DEBUG: log_vehicle_detection returned log_id={log_id}")
            
            if log_id:
                print(f"📊 Database logged: {plate_text} (confidence: {confidence:.2f}, log_id: {log_id})")
            else:
                print(f"📊 Detection ignored by toggle manager: {plate_text}")
                
        except Exception as e:
            print(f"❌ Database logging error: {e}")

    def on_worker_error(self, error_msg):
        """Handle worker errors on the UI thread."""
        print(f"Worker error: {error_msg}")
        QMessageBox.warning(self, "Processing Error", f"Frame processing error: {error_msg}")

    def on_worker_reload_progress(self, msg: str):
        """Update model reload progress dialog from worker messages."""
        try:
            if hasattr(self, 'model_progress_dialog') and self.model_progress_dialog is not None:
                self.model_progress_dialog.setLabelText(str(msg))
                QApplication.processEvents()
        except Exception:
            pass

    def on_worker_reload_finished(self, success: bool, message: str):
        """Handle completion of background model reload."""
        try:
            if hasattr(self, 'model_progress_dialog') and self.model_progress_dialog is not None:
                self.model_progress_dialog.close()
                self.model_progress_dialog = None
            if success:
                QMessageBox.information(self, "Settings Saved", "Settings have been saved and model loaded successfully!")
            else:
                QMessageBox.warning(self, "Model Loading Error", str(message))
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
            # Check if we have new candidates that are significantly different
            candidates = self.vehicle_plate_candidates.get(vehicle_id, [])
            if candidates:
                current_finalized = self.vehicle_final_plates[vehicle_id]['text']
                latest_candidate = candidates[0][0]  # Best candidate text
                latest_confidence = candidates[0][1]  # Best candidate confidence
                
                # If latest candidate is different and has high confidence, allow re-evaluation
                if (latest_candidate != current_finalized and 
                    latest_confidence >= IMMEDIATE_FINALIZATION_THRESHOLD):
                    print(f"DEBUG: Re-evaluating vehicle {vehicle_id}: current='{current_finalized}' vs new='{latest_candidate}' (conf={latest_confidence})")
                    # Clear the finalized plate to allow re-evaluation
                    del self.vehicle_final_plates[vehicle_id]
                    if current_finalized in self.plate_ownership:
                        del self.plate_ownership[current_finalized]
                else:
                    return self.vehicle_final_plates[vehicle_id]
            else:
                return self.vehicle_final_plates[vehicle_id]
        
        candidates = self.vehicle_plate_candidates.get(vehicle_id, [])
        if not candidates:
            return None
        
        print(f"DEBUG: get_final_plate_for_vehicle({vehicle_id}) - candidates: {candidates}")
        
        # Check for finalization
        for plate_text, confidence, count in candidates:
            print(f"DEBUG: Checking candidate: {plate_text}, conf={confidence}, count={count}, min_count={self.min_detections_for_final}, min_conf={self.confidence_threshold_final}")
            if count >= self.min_detections_for_final and confidence >= self.confidence_threshold_final:
                final_info = {
                    'text': plate_text,
                    'confidence': confidence,
                    'detection_count': count,
                    'finalized': True
                }
                
                self.vehicle_final_plates[vehicle_id] = final_info
                self.plate_ownership[plate_text] = vehicle_id
                print(f"DEBUG: Finalized by count/confidence: {plate_text}")
                return final_info
        
        # Immediate finalization for good detections
        if candidates:
            best_candidate = candidates[0]
            print(f"DEBUG: Best candidate: {best_candidate[0]}, conf={best_candidate[1]}, threshold={IMMEDIATE_FINALIZATION_THRESHOLD}")
            if best_candidate[1] >= IMMEDIATE_FINALIZATION_THRESHOLD:
                final_info = {
                    'text': best_candidate[0],
                    'confidence': best_candidate[1],
                    'detection_count': best_candidate[2],
                    'finalized': True
                }
                
                self.vehicle_final_plates[vehicle_id] = final_info
                self.plate_ownership[best_candidate[0]] = vehicle_id
                print(f"DEBUG: Finalized by immediate threshold: {best_candidate[0]}")
                return final_info
        
        print(f"DEBUG: No finalization for vehicle {vehicle_id}")
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
            # Request graceful stop of pipeline threads in the worker
            try:
                if hasattr(self, 'stopRequested'):
                    self.stopRequested.emit()
            except Exception:
                pass
            if hasattr(self, 'worker_thread') and self.worker_thread is not None:
                self.worker_thread.quit()
                self.worker_thread.wait(5000)
        except Exception as e:
            print(f"Worker thread shutdown error: {e}")
        
        # Clean up database connections
        try:
            if self.db:
                self.db.close()
                print("✅ Database connections closed")
        except Exception as e:
            print(f"Error closing database: {e}")
        
        super().closeEvent(event)

def main():
    """Main application entry point"""
    
    # Restart loop - allows returning to login after logout
    while True:
        # Check if QApplication instance already exists
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        else:
            # Clear any existing widgets
            for widget in app.allWidgets():
                widget.close()
        
        # Initialize RBAC system
        try:
            from src.ui.rbac_integration import RBACManager, integrate_rbac_with_main_window
            from src.db.database import get_database
            
            # Setup RBAC manager
            db = get_database()
            rbac_manager = RBACManager(db.get_session)
            
            # Show login dialog first
            if not rbac_manager.show_login_dialog():
                # User cancelled login or authentication failed
                sys.exit(0)
            
            # Create main window after successful login with authenticated auth_manager
            anpr_app = ANPRApplication(auth_manager=rbac_manager.auth_manager)
            
            # Integrate RBAC with main window
            integrate_rbac_with_main_window(anpr_app, rbac_manager)
            
            anpr_app.show()
            
        except ImportError as e:
            print(f"RBAC system not available: {e}")
            print("Running without authentication...")
            
            # Fallback to non-authenticated mode
            anpr_app = ANPRApplication()
            anpr_app.show()
        
        # Start event loop
        exit_code = app.exec_()
        
        # If exit code is 1, restart with login screen
        # If exit code is 0, exit normally
        if exit_code != 1:
            sys.exit(exit_code)
        
        print("DEBUG: Restarting application for new login...")

if __name__ == "__main__":
    main()
