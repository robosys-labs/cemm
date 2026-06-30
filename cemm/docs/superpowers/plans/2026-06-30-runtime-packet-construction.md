# Runtime Packet Construction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Wire each SLC pipeline stage to produce typed packet dataclasses (GroundedGraph, MemoryPacket, InferencePacket, DecisionPacket) and reconcile the dual DecisionPacket.

**Architecture:** Pipeline stages currently produce side effects (kernel mutations, `list[dict]` returns). Each stage is refactored to return a typed packet from `types/packets.py`. The caller (`__main__.py`) is updated to consume these packets. The dual DecisionPacket is resolved by removing `kernel/decision_router.py`'s local copy and using the canonical `types/packets.py` version.

**Tech Stack:** Python 3.11+ dataclasses

---

## File Map

| File | Role |
|------|------|
| `types/trace.py` | Add optional packet ID fields |
| `kernel/pipeline.py` | Construct MemoryPacket + carry GroundedGraph/MemoryPacket in PipelineResult |
| `kernel/grounding.py` | Return GroundedGraph instead of mutating SEG |
| `kernel/decision_router.py` | Remove local DecisionPacket; import canonical; build ActionPlan |
| `causal/inference.py` | Return InferencePacket instead of list[dict] |
| `__main__.py` | Wire InferencePacket; translate action_kind str→ActionKind; pass packets to DecisionRouter |
| `types/packet_schemas.py` | Update DecisionPacket schema |
| `tests/test_packets.py` | Create tests for all 4 new packet construction paths |

---

### Task 1: Extend Trace and PipelineResult with packet fields

**Files:**
- Modify: `types/trace.py:7-27`
- Modify: `kernel/pipeline.py:29-41`

- [ ] **Step 1: Add grounded_graph_id, memory_packet_id, inference_packet_id to Trace**

```python
# In types/trace.py, add after line 27 (semantic_answer_graph_id):
    grounded_graph_id: str | None = None
    memory_packet_id: str | None = None
    inference_packet_id: str | None = None
```

Check: `Trace(context_id="t1", grounded_graph_id="gg1")` compiles.

- [ ] **Step 2: Add grounded_graph and memory_packet fields to PipelineResult**

```python
# In kernel/pipeline.py, add to PipelineResult after line 40:
    grounded_graph: GroundedGraph | None = None
    memory_packet: MemoryPacket | None = None
```

Need import at top: `from ..types.packets import GroundedGraph, MemoryPacket`

- [ ] **Step 3: Commit**

```bash
git add types/trace.py kernel/pipeline.py
git commit -m "feat: add packet fields to Trace and PipelineResult"
```

---

### Task 2: GroundingPipeline returns GroundedGraph

**Files:**
- Modify: `kernel/grounding.py`

- [ ] **Step 1: Add import for GroundedGraph**

```python
from ..types.packets import GroundedGraph
```

- [ ] **Step 2: Change run() signature and body**

```python
def run(self, graph: SemanticEventGraph, kernel: ContextKernel) -> GroundedGraph:
    self._resolver.resolve_self(kernel)
    resolved_ids: list[str] = []
    for ref in graph.entity_refs:
        name = ref.get("name", "")
        if name and not ref.get("entity_id"):
            resolved = self._resolver.resolve_by_name(name, kernel)
            if resolved:
                ref["entity_id"] = resolved[0].id    # backward compat: still mutate SEG
                ref["entity_type"] = resolved[0].type.value
                resolved_ids.append(resolved[0].id)
    invalidated_ids = self._frames.apply_frame_rules(kernel)
    for ref in graph.entity_refs:
        ref["frame_valid"] = ref.get("entity_id", "") not in invalidated_ids

    return GroundedGraph(
        semantic_event_graph_id=graph.id,
        entity_ids=resolved_ids,
        resolved_time_refs=[],
        resolved_location_ids=[],
        active_frame_ids=list(kernel.memory.active_frame_ids) if kernel.memory else [],
        permission=kernel.permission.scope.value if kernel.permission else "public",
        missing_slots=list(kernel.goal.missing_slots) if kernel.goal else [],
        confidence=graph.confidence,
    )
```

- [ ] **Step 3: Commit**

```bash
git add kernel/grounding.py
git commit -m "feat: GroundingPipeline returns typed GroundedGraph"
```

---

### Task 3: Pipeline constructs MemoryPacket and returns new packets

**Files:**
- Modify: `kernel/pipeline.py`

- [ ] **Step 1: Add imports for MemoryPacket, RankingTraceEntry, GroundedGraph**

In `kernel/pipeline.py`, add to existing imports:
```python
from ..types.packets import GroundedGraph, MemoryPacket, RankingTraceEntry
```

- [ ] **Step 2: Capture GroundedGraph from GroundingPipeline and build MemoryPacket after ranking**

In `pipeline.py`, change line 127 from:
```python
self._grounding_pipeline.run(semantic_event_graph, kernel)
```
to:
```python
grounded_graph = self._grounding_pipeline.run(semantic_event_graph, kernel)
```

After the ranking block (after line 153), add:
```python
memory_packet = MemoryPacket(
    selected_signal_ids=[signal.id],
    selected_claim_ids=kernel.memory.working_claim_ids,
    selected_model_ids=kernel.memory.candidate_model_ids,
    ranking_trace=[
        RankingTraceEntry(
            candidate_id=c.id,
            score=s,
            reason=f"ranked {s:.3f}",
        )
        for c, s in (ranked_claims if isinstance(ranked_claims, list) else [])
    ] if ranked_claims else [],
    confidence=sum(s for _, s in ranked_claims[:5]) / max(len(ranked_claims[:5]), 1) if ranked_claims else 0.5,
)
```

Add memory_packet and grounded_graph to PipelineResult construction:
```python
result = PipelineResult(
    kernel=kernel,
    ranked_claim_ids=kernel.memory.working_claim_ids,
    ranked_model_ids=[m.id for m in retrieval_result.models],
    semantic_event_graph=semantic_event_graph,
    grounded_graph=grounded_graph,
    memory_packet=memory_packet,
)
```

- [ ] **Step 3: Commit**

```bash
git add kernel/pipeline.py
git commit -m "feat: Pipeline constructs MemoryPacket and carries GroundedGraph"
```

---

### Task 4: CausalInference returns InferencePacket

**Files:**
- Modify: `causal/inference.py`

- [ ] **Step 1: Add import for InferencePacket**

```python
from ..types.packets import InferencePacket
```

- [ ] **Step 2: Change predict() return type and body**

```python
def predict(
    self,
    action_or_event: str,
    active_claim_ids: list[str],
    kernel: ContextKernel,
) -> InferencePacket:
    models = self._store.models.find_by_kind(
        ModelKind.CAUSAL_RULE.value, ModelStatus.ACTIVE.value,
    )
    active_claims = []
    for cid in active_claim_ids:
        claim = self._store.claims.get(cid)
        if claim:
            active_claims.append(claim)

    predictions: list[dict] = []
    for model in models:
        if not self._preconditions_match(model, active_claims, action_or_event):
            continue
        for effect in model.effects:
            predictions.append({
                "model_id": model.id,
                "predicate": effect,
                "confidence": model.confidence * model.trust,
            })

    predictions.sort(key=lambda p: p["confidence"], reverse=True)
    max_ranked = kernel.budget.max_ranked
    predictions = predictions[:max_ranked]

    return InferencePacket(
        implications=[],
        contradictions=[],
        predictions=predictions,
        missing_slots=list(kernel.goal.missing_slots) if kernel.goal else [],
        state_deltas={},
        confidence=sum(p["confidence"] for p in predictions) / max(len(predictions), 1) if predictions else 0.5,
    )
```

- [ ] **Step 3: Commit**

```bash
git add causal/inference.py
git commit -m "feat: CausalInference returns typed InferencePacket"
```

---

### Task 5: DecisionRouter uses canonical DecisionPacket

**Files:**
- Modify: `kernel/decision_router.py`

- [ ] **Step 1: Replace local DecisionPacket with import from canonical**

Remove lines 11-19 (the local `@dataclass DecisionPacket`). Add import:
```python
from ..types.packets import DecisionPacket, ActionPlan
```

- [ ] **Step 2: Update run() signature to accept packets**

```python
def run(
    self,
    graph: SemanticEventGraph,
    kernel: ContextKernel,
    grounded_graph: GroundedGraph | None = None,
    memory_packet: MemoryPacket | None = None,
    inference_packet: InferencePacket | None = None,
) -> DecisionPacket:
```

Add imports:
```python
from ..types.packets import GroundedGraph, MemoryPacket, InferencePacket
```

- [ ] **Step 3: Update internal logic to read from packets instead of individual params**

Replace `selected_claim_ids` / `selected_model_ids` / `predictions` references with packet fields:

```python
selected_claim_ids = memory_packet.selected_claim_ids if memory_packet else []
selected_model_ids = memory_packet.selected_model_ids if memory_packet else []
predictions = inference_packet.predictions if inference_packet else []
missing_slots = (grounded_graph.missing_slots if grounded_graph else
                 kernel.goal.missing_slots if kernel.goal else [])
required_slots = list(kernel.goal.required_slots) if kernel.goal else []
```

- [ ] **Step 4: Replace all return DecisionPacket(...) with ActionPlan-bearing canonical type**

Each return site changes from:
```python
return DecisionPacket(
    action_kind=ActionKind.ANSWER,
    confidence=...,
    reason=...,
    selected_claim_ids=...,
    selected_model_ids=...,
)
```
to:
```python
return DecisionPacket(
    action_kind="answer",
    action_plan=ActionPlan(
        action_kind="answer",
        selected_claim_ids=selected_claim_ids,
        selected_model_ids=selected_model_ids,
        required_slots=required_slots,
        missing_slots=missing_slots,
        execution_allowed=True,
        confidence=...,
        risk=0.0,
    ),
    confidence=...,
    reason=...,
)
```

Same pattern for "ask" and "abstain" return sites.

- [ ] **Step 5: Commit**

```bash
git add kernel/decision_router.py
git commit -m "feat: DecisionRouter uses canonical DecisionPacket with ActionPlan"
```

---

### Task 6: __main__.py wires InferencePacket and action_kind translation

**Files:**
- Modify: `__main__.py`

- [ ] **Step 1: Import InferencePacket**

Add to the imports section:
```python
from .types.packets import InferencePacket
```

- [ ] **Step 2: Extract grounded_graph and memory_packet from pipeline_result**

After line 206 (`selected_model_ids = pipeline_result.ranked_model_ids`), add:
```python
grounded_graph = pipeline_result.grounded_graph
memory_packet = pipeline_result.memory_packet
```

- [ ] **Step 3: CausalInference returns InferencePacket; extract predictions**

Change lines 251-253 from:
```python
if graph and (graph.causal_edges or kernel.goal.required_slots):
    causal = CausalInference(store)
    predictions = causal.predict(text, selected_claim_ids, kernel)
```
to:
```python
inference_packet = InferencePacket()
if graph and (graph.causal_edges or kernel.goal.required_slots):
    causal = CausalInference(store)
    inference_packet = causal.predict(text, selected_claim_ids, kernel)
predictions = inference_packet.predictions
```

- [ ] **Step 4: Update DecisionRouter call to pass packets**

Change lines 266-272 from:
```python
decision = decision_router.run(
    graph=pipeline_result.semantic_event_graph,
    kernel=kernel,
    selected_claim_ids=selected_claim_ids,
    selected_model_ids=selected_model_ids,
    predictions=predictions if predictions else None,
)
```
to:
```python
decision = decision_router.run(
    graph=pipeline_result.semantic_event_graph,
    kernel=kernel,
    grounded_graph=grounded_graph,
    memory_packet=memory_packet,
    inference_packet=inference_packet if inference_packet.predictions else None,
)
```

- [ ] **Step 5: Translate action_kind str to ActionKind enum**

After line 273, replace:
```python
if decision.confidence >= _ACTION_CONFIDENCE_THRESHOLD and decision.action_kind != ActionKind.ABSTAIN:
    kind = decision.action_kind
```
with:
```python
_action_kind_map = {
    "answer": ActionKind.ANSWER,
    "ask": ActionKind.ASK,
    "remember": ActionKind.REMEMBER,
    "update": ActionKind.UPDATE_CLAIM,
    "act": ActionKind.CALL_TOOL,
    "abstain": ActionKind.ABSTAIN,
}
if decision.confidence >= _ACTION_CONFIDENCE_THRESHOLD and decision.action_kind != "abstain":
    kind = _action_kind_map.get(decision.action_kind)
```

- [ ] **Step 6: Use ActionPlan fields for params**

Change lines 275-281 from reading `decision.selected_claim_ids` to reading from `decision.action_plan`:
```python
if kind == ActionKind.ASK:
    params = {"question": "Could you elaborate?"}
elif kind == ActionKind.ANSWER:
    ap = decision.action_plan
    params = {
        "answer_text": "",
        "selected_claim_ids": list(ap.selected_claim_ids) if ap else selected_claim_ids,
    }
```

- [ ] **Step 7: Commit**

```bash
git add __main__.py
git commit -m "feat: __main__.py wires InferencePacket and translates action_kind"
```

---

### Task 7: Update packet schemas

**Files:**
- Modify: `types/packet_schemas.py`

- [ ] **Step 1: Update DecisionPacket schema to include action_plan**

In `types/packet_schemas.py`, update the `decision_packet` schema:
```python
"decision_packet": {
    "type": "object",
    "required": ["action_kind"],
    "properties": {
        "action_kind": {
            "type": "string",
            "enum": ["answer", "ask", "remember", "update", "act", "abstain"],
        },
        "semantic_answer_graph_id": {"type": "string"},
        "action_plan": {
            "type": "object",
            "properties": {
                "action_kind": {"type": "string"},
                "required_slots": {"type": "array", "items": {"type": "string"}},
                "missing_slots": {"type": "array", "items": {"type": "string"}},
                "selected_claim_ids": {"type": "array", "items": {"type": "string"}},
                "selected_model_ids": {"type": "array", "items": {"type": "string"}},
                "tool_id": {"type": "string"},
                "execution_allowed": {"type": "boolean"},
                "confidence": {"type": "number"},
                "risk": {"type": "number"},
            },
        },
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "reason": {"type": "string"},
        "version": {"type": "string", "pattern": "^cemm\\.decision_packet\\.v1$"},
    },
},
```

- [ ] **Step 2: Commit**

```bash
git add types/packet_schemas.py
git commit -m "feat: update DecisionPacket schema with action_plan"
```

---

### Task 8: Tests

**Files:**
- Create: `tests/test_packets.py`

- [ ] **Step 1: Create test file with test fixtures**

```python
import sys; sys.path.insert(0, "C:\\dev\\cemm")
import pytest
import uuid
from cemm.types.packets import (
    GroundedGraph, MemoryPacket, InferencePacket, DecisionPacket,
    ActionPlan, RankingTraceEntry,
)
from cemm.types.semantic_event_graph import SemanticEventGraph, SemanticEdge
from cemm.types.context_kernel import ContextKernel, TimeState, GoalState, MemoryState, Budget, Permission as KernelPermission
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.permission import Permission
from cemm.kernel.grounding import GroundingPipeline
from cemm.kernel.entity_resolver import EntityResolver
from cemm.kernel.frame_engine import FrameEngine
from cemm.kernel.decision_router import DecisionRouter
from cemm.causal.inference import CausalInference
from unittest.mock import Mock, MagicMock
import time


# ── fixtures ────────────────────────────────────────────────────


@pytest.fixture
def kernel():
    kernel = ContextKernel(
        id="test_kernel",
        self_state_id="self_main",
        time=TimeState(now=time.time()),
        goal=GoalState(required_slots=["subject"], missing_slots=["subject"]),
        memory=MemoryState(),
        budget=Budget(),
        permission=Permission.public(),
    )
    kernel.user.known = True
    kernel.conversation.session_id = "sess_1"
    return kernel


@pytest.fixture
def seg():
    return SemanticEventGraph(
        id="seg_1",
        source_signal_ids=["sig_1"],
        context_id="ctx_1",
        entity_refs=[{"name": "test_entity"}],
        processes=[{"frame_key": "request_clarification", "confidence": 0.8}],
        states=[],
        temporal_edges=[SemanticEdge(source_id="a", target_id="b", relation="before")],
        causal_edges=[SemanticEdge(source_id="a", target_id="b", relation="causes")],
        confidence=0.7,
    )


# ── Task 2 tests: GroundingPipeline produces GroundedGraph ─────


def test_grounding_produces_grounded_graph(kernel, seg):
    resolver = Mock(spec=EntityResolver)
    frames = Mock(spec=FrameEngine)
    resolver.resolve_self.return_value = None
    resolver.resolve_by_name.return_value = [Mock(id="ent_1", type=Mock(value="CONCEPT"))]
    frames.apply_frame_rules.return_value = []

    pipeline = GroundingPipeline(resolver, frames)
    gg = pipeline.run(seg, kernel)

    assert isinstance(gg, GroundedGraph)
    assert gg.semantic_event_graph_id == "seg_1"
    assert len(gg.entity_ids) > 0


# ── Task 4 tests: CausalInference produces InferencePacket ─────


def test_causal_inference_produces_inference_packet():
    store = Mock(spec="cemm.store.store.Store")
    store.models.find_by_kind.return_value = []
    ci = CausalInference(store)
    kernel = ContextKernel(
        id="test",
        self_state_id="self",
        time=TimeState(now=time.time()),
        budget=Budget(),
        permission=Permission.public(),
    )
    kernel.goal = GoalState()

    result = ci.predict("test event", [], kernel)
    assert isinstance(result, InferencePacket)
    assert hasattr(result, "predictions")


# ── Task 5 tests: DecisionRouter produces canonical DecisionPacket ──


def test_decision_router_produces_canonical_packet(kernel, seg):
    router = DecisionRouter()
    mp = MemoryPacket(selected_claim_ids=["c1"], selected_model_ids=["m1"])
    gg = GroundedGraph(semantic_event_graph_id="seg_1")
    ip = InferencePacket(predictions=[{"predicate": "effect", "confidence": 0.8}])

    dp = router.run(seg, kernel, grounded_graph=gg, memory_packet=mp, inference_packet=ip)
    assert isinstance(dp, DecisionPacket)
    assert isinstance(dp.action_plan, ActionPlan) or dp.action_kind == "abstain"


# ── Canonical type smoke tests ────────────────────────────────


def test_canonical_types_instantiate():
    gg = GroundedGraph(semantic_event_graph_id="gg1")
    mp = MemoryPacket(selected_claim_ids=["c1"])
    ip = InferencePacket(predictions=[{"predicate": "p", "confidence": 0.9}])
    ap = ActionPlan(action_kind="answer", execution_allowed=True)
    dp = DecisionPacket(action_kind="answer", action_plan=ap)
    assert dp.action_plan is not None
    assert dp.action_plan.execution_allowed
    assert dp.action_kind == "answer"
    assert gg.semantic_event_graph_id == "gg1"
    assert "c1" in mp.selected_claim_ids
    assert ip.predictions[0]["predicate"] == "p"
```

- [ ] **Step 2: Run tests**

```bash
cd C:\dev\cemm\cemm
rtk python -m pytest tests/test_packets.py -v
```
Expected: All 4 tests PASS.

- [ ] **Step 3: Fix any failures and re-run until green**

- [ ] **Step 4: Commit**

```bash
git add tests/test_packets.py
git commit -m "test: packet construction unit tests"
```

---

## Self-Review Checklist

- [ ] Spec coverage: Task 1 → Trace/PipelineResult fields; Task 2 → GroundingPipeline; Task 3 → Pipeline MemoryPacket; Task 4 → CausalInference; Task 5 → DecisionRouter; Task 6 → __main__.py; Task 7 → schemas; Task 8 → tests. All spec sections covered.
- [ ] No TBD/TODO/placeholder content remains.
- [ ] Type consistency: DecisionPacket.action_kind is `str` in all tasks; ActionPlan field names match between tasks.
