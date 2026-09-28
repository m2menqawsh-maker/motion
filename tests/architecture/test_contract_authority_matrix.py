"""
Architecture tests for S10 Contract Authority Matrix and Version Policy.
Enforces:
- Every governed domain has exactly one canonical authority.
- No governed domain has zero or multiple canonical authorities.
- Generated representations are marked as GENERATED and cannot masquerade as CANONICAL.
- Unknown field policy and version policy are explicitly declared for all governed domains.
- Migration owners are defined for future domains (e.g. S11, S12, S15, S17).
"""
import pytest
from pathlib import Path


def test_matrix_module_importable():
    """Test 1: Matrix API is available and machine-readable."""
    from scripts.core.authority_matrix import (
        ContractAuthorityMatrix,
        GovernedDomain,
        RepresentationRole,
        UnknownFieldPolicy,
    )
    assert ContractAuthorityMatrix is not None
    assert len(GovernedDomain) >= 12


def test_every_governed_domain_has_exactly_one_canonical_authority():
    """Test 2: Every governed domain has exactly one canonical authority."""
    from scripts.core.authority_matrix import (
        ContractAuthorityMatrix,
        GovernedDomain,
        RepresentationRole,
    )

    for domain in GovernedDomain:
        entry = ContractAuthorityMatrix.get_entry(domain)
        assert entry is not None, f"Domain {domain.value} is missing from ContractAuthorityMatrix"

        # Check representations
        canonical_reps = [r for r in entry.representations if r.role == RepresentationRole.CANONICAL]
        assert len(canonical_reps) == 1, (
            f"Domain {domain.value} must have EXACTLY ONE canonical representation, "
            f"found {len(canonical_reps)}: {[r.name for r in canonical_reps]}"
        )


def test_generated_representation_cannot_masquerade_as_authority():
    """Test 3: Generated representations must be tagged GENERATED, never CANONICAL."""
    from scripts.core.authority_matrix import (
        ContractAuthorityMatrix,
        GovernedDomain,
        RepresentationRole,
    )

    for domain in GovernedDomain:
        entry = ContractAuthorityMatrix.get_entry(domain)
        for rep in entry.representations:
            if rep.name.endswith(".schema.json") and rep.is_generated:
                assert rep.role == RepresentationRole.GENERATED, (
                    f"Representation {rep.name} in domain {domain.value} is generated "
                    f"but has role {rep.role.value} instead of GENERATED"
                )
            if rep.role == RepresentationRole.CANONICAL:
                assert not rep.is_generated, (
                    f"Canonical representation {rep.name} in domain {domain.value} cannot be marked as generated!"
                )


def test_all_governed_domains_covered():
    """Verifies that all 12 mandatory domains are registered."""
    from scripts.core.authority_matrix import ContractAuthorityMatrix, GovernedDomain

    mandatory_domains = {
        "STATE",
        "REVIEW",
        "ARTIFACT_EVIDENCE",
        "MANIFEST",
        "BLUEPRINT",
        "MEDIA_REFERENCE",
        "AUDIO",
        "TEMPLATE",
        "EFFECT",
        "TRANSITION",
        "RENDER_INPUT",
        "FAILURE",
    }
    registered_domains = {d.name for d in GovernedDomain}
    missing = mandatory_domains - registered_domains
    assert not missing, f"Missing mandatory governed domains: {missing}"

    for dom_name in mandatory_domains:
        domain = GovernedDomain[dom_name]
        entry = ContractAuthorityMatrix.get_entry(domain)
        assert entry is not None, f"Domain {dom_name} has no matrix entry"
        assert entry.migration_owner is not None, f"Domain {dom_name} has no migration owner"
        assert entry.unknown_field_policy is not None, f"Domain {dom_name} has no unknown field policy"
        assert entry.contract_version is not None, f"Domain {dom_name} has no contract version"


def test_future_domains_have_explicit_migration_owners():
    """Verifies that deferred domains have explicit migration owners and decisions."""
    from scripts.core.authority_matrix import ContractAuthorityMatrix, GovernedDomain

    expected_migration_owners = {
        GovernedDomain.MANIFEST: "S11",
        GovernedDomain.BLUEPRINT: "S12",
        GovernedDomain.AUDIO: "S12",
        GovernedDomain.TEMPLATE: "S15",
        GovernedDomain.EFFECT: "S15",
        GovernedDomain.TRANSITION: "S15",
        GovernedDomain.RENDER_INPUT: "S17",
    }

    for domain, expected_owner in expected_migration_owners.items():
        entry = ContractAuthorityMatrix.get_entry(domain)
        assert entry.migration_owner == expected_owner, (
            f"Domain {domain.value} expected migration owner {expected_owner}, "
            f"got {entry.migration_owner}"
        )


def test_no_parallel_dependency_authority_in_review_or_recovery():
    """
    Architecture Guard: ReviewService and RecoveryPlanner must NOT maintain
    a competing, un-integrated dependency graph.
    """
    import inspect
    from scripts.core import review_service, recovery_engine

    # Ensure ReviewService references the centralized graph or its semantic nodes
    rs_source = inspect.getsource(review_service)
    re_source = inspect.getsource(recovery_engine)

    assert "ArtifactDependencyGraph" in rs_source or "ArtifactKind" in rs_source, (
        "ReviewService must integrate with the centralized ArtifactDependencyGraph or ArtifactKind."
    )
    assert "ArtifactDependencyGraph" in re_source or "ArtifactKind" in re_source, (
        "RecoveryEngine must integrate with the centralized ArtifactDependencyGraph or ArtifactKind."
    )


def test_review_domain_canonical_authority_is_review_service_and_marker_is_legacy():
    """
    Architecture Guard: ReviewService is the sole canonical authority for REVIEW domain.
    .studio_approved is strictly a LEGACY marker, never a canonical authority or decision writer.
    """
    from scripts.core.authority_matrix import (
        ContractAuthorityMatrix,
        GovernedDomain,
        RepresentationRole,
    )

    review_entry = ContractAuthorityMatrix.get_entry(GovernedDomain.REVIEW)
    assert review_entry.canonical_authority == "scripts.core.review_service.ReviewService"

    # Canonical representation must be ReviewService
    canonical_reps = [r for r in review_entry.representations if r.role == RepresentationRole.CANONICAL]
    assert len(canonical_reps) == 1
    assert canonical_reps[0].name == "ReviewService"

    # Legacy marker must be registered with role LEGACY
    legacy_reps = [r for r in review_entry.representations if r.role == RepresentationRole.LEGACY]
    assert len(legacy_reps) == 1
    marker_rep = legacy_reps[0]
    assert marker_rep.name == "LegacyStudioApprovedMarker"
    assert marker_rep.path == ".studio_approved"
    assert not marker_rep.is_generated
    assert "Legacy" in marker_rep.description or "non-authoritative" in marker_rep.description

