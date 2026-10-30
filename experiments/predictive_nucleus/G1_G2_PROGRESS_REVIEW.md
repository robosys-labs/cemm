# G1 progress review and bounded G2 continuation

2026-10-30, Africa/Lagos. Tracks [#22](https://github.com/robosys-labs/cemm/issues/22).

**Development decision: proceed to G2 composition with the frozen alias-v2
checkpoint. Formal G1 scientific admission remains open.** Do not repeat the
successful fits or treat unobservable hidden outcomes as a new nucleus defect.
This is an explicit development scheduling decision, not a retrospective change
to the original research gate or a production admission.

## What is already established

The starting checkpoint is
`2361c48986276fe897a9cd9beac874720cfcbb7a` in [PR #62](https://github.com/robosys-labs/cemm/pull/62).
The [alias-v2 decision](ALIAS_EVIDENCE_DECISION_V2.md) and its committed raw records
establish the following on the public fixed-law bank:

| Capability | Retained evidence |
|---|---|
| Ordinary continuation | 704/704 queries at each of five seeds, including 672 withheld-composition queries |
| Reversed role pairs | 136/136 conjunctions per seed |
| Self-contact after adequate training evidence | 16/16 per seed, including 8/8 at each starting bit |
| Retention after the evidence correction | Zero newly incorrect continuation queries |
| Complete execution | 13,520/13,520 planned forecasts, no abstentions or terminal failures |
| Model | Same 562 parameters and 128 training updates; empirical recovery repaired with two net inference lines |

The original continuation `STOP_INCOMPLETE_RUN`, alias-v1
`REVISE_EVIDENCE_FIX`, and alias-v2 `KEEP_EVIDENCE_FIX` remain unchanged.
An old failed experiment is not turned into a pass by a later correction.

## Why the pooled accuracy must not keep reopening G1

A [read-only audit](results/g1-g2-saved-evidence-review.json) of the saved alias-v2 distributions confirms **5,240/5,240
identifiable complete-world predictions**, and 759/1,520 ambiguous predictions.
Every one of its 6,760 MAP worlds lies within the evaluator's information support.
All 183 newly wrong MAP choices are ambiguous. All 473 realized-world
unchanged-bit errors are on coordinates whose change depends on the still
unknown orientation; none is a definitely unchanged-coordinate error.

The expected optimal pooled exactness under this bank's balanced hidden-mode
law is `(1048 + 304/2)/1352 = 88.757396%`, compared with the learned 88.742604%.
The original roadmap actually specifies **in-family** complete-world exactness:
that subset contains 138 identifiable and 64 ambiguous actions per seed, giving
expected optimum `(138 + 64/2)/202 = 84.158416%`. These are information-design
expectations, not deterministic bounds on a finite realized sample.

Ambiguous mean realized NLL is 0.697084, close to the oracle's `log(2)=0.693147`;
mean KL from the oracle joint distribution is 0.003740 nats. Ambiguous confidence
ranges 0.497551–0.502004. This does not indicate confident hidden-mode guessing.
Small soft probability tails remain. The continuation NLL regression from
0.006230 to 0.008788 is retained; unchanged accuracy is not universal improvement.

The historical >=95% gate remains unpassed. Its mismatch with this information
design is not a reason to refit a predictor that already answers every
identifiable item correctly. Strong baseline adequacy and independent challenge
authorship/custody remain genuine scientific-admission requirements. They do not
prevent the user's requested bounded composition development. Learned questioning
belongs to G4 and durable clarification to G5, not new G1 exit conditions.

## The next measurement is genuinely new

V2 evaluated standalone self-contact separately from ordinary continuation.
It did not measure ordinary contacts after aliases, repeated aliases, or hidden
orientation retention across those combinations. The
[frozen mixed-composition protocol](mixed_composition_protocol_v1.json) tests:

| Family | Ordered schedule |
|---|---|
| Acquired alias and reversal | `ab, cc, ba` |
| Alias before acquisition | `cc, ab, ba` |
| Repeated alias | `cc, cc, ab, ba` |
| Withheld acquisition | `ab, cc, observe, ba, ab`; b withheld until observe |
| Coalesced worlds | `ab, ab, cc, ab, ba`; first b withheld, mechanisms later diverge |
| Interleaved chain | `ab, cc, bc, ab, ba` |

There are 48 blueprint lineages, 192 dependent mode/direction views, 3–6 entities,
3–5 contacts and 800 forecasts per checkpoint. Ten unchanged checkpoints produce
8,000 planned forecasts. Both starting bits are covered for c. Full templates
and canonical blueprints have zero overlap with all four checked historical
asset archives, including their training and reserved partitions.

Each checkpoint faces 512 identifiable and 288 ambiguous predictions. The bank's
expected optimal pooled MAP accuracy is 82%; this intentionally differs from
the identifiable accuracy target. Every raw action and realized-world metric
remains reported. Before collection, the protocol fixes >=95% identifiable
accuracy per seed/family, retention, complete support, valid MAP worlds, known
unchanged coordinates, role pairs and joint-distribution tolerances. The scorer
compares full distributions without removing probability outside oracle support.

## Execution and limits

Reuse `acceptance_runner.collect`, `acceptance_scoring.evaluate`, native
checkpoints, the simulator and the separately coded affine oracle. Two small
study adapters supply the fresh matrix and its information-aware decision.
There is no fitting stage, runtime/model change, workspace or language addition.
The original 64-path/512-expansion limits remain. At most two cumulative missing
bits keep this challenge within the existing budget without hiding its outputs.

```sh
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0 python -m \
  experiments.predictive_nucleus.mixed_composition_run prepare \
  --output experiments/predictive_nucleus/data/mixed-composition-v1
# Commit/publish source, locked protocol, plan and assets before collection.
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0 python -m \
  experiments.predictive_nucleus.mixed_composition_run collect \
  --data experiments/predictive_nucleus/data/mixed-composition-v1 \
  --output /absolute/new/results-directory
```

Do not retry or refit after collection. Retain failures and act on the first
demonstrated cause. These tests cover ordered interactions under the supplied
binary law; simultaneous timing and independently varied multi-source laws remain
unmeasured. A successful mixed-composition decision advances G2 but does not
complete the entire G2 gate or independent scientific validation.
