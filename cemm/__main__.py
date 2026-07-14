# CEMM-ARCH: Refer to cemm_architecture_gap_trace.md and AGENTS.md before modifying.
# Fix 2: Model-driven action selection. Operator models loaded from ModelStore
# and scored via Ranker. Hardcoded routing only fires when no model exceeds threshold.

from __future__ import annotations
import os
import argparse
import json
import time
import uuid
from pathlib import Path
from typing import Any

from .registry import Registry, RegistryEntry
from .legacy.v3_3.pipeline import Pipeline, PipelineResult
from .memory.concept_lattice import ConceptLattice
from .memory.construction_lattice import ConstructionLattice
from .memory.episodic_trace_store import EpisodicTraceStore
from .memory.persistent_lattice_store import PersistentLatticeStore
from .memory.predicate_schema_store import PredicateSchemaStore

_ACTION_CONFIDENCE_THRESHOLD = 0.5


def _load_seed_data(name: str) -> list[dict[str, Any]]:
    """Load seed entries (predicates, UOL semantics, etc.) from cemm/data/*.json."""
    data_dir = Path(__file__).parent / "data"
    path = data_dir / f"{name}.json"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get(name, [])


def seed_registry(registry: Registry) -> None:
    predicates = _load_seed_data("predicates")
    for i, entry in enumerate(predicates):
        canonical = entry["canonical_key"]
        aliases = entry.get("aliases", [])
        registry.register(RegistryEntry(
            model_id=f"pred_{i}",
            canonical_key=canonical,
            kind="predicate",
            aliases=list(aliases),
        ))

    uol_semantics = _load_seed_data("uol_semantics")
    for i, entry in enumerate(uol_semantics):
        canonical = entry["canonical_key"]
        aliases = entry.get("aliases", [])
        registry.register(RegistryEntry(
            model_id=f"uol_{i}",
            canonical_key=canonical,
            kind="uol_semantic",
            aliases=list(aliases),
        ))

    # Operator registration is canonical (not language-specific). The metadata
    # is loaded from cemm/data/operators.json; the implementing classes are
    # imported here so import paths remain in code while the canonical list is
    # data-driven.
    for entry in _load_seed_data("operators"):
        key = entry["canonical_key"]
        registry.register(RegistryEntry(
            model_id=f"op_{key}",
            canonical_key=key,
            kind="operator",
            description=f"{key} operator",
        ))


def seed_self_state(
    knowledge_path: str | None = None,
    concept_lattice: ConceptLattice | None = None,
    durable_store: Any | None = None,
) -> None:
    """Seed self-knowledge into concept lattice and durable semantic store."""
    import json
    path = knowledge_path or os.path.join(os.path.dirname(__file__), "self_knowledge.json")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        config = json.load(f)

    ent_cfg = config.get("entity", {})

    # Seed concept lattice with self-knowledge via GraphPatches
    if concept_lattice is not None and config.get("claims"):
        _seed_self_concepts(concept_lattice, config["claims"])

    # Seed durable semantic store with self-knowledge relations
    if durable_store is not None and config.get("claims"):
        _seed_self_durable(durable_store, config["claims"], ent_cfg)


def _seed_self_concepts(concept_lattice: ConceptLattice, claims_cfgs: list[dict]) -> None:
    """Create GraphPatches from self-knowledge claims and consolidate into concept lattice."""
    from .types.graph_patch import GraphPatch, PatchOperation
    from .learning.concept_consolidator import ConceptConsolidator

    patches = []
    for claim_cfg in claims_cfgs:
        patches.append(GraphPatch(
            target="concept_lattice",
            operations=[PatchOperation(
                operation="upsert_concept_candidate",
                target_id=f"concept:{claim_cfg['subject']}",
                fields={
                    "key": claim_cfg["subject"],
                    "atom_kind": "entity",
                    "state": "operational_atom",
                    "predicate": claim_cfg["predicate"],
                    "object_value": claim_cfg.get("object_value", ""),
                    "confidence": claim_cfg.get("confidence", 0.95),
                },
                confidence=claim_cfg.get("confidence", 0.95),
            )],
            confidence=claim_cfg.get("confidence", 0.95),
            reason=f"seed_self_knowledge:{claim_cfg.get('predicate', 'unknown')}",
        ))
    if patches:
        consolidator = ConceptConsolidator(
            concept_lattice,
            persistent_store=getattr(concept_lattice, '_persistent_store', None),
        )
        consolidator.consolidate(patches)
    if concept_lattice is not None and hasattr(concept_lattice, 'flush_to_store'):
        concept_lattice.flush_to_store()


def _seed_self_durable(durable_store: Any, claims_cfgs: list[dict], ent_cfg: dict) -> None:
    """Seed DurableSemanticStore with self-knowledge as relation records."""
    entity_id = "self"
    entity_surface = ent_cfg.get("name", "CEMM")
    schema_store = PredicateSchemaStore()

    for claim_cfg in claims_cfgs:
        predicate = claim_cfg["predicate"]
        object_value = claim_cfg.get("object_value", "")
        if not object_value:
            continue
        durable_store.add_relation(
            relation_key=predicate,
            relation_family=schema_store.relation_family_for(predicate),
            subject_entity_id=entity_id,
            subject_surface=entity_surface,
            object_surface=object_value,
            confidence=claim_cfg.get("confidence", 0.95),
            source_patch_id="seed",
            evidence_refs=["seed"],
        )


def process_input(
    text: str,
    pipeline: Pipeline,
    context_id: str,
    turn_count: list[int],
) -> str:
    turn_count[0] += 1
    result = pipeline.run(text, context_id=context_id)
    output = result.output_text or ""

    return output or "I'm not sure how to respond."


def main() -> None:
    parser = argparse.ArgumentParser(description="CEMM — Contextual Event Memory Model")
    parser.add_argument("--eval", help="Single query to evaluate and exit")
    parser.add_argument("--once", help="Handle one user turn")
    parser.add_argument("--chat", action="store_true", help="Interactive chat mode")
    args = parser.parse_args()

    registry = Registry()
    persistent_store = PersistentLatticeStore(":memory:")
    concept_lattice = ConceptLattice(persistent_store=persistent_store)
    construction_lattice = ConstructionLattice()
    episodic_store = EpisodicTraceStore()
    pipeline = Pipeline(
        registry,
        concept_lattice=concept_lattice,
        construction_lattice=construction_lattice,
        episodic_store=episodic_store,
        auto_consolidate=True,
    )

    seed_registry(registry)
    seed_self_state(concept_lattice=concept_lattice, durable_store=pipeline._runtime.durable_semantic_store)

    context_id = f"session_{int(time.time())}"
    turn_count = [0]

    # --once: single turn through full architecture
    if args.once:
        output = process_input(args.once, pipeline, context_id, turn_count)
        print(output)
        return

    # --chat: interactive loop through full architecture
    if args.chat:
        print("CEMM — Contextual Event Memory Model (full architecture)")
        print("Type 'exit' to quit.\n")
        while True:
            try:
                text_in = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not text_in:
                continue
            output = process_input(text_in, pipeline, context_id, turn_count)
            print(output)
        return

    if args.eval:
        output = process_input(args.eval, pipeline, context_id, turn_count)
        print(output)
        return

    print("CEMM — Contextual Event Memory Model")
    print("Type 'exit' to quit.\n")
    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        output = process_input(text, pipeline, context_id, turn_count)
        print(output)


if __name__ == "__main__":
    main()
