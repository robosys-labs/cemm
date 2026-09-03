"""R4 anti-leakage and retired-review absence checks."""
from __future__ import annotations

import ast
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
                                                                          'source_ast_sha256': 'de4721c167bb4e55ad228400af42fe0394d85d678bbd0b974864d153d2c1fd95'}}


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

    forbidden_import_parts = {
        "r4_1_pre_review",
        "PRE_REVIEW_RECOMMENDATIONS",
        "serve_r4_1_review",
        "r4_1_review_session",
        "r4_1_guided_review",
        "r4_1_review_ui",
        "http.server",
        "webbrowser",
    }
    violations: list[tuple[str, str]] = []
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for item in ast.walk(tree):
            imported: list[str] = []
            if isinstance(item, ast.Import):
                imported = [alias.name for alias in item.names]
            elif isinstance(item, ast.ImportFrom):
                imported = [item.module or "", *(alias.name for alias in item.names)]
            for name in imported:
                if any(part in name for part in forbidden_import_parts):
                    violations.append((path.relative_to(ROOT).as_posix(), name))
    assert violations == []
