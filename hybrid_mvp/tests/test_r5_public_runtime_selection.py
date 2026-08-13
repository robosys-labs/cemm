from __future__ import annotations

from pathlib import Path

import pytest

import cemm_authoritative_hybrid.bootstrap as runtime_bootstrap
from cemm_authoritative_hybrid import load_runtime
from cemm_authoritative_hybrid.gaps import MissingOwner
from cemm_authoritative_hybrid.proposal import BootstrapProposer


__cemm_test_inventory__ = {
    "tests/test_r5_public_runtime_selection.py::test_selected_release_runtime_never_invokes_bootstrap_proposer": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:release-path-excludes-bootstrap-proposer",
        "contributes_to_rewrite_refs": [
            "rewrite_obligation:1961f2f12d4a3f36b41db460"
        ],
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "proposal-contract",
        "source_ast_sha256": "7b9e4bb0550ea577e154d71194e48aa91b27c25fcc80fe80e73b7743a32aeb7b",
    },
    "tests/test_r5_public_runtime_selection.py::test_release_runtime_requires_selected_neural_proposer": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:neural-proposer-release-runtime-requires-neural-switch-proposer",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "proposal-contract",
        "supersedes_node_id": "tests/test_neural_proposer.py::test_release_runtime_requires_neural_switch_proposer",
        "source_ast_sha256": "4e76c77c10c0dbb5e62dd1ca5aebc4a73a123a8ae53715371707862e08aa68db",
    },
    "tests/test_r5_public_runtime_selection.py::test_release_runtime_does_not_delegate_to_bootstrap": {
        "activation_phase": "R5",
        "assertion_ref": "assertion:neural-weight-use-release-path-does-not-delegate-to-bootstrap",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "proposal-contract",
        "supersedes_node_id": "tests/test_neural_weight_use.py::test_release_path_does_not_delegate_to_bootstrap",
        "source_ast_sha256": "ba97a078c070fecefff7cb21ffca96850022b094889d5af0ff83751548052118",
    },
}


def _assert_selected_proposal_owner_is_not_admitted(monkeypatch) -> None:
    def fail_bootstrap(*_args, **_kwargs):
        raise AssertionError("release selection touched BootstrapProposer")

    monkeypatch.setattr(runtime_bootstrap, "BootstrapProposer", fail_bootstrap)
    monkeypatch.setattr(BootstrapProposer, "propose", fail_bootstrap)

    with pytest.raises(MissingOwner) as captured:
        load_runtime(Path("does-not-exist"), profile="release")

    assert type(captured.value) is MissingOwner
    assert captured.value.owner_name == "program_abi_2_proposal_owner"


def test_selected_release_runtime_never_invokes_bootstrap_proposer(monkeypatch):
    _assert_selected_proposal_owner_is_not_admitted(monkeypatch)


def test_release_runtime_requires_selected_neural_proposer(monkeypatch):
    _assert_selected_proposal_owner_is_not_admitted(monkeypatch)


def test_release_runtime_does_not_delegate_to_bootstrap(monkeypatch):
    _assert_selected_proposal_owner_is_not_admitted(monkeypatch)
