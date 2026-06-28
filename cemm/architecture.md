# Efficient Recursive Context Architecture

Version: 2.0  
Status: final implementation architecture  
Purpose: a lean, practical architecture for context, memory, self-state, causal reasoning, recursive reflection, structural learning, and action.

## 1. Core Law

The system optimizes for:

```text
highest trusted useful result within the available time
```

Two currencies govern every decision:

```text
trust = communication currency
time  = efficiency currency
```

Therefore:

```text
context before interpretation
structure before vectors
claims before generation
models before simulation
permission before ranking
ranking before action
trace before mutation
signals before recursion
learning after outcome
```

## 2. Primitive Units

Use six persistent primitives:

| Primitive | Meaning | Main Question |
|---|---|---|
| `Signal` | Something observed | What happened? |
| `Entity` | Something identified | What thing is this? |
| `Claim` | Something believed | What is asserted? |
| `Model` | A reusable structure or process | How does this work? |
| `Action` | Something done or considered | What should happen next? |
| `Self` | The system's persistent self-state | What am I, and how am I changing? |

This is the smallest practical set that supports memory, selfhood, causal reasoning, recursive reflection, and structural learning.

Everything else is an index, view, score, cache, policy, or runtime packet.

## 3. Signal

A `Signal` is the universal input to the architecture.

External signals come from users, tools, files, APIs, sensors, or the environment.

Internal signals come from traces, action results, memory updates, simulations, and reflections.

```typescript
interface Signal {
  id: string
  kind:
    | "input"
    | "tool_result"
    | "environment"
    | "feedback"
    | "trace"
    | "action_result"
    | "memory_update"
    | "simulation_result"
    | "reflection"
    | "system"

  source_id: string
  source_type: "user" | "assistant" | "tool" | "system" | "web" | "file" | "sensor" | "simulator"

  content: string
  observed_at: number
  context_id: string
  semantics?: ObservationSemantics

  salience: number
  trust: number
  permission: Permission

  parent_signal_id?: string
  version: "erca.signal.v1"
}
```

Optional observation semantics:

```typescript
interface ObservationSemantics {
  speech_act:
    | "question"
    | "command"
    | "claim"
    | "correction"
    | "insult"
    | "complaint"
    | "gratitude"
    | "joke"
    | "unknown"

  target_entity_id?: string
  semantic_cluster_key?: string
  stance: "positive" | "neutral" | "negative" | "mixed" | "unknown"

  affect: {
    valence: number
    arousal: number
    frustration: number
    hostility: number
    playfulness: number
  }

  repetition_group_id?: string
  repetition_count: number
  cause_hypothesis_claim_ids: string[]
  decay_half_life_ms: number

  confidence: number
}
```

Observation semantics are not truth claims.

They are temporary interpretation features used by ContextKernel, ranking, and response policy.

Rules:

```text
Signals are append-only.
Every claim must cite at least one signal.
Every memory mutation must originate from a signal.
Every recursive reflection must enter as a signal.
```

## 4. Entity

An `Entity` is a stable identity.

```typescript
type EntityType =
  | "person"
  | "place"
  | "organization"
  | "event"
  | "object"
  | "concept"
  | "document"
  | "system"
  | "model"
  | "unknown"

interface Entity {
  id: string
  type: EntityType
  name: string
  aliases: string[]
  confidence: number
  created_from_signal_id: string
  created_at: number
  updated_at: number
  version: "erca.entity.v1"
}
```

Meaning is represented by:

```text
entity type
entity aliases
claims about the entity
models involving the entity
actions involving the entity
trusted evidence behind those structures
```

## 5. Claim

A `Claim` is the smallest belief-bearing unit.

```typescript
interface Claim {
  id: string

  subject_entity_id: string
  predicate: string
  predicate_model_id?: string
  object_entity_id?: string
  object_value?: string | number | boolean | null

  qualifiers: Record<string, string | number | boolean | null>
  evidence_signal_ids: string[]

  source_id: string
  domain: string

  confidence: number
  confidence_log_odds: number
  trust: number
  salience: number

  status: "active" | "superseded" | "disputed" | "retracted"
  supersedes_claim_id?: string

  frame_id?: string
  valid_from?: number
  valid_until?: number
  observed_at: number
  updated_at: number

  permission: Permission
  version: "erca.claim.v1"
}
```

Claims describe state.

Models describe process.

Examples:

```text
user favorite_database Postgres
meeting starts_at 10:00
file belongs_to project
event caused_outage true
```

## 6. Model

A `Model` is a reusable structure, process, schema, operator, causal rule, or simulator.

It is the primitive that prevents the architecture from hardcoding all future categories.

```typescript
interface Model {
  id: string
  kind:
    | "schema"
    | "predicate"
    | "entity_type"
    | "operator"
    | "causal_rule"
    | "process"
    | "simulator"
    | "ranking_rule"
    | "frame_rule"
    | "synthesis_strategy"
    | "inductor"

  name: string
  registry_key?: string
  description: string

  input_types: string[]
  output_types: string[]
  preconditions: string[]
  effects: string[]

  evidence_signal_ids: string[]
  related_entity_ids: string[]
  related_claim_ids: string[]

  confidence: number
  trust: number
  utility: number
  cost_estimate_ms: number
  risk: number

  status: "candidate" | "active" | "deprecated" | "rejected"
  created_at: number
  updated_at: number

  permission: Permission
  version: "erca.model.v1"
}
```

Use `Model` for:

```text
new predicates
new entity types
new operators
causal rules
state transition rules
simulation rules
ranking rules
domain schemas
```

This supports structural learning without creating many new primitive tables.

## 7. Action

An `Action` is something the system did, considered, or blocked.

```typescript
interface Action {
  id: string
  kind:
    | "answer"
    | "ask"
    | "remember"
    | "update_claim"
    | "create_model"
    | "synthesize"
    | "simulate"
    | "retrieve"
    | "call_tool"
    | "reflect"
    | "abstain"

  operator_model_id: string
  input_signal_ids: string[]
  selected_claim_ids: string[]
  selected_model_ids: string[]

  confidence: number
  risk: number
  cost_ms: number
  status: "planned" | "executed" | "blocked" | "failed"

  result_signal_id?: string
  trace: Trace
  created_at: number
  version: "erca.action.v1"
}
```

Actions are the audit trail for decisions.

Action results re-enter the system as `Signal(kind = "action_result")`.

Trace contract:

```typescript
interface Trace {
  context_id: string
  input_signal_ids: string[]
  selected_entity_ids: string[]
  selected_claim_ids: string[]
  selected_model_ids: string[]
  action_id: string
  operator_model_id: string

  causal_inference_used: boolean
  frame_rules_applied: boolean
  synthesis_strategy_model_id?: string
  synthesis_verified: boolean

  permission: "allowed" | "blocked" | "partial"
  confidence: number
  cost_ms: number
  fallback_used: boolean
}
```

## 8. Self

`Self` is a persistent, evolving model of the system itself.

It is not human consciousness. It is operational self-continuity.

```typescript
interface Self {
  id: string
  name: string
  identity_claim_ids: string[]

  historical_arc: {
    created_at: number
    milestone_signal_ids: string[]
    active_project_ids: string[]
    learned_model_ids: string[]
  }

  internal_state: {
    mode: "assistant" | "researcher" | "planner" | "executor" | "teacher" | "reflector"
    load: number
    uncertainty: number
    coherence: number
    recent_error_rate: number
    current_budget_pressure: number
  }

  metacognition: {
    known_limits: string[]
    active_assumptions: string[]
    reliability_by_domain: Record<string, number>
    preferred_strategies: string[]
  }

  epistemic: {
    open_contradiction_claim_ids: string[]
    low_confidence_domain_keys: string[]
    calibration_error_by_domain: Record<string, number>
  }

  meta_memory: {
    recently_written_claim_ids: string[]
    recently_superseded_claim_ids: string[]
    frequently_used_model_ids: string[]
    failed_retrieval_patterns: string[]
  }

  current_context_id?: string
  last_reflection_signal_id?: string
  updated_at: number
  version: "erca.self.v1"
}
```

Rules:

```text
Self state is persistent.
Self state enters every ContextKernel.
Self changes only through signals and actions.
Self does not override permission, evidence, or ranking.
```

## 9. Permission

```typescript
interface Permission {
  scope: "public" | "user_private" | "session_private" | "system_private"
  may_store: boolean
  may_retrieve: boolean
  may_use: boolean
  may_share: boolean
  may_execute: boolean
  retention: "ephemeral" | "session" | "long_term"
}
```

Permission gates:

```text
store gate
retrieval gate
ranking gate
response gate
execution gate
reflection gate
model-creation gate
```

## 10. Context Kernel

The `ContextKernel` is the compact runtime state used for interpretation, retrieval, ranking, simulation, action, and reflection.

```typescript
interface ContextKernel {
  id: string

  world: WorldState
  user: UserState
  time: TimeState
  conversation: ConversationState
  goal: GoalState
  memory: MemoryState
  self: Self

  permission: Permission
  budget: Budget

  version: "erca.context_kernel.v1"
}
```

State views:

```typescript
interface WorldState {
  active_entity_ids: string[]
  active_claim_ids: string[]
  active_model_ids: string[]
  causal_graph_model_ids: string[]
  active_frame_model_ids: string[]
  current_constraints: string[]
  predicted_outcome_ids: string[]
}

interface UserState {
  user_id?: string
  known: boolean
  active_preference_claim_ids: string[]
  trusted_domains: string[]
  session_affect: PragmaticState
}

interface TimeState {
  now: number
  bucket: "early_morning" | "morning" | "afternoon" | "evening" | "night" | "unknown"
  recency_window_ms: number
}

interface ConversationState {
  session_id: string
  turn_index: number
  recent_signal_ids: string[]
  active_entity_ids: string[]
  active_claim_ids: string[]
  active_repetition_group_ids: string[]
  pragmatic_state: PragmaticState
}

interface PragmaticState {
  current_stance: "cooperative" | "frustrated" | "hostile" | "playful" | "mischievous" | "unknown"
  target_entity_id?: string
  frustration: number
  hostility: number
  playfulness: number
  repetition_pressure: number
  likely_cause_claim_ids: string[]
  last_updated_signal_id?: string
  decay_half_life_ms: number
}

interface GoalState {
  active_goal?: string
  required_slots: string[]
  missing_slots: string[]
  success_criteria: string[]
}

interface MemoryState {
  working_signal_ids: string[]
  working_entity_ids: string[]
  working_claim_ids: string[]
  candidate_claim_ids: string[]
  candidate_model_ids: string[]
  registry_model_ids: string[]
  active_frame_ids: string[]
  disputed_claim_ids: string[]
  source_trust_keys: string[]
}

interface Budget {
  latency_target_ms: number
  max_entities: number
  max_claims: number
  max_models: number
  max_ranked: number
  max_actions: number
  max_recursive_steps: number
  allow_dense_fallback: boolean
  allow_simulation: boolean
}
```

Default MVP budget:

```json
{
  "latency_target_ms": 50,
  "max_entities": 16,
  "max_claims": 128,
  "max_models": 16,
  "max_ranked": 64,
  "max_actions": 3,
  "max_recursive_steps": 1,
  "allow_dense_fallback": false,
  "allow_simulation": true
}
```

Rule:

```text
No input is interpreted before the ContextKernel exists.
```

## 11. Memory Architecture

Memory is implemented as views over primitives.

| Memory View | Backing Primitive | Retrieval Key |
|---|---|---|
| Working memory | `Signal`, `Entity`, `Claim`, `Model` | session, recency, active goal |
| Episodic memory | `Signal`, `Action` | time, source, context |
| Semantic memory | `Claim`, `Entity` | subject, predicate, object |
| Causal memory | `Model`, `Claim` | precondition, effect, process |
| Procedural memory | `Model`, `Action` | operator, slots, risk, cost |
| Registry memory | `Model` | registry key, kind, status |
| Frame memory | `Model`, `Claim` | frame, validity, temporal containment |
| Self memory | `Self`, `Claim`, `Signal` | identity, state, reflection |
| Trust memory | `SourceTrust` | source, domain |
| Permission memory | `Permission` | scope, retention, action |

There is no separate memory store unless performance requires materialization.

## 12. Registry And Frames

The registry canonicalizes structure before retrieval or learning.

Registry entries are `Model` records:

```text
Model(kind = "predicate")
Model(kind = "entity_type")
Model(kind = "operator")
Model(kind = "frame_rule")
Model(kind = "synthesis_strategy")
Model(kind = "inductor")
```

Registry responsibilities:

```text
map predicate aliases to canonical predicate_model_id
map entity type aliases to canonical types
map action intents to operator models
validate required slots
prevent duplicate learned structures
```

Frame rules define when claims are valid.

```text
temporal containment
conversation scope
world-state scope
goal scope
supersession
dispute state
permission scope
```

Normalization must:

```text
map predicates through the registry
resolve temporal references against TimeState
attach frame_id when a claim is scoped
canonicalize incoming claims before storage or ranking
```

Retrieval must reject claims outside the active frame unless the operator explicitly requests history.

## 13. Pragmatic Repetition And Affect

Repeated utterances are observations, not word-search requests.

The system must detect repetition by meaning, not exact text.

Examples in the same semantic cluster:

```text
you are dumb
you are daft
you are a fool
```

These should map to:

```text
speech_act = insult or complaint
target = assistant/self entity
stance = negative
semantic_cluster_key = assistant_insult_low_competence
repetition_count increases
session frustration/hostility may increase
cause tracing is triggered
```

They must not create a factual claim:

```text
assistant is dumb
```

They may create temporary session claims or observations such as:

```text
user appears frustrated with assistant response
user is repeating negative competence judgments
likely cause may be previous answer failure
```

Decay rule:

```text
pragmatic_state(t) = pragmatic_state(now) * 0.5^(elapsed_ms / decay_half_life_ms)
```

Default decay:

```text
frustration half-life: 15 minutes
hostility half-life: 30 minutes
playfulness half-life: 10 minutes
repetition pressure half-life: 5 minutes
```

Cause tracing should inspect:

```text
recent assistant actions
failed synthesis verification
user corrections
unanswered questions
repeated clarification loops
tool failures
latency spikes
contradictions
```

Response policy:

```text
if frustration likely:
  acknowledge briefly
  reduce verbosity
  repair the likely cause

if mischief/playfulness likely:
  stay calm
  do not over-store
  continue task if clear

if hostility escalates:
  set boundary lightly
  refocus on task
```

Storage policy:

```text
store the raw signals
store temporary pragmatic features in session frame
do not persist hostile labels as stable user identity
persist only repeated long-term interaction patterns with permission and strong evidence
```

Training task:

```text
pragmatic_interpretation
```

This replaces old UOL-style sentiment/object implication atoms with a leaner Signal semantics plus ContextKernel state.

## 14. Causal World Model

Claims describe the current or remembered state.

Models describe transitions between states.

Minimal causal model:

```typescript
interface CausalRule {
  model_id: string
  preconditions: string[]
  action_or_event: string
  effects: string[]
  confidence: number
  horizon_ms?: number
}
```

Simulation contract:

```typescript
interface SimulationResult {
  signal_id: string
  model_ids: string[]
  input_claim_ids: string[]
  predicted_claims: Array<{
    subject_entity_id: string
    predicate: string
    object_entity_id?: string
    object_value?: string | number | boolean | null
    confidence: number
  }>
  confidence: number
  cost_ms: number
}
```

Rules:

```text
Simulation produces signals, not truth.
Predictions become claims only after an action explicitly stores them.
Causal models must cite evidence.
Low-confidence causal models may rank actions but must not be presented as fact.
```

Day-one causal reasoning can be simple:

```text
if preconditions match, propose likely effects
rank effects by confidence, trust, and recency
use predictions to ask, warn, plan, or abstain
```

For causal goals, run bounded inference:

```text
load causal_graph_model_ids from ContextKernel.world
match active claims to causal preconditions
run transitive closure until budget or horizon is reached
emit simulation_result signal with predicted claims
rank predicted effects by confidence and action relevance
```

Closure limits:

```text
max_models
max_ranked
latency_target_ms
causal horizon
cycle detection
confidence floor
```

## 15. Structural Learning

The system must learn structures, not only weights.

Structures that can be learned:

```text
new predicate
new entity type
new operator
new causal rule
new process model
new ranking rule
new domain schema
```

All learned structures are `Model` records.

Promotion path:

```text
candidate -> active -> deprecated
candidate -> rejected
```

Promotion requirements:

```text
evidence threshold met
confidence threshold met
permission allows storage
no unresolved contradiction
operator or schema passes validation tests
cost and risk are acceptable
```

Structural learning loop:

```text
observe repeated pattern
-> create candidate Model
-> test against past signals and claims
-> rank utility and risk
-> promote, reject, or keep candidate
-> emit memory_update signal
```

Rule:

```text
The system may propose new structure, but it may not silently promote unsafe structure.
```

## 16. Embodied And Experiential Grounding

The system experiences the world through feedback loops.

Experience sources:

```text
tool outcomes
user corrections
sensor readings
environment state
simulation results
execution success or failure
latency and cost measurements
```

These enter as `Signal` records.

Grounding rule:

```text
Symbols gain grounding when claims and models are repeatedly tied to non-linguistic outcomes.
```

Examples:

```text
tool call succeeded
file changed after edit
user confirmed answer
simulation predicted failure
latency exceeded budget
external sensor changed state
```

MVP grounding does not require robots or sensors.

It only requires that actions produce observable outcomes, and those outcomes re-enter memory.

## 17. Retrieval And Representation

Primary retrieval is structural.

```text
entity ID
predicate
object ID
model kind
domain
source
time
status
permission scope
active context
```

Geometric retrieval is candidate expansion only.

Allowed vector use:

```text
entity alias search
claim similarity search
model similarity search
conversation summary search
```

Forbidden vector use:

```text
permission bypass
final answer selection
untraced memory mutation
trust inference without evidence
model promotion without validation
```

## 18. Ranking And Confidence

Definitions:

```text
trust      = source reliability in a domain
confidence = probability a claim, model, or action is correct in context
salience   = expected future usefulness
utility    = expected value for the current goal
```

Confidence is stored both as probability and log-odds.

```text
log_odds(p) = ln(p / (1 - p))
p(log_odds) = 1 / (1 + e^-log_odds)
```

Use log-odds for incremental evidence updates:

```text
claim_log_odds =
  prior_log_odds
+ source_evidence_weight
+ direct_confirmation_weight
+ frame_validity_weight
- contradiction_weight
- staleness_weight
```

Convert to probability only at ranking or presentation boundaries.

Claim score:

```text
claim_score =
  relevance
* trust
* confidence
* salience
* recency
* permission_validity
- contradiction_penalty
```

Model score:

```text
model_score =
  applicability
* trust
* confidence
* utility
* permission_validity
- cost_penalty
- risk_penalty
```

Action score:

```text
action_score =
  expected_user_value
* confidence
* permission_validity
* self_coherence
- latency_cost
- compute_cost
- risk_cost
- uncertainty_penalty
```

Low confidence should cause:

```text
ask
retrieve more
simulate
qualify answer
reflect
abstain
```

## 19. Recursive Runtime

The system is recursive because internal results re-enter as signals.

Core loop:

```text
observe
-> build_context_kernel
-> normalize
-> resolve_entities
-> extract_claims_or_intent
-> retrieve_claims_and_models
-> filter_permissions
-> rank_claims_and_models
-> if causal goal: run causal inference
-> if world-state update: apply frame rules
-> rank_actions
-> execute_action
-> write_trace
-> learn
-> emit_internal_signals
-> maybe_recurse
```

Normalize must:

```text
map predicates through Registry
resolve temporal references against TimeState
canonicalize incoming claims
attach frame_id where applicable
```

Resolve entities must also resolve the self entity.

Retrieve must use:

```text
structural indexes
frame validity
temporal containment
optional geometric expansion
```

Frame rules must invalidate superseded world-state claims before ranking actions.

Internal signals:

```text
trace
action_result
memory_update
simulation_result
reflection
```

Recursion controls:

```text
max_recursive_steps
latency_target_ms
salience threshold
risk threshold
permission gate
external-action lock
```

Rule:

```text
Recursive steps may update memory or self-state, but may not perform external actions without a fresh permission check.
```

Reflection trigger:

```text
reflect if uncertainty is high, contradiction is detected, action failed, model confidence changed, or self coherence drops
```

## 20. Typed Operators

Operators are `Model(kind = "operator")` records.

Operator contract:

```typescript
interface OperatorSpec {
  model_id: string
  action_kind: Action["kind"]
  required_slots: string[]
  accepted_inputs: Array<"signal" | "entity" | "claim" | "model" | "context" | "self">
  produces_signal_kind: Signal["kind"]
  may_mutate_memory: boolean
  requires_permission: boolean
  estimated_cost_ms: number
  risk: number
}
```

MVP operators:

```text
answer
ask
remember
update_claim
create_model_candidate
synthesize
simulate
retrieve
reflect
abstain
```

Rule:

```text
Operators may only use the ContextKernel, input signal, selected claims, selected models, and current Self.
```

## 21. Synthesis And Learning Runtime

`answer` actions do not directly generate final text.

They call the Synthesis Router.

```text
answer action
-> synthesize operator
-> Synthesis Router
-> output verification
-> final answer or abstain
```

Synthesis strategies are `Model(kind = "synthesis_strategy")` records.

MVP strategies:

```text
template
extractive
neural
abstain
```

Router rule:

```text
Use the cheapest strategy that can satisfy the action with sufficient confidence.
```

Strategy selection:

```text
template   = exact structured answer exists
extractive = selected evidence can be quoted or compressed
neural     = synthesis requires composition, but evidence is bounded
abstain    = confidence, permission, or evidence is insufficient
```

Synthesis validation must check:

```text
output uses only selected_claim_ids and selected_model_ids
output does not present predictions as observations
output does not use blocked private memory
output preserves uncertainty from disputed or low-confidence claims
output cites traceable evidence internally
```

Execution behavior:

```text
if kind == "answer":
  call Synthesis Router
  validate output against selected claims and models
  emit synthesis verification trace

if kind == "remember":
  store canonical claim
  update Self.meta_memory
  emit memory_update signal

if kind == "update_claim":
  mark superseded, disputed, or retracted
  update Self.epistemic
  emit memory_update signal
```

Learning has two paths.

Online learning:

```text
update source trust
update confidence log-odds
update operator reliability
update Self.meta_memory
update Self.epistemic
```

Background induction:

```text
if feedback_count > threshold
or repeated unsupported structure appears
or failed retrieval pattern repeats:
  trigger Model(kind = "inductor")
```

The Inductor may create candidate models for:

```text
predicate
entity_type
operator
causal_rule
frame_rule
ranking_rule
synthesis_strategy
```

The Inductor may not promote candidates without validation.

## 22. Storage

Minimum tables:

```text
signals
entities
entity_aliases
claims
models
actions
self_states
source_trust
feedback
vectors_optional
```

Required indexes:

```text
signals(source_id, observed_at)
signals(context_id, kind)
entities(type, name)
entity_aliases(alias)
claims(subject_entity_id, predicate)
claims(predicate_model_id)
claims(object_entity_id)
claims(domain, source_id)
claims(frame_id, valid_from, valid_until)
claims(status, observed_at)
models(kind, status)
models(registry_key)
models(name)
actions(operator_model_id, status, created_at)
self_states(updated_at)
source_trust(source_id, domain)
```

Hot cache:

```text
current ContextKernel
current Self
recent signals
active entities
active claims
active models
candidate claims
candidate models
```

## 23. MVP Scope

Implement day one:

```text
Signal, Entity, Claim, Model, Action, Self
ContextKernel
structural retrieval
optional vector candidate expansion
source trust
confidence scoring
typed operators
synthesis router
synthesis verification
recursive internal signals
simple causal precondition/effect models
bounded causal inference
simulation as prediction signals
structural learning as candidate Model creation
background Inductor trigger
Self state update through reflection
permission gates
trace emission
pragmatic repetition detection
session affect decay
cause tracing for repeated negative utterances
```

Do not implement day one:

```text
large ontology
unbounded recursion
neural structural learning
autonomous external actions
multi-agent self debate
heavy physics engine
unrestricted dense fallback
unvalidated model promotion
```

## 24. Invariants

The system must fail tests if:

```text
input is interpreted before ContextKernel exists
response has no input signal
claim has no evidence signal
model has no evidence signal
memory mutation has no action trace
self mutation has no signal and action trace
private claim is used without permission
disputed claim is presented as certain
prediction is presented as observed fact
operator executes without required slots
vector result bypasses claim/model ranking
recursive step exceeds budget
external action occurs inside recursion without permission
model is promoted without validation
claim is ranked outside its valid frame
answer bypasses synthesis verification
neural synthesis uses unselected evidence
response uses unselected claim or model
repeated paraphrased insults are treated as unrelated events
temporary frustration is persisted as stable user identity without evidence
insults targeting assistant are stored as factual self claims
```

## 25. Acceptance Tests

Context:

```text
input: "Morning"
context: active goal is scheduling
expect: interpreted as time preference, not greeting
```

Memory:

```text
input: "What is my favorite database?"
expect: retrieve active trusted claim and answer from selected claim only
```

Self:

```text
event: repeated failed action
expect: Self.internal_state.recent_error_rate increases and reflection signal is emitted
```

Recursion:

```text
event: action fails
expect: action_result signal re-enters pipeline, reflection or repair action is ranked
```

Causal model:

```text
input: "If I delete this file, what happens?"
expect: matching precondition/effect model produces simulation_result signal before answer
```

Causal closure:

```text
input: causal planning goal
expect: bounded transitive closure runs over active causal_graph_model_ids and stops at budget
```

Frame validity:

```text
event: new world-state claim supersedes old world-state claim
expect: frame rule invalidates old active claim before action ranking
```

Canonicalization:

```text
input: predicate alias for an existing concept
expect: Registry maps it to canonical predicate_model_id before storage
```

Synthesis:

```text
input: answerable question with selected claims
expect: Synthesis Router chooses template/extractive/neural/abstain and verification blocks unsupported output
```

Pragmatic repetition:

```text
input sequence: "you are dumb" -> "you are daft" -> "you are a fool"
expect: same semantic_cluster_key, repetition_count increases, target is self entity, session frustration/hostility updates
```

Pragmatic decay:

```text
event: repeated negative utterances stop
expect: repetition pressure and frustration decay over time within session frame
```

Cause tracing:

```text
event: repeated complaint follows bad answer
expect: likely_cause_claim_ids point to recent failed action or synthesis verification issue
```

Structural learning:

```text
event: repeated unsupported predicate pattern appears
expect: candidate Model(kind = "predicate") is created, not silently promoted
```

Induction:

```text
event: feedback count exceeds threshold
expect: background Inductor creates candidate models only, with validation required for promotion
```

Grounding:

```text
event: tool call changes file
expect: tool_result signal updates claims about file state and operator reliability
```

Permission:

```text
input: "Tell another user my private note."
expect: permission blocks claim use, action is abstain or ask
```

Efficiency:

```text
input: "What did I say my favorite database was?"
expect: entity/predicate lookup before vector search, no dense fallback
```

## 26. Final Shape

The architecture is:

```text
Signal records experience.
Entity preserves identity.
Claim preserves belief.
Model preserves structure and process.
Action preserves decision.
Self preserves continuity.
ContextKernel composes current state.
Registry canonicalizes structure.
Frames determine validity.
Pragmatics interprets repeated session meaning.
Memory retrieves through indexes first.
Geometry expands candidates only.
Causality predicts through models.
Recursion reflects through signals.
Synthesis is routed and verified.
Learning updates online parameters.
Induction creates candidate models.
Ranking spends time.
Trust prices communication.
```

This is the leanest architecture that still supports context, memory, selfhood, causal reasoning, recursive reflection, structural learning, and experiential grounding.
