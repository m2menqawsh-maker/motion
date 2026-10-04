"""
ai/audio/benchmark/metrics.py
==============================
Evaluation metrics for Audio Intelligence & DSP (S27.16 / AI-13 Rule 29).
"""

from __future__ import annotations


def evaluate_clipping_detection(expected_clipping: bool, detected_clipping: bool) -> bool:
    return expected_clipping == detected_clipping


def evaluate_snr_band(snr_db: float, expected_band: str) -> bool:
    if expected_band == "high":
        return snr_db >= 20.0
    if expected_band == "medium":
        return 10.0 <= snr_db < 25.0
    if expected_band == "low":
        return snr_db < 15.0
    return False
