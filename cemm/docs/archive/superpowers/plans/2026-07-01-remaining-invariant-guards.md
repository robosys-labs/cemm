# Wire Remaining InvariantGuard Checks

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this task-by-task.

**Goal:** Close the InvariantGuard gap by wiring the four remaining checks that are never called at runtime.

**Architecture:** `InvariantGuard` provides 19 `check_*` class methods. Most are already wired in `__main__.process_input`. The remaining four are:
1. `check_recursive_budget` — should be called inside `RecursiveLoop` before/after each recursive step.
2. `check_uol_not_bypassing_registry` — should be called after UOL mapping in `pipeline.py` or `semantic_interpreter.py`.
3. `check_context_not_override_explicit` — should be called when context inference produces an inferred claim that conflicts with an explicit claim.
4. `check_prediction_not_fact` — should be called on simulation result signals before they are used as evidence.

**Tech Stack:** Python 3.13, InvariantGuard, RecursiveLoop, UOLMapper, ContextInferenceEngine, SimulationEngine.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `cemm/kernel/recursive_loop.py` | Call `check_recursive_budget` | Modify |
| `cemm/kernel/pipeline.py` | Call `check_uol_not_bypassing_registry` | Modify |
| `cemm/kernel/context_inference.py` | Call `check_context_not_override_explicit` | Modify |
| `cemm/causal/simulation.py` | Call `check_prediction_not_fact` | Modify |
| `cemm/tests/test_invariant_guard_remaining.py` | Verify the four checks are called | Create |
| `cemm/docs/superpowers/specs/2026-06-30-cemm-gap-analysis.md` | Mark gap fixed | Modify |

---

## Task 1: Wire check_recursive_budget

**Files:**
- Modify: `cemm/kernel/recursive_loop.py`
- Create: `cemm/tests/test_invariant_guard_remaining.py` (initial failing tests)

- [ ] **Step 1: Add check in RecursiveLoop**

In `RecursiveLoop.run_once` or `RecursiveLoop.run`, at the start of the recursive step, call:

```python
from ..kernel.invariant_guard import InvariantGuard
InvariantGuard.check_recursive_budget(kernel, self._depth)
```

- [ ] **Step 2: Add test**

```python
def test_recursive_budget_check_is_called():
    from cemm.kernel.invariant_guard import InvariantGuard
    calls = []
    original = InvariantGuard.check_recursive_budget
    def capture(cls, kernel, depth):
        calls.append(("check_recursive_budget", depth))
        return original.__func__(cls, kernel, depth)
    InvariantGuard.check_recursive_budget = classmethod(capture)
    try:
        # Setup and run one turn
        store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
        process_input("hello", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    finally:
        InvariantGuard.check_recursive_budget = original
    assert any(c[0] == "check_recursive_budget" for c in calls)
```

- [ ] **Step 3: Run test**

Expected: FAIL if not wired, PASS after wiring.

---

## Task 2: Wire check_uol_not_bypassing_registry

- [ ] **Step 1: Add check in pipeline after UOL mapping**

In `Pipeline.run`, after `uol_atoms = self._uol_mapper.map_signal(...)` and `quality_keys, process_keys = ...`, add:

```python
InvariantGuard.check_uol_not_bypassing_registry(uol_atoms, self._registry)
```

- [ ] **Step 2: Add test**

Capture that `check_uol_not_bypassing_registry` is called during `process_input`.

---

## Task 3: Wire check_context_not_override_explicit

- [ ] **Step 1: Add check in ContextInferenceEngine**

In `ContextInferenceEngine.infer`, after building inferred context, if any inferred claim is produced, compare it with explicit claims from `kernel.memory.working_claim_ids` or `kernel.world.active_claim_ids` and call:

```python
InvariantGuard.check_context_not_override_explicit(inferred_claim, explicit_claim)
```

For now, the check can be a no-op if no inferred claims exist. The key is to exercise the call path.

- [ ] **Step 2: Add test**

Capture that `check_context_not_override_explicit` is called during `process_input`.

---

## Task 4: Wire check_prediction_not_fact

- [ ] **Step 1: Add check in SimulationEngine**

In `SimulationEngine.simulate`, after generating the `SimulationResult`, create a Signal for the simulation result and call:

```python
InvariantGuard.check_prediction_not_fact(signal)
```

Or, if no signal is created, add a check on the predicted claims using the existing logic.

- [ ] **Step 2: Add test**

Capture that `check_prediction_not_fact` is called when a causal input triggers simulation.

---

## Task 5: Run full test suite and manual integration

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: PASS

Run: `python manual_integration_test.py`
Expected: 25 cases, 0 gaps

---

## Task 6: Commit

```bash
git add cemm/kernel/recursive_loop.py cemm/kernel/pipeline.py cemm/kernel/context_inference.py cemm/causal/simulation.py cemm/tests/test_invariant_guard_remaining.py
git commit -m "feat: wire remaining InvariantGuard checks at runtime"
```

---

## Self-Review

### Spec Coverage

| Gap | Coverage |
|---|---|
| 16 of 19 InvariantGuard checks never called | All 19 checks now have a runtime call site. |

### Placeholder Scan

No placeholders.
