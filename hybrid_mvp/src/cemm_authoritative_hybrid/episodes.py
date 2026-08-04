"""Semantic Episodes, training sources, and the deterministic episode builder.

This module owns the Semantic Episode contract for Milestone 4. A
:class:`SemanticEpisode` serializes all six-phase inputs/outputs of the
semantic kernel:

    ORIENT -> PROPOSE -> VERIFY -> EVALUATE -> EFFECT -> REALIZE

It carries orientation, legal and rejected proposals, the selected program,
coverage, evaluation, effect-or-no-effect, response meaning, realization
receipt, authority/action hashes, generator lineage, review provenance, gap
receipt (if any), and the revision pin.

Training sources are typed as one of five closed kinds. Human/teacher language
is untrusted evidence: it may become an episode only when paired with an
already reviewed semantic target and independently re-verified. It never
creates an atom, rule, frame, policy, or transition.

The :class:`EpisodeBuilder` builds episodes from reviewed scenarios
deterministically: the same seed produces byte-identical output.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .canonical import stable_ref
from .coverage import CoverageReceipt
from .cycle import Orientation
from .expressions import VerifiedMeaning
from .gaps import GapReceipt
from .persistence import RevisionPin
from .programs import ACTION_ABI_HASH
from .proposal import RankedProgramCandidate
from .runtime import HybridRuntime

__all__ = [
    "EPISODE_ABI_VERSION",
    "SemanticEpisode",
    "TrainingSource",
    "TrainingSourceKind",
    "ScenarioCase",
    "EpisodeBuilder",
    "validate_episode",
    "validate_training_source",
    "load_scenarios",
    "write_episodes",
]

# The active Semantic Episode ABI version.
EPISODE_ABI_VERSION: int = 2

# Closed set of training source kinds.
_VALID_SOURCE_KINDS: frozenset[str] = frozenset(
    {
        "reviewed_scenario",
        "authority_derived",
        "human_paraphrase",
        "teacher_paraphrase",
        "verified_correction",
    }
)

# Kinds that represent untrusted evidence (human/teacher language).
_UNTRUSTED_KINDS: frozenset[str] = frozenset(
    {"human_paraphrase", "teacher_paraphrase", "verified_correction"}
)


# ---------------------------------------------------------------------------
# Training source kind enum
# ---------------------------------------------------------------------------


class TrainingSourceKind(Enum):
    """Closed set of training source kinds.

    - ``reviewed_scenario``: a reviewed semantic scenario with assertions.
    - ``authority_derived``: an episode derived directly from authority data.
    - ``human_paraphrase``: untrusted human language; requires a reviewed
      semantic target and independent re-verification.
    - ``teacher_paraphrase``: untrusted teacher language; requires a reviewed
      semantic target and independent re-verification.
    - ``verified_correction``: a verified correction to a prior episode;
      requires independent re-verification.

    Human/teacher language never creates an atom, rule, frame, policy, or
    transition. It is evidence, not authority.
    """

    REVIEWED_SCENARIO = "reviewed_scenario"
    AUTHORITY_DERIVED = "authority_derived"
    HUMAN_PARAPHRASE = "human_paraphrase"
    TEACHER_PARAPHRASE = "teacher_paraphrase"
    VERIFIED_CORRECTION = "verified_correction"


# ---------------------------------------------------------------------------
# ScenarioCase — a reviewed scenario with semantic assertions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScenarioCase:
    """A reviewed scenario case with semantic assertions.

    Each case specifies semantic assertions rather than exact prose. The
    ``surface_examples`` field provides illustrative surface forms, but the
    assertions are the semantic contract.

    Attributes:
        scenario_ref: a unique ref starting with ``scenario:``.
        review_status: always ``"reviewed"`` for the source matrix.
        competency_category: the semantic competency category.
        semantic_assertions: a tuple of structured assertion dicts. Each
            assertion has a ``kind`` key and category-specific fields.
        surface_examples: a tuple of illustrative surface form strings.
        expected_gap_kind: the expected :class:`GapKind` value, or None if the
            scenario is expected to resolve.
        metadata: optional metadata dict (e.g. language, polarity).
    """

    scenario_ref: str
    review_status: str
    competency_category: str
    semantic_assertions: tuple[dict[str, Any], ...]
    surface_examples: tuple[str, ...]
    expected_gap_kind: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.semantic_assertions, tuple):
            object.__setattr__(
                self, "semantic_assertions", tuple(self.semantic_assertions)
            )
        if not isinstance(self.surface_examples, tuple):
            object.__setattr__(
                self, "surface_examples", tuple(self.surface_examples)
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenario_ref": self.scenario_ref,
            "review_status": self.review_status,
            "competency_category": self.competency_category,
            "semantic_assertions": [dict(a) for a in self.semantic_assertions],
            "surface_examples": list(self.surface_examples),
            "expected_gap_kind": self.expected_gap_kind,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScenarioCase":
        return cls(
            scenario_ref=data["scenario_ref"],
            review_status=data["review_status"],
            competency_category=data["competency_category"],
            semantic_assertions=tuple(data.get("semantic_assertions", ())),
            surface_examples=tuple(data.get("surface_examples", ())),
            expected_gap_kind=data.get("expected_gap_kind"),
            metadata=dict(data.get("metadata", {})),
        )


# ---------------------------------------------------------------------------
# TrainingSource — typed training source provenance
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrainingSource:
    """Typed provenance for a training source.

    Human/teacher language is untrusted evidence: it may become an episode
    only when paired with an already reviewed semantic target
    (``reviewed_target_ref``) and independently re-verified
    (``independently_reverified == True``). It never creates an atom, rule,
    frame, policy, or transition.

    Attributes:
        source_kind: the :class:`TrainingSourceKind`.
        source_ref: the ref of the source (scenario, utterance, correction).
        reviewed_target_ref: the reviewed semantic target ref, required for
            untrusted evidence kinds.
        independently_reverified: whether the source was independently
            re-verified, required for untrusted evidence kinds.
    """

    source_kind: TrainingSourceKind
    source_ref: str
    reviewed_target_ref: str | None = None
    independently_reverified: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_kind": self.source_kind.value,
            "source_ref": self.source_ref,
            "reviewed_target_ref": self.reviewed_target_ref,
            "independently_reverified": self.independently_reverified,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TrainingSource":
        return cls(
            source_kind=TrainingSourceKind(data["source_kind"]),
            source_ref=data["source_ref"],
            reviewed_target_ref=data.get("reviewed_target_ref"),
            independently_reverified=bool(data.get("independently_reverified", False)),
        )


# ---------------------------------------------------------------------------
# SemanticEpisode — the complete six-phase serialization
# ---------------------------------------------------------------------------


_MAX_EPISODE_CANDIDATES = 64
_MAX_EPISODE_ROWS = 64
_MAX_EPISODE_TEXT = 4096
_MAX_EPISODE_DEPTH = 24
_MAX_EPISODE_NODES = 32768
_EPISODE_FIELD_ORDER = (
    "episode_ref",
    "abi_version",
    "scenario_ref",
    "orientation",
    "legal_proposals",
    "rejected_proposals",
    "selected_program",
    "verified_meaning",
    "coverage",
    "evaluation",
    "effect_or_no_effect",
    "response_meaning",
    "realization_receipt",
    "authority_hash",
    "action_abi_hash",
    "generator_lineage",
    "review_provenance",
    "gap_receipt",
    "revisions",
    "training_source",
)
_EPISODE_FIELDS = frozenset(_EPISODE_FIELD_ORDER)


def _episode_text(value: object, name: str) -> str:
    if type(value) is not str or not value:
        raise TypeError(f"{name} must be an exact nonempty str")
    if len(value) > _MAX_EPISODE_TEXT:
        raise ValueError(f"{name} exceeds the episode text bound")
    return value


def _bound_episode_wire(value: object) -> None:
    remaining = _MAX_EPISODE_NODES

    def visit(item: object, depth: int) -> None:
        nonlocal remaining
        remaining -= 1
        if remaining < 0:
            raise ValueError("episode wire exceeds the node bound")
        if depth > _MAX_EPISODE_DEPTH:
            raise ValueError("episode wire exceeds the depth bound")
        if item is None or type(item) in {bool, int}:
            return
        if type(item) is str:
            if len(item) > _MAX_EPISODE_TEXT:
                raise ValueError("episode wire string exceeds the text bound")
            return
        if type(item) is list:
            if len(item) > 256:
                raise ValueError("episode wire list exceeds the row bound")
            for child in item:
                visit(child, depth + 1)
            return
        if type(item) is dict:
            if len(item) > 64:
                raise ValueError("episode wire object exceeds the field bound")
            for key, child in item.items():
                if type(key) is not str or not key or len(key) > 128:
                    raise TypeError("episode wire keys must be bounded exact strings")
                visit(child, depth + 1)
            return
        raise TypeError("episode wire contains a non-canonical JSON value")

    visit(value, 0)


def _freeze_episode_json(value: object) -> object:
    if type(value) is dict:
        return MappingProxyType(
            {key: _freeze_episode_json(item) for key, item in value.items()}
        )
    if type(value) is list:
        return tuple(_freeze_episode_json(item) for item in value)
    return value


def _thaw_episode_json(value: object) -> object:
    if type(value) is MappingProxyType:
        return {key: _thaw_episode_json(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_thaw_episode_json(item) for item in value]
    return value


def _episode_object(value: object, name: str) -> dict[str, Any]:
    if type(value) is dict:
        result = value
    elif type(value) is MappingProxyType:
        result = _thaw_episode_json(value)
    else:
        raise TypeError(f"{name} must be an exact object")
    assert type(result) is dict
    _bound_episode_wire(result)
    return result


def _decode_derivation(value: object, name: str) -> dict[str, Any]:
    row = _episode_object(value, name)
    expected = frozenset(
        {
            "artifact_role", "candidate_ref", "rank", "score_q",
            "provenance_refs", "program",
        }
    )
    if frozenset(row) != expected:
        raise ValueError(f"{name} fields mismatch")
    if row["artifact_role"] != "derivation_lineage":
        raise ValueError(f"{name} must be derivation_lineage")
    candidate = RankedProgramCandidate.from_dict(
        {
            "candidate_ref": row["candidate_ref"],
            "rank": row["rank"],
            "score_q": row["score_q"],
            "provenance_refs": row["provenance_refs"],
            "program": row["program"],
        }
    )
    canonical = _serialize_derivation(candidate)
    if canonical != row:
        raise ValueError(f"non-canonical {name} encoding")
    return canonical


def _decode_rejection(value: object) -> dict[str, Any]:
    row = _episode_object(value, "rejected proposal")
    if frozenset(row) != frozenset(
        {"candidate_ref", "program_ref", "rejection_codes"}
    ):
        raise ValueError("rejected proposal fields mismatch")
    candidate_ref = _episode_text(row["candidate_ref"], "candidate_ref")
    program_ref = _episode_text(row["program_ref"], "program_ref")
    codes = row["rejection_codes"]
    if type(codes) is not list or not codes or len(codes) > _MAX_EPISODE_ROWS:
        raise ValueError("rejection_codes must be a bounded nonempty list")
    canonical_codes = [_episode_text(code, "rejection_code") for code in codes]
    if len(canonical_codes) != len(set(canonical_codes)):
        raise ValueError("rejection_codes must be unique")
    return {
        "candidate_ref": candidate_ref,
        "program_ref": program_ref,
        "rejection_codes": canonical_codes,
    }


def _exact_episode_projection(
    value: object, expected: frozenset[str], name: str
) -> dict[str, Any]:
    row = _episode_object(value, name)
    if frozenset(row) != expected:
        raise ValueError(f"{name} fields mismatch")
    return row


def _canonical_episode_fields(
    *,
    scenario_ref: object,
    orientation: object,
    legal_proposals: object,
    rejected_proposals: object,
    selected_program: object,
    verified_meaning: object,
    coverage: object,
    evaluation: object,
    effect_or_no_effect: object,
    response_meaning: object,
    realization_receipt: object,
    authority_hash: object,
    action_abi_hash: object,
    generator_lineage: object,
    review_provenance: object,
    gap_receipt: object,
    revisions: object,
    training_source: object,
) -> dict[str, Any]:
    scenario = _episode_text(scenario_ref, "scenario_ref")
    orientation_row = _episode_object(orientation, "orientation")
    orientation_value = Orientation.from_dict(orientation_row)
    orientation_canonical = orientation_value.as_dict()

    if type(legal_proposals) is not tuple:
        raise TypeError("legal_proposals must be an exact tuple")
    if len(legal_proposals) > _MAX_EPISODE_CANDIDATES:
        raise ValueError("legal_proposals exceeds the candidate bound")
    legal = tuple(
        _decode_derivation(row, "legal proposal") for row in legal_proposals
    )
    legal_refs = tuple(row["candidate_ref"] for row in legal)
    if len(legal_refs) != len(set(legal_refs)):
        raise ValueError("legal proposal candidate refs must be unique")

    if type(rejected_proposals) is not tuple:
        raise TypeError("rejected_proposals must be an exact tuple")
    if len(rejected_proposals) > _MAX_EPISODE_CANDIDATES:
        raise ValueError("rejected_proposals exceeds the candidate bound")
    rejected = tuple(_decode_rejection(row) for row in rejected_proposals)
    rejected_refs = tuple(row["candidate_ref"] for row in rejected)
    if len(rejected_refs) != len(set(rejected_refs)):
        raise ValueError("rejected proposal candidate refs must be unique")
    if set(legal_refs) & set(rejected_refs):
        raise ValueError("candidate cannot be both legal and rejected")

    selected_row = _episode_object(selected_program, "selected_program")
    meaning_row = _episode_object(verified_meaning, "verified_meaning")
    coverage_row = _episode_object(coverage, "coverage")
    selected = _decode_derivation(selected_row, "selected_program") if selected_row else {}
    meaning = VerifiedMeaning.from_dict(meaning_row) if meaning_row else None
    coverage_value = CoverageReceipt.from_dict(coverage_row) if coverage_row else None

    if _episode_object(evaluation, "evaluation") != {}:
        raise ValueError("EVALUATE is not admitted at R1")
    effect = _episode_object(effect_or_no_effect, "effect_or_no_effect")
    if effect != {"status": "not_admitted"}:
        raise ValueError("EFFECT is not admitted at R1")
    if _episode_object(response_meaning, "response_meaning") != {}:
        raise ValueError("response meaning is not admitted at R1")
    if _episode_object(realization_receipt, "realization_receipt") != {}:
        raise ValueError("REALIZE is not admitted at R1")

    gap_row = _episode_object(gap_receipt, "gap_receipt")
    gap = GapReceipt.from_dict(gap_row)
    revisions_row = _episode_object(revisions, "revisions")
    pin = RevisionPin.from_dict(revisions_row)
    if pin != orientation_value.revision_pin:
        raise ValueError("episode revision pin differs from Orientation")

    if meaning is None:
        if selected or coverage_value is not None:
            raise ValueError("unselected episode cannot carry derivation or meaning coverage")
        if gap.status == "later_owner_not_admitted":
            raise ValueError("later-owner gap requires VerifiedMeaning")
    else:
        if not selected or coverage_value is None:
            raise ValueError("VerifiedMeaning requires derivation and coverage lineage")
        candidate_ref = selected["candidate_ref"]
        if candidate_ref not in legal_refs:
            raise ValueError("selected derivation is not one legal proposal")
        program_ref = selected["program"]["program_ref"]
        if meaning.program_ref != program_ref:
            raise ValueError("Program derivation and VerifiedMeaning differ")
        if coverage_value.program_ref != meaning.program_ref:
            raise ValueError("coverage and VerifiedMeaning program refs differ")
        if coverage_value.coverage_receipt_ref != meaning.coverage_receipt_ref:
            raise ValueError("coverage and VerifiedMeaning receipt refs differ")
        if meaning.revision_pin != pin:
            raise ValueError("VerifiedMeaning revision pin differs from episode")
        if gap.status != "later_owner_not_admitted":
            raise ValueError("selected R1 episode requires later_owner_not_admitted gap")
        if gap.source_refs != (meaning.verified_meaning_ref,):
            raise ValueError("later-owner gap does not bind VerifiedMeaning")
        if gap.missing_contract_refs != ("contract:r3:evaluate",):
            raise ValueError("later-owner gap does not bind the R3 contract")
        if gap.safe_response_action != "stop_without_surface":
            raise ValueError("later-owner gap must stop without surface")

    authority = _episode_text(authority_hash, "authority_hash")
    expected_authority = stable_ref(
        "authority", {"generation": pin.authority_generation}
    )
    if authority != expected_authority:
        raise ValueError("authority_hash does not bind the runtime revision pin")
    if action_abi_hash != ACTION_ABI_HASH:
        raise ValueError("episode action_abi_hash mismatch")

    generator = _exact_episode_projection(
        generator_lineage,
        frozenset(
            {
                "seed", "authority_generation", "proposer", "runtime_profile",
                "surface", "normalized_text",
            }
        ),
        "generator_lineage",
    )
    if type(generator["seed"]) is not int or not 0 <= generator["seed"] < 2**63:
        raise ValueError("generator seed must be a bounded exact int")
    if generator["authority_generation"] != pin.authority_generation:
        raise ValueError("generator authority lineage mismatch")
    _episode_text(generator["proposer"], "generator proposer")
    _episode_text(generator["runtime_profile"], "runtime profile")
    if type(generator["surface"]) is not str:
        raise TypeError("generator surface must be an exact str")
    if generator["surface"] != orientation_value.source_text:
        raise ValueError("generator surface differs from Orientation")
    if generator["normalized_text"] != generator["surface"].strip().lower():
        raise ValueError("generator normalized_text mismatch")

    review = _exact_episode_projection(
        review_provenance,
        frozenset({"review_status", "scenario_ref", "competency_category"}),
        "review_provenance",
    )
    _episode_text(review["review_status"], "review_status")
    _episode_text(review["competency_category"], "competency_category")
    if review["scenario_ref"] != scenario:
        raise ValueError("review provenance scenario mismatch")

    training = _exact_episode_projection(
        training_source,
        frozenset(
            {
                "source_kind", "source_ref", "reviewed_target_ref",
                "independently_reverified",
            }
        ),
        "training_source",
    )
    if training != {
        "source_kind": TrainingSourceKind.REVIEWED_SCENARIO.value,
        "source_ref": scenario,
        "reviewed_target_ref": None,
        "independently_reverified": False,
    }:
        raise ValueError("R1 diagnostic episode cannot claim training gold")

    canonical = {
        "scenario_ref": scenario,
        "orientation": orientation_canonical,
        "legal_proposals": list(legal),
        "rejected_proposals": list(rejected),
        "selected_program": selected,
        "verified_meaning": meaning.as_dict() if meaning is not None else {},
        "coverage": coverage_value.as_dict() if coverage_value is not None else {},
        "evaluation": {},
        "effect_or_no_effect": {"status": "not_admitted"},
        "response_meaning": {},
        "realization_receipt": {},
        "authority_hash": authority,
        "action_abi_hash": ACTION_ABI_HASH,
        "generator_lineage": generator,
        "review_provenance": review,
        "gap_receipt": gap.as_dict(),
        "revisions": pin.as_dict(),
        "training_source": training,
    }
    _bound_episode_wire(canonical)
    return canonical


def _episode_material(fields: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "abi_version": EPISODE_ABI_VERSION,
        **{key: _thaw_episode_json(value) for key, value in fields.items()},
    }


@dataclass(frozen=True)
class SemanticEpisode:
    """Immutable, content-addressed R1 diagnostic episode (Episode ABI 2).

    This artifact records canonical runtime outputs through VERIFY.  Program
    values are derivation lineage; ``verified_meaning`` is the semantic owner.
    It is explicitly not R4 training gold and carries no later-phase artifact.
    """

    episode_ref: str
    abi_version: int
    scenario_ref: str
    orientation: Mapping[str, Any]
    legal_proposals: tuple[Mapping[str, Any], ...]
    rejected_proposals: tuple[Mapping[str, Any], ...]
    selected_program: Mapping[str, Any]
    verified_meaning: Mapping[str, Any]
    coverage: Mapping[str, Any]
    evaluation: Mapping[str, Any]
    effect_or_no_effect: Mapping[str, Any]
    response_meaning: Mapping[str, Any]
    realization_receipt: Mapping[str, Any]
    authority_hash: str
    action_abi_hash: str
    generator_lineage: Mapping[str, Any]
    review_provenance: Mapping[str, Any]
    gap_receipt: Mapping[str, Any]
    revisions: Mapping[str, Any]
    training_source: Mapping[str, Any]

    def __post_init__(self) -> None:
        if type(self.abi_version) is not int or self.abi_version != EPISODE_ABI_VERSION:
            raise ValueError("unsupported Semantic Episode ABI version")
        _episode_text(self.episode_ref, "episode_ref")
        fields = _canonical_episode_fields(
            **{
                name: getattr(self, name)
                for name in _EPISODE_FIELD_ORDER
                if name not in {"episode_ref", "abi_version"}
            }
        )
        frozen = {key: _freeze_episode_json(value) for key, value in fields.items()}
        for name, value in frozen.items():
            if name in {"legal_proposals", "rejected_proposals"}:
                assert type(value) is tuple
            object.__setattr__(self, name, value)
        expected = stable_ref("episode", _episode_material(frozen))
        if self.episode_ref != expected:
            raise ValueError("episode_ref mismatch")

    @staticmethod
    def _from_canonical(
        episode_ref: str, fields: Mapping[str, Any]
    ) -> "SemanticEpisode":
        value = object.__new__(SemanticEpisode)
        object.__setattr__(value, "episode_ref", episode_ref)
        object.__setattr__(value, "abi_version", EPISODE_ABI_VERSION)
        for name, item in fields.items():
            object.__setattr__(value, name, _freeze_episode_json(item))
        return value

    @classmethod
    def create(cls, **values: Any) -> "SemanticEpisode":
        if cls is not SemanticEpisode:
            raise TypeError("SemanticEpisode factories reject subclasses")
        if frozenset(values) != _EPISODE_FIELDS - {"episode_ref", "abi_version"}:
            raise ValueError("SemanticEpisode create fields mismatch")
        fields = _canonical_episode_fields(**values)
        episode_ref = stable_ref("episode", _episode_material(fields))
        return SemanticEpisode._from_canonical(episode_ref, fields)

    def as_dict(self) -> dict[str, Any]:
        fields = {
            name: _thaw_episode_json(getattr(self, name))
            for name in _EPISODE_FIELD_ORDER
            if name not in {"episode_ref", "abi_version"}
        }
        return {
            "episode_ref": self.episode_ref,
            "abi_version": EPISODE_ABI_VERSION,
            **fields,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SemanticEpisode":
        if cls is not SemanticEpisode:
            raise TypeError("SemanticEpisode factories reject subclasses")
        if type(data) is not dict:
            raise TypeError("SemanticEpisode payload must be an exact dict")
        if len(data) != len(_EPISODE_FIELDS):
            raise ValueError("SemanticEpisode fields mismatch")
        if any(type(key) is not str for key in data):
            raise TypeError("SemanticEpisode field names must be exact strings")
        if frozenset(data) != _EPISODE_FIELDS:
            raise ValueError("SemanticEpisode fields mismatch")
        _bound_episode_wire(data)
        if type(data["abi_version"]) is not int or data["abi_version"] != EPISODE_ABI_VERSION:
            raise ValueError("unsupported Semantic Episode ABI version")
        if type(data["legal_proposals"]) is not list:
            raise TypeError("legal_proposals wire value must be an exact list")
        if type(data["rejected_proposals"]) is not list:
            raise TypeError("rejected_proposals wire value must be an exact list")
        stored_ref = _episode_text(data["episode_ref"], "episode_ref")
        values = {
            key: data[key]
            for key in _EPISODE_FIELD_ORDER
            if key not in {"episode_ref", "abi_version", "legal_proposals", "rejected_proposals"}
        }
        values["legal_proposals"] = tuple(data["legal_proposals"])
        values["rejected_proposals"] = tuple(data["rejected_proposals"])
        rebuilt = cls.create(**values)
        if rebuilt.episode_ref != stored_ref:
            raise ValueError("episode_ref mismatch")
        if rebuilt.as_dict() != data:
            raise ValueError("non-canonical SemanticEpisode encoding")
        return rebuilt


def validate_episode(data: dict[str, Any]) -> None:
    """Authenticate one exact Semantic Episode ABI 2 wire value."""
    SemanticEpisode.from_dict(data)

def validate_training_source(data: dict[str, Any]) -> None:
    """Validate a serialized training source dict.

    Untrusted evidence kinds (human_paraphrase, teacher_paraphrase,
    verified_correction) require a reviewed_target_ref and independent
    re-verification.

    Raises:
        ValueError: if the training source is invalid.
    """
    if not isinstance(data, dict):
        raise ValueError("training source must be a dict")
    kind = data.get("source_kind")
    if kind not in _VALID_SOURCE_KINDS:
        raise ValueError(f"unknown training source kind: {kind!r}")
    if not data.get("source_ref"):
        raise ValueError("training source missing source_ref")
    if kind in _UNTRUSTED_KINDS:
        if not data.get("reviewed_target_ref"):
            raise ValueError(
                f"{kind} requires a reviewed_target_ref"
            )
        if not data.get("independently_reverified"):
            raise ValueError(
                f"{kind} requires independent re-verification"
            )


# ---------------------------------------------------------------------------
# EpisodeBuilder — builds episodes from scenarios deterministically
# ---------------------------------------------------------------------------


def _serialize_orientation(orientation: Orientation) -> dict[str, Any]:
    """Serialize one exact Orientation ABI 1 value without cache metadata."""
    if type(orientation) is not Orientation:
        raise TypeError("orientation must be Orientation")
    return orientation.as_dict()

def _serialize_derivation(candidate: Any) -> dict[str, Any]:
    """Serialize a ranked construction derivation without calling it meaning."""
    return {
        "artifact_role": "derivation_lineage",
        "candidate_ref": candidate.candidate_ref,
        "rank": candidate.rank,
        "score_q": candidate.score_q,
        "provenance_refs": list(candidate.provenance_refs),
        "program": candidate.program.as_dict(),
    }


def _serialize_coverage_receipt(receipt: Any) -> dict[str, Any]:
    """Serialize the complete canonical Coverage Receipt ABI 2 value."""
    if receipt is None:
        return {}
    if type(receipt) is not CoverageReceipt:
        raise TypeError("coverage receipt must be exact CoverageReceipt")
    return receipt.as_dict()


def _serialize_gap_receipt(receipt: Any) -> dict[str, Any] | None:
    """Serialize a GapReceipt to a JSON-compatible dict."""
    if receipt is None:
        return None
    return receipt.as_dict()


class EpisodeBuilder:
    """Build R1 diagnostic episodes through one injected canonical runtime.

    ``SemanticSwitchProgram`` values are serialized only as construction
    derivation lineage.  ``VerificationBatch.selected_meaning`` owns the
    canonical meaning.  Because R1 admits no later owner, every cycle retains
    its typed gap and emits no evaluation, effect, response, or surface.
    """

    def __init__(
        self,
        *,
        authority: Any,
        runtime: HybridRuntime,
        seed: int = 1701,
    ) -> None:
        if type(runtime) is not HybridRuntime:
            raise TypeError("runtime must be an exact HybridRuntime")
        if type(seed) is not int:
            raise TypeError("seed must be an exact int")
        authority_generation = getattr(authority, "generation", None)
        runtime_generation = runtime.stores.revision_pin().authority_generation
        if authority_generation != runtime_generation:
            raise ValueError("authority generation differs from runtime lineage")
        self._authority = authority
        self._runtime = runtime
        self._seed = seed

    @classmethod
    def for_reviewed_scenarios(
        cls, *, runtime: HybridRuntime, seed: int = 1701
    ) -> "EpisodeBuilder":
        """Bind an already activated canonical runtime for reviewed scenarios."""
        if type(runtime) is not HybridRuntime:
            raise TypeError("runtime must be an exact HybridRuntime")
        return cls(authority=runtime.authority, runtime=runtime, seed=seed)
    def build_episode(self, case: ScenarioCase) -> SemanticEpisode:
        """Build one R1 diagnostic episode from a reviewed scenario."""
        surface = case.surface_examples[0] if case.surface_examples else ""
        process_result = self._runtime.process(
            f"session:{case.scenario_ref}", surface, trace=False
        )
        orientation = process_result.orientation
        proposal = process_result.proposal
        verification = process_result.verification

        accepted_candidate_refs = frozenset(
            receipt.candidate_ref
            for receipt in verification.candidate_receipts
            if not receipt.verification_errors
        )
        legal_proposals = tuple(
            _serialize_derivation(candidate)
            for candidate in proposal.candidates
            if candidate.candidate_ref in accepted_candidate_refs
        )
        rejected_serialized = tuple(
            {
                "candidate_ref": receipt.candidate_ref,
                "program_ref": receipt.program_ref,
                "rejection_codes": [
                    error.code for error in receipt.verification_errors
                ],
            }
            for receipt in verification.candidate_receipts
            if receipt.verification_errors
        )

        meaning = verification.selected_meaning
        selected_candidate = None
        selected_receipt = None
        if meaning is not None:
            selected_candidate = next(
                (
                    candidate
                    for candidate in proposal.candidates
                    if candidate.candidate_ref
                    == verification.selected_candidate_ref
                    and candidate.program.program_ref == meaning.program_ref
                ),
                None,
            )
            selected_receipt = next(
                (
                    receipt
                    for receipt in verification.candidate_receipts
                    if receipt.receipt_ref == meaning.verification_receipt_ref
                    and receipt.candidate_ref == verification.selected_candidate_ref
                ),
                None,
            )
            if selected_candidate is None or selected_receipt is None:
                raise ValueError("VerifiedMeaning derivation lineage is unavailable")

        selected_program = (
            _serialize_derivation(selected_candidate)
            if selected_candidate is not None
            else {}
        )
        verified_meaning = meaning.as_dict() if meaning is not None else {}
        coverage = _serialize_coverage_receipt(
            selected_receipt.coverage_receipt if selected_receipt is not None else None
        )

        authority_hash = stable_ref(
            "authority", {"generation": self._authority.generation}
        )
        generator_lineage = {
            "seed": self._seed,
            "authority_generation": self._authority.generation,
            "proposer": type(self._runtime.proposal_model).__name__,
            "runtime_profile": self._runtime.profile,
            "surface": surface,
            "normalized_text": surface.strip().lower(),
        }
        review_provenance = {
            "review_status": case.review_status,
            "scenario_ref": case.scenario_ref,
            "competency_category": case.competency_category,
        }
        training_source = TrainingSource(
            source_kind=TrainingSourceKind.REVIEWED_SCENARIO,
            source_ref=case.scenario_ref,
            reviewed_target_ref=None,
            independently_reverified=False,
        ).as_dict()
        return SemanticEpisode.create(
            scenario_ref=case.scenario_ref,
            orientation=_serialize_orientation(orientation),
            legal_proposals=legal_proposals,
            rejected_proposals=rejected_serialized,
            selected_program=selected_program,
            verified_meaning=verified_meaning,
            coverage=coverage,
            evaluation={},
            effect_or_no_effect={"status": "not_admitted"},
            response_meaning={},
            realization_receipt={},
            authority_hash=authority_hash,
            action_abi_hash=ACTION_ABI_HASH,
            generator_lineage=generator_lineage,
            review_provenance=review_provenance,
            gap_receipt=_serialize_gap_receipt(process_result.gap_receipt),
            revisions=process_result.final_revision_pin.as_dict(),
            training_source=training_source,
        )

    def build_all(self, cases: list[ScenarioCase]) -> list[SemanticEpisode]:
        """Build episodes deterministically through the injected runtime."""
        return [self.build_episode(case) for case in cases]

# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def load_scenarios(path: Path) -> list[ScenarioCase]:
    """Load scenarios from a JSONL file."""
    cases: list[ScenarioCase] = []
    for line in path.read_text(encoding="utf-8").strip().splitlines():
        if line.strip():
            cases.append(ScenarioCase.from_dict(json.loads(line)))
    return cases


def write_episodes(episodes: list[SemanticEpisode], output_path: Path) -> None:
    """Write episodes as JSONL (one JSON object per line, canonical)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(
            episode.as_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        for episode in episodes
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
