# G5 v5 temporal correction — completed bounded study, no promotion

**Decision (2026-11-04): `REVISE_TEMPORAL_CANDIDATE;`
`STOP_CONFOUNDED_FOR_INDEPENDENT_REPLICATION;`
`KEEP_SCOPED_EVIDENCE_BASELINE`.** The experiment demonstrates a
useful local payoff-prediction improvement and improved threshold-level
abstention, but not calibrated durable beliefs, lower clarification
burden or independent G5 admission.

## Exact experimental custody

- Frozen protocol: `1c60ac9ed32c9b8b6c9567ec0dcc361b7b44da65`.
  [Pre-fit integrity erratum](TEMPORAL_PREFIT_ERRATUM_V5.md) removed an
  oracle-dependent unverified claim before accepting TRAIN fits.
- Corrected TRAIN fit source: `ed0c96813c3bc1367cd1efcfbaf300afcece05e1`;
  [published 10 fit grids](results/temporal-v5/train-fitted.json) at
  `4fd21dee3be772c51c96e5aebdb516e481f981f6`.
  All conditions selected **h=0.5, e=0.1**, with 2,880 observed
  selected-action payoff outcomes per condition and no meaning labels.
- **Raw collected before scoring:** `0988a525a8c315f4ba245400ab81d438857717d8`
  contains ten unscored challenge files, 192 episodes each and 15
  causal payoff forecasts per episode, with per-record evidence digests.
  [Collection CI](https://github.com/robosys-labs/cemm/actions/runs/41840925863):
  **1,216 tests pass**.
- The first evaluator [run 41841900837](https://github.com/robosys-labs/cemm/actions/runs/41841900837)
  incorrectly read the oracle target instead of the forecast decision
  when computing one PRE-confidence count. It is **invalid for that
  metric**. The defect, source-index fix and independent sealed-record
  check are preserved in [the scorer review](TEMPORAL_SCORER_REVIEW_V5.md).
  Neither fitting, collection, raw forecasts nor acceptance thresholds
  changed. [Corrected scorer run 41842756041](https://github.com/robosys-labs/cemm/actions/runs/41842756041)
  passes **1,217 tests**, original historical source locks and preflight.
- [Complete saved scoring](results/temporal-v5/scored/results.json) ·
  [posthoc balanced-twin calibration audit](results/temporal-v5/scored/latent-calibration.json).
  Scores come from the sealed bank and the originally declared hidden
  physical outcomes; no challenge-driven refit.

## Measured development results

| Same 9,600 priced contexts | Two-scalar temporal | G5 v1 scoped rule |
|---|---:|---:|
| Final correct with cheap, perfect verification | **9,580** (99.79%) | 9,380 (97.71%) |
| Cheap clarification requests | **4,420** | **2,480** |
| Mean net utility, fee 0.05 | **0.974896** | 0.964167 |
| Confident wrong parent/sibling/sentinel predictions | **0** | not a matching probability metric |

The candidate buys 200 more correct final choices but asks **1,940
additional questions** (78.2% more). It violates the protocol's
fewer-or-equal-query requirement; the positive 0.01073 net-utility
difference alone does not override that failure.

For the temporal candidate, **zero of 960 indistinguishable pre-probe
twin pairs** received a confident decision at threshold 0.95. The
saved PRE probabilities instead sit roughly between 0.10 and 0.90,
so abstention is a *threshold effect*, not correct probabilistic
uncertainty. On these 960 equal-latent paired contexts, mean binary
belief Brier is **0.408451** versus ideal **0.250000**, and mean
belief NLL **1.195487** versus ideal **0.693147**. Its calibrated
belief claim must therefore be rejected. The model makes **20**
confident wrong post-probe decisions and abstains on **1,120**
post-probe decisions across conditions.

Held-out **selected-payoff** NLL is **0.539345** versus 0.693163
for uniform two-meaning predictive control, with mean selected-payoff
Brier **0.181296** and descriptive ten-bin ECE **0.012861**.
This is a different prediction target from the miscalibrated
persistent-meaning posterior; the favorable payoff scores cannot
be substituted for belief calibration. The previous one-scalar,
latest-receipt and no-memory decisions remain in the complete
per-condition report. All corrected gates and adverse outcomes
appear in the machine-readable saved score.

## Confounds and architectural assessment

1. **Dependent seed views:** The supposedly new noise stream is
   derived from split salt, site index and enumerated case index,
   **not law/seed**. The ten condition-level goal/query totals are
   exact repeats despite slight G3 forecast differences, so
   9,600 contexts cannot be reported as independent environmental
   generalization. Do not patch the opened challenge salt and rescore.
2. **Observation-selection mismatch:** The contradictory epoch
   payoff was deliberately forced by the task generator. The learner
   treats it as an ordinary generative emission, creating an
   unjustifiably strong posterior for one persistent interpretation
   under genuinely 50/50 matched counterfactual alternatives.
   This is a potential selection/likelihood misspecification, not
   proof that more neural parameters are inherently required.
3. **Upper-bound fitted transition:** `h=0.5` in every condition
   maximally resets the persistent-state prior at the supplied epoch.
   The model has not established the desired evidence-preserving
   temporal persistence beyond the prior rule.
4. **Provided structure:** two candidate meanings, physical action
   menus, G3 likelihoods, entity handles, explicit epoch flags,
   scope hierarchy, verification authenticity and perfect optional
   clarification are supplied. Source-specific reliability is
   *not learned*. The physical challenge families were already
   opened during G3/G4 and have no independent custodian.
5. **Research-only scope:** the one-process simulated snapshots do
   not prove crash-safe memory, actual natural language, open-world
   truth, Wikipedia utility, or production authority.

## Smallest justified next tranche

**Freeze a new, genuinely independent G5 task before any further fit.**
Use independent per-law/seed/world noise and lineage, predeclare the
observation-selection process (especially whether and why a
contradiction was sampled), include source reliability and a separate
calibrated latent-meaning proper-score gate, and preserve the
cost-matched, goal-aware G4 information-value control. Evaluate
whether the *same minimal two-hypothesis filter* can be calibrated
under an identifiable observation law **before adding another
neural layer or a third latent mode**. Preserve the present invalid/
negative outcomes as closed regression evidence, never as a fresh
challenge success.

No runtime cutover or G6–G8 promotion follows. G5 remains
**NOT_ADMITTED**; the inclusive 2,000-line research target remains unmet.
