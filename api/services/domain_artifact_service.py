"""
Domain Service for Project Artifacts & Reports (S22 - LED-064).

Canonical domain-oriented reader and inventory for project artifacts:
- Uses canonical loaders (load_manifest, load_blueprint)
- Disallows arbitrary raw file paths or traversal
- Surfaces artifact verification evidence, hash, size, and status
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from api.core.errors import ProjectNotFoundError, ArtifactNotFoundError, APIError
from scripts.core.blueprint_loader import load_blueprint
from scripts.core.dependency_graph import ArtifactKind
from scripts.core.manifest_loader import load_manifest
from scripts.core.state_store import StateStore
from scripts.security.path_security import validate_project_id


class DomainArtifactService:
    """Domain service for reading and inventorying governed artifacts."""

    @classmethod
    def _get_project_dir(cls, project_id: str) -> Path:
        validate_project_id(project_id)
        proj_dir = Path(f"projects/{project_id}")
        if not proj_dir.exists():
            raise ProjectNotFoundError(project_id)
        return proj_dir

    @classmethod
    def get_inventory(cls, project_id: str) -> List[Dict[str, Any]]:
        """Returns inventory of governed project artifacts."""
        proj_dir = cls._get_project_dir(project_id)
        state = StateStore.load(proj_dir)

        evidence_map = {}
        if state:
            for rec in state.artifact_records:
                evidence_map[rec.path] = rec

        inventory = []
        for kind in ArtifactKind:
            fname = kind.value
            fpath = proj_dir / fname
            exists = fpath.exists()
            rec = evidence_map.get(fname)

            size_bytes = fpath.stat().st_size if exists else 0
            if rec:
                status_val = rec.status.value if hasattr(rec.status, "value") else str(rec.status)
                val_level = rec.validation.value if hasattr(rec.validation, "value") else str(rec.validation)
                sha = rec.sha256 or (StateStore._compute_sha256(fpath) if exists else None)
                up_time = getattr(rec, "recorded_at", None) or getattr(rec, "invalidated_at", None)
            else:
                status_val = "PRESENT" if exists else "MISSING"
                val_level = "NONE"
                sha = StateStore._compute_sha256(fpath) if exists else None
                up_time = None

            inventory.append({
                "kind": kind.name.lower(),
                "filename": fname,
                "status": status_val,
                "size_bytes": size_bytes,
                "sha256": sha,
                "validation_level": val_level,
                "updated_at": up_time,
            })

        return inventory

    @classmethod
    def read_artifact(cls, project_id: str, kind_identifier: str) -> Tuple[Any, str, int, Optional[str]]:
        """
        Reads and canonically parses a governed project artifact.
        Returns: (parsed_content, filename, revision, sha256)
        """
        proj_dir = cls._get_project_dir(project_id)
        kind = ArtifactKind.from_string(kind_identifier)
        if not kind:
            raise ArtifactNotFoundError(artifact_kind=kind_identifier, project_id=project_id)

        filename = kind.value
        fpath = proj_dir / filename
        if not fpath.exists():
            raise ArtifactNotFoundError(artifact_kind=kind_identifier, project_id=project_id)

        state = StateStore.load(proj_dir)
        revision = state.revision if state else 1
        sha = StateStore._compute_sha256(fpath)

        # Canonical Loaders based on ArtifactKind
        if kind == ArtifactKind.MANIFEST:
            manifest = load_manifest(fpath, expected_project_id=project_id, allow_migrate=True)
            content = manifest.to_dict()
        elif kind == ArtifactKind.BLUEPRINT:
            bp = load_blueprint(fpath)
            content = bp.model_dump()
        elif kind in (ArtifactKind.TIMINGS, ArtifactKind.PROBE_REPORT, ArtifactKind.FINAL_QC, ArtifactKind.BRAND, ArtifactKind.OVERRIDES):
            try:
                content = json.loads(fpath.read_text(encoding="utf-8"))
            except Exception as e:
                raise APIError(f"Corrupt artifact {filename}: {e}", status_code=500)
        else:
            # Text / Plan / Markdown
            content = fpath.read_text(encoding="utf-8")

        return content, filename, revision, sha
