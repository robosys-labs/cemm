"""Typed Phase-11 query binding and proof-path artifacts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..csir.model import CSIRRef


@dataclass(frozen=True, slots=True)
class QueryBinding:
    binding_ref: str
    variable_ref: CSIRRef
    value_ref: CSIRRef | None = None
    value_atom: str | int | float | bool | None = None
    value_identity_ref: str | None = None
    proposition_ref: str = ""
    claim_ref: str = ""
    confidence: float = 1.0

    def __post_init__(self) -> None:
        choices = sum(value is not None for value in (self.value_ref, self.value_atom))
        if choices != 1:
            raise ValueError("query binding requires exactly one semantic ref or atom")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("query binding confidence must be within [0,1]")


@dataclass(frozen=True, slots=True)
class ExplanationProof:
    proof_ref: str
    query_ref: str
    target_ref: str
    premise_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    operation_refs: tuple[str, ...]
    minimal: bool = True


@dataclass(frozen=True, slots=True)
class QueryResult:
    result_ref: str
    query_ref: str
    bindings: tuple[QueryBinding, ...]
    truth_value: bool | None
    explanation_proof_refs: tuple[str, ...]
    frontier_refs: tuple[str, ...] = ()

    @property
    def answered(self) -> bool:
        return bool(self.bindings) or self.truth_value is not None


__all__ = ["ExplanationProof", "QueryBinding", "QueryResult"]
