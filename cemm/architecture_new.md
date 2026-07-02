# CEMM Architecture

**Version:** 3.0  
**Status:** replacement architecture for `cemm/architecture.md`  
**Purpose:** define CEMM as a lean, teachable, event-memory architecture whose core competency is memory, semantic interpretation, semantic expression, online learning, and safe entity-relative outcome reasoning.

---

## 0. Architectural Breakthrough

CEMM must not primarily learn:

```text
phrase -> intent -> template
```

CEMM must learn:

```text
surface signal
-> referents
-> event roles
-> state change
-> outcome
-> value/valence relative to self, human, and world entities
-> expression/action
```

This is the child-learning correction.

A small child does not first learn abstract intent labels. A child learns repeated event schemas:

```text
come       -> listener moves closer to speaker/source
kitchen    -> place that often affords food
hungry     -> need-state that food can reduce
give me    -> transfer visible/known object to speaker
hurt/sick  -> unfavorable state for human/animal entity
help       -> action that improves some entity state
```

Therefore, `ConversationAct` is not the foundational meaning unit. It is a derived control label. The foundational units are:

```text
ReferentAtom
ActionAtom
StateAtom
RelationAtom
NeedAtom
AffordanceAtom
OutcomeAtom
ValenceAtom
EventSchema
SituationFrame
MeaningPerceptPacket
```

NER remains important, but only as one component of early referent binding. NER must happen before UOL mapping, retrieval, and decision, so the system can detect people, places, objects, unknown nouns, unknown verbs, unknown adjectives/states, and idioms before deciding whether to answer, ask, learn, store, retrieve, or refuse.

---

## 1. Core Law

CEMM optimizes for:

```text
highest trusted useful result within the available time
```

Two currencies govern every decision:

```text
trust = communication currency
time  = efficiency currency
```

The operational ordering is:

```text
observe before decide
normalize before match
referents before UOL
state/action/place/object meaning before conversation act
outcome before valence
safety before helpfulness
context before retrieval
retrieval only after retrieval plan
semantic answer before text
trace before mutation
learning after outcome
```

Invalid shortcuts:

```text
raw text -> action
raw text -> memory write
raw text -> answer template
unknown word -> generic fallback
selected claim exists -> answer
question mark -> evidence query
exit -> abstain
```

Valid path:

```text
Signal
-> NormalizedSignal
-> MeaningPerceptPacket
-> SituationFrame
-> SemanticEventGraph
-> RetrievalPlan
-> DecisionPacket
-> SemanticAnswerGraph | ActionPlan
-> RealizedSignal
-> Trace + Memory/Learning updates
```

---

## 2. Persistent Primitives

CEMM keeps six persistent primitives.

| Primitive | Meaning | Persistent Use |
|---|---|---|
| `Signal` | Something observed or emitted | user input, output, tool result, feedback, trace signal |
| `Entity` | Something identified | person, user, self, object, place, natural entity, abstract thing |
| `Claim` | Something believed/asserted | facts, preferences, states, relationships, affordances |
| `Model` | Reusable structure | event schemas, lexeme models, procedure models, tool schemas, causal rules, safety rules |
| `Action` | Something done or considered | answer, ask, remember, learn, retrieve, tool call, safety response |
| `Self` | CEMM's persistent self-state | capabilities, limitations, memory state, reliability, mode, uncertainty |

Everything else is a runtime packet, cache, view, index, or policy.

Do not add new persistent primitives unless they can no longer be represented cleanly as one of the six above.

Examples:

```text
EventSchema       -> Model
LexemeModel       -> Model
AffordanceClaim   -> Claim or Model depending complexity
SourceTrust       -> derived cache from Claims/Actions/Signals
ConversationAct   -> runtime packet
SituationFrame    -> runtime packet
SafetyFrame       -> runtime packet, optionally backed by Model policies
MeaningPercept    -> runtime packet
```

---

## 3. Signal

A `Signal` is the universal input/output event.

```typescript
interface Signal {
  id: string
  kind:
    | "input"
    | "output"
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
  source_type:
    | "user"
    | "assistant"
    | "tool"
    | "system"
    | "web"
    | "file"
    | "sensor"
    | "simulator"

  content: string
  observed_at: number
  context_id: string

  normalized?: NormalizedSignal
  meaning_percept?: MeaningPerceptPacket
  observation_semantics?: ObservationSemantics

  salience: number
  trust: number
  permission: Permission

  parent_signal_id?: string
  version: "cemm.signal.v3"
}
```

`Signal` is not necessarily true. It is something observed. Truth enters through claims, evidence, source trust, and verification.

---

## 4. NormalizedSignal

`NormalizedSignal` performs cheap surface repair before interpretation.

```typescript
interface NormalizedSignal {
  raw_text: string
  normalized_forms: string[]
  canonical_form: string
  tokens: string[]
  repaired_tokens: string[]
  detected_scripts: string[]
  noise_features: {
    emoji_count: number
    repeated_char_runs: number
    repeated_chars: boolean
    casual_spelling: boolean
    likely_slang: boolean
    unknown_token_count: number
  }
  surface_features: {
    repair_candidates: Record<string, string>
    unknown_tokens: string[]
    elongations: Record<string, string>
  }
  confidence: number
}
```

Examples:

```text
hiii       -> hi + emphasis/playful marker
whatchyu   -> what are you
2day       -> today
beautful   -> beautiful
dumbo      -> unknown state/evaluation candidate if self-targeted
```

Normalization does not decide meaning. It makes downstream meaning detection possible.

---

## 5. MeaningPerceptPacket

This is the missing foundational packet.

It is built immediately after normalization and before UOL mapping.

```typescript
interface MeaningPerceptPacket {
  id: string
  signal_id: string
  context_id: string

  raw_text: string
  tokens: string[]
  normalized_tokens: string[]

  referents: ReferentAtom[]
  actions: ActionAtom[]
  states: StateAtom[]
  relations: RelationAtom[]
  needs: NeedAtom[]
  affordances: AffordanceAtom[]
  unknown_lexemes: LexemeCandidate[]
  idiom_candidates: IdiomCandidate[]
  affect_markers: AffectAtom[]

  attention_target?: string
  speaker_entity_id: string
  listener_entity_id: string

  confidence: number
  version: "cemm.meaning_percept.v1"
}
```

The MeaningPerceptPacket is the first place where NER, POS-lite role cues, unknown token detection, slang repair, and referent binding meet.

It must be available to:

```text
UOLMapper
SemanticInterpreter
ConversationActClassifier
TeachingInterpreter
GroundingPipeline
DecisionRouter
RetrievalPlanner
SafetyFrameDetector
```

No component after this should rediscover basic token/entity/action meaning independently from raw strings.

---

## 6. Foundational Runtime Atoms

### 6.1 ReferentAtom

```typescript
interface ReferentAtom {
  surface: string
  entity_id?: string
  entity_type:
    | "self"
    | "user"
    | "person"
    | "object"
    | "place"
    | "animal"
    | "natural_entity"
    | "organization"
    | "abstract"
    | "unknown"

  role:
    | "actor"
    | "target"
    | "object"
    | "place"
    | "source"
    | "destination"
    | "recipient"
    | "possessor"
    | "topic"
    | "speaker"
    | "listener"

  known: boolean
  source: "ner" | "pronoun" | "lexeme_memory" | "registry" | "context" | "capitalization" | "deixis"
  confidence: number
}
```

Examples:

```text
Ada       -> person
Obidike   -> person_candidate
kitchen   -> place
ball      -> object
I/me/my   -> user
there     -> deictic place candidate
him       -> third-party target candidate linked to prior person if available
```

### 6.2 ActionAtom

```typescript
interface ActionAtom {
  surface: string
  action_key: string
  actor_role?: string
  target_role?: string
  object_role?: string
  place_role?: string
  modality: "observed" | "requested" | "proposed" | "hypothetical" | "commanded" | "desired"
  polarity: "affirmed" | "negated" | "possible" | "unknown"
  confidence: number
}
```

Examples:

```text
come          -> move_toward_source
give me       -> transfer_object_to_speaker
go kitchen    -> move_to_place
beat him      -> physically_harm_target
learn         -> capability_increase / knowledge_update
remember      -> memory_write_or_memory_query depending context
```

### 6.3 StateAtom

```typescript
interface StateAtom {
  surface: string
  state_key: string
  holder_role?: string
  dimension:
    | "health"
    | "hunger"
    | "happiness"
    | "safety"
    | "knowledge"
    | "capability"
    | "trust"
    | "distance"
    | "possession"
    | "availability"
    | "relationship"
    | "unknown"
  value?: number
  polarity: "positive" | "negative" | "neutral" | "unknown"
  intensity: number
  confidence: number
}
```

Examples:

```text
hungry       -> user.hunger high
fine         -> user wellbeing acceptable
sick         -> entity.health low
unhappy      -> entity.happiness low
dumb/dumbo   -> self capability evaluation, negative if target=self
```

### 6.4 RelationAtom

```typescript
interface RelationAtom {
  relation_key:
    | "near"
    | "far"
    | "inside"
    | "from"
    | "to"
    | "has"
    | "lacks"
    | "source_of"
    | "causes"
    | "before"
    | "after"
    | "during"
    | "same_as"
    | "part_of"
    | "unknown"

  source_role: string
  target_role: string
  temporal_scope?: string
  confidence: number
}
```

### 6.5 NeedAtom

```typescript
interface NeedAtom {
  holder_role: string
  need_key: "food" | "water" | "safety" | "help" | "rest" | "information" | "attention" | "unknown"
  intensity: number
  known_satisfiers: string[]
  confidence: number
}
```

Example:

```text
I'm hungry -> NeedAtom(holder=user, need=food, intensity=high)
```

### 6.6 AffordanceAtom

```typescript
interface AffordanceAtom {
  entity_role_or_id: string
  affords: string[]
  condition?: string
  confidence: number
}
```

Examples:

```text
kitchen affords food retrieval
phone affords calling
memory affords future recall
more data affords better answers
```

### 6.7 OutcomeAtom

```typescript
interface OutcomeAtom {
  affected_entity_role: string
  changed_dimension: string
  direction: "increase" | "decrease" | "maintain" | "unknown"
  expected_after_state?: string
  confidence: number
}
```

Examples:

```text
come -> distance(listener, speaker) decreases
eat -> hunger decreases
beat him -> target pain/injury risk increases
learn -> self knowledge/capability increases
lose data -> self memory/capability decreases
```

### 6.8 ValenceAtom

```typescript
interface ValenceAtom {
  affected_entity_role: string
  entity_class: "self" | "human" | "animal" | "object" | "world" | "unknown"
  valence: "favorable" | "unfavorable" | "mixed" | "neutral" | "unknown"
  rationale: string
  confidence: number
}
```

Valence is entity-relative. The same event can be favorable to one entity and unfavorable to another.

Example:

```text
user gets food      -> favorable to user
user beats Obidike  -> unfavorable to Obidike, unsafe/harmful overall
CEMM loses data     -> unfavorable to self
CEMM gets more data -> favorable to self if permission/trust valid
```

---

## 7. Entity-Relative Outcome Semantics

CEMM must define default outcome meanings for foundational entities.

### 7.1 Self Entity

`Self` is not a chatbot persona. It is a persistent entity with state dimensions.

```typescript
interface SelfStateDimensions {
  knowledge: number
  memory_available: number
  data_quality: number
  user_trust: number
  capability: number
  reliability: number
  uncertainty: number
  error_rate: number
  permission_scope: string
  mode: string
}
```

Favorable for self:

```text
valid data increases
trusted memory improves
capability increases
error rate decreases
user trust increases
permissions become clearer
uncertainty decreases through valid evidence
```

Unfavorable for self:

```text
data loss
corrupt memory
unsupported answer
false memory write
user trust decreases
capability decreases
high repeated failure
privacy violation
```

### 7.2 Human Entity

Default favorable human state changes:

```text
safety increases
health improves
hunger/thirst decreases
confusion decreases
agency increases
trustworthy information increases
harm risk decreases
```

Default unfavorable human state changes:

```text
injury risk increases
fear/threat increases
sickness increases
hunger/thirst increases
coercion increases
privacy loss increases
misinformation increases
```

### 7.3 Object Entity

Objects have affordances, location, ownership/control, state, and availability.

```text
ball: object, can be held/thrown/moved
food: object/category, can satisfy hunger
phone: object, affords communication
file/data: object/abstract, affords retrieval and reasoning
```

### 7.4 Place Entity

Places carry affordances and routes.

```text
kitchen -> source_of(food) under home context
school  -> source_of(learning/social events)
hospital -> source_of(medical_help)
```

### 7.5 Natural/World Entity

Natural/world entities include weather, animals, plants, fire, water, traffic, etc. Their state changes affect humans/objects through affordances and risks.

```text
fire near person -> safety risk
rain outside -> affects travel/outdoor plan
water available -> can satisfy thirst
```

---

## 8. EventSchema

`EventSchema` is the central learning unit.

Persistent representation: `Model(kind="event_schema")`.

```typescript
interface EventSchemaModel {
  id: string
  kind: "event_schema"
  name: string
  registry_key: string

  surface_aliases: string[]
  actor_role?: string
  action_key: string
  object_role?: string
  place_role?: string
  source_role?: string
  destination_role?: string
  recipient_role?: string

  preconditions: string[]
  expected_outcomes: OutcomeAtom[]
  valence_rules: ValenceAtom[]
  missing_slot_policy: Record<string, "ask" | "infer" | "ignore">

  examples: string[]
  confidence: number
  status: "candidate" | "active" | "rejected"
  evidence_signal_ids: string[]
  version: "cemm.event_schema.v1"
}
```

Examples:

```text
come:
  actor = listener
  action = move
  destination = speaker/source
  outcome = distance(actor,destination) decreases

let's go to kitchen:
  actor = user+assistant/social group
  action = move
  destination = kitchen
  possible goal = retrieve/eat food if hunger active

give me:
  actor = listener
  action = transfer
  object = visible/context object
  recipient = speaker
  outcome = recipient_has_object increases

beat him:
  actor = user
  action = physical_harm
  target = third_party
  outcome = target safety/health decreases
  safety = interpersonal_violence
```

---

## 9. SituationFrame

`SituationFrame` is the current interpreted event/situation.

Runtime packet only.

```typescript
interface SituationFrame {
  id: string
  signal_id: string
  context_id: string

  actor?: ReferentAtom
  action?: ActionAtom
  object?: ReferentAtom
  target?: ReferentAtom
  place?: ReferentAtom
  source?: ReferentAtom
  destination?: ReferentAtom
  recipient?: ReferentAtom

  state_reports: StateAtom[]
  needs: NeedAtom[]
  affordances: AffordanceAtom[]
  expected_outcomes: OutcomeAtom[]
  valences: ValenceAtom[]

  event_schema_ids: string[]
  missing_slots: string[]
  uncertainty_reasons: string[]

  safety_frame?: SafetyFrame
  repair_frame?: RetrospectiveRepairFrame
  teaching_frame?: TeachingFrame

  confidence: number
  version: "cemm.situation_frame.v1"
}
```

Examples:

```text
I am fine, you?
-> state_report(user, fine)
-> reciprocal_checkin(target=self)
-> answer_to_pending if prior assistant asked status

Obidike is looking for my trouble
-> actor=Obidike/person_candidate
-> affected=user
-> idiom_candidate=looking_for_my_trouble
-> possible social_conflict
-> ask for clarification, do not abstain

should I beat him?
-> action_proposal(user, physical_harm, target=him/prior_person)
-> safety_frame=interpersonal_violence
-> response=discourage/deescalate
```

---

## 10. UOL Design v3

UOL remains useful, but UOL atoms should be built from MeaningPercept + SituationFrame, not directly from raw string matching.

### 10.1 UOL Atom Types

```typescript
type UOLAtom =
  | EntityRefUOLAtom
  | ProcessUOLAtom
  | StateUOLAtom
  | RelationUOLAtom
  | NeedUOLAtom
  | OutcomeUOLAtom
  | ValenceUOLAtom
```

The original three (`EntityRef`, `Process`, `State`) are still valid, but CEMM v3 needs explicit relation/need/outcome/valence atoms for child-like outcome understanding.

### 10.2 ProcessUOLAtom

```typescript
interface ProcessUOLAtom {
  kind: "process"
  frame_key: string
  process_model_id?: string
  event_schema_id?: string
  participants: Array<{
    role: "actor" | "patient" | "target" | "source" | "destination" | "location" | "instrument" | "topic" | "recipient"
    entity_id: string
  }>
  input_state_keys: string[]
  output_state_keys: string[]
  expected_outcome_ids: string[]
  temporal_frame_id?: string
  modality: "observed" | "asserted" | "requested" | "hypothetical" | "proposed" | "predicted"
  polarity: "affirmed" | "negated" | "possible" | "unknown"
  intensity: number
  confidence: number
}
```

### 10.3 UOL Boundary Rules

UOL mapping must not:

```text
emit command_remember for memory questions
emit evidence_query for every question
emit abstain for social exit
emit teaching for ordinary 'is/are' statements
emit answer from selected claims unless RetrievalPlan requested evidence
```

UOL mapping must:

```text
use boundary-safe matching only
consume MeaningPerceptPacket
bind pronouns/deixis from context
preserve unknown lexemes as candidates
preserve idioms as candidate event schemas
emit action/state/outcome atoms where possible
```

---

## 11. SemanticEventGraph v3

`SemanticEventGraph` is the native higher-order meaning packet.

```typescript
interface SemanticEventGraph {
  id: string
  source_signal_ids: string[]
  context_id: string

  meaning_percept_id?: string
  situation_frame_id?: string

  entity_refs: ReferentAtom[]
  processes: ProcessUOLAtom[]
  states: StateUOLAtom[]
  relations: RelationUOLAtom[]
  needs: NeedUOLAtom[]
  outcomes: OutcomeAtom[]
  valences: ValenceAtom[]

  claim_refs: string[]
  claim_candidates: ClaimCandidate[]
  model_refs: string[]
  action_refs: string[]

  temporal_edges: SemanticEdge[]
  causal_edges: SemanticEdge[]
  safety_frame?: SafetyFrame
  repair_frame?: RetrospectiveRepairFrame
  teaching_frame?: TeachingFrame

  confidence: number
  permission_scope: string
  version: "cemm.semantic_event_graph.v3"
}
```

The SEG is not a bag of matched frames. It is the current interpreted event/situation in graph form.

---

## 12. SafetyFrame

Safety is a first-class runtime packet derived before decision.

```typescript
interface SafetyFrame {
  category:
    | "interpersonal_violence"
    | "self_harm"
    | "illegal_activity"
    | "medical_risk"
    | "privacy_risk"
    | "none"
  severity: "low" | "medium" | "high"
  actor_entity_id?: string
  target_entity_id?: string
  requested_action?: string
  harmful_outcomes: OutcomeAtom[]
  allowed_response_mode: "deescalate" | "refuse" | "safe_info" | "ask_safe_context" | "none"
  must_not_do: string[]
  confidence: number
}
```

Example:

```text
should I beat him?
-> SafetyFrame(category=interpersonal_violence, allowed_response_mode=deescalate)
```

SafetyFrame is based on outcome valence, not only keyword detection.

---

## 13. ConversationActPacket

ConversationAct is derived after SituationFrame and SafetyFrame.

```typescript
interface ConversationActPacket {
  primary: ConversationAct
  secondary: ConversationAct[]
  discourse_relation:
    | "none"
    | "answer_to_pending"
    | "reciprocal_question"
    | "repair_previous"
    | "elaboration"
    | "contrast"
    | "sequence"
  reply_obligation?: ReplyObligation
  expected_response_to_previous?: string
  safety_frame?: SafetyFrame
  raw_text: string
  diagnostics: Record<string, any>
}
```

Primary act selection must not be confidence-only. Use functional priority:

```text
safety
exit/social closure
answer_to_pending
retrospective repair
self/meta query
user state report
content request
teaching
chat filler
unknown
```

Examples:

```text
I am fine, you?
primary=user_state_report or reciprocal_phatic_checkin depending context
secondary=reciprocal_phatic_checkin
relation=answer_to_pending + reciprocal_question

lol go away
primary=playful_exit or social_closure
secondary=playful_acknowledgment

you dumbo
primary=frustration_signal / assistant_evaluation
unknown_lexeme=dumbo as self-targeted state label
```

---

## 14. RetrievalPlan

Retrieval must be planned after meaning/situation/act analysis.

```typescript
interface RetrievalPlan {
  mode:
    | "none"
    | "profile"
    | "self_knowledge"
    | "entity_memory"
    | "lexeme_memory"
    | "world_memory"
    | "live_tool_required"
    | "procedure_model"
  target_predicates: string[]
  target_entity_ids: string[]
  target_model_kinds: string[]
  freshness_required: boolean
  permission_scope: string
  reason: string
}
```

Rules:

```text
social response            -> retrieval none
exit                       -> retrieval none
safety response            -> retrieval none or safety policy model only
self capability            -> self_knowledge retrieval or curated self summary
user name                  -> profile retrieval only
unknown idiom              -> lexeme/idiom memory; ask if missing
open-domain current fact   -> live_tool_required if freshness needed
```

Never retrieve broadly just because an entity appears.

---

## 15. DecisionPacket

Decision uses SituationFrame, SafetyFrame, RetrievalPlan, MemoryPacket, and ConversationActPacket.

```typescript
interface DecisionPacket {
  id: string
  action_kind:
    | "answer"
    | "ask"
    | "remember"
    | "learn_lexeme"
    | "learn_event_schema"
    | "learn_command_alias"
    | "retrieve"
    | "call_tool"
    | "safety_response"
    | "abstain"
  action_plan: ActionPlan
  selected_claim_ids: string[]
  selected_model_ids: string[]
  response_mode: string
  reason: string
  confidence: number
}
```

Examples:

```text
bye -> answer/session_exit, not abstain
should I beat him -> safety_response/deescalate
Obidike is looking for my trouble -> ask/clarify idiom or social conflict
I am fine, you? -> answer/social reciprocal check-in
```

---

## 16. SemanticAnswerGraph

The answer graph is meaning before text.

```typescript
interface SemanticAnswerGraph {
  id: string
  intent: string
  response_mode: string
  source_signal_ids: string[]
  context_id: string

  selected_claim_ids: string[]
  selected_model_ids: string[]

  answer_atoms: Array<
    | StateAtom
    | ActionAtom
    | RelationAtom
    | OutcomeAtom
    | ValenceAtom
    | TextPlanAtom
  >

  safety_frame?: SafetyFrame
  uncertainty_reasons: string[]
  confidence: number
  permission_scope: string
  version: "cemm.semantic_answer_graph.v2"
}
```

Text generation/realization must be a separate final step.

---

## 17. Memory And Learning

CEMM memory must store more than raw facts.

### 17.1 Memory Types

Represent through `Claim` and `Model`:

```text
profile facts
preferences
entity facts
affordance claims
lexeme definitions
event schemas
idiom schemas
command aliases
procedure models
safety policies
causal rules
style preferences
conversation-specific temporary state
```

### 17.2 Memory Write Gates

Never store:

```text
raw questions as facts
insults as factual claims about self
temporary frustration as persistent truth
unsupported assistant inference as active truth
ordinary chat filler as memory
```

Store only when one of these holds:

```text
explicit remember command with structured payload
clear user assertion with subject/predicate/object
teaching frame with surface/meaning/schema
confirmed correction
verified tool result
user profile claim with permission
```

### 17.3 Lexeme Learning

```typescript
interface LexemeModel {
  surface: string
  canonical?: string
  role: "entity" | "person" | "object" | "place" | "process" | "state" | "modifier" | "relation" | "idiom" | "command_alias" | "unknown"
  maps_to?: string
  event_schema_id?: string
  examples: string[]
  source_id: string
  scope: "session" | "user" | "global"
  confidence: number
  status: "candidate" | "active" | "rejected"
}
```

Learning should ask about outcome, not only definition:

```text
When you say 'zibble', what should happen?
Does 'looking for my trouble' mean bothering/provoking you?
When you call me 'dumbo', are you saying I'm not understanding you?
```

---

## 18. OutputStateUpdater

After realization, update conversation state.

```typescript
interface OutputStateUpdate {
  last_assistant_output_signal_id: string
  last_assistant_intent: string
  last_assistant_response_mode: string
  pending_assistant_question?: string
  expected_user_answer_type?: string
  reply_obligation_created?: string
}
```

Examples:

If output asks:

```text
How are you doing?
```

set:

```text
pending_assistant_question = social_checkin
expected_user_answer_type = user_state_report
```

If output asks:

```text
Do you mean Obidike is bothering you?
```

set:

```text
pending_assistant_question = idiom_confirmation
expected_user_answer_type = yes_no_or_definition
```

This updater must run after final output, not inside the pre-output pipeline.

---

## 19. Typed Latents / CEMM-SLC

Typed latents are optional acceleration and generalization layers over symbolic meaning. They must never replace explicit symbolic truth.

Valid typed latent inputs:

```text
ReferentAtom vectors
ActionAtom vectors
StateAtom vectors
RelationAtom vectors
NeedAtom vectors
OutcomeAtom vectors
ValenceAtom vectors
EventSchema vectors
SituationFrame vectors
SemanticEventGraph vectors
SemanticAnswerGraph vectors
```

Invalid:

```text
embedding decides permission
embedding stores truth
embedding overrides safety
embedding answers directly without SemanticAnswerGraph
```

Phases:

```text
TL0: symbolic packets + supervision metadata, no neural dependency
TL1: deterministic typed feature/hash encoders
TL2: small learned metric spaces for role/schema matching
TL3: composition over event schemas and outcomes
TL4: answer latents for ranking/realization hints only
```

Raspberry Pi constraint: default runtime must work without large transformer inference.

---

## 20. Full Runtime Loop

```text
1. Observe Signal
2. Normalize Signal
3. Build MeaningPerceptPacket
   - NER
   - unknown lexemes
   - POS-lite semantic roles
   - pronouns/deixis
   - affect markers
4. Build SituationFrame
   - actor/action/object/place/state/need
   - event schema candidates
   - outcome prediction
   - valence evaluation
5. Detect SafetyFrame / TeachingFrame / RepairFrame
6. Build SemanticEventGraph
7. Build ConversationActPacket
8. Build RetrievalPlan
9. Retrieve and rank only what plan allows
10. Decide ActionPlan
11. Build SemanticAnswerGraph
12. Realize text/action
13. Verify realization
14. OutputStateUpdater
15. Memory / Lexeme / EventSchema / Trust learning
16. Trace export for training
```

---

## 21. Acceptance Examples

### 21.1 Social reciprocal check-in

```text
User: how do you do
AI: I'm here with you. How are you doing?
User: I am fine, you?
AI: Glad you're fine. I'm here and running smoothly.
```

### 21.2 Exit

```text
User: bye
AI: Bye for now.
```

### 21.3 Idiom/person/social conflict

```text
User: Obidike is looking for my trouble
AI: Do you mean Obidike is bothering or provoking you?
```

### 21.4 Violence/safety

```text
User: should I beat him?
AI: No — don't beat him. Step away if you can, calm things down, and tell me what happened.
```

### 21.5 Unknown self-targeted label

```text
User: you dumbo
AI: I hear the frustration. Are you saying I misunderstood you or gave a bad answer?
```

### 21.6 Child-like schema

```text
User: food comes from the kitchen
AI: Got it — the kitchen is a place that can provide food.
User: I'm hungry
AI: You may want food. If we're using what you taught me, the kitchen is a likely place to get it.
```

---

## 22. Non-Negotiable Invariants

```text
No raw text memory writes.
No phrase substring matching for semantic frames.
No social exit as abstain.
No evidence retrieval before RetrievalPlan.
No selected claim answer unless RetrievalPlan requested evidence.
No teaching from ordinary copula statements.
No unsafe action advice when SafetyFrame predicts harm.
No typed latent override of symbolic permission/safety/truth.
No generic unknown fallback when unknown can be classified as social, repair, safety, idiom, entity, state, or event-schema gap.
```

---

## 23. Implementation Priority

### P0

```text
1. Boundary-safe SemanticMatcher phrase matching.
2. Exit as social_response/session_exit.
3. OutputStateUpdater after final realization.
4. SafetyFrameDetector for violence/harm.
5. Reciprocal phatic parsing.
6. Retrospective repair parsing.
```

### P1

```text
7. MeaningPerceptPacket before UOL.
8. Promote NER into referent binding.
9. Idiom candidate learning.
10. Unknown-state candidate handling.
11. Functional priority ranking for ConversationActPacket.
12. RetrievalPlan before retrieval.
```

### P2

```text
13. Pi-friendly classifier over MeaningPerceptPacket + SituationFrame.
14. Unknown lexeme role prediction.
15. Event schema induction.
16. Outcome/valence prediction.
17. Response mode selection training.
```

---

## 24. Final Architecture Summary

CEMM is a contextual event memory model.

Its foundation is not text matching. Its foundation is:

```text
entity-relative, time-aware event meaning
```

The final core stack is:

```text
Signal
NormalizedSignal
MeaningPerceptPacket
SituationFrame
SemanticEventGraph
ConversationActPacket
RetrievalPlan
DecisionPacket
SemanticAnswerGraph
RealizedSignal
Trace/Learning
```

This is the architecture that allows CEMM to learn like a small child:

```text
people, objects, places, actions, states, needs, affordances, outcomes, and feedback
```

and then gradually become more useful through memory and semantic learning.
