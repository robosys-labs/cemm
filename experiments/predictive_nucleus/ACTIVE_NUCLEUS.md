# Active nucleus — prefix objective closed, selective update design next

## Current checkpoint — November 9, 2026

Continue on [PR #101](https://github.com/robosys-labs/cemm/pull/101), branch
`research/g5-temporal-transfer-v1`. This file is the sole continuation handoff;
older next-action sections describe completed or superseded work.

Three successive pieces of work are complete:

| Work | Closed decision | Consequence |
| --- | --- | --- |
| [Frozen temporal v1](TEMPORAL_NATIVE_TRANSFER_RESULT_V1.md) | `REVISE_NATIVE_TEMPORAL_UPDATER`, 52/80 gates | Native gains do not meet the original admission criteria. |
| [TRAIN receipt trace](TEMPORAL_TRAIN_TRACE_RESULT_V1.md) | `LOCALIZED_POST_TEACHING_INTERFERENCE` | Protected forecasts deteriorate during updates that help the target. |
| [Prefix protection TRAIN comparison](PREFIX_PROTECTION_TRAIN_RESULT_V1.md) | `REVISE_PREFIX_OBJECTIVE`, 42/70 checks | Redistributing the existing protected loss fails final preservation in every native cell. |

The prefix comparison ran all ten fits once with the original models,
initializations, minibatches, 256-update budget and six loss terms per sample.
Protocol, implementation, fits and raw forecasts were published before their
dependent stages. Twelve synthetic tests and the implementation CI passed; an
independent saved-array calculation agrees with all 70 decisions.

Native protected accuracy improves after the claim (95.49% to 98.93%) but falls
after both answers (93.09% to 87.74%): 630 regressions and 83 repairs, 547 net
additional errors. Final target accuracy improves from 83.27% to 84.77%, with a
regression in NAND/53. Final protected accuracy and Brier worsen in all ten
law/seed cells. Mean protected Brier across the three update prefixes also
worsens. The fixed loss allocation is rejected; it is not a preservation fix.

These are TRAIN findings. The original held-out result is unchanged. The data
do not distinguish recurrent-state information loss from a readout defect or
prove insufficient capacity. Full details and every adverse ID are retained in
the [result](PREFIX_PROTECTION_TRAIN_RESULT_V1.md) and
[manifest](results/prefix-protection-train-v1/manifest.json).

## One next action

Freeze a small successor contract for **learned selective recurrent updates**
on prospectively new, counterbalanced two-meaning histories. The owner is the
temporal recurrence and readout (`Model.receive` / `Model.predict`). Specify one
shared learned soft write/read mechanism over bounded generic memory slots,
explicit state/parameter/exposure/optimization budgets and a matched unstructured
control. This is a local architectural hypothesis to test, not an accepted fix.

Challenge either meaning and sometimes both; interleave receipts. Exclude a
protected-word flag, word-indexed slots, identity-based hard write masks and
copied old answers. The existing fixture always updates word 0 and protects
word 1, so hard routing would supply the required retention. Require new
observable histories/structures, fresh challenge custody and final correction
plus protected retention in every condition under the original admission gates.
Freeze the complete contract before implementation or fitting.

Do not run another loss schedule, budget, seed subset or relabelled challenge on
the opened bank. Do not repeat the completed trace, fits, evaluation, scoring,
preflight, publication recovery or arithmetic audits absent a concrete defect.
Approval for the completed publication was resolved; no repeated approval
request is needed. The current version is closed, and no new model is fitted.

## Roadmap state

| Stage | Development state |
| --- | --- |
| G1–G2 | Accepted bounded predictive/composition progress retained; original scientific-admission limits remain. |
| G3 | Bounded development COMPLETE by [effect/role v3](EFFECT_ROLE_DECISION_V3.md). |
| G4 | [Matched-convention result](MATCHED_CONFLICT_DECISION_V1.md) retained; broader communication and full admission open. |
| G5 | Scoped-evidence baseline retained; temporal v1, TRAIN trace and prefix comparison closed. Selective update contract next; full admission open. |
| G6–G8 | Corpus acquisition, measured Wikipedia utility and guarded integration retain their dependency gates. |

New sentence families, competence after full episodic clearing, clarification
savings at matched final correctness, independent challenge custody and general
calibration remain open. The inclusive 2,000-line objective remains unmet.
Production runtime, semantic authority and ABIs are unchanged.

## Earlier closed evidence

- [G3 accepted result and limitations](EFFECT_ROLE_DECISION_V3.md).
- [G5 v8 negative-result audit](JOINT_TRUST_AUDIT_V8.md).
- [TRAIN evidence ledger](PHYSICAL_LEDGER_RESULT_V1.md).
- [Static transport](COORDINATE_TRANSPORT_RESULT_V1.md) and [persistence](COORDINATE_PERSISTENCE_RESULT_V1.md).
- [Temporal observability](TEMPORAL_OBSERVABILITY_RESULT_V1.md).

All three newly completed results are linked above. Use their saved artifacts;
their older next-action text is historical evidence, not an instruction to rerun.
