# Auto-Promote Inducted Causal Models

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this task-by-task.

**Goal:** Close the "causal inference not full learned models" gap by auto-promoting high-confidence causal rules discovered by the `Inductor` to active status, so `CausalInference` can use them alongside the seeded models.

**Architecture:** `RecursiveLoop._run_induction` creates `PromotionCandidate` records for models found by `Inductor.maybe_induct`. Currently it never promotes them. We add a safe auto-approval path for high-confidence, low-risk `CAUSAL_RULE` candidates so they become active without manual intervention.

**Tech Stack:** Python 3.13, RecursiveLoop, Promoter, Inductor, ModelKind.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `cemm/kernel/recursive_loop.py` | Auto-approve high-confidence causal candidates | Modify |
| `cemm/tests/test_causal_inference.py` | Verify learned causal models become active | Modify |
| `cemm/docs/superpowers/specs/2026-06-30-cemm-gap-analysis.md` | Update gap status | Modify |

---

## Task 1: Auto-promote causal models

**Files:**
- Modify: `cemm/kernel/recursive_loop.py`
- Modify: `cemm/tests/test_causal_inference.py`

- [ ] **Step 1: Capture candidate and auto-approve in _run_induction**

Change `promoter.create_candidate(...)` to capture the returned `PromotionCandidate` and conditionally approve:

```python
candidate = promoter.create_candidate(
    model.id,
    reason=f"induction: {model.description}",
    score=model.confidence,
)
# Auto-promote high-confidence, low-risk causal rules so the system learns
# from repeated observations without manual gatekeeping.
if model.kind == ModelKind.CAUSAL_RULE and candidate.score >= 0.8:
    promoter.approve(candidate.id)
```

Add `ModelKind` import if needed.

- [ ] **Step 2: Add test**

Add a test that creates several claims with consistent outcomes, runs `_run_induction`, and verifies the learned causal model is active.

```python
def test_learned_causal_model_is_auto_promoted():
    store = Store(":memory:")
    from cemm.types.model import ModelKind, ModelStatus
    from cemm.types.claim import Claim, ClaimStatus
    from cemm.types.permission import Permission
    from cemm.learning.inductor import Inductor
    from cemm.kernel.recursive_loop import RecursiveLoop
    from cemm.kernel.pipeline import Pipeline
    from cemm.learning.online import OnlineLearner
    from cemm.registry import Registry
    from cemm.__main__ import seed_registry, seed_self_state

    registry = Registry()
    seed_registry(registry)
    seed_self_state(store)
    pipeline = Pipeline(store, registry)
    online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    inductor = Inductor(store, registry=registry)
    inductor.set_threshold(3)
    recursive_loop = RecursiveLoop(pipeline, store, online_learner, inductor)

    for i in range(3):
        claim = Claim(
            id=f"c{i}",
            subject_entity_id="user",
            predicate="ate_sugar",
            object_value="hyper",
            object_entity_id="hyper",
            source_id="test",
            qualifiers={"outcome": "success"},
            confidence=0.9,
            trust=0.9,
            status=ClaimStatus.ACTIVE,
            observed_at=time.time(),
            permission=Permission.public(),
        )
        store.claims.put(claim)

    recursive_loop._run_induction(store.context_kernels.get("ctx") or None)

    active = store.models.find_by_kind(ModelKind.CAUSAL_RULE.value, ModelStatus.ACTIVE.value)
    inducted = [m for m in active if "ate_sugar" in m.name or m.name == "ate_sugar"]
    assert inducted, f"No active inducted causal model found among {active!r}"
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
git add cemm/kernel/recursive_loop.py cemm/tests/test_causal_inference.py
git commit -m "feat: auto-promote high-confidence inducted causal models"
```

---

## Self-Review

### Spec Coverage

| Gap | Coverage |
|---|---|
| Causal inference only seeded models | High-confidence inducted causal rules are now promoted to active and available to CausalInference. |

### Placeholder Scan

No placeholders.
