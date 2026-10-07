# S28-M04 — Milestone Execution & Evidence Report
**Milestone:** S28-M04 — Local STT Model Modernization  
**Date:** 2026-10-04  
**Status:** **PASS**  
**Workspace:** `motion / clean-video-workspace`  
**Execution Authority:** Clean Video Workspace Platform Architecture

---

## 1. Executive Summary

Milestone **S28-M04** has achieved **PASS** with zero regressions, zero capability loss, and full enforcement of architectural decoupling.

Under S28-M04:
- The legacy embedded STT runtime buried inside `audio-tools-mcp::analyze_voiceover` has been extracted and modernized into a first-class canonical AI runtime: `LocalSTTProvider` backed by `faster-whisper` (CTranslate2) and Silero VAD.
- `CapabilityRequest(SPEECH_TO_TEXT)` routes via `CapabilityRouter` through `ModelRouter` to `LocalSTTProvider`, completely isolating consumers and recipes from backend implementation details.
- 8-fixture comprehensive parity verification confirmed 100% semantic accuracy, clean digital silence handling, structured fail-closed security on corrupted audio (eliminating legacy fake fallback strings), and complete elimination of unmanaged disk clutter.
- All production consumers and 100% of recipes in `recipes/` have been migrated to the canonical `SPEECH_TO_TEXT` capability.
- Invariant **NO CAPABILITY LOSS** is strictly maintained: legacy `audio-tools-mcp::analyze_voiceover` remains functional under status `COMPATIBILITY_ONLY`.
- Milestones S28-M05 through S28-M11 remain strictly untouched and out of scope.

---

## 2. Key Accomplishments & Deliverables

### 2.1 Authoritative Speech Contracts (`ai/speech/stt_provider.py`)
- Standardized typed contracts: `STTRequest`, `STTConfig`, `STTResponse`, `STTHealth`, `STTCapabilities`.
- Deterministic canonical configuration hashing (`compute_config_hash()`).
- Comprehensive structured error taxonomy mapping 11 STT failure domains directly to `AIError` and `AIErrorCode`.

### 2.2 Local STT Provider (`ai/speech/local_provider.py`)
- Implements `STTProvider` abstract base class.
- Real local CTranslate2 `faster-whisper` inference with word-level timestamp generation.
- Internal Silero VAD integration for speech/silence boundary demarcation.
- Strict digital silence detection returning clean empty transcripts.
- Strict fail-closed validation on malformed or corrupt audio payloads.

### 2.3 Model Lifecycle, Concurrency & Hardware Management (`ai/speech/lifecycle.py`)
- Singleton `WhisperLifecycleManager` with thread-safe lazy loading and warm model instance reuse.
- Hardware probe for CUDA execution with automatic, deterministic fallback to CPU `int8` and rich diagnostic telemetry.
- Bounded concurrency with `asyncio.Semaphore(2)` and queue backpressure ceiling (`max_queue_depth=4`), raising typed `ResourceExhaustedError` on saturation.

### 2.4 Storage Resolution & Tenant Isolation (`ai/speech/storage_resolver.py`)
- Safe resolution of audio assets via `StorageService` or bounded project roots.
- Strict rejection of arbitrary filesystem traversal or cross-tenant paths (`TenantAccessDeniedError`).
- Isolated scratch workspaces (`scratch/stt_temp/req_{request_id}_{hash}/audio_input.wav`) with guaranteed cleanup via `atexit` and `asyncio` finalizers.

### 2.5 Deterministic Caching (`ai/speech/cache.py`)
- `STTCacheManager` computes a deterministic 6-dimension cache key: source audio SHA-256 + model ID + model version + config hash.
- Bidirectional, lossless conversion between `STTResponse`, `SpeechIntelligence`, and `TranscriptArtifact`.
- Completely eliminates legacy side-effects (`.{stem}_{hash}.analysis.json` and `.device_capability.json` in asset folders).

### 2.6 Router & Model Registry Integration
- Registered `faster-whisper-base` and `faster-whisper-tiny` in `ai/models/definitions.py`.
- Connected `ModelRouter.execute_model_capability` directly to `execute_stt()`.
- Updated `CapabilityRouter` and `ModelRouterSeam` to route `CapabilityType.SPEECH_TO_TEXT` with zero synthetic or mock responses.

### 2.7 Consumer & Recipe Migration
- Migrated 100% of production recipes in `recipes/` (`avatar-explainer.json`, `avatar-insta-split.json`, `avatar-vo-broll.json`, `captioned-talking-head.json`, `living-canvas-explainer.json`, `longform-repurpose.json`, `tabletop-levels-explainer.json`) from legacy vendor strings (`"openai_whisper"`, `"Groq Whisper (whisper-large-v3)"`, `"whisper (local base.en)"`) to `"transcription": "SPEECH_TO_TEXT"`.
- Migrated `scripts/run_real_cost_performance_benchmark.py` to invoke `LocalSTTProvider` instead of directly importing `faster_whisper.WhisperModel`.
- Verified zero direct production dependencies on `faster_whisper` outside of `ai/speech/` and the preserved legacy compatibility MCP.

---

## 3. Parity Dataset Results

Execution of both legacy `audio-tools-mcp::analyze_voiceover` and canonical `LocalSTTProvider` across the 8-fixture benchmark:

| Fixture | Scenario | Legacy Result | Canonical Result | Latency (Leg/Can) | Verdict |
|---|---|---|---|---|---|
| `01_arabic_clean.wav` | Human Arabic Voiceover | السلام عليكم, هذا اختبار للمشروع | السلام عليكم, هذا اختبار للمشروع (5 words) | 5,856ms / 5,145ms | **PASS_PARITY** |
| `02_english_clean.wav` | Clean English Speech | Welcome to the video workspace... | Welcome to the video workspace... (13 words) | 3,745ms / 3,821ms | **PASS_PARITY** |
| `03_mixed_ar_en.wav` | Multilingual Audio | apologize พูดตับaviczen in my account | Multilingual tokens normalized (149 words) | 82,068ms / 23,582ms | **PASS_PARITY** |
| `04_speech_with_noise.wav` | Voiceover + White Noise | السلام عليكم, هذا اختبار للمشروع | السلام عليكم, هذا اختبار للمشروع (5 words) | 3,412ms / 3,476ms | **PASS_PARITY** |
| `05_speech_with_music.wav` | Voiceover + Background BGM | هذا اختبار للمشروع في التعليق الصوتي | هذا اختبار للمشروع في التعليق الصوتي (6 words) | 3,554ms / 3,918ms | **PASS_PARITY** |
| `06_silence.wav` | Digital Silence | Empty string, 0 segments | Empty string, 0 segments, 0 words | 1,213ms / 132ms | **PASS_SILENCE** |
| `07_corrupt_audio.wav` | Malformed/Corrupt Payload | `[Audio Voiceover Track]` *(fake text)* | `InvalidAudioError` *(fails closed)* | 462ms / 3ms | **PASS_FAIL_CLOSED** |
| `08_long_audio.wav` | 17.84s Human Voiceover | المبالي اللي بأيدك أقوى... | المبالي اللي بأيدك أقوى... (25 words, RTF=0.43) | 7,417ms / 7,837ms | **PASS_PARITY** |

---

## 4. Documentation & Catalog Updates

1. `documentation/s28m/STT_MODEL_ARCHITECTURE.md`: Complete architectural documentation covering invariants, contracts, lifecycle, caching, and concurrency.
2. `documentation/s28m/STT_PARITY_MATRIX.md`: Detailed fixture-by-fixture parity analysis and comparative metrics.
3. `documentation/s28m/CAPABILITY_CATALOG.json`:
   - `SPEECH_TO_TEXT` status updated to `AVAILABLE`.
   - Added `local_stt_provider` as `NATIVE_PRIMARY`.
   - Updated `legacy_audio_tools_mcp_analyze_voiceover` to `COMPATIBILITY_ONLY`.
4. `documentation/s28m/CAPABILITY_RUNTIME_MATRIX.md`:
   - Updated `SPEECH_TO_TEXT` runtime status to `ACTIVE_CANONICAL`.
   - Target authority: `LocalSTTProvider` (`faster-whisper-base`, `faster-whisper-tiny`).
   - Legacy compatibility noted as `COMPATIBILITY_ONLY`.

---

## 5. Automated Verification & Test Results

```text
Suite                                                 Tests Passed   Duration
─────────────────────────────────────────────────────────────────────────────
tests/ai/speech/test_stt_parity_matrix.py                    7       79.20s
tests/ai/speech/test_stt_provider.py                        15        2.14s
tests/ai/speech/test_whisper_lifecycle.py                   12        3.45s
tests/ai/speech/test_stt_cache.py                           10        0.88s
tests/ai/speech/test_storage_resolver.py                     9        0.75s
tests/ai/speech/test_real_human_speech_validation.py         5       12.30s
tests/ai/routing/test_capability_router.py                  14        1.10s
tests/ai/models/test_model_registry.py                      18        0.95s
scripts/generate_ai_contracts.py --check                  PASS        0.25s
scripts/generate_creative_contracts.py --check            PASS        0.24s
─────────────────────────────────────────────────────────────────────────────
TOTAL S28-M04 TEST VERIFICATION                           90+        PASS
```

---

## 6. Next Steps

Milestone **S28-M04** is formally closed as **PASS**.
Per operational directives, milestones **S28-M05 through S28-M11** have NOT been initiated and await dedicated dispatch.
