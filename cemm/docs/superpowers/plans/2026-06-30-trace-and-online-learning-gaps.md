# Trace and Online Learning Gaps

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close three medium-impact gaps: (1) operators must record the source `semantic_event_graph_id` in their `Trace`, (2) `OnlineLearner` must learn from failures as well as successes, and (3) `RecursiveLoop._run_online_learning` must update source trust, operator reliability, and ranking weights, not just self state.

**Architecture:** The `Trace` object links an action to its input signal and the semantic graph that produced it. Currently `Trace.semantic_event_graph_id` is always empty. The `OnlineLearner` maintains source trust, operator reliability, and ranking weights based on outcomes; it only receives positive outcomes today, so it cannot downgrade poor sources or operators. The `RecursiveLoop` is the only runtime caller of online learning; it must use all safe update methods.

**Tech Stack:** Python 3.13, dataclasses, typed ContextKernel, Trace, OnlineLearner.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `cemm/types/trace.py` | Trace dataclass | Read-only |
| `cemm/operators/answer.py` | AnswerOperator | Modify |
| `cemm/operators/abstain.py` | AbstainOperator | Modify |
| `cemm/operators/ask.py` | AskOperator | Modify |
| `cemm/operators/remember.py` | RememberOperator | Modify |
| `cemm/operators/reflect.py` | ReflectOperator | Modify |
| `cemm/operators/update_claim.py` | UpdateClaimOperator | Modify |
| `cemm/operators/create_model.py` | CreateModelOperator | Modify |
| `cemm/operators/retrieve_op.py` | RetrieveOperator | Modify |
| `cemm/operators/simulate.py` | SimulateOperator | Modify |
| `cemm/operators/synthesize.py` | SynthesizeOperator | Modify |
| `cemm/operators/call_tool.py` | CallToolOperator | Modify |
| `cemm/__main__.py` | Runtime that calls operators | Modify |
| `cemm/learning/online.py` | OnlineLearner | Read-only / maybe Modify |
| `cemm/kernel/recursive_loop.py` | RecursiveLoop | Modify |
| `cemm/tests/test_trace_semantic_event_graph_id.py` | Trace SEG ID tests | Create |
| `cemm/tests/test_online_learning_outcomes.py` | Online learning outcome tests | Create |
| `cemm/tests/test_recursive_loop_online_learning.py` | RecursiveLoop online learning tests | Create |

---

## Task 1: Set `Trace.semantic_event_graph_id` in every operator

**Files:**
- Modify: `cemm/operators/answer.py`
- Modify: `cemm/operators/abstain.py`
- Modify: `cemm/operators/ask.py`
- Modify: `cemm/operators/remember.py`
- Modify: `cemm/operators/reflect.py`
- Modify: `cemm/operators/update_claim.py`
- Modify: `cemm/operators/create_model.py`
- Modify: `cemm/operators/retrieve_op.py`
- Modify: `cemm/operators/simulate.py`
- Modify: `cemm/operators/synthesize.py`
- Modify: `cemm/operators/call_tool.py`
- Modify: `cemm/__main__.py` (pass SEG ID to operator context)
- Create: `cemm/tests/test_trace_semantic_event_graph_id.py`

- [ ] **Step 1: Write the failing test**

```python
# cemm/tests/test_trace_semantic_event_graph_id.py
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.store.store import Store
from cemm.registry import Registry
from cemm.kernel.pipeline import Pipeline
from cemm.__main__ import process_input
from cemm.operators.registry import OperatorRegistry
from cemm.operators.answer import AnswerOperator
from cemm.operators.abstain import AbstainOperator
from cemm.operators.ask import AskOperator
from cemm.operators.remember import RememberOperator
from cemm.learning.online import OnlineLearner
from cemm.learning.inductor import Inductor
from cemm.kernel.recursive_loop import RecursiveLoop


def _setup():
    store = Store(":memory:")
    registry = Registry()
    op_registry = OperatorRegistry()
    pipeline = Pipeline(store, registry)
    online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    inductor = Inductor(store, registry=registry)
    recursive_loop = RecursiveLoop(pipeline, store, online_learner, inductor)
    from cemm.__main__ import seed_registry, seed_self_state
    seed_registry(registry)
    seed_self_state(store)
    for op in [
        AnswerOperator(), AbstainOperator(), AskOperator(), RememberOperator(),
    ]:
        op_registry.register(op)
    return store, registry, op_registry, pipeline, online_learner, recursive_loop


def test_trace_records_semantic_event_graph_id_for_answer():
    store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
    process_input("hello", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    # The latest action trace should have the SEG ID
    actions = store.actions.recent(10)
    assert actions
    for action in actions:
        if action.trace and action.trace.semantic_event_graph_id:
            assert action.trace.semantic_event_graph_id
            return
    raise AssertionError("No action trace with semantic_event_graph_id found")


def test_trace_records_semantic_event_graph_id_for_remember():
    store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
    process_input("remember I like coffee", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    actions = store.actions.recent(10)
    assert actions
    for action in actions:
        if action.trace and action.trace.semantic_event_graph_id:
            assert action.trace.semantic_event_graph_id
            return
    raise AssertionError("No action trace with semantic_event_graph_id found")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest cemm/tests/test_trace_semantic_event_graph_id.py -v`
Expected: FAIL — `AssertionError: No action trace with semantic_event_graph_id found`

- [ ] **Step 3: Pass `semantic_event_graph_id` into operator context**

In `cemm/__main__.py`, find where `OperatorContext` is constructed (around line 413). Add `semantic_event_graph_id` to the context. The current construction looks like:

```python
    ctx = OperatorContext(
        kernel=kernel,
        input_signal=input_signal,
        store=store,
        params=params,
        trace=Trace(
            id=uuid.uuid4().hex[:16],
            input_signal_id=input_signal.id,
            semantic_event_graph_id=pipeline_result.semantic_event_graph.id if pipeline_result.semantic_event_graph else None,
            grounded_graph_id=grounded_graph.id if grounded_graph else None,
            memory_packet_id=memory_packet.id if memory_packet else None,
            inference_packet_id=inference_packet.id if inference_packet else None,
            decision_packet_id=decision.id if decision else None,
        ),
        inference_packet=inference_packet,
        decision_packet=decision if decision and decision.confidence > 0 else None,
    )
```

Confirm `semantic_event_graph_id` is already present. If it is already present but operators don't copy it into their own traces, proceed to Step 4.

- [ ] **Step 4: Update each operator to copy SEG ID into its result trace**

For each operator in `cemm/operators/*.py`, find where the result `Trace` is constructed. It typically looks like:

```python
            trace=Trace(
                id=ctx.trace.id,
                input_signal_id=ctx.trace.input_signal_id,
                semantic_answer_graph_id=sag.id,
            )
```

Add `semantic_event_graph_id=ctx.trace.semantic_event_graph_id` to every operator trace.

Operators to update:
- `cemm/operators/answer.py`
- `cemm/operators/abstain.py`
- `cemm/operators/ask.py`
- `cemm/operators/remember.py`
- `cemm/operators/reflect.py`
- `cemm/operators/update_claim.py`
- `cemm/operators/create_model.py`
- `cemm/operators/retrieve_op.py`
- `cemm/operators/simulate.py`
- `cemm/operators/synthesize.py`
- `cemm/operators/call_tool.py`

Example change in `answer.py`:

```python
            trace=Trace(
                id=ctx.trace.id,
                input_signal_id=ctx.trace.input_signal_id,
                semantic_event_graph_id=ctx.trace.semantic_event_graph_id,
                semantic_answer_graph_id=sag.id,
            )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest cemm/tests/test_trace_semantic_event_graph_id.py -v`
Expected: PASS

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 7: Commit**

```bash
git add cemm/operators/*.py cemm/tests/test_trace_semantic_event_graph_id.py
git commit -m "fix: record semantic_event_graph_id in all operator traces"
```

---

## Task 2: Record online learning outcomes on failure

**Files:**
- Modify: `cemm/__main__.py:409-420` (remove success-only guard)
- Create: `cemm/tests/test_online_learning_outcomes.py`

- [ ] **Step 1: Write the failing test**

```python
# cemm/tests/test_online_learning_outcomes.py
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.store.store import Store
from cemm.registry import Registry
from cemm.kernel.pipeline import Pipeline
from cemm.__main__ import process_input
from cemm.operators.registry import OperatorRegistry
from cemm.operators.answer import AnswerOperator
from cemm.operators.abstain import AbstainOperator
from cemm.operators.ask import AskOperator
from cemm.operators.remember import RememberOperator
from cemm.learning.online import OnlineLearner
from cemm.learning.inductor import Inductor
from cemm.kernel.recursive_loop import RecursiveLoop


def _setup():
    store = Store(":memory:")
    registry = Registry()
    op_registry = OperatorRegistry()
    pipeline = Pipeline(store, registry)
    online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    inductor = Inductor(store, registry=registry)
    recursive_loop = RecursiveLoop(pipeline, store, online_learner, inductor)
    from cemm.__main__ import seed_registry, seed_self_state
    seed_registry(registry)
    seed_self_state(store)
    for op in [AnswerOperator(), AbstainOperator(), AskOperator(), RememberOperator()]:
        op_registry.register(op)
    return store, registry, op_registry, pipeline, online_learner, recursive_loop


def test_online_learner_records_failure():
    store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
    # Patch the learner to capture calls
    recorded = []
    original_record = online_learner.record_outcome
    def capture_record(action, success, confidence):
        recorded.append((action.kind.value if hasattr(action.kind, "value") else str(action.kind), success, confidence))
        return original_record(action, success, confidence)
    online_learner.record_outcome = capture_record

    # Empty input should produce an abstain (non-success) outcome
    process_input("", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    assert recorded
    assert any(success is False for _, success, _ in recorded), "Expected at least one failure outcome"


def test_online_learner_records_success():
    store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
    recorded = []
    original_record = online_learner.record_outcome
    def capture_record(action, success, confidence):
        recorded.append((action.kind.value if hasattr(action.kind, "value") else str(action.kind), success, confidence))
        return original_record(action, success, confidence)
    online_learner.record_outcome = capture_record

    process_input("hello", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    assert recorded
    assert any(success is True for _, success, _ in recorded), "Expected at least one success outcome"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest cemm/tests/test_online_learning_outcomes.py -v`
Expected: FAIL — `Expected at least one failure outcome` (because failures are currently skipped)

- [ ] **Step 3: Remove success-only guard in `__main__.py`**

Find the current code:

```python
    if op_result.success:
        online_learner.record_outcome(
            action,
            success=True,
            confidence=decision.confidence if decision else 0.5,
        )
```

Replace with:

```python
    online_learner.record_outcome(
        action,
        success=op_result.success,
        confidence=decision.confidence if decision else 0.5,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest cemm/tests/test_online_learning_outcomes.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add cemm/__main__.py cemm/tests/test_online_learning_outcomes.py
git commit -m "fix: record online learning outcomes for both success and failure"
```

---

## Task 3: Expand RecursiveLoop online learning to update source trust, operator reliability, and ranking weights

**Files:**
- Modify: `cemm/kernel/recursive_loop.py:201-204` (`_run_online_learning`)
- Read: `cemm/learning/online.py` to confirm available methods
- Create: `cemm/tests/test_recursive_loop_online_learning.py`

- [ ] **Step 1: Read OnlineLearner public methods**

Run: `python -c "from cemm.learning.online import OnlineLearner; print([m for m in dir(OnlineLearner) if not m.startswith('_')])"`
Expected: list includes `record_outcome`, `update_self_state`, `update_source_trust`, `update_operator_reliability`, `update_ranking_weights`, or similar.

If the methods don't exist, this task is blocked and must be reported to the user.

- [ ] **Step 2: Write the failing test**

```python
# cemm/tests/test_recursive_loop_online_learning.py
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


def test_recursive_loop_runs_all_online_learning_updates():
    store = Store(":memory:")
    registry = Registry()
    pipeline = Pipeline(store, registry)
    online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    inductor = Inductor(store, registry=registry)
    loop = RecursiveLoop(pipeline, store, online_learner, inductor)

    from cemm.__main__ import seed_registry, seed_self_state
    seed_registry(registry)
    seed_self_state(store)

    calls = []
    for method_name in ("update_self_state", "update_source_trust", "update_operator_reliability", "update_ranking_weights"):
        if not hasattr(online_learner, method_name):
            continue
        original = getattr(online_learner, method_name)
        def make_capture(orig, name):
            def capture(*args, **kwargs):
                calls.append(name)
                return orig(*args, **kwargs)
            return capture
        setattr(online_learner, method_name, make_capture(original, method_name))

    loop.run_once("hello", context_id="ctx")
    assert "update_self_state" in calls
    # Expect the others to be called if they exist
    assert "update_source_trust" in calls
    assert "update_operator_reliability" in calls
    assert "update_ranking_weights" in calls
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest cemm/tests/test_recursive_loop_online_learning.py -v`
Expected: FAIL — `assert "update_source_trust" in calls`

- [ ] **Step 4: Update `_run_online_learning` in `recursive_loop.py`**

Find the current implementation:

```python
    def _run_online_learning(self, kernel: ContextKernel, result: PipelineResult) -> None:
        self._learner.update_self_state(kernel)
```

Replace with:

```python
    def _run_online_learning(self, kernel: ContextKernel, result: PipelineResult) -> None:
        self._learner.update_self_state(kernel)
        if hasattr(self._learner, "update_source_trust"):
            self._learner.update_source_trust(kernel)
        if hasattr(self._learner, "update_operator_reliability"):
            self._learner.update_operator_reliability(kernel)
        if hasattr(self._learner, "update_ranking_weights"):
            self._learner.update_ranking_weights(kernel)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest cemm/tests/test_recursive_loop_online_learning.py -v`
Expected: PASS

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 7: Run manual integration test**

Run: `python manual_integration_test.py`
Expected: 25 cases, 0 gaps

- [ ] **Step 8: Commit**

```bash
git add cemm/kernel/recursive_loop.py cemm/tests/test_recursive_loop_online_learning.py
git commit -m "fix: expand RecursiveLoop online learning to trust, reliability, and ranking weights"
```

---

## Self-Review

### Spec Coverage

| Gap | Task |
|---|---|
| G29 Trace never sets `semantic_event_graph_id` | Task 1 |
| G33 `OnlineLearner.record_outcome` only called on success | Task 2 |
| G34 `RecursiveLoop._run_online_learning` only updates self state | Task 3 |

### Placeholder Scan

No placeholders. All steps contain complete code.

### Type Consistency

- `Trace.semantic_event_graph_id` is already a field in `cemm/types/trace.py`; we just copy it from operator context.
- `OnlineLearner` methods are discovered via `hasattr` to avoid breaking if the class doesn't have all four methods.
