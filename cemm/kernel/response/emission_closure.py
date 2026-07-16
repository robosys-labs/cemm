"""Semantic Emission Closure Law.

A clause is public only if its predicate contract, roles, self-state claims,
lexicalizations, grammar construction, and round-trip competence all close.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..model.emission import (
    ClauseEmissionProof,
    CoverageKind,
    PlannedClause,
    SemanticEmissionProof,
    SemanticMessagePlan,
    SpanCoverage,
    UseMode,
)
from ..model.requirements import RequirementAssessment
from ..schema.foundation_contract import FoundationRegistry, OperationClass
from ..schema.lexicalization import LanguageRealizationPack, SegmentKind
from ..self_model.claim_authorizer import ClaimEvidence, SelfClaimAuthorizer


@dataclass(frozen=True, slots=True)
class EmissionEnvironment:
    environment_fingerprint: str
    grounding_refs: frozenset[str]
    active_schema_refs: frozenset[str]
    passed_competence_case_refs: frozenset[str]
    passed_round_trip_case_refs: frozenset[str]
    claim_evidence: tuple[ClaimEvidence, ...] = ()
    requirement_assessments: tuple[RequirementAssessment, ...] = ()


class SemanticEmissionGate:
    def __init__(
        self,
        foundations: FoundationRegistry,
        self_claim_authorizer: SelfClaimAuthorizer,
    ) -> None:
        self._foundations = foundations
        self._self_claims = self_claim_authorizer

    def authorize(
        self,
        plan: SemanticMessagePlan,
        pack: LanguageRealizationPack,
        environment: EmissionEnvironment,
    ) -> SemanticEmissionProof:
        clause_proofs = tuple(
            self._authorize_clause(clause, pack, environment)
            for clause in plan.clauses
        )
        blockers = tuple(
            blocker
            for proof in clause_proofs
            for blocker in proof.blocker_refs
        )
        return SemanticEmissionProof(
            plan_ref=plan.plan_id,
            language_tag=plan.language_tag,
            clause_proofs=clause_proofs,
            environment_fingerprint=environment.environment_fingerprint,
            authorized=bool(clause_proofs)
            and all(proof.authorized for proof in clause_proofs),
            blocker_refs=tuple(dict.fromkeys(blockers)),
        )

    def _authorize_clause(
        self,
        clause: PlannedClause,
        pack: LanguageRealizationPack,
        environment: EmissionEnvironment,
    ) -> ClauseEmissionProof:
        blockers: list[str] = []
        lexicalization_refs: list[str] = []
        coverage: list[SpanCoverage] = []

        contract = self._foundations.predicate(clause.predicate_key)
        if contract is None:
            blockers.append(f"missing_foundation_contract:{clause.predicate_key}")
        elif not contract.permits(OperationClass.REALIZE):
            blockers.append(f"predicate_not_realizable:{clause.predicate_key}")

        role_keys = frozenset(role.role_key for role in clause.roles)
        if contract is not None:
            missing_roles = contract.required_roles() - role_keys
            blockers.extend(f"missing_role:{role}" for role in sorted(missing_roles))
            for role in clause.roles:
                role_contract = contract.role(role.role_key)
                if role_contract is None:
                    blockers.append(f"undeclared_role:{role.role_key}")
                elif role.value_kind not in role_contract.accepted_families:
                    blockers.append(
                        f"invalid_role_family:{role.role_key}:{role.value_kind}"
                    )
                if not role.provenance_refs:
                    blockers.append(f"role_without_provenance:{role.role_key}")

        construction = pack.construction(
            predicate_key=clause.predicate_key,
            communicative_force=clause.communicative_force,
            polarity=clause.polarity,
            qualification_key=clause.qualification_key,
            role_keys=role_keys,
        )
        if construction is None:
            blockers.append(
                f"missing_construction:{pack.language_tag}:{clause.predicate_key}"
            )
            construction_ref = ""
            round_trip_ref = ""
        else:
            construction_ref = construction.schema_id
            if not set(construction.competence_case_refs) <= (
                environment.passed_competence_case_refs
            ):
                blockers.append(
                    f"construction_not_competent:{construction.schema_id}"
                )
            passed_round_trip = tuple(
                ref
                for ref in construction.round_trip_case_refs
                if ref in environment.passed_round_trip_case_refs
            )
            if not passed_round_trip:
                blockers.append(
                    f"construction_round_trip_unproven:{construction.schema_id}"
                )
                round_trip_ref = ""
            else:
                round_trip_ref = passed_round_trip[0]

            for segment in construction.segments:
                if segment.kind in {
                    SegmentKind.PUNCTUATION,
                    SegmentKind.SPACE,
                    SegmentKind.REFERRING_EXPRESSION,
                    SegmentKind.ROLE_VALUE,
                    SegmentKind.MENTION,
                    SegmentKind.QUOTATION,
                }:
                    continue
                if segment.kind is SegmentKind.LEXEME:
                    lexicalization = pack.lexicalizations.get(segment.schema_ref)
                    if lexicalization is None:
                        blockers.append(
                            f"missing_lexicalization:{segment.schema_ref}"
                        )
                    else:
                        lexicalization_refs.append(lexicalization.schema_id)
                        if lexicalization.grounding_contract_ref not in (
                            environment.active_schema_refs
                            | frozenset({contract.contract_id if contract else ""})
                        ):
                            blockers.append(
                                f"lexicalization_ungrounded:{lexicalization.schema_id}"
                            )
                        if not set(lexicalization.competence_case_refs) <= (
                            environment.passed_competence_case_refs
                        ):
                            blockers.append(
                                f"lexicalization_not_competent:{lexicalization.schema_id}"
                            )
                        if not set(lexicalization.round_trip_case_refs) & (
                            environment.passed_round_trip_case_refs
                        ):
                            blockers.append(
                                f"lexicalization_round_trip_unproven:"
                                f"{lexicalization.schema_id}"
                            )
                elif segment.kind is SegmentKind.GRAMMATICAL_MORPHEME:
                    morpheme = pack.morphemes.get(segment.schema_ref)
                    if morpheme is None:
                        blockers.append(f"missing_morpheme:{segment.schema_ref}")
                    elif not set(morpheme.competence_case_refs) <= (
                        environment.passed_competence_case_refs
                    ):
                        blockers.append(
                            f"morpheme_not_competent:{morpheme.schema_id}"
                        )
                    elif not set(morpheme.round_trip_case_refs) & (
                        environment.passed_round_trip_case_refs
                    ):
                        blockers.append(
                            f"morpheme_round_trip_unproven:{morpheme.schema_id}"
                        )

        realized_role_keys = frozenset(
            segment.role_key
            for segment in (construction.segments if construction else ())
            if segment.kind is SegmentKind.ROLE_VALUE
        )
        mention_role_keys = frozenset(
            segment.role_key
            for segment in (construction.segments if construction else ())
            if segment.kind in {SegmentKind.MENTION, SegmentKind.QUOTATION}
        )
        for role in clause.roles:
            if role.role_key in realized_role_keys and role.semantic_key and not role.semantic_key.startswith("value:"):
                lexicalization = pack.lexicalization(
                    role.semantic_key, role.use_mode.value
                )
                if lexicalization is None:
                    blockers.append(
                        f"unrealizable_role_semantics:{role.role_key}:"
                        f"{role.semantic_key}"
                    )
                else:
                    lexicalization_refs.append(lexicalization.schema_id)
            elif role.role_key in mention_role_keys:
                expected_mode = (
                    UseMode.MENTION
                    if any(
                        segment.role_key == role.role_key
                        and segment.kind is SegmentKind.MENTION
                        for segment in construction.segments
                    )
                    else UseMode.QUOTE
                )
                if role.use_mode is not expected_mode or not role.surface_hint:
                    blockers.append(
                        f"invalid_surface_preservation:{role.role_key}"
                    )
            elif not role.semantic_key and role.use_mode not in {
                UseMode.MENTION,
                UseMode.QUOTE,
            } and role.value_kind not in {
                "referent",
                "value",
                "context",
                "proposition",
            }:
                blockers.append(f"unlicensed_opaque_role:{role.role_key}")

        self_claim_proof = self._self_claims.authorize(
            clause,
            evidence=environment.claim_evidence,
            requirement_assessments=environment.requirement_assessments,
        )
        if self_claim_proof is not None and not self_claim_proof.authorized:
            blockers.extend(self_claim_proof.blocker_refs)

        if not clause.provenance_refs:
            blockers.append("clause_without_provenance")

        return ClauseEmissionProof(
            clause_ref=clause.clause_id,
            foundation_contract_ref=contract.contract_id if contract else "",
            role_grounding_refs=tuple(
                ref
                for role in clause.roles
                for ref in role.provenance_refs
            ),
            lexicalization_refs=tuple(dict.fromkeys(lexicalization_refs)),
            construction_ref=construction_ref,
            self_claim_proof=self_claim_proof,
            coverage=tuple(coverage),
            round_trip_case_ref=round_trip_ref,
            authorized=not blockers,
            blocker_refs=tuple(dict.fromkeys(blockers)),
        )
