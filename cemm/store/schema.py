import sqlite3


SIGNALS_TABLE = """
CREATE TABLE IF NOT EXISTS signals (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    source_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    content TEXT NOT NULL,
    observed_at REAL NOT NULL,
    context_id TEXT NOT NULL,
    salience REAL NOT NULL DEFAULT 0.0,
    trust REAL NOT NULL DEFAULT 0.5,
    permission_scope TEXT NOT NULL DEFAULT 'public',
    permission_may_store INTEGER NOT NULL DEFAULT 1,
    permission_may_retrieve INTEGER NOT NULL DEFAULT 1,
    permission_may_use INTEGER NOT NULL DEFAULT 1,
    permission_may_share INTEGER NOT NULL DEFAULT 0,
    permission_may_execute INTEGER NOT NULL DEFAULT 0,
    permission_retention TEXT NOT NULL DEFAULT 'long_term',
    parent_signal_id TEXT,
    observation_semantics_json TEXT,
    version TEXT NOT NULL DEFAULT 'erca.signal.v1'
)
"""

ENTITIES_TABLE = """
CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.5,
    created_from_signal_id TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    version TEXT NOT NULL DEFAULT 'erca.entity.v1'
)
"""

ENTITY_ALIASES_TABLE = """
CREATE TABLE IF NOT EXISTS entity_aliases (
    entity_id TEXT NOT NULL,
    alias TEXT NOT NULL,
    PRIMARY KEY (entity_id, alias),
    FOREIGN KEY (entity_id) REFERENCES entities(id)
)
"""

CLAIMS_TABLE = """
CREATE TABLE IF NOT EXISTS claims (
    id TEXT PRIMARY KEY,
    subject_entity_id TEXT NOT NULL,
    predicate TEXT NOT NULL,
    predicate_model_id TEXT,
    object_entity_id TEXT,
    object_value TEXT,
    source_id TEXT NOT NULL DEFAULT '',
    domain TEXT NOT NULL DEFAULT '',
    confidence REAL NOT NULL DEFAULT 0.5,
    confidence_log_odds REAL NOT NULL DEFAULT 0.0,
    trust REAL NOT NULL DEFAULT 0.5,
    salience REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'active',
    supersedes_claim_id TEXT,
    frame_id TEXT,
    valid_from REAL,
    valid_until REAL,
    observed_at REAL NOT NULL DEFAULT 0.0,
    updated_at REAL NOT NULL DEFAULT 0.0,
    permission_scope TEXT NOT NULL DEFAULT 'public',
    permission_retention TEXT NOT NULL DEFAULT 'long_term',
    permission_may_store INTEGER NOT NULL DEFAULT 1,
    permission_may_retrieve INTEGER NOT NULL DEFAULT 1,
    permission_may_use INTEGER NOT NULL DEFAULT 1,
    version TEXT NOT NULL DEFAULT 'erca.claim.v1',
    FOREIGN KEY (subject_entity_id) REFERENCES entities(id)
)
"""

CLAIM_EVIDENCE_TABLE = """
CREATE TABLE IF NOT EXISTS claim_evidence (
    claim_id TEXT NOT NULL,
    signal_id TEXT NOT NULL,
    PRIMARY KEY (claim_id, signal_id),
    FOREIGN KEY (claim_id) REFERENCES claims(id),
    FOREIGN KEY (signal_id) REFERENCES signals(id)
)
"""

CLAIM_QUALIFIERS_TABLE = """
CREATE TABLE IF NOT EXISTS claim_qualifiers (
    claim_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT,
    PRIMARY KEY (claim_id, key),
    FOREIGN KEY (claim_id) REFERENCES claims(id)
)
"""

MODELS_TABLE = """
CREATE TABLE IF NOT EXISTS models (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    registry_key TEXT,
    confidence REAL NOT NULL DEFAULT 0.5,
    trust REAL NOT NULL DEFAULT 0.5,
    utility REAL NOT NULL DEFAULT 0.0,
    cost_estimate_ms REAL NOT NULL DEFAULT 0.0,
    risk REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'candidate',
    created_at REAL NOT NULL DEFAULT 0.0,
    updated_at REAL NOT NULL DEFAULT 0.0,
    permission_scope TEXT NOT NULL DEFAULT 'public',
    permission_retention TEXT NOT NULL DEFAULT 'long_term',
    permission_may_store INTEGER NOT NULL DEFAULT 1,
    permission_may_retrieve INTEGER NOT NULL DEFAULT 1,
    permission_may_use INTEGER NOT NULL DEFAULT 1,
    version TEXT NOT NULL DEFAULT 'erca.model.v1'
)
"""

MODEL_INPUT_TYPES_TABLE = """
CREATE TABLE IF NOT EXISTS model_input_types (
    model_id TEXT NOT NULL,
    input_type TEXT NOT NULL,
    PRIMARY KEY (model_id, input_type),
    FOREIGN KEY (model_id) REFERENCES models(id)
)
"""

MODEL_OUTPUT_TYPES_TABLE = """
CREATE TABLE IF NOT EXISTS model_output_types (
    model_id TEXT NOT NULL,
    output_type TEXT NOT NULL,
    PRIMARY KEY (model_id, output_type),
    FOREIGN KEY (model_id) REFERENCES models(id)
)
"""

MODEL_PRECONDITIONS_TABLE = """
CREATE TABLE IF NOT EXISTS model_preconditions (
    model_id TEXT NOT NULL,
    precondition TEXT NOT NULL,
    PRIMARY KEY (model_id, precondition),
    FOREIGN KEY (model_id) REFERENCES models(id)
)
"""

MODEL_EFFECTS_TABLE = """
CREATE TABLE IF NOT EXISTS model_effects (
    model_id TEXT NOT NULL,
    effect TEXT NOT NULL,
    PRIMARY KEY (model_id, effect),
    FOREIGN KEY (model_id) REFERENCES models(id)
)
"""

MODEL_EVIDENCE_TABLE = """
CREATE TABLE IF NOT EXISTS model_evidence (
    model_id TEXT NOT NULL,
    signal_id TEXT NOT NULL,
    PRIMARY KEY (model_id, signal_id),
    FOREIGN KEY (model_id) REFERENCES models(id),
    FOREIGN KEY (signal_id) REFERENCES signals(id)
)
"""

MODEL_RELATED_ENTITIES_TABLE = """
CREATE TABLE IF NOT EXISTS model_related_entities (
    model_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    PRIMARY KEY (model_id, entity_id),
    FOREIGN KEY (model_id) REFERENCES models(id),
    FOREIGN KEY (entity_id) REFERENCES entities(id)
)
"""

MODEL_RELATED_CLAIMS_TABLE = """
CREATE TABLE IF NOT EXISTS model_related_claims (
    model_id TEXT NOT NULL,
    claim_id TEXT NOT NULL,
    PRIMARY KEY (model_id, claim_id),
    FOREIGN KEY (model_id) REFERENCES models(id),
    FOREIGN KEY (claim_id) REFERENCES claims(id)
)
"""

ACTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS actions (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    operator_model_id TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.5,
    risk REAL NOT NULL DEFAULT 0.0,
    cost_ms REAL NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'planned',
    result_signal_id TEXT,
    trace_json TEXT,
    created_at REAL NOT NULL DEFAULT 0.0,
    version TEXT NOT NULL DEFAULT 'erca.action.v1'
)
"""

ACTION_INPUT_SIGNALS_TABLE = """
CREATE TABLE IF NOT EXISTS action_input_signals (
    action_id TEXT NOT NULL,
    signal_id TEXT NOT NULL,
    PRIMARY KEY (action_id, signal_id),
    FOREIGN KEY (action_id) REFERENCES actions(id),
    FOREIGN KEY (signal_id) REFERENCES signals(id)
)
"""

ACTION_SELECTED_CLAIMS_TABLE = """
CREATE TABLE IF NOT EXISTS action_selected_claims (
    action_id TEXT NOT NULL,
    claim_id TEXT NOT NULL,
    PRIMARY KEY (action_id, claim_id),
    FOREIGN KEY (action_id) REFERENCES actions(id),
    FOREIGN KEY (claim_id) REFERENCES claims(id)
)
"""

ACTION_SELECTED_MODELS_TABLE = """
CREATE TABLE IF NOT EXISTS action_selected_models (
    action_id TEXT NOT NULL,
    model_id TEXT NOT NULL,
    PRIMARY KEY (action_id, model_id),
    FOREIGN KEY (action_id) REFERENCES actions(id),
    FOREIGN KEY (model_id) REFERENCES models(id)
)
"""

SELF_STATES_TABLE = """
CREATE TABLE IF NOT EXISTS self_states (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL DEFAULT 'cemm',
    identity_claim_ids_json TEXT NOT NULL DEFAULT '[]',
    mode TEXT NOT NULL DEFAULT 'assistant',
    load REAL NOT NULL DEFAULT 0.0,
    uncertainty REAL NOT NULL DEFAULT 0.0,
    coherence REAL NOT NULL DEFAULT 1.0,
    recent_error_rate REAL NOT NULL DEFAULT 0.0,
    current_budget_pressure REAL NOT NULL DEFAULT 0.0,
    metacognition_json TEXT NOT NULL DEFAULT '{}',
    epistemic_json TEXT NOT NULL DEFAULT '{}',
    meta_memory_json TEXT NOT NULL DEFAULT '{}',
    current_context_id TEXT,
    last_reflection_signal_id TEXT,
    created_at REAL NOT NULL DEFAULT 0.0,
    updated_at REAL NOT NULL DEFAULT 0.0,
    version TEXT NOT NULL DEFAULT 'erca.self.v1'
)
"""

SELF_MILESTONE_SIGNALS_TABLE = """
CREATE TABLE IF NOT EXISTS self_milestone_signals (
    self_id TEXT NOT NULL,
    signal_id TEXT NOT NULL,
    PRIMARY KEY (self_id, signal_id),
    FOREIGN KEY (self_id) REFERENCES self_states(id),
    FOREIGN KEY (signal_id) REFERENCES signals(id)
)
"""

SELF_ACTIVE_PROJECTS_TABLE = """
CREATE TABLE IF NOT EXISTS self_active_projects (
    self_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    PRIMARY KEY (self_id, project_id),
    FOREIGN KEY (self_id) REFERENCES self_states(id)
)
"""

SELF_LEARNED_MODELS_TABLE = """
CREATE TABLE IF NOT EXISTS self_learned_models (
    self_id TEXT NOT NULL,
    model_id TEXT NOT NULL,
    PRIMARY KEY (self_id, model_id),
    FOREIGN KEY (self_id) REFERENCES self_states(id),
    FOREIGN KEY (model_id) REFERENCES models(id)
)
"""

SOURCE_TRUST_TABLE = """
CREATE TABLE IF NOT EXISTS source_trust (
    source_id TEXT NOT NULL,
    domain TEXT NOT NULL,
    trust REAL NOT NULL DEFAULT 0.5,
    evidence_count INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    failure_count INTEGER NOT NULL DEFAULT 0,
    last_observed_at REAL NOT NULL DEFAULT 0.0,
    PRIMARY KEY (source_id, domain)
)
"""

FEEDBACK_TABLE = """
CREATE TABLE IF NOT EXISTS feedback (
    id TEXT PRIMARY KEY,
    signal_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    rating INTEGER NOT NULL DEFAULT 0,
    comment TEXT,
    domain TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL DEFAULT 0.0,
    FOREIGN KEY (signal_id) REFERENCES signals(id),
    FOREIGN KEY (action_id) REFERENCES actions(id)
)
"""

VECTORS_TABLE = """
CREATE TABLE IF NOT EXISTS vectors_optional (
    id TEXT PRIMARY KEY,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    vector_blob BLOB,
    created_at REAL NOT NULL DEFAULT 0.0,
    version TEXT NOT NULL DEFAULT 'cemm.vector.v1'
)
"""


INDEXES = {
    "idx_signals_source_time": "CREATE INDEX IF NOT EXISTS idx_signals_source_time ON signals(source_id, observed_at)",
    "idx_signals_context_kind": "CREATE INDEX IF NOT EXISTS idx_signals_context_kind ON signals(context_id, kind)",
    "idx_entities_type_name": "CREATE INDEX IF NOT EXISTS idx_entities_type_name ON entities(type, name)",
    "idx_entity_aliases_alias": "CREATE INDEX IF NOT EXISTS idx_entity_aliases_alias ON entity_aliases(alias)",
    "idx_claims_subject_predicate": "CREATE INDEX IF NOT EXISTS idx_claims_subject_predicate ON claims(subject_entity_id, predicate)",
    "idx_claims_predicate_model": "CREATE INDEX IF NOT EXISTS idx_claims_predicate_model ON claims(predicate_model_id)",
    "idx_claims_object_entity": "CREATE INDEX IF NOT EXISTS idx_claims_object_entity ON claims(object_entity_id)",
    "idx_claims_domain_source": "CREATE INDEX IF NOT EXISTS idx_claims_domain_source ON claims(domain, source_id)",
    "idx_claims_frame_time": "CREATE INDEX IF NOT EXISTS idx_claims_frame_time ON claims(frame_id, valid_from, valid_until)",
    "idx_claims_status_time": "CREATE INDEX IF NOT EXISTS idx_claims_status_time ON claims(status, observed_at)",
    "idx_models_kind_status": "CREATE INDEX IF NOT EXISTS idx_models_kind_status ON models(kind, status)",
    "idx_models_registry_key": "CREATE INDEX IF NOT EXISTS idx_models_registry_key ON models(registry_key)",
    "idx_models_name": "CREATE INDEX IF NOT EXISTS idx_models_name ON models(name)",
    "idx_actions_operator_status": "CREATE INDEX IF NOT EXISTS idx_actions_operator_status ON actions(operator_model_id, status, created_at)",
    "idx_self_updated": "CREATE INDEX IF NOT EXISTS idx_self_updated ON self_states(updated_at)",
    "idx_source_trust_domain": "CREATE INDEX IF NOT EXISTS idx_source_trust_domain ON source_trust(source_id, domain)",
    "idx_models_uol_key": "CREATE INDEX IF NOT EXISTS idx_models_name_uol ON models(name) WHERE kind='uol_semantic'",
}


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SIGNALS_TABLE)
    conn.executescript(ENTITIES_TABLE)
    conn.executescript(ENTITY_ALIASES_TABLE)
    conn.executescript(CLAIMS_TABLE)
    conn.executescript(CLAIM_EVIDENCE_TABLE)
    conn.executescript(CLAIM_QUALIFIERS_TABLE)
    conn.executescript(MODELS_TABLE)
    conn.executescript(MODEL_INPUT_TYPES_TABLE)
    conn.executescript(MODEL_OUTPUT_TYPES_TABLE)
    conn.executescript(MODEL_PRECONDITIONS_TABLE)
    conn.executescript(MODEL_EFFECTS_TABLE)
    conn.executescript(MODEL_EVIDENCE_TABLE)
    conn.executescript(MODEL_RELATED_ENTITIES_TABLE)
    conn.executescript(MODEL_RELATED_CLAIMS_TABLE)
    conn.executescript(ACTIONS_TABLE)
    conn.executescript(ACTION_INPUT_SIGNALS_TABLE)
    conn.executescript(ACTION_SELECTED_CLAIMS_TABLE)
    conn.executescript(ACTION_SELECTED_MODELS_TABLE)
    conn.executescript(SELF_STATES_TABLE)
    conn.executescript(SELF_MILESTONE_SIGNALS_TABLE)
    conn.executescript(SELF_ACTIVE_PROJECTS_TABLE)
    conn.executescript(SELF_LEARNED_MODELS_TABLE)
    conn.executescript(SOURCE_TRUST_TABLE)
    conn.executescript(FEEDBACK_TABLE)
    conn.executescript(VECTORS_TABLE)
    conn.commit()


def get_required_indexes() -> dict[str, str]:
    return dict(INDEXES)


def create_indexes(conn: sqlite3.Connection) -> None:
    for name, ddl in INDEXES.items():
        conn.execute(ddl)
    conn.commit()
