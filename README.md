# CEMM

**A trainable event-centered memory model for context-aware agents.**

CEMM is a pure-Python implementation of the ERCA (Efficient Recursive Context Architecture) v2.0 specification — a lean, practical architecture for context, memory, self-state, causal reasoning, recursive reflection, structural learning, and action.

## Core Primitives

| Primitive | Meaning | Main Question |
|---|---|---|
| `Signal` | Something observed | What happened? |
| `Entity` | Something identified | What thing is this? |
| `Claim` | Something believed | What is asserted? |
| `Model` | A reusable structure or process | How does this work? |
| `Action` | Something done or considered | What should happen next? |
| `Self` | The system's persistent self-state | What am I, and how am I changing? |

## Project Structure

```
cemm/
├── types/       # Data type definitions (dataclasses + enums)
├── store/       # SQLite persistence (10 tables, 16 indexes)
├── confidence/  # Log-odds math and scoring formulas
├── registry/    # Predicate/entity/operator canonicalization
├── kernel/      # ContextKernel builder + pipeline runtime
├── retrieval/   # Structural retrieval + ranking
├── operators/   # 10 typed operators (answer..abstain)
├── synthesis/   # Template/extractive router + verifier
├── causal/      # Causal inference + simulation engine
└── learning/    # Online learning, inductor, promotion
```

## Quick Start

```bash
cd C:\dev\cemm

# Run tests
python -m pytest cemm/tests -q

# Start interactive session
python -m cemm
```

## Running

```bash
python -m cemm                    # Interactive chat
python -m cemm --eval "What is my favorite database?"  # Single query
python -m cemm --db path/to/db.sqlite                   # Persistent store
python -m cemm.web_demo           # Browser demo at http://127.0.0.1:5000
```

## Architecture

```
InputEnvelope
  -> ContextKernelBuilder (signal -> kernel)
  -> Normalizer (predicate canonicalization via Registry)
  -> EntityResolver (name/alias resolution)
  -> StructuralRetriever (index-first retrieval)
  -> Ranker (confidence * trust * recency scoring)
  -> CausalInference (precondition/effect matching)
  -> FrameEngine (temporal validity, supersession)
  -> Operator dispatch (answer/ask/remember/...)
  -> Synthesis Router (template/extractive/neural)
  -> SynthesisVerifier (output validation)
  -> Trace emission + online learning
  -> Internal signals (memory_update, reflection)
```

## Tests

91 tests covering:
- 18 ERCA v2.0 invariants (drift-proof contract)
- 4 acceptance scenarios (context, memory, permission, synthesis)
- Store CRUD for all 7 subsystems
- Confidence math (log-odds, scoring)
- Registry (canonicalization, JSON round-trip)
- Causal inference (prediction, simulation, closure)
- Pipeline (signal persistence, kernel construction)
