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

### Phase 8 — Urban Traffic Analytics [COMPLETE ✅]
- **Real Stored-Data Driven Intelligence**: Computes traffic metrics strictly from stored observations, tracks, trajectories, and camera connections without mock values.
- **Traffic Analytics Capabilities**:
  - **Traffic Volume** (`GET /api/v1/analytics/volume`): Time-bucketed flow rates (`1m`, `5m`, `15m`, `1h`, `1d`) with vehicle-class breakdown.
  - **Vehicle Class Distribution** (`GET /api/v1/analytics/class-distribution`): Class breakdown and percentage distribution.
  - **Traffic Density** (`GET /api/v1/analytics/density`): Transparent Greenshields fundamental traffic flow theory ($k = q / v_s$) measuring vehicles/km from space-mean speed and flow rate, including explicit methodology metadata.
  - **Travel Time & Percentiles** (`GET /api/v1/analytics/travel-times`): Mean, median (p50), p85, p95, min, and max travel times for connected camera pairs.
  - **Congestion Index** (`GET /api/v1/analytics/congestion`): Real-time comparison of current segment travel times against baseline expected times ($CI = t_{\text{current}} / t_{\text{baseline}}$).
  - **Origin-Destination (OD) Matrix** (`GET /api/v1/analytics/od-matrix`): Camera/zone $A \to B$ trip volumes, average durations, and distances from completed trajectories.
  - **Route Frequency** (`GET /api/v1/analytics/routes`): Top recurring camera corridor sequences ranked by trip frequency.
  - **Camera Health Telemetry** (`GET /api/v1/analytics/camera-health`): Throughput (observations/minute), last sighting timestamp, inactivity tracking, and operational status (`online`, `stale`, `offline`).

---

## Architectural Decisions Made

| Decision | Reason |
|---|---|
| Fundamental Traffic Flow Theory for Density | Density is mathematically grounded ($k = q / v_s$) with explicit methodology definitions rather than arbitrary heuristics |
| Stored-Data Derived Analytics | All metrics are computed strictly from real DB observations, connections, and trajectories |
| Deterministic Trajectory Reconstruction | Trajectory generation is purely deterministic given ordered observations, ensuring reproducibility for legal audits |
| Multi-Signal Scoring over Plate Equality | Real-world ANPR suffers from weather, occlusions, and OCR confusion; multi-signal reasoning is resilient |
| Explainability-by-Design | Every association preserves its signal scores and reasoning text for government/courtroom auditing |
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
| `app/schemas/road.py` | Road schemas & GeoJSON types |
| `app/schemas/camera.py` | Camera schemas & status validation |
| `app/schemas/camera_connection.py` | CameraConnection schemas & integrity rules |
| `app/schemas/vehicle_observation.py` | VehicleObservation schemas & bulk types |
| `app/schemas/vehicle_track.py` | VehicleTrack & TrackPoint schemas & filters |
| `app/schemas/vehicle_identity.py` | VehicleIdentity & VehicleMatch schemas & explainability |
| `app/schemas/trajectory.py` | Trajectory & TrajectoryPoint schemas, filters, and timeline types |
| `app/schemas/analytics.py` | Urban Traffic Analytics schemas (volume, class, density, travel time, congestion, OD, routes, health) |
| `app/services/analytics.py` | Analytics calculation engine |
| `app/services/vehicle_identity.py` | Cross-camera association service & hypothesis management |
| `app/services/trajectory.py` | Trajectory lifecycle, transition validation & timeline reconstruction |
| `app/api/v1/analytics.py` | Analytics endpoints (volume, class-distribution, density, travel-times, congestion, od-matrix, routes, camera-health) |
| `app/api/v1/trajectories.py` | Trajectory list, detail, and timeline endpoints |
| `app/api/v1/vehicles.py` | Vehicle identity trajectory lookup endpoint |
| `alembic/versions/0006_create_trajectories.py` | DB migration for trajectories & points |
| `tools/seed_city.py` | Synthetic city network seed script |

---

## Test Status
- **Unit Tests:** 98 passing (`pytest tests/unit/ -v`)
- **Integration Tests:** Ready for Docker environment testing (`roads`, `cameras`, `connections`, `observations`, `tracks`, `identities`, `trajectories`, `analytics`)
