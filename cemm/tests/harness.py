"""Shared test harness for integration and fuzz tests.

Provides a fully seeded Pipeline + Runtime, matching the web demo setup,
so tests exercise the real production code path end-to-end.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ.setdefault("CEMM_EXPORT_PATH", "")

from cemm.registry import Registry
from cemm.kernel.pipeline import Pipeline
from cemm.memory.concept_lattice import ConceptLattice
from cemm.memory.construction_lattice import ConstructionLattice
from cemm.memory.episodic_trace_store import EpisodicTraceStore
from cemm.memory.persistent_lattice_store import PersistentLatticeStore
from cemm.__main__ import seed_registry, seed_self_state
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.permission import Permission
from cemm.memory.predicate_schema_store import PredicateSchemaStore


class SeededSystem:
    """A fully seeded CEMM system ready for multiturn conversations."""

    def __init__(self, context_id: str = "test_session") -> None:
        self.registry = Registry()
        self.persistent_store = PersistentLatticeStore(":memory:")
        self.concept_lattice = ConceptLattice(persistent_store=self.persistent_store)
        self.construction_lattice = ConstructionLattice()
        self.episodic_store = EpisodicTraceStore()
        self.pipeline = Pipeline(
            self.registry,
            concept_lattice=self.concept_lattice,
            construction_lattice=self.construction_lattice,
            episodic_store=self.episodic_store,
        )

        seed_registry(self.registry)
        seed_self_state(
            concept_lattice=self.concept_lattice,
            durable_store=self.pipeline._runtime.durable_semantic_store,
        )

        self.context_id = context_id
        self.turn_count = [0]
        self._durable = self.pipeline._runtime.durable_semantic_store

        # Install cycle capture hook (same as web demo)
        self._install_cycle_hook()

    def _install_cycle_hook(self) -> None:
        orig = self.pipeline._runtime.run_turn

        def hooked(signal, kernel, **kw):
            cycle = orig(signal, kernel, **kw)
            self.pipeline._runtime._last_cycle = cycle
            return cycle

        self.pipeline._runtime.run_turn = hooked

    @property
    def runtime(self):
        return self.pipeline._runtime

    @property
    def durable_store(self):
        return self._durable

    def run(self, text: str) -> dict[str, Any]:
        """Run one turn and return a rich result dict with cycle diagnostics."""
        from cemm.__main__ import process_input

        self.turn_count[0] += 1
        result = self.pipeline.run(text, context_id=self.context_id)
        output = result.output_text or ""

        if not output:
            # Try response bundle from new engine
            cycle = getattr(self.runtime, "_last_cycle", None)
            if cycle and cycle.response_bundle:
                output = cycle.response_bundle.text or ""

        cycle = getattr(self.runtime, "_last_cycle", None)
        return {
            "output": output,
            "turn": self.turn_count[0],
            "cycle": cycle,
            "result": result,
            "obligation_kind": cycle.obligation_frame.obligation_kind if cycle and cycle.obligation_frame else None,
            "query_kind": cycle.semantic_query.query_kind if cycle and cycle.semantic_query else None,
            "relation_key": cycle.semantic_query.relation_key if cycle and cycle.semantic_query else None,
            "has_answer": cycle.answer_binding.has_answer if cycle and cycle.answer_binding else None,
            "abstention_reason": cycle.answer_binding.abstention_reason if cycle and cycle.answer_binding else None,
            "response_moves": [m.move_type for m in cycle.response_bundle.moves] if cycle and cycle.response_bundle else [],
            "response_goals": cycle.response_bundle.diagnostics.get("goals", []) if cycle and cycle.response_bundle else [],
            "slot_fills": [
                f.surface for f in cycle.answer_binding.slot_fills
            ] if cycle and cycle.answer_binding else [],
            "durable_count": self._durable.relation_count(),
            "patch_candidates": len(cycle.patch_candidates) if cycle else 0,
            "patch_committed": len(cycle.consolidation) if cycle else 0,
            "errors": cycle.diagnostics.get("errors", []) if cycle and cycle.diagnostics else [],
        }

    def run_turns(self, texts: list[str]) -> list[dict[str, Any]]:
        """Run multiple turns and return all results."""
        return [self.run(t) for t in texts]


def make_signal(text: str = "hello", context_id: str = "test") -> Signal:
    return Signal(
        id=uuid.uuid4().hex[:16],
        kind=SignalKind.INPUT,
        source_id="user",
        source_type=SourceType.USER,
        content=text,
        observed_at=time.time(),
        context_id=context_id,
        salience=0.8,
        trust=0.8,
        permission=Permission.public(),
    )


def load_self_knowledge() -> dict[str, Any]:
    path = Path(__file__).parent.parent / "self_knowledge.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def seed_durable_from_config(system: SeededSystem) -> None:
    """Seed durable store from self_knowledge.json (replicates __main__._seed_self_durable)."""
    config = load_self_knowledge()
    claims = config.get("claims", [])
    ent_cfg = config.get("entity", {})
    entity_surface = ent_cfg.get("name", "CEMM")

    for claim in claims:
        predicate = claim["predicate"]
        object_value = claim.get("object_value", "")
        if not object_value:
            continue
        system.durable_store.add_relation(
            relation_key=predicate,
            relation_family=PredicateSchemaStore().relation_family_for(predicate),
            subject_entity_id="self",
            subject_surface=entity_surface,
            object_surface=object_value,
            confidence=claim.get("confidence", 0.95),
            source_patch_id="seed",
            evidence_refs=["seed"],
        )
