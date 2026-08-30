"""
API v1 router.

Aggregates all v1 sub-routers into a single router that gets mounted
at the API_V1_PREFIX in main.py.

Adding a new resource:
    1. Create app/api/v1/<resource>.py with its APIRouter
    2. Import the router here and include it
"""

from fastapi import APIRouter

from app.api.v1 import (
    camera_connections,
    cameras,
    health,
    identities,
    matches,
    observations,
    roads,
    tracks,
    trajectories,
    vehicles,
)

router = APIRouter()

# Infrastructure
router.include_router(health.router)

# Phase 2 — Geographic context
router.include_router(roads.router)
router.include_router(cameras.router)
router.include_router(camera_connections.router)

# Phase 3 — Observation ingestion
router.include_router(observations.router)

# Phase 5 — Single-camera tracking
router.include_router(tracks.router)

# Phase 6 — Cross-camera association & identities
router.include_router(identities.router)
router.include_router(matches.router)

# Phase 7 — City-wide vehicle trajectories
router.include_router(trajectories.router)
router.include_router(vehicles.router)

# Phase 8+ placeholders:
# router.include_router(blacklist.router)
# router.include_router(alerts.router)
