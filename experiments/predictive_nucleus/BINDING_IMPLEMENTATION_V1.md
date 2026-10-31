# G3 binding comparison: implementation, not a research result

Parent: [PR #69](https://github.com/robosys-labs/cemm/pull/69),
`2336a0bbaedca1840a2ab8e1616ebbdf3e26f82b`. Tracks [#22](https://github.com/robosys-labs/cemm/issues/22).
Updated 2026-10-31 (Africa/Lagos).
**IMPLEMENTED_NOT_SCIENTIFICALLY_EVALUATED. G3 remains open.**

## What changed

The selected comparison now has executable models and a shared outcome-only
training API. It is not yet a frozen study: there is no new research fit,
checkpoint selection, held-out score, or scientific admission decision.

| Arm | Actual trainable parameters | Hypothesis |
|---|---:|---|
| `gru` | 474 | Unchanged `OrderEncoder`, freshly initialized |
| `factor` | 89 | Learned lexical content and layout scalars with learned bilinear interaction |
| `additive` | 91 | Same two learned scalar encoders; additive readout removes their interaction |

`binding_model.py` pools the existing character features separately from the
three identity-position markers. An 8-wide lexical network produces one learned
scalar; a separate layout layer produces another. The bilinear readout learns
both output weights and biases. No scalar sign is assigned a semantic meaning.
There is no word lookup, role label, language ID, literal-word dispatch or fixed
inverse/XOR operation. The additive control receives the same evidence.

This **rank-one factorization is supplied architectural bias**. It is selected
for the existing binary participant-order interface, not inferred as a universal
structure of language. Exact roster grounding, token/event boundaries, two
candidate contacts and the acquired world/mode mixture remain supplied. The
89-parameter hypothesis may fail; the previous GRU failure does not establish
that GRUs lack the capacity to solve the task.

## Shared training API

`binding_training.fit_comparison(inputs, world, seed=..., updates=...)` reuses
`bilingual_run.pack`, `bilingual_run.forecasts` and the existing complete-world
outcome NLL. All three arms start fresh, see the identical validated history,
batching and event-weighted loss, and use the same prescribed update budget.
No old weights, teacher predictions, gold participant orders or challenge labels
enter this API. The supplied world must already be frozen and in evaluation
mode, including every child module; validation does not change its flags.

The return value contains in-memory models, parameter counts, initial/final
fingerprints, common training-input digest, actual update/event counts, loss
curves and per-arm CPU/wall cost. Native-cache preparation is recorded separately.
Per-arm timing covers the update loop, not process startup, model/optimizer
construction or persistence. Equal histories and updates do not imply equal
capacity, initialization tensors or consumed compute.

Nonfinite losses/updates, invalid budgets, gold-bearing envelopes and CPU-budget
failures are rejected. An interruption produces no completed-comparison result.
This API is not a crash-durable experiment journal, checkpoint format, optimizer
resume mechanism or sandbox. The caller owns prospective publication and output
persistence. No generic experiment framework or runtime cutover was added.

## Verification and historical preservation

Twenty-one focused synthetic tests cover feature separation, renaming, masking,
parameter counts, deterministic initialization, readout arithmetic, state-dict
round trips, outcome gradients, event weighting, identical exposure, input/world
non-mutation, label rejection and failure paths. Synthetic optimizer steps are
wiring tests, not scientific fitting or structural-transfer evidence.

Run the implementation tests and full invariant suite with:

```sh
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0 \
  python -m unittest experiments.predictive_nucleus.tests.test_binding -v
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONHASHSEED=0 \
  python -m unittest discover -s experiments/predictive_nucleus/tests -v
```

The implementation adds **145 source +245 test =390 Python lines**. Retained
research Python totals **36,903 lines**; the inclusive 2,000-line target remains
unmet. Existing model sources, checkpoints, data, protocols and decisions are
unchanged. The active handoff is condensed below; its full prior API/history
reference remains immutable at the parent commit.

## Next bounded scientific step

Freeze one genuinely fresh word-by-layout challenge and its observed training
history before fitting. A new seed or name permutation of the already opened
failure bank is not independent structural evidence. Preserve the old lexical
and bilingual checkpoints/forecasts as explicitly opened retention references;
do not train on their challenge outcomes.

Compare these three arms across the original five seeds, fitting only through
NAND outcomes and transferring unchanged to NOR. Predeclare budgets, source/data
hashes, coverage, per-word/layout/family criteria, lexical-pair conjunctions,
mask/swap controls, probability losses and exact repairs/regressions. Publish
actual new checkpoints before collection. Retain every failure without tuning
on the opened challenge. Reuse existing collection/scoring machinery where it
fits, rather than creating another framework. No new scientific cycle has run
in this implementation tranche; G4/G5 do not substitute for structural reuse.
