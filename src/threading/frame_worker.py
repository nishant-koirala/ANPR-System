import cv2
import numpy as np
import traceback
from datetime import datetime
from types import SimpleNamespace
import os
import sys
import threading
import time
from queue import Queue, Empty, Full

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from config import settings
from src.detection.vehicle_detector import VehicleDetector
from src.detection.plate_detector import PlateDetector
from src.ocr.plate_reader import PlateReader
from src.utils.image_processor import PlateImageProcessor
from src.utils.image_processing import expand_plate_roi
from src.utils.advanced_processing import calculate_plate_quality_score


class FrameWorker(QObject):
    """Background worker that processes frames off the UI thread.

    Emits a single aggregated result per processed frame so the UI can
    update state and widgets safely on the main thread without changing
    existing logic.
    """

    sig_frameProcessed = pyqtSignal(object)  # dict payload
    sig_error = pyqtSignal(str)
    sig_reloadProgress = pyqtSignal(str)
    sig_reloadFinished = pyqtSignal(bool, str)

    def __init__(self):
        super().__init__()
        try:
            # Device selection mirrors UI logic
            try:
                import torch
                self.device = 'cuda' if (getattr(settings, 'USE_GPU', True) and torch.cuda.is_available()) else 'cpu'
            except Exception:
                self.device = 'cpu'

            # Initialize models locally in the worker to avoid cross-thread access
            model_path = getattr(settings, 'VEHICLE_MODEL_PATH', 'yolov8m.pt')
            self.vehicle_detector = VehicleDetector(self.device, model_path)
            self.plate_detector = PlateDetector(self.device)
            self.plate_reader = PlateReader()
            self.image_processor = PlateImageProcessor()

            # Setup tracker per settings
            self.tracker_type = str(getattr(settings, 'TRACKER_TYPE', 'SORT')).upper()
            self._init_tracker()

            # For optional OCR debug saving
            self.debug_dir = None
            qsize = int(getattr(settings, 'QUEUE_SIZE', 32))
            self.q_frames: Queue = Queue(maxsize=qsize)
            self.q_ocr: Queue = Queue(maxsize=max(1, qsize * 2))

            # Thread controls
            self._stop_event = threading.Event()
            self.ocr_worker_count = 1  # keep 1 to avoid thread-unsafe OCR and GPU contention
            self._threads = []

            # Start staged pipeline threads
            self._start_pipeline_threads()
        except Exception as e:
            self.sig_error.emit(f"Worker init error: {e}")

    def set_debug_dir(self, debug_dir: str):
        """Optionally set debug directory for OCR debug output."""
        self.debug_dir = debug_dir
        try:
            if getattr(settings, 'DEBUG_SAVE_IMAGES', False) and hasattr(self.plate_reader, 'set_debug_dir'):
                self.plate_reader.set_debug_dir(debug_dir)
        except Exception:
            pass

    def _init_tracker(self):
        """Initialize tracker instance based on settings.TRACKER_TYPE."""
        try:
            if self.tracker_type == 'DEEPSORT':
                try:
                    from deep_sort_realtime.deepsort_tracker import DeepSort
                    self.tracker = DeepSort(
                        max_age=getattr(settings, 'TRACKER_MAX_AGE', 50),
                        n_init=getattr(settings, 'TRACKER_MIN_HITS', 1),
                        max_iou_distance=getattr(settings, 'TRACKER_IOU_THRESHOLD', 0.4),
                    )
                    return
                except Exception:
                    # Fallback to SORT if Deep SORT not available
                    self.tracker_type = 'SORT'
            elif self.tracker_type == 'BYTETRACK':
                # Try to initialize ByteTrack from common sources
                try:
                    # Ensure local ByteTrack repo is importable (adds '<project>/ByteTrack' to sys.path)
                    try:
                        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
                        bt_root = os.path.join(project_root, 'ByteTrack')
                        if os.path.isdir(bt_root) and bt_root not in sys.path:
                            sys.path.insert(0, bt_root)
                        if getattr(settings, 'SHOW_DEBUG_INFO', False):
                            try:
                                byte_file = os.path.join(bt_root, 'yolox', 'tracker', 'byte_tracker.py')
                                self.sig_error.emit(f"DEBUG WORKER: ByteTrack bt_root={bt_root}, exists={os.path.isdir(bt_root)}, byte_tracker.py exists={os.path.exists(byte_file)}")
                            except Exception:
                                self.sig_error.emit(f"DEBUG WORKER: ByteTrack bt_root={bt_root}, exists={os.path.isdir(bt_root)}")
                    except Exception:
                        pass
                    import_err1 = None
                    import_err2 = None
                    try:
                        from yolox.tracker.byte_tracker import BYTETracker  # YOLOX implementation
                    except Exception as e:
                        import_err1 = e
                        BYTETracker = None
                    if BYTETracker is None:
                        try:
                            from bytetrack.byte_tracker import BYTETracker  # alternative package
                        except Exception as e:
                            import_err2 = e
                            BYTETracker = None
                    if BYTETracker is None:
                        raise ImportError(f"BYTETracker not found. yolox err: {import_err1}; bytetrack err: {import_err2}")

                    bt_args = SimpleNamespace(
                        track_thresh=getattr(settings, 'BYTETRACK_TRACK_THRESH', 0.25),
                        match_thresh=getattr(settings, 'BYTETRACK_MATCH_THRESH', 0.8),
                        track_buffer=getattr(settings, 'BYTETRACK_TRACK_BUFFER', 30),
                        mot20=False,
                    )
                    fps = getattr(settings, 'VIDEO_FPS', 30)
                    try:
                        self.tracker = BYTETracker(bt_args, frame_rate=fps)
                    except TypeError:
                        # Some versions may use frame_rate without kw
                        self.tracker = BYTETracker(bt_args, fps)
                    return
                except Exception as e:
                    self.sig_error.emit(f"ByteTrack init failed, falling back to SORT: {e}")
                    self.tracker_type = 'SORT'
            # Default SORT
            from sort.sort import Sort
            self.tracker = Sort(
                max_age=getattr(settings, 'TRACKER_MAX_AGE', 50),
                min_hits=getattr(settings, 'TRACKER_MIN_HITS', 1),
                iou_threshold=getattr(settings, 'TRACKER_IOU_THRESHOLD', 0.4)
            )
        except Exception as e:
            # Ultimate fallback
            try:
                from sort.sort import Sort
                self.tracker = Sort(
                    max_age=50,
                    min_hits=1,
                    iou_threshold=0.4
                )
            except Exception:
                self.tracker = None
            self.sig_error.emit(f"Tracker init error: {e}")

    def _start_pipeline_threads(self):
        """Start GPU and OCR worker threads for the staged pipeline."""
        try:
            # GPU stage: vehicle detect + track + plate detect, dispatch OCR tasks
            t_gpu = threading.Thread(target=self._gpu_worker_loop, name="GPUStage", daemon=True)
            t_gpu.start()
            self._threads.append(t_gpu)

            # OCR stage: one worker to avoid thread-unsafe OCR/GPU conflicts
            for i in range(self.ocr_worker_count):
                t = threading.Thread(target=self._ocr_worker_loop, args=(i,), name=f"OCRWorker-{i}", daemon=True)
                t.start()
                self._threads.append(t)
        except Exception as e:
            self.sig_error.emit(f"Failed to start pipeline threads: {e}")

    def _update_tracker(self, detections, frame=None):
        """Return numpy array [[x1,y1,x2,y2,track_id], ...]."""
        try:
            if detections is None:
                det_arr = np.empty((0, 5), dtype=float)
            else:
                if isinstance(detections, (int, float, np.integer, np.floating)):
                    det_arr = np.empty((0, 5), dtype=float)
                else:
                    det_arr = np.asarray(detections)
                    if det_arr.size == 0:
                        det_arr = np.empty((0, 5), dtype=float)
                    elif det_arr.ndim == 1:
                        if det_arr.size >= 4:
                            if det_arr.size == 4:
                                det_arr = np.hstack([det_arr.astype(float), [1.0]])
                            det_arr = det_arr.reshape(1, -1)
                        else:
                            det_arr = np.empty((0, 5), dtype=float)
                    elif det_arr.ndim == 2:
                        if det_arr.shape[1] == 4:
                            conf_col = np.ones((det_arr.shape[0], 1), dtype=float)
                            det_arr = np.hstack([det_arr.astype(float), conf_col])
                        elif det_arr.shape[1] >= 5:
                            det_arr = det_arr[:, :5].astype(float)
                        else:
                            det_arr = np.empty((0, 5), dtype=float)
                    else:
                        det_arr = np.empty((0, 5), dtype=float)

            if self.tracker is None:
                return np.empty((0, 5))

            if self.tracker_type == 'DEEPSORT':
                det_list = []
                for d in det_arr:
                    x1, y1, x2, y2, conf = float(d[0]), float(d[1]), float(d[2]), float(d[3]), float(d[4])
                    w = max(0.0, x2 - x1)
                    h = max(0.0, y2 - y1)
                    det_list.append(([x1, y1, w, h], conf, 0))
                tracks = self.tracker.update_tracks(det_list, frame=frame)
                out = []
                for t in tracks:
                    try:
                        if hasattr(t, 'is_confirmed') and not t.is_confirmed():
                            continue
                        bb = t.to_tlbr() if hasattr(t, 'to_tlbr') else None
                        tid = t.track_id if hasattr(t, 'track_id') else None
                        if bb is not None and tid is not None:
                            out.append([bb[0], bb[1], bb[2], bb[3], int(tid)])
                    except Exception:
                        continue
                return np.array(out) if len(out) > 0 else np.empty((0, 5))
            elif self.tracker_type == 'BYTETRACK':
                # Prepare Nx5 [x1,y1,x2,y2,score]
                if det_arr.shape[1] < 5:
                    conf_col = np.ones((det_arr.shape[0], 1), dtype=float)
                    det5 = np.hstack([det_arr[:, :4].astype(float), conf_col])
                else:
                    det5 = det_arr[:, :5].astype(float)

                # Determine image size if available
                try:
                    img_h, img_w = (frame.shape[0], frame.shape[1]) if frame is not None else (0, 0)
                except Exception:
                    img_h, img_w = (0, 0)

                # Call update with flexible signatures across versions
                tracks = []
                try:
                    tracks = self.tracker.update(det5, (img_h, img_w), (img_h, img_w))
                except TypeError:
                    try:
                        tracks = self.tracker.update(det5, (img_h, img_w))
                    except Exception as e:
                        self.sig_error.emit(f"ByteTrack update failed: {e}")
                        return np.empty((0, 5))

                out = []
                for t in tracks:
                    try:
                        # Common YOLOX STrack interface
                        if hasattr(t, 'tlbr'):
                            bb = t.tlbr() if callable(t.tlbr) else t.tlbr
                        elif hasattr(t, 'to_tlbr'):
                            bb = t.to_tlbr()
                        else:
                            bb = None
                        tid = int(t.track_id) if hasattr(t, 'track_id') else None
                        if bb is not None and tid is not None:
                            out.append([bb[0], bb[1], bb[2], bb[3], tid])
                    except Exception:
                        continue
                return np.array(out) if len(out) > 0 else np.empty((0, 5))
            else:
                return self.tracker.update(det_arr)
        except Exception as e:
            try:
                desc = f"type(detections)={type(detections)}"
            except Exception:
                desc = "diagnostic_unavailable"
            self.sig_error.emit(f"Tracker update error: {e} | {desc}")
            return np.empty((0, 5))

    @pyqtSlot(str)
    def set_tracker_type(self, tracker_type: str):
        """Dynamically switch tracker type at runtime from UI."""
        try:
            if not isinstance(tracker_type, str):
                return
            tracker_type = tracker_type.upper()
            if tracker_type not in ('SORT', 'DEEPSORT', 'BYTETRACK'):
                return
            if tracker_type == self.tracker_type:
                return
            self.tracker_type = tracker_type
            self._init_tracker()
        except Exception as e:
            self.sig_error.emit(f"set_tracker_type error: {e}")
    
    @pyqtSlot(str)
    def reload_vehicle_model(self, model_path: str):
        """Reload vehicle detection model at runtime."""
        try:
            self.sig_reloadProgress.emit(f"Worker: Reloading vehicle model to {model_path}")

            def progress_cb(message: str):
                try:
                    self.sig_reloadProgress.emit(str(message))
                except Exception:
                    pass

            self.vehicle_detector.reload_model(model_path, self.device, progress_cb)
            self.sig_reloadProgress.emit("Worker: Successfully reloaded vehicle model")
            self.sig_reloadFinished.emit(True, "Model reloaded")
        except Exception as e:
            error_msg = f"Worker: Failed to reload vehicle model: {e}"
            try:
                self.sig_reloadProgress.emit(error_msg)
            except Exception:
                pass
            self.sig_error.emit(error_msg)
            try:
                self.sig_reloadFinished.emit(False, error_msg)
            except Exception:
                pass

    @pyqtSlot(object, int, bool, str, bool)
    def process_frame(self, frame: np.ndarray, frame_counter: int, hide_bboxes: bool, license_format: str, preview: bool):
        """Enqueue a frame into the staged pipeline.

        The GPU stage will emit a quick tracks update. OCR results will arrive asynchronously.
        For preview=True (single image), OCR is performed synchronously and a single combined
        result is emitted to preserve prior behavior.
        """
        try:
            if frame is None or (hasattr(frame, 'size') and frame.size == 0):
                return
            # Best-effort enqueue without blocking UI
            item = {
                'frame': frame,
                'frame_counter': int(frame_counter),
                'hide_bboxes': bool(hide_bboxes),
                'license_format': str(license_format),
                'preview': bool(preview),
            }
            try:
                self.q_frames.put_nowait(item)
            except Full:
                # Drop if queue is full to keep realtime performance
                # Silently drop frames to reduce console spam
                pass
        except Exception as e:
            try:
                tb = traceback.format_exc()
            except Exception:
                tb = ''
            self.sig_error.emit(f"Worker enqueue error: {e}\n{tb}")

    def _gpu_worker_loop(self):
        """GPU stage: vehicle detection + tracking + plate detection.

        Emits tracks early for responsiveness. Dispatches OCR tasks to OCR queue.
        For preview images, performs OCR synchronously and emits a combined result.
        """
        while not self._stop_event.is_set():
            try:
                try:
                    item = self.q_frames.get(timeout=0.1)
                except Empty:
                    continue
                if item is None:
                    break

                frame = item['frame']
                frame_counter = item['frame_counter']
                hide_bboxes = item['hide_bboxes']
                license_format = item['license_format']
                preview = item['preview']

                original_img = frame
                show_img = original_img.copy() if preview else None

                # For debug image naming sequence
                try:
                    if hasattr(self.plate_reader, 'set_frame_counter'):
                        self.plate_reader.set_frame_counter(frame_counter)
                except Exception:
                    pass

                # 1) Vehicle detection
                vehicle_detections = self.vehicle_detector.detect_vehicles(original_img)

                # 2) Tracking
                tracked_vehicles = self._update_tracker(vehicle_detections, frame=original_img)

                # Fast path: emit tracks now for UI mapping/caching during video
                if not preview:
                    try:
                        tracks_payload = tracked_vehicles.tolist() if hasattr(tracked_vehicles, 'tolist') else []
                        self.sig_frameProcessed.emit({
                            'frame': None,
                            'tracks': tracks_payload,
                            'plates': [],
                            'preview': False,
                            'frame_counter': int(frame_counter),
                        })
                    except Exception:
                        pass

                # 3) Plate detection per tracked vehicle
                if tracked_vehicles is None or len(tracked_vehicles) == 0:
                    # Nothing more to do
                    if preview:
                        self.sig_frameProcessed.emit({
                            'frame': show_img,
                            'tracks': tracked_vehicles.tolist() if hasattr(tracked_vehicles, 'tolist') else [],
                            'plates': [],
                            'preview': True,
                            'frame_counter': int(frame_counter),
                        })
                    continue

                if preview:
                    # Synchronous OCR path for single-image preview
                    plates_payload = []
                    for vehicle in tracked_vehicles:
                        try:
                            x1, y1, x2, y2, sort_id = vehicle
                            sort_id = int(sort_id)
                            roi = original_img[int(y1):int(y2), int(x1):int(x2)]
                            if roi is None or roi.size == 0:
                                continue
                            plate_detections = self.plate_detector.detect_plates_in_roi(roi)
                            for plate_det in plate_detections:
                                px1, py1, px2, py2, _ = plate_det
                                abs_px1 = int(x1 + px1)
                                abs_py1 = int(y1 + py1)
                                abs_px2 = int(x1 + px2)
                                abs_py2 = int(y1 + py2)
                                
                                # Expand ROI to avoid cutting off characters (15% expansion)
                                img_h, img_w = original_img.shape[:2]
                                abs_px1, abs_py1, abs_px2, abs_py2 = expand_plate_roi(
                                    abs_px1, abs_py1, abs_px2, abs_py2, img_w, img_h, expand_ratio=0.15
                                )
                                
                                plate_img = original_img[abs_py1:abs_py2, abs_px1:abs_px2]
                                if plate_img is None or plate_img.size == 0:
                                    continue
                                if not hide_bboxes and show_img is not None:
                                    cv2.rectangle(show_img, (abs_px1, abs_py1), (abs_px2, abs_py2), (0, 0, 255), 2)
                                # OCR inline for preview
                                plate_text, ocr_conf = self.plate_reader.extract_plate_text(plate_img, license_format)
                                plates_payload.append({
                                    'sort_id': sort_id,
                                    'abs_bbox': [abs_px1, abs_py1, abs_px2, abs_py2],
                                    'plate_img': plate_img,
                                    'text': plate_text,
                                    'confidence': float(ocr_conf) if ocr_conf is not None else None
                                })
                        except Exception:
                            continue
                    # Emit combined preview result
                    self.sig_frameProcessed.emit({
                        'frame': show_img,
                        'tracks': tracked_vehicles.tolist() if hasattr(tracked_vehicles, 'tolist') else [],
                        'plates': plates_payload,
                        'preview': True,
                        'frame_counter': int(frame_counter),
                    })
                    continue

                # Video path: dispatch OCR tasks asynchronously
                for vehicle in tracked_vehicles:
                    try:
                        x1, y1, x2, y2, sort_id = vehicle
                        sort_id = int(sort_id)
                        roi = original_img[int(y1):int(y2), int(x1):int(x2)]
                        if roi is None or roi.size == 0:
                            continue
                        plate_detections = self.plate_detector.detect_plates_in_roi(roi)
                        for plate_det in plate_detections:
                            px1, py1, px2, py2, _ = plate_det
                            abs_px1 = int(x1 + px1)
                            abs_py1 = int(y1 + py1)
                            abs_px2 = int(x1 + px2)
                            abs_py2 = int(y1 + py2)
                            
                            # Expand ROI to avoid cutting off characters (15% expansion)
                            img_h, img_w = original_img.shape[:2]
                            abs_px1, abs_py1, abs_px2, abs_py2 = expand_plate_roi(
                                abs_px1, abs_py1, abs_px2, abs_py2, img_w, img_h, expand_ratio=0.15
                            )
                            
                            plate_img = original_img[abs_py1:abs_py2, abs_px1:abs_px2]
                            if plate_img is None or plate_img.size == 0:
                                continue
                            task = {
                                'sort_id': sort_id,
                                'abs_bbox': [abs_px1, abs_py1, abs_px2, abs_py2],
                                'plate_img': plate_img,
                                'license_format': license_format,
                                'frame_counter': int(frame_counter),
                                'full_frame': original_img,  # Add full frame for image saving
                            }
                            try:
                                self.q_ocr.put_nowait(task)
                            except Full:
                                if getattr(settings, 'SHOW_DEBUG_INFO', False):
                                    self.sig_error.emit("DEBUG WORKER: q_ocr full -> dropping plate task")
                    except Exception:
                        continue
            except Exception as e:
                try:
                    tb = traceback.format_exc()
                except Exception:
                    tb = ''
                self.sig_error.emit(f"GPU worker error: {e}\n{tb}")

    def _ocr_worker_loop(self, worker_id: int):
        """OCR worker: recognizes text from plate crops and emits results."""
        while not self._stop_event.is_set():
            try:
                try:
                    task = self.q_ocr.get(timeout=0.1)
                except Empty:
                    continue
                if task is None:
                    break
                sort_id = int(task['sort_id'])
                abs_bbox = task['abs_bbox']
                plate_img = task['plate_img']
                license_format = task['license_format']
                frame_counter = int(task['frame_counter'])

                text, conf = self.plate_reader.extract_plate_text(plate_img, license_format)
                
                # Phase 3: Calculate quality score for temporal tracking
                quality_score = None
                if text and conf is not None:
                    quality_score = calculate_plate_quality_score(plate_img, conf)
                
                # Save plate image if text was detected
                image_data = {}
                if text and len(text.strip()) > 0:
                    try:
                        # Generate a temporary raw_id for image naming (will be replaced with actual DB ID)
                        temp_raw_id = f"{sort_id}_{frame_counter}_{int(time.time())}"
                        image_result = self.image_processor.save_plate_images(
                            frame=task.get('full_frame'),  # Need full frame for context
                            bbox=abs_bbox,
                            plate_text=text,
                            timestamp=datetime.now(),
                            raw_id=temp_raw_id
                        )
                        if image_result['success']:
                            image_data = {
                                'plate_image_path': image_result['plate_image_path'],
                                'thumbnail_path': image_result['thumbnail_path'],
                                'image_width': image_result['image_width'],
                                'image_height': image_result['image_height'],
                                'image_size': image_result['image_size']
                            }
                    except Exception as e:
                        if getattr(settings, 'SHOW_DEBUG_INFO', False):
                            self.sig_error.emit(f"Image save error: {e}")
                
                payload = {
                    'frame': None,
                    'tracks': [],
                    'plates': [{
                        'sort_id': sort_id,
                        'abs_bbox': abs_bbox,
                        'plate_img': plate_img,
                        'text': text,
                        'confidence': float(conf) if conf is not None else None,
                        'quality_score': float(quality_score) if quality_score is not None else None,
                        'image_data': image_data,
                    }],
                    'preview': False,
                    'frame_counter': frame_counter,
                }
                self.sig_frameProcessed.emit(payload)
            except Exception as e:
                try:
                    tb = traceback.format_exc()
                except Exception:
                    tb = ''
                self.sig_error.emit(f"OCR worker error: {e}\n{tb}")

    @pyqtSlot()
    def stop(self):
        """Stop pipeline threads and restore settings where applicable."""
        try:
            self._stop_event.set()
            # Send sentinels
            try:
                self.q_frames.put_nowait(None)
            except Exception:
                pass
            try:
                for _ in range(max(1, self.ocr_worker_count)):
                    self.q_ocr.put_nowait(None)
            except Exception:
                pass
            # Join threads
            for t in self._threads:
                try:
                    t.join(timeout=1.0)
                except Exception:
                    pass
        finally:
            # Restore OCR GPU flag if it was changed
            try:
                if hasattr(self, '_orig_ocr_gpu'):
                    settings.OCR_GPU_ENABLED = self._orig_ocr_gpu
            except Exception:
                pass
