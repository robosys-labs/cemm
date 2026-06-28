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
predicate_mapping
claim_extraction
claim_canonicalization
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
| `canonicalizer` | Map extracted structures to registry entries |
| `critic` | Find contradictions, missing evidence, invalid frames |
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
Model(kind = "predicate" | "entity_type" | "operator" | "causal_rule" | "frame_rule" | "ranking_rule" | "synthesis_strategy")
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

---

## 17. Practical PoC Training Approach

The fastest way to prove CEMM's trainability is a synthetic benchmark. No LLM calls needed.

### 17.1 Synthetic Data Generator

Generate structured event streams with known ground truth:

```text
Event: {actor, action, object, outcome, timestamp}
Ground truth: {correct_predicate, correct_entity, causal_rule}
```

Example stream (50-200 events):

```text
{"actor":"alice","action":"query","object":"postgres","outcome":"success","timestamp":1}
{"actor":"bob","action":"update","object":"mysql","outcome":"failure","timestamp":2}
{"actor":"alice","action":"query","object":"postgres","outcome":"success","timestamp":3}
{"actor":"alice","action":"save","object":"favorite_db","value":"Postgres","outcome":"success","timestamp":4}
{"actor":"charlie","action":"query","object":"sqlite","outcome":"timeout","timestamp":5}
```

Control `entity_frequency` (zipf) and `alias_noise` (0-20% alias variation) to stress-test entity resolution.

### 17.2 Training Loop Pseudocode

```text
train(stream, store, registry, learner, inductor, promoter):
  for chunk in stream.batches(batch_size=10):
    # Phase 1: Ingest
    for event in chunk:
      entity = resolve_or_create(event["actor"])
      claim = create_claim(entity, event["action"], event.get("value"), event["outcome"])
      store_claim(claim, event_signal)

    # Phase 2: Retrieve + Rank
    for event in chunk:
      results = retrieve(subject=entity.id, predicate=event["action"])
      ranked = rank(results)
      precision = precision_at_k(ranked, event["ground_truth"], k=3)
      log(f"precision@{k}", precision)

    # Phase 3: Feedback + Update
    for event in chunk:
      if feedback_available(event):
        learner.record_outcome(
          source_id=event["source"],
          domain="poc",
          success=(event["outcome"] == "success"),
        )
        learner.update_claim_confidence(
          claim_id=stored_claim.id,
          feedback_correct=(event["outcome"] == "success"),
        )

    # Phase 4: Induce + Promote
    if len(processed) % 50 == 0:
      candidates = inductor.maybe_induct(domain="poc")
      for model in candidates:
        ok, _ = promoter.can_promote(model)
        if ok:
          promoter.promote(model.id)
```

### 17.3 PoC Benchmark Script

Location: `C:\dev\cemm\scripts\poc_train.py`

```python
# Key metrics to collect over 5 runs:
metrics = {
    "retrieval_precision_at_1": [],   # % correct at rank 1
    "retrieval_precision_at_3": [],   # % correct in top 3
    "confidence_calibration": [],     # MSE(confidence, accuracy) per bucket
    "source_trust_convergence": [],   # trust value after N outcome records
    "induction_precision": [],        # % candidate models matching ground truth
    "induction_recall": [],           # % ground-truth rules discovered
    "promotion_acceptance_rate": [],  # % candidates that pass promotion gate
    "avg_latency_ms": [],             # per-event ingest+retrieve time
}
```

### 17.4 Expected Results

| Metric | Minimum Viable | Target |
|---|---|---|
| Retrieval precision@3 | >0.60 | >0.85 |
| Source trust convergence (after 10 records) | >0.80 | >0.95 |
| Confidence calibration error | <0.20 | <0.10 |
| Induction recall (after 200 events) | >0.40 | >0.70 |
| Promotion acceptance | 100% valid | 100% valid |
| Per-event latency | <50ms | <10ms |

### 17.5 What This Proves

- **Entity resolution works**: repeated actors resolve to the same entity via any alias
- **Claims persist faithfully**: stored claims survive write/read round-trips
- **Source trust learns**: sources with better outcomes get higher trust
- **Confidence responds to feedback**: correct claims gain confidence, incorrect lose it
- **Structural induction discovers rules**: repeated predicate+effect pairs create candidate models
- **Promotion enforces gates**: candidates only promote when evidence and confidence thresholds are met
- **Causal inference predicts**: once causal_rule models are promoted, `predict()` returns relevant effects
```

