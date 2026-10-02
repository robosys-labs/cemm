"""The predecessor generic-acquisition coordinator cannot publish live authority."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.learning import (
    LearningCoordinator,
    LearningGap,
    ReviewerPolicyIssuer,
)
from cemm_authoritative_hybrid.persistence import memory_stores
from cemm_authoritative_hybrid.query import QueryEngine


__cemm_test_inventory__ = {
    "tests/test_foundation_generic_acquisition_boundary.py::test_predecessor_generic_acquisition_cannot_mutate_live_authority": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:foundation-predecessor-generic-acquisition-cannot-mutate-live-authority",
        "diagnostic_role": "owner",
        "introduced_by_task": "Foundation-Task-6",
        "owner_ref": "learning-response",
        "source_ast_sha256": "cef9fdfb89e0180c4dc10f79ddf70d189e1ea9f7084580abadf928448addcb29",
    },
}


@dataclass(frozen=True)
class _VerifiedProgramWitness:
    program_ref: str = "program:reviewed-acquisition-witness"


def test_predecessor_generic_acquisition_cannot_mutate_live_authority(
    linked_authority,
) -> None:
    stores = memory_stores(authority_generation=linked_authority.generation)
    try:
        linked_authority.capabilities = {
            **linked_authority.capabilities,
            "participant:user": ["cap:learn"],
        }
        coordinator = LearningCoordinator(
            linked_authority,
            stores,
            RuntimeConfig.release(),
            QueryEngine(linked_authority, stores, RuntimeConfig.release()),
        )
        issuer = ReviewerPolicyIssuer("policy:acquisition", "reviewer:test")
        plan = coordinator.plan_reviewed_acquisition(
            (_VerifiedProgramWitness(),), "rule"
        )
        before = linked_authority.rule_generation_snapshot()

        with pytest.raises(
            LearningGap, match="reviewed_acquisition_publication_unavailable"
        ) as caught:
            coordinator.review_and_commit_acquisition(plan, issuer.for_plan(plan))

        assert caught.value.code == "reviewed_acquisition_publication_unavailable"
        assert linked_authority.rule_generation_snapshot() is before
        assert stores.revision_pin().authority_generation == before[0]
        assert not hasattr(coordinator, "_lowerer")
    finally:
        stores.close()
