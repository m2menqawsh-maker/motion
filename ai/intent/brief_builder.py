"""
ai/intent/brief_builder.py
==========================
Constructs canonical CreativeBrief contracts from IntentParseResult (S28-03).
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from ai.contracts.common import ProvenanceRecord
from ai.contracts.creative.brief import (
    CreativeBrief,
    CreativeConstraints,
    CreativeIntent,
)
from ai.contracts.media import MediaIntelligence
from ai.intent.contracts import IntentParseResult
from ai.intent.parser import IntentParser


class CreativeBriefBuilder:
    """
    Builds canonical CreativeBrief contract models by orchestrating
    the IntentParser and packaging all constraints and epistemic provenance.
    """

    def __init__(self, parser: Optional[IntentParser] = None) -> None:
        self.parser = parser or IntentParser()

    def build_brief(
        self,
        user_request: str,
        project_id: str = "proj_default",
        workspace_id: str = "ws_default",
        project_state: Optional[Dict[str, Any]] = None,
        available_assets: Optional[List[Any]] = None,
        media_intelligence: Optional[Union[MediaIntelligence, List[MediaIntelligence]]] = None,
        workspace_constraints: Optional[Dict[str, Any]] = None,
    ) -> CreativeBrief:
        """Parses user request and contextual inputs to synthesize a canonical CreativeBrief."""
        start_time = time.perf_counter()

        parsed: IntentParseResult = self.parser.parse(
            user_request=user_request,
            project_state=project_state,
            available_assets=available_assets,
            media_intelligence=media_intelligence,
            workspace_constraints=workspace_constraints,
        )

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        now_iso = datetime.now(timezone.utc).isoformat()

        # Build CreativeIntent
        intent = CreativeIntent(
            intent_id=f"intent_{uuid.uuid4().hex[:12]}",
            goal=parsed.goal,
            audience="general audience",
            tone=parsed.tone,
            key_takeaway=parsed.key_takeaway,
            call_to_action=parsed.call_to_action,
            target_platforms=parsed.target_platforms,
            video_type=parsed.video_type,
            style=parsed.style,
            pace=parsed.pace,
            language=parsed.detected_language,
        )

        # Build CreativeConstraints
        constraints = CreativeConstraints(
            min_duration_seconds=parsed.min_duration_seconds,
            max_duration_seconds=parsed.max_duration_seconds,
            target_duration_seconds=parsed.target_duration_seconds,
            aspect_ratios=["9:16"] if any("reels" in p or "tiktok" in p or "shorts" in p for p in parsed.target_platforms) else ["16:9"],
            audio_mode=parsed.audio_mode,
            brand_colors=parsed.brand_colors,
            excluded_templates=(workspace_constraints or {}).get("excluded_templates", []),
            forbidden_words=(workspace_constraints or {}).get("forbidden_words", []),
            safe_zone_margin_px=(workspace_constraints or {}).get("safe_zone_margin_px", 40),
        )

        # Top-level interpretation provenance
        brief_provenance = ProvenanceRecord(
            source="ai.intent.brief_builder.CreativeBriefBuilder",
            model_id="deterministic_intent_pipeline_v1",
            provider_id="internal_creative_engine",
            timestamp=now_iso,
            latency_ms=latency_ms,
        )

        # Assemble root brief
        brief = CreativeBrief(
            brief_id=f"brief_{uuid.uuid4().hex[:12]}",
            project_id=project_id,
            workspace_id=workspace_id,
            user_request_raw=parsed.user_request_raw,
            interpreted_intent=intent,
            constraints=constraints,
            provenance=brief_provenance,
            field_provenance=parsed.field_provenance,
            detected_contradictions=parsed.detected_contradictions,
            created_at=now_iso,
            version="1.0.0",
        )

        return brief
