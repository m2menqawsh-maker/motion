#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/generate_ai_contracts.py
================================
Deterministic generator for AI subsystem JSON Schemas and TypeScript contracts.

Authority Chain (ADR-004 DEC-06.2):
    Pydantic Canonical Contracts (`ai/contracts/*.py`)
                ↓
    JSON Schema (`schemas/ai/*.schema.json`)
                ↓
    TypeScript Types (`contracts/generated/ai_contracts.ts`, `remotion-app/src/types/ai_contracts.ts`)

Modes:
- Generation mode:  python scripts/generate_ai_contracts.py
- Verification mode: python scripts/generate_ai_contracts.py --check
  (Exits with code 1 if generated artifacts have drifted or are missing)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Type

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VENV_PY = ROOT / ".venv" / "bin" / "python"
if VENV_PY.exists() and Path(sys.executable) != VENV_PY:
    try:
        import pydantic
    except ImportError:
        os.execv(str(VENV_PY), [str(VENV_PY)] + sys.argv)

from pydantic import BaseModel

from ai.contracts import (
    AIActivityRecord,
    ActivityStatus,
    AIContractModel,
    AIError,
    AIErrorCode,
    AIRequest,
    AIResponse,
    AIResponseStatus,
    AIRun,
    AIRunStatus,
    AIStep,
    AIStepStatus,
    CapabilityCategory,
    CapabilityDefinition,
    CapabilityFamily,
    CapabilityLifecycleStatus,
    CapabilityRequest,
    CapabilityResult,
    CapabilityStatus,
    CapabilityType,
    CostClass,
    CostEstimate,
    ExecutionClass,
    ExecutionMode,
    IdempotencyPolicy,
    IdempotencySemantics,
    ImplementationDescriptor,
    ImplementationStatus,
    LatencyClass,
    MediaIntelligence,
    MediaIntelligenceRef,
    MemoryEntry,
    MemoryQuery,
    MemoryResult,
    MemoryType,
    MigrationStrategy,
    ModelRequirement,
    ModelSelection,
    PrivacyRequirement,
    ProvenanceRecord,
    QualityTarget,
    RetryPolicy,
    SideEffectClass,
    SpeechIntelligence,
    TenantScope,
    ToolCall,
    ToolCallStatus,
    ToolResult,
    UsageRecord,
    UsageUnitRecord,
    AICacheEntry,
    CacheEntryStatus,
    VisualIntelligence,
    AudioIntelligence,
    TTSRequest,
    TTSResult,
    ImageGenerationRequest,
    ImageGenerationResult,
    VideoGenerationRequest,
    VideoGenerationResult,
    PersonSegmentationRequest,
    PersonSegmentationResult,
    BackgroundRemovalRequest,
    BackgroundRemovalResult,
    LipSyncRequest,
    LipSyncResult,
    UpscaleRequest,
    UpscaleResult,
    AudioDenoiseRequest,
    AudioDenoiseResult,
    AudioEnhanceRequest,
    AudioEnhanceResult,
    VocalIsolationRequest,
    VocalIsolationResult,
    PromptContract,
    PromptMetadata,
    PromptRenderRequest,
    PromptRenderResult,
    PromptStatus,
    TraceSpanRecord,
    AITrace,
    SpanType,
    CandidateType,
    EvaluatorType,
    ModelPromotionState,
    EvalExample,
    EvalDatasetContract,
    EvalResultContract,
    BenchmarkDebtContract,
    # Media Operations (S28-M02.1)
    AudioSegmentItem,
    DownloadedAssetItem,
    StockMediaItem,
    IconSearchResultItem,
    SpeechToTextInput,
    SegmentSpeechInput,
    SegmentSpeechOutput,
    SpeechManifestInput,
    SpeechManifestOutput,
    SpeechTimelineInput,
    SpeechTimelineOutput,
    SpeechTextSegmentItem,
    SplitSpeechTextInput,
    SplitSpeechTextOutput,
    PreparedVoSegmentItem,
    PrepareVoSegmentsInput,
    PrepareVoSegmentsOutput,
    AlignedWordItem,
    AlignedSegmentItem,
    AlignAudioMetadataInput,
    AlignAudioMetadataOutput,
    SilenceIntervalItem,
    DetectSilenceInput,
    DetectSilenceOutput,
    AnalyzeLoudnessInput,
    AnalyzeLoudnessOutput,
    NormalizeAudioInput,
    NormalizeAudioOutput,
    TrimAudioInput,
    TrimAudioOutput,
    ExtendAudioInput,
    ExtendAudioOutput,
    NormalizeLoudnessInput,
    NormalizeLoudnessOutput,
    TrimSilenceInput,
    TrimSilenceOutput,
    TrimVideoInput,
    TrimVideoOutput,
    ExtendVideoInput,
    ExtendVideoOutput,
    ResizeVideoInput,
    ResizeVideoOutput,
    DetectBlackFramesInput,
    DetectBlackFramesOutput,
    ChangeVideoSpeedInput,
    ChangeVideoSpeedOutput,
    EnforceKeyframesInput,
    EnforceKeyframesOutput,
    ConcatenateVideosInput,
    ConcatenateVideosOutput,
    UpscaleImageInput,
    UpscaleImageOutput,
    CropRatioInput,
    CropRatioOutput,
    AutoCropInput,
    AutoCropOutput,
    DownloadRemoteMediaInput,
    DownloadRemoteMediaOutput,
    ExtractMediaPageInput,
    ExtractMediaPageOutput,
    SearchIconsInput,
    SearchIconsOutput,
    DownloadIconInput,
    DownloadIconOutput,
    SearchStockImagesInput,
    SearchStockImagesOutput,
    SearchStockVideosInput,
    SearchStockVideosOutput,
    SearchStockAudioInput,
    SearchStockAudioOutput,
    SearchSoundEffectsInput,
    SearchSoundEffectsOutput,
    InspectMediaInput,
    InspectMediaOutput,
    MutateAssetStatusInput,
    MutateAssetStatusOutput,
    CheckCacheInput,
    CheckCacheOutput,
    StoreCacheInput,
    StoreCacheOutput,
    GetJobStatusInput,
    GetJobStatusOutput,
    CancelJobInput,
    CancelJobOutput,
)
from ai.image_processing.contracts import (
    ProbeImageRequest,
    ProbeImageResult,
    ResizeImageRequest,
    ResizeImageResult,
    CropImageRatioRequest,
    CropImageRatioResult,
    AutoCropImageRequest,
    AutoCropImageResult,
    ConvertImageRequest,
    ConvertImageResult,
    OptimizeImageRequest,
    OptimizeImageResult,
    PrepareImageAssetRequest,
    PrepareImageAssetResult,
    ThumbnailRequest,
    ThumbnailResult,
    ProbeImageInput,
    ProbeImageOutput,
    ResizeImageInput,
    ResizeImageOutput,
    CropImageRatioInput,
    CropImageRatioOutput,
    AutoCropImageInput,
    AutoCropImageOutput,
    ConvertImageInput,
    ConvertImageOutput,
    OptimizeImageInput,
    OptimizeImageOutput,
    PrepareImageAssetInput,
    PrepareImageAssetOutput,
    ThumbnailInput,
    ThumbnailOutput,
)


SCHEMA_DIR = ROOT / "schemas" / "ai"
TS_OUTPUT_CONTRACTS = ROOT / "contracts" / "generated" / "ai_contracts.ts"
TS_OUTPUT_REMOTION = ROOT / "remotion-app" / "src" / "types" / "ai_contracts.ts"

CANONICAL_MODELS: Dict[str, Type[BaseModel]] = {
    "ai_activity": AIActivityRecord,
    "ai_cache_entry": AICacheEntry,
    "ai_request": AIRequest,
    "ai_response": AIResponse,
    "ai_run": AIRun,
    "ai_step": AIStep,
    "capability_definition": CapabilityDefinition,
    "capability_request": CapabilityRequest,
    "capability_result": CapabilityResult,
    "implementation_descriptor": ImplementationDescriptor,
    "model_requirement": ModelRequirement,
    "model_selection": ModelSelection,
    "tool_call": ToolCall,
    "tool_result": ToolResult,
    "memory_query": MemoryQuery,
    "memory_result": MemoryResult,
    "media_intelligence": MediaIntelligence,
    "media_intelligence_ref": MediaIntelligenceRef,
    "speech_intelligence": SpeechIntelligence,
    "visual_intelligence": VisualIntelligence,
    "audio_intelligence": AudioIntelligence,
    "tts_request": TTSRequest,
    "tts_result": TTSResult,
    "image_generation_request": ImageGenerationRequest,
    "image_generation_result": ImageGenerationResult,
    "video_generation_request": VideoGenerationRequest,
    "video_generation_result": VideoGenerationResult,
    "person_segmentation_request": PersonSegmentationRequest,
    "person_segmentation_result": PersonSegmentationResult,
    "background_removal_request": BackgroundRemovalRequest,
    "background_removal_result": BackgroundRemovalResult,
    "lip_sync_request": LipSyncRequest,
    "lip_sync_result": LipSyncResult,
    "upscale_request": UpscaleRequest,
    "upscale_result": UpscaleResult,
    "audio_denoise_request": AudioDenoiseRequest,
    "audio_denoise_result": AudioDenoiseResult,
    "audio_enhance_request": AudioEnhanceRequest,
    "audio_enhance_result": AudioEnhanceResult,
    "vocal_isolation_request": VocalIsolationRequest,
    "vocal_isolation_result": VocalIsolationResult,
    "usage_record": UsageRecord,
    "cost_estimate": CostEstimate,
    "ai_error": AIError,
    "prompt_contract": PromptContract,
    "prompt_metadata": PromptMetadata,
    "prompt_render_request": PromptRenderRequest,
    "prompt_render_result": PromptRenderResult,
    "trace_span_record": TraceSpanRecord,
    "ai_trace": AITrace,
    "eval_example": EvalExample,
    "eval_dataset": EvalDatasetContract,
    "eval_result": EvalResultContract,
    "benchmark_debt": BenchmarkDebtContract,
    "audio_segment_item": AudioSegmentItem,
    "downloaded_asset_item": DownloadedAssetItem,
    "stock_media_item": StockMediaItem,
    "icon_search_result_item": IconSearchResultItem,
    "speech_to_text_input": SpeechToTextInput,
    "segment_speech_input": SegmentSpeechInput,
    "segment_speech_output": SegmentSpeechOutput,
    "speech_manifest_input": SpeechManifestInput,
    "speech_manifest_output": SpeechManifestOutput,
    "speech_timeline_input": SpeechTimelineInput,
    "speech_timeline_output": SpeechTimelineOutput,
    "speech_text_segment_item": SpeechTextSegmentItem,
    "split_speech_text_input": SplitSpeechTextInput,
    "split_speech_text_output": SplitSpeechTextOutput,
    "prepared_vo_segment_item": PreparedVoSegmentItem,
    "prepare_vo_segments_input": PrepareVoSegmentsInput,
    "prepare_vo_segments_output": PrepareVoSegmentsOutput,
    "aligned_word_item": AlignedWordItem,
    "aligned_segment_item": AlignedSegmentItem,
    "align_audio_metadata_input": AlignAudioMetadataInput,
    "align_audio_metadata_output": AlignAudioMetadataOutput,
    "silence_interval_item": SilenceIntervalItem,
    "detect_silence_input": DetectSilenceInput,
    "detect_silence_output": DetectSilenceOutput,
    "analyze_loudness_input": AnalyzeLoudnessInput,
    "analyze_loudness_output": AnalyzeLoudnessOutput,
    "normalize_audio_input": NormalizeAudioInput,
    "normalize_audio_output": NormalizeAudioOutput,
    "trim_audio_input": TrimAudioInput,
    "trim_audio_output": TrimAudioOutput,
    "extend_audio_input": ExtendAudioInput,
    "extend_audio_output": ExtendAudioOutput,
    "normalize_loudness_input": NormalizeLoudnessInput,
    "normalize_loudness_output": NormalizeLoudnessOutput,
    "trim_silence_input": TrimSilenceInput,
    "trim_silence_output": TrimSilenceOutput,
    "trim_video_input": TrimVideoInput,
    "trim_video_output": TrimVideoOutput,
    "extend_video_input": ExtendVideoInput,
    "extend_video_output": ExtendVideoOutput,
    "resize_video_input": ResizeVideoInput,
    "resize_video_output": ResizeVideoOutput,
    "detect_black_frames_input": DetectBlackFramesInput,
    "detect_black_frames_output": DetectBlackFramesOutput,
    "change_video_speed_input": ChangeVideoSpeedInput,
    "change_video_speed_output": ChangeVideoSpeedOutput,
    "enforce_keyframes_input": EnforceKeyframesInput,
    "enforce_keyframes_output": EnforceKeyframesOutput,
    "concatenate_videos_input": ConcatenateVideosInput,
    "concatenate_videos_output": ConcatenateVideosOutput,
    "upscale_image_input": UpscaleImageInput,
    "upscale_image_output": UpscaleImageOutput,
    "crop_ratio_input": CropRatioInput,
    "crop_ratio_output": CropRatioOutput,
    "auto_crop_input": AutoCropInput,
    "auto_crop_output": AutoCropOutput,
    "probe_image_input": ProbeImageInput,
    "probe_image_output": ProbeImageOutput,
    "convert_image_input": ConvertImageInput,
    "convert_image_output": ConvertImageOutput,
    "optimize_image_input": OptimizeImageInput,
    "optimize_image_output": OptimizeImageOutput,
    "prepare_image_asset_input": PrepareImageAssetInput,
    "prepare_image_asset_output": PrepareImageAssetOutput,
    "thumbnail_input": ThumbnailInput,
    "thumbnail_output": ThumbnailOutput,
    "probe_image_request": ProbeImageRequest,
    "probe_image_result": ProbeImageResult,
    "resize_image_request": ResizeImageRequest,
    "resize_image_result": ResizeImageResult,
    "crop_image_ratio_request": CropImageRatioRequest,
    "crop_image_ratio_result": CropImageRatioResult,
    "auto_crop_image_request": AutoCropImageRequest,
    "auto_crop_image_result": AutoCropImageResult,
    "convert_image_request": ConvertImageRequest,
    "convert_image_result": ConvertImageResult,
    "optimize_image_request": OptimizeImageRequest,
    "optimize_image_result": OptimizeImageResult,
    "prepare_image_asset_request": PrepareImageAssetRequest,
    "prepare_image_asset_result": PrepareImageAssetResult,
    "thumbnail_request": ThumbnailRequest,
    "thumbnail_result": ThumbnailResult,
    "download_remote_media_input": DownloadRemoteMediaInput,
    "download_remote_media_output": DownloadRemoteMediaOutput,
    "extract_media_page_input": ExtractMediaPageInput,
    "extract_media_page_output": ExtractMediaPageOutput,
    "search_icons_input": SearchIconsInput,
    "search_icons_output": SearchIconsOutput,
    "download_icon_input": DownloadIconInput,
    "download_icon_output": DownloadIconOutput,
    "search_stock_images_input": SearchStockImagesInput,
    "search_stock_images_output": SearchStockImagesOutput,
    "search_stock_videos_input": SearchStockVideosInput,
    "search_stock_videos_output": SearchStockVideosOutput,
    "search_stock_audio_input": SearchStockAudioInput,
    "search_stock_audio_output": SearchStockAudioOutput,
    "search_sound_effects_input": SearchSoundEffectsInput,
    "search_sound_effects_output": SearchSoundEffectsOutput,
    "inspect_media_input": InspectMediaInput,
    "inspect_media_output": InspectMediaOutput,
    "mutate_asset_status_input": MutateAssetStatusInput,
    "mutate_asset_status_output": MutateAssetStatusOutput,
    "check_cache_input": CheckCacheInput,
    "check_cache_output": CheckCacheOutput,
    "store_cache_input": StoreCacheInput,
    "store_cache_output": StoreCacheOutput,
    "get_job_status_input": GetJobStatusInput,
    "get_job_status_output": GetJobStatusOutput,
    "cancel_job_input": CancelJobInput,
    "cancel_job_output": CancelJobOutput,
}



def serialize_json_deterministic(data: Dict) -> str:
    """Serializes data structure into deterministic formatted JSON with sorted keys."""
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def generate_json_schemas() -> Dict[Path, str]:
    """Generates deterministic JSON Schema strings for each canonical contract."""
    files: Dict[Path, str] = {}

    bundled_defs = {}
    for name, model_cls in sorted(CANONICAL_MODELS.items()):
        schema = model_cls.model_json_schema()
        # Collect defs for consolidated schema
        if "$defs" in schema:
            bundled_defs.update(schema["$defs"])
        bundled_defs[model_cls.__name__] = schema

        out_path = SCHEMA_DIR / f"{name}.schema.json"
        files[out_path] = serialize_json_deterministic(schema)

    # Consolidated bundle schema
    bundle = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "AIContractsBundle",
        "description": "Consolidated schema bundle for AI Subsystem Canonical Contracts (S27.1)",
        "$defs": bundled_defs,
    }
    files[SCHEMA_DIR / "ai_contracts.schema.json"] = serialize_json_deterministic(bundle)

    return files


def generate_typescript_content() -> str:
    """
    Generates deterministic TypeScript type definitions directly from canonical Python authority.
    Includes strict enum unions, base JSON types, and interfaces for all models.
    """
    lines: List[str] = [
        "/* eslint-disable */",
        "// ============================================================================",
        "// GENERATED FILE — DO NOT EDIT MANUALLY",
        "// Generated by scripts/generate_ai_contracts.py from ai/contracts",
        "// Single Authority: Python Pydantic Models (ai/contracts/*.py)",
        "// ============================================================================",
        "",
        "/** Generic JSON value representation strictly preventing unrestricted arbitrary objects. */",
        "export type JsonValue =",
        "  | string",
        "  | number",
        "  | boolean",
        "  | null",
        "  | JsonValue[]",
        "  | { [key: string]: JsonValue };",
        "",
        "/** ISO 8601 timezone-aware UTC datetime string (e.g. '2026-09-30T17:00:00Z'). */",
        "export type TzAwareDatetime = string;",
        "",
    ]

    # Enums to emit
    enums = [
        ("ExecutionClass", ExecutionClass),
        ("PrivacyRequirement", PrivacyRequirement),
        ("QualityTarget", QualityTarget),
        ("CapabilityType", CapabilityType),
        ("CapabilityStatus", CapabilityStatus),
        ("AIErrorCode", AIErrorCode),
        ("AIResponseStatus", AIResponseStatus),
        ("AIRunStatus", AIRunStatus),
        ("AIStepStatus", AIStepStatus),
        ("ToolCallStatus", ToolCallStatus),
        ("MemoryType", MemoryType),
        ("ActivityStatus", ActivityStatus),
        ("IdempotencySemantics", IdempotencySemantics),
        ("CacheEntryStatus", CacheEntryStatus),
        ("PromptStatus", PromptStatus),
        ("SpanType", SpanType),
        ("CandidateType", CandidateType),
        ("EvaluatorType", EvaluatorType),
        ("ModelPromotionState", ModelPromotionState),
        ("CapabilityCategory", CapabilityCategory),
        ("CapabilityFamily", CapabilityFamily),
        ("SideEffectClass", SideEffectClass),
        ("TenantScope", TenantScope),
        ("ExecutionMode", ExecutionMode),
        ("CostClass", CostClass),
        ("LatencyClass", LatencyClass),
        ("RetryPolicy", RetryPolicy),
        ("IdempotencyPolicy", IdempotencyPolicy),
        ("ImplementationStatus", ImplementationStatus),
        ("MigrationStrategy", MigrationStrategy),
        ("CapabilityLifecycleStatus", CapabilityLifecycleStatus),
    ]

    for enum_name, enum_cls in enums:
        members = [f'"{m.value}"' for m in enum_cls]
        union_str = " | ".join(members)
        lines.append(f"export type {enum_name} = {union_str};")
        lines.append("")

    # Emit interfaces
    interfaces_code = """
export interface ProvenanceRecord {
  source: string;
  model_id?: string | null;
  provider_id?: string | null;
  timestamp: TzAwareDatetime;
  latency_ms?: number | null;
}

export interface UsageUnitRecord {
  unit_type: string;
  quantity: number | string;
}

export interface UsageRecord {
  input_tokens?: number | null;
  output_tokens?: number | null;
  total_tokens?: number | null;
  audio_seconds?: number | string | null;
  video_seconds?: number | string | null;
  image_count?: number | null;
  reported_units?: UsageUnitRecord[] | null;
}

export interface CostEstimate {
  estimated_cost: number | string;
  reserved_cost?: number | string | null;
  actual_cost?: number | string | null;
  currency?: string;
  pricing_version?: string | null;
}

export interface AIError {
  code: AIErrorCode;
  message: string;
  retryable: boolean;
  details?: Record<string, JsonValue> | null;
  dependency_reference?: string | null;
}

export interface ModelRequirement {
  capability: CapabilityType;
  quality_target?: QualityTarget;
  budget_constraint?: CostEstimate | null;
  max_latency_ms?: number | null;
  language?: string | null;
  privacy_requirement?: PrivacyRequirement;
  media_type?: string | null;
  required_features?: string[];
  execution_class?: ExecutionClass | null;
}

export interface ModelSelection {
  primary_model: string;
  fallback_candidates?: string[];
  reason_code: string;
  estimated_cost: CostEstimate;
}

export interface CapabilityRequest {
  request_id?: string;
  capability_id: CapabilityType;
  capability?: CapabilityType;
  capability_version?: string;
  workspace_id?: string | null;
  project_id?: string | null;
  actor_id?: string | null;
  tenant_context?: Record<string, JsonValue> | null;
  input?: Record<string, JsonValue>;
  input_data?: Record<string, JsonValue>;
  idempotency_key?: string | null;
  correlation_id?: string | null;
  requested_timeout?: number | null;
  metadata?: Record<string, JsonValue>;
  requirements?: ModelRequirement | null;
  contract_version?: string;
}

export interface CapabilityResult {
  request_id?: string | null;
  capability_id: CapabilityType;
  capability?: CapabilityType;
  status: CapabilityStatus;
  output?: Record<string, JsonValue> | null;
  output_data?: Record<string, JsonValue> | null;
  execution_metadata?: Record<string, JsonValue>;
  implementation_id?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  duration_ms?: number | null;
  confidence?: number | null;
  provenance?: ProvenanceRecord | null;
  usage?: UsageRecord;
  error?: AIError | null;
}

export interface ImplementationDescriptor {
  implementation_id: string;
  implementation_kind: string;
  current_status: ImplementationStatus;
  source: string;
  provider_or_engine: string;
  constraints?: string[];
  known_issues?: string[];
  legacy_storage_behavior?: string | null;
}

export interface CapabilityDefinition {
  capability_id: CapabilityType;
  version?: string;
  name: string;
  description: string;
  category: CapabilityCategory;
  family: CapabilityFamily;
  input_contract: string;
  output_contract: string;
  side_effects: SideEffectClass[];
  side_effect_class: SideEffectClass;
  target_storage_boundary?: string;
  required_permissions?: string[];
  tenant_scope?: TenantScope;
  execution_mode?: ExecutionMode;
  timeout_seconds?: number;
  retry_policy?: RetryPolicy;
  idempotency_policy?: IdempotencyPolicy;
  cost_class?: CostClass;
  latency_class?: LatencyClass;
  implementations?: ImplementationDescriptor[];
  status?: CapabilityLifecycleStatus;
  owner: string;
}

export interface AudioSegmentItem {
  segment_id: string;
  storage_key: string;
  start_seconds: number;
  end_seconds: number;
  text?: string | null;
}

export interface DownloadedAssetItem {
  asset_id: string;
  storage_key: string;
  source_url: string;
  content_type: string;
  file_size_bytes: number;
}

export interface StockMediaItem {
  media_id: string;
  media_type: string;
  title?: string | null;
  preview_url?: string | null;
  download_url?: string | null;
  width?: number | null;
  height?: number | null;
  duration_seconds?: number | null;
  license?: string | null;
}

export interface IconSearchResultItem {
  icon_name: string;
  collection: string;
  name: string;
  svg_preview?: string | null;
}

export interface SpeechToTextInput {
  project_id: string;
  audio_storage_key: string;
  language?: string | null;
  model_size?: string | null;
  detect_speakers?: boolean;
}

export interface SegmentSpeechInput {
  project_id: string;
  audio_storage_key: string;
  segments?: SpeechSegment[] | null;
  min_duration_seconds?: number;
  max_duration_seconds?: number;
}

export interface SegmentSpeechOutput {
  project_id: string;
  slices: AudioSegmentItem[];
  total_segments: number;
}

export interface SpeechManifestInput {
  project_id: string;
  audio_storage_key: string;
  manifest_version?: string;
}

export interface SpeechManifestOutput {
  project_id: string;
  manifest_storage_key: string;
  sentence_count: number;
  total_duration_seconds: number;
  words_count: number;
}

export interface SpeechTimelineInput {
  project_id: string;
  audio_storage_key: string;
  fps?: number;
}

export interface SpeechTimelineOutput {
  project_id: string;
  timeline_storage_key: string;
  total_frames: number;
  cue_points_count: number;
}

export interface SpeechTextSegmentItem {
  index: number;
  text: string;
  start_seconds?: number | null;
  end_seconds?: number | null;
  duration_seconds?: number | null;
  split_reason?: string;
  word_count: number;
}

export interface SplitSpeechTextInput {
  text: string;
  language?: string | null;
  min_sentence_duration?: number;
  max_sentence_duration?: number;
  silence_threshold?: number;
}

export interface SplitSpeechTextOutput {
  segments: SpeechTextSegmentItem[];
  total_segments: number;
  total_words: number;
  language?: string | null;
}

export interface PreparedVoSegmentItem {
  segment_id: string;
  index: number;
  text: string;
  estimated_duration_seconds: number;
  voice_id?: string | null;
  audio_mode?: string;
}

export interface PrepareVoSegmentsInput {
  project_id: string;
  text_segments: string[];
  voice_id?: string | null;
  audio_mode?: string;
  speaking_rate?: number;
}

export interface PrepareVoSegmentsOutput {
  project_id: string;
  segments: PreparedVoSegmentItem[];
  total_segments: number;
  total_estimated_duration_seconds: number;
  audio_mode: string;
}

export interface AlignedWordItem {
  word: string;
  start_seconds: number;
  end_seconds: number;
  duration_seconds: number;
  confidence?: number | null;
}

export interface AlignedSegmentItem {
  segment_id: string;
  index: number;
  text: string;
  start_seconds: number;
  end_seconds: number;
  duration_seconds: number;
  words: AlignedWordItem[];
}

export interface AlignAudioMetadataInput {
  project_id: string;
  audio_storage_key: string;
  transcript: string;
  words: AlignedWordItem[];
  audio_duration_seconds: number;
}

export interface AlignAudioMetadataOutput {
  project_id: string;
  segments: AlignedSegmentItem[];
  total_words: number;
  covered_duration_seconds: number;
  audio_duration_seconds: number;
  coverage_ratio: number;
  is_valid?: boolean;
}

export interface SilenceIntervalItem {
  start_seconds: number;
  end_seconds: number;
  duration_seconds: number;
}

export interface DetectSilenceInput {
  project_id: string;
  audio_storage_key: string;
  threshold_db?: number;
  min_silence_duration_seconds?: number;
}

export interface DetectSilenceOutput {
  project_id: string;
  audio_storage_key: string;
  silence_intervals: SilenceIntervalItem[];
  total_silence_duration_seconds: number;
  audio_duration_seconds: number;
  silence_ratio: number;
  threshold_used_db: number;
}

export interface AnalyzeLoudnessInput {
  project_id: string;
  audio_storage_key: string;
}

export interface AnalyzeLoudnessOutput {
  project_id: string;
  audio_storage_key: string;
  integrated_lufs: number;
  loudness_range: number;
  true_peak_db: number;
  threshold_db?: number | null;
  measurement_standard: string;
  duration_seconds: number;
}

export interface NormalizeAudioInput {
  project_id: string;
  audio_storage_key: string;
  target_lufs?: number;
  true_peak_db?: number;
  loudness_range?: number;
  sample_rate?: number;
}

export interface NormalizeAudioOutput {
  project_id: string;
  output_storage_key: string;
  target_lufs: number;
  measured_lufs: number;
  duration_seconds: number;
  file_size_bytes: number;
}

export interface TrimAudioInput {
  project_id: string;
  audio_storage_key: string;
  target_duration_seconds: number;
}

export interface TrimAudioOutput {
  project_id: string;
  output_storage_key: string;
  duration_seconds: number;
}

export interface ExtendAudioInput {
  project_id: string;
  audio_storage_key: string;
  target_duration_seconds: number;
  mode?: string;
  fade_duration_seconds?: number;
  auto_trim_silence?: boolean;
}

export interface ExtendAudioOutput {
  project_id: string;
  output_storage_key: string;
  duration_seconds: number;
  loop_count: number;
}

export interface NormalizeLoudnessInput {
  project_id: string;
  audio_storage_key: string;
  target_lufs?: number;
  peak_limit_db?: number;
}

export interface NormalizeLoudnessOutput {
  project_id: string;
  output_storage_key: string;
  measured_lufs: number;
  normalization_applied?: boolean;
}

export interface TrimSilenceInput {
  project_id: string;
  audio_storage_key: string;
  silence_threshold_db?: number;
  min_silence_duration_seconds?: number;
}

export interface TrimSilenceOutput {
  project_id: string;
  output_storage_key: string;
  original_duration_seconds: number;
  trimmed_duration_seconds: number;
  trimmed_start_seconds: number;
  trimmed_end_seconds: number;
}

export interface TrimVideoInput {
  project_id: string;
  video_storage_key: string;
  start_time_seconds?: number;
  duration_seconds: number;
}

export interface TrimVideoOutput {
  project_id: string;
  output_storage_key: string;
  duration_seconds: number;
}

export interface ExtendVideoInput {
  project_id: string;
  video_storage_key: string;
  target_duration_seconds: number;
  mode?: string;
}

export interface ExtendVideoOutput {
  project_id: string;
  output_storage_key: string;
  duration_seconds: number;
  loop_count: number;
}

export interface ResizeVideoInput {
  project_id: string;
  video_storage_key: string;
  target_width: number;
  target_height: number;
  mode?: string;
}

export interface ResizeVideoOutput {
  project_id: string;
  output_storage_key: string;
  width: number;
  height: number;
}

export interface DetectBlackFramesInput {
  project_id: string;
  video_storage_key: string;
  black_ratio_threshold?: number;
  black_pixel_threshold?: number;
}

export interface DetectBlackFramesOutput {
  project_id: string;
  output_storage_key: string;
  original_duration_seconds: number;
  trimmed_duration_seconds: number;
  black_segments_count: number;
}

export interface ChangeVideoSpeedInput {
  project_id: string;
  video_storage_key: string;
  speed_factor: number;
  run_in_background?: boolean;
}

export interface ChangeVideoSpeedOutput {
  project_id: string;
  output_storage_key?: string | null;
  job_id?: string | null;
  is_async?: boolean;
}

export interface EnforceKeyframesInput {
  project_id: string;
  video_storage_key: string;
  keyframe_interval?: number;
}

export interface EnforceKeyframesOutput {
  project_id: string;
  output_storage_key: string;
  keyframe_interval: number;
}

export interface ConcatenateVideosInput {
  project_id: string;
  video_storage_keys: string[];
  transition?: string | null;
}

export interface ConcatenateVideosOutput {
  project_id: string;
  output_storage_key: string;
  total_duration_seconds: number;
  input_count: number;
}

export interface UpscaleImageInput {
  project_id: string;
  image_storage_key: string;
  scale_factor?: number;
  target_width?: number | null;
  target_height?: number | null;
}

export interface UpscaleImageOutput {
  project_id: string;
  output_storage_key: string;
  width: number;
  height: number;
}

export interface CropRatioInput {
  project_id: string;
  image_storage_key: string;
  aspect_ratio?: string;
}

export interface CropRatioOutput {
  project_id: string;
  output_storage_key: string;
  width: number;
  height: number;
  aspect_ratio: string;
}

export interface AutoCropInput {
  project_id: string;
  image_storage_key: string;
  padding_ratio?: number;
}

export interface AutoCropOutput {
  project_id: string;
  output_storage_key: string;
  cropped_box: number[];
  original_width: number;
  original_height: number;
  output_width: number;
  output_height: number;
}

export interface DownloadRemoteMediaInput {
  project_id: string;
  url: string;
  media_type?: string;
  destination_asset_id?: string | null;
}

export interface DownloadRemoteMediaOutput {
  project_id: string;
  asset_id: string;
  storage_key: string;
  file_size_bytes: number;
  content_type: string;
}

export interface ExtractMediaPageInput {
  project_id: string;
  page_url: string;
  media_type?: string;
}

export interface ExtractMediaPageOutput {
  project_id: string;
  extracted_assets: DownloadedAssetItem[];
  total_extracted: number;
}

export interface SearchIconsInput {
  query: string;
  limit?: number;
  collection?: string | null;
}

export interface SearchIconsOutput {
  query: string;
  icons: IconSearchResultItem[];
  total_found: number;
}

export interface DownloadIconInput {
  project_id: string;
  icon_name: string;
  color?: string | null;
  size?: number;
}

export interface DownloadIconOutput {
  project_id: string;
  asset_id: string;
  storage_key: string;
  format?: string;
}

export interface SearchStockImagesInput {
  query: string;
  page?: number;
  per_page?: number;
  orientation?: string | null;
}

export interface SearchStockImagesOutput {
  query: string;
  images: StockMediaItem[];
  page: number;
  total_results: number;
}

export interface SearchStockVideosInput {
  query: string;
  page?: number;
  per_page?: number;
  orientation?: string | null;
}

export interface SearchStockVideosOutput {
  query: string;
  videos: StockMediaItem[];
  page: number;
  total_results: number;
}

export interface SearchStockAudioInput {
  query: string;
  page?: number;
  per_page?: number;
}

export interface SearchStockAudioOutput {
  query: string;
  audio_tracks: StockMediaItem[];
  page: number;
  total_results: number;
}

export interface SearchSoundEffectsInput {
  query: string;
  page?: number;
  per_page?: number;
  duration_range?: number[] | null;
}

export interface SearchSoundEffectsOutput {
  query: string;
  sound_effects: StockMediaItem[];
  page: number;
  total_results: number;
}

export interface InspectMediaInput {
  project_id: string;
  storage_keys: string[];
}

export interface InspectMediaOutput {
  project_id: string;
  files_info: TechnicalMetadata[];
}

export interface MutateAssetStatusInput {
  project_id: string;
  asset_id: string;
  new_status: string;
  reason?: string | null;
}

export interface MutateAssetStatusOutput {
  project_id: string;
  asset_id: string;
  previous_status: string;
  current_status: string;
  manifest_updated?: boolean;
}

export interface CheckCacheInput {
  project_id: string;
  asset_id: string;
  transformation_hash: string;
}

export interface CheckCacheOutput {
  project_id: string;
  asset_id: string;
  transformation_hash: string;
  cache_hit: boolean;
  cached_storage_key?: string | null;
}

export interface StoreCacheInput {
  project_id: string;
  asset_id: string;
  transformation_hash: string;
  source_storage_key: string;
}

export interface StoreCacheOutput {
  project_id: string;
  asset_id: string;
  transformation_hash: string;
  cached_storage_key: string;
  stored?: boolean;
}

export interface GetJobStatusInput {
  project_id: string;
  job_id: string;
}

export interface GetJobStatusOutput {
  project_id: string;
  job_id: string;
  status: string;
  progress_percent?: number;
  output_storage_key?: string | null;
  error?: string | null;
}

export interface CancelJobInput {
  project_id: string;
  job_id: string;
  reason?: string | null;
}

export interface CancelJobOutput {
  project_id: string;
  job_id: string;
  cancelled: boolean;
  termination_status: string;
}

export interface ToolCall {
  call_id: string;
  tool_name: string;
  parameters?: Record<string, JsonValue>;
  untrusted_metadata?: Record<string, JsonValue> | null;
}

export interface ToolResult {
  call_id: string;
  status: ToolCallStatus;
  output?: Record<string, JsonValue> | null;
  error?: AIError | null;
  started_at: TzAwareDatetime;
  completed_at: TzAwareDatetime;
  duration_ms: number;
}

export interface MemoryQuery {
  workspace_id: string;
  project_id?: string | null;
  session_id?: string | null;
  memory_type: MemoryType;
  query_text: string;
  limit?: number;
  minimum_confidence?: number;
}

export interface MemoryEntry {
  entry_id: string;
  memory_type: MemoryType;
  content: string;
  relevance_score: number;
  confidence: number;
  provenance: ProvenanceRecord;
  created_at: TzAwareDatetime;
}

export interface MemoryResult {
  entries?: MemoryEntry[];
  total_found: number;
  query_duration_ms: number;
}

export interface MediaIntelligenceRef {
  artifact_id: string;
  asset_id: string;
  analysis_version?: string;
  content_hash: string;
  storage_key: string;
  created_at: TzAwareDatetime;
}

export interface AnalysisProvenance {
  producer: string;
  provider?: string | null;
  model?: string | null;
  version?: string | null;
  confidence?: number | null;
  timestamp: TzAwareDatetime;
  analysis_version?: string;
  contract_version?: string;
}

export interface TechnicalMetadata {
  format?: string | null;
  duration_seconds?: number | null;
  file_size_bytes?: number | null;
  has_audio: boolean;
  has_video: boolean;
  audio_channels?: number | null;
  audio_sample_rate?: number | null;
  audio_bitrate?: number | null;
  audio_codec?: string | null;
  width?: number | null;
  height?: number | null;
  fps?: number | null;
  video_codec?: string | null;
  provenance?: AnalysisProvenance | null;
}

export interface SpeechWord {
  text: string;
  start: number;
  end: number;
  speaker_id?: string | null;
  confidence?: number | null;
  language?: string | null;
}

export interface SpeechSegment {
  id?: string | null;
  start: number;
  end: number;
  text: string;
  speaker_id?: string | null;
  confidence?: number | null;
  language?: string | null;
  words?: SpeechWord[];
}

export interface SpeechSpeaker {
  speaker_id: string;
  label?: string | null;
  confidence?: number | null;
  total_speaking_time_seconds?: number | null;
}

export interface SpeechQuality {
  speech_snr_db?: number | null;
  audio_clarity_score?: number | null;
  clipping_detected?: boolean | null;
  silence_percentage?: number | null;
}

export interface SpeechIntelligence {
  language?: string | null;
  language_confidence?: number | null;
  transcript: string;
  segments?: SpeechSegment[];
  words?: SpeechWord[];
  speakers?: SpeechSpeaker[];
  duration_seconds?: number | null;
  overall_confidence?: number | null;
  provenance: AnalysisProvenance;
}

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface VideoShot {
  shot_id: string;
  start: number;
  end: number;
  duration: number;
  confidence?: number | null;
  source?: string;
  transition_type?: string | null;
  keyframe_indices?: number[];
  provenance?: AnalysisProvenance | null;
}

export interface Keyframe {
  keyframe_id: string;
  shot_id?: string | null;
  timestamp: number;
  frame_index: number;
  storage_key?: string | null;
  width?: number | null;
  height?: number | null;
  is_representative?: boolean;
  resolution_tier?: string;
  content_hash?: string | null;
  provenance?: AnalysisProvenance | null;
}

export interface VisualOCRObservation {
  text: string;
  bounding_box?: BoundingBox | null;
  timestamp: number;
  frame_ref?: string | null;
  confidence: number;
  language?: string | null;
  is_ui_screen?: boolean;
  provenance: AnalysisProvenance;
}

export interface VisualObjectObservation {
  label: string;
  bounding_box?: BoundingBox | null;
  timestamp: number;
  frame_ref?: string | null;
  confidence: number;
  provenance: AnalysisProvenance;
}

export interface VisualPersonObservation {
  person_id: string;
  bounding_box?: BoundingBox | null;
  timestamp: number;
  frame_ref?: string | null;
  confidence: number;
  provenance: AnalysisProvenance;
}

export interface VisualSceneClassification {
  label: string;
  start: number;
  end: number;
  confidence: number;
  resolution_tier?: string;
  provenance: AnalysisProvenance;
}

export interface VisualObservation {
  summary: string;
  start: number;
  end: number;
  importance_score?: number | null;
  category?: string | null;
  provenance: AnalysisProvenance;
}

export interface VisualIntelligence {
  status?: string;
  has_visual_analysis?: boolean;
  shots?: VideoShot[];
  keyframes?: Keyframe[];
  ocr?: VisualOCRObservation[];
  objects?: VisualObjectObservation[];
  people?: VisualPersonObservation[];
  scene_classifications?: VisualSceneClassification[];
  observations?: VisualObservation[];
  provenance?: AnalysisProvenance | null;
}

export type VisualIntelligenceFoundation = VisualIntelligence;

export interface TimeRange {
  start: number;
  end: number;
  confidence?: number | null;
  label?: string | null;
}

export interface AudioLoudnessMetrics {
  integrated_lufs?: number | null;
  momentary_max_lufs?: number | null;
  rms_db?: number | null;
  peak_db?: number | null;
  clipping_detected?: boolean;
  clipping_events_count?: number;
  provenance?: AnalysisProvenance | null;
}

export interface AudioNoiseEstimate {
  snr_db?: number | null;
  noise_floor_db?: number | null;
  noise_profile_label?: string | null;
  confidence?: number | null;
  provenance?: AnalysisProvenance | null;
}

export interface AudioBeatTrack {
  tempo_bpm?: number | null;
  beat_timestamps?: number[];
  confidence?: number | null;
  provenance?: AnalysisProvenance | null;
}

export interface AudioQualityObservation {
  metric_name: string;
  score: number;
  details?: string | null;
  provenance?: AnalysisProvenance | null;
}

export interface AudioIntelligence {
  status?: string;
  has_audio_analysis?: boolean;
  speech_ranges?: TimeRange[];
  silence_ranges?: TimeRange[];
  loudness?: AudioLoudnessMetrics | null;
  noise_estimate?: AudioNoiseEstimate | null;
  beats?: AudioBeatTrack | null;
  music_ranges?: TimeRange[];
  quality_observations?: AudioQualityObservation[];
  noise_profile?: string | null;
  tempo_bpm?: number | null;
  beat_timestamps?: number[];
  vocal_isolation_ref?: string | null;
  provenance?: AnalysisProvenance | null;
}

export type AudioIntelligenceFoundation = AudioIntelligence;

// Specialized Media AI Operations
export interface TTSRequest {
  text: string;
  voice_id: string;
  language?: string | null;
  speed?: number | null;
  pitch?: number | null;
  format?: string;
}

export interface TTSResult {
  audio_storage_key: string;
  audio_hash: string;
  duration_seconds: number;
  sample_rate: number;
  format?: string;
  provenance: AnalysisProvenance;
}

export interface ImageGenerationRequest {
  prompt: string;
  negative_prompt?: string | null;
  width?: number;
  height?: number;
  style?: string | null;
  seed?: number | null;
}

export interface ImageGenerationResult {
  image_storage_key: string;
  image_hash: string;
  width: number;
  height: number;
  format?: string;
  provenance: AnalysisProvenance;
}

export interface VideoGenerationRequest {
  prompt: string;
  duration_seconds?: number;
  fps?: number;
  width?: number;
  height?: number;
  input_frame_storage_key?: string | null;
  seed?: number | null;
}

export interface VideoGenerationResult {
  video_storage_key: string;
  video_hash: string;
  duration_seconds: number;
  fps: number;
  width: number;
  height: number;
  format?: string;
  provenance: AnalysisProvenance;
}

export interface PersonSegmentationRequest {
  image_storage_key: string;
  content_hash: string;
  return_mask?: boolean;
  threshold?: number;
}

export interface PersonSegmentationResult {
  mask_storage_key: string;
  mask_hash: string;
  person_count?: number;
  confidence: number;
  provenance: AnalysisProvenance;
}

export interface BackgroundRemovalRequest {
  image_storage_key: string;
  content_hash: string;
  output_format?: string;
}

export interface BackgroundRemovalResult {
  output_storage_key: string;
  output_hash: string;
  format?: string;
  provenance: AnalysisProvenance;
}

export interface LipSyncRequest {
  video_storage_key: string;
  audio_storage_key: string;
  content_hash: string;
}

export interface LipSyncResult {
  output_video_storage_key: string;
  output_video_hash: string;
  duration_seconds: number;
  sync_confidence: number;
  provenance: AnalysisProvenance;
}

export interface UpscaleRequest {
  media_storage_key: string;
  content_hash: string;
  scale_factor?: number;
  target_width?: number | null;
  target_height?: number | null;
}

export interface UpscaleResult {
  output_storage_key: string;
  output_hash: string;
  width: number;
  height: number;
  provenance: AnalysisProvenance;
}

export interface AudioDenoiseRequest {
  audio_storage_key: string;
  content_hash: string;
  aggressiveness?: number;
}

export interface AudioDenoiseResult {
  output_audio_storage_key: string;
  output_audio_hash: string;
  noise_reduction_db?: number;
  provenance: AnalysisProvenance;
}

export interface AudioEnhanceRequest {
  audio_storage_key: string;
  content_hash: string;
  target_lufs?: number;
}

export interface AudioEnhanceResult {
  output_audio_storage_key: string;
  output_audio_hash: string;
  applied_lufs: number;
  provenance: AnalysisProvenance;
}

export interface VocalIsolationRequest {
  audio_storage_key: string;
  content_hash: string;
  extract_instrumental?: boolean;
}

export interface VocalIsolationResult {
  vocals_storage_key: string;
  vocals_hash: string;
  instrumental_storage_key?: string | null;
  instrumental_hash?: string | null;
  provenance: AnalysisProvenance;
}

export interface SemanticIntelligenceFoundation {
  status?: string;
  topics?: string[];
  summary?: string | null;
}

export interface MediaQualityIntelligence {
  speech?: SpeechQuality | null;
  audio_quality_score?: number | null;
  visual_quality_score?: number | null;
  overall_score?: number | null;
}

export interface MediaIntelligence {
  workspace_id: string;
  asset_id: string;
  content_hash: string;
  analysis_version?: string;
  contract_version?: string;
  created_at: TzAwareDatetime;
  technical?: TechnicalMetadata;
  speech?: SpeechIntelligence | null;
  audio?: AudioIntelligence;
  visual?: VisualIntelligence;
  semantic?: SemanticIntelligenceFoundation;
  quality?: MediaQualityIntelligence;
  provenance: AnalysisProvenance;
}

export interface AIRequest {
  request_id: string;
  workspace_id: string;
  actor_id: string;
  project_id?: string | null;
  session_id?: string | null;
  capability: CapabilityType;
  intent?: string | null;
  input_data?: Record<string, JsonValue>;
  quality_target?: QualityTarget;
  privacy_requirement?: PrivacyRequirement;
  execution_class?: ExecutionClass;
  metadata?: Record<string, JsonValue>;
  created_at: TzAwareDatetime;
  contract_version?: string;
}

export interface AIResponse {
  request_id: string;
  run_id?: string | null;
  status: AIResponseStatus;
  result?: Record<string, JsonValue> | null;
  usage?: UsageRecord;
  cost: CostEstimate;
  warnings?: string[];
  error?: AIError | null;
  created_at: TzAwareDatetime;
  contract_version?: string;
}

export interface AIRun {
  run_id: string;
  workspace_id: string;
  project_id?: string | null;
  session_id?: string | null;
  status: AIRunStatus;
  capability: CapabilityType;
  workflow_ref?: string | null;
  created_at: TzAwareDatetime;
  started_at?: TzAwareDatetime | null;
  completed_at?: TzAwareDatetime | null;
  usage?: UsageRecord;
  cost: CostEstimate;
  error?: AIError | null;
  contract_version?: string;
  execution_class?: ExecutionClass;
  prompt_id?: string | null;
  prompt_version?: string | null;
  prompt_hash?: string | null;
}

export interface AIStep {
  step_id: string;
  run_id: string;
  status: AIStepStatus;
  attempt?: number;
  capability: CapabilityType;
  input_ref?: string | null;
  output_ref?: string | null;
  provider?: string | null;
  model?: string | null;
  usage?: UsageRecord;
  cost: CostEstimate;
  error?: AIError | null;
  created_at: TzAwareDatetime;
  started_at?: TzAwareDatetime | null;
  completed_at?: TzAwareDatetime | null;
  prompt_id?: string | null;
  prompt_version?: string | null;
  prompt_hash?: string | null;
  worker_id?: string | null;
  lease_token?: string | null;
  lease_expires_at?: TzAwareDatetime | null;
  heartbeat_at?: TzAwareDatetime | null;
  input_hash?: string | null;
  idempotency_key?: string | null;
  dependencies?: string[];
  max_attempts?: number;
  next_retry_at?: TzAwareDatetime | null;
}

export interface AIActivityRecord {
  activity_id: string;
  run_id: string;
  step_id: string;
  idempotency_key: string;
  status: ActivityStatus;
  semantics?: IdempotencySemantics;
  started_at?: TzAwareDatetime | null;
  completed_at?: TzAwareDatetime | null;
  provider?: string | null;
  model?: string | null;
  remote_operation_ref?: string | null;
  output_ref?: string | null;
  error?: AIError | null;
  cost?: CostEstimate | null;
  usage?: UsageRecord | null;
  cost_settled?: boolean;
  reservation_id?: string | null;
  created_at: TzAwareDatetime;
}

export interface AICacheEntry {
  cache_key: string;
  workspace_id: string;
  capability: CapabilityType;
  input_hash: string;
  status: CacheEntryStatus;
  output_ref?: string | null;
  producer?: string | null;
  model?: string | null;
  model_version?: string | null;
  contract_version?: string;
  prompt_version?: string;
  analysis_version?: string;
  created_at: TzAwareDatetime;
  expires_at?: TzAwareDatetime | null;
  owner_id?: string | null;
  lease_token?: string | null;
  lease_expires_at?: TzAwareDatetime | null;
  activity_id?: string | null;
  activity_idempotency_key?: string | null;
  generation?: number;
  error?: AIError | null;
}

export interface PromptMetadata {
  author?: string | null;
  description?: string | null;
  tags?: string[];
  eval_gate_id?: string | null;
  eval_quality_score?: number | null;
}

export interface PromptContract {
  prompt_id: string;
  version: number;
  hash: string;
  status: PromptStatus;
  template: string;
  system_prompt?: string | null;
  variables?: string[];
  created_at: TzAwareDatetime;
  workspace_id?: string | null;
  metadata?: PromptMetadata;
}

export interface PromptRenderRequest {
  prompt_id: string;
  version?: number | null;
  variables?: Record<string, JsonValue>;
  workspace_id?: string | null;
}

export interface PromptRenderResult {
  prompt_id: string;
  version: number;
  hash: string;
  rendered_text: string;
  system_prompt?: string | null;
  status: PromptStatus;
}

export interface TraceSpanRecord {
  trace_id: string;
  span_id: string;
  parent_span_id?: string | null;
  span_type: SpanType;
  name: string;
  run_id: string;
  step_id?: string | null;
  activity_id?: string | null;
  workspace_id: string;
  project_id?: string | null;
  capability?: string | null;
  provider?: string | null;
  model?: string | null;
  prompt_id?: string | null;
  prompt_version?: string | null;
  started_at: TzAwareDatetime;
  ended_at?: TzAwareDatetime | null;
  duration_ms?: number | null;
  input_tokens?: number | null;
  output_tokens?: number | null;
  cache_hit?: boolean | null;
  retry_count?: number;
  fallback?: boolean;
  estimated_cost?: number | string | null;
  actual_cost?: number | string | null;
  quality_score?: number | null;
  status?: string;
  error_code?: string | null;
  attributes?: Record<string, JsonValue>;
}

export interface AITrace {
  trace_id: string;
  run_id: string;
  workspace_id: string;
  spans?: TraceSpanRecord[];
}

export interface EvalExample {
  example_id: string;
  input_payload: Record<string, JsonValue>;
  expected_output?: Record<string, JsonValue> | null;
  expected_schema?: string | null;
  ground_truth_label?: string | null;
  is_human_verified?: boolean;
  min_quality_score?: number;
}

export interface EvalDatasetContract {
  dataset_id: string;
  version: string;
  content_hash: string;
  capability: CapabilityType;
  description: string;
  examples: EvalExample[];
}

export interface EvalResultContract {
  evaluation_id: string;
  dataset_id: string;
  dataset_version: string;
  candidate_type: CandidateType;
  candidate_id: string;
  candidate_version: string;
  passed: boolean;
  quality_score: number;
  cost_score: number;
  latency_ms: number;
  evaluators_used: EvaluatorType[];
  created_at: TzAwareDatetime;
  failure_reasons?: string[];
  metrics?: Record<string, JsonValue>;
}

export interface BenchmarkDebtContract {
  benchmark_id: string;
  name: string;
  status?: string;
  target_stage?: string;
  fake_scores_injected?: boolean;
  notes: string;
}
""".strip()

    lines.append(interfaces_code)
    lines.append("")
    return "\n".join(lines)


def write_file_atomic(path: Path, content: str) -> None:
    """Atomically writes content using a temporary sibling file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)


def check_artifacts() -> Tuple[bool, List[str]]:
    """
    Compares all on-disk artifacts against expected in-memory outputs.
    Returns (is_synced, diff_messages).
    """
    expected_schemas = generate_json_schemas()
    expected_ts = generate_typescript_content()

    stale_or_missing: List[str] = []

    # Check schemas
    for schema_path, expected_content in expected_schemas.items():
        if not schema_path.exists():
            stale_or_missing.append(f"Missing schema: {schema_path.relative_to(ROOT)}")
            continue
        current = schema_path.read_text(encoding="utf-8")
        if current != expected_content:
            stale_or_missing.append(f"Stale schema: {schema_path.relative_to(ROOT)}")

    # Check TypeScript outputs
    for ts_path in [TS_OUTPUT_CONTRACTS, TS_OUTPUT_REMOTION]:
        if not ts_path.exists():
            stale_or_missing.append(f"Missing TypeScript contract: {ts_path.relative_to(ROOT)}")
            continue
        current = ts_path.read_text(encoding="utf-8")
        if current != expected_ts:
            stale_or_missing.append(f"Stale TypeScript contract: {ts_path.relative_to(ROOT)}")

    return (len(stale_or_missing) == 0, stale_or_missing)


def generate_all() -> None:
    """Generates all JSON schemas and TypeScript contracts deterministically."""
    schemas = generate_json_schemas()
    for path, content in schemas.items():
        write_file_atomic(path, content)

    ts_content = generate_typescript_content()
    write_file_atomic(TS_OUTPUT_CONTRACTS, ts_content)
    write_file_atomic(TS_OUTPUT_REMOTION, ts_content)


def main() -> int:
    check_mode = "--check" in sys.argv

    if check_mode:
        synced, errors = check_artifacts()
        if synced:
            print("✅ Ground Truth Parity: AI contracts, schemas, and TypeScript definitions are fully synchronized.")
            return 0
        else:
            print("❌ STALENESS DETECTED in AI Contract artifacts:", file=sys.stderr)
            for err in errors:
                print(f"  • {err}", file=sys.stderr)
            print("\nRun `python scripts/generate_ai_contracts.py` to regenerate artifacts.", file=sys.stderr)
            return 1

    generate_all()
    print("✅ Successfully generated AI contracts:")
    print(f"   • {len(CANONICAL_MODELS) + 1} JSON schemas -> {SCHEMA_DIR.relative_to(ROOT)}/")
    print(f"   • TypeScript contracts -> {TS_OUTPUT_CONTRACTS.relative_to(ROOT)}")
    print(f"   • TypeScript contracts -> {TS_OUTPUT_REMOTION.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
