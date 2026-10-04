"""
ai/prompts/__init__.py
======================
Prompt Management and Authority Subsystem (S27.18).
"""

from ai.prompts.repository import PromptRepository
from ai.prompts.service import PromptService

__all__ = [
    "PromptRepository",
    "PromptService",
]
