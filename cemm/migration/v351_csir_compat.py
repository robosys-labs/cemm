"""One-way legacy UOL/schema -> CSIR v3.5.1 compatibility compiler.

This module is intentionally under ``cemm.migration``.  Canonical runtime modules must
never import it.  It exists only for deterministic migration/shadow comparison and can
never provide a fallback answer path.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Iterable, Mapping

from cemm.v350.csir.authority_v351 import AuthoritySnapshotV351, ClosureProof, ClosureProofError
from cemm.v350.csir.canonical_v351 import compare, exact_fingerprint, normalize, semantic_fingerprint
from cemm.v350.csir.model import (
    CSIRGraph,
    CSIRNodeKind,
    CSIRRef,
    Coordination,
    ExactAuthorityPin,
    PortBinding,
    Qualifier,
    QualifierKind,
    ScopeEmbedding,
    SemanticApplication,
    SemanticTerm,
    SemanticVariable,
    TermKind,
)
from cemm.v350.schema.model import MeaningSchema, ParentRevisionPolicy, PortFillerClass, UseOperation
from cemm.v350.uol.model import (
    ApplicationBinding as LegacyBinding,
    CoordinationGroup as LegacyCoordination,
    FillerRef,
    Polarity,
    QuotedLiteral,
    Referent as LegacyReferent,
    ScopeRelation as LegacyScope,
    SemanticApplication as LegacyApplication,
    SemanticVariable as LegacyVariable,
)


class MigrationClassification(str, Enum):
    LOSSLESS = "LOSSLESS"
    REQUIRES_EXPLICIT_INTERPRETATION = "REQUIRES_EXPLICIT_INTERPRETATION"
    AMBIGUOUS = "AMBIGUOUS"
    DEPRECATED = "DEPRECATED"
    QUARANTINED = "QUARANTINED"


@dataclass(frozen=True, slots=True)
class LegacyExactAuthorityMap:
    schema_pins: Mapping[tuple[str, int], ExactAuthorityPin]
    port_pins: Mapping[tuple[str, int, str], ExactAuthorityPin]
    type_pins: Mapping[str, ExactAuthorityPin]
    scope_kind_pins: Mapping[str, ExactAuthorityPin]
    coordination_kind_pins: Mapping[str, ExactAuthorityPin]
    closure_proofs: Mapping[tuple[str, int], ClosureProof]
    semantic_authority_snapshot: AuthoritySnapshotV351 | None = None
    # Schema-authority migration is content-bound. A ref/revision pair alone is not
    # sufficient proof that the legacy record reviewed during mapping is the record now
    # being migrated.
    schema_source_fingerprints: Mapping[tuple[str, int], str] = field(default_factory=dict)
    operational_profile_pins: Mapping[tuple[str, int], ExactAuthorityPin] = field(default_factory=dict)

    def schema(self, ref: str, revision: int) -> ExactAuthorityPin:
        return self.schema_pins[(ref, revision)]

    def port(self, schema_ref: str, revision: int, port_ref: str) -> ExactAuthorityPin:
        return self.port_pins[(schema_ref, revision, port_ref)]


@dataclass(frozen=True, slots=True)
class CompatibilityCompilationReport:
    classification: MigrationClassification
    graph: CSIRGraph | None
    semantic_fingerprint: str | None
    exact_fingerprint: str | None
    closure_proofs: tuple[ClosureProof, ...]
    reason_refs: tuple[str, ...]
    source_refs: tuple[str, ...]
    equivalent_to_authoritative: bool | None = None
    authoritative_fingerprint: str | None = None


@dataclass(frozen=True, slots=True)
class Stage5ShadowReport:
    reports: tuple[CompatibilityCompilationReport, ...]
    authoritative_candidate_fingerprints: tuple[str, ...]
    matched_fingerprints: tuple[str, ...]
    mismatched_fingerprints: tuple[str, ...]
    shadow_only: bool = True

    def __post_init__(self) -> None:
        if not self.shadow_only:
            raise ValueError("legacy compatibility comparison can only run shadow-only")


class LegacyCompatibilityCompiler:
    """Explicit translator for reviewed legacy UOL record classes.

    No duck-typed ``to_csir`` hook is accepted.  Unsupported objects are quarantined.
    Missing exact authority produces an interpretation requirement, never a floating
    "latest" lookup.
    """

    def __init__(
        self,
        authority: LegacyExactAuthorityMap,
        *,
        deprecated_record_refs: frozenset[str] = frozenset(),
    ) -> None:
        self.authority = authority
        self.deprecated_record_refs = deprecated_record_refs

    @staticmethod
    def _record_ref(value: Any) -> str:
        for name in (
            "referent_ref",
            "variable_ref",
            "application_ref",
            "group_ref",
            "scope_relation_ref",
            "schema_ref",
        ):
            raw = getattr(value, name, None)
            if raw:
                return str(raw)
        return type(value).__name__

    def compile_schema_definition(
        self,
        schema: MeaningSchema,
        *,
        authoritative_graph: CSIRGraph | None = None,
    ) -> CompatibilityCompilationReport:
        source_ref = f"{schema.schema_ref}@{schema.revision}"
        reasons: list[str] = []
        key = (schema.schema_ref, schema.revision)

        expected_source = self.authority.schema_source_fingerprints.get(key)
        if expected_source is None:
            reasons.append(f"missing-reviewed-source-fingerprint:{source_ref}")
        elif expected_source != schema.record_fingerprint:
            reasons.append(f"legacy-schema-content-drift:{source_ref}")

        definition_pin = self.authority.schema_pins.get(key)
        snapshot = self.authority.semantic_authority_snapshot
        definition = None
        if definition_pin is None:
            reasons.append(f"missing-exact-schema-pin:{source_ref}")
        elif snapshot is None:
            reasons.append(f"missing-semantic-authority-snapshot:{source_ref}")
        else:
            try:
                definition = snapshot.require_definition(definition_pin)
            except Exception:
                reasons.append(f"missing-exact-semantic-definition:{source_ref}")

        proof = self.authority.closure_proofs.get(key)
        valid_proofs: tuple[ClosureProof, ...] = ()
        if proof is None:
            reasons.append(f"missing-exact-closure-proof:{source_ref}")
        elif definition_pin is None or proof.root_definition_pin.key != definition_pin.key:
            reasons.append(f"closure-proof-root-mismatch:{source_ref}")
        elif snapshot is None:
            reasons.append(f"missing-semantic-authority-snapshot-for-closure:{source_ref}")
        else:
            try:
                proof.verify_authority(snapshot)
            except ClosureProofError as exc:
                reasons.append(f"invalid-exact-closure-proof:{source_ref}:{type(exc).__name__}")
            else:
                valid_proofs = (proof,)

        # Floating inheritance/dependency selection cannot be certified as the same exact
        # semantics by an automatic compatibility compiler. It requires an explicit
        # reviewed interpretation/mapping decision.
        for parent in schema.parent_links:
            if parent.revision_policy != ParentRevisionPolicy.EXACT:
                reasons.append(f"floating-parent-revision:{source_ref}:{parent.parent_ref}")
            elif (parent.parent_ref, int(parent.revision or 0)) not in self.authority.schema_pins:
                reasons.append(
                    f"missing-exact-parent-mapping:{source_ref}:{parent.parent_ref}@{parent.revision}"
                )
        for dependency in schema.dependencies:
            if not dependency.required:
                continue
            if dependency.exact_revision is None:
                reasons.append(
                    f"floating-required-dependency:{source_ref}:{dependency.dependency_ref}"
                )
            elif (dependency.dependency_ref, dependency.exact_revision) not in self.authority.schema_pins:
                reasons.append(
                    f"missing-exact-dependency-mapping:{source_ref}:{dependency.dependency_ref}@{dependency.exact_revision}"
                )

        if definition is not None:
            formal_port_keys = {item.port_pin.key for item in definition.formal_ports}
            for local_port in schema.local_ports:
                port_pin = self.authority.port_pins.get(
                    (schema.schema_ref, schema.revision, local_port.port_ref)
                )
                if port_pin is None:
                    reasons.append(
                        f"missing-exact-port-pin:{source_ref}:{local_port.port_ref}"
                    )
                elif port_pin.key not in formal_port_keys:
                    reasons.append(
                        f"legacy-port-maps-outside-definition:{source_ref}:{local_port.port_ref}"
                    )
                if local_port.constraint_refs:
                    reasons.append(
                        f"legacy-port-constraints-require-explicit-mapping:{source_ref}:{local_port.port_ref}"
                    )

        # The old schema record bundled lifecycle/use authority. LOSSLESS is forbidden
        # unless that operational information is explicitly mapped to the split authority
        # and has the same effective decisions in the schema's context/permission scope.
        profile = None
        if snapshot is not None and definition_pin is not None:
            profile_pin = self.authority.operational_profile_pins.get(key)
            if profile_pin is None:
                reasons.append(f"missing-split-operational-profile-mapping:{source_ref}")
            else:
                try:
                    profile = snapshot.require_operational_profile(profile_pin)
                except Exception:
                    reasons.append(f"missing-exact-operational-profile:{source_ref}")
                else:
                    if profile.definition_pin.key != definition_pin.key:
                        reasons.append(f"operational-profile-definition-mismatch:{source_ref}")
                    if profile.lifecycle_status.casefold() != schema.lifecycle_status.value.casefold():
                        reasons.append(f"lifecycle-split-mismatch:{source_ref}")
                    if profile.permission_scopes and not snapshot._scope_matches(
                        profile.permission_scopes, schema.permission_ref
                    ):
                        reasons.append(f"permission-split-mismatch:{source_ref}")

        if snapshot is not None and definition_pin is not None and profile is not None:
            for operation in UseOperation:
                legacy_decision = schema.use_profile.decision_for(operation).value
                matching = [
                    item for item in snapshot.use_authorizations
                    if item.target_pin.key in {definition_pin.key, profile.profile_pin.key}
                    and item.operation == operation.value
                    and snapshot._scope_matches(item.context_scopes, schema.scope_ref)
                    and snapshot._scope_matches(item.permission_scopes, schema.permission_ref)
                ]
                decisions = {item.decision.casefold() for item in matching}
                if "deny" in decisions:
                    split_decision = "deny"
                elif "allow" in decisions and operation.value in profile.allowed_operations:
                    split_decision = "allow"
                elif "provisional" in decisions:
                    split_decision = "provisional"
                elif "preserve_only" in decisions:
                    split_decision = "preserve_only"
                else:
                    split_decision = "deny"
                if split_decision != legacy_decision:
                    reasons.append(
                        f"use-authority-split-mismatch:{source_ref}:{operation.value}:{legacy_decision}->{split_decision}"
                    )

            legacy_cases = {hook.case_ref for hook in schema.competence_hooks if hook.required}
            split_cases = {pin.ref for pin in profile.competence_case_pins}
            if not legacy_cases.issubset(split_cases):
                reasons.append(f"competence-split-mismatch:{source_ref}")

        graph = None if definition is None else normalize(definition.body)
        sem_fp = None if graph is None else semantic_fingerprint(graph)
        ex_fp = None if graph is None else exact_fingerprint(graph)
        equivalent = None
        authoritative_fp = None
        classification = (
            MigrationClassification.LOSSLESS
            if graph is not None and not reasons
            else MigrationClassification.REQUIRES_EXPLICIT_INTERPRETATION
        )
        if graph is not None and authoritative_graph is not None:
            assessment = compare(graph, authoritative_graph)
            equivalent = assessment.equivalent
            authoritative_fp = assessment.right_fingerprint
            if classification == MigrationClassification.LOSSLESS and not equivalent:
                classification = MigrationClassification.AMBIGUOUS
                reasons.append("shadow-semantic-mismatch")
        return CompatibilityCompilationReport(
            classification, graph, sem_fp, ex_fp, valid_proofs,
            tuple(sorted(set(reasons))), (source_ref,), equivalent, authoritative_fp,
        )

    def compile_records(
        self,
        records: Iterable[Any],
        *,
        authoritative_graph: CSIRGraph | None = None,
    ) -> CompatibilityCompilationReport:
        records = tuple(records)
        if not records:
            return CompatibilityCompilationReport(
                MigrationClassification.QUARANTINED, None, None, None, (),
                ("empty-legacy-record-group",), (),
            )
        source_refs = tuple(self._record_ref(x) for x in records)
        deprecated = tuple(sorted(set(source_refs).intersection(self.deprecated_record_refs)))
        if deprecated:
            return CompatibilityCompilationReport(
                MigrationClassification.DEPRECATED,
                None,
                None,
                None,
                (),
                tuple(f"deprecated-legacy-record:{ref}" for ref in deprecated),
                source_refs,
            )
        schema_records = tuple(x for x in records if isinstance(x, MeaningSchema))
        if schema_records:
            if len(schema_records) != 1 or len(records) != 1:
                return CompatibilityCompilationReport(
                    MigrationClassification.QUARANTINED, None, None, None, (),
                    ("mixed-schema-authority-and-occurrence-records",), source_refs,
                )
            return self.compile_schema_definition(
                schema_records[0], authoritative_graph=authoritative_graph
            )
        allowed = (LegacyReferent, LegacyVariable, LegacyApplication, LegacyCoordination, LegacyScope)
        unsupported = tuple(type(x).__name__ for x in records if not isinstance(x, allowed))
        if unsupported:
            return CompatibilityCompilationReport(
                MigrationClassification.QUARANTINED,
                None,
                None,
                None,
                (),
                tuple(f"unsupported-legacy-record:{name}" for name in sorted(set(unsupported))),
                tuple(self._record_ref(x) for x in records),
            )

        referents = {x.referent_ref: x for x in records if isinstance(x, LegacyReferent)}
        variables = {x.variable_ref: x for x in records if isinstance(x, LegacyVariable)}
        applications = {x.application_ref: x for x in records if isinstance(x, LegacyApplication)}
        coordinations = {x.group_ref: x for x in records if isinstance(x, LegacyCoordination)}
        scopes = tuple(x for x in records if isinstance(x, LegacyScope))
        reasons: list[str] = []
        terms: dict[str, SemanticTerm] = {}
        csir_variables: dict[str, SemanticVariable] = {}
        csir_apps: list[SemanticApplication] = []
        bindings: list[PortBinding] = []
        qualifiers: list[Qualifier] = []
        csir_coords: list[Coordination] = []
        csir_scopes: list[ScopeEmbedding] = []
        closure_proofs: dict[str, ClosureProof] = {}

        for item in referents.values():
            pins = []
            for type_ref in item.type_refs:
                pin = self.authority.type_pins.get(type_ref)
                if pin is None:
                    reasons.append(f"missing-exact-type-pin:{type_ref}")
                else:
                    pins.append(pin)
            terms[item.referent_ref] = SemanticTerm(
                item.referent_ref,
                TermKind.REFERENT,
                identity_ref=item.referent_ref,
                type_pins=tuple(pins),
            )

        for item in variables.values():
            pins = []
            for type_ref in item.expected_type_refs:
                pin = self.authority.type_pins.get(type_ref)
                if pin is None:
                    reasons.append(f"missing-exact-variable-type-pin:{type_ref}")
                else:
                    pins.append(pin)
            # Legacy expected schema/filler classes have no direct v2 CSIR constructor;
            # they must be represented by explicit definition/port restrictions before a
            # migration can be declared lossless.
            if item.expected_schema_classes or item.expected_filler_classes or item.restriction_refs:
                reasons.append(f"legacy-variable-constraints-require-explicit-interpretation:{item.variable_ref}")
            csir_variables[item.variable_ref] = SemanticVariable(
                item.variable_ref,
                required_type_pins=tuple(pins),
                scope_ref=item.scope_ref,
                open_purpose=(
                    "partial"
                    if item.open_binding_purpose is None
                    else str(item.open_binding_purpose.value)
                ),
            )

        literal_counter = 0

        def filler_ref(
            filler: FillerRef | QuotedLiteral,
            *,
            owner_ref: str,
        ) -> CSIRRef | None:
            nonlocal literal_counter
            if isinstance(filler, QuotedLiteral):
                literal_ref = f"legacy-literal:{owner_ref}:{literal_counter}"
                literal_counter += 1
                terms[literal_ref] = SemanticTerm(
                    literal_ref,
                    TermKind.LITERAL,
                    literal_value=filler.surface,
                    features=(("language_tag", filler.language_tag),),
                )
                return CSIRRef(CSIRNodeKind.TERM, literal_ref)
            klass = filler.filler_class
            if klass == PortFillerClass.REFERENT:
                if filler.ref not in terms:
                    # A dangling identity is not silently manufactured as a durable
                    # referent. Preserve it as an explicit unresolved migration reason.
                    reasons.append(f"missing-legacy-referent:{filler.ref}")
                    return None
                return CSIRRef(CSIRNodeKind.TERM, filler.ref)
            if klass == PortFillerClass.SEMANTIC_VARIABLE:
                if filler.ref not in csir_variables:
                    reasons.append(f"missing-legacy-variable:{filler.ref}")
                    return None
                return CSIRRef(CSIRNodeKind.VARIABLE, filler.ref)
            if klass == PortFillerClass.SEMANTIC_APPLICATION:
                if filler.ref not in applications:
                    reasons.append(f"missing-legacy-application:{filler.ref}")
                    return None
                return CSIRRef(CSIRNodeKind.APPLICATION, filler.ref)
            if klass == PortFillerClass.COORDINATION_GROUP:
                if filler.ref not in coordinations:
                    reasons.append(f"missing-legacy-coordination:{filler.ref}")
                    return None
                return CSIRRef(CSIRNodeKind.COORDINATION, filler.ref)
            reasons.append(f"unsupported-filler-class:{klass.value}")
            return None

        for item in applications.values():
            try:
                predicate = self.authority.schema(item.schema_ref, item.schema_revision)
            except KeyError:
                reasons.append(f"missing-exact-schema-pin:{item.schema_ref}@{item.schema_revision}")
                continue
            proof = self.authority.closure_proofs.get((item.schema_ref, item.schema_revision))
            if proof is None:
                reasons.append(f"missing-exact-closure-proof:{item.schema_ref}@{item.schema_revision}")
            elif proof.root_definition_pin.key != predicate.key:
                reasons.append(
                    f"closure-proof-root-mismatch:{item.schema_ref}@{item.schema_revision}"
                )
            elif self.authority.semantic_authority_snapshot is None:
                reasons.append(
                    f"missing-semantic-authority-snapshot-for-closure:{item.schema_ref}@{item.schema_revision}"
                )
            else:
                try:
                    proof.verify_authority(self.authority.semantic_authority_snapshot)
                except ClosureProofError as exc:
                    reasons.append(
                        f"invalid-exact-closure-proof:{item.schema_ref}@{item.schema_revision}:{type(exc).__name__}"
                    )
                else:
                    closure_proofs[proof.proof_ref] = proof
            csir_apps.append(SemanticApplication(item.application_ref, predicate))
            for index, binding in enumerate(item.bindings):
                try:
                    port_pin = self.authority.port(
                        item.schema_ref, item.schema_revision, binding.port_ref
                    )
                except KeyError:
                    reasons.append(
                        f"missing-exact-port-pin:{item.schema_ref}@{item.schema_revision}:{binding.port_ref}"
                    )
                    continue
                converted = tuple(
                    value
                    for value in (
                        filler_ref(x, owner_ref=f"{item.application_ref}:{index}")
                        for x in binding.fillers
                    )
                    if value is not None
                )
                if len(converted) != len(binding.fillers):
                    continue
                bindings.append(
                    PortBinding(
                        f"legacy-binding:{item.application_ref}:{index}",
                        item.application_ref,
                        port_pin,
                        converted,
                        ordered=binding.ordered,
                    )
                )
                if binding.assumptions:
                    reasons.append(f"legacy-binding-assumptions-require-interpretation:{item.application_ref}:{index}")
            if item.assumptions:
                reasons.append(f"legacy-application-assumptions-require-interpretation:{item.application_ref}")
            if item.polarity == Polarity.NEGATIVE:
                qualifiers.append(
                    Qualifier(
                        f"legacy-polarity:{item.application_ref}",
                        CSIRRef(CSIRNodeKind.APPLICATION, item.application_ref),
                        QualifierKind.POLARITY,
                        value_atom="negative",
                    )
                )

        for item in coordinations.values():
            pin = self.authority.coordination_kind_pins.get(str(item.coordination_kind.value))
            if pin is None:
                reasons.append(f"missing-exact-coordination-pin:{item.coordination_kind.value}")
                continue
            members = tuple(
                value
                for value in (
                    filler_ref(x, owner_ref=item.group_ref) for x in item.members
                )
                if value is not None
            )
            if len(members) != len(item.members):
                continue
            csir_coords.append(
                Coordination(item.group_ref, pin, members, ordered=item.coordination_kind.value == "list")
            )

        for item in scopes:
            pin = self.authority.scope_kind_pins.get(str(item.scope_kind.value))
            if pin is None:
                reasons.append(f"missing-exact-scope-pin:{item.scope_kind.value}")
                continue
            scoped = filler_ref(item.scoped_ref, owner_ref=item.scope_relation_ref)
            if scoped is None or item.operator_application_ref not in applications:
                reasons.append(f"unresolved-legacy-scope:{item.scope_relation_ref}")
                continue
            csir_scopes.append(
                ScopeEmbedding(
                    item.scope_relation_ref,
                    CSIRRef(CSIRNodeKind.APPLICATION, item.operator_application_ref),
                    scoped,
                    pin,
                    item.order,
                )
            )

        if reasons:
            # Deterministic partial translation is retained for review, but it is not
            # executable authority and cannot be used as fallback cognition.
            classification = MigrationClassification.REQUIRES_EXPLICIT_INTERPRETATION
        else:
            classification = MigrationClassification.LOSSLESS

        try:
            used_as_filler = {
                filler.ref
                for binding in applications.values()
                for legacy_binding in binding.bindings
                for filler in legacy_binding.fillers
                if isinstance(filler, FillerRef)
                and filler.filler_class == PortFillerClass.SEMANTIC_APPLICATION
            }
            roots = tuple(
                CSIRRef(CSIRNodeKind.APPLICATION, ref)
                for ref in sorted(set(applications).difference(used_as_filler))
                if any(app.application_ref == ref for app in csir_apps)
            )
            if not roots:
                roots = tuple(
                    [CSIRRef(CSIRNodeKind.APPLICATION, x.application_ref) for x in csir_apps]
                    + [CSIRRef(CSIRNodeKind.COORDINATION, x.coordination_ref) for x in csir_coords]
                    + [CSIRRef(CSIRNodeKind.TERM, x.term_ref) for x in terms.values()]
                    + [CSIRRef(CSIRNodeKind.VARIABLE, x.variable_ref) for x in csir_variables.values()]
                )
            graph = normalize(
                CSIRGraph(
                    terms=tuple(terms.values()),
                    variables=tuple(csir_variables.values()),
                    applications=tuple(csir_apps),
                    bindings=tuple(bindings),
                    qualifiers=tuple(qualifiers),
                    scope_embeddings=tuple(csir_scopes),
                    coordinations=tuple(csir_coords),
                    root_refs=roots,
                    unresolved_refs=tuple(sorted(set(reasons))),
                )
            )
        except Exception as exc:
            return CompatibilityCompilationReport(
                MigrationClassification.QUARANTINED,
                None,
                None,
                None,
                tuple(closure_proofs.values()),
                tuple(sorted(set((*reasons, f"csir-validation-failed:{type(exc).__name__}")))),
                tuple(self._record_ref(x) for x in records),
            )

        sem_fp = semantic_fingerprint(graph)
        ex_fp = exact_fingerprint(graph)
        equivalent = None
        authoritative_fp = None
        if authoritative_graph is not None:
            assessment = compare(graph, authoritative_graph)
            equivalent = assessment.equivalent
            authoritative_fp = assessment.right_fingerprint
            if classification == MigrationClassification.LOSSLESS and not equivalent:
                classification = MigrationClassification.AMBIGUOUS
                reasons.append("shadow-semantic-mismatch")
        return CompatibilityCompilationReport(
            classification,
            graph,
            sem_fp,
            ex_fp,
            tuple(sorted(closure_proofs.values(), key=lambda item: item.proof_ref)),
            tuple(sorted(set(reasons))),
            tuple(self._record_ref(x) for x in records),
            equivalent,
            authoritative_fp,
        )


class Stage5ShadowComparator:
    """Non-authoritative Stage-5 migration observer.

    The return type contains reports only.  There is deliberately no method that can
    return/replace an authoritative CSIR candidate set.
    """

    def __init__(self, compiler: LegacyCompatibilityCompiler) -> None:
        self.compiler = compiler

    def compare(
        self,
        legacy_record_groups: Iterable[Iterable[Any]],
        authoritative_graphs: Iterable[CSIRGraph],
    ) -> Stage5ShadowReport:
        authoritative = tuple(authoritative_graphs)
        authoritative_fps = tuple(sorted({semantic_fingerprint(x) for x in authoritative}))
        reports = []
        matched = set()
        mismatched = set()
        for group in legacy_record_groups:
            report = self.compiler.compile_records(tuple(group))
            reports.append(report)
            if report.semantic_fingerprint is None:
                continue
            if report.semantic_fingerprint in authoritative_fps:
                matched.add(report.semantic_fingerprint)
            else:
                mismatched.add(report.semantic_fingerprint)
        return Stage5ShadowReport(
            tuple(reports),
            authoritative_fps,
            tuple(sorted(matched)),
            tuple(sorted(mismatched)),
        )


__all__ = [
    "CompatibilityCompilationReport",
    "LegacyCompatibilityCompiler",
    "LegacyExactAuthorityMap",
    "MigrationClassification",
    "Stage5ShadowComparator",
    "Stage5ShadowReport",
]
