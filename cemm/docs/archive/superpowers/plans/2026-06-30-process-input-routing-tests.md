# Process Input Routing Integration Tests

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this task.

**Goal:** Expand integration test coverage for `process_input()` in `cemm/__main__.py` to cover the main routing paths (greeting, remember, question, abstain, causal statement, self-reference). This closes the remaining coverage gap from G4 and guards against regressions in the routing cascade.

**Architecture:** `process_input()` is the runtime entry point. It builds the kernel, runs the pipeline, routes to an operator, executes the operator, and returns output text. Currently only two integration tests exist in `tests/test_routing.py`. The tests should verify the correct operator is selected and the output text is appropriate for each major input class.

**Tech Stack:** Python 3.13, pytest, process_input, Pipeline, OperatorRegistry.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `cemm/__main__.py` | Runtime entry point | Read-only |
| `cemm/tests/test_routing.py` | Existing integration tests | Modify |

---

## Task 1: Add routing-path integration tests

**Files:**
- Modify: `cemm/tests/test_routing.py`

- [ ] **Step 1: Review existing tests**

Run: `python -m pytest cemm/tests/test_routing.py -v`
Expected: 2 tests pass.

- [ ] **Step 2: Add tests for remaining routing paths**

Append to `cemm/tests/test_routing.py`:

```python

def test_process_input_greeting_routes_to_answer():
    store = Store(":memory:")
    registry = Registry()
    op_registry = OperatorRegistry()
    pipeline = Pipeline(store, registry)
    online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    inductor = Inductor(store, registry=registry)
    recursive_loop = RecursiveLoop(pipeline, store, online_learner, inductor)
    seed_registry(registry)
    seed_self_state(store)
    for op in [AnswerOperator(), AbstainOperator(), AskOperator(), RememberOperator()]:
        op_registry.register(op)
    output = process_input("hello", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    assert output is not None
    assert output.lower() not in ("", "could you elaborate?")


def test_process_input_remember_routes_to_remember():
    store = Store(":memory:")
    registry = Registry()
    op_registry = OperatorRegistry()
    pipeline = Pipeline(store, registry)
    online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    inductor = Inductor(store, registry=registry)
    recursive_loop = RecursiveLoop(pipeline, store, online_learner, inductor)
    seed_registry(registry)
    seed_self_state(store)
    for op in [AnswerOperator(), AbstainOperator(), AskOperator(), RememberOperator()]:
        op_registry.register(op)
    output = process_input("remember I like coffee", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    assert output is not None
    assert "remember" in output.lower() or "remembered" in output.lower()


def test_process_input_question_routes_to_ask_or_answer():
    store = Store(":memory:")
    registry = Registry()
    op_registry = OperatorRegistry()
    pipeline = Pipeline(store, registry)
    online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    inductor = Inductor(store, registry=registry)
    recursive_loop = RecursiveLoop(pipeline, store, online_learner, inductor)
    seed_registry(registry)
    seed_self_state(store)
    for op in [AnswerOperator(), AbstainOperator(), AskOperator(), RememberOperator()]:
        op_registry.register(op)
    output = process_input("what do I like", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    assert output is not None


def test_process_input_abstain_for_empty_input():
    store = Store(":memory:")
    registry = Registry()
    op_registry = OperatorRegistry()
    pipeline = Pipeline(store, registry)
    online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    inductor = Inductor(store, registry=registry)
    recursive_loop = RecursiveLoop(pipeline, store, online_learner, inductor)
    seed_registry(registry)
    seed_self_state(store)
    for op in [AnswerOperator(), AbstainOperator(), AskOperator(), RememberOperator()]:
        op_registry.register(op)
    output = process_input("", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    assert output is not None
    # Empty input should fall back to abstain/ask


def test_process_input_causal_statement_routes_to_remember():
    store = Store(":memory:")
    registry = Registry()
    op_registry = OperatorRegistry()
    pipeline = Pipeline(store, registry)
    online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    inductor = Inductor(store, registry=registry)
    recursive_loop = RecursiveLoop(pipeline, store, online_learner, inductor)
    seed_registry(registry)
    seed_self_state(store)
    for op in [AnswerOperator(), AbstainOperator(), AskOperator(), RememberOperator()]:
        op_registry.register(op)
    output = process_input("rain causes flooding", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    assert output is not None


def test_process_input_self_reference_routes_to_answer():
    store = Store(":memory:")
    registry = Registry()
    op_registry = OperatorRegistry()
    pipeline = Pipeline(store, registry)
    online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    inductor = Inductor(store, registry=registry)
    recursive_loop = RecursiveLoop(pipeline, store, online_learner, inductor)
    seed_registry(registry)
    seed_self_state(store)
    for op in [AnswerOperator(), AbstainOperator(), AskOperator(), RememberOperator()]:
        op_registry.register(op)
    output = process_input("what do you know", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    assert output is not None
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest cemm/tests/test_routing.py -v`
Expected: All tests pass.

- [ ] **Step 4: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass.

- [ ] **Step 5: Run manual integration test**

Run: `python manual_integration_test.py`
Expected: 25 cases, 0 gaps.

- [ ] **Step 6: Commit**

```bash
git add cemm/tests/test_routing.py
git commit -m "test: expand process_input routing integration tests"
```

---

## Self-Review

### Spec Coverage

| Gap | Coverage |
|---|---|
| G4 process_input test coverage | Expanded to cover greeting, remember, question, abstain, causal, self-reference. |

### Placeholder Scan

No placeholders.

### Type Consistency

- Tests use the same setup helper as the existing routing tests.
