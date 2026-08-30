#!/usr/bin/env python3
"""
Traffic Analytics — Real Indian Traffic Dataset Importer & Streamer.

Usage:
    python tools/import_real_dataset.py --dataset uvh26
    python tools/import_real_dataset.py --dataset indian_plate
    python tools/import_real_dataset.py --dataset roundabouthd
    python tools/import_real_dataset.py --dataset all
    python tools/import_real_dataset.py --dataset all --inject-to-api --api-url http://localhost:8000
"""

import argparse
import json
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.datasets import get_dataset_adapter, list_supported_datasets
from app.datasets.base import ParsedDatasetObservation

GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


DATASET_FILES = {
    "uvh26": "uvh26_sample.json",
    "indian_plate": "indian_plates_sample.json",
    "roundabouthd": "roundabout_sample.json",
    "itd": "itd_sample.json",
    "irdd": "irdd_sample.json",
}


def load_dataset(dataset_code: str, samples_dir: str) -> list[ParsedDatasetObservation]:
    adapter = get_dataset_adapter(dataset_code)
    filename = DATASET_FILES.get(dataset_code)
    if not filename:
        print(f"{YELLOW}No sample file mapped for '{dataset_code}'{RESET}")
        return []

    filepath = os.path.join(samples_dir, filename)
    if not os.path.exists(filepath):
        print(f"{YELLOW}Sample file not found at: {filepath}{RESET}")
        return []

    with open(filepath, encoding="utf-8") as f:
        raw = json.load(f)

    observations = adapter.load_from_file_or_dict(raw)
    summary = adapter.get_summary(observations)

    print(f"\n{BOLD}{CYAN}---------------------------------------------------------------{RESET}")
    print(f"{BOLD}{CYAN}  DATASET: {summary.dataset_name} [{summary.dataset_code.upper()}]{RESET}")
    print(f"{BOLD}{CYAN}---------------------------------------------------------------{RESET}")
    print(f"  * Description:         {summary.description}")
    print(f"  * Total Observations:  {GREEN}{summary.total_observations}{RESET}")
    print(f"  * Unique Vehicles:     {GREEN}{summary.unique_vehicles}{RESET}")
    print(f"  * Supported Classes:   {', '.join(summary.supported_classes)}")
    print(f"  * License Plates:      {'YES' if summary.has_license_plates else 'NO'}")
    print(f"  * Multi-Camera IDs:    {'YES' if summary.has_multi_camera_ids else 'NO'}\n")

    print(f"{BOLD}Sample Parsed Sightings:{RESET}")
    for idx, obs in enumerate(observations[:4]):
        plate_str = f"Plate: {obs.plate_text}" if obs.plate_text else "Plate: [Unreadable/None]"
        print(
            f"  [{idx+1}] Cam: {obs.camera_name} | Class: {obs.vehicle_class.upper():<12} | {plate_str:<20} | Conf: {obs.detection_confidence*100:.1f}%"
        )

    return observations


def inject_observations_to_api(observations: list[ParsedDatasetObservation], api_url: str):
    import urllib.error
    import urllib.request
    import uuid

    # First fetch available active cameras from API
    cameras_url = f"{api_url.rstrip('/')}/api/v1/cameras/?page_size=20"
    target_camera_id = None
    try:
        req_c = urllib.request.Request(cameras_url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req_c, timeout=5) as r:
            c_data = json.loads(r.read().decode("utf-8"))
            items = c_data.get("items", [])
            if items:
                target_camera_id = items[0].get("id")
    except Exception:
        pass

    obs_payloads = []
    for idx, obs in enumerate(observations):
        d = obs.to_observation_create().model_dump(mode="json")
        if target_camera_id:
            d["camera_id"] = target_camera_id
        # Ensure unique source_observation_id for repeated runs
        d["source_observation_id"] = f"{obs.dataset_name.lower().replace(' ', '_')}-{uuid.uuid4().hex[:8]}-{idx}"
        obs_payloads.append(d)

    url = f"{api_url.rstrip('/')}/api/v1/observations/bulk"
    payload = {"observations": obs_payloads}
    data_bytes = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            print(
                f"\n{BOLD}{GREEN}[OK] Successfully Injected {len(observations)} observations into API!{RESET}"
            )
            print(
                f"  Response: Accepted={body.get('accepted_count', len(observations))}, Rejected={body.get('rejected_count', 0)}"
            )
    except urllib.error.URLError as e:
        print(f"\n{YELLOW}[WARN] Could not connect to API at {url} ({e}){RESET}")
        print("  Ensure backend server is running with: uvicorn app.main:app --port 8000")


def main():
    parser = argparse.ArgumentParser(
        description="Real Indian Traffic Dataset Importer & Benchmark Loader"
    )
    parser.add_argument(
        "--dataset",
        choices=["all"] + list_supported_datasets(),
        default="all",
        help="Dataset to load and inspect (default: all)",
    )
    parser.add_argument(
        "--samples-dir",
        default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "samples")),
        help="Directory containing dataset sample files",
    )
    parser.add_argument(
        "--inject-to-api",
        action="store_true",
        help="Send parsed observations to the live backend API via /api/v1/observations/bulk",
    )
    parser.add_argument(
        "--api-url", default="http://localhost:8000", help="Base URL of the FastAPI backend"
    )

    args = parser.parse_args()

    print(f"\n{BOLD}{GREEN}==============================================================={RESET}")
    print(f"{BOLD}{GREEN}   REAL INDIAN TRAFFIC DATASETS LOADER & STREAMER (PS 26127)   {RESET}")
    print(f"{BOLD}{GREEN}==============================================================={RESET}")

    targets = list_supported_datasets() if args.dataset == "all" else [args.dataset]
    all_loaded: list[ParsedDatasetObservation] = []

    for code in targets:
        obs = load_dataset(code, args.samples_dir)
        all_loaded.extend(obs)

    print(
        f"\n{BOLD}Total Loaded Across Datasets:{RESET} {GREEN}{len(all_loaded)} observations{RESET}"
    )

    if args.inject_to_api and all_loaded:
        inject_observations_to_api(all_loaded, args.api_url)


if __name__ == "__main__":
    main()
