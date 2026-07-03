# Improve SemanticInterpreter Model Ref Lookup

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this task-by-task.

**Goal:** Make `SemanticInterpreter._lookup_model_refs` select the correct causal model when multiple causal models share the same registry key. This improves model-edge population in the `SemanticEventGraph` and makes the expanded causal model library useful at runtime.

**Architecture:** `_lookup_model_refs` currently only looks up models by `registry_key` (e.g., `causal_causes`) and name. Because all seeded causal models share the `causal_causes` registry key, the same model is always returned. The improvement adds a second pass that matches model preconditions/effects against the entity phrases extracted from the input text.

**Tech Stack:** Python 3.13, SemanticInterpreter, ModelStore, ModelKind, SemanticEventGraph.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `cemm/kernel/semantic_interpreter.py` | Improve model ref matching | Modify |
| `cemm/tests/test_causal_inference.py` | Verify model refs match correct model | Modify |
| `cemm/docs/superpowers/specs/2026-06-30-cemm-gap-analysis.md` | Update gap status | Modify |

---

## Task 1: Improve model ref lookup

**Files:**
- Modify: `cemm/kernel/semantic_interpreter.py`
- Modify: `cemm/tests/test_causal_inference.py`

- [ ] **Step 1: Change signature and update call site**

Change `_lookup_model_refs(self, processes)` to `_lookup_model_refs(self, processes, entity_refs, content)`.

Update the call site in `_build_graph` to pass `entity_refs` and `signal.content`.

- [ ] **Step 2: Add precondition/effect matching**

In `_lookup_model_refs`, after the existing registry-key and name passes, add:

```python
if self._store and len(model_ids) < 10:
    entity_phrases = {
        (ref.get("entity_id", "") or ref.get("entity", "")).lower()
        for ref in entity_refs
    }
    entity_phrases.discard("")
    if entity_phrases:
        for model in self._store.models.find_by_kind(ModelKind.CAUSAL_RULE.value, ModelStatus.ACTIVE.value, limit=100):
            for phrase in entity_phrases:
                if any(phrase in pre.lower() for pre in (model.preconditions or [])) or any(phrase in eff.lower() for eff in (model.effects or [])):
                    if model.id not in seen:
                        model_ids.append(model.id)
                        seen.add(model.id)
                    break
            if len(model_ids) >= 10:
                break
```

- [ ] **Step 3: Add test**

Add a test that verifies the model ref for "heat causes melting" is `causal_heat_melt` and not `causal_rain_flooding`.

```python
def test_causal_model_ref_matches_input_semantics():
    store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
    output = process_input("heat causes melting", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    assert output is not None
    result = recursive_loop._last_result
    assert result is not None
    assert result.semantic_event_graph is not None
    assert "causal_heat_melt" in result.semantic_event_graph.model_refs
    assert result.inference_packet is not None
    assert any("melt" in p.get("predicate", "").lower() for p in result.inference_packet.predictions), result.inference_packet.predictions
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest cemm/tests/test_causal_inference.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 6: Run manual integration test**

Run: `python manual_integration_test.py`
Expected: 25 cases, 0 gaps

- [ ] **Step 7: Commit**

```bash
git add cemm/kernel/semantic_interpreter.py cemm/tests/test_causal_inference.py
git commit -m "feat: match causal model refs to entity phrases in SemanticInterpreter"
```

---

## Self-Review

### Spec Coverage

| Gap | Coverage |
|---|---|
| SemanticEventGraph model edges only one model | Model refs now resolve to the correct model based on preconditions/effects. |
| Causal inference limited to one seeded model | Multiple causal models can now be selected at runtime based on input semantics. |

### Placeholder Scan

No placeholders.
