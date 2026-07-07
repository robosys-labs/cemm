from __future__ import annotations

import os
import sys
import time
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
os.environ["CEMM_EXPORT_PATH"] = ""

from ...learning.memory_patch_compiler import MemoryPatchCompiler
from ...learning.patch_validator import PatchValidator
from ...learning.patch_committer import PatchCommitter
from ...memory.durable_semantic_store import DurableSemanticStore
from ...types.context_kernel import ContextKernel, WorldState, UserState, TimeState, ConversationState, GoalState, MemoryState, Budget
from ...types.self_view import SelfView
from ...types.permission import Permission
from ...types.graph_patch import GraphPatch, PatchOperation


def _kernel(permission: Permission = Permission.public()) -> ContextKernel:
    return ContextKernel(
        id=uuid.uuid4().hex[:16],
        world=WorldState(),
        user=UserState(),
        time=TimeState(now=time.time(), bucket="test"),
        conversation=ConversationState(session_id=uuid.uuid4().hex[:16], turn_index=1),
        goal=GoalState(),
        memory=MemoryState(),
        permission=permission,
        budget=Budget(),
        self_view=SelfView(self_id="test"),
    )


def test_golden_teaching_persistence() -> None:
    """Teach a relation "entity_x1 rel_a entity_y1" and verify it persists."""
    compiler = MemoryPatchCompiler()
    validator = PatchValidator()
    committer = PatchCommitter()

    patch = compiler.compile(
        subject_entity_id="entity_x1",
        predicate="rel_a",
        object_value="entity_y1",
        source_id="sig_teach",
        evidence_signal_ids=["sig_teach"],
    )
    patch.operations[0].fields["relation_key"] = "rel_a"
    patch.operations[0].fields["relation_family"] = "test_relation"
    patch.operations[0].fields["object_entity_id"] = "entity_y1"

    kernel = _kernel()
    validation = validator.validate(patch, kernel)
    assert validation.accepted, f"Patch rejected: {validation.reasons}"

    result = committer.commit(patch, validation)
    assert result.status == "committed", f"Commit failed: {result.status}"

    frames = committer.get_stored_relation_frames(
        subject_entity_id="entity_x1",
    )
    assert len(frames) == 1, f"Expected 1 frame, got {len(frames)}"
    assert frames[0].relation_key == "rel_a"
    assert frames[0].object.entity_id == "entity_y1"
