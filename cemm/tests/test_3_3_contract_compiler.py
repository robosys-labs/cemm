"""Tests for 3.3 Single Contract Compiler (Phase 10)."""

from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.types.obligation_contract import (
    ObligationContract, QueryContract, WriteContract, ReactionContract,
    SafetyContract, StateContract, ActionContract, ResponseContract,
)
from cemm.types.operational_meaning import (
    OperationalMeaningFrame, OperationalEffect, MeaningArbitrationResult,
)
from cemm.types.semantic_gap import SemanticGap, GapKind
from cemm.types.semantic_ref import SemanticRef, SemanticRefKind
from cemm.types.learning_episode import LearningEpisode, EpisodeStatus
from cemm.types.obligation_graph import ObligationGraph, ObligationNode, ObligationNodeKind
from cemm.types.knowledge_strength import PromotionState
from cemm.types.state_transmutation import StateTransmutationFrame
from cemm.kernel.operational_contract_compiler import OperationalContractCompiler
from cemm.kernel.state_contract_builder import StateContractBuilder


class TestStateContract:
    def test_creation(self):
        sc = StateContract(
            state_family="affective",
            dimension="mood",
            holder_entity_ref="entity:user",
            value="happy",
            direction="set",
            modality="observed",
        )
        assert sc.state_family == "affective"
        assert sc.dimension == "mood"
        assert sc.holder_entity_ref == "entity:user"
        assert sc.requires_authorization is True

    def test_build_from_transmutations(self):
        builder = StateContractBuilder()
        frame = StateTransmutationFrame(
            transmutation_id="st1",
            source_frame_id="sf1",
            target_ref="entity:user",
            state_family="vital",
            dimension="energy",
            direction="increase",
            confidence=0.8,
        )
        sc = builder.build([frame])
        assert sc is not None
        assert sc.state_family == "vital"
        assert sc.dimension == "energy"

    def test_empty_transmutations_returns_none(self):
        builder = StateContractBuilder()
        sc = builder.build([])
        assert sc is None

    def test_provenance_fields(self):
        sc = StateContract(
            state_family="physical",
            dimension="location",
            source_frame_id="frame1",
            group_id="group1",
            branch_id="branch1",
            episode_id="ep1",
            gap_ids=("gap1",),
        )
        assert sc.source_frame_id == "frame1"
        assert sc.group_id == "group1"
        assert sc.branch_id == "branch1"
        assert sc.episode_id == "ep1"
        assert sc.gap_ids == ("gap1",)


class TestActionContract:
    def test_creation(self):
        ac = ActionContract(
            action_key="greet",
            action_type="social_act",
            actor_ref="entity:self",
            target_ref="entity:user",
        )
        assert ac.action_key == "greet"
        assert ac.actor_ref == "entity:self"
        assert ac.target_ref == "entity:user"

    def test_provenance(self):
        ac = ActionContract(
            action_key="compute",
            source_frame_id="frame1",
            group_id="group1",
            branch_id="branch1",
            gap_ids=("gap1",),
        )
        assert ac.source_frame_id == "frame1"


class TestResponseContract:
    def test_creation(self):
        rc = ResponseContract(
            primary_obligation_id="obl1",
            expected_output_acts=["inform"],
            evidence_policy="required",
        )
        assert rc.primary_obligation_id == "obl1"
        assert "inform" in rc.expected_output_acts

    def test_blocks_clarification(self):
        rc = ResponseContract(
            allow_clarification=False,
            blocked_output_acts=["question"],
        )
        assert rc.allow_clarification is False


class TestOperationalContractCompiler:
    def test_empty_frames(self):
        compiler = OperationalContractCompiler()
        contract = compiler.compile(
            frames=[],
            arbitration=MeaningArbitrationResult(),
        )
        assert contract.obligation_kind == "abstain"
        assert contract.response_mode == "abstain"

    def test_compiles_query_contract(self):
        compiler = OperationalContractCompiler()
        frame = OperationalMeaningFrame(
            frame_id="f1",
            graph_id="g1",
            group_id="grp1",
            frame_type="user_profile_query",
            target_scope="user_profile",
            query_policy="profile_dimension_lookup",
        )
        frames = [frame]
        arbitration = MeaningArbitrationResult(
            selected_frame_ids=["f1"],
        )
        contract = compiler.compile(
            frames=frames,
            arbitration=arbitration,
        )
        assert contract.primary_meaning_frame_id == "f1"
        assert contract.query_contract is not None
        assert contract.query_contract.query_kind == "profile_dimension"
        assert contract.response_contract is not None
        assert "inform" in contract.response_contract.expected_output_acts

    def test_compiles_write_contract(self):
        compiler = OperationalContractCompiler()
        frame = OperationalMeaningFrame(
            frame_id="f1",
            graph_id="g1",
            group_id="grp1",
            frame_type="profile_assertion",
            target_scope="user_profile",
            persistence_policy="patch_candidate",
        )
        frames = [frame]
        arbitration = MeaningArbitrationResult(
            selected_frame_ids=["f1"],
        )
        contract = compiler.compile(
            frames=frames,
            arbitration=arbitration,
        )
        assert contract.write_contract is not None
        assert contract.write_contract.is_writable

    def test_provenance_attached(self):
        compiler = OperationalContractCompiler()
        frames = [
            OperationalMeaningFrame(
                frame_id="f1", graph_id="g1", group_id="grp1",
                frame_type="social_act", target_scope="ephemeral_social",
            ),
        ]
        gaps = [
            SemanticGap(
                gap_id="gap1",
                branch_id="",
                group_id="grp1",
                span_ref=SemanticRef(kind=SemanticRefKind.SPAN, id="span_x", label="x"),
                language_tag="en",
                gap_kind=GapKind.LEXEME_SENSE,
            ),
        ]
        arbitration = MeaningArbitrationResult(selected_frame_ids=["f1"])
        contract = compiler.compile(
            frames=frames,
            arbitration=arbitration,
            gaps=gaps,
        )
        assert "f1" in contract.source_frame_ids
        assert "gap1" in contract.source_gap_ids

    def test_learning_contract_for_episodes(self):
        compiler = OperationalContractCompiler()
        frame = OperationalMeaningFrame(
            frame_id="f1", graph_id="g1", group_id="grp1",
            frame_type="concept_definition_query", target_scope="concept_lattice",
            query_policy="concept_definition_lookup",
        )
        episode = LearningEpisode(
            episode_id="ep1",
            context_id="ctx1",
            target_gap_ids=["gap1"],
            status=EpisodeStatus.ACTIVE,
        )
        contract = compiler.compile(
            frames=[frame],
            arbitration=MeaningArbitrationResult(selected_frame_ids=["f1"]),
            episodes=[episode],
            gaps=[
                SemanticGap(
                    gap_id="gap1", branch_id="", group_id="grp1",
                    span_ref=SemanticRef(kind=SemanticRefKind.SPAN, id="span_x", label="x"),
                    language_tag="en",
                    gap_kind=GapKind.LEXEME_SENSE,
                ),
            ],
        )
        assert "ep1" in contract.source_episode_ids
        diag = contract.diagnostics or {}
        learning_contracts = diag.get("learning_contracts", [])
        assert len(learning_contracts) >= 1

    def test_state_contract_from_transmutations(self):
        compiler = OperationalContractCompiler()
        frame = OperationalMeaningFrame(
            frame_id="f1", graph_id="g1", group_id="grp1",
            frame_type="user_state_report", target_scope="conversation_state",
        )
        transmutations = [
            StateTransmutationFrame(
                transmutation_id="st1",
                source_frame_id="sf1",
                target_ref="entity:user",
                state_family="affective",
                dimension="mood",
                direction="set",
            ),
        ]
        contract = compiler.compile(
            frames=[frame],
            arbitration=MeaningArbitrationResult(selected_frame_ids=["f1"]),
            state_transmutations=transmutations,
        )
        assert contract.state_contract is not None
        assert contract.state_contract.state_family == "affective"

    def test_response_mode_mapping(self):
        compiler = OperationalContractCompiler()
        mode_map = {
            "answer": ["inform"],
            "confirm_write": ["confirm"],
            "clarify": ["question"],
            "refuse": ["refusal"],
            "social": ["acknowledge"],
            "exit": ["farewell"],
        }
        for frame_type, target_scope in [
            ("concept_definition_query", "concept_lattice"),
            ("profile_assertion", "user_profile"),
            ("clarification_request", "conversation_state"),
            ("safety_candidate", "safety"),
            ("social_act", "ephemeral_social"),
            ("session_exit", "conversation_state"),
        ]:
            frame = OperationalMeaningFrame(
                frame_id=f"f_{frame_type}", graph_id="g1", group_id="grp1",
                frame_type=frame_type, target_scope=target_scope,
            )
            contract = compiler.compile(
                frames=[frame],
                arbitration=MeaningArbitrationResult(selected_frame_ids=[f"f_{frame_type}"]),
            )
            if contract.response_mode in mode_map:
                expected = mode_map[contract.response_mode]
                rc = contract.response_contract
                if rc is not None:
                    assert any(
                        exp in rc.expected_output_acts for exp in expected
                    ), f"mode {contract.response_mode} -> expected {expected}, got {rc.expected_output_acts}"
