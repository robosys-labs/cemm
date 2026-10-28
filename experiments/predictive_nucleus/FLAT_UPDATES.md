# G1h: equal-update flat ablation

> **Audit hold:** Sensor-error metadata is untrained, training and stress
> sensor geometry differ, and historical joint log loss is clipped. See [the
> integrity audit](2026-10-28-AUDIT.md).

The wall-budgeted v7 flat reference obtained only 19–24 optimizer updates
while the structured model received 200. That is a fairer wall-clock control
than giving both 200 steps, but it does not reveal whether the flat model is
primarily limited by its optimizer schedule. This predeclared development
ablation compares both budgets explicitly.

For each model seed, train the structured kernel for 200 updates. Train two
flat GRUs from the **same seed and the same sensor-visible episodes**: one
with the measured structured fit wall time as its cap, and one with exactly
200 updates. Select their temperatures separately on the same disjoint
sensor-only calibration episodes. The equal-update control is intentionally
allowed to exceed the wall cap; report its actual fit-time ratio. Equal
optimizer updates do **not** imply equal FLOPs or equal work.

The evaluator replays the same structured-selected probe actions and actual
sensor readings for both flat models. It hashes the initial observation,
public action/observation sequence, target actions and supplied sensor
calibration for each world, and rejects a comparison if the hashes differ.
Report MAP exactness, NLL, calibration, coverage, errors, pair accuracy,
paired case-level repairs and regressions, timing, parameter count, step count,
and physical probe count. The structured model, its episode guard and context
guard are retained as references.

V7 results were opened before this hypothesis. The v8 manifest and lock add
new public seeds, while also retaining v7 as an open regression split. Both
use the same developer-authored physics; model seeds share world lineages.
Neither split is a custodied blind challenge. Different objectives, explicit
structured likelihoods, the structured analytic belief and structured probe
selection remain relevant confounders. Neither a faster fit nor more updates
establishes a general architecture advantage.

```sh
python -m unittest discover -s experiments/predictive_nucleus/tests -v
python -m experiments.predictive_nucleus.flat_updates_trial \
  --train 600 --calibration 200 --worlds 10 --steps 200 --seeds 7,11,23,37,53
```

**G1 remains unadmitted.** Independent challenge custody, validated sensor
calibration, stronger compute accounting and independent replication remain
necessary before later language stages or production integration.
