import { describe, it, expect } from "vitest";
import type {
  CapabilityDefinition,
  ImplementationDescriptor,
  CapabilityCategory,
  CapabilityFamily,
  SideEffectClass,
  TenantScope,
  ExecutionMode,
  CostClass,
  LatencyClass,
  RetryPolicy,
  IdempotencyPolicy,
  ImplementationStatus,
  MigrationStrategy,
  CapabilityLifecycleStatus,
  CapabilityType,
  TrimVideoInput,
  TrimVideoOutput,
  SpeechToTextInput,
  MutateAssetStatusInput,
  MutateAssetStatusOutput,
} from "../../contracts/generated/ai_contracts";

import capabilityDefinitionSchema from "../../schemas/ai/capability_definition.schema.json";
import implementationDescriptorSchema from "../../schemas/ai/implementation_descriptor.schema.json";

describe("S28-M02 Capability Contracts TypeScript Parity", () => {
  it("validates that CapabilityDefinition interface compiles and types match canonical schema", () => {
    const validDescriptor: ImplementationDescriptor = {
      implementation_id: "legacy_video_tools_mcp_trim_video",
      implementation_kind: "LEGACY_MCP",
      current_status: "WORKING",
      source: "tools/mcp-servers/video-tools-mcp/utils/ffmpeg_ops.py",
      provider_or_engine: "FFmpeg CLI",
      constraints: ["Local FFmpeg binary required"],
      known_issues: [],
    };

    const validCapability: CapabilityDefinition = {
      capability_id: "TRIM_VIDEO",
      version: "1.0.0",
      name: "Trim Video Duration",
      description: "Trims a video file to target duration from the start using streamcopy.",
      category: "TOOL",
      family: "VIDEO_PROCESSING",
      input_contract: "TrimVideoInput",
      output_contract: "TrimVideoOutput",
      side_effect_class: "SUBPROCESS",
      required_permissions: ["editor"],
      tenant_scope: "WORKSPACE",
      execution_mode: "LOCAL",
      timeout_seconds: 30.0,
      retry_policy: "SAFE_TRANSIENT",
      idempotency_policy: "IDEMPOTENT",
      cost_class: "LOW",
      latency_class: "SHORT",
      implementations: [validDescriptor],
      status: "ACTIVE",
      owner: "MediaProcessingService (Video Subsystem)",
    };

    expect(validCapability.capability_id).toBe("TRIM_VIDEO");
    expect(validCapability.category).toBe("TOOL");
    expect(validCapability.family).toBe("VIDEO_PROCESSING");
    expect(validCapability.side_effect_class).toBe("SUBPROCESS");
    expect(validCapability.implementations?.length).toBe(1);

    expect(capabilityDefinitionSchema.title).toBe("CapabilityDefinition");
    expect(capabilityDefinitionSchema.required).toContain("capability_id");
    expect(capabilityDefinitionSchema.required).toContain("name");
    expect(capabilityDefinitionSchema.required).toContain("description");
    expect(capabilityDefinitionSchema.required).toContain("category");
    expect(capabilityDefinitionSchema.required).toContain("family");
    expect(capabilityDefinitionSchema.required).toContain("input_contract");
    expect(capabilityDefinitionSchema.required).toContain("output_contract");
    expect(capabilityDefinitionSchema.required).toContain("side_effect_class");
    expect(capabilityDefinitionSchema.required).toContain("owner");
  });

  it("validates that ImplementationDescriptor interface compiles and matches schema", () => {
    const descriptor: ImplementationDescriptor = {
      implementation_id: "legacy_media_sources_mcp_pixabay_audio",
      implementation_kind: "LEGACY_MCP",
      current_status: "BROKEN",
      source: "tools/mcp-servers/media-sources-mcp/utils/pixabay_scraper.py",
      provider_or_engine: "Playwright Chromium Scraper",
      constraints: ["Requires headless browser"],
      known_issues: ["Missing Playwright Chromium binary on host"],
    };

    expect(descriptor.current_status).toBe("BROKEN");
    expect(implementationDescriptorSchema.title).toBe("ImplementationDescriptor");
    expect(implementationDescriptorSchema.required).toContain("implementation_id");
    expect(implementationDescriptorSchema.required).toContain("implementation_kind");
    expect(implementationDescriptorSchema.required).toContain("current_status");
    expect(implementationDescriptorSchema.required).toContain("source");
    expect(implementationDescriptorSchema.required).toContain("provider_or_engine");
  });

  it("validates that CapabilityCategory matches schema enum values", () => {
    const expectedCategories: CapabilityCategory[] = ["MODEL", "TOOL", "DOMAIN_SERVICE"];
    const schemaCategories = capabilityDefinitionSchema.$defs.CapabilityCategory.enum;
    expect(schemaCategories).toEqual(expect.arrayContaining(expectedCategories));
    expect(schemaCategories.length).toBe(3);
  });

  it("validates that CapabilityFamily matches schema enum values", () => {
    const expectedFamilies: CapabilityFamily[] = [
      "SPEECH_INTELLIGENCE",
      "AUDIO_PROCESSING",
      "VIDEO_PROCESSING",
      "IMAGE_PROCESSING",
      "MEDIA_ACQUISITION",
      "MEDIA_INSPECTION",
      "ASSET_DOMAIN_OPERATIONS",
      "CACHE_MANAGEMENT",
      "JOB_MANAGEMENT",
    ];
    const schemaFamilies = capabilityDefinitionSchema.$defs.CapabilityFamily.enum;
    expect(schemaFamilies).toEqual(expect.arrayContaining(expectedFamilies));
    expect(schemaFamilies.length).toBe(9);
  });

  it("validates that Domain Service capabilities compile with appropriate semantics", () => {
    const assetMutation: CapabilityDefinition = {
      capability_id: "MUTATE_ASSET_STATUS",
      version: "1.0.0",
      name: "Mutate Asset Lifecycle Status",
      description: "Authoritative domain mutation updating asset status in ManifestV2.",
      category: "DOMAIN_SERVICE",
      family: "ASSET_DOMAIN_OPERATIONS",
      input_contract: "MutateAssetStatusInput",
      output_contract: "MutateAssetStatusOutput",
      side_effect_class: "DOMAIN_MUTATION",
      required_permissions: ["editor", "admin"],
      tenant_scope: "PROJECT",
      execution_mode: "LOCAL",
      timeout_seconds: 15.0,
      retry_policy: "NEVER",
      idempotency_policy: "IDEMPOTENT",
      cost_class: "NEGLIGIBLE",
      latency_class: "INTERACTIVE",
      status: "ACTIVE",
      owner: "AssetService",
      implementations: [],
    };

    expect(assetMutation.category).toBe("DOMAIN_SERVICE");
    expect(assetMutation.owner).toBe("AssetService");
    expect(assetMutation.side_effect_class).toBe("DOMAIN_MUTATION");
  });

  it("validates that Model capability compiles with MODEL category", () => {
    const speechModel: CapabilityDefinition = {
      capability_id: "SPEECH_TO_TEXT",
      version: "1.0.0",
      name: "Speech to Text Transcription",
      description: "Neural speech transcription via faster-whisper.",
      category: "MODEL",
      family: "SPEECH_INTELLIGENCE",
      input_contract: "AudioIntelligenceFoundation",
      output_contract: "SpeechIntelligence",
      side_effect_class: "LOCAL_TEMP_WRITE",
      required_permissions: ["viewer", "editor"],
      tenant_scope: "WORKSPACE",
      execution_mode: "MODEL",
      timeout_seconds: 60.0,
      retry_policy: "SAFE_TRANSIENT",
      idempotency_policy: "IDEMPOTENT",
      cost_class: "MEDIUM",
      latency_class: "SHORT",
      status: "ACTIVE",
      owner: "ModelRouter / SpeechIntelligenceSubsystem",
      implementations: [],
    };

    expect(speechModel.category).toBe("MODEL");
    expect(speechModel.execution_mode).toBe("MODEL");
  });

  it("validates that S28-M02.1 multi-effects, storage boundary, and media contracts compile correctly", () => {
    const multiEffectCap: CapabilityDefinition = {
      capability_id: "TRIM_VIDEO",
      version: "1.0.0",
      name: "Trim Video",
      description: "Trims video clip duration",
      category: "TOOL",
      family: "VIDEO_PROCESSING",
      input_contract: "TrimVideoInput",
      output_contract: "TrimVideoOutput",
      side_effects: ["SUBPROCESS", "PERSISTENT_WRITE"],
      side_effect_class: "SUBPROCESS",
      target_storage_boundary: "StorageService / Project Video",
      required_permissions: ["editor"],
      tenant_scope: "PROJECT",
      owner: "MediaProcessingService",
    };

    expect(multiEffectCap.side_effects.length).toBe(2);
    expect(multiEffectCap.side_effects).toContain("SUBPROCESS");
    expect(multiEffectCap.side_effects).toContain("PERSISTENT_WRITE");
    expect(multiEffectCap.target_storage_boundary).toBe("StorageService / Project Video");
    expect(multiEffectCap.tenant_scope).toBe("PROJECT");

    const trimInput: TrimVideoInput = {
      project_id: "proj_123",
      video_storage_key: "assets/raw/video.mp4",
      start_time_seconds: 0.0,
      duration_seconds: 5.0,
    };
    expect(trimInput.project_id).toBe("proj_123");

    const trimOutput: TrimVideoOutput = {
      project_id: "proj_123",
      output_storage_key: "assets/derived/trimmed.mp4",
      duration_seconds: 5.0,
    };
    expect(trimOutput.duration_seconds).toBe(5.0);

    const speechInput: SpeechToTextInput = {
      project_id: "proj_456",
      audio_storage_key: "audio/vo.wav",
      language: "ar",
    };
    expect(speechInput.language).toBe("ar");

    const statusInput: MutateAssetStatusInput = {
      project_id: "proj_789",
      asset_id: "asset_001",
      new_status: "ready",
      reason: "Processing completed successfully",
    };
    expect(statusInput.new_status).toBe("ready");

    const statusOutput: MutateAssetStatusOutput = {
      project_id: "proj_789",
      asset_id: "asset_001",
      previous_status: "processing",
      current_status: "ready",
      manifest_updated: true,
    };
    expect(statusOutput.manifest_updated).toBe(true);
  });
});
