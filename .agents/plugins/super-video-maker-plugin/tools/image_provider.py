#!/usr/bin/env python3
"""OpenAI image generation/editing helper for video assets.

This is intentionally small: agents call this script instead of writing raw API
calls. It saves outputs locally and emits one RESULT JSON line.
"""

import argparse
import base64
from contextlib import ExitStack
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


DEFAULT_MODEL = "gpt-image-2"


def emit(payload):
    print("RESULT: " + json.dumps(payload), flush=True)


def output_dir():
    out = Path.cwd() / "output_images"
    out.mkdir(parents=True, exist_ok=True)
    return out


def save_b64_image(b64_data, prefix="image", output_format="png"):
    ext = "jpg" if output_format == "jpeg" else output_format
    path = output_dir() / f"{prefix}_{int(time.time())}.{ext}"
    path.write_bytes(base64.b64decode(b64_data))
    return path


def require_openai_key():
    raise PermissionError("DIRECT SECRET ACCESS BLOCKED: Direct access to OPENAI_API_KEY outside canonical S27 capability adapters is prohibited.")


def optional_kwargs(**kwargs):
    return {key: value for key, value in kwargs.items() if value is not None}


def first_image_b64(result):
    item = result.data[0]
    b64_data = getattr(item, "b64_json", None)
    if not b64_data:
        emit({"status": "failed", "error": "No b64_json returned by image API", "provider": "openai"})
        sys.exit(1)
    return b64_data


def generate(args):
    raise RuntimeError(
        "DIRECT PROVIDER EXECUTION BLOCKED: Direct image generation via legacy image_provider.py is prohibited. "
        "Use canonical S27 image capability adapters and ModelRouter."
    )


def edit(args):
    raise RuntimeError(
        "DIRECT PROVIDER EXECUTION BLOCKED: Direct image editing via legacy image_provider.py is prohibited. "
        "Use canonical S27 image capability adapters and ModelRouter."
    )


def build_parser():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate")
    gen.add_argument("--prompt", required=True)
    gen.add_argument("--size", default="1024x1024")
    gen.add_argument("--model", default=DEFAULT_MODEL)
    gen.add_argument("--quality", default="high")
    gen.add_argument("--background", default=None)
    gen.add_argument("--output-format", default="png", choices=["png", "jpeg", "webp"])
    gen.add_argument("--output-compression", type=int, default=None)
    gen.set_defaults(func=generate)

    edit_cmd = sub.add_parser("edit")
    edit_cmd.add_argument("--reference-image", action="append", required=True, help="Local path. Repeat up to the provider limit.")
    edit_cmd.add_argument("--mask", default=None, help="Optional local mask path.")
    edit_cmd.add_argument("--prompt", required=True)
    edit_cmd.add_argument("--size", default="1024x1024")
    edit_cmd.add_argument("--model", default=DEFAULT_MODEL)
    edit_cmd.add_argument("--quality", default="high")
    edit_cmd.add_argument("--input-fidelity", default=None)
    edit_cmd.add_argument("--background", default=None)
    edit_cmd.add_argument("--output-format", default="png", choices=["png", "jpeg", "webp"])
    edit_cmd.add_argument("--output-compression", type=int, default=None)
    edit_cmd.set_defaults(func=edit)

    return parser


def main():
    raise RuntimeError(
        "DIRECT PROVIDER BYPASS BLOCKED: Direct CLI execution of image_provider.py is prohibited. "
        "Route all image generation requests via canonical S27 image capabilities and ModelRouter."
    )


if __name__ == "__main__":
    main()
