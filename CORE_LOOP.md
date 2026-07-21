# CEMM v3.5.1 Canonical Stage 0–22 Core Loop

**Status:** canonical logical cognitive contract  
**Important:** stages are logical boundaries, not mandatory database transactions.

---

## 0. Macro topology

```text
0  ORIENT_AND_PIN_SEMANTIC_BRAIN
1  OBSERVE_MULTIMODAL_EVIDENCE
2  ENCODE_FORM_AND_SENSOR_EVIDENCE
3  ACTIVATE_AND_GROUND_REFERENTS
4  PROJECT_ENTITLED_STATE_SPACES
5  COMPILE_CANDIDATES_TO_CSIR
6  RUN_RECURRENT_MEANING_DYNAMICS
7  STABILIZE_SEMANTIC_ATTRACTORS
8  BUILD_DISCOURSE_PROPOSITION_EVENT_AND_QUERY_STRUCTURES
9  PLACE_EPISTEMIC_CONTEXT_AND_ASSIMILATE_WORLD_BELIEF
10 QUERY_AND_EXPLAIN_FROM_GROUNDED_WORLD_MODEL
11 CLASSIFY_PREDICTION_ERROR_AND_ADVANCE_LEARNING
12 SIMULATE_CAUSAL_TRANSITIONS_AND_COUNTERFACTUALS
13 COMMIT_AUTHORIZED_KNOWLEDGE_STATE_AND_LEARNING_ARTIFACTS
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

Stages 3–7 and 11–17 may contain bounded recurrent subloops.

---

## 1. Cross-stage cycle state

Every stage receives an immutable or cycle-local view of:

```text
AuthoritySnapshot
ReadGeneration
CycleWorkspace
WorkingCSIR
ActivationField
GroundedBeliefState
EpistemicGraph
CausalModel
DiscourseCommonGround
GoalImpactField
FrontierGraph
ProofLineageGraph
Budgets
```

Durable effects are constrained by `RUNTIME_PLAN.md`.

---

## 2. Stage 0 — ORIENT_AND_PIN_SEMANTIC_BRAIN

### Inputs
- runtime attestation;
- session/context identity;
- target channel/language hints;
- current authority generation;
- current readable state generations.

### Work
Pin exact roots for:

```text
semantic ABI
compiler/normalizer ABI
definitions
operational profiles
dynamics parameters
causal mechanisms
use authorizations
language/multimodal packages
observation/calibration
policies/adapters
```

Construct:

```text
ParticipantFrame
ContextStack
TemporalFrame
SelfRuntimeView
Budgets
```

### Outputs
- `AuthoritySnapshot`;
- `ReadGeneration`;
- participant/context frame;
- initial `CycleWorkspace`.

### Prohibition
No later stage may resolve a floating executable semantic or parameter revision.

---

## 3. Stage 1 — OBSERVE_MULTIMODAL_EVIDENCE

Create source-attributed evidence envelopes from:

```text
text
audio
vision
location
sensors
runtime telemetry
operation results
teaching
```

Preserve:

```text
source
time
spatial extent
permission
calibration ref
lineage
raw signal identity
```

No world fact is asserted.

---

## 4. Stage 2 — ENCODE_FORM_AND_SENSOR_EVIDENCE

### Language path

```text
surface spans
→ reversible normalization
→ script/language evidence
→ morphology/form lattice
→ lexeme/sense candidates
→ semantic contributions
→ construction candidates/program outputs
```

### Non-language path

```text
signal
→ calibrated features
→ identity/referent candidates
→ state-dimension observations
→ spatial/temporal relations
```

### Output
A unified evidence lattice that may contain overlapping/disagreeing candidates.

---

## 5. Stage 3 — ACTIVATE_AND_GROUND_REFERENTS

Initialize/propagate candidate:

```text
referents
identities
types
participant anchors
mention chains
tracks
```

Use:

```text
ParticipantFrame
aliases/identifiers
discourse history
prior output
multimodal continuity
type/context/time compatibility
```

Run bounded joint identity/coreference solving.

High activation alone never commits identity.

---

## 6. Stage 4 — PROJECT_ENTITLED_STATE_SPACES

For each candidate referent:

1. resolve exact type/facet closure;
2. derive applicable state dimensions;
3. expose state-belief distributions;
4. expose relations, time, location and structure;
5. expose affordances/capabilities/resources;
6. expose applicable causal mechanisms;
7. keep defaults separate from active state;
8. expose missing/conflicting/stale dimensions.

Output semantic closure candidates for Stage 5.

---

## 7. Stage 5 — COMPILE_CANDIDATES_TO_CSIR

Mandatory compiler barrier.

For each candidate:

```text
resolve exact pins
expand definition closure
bind grounded participants/variables
add scope/context/time/polarity/modality/evidence
compile to CSIR
normalize
validate hard constraints
emit ClosureProof
```

Opaque legacy schema labels do not enter the semantic solver.

Legacy UOL may only be migration/shadow input and must compile to CSIR.

---

## 8. Stage 6 — RUN_RECURRENT_MEANING_DYNAMICS

Build typed activation/factor graph over exact CSIR candidates.

Run bounded recurrent propagation:

```text
bottom-up evidence
top-down semantic prediction
type/role/scope/context constraints
state/discourse plausibility
inhibition among incompatible hypotheses
```

Hard violations are clamped.

Stop on:

```text
convergence
certified bound
budget exhaustion
```

---

## 9. Stage 7 — STABILIZE_SEMANTIC_ATTRACTORS

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

A partial stable graph is valid cognition.

Use-specific decisiveness is assessed separately.

---

## 10. Stage 8 — BUILD DISCOURSE, PROPOSITION, EVENT AND QUERY STRUCTURES

Re-abstract stable CSIR subgraphs through authorized operational profiles into:

```text
propositions
claim occurrences
event/process/action occurrences
state/property assertions
queries/projections
directives/desires/plans
corrections/retractions
discourse acts/commitments
```

Operational profiles add lifecycle/validation behavior, not semantic content.

---

## 11. Stage 9 — PLACE EPISTEMIC CONTEXT AND ASSIMILATE WORLD BELIEF

Place structures into:

```text
actual
reported
believed
hypothetical
planned
desired
fictional
quoted
counterfactual
```

Evaluate:

```text
source
evidence dependence
contradiction
calibration
sensitivity
permission
admission policy
```

Update cycle-local grounded belief.

A claim may remain attributed-only indefinitely.

---

## 12. Stage 10 — QUERY AND EXPLAIN FROM GROUNDED WORLD MODEL

Match query restriction graphs against:

```text
identity/type
state timelines
relations
spatial/temporal structures
events
causal paths
capabilities/dependencies
epistemic support/opposition
goals/commitments
```

Return semantic bindings and exact proof paths.

Explanation is proof/causal graph extraction, not free-form story invention.

---

## 13. Stage 11 — CLASSIFY PREDICTION ERROR AND ADVANCE LEARNING

Compare predicted and observed meaning/state/outcome.

Create typed frontiers for:

```text
unknown form/lexicalization/construction
identity/grounding
definition
state model
observation calibration
role/transition
causal structure
causal parameter
context/time
capability dependency
discourse
impact/goal
response/realization
```

Advance candidate work in `CycleWorkspace`:

```text
candidate definitions
candidate language mappings
candidate causal mechanisms
candidate parameter artifacts
competence/counterexample requirements
learning questions
```

No candidate becomes active authority here.

---

## 14. Stage 12 — SIMULATE CAUSAL TRANSITIONS AND COUNTERFACTUALS

For admitted actual events, intended actions, hypotheses or planning candidates:

```text
match role-bound mechanisms
compute direct deltas
propagate dependencies
generate secondary events
update capability/resource predictions
preserve alternate branches
record causal proof
detect cycles/budget limits
```

Factual, hypothetical and counterfactual contexts remain isolated.

Preview does not mutate durable world state.

---

## 15. Stage 13 — COMMIT AUTHORIZED KNOWLEDGE, STATE AND LEARNING ARTIFACTS

Compile atomic CAS-protected graph patches for permitted:

```text
evidence admission
claims/knowledge
admitted event occurrences
state/relation timelines
causal/transition proofs
learning candidates/evidence
corrections/retractions/invalidation
```

Commit requires:

```text
exact pre-state
authority generation
proof
context
permission
CAS
```

Learning candidates remain candidates unless promotion is separately authorized.

---

## 16. Stage 14 — PROPAGATE CAPABILITY, IMPACT, AFFECT AND SIGNIFICANCE

Using committed/admissible deltas:

```text
reevaluate capabilities/dependencies
assess physical/structural/biological/cognitive/social consequences
evaluate stakeholder/goal-relative impact
infer affect only via evidence/mechanism
derive risk/urgency/salience/significance
```

No keyword-based emotional inference.

Default output is cycle-local unless retention is explicitly justified.

---

## 17. Stage 15 — DERIVE OBLIGATIONS AND ARBITRATE GOALS

Generate goals from:

```text
open queries
directives/commitments
predicted risks
impact/stakeholder state
learning frontiers
operation outcomes
discourse/social obligations
safety/privacy policy
```

Select a compatible goal set under:

```text
truth/coverage
benefit
information gain
risk
cost
obligation
urgency
resource constraints
conflicts
```

---

## 18. Stage 16 — PLAN, AUTHORIZE, EXECUTE AND OBSERVE

Use causal simulation to build plans.

External action requires:

```text
affordance
live capability
permission
role bindings
resources
acceptable predicted risk
adapter authority
effect authorization
journal/idempotency
```

External effects are journaled before execution.

Operation results return as Stage-1 evidence.

Operations never directly mutate semantic world state.

---

## 19. Stage 17 — ASSIMILATE OPERATION OUTCOMES AND RECUR

Compare predicted operation outcome with observed evidence.

Update cycle-local:

```text
world belief
prediction error
capability state
goals
frontiers
```

If materially changed:

- request bounded semantic re-entry under the same authority generation when valid; or
- restart the pass if authority/pre-state consistency requires it.

No stale response goal survives material outcome change.

---

## 20. Stage 18 — CONSTRUCT RESPONSE CSIR

Construct semantic response actions such as:

```text
answer bound query
report state/relation/event
provide causal explanation
qualify uncertainty/source
clarify missing binding
acknowledge specific target
correct prior output
warn about risk
report capability
ask learning question
propose authorized operation
remain silent for explicit reason
```

No final surface strings.

---

## 21. Stage 19 — REALIZE TARGET LANGUAGE OR MODALITY

Compile Response CSIR through target realization authority:

```text
semantic response
→ discourse/clause plan
→ role/reference realization
→ morphology/prosody/layout
→ surface candidates
→ preservation proof
```

Wording may vary; meaning may not.

---

## 22. Stage 20 — VERIFY SEMANTIC EQUIVALENCE AND AUTHORIZE EMISSION

Mandatory cheap verifier checks:

```text
source pins
realization proof
qualification preservation
target/role bindings
context/time/aspect
polarity/modality
source/uncertainty
discourse act/commitment
```

Run independent full re-analysis when policy requires:

```text
new language generation
novel path
non-deterministic generator
high-risk disclosure
proof uncertainty
audit sample
```

Then independently evaluate:

```text
privacy
safety
freshness
audience
channel
emission authorization
```

No verifier bypass.

---

## 23. Stage 21 — COMMIT OUTPUT DISCOURSE AND COMMON GROUND

Only observed emission creates durable output-discourse state.

Commit:

```text
speaker
audience
response goal
semantic content
surface
emission proof
common-ground proposal
```

Delivery does not prove recipient acceptance, understanding or truth.

---

## 24. Stage 22 — CONSOLIDATE, INVALIDATE, REPLAY AND FINALIZE

Perform bounded consolidation:

```text
merge equivalent episodic evidence
evaluate reusable abstraction candidates
evaluate parameter/definition/causal competence
promote only through authorized generation switch
invalidate dependency-affected projections
schedule replay
retain unresolved frontiers
```

Compute honest final status:

```text
SUCCESS
PARTIAL
NO_RESPONSE_REQUIRED
RESPONSE_DEFERRED
RESPONSE_BLOCKED
ACTION_UNCERTAIN
RUNTIME_ERROR
```

Return exact initial/final authority and read generations plus replay requirements.
