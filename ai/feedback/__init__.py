"""
ai/feedback/__init__.py
=======================
Creative Feedback Learning package for S28-08A.
"""

from __future__ import annotations

from ai.feedback.classifier import (
    FeedbackClassifier,
    MalformedFeedbackError,
)
from ai.feedback.service import (
    CreativeFeedbackService,
    FeedbackProcessingResult,
)

__all__ = [
    "FeedbackClassifier",
    "MalformedFeedbackError",
    "CreativeFeedbackService",
    "FeedbackProcessingResult",
]
