# Active nucleus: v2 implemented and frozen; publication approval blocked

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

## Current prospective revision — implemented and frozen; fitting awaits publication

[Native set study v2](SET_ACQUISITION_STUDY_V2.md) now isolates the numerical and
reporting correction. V1 remains immutable and unaccepted. The new version reuses
the same 562-parameter world, 68-scalar mask, exact 48-event observed training tape
and 256 updates. New interleaved-set, rotating-set and contact-set-feedback
compositions have zero audited template/blueprint/identity overlap with training
and the explicitly listed earlier native banks.

Both order/world logs use prospective absolute bounds of 1e-10, with exact
language tensor identity and unchanged world/order MAP decisions required.
Valid scientific failures produce all ten native and sixty retention reports;
invalid evidence still stops. The complete numerical runtime is frozen before
execution and checked in each stage. All native criteria remain unchanged.

Local source/data/runtime freeze: `c3fed8193e619c275229d65a41825ceae876b64c`.
Automatic approval review rejected publication to the public CEMM repository,
including after verifying the user's repository admin/push rights and that the
payload is isolated source/tests plus deterministic synthetic binary-world data.
A fresh explicit user approval is required by that review before remote publication.
The study's publication gate remains intact: **zero fit, collection or score attempts**.

A separate stdlib auditor and synthetic fixtures are now implemented. Its
input-only pre-score mode verifies all rows and runtime/checkpoint bindings
before decoding targets; its full mode reconstructs the eventual decision from
saved records without the model or original scorer. No real v2 audit result exists.
[Exact handoff](SET_ACQUISITION_V2_HANDOFF.md).

Next execution after publication approval: publish the prepared changes, fit all
ten checkpoints once, publish weights, collect/publish all 189,120 forecasts,
run the input-only audit, score once, then audit the saved result. No result or
admission is implied by prepared code or synthetic tests.

Only after a native acquisition pass should the worlds be frozen for the planned
outcome-grounded effect-and-role language study. The current **88-parameter**
language budget is a prospective target, not established feasibility. Static
review finds that the smallest direct four-action readout widens it to **92**
parameters; no such candidate is implemented or trained. Under NAND, SET(A,1)
cannot always be identified from a single endpoint, so the future design must
use contrasting contexts and preserve observationally equivalent alternatives. Use
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

## Current code accounting

The local revision adds **1,537 Python lines**, including **591 test lines**;
**45,093** research lines are retained, including **19,165** test lines. The
inclusive 2,000-line objective remains unmet; new learned parameters = **0**.

## Final local verification

[Software validation](results/set-acquisition-validation-v2.json): **1,013 tests
pass** on clean committed code, all **34 protocol locks** verify, the original
protocol and frozen-input preflight pass. The saved-record auditor also passes
6,620 synthetic arithmetic comparisons. These are implementation checks; v2
research fitting, collection and scoring counts remain **zero**.
