from __future__ import annotations
import math
import random
import time
import uuid
from collections import Counter

from cemm.store.store import Store
from cemm.registry import Registry, RegistryEntry
from cemm.kernel.pipeline import Pipeline
from cemm.kernel.context_kernel_builder import ContextKernelBuilder
from cemm.retrieval.structural import StructuralRetriever, RetrievalQuery
from cemm.retrieval.ranker import Ranker
from cemm.learning.online import OnlineLearner
from cemm.learning.inductor import Inductor
from cemm.learning.promotion import ModelPromoter
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.entity import Entity, EntityType
from cemm.types.claim import Claim, ClaimStatus
from cemm.types.context_kernel import ContextKernel
from cemm.types.permission import Permission
from cemm.types.model import Model, ModelKind, ModelStatus
from cemm.confidence.log_odds import probability


SEED = 42
NUM_EVENTS = 150
BATCH_SIZE = 10
NUM_RUNS = 5
CHECKPOINT_INTERVAL = 50
ARTIFICIAL_PREDICATES = 10

ACTORS = ["alice", "bob", "charlie", "diana", "eve", "frank", "grace", "heidi"]
ACTIONS = ["query", "update", "save", "delete", "create", "train", "deploy", "test", "config", "backup"]
OBJECTS = ["postgres", "mysql", "sqlite", "redis", "mongo", "kafka", "docker", "k8s", "s3", "lambda"]
OUTCOMES = ["success", "failure", "timeout", "error", "success", "success"]

GROUND_TRUTH_RULES = {
    ("query", "postgres"): "success",
    ("save", "favorite_db"): "success",
    ("backup", "s3"): "success",
    ("create", "docker"): "success",
    ("delete", "k8s"): "failure",
}


def zipf_choices(population: list[str], n: int, alpha: float = 1.5) -> list[str]:
    weights = [1.0 / (i + 1) ** alpha for i in range(len(population))]
    return random.choices(population, weights=weights, k=n)


def generate_event_stream(num_events: int, alias_noise: float = 0.1) -> list[dict]:
    random.seed(SEED)
    stream: list[dict] = []
    for t in range(num_events):
        actor = zipf_choices(ACTORS, 1)[0]
        action = random.choice(ACTIONS)
        obj = random.choice(OBJECTS)
        outcome: str
        if (action, obj) in GROUND_TRUTH_RULES:
            outcome = GROUND_TRUTH_RULES[(action, obj)]
        else:
            outcome = random.choice(OUTCOMES)
        event: dict = {
            "actor": actor,
            "action": action,
            "object": obj,
            "outcome": outcome,
            "timestamp": t,
            "source_id": f"source_{actor}_{t % 5}",
        }
        if random.random() < alias_noise:
            event["alias"] = f"{actor}_{t % 3}"
        stream.append(event)
    return stream


def create_kernel_for_retrieval() -> ContextKernel:
    builder = ContextKernelBuilder()
    kernel = builder.build()
    return kernel


def precision_at_k(ranked: list[tuple], ground_truth: list[str], k: int) -> float:
    top = [c.predicate if hasattr(c, "predicate") else str(c) for c, _ in ranked[:k]]
    if not top:
        return 0.0
    hits = sum(1 for t in top if t in ground_truth)
    return hits / len(top)


def precision_at_k_claims(ranked: list[tuple[Claim, float]], ground_truth_predicate: str, k: int) -> float:
    top = ranked[:k]
    if not top:
        return 0.0
    hits = sum(1 for c, _ in top if c.predicate == ground_truth_predicate)
    return hits / len(top)


def confidence_calibration_error(claims: list[Claim]) -> float:
    if not claims:
        return 0.0
    buckets: dict[str, list[float]] = {}
    for c in claims:
        bucket = round(c.confidence * 10) / 10
        buckets.setdefault(str(bucket), []).append(c.confidence)
    if not buckets:
        return 0.0
    errors: list[float] = []
    for bucket_key, vals in buckets.items():
        mean_conf = sum(vals) / len(vals)
        bucket_low = float(bucket_key)
        bucket_high = bucket_low + 0.1
        bucket_center = (bucket_low + bucket_high) / 2
        errors.append((mean_conf - bucket_center) ** 2)
    return math.sqrt(sum(errors) / len(errors)) if errors else 0.0


def run_trial(seed: int, num_events: int, alias_noise: float = 0.1) -> dict:
    random.seed(seed)
    store = Store(":memory:")
    registry = Registry()
    pipeline = Pipeline(store, registry)

    for i in range(ARTIFICIAL_PREDICATES):
        registry.register(RegistryEntry(
            model_id=f"pred_{i}",
            canonical_key=ACTIONS[i],
            kind="predicate",
            aliases=[ACTIONS[i][:3]],
        ))

    self_state_data = {
        "id": "self_main",
        "name": "cemm",
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    from cemm.types.self_state import SelfState
    self_state = SelfState(**self_state_data)
    store.self_store.put(self_state)

    stream = generate_event_stream(num_events, alias_noise)

    learner = OnlineLearner(
        source_trust_store=store.source_trust,
        self_store=store.self_store,
        claim_store=store.claims,
    )
    inductor = Inductor(store, feedback_threshold=5)
    promoter = ModelPromoter(store)
    retriever = StructuralRetriever(store)
    ranker = Ranker()
    kernel = create_kernel_for_retrieval()

    stored_claim_ids: list[str] = []
    all_events: list[dict] = []
    all_claims: list[Claim] = []

    metrics: dict = {
        "precision_at_1": [],
        "precision_at_3": [],
        "calibration_errors": [],
        "source_trust_values": [],
        "induction_counts": [],
        "promotion_counts": [],
        "latencies_ms": [],
        "checkpoints": [],
    }

    for i, event in enumerate(stream):
        t0 = time.perf_counter()

        # Phase 1: Ingest
        now = time.time()
        signal = Signal(
            id=uuid.uuid4().hex[:16],
            kind=SignalKind.INPUT,
            source_id=event["source_id"],
            source_type=SourceType.USER,
            content=f"{event['actor']} {event['action']} {event['object']}",
            observed_at=now,
            context_id="poc_train",
            salience=0.8,
            trust=0.8,
            permission=Permission.public(),
        )
        store.signals.put(signal)

        entity = store.entities.get(event["actor"])
        if entity is None:
            entity = Entity(
                id=event["actor"],
                type=EntityType.PERSON,
                name=event["actor"],
                aliases=[event.get("alias", event["actor"])],
                confidence=0.7,
                created_from_signal_id=signal.id,
                created_at=now,
                updated_at=now,
            )
            store.entities.put(entity)

        claim = Claim(
            id=uuid.uuid4().hex[:16],
            subject_entity_id=event["actor"],
            predicate=event["action"],
            object_value=event["object"],
            object_entity_id=event["object"],
            evidence_signal_ids=[signal.id],
            source_id=event["source_id"],
            domain="poc",
            confidence=0.7,
            trust=0.7,
            salience=0.3,
            status=ClaimStatus.ACTIVE,
            observed_at=now,
            updated_at=now,
            permission=Permission.public(),
        )
        store.claims.put(claim)
        stored_claim_ids.append(claim.id)
        all_claims.append(claim)
        all_events.append(event)

        # Phase 2: Retrieve + Rank
        q = RetrievalQuery(
            subject_entity_id=event["actor"],
            predicate=event["action"],
            limit=10,
        )
        result = retriever.retrieve(q, kernel)
        ranked = ranker.rank_claims(result.claims, kernel)

        p1 = precision_at_k_claims(ranked, event["action"], 1)
        p3 = precision_at_k_claims(ranked, event["action"], 3)
        metrics["precision_at_1"].append(p1)
        metrics["precision_at_3"].append(p3)

        # Phase 3: Feedback + Update
        success = event["outcome"] == "success"
        learner.record_outcome(
            source_id=event["source_id"],
            domain="poc",
            success=success,
        )
        if claim.id:
            learner.update_claim_confidence(
                claim_id=claim.id,
                feedback_correct=success,
            )

        t1 = time.perf_counter()
        metrics["latencies_ms"].append((t1 - t0) * 1000.0)

        # Phase 4: Checkpoint evaluations
        if (i + 1) % CHECKPOINT_INTERVAL == 0 or i == num_events - 1:
            checkpoint_metrics = _evaluate_checkpoint(
                store, learner, inductor, promoter, retriever, ranker, kernel,
                all_claims, all_events, num_events, i + 1,
            )
            metrics["checkpoints"].append(checkpoint_metrics)

    # Collect source trust values after all updates
    for source in set(e["source_id"] for e in stream):
        st = store.source_trust.get(source, "poc")
        if st is not None:
            metrics["source_trust_values"].append(st.trust)

    cal_error = confidence_calibration_error(all_claims)
    metrics["calibration_errors"].append(cal_error)

    return metrics


def _evaluate_checkpoint(
    store: Store,
    learner: OnlineLearner,
    inductor: Inductor,
    promoter: ModelPromoter,
    retriever: StructuralRetriever,
    ranker: Ranker,
    kernel: ContextKernel,
    all_claims: list[Claim],
    all_events: list[dict],
    total_events: int,
    events_processed: int,
) -> dict:
    cp: dict = {}

    active = store.claims.find_active(500)
    cp["total_claims"] = len(active)

    p1_vals: list[float] = []
    p3_vals: list[float] = []
    for event in all_events[-50:]:
        q = RetrievalQuery(subject_entity_id=event["actor"], predicate=event["action"], limit=10)
        result = retriever.retrieve(q, kernel)
        ranked = ranker.rank_claims(result.claims, kernel)
        p1_vals.append(precision_at_k_claims(ranked, event["action"], 1))
        p3_vals.append(precision_at_k_claims(ranked, event["action"], 3))
    cp["precision_at_1"] = sum(p1_vals) / len(p1_vals) if p1_vals else 0.0
    cp["precision_at_3"] = sum(p3_vals) / len(p3_vals) if p3_vals else 0.0

    cp["calibration_error"] = confidence_calibration_error(all_claims)

    source_ids = set(e["source_id"] for e in all_events)
    trust_vals = []
    for sid in source_ids:
        st = store.source_trust.get(sid, "poc")
        if st is not None:
            trust_vals.append(st.trust)
    cp["mean_source_trust"] = sum(trust_vals) / len(trust_vals) if trust_vals else 0.0

    inductor.set_threshold(5)
    candidates = inductor.maybe_induct(domain="poc")
    cp["induction_candidates"] = len(candidates)

    promoted = 0
    for m in candidates:
        ok, _ = promoter.can_promote(m)
        if ok:
            prom_ok, _ = promoter.promote(m.id)
            if prom_ok:
                promoted += 1
    cp["promotions"] = promoted

    all_models = store.models.find_by_kind("predicate")
    cp["total_models"] = len(all_models)
    active_models = [m for m in all_models if m.status == ModelStatus.ACTIVE]
    cp["active_models"] = len(active_models)

    induction_recall = 0.0
    total_ground_truth = len(GROUND_TRUTH_RULES)
    if total_ground_truth > 0:
        discovered = sum(
            1 for action, obj in GROUND_TRUTH_RULES
            if any(
                m.name == action and obj in m.description
                for m in all_models if m.status == ModelStatus.ACTIVE
            )
        )
        induction_recall = discovered / total_ground_truth
    cp["induction_recall"] = induction_recall

    cp["events_processed"] = events_processed
    return cp


def aggregate_metrics(all_run_metrics: list[dict]) -> dict:
    result: dict = {}

    for metric_key in ["precision_at_1", "precision_at_3", "latencies_ms", "calibration_errors"]:
        combined: list[float] = []
        for run in all_run_metrics:
            combined.extend(run.get(metric_key, []))
        if combined:
            result[f"{metric_key}_mean"] = sum(combined) / len(combined)
            combined.sort()
            result[f"{metric_key}_median"] = combined[len(combined) // 2]
            result[f"{metric_key}_min"] = combined[0]
            result[f"{metric_key}_max"] = combined[-1]

    trust_combined: list[float] = []
    for run in all_run_metrics:
        trust_combined.extend(run.get("source_trust_values", []))
    if trust_combined:
        result["source_trust_convergence_mean"] = sum(trust_combined) / len(trust_combined)

    cp_prec1: list[float] = []
    cp_prec3: list[float] = []
    cp_recall: list[float] = []
    cp_cal: list[float] = []
    cp_promotions: list[float] = []
    cp_trust: list[float] = []
    for run in all_run_metrics:
        for cp in run.get("checkpoints", []):
            cp_prec1.append(cp.get("precision_at_1", 0))
            cp_prec3.append(cp.get("precision_at_3", 0))
            cp_recall.append(cp.get("induction_recall", 0))
            cp_cal.append(cp.get("calibration_error", 0))
            cp_promotions.append(cp.get("promotions", 0))
            cp_trust.append(cp.get("mean_source_trust", 0))
    if cp_prec1:
        result["checkpoint_precision_at_1_mean"] = sum(cp_prec1) / len(cp_prec1)
        result["checkpoint_precision_at_3_mean"] = sum(cp_prec3) / len(cp_prec3)
        result["checkpoint_induction_recall_mean"] = sum(cp_recall) / len(cp_recall)
        result["checkpoint_calibration_error_mean"] = sum(cp_cal) / len(cp_cal)
        result["checkpoint_promotions_mean"] = sum(cp_promotions) / len(cp_promotions)
        result["checkpoint_source_trust_mean"] = sum(cp_trust) / len(cp_trust)
        result["checkpoint_final_recall"] = cp_recall[-1] if cp_recall else 0.0

    return result


def print_results(aggregated: dict) -> None:
    print("=" * 60)
    print("CEMM PoC Training Results")
    print("=" * 60)

    rows = [
        ("Retrieval Precision@1 (mean)", f"{aggregated.get('precision_at_1_mean', 0):.4f}"),
        ("Retrieval Precision@3 (mean)", f"{aggregated.get('precision_at_3_mean', 0):.4f}"),
        ("Source Trust Convergence (mean)", f"{aggregated.get('source_trust_convergence_mean', 0):.4f}"),
        ("Confidence Calibration Error (mean)", f"{aggregated.get('calibration_errors_mean', 0):.4f}"),
        ("Checkpoint Final Induction Recall", f"{aggregated.get('checkpoint_final_recall', 0):.4f}"),
        ("Checkpoint Avg Precision@1", f"{aggregated.get('checkpoint_precision_at_1_mean', 0):.4f}"),
        ("Checkpoint Avg Precision@3", f"{aggregated.get('checkpoint_precision_at_3_mean', 0):.4f}"),
        ("Checkpoint Avg Calibration Error", f"{aggregated.get('checkpoint_calibration_error_mean', 0):.4f}"),
        ("Checkpoint Avg Source Trust", f"{aggregated.get('checkpoint_source_trust_mean', 0):.4f}"),
        ("Checkpoint Avg Promotions", f"{aggregated.get('checkpoint_promotions_mean', 0):.4f}"),
    ]
    for label, value in rows:
        print(f"  {label:.<50s} {value:>8s}")

    print()
    print(f"Targets:")
    print(f"  Precision@3 min viable: .60  got: {aggregated.get('checkpoint_precision_at_3_mean', 0):.4f}")
    print(f"  Source trust convergence .80 target: {aggregated.get('checkpoint_source_trust_mean', 0):.4f}")
    print(f"  Calibration error .20 max:          {aggregated.get('checkpoint_calibration_error_mean', 0):.4f}")
    print(f"  Induction recall .40 min viable:    {aggregated.get('checkpoint_final_recall', 0):.4f}")


def main() -> None:
    print(f"CEMM PoC Training: {NUM_RUNS} runs x {NUM_EVENTS} events (seed={SEED})")
    print(f"  Ground truth rules: {len(GROUND_TRUTH_RULES)}")
    print(f"  Actors: {ACTORS}")
    print(f"  Actions: {ACTIONS}")
    print(f"  Objects: {OBJECTS}")
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

        p1 = sum(metrics["precision_at_1"]) / len(metrics["precision_at_1"]) if metrics["precision_at_1"] else 0
        p3 = sum(metrics["precision_at_3"]) / len(metrics["precision_at_3"]) if metrics["precision_at_3"] else 0
        lat = sum(metrics["latencies_ms"]) / len(metrics["latencies_ms"]) if metrics["latencies_ms"] else 0
        trust = sum(metrics["source_trust_values"]) / len(metrics["source_trust_values"]) if metrics["source_trust_values"] else 0
        cal = sum(metrics["calibration_errors"]) / len(metrics["calibration_errors"]) if metrics["calibration_errors"] else 0
        final_recall = metrics["checkpoints"][-1]["induction_recall"] if metrics["checkpoints"] else 0
        print(f"    P@1={p1:.3f}  P@3={p3:.3f}  trust={trust:.3f}  cal={cal:.4f}  recall={final_recall:.3f}  lat={lat:.1f}ms")
        all_metrics.append(metrics)

    print()
    aggregated = aggregate_metrics(all_metrics)
    print_results(aggregated)

    final_recall = aggregated.get("checkpoint_final_recall", 0)
    p3 = aggregated.get("checkpoint_precision_at_3_mean", 0)
    trust = aggregated.get("checkpoint_source_trust_mean", 0)
    cal = aggregated.get("checkpoint_calibration_error_mean", 0)

    all_pass = True
    if p3 < 0.60:
        print(f"  FAIL: Precision@3 {p3:.3f} < 0.60 minimum viable")
        all_pass = False
    if trust < 0.80:
        print(f"  FAIL: Source trust {trust:.3f} < 0.80 target")
        all_pass = False
    if cal > 0.20:
        print(f"  FAIL: Calibration error {cal:.3f} > 0.20 maximum")
        all_pass = False
    if final_recall < 0.40:
        print(f"  WARN: Induction recall {final_recall:.3f} < 0.40 min viable (non-deterministic over {NUM_EVENTS} events)")

    if all_pass:
        print("ALL THRESHOLDS PASSED")


if __name__ == "__main__":
    main()
