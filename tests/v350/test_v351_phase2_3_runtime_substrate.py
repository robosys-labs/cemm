from __future__ import annotations

import ast
from pathlib import Path
import threading

from cemm.v350.cycle_control import (
    CompletionEvaluator,
    CycleCompletionStatus,
    CycleWorkspace,
    FrontierEffect,
)
from cemm.v350.runtime_generations import (
    GenerationDomain,
    infer_patch_domains,
)
from cemm.v350.schema.model import semantic_fingerprint
from cemm.v350.storage import (
    EvidenceRecord,
    GraphPatch,
    PatchOperation,
    PatchOperationKind,
    RecordKind,
    SemanticStore,
    encode_record,
)


ROOT = Path(__file__).resolve().parents[2]


def _evidence(ref: str, value: str = "x") -> EvidenceRecord:
    return EvidenceRecord(
        evidence_ref=ref,
        source_ref="source:test",
        confidence=1.0,
        lineage_ref="source:test",
        context_ref="actual",
        metadata={"value": value},
    )


def _patch(store: SemanticStore, record: EvidenceRecord) -> GraphPatch:
    with store.snapshot() as snapshot:
        return GraphPatch(
            patch_ref="patch:" + semantic_fingerprint(
                "phase23-test-patch",
                (record.evidence_ref, record.metadata),
                20,
            ),
            context_ref="actual",
            scope_ref="test:world",
            source_ref="source:test",
            permission_ref="conversation",
            operations=(
                PatchOperation(
                    operation_ref="op:" + semantic_fingerprint(
                        "phase23-test-op",
                        record.evidence_ref,
                        20,
                    ),
                    operation_kind=PatchOperationKind.UPSERT,
                    record_kind=RecordKind.EVIDENCE,
                    target_ref=record.evidence_ref,
                    record_revision=1,
                    payload=encode_record(
                        RecordKind.EVIDENCE,
                        record,
                    ),
                ),
            ),
            expected_store_revision=snapshot.store_revision,
        )


def test_world_write_does_not_advance_semantic_authority(tmp_path):
    store = SemanticStore(tmp_path / "overlay.sqlite")
    try:
        before = store.current_read_generation()
        result = store.apply_patch(
            _patch(
                store,
                _evidence("evidence:phase23:a"),
            )
        )
        assert result.committed
        after = store.current_read_generation()

        assert (
            after.authority_generation
            == before.authority_generation
        )
        assert (
            after.authority_fingerprint
            == before.authority_fingerprint
        )
        assert after.world_revision == before.world_revision + 1
        assert after.audit_revision == before.audit_revision + 1
    finally:
        store.close()


def test_patch_domain_classification_keeps_evidence_out_of_authority(tmp_path):
    store = SemanticStore(tmp_path / "overlay.sqlite")
    try:
        patch = _patch(
            store,
            _evidence("evidence:phase23:domain"),
        )
        domains = infer_patch_domains(patch)
        assert GenerationDomain.WORLD in domains
        assert GenerationDomain.AUDIT in domains
        assert GenerationDomain.AUTHORITY not in domains
    finally:
        store.close()


def test_read_snapshot_does_not_hold_global_python_writer_lock(tmp_path):
    store = SemanticStore(tmp_path / "overlay.sqlite")
    try:
        with store.snapshot() as pinned:
            writer_completed = threading.Event()

            def writer():
                store.apply_patch(
                    _patch(
                        store,
                        _evidence("evidence:phase23:concurrent"),
                    )
                )
                writer_completed.set()

            thread = threading.Thread(target=writer)
            thread.start()
            assert writer_completed.wait(2.0), (
                "writer was serialized behind semantic snapshot "
                "by a process-global Python lock"
            )
            assert pinned.store_revision == 0
            thread.join(timeout=2.0)
    finally:
        store.close()


def test_two_read_snapshots_overlap_without_global_lock(tmp_path):
    store = SemanticStore(tmp_path / "overlay.sqlite")
    started = threading.Barrier(3)
    release = threading.Event()
    completed = []

    def reader():
        with store.snapshot() as snapshot:
            started.wait()
            release.wait(2.0)
            completed.append(snapshot.store_revision)

    threads = [
        threading.Thread(target=reader)
        for _ in range(2)
    ]
    try:
        for thread in threads:
            thread.start()
        started.wait(timeout=2.0)
        release.set()
        for thread in threads:
            thread.join(timeout=2.0)
        assert completed == [0, 0] or sorted(completed) == [0, 0]
    finally:
        release.set()
        for thread in threads:
            thread.join(timeout=1.0)
        store.close()


def test_resolve_any_uses_record_ref_index_not_recordkind_enumeration():
    source = (
        ROOT
        / "cemm/v350/storage/generation_store.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    method = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "resolve_any"
    )
    assert not any(
        isinstance(node, ast.For)
        and isinstance(node.iter, ast.Name)
        and node.iter.id == "RecordKind"
        for node in ast.walk(method)
    )
    assert (
        "SELECT DISTINCT record_kind "
        "FROM record_index WHERE record_ref=?"
    ) in source


def test_overlay_authenticated_root_is_append_only_not_full_record_scan():
    source = (
        ROOT
        / "cemm/v350/storage/generation_store.py"
    ).read_text(encoding="utf-8")
    start = source.index("def _overlay_record_fingerprint")
    end = source.index("def _journal_patch", start)
    method = source[start:end]
    assert "FROM record_index" not in method
    assert "overlay-append-root" in method


def test_schema_and_language_cache_keys_are_authority_generation_scoped():
    source = (
        ROOT / "cemm/v350/storage/repositories.py"
    ).read_text(encoding="utf-8")
    assert (
        "authority.generation, "
        "authority.authority_fingerprint"
    ) in source
    assert (
        "snapshot.authority_generation, "
        "snapshot.authority_fingerprint"
    ) in source


def test_cycle_workspace_carries_only_explicit_reentry_artifacts():
    workspace = CycleWorkspace({"a": 1, "b": 2})
    workspace.register_frontier(
        "frontier:test",
        (FrontierEffect.INFORMATIONAL,),
    )
    carried = workspace.carry(("b",))
    assert carried.artifacts == {"b": 2}
    assert carried.frontier_effects == {}


def test_completion_status_does_not_equate_empty_errors_with_success():
    class Cycle:
        errors = []
        artifacts = {}
        workspace = CycleWorkspace()
        frontiers = []

    assert (
        CompletionEvaluator().evaluate(Cycle())
        == CycleCompletionStatus.NO_RESPONSE_REQUIRED
    )


def test_run_text_has_no_request_frequency_learning_or_runtime_observer():
    source = (
        ROOT / "cemm/v350/runtime.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    run_text = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "run_text"
    )
    segment = ast.get_source_segment(source, run_text) or ""
    assert "LearningRuntimeActivator" not in segment
    assert "RuntimeSelfObserver" not in segment
    assert "session_lifecycle.resolve" in segment


def test_stage_snapshot_validation_ignores_audit_only_generation_movement():
    source = (
        ROOT / "cemm/v350/runtime.py"
    ).read_text(encoding="utf-8")
    start = source.index("def _snapshot(")
    end = source.index("@staticmethod", start)
    method = source[start:end]
    assert "read_generation_fingerprint" not in method
    assert "cognitive_generation_fingerprint" in method
    assert "authority_fingerprint" in method


def test_learning_advancer_preserves_dependency_pins_and_targeted_frontiers():
    source = (
        ROOT / "cemm/v350/learning/runtime_advance.py"
    ).read_text(encoding="utf-8")
    assert "frontier_refs: tuple[str, ...] | None = None" in source
    assert "frontier, pins, dependency_pins" in source
    assert "for proposal in ()" not in source
    assert "tuple(dependency_pins)" in source


def test_session_participant_concurrent_recovery_validates_all_identity_members():
    source = (
        ROOT / "cemm/v350/runtime.py"
    ).read_text(encoding="utf-8")
    assert "concurrent_referent.record_fingerprint" in source
    assert "concurrent_evidence.record_fingerprint" in source
    assert "concurrent_assertion.record_fingerprint" in source


def test_phase3_stage22_does_not_advance_learning_on_every_request():
    source = (
        ROOT / "cemm/v350/runtime_hardening.py"
    ).read_text(encoding="utf-8")
    start = source.index("def stage_22_finalize")
    segment = source[start:]
    assert "RuntimeLearningAdvancer(" not in segment
    assert '"maintenance_event"' in segment


def test_authority_publication_is_blocked_while_semantic_pass_is_active(tmp_path):
    store = SemanticStore(tmp_path / "overlay.sqlite")
    try:
        item = _evidence("evidence:phase23:authority-lease")
        with store.snapshot() as snapshot:
            patch = GraphPatch(
                patch_ref="patch:phase23:authority-lease",
                context_ref="actual",
                scope_ref="test:authority-publication",
                source_ref="source:test",
                permission_ref="internal",
                operations=(
                    PatchOperation(
                        operation_ref="op:phase23:authority-lease",
                        operation_kind=PatchOperationKind.UPSERT,
                        record_kind=RecordKind.EVIDENCE,
                        target_ref=item.evidence_ref,
                        record_revision=1,
                        payload=encode_record(RecordKind.EVIDENCE, item),
                    ),
                ),
                expected_store_revision=snapshot.store_revision,
                metadata={"generation_domains": ("authority",)},
            )

        with store.semantic_pass():
            blocked = store.apply_patch(patch)
            assert not blocked.committed
            assert any(
                "authority_generation_in_use" in error
                for error in blocked.errors
            )

        committed = store.apply_patch(patch)
        assert committed.committed
    finally:
        store.close()


def test_candidate_schema_does_not_advance_executable_authority_domain():
    candidate = GraphPatch(
        patch_ref="patch:phase23:candidate-schema-domain",
        context_ref="global",
        scope_ref="learning:candidate",
        source_ref="source:test",
        permission_ref="internal",
        operations=(
            PatchOperation(
                operation_ref="op:phase23:candidate-schema-domain",
                operation_kind=PatchOperationKind.UPSERT,
                record_kind=RecordKind.SCHEMA,
                target_ref="schema:candidate:test",
                record_revision=1,
                payload={
                    "schema_ref": "schema:candidate:test",
                    "revision": 1,
                    "lifecycle_status": "candidate",
                },
            ),
        ),
    )
    domains = infer_patch_domains(candidate)
    assert GenerationDomain.AUTHORITY not in domains
    assert GenerationDomain.AUDIT in domains


def test_active_schema_does_advance_executable_authority_domain():
    active = GraphPatch(
        patch_ref="patch:phase23:active-schema-domain",
        context_ref="global",
        scope_ref="learning:promotion",
        source_ref="source:test",
        permission_ref="internal",
        operations=(
            PatchOperation(
                operation_ref="op:phase23:active-schema-domain",
                operation_kind=PatchOperationKind.UPSERT,
                record_kind=RecordKind.SCHEMA,
                target_ref="schema:active:test",
                record_revision=2,
                payload={
                    "schema_ref": "schema:active:test",
                    "revision": 2,
                    "lifecycle_status": "active",
                },
            ),
        ),
    )
    domains = infer_patch_domains(active)
    assert GenerationDomain.AUTHORITY in domains


def test_staged_resolver_also_avoids_recordkind_enumeration():
    source = (
        ROOT / "cemm/v350/storage/store.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    staged = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
        and node.name == "_StagedResolver"
    )
    method = next(
        node
        for node in staged.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "resolve_any"
    )
    assert not any(
        isinstance(node, ast.For)
        and isinstance(node.iter, ast.Name)
        and node.iter.id == "RecordKind"
        for node in ast.walk(method)
    )


def test_emitted_partial_query_is_not_reported_as_full_success():
    class Request:
        response_requested = True

    class Retrieval:
        request = Request()

    workspace = CycleWorkspace()
    workspace.register_frontier(
        "frontier:query:missing-answer",
        (FrontierEffect.BLOCKS_QUERY_ANSWER,),
    )

    class Cycle:
        errors = []
        artifacts = {
            "retrieval_result": Retrieval(),
            "emission": object(),
        }
        frontiers = []

    Cycle.workspace = workspace
    assert (
        CompletionEvaluator().evaluate(Cycle())
        == CycleCompletionStatus.PARTIAL
    )


def test_emission_despite_emission_block_is_runtime_invariant_failure():
    workspace = CycleWorkspace()
    workspace.register_frontier(
        "frontier:emission:blocked",
        (FrontierEffect.BLOCKS_EMISSION,),
    )

    class Cycle:
        errors = []
        artifacts = {"emission": object()}
        frontiers = []

    Cycle.workspace = workspace
    assert (
        CompletionEvaluator().evaluate(Cycle())
        == CycleCompletionStatus.RUNTIME_ERROR
    )
