"""Boot validation — independent property tests, failure/downgrade policy.

Import boundary: model + schema + foundations + boot submodules only.

Architectural guardrails (SEMANTIC_FOUNDATIONS.md §5):
- The same package may not self-certify solely by supplying its own
  example/expected graph pairs. Boot validation includes kernel invariants
  and independently implemented property tests.
- Failure policy:
  - failed representation/value/foundational-predicate semantics halt boot
    or enter explicit diagnostic-safe mode;
  - failed optional boot concepts load opaque/provisional and downgrade dependents;
  - no failing schema silently activates.

Boot validation runs independent property/invariant tests for each boot schema.
A boot schema's own example/expected pairs count for structure only — they
cannot independently certify discrimination, truth, or promotion (AGENTS.md §7.3).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Protocol

from .manifest import (
    BootSchemaEntry,
    BootSchemaTier,
    FoundationManifest,
    build_boot_manifest,
)
from ..schema.store import SemanticSchemaStore
from ..schema.envelope import SchemaEnvelope
from ..schema.activation import ActivationResult, ActivationStatus


# ── Validation result types ────────────────────────────────────────


class ValidationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    OPAQUE = "opaque"  # loaded as opaque/provisional due to failure


class BootStatus(str, Enum):
    READY = "ready"
    DIAGNOSTIC_SAFE = "diagnostic_safe"
    HALTED = "halted"


@dataclass(frozen=True, slots=True)
class PropertyTestResult:
    """Result of a single independent property test."""
    test_name: str
    target_record_id: str
    status: ValidationStatus
    detail: str = ""


@dataclass(frozen=True, slots=True)
class SchemaValidationResult:
    """Validation result for a single boot schema."""
    record_id: str
    semantic_key: str
    tier: BootSchemaTier
    status: ValidationStatus
    property_test_results: tuple[PropertyTestResult, ...] = ()
    detail: str = ""
    loaded_as: str = "candidate"  # candidate, provisional, opaque, active


@dataclass(frozen=True, slots=True)
class BootValidationReport:
    """Complete boot validation report."""
    manifest_fingerprint: str
    status: BootStatus
    schema_results: tuple[SchemaValidationResult, ...] = ()
    foundation_tests_passed: bool = True
    halted_reasons: tuple[str, ...] = ()
    diagnostic_reasons: tuple[str, ...] = ()
    opaque_count: int = 0
    provisional_count: int = 0
    active_count: int = 0


# ── Property test protocol ─────────────────────────────────────────


class PropertyTest(Protocol):
    """Protocol for independent property/invariant tests.

    A property test is an independently implemented test that checks
    a kernel invariant — not the boot schema's own example/expected pairs.
    """
    name: str
    def run(self, store: SemanticSchemaStore, entry: BootSchemaEntry) -> PropertyTestResult: ...


# ── Built-in foundation property tests ─────────────────────────────


def _test_envelope_has_provenance(
    store: SemanticSchemaStore, entry: BootSchemaEntry
) -> PropertyTestResult:
    """Every boot schema must have field-level boot provenance."""
    env = entry.envelope
    if env.provenance.source_id == "boot":
        return PropertyTestResult(
            test_name="has_boot_provenance",
            target_record_id=entry.record_id,
            status=ValidationStatus.PASSED,
        )
    return PropertyTestResult(
        test_name="has_boot_provenance",
        target_record_id=entry.record_id,
        status=ValidationStatus.FAILED,
        detail=f"Provenance source_id is {env.provenance.source_id!r}, expected 'boot'",
    )


def _test_envelope_has_grounding_spec(
    store: SemanticSchemaStore, entry: BootSchemaEntry
) -> PropertyTestResult:
    """Every boot schema must have a GroundingSpecification."""
    if entry.grounding_spec is not None:
        return PropertyTestResult(
            test_name="has_grounding_spec",
            target_record_id=entry.record_id,
            status=ValidationStatus.PASSED,
        )
    return PropertyTestResult(
        test_name="has_grounding_spec",
        target_record_id=entry.record_id,
        status=ValidationStatus.FAILED,
        detail="Missing GroundingSpecification",
    )


def _test_envelope_has_manifest_version(
    store: SemanticSchemaStore, entry: BootSchemaEntry
) -> PropertyTestResult:
    """Every boot schema must have a manifest version."""
    if entry.manifest_version > 0:
        return PropertyTestResult(
            test_name="has_manifest_version",
            target_record_id=entry.record_id,
            status=ValidationStatus.PASSED,
        )
    return PropertyTestResult(
        test_name="has_manifest_version",
        target_record_id=entry.record_id,
        status=ValidationStatus.FAILED,
        detail="Missing or zero manifest version",
    )


def _test_dependencies_resolve(
    store: SemanticSchemaStore, entry: BootSchemaEntry
) -> PropertyTestResult:
    """Typed dependencies must resolve to registered schemas."""
    for dep in entry.dependencies:
        if store.get(dep.target_schema_ref) is None:
            # Dependencies may not be registered yet during early boot
            # This is a warning, not a hard failure
            return PropertyTestResult(
                test_name="dependencies_resolve",
                target_record_id=entry.record_id,
                status=ValidationStatus.FAILED,
                detail=f"Dependency {dep.target_schema_ref} not found in store",
            )
    return PropertyTestResult(
        test_name="dependencies_resolve",
        target_record_id=entry.record_id,
        status=ValidationStatus.PASSED,
    )


def _test_not_self_certified(
    store: SemanticSchemaStore, entry: BootSchemaEntry
) -> PropertyTestResult:
    """Boot example pairs cannot self-certify.

    A boot schema's own example/expected pairs count for structure only.
    They cannot independently certify discrimination, truth, or promotion.
    This test verifies that the entry has property_test_refs that are
    independent of the schema's own definition.
    """
    # Property test refs should exist and not be the schema itself
    if not entry.property_test_refs:
        # No property tests — this is acceptable for optional schemas
        # but they cannot self-certify
        if entry.tier == BootSchemaTier.OPTIONAL:
            return PropertyTestResult(
                test_name="not_self_certified",
                target_record_id=entry.record_id,
                status=ValidationStatus.PASSED,
                detail="Optional schema without property tests — loads as opaque",
            )
        return PropertyTestResult(
            test_name="not_self_certified",
            target_record_id=entry.record_id,
            status=ValidationStatus.FAILED,
            detail="Required/foundation schema has no independent property tests",
        )
    # Check that property test refs are not the schema itself
    for ref in entry.property_test_refs:
        if ref == entry.record_id:
            return PropertyTestResult(
                test_name="not_self_certified",
                target_record_id=entry.record_id,
                status=ValidationStatus.FAILED,
                detail="Schema references itself as property test — self-certification forbidden",
            )
    return PropertyTestResult(
        test_name="not_self_certified",
        target_record_id=entry.record_id,
        status=ValidationStatus.PASSED,
    )


# ── Foundation property tests ──────────────────────────────────────


def _test_value_types_registered(
    store: SemanticSchemaStore, entry: BootSchemaEntry
) -> PropertyTestResult:
    """Foundation value types must be registered."""
    from ..foundations.values import default_value_types
    types = default_value_types()
    if len(types) >= 10:
        return PropertyTestResult(
            test_name="value_types_registered",
            target_record_id="foundation:values",
            status=ValidationStatus.PASSED,
            detail=f"{len(types)} value types registered",
        )
    return PropertyTestResult(
        test_name="value_types_registered",
        target_record_id="foundation:values",
        status=ValidationStatus.FAILED,
        detail=f"Only {len(types)} value types registered, expected >= 10",
    )


def _test_predicates_registered(
    store: SemanticSchemaStore, entry: BootSchemaEntry
) -> PropertyTestResult:
    """Foundation predicates must be registered."""
    from ..foundations.predicates import foundational_predicates
    from ..foundations.epistemic_predicates import epistemic_predicates
    fps = foundational_predicates()
    eps = epistemic_predicates()
    total = len(fps) + len(eps)
    if total >= 20:
        return PropertyTestResult(
            test_name="predicates_registered",
            target_record_id="foundation:predicates",
            status=ValidationStatus.PASSED,
            detail=f"{total} predicates registered",
        )
    return PropertyTestResult(
        test_name="predicates_registered",
        target_record_id="foundation:predicates",
        status=ValidationStatus.FAILED,
        detail=f"Only {total} predicates registered, expected >= 20",
    )


# ── Boot validator ─────────────────────────────────────────────────


class BootValidator:
    """Validates boot schemas with independent property tests.

    The boot validator runs independent property/invariant tests for each
    boot schema. It applies the failure/downgrade policy:

    - foundation failure → halt or diagnostic-safe mode
    - required failure → diagnostic-safe mode
    - optional failure → load as opaque/provisional, downgrade dependents
    - no failing schema silently activates
    """

    def __init__(self) -> None:
        self._property_tests: list[tuple[str, Callable[[SemanticSchemaStore, BootSchemaEntry], PropertyTestResult]]] = [
            ("has_boot_provenance", _test_envelope_has_provenance),
            ("has_grounding_spec", _test_envelope_has_grounding_spec),
            ("has_manifest_version", _test_envelope_has_manifest_version),
            ("dependencies_resolve", _test_dependencies_resolve),
            ("not_self_certified", _test_not_self_certified),
        ]
        self._foundation_tests: list[tuple[str, Callable[[SemanticSchemaStore, BootSchemaEntry], PropertyTestResult]]] = [
            ("value_types_registered", _test_value_types_registered),
            ("predicates_registered", _test_predicates_registered),
        ]

    def validate_entry(
        self,
        store: SemanticSchemaStore,
        entry: BootSchemaEntry,
    ) -> SchemaValidationResult:
        """Validate a single boot schema entry."""
        results: list[PropertyTestResult] = []
        all_passed = True

        for test_name, test_fn in self._property_tests:
            result = test_fn(store, entry)
            results.append(result)
            if result.status == ValidationStatus.FAILED:
                all_passed = False

        if all_passed:
            return SchemaValidationResult(
                record_id=entry.record_id,
                semantic_key=entry.semantic_key,
                tier=entry.tier,
                status=ValidationStatus.PASSED,
                property_test_results=tuple(results),
                loaded_as="candidate",  # Ready for activation assessment
            )

        # Apply failure policy based on tier
        if entry.tier == BootSchemaTier.FOUNDATION:
            return SchemaValidationResult(
                record_id=entry.record_id,
                semantic_key=entry.semantic_key,
                tier=entry.tier,
                status=ValidationStatus.FAILED,
                property_test_results=tuple(results),
                loaded_as="rejected",
                detail="Foundation schema failed validation — boot must halt",
            )
        elif entry.tier == BootSchemaTier.REQUIRED:
            return SchemaValidationResult(
                record_id=entry.record_id,
                semantic_key=entry.semantic_key,
                tier=entry.tier,
                status=ValidationStatus.FAILED,
                property_test_results=tuple(results),
                loaded_as="provisional",
                detail="Required schema failed validation — diagnostic-safe mode",
            )
        else:  # OPTIONAL
            return SchemaValidationResult(
                record_id=entry.record_id,
                semantic_key=entry.semantic_key,
                tier=entry.tier,
                status=ValidationStatus.OPAQUE,
                property_test_results=tuple(results),
                loaded_as="opaque",
                detail="Optional schema failed validation — loaded as opaque",
            )

    def validate_foundations(
        self, store: SemanticSchemaStore
    ) -> tuple[PropertyTestResult, ...]:
        """Run foundation-level property tests."""
        results: list[PropertyTestResult] = []
        dummy_entry = BootSchemaEntry(
            record_id="foundation:test",
            semantic_key="foundation",
            schema_kind="foundation",
            tier=BootSchemaTier.FOUNDATION,
            envelope=SchemaEnvelope(
                record_id="foundation:test",
                semantic_key="foundation",
                schema_kind="foundation",
            ),
            grounding_spec=None,  # type: ignore[arg-type]
        )
        for test_name, test_fn in self._foundation_tests:
            results.append(test_fn(store, dummy_entry))
        return tuple(results)

    def validate_boot(
        self,
        store: SemanticSchemaStore,
        manifest: FoundationManifest | None = None,
    ) -> BootValidationReport:
        """Validate the complete boot manifest.

        Applies the failure policy:
        - foundation failure → halt
        - required failure → diagnostic-safe mode
        - optional failure → opaque/provisional
        """
        if manifest is None:
            manifest = build_boot_manifest()

        # Run foundation tests first
        foundation_results = self.validate_foundations(store)
        foundation_passed = all(
            r.status == ValidationStatus.PASSED for r in foundation_results
        )

        halted_reasons: list[str] = []
        diagnostic_reasons: list[str] = []
        schema_results: list[SchemaValidationResult] = []
        opaque_count = 0
        provisional_count = 0
        active_count = 0

        # If foundations fail, halt
        if not foundation_passed:
            failed = [r for r in foundation_results if r.status == ValidationStatus.FAILED]
            for f in failed:
                halted_reasons.append(f"Foundation test {f.test_name} failed: {f.detail}")

            # Still validate schemas for reporting, but boot will halt
            for entry in manifest.entries:
                result = self.validate_entry(store, entry)
                schema_results.append(result)
                if result.loaded_as == "opaque":
                    opaque_count += 1
                elif result.loaded_as == "provisional":
                    provisional_count += 1

            return BootValidationReport(
                manifest_fingerprint=manifest.fingerprint(),
                status=BootStatus.HALTED,
                schema_results=tuple(schema_results),
                foundation_tests_passed=False,
                halted_reasons=tuple(halted_reasons),
                opaque_count=opaque_count,
                provisional_count=provisional_count,
            )

        # Validate each boot schema entry
        for entry in manifest.entries:
            result = self.validate_entry(store, entry)
            schema_results.append(result)

            if result.status == ValidationStatus.FAILED:
                if entry.tier == BootSchemaTier.FOUNDATION:
                    halted_reasons.append(
                        f"Foundation schema {entry.record_id} failed: {result.detail}"
                    )
                elif entry.tier == BootSchemaTier.REQUIRED:
                    diagnostic_reasons.append(
                        f"Required schema {entry.record_id} failed: {result.detail}"
                    )
            elif result.status == ValidationStatus.OPAQUE:
                opaque_count += 1
            elif result.loaded_as == "provisional":
                provisional_count += 1
            elif result.loaded_as == "active":
                active_count += 1

        # Determine overall boot status
        if halted_reasons:
            status = BootStatus.HALTED
        elif diagnostic_reasons:
            status = BootStatus.DIAGNOSTIC_SAFE
        else:
            status = BootStatus.READY

        return BootValidationReport(
            manifest_fingerprint=manifest.fingerprint(),
            status=status,
            schema_results=tuple(schema_results),
            foundation_tests_passed=True,
            halted_reasons=tuple(halted_reasons),
            diagnostic_reasons=tuple(diagnostic_reasons),
            opaque_count=opaque_count,
            provisional_count=provisional_count,
            active_count=active_count,
        )

    def register_boot_schemas(
        self,
        store: SemanticSchemaStore,
        manifest: FoundationManifest | None = None,
        report: BootValidationReport | None = None,
    ) -> tuple[int, int]:
        """Register boot schemas into the store based on validation report.

        Only schemas that passed validation (or are loaded as opaque/provisional)
        are registered. No failing schema silently activates.

        Returns (registered_count, rejected_count).
        """
        if manifest is None:
            manifest = build_boot_manifest()
        if report is None:
            report = self.validate_boot(store, manifest)

        registered = 0
        rejected = 0

        for entry, result in zip(manifest.entries, report.schema_results):
            if result.loaded_as == "rejected":
                rejected += 1
                continue

            # Register the envelope
            from dataclasses import replace
            env = replace(entry.envelope, status=result.loaded_as)
            store.register(env, dependencies=entry.dependencies)
            registered += 1

        return registered, rejected
