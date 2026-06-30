# CEMM Original Work Sub-Implementation Plans

Version: 1.0  
Purpose: detailed implementation plans for CEMM components that do not commonly exist as off-the-shelf engineering patterns.

## 1. Scope

This document covers original or high-risk CEMM work:

```text
typed latent spaces
SemanticEventGraph
SemanticAnswerGraph
GroundedGraph / MemoryPacket / InferencePacket / DecisionPacket
online trust learning
procedure and tool skill models
semantic-to-text realization
```

The implementation rule is:

```text
build symbolic correctness first
build traceable training targets second
build deterministic baselines third
train learned components only after measurable baselines exist
```

The architecture must not depend on a learned embedding being correct before the symbolic path works.

## 2. Typed Latents

Typed latents are the most delicate component.

They are not generic embeddings.

They are typed projections of structured meaning.

### 2.1 Goal

Typed latents should make CEMM better at:

```text
paraphrase alignment
semantic retrieval
candidate ranking
analogy
composition
ambiguity handling
next-event prediction
semantic answer composition
```

They must not carry:

```text
permission
source of truth
time validity
claim status
negation
uncertainty
causal direction
```

Those remain explicit symbolic fields.

### 2.2 Typed Spaces

Use separate vector spaces:

```text
entity
process
state
claim
model
context
self
memory
action
answer
```

Each space has:

```typescript
interface LatentSpaceSpec {
  id: string
  kind:
    | "entity"
    | "process"
    | "state"
    | "claim"
    | "model"
    | "context"
    | "self"
    | "memory"
    | "action"
    | "answer"
  dimensions: number
  encoder_model_id: string
  feature_schema_version: string
  training_snapshot_id: string
  normalization: "l2" | "none"
  distance: "cosine" | "dot" | "euclidean"
  status: "candidate" | "active" | "deprecated"
}
```

Default MVP dimensions:

```text
entity: 64
process: 128
state: 64
claim: 128
model: 128
context: 128
self: 64
memory: 128
action: 64
answer: 128
```

These are starting budgets, not truth. They should be profiled and adjusted.

### 2.3 Phase TL0: Supervision Metadata

Do not train numeric vectors first.

First collect supervision:

```text
positive pairs
negative pairs
hard negatives
typed space target
must-preserve fields
evidence refs
confidence
uncertainty reason
```

Example:

```json
{
  "task_type": "semantic_latent_target",
  "positive_pairs": [
    {
      "a": "you are dumb",
      "b": "you are daft",
      "space": "state",
      "reason": "both map to low_competence state targeting assistant_self"
    }
  ],
  "negative_pairs": [
    {
      "a": "you are dumb",
      "b": "I prefer Postgres",
      "space": "process",
      "reason": "evaluation process vs preference process"
    }
  ],
  "must_preserve_fields": [
    "target_entity_id",
    "polarity",
    "intensity",
    "permission",
    "source"
  ]
}
```

Deliverables:

```text
semantic_latent_target examples
latent pair validation script
latent target JSON schema
small gold eval set
```

Pass criteria:

```text
examples validate
no target asks vector to encode permission/source/time as hidden meaning
positive and negative pairs cite semantic structure
```

### 2.4 Phase TL1: Deterministic Typed Baselines

Before neural training, build deterministic encoders.

Use feature hashing or sparse vectors over canonical structure:

```text
entity type
entity aliases
process frame_key
state_key
predicate_model_id
slot names
participant roles
subject/object types
temporal relation keys
causal edge labels
context bucket
goal key
action kind
```

Do not use raw text tokens as the primary feature.

Allowed text features:

```text
canonical aliases
registry keys
normalized entity names
approved synonym sets
```

Deliverables:

```text
typed_feature_extractor.py
typed_hash_encoder.py
latent_space_registry.json
latent_eval.py
```

Pass criteria:

```text
paraphrased insults cluster by state/process
preference claims cluster by predicate and holder
unrelated predicates separate
permission/source/time remain outside vector payload
retrieval improves over raw text search on eval set
```

### 2.5 Phase TL2: Learned Metric Spaces

Train small encoders only after TL1 works.

Candidate models:

```text
linear projection over deterministic features
small MLP per typed space
bi-encoder per typed space
cross-type projection heads for claim/context/action
```

Losses:

```text
contrastive loss
triplet loss
supervised ranking loss
calibration loss
hard-negative penalty
permission violation penalty
```

Training sources:

```text
seed examples
runtime exported traces
LLM-labeled semantic targets
user corrections
retrieval success/failure traces
verification failures
```

Pass criteria:

```text
beats TL1 deterministic baseline on held-out evals
does not degrade permission/frame/source constraints
has calibrated similarity thresholds
has deterministic fallback
```

### 2.6 Phase TL3: Typed Composition

Only after stable metric spaces exist, implement composition:

```text
SemanticEventGraph + ContextKernel -> context-aware event latent
MemoryPacket + query graph -> retrieval latent
InferencePacket -> decision latent
SemanticAnswerGraph -> answer latent
```

Allowed computation:

```text
bounded typed attention over graph nodes
pooling by role
relation-aware scoring
small learned scorer
```

Forbidden:

```text
dense attention over raw conversation tokens by default
unbounded graph attention
answer text decoded directly from answer latent
latent override of explicit constraints
```

Pass criteria:

```text
composition improves ranking/decision accuracy
latency stays within budget
trace records which typed spaces were used
fallback returns to symbolic/rule path
```

### 2.7 Phase TL4: Answer Latents

Answer latents are only for:

```text
ranking candidate SemanticAnswerGraphs
style-conditioned realization hints
semantic similarity between answer plans
verifier features
```

They must not be used as:

```text
generic embedding -> final text
hidden evidence carrier
hidden permission bypass
```

Pass criteria:

```text
every realized text maps back to SemanticAnswerGraph
unsupported spans are detected
selected_claim_ids remain explicit
```

## 3. SemanticEventGraph

### 3.1 Goal

`SemanticEventGraph` is the native meaning packet for a turn.

It should answer:

```text
what happened?
who/what was involved?
what process occurred?
what states changed?
what claims or actions are candidates?
what temporal/causal edges exist?
what permission scope applies?
```

### 3.2 Implementation Phases

Phase SEG0:

```text
runtime packet produced by deterministic UOL/claim extraction
stored inside trace
exported to trainer
```

Phase SEG1:

```text
JSON schema validator
gold examples
LLM labeler task
denoising task
diff tool for graph comparison
```

Phase SEG2:

```text
learned Interpret model proposes graph candidates
deterministic graph remains fallback
verifier checks graph consistency
```

### 3.3 Required Validation

Reject graph if:

```text
source_signal_ids missing
context_id missing
permission_scope missing
process/state uses raw English label instead of registry key
claim candidate lacks evidence signal
negation is only implied by embedding
target entity is ambiguous but marked certain
```

## 4. SemanticAnswerGraph

### 4.1 Goal

`SemanticAnswerGraph` is the answer/action meaning before text.

It should answer:

```text
what are we going to communicate or do?
which evidence supports it?
what uncertainty must be preserved?
what permission scope applies?
what action kind was chosen?
```

### 4.2 Implementation Phases

Phase SAG0:

```text
template/rule-created SemanticAnswerGraph
selected_claim_ids explicit
verification flag
trace export
```

Phase SAG1:

```text
semantic_answer_composition task
gold answer graph evals
unsupported-claim tests
```

Phase SAG2:

```text
learned Decide/Realize support
answer graph ranker
soft verifier for composed answers
```

### 4.3 Required Validation

Reject answer graph if:

```text
answer intent is unsupported by selected evidence
selected_claim_ids missing for factual answer
prediction is represented as observed fact
permission_scope exceeds source permission
uncertainty is dropped
```

## 5. Packet Layer

These packets make the foundational loop buildable:

```text
GroundedGraph
MemoryPacket
InferencePacket
DecisionPacket
ActionPlan
```

### 5.1 GroundedGraph

Purpose:

```text
resolve entities, time, location, frame, permission, and missing slots
```

MVP:

```text
entity ids
time refs
location ids
active frames
permission state
missing slots
confidence
```

### 5.2 MemoryPacket

Purpose:

```text
carry bounded selected memory and ranking trace
```

MVP:

```text
selected_signal_ids
selected_claim_ids
selected_model_ids
ranking_trace
confidence
```

### 5.3 InferencePacket

Purpose:

```text
carry implications, contradictions, predictions, state deltas, missing slots
```

MVP:

```text
missing_slots
contradictions
state_deltas
confidence
```

Predictions remain optional until causal phase.

### 5.4 DecisionPacket

Purpose:

```text
choose answer, ask, remember, update, act, or abstain
```

MVP:

```text
action_kind
semantic_answer_graph
action_plan
confidence
reason
```

## 6. Online Trust Learning

### 6.1 Goal

CEMM should learn quickly without model retraining by updating:

```text
claim confidence
source trust by domain
tool reliability
procedure reliability
entity aliases
predicate aliases
slot defaults
self capability state
```

### 6.2 SourceTrust Cache

Source trust is derived from primitives.

Do not treat it as a source of truth.

MVP cache:

```typescript
interface SourceTrustCache {
  source_id: string
  domain: string
  trust_log_odds: number
  observations: number
  confirmations: number
  corrections: number
  contradictions: number
  last_updated_at: number
  evidence_signal_ids: string[]
}
```

Update rule:

```text
confirmation -> increase trust_log_odds
correction -> decrease trust_log_odds
contradiction -> decrease trust_log_odds more strongly
tool success -> increase tool reliability
tool failure -> decrease tool reliability
decay stale domains over time
```

Do not use naive averaging for high-stakes confidence.

Use log-odds or another calibrated update rule.

### 6.3 Pass Criteria

```text
new user preference affects next turn immediately
user correction supersedes old claim
tool failure reduces future tool confidence
domain-specific trust changes do not globally punish a source
trust cache can be recomputed from evidence
```

## 7. Procedure And Tool Skill Models

### 7.1 Goal

New skills are `Model` records, not new foundational operators.

Examples:

```text
schedule_virtual_meeting
compute_exact_math
summarize_document
create_invoice
query_database
```

### 7.2 Procedure Model Shape

```typescript
interface ProcedureModel {
  model_id: string
  registry_key: string
  required_slots: string[]
  optional_slots: string[]
  preconditions: string[]
  tool_sequence: string[]
  confirmation_policy: "always" | "risky_only" | "never"
  success_criteria: string[]
  failure_modes: string[]
  reliability_log_odds: number
}
```

### 7.3 Tool Schema Model Shape

```typescript
interface ToolSchemaModel {
  model_id: string
  tool_id: string
  input_schema: string
  output_schema: string
  permission_required: Permission
  cost_estimate_ms: number
  risk: number
  reliability_log_odds: number
}
```

### 7.4 Math Tool Handoff

Math should use tool handoff for exact computation.

Loop:

```text
Interpret math request
Ground symbols, units, constraints
Retrieve math/tool schema
Infer exact computation is required
Decide action_kind = act
Realize tool input
Update with tool result
Realize explanation
```

MVP tool:

```text
calculator.basic
```

Do not train the semantic model to approximate arithmetic as the primary path.

### 7.5 Scheduling Skill

Scheduling should be a procedure model:

```text
procedure_model: schedule_virtual_meeting
required_slots:
  participants
  time_window
  duration
  title
tools:
  calendar.availability
  calendar.create_event
  meeting_link.generate
  calendar.invite
```

MVP without connectors:

```text
recognize workflow
extract participants/emails/time window
ask for missing slots
abstain from execution when tools/permissions are missing
export trace for procedure_model_induction
```

### 7.6 Skill Induction

Trigger candidate procedure model when:

```text
similar goal repeats
same slot pattern repeats
same tool sequence repeats
outcome succeeds often enough
user correction converges on same defaults
```

Candidate remains inactive until validated.

## 8. Semantic-To-Text Realization

### 8.1 Goal

Realization converts meaning to text.

It does not decide truth.

It does not add evidence.

### 8.2 Realizer Inputs

```text
SemanticAnswerGraph
selected claims/models
style policy
relationship/context state
permission
uncertainty
```

### 8.3 Realizer Modes

```text
template
extractive
neural
abstain
```

MVP:

```text
template only
```

### 8.4 Pass Criteria

```text
text maps back to selected_claim_ids
uncertainty is preserved
private evidence is not revealed
style changes wording but not facts
unsupported spans are blocked
```

## 9. Minimal Build Order

Implement in this order:

```text
1. JSON schemas for packets
2. validators for packets
3. runtime packet construction
4. runtime export
5. gold examples
6. deterministic typed feature encoder
7. latent eval suite
8. learned typed metric spaces
9. answer graph ranker
10. realization verifier
11. procedure/tool models
12. skill induction
```

Do not start with GPU training.

Do not start with answer-latent text decoding.

Do not start with unbounded tool execution.

## 10. Open Questions To Keep Explicit

These should remain explicit until measured:

```text
best dimensions per latent space
best threshold for semantic similarity
how much runtime export to keep
when to materialize graph caches
which tool outcomes are reliable enough for trust updates
how to evaluate answer graph quality independently from prose
```

No hidden assumption should be promoted to architecture without an eval.
