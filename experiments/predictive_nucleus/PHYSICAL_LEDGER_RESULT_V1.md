# G5 physical evidence recovery qualified on TRAIN

On November 6, the two complete process-separated invocations satisfied the
published protocol. The final decision is `QUALIFIED_TRAIN_RECOVERY`.
The [protocol](PHYSICAL_LEDGER_PROTOCOL_V1.md) was published at
`c6f48f6cdda4ad2092931ee88901fdfebe1a4732`. Implementation was published at
`a0f222eb88885ec851259b46906c8496a2f6d0b9` before either native invocation.

## Recorded result

All 80 ordered routes from the existing 16 teaching records and five fitted
worlds appear in each invocation. The worlds and delivery orders reuse those
teaching observations. Every seed-qualified receipt appears once as warm-up
and once as query.

| Check per complete invocation | Coverage | Observed result |
|---|---:|---|
| Initial checkpoint recovery | 160 | Exact posterior equality with uninterrupted and published references |
| Query policy | 960 | Exact action, ask, expected utility and query-value equality |
| Post-purchase recovery | 120 | Exact posterior equality with pre-restart, uninterrupted and published references |
| Hold branches | 840 | Receipt inventory and canonical snapshot bytes preserved |
| Unconsumed endpoint complement | 960 | Every pre-query decision preserved |
| Identical duplicate deliveries | 320 | Idempotent in every case |
| Conflicting existing IDs | 960 | Atomic rejection in every case |
| Completed two-receipt delivery orders | 20 pairs | Maximum posterior difference `1.1102230246251565e-16` |

Each conflicting-ID category has 320 attempts. The categories change the
public-prefix digest, observed endpoint or likelihood distribution. Every
attempt preserves the accepted receipts, posterior and checkpoint bytes.
Each of the six policies per prior starts from the same saved state, and each
purchased answer is retained in its own branch. Recovery reproduces the
original 80 reset and 40 retained cheap menu-identification purchases.

Both complete reports are byte-identical, with 755,169 uncompressed bytes and
SHA-256 `53c263720075d734a7375782f1912be249edf7e40922a58397014c5d96e15c5c`.
The complete [replay report](results/physical-ledger-v1/replay.json.xz)
preserves those bytes in an 18,696-byte XZ artifact. It contains every route,
binding, snapshot hash, prior, policy and purchased posterior.

The [qualification receipt](results/physical-ledger-v1/qualification.json)
records the repeat comparison, source hashes, all counts and software
validation. Separate [first-run custody](results/physical-ledger-v1/custody-1.json)
and [second-run custody](results/physical-ledger-v1/custody-2.json) record each
producer, evaluator and recovery process, its command, parent PID and zero
exit status. Each invocation has three distinct sequential child processes.
Numeric PIDs recur across the separate execution environments.

## Implemented contract

The 141-line [ledger](physical_ledger_v1.py) binds one interpretation frame to
the fitted model, source artifact, ordered physical candidates and endpoint
encoding. It retains supplied probability values and actual delivery order.
Recovery replays the receipt log through the existing posterior update.
Externally expected checkpoint hashes and bindings are required on load.

The fixed bounds are 256 receipts, 32 hypotheses and 64 outcome columns.
Duplicate delivery remains idempotent at capacity. Invalid inputs and reused
IDs with conflicting payloads reject before mutation. Distinct event IDs
remain distinct observations under the supplied event-independence assumption.

A valid observation with zero computed predictive mass remains in the log.
The ledger records the first failed update and makes its belief unavailable,
while retaining later valid observations. Synthetic cases cover both exact
zero support and positive subnormal likelihoods whose products underflow.
An available belief is required for ordinary query decisions.

Checkpoint publication serializes fully, flushes and fsyncs a same-directory
temporary file, then atomically replaces the destination. The qualification
covers one writer and successful explicit checkpoints followed by new Python
processes. Fault-injection tests preserve the previous checkpoint through
write, flush, fsync and replacement failures.

## Software validation

All 16 new synthetic ledger tests pass. The complete isolated suite ran
1,264 tests in 147.467 seconds with zero failures or errors and two intentional
sealed v7/v8 collector skips. The original protocol, all 37 historical
manifests and the guarded comparison preflight verify successfully on the
measured source commit.

The native [qualification driver](physical_ledger_preflight_v1.py) emits
`RECOVERY_CHECKS_PASSED_PENDING_REPEAT` after an individually successful run.
The final qualification receipt records `QUALIFIED_TRAIN_RECOVERY` after the
second complete invocation reproduces the report. Source and protocol hashes
are checked before and after each invocation.

## Next scientific step

This qualification uses already observed TRAIN evidence, supplied event
identity and event-local candidate alignment. The next prospective study
must align interpretations across fresh instances through the learned G3
mapping, then measure actual correctness, correction, calibration and
retained competence against reset, dated-evidence and matched unstructured
controls on common realized histories. Distinct-operation contrasts remain
necessary for a shared-reuse claim. Scientific G5 admission and the G6–G8
milestones remain open.
