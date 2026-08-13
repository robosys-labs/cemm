from __future__ import annotations

from pathlib import Path

from cemm_authoritative_hybrid import ResponseMeaning, load_runtime


ROOT = Path(__file__).parents[1]


__cemm_test_inventory__ = {
    "tests/test_r5_realization_boundary.py::test_public_development_runtime_stops_at_exact_r5_realization_owner": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:r5-public-runtime-stops-at-realization-later-owner",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "realization-contract",
        "source_ast_sha256": "9563c49aaee421068f151c7ddacca78ac6271c6d4828c46aeb9e2414d84508c7",
    },
}


def test_public_development_runtime_stops_at_exact_r5_realization_owner(
    tmp_path: Path,
) -> None:
    runtime = load_runtime(
        ROOT,
        profile="development",
        store_path=tmp_path / "runtime.sqlite3",
    )
    try:
        result = runtime.process("session:r5-realization-boundary", "hello")
    finally:
        runtime.stores.close()

    response = result.response_meaning
    assert type(response) is ResponseMeaning
    assert response.response_meaning_ref
    assert response.discourse_action
    assert response.response_expression.root_refs
    assert response.response_expression.applications
    assert response.proof_refs

    assert result.realization_receipt is None
    assert not hasattr(result, "surface")
    assert "surface" not in response.as_dict()
    assert result.gap_receipt is not None
    assert result.gap_receipt.status == "later_owner_not_admitted"
    assert result.gap_receipt.missing_contract_refs == (
        "contract:r5:realize_surface",
    )
    assert result.gap_receipt.safe_response_action == "stop_without_surface"
