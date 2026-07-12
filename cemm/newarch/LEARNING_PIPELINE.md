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

### 2.1 Derived evidence never supports its own ancestry

Every proposition carries derivation provenance: observed, attributed, or inferred (with the schema revisions and premises that licensed the inference).

An inferred proposition:

- may not increase support, confidence, or competence standing for any schema revision in its own derivation ancestry;
- may not count as an independent discriminating competence case for those schemas;
- may still serve as ordinary working knowledge and as evidence for unrelated schemas.

Without this rule, an activated schema licenses inferences whose outputs are laundered back as support for the schema itself — belief reinforcement without new information.

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

### 4.1 Probe budget and grounding frontier

Dependency probing must be bounded. Each learning episode carries:

```text
maximum probe depth along a single dependency chain
maximum open foundational gaps per episode
frontier priority: goal-blocking > differentiator > constitutive > enrichment
```

When the budget is exhausted, remaining dependencies stay as typed gaps, the schema remains `partial`, and the episode reports honestly what is still missing. The system never chases an unbounded definition regress in one conversation and never fabricates grounding to escape it.

## 5. Child schema revision

Accepted evidence stages ordinary schema changes in the existing child `SemanticSchemaStore` revision.

No learning overlay, ontology side graph, or special concept database is introduced.

### 5.1 Defeasible and prototype structure

Not every constitutive pattern is a strict necessary condition. Natural concepts are frequently prototype-based (`birds fly`).

Constitutive and differentiating patterns therefore carry an explicit strength:

```text
strict      — violation defeats classification
defeasible  — violation lowers typicality; explicit exceptions permitted
typical     — evidence for recognition ranking only
```

Competence checks must respect strength: a defeasible pattern's counterexample (`a penguin is a bird that cannot fly`) is recorded as an exception, not a contradiction, and does not defeat closure. Strict patterns remain subject to ordinary contradiction handling.

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

### 8.1 Replay budget

Activating a widely depended-on schema may unlock many deferred items. Replay drains from a prioritized queue, never as an unbounded storm:

```text
priority: active goal blockers > user-asked questions > recent episodes > background
per-cycle replay budget; the remainder stays queued with evidence intact
each replayed item re-enters the ordinary pipeline; failures re-defer with updated blockers
```

The reverse dependency index used here is the same index that drives assessment invalidation.

## 9. Truthful learning outcome

The response can claim:

- **remembered** when the proposition was stored;
- **partially learned** only when a precise, usable partial artifact was committed and the limitation is stated;
- **understood/learned** only when the executable schema revision activated and replay/competence succeeded.

## 10. Instance-driven schema induction

Verbal definition is not the only learning path. Accumulated grounded instance facts about an opaque or partial schema may propose candidate constitutive/differentiating patterns.

Induced patterns:

- enter as hypotheses with `defeasible` strength at most;
- record induction provenance (the instance evidence set that produced them);
- never activate a schema by themselves;
- must pass the same closure, competence, and provenance gates as taught definitions.

This gives the organism an ostensive learning channel without weakening the activation gate.

## 11. Consolidation and bounded growth

Deferred relations, exceptions, gaps, and evidence ledgers grow without bound unless consolidated.

Policy requirements:

```text
deferred items carry age and staleness; stale items are archived, not deleted
archived items remain retrievable and replayable when their blockers ground
redundant evidence for the same claim consolidates into summarized support with provenance intact
consolidation is journaled and never changes what is claimed — only how it is stored
```

Forgetting-by-archival is an explicit, reversible act. Silent evidence loss is forbidden.
