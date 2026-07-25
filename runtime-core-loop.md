# CEMM Runtime Core Loop — Lean Semantic Cognition Architecture

**Status:** proposed normative runtime architecture for repaired CEMM v1
**Purpose:** preserve canonical Stage 0–22 semantics while implementing them as a small number of efficient runtime components rather than 23 transactions, 23 oversized services, duplicated state models, or phrase/domain-specific patches.

---

# 0. Runtime thesis

CEMM executes one semantic cognition cycle:

```text
evidence
→ grounding
→ entitled semantic projection
→ candidate meaning
→ stabilization
→ discourse/proposition/query/action structure
→ epistemic placement
→ query / learning / transition reasoning
→ authorized commit
→ capability / goal / action
→ Response CSIR
→ realization
→ verification
→ common ground
→ finalization
```

The logical Stage 0–22 boundaries remain explicit because they define semantic ownership, persistence, and effect rules.

They do **not** require:

```text
23 database transactions
23 separate semantic brains
23 large runtime services
one class per stage artifact
```

The repaired runtime preserves:

```text
one exact semantic authority
one mutable grounded world/discourse model
one cycle-local workspace
explicit persistence/effect boundaries
bounded recursion
partial understanding
typed learning frontiers
language-independent semantics
```

---

# 1. Runtime layers

## 1.1 Immutable semantic authority

Pinned per semantic pass:

```text
Kernel Semantic ABI
operator/role contracts
CSIR constructors/normalization
semantic definitions
subtype/facet inheritance
state dimension/domain authority
operational profiles
promoted graph rules
causal/transition mechanisms
capability dependencies
language/multimodal projection authority
model artifacts
policies/authorizations
```

Authority changes only by publishing a new generation and explicit activation.

---

## 1.2 Mutable grounded world/discourse

Contains:

```text
referents
claim occurrences
admitted beliefs
state timelines
events
evidence
participant/session facts
discourse/common ground
commitments
corrections/retractions
operation observations
```

World/discourse revision never silently mutates authority.

---

## 1.3 Cycle-local cognition

`CycleWorkspace` owns transient artifacts:

```text
EvidenceLattice
GroundingCandidateSet
StateSpaceProjection[]
CSIRCandidateSet
ActivationGraph
SemanticAttractorSet
PartialMeaning
OpenVariables
EpistemicAssessment[]
QueryResult[]
TransitionPreview[]
LearningFrontier[]
CapabilityAssessment[]
GoalCandidate[]
ResponseCSIRCandidate[]
RealizationCandidate[]
proof traces
```

Persistence is exceptional.

---

# 2. Process/session/cycle object model

## 2.1 Process lifetime

```text
RuntimeAttestation
AuthorityGenerationManager
ImmutableBootStore
RuntimeServiceRegistry
ModelArtifactCache
ObservationProviderRegistry
MaintenanceScheduler
```

Do not perform full release verification or whole-store hashing on every message.

---

## 2.2 Session lifetime

```text
SessionContext
  session_ref
  conversation_ref
  stable self_ref
  participant bindings
  retention policy
  permission scope
  discourse/common-ground handle
```

Stable participants are initialized idempotently once per session/context.

---

## 2.3 Cycle lifetime

```text
CycleState
  cycle_ref
  pass_ref
  authority_snapshot
  read_generation
  ParticipantFrame
  ContextStack
  TemporalFrame
  SelfRuntimeView
  CycleWorkspace
  BudgetSet
  effect handles
```

Creating `CycleState` never implies a durable mutation.

---

# 3. ParticipantFrame precedes pronoun grounding

## 3.1 Input turn

Example runtime frame:

```text
speaker   = participant:user
addressee = participant:self
audience  = [...]
```

Language evidence contributes:

```text
first person  → require current speaker
second person → require current addressee
third person  → require discourse/coreference resolution
```

Grounding:

```text
I   → first-person requirement  → speaker   → participant:user
you → second-person requirement → addressee → participant:self
```

---

## 3.2 Output turn

```text
speaker   = participant:self
addressee = participant:user
```

Realization chooses first/second-person forms from the output frame.

```text
self → first person
user → second person
```

according to target language/construction.

Pronouns do not define participant identity.

---

## 3.3 Embedded/quoted frames

Quoted/reported speech creates an embedded participant frame:

```text
outer speaker/addressee
  → quoted/reported speech event
      → embedded speaker
      → embedded addressee
```

Do not resolve every `I`/`you` against the outer session.

---

# 4. Universal semantic state model

## 4.1 State assignment

The universal exact shape remains:

```text
op:state
  subject
  dimension
  value
```

with canonical qualifiers where applicable:

```text
time
context
modality
evidence/source
validity interval
support/confidence
```

All three semantic roles remain explicit even when a query leaves one as a variable.

---

## 4.2 State dimensions are entitled, not globally attached

A referent does not own a hard-coded type-specific state schema.

```text
referent
→ direct type/facet set
→ recursive inheritance closure
→ entitled dimensions
→ dimension domains/constraints
→ current state beliefs
```

---

## 4.3 Dimension domain families

Support through generic graph/literal/qualifier representation:

```text
categorical
ordered discrete
continuous
vector/manifold
relational
set-valued
process-valued
probabilistic
```

---

## 4.4 Defaults are expectations

An operational profile may provide:

```text
default distribution
normal range
expected transition
prior
```

Stage 4 must keep those separate from active current facts.

---

# 5. Recursive `StateSpaceProjection`

For every salient referent `R`:

```text
project_state_space(R, authority, world, context):

  direct_types = active_type_facets(R)

  closure = recursive_exact_closure(
      direct_types,
      subtype/facet inheritance,
      bounded=true,
      cycle_safe=true
  )

  dimensions = union(entitled_dimensions(x) for x in closure)
  capabilities = union(entitled_capabilities(x) for x in closure)
  resources = union(entitled_resources(x) for x in closure)
  mechanisms = union(applicable_mechanisms(x) for x in closure)

  for each dimension:
      retrieve current state timeline
      preserve source/time/context
      reconcile support/opposition
      detect missing/stale/conflicting
      enforce domain constraints
      keep defaults separate

  return StateSpaceProjection(...)
```

### Performance

Cache entitlement closure by:

```text
AuthorityGeneration
+ type/facet closure signature
```

Current state values depend on mutable world revision and are loaded separately.

Do not persist the projection by default.

---

# 6. Self architecture

## 6.1 Self identity

`participant:self` is a grounded referent anchored by runtime/session identity.

It is not defined by:

```text
I
you
assistant
system
```

Those are language/designation/session projections.

---

## 6.2 Self semantic inheritance

Illustrative closure:

```text
self
→ digital cognitive agent
→ software system
→ digital system
→ entity
```

Exact refs are semantic IDs; labels are optional language mappings.

---

## 6.3 Runtime observation providers

Stage 1 may observe:

```text
runtime attestation validity
process/service availability
authority loaded
semantic store reachability
interpreter availability
query engine availability
response adapter/channel availability
resource availability/load
network connectivity where available
operation adapter health
```

These are evidence envelopes, not hard-coded English states.

---

## 6.4 Capability assessments

A capability derives recursively from dependencies:

```text
CapabilityAssessment
  capability_ref
  availability_score 0..1
  confidence
  blockers[]
  dependencies[]
  proof
```

Example:

```text
communication capability
  depends on:
    semantic response construction
    realizer availability
    output adapter availability
    permission
    resource sufficiency
```

Raw state dimensions do not all become percentages.

---

## 6.5 Knowing semantic readiness without lexical `ready`

The runtime can know:

```text
communication capability = 1.0
semantic-runtime viability = 0.98
blocking faults = none
```

and derive a strongly positive operational condition.

A language pack may realize this as:

```text
ready
working normally
available
able to respond
```

if those mappings exist.

The semantic state does not depend on the token.

---

# 7. Cognitive status must not corrupt self-world state

When interpretation is incomplete:

```text
PartialMeaning
OpenVariables
InterpretationAssessment
LearningFrontier
```

may change.

Do not automatically set:

```text
self = confused
self = unhealthy
self = unavailable
```

unless separate entitled state evidence supports it.

Example diagnostic category:

```text
input asks about an unknown lexical target
```

Possible cycle state:

```text
world/self semantic delta:
  none

interpretation:
  query/discourse structure partly resolved
  one lexical target unresolved

frontier:
  unknown-form/lexicalization target

epistemic:
  insufficient support ABOUT meaning(target)

goal:
  resolve or clarify target

self operational capability:
  unchanged
```

---

# 8. Epistemic status is target-scoped

Use:

```text
EpistemicAssessment
  target_ref / target_graph
  support
  opposition
  sufficiency
  uncertainty
  contradiction
  source coverage
  proof dependencies
```

Targets include:

```text
proposition
query variable
referent identity
word/form meaning
state assignment
causal explanation
```

Do not model all cognition as one mutable global `self.epistemic_state`.

---

# 9. Eight efficient macro-passes mapped to Stage 0–22

```text
A ORIENT                 Stage 0
B OBSERVE_ENCODE         Stages 1–2
C GROUND_PROJECT         Stages 3–4
D COMPOSE_SETTLE         Stages 5–7
E STRUCTURE_REASON       Stages 8–12
F COMMIT_PROPAGATE       Stages 13–14
G GOAL_ACT_RECONCILE     Stages 15–17
H RESPOND_FINALIZE       Stages 18–22
```

The implementation may merge small modules, but every logical stage retains explicit artifact and side-effect ownership.

---

# 10. Detailed logical stages

## Stage 0 — ORIENT_AND_PIN_SEMANTIC_BRAIN

### Inputs

```text
RuntimeAttestation
SessionContext
current authority generation
readable world/discourse revisions
channel/language hints
```

### Work

Pin:

```text
semantic ABI
compiler/normalizer
definitions/rules
state/profile authority
model artifacts
language packages
policies
```

Construct:

```text
ParticipantFrame
ContextStack
TemporalFrame
SelfRuntimeView
BudgetSet
CycleWorkspace
```

### Persistence

None.

### Hard invariant

No lexical form may invent participant identity before this frame exists.

---

## Stage 1 — OBSERVE_MULTIMODAL_EVIDENCE

### Inputs

```text
text/audio/vision/sensors
runtime telemetry
operation results
teaching evidence
```

### Output

```text
EvidenceEnvelope[]
  source
  time
  permission
  calibration
  raw identity
  lineage
```

### Persistence

None by default.

Text establishes that an utterance occurred, not that its proposition is automatically true.

---

## Stage 2 — ENCODE_FORM_AND_SENSOR_EVIDENCE

### Language path

```text
surface
→ reversible normalization
→ language/script evidence
→ morphology/form lattice
→ lexeme/sense candidates
→ participant/deictic requirements
→ construction candidates
→ semantic contribution candidates
```

### Unknown material

Produce:

```text
UnknownFormEvidence
UnknownConstructionEvidence
SemanticKindCandidateSet
```

Do not create semantic atoms here.

### Output

```text
EvidenceLattice
```

### Persistence

None.

---

## Stage 3 — ACTIVATE_AND_GROUND_REFERENTS

### Inputs

```text
EvidenceLattice
ParticipantFrame
discourse/common ground
prior semantic outputs
world identity candidates
```

### Work

Resolve jointly:

```text
participant requirements
names/designations
coreference
identity
mention chains
multimodal tracks where available
```

### Output

```text
GroundingCandidateSet
IdentityCoreferenceTrace
```

### Persistence

None.

### Participant rule

```text
first person  → speaker
second person → addressee
```

is grounded here, not in lexical authority.

---

## Stage 4 — PROJECT_ENTITLED_STATE_SPACES

### Inputs

```text
GroundingCandidateSet
type/facet authority
world state timelines
operational profiles
```

### Work

For each salient candidate referent:

```text
recursive type/facet closure
dimension entitlement
current state-belief retrieval
capability/resource dependencies
applicable transition/causal mechanisms
missing/conflicting/stale detection
```

### Output

```text
ReferentProjection[]
StateSpaceProjection[]
SemanticClosureCandidate[]
```

### Persistence

None.

### Critical ordering

This occurs before query execution and before response selection.

---

## Stage 5 — COMPILE_CANDIDATES_TO_CSIR

### Inputs

```text
language/sensor contributions
groundings
state projections
construction candidates
```

### Neural proposal

Propose:

```text
operator applications
role bindings
semantic variables
scope/qualifiers
discourse-act candidates
```

### Exact compiler

```text
bind grounded refs
validate operator/role types
allow legitimate open query variables
normalize
clamp impossible candidates
```

### State requirement

`role:dimension` is first-class.

### Output

```text
CSIRCandidateSet
ClosureProof[]
HardConstraintTrace
```

### Persistence

None.

---

## Stage 6 — RUN_RECURRENT_MEANING_DYNAMICS

Run bounded competition over:

```text
lexical/form evidence
construction compatibility
participant grounding
type entitlement
state plausibility
scope/time/context
discourse continuity
world compatibility
```

Hard semantic violations stay clamped.

### Output

```text
ActivationGraph
ActivationTrace
```

---

## Stage 7 — STABILIZE_SEMANTIC_ATTRACTORS

### Output

```text
SemanticAttractorSet
PartialMeaning
OpenVariables
Contradictions
UnresolvedEvidence
ConvergenceAssessment
```

A partial stable graph is valid cognition.

Do not replace partial meaning with a generic failure token.

---

## Stage 8 — BUILD DISCOURSE / PROPOSITION / EVENT / QUERY STRUCTURES

Re-abstract stable semantic graphs into operational structures:

```text
Proposition
ClaimOccurrence
StateAssertion
Event/Process/Action
Query
Directive/Request
Correction/Retraction
Commitment
Greeting/Acknowledgment
```

### Utterance force

Force is settled from compositional evidence and context.

Punctuation/word order/prosody may contribute evidence but never become sole semantic authority.

Do not hard-code:

```text
how → one query type
is → one operator
question mark → guaranteed semantic query
imperative first token → guaranteed command
```

---

## Stage 9 — PLACE_EPISTEMIC_CONTEXT_AND_ASSIMILATE_WORKING_BELIEF

### Keep separate

```text
utterance evidence
proposition
claim occurrence
source
admission decision
working belief
state assignment
```

### Contexts

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

### Assertion rule

A user assertion about CEMM's runtime state is initially a source-attributed claim. It does not directly overwrite runtime-provider evidence.

### Output

```text
EpistemicPlacement
WorkingBeliefDelta
AdmissionDecision[]
```

Cycle-local until Stage 13.

---

## Stage 10 — QUERY_AND_EXPLAIN

### Query structure

```text
Query
  restriction_graph
  variables
  projection
  context/time constraints
```

### Search over

```text
identity/type
state timelines
relations
events
capabilities
epistemic support/opposition
causal/proof structures
discourse/common ground
```

### Output

```text
QueryResult
  bindings[]
  proofs[]
  coverage
  unresolved_variables
  blocking_frontiers[]
```

### Usability rule

A missing optional subsystem must not block an otherwise grounded answer.

---

## Stage 11 — CLASSIFY_PREDICTION_ERROR_AND_ADVANCE_LEARNING

Compare:

```text
predicted meaning/state/outcome
vs
observed/settled/admitted outcome
```

Create typed frontiers:

```text
unknown form
construction
identity
definition
state model
transition role
causal mechanism
capability dependency
discourse
response realization
```

### Output

```text
PredictionError[]
LearningFrontier[]
LearningCandidateWork[]
LearningQuestionCandidates
```

### Persistence

None yet.

---

## Stage 12 — SIMULATE_CAUSAL_TRANSITIONS_AND_COUNTERFACTUALS

Only events/actions/hypotheses with applicable mechanisms generate transition previews.

### Mechanism contains

```text
required roles
state/domain requirements
preconditions
defeaters
role-addressed deltas
secondary events
uncertainty
proof
```

### Semantic distinctions

The following categories may share vocabulary but must remain different:

```text
state assertion
state query
event/state transition
directive requesting a transition
```

### Persistence

None.

---

## Stage 13 — COMMIT_AUTHORIZED_KNOWLEDGE_STATE_AND_LEARNING_ARTIFACTS

This is the first normal durable semantic/world commit boundary.

Commit only permitted:

```text
admitted evidence
scoped claims/beliefs
state timeline deltas
event occurrences
participant/session facts
learning candidates/evidence
corrections/retractions
```

Require:

```text
exact pre-state
authority generation
read generation/CAS
context
source/evidence
permission
proof
```

Learning candidates remain provisional unless separately promoted.

---

## Stage 14 — PROPAGATE_CAPABILITY_IMPACT_AFFECT_AND_SIGNIFICANCE

### Capability

Reevaluate dependency graphs from committed/admissible state.

### Affect

Only infer for entitled entities through evidence/mechanism.

No keyword-based emotion inference.

### Self

Runtime capability assessments may change from telemetry/dependencies. Partial interpretation does not automatically become affective/cognitive `confusion` state.

### Output

```text
CapabilityAssessment[]
ImpactAssessment[]
AffectEstimate[]
SignificanceAssessment[]
```

Mostly cycle-local.

---

## Stage 15 — DERIVE_OBLIGATIONS_AND_ARBITRATE_GOALS

Goals may arise from:

```text
open query
directive/request
commitment
clarification frontier
learning frontier
risk
operation outcome
discourse obligation
```

Select under:

```text
truth/coverage
information gain
benefit
risk
cost
permission
resource constraints
urgency
goal conflicts
```

### Important distinction

Unknown lexical target may create:

```text
goal = request targeted clarification
```

while a well-grounded self-state query creates:

```text
goal = answer query
```

Unrelated uncertainty must not override the actual target.

---

## Stage 16 — PLAN_AUTHORIZE_EXECUTE_AND_OBSERVE

For executable goals:

```text
plan
→ capability check
→ permission
→ resource check
→ risk
→ adapter authority
→ effect journal/idempotency
→ execute
→ operation observation
```

A directive never directly mutates semantic world state.

Operation results return as new Stage-1 evidence.

---

## Stage 17 — ASSIMILATE_OPERATION_OUTCOMES_AND_RECUR

Compare predicted and observed operation results.

Update cycle-local:

```text
working belief
prediction error
capability
goals
frontiers
```

Allow bounded re-entry only.

No stale response goal survives a material outcome change.

---

## Stage 18 — CONSTRUCT_RESPONSE_CSIR

Response is a semantic action.

Possible response families:

```text
answer query bindings
report state/relation/event
report target-scoped uncertainty
provide explanation
request targeted clarification
acknowledge claim
correct prior output
report capability
accept/decline directive
ask learning question
remain silent for explicit reason
```

### Response-source precedence

1. actual query target/result;
2. exact blocking unresolved variable/frontier;
3. epistemic qualification specific to that target;
4. discourse obligation;
5. capability/action result.

Do not allow unrelated global uncertainty to dominate.

---

## Stage 19 — REALIZE_TARGET_LANGUAGE_OR_MODALITY

```text
Response CSIR
→ discourse/clause plan
→ reference realization using OUTPUT ParticipantFrame
→ lexical/construction selection
→ morphology
→ surface candidate
```

### Meaning precedes words

A semantic pattern representing strongly positive operational capability may be realized as `ready` only if the language mapping exists.

The meaning itself does not depend on that lexical item.

---

## Stage 20 — VERIFY_SEMANTIC_EQUIVALENCE_AND_AUTHORIZE_EMISSION

Verify:

```text
all content spans trace to Response CSIR
no unsupported participant/state/relation/emotion/causality
no internal IDs
required uncertainty/qualification preserved
```

Use selective independent round-trip only for novelty/risk/audit—not as a mandatory per-message tax.

---

## Stage 21 — COMMIT_OUTPUT_DISCOURSE_AND_COMMON_GROUND

After observed emission, commit:

```text
emitted semantic action
participant references
answer fulfillment
common-ground proposal
open/closed question state
new clarification target
commitment where applicable
```

Do not reparse self-generated surface and treat it as independent world truth.

The authoritative output meaning was already the Response CSIR.

---

## Stage 22 — CONSOLIDATE_INVALIDATE_REPLAY_AND_FINALIZE

Perform bounded:

```text
cycle completion
frontier retention policy
learning evidence consolidation
invalidation/retraction handling
replay scheduling
promotion eligibility signal
final trace
```

Expensive promotion scans, retraining, global integrity scans, and cache rebuilds belong to maintenance—not every turn.

---

# 11. Discourse-act decision matrix

| Settled structure | World effect before policy | Main reasoning path | Response source |
|---|---|---|---|
| Claim/assertion | attributed claim candidate | Stage 9 admission/contradiction | acknowledgment/correction only when warranted |
| Query/probe | none | Stage 10 projection | `QueryResult` |
| Directive/request | desired event/goal candidate | Stage 15–16 capability/permission/action | operation decision |
| Hypothetical | isolated context only | simulate/query | hypothetical result |
| Correction/retraction | revision candidate | reconcile/invalidate | corrected common ground |
| Unknown/partial | no implicit world mutation | frontier/clarification | exact unresolved target |

---

# 12. Resolved vs unresolved response behavior

## 12.1 Fully grounded fact/current state

```text
query target fully grounded
→ execute query
→ return bindings/proof
→ Response CSIR answers target
```

Examples of categories:

```text
current self operational capability
known participant identity/name
known relation
known state timeline
```

---

## 12.2 Partly unresolved interpretation

When:

```text
stable partial graph exists
+ one or more open variables/frontiers
```

Do:

```text
preserve stable graph
identify exact blocker
answer independently answerable portions
clarify only when blocker prevents requested use
```

Do not:

```text
discard all meaning
set self confused
return global generic uncertainty
```

---

## 12.3 Observation/claim evidence

An utterance asserting `P` first means:

```text
claim(source, P)
```

Admission policy decides whether `P` becomes current belief/state.

Response behavior follows discourse need, not automatic answering.

---

## 12.4 Command/request

A directive requesting event/state `E` means:

```text
desired(E)
```

It means neither:

```text
E already happened
```

nor:

```text
requested state already holds
```

It becomes a goal/operation candidate.

---

# 13. Minimal participant/deixis language contract

Language packages should represent structural features equivalent to:

```text
reference form:
  person: first | second | third
  number
  possessive?
  reflexive?
  deictic constraints
  semantic type constraints where linguistically relevant
```

Resolution uses:

```text
ParticipantFrame
discourse salience
type constraints
scope/context
```

No universal bound participant IDs for first/second person.

---

# 14. Minimal structured-model outputs after repair

The neural semantic model should propose independent structures roughly equivalent to:

```text
discourse-act candidates

application slots:
  present?
  operator
  role -> grounded source / variable / existential

qualifier candidates:
  time
  context
  modality
  polarity/scope

query:
  open variables
  restriction links
  projection

reference requirements:
  participant/deictic constraints
```

It must not predict arbitrary domain IDs from a flat global vocabulary as semantic truth.

Exact grounding/validation remains outside neural authority.

---

# 15. Training episodes for semantic and state transitions

Use episodes:

```text
PRE
  ParticipantFrame
  relevant StateSpaceProjection
  discourse/common ground
  active frontiers
  runtime observations

INPUT
  EvidenceEnvelope[]

TARGET
  stable CSIR
  discourse act
  epistemic placement
  query structure
  transition OR NO_TRANSITION
  cognitive/frontier delta
  discourse delta
  admitted world delta
  Response CSIR
```

### Required contrastive families

```text
assertion vs query vs directive
actual vs reported vs hypothetical
state report vs event transition
unknown word vs genuinely new concept
self output vs user input perspective
resolved query vs partial query
state delta vs explicit no-delta
```

---

# 16. Lean implementation modules

Do not mirror every logical stage with a giant class.

Suggested responsibilities:

```text
runtime.py
  cycle orchestration / stage trace / effect boundaries

context.py
  SessionContext / ParticipantFrame / ContextStack / TemporalFrame

evidence.py
  EvidenceEnvelope / EvidenceLattice

interpreter.py
  language evidence + reference requirements; PURE

grounding.py
  participant/referent/coreference grounding

state_projection.py
  recursive type/facet closure + StateSpaceProjection

codec.py
  neural structured candidate proposals

compiler.py
  exact CSIR compilation/validation

settling.py
  recurrent candidate dynamics

discourse.py
  propositions/claims/queries/directives/common ground

epistemics.py
  scoped assessments + admission policy

inference.py
  query bindings/proofs

learning.py
  frontiers/candidates/commit handoff

transitions.py
  mechanisms/transition previews

capability.py
  dependency evaluation + normalized assessments

goals.py
  goal arbitration

response.py
  Response CSIR construction

realization.py
  target-language realization/verification
```

Small modules may be merged. Modularization must not create a second semantic ABI.

---

# 17. Persistence matrix

| Stage | Durable write by default? | Allowed durable effect |
|---|---:|---|
| 0–12 | No | cycle-local cognition/evidence candidates only |
| 13 | Yes, authorized only | world/learning CAS commit |
| 14–15 | No by default | assessments/goals usually transient |
| 16 | Only for explicit action | effect journal + operation evidence |
| 17 | As required | operation observation/reconciliation evidence |
| 18–20 | No semantic world write | response planning/verification |
| 21 | Yes | emitted discourse/common ground |
| 22 | Policy-dependent | consolidation/invalidation/promotion metadata |

Parsing is never a write boundary.

Querying is never a write boundary merely because a query occurred.

---

# 18. Performance constraints

Every cycle obeys:

```text
no whole graph scan
no whole-store hash
no full closure materialization
no retraining for ordinary world facts
no per-domain schema dispatch
no phrase regex routing
bounded recursive inheritance
bounded query/inference
bounded recurrent settling
bounded re-entry
```

Cache by correct revision:

```text
authority/type entitlement closure -> AuthorityGeneration
state timeline/query data          -> WorldRevision + context
discourse retrieval                -> DiscourseRevision
model cache                         -> immutable artifact hash
```

A discourse write must not invalidate semantic-definition closure caches.

---

# 19. Required debug trace

Each cycle should expose compact typed trace information:

```text
stage
input/output artifact refs/counts
selected semantic candidates
open variables
frontiers
query bindings
admission decisions
transition previews
commit receipts
capability assessments
goal decision
Response CSIR
realization proof
```

Trace data is not semantic authority.

---

# 20. Vertical acceptance scenarios

These are architecture probes, not hard-coded feature cases.

## Scenario A — participant inversion

The same first/second-person language under input and output frames binds opposite participants correctly.

## Scenario B — semantic self condition without lexical dependency

Self runtime evidence supports operational availability. Internal semantics remain correct even when the word `ready` has no designation.

## Scenario C — unresolved meaning isolation

One unknown lexical span opens a frontier while unrelated self operational state stays unchanged.

## Scenario D — one content, three acts

Closely related semantic content can settle as:

```text
claim
query
directive
```

and follow different Stage 9/10/15 paths.

## Scenario E — recursive dimension inheritance

A newly defined subtype receives inherited parent dimensions automatically through graph closure.

## Scenario F — open state query

A query projects:

```text
?dimension
?value
```

and returns bindings/proofs rather than only boolean unknown.

## Scenario G — user claim vs runtime evidence

A user claims CEMM is unavailable while runtime evidence reports availability. Both sources remain represented; runtime state is not silently overwritten.

## Scenario H — normal learning loop

Normal conversation:

```text
creates typed frontier
collects evidence
commits only permitted scoped learning
does not require manual Learn mode
```

---

# 21. Core diagnostic order

When a surface answer is wrong, diagnose in this order:

```text
1. Was ParticipantFrame/context correct?
2. Was referent identity grounded correctly?
3. Was type/facet closure correct?
4. Were the correct dimensions/capabilities entitled?
5. Could CSIR express the meaning/query/variables?
6. Did recurrent settling preserve partial meaning?
7. Was discourse force classified correctly?
8. Was epistemic context/admission correct?
9. Did query/transition reasoning target the right structure?
10. Was Response CSIR built from the correct result?
11. Only then: is training coverage insufficient?
```

Do not jump from a bad answer directly to adding examples or phrase rules.

---

# 22. Final repaired runtime loop

```text
SESSION / TRANSPORT
      |
      v
ParticipantFrame + authority/read pins
      |
      v
EvidenceEnvelope
      |
      v
language/sensor EvidenceLattice
      |
      v
grounded referents + identity/coreference
      |
      v
recursive type/facet closure
      |
      v
entitled StateSpaceProjection
      |
      v
open compositional CSIR candidates
      |
      v
bounded recurrent stabilization
      |
      +-------------------------------+
      |               |               |
      v               v               v
 proposition        query          directive/event
      |               |               |
      v               v               v
 epistemic        bindings/proof   transition/goal
 placement                         candidate
      \               |               /
       \              |              /
        +------ learning/frontiers --+
                       |
                       v
              authorized commit only
                       |
                       v
          capability / impact / goals
                       |
                       v
                 Response CSIR
                       |
                       v
              grounded realization
                       |
                       v
                semantic verify
                       |
                       v
             discourse/common ground
                       |
                       v
                    finalize
```

This loop is the implementation ground truth.

A new referent type, vocabulary item, state dimension, capability, relation, or language construction should normally extend:

```text
semantic data
+ recursive graph relations/inheritance
+ operational profile data
+ evidence
+ learned parameters/language mappings
```

—not the kernel operator set, runtime branch count, or database schema count.
