# CEMM v3.4 — Final Foundational Acceptance Contract

Tests assert semantic structures, authorities, provenance, mutations, and outputs—not only strings.

## A. Governance and authority

### 1. Governing version consistency

- root `AGENTS.md` and `cemm/ARCHITECTURE.md` declare v3.4;
- their canonical source order points to these integrated files;
- no lower-priority v3.1/v3.3 document wins conflicts.

### 2. Single schema authority

- only `SemanticSchemaStore` activates revisions;
- validators and learning coordinator cannot activate directly;
- no session overlay or action registry resolves meaning independently.

### 3. No semantic dual representation

- relations such as `causes`, `is_a`, and `knows` are predications;
- structural links do not duplicate them as authoritative semantic edges.

## B. Original transcript regressions

### 4. Canonical contractions

Input: `I'm an engineer.`

Expected:

- raw `I'm` preserved;
- canonical decomposition supplies `I + am`;
- asserted `is_a(user, engineer)` or canonical occupation relation is composed;
- the required relation write is explicit;
- concept observation is auxiliary;
- no success claim if the relation fails to commit.

### 5. Occupation query

After test 4, input: `What do I do?`

Expected:

- query targets the occupation/classification relation;
- returns engineer with durable evidence;
- does not fall back to generic concept-definition query.

### 6. Nested epistemic query

Input: `Do you know what an engineer is?`

Expected:

- outer queried `knows(self, inner proposition pattern)`;
- inner definition query for `engineer`;
- user occupation fact does not satisfy concept definition;
- response distinguishes remembering the user fact from understanding engineer.

### 7. Metalinguistic correction

Input: `You don't know the meaning of the word “know”.`

Expected:

- quoted lexical-form referent preserved;
- negative proposition about self knowledge retained;
- `means(lexical_form, schema)` content represented;
- no positive knowledge effect or write;
- critique/pragmatic cue does not erase semantic content.

## C. Opaque concepts and definitions

### 8. Opaque relation preservation

Input: `A dax is a wug.`

- lexical refs and attributed proposition may commit;
- neither schema activates;
- no inheritance/effect/definition answer;
- self-report does not claim understanding.

### 9. Claim count does not ground meaning

Inputs:

```text
A leader leads.
Leading is what a leader does.
A leader is a chief.
A chief is a leader.
```

- support count cannot defeat ungrounded/circular closure;
- no operational activation.

### 10. Complete single definition can be structurally sufficient

Provide one compositional definition with required family fields and grounded dependencies.

- structural closure may pass;
- same-lineage tests yield provisional, not active, status;
- actual-context admission and independent competence remain separate.

### 11. False but compositional definition

Input: `A doctor is someone who owns a red car.`

- user-attributed theory may be structurally executable/provisional;
- it is not admitted as actual-world doctor meaning;
- global/audited schema is not overwritten;
- red-car ownership does not classify an actual doctor.

### 12. Typical feature is not identity

Input: `Birds typically fly.`

- pattern function is typical/default, not constitutive;
- bird definition does not close from flight;
- penguin remains a possible bird;
- absence of flight evidence is not refutation.

### 13. Expressiveness blocker

Teach definitions requiring negation, cardinality, modality, or time.

- supported constructs preserve semantics;
- unsupported constructs produce exact blockers;
- no silent approximation.

## D. Sense identity and scope/context

### 14. Polysemy split

Teach `leader` as a group-directing role and as a metal strip in a window.

- separate candidate senses;
- no contradiction across senses;
- evidence does not contaminate;
- exact sense used in each proposition is retained.

### 15. Opaque homonyms

Use one unknown spelling in two incompatible contexts before either is grounded.

- lexical form may be shared;
- candidate sense clusters remain distinct/reversible;
- no premature schema merge.

### 16. Alias versus new concept

Teach a new form with no differentiator from a grounded schema.

- alias/synonym/translation competes with new-schema hypothesis;
- duplicate active schema is not created without evidence.

### 17. Scope is not blind shadowing

Create a false/partial user-scoped revision over an active global schema.

- user-belief or convention queries can select it;
- actual-world queries retain globally admitted evidence unless explicitly scoped;
- formal/safety invariants remain active.

### 18. Context/time-qualified meaning

Teach a definition valid only in one institution, domain, jurisdiction, or period.

- applicability context/time recorded;
- no global promotion;
- out-of-context queries qualify or abstain.

## E. Evidence and competence

### 19. Self-certification rejected

Definition and all cases derive from one teaching utterance.

- well-formedness may pass;
- independent discrimination does not;
- child remains provisional;
- no unqualified `understands` claim.

### 20. Lineage-equivalent evidence collapses

Original, translation, paraphrase, summary, and generated examples share one root.

- one independence cluster;
- no false support multiplication.

### 21. Independent oracle

The same composer generates input semantics and expected graph.

- case cannot independently certify itself;
- invariant/audited expectation/independent observation is required.

### 22. Negative case uses open-world truth

A contrast has no positive evidence but no incompatibility.

- result is `neither`, not rejected;
- discrimination fails honestly.

### 23. Cross-schema inference laundering

A licenses evidence for B and B licenses evidence for A.

- transitive support SCC detected;
- competence/confidence of A and B do not increase from the cycle;
- derived propositions remain usable with provenance.

### 24. Field-level hypothesis honesty

Input: `A leader directs a group.`

- directs pattern is asserted;
- role family, occupancy, or bearer constraints are marked hypothesized/inherited where applicable;
- response does not attribute them to the user.

## F. Recursive closure and activation

### 25. Valid inverse/monotone cluster

Teach `buy/sell` with grounded transfer, goods, payment, and inverse roles.

- cycle class declared;
- fixed-point/inverse contract passes;
- independent joint competence passes;
- cluster activates atomically.

### 26. Non-monotone cluster blocked

Cycle contains negation, exception priority, permission, destructive update, or effect authorization.

- direct joint activation rejected;
- requires stratification or remains provisional;
- no effects enabled.

### 27. Activation race

Assess child against dependency D1; D2 commits before activation.

- compare-and-swap fails;
- no mixed-snapshot activation;
- reassessment required.

### 28. Joint activation atomicity

One member of a supported cluster fails commit.

- no member becomes active;
- provisional revisions/evidence remain consistent.

## G. Invalidation and replay

### 29. Dependency downgrade cascade

Ground leader, activate president, then quarantine/supersede leader.

- president assessment invalidates;
- inherited structure and use profile downgrade;
- evidence remains.

### 30. Derived cognition retraction

Before downgrade, materialize classification, inference, cached answer, plan, effect proposal, and undispatched message.

- all dependent artifacts retract/stale;
- external effect must reauthorize;
- historical dispatched output remains and may create repair goal.

### 31. Environment fingerprint invalidation

Change competence suite, foundation implementation, type registry, inference policy, or adapter contract without changing schema revision IDs.

- affected assessments invalidate;
- stale executable status is not consumed.

### 32. Replay idempotence

Deliver duplicate replay work and retries.

- one semantic result/commit;
- dedup key stable;
- stale entries cancel after supersession.

### 33. Replay budget and priority

Ground a widely depended-on schema.

- active goal blockers replay first;
- per-cycle limit enforced;
- remainder persists with evidence and blockers intact.

### 34. Probe frontier resume

Deep dependency chain exhausts probe budget.

- exact frontier and asked probes persist;
- no repeated interrogation;
- later evidence resumes transaction;
- no fabricated closure.

## H. Effects and causality

### 35. Structural effect schema does not execute

Teach a complete effect-bearing predicate from one source.

- may become provisional/structurally executable;
- can interpret/predict/propose only when use profile permits;
- no authorization, execution, or state mutation follows.

### 36. Live effect reauthorization

Authorize an operation, then change permission, capability, risk, schema use, or environment before execution/commit.

- authorization re-evaluates;
- blocked operation produces no effect claim.

### 37. Causal warrant grades

Teach `Pressing this button causes shutdown.`

- reported causal claim retained;
- warrant grade recorded;
- intervention planning blocked until required evidence grade/policy;
- teaching alone never fires shutdown.

## I. Correction, revocation, retention

### 38. Correction targets exact sense/revision

Correct one sense of a polysemous term.

- unrelated senses unaffected;
- new revision/readings explicit;
- old historical proposition meaning preserved.

### 39. Source support retraction

Retract the only independent support.

- support stops contributing;
- schema/derived cognition downgrades;
- provenance history remains where permitted.

### 40. Archival versus privacy deletion

- archival remains reversible/retrievable under policy;
- privacy deletion removes or cryptographically erases protected content;
- neither is mislabeled as the other.

## J. Self-awareness and NLG

### 41. Evidence-bound understanding report

Ask `Do you understand president?` when never seen, opaque, provisional, active/admitted, and invalidated.

- each clause binds to assessment/competence/blocker records;
- result is graded and operation-relative;
- no binary template claim.

### 42. Live capability report

Disconnect output/tool component or revoke permission.

- capability query reflects current implementation, health, resources, channel, and permission;
- static schema slots cannot override live status.

### 43. Commit-before-claim

Requested relation write fails while auxiliary concept observation commits.

- required write outcome is failure/partial;
- response does not say stored/learned.

### 44. Output commit after dispatch

Dispatch fails.

- intended text is not added to common ground;
- pending question/commitment is not created as if emitted.

### 45. Multilingual semantic equivalence

Equivalent supported utterances in multiple languages produce graph-isomorphic predications/propositions and compatible use profiles, while language-specific morphology remains in surface evidence.
