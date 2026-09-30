"""
Canonical Transactional Materializer Subsystem (S13 - ASSET-003, ASSET-010, LED-036).

Single Visibility / Commit Point Architecture:
- Each generation is staged in an immutable generation directory:
  remotion-app/public/projects/<project_id>/generations/<gen_id>/
- The staged media map is staged at:
  <project_dir>/.media_map_<gen_id>.tmp
  Entries map: asset_id -> "projects/<project_id>/generations/<gen_id>/<candidate_filename>"
- Full verification of staged files and fsync occurs BEFORE commit.
- THE SINGLE COMMIT MOMENT:
  os.replace(project_dir / f".media_map_{gen_id}.tmp", project_dir / "media_map.json")
- Consumers reading media_map.json atomically see either Generation A or Generation B.
- Zero windows of missing media or mixed generations.
- Post-commit cleanup removes unreferenced inactive generations. Failure of cleanup never affects active generation.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from scripts.core.blueprint_errors import BlueprintError, BlueprintValidationError
from scripts.core.blueprint_loader import load_blueprint
from scripts.core.manifest_errors import ManifestError, ProjectIdentityMismatchError
from scripts.core.manifest_loader import load_manifest
from scripts.core.manifest_model import ManifestV2
from scripts.core.project_identity import validate_project_identity
from scripts.security.path_security import (
    PathSecurityViolation,
    resolve_safe_path,
    validate_asset_id,
    validate_project_id,
    validate_source_asset,
)


class MaterializationError(Exception):
    """Base exception for materialization failures."""
    pass


class MaterializationPreflightError(MaterializationError):
    """Raised when preflight checks fail before any mutations occur."""
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Preflight validation failed with {len(errors)} error(s):\n" + "\n".join(f" - {e}" for e in errors))


class MaterializationStagingError(MaterializationError):
    """Raised when staging or copying assets fails."""
    pass


class MaterializationVerificationError(MaterializationError):
    """Raised when staged assets fail integrity verification before commit."""
    pass


def _fsync_file(file_path: Path) -> None:
    """Flushes and syncs a file to physical disk."""
    try:
        with open(file_path, "rb") as f:
            f.flush()
            os.fsync(f.fileno())
    except (OSError, ValueError):
        pass


def _fsync_dir(dir_path: Path) -> None:
    """Fsyncs a directory on platforms supporting it (e.g. POSIX)."""
    try:
        if hasattr(os, "O_DIRECTORY"):
            flags = os.O_RDONLY | os.O_DIRECTORY
        else:
            flags = os.O_RDONLY
        fd = os.open(str(dir_path), flags)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except (OSError, ValueError, AttributeError):
        pass


def get_active_generation_id(project_dir: Path) -> Optional[str]:
    """
    Extracts the currently active generation_id from project_dir / 'media_map.json'.
    Returns None if media_map.json is missing, empty, or not generation-based.
    """
    map_file = project_dir / "media_map.json"
    if not map_file.exists():
        return None
    try:
        data = json.loads(map_file.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        for val in data.values():
            if isinstance(val, str) and "/generations/" in val:
                parts = val.split("/generations/")[1].split("/")
                if parts and parts[0]:
                    return parts[0]
    except Exception:
        return None
    return None


def get_published_generations_history(
    pub_project: Path,
    project_dir: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieves the chronological history of published generations.
    Returns list of dicts with {"generation_id": str, "published_at": float}.
    """
    for root_dir in [pub_project, project_dir]:
        if not root_dir or not root_dir.exists():
            continue
        history_file = root_dir / ".generations_history.json"
        if history_file.exists():
            try:
                data = json.loads(history_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
            except Exception:
                pass
    return []


def record_generation_published(
    pub_project: Path,
    gen_id: str,
    project_dir: Optional[Path] = None,
    published_at: Optional[float] = None,
) -> None:
    """
    Atomically records a generation as published in .generations_history.json.
    """
    pub_at = published_at if published_at is not None else time.time()
    for root_dir in [pub_project, project_dir]:
        if not root_dir or not root_dir.exists():
            continue
        history_file = root_dir / ".generations_history.json"
        history: List[Dict[str, Any]] = []
        if history_file.exists():
            try:
                data = json.loads(history_file.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    history = data
            except Exception:
                history = []

        existing = [h for h in history if h.get("generation_id") == gen_id]
        if existing:
            existing[0]["published_at"] = pub_at
        else:
            history.append({
                "generation_id": gen_id,
                "published_at": pub_at,
            })

        if len(history) > 50:
            history = history[-50:]

        tmp_file = root_dir / f".generations_history_{gen_id}_{uuid.uuid4().hex[:6]}.tmp"
        try:
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(str(tmp_file), str(history_file))
            _fsync_dir(root_dir)
        except Exception:
            tmp_file.unlink(missing_ok=True)


def cleanup_inactive_generations(
    pub_project: Path,
    active_gen_id: Optional[str],
    project_dir: Optional[Path] = None,
    keep_previous: int = 1,
    grace_seconds: float = 300.0,
    clean_orphans: bool = True,
    orphan_grace_seconds: float = 30.0,
    now: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Safely retires inactive generations and removes lingering temporary files.
    
    Reader-Safe Retirement Policy:
    1. Active Generation: The generation currently referenced by media_map.json is NEVER deleted.
    2. Published Retention (keep_previous, default 1): Keeps the N most recent published generations
       prior to active, guaranteeing that any reader that obtained media_map.json just before a swap
       can finish consuming files without FileNotFoundError.
    3. Grace Period (grace_seconds, default 300s): Preserves published generations younger than grace_seconds.
    4. Garbage Collection Eligibility: A published generation is only eligible for GC if it is NOT active,
       NOT in the keep_previous retained set, AND older than grace_seconds.
    5. Orphan Cleanup: Uncommitted/aborted generations (never published in media_map.json) can be safely
       cleaned up if older than orphan_grace_seconds (default 30s).
    6. Decoupled Resilience: Failure of cleanup NEVER invalidates or affects the active generation.
    """
    current_time = time.time() if now is None else now
    result: Dict[str, Any] = {
        "active_generation": active_gen_id,
        "preserved": [],
        "deleted": [],
        "orphans_deleted": [],
        "errors": [],
    }

    # 1. Clean up lingering .media_map_*.tmp files in project_dir
    if project_dir and project_dir.exists():
        for tmp_file in project_dir.glob(".media_map_*.tmp"):
            try:
                if not active_gen_id or active_gen_id not in tmp_file.name:
                    tmp_file.unlink(missing_ok=True)
            except Exception as e:
                result["errors"].append(str(e))

    gen_root = pub_project / "generations"
    if not gen_root.exists():
        return result

    # 2. Identify published history
    history = get_published_generations_history(pub_project, project_dir)
    published_map: Dict[str, float] = {}
    for h in history:
        gid = h.get("generation_id")
        pub_at = h.get("published_at", 0.0)
        if gid:
            published_map[gid] = pub_at

    if active_gen_id and active_gen_id not in published_map:
        published_map[active_gen_id] = current_time

    sorted_published = sorted(published_map.items(), key=lambda x: x[1])
    sorted_published_ids = [gid for gid, _ in sorted_published]

    # Calculate protected generations set
    protected_set: Set[str] = set()
    if active_gen_id:
        protected_set.add(active_gen_id)

    if active_gen_id and active_gen_id in sorted_published_ids:
        idx = sorted_published_ids.index(active_gen_id)
        prev_ids = sorted_published_ids[:idx]
        if keep_previous > 0:
            for gid in prev_ids[-keep_previous:]:
                protected_set.add(gid)
    elif keep_previous > 0 and sorted_published_ids:
        for gid in sorted_published_ids[-keep_previous:]:
            protected_set.add(gid)

    if grace_seconds > 0:
        for gid, pub_at in published_map.items():
            if (current_time - pub_at) < grace_seconds:
                protected_set.add(gid)

    # 3. Process directories on disk
    for child in gen_root.iterdir():
        if not child.is_dir():
            continue

        gid = child.name

        if gid in protected_set:
            result["preserved"].append(gid)
            continue

        is_published = gid in published_map
        if is_published:
            try:
                shutil.rmtree(child, ignore_errors=False)
                result["deleted"].append(gid)
            except Exception as e:
                result["errors"].append(f"Failed deleting published gen {gid}: {e}")
                result["preserved"].append(gid)
        else:
            if clean_orphans:
                try:
                    mtime = child.stat().st_mtime
                    if (current_time - mtime) >= orphan_grace_seconds:
                        shutil.rmtree(child, ignore_errors=False)
                        result["orphans_deleted"].append(gid)
                    else:
                        result["preserved"].append(gid)
                except Exception as e:
                    result["errors"].append(f"Failed deleting orphan gen {gid}: {e}")
                    result["preserved"].append(gid)
            else:
                result["preserved"].append(gid)

    return result


@dataclass
class PlannedCopy:
    source_path: Path
    staging_dest: Path
    candidate_filename: str
    asset_id: str
    final_rel_url: str


def materialize_project_atomic(
    project_dir_or_path: Path,
    workspace_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Executes a fully transactional materialization for a project with single-point atomic commit.
    
    Architecture:
    1. Preflight: Zero side-effects. Validates identity, manifest, blueprint, paths, templates.
    2. Generation Staging: Builds immutable directory at
       remotion-app/public/projects/<project_id>/generations/<gen_id>/
    3. Pointer Staging: Writes candidate map to <project_dir>/.media_map_<gen_id>.tmp
    4. Verification & Fsync: Confirms all files exist and are flushed to physical media.
    5. Single Atomic Commit: os.replace(staged_map, final_media_map).
       This single atomic syscall switches reader visibility instantaneously from Old to New.
    6. Decoupled Post-Commit Cleanup: Removes inactive generations.
    """
    proj = Path(project_dir_or_path).resolve()
    ws = Path(workspace_root or Path.cwd()).resolve()
    plugin_dir = ws / ".agents" / "plugins" / "super-video-maker-plugin"
    project_id = validate_project_id(proj.name)

    # ─── PHASE 1: PREFLIGHT VALIDATION (Zero Side Effects) ───
    validate_project_identity(proj, expected_project_id=project_id)
    man = load_manifest(proj / "02_asset_manifest.json", expected_project_id=project_id, allow_migrate=True)

    has_plan = (proj / "master_plan.md").exists() or (proj / "01_plan.md").exists()
    if not (proj / "05_blueprint.json").exists() or not has_plan:
        raise MaterializationPreflightError(["Missing required master_plan.md/01_plan.md or 05_blueprint.json"])

    bp_v2 = load_blueprint(proj / "05_blueprint.json", expected_project_id=project_id, manifest=man, allow_migrate=True)
    bp = bp_v2.to_dict()

    pub_project = ws / "remotion-app" / "public" / "projects" / project_id
    gen_id = f"gen_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    gen_dir = pub_project / "generations" / gen_id

    fails: List[str] = []
    planned_copies: List[PlannedCopy] = []
    media_map: Dict[str, str] = {}
    used_templates: Set[str] = set()

    def canon(p: Union[str, Path]) -> Path:
        path_obj = Path(p)
        return path_obj if path_obj.is_absolute() else (ws / path_obj)

    # Pre-validate all assets in manifest
    for a in man.assets:
        aid = a.asset_id
        try:
            validate_asset_id(aid)
        except ValueError as e:
            fails.append(f"asset '{aid}': {e}")
            continue

        if aid in media_map:
            fails.append(f"duplicate asset_id '{aid}'")
            continue

        raw_path = a.processed_path or a.source_path or ""
        if not raw_path:
            fails.append(f"asset '{aid}': missing path")
            continue

        src = canon(raw_path)
        try:
            real_src = validate_source_asset(src, allowed_roots=[ws], forbidden_roots=[plugin_dir])
        except (PathSecurityViolation, FileNotFoundError, OSError) as e:
            fails.append(f"asset '{aid}': {e}")
            continue

        candidate_filename = f"{aid}{src.suffix}"
        staging_dest = gen_dir / candidate_filename

        try:
            staging_resolved = staging_dest.resolve()
            gen_dir_resolved = gen_dir.resolve()
            staging_resolved.relative_to(gen_dir_resolved)
        except Exception:
            fails.append(f"asset '{aid}': destination escape detected: {candidate_filename}")
            continue

        final_rel_url = f"projects/{project_id}/generations/{gen_id}/{candidate_filename}"
        media_map[aid] = final_rel_url
        planned_copies.append(
            PlannedCopy(
                source_path=real_src,
                staging_dest=staging_dest,
                candidate_filename=candidate_filename,
                asset_id=aid,
                final_rel_url=final_rel_url,
            )
        )

    # Validate blueprint scenes and template identity via authoritative contract (S15)
    from scripts.core.template_contract import get_template_contract
    template_contract = get_template_contract()

    for sec in bp.get("scenes", []):
        name = sec.get("template")
        if name:
            entry = template_contract.resolve(name)
            if entry is None or not entry.runtime_available:
                fails.append(f"template '{name}' is not registered or unavailable [UNKNOWN_TEMPLATE_ID]")
            else:
                used_templates.add(entry.canonical_id)

    # Authoritative preflight reference verification via collect_asset_references (ASSET-005)
    from scripts.core.asset_resolution import collect_asset_references, MalformedAssetRefError
    try:
        blueprint_occurrences = collect_asset_references(bp)
    except MalformedAssetRefError as e:
        fails.append(str(e))
        blueprint_occurrences = []

    for occ in blueprint_occurrences:
        if occ.is_logical and occ.asset_id:
            aid = occ.asset_id
            if aid not in media_map:
                if "sfx" in occ.slot:
                    fails.append(f"Scene references unmaterialized SFX: '{aid}'")
                else:
                    fails.append(f"Scene references unmaterialized asset: '{aid}'")

    if fails:
        raise MaterializationPreflightError(fails)

    # ─── PHASE 2: GENERATION STAGING ───
    pub_project.mkdir(parents=True, exist_ok=True)
    gen_dir.mkdir(parents=True, exist_ok=True)
    staged_map_path = proj / f".media_map_{gen_id}.tmp"

    try:
        for plan in planned_copies:
            shutil.copy2(str(plan.source_path), str(plan.staging_dest))
            _fsync_file(plan.staging_dest)

        # Write staged pointer map to project directory
        with open(staged_map_path, "w", encoding="utf-8") as f:
            json.dump(media_map, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())

        # ─── PHASE 3: VERIFY STAGED GENERATION ───
        for plan in planned_copies:
            if not plan.staging_dest.exists():
                raise MaterializationVerificationError(f"Staged file missing: {plan.staging_dest}")
            if plan.staging_dest.stat().st_size == 0 and plan.source_path.stat().st_size > 0:
                raise MaterializationVerificationError(f"Staged file truncated: {plan.staging_dest}")

        if not staged_map_path.exists():
            raise MaterializationVerificationError("Staged .media_map_<gen_id>.tmp missing")

        # Fsync directories
        _fsync_dir(gen_dir)
        _fsync_dir(gen_dir.parent)
        _fsync_dir(proj)

    except Exception as e:
        # ABORT & ISOLATE: Clean up uncommitted generation immediately.
        # Existing published generation and media_map.json are 100% untouched!
        shutil.rmtree(gen_dir, ignore_errors=True)
        staged_map_path.unlink(missing_ok=True)
        raise MaterializationStagingError(f"Failed during staging pass: {e}") from e

    # ─── PHASE 4: THE SINGLE ATOMIC COMMIT MOMENT ───
    # Exactly one atomic file replacement.
    # Before this call: readers see OLD COMPLETE GENERATION via media_map.json.
    # After this call: readers see NEW COMPLETE GENERATION via media_map.json.
    final_map_path = proj / "media_map.json"
    old_active_gen_id = get_active_generation_id(proj)

    try:
        os.replace(str(staged_map_path), str(final_map_path))
        _fsync_dir(proj)
    except Exception as commit_err:
        shutil.rmtree(gen_dir, ignore_errors=True)
        staged_map_path.unlink(missing_ok=True)
        raise MaterializationError(f"Critical commit failure replacing media_map: {commit_err}") from commit_err

    # Record newly published generation in history (and preserve previous active)
    now_ts = time.time()
    try:
        if old_active_gen_id and old_active_gen_id != gen_id:
            record_generation_published(pub_project, old_active_gen_id, project_dir=proj, published_at=now_ts - 1.0)
        record_generation_published(pub_project, gen_id, project_dir=proj, published_at=now_ts)
    except Exception:
        pass

    # ─── PHASE 5: POST-COMMIT CLEANUP (Decoupled from Commit) ───
    # Failure in cleanup MUST NEVER invalidate or revert the successful commit.
    try:
        cleanup_inactive_generations(
            pub_project,
            active_gen_id=gen_id,
            project_dir=proj,
            keep_previous=1,
            grace_seconds=300.0,
            clean_orphans=True,
        )
    except Exception:
        pass

    return {
        "project_id": project_id,
        "generation_id": gen_id,
        "media_map": media_map,
        "assets_count": len(media_map),
        "templates_count": len(used_templates),
        "used_templates": sorted(list(used_templates)),
    }
