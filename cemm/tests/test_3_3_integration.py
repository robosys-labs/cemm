"""Integration tests for CEMM 3.3 Phases 0-5 foundation.
Tests interaction between new types, indexes, gap detection, 
interpretation lattice, and learning episode components.
"""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.types.semantic_ref import SemanticRef, SemanticRefKind, RoleRef
from cemm.types.semantic_authority import AuthorityState, AuthorityRecord
from cemm.types.provenance import ProvenanceEnvelope, ProvenanceScope
from cemm.types.semantic_gap import SemanticGap, GapKind
from cemm.types.knowledge_strength import KnowledgeStrength, compute_knowledge_strength, PromotionState
from cemm.types.learning_evidence import LearningEvidenceEvent, EvidenceKind, EvidenceStance, LearningUseOutcome, UseOutcomeKind
from cemm.types.learning_hypothesis import LearningHypothesis, HypothesisTargetKind
from cemm.types.learning_episode import LearningEpisode, EpisodeStatus, LearningObligation, QuestionActKind
from cemm.types.learning_contract import LearningContract
from cemm.types.context_signature import ContextSignature
from cemm.types.lexical_semantic_candidate import LexicalSemanticCandidate
from cemm.kernel.turn_semantic_index import TurnSemanticIndex
from cemm.kernel.interpretation_lattice import InterpretationBranch, InterpretationLattice
from cemm.kernel.branch_arbitrator import BranchArbitrator
from cemm.kernel.interpretation_resolver import InterpretationResolver
from cemm.kernel.predicate_activation_resolver import PredicateActivationResolver, PredicateActivationFrame, PredicateStatus
from cemm.kernel.role_ref_resolver import RoleRefResolver
from cemm.kernel.entity_grounding_resolver import EntityGroundingResolver, EntityGroundingStatus
from cemm.learning.semantic_gap_detector import SemanticGapDetector
from cemm.learning.learning_episode_manager import LearningEpisodeManager
from cemm.learning.learning_question_planner import LearningQuestionPlanner
from cemm.learning.learning_answer_assimilator import LearningAnswerAssimilator
from cemm.kernel.learning_contract_builder import LearningContractBuilder


class TestSemanticAuthority:
    def test_authority_progression(self):
        rec = AuthorityRecord(artifact_ref="entity:test")
        rec2 = rec.transition_to(AuthorityState.CANDIDATE, "found in text")
        assert rec2.current_state == AuthorityState.CANDIDATE
        assert rec.current_state == AuthorityState.OBSERVED  # immutable

    def test_invalid_transition_raises(self):
        import pytest
        rec = AuthorityRecord(artifact_ref="entity:test", current_state=AuthorityState.COMMITTED)
        with pytest.raises(ValueError):
            rec.transition_to(AuthorityState.CANDIDATE)

    def test_terminal_transition_is_final(self):
        assert AuthorityState.COMMITTED.is_terminal()
        assert not AuthorityState.CANDIDATE.is_terminal()


class TestSemanticGap:
    def test_gap_creation(self):
        ref = SemanticRef(kind=SemanticRefKind.SPAN, id="span_1")
        gap = SemanticGap(
            gap_id="gap_1",
            branch_id="branch_1",
            group_id="group_1",
            span_ref=ref,
            language_tag="en",
            gap_kind=GapKind.LEXEME_SENSE,
            surface_form="zibble",
            entropy=0.9,
        )
        assert gap.gap_kind == GapKind.LEXEME_SENSE
        assert not gap.is_blocking
        # Gap with no required_fields is vacuously fully resolved
        assert gap.is_fully_resolved

    def test_gap_resolved_field(self):
        ref = SemanticRef(kind=SemanticRefKind.SPAN, id="span_1")
        gap = SemanticGap(
            gap_id="gap_2",
            branch_id="branch_1",
            group_id="group_1",
            span_ref=ref,
            language_tag="en",
            gap_kind=GapKind.LEXEME_SENSE,
            required_fields=("sense", "kind"),
        )
        gap2 = gap.with_resolved_field("sense", "quick_movement")
        assert not gap2.is_fully_resolved  # "kind" still missing

    def test_all_gap_kinds(self):
        assert len(GapKind) == 18


class TestKnowledgeStrength:
    def test_compute_from_counts(self):
        ks = compute_knowledge_strength(support_events=5, independent_sources=3)
        assert ks.semantic_confidence > 0.5
        assert ks.promotion_state == PromotionState.OBSERVED_CANDIDATE

    def test_contested_state(self):
        ks = KnowledgeStrength(support_mass=0.3, contradiction_mass=0.8)
        assert ks.is_contested
        assert not ks.is_promotable

    def test_direct_knowledge_strength(self):
        ks = KnowledgeStrength(
            semantic_confidence=0.8,
            source_trust=0.7,
            support_mass=0.9,
            source_diversity=0.6,
            stability=0.8,
        )
        assert ks.is_promotable


class TestSemanticRef:
    def test_ref_creation(self):
        ref = SemanticRef(kind=SemanticRefKind.ENTITY, id="user_123")
        assert str(ref) == "entity:user_123"

    def test_ref_from_string(self):
        ref = SemanticRef.from_string("entity:user_123")
        assert ref.kind == SemanticRefKind.ENTITY
        assert ref.id == "user_123"

    def test_role_ref_placeholder(self):
        role = RoleRef(role_kind="actor", is_placeholder=True)
        assert not role.is_resolved()


class TestLearningEpisode:
    def test_episode_lifecycle(self):
        mgr = LearningEpisodeManager()
        ref = SemanticRef(kind=SemanticRefKind.SPAN, id="span_1")
        gap = SemanticGap(gap_id="gap_1", branch_id="b1", group_id="g1", span_ref=ref, language_tag="en", gap_kind=GapKind.LEXEME_SENSE)
        episode = mgr.create_episode(context_id="ctx_1", gaps=[gap])
        assert episode.is_active
        assert not episode.is_terminated

        mgr.update_episode_status(episode.episode_id, EpisodeStatus.CONSOLIDATED)
        ep = mgr.get_episode(episode.episode_id)
        assert ep is not None
        assert ep.status == EpisodeStatus.CONSOLIDATED

    def test_question_tracking(self):
        mgr = LearningEpisodeManager()
        ref = SemanticRef(kind=SemanticRefKind.SPAN, id="span_1")
        gap = SemanticGap(gap_id="gap_2", branch_id="b1", group_id="g1", span_ref=ref, language_tag="en", gap_kind=GapKind.LEXEME_SENSE)
        episode = mgr.create_episode(context_id="ctx_2", gaps=[gap])
        mgr.mark_question_asked(episode.episode_id, "sense")
        assert mgr.has_question_been_asked(episode.episode_id, "sense")
        assert not mgr.has_question_been_asked(episode.episode_id, "kind")


class TestInterpretationLattice:
    def test_branch_scoring(self):
        branch = InterpretationBranch(
            branch_id="b1",
            group_id="g1",
            coherence_score=0.8,
            type_compatibility=0.7,
            context_support=0.6,
            provenance_strength=0.5,
        )
        assert branch.total_score > 0.6

    def test_lattice_add_branch(self):
        lattice = InterpretationLattice()
        branch = InterpretationBranch(branch_id="b1", group_id="g1")
        lattice.add_branch(branch)
        assert lattice.get_branch("b1") is not None
        assert lattice.top_branch() is not None

    def test_lattice_viable_branches(self):
        lattice = InterpretationLattice()
        # Low-scoring branch without gaps is not viable
        low = InterpretationBranch(branch_id="low", group_id="g1", coherence_score=0.1, type_compatibility=0.1)
        lattice.add_branch(low)
        assert len(lattice.viable_branches()) == 0

    def test_branch_with_gaps_is_viable(self):
        lattice = InterpretationLattice()
        low_with_gaps = InterpretationBranch(
            branch_id="gappy", group_id="g1", 
            coherence_score=0.1, type_compatibility=0.1,
            gap_ids=("gap_1",),
        )
        lattice.add_branch(low_with_gaps)
        assert len(lattice.viable_branches()) == 1


class TestPredicateActivation:
    def test_activation_requires_valid_ports(self):
        frame = PredicateActivationFrame(
            predicate_id="p1",
            group_id="g1",
            predicate_key="eat",
            predicate_surface="eat",
            scope="asserted",
            actor_ref="entity:user",
            target_ref="entity:food",
        )
        assert frame.is_activatable({"actor", "target"})
        activated = frame.activate()
        assert activated.status == PredicateStatus.ACTIVATED

    def test_quoted_predicate_not_activated(self):
        frame = PredicateActivationFrame(
            predicate_id="p2",
            group_id="g1",
            predicate_key="kill",
            predicate_surface="kill",
            scope="quoted",
        )
        assert not frame.is_activatable()

    def test_resolver_filters_invalid(self):
        resolver = PredicateActivationResolver()
        valid = PredicateActivationFrame(predicate_id="p1", group_id="g1", predicate_key="eat", predicate_surface="eat", scope="asserted", actor_ref="user", target_ref="food")
        quoted = PredicateActivationFrame(predicate_id="p2", group_id="g1", predicate_key="kill", predicate_surface="kill", scope="quoted")
        activated = resolver.resolve([valid, quoted], {"user", "food"})
        assert len(activated) == 1
        assert activated[0].predicate_key == "eat"

    def test_negated_is_not_activatable(self):
        frame = PredicateActivationFrame(predicate_id="p3", group_id="g1", predicate_key="run", predicate_surface="run", scope="negated")
        assert not frame.is_activatable()


class TestRoleRefResolution:
    def test_resolved_role(self):
        resolver = RoleRefResolver()
        resolved = resolver.resolve({"actor": "entity:user"}, {"entity:user": {"name": "user"}})
        assert resolved["actor"][1] is True

    def test_unresolved_role(self):
        resolver = RoleRefResolver()
        resolved = resolver.resolve({"actor": "entity:unknown"}, {"entity:user": {"name": "user"}})
        assert resolved["actor"][1] is False
        assert resolved["actor"][0] == ""


class TestEntityGrounding:
    def test_unresolved_entity(self):
        resolver = EntityGroundingResolver()
        entity_id, status = resolver.resolve("zorp", "unknown", {}, {})
        assert status == EntityGroundingStatus.UNRESOLVED_REFERENCE
        assert entity_id is None

    def test_known_entity(self):
        resolver = EntityGroundingResolver()
        entity_id, status = resolver.resolve("user", "person", {"user": {"surface": "user"}}, {"user": 0.9})
        assert status == EntityGroundingStatus.RESOLVED_ENTITY


class TestLearningContract:
    def test_contract_creation(self):
        contract = LearningContract(
            contract_id="lc_1",
            episode_id="ep_1",
            target_hypothesis_ids=("hyp_1",),
            activation_scope="session",
            promotion_ceiling=PromotionState.SESSION_PROVISIONAL,
        )
        assert contract.permits_operation("propose_binding")
        assert contract.prohibits_authority("tool_execution")
        assert not contract.can_promote_to_durable

    def test_build_from_episode(self):
        builder = LearningContractBuilder()
        ref = SemanticRef(kind=SemanticRefKind.SPAN, id="s1")
        gap = SemanticGap(gap_id="g1", branch_id="b1", group_id="g1", span_ref=ref, language_tag="en", gap_kind=GapKind.LEXEME_SENSE)
        mgr = LearningEpisodeManager()
        episode = mgr.create_episode(context_id="ctx_1", gaps=[gap])
        contract = builder.build(episode)
        assert contract.episode_id == episode.episode_id
        assert contract.activation_scope == "session"


class TestLearningQuestionPlanner:
    def test_planner_selects_blocking_gap(self):
        planner = LearningQuestionPlanner()
        ref = SemanticRef(kind=SemanticRefKind.SPAN, id="s1")
        blocking_gap = SemanticGap(gap_id="g_block", branch_id="b1", group_id="g1", span_ref=ref, language_tag="en", gap_kind=GapKind.LEXEME_SENSE, blocking_artifact_ids=("obl_1",))
        nonblocking = SemanticGap(gap_id="g_nb", branch_id="b1", group_id="g1", span_ref=ref, language_tag="en", gap_kind=GapKind.TEMPORAL_ANCHOR)
        result = planner.plan([blocking_gap, nonblocking], [], set(), {"g_block"})
        assert result is not None
        assert "g_block" in result.gap_ids

    def test_no_question_when_all_asked(self):
        planner = LearningQuestionPlanner()
        ref = SemanticRef(kind=SemanticRefKind.SPAN, id="s1")
        gap = SemanticGap(gap_id="g1", branch_id="b1", group_id="g1", span_ref=ref, language_tag="en", gap_kind=GapKind.LEXEME_SENSE)
        result = planner.plan([gap], [], {"g1"}, set())
        assert result is None


class TestSemanticGapDetector:
    def test_detector_empty_no_gaps(self):
        detector = SemanticGapDetector()
        # Using a minimal class to simulate a percept with no unknowns
        class FakePercept:
            unknown_tokens = []
            normalized_forms = {}
            language = "en"
            semantic_gaps = []
            meaning_groups = []
        
        gaps = detector.detect(FakePercept())
        assert len(gaps) == 0


# Run if called directly
if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
