"""R4 anti-leakage and anti-self-approval structural checks."""
from __future__ import annotations

from pathlib import Path

__cemm_test_inventory__ = {
    "tests/test_r4_structure.py::test_episode_builder_executes_public_runtime_for_every_expanded_case": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-episode-builder-executes-public-runtime-for-every-expanded-case",
        "diagnostic_role": "phase",
        "introduced_by_task": "R4-Complete",
        "source_ast_sha256": "25d258ca8a0306e11cfc20fd38c47b044e216381b75b40c1f5745d08d35b3f82"
    },
    "tests/test_r4_structure.py::test_expected_contract_compiler_does_not_invoke_propose_or_runtime": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-expected-contract-compiler-does-not-invoke-propose-or-runtime",
        "diagnostic_role": "phase",
        "introduced_by_task": "R4-Complete",
        "source_ast_sha256": "9148f2e358a21a5787c8e5c4d587921fe4d68cae30a33af21ad2611e6fbacf70"
    },
    "tests/test_r4_structure.py::test_r4_pipeline_cannot_self_approve_review_manifest": {
        "activation_phase": "R4",
        "assertion_ref": "assertion:r4-r4-pipeline-cannot-self-approve-review-manifest",
        "diagnostic_role": "phase",
        "introduced_by_task": "R4-Complete",
        "source_ast_sha256": "1fb20b7e8a558551144cca788dae75a8287fa352d2ac800ac104d0824d5010bd"
    }
}


ROOT = Path(__file__).parents[1]
SRC = ROOT / "src" / "cemm_authoritative_hybrid"


def test_expected_contract_compiler_does_not_invoke_propose_or_runtime() -> None:
    source = (SRC / "r4_contracts.py").read_text(encoding="utf-8")
    assert "BootstrapProposer" not in source
    assert ".propose(" not in source
    assert "HybridRuntime" not in source


def test_episode_builder_executes_public_runtime_for_every_expanded_case() -> None:
    source = (SRC / "r4_episodes.py").read_text(encoding="utf-8")
    assert "runtime_factory" in source
    assert ".process(" not in source or "process(" in source
    assert "surface_examples[0]" not in source


def test_r4_pipeline_cannot_self_approve_review_manifest() -> None:
    pipeline = (SRC / "r4_pipeline.py").read_text(encoding="utf-8")
    review = (SRC / "r4_review.py").read_text(encoding="utf-8")
    assert 'review_state="external_review_required"' in pipeline
    assert "ExternalSignatureVerifier" in review
    assert "private_key" not in pipeline
