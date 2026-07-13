"""PolicySchema — executable definition of a policy.

Import boundary: standard library only → model.refs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class PolicySchema:
    """Executable definition of a policy."""
    semantic_key: str
    policy_kind: str = ""  # access, retention, execution, safety, etc.
    rules: tuple[Any, ...] = ()
    default_decision: str = "allow"  # allow, deny, require_approval
    scope: str = "global"
