from __future__ import annotations

from cemm.v350.permissions import PermissionScope, PermissionScopeEvaluator
from cemm.v350.runtime_kernel import (
    ObservationBatch,
    ObservationEnvelope,
    ObservationKind,
    RuntimeBudgetSet,
)


def test_permission_scope_is_explicit_and_monotone():
    evaluator = PermissionScopeEvaluator(
        (
            PermissionScope("conversation:a", ("team:a",)),
            PermissionScope("team:a", ("private:user:a",)),
        )
    )
    assert evaluator.can_read("public", "conversation:a")
    assert evaluator.can_read("private:user:a", "conversation:a")
    assert not evaluator.can_read("private:user:b", "conversation:a")


def test_operation_observation_batch_cannot_mix_scope():
    item = ObservationEnvelope(
        observation_ref="obs:1",
        kind=ObservationKind.OPERATION_RESULT,
        source_ref="adapter:x",
        payload_ref="operation-result:1",
        context_ref="ctx:a",
        permission_ref="conversation:a",
    )
    batch = ObservationBatch(
        batch_ref="batch:1",
        observations=(item,),
        context_ref="ctx:a",
        permission_ref="conversation:a",
        reason_refs=("operation_reentry",),
    )
    assert batch.observations[0].kind == ObservationKind.OPERATION_RESULT


def test_runtime_budgets_bound_semantic_reentry():
    budget = RuntimeBudgetSet(semantic_reentries=2, external_operations=4)
    assert budget.semantic_reentries == 2
