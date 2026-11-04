# G5 v7 sealed-score presentation erratum — 2026-11-04

**Original raw challenge remains unchanged:** commit
[79a62ce](https://github.com/robosys-labs/cemm/commit/79a62ce8dc25b5421672a0a0b77d8f1f27866dd3)
contains all ten forecast-only banks, collected before truth scoring.
The evaluator source was preregistered before that seal. TRAIN
triple, matched neutral control, and smoothed rule were frozen in
[9dcb3e0](https://github.com/robosys-labs/cemm/commit/9dcb3e0be3b9090d0a7f57b60cc470744ad6c2c7).

The first post-seal evaluator workflow
[41889655202](https://github.com/robosys-labs/cemm/actions/runs/41889655202)
successfully emitted **all ten** condition-level \`G5_V7_SCORED\` reports
but failed on \`ZeroDivisionError\` while *serializing the aggregate summary*.
\`first_stable_b\` preallocated counters for seven arms, whereas only the
three temporal arms were populated for that displayed diagnostic.
The final output comprehension attempted to divide by zero for unused
control counters. The prespecified gate calculations directly access only
the three populated temporal arms and had already completed.

**Minimal reporting-only repair:** filter the display comprehension to
arms with nonzero \`n\`. No score, numerator, denominator, selection,
gate, fitted value, truth join, physical generator, raw forecast or
question rule changes. All ten original per-condition reports remain
in the failed workflow log. Rescore the **same** sealed raw commit
with the original evaluator math. Do not treat the failure as a new
challenge or opportunity to tune the model. No G5 scientific admission.
