# Architectural Reality Context Pack — Consolidated Master Edition (v2.0)

> **Baseline Git Commit SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`  
> **Branch**: `main`  
> **Evidence Standard**: `CODE_PROVEN` | `TEST_PROVEN` | `CI_PROVEN` | `RUNTIME_REACHABILITY_PROVEN` | `DOCUMENTATION_ONLY` | `INFERRED` | `UNKNOWN`  
> **Total Synthesized Documentation**: ~470 KB across 5 cohesive Master Pillars + 3 Machine-Readable JSON datasets.  
> **Original Reports Repository**: Preserved verbatim in `../` (21 domain reports, 00 through 20).

---

## 🏛️ The 5 Master Architectural Pillars

| # | Master Pillar File | Sub-Reports Consolidated | Core Scope & Mission |
|---|--------------------|--------------------------|----------------------|
| **1** | [`01_SYSTEM_TOPOLOGY_AND_ENTRYPOINTS.md`](./01_SYSTEM_TOPOLOGY_AND_ENTRYPOINTS.md) | Reports `00`, `01`, `02` | **Topology & Entrypoints**: Executive baseline freeze, comprehensive directory classification inventory, and live call graphs from HTTP/Worker/CLI entrypoints to storage. |
| **2** | [`02_RUNTIME_REACHABILITY_AND_AUTHORITY.md`](./02_RUNTIME_REACHABILITY_AND_AUTHORITY.md) | Reports `03`, `04`, `05`, `13` | **Reachability & Authority**: Detailed runtime matrix across 53 subsystems, bootstrap dependency injection wiring (test vs prod), source-of-truth authority boundaries, and artifact persistence lineage. |
| **3** | [`03_AI_AND_CREATIVE_PIPELINE_REALITY.md`](./03_AI_AND_CREATIVE_PIPELINE_REALITY.md) | Reports `06`, `07`, `08`, `09` | **AI & Creative Pipeline**: The gap between documented and actual AI execution flows (ContextBuilder zero callers), strict separation of Ground Truth vs Registries, Remotion vs Canvas authoring reality, and Capability/Tool routing. |
| **4** | [`04_VERIFICATION_CI_AND_GOVERNANCE.md`](./04_VERIFICATION_CI_AND_GOVERNANCE.md) | Reports `10`, `11`, `12`, `17` | **Verification & CI Governance**: Audit of mock boundaries in E2E tests, proof of CI exclusion for `tests/ai` (270 files), repository-wide silent failure/fallback scan, and multi-tenant security isolation. |
| **5** | [`05_FINDINGS_LEDGER_DRIFT_AND_UNKNOWNS.md`](./05_FINDINGS_LEDGER_DRIFT_AND_UNKNOWNS.md) | Reports `14`, `15`, `16`, `18`, `19`, `20` | **Drift, Findings & Unknowns**: Cross-generational architectural drift (Pre-S25 to S28-R), legacy deletion safety audit, true product journey breakage analysis, Unified Findings Ledger (`REALITY-001` through `REALITY-024+`), and the Catalog of Unknowns (`UNK-001` to `UNK-010`). |

---

## 🤖 Machine-Readable Datasets (Included & Validated)

1. [`component_reality_matrix.json`](./component_reality_matrix.json): Detailed JSON database covering all 53 repository subsystems with exact filepaths, callers, callees, and production reachability statuses.
2. [`findings.json`](./findings.json): Structured programmatic catalog of all verified findings with exact severity counts, affected files, and recommended remediation paths.
3. [`context_manifest.json`](./context_manifest.json): Machine-readable execution manifest linking the pack to baseline SHA `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`.

---

## 🔒 Non-Destructive Invariant
- The original 21 reports remain untouched in `documentation/reality_context_pack/`.
- No production code, tests, or CI files have been modified.
