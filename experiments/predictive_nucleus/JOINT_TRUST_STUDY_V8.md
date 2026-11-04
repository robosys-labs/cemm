# G5 v8 frozen prospective joint meaning / source-trust representation

**2026-11-04 · prospective internal development, no independent scientific
admission.** Parent: [PR #93](https://github.com/robosys-labs/cemm/pull/93),
whose v7 score is **opened** and unpromoted. The existing bounded G5 v1
scoped rule remains selected; G1–G4, v5–v7, production and G6–G8 remain
untouched.

## Question

Can *joint online uncertainty* about persistent meaning and which public
sensor is currently reliable explain a noisy contradiction versus a lasting
revision, without using gold meanings, sensor inversion labels, actual
latent mode, participant-order labels, or post hoc query suppression?
A single source-trust scalar held fixed per source failed on v7's reversed
source scenario. This is **one representation diagnostic**, not a new
grid sweep, neural layer, or post-score fix.

## Candidate: finite, bounded exact joint Bayesian state

For every episode maintain one normalized table of
`P(root,region,local,sentinel,source_trust_mode | observed payoffs)`,
where four meaning variables are binary and the shared trust mode is
binary: at most **32 states**. Prior is uniform 1/32, not from hidden
oracle. The trust mode represents which named source has the lower
inversion risk; its two source-likelihood profiles are the **permutations
of v7's *already TRAIN-fitted* reliabilities**: (e_A=.03,e_B=.20)
and (e_A=.20,e_B=.03). These are *hypotheses* derived from TRAIN, not
privileged knowledge that source reversal occurs in TEST.

At a public epoch marker (one per world), independently transition
local meaning and trust mode with the *same inherited, TRAIN-fitted*
hazard `h=.15`. This parameter tie adds **zero fitted scalars**;
it is a restrictive hypothesis, not an assertion that true mode shifts
must correlate with meaning shifts. The two transitions occur
independently; no hidden-change labels enter. At any selected physical
receipt `(a,b,outcome,source)`, use the correct binary sensor
likelihood `e+(1-2e)*a` or `e+(1-2e)*b` according to the
persistent meaning variable, then condition jointly and renormalize.
A public unverified assertion has no likelihood. No memory reset,
gold role or task truth input. Shared trust posterior may update
parent/sentinel beliefs; **all such retention changes are scored**.

No candidate parameter is fitted on v8 TRAIN or TEST; v7's previously
published `h,e_A,e_B` are frozen. Online mode inference uses only
actual observed selected payoffs. No posterior mode labels appear in
TEST forecasts; **trust-mode probabilities** may be saved as public
model forecasts and scored only by the independent evaluator.

## Prospective paired source-shift task

Use the inherited frozen NAND/NOR G3 physical forecast menus only.
A fresh v8 SHA namespace is distinct from v6/v7. 10 conditions =
NAND/NOR × seeds 7,11,23,37,53. Six disjoint metadata-selected physical
triples per condition; for each triple 16 base worlds × **two twins**,
192 episodes per condition, **1,920 episodes / 960 pairs** total.

Twins share **exactly identical** public root/region/sentinel/local-pre
records, evidence IDs, timestamps and sources through time 8, but have
opposite true local-post meanings (one lasting change, one stable).
The stable/flip role is assigned by a hidden deterministic hash, so
neither public ID nor record order is a declared truth label. Post-epoch
action/source schedule is matched across twins; post-epoch observations
have independent noise. Meaning and source-change status are *independent*.
No generator branch conditions sources, actions, evidence inclusion,
physical menus, query fees or messages on true meaning or contradiction.
The pre-transition belief for the *post* meaning must stay
non-confident on matched twins; same prehistory must produce the same
pre-score for both twins. No twin or source mode labels enter collection.

Source reliability inversion rates (evaluator-only, not model inputs):
- TRAIN: independent 50/50 starting normal/reversed per base pair;
  a 20% independently sampled *epoch* trust-orientation switch,
  used **only** for implementation checks, not model fitting or
  hyperparameter tuning.
- CHALLENGE seeds 7,11: stationary normal (.03/.20) throughout;
  seed 23: degraded B (.03/.30) throughout;
  seed 37: stationary reversed (.20/.03) throughout;
  seed 53: normal before epoch, reversed from epoch onward.
  All have exactly the same paired stable/flip counts, source
  selection probability .5 and sampling schedule. Source switch
  at time 9 is a generator fact; the learner sees only a public
  epoch opportunity, not whether either latent actually switched.
  The candidate's mode transition hazard stays .15 unchanged.

Five scored views = after first post-epoch selected payoff, after two
additional payoffs, final sibling, root and sentinel. The shared
external goal/verification policy and fees (.05/.75/unavailable)
are exactly v6's `goal_policy_v6`; a perfect answer is applied
*only after purchase*, to both post-epoch actions in the same world.
It does not feed other-scope beliefs or cross-world state.
The 960 matched pre-epoch twin pairs test indistinguishability.
No question is generated from hidden truth.

## Matched controls and gate

On **the identical** histories and goal tables:
1. Joint 32-state candidate above, with no extra fitted values.
2. Frozen v7 source filter `h=.15,e_A=.03,e_B=.20` (same reliable
   forward observation equation), unpromoted.
3. Frozen equally TRAIN-fitted v7 neutral `h=.15,e=.10`.
4. Retained G5 v1 rule `0,None,1`, mapped `0,.5,1` only for
   goal choice and proper-loss reference. Keep the smoothed rule
   as an optional benchmark, never a candidate.

All 1,920 world IDs and 28,800 observed payoffs count, no case dropped.
Score selected-payoff causal NLL/Brier (one-step before each observed
reading); post-epoch first and final meaning Brier/NLL; 95%-confident
wrong states overall and for root/sentinel; gross-optimal actions,
net utility/action, paid questions and realized question ROI vs
the policy's own *no-question* trajectory, split by law, seed,
source regime, real stable/flip, epoch source and twin pair.
Mode truth is evaluator-only and may be reported as a *separate
diagnostic*, not a training or action input. Report matched twin
pre-belief equality, pre-confidence before any post-epoch outcome,
source-mode NLL/Brier, and worst-seed utility. Runtime and
parameter/state-count budgets reported; 5 views/world are correlated.

**`KEEP_JOINT_V8_DEVELOPMENT`** iff all these prospectively fixed
gates hold on the fresh challenge:

1. All source/sha/twin/pair/no-leak/invariant checks pass (otherwise
   `STOP_INVALID_V8`).
2. **Overall** meaning Brier strictly better than both fixed
   temporal controls, and the first post-epoch *genuine flip*
   Brier no worse than both controls.
3. Reversed and within-episode-shift regimes **separately** improve
   both first-post-epoch meaning Brier and net/action against fixed
   source-v7, without extra confident parent/sentinel mistakes
   against the fitted neutral control.
4. Overall **goal** net/action no worse than both temporal controls
   and retained rule, optimal-action rate no worse than fitted neutral,
   paid requests **no more** than fitted neutral, and no seed
   regresses in goal utility against fitted neutral **or** retained
   rule.
5. **Zero additional** wrong ≥95%-confident root/sentinel predictions
   relative to the fitted neutral control; at least 100% of the
   paired pre-epoch post-meaning forecasts match and abstain at .95.
   A single seed/regime failure prevents KEEP, regardless of mean gains.

If intact but any scientific gate fails: `REVISE_JOINT_V8`, retain
G5 v1 baseline, and investigate identifiability/representation
rather than expand fixed parameter grids or reopen TEST.

## Publication and immutability

1. Commit this protocol before generator, candidate, TEST or scorer.
2. Commit candidate, new generator, collector, evaluator and
   *TRAIN-only* preflight. No TEST generation in CI initially.
3. Publish a provenance receipt of frozen v7 parameters, exact
   source/model/test snapshot and TRAIN-only code validation,
   before any TEST forecast collection.
4. Collect all new TEST forecasts *without importing* evaluator
   labels; commit immutable raw source manifests and rows.
5. Only after raw commit, execute separate truth-joined scorer
   unchanged; publish all adverse strata, per-seed and raw totals,
   final decision and updated roadmap. No refit, retries
   selecting results, or post-score criterion change.
6. The physical family is inherited, previously opened and
   authored by the same team. **G5 NOT_ADMITTED** regardless of
   bounded v8 outcome; no G6, no production integration.
