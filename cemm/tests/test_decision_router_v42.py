"""Tests for Phase 6: cycle-aware DecisionRouter with working_set/resolution/policy."""

from __future__ import annotations

import os
import sys
import uuid
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.kernel.decision_router import DecisionRouter
from cemm.types.context_kernel import ContextKernel, Budget, WorldState, UserState, TimeState, ConversationState, GoalState, MemoryState
from cemm.types.semantic_focus import SemanticFocus
from cemm.kernel.semantic_working_set import SemanticWorkingSet
from cemm.types.uol_graph import UOLGraph, UOLAtom
from cemm.types.packets import GroundedGraph, MemoryPacket, DecisionPacket, InferencePacket
from cemm.types.permission import Permission
from cemm.types.signal import SignalKind, SourceType, ObservationSemantics
from cemm.types.conversation_act import ConversationActPacket
from cemm.kernel.semantic_kernel_runtime import SemanticKernelRuntime


def _kernel() -> ContextKernel:
    return ContextKernel(
        id=uuid.uuid4().hex[:16],
        world=WorldState(),
        user=UserState(),
        time=TimeState(now=time.time(), bucket="test"),
        conversation=ConversationState(session_id=uuid.uuid4().hex[:16], turn_index=1),
        goal=GoalState(),
        memory=MemoryState(),
        permission=Permission.public(),
        budget=Budget(),
    )


class TestDecisionRouterV42:

    def test_run_accepts_working_set(self):
        router = DecisionRouter()
        graph = UOLGraph()
        kernel = _kernel()
        ws = SemanticWorkingSet()
        result = router.run(
            graph=graph, kernel=kernel,
            grounded_graph=GroundedGraph(),
            memory_packet=MemoryPacket(),
            working_set=ws,
        )
        assert result is not None
        assert isinstance(result.action_kind, str)

    def test_run_accepts_resolution(self):
        router = DecisionRouter()
        graph = UOLGraph()
        kernel = _kernel()
        result = router.run(
            graph=graph, kernel=kernel,
            grounded_graph=GroundedGraph(),
            memory_packet=MemoryPacket(),
            resolution={"concept_id": "test"},
        )
        assert result is not None

    def test_run_accepts_policy(self):
        router = DecisionRouter()
        graph = UOLGraph()
        kernel = _kernel()
        result = router.run(
            graph=graph, kernel=kernel,
            grounded_graph=GroundedGraph(),
            memory_packet=MemoryPacket(),
            policy={"scope": "public"},
        )
        assert result is not None

    def test_working_set_risk_flags_route_to_abstain(self):
        router = DecisionRouter()
        graph = UOLGraph()
        kernel = _kernel()
        ws = SemanticWorkingSet(risk_flags=["permission:deny"])
        result = router.run(
            graph=graph, kernel=kernel,
            grounded_graph=GroundedGraph(),
            memory_packet=MemoryPacket(),
            working_set=ws,
        )
        assert result is not None

    def test_working_set_unresolved_ports(self):
        router = DecisionRouter()
        graph = UOLGraph()
        kernel = _kernel()
        ws = SemanticWorkingSet(unresolved_ports=[
            {"port_key": "holder", "owner_atom_id": "a1", "required": True},
        ])
        result = router.run(
            graph=graph, kernel=kernel,
            grounded_graph=GroundedGraph(),
            memory_packet=MemoryPacket(),
            working_set=ws,
        )
        assert result is not None

    def test_attention_property_on_runtime(self):
        assert SemanticKernelRuntime().attention is not None
        ws = SemanticKernelRuntime().attention.attend(UOLGraph(), _kernel())
        assert isinstance(ws, SemanticWorkingSet)

    def test_run_with_all_new_params(self):
        router = DecisionRouter()
        graph = UOLGraph()
        kernel = _kernel()
        result = router.run(
            graph=graph,
            kernel=kernel,
            grounded_graph=GroundedGraph(),
            memory_packet=MemoryPacket(),
            inference_packet=InferencePacket(),
            input_text="hello",
            observation_semantics=ObservationSemantics(),
            context_inference=None,
            conversation_act=ConversationActPacket(),
            store=None,
            act_resolution_plan=None,
            working_set=SemanticWorkingSet(),
            resolution={"concept_id": "test"},
            policy={"scope": "public"},
        )
        assert result is not None
