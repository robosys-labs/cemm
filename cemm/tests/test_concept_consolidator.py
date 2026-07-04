"""Tests for the v4.2 ConceptConsolidator: gain scoring, state machine, staleness,
counterexample demotion, and fingerprint matching."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from cemm.learning.concept_consolidator import CONCEPT_STATES, ConceptConsolidator, ConsolidationResult
from cemm.memory.concept_lattice import ConceptLattice
from cemm.memory.construction_lattice import ConstructionLattice
from cemm.memory.episodic_trace_store import EpisodicTraceStore
from cemm.types.graph_patch import GraphPatch, PatchOperation
from cemm.types.uol_graph import UOLGraph


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def lattice() -> ConceptLattice:
    return ConceptLattice()


@pytest.fixture
def clattice() -> ConstructionLattice:
    return ConstructionLattice()


@pytest.fixture
def e_store() -> EpisodicTraceStore:
    return EpisodicTraceStore()


@pytest.fixture
def consolidator(lattice: ConceptLattice) -> ConceptConsolidator:
    return ConceptConsolidator(
        concept_lattice=lattice,
        gain_threshold=0.15,
        similarity_threshold=0.85,
        staleness_days=30,
        max_counterexamples=3,
    )


def _make_patch(
    *,
    operations: int = 1,
    target: str = "concept_lattice",
    confidence: float = 0.5,
    op_type: str = "upsert_concept_candidate",
    key: str = "test_concept",
    surface: str = "test surface",
    patch_id: str = "",
    reason: str = "test",
) -> GraphPatch:
    return GraphPatch(
        id=patch_id or f"patch_{key}",
        source_graph_id="graph:test",
        target=target,
        operations=[
            PatchOperation(
                operation=op_type,
                target_id=f"concept:{key}",
                fields={"key": key, "surface": surface},
                confidence=confidence,
                reason=reason,
            )
            for _ in range(operations)
        ],
        confidence=confidence,
        reason=reason,
    )


# ---------------------------------------------------------------------------
# Compression gain scoring
# ---------------------------------------------------------------------------

class TestGainScoring:
    def test_positive_gain(self, consolidator: ConceptConsolidator) -> None:
        patch = _make_patch(operations=5, confidence=0.9, key="high_gain")
        gain = consolidator._compute_gain_score(patch, None)
        # traces_explained = 5*0.1=0.5, prediction_gain = 0.9*0.2=0.18
        # complexity_cost = 5*0.05=0.25, contradiction_cost = 0
        # total = 0.5 + 0.18 - 0.25 = 0.43
        assert gain == pytest.approx(0.43)

    def test_negative_gain(self, consolidator: ConceptConsolidator) -> None:
        patch = _make_patch(operations=1, confidence=0.1, key="low_gain")
        gain = consolidator._compute_gain_score(patch, None)
        # traces_explained = 0.1, prediction_gain = 0.02
        # complexity_cost = 0.05, contradiction_cost = 0
        # total = 0.1 + 0.02 - 0.05 = 0.07
        assert gain == pytest.approx(0.07)

    def test_gain_with_contradiction(self, consolidator: ConceptConsolidator) -> None:
        patch = GraphPatch(
            id="patch_contra",
            source_graph_id="graph:t",
            target="concept_lattice",
            operations=[
                PatchOperation(
                    operation="upsert_concept_candidate",
                    target_id="concept:c1",
                    fields={"key": "c1", "surface": "contra", "contradiction_count": 2},
                    confidence=0.8,
                )
            ],
            confidence=0.8,
            reason="contradiction_test",
        )
        gain = consolidator._compute_gain_score(patch, None)
        # traces_explained = 0.1, prediction_gain = 0.16
        # complexity_cost = 0.05, contradiction_cost = 2*0.3 = 0.6
        # total = 0.1 + 0.16 - 0.05 - 0.6 = -0.39
        assert gain == pytest.approx(-0.39)

    def test_gain_threshold_filters_low_gain(self, consolidator: ConceptConsolidator) -> None:
        patch = _make_patch(operations=1, confidence=0.8, key="below_threshold")
        # Only 1 op with no contradiction: gain = 0.1 + 0.16 - 0.05 = 0.21
        # That's actually above 0.15 threshold... use contradiction to make it low
        patch.operations[0].fields["contradiction_count"] = 2
        result = consolidator.consolidate([patch])
        assert patch.id in result.rejected_patch_ids
        assert "gain_below_threshold" in result.reasons[patch.id]

    def test_gain_threshold_accepts_high_gain(self, consolidator: ConceptConsolidator, lattice: ConceptLattice) -> None:
        patch = _make_patch(operations=5, confidence=0.9, key="above_threshold")
        result = consolidator.consolidate([patch])
        assert patch.id in result.accepted_patch_ids


# ---------------------------------------------------------------------------
# State machine lifecycle (candidate → typed → operational → consolidated)
# ---------------------------------------------------------------------------

class TestStateMachine:
    def test_initial_state_is_candidate(self, consolidator: ConceptConsolidator) -> None:
        patch = _make_patch(operations=3, confidence=0.8, key="init_state")
        consolidator.consolidate([patch])
        assert consolidator._concept_states.get("concept:init_state") == "candidate_atom"

    def test_advance_state_forward(self, consolidator: ConceptConsolidator) -> None:
        cid = "concept:advance"
        state = consolidator._advance_state(cid, "typed_candidate")
        assert state == "typed_candidate"
        assert consolidator._concept_states[cid] == "typed_candidate"

    def test_full_progression(self, consolidator: ConceptConsolidator) -> None:
        cid = "concept:progression"
        s1 = consolidator._advance_state(cid, "candidate_atom")
        assert s1 == "candidate_atom"
        s2 = consolidator._advance_state(cid, "typed_candidate")
        assert s2 == "typed_candidate"
        s3 = consolidator._advance_state(cid, "operational_atom")
        assert s3 == "operational_atom"
        s4 = consolidator._advance_state(cid, "consolidated_atom")
        assert s4 == "consolidated_atom"

    def test_advance_state_does_not_regress(self, consolidator: ConceptConsolidator) -> None:
        cid = "concept:no_regress"
        consolidator._advance_state(cid, "operational_atom")
        s = consolidator._advance_state(cid, "candidate_atom")
        assert s == "operational_atom"

    def test_demote_state(self, consolidator: ConceptConsolidator) -> None:
        cid = "concept:demote_me"
        consolidator._advance_state(cid, "operational_atom")
        demoted = consolidator._demote_state(cid)
        assert demoted == "typed_candidate"

    def test_demote_candidate_stays_candidate(self, consolidator: ConceptConsolidator) -> None:
        cid = "concept:demote_candidate"
        consolidator._advance_state(cid, "candidate_atom")
        demoted = consolidator._demote_state(cid)
        assert demoted == "candidate_atom"

    def test_state_changes_in_result(self, consolidator: ConceptConsolidator) -> None:
        patch = _make_patch(operations=3, confidence=0.9, key="state_change_result")
        result = consolidator.consolidate([patch])
        cid = "concept:state_change_result"
        # First consolidation sets state to candidate, no change entry
        assert cid not in result.concept_state_changes
        assert consolidator._concept_states[cid] == "candidate_atom"

    def test_state_advances_on_second_consolidation(self, consolidator: ConceptConsolidator) -> None:
        cid = "concept:advance_twice"
        p1 = _make_patch(operations=3, confidence=0.9, key="advance_twice")
        consolidator.consolidate([p1])
        assert consolidator._concept_states[cid] == "candidate_atom"
        p2 = _make_patch(operations=3, confidence=0.9, key="advance_twice", patch_id="patch_adv_twice_2")
        result = consolidator.consolidate([p2])
        assert consolidator._concept_states[cid] == "typed_candidate"
        assert cid in result.concept_state_changes
        assert result.concept_state_changes[cid] == "typed_candidate"


# ---------------------------------------------------------------------------
# Staleness / decay eviction
# ---------------------------------------------------------------------------

class TestStaleness:
    def test_no_stale_within_window(self, consolidator: ConceptConsolidator) -> None:
        cid = "concept:fresh"
        consolidator._staleness_tracker[cid] = datetime.now(timezone.utc)
        stale = consolidator._check_staleness()
        assert cid not in stale

    def test_stale_beyond_window(self, consolidator: ConceptConsolidator) -> None:
        cid = "concept:stale_one"
        consolidator._staleness_tracker[cid] = datetime.now(timezone.utc) - timedelta(days=31)
        stale = consolidator._check_staleness()
        assert cid in stale

    def test_eviction_removes_stale(self, consolidator: ConceptConsolidator) -> None:
        cid = "concept:evict_me"
        consolidator._staleness_tracker[cid] = datetime.now(timezone.utc) - timedelta(days=31)
        consolidator._concept_states[cid] = "typed"
        consolidator._concept_fingerprints[cid] = {"test"}
        patch = _make_patch(operations=1, confidence=0.1, key="evict_trigger")
        result = consolidator.consolidate([patch])
        assert cid in result.evicted_concept_ids
        assert cid not in consolidator._staleness_tracker
        assert cid not in consolidator._concept_states

    def test_custom_staleness_days(self, lattice: ConceptLattice) -> None:
        c = ConceptConsolidator(lattice, staleness_days=1)
        cid = "concept:custom_stale"
        c._staleness_tracker[cid] = datetime.now(timezone.utc) - timedelta(hours=25)
        stale = c._check_staleness()
        assert cid in stale


# ---------------------------------------------------------------------------
# Counterexample demotion
# ---------------------------------------------------------------------------

class TestCounterexamples:
    def test_counterexample_demotes_at_limit(self, consolidator: ConceptConsolidator) -> None:
        cid = "concept:counter_demote"
        consolidator._advance_state(cid, "operational_atom")
        patch = GraphPatch(
            id="patch_counter",
            source_graph_id="graph:t",
            target="concept_lattice",
            operations=[PatchOperation(operation="mark_counterexample", fields={})],
            confidence=0.5,
            reason="counter_test",
        )
        for _ in range(3):
            consolidator._track_counterexample(patch, cid)
        assert consolidator._counterexample_tracker[cid] >= 3
        assert consolidator._concept_states[cid] == "typed_candidate"

    def test_counterexample_accumulates_correctly(self, consolidator: ConceptConsolidator) -> None:
        cid = "concept:counter_accum"
        patch = GraphPatch(
            id="patch_counter_acc",
            source_graph_id="graph:t",
            target="concept_lattice",
            operations=[PatchOperation(operation="mark_counterexample", fields={})],
            confidence=0.5,
            reason="counter_acc",
        )
        consolidator._track_counterexample(patch, cid)
        assert consolidator._counterexample_tracker[cid] == 1
        consolidator._track_counterexample(patch, cid)
        assert consolidator._counterexample_tracker[cid] == 2

    def test_no_demote_below_limit(self, consolidator: ConceptConsolidator) -> None:
        cid = "concept:no_demote_yet"
        consolidator._advance_state(cid, "operational_atom")
        patch = GraphPatch(
            id="patch_no_demote",
            source_graph_id="graph:t",
            target="concept_lattice",
            operations=[PatchOperation(operation="mark_counterexample", fields={})],
            confidence=0.5,
            reason="no_demote",
        )
        consolidator._track_counterexample(patch, cid)
        assert consolidator._concept_states[cid] == "operational_atom"


# ---------------------------------------------------------------------------
# Fingerprint nearest-neighbor matching
# ---------------------------------------------------------------------------

class TestFingerprintMatching:
    def test_compute_fingerprint(self, consolidator: ConceptConsolidator) -> None:
        fp = consolidator._compute_fingerprint("concept:president", "President of the USA", {"leader", "head"})
        assert "president" in fp
        assert "usa" in fp
        assert "leader" in fp

    def test_fingerprint_similarity_exact(self, consolidator: ConceptConsolidator) -> None:
        fp1 = {"president", "usa", "leader"}
        fp2 = {"president", "usa", "leader"}
        sim = consolidator._fingerprint_similarity(fp1, fp2)
        assert sim == pytest.approx(1.0)

    def test_fingerprint_similarity_partial(self, consolidator: ConceptConsolidator) -> None:
        fp1 = {"president", "usa", "leader"}
        fp2 = {"president", "usa", "white", "house"}
        sim = consolidator._fingerprint_similarity(fp1, fp2)
        assert sim == pytest.approx(2 / 5)  # intersection=2, union=5

    def test_fingerprint_similarity_no_match(self, consolidator: ConceptConsolidator) -> None:
        fp1 = {"cat", "feline"}
        fp2 = {"dog", "canine"}
        sim = consolidator._fingerprint_similarity(fp1, fp2)
        assert sim == pytest.approx(0.0)

    def test_fingerprint_similarity_empty(self, consolidator: ConceptConsolidator) -> None:
        assert consolidator._fingerprint_similarity(set(), {"a"}) == 0.0
        assert consolidator._fingerprint_similarity({"a"}, set()) == 0.0
        assert consolidator._fingerprint_similarity(set(), set()) == 0.0

    def test_find_nearest_match(self, consolidator: ConceptConsolidator) -> None:
        c = ConceptConsolidator(
            consolidator._concept_lattice,
            similarity_threshold=0.4,
        )
        existing = {
            "concept:president": {"president", "usa", "leader"},
            "concept:dog": {"dog", "canine", "pet"},
        }
        fp = {"president", "usa", "commander"}
        match = c._find_nearest_match(fp, existing)
        assert match == "concept:president"

    def test_find_nearest_match_below_threshold(self, consolidator: ConceptConsolidator) -> None:
        existing = {
            "concept:president": {"president", "usa", "leader"},
        }
        fp = {"cat", "feline", "pet"}
        match = consolidator._find_nearest_match(fp, existing)
        assert match is None

    def test_find_nearest_match_empty(self, consolidator: ConceptConsolidator) -> None:
        match = consolidator._find_nearest_match({"test"}, {})
        assert match is None


# ---------------------------------------------------------------------------
# Integration: full consolidation pipeline
# ---------------------------------------------------------------------------

class TestFullPipeline:
    def test_accept_high_gain_patch(self, consolidator: ConceptConsolidator) -> None:
        patch = _make_patch(operations=5, confidence=0.9, key="full_pipeline")
        result = consolidator.consolidate([patch])
        assert patch.id in result.accepted_patch_ids
        assert result.gain_scores[patch.id] == pytest.approx(0.43)

    def test_reject_low_confidence_patch(self, consolidator: ConceptConsolidator) -> None:
        patch = _make_patch(operations=1, confidence=0.1, key="low_conf")
        result = consolidator.consolidate([patch])
        assert patch.id in result.rejected_patch_ids

    def test_empty_patches(self, consolidator: ConceptConsolidator) -> None:
        result = consolidator.consolidate([])
        assert len(result.accepted_patch_ids) == 0
        assert len(result.rejected_patch_ids) == 0

    def test_episodic_trace_target(self, consolidator: ConceptConsolidator, e_store: EpisodicTraceStore) -> None:
        c = ConceptConsolidator(
            consolidator._concept_lattice,
            episodic_store=e_store,
            gain_threshold=-1.0,
        )
        graph = UOLGraph(id="g_test", raw_text="hello")
        patch = GraphPatch(
            id="patch_epi",
            source_graph_id="g_test",
            target="episodic_trace",
            operations=[
                PatchOperation(operation="retain_exemplar", target_id="trace:g_test", confidence=0.5)
            ],
            confidence=0.5,
            reason="epi_test",
        )
        result = c.consolidate([patch], source_graph=graph)
        assert patch.id in result.accepted_patch_ids
        assert "trace:g_test" in result.applied_targets

    def test_construction_lattice_target(self, consolidator: ConceptConsolidator, clattice: ConstructionLattice) -> None:
        c = ConceptConsolidator(
            consolidator._concept_lattice,
            construction_lattice=clattice,
            gain_threshold=-1.0,
        )
        patch = GraphPatch(
            id="patch_cx",
            source_graph_id="graph:t",
            target="construction_lattice",
            operations=[
                PatchOperation(
                    operation="observe_construction_match",
                    target_id="construction:test_cx",
                    fields={"construction_key": "test_cx", "group_type": "teaching"},
                    confidence=0.6,
                )
            ],
            confidence=0.6,
            reason="cx_test",
        )
        result = c.consolidate([patch])
        assert patch.id in result.accepted_patch_ids

    def test_patch_merging(self, consolidator: ConceptConsolidator) -> None:
        p1 = GraphPatch(
            id="patch_merge_a",
            source_graph_id="graph:t",
            target="concept_lattice",
            operations=[
                PatchOperation(operation="upsert_concept_candidate", target_id="concept:a", fields={"key": "a"}),
                PatchOperation(operation="upsert_concept_candidate", target_id="concept:b", fields={"key": "b"}),
            ],
            confidence=0.8,
            reason="test",
        )
        p2 = GraphPatch(
            id="patch_merge_b",
            source_graph_id="graph:t",
            target="concept_lattice",
            operations=[
                PatchOperation(operation="upsert_concept_candidate", target_id="concept:c", fields={"key": "c"}),
            ],
            confidence=0.7,
            reason="test",
        )
        merged = consolidator._merge_compatible_patches([p1, p2])
        assert len(merged) == 1
        assert len(merged[0].operations) == 3  # all 3 unique operations merged


# ---------------------------------------------------------------------------
# Snapshot
# ---------------------------------------------------------------------------

class TestSnapshot:
    def test_snapshot_includes_new_fields(self, consolidator: ConceptConsolidator) -> None:
        cid = "concept:snapshot_test"
        consolidator._concept_states[cid] = "operational"
        consolidator._concept_fingerprints[cid] = {"test"}
        consolidator._staleness_tracker[cid] = datetime.now(timezone.utc)
        consolidator._counterexample_tracker[cid] = 1
        snap = consolidator.snapshot()
        assert "concept_states" in snap
        assert "concept_fingerprints" in snap
        assert "staleness_tracker" in snap
        assert "counterexample_tracker" in snap
        assert "config" in snap
        assert snap["concept_states"][cid] == "operational"
        assert snap["config"]["gain_threshold"] == 0.15
        assert snap["config"]["similarity_threshold"] == 0.85

    def test_snapshot_construction_lattice_none(self, lattice: ConceptLattice) -> None:
        c = ConceptConsolidator(lattice)
        snap = c.snapshot()
        assert snap["construction_lattice"] == {}
