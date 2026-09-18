# CRD-020: DataStory Prop Contract / Deferred Runtime Failure Remediation

## 1. Root Cause
During Phase 9.13 Clean Room execution, rendering failed at global frame 312 (`local frame ~72` of `Datastorywrapper`):
```text
TypeError: Cannot read properties of undefined (reading 'slice')
    at AnimatedBarChart (src/remotion/scenes/animated-bar-chart/index.tsx)
```
Prior to migration into `BlueprintVideo`, `DataStory` was mounted in `Root.tsx` with Remotion `defaultProps` providing `barData`, `metrics`, and `steps`. When unified into `BlueprintVideo`, `template_props` became dynamic. Because `DataStory` did not handle omitted optional props, it forwarded `undefined` to low-level primitive components (`AnimatedBarChart`, `MetricTicker`, `TimelineSteps`), which strictly expect array inputs. Earlier static smoke tests sampled only frame 0 (the hook phase), failing to reach the deferred transition where `AnimatedBarChart` mounts at frame ~72.

## 2. Historical Default Source SHA
The canonical historical defaults were recovered from git history:
- **Source Commit**: `9dcb888b1ca31997e5646e0854d592e0172545c0` (`remotion-app/src/Root.tsx`)
- **Preserved Datasets**:
  - `DEFAULT_BAR_DATA`:
    ```json
    [
      {"label": "Q1", "value": 40},
      {"label": "Q2", "value": 65},
      {"label": "Q3", "value": 85},
      {"label": "Q4", "value": 95}
    ]
    ```
  - `DEFAULT_METRICS`:
    ```json
    [
      {"label": "Throughput", "value": 120, "suffix": "%"},
      {"label": "Latency", "value": 636, "suffix": "ms"},
      {"label": "Templates", "value": 172}
    ]
    ```
  - `DEFAULT_STEPS`:
    ```json
    [
      {"title": "Discovery", "description": "Scan templates and indexes"},
      {"title": "Composition", "description": "Assemble dynamic timeline"},
      {"title": "Studio", "description": "Live instant preview"}
    ]
    ```

## 3. Ownership Contract
- **Boundary**: `DataStory` owns composition-level optional defaults. Low-level primitives (`AnimatedBarChart`, `MetricTicker`, `TimelineSteps`) retain strict required contracts (`data: ChartDatum[]`, `metrics: MetricTickerItem[]`, `steps: TimelineStep[]`).
- **Nullish Semantics**:
  - `undefined`: falls back to canonical historical defaults (`barData ?? DEFAULT_BAR_DATA`).
  - Explicit empty array `[]`: preserved as-is.
  - `null` / malformed objects / non-array scalars: rejected fail-closed via runtime Zod schema parsing before render.
- **Pre-Render Gate**: `scripts/gates/code_template_gate.py` rejects invalid shapes in `template_props` for `Datastorywrapper` ahead of Remotion execution.

## 4. Deferred Branches Discovered
Within `DataStory` (duration 420 frames):
- Hook Scene: frames 0–83
- **AnimatedBarChart deferred branch**: mounts at frame ~72 (after 12-frame crossfade overlap), duration 92 frames.
- **MetricTicker deferred branch**: mounts at frame ~152 (after transition), duration 88 frames.
- **TimelineSteps deferred branch**: mounts at frame ~228 (after transition), duration 88 frames.
- CaptionBumper (Insight): mounts at frame ~304, duration 66 frames.
- EndCard (CTA): mounts at frame ~358, duration 62 frames.

All three deferred data-consuming child scenes (`AnimatedBarChart`, `MetricTicker`, `TimelineSteps`) were vulnerable to `undefined` prop dereferencing when optional props were omitted. All three were remediated under the same contract.

## 5. Temporal Smoke Evidence
Multi-frame temporal smoke script `scripts/archive/smoke_crd020_temporal.py` exercised 14 local lifecycle frames across all 4 Clean-Room templates:
- `Herodeviceassemblewrapper`: frames 0, 90, 179 (PASS)
- `Splitscreenwrapper`: frames 0, 90, 179 (PASS)
- `Datastorywrapper`:
  - Local frame 0 (early hook): PASS
  - Local frame 85 (AnimatedBarChart active): PASS
  - Local frame 170 (MetricTicker active): PASS
  - Local frame 250 (TimelineSteps active): PASS
  - Local frame 375 (Late CTA): PASS
- `Creatorreelwrapper`: frames 0, 90, 179 (PASS)
Result: **14/14 checkpoints passed** with non-empty rendered PNG frames.

## 6. Test Results
- **TypeScript (`npm test`)**: 4 test files, 48 passed, 0 failures.
  - `tests/datastory_contract.test.ts`: 9 tests passed.
  - `tests/contracts.test.ts`: 10 tests passed.
  - `tests/merge.test.ts`: 10 tests passed.
  - `tests/template_runtime_resolution.test.ts`: 19 tests passed.
- **Python (`python -m pytest tests`)**: 154 passed, 1 skipped, 0 failures.
  - `tests/test_datastory_gate_contract.py`: 6 tests passed.
