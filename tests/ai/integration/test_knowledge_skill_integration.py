"""
tests/ai/integration/test_knowledge_skill_integration.py
=========================================================
End-to-end integration tests for the S28-02 Knowledge & Skills Platform.

Validates the full collaborative workflow:
Creative Context
   ↓
KnowledgeRouter (retrieves bounded, deduplicated, provenance-backed knowledge)
   +
SkillRouter (routes 2-4 eligible operational skills with hard incompatibility gates)
   ↓
SkillContextBuilder (assembles authoritative SkillContext, resolving required knowledge)
   ↓
SkillExecutor (enforces Skill ≠ Permission via ToolAuthorizationPolicy)

Key Acceptance Scenarios:
1. music-only montage: Strictly excludes all spoken VO knowledge, voiceover humanization skills,
   and speech-specific operational context.
2. voiceover explainer: Correctly routes spoken VO humanization and explainer skills with
   relevant SOP and playbook knowledge, while excluding montage-only skills.
3. Determinism, token bounding, and provenance integrity across the combined platform.
"""

from __future__ import annotations

from pathlib import Path
import pytest
from pydantic import BaseModel

from ai.contracts.base import AIContractModel
from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.skills_knowledge import SkillStatus
from ai.knowledge.contracts import KnowledgeRetrievalQuery
from ai.knowledge.router import KnowledgeRouter
from ai.skills.contracts import SkillRoutingContext
from ai.skills.context import (
    SkillContextBuilder,
    SkillExecutor,
    ToolAuthorizationDeniedError,
    ToolUndeclaredError,
)
from ai.skills.loader import SkillLoader
from ai.skills.registry import SkillRegistry
from ai.skills.router import SkillRouter
from ai.tools.contracts import ToolDefinition
from ai.tools.types import (
    SideEffectClass,
    TrustedToolExecutionContext,
)
from scripts.core.security.permissions import Action


class DummyBeatDetectionInput(AIContractModel):
    audio_path: str = "audio/track.mp3"


class DummyBeatDetectionOutput(AIContractModel):
    bpm: float = 128.0
    beats: list[float] = [0.5, 1.0, 1.5, 2.0]


@pytest.fixture
def workspace_root():
    return Path(__file__).resolve().parent.parent.parent.parent


@pytest.fixture
def integrated_platform(workspace_root):
    # 1. Initialize Knowledge Platform
    k_router = KnowledgeRouter(workspace_root=workspace_root)
    k_router.initialize_canonical_catalog()

    # 2. Initialize Skill Platform
    s_reg = SkillRegistry()
    s_loader = SkillLoader(workspace_root=workspace_root)
    s_loader.load_canonical_catalog(registry=s_reg)
    s_router = SkillRouter(registry=s_reg)

    # 3. Initialize Context Builder
    ctx_builder = SkillContextBuilder(knowledge_router=k_router)

    return {
        "knowledge_router": k_router,
        "skill_router": s_router,
        "skill_registry": s_reg,
        "context_builder": ctx_builder,
    }


@pytest.fixture
def patch_blueprint_tool():
    return ToolDefinition(
        name="patch_blueprint",
        description="Applies creative modifications to the project blueprint",
        input_contract=DummyBeatDetectionInput,
        output_contract=DummyBeatDetectionOutput,
        side_effect_class=SideEffectClass.PROJECT_MUTATION,
        required_permission=Action.BLUEPRINT_EDIT,
        enabled=True,
    )


@pytest.fixture
def privileged_tool():
    return ToolDefinition(
        name="admin_purge_registry",
        description="Administrative tool to purge templates",
        input_contract=DummyBeatDetectionInput,
        output_contract=DummyBeatDetectionOutput,
        side_effect_class=SideEffectClass.ADMIN,
        required_permission=Action.SYSTEM_ADMIN,
        enabled=True,
    )


# =========================================================================
# Scenario 1: Music-Only Montage Pipeline (Primary Acceptance Scenario)
# =========================================================================

def test_music_only_montage_end_to_end_pipeline(integrated_platform, patch_blueprint_tool):
    """
    Verifies that for a MUSIC_ONLY montage request:
    - KnowledgeRouter excludes spoken VO documents (know_sop_spoken_vo).
    - SkillRouter selects skill_dynamic_montage and excludes skill_spoken_vo_humanizer.
    - SkillContextBuilder resolves dynamic montage knowledge without spoken VO.
    - SkillExecutor enforces ToolAuthorizationPolicy for declared tools.
    """
    k_router: KnowledgeRouter = integrated_platform["knowledge_router"]
    s_router: SkillRouter = integrated_platform["skill_router"]
    ctx_builder: SkillContextBuilder = integrated_platform["context_builder"]

    # 1. Knowledge Retrieval for Music-Only Montage
    k_query = KnowledgeRetrievalQuery(
        query="dynamic montage cuts fast pacing music beat sync transitions",
        video_type="montage",
        audio_mode=AudioMode.MUSIC_ONLY,
        limit_chunks=6,
    )
    k_result = k_router.retrieve(k_query)

    assert len(k_result.chunks) > 0
    retrieved_doc_ids = {rc.chunk.document_id for rc in k_result.chunks}

    # Strict invariant: NO spoken voiceover knowledge in MUSIC_ONLY
    assert "know_sop_spoken_vo" not in retrieved_doc_ids
    for rc in k_result.chunks:
        assert "spoken_vo_humanizer" not in rc.chunk.source
        assert AudioMode.VO_ONLY not in rc.chunk.audio_modes

    # 2. Skill Routing for Music-Only Montage
    s_ctx = SkillRoutingContext(
        intent="Assemble an energetic music montage ad with fast rhythmic cuts and beat sync",
        video_type="montage",
        audio_mode=AudioMode.MUSIC_ONLY,
        max_skills=3,
    )
    s_result = s_router.route_skills(s_ctx)

    selected_skill_ids = [s.skill_id for s in s_result.selected_skills]
    assert "skill_dynamic_montage" in selected_skill_ids
    assert "skill_spoken_vo_humanizer" not in selected_skill_ids
    assert "skill_spoken_vo_humanizer" in s_result.excluded_skills
    assert "Incompatible with MUSIC_ONLY" in s_result.excluded_skills["skill_spoken_vo_humanizer"]

    # 3. Context Construction
    montage_skill = next(s for s in s_result.selected_skills if s.skill_id == "skill_dynamic_montage")
    skill_context = ctx_builder.build_context(
        skill=montage_skill,
        audio_mode=AudioMode.MUSIC_ONLY,
    )

    assert skill_context.skill.skill_id == "skill_dynamic_montage"
    assert "patch_blueprint" in skill_context.declared_tools
    # All retrieved knowledge for the skill must also be free of spoken VO
    for rc in skill_context.retrieved_knowledge:
        assert rc.chunk.document_id != "know_sop_spoken_vo"

    # 4. Skill Execution & Tool Authorization Gate (Skill ≠ Permission)
    executor = SkillExecutor(context=skill_context)

    # 4a. Undeclared tool attempt -> ToolUndeclaredError
    undeclared_tool = ToolDefinition(
        name="generate_speech",
        description="Generates TTS speech",
        input_contract=DummyBeatDetectionInput,
        output_contract=DummyBeatDetectionOutput,
        side_effect_class=SideEffectClass.READ_ONLY,
        required_permission=Action.ASSET_READ,
        enabled=True,
    )
    with pytest.raises(ToolUndeclaredError):
        executor.authorize_tool_call(
            tool_def=undeclared_tool,
            exec_context=TrustedToolExecutionContext(actor_id="u1", workspace_id="ws1", permissions=[Action.ASSET_READ]),
            input_data=DummyBeatDetectionInput(),
        )

    # 4b. Declared tool with missing permission -> ToolAuthorizationDeniedError
    unauthorized_exec_ctx = TrustedToolExecutionContext(
        actor_id="u1",
        workspace_id="ws1",
        permissions=[],  # Missing BLUEPRINT_EDIT!
    )
    with pytest.raises(ToolAuthorizationDeniedError):
        executor.authorize_tool_call(
            tool_def=patch_blueprint_tool,
            exec_context=unauthorized_exec_ctx,
            input_data=DummyBeatDetectionInput(),
        )

    # 4c. Declared tool with valid permission -> Authorized!
    authorized_exec_ctx = TrustedToolExecutionContext(
        actor_id="u1",
        workspace_id="ws1",
        permissions=[Action.BLUEPRINT_EDIT],
    )
    auth_res = executor.authorize_tool_call(
        tool_def=patch_blueprint_tool,
        exec_context=authorized_exec_ctx,
        input_data=DummyBeatDetectionInput(),
    )
    assert auth_res.allowed is True


# =========================================================================
# Scenario 2: Voiceover Explainer Pipeline
# =========================================================================

def test_voiceover_explainer_end_to_end_pipeline(integrated_platform):
    """
    Verifies that for an explainer request with voiceover:
    - KnowledgeRouter retrieves spoken VO and explainer knowledge.
    - SkillRouter selects skill_spoken_vo_humanizer and skill_avatar_explainer.
    - SkillRouter penalizes/excludes skill_dynamic_montage.
    - SkillContextBuilder correctly resolves required knowledge for spoken VO.
    """
    k_router: KnowledgeRouter = integrated_platform["knowledge_router"]
    s_router: SkillRouter = integrated_platform["skill_router"]
    ctx_builder: SkillContextBuilder = integrated_platform["context_builder"]

    # 1. Knowledge Retrieval
    k_query = KnowledgeRetrievalQuery(
        query="conversational speech pacing narration script writing voiceover pauses",
        video_type="explainer",
        audio_mode=AudioMode.VO_MUSIC,
        limit_chunks=5,
    )
    k_result = k_router.retrieve(k_query)
    doc_ids = {rc.chunk.document_id for rc in k_result.chunks}
    assert "know_sop_spoken_vo" in doc_ids or "know_playbook_video_copy" in doc_ids

    # 2. Skill Routing
    s_ctx = SkillRoutingContext(
        intent="Create a professional avatar explainer video with friendly spoken narration and script cadence",
        video_type="explainer",
        audio_mode=AudioMode.VO_MUSIC,
        max_skills=3,
    )
    s_result = s_router.route_skills(s_ctx)
    selected_skill_ids = [s.skill_id for s in s_result.selected_skills]

    assert "skill_spoken_vo_humanizer" in selected_skill_ids
    assert "skill_avatar_explainer" in selected_skill_ids
    # Dynamic montage should NOT be activated for explainer
    assert "skill_dynamic_montage" not in selected_skill_ids

    # 3. Context Construction
    vo_skill = next(s for s in s_result.selected_skills if s.skill_id == "skill_spoken_vo_humanizer")
    skill_context = ctx_builder.build_context(
        skill=vo_skill,
        audio_mode=AudioMode.VO_MUSIC,
    )

    assert skill_context.skill.skill_id == "skill_spoken_vo_humanizer"
    assert len(skill_context.retrieved_knowledge) > 0
    retrieved_docs = {rc.chunk.document_id for rc in skill_context.retrieved_knowledge}
    assert "know_sop_spoken_vo" in retrieved_docs or "know_playbook_video_copy" in retrieved_docs


# =========================================================================
# Scenario 3: Bounding, Determinism, and Provenance Integrity
# =========================================================================

def test_pipeline_bounding_and_provenance_integrity(integrated_platform):
    """
    Verifies:
    1. Bounding: Knowledge returns <= max_chunks and Skill returns <= max_skills.
    2. Determinism: Identical queries yield identical order and scores.
    3. Provenance: Every chunk contains complete, verifiable provenance fields.
    """
    k_router: KnowledgeRouter = integrated_platform["knowledge_router"]
    s_router: SkillRouter = integrated_platform["skill_router"]

    k_query = KnowledgeRetrievalQuery(
        query="typography kinetic captions animated subtitles on-screen text",
        limit_chunks=4,
    )

    # 1. Determinism
    res1 = k_router.retrieve(k_query)
    res2 = k_router.retrieve(k_query)

    assert len(res1.chunks) == len(res2.chunks)
    assert [c.chunk.chunk_id for c in res1.chunks] == [c.chunk.chunk_id for c in res2.chunks]
    assert [c.score for c in res1.chunks] == [c.score for c in res2.chunks]

    # 2. Bounding
    assert len(res1.chunks) <= 4

    # 3. Provenance Integrity
    for rc in res1.chunks:
        chunk = rc.chunk
        assert chunk.chunk_id.startswith("chk_")
        assert chunk.document_id.startswith("know_")
        assert chunk.section != ""
        assert chunk.version != ""
        assert chunk.source.endswith(".md")
        assert len(chunk.content_hash) == 64  # SHA-256 hex digest
        assert len(chunk.content) > 0

    # Skill Bounding
    s_ctx = SkillRoutingContext(
        intent="kinetic captions typography animation subtitles styling",
        max_skills=2,
    )
    s_res = s_router.route_skills(s_ctx)
    assert len(s_res.selected_skills) <= 2
    assert s_res.selected_skills[0].skill_id == "skill_motion_typography"

