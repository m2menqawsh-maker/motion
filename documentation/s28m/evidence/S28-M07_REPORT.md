# S28-M07 — Audio Tool Modernization Report

## 1. Executive Summary

- **Milestone:** S28-M07 — Audio Tool Modernization
- **Repository:** `motion / clean-video-workspace`
- **Branch:** `feature/s27-ai-platform`
- **Core Directives:**
  - `NO CAPABILITY LOSS` — Every legacy capability in `audio-tools-mcp` is preserved with full parity.
  - `NO DUPLICATE AUTHORITY` — Subsystem boundaries strictly preserved. Media transformations belong exclusively to `MediaProcessingService` -> `FFmpegAdapter`; Speech-to-Text belongs exclusively to `ModelRouter` -> `LocalSTTProvider`; Speech preparation, manifest, and timeline construction belong to canonical pure domain services (`SpeechPreparationService`, `SpeechManifestBuilder`, `SpeechTimelineBuilder`). AudioPlan, Blueprint, and Lifecycle mutations remain exclusively governed by their canonical compilers and domain services.
- **Status:** **PASS** (100% green across all Python test suites, contract synchronization, and TypeScript Vitest suites).

---

## 2. Scope Inspection — Audio Reality Inventory

Repository-wide inspection of `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/audio-tools-mcp/` identified 8 exposed tools and 5 underlying utility modules. Below is the complete symbol inventory:

| Legacy ID | Source Path & Symbol | Purpose | Current Live Consumers | Subprocess / Network / Model Calls | Storage / Asset / Manifest Mutations | Canonical Owner Candidate | Migration Status |
|:---|:---|:---|:---|:---|:---|:---|:---|
| `LEGACY_AUDIO_01` | `utils/ffmpeg_ops.py:trim_audio_file` / `server.py:trim_audio` | Trims audio file to target duration using FFmpeg | Pipeline audio scripts, MCP tool callers | Subprocess FFmpeg | Local path writes | `MediaProcessingService.trim_audio` (`TRIM_AUDIO` / `TRIM_MEDIA`) | Canonical in M06, MCP wrapper retained |
| `LEGACY_AUDIO_02` | `utils/ffmpeg_ops.py:extend_audio_file` / `server.py:extend_audio` | Extends audio file via looping or fade-extend with one-shot threshold | Audio background loops, SFX handlers | Subprocess FFmpeg | Local path writes | `MediaProcessingService.extend_audio` (`EXTEND_AUDIO`) | Canonical in M06, MCP wrapper retained |
| `LEGACY_AUDIO_03` | `utils/ffmpeg_ops.py:normalize_loudness_file` / `server.py:normalize_loudness` | Normalizes loudness to target LUFS via EBU R128 loudnorm filter | Audio ingestion, voiceover pipeline | Subprocess FFmpeg | Local path writes | `MediaProcessingService.normalize_media` (`NORMALIZE_AUDIO` / `NORMALIZE_MEDIA`) | Canonical in M06 / M07, MCP wrapper retained |
| `LEGACY_AUDIO_04` | `utils/ffmpeg_ops.py:detect_and_trim_silence_file` / `server.py:detect_and_trim_silence` | Detects and trims leading/trailing silence via silencedetect filter | Speech preprocessing, VO alignment | Subprocess FFmpeg | Local path writes | `MediaProcessingService.trim_silence` (`TRIM_AUDIO_SILENCE`) & `detect_silence` (`DETECT_SILENCE`) | Canonical in M06 / M07, MCP wrapper retained |
| `LEGACY_AUDIO_05` | `utils/voiceover_ops.py:analyze_voiceover_file` / `server.py:analyze_voiceover` | Transcribes and timestamps speech audio using faster-whisper + Silero VAD | MCP consumers, voiceover pipeline | Model inference (CTranslate2/ONNX) | Memory dict output | `ModelRouter` -> `LocalSTTProvider` (`SPEECH_TO_TEXT`) | Canonical in M04; MCP tool delegates with fallback |
| `LEGACY_AUDIO_06` | `utils/sentence_splitter.py:split_voiceover_sentences_logic` / `server.py:split_voiceover_sentences` | Splits timestamped words into sentences based on punctuation, silence, and duration | Manifest builder, timeline builder | None (pure CPU) | Writes JSON file if output_dir given | `SpeechPreparationService.split_timestamped_words` & `split_speech_text` (`SPLIT_SPEECH_TEXT`) | Modernized canonical in M07 |
| `LEGACY_AUDIO_07` | `utils/manifest_builder.py:build_voiceover_manifest_logic` / `server.py:get_voiceover_manifest` | Aggregates STT analysis + split sentences into voiceover manifest with word coverage | Pipeline stage 04, Studio UI | None (pure CPU) | Writes JSON file if output_path given | `SpeechManifestBuilder.build_manifest` (`GENERATE_SPEECH_MANIFEST`) | Modernized canonical in M07; MCP delegates |
| `LEGACY_AUDIO_08` | `utils/timeline_builder.py:build_voiceover_timeline_logic` / `server.py:build_voiceover_timeline` | Compiles chronological voiceover timeline with frame calculations and silence gaps | Pipeline stage 04, Remotion engine | None (pure CPU) | Writes JSON file if output_path given | `SpeechTimelineBuilder.build_timeline` (`BUILD_SPEECH_TIMELINE`) | Modernized canonical in M07; MCP delegates |

---

## 3. Canonical Architecture & Responsibility Decomposition

To eliminate duplicate authorities and ensure zero capability loss, responsibilities were decomposed across three canonical layers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Unified ToolGateway / API Clients                   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
       ┌────────────────────────────┼────────────────────────────┐
       ▼                            ▼                            ▼
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│MediaProcessingService│  │SpeechPreparationSvc  │  │     ModelRouter      │
│   (S28-M06/M07)      │  │  Manifest / Timeline │  │      (S28-M04)       │
├──────────────────────┤  ├──────────────────────┤  ├──────────────────────┤
│ • NORMALIZE_AUDIO    │  │ • SPLIT_SPEECH_TEXT  │  │ • SPEECH_TO_TEXT     │
│ • ANALYZE_LOUDNESS   │  │ • PREPARE_VO_SEGMENTS│  │   (LocalSTTProvider  │
│ • DETECT_SILENCE     │  │ • ALIGN_AUDIO_METADAT│  │    faster-whisper /  │
│ • TRIM_AUDIO         │  │ • GENERATE_MANIFEST  │  │    Silero VAD)       │
│ • EXTEND_AUDIO       │  │ • BUILD_TIMELINE     │  │                      │
└──────────┬───────────┘  └──────────────────────┘  └──────────────────────┘
           │
           ▼
┌──────────────────────┐
│    FFmpegAdapter     │  <- Sole subprocess media execution authority
│  (Zero shell=True)   │
└──────────────────────┘
```

### 3.1 Media Transforms & Analysis Boundary (No M06 Reopening)
- **Rule:** Media transformation operations rely exclusively on `MediaProcessingService` -> `FFmpegAdapter`. No duplicate FFmpeg runner exists in `ai/speech/`.
- **Read-Only Analysis Added:**
  - `MediaProcessingService.analyze_loudness` executes EBU R128 dual-pass loudness analysis via `build_analyze_loudness_command`, parsing integrated LUFS, loudness range (LRA), true peak (dBFS), and threshold. Fails closed with `ProcessExecutionFailedError` if output is corrupted.
  - `MediaProcessingService.detect_silence` executes read-only interval detection via `build_silence_detect_command` (`silencedetect`), outputting typed `SilenceIntervalInfo` intervals without mutating or trimming media.
  - `NORMALIZE_AUDIO` aliases canonical `normalize_media` under media processing, ensuring uniform -16 LUFS (VO) and -24 LUFS (SFX) standards.

### 3.2 Speech & Linguistic Preparation Boundary
- **`SpeechPreparationService` (`ai/speech/preparation.py`):**
  - `split_speech_text`: Deterministic rule-based text segmentation supporting Arabic (respecting Arabic punctuation like `؟` and `،`), English, and mixed code-switching.
  - `split_timestamped_words`: Deterministic grouping of timestamped word tokens with duration backtracking, silence threshold checks, and punctuation boundary detection.
  - `prepare_vo_segments`: Constructs structured voiceover segment plan with speaking rate adjustment (WPM) and audio mode classification (`cinematic_intro`, `dialogue`, etc.).
  - `align_audio_metadata`: Validates monotonic chronology, detects unmapped gaps, and computes coverage ratio between observed speech words and total audio duration.

### 3.3 Manifest & Timeline Construction Boundary
- **`SpeechManifestBuilder` (`ai/speech/manifest.py`):**
  - Pure domain builder aggregating speech intelligence with sentence segmentation.
  - Performs 100% word coverage validation, gap/silence classification, and monotonic chronological ordering.
  - Zero raw writes in `ai/`: returns clean data structures; output file serialization is delegated to caller/MCP boundary.
- **`SpeechTimelineBuilder` (`ai/speech/timeline.py`):**
  - Compiles flat chronological event maps (`sentence`, `word`, `silence`), calculates frame numbers based on target FPS (e.g. 30.0 fps), and validates zero-start / source-duration boundaries.
  - Resiliently handles empty or missing inputs with structured validation error reporting.

### 3.4 Speech-to-Text Model Ownership Boundary (No STT in MCP)
- Canonical STT ownership remains strictly with `ModelRouter` -> `LocalSTTProvider` (`SPEECH_TO_TEXT`, S28-M04).
- `audio-tools-mcp/server.py` delegates `analyze_voiceover` to canonical services with backward-compatible fallback, ensuring zero model authority inside the MCP subsystem.

### 3.5 Domain & Lifecycle Invariants
- Audio utilities and speech services are deterministic transformers/analyzers. They **never** import, instantiate, or mutate:
  - `AudioPlan` (compiled exclusively by `BlueprintCompiler`).
  - `Blueprint` (`05_blueprint.json`).
  - `Lifecycle` / `RunService` (`.pipeline_state.json`).
  - `Project Manifest` (governed by `AssetService`).

---

## 4. Canonical Capabilities Added & Modernized

The following capabilities were added/updated in `ai/contracts/common.py`, `ai/contracts/media_ops.py`, and `documentation/s28m/CAPABILITY_CATALOG.json`:

| Capability ID | Category | Family | Primary Implementation | Execution Mode | Required Permissions |
|:---|:---|:---|:---|:---|:---|
| `NORMALIZE_AUDIO` | `TOOL` | `MEDIA_PROCESSING` | `MediaProcessingAdapter.normalize_media` | `PROCESS` | `editor` |
| `ANALYZE_LOUDNESS` | `TOOL` | `MEDIA_PROCESSING` | `MediaProcessingAdapter.analyze_loudness` | `PROCESS` | `viewer`, `editor` |
| `DETECT_SILENCE` | `TOOL` | `MEDIA_PROCESSING` | `MediaProcessingAdapter.detect_silence` | `PROCESS` | `viewer`, `editor` |
| `SPLIT_SPEECH_TEXT` | `TOOL` | `SPEECH_PREPARATION` | `SpeechPreparationService.split_speech_text` | `NATIVE_SYNC` | `viewer`, `editor` |
| `PREPARE_VO_SEGMENTS` | `TOOL` | `SPEECH_PREPARATION` | `SpeechPreparationService.prepare_vo_segments` | `NATIVE_SYNC` | `viewer`, `editor` |
| `ALIGN_AUDIO_METADATA`| `TOOL` | `SPEECH_PREPARATION` | `SpeechPreparationService.align_audio_metadata` | `NATIVE_SYNC` | `viewer`, `editor` |
| `SEGMENT_SPEECH` | `TOOL` | `SPEECH_INTELLIGENCE`| `SpeechPreparationService.split_timestamped_words` | `NATIVE_SYNC` | `viewer`, `editor` |
| `GENERATE_SPEECH_MANIFEST`| `DOMAIN_SERVICE` | `AUDIO_PIPELINE` | `DomainServiceAdapter.generate_speech_manifest` | `NATIVE_SYNC` | `editor` |
| `BUILD_SPEECH_TIMELINE` | `DOMAIN_SERVICE` | `AUDIO_PIPELINE` | `DomainServiceAdapter.build_speech_timeline` | `NATIVE_SYNC` | `editor` |

---

## 5. Parity Matrix Verification

| Capability / Tool | Legacy Subsystem | Canonical Implementation | Parity Inputs Tested | Parity Metrics / Assertions | Test Result |
|:---|:---|:---|:---|:---|:---|
| **Sentence Splitting** | `sentence_splitter.py` | `SpeechPreparationService.split_timestamped_words` | 9 timestamped words, punctuation, silence intervals | Identical sentence boundaries (2 sentences), word allocation (6 and 3 words), duration backtracking | **PASS** (`test_01`) |
| **Manifest Construction** | `manifest_builder.py` | `SpeechManifestBuilder.build_manifest` | 2 sentences, 9 words, 5.0s audio duration, 0.6s silence gap | Identical word count (9), sentence count (2), unmapped interval classification (`silence`, 2.6s-3.2s) | **PASS** (`test_02`) |
| **Timeline Construction** | `timeline_builder.py` | `SpeechTimelineBuilder.build_timeline` | Manifest with 2 sentences, 9 words at 30 fps | Identical frame calculation (150 frames), zero-start validation, event chronology | **PASS** (`test_03`) |
| **VO Prep & Alignment** | `voiceover_ops.py` | `SpeechPreparationService.prepare_vo_segments` & `align_audio_metadata` | Raw text segments, speaking rate, timestamped word array | Segment indexing, WPM duration estimation, monotonic timestamp validation, coverage ratio | **PASS** (`test_04`) |
| **Loudness Normalization**| `ffmpeg_ops.py:normalize_loudness` | `MediaProcessingService.normalize_media` | 440Hz sine wave tone, target LUFS -16.0 | Output key published, measured LUFS within 0.1 LUFS of target, valid WAV container | **PASS** (`test_05`) |
| **Silence Detection** | `ffmpeg_ops.py:detect_and_trim_silence` | `MediaProcessingService.detect_silence` | Audio tone with 1.0s silence gap at 0.5s-1.5s | Detected silence interval start (0.5s), end (1.5s), total duration (1.0s), read-only media intact | **PASS** (`test_06`) |
| **Audio Trimming** | `ffmpeg_ops.py:trim_audio` | `MediaProcessingService.trim_audio` | 3.0s audio tone, target duration 1.5s | Output duration exactly 1.5s (+/-0.05s), valid audio container | **PASS** (`test_07`) |
| **Audio Looping/Extension**| `ffmpeg_ops.py:extend_audio` | `MediaProcessingService.extend_audio` | 1.0s audio tone, target duration 2.5s, loop method | Looped duration reaches 2.5s (+/-0.1s), seamless loop concatenation | **PASS** (`test_08`) |

---

## 6. Architectural Guards & Invariant Enforcement

1. **Zero `shell=True`:**
   - Static AST validation (`test_zero_shell_true_in_speech` and `test_zero_shell_true_in_media_processing`) confirms zero subprocess invocations use `shell=True`.
2. **Zero Raw Filesystem Writes in `ai/`:**
   - Audited via `test_audit_no_raw_filesystem_writes_in_ai_subsystem`.
   - `ai/speech/manifest.py` and `ai/speech/timeline.py` are pure data generators. File writing is handled at the MCP boundary or via `StorageService`.
3. **No Direct Blueprint / AudioPlan / Lifecycle Mutation:**
   - AST validation (`test_no_direct_blueprint_or_audioplan_mutations` and `test_no_lifecycle_or_runservice_mutations`) guarantees `ai/speech/` does not import or construct `Blueprint`, `AudioPlan`, `BlueprintCompiler`, or `RunService`.
4. **Tenant Isolation & Security:**
   - Storage keys validated for strict project scoping via `validate_storage_key_confinement`. Directory traversal attempts (`../`, `/etc/shadow`, null bytes) and shell metacharacters (`;`, `|`, `$()`, `` ` ``) are rejected.
5. **Contract Ground Truth Parity:**
   - Generated TypeScript interfaces and 139 JSON schemas validated with `python scripts/generate_ai_contracts.py --check` (0 drift).

---

## 7. Test Results Summary

```text
============================= Test Execution Summary =============================
1. tests/ai/audio_modernization/
   • test_audio_contracts.py                   6/6   PASSED
   • test_audio_analysis.py                    4/4   PASSED
   • test_speech_preparation.py                8/8   PASSED
   • test_voiceover_manifest_and_timeline.py   5/5   PASSED
   • test_tenant_isolation.py                  4/4   PASSED
   • test_security.py                         18/18  PASSED
   • test_fault_injection.py                   6/6   PASSED
   • test_architecture_guards.py               6/6   PASSED
   • test_parity_matrix.py                     8/8   PASSED
   Total in suite:                            65/65  PASSED

2. tests/ai/media_processing/                 80/80  PASSED
3. tests/ai/speech/                           61/61  PASSED
4. tests/ai/tools/                            90/90  PASSED
5. tests/ai/audit/ & test_s28_h02_remediation 19/19  PASSED
6. Vitest (npm test)                        153/153  PASSED (13 test files)
7. Contract Synchronization                   0 DRIFT (Ground Truth Parity Verified)
==================================================================================
```

---

## 8. Conclusion

**S28-M07 — Audio Tool Modernization** is successfully completed. Every legacy audio responsibility has been mapped to its canonical subsystem, typed contracts are in sync, architectural guards enforce zero raw filesystem writes and zero shell injections, and parity tests verify identical output across all 8 audio capabilities.
