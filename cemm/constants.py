"""Constants for CEMM v1: database DDL and tokenizer regex.

Ported from v4 MVP kernel (cemm_mvp.py lines 27-48).
"""
import re

DDL = r"""
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS atoms(ref TEXT PRIMARY KEY,kind TEXT NOT NULL,metadata TEXT NOT NULL DEFAULT '{}',generation INTEGER NOT NULL,authority_scope TEXT NOT NULL DEFAULT 'authority' CHECK(authority_scope IN('authority','world')));
CREATE TABLE IF NOT EXISTS operator_roles(operator_ref TEXT NOT NULL,role_ref TEXT NOT NULL,required INTEGER NOT NULL DEFAULT 0,cardinality TEXT NOT NULL DEFAULT 'one',filler_kind TEXT,PRIMARY KEY(operator_ref,role_ref));
CREATE TABLE IF NOT EXISTS applications(app_ref TEXT PRIMARY KEY,operator_ref TEXT NOT NULL,generation INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS bindings(binding_ref TEXT PRIMARY KEY,app_ref TEXT NOT NULL,role_ref TEXT NOT NULL,filler_kind TEXT NOT NULL CHECK(filler_kind IN('atom','literal','app')),filler_value TEXT NOT NULL,ordinal INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS observations(observation_ref TEXT PRIMARY KEY,surface TEXT NOT NULL,modality TEXT NOT NULL,language TEXT NOT NULL,source_ref TEXT NOT NULL,observed_at TEXT NOT NULL,packet TEXT NOT NULL,confidence REAL NOT NULL,generation INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS claims(claim_ref TEXT PRIMARY KEY,app_ref TEXT NOT NULL,observation_ref TEXT NOT NULL,stance TEXT NOT NULL CHECK(stance IN('support','deny')),confidence REAL NOT NULL,authority_status TEXT NOT NULL,valid_from TEXT,valid_to TEXT,generation INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS proof_links(proof_ref TEXT PRIMARY KEY,subject_ref TEXT NOT NULL,observation_ref TEXT NOT NULL,operation TEXT NOT NULL,parent_refs TEXT NOT NULL DEFAULT '[]');
CREATE TABLE IF NOT EXISTS rules(rule_ref TEXT PRIMARY KEY,rule_kind TEXT NOT NULL CHECK(rule_kind IN('definition','entailment','causal','default')),antecedent TEXT NOT NULL,consequent TEXT NOT NULL,confidence REAL NOT NULL DEFAULT 1,authority_status TEXT NOT NULL DEFAULT 'reviewed',generation INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS rule_candidates(candidate_ref TEXT PRIMARY KEY,rule_kind TEXT NOT NULL,antecedent TEXT NOT NULL,consequent TEXT NOT NULL,evidence_count INTEGER NOT NULL DEFAULT 1,status TEXT NOT NULL DEFAULT 'provisional',confidence REAL NOT NULL DEFAULT 0,first_generation INTEGER NOT NULL,last_generation INTEGER NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS idx_rules_semantic ON rules(rule_kind,antecedent,consequent);
CREATE TABLE IF NOT EXISTS reference_forms(language TEXT NOT NULL,surface TEXT NOT NULL,features TEXT NOT NULL DEFAULT '{}',bound_ref TEXT,weight REAL NOT NULL DEFAULT 1,PRIMARY KEY(language,surface,bound_ref));
CREATE TABLE IF NOT EXISTS control_symbols(role TEXT PRIMARY KEY,semantic_ref TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS designation_index(label_ref TEXT PRIMARY KEY,target_ref TEXT NOT NULL,label_type_ref TEXT NOT NULL,surface TEXT NOT NULL,language TEXT NOT NULL,script TEXT NOT NULL,prior REAL NOT NULL,preferred INTEGER NOT NULL,context_ref TEXT);
CREATE INDEX IF NOT EXISTS idx_designation_surface ON designation_index(language,surface);
CREATE TABLE IF NOT EXISTS label_stats(label_ref TEXT PRIMARY KEY,use_count INTEGER NOT NULL DEFAULT 0,last_used TEXT);
CREATE TABLE IF NOT EXISTS discourse_entities(atom_ref TEXT PRIMARY KEY,salience REAL NOT NULL,last_turn INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS frontiers(frontier_ref TEXT PRIMARY KEY,surface TEXT NOT NULL,reason TEXT NOT NULL,details TEXT NOT NULL,generation INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS generations(generation INTEGER PRIMARY KEY,parent_generation INTEGER,created_at TEXT NOT NULL,reason TEXT NOT NULL,content_hash TEXT NOT NULL);
"""

TOK = re.compile(r"@[aAxX][0-9]+|@[0-9]+|<[A-Za-z0-9_:.=-]+>|[\wÀ-ÿ:/?.!'-]+|[^\s]", re.UNICODE)
