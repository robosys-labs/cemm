# G2 joint correlation through observed histories

2026-10-30, Africa/Lagos. Continues [#22](https://github.com/robosys-labs/cemm/issues/22)
and the completed [mixed-composition decision](G1_G2_PROGRESS_REVIEW.md).

**Result: KEEP_JOINT_CORRELATION at all five seeds.** The single collection
produced all **1,920 forecasts**; both frozen arms pass every critical contrast.
The [published freeze](https://github.com/robosys-labs/cemm/commit/2181a01d60689722d62f2ee44110b9c00471e031)
preceded collection. [PR #64](https://github.com/robosys-labs/cemm/pull/64)
retains the complete result and audit. G1 development readiness stays
**PROCEED_TO_G2**; formal G1 admission stays **NOT_ADMITTED**.

## Prospective question

Can the frozen V2 nucleus distinguish two actual histories whose individual
state probabilities are identical but whose joint correlations differ?
This follows the successful mixed-composition result without reopening G1,
altering its formal admission decision, or fitting another model.

Starting with `(a,b,c) = (0,0,1)`, use these three-contact schedules:

| Motif | Equal-correlation history | Opposite-correlation history | Common query |
|---|---|---|---|
| Chain | `ac, ba` | `ac, cb` | `ba` |
| Fork | `ca, cb` | `ca, bc` | `ab` |

After the first contact withhold a; after the second withhold a and b. The
delivered readings are identical within each matched pair: `(?,0,1)`, then
`(?,?,1)`. The equal history leaves worlds `001/111`; the opposite history
leaves `011/101`, with probability one half each. Both have the same individual
marginals, `P(a=1)=P(b=1)=1/2`, and `c=1`.

Nevertheless, the same subsequent query requires **b=0** for equal correlation
and **b=1** for opposite correlation. The predictor receives only the real action
and observation history. Condition labels, modes and oracle probabilities are
evaluator-only. The final prediction precedes full feedback.
The retained dependency includes the relationship between uncertain physical
states and the persistent mechanism, not only state-to-state correlation.

## Frozen design and decision

The [protocol](joint_correlation_protocol_v1.json) fixes 64 episodes,
192 forecasts per checkpoint and 32 critical contrasts. It includes both motifs,
3–6 entities, both physical modes and both global role reversals. Eight
motif/entity-count contrast contexts group these dependent views. Opposite
templates overlap across motifs under reversal; this is a deliberate diagnostic
comparison, not eight independent physical replications or new-topology evidence.
All historical and within-bank overlap is retained in the asset audit.
The frozen configuration has 15 unique canonical blueprints across 16
motif/condition/entity-count designs; the three-entity opposite members form the
one duplicate group. Historical blueprint overlap is zero. Action-template
overlap is three with prospective evaluation, three with continuation, one with
alias-v1 and three with alias-v2; training, selection, calibration and mixed-v1
overlap is zero. These are fresh observation/correlation histories on some
previously evaluated action templates.

Reuse both V2 arms at all five seeds: **ten unchanged 562-parameter checkpoints**
from `2361c48986276fe897a9cd9beac874720cfcbb7a`. There is no fitting,
adaptation, posterior injection, new architecture or inference source change.
Three cumulative missing bits create at most eight histories, or 512 candidate
world expansions at six entities, within the existing resource limits.

Each checkpoint has 32 identifiable and 160 ambiguous full-world forecasts.
Expected best all-action MAP accuracy is `(32 + 160/2)/192 = 58.3333%`.
The original >=95% G1 gate is unchanged. The new diagnostic requires, at every
candidate seed and motif, >=95% identifiable accuracy and role-pair conjunctions,
complete support, no identifiable regressions, no unsupported MAP world, and no
definitely unchanged-bit error. It also retains the previous probability criteria:
mean oracle KL <=0.05 nats separately in both information strata, and TV <=0.1
on every ambiguous forecast.

Every critical pair must satisfy `P(b=1|equal)<=0.1`,
`P(b=1|opposite)>=0.9`, and a paired gap >=0.8. Missing or abstained answers fail.
Full-joint scoring prevents a correct b readout from concealing collapse of the
remaining uncertainty. A factorized evaluator control discards correlations;
its two identical marginal states give `P(b=1)=0.5` in both conditions, gap zero.
That is an analytic information-loss control, not a learned baseline or neural
ablation. The two learned arms may tie without invalidating the hypothesis.

## Execution and scope

```sh
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0 python -m \
  experiments.predictive_nucleus.mixed_composition_run prepare --study correlation \
  --output experiments/predictive_nucleus/data/joint-correlation-v1
# Publish source, locked protocol, assets, plan and checkpoint inventory first.
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0 python -m \
  experiments.predictive_nucleus.mixed_composition_run collect --study correlation \
  --data experiments/predictive_nucleus/data/joint-correlation-v1 \
  --output /absolute/new/results-directory
```

One collection is permitted. All raw predictions, probability tails, repairs,
regressions, omissions and failures remain in the record. Historical studies
are not rerun. The learned likelihoods operate within supplied joint filtering
and persistent modes; this does not establish learned Bayesian machinery,
arbitrary new interaction laws, simultaneous timing, general calibration or
independent scientific custody. Full G2 and formal scientific admission remain
open while development proceeds.

## Result: KEEP_JOINT_CORRELATION

Every candidate seed (7, 11, 23, 37, 53) passes all frozen criteria. Each produces
32/32 identifiable complete worlds, 16/16 identifiable reversed-role pairs,
and 32/32 critical equal/opposite contrasts. The ordinary arm also passes these
checks. There are no missing outputs, abstentions or terminal failures.

| Measure across five seeds | Ordinary evidence | Acquired-alias evidence |
|---|---:|---:|
| Critical correlation contrasts | 160/160 | 160/160 |
| Identifiable complete worlds | 160/160 | 160/160 |
| Identifiable reversed-role pairs | 80/80 | 80/80 |
| Ambiguous realized MAP predictions | 400/800 | 400/800 |
| All-action realized MAP predictions | 560/960 (58.3333%) | 560/960 (58.3333%) |
| Unsupported MAP worlds | 0 | 0 |
| Definitely unchanged-bit errors | 0 | 0 |
| Mean joint NLL | 0.582371 | 0.582976 |
| Mean joint Brier | 0.416696 | 0.416727 |
| Mean oracle joint KL | 0.004748 | 0.005353 |
| Maximum ambiguous total variation | 0.014329 | 0.026692 |

For the acquired-alias model, **P(b=1|equal) ranges 0.002716–0.009121**,
while **P(b=1|opposite) ranges 0.995713–0.998864**. Every paired gap is
**0.988057–0.996148**, exceeding the frozen 0.8 criterion. Ordinary-arm gaps
range 0.986985–0.994486. The analytic factorized control gives exactly 0.5 in
both conditions, gap zero, for all 32 contrasts.

Full-joint quality also passes: the candidate's worst family/stratum mean KL
is **0.008059 nats** against the 0.05 limit; maximum ambiguous TV is
**0.026692** against 0.1. The same output coordinate can therefore be certain
while the remaining physical state stays uncertain. This supports the tested
history-sensitive joint prediction, including persistent state/mechanism
dependencies. It does not isolate a learned internal Bayesian algorithm from
the supplied joint filter.

### Regression accounting

The two arms tie on complete-world exactness and critical contrast success.
There are **zero identifiable repairs and zero identifiable regressions**;
ambiguous MAP choices have **136 repairs and 136 regressions**, all retained.
Realized unchanged-bit errors are 328 in the ordinary arm and 408 in the alias
arm, entirely on ambiguous forecasts; definitely unchanged-coordinate errors
remain zero. Their different equally plausible MAP choices are not new G1
failures or grounds to refit this challenge.

The alias arm's mean NLL is **0.000605 nats worse**, Brier 0.000032 worse,
and oracle KL 0.000605 worse. Among identifiable forecasts, 96 NLLs improve
and 64 worsen (maximum increase 0.001452); among ambiguous forecasts, 259
improve and 541 worsen (maximum increase 0.033950). These are comparisons of
the two already-frozen V2 checkpoints, not weight changes introduced here.
Do not claim universal improvement. Both arms remain comfortably within the
prospective tolerances.

The 58.3333% pooled accuracy matches the declared information-design expectation.
Comparing it directly with the mixed bank's 82% or V2's 88.74% would confuse
different ambiguity mixtures with model regression. Earlier source, checkpoints,
results and decisions are unchanged; no historical experiment was rerun.

### Verification and cost

- [Prepared source/checkpoint inventory](data/joint-correlation-v1/freeze.json),
  [decision](results/joint-correlation-v1/decision.json),
  [raw artifact manifest](results/joint-correlation-v1/manifest.json).
- The **681-test isolated suite**, all **23 locks** and frozen preflight pass in
  [exact-freeze CI](https://github.com/robosys-labs/cemm/actions/runs/41091915442).
  [Source snapshot CI](https://github.com/robosys-labs/cemm/actions/runs/41091915993)
  also passes. Locally, 680 tests passed before commit; the one clean-checkout
  preflight was rerun after publication and passed. This was an infrastructure
  check before the single scientific collection, not an experiment retry.
- The [internal byte/arithmetic audit](results/joint-correlation-validation-v1.json)
  verifies 14 result artifacts, 33 source bindings, ten original checkpoint and
  tensor identities, 1,920 forecast receipts, 28,800 point metrics, 1,800 summary
  metrics and all 320 learned contrast pairs. It independently reconstructs the
  physical histories and factorized control. No learner or collector was rerun;
  same-author internal review is not independent scientific custody.
- Collection took **13.223051 CPU seconds / 13.224660 measured wall seconds**,
  about **145.18 forecasts/second** across all calls. Candidate prediction p50
  ranges **1.502–1.636 ms**, p95 **2.728–4.181 ms** across seeds. Peak whole-process
  RSS is **413,896 KiB**. These are CPU collection/prediction regions; compression,
  analysis and service overhead are excluded. Runtime: Python 3.13.16,
  Torch 2.10.0+cpu, NumPy 2.3.5, single-threaded deterministic x86_64 execution.
- **Zero training updates, zero added parameters, zero inference changes.**
  The new generator is 132 physical Python lines; the reused runner grows by
  70 net lines; twelve focused tests add 211 lines. Active import closure remains
  2,732 lines (2,917 with the existing source pin). Total retained research Python
  is 28,947 lines, including 13,072 test lines; the inclusive 2,000-line objective
  remains unmet. This result does not justify a larger model or generic platform.

## Assumption review — 2026-10-30

The [saved-asset review](results/joint-correlation-assumption-review-v1.json)
finds **no defect invalidating KEEP_JOINT_CORRELATION**. It adds three scope
clarifications without changing the frozen protocol, outputs or decision.

The analytic control destroys both physical state correlation and its association
with the persistent mechanism. For every contrast, its target-one probabilities
are 0.5/0.5. Retaining the physical-state joint while discarding only its mechanism
association gives 0.25/0.75; correct associations give 0/1. Thus the result excludes
unconditional marginals, but does not establish a need for explicit full-world
enumeration. Per-entity marginals conditioned on the persistent mechanism suffice
for this bank.

The 64 episode views contain 32 distinct pre-query histories; 32 declared contrasts
contain 16 distinct paired histories repeated across physical-mode realizations.
There are 74 unique information keys across 192 forecast positions. Repeated views
and seeds do not turn these into independent physical-world demonstrations.
The known-unchanged metric checks coordinates with one fixed retained value; it
does not alone prove trajectory-wise retention of an uncertain coordinate.

## Corrected next bounded G2 task

The previous proposed ternary extension overinterpreted an atomic-event arity
limit as a compositional limit. Existing XOR contacts already compute
`t XOR a XOR b` across two actions. Preserve the successful weights and test
fresh NAND/NOR laws through the unchanged pairwise interface instead. The
[new study](MULTISOURCE_LAW_DECISION_V1.md) uses matched initial tensors and
exposure, separate law learning and crossed-law forecasts at controlled identical
histories. It changes no neural inference or checkpoint implementation.
Simultaneous timing remains unestablished scope.

The corrected follow-on is now complete: [multisource law v1](MULTISOURCE_LAW_DECISION_V1.md)
retains KEEP_MULTISOURCE_LAWS at all five seeds for both laws. It preserves this
correlation decision and establishes full-feedback one-step composition. The
next selected task uses those frozen checkpoints to test propagation through
a hidden intermediate state, with zero further fitting.
