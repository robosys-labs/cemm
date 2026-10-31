# G2 hidden intermediate cycle — frozen-weight propagation

Tracking: [#22](https://github.com/robosys-labs/cemm/issues/22). Prepared 2026-10-30;
reviewed and frozen for execution 2026-10-31 (Africa/Lagos).

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
verified separately. No scientific result has been claimed at this freeze.
