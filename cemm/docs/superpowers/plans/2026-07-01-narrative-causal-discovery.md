# Narrative Causal Discovery in Inductor

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this task-by-task.

**Goal:** Extend the `Inductor` to discover causal models from narrative text (e.g., "rain causes flooding", "heat leads to melting"), not just from repeated outcome claims. This narrows the "causal inference not full inductive causal discovery" gap.

**Architecture:** A new `_find_narrative_causal_patterns` method in `Inductor` scans recent `Signal.content` for explicit causal connectors ("causes", "leads to", "results in", "produces", "makes"). It tokenizes around the connector, extracts entity/process phrases from the left and right clauses, and creates `CAUSAL_RULE` candidates when the same pattern is observed at least `feedback_threshold` times. These candidates are then handled by the existing auto-promotion path in `RecursiveLoop._run_induction`.

**Tech Stack:** Python 3.13, Inductor, ModelKind, ModelStatus.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `cemm/learning/inductor.py` | Narrative causal pattern discovery | Modify |
| `cemm/kernel/recursive_loop.py` | Already auto-promotes high-confidence causal rules | No change |
| `cemm/tests/test_causal_inference.py` | Verify narrative causal discovery | Modify |
| `cemm/docs/superpowers/specs/2026-06-30-cemm-gap-analysis.md` | Update gap status | Modify |

---

## Task 1: Discover causal models from narrative text

**Files:**
- Modify: `cemm/learning/inductor.py`
- Modify: `cemm/tests/test_causal_inference.py`

- [ ] **Step 1: Add `_find_narrative_causal_patterns`**

Add to `Inductor`:

```python
CAUSAL_CONNECTORS = [
    " causes ", " cause ", "causes ",
    " leads to ", " lead to ",
    " results in ", " result in ",
    " produces ", " produce ",
    " makes ", " make ",
    " triggers ", " trigger ",
    " creates ", " create ",
    " generates ", " generate ",
]


def _extract_causal_phrase(words: list[str], direction: str = "left") -> str:
    """Naive phrase extraction: keep content words until a stop word or connector."""
    stop = {"the", "a", "an", "and", "or", "but", "if", "then", "to", "of", "in", "on", "at", "for", "with", "by", "from", "as", "is", "are", "was", "were"}
    if direction == "left":
        phrase = []
        for w in reversed(words):
            if w in stop or w in {"causes", "leads", "results", "produces", "makes", "triggers", "creates", "generates"}:
                break
            phrase.insert(0, w)
        return "_".join(phrase) if phrase else ""
    else:
        phrase = []
        for w in words:
            if w in stop:
                if phrase:
                    break
                continue
            phrase.append(w)
        return "_".join(phrase) if phrase else ""


def _find_narrative_causal_patterns(self, domain: str | None = None) -> list[Model]:
    recent_signals = self._store.signals.find_recent(1000)
    counts: dict[tuple[str, str], list[Signal]] = defaultdict(list)
    for signal in recent_signals:
        if not signal.content:
            continue
        if domain and signal.domain != domain:
            continue
        content = " " + signal.content.lower().strip() + " "
        for connector in self.CAUSAL_CONNECTORS:
            if connector not in content:
                continue
            parts = content.split(connector, 1)
            if len(parts) != 2:
                continue
            left_words = parts[0].strip().split()
            right_words = parts[1].strip().split()
            left_phrase = _extract_causal_phrase(left_words, "left")
            right_phrase = _extract_causal_phrase(right_words, "right")
            if not left_phrase or not right_phrase:
                continue
            counts[(left_phrase, right_phrase)].append(signal)

    candidates: list[Model] = []
    for (left, right), signals in counts.items():
        if len(signals) < self._feedback_threshold:
            continue
        name = f"causal:{left}->{right}"
        if self._existing_causal_rule(name, right, None):
            continue
        now = time.time()
        model = Model(
            id=uuid.uuid4().hex[:16],
            kind=ModelKind.CAUSAL_RULE,
            name=name,
            description=f"Narrative causal rule: {left} -> {right} (from {len(signals)} signals)",
            preconditions=[f"process:{left}"],
            effects=[f"process:{right}"],
            evidence_signal_ids=[s.id for s in signals],
            confidence=min(1.0, 0.5 + 0.1 * len(signals)),
            status=ModelStatus.CANDIDATE,
            created_at=now,
            updated_at=now,
        )
        self._store.models.put(model)
        candidates.append(model)
    return candidates
```

Then call it from `maybe_induct`:

```python
candidates.extend(self._find_narrative_causal_patterns(domain))
```

- [ ] **Step 2: Add test**

Add a test that inserts several signals with the same causal phrase and verifies the resulting active model.

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
git add cemm/learning/inductor.py cemm/tests/test_causal_inference.py
git commit -m "feat: discover causal models from narrative text"
```

---

## Self-Review

### Spec Coverage

| Gap | Coverage |
|---|---|
| Causal inference not full inductive causal discovery | System now induces causal rules from explicit causal language in signals, in addition to repeated outcome claims. |

### Placeholder Scan

No placeholders.
