# G5 v6 — why the learned temporal policy underperforms its question budget

**2026-11-04 · Post-scoring diagnosis · NOT_ADMITTED.** Source study:
[PR #91](https://github.com/robosys-labs/cemm/pull/91), sealed raw
[3f0d247](https://github.com/robosys-labs/cemm/commit/3f0d247d88c51132ff63e1fde34dfca1b45747ab),
preserved ten-condition scorer
[61e1a979](https://github.com/robosys-labs/cemm/commit/61e1a979b79e2174ea634b5849f2db89dbb4501f),
[hosted 1,224-test scoring run](https://github.com/robosys-labs/cemm/actions/runs/41861748467).
This is a **read-only opened-TEST analysis**, not a new experiment, fit,
revised acceptance criterion or scientific admission. The frozen v6 fit
is **h=.15, e=.10**.

## Confirmed headline

| Same 1,920 worlds / 3,840 goal actions | Outcome-trained v6 | Scoped G5 v1 rule | Historical h=.5 model |
|---|---:|---:|---:|
| Mean meaning Brier (9,600 correlated views; lower better) | **.055928** | .074297 | .061791 |
| Mean goal net/action (higher better) | **.841667** | .829466 | .843516 |
| Goal-optimal actions | **93.516%** | 91.484% | 94.089% |
| Paid questions | **88** | **73** | 310 |
| Wrong >=95%-confident meanings | **112** | 325 | 21 |

The saved scorer totals give **+46.85 net utility units** and
**+47.60 gross reward units** for v6 against the rule, after
**15 extra questions costing .75 total**. V6 outperforms the
rule in eight law/seed conditions but regresses in **NAND seed 37
(-2.80 total utility)** and **NAND seed 53 (-.90)**. It does not
dominate the stronger historical temporal arm on net/action
(.841667 vs .843516). The frozen G5 no-more-queries / worst-seed
admission gates therefore **fail**. No production promotion.

## Exact explanation of the 15 extra requests

Independent read-only replay of **all 1,920 sealed raw decisions**
reconstructs opaque case IDs from the registered SHA-256 world generator,
calculates the evaluator's hidden local meaning from the original
deterministic draw, and reproduces every condition's immutable
temporal/rule utility total (within 1e-8).

| Paid-query overlap | Cases |
|---|---:|
| Both v6 and scoped rule ask | **73** |
| Only v6 asks | **15** |
| Only rule asks | **0** |
| Neither asks | **1,832** |

Every extra v6 request has a consequential direct/reversed public goal
and cheap fee **.05**; nine have a B-source epoch observation and six
have A. Model PRE probabilities for these cases range **.2794–.7188**;
the scoped rule has already committed to meaning 0 or 1. Therefore
the additional requests come from genuine *belief disagreement*
with a deterministic rule, not a faulty fee check or paid
irrelevant question.

Evaluator-only, ex-post counterfactual comparison against **the same
temporal policy without purchasing its extra answer** finds:
**four** questions repair a wrong action, gaining **1.0 gross
utility each**; **eleven** provide no realized action benefit,
costing .05 each. The incremental net benefit of all fifteen
is **4 – 15×.05 = +3.25**. The remaining **+43.60** of v6's
+46.85 advantage against the rule persists if those fifteen
requests are suppressed, on this fixed *opened* bank.
This is a factual decomposition of realized outcomes, **not** a
prospectively selected query policy or unbiased conditional
VOI estimate.

The four beneficial queries all occur in **stable-meaning worlds**;
the model sometimes treats noisy evidence as a possible revision
and appropriately checks rather than committing. All **eight**
extra queries occurring after a genuine persistent flip are
unnecessary *on their realized trajectories*; this fact is not
visible to the policy beforehand. A future policy cannot simply
branch on true "flip" labels.

## Root causes: source trust and temporal revision

The current [filter](temporal_belief_v5.py) accepts `rec.source`
but its `_update` and `probability` use one global observation
inversion scalar **e=.10**. In the frozen independent v6
[generator](independent_task_v6.py), TEST source A has **.03**
observation error and source B has **.24**, and TRAIN source B has
.18. These source labels are known to the model, but **its
likelihood never conditions on them**. The resulting overall
selected-payoff NLL is **.47507 for A vs .66540 for B**
(Brier **.15472 vs .22982**). This is a directly evidenced
model-specification mismatch. The noise rates are generator facts,
not learned source reliability. It is **not** proof that simply
adding a source-specific scalar will win a new test.

The strongest goal-utility subgroup is:

| Post-epoch state and epoch observation source | v6 minus rule total net utility |
|---|---:|
| Stable meaning + source A (740 worlds) | **+21.30** |
| Stable meaning + source B (794 worlds) | **−34.95** |
| Actual revision + source A (200 worlds) | **+33.40** |
| Actual revision + source B (186 worlds) | **+27.10** |
| All 1,920 worlds | **+46.85** |

The learner better adapts to an actual change, but can **overreact
to an unreliable B observation when the meaning is stable**. An
explicit case in NAND seed 37 has source B, no actual flip,
temporal PRE/FINAL meaning probabilities **.6042/.6020** while
the rule remains unknown (.5); the temporal model commits to the
wrong direct action twice and loses **2 utility units** against
the rule on that world. Saved raw ID:
`143838e4ead5ef9fa6eae564`.

Genuine-meaning-change episodes have meaning Brier **.08882**
across five correlated views, compared with **.04765** when
stable (386 changed vs 1,534 stable worlds). Immediate local
belief is the hardest view: v6 mid-local Brier **.10573**
against rule **.10938** (small gain); after two additional
readings, final-local Brier improves to **.03723 vs .05690**.
The 95%-confidence error counts are **69 vs 85 mid**, and
**25 vs 44 final**. This is still an inference and timing
weakness, not yet structural proof that a third latent mode is
necessary.

## What the current task does *not* establish

- The rule baseline's `0, .5, 1` values are **supplied
  decision-to-probability mappings**, not its trained posterior.
  Lower Brier against these fixed endpoints is encouraging but
  does not settle a comparison with a TRAIN-calibrated, smoothed
  rule. Include that low-capacity control in the *next* study.
- A query is perfect, charged once, and its hidden meaning is
  directly supplied to the evaluator's **two actions**.
  This is a useful priced-oracle control but does not itself test
  crash-safe, learned cross-episode answer retention or a noisy
  clarification source.
- The generator samples root/regional/local meanings **independently**,
  while the filter uses a supplied scope hierarchy and starts local
  inference from .5 when local records exist. This is not yet a
  strong test of actual inherited meaning, overrides or mixed
  source reliability across scopes.
- The two original physical laws and G3 menu families were opened
  in earlier studies; distinct law/seed SHA streams improve
  nuisance separation, **not external blind physics custody**.
- The v6 algorithm optimizes **one-step selected-payoff NLL**;
  it does not optimize latent belief Brier or goal-query utility
  directly, nor does it learn source reliability.
- A future study may prospectively compare *net utility at a
  fixed cost/correctness budget*, including useful additional
  clarifications. The **opened v6 no-extra-questions gate
  cannot be rewritten retroactively**.

## Recommended next tranche — no new neural layer

1. **First:** freeze a new source-reliability experiment with
   the *same two-state temporal posterior* but source-aware
   observation likelihoods: `h, e_A, e_B` (one added
   parameter versus v6), learned from **selected physical
   payoffs only**, compared at matched histories, parameter/
   compute budgets with the unchanged v6 filter, a
   **TRAIN-calibrated smoothed G5 rule**, and strong goal-aware
   non-learning controls. Check source A/B reversals, changing
   reliability, actual epochs and independent unknown identities.
2. **Second:** fit or recalibrate a small *goal-aware* information
   policy from **actual subsequent payoffs**, not hidden semantic
   labels. Publish quality, empirical ROI and clarification
   cost across cheap/expensive/unavailable and imperfect
   verification; protect correct old behavior and opposite
   truth twins. Evaluate the query/utility Pareto frontier
   instead of assuming every additional question is wasteful.
3. **Later:** evaluate true inherited semantic scopes and
   serialization across process restarts, plus independently
   custodied fresh physical families. Do not begin the
   G6 Wikipedia bridge or production cutover until G5 passes
   meaningful prospective development and scientific admission.

Keep the implementation tiny and retain the accepted zero-scalar
rule as selection baseline. The inclusive 2,000-LOC research
objective remains unmet. **G5 NOT_ADMITTED.**
