"""
ai/evals/datasets.py
====================
Authoritative Versioned Evaluation Datasets (S27.20).

Invariants:
- Datasets for: routing, planning, memory retrieval, tool selection, structured outputs, speech, vision, audio.
- Strict dataset versioning with SHA-256 content hashes.
- Ground truth is strictly segregated from model generation.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from ai.contracts.common import CapabilityType
from ai.contracts.evals import EvalDatasetContract, EvalExample


def build_routing_dataset(version: str = "1.0.0") -> EvalDatasetContract:
    examples = [
        EvalExample(
            example_id="route_low_latency",
            input_payload={"capability": "TEXT_TO_SPEECH", "max_latency_ms": 300},
            expected_output={"preferred_tier": "REALTIME"},
            min_quality_score=0.9,
        ),
        EvalExample(
            example_id="route_zero_data_retention",
            input_payload={"capability": "VOICE_SYNTHESIS", "privacy_requirement": "ZERO_DATA_RETENTION"},
            expected_output={"privacy_compliant": True},
            min_quality_score=0.9,
        ),
    ]
    chash = EvalDatasetContract.compute_content_hash(examples)
    return EvalDatasetContract(
        dataset_id="eval_dataset_routing",
        version=version,
        content_hash=chash,
        capability=CapabilityType.TEXT_GENERATION,
        description="Benchmark dataset for router policy compliance and latency constraints",
        examples=examples,
    )


def build_planning_dataset(version: str = "1.0.0") -> EvalDatasetContract:
    examples = [
        EvalExample(
            example_id="plan_linear_video",
            input_payload={"goal": "Generate 30s video with narration and background music"},
            expected_output={"required_steps": ["script", "voiceover", "visuals", "render"]},
            min_quality_score=0.85,
        ),
    ]
    chash = EvalDatasetContract.compute_content_hash(examples)
    return EvalDatasetContract(
        dataset_id="eval_dataset_planning",
        version=version,
        content_hash=chash,
        capability=CapabilityType.REASONING,
        description="Benchmark dataset for multi-step DAG planning and sequencing",
        examples=examples,
    )


def build_memory_retrieval_dataset(version: str = "1.0.0") -> EvalDatasetContract:
    examples = [
        EvalExample(
            example_id="mem_recall_brand_color",
            input_payload={"query": "What is the corporate primary hex color?", "context_items": 5},
            expected_output={"recalled_value": "#1E40AF"},
            ground_truth_label="#1E40AF",
            is_human_verified=True,
            min_quality_score=0.95,
        ),
    ]
    chash = EvalDatasetContract.compute_content_hash(examples)
    return EvalDatasetContract(
        dataset_id="eval_dataset_memory_retrieval",
        version=version,
        content_hash=chash,
        capability=CapabilityType.CONTEXT_COMPRESSION,
        description="Benchmark dataset for semantic and exact memory retrieval",
        examples=examples,
    )


def build_tool_selection_dataset(version: str = "1.0.0") -> EvalDatasetContract:
    examples = [
        EvalExample(
            example_id="tool_crop_video",
            input_payload={"user_instruction": "Crop video to 9:16 vertical aspect ratio"},
            expected_output={"selected_tool": "crop_video", "target_aspect": "9:16"},
            min_quality_score=0.9,
        ),
    ]
    chash = EvalDatasetContract.compute_content_hash(examples)
    return EvalDatasetContract(
        dataset_id="eval_dataset_tool_selection",
        version=version,
        content_hash=chash,
        capability=CapabilityType.TOOL_EXECUTION,
        description="Benchmark dataset for tool and function selection accuracy",
        examples=examples,
    )


def build_structured_outputs_dataset(version: str = "1.0.0") -> EvalDatasetContract:
    examples = [
        EvalExample(
            example_id="struct_video_manifest",
            input_payload={"prompt": "Create storyboard scenes with duration in seconds"},
            expected_schema="scenes,duration_seconds,aspect_ratio",
            expected_output={"scenes": 3},
            min_quality_score=0.9,
        ),
    ]
    chash = EvalDatasetContract.compute_content_hash(examples)
    return EvalDatasetContract(
        dataset_id="eval_dataset_structured_outputs",
        version=version,
        content_hash=chash,
        capability=CapabilityType.TEXT_GENERATION,
        description="Benchmark dataset for JSON schema conformity and structured responses",
        examples=examples,
    )


def build_speech_dataset(version: str = "1.0.0") -> EvalDatasetContract:
    examples = [
        EvalExample(
            example_id="speech_stt_contract_probe",
            input_payload={"audio_ref": "storage://fixtures/speech_probe.wav"},
            expected_schema="transcript,words,confidence",
            min_quality_score=0.8,
        ),
    ]
    chash = EvalDatasetContract.compute_content_hash(examples)
    return EvalDatasetContract(
        dataset_id="eval_dataset_speech",
        version=version,
        content_hash=chash,
        capability=CapabilityType.SPEECH_TO_TEXT,
        description="Contract and structural validation probe for Speech subsystem (Real Quality DEFERRED)",
        examples=examples,
    )


def build_vision_dataset(version: str = "1.0.0") -> EvalDatasetContract:
    examples = [
        EvalExample(
            example_id="vision_shot_contract_probe",
            input_payload={"video_ref": "storage://fixtures/shot_probe.mp4"},
            expected_schema="shots,cut_timestamps",
            min_quality_score=0.8,
        ),
    ]
    chash = EvalDatasetContract.compute_content_hash(examples)
    return EvalDatasetContract(
        dataset_id="eval_dataset_vision",
        version=version,
        content_hash=chash,
        capability=CapabilityType.SHOT_DETECTION,
        description="Contract and structural validation probe for Vision subsystem (Real Quality DEFERRED)",
        examples=examples,
    )


def build_audio_dataset(version: str = "1.0.0") -> EvalDatasetContract:
    examples = [
        EvalExample(
            example_id="audio_dsp_contract_probe",
            input_payload={"audio_ref": "storage://fixtures/audio_probe.wav"},
            expected_schema="loudness_lufs,sample_rate,duration_seconds",
            min_quality_score=0.8,
        ),
    ]
    chash = EvalDatasetContract.compute_content_hash(examples)
    return EvalDatasetContract(
        dataset_id="eval_dataset_audio",
        version=version,
        content_hash=chash,
        capability=CapabilityType.AUDIO_ENHANCE,
        description="Contract and structural validation probe for Audio subsystem (Real Quality DEFERRED)",
        examples=examples,
    )


DATASET_BUILDERS = {
    "eval_dataset_routing": build_routing_dataset,
    "eval_dataset_planning": build_planning_dataset,
    "eval_dataset_memory_retrieval": build_memory_retrieval_dataset,
    "eval_dataset_tool_selection": build_tool_selection_dataset,
    "eval_dataset_structured_outputs": build_structured_outputs_dataset,
    "eval_dataset_speech": build_speech_dataset,
    "eval_dataset_vision": build_vision_dataset,
    "eval_dataset_audio": build_audio_dataset,
}


def get_dataset(dataset_id: str, version: str = "1.0.0") -> EvalDatasetContract:
    """Retrieves standard benchmark dataset by identifier."""
    if dataset_id not in DATASET_BUILDERS:
        raise KeyError(f"Unknown dataset identifier '{dataset_id}'.")
    return DATASET_BUILDERS[dataset_id](version=version)


def get_planning_dataset(version: str = "1.0.0") -> EvalDatasetContract:
    return build_planning_dataset(version=version)

