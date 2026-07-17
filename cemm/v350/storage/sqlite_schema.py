"""Normalized SQLite schema and deterministic connection configuration."""
from __future__ import annotations

import sqlite3
from typing import Iterable


SCHEMA_VERSION = 1
APPLICATION_ID = 0x43454D4D  # CEMM


DDL: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS meta (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    ) WITHOUT ROWID
    """,
    """
    CREATE TABLE IF NOT EXISTS record_index (
        record_kind TEXT NOT NULL,
        record_ref TEXT NOT NULL,
        revision INTEGER NOT NULL,
        lifecycle_status TEXT,
        context_ref TEXT,
        valid_from TEXT,
        valid_to TEXT,
        permission_ref TEXT,
        content_fingerprint TEXT NOT NULL,
        record_fingerprint TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        store_revision INTEGER NOT NULL,
        PRIMARY KEY(record_kind, record_ref, revision)
    ) WITHOUT ROWID
    """,
    "CREATE INDEX IF NOT EXISTS record_index_ref_idx ON record_index(record_ref, record_kind, revision DESC)",
    "CREATE INDEX IF NOT EXISTS record_index_context_idx ON record_index(record_kind, context_ref, revision DESC)",
    """
    CREATE TABLE IF NOT EXISTS record_tombstones (
        record_kind TEXT NOT NULL,
        record_ref TEXT NOT NULL,
        revision INTEGER,
        reason TEXT NOT NULL,
        store_revision INTEGER NOT NULL,
        PRIMARY KEY(record_kind, record_ref, revision)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS semantic_schemas (
        schema_ref TEXT NOT NULL,
        revision INTEGER NOT NULL,
        schema_class TEXT NOT NULL,
        semantic_key TEXT NOT NULL,
        status TEXT NOT NULL,
        scope_ref TEXT NOT NULL,
        confidence REAL NOT NULL,
        permission_ref TEXT NOT NULL,
        provenance_json TEXT NOT NULL,
        use_profile_json TEXT NOT NULL,
        dependencies_json TEXT NOT NULL,
        competence_hooks_json TEXT NOT NULL,
        valid_from TEXT,
        valid_to TEXT,
        content_fingerprint TEXT NOT NULL,
        record_fingerprint TEXT NOT NULL,
        PRIMARY KEY(schema_ref, revision)
    ) WITHOUT ROWID
    """,
    "CREATE INDEX IF NOT EXISTS semantic_schemas_authority_idx ON semantic_schemas(schema_ref, status, revision DESC)",
    """
    CREATE TABLE IF NOT EXISTS schema_parents (
        child_ref TEXT NOT NULL,
        child_revision INTEGER NOT NULL,
        parent_ref TEXT NOT NULL,
        parent_revision_policy TEXT NOT NULL,
        parent_revision INTEGER,
        inheritance_kind TEXT NOT NULL,
        priority INTEGER NOT NULL,
        PRIMARY KEY(child_ref, child_revision, parent_ref, inheritance_kind)
    ) WITHOUT ROWID
    """,
    "CREATE INDEX IF NOT EXISTS schema_parents_parent_idx ON schema_parents(parent_ref, child_ref)",
    """
    CREATE TABLE IF NOT EXISTS schema_ports (
        schema_ref TEXT NOT NULL,
        schema_revision INTEGER NOT NULL,
        port_ref TEXT NOT NULL,
        filler_classes_json TEXT NOT NULL,
        accepted_type_refs_json TEXT NOT NULL,
        accepted_storage_kinds_json TEXT NOT NULL,
        accepted_schema_classes_json TEXT NOT NULL,
        cardinality_min INTEGER NOT NULL,
        cardinality_max INTEGER,
        queryable INTEGER NOT NULL,
        open_binding_purposes_json TEXT NOT NULL,
        role_family TEXT NOT NULL,
        context_policy TEXT NOT NULL,
        time_policy TEXT NOT NULL,
        identity_contribution INTEGER NOT NULL,
        ordered_fillers INTEGER NOT NULL,
        constraint_refs_json TEXT NOT NULL,
        metadata_json TEXT NOT NULL,
        PRIMARY KEY(schema_ref, schema_revision, port_ref)
    ) WITHOUT ROWID
    """,
    """
    CREATE TABLE IF NOT EXISTS port_constraints (
        schema_ref TEXT NOT NULL,
        schema_revision INTEGER NOT NULL,
        port_ref TEXT NOT NULL,
        constraint_kind TEXT NOT NULL,
        target_ref TEXT NOT NULL,
        polarity TEXT NOT NULL,
        priority INTEGER NOT NULL,
        PRIMARY KEY(schema_ref, schema_revision, port_ref, constraint_kind, target_ref)
    ) WITHOUT ROWID
    """,
    """
    CREATE TABLE IF NOT EXISTS facet_entitlements (
        entitlement_ref TEXT NOT NULL,
        revision INTEGER NOT NULL,
        owner_type_ref TEXT NOT NULL,
        facet_ref TEXT NOT NULL,
        applicability TEXT NOT NULL,
        activation_policy TEXT NOT NULL,
        inheritance_policy TEXT NOT NULL,
        value_domain_refs_json TEXT NOT NULL,
        default_rule_refs_json TEXT NOT NULL,
        context_constraints_json TEXT NOT NULL,
        temporal_constraints_json TEXT NOT NULL,
        dependencies_json TEXT NOT NULL,
        status TEXT NOT NULL,
        scope_ref TEXT NOT NULL,
        confidence REAL NOT NULL,
        permission_ref TEXT NOT NULL,
        content_fingerprint TEXT NOT NULL,
        record_fingerprint TEXT NOT NULL,
        PRIMARY KEY(entitlement_ref, revision)
    ) WITHOUT ROWID
    """,
    "CREATE INDEX IF NOT EXISTS facet_entitlements_owner_idx ON facet_entitlements(owner_type_ref, facet_ref, status, revision DESC)",
    """
    CREATE TABLE IF NOT EXISTS referents (
        referent_ref TEXT NOT NULL,
        revision INTEGER NOT NULL,
        storage_kind TEXT NOT NULL,
        identity_status TEXT NOT NULL,
        scope_ref TEXT NOT NULL,
        context_refs_json TEXT NOT NULL,
        valid_time_ref TEXT,
        permission_ref TEXT NOT NULL,
        type_refs_json TEXT NOT NULL,
        identity_facet_refs_json TEXT NOT NULL,
        provenance_refs_json TEXT NOT NULL,
        metadata_json TEXT NOT NULL,
        PRIMARY KEY(referent_ref, revision)
    ) WITHOUT ROWID
    """,
    """
    CREATE TABLE IF NOT EXISTS referent_type_assertions (
        assertion_ref TEXT PRIMARY KEY,
        referent_ref TEXT NOT NULL,
        type_schema_ref TEXT NOT NULL,
        type_revision INTEGER NOT NULL,
        status TEXT NOT NULL,
        confidence REAL NOT NULL,
        context_ref TEXT NOT NULL,
        valid_from TEXT,
        valid_to TEXT,
        evidence_refs_json TEXT NOT NULL,
        source_refs_json TEXT NOT NULL,
        proof_refs_json TEXT NOT NULL,
        permission_ref TEXT NOT NULL
    ) WITHOUT ROWID
    """,
    "CREATE INDEX IF NOT EXISTS type_assertions_subject_idx ON referent_type_assertions(referent_ref, context_ref, status, type_schema_ref)",
    """
    CREATE TABLE IF NOT EXISTS identity_facets (
        identity_facet_ref TEXT PRIMARY KEY,
        referent_ref TEXT NOT NULL,
        facet_schema_ref TEXT NOT NULL,
        normalized_value TEXT NOT NULL,
        anchor_ref TEXT,
        confidence REAL NOT NULL,
        evidence_refs_json TEXT NOT NULL,
        context_ref TEXT NOT NULL
    ) WITHOUT ROWID
    """,
    """
    CREATE TABLE IF NOT EXISTS semantic_applications (
        application_ref TEXT NOT NULL,
        record_revision INTEGER NOT NULL,
        schema_ref TEXT NOT NULL,
        schema_revision INTEGER NOT NULL,
        context_ref TEXT NOT NULL,
        use_operation TEXT NOT NULL,
        valid_time_ref TEXT,
        polarity TEXT NOT NULL,
        confidence REAL NOT NULL,
        assumptions_json TEXT NOT NULL,
        evidence_refs_json TEXT NOT NULL,
        metadata_json TEXT NOT NULL,
        PRIMARY KEY(application_ref, record_revision)
    ) WITHOUT ROWID
    """,
    "CREATE INDEX IF NOT EXISTS semantic_applications_schema_idx ON semantic_applications(schema_ref, schema_revision, context_ref)",
    """
    CREATE TABLE IF NOT EXISTS application_bindings (
        application_ref TEXT NOT NULL,
        application_revision INTEGER NOT NULL,
        port_ref TEXT NOT NULL,
        filler_class TEXT NOT NULL,
        filler_ref TEXT NOT NULL,
        ordinal INTEGER NOT NULL,
        confidence REAL NOT NULL,
        evidence_refs_json TEXT NOT NULL,
        assumptions_json TEXT NOT NULL,
        ordered_fillers INTEGER NOT NULL,
        open_binding_purpose TEXT,
        PRIMARY KEY(application_ref, application_revision, port_ref, ordinal)
    ) WITHOUT ROWID
    """,
    "CREATE INDEX IF NOT EXISTS application_bindings_filler_idx ON application_bindings(filler_ref, filler_class)",
    """
    CREATE TABLE IF NOT EXISTS propositions (
        proposition_ref TEXT NOT NULL,
        revision INTEGER NOT NULL,
        context_ref TEXT NOT NULL,
        polarity TEXT NOT NULL,
        modality_refs_json TEXT NOT NULL,
        attribution_refs_json TEXT NOT NULL,
        valid_time_ref TEXT,
        evidence_refs_json TEXT NOT NULL,
        PRIMARY KEY(proposition_ref, revision)
    ) WITHOUT ROWID
    """,
    """
    CREATE TABLE IF NOT EXISTS proposition_content (
        proposition_ref TEXT NOT NULL,
        proposition_revision INTEGER NOT NULL,
        content_ref TEXT NOT NULL,
        content_kind TEXT NOT NULL,
        ordinal INTEGER NOT NULL,
        PRIMARY KEY(proposition_ref, proposition_revision, ordinal)
    ) WITHOUT ROWID
    """,
    """
    CREATE TABLE IF NOT EXISTS claim_occurrences (
        claim_ref TEXT NOT NULL,
        revision INTEGER NOT NULL,
        claimant_ref TEXT NOT NULL,
        audience_refs_json TEXT NOT NULL,
        proposition_ref TEXT NOT NULL,
        claim_force TEXT NOT NULL,
        source_context_ref TEXT NOT NULL,
        reported_context_ref TEXT NOT NULL,
        time_ref TEXT,
        certainty_expression_ref TEXT,
        evidence_offered_refs_json TEXT NOT NULL,
        evidence_refs_json TEXT NOT NULL,
        PRIMARY KEY(claim_ref, revision)
    ) WITHOUT ROWID
    """,
    """
    CREATE TABLE IF NOT EXISTS claim_records (
        claim_record_ref TEXT PRIMARY KEY,
        claim_occurrence_ref TEXT NOT NULL,
        proposition_ref TEXT NOT NULL,
        source_ref TEXT NOT NULL,
        source_context_ref TEXT NOT NULL,
        reported_context_ref TEXT NOT NULL,
        commitment_strength REAL NOT NULL,
        permission_ref TEXT NOT NULL,
        evidence_refs_json TEXT NOT NULL,
        superseded_by TEXT
    ) WITHOUT ROWID
    """,
    """
    CREATE TABLE IF NOT EXISTS knowledge_records (
        knowledge_ref TEXT PRIMARY KEY,
        proposition_ref TEXT NOT NULL,
        truth_status TEXT NOT NULL,
        confidence REAL NOT NULL,
        context_ref TEXT NOT NULL,
        source_refs_json TEXT NOT NULL,
        evidence_refs_json TEXT NOT NULL,
        permission_ref TEXT NOT NULL,
        sensitivity TEXT NOT NULL,
        valid_time_ref TEXT,
        valid_from TEXT,
        valid_to TEXT,
        support_lineage_refs_json TEXT NOT NULL,
        derivation_refs_json TEXT NOT NULL,
        superseded_by TEXT,
        metadata_json TEXT NOT NULL
    ) WITHOUT ROWID
    """,
    "CREATE INDEX IF NOT EXISTS knowledge_proposition_idx ON knowledge_records(proposition_ref, context_ref, truth_status)",
    """
    CREATE TABLE IF NOT EXISTS event_occurrences (
        event_ref TEXT NOT NULL,
        revision INTEGER NOT NULL,
        event_schema_ref TEXT NOT NULL,
        event_schema_revision INTEGER NOT NULL,
        participant_application_ref TEXT NOT NULL,
        occurrence_status TEXT NOT NULL,
        context_ref TEXT NOT NULL,
        time_ref TEXT,
        place_ref TEXT,
        cause_refs_json TEXT NOT NULL,
        result_refs_json TEXT NOT NULL,
        provenance_refs_json TEXT NOT NULL,
        admission_refs_json TEXT NOT NULL,
        PRIMARY KEY(event_ref, revision)
    ) WITHOUT ROWID
    """,
    "CREATE INDEX IF NOT EXISTS event_occurrences_schema_idx ON event_occurrences(event_schema_ref, context_ref, occurrence_status)",
    """
    CREATE TABLE IF NOT EXISTS state_assignments (
        assignment_ref TEXT PRIMARY KEY,
        holder_ref TEXT NOT NULL,
        dimension_ref TEXT NOT NULL,
        dimension_revision INTEGER NOT NULL,
        value_ref TEXT NOT NULL,
        value_revision INTEGER NOT NULL,
        status TEXT NOT NULL,
        context_ref TEXT NOT NULL,
        confidence REAL NOT NULL,
        valid_from TEXT,
        valid_to TEXT,
        evidence_refs_json TEXT NOT NULL,
        proof_refs_json TEXT NOT NULL,
        source_refs_json TEXT NOT NULL
    ) WITHOUT ROWID
    """,
    "CREATE INDEX IF NOT EXISTS state_assignments_timeline_idx ON state_assignments(holder_ref, dimension_ref, context_ref, valid_from, valid_to)",
    """
    CREATE TABLE IF NOT EXISTS state_deltas (
        delta_ref TEXT PRIMARY KEY,
        trigger_ref TEXT NOT NULL,
        holder_ref TEXT NOT NULL,
        dimension_ref TEXT NOT NULL,
        dimension_revision INTEGER NOT NULL,
        operation TEXT NOT NULL,
        from_value_ref TEXT,
        from_value_revision INTEGER,
        to_value_ref TEXT,
        to_value_revision INTEGER,
        magnitude_ref TEXT,
        duration_ref TEXT,
        context_ref TEXT NOT NULL,
        effective_time_ref TEXT NOT NULL,
        confidence REAL NOT NULL,
        proof_refs_json TEXT NOT NULL
    ) WITHOUT ROWID
    """,
    """
    CREATE TABLE IF NOT EXISTS capability_instances (
        capability_ref TEXT PRIMARY KEY,
        holder_ref TEXT NOT NULL,
        action_schema_ref TEXT NOT NULL,
        action_schema_revision INTEGER NOT NULL,
        status TEXT NOT NULL,
        confidence REAL NOT NULL,
        context_ref TEXT NOT NULL,
        valid_from TEXT,
        valid_to TEXT,
        dependency_refs_json TEXT NOT NULL,
        evidence_refs_json TEXT NOT NULL,
        proof_refs_json TEXT NOT NULL
    ) WITHOUT ROWID
    """,
    "CREATE INDEX IF NOT EXISTS capability_holder_idx ON capability_instances(holder_ref, context_ref, action_schema_ref, status)",
    """
    CREATE TABLE IF NOT EXISTS capability_deltas (
        delta_ref TEXT PRIMARY KEY,
        trigger_ref TEXT NOT NULL,
        holder_ref TEXT NOT NULL,
        action_schema_ref TEXT NOT NULL,
        action_schema_revision INTEGER NOT NULL,
        prior_status TEXT NOT NULL,
        new_status TEXT NOT NULL,
        context_ref TEXT NOT NULL,
        effective_time_ref TEXT NOT NULL,
        dependency_ref TEXT NOT NULL,
        confidence REAL NOT NULL,
        proof_refs_json TEXT NOT NULL
    ) WITHOUT ROWID
    """,
    """
    CREATE TABLE IF NOT EXISTS impact_assessments (
        assessment_ref TEXT PRIMARY KEY,
        source_event_or_state_ref TEXT NOT NULL,
        affected_ref TEXT NOT NULL,
        stakeholder_ref TEXT NOT NULL,
        affected_facet_refs_json TEXT NOT NULL,
        direction TEXT NOT NULL,
        valence TEXT NOT NULL,
        context_ref TEXT NOT NULL,
        reversibility TEXT NOT NULL,
        magnitude_ref TEXT,
        duration_ref TEXT,
        confidence REAL NOT NULL,
        importance_ref TEXT,
        proof_refs_json TEXT NOT NULL
    ) WITHOUT ROWID
    """,
    """
    CREATE TABLE IF NOT EXISTS importance_assessments (
        assessment_ref TEXT PRIMARY KEY,
        subject_ref TEXT NOT NULL,
        stakeholder_ref TEXT NOT NULL,
        context_ref TEXT NOT NULL,
        score REAL NOT NULL,
        importance_class TEXT NOT NULL,
        evidence_refs_json TEXT NOT NULL,
        reasons_json TEXT NOT NULL,
        valid_time_ref TEXT
    ) WITHOUT ROWID
    """,
    """
    CREATE TABLE IF NOT EXISTS evidence_records (
        evidence_ref TEXT PRIMARY KEY,
        source_ref TEXT NOT NULL,
        confidence REAL NOT NULL,
        lineage_ref TEXT NOT NULL,
        context_ref TEXT NOT NULL,
        observed_at TEXT,
        span_start INTEGER,
        span_end INTEGER,
        permission_ref TEXT NOT NULL,
        metadata_json TEXT NOT NULL
    ) WITHOUT ROWID
    """,
    "CREATE INDEX IF NOT EXISTS evidence_lineage_idx ON evidence_records(lineage_ref, context_ref)",
    """
    CREATE TABLE IF NOT EXISTS default_rules (
        rule_ref TEXT NOT NULL,
        revision INTEGER NOT NULL,
        supersedes_revision INTEGER,
        scope_ref TEXT NOT NULL,
        target_facet_ref TEXT NOT NULL,
        expected_dimension_ref TEXT,
        expected_dimension_revision INTEGER,
        expected_value_ref TEXT,
        expected_value_revision INTEGER,
        holder_type_refs_json TEXT NOT NULL,
        condition_refs_json TEXT NOT NULL,
        defeater_refs_json TEXT NOT NULL,
        context_constraints_json TEXT NOT NULL,
        temporal_constraints_json TEXT NOT NULL,
        priority INTEGER NOT NULL,
        confidence REAL NOT NULL,
        lifecycle_status TEXT NOT NULL,
        permission_ref TEXT NOT NULL,
        evidence_refs_json TEXT NOT NULL,
        PRIMARY KEY(rule_ref, revision)
    ) WITHOUT ROWID
    """,
    """
    CREATE TABLE IF NOT EXISTS dependencies (
        dependency_ref TEXT PRIMARY KEY,
        dependent_kind TEXT NOT NULL,
        dependent_ref TEXT NOT NULL,
        dependent_revision INTEGER NOT NULL,
        prerequisite_kind TEXT,
        prerequisite_ref TEXT NOT NULL,
        prerequisite_revision INTEGER,
        prerequisite_fingerprint TEXT,
        dependency_kind TEXT NOT NULL,
        active INTEGER NOT NULL,
        metadata_json TEXT NOT NULL
    ) WITHOUT ROWID
    """,
    "CREATE INDEX IF NOT EXISTS dependencies_reverse_idx ON dependencies(prerequisite_ref, active, dependent_kind)",
    "CREATE INDEX IF NOT EXISTS dependencies_forward_idx ON dependencies(dependent_kind, dependent_ref, dependent_revision, active)",
    """
    CREATE TABLE IF NOT EXISTS materialized_views (
        view_ref TEXT PRIMARY KEY,
        view_kind TEXT NOT NULL,
        subject_ref TEXT NOT NULL,
        context_ref TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        dependency_refs_json TEXT NOT NULL,
        dependency_fingerprint TEXT NOT NULL,
        snapshot_revision INTEGER NOT NULL,
        stale INTEGER NOT NULL DEFAULT 0
    ) WITHOUT ROWID
    """,
    "CREATE INDEX IF NOT EXISTS materialized_views_subject_idx ON materialized_views(view_kind, subject_ref, context_ref, stale)",
    """
    CREATE TABLE IF NOT EXISTS patch_journal (
        patch_ref TEXT PRIMARY KEY,
        patch_fingerprint TEXT NOT NULL,
        context_ref TEXT NOT NULL,
        scope_ref TEXT NOT NULL,
        source_ref TEXT NOT NULL,
        permission_ref TEXT NOT NULL,
        evidence_refs_json TEXT NOT NULL,
        validation_requirements_json TEXT NOT NULL,
        rollback_hint TEXT NOT NULL,
        metadata_json TEXT NOT NULL,
        revision_before INTEGER NOT NULL,
        revision_after INTEGER NOT NULL
    ) WITHOUT ROWID
    """,
    """
    CREATE TABLE IF NOT EXISTS patch_operations (
        patch_ref TEXT NOT NULL,
        ordinal INTEGER NOT NULL,
        operation_ref TEXT NOT NULL,
        operation_kind TEXT NOT NULL,
        record_kind TEXT NOT NULL,
        target_ref TEXT NOT NULL,
        record_revision INTEGER NOT NULL,
        expected_record_revision INTEGER,
        expected_record_fingerprint TEXT,
        dependencies_json TEXT NOT NULL,
        reason TEXT NOT NULL,
        PRIMARY KEY(patch_ref, ordinal),
        UNIQUE(operation_ref)
    ) WITHOUT ROWID
    """,
)


_META_DEFAULTS = {
    "schema_version": str(SCHEMA_VERSION),
    "store_revision": "0",
    "boot_fingerprint": "",
    "compiled_manifest_fingerprint": "",
    "record_set_fingerprint": "",
}


def configure_connection(connection: sqlite3.Connection, *, deterministic_build: bool = False) -> None:
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=5000")
    if deterministic_build:
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA synchronous=OFF")
        connection.execute("PRAGMA temp_store=MEMORY")
        connection.execute("PRAGMA page_size=4096")
        connection.execute("PRAGMA auto_vacuum=NONE")
        connection.execute("PRAGMA encoding='UTF-8'")
    else:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
    connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
    connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")


def initialize_schema(connection: sqlite3.Connection) -> None:
    for statement in DDL:
        connection.execute(statement)
    connection.executemany(
        "INSERT OR IGNORE INTO meta(key, value) VALUES (?, ?)",
        tuple(sorted(_META_DEFAULTS.items())),
    )


def set_meta(connection: sqlite3.Connection, key: str, value: str) -> None:
    connection.execute(
        "INSERT INTO meta(key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def get_meta(connection: sqlite3.Connection, key: str, default: str = "") -> str:
    row = connection.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return default if row is None else str(row[0])


def require_schema_compatible(connection: sqlite3.Connection) -> None:
    application_id = int(connection.execute("PRAGMA application_id").fetchone()[0])
    user_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
    if application_id != APPLICATION_ID:
        raise RuntimeError(f"not a CEMM v3.5 database: application_id={application_id}")
    if user_version != SCHEMA_VERSION:
        raise RuntimeError(f"unsupported CEMM database schema version: {user_version}")


def table_names(connection: sqlite3.Connection) -> tuple[str, ...]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return tuple(str(row[0]) for row in rows)


def execute_many(connection: sqlite3.Connection, statements: Iterable[str]) -> None:
    for statement in statements:
        connection.execute(statement)
