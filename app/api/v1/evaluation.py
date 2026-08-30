"""Evaluation and benchmarking API endpoints — /api/v1/evaluation."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.evaluation.contracts import EvaluationReport
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
