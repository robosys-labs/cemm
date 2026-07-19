from __future__ import annotations

import pytest

from cemm.v350.learning.model import PinnedRecord
from cemm.v350.migration.engine import MigrationRuleRegistry, MigrationTransformerRegistry
from cemm.v350.migration.model import (
    MigrationDisposition,
    MigrationRuleRecord,
    MigrationTargetMapRecord,
)
from cemm.v350.schema.model import SchemaLifecycleStatus
from cemm.v350.storage.model import RecordKind


def _pin(kind: RecordKind, ref: str, revision: int = 1) -> PinnedRecord:
    return PinnedRecord(kind, ref, revision, (ref.encode().hex() + "0" * 64)[:64])


def _rule(ref="migration-rule:x", revision=1, supersedes=None, *, active=False, min_sources=1, max_sources=1):
    return MigrationRuleRecord(
        rule_ref=ref,
        source_system_refs=("legacy:test",),
        source_version_refs=("v1",),
        source_shape_ref="shape:test",
        target_record_kinds=(RecordKind.REFERENT,),
        transformer_ref="transformer:test",
        transformer_revision="1",
        field_mapping_refs=("mapping:test",),
        validation_requirements=("validate:test",),
        minimum_source_records=min_sources,
        maximum_source_records=max_sources,
        competence_case_refs=(("competence:test",) if active else ()),
        lifecycle_status=(SchemaLifecycleStatus.ACTIVE if active else SchemaLifecycleStatus.CANDIDATE),
        revision=revision,
        supersedes_revision=supersedes,
    )


def test_active_migration_rule_requires_competence():
    with pytest.raises(ValueError):
        MigrationRuleRecord(
            rule_ref="migration-rule:bad",
            source_system_refs=("legacy:test",),
            source_version_refs=("v1",),
            source_shape_ref="shape:test",
            target_record_kinds=(RecordKind.REFERENT,),
            transformer_ref="transformer:test",
            transformer_revision="1",
            field_mapping_refs=("mapping:test",),
            validation_requirements=("validate:test",),
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        )


def test_split_and_merge_topology_are_structurally_exact():
    source1=_pin(RecordKind.MIGRATION_SOURCE,"migration-source:1")
    source2=_pin(RecordKind.MIGRATION_SOURCE,"migration-source:2")
    rule=_pin(RecordKind.MIGRATION_RULE,"migration-rule:x")
    target1=_pin(RecordKind.REFERENT,"referent:1")
    target2=_pin(RecordKind.REFERENT,"referent:2")
    split=MigrationTargetMapRecord("map:split",(source1,),rule,(target1,target2),MigrationDisposition.SPLIT,())
    merged=MigrationTargetMapRecord("map:merge",(source1,source2),rule,(target1,),MigrationDisposition.MERGED,())
    assert len(split.target_pins)==2
    assert len(merged.source_pins)==2
    with pytest.raises(ValueError):
        MigrationTargetMapRecord("map:bad",(source1,),rule,(target1,),MigrationDisposition.MERGED,())


def test_effective_migration_rule_supersession_is_per_rule_identity():
    a1=_rule("rule:a",1,active=True)
    a2=_rule("rule:a",2,1,active=True)
    b1=_rule("rule:b",1,active=True)
    registry=MigrationRuleRegistry((a1,a2,b1))
    assert {(r.rule_ref,r.revision) for r in registry.rules} == {("rule:a",2),("rule:b",1)}


def test_transformer_registry_handles_generators_without_false_duplicate_error():
    class T:
        transformer_ref="transformer:test"
        transformer_revision="1"
    registry=MigrationTransformerRegistry(iter((T(),)))
    assert registry.require(_rule()) is not None


def test_merge_target_write_uses_all_map_sources_for_dependency_lineage():
    import inspect
    from cemm.v350.migration.coordinator import MigrationCommitCoordinator
    source=inspect.getsource(MigrationCommitCoordinator.commit_batch)
    assert "lineage_sources=map_record.source_pins" in source.replace(" ","")
