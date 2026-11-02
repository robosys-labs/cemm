# Active nucleus: native set acquisition ran; retention revision required

Tracking: [#22](https://github.com/robosys-labs/cemm/issues/22),
[draft PR #77](https://github.com/robosys-labs/cemm/pull/77), stacked on #76.
Updated 2026-11-02. **Review: `REVISE_NATIVE_SET_ACQUISITION`.
Execution: `SCORING_ABORTED`; no runner-produced decision.**

## Latest work and actual outcome

[Decision and next step](SET_ACQUISITION_DECISION_V1.md) ·
[headline](results/set-acquisition-headline-v1.json) ·
[execution receipt](results/set-acquisition-execution-v1.json) ·
[retained failure](results/set-acquisition-v1/scored/failure.json).

The selected native set study was implemented and run once. Each of ten inherited
world checkpoints learned from 48 observed before/action/after set episodes for
256 updates. Each remains **562 parameters**: exactly **68 permitted scalars**
changed, while **494 complementary scalars** stayed bitwise unchanged. All final
training NLLs are between 0.002010591 and 0.003508505, below the frozen 0.05 limit.
No architecture, contact module, native inference source or language weight changed.

All **189,120 forecasts** were collected and published before scoring. Scoring
then stopped because unchanged language weights produced order-log values that
were not exactly equal to archived values. The maximum difference is
**1.0658141036401503e-14** across 84,208 unequal order vectors. The exact numerical
execution cause is unresolved. The frozen contract requires exact equality; its
separate world-log tolerance cannot be applied retroactively to the order head.
There was no retry or threshold change, and the full acquisition gate did not pass.

## What the saved-record diagnostics establish

These are explicitly post-stop arithmetic checks, with no model execution,
original scorer rerun or oracle/evaluator access. They do not replace complete
native/contact, ambiguity, trajectory and subgroup acceptance.

| Limited diagnostic | Result |
|---|---:|
| Acquired observed SET worlds correct | **11,520 / 11,520** |
| Parent SET worlds correct | 6,080 / 11,520 |
| SET exact repairs / regressions against parent | **5,440 / 0** |
| Mean SET NLL, parent → acquired | **0.823010064 → 0.004143413** |
| Current and archived language worlds correct | **131,520 / 131,520** each |
| Exact language regressions | **0** |
| Maximum world-log difference | **1.4210854715202004e-14** |

Every law/seed has 1,152/1,152 correct observed SET worlds. The acquired model's
NLL improves on every SET point against its parent. The no-change baseline retains
lower NLL on 4,160 unchanged SET cases and infinite loss on 7,360 changed cases.
Language NLL worsens on 16,738 records, improves on 17,406 and ties on 97,376.
Individual adverse records are retained. Tiny numerical differences are not
evidence of lost exact behavior, but they still violate the chosen contract.

## Verification and publication

Source/protocol/data: `23acab3e0f269906e0803e41673a3b3132e95d22`.
Actual checkpoints before collection: `ad6e6936ceb3170660e50687fa1e1456e4717025`.
Raw forecasts before scoring: `47e2cd4218358bee1e5fdd993920ce38955fc05f`.
One fitting stage, one collection and one failed scoring attempt; zero research
retries. Both source-commit hosted workflows pass: **979 tests**, original
protocol, **33 locks** and frozen-input preflight. The pre-score fit/raw audits
record 178 and 1,792,861 integrity checks with zero discrepancies. These are
same-team checks, not independent scientific custody.

Fitting used 30.468454 CPU seconds; collection used 65.747421 CPU seconds. Exact
scope, memory, publication and code-size accounting are in the execution receipt.
The inclusive 2,000-line target remains unmet. Model size does not measure total
research infrastructure, and software verification does not establish a passed
scientific gate.

## Accepted prior result remains intact

[PR #76](https://github.com/robosys-labs/cemm/pull/76) remains
**`KEEP_LAYOUT_COORDINATES`**. Its 88-parameter language encoder passes all five
seeds and both laws, with 17,280/17,280 fresh worlds, 11,520/11,520
training-withheld-cell worlds and 114,240/114,240 historical canonical predictions
correct. The [coordinate decision](COORDINATE_DECISION_V1.md) retains all probability
changes, limitations and its smaller-parameter comparison. The selected bounded
layout-fitting problem is closed. This native acquisition failure does not reopen it.

## Selected next step — revision not yet implemented or fitted

Resolve the numerical-retention contract before another acquisition decision.
Keep v1 source, protocol, weights, records and failure immutable. Use synthetic
fixtures to distinguish tensor identity, harmless numerical drift and actual
behavior/probability changes. Specify a reproducible numerical execution path or
an explicit order-log comparison rule prospectively. Expected retention failures
should produce a complete failed report, preserving all other diagnostics.

Freeze the revised source, runtime, full reporting behavior and a fresh challenge
before any new fit or collection. Keep the current world, 68-scalar learning mask
and observed learning hypothesis unless further evidence justifies a change.
Do not retry the opened v1 bank or promote its diagnostic accuracy to acceptance.

Only after a native acquisition pass should the worlds be frozen for the planned
outcome-grounded effect-and-role language study. The current **88-parameter**
language budget is a prospective target, not established feasibility. Use
word-independent contact/set alternatives and observed endpoint feedback without
gold action-kind/order labels; preserve ambiguity where alternatives share an
endpoint. No new operator, workspace, generic harness or production path is selected.

## Preserved roadmap

| Stage | Current state / remaining work |
|---|---|
| G1 | Development ready for G2; original scientific admission remains NOT_ADMITTED. |
| G2 | Bounded composition, hidden propagation and supplied timing retained; formal admission remains open. |
| G3 | Bounded coordinate/layout transfer accepted. Native set acquisition requires a numerical-retention revision; effect-and-role language and full G3 remain open. |
| G4–G5 | Learned communication, durable acquisition, correction and lifelong retention remain later work. |
| G6–G8 | Corpus bridge, measured Wikipedia utility and guarded integration remain later work. |

Independent challenge custody, matched consumed-compute comparisons and general
calibration remain open. Original scientific gate definitions and prior failed
decisions are preserved.
