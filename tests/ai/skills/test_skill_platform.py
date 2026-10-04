"""
tests/ai/skills/test_skill_platform.py
======================================
Comprehensive unit, negative, and behavioral test suite for Skills Platform (S28-02).

Covers:
- SkillRegistry (versioning, registration, active status filtering)
- SkillLoader (validation, rejection of invalid skills, markdown frontmatter parsing)
- SkillRouter (dynamic routing, 2-4 skills bounding, eligibility gate, hard audio mode exclusion)
- SkillContext & Knowledge integration (resolving required_knowledge via KnowledgeRouter)
"""

from __future__ import annotations

from pathlib import Path
import pytest

from ai.contracts.common import CapabilityType
from ai.contracts.creative.brief import AudioMode
from ai.contracts.creative.skills_knowledge import SkillDefinition, SkillStatus
from ai.knowledge.router import KnowledgeRouter
from ai.skills.contracts import SkillRoutingContext
from ai.skills.context import SkillContextBuilder
from ai.skills.loader import (
    SkillLoader,
    SkillValidationError,
)
from ai.skills.registry import (
    DuplicateSkillError,
    SkillRegistry,
)
from ai.skills.router import SkillRouter


@pytest.fixture
def workspace_root():
    return Path(__file__).resolve().parent.parent.parent.parent


@pytest.fixture
def populated_skill_router(workspace_root):
    registry = SkillRegistry()
    loader = SkillLoader(workspace_root=workspace_root)
    loader.load_canonical_catalog(registry=registry)
    return SkillRouter(registry=registry)


# =========================================================================
# 1. SkillRegistry Tests
# =========================================================================

def test_skill_registry_registration_and_status():
    reg = SkillRegistry()
    skill = SkillDefinition(
        skill_id="skill_custom_test",
        name="Custom Test Skill",
        description="Handles custom test operations",
        version="1.0.0",
        status=SkillStatus.ACTIVE,
    )
    reg.register(skill)

    assert reg.get("skill_custom_test") is not None
    assert reg.get_active("skill_custom_test") is not None
    assert len(reg.list_active()) == 1


def test_skill_registry_rejects_duplicates_when_disallowed():
    reg = SkillRegistry()
    skill = SkillDefinition(
        skill_id="skill_dup",
        name="Dup Skill",
        description="Duplicate",
        version="1.0.0",
    )
    reg.register(skill)
    with pytest.raises(DuplicateSkillError):
        reg.register(skill, allow_overwrite=False)


def test_skill_registry_excludes_retired_and_disabled():
    reg = SkillRegistry()
    s_retired = SkillDefinition(
        skill_id="skill_retired",
        name="Retired Skill",
        description="Obsolete",
        status=SkillStatus.RETIRED,
    )
    s_disabled = SkillDefinition(
        skill_id="skill_disabled",
        name="Disabled Skill",
        description="Temporarily turned off",
        status=SkillStatus.DISABLED,
    )
    reg.register(s_retired)
    reg.register(s_disabled)

    assert reg.get("skill_retired") is not None
    assert reg.get_active("skill_retired") is None
    assert reg.get_active("skill_disabled") is None
    assert len(reg.list_active()) == 0


# =========================================================================
# 2. SkillLoader & Validation Tests
# =========================================================================

def test_loader_loads_canonical_skills(workspace_root):
    loader = SkillLoader(workspace_root=workspace_root)
    skills = loader.get_canonical_skills()
    assert len(skills) >= 8
    skill_ids = [s.skill_id for s in skills]
    assert "skill_motion_typography" in skill_ids
    assert "skill_spoken_vo_humanizer" in skill_ids
    assert "skill_avatar_explainer" in skill_ids
    assert "skill_dynamic_montage" in skill_ids


def test_loader_rejects_invalid_skill_missing_required_fields(workspace_root):
    loader = SkillLoader(workspace_root=workspace_root)
    invalid_data = {
        "skill_id": "skill_broken",
        # missing name and description
    }
    with pytest.raises(SkillValidationError):
        loader.validate_skill(invalid_data)


def test_loader_rejects_invalid_capability_type(workspace_root):
    loader = SkillLoader(workspace_root=workspace_root)
    invalid_data = {
        "skill_id": "skill_bad_cap",
        "name": "Bad Capability Skill",
        "description": "Uses non-standard vendor capability",
        "required_capabilities": ["OPENAI_GPT4_DIRECT_CALL"],  # Vendor leak, forbidden!
    }
    with pytest.raises(SkillValidationError):
        loader.validate_skill(invalid_data)


def test_loader_parses_markdown_frontmatter(workspace_root):
    loader = SkillLoader(workspace_root=workspace_root)
    prompt_skill_path = workspace_root / ".agents" / "skills" / "prompt-engineering-expert" / "SKILL.md"
    if prompt_skill_path.exists():
        skill = loader.load_from_markdown(prompt_skill_path)
        assert skill.skill_id == "skill_prompt_engineering_expert"
        assert "prompt engineering" in skill.name.lower() or "prompt-engineering-expert" in skill.name
        assert len(skill.description) > 0


# =========================================================================
# 3. SkillRouter Dynamic Routing Tests
# =========================================================================

def test_skill_router_music_only_strictly_excludes_voiceover(populated_skill_router):
    """
    Key Acceptance Scenario:
    music-only montage must strictly exclude VO humanization skills.
    """
    ctx = SkillRoutingContext(
        intent="Assemble an energetic music montage ad with fast rhythmic cuts and beat sync",
        video_type="montage",
        audio_mode=AudioMode.MUSIC_ONLY,
        max_skills=3,
    )
    result = populated_skill_router.route_skills(ctx)

    assert len(result.selected_skills) > 0
    selected_ids = [s.skill_id for s in result.selected_skills]

    # Dynamic montage MUST be selected
    assert "skill_dynamic_montage" in selected_ids
    # Spoken VO humanizer MUST NOT be selected
    assert "skill_spoken_vo_humanizer" not in selected_ids
    assert "skill_spoken_vo_humanizer" in result.excluded_skills
    assert "Incompatible with MUSIC_ONLY" in result.excluded_skills["skill_spoken_vo_humanizer"]


def test_skill_router_voiceover_explainer_selects_vo(populated_skill_router):
    ctx = SkillRoutingContext(
        intent="Humanize conversational narration script and voiceover cadence for a SaaS explainer",
        video_type="explainer",
        audio_mode=AudioMode.VO_MUSIC,
        max_skills=3,
    )
    result = populated_skill_router.route_skills(ctx)

    selected_ids = [s.skill_id for s in result.selected_skills]
    assert "skill_spoken_vo_humanizer" in selected_ids


def test_skill_router_bounds_selection(populated_skill_router):
    """Verifies that router returns a small bounded set (e.g. max_skills=2), never all skills."""
    ctx = SkillRoutingContext(
        intent="Create an avatar video explainer with kinetic captions and b-roll",
        max_skills=2,
    )
    result = populated_skill_router.route_skills(ctx)
    assert len(result.selected_skills) <= 2


# =========================================================================
# 4. Required Knowledge Integration Tests
# =========================================================================

def test_skill_resolves_required_knowledge_via_knowledge_router(workspace_root):
    # Initialize knowledge platform
    k_router = KnowledgeRouter(workspace_root=workspace_root)
    k_router.initialize_canonical_catalog()

    # Initialize skill platform
    s_reg = SkillRegistry()
    s_loader = SkillLoader(workspace_root=workspace_root)
    s_loader.load_canonical_catalog(registry=s_reg)

    ctx_builder = SkillContextBuilder(knowledge_router=k_router)
    vo_skill = s_reg.get("skill_spoken_vo_humanizer")

    skill_ctx = ctx_builder.build_context(vo_skill)

    assert len(skill_ctx.retrieved_knowledge) > 0
    doc_ids = {rc.chunk.document_id for rc in skill_ctx.retrieved_knowledge}
    # Check that required knowledge declared by the skill was retrieved
    assert "know_sop_spoken_vo" in doc_ids or "know_playbook_video_copy" in doc_ids
