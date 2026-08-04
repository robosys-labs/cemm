"""Collection-only compatibility types for later-phase frozen tests.

Production removed these six-phase fixture owners at the R1 hard cut. Frozen
R3 predecessor modules still import their names while pytest enumerates the
complete suite, so the names live only in test support until those owners are
rewritten at their admitted phase.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProposalResult:
    program: Any
    output_refs: tuple[str, ...] = ()
    rejection_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class VerificationResult:
    legal: bool
    output_refs: tuple[str, ...] = ()
    rejection_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvaluationResult:
    status: str
    output_refs: tuple[str, ...] = ()
    rejection_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class EffectResult:
    executed: bool
    output_refs: tuple[str, ...] = ()
    rejection_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class RealizationResult:
    realized: bool
    output_refs: tuple[str, ...] = ()
    rejection_codes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProcessResult:
    cycle_result: Any
    response_meaning: Any
    realization_receipt: Any


class FixtureProposalOwner:
    def __init__(self, program: Any) -> None:
        self.program = program


class FixtureVerificationOwner:
    pass


class FixtureEvaluationOwner:
    pass


class FixtureEffectOwner:
    def __init__(self, stores: Any) -> None:
        self.stores = stores


class FixtureRealizationOwner:
    pass
