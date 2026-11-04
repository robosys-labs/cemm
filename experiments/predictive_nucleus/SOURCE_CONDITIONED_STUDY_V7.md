# G5 v7 — frozen prospective source-conditioned posterior comparison

**2026-11-04.** Stacked on diagnostic PR #92, which analysed the already
opened v6 TEST. This protocol precedes new source code, fitting, challenge
collection, and scoring. **G5 NOT_ADMITTED; G6–G8 and production unchanged.**

## Falsifiable question

Does replacing the v6 single sensor-exception probability with
`(h,e_A,e_B)` (one extra scalar) improve the **first post-epoch belief**
and actual priced decision utility, without compromising high-confidence
errors, inherited historical results or worst-seed outcomes? Or is the
two-state temporal representation itself insufficient?

Compare on *identical observed physical histories*:

1. `source_temporal`: one globally shared, selected-payoff-trained
   `h,e_A,e_B` using no gold meaning, state, role, actual inversion, or
   action label. Fixed grids `h=(.05,.15,.35,.5)`,
   `e_A=(.01,.03,.05,.1)`, `e_B=(.05,.1,.2,.3)`.
   64 candidates; choose lowest causal TRAIN NLL; ties lexicographic.
2. `v6_frozen`: **unchanged** `h=.15,e=.1` v6 update and query rule,
   *not* fitted from the new challenge.
3. `rule_smoothed`: the unmodified G5 v1 memory decisions
   `0/None/1`, mapped to `d/.5/(1-d)`, with **one** TRAIN-only
   `d=(.01,.05,.1,.15,.2,.3,.4)` selected by forecasting *observed
   physical payoffs* from successive public prefixes; no meaning labels.
   No source, truth or challenge calibration. Report raw `scoped_rule`
   separately, `latest`, `no_memory` as decision references.
4. `v6_frozen` and `source_temporal` must use the *same* supplied
   goal-aware perfect-verification policy, not a fitted query suppressor.
   Verification cost and reward tables remain `goal_policy_v6`.

## Data custody

- New **v7** SHA-256 namespace, independent of all v6 world IDs, source
  schedules, noisy readings, stochastic latent draws and payoffs.
  The original frozen G3 NAND/NOR physical menus are **reused**; this
  is internally produced prospective development, not externally
  custodied blind-physics validation.
- Fixed ten conditions = NAND/NOR × seeds (7,11,23,37,53),
  6 physical-layout triples × 32 independent opaque worlds = 192
  per condition, 1,920 worlds total and 28,800 observed payoffs.
  Five views/world (first/last post-epoch local, sibling, root, sentinel).
- One per-world scheduled local revision (probability .20) independent
  of source/errors; 15 selected physical readings; one final unverified
  claim. Sources, selected actions, observations and event times cannot
  be selected based on hidden meaning or resulting contradiction.
- TRAIN: **NAND seeds 7,11,23 only**, same 576 worlds/8,640 outcomes,
  source error A=.03 and B=.18. Fit one global triple and one rule delta;
  no per-law/seed fit. Do not calculate TEST truths during TRAIN.
- Challenge source regimes are *fixed by seed, for both laws*:
  seeds 7,11: **stationary** A=.03, B=.18;
  seeds 23,37: **B-degraded** A=.03, B=.30;
  seed 53: **reversed** A=.22, B=.03.
  Rates are generator-only, invisible to learner; no unsupervised
  TEST adaptation or refit. Distinct seeds/laws receive independent
  SHA source/error streams. These shifts intentionally test whether
  static source-specific trust breaks.
- Lock generator/source/test SHA and complete global TRAIN fit before
  any challenge collection. Publish all predicted probabilities with
  public world ID, source and record digest *without oracle truth*.
  Commit raw before importing evaluator-only ground truth or scoring.
  No deletion, cherry-picking, refit, new threshold or post-score test
  substitution. An invalid protocol abort preserves evidence.

## Metrics and decisions (frozen)

Publish for **all 1,920 worlds**: source/payoff causal NLL and Brier;
per-view persistent-meaning Brier and NLL; 95%-confident wrong counts;
squared loss at the *first* post-epoch local reading and after two more;
stable versus genuinely flipped meaning; A/B epoch source, including
stable-B; per-regime and per-seed net two-goal utility, optimal actions,
gross regret, fees, queries, and query overlap. Separately measure
every purchased question's **realized counterfactual gross gain and
net gain** against the same policy refusing its answer (evaluator
only, after sealing); never use that information to choose questions.
A purchased answer affects only the second action in this episode,
not sibling/root/sentinel memories. Report worst-seed utility on each
of the five seeds pooled over both laws. Correlated five views are
not five independent trials.

Integrity gates: zero distinct world/source ID overlap with v6,
unique evidence IDs, fixed 15+1 schedule, independent law/seed streams,
no oracle input in collector/fit, all historical locks/invariants pass,
consistent frozen fit and raw hashes, no self-referential calibration,
fully reproducible deterministic forecasts. All original G1–G4
development results, v5/v6 adverse results and v6 gates are unchanged.

**`KEEP_SOURCE_V7_DEVELOPMENT`** only if *all* apply on the prospective
challenged bank:
- On the **stationary** seed 7/11 conditions combined, source-temporal
  selected-payoff NLL and first-local stable-B Brier are **strictly
  better** than frozen v6; source-temporal overall five-view meaning
  Brier is no worse than the outcome-calibrated rule.
- Across **all ten** conditions, goal net/action is >= both frozen v6
  and smoothed rule, while paid queries are <= frozen v6 (at >=
  frozen-v6 optimal-action rate). No seed's pooled net/action worsens
  against either control. Zero added high-confidence parent/sentinel
  errors against v6. These are deliberately demanding and cannot be
  relaxed after scoring.
- Report descriptive worst-seed, source regime and actual query ROI
  whether or not any threshold passes. If any safety/custody invariant
  fails: `STOP_INVALID_V7`. Otherwise if any above science gate
  fails: `REVISE_SOURCE_V7` and **keep G5 rule baseline**.
  A development KEEP is *not* formal G5 scientific admission.

## Reproducibility sequence

1. Commit this protocol; no new TEST scores exist.
2. Commit tiny learner, generator, TRAIN-only calibration, collector and
   scorer code with focused unit tests; test only TRAIN substitutions.
3. Run and publish fitted TRAIN triple, rule delta, grid and test/CI
   receipts before any v7 challenge generation.
4. Collect and commit immutable raw TEST predictions and manifest.
5. Score only these committed raw files; publish full metrics, adverse
   case information and decision. Never retroactively score another
   candidate on the bank.
6. If minimal source conditioning fails, investigate whether the
   *temporal state representation* conflates noisy observations with
   durable latent changes. Do not continue source/hazard parameter
   sweeps, train a new neural layer, or begin G6.
