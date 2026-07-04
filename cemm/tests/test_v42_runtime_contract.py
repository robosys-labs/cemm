"""v4.2 runtime contract tests.

Verifies architecture invariants after Phase 0-7:
- UOLGraph sole working graph (no backward-compat properties)
- PipelineResult stores UOLGraph directly
- Native UOLGraph API works for all consumer patterns
"""

from unittest.mock import MagicMock

from cemm.types.uol_graph import UOLGraph
from cemm.kernel.semantic_kernel_runtime import SemanticKernelRuntime


def test_uolgraph_has_no_backward_compat_properties() -> None:
    g = UOLGraph(id="g1", signal_id="sig1")
    assert not hasattr(g, "processes")
    assert not hasattr(g, "states")
    assert not hasattr(g, "entity_refs")
    assert not hasattr(g, "causal_edges")
    assert not hasattr(g, "temporal_edges")
    assert not hasattr(g, "source_signal_ids")
    assert not hasattr(g, "confidence")


def test_uolgraph_native_api_works() -> None:
    g = UOLGraph(id="g1", signal_id="sig1")
    e1 = g.add_atom("entity", "user", surface="Alice")
    p1 = g.add_atom("process", "greet", surface="greeting")
    s1 = g.add_atom("state", "happy", surface="happy")
    g.add_edge("causes", p1.id, s1.id)

    entities = [a for a in g.atoms.values() if a.kind == "entity"]
    assert len(entities) == 1
    assert entities[0].surface == "Alice"

    causes = g.edges_by_type("causes")
    assert len(causes) == 1

    sig_ids = [g.signal_id] if g.signal_id else []
    assert sig_ids == ["sig1"]

    conf = max((a.confidence for a in g.atoms.values()), default=0.5)
    assert conf == 0.5

    process_keys = {a.key.replace("process:", "").replace("state:", "")
                    for a in g.atoms.values() if a.kind in ("process", "state")}
    assert "greet" in process_keys


def test_uolgraph_sole_working_graph_in_pipeline_result() -> None:
    from cemm.kernel.pipeline import PipelineResult
    assert "uol_graph" in PipelineResult.__dataclass_fields__
    assert "semantic_event_graph" not in PipelineResult.__dataclass_fields__


def test_runtime_cycle_result_stages() -> None:
    from unittest.mock import MagicMock
    from cemm.types.runtime_cycle import RuntimeCycleResult
    r = RuntimeCycleResult(
        signal=MagicMock(),
        context_kernel=MagicMock(),
        uol_graph=UOLGraph(id="g1"),
        cost_ms=0.0,
    )
    assert r.uol_graph is not None
    assert r.uol_graph.id == "g1"
    assert r.cost_ms == 0.0
    assert len(r.patch_candidates) == 0


def test_semantic_kernel_runtime_has_attention() -> None:
    store = MagicMock()
    reg = MagicMock()
    rt = SemanticKernelRuntime(store, reg)
    assert hasattr(rt, "attention")


def test_pipelineresult_uses_uolgraph() -> None:
    from cemm.kernel.pipeline import PipelineResult
    pr = PipelineResult(uol_graph=UOLGraph(id="test"))
    assert pr.uol_graph is not None
    assert pr.uol_graph.id == "test"


def test_entity_refs_access_pattern_works() -> None:
    g = UOLGraph(id="g1")
    g.add_atom("entity", "user", surface="Alice")
    g.add_atom("entity", "bob", surface="Bob")
    g.add_atom("self", "ce-mm", surface="CEMM")

    entity_ids = {a.key.replace("entity:", "").replace("self:", "")
                  for a in g.atoms.values() if a.kind in ("entity", "self")}
    assert "user" in entity_ids
    assert "bob" in entity_ids
    assert "ce-mm" in entity_ids


def test_frame_key_access_pattern_works() -> None:
    g = UOLGraph(id="g1")
    g.add_atom("process", "request_clarification")
    g.add_atom("state", "user_waiting")
    frame_keys = {a.key.replace("process:", "").replace("state:", "")
                  for a in g.atoms.values() if a.kind in ("process", "state")}
    assert "request_clarification" in frame_keys
    assert "user_waiting" in frame_keys
