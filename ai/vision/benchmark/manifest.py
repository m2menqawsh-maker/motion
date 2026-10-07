"""
ai/vision/benchmark/manifest.py
===============================
Benchmark manifest for Vision Intelligence (S27.15 / AI-13 Rules 27-28).

Covers all 11 mandatory visual domains:
1. Talking head
2. Product video
3. Screen recording
4. B-roll
5. UI demo
6. Motion graphics
7. Vertical video (9:16)
8. Horizontal video (16:9)
9. Arabic text OCR
10. English text OCR
11. Low light environment
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class VisionBenchmarkCategory(str, Enum):
    TALKING_HEAD = "talking_head"
    PRODUCT_VIDEO = "product_video"
    SCREEN_RECORDING = "screen_recording"
    B_ROLL = "b_roll"
    UI_DEMO = "ui_demo"
    MOTION_GRAPHICS = "motion_graphics"
    VERTICAL_VIDEO = "vertical_video"
    HORIZONTAL_VIDEO = "horizontal_video"
    ARABIC_TEXT = "arabic_text"
    ENGLISH_TEXT = "english_text"
    LOW_LIGHT = "low_light"


@dataclass(frozen=True)
class VisionBenchmarkSample:
    sample_id: str
    category: VisionBenchmarkCategory
    description: str
    aspect_ratio: str
    expected_shot_count: int
    has_text: bool
    text_language: Optional[str] = None
    has_human: bool = False
    has_real_video_asset: bool = False  # Set to False until Final Validation phase


PROJECT_VISION_BENCHMARK_CORPUS: List[VisionBenchmarkSample] = [
    VisionBenchmarkSample(
        sample_id="vis_talk_head_001",
        category=VisionBenchmarkCategory.TALKING_HEAD,
        description="Presenter introducing video maker platform in studio lighting",
        aspect_ratio="16:9",
        expected_shot_count=1,
        has_text=False,
        has_human=True,
    ),
    VisionBenchmarkSample(
        sample_id="vis_prod_vid_001",
        category=VisionBenchmarkCategory.PRODUCT_VIDEO,
        description="Product turntable video showing smartphone camera bump",
        aspect_ratio="16:9",
        expected_shot_count=3,
        has_text=False,
        has_human=False,
    ),
    VisionBenchmarkSample(
        sample_id="vis_screen_rec_001",
        category=VisionBenchmarkCategory.SCREEN_RECORDING,
        description="Desktop screen recording of video editor timeline drag and drop",
        aspect_ratio="16:9",
        expected_shot_count=1,
        has_text=True,
        text_language="en",
        has_human=False,
    ),
    VisionBenchmarkSample(
        sample_id="vis_broll_001",
        category=VisionBenchmarkCategory.B_ROLL,
        description="Drone cinematic landscape shot over mountain valley",
        aspect_ratio="16:9",
        expected_shot_count=2,
        has_text=False,
        has_human=False,
    ),
    VisionBenchmarkSample(
        sample_id="vis_ui_demo_001",
        category=VisionBenchmarkCategory.UI_DEMO,
        description="Software interface walkthrough highlighting settings and export buttons",
        aspect_ratio="16:9",
        expected_shot_count=2,
        has_text=True,
        text_language="en",
        has_human=False,
    ),
    VisionBenchmarkSample(
        sample_id="vis_motion_gfx_001",
        category=VisionBenchmarkCategory.MOTION_GRAPHICS,
        description="Kinetic typography and shape animations for promo title card",
        aspect_ratio="16:9",
        expected_shot_count=4,
        has_text=True,
        text_language="en",
        has_human=False,
    ),
    VisionBenchmarkSample(
        sample_id="vis_vert_vid_001",
        category=VisionBenchmarkCategory.VERTICAL_VIDEO,
        description="Short-form TikTok / Reels vertical video with centered subject",
        aspect_ratio="9:16",
        expected_shot_count=2,
        has_text=True,
        text_language="ar",
        has_human=True,
    ),
    VisionBenchmarkSample(
        sample_id="vis_horiz_vid_001",
        category=VisionBenchmarkCategory.HORIZONTAL_VIDEO,
        description="Standard 1080p horizontal corporate presentation video",
        aspect_ratio="16:9",
        expected_shot_count=2,
        has_text=False,
        has_human=True,
    ),
    VisionBenchmarkSample(
        sample_id="vis_ar_text_001",
        category=VisionBenchmarkCategory.ARABIC_TEXT,
        description="Arabic typography billboard and video lower thirds in Cairo street",
        aspect_ratio="16:9",
        expected_shot_count=1,
        has_text=True,
        text_language="ar",
        has_human=False,
    ),
    VisionBenchmarkSample(
        sample_id="vis_en_text_001",
        category=VisionBenchmarkCategory.ENGLISH_TEXT,
        description="English tech conference slide presentation with bulleted text",
        aspect_ratio="16:9",
        expected_shot_count=1,
        has_text=True,
        text_language="en",
        has_human=False,
    ),
    VisionBenchmarkSample(
        sample_id="vis_low_light_001",
        category=VisionBenchmarkCategory.LOW_LIGHT,
        description="Night city street scene with neon signs and high contrast shadows",
        aspect_ratio="16:9",
        expected_shot_count=2,
        has_text=True,
        text_language="en",
        has_human=True,
    ),
]


def get_vision_benchmark_manifest() -> List[VisionBenchmarkSample]:
    return list(PROJECT_VISION_BENCHMARK_CORPUS)


def get_vision_categories_summary() -> Dict[str, int]:
    summary: Dict[str, int] = {}
    for sample in PROJECT_VISION_BENCHMARK_CORPUS:
        key = sample.category.value
        summary[key] = summary.get(key, 0) + 1
    return summary
