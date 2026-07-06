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

from .store.store import Store

from .registry import Registry, RegistryEntry
from .kernel.pipeline import Pipeline, PipelineResult
from .learning.online import OnlineLearner
from .types.model import ModelKind, ModelStatus
from .types.permission import Permission
from .types.signal import Signal, SignalKind, SourceType
from .types.self_state import SelfState
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


def seed_causal_models(store: Store, concept_lattice: ConceptLattice | None = None) -> None:
    """Seed a small library of causal rule models so CausalInference can produce predictions."""
    from .types.model import Model, ModelKind, ModelStatus
    from .types.permission import Permission
    from .types.signal import Signal, SignalKind, SourceType

    rules = [
        ("causal_rain_flooding", "rain causes flooding", "causal_causes", ["rain"], ["flooding"]),
        ("causal_heat_melt", "heat causes melting", "causal_causes", ["heat"], ["melting"]),
        ("causal_study_pass", "studying causes passing the exam", "causal_causes", ["studying"], ["passing the exam"]),
        ("causal_exercise_energy", "exercise causes more energy", "causal_causes", ["exercise"], ["more energy"]),
    ]

    existing = store.models.find_by_kind(
        ModelKind.CAUSAL_RULE.value, ModelStatus.ACTIVE.value,
    )
    if existing:
        return

    for model_id, name, registry_key, preconditions, effects in rules:
        seed_signal = Signal(
            id=f"seed_{model_id}",
            kind=SignalKind.SYSTEM,
            source_id="seed",
            source_type=SourceType.SYSTEM,
            content=f"seed causal model: {name}",
            observed_at=time.time(),
            context_id="seed",
            salience=0.5,
            trust=1.0,
            permission=Permission.public(),
        )
        store.signals.put(seed_signal)
        model = Model(
            id=model_id,
            name=name,
            registry_key=registry_key,
            kind=ModelKind.CAUSAL_RULE,
            status=ModelStatus.ACTIVE,
            preconditions=preconditions,
            effects=effects,
            confidence=0.8,
            trust=0.9,
            risk=0.1,
            evidence_signal_ids=[seed_signal.id],
            permission=Permission.public(),
            created_at=time.time(),
            updated_at=time.time(),
        )
        store.models.put(model)

    # Also seed concept lattice with causal affordances
    if concept_lattice is not None:
        _seed_causal_affordances(concept_lattice, rules)


def _seed_causal_affordances(concept_lattice: ConceptLattice, rules: list) -> None:
    """Create GraphPatches from causal rules and consolidate into concept lattice."""
    from .types.graph_patch import GraphPatch, PatchOperation
    from .learning.concept_consolidator import ConceptConsolidator

    patches = []
    for model_id, name, _registry_key, preconditions, effects in rules:
        patches.append(GraphPatch(
            target="concept_lattice",
            operations=[PatchOperation(
                operation="custom",
                target_id=f"affordance:{model_id}",
                fields={
                    "affordance_key": name,
                    "trigger_atom_ids": preconditions,
                    "predicted_effect": effects,
                    "confidence": 0.8,
                },
                confidence=0.8,
            )],
            confidence=0.8,
            reason=f"seed_causal_affordance:{model_id}",
        ))
    if patches:
        consolidator = ConceptConsolidator(
            concept_lattice,
            persistent_store=getattr(concept_lattice, '_persistent_store', None),
        )
        consolidator.consolidate(patches)


def seed_self_state(
    store: Store,
    knowledge_path: str | None = None,
    concept_lattice: ConceptLattice | None = None,
    durable_store: Any | None = None,
) -> None:
    existing_state = store.self_store.latest()
    if existing_state is None:
        state = SelfState(
            id="self_main",
            name="cemm",
            created_at=time.time(),
            updated_at=time.time(),
        )
        store.self_store.put(state)

    if store.signals.get("seed") is None:
        store.signals.put(Signal(
            id="seed",
            kind=SignalKind.SYSTEM,
            source_id="seed",
            source_type=SourceType.SYSTEM,
            content="seed self knowledge",
            observed_at=time.time(),
            context_id="seed",
            salience=0.5,
            trust=1.0,
            permission=Permission.public(),
        ))

    # Seed self-knowledge entity + claims from JSON config
    import json, uuid
    path = knowledge_path or os.path.join(os.path.dirname(__file__), "self_knowledge.json")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        config = json.load(f)

    ent_cfg = config.get("entity", {})
    existing_entity = store.entities.get(ent_cfg["id"]) if ent_cfg.get("id") else None
    if existing_entity is None and ent_cfg:
        from .types.entity import Entity as _Entity, EntityType as _ET
        entity = _Entity(
            id=ent_cfg["id"],
            type=_ET(ent_cfg.get("type", "system")),
            name=ent_cfg.get("name", "CEMM"),
            aliases=ent_cfg.get("aliases", []),
            confidence=ent_cfg.get("confidence", 0.9),
            created_from_signal_id="seed",
            created_at=time.time(),
            updated_at=time.time(),
        )
        store.entities.put(entity)

    for claim_cfg in config.get("claims", []):
        from .types.claim import Claim as _Claim, ClaimStatus as _CS
        from .types.permission import Permission as _Perm
        existing = store.claims.find_by_subject(
            claim_cfg["subject"], claim_cfg["predicate"], limit=10,
        )
        already = any(
            c.object_value == claim_cfg.get("object_value")
            for c in existing
        )
        if not already:
            claim = _Claim(
                id=uuid.uuid4().hex[:16],
                subject_entity_id=claim_cfg["subject"],
                predicate=claim_cfg["predicate"],
                object_value=claim_cfg.get("object_value"),
                object_entity_id=claim_cfg.get("object_entity_id"),
                domain=claim_cfg.get("domain", "self_knowledge"),
                source_id="seed",
                evidence_signal_ids=["seed"],
                confidence=claim_cfg.get("confidence", 0.95),
                trust=claim_cfg.get("trust", 0.95),
                salience=0.8,
                status=_CS.ACTIVE,
                observed_at=time.time(),
                updated_at=time.time(),
                permission=_Perm.public(),
            )
            store.claims.put(claim)

    # Also seed concept lattice with self-knowledge via GraphPatches
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
    store: Store,
    registry: Registry,
    pipeline: Pipeline,
    online_learner: OnlineLearner,
    context_id: str,
    turn_count: list[int],
) -> str:
    turn_count[0] += 1
    # Single authority: Pipeline.run() injects self-state from store.self_store
    result = pipeline.run(text, context_id=context_id)
    output = result.output_text or ""

    # Backfill: re-realize from contract if output empty
    if not output and result.realization_contract is not None:
        try:
            from .kernel.semantic_realizer import SemanticRealizer
            realizer = SemanticRealizer()
            output = realizer.realize(
                result.realization_contract,
                result.answer_binding,
            ) or ""
        except Exception:
            output = ""

    # Background: online learning on semantic data
    if result.uol_graph is not None and result.kernel is not None:
        try:
            online_learner.record_outcome(
                source_id="user",
                domain="semantic_cycle",
                success=bool(output),
            )
        except Exception:
            pass

    # Background: induction on relation frames
    if result.relation_frames:
        try:
            from .learning.inductor import Inductor
            inductor = Inductor(
                store=store,
                registry=registry,
                concept_lattice=getattr(pipeline, '_concept_lattice', None),
            )
            inductor.induct(result.uol_graph, result.kernel)
        except Exception:
            pass

    return output or "I'm not sure how to respond."


def main() -> None:
    parser = argparse.ArgumentParser(description="CEMM — Contextual Event Memory Model")
    parser.add_argument("--db", default=":memory:", help="SQLite database path")
    parser.add_argument("--eval", help="Single query to evaluate and exit")
    parser.add_argument("--train", nargs="?", const="cemm_training.sqlite3",
                        help="Run training: path to SQLite DB (default: cemm_training.sqlite3)")
    parser.add_argument("--workers", type=int, default=2, help="Training worker count")
    parser.add_argument("--dry-run", action="store_true", help="Dry-run mode for training")
    parser.add_argument("--once", help="Handle one user turn")
    parser.add_argument("--chat", action="store_true", help="Interactive chat mode")
    args = parser.parse_args()

    store = Store(args.db)
    registry = Registry()
    persistent_store = PersistentLatticeStore(args.db)
    concept_lattice = ConceptLattice(persistent_store=persistent_store)
    construction_lattice = ConstructionLattice()
    episodic_store = EpisodicTraceStore()
    pipeline = Pipeline(
        store, registry,
        concept_lattice=concept_lattice,
        construction_lattice=construction_lattice,
        episodic_store=episodic_store,
        auto_consolidate=True,
    )
    online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)

    seed_registry(registry)
    seed_self_state(store, concept_lattice=concept_lattice, durable_store=pipeline._runtime.durable_semantic_store)
    seed_causal_models(store, concept_lattice=concept_lattice)

    context_id = f"session_{int(time.time())}"
    turn_count = [0]

    # --once: single turn through full architecture
    if args.once:
        output = process_input(args.once, store, registry, pipeline,
                               online_learner, context_id, turn_count)
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
            output = process_input(text_in, store, registry, pipeline,
                                   online_learner, context_id, turn_count)
            print(output)
        return

    if args.train:
        if not os.path.exists(args.train):
            print(f"No training DB at {args.train}. Create one via:")
            print(f"  python -m cemm.cemm_trainer ingest examples.jsonl")
            print(f"  python -m cemm.cemm_trainer run --workers 4")
            return
        from . import cemm_trainer as _ct
        _cargs = ["run", "--db", args.train, "--workers",
                  str(args.workers), "--poll-s", "2.0"]
        if args.dry_run:
            _cargs.append("--dry-run")
        raise SystemExit(_ct.main(_cargs))

    if args.eval:
        output = process_input(args.eval, store, registry, pipeline,
                               online_learner, context_id, turn_count)
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
        output = process_input(text, store, registry, pipeline,
                               online_learner, context_id, turn_count)
        print(output)


if __name__ == "__main__":
    main()
