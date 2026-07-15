"""Canonical v3.4.3 proof-carrying renderer.

This replaces content-kind English switches.  The renderer delegates all
word/morpheme choice to a versioned language pack and refuses output without a
SemanticEmissionProof.
"""
from __future__ import annotations

from dataclasses import dataclass

from pathlib import Path

from ..model.emission import (
    RealizedMessage,
    SemanticEmissionProof,
    SemanticMessagePlan,
)
from .emission_closure import EmissionEnvironment, SemanticEmissionGate
from .realizer import SemanticRealizer
from ..schema.lexicalization import LanguageRealizationPack


@dataclass(frozen=True, slots=True)
class SurfacePayload:
    plan_ref: str
    surface_text: str = ""
    language: str = "und"
    channel: str = "text"
    realized_item_refs: tuple[str, ...] = ()
    blocked_item_refs: tuple[str, ...] = ()
    coverage: tuple[object, ...] = ()
    emission_proof_ref: str = ""


class MessageRenderer:
    def __init__(
        self,
        emission_gate: SemanticEmissionGate | None = None,
        language_packs: dict[str, LanguageRealizationPack] | None = None,
    ) -> None:
        self._gate = emission_gate
        self._packs = language_packs or {}
        self._realizer = SemanticRealizer()

    @classmethod
    def load_default(cls, data_root: Path) -> "MessageRenderer":
        from ..schema.foundation_contract import FoundationRegistry
        from ..self_model.claim_authorizer import SelfClaimAuthorizer
        from .emission_closure import SemanticEmissionGate

        foundation_path = data_root / "foundations" / "v343"
        policies_path = (
            foundation_path / "self_claim_policies.json"
        )
        authorizer = (
            SelfClaimAuthorizer.load(policies_path)
            if policies_path.exists()
            else SelfClaimAuthorizer(policies=())
        )
        gate = SemanticEmissionGate(
            FoundationRegistry.load(foundation_path),
            authorizer,
        )
        packs: dict[str, LanguageRealizationPack] = {}
        for path in sorted((data_root / "languages").glob("*/v343/realization.json")):
            pack = LanguageRealizationPack.load(path)
            packs[pack.language_tag] = pack
        return cls(emission_gate=gate, language_packs=packs)

    def authorize(
        self,
        plan: SemanticMessagePlan,
        *,
        environment: EmissionEnvironment | None = None,
        language: str = "en",
        environment_fingerprint: str = "",
    ) -> SemanticEmissionProof:
        pack = self._pack(plan.language_tag)
        if pack is None:
            return SemanticEmissionProof(
                plan_ref=plan.plan_id,
                language_tag=plan.language_tag,
                clause_proofs=(),
                environment_fingerprint=(
                    environment.environment_fingerprint
                    if environment else environment_fingerprint
                ),
                authorized=False,
                blocker_refs=(f"missing_language_pack:{plan.language_tag}",),
            )
        if environment is None:
            from .environment_builder import build_emission_environment
            environment = build_emission_environment(
                plan, pack, environment_fingerprint
            )
        return self._gate.authorize(plan, pack, environment)

    def render(
        self,
        plan: SemanticMessagePlan,
        *,
        environment: EmissionEnvironment | None = None,
        authorization: SemanticEmissionProof | None = None,
        language: str = "en",
        environment_fingerprint: str = "",
        language_pack: object | None = None,
    ) -> SurfacePayload:
        pack = self._pack(plan.language_tag)
        if pack is None:
            return SurfacePayload(
                plan_ref=plan.plan_id,
                language=plan.language_tag,
                channel=plan.channel,
                blocked_item_refs=tuple(clause.clause_id for clause in plan.clauses),
            )
        if environment is None:
            from .environment_builder import build_emission_environment
            environment = build_emission_environment(
                plan, pack, ""
            )
        proof = authorization or self._gate.authorize(plan, pack, environment)
        message = self._realizer.realize(plan, proof, pack)
        return SurfacePayload(
            plan_ref=plan.plan_id,
            surface_text=message.surface_text,
            language=plan.language_tag,
            channel=plan.channel,
            realized_item_refs=message.realized_clause_refs,
            blocked_item_refs=message.blocked_clause_refs,
            coverage=message.coverage,
            emission_proof_ref=message.emission_proof_ref,
        )

    def _pack(self, language_tag: str) -> LanguageRealizationPack | None:
        return self._packs.get(language_tag) or self._packs.get(
            language_tag.split("-", 1)[0]
        )
