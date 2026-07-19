# CEMM v3.5 Phase 16 — Operation Boundary + Response UOL Planner

## 1. Objective

Phase 16 is the most delicate runtime boundary because it sits between **selected semantic goals** and **irreversible external effects / emitted semantic content**.

It must implement three strictly separated authorities:

1. **Operation planning, authorization, execution, and reconciliation** for selected action goals.
2. **Post-operation goal reconciliation** so operation outcomes can supersede/defer earlier response goals without mutating their history.
3. **Response UOL planning** that converts the final authorized semantic goals into proof-carrying response meaning graphs before any target-language realization.

The phase must not collapse these authorities into one “planner” that can silently act, invent response content, or treat side effects as rollback-safe database writes.

---

## 2. Canonical reconciliation required before coding

The current v3.5 documents contain a stage-number mismatch:

- `IMPLEMENTATION_PLAN.md` calls Phase 16 the **Response UOL planner**.
- `CORE_LOOP.md` places **PLAN_AUTHORIZE_EXECUTE_AND_RECONCILE** before response-goal generation and Response UOL construction.
- Phase 15 now already owns semantic obligation/goal generation and arbitration.

Phase 16 should therefore implement a **compound boundary** while preserving separate records/components:

```text
Phase 15 GoalDecisionRecord
        |
        +--> selected EXECUTE/operation goals
        |       -> OperationPlanner
        |       -> OperationAuthorizationGate
        |       -> OperationJournal pre-commit
        |       -> external adapter execution
        |       -> OperationResultRecord
        |       -> ReconciliationCoordinator
        |       -> ordinary evidence/epistemic/state-transition pipeline
        |
        +--> selected response-semantic goals
                -> ResponseMeaningPlanner
                -> proof-carrying ResponseUOLRecord
```

Do **not** reintroduce a second generic response-goal authority after Phase 15. Operation results may generate *new evidence/obligations* and trigger a new Phase-15 decision revision, but Phase 16 itself must not invent ungoverned goal kinds.

---

## 3. Non-negotiable laws

1. **Selected goal is not executable permission.** Execution requires fresh capability, permission, resource, risk, precondition and target binding checks at the execution snapshot.
2. **External effects are not GraphPatch transactions.** A network call, payment, file deletion, message send, or actuator command cannot be rolled back by reverting SQLite.
3. **Journal before side effect.** Every potentially external operation must have a durable intent/idempotency record before adapter invocation.
4. **Exactly-once claims are forbidden unless the adapter contract proves them.** Default to at-least-once/unknown outcome semantics with idempotency keys and reconciliation.
5. **No stale goal execution.** Operation planning pins the exact Phase-15 `GoalDecisionRecord`, goal candidate revision, target application, capability, permission/risk/resource evidence and operation schema revision.
6. **No optimistic success.** Adapter dispatch is not success. Success is a separately recorded observed/result state.
7. **Reconciliation uses ordinary epistemics/transitions.** Operation results become evidence/claims/events; they do not directly write arbitrary state facts.
8. **Response UOL cannot contain wording authority.** No language-specific sentence/template/punctuation/string fragments as semantic truth.
9. **Response UOL contains all and only selected authorized meaning.** Omission and aggregation must be proof-bearing transformations.
10. **No response planner may fabricate a missing answer.** Unknown dependencies remain qualification/repair/learning targets.
11. **Literal output is only allowed through explicit scoped external response policy** and remains marked as literal-policy output for Phase 17/verification.
12. **Operation output can invalidate the pre-operation goal decision.** The runtime must not emit a response planned from a snapshot invalidated by execution results.

---

## 4. Durable contracts

### 4.1 `OperationPlanRecord`

Pins:
- selected goal candidate/decision revisions;
- exact action schema/application;
- actor/holder and affected target refs;
- required ports and bound fillers;
- capability instance revision;
- permission/risk/resource/precondition evidence;
- predicted transition/impact refs;
- adapter contract revision;
- idempotency strategy;
- snapshot/store fingerprint.

No adapter-specific free-form command string may become operation authority.

### 4.2 `OperationAuthorizationRecord`

Contains independent gates:
- target completeness;
- affordance;
- live capability;
- permission;
- resource sufficiency;
- risk acceptance;
- preconditions;
- adapter availability;
- freshness/CAS.

Authorization is a hard decision, not a score. It is valid only for one exact store snapshot and must be discarded if the store changes before the `PREPARED` journal commit.

### 4.2a `OperationGateAssessmentRecord`

Every hard gate is an immutable durable assessment, not merely a name in `passed_gates`. It pins:
- exact `OperationPlanRecord`;
- gate identity;
- evaluator identity/revision;
- exact checked substrate pins;
- permission/authorization/proof refs;
- pass/fail result;
- exact snapshot fingerprint.

`ALLOW` requires exactly one current passing assessment for every required hard gate. Gate-name strings alone are never authority.

### 4.3 `OperationJournalRecord`

States should be structural lifecycle values such as:

```text
planned
preauthorized
prepared
submitted
acknowledged
observed_success
observed_failure
outcome_unknown
reconciled
cancelled_before_submit
```

The record must include:
- operation plan pin;
- idempotency key;
- adapter ref/revision;
- submission attempts;
- request/response evidence refs;
- external correlation refs;
- timestamps;
- permission/sensitivity;
- supersession lineage.

### 4.4 `OperationResultRecord`

Represents observed external outcome, not desired/predicted outcome. `SUCCESS`, `FAILURE`, and `PARTIAL` require observed evidence/proof; transport status alone cannot establish a domain outcome. Result persistence and the matching `OBSERVED_*` journal transition are one atomic local patch.

Must separate:
- transport acknowledgement;
- domain result;
- observed state/effect;
- uncertainty;
- partial completion;
- retryability;
- evidence/proof.

Crash recovery must explicitly handle `SUBMITTED`: restart queries adapter recovery state without resubmission. Missing recovery evidence degrades only to `OUTCOME_UNKNOWN`; it never proves failure.

### 4.5 `OperationReconciliationRecord`

Compares:
- predicted effects;
- submitted operation;
- returned result;
- subsequently observed state.

Outputs:
- evidence records;
- event/claim candidates;
- transition replay requests;
- contradiction records/frontiers;
- goal-decision invalidation triggers.

### 4.6 `ResponseUOLRecord`

Pins:
- final applicable `GoalDecisionRecord` revision;
- selected goal refs;
- source proposition/event/state/capability/impact/frontier refs;
- transformation proof refs;
- omission/aggregation decisions;
- discourse-act application refs;
- target audience/perspective refs;
- permission/sensitivity;
- unresolved response frontiers.

Contains a UOL graph/root set, never final surface strings. Nested semantic applications require exact goal/source lineage, are recursively closed into the graph, and every included application must be reachable from an authorized root.

### 4.7 `ResponseTransformationProof`

Each semantic transformation must identify:
- input refs;
- transformation schema/rule revision;
- output refs;
- authorization basis;
- omitted/aggregated refs;
- proof/evidence lineage.

---

## 5. Components

### 5.1 `OperationPlanner`

Consumes only selected action goals.

Responsibilities:
- bind exact action application;
- verify required ports are grounded;
- resolve actor/holder structurally;
- collect live capability/resource/risk/precondition evidence;
- pin adapter contract;
- produce predicted transition/impact references without committing them.

Forbidden:
- keyword/action-name routing;
- implicit actor selection;
- filling missing required ports from defaults as facts;
- selecting a different goal because execution is easier.

### 5.2 `OperationAuthorizationGate`

Revalidates immediately before submission.

Recommended order:
1. selected goal/decision still current;
2. target/action application unchanged;
3. capability still available for exact holder/action revision;
4. permission still valid;
5. resources sufficient;
6. preconditions true;
7. risk accepted;
8. adapter contract available;
9. idempotency/recovery contract valid.

Any failure -> no external side effect.

### 5.3 `OperationJournalCoordinator`

Atomic local commit **before** external call:
- plan;
- authorization;
- journal prepared state;
- exact dependencies.

Then adapter invocation occurs outside DB transaction.

### 5.4 `OperationExecutor`

A thin mechanical adapter boundary.

Adapter contract must expose:
- action schema compatibility;
- supported port mapping;
- idempotency capabilities;
- timeout/cancellation semantics;
- result schema;
- retry policy;
- security scope.

Adapters do not choose meaning or goals.

### 5.5 `OperationRecoveryCoordinator`

On restart:
- inspect nonterminal journal entries;
- query adapter/external correlation state where possible;
- never blindly retry unknown-outcome non-idempotent operations;
- produce explicit `outcome_unknown` frontiers when status cannot be proven.

### 5.6 `ReconciliationCoordinator`

Turns external observations into ordinary CEMM evidence.

Critical law:

```text
operation result
!= direct authoritative world-state mutation
```

Instead:

```text
adapter observation
-> EvidenceRecord
-> claim/event candidates
-> epistemic admission
-> transition proof/state update
-> impact/importance
-> Phase-15 re-arbitration if required
```

### 5.7 `ResponseMeaningPlanner`

Consumes the latest still-valid selected non-operation goals and reconciled operation-result goals.

Generic transformations:
- query answer closure;
- proposition projection;
- truth-status/uncertainty qualification;
- perspective transformation;
- state/property/event/capability reporting;
- impact-sensitive discourse act binding;
- explicit acknowledgement target binding;
- clarification/learning-frontier question semantics;
- aggregation/coordination;
- omission under authorization/privacy/budget;
- ordering/information structure hints that remain language-neutral.

### 5.8 `ResponseAuthorizationGate`

Before Response UOL commit:
- every content node traces to selected goal target/reason;
- every factual claim has admissible epistemic basis;
- no private source leaks across permission scope;
- uncertainty is preserved;
- no invented stakeholder relationship/emotion;
- literal-policy content is explicitly marked;
- no stale operation/goal dependencies.

### 5.9 `ResponseUOLCommitCoordinator`

CAS-commit:
- Response UOL;
- transformation proofs;
- omission/aggregation records;
- dependencies to goal decision and semantic sources.

No surface string is committed here.

---

## 6. Operation execution state machine

Recommended safe sequence:

```text
SELECTED ACTION GOAL
    -> plan
    -> authorize
    -> durable PREPARED journal
    -> adapter submit
    -> durable SUBMITTED/ACKNOWLEDGED/UNKNOWN
    -> observe result
    -> durable OperationResult
    -> reconcile through epistemics/transitions
    -> invalidate stale downstream goals/plans
    -> Phase-15 re-arbitrate if semantic state changed
    -> plan Response UOL
```

Never:

```text
DB transaction open
-> external side effect
-> rollback DB on error
```

That pattern falsely implies external rollback.

---

## 7. Response UOL transformation contracts

### 7.1 Query closure

Known answer:
- bind exact query variable to admissible knowledge result;
- preserve source/proof/uncertainty.

Unknown answer:
- no answer proposition fabrication;
- emit repair/learning/qualification semantic goal target only if selected by Phase 15.

### 7.2 Perspective transformation

Must be structural:
- speaker/addressee discourse participants;
- referent identity;
- deictic/time/place context.

No string replacement such as `I -> you`.

### 7.3 State/capability report

Must pin exact effective assignment/capability interval and context.
Historical state must not be emitted as current state.

### 7.4 Impact-sensitive response meaning

A consolation/warning/support discourse act must depend on:
- selected Phase-15 goal;
- Phase-14 significance proof;
- stakeholder target;
- uncertainty/permission.

No lexical trigger such as “died” may select the discourse act.

### 7.5 Repair question synthesis

Response UOL represents:
- unknown variable/frontier;
- expected structural family;
- accepted anchor types;
- reason for asking;
- priority/information gain.

Phase 17 realizes the question linguistically.

### 7.6 Aggregation and omission

Aggregation can merge content only when:
- compatible discourse act;
- compatible polarity/modality/time/context;
- no permission widening;
- no lost qualification;
- proof records identify the merge.

Omission under budget cannot silently drop mandatory warning/qualification obligations.

---

## 8. Invalidation rules

Invalidate operation plan/authorization when any pinned dependency changes:
- goal decision/candidate;
- action schema/application;
- capability;
- permission;
- resource;
- risk/precondition;
- adapter contract.

Invalidate Response UOL when:
- goal decision changes;
- operation result/reconciliation changes;
- source knowledge/state/impact changes;
- policy/permission changes;
- transformation rule changes.

Historical plans/results/UOL remain for audit.

---

## 9. Acceptance matrix

### Operations
1. selected action goal with missing port cannot execute;
2. capability owned by unrelated holder cannot authorize target action;
3. stale capability between plan and execution blocks submission;
4. permission revoked after planning blocks submission;
5. adapter timeout yields unknown/partial outcome, not success;
6. non-idempotent unknown outcome is not blindly retried after restart;
7. idempotent operation reuses same key across safe retry;
8. predicted transition is not committed merely because adapter accepted request;
9. observed operation result flows through epistemics/transitions;
10. external result invalidates stale response plan and triggers re-arbitration.

### Response UOL
11. known query produces answer meaning with exact proof lineage;
12. unknown query cannot fabricate answer;
13. private knowledge cannot enter broader Response UOL;
14. uncertainty/attribution survives transformation;
15. acknowledgement binds exact target;
16. impact-sensitive support requires Phase-14/15 lineage;
17. aggregation preserves polarity/modality/time/qualification;
18. mandatory qualification cannot be omitted by budget ranking;
19. no target-language sentence/template exists in semantic planner;
20. concept/schema renaming leaves generic planning behavior invariant.

### Restart/concurrency
21. prepared/submitted operation journal rehydrates deterministically;
22. stale snapshot CAS refuses Response UOL commit;
23. concurrent correction before emission invalidates old plan;
24. duplicate operation-result delivery is idempotently reconciled;
25. dependency cycles/frontiers remain bounded.

---

## 10. Performance gates

Measure separately:
- operation-plan lookup;
- authorization latency;
- journal write latency;
- adapter overhead excluding remote service latency;
- recovery scan cost;
- response transformation count;
- UOL node/edge growth;
- dependency-edge count;
- invalidation fanout.

All hot exact-ref/revision lookups must have query-plan proof.

---

## 11. Implementation sequence

### 16A — canonical stage contract reconciliation
Update core-loop/architecture docs so Phase 15 remains sole generic semantic goal authority.

### 16B — operation durable contracts + schema/indexes

### 16C — operation planner

### 16D — authorization gate

### 16E — journal + external adapter boundary

### 16F — execution result/recovery contracts

### 16G — reconciliation into epistemic/transition pipeline

### 16H — post-operation invalidation and Phase-15 re-arbitration

### 16I — Response UOL durable contracts

### 16J — proof-carrying transformation algebra

### 16K — response authorization/privacy gate

### 16L — atomic Response UOL commit

### 16M — restart/concurrency/adversarial suite

### 16N — performance/query-plan proof

### 16O — shadow cutover, trace comparison, authority cutover

---

## 12. Exit gate

Phase 16 passes only when:

- no external operation can execute without exact fresh authorization;
- external side effects are journaled/recoverable without pretending they are DB-rollback-safe;
- operation results re-enter ordinary epistemic/state machinery;
- stale pre-operation goals/plans are invalidated;
- every Response UOL node is authorized by an exact selected goal and semantic source;
- no language-specific wording is semantic authority;
- restart/concurrency cannot duplicate or fabricate operation success;
- no domain-specific action/response branches are required in kernel code.
