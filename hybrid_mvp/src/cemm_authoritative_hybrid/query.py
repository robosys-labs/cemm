"""Canonical expression-compiled query contracts.

The runtime owner is :class:`QueryDecisionOwner`.  This module retains a small
read-only diagnostic Query/QueryEngine API for tests and tooling; it never
accepts a construction program and exposes no mutation method.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .r3_artifacts import ProofGraph, ProofNode, QueryResult, QueryStatus
from .r3_cognition import QueryDecisionOwner

@dataclass(frozen=True)
class Query:
    subject_ref: str
    target_ref: str
    time: str | None = None

def query(subject: str, target: str, *, time: str | None = None) -> Query:
    return Query(subject, target, time)

class QueryEngine:
    """Read-only diagnostic façade over the expression-only query owner."""
    def __init__(self, owner: QueryDecisionOwner) -> None:
        if type(owner) is not QueryDecisionOwner:
            raise TypeError("owner must be exact QueryDecisionOwner")
        self._owner = owner

    def evaluate_expression(self, expression: Any, projection: Any, situation: Any) -> Any:
        return self._owner.evaluate_full(expression, projection, situation)

    def observe(self, _program: Any) -> None:
        raise TypeError("QueryEngine has no mutation authority; use R3EffectGateway")

__all__ = [
    "ProofGraph", "ProofNode", "Query", "QueryResult", "QueryStatus",
    "QueryDecisionOwner", "QueryEngine", "query",
]
