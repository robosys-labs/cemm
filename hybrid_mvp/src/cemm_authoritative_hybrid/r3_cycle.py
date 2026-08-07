"""Cycle Result ABI 3 for the admitted R3 continuation.

Cycle Result ABI 2 remains owned by :mod:`cycle` and continues to describe the
R1/R2 ORIENT→PROPOSE→VERIFY boundary.  R3 introduces a new, explicit ABI rather
than mutating ABI 2 at import time.  This module owns the six-phase result and
finalizer used by the R3 runtime.  Surface realization remains unadmitted and
is represented by the exact R5 later-owner gap.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .canonical import stable_ref
from .cycle import (
    CycleStatus,
    Orientation,
    PhaseDisposition,
    PhaseReceipt,
    SemanticPhase,
    _PhaseMaterial,
)
from .gaps import GapKind, GapReceipt
from .persistence import RevisionPin
from .proposal import ProposalResult
from .r3_artifacts import EvaluationBundle
from .r3_effects import EffectReceipt, EffectStatus, NoEffectReceipt
from .r3_response import ResponseMeaning
from .verifier import VerificationBatch

CYCLE_RESULT_ABI_VERSION = 3

__all__ = [
    "CYCLE_RESULT_ABI_VERSION",
    "CycleResult",
    "CycleFinalizer",
]

_FIELDS = frozenset(
    {
        "abi_version",
        "cycle_ref",
        "input_ref",
        "status",
        "orientation",
        "proposal",
        "verification",
        "evaluation",
        "effect_receipt",
        "response_meaning",
        "realization_receipt",
        "gap_receipt",
        "phase_material",
        "trace",
        "final_revision_pin",
    }
)


def _text(value: object, name: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{name} must be exact str")
    if not value:
        raise ValueError(f"{name} must be nonempty")
    if len(value) > 512:
        raise ValueError(f"{name} exceeds 512 characters")
    return value


def _canonical(value: object, owner: type[Any], name: str) -> object:
    if type(value) is not owner:
        raise TypeError(f"{name} must be exact {owner.__name__}")
    rebuilt = owner.from_dict(value.as_dict())
    if rebuilt != value:
        raise ValueError(f"{name} is non-canonical")
    return value


def _artifact_ref(value: object | None) -> str | None:
    if value is None:
        return None
    # Type-specific primary ref to avoid returning binding refs (e.g.
    # ProposalResult.orientation_ref) instead of the artifact's own ref.
    _PRIMARY: dict[type, str] = {
        Orientation: "orientation_ref",
        ProposalResult: "proposal_ref",
        VerificationBatch: "batch_ref",
        EvaluationBundle: "evaluation_ref",
        EffectReceipt: "receipt_ref",
        NoEffectReceipt: "receipt_ref",
        ResponseMeaning: "response_meaning_ref",
        GapReceipt: "gap_ref",
    }
    primary = _PRIMARY.get(type(value))
    if primary is not None:
        ref = getattr(value, primary, None)
        if type(ref) is str and ref:
            return ref
    for field in (
        "orientation_ref",
        "proposal_ref",
        "batch_ref",
        "evaluation_ref",
        "receipt_ref",
        "response_meaning_ref",
        "gap_ref",
    ):
        ref = getattr(value, field, None)
        if type(ref) is str and ref:
            return ref
    raise TypeError(f"unsupported cycle artifact: {type(value).__name__}")


def _artifact_wire(value: object | None) -> object:
    if value is None:
        return None
    method = getattr(value, "as_dict", None)
    if not callable(method):
        raise TypeError("cycle artifact lacks as_dict")
    return method()


def _refs(
    *,
    orientation: Orientation | None,
    proposal: ProposalResult | None,
    verification: VerificationBatch | None,
    evaluation: EvaluationBundle | None,
    effect_receipt: EffectReceipt | NoEffectReceipt | None,
    response_meaning: ResponseMeaning | None,
    realization_receipt: None,
    gap_receipt: GapReceipt | None,
) -> dict[str, str | None]:
    if orientation is not None:
        _canonical(orientation, Orientation, "orientation")
    if proposal is not None:
        _canonical(proposal, ProposalResult, "proposal")
    if verification is not None:
        _canonical(verification, VerificationBatch, "verification")
    if evaluation is not None:
        _canonical(evaluation, EvaluationBundle, "evaluation")
    if response_meaning is not None:
        _canonical(response_meaning, ResponseMeaning, "response_meaning")
    if gap_receipt is not None:
        _canonical(gap_receipt, GapReceipt, "gap_receipt")
    if effect_receipt is not None:
        if type(effect_receipt) is EffectReceipt:
            _canonical(effect_receipt, EffectReceipt, "effect_receipt")
        elif type(effect_receipt) is NoEffectReceipt:
            _canonical(effect_receipt, NoEffectReceipt, "effect_receipt")
        else:
            raise TypeError(
                "effect_receipt must be exact EffectReceipt or NoEffectReceipt"
            )
    if realization_receipt is not None:
        raise TypeError("surface realization is not admitted before R5")
    return {
        "orientation_ref": _artifact_ref(orientation),
        "proposal_ref": _artifact_ref(proposal),
        "verification_ref": _artifact_ref(verification),
        "evaluation_ref": _artifact_ref(evaluation),
        "effect_receipt_ref": _artifact_ref(effect_receipt),
        "response_meaning_ref": _artifact_ref(response_meaning),
        "realization_receipt_ref": None,
        "gap_ref": _artifact_ref(gap_receipt),
    }


def _identity(
    *,
    input_ref: str,
    status: CycleStatus,
    refs: Mapping[str, str | None],
    phase_material: tuple[_PhaseMaterial, ...],
    final_revision_pin: RevisionPin,
) -> dict[str, Any]:
    return {
        "abi_version": CYCLE_RESULT_ABI_VERSION,
        "input_ref": input_ref,
        "status": status.value,
        **dict(refs),
        "phase_material": [row.as_dict() for row in phase_material],
        "final_revision_pin": final_revision_pin.as_dict(),
    }


def _validate_phase_chain(
    input_ref: str,
    phase_material: tuple[_PhaseMaterial, ...],
    final_revision_pin: RevisionPin,
) -> None:
    _text(input_ref, "input_ref")
    if type(phase_material) is not tuple or len(phase_material) not in {3, 6}:
        raise ValueError("phase_material must contain exactly three or six phases")
    if any(type(row) is not _PhaseMaterial for row in phase_material):
        raise TypeError("phase_material rows must be exact _PhaseMaterial")
    expected = tuple(SemanticPhase)[: len(phase_material)]
    if tuple(row.phase for row in phase_material) != expected:
        raise ValueError("phase material is not an exact unique phase prefix")
    if input_ref not in phase_material[0].input_refs:
        raise ValueError("ORIENT material does not bind input_ref")
    for left, right in zip(phase_material, phase_material[1:], strict=False):
        if left.output_revision_pin != right.input_revision_pin:
            raise ValueError("phase revision pin chain is broken")
        if not set(left.output_refs).issubset(right.input_refs):
            raise ValueError("phase output refs do not feed the successor phase")
    if type(final_revision_pin) is not RevisionPin:
        raise TypeError("final_revision_pin must be exact RevisionPin")
    if RevisionPin.from_dict(final_revision_pin.as_dict()) != final_revision_pin:
        raise ValueError("final_revision_pin is non-canonical")
    if phase_material[-1].output_revision_pin != final_revision_pin:
        raise ValueError("final_revision_pin differs from terminal phase material")


def _validate_r2_terminal(
    *,
    status: CycleStatus,
    proposal: ProposalResult,
    verification: VerificationBatch,
    evaluation: EvaluationBundle | None,
    effect_receipt: EffectReceipt | NoEffectReceipt | None,
    response_meaning: ResponseMeaning | None,
    gap_receipt: GapReceipt | None,
    phase_material: tuple[_PhaseMaterial, ...],
) -> None:
    if evaluation is not None or effect_receipt is not None or response_meaning is not None:
        raise ValueError("later artifacts exist without R3 phase material")
    verify_row = phase_material[2]
    dispositions = {
        "selected": PhaseDisposition.COMPLETED,
        "abstained": PhaseDisposition.ABSTAINED,
        "rejected": PhaseDisposition.REJECTED,
        "ambiguous": PhaseDisposition.GAP,
    }
    if verify_row.disposition is not dispositions[verification.status]:
        raise ValueError("VERIFY disposition does not match VerificationBatch")
    codes = {
        "selected": (),
        "abstained": (proposal.abstention_code,),
        "rejected": ("verification:rejected",),
        "ambiguous": ("verification:ambiguous",),
    }
    if verify_row.rejection_codes != codes[verification.status]:
        raise ValueError("VERIFY rejection codes do not match VerificationBatch")
    if gap_receipt is None:
        raise ValueError("three-phase terminal cycle requires a gap receipt")
    if verification.status == "selected":
        meaning = verification.selected_meaning
        if meaning is None:
            raise ValueError("selected verification lacks VerifiedMeaning")
        if not (
            status is CycleStatus.PARTIAL
            and gap_receipt.kind is GapKind.IMPLEMENTATION
            and gap_receipt.status == "later_owner_not_admitted"
            and gap_receipt.source_refs == (meaning.verified_meaning_ref,)
            and gap_receipt.missing_contract_refs == ("contract:r3:evaluate",)
        ):
            raise ValueError("selected R2 terminal requires exact R3 owner gap")
    elif verification.status == "ambiguous":
        if status is not CycleStatus.AMBIGUOUS:
            raise ValueError("ambiguous verification requires ambiguous cycle")
    elif status is not CycleStatus.UNSUPPORTED:
        raise ValueError("abstained/rejected verification requires unsupported cycle")


def _validate_r3_terminal(
    *,
    status: CycleStatus,
    verification: VerificationBatch,
    evaluation: EvaluationBundle,
    effect_receipt: EffectReceipt | NoEffectReceipt,
    response_meaning: ResponseMeaning,
    gap_receipt: GapReceipt | None,
    phase_material: tuple[_PhaseMaterial, ...],
    final_revision_pin: RevisionPin,
) -> None:
    if verification.status != "selected" or verification.selected_meaning is None:
        raise ValueError("R3 continuation requires selected VerifiedMeaning")
    meaning = verification.selected_meaning
    if evaluation.decision.verified_meaning_ref != meaning.verified_meaning_ref:
        raise ValueError("evaluation does not bind the selected VerifiedMeaning")
    if evaluation.expression.expression_ref != meaning.expression.expression_ref:
        raise ValueError("evaluation expression differs from selected meaning")
    if effect_receipt.decision_ref != evaluation.decision.decision_ref:
        raise ValueError("effect receipt does not bind the evaluation decision")
    if response_meaning.decision_ref != evaluation.decision.decision_ref:
        raise ValueError("response meaning does not bind the decision")
    if response_meaning.effect_outcome_ref != effect_receipt.receipt_ref:
        raise ValueError("response meaning does not bind the effect outcome")
    if response_meaning.cycle_status is not status:
        raise ValueError("cycle status differs from ResponseMeaning status")

    eval_row, effect_row, realize_row = phase_material[3:]
    if evaluation.evaluation_ref not in eval_row.output_refs:
        raise ValueError("EVALUATE material lacks EvaluationBundle")
    if effect_receipt.receipt_ref not in effect_row.output_refs:
        raise ValueError("EFFECT material lacks effect/no-effect receipt")
    if response_meaning.response_meaning_ref not in realize_row.output_refs:
        raise ValueError("REALIZE material lacks ResponseMeaning")
    if type(effect_receipt) is NoEffectReceipt:
        if effect_row.disposition is not PhaseDisposition.NO_EFFECT:
            raise ValueError("NoEffectReceipt requires NO_EFFECT disposition")
    else:
        if effect_row.disposition is not PhaseDisposition.COMMITTED:
            raise ValueError("persisted EffectReceipt requires COMMITTED disposition")
        if effect_receipt.output_revision_pin != final_revision_pin:
            raise ValueError("EffectReceipt output pin differs from cycle final pin")
        if effect_receipt.status is EffectStatus.COMMITTED:
            if (
                effect_receipt.output_revision_pin.world_revision
                <= effect_receipt.input_revision_pin.world_revision
            ):
                raise ValueError("committed effect did not advance world revision")
        elif (
            effect_receipt.output_revision_pin.world_revision
            != effect_receipt.input_revision_pin.world_revision
        ):
            raise ValueError("noncommitted effect changed world revision")

    if gap_receipt is None:
        raise ValueError("R3 cycle must stop at the R5 surface-realization gap")
    if not (
        gap_receipt.kind is GapKind.IMPLEMENTATION
        and gap_receipt.status == "later_owner_not_admitted"
        and gap_receipt.source_refs == (response_meaning.response_meaning_ref,)
        and gap_receipt.missing_contract_refs == ("contract:r5:realize_surface",)
    ):
        raise ValueError("R3 cycle requires exact R5 later-owner gap")


def _validate(
    *,
    input_ref: str,
    status: CycleStatus,
    orientation: Orientation | None,
    proposal: ProposalResult | None,
    verification: VerificationBatch | None,
    evaluation: EvaluationBundle | None,
    effect_receipt: EffectReceipt | NoEffectReceipt | None,
    response_meaning: ResponseMeaning | None,
    realization_receipt: None,
    gap_receipt: GapReceipt | None,
    phase_material: tuple[_PhaseMaterial, ...],
    final_revision_pin: RevisionPin,
) -> dict[str, str | None]:
    if type(status) is not CycleStatus:
        raise TypeError("status must be exact CycleStatus")
    _validate_phase_chain(input_ref, phase_material, final_revision_pin)
    refs = _refs(
        orientation=orientation,
        proposal=proposal,
        verification=verification,
        evaluation=evaluation,
        effect_receipt=effect_receipt,
        response_meaning=response_meaning,
        realization_receipt=realization_receipt,
        gap_receipt=gap_receipt,
    )
    required = (
        (0, refs["orientation_ref"]),
        (1, refs["proposal_ref"]),
        (2, refs["verification_ref"]),
    )
    for index, ref in required:
        if ref is None or ref not in phase_material[index].output_refs:
            raise ValueError("phase material lacks its canonical owner artifact")
    if orientation is None or proposal is None or verification is None:
        raise ValueError("cycle requires ORIENT, PROPOSE and VERIFY artifacts")
    if proposal.orientation_ref != orientation.orientation_ref:
        raise ValueError("proposal does not bind the exact Orientation")
    if verification.proposal_ref != proposal.proposal_ref:
        raise ValueError("verification does not bind the exact ProposalResult")

    if len(phase_material) == 3:
        _validate_r2_terminal(
            status=status,
            proposal=proposal,
            verification=verification,
            evaluation=evaluation,
            effect_receipt=effect_receipt,
            response_meaning=response_meaning,
            gap_receipt=gap_receipt,
            phase_material=phase_material,
        )
    else:
        if evaluation is None or effect_receipt is None or response_meaning is None:
            raise ValueError("six-phase R3 cycle lacks required artifacts")
        _validate_r3_terminal(
            status=status,
            verification=verification,
            evaluation=evaluation,
            effect_receipt=effect_receipt,
            response_meaning=response_meaning,
            gap_receipt=gap_receipt,
            phase_material=phase_material,
            final_revision_pin=final_revision_pin,
        )
    return refs


@dataclass(frozen=True)
class CycleResult:
    """Canonical six-phase Cycle Result ABI 3."""

    abi_version: int
    cycle_ref: str
    input_ref: str
    status: CycleStatus
    orientation: Orientation | None
    proposal: ProposalResult | None
    verification: VerificationBatch | None
    evaluation: EvaluationBundle | None
    effect_receipt: EffectReceipt | NoEffectReceipt | None
    response_meaning: ResponseMeaning | None
    realization_receipt: None
    gap_receipt: GapReceipt | None
    phase_material: tuple[_PhaseMaterial, ...]
    trace: tuple[PhaseReceipt, ...]
    final_revision_pin: RevisionPin

    _FIELDS = _FIELDS

    def __post_init__(self) -> None:
        if type(self) is not CycleResult:
            raise TypeError("CycleResult requires exact class")
        if type(self.abi_version) is not int or self.abi_version != CYCLE_RESULT_ABI_VERSION:
            raise ValueError("unsupported Cycle Result ABI")
        _text(self.cycle_ref, "cycle_ref")
        refs = _validate(
            input_ref=self.input_ref,
            status=self.status,
            orientation=self.orientation,
            proposal=self.proposal,
            verification=self.verification,
            evaluation=self.evaluation,
            effect_receipt=self.effect_receipt,
            response_meaning=self.response_meaning,
            realization_receipt=self.realization_receipt,
            gap_receipt=self.gap_receipt,
            phase_material=self.phase_material,
            final_revision_pin=self.final_revision_pin,
        )
        expected = stable_ref(
            "cycle_v3",
            _identity(
                input_ref=self.input_ref,
                status=self.status,
                refs=refs,
                phase_material=self.phase_material,
                final_revision_pin=self.final_revision_pin,
            ),
        )
        if self.cycle_ref != expected:
            raise ValueError("CycleResult cycle_ref mismatch")
        if type(self.trace) is not tuple:
            raise TypeError("trace must be exact tuple")
        if self.trace:
            if len(self.trace) != len(self.phase_material):
                raise ValueError("trace must cover every phase material row")
            for receipt, material in zip(self.trace, self.phase_material, strict=True):
                if type(receipt) is not PhaseReceipt:
                    raise TypeError("trace rows must be exact PhaseReceipt")
                if PhaseReceipt.from_dict(receipt.as_dict()) != receipt:
                    raise ValueError("trace contains non-canonical PhaseReceipt")
                if receipt.cycle_ref != self.cycle_ref or receipt.material != material:
                    raise ValueError("trace receipt does not bind exact cycle material")

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "cycle_ref": self.cycle_ref,
            "input_ref": self.input_ref,
            "status": self.status.value,
            "orientation": _artifact_wire(self.orientation),
            "proposal": _artifact_wire(self.proposal),
            "verification": _artifact_wire(self.verification),
            "evaluation": _artifact_wire(self.evaluation),
            "effect_receipt": _artifact_wire(self.effect_receipt),
            "response_meaning": _artifact_wire(self.response_meaning),
            "realization_receipt": None,
            "gap_receipt": _artifact_wire(self.gap_receipt),
            "phase_material": [row.as_dict() for row in self.phase_material],
            "trace": [row.as_dict() for row in self.trace],
            "final_revision_pin": self.final_revision_pin.as_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CycleResult":
        if cls is not CycleResult:
            raise TypeError("CycleResult codec requires exact class")
        if type(value) is not dict or frozenset(value) != cls._FIELDS:
            raise ValueError("CycleResult fields mismatch")
        if value["realization_receipt"] is not None:
            raise ValueError("surface realization is not admitted before R5")
        effect_data = value["effect_receipt"]
        effect: EffectReceipt | NoEffectReceipt | None
        if effect_data is None:
            effect = None
        elif type(effect_data) is not dict:
            raise TypeError("effect_receipt wire value must be exact dict or None")
        elif "status" in effect_data:
            effect = EffectReceipt.from_dict(effect_data)
        else:
            effect = NoEffectReceipt.from_dict(effect_data)
        rebuilt = cls(
            abi_version=value["abi_version"],
            cycle_ref=value["cycle_ref"],
            input_ref=value["input_ref"],
            status=CycleStatus(value["status"]),
            orientation=(
                None
                if value["orientation"] is None
                else Orientation.from_dict(value["orientation"])
            ),
            proposal=(
                None
                if value["proposal"] is None
                else ProposalResult.from_dict(value["proposal"])
            ),
            verification=(
                None
                if value["verification"] is None
                else VerificationBatch.from_dict(value["verification"])
            ),
            evaluation=(
                None
                if value["evaluation"] is None
                else EvaluationBundle.from_dict(value["evaluation"])
            ),
            effect_receipt=effect,
            response_meaning=(
                None
                if value["response_meaning"] is None
                else ResponseMeaning.from_dict(value["response_meaning"])
            ),
            realization_receipt=None,
            gap_receipt=(
                None
                if value["gap_receipt"] is None
                else GapReceipt.from_dict(value["gap_receipt"])
            ),
            phase_material=tuple(
                _PhaseMaterial.from_dict(row) for row in value["phase_material"]
            ),
            trace=tuple(PhaseReceipt.from_dict(row) for row in value["trace"]),
            final_revision_pin=RevisionPin.from_dict(value["final_revision_pin"]),
        )
        if rebuilt.as_dict() != dict(value):
            raise ValueError("non-canonical CycleResult encoding")
        return rebuilt


class CycleFinalizer:
    """Create one canonical Cycle Result ABI 3 from complete phase material."""

    @classmethod
    def finalize(
        cls,
        *,
        input_ref: str,
        status: CycleStatus,
        orientation: Orientation | None,
        proposal: ProposalResult | None,
        verification: VerificationBatch | None,
        evaluation: EvaluationBundle | None,
        effect_receipt: EffectReceipt | NoEffectReceipt | None,
        response_meaning: ResponseMeaning | None,
        realization_receipt: None,
        gap_receipt: GapReceipt | None,
        phase_material: tuple[_PhaseMaterial, ...],
        final_revision_pin: RevisionPin,
        capture_trace: bool,
        durations_ns: tuple[int, ...],
    ) -> CycleResult:
        if cls is not CycleFinalizer:
            raise TypeError("CycleFinalizer requires exact class")
        refs = _validate(
            input_ref=input_ref,
            status=status,
            orientation=orientation,
            proposal=proposal,
            verification=verification,
            evaluation=evaluation,
            effect_receipt=effect_receipt,
            response_meaning=response_meaning,
            realization_receipt=realization_receipt,
            gap_receipt=gap_receipt,
            phase_material=phase_material,
            final_revision_pin=final_revision_pin,
        )
        if type(durations_ns) is not tuple or len(durations_ns) != len(phase_material):
            raise ValueError("durations_ns must match phase material")
        if any(type(value) is not int or value < 0 for value in durations_ns):
            raise ValueError("durations_ns must contain bounded nonnegative integers")
        cycle_ref = stable_ref(
            "cycle_v3",
            _identity(
                input_ref=input_ref,
                status=status,
                refs=refs,
                phase_material=phase_material,
                final_revision_pin=final_revision_pin,
            ),
        )
        trace = (
            tuple(
                PhaseReceipt.create(
                    cycle_ref=cycle_ref,
                    material=material,
                    duration_ns=duration,
                )
                for material, duration in zip(
                    phase_material, durations_ns, strict=True
                )
            )
            if capture_trace
            else ()
        )
        return CycleResult(
            abi_version=CYCLE_RESULT_ABI_VERSION,
            cycle_ref=cycle_ref,
            input_ref=input_ref,
            status=status,
            orientation=orientation,
            proposal=proposal,
            verification=verification,
            evaluation=evaluation,
            effect_receipt=effect_receipt,
            response_meaning=response_meaning,
            realization_receipt=None,
            gap_receipt=gap_receipt,
            phase_material=phase_material,
            trace=trace,
            final_revision_pin=final_revision_pin,
        )
