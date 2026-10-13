# Archive Scripts Inventory & Hygiene Report (REALITY-022)

**Generated:** 2026-10-11  
**Authority:** Architectural Governance & Structural Hardening (PR-C3)  
**Status:** Canonical Reference — All 30 archive source files inventoried, non-destructive retention preserved.

---

## 1. Executive Summary

As identified in finding `REALITY-022` and architectural constraint `REALITY-014`, the `scripts/archive/` directory contains legacy scripts created during historical remediation phases (Phases 13 through 16) and early project migrations.

In accordance with strict safety directives:
1. **Zero Deletions:** No files in `scripts/archive/` have been deleted or modified destructively.
2. **Zero Production Coupling:** Codebase analysis confirms that no active production runtime (API routers, workers, pipeline orchestrator, gates, Remotion engine) imports or executes these scripts in production workflows.
3. **Audit Ledger:** Every archived script is classified with its historical phase, original purpose, current status, and consumers.

---

## 2. Python Archived Scripts (7 Scripts + 1 Package Marker)

| Script Path | Historical Phase / Context | Original Purpose | Current Status | Production Coupling / Consumers | Retention Decision |
|---|---|---|---|---|---|
| `scripts/archive/classify_templates.py` | Phase 0 / Early Registry | One-off template classification utility | INACTIVE | None. Replaced by `registry/semantic-registry.ts` and `scripts/validators/template_lint.py`. | RETAIN (Historical) |
| `scripts/archive/migrate_assets.py` | Phase 12 / Asset Normalization | Historical utility for converting raw paths to canonical asset IDs | INACTIVE | None. Replaced by `scripts/core/storage/` and `materialize_project.py`. | RETAIN (Historical) |
| `scripts/archive/migrate_legacy_projects.py` | Phase 0 / Archaeology | Early flat project scanner and directory migrator | INACTIVE | None. Replaced by `scripts/migration/tenant_project_migration.py`. | RETAIN (Historical) |
| `scripts/archive/migrate_state.py` | Phase 4 / State Machine | Historical state file updater for pre-CAS revisions | INACTIVE | Permitted in command policy whitelist for legacy recovery; not invoked in active pipelines. | RETAIN (Historical) |
| `scripts/archive/smoke_crd019_templates.py` | CRD-019 Remediation | Ad-hoc smoke test verifying template compatibility | INACTIVE | None. Replaced by automated pytest and vitest suites (`tests/remotion/`). | RETAIN (Historical) |
| `scripts/archive/smoke_crd020_temporal.py` | CRD-020 Remediation | Ad-hoc smoke test verifying frame timeline consistency | INACTIVE | None. Replaced by `tests/contracts/` and `tests/remotion/blueprint.test.ts`. | RETAIN (Historical) |
| `scripts/archive/stitch_skill.py` | Early Agent Tooling | Script attempting to stitch skills before plugin system | INACTIVE | None. Superseded by Antigravity Customization System & Superpowers plugin. | RETAIN (Historical) |
| `scripts/archive/__init__.py` | Python Package | Standard package initialization marker | PASSIVE | Enables clean Python package discovery without execution side-effects. | RETAIN (System) |

---

## 3. TypeScript Archived Scripts (23 Scripts across Phases 13–16)

### Phase 13 Cohort (3 Scripts)
| Script Path | Historical Purpose | Current Status | Replacement Authority | Retention |
|---|---|---|---|---|
| `scripts/archive/phase13/baseline.ts` | Initial template baseline extraction and scoring | INACTIVE | `ground-truth/template_catalog.json` | RETAIN |
| `scripts/archive/phase13/coverage.ts` | Phase 13 template coverage measurement script | INACTIVE | Canonical CI test coverage gates | RETAIN |
| `scripts/archive/phase13/prioritize.ts` | Phase 13 template remediation priority ranker | INACTIVE | Architectural remediation roadmap | RETAIN |

### Phase 14 Cohort (4 Scripts)
| Script Path | Historical Purpose | Current Status | Replacement Authority | Retention |
|---|---|---|---|---|
| `scripts/archive/phase14/baseline.ts` | Phase 14 execution bridge baseline measurement | INACTIVE | `remotion-app/src/templates/effects/engine-bridge.tsx` | RETAIN |
| `scripts/archive/phase14/execution_bridge_audit.ts` | Static AST audit of template execution bridges | INACTIVE | `scripts/validators/template_lint.py` | RETAIN |
| `scripts/archive/phase14/patch_candidates.ts` | Automated generation of template patch candidates | INACTIVE | Unified template registry | RETAIN |
| `scripts/archive/phase14/prioritize.ts` | Execution bridge priority ranking matrix | INACTIVE | `ARCHITECTURE_TRUTH.md` | RETAIN |

### Phase 15 Cohort (4 Scripts)
| Script Path | Historical Purpose | Current Status | Replacement Authority | Retention |
|---|---|---|---|---|
| `scripts/archive/phase15/build_execution_cohorts.ts` | Grouped templates into execution cohorts | INACTIVE | Canonical template index | RETAIN |
| `scripts/archive/phase15/generate_sample_batch.ts` | Generated synthetic test batches for templates | INACTIVE | Vitest test fixtures (`tests/remotion/`) | RETAIN |
| `scripts/archive/phase15/validate_execution_contracts.ts` | Standalone contract validation script | INACTIVE | `contracts/render-input.ts` | RETAIN |
| `scripts/archive/phase15/validate_verification_integrity.ts` | Verification pass on generated test outputs | INACTIVE | `scripts/gates/probe_qc.py` | RETAIN |

### Phase 16 Cohort (10 Scripts)
| Script Path | Historical Purpose | Current Status | Replacement Authority | Retention |
|---|---|---|---|---|
| `scripts/archive/phase16/build_16_3_coverage_report.ts` | Generated Phase 16.3 coverage report | INACTIVE | Remotion Vitest test suite | RETAIN |
| `scripts/archive/phase16/build_blocked_inventory.ts` | Inventory of blocked template adapters | INACTIVE | Remediation tracker | RETAIN |
| `scripts/archive/phase16/build_phase_16_3_inventory.ts` | Phase 16.3 template inventory compiler | INACTIVE | `ground-truth/template_catalog.json` | RETAIN |
| `scripts/archive/phase16/build_phase_16_4_analysis.ts` | Phase 16.4 adapter capability analysis | INACTIVE | `contracts/template-schemas.ts` | RETAIN |
| `scripts/archive/phase16/build_phase_16_4_inventory.ts` | Phase 16.4 adapter inventory compiler | INACTIVE | `contracts/template-schemas.ts` | RETAIN |
| `scripts/archive/phase16/extract_proven_defaults.ts` | Extracted default props for template schemas | INACTIVE | `contracts/template-schemas.ts` | RETAIN |
| `scripts/archive/phase16/generate_16_3_runtime_batch.ts` | Batch test runner for runtime templates | INACTIVE | Vitest suite | RETAIN |
| `scripts/archive/phase16/mine_adapter_families.ts` | Mined template families for common adapters | INACTIVE | Canonical template catalog | RETAIN |
| `scripts/archive/phase16/rank_adapter_families.ts` | Ranked adapter complexity | INACTIVE | Core contracts layer | RETAIN |
| `scripts/archive/phase16/test_social_captions_adapter.ts` | One-off caption adapter test | INACTIVE | `tests/remotion/s16_pre_mount_gate.test.ts` | RETAIN |
| `scripts/archive/phase16/validate_phase_16_2.ts` | Validation runner for Phase 16.2 | INACTIVE | Vitest suite | RETAIN |
| `scripts/archive/phase16/validate_phase_16_3.ts` | Validation runner for Phase 16.3 | INACTIVE | Vitest suite | RETAIN |

---

## 4. Governance Policy & Guardrails

1. **Strict Non-Invocation Rule:** AI agents, worker processes, and API routers MUST NOT invoke scripts in `scripts/archive/` during normal operations.
2. **Preservation Invariant:** Files in `scripts/archive/` must remain untouched to ensure historical Git provenance and auditability.
3. **Verification:** Monitored by `tests/architecture/test_archive_hygiene.py` to ensure zero runtime leaks into active production systems.
