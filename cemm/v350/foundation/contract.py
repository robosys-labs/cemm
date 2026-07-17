"""Contract-driven audit of the reviewed Phase-6 foundation package."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from ..data import SourcePackageLoader, SourceRecord
from ..schema.model import (
    ActionSchema,
    DiscourseActSchema,
    EventSchema,
    FacetEntitlement,
    FacetSchema,
    PropertySchema,
    RelationSchema,
    RoleSchema,
    FunctionSchema,
    ReferentTypeSchema,
    ResponsePolicySchema,
    SchemaClass,
    SchemaLifecycleStatus,
    StateDimensionSchema,
    StateValueSchema,
    OperatorSchema,
    StorageKind,
    UseOperation,
    canonical_data,
    semantic_fingerprint,
)
from ..schema.registry import SchemaRegistry
from ..storage.model import AssignmentStatus, RecordKind
from ..uol.model import (
    CapabilityStatus, ClaimForce, IdentityStatus, ImportanceClass, OccurrenceStatus, Polarity,
    QuotedLiteral, Reversibility, SemanticApplication, Valence,
)
from .runtime import RuntimeComponentResolutionError, resolve_runtime_component
from .model import (
    AuditSeverity,
    FoundationAuditIssue,
    FoundationAuditReport,
    FoundationContract,
    FoundationContractError,
)


_FORBIDDEN_SURFACE_FIELDS = frozenset({
    "surfaces", "template", "templates", "words", "phrases",
    "lexeme", "lexemes", "sentence", "sentences",
})
_REQUIRED_ROOT_STORAGE_KINDS = frozenset(StorageKind)


def load_foundation_contract(path: str | Path) -> FoundationContract:
    contract_path = Path(path)
    payload = json.loads(contract_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise FoundationContractError("foundation contract must be a JSON object")

    def tuple_map(value: Any, label: str) -> dict[str, tuple[str, ...]]:
        if not isinstance(value, Mapping):
            raise FoundationContractError(f"{label} must be an object")
        return {
            str(key): tuple(str(item) for item in items)
            for key, items in value.items()
        }

    return FoundationContract(
        contract_ref=str(payload["contract_ref"]),
        expected_type_parents=tuple_map(payload.get("expected_type_parents", {}), "expected_type_parents"),
        expected_schema_parents=tuple_map(payload.get("expected_schema_parents", {}), "expected_schema_parents"),
        required_schema_metadata={
            str(ref): dict(values)
            for ref, values in dict(payload.get("required_schema_metadata", {})).items()
        },
        required_schema_groups=tuple_map(payload.get("required_schema_groups", {}), "required_schema_groups"),
        required_entitlement_refs=tuple(map(str, payload.get("required_entitlement_refs", ()))),
        required_referent_refs=tuple(map(str, payload.get("required_referent_refs", ()))),
        required_capability_refs=tuple(map(str, payload.get("required_capability_refs", ()))),
        required_competence_case_refs=tuple(map(str, payload.get("required_competence_case_refs", ()))),
        expected_record_counts={str(key): int(value) for key, value in dict(payload.get("expected_record_counts", {})).items()},
        expected_source_record_fingerprint=str(payload.get("expected_source_record_fingerprint", "")),
        forbidden_domain_semantic_keys=tuple(map(str, payload.get("forbidden_domain_semantic_keys", ()))),
        metadata=dict(payload.get("metadata", {})),
    )


class FoundationPackageAuditor:
    """Audit reviewed seed data without granting it runtime authority."""

    def __init__(self, contract: FoundationContract):
        self.contract = contract

    def audit(self, package_root: str | Path) -> FoundationAuditReport:
        root = Path(package_root).resolve()
        loader = SourcePackageLoader(root)
        records = loader.load()
        issues: list[FoundationAuditIssue] = []
        counts = Counter(item.record_kind.value for item in records)
        by_kind: dict[RecordKind, dict[str, list[SourceRecord]]] = {}
        for item in records:
            by_kind.setdefault(item.record_kind, {}).setdefault(item.record_ref, []).append(item)

        schemas = tuple(item.record for item in records if item.record_kind == RecordKind.SCHEMA)
        entitlements = tuple(
            item.record for item in records if item.record_kind == RecordKind.FACET_ENTITLEMENT
        )
        registry = SchemaRegistry(schemas, entitlements)
        validation = registry.validate()
        for item in validation.errors:
            self._error(issues, f"schema_{item.code}", item.target_ref, item.message)
        for item in validation.unresolved:
            self._error(issues, f"schema_{item.code}", item.target_ref, item.message)

        self._check_manifest(loader, issues)
        self._check_expected_record_counts(counts, issues)
        self._check_required_records(by_kind, registry, issues)
        self._check_type_graph(registry, issues)
        self._check_schema_contracts(registry, issues)
        self._check_seed_scope(records, registry, issues)
        self._check_record_provenance(records, issues)
        self._check_state_domains(registry, issues)
        self._check_native_axes(registry, issues)
        self._check_facet_boundaries(registry, issues)
        self._check_entitlement_domains(registry, issues)
        self._check_events(registry, issues)
        self._check_discourse(registry, issues)
        self._check_self_records(by_kind, registry, issues)
        self._check_defaults(by_kind, registry, issues)
        self._check_competence_cases(root, issues)

        source_fingerprint = semantic_fingerprint(
            "foundation-source-records",
            tuple(
                (
                    item.record_kind.value,
                    item.record_ref,
                    item.revision,
                    canonical_data(item.record),
                )
                for item in records
            ),
            64,
        )
        expected_source_fingerprint = self.contract.expected_source_record_fingerprint
        if not expected_source_fingerprint:
            self._error(
                issues,
                "source_fingerprint_contract_missing",
                self.contract.contract_ref,
                "reviewed source-record fingerprint is not pinned",
            )
        elif source_fingerprint != expected_source_fingerprint:
            self._error(
                issues,
                "source_fingerprint_mismatch",
                self.contract.contract_ref,
                f"expected {expected_source_fingerprint}, got {source_fingerprint}",
            )
        issues.sort(key=lambda item: (item.severity.value, item.code, item.target_ref, item.message))
        return FoundationAuditReport(
            contract_ref=self.contract.contract_ref,
            issues=tuple(issues),
            record_count=len(records),
            counts_by_kind=dict(sorted(counts.items())),
            manifest_fingerprint=loader.manifest.fingerprint,
            source_record_fingerprint=source_fingerprint,
        )

    def _check_manifest(self, loader: SourcePackageLoader, issues: list[FoundationAuditIssue]) -> None:
        metadata = dict(loader.manifest.metadata)
        required = {
            "phase": "6",
            "authority": "reviewed_source",
            "domain_light": True,
            "language_neutral": True,
            "foundation_contract_ref": self.contract.contract_ref,
        }
        for key, expected in required.items():
            actual = metadata.get(key)
            if str(actual).casefold() != str(expected).casefold():
                self._error(issues, "manifest_contract_mismatch", key, f"expected {expected!r}, got {actual!r}")

        pinned_files = {
            "foundation_contract_sha256": loader.package_root / "foundation_contract.json",
            "foundation_competence_sha256": loader.package_root / "competence" / "foundation.jsonl",
        }
        for key, path in pinned_files.items():
            expected = str(metadata.get(key) or "")
            if not expected:
                self._error(issues, "manifest_hash_missing", key, f"missing SHA-256 pin for {path.name}")
                continue
            actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
            if actual != expected:
                self._error(issues, "manifest_hash_mismatch", key, f"expected {expected}, got {actual}")

    def _check_expected_record_counts(
        self, counts: Mapping[str, int], issues: list[FoundationAuditIssue]
    ) -> None:
        if not self.contract.expected_record_counts:
            self._error(issues, "record_count_contract_missing", self.contract.contract_ref, "expected record counts are not pinned")
            return
        all_kinds = sorted(set(counts) | set(self.contract.expected_record_counts))
        for kind in all_kinds:
            actual = int(counts.get(kind, 0))
            expected = int(self.contract.expected_record_counts.get(kind, 0))
            if actual != expected:
                self._error(
                    issues,
                    "record_count_mismatch",
                    kind,
                    f"expected {expected} reviewed records, got {actual}",
                )

    def _check_required_records(
        self,
        by_kind: Mapping[RecordKind, Mapping[str, list[SourceRecord]]],
        registry: SchemaRegistry,
        issues: list[FoundationAuditIssue],
    ) -> None:
        for group, refs in self.contract.required_schema_groups.items():
            for ref in refs:
                schema = registry.maybe_authoritative_schema(ref)
                if schema is None:
                    self._error(issues, "missing_required_schema", ref, f"required by group {group}")
                elif schema.lifecycle_status != SchemaLifecycleStatus.ACTIVE:
                    self._error(issues, "required_schema_not_active", ref, schema.lifecycle_status.value)
        for ref in self.contract.required_entitlement_refs:
            try:
                item = registry.authoritative_entitlement(ref)
            except KeyError:
                self._error(issues, "missing_required_entitlement", ref, "required foundation entitlement")
                continue
            if item.lifecycle_status != SchemaLifecycleStatus.ACTIVE:
                self._error(issues, "required_entitlement_not_active", ref, item.lifecycle_status.value)
        for kind, refs in (
            (RecordKind.REFERENT, self.contract.required_referent_refs),
            (RecordKind.CAPABILITY_INSTANCE, self.contract.required_capability_refs),
        ):
            available = by_kind.get(kind, {})
            for ref in refs:
                if ref not in available:
                    self._error(issues, f"missing_required_{kind.value}", ref, "required by foundation contract")

    def _check_type_graph(self, registry: SchemaRegistry, issues: list[FoundationAuditIssue]) -> None:
        for type_ref, expected_parents in self.contract.expected_type_parents.items():
            schema = registry.maybe_authoritative_schema(type_ref)
            if not isinstance(schema, ReferentTypeSchema):
                self._error(issues, "missing_or_invalid_foundation_type", type_ref, "not an authoritative referent type")
                continue
            actual = tuple(sorted(item.parent_ref for item in schema.parent_links))
            if actual != tuple(sorted(expected_parents)):
                self._error(issues, "foundation_parent_mismatch", type_ref, f"expected {sorted(expected_parents)}, got {list(actual)}")
            try:
                closure = registry.type_closure(type_ref, schema.revision)
            except Exception as exc:
                self._error(issues, "foundation_type_closure_failed", type_ref, str(exc))
                continue
            if "type:referent" not in closure:
                self._error(issues, "foundation_type_not_rooted", type_ref, "closure does not include type:referent")
        root = registry.maybe_authoritative_schema("type:referent")
        if isinstance(root, ReferentTypeSchema) and root.storage_kinds != _REQUIRED_ROOT_STORAGE_KINDS:
            self._error(
                issues,
                "root_storage_kind_incomplete",
                root.schema_ref,
                f"expected all stable storage kinds, got {sorted(item.value for item in root.storage_kinds)}",
            )

    def _check_schema_contracts(
        self, registry: SchemaRegistry, issues: list[FoundationAuditIssue]
    ) -> None:
        for schema_ref, expected_parents in self.contract.expected_schema_parents.items():
            schema = registry.maybe_authoritative_schema(schema_ref)
            if schema is None:
                self._error(issues, "schema_parent_contract_missing", schema_ref, "schema is absent")
                continue
            actual = tuple(sorted(item.parent_ref for item in schema.parent_links))
            expected = tuple(sorted(expected_parents))
            if actual != expected:
                self._error(
                    issues,
                    "schema_parent_contract_mismatch",
                    schema_ref,
                    f"expected {expected}, got {actual}",
                )

        for schema_ref, expected_metadata in self.contract.required_schema_metadata.items():
            schema = registry.maybe_authoritative_schema(schema_ref)
            if schema is None:
                self._error(issues, "schema_metadata_contract_missing", schema_ref, "schema is absent")
                continue
            for key, expected in expected_metadata.items():
                actual = schema.metadata.get(key)
                if canonical_data(actual) != canonical_data(expected):
                    self._error(
                        issues,
                        "schema_metadata_contract_mismatch",
                        schema_ref,
                        f"metadata {key!r}: expected {expected!r}, got {actual!r}",
                    )

    def _check_seed_scope(
        self,
        records: Iterable[SourceRecord],
        registry: SchemaRegistry,
        issues: list[FoundationAuditIssue],
    ) -> None:
        forbidden = {item.casefold() for item in self.contract.forbidden_domain_semantic_keys}
        for schema in registry.iter_schemas(all_revisions=True):
            tokens = {
                token.casefold()
                for value in (schema.schema_ref, schema.semantic_key)
                for token in __import__("re").split(r"[:._\-]+", value)
                if token
            }
            matched = sorted(tokens.intersection(forbidden))
            if matched:
                self._error(issues, "domain_concept_seeded", schema.schema_ref, ",".join(matched))
            if not schema.provenance.created_by or not schema.provenance.source_refs:
                self._error(issues, "schema_provenance_incomplete", schema.schema_ref, "created_by and source_refs are required")
            if schema.metadata.get("foundation_layer") != "phase6":
                self._error(issues, "foundation_layer_missing", schema.schema_ref, "metadata.foundation_layer must be phase6")
        for item in records:
            matched = sorted(_string_tokens(canonical_data(item.record)).intersection(forbidden))
            if matched:
                self._error(
                    issues, "domain_concept_seeded", item.record_ref, ",".join(matched)
                )
            if item.record_kind == RecordKind.SEMANTIC_APPLICATION and isinstance(item.record, SemanticApplication):
                for binding in item.record.bindings:
                    for filler in binding.fillers:
                        if isinstance(filler, QuotedLiteral) and filler.language_tag != "und":
                            self._error(
                                issues, "language_specific_literal_in_foundation",
                                item.record_ref, filler.language_tag,
                            )
            for path in _forbidden_surface_paths(canonical_data(item.record)):
                self._error(
                    issues,
                    "surface_language_in_foundation",
                    item.record_ref,
                    f"language surface field at {path}",
                )

    def _check_record_provenance(
        self, records: Iterable[SourceRecord], issues: list[FoundationAuditIssue]
    ) -> None:
        for item in records:
            record = item.record
            if item.record_kind == RecordKind.FACET_ENTITLEMENT:
                provenance = record.provenance
                if not provenance.created_by or not provenance.source_refs:
                    self._error(
                        issues, "entitlement_provenance_incomplete", item.record_ref,
                        "created_by and source_refs are required",
                    )
            elif item.record_kind == RecordKind.REFERENT:
                if not record.provenance_refs:
                    self._error(issues, "referent_provenance_missing", item.record_ref, "required")
            elif item.record_kind == RecordKind.TYPE_ASSERTION:
                if not record.evidence_refs or not record.source_refs:
                    self._error(
                        issues, "type_assertion_provenance_missing", item.record_ref,
                        "evidence_refs and source_refs are required",
                    )
            elif item.record_kind == RecordKind.IDENTITY_FACET:
                if not record.evidence_refs:
                    self._error(issues, "identity_provenance_missing", item.record_ref, "required")
            elif item.record_kind == RecordKind.SEMANTIC_APPLICATION:
                if not record.evidence_refs:
                    self._error(issues, "application_provenance_missing", item.record_ref, "required")
            elif item.record_kind == RecordKind.CAPABILITY_INSTANCE:
                if not record.evidence_refs:
                    self._error(issues, "capability_provenance_missing", item.record_ref, "required")
            elif item.record_kind == RecordKind.DEFAULT_RULE:
                if not record.evidence_refs:
                    self._error(issues, "default_provenance_missing", item.record_ref, "required")
            elif item.record_kind == RecordKind.EVIDENCE:
                if not record.source_ref or not record.lineage_ref:
                    self._error(
                        issues, "evidence_lineage_missing", item.record_ref,
                        "source_ref and lineage_ref are required",
                    )

    def _check_state_domains(self, registry: SchemaRegistry, issues: list[FoundationAuditIssue]) -> None:
        dimensions = {
            item.schema_ref: item
            for item in registry.iter_schemas()
            if isinstance(item, StateDimensionSchema)
        }
        values = {
            item.schema_ref: item
            for item in registry.iter_schemas()
            if isinstance(item, StateValueSchema)
        }
        for dimension in dimensions.values():
            if not dimension.holder_type_refs:
                self._error(issues, "foundation_state_untyped", dimension.schema_ref, "holder_type_refs are required")
            if not dimension.value_schema_refs:
                self._error(issues, "foundation_state_has_no_values", dimension.schema_ref, "value domain is empty")
            for value_ref in dimension.value_schema_refs:
                value = values.get(value_ref)
                if value is None:
                    self._error(issues, "foundation_state_value_missing", dimension.schema_ref, value_ref)
                elif value.dimension_ref != dimension.schema_ref:
                    self._error(issues, "foundation_state_backref_mismatch", value_ref, value.dimension_ref)
        for value in values.values():
            dimension = dimensions.get(value.dimension_ref)
            if dimension is None or value.schema_ref not in dimension.value_schema_refs:
                self._error(issues, "foundation_value_not_indexed", value.schema_ref, value.dimension_ref)

    def _check_native_axes(
        self, registry: SchemaRegistry, issues: list[FoundationAuditIssue]
    ) -> None:
        truth = registry.maybe_authoritative_schema("state:truth_status")
        basis = registry.maybe_authoritative_schema("state:epistemic_basis")
        truth_values = {
            "state-value:truth_status:supported",
            "state-value:truth_status:opposed",
            "state-value:truth_status:both",
            "state-value:truth_status:undetermined",
        }
        basis_values = {
            "state-value:epistemic_basis:observed",
            "state-value:epistemic_basis:reported",
            "state-value:epistemic_basis:inferred",
            "state-value:epistemic_basis:default_expected",
            "state-value:epistemic_basis:assumed",
        }
        if not isinstance(truth, StateDimensionSchema):
            self._error(issues, "truth_status_dimension_missing", "state:truth_status", "required")
        else:
            if set(truth.value_schema_refs) != truth_values:
                self._error(
                    issues, "truth_status_domain_mismatch", truth.schema_ref,
                    "truth support must contain only supported/opposed/both/undetermined",
                )
            if not truth.exclusive or truth.value_cardinality.maximum != 1:
                self._error(
                    issues, "truth_status_not_exclusive", truth.schema_ref,
                    "truth support is a single four-state assessment",
                )
        if not isinstance(basis, StateDimensionSchema):
            self._error(issues, "epistemic_basis_dimension_missing", "state:epistemic_basis", "required")
        else:
            if set(basis.value_schema_refs) != basis_values:
                self._error(
                    issues, "epistemic_basis_domain_mismatch", basis.schema_ref,
                    "epistemic basis must contain observed/reported/inferred/default_expected/assumed",
                )
            if basis.exclusive:
                self._error(
                    issues, "epistemic_basis_wrongly_exclusive", basis.schema_ref,
                    "multiple independent epistemic bases may support one proposition",
                )
        if truth_values.intersection(basis_values):
            self._error(
                issues, "truth_basis_domain_overlap", "foundation:native_axes",
                "truth support and epistemic basis must remain orthogonal",
            )
        for family, values in (("truth_status", truth_values), ("epistemic_basis", basis_values)):
            for value_ref in values:
                key = value_ref.rsplit(":", 1)[-1]
                operator_ref = f"operator:{family}:{key}"
                operator = registry.maybe_authoritative_schema(operator_ref)
                if not isinstance(operator, OperatorSchema) or operator.operator_family != family:
                    self._error(
                        issues, "native_axis_operator_mismatch", operator_ref,
                        f"expected operator family {family}",
                    )
        required_axis_members = {
            "polarity": {"positive", "negative"},
            "change": {
                "set", "activate", "deactivate", "gain", "lose", "increase",
                "decrease", "maintain", "start", "stop", "create", "destroy",
                "enable", "disable", "restore", "terminate",
            },
        }
        for family, expected_keys in required_axis_members.items():
            observed = {
                item.semantic_key
                for item in registry.iter_schemas()
                if isinstance(item, OperatorSchema) and item.operator_family == family
            }
            if observed != expected_keys:
                self._error(
                    issues, "native_axis_membership_mismatch", f"operator-family:{family}",
                    f"expected {sorted(expected_keys)}, got {sorted(observed)}",
                )
        exact_enum_domains = {
            "state:capability_status": {item.value for item in CapabilityStatus},
            "state:occurrence_status": {item.value for item in OccurrenceStatus},
            "state:importance": {item.value for item in ImportanceClass},
            "state:valence": {item.value for item in Valence},
        }
        for dimension_ref, expected_keys in exact_enum_domains.items():
            dimension = registry.maybe_authoritative_schema(dimension_ref)
            if not isinstance(dimension, StateDimensionSchema):
                continue
            observed = {
                registry.authoritative_schema(ref).semantic_key
                for ref in dimension.value_schema_refs
            }
            if observed != expected_keys:
                self._error(
                    issues, "uol_enum_domain_mismatch", dimension_ref,
                    f"expected {sorted(expected_keys)}, got {sorted(observed)}",
                )
        exact_operator_domains = {
            "polarity": {item.value for item in Polarity},
            "valence": {item.value for item in Valence},
            "importance": {item.value for item in ImportanceClass},
            "reversibility": {item.value for item in Reversibility},
        }
        for family, expected_keys in exact_operator_domains.items():
            observed = {
                item.semantic_key
                for item in registry.iter_schemas()
                if isinstance(item, OperatorSchema) and item.operator_family == family
            }
            if observed != expected_keys:
                self._error(
                    issues, "operator_uol_enum_mismatch", f"operator-family:{family}",
                    f"expected {sorted(expected_keys)}, got {sorted(observed)}",
                )

    def _check_facet_boundaries(
        self, registry: SchemaRegistry, issues: list[FoundationAuditIssue]
    ) -> None:
        dimensions = {
            item.schema_ref: item
            for item in registry.iter_schemas()
            if isinstance(item, StateDimensionSchema)
        }
        expected_facets = {
            "state:existence_status": "facet:existence",
            "state:time_status": "facet:temporal",
            "state:location_status": "facet:localization",
            "state:affective_arousal": "facet:affective",
            "state:truth_status": "facet:epistemic",
            "state:epistemic_basis": "facet:epistemic",
            "state:common_ground_status": "facet:epistemic",
            "state:resource_level": "facet:resource",
            "state:capability_status": "facet:capability",
            "state:importance": "facet:significance",
            "state:valence": "facet:significance",
        }
        for dimension_ref, facet_ref in expected_facets.items():
            dimension = dimensions.get(dimension_ref)
            if dimension is None:
                continue
            observed = str(dimension.metadata.get("facet_ref") or "")
            if observed != facet_ref:
                self._error(
                    issues, "state_dimension_facet_boundary_mismatch", dimension_ref,
                    f"expected {facet_ref}, got {observed}",
                )
        affect = dimensions.get("state:affective_arousal")
        valence = dimensions.get("state:valence")
        if affect is not None and valence is not None:
            affect_keys = {
                registry.authoritative_schema(ref).semantic_key
                for ref in affect.value_schema_refs
            }
            valence_keys = {
                registry.authoritative_schema(ref).semantic_key
                for ref in valence.value_schema_refs
            }
            overlap = sorted(affect_keys.intersection(valence_keys) - {"unknown"})
            if overlap:
                self._error(
                    issues, "affect_valence_collapse", affect.schema_ref,
                    f"overlapping value semantics: {overlap}",
                )
        entitlement_values = {
            ref
            for entitlement in registry.iter_entitlements()
            for ref in entitlement.value_domain_refs
        }
        for assessment_ref in ("state:importance", "state:valence"):
            dimension = dimensions.get(assessment_ref)
            if dimension is None:
                continue
            if dimension.metadata.get("assessment_only") is not True:
                self._error(
                    issues, "significance_dimension_not_assessment_only", assessment_ref,
                    "stakeholder-relative significance must be assessment-only",
                )
            if assessment_ref in entitlement_values:
                self._error(
                    issues, "significance_dimension_licensed_as_state", assessment_ref,
                    "use ImportanceAssessment/ImpactAssessment rather than StateAssignment",
                )
        capability_status = dimensions.get("state:capability_status")
        if capability_status is not None:
            if capability_status.metadata.get("record_status_only") is not True:
                self._error(
                    issues, "capability_status_not_record_scoped", capability_status.schema_ref,
                    "capability status describes CapabilityInstance records",
                )
            if capability_status.schema_ref in entitlement_values:
                self._error(
                    issues, "capability_status_licensed_as_holder_state", capability_status.schema_ref,
                    "capability availability is not a generic holder StateAssignment",
                )
        property_refs = {
            item.schema_ref
            for item in registry.iter_schemas()
            if isinstance(item, PropertySchema)
        }
        missing_properties = sorted(property_refs - entitlement_values)
        for property_ref in missing_properties:
            self._error(
                issues, "foundation_property_not_entitled", property_ref,
                "core property has no applicable type entitlement",
            )
        universal = {
            item.entitlement_ref: item for item in registry.iter_entitlements()
        }
        for entitlement_ref, required_dimension in (
            ("entitlement:referent:existence", "state:existence_status"),
            ("entitlement:referent:temporal", "state:time_status"),
        ):
            entitlement = universal.get(entitlement_ref)
            if entitlement is None or required_dimension not in entitlement.value_domain_refs:
                self._error(
                    issues, "universal_facet_dimension_missing", entitlement_ref,
                    required_dimension,
                )
            elif entitlement.applicability.value != "required":
                self._error(
                    issues, "universal_facet_not_required", entitlement_ref,
                    entitlement.applicability.value,
                )

    def _check_entitlement_domains(
        self, registry: SchemaRegistry, issues: list[FoundationAuditIssue]
    ) -> None:
        for entitlement in registry.iter_entitlements():
            try:
                owner_closure = registry.type_closure(entitlement.owner_type_ref)
            except (KeyError, TypeError):
                continue
            for value_ref in entitlement.value_domain_refs:
                value = registry.maybe_authoritative_schema(value_ref)
                if isinstance(value, StateDimensionSchema):
                    facet_ref = str(value.metadata.get("facet_ref") or value.schema_ref)
                    if facet_ref != entitlement.facet_ref:
                        self._error(
                            issues, "entitlement_dimension_facet_mismatch",
                            entitlement.entitlement_ref,
                            f"{value_ref} belongs to {facet_ref}, not {entitlement.facet_ref}",
                        )
                    if value.holder_type_refs and not owner_closure.intersection(value.holder_type_refs):
                        self._error(
                            issues, "entitlement_dimension_holder_mismatch",
                            entitlement.entitlement_ref,
                            f"{value_ref} does not license owner {entitlement.owner_type_ref}",
                        )
                if entitlement.facet_ref in {"facet:action_affordance", "facet:capability"}:
                    if not isinstance(value, ActionSchema):
                        self._error(
                            issues, "action_facet_domain_not_action",
                            entitlement.entitlement_ref,
                            f"{value_ref} is not an ActionSchema",
                        )
                    elif value.controlling_port_ref is not None:
                        port = value.port(value.controlling_port_ref)
                        if port.accepted_type_refs and not owner_closure.intersection(port.accepted_type_refs):
                            self._error(
                                issues, "action_domain_holder_mismatch",
                                entitlement.entitlement_ref,
                                f"{value_ref}.{port.port_ref} does not license {entitlement.owner_type_ref}",
                            )
                if isinstance(value, PropertySchema):
                    holder = next(
                        (port for port in value.local_ports if port.port_ref == "holder"),
                        value.local_ports[0] if value.local_ports else None,
                    )
                    if holder is None or (
                        holder.accepted_type_refs
                        and not owner_closure.intersection(holder.accepted_type_refs)
                    ):
                        self._error(
                            issues, "property_domain_holder_mismatch",
                            entitlement.entitlement_ref,
                            f"{value_ref} does not license {entitlement.owner_type_ref}",
                        )
                if isinstance(value, RelationSchema):
                    participant_ports = tuple(
                        port for port in value.local_ports if port.identity_contribution
                    ) or value.local_ports
                    if participant_ports and not any(
                        not port.accepted_type_refs
                        or owner_closure.intersection(port.accepted_type_refs)
                        for port in participant_ports
                    ):
                        self._error(
                            issues, "relation_domain_holder_mismatch",
                            entitlement.entitlement_ref,
                            f"{value_ref} has no participant port for {entitlement.owner_type_ref}",
                        )
                if isinstance(value, RoleSchema):
                    if value.holder_type_refs and not owner_closure.intersection(value.holder_type_refs):
                        self._error(
                            issues, "role_domain_holder_mismatch",
                            entitlement.entitlement_ref,
                            f"{value_ref} does not license {entitlement.owner_type_ref}",
                        )
                if isinstance(value, FunctionSchema):
                    if value.holder_type_refs and not owner_closure.intersection(value.holder_type_refs):
                        self._error(
                            issues, "function_domain_holder_mismatch",
                            entitlement.entitlement_ref,
                            f"{value_ref} does not license {entitlement.owner_type_ref}",
                        )

    def _check_events(self, registry: SchemaRegistry, issues: list[FoundationAuditIssue]) -> None:
        for schema in registry.iter_schemas():
            if not isinstance(schema, EventSchema):
                continue
            if (
                schema.transition_contract_refs
                or schema.result_contract_refs
                or schema.causal_contract_refs
                or schema.impact_rule_refs
            ):
                self._error(
                    issues,
                    "phase6_event_claims_later_authority",
                    schema.schema_ref,
                    "Phase 6 may seed event meaning but not transition/causal/impact execution",
                )
            if schema.use_profile.decision_for(UseOperation.TRANSITION).value != "deny":
                self._error(issues, "phase6_event_transition_enabled", schema.schema_ref, "transition use must remain denied")

    def _check_discourse(self, registry: SchemaRegistry, issues: list[FoundationAuditIssue]) -> None:
        acknowledge = registry.maybe_authoritative_schema("discourse-act:acknowledge")
        if not isinstance(acknowledge, DiscourseActSchema) or not acknowledge.content_port_ref:
            self._error(issues, "targetless_acknowledgement", "discourse-act:acknowledge", "content port is required")
        elif acknowledge.port(acknowledge.content_port_ref).cardinality.minimum < 1:
            self._error(issues, "targetless_acknowledgement", acknowledge.schema_ref, "content cardinality must be required")
        discourse_keys = {
            item.semantic_key
            for item in registry.iter_schemas()
            if isinstance(item, DiscourseActSchema)
        }
        missing_claim_forces = sorted({item.value for item in ClaimForce} - discourse_keys)
        if missing_claim_forces:
            self._error(
                issues, "claim_force_discourse_gap", "foundation:discourse_acts",
                f"missing {missing_claim_forces}",
            )
        for schema in registry.iter_schemas():
            if isinstance(schema, ResponsePolicySchema) and schema.literal_realization_refs:
                self._error(issues, "foundation_sentence_template", schema.schema_ref, "literal realization refs are forbidden")

    def _check_self_records(
        self,
        by_kind: Mapping[RecordKind, Mapping[str, list[SourceRecord]]],
        registry: SchemaRegistry,
        issues: list[FoundationAuditIssue],
    ) -> None:
        self_records = by_kind.get(RecordKind.REFERENT, {}).get("referent:self", [])
        if not self_records:
            return
        self_ref = max(self_records, key=lambda item: item.revision).record
        if self_ref.identity_status != IdentityStatus.RESOLVED:
            self._error(issues, "self_identity_not_resolved", self_ref.referent_ref, self_ref.identity_status.value)
        if "type:software_agent" not in self_ref.type_refs:
            self._error(issues, "self_type_missing", self_ref.referent_ref, "type:software_agent is required")

        evidence_refs = set(by_kind.get(RecordKind.EVIDENCE, {}))
        capabilities = by_kind.get(RecordKind.CAPABILITY_INSTANCE, {})
        for ref in self.contract.required_capability_refs:
            items = capabilities.get(ref, [])
            if not items:
                continue
            capability = max(items, key=lambda item: item.revision).record
            action = registry.maybe_schema(capability.action_schema_ref, capability.action_schema_revision)
            if not isinstance(action, ActionSchema):
                self._error(issues, "capability_action_missing", ref, capability.action_schema_ref)
                continue
            if capability.status == CapabilityStatus.AVAILABLE:
                for operation in (UseOperation.PLAN, UseOperation.EXECUTE):
                    if not action.use_profile.permits(operation):
                        self._error(issues, "available_capability_not_authorized", ref, operation.value)
                    if not any(hook.required and hook.operation == operation for hook in action.competence_hooks):
                        self._error(issues, "available_capability_missing_competence", ref, operation.value)
                component_ref = str(action.metadata.get("runtime_component") or "")
                if not component_ref:
                    self._error(issues, "available_capability_runtime_component_missing", ref, action.schema_ref)
                else:
                    try:
                        resolve_runtime_component(component_ref)
                    except RuntimeComponentResolutionError as exc:
                        self._error(
                            issues, "available_capability_runtime_component_unresolved",
                            ref, str(exc),
                        )
            if not set(capability.evidence_refs).issubset(evidence_refs):
                self._error(issues, "capability_evidence_missing", ref, str(sorted(set(capability.evidence_refs) - evidence_refs)))
        realization = capabilities.get("capability:self:realize-language", [])
        if realization:
            capability = max(realization, key=lambda item: item.revision).record
            action = registry.maybe_schema(capability.action_schema_ref, capability.action_schema_revision)
            if capability.status != CapabilityStatus.UNAVAILABLE:
                self._error(issues, "premature_realization_capability", capability.capability_ref, capability.status.value)
            if isinstance(action, ActionSchema) and action.use_profile.permits(UseOperation.EXECUTE):
                self._error(issues, "premature_realization_authority", action.schema_ref, "execute must remain denied")

    def _check_defaults(
        self,
        by_kind: Mapping[RecordKind, Mapping[str, list[SourceRecord]]],
        registry: SchemaRegistry,
        issues: list[FoundationAuditIssue],
    ) -> None:
        for items in by_kind.get(RecordKind.STATE_ASSIGNMENT, {}).values():
            for item in items:
                if item.record.status == AssignmentStatus.ACTIVE:
                    self._error(issues, "boot_active_state_forbidden", item.record_ref, "live state must be observed, not boot-assumed")
        if by_kind.get(RecordKind.KNOWLEDGE):
            self._error(issues, "boot_actual_knowledge_forbidden", "foundation:seed_knowledge", "Phase 6 does not admit world claims")
        entitlements = tuple(registry.iter_entitlements())
        linked = {ref for item in entitlements for ref in item.default_rule_refs}
        for rule_ref, items in by_kind.get(RecordKind.DEFAULT_RULE, {}).items():
            rule = max(items, key=lambda item: item.revision).record
            if rule_ref not in linked:
                self._error(issues, "default_rule_not_entitlement_linked", rule_ref, rule.target_facet_ref)
            dimension = (
                None if rule.expected_dimension_ref is None
                else registry.maybe_schema(rule.expected_dimension_ref, rule.expected_dimension_revision)
            )
            if isinstance(dimension, StateDimensionSchema):
                facet_ref = str(dimension.metadata.get("facet_ref") or dimension.schema_ref)
                if facet_ref != rule.target_facet_ref:
                    self._error(
                        issues, "default_rule_facet_mismatch", rule_ref,
                        f"{dimension.schema_ref} belongs to {facet_ref}",
                    )

    def _check_competence_cases(self, root: Path, issues: list[FoundationAuditIssue]) -> None:
        path = root / "competence" / "foundation.jsonl"
        refs: set[str] = set()
        if path.is_file():
            for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if not raw.strip() or raw.lstrip().startswith("#"):
                    continue
                try:
                    value = json.loads(raw)
                    refs.add(str(value["case_ref"]))
                except Exception as exc:
                    self._error(issues, "invalid_competence_case", f"{path.name}:{line_number}", str(exc))
        for ref in self.contract.required_competence_case_refs:
            if ref not in refs:
                self._error(issues, "missing_competence_case", ref, "required by foundation contract")

    @staticmethod
    def _error(issues: list[FoundationAuditIssue], code: str, target: str, message: str) -> None:
        issues.append(FoundationAuditIssue(AuditSeverity.ERROR, code, target, message))


def _string_tokens(value: Any) -> set[str]:
    import re

    result: set[str] = set()
    if isinstance(value, str):
        result.update(
            token.casefold()
            for token in re.split(r"[^\w]+", value)
            if token
        )
    elif isinstance(value, Mapping):
        for key, child in value.items():
            result.update(_string_tokens(str(key)))
            result.update(_string_tokens(child))
    elif isinstance(value, (tuple, list, set, frozenset)):
        for child in value:
            result.update(_string_tokens(child))
    return result


def _forbidden_surface_paths(value: Any, path: str = "$") -> tuple[str, ...]:
    result: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key).casefold() in _FORBIDDEN_SURFACE_FIELDS:
                result.append(child_path)
            result.extend(_forbidden_surface_paths(child, child_path))
    elif isinstance(value, (tuple, list)):
        for index, child in enumerate(value):
            result.extend(_forbidden_surface_paths(child, f"{path}[{index}]"))
    return tuple(result)
