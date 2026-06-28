# Causal Prediction PoC — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development or executing-plans to implement task-by-task.

**Goal:** Build an automated causal prediction PoC that exercises the architecture pipeline — event ingest through RememberOperator, inductive causal rule learning, promotion gate validation, and CausalInference evaluation.

**Architecture:** Two small extensions to existing code (RememberOperator qualifiers, Inductor causal pattern detection) + a PoC script that drives the full cycle: synthetic events → pipeline → storage → induction → promotion → prediction → metrics.

**Tech Stack:** Pure Python 3.11+, stdlib only, SQLite backend.

---

### Task 1: Add `qualifiers` support to RememberOperator

**Files:**
- Modify: `cemm/operators/remember.py:25` (add params parse)
- Modify: `cemm/operators/remember.py:27-43` (pass to Claim)

- [ ] **Step 1: Read current file to confirm line numbers**

Run: `cat -n cemm/operators/remember.py`
Expected: `qualifiers` is not in the params or Claim constructor.

- [ ] **Step 2: Add qualifiers parsing and Claim wiring**

In `remember.py`, add after `domain = ctx.params.get("domain", "general")`:

```python
        qualifiers = ctx.params.get("qualifiers", {})
```

Then in the `Claim(…)` constructor, add `qualifiers=qualifiers,` after `object_entity_id=object_entity_id,`:

```python
        claim = Claim(
            id=uuid.uuid4().hex[:16],
            subject_entity_id=subject_id,
            predicate=predicate,
            object_value=object_value,
            object_entity_id=object_entity_id,
            qualifiers=qualifiers,
            evidence_signal_ids=[ctx.input_signal.id],
            ...
        )
```

- [ ] **Step 3: Verify the file parses**

Run: `python -c "from cemm.operators.remember import RememberOperator; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Run existing tests to confirm no regression**

Run: `python -m pytest tests/ -x -q --tb=short`
Expected: 91 passed

---

### Task 2: Add `_find_causal_patterns()` to the Inductor

**Files:**
- Modify: `cemm/learning/inductor.py` (add method, wire into `maybe_induct`)

- [ ] **Step 1: Add the new method to `inductor.py`**

Append to the `Inductor` class (before the end of file), and wire it into `maybe_induct`:

In `maybe_induct`, add after line 21:
```python
        candidates.extend(self._find_causal_patterns(domain))
```

Add the new method:
```python
    def _find_causal_patterns(self, domain: str | None = None) -> list[Model]:
        recent = self._store.claims.find_active(200)
        from collections import defaultdict
        groups: dict[tuple[str, str | None], list[Claim]] = defaultdict(list)
        for claim in recent:
            if domain and claim.domain != domain:
                continue
            if "outcome" not in claim.qualifiers:
                continue
            key = (claim.predicate, claim.object_entity_id)
            groups[key].append(claim)

        candidates: list[Model] = []
        for (predicate, obj_id), claims_list in groups.items():
            if len(claims_list) < self._feedback_threshold:
                continue
            existing = self._store.models.find_by_name(predicate)
            if any(
                m.kind == ModelKind.CAUSAL_RULE
                and m.status == ModelStatus.ACTIVE
                and obj_id in " ".join(m.preconditions)
                for m in existing
            ):
                continue
            outcome_counts: dict[str, int] = {}
            for c in claims_list:
                val = c.qualifiers.get("outcome", "unknown")
                outcome_counts[val] = outcome_counts.get(val, 0) + 1
            majority_outcome = max(outcome_counts, key=outcome_counts.get)
            total = len(claims_list)
            majority_count = outcome_counts[majority_outcome]
            consistency = majority_count / total
            if consistency < 0.8:
                continue
            confidence = min(1.0, 0.3 + 0.5 * consistency + 0.2 * (total / 20))
            signal_ids: list[str] = []
            claim_ids: list[str] = []
            for c in claims_list:
                signal_ids.extend(c.evidence_signal_ids)
                claim_ids.append(c.id)
            model = Model(
                id=uuid.uuid4().hex[:16],
                kind=ModelKind.CAUSAL_RULE,
                name=predicate,
                description=f"Causal rule: {predicate} {obj_id} -> {majority_outcome} (seen {total}x, {consistency:.0%} consistent)",
                preconditions=[f"object:{obj_id}"],
                effects=[f"outcome:{majority_outcome}"],
                evidence_signal_ids=list(set(signal_ids)),
                related_claim_ids=claim_ids,
                confidence=confidence,
                trust=0.7,
                status=ModelStatus.CANDIDATE,
                created_at=time.time(),
                updated_at=time.time(),
                permission=claims_list[0].permission if claims_list else None,
            )
            self._store.models.put(model)
            candidates.append(model)
        return candidates
```

- [ ] **Step 2: Verify the file parses**

Run: `python -c "from cemm.learning.inductor import Inductor; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Run existing tests to confirm no regression**

Run: `python -m pytest tests/ -x -q --tb=short`
Expected: 91 passed

---

### Task 3: Write tests for causal pattern detection

**Files:**
- Create: `tests/test_inductor_causal.py`

- [ ] **Step 1: Write test for basic causal rule detection**

Create `tests/test_inductor_causal.py`:

```python
from __future__ import annotations
from cemm.store.store import Store
from cemm.learning.inductor import Inductor
from cemm.types.claim import Claim, ClaimStatus
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.permission import Permission
from cemm.types.model import ModelKind, ModelStatus
import time, uuid


def _make_claim(store: Store, predicate: str, obj_id: str, outcome: str, domain: str = "causal") -> Claim:
    now = time.time()
    signal = Signal(
        id=uuid.uuid4().hex[:16],
        kind=SignalKind.INPUT,
        source_id="test",
        source_type=SourceType.USER,
        content=f"test {predicate}",
        observed_at=now,
        context_id="test",
        salience=0.5,
        trust=0.5,
        permission=Permission.public(),
    )
    store.signals.put(signal)
    claim = Claim(
        id=uuid.uuid4().hex[:16],
        subject_entity_id="alice",
        predicate=predicate,
        object_entity_id=obj_id,
        object_value=obj_id,
        qualifiers={"outcome": outcome},
        evidence_signal_ids=[signal.id],
        source_id="test",
        domain=domain,
        confidence=0.7,
        trust=0.7,
        salience=0.3,
        status=ClaimStatus.ACTIVE,
        observed_at=now,
        updated_at=now,
        permission=Permission.public(),
    )
    store.claims.put(claim)
    return claim


class TestCausalPatternInduction:
    def test_detects_repeated_consistent_pattern(self):
        store = Store(":memory:")
        inductor = Inductor(store, feedback_threshold=3)
        for _ in range(5):
            _make_claim(store, "query", "postgres", "success")
        candidates = inductor._find_causal_patterns(domain="causal")
        assert len(candidates) == 1
        model = candidates[0]
        assert model.kind == ModelKind.CAUSAL_RULE
        assert model.name == "query"
        assert "object:postgres" in model.preconditions
        assert "outcome:success" in model.effects

    def test_skips_below_threshold(self):
        store = Store(":memory:")
        inductor = Inductor(store, feedback_threshold=5)
        for _ in range(3):
            _make_claim(store, "query", "postgres", "success")
        candidates = inductor._find_causal_patterns(domain="causal")
        assert len(candidates) == 0

    def test_skips_inconsistent_pattern(self):
        store = Store(":memory:")
        inductor = Inductor(store, feedback_threshold=3)
        for _ in range(3):
            _make_claim(store, "query", "postgres", "success")
        _make_claim(store, "query", "postgres", "failure")
        candidates = inductor._find_causal_patterns(domain="causal")
        assert len(candidates) == 0

    def test_skips_without_outcome_qualifier(self):
        store = Store(":memory:")
        inductor = Inductor(store, feedback_threshold=3)
        now = time.time()
        for _ in range(5):
            claim = Claim(
                id=uuid.uuid4().hex[:16],
                subject_entity_id="alice",
                predicate="query",
                object_entity_id="postgres",
                object_value="postgres",
                evidence_signal_ids=[uuid.uuid4().hex[:16]],
                source_id="test",
                domain="causal",
                confidence=0.7,
                trust=0.7,
                salience=0.3,
                status=ClaimStatus.ACTIVE,
                observed_at=now,
                updated_at=now,
                permission=Permission.public(),
            )
            store.claims.put(claim)
        candidates = inductor._find_causal_patterns(domain="causal")
        assert len(candidates) == 0

    def test_respects_domain_filter(self):
        store = Store(":memory:")
        inductor = Inductor(store, feedback_threshold=3)
        for _ in range(5):
            _make_claim(store, "query", "postgres", "success", domain="other")
        candidates = inductor._find_causal_patterns(domain="causal")
        assert len(candidates) == 0
        candidates_all = inductor._find_causal_patterns(domain=None)
        assert len(candidates_all) == 1

    def test_skips_already_active_rule(self):
        store = Store(":memory:")
        inductor = Inductor(store, feedback_threshold=3)
        from cemm.types.model import Model
        existing = Model(
            id="existing_causal",
            kind=ModelKind.CAUSAL_RULE,
            name="query",
            description="Existing",
            preconditions=["object:postgres"],
            effects=["outcome:success"],
            confidence=0.9,
            trust=0.7,
            status=ModelStatus.ACTIVE,
            created_at=time.time(),
            updated_at=time.time(),
        )
        store.models.put(existing)
        for _ in range(5):
            _make_claim(store, "query", "postgres", "success")
        candidates = inductor._find_causal_patterns(domain="causal")
        assert len(candidates) == 0

    def test_wired_into_maybe_induct(self):
        store = Store(":memory:")
        inductor = Inductor(store, feedback_threshold=3)
        for _ in range(5):
            _make_claim(store, "query", "postgres", "success")
        candidates = inductor.maybe_induct(domain="causal")
        causal_candidates = [m for m in candidates if m.kind == ModelKind.CAUSAL_RULE]
        assert len(causal_candidates) == 1
```

- [ ] **Step 2: Run the new tests**

Run: `python -m pytest tests/test_inductor_causal.py -v --tb=short`
Expected: 7 passed

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest tests/ -x -q --tb=short`
Expected: 98 passed

---

### Task 4: Build the PoC training script

**Files:**
- Create: `scripts/poc_causal_train.py`

- [ ] **Step 1: Write the PoC script**

Create `scripts/poc_causal_train.py`:

```python
from __future__ import annotations
import math
import random
import time
import uuid
from collections import defaultdict

from cemm.store.store import Store
from cemm.registry import Registry, RegistryEntry
from cemm.kernel.pipeline import Pipeline
from cemm.operators.remember import RememberOperator
from cemm.operators.base import OperatorContext
from cemm.learning.online import OnlineLearner
from cemm.learning.inductor import Inductor
from cemm.learning.promotion import ModelPromoter
from cemm.types.signal import Signal, SignalKind, SourceType
from cemm.types.entity import Entity, EntityType
from cemm.types.claim import Claim, ClaimStatus
from cemm.types.context_kernel import (
    ContextKernel, WorldState, UserState, TimeState,
    ConversationState, GoalState, MemoryState, Budget,
)
from cemm.types.permission import Permission
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


def generate_event_stream(num_events: int, alias_noise: float = 0.1) -> list[dict]:
    random.seed(SEED)
    stream: list[dict] = []
    for t in range(num_events):
        actor = zipf_choices(ACTORS, 1)[0]
        action = random.choice(ACTIONS)
        obj = random.choice(OBJECTS)
        outcome: str
        if (action, obj) in GROUND_TRUTH_DETERMINISTIC:
            outcome = GROUND_TRUTH_DETERMINISTIC[(action, obj)]
        elif (action, obj) in GROUND_TRUTH_PROBABILISTIC:
            expected, prob = GROUND_TRUTH_PROBABILISTIC[(action, obj)]
            outcome = expected if random.random() < prob else random.choice(OUTCOMES)
        else:
            outcome = random.choice(OUTCOMES)
        event: dict = {
            "actor": actor,
            "action": action,
            "object": obj,
            "outcome": outcome,
            "timestamp": t,
            "source_id": f"source_{t % 5}",
        }
        if random.random() < alias_noise:
            event["alias"] = f"{actor}_{t % 3}"
        stream.append(event)
    return stream


def build_kernel(now: float) -> ContextKernel:
    return ContextKernel(
        id=uuid.uuid4().hex[:16],
        world=WorldState(),
        user=UserState(),
        time=TimeState(now=now, bucket="afternoon"),
        conversation=ConversationState(session_id="poc_train", turn_index=0, recent_signal_ids=[]),
        goal=GoalState(),
        memory=MemoryState(),
        permission=Permission.public(),
        budget=Budget(),
    )


def evaluate_checkpoint(
    store: Store,
    inductor: Inductor,
    promoter: ModelPromoter,
    events_processed: int,
) -> dict:
    metrics: dict = {
        "events_processed": events_processed,
    }

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

    all_ground_truth = {}
    all_ground_truth.update(GROUND_TRUTH_DETERMINISTIC)
    for (action, obj), (expected, _) in GROUND_TRUTH_PROBABILISTIC.items():
        all_ground_truth[(action, obj)] = expected

    correct = 0
    discovered = set()
    for (action, obj), expected_outcome in all_ground_truth.items():
        for rule in active_rules:
            if rule.name == action and f"object:{obj}" in rule.preconditions:
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


def run_trial(seed: int, num_events: int, alias_noise: float = 0.1) -> dict:
    random.seed(seed)
    store = Store(":memory:")
    registry = Registry()
    pipeline = Pipeline(store, registry)

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

    stream = generate_event_stream(num_events, alias_noise)
    learner = OnlineLearner(store.source_trust, store.self_store, store.claims)
    inductor = Inductor(store, feedback_threshold=5)
    promoter = ModelPromoter(store)
    remember_op = RememberOperator()
    metrics: dict = {
        "latencies_ms": [],
        "checkpoints": [],
    }

    event_counters: dict[tuple, int] = defaultdict(int)

    for i, event in enumerate(stream):
        t0 = time.perf_counter()

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

        obj_entity = store.entities.get(event["object"])
        if obj_entity is None:
            obj_entity = Entity(
                id=event["object"],
                type=EntityType.OBJECT,
                name=event["object"],
                aliases=[event["object"].lower()],
                confidence=0.7,
                created_from_signal_id=signal.id,
                created_at=now,
                updated_at=now,
            )
            store.entities.put(obj_entity)

        kernel = build_kernel(now)

        ctx = OperatorContext(
            kernel=kernel,
            input_signal=signal,
            store=store,
            registry=registry,
            selected_claim_ids=[],
            selected_model_ids=[],
            params={
                "subject_entity_id": event["actor"],
                "predicate": event["action"],
                "object_entity_id": event["object"],
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

        key = (event["action"], event["object"], event["outcome"])
        event_counters[key] += 1

        t1 = time.perf_counter()
        metrics["latencies_ms"].append((t1 - t0) * 1000.0)

        if (i + 1) % CHECKPOINT_INTERVAL == 0 or i == num_events - 1:
            cp = evaluate_checkpoint(store, inductor, promoter, i + 1)
            metrics["checkpoints"].append(cp)

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

    return result


def print_results(agg: dict) -> None:
    print("=" * 65)
    print("CEMM Causal Prediction PoC — Phase 1 Results")
    print("=" * 65)
    rows = [
        ("Latency (mean)", f"{agg.get('latency_mean_ms', 0):.1f}ms"),
        ("Candidates created (avg)", f"{agg.get('final_candidates_created', 0):.1f}"),
        ("Promoted (avg)", f"{agg.get('final_promoted', 0):.1f}"),
        ("Active rules (avg)", f"{agg.get('final_active_rules', 0):.1f}"),
        ("Prediction accuracy", f"{agg.get('final_prediction_accuracy', 0):.3f}"),
        ("Ground truth recall", f"{agg.get('final_recall', 0):.3f}"),
        ("Promoted model confidence", f"{agg.get('final_mean_confidence', 0):.3f}"),
    ]
    for label, value in rows:
        print(f"  {label:.<48s} {value:>8s}")
    print()
    print("Targets:")
    print(f"  Precision (min viable .80):     {agg.get('final_prediction_accuracy', 0):.3f}")
    print(f"  Recall (min viable .40):        {agg.get('final_recall', 0):.3f}")
    print(f"  Latency (max 50ms):             {agg.get('latency_mean_ms', 0):.1f}ms")


def main() -> None:
    print(f"CEMM Causal Prediction PoC — {NUM_RUNS} runs x {NUM_EVENTS} events (seed={SEED})")
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
```

- [ ] **Step 2: Run the PoC script**

Run: `python scripts/poc_causal_train.py`
Expected: Script runs 3 trials, reports metrics including recall >= 0.40 (10 ground truth rules, at least ~4 should be discovered in 200 events with 5+ observations each).

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest tests/ -x -q --tb=short`
Expected: All tests pass (98+)

---

### Task 5: Final verification

- [ ] **Step 1: Run the PoC with extended parameters for stability**

Run: `python scripts/poc_causal_train.py`
Expected: Results show non-zero candidates, promotions, and predictions across all runs.

- [ ] **Step 2: Full test suite**

Run: `python -m pytest tests/ -x -q --tb=short`
Expected: All pass.

- [ ] **Step 3: Summary of results**

Check:
- Causal rules are discovered (final_candidates_created > 0)
- Some rules are promoted (final_promoted > 0)
- Prediction accuracy > 0 (active rules produce correct predictions)
- Ground truth recall tracks discovery rate
- Latency < 50ms
