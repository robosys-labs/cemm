# G5 transformed-frame recovery qualified

The frozen PR #99 recovery qualification is complete. Two full invocations at
implementation commit `9083c5c0f371c8d8a950abb4e8f748b95ff8d778` produced
byte-identical reports and checkpoint banks. The final decision is
**`QUALIFIED_TRANSFORMED_FRAME_RECOVERY`**.

This closes recovery of the learned-coordinate interpretation frame through
successful explicit checkpoints and separate Python processes. It uses the
already published native projection bank; it does not establish temporal
correction or scientific G5 admission. The
[protocol](COORDINATE_PERSISTENCE_PROTOCOL_V1.md) was published at
`cd2a54e18463960e47d477b26fded26ae1b58a1f` before the implementation.

## Complete recovery result

Each invocation covers **23,040 trial/view contexts**: all five fitted seeds,
both physical laws, all three mapping views, and 768 contexts in every one of
the 30 seed/law/view cells. Each invocation uses three distinct sequential
child processes: produce, resume, and recover.

| Check per complete invocation | Count | Result |
|---|---:|---|
| First-observation checkpoints and cold reloads | 23,040 | Exact original posterior and target forecast |
| Retained two-observation checkpoints and cold reloads | 23,040 | Exact original posterior, forecast, and ordered provenance |
| Retained/reset query-policy branches | 138,240 | Exact ask/action/value, purchased history, posterior, and forecast |
| Held branches | 118,080 | Original state and receipt inventory preserved |
| Retained purchases | 8,640 | Published purchased histories reproduced |
| Reset purchases | 11,520 | Published purchased histories reproduced |
| Identical duplicate deliveries | 46,080 | Idempotent |
| Conflicting existing IDs | 138,240 | Atomic rejection: 46,080 each for prefix, endpoint, and roster changes |
| Recovered checkpoint round trips | 23,040 | Byte-identical checkpoint output |

All comparisons passed. The adverse mapping controls and expensive or
unavailable query branches retain their original decisions and histories.
Source, frame, public-prefix, and provenance checks passed before and after
execution. No model was fitted, retuned, or invoked to regenerate native
projections during this qualification.

The [qualification receipt](results/coordinate-persistence-v1/qualification.json)
contains every cell's counts, the source hashes, resource measurements, and
the repeat decision. Its raw per-run decision is
`RECOVERY_CHECKS_PASSED_PENDING_REPEAT`; the final qualification follows the
successful repeat and independent artifact audit.

## Published evidence and restart handoff

The complete [replay report](results/coordinate-persistence-v1/replay.json.xz)
contains all three stage reports, every checkpoint hash, every recovered
posterior, and digests binding every forecast and query-policy branch to the
published native references. It is **9,984,208 bytes** compressed and
**37,297,971 bytes** uncompressed. Both invocations have the same compressed
SHA-256:

```text
3bc5eb798ca034f5e003a812a0f6a3d23e011fac02315915e0474c20917af14f
```

The complete [checkpoint bank](results/coordinate-persistence-v1/checkpoint-bank.tar.xz)
preserves all **46,080 files / 215,415,310 payload bytes** in a **6,779,876-byte**
archive. The two original banks were individually hashed and proved identical,
so one complete bank is stored. The
[archive audit](results/coordinate-persistence-v1/checkpoint-archive-audit.json)
records verification of every archived member against the completed report.
The archive uses sorted relative paths and fixed USTAR metadata; it contains
only the `first/` and `retained/` checkpoint files.

Separate [first-run custody](results/coordinate-persistence-v1/custody-1.json)
and [second-run custody](results/coordinate-persistence-v1/custody-2.json)
preserve the commands, process identities, stage hashes, zero exit statuses,
and timing receipts. Numeric PIDs repeat across the separate execution
environments. The two parent invocation UUIDs and all six worker invocation
UUIDs are distinct; each invocation also has three distinct child PIDs.

The [artifact manifest](results/coordinate-persistence-v1/artifact-manifest.json)
binds the delivered evidence files. Future continuation can inspect these
artifacts directly without repeating the completed recovery run.

## Independent verification

The standard-library-only
[auditor](results/coordinate-persistence-v1/independent-audit.py) imports no
CEMM runner, ledger, evaluator, or model. Its
[receipt](results/coordinate-persistence-v1/independent-audit.json) records:

- all **92,160 actual checkpoint files** hashed across the two banks;
- all six stage-report hashes and both execution chains verified;
- fixed sorted context positions 0, 384, and 767 in all 30 cells;
- **180 actual checkpoint posteriors and forecasts** independently replayed;
- **540 query policies** independently reconstructed from the saved observations;
- exact numerical equality with the published references and recorded outputs.

A separate [reviewer spot check](results/coordinate-persistence-v1/third-party-spotcheck.json)
read 12 files from both banks and replayed six distinct checkpoints using
80-digit Decimal arithmetic. Its largest posterior difference from the
floating-point report was `1.1102230246251565e-16`.

For a fresh reproduction, run the unchanged qualification twice at the
measured implementation commit with new output/custody paths and fresh
`run-1`/`run-2` work directories. Keep the auditor outside that frozen checkout
and pass the common output directory as `--evidence-dir` and the frozen
`experiments/predictive_nucleus` directory as `--source-root`. The existing
complete bank is already sufficient for read-only file and provenance review.

## Software validation and cost

The 23 focused synthetic persistence tests pass. The full isolated suite ran
1,336 cases: 1,333 passed, two sealed v7/v8 collectors were intentionally
skipped, and the historical preflight test initially rejected the shallow
checkout. After complete history was fetched, the same guard also required
all tracked files to be physically materialized. With both prerequisites
satisfied, the one affected test and the exact guarded preflight passed.
No source or gate changed, and no other test failure occurred. The resulting
unique-case coverage is **1,334 passed and two intentional skips**. Original
attempts and targeted resolution are preserved in the
[validation receipt](results/coordinate-persistence-v1/validation.json) and
[validation logs](results/coordinate-persistence-v1/validation-logs.tar.xz).
The original protocol and all 37 historical snapshot manifests verified.

| Invocation | Worker CPU seconds | Sum of worker wall seconds | Peak worker RSS, KiB |
|---|---:|---:|---:|
| 1 | 389.341 | 451.597 | 522,540 |
| 2 | 391.327 | 453.631 | 522,380 |

These measurements cover the three worker processes, excluding parent report
compression and the independent audit/package work. The environment was
Python 3.13.5, Torch 2.10.0+cpu, and NumPy 2.3.5, with one configured numerical
thread. The checkpoint archive took 31.545 seconds to build and 1.634 seconds
to stream back and verify.

The existing tranche adds **521 implementation lines** (119 adapter + 402
runner) and **546 test lines**, with **zero additional learned parameters**.
The measured implementation snapshot has **66,646 physical Python lines
across 405 files**, including 27,171 test lines. Publishing the 320-line
independent auditor brings the visible tree to 66,966 lines across 406 files;
the validation archive also preserves the separate 50-line reviewer script.
Including that archived verification source gives **67,016 lines**. The
inclusive 2,000-line objective remains unmet.

## Scope and next work

The qualification covers one writer, successful explicit checkpoints, ordered
evidence replay, and externally supplied frame/source bindings. It preserves
the existing contract for valid zero-support evidence and unavailable belief.
Automatic crash journaling, concurrent writers, and independently authenticating
the supplied model bindings are outside this checkpoint contract.

The next scientific work remains the fresh temporal/scope experiment:
distinguish a durable correction from a temporary exception or conflicting
source, first establish what observations can separate them, and compare
learners on prospectively identical realized histories. New sentence families,
uncertainty on indistinguishable evidence, clarification savings at matched
final correctness, and retained competence after episodic-memory clearing
remain required. **G5 scientific admission is NOT_ADMITTED; G6–G8 retain their
existing dependency gates.**
