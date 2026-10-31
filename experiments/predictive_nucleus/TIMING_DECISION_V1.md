# Explicit timing v1 — KEEP_TIMING

**Stage: COMPLETE; decision KEEP_TIMING under both laws at all five seeds.**
2026-10-31, Africa/Lagos. [PR #67](https://github.com/robosys-labs/cemm/pull/67).
The [locked protocol](timing_protocol_v1.json) owns the decision criteria.
This tranche follows [hidden cycle v1](HIDDEN_CYCLE_DECISION_V1.md) and reuses
the ten checkpoints frozen at `25ae19b317c5b7dbfc487fa5204fb5da5f0e7420`.
Formal G1 scientific admission remains **NOT_ADMITTED**.

Public source/data/plan freeze: `86936788d6f90ccb99f719d48e2c9a3b13e03756`;
tree `0b899e390bb7e09c7b332f77f923532b490be1cb`. The tested and published trees
are byte-identical. The single collection starts from that public commit.

## Result

All **46,080 forecasts** were produced and answered, with zero failures,
abstentions or missing records. The unchanged learned checkpoints distinguish
ordered and common-snapshot outcomes on the predeclared timing-sensitive cases,
and common snapshots preserve their full distribution under event-list reversal.

| Metric over five seeds | NAND | NOR |
|---|---:|---:|
| Forecasts answered | 23,040 / 23,040 | 23,040 / 23,040 |
| Identifiable complete worlds correct | 14,400 / 14,400 | 14,400 / 14,400 |
| Identifiable reversed-role conjunctions | 4,320 / 4,320 | 4,320 / 4,320 |
| Critical timing pairs passing | 600 / 600 | 600 / 600 |
| Common-snapshot permutation forecast pairs equal | 7,680 / 7,680 | 7,680 / 7,680 |
| Nontrivial-permutation forecast pairs equal | 6,400 / 6,400 | 6,400 / 6,400 |
| Minimum critical true-world probability | 0.983679 | 0.985114 |
| Maximum opposite-timing world probability | 0.003864 | 0.002224 |
| Minimum critical timing separation | 0.981534 | 0.984240 |
| Worst family/condition/stratum mean KL, nats | 0.011444 | 0.010159 |
| Maximum ambiguous TV | 0.006543 | 0.007321 |
| Known-fixed-value / unsupported MAP errors | 0 / 0 | 0 / 0 |

Pooled exact-world accuracy is **81.25%**, equal to the expected oracle MAP
rate: **37,440/46,080**, including **8,640/17,280** ambiguous acquisition points.
All errors occur before the first mode-identifying feedback. Realized
unchanged-coordinate errors remain **2,160 NAND / 2,376 NOR**; these differ from
known-fixed-value errors, which are zero. The maximum full-vector permutation
log difference is **7.11e-15**, below the frozen `1e-12` tolerance. Acquisition
distributions match across all 5,760 timing pairs.

The [decision](results/timing-v1/decision.json), [headline](results/timing-v1/headline.json),
[summary](results/timing-v1/summary.json.xz) and [raw artifact manifest](results/timing-v1/manifest.json)
retain all seeds, families, conditions and planned points.

### Probability differences retained

Common-snapshot group NLL increases on **32 NAND / 5 NOR** pairs and decreases
on **2,848 / 2,875**. The largest increase is **0.000755095 nats**. Mean group
differences are **−0.003685156 / −0.003907661 nats**. All 1,920 disjoint group
comparisons have the same oracle world and correct predictions, but their soft
distributions differ: maximum TV is **0.007759 NAND / 0.009094 NOR**. Ordered
composition applies background twice, so these NLL differences do not establish
an advantage of simultaneous physics or a superior architecture.

Each law retains **1,920 suffix comparisons**, with equal oracle worlds on
**1,440**. Common-time suffix NLL increases on **340 NAND / 328 NOR**, decreases
on **1,556 / 1,590**, and is exactly equal on **24 / 2**. Mean increases are
**0.000068824 / 0.000026034 nats**; maxima are **0.002493135 / 0.001761969**.
Both conditions remain correct at every identifiable group and suffix. No
historical-weight regression is implied by these timing-conditioned differences.

## Implemented capability

The separate `timing_session.Session` accepts ordinary contacts and an explicit
two-contact group. `ordered` marginalizes two native transitions with no
intermediate feedback. `common_snapshot` makes both learned pair factors read
the same base world, conditional on the same persistent mode, then merges their
event-local changes using the supplied binary delta-union rule:

`y_i = x_i XOR OR_e(z_e,i XOR x_i)`.

The merger is supplied computation. Isolated contact data do not identify an
arbitrary simultaneous interaction law. The experiment tests reuse of learned
pair likelihoods under the declared timing contract. It adds no neural tensors,
training updates, law-specific inference branches, source/target labels or
gold write masks. Native model, inference, checkpoint and partial-feedback
implementations retain their original bytes and source pins.

The opt-in interface is restricted to full endpoint observations, 3–6 binary
entities, registered persistent-mode `DomainKernel` checkpoints and distinct
handles within each contact. It has at most 64 hypothetical intermediate worlds
and 4,096 ordered world pairs, or 16 common event-output combinations. It
preserves all four learned pair outcomes, including tiny source-change tails,
exact zero support and finite log probabilities that underflow on exponentiation.

Only actual endpoint feedback updates the committed world and mode posterior.
Every forecast binds timing, contacts, sensor coverage, checkpoint fingerprint
and the separately hashed scheduler into its receipt before feedback.

## Frozen design

Each episode has one fully observed acquisition contact, one grouped event,
then zero to two ordinary suffix contacts. Both timings have one group forecast
and one endpoint feedback: ordered timing receives no extra observation.

| Family | Group | Suffix | Atomic contacts |
|---|---|---|---:|
| Chain | `ab;bc` | `ca` | 4 |
| Repeated | `ab;ab` | None | 3 |
| Fan-in | `ac;bc` | `ab;ca` | 5 |
| Disjoint | `ab;cd` | None | 3 |

The third condition reverses the common-snapshot event list. It preserves each
contact's internal participant order. All eight three-vertex core anchors and
all sixteen four-vertex disjoint anchors are included, with both persistent
modes and global role reversals. Applicable entity counts are 3–6, with 4–6 for
disjoint groups. Spectators use one deterministic pattern per core/size/family;
this is not exhaustive coverage of all full-world anchors. The data audit
records actual group-entry core-state coverage after acquisition.

Per law/seed: **1,728 episodes, 4,608 forecasts, 6,336 atomic contacts**;
2,880 forecasts are identifiable and 1,728 acquisition forecasts ambiguous.
There are 864 role pairs, 576 timing pairs and 576 event-permutation pairs;
448 permutations change the list and 128 repeated-contact controls are trivial.
Across ten checkpoints the planned denominator is **46,080 forecasts**.

An independently coded truth-table oracle identifies **120 timing-sensitive
pairs per law** before collection: 16 chain, 64 repeated, 40 fan-in, zero disjoint.
All remaining views are retained. The expected pooled oracle MAP accuracy is
**81.25%**, because the first contact precedes mode-identifying feedback.
Episode, mode, timing, identity and seed views are dependent records.

## Decision and controls

Every seed/law/family/condition must preserve complete support, identifiable
complete-world accuracy and role conjunctions, full-joint probability quality,
known-fixed values and oracle-supported MAP predictions. Every critical pair
must give its own required world at least 0.9 and the opposite timing's world
at most 0.1, with at least 0.8 probability separation between timing inputs.
Every common-snapshot permutation must preserve the entire vector at every
forecast within `1e-12`. Missing forecasts or incomplete feedback retain their
planned denominators and cause `STOP_INCOMPLETE_EXECUTION`.

Native ordered composition applies learned background twice, including to a
future or former participant. Common snapshots apply it once outside the union
of participants. Disjoint oracle outcomes therefore agree, but their learned
soft distributions can differ. Their TV and NLL differences are descriptive;
lower common-time NLL does not establish superior dynamics. Suffix contacts may
legitimately erase a timing difference; convergence and all local NLL changes
are recorded rather than treated as failures.

The public source, protocol, bank and checkpoint-plan freeze preceded one
collection. All ten observed-only traces were saved before evaluator targets were
parsed. There was no fitting, tuning, retry or historical-study replay.

## Validation, resources and size

Synthetic tests independently enumerate both schedulers, verify exact native
single-contact compatibility, shared-mode dependence, event and identity
permutations, negative-infinity versus finite tails, receipts, endpoint-only
belief updates, rejection of invalid raw mass, and failure/omission accounting.
Fresh untrained synthetic checkpoints are separate from the ten study weights.
The clean-checkout suite passes **760 tests in 64.590 seconds**, all **26 protocol
locks**, and frozen preflight. The first uncommitted-tree pass had only the
expected clean-checkout preflight error; the subsequent committed pass is fully
green. Public-freeze [invariant CI](https://github.com/robosys-labs/cemm/actions/runs/41198968742)
and [source snapshot CI](https://github.com/robosys-labs/cemm/actions/runs/41198968713)
also pass. Result-head checks are linked in [PR #67](https://github.com/robosys-labs/cemm/pull/67/checks).

The separate [internal arithmetic audit](results/timing-validation-v1.json)
finds zero discrepancies in **1,118,458 checks** without importing any model,
collector or scorer.
It independently reconstructs 9,216 oracle distributions, checks all 46,080
forecast vectors and receipts, 61 source bindings, ten tensor fingerprints and
**374 unchanged historical data/result/lock files**. It reproduces the decision.
This is internal implementation review, not independent scientific custody.

Collection regions use **133.412 CPU / 133.447 wall seconds**, with maximum
recorded process RSS **525,232 KiB** (approximately 512.9 MiB). Per-seed forecast
p95 ranges **2.005–2.309 ms**. These measurements exclude trace compression,
scoring, report serialization and publication. The runtime is Python 3.13.16,
PyTorch 2.10.0+cpu, NumPy 2.3.5, one thread, float64 and deterministic operations.
Each checkpoint remains **562 parameters**, with zero new parameters or updates.

The new runtime/contract/session totals **273 physical Python lines**. The full
tranche adds **1,121 source lines and 975 test lines** (38 tests). The timing
entrypoint's static import closure is **2,457 lines**, or **2,642** including the
historical source-only pin. All retained research Python is **33,048 lines**,
including **14,882 test lines**; the inclusive **2,000-line objective is unmet**.
The separate temporary stdlib arithmetic-review script is 318 lines and is
identified by its digest in the audit report; it is excluded from those retained
repository counts and is not a learned component.

## Development decision and next work

**G2 development readiness: PROCEED_TO_G3.** This completes the last selected
explicit G2 capability gap, alongside ordered composition, self-reference,
correlated alternatives, separately acquired NAND/NOR laws and bounded hidden
propagation. It does not turn historical G1/G2 scientific admission into a pass.
Strong architecture comparisons at matched consumed compute, independent
challenge custody and broader calibration remain scientific limitations.

The next bounded implementation is bilingual grounding into the **same frozen
learned world model**: English-like SVO and a genuinely different artificial OSV
order, held-out entities/role reversals/combinations, and the declared text-only
and supervised-parser controls. No gold parser programs or linguistic role labels
enter the candidate. Freeze a fresh language challenge before fitting its encoder,
then execute one fit/evaluate/decision cycle. Preserve all prior world weights,
successful experiments and failed-study history. No extra fully hidden rollout,
unified-law checkpoint or larger neural workspace is added as a prerequisite.
