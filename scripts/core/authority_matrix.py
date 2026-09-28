"""
Contract Authority Matrix & Version Policy (S10).

Provides the single machine-readable source of truth for:
- Governed domains across the video workspace.
- Canonical authority specification for each domain.
- Generated vs Canonical vs Adapter representations.
- Unknown field policies (REJECT, IGNORE, PRESERVE).
- Versioning semantics and migration ownership.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, ConfigDict


class GovernedDomain(str, Enum):
    STATE = "STATE"
    REVIEW = "REVIEW"
    ARTIFACT_EVIDENCE = "ARTIFACT_EVIDENCE"
    MANIFEST = "MANIFEST"
    BLUEPRINT = "BLUEPRINT"
    MEDIA_REFERENCE = "MEDIA_REFERENCE"
    AUDIO = "AUDIO"
    TEMPLATE = "TEMPLATE"
    EFFECT = "EFFECT"
    TRANSITION = "TRANSITION"
    RENDER_INPUT = "RENDER_INPUT"
    FAILURE = "FAILURE"


class RepresentationRole(str, Enum):
    CANONICAL = "CANONICAL"
    GENERATED = "GENERATED"
    ADAPTER = "ADAPTER"
    COMPATIBILITY = "COMPATIBILITY"
    LEGACY = "LEGACY"
    RUNTIME_DERIVED = "RUNTIME_DERIVED"


class UnknownFieldPolicy(str, Enum):
    REJECT = "REJECT"      # Fails schema validation if unexpected keys exist (strict)
    IGNORE = "IGNORE"      # Discards / passes through without validation error
    PRESERVE = "PRESERVE"  # Stores unmapped fields in metadata dictionary


class ContractRepresentation(BaseModel):
    model_config = ConfigDict(extra='ignore')

    name: str
    path: str
    format: str  # e.g., "python_pydantic", "typescript_zod", "json_schema", "json_registry"
    role: RepresentationRole
    is_generated: bool = False
    description: Optional[str] = None


class OwnerPackage(BaseModel):
    model_config = ConfigDict(extra='ignore')

    current: str
    target: str
    migration_owner: str


class ContractAuthorityEntry(BaseModel):
    model_config = ConfigDict(extra='ignore')

    domain: GovernedDomain
    canonical_authority: str
    canonical_path: Optional[str] = None
    contract_version: str = "1.0.0"
    schema_version: Optional[str] = "1.0"
    representations: List[ContractRepresentation] = Field(default_factory=list)
    generated_outputs: List[str] = Field(default_factory=list)
    consumers: List[str] = Field(default_factory=list)
    migration_policy: str
    unknown_field_policy: UnknownFieldPolicy
    compatibility_adapters: List[str] = Field(default_factory=list)
    owner_package: OwnerPackage
    validation_entrypoint: str

    @property
    def migration_owner(self) -> str:
        return self.owner_package.migration_owner


class ContractAuthorityMatrix:
    """
    Centralized, executable registry for contract governance.
    Enforces that every governed domain has exactly one canonical authority.
    """

    ENTRIES: Dict[GovernedDomain, ContractAuthorityEntry] = {
        GovernedDomain.STATE: ContractAuthorityEntry(
            domain=GovernedDomain.STATE,
            canonical_authority="scripts.core.state_model.ProjectState",
            canonical_path="projects/{id}/.pipeline_state.json",
            contract_version="1.0.0",
            schema_version="1.0",
            representations=[
                ContractRepresentation(
                    name="ProjectState",
                    path="scripts/core/state_model.py",
                    format="python_pydantic",
                    role=RepresentationRole.CANONICAL,
                    is_generated=False,
                    description="Pydantic models for project state, evidence ledger, and review bundles",
                ),
                ContractRepresentation(
                    name="state.schema.json",
                    path="schemas/state.schema.json",
                    format="json_schema",
                    role=RepresentationRole.COMPATIBILITY,
                    is_generated=False,
                    description="JSON Schema Draft-07 representation of pipeline state",
                ),
                ContractRepresentation(
                    name="PipelineStatusResponse",
                    path="api/schemas/pipeline.py",
                    format="fastapi_dto",
                    role=RepresentationRole.ADAPTER,
                    is_generated=False,
                    description="API response serialization adapter",
                ),
            ],
            generated_outputs=[],
            consumers=["scripts/pipeline.py", "scripts/core/state_store.py", "api/services/pipeline_service.py"],
            migration_policy="Additive schema versioning; backward-compatible fields default to None.",
            unknown_field_policy=UnknownFieldPolicy.IGNORE,
            compatibility_adapters=["api.schemas.pipeline"],
            owner_package=OwnerPackage(current="S05", target="S05-S10", migration_owner="S05"),
            validation_entrypoint="scripts.core.state_store.StateStore.load",
        ),

        GovernedDomain.REVIEW: ContractAuthorityEntry(
            domain=GovernedDomain.REVIEW,
            canonical_authority="scripts.core.review_service.ReviewService",
            canonical_path="projects/{id}/.pipeline_state.json#review_bundles",
            contract_version="1.0.0",
            schema_version="1.0",
            representations=[
                ContractRepresentation(
                    name="ReviewService",
                    path="scripts/core/review_service.py",
                    format="python_service",
                    role=RepresentationRole.CANONICAL,
                    is_generated=False,
                    description="Canonical authority for review bundle creation, approval, and authorization",
                ),
                ContractRepresentation(
                    name="GateReviewRouter",
                    path="api/routers/gates.py",
                    format="fastapi_dto",
                    role=RepresentationRole.ADAPTER,
                    is_generated=False,
                    description="HTTP API surface delegating review decisions to ReviewService",
                ),
                ContractRepresentation(
                    name="LegacyStudioApprovedMarker",
                    path=".studio_approved",
                    format="text_marker",
                    role=RepresentationRole.LEGACY,
                    is_generated=False,
                    description="Legacy filesystem marker; non-authoritative compatibility token only",
                ),
            ],
            generated_outputs=[],
            consumers=["scripts/render_project.py", "scripts/open_studio.py", "api/routers/gates.py"],
            migration_policy="ReviewBundle digests freeze referenced hashes; mutations invalidate prior decisions.",
            unknown_field_policy=UnknownFieldPolicy.IGNORE,
            compatibility_adapters=["api.routers.gates"],
            owner_package=OwnerPackage(current="S09", target="S09", migration_owner="S09"),
            validation_entrypoint="scripts.core.review_service.ReviewService.assert_render_authorized",
        ),

        GovernedDomain.ARTIFACT_EVIDENCE: ContractAuthorityEntry(
            domain=GovernedDomain.ARTIFACT_EVIDENCE,
            canonical_authority="scripts.core.evidence_matrix.RequiredEvidenceMatrix",
            canonical_path="projects/{id}/.pipeline_state.json#artifact_records",
            contract_version="1.0.0",
            schema_version="1.0",
            representations=[
                ContractRepresentation(
                    name="RequiredEvidencePolicy",
                    path="scripts/core/evidence_matrix.py",
                    format="python_policy",
                    role=RepresentationRole.CANONICAL,
                    is_generated=False,
                    description="Canonical matrix defining mandatory evidence items and validation levels per stage",
                ),
            ],
            generated_outputs=[],
            consumers=["scripts/core/lifecycle_service.py", "scripts/core/recovery_engine.py", "scripts/pipeline.py"],
            migration_policy="Evidence retention is cumulative; invalidation marks status=INVALIDATED without record erasure.",
            unknown_field_policy=UnknownFieldPolicy.IGNORE,
            compatibility_adapters=[],
            owner_package=OwnerPackage(current="S06/S07", target="S10", migration_owner="S06"),
            validation_entrypoint="scripts.core.evidence_matrix.RequiredEvidencePolicy.validate_required_evidence",
        ),

        GovernedDomain.MANIFEST: ContractAuthorityEntry(
            domain=GovernedDomain.MANIFEST,
            canonical_authority="scripts.core.manifest_model.ManifestV2",
            canonical_path="02_asset_manifest.json",
            contract_version="2.0.0",
            schema_version="2.0",
            representations=[
                ContractRepresentation(
                    name="ManifestV2",
                    path="scripts/core/manifest_model.py",
                    format="python_pydantic",
                    role=RepresentationRole.CANONICAL,
                    is_generated=False,
                    description="Pydantic models and semantic invariants for Manifest v2",
                ),
                ContractRepresentation(
                    name="manifest.v2.schema.json",
                    path="schemas/manifest.v2.schema.json",
                    format="json_schema",
                    role=RepresentationRole.COMPATIBILITY,
                    is_generated=False,
                    description="JSON Schema Draft-07 representation of Manifest v2",
                ),
                ContractRepresentation(
                    name="ManifestV2Schema",
                    path="contracts/manifest.ts",
                    format="typescript_zod",
                    role=RepresentationRole.ADAPTER,
                    is_generated=False,
                    description="TypeScript Zod schema for Manifest v2",
                ),
                ContractRepresentation(
                    name="AssetGateValidator",
                    path="scripts/gates/asset_gate.py",
                    format="python_validator",
                    role=RepresentationRole.ADAPTER,
                    is_generated=False,
                    description="Gate script evaluating manifest validity",
                ),
                ContractRepresentation(
                    name="LegacyManifest",
                    path="manifest.json",
                    format="json_file",
                    role=RepresentationRole.LEGACY,
                    is_generated=False,
                    description="Legacy unversioned manifest file path migrated via scripts/core/manifest_migration.py",
                ),
            ],
            generated_outputs=[],
            consumers=["scripts/gates/asset_gate.py", "scripts/generators/materialize_project.py", "api/routers/projects.py"],
            migration_policy="Manifest v2 is canonical. Legacy manifests are migrated via scripts/core/manifest_migration.py with idempotency.",
            unknown_field_policy=UnknownFieldPolicy.REJECT,
            compatibility_adapters=["scripts/core/manifest_migration.py", "contracts/manifest.ts"],
            owner_package=OwnerPackage(current="S11", target="Manifest v2", migration_owner="S11"),
            validation_entrypoint="scripts.core.manifest_loader.load_manifest",
        ),

        GovernedDomain.BLUEPRINT: ContractAuthorityEntry(
            domain=GovernedDomain.BLUEPRINT,
            canonical_authority="contracts.blueprint.BlueprintV2Schema",
            canonical_path="05_blueprint.json",
            contract_version="2.0.0",
            schema_version="2.0",
            representations=[
                ContractRepresentation(
                    name="BlueprintV2Schema",
                    path="contracts/blueprint.ts",
                    format="typescript_zod",
                    role=RepresentationRole.CANONICAL,
                    is_generated=False,
                    description="Authoritative Zod schema defining scenes, timings, AudioPlan, transitions, and style tokens",
                ),
                ContractRepresentation(
                    name="BlueprintV2",
                    path="scripts/core/blueprint_model.py",
                    format="python_pydantic",
                    role=RepresentationRole.ADAPTER,
                    is_generated=False,
                    description="Python Pydantic model for Blueprint v2 contract",
                ),
                ContractRepresentation(
                    name="blueprint.schema.json",
                    path="schemas/blueprint.schema.json",
                    format="json_schema",
                    role=RepresentationRole.GENERATED,
                    is_generated=True,
                    description="Generated JSON Schema produced by scripts/generators/generate_schema.ts",
                ),
                ContractRepresentation(
                    name="load_blueprint",
                    path="scripts/core/blueprint_loader.py",
                    format="python_validator",
                    role=RepresentationRole.ADAPTER,
                    is_generated=False,
                    description="Loader and validator enforcing identity, timings, and AudioPlan semantics",
                ),
                ContractRepresentation(
                    name="BlueprintResponse",
                    path="api/schemas/blueprint.py",
                    format="fastapi_dto",
                    role=RepresentationRole.COMPATIBILITY,
                    is_generated=False,
                    description="API response model for blueprint endpoint",
                ),
            ],
            generated_outputs=["schemas/blueprint.schema.json"],
            consumers=["scripts/gates/validate_blueprint.py", "scripts/generators/materialize_project.py", "scripts/gates/probe_qc.py", "scripts/gates/final_qc.py", "scripts/render_project.py"],
            migration_policy="Blueprint v2 and AudioPlan governed in S12. Legacy v1 blueprints migrated centrally via scripts/core/blueprint_migration.py.",
            unknown_field_policy=UnknownFieldPolicy.REJECT,
            compatibility_adapters=["scripts/core/blueprint_migration.py", "contracts/blueprint.ts"],
            owner_package=OwnerPackage(current="S12", target="Blueprint v2", migration_owner="S12"),
            validation_entrypoint="scripts.core.blueprint_loader.load_blueprint",
        ),

        GovernedDomain.MEDIA_REFERENCE: ContractAuthorityEntry(
            domain=GovernedDomain.MEDIA_REFERENCE,
            canonical_authority="scripts.generators.materialize_project.py",
            canonical_path="media_map.json",
            contract_version="1.0.0",
            schema_version="1.0",
            representations=[
                ContractRepresentation(
                    name="MaterializerMediaMap",
                    path="scripts/generators/materialize_project.py",
                    format="python_script",
                    role=RepresentationRole.CANONICAL,
                    is_generated=False,
                    description="Canonical generator mapping logical asset IDs to normalized media files",
                ),
                ContractRepresentation(
                    name="ASSET_INDEX.json",
                    path="ground-truth/ASSET_INDEX.json",
                    format="json_index",
                    role=RepresentationRole.RUNTIME_DERIVED,
                    is_generated=True,
                    description="System asset catalog indexing pre-bundled static assets",
                ),
            ],
            generated_outputs=["media_map.json"],
            consumers=["scripts/gates/probe_qc.py", "scripts/render_project.py", "scripts/core/review_service.py"],
            migration_policy="Media materialize redesign with atomic transactions scheduled for S13.",
            unknown_field_policy=UnknownFieldPolicy.PRESERVE,
            compatibility_adapters=[],
            owner_package=OwnerPackage(current="S04", target="Transactional Materializer", migration_owner="S13"),
            validation_entrypoint="scripts.generators.materialize_project.py",
        ),

        GovernedDomain.AUDIO: ContractAuthorityEntry(
            domain=GovernedDomain.AUDIO,
            canonical_authority="scripts.gates.audio_gate.py",
            canonical_path="04_timings.json",
            contract_version="1.0.0",
            schema_version="1.0",
            representations=[
                ContractRepresentation(
                    name="AudioGate",
                    path="scripts/gates/audio_gate.py",
                    format="python_validator",
                    role=RepresentationRole.CANONICAL,
                    is_generated=False,
                    description="Authoritative gate enforcing -16 LUFS voiceover, -24 LUFS SFX and duration limits",
                ),
                ContractRepresentation(
                    name="AudioArchitectureSpec",
                    path="references/AUDIO_ARCHITECTURE.md",
                    format="markdown_spec",
                    role=RepresentationRole.COMPATIBILITY,
                    is_generated=False,
                    description="Reference specification for multi-track audio bus mixing",
                ),
            ],
            generated_outputs=["04_timings.json"],
            consumers=["scripts/pipeline.py", "scripts/gates/taste_gate.py"],
            migration_policy="Full AudioPlan engine redesign scheduled for S12.",
            unknown_field_policy=UnknownFieldPolicy.IGNORE,
            compatibility_adapters=[],
            owner_package=OwnerPackage(current="S04", target="AudioPlan Engine", migration_owner="S12"),
            validation_entrypoint="scripts.gates.audio_gate.py",
        ),

        GovernedDomain.TEMPLATE: ContractAuthorityEntry(
            domain=GovernedDomain.TEMPLATE,
            canonical_authority="registry.template-registry-data.json",
            canonical_path="registry/template-registry-data.json",
            contract_version="1.0.0",
            schema_version="1.0",
            representations=[
                ContractRepresentation(
                    name="template-registry-data.json",
                    path="registry/template-registry-data.json",
                    format="json_catalog",
                    role=RepresentationRole.CANONICAL,
                    is_generated=False,
                    description="Sole authoritative machine-readable template registry metadata",
                ),
                ContractRepresentation(
                    name="TemplateRegistry",
                    path="registry/template-registry.tsx",
                    format="typescript_registry",
                    role=RepresentationRole.RUNTIME_DERIVED,
                    is_generated=False,
                    description="Remotion template registry mapping component names to render implementations",
                ),
                ContractRepresentation(
                    name="template-aliases.ts",
                    path="registry/template-aliases.ts",
                    format="typescript_aliases",
                    role=RepresentationRole.GENERATED,
                    is_generated=True,
                    description="Derived alias mapping generated from single data authority",
                ),
                ContractRepresentation(
                    name="template_catalog.json",
                    path="ground-truth/template_catalog.json",
                    format="json_catalog",
                    role=RepresentationRole.COMPATIBILITY,
                    is_generated=False,
                    description="Ground truth catalog of available templates and metadata",
                ),
                ContractRepresentation(
                    name="template-runtime-contract.json",
                    path="contracts/template-runtime-contract.json",
                    format="json_contract",
                    role=RepresentationRole.GENERATED,
                    is_generated=True,
                    description="Authoritative machine-readable contract generated from runtime registry",
                ),
                ContractRepresentation(
                    name="template_intelligence_matrix.json",
                    path="template_intelligence_matrix.json",
                    format="json_matrix",
                    role=RepresentationRole.GENERATED,
                    is_generated=True,
                    description="Matrix generated by scripts/generators/generate_matrix.ts",
                ),
            ],
            generated_outputs=["contracts/template-runtime-contract.json", "template_intelligence_matrix.json"],
            consumers=[
                "scripts/gates/validate_blueprint.py",
                "scripts/core/materializer.py",
                "scripts/validators/inspect_template.py",
                "scripts/validators/template_lint.py",
            ],
            migration_policy="S15 Canonical Template Identity: single authority Runtime Registry -> generated template-runtime-contract.json.",
            unknown_field_policy=UnknownFieldPolicy.IGNORE,
            compatibility_adapters=["scripts/validators/inspect_template.py"],
            owner_package=OwnerPackage(current="registry", target="Template Engine Registry", migration_owner="S15"),
            validation_entrypoint="scripts.generators.generate_template_contract.py",
        ),

        GovernedDomain.EFFECT: ContractAuthorityEntry(
            domain=GovernedDomain.EFFECT,
            canonical_authority="registry.effects-catalog.ts",
            canonical_path="registry/effects-catalog.ts",
            contract_version="1.0.0",
            schema_version="1.0",
            representations=[
                ContractRepresentation(
                    name="EffectsCatalog",
                    path="registry/effects-catalog.ts",
                    format="typescript_catalog",
                    role=RepresentationRole.CANONICAL,
                    is_generated=False,
                    description="Catalog of visual shaders, particle systems, and ambient overlays",
                ),
                ContractRepresentation(
                    name="EngineBridge",
                    path="templates/effects/engine-bridge.tsx",
                    format="typescript_adapter",
                    role=RepresentationRole.ADAPTER,
                    is_generated=False,
                    description="Runtime bridge integrating engine effects into composition trees",
                ),
            ],
            generated_outputs=[],
            consumers=["templates/effects/engine-bridge.tsx"],
            migration_policy="Effects contract hardening scheduled for S15.",
            unknown_field_policy=UnknownFieldPolicy.IGNORE,
            compatibility_adapters=["templates/effects/engine-bridge.tsx"],
            owner_package=OwnerPackage(current="registry", target="EngineBridge v2", migration_owner="S15"),
            validation_entrypoint="templates.effects.engine-bridge.tsx",
        ),

        GovernedDomain.TRANSITION: ContractAuthorityEntry(
            domain=GovernedDomain.TRANSITION,
            canonical_authority="contracts.animations.ts",
            canonical_path="contracts/animations.ts",
            contract_version="1.0.0",
            schema_version="1.0",
            representations=[
                ContractRepresentation(
                    name="AnimationContracts",
                    path="contracts/animations.ts",
                    format="typescript_zod",
                    role=RepresentationRole.CANONICAL,
                    is_generated=False,
                    description="Zod schema defining transition types, easings, and duration limits",
                ),
                ContractRepresentation(
                    name="TransitionComponents",
                    path="templates/effects/*Transition.tsx",
                    format="react_components",
                    role=RepresentationRole.RUNTIME_DERIVED,
                    is_generated=False,
                    description="React Remotion transition implementations",
                ),
            ],
            generated_outputs=[],
            consumers=["templates/effects/engine-bridge.tsx", "scripts/gates/taste_gate.py"],
            migration_policy="Transition catalog consolidation scheduled for S15.",
            unknown_field_policy=UnknownFieldPolicy.IGNORE,
            compatibility_adapters=[],
            owner_package=OwnerPackage(current="contracts", target="Unified Transitions", migration_owner="S15"),
            validation_entrypoint="contracts.animations.ts",
        ),

        GovernedDomain.RENDER_INPUT: ContractAuthorityEntry(
            domain=GovernedDomain.RENDER_INPUT,
            canonical_authority="scripts.render_project.py",
            canonical_path="scripts/render_project.py",
            contract_version="1.0.0",
            schema_version="1.0",
            representations=[
                ContractRepresentation(
                    name="RenderProjectScript",
                    path="scripts/render_project.py",
                    format="python_script",
                    role=RepresentationRole.CANONICAL,
                    is_generated=False,
                    description="Canonical orchestrator translating project artifacts into Remotion CLI render calls",
                ),
                ContractRepresentation(
                    name="RenderRouter",
                    path="api/routers/render.py",
                    format="fastapi_dto",
                    role=RepresentationRole.ADAPTER,
                    is_generated=False,
                    description="API endpoint dispatching render tasks",
                ),
            ],
            generated_outputs=["out.mp4"],
            consumers=["scripts/pipeline.py", "api/routers/render.py"],
            migration_policy="Render payload encapsulation scheduled for S17.",
            unknown_field_policy=UnknownFieldPolicy.REJECT,
            compatibility_adapters=["api.services.pipeline_service"],
            owner_package=OwnerPackage(current="S04/S09", target="Render Payload Engine", migration_owner="S17"),
            validation_entrypoint="scripts.render_project.render_project",
        ),

        GovernedDomain.FAILURE: ContractAuthorityEntry(
            domain=GovernedDomain.FAILURE,
            canonical_authority="scripts.core.failure_model.FailureClassification",
            canonical_path="scripts/core/failure_model.py",
            contract_version="1.0.0",
            schema_version="1.0",
            representations=[
                ContractRepresentation(
                    name="FailureTaxonomyRegistry",
                    path="scripts/core/failure_model.py",
                    format="python_taxonomy",
                    role=RepresentationRole.CANONICAL,
                    is_generated=False,
                    description="Hierarchical failure taxonomy, categories, and retry decision rules",
                ),
                ContractRepresentation(
                    name="APIErrorResponses",
                    path="api/core/errors.py",
                    format="fastapi_errors",
                    role=RepresentationRole.ADAPTER,
                    is_generated=False,
                    description="HTTP status mapping for client errors",
                ),
            ],
            generated_outputs=[],
            consumers=["scripts/core/retry_policy.py", "scripts/core/recovery_engine.py", "scripts/pipeline.py"],
            migration_policy="Failure taxonomy defined in S08; immutable failure codes.",
            unknown_field_policy=UnknownFieldPolicy.IGNORE,
            compatibility_adapters=["api.core.errors"],
            owner_package=OwnerPackage(current="S08", target="S08", migration_owner="S08"),
            validation_entrypoint="scripts.core.failure_model.classify_failure",
        ),
    }

    @classmethod
    def get_entry(cls, domain: GovernedDomain) -> ContractAuthorityEntry:
        if domain not in cls.ENTRIES:
            raise KeyError(f"Domain {domain} is not registered in ContractAuthorityMatrix")
        return cls.ENTRIES[domain]

    @classmethod
    def get_all_entries(cls) -> List[ContractAuthorityEntry]:
        return list(cls.ENTRIES.values())

    @classmethod
    def get_canonical_authority(cls, domain: GovernedDomain) -> str:
        return cls.get_entry(domain).canonical_authority

    @classmethod
    def validate_matrix(cls) -> None:
        """
        Validates the integrity of the authority matrix:
        1. Every domain has exactly one CANONICAL representation.
        2. Generated representations are marked with is_generated=True and role=GENERATED.
        3. Canonical representations are NOT marked as generated.
        4. No duplicate entries or missing domains.
        """
        for domain in GovernedDomain:
            if domain not in cls.ENTRIES:
                raise ValueError(f"Domain {domain.value} is missing an authority entry")
            entry = cls.ENTRIES[domain]
            canonical_reps = [r for r in entry.representations if r.role == RepresentationRole.CANONICAL]
            if len(canonical_reps) != 1:
                raise ValueError(
                    f"Domain {domain.value} must have exactly one CANONICAL representation, found {len(canonical_reps)}"
                )
            for rep in entry.representations:
                if rep.role == RepresentationRole.CANONICAL and rep.is_generated:
                    raise ValueError(f"Canonical representation '{rep.name}' cannot be marked as generated")
                if rep.role == RepresentationRole.GENERATED and not rep.is_generated:
                    raise ValueError(f"Generated representation '{rep.name}' must have is_generated=True")
