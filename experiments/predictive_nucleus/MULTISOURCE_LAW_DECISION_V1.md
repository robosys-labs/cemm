# Multisource law v1: prospective unchanged-model test

Tracking: [#22](https://github.com/robosys-labs/cemm/issues/22). Recorded 2026-10-30.
**Status: ten prescribed fits complete; checkpoint commitment precedes collection. No scored result yet.**
G1 development remains PROCEED_TO_G2; formal scientific admission remains
NOT_ADMITTED. All earlier STOP, REVISE and KEEP decisions are preserved.

## Why this is the next measurement

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
These are exposure and provenance records, not measured competence.
