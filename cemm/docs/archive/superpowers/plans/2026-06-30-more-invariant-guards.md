# Additional InvariantGuard Checks at Runtime

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this task.

**Goal:** Continue closing G30 by wiring additional `InvariantGuard` checks that are relevant to the current runtime path: evidence for selected claims and models, simulation claims capped at 0.99, and self-insult/frustration persistence.

**Architecture:** `process_input()` in `__main__.py` already calls several `InvariantGuard` methods after operator execution. We extend this block to include checks for selected claims and models, and for any simulation claims in the operator result.

**Tech Stack:** Python 3.13, InvariantGuard, process_input, Claim, Model.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `cemm/__main__.py` | Runtime entry point | Modify |
| `cemm/tests/test_invariant_guard_runtime.py` | Runtime guard tests | Modify |

---

## Task 1: Add more InvariantGuard checks in process_input

**Files:**
- Modify: `cemm/__main__.py`
- Modify: `cemm/tests/test_invariant_guard_runtime.py`

- [ ] **Step 1: Read existing invariant guard block in `__main__.py`**

Locate the block after `op_result = op_registry.execute(kind, ctx)` and review the current guard calls.

- [ ] **Step 2: Extend the block**

Add:

```python
    # Check selected claims and models have evidence
    for cid in selected_claim_ids:
        claim = store.claims.get(cid)
        if claim:
            guard.check_claim_has_evidence(claim)
            guard.check_model_promoted_with_validation_for_claim(claim)
    for mid in selected_model_ids:
        model = store.models.get(mid)
        if model:
            guard.check_model_has_evidence(model)
            guard.check_model_promoted_with_validation(model)

    # Check simulation claims are not presented as fact
    if op_result.new_claim_ids:
        for cid in op_result.new_claim_ids:
            claim = store.claims.get(cid)
            if claim:
                guard.check_prediction_not_presented_as_fact(claim)

    # Check self-insults and temporary frustration are not persisted
    if kernel.self_view.self_id:
        for cid in (op_result.new_claim_ids or []):
            claim = store.claims.get(cid)
            if claim:
                guard.check_insults_are_not_factual_claims(claim, kernel.self_view.self_id)
                guard.check_temporary_frustration_not_persisted(claim)
```

Wait, `check_model_promoted_with_validation_for_claim` does not exist. Remove that. Keep `check_model_promoted_with_validation` for selected models.

- [ ] **Step 3: Add tests**

In `cemm/tests/test_invariant_guard_runtime.py`, add tests that:

- Mock a claim without evidence and verify `check_claim_has_evidence` is called.
- Mock a model without evidence and verify `check_model_has_evidence` is called.

Or simpler: monkeypatch the guard methods and assert they are called after process_input.

- [ ] **Step 4: Run tests**

Run: `python -m pytest cemm/tests/test_invariant_guard_runtime.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 6: Run manual integration test**

Run: `python manual_integration_test.py`
Expected: 25 cases, 0 gaps

- [ ] **Step 7: Commit**

```bash
git add cemm/__main__.py cemm/tests/test_invariant_guard_runtime.py
git commit -m "feat: wire additional InvariantGuard checks at runtime"
```

---

## Self-Review

### Spec Coverage

| Gap | Coverage |
|---|---|
| G30 InvariantGuard checks not called | Additional checks wired for evidence, simulation claims, and self-insults. |

### Placeholder Scan

No placeholders.
