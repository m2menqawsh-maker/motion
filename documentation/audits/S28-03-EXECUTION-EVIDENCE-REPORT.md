# S28-03 Execution Evidence Report: Intent + Creative Brief + Recipe Engine + Audio Modes

## 1. Executive Summary

This report provides comprehensive, verifiable execution evidence for the closure of **S28-03 — Intent + Creative Brief + Recipe Engine + Audio Modes** within `clean-video-workspace`.

The end-to-end pipeline:
```text
User Request
+
Project State
+
Available Assets
+
MediaIntelligence
+
User / Workspace Constraints
    ↓
Intent Understanding (Multilingual + Provenance + Contradiction Detection)
    ↓
typed CreativeBrief (with FieldProvenance & Epistemic Tracking)
    ↓
Audio Mode Policy (Canonical Policies & Invariant Enforcement)
    ↓
Recipe Eligibility (Deterministic Stage 1 Gating)
    ↓
Recipe Ranking / Selection (Deterministic Stage 2 Weighted Scoring)
    ↓
valid RecipeSelection (with S28-02 Knowledge + Skills Resolution)
```

The system deterministically and testably answers two fundamental questions:
1. **What does the user want?** (`CreativeBrief` with per-field epistemic provenance and contradiction detection).
2. **Which workflow is valid to execute this request?** (`RecipeSelection` with hard capability/mode gating, provider neutrality, and S28-02 skills/knowledge resolution).

---

## 2. Invariants & Architecture Compliance

| Invariant | Requirement | Verification Method | Status |
| :--- | :--- | :--- | :--- |
| **Recipe ≠ Provider** | Recipes declare neutral capabilities (`TEXT_TO_SPEECH`, `VIDEO_GENERATION`, etc.); zero cloud vendor names (`openai`, `elevenlabs`, `heygen`, `fal`, `suno`, etc.) in recipe models. | AST & Regex Guard in `ai.recipes.registry.assert_provider_neutral` | **PASS** (18/18 recipes clean) |
| **Audio Mode = Policy** | All 6 canonical modes (`MUSIC_ONLY`, `VO_ONLY`, `VO_MUSIC`, `SOURCE_AUDIO`, `SOURCE_AUDIO_MUSIC`, `SILENT`) define capability & mix policies. | `AudioModeEngine` in `ai/audio/modes.py` | **PASS** (Formal policies active) |
| **Negative Invariant: SILENT** | SILENT mode strictly forbids background music, audio playback, or speech synthesis. | `enforce_audio_action` & `assert_capability_allowed` | **PASS** (`SILENT adds BGM` → FAIL) |
| **Negative Invariant: MUSIC_ONLY** | MUSIC_ONLY strictly forbids `TEXT_TO_SPEECH`, `DIARIZATION`, and voice synthesis. | `assert_capability_allowed` | **PASS** (`MUSIC_ONLY invokes TTS` → FAIL) |
| **Epistemic Provenance** | Every important field carries `EXPLICIT`, `INFERRED`, `DEFAULTED`, or `UNKNOWN`. "Uncertain information must not become fact." | `ai.intent.parser.IntentParser` & `CreativeBriefBuilder` | **PASS** (0.00% unsupported inference rate) |
| **Contradiction Traceability** | Conflicting requests (e.g. silent + VO, no music + BGM) are detected, recorded, and testable without arbitrary silent defaults. | `_detect_contradictions` in `ai/intent/parser.py` | **PASS** (100.0% contradiction detection rate) |
| **Preservation of Legacy Assets** | Existing 18 legacy recipes (`recipes/*.json`) are wrapped/migrated into `RecipeDefinition`; zero files deleted. | `tests/ai/recipes/test_recipe_registry.py` | **PASS** (18/18 on disk, zero deleted) |
| **Hard Eligibility Runs First** | Incompatible recipes disqualified deterministically in Stage 1 before ranking or AI tie-breaks. | `RecipeSelector._evaluate_eligibility` | **PASS** (100% forbidden avoidance rate) |
| **Format Distinction** | Standard YouTube (16:9 landscape) does NOT match YouTube Shorts (9:16 vertical). | `_are_platforms_compatible` in `RecipeSelector` | **PASS** (Strict platform compatibility) |
| **S28-02 Dynamic Integration** | Selected recipe resolves bounded skills (`SkillRouter`) and knowledge (`KnowledgeRouter`) without dumping full registries. | `RecipeSelector.select_recipe` | **PASS** (Bounded skills/knowledge attached) |
| **Zero Contract Drift** | Python models, JSON Schemas (`schemas/creative/`), and TypeScript (`contracts/generated/`) remain 100% synchronized. | `python scripts/generate_creative_contracts.py --check` | **PASS** (0 drift) |

---

## 3. Legacy Migration & Recipe Registry Audit

All 18 legacy production recipes from `recipes/` were audited, migrated, and wrapped into canonical `RecipeDefinition` models:

| # | Recipe ID | Version | Owner | Supported Intents | Supported Platforms | Supported Audio Modes | Legacy Provider Audit |
|---|---|---|---|---|---|---|---|
| 1 | `agent-browser-proof` | 1.0.0 | core_media_team | SAAS_DEMO, TUTORIAL | youtube, linkedin, x_twitter, website | VO_ONLY, VO_MUSIC, MUSIC_ONLY, SILENT | Cleaned: elevenlabs |
| 2 | `avatar-explainer` | 1.0.0 | core_media_team | AVATAR_EXPLAINER, EXPLAINER | youtube, linkedin, x_twitter, website | VO_MUSIC, VO_ONLY | Cleaned: heygen, elevenlabs |
| 3 | `avatar-hook-broll` | 1.0.0 | core_media_team | AVATAR_EXPLAINER, DYNAMIC_MONTAGE | youtube_shorts, instagram_reels, tiktok | VO_MUSIC, VO_ONLY | Cleaned: heygen, elevenlabs |
| 4 | `avatar-insta-split` | 1.0.0 | core_media_team | AVATAR_EXPLAINER, SOCIAL_AD | instagram_reels, tiktok, youtube_shorts | VO_MUSIC, VO_ONLY | Cleaned: heygen, elevenlabs |
| 5 | `avatar-product-walkthrough` | 1.0.0 | core_media_team | SAAS_DEMO, AVATAR_EXPLAINER | youtube, linkedin, website | VO_MUSIC, VO_ONLY | Cleaned: heygen, elevenlabs |
| 6 | `avatar-vo-broll` | 1.0.0 | core_media_team | AVATAR_EXPLAINER, SOCIAL_AD | instagram_reels, tiktok, youtube_shorts | VO_MUSIC, VO_ONLY | Cleaned: heygen, elevenlabs |
| 7 | `captioned-talking-head` | 1.0.0 | core_media_team | TALKING_HEAD, PODCAST_SNIPPET | linkedin, youtube, instagram_reels, x_twitter | SOURCE_AUDIO, SOURCE_AUDIO_MUSIC | Cleaned: whisper |
| 8 | `dynamic-montage-ad` | 1.0.0 | core_media_team | DYNAMIC_MONTAGE, SOCIAL_AD | instagram_reels, tiktok, youtube_shorts | MUSIC_ONLY, VO_MUSIC, VO_ONLY | Cleaned: fal, elevenlabs |
| 9 | `faceless-broll-ad` | 1.0.0 | core_media_team | SOCIAL_AD, DYNAMIC_MONTAGE | tiktok, instagram_reels, facebook, youtube_shorts | VO_MUSIC, MUSIC_ONLY, VO_ONLY | Cleaned: elevenlabs |
| 10 | `living-canvas-explainer` | 1.0.0 | core_media_team | EXPLAINER, SAAS_DEMO | youtube, landing_page, product_hunt, linkedin, x_twitter | VO_MUSIC, MUSIC_ONLY, VO_ONLY | Cleaned: elevenlabs |
| 11 | `longform-repurpose` | 1.0.0 | core_media_team | PODCAST_SNIPPET, TALKING_HEAD | tiktok, instagram_reels, youtube_shorts, linkedin | SOURCE_AUDIO, SOURCE_AUDIO_MUSIC | Cleaned: whisper |
| 12 | `misotts-article-sprint` | 4.0.0 | core_media_team | ARTICLE_SPRINT, SOCIAL_AD | youtube_shorts, instagram_reels, tiktok | VO_MUSIC, VO_ONLY | Cleaned: elevenlabs, seedance |
| 13 | `motion-collage-explainer` | 1.0.0 | core_media_team | EXPLAINER, MOTION_GRAPHICS | youtube, youtube_shorts, tiktok, instagram_reels, linkedin | VO_MUSIC, MUSIC_ONLY, VO_ONLY | Cleaned: elevenlabs |
| 14 | `motion-graphics` | 1.0.0 | core_media_team | MOTION_GRAPHICS, EXPLAINER | youtube, linkedin, website, paid_ads | MUSIC_ONLY, VO_MUSIC, VO_ONLY, SILENT | Cleaned: none |
| 15 | `review-conquest-compilation` | 1.0.0 | core_media_team | COMPARATIVE_REVIEW, SOCIAL_PROOF | youtube, youtube_shorts, landing_page | VO_MUSIC, VO_ONLY | Cleaned: elevenlabs |
| 16 | `screencast-demo` | 1.0.0 | core_media_team | SAAS_DEMO, TUTORIAL | youtube, linkedin, website, product_hunt | MUSIC_ONLY, VO_MUSIC, VO_ONLY, SILENT | Cleaned: elevenlabs |
| 17 | `tabletop-levels-explainer` | 1.0.0 | core_media_team | EXPLAINER, PRODUCT_SHOWCASE | instagram_reels, youtube_shorts, tiktok | VO_MUSIC, VO_ONLY | Cleaned: elevenlabs |
| 18 | `ugc-ai-ad` | 1.0.0 | core_media_team | UGC_AD, SOCIAL_AD | tiktok, instagram_reels, facebook, youtube_shorts | VO_MUSIC, VO_ONLY | Cleaned: elevenlabs |

---

## 4. Part A: Intent Understanding & Creative Brief

### 4.1 Provenance-Driven Entity Extraction
The `IntentParser` and `CreativeBriefBuilder` process inputs across Arabic, English, and Mixed scripts. Every critical field in the `CreativeBrief` carries an explicit provenance record:
- **`EXPLICIT`**: Direct user assertion (e.g. `"بدون تعليق صوتي بس موسيقى"` → `audio_mode: MUSIC_ONLY`).
- **`INFERRED`**: Inferred deterministically from `MediaIntelligence` or provided assets (e.g. presence of speech audio or face detections).
- **`DEFAULTED`**: Canonical fallback applied when unspecified (e.g. `duration: 30s`).
- **`UNKNOWN`**: Intentionally preserved uncertainty when insufficient evidence exists.

### 4.2 Acceptance Test Verification
User Prompt:
```text
"بدي ريل سريع لمنتج SaaS بدون تعليق صوتي بس موسيقى وستايل clean."
```
Resolved Brief Properties:
- `video_type`: `SAAS_DEMO` (`provenance: EXPLICIT`)
- `target_platforms`: `["instagram_reels"]` (`provenance: EXPLICIT`)
- `audio_mode`: `MUSIC_ONLY` (`provenance: EXPLICIT`)
- `pace`: `FAST` (`provenance: EXPLICIT`)
- `style`: `CLEAN` (`provenance: EXPLICIT`)
- `target_duration_seconds`: `30.0` (`provenance: DEFAULTED`)
- `detected_contradictions`: `[]`

### 4.3 Intent Evaluation Benchmark Results
Machine-readable report: `documentation/audits/s28_03_intent_eval_report.json`
- **Total Cases Tested**: 16 (Arabic, English, Mixed, Short, Vague, Detailed, Contradictory)
- **Intent Accuracy**: **100.0%** (16/16)
- **Field Accuracy**: **100.0%** (16/16)
- **Unsupported Inference Rate**: **0.00%** (Zero fabricated facts)
- **Contradiction Detection Rate**: **100.0%** (3/3 contradictory requests caught)
- **Gate Status**: **PASSED**

---

## 5. Part B: Audio Mode Engine & Policies

### 5.1 Canonical Policies
Each mode implements a formal `AudioModePolicy`:

| Audio Mode | Required Capabilities | Forbidden Capabilities | Caption Policy | Music Policy | Mix Policy | Ducking Policy | Speech Policy |
|---|---|---|---|---|---|---|---|
| `MUSIC_ONLY` | `BEAT_DETECTION` | `TEXT_TO_SPEECH`, `DIARIZATION`, `SPEECH_ALIGNMENT`, `SPEECH_TO_TEXT`, `VOICE_ANALYSIS`, `LIP_SYNC` | FORBIDDEN | REQUIRED | MUSIC_BED_ONLY | DISABLED | FORBIDDEN |
| `VO_ONLY` | `TEXT_TO_SPEECH`, `SPEECH_ALIGNMENT` | `MUSIC_GENERATION` | OPTIONAL | FORBIDDEN | SPEECH_ONLY | DISABLED | REQUIRED |
| `VO_MUSIC` | `TEXT_TO_SPEECH`, `SPEECH_ALIGNMENT` | None | OPTIONAL | REQUIRED | SPEECH_AND_MUSIC | AUTO_DUCKING | REQUIRED |
| `SOURCE_AUDIO` | `SPEECH_TO_TEXT` | `TEXT_TO_SPEECH`, `MUSIC_GENERATION` | FROM_TRANSCRIPTION | FORBIDDEN | SOURCE_DIRECT | DISABLED | SOURCE_PRESERVED |
| `SOURCE_AUDIO_MUSIC`| `SPEECH_TO_TEXT` | `TEXT_TO_SPEECH` | FROM_TRANSCRIPTION | REQUIRED | SOURCE_AND_MUSIC | AUTO_DUCKING | SOURCE_PRESERVED |
| `SILENT` | None | `TEXT_TO_SPEECH`, `MUSIC_GENERATION`, `BEAT_DETECTION`, `AUDIO_ENHANCE`, `AUDIO_DENOISE`, `VOCAL_ISOLATION`, `SPEECH_ALIGNMENT`, `DIARIZATION`, `SPEECH_TO_TEXT`, `VOICE_ANALYSIS`, `LIP_SYNC` | FORBIDDEN | FORBIDDEN | NONE | DISABLED | FORBIDDEN |

### 5.2 Negative Requirement Invariant Execution Evidence
1. **`SILENT adds BGM` → FAIL**:
   ```python
   engine.enforce_audio_action(AudioMode.SILENT, "add_background_music")
   # Raises AudioPolicyViolationError: Action 'add_background_music' violated SILENT audio policy
   ```
2. **`MUSIC_ONLY invokes TTS` → FAIL**:
   ```python
   engine.assert_capability_allowed(AudioMode.MUSIC_ONLY, CapabilityType.TEXT_TO_SPEECH)
   # Raises AudioPolicyViolationError: Capability 'TEXT_TO_SPEECH' is strictly FORBIDDEN under audio mode 'MUSIC_ONLY'
   ```

---

## 6. Part C & D: Recipe Selection Engine & Matrix

### 6.1 Two-Stage Deterministic Selector
1. **Stage 1 (Hard Eligibility Gating)**:
   - Excluded templates/recipes from brief constraints eliminated.
   - Active `AudioMode` policy evaluated: recipes requiring forbidden capabilities disqualified.
   - Platform format compatibility enforced (`youtube` horizontal 16:9 strictly distinct from `youtube_shorts` 9:16).
   - Target duration evaluated only when provenance is `EXPLICIT` (preventing arbitrary default durations from excluding longform content).
   - Talking Head contradiction enforced (Section 34): talking head recipes disqualified under `MUSIC_ONLY` or `SILENT`, or when no speech source asset is present.
2. **Stage 2 (Multidimensional Scoring & Ranking)**:
   - Video type match (+0.30)
   - Keyword relevance matches (+0.05 per hit up to +0.20)
   - Negative keyword penalty (-0.40)
   - Budget profile alignment (+0.10)
   - Deterministic tie-breaking on `(score, recipe_id)`

### 6.2 Recipe Selection Matrix Benchmark Results
Machine-readable report: `documentation/audits/s28_03_recipe_eval_report.json`
- **Total Cases Tested**: 10
- **Selection Accuracy**: **100.0%** (10/10)
- **Forbidden Recipe Avoidance Rate**: **100.0%** (23/23 forbidden checks avoided)
- **Cases Passed**: 10/10
- **Cases Failed**: 0
- **Gate Status**: **PASSED**

---

## 7. Part E: Integration with S28-02 Platform

The `RecipeSelector` integrates directly with the S28-02 knowledge and skill platforms:
- Resolves relevant skills via `SkillRouter`: bounded skill descriptors attached to `RecipeSelection.required_skills`.
- Resolves grounded domain documentation via `KnowledgeRouter`: bounded knowledge descriptors attached to `RecipeSelection.required_knowledge`.
- Complete bounding guarantees: entire registry dumps are prohibited, and skill tool execution boundaries remain strictly enforced.

---

## 8. Test Execution Evidence

### 8.1 Pytest Test Suite
Executed command:
```bash
.venv/bin/pytest tests/ai/audio/test_audio_mode_engine.py \
                 tests/ai/recipes/test_recipe_registry.py \
                 tests/ai/recipes/test_recipe_selector.py \
                 tests/ai/intent/test_intent_parser.py \
                 tests/ai/integration/test_s28_03_e2e_pipeline.py \
                 tests/ai/security/test_s28_03_architecture_guards.py \
                 tests/ai/evals/test_creative_evals.py \
                 -v
```
**Result: 35 passed in 1.86s (100% pass rate)**

Comprehensive S28-01, S28-02, and S28-03 combined run:
```bash
.venv/bin/pytest tests/ai/contracts/test_creative_contracts.py \
                 tests/ai/knowledge/ tests/ai/skills/ tests/ai/integration/ \
                 tests/ai/evals/ tests/ai/security/ tests/ai/audio/ \
                 tests/ai/recipes/ tests/ai/intent/ -v
```
**Result: 120 passed in 6.54s (100% pass rate, 0 failures, 0 regressions)**

### 8.2 Vitest Parity Suite
Executed command:
```bash
npx vitest run tests/remotion/creative_contracts_parity.test.ts
```
**Result: 6 passed in 195ms (100% pass rate)**

### 8.3 Contract Drift Check
Executed command:
```bash
.venv/bin/python scripts/generate_creative_contracts.py --check
```
**Result: 0 drift detected across 24 JSON Schemas and TypeScript files.**

---

## 9. Exit Gate Checklist Audit

| Item | Requirement | Evidence | Status |
|---|---|---|:---:|
| 1 | All 18 legacy recipes migrated to typed `RecipeDefinition` | `tests/ai/recipes/test_recipe_registry.py` | ✅ |
| 2 | Zero legacy recipes deleted on disk | `recipes/*.json` count = 18 verified | ✅ |
| 3 | `Recipe ≠ Provider` invariant strictly enforced | `assert_provider_neutral` in registry & guards | ✅ |
| 4 | All 6 canonical `AudioMode` policies registered | `AudioModeEngine.get_all_policies()` (6 policies) | ✅ |
| 5 | Negative requirement: `SILENT adds BGM` → FAIL | `test_negative_silent_adds_bgm_fails` | ✅ |
| 6 | Negative requirement: `MUSIC_ONLY invokes TTS` → FAIL | `test_negative_music_only_invokes_tts_fails` | ✅ |
| 7 | Intent Parser supports Arabic, English, and Mixed scripts | `test_intent_parser.py` & `intent_dataset.json` | ✅ |
| 8 | Per-field epistemic provenance (`EXPLICIT`, `INFERRED`, `DEFAULTED`, `UNKNOWN`) | `FieldProvenance` in `CreativeBrief` | ✅ |
| 9 | "Uncertain information must not become fact" invariant | `test_vague_request_preserves_uncertainty` (0% unsupported) | ✅ |
| 10 | Contradiction handling detectable, traceable, testable | `test_contradiction_detection_*` | ✅ |
| 11 | Intent Evaluation Benchmark passing | `s28_03_intent_eval_report.json` (100% accuracy) | ✅ |
| 12 | Recipe Selection Matrix Benchmark passing | `s28_03_recipe_eval_report.json` (100% accuracy) | ✅ |
| 13 | Two-stage deterministic recipe selection | Stage 1 hard gating + Stage 2 ranking in `RecipeSelector` | ✅ |
| 14 | Platform format distinction (`youtube` vs `youtube_shorts`) | `_are_platforms_compatible` in `RecipeSelector` | ✅ |
| 15 | Talking head contradiction gating (Section 34) | `test_selector_disqualifies_talking_head_without_speech` | ✅ |
| 16 | S28-02 Knowledge and Skill platform integration | `test_s28_03_e2e_pipeline.py` | ✅ |
| 17 | Non-goal boundaries: no Narrative/Taste/Creative Planner built | `test_guard_non_goals_not_imported_in_s28_03` | ✅ |
| 18 | Authority boundaries: no core auth or tenant mutation | `test_guard_s28_03_no_core_auth_or_tenant_mutations` | ✅ |
| 19 | Python ↔ JSON Schema ↔ TypeScript 100% parity | `generate_creative_contracts.py --check` & Vitest | ✅ |
| 20 | Machine-readable audit reports generated and saved | `documentation/audits/s28_03_*_eval_report.json` | ✅ |

---

## 10. Conclusion & Recommendation

All milestones, architectural invariants, negative requirements, evaluation benchmarks, and quality gates for **S28-03** have been met with zero regressions and zero contract drift.

**Stage S28-03 is formally CLOSED and certified ready for S28-04 (Narrative & Visual Intelligence Platform).**
