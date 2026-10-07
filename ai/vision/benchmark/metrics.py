"""
ai/vision/benchmark/metrics.py
==============================
Evaluation metrics for Vision Intelligence (S27.15 / AI-13 Rule 28).

Covers:
- Shot recall & precision
- OCR character/word accuracy
- Object / Person detection precision
- Important moment precision
- Latency & Cost per minute
"""

from __future__ import annotations

from typing import List, Tuple


def calculate_shot_recall_and_precision(
    predicted_cuts: List[float],
    ground_truth_cuts: List[float],
    tolerance_seconds: float = 0.5,
) -> Tuple[float, float, float]:
    """
    Evaluates shot boundary detection.
    Returns (recall, precision, f1_score).
    """
    if not ground_truth_cuts:
        return (1.0, 1.0, 1.0) if not predicted_cuts else (1.0, 0.0, 0.0)
    if not predicted_cuts:
        return (0.0, 1.0, 0.0)

    true_positives = 0
    matched_gt = set()

    for pred in predicted_cuts:
        for idx, gt in enumerate(ground_truth_cuts):
            if idx not in matched_gt and abs(pred - gt) <= tolerance_seconds:
                true_positives += 1
                matched_gt.add(idx)
                break

    recall = float(true_positives) / float(len(ground_truth_cuts))
    precision = float(true_positives) / float(len(predicted_cuts))
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    return (round(recall, 3), round(precision, 3), round(f1, 3))


def calculate_ocr_word_accuracy(
    predicted_words: List[str],
    ground_truth_words: List[str],
) -> float:
    """
    Evaluates OCR word-level recognition accuracy.
    """
    if not ground_truth_words:
        return 1.0 if not predicted_words else 0.0

    gt_set = set(w.strip().lower() for w in ground_truth_words)
    pred_set = set(w.strip().lower() for w in predicted_words)

    overlap = len(gt_set.intersection(pred_set))
    return round(float(overlap) / float(len(gt_set)), 3)
