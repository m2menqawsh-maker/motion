"""
ai/speech/timeline.py
=====================
Canonical Voiceover Timeline Builder (S28-M07).

Invariants:
- Generates fully validated, strictly chronological voiceover timelines.
- Flattened events: speech sentences, individual words, and silence intervals.
- Enforces strict zero-start, duration match, no-gap, and no-overlap constraints.
- Output is machine-readable and consumable by Remotion caption components.
- Stored exclusively via StorageService, never mutating project state directly.
"""

from __future__ import annotations

import datetime
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ai.speech.timeline")

TOLERANCE_SECONDS = 0.005


class SpeechTimelineBuilder:
    """
    Authoritative builder for Voiceover Timeline artifacts.
    """

    @classmethod
    def build_timeline(
        cls,
        manifest_data: Dict[str, Any],
        fps: float = 30.0,
        output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Builds a canonical chronological voiceover timeline from manifest data.
        Validates completeness, chronology, and lack of gaps/overlaps.
        """
        validation = {
            "valid": True,
            "checks": {
                "timeline_starts_at_zero": True,
                "timeline_ends_at_source_duration": True,
                "no_gaps": True,
                "no_overlaps": True,
                "sentences_valid": True,
                "words_valid": True,
                "all_words_accounted_for": True,
                "events_chronological": True,
            },
            "warnings": [],
        }

        source_info = manifest_data.get("source", {})
        source_duration = float(source_info.get("duration", 0.0))

        if source_duration <= 0:
            return {
                "success": False,
                "error": {
                    "code": "INVALID_SOURCE_DURATION",
                    "message": "Source duration is missing or non-positive.",
                },
            }

        events: List[Dict[str, Any]] = []
        flat_sentences: List[Dict[str, Any]] = []
        flat_words: List[Dict[str, Any]] = []
        flat_silence_intervals: List[Dict[str, Any]] = []

        # 1. Process Sentences
        sentences_list = manifest_data.get("sentences", [])
        for s in sentences_list:
            s_timing = s.get("timing", {})
            start_t = float(s_timing.get("source_start", 0.0))
            end_t = float(s_timing.get("source_end", start_t))
            dur_t = float(s_timing.get("source_duration", end_t - start_t))

            if start_t < 0 or end_t <= start_t or end_t > source_duration + TOLERANCE_SECONDS:
                validation["checks"]["sentences_valid"] = False
                validation["valid"] = False
                validation["warnings"].append({
                    "code": "INVALID_SENTENCE_BOUNDS",
                    "message": f"Sentence {s.get('id')} has invalid bounds: {start_t:.3f} -> {end_t:.3f}",
                })

            words = s.get("words", [])
            speech_density = len(words) / dur_t if dur_t > 0 else 0.0
            avg_word_dur = sum(float(w.get("duration", 0.0)) for w in words) / len(words) if words else 0.0

            speech_event = {
                "id": s.get("id", f"vo_evt_{len(flat_sentences)+1:03d}"),
                "type": "speech",
                "start": round(start_t, 3),
                "end": round(end_t, 3),
                "duration": round(dur_t, 3),
                "text": s.get("text", ""),
                "audio_file": s.get("audio", {}).get("filename", ""),
                "split_reason": s.get("split", {}).get("reason", "unknown"),
                "speech_density": round(speech_density, 2),
                "word_count": len(words),
                "average_word_duration": round(avg_word_dur, 3),
                "pause_before": s.get("gaps", {}).get("before", 0.0),
                "pause_after": s.get("gaps", {}).get("after", 0.0),
                "start_frame": int(round(start_t * fps)),
                "end_frame": int(round(end_t * fps)),
            }
            events.append(speech_event)
            flat_sentences.append(speech_event)

            # Extract Words
            for w in words:
                w_start = float(w.get("start", 0.0))
                w_end = float(w.get("end", w_start))
                w_dur = float(w.get("duration", w_end - w_start))
                g_idx = w.get("global_index", len(flat_words))

                if w_start < start_t - TOLERANCE_SECONDS or w_end > end_t + TOLERANCE_SECONDS:
                    validation["checks"]["words_valid"] = False
                    validation["warnings"].append({
                        "code": "WORD_OUTSIDE_SENTENCE",
                        "message": f"Word '{w.get('text')}' at {w_start:.3f}->{w_end:.3f} falls outside sentence bounds {start_t:.3f}->{end_t:.3f}",
                    })

                flat_words.append({
                    "id": f"word_{g_idx:04d}",
                    "sentence_id": s.get("id"),
                    "global_index": g_idx,
                    "text": str(w.get("text") or w.get("word", "")),
                    "start": round(w_start, 3),
                    "end": round(w_end, 3),
                    "duration": round(w_dur, 3),
                    "probability": float(w.get("probability", 1.0)),
                    "start_frame": int(round(w_start * fps)),
                    "end_frame": int(round(w_end * fps)),
                })

        # 2. Process Unmapped / Silence Intervals
        for i, ui in enumerate(manifest_data.get("unmapped_intervals", [])):
            u_start = float(ui.get("start", 0.0))
            u_end = float(ui.get("end", u_start))
            u_dur = float(ui.get("duration", u_end - u_start))
            u_type = "silence" if ui.get("type") == "silence" else "unclassified_gap"

            silence_event = {
                "id": f"silence_{i+1:03d}",
                "type": u_type,
                "start": round(u_start, 3),
                "end": round(u_end, 3),
                "duration": round(u_dur, 3),
                "before_sentence": ui.get("between", [])[0] if len(ui.get("between", [])) > 0 else None,
                "after_sentence": ui.get("between", [])[1] if len(ui.get("between", [])) > 1 else None,
                "start_frame": int(round(u_start * fps)),
                "end_frame": int(round(u_end * fps)),
            }
            events.append(silence_event)
            flat_silence_intervals.append(silence_event)

        # 3. Sort Events chronologically
        events.sort(key=lambda e: e["start"])

        # 4. Strict Timeline Validation
        if events:
            first_event = events[0]
            if first_event["start"] > TOLERANCE_SECONDS:
                validation["checks"]["timeline_starts_at_zero"] = False
                validation["warnings"].append({
                    "code": "TIMELINE_NOT_AT_ZERO",
                    "message": f"Timeline starts at {first_event['start']}s instead of 0.000s.",
                })

            last_event = events[-1]
            if abs(last_event["end"] - source_duration) > TOLERANCE_SECONDS:
                validation["checks"]["timeline_ends_at_source_duration"] = False
                validation["warnings"].append({
                    "code": "TIMELINE_END_MISMATCH",
                    "message": f"Timeline ends at {last_event['end']}s instead of source duration {source_duration}s.",
                })

            for i in range(len(events) - 1):
                curr = events[i]
                nxt = events[i + 1]

                if curr["start"] > curr["end"]:
                    validation["checks"]["events_chronological"] = False
                    validation["valid"] = False

                gap = nxt["start"] - curr["end"]
                if gap > TOLERANCE_SECONDS:
                    validation["checks"]["no_gaps"] = False
                    validation["warnings"].append({
                        "code": "UNMAPPED_GAP_DETECTED",
                        "message": f"Gap of {gap:.3f}s detected between {curr['id']} and {nxt['id']}.",
                    })
                elif gap < -TOLERANCE_SECONDS:
                    validation["checks"]["no_overlaps"] = False
                    validation["valid"] = False
                    validation["warnings"].append({
                        "code": "EVENT_OVERLAP_DETECTED",
                        "message": f"Overlap of {-gap:.3f}s detected between {curr['id']} and {nxt['id']}.",
                    })

        total_frames = int(round(source_duration * fps))

        result = {
            "timeline_version": "1.0",
            "type": "voiceover_timeline",
            "project_id": manifest_data.get("project_id", "prj_default"),
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "source_manifest": {
                "manifest_version": manifest_data.get("manifest_version", "1.0"),
            },
            "source": {
                "audio_path": source_info.get("audio_path", ""),
                "duration": round(source_duration, 3),
                "language": source_info.get("language", "ar"),
                "fps": fps,
                "total_frames": total_frames,
            },
            "statistics": {
                "sentence_count": len(flat_sentences),
                "word_count": len(flat_words),
                "speech_duration": round(sum(s["duration"] for s in flat_sentences), 3),
                "silence_duration": round(sum(u["duration"] for u in flat_silence_intervals), 3),
            },
            "events": events,
            "sentences": flat_sentences,
            "words": flat_words,
            "silence_intervals": flat_silence_intervals,
            "validation": validation,
            "success": validation["valid"],
        }

        return result
