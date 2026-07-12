# CEMM v3.4 — Implementation Plan Delta

Do not add new architecture phases. Amend the existing phases.

## Phase 1 — Canonical model

Add `SchemaGroundingAssessment` as a derived control record and `GroundingSpecification` as common schema validation metadata.

Gate:

- semantic graph records remain unchanged;
- no new ontology object family is introduced.

## Phase 2 — Unified schema store and boot closure

Strengthen `SemanticSchemaStore`:

```text
resolve() returns candidate schemas regardless of executability
assess_grounding(revision) derives definition closure
activate(revision) requires successful assessment
```

Split boot data into:

```text
kernel formal foundations
audited boot concepts
language lexicalizations
```

Every audited boot concept needs a grounding specification and competency tests.

## Phase 4 — Authoritative understanding vertical slice

Extend `SemanticComposer` and `GroundingResolver` to preserve:

```text
schema-family hypotheses
provisional schema references
definition usability
missing definition fields
grounding blockers
```

Add scenarios:

```text
A dax is a wug.                # two opaque concepts; remember only
A leader directs a group.      # partial role-like definition
A president is a leader.       # deferred until leader grounded
What is a president?           # honest bounded response
```

## Phase 6 — Epistemics

Derive distinct assessments for:

```text
recorded assertion
accessible schema
supported definition
operational understanding
```

## Recursive learning phase

Strengthen existing learning transaction:

```text
target discrimination
schema-family completeness
closure/cycle analysis
child revision
ordinary replay
competency suite
activation through SemanticSchemaStore
```

Do not create an ontology learner beside it.

## Migration changes

Demote any code that treats these as sufficient for understanding:

```text
known lexeme
concept lattice node exists
parent relation exists
support_count threshold reached
teaching episode marked resolved
original example reparses
```

## First authoritative vertical slice

1. Teach an opaque relation: `A president is a leader.`
2. Verify CEMM stores the attributed proposition but refuses operational inheritance.
3. Teach a compositional `leader` definition using grounded predicates.
4. Verify the deferred relation replays.
5. Ask for the missing differentiator of `president`.
6. Teach formal-office/institution constraints.
7. Verify `president` activates and differs from generic `leader`.
8. Query, infer, contrast, and realize both concepts.
