"""
ai/mcp/adapters/audio.py
========================
Hardened adapters for retained audio MCP operations (S27.10).

Invariants:
- Uses asyncio.create_subprocess_exec with explicit argv (strictly no shell=True).
- Server-side path validation via MCPSecurityPolicy.validate_safe_path.
- Strict bounded execution timeouts.
- Structured error handling and audit tracking.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from ai.mcp.adapters.base import BaseMCPAdapter, run_safe_subprocess
from ai.mcp.contracts import (
    ExtendAudioInput,
    ExtendAudioOutput,
    NormalizeLoudnessInput,
    NormalizeLoudnessOutput,
    TrimAudioInput,
    TrimAudioOutput,
    TrimSilenceInput,
    TrimSilenceOutput,
)
from ai.mcp.errors import MCPExecutionError
from ai.mcp.policy import MCPSecurityPolicy
from ai.tools.types import TrustedToolExecutionContext


class AudioTrimAdapter(BaseMCPAdapter[TrimAudioInput, TrimAudioOutput]):
    """Hardened adapter for audio trimming."""
    def __init__(self):
        super().__init__("audio-tools-mcp", "trim_audio")

    async def _execute_internal(
        self,
        input_data: TrimAudioInput,
        context: TrustedToolExecutionContext,
    ) -> TrimAudioOutput:
        src = MCPSecurityPolicy.validate_safe_path(input_data.file_path, must_exist=True)

        if input_data.output_path:
            dst = MCPSecurityPolicy.validate_safe_path(input_data.output_path)
        else:
            dst = src.with_name(f"{src.stem}_trimmed{src.suffix}")

        cmd = [
            "ffmpeg", "-y",
            "-i", str(src),
            "-t", str(input_data.target_duration),
            "-c", "copy",
            str(dst),
        ]
        await run_safe_subprocess(cmd, output_path=dst)
        return TrimAudioOutput(output_path=str(dst), target_duration=input_data.target_duration)


class AudioNormalizeAdapter(BaseMCPAdapter[NormalizeLoudnessInput, NormalizeLoudnessOutput]):
    """Hardened adapter for audio loudness normalization."""
    def __init__(self):
        super().__init__("audio-tools-mcp", "normalize_loudness")

    async def _execute_internal(
        self,
        input_data: NormalizeLoudnessInput,
        context: TrustedToolExecutionContext,
    ) -> NormalizeLoudnessOutput:
        src = MCPSecurityPolicy.validate_safe_path(input_data.file_path, must_exist=True)

        if input_data.output_path:
            dst = MCPSecurityPolicy.validate_safe_path(input_data.output_path)
        else:
            dst = src.with_name(f"{src.stem}_norm{src.suffix}")

        cmd = [
            "ffmpeg", "-y",
            "-i", str(src),
            "-af", f"loudnorm=I={input_data.target_lufs}:LRA=11:TP=-1.5",
            str(dst),
        ]
        await run_safe_subprocess(cmd, output_path=dst)
        return NormalizeLoudnessOutput(output_path=str(dst), target_lufs=input_data.target_lufs)


class AudioSilenceAdapter(BaseMCPAdapter[TrimSilenceInput, TrimSilenceOutput]):
    """Hardened adapter for audio silence trimming."""
    def __init__(self):
        super().__init__("audio-tools-mcp", "detect_and_trim_silence")

    async def _execute_internal(
        self,
        input_data: TrimSilenceInput,
        context: TrustedToolExecutionContext,
    ) -> TrimSilenceOutput:
        src = MCPSecurityPolicy.validate_safe_path(input_data.file_path, must_exist=True)

        if input_data.output_path:
            dst = MCPSecurityPolicy.validate_safe_path(input_data.output_path)
        else:
            dst = src.with_name(f"{src.stem}_nosilence{src.suffix}")

        # Basic silenceremove filter
        cmd = [
            "ffmpeg", "-y",
            "-i", str(src),
            "-af", f"silenceremove=start_periods=1:start_duration={input_data.min_silence_duration}:start_threshold={input_data.threshold_db}dB",
            str(dst),
        ]
        await run_safe_subprocess(cmd, output_path=dst)
        return TrimSilenceOutput(
            output_path=str(dst),
            trimmed_start_seconds=input_data.min_silence_duration,
            trimmed_end_seconds=0.0,
        )


class AudioExtendAdapter(BaseMCPAdapter[ExtendAudioInput, ExtendAudioOutput]):
    """Hardened adapter for audio duration extension."""
    def __init__(self):
        super().__init__("audio-tools-mcp", "extend_audio")

    async def _execute_internal(
        self,
        input_data: ExtendAudioInput,
        context: TrustedToolExecutionContext,
    ) -> ExtendAudioOutput:
        src = MCPSecurityPolicy.validate_safe_path(input_data.file_path, must_exist=True)

        if input_data.output_path:
            dst = MCPSecurityPolicy.validate_safe_path(input_data.output_path)
        else:
            dst = src.with_name(f"{src.stem}_extended{src.suffix}")

        # Simple loop using ffmpeg stream_loop
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", str(src),
            "-t", str(input_data.target_duration),
            "-c", "copy",
            str(dst),
        ]
        await run_safe_subprocess(cmd, output_path=dst)
        return ExtendAudioOutput(
            output_path=str(dst),
            final_duration=input_data.target_duration,
            method=input_data.method,
        )
