"""
ai/style/resolver.py
====================
User Style Resolver for Creative Planning Personalization (S28-08A).

Responsibilities:
1. Load valid UserStyleProfile from canonical S27 MemoryService.
2. Apply strict canonical precedence hierarchy:
   CURRENT_REQUEST > BRAND_CONSTRAINT > CONFIRMED_USER_PREFERENCE > INFERRED_PREFERENCE > GLOBAL_DEFAULT
3. Resolve relevant preferences into a compact EffectiveUserStyle context.
4. Record structured, auditable decision traces for every dimension without hidden CoT.

Invariants:
- Memory ≠ Current Request Authority: Current explicit request ALWAYS wins.
- Preference ≠ Hard Constraint: Advisory guidance only.
- AI inference ≠ Confirmed user preference: Confirmed beats inferred.
- Zero lifecycle, QC, or registry authority mutation.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ai.contracts.creative.brief import AudioMode, CreativeBrief, ProvenanceType
from ai.contracts.creative.feedback import (
    EffectiveUserStyle,
    StyleDecisionTrace,
    StylePreferenceProvenance,
    UserStyleProfile,
    WinningSource,
)
from ai.memory.models import MemoryFilter, TrustedTenantContext
from ai.memory.service import MemoryService
from ai.memory.types import EpistemicStatus, MemoryScope, MemoryType, SourceType


class UserStyleResolver:
    """
    Authoritative resolver synthesizing stored user preferences with current request context.
    """

    # Global platform defaults when no stronger source is available
    GLOBAL_DEFAULTS = {
        "pacing": "moderate",
        "motion_intensity": "medium",
        "motion_personality": "Cinematic",
        "text_density": "balanced",
        "caption_style": "standard",
        "music_preference": "ambient",
        "transition_style": "subtle_dissolve",
        "visual_complexity": "clean",
    }

    @classmethod
    def load_profile(
        cls,
        context: TrustedTenantContext,
        memory_service: MemoryService,
    ) -> UserStyleProfile:
        """
        Loads the active UserStyleProfile from canonical S27 MemorySystem.
        Guarantees strict tenant and user boundary enforcement.
        """
        filter_req = MemoryFilter(
            workspace_id=context.workspace_id,
            memory_types=[MemoryType.USER_PREFERENCE],
            scopes=[MemoryScope.USER, MemoryScope.WORKSPACE],
            user_id=context.user_id,
            include_inactive=False,
            limit=50,
        )

        try:
            entries = memory_service.query_structured(context, filter_req)
        except Exception:
            entries = []

        provenance_by_dim: Dict[str, StylePreferenceProvenance] = {}
        fields: Dict[str, Any] = {
            "profile_id": f"prof_{context.workspace_id}_{context.user_id or 'workspace'}",
            "workspace_id": context.workspace_id,
            "user_id": context.user_id,
            "preferred_color_palette": [],
            "preferred_voices": [],
            "disliked_patterns": [],
            "taste_preferences": {},
        }

        # Process entries in chronological order so later entries overwrite earlier ones
        sorted_entries = sorted(entries, key=lambda e: e.updated_at)
        for entry in sorted_entries:
            payload = entry.structured_payload or {}
            dim = payload.get("dimension") or entry.metadata.get("dimension")
            val = payload.get("value") or entry.metadata.get("value")

            if not dim:
                # Attempt to extract topic from content
                lower = entry.content.lower()
                if "pacing" in lower or "ريتم" in lower or "إيقاع" in lower:
                    dim = "pacing"
                    val = "fast" if "fast" in lower or "سريع" in lower else "calm"
                elif "motion" in lower or "حركة" in lower:
                    dim = "motion_intensity"
                    val = "low" if "low" in lower or "بسيطة" in lower or "هادئة" in lower else "high"
                elif "music" in lower or "موسيقى" in lower:
                    dim = "music_tendencies"
                    val = "none" if "none" in lower or "بدون" in lower else "ambient"

            if dim and val:
                # Map dimension to profile field
                field_name = dim
                if dim == "pacing":
                    field_name = "pacing_preference"
                elif dim == "music":
                    field_name = "music_tendencies"
                elif dim == "motion":
                    field_name = "motion_intensity"

                if field_name in ["preferred_color_palette", "preferred_voices", "disliked_patterns"]:
                    if isinstance(val, list):
                        fields[field_name] = val
                    elif isinstance(val, str) and val not in fields[field_name]:
                        fields[field_name].append(val)
                else:
                    fields[field_name] = val

                provenance_by_dim[dim] = StylePreferenceProvenance(
                    dimension=dim,
                    epistemic_status=entry.epistemic_status,
                    confidence=entry.confidence,
                    source_type=entry.source_type,
                    evidence_count=int(entry.metadata.get("evidence_count", 1)),
                    last_observed_at=entry.updated_at,
                    source_id=entry.id,
                    rationale=entry.content,
                )

        now = datetime.now(timezone.utc)
        fields["provenance_by_dimension"] = provenance_by_dim
        fields["updated_at"] = now

        return UserStyleProfile(**fields)

    @classmethod
    def resolve_effective_style(
        cls,
        context: TrustedTenantContext,
        brief: CreativeBrief,
        profile: Optional[UserStyleProfile] = None,
        brand_constraints: Optional[Dict[str, Any]] = None,
    ) -> EffectiveUserStyle:
        """
        Applies canonical precedence to synthesize an EffectiveUserStyle context.

        Precedence:
        1. Current explicit request
        2. Project / brand constraints
        3. Confirmed user preferences
        4. Inferred preferences
        5. Global defaults
        """
        trace_records: List[StyleDecisionTrace] = []

        # 1. Parse Current Explicit Directives from Brief and Prompt
        explicit_req = cls._extract_explicit_request_directives(brief)

        # 2. Extract Brand Directives
        brand_dirs = cls._extract_brand_directives(brief, brand_constraints)

        # 3. Resolve Dimensions
        resolved_vals: Dict[str, Any] = {}
        dimensions = [
            "pacing",
            "motion_intensity",
            "motion_personality",
            "text_density",
            "caption_style",
            "music_preference",
            "transition_style",
            "visual_complexity",
        ]

        for dim in dimensions:
            trace = cls._resolve_dimension(
                dimension=dim,
                explicit_req=explicit_req,
                brand_dirs=brand_dirs,
                profile=profile,
                default_val=cls.GLOBAL_DEFAULTS.get(dim),
            )
            trace_records.append(trace)
            resolved_vals[dim] = trace.applied_value

        # Palette & lists resolution
        preferred_palette = (
            brief.constraints.brand_colors
            or (brand_dirs.get("brand_colors") if brand_dirs else None)
            or (profile.preferred_color_palette if profile else [])
            or []
        )

        preferred_voices = (profile.preferred_voices if profile else [])
        disliked_patterns = list(profile.disliked_patterns if profile else [])

        # If user explicitly requested no music, record that in disliked patterns or music_preference
        if resolved_vals.get("music_preference") == "none":
            if "background_music" not in disliked_patterns:
                disliked_patterns.append("background_music")

        now = datetime.now(timezone.utc)

        return EffectiveUserStyle(
            profile_id=profile.profile_id if profile else None,
            workspace_id=context.workspace_id,
            user_id=context.user_id,
            pacing=resolved_vals.get("pacing"),
            motion_intensity=resolved_vals.get("motion_intensity"),
            motion_personality=resolved_vals.get("motion_personality"),
            text_density=resolved_vals.get("text_density"),
            caption_style=resolved_vals.get("caption_style"),
            music_preference=resolved_vals.get("music_preference"),
            transition_style=resolved_vals.get("transition_style"),
            visual_complexity=resolved_vals.get("visual_complexity"),
            preferred_color_palette=preferred_palette,
            preferred_voices=preferred_voices,
            disliked_patterns=disliked_patterns,
            trace_records=trace_records,
            resolved_at=now,
        )

    @classmethod
    def _resolve_dimension(
        cls,
        dimension: str,
        explicit_req: Dict[str, str],
        brand_dirs: Dict[str, str],
        profile: Optional[UserStyleProfile],
        default_val: Optional[str],
    ) -> StyleDecisionTrace:
        """
        Resolves a single style dimension across the 5 canonical precedence levels.
        """
        # Stored preference candidate
        stored_val: Optional[str] = None
        stored_source: Optional[str] = None
        stored_conf: Optional[float] = None
        is_confirmed = False

        if profile:
            # Map dimension to profile field
            val_candidate: Optional[str] = None
            if dimension == "pacing":
                val_candidate = profile.pacing_preference
            elif dimension == "motion_intensity":
                val_candidate = profile.motion_intensity
            elif dimension == "motion_personality":
                val_candidate = profile.preferred_motion_personality
            elif dimension == "music_preference":
                val_candidate = profile.music_tendencies
            elif hasattr(profile, dimension):
                val_candidate = getattr(profile, dimension, None)

            if val_candidate:
                stored_val = val_candidate
                prov = profile.provenance_by_dimension.get(dimension)
                if prov:
                    stored_source = prov.epistemic_status.value
                    stored_conf = prov.confidence
                    is_confirmed = (
                        prov.epistemic_status == EpistemicStatus.CONFIRMED
                        or prov.epistemic_status == EpistemicStatus.EXPLICIT
                        or prov.confidence >= 0.8
                    )
                else:
                    stored_source = "USER_PREFERENCE"
                    stored_conf = 0.85
                    is_confirmed = True

        # Precedence Level 1: Current Explicit Request
        req_val = explicit_req.get(dimension)
        if req_val:
            is_overridden = stored_val is not None and stored_val.lower() != req_val.lower()
            override_reason = (
                f"Current explicit user request '{req_val}' overrides stored preference '{stored_val}'"
                if is_overridden else None
            )
            return StyleDecisionTrace(
                dimension=dimension,
                considered_value=stored_val,
                considered_source=stored_source,
                considered_confidence=stored_conf,
                applied_value=req_val,
                is_overridden=is_overridden,
                override_reason=override_reason,
                winning_source=WinningSource.CURRENT_REQUEST,
            )

        # Precedence Level 2: Project / Brand Constraints
        brand_val = brand_dirs.get(dimension)
        if brand_val:
            is_overridden = stored_val is not None and stored_val.lower() != brand_val.lower()
            override_reason = (
                f"Project/brand constraint '{brand_val}' overrides stored preference '{stored_val}'"
                if is_overridden else None
            )
            return StyleDecisionTrace(
                dimension=dimension,
                considered_value=stored_val,
                considered_source=stored_source,
                considered_confidence=stored_conf,
                applied_value=brand_val,
                is_overridden=is_overridden,
                override_reason=override_reason,
                winning_source=WinningSource.BRAND_CONSTRAINT,
            )

        # Precedence Level 3: Confirmed User Preferences
        if stored_val and is_confirmed:
            return StyleDecisionTrace(
                dimension=dimension,
                considered_value=stored_val,
                considered_source=stored_source,
                considered_confidence=stored_conf,
                applied_value=stored_val,
                is_overridden=False,
                override_reason=None,
                winning_source=WinningSource.CONFIRMED_USER_PREFERENCE,
            )

        # Precedence Level 4: Inferred User Preferences
        if stored_val and not is_confirmed:
            return StyleDecisionTrace(
                dimension=dimension,
                considered_value=stored_val,
                considered_source=stored_source,
                considered_confidence=stored_conf,
                applied_value=stored_val,
                is_overridden=False,
                override_reason=None,
                winning_source=WinningSource.INFERRED_PREFERENCE,
            )

        # Precedence Level 5: Global Defaults
        return StyleDecisionTrace(
            dimension=dimension,
            considered_value=stored_val,
            considered_source=stored_source,
            considered_confidence=stored_conf,
            applied_value=default_val,
            is_overridden=False,
            override_reason=None,
            winning_source=WinningSource.GLOBAL_DEFAULT,
        )

    @classmethod
    def _extract_explicit_request_directives(cls, brief: CreativeBrief) -> Dict[str, str]:
        """
        Inspects brief.user_request_raw, interpreted_intent, and constraints for explicit requests.
        """
        directives: Dict[str, str] = {}
        raw = (brief.user_request_raw or "").lower()

        # Check Audio Mode constraints first (HARD constraint mapped to music)
        if brief.constraints.audio_mode in (AudioMode.SILENT, AudioMode.VO_ONLY):
            directives["music_preference"] = "none"

        # Explicit Pacing
        if any(w in raw for w in ["هادئ", "هادي", "بطيء", "calm", "slow", "deliberate"]):
            directives["pacing"] = "calm"
        elif any(w in raw for w in ["سريع", "ديناميكي", "fast", "energetic", "rapid", "rushed"]):
            directives["pacing"] = "fast"
        elif brief.interpreted_intent.pace:
            pace_prov = brief.field_provenance.get("pace")
            if pace_prov and pace_prov.source_type == ProvenanceType.EXPLICIT:
                directives["pacing"] = brief.interpreted_intent.pace.lower()

        # Explicit Motion Intensity & Personality
        if any(w in raw for w in ["حركة بسيطة", "حركة خفيفة", "حركة هادئة", "low motion", "simple motion", "minimal motion"]):
            directives["motion_intensity"] = "low"
            directives["motion_personality"] = "Cinematic"
        elif any(w in raw for w in ["حركة كثيرة", "حركة قوية", "حركة سريعة", "high motion", "energetic motion"]):
            directives["motion_intensity"] = "high"
            directives["motion_personality"] = "Energetic"

        # Explicit Music
        if any(w in raw for w in ["بدون موسيقى", "بلا موسيقى", "أوقف الموسيقى", "no music", "without music", "silent"]):
            directives["music_preference"] = "none"
        elif any(w in raw for w in ["موسيقى إلكترونية", "electronic music"]):
            directives["music_preference"] = "electronic"
        elif any(w in raw for w in ["موسيقى هادئة", "ambient music", "calm music"]):
            directives["music_preference"] = "ambient"

        # Explicit Caption
        if any(w in raw for w in ["كابتشن أصغر", "خط صغير", "صغر الخط", "smaller captions", "compact captions"]):
            directives["caption_style"] = "compact"
        elif any(w in raw for w in ["كابتشن كبير", "خط كبير", "كبر الخط", "prominent captions", "large captions"]):
            directives["caption_style"] = "prominent"

        # Explicit Visual Complexity
        if any(w in raw for w in ["بسيط", "نظيف", "minimal", "clean", "simple"]):
            directives["visual_complexity"] = "minimal"
        elif any(w in raw for w in ["دارك مود", "داكن", "dark mode", "dark theme"]):
            directives["visual_complexity"] = "dark_mode"

        return directives

    @classmethod
    def _extract_brand_directives(
        cls,
        brief: CreativeBrief,
        brand_constraints: Optional[Dict[str, Any]],
    ) -> Dict[str, str]:
        """
        Extracts directives specified by project or brand constraints.
        """
        directives: Dict[str, str] = {}
        if not brand_constraints:
            return directives

        for k in ["pacing", "motion_intensity", "motion_personality", "caption_style", "music_preference", "visual_complexity", "transition_style"]:
            if k in brand_constraints and brand_constraints[k]:
                directives[k] = str(brand_constraints[k])

        return directives
