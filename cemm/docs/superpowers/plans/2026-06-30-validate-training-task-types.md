# Validate Training Record Task Types

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this task.

**Goal:** Close G21 — several PROMPTS task types in `validate_training_record` only require `context_kernel`, allowing SAG-less or SEG-less records for tasks that should operate on semantic graphs. Add minimum payload requirements for the remaining task types.

**Architecture:** `validate_training_record` in `cemm_trainer.py` uses `SEG_REQUIRED_TASKS`, `SAG_REQUIRED_TASKS`, and `GRAPH_REQUIRED_TASKS` sets. We add more specific requirement sets for the remaining task types.

**Tech Stack:** Python 3.13, cemm_trainer.py, validate_training_record.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `cemm/cemm_trainer.py` | Training record validation | Modify |
| `cemm/tests/test_validate_training_record.py` | Validation tests | Modify |

---

## Task 1: Add task-type-specific validation requirements

**Files:**
- Modify: `cemm/cemm_trainer.py`
- Modify: `cemm/tests/test_validate_training_record.py`

- [ ] **Step 1: Define requirement sets**

Add these sets near the existing `SEG_REQUIRED_TASKS`:

```python
SELF_REQUIRED_TASKS = {
    "self_state_update",
}

MEMORY_REQUIRED_TASKS = {
    "memory_retrieval_ranking",
}

INFERENCE_REQUIRED_TASKS = {
    "next_event_prediction",
    "causal_effect_prediction",
    "causal_rule_extraction",
}

CONTRADICTION_REQUIRED_TASKS = {
    "contradiction_detection",
}

VERIFIER_REQUIRED_TASKS = {
    "verifier_calibration",
}

CANONICALIZATION_REQUIRED_TASKS = {
    "claim_canonicalization",
}

STRUCTURAL_INDUCTION_REQUIRED_TASKS = {
    "structural_induction",
}

RANKING_JUDGMENT_REQUIRED_TASKS = {
    "ranking_judgment",
}
```

- [ ] **Step 2: Extend validate_training_record**

Update `validate_training_record`:

```python
def validate_training_record(task_type: str, payload: dict) -> None:
    if "context_kernel" not in payload:
        raise ValueError(f"{task_type}: missing ContextKernel")
    if task_type in SEG_REQUIRED_TASKS and "semantic_event_graph" not in payload:
        raise ValueError(f"{task_type}: missing SemanticEventGraph")
    if task_type in GRAPH_REQUIRED_TASKS and "semantic_event_graph" not in payload:
        raise ValueError(f"{task_type}: missing SemanticEventGraph")
    if task_type in SAG_REQUIRED_TASKS and "semantic_answer_graph" not in payload:
        required_by = "text->answer" if task_type == "text_to_answer" else task_type
        raise ValueError(f"{task_type}: missing SemanticAnswerGraph (required to prevent {required_by} training)")
    if task_type in SELF_REQUIRED_TASKS and "self_state" not in payload:
        raise ValueError(f"{task_type}: missing self_state")
    if task_type in MEMORY_REQUIRED_TASKS and "memory_packet" not in payload:
        raise ValueError(f"{task_type}: missing memory_packet")
    if task_type in INFERENCE_REQUIRED_TASKS and "inference_packet" not in payload:
        raise ValueError(f"{task_type}: missing inference_packet")
    if task_type in CONTRADICTION_REQUIRED_TASKS and "semantic_answer_graph" not in payload:
        raise ValueError(f"{task_type}: missing semantic_answer_graph")
    if task_type in VERIFIER_REQUIRED_TASKS:
        if "output_text" not in payload:
            raise ValueError(f"{task_type}: missing output_text")
        if "selected_evidence" not in payload:
            raise ValueError(f"{task_type}: missing selected_evidence")
    if task_type in CANONICALIZATION_REQUIRED_TASKS and "semantic_event_graph" not in payload:
        raise ValueError(f"{task_type}: missing semantic_event_graph")
    if task_type in STRUCTURAL_INDUCTION_REQUIRED_TASKS and "semantic_event_graph" not in payload:
        raise ValueError(f"{task_type}: missing semantic_event_graph")
    if task_type in RANKING_JUDGMENT_REQUIRED_TASKS and "memory_packet" not in payload:
        raise ValueError(f"{task_type}: missing memory_packet")
    if task_type == "synthesis_verification":
        if "output_text" not in payload:
            raise ValueError("synthesis_verification: missing output_text")
        if "selected_evidence" not in payload:
            raise ValueError("synthesis_verification: missing selected_evidence")
```

- [ ] **Step 3: Add tests**

Append to `cemm/tests/test_validate_training_record.py`:

```python

def test_self_state_update_requires_self_state():
    with pytest.raises(ValueError, match="missing self_state"):
        validate_training_record("self_state_update", {"context_kernel": {}})


def test_memory_retrieval_ranking_requires_memory_packet():
    with pytest.raises(ValueError, match="missing memory_packet"):
        validate_training_record("memory_retrieval_ranking", {"context_kernel": {}})


def test_causal_rule_extraction_requires_inference_packet():
    with pytest.raises(ValueError, match="missing inference_packet"):
        validate_training_record("causal_rule_extraction", {"context_kernel": {}, "semantic_event_graph": {}})


def test_verifier_calibration_requires_output_text_and_evidence():
    with pytest.raises(ValueError, match="missing output_text"):
        validate_training_record("verifier_calibration", {"context_kernel": {}})
    with pytest.raises(ValueError, match="missing selected_evidence"):
        validate_training_record("verifier_calibration", {"context_kernel": {}, "output_text": "x"})


def test_claim_canonicalization_requires_seg():
    with pytest.raises(ValueError, match="missing semantic_event_graph"):
        validate_training_record("claim_canonicalization", {"context_kernel": {}})
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest cemm/tests/test_validate_training_record.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 6: Run manual integration test**

Run: `python manual_integration_test.py`
Expected: 25 cases, 0 gaps

- [ ] **Step 7: Commit**

```bash
git add cemm/cemm_trainer.py cemm/tests/test_validate_training_record.py
git commit -m "fix: add task-type validation requirements for remaining training records"
```

---

## Self-Review

### Spec Coverage

| Gap | Coverage |
|---|---|
| G21 task types only require context_kernel | Added specific requirements for remaining task types. |

### Placeholder Scan

No placeholders.
