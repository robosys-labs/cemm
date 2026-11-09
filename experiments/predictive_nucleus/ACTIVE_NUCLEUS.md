# Active nucleus — G5 temporal updater v1 closed

## Current checkpoint — November 9, 2026

**Execution is CLOSED. Decision: `REVISE_NATIVE_TEMPORAL_UPDATER`.**
Continue on [PR #101](https://github.com/robosys-labs/cemm/pull/101), branch
`research/g5-temporal-transfer-v1`. The
[completed result](TEMPORAL_NATIVE_TRANSFER_RESULT_V1.md) and
[scored manifest](results/temporal-native-transfer-v1/scored/manifest.json)
are the current evidence. This file is the sole continuation handoff; older
result documents describe completed work rather than additional next actions.

All ten fits completed exactly 256 updates. All fifteen banks contain all
12,288 TEST cases. Two unchanged saved-record scoring invocations are byte
identical; separate arithmetic and custody audits pass. Do not prepare, fit,
collect or score this version again merely because a new chat begins.

| Gate outcome | Cells passing |
| --- | ---: |
| Attainable accuracy | 0/10 |
| Excess Brier | 0/10 |
| Protected-word retention | 2/10 |
| Confident errors, flat Brier, retained-answer Brier gain, flat cheap utility, retained-answer cheap utility | 10/10 each |
| Total | 52/80 |

Native after-both accuracy is 82.50% versus flat's 74.80%, but the
fixed-schedule conditional optimum averages 94.14%. Retaining the first answer
repairs 3,728 targets and breaks 1,194, while repairing 892 protected outcomes
and breaking 2,512. Protected accuracy falls in every cell, from 95.37% to
92.73% overall. Relative improvement does not meet G5 admission.

## One next action

Publish the source for a **TRAIN-only frozen-checkpoint receipt trace**, then
execute it once on the existing 2,048 TRAIN histories and all ten saved fits.
Measure target and protected predictions after the eight teaching receipts,
the tested-word claim, the first physical probe and the second probe. Identify
the earliest damaging update using paired case IDs. Use existing observed
TRAIN endpoints; no optimizer updates, new examples, simulator, oracle or TEST
access. This is a post-score diagnostic, not a retry of v1.

The current evidence does not justify a larger model, additional hypotheses,
longer training or threshold tuning. A later candidate requires its own frozen
contract and fresh challenge; the opened v1 bank is never training material.

### Prepared continuation — November 9, 2026

**State: READY, NOT EXECUTED; publication approval blocked.** Local commit
`24da4c73c49006aa1d4e2a41304c3c59924e238a` contains the
[trace protocol](TEMPORAL_TRAIN_TRACE_PROTOCOL_V1.md),
[tracer](temporal_train_trace_v1.py), and the exact
[TRAIN projection](data/temporal-train-trace-v1/input.json.xz).
The projection contains all 2,048 existing TRAIN histories and 104 required
native keys per seed. Its SHA-256 is
`660bb412f2d165295c30d2248daa2ae7a334c56d4fa95fe324f80aa356b7063f`.

The [independent saved-array audit](results/temporal-train-trace-v1/independent_trace_audit.py)
is also implemented. It separates predictions already wrong after teaching
from their earliest later regression, retains subsequent repairs and final
errors, and checks every reported metric and paired case ID. The
[preflight receipt](results/temporal-train-trace-v1/preflight.json) records
14 passing focused tests, synthetic transition checks, and verification of all
16 frozen source hashes and ten checkpoint hashes. No real checkpoint trace
or fit was executed.

Automatic approval review rejected the push because it requires explicit
authorization to publish this new payload to the public repository. This
remained blocked after confirming repository admin access and verifying that
the projection exactly selects already-public synthetic source artifacts.
The frozen protocol requires publication before inference. Do not treat the
local source commit as published, rerun the original study, or recreate this
preparation. After authorization, publish this branch, verify its remote head,
and execute the following once with the existing pinned numerical dependencies:

```bash
python -m experiments.predictive_nucleus.temporal_train_trace_v1 trace \
  --root experiments/predictive_nucleus \
  --prepared experiments/predictive_nucleus/data/temporal-native-transfer-v1 \
  --fitted experiments/predictive_nucleus/data/temporal-native-fit-v1 \
  --input experiments/predictive_nucleus/data/temporal-train-trace-v1/input.json.xz \
  --output experiments/predictive_nucleus/results/temporal-train-trace-v1/raw

python experiments/predictive_nucleus/results/temporal-train-trace-v1/independent_trace_audit.py \
  --input experiments/predictive_nucleus/data/temporal-train-trace-v1/input.json.xz \
  --trace experiments/predictive_nucleus/results/temporal-train-trace-v1/raw \
  --fitted experiments/predictive_nucleus/data/temporal-native-fit-v1 \
  --output experiments/predictive_nucleus/results/temporal-train-trace-v1/audit.json
```

Both output destinations must be new. Close the diagnostic with its full
saved-array evidence and a single bounded next action; do not repeat model
execution to obtain a preferred result.

## Closed evidence and publication

| Stage | Durable evidence |
| --- | --- |
| Protocol | `0bdb45172f85b755c7916907cefbcd30f21766ed` |
| Implementation | `cd8f2f6b650b315a71797338b9d43374b71d1631` |
| Prepared TRAIN/TEST | `dd65ff04a17ee3fa69b15c911b6a8796d7b2f7ae`; `data/temporal-native-transfer-v1/manifest.json` |
| All ten checkpoints | `3586f5432db10047cd856b07e1f0ac68fda02e60`; `data/temporal-native-fit-v1/manifest.json` |
| All fifteen raw banks | `a1b360d449c1ab0d54cd6a17714ba65a7cbef533`; `results/temporal-native-transfer-v1/raw/manifest.json` |
| Completed scoring and audits | `results/temporal-native-transfer-v1/scored/manifest.json` |

Uncompressed score SHA-256:
`9dc1e5b7c4b1955af1b84aba1e3fe1763194426e1427366e086058022ed7b806`.
The full score is losslessly stored as `score.json.xz`, retaining every adverse
case. All original model/data/source hashes and historical results remain intact.

## Roadmap state

| Stage | Development state |
| --- | --- |
| G1–G2 | Accepted bounded predictive/composition progress retained; original scientific-admission limits remain. |
| G3 | Bounded development COMPLETE by [effect/role v3](EFFECT_ROLE_DECISION_V3.md). |
| G4 | [Matched-convention result](MATCHED_CONFLICT_DECISION_V1.md) retained; broader communication and full admission open. |
| G5 | Original scoped-evidence baseline retained. Temporal v1 comparison CLOSED with REVISE; learned correction and full admission open. |
| G6–G8 | Corpus acquisition, measured Wikipedia utility and guarded integration retain their dependency gates. |

New sentence-family acquisition, competence after full episodic-memory clearing,
clarification savings at matched final correctness, independent challenge
custody and general calibration remain open. The inclusive 2,000-line objective
is unmet. Production runtime, semantic authority and ABIs are unchanged.

## Historical evidence — do not rerun without a new defect

- [G3 accepted result and limitations](EFFECT_ROLE_DECISION_V3.md).
- [G5 v8 negative result audit](JOINT_TRUST_AUDIT_V8.md).
- [TRAIN evidence ledger](PHYSICAL_LEDGER_RESULT_V1.md).
- [Static transport qualification](COORDINATE_TRANSPORT_RESULT_V1.md).
- [Completed transformed-frame persistence](COORDINATE_PERSISTENCE_RESULT_V1.md).
- [Completed temporal observability and restricted-input audit](TEMPORAL_OBSERVABILITY_RESULT_V1.md).
- [Frozen temporal v1 protocol](TEMPORAL_NATIVE_TRANSFER_PROTOCOL_V1.md).

The full earlier handoff remains in Git history. Old “next” directives are
superseded by the single current action above.
