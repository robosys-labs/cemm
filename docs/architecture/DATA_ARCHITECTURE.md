# CEMM v3.5 Canonical Data Architecture

**Status:** replacement data contract  
**Goal:** make the semantic substrate modular, learnable, indexed, revisioned, and capable of referent state/event/claim reasoning.

---

## 1. Store separation

CEMM uses separate logical stores behind one pinned snapshot.

```text
SchemaStore
ReferentStore
KnowledgeStore
EvidenceStore
EventStateStore
DiscourseStore
LearningStore
OperationStore
PolicyStore
```

An initial SQLite deployment may place them in one database with separate tables. Interfaces and authority remain separate.

---

## 2. Source data versus runtime data

### 2.1 Reviewed source packages

Use modular JSONL/YAML for boot schemas, language packs, rules, and competence cases.

### 2.2 Compiled semantic database

Compile source packages into deterministic indexed SQLite artifacts.

### 2.3 Writable overlays

```text
global boot        read-only
tenant overlay     optional
user overlay       private learned data
session overlay    discourse/world/learning
cycle workspace    memory only
```

---

## 3. Source tree

```text
data/v350/
  manifest.json

  schemas/
    referent_types.jsonl
    facets.jsonl
    facet_entitlements.jsonl
    properties.jsonl
    state_dimensions.jsonl
    state_values.jsonl
    relations.jsonl
    roles.jsonl
    functions.jsonl
    actions.jsonl
    events.jsonl
    units.jsonl
    operators.jsonl
    discourse_acts.jsonl

  dynamics/
    transition_contracts.jsonl
    capability_dependencies.jsonl
    affordances.jsonl
    dispositions.jsonl
    causal_rules.jsonl
    default_rules.jsonl
    impact_rules.jsonl
    response_policies.jsonl

  foundation/
    self.jsonl
    seed_referents.jsonl
    seed_knowledge.jsonl

  languages/
    en/
    fr/
    sw/

  competence/
    foundation.jsonl
    composition.jsonl
    transitions.jsonl
    learning.jsonl
    impact_response.jsonl
    multilingual.jsonl

  migration/
    v347_ref_map.jsonl
```

---

## 4. Schema tables

### 4.1 Semantic schemas

```sql
semantic_schemas(
  schema_ref TEXT,
  revision INTEGER,
  schema_class TEXT,
  semantic_key TEXT,
  status TEXT,
  scope_ref TEXT,
  confidence REAL,
  permission_ref TEXT,
  provenance_set_ref TEXT,
  valid_from TEXT,
  valid_to TEXT,
  PRIMARY KEY(schema_ref, revision)
);
```

### 4.2 Inheritance

```sql
schema_parents(
  child_ref TEXT,
  child_revision INTEGER,
  parent_ref TEXT,
  parent_revision INTEGER,
  inheritance_kind TEXT,
  priority INTEGER,
  PRIMARY KEY(child_ref, child_revision, parent_ref, inheritance_kind)
);
```

### 4.3 Local ports

```sql
schema_ports(
  schema_ref TEXT,
  schema_revision INTEGER,
  port_ref TEXT,
  port_class TEXT,
  cardinality_min INTEGER,
  cardinality_max INTEGER,
  queryable INTEGER,
  allows_open INTEGER,
  context_policy TEXT,
  time_policy TEXT,
  identity_contribution INTEGER,
  PRIMARY KEY(schema_ref, schema_revision, port_ref)
);
```

### 4.4 Port constraints

```sql
port_constraints(
  schema_ref TEXT,
  schema_revision INTEGER,
  port_ref TEXT,
  constraint_kind TEXT,
  target_schema_ref TEXT,
  polarity TEXT,
  priority INTEGER
);
```

---

## 5. Facet and entitlement tables

```sql
facets(
  facet_ref TEXT,
  revision INTEGER,
  facet_class TEXT,
  semantic_key TEXT,
  status TEXT,
  PRIMARY KEY(facet_ref, revision)
);

facet_entitlements(
  type_schema_ref TEXT,
  type_revision INTEGER,
  facet_ref TEXT,
  applicability TEXT,
  activation_policy TEXT,
  inheritance_policy TEXT,
  value_domain_ref TEXT,
  default_rule_ref TEXT,
  condition_rule_ref TEXT,
  PRIMARY KEY(type_schema_ref, type_revision, facet_ref)
);
```

Additional normalized tables link types to:

- properties;
- state dimensions;
- roles;
- relations;
- functions;
- action affordances;
- observation channels.

---

## 6. Referent tables

```sql
referents(
  referent_ref TEXT PRIMARY KEY,
  storage_kind TEXT,
  identity_status TEXT,
  scope_ref TEXT,
  primary_context_ref TEXT,
  valid_from TEXT,
  valid_to TEXT,
  permission_ref TEXT,
  revision INTEGER
);

referent_type_assertions(
  assertion_ref TEXT PRIMARY KEY,
  referent_ref TEXT,
  type_schema_ref TEXT,
  type_revision INTEGER,
  status TEXT,
  confidence REAL,
  context_ref TEXT,
  valid_from TEXT,
  valid_to TEXT,
  evidence_set_ref TEXT,
  source_set_ref TEXT
);

identity_facets(
  identity_facet_ref TEXT PRIMARY KEY,
  referent_ref TEXT,
  facet_schema_ref TEXT,
  normalized_value TEXT,
  anchor_ref TEXT,
  confidence REAL,
  evidence_set_ref TEXT
);
```

---

## 7. Semantic application tables

```sql
semantic_applications(
  application_ref TEXT PRIMARY KEY,
  schema_ref TEXT,
  schema_revision INTEGER,
  context_ref TEXT,
  valid_time_ref TEXT,
  polarity TEXT,
  confidence REAL,
  assumption_set_ref TEXT,
  evidence_set_ref TEXT
);

application_bindings(
  application_ref TEXT,
  port_ref TEXT,
  filler_ref TEXT,
  filler_kind TEXT,
  open_variable_ref TEXT,
  ordinal INTEGER,
  confidence REAL,
  PRIMARY KEY(application_ref, port_ref, ordinal)
);
```

---

## 8. Proposition and claim tables

```sql
propositions(
  proposition_ref TEXT PRIMARY KEY,
  context_ref TEXT,
  polarity TEXT,
  modality_set_ref TEXT,
  valid_time_ref TEXT,
  revision INTEGER
);

proposition_content(
  proposition_ref TEXT,
  content_ref TEXT,
  content_kind TEXT,
  ordinal INTEGER
);

claim_occurrences(
  claim_event_ref TEXT PRIMARY KEY,
  claimant_ref TEXT,
  audience_set_ref TEXT,
  proposition_ref TEXT,
  commitment_kind TEXT,
  context_ref TEXT,
  time_ref TEXT,
  evidence_set_ref TEXT
);

claim_records(
  claim_ref TEXT PRIMARY KEY,
  claim_event_ref TEXT,
  proposition_ref TEXT,
  source_ref TEXT,
  source_context_ref TEXT,
  reported_context_ref TEXT,
  commitment_strength REAL,
  permission_ref TEXT,
  revision INTEGER
);
```

---

## 9. Knowledge tables

```sql
knowledge_records(
  knowledge_ref TEXT PRIMARY KEY,
  proposition_ref TEXT,
  truth_status TEXT,
  confidence REAL,
  context_ref TEXT,
  valid_time_ref TEXT,
  source_set_ref TEXT,
  evidence_set_ref TEXT,
  sensitivity TEXT,
  permission_ref TEXT,
  superseded_by TEXT,
  revision INTEGER
);
```

Support/opposition lineage should be normalized for efficient contradiction and retraction.

---

## 10. Event and state tables

### 10.1 Event occurrences

```sql
event_occurrences(
  event_ref TEXT PRIMARY KEY,
  event_schema_ref TEXT,
  occurrence_status TEXT,
  context_ref TEXT,
  time_ref TEXT,
  place_ref TEXT,
  confidence REAL,
  evidence_set_ref TEXT,
  proof_set_ref TEXT,
  revision INTEGER
);
```

Participants use ordinary semantic application bindings.

### 10.2 State assignments

```sql
state_assignments(
  assignment_ref TEXT PRIMARY KEY,
  holder_ref TEXT,
  dimension_ref TEXT,
  value_ref TEXT,
  status TEXT,
  context_ref TEXT,
  valid_from TEXT,
  valid_to TEXT,
  confidence REAL,
  evidence_set_ref TEXT,
  proof_set_ref TEXT,
  revision INTEGER
);
```

### 10.3 State deltas

```sql
state_deltas(
  delta_ref TEXT PRIMARY KEY,
  trigger_ref TEXT,
  holder_ref TEXT,
  dimension_ref TEXT,
  operation TEXT,
  from_value_ref TEXT,
  to_value_ref TEXT,
  magnitude_ref TEXT,
  context_ref TEXT,
  effective_time_ref TEXT,
  confidence REAL,
  proof_set_ref TEXT,
  commit_status TEXT
);
```

### 10.4 Transition contracts

```sql
transition_contracts(
  contract_ref TEXT,
  revision INTEGER,
  trigger_event_schema_ref TEXT,
  affected_port_ref TEXT,
  condition_pattern_ref TEXT,
  persistence TEXT,
  reversibility TEXT,
  warrant_class TEXT,
  status TEXT,
  PRIMARY KEY(contract_ref, revision)
);

transition_effects(
  contract_ref TEXT,
  contract_revision INTEGER,
  ordinal INTEGER,
  effect_kind TEXT,
  target_dimension_or_relation_ref TEXT,
  operation TEXT,
  value_expression_ref TEXT,
  condition_ref TEXT
);
```

---

## 11. Capability and function tables

```sql
affordance_rules(
  rule_ref TEXT PRIMARY KEY,
  holder_type_ref TEXT,
  action_schema_ref TEXT,
  condition_ref TEXT,
  status TEXT
);

capability_instances(
  capability_ref TEXT PRIMARY KEY,
  holder_ref TEXT,
  action_schema_ref TEXT,
  status TEXT,
  confidence REAL,
  context_ref TEXT,
  valid_from TEXT,
  valid_to TEXT,
  evidence_set_ref TEXT,
  revision INTEGER
);

capability_dependencies(
  dependency_ref TEXT PRIMARY KEY,
  action_schema_ref TEXT,
  requirement_kind TEXT,
  requirement_pattern_ref TEXT,
  failure_status TEXT
);

function_assignments(
  function_ref TEXT PRIMARY KEY,
  holder_ref TEXT,
  function_schema_ref TEXT,
  context_ref TEXT,
  valid_from TEXT,
  valid_to TEXT,
  source_set_ref TEXT
);
```

---

## 12. Impact and importance tables

```sql
impact_assessments(
  impact_ref TEXT PRIMARY KEY,
  source_event_or_state_ref TEXT,
  affected_ref TEXT,
  stakeholder_ref TEXT,
  affected_facet_set_ref TEXT,
  direction TEXT,
  valence TEXT,
  magnitude_ref TEXT,
  reversibility TEXT,
  duration_ref TEXT,
  confidence REAL,
  importance_ref TEXT,
  proof_set_ref TEXT,
  context_ref TEXT
);

importance_assessments(
  importance_ref TEXT PRIMARY KEY,
  subject_ref TEXT,
  stakeholder_ref TEXT,
  score REAL,
  importance_class TEXT,
  context_ref TEXT,
  valid_from TEXT,
  valid_to TEXT,
  evidence_set_ref TEXT,
  reason_set_ref TEXT
);
```

Do not store one global importance score on a referent.

---

## 13. Learning tables

```sql
learning_transactions(
  transaction_ref TEXT PRIMARY KEY,
  target_ref TEXT,
  package_class TEXT,
  status TEXT,
  scope_ref TEXT,
  max_depth INTEGER,
  created_revision INTEGER
);

learning_contributions(
  contribution_ref TEXT PRIMARY KEY,
  transaction_ref TEXT,
  contribution_class TEXT,
  target_ref TEXT,
  payload_ref TEXT,
  confidence REAL,
  evidence_set_ref TEXT
);

grounding_frontier(
  frontier_ref TEXT PRIMARY KEY,
  transaction_ref TEXT,
  target_ref TEXT,
  missing_contract TEXT,
  expected_schema_class TEXT,
  accepted_anchor_set_ref TEXT,
  depth INTEGER,
  sensitivity TEXT,
  status TEXT,
  best_question_plan_ref TEXT
);

competence_cases(
  case_ref TEXT PRIMARY KEY,
  target_schema_ref TEXT,
  use_profile TEXT,
  input_graph_ref TEXT,
  expected_graph_ref TEXT,
  independent_lineage_ref TEXT,
  required INTEGER
);
```

---

## 14. Discourse tables

Store both user and system turns semantically.

```sql
discourse_turns(
  turn_ref TEXT PRIMARY KEY,
  context_ref TEXT,
  speaker_ref TEXT,
  addressee_set_ref TEXT,
  discourse_act_ref TEXT,
  content_set_ref TEXT,
  response_goal_ref TEXT,
  surface_ref TEXT,
  emission_proof_ref TEXT,
  ordinal INTEGER
);

mention_chains(...)
open_questions(...)
acknowledgement_targets(...)
commitments(...)
common_ground(...)
topic_focus(...)
```

---

## 15. Language package data

Language packages contain:

```text
lexeme forms
lexeme senses → semantic schemas/operators
morphological paradigms
argument frames
syntax rules
scope evidence rules
reference paradigms
linearization
discourse realization
idioms
competence cases
```

They do not contain ordinary predicate answer sentences.

---

## 16. Indexes

Required indexes include:

- alias/language/sense;
- referent/type/context/time;
- facet entitlement by type;
- schema port constraints;
- application schema and filler;
- state holder/dimension/time;
- event schema/participant/time/place;
- claim proposition/source;
- knowledge proposition/status/context;
- capability holder/action/status;
- transition trigger schema;
- dependency reverse index;
- impact stakeholder/subject;
- learning target/frontier;
- discourse referent recency.

---

## 17. Materialized views

Materialized views may cache:

```text
referent type closure
referent knowledge view
current state projection
live capability projection
discourse salience
schema use profile
```

Every view stores a dependency fingerprint and invalidates on relevant revision changes.

---

## 18. Compiler validation

Hard failures:

- semantic type requiring source-code enum support;
- facet entitlement referencing a missing schema;
- property without holder/value contract;
- state dimension without applicability/value domain;
- event effect without a typed affected participant;
- capability dependency cycle without cycle classification;
- transition effect writing outside its context;
- impact rule lacking stakeholder semantics;
- response policy matching raw words;
- language sense targeting a missing schema;
- grammar rule inventing semantic content;
- competence case derived only from its teaching example.

---

## 19. Migration from v3.4.7

Convert:

```text
ReferentKind → storage kind + type assertions
PredicateSchema → typed semantic schema
has_state predicates → StateDimensionSchema applications
capable_of assertions → capability instances/affordances
seed operation descriptions → action schemas + lexicalization
language fixed bindings → argument/scope evidence
predicate_answers → grammar/argument frames
response_moves → discourse schemas and response policies
```

All rejected or ambiguous conversions are reported. No silent migration.

---

## 20. Retention and privacy

Different records have distinct retention:

- raw observations;
- evidence;
- claims;
- knowledge;
- sensitive state;
- importance assessments;
- session salience;
- learned schemas.

Importance and relationship history used for response selection must obey the same permission and retention policies as its source data.
