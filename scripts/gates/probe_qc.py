# -*- coding: utf-8 -*-
"""probe_qc.py — Canonical Review Probe & Quality Gate (S18 - LED-047..LED-050).

Single authoritative scene probe tool:
- Canonical render input via build_render_input() (S17)
- Canonical scene timing via derive_probe_frame_plan() (LED-047)
- Strict FPS authority, no silent default (LED-048)
- Mandatory contact sheet generation & validation (LED-049)
- Immutable ReviewBundle creation with hash-bound evidence chain (LED-050)

Usage:
  python probe_qc.py <project_dir> [comp_id]
  python probe_qc.py --verify <project_dir>
"""
from __future__ import annotations

import concurrent.futures
from datetime import datetime, timezone
import hashlib
import hmac
import inspect
import json
import os
from pathlib import Path
import secrets
import sys
from typing import Dict, List, Optional, Any, Tuple, Union

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from scripts.core.failure_model import FailureCode
from scripts.core.probe_planner import (
    derive_probe_frame_plan,
    ProbeFramePlan,
    ProbeInvalidBlueprintError,
    ProbeFrameReason,
)
from scripts.core.render_input import (
    build_render_input,
    get_render_props_path,
    RenderInputError,
)
from scripts.core.state_store import StateStore
from scripts.core.state_model import LifecycleState
from scripts.security.security import safe_subprocess


def get_qc_salt() -> bytes:
    """Retrieves cryptographic HMAC salt from QC_HMAC_SALT environment variable.
    Strictly mandatory: fails explicitly if QC_HMAC_SALT is not set or empty.
    No file fallback and no automatic salt generation is permitted.
    """
    salt_val = os.environ.get("QC_HMAC_SALT")
    if not salt_val or not salt_val.strip():
        raise RuntimeError(
            "QC_HMAC_SALT environment variable is required for QC report sealing and verification. "
            "No file fallback or automatic salt generation is permitted."
        )
    is_prod = os.environ.get("MOTION_ENV", "development").lower() == "production"
    if is_prod and len(salt_val.strip()) < 32:
        raise RuntimeError("QC_HMAC_SALT must be at least 32 characters in production environments.")
    return salt_val.strip().encode("utf-8")


def get_or_create_salt() -> bytes:
    """Backward compatibility alias for get_qc_salt."""
    return get_qc_salt()


def compute_seal(data: bytes, salt: bytes) -> str:
    """Computes HMAC-SHA256 seal for report data using cryptographic salt."""
    return hmac.new(salt, data, hashlib.sha256).hexdigest()


def verify_seal(report_path: Path | str) -> bool:
    """Verifies HMAC/SHA-256 seal of probe report against manual tampering."""
    p = Path(report_path) if isinstance(report_path, str) else report_path
    seal_file = p.with_suffix(p.suffix + ".seal")
    if not seal_file.exists():
        print("🛑 [SECURITY] ملف الختم الرقمي (.seal) لتقرير Probe-QC مفقود!")
        return False
    if not p.exists():
        print("🛑 [SECURITY] ملف تقرير Probe-QC غير موجود!")
        return False
    expected = seal_file.read_text(encoding="utf-8").strip()

    salt = get_qc_salt()
    data = p.read_bytes()
    actual = compute_seal(data, salt)

    if not hmac.compare_digest(expected, actual):
        print("🛑 [SECURITY] تقرير Probe-QC تم تعديله يدوياً (البصمة الرقمية HMAC غير متطابقة - تقرير مزوّر)")
        return False
    return True


def render_single_frame(
    frame_index: int,
    frame_number: int,
    probe_dir: Path,
    comp_id: str,
    exec_cwd: str,
    use_engine: bool,
    props_file_abs: Path,
) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
    """
    Renders a single frame still via Remotion.
    Returns (success, file_path, sha256_digest, error_message).
    """
    out_file = probe_dir / f"probe_{frame_index:02d}_f{frame_number}.png"
    npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
    cmd = [
        npx_cmd, "remotion", "still", "src/index.ts", comp_id,
        str(out_file.absolute()),
        f"--frame={frame_number}",
        "--timeout=120000",
    ]
    if use_engine or props_file_abs.exists():
        cmd.extend(["--props", str(props_file_abs)])

    print(f"📸 توليد اللقطة {frame_index:02d} (إطار {frame_number})...")
    res = safe_subprocess(cmd, cwd=exec_cwd, shell=False, capture_output=True, timeout=120)

    if res.returncode != 0:
        err_msg = res.stderr.decode("utf-8", errors="ignore") if res.stderr else "Unknown Remotion error"
        print(f"❌ فشل توليد اللقطة {frame_index:02d} (إطار {frame_number})")
        return False, None, None, f"Remotion still exited with {res.returncode}: {err_msg[:200]}"

    if not out_file.exists() or out_file.stat().st_size == 0:
        print(f"❌ ملف اللقطة {frame_index:02d} فارغ أو مفقود على القرص")
        return False, None, None, "Rendered frame file missing or empty on disk"

    # Compute frame digest
    f_sha = hashlib.sha256(out_file.read_bytes()).hexdigest()
    return True, str(out_file.absolute()), f_sha, None


def validate_image_header(file_path: Path) -> bool:
    """Verifies that an image file has valid PNG or JPEG magic bytes and non-zero size."""
    if not file_path.exists() or file_path.stat().st_size == 0:
        return False
    try:
        header = file_path.read_bytes()[:8]
        # PNG: \x89PNG\r\n\x1a\n, JPEG: \xff\xd8\xff
        return header.startswith(b"\x89PNG\r\n\x1a\n") or header.startswith(b"\xff\xd8\xff")
    except Exception:
        return False


def _probe_fail_closed_report(message: str) -> Dict[str, Any]:
    """Generates a structured, critical fail-closed report without touching disk or creating artifacts."""
    return {
        "status": "EXECUTION_FAILURE",
        "legacy_status": "fail",
        "errors": [{
            "code": FailureCode.SECURITY_POLICY_BLOCKED.value,
            "rule": "TENANT_PATH_RESOLUTION",
            "message": f"Tenant path resolution failed (Fail-closed): {message}",
            "severity": "CRITICAL",
        }],
        "checks": {
            "path_resolution": {
                "status": "FAIL",
                "severity": "CRITICAL",
                "message": f"Tenant path resolution failed (Fail-closed): {message}",
            }
        },
    }


def run_probe_qc(
    project_id: str,
    comp_id: str = "BlueprintVideo",
    workspace_root: Optional[Union[Path, str]] = None,
    workspace_id: Optional[str] = None,
    mock_render_fn: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Executes Canonical Review Probe QC for a verified tenant project ID (Production Gate).

    Mandatory Tenant Authorization:
    - Rejects path-like arguments (slashes, relative or absolute directory paths).
    - Requires verified workspace identity (via argument, AGY_WORKSPACE_ID, or TenantRepository).
    - Resolves strictly to projects/{workspace_id}/{project_id}/.
    - Strictly fails closed upon any resolution failure.
    - NEVER accepts unmanaged flat directories or direct filesystem paths.
    - NEVER derives confinement from supplied directory paths.
    """
    raw_id = str(project_id).strip()
    if "/" in raw_id or "\\" in raw_id or isinstance(project_id, Path):
        return _probe_fail_closed_report(
            f"Direct filesystem paths are not accepted by run_probe_qc: '{project_id}'. "
            "For production calls, supply a clean project_id. For trusted internal tools or tests, "
            "use run_probe_qc_for_trusted_directory() with an explicit confinement root and authorization context."
        )

    try:
        from scripts.security.path_security import validate_project_id, resolve_project_dir
        clean_id = validate_project_id(raw_id)
    except Exception as exc:
        return _probe_fail_closed_report(f"Invalid project_id: {exc}")

    ws = Path(workspace_root).resolve() if workspace_root else Path.cwd().resolve()
    ws_id = workspace_id or os.environ.get("AGY_WORKSPACE_ID")

    try:
        proj_dir = resolve_project_dir(
            clean_id,
            workspace_id=ws_id,
            base_dir=ws / "projects" if workspace_root else None,
        )
    except Exception as exc:
        return _probe_fail_closed_report(str(exc))

    return _execute_probe_qc_core(
        proj_dir=proj_dir,
        ws=ws,
        comp_id=comp_id,
        mock_render_fn=mock_render_fn,
    )


def run_probe_qc_for_trusted_directory(
    project_dir: Union[Path, str],
    trusted_confinement_root: Union[Path, str],
    authorization_context: Any,
    comp_id: str = "BlueprintVideo",
    mock_render_fn: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Separately validated Probe QC interface for trusted internal tools and test suites.

    Guarantees:
    - Requires an independently supplied, existing trusted_confinement_root.
    - Requires an explicit authorization_context with non-empty workspace_id.
    - Rejects any derivation of confinement root from project_dir itself.
    - Enforces confinement and symlink validation against trusted_confinement_root.
    - Rejects legacy flat directory structures lacking tenant workspace scoping.
    - Validates tenant ownership consistency between authorization_context and ProjectState.
    - Strictly fails closed without creating ReviewBundle or .studio_unlocked if authorization fails.
    """
    if not trusted_confinement_root:
        return _probe_fail_closed_report("trusted_confinement_root is strictly required for trusted directory execution")

    conf_root = Path(trusted_confinement_root).resolve()
    if not conf_root.is_dir():
        return _probe_fail_closed_report(f"trusted_confinement_root does not exist or is not a directory: {conf_root}")

    if not authorization_context:
        return _probe_fail_closed_report("authorization_context is strictly required for trusted directory execution")

    auth_ws = None
    if isinstance(authorization_context, dict):
        auth_ws = authorization_context.get("workspace_id")
    else:
        auth_ws = getattr(authorization_context, "workspace_id", None)

    if not auth_ws:
        return _probe_fail_closed_report("authorization_context must specify a non-empty workspace_id")

    try:
        from scripts.security.path_security import (
            validate_project_id,
            validate_workspace_id,
            check_confinement_and_symlink,
            TenantSecurityError,
        )
        v_auth_ws = validate_workspace_id(auth_ws)
    except Exception as exc:
        return _probe_fail_closed_report(f"Invalid workspace_id in authorization context: {exc}")

    target_path = Path(project_dir).resolve()
    if not target_path.is_dir():
        return _probe_fail_closed_report(f"Target project directory does not exist: {target_path}")

    # Strict confinement check against the independently supplied confinement root
    try:
        check_confinement_and_symlink(target_path, conf_root)
    except Exception as exc:
        return _probe_fail_closed_report(f"Target directory escapes trusted confinement root: {exc}")

    # Project identifier validation from directory name
    try:
        validate_project_id(target_path.name)
    except Exception as exc:
        return _probe_fail_closed_report(f"Target directory name is not a valid project identifier: {exc}")

    # Tenant scoping & ownership validation
    # A legacy flat directory (conf_root / project_id) without workspace scoping is strictly rejected
    if target_path.parent == conf_root:
        return _probe_fail_closed_report(
            f"Legacy flat project directory rejected: '{target_path.name}' is directly under '{conf_root.name}' "
            f"without tenant workspace confinement. Expected path under '{conf_root / v_auth_ws}'."
        )

    # Ensure target is confined within the authorized workspace directory
    expected_ws_dir = (conf_root / v_auth_ws).resolve()
    try:
        check_confinement_and_symlink(target_path, expected_ws_dir)
    except Exception as exc:
        return _probe_fail_closed_report(
            f"Cross-tenant directory access rejected: target directory '{target_path}' is not confined "
            f"within workspace '{v_auth_ws}': {exc}"
        )

    # If ProjectState exists on disk, verify tenant workspace consistency
    state_file = target_path / StateStore.STATE_FILE
    if state_file.is_file():
        try:
            st = StateStore.load(target_path)
            if st and st.workspace_id and st.workspace_id != v_auth_ws:
                return _probe_fail_closed_report(
                    f"Mismatched tenant ownership: ProjectState declares workspace '{st.workspace_id}', "
                    f"but authorization context provided '{v_auth_ws}'."
                )
        except Exception as exc:
            return _probe_fail_closed_report(f"Failed to verify ProjectState tenant ownership: {exc}")

    # Derive workspace_root for engine (remotion-app lookup)
    ws = conf_root.parent if conf_root.name == "projects" else conf_root

    return _execute_probe_qc_core(
        proj_dir=target_path,
        ws=ws,
        comp_id=comp_id,
        mock_render_fn=mock_render_fn,
    )


def _execute_probe_qc_core(
    proj_dir: Path,
    ws: Path,
    comp_id: str = "BlueprintVideo",
    mock_render_fn: Optional[Any] = None,
) -> Dict[str, Any]:

    bp_path = proj_dir / "05_blueprint.json"
    build_dir = proj_dir / "06_build"
    probe_dir = proj_dir / "03_probe_qc"
    engine_dir = ws / "remotion-app"
    if not (engine_dir / "src" / "index.ts").exists():
        repo_engine = Path(__file__).resolve().parent.parent.parent / "remotion-app"
        if (repo_engine / "src" / "index.ts").exists():
            engine_dir = repo_engine

    if not bp_path.exists():
        print(f"❌ لم نجد 05_blueprint.json في {proj_dir}")
        return {
            "status": "EXECUTION_FAILURE",
            "legacy_status": "fail",
            "errors": [{
                "code": FailureCode.PROBE_INVALID_BLUEPRINT.value,
                "message": f"Mandatory 05_blueprint.json missing at {bp_path}",
                "details": {"path": str(bp_path)}
            }]
        }

    probe_dir.mkdir(parents=True, exist_ok=True)

    # 1. Unified Render Input Authority (S17 - LED-054)
    try:
        render_input = build_render_input(
            proj_dir,
            workspace_root=ws,
            verify_files_on_disk=True,
            write_to_disk=True,
        )
    except RenderInputError as e:
        print(f"❌ خطأ في مدخلات الرندر لـ Probe-QC: {e}")
        return {
            "status": "EXECUTION_FAILURE",
            "legacy_status": "fail",
            "errors": [{
                "code": FailureCode.PROBE_INVALID_BLUEPRINT.value,
                "message": f"Render input error: {e}",
                "details": getattr(e, "details", {})
            }]
        }
    except Exception as e:
        print(f"❌ خطأ غير متوقع في تجهيز مدخلات Probe-QC: {e}")
        return {
            "status": "EXECUTION_FAILURE",
            "legacy_status": "fail",
            "errors": [{
                "code": FailureCode.PROBE_INVALID_BLUEPRINT.value,
                "message": f"Unexpected error: {e}",
                "details": {"error": str(e)}
            }]
        }

    bp = render_input["projectData"]["blueprint"]
    proj_meta = render_input["projectData"]["project"]
    props_file = get_render_props_path(proj_dir, workspace_root=ws)
    props_file_abs = props_file.resolve()

    # 2. Strict FPS Authority & Invariant (LED-048)
    bp_fps = bp.get("fps")
    proj_fps = proj_meta.get("fps")

    if bp_fps is None:
        print("❌ Blueprint missing canonical 'fps' field. Silent default forbidden.")
        return {
            "status": "EXECUTION_FAILURE",
            "legacy_status": "fail",
            "errors": [{
                "code": FailureCode.PROBE_INVALID_BLUEPRINT.value,
                "message": "Blueprint missing canonical 'fps' field. Silent default forbidden.",
                "details": {}
            }]
        }

    if proj_fps is not None and int(proj_fps) != int(bp_fps):
        print(f"❌ FPS Mismatch: project specifies {proj_fps}, blueprint specifies {bp_fps}.")
        return {
            "status": "EXECUTION_FAILURE",
            "legacy_status": "fail",
            "errors": [{
                "code": FailureCode.PROBE_INVALID_BLUEPRINT.value,
                "message": f"FPS mismatch between project ({proj_fps}) and blueprint ({bp_fps}).",
                "details": {"project_fps": proj_fps, "blueprint_fps": bp_fps}
            }]
        }

    canonical_fps = int(bp_fps)

    # 3. Canonical Probe Frame Derivation (LED-047)
    try:
        plan = derive_probe_frame_plan(
            bp,
            project_id=proj_dir.name,
            canonical_fps=canonical_fps,
        )
    except ProbeInvalidBlueprintError as e:
        print(f"❌ خطأ في هيكل المشاهد لاستخراج إطارات الفحص: {e}")
        return {
            "status": "EXECUTION_FAILURE",
            "legacy_status": "fail",
            "errors": [{
                "code": FailureCode.PROBE_INVALID_BLUEPRINT.value,
                "message": str(e),
                "details": {}
            }]
        }

    # Resolve execution directory
    use_engine = False
    if not (build_dir / "src" / "index.ts").exists() and (engine_dir / "src" / "index.ts").exists():
        exec_cwd = str(engine_dir)
        use_engine = True
    else:
        if not build_dir.exists():
            print("❌ لم نجد مجلد 06_build. شغّل materialize_project.py أولاً.")
            return {
                "status": "EXECUTION_FAILURE",
                "legacy_status": "fail",
                "errors": [{
                    "code": FailureCode.PROBE_REPORT_FAILED.value,
                    "message": "Neither 06_build nor remotion-app runtime found.",
                    "details": {}
                }]
            }
        exec_cwd = str(build_dir)

    print(f"🎬 جاري فحص {len(plan.frames)} لقطات مهمة لفحص الجودة عبر الـ Canonical Scenes...")

    rendered_files: List[str] = []
    frame_hashes: Dict[str, str] = {}
    frame_errors: List[Dict[str, Any]] = []
    content_defects: List[Dict[str, Any]] = []

    # Map frame -> reasons for report
    frame_reasons: Dict[int, List[str]] = {}
    frame_scenes: Dict[int, Optional[str]] = {}
    for s in plan.samples:
        frame_reasons.setdefault(s.frame, []).append(s.reason)
        if s.scene_id:
            frame_scenes[s.frame] = s.scene_id

    # 4. Render representative frames (Multi-threaded or mock)
    if mock_render_fn:
        for idx, f in enumerate(plan.frames):
            ok, fpath, fsha, err = mock_render_fn(idx, f, probe_dir)
            if ok and fpath:
                rendered_files.append(fpath)
                if fsha:
                    frame_hashes[Path(fpath).name] = fsha
            else:
                frame_errors.append({
                    "code": FailureCode.PROBE_FRAME_RENDER_FAILED.value,
                    "frame": f,
                    "message": err or "Mock render failed",
                })
    else:
        concurrency = max(1, int(os.environ.get("PROBE_CONCURRENCY", "1")))
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            future_to_frame = {
                executor.submit(
                    render_single_frame,
                    i, f, probe_dir, comp_id, exec_cwd, use_engine, props_file_abs
                ): (i, f)
                for i, f in enumerate(plan.frames)
            }
            for future in concurrent.futures.as_completed(future_to_frame):
                i, f = future_to_frame[future]
                try:
                    ok, fpath, fsha, err = future.result()
                    if ok and fpath:
                        rendered_files.append(fpath)
                        if fsha:
                            frame_hashes[Path(fpath).name] = fsha
                    else:
                        frame_errors.append({
                            "code": FailureCode.PROBE_FRAME_RENDER_FAILED.value,
                            "frame": f,
                            "message": err or "Frame render failed",
                        })
                except Exception as e:
                    frame_errors.append({
                        "code": FailureCode.PROBE_FRAME_RENDER_FAILED.value,
                        "frame": f,
                        "message": str(e),
                    })

    # Sort rendered files for deterministic contact sheet sampling
    rendered_files = sorted(rendered_files)

    # 5. Build Contact Sheet (LED-049: Mandatory Evidence)
    out_sheet = probe_dir / "contact_sheet.png"
    proj_sheet = proj_dir / "contact_sheet.png"
    contact_sheet_sha: Optional[str] = None
    contact_sheet_errors: List[Dict[str, Any]] = []

    if frame_errors or len(rendered_files) != len(plan.frames) or len(plan.frames) == 0:
        # If any frame render failed, contact sheet generation MUST fail closed
        contact_sheet_errors.append({
            "code": FailureCode.PROBE_CONTACT_SHEET_FAILED.value,
            "message": "Cannot build contact sheet because one or more probe frames failed to render.",
            "details": {"expected_frames": len(plan.frames), "rendered_frames": len(rendered_files)}
        })
    else:
        print("🎞️ إنشاء Contact Sheet من اللقطات الممثلة...")
        # Sample up to 6 key frames across timeline for contact sheet
        sampled = rendered_files if len(rendered_files) <= 6 else [
            rendered_files[0],
            rendered_files[len(rendered_files) // 5],
            rendered_files[2 * len(rendered_files) // 5],
            rendered_files[3 * len(rendered_files) // 5],
            rendered_files[4 * len(rendered_files) // 5],
            rendered_files[-1]
        ]

        ff_cmd = ["ffmpeg", "-y"]
        for f in sampled:
            ff_cmd.extend(["-i", f])
        ff_cmd.extend(["-filter_complex", f"hstack=inputs={len(sampled)}", "-loglevel", "error", str(out_sheet)])

        try:
            res_cs = safe_subprocess(ff_cmd)
            if res_cs.returncode != 0:
                contact_sheet_errors.append({
                    "code": FailureCode.PROBE_CONTACT_SHEET_FAILED.value,
                    "message": f"FFmpeg contact sheet creation failed with exit code {res_cs.returncode}",
                    "details": {"stderr": res_cs.stderr.decode("utf-8", errors="ignore") if res_cs.stderr else ""}
                })
            elif not validate_image_header(out_sheet):
                contact_sheet_errors.append({
                    "code": FailureCode.PROBE_CONTACT_SHEET_FAILED.value,
                    "message": "Generated contact sheet is invalid, empty, or has corrupt image header.",
                    "details": {"size_bytes": out_sheet.stat().st_size if out_sheet.exists() else 0}
                })
            else:
                import shutil
                shutil.copy2(str(out_sheet), str(proj_sheet))
                contact_sheet_sha = hashlib.sha256(proj_sheet.read_bytes()).hexdigest()
                print(f"  ✓ contact sheet ({len(sampled)} frame(s)) → {proj_sheet}")
        except Exception as e:
            contact_sheet_errors.append({
                "code": FailureCode.PROBE_CONTACT_SHEET_FAILED.value,
                "message": f"FFmpeg execution exception: {e}",
                "details": {"error": str(e)}
            })

    # 6. Overall Status Model (Section 16: PASS vs CONTENT_FAILURE vs EXECUTION_FAILURE)
    all_execution_errors = frame_errors + contact_sheet_errors
    if all_execution_errors:
        overall_status = "EXECUTION_FAILURE"
        legacy_status = "fail"
    elif content_defects:
        overall_status = "CONTENT_FAILURE"
        legacy_status = "fail"
    else:
        overall_status = "PASS"
        legacy_status = "pass"

    is_passed = (overall_status == "PASS")

    # Hashes of upstream artifacts
    blueprint_sha = hashlib.sha256(bp_path.read_bytes()).hexdigest() if bp_path.exists() else ""
    mm_path = proj_dir / "media_map.json"
    media_map_sha = hashlib.sha256(mm_path.read_bytes()).hexdigest() if mm_path.exists() else ""
    render_input_sha = hashlib.sha256(props_file_abs.read_bytes()).hexdigest() if props_file_abs.exists() else ""

    # Assemble per-probe results
    probes_list = []
    for i, f in enumerate(plan.frames):
        fname = f"probe_{i:02d}_f{f}.png"
        f_abs = str((probe_dir / fname).absolute())
        f_rendered = f_abs in rendered_files
        probes_list.append({
            "frame": f,
            "file": fname,
            "sha256": frame_hashes.get(fname),
            "reasons": frame_reasons.get(f, []),
            "scene_id": frame_scenes.get(f),
            "check": "سليم ومكتمل" if f_rendered else "فشل الرندر",
            "status": "pass" if f_rendered else "fail",
        })

    # Assemble comprehensive Probe Report Contract
    report: Dict[str, Any] = {
        "schema_version": "2.0.0",
        "status": overall_status,
        "legacy_status": legacy_status,
        "project_id": proj_dir.name,
        "fps": canonical_fps,
        "total_duration_frames": plan.total_duration_frames,
        "sampled_frames": plan.frames,
        "probe_frame_plan": plan.to_dict(),
        "probes": probes_list,
        "contact_sheet": {
            "file": "contact_sheet.png",
            "sha256": contact_sheet_sha,
            "valid": contact_sheet_sha is not None and not contact_sheet_errors,
        },
        "blueprint_sha256": blueprint_sha,
        "media_map_sha256": media_map_sha,
        "render_input_sha256": render_input_sha,
        "errors": all_execution_errors + content_defects,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # 7. Write probe_qc_report.json
    report_path = proj_dir / "probe_qc_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # 8. Cryptographic Seal
    seal_file = report_path.with_suffix(report_path.suffix + ".seal")
    salt = get_qc_salt()
    data = report_path.read_bytes()
    checksum = compute_seal(data, salt)
    seal_file.write_text(checksum, encoding="utf-8")
    print(f"🔏 تم ختم التقرير ببصمة رقمية HMAC-SHA256 ({checksum[:12]}...)")

    if not verify_seal(report_path):
        print("🛑 تقرير Probe-QC فشل التحقق من الختم")
        return {"status": "EXECUTION_FAILURE", "legacy_status": "fail", "errors": ["Seal verification failed"]}

    # 9. Review Evidence Bundle & Studio Unlock (LED-050)
    review_bundle_id: Optional[str] = None
    bundle_digest: Optional[str] = None

    if is_passed:
        # Check if project state exists; if so, create immutable ReviewBundle
        state_file = proj_dir / StateStore.STATE_FILE
        if state_file.exists():
            from scripts.core.review_service import ReviewService
            try:
                bundle = ReviewService.create_review_bundle(
                    project_dir=proj_dir,
                    require_contact_sheet=True,
                    render_input_sha256=render_input_sha,
                    probe_frame_plan_digest=plan.plan_digest,
                    rendered_frames_sha256=frame_hashes,
                )
                review_bundle_id = bundle.review_bundle_id
                bundle_digest = bundle.bundle_digest
                report["review_bundle_id"] = review_bundle_id
                report["bundle_digest"] = bundle_digest
                print(f"📦 تم إنشاء حزمة المراجعة الرسمية: {review_bundle_id} (Digest: {bundle_digest[:12]}...)")
            except Exception as e:
                print(f"❌ فشل إنشاء حزمة المراجعة عبر ReviewService: {e}")
                unlock_file = proj_dir / ".studio_unlocked"
                if unlock_file.exists():
                    try:
                        unlock_file.unlink()
                    except Exception:
                        pass
                return {
                    "status": "EXECUTION_FAILURE",
                    "legacy_status": "fail",
                    "errors": [{
                        "code": FailureCode.PROBE_REPORT_FAILED.value,
                        "message": f"Failed to create ReviewBundle: {e}",
                        "details": {"error": str(e)}
                    }]
                }

        # Write .studio_unlocked marker with report checksum and review_bundle_id
        unlock_file = proj_dir / ".studio_unlocked"
        payload = {
            "unlocked_at": datetime.now(timezone.utc).isoformat(),
            "report_checksum": checksum,
            "review_bundle_id": review_bundle_id,
            "bundle_digest": bundle_digest,
        }
        unlock_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"🔓 تم إنشاء {unlock_file} مع ربطه ببصمة التقرير وحزمة المراجعة")
    else:
        # Probe failed: Clean up any prior .studio_unlocked marker
        unlock_file = proj_dir / ".studio_unlocked"
        if unlock_file.exists():
            try:
                unlock_file.unlink()
            except Exception:
                pass
        print(f"❌ فشل Probe-QC: {len(all_execution_errors + content_defects)} أخطاء تم رصدها.")

    return report


def main() -> None:
    """CLI Entry Point."""
    # Security: check caller stack against illegal invocation
    try:
        caller = inspect.stack()[1]
        if "pipeline_guard" in caller.filename or "write_to_file" in str(caller):
            print("🛑 [SECURITY] محاولة كتابة تقرير QC من مصدر غير مصرح به")
            sys.exit(1)
    except IndexError:
        pass

    if len(sys.argv) >= 2 and sys.argv[1] == "--verify":
        target_dir = Path(sys.argv[2] if len(sys.argv) > 2 else ".").resolve()
        report_file = target_dir / "probe_qc_report.json" if target_dir.is_dir() else target_dir
        if verify_seal(report_file):
            print("✅ تقرير Probe-QC أصلي وموثق بالختم الرقمي")
            sys.exit(0)
        else:
            print("🛑 تقرير Probe-QC تم تعديله يدوياً")
            sys.exit(1)

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    proj_arg = sys.argv[1]
    comp_arg = sys.argv[2] if len(sys.argv) > 2 else "BlueprintVideo"

    result = run_probe_qc(proj_arg, comp_id=comp_arg)
    if result.get("status") == "PASS":
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
