# CEMM v3.4 — Completion Plan

**Target baseline:** `d45a0f6e2989ef11122de9fef66786c40c7ef2a5`

The plan completes v3.4 without adding a second architecture. It converts the existing scaffold into the one authoritative runtime and retires the hybrid path in controlled vertical slices.

---

# Completion principles

1. **Do not delete behavior before replacing its acceptance tests.**
2. **Do not call a component authoritative until its output drives the next stage.**
3. **One vertical slice must own perception → meaning → query/write → commit → response.**
4. **Fail closed during migration.**
5. **No compatibility fallback may manufacture semantic success.**
6. **Keep legacy only behind explicit one-way adapters.**
7. **Every phase must be implemented, wired, authoritative, and verified.**

---

# Stage 0 — Stabilize the migration baseline

## Goals

- stop false completion claims;
- restore regression safety;
- make hybrid status honest.

## Work

1. Apply BF-001 through BF-006.
2. Change diagnostics from `pipeline="v3.4"` to:
   ```text
   hybrid_v34_migration
   ```
3. Add a runtime feature mode:
   ```text
   legacy_compat_read_only
   v34_authoritative
   ```
4. In migration mode:
   - legacy may supply candidate evidence;
   - legacy may not independently execute effects;
   - legacy may not independently commit requested writes;
   - legacy response must not claim writes unsupported by exact v3.4 outcome.
5. Restore/rewrite deleted regressions:
   - write truth;
   - relation identity;
   - proposition integrity;
   - query cardinality;
   - contraction/occupation;
   - nested knowledge query;
   - response provenance;
   - stress/no-op safety.
6. Add real `AuthorizationResult` executor tests.
7. Remove tracked bytecode.
8. Add CI for:
   - unit;
   - architecture;
   - end-to-end;
   - legacy guard;
   - static type/import checks.

## Exit gate

- denied operation cannot execute;
- false write fallback removed;
- no success claim from auxiliary write;
- CI status required on every commit;
- hybrid mode reported honestly.

---

# Stage 1 — Create the actual canonical orchestrator

## Goals

Replace the monolithic hybrid `SemanticKernelRuntime` with the planned event-driven v3.4 cycle.

## Work

Create:

```text
cemm/kernel/cycle/kernel.py
cemm/app/runtime.py
```

`CognitiveKernel.run(trigger)` owns:

```text
ORIENT
UNDERSTAND
KNOW
DECIDE
ACT
CRITICAL_COMMIT
COMMUNICATE
OUTPUT_COMMIT
CONSOLIDATE/SCHEDULE
```

Use immutable `CognitiveCycle` revisions.

Move dependency construction to `app/runtime.py`.

Do not import old root kernel modules from canonical packages.

Create one explicit legacy boundary:

```text
cemm/legacy/v3_3/percept_adapter.py
```

Initially the adapter may supply surface candidates, but it cannot supply final predications, goals, contracts, writes, or response content.

## Exit gate

- public app entry returns `CognitiveCycle`/public result projection;
- `RuntimeCycleResult` no longer drives the canonical path;
- no canonical component reads hidden mutable legacy kernel state;
- cutover verifier observes actual field writers.

---

# Stage 2 — Native surface and compositional vertical slice

## Goals

Make the original failing conversation work through v3.4 without old phrase/act/query authorities.

## Work

Implement English language pack:

```text
tokenization
contractions
morphology
clause boundaries
quote scope
negation scope
copular constructions
wh constructions
complement clauses
pronoun/deictic candidates
```

Implement schema-generic role alignment.

Complete composer/grounder/interpreter for:

```text
I'm an engineer.
What do I do?
Do you know what an engineer is?
You don't know what “know” means.
```

Represent:

```text
is_a(user, engineer)
has_occupation(user, engineer) where licensed
knows(self, proposition)
means(lexical_form, schema)
mentions(utterance, lexical_form)
```

Opaque `engineer` remains a stable schema-sense candidate while the user fact may still be stored.

## Exit gate

- no whole-turn alias needed;
- exact relation write;
- no false definition claim;
- nested proposition graph is inspectable;
- multilingual adapters can target the same graph interface.

---

# Stage 3 — Make the schema store real

## Goals

Complete phases 1–3 and 5 of the architecture.

## Work

1. Store actual grounding specifications and field provenance with each schema revision.
2. Implement typed dependency resolution.
3. Correct Grounded Definition Closure.
4. Build real competence execution.
5. Add context/operation-specific use profiles.
6. Implement atomic single/cluster activation.
7. Add locks or immutable store transaction swap.
8. Persist schema revisions and indices.
9. Run boot validation at startup.
10. Load boot schemas through the same store APIs.
11. Enter diagnostic-safe mode on required boot failure.

## Exit gate

- no direct activation bypass;
- unresolved dependency blocks closure;
- self-derived tests cannot activate;
- boot store is non-empty and validated;
- all active records have assessment/admissibility refs;
- historical revisions remain resolvable.

---

# Stage 4 — Canonical retrieval and epistemics

## Goals

Make answers and self-knowledge evidence-backed.

## Work

1. Implement canonical semantic/evidence/schema/discourse persistence interfaces.
2. Implement `SemanticQueryPattern`.
3. Complete `SemanticRetriever`.
4. Aggregate evidence by lineage.
5. Implement temporal validity.
6. Implement four-state truth maintenance.
7. Implement proposition and schema-definition admissibility.
8. Implement typed causal warrant.
9. Derive:
   ```text
   remembers
   has_access_to
   knows
   knows_about
   understands
   believes
   uncertain_about
   ```
10. Wire current capability observers.

## Exit gate

- actual answers come from v3.4 retrieval;
- no call to legacy `SemanticQueryEngine`;
- “what do you know/not know?” is bounded and evidence-backed;
- false user theory remains attributed;
- self/capability answer cites live records.

---

# Stage 5 — Meaning-backed recursive learning

## Goals

Replace old episodes/teaching frames with one v3.4 transaction.

## Work

1. Persist learning transactions.
2. Implement exact target discrimination.
3. Implement competing hypotheses:
   - alias;
   - new sense;
   - specialization;
   - correction;
   - instance fact;
   - schema relation.
4. Implement grounding frontier and probe budgets.
5. Bind only actually dispatched questions.
6. Assimilate answer propositions through ordinary understanding.
7. Stage immutable child revision with field provenance.
8. Run closure/competence/admissibility.
9. Replay earliest checkpoint through ordinary pipeline.
10. Commit provisional/active revision atomically.
11. Resume blocked goal.
12. Retire:
   - `LearningEpisodeManager`;
   - `LearningQuestionPlanner`;
   - `LearningAnswerAssimilator`;
   - `TeachingFrameManager`;
   - old predicate inductor.

## Exit gate

- teaching changes ordinary next-turn interpretation;
- no parallel learning overlay/episode authority;
- replay does not repeat external action/output;
- outcome wording distinguishes remembered/provisional/understood.

---

# Stage 6 — Goals, plans, effects, and real commit

## Goals

Replace label plans and legacy operational contracts.

## Work

1. Goals become desired proposition/information-state refs.
2. Register internal operation schemas:
   - retrieve;
   - query;
   - compare;
   - infer;
   - simulate;
   - stage mutation;
   - ask;
   - answer;
   - realize;
   - dispatch.
3. Planner binds exact roles and preconditions.
4. Capability evaluator evaluates each operation.
5. Authorizer consumes live typed conditions.
6. Executor fails on missing implementation.
7. Add idempotency registry.
8. Outcomes contain real result/mutation refs.
9. CommitCoordinator writes actual stores via unit of work.
10. Revalidate authorization before irreversible action and critical commit.
11. Implement prediction-error reconciliation.

## Exit gate

- no generic `op:write` with empty bindings;
- no no-op success;
- one mutation authority;
- exact write contract;
- teaching an effect never fires it;
- legacy operational compilers no longer decide behavior.

---

# Stage 7 — Semantic NLG and discourse cutover

## Goals

Make `SemanticMessagePlan` drive what is said.

## Work

Implement:

```text
content validation
discourse ordering
information structure
referring expressions
aggregation
epistemic qualification
lexicalization
syntax
morphology
round-trip/reparse validation
transport dispatch
```

Renderer returns exact realized semantic item refs.

Commit common ground only after dispatch.

Generate repair obligations when invalidated prior claims were actually dispatched.

Retire old:

- `ResponseSituation`;
- `ObligationFrame`;
- content-selecting `ResponseFormationEngine`;
- output text parser/state updater.

A compatibility renderer may remain only if it consumes a fixed message plan and cannot alter content.

## Exit gate

- every clause maps to message content/provenance;
- v3.4 message plan and actual output agree;
- no unspoken item enters common ground;
- no internal IDs/open ports leak;
- output reparses compatibly.

---

# Stage 8 — Invalidation, correction, retention

## Goals

Complete phases 8 and 11.

## Work

1. Typed dependency/provenance index for all derived artifacts.
2. Invalidation events from:
   - schema supersession;
   - boot/adapter change;
   - evidence retraction;
   - permission change;
   - temporal expiry.
3. Retract/stale:
   - inference;
   - classification;
   - answer;
   - plan;
   - message;
   - effect proposal;
   - capability/understanding conclusion.
4. Preserve historical evidence/output events.
5. Implement distinct operations:
   - semantic supersession;
   - source retraction;
   - permission revocation;
   - archival;
   - forgetting;
   - privacy deletion.
6. Wire replay queue to activation/invalidation events.
7. Prevent cross-schema support laundering.

## Exit gate

- parent downgrade cascades correctly;
- duplicate replay is idempotent;
- stale plans/effects reauthorize;
- privacy deletion is not archival;
- prior wrong output creates bounded repair.

---

# Stage 9 — Legacy isolation and retirement

## Goals

Make phase 12 pass without expected failures.

## Removal sequence

### 9.1 Remove legacy response/query/write authorities

First retire:

```text
SemanticQueryEngine
PatchCommitter
GraphPatchExtractor as writer
ResponseFormationEngine as content selector
WriteOutcome fallback
```

### 9.2 Remove operational spine

Retire:

```text
SemanticProgramCompiler
OperationalMeaningCompiler
OperationalContractCompiler
state compilers
causal router
obligation builders
old planner/executor
```

### 9.3 Remove interpretation/perception authorities

Retire:

```text
SemanticCPU
MeaningPerceptor
MeaningGraphBuilder
InterpretationLattice
PredicateActivationResolver
old gap/learning stack
```

### 9.4 Move any retained translator under `legacy/v3_3/`

Canonical kernel imports no legacy.

### 9.5 Remove old stores/result types

Migrate data, then retire:

```text
PredicateSchemaStore
DurableSemanticStore direct APIs
RuntimeCycleResult
old SessionStore semantic state
```

## Exit gate

- `LegacyImportGuard` reports zero real violations;
- forbidden pattern scanner is clean;
- remove `xfail`;
- no deleted legacy test has an uncovered v3.4 regression;
- complete end-to-end suite passes.

---

# Stage 10 — Final verification and release declaration

## Required test suites

### Architecture

- one authority per decision;
- import boundaries;
- immutable records;
- atomic activation/commit;
- no fallback success;
- no direct writer bypass.

### Foundational semantics

- contractions;
- quote/negation scope;
- nested propositions;
- open ports;
- role-generic binding;
- opaque concepts;
- sense split/merge;
- definition closure;
- recursive clusters.

### Epistemics

- four-state truth;
- attributed vs actual;
- evidence lineage;
- temporal validity;
- causal warrant;
- self-knowledge/capability.

### Learning

- multi-turn probe;
- provisional commit;
- independent activation;
- replay/resume;
- correction/retraction;
- idempotence.

### Execution

- authorization denial;
- capability/resource/permission changes;
- no-op failure;
- exact write commit;
- rollback;
- effect revalidation.

### NLG/discourse

- message-plan provenance;
- dispatch/common ground;
- repair;
- round trip;
- multilingual graph equivalence.

### Stress

- concurrent child revisions;
- activation race;
- replay storm;
- deep grounding frontier;
- large evidence graph;
- restart/persistence recovery.

## Release status language

Only declare v3.4 complete when all are true:

```text
specified
implemented
wired
authoritative
verified
```

Until then, use:

```text
v3.4 migration implementation
```

and publish the remaining incomplete phase/gate list.

## Release declaration

**v3.4 is complete.** All five states hold for all 28 canonical authority components.

- 28/28 authority keys registered in `AuthoritativeCutoverVerifier`
- `CompletionGateChecker` passes with all 14 criteria met
- `LegacyImportGuard` reports zero real violations
- `ForbiddenPatternScanner` is clean
- Legacy v3.3 modules isolated to `cemm/legacy/v3_3/`
- 1013 tests pass with zero failures and zero expected failures
