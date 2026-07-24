# CEMM v3.5 Phase 14 — Impact, Importance, and Stakeholder Assessment

## 1. Objective

Implement Stage 14 of the v3.5 core loop: assess **who or what is affected, how, how strongly, and why it matters** without changing the truth of the underlying event/state, inventing consequences, or collapsing stakeholder-relative significance into a global label.

Phase 14 consumes only committed/authorized UOL, transition/state/capability products, active learned contracts, explicit context, and proof-bearing policy data.

## 2. Governing laws

1. **Impact is an assessment, not a fact rewrite.** An impact engine may derive an assessment about a committed event/state; it may not create or mutate the source event/state merely because the consequence seems plausible.
2. **Stakeholder-relative by construction.** Every impact/importance claim is bound to an explicit affected referent/stakeholder and context.
3. **Proof-bearing rules only.** No keyword, phrase, schema name, or hardcoded domain concept may create impact.
4. **Unknown stays unknown.** Missing stakeholder, consequence, magnitude, duration, or policy dependencies create typed frontiers rather than guessed values.
5. **Contradiction survives.** Competing positive/negative/unknown impact evidence remains attributable; no early scalar collapse.
6. **Importance is evidence-derived.** Goals, relations, history, affective state, risk, irreversibility, duration, and explicit policy may contribute only through typed evidence/rules.
7. **Privacy/permission is monotone.** Assessment output may not broaden the permission/sensitivity of its source lineage.
8. **No ontology growth in kernel code.** “Loss”, “harm”, “benefit”, “family”, “financial”, etc. are schema/data values, never branches.
9. **Learned impact/policy knowledge obeys Phase 13.** New impact rules or response-policy schemas are candidates until independently competent and promoted for `IMPACT`/`RESPONSE_POLICY` as appropriate.

## 3. Existing substrate to preserve

Phase 14 must build on, not replace:

- `ImpactAssessment` in canonical UOL;
- `ImportanceAssessment` in canonical UOL;
- committed `EventOccurrence`, `StateAssignment`, `StateDelta`, `CapabilityDelta`;
- transition proof/admission lineage from Phases 10–12;
- schema/facet/role/relation UOL;
- contexts and valid-time references;
- Phase 13 exact dependency/promotion/invalidation machinery.

The existing assessment classes are useful semantic payloads but need durable revision/provenance handling around them before runtime authority.

## 4. Durable contracts

### 4.1 `ImpactRuleRecord`

A generic data-driven rule describing when an impact assessment may be derived.

Required fields:

- `rule_ref`, `revision`, `supersedes_revision`, `lifecycle_status`;
- exact trigger schema/record family pins or structural matcher refs;
- affected/stakeholder binding specifications using generic UOL ports/roles;
- affected facet refs;
- consequence relation/schema refs;
- direction/valence/reversibility semantics as existing stable primitives or schema refs;
- magnitude/duration derivation refs, never hardcoded thresholds in engine code;
- context constraints;
- required evidence/proof classes;
- policy/permission/sensitivity refs;
- competence/evidence/provenance refs.

Rules are data. The executor dispatches only by stable record/operation structure.

### 4.2 `ImpactAssessmentRecord`

Durable wrapper for an `ImpactAssessment` payload.

Required lineage:

- exact source event/state/capability pins;
- exact impact-rule revision pins;
- exact affected/stakeholder resolution pins;
- context/time pins;
- proof/evidence refs;
- permission/sensitivity inheritance;
- revision/supersession/status;
- confidence/uncertainty provenance.

Do not rely on the current UOL object's implicit fallback revision for durable updates.

### 4.3 `ImportanceEvidenceRecord`

An attributable contribution to importance, not a final score.

Possible evidence sources are represented structurally:

- explicit goal relevance;
- stakeholder relation strength;
- prior interaction/history;
- affective-state relevance;
- risk/exposure;
- irreversibility;
- duration/persistence;
- explicit user/system policy;
- resource/capability consequences.

No source category is a keyword heuristic; each is a typed/pinned semantic relation or rule output.

### 4.4 `ImportanceAssessmentRecord`

Durable wrapper for stakeholder/context-relative significance.

Must retain:

- subject/stakeholder/context;
- contributing evidence refs;
- reasons as structured refs where possible;
- policy/rule pins;
- uncertainty/contradiction state;
- valid time;
- permission/sensitivity;
- revision/supersession/invalidation lineage.

A normalized score may exist as a projection for ranking, but it is never the sole semantic record.

### 4.5 `ImpactFrontierRecord` or Phase-13 learning frontier reuse

Prefer reusing `LearningFrontierRecord`/generic unresolved frontier mechanics where the missing item is a semantic contract. Add a narrow impact-specific frontier only when runtime consequence resolution needs fields that cannot be represented generically, such as competing stakeholder bindings or unresolved consequence chains.

## 5. Components

### 5.1 `StakeholderResolver`

Input: authorized UOL + relation/role/facet graph + context.

Output:

- exact stakeholder/affected bindings;
- proof refs;
- unresolved/ambiguous bindings as frontiers.

Rules:

- no surface-name routing;
- no assumed “self/family/owner” shortcuts;
- preserve multiple plausible stakeholders until a rule or context resolves them;
- permission-filter before returning candidates.

### 5.2 `ImpactRuleRegistry`

Revision-aware active-only registry analogous to schema/language authority.

Requirements:

- exact revision lookup;
- active-only effective authority;
- candidate-safe supersession;
- per-use Phase-13 promotion for learned rules;
- deterministic indexing by structural trigger fields.

### 5.3 `ImpactAssessmentEngine`

Pipeline:

```text
authorized source occurrence/state
→ applicable active impact rules
→ stakeholder/affected binding
→ rule condition evaluation
→ consequence proof
→ ImpactAssessmentRecord candidates
→ contradiction/duplication resolution
→ durable commit
```

The engine may only assess consequences explicitly licensed by an active rule and satisfied proof.

### 5.4 `ImportanceEvidenceCollector`

Collects independent evidence channels as typed records. It must not directly select response goals.

Adapters should consume stable semantic records, not domain names:

- goal relation adapter;
- stakeholder relation adapter;
- history adapter;
- affective-state adapter;
- risk/irreversibility adapter;
- explicit policy adapter.

Each adapter emits attributable evidence with exact dependencies.

### 5.5 `ImportanceArbitrator`

Combines evidence without erasing contradiction.

Outputs:

- importance class/schema ref;
- optional normalized ranking score;
- contributing/opposing evidence refs;
- uncertainty/frontier refs;
- reason/proof refs.

Ranking math may be generic; semantic weights/thresholds must be policy data.

### 5.6 `SignificanceProjection`

A deterministic materialized projection for downstream Stage 15 planning.

It may cache:

- top stakeholder-relative impacts;
- durable vs transient significance;
- unresolved high-impact frontiers;
- risk/irreversibility summaries.

It is a projection only and must invalidate on any dependency change.

## 6. Core-loop integration

Phase 14 runs **after authorized state/knowledge commit and transition computation**, before Stage 15 goal generation.

```text
Stage 13 commit authorized facts/state
        ↓
Stage 14 resolve stakeholders
        ↓
impact assessment
        ↓
importance evidence + arbitration
        ↓
durable impact/importance records + frontiers
        ↓
Stage 15 obligation/goal generation
```

No Phase 14 component may call the realization pipeline or select surface text.

## 7. Context/time semantics

- Every assessment carries `context_ref`.
- Hypothetical/planned events produce hypothetical/planned assessments, never actual-world effects.
- Historical impacts retain their valid-time interval.
- Duration and reversibility are evidence/rule outputs.
- Current importance may depend on historical impact, but the history is not rewritten.

## 8. Contradiction and uncertainty

Represent at least:

- competing stakeholder bindings;
- positive vs negative consequence evidence;
- magnitude disagreement;
- uncertain duration/reversibility;
- conflicting importance policies.

Do not average contradiction away before downstream policy sees it.

## 9. Invalidation/recomputation

Every durable assessment must depend on exact:

- source occurrence/state/capability revisions;
- rule revisions;
- stakeholder/relation bindings;
- policy/importance evidence revisions.

On correction/retraction/supersession:

1. Phase 13 invalidation finds affected impact/importance records;
2. stale assessments are tombstoned/superseded as appropriate;
3. recomputation frontiers are emitted;
4. Stage 15 goal decisions depending on stale significance are invalidated too.

## 10. Security/privacy

- permission scope is inherited fail-closed;
- sensitive stakeholder relations must not be exposed through importance explanations to unauthorized contexts;
- no high-importance score may override authorization/privacy;
- malicious schema names cannot increase importance;
- repeated mentions cannot manufacture significance without semantic/history policy evidence.

## 11. Implementation sequence

### 14A — contract audit and revision hardening

- audit current `ImpactAssessment`/`ImportanceAssessment` storage mapping;
- remove fallback-revision ambiguity for durable assessment updates;
- define wrapper records and codecs;
- add indexes and repository APIs.

### 14B — impact rule contract/registry

- implement `ImpactRuleRecord`;
- active-only registry;
- candidate-safe supersession;
- Phase-13 learned-rule promotion hooks.

### 14C — stakeholder resolver

- generic role/relation/facet traversal;
- ambiguity/frontier output;
- permission filtering.

### 14D — impact proof engine

- structural rule matching;
- exact condition/evidence pins;
- no source-fact mutation.

### 14E — durable impact commit

- atomic assessment + proof/dependency commit;
- idempotence/CAS;
- duplicate semantic assessment detection.

### 14F — importance evidence adapters

- goal/relation/history/affect/risk/irreversibility/policy adapters;
- typed evidence only.

### 14G — importance arbitration

- policy-driven ranking/classes;
- contradiction preservation;
- durable reasons/proofs.

### 14H — significance projection

- deterministic materialized projection;
- dependency fingerprints;
- no authority outside canonical records.

### 14I — invalidation/recompute wiring

- correction/retraction cascade;
- stale Stage 15 decisions invalidated transitively.

### 14J — core-loop Stage 14 wiring

- shadow mode first;
- compare expected vs prior behavior;
- authoritative cutover only after gates.

### 14K — acceptance/adversarial suite

### 14L — performance/query-plan proof

### 14M — documentation/manifest/cutover

## 12. Acceptance tests

At minimum:

1. one event affects two stakeholders differently;
2. one stakeholder has both positive and negative impacts preserved;
3. hypothetical event cannot create actual impact;
4. missing stakeholder creates frontier, not guessed referent;
5. unsupported consequence is not invented;
6. active impact rule works; candidate/provisional rule does not;
7. candidate impact-rule supersession does not shadow active rule;
8. correction of source event invalidates impact + importance;
9. relation/history change recomputes importance;
10. high score cannot override permission;
11. repeated mention alone does not increase importance;
12. malicious/renamed concept strings do not alter result;
13. restart reproduces identical assessments/projection fingerprints;
14. contradictory evidence remains attributable;
15. performance remains inside Phase 0 budgets.

## 13. Adversarial tests

- schema named `critical_emergency` with no active policy must gain no priority;
- 10,000 repeated mentions must not create semantic importance by frequency alone;
- hidden/private stakeholder relation must not leak into public reason trace;
- candidate rule crafted with `ACTIVE`-looking metadata but non-active lifecycle must not execute;
- circular consequence rules must hit bounded frontier/dependency limits;
- stale rule competence after dependency change must fail rehydration/promotion;
- source correction during assessment commit must CAS-fail atomically.

## 14. Exit criteria

Phase 14 is complete only when:

- impact and importance are stakeholder/context/time-relative and proof-bearing;
- assessments cannot create/rewrite source state facts;
- no name/keyword/domain branch participates in authority;
- active-only rule authority is enforced at registry and commit boundaries;
- correction/retraction invalidates dependent significance;
- Stage 15 can consume durable significance without re-deriving impact heuristically;
- all predecessor + Phase 13 + Phase 14 tests/verifiers pass.
