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

### Phase 4 — ANPR Integration Layer [COMPLETE ✅]
- **Inference Contracts**: Standardized Pydantic schemas (`FrameInput`, `VehicleDetectionResult`, `PlateDetectionResult`, `OCRResult`, `ObservationCandidate`) independent of any ML framework.
- **Abstract Interfaces**: Clean ABC interfaces (`VehicleDetector`, `PlateDetector`, `PlateOCR`) allowing pluggable swap between YOLO, PaddleOCR, LPRNet, or cloud vision APIs.
- **Traceable OCR Normalizer**: `OCRNormalizer` supporting delimiter stripping, uppercasing, configurable character confusion mapping (`O`->`0`, `I`->`1`, etc.), confidence penalties, and comprehensive step-by-step transformation audit records (`TransformationStep`).
- **Plate Comparison & Similarity Engine**: `PlateMatcher` providing exact match, normalized match, Levenshtein edit distance, normalized string similarity, substring/partial overlap detection, and multi-signal confidence propagation.
- **ANPR Pipeline Orchestrator**: `ANPRPipeline` turning raw frame metadata into validated `VehicleObservationCreate` domain records with proper confidence propagation and media reference tracking.
- **Mock Inference Suite**: `MockVehicleDetector`, `MockPlateDetector`, `MockPlateOCR` providing deterministic, configurable inference simulation for unit and integration tests without GPU dependencies.

---

## Architectural Decisions Made

| Decision | Reason |
|---|---|
| Async SQLAlchemy (asyncpg) | Required for high-throughput ingestion without thread pool exhaustion |
| Confidence-first Data Model | AI outputs are uncertain; never treat OCR or detection as ground truth |
| Source + Source_Obs_ID Idempotency | Prevents double-counting from inference pipelines and retries |
| Object storage paths for media | Avoids database bloat; keeps DB lean for indexing and queries |
| Batch-query validation in bulk ingest | Pre-fetches cameras and existing IDs in $O(1)$ queries to avoid N+1 overhead |
| Trigram index on plate_text | Enables efficient sub-string and partial plate queries |
| PostGIS GIST indexes | Allows fast spatial proximity queries (`ST_DWithin`) |
| Domain exceptions separate from HTTP | Domain layer has no FastAPI coupling — cleanly testable in isolation |
| SAVEPOINT test isolation | Fast test execution and isolation without table truncation |

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
| `app/schemas/road.py` | Road schemas & GeoJSON types |
| `app/schemas/camera.py` | Camera schemas & status validation |
| `app/schemas/camera_connection.py` | CameraConnection schemas & integrity rules |
| `app/schemas/vehicle_observation.py` | VehicleObservation schemas & bulk types |
| `app/repositories/vehicle_observation.py` | Observation repository with multi-filter query builder |
| `app/services/vehicle_observation.py` | Ingestion, bulk processing, and lifecycle services |
| `app/api/v1/observations.py` | Observation endpoints (single, bulk, list, status) |
| `alembic/versions/0003_create_vehicle_observations.py` | Phase 3 DB migration with pg_trgm & GIN index |
| `tools/seed_city.py` | Synthetic city network seed script |
| `app/anpr/contracts.py` | Model-agnostic AI inference contracts & schemas |
| `app/anpr/interfaces.py` | Abstract detector & OCR interfaces (ABCs) |
| `app/anpr/normalizer.py` | Traceable OCR normalizer with transformation logs |
| `app/anpr/matcher.py` | Plate comparison, edit distances, and confidence propagation |
| `app/anpr/pipeline.py` | ANPR pipeline orchestrator converting frames to domain observations |
| `app/anpr/mock.py` | Configurable mock vision models for deterministic automated testing |

---

## Test Status
- **Unit Tests:** 59 passing (`pytest tests/unit/ -v`)
- **Integration Tests:** Ready for Docker environment testing (`roads`, `cameras`, `connections`, `observations`)
