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
