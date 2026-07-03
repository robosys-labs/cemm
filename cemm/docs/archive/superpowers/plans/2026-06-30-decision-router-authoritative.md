# Make DecisionRouter Fully Authoritative

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this task.

**Goal:** Remove the remaining hardcoded fallbacks in `process_input()` and `DecisionRouter` so the DecisionRouter is the single authoritative routing mechanism. This closes the gap where the routing cascade can bypass the SAG via Phase 2/3 fallbacks.

**Architecture:** `process_input()` currently hardcodes `if text.lower() in ("exit", "quit", "bye"): return "Goodbye!"`. `DecisionRouter.run()` also has a "short input" fallback that routes to ask for any input <= 3 characters. These bypass the normal pipeline and SAG construction. We remove the hardcoded exit path from `__main__.py` and make the short-input fallback a last-resort, only when the pipeline produced no meaningful graph.

**Tech Stack:** Python 3.13, DecisionRouter, __main__.py.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `cemm/__main__.py` | Runtime entry point | Modify |
| `cemm/kernel/decision_router.py` | Routing decision | Modify |
| `cemm/tests/test_routing.py` | Routing tests | Modify |

---

## Task 1: Remove hardcoded fallbacks

**Files:**
- Modify: `cemm/__main__.py`
- Modify: `cemm/kernel/decision_router.py`
- Modify: `cemm/tests/test_routing.py`

- [ ] **Step 1: Remove hardcoded exit/quit/bye path from `__main__.py`**

Find the block:

```python
    if text.lower() in ("exit", "quit", "bye"):
        return "Goodbye!"
```

Remove it. The `session_exit` frame in the DecisionRouter already handles this.

- [ ] **Step 2: Make short-input fallback conditional in `DecisionRouter`**

Change the short-input block from:

```python
        # Short input or question mark: route to ask/answer
        if input_text and len(input_text.strip()) <= 3:
            return DecisionPacket(
                action_kind="ask",
                ...
            )
```

To:

```python
        # Short input or question mark: only route to ask if no meaningful graph
        if input_text and len(input_text.strip()) <= 3 and graph.confidence < 0.3:
            return DecisionPacket(
                action_kind="ask",
                ...
            )
```

- [ ] **Step 3: Add tests**

Add to `test_routing.py`:

```python

def test_exit_input_routes_through_decision_router():
    store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup_routing_test()
    output = process_input("bye", store, registry, op_registry, pipeline, online_learner, recursive_loop, "test_session", [0])
    assert output is not None
    # Should not be the hardcoded "Goodbye!"
    assert output != "Goodbye!"
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest cemm/tests/test_routing.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 6: Run manual integration test**

Run: `python manual_integration_test.py`
Expected: 25 cases, 0 gaps

- [ ] **Step 7: Commit**

```bash
git add cemm/__main__.py cemm/kernel/decision_router.py cemm/tests/test_routing.py
git commit -m "fix: make DecisionRouter authoritative by removing hardcoded fallbacks"
```

---

## Self-Review

### Spec Coverage

| Gap | Coverage |
|---|---|
| Routing cascade bypasses SAG via Phase 2/3 fallbacks | Hardcoded exit and unconditional short-input fallbacks removed. |

### Placeholder Scan

No placeholders.
