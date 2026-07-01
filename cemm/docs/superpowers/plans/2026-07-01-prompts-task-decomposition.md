# PROMPTS Task Type Decomposition in Training Export

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the PROMPTS training gap by decomposing each full turn into the 25 task-type records defined in `cemm_trainer.py` so that every task type has a deployable training record.

**Architecture:** A single user turn triggers multiple CEMM subsystems: UOL mapping, semantic graph extraction, context inference, pragmatic interpretation, answer composition, memory retrieval, causal inference, structural induction, etc. Currently `training_export.serialize_turn` emits one record with `task_type="full_turn_export"`. We extend it to emit one record per subsystem stage, each with the correct `task_type` and the required payload fields validated by `validate_training_record`.

**Tech Stack:** Python 3.13, dataclasses, JSONL, `cemm_trainer.validate_training_record`, `kernel.training_export.serialize_turn`.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `cemm/kernel/training_export.py` | Decompose one turn into multiple task-type records | Modify |
| `cemm/tests/test_training_export_task_types.py` | Verify all 25 task types are emitted | Create |
| `cemm/scripts/generate_gold_task_types.py` | Generate gold examples for each task type | Create |
| `cemm/docs/superpowers/specs/2026-06-30-cemm-gap-analysis.md` | Mark gaps fixed | Modify |

---

## Task 1: Decompose training export into PROMPTS task types

**Files:**
- Modify: `cemm/kernel/training_export.py`
- Create: `cemm/tests/test_training_export_task_types.py`

- [ ] **Step 1: Write the failing test**

Create `cemm/tests/test_training_export_task_types.py` with a test that calls `serialize_turn` and asserts that the returned list contains at least one record for each of the 25 task types, and each record passes `validate_training_record`.

```python
from __future__ import annotations
import os, sys, time, uuid
from dataclasses import asdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.kernel.training_export import serialize_turn
from cemm.types.context_kernel import ContextKernel, Permission
from cemm.types.semantic_event_graph import SemanticEventGraph
from cemm.types.semantic_answer_graph import SemanticAnswerGraph
from cemm.types.packets import GroundedGraph, MemoryPacket, InferencePacket, DecisionPacket, ActionPlan
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.trace import Trace
from cemm.cemm_trainer import validate_training_record


_REQUIRED_TASK_TYPES = {
    "semantic_graph_extraction", "semantic_graph_denoising", "semantic_latent_target",
    "claim_extraction", "entity_resolution", "uol_mapping", "context_inference",
    "pragmatic_interpretation", "semantic_answer_composition", "operator_selection",
    "temporal_relation_derivation", "frame_classification", "semantic_text_realization",
    "text_to_answer", "self_state_update", "memory_retrieval_ranking",
    "next_event_prediction", "causal_effect_prediction", "causal_rule_extraction",
    "contradiction_detection", "verifier_calibration", "claim_canonicalization",
    "structural_induction", "ranking_judgment", "synthesis_verification",
}


def _make_signal() -> Signal:
    return Signal(
        id="s1",
        kind=SignalKind.INPUT,
        source_id="user",
        source_type=SourceType.USER,
        content="hello",
        observed_at=time.time(),
        context_id="ctx",
        salience=0.5,
        trust=0.8,
        permission=Permission.public(),
    )


def test_training_export_decomposes_all_prompts_task_types():
    kernel = ContextKernel(id="ctx", permission=Permission.public())
    seg = SemanticEventGraph(
        id="seg1", source_signal_ids=["s1"], context_id="ctx", entity_refs=[],
        processes=[], states=[], claim_refs=[], model_refs=[], action_refs=[],
        temporal_edges=[], causal_edges=[], permission_scope="public", confidence=0.7,
    )
    sag = SemanticAnswerGraph(
        id="sag1", intent="answer", source_signal_id="s1", context_id="ctx",
        selected_claim_ids=[], selected_model_ids=[], entity_refs=[], causal_edges=[],
        temporal_edges=[], verification_status="verified", confidence=0.7,
    )
    grounded = GroundedGraph(id="gg1", source_signal_ids=["s1"], context_id="ctx", missing_slots=[])
    memory = MemoryPacket(id="mp1", selected_signal_ids=["s1"], selected_claim_ids=[], selected_model_ids=[])
    inference = InferencePacket(id="ip1", predictions=[], implications=[], contradictions=[], missing_slots=[], state_deltas={}, inference_graph_input_signal_ids=["s1"])
    decision = DecisionPacket(
        action_kind="answer",
        action_plan=ActionPlan(action_kind="answer", execution_allowed=True, confidence=0.7, risk=0.0),
        confidence=0.7, reason="test",
    )
    trace = Trace(id="t1", input_signal_id="s1", output_signal_id="s1", operator_kind="answer", operator_params={})
    input_signal = _make_signal()

    records = serialize_turn(
        input_text="hello", output_text="hi", kernel=kernel, input_signal=input_signal,
        trace=trace, semantic_event_graph=seg, semantic_answer_graph=sag,
        grounded_graph=grounded, memory_packet=memory, inference_packet=inference,
        decision_packet=decision,
    )
    task_types = {r["task_type"] for r in records}
    missing = _REQUIRED_TASK_TYPES - task_types
    assert not missing, f"Missing task types: {missing}"

    for record in records:
        validate_training_record(record["task_type"], record["payload"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest cemm/tests/test_training_export_task_types.py -v`
Expected: FAIL with missing task types.

- [ ] **Step 3: Implement decomposition in `serialize_turn`**

Modify `serialize_turn` to return a list of records instead of a single dict. Use the existing full-turn record as a base, then derive per-task records:

1. `semantic_graph_extraction` — requires `semantic_event_graph`
2. `semantic_graph_denoising` — requires `semantic_event_graph` (if graph has any denoising artifacts, otherwise still include)
3. `semantic_latent_target` — requires `semantic_event_graph`
4. `claim_extraction` — requires `semantic_event_graph` and selected claim IDs
5. `entity_resolution` — requires `semantic_event_graph` entity_refs
6. `uol_mapping` — requires `semantic_event_graph` processes and/or a new `uol_atoms` field
7. `context_inference` — requires `context_inference` payload
8. `pragmatic_interpretation` — requires `observation_semantics` payload
9. `semantic_answer_composition` — requires `semantic_answer_graph`
10. `operator_selection` — requires `semantic_event_graph` and `decision_packet`
11. `temporal_relation_derivation` — requires `semantic_event_graph` temporal_edges
12. `frame_classification` — requires `semantic_event_graph` processes
13. `semantic_text_realization` — requires `semantic_answer_graph` and output_text
14. `text_to_answer` — requires `semantic_answer_graph`
15. `self_state_update` — requires `self_state` from `kernel.self_view`
16. `memory_retrieval_ranking` — requires `memory_packet`
17. `next_event_prediction` — requires `inference_packet` with predictions
18. `causal_effect_prediction` — requires `inference_packet` with predictions
19. `causal_rule_extraction` — requires `inference_packet`
20. `contradiction_detection` — requires `semantic_answer_graph` (and contradiction list if any)
21. `verifier_calibration` — requires `output_text` and `selected_evidence`
22. `claim_canonicalization` — requires `semantic_event_graph`
23. `structural_induction` — requires `semantic_event_graph`
24. `ranking_judgment` — requires `memory_packet`
25. `synthesis_verification` — requires `output_text` and `selected_evidence`

Also keep `full_turn_export` as the first record for backward compatibility.

Implementation sketch:

```python
def serialize_turn(...) -> list[dict[str, Any]]:
    records = []
    base_payload = {...}
    records.append({"task_type": "full_turn_export", "payload": base_payload, ...})
    # ... derive per-task records ...
    return records
```

- [ ] **Step 4: Update callers of `serialize_turn`**

Search for `serialize_turn` call sites and update them to handle a list of records.

- [ ] **Step 5: Run tests**

Run: `python -m pytest cemm/tests/test_training_export_task_types.py -v`
Expected: PASS

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 7: Run manual integration test**

Run: `python manual_integration_test.py`
Expected: 25 cases, 0 gaps

- [ ] **Step 8: Commit**

```bash
git add cemm/kernel/training_export.py cemm/tests/test_training_export_task_types.py
git commit -m "feat: decompose training export into 25 PROMPTS task types"
```

---

## Task 2: Generate gold examples for each PROMPTS task type

- [ ] Create `cemm/scripts/generate_gold_task_types.py` that writes one JSONL example per task type to `cemm/gold/task_types/`.

- [ ] Run the script and verify 25 output files.

- [ ] Add a test that asserts each task type file exists and is valid JSON.

---

## Self-Review

### Spec Coverage

| Gap | Coverage |
|---|---|
| 11 of 25 PROMPTS task types never produced by decomposition | `serialize_turn` emits one record per task type. |
| 18 of 25 PROMPTS task types produce no deployable records | Each record includes required payload and passes validation. |

### Placeholder Scan

No placeholders.
