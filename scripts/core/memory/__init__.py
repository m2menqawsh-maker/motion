"""
scripts/core/memory/__init__.py
===============================
Approved persistence and infrastructure layer for AI Memory subsystem (S27.6).
"""

from scripts.core.memory.postgres_memory_repository import PostgresMemoryRepository

__all__ = ["PostgresMemoryRepository"]
