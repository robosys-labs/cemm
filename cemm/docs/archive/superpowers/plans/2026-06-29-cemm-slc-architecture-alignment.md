# CEMM SLC Architecture Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align current CEMM with the new Semantic Latent Core architecture by making SemanticEventGraph and SemanticAnswerGraph first-class runtime/training packets before learned components are promoted.

**Architecture:** The first pass is Phase 0/Phase 1 compliance: contract tests, graph packets, corrected runtime ordering, graph-backed Decide/Realize boundaries, graph-aware training export, permission/frame/budget invariants, and gated promotion. Deterministic code remains as the cheapest fallback, but it operates over semantic packets instead of raw text routes.

**Tech Stack:** Python 3.11+, stdlib dataclasses, sqlite3, existing pytest suite, existing `cemm` package modules.

---

## File Structure

Create:
- `types/semantic_event_graph.py` - first-class SemanticEventGraph dataclasses.
- `types/semantic_answer_graph.py` - first-class SemanticAnswerGraph dataclasses.
- `kernel/semantic_interpreter.py` - deterministic/model-backed graph construction from Signal + ContextKernel.
- `kernel/grounding.py` - entity/time/frame/permission grounding stage.
- `kernel/decision_router.py` - Decide stage over SemanticEventGraph + selected memory.
- `synthesis/realizer.py` - RealizationPipeline that turns SemanticAnswerGraph into text.
- `tests/test_slc_acceptance.py` - executable version of root `cemm_acceptance_tests.md` Phase 0.
- `tests/invariants/test_slc_contracts.py` - graph/order/permission/budget/training invariants.

Modify:
- `types/__init__.py` - export new graph types.
- `types/trace.py` - include graph ids/packets and realization metadata.
- `types/action.py` - add `decision_packet_id` or decision metadata field.
- `types/model.py` - add `SEMANTIC_ENCODER` and `TEXT_REALIZER` model kinds.
- `store/schema.py` - add graph packet storage or trace graph columns.
- `kernel/pipeline.py` - reorder into explicit stage packets.
- `kernel/recursive_loop.py` - consume child budget by actual child cost.
- `retrieval/structural.py` - accept graph-derived retrieval query.
- `retrieval/ranker.py` - pass real permission/frame validity into scoring.
- `operators/answer.py` - produce SemanticAnswerGraph instead of final text.
- `synthesis/router.py` - make cheapest-first selection mandatory through RealizationPipeline.
- `cemm_runtime_router.py` - either deprecate as bootstrap or align its trace/export with graph packets and corrected ordering.
- `cemm_trainer.py` - add semantic graph/answer/text/latent task prompts and validation.
- `cemm_seed_generator.py` and `cemm_seed_spec.json` - migrate to v2 task set.
- `training/promoter.py` - enforce validation/risk/cost/permission gates before activation.

## Task 1: Add Executable SLC Contract Tests

**Files:**
- Create: `tests/test_slc_acceptance.py`
- Create: `tests/invariants/test_slc_contracts.py`

- [ ] **Step 1: Write failing Phase 0 acceptance tests**

Create `tests/test_slc_acceptance.py`:

```python
import json
import sqlite3

from cemm.cemm_runtime_router import connect, handle_turn, export_training


def test_memory_write_trace_contains_semantic_event_graph(tmp_path):
    db = tmp_path / "runtime.sqlite3"
    conn = connect(db)
    result = handle_turn(conn, "My favorite database is Postgres.", "slc")
    trace = conn.execute(
        "SELECT trace_json FROM traces WHERE id = ?",
        (result["trace_id"],),
    ).fetchone()
    payload = json.loads(trace["trace_json"])
    graph = payload.get("semantic_event_graph")
    assert graph is not None
    assert graph["source_signal_ids"] == [result["signal_id"]]
    assert graph["context_id"] == result["context_id"]
    assert any(p.get("frame_key") == "state_preference" for p in graph["processes"])
    assert graph["permission_scope"] == "local_session"


def test_memory_recall_trace_contains_answer_graph_before_text(tmp_path):
    db = tmp_path / "runtime.sqlite3"
    conn = connect(db)
    handle_turn(conn, "My favorite database is Postgres.", "slc")
    result = handle_turn(conn, "What is my favorite database?", "slc")
    trace = conn.execute(
        "SELECT trace_json FROM traces WHERE id = ?",
        (result["trace_id"],),
    ).fetchone()
    payload = json.loads(trace["trace_json"])
    answer_graph = payload.get("semantic_answer_graph")
    assert answer_graph is not None
    assert answer_graph["intent"] == "answer"
    assert answer_graph["selected_claim_ids"]
    assert payload["response"]
    assert payload["realization"]["source_answer_graph_id"] == answer_graph["id"]


def test_runtime_export_contains_graph_training_tasks(tmp_path):
    db = tmp_path / "runtime.sqlite3"
    out = tmp_path / "runtime_training.jsonl"
    conn = connect(db)
    handle_turn(conn, "My favorite database is Postgres.", "slc")
    count = export_training(conn, out)
    assert count > 0
    task_types = {json.loads(line)["task_type"] for line in out.read_text().splitlines()}
    assert "semantic_graph_extraction" in task_types
    assert "semantic_answer_composition" in task_types
    assert "semantic_text_realization" in task_types
    assert "operator_selection" in task_types
```

- [ ] **Step 2: Write failing invariant tests**

Create `tests/invariants/test_slc_contracts.py`:

```python
from cemm.confidence.scoring import score_claim
from cemm.types.context_kernel import ContextKernel
from cemm.types.permission import Permission


def test_permission_invalid_zeroes_claim_score():
    score = score_claim(
        relevance=1.0,
        trust=1.0,
        confidence=1.0,
        salience=1.0,
        recency=1.0,
        permission_valid=False,
    )
    assert score == 0.0


def test_context_kernel_has_self_state_or_reference():
    kernel = ContextKernel(id="ctx")
    assert hasattr(kernel, "self_state") or hasattr(kernel, "self_state_id")


def test_no_static_i_am_here_fallback(tmp_path):
    from cemm.cemm_runtime_router import connect, handle_turn

    conn = connect(tmp_path / "runtime.sqlite3")
    result = handle_turn(conn, "exit", "slc")
    assert result["response"] != "I am here."
```

- [ ] **Step 3: Run tests and confirm failures**

Run:

```powershell
python -m pytest tests/test_slc_acceptance.py tests/invariants/test_slc_contracts.py -q
```

Expected before implementation: failures for missing graph packets, missing realization metadata, missing graph export task types, missing self state/reference, and static fallback.

## Task 2: Add First-Class Semantic Graph Types

**Files:**
- Create: `types/semantic_event_graph.py`
- Create: `types/semantic_answer_graph.py`
- Modify: `types/__init__.py`
- Modify: `types/trace.py`

- [ ] **Step 1: Add SemanticEventGraph dataclasses**

Create `types/semantic_event_graph.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SemanticEdge:
    source_id: str
    target_id: str
    relation: str
    confidence: float = 0.5
    confidence_type: str = "inferred"


@dataclass
class SemanticEventGraph:
    id: str
    source_signal_ids: list[str]
    context_id: str
    entity_refs: list[dict[str, Any]] = field(default_factory=list)
    processes: list[dict[str, Any]] = field(default_factory=list)
    states: list[dict[str, Any]] = field(default_factory=list)
    claim_refs: list[str] = field(default_factory=list)
    claim_candidates: list[dict[str, Any]] = field(default_factory=list)
    model_refs: list[str] = field(default_factory=list)
    action_refs: list[str] = field(default_factory=list)
    temporal_edges: list[SemanticEdge] = field(default_factory=list)
    causal_edges: list[SemanticEdge] = field(default_factory=list)
    permission_scope: str = "public"
    confidence: float = 0.5
    version: str = "cemm.semantic_event_graph.v1"
```

- [ ] **Step 2: Add SemanticAnswerGraph dataclasses**

Create `types/semantic_answer_graph.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AnswerVerification:
    supported: bool = False
    verification_type: str = "none"
    confidence: float = 0.0
    unsupported_spans: list[str] = field(default_factory=list)
    uncertainty_reason: str = ""


@dataclass
class SemanticAnswerGraph:
    id: str
    intent: str
    source_signal_ids: list[str]
    context_id: str
    selected_claim_ids: list[str] = field(default_factory=list)
    selected_model_ids: list[str] = field(default_factory=list)
    entity_refs: list[dict[str, Any]] = field(default_factory=list)
    processes: list[dict[str, Any]] = field(default_factory=list)
    states: list[dict[str, Any]] = field(default_factory=list)
    causal_edges: list[dict[str, Any]] = field(default_factory=list)
    temporal_edges: list[dict[str, Any]] = field(default_factory=list)
    action_candidates: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.5
    uncertainty_reasons: list[str] = field(default_factory=list)
    permission_scope: str = "public"
    verification: AnswerVerification = field(default_factory=AnswerVerification)
    version: str = "cemm.semantic_answer_graph.v1"
```

- [ ] **Step 3: Export graph types**

Modify `types/__init__.py`:

```python
from .semantic_event_graph import SemanticEdge, SemanticEventGraph
from .semantic_answer_graph import AnswerVerification, SemanticAnswerGraph
```

- [ ] **Step 4: Add graph references to Trace**

Modify `types/trace.py` by adding fields:

```python
semantic_event_graph_id: str | None = None
semantic_answer_graph_id: str | None = None
realization_strategy: str | None = None
realization_verified: bool = False
```

- [ ] **Step 5: Run type/import tests**

Run:

```powershell
python -m pytest tests/test_signal.py tests/test_action.py tests/test_store.py -q
```

Expected after implementation: all selected tests pass.

## Task 3: Correct Basic Runtime Graph Trace And Export

**Files:**
- Modify: `cemm_runtime_router.py`
- Test: `tests/test_slc_acceptance.py`

- [ ] **Step 1: Add graph packet builders with corrected order**

Add functions before `extract_claim()`:

```python
def build_semantic_event_graph(signal_id, context, semantics, claim):
    uol = semantics.get("uol", {})
    uol_atoms = uol.get("uol_atoms", [])
    atom_confidences = [float(atom.get("confidence", 0.0) or 0.0) for atom in uol_atoms]
    claim_confidence = float((claim or {}).get("confidence", 0.0) or 0.0)
    context_confidence = float(semantics.get("context", {}).get("confidence", 0.0) or 0.0)
    return {
        "id": stable_id("seg", {"signal_id": signal_id, "uol": uol_atoms, "claim": claim}),
        "source_signal_ids": [signal_id],
        "context_id": context.id,
        "entity_refs": [a for a in uol_atoms if a.get("kind") == "entity_ref"],
        "processes": [a for a in uol_atoms if a.get("kind") == "process"],
        "states": [a for a in uol_atoms if a.get("kind") == "state"],
        "claim_refs": [],
        "claim_candidates": [claim] if claim else [],
        "model_refs": [],
        "action_refs": [],
        "temporal_edges": [],
        "causal_edges": [],
        "permission_scope": context.permission["scope"],
        "confidence": min(0.95, max(atom_confidences + [claim_confidence, context_confidence, 0.5])),
        "version": "cemm.semantic_event_graph.v1",
    }
```

- [ ] **Step 2: Add answer graph composition before text realization**

Add:

```python
def compose_semantic_answer_graph(conn, signal_id, context, decision, semantic_event_graph):
    claims = selected_claims(conn, decision.selected_claim_ids)
    return {
        "id": stable_id("sag", {"signal_id": signal_id, "decision": dataclasses.asdict(decision)}),
        "intent": decision.action_kind,
        "source_signal_ids": [signal_id],
        "context_id": context.id,
        "selected_claim_ids": decision.selected_claim_ids,
        "selected_model_ids": [],
        "entity_refs": semantic_event_graph.get("entity_refs", []),
        "processes": semantic_event_graph.get("processes", []),
        "states": semantic_event_graph.get("states", []),
        "causal_edges": semantic_event_graph.get("causal_edges", []),
        "temporal_edges": semantic_event_graph.get("temporal_edges", []),
        "action_candidates": [dataclasses.asdict(decision)],
        "selected_claims": claims,
        "confidence": decision.confidence,
        "uncertainty_reasons": [] if decision.confidence >= 0.75 else [decision.reason],
        "permission_scope": context.permission["scope"],
        "verification": {"supported": False, "verification_type": "none", "confidence": 0.0},
        "version": "cemm.semantic_answer_graph.v1",
    }
```

- [ ] **Step 3: Change `synthesize()` signature to realize from answer graph**

Change:

```python
def synthesize(conn, decision, text, context):
```

to:

```python
def synthesize(conn, decision, text, context, semantic_answer_graph):
```

Then include a realization metadata result:

```python
return text_out, {
    "strategy": "template",
    "verified": True,
    "verification_type": "hard",
    "source_answer_graph_id": semantic_answer_graph["id"],
}
```

- [ ] **Step 4: Reorder `handle_turn()`**

Use this order:

```python
context = build_context(conn, session_id)
signal_id = observe(conn, content, context)
normalized = normalize(content)
context_info = infer_context(normalized, context)
uol = map_uol(normalized)
semantics = {"context": context_info, "uol": uol}
claim_candidate = extract_claim(normalized)
semantic_event_graph = build_semantic_event_graph(signal_id, context, semantics, claim_candidate)
decision = route(conn, normalized, context, context_info)
semantic_answer_graph = compose_semantic_answer_graph(conn, signal_id, context, decision, semantic_event_graph)
response, realization = synthesize(conn, decision, normalized, context, semantic_answer_graph)
semantic_answer_graph["verification"] = {
    "supported": bool(realization.get("verified")),
    "verification_type": realization.get("verification_type", "none"),
    "confidence": 1.0 if realization.get("verified") else 0.0,
}
```

- [ ] **Step 5: Add graph fields to trace**

Extend `write_action_trace()` parameters and trace dict:

```python
"semantic_event_graph": semantic_event_graph,
"semantic_answer_graph": semantic_answer_graph,
"realization": realization,
```

- [ ] **Step 6: Add graph tasks to runtime export**

In `runtime_training_examples()`, add:

```python
examples.append({"task_type": "semantic_graph_extraction", "permission_scope": permission_scope, "payload": payload_base})
examples.append({"task_type": "semantic_latent_target", "permission_scope": permission_scope, "payload": payload_base})
examples.append({"task_type": "semantic_answer_composition", "permission_scope": permission_scope, "payload": payload_base})
examples.append({"task_type": "semantic_text_realization", "permission_scope": permission_scope, "payload": payload_base})
```

- [ ] **Step 7: Run acceptance tests**

Run:

```powershell
python -m pytest tests/test_slc_acceptance.py -q
```

Expected after implementation: all Task 1 acceptance tests pass.

## Task 4: Align Package Pipeline Stage Ordering

**Files:**
- Create: `kernel/semantic_interpreter.py`
- Create: `kernel/grounding.py`
- Modify: `kernel/pipeline.py`
- Modify: `kernel/context_kernel_builder.py`
- Test: `tests/invariants/test_slc_contracts.py`

- [ ] **Step 1: Add SemanticInterpreter**

Create `kernel/semantic_interpreter.py`:

```python
from __future__ import annotations

import uuid

from ..registry.uol_mapper import UOLMapper
from ..types.semantic_event_graph import SemanticEventGraph
from ..types.signal import Signal
from ..types.context_kernel import ContextKernel


class SemanticInterpreter:
    def __init__(self, uol_mapper: UOLMapper) -> None:
        self._uol_mapper = uol_mapper

    def run(self, signal: Signal, kernel: ContextKernel) -> SemanticEventGraph:
        atoms = self._uol_mapper.map_signal(signal.content, kernel)
        return SemanticEventGraph(
            id=uuid.uuid4().hex[:16],
            source_signal_ids=[signal.id],
            context_id=kernel.id,
            entity_refs=[a.__dict__ for a in atoms if getattr(a, "kind", "") == "entity_ref"],
            processes=[a.__dict__ for a in atoms if getattr(a, "kind", "") == "process"],
            states=[a.__dict__ for a in atoms if getattr(a, "kind", "") == "state"],
            permission_scope=kernel.permission.scope.value,
            confidence=max([getattr(a, "confidence", 0.0) for a in atoms], default=0.5),
        )
```

- [ ] **Step 2: Add GroundingPipeline skeleton**

Create `kernel/grounding.py`:

```python
from __future__ import annotations

from ..types.context_kernel import ContextKernel
from ..types.semantic_event_graph import SemanticEventGraph
from .entity_resolver import EntityResolver
from .frame_engine import FrameEngine


class GroundingPipeline:
    def __init__(self, resolver: EntityResolver, frames: FrameEngine) -> None:
        self._resolver = resolver
        self._frames = frames

    def run(self, graph: SemanticEventGraph, kernel: ContextKernel) -> SemanticEventGraph:
        self._resolver.resolve_self(kernel)
        self._frames.apply_frame_rules(kernel)
        return graph
```

- [ ] **Step 3: Reorder `Pipeline.run()`**

Change ordering to:

```text
observe signal
build kernel
infer context
interpret signal into SemanticEventGraph
ground graph/kernel
retrieve graph-grounded memory
rank
attach graph to result
```

In code, move interpretation before retrieval/ranking and add `semantic_event_graph` to `PipelineResult`.

- [ ] **Step 4: Keep raw signal content stable**

Replace:

```python
signal.content = self._normalizer.normalize_predicate(signal.content)
```

with a separate local:

```python
normalized_content = self._normalizer.normalize_predicate(signal.content)
```

Use normalized content for registry lookup only; do not mutate stored signal content.

- [ ] **Step 5: Run pipeline tests**

Run:

```powershell
python -m pytest tests/test_pipeline.py tests/test_uol_mapper.py tests/test_pragmatic.py -q
```

Expected after implementation: tests pass and new stage-order assertions pass.

## Task 5: Add DecisionRouter And Stop Text-Only Action Selection

**Files:**
- Create: `kernel/decision_router.py`
- Modify: `__main__.py`
- Modify: `types/action.py`
- Test: `tests/invariants/test_slc_contracts.py`

- [ ] **Step 1: Add DecisionPacket and DecisionRouter**

Create `kernel/decision_router.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field

from ..types.action import ActionKind
from ..types.context_kernel import ContextKernel
from ..types.semantic_event_graph import SemanticEventGraph


@dataclass
class DecisionPacket:
    action_kind: ActionKind
    confidence: float
    reason: str
    selected_claim_ids: list[str] = field(default_factory=list)
    selected_model_ids: list[str] = field(default_factory=list)
    required_slots: list[str] = field(default_factory=list)
    missing_slots: list[str] = field(default_factory=list)


class DecisionRouter:
    def run(
        self,
        graph: SemanticEventGraph,
        kernel: ContextKernel,
        selected_claim_ids: list[str],
        selected_model_ids: list[str],
    ) -> DecisionPacket:
        if kernel.goal.missing_slots:
            return DecisionPacket(
                action_kind=ActionKind.ASK,
                confidence=0.9,
                reason="missing required slots",
                required_slots=kernel.goal.required_slots,
                missing_slots=kernel.goal.missing_slots,
            )
        if selected_claim_ids:
            return DecisionPacket(
                action_kind=ActionKind.ANSWER,
                confidence=0.8,
                reason="selected evidence available",
                selected_claim_ids=selected_claim_ids,
                selected_model_ids=selected_model_ids,
            )
        return DecisionPacket(
            action_kind=ActionKind.ABSTAIN,
            confidence=0.6,
            reason="insufficient graph-grounded evidence",
            selected_model_ids=selected_model_ids,
        )
```

- [ ] **Step 2: Route `__main__.py` through DecisionRouter**

In `process_input()`, remove the hardcoded `startswith()`/`?` action selection block and call `DecisionRouter.run()` using `pipeline_result.semantic_event_graph`.

- [ ] **Step 3: Run CLI behavior probes**

Run:

```powershell
python -m cemm --once "What is my favorite database?"
python cemm_runtime_router.py --db demo_runtime.sqlite3 --session-id plan once "who is the president?" --json
```

Expected: no direct raw-text answer path for unsupported evidence; fresh-world still abstains when tools are disabled.

## Task 6: Move Text Behind RealizationPipeline

**Files:**
- Create: `synthesis/realizer.py`
- Modify: `operators/answer.py`
- Modify: `operators/synthesize.py`
- Modify: `synthesis/router.py`
- Test: `tests/invariants/test_synthesis.py`

- [ ] **Step 1: Add RealizationPipeline**

Create `synthesis/realizer.py`:

```python
from __future__ import annotations

from ..registry import Registry
from ..store.store import Store
from ..types.context_kernel import ContextKernel
from ..types.semantic_answer_graph import SemanticAnswerGraph
from .router import SynthesisRouter
from .result import SynthesisResult


class RealizationPipeline:
    def __init__(self, router: SynthesisRouter | None = None) -> None:
        self._router = router or SynthesisRouter()

    def run(
        self,
        answer_graph: SemanticAnswerGraph,
        kernel: ContextKernel,
        store: Store,
        registry: Registry,
    ) -> SynthesisResult:
        params = {
            "selected_claim_ids": answer_graph.selected_claim_ids,
            "selected_model_ids": answer_graph.selected_model_ids,
            "answer_graph": answer_graph,
        }
        strategy = self._router.select_strategy(kernel, store, registry, params)
        result = self._router.route(strategy, kernel, store, registry, params)
        result.metadata["source_answer_graph_id"] = answer_graph.id
        return result
```

- [ ] **Step 2: Make answer operator construct graph**

Modify `operators/answer.py` so selected claims produce a `SemanticAnswerGraph` and then call `RealizationPipeline.run()`. Direct `answer_text` should be allowed only for `ASK`/`ABSTAIN` templates or tests explicitly marked as legacy.

- [ ] **Step 3: Make SynthesisRouter cheapest-first mandatory**

Add a new public method:

```python
def realize(self, kernel, store, registry, params):
    strategy = self.select_strategy(kernel, store, registry, params)
    return self.route(strategy, kernel, store, registry, params)
```

Replace production calls to `route("template", ...)` with `realize(...)`.

- [ ] **Step 4: Run synthesis tests**

Run:

```powershell
python -m pytest tests/invariants/test_synthesis.py tests/test_e2e_phase2.py -q
```

Expected after implementation: synthesis still selects template/extractive first and every answer result includes source answer graph id.

## Task 7: Upgrade Training Pipeline To V2 Semantic Tasks

**Files:**
- Modify: `cemm_trainer.py`
- Modify: `cemm_seed_generator.py`
- Modify: `cemm_seed_spec.json`
- Test: `tests/test_continuous_training.py`

- [ ] **Step 1: Add v2 task prompts**

Use the archived SLC snapshot at `docs\archive\new-slc-snapshot-2026-06-29\cemm_trainer.py` as a reference for these prompt names:

```python
"semantic_graph_extraction"
"semantic_graph_denoising"
"semantic_latent_target"
"semantic_answer_composition"
"semantic_text_realization"
"next_event_prediction"
"causal_effect_prediction"
"memory_retrieval_ranking"
```

- [ ] **Step 2: Add payload validation**

Add:

```python
GRAPH_REQUIRED_TASKS = {
    "semantic_answer_composition",
    "semantic_text_realization",
    "operator_selection",
}

def validate_training_record(task_type: str, payload: dict) -> None:
    if "context_kernel" not in payload:
        raise ValueError(f"{task_type}: missing ContextKernel")
    if task_type in GRAPH_REQUIRED_TASKS and "semantic_event_graph" not in payload:
        raise ValueError(f"{task_type}: missing SemanticEventGraph")
    if task_type == "semantic_text_realization" and "semantic_answer_graph" not in payload:
        raise ValueError("semantic_text_realization: missing SemanticAnswerGraph")
```

Call this from `ingest_jsonl()` before inserting jobs.

- [ ] **Step 3: Replace seed spec with v2**

Ensure root `cemm_seed_spec.json` contains the v2 SLC categories already promoted from the SLC snapshot.

- [ ] **Step 4: Update seed generator task allow-list**

Use `docs\archive\new-slc-snapshot-2026-06-29\cemm_seed_generator.py` as a reference for the task allow-list and dry-run payload branches for semantic graph/answer/text tasks.

- [ ] **Step 5: Run training tests**

Run:

```powershell
python -m pytest tests/test_continuous_training.py tests/test_training_arbiter.py tests/test_training_evaluator.py tests/test_training_promoter.py -q
```

Expected after implementation: old continuous-training tests pass and new semantic task ingestion tests pass.

## Task 8: Enforce Permission, Frame, Budget, And Promotion Invariants

**Files:**
- Modify: `retrieval/ranker.py`
- Modify: `confidence/scoring.py`
- Modify: `kernel/recursive_loop.py`
- Modify: `training/promoter.py`
- Modify: `learning/promotion.py`
- Test: `tests/invariants/test_slc_contracts.py`

- [ ] **Step 1: Pass real permission validity into scoring**

In `Ranker.rank_claims()`:

```python
permission_valid = self._claim_permitted(claim, kernel)
if not permission_valid:
    continue
s = score_claim(..., permission_valid=permission_valid)
```

In `Ranker.rank_models()`:

```python
permission_valid = self._model_permitted(model, kernel)
if not permission_valid:
    continue
s = score_model(..., permission_valid=permission_valid)
```

- [ ] **Step 2: Add frame validity scoring input**

Add `frame_validity: float = 1.0` to `score_claim()` and multiply score by it:

```python
return relevance * trust * confidence * effective_salience * recency * pv * frame_validity - contradiction_penalty
```

- [ ] **Step 3: Consume child recursive cost**

In `RecursiveLoop.run_once()`, after `sub_result = self._pipeline.run(...)`, subtract child cost:

```python
remaining_latency -= sub_result.cost_ms
```

Also append budget telemetry to an internal signal or trace metadata.

- [ ] **Step 4: Gate promotion**

Change `training/promoter.py::approve()` to require score and eval metadata:

```python
if not self._candidate_has_passing_eval(candidate_id):
    return False
if not self._candidate_permission_safe(model_id):
    return False
if not self._candidate_risk_acceptable(model_id):
    return False
```

Implement helper methods with concrete SQL checks against `eval_results`, `models.permission_scope`, and `models.risk`.

- [ ] **Step 5: Run invariant tests**

Run:

```powershell
python -m pytest tests/invariants -q
```

Expected after implementation: invariants pass, including new graph/order/permission/budget/promotion tests.

## Task 9: Resolve Runtime Duplication

**Files:**
- Modify: `cemm_runtime_router.py`
- Modify: `__main__.py`
- Modify: `cemm_pipeline.md`
- Test: `tests/test_slc_acceptance.py`

- [ ] **Step 1: Choose package runtime as canonical**

Document in `cemm_pipeline.md`:

```text
Canonical runtime: python -m cemm --chat / --once
Bootstrap compatibility runtime: cemm_runtime_router.py
Both must emit SemanticEventGraph, SemanticAnswerGraph, realization metadata, and runtime training export.
```

- [ ] **Step 2: Make `cemm_runtime_router.py chat` handle exit safely**

In chat loop:

```python
if text.lower() in {"exit", "quit", "bye"}:
    print("Goodbye.")
    break
```

- [ ] **Step 3: Route package and bootstrap through same graph/export tests**

Add acceptance tests that call both `python -m cemm --once` and `cemm_runtime_router.py once --json` for the same memory write/recall scenario.

- [ ] **Step 4: Run full suite**

Run:

```powershell
python -m pytest tests --tb=short -q
```

Expected: all tests pass.

## Self-Review Checklist

- Spec coverage:
  - Architecture Sections 1-29 map to Tasks 1-9.
  - Training Architecture Sections 1-18 map to Tasks 7-8.
  - Pipeline regression gates map to Tasks 1, 3, 6, 7, 8.
  - Acceptance tests map to Task 1 and Task 9.
- Placeholder scan:
  - No placeholder-marker instructions are present.
  - Every code-changing task names exact files and test commands.
- Type consistency:
  - `SemanticEventGraph`, `SemanticAnswerGraph`, `AnswerVerification`, and `DecisionPacket` names are used consistently across tasks.
  - Runtime trace field names are consistently `semantic_event_graph`, `semantic_answer_graph`, and `realization`.

## Execution Order

1. Task 1: contract tests.
2. Task 2: graph types.
3. Task 3: basic runtime graph trace/export.
4. Task 4: package pipeline ordering.
5. Task 5: DecisionRouter.
6. Task 6: RealizationPipeline.
7. Task 7: training v2 tasks.
8. Task 8: invariants.
9. Task 9: runtime duplication cleanup.

Stop after Task 3 for a Phase 0 checkpoint if you want a smaller first PR.
