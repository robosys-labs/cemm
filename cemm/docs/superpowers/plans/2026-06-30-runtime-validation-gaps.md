# Runtime Validation & Routing Gaps

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close three remaining runtime gaps: (1) narrow the overly broad self-reference patterns in `process_input`, (2) call the runtime packet validator after pipeline result construction, and (3) wire more `InvariantGuard` checks at runtime.

**Architecture:** Runtime validation is a first-class operator: packets should be validated before they leave the pipeline, invariants should be checked before and after operator execution, and routing should rely on semantic signals rather than raw text regex.

**Tech Stack:** Python 3.13, InvariantGuard, PacketValidator, re.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `cemm/__main__.py` | Runtime entry point | Modify |
| `cemm/kernel/pipeline.py` | Pipeline orchestration | Modify |
| `cemm/kernel/packet_validator.py` | Runtime packet validation | Read-only |
| `cemm/kernel/invariant_guard.py` | Invariant checks | Read-only |
| `cemm/tests/test_self_reference_patterns.py` | Self-ref pattern tests | Create |
| `cemm/tests/test_pipeline_packet_validation.py` | Packet validation tests | Create |
| `cemm/tests/test_invariant_guard_runtime.py` | Invariant runtime tests | Create |

---

## Task 1: Narrow overly broad self-reference patterns

**Files:**
- Modify: `cemm/__main__.py:197-205`
- Create: `cemm/tests/test_self_reference_patterns.py`

- [ ] **Step 1: Write the failing test**

```python
# cemm/tests/test_self_reference_patterns.py
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


def test_common_words_do_not_trigger_self_reference():
    """A question containing 'you' or 'yourself' as a normal word should not be treated as a self-reference query."""
    store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
    # Query that contains "you" but is not about the system
    output = process_input("do you like pizza", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    # We expect it to be routed to ask/abstain, not to answer about self
    # The exact output is less important than the self entity not being injected
    kernel = recursive_loop._last_result.kernel
    # self entity should not be the working entity
    assert "self" not in kernel.memory.working_entity_ids


def test_explicit_self_reference_still_works():
    """A genuine self-reference query should still inject the self entity."""
    store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
    output = process_input("what do you know about yourself", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    kernel = recursive_loop._last_result.kernel
    assert "self" in kernel.memory.working_entity_ids
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest cemm/tests/test_self_reference_patterns.py -v`
Expected: FAIL — `AssertionError` on `test_common_words_do_not_trigger_self_reference`

- [ ] **Step 3: Replace broad regex with word-boundary patterns**

In `cemm/__main__.py`, find the `_self_ref_patterns` definition:

```python
_SELF_REF_PATTERNS = [
    re.compile(r"\bwhat do you know\b", re.I),
    re.compile(r"\bwhat do you like\b", re.I),
    re.compile(r"\bwhat do you think\b", re.I),
    re.compile(r"\bwhat are you\b", re.I),
    re.compile(r"\bwho are you\b", re.I),
    re.compile(r"\bwhat do I like\b", re.I),
    re.compile(r"\bwhat do I want\b", re.I),
    re.compile(r"\bwhat do I need\b", re.I),
    re.compile(r"\bwhat do I prefer\b", re.I),
    re.compile(r"\byou\b", re.I),
    re.compile(r"\byourself\b", re.I),
]
```

Replace the last two lines with more specific patterns:

```python
_SELF_REF_PATTERNS = [
    re.compile(r"\bwhat do you know\b", re.I),
    re.compile(r"\bwhat do you like\b", re.I),
    re.compile(r"\bwhat do you think\b", re.I),
    re.compile(r"\bwhat are you\b", re.I),
    re.compile(r"\bwho are you\b", re.I),
    re.compile(r"\bwhat do I like\b", re.I),
    re.compile(r"\bwhat do I want\b", re.I),
    re.compile(r"\bwhat do I need\b", re.I),
    re.compile(r"\bwhat do I prefer\b", re.I),
    re.compile(r"\byourself\b", re.I),
    re.compile(r"\byourself\b", re.I),
]
```

Wait, that's wrong. Replace with:

```python
_SELF_REF_PATTERNS = [
    re.compile(r"\bwhat do you know\b", re.I),
    re.compile(r"\bwhat do you like\b", re.I),
    re.compile(r"\bwhat do you think\b", re.I),
    re.compile(r"\bwhat are you\b", re.I),
    re.compile(r"\bwho are you\b", re.I),
    re.compile(r"\bwhat do I like\b", re.I),
    re.compile(r"\bwhat do I want\b", re.I),
    re.compile(r"\bwhat do I need\b", re.I),
    re.compile(r"\bwhat do I prefer\b", re.I),
    re.compile(r"\bwhat are you made of\b", re.I),
    re.compile(r"\btell me about yourself\b", re.I),
]
```

Remove the standalone `\byou\b` and `\byourself\b` patterns.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest cemm/tests/test_self_reference_patterns.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 6: Run manual integration test**

Run: `python manual_integration_test.py`
Expected: 25 cases, 0 gaps

- [ ] **Step 7: Commit**

```bash
git add cemm/__main__.py cemm/tests/test_self_reference_patterns.py
git commit -m "fix: narrow self-reference patterns to avoid false positives"
```

---

## Task 2: Validate runtime packets after pipeline construction

**Files:**
- Modify: `cemm/kernel/pipeline.py` (after PipelineResult construction)
- Read: `cemm/kernel/packet_validator.py`
- Create: `cemm/tests/test_pipeline_packet_validation.py`

- [ ] **Step 1: Read the packet validator API**

Run: `python -c "from cemm.kernel.packet_validator import PacketValidator; help(PacketValidator)" 2>&1 | Select-Object -First 40`

Expected: see method names like `validate_*` or `validate_packet`.

- [ ] **Step 2: Write the failing test**

```python
# cemm/tests/test_pipeline_packet_validation.py
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.store.store import Store
from cemm.registry import Registry
from cemm.kernel.pipeline import Pipeline


def test_pipeline_result_packets_are_valid():
    store = Store(":memory:")
    registry = Registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("hello", context_id="ctx_test")
    assert result.kernel is not None
    assert result.semantic_event_graph is not None
    assert result.grounded_graph is not None
    assert result.memory_packet is not None
    assert result.context_inference is not None
    assert result.inference_packet is not None
    assert result.decision_packet is not None

    # Run packet validator if available
    from cemm.kernel.packet_validator import PacketValidator
    validator = PacketValidator()
    errors = validator.validate_semantic_event_graph(result.semantic_event_graph)
    assert errors == []
    errors = validator.validate_grounded_graph(result.grounded_graph)
    assert errors == []
    errors = validator.validate_memory_packet(result.memory_packet)
    assert errors == []
    errors = validator.validate_context_inference(result.context_inference)
    assert errors == []
    errors = validator.validate_inference_packet(result.inference_packet)
    assert errors == []
    errors = validator.validate_decision_packet(result.decision_packet)
    assert errors == []
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest cemm/tests/test_pipeline_packet_validation.py -v`
Expected: FAIL — either `PacketValidator` has no `validate_decision_packet` or similar, or validation errors exist

- [ ] **Step 4: Integrate packet validator into pipeline**

In `cemm/kernel/pipeline.py`, after `PipelineResult` is constructed and before `return result`, add:

```python
        # Validate runtime packets
        from ..kernel.packet_validator import PacketValidator
        validator = PacketValidator()
        validation_errors = []
        if result.semantic_event_graph:
            validation_errors.extend(validator.validate_semantic_event_graph(result.semantic_event_graph) or [])
        if result.grounded_graph:
            validation_errors.extend(validator.validate_grounded_graph(result.grounded_graph) or [])
        if result.memory_packet:
            validation_errors.extend(validator.validate_memory_packet(result.memory_packet) or [])
        if result.context_inference:
            validation_errors.extend(validator.validate_context_inference(result.context_inference) or [])
        if result.inference_packet:
            validation_errors.extend(validator.validate_inference_packet(result.inference_packet) or [])
        if result.decision_packet:
            validation_errors.extend(validator.validate_decision_packet(result.decision_packet) or [])
        if validation_errors:
            # Attach validation errors to the result for downstream inspection
            result.abstained = True
            if result.kernel is not None:
                result.kernel.self_view.recent_error_rate = min(
                    1.0, result.kernel.self_view.recent_error_rate + 0.1
                )
```

If `PacketValidator` does not have a method (e.g., `validate_decision_packet`), guard with `getattr(validator, f"validate_{name}", None)`.

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest cemm/tests/test_pipeline_packet_validation.py -v`
Expected: PASS

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 7: Run manual integration test**

Run: `python manual_integration_test.py`
Expected: 25 cases, 0 gaps

- [ ] **Step 8: Commit**

```bash
git add cemm/kernel/pipeline.py cemm/tests/test_pipeline_packet_validation.py
git commit -m "feat: validate runtime packets in PipelineResult"
```

---

## Task 3: Wire more InvariantGuard checks at runtime

**Files:**
- Read: `cemm/kernel/invariant_guard.py`
- Modify: `cemm/__main__.py` (after operator execution)
- Create: `cemm/tests/test_invariant_guard_runtime.py`

- [ ] **Step 1: Read the InvariantGuard API**

Run: `python -c "from cemm.kernel.invariant_guard import InvariantGuard; print([m for m in dir(InvariantGuard) if m.startswith('check_')])"`

Expected: list of all check methods.

- [ ] **Step 2: Write the failing test**

```python
# cemm/tests/test_invariant_guard_runtime.py
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


def test_invariant_guard_runs_after_operator_execution():
    """InvariantGuard checks should be invoked after operator execution."""
    from cemm.kernel.invariant_guard import InvariantGuard
    calls = []
    original_reset = InvariantGuard.reset
    original_check = InvariantGuard.check_action_has_trace

    def capture_reset(self):
        calls.append("reset")
        return original_reset(self)

    def capture_check(self, action):
        calls.append("check_action_has_trace")
        return original_check(self, action)

    InvariantGuard.reset = capture_reset
    InvariantGuard.check_action_has_trace = capture_check
    try:
        process_input("hello", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    finally:
        InvariantGuard.reset = original_reset
        InvariantGuard.check_action_has_trace = original_check

    assert "reset" in calls
    assert "check_action_has_trace" in calls
```

- [ ] **Step 3: Run test to verify it passes**

Run: `python -m pytest cemm/tests/test_invariant_guard_runtime.py -v`
Expected: PASS — `__main__.py` already calls InvariantGuard after operator execution

If it passes, the test is a regression guard. If it fails, add more InvariantGuard calls in `__main__.py` after operator execution.

- [ ] **Step 4: Add remaining invariant checks to `__main__.py`**

In `cemm/__main__.py`, find the invariant guard block after operator execution:

```python
    # Invariant checks after operator execution
    from .kernel.invariant_guard import InvariantGuard
    guard = InvariantGuard()
    guard.reset()
    for action in result.actions:
        guard.check_action_has_trace(action)
        guard.check_memory_mutation_has_trace(action)
    guard.check_recursive_budget(kernel, 0)
```

Add more applicable checks:

```python
    # Invariant checks after operator execution
    from .kernel.invariant_guard import InvariantGuard
    guard = InvariantGuard()
    guard.reset()
    for action in result.actions:
        guard.check_action_has_trace(action)
        guard.check_memory_mutation_has_trace(action)
    guard.check_recursive_budget(kernel, 0)
    if pipeline_result.semantic_event_graph:
        guard.check_claim_evidence_not_empty(pipeline_result.semantic_event_graph)
        guard.check_disputed_claim_not_certain(pipeline_result.semantic_event_graph)
    if decision:
        guard.check_answer_uses_verification(decision.action_plan, op_result)
        guard.check_abstain_no_evidence(decision, op_result)
    if op_result.semantic_answer_graph:
        guard.check_response_uses_selected_claims(op_result.semantic_answer_graph, op_result)
```

Use only methods that exist in `InvariantGuard`. Verify each method signature with `help(InvariantGuard)` before adding.

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest cemm/tests/test_invariant_guard_runtime.py -v`
Expected: PASS

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 7: Run manual integration test**

Run: `python manual_integration_test.py`
Expected: 25 cases, 0 gaps

- [ ] **Step 8: Commit**

```bash
git add cemm/__main__.py cemm/tests/test_invariant_guard_runtime.py
git commit -m "feat: wire more InvariantGuard checks at runtime"
```

---

## Self-Review

### Spec Coverage

| Gap | Task |
|---|---|
| G38 Overly broad self-reference patterns | Task 1 |
| G37 No runtime packet validation | Task 2 |
| G30 InvariantGuard checks not called at runtime | Task 3 |

### Placeholder Scan

No placeholders. All steps contain complete code, but some method names (e.g., `PacketValidator.validate_decision_packet`, `InvariantGuard.check_claim_evidence_not_empty`) must be verified against the actual class before implementation.

### Type Consistency

- `PacketValidator` is imported inside `pipeline.py` to avoid circular imports at module load.
- `InvariantGuard` methods are called with the arguments they expect; verify signatures with `help()` if unsure.
