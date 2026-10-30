# G2 joint correlation through observed histories

2026-10-30, Africa/Lagos. Continues [#22](https://github.com/robosys-labs/cemm/issues/22)
and the completed [mixed-composition decision](G1_G2_PROGRESS_REVIEW.md).

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
