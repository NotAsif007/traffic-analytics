#!/usr/bin/env python3
"""
CLI Evaluation and Benchmarking Tool for PS 26127.

Usage:
    python tools/run_benchmark.py
    python tools/run_benchmark.py --json
"""

import argparse
import sys

from app.evaluation.runner import BenchmarkRunner


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run repeatable benchmark evaluation across all PS 26127 subsystems."
    )
    parser.add_argument(
        "--json", action="store_true", help="Output machine-readable JSON evaluation report"
    )
    args = parser.parse_args()

    runner = BenchmarkRunner()
    report = runner.run_benchmark()

    if args.json:
        print(report.model_dump_json(indent=2))
        return 0

    print("=" * 70)
    print(f"PS 26127 TRAFFIC INTELLIGENCE BENCHMARK REPORT: {report.benchmark_name}")
    print("=" * 70)
    print(f"Evaluation Timestamp: {report.evaluation_timestamp.isoformat()}")
    print(
        f"Dataset: {report.dataset_summary['total_cameras']} cameras, "
        f"{report.dataset_summary['total_vehicles']} vehicles, "
        f"{report.dataset_summary['total_observations']} observations, "
        f"{report.dataset_summary['total_anomalous_events']} anomalies"
    )
    print("-" * 70)
    print("1. ANPR LAYER:")
    print(f"   - Detection Precision:  {report.anpr.detection_precision:.2%}")
    print(f"   - Detection Recall:     {report.anpr.detection_recall:.2%}")
    print(f"   - Detection F1:         {report.anpr.detection_f1:.2%}")
    print(f"   - Exact Plate Accuracy: {report.anpr.exact_plate_accuracy:.2%}")
    print(f"   - Norm Plate Accuracy:  {report.anpr.normalized_plate_accuracy:.2%}")
    print(f"   - Character Accuracy:   {report.anpr.average_character_accuracy:.2%}")
    print(f"   - Mean OCR Confidence:  {report.anpr.mean_ocr_confidence:.2%}")
    print("-" * 70)
    print("2. TRACKING LAYER:")
    print(f"   - MOTA:                 {report.tracking.mota:.2%}")
    print(f"   - IDF1:                 {report.tracking.idf1:.2%}")
    print(f"   - ID Switches:          {report.tracking.id_switches}")
    print(f"   - Mostly Tracked:       {report.tracking.mostly_tracked_tracks}")
    print("-" * 70)
    print("3. CROSS-CAMERA ASSOCIATION LAYER:")
    print(f"   - Association Precision:{report.association.precision:.2%}")
    print(f"   - Association Recall:   {report.association.recall:.2%}")
    print(f"   - Association F1:       {report.association.f1_score:.2%}")
    print(f"   - Trajectory Complete:  {report.association.trajectory_completeness_rate:.2%}")
    print("-" * 70)
    print("4. ALERT & ANOMALY ENGINE:")
    print(f"   - Alert Precision:      {report.alerts.precision:.2%}")
    print(f"   - Alert Recall:         {report.alerts.recall:.2%}")
    print(f"   - Alert F1:             {report.alerts.f1_score:.2%}")
    print(f"   - False Positive Rate:  {report.alerts.false_positive_rate:.2%}")
    print("=" * 70)
    print(f"OVERALL SYSTEM COMPOSITE BENCHMARK SCORE: {report.overall_system_score:.2%}")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
