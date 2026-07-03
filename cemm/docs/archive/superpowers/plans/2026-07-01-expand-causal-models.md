# Expand Seeded Causal Models

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this task-by-task.

**Goal:** Close the causal inference gap by seeding a small library of causal rule models so the system can reason about everyday processes beyond the single `rain -> flooding` rule.

**Architecture:** `CausalInference` queries `ModelStore` for `ModelKind.CAUSAL_RULE` records. We add a few more seed models in `seed_causal_models` and add tests verifying they produce predictions.

**Tech Stack:** Python 3.13, Model, CausalInference, seed_causal_models.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `cemm/__main__.py` | Seed additional causal models | Modify |
| `cemm/tests/test_causal_inference.py` | Add tests for new models | Modify |
| `cemm/docs/superpowers/specs/2026-06-30-cemm-gap-analysis.md` | Mark gap updated | Modify |

---

## Task 1: Add additional causal rule models

**Files:**
- Modify: `cemm/__main__.py`
- Modify: `cemm/tests/test_causal_inference.py`

- [ ] **Step 1: Add seed models**

Extend `seed_causal_models` to add three more causal rules:

1. `causal_heat_melt`: heat -> melting
2. `causal_study_pass`: studying -> passing exam
3. `causal_exercise_energy`: exercise -> more energy

Use the same pattern as `causal_rain_flooding` but with distinct IDs, preconditions, and effects.

- [ ] **Step 2: Add test**

Add a test in `test_causal_inference.py` that verifies multiple seed models are active and that a relevant input produces predictions from the correct model.

```python
def test_multiple_seed_causal_models_exist():
    store = Store(":memory:")
    from cemm.types.model import ModelKind, ModelStatus
    seed_causal_models(store)
    models = store.models.find_by_kind(ModelKind.CAUSAL_RULE.value, ModelStatus.ACTIVE.value)
    assert len(models) >= 3
    ids = {m.id for m in models}
    assert "causal_rain_flooding" in ids
    assert "causal_heat_melt" in ids
    assert "causal_study_pass" in ids


def test_study_causal_model_produces_predictions():
    store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
    output = process_input("studying causes passing the exam", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    assert output is not None
    result = recursive_loop._last_result
    assert any("pass" in p.get("predicate", "").lower() for p in result.inference_packet.predictions)
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
git commit -m "feat: expand seeded causal model library"
```

---

## Self-Review

### Spec Coverage

| Gap | Coverage |
|---|---|
| Causal inference only one seed model | Multiple seed models cover everyday causal patterns. |
| Simulation never runs | Same seed models enable simulation for multiple inputs. |

### Placeholder Scan

No placeholders.
