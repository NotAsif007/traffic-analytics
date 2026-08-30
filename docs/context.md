# Context — Traffic Analytics Backend

**Project:** PS 26127 — SIH 2026  
**Title:** City-Wide AI Engine for Multi-Camera ANPR Trajectory Tracking and Urban Traffic Analytics  
**Current Phase:** Real-World Indian Traffic Datasets & Benchmarking Complete  
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
  - Measures Indian ANPR accuracy, HSRP embossing recognition, heterogeneous vehicle class F1, and RoundaboutHD multi-camera tracking.

---

## Architectural Decisions Made

| Decision | Reason |
|---|---|
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

## Key Files

| File | Purpose |
|---|---|
| `app/main.py` | FastAPI application factory + lifespan |
| `app/config.py` | Central configuration via Pydantic Settings |
| `app/datasets/base.py` | Base abstract DatasetAdapter contract & parsed schema |
| `app/datasets/uvh26_adapter.py` | UVH-26 Indian CCTV vehicle detection parser |
| `app/datasets/itd_adapter.py` | ITD static camera traffic sequence parser |
| `app/datasets/indian_plate_adapter.py` | Indian license plate ANPR/OCR parser (HSRP & state codes) |
| `app/datasets/roundabout_adapter.py` | RoundaboutHD multi-camera tracking parser |
| `app/datasets/irdd_adapter.py` | Indian Road Driving Dataset (IRDD/IDD) parser |
| `app/datasets/__init__.py` | Dataset registry & helper exports |
| `app/evaluation/real_dataset_eval.py` | Real-world Indian traffic evaluation suite |
| `tools/import_real_dataset.py` | CLI dataset importer & live API streamer |
| `tools/doctor.py` | One-command system health & diagnostics CLI |
| `frontend/src/components/BenchmarkView.tsx` | Scientific benchmarking UI with dual-mode evaluation |
| `frontend/src/components/DiagnosticsModal.tsx` | In-browser developer console and test injector |

---

## Test Status
- **Unit Tests:** 124 passing (`pytest tests/unit/ -v`)
- **Linter:** Clean 0 errors (`ruff check .`)
- **Frontend Build:** Clean compilation (`npm run build` in 1.25s)
- **Integration Tests:** Ready for Docker environment testing (`roads`, `cameras`, `connections`, `observations`, `tracks`, `identities`, `trajectories`, `analytics`, `alerts`, `blacklist`, `events`, `dashboard`)
