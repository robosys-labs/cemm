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
from typing import Any, Mapping

from .canonical import stable_ref

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
EPISODE_ABI_VERSION: int = 1

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


@dataclass(frozen=True)
class SemanticEpisode:
    """A complete semantic episode serializing all six-phase inputs/outputs.

    Carries orientation, legal and rejected proposals, the selected program,
    coverage, evaluation, effect-or-no-effect, response meaning, realization
    receipt, authority/action hashes, generator lineage, review provenance,
    gap receipt (if any), and the revision pin.

    The ``effect_or_no_effect`` field is the no-effect marker: it is always
    present (either an effect receipt or an explicit ``{"status": "no_effect"}``
    marker). Schema validation rejects episodes with a missing no-effect
    marker.

    Attributes:
        episode_ref: a stable ref for this episode.
        abi_version: the Semantic Episode ABI version (always 1).
        scenario_ref: the source scenario ref.
        orientation: serialized ORIENT phase output.
        legal_proposals: tuple of serialized legal proposal dicts.
        rejected_proposals: tuple of serialized rejected proposal dicts.
        selected_program: the serialized selected program.
        coverage: the serialized coverage receipt.
        evaluation: the serialized EVALUATE phase output.
        effect_or_no_effect: the effect receipt or no-effect marker.
        response_meaning: the serialized response meaning.
        realization_receipt: the serialized realization receipt.
        authority_hash: the authority generation hash.
        action_encoding_hash: the selected program's action encoding hash.
        generator_lineage: lineage metadata for the generator.
        review_provenance: review provenance metadata.
        gap_receipt: the serialized gap receipt, or None.
        revisions: the serialized revision pin.
        training_source: the typed training source provenance.
    """

    episode_ref: str
    abi_version: int
    scenario_ref: str
    orientation: dict[str, Any]
    legal_proposals: tuple[dict[str, Any], ...]
    rejected_proposals: tuple[dict[str, Any], ...]
    selected_program: dict[str, Any]
    coverage: dict[str, Any]
    evaluation: dict[str, Any]
    effect_or_no_effect: dict[str, Any]
    response_meaning: dict[str, Any]
    realization_receipt: dict[str, Any]
    authority_hash: str
    action_encoding_hash: str
    generator_lineage: dict[str, Any]
    review_provenance: dict[str, Any]
    gap_receipt: dict[str, Any] | None = None
    revisions: dict[str, Any] = field(default_factory=dict)
    training_source: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.legal_proposals, tuple):
            object.__setattr__(
                self, "legal_proposals", tuple(self.legal_proposals)
            )
        if not isinstance(self.rejected_proposals, tuple):
            object.__setattr__(
                self, "rejected_proposals", tuple(self.rejected_proposals)
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "episode_ref": self.episode_ref,
            "abi_version": self.abi_version,
            "scenario_ref": self.scenario_ref,
            "orientation": self.orientation,
            "legal_proposals": list(self.legal_proposals),
            "rejected_proposals": list(self.rejected_proposals),
            "selected_program": self.selected_program,
            "coverage": self.coverage,
            "evaluation": self.evaluation,
            "effect_or_no_effect": self.effect_or_no_effect,
            "response_meaning": self.response_meaning,
            "realization_receipt": self.realization_receipt,
            "authority_hash": self.authority_hash,
            "action_encoding_hash": self.action_encoding_hash,
            "generator_lineage": self.generator_lineage,
            "review_provenance": self.review_provenance,
            "gap_receipt": self.gap_receipt,
            "revisions": self.revisions,
            "training_source": self.training_source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SemanticEpisode":
        return cls(
            episode_ref=data["episode_ref"],
            abi_version=data["abi_version"],
            scenario_ref=data["scenario_ref"],
            orientation=data["orientation"],
            legal_proposals=tuple(data.get("legal_proposals", ())),
            rejected_proposals=tuple(data.get("rejected_proposals", ())),
            selected_program=data["selected_program"],
            coverage=data["coverage"],
            evaluation=data["evaluation"],
            effect_or_no_effect=data["effect_or_no_effect"],
            response_meaning=data["response_meaning"],
            realization_receipt=data["realization_receipt"],
            authority_hash=data["authority_hash"],
            action_encoding_hash=data["action_encoding_hash"],
            generator_lineage=data["generator_lineage"],
            review_provenance=data["review_provenance"],
            gap_receipt=data.get("gap_receipt"),
            revisions=data.get("revisions", {}),
            training_source=data.get("training_source", {}),
        )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_episode(data: dict[str, Any]) -> None:
    """Validate a serialized episode dict against the Semantic Episode contract.

    Rejects missing no-effect markers and unknown ABI versions.

    Raises:
        ValueError: if the episode is invalid.
    """
    if not isinstance(data, dict):
        raise ValueError("episode must be a dict")
    if data.get("abi_version") != EPISODE_ABI_VERSION:
        raise ValueError(
            f"unknown or missing ABI version: {data.get('abi_version')!r}"
        )
    required = [
        "episode_ref",
        "scenario_ref",
        "orientation",
        "legal_proposals",
        "rejected_proposals",
        "selected_program",
        "coverage",
        "evaluation",
        "effect_or_no_effect",
        "response_meaning",
        "realization_receipt",
        "authority_hash",
        "action_encoding_hash",
        "generator_lineage",
        "review_provenance",
    ]
    for key in required:
        if key not in data:
            raise ValueError(f"episode missing required field: {key}")
    # The no-effect marker must always be present.
    effect = data.get("effect_or_no_effect")
    if effect is None:
        raise ValueError("episode missing no-effect marker")
    if not isinstance(effect, dict):
        raise ValueError("effect_or_no_effect must be a dict")
    if "status" not in effect:
        raise ValueError("effect_or_no_effect missing status")
    # Authority and action hashes must be non-empty.
    if not data.get("authority_hash"):
        raise ValueError("episode missing authority_hash")
    if not data.get("action_encoding_hash"):
        raise ValueError("episode missing action_encoding_hash")


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


def _serialize_orientation(orientation: Any) -> dict[str, Any]:
    """Serialize an Orientation to a JSON-compatible dict."""
    mode = orientation.mode
    if hasattr(mode, "value"):
        mode = mode.value
    return {
        "session_ref": orientation.session_ref,
        "turn_ref": orientation.turn_ref,
        "mode": mode,
        "participant_frame": orientation.participant_frame,
        "temporal_frame": orientation.temporal_frame,
        "authority_generation": orientation.authority_generation,
        "world_revision": orientation.world_revision,
        "session_revision": orientation.session_revision,
        "episode_revision": orientation.episode_revision,
        "effect_revision": orientation.effect_revision,
        "model_identity": orientation.model_identity,
        "focus_refs": list(orientation.focus_refs),
        "obligation_refs": list(orientation.obligation_refs),
        "capability_summary": list(orientation.capability_summary),
        "permission_summary": list(orientation.permission_summary),
        "participants": list(orientation.participants),
        "active_turn_ref": orientation.active_turn_ref,
        "event_refs": list(orientation.event_refs),
        "scanned_atom_count": orientation.scanned_atom_count,
        "index_probes": list(orientation.index_probes),
        "visited_refs": list(orientation.visited_refs),
        "cache_key": orientation.cache_key,
        "source_text": getattr(orientation, "source_text", ""),
    }


def _serialize_program(program: Any) -> dict[str, Any]:
    """Serialize a SemanticSwitchProgram to a JSON-compatible dict."""
    return program.as_dict()


def _serialize_coverage_receipt(receipt: Any) -> dict[str, Any]:
    """Serialize a CoverageReceipt to a JSON-compatible dict."""
    if receipt is None:
        return {}
    return {
        "program_ref": receipt.program_ref,
        "assigned_unit_refs": list(receipt.assigned_unit_refs),
        "residual_unit_refs": list(receipt.residual_unit_refs),
        "duplicate_unit_refs": list(receipt.duplicate_unit_refs),
        "missing_unit_refs": list(receipt.missing_unit_refs),
        "critical_residuals": [
            {
                "source_unit_ref": cr.source_unit_ref,
                "contribution_kind": cr.contribution_kind,
                "reason": cr.reason,
            }
            for cr in receipt.critical_residuals
        ],
        "executable": receipt.executable,
        "coverage_hash": receipt.coverage_hash,
        "errors": [
            {"code": e.code, "detail": e.detail} for e in receipt.errors
        ],
    }


def _serialize_verification_result(verification: Any) -> dict[str, Any]:
    """Serialize a verifier VerificationResult to a JSON-compatible dict."""
    return {
        "program_ref": verification.program_ref,
        "accepted": verification.accepted,
        "well_formed": verification.well_formed,
        "errors": [
            {"code": e.code, "detail": e.detail, "action_ref": e.action_ref}
            for e in verification.errors
        ],
        "verification_hash": verification.verification_hash,
    }


def _serialize_response_meaning(response_meaning: Any) -> dict[str, Any]:
    """Serialize a ResponseMeaning to a JSON-compatible dict."""
    if response_meaning is None:
        return {}
    return response_meaning.as_dict()


def _serialize_realization_receipt(receipt: Any) -> dict[str, Any]:
    """Serialize a RealizationReceipt to a JSON-compatible dict."""
    if receipt is None:
        return {"status": "no_effect", "surface": None, "model_identity": None}
    equiv = None
    if receipt.equivalence_receipt is not None:
        equiv = {
            "equivalent": receipt.equivalence_receipt.equivalent,
            "mismatch_codes": list(receipt.equivalence_receipt.mismatch_codes),
        }
    return {
        "status": receipt.status,
        "surface": receipt.surface,
        "model_identity": receipt.model_identity,
        "semantic_content_ref": receipt.semantic_content_ref,
        "decoder_invocations": receipt.decoder_invocations,
        "equivalence_receipt": equiv,
    }


def _serialize_effect_receipt(receipt: Any) -> dict[str, Any]:
    """Serialize an EffectReceipt to a JSON-compatible dict."""
    if receipt is None:
        return {"status": "no_effect"}
    return {
        "effect_ref": receipt.effect_ref,
        "status": receipt.status,
        "world_revision": receipt.world_revision,
        "proof_refs": list(receipt.proof_refs),
        "adapter_receipt_ref": receipt.adapter_receipt_ref,
    }


def _serialize_revision_pin(pin: Any) -> dict[str, Any]:
    """Serialize a RevisionPin to a JSON-compatible dict."""
    return {
        "authority_generation": pin.authority_generation,
        "world_revision": pin.world_revision,
        "session_revision": pin.session_revision,
        "episode_revision": pin.episode_revision,
        "effect_revision": pin.effect_revision,
        "model_identity": pin.model_identity,
    }


def _serialize_gap_receipt(receipt: Any) -> dict[str, Any] | None:
    """Serialize a GapReceipt to a JSON-compatible dict."""
    if receipt is None:
        return None
    return receipt.as_dict()


class EpisodeBuilder:
    """Builds :class:`SemanticEpisode` objects from reviewed scenarios.

    The builder uses the runtime components (authority, form resolver, proposer,
    verifier, coverage verifier, and the six-phase runtime) to process each
    scenario and record the full six-phase output. Generation is deterministic:
    the same seed produces byte-identical output.

    The builder is constructed via :meth:`for_reviewed_scenarios` which wires up
    all runtime components from the project's authority data.
    """

    def __init__(
        self,
        *,
        authority: Any,
        config: Any,
        form_resolver: Any,
        projector: Any,
        verifier: Any,
        proposer: Any,
        runtime_factory: Any,
        stores: Any,
        seed: int = 1701,
    ) -> None:
        self._authority = authority
        self._config = config
        self._form_resolver = form_resolver
        self._projector = projector
        self._verifier = verifier
        self._proposer = proposer
        self._runtime_factory = runtime_factory
        self._stores = stores
        self._seed = seed

    @classmethod
    def for_reviewed_scenarios(cls, *, seed: int = 1701) -> "EpisodeBuilder":
        """Create a builder wired with the project's runtime components."""
        import sys
        from pathlib import Path as _Path

        root = _Path(__file__).resolve().parents[2]
        if str(root / "src") not in sys.path:
            sys.path.insert(0, str(root / "src"))

        from .authority import AuthorityLinker
        from .affordances import SemanticAffordanceIndex
        from .config import RuntimeConfig
        from .contributions import ContributionExpander
        from .cycle import OrientationProjector
        from .forms import FormResolver
        from .grounding import Grounder
        from .persistence import memory_stores
        from .proposal import BootstrapProposer
        from .verifier import ExactProgramVerifier, LegalActionIndex
        from .coverage import CoverageVerifier
        from .runtime import (
            FixtureEffectOwner,
            FixtureEvaluationOwner,
            FixtureRealizationOwner,
            FixtureVerificationOwner,
            HybridRuntime,
        )

        config = RuntimeConfig.release()
        authority = AuthorityLinker().link_path(
            root / "data" / "authority" / "manifest.json"
        )

        with open(
            root / "data" / "languages" / "en" / "forms.json", encoding="utf-8"
        ) as fh:
            form_pack = json.load(fh)

        form_resolver = FormResolver(form_pack, config)
        affordance_index = SemanticAffordanceIndex(authority, config)
        contribution_expander = ContributionExpander(affordance_index, config)
        coverage_verifier = CoverageVerifier(config)
        verifier = ExactProgramVerifier(authority, config, coverage_verifier)
        legal_action_index = LegalActionIndex(authority, config)

        stores = memory_stores(authority_generation=authority.generation)
        projector = OrientationProjector(authority, stores, config)

        grounder = Grounder(
            authority=authority,
            config=config,
            form_pack=form_pack,
            form_pack_hash="",
            designation_store=None,
        )

        proposer = BootstrapProposer(
            authority=authority,
            config=config,
            form_resolver=form_resolver,
            grounder=grounder,
            affordance_index=affordance_index,
            contribution_expander=contribution_expander,
            verifier=verifier,
            coverage_verifier=coverage_verifier,
            legal_action_index=legal_action_index,
        )

        def _runtime_factory(program: Any) -> Any:
            from .propositions import (
                Application,
                PropositionGraph,
                SemanticSwitchProgram,
            )
            from .runtime import FixtureProposalOwner

            owners = {
                "proposal": FixtureProposalOwner(program),
                "verification": FixtureVerificationOwner(),
                "evaluation": FixtureEvaluationOwner(),
                "effect": FixtureEffectOwner(stores),
                "realization": FixtureRealizationOwner(),
            }
            return HybridRuntime(
                config=config,
                authority=authority,
                stores=stores,
                owners=owners,
                profile="development",
            )

        return cls(
            authority=authority,
            config=config,
            form_resolver=form_resolver,
            projector=projector,
            verifier=verifier,
            proposer=proposer,
            runtime_factory=_runtime_factory,
            stores=stores,
            seed=seed,
        )

    def build_episode(self, case: ScenarioCase) -> SemanticEpisode:
        """Build a single :class:`SemanticEpisode` from a reviewed scenario."""
        from dataclasses import replace

        # Pick the first surface example as the representative surface.
        surface = case.surface_examples[0] if case.surface_examples else ""

        # Build orientation.
        orientation = self._projector.project(
            f"session:{case.scenario_ref}", surface
        )
        orientation = replace(orientation, source_text=surface)

        # Run proposer with detailed results.
        result, rejected = self._proposer.propose_detailed(orientation)

        # Pick the first accepted candidate (or None if no accepted).
        accepted_program = None
        if result.candidates:
            accepted_program = result.candidates[0]

        # Serialize legal proposals (all accepted candidates).
        legal_proposals = tuple(
            _serialize_program(p) for p in result.candidates
        )

        # Serialize rejected alternatives (bounded to first 20 for compactness).
        rejected_serialized = tuple(
            {
                "action_ids": r["action_ids"],
                "program_ref": r["program_ref"],
                "rejection_codes": r["rejection_codes"],
            }
            for r in rejected[:20]
        )

        # Build selected program, coverage, and the full six-phase output.
        if accepted_program is not None:
            selected_program = _serialize_program(accepted_program)
            verification = self._verifier.verify(accepted_program)
            coverage = _serialize_coverage_receipt(
                verification.coverage_receipt
            )
            verification_dict = _serialize_verification_result(verification)

            # Run the six-phase runtime with the accepted program.
            runtime = self._runtime_factory(accepted_program)
            process_result = runtime.process(
                f"session:{case.scenario_ref}", surface, trace=True
            )

            evaluation = {
                "status": process_result.evaluation.status,
                "output_refs": list(process_result.evaluation.output_refs),
                "rejection_codes": list(
                    process_result.evaluation.rejection_codes
                ),
            }

            effect_receipt = process_result.effect_receipt
            effect_or_no_effect = _serialize_effect_receipt(effect_receipt)

            response_meaning = _serialize_response_meaning(
                process_result.response_meaning
            )

            realization_receipt = _serialize_realization_receipt(
                process_result.realization_receipt
            )

            gap_receipt = _serialize_gap_receipt(
                process_result.gap_receipt
            )

            revisions = _serialize_revision_pin(
                process_result.final_revision_pin
            )

            action_encoding_hash = accepted_program.action_encoding_hash
        else:
            # No accepted program — the scenario produced a gap.
            selected_program = {}
            coverage = {}
            verification_dict = {}
            evaluation = {
                "status": "unsupported",
                "output_refs": [],
                "rejection_codes": [],
            }
            effect_or_no_effect = {"status": "no_effect"}
            response_meaning = {}
            realization_receipt = {
                "status": "no_effect",
                "surface": None,
                "model_identity": None,
            }
            gap_receipt = {
                "gap_ref": stable_ref(
                    "gap", {"scenario": case.scenario_ref, "kind": "proposal"}
                ),
                "kind": case.expected_gap_kind or "proposal",
                "status": "no_accepted_program",
                "source_refs": [case.scenario_ref],
                "blockers": ["no accepted candidate"],
                "missing_contract_refs": [],
                "rejected_candidate_refs": [
                    r["program_ref"] for r in rejected[:20]
                ],
                "recommended_owner": "training",
                "safe_response_action": "request_designation",
            }
            revisions = _serialize_revision_pin(
                self._stores.revision_pin()
            )
            action_encoding_hash = ""

        # Compute authority hash.
        authority_hash = stable_ref(
            "authority", {"generation": self._authority.generation}
        )

        # Build generator lineage.
        generator_lineage = {
            "seed": self._seed,
            "authority_generation": self._authority.generation,
            "proposer": "BootstrapProposer",
            "verifier": "ExactProgramVerifier",
            "surface": surface,
            "normalized_text": surface.strip().lower(),
        }

        # Build review provenance.
        review_provenance = {
            "review_status": case.review_status,
            "scenario_ref": case.scenario_ref,
            "competency_category": case.competency_category,
        }

        # Build training source provenance.
        training_source = TrainingSource(
            source_kind=TrainingSourceKind.REVIEWED_SCENARIO,
            source_ref=case.scenario_ref,
            reviewed_target_ref=None,
            independently_reverified=True,
        ).as_dict()

        # Build episode ref.
        episode_ref = stable_ref(
            "episode",
            {
                "scenario": case.scenario_ref,
                "seed": self._seed,
                "authority_generation": self._authority.generation,
            },
        )

        return SemanticEpisode(
            episode_ref=episode_ref,
            abi_version=EPISODE_ABI_VERSION,
            scenario_ref=case.scenario_ref,
            orientation=_serialize_orientation(orientation),
            legal_proposals=legal_proposals,
            rejected_proposals=rejected_serialized,
            selected_program=selected_program,
            coverage=coverage,
            evaluation=evaluation,
            effect_or_no_effect=effect_or_no_effect,
            response_meaning=response_meaning,
            realization_receipt=realization_receipt,
            authority_hash=authority_hash,
            action_encoding_hash=action_encoding_hash,
            generator_lineage=generator_lineage,
            review_provenance=review_provenance,
            gap_receipt=gap_receipt,
            revisions=revisions,
            training_source=training_source,
        )

    def build_all(self, cases: list[ScenarioCase]) -> list[SemanticEpisode]:
        """Build episodes for all scenarios deterministically.

        Episodes are returned in the same order as the input cases.
        """
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
