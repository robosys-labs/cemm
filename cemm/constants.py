"""Database ABI and tokenizer constants for CEMM v1.

The schema is generic: it stores semantic atoms/graphs, revisions, receipts,
common ground, and effects. It does not add tables per domain or referent type.
"""
import re

SCHEMA_VERSION = "3"

DDL = rf"""
PRAGMA foreign_keys=ON;
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS schema_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
INSERT OR IGNORE INTO schema_meta VALUES('schema_version','{SCHEMA_VERSION}');

CREATE TABLE IF NOT EXISTS atoms(ref TEXT PRIMARY KEY,kind TEXT NOT NULL,metadata TEXT NOT NULL DEFAULT '{{}}',generation INTEGER NOT NULL,authority_scope TEXT NOT NULL DEFAULT 'authority' CHECK(authority_scope IN('authority','world')));
CREATE TABLE IF NOT EXISTS operator_roles(operator_ref TEXT NOT NULL,role_ref TEXT NOT NULL,required INTEGER NOT NULL DEFAULT 0,cardinality TEXT NOT NULL DEFAULT 'one',filler_kind TEXT,PRIMARY KEY(operator_ref,role_ref));
CREATE TABLE IF NOT EXISTS applications(app_ref TEXT PRIMARY KEY,operator_ref TEXT NOT NULL,generation INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS bindings(binding_ref TEXT PRIMARY KEY,app_ref TEXT NOT NULL,role_ref TEXT NOT NULL,filler_kind TEXT NOT NULL CHECK(filler_kind IN('atom','literal','app')),filler_value TEXT NOT NULL,ordinal INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS observations(observation_ref TEXT PRIMARY KEY,surface TEXT NOT NULL,modality TEXT NOT NULL,language TEXT NOT NULL,source_ref TEXT NOT NULL,observed_at TEXT NOT NULL,packet TEXT NOT NULL,confidence REAL NOT NULL,generation INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS claims(claim_ref TEXT PRIMARY KEY,app_ref TEXT NOT NULL,observation_ref TEXT NOT NULL,stance TEXT NOT NULL CHECK(stance IN('support','deny')),confidence REAL NOT NULL,authority_status TEXT NOT NULL,valid_from TEXT,valid_to TEXT,generation INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS claim_occurrences(occurrence_ref TEXT PRIMARY KEY,observation_ref TEXT NOT NULL,act_ref TEXT NOT NULL,force TEXT NOT NULL,speaker_ref TEXT NOT NULL,addressee_ref TEXT NOT NULL,content TEXT NOT NULL,context_ref TEXT,modality TEXT NOT NULL,created_at TEXT NOT NULL,generation INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS epistemic_placements(placement_ref TEXT PRIMARY KEY,occurrence_ref TEXT NOT NULL,admission_class TEXT NOT NULL,admitted INTEGER NOT NULL,reason TEXT NOT NULL,context_ref TEXT,target_refs TEXT NOT NULL,created_at TEXT NOT NULL,generation INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS proof_links(proof_ref TEXT PRIMARY KEY,subject_ref TEXT NOT NULL,observation_ref TEXT NOT NULL,operation TEXT NOT NULL,parent_refs TEXT NOT NULL DEFAULT '[]');
CREATE TABLE IF NOT EXISTS rules(rule_ref TEXT PRIMARY KEY,rule_kind TEXT NOT NULL CHECK(rule_kind IN('definition','entailment','causal','default')),antecedent TEXT NOT NULL,consequent TEXT NOT NULL,confidence REAL NOT NULL DEFAULT 1,authority_status TEXT NOT NULL DEFAULT 'reviewed',generation INTEGER NOT NULL,definition_ref TEXT);
CREATE TABLE IF NOT EXISTS rule_candidates(candidate_ref TEXT PRIMARY KEY,rule_kind TEXT NOT NULL,antecedent TEXT NOT NULL,consequent TEXT NOT NULL,evidence_count INTEGER NOT NULL DEFAULT 1,status TEXT NOT NULL DEFAULT 'provisional',confidence REAL NOT NULL DEFAULT 0,first_generation INTEGER NOT NULL,last_generation INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS rule_index(rule_ref TEXT NOT NULL,side TEXT NOT NULL,operator_ref TEXT NOT NULL,semantic_ref TEXT,PRIMARY KEY(rule_ref,side,operator_ref,semantic_ref));
CREATE TABLE IF NOT EXISTS reference_forms(language TEXT NOT NULL,surface TEXT NOT NULL,features TEXT NOT NULL DEFAULT '{{}}',bound_ref TEXT,weight REAL NOT NULL DEFAULT 1,PRIMARY KEY(language,surface,bound_ref));
CREATE TABLE IF NOT EXISTS control_symbols(role TEXT PRIMARY KEY,semantic_ref TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS designation_index(label_ref TEXT PRIMARY KEY,target_ref TEXT NOT NULL,label_type_ref TEXT NOT NULL,surface TEXT NOT NULL,language TEXT NOT NULL,script TEXT NOT NULL,prior REAL NOT NULL,preferred INTEGER NOT NULL,context_ref TEXT);
CREATE TABLE IF NOT EXISTS label_stats(label_ref TEXT PRIMARY KEY,use_count INTEGER NOT NULL DEFAULT 0,last_used TEXT);
CREATE TABLE IF NOT EXISTS discourse_entities(atom_ref TEXT PRIMARY KEY,salience REAL NOT NULL,last_turn INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS frontiers(
  frontier_ref TEXT PRIMARY KEY,
  surface TEXT NOT NULL,
  reason TEXT NOT NULL,
  details TEXT NOT NULL,
  generation INTEGER NOT NULL,
  last_generation INTEGER NOT NULL,
  evidence_count INTEGER NOT NULL DEFAULT 1,
  status TEXT NOT NULL DEFAULT 'open'
);
CREATE TABLE IF NOT EXISTS generations(generation INTEGER PRIMARY KEY,parent_generation INTEGER,created_at TEXT NOT NULL,reason TEXT NOT NULL,content_hash TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS revision_state(
  singleton INTEGER PRIMARY KEY CHECK(singleton=1),
  world_revision INTEGER NOT NULL,
  discourse_revision INTEGER NOT NULL,
  observation_revision INTEGER NOT NULL,
  effect_revision INTEGER NOT NULL
);
INSERT OR IGNORE INTO revision_state VALUES(1,0,0,0,0);

CREATE TABLE IF NOT EXISTS commit_receipts(
  receipt_ref TEXT PRIMARY KEY,
  cycle_ref TEXT NOT NULL,
  stage INTEGER NOT NULL,
  expected_world_revision INTEGER,
  new_world_revision INTEGER NOT NULL,
  generation INTEGER NOT NULL,
  payload_hash TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS common_ground(
  entry_ref TEXT PRIMARY KEY,
  conversation_ref TEXT NOT NULL,
  act_ref TEXT NOT NULL,
  semantic_action TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  discourse_revision INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS effect_journal(
  effect_ref TEXT PRIMARY KEY,
  idempotency_key TEXT NOT NULL UNIQUE,
  goal_ref TEXT NOT NULL,
  adapter_ref TEXT,
  request TEXT NOT NULL,
  status TEXT NOT NULL,
  result TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  effect_revision INTEGER NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_rules_semantic ON rules(rule_kind,antecedent,consequent);
CREATE INDEX IF NOT EXISTS idx_app_operator_generation ON applications(operator_ref,generation);
CREATE INDEX IF NOT EXISTS idx_binding_lookup ON bindings(role_ref,filler_kind,filler_value,app_ref);
CREATE INDEX IF NOT EXISTS idx_binding_app ON bindings(app_ref,role_ref,ordinal);
CREATE INDEX IF NOT EXISTS idx_claim_active ON claims(app_ref,valid_to,stance,generation);
CREATE INDEX IF NOT EXISTS idx_claim_generation ON claims(generation,authority_status);
CREATE INDEX IF NOT EXISTS idx_observation_generation ON observations(generation,source_ref);
CREATE INDEX IF NOT EXISTS idx_rule_active ON rules(rule_kind,authority_status,generation);
CREATE INDEX IF NOT EXISTS idx_rule_index_lookup ON rule_index(side,operator_ref,semantic_ref,rule_ref);
CREATE INDEX IF NOT EXISTS idx_reference_surface ON reference_forms(language,surface,weight);
CREATE INDEX IF NOT EXISTS idx_designation_surface ON designation_index(language,surface,context_ref);
CREATE INDEX IF NOT EXISTS idx_designation_target ON designation_index(target_ref,language,context_ref);
CREATE INDEX IF NOT EXISTS idx_claim_occurrence_observation ON claim_occurrences(observation_ref);
CREATE INDEX IF NOT EXISTS idx_epistemic_occurrence ON epistemic_placements(occurrence_ref);
CREATE INDEX IF NOT EXISTS idx_state_subject ON bindings(role_ref,filler_value,app_ref);
CREATE INDEX IF NOT EXISTS idx_common_ground_conversation ON common_ground(conversation_ref,discourse_revision);
CREATE INDEX IF NOT EXISTS idx_frontier_open ON frontiers(status,reason,last_generation,evidence_count);
"""

TOK = re.compile(r"@[A-Za-z][0-9]+|@[0-9]+|<[A-Za-z0-9_:.=-]+>|[\wÀ-ÿ:/?.!'-]+|[^\s]", re.UNICODE)
