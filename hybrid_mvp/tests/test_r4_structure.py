"""R4 anti-leakage and retired-review absence checks."""
from __future__ import annotations

from pathlib import Path

__cemm_test_inventory__ = {'tests/test_r4_structure.py::test_episode_builder_executes_public_runtime_for_every_expanded_case': {'activation_phase': 'R4',
                                                                                                      'assertion_ref': 'assertion:r4-episode-builder-executes-public-runtime-for-every-expanded-case',
                                                                                                      'diagnostic_role': 'phase',
                                                                                                      'introduced_by_task': 'R4-Complete',
                                                                                                      'source_ast_sha256': '25d258ca8a0306e11cfc20fd38c47b044e216381b75b40c1f5745d08d35b3f82'},
 'tests/test_r4_structure.py::test_expected_contract_compiler_does_not_invoke_propose_or_runtime': {'activation_phase': 'R4',
                                                                                                    'assertion_ref': 'assertion:r4-expected-contract-compiler-does-not-invoke-propose-or-runtime',
                                                                                                    'diagnostic_role': 'phase',
                                                                                                    'introduced_by_task': 'R4-Complete',
                                                                                                    'source_ast_sha256': '9148f2e358a21a5787c8e5c4d587921fe4d68cae30a33af21ad2611e6fbacf70'},
 'tests/test_r4_structure.py::test_external_review_subsystem_is_absent': {'activation_phase': 'R4',
                                                                          'assertion_ref': 'assertion:r4-external-review-subsystem-is-absent',
                                                                          'diagnostic_role': 'phase',
                                                                          'introduced_by_task': 'R4-Complete',
                                                                          'source_ast_sha256': '454a4d90681f014b867ac0408b752bc9ccb2bf1205bd07e94f4a66f558f06ee7'}}


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


def test_external_review_subsystem_is_absent() -> None:
    forbidden = (
        SRC / "r4_review.py",
        ROOT / "scripts" / "prepare_r4_review_request.py",
        ROOT / "scripts" / "verify_r4_review_manifest.py",
        ROOT / "schemas" / "corpus_review_manifest.schema.json",
        ROOT / "data" / "review" / "R4_REVIEW_MANIFEST.template.json",
    )
    assert all(not path.exists() for path in forbidden)
    tokens = (
        "CorpusReviewManifest",
        "ApprovedR4Build",
        "CEMM_R4_REVIEW",
        "R4_REVIEW_MANIFEST",
        "external_review_required",
    )
    owners = (
        SRC / "r4_pipeline.py",
        SRC / "r4_admission.py",
        ROOT / "scripts" / "validation_gate.py",
    )
    assert not any(token in path.read_text(encoding="utf-8") for token in tokens for path in owners)
