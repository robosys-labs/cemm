"""Normalized record persistence for the compiled boot DB and overlays."""
from __future__ import annotations

import json
import sqlite3
from typing import Any, Mapping

from ..schema.model import FacetEntitlement, MeaningSchema, canonical_data
from ..language.model import (
    ConstructionRecord, FormSenseLinkRecord, LanguageFormRecord,
    LanguagePackRecord, LexicalSenseRecord,
)
from ..transitions.model import (
    CapabilityDependencyRecord,
    TransitionContractRecord,
    TransitionProofRecord,
)
from ..uol.model import (
    CapabilityDelta,
    ClaimOccurrence,
    EventOccurrence,
    ImpactAssessment,
    ImportanceAssessment,
    PropositionReferent,
    QuotedLiteral,
    Referent,
    SemanticApplication,
    StateDelta,
)
from .codec import (
    encode_record,
    record_context,
    record_fingerprints,
    record_interval,
    record_lifecycle,
    record_permission,
    record_ref,
)
from .model import (
    CapabilityInstance,
    ClaimHistoryRecord,
    ClaimRecord,
    DefaultRuleRecord,
    DependencyEdge,
    EpistemicAdmissionRecord,
    EvidenceRecord,
    IdentityFacetRecord,
    KnowledgeRecord,
    MaterializedViewRecord,
    RecordKind,
    ReferentTypeAssertion,
    SourceAssessmentRecord,
    StateAssignment,
)


def canonical_json(value: Any) -> str:
    return json.dumps(canonical_data(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def write_record(
    connection: sqlite3.Connection,
    record_kind: RecordKind,
    record: Any,
    *,
    revision: int,
    store_revision: int,
) -> tuple[str, str]:
    target_ref = record_ref(record_kind, record)
    content_fingerprint, complete_fingerprint = record_fingerprints(record_kind, record)
    valid_from, valid_to = record_interval(record_kind, record)
    payload = encode_record(record_kind, record)
    connection.execute(
        """
        INSERT INTO record_index(
            record_kind, record_ref, revision, lifecycle_status, context_ref,
            valid_from, valid_to, permission_ref, content_fingerprint,
            record_fingerprint, payload_json, store_revision
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(record_kind, record_ref, revision) DO UPDATE SET
            lifecycle_status=excluded.lifecycle_status,
            context_ref=excluded.context_ref,
            valid_from=excluded.valid_from,
            valid_to=excluded.valid_to,
            permission_ref=excluded.permission_ref,
            content_fingerprint=excluded.content_fingerprint,
            record_fingerprint=excluded.record_fingerprint,
            payload_json=excluded.payload_json,
            store_revision=excluded.store_revision
        """,
        (
            record_kind.value,
            target_ref,
            revision,
            record_lifecycle(record_kind, record),
            record_context(record_kind, record),
            valid_from,
            valid_to,
            record_permission(record_kind, record),
            content_fingerprint,
            complete_fingerprint,
            canonical_json(payload),
            store_revision,
        ),
    )
    _write_normalized(connection, record_kind, record, revision)
    return content_fingerprint, complete_fingerprint


def tombstone_record(
    connection: sqlite3.Connection,
    record_kind: RecordKind,
    target_ref: str,
    revision: int | None,
    *,
    reason: str,
    store_revision: int,
) -> None:
    connection.execute(
        """
        INSERT INTO record_tombstones(record_kind, record_ref, revision, reason, store_revision)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(record_kind, record_ref, revision) DO UPDATE SET
            reason=excluded.reason,
            store_revision=excluded.store_revision
        """,
        (record_kind.value, target_ref, revision, reason, store_revision),
    )


def _write_normalized(
    connection: sqlite3.Connection,
    record_kind: RecordKind,
    record: Any,
    revision: int,
) -> None:
    if record_kind == RecordKind.SCHEMA:
        _write_schema(connection, record)
    elif record_kind == RecordKind.FACET_ENTITLEMENT:
        _write_entitlement(connection, record)
    elif record_kind == RecordKind.REFERENT:
        _write_referent(connection, record)
    elif record_kind == RecordKind.TYPE_ASSERTION:
        _write_type_assertion(connection, record)
    elif record_kind == RecordKind.IDENTITY_FACET:
        _write_identity_facet(connection, record)
    elif record_kind == RecordKind.SEMANTIC_APPLICATION:
        _write_application(connection, record, revision)
    elif record_kind == RecordKind.PROPOSITION:
        _write_proposition(connection, record)
    elif record_kind == RecordKind.CLAIM_OCCURRENCE:
        _write_claim_occurrence(connection, record)
    elif record_kind == RecordKind.CLAIM_RECORD:
        _write_claim_record(connection, record)
    elif record_kind == RecordKind.CLAIM_HISTORY:
        _write_claim_history(connection, record)
    elif record_kind == RecordKind.SOURCE_ASSESSMENT:
        _write_source_assessment(connection, record)
    elif record_kind == RecordKind.EPISTEMIC_ADMISSION:
        _write_epistemic_admission(connection, record)
    elif record_kind == RecordKind.KNOWLEDGE:
        _write_knowledge(connection, record)
    elif record_kind == RecordKind.EVENT_OCCURRENCE:
        _write_event(connection, record)
    elif record_kind == RecordKind.STATE_ASSIGNMENT:
        _write_state_assignment(connection, record)
    elif record_kind == RecordKind.STATE_DELTA:
        _write_state_delta(connection, record)
    elif record_kind == RecordKind.CAPABILITY_INSTANCE:
        _write_capability(connection, record)
    elif record_kind == RecordKind.CAPABILITY_DELTA:
        _write_capability_delta(connection, record)
    elif record_kind == RecordKind.TRANSITION_CONTRACT:
        _write_transition_contract(connection, record)
    elif record_kind == RecordKind.CAPABILITY_DEPENDENCY:
        _write_capability_dependency(connection, record)
    elif record_kind == RecordKind.TRANSITION_PROOF:
        _write_transition_proof(connection, record)
    elif record_kind == RecordKind.IMPACT_ASSESSMENT:
        _write_impact(connection, record)
    elif record_kind == RecordKind.IMPORTANCE_ASSESSMENT:
        _write_importance(connection, record)
    elif record_kind == RecordKind.EVIDENCE:
        _write_evidence(connection, record)
    elif record_kind == RecordKind.DEFAULT_RULE:
        _write_default_rule(connection, record)
    elif record_kind == RecordKind.DEPENDENCY:
        _write_dependency(connection, record)
    elif record_kind == RecordKind.LANGUAGE_PACK:
        _write_language_pack(connection, record)
    elif record_kind == RecordKind.LANGUAGE_FORM:
        _write_language_form(connection, record)
    elif record_kind == RecordKind.LEXICAL_SENSE:
        _write_lexical_sense(connection, record)
    elif record_kind == RecordKind.FORM_SENSE_LINK:
        _write_form_sense_link(connection, record)
    elif record_kind == RecordKind.CONSTRUCTION:
        _write_construction(connection, record)
    elif record_kind == RecordKind.MATERIALIZED_VIEW:
        _write_view(connection, record)
    elif record_kind in {
        RecordKind.LEARNING_PACKAGE, RecordKind.LEARNING_FRONTIER,
        RecordKind.LEARNING_EVIDENCE_LINK, RecordKind.COMPETENCE_RESULT,
        RecordKind.PROMOTION_DECISION, RecordKind.LEARNING_INVALIDATION,
    }:
        _write_learning_record(connection, record_kind, record, revision)
    elif record_kind in {
        RecordKind.IMPACT_RULE, RecordKind.IMPACT_PROOF, RecordKind.IMPORTANCE_EVIDENCE,
        RecordKind.IMPORTANCE_POLICY, RecordKind.SIGNIFICANCE_ASSESSMENT,
        RecordKind.RESPONSE_POLICY_RULE, RecordKind.SEMANTIC_OBLIGATION,
        RecordKind.GOAL_CANDIDATE, RecordKind.GOAL_CONFLICT, RecordKind.GOAL_DECISION,
    }:
        _write_phase14_15_record(connection, record_kind, record, revision)


def _write_phase14_15_record(
    connection: sqlite3.Connection, record_kind: RecordKind, record: Any, revision: int
) -> None:
    payload = encode_record(record_kind, record)
    table = "phase14_records" if record_kind in {
        RecordKind.IMPACT_RULE, RecordKind.IMPACT_PROOF, RecordKind.IMPORTANCE_EVIDENCE,
        RecordKind.IMPORTANCE_POLICY, RecordKind.SIGNIFICANCE_ASSESSMENT,
    } else "phase15_records"
    source_ref = getattr(record, "source_ref", None)
    source_pin = getattr(record, "source_pin", None)
    if source_ref is None and source_pin is not None:
        source_ref = source_pin.record_ref
    stakeholder_ref = getattr(record, "stakeholder_ref", None)
    affected_ref = getattr(record, "affected_ref", None)
    impact = getattr(record, "impact", None)
    if impact is not None:
        stakeholder_ref = getattr(impact, "stakeholder_ref", stakeholder_ref)
        affected_ref = getattr(impact, "affected_ref", affected_ref)
    if table == "phase14_records":
        connection.execute(
            """INSERT OR REPLACE INTO phase14_records(
                record_kind, record_ref, revision, source_ref, stakeholder_ref, affected_ref,
                context_ref, permission_ref, lifecycle_status, use_operation, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (record_kind.value, record_ref(record_kind, record), revision, source_ref, stakeholder_ref, affected_ref,
             record_context(record_kind, record), record_permission(record_kind, record), record_lifecycle(record_kind, record),
             getattr(getattr(record, "use_operation", None), "value", getattr(record, "use_operation", None)), canonical_json(payload)),
        )
    else:
        target_refs = getattr(record, "target_refs", ())
        connection.execute(
            """INSERT OR REPLACE INTO phase15_records(
                record_kind, record_ref, revision, goal_schema_ref, operation, target_refs_json,
                authorized, context_ref, permission_ref, lifecycle_status, payload_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (record_kind.value, record_ref(record_kind, record), revision, getattr(record, "goal_schema_ref", None),
             getattr(getattr(record, "operation", None), "value", getattr(record, "operation", None)), canonical_json(target_refs),
             None if not hasattr(record, "authorized") else int(bool(record.authorized)), record_context(record_kind, record),
             record_permission(record_kind, record), record_lifecycle(record_kind, record), canonical_json(payload)),
        )


def _write_learning_record(
    connection: sqlite3.Connection, record_kind: RecordKind, record: Any, revision: int
) -> None:
    package_ref = getattr(record, "package_ref", None)
    package_revision = getattr(record, "package_revision", None)
    lifecycle = record_lifecycle(record_kind, record)
    operation = getattr(record, "use_operation", None)
    polarity = getattr(record, "polarity", None)
    decision = getattr(record, "decision", None)
    connection.execute(
        """
        INSERT INTO learning_records(
            record_kind, record_ref, revision, package_ref, package_revision,
            lifecycle_status, use_operation, polarity, decision, permission_ref, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(record_kind, record_ref, revision) DO UPDATE SET
            package_ref=excluded.package_ref,
            package_revision=excluded.package_revision,
            lifecycle_status=excluded.lifecycle_status,
            use_operation=excluded.use_operation,
            polarity=excluded.polarity,
            decision=excluded.decision,
            permission_ref=excluded.permission_ref,
            payload_json=excluded.payload_json
        """,
        (
            record_kind.value,
            record_ref(record_kind, record),
            revision,
            package_ref,
            package_revision,
            lifecycle,
            None if operation is None else getattr(operation, "value", str(operation)),
            None if polarity is None else getattr(polarity, "value", str(polarity)),
            None if decision is None else getattr(decision, "value", str(decision)),
            record_permission(record_kind, record),
            canonical_json(encode_record(record_kind, record)),
        ),
    )


def _write_schema(connection: sqlite3.Connection, schema: MeaningSchema) -> None:
    connection.execute(
        """
        INSERT INTO semantic_schemas(
            schema_ref, revision, schema_class, semantic_key, status, scope_ref,
            confidence, permission_ref, provenance_json, use_profile_json,
            dependencies_json, competence_hooks_json, valid_from, valid_to,
            content_fingerprint, record_fingerprint
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(schema_ref, revision) DO UPDATE SET
            schema_class=excluded.schema_class,
            semantic_key=excluded.semantic_key,
            status=excluded.status,
            scope_ref=excluded.scope_ref,
            confidence=excluded.confidence,
            permission_ref=excluded.permission_ref,
            provenance_json=excluded.provenance_json,
            use_profile_json=excluded.use_profile_json,
            dependencies_json=excluded.dependencies_json,
            competence_hooks_json=excluded.competence_hooks_json,
            valid_from=excluded.valid_from,
            valid_to=excluded.valid_to,
            content_fingerprint=excluded.content_fingerprint,
            record_fingerprint=excluded.record_fingerprint
        """,
        (
            schema.schema_ref,
            schema.revision,
            schema.schema_class.value,
            schema.semantic_key,
            schema.lifecycle_status.value,
            schema.scope_ref,
            schema.confidence,
            schema.permission_ref,
            canonical_json(schema.provenance),
            canonical_json(schema.use_profile),
            canonical_json(schema.dependencies),
            canonical_json(schema.competence_hooks),
            schema.valid_from,
            schema.valid_to,
            schema.content_fingerprint,
            schema.record_fingerprint,
        ),
    )
    connection.execute(
        "DELETE FROM schema_parents WHERE child_ref=? AND child_revision=?",
        (schema.schema_ref, schema.revision),
    )
    connection.executemany(
        """
        INSERT INTO schema_parents(
            child_ref, child_revision, parent_ref, parent_revision_policy,
            parent_revision, inheritance_kind, priority
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            (
                schema.schema_ref,
                schema.revision,
                link.parent_ref,
                link.revision_policy.value,
                link.revision,
                link.inheritance_kind,
                link.priority,
            )
            for link in schema.parent_links
        ),
    )
    connection.execute(
        "DELETE FROM schema_ports WHERE schema_ref=? AND schema_revision=?",
        (schema.schema_ref, schema.revision),
    )
    connection.executemany(
        """
        INSERT INTO schema_ports(
            schema_ref, schema_revision, port_ref, filler_classes_json,
            accepted_type_refs_json, accepted_storage_kinds_json,
            accepted_schema_classes_json, cardinality_min, cardinality_max,
            queryable, open_binding_purposes_json, role_family,
            context_policy, time_policy, identity_contribution, ordered_fillers,
            constraint_refs_json, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            (
                schema.schema_ref,
                schema.revision,
                port.port_ref,
                canonical_json(port.filler_classes),
                canonical_json(port.accepted_type_refs),
                canonical_json(port.accepted_storage_kinds),
                canonical_json(port.accepted_schema_classes),
                port.cardinality.minimum,
                port.cardinality.maximum,
                int(port.queryable),
                canonical_json(port.open_binding_purposes),
                port.role_family,
                port.context_policy,
                port.time_policy,
                int(port.identity_contribution),
                int(port.ordered_fillers),
                canonical_json(port.constraint_refs),
                canonical_json(port.metadata),
            )
            for port in schema.local_ports
        ),
    )


def _write_entitlement(connection: sqlite3.Connection, entitlement: FacetEntitlement) -> None:
    connection.execute(
        """
        INSERT INTO facet_entitlements(
            entitlement_ref, revision, owner_type_ref, facet_ref, applicability,
            activation_policy, inheritance_policy, value_domain_refs_json,
            default_rule_refs_json, context_constraints_json,
            temporal_constraints_json, dependencies_json, status, scope_ref,
            confidence, permission_ref, content_fingerprint, record_fingerprint
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(entitlement_ref, revision) DO UPDATE SET
            owner_type_ref=excluded.owner_type_ref,
            facet_ref=excluded.facet_ref,
            applicability=excluded.applicability,
            activation_policy=excluded.activation_policy,
            inheritance_policy=excluded.inheritance_policy,
            value_domain_refs_json=excluded.value_domain_refs_json,
            default_rule_refs_json=excluded.default_rule_refs_json,
            context_constraints_json=excluded.context_constraints_json,
            temporal_constraints_json=excluded.temporal_constraints_json,
            dependencies_json=excluded.dependencies_json,
            status=excluded.status,
            scope_ref=excluded.scope_ref,
            confidence=excluded.confidence,
            permission_ref=excluded.permission_ref,
            content_fingerprint=excluded.content_fingerprint,
            record_fingerprint=excluded.record_fingerprint
        """,
        (
            entitlement.entitlement_ref,
            entitlement.revision,
            entitlement.owner_type_ref,
            entitlement.facet_ref,
            entitlement.applicability.value,
            entitlement.activation_policy,
            entitlement.inheritance_policy.value,
            canonical_json(entitlement.value_domain_refs),
            canonical_json(entitlement.default_rule_refs),
            canonical_json(entitlement.context_constraints),
            canonical_json(entitlement.temporal_constraints),
            canonical_json(entitlement.dependencies),
            entitlement.lifecycle_status.value,
            entitlement.scope_ref,
            entitlement.confidence,
            entitlement.permission_ref,
            entitlement.content_fingerprint,
            entitlement.record_fingerprint,
        ),
    )


def _write_referent(connection: sqlite3.Connection, referent: Referent) -> None:
    connection.execute(
        """
        INSERT INTO referents(
            referent_ref, revision, storage_kind, identity_status, scope_ref,
            context_refs_json, valid_time_ref, permission_ref, type_refs_json,
            identity_facet_refs_json, provenance_refs_json, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(referent_ref, revision) DO UPDATE SET
            storage_kind=excluded.storage_kind,
            identity_status=excluded.identity_status,
            scope_ref=excluded.scope_ref,
            context_refs_json=excluded.context_refs_json,
            valid_time_ref=excluded.valid_time_ref,
            permission_ref=excluded.permission_ref,
            type_refs_json=excluded.type_refs_json,
            identity_facet_refs_json=excluded.identity_facet_refs_json,
            provenance_refs_json=excluded.provenance_refs_json,
            metadata_json=excluded.metadata_json
        """,
        (
            referent.referent_ref,
            referent.revision,
            referent.storage_kind.value,
            referent.identity_status.value,
            referent.scope_ref,
            canonical_json(referent.context_refs),
            referent.valid_time_ref,
            referent.permission_ref,
            canonical_json(referent.type_refs),
            canonical_json(referent.identity_facet_refs),
            canonical_json(referent.provenance_refs),
            canonical_json(referent.metadata),
        ),
    )


def _write_type_assertion(connection: sqlite3.Connection, item: ReferentTypeAssertion) -> None:
    connection.execute(
        """
        INSERT INTO referent_type_assertions(
            assertion_ref, referent_ref, type_schema_ref, type_revision, status,
            confidence, context_ref, valid_from, valid_to, evidence_refs_json,
            source_refs_json, proof_refs_json, permission_ref
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(assertion_ref) DO UPDATE SET
            referent_ref=excluded.referent_ref,
            type_schema_ref=excluded.type_schema_ref,
            type_revision=excluded.type_revision,
            status=excluded.status,
            confidence=excluded.confidence,
            context_ref=excluded.context_ref,
            valid_from=excluded.valid_from,
            valid_to=excluded.valid_to,
            evidence_refs_json=excluded.evidence_refs_json,
            source_refs_json=excluded.source_refs_json,
            proof_refs_json=excluded.proof_refs_json,
            permission_ref=excluded.permission_ref
        """,
        (
            item.assertion_ref,
            item.referent_ref,
            item.type_schema_ref,
            item.type_revision,
            item.status.value,
            item.confidence,
            item.context_ref,
            item.valid_from,
            item.valid_to,
            canonical_json(item.evidence_refs),
            canonical_json(item.source_refs),
            canonical_json(item.proof_refs),
            item.permission_ref,
        ),
    )


def _write_identity_facet(connection: sqlite3.Connection, item: IdentityFacetRecord) -> None:
    connection.execute(
        """
        INSERT INTO identity_facets(
            identity_facet_ref, referent_ref, facet_schema_ref, normalized_value,
            anchor_ref, confidence, evidence_refs_json, context_ref
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(identity_facet_ref) DO UPDATE SET
            referent_ref=excluded.referent_ref,
            facet_schema_ref=excluded.facet_schema_ref,
            normalized_value=excluded.normalized_value,
            anchor_ref=excluded.anchor_ref,
            confidence=excluded.confidence,
            evidence_refs_json=excluded.evidence_refs_json,
            context_ref=excluded.context_ref
        """,
        (
            item.identity_facet_ref,
            item.referent_ref,
            item.facet_schema_ref,
            item.normalized_value,
            item.anchor_ref,
            item.confidence,
            canonical_json(item.evidence_refs),
            item.context_ref,
        ),
    )


def _write_application(connection: sqlite3.Connection, application: SemanticApplication, revision: int) -> None:
    connection.execute(
        """
        INSERT INTO semantic_applications(
            application_ref, record_revision, schema_ref, schema_revision,
            context_ref, use_operation, valid_time_ref, polarity, confidence,
            assumptions_json, evidence_refs_json, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(application_ref, record_revision) DO UPDATE SET
            schema_ref=excluded.schema_ref,
            schema_revision=excluded.schema_revision,
            context_ref=excluded.context_ref,
            use_operation=excluded.use_operation,
            valid_time_ref=excluded.valid_time_ref,
            polarity=excluded.polarity,
            confidence=excluded.confidence,
            assumptions_json=excluded.assumptions_json,
            evidence_refs_json=excluded.evidence_refs_json,
            metadata_json=excluded.metadata_json
        """,
        (
            application.application_ref,
            revision,
            application.schema_ref,
            application.schema_revision,
            application.context_ref,
            application.use_operation.value,
            application.valid_time_ref,
            application.polarity.value,
            application.confidence,
            canonical_json(application.assumptions),
            canonical_json(application.evidence_refs),
            canonical_json(application.metadata),
        ),
    )
    connection.execute(
        "DELETE FROM application_bindings WHERE application_ref=? AND application_revision=?",
        (application.application_ref, revision),
    )
    rows = []
    for binding in application.bindings:
        for ordinal, filler in enumerate(binding.fillers):
            if isinstance(filler, QuotedLiteral):
                filler_class = "quoted_literal"
                filler_ref = filler.literal_ref
            else:
                filler_class = filler.filler_class.value
                filler_ref = filler.ref
            rows.append((
                application.application_ref,
                revision,
                binding.port_ref,
                filler_class,
                filler_ref,
                ordinal,
                binding.confidence,
                canonical_json(binding.evidence_refs),
                canonical_json(binding.assumptions),
                int(binding.ordered),
                None if binding.open_binding_purpose is None else binding.open_binding_purpose.value,
            ))
    connection.executemany(
        """
        INSERT INTO application_bindings(
            application_ref, application_revision, port_ref, filler_class,
            filler_ref, ordinal, confidence, evidence_refs_json,
            assumptions_json, ordered_fillers, open_binding_purpose
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _write_proposition(connection: sqlite3.Connection, proposition: PropositionReferent) -> None:
    revision = proposition.referent.revision
    connection.execute(
        """
        INSERT INTO propositions(
            proposition_ref, revision, context_ref, polarity, modality_refs_json,
            attribution_refs_json, valid_time_ref, evidence_refs_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(proposition_ref, revision) DO UPDATE SET
            context_ref=excluded.context_ref,
            polarity=excluded.polarity,
            modality_refs_json=excluded.modality_refs_json,
            attribution_refs_json=excluded.attribution_refs_json,
            valid_time_ref=excluded.valid_time_ref,
            evidence_refs_json=excluded.evidence_refs_json
        """,
        (
            proposition.proposition_ref,
            revision,
            proposition.context_ref,
            proposition.polarity.value,
            canonical_json(proposition.modality_application_refs),
            canonical_json(proposition.attribution_refs),
            proposition.valid_time_ref,
            canonical_json(proposition.evidence_refs),
        ),
    )
    connection.execute(
        "DELETE FROM proposition_content WHERE proposition_ref=? AND proposition_revision=?",
        (proposition.proposition_ref, revision),
    )
    connection.executemany(
        """
        INSERT INTO proposition_content(
            proposition_ref, proposition_revision, content_ref, content_kind, ordinal
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            (
                proposition.proposition_ref,
                revision,
                filler.ref,
                filler.filler_class.value,
                ordinal,
            )
            for ordinal, filler in enumerate(proposition.content_refs)
        ),
    )


def _write_claim_occurrence(connection: sqlite3.Connection, claim: ClaimOccurrence) -> None:
    connection.execute(
        """
        INSERT INTO claim_occurrences(
            claim_ref, revision, claimant_ref, audience_refs_json,
            proposition_ref, claim_force, source_context_ref,
            reported_context_ref, time_ref, certainty_expression_ref,
            evidence_offered_refs_json, evidence_refs_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(claim_ref, revision) DO UPDATE SET
            claimant_ref=excluded.claimant_ref,
            audience_refs_json=excluded.audience_refs_json,
            proposition_ref=excluded.proposition_ref,
            claim_force=excluded.claim_force,
            source_context_ref=excluded.source_context_ref,
            reported_context_ref=excluded.reported_context_ref,
            time_ref=excluded.time_ref,
            certainty_expression_ref=excluded.certainty_expression_ref,
            evidence_offered_refs_json=excluded.evidence_offered_refs_json,
            evidence_refs_json=excluded.evidence_refs_json
        """,
        (
            claim.claim_ref,
            claim.referent.revision,
            claim.claimant_ref,
            canonical_json(claim.audience_refs),
            claim.proposition_ref,
            claim.claim_force.value,
            claim.source_context_ref,
            claim.reported_context_ref,
            claim.time_ref,
            claim.certainty_expression_ref,
            canonical_json(claim.evidence_offered_refs),
            canonical_json(claim.evidence_refs),
        ),
    )


def _write_claim_record(connection: sqlite3.Connection, item: ClaimRecord) -> None:
    connection.execute(
        """
        INSERT INTO claim_records(
            claim_record_ref, claim_occurrence_ref, proposition_ref, source_ref,
            source_context_ref, reported_context_ref, commitment_strength,
            permission_ref, evidence_refs_json, superseded_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(claim_record_ref) DO UPDATE SET
            claim_occurrence_ref=excluded.claim_occurrence_ref,
            proposition_ref=excluded.proposition_ref,
            source_ref=excluded.source_ref,
            source_context_ref=excluded.source_context_ref,
            reported_context_ref=excluded.reported_context_ref,
            commitment_strength=excluded.commitment_strength,
            permission_ref=excluded.permission_ref,
            evidence_refs_json=excluded.evidence_refs_json,
            superseded_by=excluded.superseded_by
        """,
        (
            item.claim_record_ref,
            item.claim_occurrence_ref,
            item.proposition_ref,
            item.source_ref,
            item.source_context_ref,
            item.reported_context_ref,
            item.commitment_strength,
            item.permission_ref,
            canonical_json(item.evidence_refs),
            item.superseded_by,
        ),
    )


def _write_claim_history(connection: sqlite3.Connection, item: ClaimHistoryRecord) -> None:
    connection.execute(
        """
        INSERT INTO claim_history_records(
            history_ref, revision, claim_record_ref, action, source_ref, context_ref,
            evidence_refs_json, target_claim_record_ref, occurred_at,
            supersedes_revision, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(history_ref, revision) DO UPDATE SET
            claim_record_ref=excluded.claim_record_ref,
            action=excluded.action,
            source_ref=excluded.source_ref,
            context_ref=excluded.context_ref,
            evidence_refs_json=excluded.evidence_refs_json,
            target_claim_record_ref=excluded.target_claim_record_ref,
            occurred_at=excluded.occurred_at,
            supersedes_revision=excluded.supersedes_revision,
            metadata_json=excluded.metadata_json
        """,
        (
            item.history_ref, item.revision, item.claim_record_ref, item.action.value,
            item.source_ref, item.context_ref, canonical_json(item.evidence_refs),
            item.target_claim_record_ref, item.occurred_at, item.supersedes_revision,
            canonical_json(item.metadata),
        ),
    )


def _write_source_assessment(connection: sqlite3.Connection, item: SourceAssessmentRecord) -> None:
    connection.execute(
        """
        INSERT INTO source_assessment_records(
            assessment_ref, revision, source_ref, authority, reliability,
            access_quality, bias_risk, context_ref, evidence_refs_json,
            supersedes_revision, valid_from, valid_to, permission_ref, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(assessment_ref, revision) DO UPDATE SET
            source_ref=excluded.source_ref, authority=excluded.authority,
            reliability=excluded.reliability, access_quality=excluded.access_quality,
            bias_risk=excluded.bias_risk, context_ref=excluded.context_ref,
            evidence_refs_json=excluded.evidence_refs_json,
            supersedes_revision=excluded.supersedes_revision, valid_from=excluded.valid_from,
            valid_to=excluded.valid_to, permission_ref=excluded.permission_ref,
            metadata_json=excluded.metadata_json
        """,
        (
            item.assessment_ref, item.revision, item.source_ref, item.authority,
            item.reliability, item.access_quality, item.bias_risk, item.context_ref,
            canonical_json(item.evidence_refs), item.supersedes_revision, item.valid_from,
            item.valid_to, item.permission_ref, canonical_json(item.metadata),
        ),
    )


def _write_epistemic_admission(connection: sqlite3.Connection, item: EpistemicAdmissionRecord) -> None:
    connection.execute(
        """
        INSERT INTO epistemic_admissions(
            admission_ref, revision, proposition_ref, source_context_ref, target_context_ref,
            decision, truth_status, confidence, source_refs_json, source_assessment_pins_json,
            evidence_refs_json, proof_refs_json, policy_ref, authorization_ref, permission_ref, sensitivity, lifecycle_status,
            valid_time_ref, valid_from, valid_to, retracts_admission_ref,
            supersedes_revision, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(admission_ref, revision) DO UPDATE SET
            proposition_ref=excluded.proposition_ref,
            source_context_ref=excluded.source_context_ref,
            target_context_ref=excluded.target_context_ref,
            decision=excluded.decision,
            truth_status=excluded.truth_status,
            confidence=excluded.confidence,
            source_refs_json=excluded.source_refs_json,
            source_assessment_pins_json=excluded.source_assessment_pins_json,
            evidence_refs_json=excluded.evidence_refs_json,
            proof_refs_json=excluded.proof_refs_json,
            policy_ref=excluded.policy_ref,
            authorization_ref=excluded.authorization_ref,
            permission_ref=excluded.permission_ref,
            sensitivity=excluded.sensitivity,
            lifecycle_status=excluded.lifecycle_status,
            valid_time_ref=excluded.valid_time_ref,
            valid_from=excluded.valid_from,
            valid_to=excluded.valid_to,
            retracts_admission_ref=excluded.retracts_admission_ref,
            supersedes_revision=excluded.supersedes_revision,
            metadata_json=excluded.metadata_json
        """,
        (
            item.admission_ref, item.revision, item.proposition_ref,
            item.source_context_ref, item.target_context_ref, item.decision.value,
            item.truth_status.value, item.confidence, canonical_json(item.source_refs),
            canonical_json(item.source_assessment_pins), canonical_json(item.evidence_refs),
            canonical_json(item.proof_refs),
            item.policy_ref, item.authorization_ref, item.permission_ref, item.sensitivity, item.lifecycle_status.value,
            item.valid_time_ref, item.valid_from, item.valid_to, item.retracts_admission_ref,
            item.supersedes_revision, canonical_json(item.metadata),
        ),
    )


def _write_knowledge(connection: sqlite3.Connection, item: KnowledgeRecord) -> None:
    connection.execute(
        """
        INSERT INTO knowledge_records(
            knowledge_ref, proposition_ref, truth_status, confidence, context_ref,
            source_refs_json, evidence_refs_json, permission_ref, sensitivity,
            valid_time_ref, valid_from, valid_to, support_lineage_refs_json,
            derivation_refs_json, superseded_by, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(knowledge_ref) DO UPDATE SET
            proposition_ref=excluded.proposition_ref,
            truth_status=excluded.truth_status,
            confidence=excluded.confidence,
            context_ref=excluded.context_ref,
            source_refs_json=excluded.source_refs_json,
            evidence_refs_json=excluded.evidence_refs_json,
            permission_ref=excluded.permission_ref,
            sensitivity=excluded.sensitivity,
            valid_time_ref=excluded.valid_time_ref,
            valid_from=excluded.valid_from,
            valid_to=excluded.valid_to,
            support_lineage_refs_json=excluded.support_lineage_refs_json,
            derivation_refs_json=excluded.derivation_refs_json,
            superseded_by=excluded.superseded_by,
            metadata_json=excluded.metadata_json
        """,
        (
            item.knowledge_ref,
            item.proposition_ref,
            item.truth_status.value,
            item.confidence,
            item.context_ref,
            canonical_json(item.source_refs),
            canonical_json(item.evidence_refs),
            item.permission_ref,
            item.sensitivity,
            item.valid_time_ref,
            item.valid_from,
            item.valid_to,
            canonical_json(item.support_lineage_refs),
            canonical_json(item.derivation_refs),
            item.superseded_by,
            canonical_json(item.metadata),
        ),
    )


def _write_event(connection: sqlite3.Connection, event: EventOccurrence) -> None:
    connection.execute(
        """
        INSERT INTO event_occurrences(
            event_ref, revision, event_schema_ref, event_schema_revision,
            participant_application_ref, occurrence_status, context_ref,
            time_ref, place_ref, cause_refs_json, result_refs_json,
            provenance_refs_json, admission_refs_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(event_ref, revision) DO UPDATE SET
            event_schema_ref=excluded.event_schema_ref,
            event_schema_revision=excluded.event_schema_revision,
            participant_application_ref=excluded.participant_application_ref,
            occurrence_status=excluded.occurrence_status,
            context_ref=excluded.context_ref,
            time_ref=excluded.time_ref,
            place_ref=excluded.place_ref,
            cause_refs_json=excluded.cause_refs_json,
            result_refs_json=excluded.result_refs_json,
            provenance_refs_json=excluded.provenance_refs_json,
            admission_refs_json=excluded.admission_refs_json
        """,
        (
            event.event_ref,
            event.referent.revision,
            event.event_schema_ref,
            event.event_schema_revision,
            event.participant_application_ref,
            event.occurrence_status.value,
            event.context_ref,
            event.time_ref,
            event.place_ref,
            canonical_json(event.cause_refs),
            canonical_json(event.result_refs),
            canonical_json(event.provenance_refs),
            canonical_json(event.admission_refs),
        ),
    )


def _write_state_assignment(connection: sqlite3.Connection, item: StateAssignment) -> None:
    connection.execute(
        """
        INSERT INTO state_assignments(
            assignment_ref, holder_ref, dimension_ref, dimension_revision,
            value_ref, value_revision, status, context_ref, confidence,
            valid_from, valid_to, evidence_refs_json, proof_refs_json,
            source_refs_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(assignment_ref) DO UPDATE SET
            holder_ref=excluded.holder_ref,
            dimension_ref=excluded.dimension_ref,
            dimension_revision=excluded.dimension_revision,
            value_ref=excluded.value_ref,
            value_revision=excluded.value_revision,
            status=excluded.status,
            context_ref=excluded.context_ref,
            confidence=excluded.confidence,
            valid_from=excluded.valid_from,
            valid_to=excluded.valid_to,
            evidence_refs_json=excluded.evidence_refs_json,
            proof_refs_json=excluded.proof_refs_json,
            source_refs_json=excluded.source_refs_json
        """,
        (
            item.assignment_ref,
            item.holder_ref,
            item.dimension_ref,
            item.dimension_revision,
            item.value_ref,
            item.value_revision,
            item.status.value,
            item.context_ref,
            item.confidence,
            item.valid_from,
            item.valid_to,
            canonical_json(item.evidence_refs),
            canonical_json(item.proof_refs),
            canonical_json(item.source_refs),
        ),
    )


def _write_state_delta(connection: sqlite3.Connection, item: StateDelta) -> None:
    connection.execute(
        """
        INSERT INTO state_deltas(
            delta_ref, trigger_ref, holder_ref, dimension_ref, dimension_revision,
            operation, from_value_ref, from_value_revision, to_value_ref,
            to_value_revision, magnitude_ref, duration_ref, context_ref,
            effective_time_ref, confidence, proof_refs_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(delta_ref) DO UPDATE SET
            trigger_ref=excluded.trigger_ref,
            holder_ref=excluded.holder_ref,
            dimension_ref=excluded.dimension_ref,
            dimension_revision=excluded.dimension_revision,
            operation=excluded.operation,
            from_value_ref=excluded.from_value_ref,
            from_value_revision=excluded.from_value_revision,
            to_value_ref=excluded.to_value_ref,
            to_value_revision=excluded.to_value_revision,
            magnitude_ref=excluded.magnitude_ref,
            duration_ref=excluded.duration_ref,
            context_ref=excluded.context_ref,
            effective_time_ref=excluded.effective_time_ref,
            confidence=excluded.confidence,
            proof_refs_json=excluded.proof_refs_json
        """,
        (
            item.delta_ref,
            item.trigger_ref,
            item.holder_ref,
            item.dimension_ref,
            item.dimension_revision,
            item.operation.value,
            item.from_value_ref,
            item.from_value_revision,
            item.to_value_ref,
            item.to_value_revision,
            item.magnitude_ref,
            item.duration_ref,
            item.context_ref,
            item.effective_time_ref,
            item.confidence,
            canonical_json(item.proof_refs),
        ),
    )


def _write_capability(connection: sqlite3.Connection, item: CapabilityInstance) -> None:
    connection.execute(
        """
        INSERT INTO capability_instances(
            capability_ref, holder_ref, action_schema_ref, action_schema_revision,
            status, confidence, context_ref, valid_from, valid_to,
            dependency_refs_json, evidence_refs_json, proof_refs_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(capability_ref) DO UPDATE SET
            holder_ref=excluded.holder_ref,
            action_schema_ref=excluded.action_schema_ref,
            action_schema_revision=excluded.action_schema_revision,
            status=excluded.status,
            confidence=excluded.confidence,
            context_ref=excluded.context_ref,
            valid_from=excluded.valid_from,
            valid_to=excluded.valid_to,
            dependency_refs_json=excluded.dependency_refs_json,
            evidence_refs_json=excluded.evidence_refs_json,
            proof_refs_json=excluded.proof_refs_json
        """,
        (
            item.capability_ref,
            item.holder_ref,
            item.action_schema_ref,
            item.action_schema_revision,
            item.status.value,
            item.confidence,
            item.context_ref,
            item.valid_from,
            item.valid_to,
            canonical_json(item.dependency_refs),
            canonical_json(item.evidence_refs),
            canonical_json(item.proof_refs),
        ),
    )


def _write_capability_delta(connection: sqlite3.Connection, item: CapabilityDelta) -> None:
    connection.execute(
        """
        INSERT INTO capability_deltas(
            delta_ref, trigger_ref, holder_ref, action_schema_ref,
            action_schema_revision, prior_status, new_status, context_ref,
            effective_time_ref, dependency_ref, confidence, proof_refs_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(delta_ref) DO UPDATE SET
            trigger_ref=excluded.trigger_ref,
            holder_ref=excluded.holder_ref,
            action_schema_ref=excluded.action_schema_ref,
            action_schema_revision=excluded.action_schema_revision,
            prior_status=excluded.prior_status,
            new_status=excluded.new_status,
            context_ref=excluded.context_ref,
            effective_time_ref=excluded.effective_time_ref,
            dependency_ref=excluded.dependency_ref,
            confidence=excluded.confidence,
            proof_refs_json=excluded.proof_refs_json
        """,
        (
            item.delta_ref,
            item.trigger_ref,
            item.holder_ref,
            item.action_schema_ref,
            item.action_schema_revision,
            item.prior_status.value,
            item.new_status.value,
            item.context_ref,
            item.effective_time_ref,
            item.dependency_ref,
            item.confidence,
            canonical_json(item.proof_refs),
        ),
    )


def _write_impact(connection: sqlite3.Connection, item: ImpactAssessment) -> None:
    connection.execute(
        """
        INSERT INTO impact_assessments(
            assessment_ref, source_event_or_state_ref, affected_ref,
            stakeholder_ref, affected_facet_refs_json, direction, valence,
            context_ref, reversibility, magnitude_ref, duration_ref,
            confidence, importance_ref, proof_refs_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(assessment_ref) DO UPDATE SET
            source_event_or_state_ref=excluded.source_event_or_state_ref,
            affected_ref=excluded.affected_ref,
            stakeholder_ref=excluded.stakeholder_ref,
            affected_facet_refs_json=excluded.affected_facet_refs_json,
            direction=excluded.direction,
            valence=excluded.valence,
            context_ref=excluded.context_ref,
            reversibility=excluded.reversibility,
            magnitude_ref=excluded.magnitude_ref,
            duration_ref=excluded.duration_ref,
            confidence=excluded.confidence,
            importance_ref=excluded.importance_ref,
            proof_refs_json=excluded.proof_refs_json
        """,
        (
            item.assessment_ref,
            item.source_event_or_state_ref,
            item.affected_ref,
            item.stakeholder_ref,
            canonical_json(item.affected_facet_refs),
            item.direction.value,
            item.valence.value,
            item.context_ref,
            item.reversibility.value,
            item.magnitude_ref,
            item.duration_ref,
            item.confidence,
            item.importance_ref,
            canonical_json(item.proof_refs),
        ),
    )


def _write_importance(connection: sqlite3.Connection, item: ImportanceAssessment) -> None:
    connection.execute(
        """
        INSERT INTO importance_assessments(
            assessment_ref, subject_ref, stakeholder_ref, context_ref, score,
            importance_class, evidence_refs_json, reasons_json, valid_time_ref
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(assessment_ref) DO UPDATE SET
            subject_ref=excluded.subject_ref,
            stakeholder_ref=excluded.stakeholder_ref,
            context_ref=excluded.context_ref,
            score=excluded.score,
            importance_class=excluded.importance_class,
            evidence_refs_json=excluded.evidence_refs_json,
            reasons_json=excluded.reasons_json,
            valid_time_ref=excluded.valid_time_ref
        """,
        (
            item.assessment_ref,
            item.subject_ref,
            item.stakeholder_ref,
            item.context_ref,
            item.score,
            item.importance_class.value,
            canonical_json(item.evidence_refs),
            canonical_json(item.reasons),
            item.valid_time_ref,
        ),
    )


def _write_evidence(connection: sqlite3.Connection, item: EvidenceRecord) -> None:
    connection.execute(
        """
        INSERT INTO evidence_records(
            evidence_ref, source_ref, confidence, lineage_ref, context_ref,
            observed_at, span_start, span_end, permission_ref, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(evidence_ref) DO UPDATE SET
            source_ref=excluded.source_ref,
            confidence=excluded.confidence,
            lineage_ref=excluded.lineage_ref,
            context_ref=excluded.context_ref,
            observed_at=excluded.observed_at,
            span_start=excluded.span_start,
            span_end=excluded.span_end,
            permission_ref=excluded.permission_ref,
            metadata_json=excluded.metadata_json
        """,
        (
            item.evidence_ref,
            item.source_ref,
            item.confidence,
            item.lineage_ref,
            item.context_ref,
            item.observed_at,
            item.span_start,
            item.span_end,
            item.permission_ref,
            canonical_json(item.metadata),
        ),
    )


def _write_default_rule(connection: sqlite3.Connection, item: DefaultRuleRecord) -> None:
    connection.execute(
        """
        INSERT INTO default_rules(
            rule_ref, revision, supersedes_revision, scope_ref, target_facet_ref,
            expected_dimension_ref, expected_dimension_revision, expected_value_ref,
            expected_value_revision, holder_type_refs_json, condition_refs_json,
            defeater_refs_json, context_constraints_json, temporal_constraints_json,
            priority, confidence, lifecycle_status, permission_ref, evidence_refs_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(rule_ref, revision) DO UPDATE SET
            supersedes_revision=excluded.supersedes_revision,
            scope_ref=excluded.scope_ref,
            target_facet_ref=excluded.target_facet_ref,
            expected_dimension_ref=excluded.expected_dimension_ref,
            expected_dimension_revision=excluded.expected_dimension_revision,
            expected_value_ref=excluded.expected_value_ref,
            expected_value_revision=excluded.expected_value_revision,
            holder_type_refs_json=excluded.holder_type_refs_json,
            condition_refs_json=excluded.condition_refs_json,
            defeater_refs_json=excluded.defeater_refs_json,
            context_constraints_json=excluded.context_constraints_json,
            temporal_constraints_json=excluded.temporal_constraints_json,
            priority=excluded.priority,
            confidence=excluded.confidence,
            lifecycle_status=excluded.lifecycle_status,
            permission_ref=excluded.permission_ref,
            evidence_refs_json=excluded.evidence_refs_json
        """,
        (
            item.rule_ref, item.revision, item.supersedes_revision, item.scope_ref,
            item.target_facet_ref, item.expected_dimension_ref,
            item.expected_dimension_revision, item.expected_value_ref,
            item.expected_value_revision, canonical_json(item.holder_type_refs),
            canonical_json(item.condition_refs), canonical_json(item.defeater_refs),
            canonical_json(item.context_constraints), canonical_json(item.temporal_constraints),
            item.priority, item.confidence, item.lifecycle_status.value,
            item.permission_ref, canonical_json(item.evidence_refs),
        ),
    )


def _write_dependency(connection: sqlite3.Connection, item: DependencyEdge) -> None:
    connection.execute(
        """
        INSERT INTO dependencies(
            dependency_ref, dependent_kind, dependent_ref, dependent_revision,
            prerequisite_kind, prerequisite_ref, prerequisite_revision,
            prerequisite_fingerprint, dependency_kind, active, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(dependency_ref) DO UPDATE SET
            dependent_kind=excluded.dependent_kind,
            dependent_ref=excluded.dependent_ref,
            dependent_revision=excluded.dependent_revision,
            prerequisite_kind=excluded.prerequisite_kind,
            prerequisite_ref=excluded.prerequisite_ref,
            prerequisite_revision=excluded.prerequisite_revision,
            prerequisite_fingerprint=excluded.prerequisite_fingerprint,
            dependency_kind=excluded.dependency_kind,
            active=excluded.active,
            metadata_json=excluded.metadata_json
        """,
        (
            item.dependency_ref,
            item.dependent_kind.value,
            item.dependent_ref,
            item.dependent_revision,
            None if item.prerequisite_kind is None else item.prerequisite_kind.value,
            item.prerequisite_ref,
            item.prerequisite_revision,
            item.prerequisite_fingerprint,
            item.dependency_kind,
            int(item.active),
            canonical_json(item.metadata),
        ),
    )


def _write_language_pack(connection: sqlite3.Connection, item: LanguagePackRecord) -> None:
    connection.execute(
        """
        INSERT INTO language_packs(
            pack_ref, revision, supersedes_revision, language_tag, lifecycle_status, scripts_json,
            tokenizer_profile, normalization_profile, competence_case_refs_json,
            permission_ref, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(pack_ref, revision) DO UPDATE SET
            supersedes_revision=excluded.supersedes_revision, language_tag=excluded.language_tag, lifecycle_status=excluded.lifecycle_status,
            scripts_json=excluded.scripts_json, tokenizer_profile=excluded.tokenizer_profile,
            normalization_profile=excluded.normalization_profile,
            competence_case_refs_json=excluded.competence_case_refs_json,
            permission_ref=excluded.permission_ref, metadata_json=excluded.metadata_json
        """,
        (item.pack_ref, item.revision, item.supersedes_revision, item.language_tag, item.lifecycle_status.value,
         canonical_json(item.scripts), item.tokenizer_profile, item.normalization_profile,
         canonical_json(item.competence_case_refs), item.permission_ref, canonical_json(item.metadata)),
    )


def _write_language_form(connection: sqlite3.Connection, item: LanguageFormRecord) -> None:
    connection.execute(
        """
        INSERT INTO language_forms(
            form_ref, revision, supersedes_revision, pack_ref, pack_revision, written_form, normalized_form,
            form_kind, script, token_count, feature_values_json, variant_of_ref,
            lifecycle_status, permission_ref, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(form_ref, revision) DO UPDATE SET
            supersedes_revision=excluded.supersedes_revision, pack_ref=excluded.pack_ref, pack_revision=excluded.pack_revision,
            written_form=excluded.written_form, normalized_form=excluded.normalized_form,
            form_kind=excluded.form_kind, script=excluded.script,
            token_count=excluded.token_count, feature_values_json=excluded.feature_values_json,
            variant_of_ref=excluded.variant_of_ref, lifecycle_status=excluded.lifecycle_status,
            permission_ref=excluded.permission_ref, metadata_json=excluded.metadata_json
        """,
        (item.form_ref, item.revision, item.supersedes_revision, item.pack_ref, item.pack_revision, item.written_form,
         item.normalized_form, item.form_kind.value, item.script, item.token_count,
         canonical_json(item.feature_values), item.variant_of_ref, item.lifecycle_status.value,
         item.permission_ref, canonical_json(item.metadata)),
    )


def _write_lexical_sense(connection: sqlite3.Connection, item: LexicalSenseRecord) -> None:
    connection.execute(
        """
        INSERT INTO lexical_senses(
            sense_ref, revision, supersedes_revision, pack_ref, pack_revision, target_kind, target_ref,
            target_revision, target_schema_class, use_operation, lexical_category,
            frame_ref, argument_map_json, expected_type_refs_json, scope_behavior,
            context_constraints_json, feature_constraints_json, lifecycle_status,
            competence_case_refs_json, permission_ref, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(sense_ref, revision) DO UPDATE SET
            supersedes_revision=excluded.supersedes_revision, pack_ref=excluded.pack_ref, pack_revision=excluded.pack_revision,
            target_kind=excluded.target_kind, target_ref=excluded.target_ref,
            target_revision=excluded.target_revision, target_schema_class=excluded.target_schema_class,
            use_operation=excluded.use_operation, lexical_category=excluded.lexical_category,
            frame_ref=excluded.frame_ref, argument_map_json=excluded.argument_map_json,
            expected_type_refs_json=excluded.expected_type_refs_json,
            scope_behavior=excluded.scope_behavior, context_constraints_json=excluded.context_constraints_json,
            feature_constraints_json=excluded.feature_constraints_json,
            lifecycle_status=excluded.lifecycle_status, competence_case_refs_json=excluded.competence_case_refs_json,
            permission_ref=excluded.permission_ref, metadata_json=excluded.metadata_json
        """,
        (item.sense_ref, item.revision, item.supersedes_revision, item.pack_ref, item.pack_revision, item.target_kind.value,
         item.target_ref, item.target_revision, None if item.target_schema_class is None else item.target_schema_class.value,
         item.use_operation.value, item.lexical_category, item.frame_ref, canonical_json(item.argument_map),
         canonical_json(item.expected_type_refs), item.scope_behavior, canonical_json(item.context_constraints),
         canonical_json(item.feature_constraints), item.lifecycle_status.value,
         canonical_json(item.competence_case_refs), item.permission_ref, canonical_json(item.metadata)),
    )


def _write_form_sense_link(connection: sqlite3.Connection, item: FormSenseLinkRecord) -> None:
    connection.execute(
        """
        INSERT INTO form_sense_links(
            link_ref, revision, supersedes_revision, form_ref, form_revision, sense_ref, sense_revision,
            prior_weight, register_refs_json, condition_refs_json, lifecycle_status,
            permission_ref, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(link_ref, revision) DO UPDATE SET
            supersedes_revision=excluded.supersedes_revision, form_ref=excluded.form_ref, form_revision=excluded.form_revision,
            sense_ref=excluded.sense_ref, sense_revision=excluded.sense_revision,
            prior_weight=excluded.prior_weight, register_refs_json=excluded.register_refs_json,
            condition_refs_json=excluded.condition_refs_json, lifecycle_status=excluded.lifecycle_status,
            permission_ref=excluded.permission_ref, metadata_json=excluded.metadata_json
        """,
        (item.link_ref, item.revision, item.supersedes_revision, item.form_ref, item.form_revision, item.sense_ref,
         item.sense_revision, item.prior_weight, canonical_json(item.register_refs),
         canonical_json(item.condition_refs), item.lifecycle_status.value,
         item.permission_ref, canonical_json(item.metadata)),
    )


def _write_construction(connection: sqlite3.Connection, item: ConstructionRecord) -> None:
    connection.execute(
        """
        INSERT INTO constructions(
            construction_ref, revision, supersedes_revision, pack_ref, pack_revision, construction_kind,
            slots_json, trigger_form_refs_json, trigger_sense_refs_json,
            output_schema_ref, output_schema_revision, output_schema_class,
            full_sentence_pattern, genuine_idiom, preserves_gap, lifecycle_status,
            competence_case_refs_json, permission_ref, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(construction_ref, revision) DO UPDATE SET
            supersedes_revision=excluded.supersedes_revision, pack_ref=excluded.pack_ref, pack_revision=excluded.pack_revision,
            construction_kind=excluded.construction_kind, slots_json=excluded.slots_json,
            trigger_form_refs_json=excluded.trigger_form_refs_json,
            trigger_sense_refs_json=excluded.trigger_sense_refs_json,
            output_schema_ref=excluded.output_schema_ref, output_schema_revision=excluded.output_schema_revision,
            output_schema_class=excluded.output_schema_class,
            full_sentence_pattern=excluded.full_sentence_pattern, genuine_idiom=excluded.genuine_idiom,
            preserves_gap=excluded.preserves_gap, lifecycle_status=excluded.lifecycle_status,
            competence_case_refs_json=excluded.competence_case_refs_json,
            permission_ref=excluded.permission_ref, metadata_json=excluded.metadata_json
        """,
        (item.construction_ref, item.revision, item.supersedes_revision, item.pack_ref, item.pack_revision,
         item.construction_kind.value, canonical_json(item.slots),
         canonical_json(item.trigger_form_refs), canonical_json(item.trigger_sense_refs),
         item.output_schema_ref, item.output_schema_revision,
         None if item.output_schema_class is None else item.output_schema_class.value,
         int(item.full_sentence_pattern), int(item.genuine_idiom), int(item.preserves_gap),
         item.lifecycle_status.value, canonical_json(item.competence_case_refs),
         item.permission_ref, canonical_json(item.metadata)),
    )


def _write_view(connection: sqlite3.Connection, item: MaterializedViewRecord) -> None:
    connection.execute(
        """
        INSERT INTO materialized_views(
            view_ref, view_kind, subject_ref, context_ref, payload_json,
            dependency_refs_json, dependency_fingerprint, snapshot_revision, stale
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
        ON CONFLICT(view_ref) DO UPDATE SET
            view_kind=excluded.view_kind,
            subject_ref=excluded.subject_ref,
            context_ref=excluded.context_ref,
            payload_json=excluded.payload_json,
            dependency_refs_json=excluded.dependency_refs_json,
            dependency_fingerprint=excluded.dependency_fingerprint,
            snapshot_revision=excluded.snapshot_revision,
            stale=0
        """,
        (
            item.view_ref,
            item.view_kind,
            item.subject_ref,
            item.context_ref,
            canonical_json(item.payload),
            canonical_json(item.dependency_refs),
            item.dependency_fingerprint,
            item.snapshot_revision,
        ),
    )


def _write_transition_contract(
    connection: sqlite3.Connection, record: TransitionContractRecord
) -> None:
    connection.execute(
        """
        INSERT INTO transition_contracts(
            contract_ref, revision, trigger_schema_ref, trigger_schema_revision, lifecycle_status,
            state_conditions_json, state_effects_json, evidence_refs_json, supersedes_revision,
            context_policy, permission_ref, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(contract_ref, revision) DO UPDATE SET
            trigger_schema_ref=excluded.trigger_schema_ref,
            trigger_schema_revision=excluded.trigger_schema_revision,
            lifecycle_status=excluded.lifecycle_status,
            state_conditions_json=excluded.state_conditions_json,
            state_effects_json=excluded.state_effects_json,
            evidence_refs_json=excluded.evidence_refs_json,
            supersedes_revision=excluded.supersedes_revision,
            context_policy=excluded.context_policy,
            permission_ref=excluded.permission_ref,
            metadata_json=excluded.metadata_json
        """,
        (
            record.contract_ref, record.revision, record.trigger_schema_ref, record.trigger_schema_revision,
            record.lifecycle_status.value, canonical_json(record.state_conditions), canonical_json(record.state_effects),
            canonical_json(record.evidence_refs), record.supersedes_revision, record.context_policy,
            record.permission_ref, canonical_json(record.metadata),
        ),
    )


def _write_capability_dependency(
    connection: sqlite3.Connection, record: CapabilityDependencyRecord
) -> None:
    connection.execute(
        """
        INSERT INTO capability_dependencies(
            dependency_ref, revision, action_schema_ref, action_schema_revision, holder_type_refs_json,
            state_conditions_json, status_if_satisfied, status_if_unsatisfied, status_if_unknown,
            evidence_refs_json, lifecycle_status, supersedes_revision, permission_ref, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(dependency_ref, revision) DO UPDATE SET
            action_schema_ref=excluded.action_schema_ref,
            action_schema_revision=excluded.action_schema_revision,
            holder_type_refs_json=excluded.holder_type_refs_json,
            state_conditions_json=excluded.state_conditions_json,
            status_if_satisfied=excluded.status_if_satisfied,
            status_if_unsatisfied=excluded.status_if_unsatisfied,
            status_if_unknown=excluded.status_if_unknown,
            evidence_refs_json=excluded.evidence_refs_json,
            lifecycle_status=excluded.lifecycle_status,
            supersedes_revision=excluded.supersedes_revision,
            permission_ref=excluded.permission_ref,
            metadata_json=excluded.metadata_json
        """,
        (
            record.dependency_ref, record.revision, record.action_schema_ref, record.action_schema_revision,
            canonical_json(record.holder_type_refs), canonical_json(record.state_conditions),
            record.status_if_satisfied.value, record.status_if_unsatisfied.value, record.status_if_unknown.value,
            canonical_json(record.evidence_refs), record.lifecycle_status.value, record.supersedes_revision,
            record.permission_ref, canonical_json(record.metadata),
        ),
    )


def _write_transition_proof(
    connection: sqlite3.Connection, record: TransitionProofRecord
) -> None:
    connection.execute(
        """
        INSERT INTO transition_proofs(
            proof_ref, event_ref, event_revision, participant_application_ref, participant_application_revision,
            transition_contract_ref, transition_contract_revision, admission_pins_json, condition_evidence_refs_json,
            input_assignment_pins_json, derived_state_delta_refs_json, context_ref, effective_time_ref, confidence, evidence_refs_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(proof_ref) DO UPDATE SET
            event_ref=excluded.event_ref,
            event_revision=excluded.event_revision,
            participant_application_ref=excluded.participant_application_ref,
            participant_application_revision=excluded.participant_application_revision,
            transition_contract_ref=excluded.transition_contract_ref,
            transition_contract_revision=excluded.transition_contract_revision,
            admission_pins_json=excluded.admission_pins_json,
            condition_evidence_refs_json=excluded.condition_evidence_refs_json,
            input_assignment_pins_json=excluded.input_assignment_pins_json,
            derived_state_delta_refs_json=excluded.derived_state_delta_refs_json,
            context_ref=excluded.context_ref,
            effective_time_ref=excluded.effective_time_ref,
            confidence=excluded.confidence,
            evidence_refs_json=excluded.evidence_refs_json
        """,
        (
            record.proof_ref, record.event_ref, record.event_revision,
            record.participant_application_ref, record.participant_application_revision,
            record.transition_contract_ref, record.transition_contract_revision, canonical_json(record.admission_pins),
            canonical_json(record.condition_evidence_refs), canonical_json(record.input_assignment_pins),
            canonical_json(record.derived_state_delta_refs), record.context_ref, record.effective_time_ref,
            record.confidence, canonical_json(record.evidence_refs),
        ),
    )
