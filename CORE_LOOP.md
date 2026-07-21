# CEMM v3.5.1 Grounded Semantic Brain Core Loop

**Status:** proposed Stage-0..22 governing runtime contract  
**Core law:** every stage operates over the same pinned semantic brain state; perception, meaning, state, causality, learning and response are recurrent transformations, not disconnected pipelines.

---

# 1. Macro topology

```text
0  ORIENT_AND_PIN_SEMANTIC_BRAIN
1  OBSERVE_MULTIMODAL_EVIDENCE
2  ENCODE_FORM_AND_SENSOR_EVIDENCE
3  ACTIVATE_AND_GROUND_REFERENTS
4  PROJECT_ENTITLED_STATE_SPACES
5  COMPILE_CANDIDATES_TO_CSIR
6  RUN_RECURRENT_MEANING_DYNAMICS
7  STABILIZE_SEMANTIC_ATTRACTORS
8  BUILD_DISCOURSE_PROPOSITION_EVENT_AND_QUERY STRUCTURES
9  PLACE_EPISTEMIC_CONTEXT_AND_ASSIMILATE_WORLD_BELIEF
10 QUERY_AND_EXPLAIN_FROM_GROUNDED_WORLD_MODEL
11 CLASSIFY_PREDICTION_ERROR_AND_ADVANCE_LEARNING
12 SIMULATE_CAUSAL_TRANSITIONS_AND_COUNTERFACTUALS
13 COMMIT_AUTHORIZED_KNOWLEDGE_STATE_AND_LEARNING ARTIFACTS
14 PROPAGATE_CAPABILITY_IMPACT_AFFECT_AND_SIGNIFICANCE
15 DERIVE_OBLIGATIONS_AND_ARBITRATE_GOALS
16 PLAN_AUTHORIZE_EXECUTE_AND_OBSERVE
17 ASSIMILATE_OPERATION_OUTCOMES_AND_RECUR
18 CONSTRUCT_RESPONSE_CSIR
19 REALIZE_TARGET_LANGUAGE_OR_MODALITY
20 VERIFY_SEMANTIC_EQUIVALENCE_AND_AUTHORIZE_EMISSION
21 COMMIT_OUTPUT_DISCOURSE_AND_COMMON_GROUND
22 CONSOLIDATE_INVALIDATE_REPLAY_AND_FINALIZE
```

The public stage count remains stable, but Stages 3–7 and 11–17 contain bounded recurrent subloops.

---

# 2. Cross-stage brain state

Every stage receives an immutable view of:

```text
exact authority snapshot
working CSIR graph
activation field
grounded belief state
causal mechanism graph
epistemic graph
goals/values/impact field
discourse/common ground
frontier and proof graph
budgets
```

A stage may propose an updated cycle-local state. Only Stage 13, Stage 16 side-effect journals, and Stage 21 discourse commit may create their authorized durable effects.

---

# 3. Stage 0 — ORIENT_AND_PIN_SEMANTIC_BRAIN

Pin exact roots for:

```text
Kernel Semantic ABI
CSIR compiler and normalizer ABI
semantic definitions and dependency closures
operational profiles
semantic-dynamics parameters
causal mechanisms and parameters
use authorizations
language and multimodal packages
sensor calibration and observation models
epistemic, safety, privacy and response policies
runtime adapters
boot and overlays
```

Construct:

- ParticipantFrame;
- context/world stack;
- cycle clock and temporal frame;
- active self referent and runtime-backed state/capability view;
- resource and inference budgets.

No later stage resolves a floating semantic or parameter revision.

---

# 4. Stage 1 — OBSERVE_MULTIMODAL_EVIDENCE

Create source-attributed evidence envelopes from text, audio, vision, location, temperature, telemetry, operation results and teaching.

Preserve raw signal identity, source, calibration reference, time, spatial extent, permission and lineage.

No semantic fact is asserted.

---

# 5. Stage 2 — ENCODE_FORM_AND_SENSOR_EVIDENCE

## 5.1 Language path

```text
surface spans
→ reversible normalization
→ script/language evidence
→ morphology/form lattice
→ lexeme/sense candidates
→ semantic contribution graph fragments
→ construction candidates
```

## 5.2 Non-language path

```text
sensor/track signal
→ calibrated feature likelihoods
→ candidate referent/identity links
→ candidate state-dimension observations
→ spatial/temporal relations
```

## 5.3 Output

A unified evidence lattice. Evidence candidates may overlap and disagree.

---

# 6. Stage 3 — ACTIVATE_AND_GROUND_REFERENTS

Initialize sparse activations for candidate referents, identities, types and role anchors.

Use:

- ParticipantFrame;
- aliases and identifiers;
- discourse mention chains;
- visual/audio tracks;
- spatial continuity;
- prior system output;
- event/proposition history;
- type/context/time compatibility.

Run bounded joint identity/coreference message passing.

A high activation does not convert a provisional referent into resolved identity without the required evidence contract.

---

# 7. Stage 4 — PROJECT_ENTITLED_STATE_SPACES

For each candidate referent:

1. resolve exact type-definition closure;
2. derive facet entitlements;
3. instantiate applicable state-variable domains;
4. project current state-belief distributions;
5. expose relation, structure, location and temporal state;
6. expose affordances, capabilities, dependencies and resources;
7. expose causal mechanisms applicable by type/role/context;
8. retain defaults separately from active state;
9. expose conflicts, staleness and missing dimensions.

Stage 4 generates semantic closure candidates for Stage 5.

---

# 8. Stage 5 — COMPILE_CANDIDATES_TO_CSIR

This is the mandatory semantic compiler barrier.

For every lexical, construction, grounding, state and causal candidate:

```text
resolve exact definition/profile/parameter/use pins
expand definition closure
bind grounded participants and variables
add context/time/scope/polarity/evidence
compile to CSIR
canonicalize
validate hard constraints
emit closure proof
```

No opaque schema label enters the meaning solver.

Candidate neural embeddings/activations remain annotations over exact CSIR candidates.

---

# 9. Stage 6 — RUN_RECURRENT_MEANING_DYNAMICS

Construct the typed factor/message graph over CSIR candidates.

Run recurrent bottom-up/top-down propagation:

- evidence supports candidate fragments;
- candidate definitions predict roles and restrictions;
- type/state knowledge activates compatible closures;
- incompatible identities, bindings and scopes inhibit one another;
- causal/state plausibility contributes soft evidence;
- hard semantic violations are clamped out.

The stage stops on convergence, certified bound, or budget exhaustion.

It emits activation history, pruning trace and best semantic-equivalence classes.

---

# 10. Stage 7 — STABILIZE_SEMANTIC_ATTRACTORS

Cluster derivations by canonical CSIR normal form.

Produce:

```text
stable meaning classes
posterior/energy assessment
close alternatives
partial graph
open variables
contradictions
unresolved evidence
convergence/budget status
```

Use-specific decisiveness is assessed. A graph may be adequate for mention but not transition or execution.

---

# 11. Stage 8 — BUILD DISCOURSE, PROPOSITION, EVENT AND QUERY STRUCTURES

Re-abstract stable CSIR subgraphs through authorized operational profiles:

- propositions and claim occurrences;
- event/action/process occurrences;
- state/property assertions;
- queries and projections;
- directives, desires and plans;
- corrections and retractions;
- discourse acts and commitments.

Operational records add validation/lifecycle behavior, not new meaning.

---

# 12. Stage 9 — PLACE EPISTEMIC CONTEXT AND ASSIMILATE WORLD BELIEF

Determine actual, reported, believed, hypothetical, planned, desired, fictional, quoted or counterfactual placement.

Evaluate source, evidence, contradiction, calibration, sensitivity and permission.

Update cycle-local grounded belief through source-aware Bayesian/paraconsistent assimilation.

A claim may remain an attributed proposition indefinitely.

---

# 13. Stage 10 — QUERY AND EXPLAIN FROM GROUNDED WORLD MODEL

Bind query restriction graphs against the canonical semantic world model:

- identity and type;
- state belief/timelines;
- relations and spatial structure;
- events and causal paths;
- capabilities and dependencies;
- epistemic support/opposition;
- goals, impact and commitments.

Return semantic bindings and proof paths.

Explanation is graph extraction from the causal/proof model, not a generated story.

---

# 14. Stage 11 — CLASSIFY PREDICTION ERROR AND ADVANCE LEARNING

Compare predicted and observed meaning/state/outcome.

Create precise frontiers for:

```text
unknown form/sense/construction
identity or grounding error
missing state dimension/value
observation calibration error
missing role or transition effect
causal-structure error
causal-parameter error
context/time error
capability dependency error
impact/goal error
realization/response error
```

Advance:

- continuous parameter candidates;
- discrete definition candidates;
- causal mechanism candidates;
- competence and counterexample cases;
- learning questions selected by information gain.

No candidate becomes authoritative here.

---

# 15. Stage 12 — SIMULATE CAUSAL TRANSITIONS AND COUNTERFACTUALS

For admitted actual events, intended actions, hypotheses or planning candidates:

1. match applicable role-bound mechanisms;
2. compute direct state deltas;
3. propagate dependency and cross-dimensional effects;
4. generate secondary event candidates;
5. update capability/resource predictions;
6. calculate confidence and causal paths;
7. preserve alternate outcome branches;
8. detect cycles and budget limits.

Actual, hypothetical and counterfactual simulations remain in separate contexts.

Preview never mutates durable state.

---

# 16. Stage 13 — COMMIT AUTHORIZED KNOWLEDGE, STATE AND LEARNING ARTIFACTS

Compile one or more atomic GraphPatches for:

- observations/evidence;
- claim and knowledge records;
- admitted event occurrences;
- state and relation timeline changes;
- causal/transition proofs;
- candidate learned definitions/parameters;
- corrections, retractions and invalidations.

Commit requires exact pre-state, authority root, proof, context, permission and CAS validation.

Learning candidates are committed as candidates, not active authority.

---

# 17. Stage 14 — PROPAGATE CAPABILITY, IMPACT, AFFECT AND SIGNIFICANCE

Using committed or admissible preview deltas:

- reevaluate capability dependencies;
- assess physical/structural/biological/cognitive/social consequences;
- evaluate stakeholder- and goal-relative impact;
- infer affective consequences only through explicit mechanisms/evidence;
- distinguish salience, durable importance, urgency and risk;
- preserve uncertainty and privacy scope.

No keyword-based emotional inference.

---

# 18. Stage 15 — DERIVE OBLIGATIONS AND ARBITRATE GOALS

Generate goals from:

- open queries;
- directives and commitments;
- predicted risks;
- impact and stakeholder state;
- learning frontiers;
- operation outcomes;
- discourse/social obligations;
- safety and privacy policy.

Optimize a compatible goal set under benefit, information gain, risk, cost, obligation, urgency, resources and conflicts.

---

# 19. Stage 16 — PLAN, AUTHORIZE, EXECUTE AND OBSERVE

Use causal simulation to construct plans.

External action requires:

```text
affordance
live capability
permission
required role bindings
resources
acceptable predicted risk
operation adapter authority
journal/idempotency
```

Operation results return as new Stage-1 evidence. Operations never directly write semantic state.

---

# 20. Stage 17 — ASSIMILATE OPERATION OUTCOMES AND RECUR

Compare predicted operation outcome with observation.

Update cycle-local world belief, causal prediction error, capability state and goals.

If materially changed, rerun bounded portions of Stages 9–16 using the same cycle authority or restart if authority/pre-state changed.

No stale response goal survives material outcome change.

---

# 21. Stage 18 — CONSTRUCT RESPONSE CSIR

Construct target-bearing semantic response actions such as:

```text
answer bound query
report current state/event/set
provide causal explanation
qualify uncertainty/source
warn about predicted risk
clarify missing identity/binding
acknowledge a specific claim or impact
propose an authorized operation
ask a high-information learning question
remain silent for an explicit reason
```

Response selection uses truth, coverage, information gain, impact sensitivity, social appropriateness, risk and cost.

No final surface strings.

---

# 22. Stage 19 — REALIZE TARGET LANGUAGE OR MODALITY

Compile Response CSIR through target-language or multimodal realization authority:

```text
semantic response graph
→ discourse/clause plan
→ role realization and information structure
→ reference generation
→ morphology/prosody/layout
→ surface candidates
```

The realizer may choose wording, not meaning.

---

# 23. Stage 20 — VERIFY SEMANTIC EQUIVALENCE AND AUTHORIZE EMISSION

Re-analyze each generated candidate under pinned compatible authority.

Require semantic equivalence of:

- target and role bindings;
- context/time/aspect;
- polarity/modality;
- causal and epistemic qualification;
- discourse act and commitment;
- uncertainty and source attribution.

Then independently verify safety, privacy, freshness, audience, channel and emission policy.

---

# 24. Stage 21 — COMMIT OUTPUT DISCOURSE AND COMMON GROUND

Only observed emission creates output discourse records.

Commit speaker, audience, response goal, semantic content, surface, emission proof and common-ground proposal.

Delivery does not prove user acceptance, understanding or truth.

---

# 25. Stage 22 — CONSOLIDATE, INVALIDATE, REPLAY AND FINALIZE

Perform bounded consolidation:

- merge equivalent episodic evidence;
- abstract reusable subgraphs conservatively;
- evaluate parameter/definition/causal candidate competence;
- promote only authorized uses;
- supersede exact prior authority;
- invalidate affected projections and decisions;
- schedule replay under new snapshots;
- retain unresolved frontiers and budget incompleteness.

Produce final cycle summary with exact initial/final roots and replay requirements.
