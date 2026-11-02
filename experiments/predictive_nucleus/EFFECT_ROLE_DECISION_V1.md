# G3 effect, role and goal transfer v1 — completed decision

**Decision: `REVISE_EFFECT_ROLE_GROUNDING`. Development G3 remains incomplete;
next stage is G3.** All 15 planned language/control fits, 408,000 formal saved
forecasts and all ten law/seed reports completed. **Zero of ten conditions passes
every frozen criterion.** This is a completed scientific failure, not an execution
abort. No v1 source, model, threshold or evidence has been replaced.

[Exact decision](results/effect-role-v1/scored/decision.json) ·
[complete headline](results/effect-role-headline-v1.json) ·
[execution receipt](results/effect-role-execution-v1.json) ·
[saved-record audit](results/effect-role-saved-audit-v1.json) ·
[frozen study](EFFECT_ROLE_STUDY_V1.md) · [protocol](effect_role_protocol_v1.json).

## Every law and seed

Each condition includes 6,912 fresh canonical candidate forecasts: 6,144
identifiable and 768 ambiguous; all 1,152 held new-word/VOS events remain included.
The table reports the largest mean KL over nonempty family/layout/effect/lexicon
cells and information strata, not merely an overall average. Required floors are
0.95 for identifiable/action/goal accuracy; bounds are **KL ≤0.05**, **bilingual
TV ≤0.05** and **mean retained NLL ≤0.05 per bank**. Exact-world retention and
retained action decisions additionally permit zero regressions/changes.

| Law / seed | Identifiable world accuracy | Action accuracy | Worst cell mean KL | Max bilingual TV | Worst retained-bank NLL | Optimal goals |
| --- | --- | --- | --- | --- | --- | --- |
| nand/7 | 76.790% | 74.074% | 3.318031 | 0.998944 | 0.005162 | 89.844% |
| nand/11 | 100.000% | 100.000% | 0.096978 | 0.068815 | 0.032331 | 100.000% |
| nand/23 | 100.000% | 100.000% | 0.084433 | 0.066054 | 0.070267 | 100.000% |
| nand/37 | 100.000% | 100.000% | 0.132998 | 0.130794 | 0.096592 | 100.000% |
| nand/53 | 100.000% | 100.000% | 0.094052 | 0.077885 | 0.065518 | 100.000% |
| nor/7 | 77.783% | 74.074% | 5.051500 | 0.999566 | 0.005564 | 86.393% |
| nor/11 | 100.000% | 100.000% | 0.109800 | 0.068865 | 0.035025 | 100.000% |
| nor/23 | 100.000% | 100.000% | 0.095351 | 0.066117 | 0.076382 | 100.000% |
| nor/37 | 100.000% | 100.000% | 0.151192 | 0.131015 | 0.104660 | 100.000% |
| nor/53 | 100.000% | 100.000% | 0.106960 | 0.078006 | 0.070916 | 100.000% |

All ten conditions fail conditional probability quality and bilingual agreement.
Seeds 11, 23, 37 and 53 correctly select every identifiable fresh world and every
fresh action, every held new-word/VOS world, and every supplied goal; their
probabilities still fail the frozen checks. In these eight conditions, actual-world
MAP accuracy is 6,528/6,912 because each retains 384/768 correct realized outcomes
on the genuinely ambiguous cases. Those ambiguous realized errors are reported
and do not become identifiable failures.

Seed 7 also fails identifiable accuracy, action identity, uncertainty, unchanged
coordinates, trajectory/role-pair conjunctions and goal quality under both laws.
It has **1,426/1,365 unsupported MAP worlds** and **1,094/1,087 known-unchanged
coordinate errors** under NAND/NOR. Its maximum ambiguous TV is
0.499736766/0.499825283 (limit 0.1), trajectory accuracy
0.578125/0.532552 and role-pair accuracy 0.546875/0.500000. Goal optimality is
1,380/1,536 and 1,327/1,536, with mean regret 0.1015625/0.136067708 and maximum
regret 1.0 (limits 0.01 and 0.05). Exact per-cell, trajectory and paired evidence
is retained in the [scored reports](results/effect-role-v1/scored/manifest.json).

## Retention and controls

All six historical banks remain in every condition. Seeds 23, 37 and 53 exceed
the NLL bound on **saturation, centering and coordinate** under both laws. Seed 37
also causes all **525 exact-world regressions** and **768 changed action MAPs**:
128 action changes per failing bank/law. The changed actions are SET of the second
mentioned participant, rather than contact reversals. Across all 131,520 retention
points, NLL worsens on **89,075**, improves on **41,628**, and is exactly equal on
**817**; no delta is undefined. All adverse records are preserved. The largest
retained NLL is 0.104659507; maximum unwanted SET mass reaches 0.595720141.

The supervised parser chooses every supplied goal correctly in every condition.
Masked and text-only controls remain reported, including their failures. Grounded
effect-sensitive goal accuracy improves by at least 0.1 over both controls in all
ten conditions; those comparisons do not override failed absolute competence or
retention gates. All four two-bit goals per prefix are included, with spectators
fixed and impossible goals retained. NAND/NOR contain 558/714 effect-sensitive
cases, of which 186/294 require SET and 372/420 require contact. All six exact
lexical-identity checks pass, preserving 18 registered and two separately unresolved
identities. Full goal strata, control metrics and gains are in the headline.

## Execution, resources and audit

Source/data publication: [`75fe2474fcbf103a569f3f9375fa899922931b2d`](https://github.com/robosys-labs/cemm/commit/75fe2474fcbf103a569f3f9375fa899922931b2d).
Weights publication: [`6742c7df5b00f966c99c2a93d885d91eb21034e6`](https://github.com/robosys-labs/cemm/commit/6742c7df5b00f966c99c2a93d885d91eb21034e6).
Raw forecasts publication: [`dbdd8ab95588913be5b647e0be789f8ed93c07c7`](https://github.com/robosys-labs/cemm/commit/dbdd8ab95588913be5b647e0be789f8ed93c07c7).
Freeze: `7b500d3bb1811dd484ea0af9ce7131776e7aea6d7a60a33f0e8490e34d494dca`.

One attempt per stage, zero retries: five seeds × grounded/parser/text-only,
256 Adam updates each, 16 new observations plus the same 1,152-event TRAIN tape,
92/92/1,048 language parameters. The ten accepted 562-parameter native worlds
remain immutable. There are **276,480 fresh/control rows + 131,520 retention rows
= 408,000 formal forecast rows**. Software verification passed 1,073 isolated
tests, 35 protocol locks and original frozen-input preflight; 68 source files and
186 historical files are bound.

| Stage | CPU seconds | Wall seconds | Peak RSS (KiB) |
| --- | --- | --- | --- |
| collection | 288.578851 | 288.706685 | 495464 |
| scoring | 189.800669 | 189.905301 | 733232 |
| training | 67.218676 | 67.226605 | 368444 |

Recorded fit/collection/scoring totals are **545.598196 CPU seconds** and
**545.838591 wall seconds**, with maximum peak RSS **733,232 KiB**. Per-fit
subtotals are already inside training and are not counted twice. Optimization
presents 4,485,120 TRAIN targets; final objective measurement presents another
17,520. These are training exposure counts, not additional held-out evidence.

The [pre-score audit](results/effect-role-pre-score-audit-v1.json) passes **2,773
checks** before evaluator parsing. The full saved-record audit passes
**12,946,593 checks with zero discrepancies**, including the immutable native
checkpoints, saved point metrics and exact failed decision. It runs no original
model, scorer or oracle. It verifies publication against local git objects;
it does not establish independent external custody.

## Post-publication diagnosis and prospective v2

The [isolated diagnostic archive](diagnostics/effect-role-v1/README.md) records
**17,520 additional TRAIN-only forecast rows and zero optimizer updates** across
five seeds and three initial/final conditions. These rows are outside the formal
408,000-row bank, bringing explicitly reported formal-plus-diagnostic rows to
425,520. Saved-curve arithmetic and the broader saved-result review add **zero**
model executions, forecasts, gradients, updates, fits or collections. The original
TRAIN diagnostic did evaluate gradients. Its CPU/wall/RSS were not recorded;
those costs, audits and publication are excluded from the recorded stage totals,
not silently treated as zero.

The TRAIN diagnosis establishes that adding raw zero SET logits was not neutral
in probability space. In seed 7, `zef` starts with mean SET mass 3.881199e-7 and
ends at 2.095047e-11 despite informative observed endpoints. This supports a
specific credit-assignment failure. The broader review also identifies probability
and retention failures in the other seeds and a possible coupling between layout
magnitude and effect confidence. These observations do **not** establish a single
cause for every failed gate or prove that normalization will fix them.

The prospective v2 hypothesis changes only the action normalization to
`softmax(concat(log_softmax(contact_logits) + log(2), set_logits))`, preserving
all 92 scalars, inherited initialization, TRAIN tapes, five seeds, 256 updates,
optimizer and numerical criteria. At initialization, total contact/SET mass is
1/2 each while conditional contact probabilities are preserved. A new source/data
publication must precede real v2 execution. V2 requires a fresh bank and retains
the opened v1 bank as explicitly opened regression evidence; v1 stays REVISE.
The old parser is an archived descriptive control on that opened bank, and reused
text-only evidence requires exact current state/curve reproduction. No G4 work
is unlocked by this decision.

## Limits and retained scope

This remains a bounded controlled world with supplied entity identities, four
action candidates, token/layout features and finite externally supplied goals.
Delivered intermediate observations make trajectory conjunctions dependent views,
not autonomous rollouts or independent trials. No unrestricted language,
polysemy, natural-language goal parsing, general calibration or planning claim is
admitted. Parameter/consumed-compute matching and independent custody remain open.
Original scientific admission is **NOT_ADMITTED**. Accepted native SET v2 and
coordinate results remain intact; production runtime, authority and ABIs are unchanged.

Frozen pre-execution code contains **48,323 Python lines**, including **20,486 test
lines**. Archiving the 127-line TRAIN diagnostic and 274-line saved-result reader
adds 401 lines, for **48,724** inclusive lines. The 2,000-line objective remains unmet.
