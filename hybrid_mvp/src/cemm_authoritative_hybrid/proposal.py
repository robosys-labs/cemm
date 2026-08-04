"""Canonical PROPOSE owner and exact Proposal Result ABI 2.

``BootstrapProposer`` is a deterministic episode/test producer over one exact,
already-oriented ``ProposalContext``. It never resolves forms, grounds text,
scans authority or invokes VERIFY. The release runtime must use the separately
admitted safetensors-backed neural proposal owner.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import islice
from typing import Any, Iterable, Literal, Mapping, Protocol, runtime_checkable

from .canonical import stable_ref
from .config import RuntimeConfig
from .persistence import RevisionPin
from .programs import ProgramAction, SemanticSwitchProgram, SourceAssignment
from .proposal_context import ProposalContext

__all__ = [
    "PROPOSAL_RESULT_ABI_VERSION",
    "ProposalOwner",
    "RankedProgramCandidate",
    "ProposalResult",
    "BootstrapProposer",
]


# ---------------------------------------------------------------------------
# ProposalOwner protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class ProposalOwner(Protocol):
    """Exact owner boundary for the PROPOSE phase."""

    model_identity: str

    def propose(self, context: ProposalContext) -> "ProposalResult":
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Proposal Result ABI 2
# ---------------------------------------------------------------------------


PROPOSAL_RESULT_ABI_VERSION = 2
ProposalStatus = Literal["candidates", "abstained"]

_RELEASE_CONFIG = RuntimeConfig.release()
_MAX_PROPOSAL_CANDIDATES = _RELEASE_CONFIG.max_complete_candidates
_MAX_EXPLORED_STATES = (
    _RELEASE_CONFIG.max_beam_states * _RELEASE_CONFIG.max_applications
)
_MAX_PROVENANCE_REFS = _RELEASE_CONFIG.max_input_tokens
_MAX_REF_CHARS = 256
_MAX_ABSTENTION_CODE_CHARS = 128


def _required_text(value: object, field: str, maximum: int = _MAX_REF_CHARS) -> str:
    if type(value) is not str or not value or len(value) > maximum:
        raise ValueError(f"{field} must be a bounded non-empty string")
    return value


def _exact_fields(
    data: Mapping[str, Any], expected: frozenset[str], owner: str
) -> None:
    if not isinstance(data, Mapping):
        raise ValueError(f"{owner} payload must be an object")
    keys = tuple(data.keys())
    if any(type(key) is not str for key in keys):
        raise ValueError(f"{owner} fields must be strings")
    actual = frozenset(keys)
    if actual != expected:
        raise ValueError(
            f"{owner} fields mismatch: "
            f"missing={sorted(expected - actual)}, unknown={sorted(actual - expected)}"
        )


def _wire_list(value: object, field: str) -> list[Any]:
    if type(value) is not list:
        raise ValueError(f"{field} must use canonical list encoding")
    return value


def _bounded_tuple(
    values: Iterable[Any], maximum: int, field: str
) -> tuple[Any, ...]:
    if isinstance(values, (str, bytes, Mapping)):
        raise ValueError(f"{field} must be an iterable of values")
    try:
        result = tuple(islice(iter(values), maximum + 1))
    except TypeError as exc:
        raise ValueError(f"{field} must be iterable") from exc
    if len(result) > maximum:
        raise ValueError(f"{field} exceeds its bound of {maximum}")
    return result


def _candidate_identity_material(
    rank: int,
    score_q: int,
    program: SemanticSwitchProgram,
    provenance_refs: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "proposal_result_abi_version": PROPOSAL_RESULT_ABI_VERSION,
        "rank": rank,
        "score_q": score_q,
        "program_ref": program.program_ref,
        "provenance_refs": list(provenance_refs),
    }


@dataclass(frozen=True, init=False)
class RankedProgramCandidate:
    """One exact, proposer-ordered Program ABI 2 candidate envelope."""

    candidate_ref: str
    rank: int
    score_q: int
    program: SemanticSwitchProgram
    provenance_refs: tuple[str, ...]

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use RankedProgramCandidate.create")

    @classmethod
    def _from_canonical(
        cls,
        candidate_ref: str,
        *,
        rank: int,
        score_q: int,
        program: SemanticSwitchProgram,
        provenance_refs: tuple[str, ...],
    ) -> "RankedProgramCandidate":
        value = object.__new__(cls)
        object.__setattr__(value, "candidate_ref", candidate_ref)
        object.__setattr__(value, "rank", rank)
        object.__setattr__(value, "score_q", score_q)
        object.__setattr__(value, "program", program)
        object.__setattr__(value, "provenance_refs", provenance_refs)
        return value

    @classmethod
    def create(
        cls,
        *,
        rank: int,
        score_q: int,
        program: SemanticSwitchProgram,
        provenance_refs: Iterable[str],
    ) -> "RankedProgramCandidate":
        if type(rank) is not int or not 0 <= rank < _MAX_PROPOSAL_CANDIDATES:
            raise ValueError("candidate rank must be an exact bounded non-negative int")
        if type(score_q) is not int or not -(2**63) <= score_q < 2**63:
            raise ValueError("candidate score_q must be an exact signed 64-bit int")
        if type(program) is not SemanticSwitchProgram:
            raise ValueError("candidate program must be SemanticSwitchProgram")
        if not program.actions or program.actions[-1].action_type != "complete_program":
            raise ValueError("ranked candidate must contain a completed program")
        provenance = _bounded_tuple(
            provenance_refs, _MAX_PROVENANCE_REFS, "candidate provenance refs"
        )
        for ref in provenance:
            _required_text(ref, "candidate provenance ref")
        if len(provenance) != len(set(provenance)):
            raise ValueError("candidate provenance refs must be unique")
        material = _candidate_identity_material(rank, score_q, program, provenance)
        return cls._from_canonical(
            stable_ref("proposal_candidate", material),
            rank=rank,
            score_q=score_q,
            program=program,
            provenance_refs=provenance,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_ref": self.candidate_ref,
            "rank": self.rank,
            "score_q": self.score_q,
            "program": self.program.as_dict(),
            "provenance_refs": list(self.provenance_refs),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RankedProgramCandidate":
        _exact_fields(
            data,
            frozenset(
                {"candidate_ref", "rank", "score_q", "program", "provenance_refs"}
            ),
            "RankedProgramCandidate",
        )
        _required_text(data["candidate_ref"], "candidate_ref")
        program_data = data["program"]
        if not isinstance(program_data, Mapping):
            raise ValueError("candidate program must be an object")
        rebuilt = cls.create(
            rank=data["rank"],
            score_q=data["score_q"],
            program=SemanticSwitchProgram.from_dict(program_data),
            provenance_refs=(
                _required_text(item, "candidate provenance ref")
                for item in _wire_list(data["provenance_refs"], "provenance_refs")
            ),
        )
        if data["candidate_ref"] != rebuilt.candidate_ref:
            raise ValueError("RankedProgramCandidate ref mismatch")
        if rebuilt.as_dict() != dict(data):
            raise ValueError("non-canonical RankedProgramCandidate encoding")
        return rebuilt


def _proposal_identity_material(
    *,
    orientation_ref: str,
    proposal_context_ref: str,
    candidates: tuple[RankedProgramCandidate, ...],
    status: ProposalStatus,
    abstention_code: str | None,
    explored_states: int,
    truncated: bool,
    model_identity: str,
    revision_pin: RevisionPin,
) -> dict[str, Any]:
    return {
        "abi_version": PROPOSAL_RESULT_ABI_VERSION,
        "orientation_ref": orientation_ref,
        "proposal_context_ref": proposal_context_ref,
        "candidate_refs": [candidate.candidate_ref for candidate in candidates],
        "status": status,
        "abstention_code": abstention_code,
        "explored_states": explored_states,
        "truncated": truncated,
        "model_identity": model_identity,
        "revision_pin": revision_pin.as_dict(),
    }


@dataclass(frozen=True, init=False)
class ProposalResult:
    """The complete exact output batch owned by the PROPOSE phase."""

    proposal_ref: str
    orientation_ref: str
    proposal_context_ref: str
    candidates: tuple[RankedProgramCandidate, ...]
    status: ProposalStatus
    abstention_code: str | None
    explored_states: int
    truncated: bool
    model_identity: str
    revision_pin: RevisionPin

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use ProposalResult.create")

    @classmethod
    def _from_canonical(
        cls,
        proposal_ref: str,
        *,
        orientation_ref: str,
        proposal_context_ref: str,
        candidates: tuple[RankedProgramCandidate, ...],
        status: ProposalStatus,
        abstention_code: str | None,
        explored_states: int,
        truncated: bool,
        model_identity: str,
        revision_pin: RevisionPin,
    ) -> "ProposalResult":
        value = object.__new__(cls)
        object.__setattr__(value, "proposal_ref", proposal_ref)
        object.__setattr__(value, "orientation_ref", orientation_ref)
        object.__setattr__(value, "proposal_context_ref", proposal_context_ref)
        object.__setattr__(value, "candidates", candidates)
        object.__setattr__(value, "status", status)
        object.__setattr__(value, "abstention_code", abstention_code)
        object.__setattr__(value, "explored_states", explored_states)
        object.__setattr__(value, "truncated", truncated)
        object.__setattr__(value, "model_identity", model_identity)
        object.__setattr__(value, "revision_pin", revision_pin)
        return value

    @classmethod
    def create(
        cls,
        *,
        orientation_ref: str,
        proposal_context_ref: str,
        candidates: Iterable[RankedProgramCandidate],
        status: ProposalStatus,
        abstention_code: str | None,
        explored_states: int,
        truncated: bool,
        model_identity: str,
        revision_pin: RevisionPin,
    ) -> "ProposalResult":
        orientation = _required_text(orientation_ref, "orientation_ref")
        context = _required_text(proposal_context_ref, "proposal_context_ref")
        model = _required_text(model_identity, "model_identity")
        candidate_tuple = _bounded_tuple(
            candidates, _MAX_PROPOSAL_CANDIDATES, "proposal candidates"
        )
        if any(type(candidate) is not RankedProgramCandidate for candidate in candidate_tuple):
            raise ValueError("proposal candidates must be RankedProgramCandidate values")
        expected_ranks = tuple(range(len(candidate_tuple)))
        if tuple(candidate.rank for candidate in candidate_tuple) != expected_ranks:
            raise ValueError("proposal candidate ranks must be contiguous in proposer order")
        candidate_refs = tuple(candidate.candidate_ref for candidate in candidate_tuple)
        if len(candidate_refs) != len(set(candidate_refs)):
            raise ValueError("proposal candidate refs must be unique")
        for candidate in candidate_tuple:
            expected_candidate_ref = stable_ref(
                "proposal_candidate",
                _candidate_identity_material(
                    candidate.rank,
                    candidate.score_q,
                    candidate.program,
                    candidate.provenance_refs,
                ),
            )
            if candidate.candidate_ref != expected_candidate_ref:
                raise ValueError("proposal contains a non-canonical candidate ref")
        if type(status) is not str or status not in {"candidates", "abstained"}:
            raise ValueError("proposal status must be candidates or abstained")
        if status == "candidates":
            if not candidate_tuple:
                raise ValueError("candidates status requires at least one candidate")
            if abstention_code is not None:
                raise ValueError("candidates status cannot carry an abstention code")
        else:
            if candidate_tuple:
                raise ValueError("abstained status cannot carry candidates")
            _required_text(
                abstention_code,
                "abstention_code",
                _MAX_ABSTENTION_CODE_CHARS,
            )
        if type(explored_states) is not int or not 0 <= explored_states <= _MAX_EXPLORED_STATES:
            raise ValueError("explored_states must be an exact bounded non-negative int")
        if type(truncated) is not bool:
            raise ValueError("truncated must be an exact bool")
        if type(revision_pin) is not RevisionPin:
            raise ValueError("revision_pin must be RevisionPin")
        if revision_pin.model_identity != model:
            raise ValueError("proposal model and revision identities differ")
        for candidate in candidate_tuple:
            program = candidate.program
            if program.orientation_ref != orientation:
                raise ValueError("candidate program orientation mismatch")
            if program.proposal_context_ref != context:
                raise ValueError("candidate program proposal context mismatch")
            if program.revision_pin != revision_pin:
                raise ValueError("candidate program revision mismatch")
        typed_status: ProposalStatus = status
        material = _proposal_identity_material(
            orientation_ref=orientation,
            proposal_context_ref=context,
            candidates=candidate_tuple,
            status=typed_status,
            abstention_code=abstention_code,
            explored_states=explored_states,
            truncated=truncated,
            model_identity=model,
            revision_pin=revision_pin,
        )
        return cls._from_canonical(
            stable_ref("proposal", material),
            orientation_ref=orientation,
            proposal_context_ref=context,
            candidates=candidate_tuple,
            status=typed_status,
            abstention_code=abstention_code,
            explored_states=explored_states,
            truncated=truncated,
            model_identity=model,
            revision_pin=revision_pin,
        )

    @property
    def output_refs(self) -> tuple[str, ...]:
        return (self.proposal_ref,)

    def candidate_by_ref(self, candidate_ref: str) -> RankedProgramCandidate:
        matches = tuple(
            candidate
            for candidate in self.candidates
            if candidate.candidate_ref == candidate_ref
        )
        if len(matches) != 1:
            raise KeyError(candidate_ref)
        return matches[0]

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": PROPOSAL_RESULT_ABI_VERSION,
            "proposal_ref": self.proposal_ref,
            "orientation_ref": self.orientation_ref,
            "proposal_context_ref": self.proposal_context_ref,
            "candidates": [candidate.as_dict() for candidate in self.candidates],
            "status": self.status,
            "abstention_code": self.abstention_code,
            "explored_states": self.explored_states,
            "truncated": self.truncated,
            "model_identity": self.model_identity,
            "revision_pin": self.revision_pin.as_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProposalResult":
        _exact_fields(
            data,
            frozenset(
                {
                    "abi_version",
                    "proposal_ref",
                    "orientation_ref",
                    "proposal_context_ref",
                    "candidates",
                    "status",
                    "abstention_code",
                    "explored_states",
                    "truncated",
                    "model_identity",
                    "revision_pin",
                }
            ),
            "ProposalResult",
        )
        abi_version = data["abi_version"]
        if type(abi_version) is not int or abi_version != PROPOSAL_RESULT_ABI_VERSION:
            raise ValueError("unsupported Proposal Result ABI")
        _required_text(data["proposal_ref"], "proposal_ref")
        pin_data = data["revision_pin"]
        if not isinstance(pin_data, Mapping):
            raise ValueError("revision_pin must be an object")
        rebuilt = cls.create(
            orientation_ref=data["orientation_ref"],
            proposal_context_ref=data["proposal_context_ref"],
            candidates=(
                RankedProgramCandidate.from_dict(item)
                for item in _wire_list(data["candidates"], "candidates")
            ),
            status=data["status"],
            abstention_code=data["abstention_code"],
            explored_states=data["explored_states"],
            truncated=data["truncated"],
            model_identity=data["model_identity"],
            revision_pin=RevisionPin.from_dict(pin_data),
        )
        if data["proposal_ref"] != rebuilt.proposal_ref:
            raise ValueError("ProposalResult ref mismatch")
        if rebuilt.as_dict() != dict(data):
            raise ValueError("non-canonical ProposalResult encoding")
        return rebuilt


# ---------------------------------------------------------------------------
# BootstrapProposer — bounded deterministic Program ABI 2 producer
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _BindingOption:
    action_type: Literal["bind_role", "bind_reference"]
    assignment_kind: Literal["role", "reference", "qualifier"]
    role_ref: str
    action_slot_ref: str
    supporting_slots: tuple[tuple[str, str], ...]
    source_unit_refs: tuple[str, ...]
    score_q: int
    critical: bool
    provenance_refs: tuple[str, ...]


class BootstrapProposer:
    """Deterministic, non-release producer over one exact ProposalContext.

    ORIENT has already resolved every form, designation, contribution and
    grounding choice in ``context``. This owner only enumerates bounded Program
    ABI 2 derivations from those slots. Exact semantic acceptance belongs to
    VERIFY and is intentionally not invoked here.
    """

    model_identity: str = "bootstrap-proposer"

    def __init__(
        self,
        config: RuntimeConfig,
        *,
        release_only: bool = False,
    ) -> None:
        if type(config) is not RuntimeConfig:
            raise TypeError("config must be exact RuntimeConfig")
        if type(release_only) is not bool:
            raise TypeError("release_only must be an exact bool")
        self._config = config
        self._max_candidates = min(
            config.max_complete_candidates, _MAX_PROPOSAL_CANDIDATES
        )
        self._max_explored = min(
            config.max_beam_states * config.max_applications,
            _MAX_EXPLORED_STATES,
        )
        self._max_provenance = min(config.max_input_tokens, _MAX_PROVENANCE_REFS)
        self._release_only = release_only

    def propose(self, context: ProposalContext) -> ProposalResult:
        """Return one canonical, bounded proposal batch for ``context``."""
        if self._release_only:
            raise RuntimeError("BootstrapProposer cannot be used in release runtime")
        if type(context) is not ProposalContext:
            raise TypeError("propose requires exact ProposalContext")
        pin = context.revision_pin
        if pin.model_identity != self.model_identity:
            raise ValueError("proposal context is pinned to a different model identity")
        if context.critical_residual_unit_refs:
            return self._abstained(context, "proposal:critical_residual", 0)
        if not context.mode_slots:
            return self._abstained(context, "proposal:no_mode", 0)
        if not context.designation_slots or not context.application_frames:
            return self._abstained(context, "proposal:no_application_frame", 0)

        from .recursive_composer import RecursiveComposer

        composer = RecursiveComposer(
            context,
            max_candidates=self._max_candidates,
            max_explored=self._max_explored,
            max_provenance=self._max_provenance,
            max_applications=self._config.max_applications,
            max_nodes=64,
        )
        completed = composer.search()

        if not completed:
            code = (
                "proposal:budget_exhausted"
                if composer.truncated
                else "proposal:no_complete_candidate"
            )
            return self._abstained(
                context, code, composer.explored, truncated=composer.truncated
            )

        candidates = tuple(
            RankedProgramCandidate.create(
                rank=rank,
                score_q=result.score_q,
                program=result.program,
                provenance_refs=result.provenance,
            )
            for rank, result in enumerate(completed)
        )
        return ProposalResult.create(
            orientation_ref=context.orientation_ref,
            proposal_context_ref=context.context_ref,
            candidates=candidates,
            status="candidates",
            abstention_code=None,
            explored_states=composer.explored,
            truncated=composer.truncated,
            model_identity=self.model_identity,
            revision_pin=pin,
        )

    def _abstained(
        self,
        context: ProposalContext,
        code: str,
        explored_states: int,
        *,
        truncated: bool = False,
    ) -> ProposalResult:
        return ProposalResult.create(
            orientation_ref=context.orientation_ref,
            proposal_context_ref=context.context_ref,
            candidates=(),
            status="abstained",
            abstention_code=code,
            explored_states=explored_states,
            truncated=truncated,
            model_identity=self.model_identity,
            revision_pin=context.revision_pin,
        )

