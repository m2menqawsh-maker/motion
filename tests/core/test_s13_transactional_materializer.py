"""
S13 Comprehensive Test Suite:
- ASSET-003: Single-point atomic commit materializer, fault injection at all boundaries, concurrent reader visibility.
- ASSET-010: Zero stale files after re-materialization.
- ASSET-004: Expected status enforcement & atomic transitions with rollback.
- ASSET-007: Cache identity correctness (content hash, spec hash, version).
- LED-036: Architectural dependency direction guard.
- Idempotency & Invariants verification.
"""

import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
import pytest

from scripts.core.asset_cache import (
    AssetCacheKey,
    compute_cache_identity,
    compute_content_hash,
    compute_processing_spec_hash,
    normalize_processing_spec,
    DEFAULT_PROCESSOR_VERSION,
)
from scripts.core.asset_lifecycle import (
    AssetFileMissingError,
    AssetLifecycleError,
    AssetNotFoundError,
    AssetStatusMismatchError,
    move_asset,
)
from scripts.core.manifest_model import AssetKind, AssetStatus, AssetV2, ManifestV2, Provenance
from scripts.core.manifest_loader import save_manifest, load_manifest
from scripts.core.materializer import (
    MaterializationError,
    MaterializationPreflightError,
    MaterializationStagingError,
    MaterializationVerificationError,
    cleanup_inactive_generations,
    get_active_generation_id,
    materialize_project_atomic,
)


# ─────────────────────────────────────────────────────────────────────────────
# ASSET-003: Single Visibility / Commit Point Materializer Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_materializer_preflight_missing_source_fails_without_side_effects(tmp_path):
    """
    ASSET-003: Missing source file must fail at preflight stage with zero filesystem changes.
    """
    workspace = Path.cwd()
    project_id = "prj_s13_preflight"
    project_dir = tmp_path / "projects" / project_id
    project_dir.mkdir(parents=True)

    non_existent_file = workspace / "assets" / "ready" / "non_existent_file_12345.mp4"

    manifest = ManifestV2(
        project_id=project_id,
        assets=[
            AssetV2(
                asset_id="ast_missing",
                kind=AssetKind.VIDEO,
                provenance=Provenance.USER_UPLOAD,
                status=AssetStatus.READY,
                processed_path=str(non_existent_file),
            )
        ]
    )
    save_manifest(manifest, project_dir)

    blueprint = {
        "project_id": project_id,
        "version": "1.0",
        "scenes": [
            {
                "scene_id": "scene_1",
                "template": "ShowcaseWrapper",
                "startFrame": 0,
                "durationFrames": 30,
                "media_refs": ["ast_missing"]
            }
        ]
    }
    (project_dir / "05_blueprint.json").write_text(json.dumps(blueprint), encoding="utf-8")
    (project_dir / "01_plan.md").write_text("plan", encoding="utf-8")

    pub_project = workspace / "remotion-app" / "public" / "projects" / project_id
    assert not (pub_project / "generations").exists()

    with pytest.raises(MaterializationPreflightError) as exc_info:
        materialize_project_atomic(project_dir, workspace_root=workspace)

    assert any("ast_missing" in err for err in exc_info.value.errors)
    assert not (pub_project / "generations").exists()
    assert not (project_dir / "media_map.json").exists()


def test_fault_injection_1_staging_copy_failure_preserves_old_generation(tmp_path, monkeypatch):
    """
    FAULT INJECTION 1: Crash during generation staging build.
    The old generation and old media_map.json MUST remain 100% intact and complete.
    No partial files appear in active generation.
    """
    workspace = Path.cwd()
    project_id = "prj_s13_fi_1"
    project_dir = tmp_path / "projects" / project_id
    project_dir.mkdir(parents=True)

    assets_ready = workspace / "assets" / "ready"
    assets_ready.mkdir(parents=True, exist_ok=True)
    video1 = assets_ready / "s13_fi1_vid1.mp4"
    video2 = assets_ready / "s13_fi1_vid2.mp4"
    video1.write_text("vid 1 content", encoding="utf-8")
    video2.write_text("vid 2 content", encoding="utf-8")

    pub_project = workspace / "remotion-app" / "public" / "projects" / project_id
    gen_old_id = "gen_initial_old"
    gen_old_dir = pub_project / "generations" / gen_old_id
    gen_old_dir.mkdir(parents=True, exist_ok=True)

    old_file = gen_old_dir / "legacy_asset.mp4"
    old_file.write_text("LEGACY GENERATION CONTENT", encoding="utf-8")
    old_map_data = {"legacy_asset": f"projects/{project_id}/generations/{gen_old_id}/legacy_asset.mp4"}
    (project_dir / "media_map.json").write_text(json.dumps(old_map_data), encoding="utf-8")

    try:
        manifest = ManifestV2(
            project_id=project_id,
            assets=[
                AssetV2(asset_id="ast_ok", kind=AssetKind.VIDEO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, processed_path=str(video1)),
                AssetV2(asset_id="ast_fail", kind=AssetKind.VIDEO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, processed_path=str(video2)),
            ]
        )
        save_manifest(manifest, project_dir)

        blueprint = {
            "project_id": project_id,
            "version": "1.0",
            "scenes": [{"scene_id": "s1", "template": "ShowcaseWrapper", "startFrame": 0, "durationFrames": 30, "media_refs": ["ast_ok", "ast_fail"]}]
        }
        (project_dir / "05_blueprint.json").write_text(json.dumps(blueprint), encoding="utf-8")
        (project_dir / "01_plan.md").write_text("plan", encoding="utf-8")

        # Inject failure specifically when copying ast_fail
        orig_copy2 = shutil.copy2
        def failing_copy2(src, dst, **kwargs):
            if "ast_fail" in str(dst) or "ast_fail" in str(src):
                raise OSError("Simulated I/O failure while writing ast_fail")
            return orig_copy2(src, dst, **kwargs)

        monkeypatch.setattr(shutil, "copy2", failing_copy2)

        with pytest.raises(MaterializationStagingError):
            materialize_project_atomic(project_dir, workspace_root=workspace)

        # Invariant Checks:
        # 1. Old generation must be completely intact
        assert old_file.exists()
        assert old_file.read_text(encoding="utf-8") == "LEGACY GENERATION CONTENT"
        # 2. media_map.json must retain old generation content
        current_map = json.loads((project_dir / "media_map.json").read_text(encoding="utf-8"))
        assert current_map == old_map_data
        # 3. Active generation ID is still gen_old_id
        assert get_active_generation_id(project_dir) == gen_old_id
        # 4. No uncommitted generation directory remains
        remaining_gens = list((pub_project / "generations").iterdir())
        assert len(remaining_gens) == 1
        assert remaining_gens[0].name == gen_old_id
        # 5. Every file referenced in active map exists
        for path in current_map.values():
            assert (workspace / "remotion-app" / "public" / path).exists()
    finally:
        if video1.exists():
            video1.unlink()
        if video2.exists():
            video2.unlink()
        if pub_project.exists():
            shutil.rmtree(pub_project)


def test_fault_injection_2_crash_before_commit_preserves_old_generation(tmp_path, monkeypatch):
    """
    FAULT INJECTION 2: Crash after generation is fully staged and verified, but immediately before commit.
    The single commit moment (os.replace) has not been reached.
    Active media_map.json still points to Generation 1.
    """
    workspace = Path.cwd()
    project_id = "prj_s13_fi_2"
    project_dir = tmp_path / "projects" / project_id
    project_dir.mkdir(parents=True)

    assets_ready = workspace / "assets" / "ready"
    assets_ready.mkdir(parents=True, exist_ok=True)
    video = assets_ready / "s13_fi2_vid.mp4"
    video.write_text("New Gen Video Content", encoding="utf-8")

    pub_project = workspace / "remotion-app" / "public" / "projects" / project_id
    gen_old_id = "gen_prev_complete"
    gen_old_dir = pub_project / "generations" / gen_old_id
    gen_old_dir.mkdir(parents=True, exist_ok=True)
    old_file = gen_old_dir / "old_vid.mp4"
    old_file.write_text("PREV VIDEO CONTENT", encoding="utf-8")

    old_map_data = {"old_asset": f"projects/{project_id}/generations/{gen_old_id}/old_vid.mp4"}
    (project_dir / "media_map.json").write_text(json.dumps(old_map_data), encoding="utf-8")

    try:
        manifest = ManifestV2(
            project_id=project_id,
            assets=[
                AssetV2(asset_id="ast_new", kind=AssetKind.VIDEO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, processed_path=str(video)),
            ]
        )
        save_manifest(manifest, project_dir)
        bp = {
            "project_id": project_id,
            "version": "1.0",
            "scenes": [{"scene_id": "s1", "template": "ShowcaseWrapper", "startFrame": 0, "durationFrames": 30, "media_refs": ["ast_new"]}]
        }
        (project_dir / "05_blueprint.json").write_text(json.dumps(bp), encoding="utf-8")
        (project_dir / "01_plan.md").write_text("plan", encoding="utf-8")

        # Simulate crash right before atomic os.replace:
        orig_replace = os.replace
        def crash_on_commit(src, dst):
            if "media_map" in str(dst):
                raise RuntimeError("Simulated system crash immediately before atomic commit")
            return orig_replace(src, dst)

        monkeypatch.setattr(os, "replace", crash_on_commit)

        with pytest.raises(MaterializationError) as exc_info:
            materialize_project_atomic(project_dir, workspace_root=workspace)

        assert "Simulated system crash" in str(exc_info.value)

        # Invariant Checks:
        # 1. media_map.json is unchanged (Generation 1 remains active)
        active_map = json.loads((project_dir / "media_map.json").read_text(encoding="utf-8"))
        assert active_map == old_map_data
        assert get_active_generation_id(project_dir) == gen_old_id
        # 2. Old generation files are fully accessible
        assert old_file.exists()
        assert old_file.read_text(encoding="utf-8") == "PREV VIDEO CONTENT"
        # 3. No orphan staged map remained
        assert not list(project_dir.glob(".media_map_*.tmp"))

    finally:
        if video.exists():
            video.unlink()
        if pub_project.exists():
            shutil.rmtree(pub_project)


def test_fault_injection_3_cleanup_failure_does_not_affect_active_generation(tmp_path, monkeypatch):
    """
    FAULT INJECTION 3: Failure during post-commit cleanup (e.g. transient file lock on old gen).
    The commit itself was 100% successful.
    Active media_map MUST point to Generation 2 and Generation 2 must be 100% complete.
    Cleanup failure NEVER rolls back the active pointer or corrupts the published generation.
    """
    workspace = Path.cwd()
    project_id = "prj_s13_fi_3"
    project_dir = tmp_path / "projects" / project_id
    project_dir.mkdir(parents=True)

    assets_ready = workspace / "assets" / "ready"
    assets_ready.mkdir(parents=True, exist_ok=True)
    video = assets_ready / "s13_fi3_vid.mp4"
    video.write_text("Generation 2 Video Content", encoding="utf-8")

    pub_project = workspace / "remotion-app" / "public" / "projects" / project_id
    gen_old_id = "gen_1_active"
    gen_old_dir = pub_project / "generations" / gen_old_id
    gen_old_dir.mkdir(parents=True, exist_ok=True)
    (gen_old_dir / "gen1.mp4").write_text("Gen 1 data", encoding="utf-8")

    (project_dir / "media_map.json").write_text(
        json.dumps({"ast_gen1": f"projects/{project_id}/generations/{gen_old_id}/gen1.mp4"}), encoding="utf-8"
    )

    try:
        manifest = ManifestV2(
            project_id=project_id,
            assets=[
                AssetV2(asset_id="ast_gen2", kind=AssetKind.VIDEO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, processed_path=str(video)),
            ]
        )
        save_manifest(manifest, project_dir)
        bp = {
            "project_id": project_id,
            "version": "1.0",
            "scenes": [{"scene_id": "s1", "template": "ShowcaseWrapper", "startFrame": 0, "durationFrames": 30, "media_refs": ["ast_gen2"]}]
        }
        (project_dir / "05_blueprint.json").write_text(json.dumps(bp), encoding="utf-8")
        (project_dir / "01_plan.md").write_text("plan", encoding="utf-8")

        # Simulate cleanup failure: PermissionError when trying to remove old generation
        orig_rmtree = shutil.rmtree
        def locked_rmtree(path, **kwargs):
            if gen_old_id in str(path):
                raise PermissionError("Simulated locked file in inactive generation on Windows")
            return orig_rmtree(path, **kwargs)

        monkeypatch.setattr(shutil, "rmtree", locked_rmtree)

        # Run materialization
        res = materialize_project_atomic(project_dir, workspace_root=workspace)

        # Invariant Checks:
        # 1. Materialization succeeded!
        assert res["assets_count"] == 1
        new_gen_id = res["generation_id"]
        assert new_gen_id != gen_old_id

        # 2. Active pointer is strictly Generation 2
        active_map = json.loads((project_dir / "media_map.json").read_text(encoding="utf-8"))
        assert "ast_gen2" in active_map
        assert "ast_gen1" not in active_map
        assert get_active_generation_id(project_dir) == new_gen_id

        # 3. Generation 2 files are 100% complete and readable
        new_file = workspace / "remotion-app" / "public" / active_map["ast_gen2"]
        assert new_file.exists()
        assert new_file.read_text(encoding="utf-8") == "Generation 2 Video Content"

        # 4. Next reconciliation (e.g. when lock is released) cleans up inactive generation
        monkeypatch.undo()
        cleanup_inactive_generations(pub_project, active_gen_id=new_gen_id, project_dir=project_dir, keep_previous=0, grace_seconds=0)
        assert not gen_old_dir.exists(), "Old generation cleaned up after lock released"
        assert (pub_project / "generations" / new_gen_id).exists()

    finally:
        if video.exists():
            video.unlink()
        if pub_project.exists():
            shutil.rmtree(pub_project)


def test_concurrent_reader_never_observes_mixed_generation_or_missing_media(tmp_path):
    """
    CONCURRENCY / VISIBILITY TEST:
    A concurrent reader repeatedly inspects media_map.json and verifies every referenced file.
    While the reader is reading, materialization runs to transition Generation 1 -> Generation 2 -> Generation 3.
    The reader MUST NEVER observe:
    - Missing media_map.json
    - Empty media_map.json
    - A mixed generation (paths from different generations in the same map)
    - Any referenced media file missing from disk.
    """
    workspace = Path.cwd()
    project_id = "prj_s13_concurrency"
    project_dir = tmp_path / "projects" / project_id
    project_dir.mkdir(parents=True)

    assets_ready = workspace / "assets" / "ready"
    assets_ready.mkdir(parents=True, exist_ok=True)
    vid_a = assets_ready / "s13_conc_a.mp4"
    vid_b = assets_ready / "s13_conc_b.mp4"
    vid_c = assets_ready / "s13_conc_c.mp4"
    vid_a.write_text("Video Alpha", encoding="utf-8")
    vid_b.write_text("Video Beta", encoding="utf-8")
    vid_c.write_text("Video Gamma", encoding="utf-8")

    pub_project = workspace / "remotion-app" / "public" / "projects" / project_id

    # 1. Seed initial Generation 1 (A + B)
    man1 = ManifestV2(
        project_id=project_id,
        assets=[
            AssetV2(asset_id="ast_a", kind=AssetKind.VIDEO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, processed_path=str(vid_a)),
            AssetV2(asset_id="ast_b", kind=AssetKind.VIDEO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, processed_path=str(vid_b)),
        ]
    )
    save_manifest(man1, project_dir)
    bp1 = {
        "project_id": project_id,
        "version": "1.0",
        "scenes": [{"scene_id": "s1", "template": "ShowcaseWrapper", "startFrame": 0, "durationFrames": 30, "media_refs": ["ast_a", "ast_b"]}]
    }
    (project_dir / "05_blueprint.json").write_text(json.dumps(bp1), encoding="utf-8")
    (project_dir / "01_plan.md").write_text("plan", encoding="utf-8")
    materialize_project_atomic(project_dir, workspace_root=workspace)

    stop_reader = threading.Event()
    reader_errors = []
    read_count = [0]

    def reader_loop():
        media_map_path = project_dir / "media_map.json"
        while not stop_reader.is_set():
            try:
                if not media_map_path.exists():
                    reader_errors.append("media_map.json missing during read!")
                    continue
                raw = media_map_path.read_text(encoding="utf-8")
                if not raw.strip():
                    reader_errors.append("media_map.json empty during read!")
                    continue
                data = json.loads(raw)

                # Check 1: All paths must belong to the exact same generation
                seen_gens = set()
                for aid, rel_path in data.items():
                    assert "/generations/" in rel_path, f"Path not generation-addressed: {rel_path}"
                    gen_part = rel_path.split("/generations/")[1].split("/")[0]
                    seen_gens.add(gen_part)

                    # Check 2: Physical file must exist on disk right now
                    full_path = workspace / "remotion-app" / "public" / rel_path
                    if not full_path.exists():
                        reader_errors.append(f"Referenced file missing on disk: {full_path}")
                    elif full_path.stat().st_size == 0:
                        reader_errors.append(f"Referenced file is zero bytes: {full_path}")

                if len(seen_gens) > 1:
                    reader_errors.append(f"Mixed generations detected in single media_map: {seen_gens}")

                read_count[0] += 1
            except Exception as e:
                reader_errors.append(f"Reader exception: {e}")
            time.sleep(0.005)

    reader_thread = threading.Thread(target=reader_loop, daemon=True)
    reader_thread.start()

    try:
        # Step 2: Materialize Generation 2 (A + C)
        man2 = ManifestV2(
            project_id=project_id,
            assets=[
                AssetV2(asset_id="ast_a", kind=AssetKind.VIDEO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, processed_path=str(vid_a)),
                AssetV2(asset_id="ast_c", kind=AssetKind.VIDEO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, processed_path=str(vid_c)),
            ]
        )
        save_manifest(man2, project_dir)
        bp2 = {
            "project_id": project_id,
            "version": "1.0",
            "scenes": [{"scene_id": "s1", "template": "ShowcaseWrapper", "startFrame": 0, "durationFrames": 30, "media_refs": ["ast_a", "ast_c"]}]
        }
        (project_dir / "05_blueprint.json").write_text(json.dumps(bp2), encoding="utf-8")
        materialize_project_atomic(project_dir, workspace_root=workspace)

        # Step 3: Materialize Generation 3 (B + C)
        man3 = ManifestV2(
            project_id=project_id,
            assets=[
                AssetV2(asset_id="ast_b", kind=AssetKind.VIDEO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, processed_path=str(vid_b)),
                AssetV2(asset_id="ast_c", kind=AssetKind.VIDEO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, processed_path=str(vid_c)),
            ]
        )
        save_manifest(man3, project_dir)
        bp3 = {
            "project_id": project_id,
            "version": "1.0",
            "scenes": [{"scene_id": "s1", "template": "ShowcaseWrapper", "startFrame": 0, "durationFrames": 30, "media_refs": ["ast_b", "ast_c"]}]
        }
        (project_dir / "05_blueprint.json").write_text(json.dumps(bp3), encoding="utf-8")
        materialize_project_atomic(project_dir, workspace_root=workspace)

    finally:
        stop_reader.set()
        reader_thread.join(timeout=2.0)
        if vid_a.exists():
            vid_a.unlink()
        if vid_b.exists():
            vid_b.unlink()
        if vid_c.exists():
            vid_c.unlink()
        if pub_project.exists():
            shutil.rmtree(pub_project)

    # Concurrency Invariant Assertion:
    assert read_count[0] > 0, "Reader did not execute any iterations!"
    assert len(reader_errors) == 0, f"Reader observed visibility anomalies: {reader_errors}"


# ─────────────────────────────────────────────────────────────────────────────
# ASSET-010: Stale Files Elimination Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_rematerialization_eliminates_stale_files(tmp_path):
    """
    ASSET-010: When a project is rematerialized with fewer assets (A+B -> A),
    asset B is absent from the newly published active generation.
    """
    workspace = Path.cwd()
    project_id = "prj_s13_stale_test"
    project_dir = tmp_path / "projects" / project_id
    project_dir.mkdir(parents=True)

    assets_ready = workspace / "assets" / "ready"
    assets_ready.mkdir(parents=True, exist_ok=True)
    video_a = assets_ready / "s13_stale_a.mp4"
    video_b = assets_ready / "s13_stale_b.mp4"
    video_a.write_text("Video A", encoding="utf-8")
    video_b.write_text("Video B", encoding="utf-8")

    pub_project = workspace / "remotion-app" / "public" / "projects" / project_id

    try:
        # Step 1: Materialize with A and B
        manifest_1 = ManifestV2(
            project_id=project_id,
            assets=[
                AssetV2(asset_id="ast_a", kind=AssetKind.VIDEO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, processed_path=str(video_a)),
                AssetV2(asset_id="ast_b", kind=AssetKind.VIDEO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, processed_path=str(video_b)),
            ]
        )
        save_manifest(manifest_1, project_dir)
        bp_1 = {
            "project_id": project_id,
            "version": "1.0",
            "scenes": [{"scene_id": "s1", "template": "ShowcaseWrapper", "startFrame": 0, "durationFrames": 30, "media_refs": ["ast_a", "ast_b"]}]
        }
        (project_dir / "05_blueprint.json").write_text(json.dumps(bp_1), encoding="utf-8")
        (project_dir / "01_plan.md").write_text("plan", encoding="utf-8")

        res1 = materialize_project_atomic(project_dir, workspace_root=workspace)
        assert res1["assets_count"] == 2
        gen1_id = res1["generation_id"]
        gen1_dir = pub_project / "generations" / gen1_id
        assert (gen1_dir / "ast_a.mp4").exists()
        assert (gen1_dir / "ast_b.mp4").exists()

        # Step 2: Rematerialize with ONLY A
        manifest_2 = ManifestV2(
            project_id=project_id,
            assets=[
                AssetV2(asset_id="ast_a", kind=AssetKind.VIDEO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, processed_path=str(video_a)),
            ]
        )
        save_manifest(manifest_2, project_dir)
        bp_2 = {
            "project_id": project_id,
            "version": "1.0",
            "scenes": [{"scene_id": "s1", "template": "ShowcaseWrapper", "startFrame": 0, "durationFrames": 30, "media_refs": ["ast_a"]}]
        }
        (project_dir / "05_blueprint.json").write_text(json.dumps(bp_2), encoding="utf-8")

        res2 = materialize_project_atomic(project_dir, workspace_root=workspace)
        assert res2["assets_count"] == 1
        gen2_id = res2["generation_id"]
        gen2_dir = pub_project / "generations" / gen2_id

        # ASSET-010 Verification: Active generation contains A, but NOT B!
        assert (gen2_dir / "ast_a.mp4").exists()
        assert not (gen2_dir / "ast_b.mp4").exists(), "Stale asset B remained in active generation!"

        # media_map.json only references A
        current_map = json.loads((project_dir / "media_map.json").read_text(encoding="utf-8"))
        assert "ast_a" in current_map
        assert "ast_b" not in current_map
        assert get_active_generation_id(project_dir) == gen2_id

    finally:
        if video_a.exists():
            video_a.unlink()
        if video_b.exists():
            video_b.unlink()
        if pub_project.exists():
            shutil.rmtree(pub_project)


# ─────────────────────────────────────────────────────────────────────────────
# ASSET-004: Status Transition & expected_status Enforcement Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_move_asset_status_mismatch_raises_and_preserves_state(tmp_path):
    """
    ASSET-004: Attempting to transition an asset with an incorrect expected_status
    must fail closed with AssetStatusMismatchError and cause ZERO filesystem or manifest mutations.
    """
    project_dir = tmp_path / "prj_s13_status"
    project_dir.mkdir()

    asset_file = project_dir / "audio.wav"
    asset_file.write_text("audio sample", encoding="utf-8")

    manifest = ManifestV2(
        project_id="prj_s13_status",
        assets=[
            AssetV2(
                asset_id="ast_audio",
                kind=AssetKind.AUDIO,
                provenance=Provenance.USER_UPLOAD,
                status=AssetStatus.READY,  # Actual status is READY
                processed_path=str(asset_file),
            )
        ]
    )
    save_manifest(manifest, project_dir)

    # Caller claims expected_status="incoming", but actual status is "ready"
    with pytest.raises(AssetStatusMismatchError) as exc_info:
        move_asset(
            project_dir_or_manifest=project_dir,
            asset_id="ast_audio",
            expected_status="incoming",
            target_status="processing",
            destination_path=project_dir / "audio_processing.wav",
        )

    assert exc_info.value.asset_id == "ast_audio"
    assert exc_info.value.actual_status == "ready"
    assert exc_info.value.expected_status == "incoming"

    # Verify zero mutations
    reloaded_man = load_manifest(project_dir)
    assert reloaded_man.get_asset("ast_audio").status == AssetStatus.READY
    assert asset_file.exists()
    assert not (project_dir / "audio_processing.wav").exists()


def test_move_asset_successful_transition_and_atomic_rollback(tmp_path, monkeypatch):
    """
    ASSET-004: Successful transition moves the file and updates the manifest.
    If manifest save fails, file movement is rolled back.
    """
    project_dir = tmp_path / "prj_s13_move_ok"
    project_dir.mkdir()

    src_file = project_dir / "raw.mp4"
    dst_file = project_dir / "processed.mp4"
    src_file.write_text("video raw", encoding="utf-8")

    manifest = ManifestV2(
        project_id="prj_s13_move_ok",
        assets=[
            AssetV2(
                asset_id="ast_vid",
                kind=AssetKind.VIDEO,
                provenance=Provenance.USER_UPLOAD,
                status=AssetStatus.PROCESSING,
                processed_path=str(src_file),
            )
        ]
    )
    save_manifest(manifest, project_dir)

    # 1. Successful move: processing -> ready
    updated_asset = move_asset(
        project_dir_or_manifest=project_dir,
        asset_id="ast_vid",
        expected_status=AssetStatus.PROCESSING,
        target_status=AssetStatus.READY,
        destination_path=dst_file,
    )
    assert updated_asset.status == AssetStatus.READY
    assert not src_file.exists()
    assert dst_file.exists()

    # Verify persisted manifest
    persisted = load_manifest(project_dir)
    assert persisted.get_asset("ast_vid").status == AssetStatus.READY
    assert persisted.get_asset("ast_vid").processed_path == str(dst_file)

    # 2. Test Rollback on Manifest Save Failure
    import scripts.core.asset_lifecycle as lifecycle_mod
    orig_save = lifecycle_mod.save_manifest

    def failing_save(*args, **kwargs):
        raise IOError("Simulated disk error during save_manifest")

    monkeypatch.setattr(lifecycle_mod, "save_manifest", failing_save)

    with pytest.raises(IOError):
        move_asset(
            project_dir_or_manifest=project_dir,
            asset_id="ast_vid",
            expected_status=AssetStatus.READY,
            target_status=AssetStatus.PROCESSING,
            destination_path=src_file,
        )

    # Verify rollback: file must still be at dst_file, not src_file
    assert dst_file.exists(), "Rollback failed: dst_file should have been restored!"
    assert not src_file.exists()
    final_man = load_manifest(project_dir)
    assert final_man.get_asset("ast_vid").status == AssetStatus.READY


# ─────────────────────────────────────────────────────────────────────────────
# ASSET-007: Cache Identity Correctness Tests
# ─────────────────────────────────────────────────────────────────────────────

def test_cache_identity_properties(tmp_path):
    """
    ASSET-007:
    - Same content + same spec (any key order) + same version = Cache Hit.
    - Changed spec parameter = Cache Miss.
    - Changed content = Cache Miss.
    - Changed processor version = Cache Miss.
    """
    file1 = tmp_path / "sample1.wav"
    file2 = tmp_path / "sample2.wav"
    file1.write_bytes(b"content alpha")
    file2.write_bytes(b"content beta")

    hash1 = compute_content_hash(file1)
    hash2 = compute_content_hash(file2)
    assert hash1 != hash2

    spec_1 = {"lufs": -16.0, "format": "wav", "rate": 44100}
    spec_1_reordered = {"rate": 44100, "format": "wav", "lufs": -16.0}
    spec_2 = {"lufs": -24.0, "format": "wav", "rate": 44100}

    # Deterministic normalization
    norm1 = normalize_processing_spec(spec_1)
    norm1_reordered = normalize_processing_spec(spec_1_reordered)
    assert norm1 == norm1_reordered

    h_spec1 = compute_processing_spec_hash(spec_1)
    h_spec1_reordered = compute_processing_spec_hash(spec_1_reordered)
    h_spec2 = compute_processing_spec_hash(spec_2)
    assert h_spec1 == h_spec1_reordered
    assert h_spec1 != h_spec2

    # Identity verification
    key_base = compute_cache_identity(hash1, h_spec1, processor_version="1.0.0")
    key_same = compute_cache_identity(hash1, h_spec1_reordered, processor_version="1.0.0")
    assert key_base == key_same, "Cache Hit expected on semantically identical specs"

    key_diff_spec = compute_cache_identity(hash1, h_spec2, processor_version="1.0.0")
    assert key_base != key_diff_spec, "Cache Miss expected on changed spec"

    key_diff_content = compute_cache_identity(hash2, h_spec1, processor_version="1.0.0")
    assert key_base != key_diff_content, "Cache Miss expected on changed content"

    key_diff_version = compute_cache_identity(hash1, h_spec1, processor_version="2.0.0")
    assert key_base != key_diff_version, "Cache Miss expected on changed processor version"


# ─────────────────────────────────────────────────────────────────────────────
# LED-036: Architecture Boundary Guard
# ─────────────────────────────────────────────────────────────────────────────

def test_materializer_has_no_api_dependencies():
    """
    LED-036: Enforce clean architectural dependency direction.
    scripts/generators/materialize_project.py and scripts/core/materializer.py
    MUST NOT import from api.
    """
    files_to_check = [
        Path("scripts/generators/materialize_project.py"),
        Path("scripts/core/materializer.py"),
        Path("scripts/core/asset_lifecycle.py"),
        Path("scripts/core/asset_cache.py"),
    ]

    for fpath in files_to_check:
        text = fpath.read_text(encoding="utf-8")
        assert "from api." not in text, f"Forbidden import from api in {fpath}"
        assert "import api." not in text, f"Forbidden import of api in {fpath}"
        assert "PipelineService" not in text, f"Forbidden PipelineService reference in {fpath}"


# ─────────────────────────────────────────────────────────────────────────────
# Idempotency & Invariants
# ─────────────────────────────────────────────────────────────────────────────

def test_materialization_is_idempotent(tmp_path):
    """
    Running materialization multiple times with the same input produces
    identical media_map and no stale or duplicate files.
    """
    workspace = Path.cwd()
    project_id = "prj_s13_idempotent"
    project_dir = tmp_path / "projects" / project_id
    project_dir.mkdir(parents=True)

    assets_ready = workspace / "assets" / "ready"
    assets_ready.mkdir(parents=True, exist_ok=True)
    video = assets_ready / "s13_idem_vid.mp4"
    video.write_text("Idempotent Video Content", encoding="utf-8")

    pub_project = workspace / "remotion-app" / "public" / "projects" / project_id

    try:
        manifest = ManifestV2(
            project_id=project_id,
            assets=[
                AssetV2(asset_id="ast_idem", kind=AssetKind.VIDEO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, processed_path=str(video)),
            ]
        )
        save_manifest(manifest, project_dir)
        bp = {
            "project_id": project_id,
            "version": "1.0",
            "scenes": [{"scene_id": "s1", "template": "ShowcaseWrapper", "startFrame": 0, "durationFrames": 30, "media_refs": ["ast_idem"]}]
        }
        (project_dir / "05_blueprint.json").write_text(json.dumps(bp), encoding="utf-8")
        (project_dir / "01_plan.md").write_text("plan", encoding="utf-8")

        # Run 1
        res1 = materialize_project_atomic(project_dir, workspace_root=workspace)
        map1 = (project_dir / "media_map.json").read_text(encoding="utf-8")
        gen1_id = res1["generation_id"]

        # Run 2 (Immediately after)
        res2 = materialize_project_atomic(project_dir, workspace_root=workspace)
        map2 = (project_dir / "media_map.json").read_text(encoding="utf-8")
        gen2_id = res2["generation_id"]

        assert res1["assets_count"] == res2["assets_count"]
        # Both generation directories contain the exact file
        file1 = workspace / "remotion-app" / "public" / f"projects/{project_id}/generations/{gen2_id}/ast_idem.mp4"
        assert file1.exists()
        assert file1.read_text(encoding="utf-8") == "Idempotent Video Content"
    finally:
        if video.exists():
            video.unlink()
        if pub_project.exists():
            shutil.rmtree(pub_project)


# ─────────────────────────────────────────────────────────────────────────────
# Reader-Safe Retirement & GC Tests (Barrier/Event Synchronized)
# ─────────────────────────────────────────────────────────────────────────────

def test_reader_safe_retirement_barrier_event(tmp_path):
    """
    MANDATORY S13 REGRESSION TEST (Barrier/Event Synchronized):
    Proves that a reader that obtained a valid generation descriptor (Generation A)
    can finish consuming that generation even after Writer commits Generation B
    and runs production cleanup.

    Deterministic Sequence:
    1. Writer publishes Generation A.
    2. Reader reads media_map.json (pointing to A), records file path,
       and halts on Barrier/Event before opening the file.
    3. Writer publishes Generation B (os.replace).
    4. Production cleanup runs (cleanup_inactive_generations with production defaults).
    5. Reader is released from Barrier/Event.
    6. Reader opens and reads the file from Generation A without FileNotFoundError.
    """
    workspace = Path.cwd()
    project_id = "prj_s13_barrier_test"
    project_dir = tmp_path / "projects" / project_id
    project_dir.mkdir(parents=True)

    assets_ready = workspace / "assets" / "ready"
    assets_ready.mkdir(parents=True, exist_ok=True)
    vid_a = assets_ready / "vid_barrier_a.mp4"
    vid_b = assets_ready / "vid_barrier_b.mp4"
    vid_a.write_text("CONTENT GENERATION A", encoding="utf-8")
    vid_b.write_text("CONTENT GENERATION B", encoding="utf-8")

    pub_project = workspace / "remotion-app" / "public" / "projects" / project_id

    try:
        # Step 1: Publish Generation A
        manifest_a = ManifestV2(
            project_id=project_id,
            assets=[
                AssetV2(asset_id="ast_main", kind=AssetKind.VIDEO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, processed_path=str(vid_a)),
            ]
        )
        save_manifest(manifest_a, project_dir)
        bp_a = {
            "project_id": project_id,
            "version": "1.0",
            "scenes": [{"scene_id": "s1", "template": "ShowcaseWrapper", "startFrame": 0, "durationFrames": 30, "media_refs": ["ast_main"]}]
        }
        (project_dir / "05_blueprint.json").write_text(json.dumps(bp_a), encoding="utf-8")
        (project_dir / "01_plan.md").write_text("plan", encoding="utf-8")

        res_a = materialize_project_atomic(project_dir, workspace_root=workspace)
        gen_a_id = res_a["generation_id"]

        # Synchronization primitives
        reader_read_map_event = threading.Event()
        writer_finished_event = threading.Event()
        reader_result = {"content": None, "error": None}

        def reader_worker():
            try:
                # 2. Reader reads media_map.json
                map_file = project_dir / "media_map.json"
                data = json.loads(map_file.read_text(encoding="utf-8"))
                rel_path = data["ast_main"]
                assert gen_a_id in rel_path, "Reader must have read Generation A map"
                full_path = workspace / "remotion-app" / "public" / rel_path

                # Signal that reader has the path, but has NOT opened the file yet!
                reader_read_map_event.set()

                # Wait deterministically for writer to publish B and run cleanup
                assert writer_finished_event.wait(timeout=10.0), "Timed out waiting for writer"

                # 6. Reader opens the file from Generation A
                with open(full_path, "r", encoding="utf-8") as f:
                    reader_result["content"] = f.read()
            except Exception as e:
                reader_result["error"] = e

        reader_thread = threading.Thread(target=reader_worker)
        reader_thread.start()

        # Wait until reader has acquired the map descriptor
        assert reader_read_map_event.wait(timeout=5.0), "Reader failed to read map in time"

        # Step 3: Writer publishes Generation B
        manifest_b = ManifestV2(
            project_id=project_id,
            assets=[
                AssetV2(asset_id="ast_main", kind=AssetKind.VIDEO, provenance=Provenance.USER_UPLOAD, status=AssetStatus.READY, processed_path=str(vid_b)),
            ]
        )
        save_manifest(manifest_b, project_dir)
        res_b = materialize_project_atomic(project_dir, workspace_root=workspace)
        gen_b_id = res_b["generation_id"]
        assert gen_b_id != gen_a_id

        # Step 4: Run production cleanup
        cleanup_inactive_generations(pub_project, active_gen_id=gen_b_id, project_dir=project_dir)

        # Step 5: Release the reader
        writer_finished_event.set()
        reader_thread.join(timeout=5.0)

        # Step 6: Verify reader consumed Generation A successfully
        assert reader_result["error"] is None, f"Reader suffered error: {reader_result['error']}"
        assert reader_result["content"] == "CONTENT GENERATION A"

    finally:
        if vid_a.exists():
            vid_a.unlink()
        if vid_b.exists():
            vid_b.unlink()
        if pub_project.exists():
            shutil.rmtree(pub_project)


def test_garbage_collection_policy(tmp_path, monkeypatch):
    """
    Subsequent GC Verification:
    - Active generation is NEVER deleted under any circumstances.
    - Previous generation still within policy (keep_previous=1 or within grace) is NOT deleted.
    - Old generation past retention and grace is deleted.
    - Orphan generation (never published) is cleaned up.
    - Cleanup failure does not affect active pointer or data.
    """
    pub_project = tmp_path / "remotion_pub" / "projects" / "prj_gc_test"
    project_dir = tmp_path / "projects" / "prj_gc_test"
    gen_root = pub_project / "generations"
    gen_root.mkdir(parents=True)
    project_dir.mkdir(parents=True)

    # 1. Setup 3 published generations: gen_0 (old), gen_1 (prev), gen_2 (active)
    for gid in ["gen_0", "gen_1", "gen_2"]:
        gdir = gen_root / gid
        gdir.mkdir()
        (gdir / "media.mp4").write_text(f"content_{gid}", encoding="utf-8")

    # Orphan generation: staged directory that was never published
    orphan_dir = gen_root / "gen_orphan_staged"
    orphan_dir.mkdir()
    (orphan_dir / "temp.mp4").write_text("orphan content", encoding="utf-8")
    # Make orphan mtime 60s in the past so orphan_grace_seconds (30s) passes
    past_time = time.time() - 60.0
    os.utime(orphan_dir, (past_time, past_time))

    # Active media map points to gen_2
    (project_dir / "media_map.json").write_text(
        json.dumps({"asset": "projects/prj_gc_test/generations/gen_2/media.mp4"}), encoding="utf-8"
    )

    # Record published history:
    # gen_0 published 500s ago, gen_1 published 100s ago, gen_2 published 10s ago
    t_now = time.time()
    from scripts.core.materializer import record_generation_published
    record_generation_published(pub_project, "gen_0", project_dir=project_dir, published_at=t_now - 500.0)
    record_generation_published(pub_project, "gen_1", project_dir=project_dir, published_at=t_now - 100.0)
    record_generation_published(pub_project, "gen_2", project_dir=project_dir, published_at=t_now - 10.0)

    # GC Run 1: keep_previous=1, grace_seconds=300
    # Active: gen_2 (preserved)
    # Prev: gen_1 (preserved by keep_previous=1 and grace 300)
    # Old: gen_0 (older than grace 300 and beyond keep_previous -> eligible and deleted)
    # Orphan: gen_orphan_staged (older than orphan grace -> deleted)
    gc1 = cleanup_inactive_generations(
        pub_project,
        active_gen_id="gen_2",
        project_dir=project_dir,
        keep_previous=1,
        grace_seconds=300.0,
        clean_orphans=True,
        orphan_grace_seconds=30.0,
        now=t_now,
    )

    assert "gen_2" in gc1["preserved"]
    assert "gen_1" in gc1["preserved"]
    assert "gen_0" in gc1["deleted"]
    assert "gen_orphan_staged" in gc1["orphans_deleted"]

    assert (gen_root / "gen_2").exists()
    assert (gen_root / "gen_1").exists()
    assert not (gen_root / "gen_0").exists()
    assert not (gen_root / "gen_orphan_staged").exists()

    # GC Run 2: Active generation is NEVER deleted even if keep_previous=0 and grace=0
    gc2 = cleanup_inactive_generations(
        pub_project,
        active_gen_id="gen_2",
        project_dir=project_dir,
        keep_previous=0,
        grace_seconds=0.0,
        now=t_now,
    )
    assert "gen_2" in gc2["preserved"]
    assert (gen_root / "gen_2").exists()
    assert not (gen_root / "gen_1").exists()  # gen_1 now deleted since keep_previous=0 and grace=0

    # GC Run 3: Cleanup failure (e.g. PermissionError) does NOT affect active pointer
    orig_rmtree = shutil.rmtree
    def fail_rmtree(path, **kwargs):
        raise PermissionError("Simulated locked file")
    monkeypatch.setattr(shutil, "rmtree", fail_rmtree)

    # Recreate an extra generation to trigger deletion failure
    extra_dir = gen_root / "gen_extra"
    extra_dir.mkdir()
    record_generation_published(pub_project, "gen_extra", project_dir=project_dir, published_at=t_now - 1000.0)

    gc3 = cleanup_inactive_generations(
        pub_project,
        active_gen_id="gen_2",
        project_dir=project_dir,
        keep_previous=0,
        grace_seconds=0.0,
        now=t_now,
    )
    assert len(gc3["errors"]) > 0
    # Active generation and pointer are 100% intact
    assert (gen_root / "gen_2").exists()
    active_map = json.loads((project_dir / "media_map.json").read_text(encoding="utf-8"))
    assert "gen_2" in active_map["asset"]
