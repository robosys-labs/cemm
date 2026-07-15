# Data definition guide

## Foundation predicate contract

```json
{
  "contract_id": "foundation:predicate:requires_for_goal:v1",
  "semantic_key": "requires_for_goal",
  "roles": [
    {"role_key": "requirer", "accepted_families": ["referent"]},
    {"role_key": "requirement", "accepted_families": ["referent"]},
    {"role_key": "goal", "accepted_families": ["referent"]},
    {"role_key": "context", "accepted_families": ["context"]}
  ],
  "identity_role_keys": ["requirer", "requirement", "goal", "context"],
  "query_projections": [
    {"projection_key": "query:requirement", "open_role_keys": ["requirement"]}
  ],
  "permitted_operations": ["recognize", "compose", "query", "infer", "realize"],
  "property_case_refs": [
    "independent:property:requires_for_goal:identity",
    "independent:property:requires_for_goal:query"
  ],
  "implementation_ref": "kernel:semantics:requires_for_goal"
}
```

The contract, implementation, and independent property cases—not the label—are
the meaning.

## Boot schema contract

```json
{
  "contract_id": "boot:schema:information_object:v1",
  "semantic_key": "information_object",
  "schema_family": "entity_kind",
  "dependency_refs": [
    "foundation:representation:referent",
    "foundation:predicate:represents:v1"
  ],
  "constitutive_pattern_refs": [
    "pattern:information_object:represents_content_with_provenance"
  ],
  "identity_criteria_refs": [
    "identity:information:content_provenance_encoding"
  ],
  "operational_port_refs": [
    "port:information:content",
    "port:information:provenance",
    "port:information:encoding"
  ],
  "competence_case_refs": [
    "independent:competence:information:representation_content"
  ]
}
```

## Language lexicalization

```json
{
  "schema_id": "lex:en:requires_for_goal:v1",
  "semantic_key": "requires_for_goal",
  "lemma": "need",
  "forms": {"base": "need"},
  "permitted_use_modes": ["assert", "qualified", "probe"],
  "contributions": [
    {
      "contribution_id": "contrib:en:need:predicate",
      "contribution_kind": "predicate",
      "semantic_key": "requires_for_goal"
    }
  ],
  "grounding_contract_ref": "foundation:predicate:requires_for_goal:v1",
  "competence_case_refs": [
    "competence:en:need:requires_live_goal_dependency"
  ],
  "round_trip_case_refs": [
    "roundtrip:en:need:requires_for_goal:v1"
  ]
}
```

## Realization restrictions

Content-bearing literal strings are forbidden. Segments may be:

```text
lexeme
grammatical_morpheme
referring_expression
role_value
mention
quotation
punctuation
space
```

Only punctuation and space may be unbound literal surface material.

## Learned operational attachment

A learned concept must attach through at least one:

```text
constitutive state pattern
constitutive relation pattern
constitutive event pattern
identity criterion
operation port
observation discriminator
```

Parent labels and related words alone do not make a concept executable.

## Rule definition

Every rule declares:

```text
premises
conclusions
strict/defeasible/probabilistic strength
cycle class
causal warrant
exceptions
existential variables
context and valid-time policy
sensitivity
firing limit
provenance
```

Unbound variables are rejected unless explicitly declared existential. Declared
existentials yield constraints rather than fabricated concrete referents.
