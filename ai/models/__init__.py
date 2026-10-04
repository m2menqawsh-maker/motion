"""
ai/models
=========
Model Registry and pricing infrastructure for S27.
"""

from ai.models.types import (
    CostTier,
    LatencyTier,
    ModelDefinition,
    ModelPricing,
)
from ai.models.definitions import CANONICAL_MODELS_LIST
from ai.models.registry import (
    DuplicateModelError,
    ModelRegistry,
    ModelRegistryError,
    UnknownModelError,
    create_empty_model_registry,
    get_model_registry,
)

__all__ = [
    "CostTier",
    "LatencyTier",
    "ModelDefinition",
    "ModelPricing",
    "CANONICAL_MODELS_LIST",
    "DuplicateModelError",
    "ModelRegistry",
    "ModelRegistryError",
    "UnknownModelError",
    "create_empty_model_registry",
    "get_model_registry",
]
