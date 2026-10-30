# Continuation study v1 — retained result and decision

**Frozen decision: `STOP_INCOMPLETE_RUN`. G1 remains `NOT_ADMITTED`.**
The artifact collection completed and its manifest retains all 57 listed files.
The scientific run is not participant-complete: empirical feedback contradictions
terminated episodes and left required later forecasts `UNPRODUCED`. The first
decision rule therefore stops the comparison before the later superiority rules.
This decision is preserved without dropping controls or changing denominators.

The shared learner nevertheless produced a clear descriptive continuation result:
704/704 fixed queries correct at each of five seeds, including every held-out
query. A separate limitation is equally clear: it answered only **7/16 held-out
self-contact queries correctly at every seed**, with mean confidence 98.8431%.
These findings do not establish a complete domain solution or admit G1.

Authoritative artifacts: [decision](results/continuation-v1/decision.json),
[summary](results/continuation-v1/summary.json.xz),
[result manifest](results/continuation-v1/manifest.json), and
[training inventory](data/continuation-fit-v1/training.json).
The [protocol](continuation_protocol_v1.json) and
[study guide](CONTINUATION_STUDY_V1.md) define the task and decision order.

## What was frozen and completed

Source/data prefit commit: `994054d892b14e4d18835758e9ee1837f394d911`.
Actual checkpoint/plan commit: `edb6ab2abad3575ed6ba4f67fad95d8aae4d0f00`.
The [bound plan](data/continuation-fit-v1/plan.json) identifies real checkpoint
bytes before collection. No source, hyperparameter, checkpoint-selection, or
calibration change was made in response to evaluation results.

All **15 neural fits completed 128 updates at 562 parameters**, using the same
training-input hash. Each update delivered 334 observed action events and 1,476
visible bits. Shared/reset initial tensors matched within seed. The three arms
used seeds 7, 11, 23, 37, and 53; selection/calibration tapes remained unused.
Four empirical controls were each fit once. Their five collection labels repeat
the same fitted control; they are not five independent empirical replications.

Evaluation has 320 views of 168 physical draws. The 704 continuation queries
comprise 32 in-family queries and 672 held-out queries. The latter come from 120
physical draws in 30 eligible family/entity/contact-count cells. Sixteen separate
self-contact queries and all acquisition/other actions remain recorded. Ordinary
first-contact acquisition is counted within each schedule's contact budget.

## Neural results by seed

IF is exactness on the 32 in-family continuation queries. OOD is the primary
macro: equal families, then eligible cells, then physical draws; each draw averages
its fixed query positions across both related views. Values below are percentages.

| Seed | Shared IF | Shared OOD | Reset IF | Reset OOD | Flat IF | Flat OOD |
|---|---:|---:|---:|---:|---:|---:|
| 7 | 100.000 | 100.000 | 50.000 | 59.635417 | 3.125 | 11.834491 |
| 11 | 100.000 | 100.000 | 50.000 | 60.141782 | 15.625 | 10.821759 |
| 23 | 100.000 | 100.000 | 50.000 | 60.575810 | 28.125 | 8.883102 |
| 37 | 100.000 | 100.000 | 50.000 | 61.140046 | 9.375 | 8.304398 |
| 53 | 100.000 | 100.000 | 43.750 | 60.706019 | 18.750 | 8.000579 |
| Mean | 100.000 | 100.000 | 48.750 | 60.439815 | 15.000 | 9.568866 |

Shared passed every recorded competence check: 32/32 IF queries and 16/16 IF
reversed-pair conjunctions per seed, 100% continuation support, zero unchanged-bit
errors, and IF nonregression against flat. All 136 continuation role pairs were
exact, and all four held-out family macros were 1.0 at every seed.

Shared-minus-flat OOD differences, in the seed order above, were
`[0.8816550926, 0.8917824074, 0.9111689815, 0.9169560185, 0.9199942130]`.
Their mean was **0.9043113426**, or **90.431134 percentage points**; all five were
positive. The prespecified one-sided sign reference is **p = 1/32 = 0.03125**,
conditional on this frozen bank and the assumed independent initializations.
These retained quantities do not override STOP or establish physical-world
generalization. Related views and query positions are not independent samples.

Flat's mean IF accuracy was only 15%. The full gap therefore cannot be attributed
specifically to compositional extrapolation: the reference also learned the
development task poorly at this fixed budget. Equal parameter count and observed
exposure do not equalize capacity, inductive biases, or consumed compute.

## Empirical controls and the reason for STOP

These are per-label counts, identical across the five repeated labels. Accuracy
uses planned denominators; an abstention or unproduced forecast is incorrect.
Support counts mean answered forecasts, not guaranteed positive mass on truth.
The empirical OOD macro uses the same family/cell/draw weighting as the neural one.

| Control | IF % | OOD macro % | Correct /704 | Supported /704 | Abstained | Unproduced | Terminal failures |
|---|---:|---:|---:|---:|---:|---:|---:|
| Local | 37.500 | 26.142940 | 177 | 323 | 199 | 182 | 109 |
| Contact | 37.500 | 5.396412 | 42 | 42 | 560 | 102 | 42 |
| First-contact | 37.500 | 10.286458 | 76 | 76 | 526 | 102 | 42 |
| Prefix | 0.000 | 0.000000 | 0 | 0 | 686 | 18 | 8 |

Continuation production coverage was 522/704 local, 602/704 contact and
first-contact, and 686/704 prefix. Supported coverage was respectively 45.8807%,
5.9659%, 10.7955%, and 0%. The perfect conditional accuracy of the few supported
contact/first-contact queries does not describe their planned-query performance.

All terminal errors reported `visible evidence outside empirical support` during
feedback. Per label, contact and first-contact each failed on 42 acquisitions;
prefix failed on eight acquisitions. Local failed on 47 acquisitions, 61 later
continuation contacts, and one observe action. Across repeated labels there are
1,005 failure records. Later all-action `UNPRODUCED` counts per label are local
233, contact 128, first-contact 128, and prefix 24. The collector retained these
failures and completed its artifact inventory; no failed trajectory was repaired.

The strongest empirical planned OOD macro was local at 26.142940%, below shared's
mean minus 0.01. That later-rule comparison is descriptive because STOP already
applies. Neural, untrained-shared, and no-change collection had no terminal failures.
See the [local](results/continuation-v1/all-action-empirical_local.json.xz),
[contact](results/continuation-v1/all-action-empirical_contact.json.xz),
[first-contact](results/continuation-v1/all-action-empirical_first_contact.json.xz),
and [prefix](results/continuation-v1/all-action-empirical_prefix.json.xz) reports.

## Reset, untrained, no-change, and self-contact

| Arm | Mean OOD macro % | Mean all-action exactness % | Mean self-contact exactness % |
|---|---:|---:|---:|
| Shared | 100.000000 | 88.265683 | 43.750 |
| Reset | 60.439815 | 67.099631 | 43.750 |
| Flat | 9.568866 | 11.867159 | 22.500 |
| Untrained shared | 2.688079 | 2.981550 | 11.250 |
| No-change | 43.706597 | 48.339483 | 43.750 |

All five arms answered every planned continuation query. Reset/untrained results
show that the trained persistent shared configuration differs substantially from
these fixed controls; the study does not isolate every possible causal mechanism.
Shared's all-action result is below 95%, and does not replace the original gate.

Shared made nine supported self-contact errors per seed. Its mean confidence on
the 16 self queries was 98.8431% (seed range 98.3123–99.0351%); mean NLL was 2.93603
and Brier 1.10765. The first self-contact was prospectively separate from ordinary
continuation, so it does not change the 704-query result. Its poor accuracy and
high confidence remain a substantive domain limitation, not a warm-up exclusion.

The retained trace/source audit found that shared and reset copy the entire
pre-world on all 16 self queries: seven active-zero cases succeed; nine active-one
cases fail, with no background-bit errors. Existing [alias conditioning](domain_kernel.py)
uses `q_m(bb | x,x) / (q_m(00 | x,x) + q_m(11 | x,x))` before mode mixing.
For ordinary distinct operands 11, the physical outcomes are 10/01. Conditioning
on equal outputs discards those principal outcomes and normalizes learned error
tails. This identifies an underdetermined transfer assumption; it does not prove
that the unchanged function class cannot learn self-contact from observations.
The training tape has no self contacts; its 63 ordinary `11` contacts yield only
`01` or `10`. At the conditional-distribution level, keeping correct off-diagonal
mass at `1-epsilon` while assigning diagonal masses `epsilon*r` and
`epsilon*(1-r)` leaves the distinct-target loss unchanged, but makes the self-zero
probability equal to `r`. The retained source/trace audit establishes this missing
identification; it does not measure the checkpoint's individual per-mode tail masses.

## Probability quality and uncertainty

The following are means of the five seed-level summaries over all 704 continuation
queries. NLL uses natural logarithms; Brier is the joint-world sum-form score.
Each listed arm has complete forecast coverage, so these are overall query means.

| Arm | NLL | Brier | Fixed ECE10 |
|---|---:|---:|---:|
| Shared | 0.00796983 | 0.00019308 | 0.00789992 |
| Reset | 0.61770918 | 0.43646032 | 0.04998659 |
| Flat | 4.44577503 | 1.03757807 | 0.23150559 |
| Untrained shared | 3.64724155 | 0.97088175 | 0.03386903 |
| No-change | +infinity | 1.11647727 | 0.55823864 |

Shared's continuation NLL ranged 0.006608–0.009266 across seeds. Its ambiguous
acquisition mean NLL was 0.69668428, an excess of 0.00353710 above ln(2); Brier
was 0.49999020, an empirical excess of -0.00000980 above the 0.5 expected floor.
The small negative finite-bank Brier excess is retained without clamping.
Acquisition mean MAP exactness was 50.6579%, consistent with this distinct task's
ambiguity; it was not used as an identifiable-query competence gate.

Empirical overall NLL/Brier means remain unavailable because support is incomplete.
Contact and first-contact conditional continuation losses are zero on only 42 and
76 supported queries. Local's conditional continuation NLL is infinite, with 66
zero-mass true outcomes; its conditional Brier is 0.67277541. Prefix supports no
continuation queries. No-change has 393 infinite-NLL continuation points per label.
ECE here is a fixed within-bank diagnostic; low ECE alone does not establish useful
accuracy or general calibration. No calibration transform was fitted.

## Actual measured costs

Fit times sum the five neural fits or the single deterministic empirical fit.
Collection times retain all five executions for every arm, including reused controls.

| Arm | Fit CPU s | Fit wall s | Collection CPU s | Collection wall s |
|---|---:|---:|---:|---:|
| Shared | 187.292 | 187.334 | 45.793 | 45.823 |
| Reset | 210.682 | 210.728 | 42.426 | 42.444 |
| Flat | 152.549 | 152.698 | 34.657 | 34.671 |
| Empirical local | 0.035 | 0.035 | 17.574 | 17.577 |
| Empirical contact | 0.033 | 0.033 | 27.096 | 27.113 |
| Empirical first-contact | 0.033 | 0.033 | 18.224 | 18.231 |
| Empirical prefix | 0.035 | 0.035 | 22.489 | 22.503 |
| Untrained shared | 0 | 0 | 44.781 | 44.907 |
| No-change | 0 | 0 | 15.035 | 15.043 |
| Total | 550.659 | 550.897 | 268.075 | 268.312 |

Neural fitting alone used 550.523 CPU seconds; no fit hit its 300-second ceiling.
Every neural fit recorded 42,752 path-model evaluations and 1,216,512 candidate
worlds. Across each arm's five collection traces, shared/reset/flat/untrained each
recorded 381,160 candidate expansions; observed peaks were eight live histories
and 512 expansions. These are measured work counts, not capacity equivalence.

Maximum reported process RSS was 350,952 KiB during fitting and 674,120 KiB during
collection. RSS is the whole-process lifetime high-water mark, not an isolated
per-arm allocation. Timing sums cover the reported fit/collector sections and do
not measure end-to-end artifact compression, validation, publication, or human review.

## Interpretation boundary

The data are public and share authorship with the implementation. Entity counts
were familiar; the exact oracle is conditional on the supplied binary-contact law.
Blueprint disjointness excludes canonical copies, not every repeated atomic context.
The architecture supplies locality/factorization, two modes, identifier equivariance,
and an alias-conditioning rule. This is a bounded development comparison with
reported biases, not independent discovery of general composition or new physics.
The frozen STOP, self-contact failure, and weak flat IF fit all remain part of the
record. None authorizes automatic architecture growth or same-bank retuning.

## One bounded next action

Prespecify a fresh evidence discriminator using the unchanged model and a matched
fixed budget: ordinary-only training versus a fixed replacement tranche of observed
self-contact outcomes, followed by fresh held-out self contacts starting at bit 0
and bit 1 (both correct next values are zero), plus continuation regression checks.
This tests learned alias transfer, not zero-shot self transfer.
The fresh protocol must distinguish terminal participant-model failure from
interrupted execution before fitting. Retain v1 and its successful continuation
configuration unchanged; add no hardcoded self-contact rule, new architecture, or
v1 retry. The retained trace/source diagnosis above is already complete.
