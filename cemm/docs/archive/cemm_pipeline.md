# CEMM-SLC End-to-End Pipeline

This workspace has four practical layers:

```text
1. cemm_seed_generator.py
   Generates scenario/context/semantic task seed data.

2. cemm_trainer.py
   Labels, judges, verifies, denoises, ranks, and induces structure from task data.

3. cemm_runtime_router.py
   Runs a basic live conversation loop using CEMM routing and trace logic.

4. Future promoted artifacts
   Replace deterministic runtime internals with trained semantic modules.
```

Planning and tests:

```text
cemm_implementation_plan.md
cemm_original_work_subplans.md
cemm_acceptance_tests.md
```

The target model shape is:

```text
Signal + ContextKernel + Memory
-> SemanticEventGraph
-> typed latent computation
-> SemanticAnswerGraph or Action
-> optional text realization
```

It is not:

```text
text -> text
text -> action
embedding -> text answer
```

## 1. Generate Seed Data

Dry run:

```bash
python3 cemm_seed_generator.py generate --dry-run --per-category 2 --limit-categories 3 --out-dir generated
python3 cemm_seed_generator.py validate generated/cemm_generated_training.jsonl
```

NVIDIA API:

```bash
export NVIDIA_API_KEY="..."
export NVIDIA_BASE_URL="https://integrate.api.nvidia.com/v1"
export NVIDIA_MODEL="meta/llama-3.1-70b-instruct"

python3 cemm_seed_generator.py generate --workers 4 --per-category 20 --out-dir generated
```

Seed data should include:

```text
ContextKernel examples
SemanticEventGraph examples
UOL process/state mappings
claim extraction examples
memory retrieval ranking examples
causal effect examples
SemanticAnswerGraph examples
text realization examples
synthesis verification examples
self-state update examples
structural induction examples
```

## 2. Label And Judge

```bash
python3 cemm_trainer.py ingest generated/cemm_generated_training.jsonl
python3 cemm_trainer.py run --workers 8
```

Dry run:

```bash
python3 cemm_trainer.py ingest generated/cemm_generated_training.jsonl
python3 cemm_trainer.py run --workers 8 --dry-run --once
```

The trainer currently produces labeled/judged artifacts through task prompts.

It is intentionally not yet a custom GPU trainer.

The promotion path should come later:

```text
agent labels
-> validated training labels
-> eval sets
-> trained component artifact
-> promotion candidate
-> runtime loader
```

## 3. Run Basic Conversation Router

Single turn:

```bash
python3 cemm_runtime_router.py once "Good morning"
python3 cemm_runtime_router.py once "My favorite database is Postgres."
python3 cemm_runtime_router.py once "What is my favorite database?"
```

Interactive:

```bash
python3 cemm_runtime_router.py chat
```

Current runtime path:

```text
observe
-> build_context_kernel
-> interpret
-> ground
-> retrieve
-> infer
-> decide
-> realize
-> update
```

The runtime path is context-grounded. The router receives:

```text
world state
user state
time state
conversation state
goal state
memory state
self state
permission state
compute budget
```

The trained router should learn:

```text
signal + ContextKernel + SemanticEventGraph + selected memory -> typed action or SemanticAnswerGraph
```

In training files, the existing task name `operator_selection` means:

```text
train the foundational Decide step
```

It should not learn:

```text
signal text -> action
```

## 4. Feed Runtime Back Into Training

After using the router, export grounded runtime examples:

```bash
python3 cemm_runtime_router.py export-training --out generated/cemm_runtime_training.jsonl
python3 cemm_trainer.py ingest generated/cemm_runtime_training.jsonl
python3 cemm_trainer.py run --workers 8 --dry-run --once
```

Runtime exports include:

```text
full ContextKernel
semantics
SemanticEventGraph
selected claims
SemanticAnswerGraph
realized text
synthesis verification
self-state update context
```

## 5. What Works Now

The current bootstrap runtime supports:

```text
greetings
remember user facts
recall user facts
weather/location clarification
fresh-world abstention when tools are disabled
simple frustration/repetition handling
SemanticEventGraph trace objects
SemanticAnswerGraph trace objects
SQLite memory
self-state updates
runtime-to-training export
```

## 6. What Is Still Missing

The current runtime does not yet contain the trained CEMM-SLC model.

Missing components:

```text
Interpret model artifact
Ground model artifact
Retrieve ranker artifact
Infer model artifact
Decide model artifact
Realize model artifact
Verifier artifact
promotion/evaluation registry
```

The deterministic router remains the fallback path.

## 7. Promotion Plan

The detailed phased plan lives in:

```text
cemm_implementation_plan.md
```

Do not replace the whole runtime at once.

Promote components in this order:

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

Each promoted artifact must include:

```text
schema version
registry version
training data snapshot
eval results
known failure modes
fallback behavior
permission constraints
```

## 8. Regression Gates

Fail the pipeline if:

```text
training example lacks ContextKernel
router trains on text-only action labels
text realization bypasses SemanticAnswerGraph
runtime answer uses unselected claims
embedding output overrides permission or frame validity
generated labels are promoted without eval
private runtime traces are exported as public data
```
