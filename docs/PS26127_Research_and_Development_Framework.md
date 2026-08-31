# PS 26127 – Problem Discovery, Research & Development Framework

## 1. Identifying the Gap

### Current Situation

Cities already have:

- CCTV cameras
- ANPR systems
- Traffic control rooms
- E-challan systems
- Vehicle databases
- Surveillance infrastructure

### Gap 1: Isolated ANPR Systems

Most systems work as:

Camera → Plate Read → Store Record

They cannot reliably answer:

- Where did the vehicle come from?
- What route did it take?
- Which cameras missed it?
- Is the route unusual?

### Gap 2: Fragmented Traffic Data

Each camera behaves independently.

Camera A → Database A
Camera B → Database B
Camera C → Database C

There is no city-wide intelligence layer.

### Gap 3: OCR Failures Break Tracking

Challenges:

- OCR mistakes
- Partial plates
- Different camera angles
- Missing observations

Result:
The same vehicle may appear as multiple identities.

### Gap 4: Reactive Traffic Analytics

Authorities often know congestion occurred only after the fact.

Missing insights:

- Traffic flow patterns
- Congestion root causes
- Corridor utilization
- Route-level intelligence

### Problem Statement

Existing ANPR systems primarily function as isolated plate-recognition tools and lack the capability to reconstruct vehicle trajectories across multiple cameras, perform city-wide traffic intelligence, correlate fragmented observations, and generate actionable insights for urban mobility management.

---

# 2. Research

## Layer 1: Traffic Surveillance Research

Study:

- ANPR systems
- Intelligent Transportation Systems (ITS)
- Smart City surveillance
- Vehicle Re-identification (Re-ID)
- Traffic analytics

Research Topics:

- Multi-camera vehicle tracking
- Vehicle re-identification
- City-scale ANPR systems
- Urban mobility analytics

## Layer 2: Government & Industry Requirements

Study:

- Smart Cities Mission
- Ministry of Road Transport & Highways (MoRTH)
- Bharat Electronics Limited (BEL)
- Safe City initiatives

Goal:
Understand the motivation behind the problem statement.

## Layer 3: Academic Research

Focus Areas:

- Vehicle Re-ID
- Multi-camera tracking
- Trajectory reconstruction
- Traffic intelligence systems

## Layer 4: Datasets

Investigate:

- VeRi-776
- VehicleID
- UA-DETRAC
- AI City Challenge

Questions:

- Can they support benchmarking?
- Can they support trajectory reconstruction experiments?

## Layer 5: Traffic Operations

Study:

- Traffic command centers
- Vehicle investigations
- Alert workflows
- Traffic monitoring procedures

---

# 3. Existing Solutions in the Market

## Commercial ANPR Solutions

Examples:

- Genetec AutoVu
- Bosch ANPR
- Hikvision ANPR
- Dahua ANPR

Capabilities:

- License plate recognition
- Vehicle logging
- Basic alert generation

## Traffic Monitoring Platforms

Capabilities:

- Vehicle counting
- Traffic flow measurement
- Intersection monitoring

## Vehicle Re-ID Research Systems

Capabilities:

- Vehicle re-identification

Limitations:

- Often research-only
- Not integrated with traffic intelligence workflows

## Opportunity & Differentiation

Our platform aims to combine:

- ANPR
- Vehicle identity resolution
- Cross-camera association
- Trajectory reconstruction
- Traffic analytics
- Explainable intelligence
- Alert generation

within a single integrated architecture.

---

# 4. Ideation

## Idea 1

Simple ANPR

Status: Rejected

Reason:
Too common and lacks innovation.

## Idea 2

ANPR + Dashboard

Status: Weak

Reason:
Limited intelligence.

## Idea 3

ANPR + Cross-Camera Tracking

Status: Better

Reason:
Introduces vehicle continuity.

## Idea 4

ANPR + Trajectory Intelligence

Status: Strong

Reason:
Enables route reconstruction.

## Idea 5 (Selected)

ANPR + Trajectory Intelligence + Traffic Analytics + Alerts

Vision:

An AI-powered city-wide vehicle intelligence platform that reconstructs vehicle journeys across distributed camera networks and transforms fragmented surveillance data into actionable traffic intelligence.

---

# 5. Design

## High-Level System Architecture

CCTV
↓
Vehicle Detection
↓
Plate Detection
↓
OCR
↓
Observation Engine
↓
Association Engine
↓
Vehicle Identity
↓
Trajectory Engine
↓
Analytics
↓
Alerts
↓
Dashboard

## Core Database Entities

### Camera

Stores camera metadata and location.

### Observation

Stores normalized vehicle observations.

### Track

Stores single-camera tracking information.

### VehicleIdentity

Represents city-wide vehicle identity hypotheses.

### Trajectory

Represents vehicle journeys.

### Alert

Stores generated alerts.

### AnalyticsSnapshot

Stores traffic intelligence metrics.

## UI Modules

### Dashboard

System overview.

### Live Cameras

Camera monitoring.

### Vehicle Search

Vehicle investigation.

### Trajectory Explorer

Journey visualization.

### Traffic Analytics

Traffic intelligence.

### Alert Center

Alert management.

## Explainability Layer

Every vehicle match should provide:

- Plate similarity
- Appearance similarity
- Travel feasibility
- Direction compatibility
- Final confidence score

---

# 6. Build

## Page 1

Backend Foundation

Deliverables:

- FastAPI
- PostgreSQL/PostGIS
- Camera Management
- Observation Ingestion

## Page 2

ANPR Pipeline

Deliverables:

- Vehicle Detection
- Plate Detection
- OCR

## Page 3

Single-Camera Tracking

Deliverables:

- Track creation
- Track management

## Page 4

Cross-Camera Association

Deliverables:

- Vehicle matching
- Identity creation

## Page 5

Trajectory Engine

Deliverables:

- Route reconstruction
- Confidence scoring

## Page 6

Traffic Analytics

Deliverables:

- Vehicle counts
- Travel time analytics
- Congestion detection

## Page 7

Alerts

Deliverables:

- Blacklist detection
- Route anomaly detection

## Page 8

Dashboard

Deliverables:

- GIS visualization
- Traffic intelligence views
- Alert management

---

# 7. Validate

## Validation Layer 1: ANPR Accuracy

Metrics:

- Detection Precision
- Detection Recall
- OCR Accuracy

## Validation Layer 2: Tracking

Metrics:

- IDF1
- MOTA
- ID Switches

## Validation Layer 3: Cross-Camera Matching

Metrics:

- Association Precision
- Association Recall

## Validation Layer 4: Trajectory Reconstruction

Ground Truth Example:

Vehicle A:
C1 → C3 → C6

Compare:

- Predicted Route
- Actual Route

Metrics:

- Trajectory Accuracy
- Missed Associations
- False Associations

## Validation Layer 5: Traffic Analytics

Validate:

- Vehicle counts
- Travel time estimation
- Congestion detection

using deterministic synthetic scenarios.
