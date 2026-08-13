# CEMM Hybrid MVP R3 Cognition Activation Implementation Plan

> **Historical completion notice (2026-08-13):** R3 has been admitted; this
> plan's branch, head, gaps, and execution steps are historical snapshots.
> Status is derived only from
> [`governance/replay_status.jsonl`](../../../governance/replay_status.jsonl).

**Reviewed source:** `robosys-labs/cemm`
**Branch:** `codex/hybrid-mvp-r2`
**Reviewed head:** `68c8c04` (R2 green admission)
**Plan status at publication:** Proposed governing implementation plan
**Scope:** `hybrid_mvp/` only
**Predecessor:** R2 recursive semantic composition and exact verification
**Successors:** R5 neural proposal/realization activation and later evaluation/release phases

---

## 1. Executive determination

R2 admits ORIENT, PROPOSE, and VERIFY. When verification selects a meaning, the runtime finalizes with `evaluation=None`, `effect_receipt=None`, `response_meaning=None`, `realization_receipt=None` and emits the exact R3 gap:

```text
LaterOwnerNotAdmitted("contract:t3:evaluate")
```

R3 must activate the exact downstream semantic path:

```text
VerifiedMeaning + independently verified SituationContext
  → Decision
  → EffectReceipt or NoEffectReceipt
  → LearningPlan / DialogueObligation when applicable
  → ResponseMeaning
  → exact LaterOwnerNotAdmitted boundary for R5 surface realization
```

The active ABI registry reserves Situation Context ABI 1, Effect/No-Effect Receipt ABI 1, Learning Plan ABI 2, and Response Meaning ABI 2. R3 adds Decision ABI 1 as a new governed contract.

---

## 2. Mandatory phase boundaries

### R3 owns

1. structural mode and situation verification
2. expression-based query and bounded inference
3. epistemic placement and admission decisions
4. temporal-state evaluation
5. transition simulation
6. capability, permission, resource and adapter derivation
7. guarded semantic and external effects
8. typed learning-plan generation
9. persistent dialogue obligations and verified focus
10. deterministic Response Meaning ABI 2 construction
11. the canonical runtime path through the beginning of REALIZE
12. persisted activation canaries produced by real runtime cycles

### R3 does not activate

- natural-language generation; a neural realizer; neural proposal weights; model training
- authority publication from conversation; externally reviewed acquisition
- corpus partitioning; release evaluation

---

## 3. R3 task sequence (15 commits)

Each task follows: introduce/repair the exact failing test, run focused owner tier, implement earliest owner, run focused tests, contract review, code-quality review, phase tier when cross-owner boundary changes, commit one coherent task. No task may weaken a bound or convert a programming error into a semantic gap.

### R3-00 — Establish governance and immutable ABI allocation

**Files:** Create this plan; modify `docs/DOCUMENT_AUTHORITY.json`, `docs/ABI_REGISTRY.md`, `configs/validation_gates.json`, `scripts/validation_gate.py`; create `tests/test_r3_plan_contract.py`; modify `tests/test_replay_governance.py`.

**Requirements:** Add R3 plan to `governing_documents`. Add Decision ABI 1 (owner `decision.py`). Add Activation Canary Receipt ABI 1 if needed. Do not mutate existing ABI versions. Define R3 as depending on green R2. Keep gate steps within eight per tier; one pytest process per tier.

**Exit tests:** Unknown R3 ABI versions fail; removing R3 plan fails governance; second Decision owner fails; R3 cannot admit while R2 non-green; admission receipts reconstruct from exact refs.

**Commit:** `docs: freeze R3 cognition activation plan and ABI allocation`

---

### R3-01 — Hard-cut all legacy Program-as-meaning consumers

**Files:** Create `tests/test_r3_no_program_as_meaning.py`, `tests/test_r3_owner_structure.py`; modify/quarantine callers in `query.py`, `epistemics.py`, `state.py`, `effects.py`, `learning.py`, `response.py`, `dialogue.py`.

**Requirements:** AST-based inventory rejecting active R3 code that: accesses `program.graph` or `program.actions` after VERIFY; accepts `SemanticSwitchProgram` as EVALUATE input; reads `Orientation.source_text` after VERIFY; branches on raw words; calls `FormResolver`/`Grounder` after ORIENT; commits to `stores.world` outside effect owner; uses `program_ref` except for lineage; treats R2 `TransitionPreview` as effect authorization. Only valid EVALUATE input: `evaluate(meaning: VerifiedMeaning, situation: SituationContext) -> Decision`.

**Exit tests:** Program to EVALUATE raises `TypeError`; same VerifiedMeaning → same Decision regardless of derivation; no legacy proposition fixture imports; no `program.graph` in active R3 owners.

**Commit:** `refactor: hard-cut legacy program-as-meaning consumers for R3`

---

### R3-02 — Correct structural mode ownership

**Files:** Modify `runtime.py`, `cycle.py`, `proposal_context.py`, `forms.py`; create `tests/test_r3_mode_projection.py`.

**Requirements:** Implement bounded structural `ModeProjector` consuming Form Lattice hypotheses, closed-class contribution kinds, session obligations, reviewed construction contracts. No raw-text branching. Rules: interrogative → QUERY; operation/directive → REQUEST; hypothetical/counterfactual → SIMULATE; declarative without competing force → OBSERVE; competing equal modes → typed ambiguity; unsupported force → typed gap. No "default QUERY because question mark." Selected ModeSlot, Orientation mode, and SituationContext mode must agree exactly.

**Exit tests:** `HybridRuntime.process()` reaches correct mode: "Who likes Bob?" → QUERY; "Alice likes Bob." → OBSERVE; "Open the door." → REQUEST; "If the door opens..." → SIMULATE.

**Commit:** `feat: implement bounded structural mode projection`

---

### R3-03 — Implement Situation Context ABI 1

**Files:** Create `src/cemm_authoritative_hybrid/situation.py`, `schemas/situation_context.schema.json`, `tests/test_situation_context.py`, `tests/test_situation_context_security.py`; modify `bootstrap.py`, `runtime.py`, `__init__.py`.

**Requirements:** Frozen dataclass `SituationContext` binding: `abi_version`, `situation_ref`, `orientation_ref`, `proposal_context_ref`, `mode`, `session_ref`, `turn_ref`, `session_phase`, `participant_refs`, `speaker_ref`, `addressee_ref`, `actor_ref`, `temporal_frame_ref`, `interval`, `source_refs`, `epistemic_frame_ref`, focus/obligation/resource/permission/adapter snapshot and ref tuples, `provenance_refs`, `revision_pin`. Constraints: no source text, no Program ref, no expression ref, no mutable mappings, exact canonical round trip, bounded collections, content-addressed identity over every field, participant refs under pinned authority generation, snapshot refs bind exact store content, situation construction independent of Program derivation. Owners: `SituationContextBuilder` (reads Orientation + persisted snapshots), `SituationContextVerifier` (independent reconstruction), EVALUATE receives only verified context.

**Exit tests:** Round-trip preserves identity; tampering changes `situation_ref`; stale revision pins rejected; no Program or source text access.

**Commit:** `feat: implement Situation Context ABI 1`

---

### R3-04 — Implement a total Semantic Expression evaluator view

**Files:** Create `src/cemm_authoritative_hybrid/expression_projection.py`, `tests/test_expression_projection.py`, `tests/test_expression_projection_recursive.py`.

**Requirements:** One canonical read-only traversal of `SemanticExpression` for all R3 sub-owners. Indexes: roots, applications, roles, qualifiers, grounded/literal/variable/proposition fillers, scopes, ordered and commutative links, binder environments, predicate/operator indexes, participant/entity/state/event refs, proof/grounding lineage. Must not infer from ref prefixes; must use authority records; must not mutate; must reject dangling/noncanonical structures; must preserve root order only where semantically meaningful. Expose typed helpers: `state_assertions()`, `query_patterns()`, `claim_roots()`, `transition_intents()`, `reported_contents()`, `simulated_roots()` — derived from operator/roles/scopes/links/authority, not surface words.

**Exit tests:** Recursive nested expressions project correctly; dangling refs rejected; helpers return correct typed results per operator family.

**Commit:** `feat: implement canonical semantic expression projection`

---

### R3-05 — Implement Decision ABI 1 and the exact EVALUATE owner

**Files:** Create `src/cemm_authoritative_hybrid/decision.py`, `schemas/decision.schema.json`, `tests/test_decision_abi.py`, `tests/test_exact_decision_evaluator.py`.

**Requirements:** Content-addressed `Decision` binding: `abi_version`, `decision_ref`, `verified_meaning_ref`, `expression_ref`, `situation_ref`, `program_ref` (lineage only), `mode`, `status`, `action`, `answer_expression_ref`, `bindings`, claim/admission/query/transition ref tuples, `effect_intent_ref`, `learning_plan_ref`, `obligation_ref`, `proof_refs`, `source_refs`, `blocker_refs`, `policy_refs`, `revision_pin`. Statuses: supported, contradicted, conflict, unknown, partial, budget_exhausted, admitted, attributed, contested, denied, resource_unavailable, adapter_missing, simulation, pending, failed. Actions: answer, acknowledge, admit_claim, retain_attribution, preview_transition, request_effect, create_learning_obligation, request_clarification, no_op. `ExactDecisionEvaluator`: validates canonical identity and matching revision pins; traverses only semantic expression; dispatches by structure and closed mode; invokes pure sub-owners; combines receipts; creates one Decision; no mutation; no ResponseMeaning; programming exceptions propagate.

**Exit tests:** Identity content-addressed and stable; same expression+situation → same Decision regardless of derivation; programming exceptions propagate; all statuses/actions covered.

**Commit:** `feat: implement Decision ABI 1 and exact EVALUATE owner`

---

### R3-06 — Rewrite proof-bearing query and inference

**Files:** Rewrite `query.py`, `proof.py`; create `schemas/query_result.schema.json`, `schemas/proof_graph.schema.json`, `tests/test_r3_query_evaluation.py`, `tests/test_r3_recursive_inference.py`, `tests/test_r3_inference_bounds.py`, `tests/test_r3_query_conflict.py`.

**Requirements:** Query compilation from bound variables, application predicates, named roles, scopes, conjunction/disjunction, temporal constraints, epistemic placement, SituationContext. Bounded indexes for operator/predicate/role/argument/time/source/stance/epistemic placement. Proof nodes bind: `proof_node_ref`, conclusion, source_fact_refs, rule_ref, premise_node_refs, substitution bindings, revision pin. Graph validates: unique nodes, known premises, roots, reachability, acyclicity, exact lineage, bounds, transient witness isolation. Statuses: supported, contradicted, conflict, unknown, partial, budget_exhausted. Unknown never becomes false. Hard cut: remove `QueryEngine.observe(program)`, `GenericDefinitionLowerer.preview(programs)`, `set_form_pack(...)`, `describe_surface(...)`.

**Exit tests:** Recursive inference returns correct statuses; budget exhaustion yields typed frontier; proof graph validates; conflict returns all sources.

**Commit:** `feat: rewrite proof-bearing query and bounded inference`

---

### R3-07 — Rewrite epistemic placement and temporal state

**Files:** Rewrite `epistemics.py`, `state.py`; create `schemas/claim_occurrence.schema.json`, `schemas/admission_decision.schema.json`, `schemas/state_result.schema.json`, `tests/test_r3_epistemic_admission.py`, `tests/test_r3_temporal_state.py`, `tests/test_r3_state_conflict.py`.

**Requirements:** Canonical claim occurrence binds: expression root, source, evidence, interval, confidence, modality, scope, situation, revision, prior occurrence when correcting. Placement: reported/believed/desired/predicted/quoted → attributed; simulated → attributed/no commit; observed with reviewed evidence → eligible for admission; observed without sufficient evidence → contested; correction → supersedes prior while preserving both. State assertion: entity, dimension, value, interval, placement, source, proof, revision. Query index: unknown when absent, supported with coherent value, conflict with all sources, never overwrites conflict to appear resolved. Epistemics and state produce proposed deltas only — never commit.

**Exit tests:** Attributed placement → no world commit; correction preserves both; conflicting observations → conflict not resolved; unknown → unknown not false.

**Commit:** `feat: rewrite epistemic placement and temporal state evaluation`

---

### R3-08 — Rebuild transition and capability evaluation

**Files:** Modify `transition_preview.py`, `capabilities.py`, `authority.py`, `proposal_context.py`; create `tests/test_r3_transition_evaluation.py`, `tests/test_r3_capability_derivation.py`, `tests/test_r3_transition_authority.py`.

**Requirements:** R2 preview remains nonauthoritative lineage. R3 independently derives transition from: selected expression, authority transition record, event signature, current state, mode, SituationContext. REQUEST may create effect intent; SIMULATE may only preview; OBSERVE/QUERY may not execute. Sequence composition typed and left-to-right; no implicit inverse/overwrite/commutativity. Missing authority → typed gap, not guessed event. Capability derived under exact revisions from actor kind, event signature, transition, current state, capability, permission, resource, policy, adapter availability. Result content-addressed and proof-bearing. No `event_type_ref = ""` fallback.

**Exit tests:** REQUEST→intent, SIMULATE→preview, OBSERVE/QUERY→neither; missing authority→typed gap; capability denial proof-bearing; no empty event-type fallback.

**Commit:** `feat: rebuild transition and capability evaluation`

---

### R3-09 — Implement Learning Plan ABI 2 and persistent obligations

**Files:** Rewrite `learning.py`, `dialogue.py`; create `schemas/learning_plan.schema.json`, `schemas/dialogue_obligation.schema.json`, `tests/test_r3_learning_distinctions.py`, `tests/test_r3_learning_plan_abi2.py`, `tests/test_r3_learning_security.py`, `tests/test_r3_dialogue_obligations.py`.

**Requirements:** Learning Plan ABI 2 fields: `abi_version`, `plan_ref`, `contract_ref`, `verified_meaning_ref`, `expression_ref`, `situation_ref`, `decision_ref`, `source_query_ref`, `goal_ref`, `capability_ref`, `permission_ref`, `commit_operator_ref`, `surface_literal`, `target_ref`, `expected_target_kinds`, `answer_contract_ref`, `provenance_refs`, `revision_pin`, `expires_at_turn`, `obligation_ref`. Distinctions: lookup (read-only, no plan); teaching claim (attributed, no designation); learning directive (may create plan+obligation if verified, target exists, capability/permission represented, kinds known, no conflicting pending obligation — still no authority publication); learning-event claim (about speaker, not directive). Security: conversation cannot issue reviewer authorization; internal refs cannot become surfaces; one pending obligation max; expired/replayed plans fail; external review is separate authenticated workflow.

**Exit tests:** Four distinct outcomes for four learning types; expired/replayed plans fail; one pending obligation max; conversation cannot authorize publication.

**Commit:** `feat: implement Learning Plan ABI 2 and persistent obligations`

---

### R3-10 — Implement Effect / No-Effect Receipt ABI 1

**Files:** Rewrite `effects.py`; modify `persistence.py`; create `schemas/effect_receipt.schema.json`, `schemas/no_effect_receipt.schema.json`, `tests/test_r3_effect_gateway.py`, `tests/test_r3_no_effect_receipt.py`, `tests/test_r3_effect_recovery.py`, `tests/test_r3_effect_atomicity.py`.

**Requirements:** Effect plan binds: `effect_plan_ref`, `decision_ref`, `verified_meaning_ref`, `expression_ref`, `situation_ref`, `program_ref`, `actor_ref`, `event_type_ref`, `transition_ref`, `expected_revision_pin`, `capability_result_ref`, `requirement_proof_refs`, `idempotency_key`. EffectReceipt statuses: committed, denied, resource_unavailable, adapter_missing, pending, failed, stale_revision. NoEffectReceipt statuses: read_only, simulation, attributed_only, unknown, conflict, no_requested_effect, learning_obligation_only. Gateway: sole caller of world commits and external adapters; adapter never receives stores; decision authorization precedes journal; journal before invocation; retry uses idempotency key; timeout remains pending; failed observation never becomes success; world mutation and effect completion in one SQLite transaction; denied/no-effect persisted; receipt binds pre/post revision pins; observed fact admitted to world is guarded semantic effect even without external adapter.

**Exit tests:** Exactly one receipt per cycle; idempotent retry returns same receipt; denied/no-effect persisted; atomic transaction; stale revision rejected.

**Commit:** `feat: implement Effect/No-Effect Receipt ABI 1`

---

### R3-11 — Implement Response Meaning ABI 2

**Files:** Rewrite `response.py`; create `schemas/response_meaning.schema.json`, `tests/test_r3_response_meaning.py`, `tests/test_r3_response_security.py`.

**Requirements:** Canonical fields: `abi_version`, `response_meaning_ref`, `decision_ref`, `verified_meaning_ref`, `source_expression_ref`, `response_expression_ref`, `situation_ref`, `effect_outcome_ref`, `learning_plan_ref`, `obligation_ref`, `mode`, `cycle_status`, `discourse_action`, `bindings`, `polarity`, `modality`, `epistemic_status`, `source_refs`, `proof_refs`, `blocker_refs`, `policy_refs`, `permitted_omissions`, `revision_pin`. Rules: construct only from canonical Decision, effect/no-effect receipt, obligation; no source text inspection; no canned prose; no arbitrary focus-ref bindings; no Program actions; every material field participates in identity; response expression describes what a later realizer may say; unknown/conflict/denial/pending/failure remain distinct; no surface string generated in R3.

**Exit tests:** Identity content-addressed; distinct statuses produce distinct response meanings; no surface string; tampering changes identity.

**Commit:** `feat: implement Response Meaning ABI 2`

---

### R3-12 — Extend the canonical runtime

**Files:** Modify `runtime.py`, `cycle.py`, `bootstrap.py`, `__init__.py`.

**Requirements:** New protocols: `SituationOwner.build()`, `EvaluationOwner.evaluate(meaning, situation)`, `EffectOwner.execute(decision, meaning, situation)`, `ResponseOwner.build(decision, effect, ...)`. Runtime sequence after VERIFY selects: build/verify SituationContext → EVALUATE → Decision → EFFECT → Receipt → begin REALIZE → ResponseMeaning → stop at `contract:r5:realize_surface`. Phase receipts: EVALUATE (inputs meaning+situation refs, outputs decision+sub-owner refs); EFFECT (inputs decision+meaning+situation refs, outputs receipt ref); REALIZE at R3 (inputs decision+effect+obligation refs, outputs ResponseMeaning ref + R5 gap). Cycle remains `PARTIAL` with exact later-owner gap but carries complete R3 artifacts. Revision: ORIENT/PROPOSE/VERIFY pin unchanged; EVALUATE read-only; EFFECT may change world/effect revisions; obligation creation returns commit receipt; final CycleResult uses post-effect pin; phase receipts record input/output pins.

**Exit tests:** Path executes ORIENT→PROPOSE→VERIFY→EVALUATE→EFFECT→REALIZE(partial); cycle PARTIAL with R5 gap; receipts carry correct refs/pins; `HybridRuntime.process()` sole public path.

**Commit:** `feat: extend canonical runtime through EVALUATE, EFFECT and partial REALIZE`

---

### R3-13 — Implement crash-safe persistence and restart

**Files:** Modify `persistence.py`; create `tests/test_r3_sqlite_activation.py`, `tests/test_r3_restart.py`, `tests/test_r3_pending_effect_restart.py`, `tests/test_r3_obligation_restart.py`.

**Requirements:** Bump SQLite schema via explicit migration. Add strict effect-journal states: planned, authorized, invoked, observed, committed, denied, pending, failed. Persist Decision and ResponseMeaning in immutable cycle-artifact table or activation/episode records. Persist learning plans, obligations, and verified focus snapshots canonically. Validate every row hash at startup. Reconstruct pending effects without invoking adapters twice. Never reset corrupt database. Preserve exact parent revisions. One connection transaction for effect journal, world delta, and final receipt.

**Exit tests:** Pending effect survives restart; committed not duplicated; obligation survives; focus survives; same idempotency key returns same receipt; row hash validation detects corruption; corrupt database never silently reset.

**Commit:** `feat: implement crash-safe persistence and restart for R3`

---

### R3-14 — Replace synthetic cognition tests with public-runtime canaries and add R3 validation gates

**Files:** Create public-runtime canary tests using only `load_runtime(...)` and `runtime.process(session_ref, text)`; modify `configs/validation_gates.json`, `scripts/validation_gate.py`.

**Requirements:** Authentic canaries using only the public runtime:

- **Query:** "Who likes Bob?", "What is CEMM?", "What is the door state?" — supported, unknown, bound-variable cases.
- **Conflict:** two sensor observations for same interval → conflict plus both sources.
- **Epistemic:** "Ada said the door is open.", "I believe the door is open.", "Imagine the door is open." — attributed, no world commit.
- **Observation:** "The door is open." — admission Decision and semantic world-effect receipt.
- **Simulation:** "If the door opens, will it be open?" — transition preview and NoEffectReceipt(simulation).
- **Request:** "Open the door." — denied, resource unavailable, adapter missing, pending timeout, failed observation, committed, identical retry.
- **Learning:** "What does cheerful mean?", "Cheerful means happy.", "Learn that cheerful means happy.", "I learned cheerful." — four distinct outcomes.
- **Restart:** pending effect survives; committed not duplicated; obligation survives; focus survives; same idempotency key returns same receipt.
- **Programming failures:** injected exceptions propagate, not become semantic gaps.

R3 phase tier proves: real Orientation → ProposalContext → proposal → VerificationBatch → VerifiedMeaning → SituationContext → Decision → Effect/NoEffect → ResponseMeaning → exact R5 gap.

R3 structural gate AST checks reject: downstream `program.graph`, downstream `SemanticSwitchProgram` parameters, raw-text dispatch after VERIFY, direct world commits outside effect/persistence owners, adapter store access, duplicate Decision/EffectReceipt owners, RuntimeConfig compatibility branches, skip/xfail markers, fixture-only activation tests.

**Exit tests:** All eight canary categories pass; R3 owner tiers pass (8 groups); R3 phase tier passes; R3 structural gate passes; R3 admission gate passes; zero failures/errors/skips/xfails/xpasses.

**Commit:** `test: replace synthetic cognition tests with public-runtime canaries and add R3 gates`

---

## 4. R3 definition of done

R3 is complete only when:

1. R2 is reconstructably green.
2. Situation Context ABI 1 is implemented and canonical.
3. Decision ABI 1 is governed and canonical.
4. Learning Plan ABI 2 is implemented.
5. Effect/No-Effect Receipt ABI 1 is implemented.
6. Response Meaning ABI 2 is implemented.
7. All EVALUATE owners consume expression and situation, never program.
8. No active R3 code accesses `program.graph` or `program.actions` after VERIFY.
9. The canonical runtime path executes ORIENT→PROPOSE→VERIFY→EVALUATE→EFFECT→REALIZE(partial).
10. Persistence is crash-safe and restartable.
11. Public-runtime canaries pass for query, conflict, epistemic, observation, simulation, request, learning, and restart.
12. R3 owner tiers pass.
13. R3 phase tier passes.
14. R3 admission passes.
15. Zero active failures, errors, skips, xfails or xpasses exist.

The exact post-R3 boundary is:

```text
ResponseMeaning → LaterOwnerNotAdmitted("contract:r5:realize_surface")
```

---

## 5. Proposed owner groups (8 max)

1. `situation-context`
2. `decision-query-proof`
3. `epistemic-state`
4. `capability-effect`
5. `learning-dialogue`
6. `response-contract`
7. `persistence-recovery`
8. `runtime-activation`

---

## 6. R3 admission gate

```text
governance
→ source_compile
→ authority_link
→ pytest_active
→ r3_structure
→ sqlite_activation
→ r3_activation_canaries
```

The activation step must execute real cycles against a temporary persistent SQLite database and return content-bound refs for: cycle, VerifiedMeaning, situation, Decision, effect/no-effect, ResponseMeaning, gap, final RevisionPin, and persisted canary row. No hand-authored output ref may be accepted as activation evidence.
