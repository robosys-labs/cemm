# Hybrid MVP R1 Legacy-Test Retirement Design

**Status:** approved design; implementation pending
**Date:** 2026-08-12
**Scope:** obsolete R1 phase tests and their governed inventory records
**Starting commit:** `8cd27234454caae6942888c18b5d497d6d2490ee`

## 1. Goal

Restore a truthful G0-through-R4 replay without adding compatibility behavior for
retired R1 expectations. The active R3/R4 semantic runtime remains authoritative.
Legacy tests are retained only when they still protect an active contract and
have no reviewed successor.

## 2. Evidence

Fresh post-merge phase replay passes G0, R2, R3, and R4. R1 alone fails three
legacy assertions:

1. two episode tests construct `HybridRuntime` without the now-required R3
   owner; and
2. one integration test expects `CycleStatus.UNSUPPORTED` for `hello`, while the
   active runtime correctly returns a typed `PARTIAL` result.

Each assertion already has a reviewed R3 successor with the same
`assertion_ref`:

- `assertion:r1-episode-verified-meaning-separation`;
- `assertion:r1-episode-strict-codec`; and
- `assertion:r1-one-orient-transform-pass`.

The failures therefore identify stale predecessor tests, not missing runtime
compatibility.

## 3. Approaches considered

### A. Retire the superseded R1 predecessors

Delete the three obsolete test functions and their local metadata entries.
Keep their reviewed R3 successors as the only executable lineage leaves.
Regenerate the governed test inventory and G0 inventory receipt.

This is the selected approach. It follows the existing supersession model,
removes drift and bloat, and preserves one active assertion owner.

### B. Add an R1 compatibility owner

Teach the current runtime to operate without the R3 owner and stop after VERIFY.
This would add a second runtime behavior solely to satisfy historical tests and
would weaken the exact active owner contract. It is rejected.

### C. Rewrite the R1 expectations to current R3 behavior

Update the predecessors so they pass against the current runtime while retaining
the R3 successors. This would duplicate assertion coverage across phases and
obscure which test is authoritative. It is rejected.

## 4. Exact retirement scope

Remove only these predecessor nodes:

- `tests/test_r1_episode_runtime_path.py::test_r1_episode_builder_uses_process_and_separates_derivation_from_meaning`;
- `tests/test_r1_episode_runtime_path.py::test_r1_episode_codec_is_strict_bounded_and_authority_bound`; and
- `tests/test_r1_phase_integration.py::test_r1_composition_root_runs_each_orient_transform_once`.

Remove imports and helpers only when they become unused as a direct consequence.
Do not delete unrelated R1 tests, historical evidence artifacts, reviewed R3
successors, or active runtime behavior.

## 5. Governance and data flow

The implementation follows the existing literal-metadata pipeline:

```text
delete obsolete predecessor tests and metadata
-> verify reviewed R3 successor lineages remain unique
-> regenerate deterministic test inventory
-> regenerate canonical G0 inventory receipt
-> validate document-authority and inventory pins
-> replay G0, R1, R2, R3, and R4 phase gates
```

No test selector may hard-code exclusions for these nodes. No validator may be
weakened. The source inventory must derive the smaller executable set from the
actual remaining tests and the reviewed successor lineage.

## 6. Acceptance criteria

The change is complete only when:

1. the three predecessor functions and metadata entries no longer exist;
2. each preserved assertion identity has exactly one active reviewed successor;
3. source-only inventory verification passes for G0 through R4;
4. regenerated inventory and receipt artifacts are canonical and deterministic;
5. fresh G0, R1, R2, R3, and R4 phase gates all pass;
6. R3/R4 authentic runtime and 400-case corpus behavior remain unchanged; and
7. no compatibility shim, permissive owner fallback, or duplicate legacy test is
   introduced.

## 7. Failure handling

If removing a predecessor exposes a missing successor, incorrect assertion
identity, or inventory lineage defect, stop and repair the earliest metadata
owner. Do not restore the obsolete behavior merely to make the phase green.
If an assertion still protects active behavior not covered by its successor,
split out only that distinct active contract as a new reviewed test.
