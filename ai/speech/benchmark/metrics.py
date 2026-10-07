"""
ai/speech/benchmark/metrics.py
==============================
Rigorous analytical evaluation metrics for Speech Intelligence (S27.14).

Supported Metrics:
1. Arabic & Multilingual Word Error Rate (WER) with documented normalization.
2. Temporal Alignment Error (Timestamp MAE in seconds).
3. Speaker Diarization Error Rate (DER / Speaker Error) with permutation-invariant assignment.
4. Language Detection Accuracy.
5. Latency per Audio Minute & Cost per Audio Minute.
"""

from __future__ import annotations

import itertools
import re
from typing import Dict, List, Optional, Sequence, Tuple


# =============================================================================
# 1. Text Normalization (Arabic + English)
# =============================================================================

# Arabic Diacritics (Tashkeel) Unicode Range
ARABIC_DIACRITICS = re.compile(r"[\u064B-\u0652\u0670\u0640]")

# Arabic Alef Variants
ALEF_VARIANTS = re.compile(r"[إأآٱ]")

# Punctuation (Arabic and Western)
PUNCTUATION_PATTERN = re.compile(r"[،؛؟!\?.,:;\-\"'\(\)\[\]\{\}\<\>/\\]")


def normalize_text_for_wer(text: str, is_arabic: bool = True) -> str:
    """
    Applies authoritative, deterministic text normalization for WER calculation.

    Normalization Pipeline:
    1. Unicode Diacritics Removal: strips all Arabic vowel marks (Fathah, Dammah, Kasrah, Sukun, Shaddah, etc.).
    2. Alef Normalization: unifies [إ, أ, آ, ٱ] to bare [ا].
    3. Ta Marbuta Normalization: [ة] converted to [ه] for phonetic consistency.
    4. Alef Maksura Normalization: [ى] converted to [ي].
    5. Tatweel Removal: strips kashida elongation character.
    6. Punctuation Stripping: removes all commas, periods, question marks, brackets.
    7. Case Folding: lowercases all Latin characters for code-switching/English words.
    8. Whitespace Normalization: collapses multiple spaces, tabs, and newlines into a single space.
    """
    if not text:
        return ""

    normalized = text

    # Step 1: Remove diacritics & tatweel
    normalized = ARABIC_DIACRITICS.sub("", normalized)

    # Step 2: Normalize Alef variants
    normalized = ALEF_VARIANTS.sub("ا", normalized)

    # Step 3: Normalize Ta Marbuta and Alef Maksura
    normalized = normalized.replace("ة", "ه").replace("ى", "ي")

    # Step 4: Strip punctuation
    normalized = PUNCTUATION_PATTERN.sub(" ", normalized)

    # Step 5: Lowercase Latin characters
    normalized = normalized.lower()

    # Step 6: Collapse whitespace
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return normalized


# =============================================================================
# 2. Word Error Rate (WER) Calculation
# =============================================================================

def calculate_levenshtein_distance(seq_a: Sequence[str], seq_b: Sequence[str]) -> Tuple[int, int, int]:
    """
    Computes Levenshtein edit distance between two sequences of tokens.
    Returns (substitutions: int, deletions: int, insertions: int).
    """
    len_a = len(seq_a)
    len_b = len(seq_b)

    # Dynamic programming table for edit operations: (cost, S, D, I)
    dp = [[(0, 0, 0, 0) for _ in range(len_b + 1)] for _ in range(len_a + 1)]

    for i in range(1, len_a + 1):
        dp[i][0] = (i, 0, i, 0)  # i deletions

    for j in range(1, len_b + 1):
        dp[0][j] = (j, 0, 0, j)  # j insertions

    for i in range(1, len_a + 1):
        for j in range(1, len_b + 1):
            if seq_a[i - 1] == seq_b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                cost_sub, s, d, ins = dp[i - 1][j - 1]
                cost_del, s_d, d_d, ins_d = dp[i - 1][j]
                cost_ins, s_i, d_i, ins_i = dp[i][j - 1]

                choice_sub = (cost_sub + 1, s + 1, d, ins)
                choice_del = (cost_del + 1, s_d, d_d + 1, ins_d)
                choice_ins = (cost_ins + 1, s_i, d_i, ins_i + 1)

                best = min(choice_sub, choice_del, choice_ins, key=lambda x: x[0])
                dp[i][j] = best

    _, s, d, ins = dp[len_a][len_b]
    return s, d, ins


def calculate_wer(reference_text: str, hypothesis_text: str, is_arabic: bool = True) -> float:
    """
    Computes normalized Word Error Rate (WER).
    WER = (S + D + I) / N, where N is the number of words in the normalized reference.
    Returns float in range [0.0, +inf).
    """
    norm_ref = normalize_text_for_wer(reference_text, is_arabic=is_arabic)
    norm_hyp = normalize_text_for_wer(hypothesis_text, is_arabic=is_arabic)

    ref_words = norm_ref.split() if norm_ref else []
    hyp_words = norm_hyp.split() if norm_hyp else []

    if not ref_words:
        return 0.0 if not hyp_words else 1.0

    s, d, ins = calculate_levenshtein_distance(ref_words, hyp_words)
    total_errors = s + d + ins
    wer = total_errors / float(len(ref_words))
    return round(wer, 4)


def calculate_cer(
    reference_text: str,
    hypothesis_text: str,
    is_arabic: bool = True,
    ignore_whitespace: bool = False,
) -> float:
    """
    Computes normalized Character Error Rate (CER).
    CER = (S + D + I) / N, where N is the number of characters in the normalized reference.
    Returns float in range [0.0, +inf).
    """
    norm_ref = normalize_text_for_wer(reference_text, is_arabic=is_arabic)
    norm_hyp = normalize_text_for_wer(hypothesis_text, is_arabic=is_arabic)

    if ignore_whitespace:
        norm_ref = norm_ref.replace(" ", "")
        norm_hyp = norm_hyp.replace(" ", "")

    if not norm_ref:
        return 0.0 if not norm_hyp else 1.0

    s, d, ins = calculate_levenshtein_distance(list(norm_ref), list(norm_hyp))
    total_errors = s + d + ins
    cer = total_errors / float(len(norm_ref))
    return round(cer, 4)


# =============================================================================
# 3. Temporal Alignment Error (Timestamp MAE)
# =============================================================================

def calculate_timestamp_error(
    reference_intervals: List[Tuple[float, float]],
    hypothesis_intervals: List[Tuple[float, float]],
) -> float:
    """
    Computes Mean Absolute Error (MAE) in seconds between reference and predicted timestamps.
    Compares start and end boundaries for matching sequential intervals.
    """
    if not reference_intervals or not hypothesis_intervals:
        return 0.0

    n = min(len(reference_intervals), len(hypothesis_intervals))
    total_error = 0.0

    for i in range(n):
        ref_start, ref_end = reference_intervals[i]
        hyp_start, hyp_end = hypothesis_intervals[i]

        err_start = abs(hyp_start - ref_start)
        err_end = abs(hyp_end - ref_end)
        total_error += (err_start + err_end) / 2.0

    # Penalize length mismatch
    mismatch_penalty = abs(len(reference_intervals) - len(hypothesis_intervals)) * 0.5
    total_error += mismatch_penalty

    mae = total_error / float(n)
    return round(mae, 4)


# =============================================================================
# 4. Diarization Error Rate (Permutation-Invariant)
# =============================================================================

def calculate_diarization_error(
    reference_turns: List[Tuple[float, float, str]],
    hypothesis_turns: List[Tuple[float, float, str]],
) -> float:
    """
    Computes Diarization Error Rate (DER) using permutation-invariant speaker assignment.
    Hypothesis speaker tags (e.g. SPEAKER_00, SPEAKER_01) may be arbitrary;
    this finds the bijection that minimizes total mismatched speech time.
    """
    if not reference_turns:
        return 0.0 if not hypothesis_turns else 1.0

    ref_speakers = sorted(list({spk for _, _, spk in reference_turns}))
    hyp_speakers = sorted(list({spk for _, _, spk in hypothesis_turns}))

    if not hyp_speakers:
        return 1.0  # Missed all speakers

    total_ref_duration = sum(max(0.0, end - start) for start, end, _ in reference_turns)
    if total_ref_duration <= 0.0:
        return 0.0

    # Calculate temporal overlap matrix between ref_speakers and hyp_speakers
    overlap: Dict[Tuple[str, str], float] = {}
    for r_start, r_end, r_spk in reference_turns:
        for h_start, h_end, h_spk in hypothesis_turns:
            inter_start = max(r_start, h_start)
            inter_end = min(r_end, h_end)
            if inter_end > inter_start:
                key = (r_spk, h_spk)
                overlap[key] = overlap.get(key, 0.0) + (inter_end - inter_start)

    # Find optimal 1-to-1 speaker mapping maximizing overlap
    best_overlap = 0.0
    k = max(len(ref_speakers), len(hyp_speakers))
    # Pad hypothesis speakers with dummy labels if needed
    padded_hyp = hyp_speakers + [f"__dummy_{i}__" for i in range(k - len(hyp_speakers))]

    for perm in itertools.permutations(padded_hyp, len(ref_speakers)):
        curr_overlap = sum(overlap.get((ref_spk, hyp_spk), 0.0) for ref_spk, hyp_spk in zip(ref_speakers, perm))
        if curr_overlap > best_overlap:
            best_overlap = curr_overlap

    # DER = (Total Ref Time - Matched Overlap Time) / Total Ref Time
    error_time = max(0.0, total_ref_duration - best_overlap)
    der = error_time / total_ref_duration
    return round(der, 4)


# =============================================================================
# 5. Language Detection Accuracy
# =============================================================================

def calculate_language_accuracy(reference_language: str, predicted_language: Optional[str]) -> float:
    """Returns 1.0 if predicted primary language matches reference, else 0.0."""
    if not predicted_language:
        return 0.0
    ref_norm = reference_language.strip().lower()
    pred_norm = predicted_language.strip().lower()

    # Exact or prefix match (e.g. 'ar' matches 'ar-eg' or 'ar-xa')
    if pred_norm == ref_norm or pred_norm.startswith(f"{ref_norm}-") or ref_norm.startswith(f"{pred_norm}-"):
        return 1.0
    return 0.0
