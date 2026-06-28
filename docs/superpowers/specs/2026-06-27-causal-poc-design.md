# Causal Prediction PoC — Design Spec

Version: 1.0
Status: draft
Purpose: demonstrate the ERCA v2.0 architecture's causal learning and prediction capabilities through an automated, deterministic benchmark.

## 1. Scenario

The system observes a stream of action-outcome events through the full architecture pipeline. Each event has the form "actor performs action on object → outcome". After observing repeated patterns (e.g., `query postgres` always → `success`, `delete k8s` always → `failure`), the Inductor creates candidate `Model(kind=CAUSAL_RULE)` records, the promotion gate validates them, and the CausalInference engine uses promoted models to predict outcomes for novel queries.

This exercises the architecture's full learning-to-prediction loop: §2 (claims before generation, learning after outcome), §13 (causal world model + simulation), §14 (structural learning + promotion path), §20 (online learning + background induction).

## 2. Ground Truth

Ten causal rules, embedded in the event generator:

### 2.1 Deterministic (100% consistent, 5 rules)
| Action | Object | Outcome |
|--------|--------|---------|
| query | postgres | success |
| delete | k8s | failure |
| save | favorite_db | success |
| backup | s3 | success |
| create | docker | success |

### 2.2 Probabilistic (80% consistent, 5 rules)
| Action | Object | Outcome |
|--------|--------|---------|
| update | mysql | success |
| delete | mongo | failure |
| config | redis | success |
| train | lambda | success |
| test | sqlite | success |

Noise events (random action+object+outcome) fill the remaining probability mass.

## 3. Architecture Changes

Three small, backward-compatible changes:

### 3.1 `RememberOperator` — accept `qualifiers` in params

In `execute()`, read `ctx.params.get("qualifiers", {})` and pass to the `Claim` constructor. This allows storing outcome metadata as a claim qualifier (e.g., `{"outcome": "success"}`) without changing the operator's contract — qualifiers is optional and defaults to empty dict.

Architecture basis: §5 defines `qualifiers: Record<string, string|number|boolean|null>` on claims. This is the standard place for structured metadata like outcome.

### 3.2 `Inductor._find_causal_patterns()` — detect causal rule candidates

Add a new method that:
1. Scans the most recent N active claims (default 200)
2. Filters to claims with an `outcome` qualifier
3. Groups by `(predicate, object_entity_id)`
4. For groups with count >= `feedback_threshold` (default 5) and outcome consistency >= 80%:
   - majority_outcome = most common outcome value in the group
   - consistency_ratio = majority_count / total_count
   - Creates `Model(kind=CAUSAL_RULE)` with:
     - `name` = predicate (the action)
     - `preconditions` = `[f"object:{object_entity_id}"]`
     - `effects` = `[f"outcome:{majority_outcome}"]`
     - `confidence` = `min(1.0, 0.3 + 0.5 * consistency_ratio + 0.2 * (count / 20))`
     - `trust` = `0.7`
     - `evidence_signal_ids` = union of signal IDs from the group's claims
     - `related_claim_ids` = claim IDs from the group
5. Skips groups where an active CAUSAL_RULE model with matching name+preconditions already exists

Architecture basis: §14 says "The Inductor may create candidate models for: causal_rule", §20 says "repeated unsupported structure" triggers induction. The method stays within the structural learning loop: observe repeated pattern → create candidate Model (remaining steps are handled by the promotion gate and runtime).

### 3.3 `promoter.can_promote()` — adjust for causal rules

No change needed. The existing gate already validates:
- `model.status == CANDIDATE` ✓
- `model.confidence >= 0.6` — causal models start at ~0.7-0.95 ✓
- `model.evidence_signal_ids` non-empty ✓
- `model.permission.may_store` — default permission allows ✓

Architecture basis: §14 promotion requirements.

## 4. PoC Script (`scripts/poc_causal_train.py`)

### 4.1 Event Generator
- 200 events total
- 8 actors (zipf distribution, alpha=1.5)
- 10 actions, 10 objects
- 10% alias noise (alternate actor names)
- 5 source IDs (deterministic mapping: `source_{t % 5}`)
- Events follow ground truth rules with specified consistency; remaining are random

### 4.2 Training Loop

```
for each event in stream:
    t0 = time.perf_counter()

    # Phase 1: Ingest through architecture
    signal = Signal(... event metadata ...)
    store.signals.put(signal)

    entity = store.entities.get(actor) or create Entity
    pipeline = Pipeline.run(signal.content)  # builds ContextKernel

    # Phase 2: Store claim via RememberOperator
    ctx = OperatorContext(kernel, signal, store, registry, params={
        "subject_entity_id": actor,
        "predicate": action,
        "object_entity_id": object,
        "object_value": object,
        "domain": "causal",
        "qualifiers": {"outcome": outcome},
    })
    op_result = RememberOperator().execute(ctx)
    claim_id = op_result.new_claim_ids[0]

    # Phase 3: Online learning
    learner.record_outcome(source_id, "causal", success=(outcome=="success"))
    learner.update_claim_confidence(claim_id, feedback_correct=(outcome=="success"))

    t1 = time.perf_counter()
    latency = (t1 - t0) * 1000.0

    # Phase 4: Checkpoint evaluation
    if (i+1) % CHECKPOINT_INTERVAL == 0:
        evaluate_checkpoint(i+1)
```

### 4.3 Checkpoint Evaluation

```
def evaluate_checkpoint(events_processed):
    # Induction
    inductor.set_threshold(5)
    candidates = inductor.maybe_induct(domain="causal")

    # Promotion
    promoted_ids = []
    for model in candidates:
        if model.kind == ModelKind.CAUSAL_RULE:
            ok, msg = promoter.can_promote(model)
            if ok:
                prom_ok, _ = promoter.promote(model.id)
                if prom_ok:
                    promoted_ids.append(model.id)

    # Causal prediction scoring
    active_rules = store.models.find_by_kind("causal_rule", "active")
    for (action, object), expected_outcome in GROUND_TRUTH.items():
        for rule in active_rules:
            if rule.name == action and f"object:{object}" in rule.preconditions:
                predicted = [e for e in rule.effects if e.startswith("outcome:")]
                correct = any(f"outcome:{expected_outcome}" == e for e in predicted)

    # Metrics
    precision = correct_predictions / max(len(active_rules), 1)
    recall = rules_discovered / len(GROUND_TRUTH)
    induction_recall = rules_with_candidates / len(GROUND_TRUTH)
    promotion_rate = len(promoted_ids) / max(len(candidates), 1)
```

### 4.4 Metrics Collected

| Metric | Definition |
|--------|-----------|
| Causal precision | % of active CAUSAL_RULE models whose predictions match ground truth |
| Causal recall | % of ground truth rules discovered as active models |
| Induction recall | % of ground truth rules with candidate models created |
| Promotion acceptance | % of candidates passing promotion gate |
| Promoted model confidence | Mean confidence of promoted models |
| Per-event latency | Mean ms per event (ingest + store + learn) |
| Source trust convergence | Mean trust across all causal-domain sources |

### 4.5 Expected Results

| Metric | Minimum Viable | Target |
|--------|---------------|--------|
| Causal precision | >0.80 | >0.95 |
| Causal recall | >0.40 | >0.70 |
| Induction recall | >0.60 | >0.90 |
| Promotion acceptance | 100% valid | 100% valid |
| Per-event latency | <50ms | <10ms |

## 5. Success Criteria

The PoC proves:

1. **Causal rules can be learned from repeated observations**: the Inductor detects (predicate, object, outcome) patterns and creates CAUSAL_RULE candidates
2. **The promotion gate correctly validates causal candidates**: only well-evidenced, high-confidence models are promoted
3. **The CausalInference engine uses promoted rules**: once promoted, `predict()` returns effects matching the learned rules
4. **Source trust converges with outcomes**: sources with consistent outcomes get higher trust
5. **The full architecture pipeline works**: Signal → ContextKernel → RememberOperator → claims → induction → promotion → prediction

## 6. Non-Goals

- Not a production training system
- No LLM calls, neural models, or vector embeddings
- No interactive UI or REPL
- No multi-turn conversation
- No recursive reflection
- No synthesis router (predictions are evaluated directly, not NLG-synthesized)
- No frame rules or temporal reasoning
- No changes to existing test suite behavior
