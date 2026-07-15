"""Canonical records for semantic message plans and emission proofs."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class UseMode(str, Enum):
    ASSERT = "assert"
    QUALIFIED = "qualified"
    PROBE = "probe"
    MENTION = "mention"
    QUOTE = "quote"


class CoverageKind(str, Enum):
    LEXICALIZATION = "lexicalization"
    GRAMMATICAL_MORPHEME = "grammatical_morpheme"
    REFERRING_EXPRESSION = "referring_expression"
    ROLE_VALUE = "role_value"
    MENTION = "mention"
    QUOTATION = "quotation"
    PUNCTUATION = "punctuation"
    SPACING = "spacing"


@dataclass(frozen=True, slots=True)
class SemanticRoleValue:
    role_key: str
    value_ref: str
    value_kind: str = "referent"
    semantic_key: str = ""
    surface_hint: str = ""
    use_mode: UseMode = UseMode.ASSERT
    provenance_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PlannedClause:
    clause_id: str
    predicate_key: str
    roles: tuple[SemanticRoleValue, ...]
    communicative_force: str
    polarity: str = "positive"
    modality: str = "actual"
    context_ref: str = ""
    valid_time_ref: str = ""
    qualification_key: str = ""
    required: bool = True
    provenance_refs: tuple[str, ...] = ()

    def role(self, key: str) -> SemanticRoleValue | None:
        return next((role for role in self.roles if role.role_key == key), None)


@dataclass(frozen=True, slots=True)
class SemanticMessagePlan:
    plan_id: str
    clauses: tuple[PlannedClause, ...]
    language_tag: str
    channel: str = "text"
    addressee_refs: tuple[str, ...] = ()
    goal_refs: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SpanCoverage:
    start: int
    end: int
    surface: str
    coverage_kind: CoverageKind
    semantic_ref: str = ""
    schema_ref: str = ""
    contribution_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SelfClaimProof:
    clause_ref: str
    policy_ref: str
    evidence_refs: tuple[str, ...]
    authorized: bool
    blocker_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ClauseEmissionProof:
    clause_ref: str
    foundation_contract_ref: str
    role_grounding_refs: tuple[str, ...]
    lexicalization_refs: tuple[str, ...]
    construction_ref: str
    self_claim_proof: SelfClaimProof | None
    coverage: tuple[SpanCoverage, ...]
    round_trip_case_ref: str
    authorized: bool
    blocker_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SemanticEmissionProof:
    plan_ref: str
    language_tag: str
    clause_proofs: tuple[ClauseEmissionProof, ...]
    environment_fingerprint: str
    authorized: bool
    blocker_refs: tuple[str, ...] = ()

    def for_clause(self, clause_ref: str) -> ClauseEmissionProof | None:
        return next(
            (proof for proof in self.clause_proofs if proof.clause_ref == clause_ref),
            None,
        )


@dataclass(frozen=True, slots=True)
class RealizedMessage:
    plan_ref: str
    language_tag: str
    surface_text: str
    coverage: tuple[SpanCoverage, ...]
    realized_clause_refs: tuple[str, ...]
    blocked_clause_refs: tuple[str, ...]
    emission_proof_ref: str
