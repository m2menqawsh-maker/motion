"""
scripts/core/blueprint_compiler.py
==================================
Core bridge to Canonical BlueprintCompiler (S28-05).

Provides Core domain access to deterministic Blueprint compilation.
"""

from ai.planning.compiler import BlueprintCompiler
from ai.planning.errors import (
    CompilerError,
    CompilerValidationError,
    ForbiddenCapabilityCompilerError,
    MissingRequiredSceneCompilerError,
    TimingCompilerError,
    UnknownAssetCompilerError,
    UnknownTemplateCompilerError,
)

__all__ = [
    "BlueprintCompiler",
    "CompilerError",
    "UnknownTemplateCompilerError",
    "UnknownAssetCompilerError",
    "TimingCompilerError",
    "MissingRequiredSceneCompilerError",
    "ForbiddenCapabilityCompilerError",
    "CompilerValidationError",
]
