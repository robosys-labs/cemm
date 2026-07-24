# CEMM v3.5 Phase 15 — Goals, Obligations, and Semantic Response Policy

## 1. Objective

Implement Stage 15 of the v3.5 core loop: generate and arbitrate **target-bearing semantic goals and obligations** from authorized meaning, unresolved frontiers, impact/importance, explicit policies, permissions, and dialogue state—without surface-intent labels or generic acknowledgement fallbacks.

Phase 15 decides **what semantic outcome should be pursued and why**. It does not yet decide wording; Phase 16+ builds response UOL and realization.

## 2. Governing laws

1. **Every selected goal has a target.** No targetless “acknowledge”, “answer”, or “help” action.
2. **Goals derive from semantic obligations/policy, not intent labels.** Surface classification can be evidence only.
3. **Policy is data.** Answer/act/learn/clarify/qualify/acknowledge/warn/support/silence are represented by schemas/rules, never a kernel switch over phrases.
4. **Authorization precedes utility.** A high score cannot authorize an action or disclosure.
5. **Unknown dependencies produce learn/clarify/preserve goals, not fabricated answers.**
6. **Literal/explicit policy overrides are first-class evidence.** They must be pinned, scoped, and permission checked.
7. **Conflict is explicit.** Competing obligations/goals retain reasons and arbitration traces.
8. **Repetition/social pressure are policy evidence, not hidden heuristics.**
9. **No generic targetless acknowledgement fallback.** Silence is a legitimate policy result when no authorized target-bearing goal exists.
10. **Response-policy knowledge is independently promoted.** Use `UseOperation.RESPONSE_POLICY`; do not piggyback on `PLAN` or `REALIZE`.

## 3. Inputs

Stage 15 may consume:

- selected/committed UOL meaning;
- unresolved learning/grounding frontiers;
- epistemic status/admission/knowledge records;
- current state/capability/transition products;
- Phase 14 impact/importance/significance;
- dialogue/discourse relations;
- explicit user/system constraints and permission policy;
- active response-policy schemas/rules promoted for `RESPONSE_POLICY`;
- available action/capability contracts.

It must not inspect raw text as authority once semantic interpretation exists.

## 4. Durable contracts

### 4.1 `SemanticObligationRecord`

Represents a reason that some semantic outcome should or should not be pursued.

Fields:

- `obligation_ref`, revision/supersession/status;
- obligation schema/policy ref + exact revision;
- target UOL refs (required for positive obligations);
- source proposition/event/frontier/impact/importance refs;
- stakeholder/context/time refs;
- required/prohibited operation/action schema refs;
- preconditions/constraints;
- permission/sensitivity;
- priority/risk evidence refs;
- proof/reason/provenance refs.

No obligation may exist solely as a string label such as `answer_question`.

### 4.2 `ResponsePolicyRuleRecord`

Generic semantic rule mapping structural conditions to obligation/goal templates.

Conditions may reference:

- discourse-act schemas;
- proposition/claim state;
- unresolved dependency/frontier state;
- impact/importance classes;
- capability availability;
- explicit literal policy;
- repetition/dialogue history;
- authorization/privacy predicates.

Outputs are schema/application templates with bound target ports.

Learned policy rules require Phase 13 response-policy competence and promotion.

### 4.3 `GoalCandidateRecord`

A proposed semantic objective.

Required:

- `goal_ref`, revision;
- goal schema/application ref;
- **non-empty target refs** unless the goal schema explicitly models a structurally targetless operation and passes a dedicated contract (default deny);
- obligation refs;
- policy-rule pins;
- stakeholder/context refs;
- prerequisite/frontier refs;
- authorization refs;
- impact/importance evidence refs;
- risk/cost/capability evidence refs;
- reason/proof refs;
- permission/sensitivity.

Candidate goals are not selected authority.

### 4.4 `GoalDecisionRecord`

Durable arbitration result.

Contains:

- exact candidate pins;
- selected goal refs;
- rejected/deferred goal refs;
- arbitration policy ref/revision;
- authorization decisions;
- conflict groups;
- reason/proof refs;
- snapshot/store fingerprint;
- revision/supersession.

### 4.5 `GoalConflictRecord`

Optional but recommended for explicit unresolved conflicts:

- competing goal refs;
- conflict relation/schema refs;
- affected targets/stakeholders;
- resolution policy refs;
- unresolved dependencies/frontiers.

## 5. Goal classes are data, not enums

The implementation plan names useful semantic outcomes:

- answer;
- act;
- learn;
- clarify;
- qualify;
- acknowledge;
- warn;
- support;
- silence.

These must be **boot/data schemas or learned schemas**, not a Python `GoalKind` enum that drives domain logic.

Kernel code knows only stable mechanics:

- goal candidate;
- target binding;
- obligation;
- authorization;
- conflict;
- selection/defer/reject;
- dependency/proof.

## 6. Components

### 6.1 `ObligationDeriver`

Applies active response-policy rules to semantic inputs.

Examples structurally, not lexically:

- a proposition request + known authorized proposition → answer obligation targeting proposition;
- unresolved required slot/frontier → learn/clarify obligation targeting missing contract;
- high-impact risk evidence → warning/support obligation targeting affected stakeholder/consequence;
- explicit action request + available authorized capability → act obligation targeting action application;
- explicit correction → qualification/correction obligation targeting prior claim/response content.

### 6.2 `GoalCandidateBuilder`

Converts obligations into fully bound semantic goal applications.

Hard gate: target binding must be structurally complete before selection.

### 6.3 `GoalAuthorizationGate`

Checks before scoring:

- permission/privacy;
- action capability;
- policy constraints;
- epistemic authorization;
- unresolved critical dependencies;
- safety/risk constraints represented by active policy data.

Unauthorized candidates remain rejected/deferred with reasons; they are not merely down-ranked.

### 6.4 `GoalConflictDetector`

Builds conflict groups using explicit structural relations:

- mutually exclusive actions;
- answer vs withhold;
- act vs clarify prerequisite;
- disclose vs privacy constraint;
- warn vs silence policy;
- competing stakeholder obligations.

No concept-name comparisons.

### 6.5 `GoalArbitrator`

Recommended generic order:

1. authorization/permission hard gates;
2. explicit prohibitions/mandatory obligations;
3. unresolved prerequisite constraints;
4. stakeholder impact/risk/irreversibility evidence;
5. explicit user/system policy evidence;
6. relevance/importance evidence;
7. repetition/dialogue-history policy;
8. resource/capability cost;
9. deterministic tie-break.

The ordering itself is policy configuration where possible. Kernel enforcement is limited to non-negotiable authorization and structural completeness.

### 6.6 `ResponsePolicyRegistry`

- exact revision lookup;
- `ACTIVE`-only executable authority;
- Phase 13 `RESPONSE_POLICY` promotion;
- candidate-safe supersession;
- deterministic structural indexes;
- restart rehydration/invalidation.

### 6.7 `GoalDecisionCoordinator`

Atomic CAS commit of:

- derived obligations;
- goal candidates;
- conflict records;
- final goal decision;
- dependency edges to all policy/impact/knowledge/frontier/capability inputs.

No selection may be committed from a stale snapshot.

## 7. Response-policy semantics

### Answer

Target: proposition/query variable/unknown slot.

Requires adequate authorized knowledge/evidence. Unknown answer creates learn/clarify/qualification obligation instead of fabricated content.

### Act

Target: exact action schema/application + affected referents.

Requires capability + permission + preconditions.

### Learn

Target: exact learning frontier/missing semantic contract.

Must not silently turn into an external question unless later planning selects a clarification response.

### Clarify

Target: unresolved semantic variable/frontier/ambiguity.

Question generation belongs downstream; Stage 15 only selects the semantic clarification target/reason.

### Qualify

Target: proposition/claim/answer content requiring uncertainty, attribution, scope, or correction.

### Acknowledge

Target: an explicit discourse contribution/state transition that merits acknowledgement.

A generic targetless “Okay” goal is forbidden.

### Warn / Support

Target: stakeholder + impact/risk/need assessment.

Must be grounded in Phase 14 proof-bearing significance or explicit policy.

### Silence

Represent as a policy decision with reason/authorization trace, not as absence caused by failure.

## 8. Literal/explicit policy overrides

Explicit user/system constraints should become durable/pinned semantic policy evidence where applicable.

Examples:

- requested format/scope;
- “do not act” / “only explain” constraints;
- privacy/disclosure constraints;
- correction/withdrawal of prior instruction.

Rules:

- scope by context/session/identity/permission;
- latest valid revision wins only through explicit supersession;
- conflicts stay explicit;
- text itself is not executed—its grounded policy meaning is.

## 9. Repetition and dialogue history

Repetition may affect goal selection only through structured history:

- already answered target/proposition;
- unresolved prior clarification;
- prior acknowledgement target;
- changed evidence/state since last response.

The engine must distinguish:

- exact repeated request with unchanged state;
- repeated request after correction/new evidence;
- reformulation of unresolved meaning;
- repeated social signal whose importance policy changes.

No regex/string similarity shortcut may directly select acknowledgement or refusal.

## 10. Invalidation/replanning

Goal decisions depend on exact revisions of:

- knowledge/admissions;
- frontiers;
- state/capability;
- impact/importance;
- response-policy rules;
- permissions;
- explicit policy;
- dialogue history.

Any correction/retraction/supersession must:

1. invalidate affected obligations/goals/decisions;
2. preserve historical decisions for audit;
3. emit recomputation frontier;
4. prevent stale response planning from Phase 16 onward.

## 11. Core-loop integration

```text
Stage 14 impact/importance
        ↓
Stage 15 derive obligations
        ↓
build target-bearing goal candidates
        ↓
authorization hard gate
        ↓
conflict detection/arbitration
        ↓
GoalDecisionRecord
        ↓
Stage 16 Response UOL planning
```

Phase 15 outputs semantic goals only. It must not choose words, templates, punctuation, or language-specific constructions.

## 12. Implementation sequence

### 15A — contract model

- obligation, policy-rule, goal-candidate, decision, conflict records;
- deterministic codecs/storage/repositories/indexes;
- target-bearing invariants.

### 15B — response-policy registry

- active-only authority;
- `RESPONSE_POLICY` use-axis integration;
- Phase 13 promotion/invalidation hooks.

### 15C — obligation derivation

- structural rule matcher;
- exact dependency/proof lineage;
- unknown/frontier handling.

### 15D — goal candidate builder

- bind target ports;
- reject incomplete/targetless candidates.

### 15E — authorization gate

- permission/privacy/capability/epistemic/policy constraints;
- fail closed.

### 15F — conflict detection

- explicit conflict graph;
- no score-only conflict erasure.

### 15G — arbitration

- policy-driven priority/evidence model;
- deterministic tie-breaking;
- explanation trace.

### 15H — atomic decision commit

- CAS snapshot;
- obligations+candidates+conflicts+decision in one transaction where required;
- exact dependency edges.

### 15I — invalidation/replanning

- Phase 13 invalidation integration;
- stale downstream response plan rejection.

### 15J — Stage 15 core-loop wiring

- shadow decisions first;
- compare against expected traces;
- authoritative cutover only after gates.

### 15K — acceptance/adversarial suite

### 15L — performance/query-plan proof

### 15M — documentation/manifest/cutover

## 13. Acceptance tests

At minimum:

1. known proposition request selects answer goal targeting exact proposition;
2. unknown required fact selects learn/clarify target, never fabricated answer;
3. action request without capability cannot select act goal;
4. action request with capability but no permission cannot select act goal;
5. explicit correction selects target-bearing qualification/correction obligation;
6. high-impact stakeholder risk can produce warning/support goal from Phase 14 evidence;
7. low/no authorized obligation can legitimately select silence;
8. acknowledgement requires explicit discourse target;
9. no generic targetless acknowledgement fallback exists;
10. repeated request with unchanged state follows repetition policy without string hacks;
11. repeated request after new evidence is re-evaluated;
12. conflicting obligations remain explicit and are arbitrated with trace;
13. private knowledge cannot become answer goal in unauthorized context;
14. candidate/provisional response policy cannot execute;
15. independently promoted response policy works only for `RESPONSE_POLICY` authorization;
16. policy correction invalidates old goal decision;
17. restart reconstructs same effective policy/decision dependencies;
18. malicious policy/schema names do not alter selection;
19. renaming fixtures/concepts leaves structural result invariant;
20. all selected goals expose target, reason, policy basis, and authorization trace.

## 14. Adversarial tests

- policy schema named `always_answer` without active authority must do nothing;
- candidate rule attempts to grant itself `RESPONSE_POLICY` via metadata → rejected;
- repeated examples attempt frequency promotion → rejected without Phase 13 competence;
- targetless acknowledgement candidate → commit rejection;
- high importance attempts to bypass privacy → authorization gate rejects;
- stale capability after goal snapshot → CAS/revalidation rejects act decision;
- conflicting literal policies → explicit conflict, no last-string-wins shortcut;
- LLM/inducer proposes a goal and self-certifies it → proposal remains non-authoritative;
- policy dependency cycle → bounded frontier, no recursive explosion.

## 15. Performance gates

Measure separately:

- policy candidate lookup by structural indexes;
- obligation derivation count;
- conflict graph size;
- arbitration latency;
- dependency-edge count per decision;
- restart rehydration cost.

Add explain/query-plan proof for hot lookups and preserve Phase 0 latency/memory budgets.

## 16. Exit criteria

Phase 15 is complete only when every selected response/action goal has:

- an explicit semantic target;
- a reason/obligation trace;
- an exact response-policy basis;
- authorization/permission trace;
- exact dependency lineage;
- deterministic conflict/arbitration result;
- invalidation/replanning behavior on upstream change.

No goal selection may depend on surface-intent labels, keyword switches, concept names, or a generic targetless acknowledgement fallback.
