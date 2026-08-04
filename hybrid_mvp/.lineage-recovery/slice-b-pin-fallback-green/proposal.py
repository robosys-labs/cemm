"""Deterministic proposal oracle and semantic episode seed.

This module owns :class:`ProposalModel`, :class:`ProposalResult`, and
:class:`BootstrapProposer`.

The :class:`BootstrapProposer` is a deterministic oracle for tests and episode
construction only. It searches legal action prefixes using the
:class:`LegalActionIndex` and indexed contributions/ports. It has no phrase
inventory and no word/regex branch. Canonical tie-breaking makes episode
generation deterministic.

The running product must load a safetensors-backed
:class:`NeuralSwitchProposer`; the :class:`BootstrapProposer` raises if
constructed by the release runtime factory.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import islice
from typing import Any, Iterable, Literal, Mapping, Protocol

from .canonical import stable_ref
from .contributions import ContributionExpander
from .coverage import CoverageVerifier
from .cycle import Orientation
from .forms import FormResolver
from .grounding import Grounder
from .affordances import SemanticAffordanceIndex
from .authority import LinkedAuthority
from .config import RuntimeConfig
from .persistence import RevisionPin
from .programs import ProgramAction, SemanticSwitchProgram, SourceAssignment
from .verifier import ExactProgramVerifier, LegalActionIndex

__all__ = [
    "PROPOSAL_RESULT_ABI_VERSION",
    "ProposalModel",
    "RankedProgramCandidate",
    "ProposalResult",
    "BootstrapProposer",
]


# ---------------------------------------------------------------------------
# ProposalModel protocol
# ---------------------------------------------------------------------------


class ProposalModel(Protocol):
    """Protocol for a proposal model (bootstrap or neural)."""

    model_identity: str

    def propose(self, orientation: Orientation) -> "ProposalResult":
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
# BootstrapProposer — deterministic oracle for tests and episode construction
# ---------------------------------------------------------------------------


class BootstrapProposer:
    """Deterministic proposal oracle for tests and episode construction.

    Searches legal action prefixes using the :class:`LegalActionIndex` and
    indexed contributions/ports. It has no phrase inventory and no word/regex
    branch. Canonical tie-breaking makes episode generation deterministic.

    Raises :class:`RuntimeError` if the ``release_only`` flag is set, preventing
    use in the release runtime.
    """

    model_identity: str = "bootstrap-proposer"

    def __init__(
        self,
        authority: LinkedAuthority,
        config: RuntimeConfig,
        form_resolver: FormResolver,
        grounder: Grounder,
        affordance_index: SemanticAffordanceIndex,
        contribution_expander: ContributionExpander,
        verifier: ExactProgramVerifier,
        coverage_verifier: CoverageVerifier,
        legal_action_index: LegalActionIndex,
    ) -> None:
        self._authority = authority
        self._config = config
        self._form_resolver = form_resolver
        self._grounder = grounder
        self._affordance_index = affordance_index
        self._contribution_expander = contribution_expander
        self._verifier = verifier
        self._coverage_verifier = coverage_verifier
        self._legal_action_index = legal_action_index
        self._max_candidates = getattr(config, "max_complete_candidates", 48)
        self._max_actions = getattr(config, "max_applications", 24)
        self._max_explored = getattr(config, "max_beam_states", 32) * self._max_actions
        self._release_only: bool = False

    # -- public API ----------------------------------------------------------

    def propose(self, orientation: Orientation) -> ProposalResult:
        """Propose verified programs for ``orientation``.

        Searches legal action prefixes using BFS over the
        :class:`LegalActionIndex`. For each complete prefix (ending with
        ``complete_program`` or ``abstain``), builds a
        :class:`SemanticSwitchProgram` with source assignments and verifies it.

        Canonical tie-breaking: candidates are sorted by ``program_ref`` for
        determinism.
        """
        if self._release_only:
            raise RuntimeError(
                "BootstrapProposer cannot be used in release runtime"
            )

        text = orientation.source_text
        lattice = self._form_resolver.resolve(text)

        # Ground designations and expand contributions.
        grounding_result = self._grounder.ground_text(text)
        self._contribution_expander.expand(grounding_result, lattice)

        # Collect content units (non-whitespace, non-punctuation).
        content_unit_refs = [
            u.unit_ref for u in lattice.units if u.source_text.strip()
        ]

        # Build revision pin matching the authority generation.
        pin = self._build_revision_pin(orientation)

        # DFS over legal action prefixes.
        candidates, explored, truncated = self._search(
            lattice, content_unit_refs, orientation, pin
        )

        # Canonical tie-breaking: sort by program_ref, deduplicate.
        seen_refs: set[str] = set()
        unique: list[SemanticSwitchProgram] = []
        for p in sorted(candidates, key=lambda p: p.program_ref):
            if p.program_ref not in seen_refs:
                seen_refs.add(p.program_ref)
                unique.append(p)
        candidates = tuple(unique)

        return ProposalResult(
            candidates=candidates,
            explored_states=explored,
            truncated=truncated,
            model_identity=self.model_identity,
        )

    def propose_detailed(
        self, orientation: Orientation
    ) -> tuple[ProposalResult, list[dict[str, Any]]]:
        """Propose and return detailed results including rejected alternatives.

        Returns a tuple of (ProposalResult, rejected_alternatives) where
        ``rejected_alternatives`` is a list of dicts with ``action_ids``,
        ``program_ref``, and ``rejection_codes`` for each legal prefix that was
        built into a program but failed verification.
        """
        if self._release_only:
            raise RuntimeError(
                "BootstrapProposer cannot be used in release runtime"
            )

        text = orientation.source_text
        lattice = self._form_resolver.resolve(text)

        grounding_result = self._grounder.ground_text(text)
        self._contribution_expander.expand(grounding_result, lattice)

        content_unit_refs = [
            u.unit_ref for u in lattice.units if u.source_text.strip()
        ]
        pin = self._build_revision_pin(orientation)

        candidates, rejected, explored, truncated = self._search_detailed(
            lattice, content_unit_refs, orientation, pin
        )
        # Canonical tie-breaking: sort by program_ref, deduplicate.
        seen_refs: set[str] = set()
        unique: list[SemanticSwitchProgram] = []
        for p in sorted(candidates, key=lambda p: p.program_ref):
            if p.program_ref not in seen_refs:
                seen_refs.add(p.program_ref)
                unique.append(p)
        candidates = tuple(unique)

        result = ProposalResult(
            candidates=candidates,
            explored_states=explored,
            truncated=truncated,
            model_identity=self.model_identity,
        )
        return result, rejected

    # -- internal: revision pin ---------------------------------------------

    def _build_revision_pin(self, orientation: Orientation) -> RevisionPin:
        """Retain the exact orientation pin or fail closed on generation drift."""
        pin = orientation.revision_pin
        if pin.authority_generation != self._authority.generation:
            raise ValueError(
                "orientation revision pin authority generation mismatch"
            )
        return pin

    # -- internal: DFS search -----------------------------------------------

    def _search(
        self,
        lattice: Any,
        content_unit_refs: list[str],
        orientation: Orientation,
        pin: RevisionPin,
    ) -> tuple[list[SemanticSwitchProgram], int, bool]:
        """Bounded DFS over legal action prefixes.

        Searches for prefixes ending with ``complete_program``. If no
        complete_program candidates are found, an abstain fallback is added.

        Returns a tuple of (candidates, explored_states, truncated).
        """
        candidates: list[SemanticSwitchProgram] = []
        explored = 0
        truncated = False

        stack: list[tuple[ProgramAction, ...]] = [()]

        while stack:
            if len(candidates) >= self._max_candidates:
                truncated = True
                break
            if explored >= self._max_explored:
                truncated = True
                break

            prefix = stack.pop()
            explored += 1

            actions = self._generate_candidates(prefix, content_unit_refs)
            legal_actions = [
                a for a in actions if self._legal_action_index.is_legal(a, prefix)
            ]
            legal_actions.sort(key=lambda a: a.structural_id())

            # Push non-terminal actions in reverse order so the first
            # (by structural_id) is processed first (DFS).
            for action in reversed(legal_actions):
                if action.action_type == "complete_program":
                    new_prefix = prefix + (action,)
                    program = self._build_program(
                        new_prefix, lattice, orientation, pin
                    )
                    if program is not None:
                        result = self._verifier.verify(program)
                        if result.accepted:
                            candidates.append(program)
                            if len(candidates) >= self._max_candidates:
                                break
                elif action.action_type == "abstain":
                    # Skip abstain during DFS; only use as fallback.
                    continue
                else:
                    new_prefix = prefix + (action,)
                    if len(new_prefix) < self._max_actions:
                        stack.append(new_prefix)

            if len(candidates) >= self._max_candidates:
                truncated = True
                break

        # Fallback: if no complete_program candidates, add abstain.
        if not candidates:
            abstain_action = ProgramAction(
                action_ref="action:0",
                action_type="abstain",
                arguments=(),
                source_unit_refs=(),
            )
            program = self._build_program(
                (abstain_action,), lattice, orientation, pin
            )
            if program is not None:
                result = self._verifier.verify(program)
                if result.accepted:
                    candidates.append(program)

        return candidates, explored, truncated

    def _search_detailed(
        self,
        lattice: Any,
        content_unit_refs: list[str],
        orientation: Orientation,
        pin: RevisionPin,
    ) -> tuple[list[SemanticSwitchProgram], list[dict[str, Any]], int, bool]:
        """Bounded DFS over legal action prefixes with rejected tracking.

        Returns a tuple of (candidates, rejected, explored_states, truncated).
        """
        candidates: list[SemanticSwitchProgram] = []
        rejected: list[dict[str, Any]] = []
        explored = 0
        truncated = False

        stack: list[tuple[ProgramAction, ...]] = [()]

        while stack:
            if len(candidates) >= self._max_candidates:
                truncated = True
                break
            if explored >= self._max_explored:
                truncated = True
                break

            prefix = stack.pop()
            explored += 1

            actions = self._generate_candidates(prefix, content_unit_refs)
            legal_actions = [
                a for a in actions if self._legal_action_index.is_legal(a, prefix)
            ]
            legal_actions.sort(key=lambda a: a.structural_id())

            for action in reversed(legal_actions):
                if action.action_type == "complete_program":
                    new_prefix = prefix + (action,)
                    program = self._build_program(
                        new_prefix, lattice, orientation, pin
                    )
                    if program is not None:
                        result = self._verifier.verify(program)
                        if result.accepted:
                            candidates.append(program)
                            if len(candidates) >= self._max_candidates:
                                break
                        else:
                            rejected.append({
                                "action_ids": [
                                    a.structural_id() for a in new_prefix
                                ],
                                "program_ref": program.program_ref,
                                "rejection_codes": [
                                    e.code for e in result.errors
                                ],
                            })
                elif action.action_type == "abstain":
                    continue
                else:
                    new_prefix = prefix + (action,)
                    if len(new_prefix) < self._max_actions:
                        stack.append(new_prefix)

            if len(candidates) >= self._max_candidates:
                truncated = True
                break

        # Fallback: if no complete_program candidates, add abstain.
        if not candidates:
            abstain_action = ProgramAction(
                action_ref="action:0",
                action_type="abstain",
                arguments=(),
                source_unit_refs=(),
            )
            program = self._build_program(
                (abstain_action,), lattice, orientation, pin
            )
            if program is not None:
                result = self._verifier.verify(program)
                if result.accepted:
                    candidates.append(program)

        return candidates, rejected, explored, truncated

    # -- internal: candidate generation -------------------------------------

    def _generate_candidates(
        self, prefix: tuple[ProgramAction, ...], content_unit_refs: list[str]
    ) -> list[ProgramAction]:
        """Generate candidate actions for the given prefix.

        Generates only the essential actions for finding complete programs:
        ``select_context``, ``select_mode``, ``select_designation``,
        ``instantiate_operator``, ``bind_role``, and ``complete_program``.
        For ``bind_role``, uses actual lattice content units instead of the
        fallback ``unit:0``.

        The :class:`LegalActionIndex`'s ``is_legal`` predicate is used to
        filter these candidates, ensuring the same legality constraints as the
        verifier's exhaustive enumeration.
        """
        candidates: list[ProgramAction] = []
        idx = len(prefix)
        legal = self._legal_action_index

        # select_context
        for ctx in sorted(legal._context_refs):
            candidates.append(
                ProgramAction(
                    action_ref=f"action:{idx}",
                    action_type="select_context",
                    arguments=(ctx,),
                    source_unit_refs=(),
                )
            )
        if not legal._context_refs:
            candidates.append(
                ProgramAction(
                    action_ref=f"action:{idx}",
                    action_type="select_context",
                    arguments=("context:turn",),
                    source_unit_refs=(),
                )
            )

        # select_mode
        for mode in sorted(legal._modes):
            candidates.append(
                ProgramAction(
                    action_ref=f"action:{idx}",
                    action_type="select_mode",
                    arguments=(mode,),
                    source_unit_refs=(),
                )
            )

        # select_designation
        for target in sorted(legal._designation_targets):
            candidates.append(
                ProgramAction(
                    action_ref=f"action:{idx}",
                    action_type="select_designation",
                    arguments=("designation:0", target),
                    source_unit_refs=(),
                )
            )

        # instantiate_operator
        for op in sorted(legal._operators):
            candidates.append(
                ProgramAction(
                    action_ref=f"action:{idx}",
                    action_type="instantiate_operator",
                    arguments=(op, "designation:0"),
                    source_unit_refs=(),
                )
            )

        # bind_role — use actual lattice content units, skip already-bound roles/units
        operator: str | None = None
        for a in prefix:
            if a.action_type == "instantiate_operator" and a.arguments:
                operator = a.arguments[0]
                break
        if operator is not None:
            # Track already-bound roles and consumed units.
            bound_roles: set[str] = set()
            consumed_units: set[str] = set()
            for a in prefix:
                if a.action_type == "bind_role" and a.arguments:
                    bound_roles.add(a.arguments[0])
                    consumed_units.update(a.source_unit_refs)
            for role in legal._operator_roles.get(operator, ()):
                if role in bound_roles:
                    continue
                for unit in content_unit_refs:
                    if unit in consumed_units:
                        continue
                    candidates.append(
                        ProgramAction(
                            action_ref=f"action:{idx}",
                            action_type="bind_role",
                            arguments=(role, unit),
                            source_unit_refs=(unit,),
                        )
                    )

        # complete_program
        candidates.append(
            ProgramAction(
                action_ref=f"action:{idx}",
                action_type="complete_program",
                arguments=(),
                source_unit_refs=(),
            )
        )

        return candidates

    # -- internal: program building ------------------------------------------

    def _build_program(
        self,
        prefix: tuple[ProgramAction, ...],
        lattice: Any,
        orientation: Orientation,
        pin: RevisionPin,
    ) -> SemanticSwitchProgram | None:
        """Build a :class:`SemanticSwitchProgram` from a complete prefix.

        Returns None if the prefix is not a valid complete program.
        """
        if not prefix:
            return None

        last = prefix[-1]
        if last.action_type not in ("complete_program", "abstain"):
            return None

        # Extract mode from select_mode action.
        mode_name = "OBSERVE"
        for a in prefix:
            if a.action_type == "select_mode" and a.arguments:
                mode_name = a.arguments[0]
                break

        # Extract root graph ref from instantiate_operator action.
        root_refs: tuple[str, ...] = ()
        for a in prefix:
            if a.action_type == "instantiate_operator":
                root_refs = (a.action_ref,)
                break

        # Collect all source unit refs from the lattice.
        unit_refs = tuple(u.unit_ref for u in lattice.units)

        # Build source assignments.
        assignments = self._build_assignments(prefix, lattice)

        # Generate a deterministic program_ref.
        action_ids = [a.structural_id() for a in prefix]
        program_ref = stable_ref(
            "program",
            {
                "orientation": orientation.orientation_ref,
                "actions": sorted(action_ids),
                "mode": mode_name,
            },
        )

        return SemanticSwitchProgram(
            program_ref=program_ref,
            orientation_ref=orientation.orientation_ref,
            actions=prefix,
            root_graph_refs=root_refs,
            mode_ref=f"mode:{mode_name}",
            goal_refs=(),
            source_unit_refs=unit_refs,
            source_assignments=assignments,
            revision_pin=pin,
        )

    def _build_assignments(
        self,
        prefix: tuple[ProgramAction, ...],
        lattice: Any,
    ) -> tuple[SourceAssignment, ...]:
        """Build source assignments from the prefix and lattice.

        For each bind_role action, the source_unit_refs are consumed into a
        role assignment. For remaining units, punctuation/whitespace become
        noncritical discourse residuals and content units become noncritical
        qualifier residuals.
        """
        # Track which units are consumed by bind_role actions.
        consumed: dict[str, str] = {}  # unit_ref -> role_name
        for action in prefix:
            if action.action_type == "bind_role" and action.source_unit_refs:
                role_name = action.arguments[0] if action.arguments else ""
                for unit_ref in action.source_unit_refs:
                    consumed[unit_ref] = role_name

        assignments: list[SourceAssignment] = []
        for unit in lattice.units:
            unit_ref = unit.unit_ref
            is_punct = not unit.source_text.strip() or not unit.normalized_forms

            if unit_ref in consumed:
                role_name = consumed[unit_ref]
                assignments.append(
                    SourceAssignment(
                        assignment_ref=f"assignment:{unit_ref}",
                        source_unit_ref=unit_ref,
                        contribution_ref=f"contribution:{unit_ref}",
                        assignment_kind="role",
                        target_ref=f"target:{role_name}",
                        residual_kind=None,
                        critical=False,
                    )
                )
            elif is_punct:
                assignments.append(
                    SourceAssignment(
                        assignment_ref=f"assignment:{unit_ref}",
                        source_unit_ref=unit_ref,
                        contribution_ref=f"contribution:{unit_ref}",
                        assignment_kind="residual",
                        target_ref=None,
                        residual_kind="discourse",
                        critical=False,
                    )
                )
            else:
                assignments.append(
                    SourceAssignment(
                        assignment_ref=f"assignment:{unit_ref}",
                        source_unit_ref=unit_ref,
                        contribution_ref=f"contribution:{unit_ref}",
                        assignment_kind="residual",
                        target_ref=None,
                        residual_kind="qualifier",
                        critical=False,
                    )
                )

        return tuple(assignments)
