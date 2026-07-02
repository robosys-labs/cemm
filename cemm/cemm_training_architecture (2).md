# CEMM-SLC Training Architecture

Version: 2.0  
Purpose: an efficient continuous training architecture for CEMM and its Semantic Latent Core.

## 1. Goal

The training target is not a text-only chatbot.

The target is:

```text
Signal + ContextKernel + Memory
-> SemanticEventGraph
-> typed latent computation
-> SemanticAnswerGraph or Action
-> optional text realization
```

CEMM training must improve:

```text
semantic graph extraction
typed latent alignment
entity resolution
process/state/UOL mapping
predicate canonicalization
claim extraction
frame validity
memory retrieval ranking
causal model extraction
causal effect prediction
semantic answer composition
decision/action routing
text realization
synthesis verification
self-state calibration
structural induction
```

The training system is a continuous labeling, judging, distillation, evaluation, and promotion loop.

It is not one opaque fine-tuning job.

## 2. Training Law

```text
learn from events
train over meaning before text
prefer cheap labels first
use disagreement as signal
promote structure only after validation
never train on private data without permission
never let generated labels become active truth without trace
never allow embeddings to replace explicit truth, permission, time, source, or confidence
```

Invalid training shortcuts:

```text
text -> action
text -> answer
embedding -> text answer without SemanticAnswerGraph
generated label -> promoted memory
private trace -> public training example
```

Valid training target:

```text
text/context/memory -> semantic graph -> semantic answer/action -> realized text
```

## 3. Training Inputs

Training examples come from CEMM primitives and runtime packets:

```text
Signal
Entity
Claim
Model
Action
Self
Trace
Feedback
ContextKernel
SemanticEventGraph
SemanticAnswerGraph
```

High-value inputs:

```text
failed retrievals
user corrections
low-confidence answers
contradictions
tool failures
successful tool outcomes
high-latency traces
unsupported predicates
repeated manual fixes
synthesis verification failures
semantic graph parser disagreement
text realization verification failures
causal prediction misses
self-state miscalibration
```

Every runtime-derived example should include:

```text
input signal
full ContextKernel
selected claims/models
semantic graph if available
action decision
semantic answer graph if available
realized text if available
synthesis verification trace
outcome or feedback if available
```

## 4. Training Outputs

Training produces inactive artifacts first:

```text
labels
semantic graph targets
typed latent targets
candidate claims
candidate models
ranking updates
source trust updates
operator reliability updates
semantic answer targets
text realization examples
synthesis verifier examples
evaluation reports
promotion recommendations
```

Generated outputs must be stored as training artifacts until validated.

They must not directly become active memory, active models, or active policy.

## 5. Task Types

Each training job has one task type.

Core semantic tasks:

```text
semantic_graph_extraction
semantic_graph_denoising
semantic_latent_target
semantic_answer_composition
semantic_text_realization
next_event_prediction
```

Symbolic grounding tasks:

```text
entity_resolution
uol_mapping
predicate_mapping
claim_extraction
claim_canonicalization
context_inference
pragmatic_interpretation
frame_classification
contradiction_detection
temporal_relation_derivation
```

Reasoning/routing tasks:

```text
memory_retrieval_ranking
causal_rule_extraction
causal_effect_prediction
tool_handoff_planning
procedure_model_induction
operator_selection
ranking_judgment
```

Compatibility note:

```text
operator_selection trains the Decide operator.
It does not create a separate domain-specific operator family.
```

Safety/quality/learning tasks:

```text
synthesis_verification
verifier_calibration
self_state_update
structural_induction
```

## 6. Agent Roles

Parallel LLM/agent roles:

| Agent | Job |
|---|---|
| `semantic_graph_builder` | Convert signals/context into SemanticEventGraph targets |
| `semantic_graph_denoiser` | Repair corrupted or incomplete semantic graphs |
| `latent_teacher` | Produce typed latent supervision metadata, not raw vectors |
| `extractor` | Extract entities, claims, predicates, temporal refs |
| `uol_mapper` | Map language into entity refs, process atoms, and state atoms |
| `canonicalizer` | Map extracted structures to registry entries |
| `contextualist` | Infer temporary context from time, location, session position, world, memory, and self |
| `critic` | Find contradictions, missing evidence, invalid frames |
| `pragmaticist` | Detect speech act, target, affect, repetition, and likely cause |
| `causalist` | Extract causal preconditions/effects and judge predictions |
| `memory_ranker` | Judge Retrieve candidate relevance and ordering |
| `semantic_answerer` | Compose SemanticAnswerGraph targets |
| `text_realizer` | Realize verified semantic answers into text |
| `synthesis_judge` | Verify answer faithfulness to selected claims/models |
| `inductor` | Propose candidate models from repeated patterns |
| `arbiter` | Resolve disagreement and assign final label |

Use multiple cheap agents first.

Escalate to stronger models only when:

```text
agents disagree
confidence is low
risk is high
example is valuable
pattern may create new structure
semantic graph or answer graph would affect future promotion
```

## 7. Continuous Loop

```text
ingest_examples
-> create_training_jobs
-> run_parallel_agents
-> validate_json
-> score_disagreement
-> arbitrate_if_needed
-> write_labels
-> update_online_parameters
-> update inactive model artifacts
-> trigger_inductor_if_threshold_met
-> run_evaluations
-> recommend_promotions
```

Runtime integration loop:

```text
generated seed data
-> cemm_trainer.py labels/judges examples
-> trained rules/classifiers/rankers/semantic modules
-> cemm_runtime_router.py routes live turns
-> runtime traces export context-grounded semantic examples
-> cemm_trainer.py ingests runtime examples
-> promoted artifacts improve graph parsing, retrieval, routing, answer composition, realization, verification, and self-state
```

The runtime router must support:

```text
fast deterministic rules
model-backed semantic graph parsing
typed latent component loading
model-backed Decide routing
template/extractive text realization
soft neural fallback
trace writing
feedback-to-training export
```

## 8. Efficiency Strategy

Use a cascade:

```text
exact indexes
-> deterministic rules
-> small semantic models
-> parallel small agents
-> stronger arbiter
-> background induction
```

Cache everything by deterministic hash:

```text
task_type
prompt_version
model
input_payload_hash
registry_version
context_schema_version
```

Avoid repeated API calls for identical examples.

Batch only when examples share:

```text
task type
permission scope
prompt version
model target
registry version
```

Do not compute dense vectors when:

```text
typed index lookup is exact
required slots are missing
permission blocks retrieval
frame validity already excludes candidates
template realization is sufficient
```

## 9. Semantic Latent Training

The trainable core should learn typed latent spaces, not one undifferentiated embedding.

Detailed implementation phases for typed latents are defined in:

```text
cemm_original_work_subplans.md
```

Typed latent targets:

```text
entity latent
process latent
state latent
claim latent
model latent
context latent
self latent
memory latent
action latent
answer latent
```

Training objectives:

```text
reconstruct SemanticEventGraph from text/context
denoise corrupted SemanticEventGraph
predict missing entities/processes/states
align paraphrases to same semantic cluster
separate negation, uncertainty, time validity, and source trust
retrieve supporting memory
predict next semantic event
predict causal effects
compose SemanticAnswerGraph
realize SemanticAnswerGraph into faithful text
calibrate confidence
```

Loss families:

```text
type classification loss
slot/filler loss
contrastive latent loss
ranking loss
graph edge loss
causal effect loss
answer graph reconstruction loss
text realization faithfulness loss
calibration loss
permission violation penalty
cost-aware routing penalty
```

Rule:

```text
The model may learn embeddings for meaning.
The system must retain explicit symbolic fields for evidence, permission, time, negation, uncertainty, and confidence.
```

## 10. Confidence And Disagreement

Agent outputs must include:

```text
confidence
evidence_refs
uncertainty_reason
```

Disagreement score:

```text
disagreement =
  structure_mismatch
+ confidence_gap
+ evidence_mismatch
+ frame_mismatch
+ graph_edge_mismatch
+ answer_graph_mismatch
+ contradiction_flag
```

High disagreement examples become:

```text
arbiter jobs
evaluation examples
future fine-tuning examples
candidate model evidence
semantic parser hard cases
verifier hard cases
```

## 11. Online Updates

Safe online updates:

```text
source trust
foundational operator reliability
ranking weights
predicate alias counts
entity alias counts
semantic cluster alias counts
frame validity statistics
synthesis verifier thresholds
self mode calibration
self calibration metrics
```

Unsafe online updates:

```text
changing foundational operator semantics
promoting new predicates
promoting new entity types
promoting new causal rules
changing permission behavior
deleting memory
activating new latent encoders without evaluation
```

Unsafe updates require validation and explicit promotion.

## 12. Structural Induction

The Inductor runs in the background.

Trigger when:

```text
feedback_count exceeds threshold
same unsupported predicate repeats
same semantic graph gap repeats
same contradiction pattern repeats
same retrieval failure repeats
same synthesis failure repeats
causal pattern appears across examples
text realization repeatedly needs the same structure
```

Inductor output:

```text
Model(kind = "predicate" | "uol_semantic" | "entity_type" | "operator" | "causal_rule" | "frame_rule" | "context_rule" | "ranking_rule" | "synthesis_strategy" | "verifier" | "semantic_encoder" | "text_realizer")
```

Candidate models remain inactive until:

```text
validation tests pass
cost is acceptable
risk is acceptable
permission allows use
promotion policy approves
```

MVP Inductor is deterministic and limited to:

```text
Synonym aggregation:
  same subject/object type pairs + co-occurrence > 5
  -> candidate Model(kind = "predicate")

Semantic cluster aggregation:
  paraphrased UOL process/state pattern repeats > 5
  -> candidate Model(kind = "uol_semantic")

Sequential pattern mining:
  Action A followed by Signal B within 5 seconds
  -> candidate Model(kind = "causal_rule")
  confidence = support / (support + failures)

Slot completion:
  Goal missing slot repeatedly filled by same claim pattern
  -> candidate Model(kind = "context_rule")
```

Forbidden in MVP:

```text
novel ontological class invention without validation
autonomous foundational operator changes
unbounded arbitrary predicate search
embedding-only model promotion
```

## 13. Storage

Minimum training tables:

```text
training_examples
training_jobs
agent_runs
agent_outputs
training_labels
training_cache
eval_sets
eval_results
promotion_candidates
model_artifacts
```

Artifacts should be versioned by:

```text
task type
schema version
registry version
training data snapshot
model/provider
prompt version
evaluation result
promotion status
```

## 14. API Key Policy

API keys must come from environment variables.

Never store keys in:

```text
code
database
logs
training artifacts
trace output
```

The training runner should support:

```text
parallel workers
rate limits
budget limits
retry with backoff
provider adapters
local model adapter
dry-run mode
```

## 15. Day-One Implementation

Start with:

```text
SQLite queue
JSONL example ingest
NVIDIA API seed generation
basic runtime router
context-grounded runtime export
semantic graph target generation
semantic answer target generation
async worker pool
OpenAI-compatible HTTP adapter
prompt templates in code
strict JSON output parsing
cache by hash
arbiter on disagreement
candidate model output only
```

Detailed sequencing lives in:

```text
cemm_implementation_plan.md
cemm_original_work_subplans.md
```

Do not start with:

```text
custom GPU training
complex RL
unbounded agents
automatic model promotion
private data export
embedding-only answer decoding
```

Fine-tuning or custom GPU training comes after the JSONL/label/eval loop is stable.

## 16. Seed Generation

Seed generation should create scenarios, not word lists.

Use:

```text
cemm_seed_spec.json
cemm_seed_generator.py
```

Pipeline:

```text
seed spec
-> NVIDIA API scenario generation
-> task-specific JSONL records
-> cemm_trainer.py ingest
-> agent labeling / judging
-> eval and promotion pipeline
```

Required outputs:

```text
generated/cemm_generated_scenarios.jsonl
generated/cemm_generated_training.jsonl
```

Dry run:

```text
python3 cemm_seed_generator.py generate --dry-run --per-category 2
python3 cemm_seed_generator.py validate generated/cemm_generated_training.jsonl
```

NVIDIA run:

```text
export NVIDIA_API_KEY="..."
export NVIDIA_BASE_URL="https://integrate.api.nvidia.com/v1"
export NVIDIA_MODEL="meta/llama-3.1-70b-instruct"
python3 cemm_seed_generator.py generate --workers 4 --per-category 20
```

Trainer ingest:

```text
python3 cemm_trainer.py ingest generated/cemm_generated_training.jsonl
```

## 17. Success Metrics

Track:

```text
semantic graph extraction accuracy
semantic graph denoising accuracy
typed latent retrieval quality
claim extraction precision
entity resolution accuracy
predicate canonicalization accuracy
frame validity accuracy
memory retrieval recall@k
semantic answer graph correctness
text realization faithfulness
synthesis hard-gate pass rate
synthesis soft-verifier contradiction rate
decision routing accuracy
contradiction detection recall
causal prediction calibration
causal chain confidence calibration
frame-rule stale-claim prevention
recursive budget abort rate
temporal relation accuracy
cost per accepted label
latency per job
disagreement rate
promotion acceptance rate
```

## 18. Final Shape

CEMM-SLC training is not one model.

It is a continuous distillation system:

```text
events create examples
examples create jobs
agents create labels
labels create semantic graph targets
semantic graph targets train typed meaning
typed meaning composes semantic answer graphs
semantic answer graphs train faithful text realization
disagreement creates value
labels update parameters
patterns create candidate models
validation promotes structure
runtime improves without losing traceability
```
