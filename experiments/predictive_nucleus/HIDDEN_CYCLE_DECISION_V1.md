# G2 hidden intermediate cycle — frozen-weight propagation

Tracking: [#22](https://github.com/robosys-labs/cemm/issues/22). Prepared 2026-10-30;
reviewed and frozen for execution 2026-10-31 (Africa/Lagos).

## Result: KEEP_HIDDEN_CYCLE

[PR #66](https://github.com/robosys-labs/cemm/pull/66) completes the selected
tranche. Public source/data/plan freeze:
`16a2326491b1add7e3057304d88e430724964584`. Its exact source tree was tested
before publication, then fetched and verified before the single collection.

All **15,360 planned forecasts** were produced and answered, with no missing
records, failed episodes or abstentions. Both learned laws pass every frozen
criterion at all five seeds. The [decision](results/hidden-cycle-v1/decision.json),
[headline metrics](results/hidden-cycle-v1/headline.json),
[complete trace manifest](results/hidden-cycle-v1/manifest.json) and
[internal arithmetic audit](results/hidden-cycle-validation-v1.json) retain the evidence.

| Measured outcome | NAND, five seeds | NOR, five seeds |
|---|---:|---:|
| Identifiable complete worlds | **5,120 / 5,120** | **5,120 / 5,120** |
| Identifiable reversed-role conjunctions | **1,280 / 1,280** | **1,280 / 1,280** |
| Hidden-intermediate final worlds | **1,280 / 1,280** | **1,280 / 1,280** |
| Critical hidden finals | **240 / 240** | **240 / 240** |
| Full-to-hidden MAP regressions / repairs | **0 / 0** | **0 / 0** |
| Minimum critical true-world probability | **0.990451** | **0.992616** |
| Maximum critical stale-target probability | **0.004360** | **0.001883** |
| Worst family/condition/stratum mean oracle KL | **0.005813 nats** | **0.004827 nats** |
| Maximum ambiguous total variation | **0.006519** | **0.007076** |

The 2,560 hidden final predictions remain correct despite unavailable intermediate
readings, including all 480 cases where a stale intermediate value would change
the downstream target. Full/hidden forecasts before the differing feedback are
identical. All-action accuracy is **83.3333%**, exactly this bank's expected
oracle MAP rate; every MAP error is in an ambiguous first forecast.

### Adverse differences remain visible

Withholding feedback slightly reduces probability quality even though it changes
no identifiable MAP answer. Each law has **1,256 final NLL increases and 24
decreases** across 1,280 twins. Mean hidden-minus-full NLL is **+0.000518286 nats
for NAND** and **+0.000304000 for NOR**; maximum increases are **0.002847856**
and **0.001247363 nats**, respectively. The largest true-world probability drop
is 0.002833. These are information-condition comparisons with unchanged weights,
not historical parameter regressions. All exact distributions and per-twin
differences remain in the summary and all-action reports.

There are zero unsupported MAP worlds and zero errors on coordinates known to
remain fixed. Realized unchanged-coordinate errors are **640 NAND / 704 NOR**,
all from ambiguous first forecasts. The narrower known-fixed-value result must
not be substituted for this retained error count.

### Validation and resource use

The source passes **722 isolated tests** locally in **58.425 seconds**, all
**25 protocol/manifest locks** and the frozen preflight. Both public-freeze
[invariant CI](https://github.com/robosys-labs/cemm/actions/runs/41195738585) and
[source snapshot CI](https://github.com/robosys-labs/cemm/actions/runs/41195738479)
passed. Final result-commit checks are linked on PR #66.

The separate stdlib-only audit recomputes all 15,360 forecast vectors/receipts,
3,072 oracle distributions, the decision and local differences, checks 50 source
bindings and ten tensor fingerprints, and verifies 349 historical data/result/lock
files are byte-identical. It finds **zero discrepancies** without executing the
model, collector or scorer. Its temporary 292-line analysis script is identified
by SHA-256 in the report; this is internal arithmetic review, not independent
scientific custody.

Collection regions total **62.512 CPU / 62.558 wall seconds**, excluding
compression, scoring and publication. Process high-water RSS is **519,152 KiB**.
Per-seed all-action forecast p95 wall latency ranges from **1.412 to 1.922 ms**.
The 545 study-code lines and 471 focused-test lines add no inference imports or
learned parameters. Active imports remain **2,732 physical lines** (2,917 with
the historical source pin); retained research Python is **30,952 lines**, including
13,907 test lines. The inclusive 2,000-line objective remains unmet.

All six preceding STOP/REVISE/KEEP decisions, original gates, checkpoints and
inference implementations remain unchanged. This completes the selected hidden
intermediate task; full G2 and independent scientific admission remain open.


## Hypothesis and scope

The ten retained NAND/NOR checkpoints can carry a learned consequence through
one missing intermediate reading and use it in the next contact. Compare each
hidden-feedback episode with a full-feedback twin using the identical checkpoint,
actions, initial state and actual outcomes. Only one reading differs.

The nucleus stays at **562 parameters**, with **zero new fitting**, unchanged
learning/inference/checkpoint code and the existing observation API. Checkpoints
are pinned to `25ae19b317c5b7dbfc487fa5204fb5da5f0e7420`; the implementation base
is `66f0e28f34fdd1767e271c813988a3494023e6ae`. Historical studies are not rerun.

This is an ordered three-contact cycle, with one hidden consequence after contact
two and one subsequent forecast. It does not establish fully open-loop rollout,
simultaneous timing, a unified checkpoint for both laws, architecture superiority,
general calibration, or independent scientific custody. G1 development readiness
remains `PROCEED_TO_G2`; original scientific admission remains `NOT_ADMITTED`.

## Frozen design and denominators

The [protocol](hidden_cycle_protocol_v1.json), its checksum, generated
[assets/plans](data/hidden-cycle-v1/), and the complete source inventory are
committed and published before collection. The runner verifies committed bytes,
all 50 source bindings, all five prepared artifacts, and original historical
checkpoint bytes. It records all observed-only traces before loading targets.

| Quantity | Per law and checkpoint seed | Across both laws and five seeds |
|---|---:|---:|
| Episode views | 512 | 5,120 |
| All-action forecasts | 1,536 | 15,360 |
| Identifiable forecasts | 1,024 | 10,240 |
| Ambiguous first forecasts | 512 | 5,120 |
| Final full/hidden twin pairs | 256 | 2,560 |
| Critical hidden finals | 48 | 480 |

The design covers three through six entities, all eight core binary anchors,
both persistent modes, both global role assignments and two cycle orders. Law,
mode, role, feedback and seed views are dependent. The orders are isomorphic
under identity/global reversal. Each law has 64 physical lineages, 92 canonical
blueprints and four canonical topology/mask templates; these are not thousands
of independent physical trials.

Mask selection depends only on the shared entity in the second and third
contacts. The evaluator marks a final forecast critical only when resetting
that hidden entity to its last delivered value changes the final physical target.
There are 112 changed hidden intermediates per law but only 48 critical ones.
All remaining cases remain in the denominators.

The first complete feedback identifies the fixed mode. All later outcomes are
identifiable from available evidence even when the intermediate bit is hidden.
First forecasts have two equiprobable possible worlds, so the expected optimal
pooled MAP accuracy is **83.3333%**. This is not comparable to pooled percentages
from banks with different ambiguity mixtures.

Historical overlap is retained in the asset audit. There is zero complete
blueprint/template overlap with actual NAND/NOR training or its earlier
evaluation bank. One canonical blueprint and some templates overlap older XOR
evaluation banks. Constituents and cycle geometry are familiar; the new test is
propagation under learned NAND/NOR laws when intermediate feedback is withheld.

## Prospective decision criteria

Every law/seed/order/feedback cell must retain complete support, at least 95%
identifiable complete-world and role-pair accuracy, zero unsupported MAP worlds,
zero errors on values known to stay fixed, mean oracle KL at most 0.05 nats per
information stratum, and ambiguous maximum total variation at most 0.1.
Singleton oracle support plus zero unsupported MAP makes effective identifiable
exactness **100%**.

Each critical hidden final must assign at least 0.9 probability to the exact
true world and at most 0.1 to the stale-target event, summing the complete
distribution. Full/hidden predictions before the differing feedback must agree
within the frozen tolerance. No identifiable full-to-hidden regressions are
allowed. Every local probability/NLL change, including adverse changes, remains
visible; probabilities are never renormalized onto oracle support.

Missing outputs, failures and invalid artifacts yield `STOP_INCOMPLETE_EXECUTION`.
Complete execution with any failed criterion yields `REVISE_HIDDEN_CYCLE`.
Otherwise the bounded decision is `KEEP_HIDDEN_CYCLE`. No tuning or retry on
this bank is permitted.

## Implementation and verification

The recovered implementation consists of a 144-line data adapter, 194-line
scorer and 207-line freeze/collection adapter. It reuses the native acceptance
collector, checkpoint loader, independent truth-table oracle and joint scoring.
The 471 lines of focused invariant tests cover future-feedback leakage, missing
forecasts, exact-zero probabilities, complete-world preservation, checkpoint
provenance, collection order and retained failure prefixes. Runtime code and
historical evidence remain unchanged.

An independent internal stdlib review recomputed all 512 trajectories and 1,536
oracle distributions per law, all critical-case membership, and every prepared
source/artifact digest, with zero discrepancies. This is implementation review,
not independent challenge authorship or scientific custody.

## Execution

Run from a clean checkout of the public freeze, using Python 3.13.16,
Torch 2.10.0+cpu and NumPy 2.3.5:

```sh
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0 \
  python -m experiments.predictive_nucleus.hidden_cycle_run collect \
  --data experiments/predictive_nucleus/data/hidden-cycle-v1 \
  --output /absolute/path/to/new-hidden-cycle-output
```

The output path must not exist. Collection is one attempt; keep any failure
record and partial traces. The public source/data/plan freeze must precede the
command. The runner enforces committed local bytes; remote publication is
verified separately. No scientific result was claimed by the freeze commit.

## Next G2 task: make interaction timing observable

Implement one bounded compound-contact input with explicit ordered versus
common-snapshot timing, then freeze and execute a fresh timing-twin challenge.
This addresses the roadmap's remaining simultaneous/ordered requirement. A
new time-group field is necessary: the current serial action contract cannot
express simultaneous effects, and missing feedback does not supply that meaning.

Reuse the learned pair distributions conditional on the **same persistent mode**.
For common-snapshot groups, each contact predicts its own event-local outputs
from one base world. Combine proposed changes afterward; do not multiply both
pair factors against a shared final variable, which would incorrectly require a
participant to change and persist simultaneously. In the first binary-domain
contract, combine the union of event-local changes relative to the base state.
This is explicitly **supplied scheduling semantics**, not learned physics or
inferred write roles. Preserve the existing learned background distribution once
for uninvolved entities. No law-specific branch, gold source orientation or new
neural parameter is selected. Simultaneous combination cannot be inferred from
isolated outcomes without either a declared scheduler or new simultaneous data.

The selected bank should use an ordinary acquisition contact, one two-contact
group and zero to two ordinary suffix contacts: three to five total contacts.
Pair timing twins with identical pre-group history and atomic contact lists,
with no intermediate readings inside either group. Include overlapping chains
and cycles where timing matters, disjoint controls, reversals, applicable 3–6
entity cases, both learned laws and five frozen seeds. Predeclare the critical
timing subset and retain every action/condition in scoring. Check exact
single-contact compatibility, group-order invariance for common snapshots,
shared-mode dependence and forecast non-mutation before the prospective run.

This task is selected, not implemented, frozen or evaluated by this tranche.
Fully unobserved long rollouts remain a separate scaling question, not a newly
invented G2 prerequisite: positive soft tails exceed the current exact-history
path/expansion budgets as missing horizons grow. That is a resource limit, not
evidence that the learned pair dynamics cannot represent composition.
