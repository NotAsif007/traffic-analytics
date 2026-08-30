#!/usr/bin/env python3
"""
CityTrack AI (PS 26127) — Real-Time Traffic & ANPR Telemetry Console Monitor.

Streams live vehicle observations, ANPR plate recognitions, cross-camera associations,
trajectories, and security alerts directly to your terminal.

Usage:
    python tools/monitor_realtime.py
    python tools/monitor_realtime.py --api-url http://localhost:8000
    python tools/monitor_realtime.py --simulate --interval 1.5
    python tools/monitor_realtime.py --filter-plate KA
    python tools/monitor_realtime.py --filter-class auto_rickshaw
"""

from __future__ import annotations

import argparse
import datetime
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

# Terminal ANSI Color Codes
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# Colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"

# Backgrounds
BG_RED = "\033[41m\033[97m"
BG_YELLOW = "\033[43m\033[30m"
BG_BLUE = "\033[44m\033[97m"
BG_PURPLE = "\033[45m\033[97m"
BG_CYAN = "\033[46m\033[30m"

CLASS_BADGES = {
    "car": f"{CYAN}[🚗 CAR]{RESET}",
    "auto_rickshaw": f"{YELLOW}[🛺 AUTO-RICKSHAW]{RESET}",
    "motorcycle": f"{GREEN}[🏍️ MOTORCYCLE]{RESET}",
    "bus": f"{MAGENTA}[🚌 BUS]{RESET}",
    "truck": f"{BLUE}[🚛 TRUCK]{RESET}",
    "van": f"{WHITE}[🚐 VAN]{RESET}",
}


def print_banner(api_url: str, simulate: bool):
    print(f"\n{BOLD}{CYAN}╔══════════════════════════════════════════════════════════════════════════════╗{RESET}")
    print(f"{BOLD}{CYAN}║     CITYTRACK AI (PS 26127) — REAL-TIME TRAFFIC & ANPR TELEMETRY MONITOR     ║{RESET}")
    print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════════════════════════╝{RESET}")
    print(f"  {BOLD}Server API:{RESET}    {GREEN}{api_url}{RESET}")
    print(f"  {BOLD}Stream Mode:{RESET}   {YELLOW}{'Active Live Simulator + SSE Stream' if simulate else 'Live Server Stream'}{RESET}")
    print(f"  {BOLD}Status:{RESET}        {GREEN}LISTENING FOR REAL-TIME TELEMETRY PACKETS{RESET}")
    print(f"  {DIM}Press Ctrl+C at any time to exit.{RESET}\n")
    print(f"{BOLD}{'TIME (UTC)':<12} | {'EVENT TYPE':<18} | {'CAMERA / CORRIDOR':<22} | {'VEHICLE / PLATE':<26} | {'DETAILS'}{RESET}")
    print(f"{DIM}{'─' * 110}{RESET}")


def format_plate(plate_text: str | None, conf: float | None) -> str:
    if not plate_text:
        return f"{DIM}[No Plate Detected]{RESET}"
    state = plate_text[:2] if len(plate_text) >= 2 else "IN"
    conf_str = f"({conf*100:.1f}%)" if conf else ""
    return f"{BOLD}{YELLOW}[{state} {plate_text[2:]}]{RESET} {DIM}{conf_str}{RESET}"


def format_speed(speed: float | None) -> str:
    if speed is None:
        return f"{DIM}-- km/h{RESET}"
    if speed > 80:
        return f"{RED}{BOLD}{speed:.1f} km/h ⚠️{RESET}"
    elif speed > 50:
        return f"{YELLOW}{speed:.1f} km/h{RESET}"
    return f"{GREEN}{speed:.1f} km/h{RESET}"


def print_event(ev: dict, filter_plate: str | None = None, filter_class: str | None = None):
    ev_type = ev.get("event_type", "UNKNOWN")
    payload = ev.get("payload", {})
    ts_str = ev.get("timestamp", datetime.datetime.utcnow().isoformat())
    time_part = ts_str.split("T")[-1][:8] if "T" in ts_str else ts_str[:8]

    if ev_type == "CONNECTED":
        msg = payload.get("message", "Connected")
        print(f"{DIM}{time_part:<12}{RESET} | {GREEN}{'SYSTEM_READY':<18}{RESET} | {DIM}{'Central Telemetry':<22}{RESET} | {GREEN}{msg}{RESET}")
        return

    if ev_type == "VEHICLE_OBSERVED":
        plate = payload.get("plate_text")
        v_class = payload.get("vehicle_class") or "car"

        # Filtering
        if filter_plate and (not plate or filter_plate.lower() not in plate.lower()):
            return
        if filter_class and filter_class.lower() not in v_class.lower():
            return

        cam_id = str(payload.get("camera_id", "cam-feed"))[:8]
        conf = payload.get("plate_confidence") or payload.get("detection_confidence")
        speed = payload.get("estimated_speed_kmh")
        color = payload.get("vehicle_color") or ""
        badge = CLASS_BADGES.get(v_class.lower(), f"[{v_class.upper()}]")

        plate_badge = format_plate(plate, conf)
        speed_badge = format_speed(speed)

        details = f"{badge} {color} | Speed: {speed_badge}"
        print(f"{WHITE}{time_part:<12}{RESET} | {CYAN}{'VEHICLE_SIGHTING':<18}{RESET} | {WHITE}{cam_id:<22}{RESET} | {plate_badge:<36} | {details}")

    elif ev_type == "ALERT_CREATED":
        alert_code = payload.get("alert_code", "ALT")
        a_type = payload.get("type", "SECURITY_ALERT")
        title = payload.get("title") or f"{a_type} detected"
        print(f"{RED}{BOLD}{time_part:<12}{RESET} | {BG_RED}{' 🚨 ' + a_type[:14] + ' ':^18}{RESET} | {RED}{alert_code:<22}{RESET} | {YELLOW}{BOLD}{title}{RESET}")

    elif ev_type == "VEHICLE_MATCHED":
        score = payload.get("match_score", 0.95)
        reason = payload.get("reasoning", "Cross-camera re-ID match")
        print(f"{MAGENTA}{time_part:<12}{RESET} | {BG_PURPLE}{' 🔗 CROSS-CAMERA ':<18}{RESET} | {MAGENTA}{'Re-ID Match':<22}{RESET} | {GREEN}Score: {score*100:.1f}%{RESET} | {DIM}{reason[:40]}{RESET}")

    elif ev_type == "TRAJECTORY_UPDATED":
        traj_code = payload.get("trajectory_id", "TRJ")[:12]
        pts = payload.get("points_count", 2)
        print(f"{BLUE}{time_part:<12}{RESET} | {BLUE}{'TRAJECTORY_HOP':<18}{RESET} | {BLUE}{traj_code:<22}{RESET} | {CYAN}{pts} Cameras Visited{RESET} | {DIM}Route Progressing{RESET}")


def run_simulator_loop(api_url: str, interval: float, stop_event: threading.Event):
    tick_url = f"{api_url.rstrip('/')}/api/v1/events/simulate-tick?count=1"
    while not stop_event.is_set():
        try:
            req = urllib.request.Request(
                tick_url,
                data=b"",
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                resp.read()
        except Exception:
            pass
        time.sleep(interval)


def poll_recent_fallback(api_url: str, filter_plate: str | None, filter_class: str | None, stop_event: threading.Event):
    seen_ids = set()
    url = f"{api_url.rstrip('/')}/api/v1/events/recent?limit=20"
    while not stop_event.is_set():
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                events = json.loads(resp.read().decode("utf-8"))
                for ev in events:
                    eid = ev.get("event_id")
                    if eid and eid not in seen_ids:
                        seen_ids.add(eid)
                        print_event(ev, filter_plate, filter_class)
        except Exception:
            pass
        time.sleep(1.0)


def stream_sse(api_url: str, filter_plate: str | None, filter_class: str | None, stop_event: threading.Event):
    stream_url = f"{api_url.rstrip('/')}/api/v1/events/stream"
    req = urllib.request.Request(
        stream_url,
        headers={"Accept": "text/event-stream", "Cache-Control": "no-cache"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            for line in resp:
                if stop_event.is_set():
                    break
                line_str = line.decode("utf-8").strip()
                if line_str.startswith("data: "):
                    raw_data = line_str[6:]
                    try:
                        ev = json.loads(raw_data)
                        print_event(ev, filter_plate, filter_class)
                    except json.JSONDecodeError:
                        pass
    except Exception as e:
        print(f"{YELLOW}[Stream disconnected, switching to continuous polling: {e}]{RESET}")
        poll_recent_fallback(api_url, filter_plate, filter_class, stop_event)


def main():
    parser = argparse.ArgumentParser(
        description="CityTrack AI — Real-Time Traffic & ANPR Telemetry Console Monitor"
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000",
        help="Backend API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Enable background live CCTV traffic simulation",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.5,
        help="Simulation interval in seconds (default: 1.5s)",
    )
    parser.add_argument(
        "--filter-plate",
        default=None,
        help="Filter stream by partial plate string (e.g. KA, DL, MH)",
    )
    parser.add_argument(
        "--filter-class",
        default=None,
        help="Filter stream by vehicle class (e.g. auto_rickshaw, bus, car)",
    )

    args = parser.parse_args()
    print_banner(args.api_url, args.simulate)

    stop_event = threading.Event()
    sim_thread = None

    if args.simulate:
        sim_thread = threading.Thread(
            target=run_simulator_loop,
            args=(args.api_url, args.interval, stop_event),
            daemon=True,
        )
        sim_thread.start()

    try:
        stream_sse(args.api_url, args.filter_plate, args.filter_class, stop_event)
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Stopping telemetry monitor...{RESET}")
    finally:
        stop_event.set()
        if sim_thread and sim_thread.is_alive():
            sim_thread.join(timeout=1.0)
        print(f"{GREEN}Telemetry monitor exited cleanly.{RESET}\n")


if __name__ == "__main__":
    main()
