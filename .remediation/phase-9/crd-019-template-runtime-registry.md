# CRD-019: Runtime Template Registry / Ground-Truth Drift Remediation

## 1. Executive Summary

- **Defect ID**: CRD-019
- **Category**: Template Registry / Ground-Truth Drift
- **Root Cause**: Upstream catalog generation (`scripts/build_ground_truth.py`) formatted PascalCase component stems using Python's `.title()` method (e.g. `HeroDeviceAssembleWrapper` -> `Herodeviceassemblewrapper`). The upstream pipeline validators (`scripts/validate_blueprint.py`, `scripts/motion_validator.py`) validated against this ground-truth title-case name. However, the runtime registry (`registry/template-registry.tsx`) registered templates under kebab-case IDs (e.g. `rui-hero-device-assemble`) and only contained 13 manual aliases. During the Phase 9.13 Clean-Room render, Remotion threw: `Template not found in registry: Herodeviceassemblewrapper`.
- **Status**: **RESOLVED**
- **Invariant Established**: `ACTIVE + VALIDATOR-ACCEPTED ⊆ RUNTIME-RESOLVABLE` with 0 missing registrations, 0 missing implementations, and 0 drift.

---

## 2. Architecture & Implementation

### A. Deterministic Derivation (No Manual Duplication)
Rather than manually maintaining 105 or 210 static entries, `scripts/generate_template_aliases.py` was created to deterministically derive all aliases from authoritative metadata:
```text
template_catalog ground-truth name (Title-case)
+ component stem (PascalCase)
+ canonical runtime id (kebab-case)
→ deterministic alias mapping (registry/template-aliases.ts)
```
- Total active production templates: **105** (Scenes: 22, Elements: 65, Effects: 18)
- Derived alias entries: **210** (2 per template: ground-truth title-case name and component PascalCase stem)
- Supports `--check` flag to verify synchronization during CI and automated testing.

### B. Transparent Runtime Proxy (`TEMPLATE_REGISTRY`)
In `registry/template-registry.tsx`, `TEMPLATE_REGISTRY` wraps the canonical dictionary in a JavaScript `Proxy`:
1. `get` trap: Resolves canonical IDs directly, intercepts alias lookups via `TEMPLATE_ALIASES`, and fails closed (`undefined`) on unknown names.
2. `has` trap: Accurately reflects alias membership (`template in TEMPLATE_REGISTRY`).
3. `Object.values(TEMPLATE_REGISTRY)`: Preserves clean iteration over exactly the 105 canonical entries without polluting enumerable keys, ensuring UI galleries (`Showcase.tsx`, `TemplateGallery.tsx`) and conformance tests (`tests/registry.test.ts`) encounter zero duplicates.
4. Exported `getRegistryEntry(templateName)` helper provides the canonical functional resolution point.

### C. Zero Unnecessary Changes to Root.tsx
Because `Root.tsx` passes `(template) => TEMPLATE_REGISTRY[template]` into `mergeProject`, the transparent Proxy seamlessly resolves ground-truth names without modifying `Root.tsx`.

### D. Production Component Integrity (Zero Test Accommodations)
The production wrapper `SplitScreenWrapper.tsx` was verified against its upstream contract (`@/remotion/scenes/split-screen`) and kept completely unmodified. The smoke test fixture was configured with legitimate runtime inputs conforming to `SplitScreenProps` (`left` and `right` panels with valid image sources and labels) rather than modifying production sources for tests.

---

## 3. Authoritative Verification

### A. Targeted Remotion Stills (5 Clean-Room Templates)
Executed `scripts/smoke_crd019_templates.py` via Remotion `still`:
1. `Herodeviceassemblewrapper` (Frame 10): **PASS** (945,393 bytes)
2. `Splitscreenwrapper` (Frame 40): **PASS** (280,905 bytes)
3. `Landingcodeshowcasewrapper` (Frame 70): **PASS** (943,214 bytes)
4. `Datastorywrapper` (Frame 100): **PASS** (854,433 bytes)
5. `Creatorreelwrapper` (Frame 130): **PASS** (852,960 bytes)
- **Result**: 5/5 rendered successfully with 0 resolution failures, 0 component load failures, and 0 render smoke failures.

### B. TypeScript Runtime Resolution Test (Vitest)
Executed `vitest run tests/template_runtime_resolution.test.ts`:
- Resolves all 5 Clean-Room templates by GT name, stem, and canonical ID.
- Dynamically validates resolution for all 105 active templates.
- Asserts strict failure-closed behavior for `UnknownFakeTemplate123`.
- Asserts `mergeProject` throws on unknown templates and succeeds on target templates.
- **Result**: 19/19 tests **PASSED**.

### C. Python Permanent Consistency Test (Pytest)
Executed `pytest tests/test_template_registry_consistency.py`:
- Asserts exactly 105 active production templates in ground truth.
- Asserts physical file existence for all 105 components on disk.
- Asserts validator acceptance (`validate_blueprint.py` rules).
- Asserts all 5 Clean-Room failure templates belong to active set.
- Asserts `template-aliases.ts` is in exact sync with ground truth via generator `--check`.
- **Result**: 5/5 tests **PASSED**.

### D. Drift Matrix Output
Generated `.remediation/phase-9/template-runtime-drift.json`:
- Total active production templates: **105**
- Consistent count: **105**
- Missing runtime registrations: **0**
- Missing implementations: **0**
- Validator drift: **0**
- Unknown classifications: **0**

### E. Full Regression Test Suites
1. **Full Python Suite**: `python -m pytest tests`
   - **148 passed**, 1 skipped, 0 failed (90.84s).
2. **Full TypeScript Suite**: `npm test` (`contracts.test.ts`, `merge.test.ts`, `template_runtime_resolution.test.ts`)
   - **39 passed**, 0 failed (4.91s).

---

## 4. Final Metrics Table

| Metric | Target | Actual | Status |
| :--- | :---: | :---: | :---: |
| Active production templates | 105 | 105 | PASS |
| Runtime-resolvable by canonical ID | 105 | 105 | PASS |
| Runtime-resolvable by ground-truth name | 105 | 105 | PASS |
| Runtime-resolvable by component stem | 105 | 105 | PASS |
| Missing implementation | 0 | 0 | PASS |
| Missing runtime registration | 0 | 0 | PASS |
| Incorrect alias target | 0 | 0 | PASS |
| Unknown classifications | 0 | 0 | PASS |
| Five failed-run templates resolve | 5/5 | 5/5 | PASS |
| Five failed-run render smokes | 5/5 | 5/5 | PASS |
| Python targeted failures | 0 | 0 | PASS |
| Vitest targeted failures | 0 | 0 | PASS |
| Full Python regression failures | 0 | 0 | PASS |
| Full TypeScript regression failures | 0 | 0 | PASS |
