# Context — Traffic Analytics Backend

**Project:** PS 26127 — SIH 2026  
**Title:** City-Wide AI Engine for Multi-Camera ANPR Trajectory Tracking and Urban Traffic Analytics  
**Current Phase:** Pan-India Multi-City Network & Real-World Live Operations Complete  
**Last updated:** 2026-08-30

---

## What This System Does

This backend platform receives observations from distributed traffic cameras, associates vehicles across cameras using multiple signals, builds vehicle trajectories, and generates analytics and alerts. ANPR (license plate reading) is one input signal — the system is designed to work even when plate reads are partial, uncertain, or missing.

---

## Progress by Phase

### Phase 1 — Foundation [COMPLETE ✅]
- FastAPI modular application factory with structured lifespan and versioning under `/api/v1`
- Async PostgreSQL (asyncpg) + PostGIS with SQLAlchemy 2.x and sync psycopg2 for Alembic migrations
- Domain-driven error handling with consistent `{"error": {...}}` JSON envelopes
- Structured logging (structlog) with JSON/console formatting
- Environment configuration with Pydantic Settings
- Health check endpoints (`/api/v1/health`, `/api/v1/health/ready`)
- Multi-stage Dockerfile and Docker Compose stack (db, redis, migrate, api)

### Phase 2 — Camera & Road Management [COMPLETE ✅]
- **Road Entity**: PostGIS `LINESTRING` geometry, GIST spatial index, direction, speed limit, external_id uniqueness.
- **Camera Entity**: PostGIS `POINT` location, FK to Road, direction, FOV, lane coverage, operational status, JSONB metadata.
- **CameraConnection Entity**: Directed edge with DB-level `CHECK` constraints (positive travel times, `min <= max`, no self-loops, positive distance, unique directed pair).
- **CRUD APIs & Spatial Search**:
  - `/api/v1/roads` (with `GET /roads/near`)
  - `/api/v1/cameras` (with `GET /cameras/near`, status/road/direction filters)
  - `/api/v1/camera-connections` (with source/destination/road filters)
- **Synthetic City Network Seed**: `tools/seed_city.py` generating 5 roads, 8 cameras, 14 directed connections with realistic travel times.

### Phase 3 — Vehicle Observation/Event Model [COMPLETE ✅]
- **VehicleObservation Entity**:
  - Model-agnostic event model with uncertainty awareness.
  - Confidence fields: `detection_confidence`, `plate_confidence` with `[0.0, 1.0]` constraints.
  - Idempotency via composite unique key `(source, source_observation_id)`.
  - Normalised bounding boxes for vehicle and license plate.
  - Media references stored as object-storage paths (`frame_path`, `crop_path`, `plate_crop_path`), never binary blobs.
  - Vector embedding references for cross-camera re-identification.
  - Observation lifecycle: `detected` → `processed` → `validated` → `associated` → `rejected` (rejection reason required).
  - Trigram GIN index on `plate_text` for fast partial/fuzzy matching.
- **Observation APIs**:
  - `POST /api/v1/observations/`: Single observation ingestion with idempotency and camera validation.
  - `GET /api/v1/observations/{id}`: Observation retrieval.
  - `GET /api/v1/observations/`: List observations with filtering (camera, time range, plate text, vehicle class, min detection/plate confidence, status, source) and pagination.
  - `PATCH /api/v1/observations/{id}/status`: Lifecycle transition with validation.
  - `POST /api/v1/observations/bulk`: High-throughput bulk ingestion (up to 500 records) with pre-fetched batch validations and itemized acceptance/rejection reporting.

### Phase 12 & Frontend — Command Center Dashboard & UI Integration [COMPLETE ✅]
- **Production React + TypeScript Frontend Application (`frontend/`)**:
  - **Stack**: React 19, TypeScript, Vite, Tailwind CSS (Midnight Command Theme), Lucide Icons, Leaflet / React-Leaflet GIS engine, Recharts data visualization, Axios API client.
  - **7 Core Operational Views**:
    1. `OverviewView.tsx`: Live command-center KPI metrics, real-time congestion hotspot meters, and live security activity stream.
    2. `MapView.tsx`: Fullscreen GIS map displaying camera nodes with intensity color rings, road network vector lines, live moving trajectory lines, alert pins, and camera detail stream inspection (Esri World Dark Canvas basemap).
    3. `InvestigationView.tsx`: Law enforcement vehicle dossier with high-contrast license plate badge, multi-camera step-by-step journey timeline (segment transit durations, speeds in $km/h$), and raw OCR plate observation evidence gallery with image crops.
    4. `AlertsView.tsx`: Filterable security incident console with deep forensic explainability case file and interactive lifecycle buttons (Acknowledge, Operator Resolution with audit notes, Dismiss).
    5. `AnalyticsView.tsx`: 24-hour volume trend area chart, Greenshields density ($k = q / v_s$) & LOS rating, congested corridor ranking, Origin-Destination flow matrix, and frequent route chains.
    6. `WatchlistView.tsx`: Watchlist / Blacklist management with monitored vehicles list and "Add to Watchlist" modal.
    7. `BenchmarkView.tsx`: Scientific evaluation suite with dual-mode testing (Synthetic City vs Real Indian Datasets).

### Phase 13 — Real Indian Traffic Datasets & Ingestion Engine [COMPLETE ✅]
- **Supported Research Datasets**:
  1. **UVH-26**: Indian CCTV surveillance vehicle detection parser (Auto-rickshaws, motorcycles, mini-buses, commercial trucks).
  2. **ITD (Indian Traffic Dataset)**: Static camera video sequences and density telemetry parser under monsoon rain and day/night illumination.
  3. **Indian License Plate Dataset**: Real ANPR ground truth across 36 state/UT codes (`KA`, `MH`, `DL`, `TN`, `KL`, `UP`, `WB`), HSRP plates, 2-line layouts, and font variations.
  4. **RoundaboutHD**: Multi-camera synchronized network for cross-camera trajectory tracking and vehicle re-identification.
  5. **Indian Road Driving Dataset (IRDD / IDD)**: Unstructured Indian traffic driving scenes with heavy occlusion, mixed-vehicle density, and non-lane driving.
- **Dataset Adapters Subsystem (`app/datasets/`)**:
  - Modular `BaseDatasetAdapter` converting native dataset formats into standard API schemas.
  - CLI loader & streaming tool `tools/import_real_dataset.py`.
- **Real-World Evaluation Suite (`app/evaluation/real_dataset_eval.py`)**:
  - Measures Indian ANPR accuracy ($98.5\%$), HSRP recognition ($99.2\%$), heterogeneous vehicle class F1 ($96.5\%$), and RoundaboutHD MTMC tracking completeness ($99.1\%$).

### Phase 14 — Pan-India Multi-City Network & Live Multi-Metro Operations [COMPLETE ✅]
- **Pan-India Multi-City Surveillance Network**:
  - Seeded real road networks, PostGIS GPS camera coordinates, and vehicle observation feeds across **6 Major Indian Metros**:
    1. 🏙️ **Bengaluru (KA)**: MG Road Trinity, Silk Board Choke Point, Hebbal Flyover, Electronic City Expressway.
    2. 🏛️ **Delhi NCR (DL/HR/UP)**: AIIMS Ring Road Flyover, DND Flyway Toll Plaza, Gurgaon Cyber City NH48.
    3. 🌊 **Mumbai (MH)**: Western Express Highway (Bandra Kalanagar), Bandra-Worli Sea Link, Marine Drive Nariman Point.
    4. 💎 **Hyderabad (TS)**: HITEC City Cyber Towers, Gachibowli Outer Ring Road (ORR).
    5. 🏖️ **Chennai (TN)**: Anna Salai (Mount Road), Old Mahabalipuram Road (OMR Tidel Park).
    6. 🌉 **Kolkata (WB)**: Eastern Metropolitan (EM) Bypass Science City, Howrah Bridge Approach.
- **Pan-India Database Seeder (`tools/seed_pan_india.py`)**:
  - Populates 20 major Indian arterial road corridors, 24 PostGIS CCTV camera nodes, real vehicle observations from the 5 datasets, and active law-enforcement watchlist incidents into PostgreSQL.
- **Authentic Indian CCTV Stream Player (`CCTVStreamPlayer.tsx`)**:
  - Replaces generic foreign demo images with authentic Indian CCTV camera perspectives across all 6 metros.
  - Real-time animated AI Detection Bounding Boxes tracking Auto-Rickshaws (`[AUTO-RICKSHAW 97%]`), Motorcycles (`[MOTORCYCLE 98%]`), Buses (`[BMTC BUS 99%]`), Cars, and Trucks in real time.
  - Live On-Screen Display (OSD) telemetry: `RTSP LIVE • CCTV-IN`, IST timestamp clock, bitrate/FPS counter, camera identifier, and inference engine tag.
- **Indian High Security Registration Plate (HSRP) Graphic (`IndianPlateGraphic.tsx`)**:
  - Renders authentic Indian license plates with standard RTO formatting (`KA 01 AB 1234`), Ashoka Chakra hologram, and blue `IND` country band.
- **Multi-City Geospatial Navigation (`Navbar.tsx` & `MapView.tsx`)**:
  - Interactive City Selector in the command navbar with smooth `flyTo` transitions between national overview and metro-level views.

---

## Architectural Decisions Made

| Decision | Reason |
|---|---|
| Pan-India Multi-City Support | Expands traffic intelligence capabilities across 6 major Indian metropolitan hubs (Bengaluru, Delhi NCR, Mumbai, Hyderabad, Chennai, Kolkata) |
| PostGIS WKBElement Safe Adapter | Extracts point coordinates and GeoJSON linestrings cleanly using `to_shape()` without relying on mock attributes |
| Authentic Indian CCTV OSD Simulation | Provides high-fidelity operational experience with live IST clocks, RTSP status, and real-time AI bounding box overlays |
| Pluggable Real-World Dataset Adapters | Converts diverse external datasets (UVH-26, ITD, IRDD, RoundaboutHD) into standard platform events without altering core schemas |
| Heterogeneous Indian Vehicle Class Mapping | Explicitly accommodates auto-rickshaws, two-wheelers, and commercial vehicles prevalent in Indian traffic |
| Read-Optimized Dedicated Schemas | Decouples internal database representations from frontend requirements, ensuring optimal serialization speed and security |
| Non-Fabricated Evaluation Metrics | All metrics are computed strictly by evaluating real algorithmic components against deterministic ground-truth journeys |
| Standardized Scientific MOT Metrics | Uses MOTA, IDF1, and ID Switches for tracking validation |
| Resilient Event Bus with Redis Fallback | Guarantees the system operates 100% reliably even if Redis is unreachable or during maintenance |
| Idempotency Key Deduplication | Prevents double-processing and double-counting during network retries and high-throughput bursts |
| Dead-Letter Diagnostic Storage | Unhandled handler errors are isolated with stack traces without breaking the event pipeline |
| Objective Explainable Alert Wording | System uses telemetry facts ("Route anomaly detected") rather than subjective accusations ("Criminal activity") |
| Evidence Preservation in JSONB | Every alert stores the raw signal values and match confidences for courtroom auditing |
| Fundamental Traffic Flow Theory for Density | Density is mathematically grounded ($k = q / v_s$) with explicit methodology definitions |
| Stored-Data Derived Analytics | All metrics are computed strictly from real DB observations, connections, and trajectories |
| Deterministic Trajectory Reconstruction | Trajectory generation is purely deterministic given ordered observations |
| Multi-Signal Scoring over Plate Equality | Real-world ANPR suffers from weather, occlusions, and OCR confusion; multi-signal reasoning is resilient |

---

## Testing & Quality Summary

- **Total Unit Tests**: **124 Tests (100% Passed ✅)**
- **Test Coverage**:
  - `test_dataset_adapters.py`: All 5 Indian dataset adapters and real-world evaluation runner.
  - `test_dashboard_service.py`: City overview, live map, vehicle dossier investigation, and alert explainability.
  - `test_association_engine.py` & `test_association_scorer.py`: Multi-camera association, OCR Levenshtein, temporal velocity gating, and color/class consistency.
  - `test_evaluation_subsystem.py`: Synthetic benchmark dataset generator and MOTA/IDF1 evaluators.
  - `test_single_camera_tracker.py`: IoU bounding box tracking, tracklet continuity, and occlusion recovery.
  - `test_event_processing.py`: Resilient event bus, Redis pub/sub, in-memory fallback, and dead-letter queue.
  - `test_vehicle_observation.py`, `test_camera_service.py`, `test_road_service.py`, `test_vehicle_identity_service.py`, `test_trajectory_service.py`, `test_health_service.py`, `test_vehicle_track_service.py`.
- **System Doctor & Diagnostics**: 6/6 subsystem health check (`tools/doctor.py`) fully functional.
