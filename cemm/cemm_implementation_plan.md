# CEMM-SLC Implementation Plan

Version: 1.0  
Purpose: phased build plan for the CEMM runtime and CEMM-SLC training path.

## 1. Build Principle

Implement in layers.

```text
make the trace correct
make the memory bounded
make the semantic packets explicit
make the training export useful
then replace deterministic internals inside foundational operators with learned components
```

Do not promote final-architecture features into the MVP unless they are needed for a working conversation loop.

Foundational operators are fixed:

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

Do not add top-level domain operators.

New use cases add:

```text
Models
Claims
Entities
registry entries
style policies
permission policies
training examples
```

Detailed sub-plans for original CEMM work live in:

```text
cemm_original_work_subplans.md
```

Use that document for:

```text
typed latent spaces
SemanticEventGraph
SemanticAnswerGraph
packet layer
online trust learning
procedure/tool skill models
semantic-to-text realization
```

## 2. Phase 0: Bootstrap Runtime

Goal:

```text
usable basic conversation with valid CEMM traces
```

Implement:

```text
Signal table
Claim table
Action table
Trace table
Self state table
World state table
ContextKernel builder
UOL mapping
SemanticEventGraph packet
Claim extraction/retrieval
SemanticAnswerGraph packet
template text realization
basic synthesis verification flag
runtime export to trainer JSONL
```

Allowed behavior:

```text
greeting
remember user fact
recall user fact
ask for missing location
abstain on fresh-world request when tools are disabled
detect repeated negative evaluation within a session
update temporary user affect
update basic Self state
```

Not Phase 0:

```text
vector search
custom embedding training
causal simulation
recursive reflection
background induction
neural text generation
external tool execution
multi-user memory conflict handling
```

Performance requirements:

```text
single-turn latency target: <= 50 ms without model calls
SQLite only
no dense fallback
bounded recent signals
bounded claim candidates
```

Schema cleanup required in Phase 0:

```text
signals.session_id real column
signals.context_id real column
traces.context_id real column
canonical ContextKernel budget names
permission scope = session_private for local runtime sessions
```

## 3. Phase 1: Grounded Training Loop

Goal:

```text
turn runtime traces and generated scenarios into useful labels
```

Implement:

```text
seed generation from cemm_seed_spec.json
trainer ingest
parallel prompt workers
strict JSON parsing
response cache
runtime export
semantic graph extraction tasks
semantic answer composition tasks
text realization tasks
synthesis verification tasks
memory retrieval ranking tasks
```

Phase 1 task set:

```text
semantic_graph_extraction
uol_mapping
claim_extraction
memory_retrieval_ranking
tool_handoff_planning
operator_selection
semantic_answer_composition
semantic_text_realization
synthesis_verification
context_inference
pragmatic_interpretation
self_state_update
```

Not Phase 1:

```text
automatic model promotion
custom GPU training
embedding-only decoding
unbounded agents
private data export
```

## 4. Phase 2: Learned Components

Goal:

```text
replace deterministic internals one foundational operator at a time
```

Promotion order:

```text
1. Interpret
2. Ground
3. Retrieve
4. Infer
5. Decide
6. Realize
7. Update
8. Learn
```

Every promoted component must declare:

```text
artifact id
schema version
registry version
training data snapshot
eval result ids
known failure modes
fallback behavior
permission constraints
latency budget
```

Runtime must keep deterministic fallback for every learned component.

Foundational operators remain stable.

New domains add:

```text
Models
Claims
Entities
registry entries
style policies
permission policies
```

not new top-level operators.

## 5. Phase 3: Causal And Recursive Runtime

Goal:

```text
support prediction, repair, and bounded internal reflection
```

Implement:

```text
causal_rule models
causal effect prediction
procedure model execution planning
bounded transitive closure
simulation_result signals
action_result signals
recursive signal re-entry
budget consumption across recursion
reflect action
self mode changes through trace
```

Strict limits:

```text
max_recursive_steps defaults to 1
simulation produces predictions, not facts
external actions are blocked inside recursion unless explicitly permitted
```

## 6. Phase 4: Structural Learning

Goal:

```text
create candidate Model records from repeated validated patterns
```

MVP induction heuristics:

```text
synonym aggregation
semantic cluster aggregation
sequential pattern mining
slot completion
procedure model induction
```

Forbidden:

```text
autonomous operator promotion
unvalidated ontology expansion
embedding-only model promotion
silent permission-policy changes
```

## 7. Data Layout Guidance

Use primitive tables first:

```text
signals
entities
claims
models
actions
self_state
traces
```

Materialized/cache tables are allowed only after they show measured value:

```text
source_trust_cache
context_snapshots
semantic_event_graph_cache
semantic_answer_graph_cache
embedding_cache
retrieval_cache
```

Cache promotion requires:

```text
clear latency win
bounded invalidation rule
traceable source primitive ids
permission-safe contents
measured reuse
```

## 8. Runtime Export Limits

Do not emit every possible task forever.

Phase 0 export defaults:

```text
semantic_graph_extraction
semantic_latent_target
context_inference
uol_mapping
operator_selection
semantic_answer_composition
synthesis_verification
semantic_text_realization
self_state_update
```

Export priority should increase for:

```text
low confidence
abstain
missing slot
user correction
repeated pragmatic signal
retrieval failure
synthesis verification failure
```

Export should support future caps:

```text
max_examples_per_signal
min_priority
task_type allowlist
permission_scope filter
```

## 9. Current Known Gaps

The current scripts are bootstrap-quality.

Known gaps:

```text
runtime still uses deterministic parsing/routing
semantic graphs are lightweight trace packets, not learned parser outputs
semantic latents are supervised metadata, not trained vectors
trainer labels through LLM prompts, not custom model training
no artifact promotion registry yet
no evaluator/promotion gate yet
```

These are acceptable only because deterministic fallbacks and trace export exist.
