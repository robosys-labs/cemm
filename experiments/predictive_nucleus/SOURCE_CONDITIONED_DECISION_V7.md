# G5 v7 — source-conditioned temporal update; scientific development decision

**2026-11-04 | `REVISE_SOURCE_V7` | 6/10 prospective gates pass |
G5 scientific admission: NOT_ADMITTED.**
**Retain the zero-parameter G5 v1 scoped-evidence rule** as bounded development
baseline. Do not merge or activate v7 temporal memory in production,
retroactively change v6 gates, begin G6–G8, or claim general intelligence.

## Exact question and custody

[Protocol frozen before implementation at 4bf1e61](https://github.com/robosys-labs/cemm/commit/4bf1e61efd22c4789ee94dcd570c74e74b16c4a8)
and [PR #93](https://github.com/robosys-labs/cemm/pull/93)
compare source-aware `(h,e_A,e_B)` against an equally TRAIN-fitted
physics-matched single-e temporal control, the literal frozen v6
two-scalar update and a TRAIN-outcome-calibrated G5 rule.

A pre-fit audit found that the physical simulator flips **binary
observed payoffs**, whereas v6's likelihood mixes the two
meaning-conditional payoff columns. All **8,640** TRAIN selected
physical forecast matrices have `a+b != 1`; these likelihoods
are not equivalent. Fixing the observation equation was necessary
to avoid attributing a physics correction to source conditioning.
The v7 fit reuses the unchanged two-state temporal recursion and
supplies source-conditioned observation likelihoods; the neutral
control shares this correction and is fitted on the identical data.
No hidden meaning, oracle correct interpretation, gold role or
participant-order label entered either fit. The original v6 and
its adverse scored evidence remain unchanged.

TRAIN NAND seeds 7,11,23: 576 worlds, 8,640 observed selected-payoff
outcomes, source counts A=4,324/B=4,316:

| TRAIN model | Parameters | Causal NLL |
|---|---|---:|
| Source-aware v7 | h=.15, e_A=.03, e_B=.20 | .4997977533 |
| Physics-matched neutral | h=.15, e=.10 | .5225088093 |
| TRAIN-smoothed G5 rule | delta=.20 | .5690398380 |

[TRAIN fit sealed before TEST](results/independent-v7/train-fitted.json)
at commit `9dcb3e0be3b9090d0a7f57b60cc470744ad6c2c7`.

New SHA-seeded v7 generator; held-out source conditions on both NAND and NOR:

| Seeds | Challenge sensor inversion, A / B | Regime |
|---|---|---|
| 7, 11 | .03 / .18 | Stationary |
| 23, 37 | .03 / .30 | B degraded |
| 53 | .22 / .03 | Source-reliability reversed |

32 independent opaque worlds per physical triple, 6 triples per
law/seed, 2 laws, 5 seeds: **1,920 worlds**. Each has 15
physically observed selected payoffs, 1 unverified late assertion and
5 correlated scope views. Source/action/epoch schedules do not filter
outcomes based on hidden truth or contradiction. Train/test source
stream and public world identities are independent; the G3
*physical menus* are inherited from earlier opened studies. This
is same-team internally prospective research, **not an external
blind-world scientific admission**.

[Raw sealed first](results/independent-v7/raw/manifest.json),
commit `79a62ce8dc25b5421672a0a0b77d8f1f27866dd3`.
The truth-blind collector emitted all 10 banks and passed **1,229
historical/software tests**. The scoring driver was added **after**
raw commit. First scorer
[run 41889655202](https://github.com/robosys-labs/cemm/actions/runs/41889655202)
emitted all 10 condition score reports, then failed while
displaying unused zero-count subgroup counters. The repair at
`88fa9a8e59af169e6d618cf636223175d1b58214`
filters only the *display* comprehension. No raw forecast, fitted
parameter, meaning score, question policy, gate or criterion
changed. [Scoring erratum](SOURCE_CONDITIONED_SCORING_ERRATUM_V7.md).
[Corrected run 41890264288](https://github.com/robosys-labs/cemm/actions/runs/41890264288)
passes **1,230 tests** and evaluates the exact same raw bank.
[All 10 saved reports](results/independent-v7/scored/manifest.json) ·
[machine-readable decision](results/independent-v7/scored/decision.json).

## Actual held-out scores — no dropped cases

2 goal-actions/world = 3,840 actions. Five meaning views/world =
9,600 **correlated** belief scores. High-confidence means
p>=.95 for wrong 0, or p<=.05 for wrong 1.

| Arm | Mean meaning Brier ↓ | Net/action ↑ | Optimal-action % ↑ | Queries ↓ | Wrong-confident meaning views ↓ |
|---|---:|---:|---:|---:|---:|
| Source-aware v7 | **.048073** | **.852500** | 94.3229 | 148 | 152 |
| Fitted physics-matched neutral | .052206 | .851810 | **94.8698** | **127** | **102** |
| Frozen v6 | .052208 | .851810 | 94.8698 | 127 | 102 |
| TRAIN-smoothed G5 rule | .092597 | .836328 | 92.1094 | 355 | 0 |
| Unmodified G5 v1 rule | .072109 | .832018 | 91.1979 | 100 | 319 |

The v7 net/action increment over neutral is only **+.0006901**,
equivalent to **+2.65 net utility units** on 3,840 actions.
It loses 21 gross-optimal actions, buys 21 additional questions,
has 50 additional wrong ≥95%-confident meaning views, and
introduces **53 new confident root/sentinel errors relative
to frozen v6** (gated regression).
The average Brier gain does **not** protect adverse confident tails,
physical action correctness, query efficiency or the seed floor.

For stationary seeds 7/11, physical payoff causal NLL is
**.499879 v7 vs .522708 neutral**. First local post-epoch
persistent-meaning Brier for stable-B is **.041545 v7 vs .074241
neutral** (n=322), confirming the original attribution. But for
**real persistent meaning flips initially observed via B**,
Brier is **.429457 vs .295480** (n=67): treating noisy B cautiously
also delays accepting a legitimate revision. With B degraded, the
same problematic true-flip-B subgroup is **.456940 vs .325404**
(n=74). Thus this is not just a source-rate estimation problem.

| Seed pooled across NAND/NOR | Source-aware net/action | Neutral net/action | Candidate minus neutral |
|---|---:|---:|---:|
| 7 | .857682 | .853320 | +.004362 |
| 11 | .865299 | .865430 | −.000130 |
| 23 | .858268 | .844922 | +.013346 |
| 37 | .850195 | .842318 | +.007878 |
| **53, reversed trust** | **.831055** | **.853060** | **−.022005** |

In source-reversed seed 53, 36 of the 53 newly wrong
parent/sentinel confident decisions arise; learned static trust
fails when A becomes less reliable and B becomes more reliable.

### Question value — realized outcome, not oracle policy input

The v7 policy purchases **148** verifications. Against
*its own unchanged trajectory if that verification were declined*,
36 purchases have positive realized net value and 112 have
negative realized net value; total realized query net gain
**+34.80**. The neutral control buys **127** (52 beneficial,
75 adverse), gain **+51.95**. These post-score ex-post
counterfactuals are diagnostic only: they are **not**
legally available to the learner when deciding whether to ask
and must not be used to retrofit request suppression.

TRAIN smoothing alone is not the answer: the δ=.20 G5 rule
has Brier **.092597** with **355** paid requests; the
unmodified rule buys 100 and is retained as operational
bounded baseline, not a learned belief update.

## Prospective gates (frozen before scoring)

| Registered gate | Result |
|---|---|
| Stationary observed-payoff NLL better than frozen v6 | PASS |
| Stationary observed-payoff NLL better than fitted physics-matched neutral | PASS |
| Stationary stable-B first meaning Brier better than frozen v6 | PASS |
| Stationary stable-B first meaning Brier better than fitted neutral | PASS |
| Overall meaning Brier no worse than TRAIN-smoothed rule | PASS |
| Global net/action no worse than all three controls | PASS |
| Questions no more than frozen v6 | **FAIL: 148 > 127** |
| Optimal-action rate no worse than frozen v6 | **FAIL: 94.32% < 94.87%** |
| Zero additional confident wrong parent/sentinel views | **FAIL: 53 new** |
| Every seed's net/action nonregressing versus controls | **FAIL: 11 and 53** |

**Formal decision: `REVISE_SOURCE_V7`; G5 NOT_ADMITTED.**
Source-aware observation is informative, yet this exact candidate
is not an acceptable durable meaning updater.

## Technical diagnosis / next experiment boundary

The old source-neutral model was physically misspecified for
bit-flipping sensors. Correcting that mismatch and fitting an
extra source-reliability scalar improves calibration in stable noisy
cases. It does not produce a transferable account of **when the
underlying meaning changes**, how quickly a true post-epoch change
is accepted after low-quality evidence, or how source reliability
itself evolves. Under reversed trust, the static source prior
creates overconfident errors even on unrelated retained meanings.

Next highest-information step is **one representation diagnostic**,
not a new scalar grid or architecture expansion by habit. Freeze a
small joint latent hypothesis about (a) time-indexed persistent
meaning and (b) source-trust mode/uncertainty, trained from observed
selected payoffs. Contrast with both frozen fixed-trust filters
and G5 v1 rule on entirely fresh, independently seeded
matched-history stable/true-change/source-reversal cases.
Require indistinguishable pre-probe histories to remain
appropriately uncertain; count query value and utility per seed,
and protect root/sentinel retention. Avoid supplying true
source rates, change labels, gold meanings, gold role order
or oracle clarification responses at decision time. If the
representation cannot beat the compact rule without unacceptable
questions/error tails, stop and reassess scientific viability.

No neural/compositional generality claim follows from these
hand-structured, source-ID-visible cases. Real inherited semantic
scope, learned answer persistence across processes, independent
real-world validation, and the inclusive ≤2,000-LOC target
remain unproven/open. G1–G3 bounded development acceptance,
G4 retained receiver, and all historical negative results
are untouched. No G6 or production cutover.
