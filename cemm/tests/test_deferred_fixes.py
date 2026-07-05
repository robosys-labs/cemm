"""Tests for deferred foundational fixes implementation.

Covers:
- D1: OutcomeAtom enriched fields (event_key, state_changes, relation_changes, resource_changes)
- D2/D3: SemanticInterpreter consumes MeaningPerceptPacket + SituationFrame
- D4: Event schema entries in uol_semantics.json (action_schema, state_schema, etc.)
- EventSchemaStore loader and lookup
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ["CEMM_EXPORT_PATH"] = ""

from cemm.store.store import Store
from cemm.registry import Registry
from cemm.kernel.pipeline import Pipeline
from cemm.kernel.event_schema_loader import load_event_schemas, EventSchemaStore
from cemm.types.meaning_percept import (
    OutcomeAtom,
    MeaningPerceptPacket,
    SituationFrame,
    ReferentAtom,
    ActionAtom,
)
from cemm.kernel.semantic_interpreter import SemanticInterpreter
from cemm.kernel.situation_frame_builder import SituationFrameBuilder
from cemm.kernel.safety_frame_detector import SafetyFrameDetector
from cemm.registry.uol_mapper import UOLMapper
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.permission import Permission
import time
import uuid


def _make_signal(text: str) -> Signal:
    return Signal(
        id=uuid.uuid4().hex[:16],
        kind=SignalKind.INPUT,
        source_id="test",
        source_type=SourceType.USER,
        content=text,
        observed_at=time.time(),
        context_id=uuid.uuid4().hex[:16],
        salience=0.8,
        trust=0.8,
        permission=Permission.public(),
    )


def _make_store() -> Store:
    return Store(":memory:")


def _make_registry() -> Registry:
    return Registry()


# ── D1: OutcomeAtom enriched fields ───────────────────────────────────

def test_outcome_atom_has_event_key() -> None:
    o = OutcomeAtom(
        affected_entity_role="target",
        changed_dimension="health",
        direction="decrease",
        event_key="physically_harm_target",
    )
    assert o.event_key == "physically_harm_target"


def test_outcome_atom_has_state_changes() -> None:
    o = OutcomeAtom(
        affected_entity_role="target",
        changed_dimension="health",
        direction="decrease",
        state_changes=[{"dimension": "health", "direction": "decrease"}],
    )
    assert len(o.state_changes) == 1
    assert o.state_changes[0]["dimension"] == "health"


def test_outcome_atom_has_resource_changes() -> None:
    o = OutcomeAtom(
        affected_entity_role="recipient",
        changed_dimension="possession",
        direction="increase",
        resource_changes=[{"resource": "object", "direction": "transfer"}],
    )
    assert len(o.resource_changes) == 1
    assert o.resource_changes[0]["resource"] == "object"


def test_outcome_atom_has_relation_changes() -> None:
    o = OutcomeAtom(
        affected_entity_role="actor",
        changed_dimension="distance",
        direction="decrease",
        relation_changes=[{"relation": "proximity", "direction": "increase"}],
    )
    assert len(o.relation_changes) == 1





# ── D2/D3: SemanticInterpreter consumes MeaningPerceptPacket ──────────

def test_semantic_interpreter_accepts_meaning_percept() -> None:
    """SemanticInterpreter.run() should accept optional meaning_percept."""
    store = _make_store()
    registry = _make_registry()
    uol_mapper = UOLMapper(registry)
    interpreter = SemanticInterpreter(uol_mapper, store=store)

    signal = _make_signal("come here")

    from cemm.kernel.context_kernel_builder import ContextKernelBuilder
    kernel = ContextKernelBuilder().from_signal(signal, turn_index=0)

    percept = MeaningPerceptPacket(
        id="mp_test",
        signal_id=signal.id,
        context_id=signal.context_id,
        raw_text="come here",
        tokens=["come", "here"],
        referents=[ReferentAtom(surface="here", role="place", entity_type="place")],
        actions=[ActionAtom(surface="come", action_key="move_toward_source")],
    )

    graph = interpreter.run(signal, kernel, meaning_percept=percept)
    assert graph is not None
    # The percept's referent "here" should be in entity_refs
    entity_ids = [e.get("entity_id", "") for e in graph.entity_refs]
    assert "here" in entity_ids


def test_semantic_interpreter_enriches_with_percept_actions() -> None:
    """SemanticInterpreter should add percept actions as processes."""
    store = _make_store()
    registry = _make_registry()
    uol_mapper = UOLMapper(registry)
    interpreter = SemanticInterpreter(uol_mapper, store=store)

    signal = _make_signal("eat food")

    from cemm.kernel.context_kernel_builder import ContextKernelBuilder
    kernel = ContextKernelBuilder().from_signal(signal, turn_index=0)

    percept = MeaningPerceptPacket(
        id="mp_test2",
        signal_id=signal.id,
        context_id=signal.context_id,
        raw_text="eat food",
        tokens=["eat", "food"],
        actions=[ActionAtom(surface="eat", action_key="consume_food")],
    )

    graph = interpreter.run(signal, kernel, meaning_percept=percept)
    process_keys = [p.get("frame_key", "") for p in graph.processes]
    assert "consume_food" in process_keys


def test_pipeline_passes_percept_to_uol_graph() -> None:
    """Pipeline should produce a UOLGraph from the meaning percept."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("come here")
    assert result.meaning_percept is not None
    assert result.uol_graph is not None
    assert result.uol_graph.signal_id


# ── D4: Event schema entries in uol_semantics.json ────────────────────

def test_event_schema_store_loads_action_schemas() -> None:
    store = load_event_schemas()
    assert len(store.action_schemas) > 0
    assert "come" in store.action_schemas
    assert store.action_schemas["come"].action_key == "move_toward_source"


def test_event_schema_store_loads_state_schemas() -> None:
    store = load_event_schemas()
    assert len(store.state_schemas) > 0
    assert "hungry" in store.state_schemas
    assert store.state_schemas["hungry"].dimension == "hunger"
    assert store.state_schemas["hungry"].triggers_need == "food"


def test_event_schema_store_loads_need_schemas() -> None:
    store = load_event_schemas()
    assert len(store.need_schemas) > 0
    assert "food" in store.need_schemas
    assert store.need_schemas["food"].satisfies_state == "hungry"


def test_event_schema_store_loads_place_affordances() -> None:
    store = load_event_schemas()
    assert len(store.place_affordances) > 0
    assert "kitchen" in store.place_affordances
    assert "food" in store.place_affordances["kitchen"].affords


def test_event_schema_store_loads_object_affordances() -> None:
    store = load_event_schemas()
    assert len(store.object_affordances) > 0
    assert "book" in store.object_affordances
    assert "increase_capability" in store.object_affordances["book"].affords


def test_event_schema_store_loads_social_schemas() -> None:
    store = load_event_schemas()
    assert len(store.social_schemas) > 0
    assert "greeting" in store.social_schemas
    assert store.social_schemas["greeting"].reply_obligation is True


def test_event_schema_store_loads_safety_schemas() -> None:
    store = load_event_schemas()
    assert len(store.safety_schemas) > 0
    assert "interpersonal_violence" in store.safety_schemas
    assert store.safety_schemas["interpersonal_violence"].severity == "high"


def test_event_schema_store_loads_idiom_schemas() -> None:
    store = load_event_schemas()
    assert len(store.idiom_schemas) > 0
    assert "looking_for_trouble" in store.idiom_schemas
    assert store.idiom_schemas["looking_for_trouble"].act_type == "social_conflict_clarify"


def test_event_schema_store_lookup_alias() -> None:
    store = load_event_schemas()
    result = store.lookup_alias("kitchen")
    assert result is not None
    assert result[0] == "place_affordance"
    assert result[1] == "kitchen"


def test_event_schema_store_lookup_alias_not_found() -> None:
    store = load_event_schemas()
    result = store.lookup_alias("nonexistent_xyz")
    assert result is None


def test_situation_frame_builder_uses_json_action_schemas() -> None:
    """SituationFrameBuilder should merge JSON-defined action schemas."""
    builder = SituationFrameBuilder()
    # JSON-defined schemas should be in the builder's schema dict
    # The seed schemas use action_key as dict key, JSON schemas should merge
    assert "move_toward_source" in builder._schemas
    assert "consume_food" in builder._schemas


def test_safety_frame_detector_uses_json_safety_schemas() -> None:
    """SafetyFrameDetector should merge JSON-defined safety aliases."""
    detector = SafetyFrameDetector()
    # "shoot" is in the JSON safety_schemas aliases
    # It should be detected as interpersonal_violence
    from cemm.types.meaning_percept import SituationFrame
    frame = SafetyFrameDetector().detect(
        situation=None,
        input_text="should I shoot him?",
    )
    assert frame is not None
    assert frame.category == "interpersonal_violence"


def test_safety_frame_detector_detects_json_self_harm() -> None:
    """SafetyFrameDetector should detect self_harm from JSON aliases."""
    detector = SafetyFrameDetector()
    frame = detector.detect(
        situation=None,
        input_text="I want to end it all",
    )
    assert frame is not None
    assert frame.category == "self_harm"


# ── Integration: full pipeline with event schemas ─────────────────────

def test_pipeline_enriches_graph_with_percept_referents() -> None:
    """Pipeline should produce a UOLGraph with percept content."""
    store = _make_store()
    registry = _make_registry()
    pipeline = Pipeline(store, registry)
    result = pipeline.run("give me the book")
    assert result.uol_graph is not None
    assert result.meaning_percept is not None
    # The graph should exist with the raw_text from the signal
    assert result.uol_graph.raw_text == "give me the book"
    assert result.uol_graph.signal_id
