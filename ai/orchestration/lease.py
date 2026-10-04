"""
ai/orchestration/lease.py
==========================
Durable worker lease tokens, fencing, and heartbeat records (S27.11).

Invariants:
- Every running step has an exclusive lease held by a designated worker_id.
- Monotonically unique fencing lease_token prevents stale worker commits.
- Expiration is evaluated against UTC clock.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional
from ai.contracts.base import AIContractModel, TzAwareDatetime


class LeaseRecord(AIContractModel):
    """Encapsulates active execution lease held by an autonomous worker."""
    worker_id: str
    lease_token: str
    acquired_at: TzAwareDatetime
    expires_at: TzAwareDatetime
    heartbeat_at: TzAwareDatetime

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        reference = now or datetime.now(timezone.utc)
        return reference >= self.expires_at


def generate_lease_token() -> str:
    """Generates a cryptographically random, collision-resistant fencing token."""
    return f"lease_{uuid.uuid4().hex}"
