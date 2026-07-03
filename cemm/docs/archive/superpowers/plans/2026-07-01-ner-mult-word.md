# Improve Learned NER for Multi-Word Entities

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this task-by-task.

**Goal:** Narrow the NER generalization gap by extending the synthetic training corpus to include multi-word person, place, and organization names. The learned tagger already uses BIO tagging; the training data was the limiting factor.

**Architecture:** Update `cemm/scripts/train_ner_tagger.py` to generate multi-word entities and template sentences that exercise them. Retrain the tagger and save new weights. The `SemanticInterpreter` integration remains unchanged because the tagger's `extract_entities` already handles IOB spans.

**Tech Stack:** Python 3.13, NERTagger.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `cemm/scripts/train_ner_tagger.py` | Generate multi-word training data | Modify |
| `cemm/data/models/ner_tagger_weights.json` | Updated weights | Regenerate |
| `cemm/tests/test_learned_ner.py` | Verify multi-word entity extraction | Modify |
| `cemm/docs/superpowers/specs/2026-06-30-cemm-gap-analysis.md` | Update gap status | Modify |

---

## Task 1: Add multi-word entity training data

**Files:**
- Modify: `cemm/scripts/train_ner_tagger.py`
- Modify: `cemm/tests/test_learned_ner.py`

- [ ] **Step 1: Add multi-word entity lists**

Add lists like:

```python
PERSONS_MULTI = ["New York", "San Francisco", "Los Angeles", "United States", "European Union"]
PLACES_MULTI = ["New York", "San Francisco", "Los Angeles", "United States", "European Union"]
ORGS_MULTI = ["Microsoft Corporation", "Google LLC", "Apple Inc.", "OpenAI LP", "IBM Research"]
```

Wait, persons and places overlap. Use different lists for persons and places to avoid confusion.

- [ ] **Step 2: Update templates and annotation logic**

Use multi-word templates and tokenize carefully so multi-word entities span multiple tokens.

- [ ] **Step 3: Retrain and save**

Run `python cemm/scripts/train_ner_tagger.py`.

- [ ] **Step 4: Add test**

Add a test that verifies extraction of a multi-word entity like "New York" or "Microsoft Corporation".

- [ ] **Step 5: Run tests**

Run: `python -m pytest cemm/tests/test_learned_ner.py -v`
Expected: PASS

- [ ] **Step 6: Run full suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 7: Run manual integration**

Run: `python manual_integration_test.py`
Expected: 25 cases, 0 gaps

- [ ] **Step 8: Commit**

```bash
git add cemm/scripts/train_ner_tagger.py cemm/data/models/ner_tagger_weights.json cemm/tests/test_learned_ner.py
git commit -m "feat: improve learned NER with multi-word entity training"
```

---

## Self-Review

### Spec Coverage

| Gap | Coverage |
|---|---|
| NER limited to synthetic/single-token | Multi-word entities now included in training and extraction. |

### Placeholder Scan

No placeholders.
