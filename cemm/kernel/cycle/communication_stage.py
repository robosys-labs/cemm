"""COMMUNICATE and OUTPUT COMMIT hooks for v3.4.3."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..model.emission import (
    RealizedMessage,
    SemanticEmissionProof,
    SemanticMessagePlan,
)
from ..response.emission_closure import EmissionEnvironment, SemanticEmissionGate
from ..response.realizer import SemanticRealizer
from ..schema.lexicalization import LanguageRealizationPack


@dataclass(frozen=True, slots=True)
class CommunicationOutcome:
    plan_ref: str
    emission_proof: SemanticEmissionProof
    realized_message: RealizedMessage
    dispatched: bool
    output_event_ref: str = ""
    blocker_refs: tuple[str, ...] = ()


class CommunicationStage:
    def __init__(
        self,
        emission_gate: SemanticEmissionGate,
        realizer: SemanticRealizer,
        language_packs: dict[str, LanguageRealizationPack],
        dispatch: Callable[[str, str], str],
    ) -> None:
        self._gate = emission_gate
        self._realizer = realizer
        self._packs = language_packs
        self._dispatch = dispatch

    def run(
        self,
        plan: SemanticMessagePlan,
        environment: EmissionEnvironment,
    ) -> CommunicationOutcome:
        pack = self._packs.get(plan.language_tag) or self._packs.get(
            plan.language_tag.split("-", 1)[0]
        )
        if pack is None:
            proof = SemanticEmissionProof(
                plan_ref=plan.plan_id,
                language_tag=plan.language_tag,
                clause_proofs=(),
                environment_fingerprint=environment.environment_fingerprint,
                authorized=False,
                blocker_refs=(f"missing_language_pack:{plan.language_tag}",),
            )
            return CommunicationOutcome(
                plan_ref=plan.plan_id,
                emission_proof=proof,
                realized_message=RealizedMessage(
                    plan_ref=plan.plan_id,
                    language_tag=plan.language_tag,
                    surface_text="",
                    coverage=(),
                    realized_clause_refs=(),
                    blocked_clause_refs=tuple(
                        clause.clause_id for clause in plan.clauses
                    ),
                    emission_proof_ref="",
                ),
                dispatched=False,
                blocker_refs=proof.blocker_refs,
            )

        proof = self._gate.authorize(plan, pack, environment)
        realized = self._realizer.realize(plan, proof, pack)
        if not proof.authorized or not realized.surface_text:
            return CommunicationOutcome(
                plan_ref=plan.plan_id,
                emission_proof=proof,
                realized_message=realized,
                dispatched=False,
                blocker_refs=proof.blocker_refs,
            )

        output_event_ref = self._dispatch(
            realized.surface_text,
            plan.channel,
        )
        return CommunicationOutcome(
            plan_ref=plan.plan_id,
            emission_proof=proof,
            realized_message=realized,
            dispatched=bool(output_event_ref),
            output_event_ref=output_event_ref,
            blocker_refs=()
            if output_event_ref
            else ("dispatch_failed",),
        )
