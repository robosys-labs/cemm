import sys; sys.path.insert(0, "C:\\dev\\cemm")
import pytest
import uuid
import time
from unittest.mock import Mock, MagicMock

from cemm.types.packets import (
    GroundedGraph, MemoryPacket, InferencePacket, DecisionPacket,
    ActionPlan, RankingTraceEntry,
)

from cemm.types.context_kernel import ContextKernel, TimeState, GoalState, MemoryState, Budget, Permission as KernelPermission
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.permission import Permission
from cemm.kernel.grounding import GroundingPipeline
from cemm.kernel.entity_resolver import EntityResolver
from cemm.kernel.frame_engine import FrameEngine
from cemm.kernel.decision_router import DecisionRouter
from cemm.causal.inference import CausalInference
from cemm.store.store import Store


# ── fixtures ────────────────────────────────────────────────────


@pytest.fixture
def kernel():
    kernel = ContextKernel(
        id="test_kernel",
        self_state_id="self_main",
        time=TimeState(now=time.time()),
        goal=GoalState(required_slots=["subject"], missing_slots=["subject"]),
        memory=MemoryState(),
        budget=Budget(),
        permission=Permission.public(),
    )
    kernel.user.known = True
    kernel.conversation.session_id = "sess_1"
    return kernel



# ── canonical type instantiation ──────────────────────────────




# ── GroundingPipeline produces GroundedGraph ─────────────────




# ── CausalInference produces InferencePacket ──────────────────


def test_causal_inference_produces_inference_packet():
    store = MagicMock()
    store.models.find_by_kind.return_value = []
    ci = CausalInference(store)
    k = ContextKernel(
        id="test",
        self_state_id="self",
        time=TimeState(now=time.time()),
        budget=Budget(),
        permission=Permission.public(),
    )
    k.goal = GoalState()

    result = ci.predict("test event", [], k)
    assert isinstance(result, InferencePacket)
    assert hasattr(result, "predictions")
    assert isinstance(result.predictions, list)



# ── DecisionRouter produces canonical DecisionPacket ──────────





# ── packet schema validation ──────────────────────────────────



def test_packet_validator_rejects_bad_action_kind():
    from cemm.kernel.packet_validator import validate_packet
    dp = {"action_kind": "invalid", "version": "cemm.decision_packet.v1"}
    errs = validate_packet(dp, "decision_packet")
    assert errs, "expected validation errors for invalid action_kind"


# ── Trace packet fields ──────────────────────────────────────



# ── PipelineResult packet fields ─────────────────────────────



# ── packet IDs ────────────────────────────────────────────────




# ── training export serialization ─────────────────────────────


