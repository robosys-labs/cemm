# CEMM v3.4 — Meaning-Backed Learning Pipeline

This is a strengthening of the existing recursive learning transaction.

## 1. Learning target discrimination

Before learning, determine what the user supplied:

```text
instance fact
relation between existing schemas
lexeme-to-schema binding
partial schema definition
complete schema definition
correction/counterexample
prototype or defeasible generalization
```

Do not treat every teaching statement as a schema definition.

## 2. Assimilate evidence normally

The user's teaching utterance is composed and grounded through the ordinary pipeline.

The learning transaction receives grounded propositions, not copied text fields.

Example:

```text
A president is a leader.
```

may yield evidence for a relation hypothesis between two schema referents. It does not by itself define either schema.

## 3. Evaluate current definition closure

For each affected schema revision, compute:

```text
semantic family resolved?
required definition shape complete?
parent/dependencies grounded?
constitutive pattern executable?
differentiator present where needed?
circularity-free?
competence specification satisfiable?
```

The result determines what can be staged and what must remain deferred.

## 4. Probe only the blocking foundation

The existing probe planner asks the highest-leverage missing question.

For an opaque `leader`, likely semantic questions are:

```text
Does “leader” name a kind of thing, or a role that a person/system can have?
Who or what can be a leader?
What relation or responsibility makes something a leader?
What group, activity, or goal is the leadership relative to?
When does something stop being the leader?
```

For `president` after `leader` is grounded:

```text
What makes a president different from another leader?
Is president a formal office in an institution?
How is the role acquired and when does it end?
```

The renderer chooses language. The learning system stores semantic expected-evidence patterns.

## 5. Child schema revision

Accepted evidence stages ordinary schema changes in the existing child `SemanticSchemaStore` revision.

No learning overlay, ontology side graph, or special concept database is introduced.

## 6. Replay and validation

Replay must prove more than parsing the original sentence.

It runs:

```text
original blocked interpretation
schema-family structural validation
dependency closure
non-circularity check
positive example
contrast/negative example
defining query projection
licensed inference test
basic realization/reparse where available
```

## 7. Activation and commit

`SemanticSchemaStore` activates the revision only when:

```text
Grounded Definition Closure passes
competence checks pass
required provenance/permission exists
schema identity/version is valid
promotion policy permits the requested scope
```

Evidence confidence may keep a semantically grounded definition session- or user-scoped. It does not make an ungrounded definition executable.

## 8. Deferred relation replay

Assertions involving opaque schemas remain ordinary attributed propositions plus deferred schema-relation evidence.

When a dependency later becomes grounded:

```text
retrieve affected provisional/deferred relations
re-evaluate exact relation type
replay original evidence
validate child schema differentiation
activate only if closure passes
```

## 9. Truthful learning outcome

The response can claim:

- **remembered** when the proposition was stored;
- **partially learned** only when a precise, usable partial artifact was committed and the limitation is stated;
- **understood/learned** only when the executable schema revision activated and replay/competence succeeded.
