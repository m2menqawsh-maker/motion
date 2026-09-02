# Phase 16.2 Implementation Plan

## Goal
Unlock the 37 `defaultFixCandidates` and 3 `genericMappingCandidates` using generic engine improvements and proven defaults, without inventing any values or building specialized template adapters. 

## User Review Required
Please review the plan below. We will use a script to statically analyze the template source files to extract destructured default arguments as "proven defaults" to solve the 37 default candidates. We will also enhance the generic media mapping in `generate_registry.ts` to catch props like `audioSrc` or `src` that were previously unmapped.

## Open Questions
- Is extracting the defaults from the destructured React component props (e.g. `({ size = 24 }) => ...`) acceptable as proven source evidence? (The plan assumes YES, as it fulfills the "TypeScript parameter/default initialization" rule).

## Proposed Changes

### 1. Extractor Script
#### [NEW] [extract_proven_defaults.ts](file:///c:/video/clean-video-workspace/.agents/plugins/super-video-maker-plugin/scripts/phase16/extract_proven_defaults.ts)
- Read the 37 `defaultFixCandidates` from Phase 16.1.
- Parse their source files using Regex/AST to extract explicit default values (e.g., `size = 24`, `color = "red"`).
- Write to `ground-truth/phase_16_2_default_evidence.json`.

### 2. Generic Engine Updates
#### [MODIFY] [generate_registry.ts](file:///c:/video/clean-video-workspace/.agents/plugins/super-video-maker-plugin/scripts/generate_registry.ts)
- **Media Mapping:** Enhance `derivePropIntelligence` to map props named `audioSrc`, `src`, `media`, `poster`, etc., resolving the 3 `genericMappingCandidates`.
- **Capability:** Update `deriveAdapterCapability` to assign `generic_execution_v1` to scalar templates, even if they have unmapped optional props, enabling them to bypass the `NO_SEMANTIC_ROLE` blocker.

#### [MODIFY] [validate_execution_contracts.ts](file:///c:/video/clean-video-workspace/.agents/plugins/super-video-maker-plugin/scripts/phase15/validate_execution_contracts.ts)
- Load `phase_16_2_default_evidence.json`.
- Allow contracts to pass if any unmapped required props have proven defaults in the evidence artifact.

#### [MODIFY] [TemplateAdapter.ts](file:///c:/video/clean-video-workspace/.agents/plugins/super-video-maker-plugin/remotion-app/src/engine/planning/TemplateAdapter.ts)
- Import `phase_16_2_default_evidence.json`.
- In `resolveTemplateProps`, inject the proven defaults from the evidence for any missing props.

### 3. Validation & Reporting
#### [NEW] [validate_phase_16_2.ts](file:///c:/video/clean-video-workspace/.agents/plugins/super-video-maker-plugin/scripts/phase16/validate_phase_16_2.ts)
- Run the required integrity checks (e.g. no invented defaults, singletons untouched, ChaosDesktop untouched).
#### [NEW] [PHASE_16_2_REPORT.md](file:///c:/video/clean-video-workspace/.agents/plugins/super-video-maker-plugin/PHASE_16_2_REPORT.md)
- Generate the final markdown report detailing the unlocked templates, exact coverage changes, and runtime sample results.

## Verification Plan
### Automated Tests
- Run `npx tsx scripts/generate_registry.ts`
- Run `npx tsx scripts/phase15/validate_execution_contracts.ts`
- Run `npx tsx scripts/phase16/validate_phase_16_2.ts`

### Manual Verification
- Perform a targeted runtime render (`npx remotion render`) of 2-3 unlocked scalar templates and 1 unlocked media template to prove the generic compiler path works.
