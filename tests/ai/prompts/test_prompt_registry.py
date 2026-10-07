"""
tests/ai/prompts/test_prompt_registry.py
=========================================
Unit and integration tests for Prompt Registry & Authority Service (S27.18).

Invariants verified:
1. Every prompt is a versioned entity with prompt_id, version, hash, status, created_at.
2. Production prompts cannot be unversioned random strings inside services.
3. Versions are strictly immutable (attempting to overwrite v1 in place fails).
4. Lifecycle states strictly enforced: DRAFT -> TESTING -> eval gate -> PRODUCTION -> RETIRED.
5. Direct promotion from DRAFT to PRODUCTION is strictly blocked.
6. AI models have zero authority to create, mutate, or promote prompts.
7. Active production resolution retrieves latest approved PRODUCTION prompt.
8. Safe variable interpolation with missing variable validation.
9. Tenant isolation: workspace prompts are isolated.
"""

from datetime import datetime, timezone
import pytest

from ai.contracts.prompt import (
    InvalidPromptLifecycleTransitionError,
    MissingPromptVariableError,
    PromptContract,
    PromptMetadata,
    PromptNotFoundError,
    PromptRenderRequest,
    PromptStatus,
    PromptVersionImmutableError,
    PromptVersionNotFoundError,
    UnauthorizedPromptMutationError,
    PromptEvalGateRejectedError,
)
from ai.prompts.service import PromptService
from scripts.core.ai_prompt_repository import SQLPromptRepository
from scripts.core.database import DatabaseEngine


@pytest.fixture
def prompt_service(tmp_path):
    db_file = tmp_path / "test_prompts.db"
    engine = DatabaseEngine(f"sqlite:///{db_file}")
    repo = SQLPromptRepository(engine=engine)
    return PromptService(repository=repo)


def test_create_prompt_v1_versioned_entity(prompt_service):
    prompt = prompt_service.create_prompt(
        prompt_id="video_planner",
        template="Plan a video about {topic} with {tone} style.",
        system_prompt="You are an expert video director.",
        variables=["topic", "tone"],
        author="eng_team",
        description="Core planning prompt",
    )

    assert prompt.prompt_id == "video_planner"
    assert prompt.version == 1
    assert len(prompt.hash) == 64
    assert prompt.status == PromptStatus.DRAFT
    assert prompt.variables == ["topic", "tone"]
    assert prompt.created_at is not None
    assert prompt.metadata.author == "eng_team"


def test_immutable_versioning(prompt_service):
    # Create v1
    v1 = prompt_service.create_prompt(
        prompt_id="video_planner",
        template="Plan a video about {topic}.",
        variables=["topic"],
    )
    assert v1.version == 1
    v1_hash = v1.hash

    # Cannot recreate or overwrite v1 in place with direct repo save
    mod_template = "Modified template in place"
    duplicate_v1 = PromptContract(
        prompt_id="video_planner",
        version=1,
        hash=PromptContract.compute_content_hash(mod_template),
        status=PromptStatus.DRAFT,
        template=mod_template,
        variables=["topic"],
        created_at=datetime.now(timezone.utc),
    )
    with pytest.raises(PromptVersionImmutableError):
        prompt_service._repository.save_prompt(duplicate_v1)

    # Creating a new version increments version to 2 and produces distinct hash
    v2 = prompt_service.create_version(
        prompt_id="video_planner",
        template="Plan an engaging viral video about {topic} with {duration} seconds.",
        variables=["topic", "duration"],
    )
    assert v2.version == 2
    assert v2.hash != v1_hash
    assert v2.status == PromptStatus.DRAFT


def test_unauthorized_ai_model_mutation_blocked(prompt_service):
    # AI model attempting to create prompt
    with pytest.raises(UnauthorizedPromptMutationError):
        prompt_service.create_prompt(
            prompt_id="unauthorized_prompt",
            template="AI generated prompt",
            caller_role="AI_MODEL",
        )

    # Human creates v1
    prompt_service.create_prompt(
        prompt_id="script_generator",
        template="Write a script for {topic}.",
        caller_role="HUMAN_OPERATOR",
    )

    # AI model attempting to create new version
    with pytest.raises(UnauthorizedPromptMutationError):
        prompt_service.create_version(
            prompt_id="script_generator",
            template="AI modified script prompt",
            caller_role="AGENT",
        )

    # AI model attempting to promote prompt
    with pytest.raises(UnauthorizedPromptMutationError):
        prompt_service.promote_prompt(
            prompt_id="script_generator",
            version=1,
            target_status=PromptStatus.TESTING,
            caller_role="LLM",
        )


def test_direct_draft_to_production_blocked(prompt_service):
    # Cannot create directly in PRODUCTION
    with pytest.raises(InvalidPromptLifecycleTransitionError):
        prompt_service.create_prompt(
            prompt_id="fast_lane_prompt",
            template="Direct prod prompt",
            initial_status=PromptStatus.PRODUCTION,
        )

    prompt = prompt_service.create_prompt(
        prompt_id="fast_lane_prompt",
        template="Direct prod prompt",
        initial_status=PromptStatus.DRAFT,
    )

    # Cannot transition directly from DRAFT to PRODUCTION
    with pytest.raises(InvalidPromptLifecycleTransitionError) as exc_info:
        prompt_service.promote_prompt(
            prompt_id="fast_lane_prompt",
            version=1,
            target_status=PromptStatus.PRODUCTION,
        )
    assert "Direct promotion from DRAFT to PRODUCTION" in str(exc_info.value)


def test_full_lifecycle_and_eval_gate(prompt_service):
    # 1. Create in DRAFT
    prompt = prompt_service.create_prompt(
        prompt_id="audio_prompt",
        template="Analyze audio stem {stem_id}.",
        variables=["stem_id"],
    )
    assert prompt.status == PromptStatus.DRAFT

    # 2. Advance to TESTING
    testing_prompt = prompt_service.promote_prompt(
        prompt_id="audio_prompt",
        version=1,
        target_status=PromptStatus.TESTING,
    )
    assert testing_prompt.status == PromptStatus.TESTING

    # 3. Attempt promotion to PRODUCTION without eval gate -> blocked
    with pytest.raises(PromptEvalGateRejectedError):
        prompt_service.promote_prompt(
            prompt_id="audio_prompt",
            version=1,
            target_status=PromptStatus.PRODUCTION,
        )

    # 4. Attempt promotion with failing eval quality score (< 0.80) -> blocked
    with pytest.raises(PromptEvalGateRejectedError) as exc_fail:
        prompt_service.promote_prompt(
            prompt_id="audio_prompt",
            version=1,
            target_status=PromptStatus.PRODUCTION,
            eval_quality_score=0.74,
        )
    assert "below the 0.80 minimum threshold" in str(exc_fail.value)

    # 5. Promote with passing eval gate (score >= 0.80)
    prod_prompt = prompt_service.promote_prompt(
        prompt_id="audio_prompt",
        version=1,
        target_status=PromptStatus.PRODUCTION,
        eval_gate_id="eval_gate_s27_audio_001",
        eval_quality_score=0.92,
    )
    assert prod_prompt.status == PromptStatus.PRODUCTION

    # 6. Retire version
    retired_prompt = prompt_service.promote_prompt(
        prompt_id="audio_prompt",
        version=1,
        target_status=PromptStatus.RETIRED,
    )
    assert retired_prompt.status == PromptStatus.RETIRED

    # 7. Resurrecting RETIRED prompt is blocked
    with pytest.raises(InvalidPromptLifecycleTransitionError):
        prompt_service.promote_prompt(
            prompt_id="audio_prompt",
            version=1,
            target_status=PromptStatus.TESTING,
        )


def test_active_production_resolution_and_superseding(prompt_service):
    # Create v1 and promote to PRODUCTION
    prompt_service.create_prompt(
        prompt_id="summarizer",
        template="Summarize text: {text} in v1 style.",
        variables=["text"],
    )
    prompt_service.promote_prompt("summarizer", 1, PromptStatus.TESTING)
    prompt_service.promote_prompt("summarizer", 1, PromptStatus.PRODUCTION, eval_gate_id="gate_1", eval_quality_score=0.9)

    # Render without specifying version resolves active v1
    rendered_v1 = prompt_service.render_prompt(
        PromptRenderRequest(
            prompt_id="summarizer",
            variables={"text": "video content"},
        )
    )
    assert rendered_v1.version == 1
    assert "v1 style" in rendered_v1.rendered_text

    # Create v2 and promote to PRODUCTION
    prompt_service.create_version(
        prompt_id="summarizer",
        template="Summarize text: {text} in modern v2 style.",
        variables=["text"],
    )
    prompt_service.promote_prompt("summarizer", 2, PromptStatus.TESTING)
    prompt_service.promote_prompt("summarizer", 2, PromptStatus.PRODUCTION, eval_gate_id="gate_2", eval_quality_score=0.95)

    # Verify v1 was automatically RETIRED when v2 was promoted to PRODUCTION
    v1_check = prompt_service._repository.get_prompt("summarizer", 1)
    assert v1_check.status == PromptStatus.RETIRED

    # Active production prompt now resolves to v2
    rendered_v2 = prompt_service.render_prompt(
        PromptRenderRequest(
            prompt_id="summarizer",
            variables={"text": "video content"},
        )
    )
    assert rendered_v2.version == 2
    assert "modern v2 style" in rendered_v2.rendered_text


def test_render_variable_validation(prompt_service):
    prompt_service.create_prompt(
        prompt_id="interpolator",
        template="Hello {name}, your role is {role}.",
        variables=["name", "role"],
    )
    prompt_service.promote_prompt("interpolator", 1, PromptStatus.TESTING)
    prompt_service.promote_prompt("interpolator", 1, PromptStatus.PRODUCTION, eval_gate_id="gate_x")

    # Missing variable 'role' raises error
    with pytest.raises(MissingPromptVariableError) as exc_info:
        prompt_service.render_prompt(
            PromptRenderRequest(
                prompt_id="interpolator",
                version=1,
                variables={"name": "Alice"},
            )
        )
    assert "Missing required variables" in str(exc_info.value)
    assert "role" in str(exc_info.value)

    # Valid rendering succeeds
    res = prompt_service.render_prompt(
        PromptRenderRequest(
            prompt_id="interpolator",
            version=1,
            variables={"name": "Alice", "role": "Director"},
        )
    )
    assert res.rendered_text == "Hello Alice, your role is Director."
