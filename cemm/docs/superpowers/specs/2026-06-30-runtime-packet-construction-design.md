# Runtime Packet Construction

**Date:** 2026-06-30
**Status:** Design (approved)
**References:** architecture.md §10.1.2, AGENTS.md, cemm_original_work_subplans.md §5

## Problem

The SLC runtime produces rich intermediate data at each pipeline stage, but packets
(GroundedGraph, MemoryPacket, InferencePacket, DecisionPacket) are currently ad-hoc dicts,
side effects on ContextKernel fields, or local-scope structures that never get captured as
typed packets. This violates the export and training invariants in architecture.md §27.

## Scope

Full refactor: each pipeline stage constructs a typed packet as its final step.

## Component Changes

### 1. GroundingPipeline: returns GroundedGraph

```python
# Before:
def run(self, graph: SemanticEventGraph, kernel: ContextKernel) -> SemanticEventGraph:
    # mutates graph.entity_refs[*]["entity_id"] in-place
    # mutates graph.permission_scope
    return graph

# After:
def run(self, graph: SemanticEventGraph, kernel: ContextKernel) -> GroundedGraph:
    # same entity resolution and frame engine logic
    # returns typed GroundedGraph with resolved entity_ids, active_frame_ids, missing_slots
```

Existing SEG mutation is removed — entity resolution results live in the GroundedGraph
packet, not in the SEG dicts. The SEG is read-only after grounding.

### 2. CausalInference: returns InferencePacket

```python
# Before:
def predict(self, action_or_event, active_claim_ids, kernel) -> list[dict]:
    return [{"model_id": ..., "predicate": ..., "confidence": ...}, ...]

# After:
def predict(self, action_or_event, active_claim_ids, kernel) -> InferencePacket:
    # same matching logic
    # returns typed InferencePacket with implications/contradictions/predictions
```

### 3. DecisionRouter: returns canonical DecisionPacket

```python
# Before:
# kernel/decision_router.py defines its own DecisionPacket dataclass
def run(...) -> DecisionPacket:  # local type

# After:
# uses types/packets.DecisionPacket (canonical)
def run(...) -> DecisionPacket:  # canonical type, with ActionPlan
```

The ActionPlan carries selected_claim_ids, selected_model_ids, required_slots,
missing_slots, execution_allowed, risk, confidence. The semantic_answer_graph_id
on DecisionPacket is populated later by AnswerOperator.

### 4. PipelineResult: carries new packets

New fields:
- `grounded_graph: GroundedGraph | None`
- `memory_packet: MemoryPacket | None`

MemoryPacket is constructed after ranking: wraps ranked claim IDs, model IDs, and
ranking trace (candidate_id, score, reason) into a typed packet.

### 5. Trace: references packet IDs

New optional fields:
- `grounded_graph_id: str | None`
- `memory_packet_id: str | None`
- `inference_packet_id: str | None`

## Data Flow

```
Pipeline.run():
  signal -> ContextKernel -> SemanticEventGraph
  -> GroundingPipeline -> GroundedGraph
  -> ContextInferenceEngine -> (applied to kernel, no new packet)
  -> retrieval + ranker -> MemoryPacket
  -> PipelineResult(kernel, SEG, GG, MP, ranked IDs)

process_input():
  PipelineResult
  -> CausalInference.predict() -> InferencePacket
  -> DecisionRouter.run(graph, kernel, GG, MP, IP) -> DecisionPacket (with ActionPlan)
  -> OperatorRegistry.execute() -> OperatorResult (unchanged)
  -> Trace populated from all packet IDs
```

No stage reads back from a packet produced earlier in the same turn. The data was
already available on the kernel/SEG. This makes the change zero-risk to existing logic.

## Dual DecisionPacket Resolution

| Field | kernel/decision_router.py | types/packets.py (keeper) |
|-------|--------------------------|--------------------------|
| action_kind | ActionKind enum | str → ActionPlan |
| ActionPlan | selected_claim_ids, selected_model_ids, required_slots, missing_slots | execution_allowed, risk, tool_id, confidence |
| semantic_answer_graph_id | — | str or None |

Merge: ActionPlan absorbs all fields from the kernel version (selected_claim_ids,
selected_model_ids, required_slots, missing_slots) in addition to its own.
DecisionPacket uses str action_kind; translation to ActionKind enum happens at
the dispatch boundary in __main__.py.

## Files to Modify

| File | Change |
|------|--------|
| `kernel/grounding.py` | Return GroundedGraph instead of mutating SEG |
| `kernel/decision_router.py` | Remove local DecisionPacket; import canonical; add ActionPlan construction |
| `kernel/pipeline.py` | Construct MemoryPacket after ranking; add GG/MP to PipelineResult |
| `__main__.py` | Build InferencePacket; translate action_kind str→ActionKind |
| `types/packets.py` | Add missing fields to DecisionPacket/ActionPlan if needed |
| `types/trace.py` | Add optional packet ID fields |
| `types/packet_schemas.py` | Update DecisionPacket schema to match merged type |
| `causal/inference.py` | Return InferencePacket instead of list[dict] |

## Testing

- `test_grounding_produces_grounded_graph`: run GroundingPipeline, verify typed GroundedGraph
- `test_causal_inference_produces_inference_packet`: seeded models, verify InferencePacket
- `test_decision_router_produces_canonical_packet`: verify types.packets.DecisionPacket + ActionPlan
- `test_pipeline_result_carries_packets`: full Pipeline.run(), verify GG + MP populated
- `test_action_kind_translation`: verify str action_kind maps to correct ActionKind

All tests pure deterministic/structural — no LLM calls needed.
