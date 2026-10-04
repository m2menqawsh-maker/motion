"""
ai/evals/deferred.py
====================
Authoritative Tracking for Deferred Real-Media Benchmarks (S27.20).

Invariants:
- Formally records deferred real-media quality benchmarks without fabricating scores.
- Status is strictly DEFERRED_FINAL_VALIDATION (never synthetic PASS).
- Tracks open production debt to be resolved in AI-15.
"""

from __future__ import annotations

from typing import Dict, List
from ai.contracts.evals import BenchmarkDebtContract


DEFERRED_BENCHMARKS: Dict[str, BenchmarkDebtContract] = {
    "BENCH_SPEECH_QUALITY": BenchmarkDebtContract(
        benchmark_id="BENCH_SPEECH_QUALITY",
        name="Speech Real Quality Benchmark",
        status="DEFERRED_FINAL_VALIDATION",
        target_stage="AI-15",
        fake_scores_injected=False,
        notes="Awaiting golden real Arabic/English multi-speaker acoustic recordings for Word Error Rate (WER) calibration.",
    ),
    "BENCH_VISION_QUALITY": BenchmarkDebtContract(
        benchmark_id="BENCH_VISION_QUALITY",
        name="Vision Real Quality Benchmark",
        status="DEFERRED_FINAL_VALIDATION",
        target_stage="AI-15",
        fake_scores_injected=False,
        notes="Awaiting high-motion 4K raw video sequences for temporal shot boundary and F1 segmentation score calibration.",
    ),
    "BENCH_AUDIO_AI": BenchmarkDebtContract(
        benchmark_id="BENCH_AUDIO_AI",
        name="Audio AI Transform Benchmark",
        status="DEFERRED_FINAL_VALIDATION",
        target_stage="AI-15",
        fake_scores_injected=False,
        notes="Awaiting multi-track studio audio stems for SNR and perceptual music beat evaluation calibration.",
    ),
}


def list_deferred_benchmarks() -> List[BenchmarkDebtContract]:
    """Returns the list of open deferred benchmark production gates."""
    return list(DEFERRED_BENCHMARKS.values())


def get_deferred_benchmark(benchmark_id: str) -> BenchmarkDebtContract:
    """Retrieves an individual deferred benchmark debt record."""
    if benchmark_id not in DEFERRED_BENCHMARKS:
        raise KeyError(f"Unknown benchmark identifier '{benchmark_id}'.")
    return DEFERRED_BENCHMARKS[benchmark_id]
