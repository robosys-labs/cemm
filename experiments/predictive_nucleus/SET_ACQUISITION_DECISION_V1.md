# Native set acquisition v1: retention criterion failed; scoring stopped

Tracks [#22](https://github.com/robosys-labs/cemm/issues/22) and
[draft PR #77](https://github.com/robosys-labs/cemm/pull/77), stacked on the
accepted [coordinate comparison, PR #76](https://github.com/robosys-labs/cemm/pull/76).
Recorded 2026-11-02.

**Review disposition: `REVISE_NATIVE_SET_ACQUISITION`. Execution status:
`SCORING_ABORTED`; the frozen runner produced no decision.** All prescribed fits
and forecast collection completed. Scoring stopped at its exact language-order
retention check, before saving any per-seed report. No fit, collection or scorer
was retried, and no threshold or frozen source was changed.

This disposition follows the protocol's retention-failure clause; it is a
post-stop review, not a fabricated completed score. The full native acceptance
comparison remains unavailable. Native set acquisition is not accepted, and
effect-and-role language training is not yet unlocked. The accepted coordinate
result and earlier G1/G2 development gains remain intact; full G3 and independent
scientific admission remain open.

[Frozen study](SET_ACQUISITION_STUDY_V1.md) ·
[headline](results/set-acquisition-headline-v1.json) ·
[execution receipt](results/set-acquisition-execution-v1.json) ·
[original failure](results/set-acquisition-v1/scored/failure.json).

## What was implemented and executed

The existing 562-parameter world had learned contact laws but had received zero
native set events. This study fits only its existing **57 intervention scalars**
and **11 set-only background weights**. All **494 complementary scalars** remain
bitwise unchanged after every update. The architecture, inference, contact
modules and accepted 88-parameter language model are unchanged.

Each of the five seeds, 7/11/23/37/53, under each of NAND and NOR receives the same
fresh **48 observed before/action/after examples** and **256 fixed updates**.
The action family, addressed entity and requested bit are supplied. The neural
output distribution is learned from observed outcomes; it is not assigned from
the requested value. The training tape covers all four prior/request tuples.
Freshness is therefore in identities and sequence compositions, not an unseen
atomic set truth table.

All ten fits finish: **2,560 updates**, exactly **68 permitted scalar changes**
per checkpoint, zero forbidden changes. Saved training NLL falls from a mean
of **0.792795225** to **0.002559423**, with final values between **0.002010591**
and **0.003508505**. Every final value is below the frozen 0.05 limit. These are
training results, not sufficient evidence for acceptance.

Collection produces all **90 traces / 189,120 planned forecasts**:

| Saved forecast inventory | Count |
|---|---:|
| Native parent, acquired and no-change arms | 57,600 |
| Six canonical language-retention banks | 131,520 |
| Missing or duplicate forecasts | 0 |

The deterministic no-change baseline is computed once per law and reused under
seed labels. Counts pool dependent views. Sequences use actual observed-prefix
feedback; they are not autonomous five-step rollouts.

## Why scoring stopped

The frozen contract requires **identical language-order probabilities**, separately
from its 1e-10 tolerance for world log probabilities. `retention()` checks exact
list equality first. The first NAND/seed-7 bilingual record contains:

| Saved order-log value | Value |
|---|---:|
| Archived | -9.316926039300094 |
| Current | -9.316926039300089 |
| Absolute difference | 5.329070518200751e-15 |

That is three floating-point ULPs, but it is not exact equality. The runner raises
`ValueError: frozen language output changed`, retains `failure.json`, and stops.
No completed native/retention reports or automatic KEEP/REVISE decision exist.
The world-log tolerance cannot be applied retroactively to the order head.

A separate standard-library comparison of saved files finds **84,208 unequal
order vectors out of 131,520**, affecting all 60 law/seed/bank cells. The largest
order-log difference is **1.0658141036401503e-14**. Accepted checkpoint bytes and
all five coordinate-language tensor fingerprints are unchanged.

Static inspection of the first failing bank confirms identical input/source
hashes and the same packing and grounded-forecast path. The order head depends
only on token features and fixed language parameters, so updated native set
tensors do not enter this computation. This establishes a numerical
reproducibility discrepancy in the language path. Its exact execution-environment
cause is unresolved. Python versions differ, 3.13.16 versus 3.13.5, but those
records do not establish that Python caused the discrepancy, nor do they identify
a particular CPU or numerical-library dispatch difference.

## Limited post-stop diagnostics

The following are arithmetic inspections of already-published forecasts. They
execute no model or original scorer and open no evaluator/oracle artifacts.
They do not replace the aborted acceptance run or reconstruct its uncompleted
contact, ambiguity, trajectory and subgroup gates.

### Observed native SET endpoints

[Diagnostic summary](results/set-acquisition-v1/native-diagnostic/summary.json) ·
[all point records](results/set-acquisition-v1/native-diagnostic/points.json.xz) ·
[standalone arithmetic](audit_set_observed_v1.py).

| Complete observed SET outcomes | Acquired | Parent | No-change |
|---|---:|---:|---:|
| Correct complete worlds | **11,520 / 11,520** | 6,080 / 11,520 | 4,160 / 11,520 |
| Changed outcomes correct | **7,360 / 7,360** | 4,416 / 7,360 | 0 / 7,360 |
| Unchanged outcomes correct | **4,160 / 4,160** | 1,664 / 4,160 | 4,160 / 4,160 |
| Mean joint NLL, nats | **0.004143413** | 0.823010064 | Infinity |

Every law/seed is 1,152/1,152 correct. The acquired forecasts repair **5,440**
parent errors, introduce **zero** exact regressions, and improve NLL on every SET
point relative to the parent. The largest acquired point NLL is 0.008370146.

The no-change control has zero NLL on its 4,160 unchanged cases, so the acquired
model's NLL is slightly worse there. It gives zero probability to all 7,360
changed cases and therefore infinite loss. These adverse comparisons and
infinities remain in the retained individual records.

### Saved language worlds

[Diagnostic summary](results/set-acquisition-v1/retention-diagnostic/summary.json) ·
[unequal/adverse point records](results/set-acquisition-v1/retention-diagnostic/points.json.xz) ·
[standalone arithmetic](audit_set_retention_v1.py).

All **131,520 archived and current complete-world MAP predictions are correct**;
there are zero exact regressions. Maximum world-log difference is
**1.4210854715202004e-14**, and maximum world-probability difference is
**3.3306690738754696e-16**. NLL increases on 16,738 records, decreases on 17,406,
and is equal on 97,376; every adverse or unequal record remains available.

The diagnostics find no observed SET endpoint error or changed language answer.
They support investigating numerical reproducibility before changing the learned
model. They do not satisfy the frozen exact-order requirement.

## Publication, verification and cost

| Published before the next stage | Commit |
|---|---|
| Source, protocol and data before fitting | `23acab3e0f269906e0803e41673a3b3132e95d22` |
| Actual fitted checkpoints before collection | `ad6e6936ceb3170660e50687fa1e1456e4717025` |
| All raw forecasts before scoring | `47e2cd4218358bee1e5fdd993920ce38955fc05f` |

Remote commit trees were checked against the exact local trees. The pre-score
same-team audits perform **178 fit-record checks** and **1,792,861 raw-record
checks**, with zero integrity discrepancies. They execute no models; the raw
audit opens no oracle. These are reproducibility checks, not independent custody.
Their complete scope and limitations are retained in
[the audit receipt](results/set-acquisition-pre-score-audits-v1.json).

The published source passes **979 isolated invariant tests**, including 25 new
synthetic tests, the original protocol, all **33 manifest locks**, and frozen
input preflight. [Hosted invariant run](https://github.com/robosys-labs/cemm/actions/runs/41416804302)
and [source snapshot](https://github.com/robosys-labs/cemm/actions/runs/41416804346)
both succeed. An initial local preflight error came from shallow Git history;
the exact test passed after fetching complete history, with no source change.
Passing software tests does not override the failed scientific retention check.

The full fitting stage uses **30.468454 CPU / 30.469707 wall seconds**, peak RSS
**343,232 KiB**. Collection uses **65.747421 CPU / 65.770341 wall seconds**, peak
RSS **430,456 KiB**. These scopes include their recorded stage operations; scoring,
publication and diagnostic costs are not included. No matched consumed-compute
or service-latency claim follows. Exact source/test/audit line accounting is in
the execution receipt; the inclusive 2,000-line research target remains unmet.

## Selected next step

Resolve the demonstrated issue with numerical reproducibility and failure
reporting before another native acquisition decision. Preserve this failed
version and all raw records.
Use synthetic numerical fixtures to distinguish unchanged tensor identity,
floating-point output drift and behavioral/probability regression. Record enough
runtime identity to diagnose reproducibility, and prospectively specify an
explicit order-output numerical comparison rule or a demonstrably reproducible
execution path. The current version's exact-equality gate stays unchanged.

Then freeze a new version's complete reporting behavior, fresh challenge lineage,
runtime and criteria before any fit or collection. Expected numerical failures
must be retained as completed failure checks instead of discarding all remaining
diagnostics. Keep the same 562-parameter model, 68-scalar update mask and observed
learning hypothesis unless new evidence specifically justifies another change.
This is a selected revision, not an implemented or fitted v2 and not permission
to retry the opened v1 challenge.

Only after native acquisition passes should frozen worlds support the planned
outcome-grounded effect-and-role language study, with the prospective 88-parameter
target and no gold action-kind/order labels. Distinct native actions can share an
endpoint, so later language criteria must distinguish diagnostic contexts from
observationally equivalent choices. No new operator, workspace, communication
stage or production integration is selected by this result.
