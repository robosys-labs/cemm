from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.synthesis.verifier import SynthesisVerifier
from cemm.types.claim import Claim, ClaimStatus
from cemm.types.context_kernel import ContextKernel
from cemm.types.permission import Permission
from cemm.types.self_view import SelfView
from cemm.types.context_kernel import (
    ContextKernel, WorldState, UserState, TimeState,
    ConversationState, GoalState, MemoryState, Budget,
)
import uuid
import time


def _kernel() -> ContextKernel:
    return ContextKernel(
        id=uuid.uuid4().hex[:16],
        world=WorldState(),
        user=UserState(),
        time=TimeState(now=time.time(), bucket="test"),
        conversation=ConversationState(
            session_id=uuid.uuid4().hex[:16], turn_index=1,
        ),
        goal=GoalState(),
        memory=MemoryState(),
        permission=Permission.public(),
        budget=Budget(),
        self_view=SelfView(self_id="test"),
    )


def test_abstain_rejects_with_selected_claims() -> None:
    """SynthesisVerifier must reject abstain outputs that still
    select claims as if they were evidence."""
    verifier = SynthesisVerifier()
    c = Claim(id="c1", subject_entity_id="e1", predicate="test", object_value="Postgres is best",
              status=ClaimStatus.ACTIVE)
    ok, issues = verifier.verify(
        "I can't answer that.",
        selected_claim_ids=["c1"],
        selected_model_ids=[],
        kernel=_kernel(),
        claims=[c],
        intent="abstain",
    )
    assert not ok, "Abstain with selected claims should fail verification"
    assert any("claim" in i.lower() for i in issues)


def test_abstain_passes_without_claims() -> None:
    """SynthesisVerifier must pass abstain outputs with no selected claims."""
    verifier = SynthesisVerifier()
    ok, issues = verifier.verify(
        "I don't have enough information.",
        selected_claim_ids=[],
        selected_model_ids=[],
        kernel=_kernel(),
        claims=[],
        intent="abstain",
    )
    assert ok, f"Abstain without claims should pass: {issues}"
