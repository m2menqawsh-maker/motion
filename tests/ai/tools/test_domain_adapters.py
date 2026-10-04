"""
tests/ai/tools/test_domain_adapters.py
======================================
Unit and functional tests for the 7 canonical domain tool adapters (S27.9).
"""

from unittest.mock import MagicMock, patch
import pytest

from api.schemas.lifecycle import LifecycleDTO
from api.schemas.run import RunResponse
from scripts.core.manifest_model import AssetKind, AssetStatus
from scripts.core.run_model import RunRecord, RunStatus
from scripts.core.review_service import ReviewStatusDTO
from ai.tools.contracts import (
    CancelRunInput,
    CheckAssetCacheInput,
    GetProjectStatusInput,
    GetQcReportInput,
    ListAssetsInput,
    PatchBlueprintInput,
    ReadBlueprintInput,
    SaveAssetCacheInput,
    StartRunInput,
)
from ai.tools.domain.assets import (
    check_asset_cache_adapter,
    list_assets_adapter,
    save_asset_cache_adapter,
)
from ai.tools.domain.blueprint import patch_blueprint_adapter, read_blueprint_adapter
from ai.tools.domain.projects import get_project_status_adapter
from ai.tools.domain.qc import get_qc_report_adapter
from ai.tools.domain.runs import cancel_run_adapter, start_run_adapter
from ai.tools.types import TrustedToolExecutionContext


@pytest.fixture
def test_ctx():
    return TrustedToolExecutionContext(
        workspace_id="ws_adapter_test",
        actor_id="usr_adapter_test",
        roles=["editor"],
        permissions=["project:read", "asset:read", "blueprint:read", "blueprint:edit", "run:execute", "run:cancel", "qc:view"],
    )


def test_get_project_status_adapter(test_ctx):
    """Verify get_project_status_adapter delegates to ProjectService."""
    mock_dto = LifecycleDTO(
        project_id="prj_test",
        lifecycle_state="ASSETS_READY",
        revision=3,
        allowed_actions=["blueprint:edit", "run:execute"],
        blocked_reason=None,
        review={"review_state": "PENDING"},
        latest_run={"run_id": "run_999"},
        artifacts_status={},
    )
    with patch("api.services.project_service.ProjectService.get_lifecycle_dto", return_value=mock_dto):
        inp = GetProjectStatusInput(project_id="prj_test")
        out = get_project_status_adapter(inp, test_ctx)

        assert out.project_id == "prj_test"
        assert out.lifecycle_state == "ASSETS_READY"
        assert out.revision == 3
        assert out.allowed_actions == ["blueprint:edit", "run:execute"]
        assert out.review_status == "PENDING"
        assert out.latest_run_id == "run_999"


def test_list_assets_adapter(test_ctx):
    """Verify list_assets_adapter formats assets from AssetService."""
    mock_raw_assets = [
        {
            "asset_id": "ast_1",
            "kind": "image",
            "status": "ready",
            "processed_path": "assets/ready/ast_1.png",
            "metadata": {"original_filename": "photo.png", "size_bytes": 1024},
        },
        {
            "asset_id": "ast_2",
            "kind": "audio",
            "status": "ready",
            "processed_path": "assets/ready/ast_2.mp3",
            "metadata": {"original_filename": "voice.mp3", "size_bytes": 2048},
        },
    ]
    with patch("api.services.asset_service.AssetService.list_assets", return_value=mock_raw_assets):
        inp = ListAssetsInput(project_id="prj_test")
        out = list_assets_adapter(inp, test_ctx)

        assert out.project_id == "prj_test"
        assert out.total_count == 2
        assert len(out.assets) == 2
        assert out.assets[0].asset_id == "ast_1"
        assert out.assets[0].filename == "photo.png"
        assert out.assets[1].kind == "audio"


def test_read_blueprint_adapter(test_ctx):
    """Verify read_blueprint_adapter retrieves blueprint via PipelineService."""
    mock_bp = {
        "blueprint_version": "2.0.0",
        "project_id": "prj_test",
        "fps": 60,
        "aspect_ratio": "9:16",
        "scenes": [{"scene_id": "sc_1", "template": "intro", "startFrame": 0, "durationFrames": 60}],
        "audio": {"voiceover": None},
    }
    mock_dto = LifecycleDTO(
        project_id="prj_test",
        lifecycle_state="BLUEPRINT_READY",
        revision=5,
        allowed_actions=[],
        blocked_reason=None,
        review={},
        latest_run=None,
        artifacts_status={},
    )
    with patch("api.services.pipeline_service.PipelineService.get_blueprint", return_value=mock_bp), \
         patch("api.services.project_service.ProjectService.get_lifecycle_dto", return_value=mock_dto):
        inp = ReadBlueprintInput(project_id="prj_test")
        out = read_blueprint_adapter(inp, test_ctx)

        assert out.project_id == "prj_test"
        assert out.fps == 60
        assert out.aspect_ratio == "9:16"
        assert out.scene_count == 1
        assert out.revision == 5


def test_patch_blueprint_adapter(test_ctx):
    """Verify patch_blueprint_adapter validates and mutates via PipelineService."""
    payload = {"project_id": "prj_test", "fps": 30, "aspect_ratio": "16:9", "scenes": []}
    mock_dto = LifecycleDTO(
        project_id="prj_test",
        lifecycle_state="BLUEPRINT_READY",
        revision=6,
        allowed_actions=[],
        blocked_reason=None,
        review={},
        latest_run=None,
        artifacts_status={},
    )
    with patch("api.services.pipeline_service.PipelineService.validate_blueprint_payload", return_value=(True, [])), \
         patch("api.services.pipeline_service.PipelineService.mutate_blueprint") as mock_mutate, \
         patch("api.services.project_service.ProjectService.get_lifecycle_dto", return_value=mock_dto):
        inp = PatchBlueprintInput(project_id="prj_test", expected_revision=6, blueprint=payload)
        out = patch_blueprint_adapter(inp, test_ctx)

        assert out.success is True
        assert out.revision == 6
        mock_mutate.assert_called_once()
        call_args = mock_mutate.call_args[1]
        assert call_args["project_id"] == "prj_test"
        assert call_args["payload"]["project_id"] == "prj_test"
        assert call_args["actor_id"] == test_ctx.actor_id


def test_patch_blueprint_adapter_stale_revision_conflict(test_ctx):
    """Verify patch_blueprint_adapter rejects stale revisions (optimistic concurrency control)."""
    payload = {"project_id": "prj_test", "fps": 30, "aspect_ratio": "16:9", "scenes": []}
    mock_dto = LifecycleDTO(
        project_id="prj_test",
        lifecycle_state="BLUEPRINT_READY",
        revision=6,  # current revision is 6
        allowed_actions=[],
        blocked_reason=None,
        review={},
        latest_run=None,
        artifacts_status={},
    )
    with patch("api.services.pipeline_service.PipelineService.validate_blueprint_payload", return_value=(True, [])), \
         patch("api.services.pipeline_service.PipelineService.mutate_blueprint") as mock_mutate, \
         patch("api.services.project_service.ProjectService.get_lifecycle_dto", return_value=mock_dto):
        inp = PatchBlueprintInput(project_id="prj_test", expected_revision=3, blueprint=payload)  # expected is 3!
        with pytest.raises(ValueError) as exc_info:
            patch_blueprint_adapter(inp, test_ctx)
        assert "Stale revision conflict" in str(exc_info.value)
        mock_mutate.assert_not_called()


def test_start_run_adapter(test_ctx):
    """Verify start_run_adapter creates a run via RunService."""
    mock_record = RunRecord(
        run_id="run_abc123",
        workspace_id=test_ctx.workspace_id,
        project_id="prj_test",
        status=RunStatus.QUEUED,
        input_revision=2,
        idempotency_key="idemp_1",
    )
    with patch("api.services.run_service.RunService.create_run", return_value=(mock_record, True)):
        inp = StartRunInput(project_id="prj_test", idempotency_key="idemp_1")
        out = start_run_adapter(inp, test_ctx)

        assert out.project_id == "prj_test"
        assert out.run_id == "run_abc123"
        assert out.status == "QUEUED"
        assert out.is_created is True
        assert out.input_revision == 2


def test_cancel_run_adapter(test_ctx):
    """Verify cancel_run_adapter calls RunService.cancel_run."""
    mock_record = RunRecord(
        run_id="run_abc123",
        workspace_id=test_ctx.workspace_id,
        project_id="prj_test",
        status=RunStatus.CANCELLED,
        input_revision=2,
    )
    with patch("api.services.run_service.RunService.cancel_run", return_value=mock_record):
        inp = CancelRunInput(project_id="prj_test", run_id="run_abc123")
        out = cancel_run_adapter(inp, test_ctx)

        assert out.project_id == "prj_test"
        assert out.run_id == "run_abc123"
        assert out.status == "CANCELLED"


def test_get_qc_report_adapter(test_ctx):
    """Verify get_qc_report_adapter reads QC artifacts and review status."""
    mock_qc_data = {
        "verdict": "PASS",
        "overall_status": "PROBE_PASSED",
        "issues": [],
    }
    mock_review_dto = ReviewStatusDTO(
        project_id="prj_test",
        lifecycle_state="PROBE_PASSED",
        active_decision="APPROVED",
    )
    with patch("api.services.domain_artifact_service.DomainArtifactService.read_artifact", return_value=(mock_qc_data, "probe_qc_report.json", 1, "sha")):
        with patch("scripts.core.review_service.ReviewService.get_review_status", return_value=mock_review_dto):
            inp = GetQcReportInput(project_id="prj_test")
            out = get_qc_report_adapter(inp, test_ctx)

            assert out.project_id == "prj_test"
            assert out.has_report is True
            assert out.status == "AVAILABLE"
            assert out.verdict == "PASS"
            assert out.review_state == "APPROVED"


def test_check_asset_cache_adapter(test_ctx):
    """Verify check_asset_cache_adapter delegates to AssetService.check_asset_cache."""
    with patch("api.services.asset_service.AssetService.check_asset_cache", return_value="/abs/path/to/cached.png"):
        inp = CheckAssetCacheInput(project_id="prj_test", asset_id="ast_1", specs_hash="w200")
        out = check_asset_cache_adapter(inp, test_ctx)

        assert out.project_id == "prj_test"
        assert out.asset_id == "ast_1"
        assert out.hit is True
        assert out.cached_location == "/abs/path/to/cached.png"


def test_save_asset_cache_adapter(test_ctx):
    """Verify save_asset_cache_adapter delegates to AssetService.save_asset_to_cache."""
    with patch("api.services.asset_service.AssetService.save_asset_to_cache", return_value="/abs/path/to/saved.png"):
        inp = SaveAssetCacheInput(
            project_id="prj_test",
            asset_id="ast_1",
            file_path="/tmp/source.png",
            specs_hash="w200",
        )
        out = save_asset_cache_adapter(inp, test_ctx)

        assert out.project_id == "prj_test"
        assert out.asset_id == "ast_1"
        assert out.cached_location == "/abs/path/to/saved.png"
