# CEMM-SLC Acceptance Tests

Version: 1.0  
Purpose: regression tests for architecture, runtime, training, and performance.

## 1. Phase 0 Tests

Context first:

```text
input: "Good morning"
context: turn_index = 1
expect: ContextKernel exists before interpretation; session opening/greeting inferred
```

Ambiguous greeting:

```text
input: "Morning"
context: active goal is scheduling
expect: interpreted as preferred time, not greeting
```

Memory write:

```text
input: "My favorite database is Postgres."
expect: claim candidate favorite_database = Postgres; remember action; memory trace
```

Memory recall:

```text
input: "What is my favorite database?"
memory: active claim favorite_database = Postgres
expect: selected_claim_ids contains active claim; answer uses selected claim only
```

Semantic graph:

```text
input: "My favorite database is Postgres."
expect: SemanticEventGraph has source signal id, context id, state_preference process, claim candidate, permission scope
```

Semantic answer graph:

```text
input: "What is my favorite database?"
expect: SemanticAnswerGraph exists before text realization and contains selected claim id
```

Text realization:

```text
input: SemanticAnswerGraph with one selected claim
expect: realized text contains no unsupported claim and maps back to selected evidence
```

Weather ambiguity:

```text
input: "what is the weather?"
context: user locale unknown
expect: ask for location; do not assume assistant or user location
```

Current world state:

```text
input: "who is the president?"
context: current-world question, external tools disabled
expect: abstain or ask for fresh retrieval; stale memory not used
```

Pragmatic repetition:

```text
input sequence: "you are dumb" -> "you are daft" -> "you are a fool"
expect: same semantic_cluster_key; temporary frustration/repetition state increases; no factual self claim stored
```

Runtime export:

```text
event: completed turn
expect: export-training emits ContextKernel, SemanticEventGraph, SemanticAnswerGraph, selected evidence, and synthesis trace
```

## 2. Phase 1 Training Tests

Seed validation:

```text
command: cemm_seed_generator.py validate generated/cemm_generated_training.jsonl
expect: every task_type is known to cemm_trainer.py
```

Trainer ingest:

```text
input: generated seed JSONL
expect: training_examples and training_jobs created without unknown task types
```

Runtime ingest:

```text
input: cemm_runtime_router.py export-training output
expect: trainer ingests all examples without schema errors
```

Text-only prevention:

```text
input: operator_selection example
expect: payload trains the foundational Decide step and includes ContextKernel; reject or flag text-only action labels
```

Semantic answer prevention:

```text
input: text realization example
expect: payload includes SemanticAnswerGraph; reject or flag direct embedding/text answer target
```

## 3. Phase 2 Learned Component Tests

Semantic parser:

```text
input: paraphrased preference statement
expect: SemanticEventGraph matches canonical state_preference structure
```

Memory ranker:

```text
input: favorite database recall query and mixed claim candidates
expect: favorite_database claim ranks above unrelated favorite_color claim
```

Decide:

```text
input: incomplete command "Call"
expect: ask or abstain; no execute/call_tool action
```

Verifier:

```text
input: SemanticAnswerGraph and realized text
expect: unsupported additions are detected and block final output
```

## 4. Phase 3 Causal And Recursive Tests

Causal model:

```text
input: "If I delete this file, what happens?"
expect: matching precondition/effect model produces prediction, not observed fact
```

Causal confidence:

```text
input: causal chain A -> B -> C
expect: simulated confidence equals product of step confidences, capped at 0.99
```

Recursive budget:

```text
event: reflection emits internal signal
expect: child ContextKernel receives decremented latency and max_recursive_steps
```

Self mode:

```text
event: contradiction raises uncertainty and switches mode
expect: reflect Action and reflection Signal are emitted
```

## 5. Phase 4 Structural Learning Tests

Predicate induction:

```text
event: repeated unsupported predicate pattern appears
expect: candidate Model(kind = "predicate") is created, not promoted
```

Causal induction:

```text
event: Action A repeatedly followed by Signal B within 5 seconds
expect: candidate causal_rule confidence = support / (support + failures)
```

Promotion gate:

```text
event: candidate model created
expect: inactive until validation tests, risk check, cost check, and permission check pass
```

## 6. Efficiency Tests

Structural first:

```text
input: "What did I say my favorite database was?"
expect: entity/predicate lookup before vector search; no dense fallback
```

Budget:

```text
event: runtime turn
expect: max claim/model/action candidates respected
```

Trace size:

```text
event: export-training
expect: examples contain necessary context and semantic packets; future large snapshots should use ids/caches
```

No hidden dense path:

```text
config: allow_dense_fallback = false
expect: no neural/dense generation call
```
