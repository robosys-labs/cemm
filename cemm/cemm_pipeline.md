# CEMM End-to-End Pipeline

This workspace now has three layers:

```text
1. cemm_seed_generator.py
   Generates scenario/context/task seed data.

2. cemm_trainer.py
   Labels, judges, verifies, and induces structure from task data.

3. cemm_runtime_router.py
   Runs a basic live conversation loop using CEMM routing logic.
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

## 2. Label And Judge

```bash
python3 cemm_trainer.py ingest generated/cemm_generated_training.jsonl
python3 cemm_trainer.py run --workers 8
```

Dry run:

```bash
python3 cemm_trainer.py ingest generated/cemm_generated_training.jsonl
python3 cemm_trainer.py run --workers 8 --dry-run
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

## Runtime Path

```text
observe
-> build_context_kernel
-> infer_context
-> map_uol
-> extract_or_retrieve_claims
-> route_operator
-> synthesize
-> write_trace
```

## What Works In The Basic Router

```text
greetings
remember user facts
recall user facts
weather/location clarification
simple frustration handling
trace writing
SQLite memory
```

## Next Model Step

Replace the current deterministic router functions with trained components:

```text
ContextInferenceModel
UOLMapper
ClaimExtractor
MemoryRanker
OperatorRouter
SynthesisVerifier
```

The runtime API stays stable while the internals become learned.

