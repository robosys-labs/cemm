# Native SET acquisition v2 — KEEP

**Decision: `KEEP_NATIVE_SET_ACQUISITION`.** Every frozen criterion passes for all
five seeds and both laws. Updated 2026-11-02, [PR #78](https://github.com/robosys-labs/cemm/pull/78),
tracking [#22](https://github.com/robosys-labs/cemm/issues/22).

[Protocol](set_acquisition_protocol_v2.json) · [headline](results/set-acquisition-headline-v2.json) ·
[execution receipt](results/set-acquisition-execution-v2.json) ·
[complete decision](results/set-acquisition-v2/scored/decision.json) ·
[saved-record audit](results/set-acquisition-saved-audit-v2.json).

## Result

| Measure | Result |
|---|---:|
| Identifiable acquired-world forecasts | **16,640 / 16,640 correct** |
| Native SET forecasts | **11,520 / 11,520 correct** |
| Mean SET negative log likelihood | **0.004149956** |
| Ambiguous actual-world MAP forecasts | **1,280 / 2,560 correct** |
| Maximum ambiguous total variation from conditional oracle | **0.007081035**, bound 0.1 |
| Unsupported MAP / known-fixed-coordinate errors | **0 / 0** |
| Identifiable regressions against inherited parent | **0** |
| Historical language worlds | **131,520 / 131,520 correct** |
| Retained world / language-order MAP changes | **0 / 0** |
| Maximum world / order log drift | **1.4211e-14 / 1.0658e-14**, bounds 1e-10 |

Ambiguous cases retain conditional uncertainty. The 50% actual-world MAP result
is expected for these balanced unresolved two-mode cases; it is not counted as
exact success. All family/information strata, SET cells, identifiable trajectories,
paired reversals and six retention banks pass for each seed under both laws.

Each world remains **562 parameters**. The exact same 48 observed episodes were
used for 256 fixed updates. The permitted 68 scalars changed; all 494 protected
scalars remained bitwise unchanged. Final training NLL spans
0.002010591–0.003508505. Language weights remain byte-identical.

Adverse probability changes remain visible: retained NLL worsened on 16,738
records, improved on 17,406 and tied on 97,376. These tiny differences pass the
prospective numerical bounds and exact decision checks.

## Publication and verification

| Stage | Public commit |
|---|---|
| Source, protocol, data and runtime before fitting | `aabea061388d10ab9ad255983075464d9e8401db` |
| Ten actual checkpoints before collection | `59fb13bfd57b575bdf5ee0212afe53df2388e213` |
| All 189,120 raw forecasts before scoring | `c3f5379314dfed65c18b9bcee4d281b0b39afc85` |

One fitting stage, one collection and one complete score; zero research retries.
Remote trees were verified against local trees at each stage. The user explicitly
approved publication after the earlier automatic approval-review block. The
published source tree is identical to the previously verified prepared tree.

The input-only audit passed **17,967 checks** before target parsing. A separate
arithmetic implementation reconstructed the result with **5,201,663 checks and
zero discrepancies**, running neither model nor original scorer. This is same-team
implementation independence, not independent challenge custody. Software evidence
retains 1,013 passing tests, 34 protocol locks and original frozen-input preflight.

Fit, collection and scoring consumed 44.660, 64.980 and 53.688 CPU seconds.
These are not matched-consumed-compute comparisons. Completed research code
retains 45,093 Python lines, including 19,165 tests; the inclusive 2,000-line
target remains unmet.

## Consequence for G3

Freeze these accepted worlds for a separate effect/role language and goal study.
Native acquisition is accepted for development; this result alone does not close
G3. G1/G2 development readiness and coordinate transfer remain intact. Formal
scientific admission remains open.

V1 is preserved as **SCORING_ABORTED / REVISE_NATIVE_SET_ACQUISITION**. Its exact
rule was not changed or rescored. V2 has its own prospective tolerances, fresh
compositions, published evidence and complete decision.
