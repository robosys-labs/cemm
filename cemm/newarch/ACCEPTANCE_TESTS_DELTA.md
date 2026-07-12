# CEMM v3.4 — Foundational Reliability Acceptance Tests

Tests must assert structures and authority decisions, not only response strings.

## 1. Opaque relation preservation

Input:

```text
A dax is a wug.
```

Expected:

- lexical/schema refs may be created;
- user-attributed proposition persists;
- neither schema becomes active;
- no inheritance/effects/query definition are enabled;
- response does not claim understanding.

## 2. Claim count does not ground meaning

Inputs:

```text
A leader leads.
Leading is what a leader does.
A leader is a chief.
A chief is a leader.
```

Expected:

- circular dependency detected;
- no operational activation;
- support count cannot override closure failure.

## 3. Single complete definition may suffice structurally

Provide one definition containing semantic family, required roles, constitutive pattern, grounded dependencies, and differentiator.

Expected:

- semantic closure may pass from one utterance;
- confidence/scope remains governed by evidence policy;
- structural sufficiency is not blocked by an arbitrary two-fact minimum.

## 4. Parent grounding gate

Input:

```text
A president is a leader.
```

with opaque `leader`.

Expected:

- relation remains attributed/deferred;
- no inherited role/effect/query behavior;
- `understands(self, president)` and `understands(self, leader)` are false/not supported.

## 5. Child differentiator gate

Ground `leader`, then teach only:

```text
A president is a leader.
```

Expected:

- president may become typed as a candidate specialization;
- it does not become a complete non-synonym definition without differentiating constraints;
- system asks or records a gap for the distinguishing condition.

## 6. Role bearer separation

Input:

```text
Ada is the president of Club C.
```

Expected:

- Ada is an instance referent;
- president is a schema ref;
- role occupancy connects Ada, role, context, and time;
- instance and schema identities never unify.

## 7. Understanding versus remembering

After only the opaque assertion:

```text
Do you know what a president is?
```

Expected response semantics:

```text
remembers(self, user_assertion)
NOT understands(self, president_schema)
```

## 8. Ordinary replay proof

After completing `leader` and `president` definitions:

- original Turn 1 is replayed through normal composer/grounder/resolver;
- no special learning resolver is invoked;
- exact relation type is selected;
- competence tests pass before activation.

## 9. Boot concepts are ordinary schemas

For `person`, `agent`, `software_system`, and other boot concepts:

- records have boot provenance;
- grounding specifications exist;
- startup validation executes;
- no hard-coded domain Python type is required for meaning.

## 10. No new authority

Architecture test fails when any component outside `SemanticSchemaStore` can mark a schema active or independently determine executable understanding.

## 11. Jointly anchored cycle

Teach `buy`/`sell` as mutually referring definitions sharing grounded external dependencies (transfer, goods, payment).

Expected:

- the cycle is detected but classified as supported;
- both schemas may activate together via a joint competence suite;
- the unanchored `leader ↔ chief` cycle from test 2 still fails.

## 12. Dependency downgrade cascade

Ground `leader`, activate `president`, then quarantine `leader`.

Expected:

- the `president` assessment is invalidated via its closure fingerprint;
- `president` downgrades to partial/opaque usability;
- attributed evidence survives; nothing is deleted;
- re-grounding `leader` restores `president` through re-assessment, not from cache.

## 13. Self-certification rejection

One source teaches a definition and supplies the only discriminating competence cases.

Expected:

- session/user-scope activation may proceed per policy with the limitation journaled;
- promotion above user scope is blocked until independent discriminating cases exist;
- cases derived mechanically from the teaching utterance count only toward well-formedness.

## 14. Effect authorization gate

Teach a structurally complete predicate schema carrying effect semantics from a single unverified source.

Expected:

- the schema may reach executable usability;
- effect projection remains unauthorized;
- no state/action effect fires from it until effect authorization passes.

## 15. Defeasible exception handling

Teach `birds fly`, then `penguins are birds that cannot fly`.

Expected:

- flying is recorded as defeasible/typical for bird;
- the penguin exception is stored as an exception, not a contradiction;
- bird closure does not fail; penguin classification as bird survives.

## 16. Replay storm budget

Defer many relations on one opaque foundational schema, then ground it.

Expected:

- replays drain from a prioritized queue within a per-cycle budget;
- goal-blocking items replay first;
- unprocessed items remain queued with intact evidence and updated blockers.

## 17. Probe budget honesty

Teach a definition whose dependencies form a deep ungrounded chain.

Expected:

- probing stops at the episode's depth/gap budget;
- remaining dependencies persist as typed gaps;
- the schema stays partial and the response states exactly what is missing;
- no grounding is fabricated to close the episode.

## 18. Sense split and evidence accumulation

Teach `a leader directs a group`, then `a leader is a strip of metal holding window glass`.

Expected:

- the incompatible definition produces a candidate second sense or a sense-individuation probe — not a contradiction against the first;
- neither sense's evidence contaminates the other;
- separately, mentioning an opaque term across two sessions resolves to the same provisional ref, so deferred evidence accumulates instead of fragmenting.

## 19. Inference laundering rejected

Activate a schema, let it license inferences, and feed the inferred propositions back as evidence.

Expected:

- derivation provenance marks them as inferred with their ancestry;
- support/confidence/competence standing of ancestor schema revisions does not increase;
- the same propositions may still support unrelated schemas.

## 20. Proposition–revision binding under concept drift

Assert an instance fact under revision N of a schema, then activate a materially revised N+1.

Expected:

- the stored proposition still carries its revision-N reading;
- reinterpretation under N+1 appears only as an explicit journaled replay result;
- no stored proposition content is silently rewritten.

## 21. Evidence-bound self-report

Ask `Do you understand what a president is?` at each stage: never mentioned, opaque, partial, active.

Expected:

- each answer's clauses bind to derivable epistemic records (assessment, ledger entry, blocker set);
- the answer flows through the ordinary query path over those records;
- no self-claim exists without a backing record; missing derivation yields expressed uncertainty.

## 22. Expressiveness blocker instead of silent approximation

Teach a definition requiring negation or cardinality (`a bachelor is an unmarried adult`, `an institution has at most one president`).

Expected:

- if the construct is supported, closure evaluates it with correct truth/contradiction behavior;
- if unsupported, a concrete expressiveness blocker is produced;
- the definition is never approximated by silently dropping the construct.

## 23. Scope shadowing without mutation

Create a user-scoped revision of a globally active schema.

Expected:

- resolution in that user's context uses the user-scoped revision;
- the global revision is unchanged and continues serving other contexts;
- the shadowing decision is journaled in the interpretation trace;
- promotion of the user-scoped revision to global follows ordinary promotion policy.
