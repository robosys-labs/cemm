# SAG-less Training Export Records

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this task.

**Goal:** Ensure training export records always contain a `SemanticAnswerGraph` for non-answer/abstain operators, so downstream trainers and validators have consistent SAG supervision. This closes the remaining training-export gap.

**Architecture:** `process_input()` in `__main__.py` exports training records via `serialize_turn()`. For `answer` and `abstain` operators, the `op_result` carries a `semantic_answer_graph`. For other operators (remember, ask, update, act), it does not. The export currently falls back to the decision packet's SAG, but that is also None for these operators. We synthesize a minimal SAG from the operator's intent and selected evidence.

**Tech Stack:** Python 3.13, SemanticAnswerGraph, training_export, OperatorResult.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `cemm/__main__.py` | Runtime entry point and training export | Modify |
| `cemm/tests/test_training_export_sag.py` | Tests | Create |

---

## Task 1: Synthesize SAG for non-answer operators during export

**Files:**
- Modify: `cemm/__main__.py`
- Create: `cemm/tests/test_training_export_sag.py`

- [ ] **Step 1: Write the failing test**

```python
# cemm/tests/test_training_export_sag.py
from __future__ import annotations
import os
import sys
import json
import tempfile

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
from cemm.__main__ import seed_registry, seed_self_state, process_input


def test_remember_export_includes_sag():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    os.environ["CEMM_EXPORT_PATH"] = path
    try:
        store = Store(":memory:")
        registry = Registry()
        op_registry = OperatorRegistry()
        pipeline = Pipeline(store, registry)
        online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
        inductor = Inductor(store, registry=registry)
        recursive_loop = RecursiveLoop(pipeline, store, online_learner, inductor)
        seed_registry(registry)
        seed_self_state(store)
        for op in [AnswerOperator(), AskOperator(), RememberOperator(), AbstainOperator()]:
            op_registry.register(op)

        process_input("remember I like coffee", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])

        with open(path, "r", encoding="utf-8") as f:
            line = f.readline()
        record = json.loads(line)
        assert "semantic_answer_graph" in record["payload"]
        assert record["payload"]["semantic_answer_graph"]["intent"] == "remember"
    finally:
        os.environ.pop("CEMM_EXPORT_PATH", None)
        os.unlink(path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest cemm/tests/test_training_export_sag.py -v`
Expected: FAIL — semantic_answer_graph missing or intent mismatch

- [ ] **Step 3: Modify `__main__.py` to synthesize SAG for export**

In `__main__.py`, around the training export block (after `op_result` is obtained), before calling `serialize_turn`, synthesize a SAG if none exists:

```python
    # Export training data if CEMM_EXPORT_PATH is set
    _export_path = os.environ.get("CEMM_EXPORT_PATH")
    if _export_path and op_result.trace:
        from .kernel.training_export import serialize_turn, write_turn_to_jsonl
        sag_for_export = op_result.semantic_answer_graph
        if sag_for_export is None and decision is not None:
            sag_for_export = decision.semantic_answer_graph
        if sag_for_export is None:
            # Synthesize a minimal SAG for operators that do not produce one,
            # so training records always have SAG supervision.
            intent_map = {
                ActionKind.REMEMBER: "remember",
                ActionKind.ASK: "ask",
                ActionKind.UPDATE_CLAIM: "update",
                ActionKind.CALL_TOOL: "act",
                ActionKind.REFLECT: "reflect",
                ActionKind.RETRIEVE: "retrieve",
                ActionKind.ABSTAIN: "abstain",
            }
            sag_intent = intent_map.get(kind, "answer")
            sag_for_export = SemanticAnswerGraph(
                id=uuid.uuid4().hex[:16],
                intent=sag_intent,
                source_signal_ids=[input_signal.id],
                context_id=kernel.id,
                selected_claim_ids=list(selected_claim_ids),
                selected_model_ids=list(selected_model_ids),
                confidence=decision.confidence if decision else 0.5,
                answer_latent=_latent_encoder.encode_answer(
                    intent=sag_intent,
                    selected_claim_ids=list(selected_claim_ids),
                    selected_model_ids=list(selected_model_ids),
                ),
            )
        turn_data = serialize_turn(...)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest cemm/tests/test_training_export_sag.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 6: Run manual integration test**

Run: `python manual_integration_test.py`
Expected: 25 cases, 0 gaps

- [ ] **Step 7: Commit**

```bash
git add cemm/__main__.py cemm/tests/test_training_export_sag.py
git commit -m "fix: synthesize SAG for non-answer operators in training export"
```

---

## Self-Review

### Spec Coverage

| Gap | Coverage |
|---|---|
| Training export SAG-less records | All exported turns now include a SAG, either from the operator or synthesized. |

### Placeholder Scan

No placeholders.

### Type Consistency

- `SemanticAnswerGraph` constructor is used with all required fields.
- `answer_latent` is computed via the existing latent encoder.
