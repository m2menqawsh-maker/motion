# S28-08A — User Personalization & Creative Feedback Learning Report

## Metadata
- **Stage:** S28-08A (User Personalization & Creative Feedback Learning)
- **Status:** **PASS**
- **Date:** 2026-10-03
- **Authority:** Architecture Level 3 / ADR-004 DEC-01
- **Target Modules:**
  - Contracts: `ai/contracts/creative/feedback.py`, `ai/contracts/creative/__init__.py`
  - Feedback Subsystem: `ai/feedback/classifier.py`, `ai/feedback/service.py`, `ai/feedback/__init__.py`
  - Style Subsystem: `ai/style/resolver.py`, `ai/style/__init__.py`
  - Planning Integration: `ai/planning/creative_planner.py`
  - S27 Memory Integration: `ai/memory/service.py`, `ai/memory/deduplication.py`, `ai/memory/policy.py`

---

## 1. Executive Summary

`S28-08A` establishes the foundational personalization and creative feedback learning loop for the `clean-video-workspace` video generation platform. It empowers the system to:
1. Remember useful user style preferences across creative dimensions.
2. Learn carefully from explicit human feedback without over-generalizing single actions into permanent rules.
3. Apply stored preferences to downstream creative planning via compact, auditable context.

### The Non-Negotiable Core Invariant
```text
Current explicit request ALWAYS overrides remembered preferences.
```

Precedence hierarchy:
```text
Current explicit request
  > Project / Brand constraints
    > Confirmed user preferences
      > Inferred preferences
        > Global platform defaults
```

### Core Authority Invariants
- `Memory ≠ Current Request Authority`: Stored memory is advisory; it can never dictate or override an active user brief.
- `Preference ≠ Hard Constraint`: A stylistic preference cannot violate `AudioMode`, security boundaries, or tier policies.
- `Feedback ≠ Permanent Preference`: A single local complaint on a scene never automatically creates a global permanent profile rule.
- `Single Action ≠ Permanent Truth`: Removing music once in a project does not mark music as permanently forbidden.
- `AI Inference ≠ Confirmed User Preference`: System hypotheses start as `INFERRED` with low confidence; only repeated evidence promotes them to `CONFIRMED`.
- `Zero AI Authority Forgery`: Model or client `confidence=1.0` is ignored; confidence and epistemic status are strictly computed and governed by server-side domain policy.
- `Zero Secondary Memory Stores`: Extends and strictly reuses the canonical S27 Memory System (`ai/memory/`). No second database, table, or shadow storage was created.

---

## 2. Contracts & TypeScript Parity

All contracts were defined using Pydantic v2 with strict immutability (`frozen=True`, `extra="forbid"`), verified against JSON Schema generators and TypeScript runtime bindings.

### 2.1 `UserStyleProfile`
Represents an aggregated, multi-dimensional user profile loaded from canonical S27 memory:
- `pacing_preference`: Optional string (`fast`, `slow`, `calm`, `moderate`)
- `motion_intensity`: Optional string (`high`, `low`, `medium`)
- `preferred_motion_personality`: Optional string (`Cinematic`, `EnergeticSnap`, `FluidContinuous`)
- `text_density`: Optional string (`compact`, `balanced`, `heavy`)
- `caption_style`: Optional string (`minimal`, `standard`, `prominent`, `compact`)
- `music_tendencies`: Optional string (`energetic`, `ambient`, `none`, `avoid_electronic`)
- `transition_preference`: Optional string (`cut`, `whip`, `dissolve`, `fade`)
- `visual_complexity`: Optional string (`minimal`, `clean`, `rich`)
- `preferred_color_palette`: List of hex color strings
- `preferred_voices`: List of voice profile IDs
- `disliked_patterns`: List of stylistic antipatterns
- `provenance_by_dimension`: Mapping of dimension name to `StylePreferenceProvenance`

### 2.2 `StylePreferenceProvenance`
Tracks the exact lineage and epistemic validity of each individual preference dimension:
- `dimension`: Style dimension name
- `epistemic_status`: `EXPLICIT`, `CONFIRMED`, or `INFERRED`
- `confidence`: Domain-governed confidence score (`0.0` to `1.0`)
- `source_type`: `USER_STATEMENT`, `USER_ACTION`, `FEEDBACK_INFERENCE`, `SYSTEM_DEFAULT`
- `evidence_count`: Monotonically incremented evidence occurrences
- `last_observed_at`: UTC timestamp of latest corroborating evidence
- `source_id`: Originating memory entry or feedback ID
- `rationale`: Human-readable summary of provenance

### 2.3 `FeedbackClassification`
Structured output produced by `FeedbackClassifier` from raw feedback:
- `classification_id`: Server-generated UUID
- `feedback_id`: Originating feedback ID
- `workspace_id` & `user_id`: Tenant boundary context
- `project_id`: Project scope if project-bound
- `target_type`: `SCENE`, `PROJECT`, `TEMPLATE`, `VIDEO_TYPE`, `GENERAL_STYLE`
- `category`: `PACING`, `MOTION`, `MUSIC`, `CAPTION`, `VISUAL`, `TRANSITION`, `VOICE`, `GENERAL`
- `sentiment`: `POSITIVE`, `NEGATIVE`, `NEUTRAL`, `CONSTRUCTIVE`
- `preference_dimension`: Target creative dimension
- `proposed_value`: Extracted preference value
- `scope`: `MemoryScope.USER` or `MemoryScope.PROJECT`
- `confidence`: Domain-assigned score (e.g. 0.4 for scene inference, 0.9 for explicit rule)
- `source`: `SourceType.USER_STATEMENT` or `SourceType.FEEDBACK_INFERENCE`
- `is_explicit_general_rule`: Boolean flag

### 2.4 `EffectiveUserStyle`
Compact, structured context delivered downstream to `CreativePlanner`:
- Delivers **only** the preferences relevant to the current brief with resolved values.
- Does **not** dump raw memory history or unstructured logs into LLM context.
- Contains `trace_records`: List of `StyleDecisionTrace` documenting every considered dimension, the winner, whether an override occurred, and why.

### 2.5 `StyleDecisionTrace`
Auditable, deterministic trace entry generated per dimension without hidden chain-of-thought:
- `dimension`: Dimension evaluated
- `considered_value`: Stored profile value considered
- `considered_source`: Provenance of considered preference
- `considered_confidence`: Confidence of considered preference
- `applied_value`: Final effective style value chosen
- `is_overridden`: Boolean flag (true if a higher-priority source superseded stored preference)
- `override_reason`: Structured explanation (e.g., `"Current explicit brief request overrides stored user preference"`)
- `winning_source`: `CURRENT_REQUEST`, `BRAND_CONSTRAINT`, `CONFIRMED_USER_PREFERENCE`, `INFERRED_PREFERENCE`, `GLOBAL_DEFAULT`

### 2.6 Parity Verification
- **JSON Schemas**: 49 schemas regenerated via `python scripts/generate_creative_contracts.py`.
- **TypeScript**: `contracts/generated/creative_contracts.ts` and `remotion-app/src/types/creative_contracts.ts` updated.
- **Vitest**: `tests/remotion/creative_contracts_parity.test.ts` passed 13/13 tests cleanly.

---

## 3. Architecture & Implementation

```text
========================================================================================
                      S28-08A PERSONALIZATION & LEARNING FLOW
========================================================================================

    [ User Feedback ]
           │
           ▼
    ┌───────────────────────────────┐
    │ FeedbackClassifier            │ ── Deterministic regex/semantic parsing (Ar & En)
    │ (ai/feedback/classifier.py)   │ ── Domain assigns confidence (0.4 scene, 0.9 explicit)
    └───────────────────────────────┘ ── Rejects forged client confidence & malformed data
           │
           ▼
    ┌───────────────────────────────┐
    │ CreativeFeedbackService       │ ── Authoritative Multi-Tenant Boundary Validation
    │ (ai/feedback/service.py)      │ ── Formulates canonical S27 MemoryCandidate
    └───────────────────────────────┘
           │
           ▼
    ┌───────────────────────────────┐
    │ S27 MemoryPolicy              │ ── Single Scene Critique: REQUIRE_CONFIRMATION (persisted=False)
    │ (ai/memory/policy.py)         │ ── Repeated Feedback: MERGE (reinforces confidence)
    └───────────────────────────────┘ ── Contradiction: SUPERSEDE (retires stale entry)
           │
           ▼
    ┌───────────────────────────────┐
    │ S27 MemoryRepository          │ ── Canonical Memory Storage (Zero duplicate databases)
    └───────────────────────────────┘
           │
           │ (Downstream Planning Request)
           ▼
    ┌───────────────────────────────┐
    │ UserStyleResolver             │ ── Loads active USER_PREFERENCE entries
    │ (ai/style/resolver.py)        │ ── Evaluates 5-tier Precedence Hierarchy
    └───────────────────────────────┘ ── Generates Auditable StyleDecisionTrace per dimension
           │
           ▼
    ┌───────────────────────────────┐
    │ EffectiveUserStyle            │ ── Compact style context (no raw history dump)
    └───────────────────────────────┘
           │
           ▼
    ┌───────────────────────────────┐
    │ CreativePlanner               │ ── Integrates style into scene motion personalities
    │ (ai/planning/)                │ ── Invariant: AudioMode.SILENT immune to preferences
    └───────────────────────────────┘ ── Invariant: Plan status strictly PROPOSED (no QC mutation)
========================================================================================
```

### 3.1 Feedback Classification (`ai/feedback/classifier.py`)
- Distinguishes local scene complaints (e.g., `"هذا المشهد حركته كثيرة"` -> `target_type=SCENE`, `confidence=0.4`) from persistent rules (e.g., `"أنا دائمًا ما بحب الحركات السريعة"` -> `target_type=GENERAL_STYLE`, `confidence=0.9`).
- Handles both Arabic and English semantic patterns for pacing, motion intensity, music tendencies, caption styles, visual complexity, and forbidden patterns.
- Clamps client-supplied confidence and source types; untrusted parameters cannot promote an inference to explicit status.

### 3.2 Creative Feedback Learning Service (`ai/feedback/service.py`)
- Enforces strict tenant and user authorization (`context.workspace_id == feedback.workspace_id`, `context.can_access_project()`, `context.can_access_user()`).
- Normalizes `structured_payload` to `{"dimension": ..., "value": ...}` so canonical `MemoryPolicy` content hashing detects duplicate/contradictory candidates deterministically.
- Delegates candidate writing to `MemoryService.propose_candidate()`, guaranteeing that:
  - Single local inferences are flagged `REQUIRE_CONFIRMATION` (not saved as permanent preferences).
  - Explicit general rules pass `DIRECT_WRITE` as `EpistemicStatus.EXPLICIT`.
  - Repeated identical feedback triggers `MERGE` to reinforce confidence.
  - Contradictory feedback triggers `SUPERSEDE`, archiving the previous preference and preserving historical auditability.

### 3.3 Memory Service & Deduplication Fixes (`ai/memory/`)
- Updated `supersede_memory` and `propose_candidate` in `ai/memory/service.py` to accept and persist the new candidate's `structured_payload` when replacing an existing entry, ensuring structured queries reflect the new preference value.
- Extended `ai/memory/deduplication.py` with dimension-aware comparison (`is_contradictory_preference`) for `motion`, `intensity`, `density`, and `complexity`.

### 3.4 User Style Resolver (`ai/style/resolver.py`)
- `load_profile`: Queries active `MemoryType.USER_PREFERENCE` entries filtered by `TrustedTenantContext`. Synthesizes a valid `UserStyleProfile` with per-dimension provenance tracking.
- `resolve_effective_style`: Strictly executes the canonical precedence ladder:
  1. `CURRENT_REQUEST`: Evaluates explicit directives in `brief.prompt`, `brief.script_content`, or `brief.constraints`.
  2. `BRAND_CONSTRAINT`: Evaluates brand guidelines and project-level restrictions.
  3. `CONFIRMED_USER_PREFERENCE`: Evaluates stored preferences with `EpistemicStatus.CONFIRMED` or `EXPLICIT`.
  4. `INFERRED_PREFERENCE`: Evaluates stored preferences with `EpistemicStatus.INFERRED`.
  5. `GLOBAL_DEFAULT`: Applies canonical platform fallbacks.
- Generates a structured `StyleDecisionTrace` for each dimension recording `considered_value`, `applied_value`, `is_overridden`, `override_reason`, and `winning_source`.

### 3.5 Creative Planner Integration (`ai/planning/creative_planner.py`)
- Accepts `effective_user_style: Optional[EffectiveUserStyle]`.
- If a raw `user_style: Optional[UserStyleProfile]` is passed instead, automatically resolves it via `UserStyleResolver.resolve_effective_style` with the caller's brief and tenant boundary.
- Applies personalized motion personality to scenes when not overridden by explicit director instructions.
- Enforces hard audio invariants:
  - `AudioMode.SILENT` unconditionally produces `silent_mode_no_audio` and zero spoken text, completely immune to user style music preferences.
  - `AudioMode.VO_MUSIC` with user preference `music_preference="none"` suppresses background music into `focused_voiceover_track` while preserving spoken narration.
  - Guarantees plan status remains strictly `PROPOSED` (cannot award QC pass or mutate tier decisions).

---

## 4. Test Evidence & Gate Verification

A comprehensive test suite of 46 dedicated tests covering all sections of the S28-08A specification was executed and verified:

```text
========================================================================================
                                 S28-08A TEST MATRIX
========================================================================================
Test Suite                                         Passed / Total     Status
----------------------------------------------------------------------------------------
Current Request Wins Critical Gate (Sec. 16)       2 / 2              PASS
Style Resolver Precedence Suite (Sec. 6, 7, 17)    6 / 6              PASS
UserStyleProfile Contract Suite (Sec. 4, 5)        7 / 7              PASS
Feedback Classification Suite (Sec. 9, 10)         8 / 8              PASS
Feedback Learning Service Suite (Sec. 8, 11, 12)   5 / 5              PASS
Multi-Tenant Isolation Suite (Sec. 19)             6 / 6              PASS
Planner Personalization Integration (Sec. 13-15)   6 / 6              PASS
S28-08A Architecture Guards (Sec. 2, 3, 20)        6 / 6              PASS
----------------------------------------------------------------------------------------
S28-08A Total Python Suite                         46 / 46            PASS
Creative Contracts Parity (Vitest)                 13 / 13            PASS
Preceding Creative Intelligence Regression         282 / 282          PASS
========================================================================================
```

### 4.1 Critical Gate: Section 16 "Current Request Wins" Verification
- **Scenario Tested**:
  - Stored Profile: `pacing_preference="fast"`, `motion_intensity="high"`, `music_tendencies="energetic"`, `preferred_motion_personality="EnergeticSnap"`.
  - Current Request: `"اعمل الفيديو هادئ، حركة بسيطة، بدون موسيقى"` (Make video calm, low motion, without music) with `AudioMode.SILENT`.
- **Results Verified**:
  - `pacing` resolved to `"calm"` (Winning Source: `CURRENT_REQUEST`, overridden=True).
  - `motion_intensity` resolved to `"low"` (Winning Source: `CURRENT_REQUEST`, overridden=True).
  - `motion_personality` resolved to `"Cinematic"` (calm baseline, overridden=True).
  - `music_preference` resolved to `"none"` (Winning Source: `CURRENT_REQUEST`, overridden=True).
  - E2E CreativePlan: All scenes have `motion_personality="Cinematic"`, `spoken_text=None`, `audio_intent="silent_mode_no_audio"`.
  - All decision traces explicitly record `override_reason="Current explicit brief request overrides stored user preference"`.

### 4.2 Multi-Tenant & User Isolation Verification (Section 19)
- **User A vs User B**: Alice and Bob in the same workspace have strictly isolated personal preference profiles; Bob cannot read Alice's stored pacing preference.
- **Cross-Workspace Mutation**: A caller in Workspace Alpha attempting to submit feedback claiming `workspace_id="ws_beta"` is immediately rejected with `TenantAuthorizationError`.
- **Cross-User Mutation**: An actor in Workspace Alpha attempting to submit feedback for a user they cannot access fails closed with `TenantAuthorizationError`.
- **Project Boundary Confinement**: Submitting feedback on an unpermitted `project_id` fails closed.
- **Cross-Tenant Query Fails Closed**: Mismatched tenant query requests raise `TenantAuthorizationError` without leaking metadata.
- **End-to-End Workspace Isolation**: Simultaneous feedback in `ws_alpha` (fast pacing) and `ws_beta` (slow pacing) updates only the respective tenant profiles.

### 4.3 Architecture Guards Verification (`test_s28_08a_architecture_guards.py`)
- **Rule S28-08A-01 (No Secondary Memory)**: Verified AST of `ai/style` and `ai/feedback` contains zero imports of sqlite3, psycopg2, mysql, redis, etc., and zero raw SQL statements.
- **Rule S28-08A-02 (Zero Registry Writes)**: Verified style and feedback modules contain zero references or write calls targeting Canonical Template Registry files (`template-registry-data.json`, `template-registry.tsx`, `template_catalog.json`, etc.).
- **Rule S28-08A-03 (Zero Lifecycle Mutations)**: Verified zero writes targeting `.pipeline_state.json`, `.qc_passed`, `studio_approved`, `STATIC_PASS`, or `RUNTIME_PASS`.
- **Rule S28-08A-04 (Contract Immutability)**: Verified `UserStyleProfile`, `EffectiveUserStyle`, `FeedbackClassification`, and `StyleDecisionTrace` enforce `frozen=True` and `extra="forbid"`.
- **Rule S28-08A-06 (Precedence Ranking)**: Verified `WinningSource.CURRENT_REQUEST` is strictly ranked at highest precedence.

---

## 5. Scope Boundary & Non-Goals

`S28-08A` is strictly bounded to personalization contracts, feedback classification, memory policy learning integration, user style resolution, and planner integration.

The following items are **explicitly out of scope** and deferred to future stages (S28-08B+):
1. Creative trace grading and evaluation harness.
2. Multi-tier regression evaluation frameworks.
3. Cost and latency performance dashboards.
4. Legacy creative script deletion and filesystem pruning.
5. Final master S28 architecture closure audit.

---

## 6. Final Stage Verdict

```text
========================================================================================
                               S28-08A — FINAL VERDICT
========================================================================================
  Mission:                  User Personalization & Creative Feedback Learning
  Current Request Wins:     VERIFIED (Section 16 Gate PASS)
  S27 Memory Reuse:         VERIFIED (Zero secondary storage)
  Single Action != Truth:   VERIFIED (Domain policy mediated)
  Tenant Isolation:         VERIFIED (Strict boundary enforcement)
  Architecture Guards:      VERIFIED (AST analysis PASS)
  TypeScript Parity:        VERIFIED (13/13 Vitest PASS)
  Regressions:              ZERO (282/282 upstream creative tests PASS)

  OVERALL VERDICT:          PASS
========================================================================================
```
