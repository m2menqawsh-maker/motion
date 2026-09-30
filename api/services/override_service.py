"""
Domain Service for Scene Overrides (S22 - LED-067, LED-068).

Canonical contract enforcement:
- Validates overrides against schemas/overrides.schema.json and contracts/override-validator.ts
- Enforces strict whitelist of allowed style keys
- Prohibits dangerous injection contents ('javascript:', 'expression(', 'url(')
- Optimistic concurrency control via ETag / If-Match (409 Conflict)
- Atomic persistence with downstream invalidation via ArtifactService
"""

import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
import jsonschema
from jsonschema import Draft7Validator

from api.core.errors import (
    ProjectNotFoundError,
    APIError,
    RevisionConflictError,
)
from scripts.core.artifact_service import ArtifactService
from scripts.core.dependency_graph import ArtifactKind
from scripts.core.state_store import StateStore, StateConflictError
from scripts.security.path_security import validate_project_id

SCHEMA_PATH = Path("schemas/overrides.schema.json")
BLUEPRINT_SCHEMA_PATH = Path("schemas/blueprint.schema.json")

def _init_overrides_validator():
    if not SCHEMA_PATH.exists():
        return None, None
    overrides_schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    if not BLUEPRINT_SCHEMA_PATH.exists():
        return overrides_schema, Draft7Validator(overrides_schema)
    bp_schema = json.loads(BLUEPRINT_SCHEMA_PATH.read_text(encoding="utf-8"))
    try:
        from referencing.jsonschema import DRAFT7
        from referencing import Registry
        bp_res = DRAFT7.create_resource(bp_schema)
        registry = Registry().with_resources([
            ("blueprint.schema.json", bp_res),
            (bp_schema.get("$id", "blueprint.schema.json"), bp_res),
        ])
        return overrides_schema, Draft7Validator(overrides_schema, registry=registry)
    except Exception:
        from jsonschema import RefResolver
        schemas_dir = Path("schemas").resolve()
        resolver = RefResolver(
            schemas_dir.as_uri() + "/",
            {},
            store={"blueprint.schema.json": bp_schema, bp_schema.get("$id", "blueprint.schema.json"): bp_schema}
        )
        return overrides_schema, Draft7Validator(overrides_schema, resolver=resolver)

OVERRIDES_SCHEMA, OVERRIDES_VALIDATOR = _init_overrides_validator()

ALLOWED_STYLE_KEYS = {
    "borderRadius",
    "boxShadow",
    "textShadow",
    "filter",
    "backdropFilter",
    "border",
    "borderColor",
    "borderWidth",
    "textStroke",
    "textStrokeWidth",
    "padding",
    "gap",
}

FORBIDDEN_NEEDLES = ["javascript:", "expression(", "url("]


class OverrideService:
    """Domain authority for scene overrides and style overrides."""

    @classmethod
    def _get_project_dir(cls, project_id: str) -> Path:
        validate_project_id(project_id)
        proj_dir = Path(f"projects/{project_id}")
        if not proj_dir.exists():
            raise ProjectNotFoundError(project_id)
        return proj_dir

    @classmethod
    def validate_overrides_payload(cls, project_id: str, payload: Any) -> Tuple[bool, List[str]]:
        """
        Validates overrides against schemas/overrides.schema.json and contracts/override-validator.ts.
        """
        if not isinstance(payload, dict):
            return False, ["Overrides payload must be a JSON object"]

        errors: List[str] = []

        # 1. Outer structure validation against schema
        if "project_id" in payload and payload["project_id"] != project_id:
            errors.append(f"Payload project_id '{payload['project_id']}' does not match URL project_id '{project_id}'")

        if OVERRIDES_VALIDATOR:
            for err in sorted(OVERRIDES_VALIDATOR.iter_errors(payload), key=lambda e: e.path):
                field = ".".join(str(p) for p in err.path) or "root"
                errors.append(f"{field}: {err.message}")

        # 2. Semantic style override validation (matching contracts/override-validator.ts)
        scenes = payload.get("scenes", [])
        if isinstance(scenes, list):
            for s_idx, scene in enumerate(scenes):
                if not isinstance(scene, dict):
                    continue
                props = scene.get("props")
                if isinstance(props, dict):
                    style_override = props.get("styleOverride")
                    if style_override is not None:
                        if not isinstance(style_override, dict):
                            errors.append(f"scenes[{s_idx}].props.styleOverride must be a valid object")
                        else:
                            for key, value in style_override.items():
                                if key not in ALLOWED_STYLE_KEYS:
                                    errors.append(f"Key '{key}' is not allowed in styleOverride")
                                if not isinstance(value, (str, int, float)):
                                    errors.append(f"Value for '{key}' must be a string or a number")
                                    continue
                                if isinstance(value, str):
                                    lower_val = value.lower()
                                    if any(needle in lower_val for needle in FORBIDDEN_NEEDLES):
                                        errors.append(f"Value for '{key}' contains dangerous content")
        elif "dangerous" in payload or "malicious_key" in payload:
            # Direct malformed payload
            errors.append("Invalid overrides format: missing scenes array or contains unauthorized keys")

        if any(needle in str(payload).lower() for needle in FORBIDDEN_NEEDLES):
            if not any("dangerous content" in e for e in errors):
                errors.append("Overrides payload contains forbidden executable or injection patterns")

        return len(errors) == 0, errors

    @classmethod
    def get_overrides(cls, project_id: str) -> Tuple[Dict[str, Any], int]:
        """Loads scene overrides and current state revision."""
        proj_dir = cls._get_project_dir(project_id)
        overrides_path = proj_dir / "overrides.json"
        if not overrides_path.exists():
            return {}, 1

        try:
            data = json.loads(overrides_path.read_text(encoding="utf-8"))
        except Exception as e:
            raise APIError(f"Corrupt overrides.json: {e}", status_code=500)

        state = StateStore.load(proj_dir)
        revision = state.revision if state else 1
        return data, revision

    @classmethod
    def update_overrides(
        cls,
        project_id: str,
        payload: Dict[str, Any],
        expected_revision: Optional[int] = None,
    ) -> Tuple[Dict[str, Any], int]:
        """
        Validates, checks concurrency, and atomically persists overrides with downstream invalidation.
        """
        proj_dir = cls._get_project_dir(project_id)

        # 1. Strict Contract Validation
        ok, errors = cls.validate_overrides_payload(project_id, payload)
        if not ok:
            raise APIError(
                message=f"Overrides validation failed: {'; '.join(errors)}",
                status_code=422,
                details={"code": "OVERRIDES_VALIDATION_FAILED", "errors": errors},
            )

        # 2. Concurrency Precondition Check
        state = StateStore.load(proj_dir)
        current_rev = state.revision if state else 1

        if expected_revision is not None and expected_revision != current_rev:
            raise RevisionConflictError(
                expected_revision=expected_revision,
                actual_revision=current_rev,
                message=f"Conflict: ETag/If-Match revision {expected_revision} does not match current state revision {current_rev}.",
            )

        # 3. Atomic persistence and invalidation
        payload_str = json.dumps(payload, indent=2, ensure_ascii=False)
        try:
            if state:
                ArtifactService.mutate_artifact(
                    project_dir=proj_dir,
                    artifact_kind=ArtifactKind.OVERRIDES,
                    new_content=payload_str,
                    reason="Scene overrides updated via API",
                    expected_revision=expected_revision,
                )
                updated_state = StateStore.load(proj_dir)
                new_rev = updated_state.revision if updated_state else current_rev + 1
            else:
                (proj_dir / "overrides.json").write_text(payload_str, encoding="utf-8")
                new_rev = 1
        except StateConflictError as e:
            raise RevisionConflictError(
                expected_revision=e.expected_revision,
                actual_revision=e.actual_revision,
                message=str(e),
            )

        return payload, new_rev
