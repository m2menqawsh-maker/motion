import { describe, it, expect } from "vitest";
import type {
  AIRequest,
  AIResponse,
  AIRun,
  AIStep,
  CapabilityRequest,
  CapabilityResult,
  CostEstimate,
  MediaIntelligenceRef,
  MemoryQuery,
  MemoryResult,
  ModelRequirement,
  ModelSelection,
  ProvenanceRecord,
  ToolCall,
  ToolResult,
  UsageRecord,
  CapabilityType,
  AIErrorCode,
  AICacheEntry,
  MediaIntelligence,
  SpeechIntelligence,
} from "../../contracts/generated/ai_contracts";

import aiRequestSchema from "../../schemas/ai/ai_request.schema.json";
import aiResponseSchema from "../../schemas/ai/ai_response.schema.json";
import aiCacheEntrySchema from "../../schemas/ai/ai_cache_entry.schema.json";
import mediaIntelligenceSchema from "../../schemas/ai/media_intelligence.schema.json";
import speechIntelligenceSchema from "../../schemas/ai/speech_intelligence.schema.json";


describe("AI Contracts TypeScript Parity (S27.1)", () => {
  it("validates that AIRequest interface compiles and types match canonical schema", () => {
    const validRequest: AIRequest = {
      request_id: "req_test_001",
      workspace_id: "ws_alpha",
      actor_id: "usr_editor_1",
      capability: "TEXT_TO_SPEECH",
      created_at: "2026-09-30T17:00:00Z",
      quality_target: "STANDARD",
      privacy_requirement: "PUBLIC_ALLOWED",
      execution_class: "INTERACTIVE",
      input_data: { text: "Test voiceover prompt" },
      metadata: { debug: false },
      contract_version: "1.0.0",
    };

    expect(validRequest.request_id).toBe("req_test_001");
    expect(validRequest.capability).toBe("TEXT_TO_SPEECH");
    expect(aiRequestSchema.title).toBe("AIRequest");
    expect(aiRequestSchema.required).toContain("request_id");
    expect(aiRequestSchema.required).toContain("workspace_id");
    expect(aiRequestSchema.required).toContain("actor_id");
  });

  it("validates that AIResponse interface compiles and matches canonical schema", () => {
    const validResponse: AIResponse = {
      request_id: "req_test_001",
      status: "SUCCEEDED",
      result: { audio_url: "storage://audio/output.mp3" },
      usage: { audio_seconds: "3.2" },
      cost: { estimated_cost: "0.01", actual_cost: "0.01", currency: "USD" },
      warnings: [],
      error: null,
      created_at: "2026-09-30T17:00:05Z",
      contract_version: "1.0.0",
    };

    expect(validResponse.status).toBe("SUCCEEDED");
    expect(validResponse.error).toBeNull();
    expect(aiResponseSchema.title).toBe("AIResponse");
    expect(aiResponseSchema.required).toContain("request_id");
    expect(aiResponseSchema.required).toContain("status");
    expect(aiResponseSchema.required).toContain("cost");
  });

  it("validates that ToolCall and ToolResult interfaces compile and enforce type safety", () => {
    const toolCall: ToolCall = {
      call_id: "call_crop_100",
      tool_name: "crop_video",
      parameters: { width: 1080, height: 1920 },
    };

    const toolResult: ToolResult = {
      call_id: "call_crop_100",
      status: "SUCCESS",
      output: { asset_id: "ast_crop_ready" },
      error: null,
      started_at: "2026-09-30T17:00:00Z",
      completed_at: "2026-09-30T17:00:03Z",
      duration_ms: 3000,
    };

    expect(toolCall.call_id).toBe(toolResult.call_id);
    expect(toolResult.status).toBe("SUCCESS");
  });

  it("validates that AIRun and AIStep interfaces compile correctly", () => {
    const run: AIRun = {
      run_id: "run_999",
      workspace_id: "ws_alpha",
      status: "RUNNING",
      capability: "PLANNING",
      created_at: "2026-09-30T17:00:00Z",
      cost: { estimated_cost: "0.10" },
    };

    const step: AIStep = {
      step_id: "step_001",
      run_id: "run_999",
      status: "SUCCEEDED",
      attempt: 1,
      capability: "PLANNING",
      cost: { estimated_cost: "0.05" },
      created_at: "2026-09-30T17:00:00Z",
    };

    expect(step.run_id).toBe(run.run_id);
    expect(step.attempt).toBe(1);
  });

  it("validates that AICacheEntry interface compiles and matches canonical schema (S27.12)", () => {
    const entry: AICacheEntry = {
      cache_key: "ck_abc1234567890",
      workspace_id: "ws_alpha",
      capability: "TEXT_GENERATION",
      input_hash: "hash_input_12345",
      status: "READY",
      output_ref: "workspaces/ws_alpha/cache/text_generation/ck_abc1234567890.json",
      producer: "provider_openai",
      model: "gpt-4o",
      model_version: "2026-05-01",
      contract_version: "1.0.0",
      prompt_version: "1.0.0",
      analysis_version: "1.0.0",
      created_at: "2026-10-01T17:00:00Z",
      expires_at: null,
      owner_id: null,
      lease_token: null,
      lease_expires_at: null,
      activity_id: null,
      activity_idempotency_key: null,
      generation: 1,
      error: null,
    };


    expect(entry.cache_key).toBe("ck_abc1234567890");
    expect(entry.status).toBe("READY");
    expect(aiCacheEntrySchema.title).toBe("AICacheEntry");
    expect(aiCacheEntrySchema.required).toContain("cache_key");
    expect(aiCacheEntrySchema.required).toContain("workspace_id");
    expect(aiCacheEntrySchema.required).toContain("capability");
    expect(aiCacheEntrySchema.required).toContain("input_hash");
    expect(aiCacheEntrySchema.required).toContain("status");
  });

  it("validates that MediaIntelligence and SpeechIntelligence compile and match schema (S27.13 / S27.14)", () => {
    const speechIntel: SpeechIntelligence = {
      language: "ar",
      language_confidence: 0.98,
      transcript: "الموبايل الي بايدك",
      segments: [
        {
          id: "seg_001",
          start: 0.0,
          end: 1.5,
          text: "الموبايل الي بايدك",
          speaker_id: "SPEAKER_00",
          confidence: 0.97,
          words: [
            { text: "الموبايل", start: 0.0, end: 0.6, speaker_id: "SPEAKER_00", confidence: 0.98 },
            { text: "الي", start: 0.65, end: 0.9, speaker_id: "SPEAKER_00", confidence: 0.96 },
            { text: "بايدك", start: 0.95, end: 1.5, speaker_id: "SPEAKER_00", confidence: 0.97 },
          ],
        },
      ],
      words: [
        { text: "الموبايل", start: 0.0, end: 0.6, speaker_id: "SPEAKER_00", confidence: 0.98 },
        { text: "الي", start: 0.65, end: 0.9, speaker_id: "SPEAKER_00", confidence: 0.96 },
        { text: "بايدك", start: 0.95, end: 1.5, speaker_id: "SPEAKER_00", confidence: 0.97 },
      ],
      speakers: [
        {
          speaker_id: "SPEAKER_00",
          label: "Host",
          confidence: 0.99,
          total_speaking_time_seconds: 1.5,
        },
      ],
      duration_seconds: 1.5,
      overall_confidence: 0.97,
      provenance: {
        producer: "speech_pipeline",
        provider: "local",
        model: "whisper-large-v3",
        timestamp: "2026-10-01T17:00:00Z",
        analysis_version: "1.0.0",
        contract_version: "1.0.0",
      },
    };

    const mediaIntel: MediaIntelligence = {
      workspace_id: "ws_alpha",
      asset_id: "ast_voiceover_001",
      content_hash: "a1b2c3d4e5f67890",
      analysis_version: "1.0.0",
      contract_version: "1.0.0",
      created_at: "2026-10-01T17:00:00Z",
      technical: {
        format: "wav",
        duration_seconds: 1.5,
        has_audio: true,
        has_video: false,
        audio_channels: 1,
        audio_sample_rate: 44100,
        audio_codec: "pcm_s16le",
      },
      speech: speechIntel,
      audio: { status: "TYPED_FOUNDATION_AI13" },
      visual: { status: "TYPED_FOUNDATION_AI13", has_visual_analysis: false },
      semantic: { status: "TYPED_FOUNDATION_AI13", topics: ["tech", "mobile"] },
      quality: { overall_score: 0.95 },
      provenance: {
        producer: "media_intelligence_service",
        timestamp: "2026-10-01T17:00:00Z",
        analysis_version: "1.0.0",
        contract_version: "1.0.0",
      },
    };

    expect(mediaIntel.workspace_id).toBe("ws_alpha");
    expect(mediaIntel.speech?.transcript).toBe("الموبايل الي بايدك");
    expect(mediaIntelligenceSchema.title).toBe("MediaIntelligence");
    expect(mediaIntelligenceSchema.required).toContain("workspace_id");
    expect(mediaIntelligenceSchema.required).toContain("asset_id");
    expect(mediaIntelligenceSchema.required).toContain("content_hash");
    expect(mediaIntelligenceSchema.required).toContain("created_at");
    expect(mediaIntelligenceSchema.required).toContain("provenance");

    expect(speechIntelligenceSchema.title).toBe("SpeechIntelligence");
    expect(speechIntelligenceSchema.required).toContain("transcript");
    expect(speechIntelligenceSchema.required).toContain("provenance");
  });
});

