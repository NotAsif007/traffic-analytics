"""Datasets subsystem registry and exports."""

from __future__ import annotations

from app.datasets.base import BaseDatasetAdapter, DatasetSummary, ParsedDatasetObservation
from app.datasets.indian_plate_adapter import IndianPlateDatasetAdapter
from app.datasets.irdd_adapter import IRDDDatasetAdapter
from app.datasets.itd_adapter import ITDDatasetAdapter
from app.datasets.roundabout_adapter import RoundaboutHDDatasetAdapter
from app.datasets.uvh26_adapter import UVH26DatasetAdapter

ADAPTER_REGISTRY: dict[str, type[BaseDatasetAdapter]] = {
    "uvh26": UVH26DatasetAdapter,
    "itd": ITDDatasetAdapter,
    "indian_plate": IndianPlateDatasetAdapter,
    "roundabouthd": RoundaboutHDDatasetAdapter,
    "irdd": IRDDDatasetAdapter,
}


def get_dataset_adapter(code: str) -> BaseDatasetAdapter:
    """Retrieve an instantiated dataset adapter by code name."""
    adapter_cls = ADAPTER_REGISTRY.get(code.lower().strip())
    if not adapter_cls:
        raise ValueError(
            f"Unknown dataset code '{code}'. Available datasets: {list(ADAPTER_REGISTRY.keys())}"
        )
    return adapter_cls()


def list_supported_datasets() -> list[str]:
    """List all registered dataset codes."""
    return list(ADAPTER_REGISTRY.keys())


__all__ = [
    "ADAPTER_REGISTRY",
    "BaseDatasetAdapter",
    "DatasetSummary",
    "IndianPlateDatasetAdapter",
    "IRDDDatasetAdapter",
    "ITDDatasetAdapter",
    "ParsedDatasetObservation",
    "RoundaboutHDDatasetAdapter",
    "UVH26DatasetAdapter",
    "get_dataset_adapter",
    "list_supported_datasets",
]
