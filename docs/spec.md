# Technical Specification — Traffic Analytics Backend

**Document version:** 1.0  
**Phase:** 1 — Foundation  
**Problem Statement:** PS 26127, SIH 2026

---

## 1. Scope

This specification covers the backend server for the City-Wide ANPR Trajectory Tracking system. It does not cover:

- Frontend applications
- Computer vision / AI model implementation
- Camera firmware or RTSP stream handling
- Network infrastructure

---

## 2. Functional Requirements

### 2.1 Observation Ingestion (Phase 1b)

| ID | Requirement |
|---|---|
| FR-01 | The system shall accept vehicle observation payloads via HTTP POST |
| FR-02 | Each observation shall include at minimum: camera ID, timestamp, detection confidence |
| FR-03 | Observations may include zero or more plate reads, each with a confidence score |
| FR-04 | All AI-derived fields shall carry a confidence value in [0.0, 1.0] |
| FR-05 | Observations shall be stored immutably — never overwritten after creation |
| FR-06 | Batch ingestion of multiple observations shall be supported |

### 2.2 Vehicle Identity & Association (Phase 1b)

| ID | Requirement |
|---|---|
| FR-10 | The system shall attempt to associate new observations with existing vehicle identities |
| FR-11 | Association confidence shall be stored alongside the match |
| FR-12 | Each match shall record which signals contributed and their individual scores |
| FR-13 | Multiple observations may share one vehicle identity |
| FR-14 | Vehicle identities may be manually merged by operators |
| FR-15 | Unassociated observations shall remain in the system and be re-evaluated on demand |

### 2.3 Blacklist Checking (Phase 1b)

| ID | Requirement |
|---|---|
| FR-20 | The system shall maintain a configurable list of blacklisted plate patterns |
| FR-21 | Blacklist matching shall support exact, fuzzy, and regex pattern types |
| FR-22 | Every ingested observation with a plate read shall be checked against active blacklist entries |
| FR-23 | A match shall generate an Alert record immediately |

### 2.4 Alerts (Phase 1b)

| ID | Requirement |
|---|---|
| FR-30 | Alerts shall be queryable with filters (type, severity, status, time range) |
| FR-31 | Operators shall be able to acknowledge and resolve alerts |
| FR-32 | Alert status transitions: new → acknowledged → resolved (or dismissed) |

### 2.5 Health & Operations (Phase 1 ✅)

| ID | Requirement | Status |
|---|---|---|
| FR-40 | The system shall expose a health endpoint that tests DB connectivity | ✅ Done |
| FR-41 | The system shall expose a lightweight readiness probe | ✅ Done |
| FR-42 | All errors shall return a consistent JSON error envelope | ✅ Done |

---

## 3. Non-Functional Requirements

| ID | Requirement | Target |
|---|---|---|
| NFR-01 | Observation ingestion latency (p99) | < 200ms |
| NFR-02 | API availability | > 99.5% |
| NFR-03 | All configuration via environment variables | 100% |
| NFR-04 | No secrets committed to version control | 100% |
| NFR-05 | All database changes via Alembic migrations | 100% |
| NFR-06 | API endpoints versioned under /api/v{n}/ | All endpoints |
| NFR-07 | Unit test coverage on service layer | > 80% |
| NFR-08 | Type hints throughout production code | 100% |

---

## 4. API Conventions

### 4.1 Versioning

All domain endpoints are prefixed with `/api/v1/`. Infrastructure endpoints (`/api/v1/health`) do not change between versions.

### 4.2 Error Responses

Every error (4xx, 5xx) returns:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Camera not found",
    "details": {
      "resource": "Camera",
      "identifier": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    }
  }
}
```

Standard error codes:

| HTTP | Code | When |
|---|---|---|
| 400 | `DOMAIN_ERROR` | Domain business rule violation |
| 404 | `NOT_FOUND` | Resource does not exist |
| 409 | `CONFLICT` | State conflict |
| 422 | `REQUEST_VALIDATION_ERROR` | Pydantic validation failure |
| 422 | `VALIDATION_ERROR` | Domain validation failure |
| 500 | `INTERNAL_ERROR` | Unhandled exception |
| 503 | `DATABASE_ERROR` | DB unreachable |
| 503 | `SERVICE_UNAVAILABLE` | External service unavailable |

### 4.3 Confidence Values

All AI-derived fields carry a corresponding `_confidence` field:

```json
{
  "plate_text": "AS01AB1234",
  "plate_confidence": 0.94,
  "vehicle_class": "car",
  "vehicle_class_confidence": 0.88
}
```

Confidence is always a float in [0.0, 1.0]. A value of `null` means the field was not computed.

### 4.4 Pagination

List endpoints accept `page` (1-indexed) and `page_size` query parameters and return:

```json
{
  "items": [...],
  "total": 1024,
  "page": 1,
  "page_size": 20,
  "pages": 52
}
```

### 4.5 IDs

All entity IDs are UUIDs (v4). They are represented as strings in JSON.

---

## 5. Data Model Summary

See [architecture.md](architecture.md) for the full ER diagram.

| Entity | Phase | Description |
|---|---|---|
| Camera | 1b | Physical camera with GPS location |
| VehicleObservation | 1b | Single camera sighting of a vehicle |
| PlateObservation | 1b | OCR plate read within an observation |
| VehicleIdentity | 1b | Cross-camera vehicle identity (derived) |
| VehicleMatch | 1b | Record of how two observations were associated |
| BlacklistEntry | 1b | Pattern-based plate blacklist |
| Alert | 1b | Triggered alert (blacklist hit, anomaly, etc.) |
| Road | 2 | Road segment with spatial geometry |
| CameraConnection | 2 | Topological edge between cameras |
| VideoSource | 2 | Metadata about an ingested video stream |
| Trajectory | 2 | Ordered set of trajectory points for a vehicle |
| TrajectoryPoint | 2 | Single point on a trajectory |
| AnalyticsSnapshot | 2 | Aggregated traffic metrics per camera/road/time |

---

## 6. Technology Stack

| Component | Technology | Version |
|---|---|---|
| Language | Python | 3.12+ |
| Web framework | FastAPI | 0.115+ |
| ASGI server | Uvicorn | 0.30+ |
| ORM | SQLAlchemy | 2.0+ (async) |
| DB driver | asyncpg | 0.29+ |
| Database | PostgreSQL + PostGIS | 16 + 3.4 |
| Migrations | Alembic | 1.13+ |
| Validation | Pydantic | 2.9+ |
| Settings | pydantic-settings | 2.5+ |
| Logging | structlog | 24.4+ |
| Queue (infra ready) | Redis | 7.4 |
| Testing | pytest + pytest-asyncio | 8.3+ |
| HTTP client (tests) | httpx | 0.27+ |
| Containerisation | Docker + Docker Compose | v2 |

---

## 7. Security Requirements (Phase 4)

- Authentication via API keys for camera-side clients
- JWT-based authentication for operator dashboard
- Rate limiting on ingestion endpoints
- No sensitive data in logs
- All database credentials from environment only
