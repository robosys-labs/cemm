# Active nucleus — selective memory comparison

## Current checkpoint — November 10, 2026

Continue on [PR #103](https://github.com/robosys-labs/cemm/pull/103), branch
`research/g5-selective-memory-v1`, based on PR #101 at
`a32c0e81281b4d272a03781ae4415e9a77978c29`. This file is the sole continuation
handoff. Older next-action sections are historical and must not restart work.

The [selective-memory contract](SELECTIVE_MEMORY_PROTOCOL_V1.md) was published
at `6e4aa1b737f4ce36d8608a8adea73e1420eaff42` before implementation. The implementation
provides a shared learned soft write/read over two generic slots, matched dense
native and dense flat controls, new counterbalanced two-meaning histories,
separate challenge predictions and saved-array scoring. Model parameters are
2,188 / 2,244 / 2,280, with 16 recurrent values each. No slot is assigned to a word.

Current execution stage: **all 15 fixed-budget fits complete; challenge not collected**.
Implementation: `58fa61ea96aa729fe65ce3c8ae0b2c30d1854dbd`. Prepared observations:
`52138070c0b51ec17727f95c2bccccf59cac26b3`. Each arm/seed ran once; samples
and all 256 updates matched. Checkpoints are in `data/selective-memory-fit-v1/`.

## One next action

Publish the completed fifteen checkpoints, then run `collect` once; publish all
raw forecasts before `score`. The runner enforces source, data, checkpoint and
publication hashes. Source may not change between preparation and the result.
Preparation and fitting are complete: do not rerun them. Output directories are
create-only, and existing manifests identify completed stages.

```bash
python -m experiments.predictive_nucleus.selective_memory_run_v1 collect
python -m experiments.predictive_nucleus.selective_memory_run_v1 score
```

These are separate publication stages, not a shell sequence. Any failed frozen
gate closes v1 as `REVISE_SELECTIVE_MEMORY_V1`; do not extend its budget, retune its
loss or select successful seeds. Approval for this continuation is already given.

## Closed evidence retained

| Work | Closed outcome | Finding |
| --- | --- | --- |
| [Temporal v1](TEMPORAL_NATIVE_TRANSFER_RESULT_V1.md) | REVISE, 52/80 gates | Native relative gains fail absolute correction and retention gates. |
| [TRAIN trace](TEMPORAL_TRAIN_TRACE_RESULT_V1.md) | Post-teaching interference localized | Updates improve the target while damaging another meaning. |
| [Prefix protection](PREFIX_PROTECTION_TRAIN_RESULT_V1.md) | REVISE, 42/70 checks | Earlier protection improves, final protected accuracy falls from 93.09% to 87.74%. |

Do not rerun these fits, traces, collections, scoring, arithmetic audits or
persistence qualifications absent a specific newly discovered defect. Their
results do not prove state erasure or inadequate capacity.

## Roadmap state

| Stage | Development state |
| --- | --- |
| G1–G2 | Accepted bounded predictive/composition progress retained; full admission limits remain. |
| G3 | Bounded development COMPLETE by [effect/role v3](EFFECT_ROLE_DECISION_V3.md). |
| G4 | [Matched-convention result](MATCHED_CONFLICT_DECISION_V1.md) retained; broader communication open. |
| G5 | Selective-memory v1 executing; scoped-evidence baseline retained; full admission open. |
| G6–G8 | Corpus acquisition, measured Wikipedia utility and guarded integration retain dependency gates. |

New sentence families, full episodic-clear competence, clarification savings at
matched final correctness, independent challenge custody and general calibration
remain open. The inclusive 2,000-line objective remains unmet. This experiment
reuses a supplied native candidate family. Production runtime, semantic authority
and ABIs are unchanged.
