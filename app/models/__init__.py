"""
Models package.

Import all models here so Alembic can discover them via
`from app.models import *` in alembic/env.py.
"""

from app.models.alert import Alert, BlacklistEntry  # noqa: F401
from app.models.camera import Camera  # noqa: F401
from app.models.camera_connection import CameraConnection  # noqa: F401
from app.models.mixins import TimestampMixin, UUIDMixin  # noqa: F401
from app.models.road import Road  # noqa: F401
from app.models.trajectory import Trajectory, TrajectoryPoint  # noqa: F401
from app.models.vehicle_identity import VehicleIdentity, VehicleMatch  # noqa: F401
from app.models.vehicle_observation import VehicleObservation  # noqa: F401
from app.models.vehicle_track import TrackPoint, VehicleTrack  # noqa: F401

__all__ = [
    "UUIDMixin",
    "TimestampMixin",
    "Road",
    "Camera",
    "CameraConnection",
    "VehicleObservation",
    "VehicleTrack",
    "TrackPoint",
    "VehicleIdentity",
    "VehicleMatch",
    "Trajectory",
    "TrajectoryPoint",
    "BlacklistEntry",
    "Alert",
]
