"""Exact candidate-batch verification over one immutable Proposal Context.

VERIFY consumes the complete ranked proposal once.  It independently replays
Program ABI 2 pointers, validates Source Coverage ABI 2, compiles canonical
Semantic Expression ABI 1, and checks the retained proof domains.  It never
opens authority data, repairs a candidate, or sums duplicate derivation scores.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import islice
from typing import TYPE_CHECKING, Any, Iterable, Literal, Mapping

from .canonical import stable_ref
from .config import RuntimeConfig
from .coverage import CoverageReceipt, CoverageVerifier
from .expressions import (
    CompilationFailure,
    CompilationProof,
    CompilationSuccess,
    GroundedReference,
    LiteralValue,
    RoleBinding,
    SemanticApplication,
    SemanticExpression,
    SemanticExpressionCompiler,
    VerifiedMeaning,
)
from .programs import (
    ACTION_ABI_HASH,
    PERSISTENT_OPERATORS,
    SWITCH_ACTION_TYPES,
    ProgramAction,
    SemanticSwitchProgram,
)
from .proposal_context import ProposalContext
from .verifier_reconstruction import reconstruct_expected_expression as _reconstruct_r2_expression

if TYPE_CHECKING:
    from .proposal import ProposalResult, RankedProgramCandidate

VERIFICATION_BATCH_ABI_VERSION = 2
VERIFICATION_ABI_VERSION = VERIFICATION_BATCH_ABI_VERSION
VerificationStatus = Literal["selected", "rejected", "abstained", "ambiguous"]

_RELEASE = RuntimeConfig.release()
_MAX_CANDIDATES = _RELEASE.max_complete_candidates
_MAX_EXPLORED_STATES = _RELEASE.max_beam_states * _RELEASE.max_applications
_MAX_PROVENANCE_REFS = _RELEASE.max_input_tokens
_MAX_ERRORS = _RELEASE.max_input_tokens * 8 + 64
_MAX_REF = 256
_MAX_DETAIL = 4096

__all__ = [
    "VERIFICATION_BATCH_ABI_VERSION",
    "VERIFICATION_ABI_VERSION",
    "VerificationError",
    "CandidateVerificationReceipt",
    "VerificationBatch",
    "LegalActionIndex",
    "ActionMasker",
    "ExactProgramVerifier",
]


def _required(value: object, field: str) -> str:
    if type(value) is not str or not value or len(value) > _MAX_REF:
        raise ValueError(f"{field} must be a bounded non-empty string")
    return value


def _optional(value: object, field: str) -> str | None:
    return None if value is None else _required(value, field)


def _bounded(values: Iterable[Any], maximum: int, field: str) -> tuple[Any, ...]:
    if isinstance(values, (str, bytes, Mapping)):
        raise ValueError(f"{field} must be an iterable of values")
    try:
        result = tuple(islice(iter(values), maximum + 1))
    except TypeError as exc:
        raise ValueError(f"{field} must be iterable") from exc
    if len(result) > maximum:
        raise ValueError(f"{field} exceeds the release bound")
    return result


def _exact(data: Mapping[str, Any], expected: frozenset[str], owner: str) -> None:
    if not isinstance(data, Mapping) or set(data) != expected:
        raise ValueError(f"{owner} fields must match the canonical schema exactly")


def _array(value: object, field: str) -> list[Any]:
    if type(value) is not list:
        raise ValueError(f"{field} must use canonical list encoding")
    return value


@dataclass(frozen=True)
class VerificationError:
    code: str
    detail: str = ""
    action_ref: str | None = None

    def __post_init__(self) -> None:
        _required(self.code, "verification error code")
        if type(self.detail) is not str or len(self.detail) > _MAX_DETAIL:
            raise ValueError("verification error detail must be a bounded string")
        _optional(self.action_ref, "verification error action_ref")

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "detail": self.detail,
            "action_ref": self.action_ref,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "VerificationError":
        _exact(data, frozenset({"code", "detail", "action_ref"}), "VerificationError")
        result = cls(
            code=_required(data["code"], "verification error code"),
            detail=data["detail"],
            action_ref=_optional(data["action_ref"], "verification error action_ref"),
        )
        if result.as_dict() != dict(data):
            raise ValueError("non-canonical VerificationError encoding")
        return result


def _proposal_candidate_ref(
    *,
    candidate_rank: int,
    score_q: int,
    program_ref: str,
    candidate_provenance_refs: tuple[str, ...],
) -> str:
    return stable_ref(
        "proposal_candidate",
        {
            "proposal_result_abi_version": 2,
            "rank": candidate_rank,
            "score_q": score_q,
            "program_ref": program_ref,
            "provenance_refs": list(candidate_provenance_refs),
        },
    )


def _receipt_material(
    *,
    candidate_ref: str,
    candidate_index: int,
    candidate_rank: int,
    score_q: int,
    candidate_provenance_refs: tuple[str, ...],
    program_ref: str,
    expression: SemanticExpression | None,
    compilation_proof: CompilationProof | None,
    coverage_receipt: CoverageReceipt,
    verification_errors: tuple[VerificationError, ...],
) -> dict[str, Any]:
    return {
        "abi_version": VERIFICATION_BATCH_ABI_VERSION,
        "candidate_ref": candidate_ref,
        "candidate_index": candidate_index,
        "candidate_rank": candidate_rank,
        "score_q": score_q,
        "candidate_provenance_refs": list(candidate_provenance_refs),
        "program_ref": program_ref,
        "expression_ref": expression.expression_ref if expression is not None else None,
        "compilation_proof_ref": (
            compilation_proof.proof_ref if compilation_proof is not None else None
        ),
        "coverage_receipt_ref": coverage_receipt.coverage_receipt_ref,
        "verification_errors": [row.as_dict() for row in verification_errors],
    }


@dataclass(frozen=True, init=False)
class CandidateVerificationReceipt:
    receipt_ref: str
    candidate_ref: str
    candidate_index: int
    candidate_rank: int
    score_q: int
    candidate_provenance_refs: tuple[str, ...]
    program_ref: str
    expression: SemanticExpression | None
    compilation_proof: CompilationProof | None
    coverage_receipt: CoverageReceipt
    verification_errors: tuple[VerificationError, ...]

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use CandidateVerificationReceipt.create")

    @classmethod
    def _canonical(
        cls, receipt_ref: str, **values: Any
    ) -> "CandidateVerificationReceipt":
        result = object.__new__(cls)
        object.__setattr__(result, "receipt_ref", receipt_ref)
        for field, value in values.items():
            object.__setattr__(result, field, value)
        return result

    @classmethod
    def create(
        cls,
        *,
        candidate_ref: str,
        candidate_index: int,
        candidate_rank: int,
        score_q: int,
        candidate_provenance_refs: Iterable[str],
        program_ref: str,
        expression: SemanticExpression | None,
        compilation_proof: CompilationProof | None,
        coverage_receipt: CoverageReceipt,
        verification_errors: Iterable[VerificationError],
    ) -> "CandidateVerificationReceipt":
        candidate_ref = _required(candidate_ref, "candidate_ref")
        program_ref = _required(program_ref, "program_ref")
        if (
            type(candidate_index) is not int
            or candidate_index < 0
            or candidate_index >= _MAX_CANDIDATES
        ):
            raise ValueError("candidate_index must be a bounded non-negative exact int")
        if (
            type(candidate_rank) is not int
            or candidate_rank < 0
            or candidate_rank >= _MAX_CANDIDATES
        ):
            raise ValueError("candidate_rank must be a bounded non-negative exact int")
        if candidate_rank != candidate_index:
            raise ValueError("candidate rank and verification index differ")
        if type(score_q) is not int or not -(2**63) <= score_q < 2**63:
            raise ValueError("score_q must be an exact signed 64-bit int")
        provenance = _bounded(
            candidate_provenance_refs,
            _MAX_PROVENANCE_REFS,
            "candidate provenance refs",
        )
        for ref in provenance:
            _required(ref, "candidate provenance ref")
        if len(provenance) != len(set(provenance)):
            raise ValueError("candidate provenance refs must be unique")
        expected_candidate_ref = _proposal_candidate_ref(
            candidate_rank=candidate_rank,
            score_q=score_q,
            program_ref=program_ref,
            candidate_provenance_refs=provenance,
        )
        if candidate_ref != expected_candidate_ref:
            raise ValueError("candidate_ref does not bind exact candidate material")
        if not isinstance(coverage_receipt, CoverageReceipt):
            raise ValueError("coverage_receipt must be CoverageReceipt")
        try:
            if (
                CoverageReceipt.from_dict(coverage_receipt.as_dict())
                != coverage_receipt
            ):
                raise ValueError("coverage receipt changed during canonical round trip")
        except (TypeError, ValueError) as exc:
            raise ValueError("coverage receipt is not canonical") from exc
        errors = _bounded(verification_errors, _MAX_ERRORS, "verification errors")
        if any(not isinstance(row, VerificationError) for row in errors):
            raise ValueError(
                "verification_errors must contain VerificationError values"
            )
        if (expression is None) != (compilation_proof is None):
            raise ValueError(
                "expression and compilation proof must be present together"
            )
        if expression is not None and not isinstance(expression, SemanticExpression):
            raise ValueError("expression must be SemanticExpression")
        if compilation_proof is not None and not isinstance(
            compilation_proof, CompilationProof
        ):
            raise ValueError("compilation_proof must be CompilationProof")
        if expression is not None and compilation_proof is not None:
            try:
                if SemanticExpression.from_dict(expression.as_dict()) != expression:
                    raise ValueError("expression changed during canonical round trip")
            except (TypeError, ValueError) as exc:
                raise ValueError("expression is not canonical") from exc
            try:
                if (
                    CompilationProof.from_dict(compilation_proof.as_dict())
                    != compilation_proof
                ):
                    raise ValueError(
                        "compilation proof changed during canonical round trip"
                    )
            except (TypeError, ValueError) as exc:
                raise ValueError("compilation proof is not canonical") from exc
        if coverage_receipt.program_ref != program_ref:
            raise ValueError("coverage receipt program lineage mismatch")
        if expression is not None and compilation_proof is not None:
            if compilation_proof.program_ref != program_ref:
                raise ValueError("compilation proof program lineage mismatch")
            if compilation_proof.expression_ref != expression.expression_ref:
                raise ValueError("compilation proof expression lineage mismatch")
            if (
                compilation_proof.proposal_context_ref
                != coverage_receipt.proposal_context_ref
            ):
                raise ValueError("proof and coverage context lineage mismatch")
            if compilation_proof.revision_pin != coverage_receipt.revision_pin:
                raise ValueError("proof and coverage revision lineage mismatch")
        if not errors and (
            expression is None
            or compilation_proof is None
            or not coverage_receipt.executable
        ):
            raise ValueError(
                "error-free receipt must contain executable verified artifacts"
            )
        values = {
            "candidate_ref": candidate_ref,
            "candidate_index": candidate_index,
            "candidate_rank": candidate_rank,
            "score_q": score_q,
            "candidate_provenance_refs": provenance,
            "program_ref": program_ref,
            "expression": expression,
            "compilation_proof": compilation_proof,
            "coverage_receipt": coverage_receipt,
            "verification_errors": errors,
        }
        return cls._canonical(
            stable_ref("candidate_verification_receipt", _receipt_material(**values)),
            **values,
        )

    @property
    def accepted(self) -> bool:
        return (
            not self.verification_errors
            and self.expression is not None
            and self.compilation_proof is not None
            and self.coverage_receipt.executable
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": VERIFICATION_BATCH_ABI_VERSION,
            "receipt_ref": self.receipt_ref,
            "candidate_ref": self.candidate_ref,
            "candidate_index": self.candidate_index,
            "candidate_rank": self.candidate_rank,
            "score_q": self.score_q,
            "candidate_provenance_refs": list(self.candidate_provenance_refs),
            "program_ref": self.program_ref,
            "expression": self.expression.as_dict()
            if self.expression is not None
            else None,
            "compilation_proof": (
                self.compilation_proof.as_dict()
                if self.compilation_proof is not None
                else None
            ),
            "coverage_receipt": self.coverage_receipt.as_dict(),
            "verification_errors": [row.as_dict() for row in self.verification_errors],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CandidateVerificationReceipt":
        _exact(
            data,
            frozenset(
                {
                    "abi_version",
                    "receipt_ref",
                    "candidate_ref",
                    "candidate_index",
                    "candidate_rank",
                    "score_q",
                    "candidate_provenance_refs",
                    "program_ref",
                    "expression",
                    "compilation_proof",
                    "coverage_receipt",
                    "verification_errors",
                }
            ),
            "CandidateVerificationReceipt",
        )
        if (
            type(data["abi_version"]) is not int
            or data["abi_version"] != VERIFICATION_BATCH_ABI_VERSION
        ):
            raise ValueError("unsupported Verification Batch ABI")
        expression_data = data["expression"]
        proof_data = data["compilation_proof"]
        coverage_data = data["coverage_receipt"]
        if expression_data is not None and not isinstance(expression_data, Mapping):
            raise ValueError("expression must be an object or null")
        if proof_data is not None and not isinstance(proof_data, Mapping):
            raise ValueError("compilation_proof must be an object or null")
        if not isinstance(coverage_data, Mapping):
            raise ValueError("coverage_receipt must be an object")
        rebuilt = cls.create(
            candidate_ref=_required(data["candidate_ref"], "candidate_ref"),
            candidate_index=data["candidate_index"],
            candidate_rank=data["candidate_rank"],
            score_q=data["score_q"],
            candidate_provenance_refs=(
                _required(ref, "candidate provenance ref")
                for ref in _array(
                    data["candidate_provenance_refs"],
                    "candidate_provenance_refs",
                )
            ),
            program_ref=_required(data["program_ref"], "program_ref"),
            expression=(
                SemanticExpression.from_dict(expression_data)
                if expression_data is not None
                else None
            ),
            compilation_proof=(
                CompilationProof.from_dict(proof_data)
                if proof_data is not None
                else None
            ),
            coverage_receipt=CoverageReceipt.from_dict(coverage_data),
            verification_errors=(
                VerificationError.from_dict(row)
                for row in _array(data["verification_errors"], "verification_errors")
            ),
        )
        if data["receipt_ref"] != rebuilt.receipt_ref:
            raise ValueError("CandidateVerificationReceipt ref mismatch")
        if rebuilt.as_dict() != dict(data):
            raise ValueError("non-canonical CandidateVerificationReceipt encoding")
        return rebuilt


def _is_better_receipt(
    candidate: CandidateVerificationReceipt,
    current: CandidateVerificationReceipt,
) -> bool:
    return candidate.score_q > current.score_q or (
        candidate.score_q == current.score_q
        and candidate.candidate_rank < current.candidate_rank
    )


def _derive_batch_outcome(
    receipts: tuple[CandidateVerificationReceipt, ...],
    ambiguity_margin_q: int,
) -> tuple[
    VerificationStatus,
    CandidateVerificationReceipt | None,
    tuple[str, ...],
]:
    if not receipts:
        return "abstained", None, ()
    best_by_expression: dict[str, CandidateVerificationReceipt] = {}
    best: CandidateVerificationReceipt | None = None
    best_expression_ref: str | None = None
    for receipt in receipts:
        if not receipt.accepted or receipt.expression is None:
            continue
        expression_ref = receipt.expression.expression_ref
        current = best_by_expression.get(expression_ref)
        if current is not None and not _is_better_receipt(receipt, current):
            continue
        best_by_expression[expression_ref] = receipt
        if (
            best is None
            or expression_ref == best_expression_ref
            or _is_better_receipt(receipt, best)
        ):
            best = receipt
            best_expression_ref = expression_ref
    if best is None:
        return "rejected", None, ()
    contenders = [best]
    for receipt in best_by_expression.values():
        if receipt.candidate_ref == best.candidate_ref:
            continue
        if best.score_q - receipt.score_q <= ambiguity_margin_q:
            contenders.append(receipt)
    if len(contenders) > 1:
        return (
            "ambiguous",
            None,
            tuple(
                row.expression.expression_ref
                for row in contenders
                if row.expression is not None
            ),
        )
    return "selected", best, ()


def _batch_material(
    *,
    proposal_ref: str,
    proposal_context_ref: str,
    candidate_receipts: tuple[CandidateVerificationReceipt, ...],
    ambiguity_margin_q: int,
    status: VerificationStatus,
    selected_candidate_ref: str | None,
    selected_meaning: VerifiedMeaning | None,
    ambiguity_expression_refs: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "abi_version": VERIFICATION_BATCH_ABI_VERSION,
        "proposal_ref": proposal_ref,
        "proposal_context_ref": proposal_context_ref,
        "candidate_receipt_refs": [row.receipt_ref for row in candidate_receipts],
        "ambiguity_margin_q": ambiguity_margin_q,
        "status": status,
        "selected_candidate_ref": selected_candidate_ref,
        "selected_meaning_ref": (
            selected_meaning.verified_meaning_ref
            if selected_meaning is not None
            else None
        ),
        "ambiguity_expression_refs": list(ambiguity_expression_refs),
    }


@dataclass(frozen=True, init=False)
class VerificationBatch:
    batch_ref: str
    proposal_ref: str
    proposal_context_ref: str
    candidate_receipts: tuple[CandidateVerificationReceipt, ...]
    ambiguity_margin_q: int
    status: VerificationStatus
    selected_candidate_ref: str | None
    selected_meaning: VerifiedMeaning | None
    ambiguity_expression_refs: tuple[str, ...]

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use VerificationBatch.create")

    @classmethod
    def _canonical(cls, batch_ref: str, **values: Any) -> "VerificationBatch":
        result = object.__new__(cls)
        object.__setattr__(result, "batch_ref", batch_ref)
        for field, value in values.items():
            object.__setattr__(result, field, value)
        return result

    @classmethod
    def create(
        cls,
        *,
        proposal_ref: str,
        proposal_context_ref: str,
        candidate_receipts: Iterable[CandidateVerificationReceipt],
        ambiguity_margin_q: int,
        status: VerificationStatus,
        selected_candidate_ref: str | None,
        selected_meaning: VerifiedMeaning | None,
        ambiguity_expression_refs: Iterable[str],
    ) -> "VerificationBatch":
        proposal_ref = _required(proposal_ref, "proposal_ref")
        proposal_context_ref = _required(proposal_context_ref, "proposal_context_ref")
        receipts = _bounded(candidate_receipts, _MAX_CANDIDATES, "candidate receipts")
        if any(not isinstance(row, CandidateVerificationReceipt) for row in receipts):
            raise ValueError("candidate_receipts must contain exact receipt values")
        for row in receipts:
            provenance = _bounded(
                row.candidate_provenance_refs,
                _MAX_PROVENANCE_REFS,
                "candidate provenance refs",
            )
            for ref in provenance:
                _required(ref, "candidate provenance ref")
            if len(provenance) != len(set(provenance)):
                raise ValueError("candidate provenance refs must be unique")
            expected_candidate_ref = _proposal_candidate_ref(
                candidate_rank=row.candidate_rank,
                score_q=row.score_q,
                program_ref=row.program_ref,
                candidate_provenance_refs=provenance,
            )
            if row.candidate_ref != expected_candidate_ref:
                raise ValueError("candidate_ref does not bind exact candidate material")
            expected_receipt_ref = stable_ref(
                "candidate_verification_receipt",
                _receipt_material(
                    candidate_ref=row.candidate_ref,
                    candidate_index=row.candidate_index,
                    candidate_rank=row.candidate_rank,
                    score_q=row.score_q,
                    candidate_provenance_refs=provenance,
                    program_ref=row.program_ref,
                    expression=row.expression,
                    compilation_proof=row.compilation_proof,
                    coverage_receipt=row.coverage_receipt,
                    verification_errors=row.verification_errors,
                ),
            )
            if row.receipt_ref != expected_receipt_ref:
                raise ValueError("candidate receipt ref mismatch")
        if tuple(row.candidate_index for row in receipts) != tuple(
            range(len(receipts))
        ):
            raise ValueError("candidate receipt indices must be contiguous")
        if tuple(row.candidate_rank for row in receipts) != tuple(range(len(receipts))):
            raise ValueError("candidate receipt ranks must be contiguous and ordered")
        if type(ambiguity_margin_q) is not int or not 0 <= ambiguity_margin_q < 2**63:
            raise ValueError("ambiguity_margin_q must be a non-negative exact int")
        candidate_refs = tuple(row.candidate_ref for row in receipts)
        if len(candidate_refs) != len(set(candidate_refs)):
            raise ValueError("candidate receipt refs must be unique")
        if any(
            row.coverage_receipt.proposal_context_ref != proposal_context_ref
            for row in receipts
        ):
            raise ValueError("candidate receipt proposal context mismatch")
        if type(status) is not str or status not in {
            "selected",
            "rejected",
            "abstained",
            "ambiguous",
        }:
            raise ValueError("invalid verification batch status")
        selected_candidate_ref = _optional(
            selected_candidate_ref, "selected_candidate_ref"
        )
        if selected_meaning is not None and not isinstance(
            selected_meaning, VerifiedMeaning
        ):
            raise ValueError("selected_meaning must be VerifiedMeaning or null")
        if selected_meaning is not None:
            try:
                if (
                    VerifiedMeaning.from_dict(selected_meaning.as_dict())
                    != selected_meaning
                ):
                    raise ValueError(
                        "selected meaning changed during canonical round trip"
                    )
            except (TypeError, ValueError) as exc:
                raise ValueError("selected meaning is not canonical") from exc
        ambiguity = _bounded(
            ambiguity_expression_refs, _MAX_CANDIDATES, "ambiguity expression refs"
        )
        for ref in ambiguity:
            _required(ref, "ambiguity expression ref")
        if len(ambiguity) != len(set(ambiguity)):
            raise ValueError("ambiguity expression refs must be unique")
        receipt_by_candidate = {row.candidate_ref: row for row in receipts}
        derived_status, derived_selected, derived_ambiguity = _derive_batch_outcome(
            receipts,
            ambiguity_margin_q,
        )
        if status != derived_status:
            raise ValueError(
                f"declared {status} verification status differs from derived outcome"
            )
        if status == "selected":
            if selected_candidate_ref is None or selected_meaning is None:
                raise ValueError("selected batch requires complete selected lineage")
            if ambiguity:
                raise ValueError("selected batch cannot carry ambiguity")
            selected = receipt_by_candidate.get(selected_candidate_ref)
            if selected is None or not selected.accepted:
                raise ValueError("selected candidate must identify an accepted receipt")
            if derived_selected is None or selected is not derived_selected:
                raise ValueError(
                    "selected candidate is not the derived winning lineage"
                )
            proof = selected.compilation_proof
            if proof is None or selected.expression is None:
                raise ValueError("selected receipt lacks verified artifacts")
            if (
                selected_meaning.program_ref != selected.program_ref
                or selected_meaning.expression != selected.expression
                or selected_meaning.grounding_refs != proof.grounding_refs
                or selected_meaning.coverage_receipt_ref
                != selected.coverage_receipt.coverage_receipt_ref
                or selected_meaning.compilation_proof_ref != proof.proof_ref
                or selected_meaning.verification_receipt_ref != selected.receipt_ref
                or selected_meaning.revision_pin
                != selected.coverage_receipt.revision_pin
            ):
                raise ValueError("selected meaning lineage mismatch")
        else:
            if selected_candidate_ref is not None or selected_meaning is not None:
                raise ValueError("non-selected batch cannot carry selected lineage")
            if status == "ambiguous":
                if len(ambiguity) < 2:
                    raise ValueError(
                        "ambiguous batch requires two distinct expressions"
                    )
                if tuple(ambiguity) != derived_ambiguity:
                    raise ValueError("ambiguity does not match the derived margin set")
            elif ambiguity:
                raise ValueError("non-ambiguous batch cannot carry ambiguity")
            if status == "abstained" and receipts:
                raise ValueError("abstained batch cannot carry candidate receipts")
            if status == "rejected":
                if not receipts:
                    raise ValueError("rejected batch requires candidate receipts")
                if any(row.accepted for row in receipts):
                    raise ValueError("rejected batch cannot conceal accepted receipts")
        values = {
            "proposal_ref": proposal_ref,
            "proposal_context_ref": proposal_context_ref,
            "candidate_receipts": receipts,
            "ambiguity_margin_q": ambiguity_margin_q,
            "status": status,
            "selected_candidate_ref": selected_candidate_ref,
            "selected_meaning": selected_meaning,
            "ambiguity_expression_refs": ambiguity,
        }
        return cls._canonical(
            stable_ref("verification_batch", _batch_material(**values)), **values
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": VERIFICATION_BATCH_ABI_VERSION,
            "batch_ref": self.batch_ref,
            "proposal_ref": self.proposal_ref,
            "proposal_context_ref": self.proposal_context_ref,
            "candidate_receipts": [row.as_dict() for row in self.candidate_receipts],
            "ambiguity_margin_q": self.ambiguity_margin_q,
            "status": self.status,
            "selected_candidate_ref": self.selected_candidate_ref,
            "selected_meaning": (
                self.selected_meaning.as_dict()
                if self.selected_meaning is not None
                else None
            ),
            "ambiguity_expression_refs": list(self.ambiguity_expression_refs),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "VerificationBatch":
        _exact(
            data,
            frozenset(
                {
                    "abi_version",
                    "batch_ref",
                    "proposal_ref",
                    "proposal_context_ref",
                    "candidate_receipts",
                    "ambiguity_margin_q",
                    "status",
                    "selected_candidate_ref",
                    "selected_meaning",
                    "ambiguity_expression_refs",
                }
            ),
            "VerificationBatch",
        )
        if (
            type(data["abi_version"]) is not int
            or data["abi_version"] != VERIFICATION_BATCH_ABI_VERSION
        ):
            raise ValueError("unsupported Verification Batch ABI")
        selected_data = data["selected_meaning"]
        if selected_data is not None and not isinstance(selected_data, Mapping):
            raise ValueError("selected_meaning must be an object or null")
        rebuilt = cls.create(
            proposal_ref=_required(data["proposal_ref"], "proposal_ref"),
            proposal_context_ref=_required(
                data["proposal_context_ref"], "proposal_context_ref"
            ),
            candidate_receipts=(
                CandidateVerificationReceipt.from_dict(row)
                for row in _array(data["candidate_receipts"], "candidate_receipts")
            ),
            ambiguity_margin_q=data["ambiguity_margin_q"],
            status=data["status"],
            selected_candidate_ref=_optional(
                data["selected_candidate_ref"], "selected_candidate_ref"
            ),
            selected_meaning=(
                VerifiedMeaning.from_dict(selected_data)
                if selected_data is not None
                else None
            ),
            ambiguity_expression_refs=(
                _required(row, "ambiguity expression ref")
                for row in _array(
                    data["ambiguity_expression_refs"], "ambiguity_expression_refs"
                )
            ),
        )
        if data["batch_ref"] != rebuilt.batch_ref:
            raise ValueError("VerificationBatch ref mismatch")
        if rebuilt.as_dict() != dict(data):
            raise ValueError("non-canonical VerificationBatch encoding")
        return rebuilt


def _prefix_state(
    context: ProposalContext, prefix: tuple[ProgramAction, ...]
) -> tuple[set[str], dict[str, Any], set[str], dict[str, set[str]], bool]:
    designations: set[str] = set()
    applications: dict[str, Any] = {}
    nodes: set[str] = set()
    bound_roles: dict[str, set[str]] = {}
    terminal = False
    for action in prefix:
        args = action.arguments
        if action.action_type == "select_designation":
            designations.add(args[0])
        elif action.action_type == "instantiate_operator":
            frame = context.frame(args[1])
            if frame is not None:
                applications[args[0]] = frame
                nodes.add(args[0])
                bound_roles.setdefault(args[0], set())
        elif action.action_type in {"bind_role", "bind_reference"}:
            bound_roles.setdefault(args[0], set()).add(args[1])
        elif action.action_type == "bind_nested_application":
            if args[0] == "role":
                bound_roles.setdefault(args[1], set()).add(args[2])
            else:
                nodes.add(args[1])
        elif action.action_type == "attach_scope":
            nodes.add(args[0])
        elif action.action_type == "project_variable":
            nodes.add(args[0])
        elif action.action_type in {"complete_program", "abstain"}:
            terminal = True
    return designations, applications, nodes, bound_roles, terminal


def _prefix_budget(
    prefix: tuple[ProgramAction, ...]
) -> tuple[int, int, int]:
    """Track budget use: (application_count, action_count, node_count).

    Per R2 plan section 3.1: track application, action, root, and
    graph-depth budget use without authority access.
    """
    application_count = 0
    action_count = len(prefix)
    node_count = 0
    for action in prefix:
        if action.action_type == "instantiate_operator":
            application_count += 1
            node_count += 1
        elif action.action_type == "bind_nested_application":
            if action.arguments[0] != "role":
                node_count += 1
        elif action.action_type == "attach_scope":
            node_count += 1
        elif action.action_type == "project_variable":
            node_count += 1
    return application_count, action_count, node_count


class LegalActionIndex:
    """Context-local legality predicate with no authority or vocabulary scan."""

    __slots__ = ("_context", "_max_applications", "_max_actions", "_max_nodes")

    def __init__(self, context: ProposalContext, *, max_applications: int = 24, max_actions: int = 256, max_nodes: int = 64) -> None:
        if not isinstance(context, ProposalContext):
            raise ValueError("LegalActionIndex requires one exact ProposalContext")
        self._context = context
        self._max_applications = max_applications
        self._max_actions = max_actions
        self._max_nodes = max_nodes

    @property
    def context(self) -> ProposalContext:
        return self._context

    @property
    def action_abi_hash(self) -> str:
        return ACTION_ABI_HASH

    def is_legal(self, action: ProgramAction, prefix: Iterable[ProgramAction]) -> bool:
        if not isinstance(action, ProgramAction):
            return False
        rows = tuple(prefix)
        if any(not isinstance(row, ProgramAction) for row in rows):
            return False
        if action.action_index != len(rows):
            return False
        if rows and rows[-1].action_type in {"complete_program", "abstain"}:
            return False
        try:
            if ProgramAction.from_dict(action.as_dict()) != action:
                return False
        except (TypeError, ValueError):
            return False
        if not rows:
            return action.action_type == "select_context" and action.arguments == (
                self._context.context_ref,
            )
        if len(rows) == 1:
            return (
                rows[0].action_type == "select_context"
                and action.action_type == "select_mode"
                and self._context.mode_slot(action.arguments[0]) is not None
            )
        if action.action_type in {"select_context", "select_mode", "abstain"}:
            return False
        designations, applications, nodes, bound_roles, _ = _prefix_state(
            self._context, rows
        )
        app_count, action_count, node_count = _prefix_budget(rows)
        args = action.arguments
        if action.action_type == "select_designation":
            return (
                self._context.designation(args[0]) is not None
                and args[0] not in designations
            )
        if action.action_type == "instantiate_operator":
            if app_count >= self._max_applications:
                return False
            frame = self._context.frame(args[1])
            return (
                frame is not None
                and frame.designation_slot_ref in designations
                and args[0] not in nodes
            )
        if action.action_type == "bind_role":
            frame = applications.get(args[0])
            contribution = self._context.contribution(args[2])
            return (
                frame is not None
                and contribution is not None
                and args[1] in set(frame.required_roles) | set(frame.optional_roles)
                and args[1] in contribution.output_ports
                and args[1] not in bound_roles.get(args[0], set())
            )
        if action.action_type == "bind_reference":
            frame = applications.get(args[0])
            reference = self._context.reference(args[2])
            return (
                frame is not None
                and reference is not None
                and args[1] in set(frame.required_roles) | set(frame.optional_roles)
                and args[1] in reference.compatible_roles
                and args[1] not in bound_roles.get(args[0], set())
            )
        if action.action_type == "bind_nested_application":
            if args[0] == "role":
                frame = applications.get(args[1])
                return (
                    frame is not None
                    and args[2] in frame.proposition_roles
                    and args[3] in nodes
                    and args[2] not in bound_roles.get(args[1], set())
                )
            if node_count >= self._max_nodes:
                return False
            link = self._context.expression_link(args[2])
            arity = len(args) - 3
            return (
                link is not None
                and args[1] not in nodes
                and link.min_arity <= arity <= link.max_arity
                and all(ref in nodes for ref in args[3:])
            )
        if action.action_type == "attach_scope":
            if node_count >= self._max_nodes:
                return False
            return (
                args[0] not in nodes
                and self._context.scope(args[1]) is not None
                and args[2] in nodes
            )
        if action.action_type == "project_variable":
            if node_count >= self._max_nodes:
                return False
            variable = self._context.variable(args[1])
            return (
                args[0] not in nodes
                and variable is not None
                and variable.application_frame_ref
                in {frame.slot_ref for frame in applications.values()}
                and args[2] in nodes
            )
        if action.action_type == "propose_transition":
            transition = self._context.transition(args[0])
            frame = applications.get(args[1])
            mode = self._context.mode_slot(rows[1].arguments[0])
            return (
                transition is not None
                and frame is not None
                and transition.application_frame_ref == frame.slot_ref
                and mode is not None
                and mode.mode in transition.compatible_modes
            )
        if action.action_type == "complete_program":
            return bool(applications) and all(
                set(frame.required_roles) <= bound_roles.get(local_ref, set())
                for local_ref, frame in applications.items()
            )
        return False


class ActionMasker:
    """Thin exact mask over the same context-local transition predicate."""

    __slots__ = ("_legal_index",)

    def __init__(self, legal_index: LegalActionIndex) -> None:
        if not isinstance(legal_index, LegalActionIndex):
            raise ValueError("ActionMasker requires LegalActionIndex")
        self._legal_index = legal_index

    @property
    def legal_index(self) -> LegalActionIndex:
        return self._legal_index

    def is_allowed(
        self, action: ProgramAction, prefix: Iterable[ProgramAction]
    ) -> bool:
        return self._legal_index.is_legal(action, prefix)

    def filter_legal(
        self,
        prefix: Iterable[ProgramAction],
        candidates: Iterable[ProgramAction],
    ) -> tuple[ProgramAction, ...]:
        rows = tuple(prefix)
        return tuple(
            candidate
            for candidate in candidates
            if self._legal_index.is_legal(candidate, rows)
        )


def _replay_program(
    program: SemanticSwitchProgram, context: ProposalContext
) -> tuple[VerificationError, ...]:
    errors: list[VerificationError] = []

    def report(
        code: str, detail: str = "", action: ProgramAction | None = None
    ) -> None:
        if len(errors) < _MAX_ERRORS:
            errors.append(
                VerificationError(
                    code,
                    detail,
                    action.action_ref if action is not None else None,
                )
            )

    actions = tuple(program.actions)
    if not actions:
        return (VerificationError("empty_program"),)
    if tuple(row.action_index for row in actions) != tuple(range(len(actions))):
        report("noncontiguous_action_indices")
    if actions[0].action_type != "select_context":
        report("missing_initial_context_selection", action=actions[0])
    if len(actions) < 2 or actions[1].action_type != "select_mode":
        report("missing_initial_mode_selection", action=actions[0])
    if actions[-1].action_type != "complete_program":
        report("invalid_candidate_terminal", action=actions[-1])
    if any(row.action_type in {"complete_program", "abstain"} for row in actions[:-1]):
        report("nonfinal_terminal_action")

    selected_designations: set[str] = set()
    applications: dict[str, Any] = {}
    nodes: set[str] = set()
    bound_roles: dict[str, set[str]] = {}
    selected_mode: Any | None = None
    for action in actions:
        try:
            if ProgramAction.from_dict(action.as_dict()) != action:
                report("action_identity_mismatch", action=action)
        except (TypeError, ValueError):
            report("action_identity_mismatch", action=action)
        if action.action_type not in SWITCH_ACTION_TYPES:
            report("unknown_action_type", action=action)
            continue
        args = action.arguments
        kind = action.action_type
        if kind == "select_context":
            if args != (context.context_ref,):
                report("proposal_context_pointer_mismatch", action=action)
        elif kind == "select_mode":
            selected_mode = context.mode_slot(args[0])
            if selected_mode is None:
                report("unknown_mode_slot", action=action)
            if args[0] != program.mode_slot_ref:
                report("program_mode_pointer_mismatch", action=action)
        elif kind == "select_designation":
            designation = context.designation(args[0])
            if designation is None:
                report("unknown_designation_slot", action=action)
            elif args[0] in selected_designations:
                report("duplicate_designation_selection", action=action)
            else:
                selected_designations.add(args[0])
        elif kind == "instantiate_operator":
            local_ref, frame_ref = args
            frame = context.frame(frame_ref)
            if frame is None:
                report("unknown_application_frame", action=action)
                continue
            if frame.designation_slot_ref not in selected_designations:
                report("unselected_application_designation", action=action)
            designation = context.designation(frame.designation_slot_ref)
            if designation is None:
                report("unknown_application_designation", action=action)
            elif (
                designation.target_ref != frame.predicate_target_ref
                or designation.target_kind != frame.predicate_kind
            ):
                report("application_frame_designation_mismatch", action=action)
            if frame.operator_ref not in PERSISTENT_OPERATORS:
                report("invalid_operator", action=action)
            if local_ref in nodes:
                report("duplicate_local_node", action=action)
            else:
                nodes.add(local_ref)
                applications[local_ref] = frame
                bound_roles[local_ref] = set()
        elif kind in {"bind_role", "bind_reference"}:
            local_ref, role_ref, slot_ref = args
            frame = applications.get(local_ref)
            if frame is None:
                report("unknown_application_ref", action=action)
                continue
            legal_roles = set(frame.required_roles) | set(frame.optional_roles)
            if role_ref not in legal_roles:
                report("frame_role_mismatch", action=action)
            if role_ref in bound_roles[local_ref]:
                report("duplicate_role_binding", action=action)
            if kind == "bind_role":
                contribution = context.contribution(slot_ref)
                if contribution is None:
                    report("unknown_contribution_slot", action=action)
                elif role_ref not in contribution.output_ports:
                    report("contribution_role_mismatch", action=action)
            else:
                reference = context.reference(slot_ref)
                if reference is None:
                    report("unknown_reference_slot", action=action)
                elif role_ref not in reference.compatible_roles:
                    report("reference_role_mismatch", action=action)
            bound_roles[local_ref].add(role_ref)
        elif kind == "bind_nested_application":
            variant = args[0]
            if variant == "role":
                parent_ref, role_ref, child_ref = args[1:]
                frame = applications.get(parent_ref)
                if frame is None:
                    report("unknown_parent_application", action=action)
                else:
                    if role_ref not in frame.proposition_roles:
                        report("nonproposition_nested_role", action=action)
                    if role_ref in bound_roles[parent_ref]:
                        report("duplicate_role_binding", action=action)
                    bound_roles[parent_ref].add(role_ref)
                if child_ref not in nodes:
                    report("unknown_nested_child", action=action)
            else:
                local_ref, slot_ref, *operands = args[1:]
                slot = context.expression_link(slot_ref)
                if slot is None:
                    report("unknown_expression_link_slot", action=action)
                elif not slot.min_arity <= len(operands) <= slot.max_arity:
                    report("expression_link_arity_mismatch", action=action)
                if any(ref not in nodes for ref in operands):
                    report("unknown_expression_link_operand", action=action)
                if local_ref in nodes:
                    report("duplicate_local_node", action=action)
                else:
                    nodes.add(local_ref)
        elif kind == "attach_scope":
            local_ref, slot_ref, operand_ref = args
            if context.scope(slot_ref) is None:
                report("unknown_scope_slot", action=action)
            if operand_ref not in nodes:
                report("unknown_scope_operand", action=action)
            if local_ref in nodes:
                report("duplicate_local_node", action=action)
            else:
                nodes.add(local_ref)
        elif kind == "project_variable":
            local_ref, slot_ref, body_ref = args
            slot = context.variable(slot_ref)
            if slot is None:
                report("unknown_variable_slot", action=action)
            elif slot.application_frame_ref not in {
                frame.slot_ref for frame in applications.values()
            }:
                report("variable_frame_mismatch", action=action)
            if body_ref not in nodes:
                report("unknown_variable_body", action=action)
            if local_ref in nodes:
                report("duplicate_local_node", action=action)
            else:
                nodes.add(local_ref)
        elif kind == "propose_transition":
            slot_ref, source_ref = args
            slot = context.transition(slot_ref)
            frame = applications.get(source_ref)
            if slot is None:
                report("unknown_transition_slot", action=action)
            elif frame is None:
                report("unknown_transition_application", action=action)
            else:
                if slot.application_frame_ref != frame.slot_ref:
                    report("transition_frame_mismatch", action=action)
                if (
                    selected_mode is None
                    or selected_mode.mode not in slot.compatible_modes
                ):
                    report("transition_mode_mismatch", action=action)

    for local_ref, frame in applications.items():
        missing = tuple(
            role for role in frame.required_roles if role not in bound_roles[local_ref]
        )
        if missing:
            report(
                "missing_required_role",
                f"{local_ref}:{','.join(missing)}",
            )
    for root_ref in program.root_refs:
        if root_ref not in nodes:
            report("unknown_program_root", root_ref)
    return tuple(errors)


def _proposal_material(proposal: Any) -> dict[str, Any]:
    return {
        "abi_version": 2,
        "orientation_ref": proposal.orientation_ref,
        "proposal_context_ref": proposal.proposal_context_ref,
        "candidate_refs": [row.candidate_ref for row in proposal.candidates],
        "status": proposal.status,
        "abstention_code": proposal.abstention_code,
        "explored_states": proposal.explored_states,
        "truncated": proposal.truncated,
        "model_identity": proposal.model_identity,
        "revision_pin": proposal.revision_pin.as_dict(),
    }


def _validate_envelope(proposal: Any, context: ProposalContext) -> None:
    from .proposal import ProposalResult, RankedProgramCandidate

    if type(proposal) is not ProposalResult:
        raise ValueError("verify_candidates requires ProposalResult")
    if type(context) is not ProposalContext:
        raise ValueError("verify_candidates requires ProposalContext")
    if ProposalContext.from_dict(context.as_dict()) != context:
        raise ValueError("non-canonical proposal context")
    if proposal.proposal_context_ref != context.context_ref:
        raise ValueError("proposal and context identities differ")
    if proposal.orientation_ref != context.orientation_ref:
        raise ValueError("proposal and context orientations differ")
    if proposal.revision_pin != context.revision_pin:
        raise ValueError("proposal and context revision pins differ")
    if proposal.model_identity != context.revision_pin.model_identity:
        raise ValueError("proposal model identity differs from context revision")
    if type(proposal.truncated) is not bool:
        raise ValueError("proposal truncated must be an exact bool")
    if (
        type(proposal.explored_states) is not int
        or not 0 <= proposal.explored_states <= _MAX_EXPLORED_STATES
    ):
        raise ValueError(
            "proposal explored_states must be an exact bounded non-negative int"
        )
    if type(proposal.candidates) is not tuple:
        raise ValueError("proposal candidates must use canonical tuple storage")
    candidates = proposal.candidates
    if len(candidates) > _MAX_CANDIDATES:
        raise ValueError("proposal candidate bound exceeded")
    if any(type(row) is not RankedProgramCandidate for row in candidates):
        raise ValueError("proposal contains a non-canonical candidate value")
    for row in candidates:
        if type(row.provenance_refs) is not tuple:
            raise ValueError("candidate provenance must use canonical tuple storage")
        if len(row.provenance_refs) > _MAX_PROVENANCE_REFS:
            raise ValueError("candidate provenance bound exceeded")
        if len(row.provenance_refs) != len(set(row.provenance_refs)) or any(
            type(ref) is not str or not ref for ref in row.provenance_refs
        ):
            raise ValueError("candidate provenance is not canonical")
        if RankedProgramCandidate.from_dict(row.as_dict()) != row:
            raise ValueError("proposal contains a non-canonical candidate")
    if tuple(row.rank for row in candidates) != tuple(range(len(candidates))):
        raise ValueError("proposal candidate ranks are not contiguous")
    candidate_refs = tuple(row.candidate_ref for row in candidates)
    if len(candidate_refs) != len(set(candidate_refs)):
        raise ValueError("proposal candidate refs are not unique")
    if proposal.status == "candidates":
        if not candidates or proposal.abstention_code is not None:
            raise ValueError("candidate proposal envelope is incoherent")
    elif proposal.status == "abstained":
        if candidates or not proposal.abstention_code:
            raise ValueError("abstained proposal envelope is incoherent")
    else:
        raise ValueError("unknown proposal status")
    expected_ref = stable_ref("proposal", _proposal_material(proposal))
    if proposal.proposal_ref != expected_ref:
        raise ValueError("proposal_ref mismatch")
    if ProposalResult.from_dict(proposal.as_dict()) != proposal:
        raise ValueError("proposal result is not canonical")


def _candidate_errors(
    candidate: Any,
    candidate_index: int,
    proposal: Any,
    context: ProposalContext,
) -> tuple[VerificationError, ...]:
    errors: list[VerificationError] = []
    program = candidate.program
    if type(candidate.rank) is not int or candidate.rank != candidate_index:
        errors.append(VerificationError("candidate_rank_mismatch"))
    if type(candidate.score_q) is not int or not -(2**63) <= candidate.score_q < 2**63:
        errors.append(VerificationError("candidate_score_not_exact"))
    provenance = tuple(candidate.provenance_refs)
    if len(provenance) != len(set(provenance)) or any(
        type(ref) is not str or not ref for ref in provenance
    ):
        errors.append(VerificationError("candidate_provenance_not_canonical"))
    expected_candidate_ref = _proposal_candidate_ref(
        candidate_rank=candidate.rank,
        score_q=candidate.score_q,
        program_ref=program.program_ref,
        candidate_provenance_refs=provenance,
    )
    if candidate.candidate_ref != expected_candidate_ref:
        errors.append(VerificationError("candidate_identity_mismatch"))
    try:
        if SemanticSwitchProgram.from_dict(program.as_dict()) != program:
            errors.append(VerificationError("program_identity_mismatch"))
    except (TypeError, ValueError):
        errors.append(VerificationError("program_identity_mismatch"))
    if program.orientation_ref != proposal.orientation_ref:
        errors.append(VerificationError("program_orientation_mismatch"))
    if program.proposal_context_ref != context.context_ref:
        errors.append(VerificationError("program_context_mismatch"))
    if program.revision_pin != context.revision_pin:
        errors.append(VerificationError("program_revision_mismatch"))
    if program.action_abi_hash != ACTION_ABI_HASH:
        errors.append(VerificationError("action_abi_mismatch"))
    return tuple(errors)


def _coverage_error(row: Any) -> VerificationError:
    details = [row.detail] if row.detail else []
    for label in (
        "source_unit_ref",
        "contribution_slot_ref",
        "target_role_ref",
    ):
        value = getattr(row, label, None)
        if value is not None:
            details.append(f"{label}={value}")
    return VerificationError(
        row.code,
        ";".join(details),
        getattr(row, "target_action_ref", None),
    )


_R1_EXPRESSION_ACTIONS = frozenset(
    {
        "select_context",
        "select_mode",
        "select_designation",
        "instantiate_operator",
        "bind_role",
        "bind_reference",
        "complete_program",
    }
)


def _reconstruct_expected_r1_expression(
    program: SemanticSwitchProgram,
    context: ProposalContext,
) -> SemanticExpression | None:
    actions = tuple(program.actions)
    if not actions or any(
        action.action_type not in _R1_EXPRESSION_ACTIONS for action in actions
    ):
        return None
    instantiations = tuple(
        action for action in actions if action.action_type == "instantiate_operator"
    )
    if len(instantiations) != 1 or actions[-1].action_type != "complete_program":
        return None
    local_ref, frame_ref = instantiations[0].arguments
    frame = context.frame(frame_ref)
    if frame is None or frame.proposition_roles or program.root_refs != (local_ref,):
        return None

    bindings: dict[str, RoleBinding] = {
        role_ref: RoleBinding(role_ref, GroundedReference(target_ref))
        for role_ref, target_ref in frame.derived_role_targets
    }
    legal_roles = frozenset((*frame.required_roles, *frame.optional_roles))
    for action in actions:
        if action.action_type not in {"bind_role", "bind_reference"}:
            continue
        owner_ref, role_ref, slot_ref = action.arguments
        if (
            owner_ref != local_ref
            or role_ref not in legal_roles
            or role_ref in bindings
        ):
            return None
        if action.action_type == "bind_role":
            contribution = context.contribution(slot_ref)
            if contribution is None or role_ref not in contribution.output_ports:
                return None
            if contribution.target_ref is not None:
                filler = GroundedReference(contribution.target_ref)
            elif contribution.literal_value is not None:
                filler = LiteralValue("string", contribution.literal_value)
            else:
                return None
        else:
            reference = context.reference(slot_ref)
            if reference is None or role_ref not in reference.compatible_roles:
                return None
            filler = GroundedReference(reference.target_ref)
        bindings[role_ref] = RoleBinding(role_ref, filler)

    if any(role_ref not in bindings for role_ref in frame.required_roles):
        return None
    application = SemanticApplication(
        local_ref,
        frame.operator_ref,
        frame.predicate_target_ref,
        tuple(bindings[role_ref] for role_ref in sorted(bindings)),
    )
    return SemanticExpression.create(
        applications=(application,),
        root_refs=(local_ref,),
    )


def _reconstruct_expected_expression(
    program: SemanticSwitchProgram,
    context: ProposalContext,
) -> SemanticExpression | None:
    """Reconstruct the expected expression, trying R1 first then R2."""
    expected = _reconstruct_expected_r1_expression(program, context)
    if expected is not None:
        return expected
    return _reconstruct_r2_expression(program, context)


def _proof_errors(
    program: SemanticSwitchProgram,
    context: ProposalContext,
    expression: SemanticExpression,
    proof: CompilationProof,
) -> tuple[VerificationError, ...]:
    errors: list[VerificationError] = []

    def report(code: str, detail: str = "") -> None:
        if len(errors) < _MAX_ERRORS:
            errors.append(VerificationError(code, detail))

    try:
        if SemanticExpression.from_dict(expression.as_dict()) != expression:
            report("expression_identity_mismatch")
    except (TypeError, ValueError):
        report("expression_identity_mismatch")
    expected_expression = _reconstruct_expected_expression(program, context)
    if expected_expression is None or expression != expected_expression:
        report("expression_semantics_mismatch")
    try:
        if CompilationProof.from_dict(proof.as_dict()) != proof:
            report("compilation_proof_identity_mismatch")
    except (TypeError, ValueError):
        report("compilation_proof_identity_mismatch")
    if proof.program_ref != program.program_ref:
        report("compilation_proof_program_mismatch")
    if proof.proposal_context_ref != context.context_ref:
        report("compilation_proof_context_mismatch")
    if proof.expression_ref != expression.expression_ref:
        report("compilation_proof_expression_mismatch")
    if proof.revision_pin != program.revision_pin:
        report("compilation_proof_revision_mismatch")

    action_domain = tuple(row.source_ref for row in proof.action_translations)
    expected_actions = tuple(row.action_ref for row in program.actions)
    if action_domain != expected_actions:
        report("action_translation_domain_mismatch")
    assignment_domain = tuple(row.source_ref for row in proof.assignment_translations)
    expected_assignments = tuple(
        row.assignment_ref for row in program.source_assignments
    )
    if assignment_domain != expected_assignments:
        report("assignment_translation_domain_mismatch")
    root_domain = tuple(row.source_ref for row in proof.root_translations)
    if root_domain != program.root_refs:
        report("root_translation_domain_mismatch")
    translated_roots = tuple(
        target for row in proof.root_translations for target in row.target_refs
    )
    if translated_roots != expression.root_refs or any(
        row.disposition != "translated" for row in proof.root_translations
    ):
        report("root_translation_target_mismatch")

    root_targets = {row.source_ref: row.target_refs for row in proof.root_translations}
    if len(proof.action_translations) == len(program.actions):
        for action, row in zip(
            program.actions,
            proof.action_translations,
            strict=True,
        ):
            expected_disposition: str | None = None
            expected_targets: tuple[str, ...] | None = None
            if action.action_type == "select_context":
                expected_disposition = "validated"
                expected_targets = (context.context_ref,)
            elif action.action_type == "select_mode":
                expected_disposition = "validated"
                expected_targets = (program.mode_slot_ref,)
            elif action.action_type == "select_designation":
                expected_disposition = "validated"
                expected_targets = (action.arguments[0],)
            elif action.action_type == "instantiate_operator":
                expected_disposition = "translated"
                expected_targets = root_targets.get(action.arguments[0], ())
            elif action.action_type in {"bind_role", "bind_reference"}:
                canonical_application_refs = root_targets.get(action.arguments[0], ())
                expected_disposition = "translated"
                expected_targets = (
                    (
                        canonical_application_refs[0],
                        action.arguments[1],
                    )
                    if len(canonical_application_refs) == 1
                    else ()
                )
            elif action.action_type == "complete_program":
                expected_disposition = "translated"
                expected_targets = (expression.expression_ref,)
            if (
                expected_disposition is None
                or row.disposition != expected_disposition
                or row.target_refs != expected_targets
            ):
                report(
                    "action_translation_target_mismatch",
                    action.action_ref,
                )

    if len(proof.assignment_translations) == len(program.source_assignments):
        for assignment, row in zip(
            program.source_assignments,
            proof.assignment_translations,
            strict=True,
        ):
            expected_targets = tuple(
                target
                for target in (
                    assignment.target_action_ref or assignment.contribution_slot_ref,
                    assignment.target_role_ref,
                )
                if target is not None
            )
            expected_disposition = (
                "retained" if assignment.assignment_kind == "residual" else "translated"
            )
            if (
                row.disposition != expected_disposition
                or row.target_refs != expected_targets
            ):
                report(
                    "assignment_translation_target_mismatch",
                    assignment.assignment_ref,
                )

    expected_grounding: set[str] = set()
    for action in program.actions:
        if action.action_type == "select_designation":
            designation = context.designation(action.arguments[0])
            if designation is not None:
                expected_grounding.update(
                    (
                        designation.slot_ref,
                        designation.target_ref,
                        designation.designation_fact_ref,
                        *designation.provenance_refs,
                    )
                )
        elif action.action_type == "instantiate_operator":
            frame = context.frame(action.arguments[1])
            if frame is not None:
                expected_grounding.add(frame.predicate_target_ref)
                expected_grounding.update(
                    target_ref for _, target_ref in frame.derived_role_targets
                )
        elif action.action_type == "bind_role":
            contribution = context.contribution(action.arguments[2])
            if contribution is not None:
                if contribution.target_ref is not None:
                    expected_grounding.add(contribution.target_ref)
                expected_grounding.update(contribution.provenance_refs)
        elif action.action_type == "bind_reference":
            reference = context.reference(action.arguments[2])
            if reference is not None:
                expected_grounding.add(reference.target_ref)
                expected_grounding.update(reference.provenance_refs)
    if proof.grounding_refs != tuple(sorted(expected_grounding)):
        report("compilation_grounding_mismatch")
    return tuple(errors)


_UNRETAINABLE_COMPILATION_ERRORS = frozenset(
    {
        "expression_identity_mismatch",
        "expression_semantics_mismatch",
        "compilation_proof_identity_mismatch",
        "compilation_proof_program_mismatch",
        "compilation_proof_context_mismatch",
        "compilation_proof_expression_mismatch",
        "compilation_proof_revision_mismatch",
    }
)


def _dedupe_errors(
    values: Iterable[VerificationError],
) -> tuple[VerificationError, ...]:
    result: list[VerificationError] = []
    seen: set[tuple[str, str, str | None]] = set()
    for row in values:
        key = (row.code, row.detail, row.action_ref)
        if key in seen:
            continue
        if len(result) == _MAX_ERRORS:
            result[-1] = VerificationError(
                "verification_error_budget_exhausted",
                "unique verification errors exceeded the retained release bound",
            )
            return tuple(result)
        seen.add(key)
        result.append(row)
    return tuple(result)


class ExactProgramVerifier:
    """Verify one complete proposal batch with bounded O(n) selection."""

    __slots__ = ("_coverage", "_compiler", "_ambiguity_margin_q")

    def __init__(
        self,
        coverage_verifier: CoverageVerifier | Any | None = None,
        compiler: SemanticExpressionCompiler | Any | None = None,
        *,
        ambiguity_margin_q: int = 0,
    ) -> None:
        if (
            type(ambiguity_margin_q) is not int
            or ambiguity_margin_q < 0
            or ambiguity_margin_q >= 2**63
        ):
            raise ValueError("ambiguity_margin_q must be a non-negative exact int")
        self._coverage = coverage_verifier or CoverageVerifier()
        self._compiler = compiler or SemanticExpressionCompiler()
        if not callable(getattr(self._coverage, "verify", None)):
            raise ValueError("coverage_verifier must expose verify(context, program)")
        if not callable(getattr(self._compiler, "compile", None)):
            raise ValueError("compiler must expose compile(program, context)")
        self._ambiguity_margin_q = ambiguity_margin_q

    @property
    def ambiguity_margin_q(self) -> int:
        return self._ambiguity_margin_q

    def verify_candidates(
        self, proposal: "ProposalResult", context: ProposalContext
    ) -> VerificationBatch:
        _validate_envelope(proposal, context)
        if proposal.status == "abstained":
            return VerificationBatch.create(
                proposal_ref=proposal.proposal_ref,
                proposal_context_ref=context.context_ref,
                candidate_receipts=(),
                ambiguity_margin_q=self._ambiguity_margin_q,
                status="abstained",
                selected_candidate_ref=None,
                selected_meaning=None,
                ambiguity_expression_refs=(),
            )

        receipts: list[CandidateVerificationReceipt] = []
        for candidate_index, candidate in enumerate(proposal.candidates):
            receipts.append(
                self._verify_candidate(
                    candidate,
                    candidate_index,
                    proposal,
                    context,
                )
            )

        best_by_expression: dict[str, tuple[Any, CandidateVerificationReceipt]] = {}
        best_group: tuple[Any, CandidateVerificationReceipt] | None = None
        best_expression_ref: str | None = None
        for candidate, receipt in zip(proposal.candidates, receipts, strict=True):
            if not receipt.accepted or receipt.expression is None:
                continue
            key = receipt.expression.expression_ref
            current = best_by_expression.get(key)
            replacement = current is None or (
                candidate.score_q > current[0].score_q
                or (
                    candidate.score_q == current[0].score_q
                    and candidate.rank < current[0].rank
                )
            )
            if not replacement:
                continue
            group = (candidate, receipt)
            best_by_expression[key] = group
            if (
                best_group is None
                or key == best_expression_ref
                or candidate.score_q > best_group[0].score_q
                or (
                    candidate.score_q == best_group[0].score_q
                    and candidate.rank < best_group[0].rank
                )
            ):
                best_group = group
                best_expression_ref = key

        if best_group is None:
            return VerificationBatch.create(
                proposal_ref=proposal.proposal_ref,
                proposal_context_ref=context.context_ref,
                candidate_receipts=receipts,
                ambiguity_margin_q=self._ambiguity_margin_q,
                status="rejected",
                selected_candidate_ref=None,
                selected_meaning=None,
                ambiguity_expression_refs=(),
            )

        top_score = best_group[0].score_q
        contenders = [best_group]
        for group in best_by_expression.values():
            if group[1].candidate_ref == best_group[1].candidate_ref:
                continue
            if top_score - group[0].score_q <= self._ambiguity_margin_q:
                contenders.append(group)
        if len(contenders) > 1:
            return VerificationBatch.create(
                proposal_ref=proposal.proposal_ref,
                proposal_context_ref=context.context_ref,
                candidate_receipts=receipts,
                ambiguity_margin_q=self._ambiguity_margin_q,
                status="ambiguous",
                selected_candidate_ref=None,
                selected_meaning=None,
                ambiguity_expression_refs=tuple(
                    pair[1].expression.expression_ref for pair in contenders
                ),
            )

        candidate, receipt = best_group
        expression = receipt.expression
        proof = receipt.compilation_proof
        if expression is None or proof is None:
            raise AssertionError("accepted receipt lost its verified artifacts")
        selected_meaning = VerifiedMeaning.create(
            program_ref=receipt.program_ref,
            expression=expression,
            grounding_refs=proof.grounding_refs,
            coverage_receipt_ref=receipt.coverage_receipt.coverage_receipt_ref,
            compilation_proof_ref=proof.proof_ref,
            verification_receipt_ref=receipt.receipt_ref,
            revision_pin=receipt.coverage_receipt.revision_pin,
        )
        return VerificationBatch.create(
            proposal_ref=proposal.proposal_ref,
            proposal_context_ref=context.context_ref,
            candidate_receipts=receipts,
            ambiguity_margin_q=self._ambiguity_margin_q,
            status="selected",
            selected_candidate_ref=candidate.candidate_ref,
            selected_meaning=selected_meaning,
            ambiguity_expression_refs=(),
        )

    def _verify_candidate(
        self,
        candidate: "RankedProgramCandidate",
        candidate_index: int,
        proposal: "ProposalResult",
        context: ProposalContext,
    ) -> CandidateVerificationReceipt:
        program = candidate.program
        errors: list[VerificationError] = list(
            _candidate_errors(candidate, candidate_index, proposal, context)
        )
        errors.extend(_replay_program(program, context))
        if proposal.truncated:
            errors.append(
                VerificationError(
                    "proposal_truncated",
                    "truncated proposal cannot establish a unique verified meaning",
                )
            )

        # Trusted component exceptions deliberately propagate.
        coverage = self._coverage.verify(context, program)
        if not isinstance(coverage, CoverageReceipt):
            raise TypeError("coverage verifier returned a non-CoverageReceipt")
        if CoverageReceipt.from_dict(coverage.as_dict()) != coverage:
            raise ValueError("coverage verifier returned a non-canonical receipt")
        errors.extend(_coverage_error(row) for row in coverage.errors)
        errors.extend(
            VerificationError(
                "critical_residual",
                (
                    f"source_unit_ref={row.source_unit_ref};"
                    f"contribution_slot_ref={row.contribution_slot_ref};"
                    f"kind={row.contribution_kind};reason={row.reason}"
                ),
            )
            for row in coverage.critical_residuals
        )
        if (
            not coverage.executable
            and not coverage.errors
            and not coverage.critical_residuals
        ):
            errors.append(VerificationError("coverage_not_executable"))

        expression: SemanticExpression | None = None
        proof: CompilationProof | None = None
        errors = list(_dedupe_errors(errors))
        if not errors and coverage.executable:
            result = self._compiler.compile(program, context)
            if isinstance(result, CompilationFailure):
                errors.append(
                    VerificationError(result.code, result.detail, result.action_ref)
                )
            elif isinstance(result, CompilationSuccess):
                expression = result.expression
                proof = result.proof
                proof_errors = _proof_errors(program, context, expression, proof)
                errors.extend(proof_errors)
                if any(
                    row.code in _UNRETAINABLE_COMPILATION_ERRORS for row in proof_errors
                ):
                    expression = None
                    proof = None
            else:
                raise TypeError("semantic compiler returned an unknown result type")

        return CandidateVerificationReceipt.create(
            candidate_ref=candidate.candidate_ref,
            candidate_index=candidate_index,
            candidate_rank=candidate.rank,
            score_q=candidate.score_q,
            candidate_provenance_refs=candidate.provenance_refs,
            program_ref=program.program_ref,
            expression=expression,
            compilation_proof=proof,
            coverage_receipt=coverage,
            verification_errors=_dedupe_errors(errors),
        )
