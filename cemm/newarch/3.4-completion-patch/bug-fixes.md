# CEMM v3.4 — Bug Fixes

**Target repository:** `robosys-labs/cemm`  
**Audited commit:** `d45a0f6e2989ef11122de9fef66786c40c7ef2a5`

This file contains concrete corrective work. Severity:

- **P0:** unsafe or invalidates core architectural truth;
- **P1:** blocks foundational v3.4 behavior;
- **P2:** required before final cutover;
- **P3:** cleanup/hardening.

---

# P0 — Immediate correctness and safety fixes

## BF-001 — Denied operations execute

**Files**

- `cemm/kernel/execution/executor.py`
- `cemm/kernel/execution/authorizer.py`
- `cemm/kernel/semantic_kernel_runtime.py`
- `cemm/tests/architecture/test_v34_components.py`

**Bug**

`OperationExecutor.execute()` checks:

```python
getattr(authorization, "authorized", True)
```

The real `AuthorizationResult` has:

```python
status: AuthorizationStatus
```

and no `authorized` property.

A denied real authorization therefore defaults to `True`.

**Fix**

Use an exact type/enum check:

```python
if authorization is None:
    fail closed

if authorization.status is not AuthorizationStatus.AUTHORIZED:
    fail
```

Authorization should be per operation, not one result reused for the whole plan.

Introduce:

```python
AuthorizationBatch {
    by_operation_ref: FrozenMap[str, AuthorizationResult]
}
```

The executor must require an authorized result matching each operation ID and current environment fingerprint.

**Tests**

1. Real `AuthorizationResult(DENIED)` never executes.
2. `None` authorization fails closed.
3. Authorization for operation A cannot authorize B.
4. Changed fingerprint requires reauthorization.
5. Adapter is not called on denial.

---

## BF-002 — Capability denial is converted into authorization success

**Files**

- `cemm/kernel/semantic_kernel_runtime.py`
- `cemm/kernel/self_model/capability_evaluator.py`

**Bug**

Runtime sets:

```python
capability_available = capability_assessment is not None
```

A negative assessment object is treated as available capability.

**Fix**

Use an explicit capability predicate/property:

```python
capability_available = capability_assessment.status in ("capable", "degraded")
```

Better: pass the exact `CapabilityAssessment` to `OperationAuthorizer`, and make the authorizer validate:

- subject;
- operation schema;
- conditions;
- environment fingerprint;
- validity interval.

Do not fabricate competence/implementation records in `run_turn()`.

Wire live registries/observers.

**Tests**

- missing channels/resources/permission produces denial;
- assessment existence alone never passes;
- degraded capability is qualified;
- capability for `understand` does not authorize `write`.

---

## BF-003 — Authorization defaults fail open

**Files**

- `cemm/kernel/execution/authorizer.py`

**Bug**

`AuthorizationConditions` defaults most checks to `True`.

A caller can omit safety, privacy, permission, resources, context, and schema use and receive authorization.

**Fix**

Default evidence-bearing gates to unknown/false.

```python
permission_allowed: bool | None = None
...
```

Unknown must produce `DEFERRED` or `DENIED`, never `AUTHORIZED`.

Require typed condition records and record refs, not bare Booleans, for high-risk/write/effect operations.

**Tests**

- empty conditions never authorize;
- missing schema-use profile never authorizes;
- missing permission never authorizes;
- low-risk cognitive read may use an explicit policy profile, not defaults.

---

## BF-004 — Legacy false write-success fallback remains

**File**

- `cemm/kernel/semantic_kernel_runtime.py::_build_write_outcome`

**Bug**

If exact required targets are missing but a write contract exists, all patch operation targets become “required.”

This lets an auxiliary concept/schema write satisfy a missing relation write.

**Fix**

Delete the fallback completely.

A `WriteContract` must contain exact required semantic identities before extraction/commit.

If extraction produces no matching required mutation:

```text
status = failed/partial
required_satisfied = false
```

Do not infer the contract from whatever patches happened to exist.

**Tests**

- “I’m an engineer” with only concept candidate committed cannot say stored;
- auxiliary `engineer` schema write cannot satisfy `is_a(user, engineer)`;
- zero required targets under a requested write is a contract-construction failure;
- response success clause requires exact semantic identity.

---

## BF-005 — Two persistent mutation authorities

**Files**

- `cemm/kernel/semantic_kernel_runtime.py`
- `cemm/kernel/execution/commit.py`
- `cemm/learning/patch_committer.py`
- `cemm/memory/durable_semantic_store.py`

**Bug**

Legacy `PatchCommitter` performs the actual durable semantic write.

The v3.4 `CommitCoordinator` separately simulates commits by incrementing an internal counter.

Both claim persistent-mutation authority.

**Fix**

Create one writable persistence interface and one `CommitCoordinator`.

Migration path:

1. add a `LegacyPatchMutationAdapter` converting validated legacy patches into exact `MutationOperation`s;
2. make `PatchCommitter` non-writing or retire it;
3. make `CommitCoordinator` apply operations to actual semantic/schema/discourse/transaction stores through a unit of work;
4. remove internal synthetic record IDs;
5. return real created/updated/superseded record refs;
6. use one commit outcome for response truth.

Until this is finished, disable legacy write success claims.

**Tests**

- one writer modifies semantic memory;
- rollback is atomic;
- commit outcome matches store state;
- no legacy patch can bypass `CommitCoordinator`;
- no synthetic success when store is unchanged.

---

## BF-006 — Old pipeline remains authoritative while runtime reports `v3.4`

**Files**

- `cemm/kernel/semantic_kernel_runtime.py`
- `cemm/kernel/pipeline.py`
- `cemm/types/runtime_cycle.py`
- `cemm/kernel/retirement/cutover.py`

**Bug**

The runtime labels diagnostics `pipeline = "v3.4"` despite using legacy semantic/query/write/response authorities.

`RuntimeCycleResult` calls v3.4 fields trace-only.

**Fix**

Until actual cutover:

```text
pipeline_status = hybrid_migration
v34_authoritative = false
legacy_authorities = [...]
```

Do not register an authority merely because an object exists.

The cutover verifier must verify call graph/output ownership, not only string registrations.

Add actual ownership assertions around:

- selected interpretation consumed downstream;
- query pattern consumed by retriever;
- mutation set used for actual write;
- message plan consumed by renderer.

**Tests**

- cutover verification fails on current hybrid runtime;
- diagnostics cannot claim v3.4 authoritative while legacy imports/hot-path calls remain;
- no xfail for final cutover gate.

---

## BF-007 — Grounded Definition Closure returns false positives

**Files**

- `cemm/kernel/schema/closure.py`
- `cemm/kernel/schema/pattern_assessment.py`
- `cemm/kernel/schema/grounding_spec.py`

**Bug**

The current assessment can be structurally executable while dependency, competence, recursion, and behavior checks are only blocked/unimplemented.

**Fix**

Define exact gate categories:

```text
required-for-structural-executability
required-for-active-status
informational-only
```

Structural executability must fail when:

- required dependency is unresolved;
- required role/type is unverified;
- required semantic construct has no evaluator;
- recursive component is unclassified;
- query/recognition behavior cannot instantiate;
- required constitutive pattern does not resolve.

Competence remains separate from structural closure but must block activation.

Resolve actual grounding spec and actual pattern refs from the envelope/store.

Never treat `BLOCKED` as success for a required gate.

**Tests**

- unresolved dependency prevents structural closure;
- missing competence prevents activation;
- unclassified recursion prevents activation;
- typical/probabilistic pattern cannot satisfy constitutive closure;
- unsupported pattern AST produces expressiveness blocker.

---

## BF-008 — Schema activation bypasses validation and is not atomic

**Files**

- `cemm/kernel/schema/store.py`
- `cemm/kernel/schema/activation.py`
- `cemm/kernel/learning/coordinator.py`

**Bug**

`SemanticSchemaStore.activate()` only checks lifecycle status and revision.

`activate_cluster()` sequentially changes statuses and later attempts rollback.

**Fix**

Require an activation request:

```text
record/cluster refs
expected record revisions
base store revision
environment fingerprint
grounding assessment refs
competence assessment refs
admissibility refs
target scope/context
```

The store verifies all refs/fingerprints and commits one atomic unit.

Use a real lock/transaction or immutable store-snapshot swap.

No public status setter may bypass activation policy.

**Tests**

- direct activation without assessments is rejected;
- dependency changes after assessment cause CAS failure;
- readers never observe partially active cluster;
- failed cluster activation restores exact prior state/revisions;
- concurrent child revisions never silently merge.

---

## BF-009 — Common ground records content that was not spoken

**Files**

- `cemm/kernel/semantic_kernel_runtime.py`
- `cemm/kernel/response/common_ground.py`
- response realization path

**Bug**

Legacy `ResponseFormationEngine` produces actual text.

Common ground records semantic items from an unused v3.4 message plan whenever any output text exists.

**Fix**

Only the message plan used by the renderer can be output-committed.

Renderer returns:

```text
RealizationResult {
    text
    realized_item_refs
    omitted_item_refs
    surface_spans_by_item
    dispatch_payload
}
```

After transport success, common ground records only `realized_item_refs`.

**Tests**

- omitted content is not recorded;
- legacy output cannot commit unrelated v3.4 items;
- failed dispatch creates no common-ground entry;
- a question obligation exists only if the question item was realized and dispatched.

---

## BF-010 — ResponsePlanner fails open to asserted stance

**File**

- `cemm/kernel/response/planner.py`

**Bug**

When no epistemic assessment is found, stance defaults to `ASSERTED`.

**Fix**

Default to `HEDGED`/blocked and require an assessment or a special non-truth-bearing discourse item.

A required factual item with no assessment should fail message validation.

**Tests**

- missing assessment cannot become asserted;
- commit outcome content binds exact mutation results;
- denied/blocked propositions are not realized as factual assertions.

---

# P1 — Foundational semantic-path fixes

## BF-011 — Replace the legacy perceptor bridge with a native language adapter

**Files**

- `cemm/kernel/understanding/percept_bridge.py`
- `cemm/language/interfaces.py`
- new `cemm/language/packs/en/...`
- app/runtime assembly

**Bug**

Legacy meaning decisions are imported as surface evidence.

**Fix**

Implement an English adapter that produces only reversible evidence:

- raw/canonical token stream;
- contraction decomposition;
- morphology/lemma;
- offsets;
- clause boundaries;
- quote spans;
- dependency candidates;
- lexical-sense candidates;
- construction candidates;
- communicative-force candidates;
- pragmatic cues.

No entity/predicate/intent selection.

Retain the old bridge only under `legacy/v3_3/adapter.py` and never as canonical authority.

---

## BF-012 — Hard-coded roles survive through the bridge

**File**

- `cemm/kernel/understanding/percept_bridge.py`

**Bug**

Roles are limited to:

```text
actor object target place
source target
```

**Fix**

Construction candidates refer to actual schema role refs.

The adapter proposes syntax-to-role alignments without enumerating role names globally.

The composer/grounder iterates schema roles.

---

## BF-013 — Global negation corrupts all propositions

**File**

- `cemm/kernel/understanding/composer.py`

**Bug**

Any negation token makes every proposition negative.

**Fix**

Derive polarity per clause/proposition using token scope/dependencies and context.

Preserve:

- lexical negation;
- constituent negation;
- proposition negation;
- negative quantifiers;
- quoted negation.

**Tests**

- “I know X but do not know Y” produces positive X, negative Y;
- quoted “not” does not negate the reporting proposition;
- “not only” does not become simple proposition negation.

---

## BF-014 — Opaque concept identity is random and non-durable

**Files**

- `cemm/kernel/understanding/composer.py`
- `cemm/kernel/schema/store.py`
- `cemm/kernel/schema/resolver.py`

**Bug**

Unknown refs include random UUIDs and are not registered.

**Fix**

Create stable lexical-form refs and reversible candidate sense clusters through `SemanticSchemaStore`.

Identity must include:

- language;
- normalized lexical form;
- context cluster;
- discourse evidence;
- provisional sense ID.

Do not automatically merge homonyms.

---

## BF-015 — Nested propositions are not parsed or role-bound

**Files**

- `cemm/kernel/understanding/composer.py`
- language constructions
- predication/proposition builders

**Bug**

`compose_nested()` is not called and only adds metadata; it does not bind the inner proposition into the outer predicate’s content role.

**Fix**

Composition must recursively build complement clauses and bind:

```text
knows.knower → self
knows.content → inner proposition
```

Questions retain open ports on the inner proposition.

**Tests**

- “Do you know what an engineer is?”
- “I think the server failed.”
- “She said the switch was off.”
- “I want you to learn this.”

---

## BF-016 — Generic question open ports are incorrect

**Files**

- `composer.py`
- `gap_detector.py`
- `retriever.py`

**Bug**

All questions create `role:unknown`, and downstream reads the wrong field name.

**Fix**

Open ports belong to exact predication roles and carry:

- role schema ref;
- type constraints;
- parent proposition;
- projection requested;
- cardinality;
- scope/context.

Retrieval queries those exact ports.

---

## BF-017 — Grounding hot path never grounds definitions

**Files**

- `semantic_kernel_runtime.py`
- `understanding/grounding.py`

**Fix**

For each selected candidate sense:

1. ground referent identity;
2. resolve exact schema revision;
3. fetch actual grounding spec/patterns/provenance/dependencies;
4. assess structural closure;
5. execute competence;
6. evaluate context admissibility;
7. derive operation-specific use profile.

Pass these results to interpretation and gaps.

Remove hard-coded generic grounding specifications.

---

## BF-018 — Interpretation ignores grounding and blocked admissibility

**File**

- `understanding/interpreter.py`

**Fix**

Branch selection must intersect:

- proposition/predication linkage;
- sense/schema candidates;
- role grounding;
- context;
- schema use profile for requested operation;
- epistemic admissibility;
- common ground/coherence;
- ambiguity and contradiction.

Blocked actual-world candidates may survive only as attributed/quoted/learning interpretations.

Use each proposition’s explicit `predication_ref`.

---

## BF-019 — Retrieval is a stub

**File**

- `epistemics/retriever.py`

**Fix**

Build `SemanticQueryPattern`s from:

- selected propositions;
- exact open ports;
- goals;
- context;
- schema revisions;
- participant/time/place constraints.

Query canonical semantic/evidence/schema/discourse stores.

Return record and evidence refs used by `EpistemicEvaluator`.

Delete `pass` retrieval branches.

---

## BF-020 — Epistemic evaluation uses placeholders

**File**

- `epistemics/evaluator.py`

**Fix**

- aggregate support by lineage clusters;
- implement temporal validity against snapshot clock;
- represent counterevidence search completeness/policy;
- derive causal warrant from typed evidence metadata;
- require schema use profile for actual-world admission;
- distinguish proposition support from schema-definition support;
- persist explanation refs.

---

## BF-021 — Capability observations are not live

**Files**

- `self_model/*`
- runtime assembly

**Fix**

Implement and wire:

- component registry;
- health observer;
- channel observer;
- resource observer;
- permission/policy observer;
- competence tracker;
- reliability tracker.

Evaluate the operation actually being planned, not a generic `op:understand`.

---

## BF-022 — Goal and plan semantics collapse to labels

**Files**

- `execution/goal_arbiter.py`
- `execution/planner.py`

**Fix**

Goals must reference desired propositions/information states.

Planner selects registered operation schemas and binds their roles.

Remove:

```text
goal kind → op:query/op:write/op:respond
```

The plan must contain exact query, write, learning, communicative, or adapter operation targets.

Never select a rejected plan as the chosen plan.

---

## BF-023 — Executor reports no-op success

**File**

- `execution/executor.py`

**Bug**

Without an adapter, operations succeed with empty outputs.

**Fix**

Provide explicit cognitive operation implementations:

- retrieve;
- evaluate;
- compare;
- infer;
- simulate;
- stage mutation;
- prepare message.

Unknown/unimplemented operation schemas fail as `implementation_missing`.

No-op is success only for an explicitly declared no-op schema.

Add a persistent/in-cycle idempotency registry.

---

## BF-024 — Critical commit has no semantic payload

**Files**

- `semantic_kernel_runtime.py`
- `execution/commit.py`
- `model/mutation.py`

**Bug**

Mutation payloads are operation IDs, not semantic records or deltas.

**Fix**

Executors return typed mutation proposals:

```text
FactMutation
SchemaRevisionMutation
StateTransitionMutation
DiscourseMutation
TransactionMutation
```

`MutationOperation` references immutable payload records with semantic identity and evidence.

Critical commit validates exact requested identity and expected revisions.

---

# P1 — Learning and schema bugs

## BF-025 — Competence harness trusts `passed=True`

**File**

- `schema/competence.py`

**Fix**

Cases contain inputs and expected invariant/pattern refs, not a caller-supplied verdict.

Harness executes in a read-only child snapshot:

- compose;
- ground;
- query;
- infer;
- contrast;
- realize/reparse where applicable.

An independent comparator returns pass/fail.

Lineage/independence are computed from evidence records, not trusted Booleans.

---

## BF-026 — Learning transaction never progresses in runtime

**Files**

- `semantic_kernel_runtime.py`
- `learning/coordinator.py`
- session/transaction persistence

**Fix**

Wire:

```text
open
→ hypotheses
→ grounding frontier
→ emitted probe
→ answer evidence
→ staged child
→ closure
→ competence
→ admissibility
→ replay
→ provisional/active commit
→ resume goal
```

Persist transactions and only bind a user turn to a question that was actually dispatched.

Remove the parallel old `LearningEpisodeManager` after migration.

---

## BF-027 — Learning activation path cannot work correctly

**File**

- `learning/coordinator.py`

**Bugs**

- every child becomes predicate kind;
- competence is called with empty cases;
- no replay;
- provisional child is not stored;
- admissibility is declared but not passed to use profile;
- fingerprint only includes base store revision;
- no event publication;
- completion gate is incomplete.

**Fix**

Use the child’s actual schema family and full snapshot.

Persist provisional revision with limitations.

Execute replay through the ordinary composer/grounder/resolver.

Enforce the complete completion gate.

---

## BF-028 — Replay queue is not connected

**Files**

- `learning/replay_queue.py`
- runtime/cycle scheduler
- operation executor
- schema activation/invalidation

**Fix**

- enqueue from dependency/activation events;
- persist queue and completed keys;
- call ordinary checkpoint replay;
- record executed/dispatched exclusions;
- cancel stale work;
- resume blocked goals;
- process under per-cycle budget.

---

# P2 — Boot, invalidation, correction, NLG, and retirement

## BF-029 — Boot validation is never executed

**Files**

- `boot/validation.py`
- runtime/app assembly

**Fix**

At startup:

1. build manifest;
2. validate foundations;
3. enter halted/diagnostic-safe/ready mode;
4. register boot schemas;
5. activate only through normal activation policy;
6. expose boot report in health diagnostics.

The runtime must not begin with an unseeded schema store while claiming v3.4 readiness.

---

## BF-030 — Boot tests are weak count/existence checks

**File**

- `boot/validation.py`

**Fix**

Replace “at least N predicates/types exist” with executable invariants:

- identity symmetry/transitivity constraints;
- before/after inverse behavior;
- state occupancy cardinality;
- context isolation;
- query projection;
- epistemic predicate derivation;
- serialization/content-hash stability.

Property test refs must resolve to independent implementations.

---

## BF-031 — Derived-cognition invalidation authority is falsely registered

**File**

- `semantic_kernel_runtime.py`

**Bug**

Cutover registration assigns `derived_cognition_retraction` to `EpistemicEvaluator`, which does not perform full retraction.

**Fix**

Implement an actual invalidation/retraction coordinator using typed dependency edges and provenance indexes.

It invalidates:

- assessments;
- classifications;
- inferences;
- answers;
- plans;
- undispatched messages;
- effect proposals;
- understanding/capability claims.

Register that component only after it is wired.

---

## BF-032 — Cutover verifier verifies names, not behavior

**Files**

- `retirement/cutover.py`
- runtime tests

**Fix**

Authority registration must include concrete callable/component identity and output field.

Verify:

- component is invoked;
- output is consumed by next authoritative stage;
- no legacy component writes the same decision;
- final durable/output behavior derives from it.

Remove default-true completion-gate arguments.

Completion checker must consume actual test/invariant reports.

---

## BF-033 — Final response is not generated from SemanticMessagePlan

**Files**

- response planner/realization;
- runtime;
- language realization pack.

**Fix**

Implement:

```text
SemanticMessagePlan
→ information structure
→ referring expressions
→ lexicalization
→ syntax/morphology
→ realization validation
→ dispatch
```

The old response engine may be a temporary surface renderer only if it consumes exactly the semantic message plan and is prohibited from selecting content/truth.

---

## BF-034 — Self-report builder is initialized but not used

**Files**

- `self_model/self_report.py`
- runtime/response planner

**Fix**

Self-knowledge/capability queries go through ordinary query and response planning using current assessments.

No static capability text.

---

## BF-035 — v3.4 state is not persisted

**Files**

- persistence interfaces;
- app/runtime;
- schema/learning/common-ground stores.

**Fix**

Persist:

- schema revisions and indices;
- learning transactions;
- replay work;
- evidence/propositions;
- common ground;
- operation/commit journals;
- capability observations;
- repair obligations.

Use a unit of work for atomic cross-store commits.

---

## BF-036 — Cutover tests are expected failures

**File**

- `tests/architecture/test_phase12_retirement.py`

**Fix**

Do not remove `xfail` until code is corrected.

At final cutover:

- make tests strict;
- zero legacy imports in canonical kernel;
- zero forbidden-pattern findings;
- no parallel hot path;
- all acceptance/end-to-end tests pass.

---

## BF-037 — Removed regression tests reduce safety during migration

**Scope**

Tests removed in latest legacy-removal commit include hot-path write truth, proposition integrity, relation identity, query cardinality, stress, response-formation, and deep diagnostic tests.

**Fix**

Restore relevant behavior as v3.4 end-to-end tests before deleting old tests.

Do not preserve old architectural expectations; preserve the failure scenarios and correctness invariants.

---

## BF-038 — Tracked `__pycache__` bytecode

**File**

- `cemm/kernel/__pycache__/pipeline.cpython-313.pyc`

**Fix**

Remove tracked bytecode and add repository ignore rules.

This is not a cognitive bug, but it undermines reproducible review and clean diffs.
