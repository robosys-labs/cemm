# G5 physical evidence ledger and cold-process recovery v1

## Prospective boundary

Freeze this protocol on the published parent `332a057e612c68a70887f09e7fd807cca8eac1ec` before implementing or running native ledger measurements. The study qualifies persistence and evidence custody on the existing TRAIN observations. The active roadmap's next scientific work remains fresh-instance alignment, correction, actual correctness, calibration and retained competence under matched controls.

## Ledger contract

One bounded ledger has one immutable interpretation frame. Bind the exact utterance and ordered entity roster by digest, the frozen world/model SHA-256, the source receipt artifact SHA-256, the ordered physical action tuples, and the endpoint encoding and count. Each receipt carries its stable evidence ID, public-prefix digest, binding digest, physical-endpoint kind, full likelihood matrix and observed endpoint index. The ingestion adapter verifies the pinned source artifacts. These hashes provide reproducible custody under the caller's trust boundary.

Validate identity, binding, physical kind, finite normalized probabilities, dimensions and endpoint before mutation. Preserve raw supplied probabilities and delivery order. Identical canonical payloads with the same evidence ID are idempotent, including after recovery. Changed payloads under an existing ID reject atomically. Distinct event IDs remain distinct evidence even if their numerical payloads match. This relies on the supplied event identity and independence assumptions.

Reuse `physical_query_v1.posterior` for every supported update. A valid receipt with zero computed predictive mass remains accepted and retained. Derive an unavailable posterior and the first failed-update evidence ID, retain later valid receipts, and require an available belief for ordinary decisions. Exact zero support and floating-point underflow can both cause this state. The ledger introduces no correction or numerical inference replacement.

Bound each ledger to 256 unique receipts, 32 hypotheses and 64 endpoint columns. Candidate tuples have at most 16 signed 32-bit integer coordinates. These are fixed implementation limits. Duplicate delivery at capacity remains idempotent. Capacity or malformed-input rejection preserves state.

Persist only schema version, binding, initial prior and ordered receipts. Reconstruct posterior and failed-update state from the log. Recovery requires the caller's expected binding and snapshot SHA-256. Reject duplicate JSON keys, nonfinite constants, unexpected fields, repeated persisted evidence IDs, malformed snapshots and hash or binding mismatches.

A single writer serializes completely, writes a same-directory temporary file, flushes and fsyncs it, and atomically replaces the destination. A failed write or replacement preserves the previous checkpoint and removes the temporary file. The declared recovery boundary is a successful explicit checkpoint followed by a new operating-system process.

## Locked inputs

| Input | SHA-256 |
|---|---|
| `data/effect-role-v3/teach-inputs.json.xz` | `74fecfda5a3287e5109d31990b9c62b34c39d7694bfeae7a6c1b0c50a029770d` |
| `results/g3-g5-receipt-preflight.json` | `90b8cc1d175efd11070c5549bceeba80154db30319faa30ba707852579df2363` |
| `results/physical-query-preflight-v1.json` | `769c7e83ce92c8e216a68c137e22624fa0d4e3ce4e34a62c13c25b5e84c94623` |

Require 16 unique teaching episodes, five worlds with seeds 7, 11, 23, 37 and 53, and 16 unique receipt rows per world. Group by exact utterance and ordered roster into eight pairs per world. Require matching ordered action tuples and distinct evidence IDs and prefix digests within each pair. Evaluate both delivery orders, giving 80 routes. Every seed-qualified row appears once as warm-up and once as query.

## Process-separated qualification

1. A producer process constructs uninterrupted reference states and writes 160 initial snapshots. Each route has a reset uniform ledger with zero receipts and a retained ledger with the warm-up receipt. The producer exits.
2. A new evaluator process receives snapshot paths and externally expected hashes and bindings, loads the 160 ledgers, and evaluates the original 960 goal/fee policies. Each of the six policies per prior starts from the same pre-query state. After a purchase, consume the actual query endpoint into a separate branch and checkpoint it. The published reference predicts 120 purchased branches, 80 reset and 40 retained. The evaluator exits.
3. A new post-purchase process reloads every purchased branch and derives its posterior and receipt inventory. Require one receipt for reset purchases and two for retained purchases.

Use the existing identity and all-ones reward tables and fees .05, .75 and unavailable. The forecast adapter exposes the endpoint likelihood matrix and binding, with outcome-derived fields excluded. Complement the unconsumed query endpoint while holding forecasts and prior fixed and require all 960 pre-query decisions to agree. Apply the original observed endpoint only after a purchased decision.

Compare the 160 initial priors, 960 decisions and 120 purchased posteriors against uninterrupted replay and the pinned published result. Require exact action and ask equality, and maximum absolute numerical error at most `1e-12` for every prior, expected utility, query value and purchased posterior. Require the 840 hold branches to preserve receipt inventory and canonical snapshot bytes. Compare both completed delivery orders for the 20 unordered pairs whose retained branches both purchase, at the same numerical tolerance.

## Duplicate and conflict coverage

At the producer, cold evaluator and cold post-purchase stages, respectively exercise all 80, 80 and 160 accepted receipt occurrences. Each occurrence receives one identical duplicate and three independently altered copies with the same ID. Change the prefix digest, change the observed endpoint to a different valid column, or exchange two unequal entries in one likelihood row while preserving normalization. Require 320 idempotent duplicates and 960 atomic conflict rejections across the three stages, with inventory, posterior and canonical snapshot bytes preserved in every attempt.

Synthetic regression tests cover altered frame/model/source/action order/outcome encoding, caller mutation, distinct equal-valued events, delivery order, full capacity, malformed distributions and snapshots, write/fsync/replace failures, exact-zero and subnormal failed updates, failure retention and cold recovery. Every invalid operation must preserve its prior in-memory or checkpoint state.

## Evidence and decision

Record all route keys, bindings, accepted receipt IDs, snapshot hashes, priors, policies, purchased posteriors, maxima and coverage/rejection counts. Keep process IDs, parent IDs, exit status and invocation commands in a separate execution receipt. Numeric results must reproduce byte-for-byte on a second complete three-process invocation. Publish implementation before measurement and retain the exact measured source commit.

Declare `QUALIFIED_TRAIN_RECOVERY` only if every registered check passes. Otherwise report `REVISE_LEDGER_RECOVERY` with the failed checks and all collected evidence. This is a software and custody qualification on 16 already observed teaching records reused across five fitted worlds. Event independence, cross-layout transfer, learned correction, empirical calibration and scientific G5 admission require further evidence.
