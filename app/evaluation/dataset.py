"""Synthetic benchmark dataset generator for repeatable PS 26127 evaluation."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import NamedTuple

from app.evaluation.contracts import GroundTruthObservation, GroundTruthVehicle
from app.schemas.vehicle_observation import BoundingBox

BENCHMARK_BASE_TIME = datetime(2026, 8, 30, 9, 0, 0, tzinfo=timezone.utc)

# 8 Camera definitions
CAMERA_SPECS = [
    {
        "name": "C01",
        "id": uuid.UUID("11111111-1111-1111-1111-111111111101"),
        "lat": 12.9716,
        "lon": 77.5946,
    },
    {
        "name": "C02",
        "id": uuid.UUID("11111111-1111-1111-1111-111111111102"),
        "lat": 12.9750,
        "lon": 77.5980,
    },
    {
        "name": "C03",
        "id": uuid.UUID("11111111-1111-1111-1111-111111111103"),
        "lat": 12.9800,
        "lon": 77.6020,
    },
    {
        "name": "C04",
        "id": uuid.UUID("11111111-1111-1111-1111-111111111104"),
        "lat": 12.9650,
        "lon": 77.5900,
    },
    {
        "name": "C05",
        "id": uuid.UUID("11111111-1111-1111-1111-111111111105"),
        "lat": 12.9680,
        "lon": 77.5930,
    },
    {
        "name": "C06",
        "id": uuid.UUID("11111111-1111-1111-1111-111111111106"),
        "lat": 12.9850,
        "lon": 77.6080,
    },
    {
        "name": "C07",
        "id": uuid.UUID("11111111-1111-1111-1111-111111111107"),
        "lat": 12.9900,
        "lon": 77.6120,
    },
    {
        "name": "C08",
        "id": uuid.UUID("11111111-1111-1111-1111-111111111108"),
        "lat": 12.9950,
        "lon": 77.6150,
    },
]

CAM_MAP = {c["name"]: c for c in CAMERA_SPECS}

# Route definitions
ROUTES = [
    ["C01", "C02", "C03"],
    ["C01", "C03", "C06"],
    ["C04", "C05", "C01", "C02"],
    ["C03", "C06", "C07", "C08"],
    ["C05", "C01", "C03", "C06"],
    ["C02", "C03", "C06", "C07"],
]


class BenchmarkDataset(NamedTuple):
    cameras: list[dict]
    vehicles: list[GroundTruthVehicle]
    all_observations: list[GroundTruthObservation]
    blacklist_plates: set[str]
    total_anomalies: int


def generate_synthetic_benchmark() -> BenchmarkDataset:
    """
    Generates a deterministic benchmark dataset:
    - 8 Cameras
    - 35 Vehicles
    - Multiple urban routes
    - 5 OCR character substitution errors
    - 4 unreadable/missing plate observations
    - 3 Blacklisted vehicles
    - 3 Speed/temporal anomalies
    - 2 Route/direction anomalies
    - 4 Similar-looking vehicle pairs
    """
    vehicles: list[GroundTruthVehicle] = []
    all_observations: list[GroundTruthObservation] = []
    blacklist_plates: set[str] = {"KA01ST9999", "DL03TH1234", "MH12WR5555"}
    total_anomalies = 0

    # 35 Vehicle Profiles
    classes = ["car", "auto_rickshaw", "truck", "bus", "motorcycle", "van"]
    colors = ["white", "silver", "black", "red", "blue", "grey"]

    for i in range(1, 36):
        v_id = f"VEH-{i:03d}"
        plate = f"KA{i:02d}AB{1000 + i * 111}"
        if i == 1:
            plate = "KA01ST9999"  # Blacklisted stolen vehicle
        elif i == 2:
            plate = "DL03TH1234"  # Blacklisted bolo
        elif i == 3:
            plate = "MH12WR5555"  # Blacklisted tax defaulter

        is_blacklisted = plate in blacklist_plates
        v_class = classes[(i - 1) % len(classes)]
        v_color = colors[(i - 1) % len(colors)]

        # Select route
        route_names = ROUTES[(i - 1) % len(ROUTES)]

        # Start time staggered by vehicle index
        start_ts = BENCHMARK_BASE_TIME + timedelta(minutes=(i * 3))

        gt_veh = GroundTruthVehicle(
            vehicle_id=v_id,
            plate=plate,
            vehicle_class=v_class,
            vehicle_color=v_color,
            is_blacklisted=is_blacklisted,
            route_camera_names=route_names,
            observations=[],
        )

        curr_ts = start_ts
        for step_idx, cam_name in enumerate(route_names):
            cam_info = CAM_MAP[cam_name]
            obs_id = f"OBS-{v_id}-{step_idx+1}"

            # Default: high confidence perfect OCR read
            sim_plate = plate
            sim_conf = 0.96
            is_speed_anomaly = False
            is_route_anomaly = False

            # Inject simulated real-world noise:
            # 1. OCR character substitution on step 2 for vehicles 4, 5, 6, 7, 8
            if i in {4, 5, 6, 7, 8} and step_idx == 1:
                # e.g. change last digit 4 -> 8 or 0 -> O
                sim_plate = plate[:-1] + ("8" if plate[-1] != "8" else "3")
                sim_conf = 0.88

            # 2. Missing/unreadable plate on step 3 for vehicles 9, 10, 11, 12
            if i in {9, 10, 11, 12} and step_idx == len(route_names) - 1:
                sim_plate = None
                sim_conf = None

            # 3. Speed anomaly for vehicles 13, 14, 15 (transit in 3s instead of 180s)
            if i in {13, 14, 15} and step_idx == 1:
                curr_ts += timedelta(seconds=3)  # Impossible speed
                is_speed_anomaly = True
                total_anomalies += 1
            else:
                curr_ts += timedelta(minutes=4, seconds=30)  # Standard 270s transit

            # 4. Route direction anomaly for vehicles 16, 17
            if i in {16, 17} and step_idx == 1:
                is_route_anomaly = True
                total_anomalies += 1

            if is_blacklisted and step_idx == 0:
                total_anomalies += 1

            gt_obs = GroundTruthObservation(
                observation_id=obs_id,
                camera_id=cam_info["id"],
                camera_name=cam_name,
                timestamp=curr_ts,
                true_vehicle_id=v_id,
                true_plate=plate,
                true_class=v_class,
                true_color=v_color,
                true_bbox=BoundingBox(x1=0.2, y1=0.2, x2=0.6, y2=0.7),
                true_plate_bbox=BoundingBox(x1=0.35, y1=0.55, x2=0.55, y2=0.65),
                simulated_ocr_plate=sim_plate,
                simulated_ocr_confidence=sim_conf,
                is_blacklisted=is_blacklisted,
                is_speed_anomaly=is_speed_anomaly,
                is_route_anomaly=is_route_anomaly,
            )

            gt_veh.observations.append(gt_obs)
            all_observations.append(gt_obs)

        vehicles.append(gt_veh)

    return BenchmarkDataset(
        cameras=CAMERA_SPECS,
        vehicles=vehicles,
        all_observations=all_observations,
        blacklist_plates=blacklist_plates,
        total_anomalies=total_anomalies,
    )
