# MOTION Architecture Atlas — Developer Troubleshooting Guide

> **Scope:** Practical diagnostic and root-cause analysis guide for backend engineers, DevOps operators, and systems architects maintaining MOTION.
> **Philosophy:** Distinguish root causes from downstream symptoms. Never apply superficial symptom patches; verify invariants.

---

## 1. Diagnostic Architecture & Error Propagation

MOTION enforces a layered fail-closed architecture. Errors originate at specific domain boundaries and propagate through standardized exception hierarchies:

```
[Hardware / System / Network Layer]
                 │
                 ▼
[Security & Path Jail Boundary]   ──► SecurityViolationError (403/Forbidden)
                 │
                 ▼
[Relational CAS & Storage Layer]  ──► RevisionConflictError (409/Conflict)
                 │
                 ▼
[Governance & Review Gate]        ──► RenderNotAuthorizedError (403/Blocked)
                 │
                 ▼
[Project Lock & Lease Fence]      ──► LockAcquisitionError (409/Retry)
                 │
                 ▼
[Remotion & FFmpeg Engine]        ──► RenderExecutionError (500/Pipeline Failed)
                 │
                 ▼
[Probe QC & Final QC Gates]       ──► QualityGateFailure (422/Defect Detected)
```

When investigating any issue, check logs from the innermost boundary outward to find the root cause rather than reacting to the outer HTTP status.

---

## 2. Common Symptom to Root Cause Mapping Matrix

| Symptom / Error Code | Observed In | Likely Subsystem | Critical Source Files | Diagnostic Log Signature |
| :--- | :--- | :--- | :--- | :--- |
| `RENDER_NOT_AUTHORIZED` | Worker / Pipeline | Review Governance | `api/services/review_service.py`, `scripts/pipeline.py` | `[GUARDIAN BLOCK] Render execution not authorized` |
| `sqlite3.IntegrityError: FOREIGN KEY constraint failed` | Project Execution Lock | Run Repository / Durable Worker | `scripts/core/project_lock.py`, `scripts/core/run_repository.py` | `FOREIGN KEY constraint failed on project_leases(workspace_id)` |
| `DATABASE_URL stripped / Database missing` | Child Process (Remotion/Render) | Security Command Policy | `scripts/core/security/command_policy.py`, `scripts/pipeline.py` | `sqlite3.OperationalError: no such table: runs` (under `AGY_IS_MANAGED=1`) |
| `SecurityViolationError: Path outside workspace` | Path Sanitizer | Auth & Tenancy | `scripts/core/security/path_sanitizer.py` | `Security Violation: Attempted traversal outside workspace` |
| `409 Conflict: Revision mismatch` | Creative / Document API | Canonical Document Repository | `api/services/canonical_document_service.py` | `RevisionConflictError: Expected revision X, found Y` |
| `Probe QC Failure: Audio duration mismatch` | Review Service / Gate | Quality Control | `scripts/gates/probe_qc.py` | `Audio duration X does not match scene target Y (+-0.5s)` |
| `Remotion exit code 1 / Webpack error` | Rendering Engine | Remotion / React | `scripts/render_project.py`, `remotion-app/` | `Error: Cannot find module '../templates/...'` or `Chromium crashed` |
| `Final QC Failure: Stream defect` | Post-Render Gate | Quality Control | `scripts/gates/final_qc.py` | `Final QC Failed: Video codec is X, expected h264` |
| `416 Range Not Satisfiable` | Artifact Download | Storage & Delivery | `api/routers/artifacts.py` | `Invalid byte range header: bytes=X-Y/Z` |
| `Worker Run Queue Stall` | Worker Pool | Durable Execution | `scripts/core/worker.py` | `Active lease held by dead worker; lease expired` |

---

## 3. Deep-Dive Diagnostic Scenarios

### Scenario 1: `RENDER_NOT_AUTHORIZED` / Governance Gate Block

#### Root Cause Analysis:
MOTION requires two conditions for rendering:
1. An approved `ReviewDecision(status="APPROVED")` must exist in the database for the project.
2. The SHA-256 hash of `05_blueprint.json` on disk must **identically match** the `blueprint_hash` stored in the canonical document repository when approval was granted.
If a developer or script modifies `05_blueprint.json` on disk after review approval was issued, the worker recalculates the hash, detects tampering or drift, and immediately aborts with `RENDER_NOT_AUTHORIZED`.

#### Diagnostic Procedure:
1. Check the database approval record:
   ```bash
   sqlite3 data/runs.db "SELECT project_id, status, blueprint_hash FROM review_decisions WHERE project_id='proj_xyz';"
   ```
2. Compute the disk blueprint hash:
   ```bash
   sha256sum projects/proj_xyz/05_blueprint.json
   ```
3. If hashes differ, the blueprint was altered post-approval. Re-submit the updated blueprint via `POST /api/v1/projects/{id}/creative/apply` and grant a fresh approval via `POST /api/v1/projects/{id}/review/decision`.

---

### Scenario 2: Foreign Key Integrity Error on `project_leases`

#### Root Cause Analysis:
`project_leases` has a foreign key constraint: `FOREIGN KEY (workspace_id) REFERENCES workspaces(id)`.
When SQLite enables `PRAGMA foreign_keys = ON`, inserting a lease where `workspace_id="ws_default"` when the project actually belongs to `workspace_xyz` causes SQLite to reject the insert if `ws_default` is not registered in the `workspaces` table.

#### Fix & Verification:
Ensure `ProjectExecutionLock` resolves the actual project `workspace_id` from the database or project metadata before acquiring direct leases:
```python
# In scripts/core/project_lock.py:
workspace_id = self._resolve_workspace_id(project_id)
self.repo.acquire_direct_project_lease(project_id, lease_holder, ttl_seconds, workspace_id=workspace_id)
```

---

### Scenario 3: Environment Sanitization Stripping Database Credentials

#### Root Cause Analysis:
`CommandPolicy.sanitize_environment` strips dangerous or unapproved environment variables before launching child processes.
If `scripts/pipeline.py` or `scripts/render_project.py` are executed without `allow_database_env=True`, `DATABASE_URL` is removed. When running under managed mode (`AGY_IS_MANAGED=1`), the script falls back to the default SQLite path instead of the production database URL, causing missing table errors or unapproved state lookups.

#### Verification:
Confirm that `DATABASE_AUTHORIZED_SCRIPTS` in `scripts/core/security/command_policy.py` includes `"scripts/pipeline.py"` and `"scripts/render_project.py"`, and verify that `safe_subprocess` passes `allow_database_env=True` when database variables are active.

---

### Scenario 4: Path Traversal & Jailbreak Rejections

#### Root Cause Analysis:
`PathSanitizer.assert_in_workspace` resolves the canonical real path of any target file and verifies that its path components start with the tenant's workspace root.
If an attacker or buggy script passes `../../etc/passwd` or creates a symlink pointing outside the workspace, `PathSanitizer` raises `SecurityViolationError`.

#### Diagnostic Command:
```bash
python -c "
from pathlib import Path
from scripts.core.security.path_sanitizer import PathSanitizer
sanitizer = PathSanitizer(Path('/tmp/workspace_alpha'))
print(sanitizer.sanitize_path('/tmp/workspace_alpha/assets/logo.png')) # OK
sanitizer.sanitize_path('/tmp/workspace_alpha/../../etc/shadow') # Raises SecurityViolationError
"
```

---

### Scenario 5: CAS Revision Conflict (`409 Conflict`)

#### Root Cause Analysis:
`CanonicalDocumentService` uses optimistic concurrency control. Every document write requires the client to supply `expected_revision`.
If Client A and Client B both fetch revision 3, Client A writes revision 4 first. When Client B attempts to write with `expected_revision=3`, the server detects that the current revision is now 4 and rejects the write with `409 Conflict`.

#### Resolution:
Client B must fetch the latest state (`GET /api/v1/projects/{id}`), reconcile its changes against the updated document, and submit with `expected_revision=4`.

---

### Scenario 6: Remotion Frame Rendering & Webpack Errors

#### Root Cause Analysis:
Remotion bundles visual templates using Webpack. Failures typically arise from:
1. Missing React component imports in `templates/`.
2. Incorrect syntax in custom `.tsx` files.
3. System fonts not installed on the host or Docker container (causes Chromium layout crashes).

#### Diagnostic Commands:
1. Test TypeScript compilation without emitting files:
   ```bash
   cd remotion-app && npx tsc --noEmit
   ```
2. Run Vitest component unit tests:
   ```bash
   cd remotion-app && npm run test
   ```
3. Test isolated template rendering:
   ```bash
   python scripts/validators/inspect_template.py LivingCanvas
   ```

---

### Scenario 7: Final QC ffprobe Rejection

#### Root Cause Analysis:
`scripts/gates/final_qc.py` inspects the final MP4 using `ffprobe`. Common failures include:
- Duration mismatch: The video duration is more than 0.1s different from target blueprint duration.
- Codec mismatch: FFmpeg encoded in MPEG-4 Part 2 or VP8 instead of H.264 (`avc1`).
- Missing audio stream: Video has no audio track or the audio was muted.
- Missing `moov` atom: Web streaming requires `faststart` so metadata is at the beginning of the file.

#### Diagnostic Command:
```bash
ffprobe -v error -show_entries format=duration,size,bit_rate -show_streams -print_format json projects/proj_xyz/output/final.mp4
```

---

## 4. Universal Diagnostic Toolbelt

When troubleshooting MOTION on any environment, execute these standard diagnostics in order:

```bash
# 1. Check code quality and style invariants
ruff check api/ scripts/core/

# 2. Check TypeScript and frontend bundle health
cd remotion-app && npm run test && npx tsc --noEmit && cd ..

# 3. Check full backend test suite
pytest tests/ -q

# 4. Run authentic product E2E HTTP-to-MP4 verification
pytest tests/e2e/test_product_http_to_mp4_e2e.py -v -s

# 5. Inspect database leases and active runs
sqlite3 data/runs.db "SELECT id, project_id, status, worker_id, created_at FROM runs ORDER BY created_at DESC LIMIT 5;"
sqlite3 data/runs.db "SELECT * FROM project_leases;"
```
