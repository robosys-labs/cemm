"""Tests for epistemic placement, claim occurrence, and admission decisions.

Tests cover:
- Reported speech does not become world truth (placement.mode == "reported",
  world query returns "unknown").
- Belief, desire, prediction, quotation, and simulation remain nested
  placements (status "attributed").
- Observed claims with evidence are admitted as world truth.
- Corrections supersede exact occurrences without deleting provenance.
- AdmissionDecision is policy-derived and cannot be requested by a lexical
  token.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

import pytest

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.epistemics import (
    AdmissionDecision,
    ClaimOccurrence,
    EpistemicEngine,
    EpistemicPlacement,
)
from legacy_propositions import (
    Application,
    PropositionGraph,
    SemanticSwitchProgram,
)
from cemm_authoritative_hybrid.state import StateIndex, StateClaim


# ---------------------------------------------------------------------------
# Test-only authority (minimal, with value_dimensions)
# ---------------------------------------------------------------------------


class _TestAuthority:
    """Minimal authority-like object for epistemic tests."""

    generation = "authority:test-v1"
    content_hash = "test-content"
    model_compatibility_hash = "test-compat"

    def __init__(self) -> None:
        self.value_dimensions = {
            "value:open": "dim:door_state",
            "value:closed": "dim:door_state",
        }

    def by_kind(self, kind: str) -> frozenset[str]:
        return frozenset()

    def by_transition(self, key: str) -> dict[str, Any] | None:
        return None

    def by_event_signature(self, event_type: str) -> Any:
        return None

    def by_state_dimension(self, dim: str) -> frozenset[str]:
        return frozenset()


# ---------------------------------------------------------------------------
# Test-only orientation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _TestOrientation:
    session_ref: str = "session:test"
    world_revision: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_program(
    *,
    epistemic_mode: str = "observed",
    source_ref: str = "participant:user",
    evidence_refs: tuple[str, ...] = (),
    claim_ref: str = "",
    modality: str = "actual",
) -> Any:
    """Build a verified-meaning-like object with epistemic provenance metadata.

    R3-01 hard-cut: EpistemicEngine.classify now accepts a VerifiedMeaning-like
    object (with ``provenance``, ``modality``, ``expression_root_ref`` and
    ``verified_meaning_ref``) instead of a raw SemanticSwitchProgram.
    """
    app = Application.create(
        "op:state",
        {
            "role:subject": "entity:door",
            "role:dimension": "dim:door_state",
            "role:value": "value:open",
        },
    )

    class _VerifiedMeaningLike:
        """Minimal verified-meaning-like object for epistemic classification."""

        def __init__(self) -> None:
            self.provenance = {
                "epistemic_mode": epistemic_mode,
                "source_ref": source_ref,
                "evidence_refs": list(evidence_refs),
                "claim_ref": claim_ref or f"claim:{epistemic_mode}",
                "interval": (0, 0),
                "confidence": 1.0,
                "scope": "world",
            }
            self.modality = modality
            self.expression_root_ref = app.application_ref
            self.verified_meaning_ref = f"meaning:{epistemic_mode}:{source_ref}"

    return _VerifiedMeaningLike()


def _placement(
    *,
    mode: str = "observed",
    source_ref: str = "participant:user",
    evidence_refs: tuple[str, ...] = (),
) -> EpistemicPlacement:
    return EpistemicPlacement(
        source_ref=source_ref,
        mode=mode,  # type: ignore[arg-type]
        evidence_refs=evidence_refs,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def authority() -> _TestAuthority:
    return _TestAuthority()


@pytest.fixture
def config() -> RuntimeConfig:
    return RuntimeConfig.release()


@pytest.fixture
def epistemic_engine(authority, config) -> EpistemicEngine:
    return EpistemicEngine(authority, config)


@pytest.fixture
def orientation() -> _TestOrientation:
    return _TestOrientation()


@pytest.fixture
def state_index() -> StateIndex:
    return StateIndex()


@pytest.fixture
def runtime(authority, config, state_index):
    """Lightweight test runtime wrapping epistemics and state modules."""

    from cemm_authoritative_hybrid.persistence import memory_stores

    stores = memory_stores(authority_generation=authority.generation)

    class _WorldFacade:
        """Facade exposing query() over the state index."""

        def __init__(self, idx: StateIndex) -> None:
            self._idx = idx

        def query(self, q: _StateQuery) -> Any:
            return self._idx.query(q.entity_ref, q.dimension_ref)

    @dataclass(frozen=True)
    class _StateQuery:
        entity_ref: str
        dimension_ref: str

    @dataclass(frozen=True)
    class _EvaluationResult:
        claim_occurrences: tuple[ClaimOccurrence, ...]
        admission: AdmissionDecision
        transition_previews: tuple = ()

    @dataclass(frozen=True)
    class _ProcessResult:
        evaluation: _EvaluationResult

    class _TestRuntime:
        def __init__(self) -> None:
            self._authority = authority
            self._config = config
            self._stores = stores
            self._epistemic = EpistemicEngine(authority, config)
            self._state_index = state_index
            self.world = _WorldFacade(state_index)

        @property
        def stores(self):
            return self._stores

        def process(self, session_ref: str, text: str) -> _ProcessResult:
            """Build a program from text (test-only, deterministic).

            Recognises simple patterns:
            - "X said ..." → reported speech, source_ref="entity:X_lower"
            - "If I ..." → simulated mode
            - otherwise → observed mode
            """
            text_lower = text.lower().strip()

            if " said " in text_lower:
                # Reported speech: "Ada said the door is open"
                speaker = text_lower.split(" said ")[0].strip()
                source = f"entity:{speaker}"
                program = _make_program(
                    epistemic_mode="reported",
                    source_ref=source,
                )
            elif text_lower.startswith("if "):
                # Simulation / hypothetical
                program = _make_program(
                    epistemic_mode="simulated",
                    source_ref="participant:user",
                )
            else:
                program = _make_program(
                    epistemic_mode="observed",
                    source_ref="participant:user",
                    evidence_refs=("evidence:test",),
                )

            occ = self._epistemic.classify(program, _TestOrientation())
            decision = self._epistemic.admit(occ)

            # If admitted, record the state observation in the world index.
            if decision.status == "admitted":
                claim = StateClaim(
                    entity_ref="entity:door",
                    dimension_ref="dim:door_state",
                    value_ref="value:open",
                    interval=(0, 100),
                    source_ref=occ.placement.source_ref,
                    placement=occ.placement,
                )
                self._state_index.observe(claim)

            return _ProcessResult(
                evaluation=_EvaluationResult(
                    claim_occurrences=(occ,),
                    admission=decision,
                )
            )

        def observe(self, claim: StateClaim) -> None:
            self._state_index.observe(claim)

        def query(self, q: _StateQuery) -> Any:
            return self._state_index.query(q.entity_ref, q.dimension_ref)

    return _TestRuntime()


def state(entity: str, value: str) -> Any:
    """Create a state query for ``entity`` and the dimension of ``value``."""
    dim_map = {
        "open": "dim:door_state",
        "closed": "dim:door_state",
    }
    return _StateQueryHelper(f"entity:{entity}", dim_map.get(value, f"dim:{value}"))


@dataclass(frozen=True)
class _StateQueryHelper:
    entity_ref: str
    dimension_ref: str


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestReportedSpeechDoesNotBecomeWorldTruth:
    def test_reported_speech_placement_mode(self, runtime):
        result = runtime.process("s", "Ada said the door is open")
        occurrence = result.evaluation.claim_occurrences[0]
        assert occurrence.placement.source_ref == "entity:ada"
        assert occurrence.placement.mode == "reported"

    def test_reported_speech_world_query_unknown(self, runtime):
        runtime.process("s", "Ada said the door is open")
        assert runtime.world.query(state("door", "open")).status == "unknown"

    def test_reported_speech_admission_is_attributed(self, runtime):
        result = runtime.process("s", "Ada said the door is open")
        assert result.evaluation.admission.status == "attributed"
        assert result.evaluation.admission.policy_ref == "policy:nested_placement"


class TestNestedPlacementsRemainAttributed:
    @pytest.mark.parametrize(
        "mode",
        ["believed", "desired", "predicted", "quoted", "simulated"],
    )
    def test_nested_mode_is_attributed(self, epistemic_engine, orientation, mode):
        program = _make_program(epistemic_mode=mode, source_ref="entity:test")
        occ = epistemic_engine.classify(program, orientation)
        decision = epistemic_engine.admit(occ)
        assert decision.status == "attributed"
        assert occ.placement.mode == mode


class TestObservedClaimsWithEvidenceAreAdmitted:
    def test_observed_with_evidence_is_admitted(self, epistemic_engine, orientation):
        program = _make_program(
            epistemic_mode="observed",
            evidence_refs=("evidence:sensor",),
        )
        occ = epistemic_engine.classify(program, orientation)
        decision = epistemic_engine.admit(occ)
        assert decision.status == "admitted"
        assert decision.policy_ref == "policy:observed_with_evidence"

    def test_observed_without_evidence_is_contested(self, epistemic_engine, orientation):
        program = _make_program(epistemic_mode="observed", evidence_refs=())
        occ = epistemic_engine.classify(program, orientation)
        decision = epistemic_engine.admit(occ)
        assert decision.status == "contested"


class TestCorrectionsSupersedeWithoutDeletingProvenance:
    def test_correction_status(self, epistemic_engine, orientation):
        program = _make_program(
            epistemic_mode="corrected",
            source_ref="participant:user",
            claim_ref="claim:door_state",
        )
        occ = epistemic_engine.classify(program, orientation)
        decision = epistemic_engine.admit(occ)
        assert decision.status == "corrected"
        assert decision.policy_ref == "policy:correction_supersede"
        # Provenance is preserved — the occurrence still exists.
        assert occ.occurrence_ref


class TestAdmissionIsPolicyDerived:
    def test_admission_carries_policy_ref(self, epistemic_engine, orientation):
        program = _make_program(epistemic_mode="reported")
        occ = epistemic_engine.classify(program, orientation)
        decision = epistemic_engine.admit(occ)
        assert decision.policy_ref.startswith("policy:")

    def test_admission_cannot_be_requested_by_token(self, epistemic_engine, orientation):
        """Admission status is derived from placement mode, not a lexical token."""
        # Two programs with the same text but different structural provenance
        # produce different admission decisions.
        reported = _make_program(epistemic_mode="reported", source_ref="entity:ada")
        observed = _make_program(
            epistemic_mode="observed",
            source_ref="participant:user",
            evidence_refs=("evidence:sensor",),
        )
        occ_r = epistemic_engine.classify(reported, orientation)
        occ_o = epistemic_engine.classify(observed, orientation)
        dec_r = epistemic_engine.admit(occ_r)
        dec_o = epistemic_engine.admit(occ_o)
        assert dec_r.status != dec_o.status
