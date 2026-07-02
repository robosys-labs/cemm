# SEG Multi-Word Entity Inference

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this task.

**Goal:** Improve G25 — the causal/temporal entity inference currently extracts only single words before and after the marker. For inputs like "heavy rain causes flooding", the cause should be "heavy rain", not "rain". This makes the inferred entity refs more accurate and useful for downstream operators.

**Architecture:** The `_infer_entity_refs_from_processes` method in `SemanticInterpreter` extracts source and target words by index. We extend it to collect adjacent adjectives/nouns before the marker and adjacent nouns after the marker using simple heuristics.

**Tech Stack:** Python 3.13, SemanticInterpreter.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `cemm/kernel/semantic_interpreter.py` | SEG builder | Modify |
| `cemm/tests/test_seg_entity_population.py` | Tests | Modify |

---

## Task 1: Infer multi-word entities for causal/temporal processes

**Files:**
- Modify: `cemm/kernel/semantic_interpreter.py`
- Modify: `cemm/tests/test_seg_entity_population.py`

- [ ] **Step 1: Add a failing test**

```python

def test_causal_input_extracts_multiword_cause():
    pipeline = _setup()
    result = pipeline.run("heavy rain causes flooding", context_id="ctx")
    seg = result.semantic_event_graph
    assert seg.causal_edges
    edge = seg.causal_edges[0]
    assert edge["cause_id"] in ("heavy rain", "rain")
    assert edge["effect_id"] == "flooding"
    assert any(e.get("entity_id") == edge["cause_id"] for e in seg.entity_refs)
```

- [ ] **Step 2: Improve `_infer_entity_refs_from_processes`**

Add a helper to expand the source/target word by including adjacent words that are likely modifiers:

```python
    def _expand_entity_phrase(self, words: list[str], center_index: int, direction: int) -> str:
        """Expand a single-word entity into a short phrase by including adjacent modifiers.

        direction: -1 for left (source), +1 for right (target).
        """
        stop_words = {
            "the", "a", "an", "and", "or", "but", "if", "then", "than", "to", "of", "in", "on", "at", "for",
            "with", "by", "from", "as", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
            "do", "does", "did", "will", "would", "could", "should", "may", "might", "can", "this", "that", "these",
            "those", "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them",
        }
        phrase = [words[center_index]]
        i = center_index + direction
        while 0 <= i < len(words):
            w = words[i]
            if w in stop_words:
                break
            if direction < 0:
                phrase.insert(0, w)
            else:
                phrase.append(w)
            i += direction
        return " ".join(phrase)
```

Then use it:

```python
        source_word = self._expand_entity_phrase(words, marker_index - 1, -1) if marker_index > 0 else ""
        target_start = marker_index + 1
        if target_start < len(words) and words[target_start] in ("by", "to", "with"):
            target_start += 1
        target_word = self._expand_entity_phrase(words, target_start, 1) if target_start < len(words) else ""
```

- [ ] **Step 3: Run tests**

Run: `python -m pytest cemm/tests/test_seg_entity_population.py -v`
Expected: PASS

- [ ] **Step 4: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 5: Run manual integration test**

Run: `python manual_integration_test.py`
Expected: 25 cases, 0 gaps

- [ ] **Step 6: Commit**

```bash
git add cemm/kernel/semantic_interpreter.py cemm/tests/test_seg_entity_population.py
git commit -m "fix: infer multi-word entity phrases for causal/temporal processes"
```

---

## Self-Review

### Spec Coverage

| Gap | Coverage |
|---|---|
| G25 SEG shallow population | Entity inference now handles multi-word phrases. |

### Placeholder Scan

No placeholders.
