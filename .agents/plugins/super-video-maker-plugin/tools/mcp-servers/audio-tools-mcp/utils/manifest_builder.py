import os
import json
import datetime
from typing import Dict, Any, List, Optional

def build_voiceover_manifest_logic(
    audio_path: str,
    analysis_data: Dict[str, Any],
    split_data: Dict[str, Any],
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    
    # Validation object
    validation = {
        "valid": True,
        "warnings": [],
        "checks": {
            "sentences_valid": True,
            "words_valid": True,
            "no_overlap": True,
            "files_exist": True,
            "timeline_valid": True
        }
    }
    
    def add_error(code, msg):
        return {
            "success": False,
            "error": {
                "code": code,
                "message": msg
            }
        }
        
    def add_warning(code, msg):
        validation["warnings"].append({"code": code, "message": msg})
        
    # Check audio file
    if not os.path.exists(audio_path) or not os.path.isfile(audio_path) or not os.access(audio_path, os.R_OK):
        return add_error("AUDIO_FILE_ERROR", f"Audio file is missing, not a file, or unreadable: {audio_path}")
        
    # Flatten words from analysis
    all_source_words = []
    if "segments" in analysis_data:
        for seg in analysis_data["segments"]:
            if "words" in seg:
                all_source_words.extend(seg["words"])
    else:
        all_source_words = analysis_data.get("words", [])
        
    for i, w in enumerate(all_source_words):
        w["global_index"] = i
        
    source_duration = analysis_data.get("duration", 0.0)
    
    # Process Sentences
    split_sentences = split_data.get("sentences", [])
    manifest_sentences = []
    
    prev_end = 0.0
    mapped_word_indices = set()
    unmapped_intervals = []
    
    TOLERANCE = 0.005
    
    silence_periods = analysis_data.get("silence_periods", [])
    def is_silence(start, end):
        # A simple check: if the interval is mostly covered by a silence period
        midpoint = (start + end) / 2.0
        for sp in silence_periods:
            if sp["start"] <= midpoint <= sp["end"]:
                return True
        return False
    
    for i, sent in enumerate(split_sentences):
        s_start = sent["source_timing"]["start"]
        s_end = sent["source_timing"]["end"]
        
        # Check chronology and overlap
        if s_start < prev_end - TOLERANCE:
            validation["checks"]["no_overlap"] = False
            validation["valid"] = False
            add_warning("OVERLAP_DETECTED", f"Sentence {i+1} overlaps with previous. {s_start} < {prev_end}")
            
        if s_start < 0 or s_end > source_duration + TOLERANCE or s_start >= s_end:
            validation["checks"]["sentences_valid"] = False
            validation["valid"] = False
            
        # Unmapped interval before this sentence
        if s_start > prev_end + TOLERANCE:
            gap_dur = s_start - prev_end
            unmapped_intervals.append({
                "start": prev_end,
                "end": s_start,
                "duration": gap_dur,
                "type": "silence" if is_silence(prev_end, s_start) else "unclassified",
                "between": [f"vo_{i:03d}" if i > 0 else "start", f"vo_{i+1:03d}"]
            })
            gap_before = gap_dur
        else:
            gap_before = 0.0
            
        # File check
        out_path = sent["output_path"]
        if not os.path.exists(out_path) or not os.path.isfile(out_path) or not os.access(out_path, os.R_OK):
            validation["checks"]["files_exist"] = False
            validation["valid"] = False
            add_warning("FILE_MISSING", f"Sentence file is missing or unreadable: {out_path}")
            
        # Word mapping
        sentence_words = []
        s_words_data = sent.get("words", [])
        
        for w_idx, w in enumerate(s_words_data):
            # Find the word in source
            w_start = w["start"]
            w_end = w["end"]
            
            # Find matching global word
            match = next((sw for sw in all_source_words if abs(sw["start"] - w_start) <= TOLERANCE and abs(sw["end"] - w_end) <= TOLERANCE), None)
            
            if match:
                mapped_word_indices.add(match["global_index"])
                sentence_words.append({
                    "global_index": match["global_index"],
                    "sentence_word_index": w_idx,
                    "text": match.get("word", "").strip() or match.get("text", "").strip(),
                    "start": match["start"],
                    "end": match["end"],
                    "duration": match["end"] - match["start"],
                    "probability": match.get("probability", 1.0)
                })
            else:
                validation["checks"]["words_valid"] = False
                validation["valid"] = False
                add_warning("WORD_NOT_FOUND", f"Word '{w.get('word')}' at {w_start} not found in source analysis.")
                
        # Gap after calculation (if last sentence)
        gap_after = 0.0
        if i == len(split_sentences) - 1:
            if s_end < source_duration - TOLERANCE:
                gap_after = source_duration - s_end
                
        elif len(split_sentences) > i + 1:
            next_start = split_sentences[i+1]["source_timing"]["start"]
            if next_start > s_end + TOLERANCE:
                gap_after = next_start - s_end
                
        manifest_sentences.append({
            "id": f"vo_{i+1:03d}",
            "index": i + 1,
            "text": sent["text"],
            "timing": {
                "source_start": s_start,
                "source_end": s_end,
                "source_duration": sent["source_timing"]["duration"]
            },
            "audio": {
                "path": out_path,
                "filename": os.path.basename(out_path),
                "duration": sent["file_timing"]["duration"],
                "format": "wav"
            },
            "split": {
                "reason": sent["split_reason"],
                "pre_padding": sent["file_timing"].get("pre_padding_applied", 0.03),
                "post_padding": sent["file_timing"].get("post_padding_applied", 0.05)
            },
            "gaps": {
                "before": gap_before,
                "after": gap_after
            },
            "words": sentence_words
        })
        
        prev_end = s_end
        
    # Check end interval
    if prev_end < source_duration - TOLERANCE:
        gap_dur = source_duration - prev_end
        unmapped_intervals.append({
            "start": prev_end,
            "end": source_duration,
            "duration": gap_dur,
            "type": "silence" if is_silence(prev_end, source_duration) else "unclassified",
            "between": [f"vo_{len(split_sentences):03d}", "end"]
        })
        
    # Word coverage validation
    if len(mapped_word_indices) != len(all_source_words):
        validation["checks"]["words_valid"] = False
        validation["valid"] = False
        missing = len(all_source_words) - len(mapped_word_indices)
        add_warning("WORD_COVERAGE_MISMATCH", f"{missing} words from source are missing in sentences.")

    # Timeline coverage validation
    covered_duration = sum(s["timing"]["source_duration"] for s in manifest_sentences)
    unmapped_duration = sum(u["duration"] for u in unmapped_intervals)
    total_calculated = covered_duration + unmapped_duration
    if abs(total_calculated - source_duration) > max(TOLERANCE * (len(manifest_sentences) + 1), 0.05):
        validation["checks"]["timeline_valid"] = False
        validation["valid"] = False
        add_warning("TIMELINE_MISMATCH", f"Sentences + unmapped ({total_calculated}) != source duration ({source_duration}).")
        
    # Build final manifest
    manifest = {
        "manifest_version": "1.0",
        "manifest_type": "voiceover_manifest",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source": {
            "audio_path": audio_path,
            "filename": os.path.basename(audio_path),
            "duration": source_duration,
            "format": "wav",
            "sample_rate": analysis_data.get("sample_rate", None),
            "channels": analysis_data.get("channels", None),
            "language": analysis_data.get("language", None),
            "language_probability": analysis_data.get("language_probability", None)
        },
        "model": analysis_data.get("model", {
            "provider": "faster-whisper",
            "name": analysis_data.get("model_size", "small"),
            "device": analysis_data.get("model_device", "cpu"),
            "compute_type": analysis_data.get("compute_type", "int8")
        }),
        "statistics": {
            "sentence_count": len(manifest_sentences),
            "word_count": len(all_source_words),
            "speech_duration": covered_duration,
            "silence_duration": unmapped_duration
        },
        "sentences": manifest_sentences,
        "unmapped_intervals": unmapped_intervals,
        "validation": validation
    }
    
    if not validation["valid"]:
        manifest["success"] = False
        manifest["error"] = {
            "code": "VALIDATION_FAILED",
            "message": "One or more validation checks failed."
        }
    else:
        manifest["success"] = True
    
    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
            
    return manifest
