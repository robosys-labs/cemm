# Full-sensor paired development study: incomplete v2 run

**Decision: INCOMPLETE; G1 HOLD / REVISE.** The first run of the locked v2
public development protocol stopped during evaluation in
[CI run 40707878378](https://github.com/robosys-labs/cemm/actions/runs/40707878378).
It did not produce a complete result or a G1 gate score.

All 40 planned neural checkpoint files were present. Their file SHA-256
hashes were independently checked against the runner's verified-checkpoint
progress entries. A separate restricted checkpoint parser also reproduced all
40 recorded tensor fingerprints without executing the models. This does not
verify training correctness or cross-host numerical reproduction. Six case records, for
cases 0–5, were completed; case 6 began but was not written. The runner had
already read case 6 evaluator truth before attempting its scores. Neither
`report.json` nor the `COMPLETE` marker exists. The explicit failure report
records `ValueError: invalid represented world` in the evaluation phase.

The exact incomplete artifact, including checkpoints, progress and the six
partial case records, is retained at [cemm-failed-study.zip](https://chatgpt.com/library?file_id=libfile_5248f15801648191b1472ff0596aaa5e&account_id=personal).
Its ZIP SHA-256 is
`e8a891e113de13fcc6dce00bbf2b39a08a20f20a80881d1fba351d4c976d7bc7`.
These partial case records must not be reported as the study's primary
contrast or interpreted as a complete set of outcomes.

The failure report does not identify the offending model, ID permutation,
step or probability. A represented probability slightly above one due to
floating-point aggregation is a plausible hypothesis, not an established
cause. A separate post-hoc diagnostic may load the retained, verified
checkpoints and inspect case 6 forecasts without reading evaluator truth or
scoring; it must record its environment and whether the failure reproduces.
Any correction must preserve this opened failure and be explicitly documented
as a revision. Do not silently rerun v2 or call the opened public cases a fresh
held-out challenge.

## Post-hoc inspection of saved forecasts

[CI run 40709831687](https://github.com/robosys-labs/cemm/actions/runs/40709831687)
loaded the 40 byte- and tensor-verified checkpoints, reconstructed and verified
the six empirical control tables, and inspected 3,600 raw forecasts for case 6
without calling `gold_after` or computing scores. One flat forecast for the
augmented/masked arm, seed 37, final set action, assigned a world represented
probability `1.00000003851976`, which the original strict scorer rejects.
The flat model aggregates float32 softmax outputs into each world; numerical
aggregation is a plausible explanation for this observed overshoot.

This does **not** establish the exact original failure's cause: its offending
forecast, full distribution and host configuration were not logged, and the
post-hoc run may have used a different host. The full diagnostic output is
retained at [case6-posthoc-274b2cf.json](results/case6-posthoc-274b2cf.json),
SHA-256 `8ac484d4c78956e6a76bf7bdf0496037bce7c967d94e601dc04a7440e3193fa6`.
V2 remains incomplete and the opened cases are not a fresh held-out test.

## Subsequent full-mass inspection

[CI run 40711735519](https://github.com/robosys-labs/cemm/actions/runs/40711735519)
replayed the selected forecast from the saved weights, without `gold_after`
or accuracy scoring, and retained all eight raw masses. The same individual
value `1.00000003851976` appeared; the joint mass was
`1.0000000433514706`. Dividing all eight masses by that total produced a
unit-sum vector with maximum absolute change `4.335147041345522e-08` and the
same lexicographic MAP on this replay. These are arithmetic observations, not
an approved scoring correction or evidence of model accuracy.

The later run matched the prior replay's individual value but used a different
Python patch and PyTorch configuration. The original failing forecast and
host were not recorded, so it remains unknown whether this is the identical
original fault. The exact output is retained at
[case6-masses-0adc3a2.json](results/case6-masses-0adc3a2.json), SHA-256
`a98d3a497a8dc5fec74fd3c6a3621f4176d1d6d0199478d3f23458e8a022c881`.
