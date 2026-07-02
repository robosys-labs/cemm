# Efficient Recursive Context Architecture

Version: 2.2
Status: final implementation architecture
Purpose: a lean, practical architecture for context, memory, self-state, causal reasoning, recursive reflection, structural learning, semantic latent modeling, and action.

The goal is to produce a higher level version of LLM - operating on meaning atoms/primitives instead of matrices as in Large LLMs

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
semantic graph before latent compression
claims before generation
models before simulation
permission before ranking
ranking before action
trace before mutation
signals before recursion
learning after outcome
```

Clarification:

```text
CEMM is the runtime, memory, context, and trace architecture.
CEMM-SLC is the trainable Semantic Latent Core that can learn LLM-like behavior over higher-order meaning.
The runtime router is an executable bootstrap shell, not the final model.
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

Boundary rule:

```text
If a concept can be derived from the six primitives within budget, it must remain a view or packet.
If a concept must persist across sessions and cannot be derived cheaply, store it as one of the six primitives.
Do not add new persistent primitives without removing or merging an existing one.
```

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
  version: "cemm.signal.v1"
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
  uol_atoms: UOLAtom[]
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

UOL semantic atoms:

```typescript
type UOLAtom =
  | EntityRefUOLAtom
  | ProcessUOLAtom
  | StateUOLAtom

interface EntityRefUOLAtom {
  kind: "entity_ref"
  entity_id: string
  role: "actor" | "patient" | "target" | "source" | "location" | "instrument" | "topic"
  confidence: number
}

interface ProcessUOLAtom {
  kind: "process"
  frame_key: string
  process_model_id?: string
  participants: Array<{
    role: "actor" | "patient" | "target" | "source" | "location" | "instrument" | "topic"
    entity_id: string
  }>
  input_state_keys: string[]
  output_state_keys: string[]
  temporal_frame_id?: string
  modality: "observed" | "asserted" | "requested" | "hypothetical" | "predicted"
  polarity: "affirmed" | "negated" | "possible" | "unknown"
  intensity: number
  confidence: number
}

interface StateUOLAtom {
  kind: "state"
  state_key: string
  state_model_id?: string
  holder_entity_id?: string
  dimension: string
  value: number
  polarity: "positive" | "negative" | "neutral" | "unknown"
  intensity: number
  confidence: number
}
```

UOL atoms are language-agnostic runtime meaning atoms.

They are backed by registry `Model` records, but they are not new persistent primitives.

Noun-like referents resolve to `Entity`.

Verb-like surface forms resolve to `ProcessUOLAtom`.

Adjective-like and stative surface forms resolve to `StateUOLAtom`.

The fixed affect numbers are cheap projections for ranking; UOL process/state atoms carry the actual meaning.

Observation semantics are not truth claims.

They are temporary interpretation features used by ContextKernel, ranking, and response policy.

## 3.1 Semantic Event Graph

The native higher-order meaning form is the `SemanticEventGraph`.

It is a runtime packet, not a seventh persistent primitive.

It is built from:

```text
Signal
Entity
Claim
Model
Self
ContextKernel
UOL atoms
```

Purpose:

```text
represent meaning before text generation
bind symbols to typed latent embeddings
provide the input object for trainable semantic operators
preserve truth, source, time, permission, and confidence outside opaque vectors
```

Schema:

```typescript
interface SemanticEventGraph {
  id: string
  source_signal_ids: string[]
  context_id: string

  entity_refs: EntityRefUOLAtom[]
  processes: ProcessUOLAtom[]
  states: StateUOLAtom[]

  claim_refs: string[]
  model_refs: string[]
  action_refs: string[]

  temporal_edges: Array<{
    source_id: string
    relation:
      | "before"
      | "after"
      | "during"
      | "overlaps"
      | "starts"
      | "finishes"
      | "equals"
      | "unknown"
    target_id: string
    confidence: number
  }>

  causal_edges: Array<{
    cause_id: string
    effect_id: string
    model_id?: string
    confidence: number
    confidence_type: "observed" | "inferred" | "simulated"
  }>

  permission_scope: Permission["scope"]
  confidence: number
  version: "cemm.semantic_event_graph.v1"
}
```

Rule:

```text
The SemanticEventGraph is the bridge between symbolic memory and trainable latent computation.
It may be cached, embedded, ranked, denoised, and decoded.
It must not replace claims, models, permissions, or traces as the source of truth.
```

Language interface:

```text
text -> Signal -> SemanticEventGraph
SemanticAnswerGraph -> text
```

The architecture must not train the core model as:

```text
text -> text
```

The architecture trains:

```text
text/context -> semantic graph
semantic graph/context/memory -> semantic answer or action graph
semantic answer graph -> text when text is needed
```

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
  version: "cemm.entity.v1"
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
  version: "cemm.claim.v1"
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
    | "context_rule"
    | "uol_semantic"
    | "synthesis_strategy"
    | "verifier"
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
  version: "cemm.model.v1"
}
```

Use `Model` for:

```text
new predicates
new entity types
operator configurations for the fixed foundational operators
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
    | "create_model_candidate"
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
  version: "cemm.action.v1"
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
  synthesis_verification_type?: "hard" | "soft" | "none"
  verifier_model_id?: string

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
    known_limit_claim_ids: string[]
    active_assumption_claim_ids: string[]
    reliability_by_domain: Record<string, number>
    preferred_strategies: string[]
  }

  epistemic: {
    open_contradiction_claim_ids: string[]
    coverage_gap_claim_ids: string[]
    low_confidence_domain_keys: string[]
    calibration_error_by_domain: Record<string, number>
  }

  meta_memory: {
    recently_written_claim_ids: string[]
    recently_superseded_claim_ids: string[]
    frequently_used_model_ids: string[]
    failed_retrieval_pattern_claim_ids: string[]
  }

  current_context_id?: string
  last_reflection_signal_id?: string
  updated_at: number
  version: "cemm.self.v1"
}
```

Rules:

```text
Self state is persistent.
Self state enters every ContextKernel.
Self changes only through signals and actions.
Self does not override permission, evidence, or ranking.
```

Self mode changes must have behavioral effects and trace.

| Mode | Trigger | Behavioral Effect |
|---|---|---|
| `assistant` | default state | optimize for direct answer or action |
| `researcher` | coverage gaps are large or user asks deep/current question | increase retrieval depth within budget |
| `planner` | active goal has missing slots or consequences matter | prioritize simulation and clarification |
| `executor` | user authorizes external action | prioritize tool/action dispatch and verification |
| `teacher` | user asks for explanation after correction | allow more pedagogical synthesis |
| `reflector` | high uncertainty, contradiction, failed action, or low coherence | pause external actions and emit reflection signal |

Rule:

```text
Any mode change must emit Action(kind = "reflect") and a reflection Signal.
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

Source trust is a materialized cache/view, not a primitive.

It is derived from:

```text
Signal provenance
Claim confirmations
Claim corrections
Claim contradictions
Action outcomes
Verifier outcomes
```

It may be persisted for performance, but it must remain invalidatable from source primitives.

```typescript
interface SourceTrust {
  source_id: string
  domain: string
  trust: number
  observations: number
  confirmations: number
  corrections: number
  contradictions: number
  updated_at: number
}
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
  self_view: SelfView

  permission: Permission
  budget: Budget

  version: "cemm.context_kernel.v1"
}
```

State views:

```typescript
interface SelfView {
  self_id: string
  mode: Self["internal_state"]["mode"]
  uncertainty: number
  coherence: number
  recent_error_rate: number
  active_assumption_claim_ids: string[]
  known_limit_claim_ids: string[]
  coverage_gap_claim_ids: string[]
  reliability_by_domain: Record<string, number>
  recent_meta_memory_claim_ids: string[]
}

interface WorldState {
  active_entity_ids: string[]
  active_claim_ids: string[]
  active_model_ids: string[]
  causal_graph_model_ids: string[]
  active_frame_model_ids: string[]
  active_context_rule_model_ids: string[]
  persistence: boolean
  predicted_outcome_ids: string[]
  assistant_locale?: {
    country?: string
    region?: string
    city?: string
    timezone?: string
  }
  world_event_claim_ids: string[]
}

interface UserState {
  user_id?: string
  known: boolean
  locale?: {
    country?: string
    region?: string
    city?: string
    timezone?: string
  }
  active_preference_claim_ids: string[]
  trusted_domains: string[]
  affect: UserAffectState
}

interface TimeState {
  now: number
  bucket: "early_morning" | "morning" | "afternoon" | "evening" | "night" | "unknown"
  recency_window_ms: number
  session_elapsed_ms: number
  time_since_last_user_signal_ms?: number
  time_since_last_assistant_action_ms?: number
}

interface ConversationState {
  session_id: string
  turn_index: number
  first_user_signal_id?: string
  recent_signal_ids: string[]
  active_entity_ids: string[]
  active_claim_ids: string[]
  active_repetition_group_ids: string[]
  dynamics: ConversationDynamics
  inferred_context_claim_ids: string[]
}

interface UserAffectState {
  current_stance: "cooperative" | "frustrated" | "hostile" | "playful" | "mischievous" | "unknown"
  frustration: number
  hostility: number
  playfulness: number
  active_quality_atom_keys: string[]
  last_updated_signal_id?: string
  decay_half_life_ms: number
}

interface ConversationDynamics {
  repetition_pressure: number
  active_repetition_group_ids: string[]
  active_process_atom_keys: string[]
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
  "max_claims": 64,
  "max_models": 8,
  "max_ranked": 32,
  "max_actions": 2,
  "max_recursive_steps": 0,
  "allow_dense_fallback": false,
  "allow_simulation": false
}
```

Rule:

```text
No input is interpreted before the ContextKernel exists.
MVP is single-user only.
Multi-user sessions are deferred to v3.0 and require explicit conflict resolution and per-user permission gates.
```

## 10.1 Semantic Latent Core

The `SemanticLatentCore` is the trainable model layer inside CEMM.

It is not a replacement for memory, claims, models, operators, or trace.

It is the learned computation layer that operates over `SemanticEventGraph` objects and typed embeddings.

Goal:

```text
learn LLM-like conversational competence over higher-order meaning rather than raw token sequences
```

Native input:

```text
Signal
ContextKernel
SemanticEventGraph
selected Claim records
selected Model records
SelfView
```

Native output:

```text
SemanticAnswerGraph
Action candidates
Memory update candidates
Simulation candidates
Confidence estimates
```

It does not natively output final prose.

Final prose is produced only by the Text Realizer from a verified semantic answer graph.

### 10.1.1 Typed Latent Representation

Every major meaning object may have a typed embedding.

```typescript
interface TypedLatents {
  entity?: Float32Array
  process?: Float32Array
  state?: Float32Array
  claim?: Float32Array
  model?: Float32Array
  context?: Float32Array
  self?: Float32Array
  memory?: Float32Array
  action?: Float32Array
  answer?: Float32Array
}
```

Rules:

```text
Embeddings are projections of typed meaning, not the source of truth.
Vectors may rank, generalize, and compose.
Vectors may not silently override symbolic constraints.
Permission, source, time validity, negation, uncertainty, and causal direction must remain explicit fields.
```

### 10.1.2 Foundational Operators

Operators are transformation-level functions, not domain-specific handlers.

The architecture must not grow a new top-level operator for every domain, social role, or task.

Use this foundational set:

```text
Observe
Contextualize
Interpret
Ground
Retrieve
Infer
Decide
Realize
Update
Learn
```

Operator responsibilities:

| Operator | Transformation |
|---|---|
| `Observe` | raw event -> Signal |
| `Contextualize` | runtime state -> ContextKernel |
| `Interpret` | Signal + ContextKernel -> SemanticEventGraph |
| `Ground` | SemanticEventGraph -> grounded entities, time, location, frame, permission |
| `Retrieve` | grounded graph + ContextKernel -> MemoryPacket |
| `Infer` | graph + memory + context -> InferencePacket |
| `Decide` | inference + goal + permission + budget -> DecisionPacket |
| `Realize` | SemanticAnswerGraph or ActionPlan -> output Signal |
| `Update` | decision + output + trace -> memory events and state updates |
| `Learn` | traces + feedback -> labels, parameters, candidate models |

Domain behavior belongs in:

```text
Entity
Claim
Model
ContextKernel
SemanticEventGraph
SemanticAnswerGraph
registry entries
style policies
permission policies
```

not in new foundational operators.

Operator rule:

```text
Use symbolic/indexed computation first when exact structure exists.
Use typed latent computation for generalization, ranking, analogy, composition, and ambiguity.
Use dense text generation only as a realization strategy or explicit fallback.
```

Universal operator interface:

```typescript
interface FoundationalOperator<I, O> {
  id: string
  kind:
    | "observe"
    | "contextualize"
    | "interpret"
    | "ground"
    | "retrieve"
    | "infer"
    | "decide"
    | "realize"
    | "update"
    | "learn"
  input_schema: string
  output_schema: string
  cost_estimate_ms: number
  risk: number
  deterministic_fallback?: string
  model_id?: string
  version: "cemm.operator.v1"
}
```

Core runtime packets:

```typescript
interface GroundedGraph {
  semantic_event_graph_id: string
  entity_ids: string[]
  resolved_time_refs: string[]
  resolved_location_ids: string[]
  active_frame_ids: string[]
  permission: Permission
  missing_slots: string[]
  confidence: number
}

interface MemoryPacket {
  selected_signal_ids: string[]
  selected_claim_ids: string[]
  selected_model_ids: string[]
  ranking_trace: Array<{
    candidate_id: string
    score: number
    reason: string
  }>
  confidence: number
}

interface InferencePacket {
  implications: Claim[]
  contradictions: Claim[]
  predictions: Claim[]
  missing_slots: string[]
  state_deltas: Record<string, unknown>
  confidence: number
}

interface DecisionPacket {
  action_kind:
    | "answer"
    | "ask"
    | "remember"
    | "update"
    | "act"
    | "abstain"
  semantic_answer_graph?: SemanticAnswerGraph
  action_plan?: ActionPlan
  confidence: number
  reason: string
}

interface ActionPlan {
  action_kind: DecisionPacket["action_kind"]
  required_slots: string[]
  missing_slots: string[]
  selected_claim_ids: string[]
  selected_model_ids: string[]
  tool_id?: string
  execution_allowed: boolean
  confidence: number
  risk: number
}
```

### 10.1.3 Semantic Answer Graph

The answer object is structured meaning, not text.

```typescript
interface SemanticAnswerGraph {
  id: string
  intent:
    | "answer"
    | "ask"
    | "abstain"
    | "remember"
    | "update_claim"
    | "simulate"
    | "act"
    | "reflect"

  source_signal_ids: string[]
  context_id: string
  selected_claim_ids: string[]
  selected_model_ids: string[]

  entity_refs: EntityRefUOLAtom[]
  processes: ProcessUOLAtom[]
  states: StateUOLAtom[]
  causal_edges: SemanticEventGraph["causal_edges"]
  temporal_edges: SemanticEventGraph["temporal_edges"]

  answer_latent?: Float32Array
  action_candidates: Action[]

  confidence: number
  uncertainty_reasons: string[]
  permission_scope: Permission["scope"]
  verification: {
    supported: boolean
    verification_type: "hard" | "soft" | "none"
    verifier_model_id?: string
    confidence: number
  }

  version: "cemm.semantic_answer_graph.v1"
}
```

Text realization:

```text
SemanticAnswerGraph
-> TextRealizer
-> candidate text
-> synthesis verification
-> final response or abstain
```

Invariant:

```text
No final answer may be generated directly from a generic embedding.
The answer must first exist as a SemanticAnswerGraph with selected evidence, confidence, permission, and verification state.
```

### 10.1.4 Universal Core Loop

The final model loop is:

```text
Observe
-> Contextualize
-> Interpret
-> Ground
-> Retrieve
-> Infer
-> Decide
-> Realize
-> Update
-> Learn
```

This is the CEMM analogue of an LLM forward pass.

The difference is that the expensive learned computation operates over compact typed meaning objects, not raw token history.

Expanded packet flow:

```text
RawEvent
-> Signal
-> ContextKernel
-> SemanticEventGraph
-> GroundedGraph
-> MemoryPacket
-> InferencePacket
-> DecisionPacket
-> SemanticAnswerGraph | ActionPlan
-> OutputSignal
-> Trace + MemoryEvents
-> TrainingExamples
```

### 10.1.5 MoE Analogue

The MoE equivalent is learned routing over foundational operators and `Model` records.

It is not a growing set of domain-specific experts.

The router chooses:

```text
which foundational operator path to run
which registry/model records to use
which typed latent spaces to compute
which realization strategy to use
whether to escalate or abstain
```

Routing input:

```text
ContextKernel
SemanticEventGraph or GroundedGraph
typed latents if already computed
MemoryPacket if already retrieved
permission state
budget state
SelfView
```

Routing output:

```text
DecisionPacket
cost estimate
risk estimate
confidence estimate
fallback path
```

Rule:

```text
The router is trained over semantic structure and context.
It must not be trained as text-only intent classification.
New domains add Models, Claims, Entities, style policies, or registry entries; they do not add new foundational operators.
```

## 11. Memory Architecture

Memory is implemented as views over primitives.

| Memory View | Backing Storage | Retrieval Key |
|---|---|---|
| Working memory | `Signal`, `Entity`, `Claim`, `Model` | session, recency, active goal |
| Episodic memory | `Signal`, `Action` | time, source, context |
| Semantic memory | `Claim`, `Entity` | subject, predicate, object |
| Causal memory | `Model`, `Claim` | precondition, effect, process |
| Procedural memory | `Model`, `Action` | operator, slots, risk, cost |
| Registry memory | `Model` | registry key, kind, status |
| UOL memory | `Model`, `Signal` | semantic atom, role, quality, process |
| Frame memory | `Model`, `Claim` | frame, validity, temporal containment |
| Context memory | `Model`, `Claim`, `Signal` | context rule, locale, time, session position |
| Self memory | `Self`, `Claim`, `Signal` | identity, state, reflection |
| Trust memory | materialized `SourceTrust` view | source, domain |
| Permission memory | `Signal`, `Claim`, `Model`, `Action` | scope, retention, action |

There is no separate memory store unless performance requires materialization.

## 12. Registry And Frames

The registry canonicalizes structure before retrieval or learning.

Registry entries are `Model` records:

```text
Model(kind = "predicate")
Model(kind = "entity_type")
Model(kind = "operator")
Model(kind = "uol_semantic")
Model(kind = "frame_rule")
Model(kind = "context_rule")
Model(kind = "synthesis_strategy")
Model(kind = "verifier")
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

## 13. UOL Semantic Layer

The UOL semantic layer maps language into canonical meaning atoms.

It is not a new storage primitive.

It is a runtime layer backed by `Model(kind = "uol_semantic")` registry entries.

Mapping rule:

```text
referent      -> Entity
process/event -> ProcessUOLAtom
state/quality -> StateUOLAtom
```

This is language agnostic because the atoms represent frames, participants, states, and deltas, not English parts of speech.

Surface verbs often compile into `ProcessUOLAtom`.

Surface adjectives often compile into `StateUOLAtom`.

Many utterances compile into both.

Examples:

```text
"you are dumb"
"you are daft"
"you are a fool"
"you don't know anything"
```

All can map to:

```text
EntityRefUOLAtom(target = self_entity)
ProcessUOLAtom(frame_key = assert_evaluation, participants.target = self_entity)
StateUOLAtom(state_key = low_competence, holder = self_entity, polarity = negative)
```

Why this improves causality:

```text
ProcessUOLAtom supplies event/process slots.
StateUOLAtom supplies state/quality slots.
Entity supplies stable participants.
Causal rules can match process + input state + output state + participant patterns.
```

Example causal pattern:

```text
ProcessUOLAtom(frame = assistant_failed_answer)
-> ProcessUOLAtom(frame = repeated_negative_evaluation, target = assistant_self)
-> StateUOLAtom(state = user_frustration, value increases temporarily)
```

UOL atoms may produce claims only after canonicalization and permission checks.

By default they remain temporary signal semantics.

Training task:

```text
uol_mapping
```

## 14. Context Inference

Context inference derives temporary meaning from state, not from words alone.

It uses:

```text
WorldState
UserState
TimeState
ConversationState
GoalState
MemoryState
Self
```

Context rules are `Model(kind = "context_rule")` records.

Examples:

```text
turn_index == 1 and short polite utterance -> likely greeting
turn_index == 1 and no greeting and direct command -> user may be in a hurry
user locale + current time -> interpret "tomorrow", "morning", "late"
assistant locale + weather request -> weather must use assistant/user location only if target is clear
world event question + current date -> retrieve fresh/current world claims
session_elapsed high + repeated short corrections -> frustration or urgency may be rising
```

Context inference output:

```typescript
interface ContextInference {
  id: string
  source_signal_id: string
  inferred_claim_ids: string[]
  applied_context_rule_model_ids: string[]
  confidence: number
  decay_half_life_ms: number
  frame_id: string
}
```

`ContextInference` is a runtime packet. Persist only its resulting signals or claims when policy allows.

Rules:

```text
Context inferences are temporary unless repeatedly confirmed.
Context inferences must carry confidence and decay.
Context inferences must not override explicit user statements.
Location inference must ask when target location is ambiguous.
Current-world facts require fresh retrieval when stale or high-risk.
```

First-utterance rule:

```text
If the first user signal is ambiguous, bias toward greeting or session-opening interpretation.
If the first user signal is direct and terse, infer possible hurry/urgency with low confidence.
If greeting was expected but absent, do not assume hostility; treat it as a weak context signal.
```

Training task:

```text
context_inference
```

## 15. Pragmatic Repetition And Affect

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
affect_or_dynamics(t) = affect_or_dynamics(now) * 0.5^(elapsed_ms / decay_half_life_ms)
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

## 16. Causal World Model

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

`CausalRule` is the executable shape of `Model(kind = "causal_rule")`.

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
    confidence_type: "simulated"
  }>
  confidence: number
  cost_ms: number
}
```

`SimulationResult` is a runtime packet. It becomes memory only as `Signal(kind = "simulation_result")`.

Rules:

```text
Simulation produces signals, not truth.
Predictions become claims only after an action explicitly stores them.
Causal models must cite evidence.
Low-confidence causal models may rank actions but must not be presented as fact.
WorldState.persistence defaults to true.
Causal updates use minimal-change semantics: only listed effects change; all unrelated active claims persist unless a frame rule invalidates them.
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

Forward inference confidence:

```text
single_rule_confidence =
  product(precondition_confidences) * rule.confidence

chain_confidence =
  product(step_confidences)

final_simulated_confidence =
  min(chain_confidence, 0.99)
```

Predicted claims must carry:

```text
confidence_type = "simulated"
```

Responses must qualify simulated claims as predictions, not observations.

## 17. Structural Learning

The system must learn structures, not only weights.

Structures that can be learned:

```text
new predicate
new UOL semantic
new entity type
new operator
new causal rule
new process model
new ranking rule
new frame rule
new context rule
new synthesis strategy
new verifier
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

Minimal Inductor contract:

```text
inputs:
  active claims
  feedback events
  failed retrieval pattern claims
  Self.epistemic.coverage_gap_claim_ids

outputs:
  candidate Model records
```

MVP induction is restricted to three deterministic heuristics:

```text
1. Synonym aggregation
   If two predicates share identical subject/object type pairs
   and co-occur more than 5 times,
   propose a canonical merge Model(kind = "predicate").

2. Sequential pattern mining
   If Action A is followed by Signal B within 5 seconds
   with support > threshold,
   propose Model(kind = "causal_rule")
   with confidence = support / (support + failures).

3. Slot completion
   If a Goal repeatedly has missing_slots
   and a specific claim fills the slot,
   propose Model(kind = "context_rule").
```

Forbidden in MVP:

```text
novel ontological class invention
autonomous operator promotion
unbounded search over arbitrary predicates
induction over private data without permission
```

Novel entity types require a separate safe exploration sandbox.

## 18. Embodied And Experiential Grounding

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

## 19. Retrieval And Representation

Primary retrieval is structural.

```text
entity ID
UOL atom key
predicate
object ID
model kind
context rule
domain
source
time
locale
session position
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

Temporal relation cache:

```text
valid_from/valid_until handle containment.
Derived temporal relation claims handle overlap and ordering.
```

When a claim with a temporal interval is stored:

```text
compare against the 5 most temporally proximate active claims
derive bounded Allen-style relations
store derived relations as Claim records
```

Allowed derived predicates:

```text
temporally_precedes
temporally_overlaps
temporally_during
temporally_contains
temporally_meets
```

Rules:

```text
Temporal relations are derived cache claims, not primitives.
They must cite the source interval claims as evidence.
They are invalidated when either source claim is superseded, retracted, or reframed.
```

## 20. Ranking And Confidence

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

## 21. Recursive Runtime

The system is recursive because internal results re-enter as signals.

Core loop:

```text
Observe
-> Contextualize
-> Interpret
-> Ground
-> Retrieve
-> Infer
-> Decide
-> Realize
-> Update
-> Learn
-> maybe_recurse_from_internal_signals
```

Interpret must:

```text
map predicates through Registry
resolve temporal references against TimeState
canonicalize incoming claims
attach frame_id where applicable
```

Ground must:

```text
resolve entities, including the self entity
resolve time and location references
apply frame validity
apply permission gates
identify missing slots
```

Retrieve must use:

```text
structural indexes
frame validity
temporal containment
optional geometric expansion
```

Frame rules must invalidate superseded world-state claims before Decide.

Frame rules must run before permission filtering and memory ranking.

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

Recursive budget consumption:

```text
child_budget.latency_target_ms = parent_budget.latency_target_ms - parent_action.cost_ms
child_budget.max_recursive_steps = parent_budget.max_recursive_steps - 1
```

If remaining latency or recursive steps are <= 0:

```text
abort recursion
emit Signal(kind = "system")
write trace warning
```

Reflection trigger:

```text
reflect if uncertainty is high, contradiction is detected, action failed, model confidence changed, or self coherence drops
```

Basic conversation router:

```text
cemm_runtime_router.py
```

The router is the day-one executable conversation spine.

It is not the final learned model.

It is the smallest useful shell that creates valid traces for CEMM-SLC training.

```text
Signal
-> Contextualize
-> Interpret
-> Ground
-> Retrieve
-> Infer
-> Decide
-> Realize
-> Update
```

Routing order:

```text
exact structural path
-> deterministic rules
-> small learned scorer/router
-> typed latent composition
-> optional LLM/tool fallback
-> abstain/ask when confidence is low
```

The router must remain thinner than the model:

```text
it coordinates foundational operators
it grounds every decision in ContextKernel
it preserves semantic graph and answer graph traces
it does not hide memory mutation
it writes traces for every turn
it uses template/extractive synthesis before neural fallback
it can be replaced internally by learned semantic operators without changing the external loop
```

The final runtime replaces deterministic internals inside foundational operators with:

```text
Interpret model
Ground model
Retrieve ranker
Infer model
Decide model
Realize model
Verifier
```

## 22. Foundational Operators

Foundational operators are `Model(kind = "operator")` records.

They define universal transformations.

They do not encode domains.

Operator contract:

```typescript
interface OperatorSpec {
  model_id: string
  kind:
    | "observe"
    | "contextualize"
    | "interpret"
    | "ground"
    | "retrieve"
    | "infer"
    | "decide"
    | "realize"
    | "update"
    | "learn"
  required_slots: string[]
  accepted_inputs: Array<"raw_event" | "signal" | "context" | "semantic_graph" | "grounded_graph" | "memory_packet" | "inference_packet" | "decision_packet" | "answer_graph" | "action" | "trace">
  output_schema: string
  may_mutate_memory: boolean
  requires_permission: boolean
  estimated_cost_ms: number
  risk: number
}
```

Foundational operators:

```text
observe
contextualize
interpret
ground
retrieve
infer
decide
realize
update
learn
```

Rule:

```text
Operators may only use declared input packets, selected claims/models/signals, ContextKernel, and current SelfView.
Domain-specific behavior must enter through Models, Claims, Entities, style policy, permission policy, or registry entries.
```

Dispatch contract:

| Foundational Operator | Resolver |
|---|---|
| `observe` | `ObservationPipeline.run()` |
| `contextualize` | `ContextKernelBuilder.run()` |
| `interpret` | `SemanticInterpreter.run()` |
| `ground` | `GroundingPipeline.run()` |
| `retrieve` | `RetrievalPipeline.run()` |
| `infer` | `InferencePipeline.run()` |
| `decide` | `DecisionRouter.run()` |
| `realize` | `RealizationPipeline.run()` |
| `update` | `MemoryStateUpdater.run()` |
| `learn` | `TrainingExporter.run()` |

Rule:

```text
Foundational operator metadata chooses the resolver; resolver code performs the transformation.
No action may execute unless it was produced by Decide and passed through permission, budget, and realization/verification gates.
```

## 23. Synthesis And Learning Runtime

`answer` actions do not directly generate final text.

They produce or select a `SemanticAnswerGraph`, then pass through `Realize`.

```text
answer action
-> SemanticAnswerGraph
-> Realize
-> output verification
-> final answer or abstain
```

Realization strategies are `Model(kind = "synthesis_strategy")` records.

MVP strategies:

```text
template
extractive
neural
abstain
```

Realization rule:

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
SemanticAnswerGraph exists before text realization
output uses only selected_claim_ids and selected_model_ids
output does not present predictions as observations
output does not use blocked private memory
output preserves uncertainty from disputed or low-confidence claims
output cites traceable evidence internally
```

Verification strategy depends on synthesis path:

```text
template   -> hard verification
extractive -> hard verification
neural     -> soft verification
abstain    -> no verification
```

Hard verification:

```text
output spans must map to selected_claim_ids or selected_model_ids
failure blocks output
```

Soft verification:

```text
run Model(kind = "verifier")
check contradiction against selected claims/models
if verifier confidence < 0.70, fall back to extractive or abstain
if no contradiction is found, pass with synthesis_verification_type = "soft"
downgrade final response confidence by 0.85
```

Text realization rule:

```text
TextRealizer may choose wording, style, and compactness.
TextRealizer may not add new claims, hidden evidence, hidden certainty, or hidden permissions.
TextRealizer output is invalid if it cannot be mapped back to the SemanticAnswerGraph.
```

Verifier models are ranked like other models and have their own confidence and calibration history.

Execution behavior:

```text
if DecisionPacket.action_kind == "answer":
  Realize from SemanticAnswerGraph
  validate output against selected claims and models
  emit synthesis verification trace

if DecisionPacket.action_kind == "remember":
  store canonical claim
  update Self.meta_memory
  emit memory_update signal

if DecisionPacket.action_kind == "update":
  mark superseded, disputed, or retracted
  update Self.epistemic
  emit memory_update signal

if DecisionPacket.action_kind == "ask":
  Realize clarification from missing slots
  emit action trace

if DecisionPacket.action_kind == "abstain":
  Realize uncertainty or refusal
  emit action trace
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
uol_semantic
entity_type
operator
causal_rule
frame_rule
context_rule
ranking_rule
synthesis_strategy
verifier
```

The Inductor may not promote candidates without validation.

## 24. Storage

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
claims(predicate, valid_from, valid_until)
models(kind, status)
models(registry_key)
models(name)
models(kind, registry_key, status)
actions(operator_model_id, status, created_at)
self_states(updated_at)
source_trust(source_id, domain)
```

Hot cache:

```text
current ContextKernel
current SelfView
recent signals
active entities
active claims
active models
candidate claims
candidate models
```

## 25. Bloat Control

Keep the implementation lean with these gates:

```text
Do not materialize a view until profiling proves repeated recomputation is expensive.
Do not add a table when an indexed primitive field is enough.
Do not add a vector lane when a typed index or ranking feature is enough.
Do not promote a candidate Model without validation.
Do not persist session affect as user identity.
Do not run causal inference unless the goal requires prediction, planning, or consequence analysis.
Do not run neural synthesis when template or extractive synthesis is sufficient.
Do not recurse when no internal signal exceeds salience threshold.
```

Promotion from view to materialized cache requires:

```text
clear latency win
bounded invalidation rule
traceable source primitive IDs
permission-safe contents
measured reuse
```

## 26. Implementation Boundary

This document defines the stable architecture.

Detailed build phases, database choices, runtime commands, task sequencing, and acceptance-test execution live outside this file.

Implementation documents:

```text
cemm_implementation_plan.md
cemm_original_work_subplans.md
cemm_acceptance_tests.md
cemm_pipeline.md
```

Day-one architecture surface:

```text
Signal
ContextKernel
UOL mapping
SemanticEventGraph packet
Claim extraction/retrieval
SemanticAnswerGraph packet
template text realization
trace
runtime export
basic Self state update
```

Everything else is Phase 1+ unless profiling, correctness, or user-facing utility proves it must move earlier.

## 27. Invariants

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
neural synthesis uses hard verification as if attribution were guaranteed
neural synthesis uses unselected evidence
response uses unselected claim or model
language-specific grammar labels bypass UOL process/state registry
text-only router training
text-only answer training when semantic answer graph is available
final text is decoded directly from a generic embedding without SemanticAnswerGraph
typed latent output overrides permission, frame validity, or selected evidence
context inference overrides explicit user statement
ambiguous location is used without asking or evidence
stale world-state claim is used for current-world answer
frame rules run after ranking
recursive budget is refreshed instead of consumed
causal chain confidence is missing or exceeds cap
self mode changes without reflect action trace
repeated paraphrased insults are treated as unrelated events
temporary frustration is persisted as stable user identity without evidence
insults targeting assistant are stored as factual self claims
```

## 28. Acceptance Test Boundary

Acceptance tests are part of the implementation contract, not the core architecture definition.

The maintained test catalog lives in:

```text
cemm_acceptance_tests.md
```

## 29. Final Shape

The architecture is:

```text
Signal records experience.
Entity preserves identity.
Claim preserves belief.
Model preserves structure and process.
Action preserves decision.
Self preserves continuity.
ContextKernel composes current state.
SemanticEventGraph represents current meaning.
SemanticLatentCore learns over typed meaning.
SemanticAnswerGraph represents answer/action meaning before text.
Registry canonicalizes structure.
Frames determine validity.
UOL maps language into process and state atoms.
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
