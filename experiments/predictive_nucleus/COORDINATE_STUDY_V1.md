# Equivalent-function layout-coordinate comparison

Tracks [#22](https://github.com/robosys-labs/cemm/issues/22); continues
[PR #75](https://github.com/robosys-labs/cemm/pull/75) at
`6efdc97164dafb45b82718688bf8dbb275987518`. Registered 2026-11-01.
This prospective protocol does not claim a successful result.

## Hypothesis

The completed centering study passed for four of five seeds, but seed 11 retained
same-sign layout responses, poor training fit and exact regressions. The existing
88-parameter `binding_layout_coordinates.py` removes the redundant fourth affine
layout scalar. On the three legal identity masks it preserves the centered
89-parameter model's initial function and full response class. The other 85
initial scalars are identical. No word meaning, participant order, response sign
or permanent zero mean is imposed.

For the old affine map, the response Jacobian satisfies
`J J^T = I + 2 11^T`; direct response coordinates remove this coupling under
ordinary gradient descent. This motivates a parameterization test. It is not
an Adam convergence proof. Identical Adam and parameter-space clipping settings
intentionally produce different effective optimization geometry.

## Fixed comparison

- Arms: `centered` (89 parameters) and `coordinates` (88 parameters).
- All five seeds: **7, 11, 23, 37, 53**.
- The exact prior **1,152-event observed NAND tape**, in the same order.
- **256 updates**, Adam learning rate **0.02**, gradient clip **5.0**,
  **120 CPU seconds per arm**, no early stopping or retries.
- Python **3.13.5**, PyTorch **2.10.0+cpu**, NumPy **2.3.5**, float64,
  deterministic algorithms and one thread.
- The original acquired **562-parameter** NAND/NOR worlds stay frozen.
  Language weights fitted on NAND transfer unchanged to NOR.

Save actual initial states, shared-tensor fingerprints and the three layout
responses. Check initial output equivalence on every training token feature.
All centered control initial/final fingerprints must match the original
centering study. A mismatch invalidates execution; the repeated controls are
reproduction checks, not independent training evidence. No gold roles or
participant-order labels enter fitting.

## Fresh structures and retention

Fresh ordered graphs are `fanout_cross4` and `chain_shortcut5`, with four/five
active participants and four/five interactions. The novelty guard rejects every
opened bilingual, binding, saturation **and centering** event structure under
active-entity renaming and edge-direction reversal, preserving event order.
There are **384 episodes and 1,728 canonical forecasts per law**. All prescribed
anchors, role reversals, lexical pairs and layouts are retained without filtering
by outcome. Words/layouts and the eight training-withheld cells have been opened
before; only the event structures are fresh.

Five opened banks remain explicit retention: bilingual-v1, lexical-v1,
binding-v1, saturation-v1 and centering-v1. Archived references retain their
original lexical, binding-factor, saturation-unsaturated and centering-centered
forecasts. Also compare every candidate prediction against its current paired
centered control. Final-word masks and swaps use the identical canonical prefix;
native-action references remain evaluator-only. Forecasts use observed-prefix
feedback at each step; this is not an autonomous open-loop trajectory rollout.

Expected collection: **278,400** canonical/probe/retention rows and **17,280**
separate native references. These pool dependent laws, seeds and lexical/role
views, not independent experimental samples.

## Decision

Preserve all existing per-cell accuracy, order, NLL, critical probability,
lexical/role-pair, lexical-gap, masking and swap gates at **every seed/law**.
Training mean NLL must be at most **0.05**. Native, archived and paired exact
regressions must be zero, and fresh mean NLL must not increase against the paired
centered arm. Report every adverse per-point probability change; its presence is
not a new post-hoc veto.

Return `KEEP_LAYOUT_COORDINATES` only if all gates pass; otherwise
`REVISE_COORDINATE_HYPOTHESIS`. A pass settles only this bounded fitting/transfer
comparison. It does not complete G3's remaining reusable-meaning requirements,
resolve independent scientific admission or advance G4.

## Execution and evidence

Publish source/protocol/data commitments before fitting, then all ten actual
checkpoints before collection. Use the existing loss, inference, probes and
metric primitives without altering historical sources. Each stage writes an
exclusive new directory and preserves failures. Synthetic invariant tests use
toy observations/worlds; they do not fit or evaluate research checkpoints.

Run `python -m experiments.predictive_nucleus.coordinate_run` with `prepare`,
`fit`, `collect`, then `score`. Paths are `data/coordinate-v1`,
`data/coordinate-fit-v1`, `results/coordinate-v1/traces` and
`results/coordinate-v1/scoring`. Fit receives the verified source publication SHA
via `--publication`; collection receives the actual weights publication SHA.
These strings are offline attestations, verified separately on GitHub.

The separate saved-record auditor imports no numerical runtime, fitter, model,
collector or original scorer. It verifies record arithmetic and provenance,
not independent custody. Keep G1/G2 development progress, formal admission limits,
all previous failures and production authority unchanged. Equal exposure/update
budgets are not matched consumed compute; compact parameter count does not meet
the outstanding inclusive 2,000-line research-code goal.
