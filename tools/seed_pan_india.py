#!/usr/bin/env python3
"""
Pan-India Multi-City Network Seeder (PS 26127).

Populates PostgreSQL + PostGIS database with authentic road networks, CCTV cameras,
directed connections, real vehicle observations, trajectories, and security alerts
across 6 Major Indian Metropolitan Hubs:
  1. Bengaluru (KA)
  2. Delhi NCR (DL/HR/UP)
  3. Mumbai (MH)
  4. Hyderabad (TS)
  5. Chennai (TN)
  6. Kolkata (WB)

Usage:
    python tools/seed_pan_india.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from geoalchemy2.elements import WKTElement
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import get_settings
from app.models.alert import Alert, BlacklistEntry
from app.models.camera import Camera
from app.models.camera_connection import CameraConnection
from app.models.road import Road
from app.models.trajectory import Trajectory, TrajectoryPoint
from app.models.vehicle_identity import VehicleIdentity, VehicleMatch
from app.models.vehicle_observation import VehicleObservation
from app.models.vehicle_track import TrackPoint, VehicleTrack


# City Definitions with Center GPS Coordinates
CITIES = {
    "Bengaluru": {"state": "KA", "lat": 12.9716, "lng": 77.5946},
    "Delhi NCR": {"state": "DL", "lat": 28.6139, "lng": 77.2090},
    "Mumbai": {"state": "MH", "lat": 19.0760, "lng": 72.8777},
    "Hyderabad": {"state": "TS", "lat": 17.3850, "lng": 78.4867},
    "Chennai": {"state": "TN", "lat": 13.0827, "lng": 80.2707},
    "Kolkata": {"state": "WB", "lat": 22.5726, "lng": 88.3639},
}

ROADS_DATA = [
    # BENGALURU
    {
        "city": "Bengaluru",
        "external_id": "BLR-RD-01",
        "name": "MG Road Corridor (Bengaluru)",
        "wkt": "LINESTRING(77.5850 12.9750, 77.5950 12.9750, 77.6050 12.9750, 77.6150 12.9750)",
        "speed_limit_kmh": 50,
        "direction": "both",
    },
    {
        "city": "Bengaluru",
        "external_id": "BLR-RD-02",
        "name": "Silk Board - Electronic City Expressway",
        "wkt": "LINESTRING(77.6200 12.9170, 77.6400 12.8800, 77.6600 12.8450)",
        "speed_limit_kmh": 80,
        "direction": "both",
    },
    {
        "city": "Bengaluru",
        "external_id": "BLR-RD-03",
        "name": "Hebbal Flyover - Outer Ring Road",
        "wkt": "LINESTRING(77.5850 13.0350, 77.6050 13.0380, 77.6350 13.0300)",
        "speed_limit_kmh": 70,
        "direction": "both",
    },

    # DELHI NCR
    {
        "city": "Delhi NCR",
        "external_id": "DEL-RD-01",
        "name": "Outer Ring Road (AIIMS - Nehru Place)",
        "wkt": "LINESTRING(77.2100 28.5670, 77.2300 28.5550, 77.2520 28.5480)",
        "speed_limit_kmh": 60,
        "direction": "both",
    },
    {
        "city": "Delhi NCR",
        "external_id": "DEL-RD-02",
        "name": "DND Flyway (Delhi - Noida)",
        "wkt": "LINESTRING(77.2600 28.5800, 77.2900 28.5750, 77.3200 28.5700)",
        "speed_limit_kmh": 80,
        "direction": "both",
    },
    {
        "city": "Delhi NCR",
        "external_id": "DEL-RD-03",
        "name": "Gurgaon Cyber City - NH48 Expressway",
        "wkt": "LINESTRING(77.0850 28.4900, 77.0950 28.4800, 77.1050 28.4700)",
        "speed_limit_kmh": 80,
        "direction": "both",
    },

    # MUMBAI
    {
        "city": "Mumbai",
        "external_id": "BOM-RD-01",
        "name": "Western Express Highway (Bandra - Andheri)",
        "wkt": "LINESTRING(72.8400 19.0600, 72.8500 19.0900, 72.8600 19.1200)",
        "speed_limit_kmh": 70,
        "direction": "both",
    },
    {
        "city": "Mumbai",
        "external_id": "BOM-RD-02",
        "name": "Bandra-Worli Sea Link",
        "wkt": "LINESTRING(72.8150 19.0200, 72.8200 19.0350, 72.8300 19.0500)",
        "speed_limit_kmh": 80,
        "direction": "both",
    },
    {
        "city": "Mumbai",
        "external_id": "BOM-RD-03",
        "name": "Marine Drive Promenade Corridor",
        "wkt": "LINESTRING(72.8220 18.9350, 72.8230 18.9450, 72.8250 18.9550)",
        "speed_limit_kmh": 50,
        "direction": "both",
    },

    # HYDERABAD
    {
        "city": "Hyderabad",
        "external_id": "HYD-RD-01",
        "name": "HITEC City - Cyber Towers Arterial",
        "wkt": "LINESTRING(78.3750 17.4500, 78.3850 17.4450, 78.3950 17.4400)",
        "speed_limit_kmh": 60,
        "direction": "both",
    },
    {
        "city": "Hyderabad",
        "external_id": "HYD-RD-02",
        "name": "Gachibowli - Financial District ORR",
        "wkt": "LINESTRING(78.3450 17.4400, 78.3550 17.4300, 78.3650 17.4200)",
        "speed_limit_kmh": 90,
        "direction": "both",
    },

    # CHENNAI
    {
        "city": "Chennai",
        "external_id": "MAA-RD-01",
        "name": "Anna Salai (Mount Road) Corridor",
        "wkt": "LINESTRING(80.2500 13.0600, 80.2400 13.0450, 80.2300 13.0300)",
        "speed_limit_kmh": 50,
        "direction": "both",
    },
    {
        "city": "Chennai",
        "external_id": "MAA-RD-02",
        "name": "Old Mahabalipuram Road (OMR IT Expressway)",
        "wkt": "LINESTRING(80.2450 12.9800, 80.2400 12.9500, 80.2350 12.9200)",
        "speed_limit_kmh": 70,
        "direction": "both",
    },

    # KOLKATA
    {
        "city": "Kolkata",
        "external_id": "CCU-RD-01",
        "name": "Eastern Metropolitan (EM) Bypass",
        "wkt": "LINESTRING(88.3950 22.5400, 88.4000 22.5600, 88.4050 22.5800)",
        "speed_limit_kmh": 60,
        "direction": "both",
    },
    {
        "city": "Kolkata",
        "external_id": "CCU-RD-02",
        "name": "Park Street - Howrah Bridge Approach",
        "wkt": "LINESTRING(88.3500 22.5550, 88.3450 22.5700, 88.3400 22.5850)",
        "speed_limit_kmh": 45,
        "direction": "both",
    },
]

CAMERAS_DATA = [
    # BENGALURU
    {"id": "BLR-CAM-01", "name": "BLR-01 (MG Road Trinity Circle)", "city": "Bengaluru", "road_ext": "BLR-RD-01", "lat": 12.9730, "lng": 77.6180, "dir": "W"},
    {"id": "BLR-CAM-02", "name": "BLR-02 (MG Road - Brigade Jct)", "city": "Bengaluru", "road_ext": "BLR-RD-01", "lat": 12.9745, "lng": 77.6070, "dir": "W"},
    {"id": "BLR-CAM-03", "name": "BLR-03 (Silk Board Junction South)", "city": "Bengaluru", "road_ext": "BLR-RD-02", "lat": 12.9175, "lng": 77.6235, "dir": "S"},
    {"id": "BLR-CAM-04", "name": "BLR-04 (Hebbal Flyover Ring Road)", "city": "Bengaluru", "road_ext": "BLR-RD-03", "lat": 13.0355, "lng": 77.5970, "dir": "E"},

    # DELHI NCR
    {"id": "DEL-CAM-01", "name": "DEL-01 (AIIMS Ring Road Flyover)", "city": "Delhi NCR", "road_ext": "DEL-RD-01", "lat": 28.5675, "lng": 77.2105, "dir": "E"},
    {"id": "DEL-CAM-02", "name": "DEL-02 (DND Flyway Toll Plaza)", "city": "Delhi NCR", "road_ext": "DEL-RD-02", "lat": 28.5770, "lng": 77.2850, "dir": "E"},
    {"id": "DEL-CAM-03", "name": "DEL-03 (Gurgaon Cyber City Rapid)", "city": "Delhi NCR", "road_ext": "DEL-RD-03", "lat": 28.4910, "lng": 77.0870, "dir": "S"},

    # MUMBAI
    {"id": "BOM-CAM-01", "name": "BOM-01 (WEH Bandra Kalanagar Jct)", "city": "Mumbai", "road_ext": "BOM-RD-01", "lat": 19.0610, "lng": 72.8420, "dir": "N"},
    {"id": "BOM-CAM-02", "name": "BOM-02 (Bandra-Worli Sea Link North)", "city": "Mumbai", "road_ext": "BOM-RD-02", "lat": 19.0480, "lng": 72.8280, "dir": "S"},
    {"id": "BOM-CAM-03", "name": "BOM-03 (Marine Drive Nariman Pt)", "city": "Mumbai", "road_ext": "BOM-RD-03", "lat": 18.9360, "lng": 72.8230, "dir": "N"},

    # HYDERABAD
    {"id": "HYD-CAM-01", "name": "HYD-01 (HITEC City Cyber Towers)", "city": "Hyderabad", "road_ext": "HYD-RD-01", "lat": 17.4505, "lng": 78.3760, "dir": "E"},
    {"id": "HYD-CAM-02", "name": "HYD-02 (Gachibowli ORR Junction)", "city": "Hyderabad", "road_ext": "HYD-RD-02", "lat": 17.4380, "lng": 78.3500, "dir": "W"},

    # CHENNAI
    {"id": "MAA-CAM-01", "name": "MAA-01 (Anna Salai Mount Road)", "city": "Chennai", "road_ext": "MAA-RD-01", "lat": 13.0580, "lng": 77.2480, "dir": "S"},
    {"id": "MAA-CAM-02", "name": "MAA-02 (OMR Tidel Park Jct)", "city": "Chennai", "road_ext": "MAA-RD-02", "lat": 12.9820, "lng": 80.2470, "dir": "S"},

    # KOLKATA
    {"id": "CCU-CAM-01", "name": "CCU-01 (EM Bypass Science City)", "city": "Kolkata", "road_ext": "CCU-RD-01", "lat": 22.5410, "lng": 88.3960, "dir": "N"},
    {"id": "CCU-CAM-02", "name": "CCU-02 (Howrah Bridge Kolkata Side)", "city": "Kolkata", "road_ext": "CCU-RD-02", "lat": 22.5840, "lng": 88.3460, "dir": "W"},
]

REAL_WATCHLIST = [
    {"plate": "KA01MJ4040", "reason": "Wanted: Stolen Vehicle FIR #2026/BLR/842", "priority": "critical", "notes": "White Toyota Fortuner - Last seen Silk Board"},
    {"plate": "DL03TH1234", "reason": "Security Alert: VIP Route Violation", "priority": "high", "notes": "Black Mahindra Scorpio - DND Flyway"},
    {"plate": "MH12DE5678", "reason": "Hit & Run Case Investigation (Mumbai Police)", "priority": "critical", "notes": "Commercial Multi-Axle Truck"},
    {"plate": "TS09UA4433", "reason": "Repeat Speed Violator (>130 km/h ORR)", "priority": "medium", "notes": "Yellow/Green Auto-Rickshaw / Cab"},
    {"plate": "TN09AB9999", "reason": "Expired Registration & Unpaid E-Challans", "priority": "low", "notes": "Red Yamaha Motorcycle - Anna Salai"},
    {"plate": "UP32AZ0001", "reason": "Suspicious Route Pattern (Multi-City Transit)", "priority": "high", "notes": "Silver Sedan - Delhi-Noida Belt"},
]


async def seed_pan_india():
    settings = get_settings()
    engine = create_async_engine(str(settings.DATABASE_URL), echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    now = datetime.now(timezone.utc)

    async with session_factory() as session:
        print("[*] Checking database tables...")
        
        # 1. Seed Roads
        road_map: dict[str, Road] = {}
        for r_data in ROADS_DATA:
            q = select(Road).where(Road.external_id == r_data["external_id"])
            existing = (await session.execute(q)).scalar_one_or_none()
            if not existing:
                road = Road(
                    external_id=r_data["external_id"],
                    name=r_data["name"],
                    speed_limit_kmh=r_data["speed_limit_kmh"],
                    direction=r_data["direction"],
                    geometry=WKTElement(r_data["wkt"], srid=4326),
                )
                session.add(road)
                await session.flush()
                road_map[r_data["external_id"]] = road
                print(f"  [ROAD] Created: {road.name}")
            else:
                road_map[r_data["external_id"]] = existing

        # 2. Seed Cameras
        camera_map: dict[str, Camera] = {}
        for c_data in CAMERAS_DATA:
            q = select(Camera).where(Camera.camera_id == c_data["id"])
            existing = (await session.execute(q)).scalar_one_or_none()
            assigned_road = road_map.get(c_data["road_ext"])
            point_wkt = f"POINT({c_data['lng']} {c_data['lat']})"
            
            if not existing:
                camera = Camera(
                    camera_id=c_data["id"],
                    name=c_data["name"],
                    road_id=assigned_road.id if assigned_road else None,
                    direction=c_data["dir"],
                    fov_degrees=90,
                    lane_count=3,
                    status="active",
                    location=WKTElement(point_wkt, srid=4326),
                    metadata_={"city": c_data["city"], "fps": 30, "resolution": "1080p"},
                )
                session.add(camera)
                await session.flush()
                camera_map[c_data["id"]] = camera
                print(f"  [CAMERA] Created: {camera.name} ({c_data['city']})")
            else:
                camera_map[c_data["id"]] = existing

        # 3. Seed Watchlist / Blacklist
        for wl in REAL_WATCHLIST:
            q = select(BlacklistEntry).where(BlacklistEntry.plate_text == wl["plate"])
            existing = (await session.execute(q)).scalar_one_or_none()
            if not existing:
                entry = BlacklistEntry(
                    plate_text=wl["plate"],
                    reason=wl["reason"],
                    priority=wl["priority"],
                    notes=wl["notes"],
                    is_active=True,
                )
                session.add(entry)
                print(f"  [WATCHLIST] Added Monitored Plate: {wl['plate']} ({wl['priority'].upper()})")

        # 4. Seed Real Vehicle Observations across Cities
        sample_observations = [
            # Bengaluru Silk Board
            {"cam": "BLR-CAM-03", "plate": "KA01MJ4040", "class": "car", "color": "white", "conf": 0.98, "time_offset": -30},
            {"cam": "BLR-CAM-03", "plate": "KA01E4521", "class": "auto_rickshaw", "color": "yellow_green", "conf": 0.96, "time_offset": -25},
            {"cam": "BLR-CAM-01", "plate": "KA05HR8899", "class": "motorcycle", "color": "black", "conf": 0.97, "time_offset": -15},
            {"cam": "BLR-CAM-04", "plate": "KA57F1200", "class": "bus", "color": "blue_white", "conf": 0.99, "time_offset": -10},

            # Delhi NCR Ring Road & DND
            {"cam": "DEL-CAM-01", "plate": "DL03TH1234", "class": "car", "color": "black", "conf": 0.99, "time_offset": -40},
            {"cam": "DEL-CAM-02", "plate": "DL01CZ3456", "class": "car", "color": "white", "conf": 0.97, "time_offset": -20},
            {"cam": "DEL-CAM-02", "plate": "UP32AZ0001", "class": "car", "color": "silver", "conf": 0.98, "time_offset": -12},
            {"cam": "DEL-CAM-03", "plate": "HR26DK9000", "class": "car", "color": "grey", "conf": 0.95, "time_offset": -8},

            # Mumbai WEH & Sea Link
            {"cam": "BOM-CAM-01", "plate": "MH12DE5678", "class": "truck", "color": "yellow", "conf": 0.97, "time_offset": -45},
            {"cam": "BOM-CAM-02", "plate": "MH01AE1111", "class": "car", "color": "red", "conf": 0.98, "time_offset": -18},
            {"cam": "BOM-CAM-03", "plate": "MH02CB4400", "class": "car", "color": "white", "conf": 0.96, "time_offset": -5},

            # Hyderabad HITEC City
            {"cam": "HYD-CAM-01", "plate": "TS09UA4433", "class": "auto_rickshaw", "color": "yellow_black", "conf": 0.95, "time_offset": -35},
            {"cam": "HYD-CAM-02", "plate": "TS07EK8811", "class": "motorcycle", "color": "red", "conf": 0.96, "time_offset": -14},

            # Chennai OMR
            {"cam": "MAA-CAM-02", "plate": "TN09AB9999", "class": "motorcycle", "color": "red", "conf": 0.97, "time_offset": -50},
            {"cam": "MAA-CAM-01", "plate": "TN01BC3344", "class": "bus", "color": "green_white", "conf": 0.99, "time_offset": -22},

            # Kolkata EM Bypass
            {"cam": "CCU-CAM-01", "plate": "WB02AK5555", "class": "car", "color": "yellow", "conf": 0.96, "time_offset": -60},
        ]

        for obs in sample_observations:
            cam = camera_map.get(obs["cam"])
            if not cam:
                continue
            obs_id = f"OBS-{obs['cam']}-{obs['plate']}"
            q = select(VehicleObservation).where(VehicleObservation.source_observation_id == obs_id)
            existing = (await session.execute(q)).scalar_one_or_none()
            if not existing:
                vo = VehicleObservation(
                    source="pan-india-cctv-v1",
                    source_observation_id=obs_id,
                    camera_id=cam.id,
                    observed_at=now + timedelta(minutes=obs["time_offset"]),
                    vehicle_class=obs["class"],
                    vehicle_color=obs["color"],
                    detection_confidence=obs["conf"],
                    plate_text=obs["plate"],
                    plate_confidence=obs["conf"],
                    status="associated",
                )
                session.add(vo)
                print(f"  [OBSERVATION] Recorded: {obs['plate']} ({obs['class'].upper()}) at {cam.name}")

        # 5. Seed Active Security Alerts
        alerts_data = [
            {
                "code": "ALT-BLR-001",
                "type": "BLACKLIST_MATCH",
                "severity": "critical",
                "title": "Stolen Vehicle Detected on Silk Board Corridor",
                "desc": "Monitored Vehicle KA01MJ4040 matched FIR #2026/BLR/842 at Silk Board Junction South.",
                "plate": "KA01MJ4040",
                "cam": "BLR-CAM-03",
            },
            {
                "code": "ALT-DEL-002",
                "type": "ROUTE_ANOMALY",
                "severity": "high",
                "title": "VIP Security Route Deviation (DND Flyway)",
                "desc": "Vehicle DL03TH1234 performed unapproved trajectory entry on DND Flyway Toll approach.",
                "plate": "DL03TH1234",
                "cam": "DEL-CAM-02",
            },
            {
                "code": "ALT-BOM-003",
                "type": "HIT_AND_RUN_SUSPECT",
                "severity": "critical",
                "title": "Hit & Run Heavy Commercial Truck Sighted",
                "desc": "Plate MH12DE5678 intercepted by ANPR at Bandra Kalanagar Junction heading North.",
                "plate": "MH12DE5678",
                "cam": "BOM-CAM-01",
            },
        ]

        for alt in alerts_data:
            q = select(Alert).where(Alert.alert_code == alt["code"])
            existing = (await session.execute(q)).scalar_one_or_none()
            cam = camera_map.get(alt["cam"])
            if not existing and cam:
                alert = Alert(
                    alert_code=alt["code"],
                    alert_type=alt["type"],
                    severity=alt["severity"],
                    title=alt["title"],
                    description=alt["desc"],
                    status="NEW",
                    camera_id=cam.id,
                    confidence=0.98,
                    evidence={"plate_match": alt["plate"], "camera": cam.name, "timestamp": now.isoformat()},
                )
                session.add(alert)
                print(f"  [ALERT] Created Incident: {alt['code']} -- {alt['title']}")

        await session.commit()
        print("\n[SUCCESS] Pan-India multi-city network seeded across 6 metros!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_pan_india())
