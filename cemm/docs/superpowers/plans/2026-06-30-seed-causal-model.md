# Seed a Causal Model for Runtime Inference

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this task.

**Goal:** Close the causal inference gap by seeding a simple causal rule model so `CausalInference.predict` can produce predictions when the user asks about causal events. This enables the causal inference path to actually produce output and lets the simulation engine run.

**Architecture:** `CausalInference` searches `store.models` for `ModelKind.CAUSAL_RULE` with `ModelStatus.ACTIVE`. We add a model to `seed_registry` (or a new `seed_causal_models` helper) that maps a precondition to an effect. The pipeline's `CausalInference` step will then populate `inference_packet.predictions`.

**Tech Stack:** Python 3.13, Model, CausalInference, seed_registry.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `cemm/__main__.py` | Seed causal models | Modify |
| `cemm/tests/test_causal_inference.py` | Tests | Create |

---

## Task 1: Seed causal rule model

**Files:**
- Modify: `cemm/__main__.py`
- Create: `cemm/tests/test_causal_inference.py`

- [ ] **Step 1: Add seed causal model**

In `__main__.py`, add a `seed_causal_models` helper and call it from `seed_registry` or from the main block.

```python

def seed_causal_models(store: Store) -> None:
    """Seed a small causal rule model so CausalInference can produce predictions."""
    from .types.model import Model, ModelKind, ModelStatus
    existing = store.models.find_by_kind(ModelKind.CAUSAL_RULE.value, ModelStatus.ACTIVE.value)
    if existing:
        return
    model = Model(
        id="causal_rain_flooding",
        name="rain causes flooding",
        registry_key="causal_causes",
        kind=ModelKind.CAUSAL_RULE,
        status=ModelStatus.ACTIVE,
        preconditions=["rain"],
        effects=["flooding"],
        confidence=0.8,
        trust=0.9,
        risk=0.1,
        evidence_signal_ids=["seed"],
        owner="system",
        permission=Permission.public(),
    )
    store.models.put(model)
```

Call it in `seed_registry` or in the main block after `seed_self_state`.

- [ ] **Step 2: Write test**

```python
# cemm/tests/test_causal_inference.py
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.store.store import Store
from cemm.registry import Registry
from cemm.kernel.pipeline import Pipeline
from cemm.learning.online import OnlineLearner
from cemm.learning.inductor import Inductor
from cemm.kernel.recursive_loop import RecursiveLoop
from cemm.operators.registry import OperatorRegistry
from cemm.operators.answer import AnswerOperator
from cemm.operators.ask import AskOperator
from cemm.operators.remember import RememberOperator
from cemm.operators.abstain import AbstainOperator
from cemm.__main__ import seed_registry, seed_self_state, seed_causal_models, process_input


def _setup():
    store = Store(":memory:")
    registry = Registry()
    op_registry = OperatorRegistry()
    pipeline = Pipeline(store, registry)
    online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    inductor = Inductor(store, registry=registry)
    recursive_loop = RecursiveLoop(pipeline, store, online_learner, inductor)
    seed_registry(registry)
    seed_self_state(store)
    seed_causal_models(store)
    for op in [AnswerOperator(), AskOperator(), RememberOperator(), AbstainOperator()]:
        op_registry.register(op)
    return store, registry, op_registry, pipeline, online_learner, recursive_loop


def test_causal_inference_populates_predictions():
    store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
    # Store the causal claim first
    process_input("remember rain causes flooding", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    # Then ask about the effect
    output = process_input("what happens if it rains", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    assert output is not None
    assert "flood" in output.lower(), output
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest cemm/tests/test_causal_inference.py -v`
Expected: PASS

- [ ] **Step 4: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 5: Run manual integration test**

Run: `python manual_integration_test.py`
Expected: 25 cases, 0 gaps

- [ ] **Step 6: Commit**

```bash
git add cemm/__main__.py cemm/tests/test_causal_inference.py
git commit -m "feat: seed causal rule model and enable runtime causal inference"
```

---

## Self-Review

### Spec Coverage

| Gap | Coverage |
|---|---|
| Causal inference never produces predictions | A causal rule model is seeded and can produce predictions. |

### Placeholder Scan

No placeholders.
