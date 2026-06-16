# Nepali ANPR — Automatic Number Plate Recognition System

A real-time Automatic Number Plate Recognition system purpose-built for Nepali license plates. It detects vehicles and plates from live camera feeds or video files, reads Nepali plate text, logs entry/exit events, manages a stolen vehicle registry, and provides analytics — all through a PyQt5 desktop UI with role-based access control.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Module Reference](#3-module-reference)
4. [Database Schema](#4-database-schema)
5. [Detection & OCR Pipeline](#5-detection--ocr-pipeline)
6. [RBAC & Authentication](#6-rbac--authentication)
7. [Stolen Vehicle Alert System](#7-stolen-vehicle-alert-system)
8. [Analytics & Reporting](#8-analytics--reporting)
9. [Configuration Reference](#9-configuration-reference)
10. [Installation & Setup](#10-installation--setup)
11. [Known Issues & Bugs](#11-known-issues--bugs)
12. [Security Warnings](#12-security-warnings)

---

## 1. System Overview

### Purpose

The system automates parking management for Nepali institutions: schools, hospitals, corporate premises, and toll gates. It replaces manual gate-keeping with a camera-based pipeline that:

- Detects vehicles using YOLOv8
- Locates and crops the license plate region
- Reads Nepali plate text via a two-stage YOLO+CNN pipeline or EasyOCR
- Logs ENTRY and EXIT events with timestamps and calculates parking fees
- Alerts security staff in real-time when a stolen or flagged vehicle is detected
- Provides daily/weekly/monthly analytics with occupancy forecasting
- Enforces role-based access so administrators, operators, and viewers each see only what they are permitted to see

### Supported Plate Formats

The system recognises two distinct script families: **Latin (English)** plates used on post-2000 vehicles and **Devanagari** plates used on older and government-registered vehicles. Both are handled in the same pipeline — the two-stage recogniser outputs Devanagari characters directly, while EasyOCR covers the Latin formats.

#### Latin (English) Plates

| Format | Pattern | Example | Length |
|--------|---------|---------|--------|
| Format 1 | `AA00AAA` | `BA1PA234` | 7 chars |
| Format 2 | `AA 1111` | `BA 1234` | 6 chars |
| Format 3 | `A AA 1111` | `P BA 1234` | 7 chars |
| Auto | Try all three | — | variable |

- Format 2 (`AA 1111`) is the **default** and covers the majority of current civilian plates.
- The two-letter prefix is the district registration code (e.g. `BA` = Bagmati, `KO` = Koshi).

#### Devanagari Plates

Older and government vehicles carry plates written entirely in Devanagari script. The two-stage YOLO+CNN pipeline is specifically trained for this script.

| Component | Script | Characters | Count |
|-----------|--------|-----------|-------|
| Region code | Devanagari | मे को स ज बा ना ग लु ध रा भे क से म | 1 compound char (optional) |
| Middle digits | Devanagari numerals | ०-९ | 1–3 digits |
| Vehicle type letter | Devanagari consonant | क च प ख ज फ ग झ ब य घ ञ | 1 letter |
| Serial digits | Devanagari numerals | ०-९ | 3–4 digits |

**Full pattern:** `[Region] [1–3 digits] [Vehicle letter] [3–4 digits]`

| Example | Breakdown | Meaning |
|---------|-----------|---------|
| `मे०४च०५४` | मे + ०४ + च + ०५४ | Mechi zone, series 4, cha-type, serial 054 |
| `बा१क१२३४` | बा + १ + क + १२३४ | Bagmati zone, series 1, ka-type, serial 1234 |
| `को३ग२०५` | को + ३ + ग + २०५ | Koshi zone, series 3, ga-type, serial 205 |

The region code is **optional** in extraction — the parser first anchors on the mandatory `[digits][vehicle letter][digits]` core, then includes the preceding region code if it matches a known value.

Minimum valid Devanagari plate length is **5 characters** (1 middle digit + 1 vehicle letter + 3 serial digits). Maximum is **8 characters** (1 region code + 3 middle digits + 1 vehicle letter + 4 serial digits).

### Technology Stack

| Layer | Technology |
|-------|-----------|
| UI | PyQt5 (Qt 5) |
| Detection | YOLOv8 (Ultralytics) — `yolov8m.pt` for vehicles, `models/best.pt` for plates |
| OCR | EasyOCR (EN + NE) **or** Two-Stage Pipeline (YOLOv8 + PyTorch CNN) |
| Tracking | ByteTrack (default), SORT, DeepSORT |
| Database | SQLite via SQLAlchemy ORM (WAL mode) |
| Auth | bcrypt password hashing, session tokens via `secrets.token_urlsafe` |
| Email | Gmail SMTP + TLS via `smtplib` |
| Analytics | pandas, matplotlib, scipy (linear regression for forecasting) |
| Export | openpyxl (Excel), ReportLab (PDF) |

---

## 2. Architecture

```
+---------------------------------------------------------------------+
|                          main.py  (ANPRApplication)                  |
|   +---------------+  frameRequested  +-------------------------+   |
|   |  UI Thread     | ---------------> |  FrameWorker (QThread)  |   |
|   |  (PyQt5)       | <--------------- |  GPU Stage + OCR Stage  |   |
|   |                |  sig_frame-      +-------------------------+   |
|   |  PlateDetector |  Processed                                      |
|   |  Dashboard     |                                                 |
|   +-------+-------+                                                 |
|           |                                                          |
|    +------v--------------------------------------------+           |
|    |                  src/ui/  (PyQt5 Pages)            |           |
|    |  Dashboard | Database | Analytics | Search | SV    |           |
|    |  Settings  | User Mgmt| Login     | RBAC   | Invite|           |
|    +------+--------------------------------------------+           |
|           |                                                          |
|    +------v--------+  +--------------+  +--------------------+     |
|    |  src/db/      |  |  src/auth/   |  |  src/analytics/    |     |
|    |  Database     |  |  AuthManager |  |  AnalyticsEngine   |     |
|    |  ToggleMgr    |  |  (bcrypt)    |  |  ExportUtils       |     |
|    |  SpecialVeh   |  +--------------+  +--------------------+     |
|    +---------------+                                                 |
|                                                                      |
|    +--------------+  +--------------+  +--------------------+       |
|    | src/detection|  |  src/ocr/    |  |  src/alerts/       |       |
|    | PlateDetector|  |  PlateReader |  |  EmailSender       |       |
|    | VehicleDetect|  |  CharRecog.  |  |  InvitationEmail   |       |
|    +--------------+  +--------------+  +--------------------+       |
+---------------------------------------------------------------------+
```

### Data Flow (per frame)

```
Camera/Video
    |
    v
FrameWorker.process_frame()
    |
    +-> VehicleDetector (YOLOv8m)  --> ByteTrack tracker
    |         Vehicle bounding boxes + track IDs
    |
    +-> PlateDetector (YOLOv8-best.pt)  --> crop plate region
    |
    +-> ImageProcessor  --> CLAHE, denoise, resize (3.5x)
    |
    +-> PlateReader  --> Two-Stage (YOLO+CNN) or EasyOCR
    |         Raw text + confidence
    |
    +-> sig_frameProcessed --> UI Thread
              |
              +-> add_plate_candidate()  (consensus voting)
              +-> get_final_plate_for_vehicle()
              +-> log_detection_to_database()  --> ToggleManager
              |         +-> add_raw_log()
              |         +-> add_vehicle_log() (ENTRY/EXIT)
              +-> check_stolen_alerts()  --> EmailSender
```

---

## 3. Module Reference

### `main.py` — `ANPRApplication`

Entry point. Extends `PlateDetectorDashboard` (UI base class).

| Method | Responsibility |
|--------|---------------|
| `__init__` | Initialises DB, ToggleManager, FrameWorker thread, stolen-alert timer |
| `init_database` | Creates tables, sets up camera record, re-initialises ToggleManager |
| `process_frame(frame_or_path)` | Enqueues frame for worker via `frameRequested` signal |
| `on_worker_frame_processed(result)` | Receives OCR results on UI thread, updates table/dashboard |
| `add_plate_candidate(vehicle_id, text, conf, quality)` | Consensus tracker — stores up to 8 candidates per vehicle as 4-tuples `(text, conf, count, quality)` |
| `get_final_plate_for_vehicle(vehicle_id)` | Returns finalised plate when `count >= MIN_DETECTIONS_FOR_FINAL` and combined score >= threshold |
| `remove_plate_from_vehicle(vehicle_id, plate)` | Removes plate from candidate list (currently broken — see Known Issues) |
| `log_detection_to_database(plate, conf, src, bbox, img)` | Calls `add_raw_log` then `ToggleManager.log_vehicle_detection` |
| `check_stolen_alerts` | Called every 1 s by QTimer; pops pending alert from ToggleManager and emits signal |
| `show_stolen_vehicle_alert(data)` | Shows modal QMessageBox with stolen vehicle details |
| `closeEvent` | Stops worker thread, closes DB connections |

---

### `src/detection/`

#### `plate_detector.py` — `PlateDetector`

Wraps the custom YOLOv8 plate detection model (`models/best.pt`). Accepts a BGR frame, returns a list of plate bounding boxes with confidence scores.

#### `vehicle_detector.py` — `VehicleDetector`

Wraps `yolov8m.pt` for vehicle class detection (classes 1-3, 5, 7: bicycle, car, motorcycle, bus, truck). Per-class confidence thresholds are applied from `VEHICLE_CLASSES` in `config/settings.py`.

---

### `src/ocr/`

#### `plate_reader.py` — `PlateReader`

Orchestrates OCR. Selects pipeline based on `RECOGNITION_METHOD` setting:

- **`two_stage`**: Runs YOLOv8 character segmentation (`modelcheck/best.pt`) then classifies each character with a CNN (`modelcheck/model.pth`). Groups characters by row using pixel proximity (`TWO_STAGE_ROW_TOLERANCE = 30`).
- **`easyocr`**: Runs EasyOCR with EN+NE language models, then applies format-specific post-processing.

Post-processing (both pipelines):
1. Uppercase and strip whitespace
2. Apply `char_substitutions` map (see Known Issues — this step is currently destructive)
3. Validate against the selected `license_format`
4. Return `(text, confidence)` or `(None, None)` if validation fails

#### `character_recognizer.py` — `CharacterRecognizer`

Loads the PyTorch CNN from `modelcheck/model.pth` and `modelcheck/labels.json`. Performs per-character classification for the two-stage pipeline.

---

### `src/threading/`

#### `frame_worker.py` — `FrameWorker`

Runs in a `QThread`. Internally maintains two sub-queues:

| Queue | Workers | Purpose |
|-------|---------|---------|
| `q_gpu` | 1 GPU thread | Vehicle detection, plate detection, image preprocessing |
| `q_ocr` | 1 OCR thread | Plate text recognition (EasyOCR / two-stage) |

Each GPU result is packaged into an OCR task containing the plate crop and the full frame reference. Results are emitted back to the UI thread via `sig_frameProcessed`.

---

### `src/db/`

#### `database.py` — `Database`

SQLAlchemy wrapper around SQLite (WAL mode). Key methods:

| Method | Returns |
|--------|---------|
| `get_session()` | Context manager — commits on success, rolls back on exception |
| `add_raw_log(...)` | `raw_id` (int) |
| `add_vehicle_log(...)` | `log_id` (int) |
| `get_or_create_vehicle(plate)` | `vehicle_id` (int) |
| `get_or_create_camera(name)` | `camera_id` (int) |
| `get_last_vehicle_log_data(plate)` | dict or None |
| `close()` | Disposes engine, removes scoped session |

A module-level singleton is provided via `get_database()`.

#### `toggle_manager.py` — `ToggleManager`

Implements ENTRY/EXIT state machine per plate number.

- On first detection of a plate -> logs `ENTRY`
- On subsequent detections within `cooldown_minutes` -> ignored (deduplication)
- When a plate is re-detected after cooldown -> logs `EXIT`, calculates `duration_minutes`, `duration_hours`, and parking `amount` (NPR)
- Plate similarity matching via `SequenceMatcher` catches minor OCR variation between ENTRY and EXIT reads
- Stolen vehicle check runs on every detection; sets a pending alert retrieved by the UI timer

#### `special_vehicles_db.py` — `SpecialVehiclesDB`

Manages two registries:

- **Stolen vehicles**: `plate_number`, `owner_name`, `vehicle_type`, `color`, `contact_number`, `email_recipients`, `alert_on_detection`, `reported_date`, `case_number`
- **Staff/VIP vehicles**: `plate_number`, `employee_id`, `owner_name`, `department`, `vehicle_type`, `access_level`, `expiry_date`

Includes alert cooldown logic (`check_alert_cooldown`) to prevent email flooding — minimum 5-minute gap between alerts for the same plate.

#### `rbac_models.py` — SQLAlchemy ORM models for RBAC

| Table | Purpose |
|-------|---------|
| `users` | User accounts with bcrypt password hash, status enum |
| `roles` | Named roles (ADMIN, OPERATOR, VIEWER, etc.) |
| `permissions` | Granular permissions (e.g., `MANAGE_USERS`, `VIEW_LOGS`) |
| `role_permissions` | Many-to-many: role -> permissions |
| `user_roles` | Many-to-many: user -> roles, with optional `expires_at` |
| `user_sessions` | Login session tracking with IP and user-agent |
| `audit_logs` | Immutable audit trail for all auth events |

#### `models.py` — Core ANPR ORM models

| Table | Purpose |
|-------|---------|
| `cameras` | Camera registry |
| `vehicles` | Vehicle registry keyed by `plate_number` |
| `raw_logs` | Every OCR detection (noisy, unfiltered) |
| `vehicle_log` | Filtered ENTRY/EXIT records with duration and amount |
| `plate_edit_history` | Audit trail for manual plate corrections |

---

### `src/auth/`

#### `auth_manager.py` — `AuthManager`

Full RBAC authentication layer:

| Method | Description |
|--------|-------------|
| `login(username, password)` | bcrypt verify, account status check, session creation, audit log |
| `logout(session_id)` | Marks session inactive, clears `current_user` |
| `validate_session(session_id)` | Checks session is active and not expired |
| `check_permission(permission_name)` | Queries `user_roles -> role_permissions` chain |
| `require_permission(permission_name)` | Raises `AuthorizationError` if not permitted |
| `create_user(username, password, email, role)` | Creates user + assigns role, requires `MANAGE_USERS` permission |
| `update_password(username, new_password)` | Resets password — no authentication required (see Security Warnings) |
| `suspend_user / activate_user` | Status management |

Accounts are automatically suspended after 5 consecutive failed login attempts.

#### `simple_auth.py` — `SimpleAuthManager`

A legacy, parallel authentication module that uses unsalted SHA-256. It is present as a fallback but should not be used in production (see Security Warnings).

---

### `src/analytics/`

#### `analytics_engine.py` — `AnalyticsEngine`

Queries `vehicle_log` and computes:

- Peak hours / peak days of the week
- Current occupancy (vehicles entered minus vehicles exited)
- Entry/exit rates
- Revenue summary (total, average per vehicle, by time period)
- Demand forecast using a simple moving-average extrapolation

#### `export_utils.py` — `ExportUtils`

Exports analytics reports to:
- **Excel** (`.xlsx`) via `openpyxl` — separate sheets for summary, trends, revenue, vehicles
- **PDF** via ReportLab — formatted tables and charts

---

### `src/alerts/`

#### `email_sender.py` — `StolenVehicleEmailSender`

Sends HTML email alerts when a stolen vehicle is detected. Includes:
- Inline plate image (Base64 CID attachment)
- Vehicle details (plate, owner, type, color, reported date)
- SMTP via Gmail with STARTTLS on port 587

#### `invitation_email.py` — `InvitationEmailSender`

Sends account invitation emails with a one-time OTP for new user registration. OTP is 6 digits, generated with `secrets.randbelow(1000000)`.

---

### `src/ui/`

| File | Page/Dialog | Description |
|------|-------------|-------------|
| `main_window.py` | `PlateDetectorDashboard` | Base window: sidebar nav, stacked pages, camera/video controls |
| `dashboard_page.py` | Dashboard | Live stats cards: total entries, exits, revenue, active vehicles |
| `database_page.py` | Database | Paginated table of `vehicle_log` records with filters; export; plate edit |
| `search_plate_page.py` | Search Plate | Search by plate number or date range across `vehicle_log` |
| `analytics_page.py` | Analytics | Tabbed: trends chart, revenue chart, forecast chart, summary cards |
| `special_vehicles_page.py` | Special Vehicles | CRUD for stolen vehicles and staff vehicles; alert configuration |
| `user_management_page.py` | User Management | Admin CRUD for users, role assignment, status toggle |
| `settings_page.py` | Settings | Model selection, detection thresholds, OCR method, email config |
| `login_dialog.py` | Login | Username/password with background login thread |
| `registration_dialog.py` | Registration | OTP-gated new user registration |
| `invite_user_dialog.py` | Invite User | Admin sends invitation email to new user |
| `plate_edit_dialog.py` | Plate Edit | Correct OCR errors in `vehicle_log` records; stores audit trail |
| `password_reset_dialog.py` | Password Reset | Self-service password change |

---

## 4. Database Schema

### Entity Relationship (simplified)

```
cameras --< raw_logs --< vehicle_log >-- vehicles
                              |
                              +-- is_edited, edited_by --> users
                              +-- plate_edit_history

users >--< user_roles >--< roles >--< role_permissions >--< permissions

users --< user_sessions
users --< audit_logs

stolen_vehicles   (independent table)
staff_vehicles    (independent table)
stolen_vehicle_alerts  (cooldown log)
invitations
```

### Key Columns

#### `vehicle_log`

| Column | Type | Notes |
|--------|------|-------|
| `log_id` | INTEGER PK | Auto-increment |
| `plate_number` | VARCHAR(20) | Cleaned OCR text |
| `toggle_mode` | ENUM | `ENTRY` or `EXIT` |
| `captured_at` | DATETIME | UTC timestamp |
| `duration_minutes` | INTEGER | Null on ENTRY, set on EXIT |
| `duration_hours` | FLOAT | Derived from `duration_minutes` |
| `amount` | FLOAT | `duration_hours x PARKING_HOURLY_RATE` (NPR 50/hr) |
| `plate_image_path` | VARCHAR(500) | Path to full cropped plate image |
| `thumbnail_path` | VARCHAR(500) | Path to thumbnail |
| `is_edited` | BOOLEAN | True if manually corrected |
| `original_plate_number` | VARCHAR(20) | Pre-correction OCR text |

#### `raw_logs`

| Column | Type | Notes |
|--------|------|-------|
| `raw_id` | INTEGER PK | |
| `plate_text` | VARCHAR(20) | Raw OCR output (may be noisy) |
| `confidence` | FLOAT | OCR confidence 0.0-1.0 |
| `bbox_x/y/width/height` | FLOAT | Plate bounding box |
| `plate_image_path` | VARCHAR(500) | |

#### `stolen_vehicles`

| Column | Type | Notes |
|--------|------|-------|
| `plate_number` | VARCHAR(20) UNIQUE | |
| `owner_name` | VARCHAR(200) | |
| `email_recipients` | TEXT | Comma-separated email addresses |
| `alert_on_detection` | BOOLEAN | If True, email sent on detection |
| `alert_cooldown_minutes` | INTEGER | Default 60 |
| `case_number` | VARCHAR(100) | Police case reference |

---

## 5. Detection & OCR Pipeline

### Stage 1 — Vehicle Detection

YOLOv8m runs at 416x416 input resolution (`MODEL_IMAGE_SIZE`). Detected classes:

| YOLO Class | Vehicle | Confidence Threshold |
|-----------|---------|---------------------|
| 1 | Bicycle | 0.30 |
| 2 | Car | 0.40 |
| 3 | Motorcycle | 0.25 |
| 5 | Bus | 0.40 |
| 7 | Truck | 0.40 |

Tracking is performed by ByteTrack with:
- `track_thresh = 0.25`
- `match_thresh = 0.8`
- `track_buffer = 30` frames

Each track receives a stable `continuous_id` mapped from ByteTrack's internal ID through `vehicle_id_map`.

### Stage 2 — Plate Detection

A custom YOLOv8 model (`models/best.pt`) trained on Nepali plates locates the plate region within each vehicle crop. Minimum plate dimensions: 120x40 pixels (`MIN_PLATE_WIDTH`, `MIN_PLATE_HEIGHT`).

### Stage 3 — Image Preprocessing

Applied before OCR:
1. Convert to grayscale
2. CLAHE (clip limit 3.0, tile 4x4) for local contrast enhancement
3. Gaussian denoise
4. Resize by 3.5x (`PLATE_RESIZE_SCALE`)
5. Perspective correction (if enabled for two-stage pipeline)

### Stage 4 — Text Recognition

**Two-Stage Pipeline (default):**
1. YOLOv8 (`modelcheck/best.pt`) detects individual character bounding boxes
2. Characters sorted left-to-right, grouped into rows by vertical proximity (30 px tolerance)
3. PyTorch CNN (`modelcheck/model.pth`) classifies each character crop
4. Characters concatenated per row with space separator
5. Minimum 3 characters, minimum average confidence 0.55

**EasyOCR Pipeline:**
1. EasyOCR with `['en', 'ne']` language models
2. Multiple strategy passes with varying width/height merge thresholds
3. Best result selected by confidence

### Stage 5 — Consensus Voting

Each detected plate text is stored as a candidate `(text, confidence, count, quality_score)` tuple per vehicle. Final plate is selected when either:
- `count >= MIN_DETECTIONS_FOR_FINAL (1)` AND `combined_score >= CONFIDENCE_THRESHOLD_FINAL (0.55)`
- OR best candidate confidence >= `IMMEDIATE_FINALIZATION_THRESHOLD (0.70)`

Combined score = `0.7 x confidence + 0.3 x quality_score`.

---

## 6. RBAC & Authentication

### Roles (default setup)

| Role | Typical Permissions |
|------|---------------------|
| ADMIN | All permissions |
| OPERATOR | View logs, edit plates, manage special vehicles |
| VIEWER | View logs only |

### Permission Identifiers

Key permission names checked in code:

| Permission | Guards |
|-----------|--------|
| `MANAGE_USERS` | User creation, role assignment, suspension |
| `VIEW_LOGS` | Database page, search page |
| `EDIT_PLATE` | Plate edit dialog |
| `MANAGE_SPECIAL_VEHICLES` | Stolen/staff vehicle CRUD |
| `VIEW_ANALYTICS` | Analytics page |
| `MANAGE_SETTINGS` | Settings page |

### Session Lifecycle

1. `AuthManager.login()` — verifies bcrypt hash, creates `UserSession` row, stores session token
2. Token stored in memory as `current_session`; `current_username` cached to avoid detached ORM issues
3. After 5 failed attempts, account is set to `SUSPENDED`; subsequent logins are denied before password check
4. `logout()` marks session `is_active = False`, clears `current_user`
5. All auth events written to `audit_logs`

### Invitation Flow

1. Admin opens Invite User dialog, enters email and role
2. System generates 6-digit OTP via `secrets.randbelow`
3. OTP stored in `invitations` table with 24-hour expiry
4. Invitation email sent via `InvitationEmailSender`
5. Recipient opens Registration dialog, enters OTP
6. System validates OTP, creates user account, deletes invitation record

---

## 7. Stolen Vehicle Alert System

### Detection Path

```
ToggleManager.log_vehicle_detection(plate_text)
    +-> SpecialVehiclesDB.check_if_stolen(plate_text)
            +-> if stolen:
                    check_alert_cooldown()  (5-min minimum gap)
                    log_stolen_vehicle_alert()
                    set pending_stolen_alert
                    
ANPRApplication.check_stolen_alerts()  [every 1 second via QTimer]
    +-> toggle_manager.get_and_clear_stolen_alert()
            +-> show_stolen_vehicle_alert()  (modal QMessageBox)
            +-> StolenVehicleEmailSender.send_alert()  (if email enabled)
```

### Email Alert Contents

- Subject: `STOLEN VEHICLE ALERT -- <plate_number>`
- Body: owner name, vehicle type, color, contact, case number, reported date
- Attachment: inline plate image (CID)
- Recipients: per-vehicle `email_recipients` list stored in `stolen_vehicles` table

### Staff Vehicle Recognition

Staff vehicles are flagged in the UI with a different highlight color but do not trigger an alert. `access_level` and `expiry_date` are stored for future gate automation integration.

---

## 8. Analytics & Reporting

### Analytics Page Tabs

| Tab | Content |
|-----|---------|
| Dashboard | Summary cards: total entries, exits, revenue, peak hour, occupancy |
| Trends | Hourly and daily bar charts |
| Revenue | Daily revenue line chart with running total |
| Forecast | Moving-average demand forecast for configurable days ahead |

### Forecast Algorithm

Uses a 7-day rolling average of historical daily entry counts. Each predicted day is appended to the history for subsequent-day predictions. The forecast is labelled with confidence bands derived from historical standard deviation.

### Export Formats

**Excel** (via openpyxl):
- Sheet 1: Summary statistics
- Sheet 2: Daily trend data
- Sheet 3: Revenue breakdown
- Sheet 4: Top vehicles by frequency

**PDF** (via ReportLab):
- Title page with date range
- Summary table
- Charts embedded as images

---

## 9. Configuration Reference

All settings live in [config/settings.py](config/settings.py).

### Detection Thresholds

| Setting | Default | Effect |
|---------|---------|--------|
| `VEHICLE_CONFIDENCE_THRESHOLD` | 0.20 | Minimum YOLO confidence to register a vehicle |
| `PLATE_CONFIDENCE_THRESHOLD` | 0.30 | Minimum YOLO confidence to register a plate |
| `OCR_CONFIDENCE_THRESHOLD` | 0.50 | Minimum OCR confidence to accept text |
| `CONFIDENCE_THRESHOLD_FINAL` | 0.55 | Minimum to finalise a plate from candidates |
| `IMMEDIATE_FINALIZATION_THRESHOLD` | 0.70 | High-confidence plates finalised on first detection |

### Tracking

| Setting | Default | Effect |
|---------|---------|--------|
| `TRACKER_TYPE` | `BYTETRACK` | Options: `SORT`, `DEEPSORT`, `BYTETRACK` |
| `TRACKER_MAX_AGE` | 30 | Frames before a track is dropped |
| `TRACKER_MIN_HITS` | 2 | Detections required before confirming a track |
| `TRACKER_IOU_THRESHOLD` | 0.3 | IoU threshold for track matching |

### OCR

| Setting | Default | Effect |
|---------|---------|--------|
| `RECOGNITION_METHOD` | `two_stage` | `two_stage` or `easyocr` |
| `TWO_STAGE_CONF_THRESHOLD` | 0.25 | YOLO character detection confidence |
| `TWO_STAGE_MIN_CONFIDENCE` | 0.55 | Minimum average CNN confidence |
| `TWO_STAGE_ROW_TOLERANCE` | 30 | Pixel tolerance for row grouping |
| `PLATE_RESIZE_SCALE` | 3.5 | Upscale factor before OCR |

### Parking Fees

| Setting | Default |
|---------|---------|
| `PARKING_HOURLY_RATE` | 50.0 NPR/hour |
| `MINIMUM_CHARGE_HOURS` | 1.0 hour |

### Debug

| Setting | Default | Note |
|---------|---------|------|
| `DEBUG_SAVE_IMAGES` | `True` | Saves plate images to `plate_images/daily/` |
| `DEBUG_OCR_VERBOSE` | `True` | Prints OCR results to console |

Set both to `False` in production to avoid filling disk and flooding the console.

### Email

| Setting | Default |
|---------|---------|
| `SMTP_SERVER` | `smtp.gmail.com` |
| `SMTP_PORT` | 587 |
| `EMAIL_SENDER` | Configured Gmail address |
| `EMAIL_APP_PASSWORD` | Gmail app password |

---

## 10. Installation & Setup

### Prerequisites

- Python 3.9+
- CUDA-capable GPU (optional but recommended for real-time processing)
- Windows 10/11 (tested); Linux compatible with minor path adjustments

### Steps

```bash
# 1. Clone the repository
git clone <repo-url>
cd "NEPALI ANPR"

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Initialise the database and default roles
python scripts/init_database.py

# 5. (Optional) Initialise RBAC with custom admin password
python src/scripts/init_rbac_system.py

# 6. Run the application
python main.py
```

### Required Model Files

Place these in the specified directories before running:

| File | Directory | Purpose |
|------|-----------|---------|
| `best.pt` | `models/` | YOLOv8 plate detection model |
| `yolov8m.pt` | project root | YOLOv8m vehicle detection |
| `best.pt` | `modelcheck/` | YOLOv8 character segmentation |
| `model.pth` | `modelcheck/` | PyTorch CNN character classifier |
| `labels.json` | `modelcheck/` | CNN class label mapping |

### Email Configuration

Before stolen vehicle alerts will work, move credentials out of source code and into environment variables:

```python
# config/settings.py
import os
EMAIL_SENDER = os.environ.get("ANPR_EMAIL_SENDER", "")
EMAIL_APP_PASSWORD = os.environ.get("ANPR_EMAIL_PASSWORD", "")
```

Then set them before running:

```bash
# Windows
set ANPR_EMAIL_SENDER=your@gmail.com
set ANPR_EMAIL_PASSWORD=your_app_password
python main.py
```

### Default Credentials

On first run, `init_rbac_system.py` creates an admin account with a default password. **Change the password immediately after first login.**

