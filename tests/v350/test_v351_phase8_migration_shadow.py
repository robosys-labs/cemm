from __future__ import annotations

from cemm.migration.v351_csir_compat import (
    LegacyCompatibilityCompiler,
    LegacyExactAuthorityMap,
    MigrationClassification,
    Stage5ShadowComparator,
)
from cemm.v350.csir import ExactAuthorityPin
from cemm.v350.uol.model import Referent
from cemm.v350.schema.model import MeaningSchema


def test_unknown_legacy_object_is_quarantined_and_never_fallback():
    compiler = LegacyCompatibilityCompiler(
        LegacyExactAuthorityMap({}, {}, {}, {}, {}, {})
    )
    report = compiler.compile_records((object(),))
    assert report.classification is MigrationClassification.QUARANTINED
    assert report.graph is None


def test_shadow_report_is_observation_only():
    compiler = LegacyCompatibilityCompiler(
        LegacyExactAuthorityMap({}, {}, {}, {}, {}, {})
    )
    comparator = Stage5ShadowComparator(compiler)
    report = comparator.compare(((Referent("r"),),), ())
    assert report.shadow_only is True
    assert not hasattr(report, "authoritative_candidates")


def test_explicit_deprecated_record_is_classified_without_compilation():
    record = Referent("legacy:retired")
    compiler = LegacyCompatibilityCompiler(
        LegacyExactAuthorityMap({}, {}, {}, {}, {}, {}),
        deprecated_record_refs=frozenset({"legacy:retired"}),
    )
    report = compiler.compile_records((record,))
    assert report.classification is MigrationClassification.DEPRECATED
    assert report.graph is None


def test_empty_legacy_record_group_is_not_classified_lossless():
    compiler = LegacyCompatibilityCompiler(LegacyExactAuthorityMap({}, {}, {}, {}, {}, {}))
    report = compiler.compile_records(())
    assert report.classification is MigrationClassification.QUARANTINED
    assert "empty-legacy-record-group" in report.reason_refs


def test_schema_authority_migration_requires_content_bound_split_mapping():
    schema = MeaningSchema("schema:legacy", "legacy-key")
    compiler = LegacyCompatibilityCompiler(LegacyExactAuthorityMap({}, {}, {}, {}, {}, {}))
    report = compiler.compile_records((schema,))
    assert report.classification is MigrationClassification.REQUIRES_EXPLICIT_INTERPRETATION
    assert any("missing-reviewed-source-fingerprint" in reason for reason in report.reason_refs)
    assert any("missing-exact-schema-pin" in reason for reason in report.reason_refs)
