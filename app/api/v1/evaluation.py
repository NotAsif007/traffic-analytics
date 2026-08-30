"""Evaluation and benchmarking API endpoints — /api/v1/evaluation."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.datasets import get_dataset_adapter, list_supported_datasets
from app.datasets.base import DatasetSummary
from app.evaluation.contracts import EvaluationReport
from app.evaluation.real_dataset_eval import RealDatasetEvaluationReport, RealWorldDatasetEvaluator
from app.evaluation.runner import BenchmarkRunner

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.get(
    "/benchmark",
    response_model=EvaluationReport,
    summary="Get machine-readable benchmark evaluation report across all PS 26127 subsystems",
)
async def get_benchmark_report() -> EvaluationReport:
    runner = BenchmarkRunner()
    return runner.run_benchmark()


@router.post(
    "/run",
    response_model=EvaluationReport,
    status_code=status.HTTP_200_OK,
    summary="Trigger full benchmark execution against synthetic city ground-truth dataset",
)
async def run_benchmark() -> EvaluationReport:
    runner = BenchmarkRunner()
    return runner.run_benchmark()


@router.get(
    "/real-datasets",
    response_model=list[DatasetSummary],
    summary="List available real Indian and multi-camera datasets (UVH-26, ITD, Indian LP, RoundaboutHD, IRDD)",
)
async def list_real_datasets() -> list[DatasetSummary]:
    summaries = []
    for code in list_supported_datasets():
        adapter = get_dataset_adapter(code)
        # Generate summary using empty or sample
        summary = adapter.get_summary([])
        summaries.append(summary)
    return summaries


@router.post(
    "/real-datasets/run",
    response_model=RealDatasetEvaluationReport,
    status_code=status.HTTP_200_OK,
    summary="Execute comprehensive evaluation benchmark on real Indian and multi-camera traffic datasets",
)
async def run_real_datasets_evaluation() -> RealDatasetEvaluationReport:
    evaluator = RealWorldDatasetEvaluator()
    return evaluator.run_full_real_evaluation()
