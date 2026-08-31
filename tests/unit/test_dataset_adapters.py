"""Unit tests for real-world Indian traffic dataset adapters and evaluation suite."""

from app.datasets import get_dataset_adapter, list_supported_datasets
from app.datasets.indian_plate_adapter import IndianPlateDatasetAdapter
from app.datasets.irdd_adapter import IRDDDatasetAdapter
from app.datasets.itd_adapter import ITDDatasetAdapter
from app.datasets.roundabout_adapter import RoundaboutHDDatasetAdapter
from app.datasets.uvh26_adapter import UVH26DatasetAdapter
from app.evaluation.real_dataset_eval import RealWorldDatasetEvaluator


def test_supported_datasets_list():
    datasets = list_supported_datasets()
    assert "uvh26" in datasets
    assert "itd" in datasets
    assert "indian_plate" in datasets
    assert "roundabouthd" in datasets
    assert "irdd" in datasets
    assert len(datasets) == 5


def test_uvh26_adapter_parsing():
    adapter = get_dataset_adapter("uvh26")
    assert isinstance(adapter, UVH26DatasetAdapter)

    sample_payload = {
        "camera_id": "11111111-1111-1111-1111-111111111101",
        "camera_name": "UVH26-TEST-CAM",
        "frames": [
            {
                "frame_id": "F01",
                "detections": [
                    {
                        "vehicle_id": "V-01",
                        "class": "auto_rickshaw",
                        "confidence": 0.95,
                        "bbox": [0.1, 0.2, 0.4, 0.6],
                        "license_plate": "KA01AB1234",
                    },
                    {
                        "vehicle_id": "V-02",
                        "class": "two_wheeler",
                        "confidence": 0.97,
                        "bbox": [0.5, 0.3, 0.7, 0.8],
                        "license_plate": "KA05CD5678",
                    },
                ],
            }
        ],
    }

    observations = adapter.load_from_file_or_dict(sample_payload)
    assert len(observations) == 2
    assert observations[0].vehicle_class == "auto_rickshaw"
    assert observations[1].vehicle_class == "motorcycle"
    assert observations[0].plate_text == "KA01AB1234"

    # Test conversion to API schema
    api_obs = observations[0].to_observation_create()
    assert api_obs.vehicle_class == "auto_rickshaw"
    assert api_obs.source == "dataset:uvh26"

    summary = adapter.get_summary(observations)
    assert summary.total_observations == 2
    assert summary.unique_vehicles == 2
    assert summary.has_license_plates is True


def test_itd_adapter_parsing():
    adapter = get_dataset_adapter("itd")
    assert isinstance(adapter, ITDDatasetAdapter)

    sample_payload = {
        "camera_id": "11111111-1111-1111-1111-111111111102",
        "sequences": [
            {
                "sequence_id": "SEQ-01",
                "weather": "rain",
                "vehicles": [
                    {
                        "vehicle_id": "ITD-01",
                        "class": "car",
                        "bounding_box": [0.2, 0.2, 0.6, 0.6],
                        "plate_text": "DL01AB9999",
                    }
                ],
            }
        ],
    }

    observations = adapter.load_from_file_or_dict(sample_payload)
    assert len(observations) == 1
    assert observations[0].vehicle_class == "car"
    assert observations[0].metadata.get("weather") == "rain"


def test_indian_plate_adapter_parsing():
    adapter = get_dataset_adapter("indian_plate")
    assert isinstance(adapter, IndianPlateDatasetAdapter)

    sample_payload = {
        "samples": [
            {
                "plate_number": "KA01AB1234",
                "is_hsrp": True,
                "layout": "single_line",
                "vehicle_class": "car",
                "noisy_ocr_variant": "KA01AB1234",
            },
            {
                "plate_number": "MH12DE5678",
                "is_hsrp": False,
                "layout": "double_line",
                "vehicle_class": "motorcycle",
                "noisy_ocr_variant": "MH12DE567B",
            },
        ]
    }

    observations = adapter.load_from_file_or_dict(sample_payload)
    assert len(observations) == 2
    assert observations[0].metadata.get("state_code") == "KA"
    assert observations[0].metadata.get("is_state_valid") is True
    assert observations[1].metadata.get("state_code") == "MH"


def test_roundabout_adapter_parsing():
    adapter = get_dataset_adapter("roundabouthd")
    assert isinstance(adapter, RoundaboutHDDatasetAdapter)

    sample_payload = {
        "cameras": [{"id": "11111111-1111-1111-1111-111111111101", "name": "CAM-ENTRY"}],
        "multi_camera_tracks": [
            {
                "global_vehicle_id": "GLOBAL-01",
                "license_plate": "KA01AB1234",
                "vehicle_class": "car",
                "camera_sightings": [
                    {
                        "camera_name": "CAM-ENTRY",
                        "local_track_id": "TRK-01",
                        "bounding_box": [0.1, 0.1, 0.4, 0.4],
                    }
                ],
            }
        ],
    }

    observations = adapter.load_from_file_or_dict(sample_payload)
    assert len(observations) == 1
    assert observations[0].true_vehicle_id == "GLOBAL-01"
    summary = adapter.get_summary(observations)
    assert summary.has_multi_camera_ids is True


def test_irdd_adapter_parsing():
    adapter = get_dataset_adapter("irdd")
    assert isinstance(adapter, IRDDDatasetAdapter)

    sample_payload = {
        "scenes": [
            {
                "scene_id": "SCN-01",
                "objects": [
                    {
                        "vehicle_id": "IRDD-01",
                        "category": "autorickshaw",
                        "box": [0.1, 0.1, 0.4, 0.5],
                    }
                ],
            }
        ]
    }

    observations = adapter.load_from_file_or_dict(sample_payload)
    assert len(observations) == 1
    assert observations[0].vehicle_class == "auto_rickshaw"


def test_real_world_evaluator():
    evaluator = RealWorldDatasetEvaluator()
    report = evaluator.run_full_real_evaluation()

    assert report.composite_indian_readiness_score > 0.85
    assert report.anpr_metrics.character_accuracy > 0.90
    assert report.anpr_metrics.state_code_accuracy > 0.90
    assert len(report.classification_breakdown) >= 5
    assert report.multicamera_metrics.association_precision > 0.95
    assert len(report.datasets_evaluated) == 5
