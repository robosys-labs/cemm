# CEMM Training Architecture

Version: 1.0  
Purpose: an efficient continuous training architecture for the Contextual Event Memory Model.

## 1. Goal

CEMM training must improve:

```text
entity resolution
predicate canonicalization
claim extraction
frame validity
causal model extraction
claim ranking
model ranking
operator routing
synthesis verification
self-state calibration
structural induction
```

The training system should not be one giant model-training job.

It should be a continuous labeling, judging, distillation, and induction loop.

## 2. Training Law

```text
learn from events
prefer cheap labels first
use disagreement as signal
promote structure only after validation
never train on private data without permission
never let generated labels become truth without trace
```

## 3. Training Inputs

Training examples come from CEMM primitives:

```text
Signal
Entity
Claim
Model
Action
Self
Trace
Feedback
```

Best high-value inputs:

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
```

## 4. Training Outputs

Training produces:

```text
labels
candidate claims
candidate models
ranking updates
source trust updates
operator reliability updates
synthesis verifier examples
evaluation reports
promotion recommendations
```

Generated outputs must be stored as training artifacts until validated.

They must not directly become active memory.

## 5. Task Types

Each training job has one task type.

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
causal_rule_extraction
operator_selection
synthesis_verification
self_state_update
structural_induction
ranking_judgment
```

## 6. Agent Roles

Parallel LLM/agent roles:

| Agent | Job |
|---|---|
| `extractor` | Extract entities, claims, predicates, temporal refs |
| `uol_mapper` | Map language into entity refs, process atoms, and state atoms |
| `canonicalizer` | Map extracted structures to registry entries |
| `contextualist` | Infer temporary context from time, location, session position, world state |
| `critic` | Find contradictions, missing evidence, invalid frames |
| `pragmaticist` | Detect speech act, target, affect, repetition, and likely cause |
| `causalist` | Extract causal preconditions and effects |
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
-> trigger_inductor_if_threshold_met
-> run_evaluations
-> recommend_promotions
```

## 8. Efficiency Strategy

Use a cascade:

```text
rules
-> small model
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
```

Avoid repeated API calls for identical examples.

Batch only when examples share:

```text
task type
permission scope
prompt version
model target
```

## 9. Confidence And Disagreement

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
+ contradiction_flag
```

High disagreement examples become:

```text
arbiter jobs
evaluation examples
future fine-tuning examples
candidate model evidence
```

## 10. Online Updates

Safe online updates:

```text
source trust
operator reliability
ranking weights
predicate alias counts
entity alias counts
frame validity statistics
synthesis verifier thresholds
self calibration metrics
```

Unsafe online updates:

```text
promoting new operators
promoting new predicates
promoting new causal rules
changing permission behavior
deleting memory
```

Unsafe updates require validation and explicit promotion.

## 11. Structural Induction

The Inductor runs in the background.

Trigger when:

```text
feedback_count exceeds threshold
same unsupported predicate repeats
same contradiction pattern repeats
same retrieval failure repeats
same synthesis failure repeats
causal pattern appears across examples
```

Inductor output:

```text
Model(kind = "predicate" | "uol_semantic" | "entity_type" | "operator" | "causal_rule" | "frame_rule" | "context_rule" | "ranking_rule" | "synthesis_strategy")
```

Candidate models remain inactive until:

```text
validation tests pass
cost is acceptable
risk is acceptable
permission allows use
promotion policy approves
```

## 12. Storage

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
```

## 13. API Key Policy

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

## 14. Day-One Implementation

Start with:

```text
SQLite queue
JSONL example ingest
async worker pool
OpenAI-compatible HTTP adapter
prompt templates in code
strict JSON output parsing
cache by hash
arbiter on disagreement
candidate model output only
```

Do not start with:

```text
fine-tuning
custom GPU training
complex RL
unbounded agents
automatic model promotion
private data export
```

## 15. Success Metrics

Track:

```text
claim extraction precision
entity resolution accuracy
predicate canonicalization accuracy
frame validity accuracy
synthesis faithfulness
operator selection accuracy
contradiction detection recall
causal prediction calibration
cost per accepted label
latency per job
disagreement rate
promotion acceptance rate
```

## 16. Final Shape

CEMM training is not one model.

It is a continuous distillation system:

```text
events create examples
examples create jobs
agents create labels
disagreement creates value
labels update parameters
patterns create candidate models
validation promotes structure
runtime improves without losing traceability
```
