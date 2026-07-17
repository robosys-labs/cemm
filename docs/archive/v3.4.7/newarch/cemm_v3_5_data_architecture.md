# CEMM v3.5 Data Architecture

**Status:** proposed canonical data refactor  
**Baseline problem:** v3.4.7 stores most foundation semantics in one large `foundation.json`, language semantics and realization in large per-language JSON files, and many runtime records as JSON blobs in broad SQLite tables.  
**Goal:** modular, typed, compiler-validated source data that produces an indexed runtime semantic database and reusable multilingual grammar packages.

---

## 1. Data architecture principles

1. Human-authored semantic source data must be modular and reviewable.
2. Runtime lookup must use compiled indexed data, not repeatedly scan large JSON documents.
3. Semantic data contains no language surfaces.
4. Language data may reference semantic atoms but cannot activate meaning by itself.
5. Boot and learned schemas use the same revision and lifecycle model.
6. Source packages compile into a deterministic content-addressed artifact.
7. Every record carries provenance, version, scope, dependency, and validation status.
8. Runtime state is layered by global, tenant, user, session, and cycle scope.
9. Legacy identifiers are migrated through explicit mapping tables, never silent aliases.
10. JSON payloads are allowed for rare extensibility fields, not as the primary shape of core searchable data.

---

## 2. Source tree

```text
cemm/data/v350/
  manifest.json

  semantic/
    atoms/
      referent_types.jsonl
      properties.jsonl
      state_dimensions.jsonl
      state_values.jsonl
      actions.jsonl
      relations.jsonl
      roles.jsonl
      units.jsonl
      operators.jsonl
      discourse.jsonl

    profiles/
      type_profiles.jsonl
      self_profile.jsonl
      affordances.jsonl
      capability_contracts.jsonl

    rules/
      constitutive.jsonl
      strict.jsonl
      causal.jsonl
      enabling.jsonl
      preventing.jsonl
      defaults.jsonl
      pragmatic.jsonl
      relation_algebra.jsonl

    operations/
      builtins.jsonl
      adapter_contracts.jsonl

    competence/
      semantic_cases.jsonl
      operation_cases.jsonl
      learning_cases.jsonl

  languages/
    en/
      manifest.json
      lexemes.jsonl
      senses.jsonl
      morphology.json
      paradigms.jsonl
      syntax_rules.jsonl
      linearization_rules.jsonl
      discourse_realization.jsonl
      idioms.jsonl
      competence_cases.jsonl

    fr/
      ...

    sw/
      ...

  migration/
    v347_ref_map.jsonl
    v347_data_conversion.json
```

The source format may be JSONL, YAML, or another deterministic text format. JSONL is recommended for large append-friendly datasets and precise line-level review.

---

## 3. Compiled artifacts

The compiler produces:

```text
build/cemm-v350-semantic.sqlite
build/languages/en.cemm-lang
build/languages/fr.cemm-lang
build/languages/sw.cemm-lang
build/cemm-v350-manifest.json
build/cemm-v350-validation.json
```

The runtime opens immutable boot artifacts and writable overlay databases.

```text
boot semantic DB       read-only global schemas
tenant overlay DB      optional
user overlay DB        learned/private schemas and knowledge
session DB             discourse, state, pending learning
cycle workspace        in memory only
```

---

## 4. Core semantic tables

### 4.1 Meaning atoms

```sql
meaning_atoms(
  atom_ref TEXT,
  revision INTEGER,
  atom_class TEXT,
  semantic_key TEXT,
  status TEXT,
  scope_ref TEXT,
  confidence REAL,
  permission_ref TEXT,
  valid_from TEXT,
  valid_to TEXT,
  provenance_ref TEXT,
  PRIMARY KEY(atom_ref, revision)
);
```

### 4.2 Atom inheritance

```sql
atom_parents(
  child_atom_ref TEXT,
  child_revision INTEGER,
  parent_atom_ref TEXT,
  parent_revision INTEGER,
  relation_kind TEXT,
  priority INTEGER,
  PRIMARY KEY(child_atom_ref, child_revision, parent_atom_ref, relation_kind)
);
```

### 4.3 Atom-local ports

```sql
atom_ports(
  atom_ref TEXT,
  atom_revision INTEGER,
  port_ref TEXT,
  port_class TEXT,
  cardinality_min INTEGER,
  cardinality_max INTEGER,
  queryable INTEGER,
  allows_open INTEGER,
  identity_contribution INTEGER,
  context_propagation TEXT,
  time_propagation TEXT,
  PRIMARY KEY(atom_ref, atom_revision, port_ref)
);
```

### 4.4 Port type constraints

```sql
port_type_constraints(
  atom_ref TEXT,
  atom_revision INTEGER,
  port_ref TEXT,
  accepted_atom_ref TEXT,
  constraint_kind TEXT,
  polarity TEXT,
  priority INTEGER
);
```

### 4.5 Composition behaviors

```sql
atom_composition_rules(
  rule_ref TEXT PRIMARY KEY,
  atom_ref TEXT,
  rule_kind TEXT,
  input_signature_json TEXT,
  output_signature_json TEXT,
  constraints_json TEXT,
  priority INTEGER,
  status TEXT
);
```

The core type, port, and composition fields are normalized. JSON is reserved for uncommon rule-specific arguments.

---

## 5. Referent and profile tables

### 5.1 Referents

```sql
referents(
  referent_ref TEXT PRIMARY KEY,
  storage_kind TEXT,
  identity_status TEXT,
  scope_ref TEXT,
  context_ref TEXT,
  valid_from TEXT,
  valid_to TEXT,
  revision INTEGER,
  provenance_ref TEXT
);
```

`storage_kind` remains a broad serialization discriminator. Executable semantic typing lives in `referent_types`.

### 5.2 Referent typing

```sql
referent_types(
  referent_ref TEXT,
  type_atom_ref TEXT,
  type_atom_revision INTEGER,
  confidence REAL,
  source_ref TEXT,
  status TEXT,
  PRIMARY KEY(referent_ref, type_atom_ref, source_ref)
);
```

### 5.3 Identity facets

```sql
referent_identity_facets(
  referent_ref TEXT,
  facet_atom_ref TEXT,
  normalized_value TEXT,
  anchor_ref TEXT,
  confidence REAL,
  source_ref TEXT
);
```

### 5.4 Type profiles

```sql
type_profile_properties(
  type_atom_ref TEXT,
  property_atom_ref TEXT,
  requirement TEXT,
  default_rule_ref TEXT
);

type_profile_states(
  type_atom_ref TEXT,
  state_dimension_atom_ref TEXT,
  requirement TEXT
);

type_profile_affordances(
  type_atom_ref TEXT,
  action_atom_ref TEXT,
  affordance_kind TEXT,
  condition_rule_ref TEXT,
  priority INTEGER
);

type_profile_roles(
  type_atom_ref TEXT,
  role_atom_ref TEXT,
  admissibility TEXT
);
```

### 5.5 Runtime capability evidence

```sql
capability_instances(
  capability_ref TEXT PRIMARY KEY,
  holder_ref TEXT,
  action_atom_ref TEXT,
  status TEXT,
  confidence REAL,
  condition_set_ref TEXT,
  valid_from TEXT,
  valid_to TEXT,
  source_ref TEXT,
  evidence_ref TEXT,
  revision INTEGER
);

capability_conditions(
  capability_ref TEXT,
  condition_atom_ref TEXT,
  required_value_ref TEXT,
  requirement_kind TEXT
);
```

Permissions, resources, and competence are separate tables.

---

## 6. UOL and knowledge tables

### 6.1 Atom applications

```sql
atom_applications(
  application_ref TEXT PRIMARY KEY,
  atom_ref TEXT,
  atom_revision INTEGER,
  context_ref TEXT,
  confidence REAL,
  assumption_set_ref TEXT,
  source_evidence_set_ref TEXT
);
```

### 6.2 Port bindings

```sql
application_bindings(
  application_ref TEXT,
  port_ref TEXT,
  filler_ref TEXT,
  filler_kind TEXT,
  ordinal INTEGER,
  confidence REAL,
  open_variable_ref TEXT,
  PRIMARY KEY(application_ref, port_ref, ordinal)
);
```

`filler_ref` may reference a Referent, another atom application, a proposition, a coordination group, or a semantic variable according to the port contract. Every filler kind is explicit.

### 6.3 Semantic variables

```sql
semantic_variables(
  variable_ref TEXT PRIMARY KEY,
  expected_atom_class TEXT,
  expected_type_ref TEXT,
  restriction_application_ref TEXT,
  projection_kind TEXT,
  scope_ref TEXT
);
```

### 6.4 Propositions

```sql
propositions(
  proposition_ref TEXT PRIMARY KEY,
  context_ref TEXT,
  polarity TEXT,
  attribution_ref TEXT,
  valid_time_ref TEXT,
  epistemic_qualification TEXT,
  revision INTEGER
);

proposition_content(
  proposition_ref TEXT,
  semantic_ref TEXT,
  semantic_kind TEXT,
  ordinal INTEGER
);
```

### 6.5 Knowledge

```sql
knowledge_records(
  knowledge_ref TEXT PRIMARY KEY,
  proposition_ref TEXT,
  truth_status TEXT,
  confidence REAL,
  scope_ref TEXT,
  context_ref TEXT,
  source_set_ref TEXT,
  evidence_set_ref TEXT,
  permission_ref TEXT,
  sensitivity TEXT,
  valid_from TEXT,
  valid_to TEXT,
  superseded_by TEXT,
  revision INTEGER
);
```

---

## 7. Language package tables

### 7.1 Lexeme forms

```sql
lexeme_forms(
  lexeme_ref TEXT,
  language_tag TEXT,
  lemma TEXT,
  normalized_form TEXT,
  part_of_speech TEXT,
  paradigm_ref TEXT,
  register TEXT,
  frequency_rank INTEGER,
  status TEXT,
  PRIMARY KEY(lexeme_ref, language_tag, normalized_form)
);
```

### 7.2 Lexeme senses

```sql
lexeme_senses(
  sense_ref TEXT PRIMARY KEY,
  lexeme_ref TEXT,
  atom_ref TEXT,
  sense_kind TEXT,
  prior REAL,
  selection_constraints_json TEXT,
  argument_mapping_ref TEXT,
  status TEXT
);
```

A sense points to a meaning atom or operator, not a completed proposition.

Examples:

```text
English "can"  → operator:ability
English "do"   → operator:pro_action or action:perform depending context
English "what" → operator:query with entity/action/value type alternatives
English "name" → property:name
```

### 7.3 Argument realization frames

```sql
argument_frames(
  frame_ref TEXT PRIMARY KEY,
  language_tag TEXT,
  atom_ref TEXT,
  syntactic_head_role TEXT,
  voice TEXT,
  clause_family TEXT,
  constraints_json TEXT
);

argument_frame_slots(
  frame_ref TEXT,
  semantic_port_ref TEXT,
  syntactic_function TEXT,
  case_or_adposition_ref TEXT,
  optionality TEXT,
  ordering_class TEXT
);
```

### 7.4 Grammar rules

```sql
grammar_rules(
  grammar_rule_ref TEXT PRIMARY KEY,
  language_tag TEXT,
  rule_class TEXT,
  input_feature_pattern_json TEXT,
  output_feature_graph_json TEXT,
  priority INTEGER,
  status TEXT
);
```

Rule classes:

```text
clause formation
copular/property clause
modal composition
negation
question formation
relative clause
complement clause
coordination
argument sharing
reference realization
agreement
ellipsis
punctuation
```

### 7.5 Morphology

```sql
morph_paradigms(
  paradigm_ref TEXT PRIMARY KEY,
  language_tag TEXT,
  part_of_speech TEXT,
  stem_rules_json TEXT,
  feature_rules_json TEXT
);

morph_irregular_forms(
  lexeme_ref TEXT,
  feature_bundle_hash TEXT,
  surface TEXT
);
```

### 7.6 Idioms

Idioms are isolated:

```sql
idiom_rules(
  idiom_ref TEXT PRIMARY KEY,
  language_tag TEXT,
  form_pattern_json TEXT,
  atom_graph_json TEXT,
  non_compositional_reason TEXT,
  status TEXT
);
```

An idiom cannot be added merely because a regression sentence failed.

---

## 8. Source examples

### 8.1 Name property atom

```json
{
  "atom_ref": "property:name",
  "atom_class": "property",
  "semantic_key": "name",
  "parent_atom_refs": ["property:identity"],
  "ports": [
    {
      "port_ref": "holder",
      "accepted_atom_refs": ["type:referent"],
      "min": 1,
      "max": 1
    },
    {
      "port_ref": "value",
      "accepted_atom_refs": ["type:name_value", "type:text"],
      "min": 1,
      "max": 1,
      "queryable": true,
      "identity_contribution": true
    }
  ],
  "cardinality": "single_per_scope_and_time",
  "alias_projection": {
    "surface_port": "value",
    "target_port": "holder"
  }
}
```

### 8.2 Read action

```json
{
  "atom_ref": "action:read",
  "atom_class": "action",
  "semantic_key": "read",
  "parent_atom_refs": ["action:information_access"],
  "ports": [
    {
      "port_ref": "actor",
      "accepted_atom_refs": ["type:agent"],
      "min": 1,
      "max": 1
    },
    {
      "port_ref": "content",
      "accepted_atom_refs": ["type:information_object"],
      "min": 1,
      "max": 1,
      "queryable": true
    },
    {
      "port_ref": "source",
      "accepted_atom_refs": ["type:place", "type:digital_object"],
      "min": 0,
      "max": 1
    }
  ]
}
```

### 8.3 Ability operator

```json
{
  "atom_ref": "operator:ability",
  "atom_class": "modal_operator",
  "semantic_key": "ability",
  "ports": [
    {
      "port_ref": "holder",
      "accepted_atom_refs": ["type:agent"],
      "min": 1,
      "max": 1
    },
    {
      "port_ref": "action",
      "accepted_atom_classes": ["action"],
      "min": 1,
      "max": 1,
      "queryable": true
    }
  ],
  "evaluation_contract": "resolve_live_capability"
}
```

### 8.4 Software-agent affordance profile

```json
{
  "profile_ref": "profile:type:software_agent",
  "type_ref": "type:software_agent",
  "properties": [
    "property:name",
    "property:version",
    "property:capability_set"
  ],
  "states": [
    "state:operational_status",
    "state:availability",
    "state:connectivity"
  ],
  "affordances": [
    "action:observe",
    "action:read",
    "action:write",
    "action:retrieve",
    "action:learn",
    "action:reason",
    "action:remember",
    "action:answer",
    "action:communicate",
    "action:obey"
  ]
}
```

---

## 9. Data compiler

The compiler must:

1. parse all source modules;
2. validate unique IDs and revisions;
3. validate atom-class-specific fields;
4. compute inheritance closure;
5. detect illegal cycles;
6. compile local port constraints;
7. verify affordance/action compatibility;
8. verify state value domains;
9. verify units and dimensions;
10. validate rule variables and scope;
11. validate language senses against active atom refs;
12. validate grammar rule feature signatures;
13. run semantic competence cases;
14. run language round-trip cases;
15. produce deterministic SQLite and package artifacts;
16. emit a content fingerprint and dependency manifest.

Hard failures include:

- a surface string in semantic atom data;
- a language sense targeting a missing atom;
- a property with no holder/value semantics;
- an action whose actor type cannot inherit its declared affordance;
- a grammar rule that invents semantic content;
- a realization path with uncovered semantic ports;
- a circular strict definition without an external anchor;
- duplicate authority for the same atom revision.

---

## 10. Runtime overlays

Resolution order is not blind override.

```text
global boot
tenant
user
session
cycle candidate
```

Selection considers:

- exact sense and atom identity;
- context and possible world;
- validity interval;
- access permission;
- lifecycle status;
- epistemic admissibility;
- requested operation;
- specificity.

A user-scoped theory does not silently replace global actual-world meaning.

---

## 11. Migration from v3.4.7

### 11.1 Foundation conversion

```text
ReferentKind enum
→ broad storage discriminator + data-driven type atoms

PredicateSchema
→ MeaningAtomSchema(atom_class=property/state/action/relation)
  or compatibility reference

PortSchema
→ atom_ports + port_type_constraints

OperationSchema
→ operation contract linked to action atom

capable_of seed assertions
→ capability_instances backed by adapter/builtin evidence
```

### 11.2 Language conversion

```text
lexical entry → lexeme form + lexeme sense
fixed_bindings → argument-frame or construction evidence
predicate_answers → deleted after conversion to grammar/lexeme data
response_moves → discourse-act realization rules or semantic repair plans
pronoun table → referential grammar features
constructions → syntax/idiom evidence rules
```

### 11.3 Storage conversion

Current broad JSON columns are decoded and migrated into normalized tables. The migration generates:

- converted record count;
- rejected record count;
- unresolved semantic refs;
- legacy-to-new ref mapping;
- semantic equivalence cases;
- rollback database.

### 11.4 Compatibility boundary

Legacy refs can be accepted only through:

```text
legacy_semantic_ref_map
```

They must resolve to canonical atom refs before composition. No canonical v3.5 object may contain a legacy predicate ref after migration.

---

## 12. Deletion gates

The cutover is incomplete while any canonical path reads:

```text
foundation.json as one runtime authority
language.realization.predicate_answers
language.realization.response_moves
lexical fixed_bindings that assert semantic facts
surface → completed predicate shortcuts for modal/query/light verbs
```

These may remain only in migration fixtures or archived tests.

---

## 13. Data acceptance gates

1. Foundation compiles deterministically.
2. At least 95% of seed atom refs have executable competence cases.
3. Every referent type has a profile or explicitly inherits one.
4. Every action has an actor/initiator contract.
5. Every property has holder/value contracts.
6. Every state dimension has a value domain.
7. Every capability is linked to an action atom and evidence.
8. Every language sense targets an active atom.
9. No ordinary predicate requires a sentence template.
10. English, French, and Swahili packages realize the same UOL competence suite.
11. Restart hydration preserves learned atoms, senses, properties, and capabilities.
12. Migration produces no silent semantic drops.
