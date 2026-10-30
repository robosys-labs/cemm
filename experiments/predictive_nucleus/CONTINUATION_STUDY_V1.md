# Continuation study v1

This public, prefit-frozen development comparison follows
[`continuation_protocol_v1.json`](continuation_protocol_v1.json) and its SHA-256 lock.
It tests whether the untied shared learner improves on the flat GRU at equal
parameters and completed training exposure on fixed post-acquisition queries.
**G1 remains NOT ADMITTED.** The original protocol, 95% target, archived results,
and closed studies remain in force. This prospective design makes no outcome claim.

## Task and evidence boundary

Train, selection, and calibration use one or two total contacts. Evaluation adds
chain, fork, cycle, and disjoint schedules with three to five total contacts;
entity counts remain 3–6. The first ordinary contact is informative acquisition,
counted within that total. Its precontact pair is selected from 01/10/11 after
any leading set, before drawing the persistent hidden mode. Complete feedback
through acquisition makes every later contact identifiable under the declared
two-mode law. Those later contact indices are the prospective query set.

Single-contact episodes have no continuation query; the first held-out self-contact
is a separate diagnostic without a reversed duplicate. All actions remain in
collection and diagnostics; acquisition MAP accuracy is not a query
competence gate. Its irreducible proper-score floors are ln(2) NLL and 0.5 Brier.

There is no intercontact reset. Development feedback is complete; evaluation
has 0–3 exogenous missing bit-events after acquisition, with self-contact fully
observed. Masks and blueprint selection precede actual mode/outcomes. Reversed
views share mode, anchor, IDs, masks, and lineage, and remain one physical draw.
Global canonical blueprint deduplication excludes cross-split copies and renamed
or globally reversed derivatives; atomic contexts and action templates may repeat.

Planned physical draws/views: train 64/128, selection 32/64, calibration 32/64,
evaluation 168/320. Evaluation has 32 in-family and 672 held-out continuation
queries, plus 16 self queries. The evaluator-only oracle is conditional on the declared law.

## Fixed fit and controls

There are **15 neural fits**: shared, memory-reset, and flat, each at seeds
`[7, 11, 23, 37, 53]`. Each has 562 parameters. Shared/reset start from identical
tensors; flat uses the same seed labels with its own architecture. Each receives
the same observed training tape for 128 full-dataset updates, batch size 32,
learning rate 0.02, existing Adam defaults, and observed joint-event NLL.
The final prescribed checkpoint is used. There is no tuning, selection search,
calibration fit, or retry; selection/calibration tapes are reserved and unused.

Untrained shared, no-change, and four empirical controls (local, contact,
first-contact, prefix) accompany the comparison. Each empirical control is fit
once and reused under five collection seed labels; these are not independent
empirical replicates. Each neural fit has a 300 CPU-second cap; incomplete exposure
forces STOP. Bounds remain 64 live paths and 512 candidate expansions.

## Recorded execution, with two committed freezes

This attempt is closed; its [results and decision](CONTINUATION_DECISION_V1.md)
are retained. The commands below document the executed sequence. Any new fitting
requires a separately frozen study scope; a new output path is not a v1 retry.

Run from the repository root in the pinned Python 3.13.16, PyTorch 2.10.0+cpu,
NumPy 2.3.5 environment. The runner enforces float64, one thread, deterministic
algorithms, exact source/artifact hashes, and a clean committed checkout for
fit/bind/collect. Every output directory must be new. Preserve a failed attempt;
changing paths does not authorize a retry.

```sh
set -eu
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0
cemm_python=/tmp/cemm-active-venv/bin/python
cemm_module=experiments.predictive_nucleus.continuation_run
cemm_data=/tmp/cemm-continuation-v1-data
cemm_fit=/tmp/cemm-continuation-v1-fit
cemm_results=/tmp/cemm-continuation-v1-results
cemm_saved_fit=experiments/predictive_nucleus/data/continuation-fit-v1
cemm_saved_results=experiments/predictive_nucleus/results/continuation-v1
"$cemm_python" -m "$cemm_module" prepare --output "$cemm_data"
cp "$cemm_data/assets.json.xz" experiments/predictive_nucleus/data/continuation-assets-v1.json.xz
cp "$cemm_data/prefit.json" experiments/predictive_nucleus/data/continuation-prefit-v1.json
git add experiments/predictive_nucleus/continuation_*.py experiments/predictive_nucleus/continuation_protocol_v1.json
git add experiments/predictive_nucleus/snapshots/continuation_protocol_v1.sha256
git add experiments/predictive_nucleus/tests/test_continuation_*.py experiments/predictive_nucleus/CONTINUATION_STUDY_V1.md
git add experiments/predictive_nucleus/data/continuation-assets-v1.json.xz experiments/predictive_nucleus/data/continuation-prefit-v1.json
git commit -m "Freeze continuation v1 protocol, sources and data before fitting"

"$cemm_python" -m "$cemm_module" fit --data "$cemm_data" --output "$cemm_fit"
"$cemm_python" -m "$cemm_module" bind --data "$cemm_data" --fitted "$cemm_fit"
test ! -e "$cemm_saved_fit"
cp -R "$cemm_fit" "$cemm_saved_fit"
git add "$cemm_saved_fit"
git commit -m "Bind actual continuation v1 checkpoint hashes before collection"
"$cemm_python" -m "$cemm_module" collect --data "$cemm_data" --fitted "$cemm_saved_fit" --output "$cemm_results"
test ! -e "$cemm_saved_results"
cp -R "$cemm_results" "$cemm_saved_results"
git add "$cemm_saved_results"
git commit -m "Retain complete continuation v1 traces, scores and decision"
```

Preparation imports the simulator; fitting receives observed inputs only. Binding
records actual checkpoint hashes in the strict plan. Collection requires the plan,
training inventory, and checkpoints to be committed. Retain scratch outputs in
`results/continuation-v1`; traces, all-action reports, and summary are already
XZ-compressed. Keep failure/cost records and manifests.

## Metric, decision order, and limits

Primary exactness weights held-out families equally, then eligible `(N, contacts)`
cells equally, then physical draws equally; each draw averages both views and all
fixed query positions. Missing/abstained queries count incorrect. Unsupported
proper scores prevent an overall numeric mean; supported-only means are labeled.

1. **STOP** for an incomplete run or unequal completed exposure.
2. **REJECT_CURRENT_CONFIGURATION** if any seed fails 95% in-family query accuracy,
   95% in-family reversed-pair conjunction, full continuation support, zero
   unchanged-bit errors, or in-family nonregression against flat.
3. **REJECT_SUPERIORITY_SIMPLIFY** if the strongest prespecified empirical control
   reaches the mean shared held-out accuracy minus 0.01.
4. **KEEP_BOUNDED_ADVANTAGE** requires competence, mean paired gain at least 0.05,
   all five seed differences positive, and one-sided exact sign-test p ≤ 0.05.
5. Otherwise **REJECT_MATERIAL_ADVANTAGE** at this fixed budget.

The sign test concerns initialization variability conditional on this frozen bank;
physical-world generalization is untested. Other contrasts are descriptive.
Parameter/exposure matching does not match consumed compute: report CPU/wall time,
path work, and RSS. Public same-author data, familiar entity counts, and a declared
oracle law do not establish independent custody or general calibration.
A failure does not diagnose its cause or authorize retuning. KEEP leaves G1 unadmitted.
