# Context — Traffic Analytics Backend

**Project:** PS 26127 — SIH 2026  
**Title:** City-Wide AI Engine for Multi-Camera ANPR Trajectory Tracking and Urban Traffic Analytics  
**Current Phase:** Phase 4 — ANPR Integration Layer Complete  
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

### Phase 12 — Command Center API Integration [COMPLETE ✅]
- **Read-Optimized Command Center Views**:
  - `CityOverviewResponse` ([`app/schemas/dashboard.py`](file:///d:/traffic-analytics/app/schemas/dashboard.py)): Summary of active cameras, total vehicles observed today, network traffic level, active/critical alerts count, congestion hotspots, and recent activity feed.
  - `LiveMapResponse` ([`app/schemas/dashboard.py`](file:///d:/traffic-analytics/app/schemas/dashboard.py)): GIS layers for Leaflet/Mapbox with camera intensity markers, road LineStrings, moving vehicle trajectory paths, and alert pins.
  - `VehicleInvestigationResponse` ([`app/schemas/dashboard.py`](file:///d:/traffic-analytics/app/schemas/dashboard.py)): Complete law enforcement vehicle dossier with camera history timeline, travel speeds, raw OCR plate detections, confidence scores, and crop image paths.
  - `AlertInvestigationResponse` ([`app/schemas/dashboard.py`](file:///d:/traffic-analytics/app/schemas/dashboard.py)): Forensic dossier containing full explainability evidence, multi-camera trajectory context, and involved cameras.
  - `DashboardAnalyticsSummaryResponse` ([`app/schemas/dashboard.py`](file:///d:/traffic-analytics/app/schemas/dashboard.py)): Executive overview aggregating 24-hour volume trend, top congested corridors, frequent routes, and OD flow matrix.
- **Dashboard APIs**:
  - `GET /api/v1/dashboard/overview`
  - `GET /api/v1/dashboard/map`
  - `GET /api/v1/dashboard/investigate/vehicle/{identity_id}`
  - `GET /api/v1/dashboard/investigate/alert/{alert_id}`
  - `GET /api/v1/dashboard/analytics/summary`

---

## Architectural Decisions Made

| Decision | Reason |
|---|---|
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
| Track ID vs Vehicle Identity | A track is local to a single camera stream; a vehicle identity is global across the road network |
| Spatio-Temporal Candidate Gating | Prevents $O(N^2)$ comparison explosion by gating candidates on connected road graph travel windows |
| Pluggable Tracker & Detector ABCs | Allows seamless swapping of AI models without touching domain models |
| Async SQLAlchemy (asyncpg) | Required for high-throughput ingestion without thread pool exhaustion |
| Confidence-first Data Model | AI outputs are uncertain; never treat OCR or detection as ground truth |
| Source + Source_Obs_ID Idempotency | Prevents double-counting from inference pipelines and retries |
| Object storage paths for media | Avoids database bloat; keeps DB lean for indexing and queries |
| Trigram index on plate_text | Enables efficient sub-string and partial plate queries |
| PostGIS GIST indexes | Allows fast spatial proximity queries (`ST_DWithin`) |
| Domain exceptions separate from HTTP | Domain layer has no FastAPI coupling — cleanly testable in isolation |

---

## Key Files

| File | Purpose |
|---|---|
| `app/main.py` | FastAPI application factory + lifespan |
| `app/config.py` | Central configuration via Pydantic Settings |
| `app/models/road.py` | Road model with PostGIS LINESTRING |
| `app/models/camera.py` | Camera model with PostGIS POINT |
| `app/models/camera_connection.py` | CameraConnection directed graph edge |
| `app/models/vehicle_observation.py` | VehicleObservation event model |
| `app/models/vehicle_track.py` | VehicleTrack and TrackPoint models |
| `app/models/vehicle_identity.py` | VehicleIdentity and VehicleMatch models |
| `app/models/trajectory.py` | Trajectory and TrajectoryPoint models |
| `app/models/alert.py` | Alert and BlacklistEntry models |
| `app/schemas/dashboard.py` | Read-optimized Command Center schemas (Overview, Map, Investigation, Analytics) |
| `app/services/dashboard.py` | Read-optimized consolidation engine for dashboard views |
| `app/api/v1/dashboard.py` | Command center endpoints (/overview, /map, /investigate/..., /analytics/summary) |
| `app/evaluation/contracts.py` | Ground truth schemas and EvaluationReport model |
| `app/evaluation/dataset.py` | Synthetic city benchmark dataset generator |
| `app/evaluation/runner.py` | Full-system benchmark runner |
| `tools/run_benchmark.py` | CLI benchmark executable tool |
| `app/events/contracts.py` | DomainEvent, EventType, DeadLetterRecord contracts |
| `app/events/interfaces.py` | EventBus and DeadLetterStore ABC interfaces |
| `app/events/coordinator.py` | End-to-end pipeline coordinator across all subsystems |
| `app/schemas/road.py` | Road schemas & GeoJSON types |
| `app/schemas/camera.py` | Camera schemas & status validation |
| `app/schemas/camera_connection.py` | CameraConnection schemas & integrity rules |
| `app/schemas/vehicle_observation.py` | VehicleObservation schemas & bulk types |
| `app/schemas/vehicle_track.py` | VehicleTrack & TrackPoint schemas & filters |
| `app/schemas/vehicle_identity.py` | VehicleIdentity & VehicleMatch schemas & explainability |
| `app/schemas/trajectory.py` | Trajectory & TrajectoryPoint schemas, filters, and timeline types |
| `app/schemas/analytics.py` | Urban Traffic Analytics schemas |
| `app/schemas/alert.py` | Alert and BlacklistEntry schemas & action requests |
| `app/services/alert.py` | Alert and anomaly detection service with lifecycle transitions |
| `app/services/analytics.py` | Analytics calculation engine |
| `app/services/vehicle_identity.py` | Cross-camera association service & hypothesis management |
| `app/services/trajectory.py` | Trajectory lifecycle, transition validation & timeline reconstruction |
| `app/api/v1/evaluation.py` | Benchmark evaluation report endpoints |
| `app/api/v1/events.py` | Real-time event publishing & dead-letter queue endpoints |
| `app/api/v1/alerts.py` | Alerts endpoints (list, get, acknowledge, resolve, dismiss) |
| `app/api/v1/blacklist.py` | Watchlist management endpoints |
| `app/api/v1/analytics.py` | Analytics endpoints |
| `app/api/v1/trajectories.py` | Trajectory endpoints |
| `app/api/v1/vehicles.py` | Vehicle identity trajectory lookup endpoint |
| `alembic/versions/0007_create_alerts_and_blacklist.py` | DB migration for alerts & blacklist |
| `tools/seed_city.py` | Synthetic city network seed script |

---

## Test Status
- **Unit Tests:** 117 passing (`pytest tests/unit/ -v`)
- **Integration Tests:** Ready for Docker environment testing (`roads`, `cameras`, `connections`, `observations`, `tracks`, `identities`, `trajectories`, `analytics`, `alerts`, `blacklist`, `events`, `dashboard`)
