"""Phase 3 gate tests: Foundations and boot validation.

Gates (from IMPLEMENTATION_PLAN.md Phase 3):
- a failing formal foundation halts or enters explicit diagnostic-safe mode;
- failing optional boot concepts remain opaque/provisional;
- boot example pairs cannot self-certify.

Additional guardrail tests from SEMANTIC_FOUNDATIONS.md:
- Kernel value types have identity, normalization, comparison, contradiction, serialization
- Foundational predicates have type signatures and truth/query behavior
- Epistemic predicates are ordinary predicates over ordinary records
- Boot schemas have ordinary representation, boot provenance, grounding spec, manifest version
- Adapter observation contracts record input/output type, verification, version, permission
- Version fingerprints change on foundation version change
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from cemm.kernel.foundations.values import (
    BooleanType, EnumType, TextType, IdentifierType, QuantityType,
    SetType, OrderedSequenceType, TimePointType, TimeIntervalType,
    CoordinateType, ProbabilityType, DistributionType,
    Quantity, TimeInterval, Coordinate, Distribution,
    ValueKind, default_value_types,
)
from cemm.kernel.foundations.predicates import (
    foundational_predicates, foundational_roles,
)
from cemm.kernel.foundations.epistemic_predicates import (
    epistemic_predicates, epistemic_roles,
)
from cemm.kernel.boot.manifest import (
    BootSchemaEntry, BootSchemaTier, FoundationManifest,
    build_boot_manifest, all_boot_entries,
    boot_entity_kinds, boot_contexts, boot_cognitive_operations,
    boot_communicative_operations, boot_policies, boot_metalanguage,
)
from cemm.kernel.boot.validation import (
    BootValidator, BootValidationReport, BootStatus,
    ValidationStatus, SchemaValidationResult, PropertyTestResult,
)
from cemm.kernel.schema.store import SemanticSchemaStore
from cemm.kernel.schema.envelope import SchemaEnvelope, SchemaDependency
from cemm.kernel.schema.grounding_spec import GroundingSpecification
from cemm.kernel.schema.predicate import PredicateSchema
from cemm.kernel.model.identity import Scope, ScopeLevel, Provenance, Permission


# ── Gate 1: failing foundation halts or diagnostic-safe ────────────


def test_failing_foundation_halts_boot():
    """A failing formal foundation must halt or enter diagnostic-safe mode."""
    validator = BootValidator()
    store = SemanticSchemaStore()

    # Override foundation tests to simulate failure
    original_tests = validator._foundation_tests
    validator._foundation_tests = [(
        "failing_test",
        lambda s, e: PropertyTestResult(
            test_name="failing_test",
            target_record_id="foundation",
            status=ValidationStatus.FAILED,
            detail="Simulated foundation failure",
        ),
    )]

    report = validator.validate_boot(store)
    assert report.status == BootStatus.HALTED
    assert not report.foundation_tests_passed
    assert len(report.halted_reasons) > 0

    # Restore
    validator._foundation_tests = original_tests


def test_passing_foundations_proceed():
    """When foundations pass, boot should proceed (ready or diagnostic-safe)."""
    validator = BootValidator()
    store = SemanticSchemaStore()
    report = validator.validate_boot(store)
    assert report.foundation_tests_passed
    assert report.status in (BootStatus.READY, BootStatus.DIAGNOSTIC_SAFE)
    assert len(report.halted_reasons) == 0


# ── Gate 2: failing optional boot concepts remain opaque/provisional ──


def test_optional_failure_loads_opaque():
    """Failing optional boot concepts must load as opaque/provisional."""
    validator = BootValidator()
    store = SemanticSchemaStore()

    manifest = build_boot_manifest()
    report = validator.validate_boot(store, manifest)

    # Optional schemas that fail should be opaque
    for result in report.schema_results:
        if result.tier == BootSchemaTier.OPTIONAL and result.status == ValidationStatus.OPAQUE:
            assert result.loaded_as == "opaque"
            assert "opaque" in result.detail.lower() or "failed" in result.detail.lower()


def test_no_failing_schema_silently_activates():
    """No failing schema may silently activate."""
    validator = BootValidator()
    store = SemanticSchemaStore()
    manifest = build_boot_manifest()
    report = validator.validate_boot(store, manifest)

    for result in report.schema_results:
        if result.status in (ValidationStatus.FAILED, ValidationStatus.OPAQUE):
            assert result.loaded_as != "active", (
                f"Schema {result.record_id} failed but loaded as active!"
            )


# ── Gate 3: boot example pairs cannot self-certify ─────────────────


def test_self_certification_rejected():
    """A boot schema referencing itself as property test must fail."""
    from cemm.kernel.schema.envelope import SchemaEnvelope

    env = SchemaEnvelope(
        record_id="boot:self_cert:v1",
        semantic_key="self_cert",
        schema_kind="entity_kind",
        provenance=Provenance(source_id="boot", source_kind="boot"),
    )
    entry = BootSchemaEntry(
        record_id="boot:self_cert:v1",
        semantic_key="self_cert",
        schema_kind="entity_kind",
        tier=BootSchemaTier.REQUIRED,
        envelope=env,
        grounding_spec=GroundingSpecification(),
        property_test_refs=("boot:self_cert:v1",),  # Self-reference!
    )

    validator = BootValidator()
    store = SemanticSchemaStore()
    result = validator.validate_entry(store, entry)

    # Must fail — self-certification forbidden
    assert result.status == ValidationStatus.FAILED
    has_self_cert_fail = any(
        "self_cert" in r.test_name and r.status == ValidationStatus.FAILED
        for r in result.property_test_results
    )
    assert has_self_cert_fail


def test_no_property_tests_for_optional_is_ok():
    """Optional schemas without property tests load as opaque, not rejected."""
    from cemm.kernel.schema.envelope import SchemaEnvelope

    env = SchemaEnvelope(
        record_id="boot:no_tests:v1",
        semantic_key="no_tests",
        schema_kind="entity_kind",
        provenance=Provenance(source_id="boot", source_kind="boot"),
    )
    entry = BootSchemaEntry(
        record_id="boot:no_tests:v1",
        semantic_key="no_tests",
        schema_kind="entity_kind",
        tier=BootSchemaTier.OPTIONAL,
        envelope=env,
        grounding_spec=GroundingSpecification(),
    )

    validator = BootValidator()
    store = SemanticSchemaStore()
    result = validator.validate_entry(store, entry)

    # Should pass the self-cert test (optional without tests → opaque)
    assert result.status == ValidationStatus.PASSED or result.status == ValidationStatus.OPAQUE


# ── Value type tests ───────────────────────────────────────────────


def test_all_value_types_registered():
    """All 10+ kernel value types must be registered."""
    types = default_value_types()
    expected = {
        "boolean", "enum", "text", "identifier", "quantity",
        "set", "ordered_sequence", "time_point", "time_interval",
        "coordinate", "probability", "distribution",
    }
    assert expected.issubset(set(types.keys())), (
        f"Missing value types: {expected - set(types.keys())}"
    )


def test_boolean_normalize_and_contradict():
    """Boolean type must normalize and detect contradictions."""
    bt = BooleanType()
    assert bt.normalize("true") is True
    assert bt.normalize("false") is False
    assert bt.normalize(1) is True
    assert bt.normalize(0) is False
    assert bt.contradicts(True, False) is True
    assert bt.contradicts(True, True) is False
    assert bt.serialize(True) == "true"
    assert bt.identity_hash(True) != bt.identity_hash(False)


def test_quantity_normalize_and_compare():
    """Quantity type must normalize and compare with units."""
    qt = QuantityType(compatible_units=frozenset({"m", "cm"}))
    q1 = qt.normalize(Quantity(5.0, "m"))
    q2 = qt.normalize(Quantity(3.0, "m"))
    assert qt.compare(q1, q2) == 1  # 5m > 3m
    assert qt.contradicts(q1, q2) is True  # Different values, same unit
    assert qt.serialize(q1) == "5.0 m"


def test_time_point_normalize_utc():
    """Time point must normalize to UTC."""
    tp = TimePointType()
    naive = datetime(2024, 1, 1, 12, 0, 0)
    normalized = tp.normalize(naive)
    assert normalized.tzinfo is not None
    assert normalized.utcoffset() == timedelta(0)


def test_time_interval_contains_and_overlaps():
    """Time interval must support contains and overlaps."""
    ti = TimeInterval(
        start=datetime(2020, 1, 1, tzinfo=timezone.utc),
        end=datetime(2025, 12, 31, tzinfo=timezone.utc),
    )
    assert ti.contains(datetime(2023, 6, 1, tzinfo=timezone.utc))
    assert not ti.contains(datetime(2030, 1, 1, tzinfo=timezone.utc))

    other = TimeInterval(
        start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    assert ti.overlaps(other)


def test_probability_bounds():
    """Probability must be in [0, 1]."""
    pt = ProbabilityType()
    assert pt.normalize(0.5) == 0.5
    assert pt.normalize(1.0) == 1.0
    with pytest.raises(ValueError):
        pt.normalize(1.5)
    with pytest.raises(ValueError):
        pt.normalize(-0.1)


def test_distribution_sums_to_one():
    """Distribution probabilities must sum to 1.0."""
    dt = DistributionType()
    dist = dt.normalize({"a": 0.3, "b": 0.7})
    assert dist.outcomes == ("a", "b")
    assert abs(sum(dist.probabilities) - 1.0) < 1e-6
    with pytest.raises(ValueError):
        dt.normalize({"a": 0.5, "b": 0.6})  # Sums to 1.1


def test_set_contradicts_disjoint():
    """Sets contradict when disjoint."""
    st = SetType()
    a = st.normalize({1, 2, 3})
    b = st.normalize({4, 5})
    c = st.normalize({2, 3, 4})
    assert st.contradicts(a, b) is True  # Disjoint
    assert st.contradicts(a, c) is False  # Overlapping


def test_coordinate_frame_mismatch():
    """Coordinates in different frames cannot be compared."""
    ct = CoordinateType(dimensions=2)
    a = ct.normalize((1.0, 2.0))
    b = Coordinate((1.0, 2.0), frame="other")
    with pytest.raises(ValueError):
        ct.compare(a, b)


# ── Foundational predicate tests ───────────────────────────────────


def test_foundational_predicates_count():
    """All 17 foundational predicates must be defined."""
    preds = foundational_predicates()
    expected = {
        "same_identity", "different_identity", "instance_of",
        "occupies_role", "participates_in", "has_state",
        "occurs", "transitions", "located_at",
        "before", "after", "depends_on",
        "causes", "enables", "prevents",
        "refers_to", "represents",
    }
    assert set(preds.keys()) == expected


def test_epistemic_predicates_count():
    """All 8 epistemic/learning predicates must be defined."""
    preds = epistemic_predicates()
    expected = {
        "remembers", "has_access_to", "has_evidence_for",
        "understands", "uncertain_about", "means",
        "defines", "learns",
    }
    assert set(preds.keys()) == expected


def test_predicates_have_role_refs():
    """Every foundational predicate must have role references."""
    all_preds = {**foundational_predicates(), **epistemic_predicates()}
    for key, pred in all_preds.items():
        assert pred.role_refs, f"Predicate {key} has no role_refs"


def test_learns_requires_independent_evidence():
    """learns predicate must require independent sources — not self-attribution."""
    learns = epistemic_predicates()["learns"]
    assert learns.evidence_policy.minimum_evidence_count >= 2
    assert learns.evidence_policy.requires_independent_sources is True
    assert learns.evidence_policy.allows_self_attribution is False


def test_same_identity_supports_negation():
    """same_identity must support negation with contradictory semantics."""
    pred = foundational_predicates()["same_identity"]
    assert pred.polarity_behavior.supports_negation is True
    assert pred.polarity_behavior.negation_kind == "contradictory"


# ── Boot manifest tests ─────────────────────────────────────────────


def test_manifest_has_entries():
    """Boot manifest must have schema entries."""
    manifest = build_boot_manifest()
    assert len(manifest.entries) > 0
    assert manifest.foundation_version == "v3.4"


def test_manifest_fingerprint_stable():
    """Manifest fingerprint must be stable for same content."""
    m1 = build_boot_manifest()
    m2 = build_boot_manifest()
    assert m1.fingerprint() == m2.fingerprint()


def test_manifest_fingerprint_changes_on_version():
    """Manifest fingerprint must change when version changes."""
    m1 = build_boot_manifest()
    from dataclasses import replace
    m2 = replace(m1, foundation_version="v3.5")
    assert m1.fingerprint() != m2.fingerprint()


def test_boot_schemas_have_boot_provenance():
    """Every boot schema must have boot provenance."""
    entries = all_boot_entries()
    for entry in entries:
        assert entry.envelope.provenance.source_id == "boot", (
            f"Schema {entry.record_id} lacks boot provenance"
        )


def test_boot_schemas_have_grounding_spec():
    """Every boot schema must have a GroundingSpecification."""
    entries = all_boot_entries()
    for entry in entries:
        assert entry.grounding_spec is not None, (
            f"Schema {entry.record_id} lacks GroundingSpecification"
        )


def test_boot_schemas_have_manifest_version():
    """Every boot schema must have a manifest version."""
    entries = all_boot_entries()
    for entry in entries:
        assert entry.manifest_version > 0, (
            f"Schema {entry.record_id} has no manifest version"
        )


def test_boot_entity_kinds_present():
    """Boot entity kinds must include the specified concepts."""
    entries = boot_entity_kinds()
    keys = {e.semantic_key for e in entries}
    expected = {
        "physical_entity", "biological_entity", "person",
        "agent", "software_system", "organization",
        "place", "information_object", "group", "goal",
    }
    assert expected.issubset(keys)


def test_boot_contexts_present():
    """Boot contexts must include all context kinds."""
    entries = boot_contexts()
    keys = {e.semantic_key for e in entries}
    for kind in ["actual", "reported", "belief", "hypothetical", "counterfactual", "simulated", "quoted", "desired"]:
        assert f"context:{kind}" in keys


def test_boot_cognitive_operations_present():
    """Boot cognitive operations must include core operations."""
    entries = boot_cognitive_operations()
    keys = {e.semantic_key for e in entries}
    for op in ["perceive", "interpret", "ground", "plan", "execute", "learn", "respond"]:
        assert f"op:{op}" in keys


def test_boot_communicative_operations_present():
    """Boot communicative operations must include all communicative forces."""
    entries = boot_communicative_operations()
    keys = {e.semantic_key for e in entries}
    for op in ["assert", "ask", "request", "direct", "acknowledge", "correct", "promise", "refuse"]:
        assert f"comm:{op}" in keys


# ── Boot registration tests ────────────────────────────────────────


def test_register_boot_schemas():
    """Boot schemas should register into the store after validation."""
    validator = BootValidator()
    store = SemanticSchemaStore()
    manifest = build_boot_manifest()
    report = validator.validate_boot(store, manifest)

    registered, rejected = validator.register_boot_schemas(store, manifest, report)

    # Should have registered most schemas
    assert registered > 0
    # Store should have records
    assert len(store) > 0


def test_no_failing_schema_activated_in_store():
    """After registration, no failed schema should be active."""
    validator = BootValidator()
    store = SemanticSchemaStore()
    manifest = build_boot_manifest()
    report = validator.validate_boot(store, manifest)
    validator.register_boot_schemas(store, manifest, report)

    for result in report.schema_results:
        if result.status in (ValidationStatus.FAILED, ValidationStatus.OPAQUE):
            env = store.get(result.record_id)
            if env is not None:
                assert env.status != "active", (
                    f"Failed schema {result.record_id} was activated!"
                )


# ── Import boundary ────────────────────────────────────────────────


def test_foundations_imports_no_engine():
    """Foundations must not import any engine module."""
    import cemm.kernel.foundations.values as values_mod
    import cemm.kernel.foundations.predicates as preds_mod
    import cemm.kernel.foundations.epistemic_predicates as epist_mod

    forbidden = [
        "cemm.kernel.semantic_kernel_runtime",
        "cemm.kernel.meaning_perceptor",
        "cemm.kernel.meaning_graph_builder",
        "cemm.memory.durable_semantic_store",
    ]
    for mod in [values_mod, preds_mod, epist_mod]:
        source = open(mod.__file__, encoding="utf-8").read()
        for f in forbidden:
            assert f not in source, f"{mod.__name__} imports forbidden module {f}"


def test_boot_imports_no_engine():
    """Boot modules must not import any engine module."""
    import cemm.kernel.boot.manifest as manifest_mod
    import cemm.kernel.boot.validation as validation_mod

    forbidden = [
        "cemm.kernel.semantic_kernel_runtime",
        "cemm.kernel.meaning_perceptor",
        "cemm.kernel.meaning_graph_builder",
        "cemm.memory.durable_semantic_store",
    ]
    for mod in [manifest_mod, validation_mod]:
        source = open(mod.__file__, encoding="utf-8").read()
        for f in forbidden:
            assert f not in source, f"{mod.__name__} imports forbidden module {f}"
