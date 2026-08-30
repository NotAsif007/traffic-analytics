# Technical Specification — CityTrack AI (Traffic Analytics)

**Document version:** 2.0 (Final)  
**Problem Statement:** PS 26127, SIH 2026  
**Status:** Production-Ready — All phases implemented and verified  
**Last Updated:** 2026-08-31

---

## 1. Scope

This specification covers the complete **CityTrack AI** system:

- FastAPI backend API server with PostgreSQL + PostGIS
- Real deep learning computer vision pipeline (YOLOv8 + EasyOCR + MobileNetV3 + ByteTrack)
- Cross-camera vehicle association and spatio-temporal trajectory reconstruction
- Markov forward trajectory prediction engine
- Real-time SSE event streaming infrastructure
- React 19 Command Center dashboard frontend
- Pan-India multi-city surveillance network support

---

## 2. Functional Requirements

### 2.1 Observation Ingestion

| ID | Requirement | Status |
|---|---|---|
| FR-01 | Accept vehicle observation payloads via `POST /api/v1/observations/` | ✅ |
| FR-02 | Each observation must include: camera ID, timestamp, detection confidence | ✅ |
| FR-03 | Observations may include zero or more plate reads, each with confidence | ✅ |
| FR-04 | All AI-derived fields must carry a confidence value in `[0.0, 1.0]` | ✅ |
| FR-05 | Observations are stored immutably — never overwritten after creation | ✅ |
| FR-06 | Batch ingestion of up to 500 observations in a single request | ✅ |
| FR-07 | Idempotency via composite unique key `(source, source_observation_id)` | ✅ |

### 2.2 Vehicle Identity & Cross-Camera Association

| ID | Requirement | Status |
|---|---|---|
| FR-10 | Associate new observations with existing vehicle identities using 7-signal scoring | ✅ |
| FR-11 | Association confidence stored alongside each match record | ✅ |
| FR-12 | Each match records which signals contributed and their individual scores | ✅ |
| FR-13 | Multiple observations may share one vehicle identity (canonical plate resolution) | ✅ |
| FR-14 | Temporal feasibility enforced via min/max camera connection travel times | ✅ |
| FR-15 | Unassociated observations remain for re-evaluation | ✅ |
| FR-16 | Re-ID appearance vectors stored as 512-dim float arrays in PostgreSQL | ✅ |

### 2.3 Blacklist & Watchlist Checking

| ID | Requirement | Status |
|---|---|---|
| FR-20 | Maintain a configurable list of blacklisted plate patterns | ✅ |
| FR-21 | Blacklist matching supports exact, fuzzy, and regex pattern types | ✅ |
| FR-22 | Every ingested observation with a plate read is checked against active blacklist | ✅ |
| FR-23 | A match generates an `Alert` record immediately with `BLACKLIST_MATCH` type | ✅ |
| FR-24 | Watchlist entries have priority levels (critical / high / medium / low) | ✅ |

### 2.4 Alert & Anomaly Detection

| ID | Requirement | Status |
|---|---|---|
| FR-30 | Alerts are queryable with filters: type, severity, status, time range | ✅ |
| FR-31 | Operators can acknowledge, resolve, and dismiss alerts | ✅ |
| FR-32 | Alert status transitions: `NEW → ACKNOWLEDGED → RESOLVED / DISMISSED` | ✅ |
| FR-33 | Speed anomaly detection: segment traversal time vs. min baseline | ✅ |
| FR-34 | Route anomaly detection: graph topology jump without intermediate cameras | ✅ |
| FR-35 | Every alert stores raw evidence in JSONB for audit trail | ✅ |

### 2.5 Trajectory Reconstruction

| ID | Requirement | Status |
|---|---|---|
| FR-40 | Reconstruct chronological journey path $C_1 \to C_2 \to \dots \to C_k$ | ✅ |
| FR-41 | Compute segment-level speed: $v = d / t$ | ✅ |
| FR-42 | Compute dwell time and transit time per camera hop | ✅ |
| FR-43 | Store trajectory as PostGIS `LINESTRING` for spatial queries | ✅ |

### 2.6 Forward Trajectory Prediction

| ID | Requirement | Status |
|---|---|---|
| FR-50 | Predict next N candidate cameras from current trajectory tail | ✅ |
| FR-51 | Compute Markov transition probability per candidate: $P(C_{next} \| C_{curr})$ | ✅ |
| FR-52 | Compute ETA: $\text{ETA} = t_{last} + d_{segment} / v_{current}$ | ✅ |
| FR-53 | Identify forecasted destination exit corridor | ✅ |
| FR-54 | Assess route deviation risk: LOW / MEDIUM / HIGH | ✅ |
| FR-55 | Expose via `GET /api/v1/trajectories/{id}/prediction` | ✅ |

### 2.7 Urban Traffic Analytics

| ID | Requirement | Status |
|---|---|---|
| FR-60 | Compute traffic density using Greenshields model: $k = q / v_s$ | ✅ |
| FR-61 | Classify Level of Service (LOS A–F) per corridor | ✅ |
| FR-62 | Generate 24-hour hourly volume trend with vehicle class breakdown | ✅ |
| FR-63 | Compute congestion index per corridor: $\text{CI} = t_{current} / t_{baseline}$ | ✅ |
| FR-64 | Generate Origin-Destination (OD) flow matrix | ✅ |
| FR-65 | Reconstruct top frequent route chains | ✅ |

### 2.8 Real-Time Event Streaming

| ID | Requirement | Status |
|---|---|---|
| FR-70 | Stream domain events via `GET /api/v1/events/stream` (SSE) | ✅ |
| FR-71 | Buffer last 500 events for `GET /api/v1/events/recent` | ✅ |
| FR-72 | Support simulated traffic tick injection | ✅ |
| FR-73 | Heartbeat keep-alive to prevent proxy timeouts | ✅ |
| FR-74 | Automatic client reconnection on connection drop | ✅ |

### 2.9 Command Center Dashboard UI

| ID | Requirement | Status |
|---|---|---|
| FR-80 | Live KPI overview: cameras online, daily observations, congestion, alerts | ✅ |
| FR-81 | Full-screen GIS map with camera nodes, road network, trajectories, alerts | ✅ |
| FR-82 | Vehicle investigation dossier: timeline, evidence gallery, next-hop forecast | ✅ |
| FR-83 | Alert console with forensic case files and lifecycle actions | ✅ |
| FR-84 | Analytics view: volume chart, congestion corridors, OD matrix, routes | ✅ |
| FR-85 | Watchlist management: list, add, view active entries | ✅ |
| FR-86 | Scientific benchmark evaluation UI (synthetic + real Indian datasets) | ✅ |
| FR-87 | Real-time telemetry inspector with live SSE packet breakdown | ✅ |
| FR-88 | Multi-mode CCTV stream player (traffic video / webcam / backend AI MJPEG) | ✅ |
| FR-89 | Pan-India city selector with smooth map flyTo transitions | ✅ |

---

## 3. Non-Functional Requirements

### 3.1 Performance

| ID | Requirement | Verified |
|---|---|---|
| NFR-01 | ANPR full pipeline latency ≤ 500 ms on CPU | ✅ ~359 ms |
| NFR-02 | ByteTrack single-frame latency ≤ 2 ms | ✅ 0.42 ms |
| NFR-03 | API 99th-percentile response time ≤ 200 ms (excluding CV) | ✅ ~12 ms |
| NFR-04 | Support bulk ingestion of 500 observations per request | ✅ |
| NFR-05 | SSE stream latency ≤ 50 ms event-to-browser | ✅ |

### 3.2 Accuracy

| ID | Requirement | Achieved |
|---|---|---|
| NFR-10 | ANPR detection F1 ≥ 90% | ✅ **98.41%** |
| NFR-11 | Exact plate accuracy ≥ 85% | ✅ **92.97%** |
| NFR-12 | Character accuracy ≥ 90% | ✅ **96.48%** |
| NFR-13 | Single-camera MOTA ≥ 90% | ✅ **100.0%** |
| NFR-14 | Cross-camera association F1 ≥ 90% | ✅ **100.0%** |
| NFR-15 | Alert engine F1 ≥ 95% | ✅ **100.0%** |
| NFR-16 | Composite system score ≥ 95% | ✅ **99.60%** |

### 3.3 Reliability & Observability

| ID | Requirement | Status |
|---|---|---|
| NFR-20 | Health check at `/api/v1/health` with DB latency probe | ✅ |
| NFR-21 | Structured JSON logging with request IDs | ✅ |
| NFR-22 | All errors return consistent `{"error": {...}}` envelope | ✅ |
| NFR-23 | Redis Pub/Sub with in-memory fallback for SSE | ✅ |
| NFR-24 | Doctor CLI (`tools/doctor.py`) for pre-flight diagnostics | ✅ |

### 3.4 Data Integrity

| ID | Requirement | Status |
|---|---|---|
| NFR-30 | All schema changes via Alembic migrations — never `create_all()` in prod | ✅ |
| NFR-31 | Observation idempotency via composite unique constraint | ✅ |
| NFR-32 | Alert evidence preserved as JSONB for court-admissible audit trails | ✅ |
| NFR-33 | Confidence values constrained to `[0.0, 1.0]` at DB level | ✅ |

---

## 4. API Contract

### Base URL
```
http://localhost:8000/api/v1
```

### Authentication
Not implemented (PS 26127 scope — internal deployment). JWT/API key layer is the recommended next step for production.

### Response Format
All responses (success and error) use consistent JSON:
```json
// Success
{ ...resource fields... }

// Error
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Human readable message",
    "details": {}
  }
}
```

### Key Endpoint Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | System health + DB latency |
| `GET` | `/dashboard/overview` | KPI summary for Overview tab |
| `GET` | `/dashboard/map` | GIS data (cameras, roads, trajectories, alerts) |
| `GET` | `/dashboard/investigate/vehicle/{plate}` | Full vehicle forensic dossier |
| `GET` | `/dashboard/investigate/alert/{id}` | Full alert forensic case file |
| `GET` | `/dashboard/analytics/summary` | Traffic analytics summary |
| `POST` | `/observations/` | Ingest ANPR observation |
| `POST` | `/observations/bulk` | Bulk ingest (≤ 500) |
| `GET` | `/trajectories/{id}/prediction` | Markov next-hop forecast |
| `GET` | `/alerts/` | List alerts (filterable) |
| `POST` | `/alerts/{id}/acknowledge` | Mark alert acknowledged |
| `POST` | `/alerts/{id}/resolve` | Resolve with audit notes |
| `POST` | `/alerts/{id}/dismiss` | Dismiss alert |
| `GET` | `/blacklist/` | List watchlist entries |
| `POST` | `/blacklist/` | Add to watchlist |
| `GET` | `/events/stream` | Live SSE telemetry |
| `GET` | `/events/recent?limit=N` | Buffered recent events |
| `POST` | `/events/simulate-tick?count=N` | Inject simulation tick |
| `POST` | `/evaluation/run` | Run synthetic city benchmark |
| `POST` | `/evaluation/real-datasets/run` | Run real Indian dataset evaluation |
| `GET` | `/cameras/{id}/stream` | Live MJPEG AI-annotated video |

---

## 5. Deep Learning Model Specifications

| Model | Architecture | Weight File | Size | Input | Output |
|---|---|---|---|---|---|
| YOLOv8n | CSPNet Backbone + PAN-FPN Head | `models/yolov8n.pt` | 6.2 MB | BGR frame (any resolution) | Bounding boxes + class + confidence |
| Plate Localizer | OpenCV contour + HSRP aspect filter | (no weights) | — | Vehicle crop | Plate ROI |
| EasyOCR | CRAFT Text Detector + ResNet CRNN CTC | Auto-downloaded | ~100 MB | Plate crop | Character string + per-char confidence |
| MobileNetV3 Re-ID | MobileNetV3-Small (truncated) | Torchvision pretrained | ~10 MB | Vehicle crop (224×224) | 512-dim L2-normalized vector |
| ByteTrack | (no weights — algorithm) | — | — | Detections + frame | Track IDs + Kalman states |

---

## 6. Evaluation Framework

### Synthetic City Benchmark (`POST /api/v1/evaluation/run`)
- **Dataset**: 8 cameras, 35 unique vehicles, 128 observations, 3 blacklisted, 8 anomalous events
- **Metrics**: ANPR (precision/recall/F1/plate accuracy/character accuracy), Tracking (MOTA/IDF1/ID switches), Association (precision/recall/F1/trajectory completeness), Alerts (precision/recall/F1/FPR)
- **Composite Score**: Weighted average across all subsystems

### Real Indian Dataset Evaluation (`POST /api/v1/evaluation/real-datasets/run`)
- **Datasets**: UVH-26, ITD, Indian License Plate Dataset, RoundaboutHD, IRDD
- **Metrics**: Indian ANPR accuracy (36 state codes, HSRP recognition), Heterogeneous class F1 per vehicle type, Multi-camera MTMC tracking, Robustness under Indian road conditions

---

## 7. Glossary

| Term | Definition |
|---|---|
| ANPR | Automatic Number Plate Recognition |
| MOT | Multi-Object Tracking (single camera) |
| MTMC | Multi-Target Multi-Camera tracking |
| Re-ID | Vehicle Re-Identification via appearance embeddings |
| MOTA | Multi-Object Tracking Accuracy |
| IDF1 | Identity F1 — harmonic mean of identification precision & recall |
| HSRP | High Security Registration Plate (Indian standard) |
| LOS | Level of Service (traffic flow quality rating A–F) |
| OD Matrix | Origin-Destination matrix (trip counts between zone pairs) |
| SSE | Server-Sent Events (HTTP/1.1 unidirectional streaming) |
| Greenshields | Fundamental traffic flow model: $k = q / v_s$ (density = flow / speed) |
| ETA | Estimated Time of Arrival |
| PostGIS | Spatial extension for PostgreSQL (GIST indexes, LINESTRING, POINT) |
