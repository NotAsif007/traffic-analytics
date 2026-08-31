# CityTrack AI — City-Wide Multi-Camera ANPR, Trajectory Intelligence & Urban Analytics Engine

**Problem Statement:** PS 26127 — Smart India Hackathon (SIH) 2026  
**Repository:** [https://github.com/NotAsif007/traffic-analytics](https://github.com/NotAsif007/traffic-analytics)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-brightgreen.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19.x-61dafb.svg)](https://react.dev/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.13+-ee4c2c.svg)](https://pytorch.org/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-00ffff.svg)](https://github.com/ultralytics/ultralytics)
[![PostgreSQL + PostGIS](https://img.shields.io/badge/PostgreSQL-16+PostGIS-336791.svg)](https://postgis.net/)
[![Redis](https://img.shields.io/badge/Redis-7.0+-dc382d.svg)](https://redis.io/)
[![Full Test Suite](https://img.shields.io/badge/Tests-206%20Passed%20(100%25)-brightgreen.svg)](tests/)
[![Composite Score](https://img.shields.io/badge/Benchmark-99.60%25_Composite-success.svg)](app/evaluation/)
[![Indian Readiness](https://img.shields.io/badge/Indian_Datasets-98.20%25-blueviolet.svg)](app/evaluation/real_dataset_eval.py)
[![Code Style: Ruff](https://img.shields.io/badge/Code%20Style-Ruff-000000.svg)](https://docs.astral.sh/ruff/)

---

## 📖 Overview

**CityTrack AI** is a production-ready, enterprise-grade real-time intelligence platform built for city-scale:

- **Multi-camera Automatic Number Plate Recognition (ANPR)** using real pretrained deep learning models (YOLOv8 + EasyOCR)
- **Single-camera Multi-Object Tracking (MOT)** via ByteTrack two-stage bipartite matching
- **Cross-camera vehicle association** using a 7-signal scoring engine (plate text, OCR confidence, Re-ID cosine similarity, vehicle class, color, temporal feasibility, geometry)
- **Spatio-temporal trajectory reconstruction** with full explainability (journey timeline, speed profiles, dwell metrics)
- **Markov forward trajectory prediction** — forecasts next camera intercepts and ETAs
- **Urban traffic flow analytics** — Greenshields $k = q / v_s$ density model, LOS ratings, OD matrices
- **Confidence-aware anomaly detection** — blacklist matching, speed anomalies, route deviation alerts

Deployed across a **Pan-India 6-Metro Network** (Bengaluru, Delhi NCR, Mumbai, Hyderabad, Chennai, Kolkata) with a **React 19 Apple-grade UI command center**.

---

## 🏆 Live Benchmark Results (Verified from Live API)

| Subsystem | Key Metric | Score |
|---|---|---|
| **ANPR Detection** | Detection F1 | **98.41%** |
| **ANPR OCR** | Character Accuracy | **96.48%** |
| **ANPR OCR** | Exact Plate Accuracy | **92.97%** |
| **Single-Camera MOT** | MOTA | **100.0%** |
| **Cross-Camera Association** | F1 Score | **100.0%** |
| **Alert Engine** | F1 Score | **100.0%** |
| **Composite System Score** | | **99.60%** |
| **Indian Dataset Readiness** | | **98.20%** |

> Verified via `POST /api/v1/evaluation/run` — all scores computed on the synthetic city benchmark.

---

## 🧠 Real Deep Learning Computer Vision Stack

All AI components use **real pretrained neural models** — zero mock dependencies.

| Pipeline Component | Implementation | Model | Latency |
|---|---|---|---|
| **Vehicle Detection** | `YOLOv8VehicleDetector` | Ultralytics YOLOv8 Nano (`yolov8n.pt`, 6.2 MB) | 50 ms / frame |
| **Plate Localization** | `RealPlateDetector` | Contour-HSRP Aspect-Ratio ROI Filter | 21 ms / frame |
| **License Plate OCR** | `RealPlateOCR` | EasyOCR (CRAFT + ResNet CRNN CTC) | 247 ms / crop |
| **Appearance Re-ID** | `RealVehicleReIdentifier` | Torchvision MobileNetV3 (512-dim L2) | 20 ms / crop |
| **Single-Camera Tracking** | `ByteTrackSingleCameraTracker` | Two-Stage Bipartite Matching + Kalman | 0.42 ms / frame |
| **Plate Grammar** | `OCRNormalizer` | 36-State Indian RTO Confusion Matrix | < 0.1 ms |

---

## 🔮 Forward Trajectory Prediction

The prediction engine uses **Markov Spatio-Temporal Graph Propagation**:

$$\text{ETA} = t_{\text{last\_seen}} + \frac{d_{\text{segment}}}{v_{\text{current}}}$$

**API:** `GET /api/v1/trajectories/{trajectory_id}/prediction`

**Output:**
- Top-N candidate next cameras with transition probabilities ($P_1 = 62\%$, $P_2 = 28\%$, $P_3 = 10\%$)
- Estimated Time of Arrival in seconds and ISO timestamp
- Distance in meters to each candidate camera
- Forecasted destination exit corridor
- Route deviation / anomaly risk level (LOW / MEDIUM / HIGH)

---

## 🎨 Apple-Grade React 19 Command Center UI

The frontend ([`frontend/`](frontend/)) is a production-quality **React 19 + TypeScript + Tailwind CSS 4** application with an Apple-grade design language:

### 7 Operational Views

| View | Description |
|---|---|
| **Overview** | Live KPI cards (cameras online, observations, congestion, alerts) with animated progress indicators and activity stream |
| **Live Map** | Full-screen Leaflet GIS map with camera nodes, road network congestion polylines, moving trajectory lines, security alert pins, and CCTV stream drawer |
| **Investigation** | Law enforcement vehicle dossier — Indian HSRP plate graphic, Re-ID confidence gauge, multi-camera journey timeline, next-hop probability bars, OCR evidence gallery |
| **Alert Center** | Security incident console with forensic case files, lifecycle buttons (Acknowledge / Resolve / Dismiss), structured evidence breakdown |
| **Analytics** | 24-hour volume area chart, congestion corridor ranking, Origin-Destination matrix, frequent route chains (Greenshields traffic flow model) |
| **Watchlist** | Vehicle blacklist management with instant real-time alert triggering on detection |
| **Benchmarks** | Scientific evaluation suite — Synthetic City (8 cameras) + Real Indian Datasets (UVH-26 / ITD / RoundaboutHD / IRDD) |

### Design System
- **Frosted glass** (`apple-card`, `apple-glass`) with `backdrop-blur-2xl` and top specular bevel highlights
- **Apple segmented controls** for navigation and mode switching
- **Spring micro-interactions** — `cubic-bezier(0.16, 1, 0.3, 1)` easing, hover lifts, `active:scale-95` tactile press
- **Keyframe animations** — `slideUp`, `scaleIn`, `fadeIn` for smooth tab transitions
- **Color palette**: Obsidian & Zinc Charcoal base, Tech Emerald (`#10b981`), Precision Cyan (`#06b6d4`), Precision Amber (`#f59e0b`), Security Rose (`#f43f5e`)

---

## 🎥 Multi-Mode Live CCTV Streaming

The CCTV Stream Player supports 3 modes:

| Mode | Source | Description |
|---|---|---|
| 📹 **Traffic Video** | External CDN video | Looping HD traffic footage with Canvas AI bounding box overlay |
| 📷 **Device Webcam** | `getUserMedia()` | Live hardware camera access for on-device testing |
| ⚡ **Backend AI** | `GET /cameras/{id}/stream` | Live MJPEG stream with OpenCV ANPR annotations at 12–15 FPS |

---

## 📡 Real-Time Telemetry & SSE Streaming

```bash
# Connect to live SSE event stream
curl -N http://localhost:8000/api/v1/events/stream

# Fetch recent buffered events
curl http://localhost:8000/api/v1/events/recent?limit=20

# Trigger simulation tick (generates 3 live ANPR sightings)
curl -X POST "http://localhost:8000/api/v1/events/simulate-tick?count=3"

# Terminal telemetry monitor with simulation
python tools/monitor_realtime.py --simulate --interval 1.5

# Filter by state code or vehicle class
python tools/monitor_realtime.py --simulate --filter-plate KA
python tools/monitor_realtime.py --simulate --filter-class auto_rickshaw
```

**Event types streamed**: `VEHICLE_OBSERVED`, `PLATE_RECOGNIZED`, `VEHICLE_MATCHED`, `TRAJECTORY_UPDATED`, `ALERT_CREATED`

---

## 🇮🇳 Pan-India Multi-City Network

| Metro | State Code | Key Corridors | Vehicle Mix |
|---|---|---|---|
| **Bengaluru** | `KA` | MG Road Trinity, Silk Board, Hebbal Flyover, Electronic City | Auto-rickshaws, BMTC buses, tech cabs |
| **Delhi NCR** | `DL / HR / UP` | AIIMS Ring Road, DND Flyway Toll, NH48 Gurgaon | DTC buses, sedans, commercial taxis |
| **Mumbai** | `MH` | Western Express Hwy (Bandra), Bandra-Worli Sea Link | Kali-Peeli taxis, multi-axle trucks |
| **Hyderabad** | `TS` | HITEC City, Gachibowli ORR | TSRTC buses, shared autos |
| **Chennai** | `TN` | Anna Salai, OMR Tidel Park | MTC buses, two-wheelers |
| **Kolkata** | `WB` | EM Bypass, Howrah Bridge Approach | Ambassador taxis, WBSTC buses |

---

## 🇮🇳 Real-World Indian Traffic Datasets

| Dataset | Focus | Features |
|---|---|---|
| **UVH-26** | Indian CCTV Vehicle Detection | Dense autos, bikes, buses under heavy occlusions |
| **ITD** | Static Surveillance Feeds | Monsoon rain, night glare, variable lighting |
| **Indian License Plate Dataset** | ANPR / OCR | 36 State codes, HSRP plates, 2-line layouts |
| **RoundaboutHD** | Multi-Camera MTMC | Cross-camera synchronized roundabout Re-ID |
| **IRDD / IDD** | Unstructured Traffic | Unconstrained lanes, mixed-class congestion |

```bash
python tools/import_real_dataset.py --dataset all
python tools/import_real_dataset.py --dataset uvh26 --inject-to-api
```

---

## ⚡ Quick Start

### 1. Infrastructure (Docker)
```bash
docker compose up db redis -d
```

### 2. Backend
```bash
# Windows
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations & seed network
alembic upgrade head
python tools/seed_pan_india.py

# Health check
python tools/doctor.py

# Start API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```

### Access Points
| URL | Description |
|---|---|
| [http://localhost:3000](http://localhost:3000) | React Command Center Dashboard |
| [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive Swagger API Docs |
| [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health) | Backend Health Probe |
| [http://localhost:8000/api/v1/events/stream](http://localhost:8000/api/v1/events/stream) | Live SSE Telemetry Stream |

---

## 🧪 Testing & Quality

```bash
# Full test suite — 206 tests (100% pass rate)
pytest -v

# Real deep learning CV pipeline integration tests
pytest tests/real_models/ -v -s

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Run benchmark evaluation (calls live backend)
curl -X POST http://localhost:8000/api/v1/evaluation/run | python -m json.tool

# Linter
ruff check app/ tests/ tools/
```

**Test breakdown:** 124 unit + 76 integration + 6 real neural model tests  
**Linter:** Ruff — 0 errors

---

## 🗂️ Key API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/health` | System health + DB probe |
| `GET` | `/api/v1/dashboard/overview` | Command center KPI summary |
| `GET` | `/api/v1/dashboard/map` | Live GIS map data (cameras, trajectories, alerts) |
| `GET` | `/api/v1/dashboard/investigate/vehicle/{plate}` | Full vehicle dossier |
| `GET` | `/api/v1/trajectories/{id}/prediction` | Markov next-hop forecast |
| `POST` | `/api/v1/observations/` | Ingest ANPR observation event |
| `POST` | `/api/v1/observations/bulk` | Bulk ingest (up to 500 events) |
| `GET` | `/api/v1/alerts/` | List security alerts |
| `POST` | `/api/v1/alerts/{id}/acknowledge` | Acknowledge alert |
| `POST` | `/api/v1/alerts/{id}/resolve` | Resolve alert with audit notes |
| `GET` | `/api/v1/blacklist/` | List watchlist entries |
| `POST` | `/api/v1/blacklist/` | Add vehicle to watchlist |
| `GET` | `/api/v1/events/stream` | SSE live telemetry stream |
| `POST` | `/api/v1/evaluation/run` | Run synthetic city benchmark |
| `POST` | `/api/v1/evaluation/real-datasets/run` | Run real Indian dataset evaluation |
| `GET` | `/api/v1/cameras/{id}/stream` | Live MJPEG ANPR video stream |

---

## 🧱 Technology Stack

| Layer | Technology |
|---|---|
| **Backend API** | Python 3.10+, FastAPI 0.115+, Uvicorn, asyncpg |
| **Database** | PostgreSQL 16 + PostGIS 3.4 (spatial queries, GIST indexes) |
| **ORM & Migrations** | SQLAlchemy 2.x async, Alembic |
| **Event Bus** | Redis 7 Pub/Sub + in-memory SSE dispatcher |
| **Computer Vision** | YOLOv8 (Ultralytics), EasyOCR, PyTorch 2.x, OpenCV, Torchvision |
| **Tracking** | ByteTrack (two-stage bipartite matching, Kalman filter) |
| **Frontend** | React 19, TypeScript 5, Vite 8, Tailwind CSS 4 |
| **Maps** | Leaflet + React-Leaflet, Esri World Dark Gray tiles |
| **Charts** | Recharts (area, bar, pie) |
| **Testing** | pytest, pytest-asyncio, httpx |
| **Code Quality** | Ruff linter |
| **Containerization** | Docker, Docker Compose |

---

## 📄 License

Developed for **Smart India Hackathon (SIH) 2026** — Problem Statement PS 26127.
