"""
api/services/authoring_service.py — Production Authoring Domain Service.
S28-R14: Integrates Unified Authoring (AI + User + Templates) with SaaS Infrastructure.

Flow:
HTTP / Router
  ↓
TenantContext & Authorization
  ↓
AuthoringService
  ↓
AuthoringIdempotencyRepository (Durable Idempotency & Conflict Check)
  ↓
CanonicalDocumentRepository (Persistent Base Revision Check)
  ↓
UnifiedAuthoringSession Bridge (Typed Mutation Engine & Intent Planning)
  ↓
CanonicalDocumentRepository (Transactional CAS Commit to SQL + StorageService)
  ↓
Durable Events & ChangeSet Invalidation
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from api.core.errors import APIError, ProjectNotFoundError, RevisionConflictError
from scripts.core.authoring_idempotency_repository import (
    AuthoringIdempotencyRepository,
    IdempotencyConflictError,
)
from scripts.core.canonical_document_repository import (
    CanonicalDocumentRepository,
    DocumentValidationError,
)
from scripts.core.database import get_database_engine, TenantSecurityError
from scripts.core.security.principal import Role
from scripts.core.security.permissions import Action, AuthorizationPolicy, AccessDeniedError
from scripts.core.state_store import StateConflictError, StateNotFoundError
from scripts.core.tenant_model import TenantContext
from scripts.security.path_security import validate_project_id
from scripts.security.security import safe_subprocess

logger = logging.getLogger("clean_video.authoring_service")


class AuthoringService:
    """Domain service orchestrating production video authoring, mutations, and revisions."""

    _doc_repo = CanonicalDocumentRepository()
    _idemp_repo = AuthoringIdempotencyRepository()

    @classmethod
    def _compute_payload_hash(cls, payload: Any) -> str:
        serialized = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @classmethod
    def get_canonical_document(
        cls,
        project_id: str,
        tenant_context: TenantContext,
        revision: Optional[int] = None,
    ) -> Tuple[Dict[str, Any], int]:
        """Loads the authoritative canonical document under tenant context."""
        validate_project_id(project_id)
        return cls._doc_repo.get_document(
            workspace_id=tenant_context.workspace_id,
            project_id=project_id,
            revision=revision,
        )

    @classmethod
    def execute_authoring(
        cls,
        project_id: str,
        tenant_context: TenantContext,
        action: str,
        payload: Dict[str, Any],
        actor_id: str,
    ) -> Dict[str, Any]:
        """
        Authoritative transaction boundary for video mutations, AI intents, templates, undo/redo.
        """
        validate_project_id(project_id)
        ws_id = tenant_context.workspace_id

        # 1. Extract and validate parameters
        operation_id = payload.get("operation_id") or payload.get("request_id") or f"op_{hashlib.md5(os.urandom(16)).hexdigest()[:12]}"
        base_revision = payload.get("base_revision")

        if base_revision is None and action in ("execute_request", "undo", "redo", "apply_intent", "batch"):
            # If not provided, fetch current revision to verify
            _, curr_rev = cls._doc_repo.get_document(workspace_id=ws_id, project_id=project_id)
            base_revision = curr_rev

        base_revision = int(base_revision if base_revision is not None else 0)

        # 2. Durable Idempotency Check (Cross-Process / Cross-Worker Safe)
        payload_hash = cls._compute_payload_hash(payload)
        claim_status, cached_res = cls._idemp_repo.try_claim_leader(
            workspace_id=ws_id,
            project_id=project_id,
            operation_id=operation_id,
            operation_type=action,
            base_revision=base_revision,
            payload_hash=payload_hash,
        )

        if claim_status == "COMPLETED" and cached_res is not None:
            logger.info(f"Replaying cached idempotent authoring result for '{operation_id}'")
            return {**cached_res, "idempotent": True}

        # 3. Load Current Canonical Document at Base Revision
        try:
            curr_doc, curr_rev = cls._doc_repo.get_document(workspace_id=ws_id, project_id=project_id)
        except StateNotFoundError:
            cls._idemp_repo.mark_failed(ws_id, project_id, operation_id, {"error": "PROJECT_NOT_FOUND"})
            raise ProjectNotFoundError(project_id)

        # Optimistic Concurrency Check
        if base_revision != curr_rev:
            diag = {
                "code": "REVISION_CONFLICT",
                "message": (
                    f"REVISION_CONFLICT: Expected revision {base_revision}, "
                    f"but persistent document is currently at revision {curr_rev}."
                ),
                "details": {
                    "expected_revision": base_revision,
                    "actual_revision": curr_rev,
                    "operation_id": operation_id,
                },
            }
            cls._idemp_repo.mark_failed(ws_id, project_id, operation_id, diag)
            raise RevisionConflictError(
                expected_revision=base_revision,
                actual_revision=curr_rev,
                message=diag["message"],
            )

        # 4. Invoke Unified Authoring Engine Bridge
        bridge_script = Path(__file__).resolve().parent.parent.parent / "scripts" / "execute_authoring_mutation.ts"
        bridge_input = {
            "action": "execute_request" if action in ("apply_intent", "apply_mutation", "execute_request", "batch") else action,
            "document": curr_doc,
            "request": payload.get("request") or payload,
            "template_spec": payload.get("template_spec"),
        }

        # Ensure request has required fields
        if "request" in bridge_input and isinstance(bridge_input["request"], dict):
            req_dict = bridge_input["request"]
            req_dict.setdefault("request_id", operation_id)
            req_dict.setdefault("actor", "ai" if "ai" in str(req_dict.get("actor", "")).lower() else "user")
            req_dict.setdefault("base_revision", base_revision)
            req_dict.setdefault("project_id", project_id)

        try:
            input_json = json.dumps(bridge_input, ensure_ascii=False)
            npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
            res = safe_subprocess(
                [npx_cmd, "tsx", str(bridge_script)],
                input=input_json,
                capture_output=True,
                text=True,
                check=True,
            )
            bridge_output = json.loads(res.stdout.strip())
        except Exception as e:
            err_msg = f"Authoring bridge execution error: {e}"
            logger.error(err_msg)
            fail_diag = {
                "code": "AUTHORING_EXECUTION_FAILED",
                "message": err_msg,
            }
            cls._idemp_repo.mark_failed(ws_id, project_id, operation_id, fail_diag)
            raise APIError(message=err_msg, status_code=500)

        # 5. Check Bridge Output
        if not bridge_output.get("success", False):
            diag = bridge_output.get("error") or (bridge_output.get("diagnostics") and bridge_output["diagnostics"][0]) or {
                "code": "AUTHORING_REJECTED",
                "message": "Mutation was rejected by canonical authoring validation",
            }
            cls._idemp_repo.mark_failed(ws_id, project_id, operation_id, diag)
            return {
                "success": False,
                "operation_id": operation_id,
                "base_revision": base_revision,
                "result_revision": curr_rev,
                "blueprint": curr_doc,
                "changeset": bridge_output.get("changeset"),
                "applied_mutation_ids": [],
                "diagnostics": bridge_output.get("diagnostics", [diag]),
                "error": diag,
                "idempotent": False,
            }

        new_blueprint = bridge_output["blueprint"]

        # 6. Transactional CAS Commit to SQL + StorageService
        try:
            provenance = {
                "actor_id": actor_id,
                "operation_id": operation_id,
                "action": action,
                "applied_mutation_ids": bridge_output.get("applied_mutation_ids", []),
            }
            committed_doc, next_rev, storage_key = cls._doc_repo.commit_candidate(
                workspace_id=ws_id,
                project_id=project_id,
                expected_revision=base_revision,
                candidate_doc=new_blueprint,
                actor_id=actor_id,
                operation_id=operation_id,
                provenance=provenance,
            )
        except StateConflictError as sce:
            cls._idemp_repo.mark_failed(ws_id, project_id, operation_id, {"error": "REVISION_CONFLICT", "details": str(sce)})
            raise RevisionConflictError(
                expected_revision=base_revision,
                actual_revision=-1,
                message=str(sce),
            )
        except DocumentValidationError as dve:
            cls._idemp_repo.mark_failed(ws_id, project_id, operation_id, {"error": "INVALID_DOCUMENT", "details": str(dve)})
            raise APIError(message=str(dve), status_code=400)

        # 7. Finalize and Mark Idempotency Record
        final_result = {
            "success": True,
            "operation_id": operation_id,
            "base_revision": base_revision,
            "result_revision": next_rev,
            "blueprint": committed_doc,
            "storage_key": storage_key,
            "changeset": bridge_output.get("changeset"),
            "applied_mutation_ids": bridge_output.get("applied_mutation_ids", []),
            "diagnostics": bridge_output.get("diagnostics", []),
            "provenance": provenance,
            "idempotent": False,
        }

        cls._idemp_repo.mark_completed(
            workspace_id=ws_id,
            project_id=project_id,
            operation_id=operation_id,
            result_revision=next_rev,
            result_payload=final_result,
        )

        return final_result
