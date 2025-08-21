import cv2
import numpy as np
import traceback
from datetime import datetime
from types import SimpleNamespace
import os
import sys

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from config import settings
from src.detection.vehicle_detector import VehicleDetector
from src.detection.plate_detector import PlateDetector
from src.ocr.plate_reader import PlateReader


class FrameWorker(QObject):
    """Background worker that processes frames off the UI thread.

    Emits a single aggregated result per processed frame so the UI can
    update state and widgets safely on the main thread without changing
    existing logic.
    """

    sig_frameProcessed = pyqtSignal(object)  # dict payload
    sig_error = pyqtSignal(str)

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
            self.vehicle_detector = VehicleDetector(self.device)
            self.plate_detector = PlateDetector(self.device)
            self.plate_reader = PlateReader()

            # Setup tracker per settings
            self.tracker_type = str(getattr(settings, 'TRACKER_TYPE', 'SORT')).upper()
            self._init_tracker()

            # For optional OCR debug saving
            self.debug_dir = None
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

    @pyqtSlot(object, int, bool, str, bool)
    def process_frame(self, frame: np.ndarray, frame_counter: int, hide_bboxes: bool, license_format: str, preview: bool):
        """Process a frame and emit aggregated results to the UI thread.

        Parameters map to current UI state to keep behavior unchanged.
        """
        try:
            if frame is None or (hasattr(frame, 'size') and frame.size == 0):
                return

            original_img = frame
            show_img = original_img.copy()

            # Plate reader debug naming
            try:
                if hasattr(self.plate_reader, 'set_frame_counter'):
                    self.plate_reader.set_frame_counter(frame_counter)
            except Exception:
                pass

            # 1) Vehicle detection
            vehicle_detections = self.vehicle_detector.detect_vehicles(original_img)

            # 2) Tracking
            tracked_vehicles = self._update_tracker(vehicle_detections, frame=original_img)

            # 3) Plate detection + OCR per tracked vehicle
            plates_payload = []
            for vehicle in tracked_vehicles:
                try:
                    x1, y1, x2, y2, sort_id = vehicle
                    sort_id = int(sort_id)
                    roi = original_img[int(y1):int(y2), int(x1):int(x2)]
                    if roi.size == 0:
                        continue

                    plate_detections = self.plate_detector.detect_plates_in_roi(roi)

                    for plate_det in plate_detections:
                        px1, py1, px2, py2, conf = plate_det
                        abs_px1 = int(x1 + px1)
                        abs_py1 = int(y1 + py1)
                        abs_px2 = int(x1 + px2)
                        abs_py2 = int(y1 + py2)

                        # Extract plate image
                        plate_img = original_img[abs_py1:abs_py2, abs_px1:abs_px2]
                        if plate_img is None or plate_img.size == 0:
                            continue

                        # Draw plate bbox (as before)
                        if not hide_bboxes:
                            cv2.rectangle(show_img, (abs_px1, abs_py1), (abs_px2, abs_py2), (0, 0, 255), 2)

                        # OCR
                        plate_text, ocr_confidence = self.plate_reader.extract_plate_text(plate_img, license_format)

                        # Collect for UI to finalize and update widgets
                        plates_payload.append({
                            'sort_id': sort_id,
                            'abs_bbox': [abs_px1, abs_py1, abs_px2, abs_py2],
                            'plate_img': plate_img,
                            'text': plate_text,
                            'confidence': float(ocr_confidence) if ocr_confidence is not None else None
                        })
                except Exception:
                    # Keep robust to per-vehicle errors
                    continue

            # Aggregate and emit result
            result = {
                'frame': show_img,
                'tracks': tracked_vehicles.tolist() if hasattr(tracked_vehicles, 'tolist') else [],
                'plates': plates_payload,
                'preview': bool(preview),
                'frame_counter': int(frame_counter),
            }
            self.sig_frameProcessed.emit(result)
        except Exception as e:
            try:
                tb = traceback.format_exc()
            except Exception:
                tb = ''
            self.sig_error.emit(f"Worker process_frame error: {e}\n{tb}")
