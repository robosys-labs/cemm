from cemm.response.types import WriteOutcome


def test_auxiliary_commit_does_not_satisfy_required_relation_write():
    outcome = WriteOutcome(
        patch_count=2, committed_count=1, commit_status="conflict",
        required_target_ids=["relation:email"],
        committed_target_ids=["concept:email"],
        operation_results={"relation:email": "rejected", "concept:email": "committed"},
    )
    assert not outcome.satisfied
    assert not outcome.committed


def test_required_operation_commit_is_truthful():
    outcome = WriteOutcome(
        patch_count=1, committed_count=1, commit_status="committed",
        required_target_ids=["relation:email"],
        committed_target_ids=["relation:email"],
    )
    assert outcome.satisfied
    assert outcome.committed
