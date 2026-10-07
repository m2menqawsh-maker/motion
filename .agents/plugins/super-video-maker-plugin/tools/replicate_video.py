#!/usr/bin/env python3
"""CLI wrapper around Replicate's bytedance/seedance-2.0 video model.

Always prints exactly one line to stdout starting with `RESULT: ` containing
JSON. Human logs go to stderr.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


def _find_repo_root(start: Path) -> Path:
    """Walk up from the skill dir to the project root (marked by .env or .git)."""
    for p in [start, *start.parents]:
        if (p / ".env").exists() or (p / ".git").exists():
            return p
    return start


SKILL_DIR = Path(__file__).resolve().parents[1]
# CWD wins if it has a .env (lets users invoke from any project), else walk up.
_CWD = Path.cwd().resolve()
REPO_ROOT = _CWD if (_CWD / ".env").exists() else _find_repo_root(SKILL_DIR)
DEFAULT_MODEL = "bytedance/seedance-2.0"
OUTPUT_DIR = REPO_ROOT / "output_videos"


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def emit(payload: dict[str, Any]) -> None:
    print("RESULT: " + json.dumps(payload), flush=True)


def load_env() -> str:
    raise PermissionError("DIRECT SECRET ACCESS BLOCKED: Direct access to REPLICATE_API_TOKEN outside canonical S27 capability adapters is prohibited.")


def resolve_reference(ref: str) -> Any:
    """Local paths are returned as open file handles; URLs pass through."""
    if ref.startswith(("http://", "https://")):
        return ref
    p = Path(ref).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"reference not found: {ref}")
    return open(p, "rb")


def cmd_generate(args: argparse.Namespace) -> None:
    raise RuntimeError(
        "DIRECT PROVIDER EXECUTION BLOCKED: Direct Replicate provider execution via legacy replicate_video.py is prohibited. "
        "Use canonical S27 video capability adapters and ModelRouter."
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="replicate_video.py")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="Generate a video clip with Seedance 2.0")
    g.add_argument("--prompt", required=True)
    g.add_argument("--aspect-ratio", default="16:9", choices=["16:9", "9:16", "1:1", "4:3", "3:4", "21:9"])
    g.add_argument("--duration", type=int, default=7, help="Clip length in seconds")
    g.add_argument("--resolution", default="1080p", choices=["480p", "720p", "1080p"])
    g.add_argument("--generate-audio", action="store_true")
    g.add_argument("--reference-image", action="append", help="Local path or URL. Repeat to add more.")
    g.add_argument("--reference-audio", action="append", help="Local path or URL. Repeat to add more.")
    g.add_argument("--reference-video", action="append", help="Local path or URL. Repeat to add more.")
    g.add_argument("--seed", type=int, default=None)
    g.add_argument("--model", default=DEFAULT_MODEL, help="Override model slug or pin a version (owner/name:hash).")
    g.set_defaults(func=cmd_generate)

    return p


def main() -> None:
    raise RuntimeError(
        "DIRECT PROVIDER BYPASS BLOCKED: Direct CLI execution of replicate_video.py is prohibited. "
        "Route all video requests via canonical S27 capabilities and ModelRouter."
    )


if __name__ == "__main__":
    main()
