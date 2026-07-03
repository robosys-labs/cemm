# Pipeline Packet Gaps — Context Inference Timing & PipelineResult Fields

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two architecture violations in the pipeline: (1) move context inference to run during Contextualize (before Interpret), and (2) populate `inference_packet` and `decision_packet` in `PipelineResult` so the runtime packet spec is satisfied.

**Architecture:** The architecture defines the operator sequence as Observe → Contextualize → Interpret → Ground → Retrieve → Infer → Decide → Realize → Update → Learn. The current pipeline runs `ContextInferenceEngine.infer()` after Interpret and Ground, which means context state cannot influence interpretation. Also, `PipelineResult` carries `semantic_event_graph`, `grounded_graph`, `memory_packet`, but not `inference_packet` or `decision_packet`, forcing `process_input()` to re-run inference and decision outside the pipeline. This plan fixes both.

**Tech Stack:** Python 3.13, dataclasses, typed ContextKernel, SemanticEventGraph, InferencePacket, DecisionPacket.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `cemm/kernel/pipeline.py` | Pipeline orchestration | Modify |
| `cemm/types/context_inference.py` | ContextInference dataclass | Modify (add `frame_id` if missing) |
| `cemm/types/context_kernel.py` | ContextKernel fields | Read-only |
| `cemm/types/packets.py` | InferencePacket, DecisionPacket dataclasses | Read-only |
| `cemm/kernel/context_inference.py` | ContextInferenceEngine | Read-only |
| `cemm/kernel/decision_router.py` | DecisionRouter | Read-only |
| `cemm/__main__.py` | Runtime that uses pipeline result | Modify |
| `cemm/tests/test_pipeline_packet_fields.py` | Tests for PipelineResult fields | Create |
| `cemm/tests/test_context_inference_timing.py` | Tests for context inference timing | Create |

---

## Task 1: Move Context Inference Before Interpret

**Files:**
- Modify: `cemm/kernel/pipeline.py:110-140` (reorder pipeline stages)
- Create: `cemm/tests/test_context_inference_timing.py`

- [ ] **Step 1: Write the failing test**

```python
# cemm/tests/test_context_inference_timing.py
from __future__ import annotations
import os, sys, time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from cemm.store.store import Store
from cemm.registry import Registry
from cemm.kernel.pipeline import Pipeline


def test_context_inference_runs_before_interpret():
    """Context inference should be applied to the kernel before
    UOL/semantic interpretation, so the inferred frame can bias
    interpretation."""
    store = Store(":memory:")
    registry = Registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("hello", context_id="ctx_test")
    kernel = result.kernel
    assert kernel is not None
    # The kernel should have the inferred frame in active frames
    assert "session_opening" in kernel.memory.active_frame_ids or "greeting" in kernel.memory.active_frame_ids
    assert result.context_inference is not None
    assert result.context_inference.frame_id in ("session_opening", "greeting")


def test_context_inference_affects_semantic_interpretation():
    """A first-turn short greeting should produce a greeting process in the SEG
    even if UOL matching is weak, because context inference biases toward greeting."""
    store = Store(":memory:")
    registry = Registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("hey", context_id="ctx_test", budget_override={"max_entities": 10})
    seg = result.semantic_event_graph
    assert seg is not None
    frame_keys = [p.get("frame_key", "") for p in seg.processes]
    assert "greeting" in frame_keys
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest cemm/tests/test_context_inference_timing.py -v`
Expected: FAIL — `AssertionError: assert 'session_opening' in kernel.memory.active_frame_ids` or similar

- [ ] **Step 3: Reorder pipeline stages in `pipeline.py`**

In `cemm/kernel/pipeline.py`, find the current order:

```python
        # Interpret: SemanticEventGraph + UOL atoms
        semantic_event_graph = self._semantic_interpreter.run(signal, kernel)
        semantics = interpret_signal(signal, kernel, self._store, main_registry=self._registry)
        if semantics is not None:
            uol_atoms = self._uol_mapper.map_signal(signal.content, kernel)
            semantics.uol_atoms = uol_atoms
            quality_keys, process_keys = self._uol_mapper.compile_to_pragmatic_keys(uol_atoms)
            kernel.user.affect.active_quality_atom_keys = quality_keys
            if kernel.conversation.dynamics:
                kernel.conversation.dynamics.active_process_atom_keys = process_keys
            signal.observation_semantics = semantics
            if semantics.semantic_cluster_key:
                kernel.user.affect = update_user_affect(kernel.user.affect, semantics, kernel, signal.id)
                kernel.conversation.dynamics = update_conversation_dynamics(
                    kernel.conversation.dynamics, semantics, kernel, signal.id
                )

        # Ground entities, time, frame, permission
        grounded_graph = self._grounding_pipeline.run(semantic_event_graph, kernel)

        # Infer context from signal + grounded graph + kernel (not raw text alone)
        context_inference = self._context_inference_engine.infer(signal, kernel)
        self._context_inference_engine.apply_to_kernel(context_inference, kernel)

        # Seed entity IDs from graph for graph-grounded retrieval
        for ref in semantic_event_graph.entity_refs:
            eid = ref.get("entity_id", "")
            if eid and eid not in kernel.memory.working_entity_ids:
                kernel.memory.working_entity_ids.append(eid)
```

Move the context inference block to run immediately after the kernel is built (after `self_state` and before the `# Interpret` comment). The new order should be:

1. Build kernel
2. Load self state
3. **Context inference** (new location)
4. **Interpret** (semantic graph)
5. **Ground**
6. **Retrieve**

After the change, the code around lines 110-140 should look like:

```python
        self_state = self._store.self_store.latest()
        if self_state:
            kernel.self_view = SelfView.from_self_state(self_state, kernel.memory.working_claim_ids)
        else:
            kernel.self_view = SelfView()

        # Contextualize: infer context from signal + kernel before interpretation
        context_inference = self._context_inference_engine.infer(signal, kernel)
        self._context_inference_engine.apply_to_kernel(context_inference, kernel)

        # Interpret: SemanticEventGraph + UOL atoms
        semantic_event_graph = self._semantic_interpreter.run(signal, kernel)
        semantics = interpret_signal(signal, kernel, self._store, main_registry=self._registry)
        if semantics is not None:
            uol_atoms = self._uol_mapper.map_signal(signal.content, kernel)
            semantics.uol_atoms = uol_atoms
            quality_keys, process_keys = self._uol_mapper.compile_to_pragmatic_keys(uol_atoms)
            kernel.user.affect.active_quality_atom_keys = quality_keys
            if kernel.conversation.dynamics:
                kernel.conversation.dynamics.active_process_atom_keys = process_keys
            signal.observation_semantics = semantics
            if semantics.semantic_cluster_key:
                kernel.user.affect = update_user_affect(kernel.user.affect, semantics, kernel, signal.id)
                kernel.conversation.dynamics = update_conversation_dynamics(
                    kernel.conversation.dynamics, semantics, kernel, signal.id
                )

        # Ground entities, time, frame, permission
        grounded_graph = self._grounding_pipeline.run(semantic_event_graph, kernel)

        # Seed entity IDs from graph for graph-grounded retrieval
        for ref in semantic_event_graph.entity_refs:
            eid = ref.get("entity_id", "")
            if eid and eid not in kernel.memory.working_entity_ids:
                kernel.memory.working_entity_ids.append(eid)
```

Remove the duplicate context inference block that was previously after grounding.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest cemm/tests/test_context_inference_timing.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite to check regressions**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 6: Commit**

```bash
git add cemm/kernel/pipeline.py cemm/tests/test_context_inference_timing.py
git commit -m "fix: run context inference during Contextualize, before Interpret"
```

---

## Task 2: Populate `inference_packet` and `decision_packet` in PipelineResult

**Files:**
- Modify: `cemm/kernel/pipeline.py:160-200` (add inference/decision stages)
- Modify: `cemm/__main__.py:310-320` (use pipeline_result.inference_packet)
- Create: `cemm/tests/test_pipeline_packet_fields.py`

- [ ] **Step 1: Write the failing test**

```python
# cemm/tests/test_pipeline_packet_fields.py
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from cemm.store.store import Store
from cemm.registry import Registry
from cemm.kernel.pipeline import Pipeline


def test_pipeline_result_carries_inference_packet():
    store = Store(":memory:")
    registry = Registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("rain causes flooding", context_id="ctx_test")
    assert result.inference_packet is not None
    assert result.inference_packet.id
    assert result.inference_packet.source_signal_id


def test_pipeline_result_carries_decision_packet():
    store = Store(":memory:")
    registry = Registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("hello", context_id="ctx_test")
    assert result.decision_packet is not None
    assert result.decision_packet.action_kind in ("answer", "ask", "abstain", "remember")


def test_pipeline_result_includes_context_inference():
    store = Store(":memory:")
    registry = Registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("ok", context_id="ctx_test")
    assert result.context_inference is not None
    assert result.context_inference.frame_id == "acknowledgment"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest cemm/tests/test_pipeline_packet_fields.py -v`
Expected: FAIL — `AssertionError: assert result.inference_packet is not None`

- [ ] **Step 3: Add Inference and Decide stages to pipeline**

In `cemm/kernel/pipeline.py`, add imports:

```python
from ..kernel.decision_router import DecisionRouter
from ..causal.inference import CausalInference
from ..types.packets import InferencePacket, DecisionPacket
```

(Note: `InferencePacket` is already imported via `from ..types.packets import ...`, but confirm `DecisionPacket` is imported. If not, add it.)

In `Pipeline.__init__`, add:

```python
        self._causal_inference = CausalInference(store)
        self._decision_router = DecisionRouter()
```

In `Pipeline.run`, after grounding and retrieval, add the Infer and Decide stages:

```python
        # Infer: causal inference + slot inference
        inference_packet = InferencePacket(
            id=uuid.uuid4().hex[:16],
            source_signal_id=signal.id,
            context_id=kernel.id,
        )
        if semantic_event_graph and semantic_event_graph.causal_edges:
            inference_packet = self._causal_inference.predict(
                signal.content,
                semantic_event_graph.claim_refs,
                kernel,
                graph=semantic_event_graph,
            )

        # Decide: choose action based on grounded graph, memory, inference
        decision_packet = self._decision_router.run(
            graph=semantic_event_graph,
            kernel=kernel,
            grounded_graph=grounded_graph,
            memory_packet=memory_packet,
            inference_packet=inference_packet,
            input_text=signal.content,
            observation_semantics=signal.observation_semantics,
            context_inference=context_inference,
        )

        # Pass decision to kernel for downstream action execution
        kernel.goal.action_kind = decision_packet.action_kind
```

Then update the `PipelineResult` constructor to include these:

```python
        result = PipelineResult(
            kernel=kernel,
            ranked_claim_ids=kernel.memory.working_claim_ids,
            ranked_model_ids=[m.id for m in retrieval_result.models],
            semantic_event_graph=semantic_event_graph,
            grounded_graph=grounded_graph,
            memory_packet=memory_packet,
            context_inference=context_inference,
            inference_packet=inference_packet,
            decision_packet=decision_packet,
        )
```

- [ ] **Step 4: Update `process_input` in `__main__.py` to use pipeline packets**

In `cemm/__main__.py`, find the inference and decision construction code:

```python
    inference_packet = InferencePacket()
    sim_result = None
    graph = pipeline_result.semantic_event_graph
    if graph and (graph.causal_edges or kernel.goal.required_slots):
        causal = CausalInference(store)
        inference_packet = causal.predict(text, selected_claim_ids, kernel, graph=graph)
        if graph.causal_edges:
            sim_engine = SimulationEngine(store)
            sim_result = sim_engine.simulate(text, kernel)
    predictions = inference_packet.predictions
```

Replace with:

```python
    inference_packet = pipeline_result.inference_packet or InferencePacket()
    sim_result = None
    graph = pipeline_result.semantic_event_graph
    # Pipeline already ran causal inference; only run simulation if causal edges exist
    if graph and graph.causal_edges:
        sim_engine = SimulationEngine(store)
        sim_result = sim_engine.simulate(text, kernel)
    predictions = inference_packet.predictions
```

Also, the decision router call in `process_input` should use the pipeline's decision_packet as a first-class source, but still allow override (the pipeline's decision is the authoritative one). Find:

```python
        decision_router = DecisionRouter()
        decision = decision_router.run(
            graph=pipeline_result.semantic_event_graph,
            kernel=kernel,
            grounded_graph=grounded_graph,
            memory_packet=memory_packet,
            inference_packet=inference_packet if inference_packet.predictions else None,
            input_text=text,
            observation_semantics=input_signal.observation_semantics,
            context_inference=context_inference,
        )
```

Replace with:

```python
        decision = pipeline_result.decision_packet
        if decision is None:
            decision_router = DecisionRouter()
            decision = decision_router.run(
                graph=pipeline_result.semantic_event_graph,
                kernel=kernel,
                grounded_graph=grounded_graph,
                memory_packet=memory_packet,
                inference_packet=inference_packet if inference_packet.predictions else None,
                input_text=text,
                observation_semantics=input_signal.observation_semantics,
                context_inference=context_inference,
            )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest cemm/tests/test_pipeline_packet_fields.py -v`
Expected: PASS

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 7: Run manual integration test**

Run: `python manual_integration_test.py`
Expected: 25 cases, 0 gaps

- [ ] **Step 8: Commit**

```bash
git add cemm/kernel/pipeline.py cemm/__main__.py cemm/tests/test_pipeline_packet_fields.py
git commit -m "feat: populate inference_packet and decision_packet in PipelineResult"
```

---

## Self-Review

### Spec Coverage

| Gap | Task |
|---|---|
| G32 Context inference runs after Ground, not during Contextualize | Task 1 |
| G28 PipelineResult missing inference_packet and decision_packet | Task 2 |

### Placeholder Scan

No placeholders. All steps contain complete code.

### Type Consistency

- `PipelineResult` fields: `context_inference`, `inference_packet`, `decision_packet` — all added in Task 2
- `Pipeline.__init__` adds `self._causal_inference` and `self._decision_router`
- `DecisionRouter.run()` already accepts `observation_semantics` and `context_inference` from the merged worktree
- `InferencePacket` constructor signature: confirm `id`, `source_signal_id`, `context_id` fields exist; if not, adjust to the actual constructor in `cemm/types/packets.py`
- `CausalInference.predict()` signature: `predict(self, text, selected_claim_ids, kernel, graph=None)` — call it with `signal.content`, `semantic_event_graph.claim_refs`, `kernel`, `graph=semantic_event_graph`
