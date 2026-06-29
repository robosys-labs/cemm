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
python3 cemm_runtime_router.py once "how are you"
python3 cemm_runtime_router.py once "who are you"
python3 cemm_runtime_router.py once "what can you do"
python3 cemm_runtime_router.py once "where are you"
```

Interactive:

```bash
python3 cemm_runtime_router.py chat
```

Inspect context:

```bash
python3 cemm_runtime_router.py show-context
python3 cemm_runtime_router.py show-context --json
```

## Runtime Path

```text
connect/seed_entities
-> build_context (creates 9-section ContextKernel + SelfView)
-> observe (writes signal)
-> normalize (slang/typo/contraction map + repeat-char reduction)
-> infer_context (context-grounded, permission-aware)
-> map_uol (process/state atoms)
-> extract_or_retrieve_claims
-> route_operator (ContextKernel + signals + permissions)
-> synthesize (self-grounded via SelfView)
-> write_action_trace (full ContextKernel in trace_json)
-> update_self_after_turn (uncertainty, coherence, load, epistemic)
```

## What Works In The Basic Router

```text
greetings (hi+/hello+/hey+)
remember user facts
recall user facts
weather/location clarification
correction supersession ("actually", "wait", "no,")
negative evaluation routing
informal opener ("what's going on/up")
assistant location question ("where are you")
self-grounded identity ("who are you" → self_state.identity.name)
self-grounded status ("how are you" → SelfView.uncertainty/coherence)
self-grounded capability ("what can you do" → SelfView.known_limit_claim_ids)
world-grounded location ("where are you" → world_state.assistant_location or env vars)
static small talk (thanks, bye, etc.)
trace writing
SQLite memory (signals, claims with supersede, actions, traces, self_state, world_state)
entity seeding (entities + entity_aliases tables)
```

## ContextKernel Sections

```text
world         — assistant_location, knowledge_freshness, active_frame_ids
user          — entity_id, location, affect (valence/arousal/frustration/hostility)
time          — now_unix, bucket, session_elapsed_s, since_last_user_signal_s
conversation  — session_id, turn_index, phase, recent_signal_ids, active_repetition_groups
goal          — active_goal_id, required_slots, missing_slots, success_criteria
memory        — working_signal_ids, candidate_claim_ids, active_frame_ids, source_trust
self_state    — dict with identity, internal (mode/uncertainty/coherence/load), epistemic, meta_memory, historical_arc
self_view     — SelfView dataclass computed from self_state (architected type from types/self_view.py)
permission    — scope, can_use_user_memory, can_write_user_memory, can_call_external_tools
budget        — latency_target_ms, max_claim_candidates, max_recent_signals
```

## 4. Feed Runtime Back Into Training

After using the router, export grounded runtime examples:

```bash
python3 cemm_runtime_router.py export-training --out generated/cemm_runtime_training.jsonl
```

Each turn generates 5-7 training examples (context_inference, uol_mapping, operator_selection,
plus conditional claim_extraction, predicate_mapping, pragmatic_interpretation,
synthesis_verification, self_state_update) — all with the full ContextKernel attached.

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

