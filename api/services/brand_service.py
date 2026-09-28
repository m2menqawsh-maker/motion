"""
Domain Service for Brand Identity (S22 - LED-066, LED-068).

Canonical contract enforcement:
- Validates brand payloads against schemas/brand.schema.json (contracts/brand.ts)
- Rejects unvalidated/unknown fields before writing to disk (Zero side effects on error)
- Optimistic concurrency control via ETag / If-Match (409 Conflict on revision mismatch)
- Atomic persistence with downstream invalidation via ArtifactService
"""

import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
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

SCHEMA_PATH = Path("schemas/brand.schema.json")
if SCHEMA_PATH.exists():
    BRAND_SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    BRAND_VALIDATOR = Draft7Validator(BRAND_SCHEMA)
else:
    BRAND_SCHEMA = None
    BRAND_VALIDATOR = None


class BrandService:
    """Domain authority for project brand kit and identity."""

    @classmethod
    def _get_project_dir(cls, project_id: str) -> Path:
        validate_project_id(project_id)
        proj_dir = Path(f"projects/{project_id}")
        if not proj_dir.exists():
            raise ProjectNotFoundError(project_id)
        return proj_dir

    @classmethod
    def get_brand(cls, project_id: str) -> Tuple[Dict[str, Any], int]:
        """
        Loads the brand configuration and current state revision.
        Returns: (brand_dict, revision)
        """
        proj_dir = cls._get_project_dir(project_id)
        brand_path = proj_dir / "brand.json"
        if not brand_path.exists():
            raise APIError("Brand not found", status_code=404)

        try:
            brand_data = json.loads(brand_path.read_text(encoding="utf-8"))
        except Exception as e:
            raise APIError(f"Corrupt brand.json: {e}", status_code=500)

        state = StateStore.load(proj_dir)
        revision = state.revision if state else 1
        return brand_data, revision

    @classmethod
    def validate_brand_payload(cls, payload: Any) -> Tuple[bool, list[str]]:
        """Validates payload strictly against schemas/brand.schema.json."""
        if not isinstance(payload, dict):
            return False, ["Brand payload must be a JSON object"]

        if BRAND_VALIDATOR:
            errors = []
            for err in sorted(BRAND_VALIDATOR.iter_errors(payload), key=lambda e: e.path):
                field = ".".join(str(p) for p in err.path) or "root"
                errors.append(f"{field}: {err.message}")
            if errors:
                return False, errors

        return True, []

    @classmethod
    def update_brand(
        cls,
        project_id: str,
        payload: Dict[str, Any],
        expected_revision: Optional[int] = None,
    ) -> Tuple[Dict[str, Any], int]:
        """
        Validates, checks concurrency, and atomically persists brand update with downstream invalidation.
        """
        proj_dir = cls._get_project_dir(project_id)

        # 1. Strict Schema Validation (Zero side-effects on failure)
        ok, errors = cls.validate_brand_payload(payload)
        if not ok:
            raise APIError(
                message=f"Brand validation failed: {'; '.join(errors)}",
                status_code=422,
                details={"code": "BRAND_VALIDATION_FAILED", "errors": errors},
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
                    artifact_kind=ArtifactKind.BRAND,
                    new_content=payload_str,
                    reason="Brand kit updated via API",
                    expected_revision=expected_revision,
                )
                updated_state = StateStore.load(proj_dir)
                new_rev = updated_state.revision if updated_state else current_rev + 1
            else:
                # Project directory without initialized state
                (proj_dir / "brand.json").write_text(payload_str, encoding="utf-8")
                new_rev = 1
        except StateConflictError as e:
            raise RevisionConflictError(
                expected_revision=e.expected_revision,
                actual_revision=e.actual_revision,
                message=str(e),
            )

        return payload, new_rev
