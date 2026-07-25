# CEMM v1 Fixes — Architecture-Grounded Repair Plan

**Status:** implementation grounding plan
**Target:** repair current modular CEMM v1 without reintroducing phrase routing, domain schemas, English shortcuts, or a second semantic authority.
**Primary contracts:** current `AGENTS.md` and `ARCHITECTURE.md`, plus the canonical v3.5.1 `ARCHITECTURE.md`, `RUNTIME_PLAN.md`, and `CORE_LOOP.md` referenced by the current architecture.

---

## 0. Purpose

The current v1 refactor retains useful MVP properties—five compact operator shapes, exact semantic validation, immutable authority generations, N-best structured prediction, bounded inference, and semantic-pointer realization—but it also preserves proof-MVP shortcuts and introduces regressions that prevent the runtime from behaving like the intended semantic cognition kernel.

This plan deliberately does **not** optimize for one diagnostic phrase such as `how are you?`, one copula form, one state word, one family relation, or one query topology. Those are probes that expose missing general machinery.

The repair target is:

```text
meaning ≠ language

transport/session grounding
→ evidence
→ referents
→ recursive type/facet closure
→ entitled state-space projection
→ compositional CSIR
→ recurrent/partial stabilization
→ discourse act / proposition / query / event
→ epistemic placement
→ query / learning / transition reasoning
→ authorized commit
→ capability / goals / action
→ Response CSIR
→ realization
→ verification
→ common ground
```

The implementation must preserve these laws:

```text
exact semantics are authority
neural models propose/rank/compose/realize
world/discourse state is mutable
semantic authority is immutable and generation-pinned
partial understanding is valid cognition
unknown material must not erase grounded meaning
learning happens through typed frontiers and explicit boundaries
new domain ≠ new schema/class/runtime branch
```

---

# 1. Root defects observed in current v1

## 1.1 Participant identity is encoded as lexical truth

Current reference data directly binds forms equivalent to:

```text
I / me / my   → participant:user
you / your    → participant:system
```

This is only correct for one outer frame: user speaking to CEMM.

It is incorrect for:

- CEMM output;
- quoted/reported speech;
- replayed logs containing both speakers;
- agent-to-agent interaction;
- multi-party sessions;
- synthetic-language tests;
- training over speaker/addressee reversal.

### Required repair

Language contributes **participant requirements**, not participant identity:

```text
first person  → current speaker requirement
second person → current addressee requirement
third person  → discourse/coreference requirement
```

Stage 0 creates `ParticipantFrame`; Stage 3 grounds those requirements.

---

## 1.2 Query representation is structurally too weak

Current structured prediction reduces a query to essentially one ordinary application. This naturally supports yes/no matching better than open information gaps.

Canonical query semantics need separable:

```text
information gap
semantic variables
restriction graph
projection
scope/context/time restrictions
discourse act
response obligation
```

### Required repair

Add first-class query structures that still compile to the same small CSIR kernel:

```text
QueryStructure
  restriction_graph
  variables
  projection
  qualifiers
```

Stage 10 returns:

```text
bindings
proof paths
coverage
unresolved variables
support/opposition
```

not only:

```text
supported / contradicted / unknown
```

---

## 1.3 `role:dimension` is exact authority but not a first-class learned binding

The exact state operator correctly requires:

```text
op:state(subject, dimension, value)
```

but the current neural language pack does not predict `role:dimension`, and the compiler reconstructs it from a uniquely licensed value when possible.

Unique exact completion is a useful optimization. It cannot be the architecture because it fails for:

- projected/unknown dimensions;
- values licensed under multiple dimensions;
- continuous/vector/set-valued dimensions;
- newly learned dimensions;
- generic state queries;
- queries projecting both dimension and value.

### Required repair

`dimension` must be predicted/grounded exactly like other semantic roles and may legally be a variable in query CSIR.

---

## 1.4 Stage-4 entitled state-space projection is mostly absent

Canonical runtime requires:

```text
referent
→ type/facet closure
→ recursively inherited dimensions
→ current state-belief distributions
→ missing/conflicting/stale state
→ capability/resource dependencies
→ applicable mechanisms
```

Current v1 largely has state facts plus a few hard-coded self slots.

### Required repair

Implement ephemeral `StateSpaceProjection` from exact graph closure. Do **not** create `PersonState`, `AnimalState`, `ServerState`, `CEMMSelfState`, etc.

---

## 1.5 `SessionSelf` conflates unrelated semantic layers

Current self tracking compresses:

```text
response_state
interpretation_state
epistemic_state
```

into ordinary semantic self-state.

That conflates:

1. cycle-local control/cognitive status;
2. grounded mutable state of the digital self;
3. target-scoped epistemic assessment;
4. discourse state;
5. learning/frontier state.

A global state such as:

```text
self.epistemic_state = insufficient
```

is especially wrong because insufficiency is normally **about a target**.

### Required repair

Separate:

```text
SelfRuntimeView
semantic self/world state
InterpretationAssessment
EpistemicAssessment(target)
DiscourseCommonGround
FrontierGraph
GoalState
```

---

## 1.6 State/workspace retrieval occurs after query outcome selection

Current query logic can decide `unknown` before building the workspace where self slots are added.

This means debug traces may show relevant self-state that had no opportunity to influence the answer.

### Required repair

State projection/workspace relevance must occur before query execution, following the canonical Stage 3 → 4 → 5–7 → 8 → 9 → 10 order.

---

## 1.7 Parsing has hidden durable side effects

Current parse can invoke autonomous acquisition; unknown forms can default to `concept`, create atoms/designations, and write a new generation.

That violates the persistence boundary and incorrectly equates:

```text
unknown form
```

with:

```text
new semantic concept
```

An unknown form may instead be:

```text
morphology
function word
pronoun/deictic
auxiliary
construction marker
name
typo/noise
lexicalization of known semantics
relation
event
value
concept
```

### Required repair

Interpretation must be pure. Unknown material becomes typed frontier evidence. Durable lexical/semantic acquisition occurs only at authorized learning boundaries.

---

## 1.8 Grammar/function knowledge is accidentally derived from seed examples

The interpreter currently treats literal words appearing in training examples as a privileged function-word set.

This makes seed-corpus composition silently alter grammar authority.

### Required repair

Language packs/models should explicitly represent or learn morphology/construction evidence. Training examples are supervision, not a hidden grammar whitelist.

---

## 1.9 Normal cognition is split into Ask/Learn/Teach modes

The demo defaults to Ask and disables learning.

The canonical cognitive loop should not switch between separate brains/modes for asking versus learning.

Every normal turn should:

```text
observe
interpret
ground
classify discourse force
query and/or assimilate
create frontiers/prediction errors
commit only permitted deltas
respond
```

Explicit reviewed teaching may remain a high-strength evidence mode. Read-only diagnostic execution may remain for tests.

---

## 1.10 Training coverage cannot fix missing semantic expressiveness

Current training is too narrow in several structural dimensions:

- participant-role requirements;
- first-class dimensions;
- open query variables/projections;
- assertion/query/directive contrasts;
- generic/subtype semantics;
- scope/modality/negation;
- explicit no-delta supervision;
- pre-state/post-state transitions;
- partial understanding;
- response-side participant inversion;
- target-scoped epistemics.

Training expansion must happen **after** runtime representations can express these distinctions.

---

# 2. Non-negotiable repair invariants

## 2.1 No phrase-specific cognition

Forbidden:

```python
if text == "how are you": ...
```

Also forbidden in disguised form:

```text
how → SELF_STATE_QUERY
is/are/am → STATE_OPERATOR
ready → self.ready
```

Language contributes evidence/constraints; grounded semantics determine the structure.

---

## 2.2 No referent-specific state schema proliferation

Do not define dimension lists separately for every type.

Use recursive inheritance:

```text
referent
→ direct types/facets
→ parent type/facet closure
→ inherited dimensions/capabilities/resources/mechanisms
```

New types should normally be data/graph additions only.

---

## 2.3 Five operator shapes remain fixed

New competence must compile through:

```text
op:designation
op:type
op:relation
op:state
op:event
```

plus canonical CSIR constructors such as variables/qualifiers/scope where current v1 compression must be restored.

---

## 2.4 Semantic knowledge must not depend on English words

CEMM may know an operational condition before it knows a word for it.

Example:

```text
self communication capability availability = 1.0
self semantic-runtime viability = 0.98
critical blockers = none
```

The English word `ready` is only one possible realization of a compatible semantic pattern.

If `ready` is unknown, the semantic condition still exists.

---

## 2.5 Partial interpretation must not corrupt semantic self-state

Unresolved meaning updates:

```text
PartialMeaning
OpenVariables
InterpretationAssessment
LearningFrontier
ClarificationTarget
```

It must not automatically set:

```text
self = confused
self = broken
self = globally epistemically insufficient
```

---

## 2.6 Epistemic state is target-scoped

Use:

```text
EpistemicAssessment(
  target,
  support,
  opposition,
  sufficiency,
  uncertainty,
  contradiction,
  proof
)
```

A system can know its runtime condition well while failing to ground one unfamiliar word.

---

# 3. Minimal universal state algebra

The irreducible universal element is the **state algebra**, not a universal list of dimensions.

## 3.1 State assignment

```text
StateAssignment
  subject
  dimension
  value | distribution
  qualifiers:
    valid time
    context
    modality
    source/evidence
    support/confidence
```

## 3.2 State transition

```text
StateTransition
  subject
  dimension
  precondition / pre-value
  post-value / delta
  trigger/event
  affected semantic role
  time/context
  mechanism/warrant
  uncertainty
  proof
```

## 3.3 State domain families

Dimensions may use:

```text
categorical
ordered_discrete
continuous
vector_or_manifold
relational
set_valued
process_valued
probabilistic
```

Do not normalize every raw state to 0–1.

## 3.4 Normalized operational assessments

A 0–1 score is appropriate for **derived assessments** when an operational profile defines the dependency function, for example:

```text
capability availability
resource sufficiency
operational viability
confidence/support
risk
```

Example:

```text
communication_capability_score = f(
  runtime_attestation,
  semantic_engine_availability,
  realizer_availability,
  output_adapter_availability,
  resource_sufficiency,
  permission
)
```

The score is semantic/runtime knowledge. `ready` is downstream lexicalization.

---

# 4. Recursive chained entitlement instead of schemas

## 4.1 Entitlement rule

For referent `R`:

```text
direct active types/facets
→ bounded recursive inheritance closure
→ collect dimension entitlements
→ collect capability/resource dependencies
→ collect applicable mechanisms
→ reconcile current state beliefs
→ expose missing/conflicting/stale dimensions
→ StateSpaceProjection(R)
```

## 4.2 Example inheritance

```text
physical_entity
  → position
  → integrity

living_entity
  → inherits physical_entity
  → homeostatic dimensions

animal
  → inherits living_entity
  → organism/cognitive facets

cat
  → inherits animal
```

A cat referent inherits through closure. No copied `cat_state_schema` is created.

## 4.3 Generic semantic relations

Use graph relations/rules equivalent to:

```text
subtype/facet inheritance
entitles dimension
dimension domain/licensing
capability depends on state/resource/capability
mechanism applies to type/facet
```

These are semantic authority data represented through existing graph operators—not new Python classes per domain.

## 4.4 Projection algorithm

```text
project_state_space(R):
  direct = active_types_and_facets(R)
  closure = bounded_recursive_exact_closure(direct)

  dimensions   = union(entitled_dimensions(x) for x in closure)
  capabilities = union(entitled_capabilities(x) for x in closure)
  resources    = union(entitled_resources(x) for x in closure)
  mechanisms   = union(applicable_mechanisms(x) for x in closure)

  for dimension in dimensions:
    retrieve current timeline/claims
    preserve source/time/context
    reconcile support/opposition
    mark missing/conflicting/stale
    keep defaults separate from facts

  return ephemeral StateSpaceProjection
```

Cache entitlement closure by exact authority generation + type/facet closure signature.

---

# 5. Correct self model

## 5.1 Fundamental self identity

`self` is a transport/session-grounded referent.

It is not defined by the language tokens:

```text
I
me
you
assistant
system
```

Those are language/session projections.

## 5.2 Self type/facet chain

Illustrative semantic closure:

```text
participant:self
→ digital cognitive agent
→ software system
→ digital system
→ entity
```

Exact refs are semantic authority IDs; English labels are optional designations.

## 5.3 Runtime observations

Stage-1 providers may observe:

```text
process alive
runtime attestation valid
authority loaded
semantic store reachable
interpreter available
query engine available
response channel available
adapter availability
resource load/connectivity where observable
```

These are evidence—not lexical state words.

## 5.4 Capability assessments

```text
CapabilityAssessment
  capability_ref
  availability_score 0..1
  confidence
  blockers[]
  dependencies[]
  proof
```

Capabilities derive recursively from state/resource/capability dependencies.

## 5.5 Knowing “ready” without knowing `ready`

CEMM may semantically know:

```text
communication capability = 1.0
semantic runtime viability = 0.98
blocking faults = none
```

A derived qualitative projection may be strongly positive.

English realization may later map that to:

```text
ready
working normally
available
able to respond
```

The lexical token is never the semantic source of truth.

---

# 6. Separate five state-like layers

## A. Grounded entity/world state

Examples:

```text
server availability
battery energy
person location
self communication capability
```

Queryable semantic/world state.

## B. Cycle-local cognitive status

Examples:

```text
candidate graph unsettled
interpretation partly resolved
budget exhausted
response plan pending
```

Lives in `CycleState` / `CycleWorkspace`.

## C. Scoped epistemic assessment

Examples:

```text
support for proposition P
meaning of span S unresolved
query variable ?X unbound
two claims conflict
```

## D. Discourse/common-ground state

Examples:

```text
open question
clarification target
commitment
correction/retraction
topic/focus
prior emitted semantics
```

## E. Learning/frontier state

Examples:

```text
unknown form frontier
identity frontier
state-model frontier
construction frontier
causal frontier
realization frontier
```

One turn may update B/C/D/E without changing A.

---

# 7. Utterance force: probing, asserting, commanding

Force must be compositional, not lexical.

Stages 2–8 combine:

```text
surface/morphology
construction evidence
ParticipantFrame
modality/scope
word order/prosody/punctuation as evidence
grounded semantic structure
discourse context
open commitments/questions
```

## 7.1 Assertion / claim

Produces:

```text
proposition
claim occurrence
source
context
epistemic admission candidate
```

It does **not** automatically become world truth.

A user assertion about CEMM's runtime state remains source-attributed and cannot silently override trusted runtime telemetry.

## 7.2 Probe / query

Produces:

```text
information gap
restriction graph
semantic variables
answer projection
response obligation
```

No subject state changes simply because it was queried.

## 7.3 Directive / command / request

Produces:

```text
desired/proposed event or state
directed participant
constraints
goal/operation candidate
```

It does not assert that the event occurred.

Stage 15/16 checks:

```text
capability
permission
resources
risk
goal conflicts
authorization
```

## 7.4 Embedded acts

Examples such as:

```text
Tell me whether the server is available.
If it is available, restart it.
```

must preserve embedded query/directive scope rather than flattening the whole utterance to one intent label.

---

# 8. Query architecture

## 8.1 Query structure

```text
QueryCSIR
  restriction_graph
  variables
  projection
  context/time constraints
  expected answer shape
  discourse source/target
```

## 8.2 Structural examples

Boolean:

```text
restriction: state(server, availability, unavailable)
projection: none
```

Open value:

```text
restriction: state(server, operational_status, ?V)
projection: ?V
```

Open dimension/value:

```text
restriction: state(server, ?D, ?V)
projection: ?D, ?V
```

Relation:

```text
restriction: relation(?X, manages, server)
projection: ?X
```

## 8.3 Query result

```text
QueryResult
  bindings[]
  proof_paths[]
  support/opposition
  coverage
  unresolved_variables
  blocking_frontiers[]
```

Yes/no is only the zero-projection special case.

---

# 9. Response selection must be target-aware

## 9.1 Fully grounded query

Return grounded bindings/proof and only relevant qualification.

## 9.2 Partly resolved query

Preserve known meaning. Answer any independently answerable part. Clarify only the blocking unresolved variable.

## 9.3 Query about unresolved meaning

The target is the semantic/lexical frontier—not self operational state.

Possible Response CSIR:

```text
report unresolved target
report understood surrounding structure if useful
request targeted clarification
```

## 9.4 Assertion

Possible paths:

```text
admit scoped claim
keep attributed only
detect contradiction
request clarification only if needed for admission
acknowledge only when discourse goal warrants
```

## 9.5 Directive

Possible paths:

```text
accept/execute
reject with grounded blocker
request missing binding
report capability limitation
```

## 9.6 Known self-state query

Answer from:

```text
StateSpaceProjection(self)
+ runtime/world observations
+ capability dependency assessment
```

not a global `self.epistemic_state`.

---

# 10. Pre-state/post-state training without causal shortcuts

Do not train only:

```text
text → graph
```

and do not naively train:

```text
text + pre-state → post-state
```

because co-occurrence is not causation.

Use episodes:

```text
TrainingEpisode
  authority_generation
  ParticipantFrame
  context/discourse_before
  relevant StateSpaceProjection before
  EvidenceEnvelope[]

  targets:
    stabilized semantics
    discourse act
    query structure
    epistemic placement
    transition candidate OR NO_TRANSITION
    cognitive/frontier delta
    discourse delta
    admitted world delta if any
    relevant StateSpaceProjection after
    Response CSIR if applicable
```

### Mandatory no-delta supervision

Train cases where:

```text
query → no subject-state mutation
mention → no state mutation
hypothetical → no actual-world mutation
reported claim → no automatic actual-world mutation
failed interpretation → no self-world corruption
prediction → no observation commit
```

---

# 11. Learning architecture

## Tier A — episodic/participant knowledge

Scoped participant/world facts subject to admission/privacy policy.

## Tier B — language/lexicalization/construction

Learn:

```text
surface/form → existing semantic contribution
morphology
deixis
construction
realization
```

Unknown forms belong here first unless stronger evidence supports a new semantic atom.

## Tier C — semantic/state/causal structure

Learn:

```text
new concept/relation
state dimension/domain
inheritance/entitlement
transition mechanism
causal mechanism
capability dependency
```

with stronger competence/review.

## Tier D — continuous parameter artifacts

Immutable/versioned model artifacts.

### Critical rule

Unknown-form detection never directly creates semantic concept authority.

---

# 12. Dependency-ordered implementation phases

## Phase 0 — Contract tests before code changes

Add failing architecture tests for:

1. input/output participant inversion;
2. quoted-speech participant frames;
3. parse/query produces zero hidden writes;
4. unknown token does not default to concept;
5. query produces no world-state delta;
6. variable dimension/value query representation;
7. state projection occurs before query result;
8. one unresolved term cannot globally poison self epistemics;
9. directive does not assert requested effect;
10. assertion is source-attributed before admission;
11. generic/subtype statement is not instance confusion;
12. digital self cannot inherit human states without entitlement;
13. partial interpretation preserves grounded subgraphs;
14. no literal phrase branch in kernel cognition.

**Exit gate:** tests fail for the expected architectural reasons.

---

## Phase 1 — Session/cycle objects + ParticipantFrame

### Implement

```text
SessionContext
ParticipantFrame
CycleState
CycleWorkspace
ContextStack
TemporalFrame
SelfRuntimeView
```

Minimum `ParticipantFrame`:

```text
self_ref
speaker_ref
addressee_ref
audience_refs
conversation_ref
source/channel
```

### Language changes

Replace fixed pronoun refs with structural features equivalent to:

```text
first-person speaker requirement
second-person addressee requirement
third-person/coreference constraints
possessive relation requirement
```

### Files

- `cemm/data/base.json`
- `cemm/interpreter.py`
- small context/runtime artifact module
- `cemm/runtime.py`
- language packs/trainer
- tests

**Exit gate:** swapping speaker/addressee changes grounding without changing lexical authority.

---

## Phase 2 — Pure observation/interpretation

### Refactor

`Interpreter.parse()` becomes side-effect free.

Split:

```text
unknown detection
candidate induction
authorized learning commit
```

Unknown input produces:

```text
UnknownFormEvidence
SemanticKindCandidateSet
LearningFrontier
```

No atom/designation write.

**Exit gate:** DB hash/counts unchanged after read-only parsing/querying unknown text.

---

## Phase 3 — Recursive type/facet + state entitlement

Implement bounded exact closure for:

```text
type/facet ancestors
entitled dimensions
domain constraints
capability/resource dependencies
applicable mechanisms
```

Add generation-keyed caches.

**Exit gate:** a new subtype gains inherited dimensions using data only.

---

## Phase 4 — General state algebra/timelines

Generalize current state handling for:

```text
categorical exclusive
nonexclusive/set-valued
continuous
ordered
probabilistic
vector/process-valued references
```

Keep state claims separate from admitted state beliefs.

Preserve:

```text
source
time
context
validity
support/opposition
contradiction lineage
```

**Exit gate:** state can be missing/stale/conflicting/uncertain/resolved without inventing defaults.

---

## Phase 5 — Split self runtime, semantic self state, epistemics, frontiers

Retire overloaded `SessionSelf` semantics.

Use:

```text
SelfRuntimeView
StateSpaceProjection(self)
ScopedEpistemicAssessment
InterpretationAssessment
FrontierGraph
```

Quarantine automatic `self.confused` behavior.

**Exit gate:** unknown word opens a frontier while self operational capability remains independently available.

---

## Phase 6 — First-class `role:dimension`

Add `role:dimension` to learned structured semantics.

Allow:

```text
grounded dimension
variable dimension
```

Keep value→dimension exact completion only as an optional normalization case.

**Exit gate:** represent and compile:

```text
state(X, knownD, ?V)
state(X, ?D, ?V)
state(X, ?D, knownV)
```

where valid.

---

## Phase 7 — First-class QueryCSIR

Add compressed structures mapping to canonical CSIR:

```text
QueryStructure
SemanticVariable
RestrictionGraph
Projection
```

Do not add one class per question word.

Extend inference to return bindings/proofs/coverage.

**Exit gate:** unseen type/state/relation queries project bindings with no phrase handlers.

---

## Phase 8 — Discourse-force architecture

Replace overly flat intent handling with compositional candidates for:

```text
claim/assertion
query/probe
directive/request
description request
correction/retraction
acknowledgment/greeting
```

These are semantic/discourse patterns, not keywords.

Support embedded acts.

**Exit gate:** same content words can settle into different acts from construction/modality/context.

---

## Phase 9 — Epistemic placement/admission

Implement explicit admission classes equivalent to:

```text
ATTRIBUTED_ONLY
SESSION_PARTICIPANT_FACT
SCOPED_USER_ASSERTED_FACT
CORROBORATION_REQUIRED
HIGH_RISK_NO_AUTO_ADMISSION
HYPOTHETICAL_ONLY
```

**Exit gate:** claim occurrence, admitted belief, state assignment, and authority remain separately inspectable.

---

## Phase 10 — Transitions + prediction error

Implement role-addressed transition previews:

```text
affected referent/role
dimension
preconditions
post delta
mechanism
uncertainty
proof
```

Never positional `subject gets effect A / object gets effect B` shortcuts.

Train pre-state + event + observed post-state, including no-delta cases.

**Exit gate:** state assertion, state query, state transition, and directive remain distinct despite overlapping vocabulary.

---

## Phase 11 — Canonical runtime ordering

Refactor `Runtime.process()` into typed stage artifacts.

No query result before:

```text
participant grounding
state-space projection
semantic stabilization
query construction
epistemic placement
```

No hidden writes before Stage 13.

**Exit gate:** trace proves stage ownership and persistence boundaries.

---

## Phase 12 — Self operational profile and readiness semantics

Seed self type/facet/profile authority—not English state words.

Runtime observation providers produce grounded evidence.

Capability dependency evaluation produces normalized assessments.

NLG learns mappings from semantics to words such as `ready`.

**Exit gate:** remove/disable lexical `ready`; internal operational reasoning remains correct and only realization changes.

---

## Phase 13 — Response CSIR + targeted uncertainty

Response planner consumes:

```text
QueryResult
InterpretationAssessment
EpistemicPlacement
FrontierGraph
DirectiveDecision
CapabilityAssessment
Discourse obligations
```

Replace generic outcome-first responses.

**Exit gate:** self can be operationally well while meaning of `flarble` is unresolved; response addresses the actual target.

---

## Phase 14 — One normal conversation loop

Default runtime is normal cognitive cycle, not Ask mode.

Every turn may create learning candidates/frontiers; policy decides persistence.

Keep explicit modes only for read-only diagnostics and reviewed import/teaching.

**Exit gate:** normal chat learns permitted participant facts, answers, creates frontiers, and preserves authority boundaries without manual mode switching.

---

## Phase 15 — Training curriculum redesign

Train structural contrasts:

1. participant deixis/perspective inversion;
2. identity/type/relation/state/event;
3. dimension/value separation;
4. query variables/projections;
5. assertion/query/directive minimal pairs;
6. generic/subtype/quantified patterns;
7. tense/aspect/time/context;
8. partial interpretation;
9. pre/post transitions + no-delta;
10. discourse/coreference/common ground;
11. Response CSIR → faithful realization;
12. multilingual projection.

Hold out entire paraphrase/construction/entity/perspective families to test generalization.

---

## Phase 16 — Performance/anti-bloat pass

Require:

```text
bounded recursive closure
generation-keyed caches
indexed state timeline lookup
hard-required workspace slots before learned ranking
no whole-store scan
no closure materialization by default
no retraining on ordinary world facts
no persistence of transient candidates
```

**Exit gate:** new concepts/types grow data, not schema or kernel branch count.

---

## Phase 17 — Remove/quarantine inherited shortcuts

Explicitly remove or quarantine:

```text
static USER/SYSTEM lexical identity
global SessionSelf semantic state
dimension omission as primary state path
function-word set derived from examples
autonomous concept defaulting
Ask/Learn/Teach as normal cognition split
generic outcome-only response mapping
post-query workspace/state construction
```

No hidden fallback.

---

# 13. File-level implementation map

## `cemm/data/base.json`

Change:

- reference forms to participant-role requirements;
- remove/quarantine automatic `self.confused` semantics;
- seed minimal meta-relations for inheritance/entitlement/dependency;
- seed self type/facet/profile authority independently of language words;
- keep runtime semantic refs independent of English designations.

Do not add exhaustive lists for every possible referent type.

---

## `cemm/interpreter.py`

Change:

- accept `ParticipantFrame`;
- emit reference requirements/candidates rather than fixed participant identity;
- make parse pure;
- preserve unknown spans as evidence;
- remove seed-example function-word authority;
- preserve stable partial structures when one span is unresolved.

---

## `cemm/acquisition.py`

Split:

```text
unknown-form detection
learning candidate induction
authorized lexical/semantic commit
```

Remove universal `concept` fallback.

---

## `cemm/codec.py`

Add:

- `role:dimension`;
- frame-relative participant sources;
- semantic variable/projection sources;
- discourse-act candidates;
- query structure outputs;
- partial candidate calibration.

Keep neural proposal subordinate to exact compile.

---

## `cemm/compiler.py`

Add:

- variable-aware query compilation;
- frame grounding validation;
- qualifier/scope support required by repaired v1;
- distinction between incomplete assertion and valid open-variable query.

Keep unique state-dimension completion only as safe normalization.

---

## `cemm/store.py`

Prefer generic graph storage.

Add only generic/indexed helpers for:

```text
recursive type/facet closure
entitlement lookup
state timeline retrieval
dependency lookup
scoped claim/epistemic retrieval
```

No table per domain/state family.

---

## `cemm/selfstate.py`

Retire or narrow to transient runtime/cycle concerns.

Semantic self-state must come through `StateSpaceProjection(self)`.

---

## `cemm/workspace.py`

Build relevant workspace before query execution from:

```text
facts
StateSpaceProjection
self runtime observations
query restrictions
frontiers
proof dependencies
recent transitions
discourse commitments
```

Learned ranking cannot hide hard-required semantic slots.

---

## `cemm/inference.py`

Return:

```text
bindings
proofs
coverage
support/opposition
```

without persisting derived closure.

---

## `cemm/response.py`

Consume semantic artifacts, not only generic result labels.

Support:

```text
answer bindings
report current state
report target-scoped uncertainty
clarify exact unresolved binding
acknowledge/qualify claim
respond to directive/capability
```

---

## `cemm/runtime.py`

Become the orchestrator defined by `runtime-core-loop.md`.

No hidden write before Stage 13. No query decision before state projection.

---

## `cemm/web_demo.py`

Default to normal cognitive cycle.

Expose typed stage trace rather than forcing users to choose Ask/Learn/Teach for ordinary interaction.

---

# 14. Mandatory acceptance suites

## A. Participant perspective

```text
input speaker=user, addressee=self:
  I -> user
  you -> self

output speaker=self, addressee=user:
  I -> self
  you -> user
```

Quoted speech uses embedded frame.

## B. Recursive state inheritance

Create a subtype entirely via graph data and verify inherited dimensions appear without code/schema changes.

## C. Semantic readiness without `ready`

1. disable English lexical mapping for `ready`;
2. provide positive runtime/capability evidence;
3. verify internal operational assessment remains positive;
4. allow alternate realization or a realization frontier;
5. learn/re-enable `ready` and verify surface changes without semantic-state changes.

## D. Partial interpretation isolation

Unknown span:

```text
preserves grounded subgraph
creates typed frontier
leaves unrelated self operational state unchanged
```

## E. Discourse-force minimal pairs

Same underlying content represented as:

```text
assertion
query
directive
hypothetical
reported claim
```

must route differently through Stage 8/9/10/15 without phrase branches.

## F. State vs query vs transition

```text
state assertion → claim/admission candidate
state query → projection only
event → transition preview
directive → desired event/goal candidate
```

## G. Self truth-source ordering

Runtime telemetry remains primary current evidence for runtime state; user claims remain source-attributed and cannot silently overwrite it.

## H. Open query projection

Test:

```text
?value
?dimension
?subject
multiple variables
partial bindings
proof retrieval
```

## I. Generic knowledge

Generic class/subtype teaching generalizes to instances without treating a concept atom as a concrete individual.

## J. Persistence boundaries

No unauthorized DB/world/authority write before Stage 13.

---

# 15. Definition of done

The repair is not complete because a handful of chat phrases answer correctly.

It is complete when the runtime can execute:

```text
ParticipantFrame
→ evidence lattice
→ referent grounding
→ recursive type/facet closure
→ entitled state-space projection
→ open compositional CSIR
→ recurrent/partial stabilization
→ discourse act + proposition/query/event/directive
→ scoped epistemic placement
→ query bindings / transition previews / learning frontiers
→ authorized commit only
→ capability/goal reasoning
→ Response CSIR
→ faithful realization
→ common-ground update
```

and a new domain normally requires only:

```text
semantic atoms
+ graph relations
+ recursive inheritance
+ operational profile data
+ evidence
+ learned language mappings/parameters
```

—not new kernel operators, phrase handlers, per-type state schemas, or parallel semantic brains.
