from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import sqlite3

import pytest

from cemm.v350.data.compiler import DeterministicSQLiteCompiler, SourceCompilationError
from cemm.v350.schema.codec import record_to_document
from cemm.v350.schema.model import (
    Cardinality,
    LocalPortSchema,
    PortFillerClass,
    PropertySchema,
    ReferentTypeSchema,
    SchemaLifecycleStatus,
    SchemaParentLink,
    StateDimensionSchema,
    StateValueSchema,
    StorageKind,
    UseProfile,
)
from cemm.v350.storage import (
    AssignmentStatus,
    EvidenceRecord,
    GraphPatch,
    KnowledgeRecord,
    KnowledgeStatus,
    MaterializedViewRecord,
    PatchCommitStatus,
    PatchOperation,
    PatchOperationKind,
    RecordDependency,
    RecordKind,
    SemanticStore,
    StateAssignment,
    StoreConflictError,
    StoreSnapshot,
    encode_record,
)
from cemm.v350.uol.model import (
    ApplicationBinding,
    FillerRef,
    IdentityStatus,
    Referent,
    SemanticApplication,
)


def profile(**values: str) -> UseProfile:
    return UseProfile.from_mapping(values)


def active_type(
    schema_ref: str,
    *parents: str,
    revision: int = 1,
    storage_kinds: frozenset[StorageKind] = frozenset({StorageKind.ORDINARY}),
) -> ReferentTypeSchema:
    return ReferentTypeSchema(
        schema_ref=schema_ref,
        semantic_key=schema_ref.rsplit(":", 1)[-1],
        parent_links=tuple(SchemaParentLink(item) for item in parents),
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        revision=revision,
        storage_kinds=storage_kinds,
        use_profile=profile(mention="allow", ground="allow", compose="allow", query="allow"),
    )


def operation(
    kind: RecordKind,
    record,
    *,
    revision: int | None = None,
    expected: int | None = None,
    dependencies: tuple[RecordDependency, ...] = (),
    operation_kind: PatchOperationKind = PatchOperationKind.UPSERT,
) -> PatchOperation:
    from cemm.v350.storage.codec import record_ref, record_revision

    resolved_revision = record_revision(kind, record) if revision is None else revision
    return PatchOperation(
        operation_ref=f"op:{kind.value}:{record_ref(kind, record)}:{resolved_revision}",
        operation_kind=operation_kind,
        record_kind=kind,
        target_ref=record_ref(kind, record),
        record_revision=resolved_revision,
        payload=encode_record(kind, record),
        expected_record_revision=expected,
        dependencies=dependencies,
    )


def patch(store: SemanticStore, *operations: PatchOperation, ref: str = "patch:test") -> GraphPatch:
    return GraphPatch(
        patch_ref=ref,
        context_ref="actual",
        scope_ref="global",
        source_ref="test",
        permission_ref="internal",
        operations=tuple(operations),
        expected_store_revision=store.revision,
    )


def bootstrap_store() -> SemanticStore:
    store = SemanticStore(":memory:")
    root = active_type("type:referent")
    person = active_type("type:person", "type:referent")
    animal = active_type("type:animal", "type:referent")
    result = store.apply_patch(patch(
        store,
        operation(RecordKind.SCHEMA, root),
        operation(RecordKind.SCHEMA, person),
        operation(RecordKind.SCHEMA, animal),
        ref="patch:types",
    ))
    assert result.committed, result.errors
    return store


def write_package(root: Path, records: list[tuple[RecordKind, object]]) -> None:
    modules = []
    by_kind: dict[RecordKind, list[object]] = {}
    for kind, record in records:
        by_kind.setdefault(kind, []).append(record)
    for kind in sorted(by_kind, key=lambda item: item.value):
        relative = f"modules/{kind.value}.jsonl"
        modules.append({
            "module_ref": f"module:{kind.value}",
            "path": relative,
            "record_kind": kind.value,
        })
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "".join(
                json.dumps(encode_record(kind, item), sort_keys=True) + "\n"
                for item in by_kind[kind]
            ),
            encoding="utf-8",
        )
    (root / "manifest.json").write_text(json.dumps({
        "package_ref": "test:package",
        "version": "1",
        "schema_version": 1,
        "modules": modules,
    }, sort_keys=True), encoding="utf-8")


def test_deterministic_compiler_produces_identical_database_bytes(tmp_path: Path) -> None:
    package = tmp_path / "source"
    package.mkdir()
    root = active_type("type:referent")
    person = active_type("type:person", "type:referent")
    user = Referent(
        "ref:user",
        storage_kind=StorageKind.ORDINARY,
        identity_status=IdentityStatus.RESOLVED,
        type_refs=("type:person",),
        context_refs=("actual",),
    )
    write_package(package, [
        (RecordKind.SCHEMA, root),
        (RecordKind.SCHEMA, person),
        (RecordKind.REFERENT, user),
    ])
    first = DeterministicSQLiteCompiler().compile(package, tmp_path / "one.sqlite", make_read_only=False)
    second = DeterministicSQLiteCompiler().compile(package, tmp_path / "two.sqlite", make_read_only=False)
    assert first.boot_fingerprint == second.boot_fingerprint
    assert first.record_set_fingerprint == second.record_set_fingerprint
    assert first.output_path.read_bytes() == second.output_path.read_bytes()


def test_compiler_rejects_duplicate_record_revision(tmp_path: Path) -> None:
    package = tmp_path / "source"
    package.mkdir()
    root = active_type("type:referent")
    path = package / "schemas.jsonl"
    path.write_text(
        json.dumps(record_to_document(root)) + "\n" + json.dumps(record_to_document(root)) + "\n",
        encoding="utf-8",
    )
    (package / "manifest.json").write_text(json.dumps({
        "package_ref": "test:duplicates",
        "version": "1",
        "modules": [{
            "module_ref": "schemas",
            "path": "schemas.jsonl",
            "record_kind": "schema",
        }],
    }), encoding="utf-8")
    with pytest.raises(SourceCompilationError, match="duplicate source record"):
        DeterministicSQLiteCompiler().compile(package, tmp_path / "boot.sqlite")


def test_read_only_boot_and_overlay_supersession(tmp_path: Path) -> None:
    package = tmp_path / "source"
    package.mkdir()
    type_v1 = active_type("type:referent")
    write_package(package, [(RecordKind.SCHEMA, type_v1)])
    boot = DeterministicSQLiteCompiler().compile(package, tmp_path / "boot.sqlite").output_path
    store = SemanticStore(tmp_path / "overlay.sqlite", boot_path=boot)
    try:
        assert store.repositories.schemas.authoritative("type:referent").revision == 1
        with pytest.raises(sqlite3.OperationalError):
            store._boot.execute("INSERT INTO meta(key, value) VALUES ('x', 'y')")
        type_v2 = replace(type_v1, revision=2, supersedes_revision=1)
        result = store.apply_patch(patch(
            store,
            operation(RecordKind.SCHEMA, type_v2, expected=1),
            ref="patch:type-v2",
        ))
        assert result.committed, result.errors
        assert store.repositories.schemas.authoritative("type:referent").revision == 2
        assert store.get_record(RecordKind.SCHEMA, "type:referent", 1).layer == "boot"
        assert store.get_record(RecordKind.SCHEMA, "type:referent", 2).layer == "overlay"
    finally:
        store.close()


def test_patch_is_atomic_when_one_record_is_invalid() -> None:
    store = bootstrap_store()
    try:
        evidence = EvidenceRecord("evidence:1", "source:test", 1.0, "lineage:test")
        knowledge = KnowledgeRecord(
            knowledge_ref="knowledge:missing",
            proposition_ref="proposition:missing",
            truth_status=KnowledgeStatus.SUPPORTED,
            confidence=1.0,
            context_ref="actual",
            source_refs=("source:test",),
            evidence_refs=(evidence.evidence_ref,),
        )
        result = store.apply_patch(patch(
            store,
            operation(RecordKind.EVIDENCE, evidence),
            operation(RecordKind.KNOWLEDGE, knowledge),
            ref="patch:atomic-reject",
        ))
        assert not result.committed
        assert store.get_record(RecordKind.EVIDENCE, evidence.evidence_ref) is None
        assert store.revision == 1
    finally:
        store.close()


def test_store_and_record_compare_and_swap() -> None:
    store = bootstrap_store()
    try:
        person = Referent(
            "ref:person",
            identity_status=IdentityStatus.RESOLVED,
            type_refs=("type:person",),
            context_refs=("actual",),
        )
        first = store.apply_patch(patch(
            store,
            operation(RecordKind.REFERENT, person),
            ref="patch:person-v1",
        ))
        assert first.committed
        stale_store_patch = GraphPatch(
            patch_ref="patch:stale-store",
            context_ref="actual",
            scope_ref="global",
            source_ref="test",
            permission_ref="internal",
            operations=(operation(RecordKind.REFERENT, replace(person, revision=2), expected=1),),
            expected_store_revision=1,
        )
        result = store.apply_patch(stale_store_patch)
        assert result.status == PatchCommitStatus.CONFLICT
        stale_record = store.apply_patch(patch(
            store,
            operation(RecordKind.REFERENT, replace(person, revision=2), expected=7),
            ref="patch:stale-record",
        ))
        assert stale_record.status == PatchCommitStatus.CONFLICT
    finally:
        store.close()


def test_application_commit_enforces_exact_schema_ports() -> None:
    store = bootstrap_store()
    try:
        named = PropertySchema(
            schema_ref="property:named",
            semantic_key="named",
            holder_type_refs=("type:referent",),
            value_type_refs=("type:referent",),
            local_ports=(
                LocalPortSchema(
                    "holder",
                    accepted_type_refs=("type:referent",),
                    cardinality=Cardinality(1, 1),
                ),
                LocalPortSchema(
                    "value",
                    accepted_type_refs=("type:referent",),
                    cardinality=Cardinality(1, 1),
                ),
            ),
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            use_profile=profile(compose="allow", query="allow"),
        )
        holder = Referent(
            "ref:holder",
            identity_status=IdentityStatus.RESOLVED,
            type_refs=("type:person",),
            context_refs=("actual",),
        )
        result = store.apply_patch(patch(
            store,
            operation(RecordKind.SCHEMA, named),
            operation(RecordKind.REFERENT, holder),
            ref="patch:named-foundation",
        ))
        assert result.committed, result.errors
        incomplete = SemanticApplication(
            "application:named",
            named.schema_ref,
            1,
            (
                ApplicationBinding(
                    "holder",
                    (FillerRef(PortFillerClass.REFERENT, holder.referent_ref),),
                ),
            ),
            "actual",
        )
        rejected = store.apply_patch(patch(
            store,
            operation(RecordKind.SEMANTIC_APPLICATION, incomplete),
            ref="patch:bad-application",
        ))
        assert not rejected.committed
        assert any("cardinality" in item for item in rejected.errors)
    finally:
        store.close()


def test_state_assignment_enforces_holder_type_applicability() -> None:
    store = bootstrap_store()
    try:
        dimension = StateDimensionSchema(
            schema_ref="state:life-status",
            semantic_key="life_status",
            holder_type_refs=("type:animal",),
            value_schema_refs=("state-value:alive",),
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            use_profile=profile(compose="allow", query="allow"),
        )
        alive = StateValueSchema(
            schema_ref="state-value:alive",
            semantic_key="alive",
            dimension_ref=dimension.schema_ref,
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            use_profile=profile(compose="allow", query="allow"),
        )
        person = Referent(
            "ref:person",
            identity_status=IdentityStatus.RESOLVED,
            type_refs=("type:person",),
            context_refs=("actual",),
        )
        seed = store.apply_patch(patch(
            store,
            operation(RecordKind.SCHEMA, dimension),
            operation(RecordKind.SCHEMA, alive),
            operation(RecordKind.REFERENT, person),
            ref="patch:state-foundation",
        ))
        assert seed.committed, seed.errors
        assignment = StateAssignment(
            assignment_ref="assignment:person:alive",
            holder_ref=person.referent_ref,
            dimension_ref=dimension.schema_ref,
            dimension_revision=1,
            value_ref=alive.schema_ref,
            value_revision=1,
            status=AssignmentStatus.ACTIVE,
            context_ref="actual",
            confidence=1.0,
            evidence_refs=("evidence:asserted",),
        )
        result = store.apply_patch(patch(
            store,
            operation(RecordKind.STATE_ASSIGNMENT, assignment),
            ref="patch:invalid-state-holder",
        ))
        assert not result.committed
        assert any("does not satisfy type constraints" in item for item in result.errors)
    finally:
        store.close()


def test_dependency_change_invalidates_materialized_view() -> None:
    store = bootstrap_store()
    try:
        person = Referent(
            "ref:person",
            identity_status=IdentityStatus.RESOLVED,
            type_refs=("type:person",),
            context_refs=("actual",),
        )
        assert store.apply_patch(patch(
            store,
            operation(RecordKind.REFERENT, person),
            ref="patch:person",
        )).committed
        dependency_fingerprint = store.dependency_fingerprint((person.referent_ref,))
        current = store.get_record(RecordKind.REFERENT, person.referent_ref)
        view = MaterializedViewRecord(
            view_ref="view:person",
            view_kind="referent_knowledge",
            subject_ref=person.referent_ref,
            context_ref="actual",
            payload={"types": ["type:person"]},
            dependency_refs=(person.referent_ref,),
            dependency_fingerprint=dependency_fingerprint,
            snapshot_revision=store.revision,
        )
        materialized = PatchOperation(
            operation_ref="op:view:person",
            operation_kind=PatchOperationKind.MATERIALIZE,
            record_kind=RecordKind.MATERIALIZED_VIEW,
            target_ref=view.view_ref,
            payload=encode_record(RecordKind.MATERIALIZED_VIEW, view),
            dependencies=(RecordDependency(
                RecordKind.REFERENT,
                person.referent_ref,
                revision=current.revision,
                fingerprint=current.record_fingerprint,
            ),),
        )
        result = store.apply_patch(patch(store, materialized, ref="patch:view"))
        assert result.committed, result.errors
        assert store.materialized_view(view.view_ref) is not None
        updated = replace(person, revision=2, metadata={"changed": True})
        result = store.apply_patch(patch(
            store,
            operation(RecordKind.REFERENT, updated, expected=1),
            ref="patch:person-v2",
        ))
        assert result.committed, result.errors
        assert view.view_ref in result.invalidated_view_refs
        assert store.materialized_view(view.view_ref) is None
    finally:
        store.close()


def test_snapshot_detects_later_overlay_revision() -> None:
    store = bootstrap_store()
    try:
        snapshot = StoreSnapshot(
            store_revision=store.revision,
            boot_fingerprint=store.boot_fingerprint,
            overlay_fingerprint=store.overlay_fingerprint,
        )
        person = Referent(
            "ref:person",
            identity_status=IdentityStatus.RESOLVED,
            type_refs=("type:person",),
            context_refs=("actual",),
        )
        assert store.apply_patch(patch(
            store,
            operation(RecordKind.REFERENT, person),
            ref="patch:snapshot-change",
        )).committed
        with pytest.raises(StoreConflictError, match="stale"):
            store.get_record(RecordKind.REFERENT, person.referent_ref, snapshot=snapshot)
    finally:
        store.close()


def test_snapshot_detects_overlay_fingerprint_change_without_revision_change() -> None:
    store = bootstrap_store()
    try:
        snapshot = StoreSnapshot(
            store_revision=store.revision,
            boot_fingerprint=store.boot_fingerprint,
            overlay_fingerprint=store.overlay_fingerprint,
        )
        store._overlay.execute(
            "UPDATE meta SET value=? WHERE key='record_set_fingerprint'",
            ("overlay-records:fixture-drift",),
        )
        store._overlay.commit()
        with pytest.raises(StoreConflictError, match="overlay database fingerprint changed"):
            store.records(RecordKind.SCHEMA, snapshot=snapshot)
    finally:
        store.close()


def test_normalized_tables_are_populated() -> None:
    store = bootstrap_store()
    try:
        rows = store._overlay.execute(
            "SELECT COUNT(*) FROM semantic_schemas"
        ).fetchone()[0]
        parents = store._overlay.execute(
            "SELECT COUNT(*) FROM schema_parents"
        ).fetchone()[0]
        assert rows == 3
        assert parents == 2
    finally:
        store.close()


def test_existing_record_revision_is_immutable_even_with_a_new_patch() -> None:
    store = bootstrap_store()
    try:
        person = Referent(
            "ref:immutable-person",
            identity_status=IdentityStatus.RESOLVED,
            type_refs=("type:person",),
            context_refs=("actual",),
        )
        first = store.apply_patch(patch(
            store,
            operation(RecordKind.REFERENT, person),
            ref="patch:immutable-person-v1",
        ))
        assert first.committed, first.errors

        rewritten = replace(person, metadata={"rewritten": True})
        second = store.apply_patch(patch(
            store,
            operation(RecordKind.REFERENT, rewritten),
            ref="patch:rewrite-same-revision",
        ))
        assert not second.committed
        assert second.status == PatchCommitStatus.CONFLICT
        assert second.errors == ("record_revision_immutable:ref:immutable-person@1",)
        stored = store.repositories.referents.require(person.referent_ref)
        assert stored.payload.metadata == {}
    finally:
        store.close()


def test_invalidated_materialized_view_can_be_rebuilt_at_a_new_revision() -> None:
    store = bootstrap_store()
    try:
        person = Referent(
            "ref:rematerialized-person",
            identity_status=IdentityStatus.RESOLVED,
            type_refs=("type:person",),
            context_refs=("actual",),
        )
        assert store.apply_patch(patch(
            store,
            operation(RecordKind.REFERENT, person),
            ref="patch:rematerialized-person",
        )).committed
        current = store.repositories.referents.require(person.referent_ref)
        first_view = MaterializedViewRecord(
            view_ref="view:rematerialized-person",
            view_kind="referent_knowledge",
            subject_ref=person.referent_ref,
            context_ref="actual",
            payload={"revision": 1},
            dependency_refs=(person.referent_ref,),
            dependency_fingerprint=store.dependency_fingerprint((person.referent_ref,)),
            snapshot_revision=store.revision,
        )
        first_operation = PatchOperation(
            operation_ref="op:view:rematerialized-person:1",
            operation_kind=PatchOperationKind.MATERIALIZE,
            record_kind=RecordKind.MATERIALIZED_VIEW,
            target_ref=first_view.view_ref,
            record_revision=1,
            payload=encode_record(RecordKind.MATERIALIZED_VIEW, first_view),
            dependencies=(RecordDependency(
                RecordKind.REFERENT,
                person.referent_ref,
                revision=current.revision,
                fingerprint=current.record_fingerprint,
            ),),
        )
        assert store.apply_patch(patch(
            store, first_operation, ref="patch:view:rematerialized-person:1"
        )).committed

        revised_person = replace(person, revision=2, metadata={"changed": True})
        changed = store.apply_patch(patch(
            store,
            operation(RecordKind.REFERENT, revised_person, expected=1),
            ref="patch:rematerialized-person-v2",
        ))
        assert changed.committed, changed.errors
        assert store.materialized_view(first_view.view_ref) is None

        revised_record = store.repositories.referents.require(person.referent_ref)
        second_view = replace(
            first_view,
            payload={"revision": 2},
            dependency_fingerprint=store.dependency_fingerprint((person.referent_ref,)),
            snapshot_revision=store.revision,
        )
        prior_view = store.get_record(RecordKind.MATERIALIZED_VIEW, first_view.view_ref)
        second_operation = PatchOperation(
            operation_ref="op:view:rematerialized-person:2",
            operation_kind=PatchOperationKind.MATERIALIZE,
            record_kind=RecordKind.MATERIALIZED_VIEW,
            target_ref=second_view.view_ref,
            record_revision=2,
            payload=encode_record(RecordKind.MATERIALIZED_VIEW, second_view),
            expected_record_revision=prior_view.revision,
            expected_record_fingerprint=prior_view.record_fingerprint,
            dependencies=(RecordDependency(
                RecordKind.REFERENT,
                person.referent_ref,
                revision=revised_record.revision,
                fingerprint=revised_record.record_fingerprint,
            ),),
        )
        rebuilt = store.apply_patch(patch(
            store, second_operation, ref="patch:view:rematerialized-person:2"
        ))
        assert rebuilt.committed, rebuilt.errors
        assert store.materialized_view(first_view.view_ref).payload == {"revision": 2}
    finally:
        store.close()
