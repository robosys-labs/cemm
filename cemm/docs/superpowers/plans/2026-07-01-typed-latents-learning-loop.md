# Use TypedLatents in the Learning Loop

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this task-by-task.

**Goal:** Close the "typed latent spaces / CEMM-SLC integration" gap by making the runtime actually use `TypedLatents` for learning. First, persist typed latents in stored traces; then use latent similarity to bias model ranking toward historically successful strategies.

**Architecture:** `ActionStore` already serializes `Trace` into `trace_json`. We extend that serialization to include `typed_latents`. Then we add a small latent-experience lookup: `Ranker` can retrieve recent actions with stored latent snapshots and boost models whose historical traces had similar latent contexts and positive outcomes.

**Tech Stack:** Python 3.13, ActionStore, Trace, TypedLatents, Ranker.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `cemm/store/action_store.py` | Serialize/deserialize typed_latents in Trace | Modify |
| `cemm/retrieval/ranker.py` | Use latent similarity to bias model ranking | Modify |
| `cemm/tests/test_typed_latent_spaces.py` | Verify typed latents persist in action store and ranker uses them | Modify |
| `cemm/docs/superpowers/specs/2026-06-30-cemm-gap-analysis.md` | Update gap status | Modify |

---

## Task 1: Persist typed latents in action store

**Files:**
- Modify: `cemm/store/action_store.py`

- [ ] **Step 1: Extend `_trace_to_dict`**

Include typed_latents as nested dicts.

```python
d["typed_latents"] = {
    "entity": trace.typed_latents.entity,
    "process": trace.typed_latents.process,
    ...
} if trace.typed_latents else None
```

- [ ] **Step 2: Extend `_row_to_action` deserialization**

Reconstruct `TypedLatents` from `trace_json` if present.

---

## Task 2: Use latent similarity in Ranker

**Files:**
- Modify: `cemm/retrieval/ranker.py`

- [ ] **Step 1: Add cosine similarity helper**

```python
@staticmethod
def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
```

- [ ] **Step 2: Add `_latent_similarity_bonus`**

Query recent actions, compute latent similarity between the current kernel's latent snapshot and each action's trace latent snapshot, and return a small bonus for models that appeared in successful actions with high similarity.

- [ ] **Step 3: Apply bonus in `rank_models`**

Use `score_model(...)` with an additional `latent_bonus` parameter (or just boost the score).

---

## Task 3: Add tests

**Files:**
- Modify: `cemm/tests/test_typed_latent_spaces.py`

- [ ] **Step 1: Add persistence test**

Verify that an action stored with a trace containing typed_latents round-trips through `ActionStore`.

- [ ] **Step 2: Add ranking test**

Verify that `Ranker.rank_models` boosts a model that was previously used in a similar successful context.

---

## Task 4: Run verification

- Run: `python -m pytest cemm/tests/test_typed_latent_spaces.py cemm/tests/test_action_store.py -v`
- Run: `python -m pytest cemm/tests/ --tb=short`
- Run: `python manual_integration_test.py`

---

## Task 5: Commit

```bash
git add cemm/store/action_store.py cemm/retrieval/ranker.py cemm/tests/test_typed_latent_spaces.py
git commit -m "feat: persist typed latents in traces and use latent similarity for model ranking"
```

---

## Self-Review

### Spec Coverage

| Gap | Coverage |
|---|---|
| No typed latent spaces | Latent snapshots are now persisted and used to improve model ranking. |
| CEMM-SLC learning loop | First step: historical latent similarity influences future retrieval. |

### Placeholder Scan

No placeholders.
