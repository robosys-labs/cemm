# Temporal v1 post-score TRAIN receipt attribution

The original study is closed with `REVISE_NATIVE_TEMPORAL_UPDATER`; its budget,
weights, held-out records, gates and decision remain unchanged. This is a
post hoc diagnostic of its ten final checkpoints, not a new challenge or retry.
Publish this protocol, the tracer source and its exact TRAIN projection before
executing the tracer. Execute the fixed trace once; audit its saved arrays.

## Question and fixed observations

Does a tested-word claim or physical receipt damage recall of the already
taught protected word? Locate the earliest responsible recurrent update before
choosing a new mechanism. The saved held-out omission control motivated this
question; no held-out record enters the tracer or a training update.

Use all 2,048 existing TRAIN histories and all five seeds, both native and flat
arms. Both retain their original final weights, float64 CPU and one thread.
No optimizer, gradient update, new data, simulator, evaluator, model selection,
checkpoint selection, seed selection, hyperparameter sweep or TEST tuning.

The shared prepared public file physically contains both splits. The separate
`prepare-input` command selects only its hash-bound `train` array and the native
projections needed by those records. The actual `trace` command opens only this
published TRAIN projection, frozen checkpoint files, source files and manifests;
it never opens the original public file, TEST answers or evaluator records.

## Recorded sequence and measurements

For each history retain forecasts after: (1) eight physical parent teaching
receipts, (2) the tested-word claim, (3) its first physical probe, and (4) its
second physical probe. At every state forecast the same TRAIN-observed t=2
target and protected endpoints. Labels score forecasts only; they are not
inserted into recurrent state. The latter two physical receipts enter only at
their scheduled step. No parent-scope t=2 target is fabricated.

Report exact accuracy, uncapped NLL, multiclass Brier and paired newly-wrong,
repaired and NLL-worsened IDs across each transition. Preserve every raw
eight-endpoint forecast. Report all histories together and disjoint groups by
law, public target scope and first-probe scope. Second-probe scope is the other
scope by the original schedule. Hidden temporal causes are not available.

"Earliest" means the first damaging post-teaching update. Count protected
predictions already wrong after teaching separately. For teaching-correct
cases, retain the first regression stage and whether the error survives the
second probe; keep adjacent-stage regressions and repairs for every case.
The protected endpoint remains unchanged, whereas target metrics forecast a
future t=2 outcome. Intermediate protected forecasts were not directly
supervised by the original fit. A stage-local error does not distinguish
hidden-memory interference from a state-dependent readout failure.

Verify prepared/history/source/checkpoint hashes and exact loaded weight
fingerprints, then verify unchanged weights and absent parameter gradients.
Retain diagnostic source commit, input hash, checkpoint identities and raw
artifact hashes. These observations identify interference on TRAIN; they do
not prove insufficient capacity, identify an optimal loss, or establish a new
generalization gain. No new scientific pass threshold is introduced.

## Stopping decision

Close this diagnostic after the single fixed trace and saved-record audit.
If damage begins at a particular receipt, name that update and preserve the
counterexamples. If the expected pattern is absent on TRAIN, report that gap
without sampling more cases or rerunning TEST. Do not automatically extend
training or enlarge the recurrent state. A later candidate requires its own
prospective comparison; G5 admission and G6–G8 remain open.
