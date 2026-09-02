import os
import json
import datetime
from typing import Dict, Any, List, Optional

def build_voiceover_timeline_logic(
    manifest_data: Dict[str, Any],
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    
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
            "events_chronological": True
        },
        "warnings": []
    }
    
    def add_warning(code: str, message: str):
        validation["warnings"].append({"code": code, "message": message})
        
    def fail_check(check: str, code: str, message: str):
        validation["checks"][check] = False
        validation["valid"] = False
        add_warning(code, message)
        
    # Validation constraints
    TOLERANCE = 0.005
    
    if not isinstance(manifest_data, dict) or "sentences" not in manifest_data:
        return {
            "success": False,
            "error": {
                "code": "INVALID_MANIFEST",
                "message": "Provided data is not a valid voiceover manifest."
            }
        }
        
    source_info = manifest_data.get("source", {})
    source_duration = source_info.get("duration", 0.0)
    
    if source_duration <= 0:
        return {
            "success": False,
            "error": {
                "code": "INVALID_SOURCE_DURATION",
                "message": "Source duration is missing or invalid."
            }
        }
    
    events = []
    flat_sentences = []
    flat_words = []
    flat_silence_intervals = []
    
    # 1. Process Sentences -> Speech Events
    for i, s in enumerate(manifest_data.get("sentences", [])):
        start_t = s["timing"]["source_start"]
        end_t = s["timing"]["source_end"]
        dur_t = s["timing"]["source_duration"]
        
        # Sentence vs Audio validation
        if start_t < 0 or end_t <= start_t or end_t > source_duration + TOLERANCE:
            fail_check("sentences_valid", "INVALID_SENTENCE", f"Sentence {s['id']} has invalid bounds: {start_t} -> {end_t}")
            
        speech_density = len(s.get("words", [])) / dur_t if dur_t > 0 else 0.0
        avg_word_dur = sum(w["duration"] for w in s.get("words", [])) / len(s.get("words", [])) if s.get("words", []) else 0.0
        
        speech_event = {
            "id": s["id"],
            "type": "speech",
            "start": start_t,
            "end": end_t,
            "duration": dur_t,
            "text": s.get("text", ""),
            "audio_file": s.get("audio", {}).get("filename", ""),
            "split_reason": s.get("split", {}).get("reason", "unknown"),
            "speech_density": speech_density,
            "word_count": len(s.get("words", [])),
            "average_word_duration": avg_word_dur,
            "pause_before": s.get("gaps", {}).get("before", 0.0),
            "pause_after": s.get("gaps", {}).get("after", 0.0)
        }
        events.append(speech_event)
        flat_sentences.append(speech_event)
        
        # Extract Words
        for w in s.get("words", []):
            w_start = w["start"]
            w_end = w["end"]
            
            if w_start < start_t - TOLERANCE or w_end > end_t + TOLERANCE:
                fail_check("words_valid", "WORD_OUTSIDE_SENTENCE", f"Word '{w.get('text')}' at {w_start}->{w_end} falls outside sentence {s['id']} bounds {start_t}->{end_t}")
                
            word_obj = {
                "id": f"word_{w['global_index']:04d}",
                "sentence_id": s["id"],
                "global_index": w["global_index"],
                "text": w["text"],
                "start": w_start,
                "end": w_end,
                "duration": w["duration"],
                "probability": w.get("probability", 1.0)
            }
            flat_words.append(word_obj)
            
    # Check for duplicate global indices
    word_indices = [w["global_index"] for w in flat_words]
    if len(word_indices) != len(set(word_indices)):
        fail_check("words_valid", "DUPLICATE_WORD", "Duplicate word global indices found.")
        
    expected_word_count = manifest_data.get("statistics", {}).get("word_count", len(flat_words))
    if len(flat_words) != expected_word_count:
        fail_check("all_words_accounted_for", "MISSING_WORD", f"Expected {expected_word_count} words but found {len(flat_words)}")
        
    # 2. Process Unmapped Intervals -> Silence/Gap Events
    for i, ui in enumerate(manifest_data.get("unmapped_intervals", [])):
        u_type = "silence" if ui.get("type") == "silence" else "unclassified_gap"
        
        silence_event = {
            "id": f"silence_{i+1:03d}",
            "type": u_type,
            "start": ui["start"],
            "end": ui["end"],
            "duration": ui["duration"],
            "before_sentence": ui.get("between", [])[0] if len(ui.get("between", [])) > 0 else None,
            "after_sentence": ui.get("between", [])[1] if len(ui.get("between", [])) > 1 else None
        }
        events.append(silence_event)
        flat_silence_intervals.append(silence_event)
        
    # 3. Sort Events chronologically
    events.sort(key=lambda e: e["start"])
    
    # 4. Strict Timeline Validation (Gap & Overlap)
    if events:
        first_event = events[0]
        if first_event["start"] > TOLERANCE:
            fail_check("timeline_starts_at_zero", "TIMELINE_GAP", f"Timeline starts at {first_event['start']} instead of 0.000")
            
        last_event = events[-1]
        if abs(last_event["end"] - source_duration) > TOLERANCE:
            fail_check("timeline_ends_at_source_duration", "TIMELINE_GAP", f"Timeline ends at {last_event['end']} instead of {source_duration}")
            
        for i in range(len(events) - 1):
            curr = events[i]
            nxt = events[i+1]
            
            if curr["start"] > curr["end"]:
                fail_check("events_chronological", "INVALID_EVENT", f"Event {curr['id']} has start > end")
                
            gap = nxt["start"] - curr["end"]
            
            if gap > TOLERANCE:
                # Actual unmapped gap discovered (CRITICAL DO NOT INVENT SILENCE RULE)
                fail_check("no_gaps", "TIMELINE_GAP", f"Unmapped gap of {gap:.3f}s detected between {curr['id']} and {nxt['id']}")
            elif gap < -TOLERANCE:
                fail_check("no_overlaps", "TIMELINE_OVERLAP", f"Overlap of {-gap:.3f}s detected between {curr['id']} and {nxt['id']}")
                
    # Compile stats
    stats = {
        "sentence_count": len(flat_sentences),
        "word_count": len(flat_words),
        "speech_duration": sum(s["duration"] for s in flat_sentences),
        "silence_duration": sum(u["duration"] for u in flat_silence_intervals)
    }
    
    # Assembly
    timeline = {
        "timeline_version": "1.0",
        "type": "voiceover_timeline",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        
        "source_manifest": {
            "manifest_version": manifest_data.get("manifest_version", "1.0")
        },
        
        "source": {
            "audio_path": source_info.get("audio_path", ""),
            "duration": source_duration,
            "language": source_info.get("language", "en")
        },
        
        "statistics": stats,
        
        "events": events,
        "sentences": flat_sentences,
        "words": flat_words,
        "silence_intervals": flat_silence_intervals,
        
        "validation": validation
    }
    
    if not validation["valid"]:
        timeline["success"] = False
        timeline["error"] = {
            "code": "VALIDATION_FAILED",
            "message": "One or more timeline validation checks failed."
        }
    else:
        timeline["success"] = True
        
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(timeline, f, ensure_ascii=False, indent=2)
            
    return timeline
