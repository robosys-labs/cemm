# G1 progress review and bounded G2 continuation

2026-10-30, Africa/Lagos. Tracks [#22](https://github.com/robosys-labs/cemm/issues/22).

**Development decision: proceed to G2 composition with the frozen alias-v2
checkpoint. Formal G1 scientific admission remains open.** Do not repeat the
successful fits or treat unobservable hidden outcomes as a new nucleus defect.
This is an explicit development scheduling decision, not a retrospective change
to the original research gate or a production admission.

**Completed result: `KEEP_MIXED_COMPOSITION` at every seed.** The published freeze
is `669b7b1181f478cdd6c74429535b52a3d80b5ade`; the single collection and byte audit
are complete in [PR #63](https://github.com/robosys-labs/cemm/pull/63).

**Subsequent progress:** the selected joint-correlation challenge is also
complete with **KEEP_JOINT_CORRELATION** at every seed. See its
[retained decision](JOINT_CORRELATION_DECISION_V1.md) and
[PR #64](https://github.com/robosys-labs/cemm/pull/64). This review's historical
mixed-composition measurements and admission boundaries are unchanged.

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

## Result: KEEP_MIXED_COMPOSITION

All frozen criteria pass at seeds **7, 11, 23, 37 and 53**. Every alias seed
answers **512/512 identifiable predictions** and **96/96 identifiable role-pair
conjunctions** correctly, including every family. The paired ordinary-evidence
control achieves 432/512 and 56/96 respectively. All **8,000 planned forecasts**
were produced and supported, with no failures, abstentions or missing trials.

| Metric across five seeds | Ordinary evidence | Acquired-alias evidence |
|---|---:|---:|
| Identifiable predictions | 2,160/2,560 | **2,560/2,560** |
| Identifiable role pairs | 280/480 | **480/480** |
| Ambiguous realized predictions | 680/1,440 | 720/1,440 |
| All-action realized predictions | 2,840/4,000 (71%) | 3,280/4,000 (82%) |
| MAP worlds outside information support | 480 | **0** |
| Definitely unchanged-bit errors | 0 | **0** |
| Mean joint NLL | 0.900871 | **0.256122** |
| Mean joint Brier | 0.416261 | **0.180091** |
| Mean oracle KL, all actions | 0.651338 | **0.006589** |

The candidate's 82% pooled accuracy matches the bank's expected oracle accuracy.
It is not a decline from V2's 88.74%: the new bank deliberately contains more
ambiguous prediction points. All identifiable points remain correct. Its worst
family/stratum mean KL is **0.010532 nats**, below the frozen 0.05 threshold;
worst ambiguous total variation is **0.020285**, below 0.1. The coalescence and
withheld-feedback families pass, supporting persistent mechanism uncertainty
through the tested alias/ordinary combinations.

### Retained regressions and interpretation

There are **400 identifiable repairs and zero identifiable accuracy regressions**.
All-action accounting also retains **372 ambiguous repairs and 332 ambiguous
regressions**. Realized unchanged-bit errors rise **272 to 376**, entirely on
ambiguous forecasts; every candidate MAP world is nevertheless compatible with
the available information. None is a definitely unchanged-coordinate error.

Probability scores do not improve at every point. The ambiguous first-acquisition
strata in `acquired_alias_reverse` and `interleaved_chain` worsen by 0.000453 nats
in mean NLL/KL versus the ordinary arm. Among identifiable points, 1,375 individual
NLLs worsen and 1,185 improve; the largest increase is 0.017532 nats. The overall
improvement and exactness retention do not erase those differences. These compare
the two already-frozen V2 arms; this tranche changes neither arm's weights.

### Reproduction, verification and cost

- [Frozen plan and checkpoints](data/mixed-composition-v1/freeze.json),
  [decision](results/mixed-composition-v1/decision.json),
  [complete artifact manifest](results/mixed-composition-v1/manifest.json).
- **669 tests passed**, zero skips, in **87.920 seconds**. All 22 manifest locks
  and the existing frozen preflight passed. Exact-freeze
  [invariant CI](https://github.com/robosys-labs/cemm/actions/runs/41086979788) and
  [source snapshot CI](https://github.com/robosys-labs/cemm/actions/runs/41086980144)
  passed. Final result-head checks are linked in PR #63.
- The [separate internal byte audit](results/mixed-composition-validation-v1.json)
  verifies 14 result artifacts, 31 source bindings, ten original checkpoints and
  tensor fingerprints, 8,000 receipts, 120,000 point metrics and 4,200 summary
  metrics. No learner or collector was rerun; internal review is not independent
  scientific custody.
- Collection: **57.596350 CPU seconds / 57.652386 measured wall seconds** across
  ten calls; **560,740 KiB** whole-process peak RSS. Compression and analysis are
  outside those collection timings. Candidate per-seed prediction p95 is
  **3.878–7.712 ms**; this is the measured prediction region, not service latency.
- **Zero training updates, zero added parameters, zero inference source changes.**
  Two study adapters add 401 physical lines and their tests add 212. The active
  import closure remains 2,732 lines, or 2,917 with its source pin. Total retained
  research Python is 28,534 lines, including 12,861 test lines; the inclusive
  2,000-line objective remains unmet.
- Before collection, a local mirror was not yet synchronized to the published
  commit. The clean-checkout guard rejected launch before any output directory
  or forecast existed. After exact tree/commit synchronization, the one recorded
  scientific attempt ran to completion. No scored bank was retried.

## Selected follow-on G2 step — now completed

Keep the successful weights fixed. Test two **observed histories with the same
individual 50/50 state marginals but different joint correlations**, followed by
the same relational or ordered two-source prediction. Construct those beliefs
through actual actions and observations, not by injecting a gold posterior.
Use the existing oracle, collector and joint scorer, retain reversed roles and
untouched coordinates, and freeze the contrasting predictions before execution.

This closes the next explicit G2 dependency question. It does not require another
alias curriculum, larger model or workspace. Add a mechanism only if a concrete
failure demonstrates the current function class cannot represent the task.
Simultaneous timing and independently varied multi-source laws remain subsequent
G2 scope; G3 language follows the relevant composition evidence.

The [joint-correlation result](JOINT_CORRELATION_DECISION_V1.md) fulfills this
follow-on task without new fitting. A subsequent assumption review preserves
that decision and corrects the proposed next step: an atomic-event arity limit
does not imply a serial-composition limit. Existing contacts already combine
two independent sources. The bounded
[NAND/NOR law-learning study](MULTISOURCE_LAW_DECISION_V1.md) now retains
KEEP_MULTISOURCE_LAWS: all 11,520 identifiable and 7,680 primary matched forecasts
are correct, and 320 common-history contrast pairs pass. This used the unchanged
model and native API with matched exposure and controlled crossed-law comparisons.
It establishes full-feedback one-step composition; the next selected test carries
a hidden intermediate learned consequence through a cycle with zero new fitting.
