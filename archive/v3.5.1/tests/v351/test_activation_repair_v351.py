from __future__ import annotations

from types import SimpleNamespace

from cemm.v350.csir.authority_v351 import AuthoritySnapshotV351
from cemm.v350.csir.runtime_projection_v351 import project_runtime_semantic_authority_v351
from cemm.v350.language.registry import LanguageRegistry
from cemm.v350.schema.model import (
    RelationSchema, SchemaLifecycleStatus, SchemaProvenance,
    UseDecision, UseOperation, UseProfile,
)
from cemm.v350.schema.registry import SchemaRegistry


class _Snapshot:
    authority_generation = 1
    authority_fingerprint = "authority:test"
    read_generation = SimpleNamespace(
        authority_generation=1, authority_fingerprint="authority:test",
        cognitive_fingerprint="cognitive:test",
    )


class _SnapshotCM:
    def __enter__(self): return _Snapshot()
    def __exit__(self, *args): return False


class _SchemaRepo:
    def __init__(self, registry): self._registry = registry
    def registry(self, *, snapshot=None): return self._registry


class _LanguageRepo:
    def __init__(self, registry): self._registry = registry
    def registry(self, *, snapshot=None): return self._registry


class _Store:
    def __init__(self, schemas):
        self.repositories = SimpleNamespace(
            schemas=_SchemaRepo(SchemaRegistry(schemas)),
            language=_LanguageRepo(LanguageRegistry()),
        )
    def current_authority_snapshot(self):
        return SimpleNamespace(generation=1, authority_fingerprint="authority:test")
    def snapshot(self): return _SnapshotCM()
    def assert_snapshot(self, snapshot): return None


def _active_relation():
    return RelationSchema(
        schema_ref="relation:test",
        semantic_key="test_relation",
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        revision=1,
        permission_ref="public",
        provenance=SchemaProvenance(source_refs=("source:test",), evidence_refs=("evidence:test",)),
        use_profile=UseProfile.from_mapping({UseOperation.COMPOSE: UseDecision.ALLOW}),
    )


def test_restart_projection_reconstructs_exact_semantic_definition_and_public_permission():
    store = _Store((_active_relation(),))
    base = AuthoritySnapshotV351(1, "authority:test")
    first = project_runtime_semantic_authority_v351(store, base)
    second = project_runtime_semantic_authority_v351(store, base)
    assert first.snapshot_fingerprint == second.snapshot_fingerprint
    assert len(first.semantic_definitions) == 1
    definition = first.semantic_definitions[0]
    profile = first.select_operational_profile(
        definition.definition_pin,
        operation="compose",
        permission_ref="conversation",
    )
    assert profile.lifecycle_status == "active"
    allowed = first.select_use_authorizations(
        definition_pin=definition.definition_pin,
        profile_pin=profile.profile_pin,
        operation="compose",
        context_ref="conversation",
        permission_ref="conversation",
    )
    assert allowed


def test_signed_supplement_observation_model_resolves_exact_output_definition():
    store = _Store((_active_relation(),))
    base = AuthoritySnapshotV351(1, "authority:test")
    supplement = {
        "schema_version": 1,
        "auxiliary_exact_pins": [],
        "observation_models": [{
            "model_ref": "observation-model:test",
            "revision": 1,
            "modality_ref": "generic_sensor",
            "output_definitions": [{"schema_ref": "relation:test", "revision": 1}],
            "calibration": {
                "kind": "calibration",
                "namespace": "test",
                "ref": "calibration:test",
                "revision": 1,
                "content_hash": "a" * 64,
            },
            "evidence_refs": ["evidence:calibration:test"],
        }],
    }
    snapshot = project_runtime_semantic_authority_v351(store, base, supplement=supplement)
    assert len(snapshot.observation_models) == 1
    model = snapshot.observation_models[0]
    assert model.output_definition_pins == (snapshot.semantic_definitions[0].definition_pin,)
    assert model.calibration_pin is not None


def test_uol_namespace_is_compatibility_alias_not_distinct_runtime_record_class():
    from cemm.v350.semantic_records.model import Referent as CanonicalReferent
    from cemm.v350.uol.model import Referent as LegacyAlias
    assert LegacyAlias is CanonicalReferent

def test_canonical_service_inventory_requires_explicit_implementation_identity():
    from importlib import import_module
    from cemm.v350.finalization.service_authority_v351 import SERVICE_SPECS
    for slot, class_path, required_methods in SERVICE_SPECS:
        module_name, symbol = class_path.split(":", 1)
        cls = getattr(import_module(module_name), symbol)
        assert getattr(cls, "RUNTIME_ABI", None) == "v351", (slot, class_path)
        kind = getattr(cls, "SERVICE_KIND", None)
        assert isinstance(kind, str) and kind.strip(), (slot, class_path)
        for method in required_methods:
            assert callable(getattr(cls, method, None)), (slot, class_path, method)


def test_canonical_record_namespace_excludes_uol_graph_and_response_uol():
    import cemm.v350.semantic_records.model as records
    from cemm.v350.response import records_model_v351 as response_records
    assert not hasattr(records, "UOLGraph")
    assert not hasattr(response_records, "ResponseUOLRecord")


def test_language_candidate_abi_preserves_exact_derivation_revisions():
    from cemm.v350.language.model import LexemeCandidate, SemanticContribution, SenseCandidate
    from cemm.v350.language.model import SenseTargetKind, SemanticContributionKind
    lexeme = LexemeCandidate(
        candidate_ref="lc", form_candidate_ref="fc", lexeme_ref="lexeme:x",
        lexeme_revision=2, language_tag="en", confidence=1.0,
        feature_values=(), evidence_refs=("e",), link_ref="form-lexeme:x", link_revision=3,
    )
    assert (lexeme.link_ref, lexeme.link_revision) == ("form-lexeme:x", 3)
    contribution = SemanticContribution(
        contribution_ref="c", contribution_kind=SemanticContributionKind.TARGET,
        spec_ref="spec:x", spec_revision=4, target_kind=SenseTargetKind.SCHEMA,
        target_ref="relation:x", target_revision=1, evidence_refs=("e",),
    )
    sense = SenseCandidate(
        candidate_ref="sc", form_candidate_ref="fc", sense_ref="sense:x",
        sense_revision=5, target_kind=SenseTargetKind.SCHEMA, target_ref="relation:x",
        target_revision=1, target_schema_class=None, confidence=1.0, evidence_refs=("e",),
        contributions=(contribution,), lexeme_ref="lexeme:x", lexeme_revision=2,
        authority_path="lexeme", authority_ref="lexeme-sense:x", authority_revision=6,
    )
    assert sense.lexeme_revision == 2
    assert sense.authority_revision == 6
    assert sense.contributions[0].spec_revision == 4


def test_canonical_authority_set_fingerprints_are_deterministic():
    from cemm.v350.csir.runtime_projection_v351 import (
        CANONICAL_AUTHORITY_SET_REFS,
        canonical_authority_set_fingerprints_v351,
    )
    first = canonical_authority_set_fingerprints_v351()
    second = canonical_authority_set_fingerprints_v351()
    assert first == second
    assert set(first) == set(CANONICAL_AUTHORITY_SET_REFS)
    assert all(len(value) == 64 for value in first.values())

