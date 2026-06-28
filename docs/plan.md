# CEMM — Contextual Event Memory Model

## Implementation Plan

### Overview

CEMM is a pure-Python implementation of the ERCA (Efficient Recursive Context Architecture) v2.0 specification. It implements 6 primitives (Signal, Entity, Claim, Model, Action, Self), a SQLite store with 10 tables and 16 indexes, a typed operator dispatch system, structural retrieval with confidence scoring, causal inference, a synthesis router, and online learning.

### Project Structure

```
C:\dev\cemm\
├── pyproject.toml
├── cemm/
│   ├── __init__.py
│   ├── types/           # Data type definitions (dataclasses + enums)
│   ├── store/           # SQLite persistence layer (10 tables)
│   ├── confidence/      # Log-odds math and scoring formulas
│   ├── registry/        # Predicate/entity/operator canonicalization
│   ├── kernel/          # ContextKernel builder + pipeline runtime
│   ├── retrieval/       # Structural retrieval + ranking
│   ├── operators/       # 10 typed operators (answer..abstain)
│   ├── synthesis/       # Template/extractive router + verifier
│   ├── causal/          # Causal inference + simulation engine
│   └── learning/        # Online learning, inductor, promotion
├── tests/
│   ├── invariants/      # 18 ERCA invariant tests (drift-proof anchors)
│   ├── test_signal.py
│   ├── test_entity.py
│   ├── test_claim.py
│   ├── test_model.py
│   ├── test_action.py
│   ├── test_self.py
│   ├── test_store.py
│   ├── test_pipeline.py
│   ├── test_causal.py
│   ├── test_confidence.py
│   ├── test_registry.py
│   └── test_acceptance.py
└── docs/
    ├── milestones.md
    └── plan.md
```

### Architecture

```
InputEnvelope
  -> ContextKernelBuilder (signal → kernel)
  -> Normalizer (predicate canonicalization via Registry)
  -> EntityResolver (name/alias resolution, auto-create)
  -> StructuralRetriever (index-first retrieval)
  -> Ranker (confidence * trust * recency scoring)
  -> CausalInference (precondition/effect matching)
  -> FrameEngine (temporal validity, supersession)
  -> Operator dispatch (answer/ask/remember/...)
  -> Synthesis Router (template/extractive)
  -> SynthesisVerifier (output validation)
  -> Trace emission + online learning
  -> Internal signals (memory_update, reflection)
```

### Invariants (Drift-Proof Anchors)

The test suite asserts 18 invariants from the ERCA spec:

1. Input not interpreted before ContextKernel exists
2. Response has input signal
3. Claim has evidence signal
4. Model has evidence signal
5. Memory mutation has action trace
6. Self mutation has signal and action trace
7. Private claim permission gates
8. Disputed claim not presented as certain
9. Prediction not presented as observed fact
10. Operator executes with required slots
11. Vector result not bypassing claim/model ranking
12. Recursive step within budget
13. External action permission inside recursion
14. Model promoted only after validation
15. Claim ranked within valid frame
16. Answer verifies synthesis output
17. Response uses only selected claims/models
18. Output preserves uncertainty

### Running Tests

```bash
cd C:\dev\cemm
python -m pytest tests/ -v
python -m pytest tests/invariants/ -v
python -m pytest tests/test_acceptance.py -v
```
