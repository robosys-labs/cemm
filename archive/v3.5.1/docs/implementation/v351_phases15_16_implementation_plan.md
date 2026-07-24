# CEMM v3.5.1 — Phases 15–16 exhaustive implementation plan

Baseline: `d20377430213b83ba6c4f104b989ea991cb73def` (post-Phases 13–14).

## Governing contract

Priority: `AGENTS.md` → `ARCHITECTURE.md` → `CORE_LOOP.md` → `RUNTIME_PLAN.md` → `CEMM_CORE_MATHS.md` → `IMPLEMENTATION_PLAN.md` → `CORE_ISSUES.md` → `ISSUES_TO_AVOID.md`.

The implementation treats Phases 15 and 16 as one semantic-mechanics program. State, transition, causality, prediction, explanation, impact, goal arbitration, planning, causal question answering and causal learning must share the same exact authority, typed values and proof DAG. No subsystem may infer a second private notion of “cause”.

## 1. Close mathematical/document gaps first

Add normative contracts for:

1. one typed runtime state-value algebra covering categorical, ordered, continuous, vector/manifold, relational, set, process and probabilistic domains;
2. exact unit/frame/manifold/value/relation/element/process authority and typed probability support values;
3. typed partial state-transform functions rather than event-name mutation callbacks;
4. exact mechanism roles, preconditions, defeaters, stochastic branches, secondary events, aggregation, independence and explicit per-use TRANSITION authority;
5. observation vs intervention semantics (`condition` vs `do` edge cutting);
6. counterfactual abduction → intervention → prediction with explicit exogenous assumptions;
7. absolute branch probability and unresolved mass under pruning/budget exhaustion;
8. one causal proof DAG reused by QA, prediction, impact, planning and learning;
9. causal structure learning that requires intervention/mechanism evidence and never promotes co-occurrence;
10. simulation/commit separation for actual, hypothetical, intervention, counterfactual and planning contexts.

## 2. Phase 15 — full state algebra

### 2.1 StateDomainContractV351
Compile each exact `StateDimensionSchema` revision into one typed runtime domain contract. Legacy categorical/ordered/scalar fields remain readable, while rich domains use exact fingerprinted schema metadata.

### 2.2 StateValueV351
Represent runtime values as content-addressed occurrences, not ontology records. Probabilistic values distribute mass over typed `StateValueV351` support occurrences validated by the underlying exact support domain. Persist rich values through `StateAssignment.value_document`; retain legacy `value_ref/value_revision` for categorical compatibility.

### 2.3 StateAlgebraV351
Implement typed operators:
- categorical assign/clear;
- exact ordered shift;
- scalar add/scale/affine/clamp;
- vector add/scale/affine;
- manifold map only through exact external evaluator authority;
- relation add/remove;
- set add/remove/union/difference with optional exact member type validation;
- process start/stop/advance;
- distribution replace/mix.

Any incompatible operation is undefined/fails closed. No coercion by English labels or event names.

### 2.4 Role-addressed transitions
Implement exact `ParticipantRoleBinding`, `MechanismPrecondition`, `MechanismDefeater`, `RoleStateTransformV351`, `SecondaryEventTemplateV351`, `TransitionMechanismV351`, `TransitionPreviewProof`, and `TransitionDistribution`. Lifecycle alone never authorizes use: executable transition authority requires explicit TRANSITION use grant plus competence.

Surface subject/object/voice must not enter transition semantics. Active/passive derivations that resolve to the same semantic roles produce the same consequences.

### 2.5 Capability dependencies
Implement a bounded tri-valued `CapabilityDependencyGraphV351` over exact state/capability/resource/adapter/permission/competence facts. Capability evidence remains separate from action authorization.

## 3. Phase 16 — structural causality

### 3.1 SCM contracts
Implement `CausalVariable`, `CausalMechanismGraph`, exact mechanism edges, lag semantics, instantaneous-cycle solver authority, intervention and counterfactual contexts.

### 3.2 Bounded causal propagation
One engine processes:
- direct state deltas;
- state-change-triggered mechanisms;
- secondary events;
- threshold/precondition triggers;
- stochastic branches;
- intervention cuts;
- bounded recursion/cycle detection;
- proof-step and event/delta/branch budgets.

Derived state changes are reified as causal queue events so secondary mechanisms pass through exactly the same branching, proof and budget logic.

### 3.3 Probability and mechanism conflict law
Do not renormalize surviving branches to certainty. Joint stochastic composition requires exact independence authority. Competing writes to the same variable/time require an exact aggregation contract and evaluator; otherwise preserve a frontier.

### 3.4 Explanation and causal QA
Extract the least warranted reverse proof subgraph for why/cause-of and a bounded forward subgraph for effect-of. Stage 10 creates causal-query work only from exact answer-projection authority plus an already grounded causal target—not from tokens such as “why”. Add a distinct `PROVIDE_CAUSAL_EXPLANATION` response family with exact cause/effect semantic ports. Language realization may render these ports, but may not invent a causal link.

### 3.5 Causal learning/research
Turn causal proof steps into structured learning evidence. Score explicit candidate mechanisms using lineage-discounted likelihood evidence and complexity penalties. Require intervention/mechanism evidence before generating a Phase-14 causal candidate signal. Candidate scoring never bypasses exact dependencies, competence, review, promotion or authority-generation restart.

### 3.6 Impact, goals and planning
Derive `ImpactVector` from causal deltas while keeping physical state, affective consequence, reported emotion and response stance separate. Goal utility is vector/policy based. Planning evaluates action candidates by causal simulation in isolated planning contexts. A selected plan remains semantic eligibility only; existing operation adapter/gate/journal/effect authorization remains mandatory before I/O.

## 4. Runtime integration

- Stage 10: ordinary grounded query + exact causal-query projection.
- Stage 12: causal simulator is preview-only.
- Stage 13: existing session/learning commit then actual deterministic causal state commit; no simulated branch is world truth.
- Stage 14: impact/capability propagation from the same proof-bearing deltas.
- Stage 15: composite conversational + causal goal arbitration.
- Stage 16: causal planning before existing effect gates.
- Stage 18: causal-explanation Response CSIR when warranted.
- Stage 19: exact language projection for cause/effect ports.

## 5. Corrective fixes included

- remove canonical capability decoder import of legacy UOL enum;
- repair Phase-14 Stage-13 illegal `effect_store.base_store` access;
- make transition storage codec/repository accept canonical Phase-15 mechanisms while preserving old decode compatibility;
- persist typed rich state values;
- prevent branch-pruning renormalization;
- preserve state-trigger stochastic branch structure;
- isolate non-actual contexts before causal simulation;
- make counterfactual exogenous assumptions typed and operational;
- fail closed on unresolved transform operands/evaluators;
- fix causal proof source-event vs source-variable lineage separation;
- require exact stochastic independence and aggregation authority.

## 6. Verification matrix

Focused tests must prove:

1. all eight state domains;
2. exact ordered shift and manifold fail-closed behavior;
3. active/passive semantic-role equivalence;
4. direct + cross-dimensional secondary causal propagation;
5. intervention edge cutting and factual-state isolation;
6. counterfactual unresolved abduction and explicit exogenous restoration;
7. branch probability remains absolute under pruning;
8. same causal proof drives explanation and learning evidence;
9. association-only causal research cannot create promotable candidate work;
10. causal-query dispatch is exact semantic projection, not wording;
11. active mechanism without explicit TRANSITION use remains non-executable;
12. durable actual-state commit persists exact causal proof DAG plus exact mechanism dependencies;
13. effect-of traverses causal proof forward and what-if selects the exact matching intervention simulation;
14. non-actual impact cannot become actual goal pressure;
15. planning requires capability + explicit planning authorization + utility evaluator;
16. no operation is executed by planner alone;
17. full `tests/v350` regression suite and architecture scans after application.

## 7. Activation honesty

The source patch implements the mechanics. Existing signed boot/release artifacts containing old transition contracts remain valid only as legacy-compatible records; new Phase-15/16 exact mechanism/state-domain/query-projection authority must be generated, competence-tested and published through the canonical release pipeline. Do not hand-edit manifest hashes or mark causal authority active merely because the runtime classes exist.

## 8. Final completion gates used

The implementation was not frozen until all of the following were represented as code-level invariants or explicit frontiers:

- exact typed state identity and durable rich-value content verification;
- exact semantic role binding for relations, transitions, secondary events and impact participants;
- lifecycle/competence/use separation for mechanisms and capability graphs;
- independent Stage-13 per-use reauthorization before world mutation;
- generation-pinned Stage-0 projection of already-promoted operational authority;
- structural intervention edge cuts plus downstream propagation of imposed state;
- typed exogenous assumptions and underidentified counterfactual fail-partial behavior;
- absolute branch probability plus unresolved-mass conservation under all bounded exits;
- explicit aggregation/independence authority for competing/stochastic mechanisms;
- branch-to-proof identity and resolved-only definitive causal answers;
- directional cause/effect traversal and factual-vs-contrast `why_not` semantics;
- durable proof DAG persistence for committed actual consequences;
- final-current-state materialization distinct from intermediate causal history;
- capability recomputation from typed state with tri-valued support;
- probability/context-aware impact and goal formation;
- exact action PLAN + utility-policy authorization with zero implicit external effect authority;
- no legacy UOL/v347 imports or language-word semantic branches in the new state/causal kernel.
