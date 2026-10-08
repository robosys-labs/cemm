"""The first complete, *structured-semantic* CEMM output boundary.

This adapter has no interpretation, query, rule, or effect authority.  It
uses the existing six-phase HybridRuntime and faithfully exposes its verified
ResponseMeaning or typed unresolved frontier as an exactly reversible semantic
protocol.  It does NOT pretend to authorize free-form natural-language
realization: R5 linguistic equivalence remains unadmitted.

Until natural-language realization is proven, this is the reference end-to-end
semantic acceptance path.  It may not be substituted with a canned sentence.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .bootstrap import load_runtime
from .canonical import canonical_json, stable_ref
from .cycle import SemanticPhase
from .r3_cycle import CycleResult
from .r3_response import ResponseMeaning
from .runtime import HybridRuntime

SCHEMA = "cemm-foundation-semantic-surface-v1"
R5_GAP = "contract:r5:realize_surface"


def _document(cycle: CycleResult) -> dict[str, object]:
    """Validate provenance and construct a lossless semantic output.

    Do not infer an answer, paraphrase it, or coerce a failed meaning into
    success.  The protocol is intentionally structured, not natural language.
    """
    if type(cycle) is not CycleResult:
        raise TypeError("foundation requires the canonical R3 CycleResult")
    response = cycle.response_meaning
    if response is None:
        if cycle.effect_receipt is not None:
            raise ValueError("effect without response meaning")
        if cycle.gap_receipt is None:
            raise ValueError("unresolved cycle without typed gap")
        return {
            "schema": SCHEMA,
            "kind": "unresolved_frontier",
            "cycle_ref": cycle.cycle_ref,
            "status": cycle.status.value,
            "revision_pin": cycle.final_revision_pin.as_dict(),
            "gap_receipt": cycle.gap_receipt.as_dict(),
        }

    if type(response) is not ResponseMeaning:
        raise TypeError("noncanonical response meaning")
    if ResponseMeaning.from_dict(response.as_dict()) != response:
        raise ValueError("response meaning failed canonical round trip")
    if cycle.effect_receipt is None or cycle.evaluation is None:
        raise ValueError("response without evaluated effect/no-effect evidence")
    if cycle.gap_receipt is None or (
        cycle.gap_receipt.missing_contract_refs != (R5_GAP,)
    ):
        raise ValueError("unexpected predecessor realization contract")
    if response.revision_pin != cycle.final_revision_pin:
        raise ValueError("response and cycle revisions diverge")
    if response.effect_outcome_ref != cycle.effect_receipt.receipt_ref:
        raise ValueError("response and effect receipt identities diverge")
    if response.decision_ref != cycle.evaluation.decision.decision_ref:
        raise ValueError("response and decision identities diverge")
    if response.cycle_status is not cycle.status:
        raise ValueError("response status and cycle status diverge")
    if tuple(row.phase for row in cycle.phase_material) != tuple(SemanticPhase):
        raise ValueError("complete foundation result requires all six phases")
    return {
        "schema": SCHEMA,
        "kind": "response_meaning",
        "cycle_ref": cycle.cycle_ref,
        "status": cycle.status.value,
        "revision_pin": cycle.final_revision_pin.as_dict(),
        "decision_ref": response.decision_ref,
        "effect_receipt_ref": cycle.effect_receipt.receipt_ref,
        "response_meaning": response.as_dict(),
    }


@dataclass(frozen=True, slots=True)
class FoundationTurn:
    """One semantic output with a verifiable source-cycle identity."""
    cycle: CycleResult
    semantic_surface: str
    surface_ref: str

    @classmethod
    def from_cycle(cls, cycle: CycleResult) -> "FoundationTurn":
        document = _document(cycle)
        surface = canonical_json(document)
        return cls(cycle, surface, stable_ref("foundation_surface", document))

    def to_wire(self) -> dict[str, object]:
        """Create a durable review handoff, with no credentials or secret."""
        self.verify()
        return {
            "cycle": self.cycle.as_dict(),
            "semantic_surface": self.semantic_surface,
            "surface_ref": self.surface_ref,
        }

    @classmethod
    def from_wire(cls, value: object) -> "FoundationTurn":
        """Reconstruct exact proven R3 output after an application restart.

        A stored reviewer handoff is not itself authorization: the effect
        journal must still contain its original persisted NoEffect receipt,
        and a separate reviewer signature must approve its exact lineage.
        """
        if type(value) is not dict or set(value) != {
            "cycle", "semantic_surface", "surface_ref",
        }:
            raise ValueError("foundation review handoff fields mismatch")
        cycle = CycleResult.from_dict(value["cycle"])
        result = cls(
            cycle=cycle, semantic_surface=value["semantic_surface"],
            surface_ref=value["surface_ref"],
        )
        result.verify()
        return result

    def verify(self) -> bool:
        """Reject altered output, stale cycle metadata and noncanonical wires."""
        expected = _document(self.cycle)
        try:
            decoded = json.loads(self.semantic_surface)
        except (ValueError, TypeError) as exc:
            raise ValueError("invalid semantic surface") from exc
        if type(decoded) is not dict or decoded != expected:
            raise ValueError("surface differs from authenticated cycle")
        if self.semantic_surface != canonical_json(expected):
            raise ValueError("noncanonical semantic serialization")
        if self.surface_ref != stable_ref("foundation_surface", expected):
            raise ValueError("semantic surface identity mismatch")
        if decoded["kind"] == "response_meaning":
            restored = ResponseMeaning.from_dict(decoded["response_meaning"])
            if restored != self.cycle.response_meaning:
                raise ValueError("semantic response changed during realization")
        return True


class FoundationRuntime:
    """Single-brain semantic adapter around the existing HybridRuntime.

    This wrapper must never ground, compile, evaluate, mutate, or learn
    independently.  For ordinary language release, a separately proven
    graph-equivalent natural-language owner is still required.
    """

    def __init__(self, cognitive_runtime: HybridRuntime) -> None:
        if type(cognitive_runtime) is not HybridRuntime:
            raise TypeError("foundation needs one canonical HybridRuntime")
        self._cognitive_runtime = cognitive_runtime

    @property
    def stores(self):
        return self._cognitive_runtime.stores

    def process(self, session_ref: str, text: str, *, trace: bool = True) -> FoundationTurn:
        cycle = self._cognitive_runtime.process(session_ref, text, trace=trace)
        result = FoundationTurn.from_cycle(cycle)
        result.verify()
        return result

    def approve_reviewed_learning(
        self, source: FoundationTurn, approval: object,
        verifier: object, *, now: int,
    ):
        """Administrative approval of an *existing* R3 learning obligation.

        External authenticated reviewer services issue signatures. This
        reference adapter delegates the actual mutation to R3EffectGateway
        and never creates a meaning, world fact or designation independently.
        """
        from .r3_effects import AdapterRegistry, NoEffectReceipt, R3EffectGateway
        if type(source) is not FoundationTurn or not source.verify():
            raise ValueError("reviewed learning requires an exact verified turn")
        receipt = source.cycle.effect_receipt
        if type(receipt) is not NoEffectReceipt:
            raise ValueError("source turn lacks a pending NoEffectReceipt")
        return R3EffectGateway(
            self.stores, AdapterRegistry(),
        ).commit_reviewed_learning(
            response=source.cycle.response_meaning,
            source_receipt=receipt,
            authority=self._cognitive_runtime.authority,
            approval=approval, verifier=verifier, now=now,
        )

    def close(self) -> None:
        self.stores.close()


def load_foundation(
    root: str | Path,
    *,
    store_path: str | Path | None = None,
) -> FoundationRuntime:
    """Open the non-neural reference foundation with no external adapters.

    The profile is deliberately developmental: no R5 model, generated prose,
    or service connectors are silently admitted.
    """
    core = load_runtime(root, profile="development", store_path=store_path)
    return FoundationRuntime(core)
