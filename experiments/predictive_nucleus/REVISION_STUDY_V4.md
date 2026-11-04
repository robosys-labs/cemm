# G5 v4 — post-hoc TRAIN switch-boundary feasibility audit

**Parent:** PR #88, `14556a91c724476b2c3407b95d3fe80890b4d620`. **Purpose:** localize the lower-bound limitation observed after the *published* v3 result, not rescue v3 or claim fresh unseen generalization. This is a separate **post-hoc TRAIN-only diagnostic**.

## Immutable objects

Import the unchanged `revision_outcome.posterior`, `decision`, `revision_objective_v3.train_rows` and original underlying TRAIN physical catalogues. Do not alter the G3 world/language forecasts, the original v1 memory rule, v2/v3 fitted artifacts, source IDs or the registered .95 confidence threshold. All five inherited seeds and both NAND/NOR laws mandatory. The 960 selected-payoff TRAIN observations and 96 independent-of-truth public prefix IDs per condition stay exactly the same.

## Newly registered subgrid

Use this **fixed, ordered** grid and no gradient tuning:
`[0.00001, 0.000025, 0.00005, 0.0001, 0.0002, 0.0004, 0.0006, 0.0008, 0.001, 0.00125, 0.0015, 0.00175, 0.002, 0.00225, 0.0025]`.

The final value is the v3 boundary control. For every rate, evaluate the same 192 PRE, 192 POST, 576 RETAIN decisions per condition. Report pre-confidence on matched opposite-truth pairs, wrong/confident/abstaining post and retained decisions, and balanced payoff NLL. The evaluator may use known meanings solely to **diagnose** feasibility. Do not select a production/fitted parameter by consulting evaluator labels.

The joint feasibility rule remains: no confident PRE decisions, all 192 POST and 576 RETAIN confident and correct. Report per-seed feasible rates and their intersection across all ten conditions. If no rate works, say only `NO_FEASIBLE_RATE_IN_REGISTERED_SUBGRID`, not a proof against every real-valued rate. If one works, call it `BOUNDED_REPRESENTATION_FEASIBLE_ON_TRAIN`, not a scientific admission or learned fit.

## Additional no-information temporal diagnostic

For existing TRAIN prefixes, append an authenticated physical receipt whose likelihoods are exactly equal `(.5,.5)`, with a fresh evidence ID and a later event timestamp. Compare v2 posterior *before and after* at each subgrid rate. Report maximum absolute drift and the count of changed .95-confidence decisions. This is a **time-transition sensitivity check**; a model that treats each new timestamp as a possible state transition may legitimately drift even without discriminating observations, so do not automatically call it a bug. Do not introduce an elapsed-time clock or change the filter in this study.

## Sequence and decision

1. Freeze this text before running or authoring the new audit source.
2. Publish a single standalone TRAIN-only auditor plus isolated invariant test; do not modify any previously retained source or thresholds.
3. Publish the full per-condition grid and adverse cases from a completed hosted run, including software failures.
4. If the subgrid has no joint solution, the next study may compare one minimal temporal-exception latent alternative against this full simple baseline at matched data/compute. If a solution exists, first test whether a **payoff-only objective** can select it without interpretation labels, then use a newly frozen challenge. Do not advance to G6 or merge production based on a diagnostic.
