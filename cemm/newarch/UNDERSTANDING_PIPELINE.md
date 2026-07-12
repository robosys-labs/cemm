# CEMM v3.4 — Reliable Understanding Pipeline

This document modifies the existing UNDERSTAND stage. It does not add a new stage.

## 1. Perceive

Preserve reversible lexical and structural evidence:

```text
raw form
normalized form
lemma/morphology
span offsets
syntactic dependencies
quotation/negation/modality boundaries
candidate lexical senses
```

No unknown content word is silently converted into a generic entity or concept fact.

## 2. Compose

For each candidate sense, `SemanticComposer` creates:

```text
semantic target reference or provisional schema reference
candidate schema family
candidate predication/proposition structure
role bindings/open ports
context/polarity/modality
source evidence
```

Unknown terms remain explicit candidate senses. Surface recognition is not schema activation.

## 3. Ground

`GroundingResolver` resolves two different questions.

### Referent grounding

```text
What existing/new discourse or durable referent is being mentioned?
Is this an instance, schema referent, value, proposition, place, or context?
```

### Definition grounding

```text
Which schema revision defines this sense?
Is its semantic family known?
Are required definition fields present?
Are its dependencies grounded?
Is this revision operationally usable or only referentially available?
```

Grounded candidates therefore carry:

```text
selected/provisional schema ref
definition usability: executable | opaque | partial
missing definition fields
grounding dependency blockers
permitted operations
```

## 4. Resolve

`InterpretationResolver` may select an opaque/partial meaning when that is enough for the current goal.

Examples:

- quote or repeat the user's term;
- remember that the user asserted a relation;
- ask what the term means;
- search external/durable sources;
- preserve the concept for later learning.

It may not use opaque schemas for:

```text
inheritance
causal effects
state mutation
strong definition answers
selectional rejection that depends on unknown constraints
unqualified self-knowledge claims
```

## 5. Epistemic evaluation

The system separately assesses:

```text
I remember the assertion.
I can access a record about the term.
I know the asserted relation is supported/contested.
I understand the term's executable schema.
```

This allows truthful answers such as:

> I remember that you said a president is a leader, but I do not yet have enough grounded structure for “leader” to use that as a definition.

### 5.1 Evidence-bound self-reports

Every clause of a self-report must bind to a derivable epistemic record: the remembered proposition ref, the evidence ledger entry, the grounding assessment, or the blocker set.

- the renderer receives epistemic slots the same way it receives domain answer slots — it never invents epistemic claims;
- a self-report claim with no backing record is a realization error, not a stylistic choice;
- `SchemaGroundingAssessment` and epistemic derivations are queryable through the ordinary query path, so "do you understand X?" is answered by the same machinery as any other question.

## 6. Gap detection

A foundational gap is created only when missing definition structure blocks the selected goal.

Gap types reuse the existing `GapRecord`:

```text
missing_semantic_family
missing_parent_or_anchor
missing_bearer_or_holder_constraint
missing_constitutive_pattern
missing_required_role
missing_value_type
missing_differentiator
ungrounded_dependency
circular_definition
missing_competency_behavior
```

No new gap subsystem is required.

## 7. Understanding competence

An activated schema must support the competencies appropriate to its family.

Minimum generic checks:

```text
compose a positive example
reject or distinguish a negative/contrast example
answer at least one defining query
preserve role/context/polarity structure
produce a basic grounded paraphrase or explanation when lexical resources exist
```

Understanding is therefore operational, not a label attached to a graph node.

### 7.1 Competence case provenance

Competence cases must be independent of the definition they validate; otherwise activation is self-certifying.

Rules:

1. a case derived mechanically from the teaching utterance itself may check structural well-formedness only — it cannot count toward discrimination;
2. negative/contrast cases are drawn from sibling schemas, the parent minus the differentiator, or previously grounded near-neighbors — never generated from the candidate definition alone;
3. user-supplied competence cases are admissible, but a single source may not supply both the definition and its only discriminating cases at promotion scopes above session/user;
4. every competence case records its own provenance and participates in the same evidence ledger as other claims;
5. when no independent discriminating case exists yet, the schema may activate at session/user scope with the limitation journaled; broader promotion waits for independent discrimination.
