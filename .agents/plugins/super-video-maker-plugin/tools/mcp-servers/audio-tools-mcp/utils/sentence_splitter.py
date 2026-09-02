import os
import json
import asyncio
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

STRONG_PUNCTUATION = ['.', '!', '؟', '?', '…']
WEAK_PUNCTUATION = [',', '،', ';', ':']

def _get_punctuation_level(word_text: str) -> int:
    text = word_text.strip()
    if not text:
        return 0
    last_char = text[-1]
    if last_char in STRONG_PUNCTUATION:
        return 2
    if last_char in WEAK_PUNCTUATION:
        return 1
    return 0

async def split_voiceover_sentences_logic(
    audio_path: str,
    analysis_data: Dict[str, Any],
    output_dir: str,
    min_sentence_duration: float = 2.0,
    max_sentence_duration: float = 10.0,
    silence_threshold: float = 0.30,
    pre_padding: float = 0.03,
    post_padding: float = 0.05
) -> Dict[str, Any]:
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Flatten words with segment awareness
    all_words = []
    if "segments" in analysis_data:
        for seg in analysis_data["segments"]:
            if "words" in seg:
                seg_words = seg["words"]
                for i, w in enumerate(seg_words):
                    w_copy = dict(w)
                    if i == len(seg_words) - 1:
                        w_copy["is_segment_end"] = True
                    else:
                        w_copy["is_segment_end"] = False
                    all_words.append(w_copy)
    else:
        # Fallback if just words
        all_words = analysis_data.get("words", [])
        
    if not all_words:
        raise ValueError("No words found in the analysis data.")
        
    sentences_raw = []
    current_words = []
    
    word_index = 0
    total_words = len(all_words)
    
    while word_index < total_words:
        word = all_words[word_index]
        current_words.append(word)
        
        is_last_word = (word_index == total_words - 1)
        next_word = all_words[word_index + 1] if not is_last_word else None
        
        gap_to_next = (next_word["start"] - word["end"]) if next_word else float('inf')
        
        curr_duration = word["end"] - current_words[0]["start"]
        punct_level = _get_punctuation_level(word["word"])
        
        is_long_silence = gap_to_next > silence_threshold
        is_segment_end = word.get("is_segment_end", False)
        
        split_reason = None
        
        if is_last_word:
            split_reason = "end_of_file"
        elif curr_duration > max_sentence_duration:
            split_reason = "duration_limit"
        else:
            # Normal forward logic
            # Condition 1: End of sentence clearly (Strong Punct + gap > 0.1s)
            if punct_level == 2 and gap_to_next > 0.1:
                split_reason = "strong_punctuation"
            # Condition 2: Segment end! We should respect whisper segments if duration is decent.
            elif is_segment_end and curr_duration >= min_sentence_duration:
                split_reason = "whisper_segment_end"
            # Condition 3: Min duration met AND (Silence > threshold OR Strong Punctuation)
            elif curr_duration >= min_sentence_duration:
                if is_long_silence and punct_level > 0:
                    split_reason = "silence_and_punctuation"
                elif is_long_silence:
                    split_reason = "silence"
                elif punct_level == 2:
                    split_reason = "strong_punctuation"
        
        if split_reason == "duration_limit":
            # Backtrack to find the best split point
            best_idx = -1
            best_score = -1
            
            for i in range(len(current_words) - 1):
                cw = current_words[i]
                nw = current_words[i+1]
                cg = nw["start"] - cw["end"]
                cp = _get_punctuation_level(cw["word"])
                
                score = 0
                if cw.get("is_segment_end", False):
                    score += 50
                if cg > silence_threshold:
                    score += 10
                score += cp * 3
                if cg > 0.1:
                    score += 1
                
                if score >= best_score:
                    best_score = score
                    best_idx = i
                    
            if best_idx != -1 and best_score > 0:
                split_words = current_words[:best_idx+1]
                remaining_words = current_words[best_idx+1:]
                
                cw = split_words[-1]
                nw = remaining_words[0]
                cg = nw["start"] - cw["end"]
                cp = _get_punctuation_level(cw["word"])
                
                if cg > silence_threshold:
                    s_reason = "max_duration_backtrack_silence"
                elif cp > 0:
                    s_reason = "max_duration_backtrack_punctuation"
                else:
                    s_reason = "max_duration_fallback"
                    
                sentences_raw.append({
                    "words": split_words,
                    "reason": s_reason
                })
                current_words = remaining_words
            else:
                if len(current_words) > 1:
                    split_words = current_words[:-1]
                    remaining_words = [current_words[-1]]
                    sentences_raw.append({
                        "words": split_words,
                        "reason": "duration_limit_forced"
                    })
                    current_words = remaining_words
                else:
                    sentences_raw.append({
                        "words": current_words,
                        "reason": "duration_limit_forced_single_word"
                    })
                    current_words = []
                    
        elif split_reason:
            sentences_raw.append({
                "words": list(current_words),
                "reason": split_reason
            })
            current_words = []
            
        word_index += 1

    audio_duration = analysis_data.get("audio_duration", 0.0)
    
    result_sentences = []
    
    for i, sent in enumerate(sentences_raw):
        words = sent["words"]
        reason = sent["reason"]
        
        raw_start = words[0]["start"]
        raw_end = words[-1]["end"]
        
        # Calculate padding without overlap
        if i > 0:
            prev_raw_end = sentences_raw[i-1]["words"][-1]["end"]
            gap_prev = raw_start - prev_raw_end
            actual_pre_pad = min(pre_padding, gap_prev / 2.0)
        else:
            actual_pre_pad = pre_padding
            
        if i < len(sentences_raw) - 1:
            next_raw_start = sentences_raw[i+1]["words"][0]["start"]
            gap_next = next_raw_start - raw_end
            actual_post_pad = min(post_padding, gap_next / 2.0)
        else:
            actual_post_pad = post_padding
            
        final_start = max(0.0, raw_start - actual_pre_pad)
        final_end = raw_end + actual_post_pad
        if audio_duration > 0:
            final_end = min(audio_duration, final_end)
            
        file_name = f"sentence_{i+1:03d}.wav"
        out_path = os.path.abspath(os.path.join(output_dir, file_name))
        
        # FFmpeg command for re-encoding to WAV (sample accuracy)
        cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(final_start),
            "-to", str(final_end),
            "-i", audio_path,
            "-c:a", "pcm_s16le",
            out_path
        ]
        
        logger.info(f"Extracting {file_name} from {final_start:.3f} to {final_end:.3f} (Reason: {reason})")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.error(f"FFmpeg failed for {file_name}: {stderr.decode()}")
            raise RuntimeError(f"FFmpeg failed to extract {file_name}")
            
        sentence_text = " ".join([w["word"].strip() for w in words])
        
        # Calculate inter-sentence gap with previous sentence
        inter_sentence_gap = 0.0
        if i > 0:
            inter_sentence_gap = raw_start - sentences_raw[i-1]["words"][-1]["end"]
            
        result_sentences.append({
            "index": i + 1,
            "text": sentence_text,
            "split_reason": reason,
            "output_path": out_path,
            "source_timing": {
                "start": raw_start,
                "end": raw_end,
                "duration": raw_end - raw_start
            },
            "file_timing": {
                "start": final_start,
                "end": final_end,
                "duration": final_end - final_start,
                "pre_padding_applied": actual_pre_pad,
                "post_padding_applied": actual_post_pad
            },
            "inter_sentence_gap": inter_sentence_gap,
            "words": words
        })
        
    return {
        "status": "success",
        "audio_path": os.path.abspath(audio_path),
        "total_sentences": len(result_sentences),
        "sentences": result_sentences
    }
