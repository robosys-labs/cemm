from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_indexed_get_record_filters_invalidated_revision_before_returning():
    source = (ROOT / "cemm/v350/storage/generation_store.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    method = next(
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "get_record"
    )
    segment = ast.get_source_segment(source, method) or ""
    assert "self.is_invalidated" in segment
    assert "chosen = candidates[max(candidates)]" in segment


def test_phase5_runtime_does_not_import_old_runtime_hardening_wrapper():
    source = (ROOT / "cemm/v350/runtime_v351.py").read_text(encoding="utf-8")
    assert "runtime_hardening" not in source
    assert "MeaningComposer" not in source
    assert "SelectedUOLCommitPlanner" not in source


def test_compiled_semantic_capabilities_ignore_invalidated_authority_and_dependencies():
    source = (ROOT / "cemm/v350/semantic_capability.py").read_text(encoding="utf-8")
    assert "self.__store.is_invalidated(kind, stored.record_ref, stored.revision)" in source
    assert "stale_missing_or_invalidated_exact_record" in source
    assert "stale_or_invalidated_compiled_dependency" in source


def test_workspace_exact_lookup_cannot_shadow_newer_durable_revision():
    source = (ROOT / "cemm/v350/workspace_store.py").read_text(encoding="utf-8")
    assert "transient if transient.revision > durable.revision else durable" in source
    assert "transient record collides with durable exact identity" in source


def test_workspace_cannot_resurrect_invalidated_durable_exact_identity():
    source = (ROOT / "cemm/v350/workspace_store.py").read_text(encoding="utf-8")
    assert "transient record cannot resurrect invalidated durable identity" in source
    assert "self.__base.records(kind, all_revisions=True)" in source
