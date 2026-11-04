# G5 v5 evaluator correction and split-dependence disclosure (2026-11-04)

**Integrity status:** Raw challenge collection is immutable at `0988a525a8c315f4ba245400ab81d438857717d8`, built from the published TRAIN fit at `4fd21dee3be772c51c96e5aebdb516e481f981f6`. Neither model, fit, generator, raw forecast, case inventory nor frozen decision threshold changes in this correction.

## Original scoring defect — retained

The first saved-bank evaluator run at [GitHub Actions 41841900837](https://github.com/robosys-labs/cemm/actions/runs/41841900837) ran 1,217 software tests successfully but produced an invalid `pre_confident_pairs=96/96` in every condition. The collector stores counterfactual tuples `(saved_p, decoded_decision, evaluator_truth)`. Its scorer mistakenly counted `left[2] is not None`, which checks the always-present hidden **truth** rather than `left[1] is not None`, the model's **decision**. The preconfidence aggregate is invalid; all other published metrics remain provisional until independent rescore.

Before correction, a direct, separate read of sealed `raw/nand-7.json` found **0/192** confident pre-probe probabilities; their range was **0.1005682456–0.8993599447**, with exact equality across both members of every paired public prefix. The earliest defect is evaluator indexing, not a learned-state or generator change.

**Correction:** replace only the wrong tuple index and add an invariant that counts confident PRE predictions directly from the immutable raw probability field. Keep the original failed evaluator log and run unchanged. No fit, retraining, new TEST selection, new challenge generation, threshold adjustment or model retry is authorized by this fix.

## Additional confound discovered from the published source

`temporal_task_v5.py` generates its SHA-256 disturbance stream from `SALT[split]`, a six-triple index `k`, and enumerated case index `idx`, **without law or seed**. Consequently the ten reported law/seed conditions reuse the same noise and hidden scenario pattern (although G3 conditional probabilities vary). Their equal goal/query counts are therefore **dependent views**, not ten independent environmental replications. The opened challenge cannot be repaired by changing the salt or assigning new seeds; doing so would create a **new prospective study** with a separately frozen task and new challenge. The present result must be labeled **STOP_CONFOUNDED_FOR_INDEPENDENT_REPLICATION**, even if its bounded action comparisons are useful diagnostics.

The existing G5 v1 rule remains selected until new evidence independently establishes a simpler or more useful learned correction mechanism.
