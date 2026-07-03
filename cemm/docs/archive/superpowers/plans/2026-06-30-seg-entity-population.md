# SEG Entity Population for Causal/Temporal Edges

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this task.

**Goal:** Fix the shallow population of `SemanticEventGraph` (G25) for causal and temporal inputs by ensuring entity references are inferred when the UOL mapper only emits process atoms but no entity atoms. This makes `causal_edges` and `temporal_edges` meaningful (with real cause/effect entity IDs) and unblocks downstream `CausalInference` and `SimulationEngine`.

**Architecture:** The `SemanticInterpreter` builds the SEG from UOL atoms. Currently it only uses `entity_ref` atoms for entities. For causal inputs like "rain causes flooding", the UOL mapper emits a `causal_causes` process but no entity refs, so the causal edge has `cause_id="unknown"` and `effect_id="unknown"`. The interpreter should infer entity refs from the process context when no entity atoms are present.

**Tech Stack:** Python 3.13, SemanticEventGraph, UOL atoms, SemanticInterpreter.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `cemm/kernel/semantic_interpreter.py` | Builds SEG from UOL atoms | Modify |
| `cemm/types/semantic_event_graph.py` | SEG dataclass | Read-only |
| `cemm/tests/test_seg_entity_population.py` | SEG population tests | Create |

---

## Task 1: Infer entity refs from causal/temporal processes

**Files:**
- Modify: `cemm/kernel/semantic_interpreter.py`
- Create: `cemm/tests/test_seg_entity_population.py`

- [ ] **Step 1: Write the failing test**

```python
# cemm/tests/test_seg_entity_population.py
from __future__ import annotations
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.store.store import Store
from cemm.registry import Registry
from cemm.kernel.pipeline import Pipeline
from cemm.__main__ import seed_registry, seed_self_state


def test_causal_input_populates_entity_refs():
    store = Store(":memory:")
    registry = Registry()
    seed_registry(registry)
    seed_self_state(store)
    pipeline = Pipeline(store, registry)
    result = pipeline.run("rain causes flooding", context_id="ctx")
    seg = result.semantic_event_graph
    assert seg is not None
    assert seg.causal_edges
    edge = seg.causal_edges[0]
    assert edge["cause_id"] != "unknown"
    assert edge["effect_id"] != "unknown"
    assert any(e.get("entity_id") == edge["cause_id"] for e in seg.entity_refs)
    assert any(e.get("entity_id") == edge["effect_id"] for e in seg.entity_refs)


def test_causal_input_populates_claim_candidates():
    store = Store(":memory:")
    registry = Registry()
    seed_registry(registry)
    seed_self_state(store)
    pipeline = Pipeline(store, registry)
    result = pipeline.run("rain causes flooding", context_id="ctx")
    seg = result.semantic_event_graph
    assert seg.claim_candidates
    candidate = seg.claim_candidates[0]
    assert candidate["subject"] != "user" or candidate["predicate"] != "causes"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest cemm/tests/test_seg_entity_population.py -v`
Expected: FAIL — `edge["cause_id"] == "unknown"`

- [ ] **Step 3: Add entity inference in `SemanticInterpreter._build_graph`**

In `cemm/kernel/semantic_interpreter.py`, before building the graph, add entity refs from the text content for causal and temporal processes.

Modify `_build_graph` to:

1. Detect causal/temporal processes in atoms.
2. If no entity refs exist and a causal/temporal process is found, extract two entity references from the content: one for the cause/before and one for the effect/after.
3. Use simple heuristics: the word before the causal marker is the cause, the word after is the effect. Causal markers: `causes`, `caused by`, `leads to`, `because`, `so`. Temporal markers: `before`, `after`, `during`, `then`.

For the initial implementation, add a helper method:

```python
    def _infer_entity_refs_from_processes(
        self, content: str, processes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Infer entity refs from causal/temporal processes when no entity atoms are present."""
        inferred = []
        content_lower = content.lower().strip()
        words = content_lower.split()
        if len(words) < 3:
            return inferred

        causal_map = {
            "causal_causes": ("causes", "caused", "cause"),
            "causal_caused_by": ("caused by", "caused", "by"),
            "causal_leads_to": ("leads to", "leads", "lead to"),
            "causal_because": ("because",),
            "causal_so": ("so",),
        }
        temporal_map = {
            "temporal_before": ("before",),
            "temporal_after": ("after",),
            "temporal_during": ("during",),
            "temporal_overlaps": ("overlaps", "while"),
            "temporal_starts": ("starts", "begins"),
            "temporal_finishes": ("finishes", "ends"),
        }

        relation_words = set()
        for proc in processes:
            frame_key = proc.get("frame_key", "")
            relation_words.update(causal_map.get(frame_key, ()))
            relation_words.update(temporal_map.get(frame_key, ()))

        if not relation_words:
            return inferred

        # Find the marker position in the text
        marker_index = None
        for i, w in enumerate(words):
            if w in relation_words:
                marker_index = i
                break
            # Check bigram for "caused by", "leads to"
            if i + 1 < len(words):
                bigram = f"{w} {words[i + 1]}"
                if bigram in relation_words:
                    marker_index = i
                    break

        if marker_index is None:
            return inferred

        # Entity before the marker is the source/cause
        source_word = words[marker_index - 1] if marker_index > 0 else ""
        # Entity after the marker is the target/effect
        target_start = marker_index + 1
        # Skip "by" after "caused"
        if target_start < len(words) and words[target_start] in ("by", "to", "with"):
            target_start += 1
        target_word = words[target_start] if target_start < len(words) else ""

        if source_word:
            inferred.append({
                "kind": "entity_ref",
                "entity_id": source_word,
                "role": "cause" if any(proc.get("frame_key", "").startswith("causal_") for proc in processes) else "source",
                "confidence": 0.6,
            })
        if target_word:
            inferred.append({
                "kind": "entity_ref",
                "entity_id": target_word,
                "role": "effect" if any(proc.get("frame_key", "").startswith("causal_") for proc in processes) else "target",
                "confidence": 0.6,
            })

        return inferred
```

Then in `_build_graph`, before extracting edges, call this helper and add the inferred entity refs to the entity_refs list if no entity refs are present:

```python
        if not entity_refs:
            entity_refs = self._infer_entity_refs_from_processes(signal.content, processes)
```

Update `_extract_causal_edges_from_atoms` and `_extract_temporal_edges_from_atoms` to use the inferred entity refs.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest cemm/tests/test_seg_entity_population.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 6: Run manual integration test**

Run: `python manual_integration_test.py`
Expected: 25 cases, 0 gaps

- [ ] **Step 7: Commit**

```bash
git add cemm/kernel/semantic_interpreter.py cemm/tests/test_seg_entity_population.py
git commit -m "fix: infer entity refs for causal/temporal processes in SEG"
```

---

## Self-Review

### Spec Coverage

| Gap | Coverage |
|---|---|
| G25 SemanticEventGraph shallow population | Partially addressed — entity refs now inferred for causal/temporal processes, making causal/temporal edges meaningful. |

### Placeholder Scan

No placeholders. All code is complete.

### Type Consistency

- Entity refs are dicts with `kind`, `entity_id`, `role`, `confidence`, matching the existing structure.
- Causal/temporal edge extraction already expects entity refs and uses them correctly.
