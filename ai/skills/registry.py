"""
ai/skills/registry.py
=====================
Canonical registry for operational skills (S28-02).

Guarantees:
- Skill = How the system handles a task type (Skill ≠ Permission, Skill ≠ Tool).
- Strict status and version tracking (ACTIVE vs RETIRED vs DISABLED).
- Retired or disabled skills are excluded from active routing.
- Immutable snapshotting for deterministic execution.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple
from ai.contracts.creative.skills_knowledge import SkillDefinition, SkillStatus


class SkillRegistryError(Exception):
    """Base exception for Skill Registry errors."""
    pass


class DuplicateSkillError(SkillRegistryError):
    """Raised when registering conflicting skills."""
    pass


class SkillNotFoundError(SkillRegistryError):
    """Raised when a requested skill is not found in the registry."""
    pass


class SkillRegistry:
    """
    Authoritative in-memory registry of validated SkillDefinitions.
    """

    def __init__(self) -> None:
        # Key: (skill_id, version) -> SkillDefinition
        self._entries: Dict[Tuple[str, str], SkillDefinition] = {}
        # Key: skill_id -> latest/default SkillDefinition
        self._latest: Dict[str, SkillDefinition] = {}

    def register(self, skill: SkillDefinition, allow_overwrite: bool = True) -> None:
        """Registers a SkillDefinition in the registry."""
        key = (skill.skill_id, skill.version)
        if key in self._entries and not allow_overwrite:
            raise DuplicateSkillError(f"Skill '{skill.skill_id}' v{skill.version} already registered.")

        self._entries[key] = skill

        # Track the latest active version (or latest registered if none active)
        existing_latest = self._latest.get(skill.skill_id)
        if existing_latest is None:
            self._latest[skill.skill_id] = skill
        else:
            if skill.status == SkillStatus.ACTIVE and existing_latest.status != SkillStatus.ACTIVE:
                self._latest[skill.skill_id] = skill
            elif skill.status == existing_latest.status and skill.version >= existing_latest.version:
                self._latest[skill.skill_id] = skill

    def register_many(self, skills: Sequence[SkillDefinition], allow_overwrite: bool = True) -> None:
        for s in skills:
            self.register(s, allow_overwrite=allow_overwrite)

    def get(self, skill_id: str, version: Optional[str] = None) -> Optional[SkillDefinition]:
        """Retrieves a skill by ID and optional version."""
        if version is not None:
            return self._entries.get((skill_id, version))
        return self._latest.get(skill_id)

    def get_active(self, skill_id: str, version: Optional[str] = None) -> Optional[SkillDefinition]:
        """Retrieves a skill ONLY if its status is ACTIVE."""
        s = self.get(skill_id, version=version)
        if s is not None and s.status == SkillStatus.ACTIVE:
            return s
        return None

    def list_active(self) -> List[SkillDefinition]:
        """Returns all skills with status ACTIVE."""
        return [s for s in self._entries.values() if s.status == SkillStatus.ACTIVE]

    def list_all(self) -> List[SkillDefinition]:
        """Returns all registered skills."""
        return list(self._entries.values())

    def unregister(self, skill_id: str, version: Optional[str] = None) -> bool:
        """Removes a skill or specific version from registry."""
        removed = False
        if version is not None:
            key = (skill_id, version)
            if key in self._entries:
                del self._entries[key]
                removed = True
        else:
            keys_to_del = [k for k in self._entries if k[0] == skill_id]
            for k in keys_to_del:
                del self._entries[k]
                removed = True

        remaining = [s for s in self._entries.values() if s.skill_id == skill_id]
        if remaining:
            self._latest[skill_id] = sorted(remaining, key=lambda x: (x.status == SkillStatus.ACTIVE, x.version))[-1]
        elif skill_id in self._latest:
            del self._latest[skill_id]

        return removed

    def clear(self) -> None:
        self._entries.clear()
        self._latest.clear()

    def snapshot(self) -> Dict[str, SkillDefinition]:
        return dict(self._latest)
