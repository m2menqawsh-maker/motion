# S28 — Legacy Creative Inventory & Migration Map

> [!IMPORTANT]
> **Exit Gate Criteria (S28-01):**
> Exactly 0 unclassified critical creative artifacts.
> No legacy paths moved or deleted prematurely.
> Deletion permitted only after: replacement exists + behavior/parity verified + no required live consumer.

## 1. Executive Summary

- **Total Audited Artifacts:** 102
- **Unclassified Artifacts:** 0
- **Audit Scope:** `references/`, `recipes/`, `.agents/`, `scripts/gates/`, `scripts/maintenance/`, `templates/custom/`, `ground-truth/`

### Classification Breakdown

- **`DEPRECATE`:** 6 artifacts
- **`KEEP`:** 36 artifacts
- **`MIGRATE`:** 23 artifacts
- **`WRAP`:** 37 artifacts

---

## 2. Master Creative Artifact Inventory

| Legacy ID | Source Path | Current Purpose | Consumer | Current Authority | Target Subsystem | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ref-taste-choreography` | `references/4_taste_engine/choreography.md` | Multi-element choreography, 3D camera staging, and layer parallax rules | Agent, Remotion Developers | Reference Level 5 | `S28-04 Taste Engine` | **`MIGRATE`** |
| `ref-taste-context` | `references/4_taste_engine/context-adaptation.md` | Context-based adaptation rules (mood-to-personality mapping) | Agent, Template Router | Reference Level 5 | `S28-04 Taste Engine` | **`MIGRATE`** |
| `ref-taste-philosophy` | `references/4_taste_engine/core-philosophy.md` | Three pillars (Emotional Intent, Visual Narrative, Motion Craft) and Attention Budget | Agent, Developers | Reference Level 5 | `S28-04 Taste Engine` | **`MIGRATE`** |
| `ref-taste-decision` | `references/4_taste_engine/decision-framework.md` | Creative decision framework and style selection matrix | Agent, Pipeline Planner | Reference Level 5 | `S28-04 Taste Engine` | **`MIGRATE`** |
| `ref-taste-disney` | `references/4_taste_engine/disney-principles.md` | 12 Disney animation principles adapted to Remotion declarative motion | Agent, Component Authors | Reference Level 5 | `S28-02 Knowledge Platform` | **`MIGRATE`** |
| `ref-taste-emotion` | `references/4_taste_engine/emotion-mapping.md` | Emotional intent to spring physics, timing, and color mappings | Agent, Scene Planner | Reference Level 5 | `S28-04 Taste Engine` | **`MIGRATE`** |
| `ref-taste-personality` | `references/4_taste_engine/motion-personality.md` | Official motion personalities (Cinematic, Energetic, Playful, Technical) with timing/easing numbers | scripts/gates/motion_validator.py, Agent | Reference Level 5 | `S28-04 Taste Engine` | **`MIGRATE`** |
| `ref-taste-narrative` | `references/4_taste_engine/narrative-structure.md` | Narrative arcs (Three-Act, Hook-Proof-CTA, Problem-Agitation-Solution) | Agent, Narrative Planner | Reference Level 5 | `S28-04 Narrative Planning` | **`MIGRATE`** |
| `ref-taste-sfx` | `references/4_taste_engine/sfx_binding_matrix.md` | SFX gesture binding matrix, audio ducking, and frequency rules | Agent, Blueprint Validator | Reference Level 5 | `S28-04 Taste Engine` | **`MIGRATE`** |
| `ref-taste-signature` | `references/4_taste_engine/user-signature-style.md` | Director's Signature v2: Scene=Sentence, Shot=Beat, double variance, emphasis grammar | scripts/gates/taste_gate.py, Agent | Reference Level 5 | `S28-04 Taste Engine` | **`MIGRATE`** |
| `ref-playbook-ffmpeg` | `references/1_playbooks/ffmpeg_recipes.md` | FFmpeg command line recipes for normalization, all-intra transcoding, and concatenation | Developers, Processing MCPs | Reference Level 5 | `S28-02 Knowledge Platform` | **`KEEP`** |
| `ref-playbook-hook-sprint` | `references/1_playbooks/hook_playbook_article_sprint.md` | Production playbook for 30s fast article sprint reels | Agent | Reference Level 5 | `S28-02 Knowledge Platform` | **`MIGRATE`** |
| `ref-playbook-living-canvas` | `references/1_playbooks/living_canvas.md` | Playbook for seamless, continuous living canvas explainer videos | Agent | Reference Level 5 | `S28-02 Knowledge Platform` | **`MIGRATE`** |
| `ref-playbook-motion-collage` | `references/1_playbooks/motion_collage.md` | Playbook for living collage cutout animation videos | Agent | Reference Level 5 | `S28-02 Knowledge Platform` | **`MIGRATE`** |
| `ref-playbook-review` | `references/1_playbooks/review_video.md` | Playbook for competitor review conquest compilation videos | Agent | Reference Level 5 | `S28-02 Knowledge Platform` | **`MIGRATE`** |
| `ref-playbook-tabletop` | `references/1_playbooks/tabletop_explainer.md` | Playbook for tiered concept layered tabletop explainer reels | Agent | Reference Level 5 | `S28-02 Knowledge Platform` | **`MIGRATE`** |
| `ref-playbook-video-copy` | `references/1_playbooks/video_copy.md` | Copywriting guidelines, word count bounds, and voiceover pacing rules | Agent, Script Writer | Reference Level 5 | `S28-02 Knowledge Platform` | **`MIGRATE`** |
| `ref-sop-hyperrealistic` | `references/2_sops/hyperrealistic_image.md` | Standard operating procedure for realistic character and background prompts | Agent, Image Capability | Reference Level 5 | `S28-02 Knowledge Platform` | **`MIGRATE`** |
| `ref-sop-plan-template` | `references/2_sops/plan_template.md` | Structural markdown specification for human/agent detailed video plans | Agent, scripts/gates/plan_gate.py | Reference Level 5 | `S28-05 Creative Planning` | **`MIGRATE`** |
| `ref-sop-seedance-avatar` | `references/2_sops/seedance_avatar.md` | SOP for avatar video generation, lip sync, and green-screen extraction | Agent, Avatar Capability | Reference Level 5 | `S28-02 Knowledge Platform` | **`MIGRATE`** |
| `ref-sop-spoken-vo` | `references/2_sops/spoken_vo_humanizer.md` | SOP for adapting written text into natural spoken cadence for TTS | Agent, TTS Capability | Reference Level 5 | `S28-02 Knowledge Platform` | **`MIGRATE`** |
| `ref-sop-template-proposal` | `references/2_sops/template_proposal.md` | SOP for proposing new custom templates from projects/ into catalog | Agent, scripts/validators/template_proposal_validator.py | Reference Level 5 | `S28-07 Template Promotion` | **`WRAP`** |
| `ref-eng-remotion` | `references/3_engineering/remotion_guide.md` | Remotion engineering rules, composition lifecycle, and spring math | Developers, Agent | Reference Level 5 | `S28-02 Knowledge Platform` | **`KEEP`** |
| `ref-router` | `references/ROUTER.md` | Monolithic decision router: recipe matching, tool dispatch, personality selection | Agent | Reference Level 5 | `S28-03 Recipe Engine / S28-04 Taste Engine` | **`WRAP`** |
| `ref-readme` | `references/README.md` | Documentation index for references folder | Developers | Reference Level 5 | `S28-02 Knowledge Platform` | **`KEEP`** |
| `recipe-agent-browser-proof` | `recipes/agent-browser-proof.json` | Production recipe specification for agent-browser-proof: stages, keywords, platforms, and required deliverables | references/ROUTER.md, Agent, tools/video_recipes.py (quarantined) | Unversioned JSON File | `S28-03 Recipe Engine` | **`WRAP`** |
| `recipe-avatar-explainer` | `recipes/avatar-explainer.json` | Production recipe specification for avatar-explainer: stages, keywords, platforms, and required deliverables | references/ROUTER.md, Agent, tools/video_recipes.py (quarantined) | Unversioned JSON File | `S28-03 Recipe Engine` | **`WRAP`** |
| `recipe-avatar-hook-broll` | `recipes/avatar-hook-broll.json` | Production recipe specification for avatar-hook-broll: stages, keywords, platforms, and required deliverables | references/ROUTER.md, Agent, tools/video_recipes.py (quarantined) | Unversioned JSON File | `S28-03 Recipe Engine` | **`WRAP`** |
| `recipe-avatar-insta-split` | `recipes/avatar-insta-split.json` | Production recipe specification for avatar-insta-split: stages, keywords, platforms, and required deliverables | references/ROUTER.md, Agent, tools/video_recipes.py (quarantined) | Unversioned JSON File | `S28-03 Recipe Engine` | **`WRAP`** |
| `recipe-avatar-product-walkthrough` | `recipes/avatar-product-walkthrough.json` | Production recipe specification for avatar-product-walkthrough: stages, keywords, platforms, and required deliverables | references/ROUTER.md, Agent, tools/video_recipes.py (quarantined) | Unversioned JSON File | `S28-03 Recipe Engine` | **`WRAP`** |
| `recipe-avatar-vo-broll` | `recipes/avatar-vo-broll.json` | Production recipe specification for avatar-vo-broll: stages, keywords, platforms, and required deliverables | references/ROUTER.md, Agent, tools/video_recipes.py (quarantined) | Unversioned JSON File | `S28-03 Recipe Engine` | **`WRAP`** |
| `recipe-captioned-talking-head` | `recipes/captioned-talking-head.json` | Production recipe specification for captioned-talking-head: stages, keywords, platforms, and required deliverables | references/ROUTER.md, Agent, tools/video_recipes.py (quarantined) | Unversioned JSON File | `S28-03 Recipe Engine` | **`WRAP`** |
| `recipe-dynamic-montage-ad` | `recipes/dynamic-montage-ad.json` | Production recipe specification for dynamic-montage-ad: stages, keywords, platforms, and required deliverables | references/ROUTER.md, Agent, tools/video_recipes.py (quarantined) | Unversioned JSON File | `S28-03 Recipe Engine` | **`WRAP`** |
| `recipe-faceless-broll-ad` | `recipes/faceless-broll-ad.json` | Production recipe specification for faceless-broll-ad: stages, keywords, platforms, and required deliverables | references/ROUTER.md, Agent, tools/video_recipes.py (quarantined) | Unversioned JSON File | `S28-03 Recipe Engine` | **`WRAP`** |
| `recipe-living-canvas-explainer` | `recipes/living-canvas-explainer.json` | Production recipe specification for living-canvas-explainer: stages, keywords, platforms, and required deliverables | references/ROUTER.md, Agent, tools/video_recipes.py (quarantined) | Unversioned JSON File | `S28-03 Recipe Engine` | **`WRAP`** |
| `recipe-longform-repurpose` | `recipes/longform-repurpose.json` | Production recipe specification for longform-repurpose: stages, keywords, platforms, and required deliverables | references/ROUTER.md, Agent, tools/video_recipes.py (quarantined) | Unversioned JSON File | `S28-03 Recipe Engine` | **`WRAP`** |
| `recipe-misotts-article-sprint` | `recipes/misotts-article-sprint.json` | Production recipe specification for misotts-article-sprint: stages, keywords, platforms, and required deliverables | references/ROUTER.md, Agent, tools/video_recipes.py (quarantined) | Unversioned JSON File | `S28-03 Recipe Engine` | **`WRAP`** |
| `recipe-motion-collage-explainer` | `recipes/motion-collage-explainer.json` | Production recipe specification for motion-collage-explainer: stages, keywords, platforms, and required deliverables | references/ROUTER.md, Agent, tools/video_recipes.py (quarantined) | Unversioned JSON File | `S28-03 Recipe Engine` | **`WRAP`** |
| `recipe-motion-graphics` | `recipes/motion-graphics.json` | Production recipe specification for motion-graphics: stages, keywords, platforms, and required deliverables | references/ROUTER.md, Agent, tools/video_recipes.py (quarantined) | Unversioned JSON File | `S28-03 Recipe Engine` | **`WRAP`** |
| `recipe-review-conquest-compilation` | `recipes/review-conquest-compilation.json` | Production recipe specification for review-conquest-compilation: stages, keywords, platforms, and required deliverables | references/ROUTER.md, Agent, tools/video_recipes.py (quarantined) | Unversioned JSON File | `S28-03 Recipe Engine` | **`WRAP`** |
| `recipe-screencast-demo` | `recipes/screencast-demo.json` | Production recipe specification for screencast-demo: stages, keywords, platforms, and required deliverables | references/ROUTER.md, Agent, tools/video_recipes.py (quarantined) | Unversioned JSON File | `S28-03 Recipe Engine` | **`WRAP`** |
| `recipe-tabletop-levels-explainer` | `recipes/tabletop-levels-explainer.json` | Production recipe specification for tabletop-levels-explainer: stages, keywords, platforms, and required deliverables | references/ROUTER.md, Agent, tools/video_recipes.py (quarantined) | Unversioned JSON File | `S28-03 Recipe Engine` | **`WRAP`** |
| `recipe-ugc-ai-ad` | `recipes/ugc-ai-ad.json` | Production recipe specification for ugc-ai-ad: stages, keywords, platforms, and required deliverables | references/ROUTER.md, Agent, tools/video_recipes.py (quarantined) | Unversioned JSON File | `S28-03 Recipe Engine` | **`WRAP`** |
| `recipe-schema` | `recipes/schema.json` | Draft-07 JSON Schema for legacy recipes/*.json files | tools/video_recipes.py | Unversioned Schema | `S28-03 Recipe Engine` | **`DEPRECATE`** |
| `recipe-readme` | `recipes/README.md` | Documentation guide for recipe CLI commands and recipe authoring | Developers | Documentation | `S28-03 Recipe Engine` | **`KEEP`** |
| `agent-directives` | `.agents/AGENTS.md` | Master agent directives, source of truth hierarchy, and pipeline operating rules | AI Agents | Instruction Authority Level 4 | `S28-01 Foundation & Governance` | **`WRAP`** |
| `agent-protocol` | `.agents/rules/video-production-protocol.md` | Operational rules for phased pipeline execution (Phases 0 through 8) | AI Agents | Instruction Authority Level 4 | `S28-01 Foundation & Governance` | **`WRAP`** |
| `agent-skill-prompt-expert` | `.agents/skills/prompt-engineering-expert/SKILL.md` | Prompt engineering guidelines and best practices for Claude agent | Claude Agent | Skill Specification | `S28-02 Skills Platform` | **`KEEP`** |
| `agent-skill-remocn` | `.agents/plugins/super-video-maker-plugin/skills/remocn/SKILL.md` | Remocn vendor skill for React Remotion component authoring and archetypes | Claude Agent, skills-lock.json | Vendor GitHub Lock | `S28-02 Skills Platform` | **`KEEP`** |
| `agent-skill-snapcn` | `.agents/plugins/super-video-maker-plugin/skills/snapcn/SKILL.md` | Snapcn vendor skill for Tailwind/motion UI component authoring and archetypes | Claude Agent, skills-lock.json | Vendor GitHub Lock | `S28-02 Skills Platform` | **`KEEP`** |
| `agent-skills-index` | `.agents/plugins/super-video-maker-plugin/skills/INDEX.md` | Notice declaring vendor skills live under plugin directory | Developers | Documentation | `S28-02 Skills Platform` | **`KEEP`** |
| `agent-cmd-avatar-insta` | `.agents/plugins/super-video-maker-plugin/commands/avatar-insta-reel.md` | Slash command prompt for Instagram split-screen reel production | AI Agent | Slash Command | `S28-03 Recipe Engine` | **`MIGRATE`** |
| `agent-plugin-json` | `.agents/plugins/super-video-maker-plugin/plugin.json` | Plugin manifest defining tools, skills, and configuration | Antigravity CLI / Agent Runner | Plugin Manifest | `S28-01 Foundation` | **`KEEP`** |
| `agent-mcp-config` | `.agents/plugins/super-video-maker-plugin/mcp_config.json` | Configuration for local MCP servers registered in plugin | MCP Runner | MCP Config | `S27 / Core` | **`KEEP`** |
| `agent-guard-behavior` | `.agents/guardian/behavior_guard.py` | Guardian hook evaluating general agent actions | hooks.json | Security Guard | `Security Core` | **`KEEP`** |
| `agent-guard-command` | `.agents/guardian/command_guard.py` | Guardian hook validating shell commands against security policy | hooks.json | Security Guard | `Security Core` | **`KEEP`** |
| `agent-guard-write` | `.agents/guardian/write_guard.py` | Guardian hook preventing direct writes to protected files | hooks.json | Security Guard | `Security Core` | **`KEEP`** |
| `agent-guard-post` | `.agents/guardian/post_executor.py` | Guardian post-execution validation hook | hooks.json | Security Guard | `Security Core` | **`KEEP`** |
| `agent-guard-circuit` | `.agents/guardian/circuit_breaker.json` | Circuit breaker state for agent failures | Guardian Hooks | Security Guard | `Security Core` | **`KEEP`** |
| `agent-guard-utils` | `.agents/guardian/utils.py` | Helper utilities for Guardian security hooks | Guardian Hooks | Security Guard | `Security Core` | **`KEEP`** |
| `agent-guard-log` | `.agents/logs/guardrails.log` | Audit log of guardian hook executions and blocks | Audit System | Security Audit | `Security Core` | **`KEEP`** |
| `agent-qc-salt` | `.agents/secrets/.qc_salt` | HMAC secret salt for authenticating QC signatures | SmartQC / ReviewService | Cryptographic Secret | `Core Security` | **`KEEP`** |
| `agent-docker-remotion` | `.agents/docker/Dockerfile.remotion` | Docker container definition for hermetic Remotion rendering | CI / Docker Runner | DevOps Contract | `Core Render` | **`KEEP`** |
| `tool-ad-quality-gate` | `.agents/plugins/super-video-maker-plugin/tools/ad_quality_gate.py` | Quality checks for paid-social ads (aspect ratio, duration, hooks) | Agent, QC Runner | Local Script | `scripts/gates/` | **`WRAP`** |
| `tool-broll-layout-qc` | `.agents/plugins/super-video-maker-plugin/tools/broll_layout_qc.py` | B-roll layout and safe-zone verification tool | Agent, QC Runner | Local Script | `scripts/gates/` | **`WRAP`** |
| `tool-ffmpeg-qc` | `.agents/plugins/super-video-maker-plugin/tools/ffmpeg_qc.py` | FFmpeg-based technical validation (GOP, codec, audio levels) | Agent, QC Runner | Local Script | `scripts/gates/` | **`WRAP`** |
| `tool-media-pipeline` | `.agents/plugins/super-video-maker-plugin/tools/media_pipeline.py` | Legacy asset life-cycle coordinator and download orchestrator | Agent | Local Script | `api/services/asset_service.py` | **`WRAP`** |
| `tool-screen-recorder` | `.agents/plugins/super-video-maker-plugin/tools/screen_recorder.py` | Screen recording capture utility for demo videos | Agent | Local Script | `ai/specialized` | **`WRAP`** |
| `tool-agent-browser` | `.agents/plugins/super-video-maker-plugin/tools/agent_browser_recorder.py` | Browser automation recording for software demo videos | Agent | Local Script | `ai/specialized` | **`WRAP`** |
| `tool-video-captioner` | `.agents/plugins/super-video-maker-plugin/tools/video_captioner.py` | Whisper/SRT subtitle generator and timing extractor | Agent | Local Script | `ai/speech` | **`WRAP`** |
| `tool-elevenlabs` | `.agents/plugins/super-video-maker-plugin/tools/elevenlabs_voice.py` | Direct ElevenLabs API client for TTS audio generation | Agent | Local Script | `ai/providers/elevenlabs` | **`DEPRECATE`** |
| `tool-heygen` | `.agents/plugins/super-video-maker-plugin/tools/heygen_client.py` | Direct HeyGen API client for avatar video synthesis | Agent | Local Script | `ai/providers/heygen` | **`DEPRECATE`** |
| `tool-fal-seedance` | `.agents/plugins/super-video-maker-plugin/tools/fal_seedance_video.py` | Direct Fal AI / Seedance API client for avatar video | Agent | Local Script | `ai/providers/fal` | **`DEPRECATE`** |
| `tool-replicate` | `.agents/plugins/super-video-maker-plugin/tools/replicate_video.py` | Direct Replicate API client for fallback video generation | Agent | Local Script | `ai/providers/replicate` | **`DEPRECATE`** |
| `tool-image-provider` | `.agents/plugins/super-video-maker-plugin/tools/image_provider.py` | Direct OpenAI/Replicate image generation wrapper | Agent | Local Script | `ai/capabilities/image_generation` | **`DEPRECATE`** |
| `tool-music-provider` | `.agents/plugins/super-video-maker-plugin/tools/music_provider.py` | Direct audio/music search and fetch utility | Agent | Local Script | `ai/capabilities/audio` | **`WRAP`** |
| `tool-plugin-verify` | `.agents/plugins/super-video-maker-plugin/verify.py` | Self-verification test script for plugin tools and configs | Developers | Test Script | `scripts/ci` | **`KEEP`** |
| `script-taste-gate` | `scripts/gates/taste_gate.py` | Active gate verifying scene plans against user signature style rules | scripts/pipeline.py, Stage Gate | Pipeline Gate Authority | `S28-04 Taste Engine` | **`WRAP`** |
| `script-motion-validator` | `scripts/gates/motion_validator.py` | Validates motion parameters against motion-personality.md | Pipeline, Developers | Gate Validator | `S28-04 Taste Engine` | **`WRAP`** |
| `script-plan-gate` | `scripts/gates/plan_gate.py` | Validates master_plan.md structure and contains legacy OpenAI judge call | scripts/pipeline.py | Pipeline Gate Authority | `S28-05 Creative Planning` | **`WRAP`** |
| `script-generate-plan` | `scripts/generators/generate_plan.py` | Generates plan_skeleton.md for project initialization | Agent, Developers | Generator | `S28-05 Creative Planning` | **`WRAP`** |
| `script-template-router` | `scripts/maintenance/template_router.py` | CLI heuristic matcher searching template_catalog.json | references/ROUTER.md, Agent | Maintenance Script | `S28-05 Creative Planning / Blueprint Compiler` | **`WRAP`** |
| `script-promote-template` | `scripts/maintenance/promote_template.py` | Direct promoter copying proposed templates to templates/ and editing TEMPLATE_INDEX.md | references/2_sops/template_proposal.md | Uncontrolled Script | `S28-07 Template Promotion` | **`WRAP`** |
| `script-template-proposal-val` | `scripts/validators/template_proposal_validator.py` | Validates template candidate directory and proposal.json | references/2_sops/template_proposal.md | Validator Script | `S28-07 Template Candidate Validation` | **`WRAP`** |
| `script-sync-templates` | `scripts/maintenance/sync_templates.py` | Synchronizes templates and extracts metadata | Maintenance | Maintenance Script | `registry` | **`KEEP`** |
| `script-probe-planner` | `scripts/core/probe_planner.py` | Planning probe utility for checking plan validity | Probe System | Core Script | `scripts/core` | **`KEEP`** |
| `script-template-lint` | `scripts/validators/template_lint.py` | Lints React Remotion template syntax and props | Pipeline, Developers | Code Linter | `registry` | **`KEEP`** |
| `script-validate-template` | `scripts/validators/validate_template.py` | Validates template component constraints | Pipeline | Validator | `registry` | **`KEEP`** |
| `script-inspect-template` | `scripts/validators/inspect_template.py` | Inspects template properties from runtime registry | Agent, Developers | Inspector Tool | `registry` | **`KEEP`** |
| `script-template-contract` | `scripts/core/template_contract.py` | Core models for template registry contract | scripts/generators/generate_template_contract.py | Contract Model | `registry` | **`KEEP`** |
| `script-gen-template-contract` | `scripts/generators/generate_template_contract.py` | Generates template-runtime-contract.json from runtime registry | Build System | Generator | `registry` | **`KEEP`** |
| `script-gen-template-aliases` | `scripts/generators/generate_template_aliases.py` | Generates template-aliases.ts from single data authority | Build System | Generator | `registry` | **`KEEP`** |
| `tmpl-custom-level-one` | `templates/custom/LevelOneScene.tsx` | Staged custom composite scene template created in Level 1 workflow | Experimental Projects | Unregistered Code | `S28-07 Template Candidate` | **`MIGRATE`** |
| `tmpl-custom-level-zero` | `templates/custom/LevelZeroBox.tsx` | Staged raw primitive box template created in Level 0 workflow | Experimental Projects | Unregistered Code | `S28-07 Template Candidate` | **`MIGRATE`** |
| `gt-template-catalog` | `ground-truth/template_catalog.json` | Compiled catalog of registered templates with metadata, keywords, and quality ratings | scripts/maintenance/template_router.py, Agent | Derived Ground Truth | `registry` | **`KEEP`** |
| `gt-template-index` | `ground-truth/TEMPLATE_INDEX.md` | Human-readable index of all available Remotion templates | Agent, Developers | Ground Truth Doc | `ground-truth` | **`KEEP`** |
| `gt-recipes-index` | `ground-truth/RECIPES_INDEX.md` | Index of all 18 production recipes | Agent, references/ROUTER.md | Derived Ground Truth | `ground-truth` | **`KEEP`** |
| `gt-playbooks-index` | `ground-truth/PLAYBOOKS_INDEX.md` | Index of all production playbooks | Agent | Derived Ground Truth | `ground-truth` | **`KEEP`** |
| `gt-cinematic-index` | `ground-truth/CINEMATIC_INDEX.md` | Index of cinematic engine primitives and properties | Agent | Derived Ground Truth | `ground-truth` | **`KEEP`** |
| `gt-vocab-remap` | `ground-truth/VOCAB_REMAP.md` | Remapping table preventing hallucinated component names | Agent, Template Linter | Ground Truth Policy | `ground-truth` | **`KEEP`** |
| `skills-lock` | `skills-lock.json` | Lock file tracking vendor skill git hashes (remocn, snapcn) | Agent Runner | Security Lock | `S28-02 Skills Platform` | **`KEEP`** |
| `hooks-config` | `hooks.json` | Tool use hooks configuration routing to Guardian security scripts | Antigravity CLI / Runner | Security Configuration | `Security Core` | **`KEEP`** |

---

## 3. Detailed Subsystem Analysis & Governance Notes

### 3.1 Taste Engine & Style References (`references/4_taste_engine/`)
- All 10 taste reference documents define creative principles, spring mathematics, emotional mappings, and gestures.
- In S28-01, they are preserved in `references/` without file movement.
- In S28-04, their rules will be mapped to canonical `TasteRule` contracts evaluated by a deterministic `TasteValidator`.

### 3.2 Production Recipes (`recipes/*.json`)
- 18 production recipes define workflow stages and routing keywords.
- Current recipes contain provider lock-in (e.g. `"avatar": "heygen"`, `"voice": "elevenlabs"`).
- In S28-03, `RecipeDefinition` decouples workflows from specific cloud providers and expresses requirements via `CapabilityType`.

### 3.3 Agent Tools & Vendor Skills (`.agents/`)
- Vendor skills (`remocn`, `snapcn`) are locked via `skills-lock.json` and remain active.
- Direct provider scripts (`elevenlabs_voice.py`, `heygen_client.py`, `fal_seedance_video.py`) are classified as `DEPRECATE` because S27 provider-neutral capability adapters supersede them.
- Guardian hooks (`.agents/guardian/`) remain `KEEP` as an active security baseline.

### 3.4 Template Promotion Flow (`scripts/maintenance/promote_template.py`)
- Current `promote_template.py` allows uncontrolled copying from `proposed/` to `templates/` and directly rewrites `TEMPLATE_INDEX.md`.
- This violates registry authority.
- In S28-07, promotion is strictly governed: `TemplateCandidate` -> `CandidateValidationReport` -> `PromotionDecision` (authorized by human/domain authority, never raw AI).

