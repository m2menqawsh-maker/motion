"""
ai/contracts/base.py
====================
Base class and core typing primitives for the AI subsystem canonical contracts.

Guarantees:
- Strict validation policy: unexpected fields are strictly forbidden (extra = "forbid").
- Strict type checking: coercion of mismatched primitives is disabled (strict = True).
- Immutability: models are frozen value objects (frozen = True).
- Timezone safety: all datetimes must be timezone-aware (TzAwareDatetime).
- Decimal monetary safety: binary floats are strictly forbidden (StrictDecimal).
- Enum string compatibility: string literals corresponding to enums are safely resolved.
- Structured JSON: no unrestricted `dict[str, Any]` at boundaries; typed via `JsonValue`.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, Dict, Type, TypeVar
from pydantic import BaseModel, ConfigDict, JsonValue, BeforeValidator


def parse_tz_aware_datetime(v: Any) -> Any:
    """Parses and validates that datetime instances and strings are strictly timezone-aware."""
    if isinstance(v, str):
        try:
            v = datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception as e:
            raise ValueError(f"Invalid ISO 8601 datetime string: {e}")
    if isinstance(v, datetime):
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError("Datetime must be timezone-aware (e.g., UTC with timezone offset)")
        return v
    raise ValueError(f"Datetime value must be datetime or ISO string, not {type(v).__name__}")


TzAwareDatetime = Annotated[datetime, BeforeValidator(parse_tz_aware_datetime)]


def parse_strict_decimal(v: Any) -> Any:
    """Enforces exact decimal monetary representation; strictly rejects binary floats."""
    if isinstance(v, float):
        raise ValueError(
            "Monetary amounts cannot use binary floating-point representation. "
            "Use exact Decimal or string representation to avoid precision loss."
        )
    if isinstance(v, (str, int)):
        try:
            return Decimal(str(v))
        except Exception as e:
            raise ValueError(f"Invalid decimal value: {e}")
    if isinstance(v, Decimal):
        return v
    raise ValueError(f"Decimal value must be Decimal, int, or string, not {type(v).__name__}")


StrictDecimal = Annotated[Decimal, BeforeValidator(parse_strict_decimal)]

E = TypeVar("E", bound=Enum)


def strict_enum(enum_cls: Type[E]) -> Any:
    """Creates an annotated enum type that accepts string values and enum instances while strict=True."""
    def validator(v: Any) -> Any:
        if isinstance(v, str):
            try:
                return enum_cls(v)
            except ValueError:
                valid_vals = [m.value for m in enum_cls]
                raise ValueError(f"Input should be one of {valid_vals}")
        if isinstance(v, enum_cls):
            return v
        raise ValueError(f"Value must be a valid {enum_cls.__name__} or string, got {type(v).__name__}")

    return Annotated[enum_cls, BeforeValidator(validator)]


T = TypeVar("T")


class AIContractModel(BaseModel):
    """
    Canonical base class for all AI subsystem contracts.
    Enforces strict typing, immutability, and rejection of unexpected fields.
    """

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        validate_default=True,
        frozen=True,
    )
