# S28 — Creative Intelligence Platform: Architectural Foundation & Contracts

## Metadata
- **Status:** APPROVED & FROZEN (S28-01 Foundation)
- **Target:** S28 Creative Intelligence Platform (`ai/contracts/creative/`, `schemas/creative/`, `contracts/generated/creative_contracts.ts`)
- **Authority:** Architecture Level 3
- **Supersedes:** Monolithic legacy decision guidelines in `references/ROUTER.md`

---

## 1. Executive Summary

The **Creative Intelligence Platform (S28)** introduces formal creative reasoning, style governance, recipe orchestration, and template evolution to `clean-video-workspace`. 

Following the strict boundary established in S27 (ADR-004), Creative Intelligence acts purely as an **advisory and proposal engine**. It never assumes ownership over Core lifecycle, authorization, QC acceptance, or the Canonical Template Registry.

```text
User Request (Request Authority)
       ↓
CreativeBrief (Interpreted Intent)
       ↓
CreativePlan (Creative Proposal: Narrative, Scenes, Taste Decisions)
       ↓ [Compiler]
Blueprint v2 (Canonical Executable Project Contract)
       ↓
Domain Services & Lifecycle Gates (StateStore, ReviewService, QC)
       ↓
Remotion Engine Runtime & Render
```

### 1.1 S28 Stage Breakdown & Ownership

The Creative Intelligence Platform is delivered across strictly phased stages:
- **S28-01:** Creative Foundation, Inventory & Contracts
- **S28-02:** Knowledge + Skills Platform
- **S28-03:** Intent + Creative Brief + Recipe Engine + Audio Modes
- **S28-04:** Narrative + Taste Engine
- **S28-05:** CreativePlan + Blueprint Compiler
- **S28-06:** REUSE + COMPOSE + Tier Policy
- **S28-07:** CREATE + Candidate + Validation + Approval + Promotion

---

## 2. Official S28 Vocabulary

To eliminate ambiguity across Python, TypeScript, documentation, and agent reasoning, the following concepts are defined with strict semantic boundaries:

### 2.1 Core Conceptual Triad: Knowledge, Skill, Recipe

| Concept | Formal Definition | Semantic Boundary | Anti-Pattern to Reject |
| :--- | :--- | :--- | :--- |
| **Knowledge** | Information, design heuristics, playbooks, guidelines, and historical craft experience relied upon by the system (e.g., Disney 12 principles, copywriting SOPs, motion physics). | **Knowledge = Information & Experience**<br>`Knowledge ≠ Runtime Authority` | Treating reference markdown files as executable state or pipeline gates. |
| **Skill** | How the system handles a specific task type (e.g., motion typography, avatar explainer, B-roll assembly, screen recording). Specifies required capabilities and applicable recipes. | **Skill = How the system handles a task type**<br>`Skill ≠ Permission`<br>`Skill ≠ Tool` | Granting filesystem write permissions or equating a skill to an individual CLI tool. |
| **Recipe** | What happens and in what order across a video production workflow (stages, sequencing, platforms, deliverables, required capabilities). | **Recipe = What happens and in what order**<br>`Recipe ≠ Prompt`<br>`Recipe ≠ Provider` | Hardcoding cloud vendor names (`heygen`, `elevenlabs`) or large prompts inside recipes. |
| **Capability** | An executable, provider-neutral media operation provided by the platform (e.g., `TEXT_TO_SPEECH`, `VIDEO_GENERATION`, `BACKGROUND_REMOVAL`). | **Capability = Executable operation provided by the system** | Direct provider API calls bypassing the capability routing layer. |

---

### 2.2 Intent & Planning Concepts

| Concept | Formal Definition | Semantic Boundary |
| :--- | :--- | :--- |
| **CreativeBrief** | The structured specification of a creative project, containing raw user requests, interpreted intent, constraints, and provenance. | Structured input contract capturing what the user wants. |
| **CreativeIntent** | High-level creative goals, target audience, tone, core takeaway, and target distribution channels. | Expresses purpose and message. |
| **CreativeConstraints** | Technical and stylistic boundaries: duration bounds, aspect ratios, audio mode (`MUSIC_ONLY`, `VO_ONLY`, `VO_MUSIC`, `SOURCE_AUDIO`, `SOURCE_AUDIO_MUSIC`, `SILENT`), brand color palette, excluded templates, and safe zones. | Hard bounds within which planning must operate. |
| **NarrativePlan** | The multi-beat story arc structuring the message prior to visual composition (arc structure, core hook, beat sequence). | Pure story/editorial structure. |
| **NarrativeBeat** | An individual story beat within a NarrativePlan, defining phase (hook, setup, proof, cta), emotional target, pacing, and duration. | Atomic unit of narrative progression. |
| **CreativePlan** | The comprehensive creative proposal specifying scenes, composition plans, taste decisions, and tier selections. | **CreativePlan = What we want to create creatively**<br>`CreativePlan ≠ Blueprint` |
| **SceneIntent** | The creative styling and intent for an individual scene (mood, motion personality, visual job, duration, spoken text, taste citations). | Intent for a single scene unit. |
| **CompositionPlan** | Spatial layout, multi-layer hierarchy (Primary, Secondary, Ambient), camera motion, visual gestures, and SFX bindings for a scene. | Layout and visual choreography proposal. |

---

### 2.3 Taste & Style Concepts

| Concept | Formal Definition | Semantic Boundary |
| :--- | :--- | :--- |
| **Taste Rule** | A creative principle or rule influencing creative decisions (e.g., Beat Density, Double Variance, Gestural Sync, 1/3 Screen Rule, Color Discipline). | **Taste Rule = Creative principle influencing decisions**<br>`Taste ≠ QC` |
| **Taste Decision** | An applied choice grounded in a specific Taste Rule for a concrete scene or shot, citing the exact rule and rationale. | Documented application of a taste rule. |
| **UserStyleProfile** | Persistent preferences of a user or workspace regarding motion personality, color palettes, pacing, and taste rules. | Personalization data informing planning. |
| **CreativeFeedback** | Structured user feedback on a creative plan or rendered video (rating, liked/disliked aspects, critique) to inform style learning. | Learning and refinement signal. |

---

### 2.4 Template Evolution & Tier Concepts

| Concept | Formal Definition | Semantic Boundary |
| :--- | :--- | :--- |
| **CreativeTier** | Architectural classification of visual implementation tiers adhering to the canonical S28 creativity policy:<br>• `REUSE`: Canonical registered template from the template catalog (highest predictability, zero new code).<br>• `COMPOSE`: Composed from verified primitive Lego blocks in `templates/elements` and `scenes/`.<br>• `CREATE`: Novel scene/template candidate generation requiring candidate quarantine and promotion evaluation. | Execution strategy classification adhering to the canonical S28 creativity policy (`REUSE` → `COMPOSE` → `CREATE`). |
| **CreativeTierDecision** | The explicit decision choosing a CreativeTier for a scene, accompanied by rationale, element references, and an optional `needs_create_evaluation` flag before allowing novel candidate authoring. | Explicit tier selection record. |
| **TemplateCandidate** | A proposed template candidate created during custom project development (e.g., in `templates/custom/`), undergoing validation. | **Candidate = Proposed template undergoing review**<br>`Candidate ≠ Approved/Registered Template` |
| **CandidateValidationReport** | Automated validation report verifying TypeScript compilation, security purity, documentation, and quality score. | Objective gate checking candidate quality. |
| **PromotionDecision** | An explicit governance decision to promote a validated candidate into the canonical Template Registry. | **Promotion requires authorized human/registry decision**<br>`AI ≠ Canonical Registry Authority` |

---

## 3. Core Architectural Invariants

The following non-negotiable boundaries are strictly enforced across code, tests, and CI gates:

1. **Knowledge ≠ Runtime Authority**: Reference guides in `references/` inform planning heuristics but have zero execution or gating authority. The deterministic Core and Stage Gates hold runtime authority.
2. **Skill ≠ Permission**: A Skill encapsulates operational know-how. It conveys no execution permissions or filesystem access rights.
3. **Skill ≠ Tool**: A Skill coordinates tasks; tools are discrete capability executions mediated by Domain Services.
4. **Recipe ≠ Prompt**: A Recipe specifies workflow topology, sequencing, and deliverables. It is not an unconstrained LLM prompt.
5. **Recipe ≠ Provider**: Recipes describe platform requirements via provider-neutral `CapabilityType`. Recipes never import or invoke vendor SDKs (`elevenlabs`, `heygen`, `fal`) directly.
6. **Taste ≠ QC**: Taste guides aesthetic choices and creative proposals. QC (`probe_qc.py`, `final_qc.py`) evaluates objective technical and compliance acceptance. Taste never overrides QC.
7. **CreativePlan ≠ Blueprint**: A `CreativePlan` is a proposed creative structure (`PROPOSED`). A `Blueprint` (`05_blueprint.json`) is the canonical, locked, executable project contract.
8. **Candidate ≠ Approved/Registered Template**: A `TemplateCandidate` lives in quarantine/proposal storage. It cannot be rendered in production pipelines until formally certified and promoted.
9. **AI ≠ Lifecycle Authority**: AI cannot modify `.pipeline_state.json` or alter `state.lifecycle_state`. State transitions are governed exclusively by `Lifecycle / Transition Services` (`scripts/core/lifecycle_service.py`), with durable persistence and CAS validation enforced by PostgreSQL / `StateStore`.
10. **AI ≠ Authorization Authority**: AI cannot generate or sign `.studio_approved`, `.studio_unlocked`, or `ReviewDecision`. Render authorization requires explicit human or authenticated service action.
11. **AI ≠ QC Authority**: AI cannot forge QC reports, alter failure verdicts, or mark a rejected video as passed.
12. **AI ≠ Canonical Registry Authority**: AI cannot write to or mutate `templates/` or `registry/template-registry-data.json`. Template promotion requires formal certification and human/domain sign-off.

---

## 4. Authority Matrix

| Domain / Concept | Canonical Authority | Representation Role | Consumer | Invariant / Boundary |
| :--- | :--- | :--- | :--- | :--- |
| **User Request** | Human User | Request Authority | CreativeBrief Interpreter | Ultimate intent authority. |
| **CreativeBrief** | `ai.contracts.creative.CreativeBrief` | Interpreted Intent | Narrative & Creative Planner | Canonical structured brief; contains raw prompt + provenance. |
| **CreativePlan** | `ai.contracts.creative.CreativePlan` | Creative Proposal | Blueprint Compiler, Human Reviewer | Advisory proposal; non-executable; requires user approval. |
| **Blueprint v2** | `contracts/blueprint.ts` (`BlueprintV2Schema`) | Executable Contract | Remotion Runtime, Probe QC | Sole canonical execution truth for renderable composition. |
| **Template Registry** | `registry/template-registry-data.json` | Reusable Template Authority | Template Registry, Template Router | Sole authoritative metadata for certified reusable templates. |
| **QC & Compliance** | `scripts/gates/probe_qc.py`, `final_qc.py` | Acceptance Authority | Pipeline Orchestrator, ReviewService | Deterministic technical pass/fail; overrides all creative suggestions. |
| **Render Authorization** | `scripts/core/review_service.ReviewService` | Render Authorization Authority | `render_project.py`, `open_studio.py` | Governs access to render execution via cryptographic/digested bundles. |
| **Lifecycle Transition** | `scripts/core/lifecycle_service.LifecycleService` / Transition Service | Transition Decision Authority | `pipeline.py`, Domain Services | Governs `.pipeline_state.json` state machine transitions and valid lifecycle progression. |
| **State Persistence** | `scripts/core/state_store.StateStore` / PostgreSQL repository | Durable Persistence + CAS Authority | `LifecycleService`, Pipeline Services | Provides atomic read/write, durable persistence, and CAS validation; does not decide transition business logic. |

---

## 5. Contract Evolution & Parity Flow

All contracts follow the Single Authority Chain established in S27:

```text
Pydantic Canonical Models (`ai/contracts/creative/*.py`)
                  ↓
Deterministic Generator (`scripts/generate_creative_contracts.py`)
                  ↓
JSON Schema (`schemas/creative/*.schema.json`)
                  ↓
TypeScript Types (`contracts/generated/creative_contracts.ts`, `remotion-app/src/types/creative_contracts.ts`)
```

- **Zero Hand-Coded TypeScript Models**: Hand-edited TypeScript interfaces at system boundaries are prohibited.
- **Automated Drift Detection**: CI enforces parity via `python scripts/generate_creative_contracts.py --check`.
- **Vitest Parity Suite**: Validates TypeScript type compilation and schema alignment in `tests/remotion/creative_contracts_parity.test.ts`.
