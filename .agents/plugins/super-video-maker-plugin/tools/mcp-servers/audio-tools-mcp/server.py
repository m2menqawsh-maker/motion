from mcp.server.fastmcp import FastMCP
import os
import sys
import io
import asyncio
import logging
from typing import Optional

# Setup standard output to handle UTF-8 properly on Windows
if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding='utf-8')
if isinstance(sys.stderr, io.TextIOWrapper):
    sys.stderr.reconfigure(encoding='utf-8')

# Setup basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from utils.ffmpeg_ops import (
    trim_audio_file,
    detect_and_trim_silence_file,
    extend_audio_file,
    normalize_loudness_file
)

# Initialize MCP server
mcp = FastMCP("audio-tools-mcp")

@mcp.tool()
async def trim_audio(file_path: str, target_duration: float, output_path: str | None = None) -> str:
    """
    Trims an audio file to a specific duration from the beginning.
    Returns the absolute path to the processed file.
    """
    return await trim_audio_file(file_path, target_duration, output_path)

@mcp.tool()
async def extend_audio(file_path: str, target_duration: float, method: str = "loop", output_path: str | None = None, auto_trim_silence_before_loop: bool = True, short_duration_threshold: float = 2.0) -> str:
    """
    Extends audio to a target duration.
    method: "loop" (simple looping) or "fade_extend" (looping with crossfades for smoothness).
    auto_trim_silence_before_loop: If True, trims leading/trailing silence before looping to avoid silent gaps.
    short_duration_threshold: If active audio is shorter than this, or decays abruptly, it's considered a one-shot and will NOT be extended.
    Returns the absolute path to the processed file.
    """
    return await extend_audio_file(file_path, target_duration, method, output_path, auto_trim_silence_before_loop, short_duration_threshold)

@mcp.tool()
async def normalize_loudness(file_path: str, target_lufs: float, output_path: str | None = None) -> str:
    """
    Normalizes the loudness of the audio to a specific LUFS target using ffmpeg's loudnorm filter (single-pass).
    Returns the absolute path to the processed file.
    """
    return await normalize_loudness_file(file_path, target_lufs, output_path)

@mcp.tool()
async def detect_and_trim_silence(
    file_path: str, 
    threshold_db: float = -40.0, 
    min_silence_duration: float = 0.1, 
    trim_start: bool = True, 
    trim_end: bool = True, 
    output_path: str | None = None
) -> dict:
    """
    Detects and exactly trims actual silence at the beginning and/or end of an audio file using ffmpeg silencedetect.
    Returns a dictionary containing 'output_path', 'trimmed_start_seconds', and 'trimmed_end_seconds'.
    """
    return await detect_and_trim_silence_file(
        file_path, threshold_db, min_silence_duration, trim_start, trim_end, output_path
    )

from utils.voiceover_ops import analyze_voiceover_file
from utils.sentence_splitter import split_voiceover_sentences_logic
from utils.manifest_builder import build_voiceover_manifest_logic
from utils.timeline_builder import build_voiceover_timeline_logic

@mcp.tool()
async def analyze_voiceover(audio_path: str, language: str | None = None, model_size: str | None = None) -> dict:
    """
    Analyzes a voiceover audio file locally using faster-whisper and Silero VAD.
    Extracts the full text, language, start/end timing for segments and words,
    confidence, speech periods, silence periods, and duration.
    """
    return await analyze_voiceover_file(audio_path, language, model_size)

@mcp.tool()
async def split_voiceover_sentences(
    audio_path: str,
    analysis_path: str,
    output_dir: str,
    min_sentence_duration: float = 2.0,
    max_sentence_duration: float = 10.0,
    silence_threshold: float = 0.30
) -> dict:
    """
    Splits a voiceover audio file into sentence files based on a previously generated analysis JSON.
    Applies logic for punctuation, silence, and duration limits.
    Returns a detailed JSON mapping of each sentence.
    """
    import json
    with open(analysis_path, 'r', encoding='utf-8') as f:
        analysis_data = json.load(f)
        
    return await split_voiceover_sentences_logic(
        audio_path,
        analysis_data,
        output_dir,
        min_sentence_duration,
        max_sentence_duration,
        silence_threshold
    )

@mcp.tool()
async def get_voiceover_manifest(
    audio_path: str,
    analysis: dict | None = None,
    analysis_path: str | None = None,
    split_result: dict | None = None,
    split_result_path: str | None = None,
    output_path: str | None = None
) -> dict:
    """
    Aggregates the results of analyze_voiceover and split_voiceover_sentences into a unified manifest.
    Provides strict validation, absolute word mapping, and timeline coverage calculations.
    Returns the voiceover manifest JSON.
    """
    import json
    if analysis is None:
        if analysis_path is None:
            return {"success": False, "error": {"code": "MISSING_INPUT", "message": "Must provide either analysis or analysis_path"}}
        with open(analysis_path, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
    else:
        analysis_data = analysis

    if split_result is None:
        if split_result_path is None:
            return {"success": False, "error": {"code": "MISSING_INPUT", "message": "Must provide either split_result or split_result_path"}}
        with open(split_result_path, 'r', encoding='utf-8') as f:
            split_data = json.load(f)
    else:
        split_data = split_result
        
    return build_voiceover_manifest_logic(audio_path, analysis_data, split_data, output_path)

@mcp.tool()
async def build_voiceover_timeline(
    manifest: dict | None = None,
    manifest_path: str | None = None,
    output_path: str | None = None
) -> dict:
    """
    Converts a voiceover manifest into a fully chronological, strictly validated audio timeline map.
    The resulting timeline contains flat arrays of sentences, words, and silence_intervals.
    Returns the voiceover timeline JSON.
    """
    import json
    if manifest is None:
        if manifest_path is None:
            return {"success": False, "error": {"code": "MISSING_INPUT", "message": "Must provide either manifest or manifest_path"}}
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)
    else:
        manifest_data = manifest
        
    return build_voiceover_timeline_logic(manifest_data, output_path)

if __name__ == "__main__":
    mcp.run()
