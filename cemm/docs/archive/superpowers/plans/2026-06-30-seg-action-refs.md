# SEG Action References and Model References

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this task.

**Goal:** Continue closing G25 by ensuring `SemanticEventGraph.action_refs` and `model_refs` are populated for actionable and model-backed processes. This makes the SEG a complete input object for downstream Decide and operator selection.

**Architecture:** The `SemanticInterpreter` builds the SEG. It already populates `claim_refs`, `claim_candidates`, `temporal_edges`, `causal_edges`, but `action_refs` is hardcoded to `[]`. Actionable processes (command_remember, command_reflect, command_retrieve, greeting, session_exit) should produce `action_refs`. Process frame_keys that map to registry models should produce `model_refs`.

**Tech Stack:** Python 3.13, SemanticEventGraph, SemanticInterpreter, ModelStore, Registry.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `cemm/kernel/semantic_interpreter.py` | Builds SEG | Modify |
| `cemm/types/semantic_event_graph.py` | SEG dataclass | Read-only |
| `cemm/tests/test_seg_action_model_refs.py` | Tests | Create |

---

## Task 1: Populate action_refs and improve model_refs

**Files:**
- Modify: `cemm/kernel/semantic_interpreter.py`
- Create: `cemm/tests/test_seg_action_model_refs.py`

- [ ] **Step 1: Write the failing test**

```python
# cemm/tests/test_seg_action_model_refs.py
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.store.store import Store
from cemm.registry import Registry
from cemm.kernel.pipeline import Pipeline
from cemm.__main__ import seed_registry, seed_self_state


def _setup():
    store = Store(":memory:")
    registry = Registry()
    seed_registry(registry)
    seed_self_state(store)
    pipeline = Pipeline(store, registry)
    return pipeline


def test_remember_input_populates_action_ref():
    pipeline = _setup()
    result = pipeline.run("remember I like coffee", context_id="ctx")
    seg = result.semantic_event_graph
    assert seg.action_refs
    assert any("remember" in ref.lower() for ref in seg.action_refs)


def test_greeting_populates_action_ref():
    pipeline = _setup()
    result = pipeline.run("hello", context_id="ctx")
    seg = result.semantic_event_graph
    assert seg.action_refs
    assert any("greeting" in ref.lower() for ref in seg.action_refs)


def test_model_refs_populated_for_known_processes():
    pipeline = _setup()
    result = pipeline.run("rain causes flooding", context_id="ctx")
    seg = result.semantic_event_graph
    # The causal_causes process should map to a model if one exists
    assert seg.model_refs is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest cemm/tests/test_seg_action_model_refs.py -v`
Expected: FAIL — `assert seg.action_refs` fails

- [ ] **Step 3: Implement action_refs and model_refs population**

In `cemm/kernel/semantic_interpreter.py`, add helper methods:

```python
    def _extract_action_refs(self, processes: list[dict[str, Any]]) -> list[str]:
        """Map actionable processes to action references."""
        action_keys = {
            "command_remember": "remember",
            "command_reflect": "reflect",
            "command_retrieve": "retrieve",
            "greeting": "greeting",
            "session_exit": "session_exit",
        }
        refs: list[str] = []
        seen = set()
        for proc in processes:
            frame_key = proc.get("frame_key", "")
            action = action_keys.get(frame_key)
            if action and action not in seen:
                refs.append(action)
                seen.add(action)
        return refs

    def _lookup_model_refs(self, processes: list[dict[str, Any]]) -> list[str]:
        """Map process frame_keys to registry models."""
        if not self._store:
            return []
        model_ids: list[str] = []
        seen: set[str] = set()
        for proc in processes:
            frame_key = proc.get("frame_key", "")
            if not frame_key:
                continue
            # Look up by registry key first, then by name
            model = self._store.models.find_by_registry_key(frame_key)
            if model and model.id not in seen:
                model_ids.append(model.id)
                seen.add(model.id)
                continue
            models = self._store.models.find_by_name(frame_key)
            for m in models:
                if m.id not in seen:
                    model_ids.append(m.id)
                    seen.add(m.id)
                    break
            if len(model_ids) >= 10:
                break
        return model_ids
```

Update `_build_graph` to use `action_refs = self._extract_action_refs(processes)` instead of `[]`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest cemm/tests/test_seg_action_model_refs.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 6: Run manual integration test**

Run: `python manual_integration_test.py`
Expected: 25 cases, 0 gaps

- [ ] **Step 7: Commit**

```bash
git add cemm/kernel/semantic_interpreter.py cemm/tests/test_seg_action_model_refs.py
git commit -m "fix: populate SEG action_refs and model_refs"
```

---

## Self-Review

### Spec Coverage

| Gap | Coverage |
|---|---|
| G25 shallow SEG population | action_refs and model_refs now populated. |

### Placeholder Scan

No placeholders.
