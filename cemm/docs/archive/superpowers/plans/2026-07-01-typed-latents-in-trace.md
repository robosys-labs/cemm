# Populate Full Typed Latents in Trace

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this task-by-task.

**Goal:** Make a small step toward deeper CEMM-SLC integration by populating all typed latent spaces in the `Trace` object during `process_input`. Currently only `SemanticAnswerGraph.answer_latent` is populated; the `Trace` should carry the full `TypedLatents` snapshot for training and learning.

**Architecture:** `LatentEncoder.encode_all` can produce a `TypedLatents` object from a turn's entities, processes, claims, models, and answer. We add a `typed_latents` field to `Trace` and populate it in `__main__.process_input` after operator execution.

**Tech Stack:** Python 3.13, Trace, LatentEncoder, TypedLatents, process_input.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `cemm/types/trace.py` | Add typed_latents field | Modify |
| `cemm/__main__.py` | Populate typed_latents in Trace | Modify |
| `cemm/tests/test_typed_latent_spaces.py` | Verify trace typed latents | Modify |
| `cemm/docs/superpowers/specs/2026-06-30-cemm-gap-analysis.md` | Update gap status | Modify |

---

## Task 1: Add typed_latents to Trace

**Files:**
- Modify: `cemm/types/trace.py`
- Modify: `cemm/__main__.py`
- Modify: `cemm/tests/test_typed_latent_spaces.py`

- [ ] **Step 1: Add field to Trace**

```python
from ..types.latent_space import TypedLatents

@dataclass
class Trace:
    ...
    typed_latents: TypedLatents | None = None
```

- [ ] **Step 2: Populate in process_input**

After the trace is built and before invariant checks, call `LatentEncoder.encode_all` and set `trace.typed_latents`.

```python
from .latent.encoder import LatentEncoder
latent_encoder = LatentEncoder(dim=64)
latents = latent_encoder.encode_all(
    entity_ids=kernel.memory.working_entity_ids + kernel.world.active_entity_ids,
    process_keys=[p.get("frame_key", "") for p in (seg.processes if seg else [])],
    state_keys=[s.get("state_key", "") for s in (seg.states if seg else [])],
    claim_tuples=[(c.predicate, c.object_value) for c in selected_claims],
    model_keys=[m.id for m in selected_models],
    context_id=kernel.id,
    self_mode=kernel.self_view.mode,
    self_uncertainty=kernel.self_view.uncertainty,
    memory_claim_ids=kernel.memory.working_claim_ids,
    action_kind=kind.value,
    answer_intent=sag_for_export.intent if sag_for_export else "",
    answer_claim_ids=sag_for_export.selected_claim_ids if sag_for_export else [],
    answer_model_ids=sag_for_export.selected_model_ids if sag_for_export else [],
)
trace.typed_latents = latents
```

- [ ] **Step 3: Add test**

In `test_typed_latent_spaces.py`, add:

```python
def test_trace_contains_full_typed_latents():
    store, registry, op_registry, pipeline, online_learner, recursive_loop = _setup()
    process_input("hello", store, registry, op_registry, pipeline, online_learner, recursive_loop, "ctx", [0])
    result = recursive_loop._last_result
    assert result is not None
    assert result.trace is not None
    assert result.trace.typed_latents is not None
    assert len(result.trace.typed_latents.answer) == 64
    assert len(result.trace.typed_latents.entity) == 64
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest cemm/tests/test_typed_latent_spaces.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 6: Run manual integration test**

Run: `python manual_integration_test.py`
Expected: 25 cases, 0 gaps

- [ ] **Step 7: Commit**

```bash
git add cemm/types/trace.py cemm/__main__.py cemm/tests/test_typed_latent_spaces.py
git commit -m "feat: populate full TypedLatents in Trace during process_input"
```

---

## Self-Review

### Spec Coverage

| Gap | Coverage |
|---|---|
| Typed latent spaces only answer_latent | Full typed latent snapshot now captured in Trace. |

### Placeholder Scan

No placeholders.
