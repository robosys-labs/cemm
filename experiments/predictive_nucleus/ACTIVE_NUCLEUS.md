# Active nucleus — TRAIN trace closed, one objective comparison next

## Current checkpoint — November 9, 2026

Continue on [PR #101](https://github.com/robosys-labs/cemm/pull/101), branch
`research/g5-temporal-transfer-v1`. This file is the sole continuation handoff;
older next-action sections describe completed or superseded work.

The [frozen temporal v1 comparison](TEMPORAL_NATIVE_TRANSFER_RESULT_V1.md) is
CLOSED with `REVISE_NATIVE_TEMPORAL_UPDATER`. The subsequent
[TRAIN receipt trace](TEMPORAL_TRAIN_TRACE_RESULT_V1.md) is also CLOSED with
`LOCALIZED_POST_TEACHING_INTERFERENCE`: one inference run, ten unchanged fits,
2,048 existing TRAIN histories and 5,358 passing saved-array audit checks.

Native protected accuracy falls from 99.57% after teaching to 95.49% after the
claim, 92.94% after the first answer and 93.09% after the second. Of 696 initially
correct predictions still wrong at final, the earliest losses are the claim
(147), first answer (312) and second answer (237). The same updates improve
target forecasts. The evidence identifies behavioral interference, without
separating hidden-state damage from a query-dependent readout problem.

Source publication is resolved. The approved source trees were published as
`d446ede2e5d62a057be18ae9403503bcae087ebf` and
`eb8c4879f72a7da1f65dec50ef104032d4487872` before the trace. The
[publication mapping](results/temporal-train-trace-v1/publication.json)
records exact tree equality with the approved local commits. No repeated
permission request, checkout recovery, preparation or original study rerun is
needed for this continuation.

## One next action

Implement the published [prefix-protection TRAIN protocol](PREFIX_PROTECTION_TRAIN_PROTOCOL_V1.md),
verify its synthetic equivalence checks, publish the implementation, and execute
its fixed fit/evaluation/comparison stages in order. Both original models and
training histories stay unchanged. Only the existing protected sixth loss moves
across the three post-teaching horizons; total loss terms and update budget stay
fixed. Publish all ten new checkpoints before inference and raw forecasts before
comparison. Keep every adverse result and stop after the registered decision.

This is TRAIN feasibility, not a fresh challenge. A passing development screen
would only justify designing a new study with new observable histories and
counterbalanced challenged/protected words. Hard-routing writes by the supplied
word ID would provide protection by construction in the current fixture.

## Roadmap state

| Stage | Development state |
| --- | --- |
| G1–G2 | Accepted bounded predictive/composition progress retained; original scientific-admission limits remain. |
| G3 | Bounded development COMPLETE by [effect/role v3](EFFECT_ROLE_DECISION_V3.md). |
| G4 | [Matched-convention result](MATCHED_CONFLICT_DECISION_V1.md) retained; broader communication and full admission open. |
| G5 | Scoped-evidence baseline retained; temporal v1 and receipt trace closed. One objective-only TRAIN feasibility comparison next; full admission open. |
| G6–G8 | Corpus acquisition, measured Wikipedia utility and guarded integration retain their dependency gates. |

New sentence families, competence after full episodic clearing, clarification
savings at matched final correctness, independent challenge custody and general
calibration remain open. The inclusive 2,000-line objective remains unmet.
Production runtime, semantic authority and ABIs are unchanged.

## Closed evidence — do not repeat without a new defect

- [G3 accepted result and limitations](EFFECT_ROLE_DECISION_V3.md).
- [G5 v8 negative-result audit](JOINT_TRUST_AUDIT_V8.md).
- [TRAIN evidence ledger](PHYSICAL_LEDGER_RESULT_V1.md).
- [Static transport](COORDINATE_TRANSPORT_RESULT_V1.md) and [persistence](COORDINATE_PERSISTENCE_RESULT_V1.md).
- [Temporal observability](TEMPORAL_OBSERVABILITY_RESULT_V1.md).
- [Temporal native v1 result](TEMPORAL_NATIVE_TRANSFER_RESULT_V1.md).
- [Completed TRAIN trace](TEMPORAL_TRAIN_TRACE_RESULT_V1.md) and [artifact manifest](results/temporal-train-trace-v1/manifest.json).
