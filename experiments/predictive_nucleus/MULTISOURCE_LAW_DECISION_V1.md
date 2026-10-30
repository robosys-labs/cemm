# Multisource law v1: KEEP_MULTISOURCE_LAWS

Tracking: [#22](https://github.com/robosys-labs/cemm/issues/22), [PR #65](https://github.com/robosys-labs/cemm/pull/65). Recorded 2026-10-30.
**Status: KEEP_MULTISOURCE_LAWS. All 30,720 planned forecasts completed in the single collection.**
G1 development remains PROCEED_TO_G2; formal scientific admission remains
NOT_ADMITTED. All earlier STOP, REVISE and KEEP decisions are preserved.

## Why this was the next measurement

Review of the completed correlation challenge found no invalidating result
defect. It did correct the earlier proposal to add a ternary action: a limit on
the inputs to one atomic event is not a limit on composing pairwise events.
Existing XOR contacts `(a,t); (b,t)` already combine two independent external
sources. The earlier reversed-fork evaluation also includes physical fan-in.
The [assumption review](JOINT_CORRELATION_DECISION_V1.md#assumption-review--2026-10-30)
records the probability-control and dependent-count qualifications.

This study asks whether **observed consequences teach different dynamics, and
those dynamics compose under held action schedules**, using the unchanged
562-parameter model and native training, checkpoint and prediction APIs.
No new action, neural factor, memory workspace or checkpoint schema is introduced.

## Fixed paired design

Two datasets share initial states, opaque entity handles, episode geometry,
action tapes, observation masks and exposure. Their outcomes follow separate
laws: NAND sets the target to `1 - source*target`; NOR sets it to
`(1-source)*(1-target)`. The source is unchanged. Every episode has one persistent
hidden source-slot mode; both modes and global role reversals are balanced.
The learner receives only the existing observed-input schema, with no law name,
mode, physical role, family or oracle label.

| Inventory per law | Training | Evaluation |
|---|---:|---:|
| Episode views | 128 | 384 |
| Physical context lineages | 32 | 96 |
| Role pairs | 64 | 192 |
| Contacts / forecasts | 256 | 1,536 |
| Identifiable forecasts | 128 | 1,152 |
| Ambiguous first forecasts | 128 | 384 |
| Primary composition forecasts | 0 | 768 |
| Visible post-action bits | 1,152 | 6,912 |

All eight `(a,b,t)` states occur at each entity count 3–6. Training is
`contact(a,t); contact(t,b)`. With A=`contact(a,t)` and B=`contact(b,t)`,
evaluation holds AAB, ABBA and ABAAB schedules. Primary composition starts at
zero-based step 2. Physical fan-in and fan-out each have 192 evaluation views.
The first full feedback identifies the persistent mode under either law; later
forecasts are identifiable. The expected best pooled all-action MAP accuracy is
87.5%, so that pooled rate is not used as a 95% gate. These are closed-loop
one-step forecasts with full intermediate feedback; observed states carry earlier
source effects. This does not test a 3–5-step open-loop rollout from the anchor.

At 64 AAB step-1 contexts with initial `a=t` (32 zero, 32 one), the delivered
histories and next actions are identical across laws but the required worlds
differ. Both laws map 00 to 1: the discriminator is the **second** repeated
contact after the shared feedback, not the first 00 contact.

Five seeds (7, 11, 23, 37, 53) each produce two fits from identical initial
tensors: ten fits, each 128 updates with a 180 CPU-second ceiling, fixed learning
rate 0.02 and the existing resource bounds. Matching checkpoints are compared
with the other law's checkpoint on each bank. These controls match architecture,
initialization and prescribed exposure. Shared initial checkpoints are retained
for provenance, not scored as an additional baseline. There are 20 planned
collections and 30,720 forecasts. Law twins, modes and role reversals are dependent
views, not independent replications.

## Prospective decision

The [locked protocol](multisource_law_protocol_v1.json) fixes all criteria before
fitting. Each matched law/seed/family requires at least 95% identifiable complete
world and identifiable role-pair accuracy, complete support coverage, zero
identifiable regressions relative to the crossed checkpoint, zero unsupported MAP
worlds, and zero errors on coordinates known to retain a fixed value. Mean joint
oracle KL must be at most 0.05 nats in each information stratum; maximum ambiguous
TV is at most 0.1. Every primary family/physical-flow cell has the same accuracy,
coverage and preservation requirements. **Zero unsupported MAP worlds makes the
effective primary exactness requirement 100%, because these targets are identifiable.**

At every shared-history contrast, each matching model must give its own required
world at least 0.9 probability; the NOR model gives the NAND world at most 0.1,
with a NAND-minus-NOR probability gap of at least 0.8. Each law/seed must improve
mean critical NLL by at least 0.1 nats over the crossed model. Full crossed
distributions must equal the corresponding other-bank matching distributions at
identical histories. Predictions retain all soft tails; no oracle renormalization
or removed abstention denominators are allowed.

Incomplete prescribed fitting stops before collection. Incomplete execution or
invalid binding stops the study. Any failed competence criterion yields
REVISE_MULTISOURCE_LAWS; otherwise KEEP_MULTISOURCE_LAWS. Every attempt and local
regression is retained. There is one fit/collection attempt, no selection or
calibration fitting, and no retuning on this bank.

## Execution and interpretation boundaries

The runner prepares observed inputs and evaluator assets separately, verifies
source and protocol hashes, and requires public source/data commitment before
fitting. Actual trained checkpoints and native plans are committed before
collection. It records all 20 traces before reading evaluator targets for scoring.
The generator's Boolean implementation and the oracle's separate truth-table
implementation are checked using whole-history enumeration tests.

Training/evaluation blueprint and template overlap is zero. Evaluation overlap
with six historical archives is zero. Reused two-contact training geometries
from older banks are disclosed in the prepared audit. Successful old V2 weights,
frozen protocols and historical outcomes remain unchanged; crossed-law
differences do not measure regression of those historical weights.

Stable handles, two persistent modes, pair factorization, state enumeration and
Bayesian filtering are supplied. Pairwise outcome likelihoods, role distinctions
and background persistence are learned. This tests two separately learned laws;
it does not establish one unified checkpoint, zero-shot transfer to an unseen
law, atomic ternary effects, simultaneous timing, general calibration, architecture
superiority or independent scientific custody.

The stage commands are `python -m experiments.predictive_nucleus.multisource_law_run`
with `prepare --output DATA`, `fit --data DATA --output FIT`,
`bind --data DATA --fitted FIT`, then `collect --data DATA --fitted FIT --output RESULTS`.
The required public commits separate prepare/fit and bind/collect.

## Prefit and checkpoint record

Public source/data freeze: `682672eb3ff30ceb8437b808b6058c9c673c4380`.
All **700 isolated tests** passed locally in **89.796 seconds**, all 24 locks
match, and [freeze invariant CI](https://github.com/robosys-labs/cemm/actions/runs/41103517083)
passed. All ten fits completed 128 updates each (**1,280 updates** total), using
**92.190741 CPU seconds** and **92.206629 fit-region wall seconds** in total.
No fit reached its 180-second ceiling or required a retry. The exact native
[training manifest](data/multisource-law-fit-v1/training.json), five initial
checkpoints, ten trained checkpoints and both evaluation plans are retained.
These exposure and provenance records are separate from the competence results below.

## Result: KEEP_MULTISOURCE_LAWS

The [decision](results/multisource-law-v1/decision.json) passes for both laws at
all five seeds. Actual checkpoint/plan commit
`25ae19b317c5b7dbfc487fa5204fb5da5f0e7420` was public before collection. All
**30,720 forecasts** were produced and answered; there were no missing records,
terminal failures or abstentions. The [artifact manifest](results/multisource-law-v1/manifest.json)
retains all 20 raw traces, both all-action reports and the complete summary.

Counts below combine five seeds within each law and arm. They are descriptive
counts over dependent views and a shared fixed bank, not independent world trials.

| Metric | NAND matched | NAND crossed | NOR matched | NOR crossed |
|---|---:|---:|---:|---:|
| Identifiable complete worlds | **5,760/5,760** | 2,836/5,760 | **5,760/5,760** | 2,772/5,760 |
| Primary composition worlds | **3,840/3,840** | 2,068/3,840 | **3,840/3,840** | 2,052/3,840 |
| Identifiable role-pair conjunctions | **960/960** | 0/960 | **960/960** | 0/960 |
| All-action realized MAP accuracy | 6,720/7,680 (87.5%) | 3,748/7,680 (48.80%) | 6,720/7,680 (87.5%) | 3,732/7,680 (48.59%) |
| Mean realized NLL, nats | **0.177005** | 3.447498 | **0.176762** | 3.298884 |
| Unsupported MAP worlds | **0** | 3,020 | **0** | 2,988 |
| Errors on coordinates known to retain a fixed value | **0** | 1,836 | **0** | 1,836 |

Every matched law/seed has **1,152/1,152 identifiable worlds**, **768/768 primary
worlds** and **192/192 role pairs** correct. Every primary family/physical-flow
cell passes. All residual matched MAP errors are the ambiguous first forecasts:
192/384 are correct per law/seed. The resulting 87.5% pooled score equals this
bank's expected oracle MAP rate; comparing it with other banks' pooled rates
would conflate different information mixtures.

All **320/320 common-history contrast pairs** pass. Matched NAND assigns
**0.991302–0.998410** to its required world; matched NOR assigns
**0.991901–0.998762** to its own. NOR assigns at most **0.00142143** to the NAND
world, and every NAND-minus-NOR separation is **0.991163–0.998049** (minimum
required: 0.8). Each crossed full distribution equals the other bank's matched
forecast at the same history. Minimum critical mean NLL gain is **7.543284 nats**
(required: 0.1). The same initialized predictor cannot produce these different
law-specific forecasts for identical inputs; the paired outcome learning changes
its predictive behavior. This is not an architecture-superiority comparison.

Worst matched family/stratum mean oracle KL is **0.005425 nats** (limit 0.05),
and maximum ambiguous TV is **0.007081** (limit 0.1). The complete distributions,
including soft tails outside oracle support, are retained and scored.

### Repairs, regressions and preservation

| Crossed to matched comparison | NAND | NOR | Total |
|---|---:|---:|---:|
| Identifiable repairs | 2,924 | 2,988 | **5,912** |
| Identifiable regressions | **0** | **0** | **0** |
| Primary composition repairs | 1,772 | 1,788 | **3,560** |
| Primary composition regressions | **0** | **0** | **0** |
| Ambiguous MAP repairs | 384 | 384 | **768** |
| Ambiguous MAP regressions | 336 | 384 | **720** |

These compare different law-trained checkpoints on this new bank; they are not
before/after updates to old V2 weights. Historical V2 files remain byte-identical.
The realized-unchanged metric retains **480 NAND / 528 NOR bit errors**, all at
ambiguous first forecasts. None is an error on a coordinate known to retain a
fixed value. Do not report the realized metric as zero.

Local probability scores also remain visible: matched NLL is slightly worse on
**1,826 NAND / 1,546 NOR** forecasts, with maximum increases **0.002889 / 0.002095
nats** respectively. It improves on 5,854 / 6,134 forecasts; the overall mean NLL
changes are **−3.270494 / −3.122122 nats**. Thus this result does not claim that
every individual probability score improves. Raw point records preserve all IDs.

### Verification, cost and code size

The [standalone byte/arithmetic audit](results/multisource-law-validation-v1.json)
reconstructs the decision from saved bytes without importing the model, learner,
collector or scoring functions. It verifies **41 source bindings, 15 checkpoint
tensor fingerprints, 46 unchanged historical V2 files, 25 result artifacts and
all 30,720 receipts**, with **zero discrepancies** across 4,384,792 checks.
Maximum probability-mass error is 6.67e-16. This is same-author internal review,
not independent scientific custody, and its check count is not learned evidence.

The prefit source passed **700 tests**, all **24 locks** and frozen preflight in
[CI](https://github.com/robosys-labs/cemm/actions/runs/41103517083); its
[source snapshot](https://github.com/robosys-labs/cemm/actions/runs/41103516949)
also passed. The checkpoint commit passed
[invariant CI](https://github.com/robosys-labs/cemm/actions/runs/41104430562).
Final result-head checks are linked in [PR #65](https://github.com/robosys-labs/cemm/pull/65/checks).

Ten fit regions used **92.190741 CPU / 92.206629 wall seconds**; twenty native
collection regions used **195.268915 CPU / 195.494048 wall seconds**. These
exclude artifact compression, scoring, audit and publication overhead. Peak
process RSS was **345,608 KiB** during fitting and **526,016 KiB** during
collection. Matched forecast CPU p50 ranges **1.462–1.884 ms**, p95
**2.466–5.454 ms** across law/seed runs. Runtime remained pinned to Python 3.13.16,
Torch 2.10.0+cpu, NumPy 2.3.5 and single-thread deterministic execution.

There are **zero neural inference/learning source changes and zero added parameters
per model**. Four study modules add 624 physical Python lines and the reused
analyzer grows by one net line; 19 focused tests add 364 lines. The active import
closure remains **2,732 lines**, or **2,917** including its historical source pin.
All retained research Python is **29,936 lines**, including **13,436 test lines**;
the inclusive 2,000-line objective remains unmet. This tranche does not justify
expanding the learned architecture.

## Next bounded G2 task: propagate a hidden learned consequence

Reuse these ten frozen checkpoints with **zero new fitting**. A fresh three-contact
cycle challenge should pair full feedback with one hidden intermediate participant
before the final contact, using both cycle orders `ab;bc;ca` and `ca;bc;ab`, all
anchors, modes, role reversals and entity counts 3–6. Define the nontrivial
propagation subset from the oracle before forecasting, and retain the all-action
and full-feedback denominators. One missing bit needs at most two physical paths
and 128 candidate expansions at six entities, within the existing API and bounds.

For example, under mode 0 and order `ab;bc;ca`, NAND from anchor `101` yields
`111 → 110 → 110`. If the second feedback hides c, carrying stale c=1 instead of
its learned consequence c=0 gives the wrong final a. NOR from `010` similarly
yields `000 → 001 → 001`; stale c=0 gives the wrong final a. This directly tests
state propagation that the current full-feedback experiment does not establish.
Related cycle geometry existed under old XOR; the new evidence concerns these
independently learned laws under withheld feedback. A paired challenge across two
orders, two feedback conditions, two laws and five seeds would retain **15,360
forecasts**, with no checkpoint tuning. It is selected, not yet frozen or run.

Simultaneous timing still needs an explicit observable time-group contract; the
serial Session cannot distinguish it. That is an input distinction to specify,
not a newly demonstrated neural capacity failure. Full G2 and independent
scientific admission remain open; the completed studies are not reopened.
