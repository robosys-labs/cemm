from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from cemm.kernel.meaning_perceptor import MeaningPerceptor
from cemm.learning.ner_tagger import NERTagger
from cemm.learning.surface_tagger import SurfaceTagger
from cemm.types.context_kernel import ContextKernel
from cemm.types.permission import Permission
from cemm.types.signal import Signal, SignalKind, SourceType


def _make_signal(text: str) -> Signal:
    return Signal(
        id=uuid.uuid4().hex[:16],
        kind=SignalKind.INPUT,
        source_id="user",
        source_type=SourceType.USER,
        content=text,
        observed_at=time.time(),
        context_id="semantic_core_loop_test",
        salience=0.8,
        trust=0.8,
        permission=Permission.public(),
    )


def _make_perceptor() -> MeaningPerceptor:
    ner = NERTagger()
    vocab_path = Path(__file__).parent.parent / "data" / "vocab.json"
    known_words: set[str] = set()
    if vocab_path.exists():
        data = json.loads(vocab_path.read_text(encoding="utf-8"))
        known_words = set(data.get("known_words", []))
    return MeaningPerceptor(ner_tagger=ner, surface_tagger=SurfaceTagger(ner, known_words=known_words))


def test_semantic_kernel_runtime_produces_cycle_result() -> None:
    from cemm.kernel.semantic_kernel_runtime import SemanticKernelRuntime

    result = SemanticKernelRuntime().run_turn(
        _make_signal("hello"), ContextKernel(id="ctx_cpu"),
    )

    assert result.percept is not None
    assert result.percept.uol_graph is not None
    assert result.act_plan is not None


def test_working_graph_promotes_discourse_and_anaphora_to_edges() -> None:
    packet = _make_perceptor().perceive(
        _make_signal("Alice stayed home because she was cold"),
        ContextKernel(id="ctx_graph"),
    )
    graph = packet.uol_graph

    assert graph is not None
    assert any(
        edge.edge_type == "causes"
        and edge.features.get("discourse_relation") == "cause"
        for edge in graph.edges
    )
    assert any(
        edge.edge_type == "refers_to"
        and edge.features.get("anaphoric")
        and graph.atoms[edge.source_id].key == "she"
        and graph.atoms[edge.target_id].key == "alice"
        for edge in graph.edges
    )


def test_phatic_checkin_not_classified_as_teaching() -> None:
    perceptor = _make_perceptor()
    signal = _make_signal("I'm good lol, how are you")
    packet = perceptor.perceive(signal, ContextKernel(id="ctx_phatic"))
    groups = packet.meaning_groups

    assert len(groups) >= 2, (
        f"Expected at least 2 groups for 'I\\'m good lol, how are you', got {len(groups)}: "
        f"{[(g.surface, g.group_type) for g in groups]}"
    )
    second = groups[-1]
    assert second.group_type == "question", (
        f"Expected second group 'how are you' to be 'question', got '{second.group_type}'"
    )
    assert second.confidence >= 0.55


def test_initial_group_type_teaching_requires_guard() -> None:
    perceptor = _make_perceptor()
    signal = _make_signal("my name is Opata")
    packet = perceptor.perceive(signal, ContextKernel(id="ctx_teach"))
    groups = packet.meaning_groups

    assert len(groups) >= 1
    group = groups[0]
    assert group.group_type == "teaching", (
        f"Expected 'my name is Opata' to be 'teaching', got '{group.group_type}'"
    )
