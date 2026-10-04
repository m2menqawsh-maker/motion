"""
scripts/validators/candidate_runtime_runner.py
==============================================
Hermetic, isolated runtime execution runner for TemplateCandidate validation (S28-07C).
Complying with ADR-004 DEC-01.

Guarantees:
- Zero canonical registry mutation (never writes to templates/, registry/, or remotion-app/src/).
- Executes candidate code strictly within an ephemeral, isolated temporary workspace.
- Enforces strict process timeouts, memory limits, and subprocess confinement via safe_subprocess.
- Distinguishes candidate runtime failures (mount error, syntax crash) from tool execution errors.
- Guarantees complete cleanup of the ephemeral workspace upon completion or error.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from PIL import Image

from creative_governance.candidates.policies import (
    CANONICAL_ASPECT_RATIOS,
    ValidationFailureCode,
)
from scripts.security.security import safe_subprocess


@dataclass
class CandidateRenderResult:
    """Standardized result of a candidate frame still render."""
    success: bool
    frame_index: int
    frame_number: int
    width: int
    height: int
    aspect_ratio: str
    output_path: Optional[str] = None
    sha256_digest: Optional[str] = None
    file_size_bytes: int = 0
    error_message: Optional[str] = None
    failure_code: Optional[str] = None
    is_tool_error: bool = False
    raw_stdout: str = ""
    raw_stderr: str = ""


class IsolatedCandidateRunner:
    """
    Manages isolated temporary workspace preparation, harness compilation,
    and headless Remotion frame rendering for a candidate.
    """

    def __init__(
        self,
        workspace_root: Optional[Path] = None,
        mock_render_fn: Optional[Callable[..., CandidateRenderResult]] = None,
    ) -> None:
        self.workspace_root = (workspace_root or Path.cwd()).resolve()
        self.base_tmp_dir = self.workspace_root / "data" / "tmp_candidate_runtime"
        self.base_tmp_dir.mkdir(parents=True, exist_ok=True)
        self.mock_render_fn = mock_render_fn

    def create_workspace(self, candidate_id: str, validation_id: str) -> Path:
        """Creates an isolated temporary directory within the workspace root."""
        prefix = f"cand_rt_{candidate_id}_{validation_id}_"
        temp_dir = tempfile.mkdtemp(prefix=prefix, dir=self.base_tmp_dir)
        return Path(temp_dir).resolve()

    def prepare_workspace(
        self,
        workspace_dir: Path,
        source_code: str,
        fixtures: Dict[str, Any],
        component_name: Optional[str] = None,
    ) -> Tuple[Path, Path]:
        """
        Populates the isolated temporary workspace with:
        1. CandidateComponent.tsx (the candidate code)
        2. render_props.json (the test fixtures)
        3. CandidateHarness.tsx (the isolated Remotion root harness)
        """
        # 1. Candidate source component
        component_file = workspace_dir / "CandidateComponent.tsx"
        component_file.write_text(source_code, encoding="utf-8")

        # 2. Render props JSON
        props_file = workspace_dir / "render_props.json"
        props_file.write_text(json.dumps(fixtures or {}), encoding="utf-8")

        # 3. Dynamic Harness Root
        comp_id = component_name or "CandidateComponent"
        harness_code = f"""import React from 'react';
import {{ Composition, registerRoot }} from 'remotion';
import * as CandidateModule from './CandidateComponent';

// Dynamic resolver for component export (default or named)
const resolveComponent = () => {{
  const mod = CandidateModule as any;
  if (mod.default && typeof mod.default === 'function') return mod.default;
  if (mod['{comp_id}'] && typeof mod['{comp_id}'] === 'function') return mod['{comp_id}'];
  for (const key of Object.keys(mod)) {{
    if (typeof mod[key] === 'function') return mod[key];
  }}
  return () => React.createElement('div', null, 'Failed to resolve component export');
}};

const ResolvedComponent = resolveComponent();

export const CandidateHarness: React.FC<any> = (props) => {{
  return React.createElement(ResolvedComponent, props);
}};

export const Root: React.FC = () => {{
  return (
    <Composition
      id="CandidateHarness"
      component={{CandidateHarness}}
      width={{1080}}
      height={{1920}}
      fps={{30}}
      durationInFrames={{30}}
      defaultProps={{{{}}}}
    />
  );
}};

registerRoot(Root);
"""
        harness_file = workspace_dir / "CandidateHarness.tsx"
        harness_file.write_text(harness_code, encoding="utf-8")

        return harness_file, props_file

    def render_still(
        self,
        workspace_dir: Path,
        harness_file: Path,
        props_file: Path,
        frame_number: int = 0,
        frame_index: int = 0,
        width: int = 1080,
        height: int = 1920,
        fps: int = 30,
        duration: int = 30,
        aspect_ratio: str = "9:16",
        out_filename: Optional[str] = None,
        timeout_seconds: int = 35,
    ) -> CandidateRenderResult:
        """
        Renders a single frame still using Remotion CLI in the isolated workspace.
        """
        if self.mock_render_fn is not None:
            return self.mock_render_fn(
                workspace_dir=workspace_dir,
                frame_number=frame_number,
                frame_index=frame_index,
                width=width,
                height=height,
                aspect_ratio=aspect_ratio,
                out_filename=out_filename,
            )

        out_name = out_filename or f"frame_{frame_index:02d}_f{frame_number}.png"
        out_path = workspace_dir / out_name
        if out_path.exists():
            out_path.unlink()

        npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
        cmd = [
            npx_cmd,
            "remotion",
            "still",
            str(harness_file),
            "CandidateHarness",
            str(out_path),
            f"--frame={frame_number}",
            f"--width={width}",
            f"--height={height}",
            f"--fps={fps}",
            f"--duration={duration}",
            f"--props={str(props_file)}",
            "--log=error",
        ]

        try:
            res = safe_subprocess(
                cmd,
                cwd=str(self.workspace_root),
                shell=False,
                capture_output=True,
                timeout=timeout_seconds,
            )
        except PermissionError as e:
            return CandidateRenderResult(
                success=False,
                frame_index=frame_index,
                frame_number=frame_number,
                width=width,
                height=height,
                aspect_ratio=aspect_ratio,
                error_message=f"Subprocess permission denied: {e}",
                failure_code=ValidationFailureCode.RENDER_TOOL_EXECUTION_ERROR,
                is_tool_error=True,
            )
        except Exception as e:
            if "TimeoutExpired" in type(e).__name__ or "timeout" in str(e).lower():
                return CandidateRenderResult(
                    success=False,
                    frame_index=frame_index,
                    frame_number=frame_number,
                    width=width,
                    height=height,
                    aspect_ratio=aspect_ratio,
                    error_message=f"Render timed out after {timeout_seconds}s",
                    failure_code=ValidationFailureCode.RENDER_TIMEOUT,
                    is_tool_error=False,
                )
            return CandidateRenderResult(
                success=False,
                frame_index=frame_index,
                frame_number=frame_number,
                width=width,
                height=height,
                aspect_ratio=aspect_ratio,
                error_message=f"Render tool execution error: {e}",
                failure_code=ValidationFailureCode.RENDER_TOOL_EXECUTION_ERROR,
                is_tool_error=True,
            )

        stdout_str = res.stdout.decode("utf-8", errors="ignore") if res.stdout else ""
        stderr_str = res.stderr.decode("utf-8", errors="ignore") if res.stderr else ""
        full_output = f"{stdout_str}\n{stderr_str}".strip()

        if res.returncode != 0:
            lower_err = full_output.lower()
            if "cannot find module" in lower_err or "failed to resolve" in lower_err:
                code = ValidationFailureCode.RENDER_IMPORT_ERROR
                is_tool = False
            elif "error:" in lower_err or "uncaught" in lower_err or "react" in lower_err or "element type is invalid" in lower_err:
                code = ValidationFailureCode.RENDER_MOUNT_ERROR
                is_tool = False
            elif "timed out" in lower_err:
                code = ValidationFailureCode.RENDER_TIMEOUT
                is_tool = False
            elif res.returncode in (127, 126):
                code = ValidationFailureCode.RENDER_TOOL_EXECUTION_ERROR
                is_tool = True
            else:
                code = ValidationFailureCode.CANDIDATE_RUNTIME_FAILURE
                is_tool = False

            return CandidateRenderResult(
                success=False,
                frame_index=frame_index,
                frame_number=frame_number,
                width=width,
                height=height,
                aspect_ratio=aspect_ratio,
                error_message=f"Remotion exited with {res.returncode}: {full_output[:300]}",
                failure_code=code,
                is_tool_error=is_tool,
                raw_stdout=stdout_str,
                raw_stderr=stderr_str,
            )

        if not out_path.exists() or out_path.stat().st_size == 0:
            return CandidateRenderResult(
                success=False,
                frame_index=frame_index,
                frame_number=frame_number,
                width=width,
                height=height,
                aspect_ratio=aspect_ratio,
                error_message="Rendered output image missing or 0 bytes",
                failure_code=ValidationFailureCode.RENDER_EMPTY_OUTPUT,
                is_tool_error=False,
                raw_stdout=stdout_str,
                raw_stderr=stderr_str,
            )

        data = out_path.read_bytes()
        if not data.startswith(b"\x89PNG\r\n\x1a\n") and not data.startswith(b"\xff\xd8\xff"):
            return CandidateRenderResult(
                success=False,
                frame_index=frame_index,
                frame_number=frame_number,
                width=width,
                height=height,
                aspect_ratio=aspect_ratio,
                error_message="Rendered output is not a valid PNG or JPEG image",
                failure_code=ValidationFailureCode.PROBE_CORRUPT_HEADER,
                is_tool_error=False,
                raw_stdout=stdout_str,
                raw_stderr=stderr_str,
            )

        try:
            with Image.open(out_path) as img:
                actual_w, actual_h = img.size
        except Exception as e:
            return CandidateRenderResult(
                success=False,
                frame_index=frame_index,
                frame_number=frame_number,
                width=width,
                height=height,
                aspect_ratio=aspect_ratio,
                error_message=f"Failed to decode image dimensions: {e}",
                failure_code=ValidationFailureCode.QC_CORRUPT_FRAME,
                is_tool_error=False,
                raw_stdout=stdout_str,
                raw_stderr=stderr_str,
            )

        sha = hashlib.sha256(data).hexdigest()
        return CandidateRenderResult(
            success=True,
            frame_index=frame_index,
            frame_number=frame_number,
            width=actual_w,
            height=actual_h,
            aspect_ratio=aspect_ratio,
            output_path=str(out_path.absolute()),
            sha256_digest=sha,
            file_size_bytes=len(data),
            raw_stdout=stdout_str,
            raw_stderr=stderr_str,
        )

    def cleanup_workspace(self, workspace_dir: Path) -> None:
        """Removes the ephemeral isolated workspace directory safely."""
        try:
            if workspace_dir.exists() and workspace_dir.is_dir():
                shutil.rmtree(workspace_dir, ignore_errors=True)
        except Exception:
            pass
