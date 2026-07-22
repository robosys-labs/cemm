# CEMM v3.5.1 — Phases 15–16 implementation report

## Baseline

Exact baseline: `d20377430213b83ba6c4f104b989ea991cb73def`, the applied Phases 13–14 commit.

## Executive result

This bundle replaces the old categorical/event-effect transition seam with a typed state algebra and a structural causal substrate. The same exact role-addressed mechanisms and causal proof DAG are now designed to support:

- state interpretation and transition prediction;
- recursive causal propagation and secondary events;
- intervention and counterfactual simulation;
- causal explanation/question answering;
- impact and goal evaluation;
- causal planning;
- causal learning/research through the existing Phase-14 candidate/promotion pipeline.

No event-name mutator table, English causal phrase handler, subject/object semantic shortcut, or concept-specific causal branch is introduced.

## Major architectural defects found

### P15-16-01 — Old transition layer was categorical-only and imported legacy UOL mechanics
The pre-existing `transitions/model.py` still used legacy `StateDelta`, `CapabilityDelta`, `ChangeOperation` and categorical target values. It could not represent the eight Phase-15 state families mathematically.

**Fix:** new canonical `cemm/v350/state/*_v351.py` typed value/domain/transition substrate. Old records remain decode-compatible but are not the new causal runtime brain.

### P15-16-02 — Durable state could not represent measured/vector/set/process/distribution values
`StateAssignment` only had schema-backed `value_ref/value_revision`.

**Fix:** add `value_document` for content-addressed typed occurrence values while retaining categorical compatibility.

### P15-16-03 — Increase/decrease could collapse into preselected target values
This is not a mathematical transition.

**Fix:** exact ordered shift and typed numeric/vector transforms. Manifold transforms require exact operator/evaluator authority.

### P15-16-04 — State-trigger causal propagation risked collapsing stochastic branches
Applying secondary mechanisms inline would lose branch probability/proof lineage.

**Fix:** every derived state change is reified as a causal queue event and passes through the same bounded branching/cycle/intervention/proof engine.

### P15-16-05 — Counterfactual exogenous assumptions were opaque and not applied
A string assumption cannot implement abduction-action-prediction.

**Fix:** typed `ExogenousAssumptionV351(variable, value, support, evidence)` is restored in the isolated counterfactual state before `do(...)` replacement/prediction. Underidentified abduction yields a frontier.

### P15-16-06 — Non-actual root events were not context-isolated
Planning/intervention could otherwise read/write mismatched actual-context keys.

**Fix:** clone the input state and root event context before simulation for hypothetical/intervention/counterfactual/planning semantics.

### P15-16-07 — Branch pruning could silently preserve the pre-branch state and imply probability 1
A fallback `next_comb or combinations` could manufacture certainty after every branch was pruned.

**Fix:** removed fallback, preserve absolute branch probabilities, expose unresolved probability mass, and emit pruning frontiers.

### P15-16-08 — Simultaneous mechanisms could overwrite the same state by evaluation order
Mechanism order is not a causal aggregation law.

**Fix:** competing writes require one exact aggregation contract and evaluator. Without it, fail closed. Stochastic products likewise require exact independence authority.

### P15-16-09 — Causal proof lineage mixed event participation with state-variable causes
Participant identity is not itself a state change.

**Fix:** proof steps separately record `source_event_refs` and state variables actually read by preconditions/role-state operands/source deltas.

### P15-16-10 — Causal learning could become a separate heuristic brain

**Fix:** simulation proof steps become `CausalLearningEvidenceV351`; explicit hypotheses are scored with lineage clustering, intervention support and complexity penalty; accepted hypotheses become ordinary Phase-14 `ExactStructuralCandidateSignal` values with exact dependencies/competence/requested uses. Promotion remains Phase 14’s only authority crossing.

### P15-16-11 — Stage-13 Phase-14 committer accessed hidden `AuthorizedEffectStore.base_store`

**Fix:** use the exposed read-only store view/read generation.

### P15-16-12 — Canonical capability decoder still imported a legacy UOL enum

**Fix:** resolve canonical `CapabilityStatus` from storage model.


### P15-16-13 — Active lifecycle could imply causal execution without explicit per-use TRANSITION authority
Lifecycle, competence and use authority are distinct. An active mechanism was initially executable with competence alone.

**Fix:** `TransitionMechanismV351` declares `use_operation=TRANSITION`, carries promotion-written `authorized_use_operations`, and becomes executable only when lifecycle is active, competence exists, and explicit TRANSITION use authority is present. Phase-14 promotion remains the authority crossing.

### P15-16-14 — Probabilistic state support was too weakly typed
A probability distribution over opaque support keys cannot preserve whether its support is categorical, scalar, relational, process-valued, etc.

**Fix:** probability mass is defined over typed `StateValueV351` support occurrences. Every support value is validated against the exact underlying domain contract before the distribution is accepted.

### P15-16-15 — Actual state commits could retain only opaque causal proof refs
Persisting a new state assignment with a proof string but without the proof DAG weakens replay, invalidation, explanation and future causal learning.

**Fix:** every committed deterministic actual consequence persists its exact `CausalProofV351` under the existing transition-proof record family, with durable dependencies on every exact mechanism used. The new assignment depends on that durable proof and exact mechanism authority.

### P15-16-16 — Causal query direction/context could be semantically wrong
Treating `effect_of` as reverse explanation returns causes rather than effects, while selecting an arbitrary simulation can answer a `what-if` from the factual branch.

**Fix:** `why/cause_of` traverse the proof DAG backward; `effect_of` traverses forward and fails closed when the terminal effect projection is ambiguous. Exact query projection may carry source, target, contrast and intervention-context identities, and runtime selects the matching factual/interventional/counterfactual simulation.

### P15-16-17 — Non-actual impact could leak into actual goal pressure
Hypothetical, interventional, counterfactual and planning deltas are useful for evaluation but are not actual obligations.

**Fix:** impact vectors retain `ContextSemantics`; Stage 14 separates actual impact from simulated impact, and automatic goal generation accepts only ACTUAL-context impact. Planning utility may still consume isolated simulation results explicitly.

## Phase 15 implementation

### State domain/value algebra
Implemented all required families:
- categorical;
- ordered;
- continuous;
- vector/manifold;
- relational;
- set-valued;
- process-valued;
- probabilistic.

Every runtime state value is a typed occurrence with deterministic identity. Exact authority can constrain units, frames, manifold, value order, relations, element types, processes and probability support semantics. Probabilistic state is a distribution over typed state-value support occurrences, never opaque outcome labels.

### Role-sensitive transition calculus
`TransitionMechanismV351` contains exact and per-use governed:
- trigger authority;
- semantic participant-role pins;
- type requirements;
- source state dimensions;
- preconditions and defeaters;
- state transforms;
- secondary events;
- stochastic branches;
- parameter/competence pins;
- explicit TRANSITION use authority distinct from lifecycle;
- context scope;
- aggregation/independence authority.

`TransitionPreviewEngineV351` never performs durable writes.

### Capability dependencies
A bounded tri-valued dependency graph separates capability evidence from operation authorization and supports ALL/ANY/NOT/state/capability/resource/adapter/permission/competence requirements.

## Phase 16 implementation

### Structural causal model
Implemented causal variables/graphs, lagged edges, solver-gated zero-lag cycles, intervention contexts, typed exogenous assumptions and isolated counterfactual contexts.

### Bounded causal engine
One engine handles actual prediction, intervention, counterfactual and planning contexts. It supports direct deltas, state-trigger mechanisms, secondary events, stochastic branches, intervention cuts, cycle/depth/event/delta/branch/proof budgets and proof DAG generation.

### Causal explanation and QA
`ExplanationExtractor` computes a minimal warranted reverse proof subgraph for why/cause-of and a bounded forward proof traversal for effect-of. `Phase16QueryEngineV351` creates causal requests only from exact query-projection authority and a grounded causal target. `PROVIDE_CAUSAL_EXPLANATION` adds exact cause/effect response ports. English realization is only a content-addressed projection of those ports.

`why_not` requires an explicit contrast and counterfactual/interventional substrate. `what_if` requires an explicit intervention and matching interventional simulation.

### Impact, goals, planning
Impact vectors keep physical/affective/reported-emotion/response-stance channels distinct and retain context semantics. Only ACTUAL impact may automatically become goal pressure; non-actual impact remains explicit simulation/evaluation evidence. Goal arbitration is vector/policy based. Causal planning simulates authorized action candidates in isolated planning contexts; it does not create operation authorization.

### Causal research/learning
The same causal proof graph is transformed into structured learning evidence. Causal structure research discounts shared lineage, applies complexity penalty, requires intervention/mechanism evidence, and emits exact Phase-14 candidate work only when thresholds are met.

## Deliberate fail-closed boundaries

- exact aggregation contract without evaluator remains a frontier;
- manifold transform without evaluator remains a frontier;
- typed set domain without exact member-type resolver remains a frontier;
- counterfactual with underidentified exogenous state remains a frontier;
- event-port transform without exact bound port value remains a frontier;
- causal question lacking exact projection/grounded target remains ordinary/partial cognition;
- planner without exact utility evaluator cannot select an executable plan;
- no plan bypasses operation adapter/gate/journal/effect authorization;
- new causal/state authority still requires canonical competence/release activation;
- exact causal projection lowerers must supply grounded source/target/contrast/intervention identities;
- rich ordered domains require exact reviewed value pins for generic ordered shift.

## Verification status

The bundle is `IMPLEMENTED_UNVERIFIED_FULL_CHECKOUT`:
- local Python AST/compile validation is performed on bundle source/tests/tools;
- exact baseline lock is encoded in the apply script;
- focused semantic tests and architecture verifier are included;
- full repository pytest, canonical boot rebuild, signed release regeneration, performance/concurrency tests and live end-to-end causal dialogue must run after applying to a full checkout.

## Final deep end-to-end audit and freeze

The final review treated Phase 15 and Phase 16 as one semantic mechanics boundary rather than two feature layers. The following invariants are now release gates in code/tests/verifiers:

1. **State is typed before it is causal.** Every causal transform is defined over an exact state-domain contract; unit, frame, manifold, relation-role, element/process and probability-support constraints fail closed before a mechanism can produce a delta.
2. **Mechanism identity is semantic, operational permission is separate.** Context scopes, permission, lifecycle, competence and per-use grants do not mutate causal mechanism identity. Runtime execution requires an active/competent record *and* exact `TRANSITION` ALLOW authority for the current world/context.
3. **Stage 13 reauthorizes independently.** Durable actual-world state mutation revalidates every proof mechanism against the cycle-pinned `AuthoritySnapshotV351`; a forged/injected Stage-12 simulation cannot turn ACTIVE lifecycle into persistence authority.
4. **Actual-world context is exact.** An `ACTUAL` result is commit-eligible only when its simulation context and each committed delta context equal the cycle context, with one fully resolved probability-1 branch, zero unresolved mass and no branch frontier.
5. **Interventions replace structural equations.** Incoming edges to an intervened structural variable remain cut across time steps; the imposed state change itself becomes a causal root so downstream effects still propagate.
6. **Partial causality remains numerically partial.** Pruned, low-confidence, cycle-blocked, depth/time-budgeted, unresolved-precondition or unresolved-conflict paths contribute explicit unresolved probability mass. Surviving branches are never renormalized to false certainty.
7. **Current state is not causal history.** All intermediate deltas remain in the proof DAG, but Stage 13 materializes only the final value per exact current-state variable. A final CLEAR invalidates the prior assignment without creating a fictitious replacement.
8. **The proof DAG is shared.** Query/explanation, impact, recursive causal research, planning and durable commit all consume the same exact proof-step identities. Branches explicitly identify their proof; unresolved branches cannot supply definitive answers.
9. **Capability is derived, not hand-maintained.** Exact capability dependency graphs consume the same typed state substrate after actual state commit and preserve tri-valued unknown/false/true support without inventing certainty.
10. **Impact and goals preserve probability/context.** Physical/affective/report/stance channels remain distinct; branch probability and epistemic confidence are separate; nonactual or unresolved branches do not automatically become ordinary obligations.
11. **Planning is not execution.** Exact action `PLAN` use and exact utility-policy use are required before simulation/selection. Selected plans still return zero authorized operations unless the existing external operation adapter/gate/journal/effect boundary independently authorizes an effect.
12. **Promoted operational authority is generation-pinned.** Stage 0 deterministically projects only highest active, non-invalidated, explicitly per-use-authorized rich transition/capability records from the already-pinned store generation. It aborts if authority changes during projection.

### Final verification performed in the delivery environment

Executed successfully on the final source tree:

- `python -m compileall -q cemm tests tools apply_phases15_16.py`
- `python tools/verify_v351_phases15_16.py`
- `python tools/run_isolated_v351_phases15_16_checks.py`

The static verifier covers the core architecture laws and the isolated behavioral verifier executes the real Phase-15/16 state/transition/causal modules with minimal baseline stubs to prove core algebra, role-addressed transitions, defeater behavior, probability accounting, context isolation, mechanism identity separation and proof/partial-query invariants.

The environment did not contain a full Git checkout of the baseline repository and direct clone/archive retrieval was unavailable, so the complete `tests/v350` suite could not honestly be executed here. The bundle therefore ships focused full-checkout tests plus a baseline-locked apply script. Full-checkout pytest, boot/release regeneration and live end-to-end dialogue remain mandatory activation gates, not hidden implementation TODOs.
