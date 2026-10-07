"""
scripts/core/template_registry_publisher.py
===========================================
Canonical Template Registry Publisher, Staging Engine, and Atomic Rollback Authority (S28-07E).

Single Source of Truth:
- registry/template-registry-data.json is the CANONICAL machine-readable authority.
- contracts/template-runtime-contract.json and registry/template-aliases.ts are GENERATED derivatives.
- registry/template-registry.tsx is the concrete Remotion component binding authority.
- ground-truth/template_catalog.json is the compatibility catalog.
- templates/<category>/<ComponentName>.tsx is the production component package.

Guarantees:
- Zero AI mutation rights: only invoked by authoritative PromotionService.
- Hermetic Staging: all outputs are prepared and validated in isolated staging before commit.
- Atomic Publication & Rollback Journal: any failure before, during, or after commit restores exact previous canonical bytes.
- Deterministic Output: sorted keys, stable formatting, canonical indentation.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from creative_governance.candidates.errors import (
    PromotionCollisionError,
    PromotionError,
    PromotionRollbackError,
    PromotionSecurityError,
)
from ai.contracts.creative.template_candidate import TemplateCandidate
from scripts.generators.generate_template_contract import (
    CANONICAL_ID_REGEX,
    build_template_contract,
    serialize_aliases_ts,
    serialize_contract_deterministic,
)

ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class StagedPublication:
    """Encapsulates all artifacts materialized in the isolated staging directory."""
    stage_dir: Path
    target_template_id: str
    component_name: str
    rel_file_path: str
    registry_category: str
    catalog_type: str
    pre_publish_registry_hash: str
    staged_source_path: Path
    staged_registry_data_path: Path
    staged_contract_path: Path
    staged_aliases_path: Path
    staged_registry_tsx_path: Path
    staged_catalog_path: Path


@dataclass
class RollbackJournal:
    """Tracks pre-mutation file states for atomic rollback on failure."""
    snapshots: Dict[Path, Optional[bytes]] = field(default_factory=dict)

    def record_pre_state(self, path: Path) -> None:
        if path not in self.snapshots:
            if path.exists():
                self.snapshots[path] = path.read_bytes()
            else:
                self.snapshots[path] = None


class TemplateRegistryPublisher:
    """
    Authoritative low-level publisher for canonical template mutations.
    Enforces identity policies, isolated staging, consistency verification,
    and journaled atomic commits and rollbacks.
    """

    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        self.workspace_root = (workspace_root or ROOT).resolve()
        self.registry_data_path = self.workspace_root / "registry" / "template-registry-data.json"
        self.registry_tsx_path = self.workspace_root / "registry" / "template-registry.tsx"
        self.contract_path = self.workspace_root / "contracts" / "template-runtime-contract.json"
        self.aliases_path = self.workspace_root / "registry" / "template-aliases.ts"
        self.catalog_path = self.workspace_root / "ground-truth" / "template_catalog.json"
        self.templates_dir = self.workspace_root / "templates"

    # =========================================================================
    # 1. IDENTITY & PATH VALIDATION
    # =========================================================================

    def validate_target_identity(self, target_template_id: str, allow_existing: bool = False) -> None:
        """
        Enforces canonical naming policy (lowercase kebab-case alphanumeric).
        Rejects path traversal (.., /, \\) and existing template/alias collisions.
        """
        if not target_template_id or not isinstance(target_template_id, str):
            raise PromotionSecurityError(f"Target template ID must be a non-empty string. Got '{target_template_id}'")

        if target_template_id.strip() != target_template_id:
            raise PromotionSecurityError(f"Target template ID cannot have leading/trailing whitespace: '{target_template_id}'")

        # Path traversal guard
        if ".." in target_template_id or "/" in target_template_id or "\\" in target_template_id:
            raise PromotionSecurityError(f"Path traversal detected in target template ID: '{target_template_id}'")

        # Canonical ID naming regex
        if not CANONICAL_ID_REGEX.match(target_template_id):
            raise PromotionSecurityError(
                f"Target template ID '{target_template_id}' violates canonical naming rule regex '{CANONICAL_ID_REGEX.pattern}'. "
                f"Must be strictly lowercase kebab-case."
            )

        if not allow_existing:
            # Collision check against existing registry data
            if self.registry_data_path.exists():
                try:
                    data = json.loads(self.registry_data_path.read_text(encoding="utf-8"))
                    raw_templates = data.get("templates", {})
                    if target_template_id in raw_templates:
                        raise PromotionCollisionError(
                            f"Target template ID '{target_template_id}' collides with an existing canonical template."
                        )
                    # Check alias collisions (both raw target ID and derived component name)
                    comp_name = self.derive_component_name(target_template_id)
                    for cid, entry in raw_templates.items():
                        aliases = entry.get("aliases", [])
                        if target_template_id in aliases or comp_name in aliases:
                            raise PromotionCollisionError(
                                f"Target template ID '{target_template_id}' collides with alias of existing template '{cid}'."
                            )
                except json.JSONDecodeError as e:
                    raise PromotionError(f"Failed to parse authoritative registry data: {e}")

    def derive_component_name(self, target_template_id: str, candidate_name: Optional[str] = None) -> str:
        """
        Derives a clean, valid PascalCase component identifier from the target template ID.
        """
        # Split on hyphens and convert to PascalCase
        parts = [p.capitalize() for p in target_template_id.split("-") if p]
        component_name = "".join(parts)
        if not re.match(r"^[A-Za-z][A-Za-z0-9_]*$", component_name):
            raise PromotionSecurityError(f"Derived component name '{component_name}' is not a valid identifier.")
        return component_name

    def derive_relative_path(
        self,
        target_template_id: str,
        component_name: str,
        proposed_category: str,
    ) -> Tuple[str, str, str]:
        """
        Determines canonical relative file path, registry category, and catalog type.
        Ensures target destination is strictly bounded within templates/.
        """
        cat_lower = (proposed_category or "").lower().strip()

        if cat_lower.startswith("effects") or cat_lower == "effect":
            rel_path = f"effects/{component_name}.tsx"
            reg_cat = "effect"
            cat_type = "effect"
        elif cat_lower.startswith("scenes") or cat_lower in ("scene", "composition"):
            rel_path = f"scenes/{component_name}.tsx"
            reg_cat = "composition"
            cat_type = "scene"
        elif "text" in cat_lower or "typography" in cat_lower:
            rel_path = f"elements/{component_name}.tsx"
            reg_cat = "text"
            cat_type = "text"
        else:
            rel_path = f"elements/{component_name}.tsx"
            reg_cat = "ui-block"
            cat_type = "ui-block"

        # Confinement verification
        target_full = (self.templates_dir / rel_path).resolve()
        try:
            target_full.relative_to(self.templates_dir.resolve())
        except ValueError:
            raise PromotionSecurityError(f"Resolved destination '{target_full}' escapes canonical templates directory.")

        return rel_path, reg_cat, cat_type

    # =========================================================================
    # 2. ISOLATED STAGING PREPARATION
    # =========================================================================

    def prepare_staged_publication(
        self,
        candidate: TemplateCandidate,
        target_template_id: str,
        source_code: str,
    ) -> StagedPublication:
        """
        Prepares all publication artifacts within an isolated staging directory.
        Performs zero mutation on canonical workspace files.
        """
        self.validate_target_identity(target_template_id)
        component_name = self.derive_component_name(target_template_id, candidate.name)
        rel_file_path, reg_cat, cat_type = self.derive_relative_path(
            target_template_id, component_name, candidate.proposed_category
        )

        stage_dir = Path(tempfile.mkdtemp(prefix="stage_promote_"))

        try:
            # 1. Materialize production component source in stage
            staged_source = stage_dir / "templates" / rel_file_path
            staged_source.parent.mkdir(parents=True, exist_ok=True)
            staged_source.write_text(source_code, encoding="utf-8")

            # 2. Prepare staged registry data (Source of Truth)
            if not self.registry_data_path.exists():
                raise FileNotFoundError(f"Missing authoritative registry data: {self.registry_data_path}")

            pre_publish_hash = hashlib.sha256(self.registry_data_path.read_bytes()).hexdigest()
            raw_reg_data = self.registry_data_path.read_text(encoding="utf-8")
            registry_dict = json.loads(raw_reg_data)

            # Build new template entry
            duration = 150
            if isinstance(candidate.fixtures, dict):
                duration = int(candidate.fixtures.get("durationInFrames") or candidate.fixtures.get("duration", 150))

            schema_props = candidate.template_schema.get("properties", candidate.template_schema) if isinstance(candidate.template_schema, dict) else {}
            defaults = candidate.fixtures.get("props", candidate.fixtures) if isinstance(candidate.fixtures, dict) else {}

            new_entry = {
                "canonical_id": target_template_id,
                "category": reg_cat,
                "component_name": component_name,
                "default_duration_frames": duration,
                "runtime_available": True,
                "aliases": sorted(list(set([component_name]))),
                "label": {
                    "ar": candidate.name or component_name,
                    "en": candidate.name or component_name,
                },
                "description": {
                    "ar": candidate.description or candidate.name or component_name,
                    "en": candidate.description or candidate.name or component_name,
                },
                "schema": schema_props,
                "defaults": defaults,
            }

            registry_dict["templates"][target_template_id] = new_entry

            staged_reg_data = stage_dir / "registry" / "template-registry-data.json"
            staged_reg_data.parent.mkdir(parents=True, exist_ok=True)
            staged_reg_data.write_text(
                json.dumps(registry_dict, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            # 3. Generate derivative runtime contract & aliases using canonical generator
            contract, aliases = build_template_contract(authority_path=staged_reg_data)
            contract_json = serialize_contract_deterministic(contract)
            aliases_ts = serialize_aliases_ts(aliases)

            staged_contract = stage_dir / "contracts" / "template-runtime-contract.json"
            staged_contract.parent.mkdir(parents=True, exist_ok=True)
            staged_contract.write_text(contract_json, encoding="utf-8")

            staged_aliases = stage_dir / "registry" / "template-aliases.ts"
            staged_aliases.write_text(aliases_ts, encoding="utf-8")

            # 4. Generate updated template-registry.tsx
            if not self.registry_tsx_path.exists():
                raise FileNotFoundError(f"Missing registry.tsx: {self.registry_tsx_path}")

            tsx_content = self.registry_tsx_path.read_text(encoding="utf-8")
            rel_import_path = f"../templates/{rel_file_path[:-4]}"  # strip .tsx
            new_import = f'import {{ {component_name} }} from "{rel_import_path}";\n'

            # Insert import before first export or metadata import
            if "import registryMetadata from" in tsx_content:
                tsx_content = tsx_content.replace(
                    "import registryMetadata from",
                    f"{new_import}import registryMetadata from",
                )
            else:
                tsx_content = new_import + tsx_content

            # Insert into COMPONENT_BINDINGS dictionary
            bindings_marker = "export const COMPONENT_BINDINGS: Record<string, any> = {"
            if bindings_marker in tsx_content:
                tsx_content = tsx_content.replace(
                    bindings_marker,
                    f"{bindings_marker}\n  {component_name},",
                )
            else:
                raise PromotionError("Could not locate COMPONENT_BINDINGS marker in template-registry.tsx")

            staged_tsx = stage_dir / "registry" / "template-registry.tsx"
            staged_tsx.write_text(tsx_content, encoding="utf-8")

            # 5. Generate updated template_catalog.json
            if not self.catalog_path.exists():
                raise FileNotFoundError(f"Missing template_catalog.json: {self.catalog_path}")

            catalog_list = json.loads(self.catalog_path.read_text(encoding="utf-8"))
            schema_keys = list(schema_props.keys()) if isinstance(schema_props, dict) else []
            caps = list(dict.fromkeys(schema_keys + (candidate.proposed_tags or [])))
            intents = list(dict.fromkeys(candidate.proposed_tags or [candidate.proposed_category, reg_cat]))
            moods = ["Cinematic", "Modern", "Energetic"]
            use_cases = [candidate.proposed_category, "promoted_template"]
            new_catalog_entry = {
                "id": target_template_id,
                "name": component_name,
                "type": cat_type,
                "family": component_name,
                "quality": "B",
                "status": "production-ready",
                "supported_aspects": ["16:9", "9:16", "1:1"],
                "rtl_ready": True,
                "source": "promoted",
                "path": f"templates/{rel_file_path[:-4]}",
                "use_cases": use_cases,
                "intents": intents,
                "moods": moods,
                "capabilities": caps,
                "notes": f"Promoted candidate {candidate.candidate_id}",
            }
            catalog_list.append(new_catalog_entry)

            staged_catalog = stage_dir / "ground-truth" / "template_catalog.json"
            staged_catalog.parent.mkdir(parents=True, exist_ok=True)
            staged_catalog.write_text(
                json.dumps(catalog_list, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            return StagedPublication(
                stage_dir=stage_dir,
                target_template_id=target_template_id,
                component_name=component_name,
                rel_file_path=rel_file_path,
                registry_category=reg_cat,
                catalog_type=cat_type,
                pre_publish_registry_hash=pre_publish_hash,
                staged_source_path=staged_source,
                staged_registry_data_path=staged_reg_data,
                staged_contract_path=staged_contract,
                staged_aliases_path=staged_aliases,
                staged_registry_tsx_path=staged_tsx,
                staged_catalog_path=staged_catalog,
            )
        except Exception:
            shutil.rmtree(stage_dir, ignore_errors=True)
            raise

    # =========================================================================
    # 3. STAGING CONSISTENCY CHECKS
    # =========================================================================

    def verify_staged_publication(self, staged: StagedPublication, expected_source_hash: str) -> None:
        """
        Rigorous consistency checks performed exclusively on the staged state
        BEFORE any mutations to the canonical workspace.
        """
        # Staged source exists and matches hash
        if not staged.staged_source_path.exists():
            raise PromotionError("Staged source component was not generated.")

        source_bytes = staged.staged_source_path.read_bytes()
        actual_source_hash = hashlib.sha256(source_bytes).hexdigest()
        if actual_source_hash != expected_source_hash:
            raise PromotionError(
                f"Staged source code hash mismatch: expected {expected_source_hash}, got {actual_source_hash}"
            )

        # Staged registry data validity
        if not staged.staged_registry_data_path.exists():
            raise PromotionError("Staged template-registry-data.json missing.")
        reg_dict = json.loads(staged.staged_registry_data_path.read_text(encoding="utf-8"))
        if staged.target_template_id not in reg_dict.get("templates", {}):
            raise PromotionError("Staged registry data does not contain new target template.")

        # Staged contract validity
        if not staged.staged_contract_path.exists():
            raise PromotionError("Staged template-runtime-contract.json missing.")
        contract_dict = json.loads(staged.staged_contract_path.read_text(encoding="utf-8"))
        if staged.target_template_id not in contract_dict.get("templates", {}):
            raise PromotionError("Staged contract does not contain new target template.")
        if staged.component_name not in contract_dict.get("aliases", {}):
            raise PromotionError("Staged contract aliases missing component alias.")

        # Staged tsx bindings validity
        tsx_text = staged.staged_registry_tsx_path.read_text(encoding="utf-8")
        if f"import {{ {staged.component_name} }}" not in tsx_text:
            raise PromotionError(f"Staged registry.tsx missing import for {staged.component_name}.")
        if f"{staged.component_name}," not in tsx_text:
            raise PromotionError(f"Staged registry.tsx missing COMPONENT_BINDINGS entry for {staged.component_name}.")

        # Staged catalog validity
        cat_list = json.loads(staged.staged_catalog_path.read_text(encoding="utf-8"))
        if not any(item.get("id") == staged.target_template_id for item in cat_list):
            raise PromotionError("Staged catalog does not contain new target template.")

    # =========================================================================
    # 4. ATOMIC COMMIT & ROLLBACK JOURNAL
    # =========================================================================

    def commit_publication(
        self,
        staged: StagedPublication,
    ) -> Tuple[str, Dict[str, str], RollbackJournal]:
        """
        Commits staged publication into the canonical workspace with a journaled rollback safety net.
        Returns (post_publish_registry_hash, published_artifact_hashes, journal).
        """
        journal = RollbackJournal()
        dest_source = self.templates_dir / staged.rel_file_path

        # Record pre-state for all affected targets
        journal.record_pre_state(dest_source)
        journal.record_pre_state(self.registry_data_path)
        journal.record_pre_state(self.contract_path)
        journal.record_pre_state(self.aliases_path)
        journal.record_pre_state(self.registry_tsx_path)
        journal.record_pre_state(self.catalog_path)

        published_hashes: Dict[str, str] = {}

        try:
            # 1. Commit template source file
            dest_source.parent.mkdir(parents=True, exist_ok=True)
            self._atomic_copy(staged.staged_source_path, dest_source)
            published_hashes[f"templates/{staged.rel_file_path}"] = hashlib.sha256(
                dest_source.read_bytes()
            ).hexdigest()

            # 2. Commit registry data
            self._atomic_copy(staged.staged_registry_data_path, self.registry_data_path)
            post_reg_bytes = self.registry_data_path.read_bytes()
            post_publish_hash = hashlib.sha256(post_reg_bytes).hexdigest()
            published_hashes["registry/template-registry-data.json"] = post_publish_hash

            # 3. Commit contract
            self._atomic_copy(staged.staged_contract_path, self.contract_path)
            published_hashes["contracts/template-runtime-contract.json"] = hashlib.sha256(
                self.contract_path.read_bytes()
            ).hexdigest()

            # 4. Commit aliases
            self._atomic_copy(staged.staged_aliases_path, self.aliases_path)
            published_hashes["registry/template-aliases.ts"] = hashlib.sha256(
                self.aliases_path.read_bytes()
            ).hexdigest()

            # 5. Commit registry.tsx
            self._atomic_copy(staged.staged_registry_tsx_path, self.registry_tsx_path)
            published_hashes["registry/template-registry.tsx"] = hashlib.sha256(
                self.registry_tsx_path.read_bytes()
            ).hexdigest()

            # 6. Commit catalog
            self._atomic_copy(staged.staged_catalog_path, self.catalog_path)
            published_hashes["ground-truth/template_catalog.json"] = hashlib.sha256(
                self.catalog_path.read_bytes()
            ).hexdigest()

            # Invalidate and reload template contract cache so downstream readers see the new template
            try:
                from scripts.core.template_contract import get_template_contract
                get_template_contract(contract_path=self.contract_path, reload=True)
            except Exception:
                pass

            return post_publish_hash, published_hashes, journal

        except Exception as exc:
            # Automatic rollback on unexpected commit failure
            self.rollback(journal)
            raise PromotionError(f"Publication commit failed, changes rolled back cleanly: {exc}")
        finally:
            shutil.rmtree(staged.stage_dir, ignore_errors=True)

    def verify_canonical_publication(
        self,
        target_template_id: str,
        component_name: str,
        rel_file_path: str,
        expected_source_hash: str,
    ) -> None:
        """
        Executes post-publish verification on live canonical state.
        Fails closed with PromotionRollbackError if any output is missing or corrupt.
        """
        dest_source = self.templates_dir / rel_file_path
        if not dest_source.exists():
            raise PromotionRollbackError(f"Post-publish verification failed: {dest_source} not found on disk.")

        actual_source_hash = hashlib.sha256(dest_source.read_bytes()).hexdigest()
        if actual_source_hash != expected_source_hash:
            raise PromotionRollbackError(
                f"Post-publish verification failed: {dest_source} source hash mismatch."
            )

        # Verify registry entry
        if not self.registry_data_path.exists():
            raise PromotionRollbackError("Post-publish verification failed: template-registry-data.json missing.")
        data = json.loads(self.registry_data_path.read_text(encoding="utf-8"))
        if target_template_id not in data.get("templates", {}):
            raise PromotionRollbackError(
                f"Post-publish verification failed: {target_template_id} missing from template-registry-data.json."
            )

        # Verify contract entry
        if not self.contract_path.exists():
            raise PromotionRollbackError("Post-publish verification failed: template-runtime-contract.json missing.")
        contract = json.loads(self.contract_path.read_text(encoding="utf-8"))
        if target_template_id not in contract.get("templates", {}):
            raise PromotionRollbackError(
                f"Post-publish verification failed: {target_template_id} missing from template-runtime-contract.json."
            )
        if component_name not in contract.get("aliases", {}):
            raise PromotionRollbackError(
                f"Post-publish verification failed: {component_name} missing from template-runtime-contract aliases."
            )

        # Verify catalog entry
        if not self.catalog_path.exists():
            raise PromotionRollbackError("Post-publish verification failed: template_catalog.json missing.")
        cat = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        if not any(item.get("id") == target_template_id for item in cat):
            raise PromotionRollbackError(
                f"Post-publish verification failed: {target_template_id} missing from template_catalog.json."
            )

        # Verify registry.tsx component binding
        if not self.registry_tsx_path.exists():
            raise PromotionRollbackError("Post-publish verification failed: template-registry.tsx missing.")
        tsx = self.registry_tsx_path.read_text(encoding="utf-8")
        if f"import {{ {component_name} }}" not in tsx:
            raise PromotionRollbackError(
                f"Post-publish verification failed: import for {component_name} missing from template-registry.tsx."
            )
        if f"{component_name}," not in tsx:
            raise PromotionRollbackError(
                f"Post-publish verification failed: {component_name} missing from COMPONENT_BINDINGS."
            )

    def rollback(self, journal: RollbackJournal) -> None:
        """
        Executes a complete, atomic restoration of all pre-publish snapshots recorded in the journal.
        """
        for path, original_bytes in journal.snapshots.items():
            try:
                if original_bytes is None:
                    # File did not exist prior to publication -> delete it
                    if path.exists():
                        if path.is_dir():
                            shutil.rmtree(path, ignore_errors=True)
                        else:
                            path.unlink(missing_ok=True)
                else:
                    # File existed -> restore exact bytes atomically
                    path.parent.mkdir(parents=True, exist_ok=True)
                    tmp_file = path.with_name(f".{path.name}.rollback.tmp")
                    with open(tmp_file, "wb") as f:
                        f.write(original_bytes)
                        f.flush()
                        os.fsync(f.fileno())
                    tmp_file.replace(path)
            except Exception as e:
                # Log but continue restoring remaining files
                print(f"Warning during rollback of {path}: {e}")

        # Invalidate and reload template contract cache after rollback to restore previous state
        try:
            from scripts.core.template_contract import get_template_contract
            get_template_contract(contract_path=self.contract_path, reload=True)
        except Exception:
            pass

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _atomic_copy(self, src: Path, dest: Path) -> None:
        """Copies file atomically using a temporary file in destination directory."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp_dest = dest.with_name(f".{dest.name}.atomic.tmp")
        shutil.copy2(src, tmp_dest)
        tmp_dest.replace(dest)
