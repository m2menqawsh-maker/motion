"""
ai/directors/bundle.py
======================
Coordinator orchestrating all four creative directors into a unified DirectorRecommendationBundle (S28-04).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from ai.contracts.creative.directors import DirectorRecommendationBundle
from ai.contracts.creative.taste import TasteContext
from ai.directors.emotion_director import EmotionDirector
from ai.directors.motion_director import MotionDirector
from ai.directors.narrative_director import NarrativeDirector
from ai.directors.sfx_director import SfxDirector

logger = logging.getLogger(__name__)


class CreativeDirectorCoordinator:
    """
    Coordinates invocation of NarrativeDirector, MotionDirector, EmotionDirector, and SfxDirector.
    Produces a unified DirectorRecommendationBundle.
    """

    def __init__(
        self,
        narrative_director: Optional[NarrativeDirector] = None,
        motion_director: Optional[MotionDirector] = None,
        emotion_director: Optional[EmotionDirector] = None,
        sfx_director: Optional[SfxDirector] = None,
    ) -> None:
        self.narrative_director = narrative_director or NarrativeDirector()
        self.motion_director = motion_director or MotionDirector()
        self.emotion_director = emotion_director or EmotionDirector()
        self.sfx_director = sfx_director or SfxDirector()

    def direct_all(self, context: TasteContext) -> DirectorRecommendationBundle:
        """Invokes all four directors and aggregates their structured recommendations."""
        narrative_dirs = self.narrative_director.direct(context)
        motion_dirs = self.motion_director.direct(context)
        emotion_dirs = self.emotion_director.direct(context)
        sfx_dirs = self.sfx_director.direct(context)

        return DirectorRecommendationBundle(
            brief_id=context.brief.brief_id,
            narrative_directions=narrative_dirs,
            motion_directions=motion_dirs,
            emotion_directions=emotion_dirs,
            sfx_directions=sfx_dirs,
            created_at=datetime.now(timezone.utc),
        )
