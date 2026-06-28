from __future__ import annotations
import random
import time

from cemm.store.store import Store
from cemm.registry import Registry, RegistryEntry
from cemm.kernel.pipeline import Pipeline
from cemm.kernel.entity_resolver import EntityResolver
from cemm.operators.remember import RememberOperator
from cemm.operators.base import OperatorContext
from cemm.learning.online import OnlineLearner
from cemm.learning.inductor import Inductor
from cemm.learning.promotion import ModelPromoter
from cemm.retrieval.structural import StructuralRetriever, RetrievalQuery
from cemm.retrieval.ranker import Ranker
from cemm.synthesis.router import SynthesisRouter
from cemm.synthesis.result import SynthesisResult
from cemm.types.entity import EntityType
from cemm.types.model import ModelKind, ModelStatus


SEED = 42
NUM_EVENTS = 200
CHECKPOINT_INTERVAL = 50
NUM_RUNS = 3
ACTORS = ["alice", "bob", "charlie", "diana", "eve", "frank", "grace", "heidi"]
ACTIONS = ["query", "update", "save", "delete", "create", "train", "deploy", "test", "config", "backup"]
OBJECTS = ["postgres", "mysql", "sqlite", "redis", "mongo", "kafka", "docker", "k8s", "s3", "lambda"]
OUTCOMES = ["success", "failure", "timeout", "error", "success", "success"]

GROUND_TRUTH_DETERMINISTIC = {
    ("query", "postgres"): "success",
    ("delete", "k8s"): "failure",
    ("save", "favorite_db"): "success",
    ("backup", "s3"): "success",
    ("create", "docker"): "success",
}

GROUND_TRUTH_PROBABILISTIC = {
    ("update", "mysql"): ("success", 0.8),
    ("delete", "mongo"): ("failure", 0.8),
    ("config", "redis"): ("success", 0.8),
    ("train", "lambda"): ("success", 0.8),
    ("test", "sqlite"): ("success", 0.8),
}


def zipf_choices(population: list[str], n: int, alpha: float = 1.5) -> list[str]:
    weights = [1.0 / (i + 1) ** alpha for i in range(len(population))]
    return random.choices(population, weights=weights, k=n)


ALL_GROUND_TRUTH: list[tuple[str, str, str]] = []
for (action, obj), outcome in GROUND_TRUTH_DETERMINISTIC.items():
    ALL_GROUND_TRUTH.append((action, obj, outcome))
for (action, obj), (expected, _prob) in GROUND_TRUTH_PROBABILISTIC.items():
    ALL_GROUND_TRUTH.append((action, obj, expected))


def generate_event_stream(num_events: int, alias_noise: float = 0.1, rng: random.Random | None = None) -> list[dict]:
    rng = rng or random.Random()
    stream: list[dict] = []
    for t in range(num_events):
        actor = zipf_choices(ACTORS, 1, alpha=1.5) if random else [rng.choice(ACTORS)][0]
        actor = rng.choices(ACTORS, weights=[1.0/(i+1)**1.5 for i in range(len(ACTORS))])[0]
        if rng.random() < 0.5:
            action, obj, outcome = rng.choice(ALL_GROUND_TRUTH)
        else:
            action = rng.choice(ACTIONS)
            obj = rng.choice(OBJECTS)
            if (action, obj) in GROUND_TRUTH_DETERMINISTIC:
                outcome = GROUND_TRUTH_DETERMINISTIC[(action, obj)]
            elif (action, obj) in GROUND_TRUTH_PROBABILISTIC:
                expected, prob = GROUND_TRUTH_PROBABILISTIC[(action, obj)]
                outcome = expected if rng.random() < prob else rng.choice(OUTCOMES)
            else:
                outcome = rng.choice(OUTCOMES)
        event: dict = {
            "actor": actor,
            "action": action,
            "object": obj,
            "outcome": outcome,
            "timestamp": t,
            "source_id": f"source_{t % 5}",
        }
        if rng.random() < alias_noise:
            event["alias"] = f"{actor}_{t % 3}"
        stream.append(event)
    return stream


def _entity_name_from_precondition(
    store: Store, precondition: str,
) -> str | None:
    if not precondition.startswith("object:"):
        return None
    eid = precondition[len("object:"):]
    entity = store.entities.get(eid)
    return entity.name if entity else eid


def evaluate_checkpoint(
    store: Store,
    inductor: Inductor,
    promoter: ModelPromoter,
    events_processed: int,
    entity_resolver: EntityResolver,
) -> dict:
    metrics: dict = {"events_processed": events_processed}

    inductor.set_threshold(5)
    candidates = inductor.maybe_induct(domain="causal")
    causal_candidates = [m for m in candidates if m.kind == ModelKind.CAUSAL_RULE]
    metrics["candidates_created"] = len(causal_candidates)

    promoted_ids: list[str] = []
    for model in causal_candidates:
        ok, msg = promoter.can_promote(model)
        if ok:
            prom_ok, _ = promoter.promote(model.id)
            if prom_ok:
                promoted_ids.append(model.id)
    metrics["promoted"] = len(promoted_ids)

    active_rules = store.models.find_by_kind("causal_rule", "active")
    metrics["active_rules"] = len(active_rules)

    all_ground_truth: dict = {}
    all_ground_truth.update(GROUND_TRUTH_DETERMINISTIC)
    for (action, obj), (expected, _) in GROUND_TRUTH_PROBABILISTIC.items():
        all_ground_truth[(action, obj)] = expected

    correct = 0
    discovered = set()
    for (action, obj), expected_outcome in all_ground_truth.items():
        for rule in active_rules:
            if rule.name != action:
                continue
            precond_names = [
                _entity_name_from_precondition(store, p) for p in rule.preconditions
            ]
            if obj not in precond_names:
                continue
            predicted = [e for e in rule.effects if e.startswith("outcome:")]
            if any(f"outcome:{expected_outcome}" == e for e in predicted):
                correct += 1
                discovered.add((action, obj))

    metrics["prediction_accuracy"] = correct / max(len(active_rules), 1) if active_rules else 0.0
    metrics["ground_truth_discovered"] = len(discovered)
    metrics["ground_truth_recall"] = len(discovered) / max(len(all_ground_truth), 1)

    promoted_model_confidences = [m.confidence for m in active_rules]
    metrics["mean_promoted_confidence"] = (
        sum(promoted_model_confidences) / len(promoted_model_confidences) if promoted_model_confidences else 0.0
    )

    return metrics


PREFERENCES = [
    {"predicate": "favorite_database", "object": "postgres"},
    {"predicate": "preferred_language", "object": "python"},
    {"predicate": "favorite_editor", "object": "vscode"},
    {"predicate": "preferred_os", "object": "linux"},
]

DISTRACTOR_CLAIMS = [
    {"predicate": "favorite_database", "object": "mysql"},
    {"predicate": "preferred_language", "object": "java"},
    {"predicate": "favorite_color", "object": "blue"},
    {"predicate": "preferred_os", "object": "macos"},
]

MEMORY_QUERIES = [
    {"predicate": "favorite_database", "expected": "postgres"},
    {"predicate": "preferred_language", "expected": "python"},
    {"predicate": "favorite_editor", "expected": "vscode"},
    {"predicate": "preferred_os", "expected": "linux"},
]


def _rank_kernel() -> "ContextKernel":
    from cemm.types.context_kernel import ContextKernel, WorldState, UserState, TimeState, ConversationState, GoalState, MemoryState, Budget
    return ContextKernel(
        id="rank_kernel", world=WorldState(), user=UserState(),
        time=TimeState(now=time.time(), bucket="afternoon"),
        conversation=ConversationState(session_id="memory", turn_index=0, recent_signal_ids=[]),
        goal=GoalState(), memory=MemoryState(), permission=__import__("cemm.types.permission", fromlist=["Permission"]).Permission.public(),
        budget=Budget(),
    )


def run_memory_phase(store: Store, registry: Registry, pipeline: Pipeline, resolver: EntityResolver) -> dict:
    remember_op = RememberOperator()
    retriever = StructuralRetriever(store)
    ranker = Ranker()
    synth_router = SynthesisRouter()

    user_entity = resolver.resolve_or_create("user", EntityType.PERSON, "", None)

    def _store(predicate: str, obj: str, domain: str = "memory") -> None:
        now = time.time()
        text = f"user {predicate} {obj}"
        pr = pipeline.run(text, context_id="memory_phase")
        signal = pr.signals[0]
        kernel = pr.kernel
        obj_entity = resolver.resolve_or_create(obj, EntityType.OBJECT, signal.id, kernel)
        ctx = OperatorContext(
            kernel=kernel, input_signal=signal, store=store, registry=registry,
            selected_claim_ids=[], selected_model_ids=[],
            params={
                "subject_entity_id": user_entity.id,
                "predicate": predicate,
                "object_entity_id": obj_entity.id,
                "object_value": obj,
                "domain": domain,
                "qualifiers": {},
            },
        )
        remember_op.execute(ctx)

    for dist in DISTRACTOR_CLAIMS:
        _store(dist["predicate"], dist["object"], domain="distractor")
    for pref in PREFERENCES:
        _store(pref["predicate"], pref["object"], domain="preference")

    rk = _rank_kernel()
    prec_at_1: list[float] = []
    synth_correct: list[float] = []
    for q in MEMORY_QUERIES:
        q_result = retriever.retrieve(RetrievalQuery(subject_entity_id=user_entity.id, predicate=q["predicate"]))
        ranked = ranker.rank_claims(q_result.claims, rk)
        correct = 0.0
        if ranked:
            top_claim = ranked[0][0]
            if top_claim.object_value == q["expected"]:
                correct = 1.0
        prec_at_1.append(correct)

        synth_params = {"selected_claim_ids": [c.id for c, _ in ranked[:3]]} if ranked else {}
        synth_result: SynthesisResult = synth_router.route("extractive", rk, store, registry, synth_params)
        faithful = 1.0 if q["expected"] in synth_result.output else 0.0
        synth_correct.append(faithful)

    return {
        "memory_precision_at_1": sum(prec_at_1) / len(prec_at_1) if prec_at_1 else 0.0,
        "memory_synthesis_faithfulness": sum(synth_correct) / len(synth_correct) if synth_correct else 0.0,
    }


def run_trial(seed: int, num_events: int, alias_noise: float = 0.1) -> dict:
    rng = random.Random(seed)
    store = Store(":memory:")
    registry = Registry()
    pipeline = Pipeline(store, registry)
    resolver = EntityResolver(store.entities)

    for i, action in enumerate(ACTIONS):
        registry.register(RegistryEntry(
            model_id=f"pred_{i}",
            canonical_key=action,
            kind="predicate",
            aliases=[action[:3]],
        ))

    self_state_data = {"id": "self_main", "name": "cemm", "created_at": time.time(), "updated_at": time.time()}
    from cemm.types.self_state import SelfState
    store.self_store.put(SelfState(**self_state_data))

    stream = generate_event_stream(num_events, alias_noise, rng=rng)
    learner = OnlineLearner(store.source_trust, store.self_store, store.claims)
    inductor = Inductor(store, feedback_threshold=5)
    promoter = ModelPromoter(store)
    remember_op = RememberOperator()

    metrics: dict = {"latencies_ms": [], "checkpoints": []}

    for i, event in enumerate(stream):
        t0 = time.perf_counter()

        now = time.time()
        event_text = f"{event['actor']} {event['action']} {event['object']}"
        pipeline_result = pipeline.run(event_text, context_id="poc_train")
        signal = pipeline_result.signals[0]
        kernel = pipeline_result.kernel

        actor_entity = resolver.resolve_or_create(
            event["actor"], EntityType.PERSON, signal.id, kernel,
        )
        obj_entity = resolver.resolve_or_create(
            event["object"], EntityType.OBJECT, signal.id, kernel,
        )

        ctx = OperatorContext(
            kernel=kernel,
            input_signal=signal,
            store=store,
            registry=registry,
            selected_claim_ids=[],
            selected_model_ids=[],
            params={
                "subject_entity_id": actor_entity.id,
                "predicate": event["action"],
                "object_entity_id": obj_entity.id,
                "object_value": event["object"],
                "domain": "causal",
                "qualifiers": {"outcome": event["outcome"]},
            },
        )
        op_result = remember_op.execute(ctx)

        success = event["outcome"] == "success"
        learner.record_outcome(source_id=event["source_id"], domain="causal", success=success)
        if op_result.new_claim_ids:
            learner.update_claim_confidence(
                claim_id=op_result.new_claim_ids[0],
                feedback_correct=success,
            )

        t1 = time.perf_counter()
        metrics["latencies_ms"].append((t1 - t0) * 1000.0)

        if (i + 1) % CHECKPOINT_INTERVAL == 0 or i == num_events - 1:
            cp = evaluate_checkpoint(store, inductor, promoter, i + 1, resolver)
            metrics["checkpoints"].append(cp)

    mem = run_memory_phase(store, registry, pipeline, resolver)
    metrics.update(mem)
    return metrics


def aggregate_metrics(all_metrics: list[dict]) -> dict:
    result: dict = {}
    latencies: list[float] = []
    for run in all_metrics:
        latencies.extend(run.get("latencies_ms", []))
    if latencies:
        result["latency_mean_ms"] = sum(latencies) / len(latencies)
        latencies.sort()
        result["latency_median_ms"] = latencies[len(latencies) // 2]

    final_checkpoints = [run["checkpoints"][-1] for run in all_metrics if run.get("checkpoints")]
    if final_checkpoints:
        result["final_candidates_created"] = sum(cp["candidates_created"] for cp in final_checkpoints) / len(final_checkpoints)
        result["final_promoted"] = sum(cp["promoted"] for cp in final_checkpoints) / len(final_checkpoints)
        result["final_active_rules"] = sum(cp["active_rules"] for cp in final_checkpoints) / len(final_checkpoints)
        result["final_prediction_accuracy"] = sum(cp["prediction_accuracy"] for cp in final_checkpoints) / len(final_checkpoints)
        result["final_recall"] = sum(cp["ground_truth_recall"] for cp in final_checkpoints) / len(final_checkpoints)
        result["final_mean_confidence"] = sum(cp["mean_promoted_confidence"] for cp in final_checkpoints) / len(final_checkpoints)

    all_cp = []
    for run in all_metrics:
        all_cp.extend(run.get("checkpoints", []))
    if all_cp:
        result["checkpoint_candidates_created"] = sum(cp["candidates_created"] for cp in all_cp) / len(all_cp)
        result["checkpoint_promoted"] = sum(cp["promoted"] for cp in all_cp) / len(all_cp)
        result["checkpoint_accuracy"] = sum(cp["prediction_accuracy"] for cp in all_cp) / len(all_cp)
        result["checkpoint_recall"] = sum(cp["ground_truth_recall"] for cp in all_cp) / len(all_cp)
        result["checkpoint_mean_confidence"] = sum(cp["mean_promoted_confidence"] for cp in all_cp) / len(all_cp)

    if "memory_precision_at_1" in all_metrics[0]:
        p1_vals = [m["memory_precision_at_1"] for m in all_metrics]
        sf_vals = [m["memory_synthesis_faithfulness"] for m in all_metrics]
        result["memory_precision_at_1"] = sum(p1_vals) / len(p1_vals)
        result["memory_synthesis_faithfulness"] = sum(sf_vals) / len(sf_vals)

    return result


def print_results(agg: dict) -> None:
    print("=" * 65)
    print("CEMM Causal + Memory PoC -- Phase 1+2 Results")
    print("=" * 65)
    rows = [
        ("Causal latency (mean)", f"{agg.get('latency_mean_ms', 0):.1f}ms"),
        ("Causal candidates created (avg)", f"{agg.get('final_candidates_created', 0):.1f}"),
        ("Causal promoted (avg)", f"{agg.get('final_promoted', 0):.1f}"),
        ("Causal active rules (avg)", f"{agg.get('final_active_rules', 0):.1f}"),
        ("Causal prediction accuracy", f"{agg.get('final_prediction_accuracy', 0):.3f}"),
        ("Causal ground truth recall", f"{agg.get('final_recall', 0):.3f}"),
        ("Causal promoted model confidence", f"{agg.get('final_mean_confidence', 0):.3f}"),
        "---",
        ("Memory precision@1", f"{agg.get('memory_precision_at_1', 0):.3f}"),
        ("Memory synthesis faithfulness", f"{agg.get('memory_synthesis_faithfulness', 0):.3f}"),
    ]
    for item in rows:
        if item == "---":
            print("  " + "-" * 55)
        else:
            label, value = item
            print(f"  {label:.<48s} {value:>8s}")
    print()
    print("Causal targets:")
    print(f"  Precision (min viable .80):     {agg.get('final_prediction_accuracy', 0):.3f}")
    print(f"  Recall (min viable .40):        {agg.get('final_recall', 0):.3f}")
    print(f"  Latency (max 50ms):             {agg.get('latency_mean_ms', 0):.1f}ms")
    print()
    print("Memory targets:")
    print(f"  Precision@1 (target 1.0):        {agg.get('memory_precision_at_1', 0):.3f}")
    print(f"  Synthesis faithfulness (1.0):    {agg.get('memory_synthesis_faithfulness', 0):.3f}")


def main() -> None:
    print(f"CEMM Causal Prediction PoC -- {NUM_RUNS} runs x {NUM_EVENTS} events (seed={SEED})")
    print(f"  Ground truth: {len(GROUND_TRUTH_DETERMINISTIC)} deterministic + {len(GROUND_TRUTH_PROBABILISTIC)} probabilistic")
    print(f"  Checkpoint interval: {CHECKPOINT_INTERVAL}")
    print()

    all_metrics: list[dict] = []
    for run in range(NUM_RUNS):
        t0 = time.time()
        seed = SEED + run
        print(f"Run {run + 1}/{NUM_RUNS} (seed={seed})...", end=" ", flush=True)
        metrics = run_trial(seed, NUM_EVENTS, alias_noise=0.1)
        elapsed = time.time() - t0
        print(f"done in {elapsed:.2f}s")
        all_metrics.append(metrics)

    print()
    agg = aggregate_metrics(all_metrics)
    print_results(agg)


if __name__ == "__main__":
    main()
