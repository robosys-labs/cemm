# CEMM v3.4 — Final Meaning-Backed Learning Pipeline

This document strengthens the existing recursive learning transaction. It does not create an ontology learner, second schema store, or separate interpretation path.

## 1. Learning is evidence-driven schema revision

The ordinary understanding path first determines whether an utterance supplies:

```text
instance fact
relation between existing schemas
lexeme-to-schema binding
partial definition
complete compositional definition
prototype/default generalization
correction or counterexample
source retraction
permission change
```

Not every teaching-looking utterance defines a concept.

The learning transaction receives grounded propositions and evidence records, never copied free-text fields as semantic authority.

## 2. Learning outcomes are distinct

The kernel may truthfully report:

```text
remembered
    exact attributed proposition/evidence committed

staged
    child revision exists but is not usable

provisionally usable
    structurally executable or partial revision committed for a qualified
    attributed/hypothetical/private context; limitations remain

understood for operations O in contexts C
    exact active revision has independent competence, valid dependencies,
    and admissibility for O/C

known/adopted as actual-world definition
    definition propositions satisfy epistemic policy for actual context
```

“Stored” and “learned” are never synonyms.

## 3. Evidence assimilation and lineage

Every evidence record stores source, transformation, derivation parents, lineage roots, independence cluster, context, and permission.

Derived propositions may be working knowledge but cannot increase support or competence for any schema in their transitive support ancestry or support strongly connected component.

A translation, paraphrase, generated case, summary, or copied source does not create new independent support.

## 4. Exact target and field provenance

A transaction targets an exact:

```text
lexical sense or candidate sense cluster
schema revision
schema field/pattern
relation orientation
construction
state/value constraint
realization binding
```

Every staged contribution records whether it is asserted, observed, entailed, inherited, hypothesized, defaulted, induced, adapter-supplied, or boot-supplied.

No hypothesis is silently rewritten as user teaching.

## 5. Grounding frontier and probe policy

The transaction computes the smallest blocking frontier over typed dependencies.

Priority:

```text
active goal blocker
required semantic family/role/value
constitutive structure
independent discrimination
differentiator
context/time applicability
enrichment
```

Budgets include:

```text
maximum dependency depth
maximum open gaps
maximum probes
maximum hypothesis branches
maximum schema size
maximum competence cost
maximum replay work
user-burden/repeated-question limit
```

Asked probe keys are persisted. Budget exhaustion leaves exact typed gaps and a resumable transaction. It does not mark failure, repeat the same question, or fabricate closure.

## 6. Child revision

Accepted evidence creates an immutable child revision in the same `SemanticSchemaStore` snapshot.

The child includes:

```text
base store revision
field-level contributions
typed dependencies
applicability contexts/time
support/counterevidence
GroundingSpecification
```

Untrusted learning is declarative. User data cannot install executable code or override formal kernel semantics.

## 7. Pattern learning

Patterns have independent function and strength.

```text
function:
  constitutive | identity | selectional | diagnostic |
  default | typical | incidental | causal | normative

strength:
  strict | defeasible | probabilistic
```

Instance induction proposes hypotheses with diagnostic/default/typical function and defeasible/probabilistic strength unless evidence establishes more. Induced patterns alone never activate a definition.

Exceptions preserve context, specificity, and provenance. Missing evidence is not an exception and is not negation.

## 8. Recursive definitions

The dependency graph is typed and analyzed before replay.

Supported direct joint activation is limited to inverse or positive-monotone clusters with a defined fixed point/inverse contract, external anchors, non-redundant member content, and independent joint competence.

Stratified defeasible cycles are evaluated by explicit strata. Unsupported non-monotone cycles remain provisional.

Joint cluster activation is one atomic store transaction.

## 9. Competence suite

Competence execution is sandboxed and cannot mutate memory, common ground, schema lifecycle, external state, or capability statistics until results commit.

Test classes:

```text
structural well-formedness
role/query behavior
positive recognition
real contrast/discrimination
licensed inference
context/polarity/time preservation
basic realization/reparse
```

Self-derived cases can pass structural tests only. Independent competence requires independent oracle lineage.

A shared implementation cannot generate both expected semantics and the pass decision without an independent invariant/comparator.

## 10. Epistemic admissibility

Structural closure answers whether the schema is executable. `EpistemicEvaluator` separately assesses definition propositions in actual, reported, user-belief, hypothetical, domain, and time contexts.

A false but compositional definition can remain provisionally usable in `reported_by(user)` without becoming actual-world knowledge or overriding a global schema.

Access scope and epistemic context remain separate.

## 11. Replay

Replay begins at the earliest affected checkpoint in the ordinary pipeline.

It verifies:

```text
original blocked interpretation
schema-family structure
expressiveness
typed dependency closure
recursive-cycle semantics
competence suite
context/admissibility behavior
query/inference behavior
realization/reparse where available
```

Replay key:

```text
source evidence
exact target sense/schema revision
checkpoint
context/scope
dependency/environment fingerprint
```

Replay is deduplicated, snapshot-pinned, retry-safe, and stale-cancellable. It never repeats external actions or already dispatched communication.

## 12. Atomic activation

Activation sequence:

```text
pin child and environment snapshot
→ derive structural assessment
→ run competence suite
→ derive admissibility profile
→ replay
→ compare-and-swap store/environment fingerprint
→ atomically commit active revision or cluster
→ publish typed invalidation and deferred-replay events
```

If independent competence or admissibility is incomplete, the child remains provisional. It may be committed with exact limitations, not falsely activated.

## 13. Invalidation and downgrade

Schema, policy, foundation, competence-suite, adapter-contract, or type-registry changes invalidate dependent assessments.

The existing truth-maintenance/dependency infrastructure retracts or marks stale:

```text
inherited constraints
classifications
inferred propositions
cached answers
plans
effect proposals
undispatched messages
capability/understanding conclusions
learning-success claims
```

Original evidence remains. Historical output remains an event and may generate a repair obligation.

Effects and irreversible operations revalidate at authorization and critical commit.

## 14. Correction, retraction, and forgetting

Operations are distinct:

```text
supersede schema/proposition meaning
retract a source's support
register counterevidence
revoke permission
archive from active retrieval
forget under user policy
privacy-delete/cryptographically erase where required
```

Each targets exact revisions/evidence and triggers dependency reassessment. A correction never mutates old historical interpretation in place; it creates a new reading/revision and explicit relation to the old.

## 15. Sense split and merge

New incompatible evidence creates a candidate sense or ambiguity set unless correction is explicit.

Alias/synonym/translation hypotheses compete with new-schema and specialization hypotheses.

Merge is reversible and non-destructive. Original refs and proposition bindings remain resolvable.

## 16. Consolidation

Deferred evidence, gaps, exceptions, and replay work have age, relevance, status, and retention policy.

Consolidation may summarize redundant storage while preserving lineage and claim identity. It cannot manufacture independent support, change asserted meaning, or bypass privacy deletion.

## 17. Learning completion gate

A learning change is complete only when:

- exact artifact and field provenance are known;
- ordinary understanding uses the changed revision;
- structural closure is valid;
- competence status is honestly represented;
- context/scope admissibility is explicit;
- replay is idempotent and successful for claimed competencies;
- activation, if any, committed atomically;
- dependent cognition has valid fingerprints;
- response wording matches the actual outcome.
