# G5 v6 — independent nuisance/selection test of unchanged temporal belief

**Parent:** [PR #90](https://github.com/robosys-labs/cemm/pull/90), commit
`191bb84ece9f7c942bd9f7ba3a74189019953d16`.
**Status:** frozen before authoring new generator, fitting, challenge collection or scoring.
This is a **research development** transfer test, *not* externally
blind scientific admission: the frozen G3/G4 physical menus are reused and
the generation source is visible to its authors.

## Question

Was v5's poor latent calibration and high question burden caused by
(1) forced outcome-conditioned contradiction selection, (2) shared noise
across law/seeds, or (3) an actual limitation of the same two-parameter
belief family? Run the **unchanged** `temporal_belief_v5.probability`,
`causal_nll` and `fit` first. Do not modify accepted G3/G4 weights,
G5 v1 memory, the v5 raw/scored artifacts, or the production runtime.

## Fixed causal generation law and information boundary

Use exactly the existing `transfer_task.catalogue(law, split)` and
metadata-only `revision_study.select_triples`. Six disjoint
site/layout triples per law/seed; exactly 32 fresh opaque-world episodes
per triple (192 episodes per condition). Every episode has a root `qor`,
independent `nav`, regional `qor`, local pre-epoch `qor`, and
local post-epoch `qor`. Generate 3 observed physical payoffs per
root/sentinel/region/local-pre and 3 local-post payoffs (15 physical
receipts total), followed by an unverified *truth-independent* assertion.
A true epoch is supplied only on the first local-post event.

Initial hidden meanings are independent fair bits. The **local** persistent
meaning flips at its genuine epoch with probability 0.20. Each scheduled
physical reading uses a selected G3 action/forecast conditional on the
currently true local meaning, then independent event-local observation
inversion with source reliability error probability 0.03 for source A
or 0.18 for source B in TRAIN; TEST uses 0.03 / 0.24 for A/B.
Sources/episode times/actions are selected **without consulting meaning,
observed payoff, whether a contradiction occurred, or future reward**.
Never force or filter a contradictory observation. Include non-informative
menus without case exclusion. Source IDs are visible; source error rates,
the flip schedule and actual true meaning are evaluator-only.

Use distinct fixed SHA-256 domains for split, law, seed, physical site
lineage, world number, source, time, and each independent random draw.
No law/seed/noise reuse. An opaque public ID is drawn from a separate
domain, not by concatenating hidden bit values. The evaluator must audit
the 10 independent noise streams, distinct train/test lineages and no
outcome-conditioned selection before permitting any challenge score.

Train a **single globally shared (h,e)** from NAND law seeds 7/11/23,
using every observed *selected physical payoff* and no hidden meaning
labels. Fixed original grid: `h ∈ (0.05,0.15,0.35,0.5)`,
`e ∈ (0.01,0.05,0.1,0.2)`; ties smaller h then e. Publish actual fitted
values, full grid, number of observed outcomes, runtime and source SHA
**before** challenging. Evaluate the unchanged shared fit on all NAND/NOR
× five seeds; new challenge task lineages and noise draw streams must be
disjoint from all training data. This is prospective *task-family* testing,
not independently held physically blind worlds.

## Bounded goal-aware decision policy

At two checkpoints (after the first post-epoch observation, then after two
additional independent observations), and for retained root, sibling and
sentinel meanings, collect frozen posterior probabilities or the
unmodified v1 rule's discrete state. **Never pass evaluator labels to
collection.** Evaluate two physical actions under externally supplied
2 × 2 reward tables: direct and reverse conflict, indifferent goals,
and low-margin choices, balanced by public index independent of truth.
A perfect scoped verification may be bought **only** at the first
post-epoch checkpoint. Price/availability is publicly fixed at
0.05 / 0.75 / unavailable. For every arm, calculate the same
value of perfect information
`VOI = E[max_a R(z,a)] - max_a E[R(z,a)]`; ask only if available and
`VOI > price`. Return the hidden meaning **only after paying**, and
retain it for the second checkpoint. Other scopes must not receive that
answer. Do not ask on indifferent goals, unavailable replies or
nonbeneficial high-cost information. This is a supplied planner, not
proof the learner acquired goal language.

Compare: (a) trained temporal posterior; (b) unchanged dated-evidence
G5 v1 rule converted to p=0, .5 or 1 *only for action choice*;
(c) latest physical receipt; (d) no-memory p=.5; and
(e) matched fixed v5 h=.5/e=.1 historical parameters. A
known-generative-parameter oracle may be reported only as a separately
labeled reference, never as a learned arm.

## Prospective scores, gates and publication sequence

Report all 1920 episodes / 10 conditions, with **no case dropped**:
posterior proper Brier/NLL and ten-bin calibration for *persistent
meaning* after first and final observations; selected-payoff predictive
NLL/Brier separately; source/epoch/correction partitions;
number of gross-goal-optimal actions, regret/net utility, paid
clarifications, retained-answer utility, denied/irrelevant questions,
high-confidence errors on parent/sentinel, scope isolation,
repeat receipt IDs, and actual CPU/parameters/lines. Keep dependent
measurements distinct from independent world/seed counts.

**KEEP_V6_TEMPORAL_TRANSFER** only if the same trained model beats
the v1 rule's meaning Brier *and* final net utility in both laws,
uses no more paid queries at equal or better final correctness,
does not worsen any of the five seed net utilities, has no
extra confident parent/sentinel mistakes, and wins on observed
payoff NLL against no-memory. All integrity/equivalence gates must pass.
Else record `REVISE_V6` or `STOP_INVALID_DATA`. Proper calibration
alone does not establish learned general semantics.

Publication order is strict:
1. Commit this protocol before implementation.
2. Publish minimal generator and TRAIN-only invariants. No challenge
   generation by CI at this stage.
3. Run TRAIN once; publish fitted scalars and grid before any challenge.
4. Collect raw challenge probabilities/action inputs **without oracle**;
   publish all immutable raw files, content hashes and process receipts.
5. Score raw against a separately read evaluator oracle, publish all
   adverse outcomes and one final decision. Do not refit or patch a
   challenge failure into a pass.
6. Preserve all earlier G1–G5 studies, source locks and active production
   authority. G6–G8 and 2,000-LOC target remain open.
