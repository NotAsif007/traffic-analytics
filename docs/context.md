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

### Phase 6 — Cross-Camera Vehicle Association Engine [COMPLETE ✅]
- **Core Intelligence Engine**: Multi-signal cross-camera association determining whether sightings across disparate cameras represent the same physical vehicle without relying purely on plate string equality.
- **VehicleIdentity & VehicleMatch Entities**:
  - `VehicleIdentity` ([`app/models/vehicle_identity.py`](file:///d:/traffic-analytics/app/models/vehicle_identity.py)): City-wide vehicle hypothesis tracking consensus plate, class, color, confidence, total sightings, and lifecycle status (`candidate`, `accepted`, `rejected`, `needs_review`).
  - `VehicleMatch` ([`app/models/vehicle_match.py`](file:///d:/traffic-analytics/app/models/vehicle_identity.py)): Association link with `match_score`, `signals` breakdown JSONB, and human-auditable `reasoning` text.
  - Migration: [`alembic/versions/0005_create_vehicle_identities.py`](file:///d:/traffic-analytics/alembic/versions/0005_create_vehicle_identities.py).
- **Candidate Gating & Multi-Signal Scoring**:
  - `CandidateGating` ([`app/association/gating.py`](file:///d:/traffic-analytics/app/association/gating.py)): Spatio-temporal time window and topology filtering to eliminate $O(N^2)$ pairwise comparisons.
  - `AssociationScorer` ([`app/association/scorer.py`](file:///d:/traffic-analytics/app/association/scorer.py)): Computes plate similarity, appearance similarity, temporal travel feasibility with speed violation penalties, route connectivity, direction heading compatibility, and vehicle class/color alignment.
  - `AssociationEngine` ([`app/association/engine.py`](file:///d:/traffic-analytics/app/association/engine.py)): Evaluates candidate pairs, applies configurable weights & thresholds, and builds structured explainability narratives.
- **Association APIs**:
  - `GET /api/v1/identities`: List vehicle identities with filters.
  - `GET /api/v1/identities/{id}`: Detailed identity with all cross-camera match events.
  - `POST /api/v1/identities/associate`: On-demand or automated association engine trigger.
  - `GET /api/v1/matches`: List association match events with explainability metrics.

---

## Architectural Decisions Made

| Decision | Reason |
|---|---|
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
| `app/schemas/road.py` | Road schemas & GeoJSON types |
| `app/schemas/camera.py` | Camera schemas & status validation |
| `app/schemas/camera_connection.py` | CameraConnection schemas & integrity rules |
| `app/schemas/vehicle_observation.py` | VehicleObservation schemas & bulk types |
| `app/schemas/vehicle_track.py` | VehicleTrack & TrackPoint schemas & filters |
| `app/schemas/vehicle_identity.py` | VehicleIdentity & VehicleMatch schemas & explainability |
| `app/association/contracts.py` | Association contracts, scoring weights, and decision schemas |
| `app/association/scorer.py` | Multi-signal association scorer |
| `app/association/gating.py` | Spatio-temporal candidate generation gating |
| `app/association/engine.py` | AssociationEngine with explainability generation |
| `app/services/vehicle_identity.py` | Cross-camera association service & hypothesis management |
| `app/api/v1/identities.py` | VehicleIdentity API endpoints |
| `app/api/v1/matches.py` | VehicleMatch explainability query endpoints |
| `alembic/versions/0005_create_vehicle_identities.py` | DB migration for identities & matches |
| `tools/seed_city.py` | Synthetic city network seed script |

---

## Test Status
- **Unit Tests:** 89 passing (`pytest tests/unit/ -v`)
- **Integration Tests:** Ready for Docker environment testing (`roads`, `cameras`, `connections`, `observations`, `tracks`, `identities`)
