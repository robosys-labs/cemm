# Initial layout centering: REVISE_CENTERING_HYPOTHESIS

Tracks [#22](https://github.com/robosys-labs/cemm/issues/22) and
[PR #75](https://github.com/robosys-labs/cemm/pull/75), stacked on #74. Completed
2026-11-01. **Execution complete; G3 remains open.**

## Controlled comparison and publication

The [protocol](centering_protocol_v1.json) compares standard unsaturated and
centered initialization of the same **89-parameter language encoder**. Only
`layout.0.bias` changes initially; the other 88 initial scalars, model class,
inference, outcome loss, Adam optimizer and update budget are identical. All ten
fits completed 256 updates on the exact previous 1,152-event NAND training tape.
No gold participant order, world-weight update, extra evidence, seed selection,
early stopping or research retry occurred. Each encoder transfers unchanged to NOR.

Source/protocol/data freeze: `4bbbc1148d70ddefb8813b0c435f9ef22c6c5016`.
Actual ten-checkpoint publication: `7826726ff67e1c743c0a3cccbe7a9d35574642cb`.
The source was public before fitting and actual weights before collection.
All five standard controls reproduce their archived final parameter fingerprints
exactly. The treatment therefore compares against a reproducible fitted control.

All **243,840 planned candidate/control/retention forecasts** and **17,280
separate evaluator-only native references** were produced. New evidence concerns
the ordered `relay4` and `fork_return5` structures. The novelty guard ignores
entity spelling, unused slots and edge direction while retaining event order.
Words, layouts and the eight training-withheld cells were already opened in prior
studies. They are not new lexical-generalization evidence. Four old banks are
explicitly retention. Final masking/swapping shares the canonical observed prefix.

## Results and retained failures

Counts pool dependent laws, seeds, role reversals and lexical views; they are not
independent physical trials. Different historical challenge banks are not a
progress time series. [Headline](results/centering-headline-v1.json),
[full summary](results/centering-v1/scoring/summary.json.xz), and
[frozen decision](results/centering-v1/scoring/decision.json) retain exact values.

| Metric | Standard unsaturated | Centered initialization |
|---|---:|---:|
| Fresh complete worlds correct | 11,868/17,280 (68.68%) | 15,268/17,280 (88.36%) |
| Training-withheld-cell worlds correct | 7,048/11,520 (61.18%) | 9,744/11,520 (84.58%) |
| Fresh mean NLL, nats | 1.474851 | 0.370798 |
| Training-withheld-cell mean NLL | 1.925924 | 0.508038 |
| Fresh order predictions correct | 12,224/17,280 | 15,488/17,280 |
| Exact regressions versus native reference | 5,412/17,280 | 2,012/17,280 |

| Seed | Standard training NLL | Centered training NLL | Centered NAND / NOR correct, each out of 1,728 | All frozen criteria, both laws |
|---|---:|---:|---:|---|
| 7 | 0.002459 | 0.002469 | 1,728 / 1,728 | Pass |
| 11 | 0.338064 | 0.336042 | 712 / 732 | Fail |
| 23 | 0.151573 | 0.003398 | 1,728 / 1,728 | Pass |
| 37 | 0.004346 | 0.004345 | 1,728 / 1,728 | Pass |
| 53 | 0.157624 | 0.003376 | 1,728 / 1,728 | Pass |

Centering repairs the prior failures at seeds 23 and 53; seed 11 remains outside
the unchanged training-NLL limit of 0.05 and fails both law-specific evaluations.
It produces eight fewer correct NAND forecasts than its paired standard control;
NOR exactness ties, while mean NLL worsens under both laws. Every masking/swap
check passes, which does not rescue the incorrect predictions. The decision is
**REVISE_CENTERING_HYPOTHESIS**, with no replacement or scientific admission.

Across fresh forecasts, centering repairs **3,408** and breaks **8** previously
correct worlds. NLL worsens on **7,230**, improves on 9,900, and ties on 150.
Case IDs and full probability differences remain in the saved summary.

| Retention bank / denominator | Standard regressions versus archive | Centered regressions versus archive | Centered repairs / regressions versus paired standard | Paired NLL worsens |
|---|---:|---:|---:|---:|
| Bilingual / 20,800 | 0 | 0 | 0 / 0 | 5,200 |
| Lexical / 41,600 | 4,160 | 2,080 | 2,080 / 0 | 13,203 |
| Binding / 17,280 | 1,208 | 464 | 3,644 / 22 | 9,172 |
| Saturation / 17,280 | 0 | 8 | 3,390 / 8 | 7,231 |

Archived references are the original lexical study's bilingual/lexical forecasts,
the binding study's factor forecasts and the saturation study's unsaturated
forecasts, respectively. These differ from the paired current standard. Against
archived binding forecasts, centering also repairs 4,458; against archived
saturation forecasts it repairs 3,390. All remaining centered exact regressions
belong to seed 11. Gains are insufficient under the frozen all-seed criteria.

## Diagnosis and minimal next implementation

Saved seed-11 centered layout responses remain all positive:
`[0.125702, 2.403539, 0.011255]`. The earlier rank-one diagnosis still applies:
same-sign layout factors cannot reverse lexical preference rankings. Centering
helps fitting at two seeds but does not prevent drift back to this representation.
These saved-tensor calculations require no replay or new training.

The opt-in [layout-coordinate candidate](binding_layout_coordinates.py) removes
one redundant parameter: **88 parameters**, preserving the centered model's
initial responses on all three legal identity masks and its other 85 scalars.
For the old affine map, `l = M w + b 1` with `M = 11^T - I`, its parameter
Jacobian satisfies `J J^T = I + 2 11^T`. The common direction has sensitivity 7,
and the two contrast directions have sensitivity 1 under unpreconditioned gradient
descent. Direct learned response coordinates have identity sensitivity. This is
an optimization hypothesis, not an exact Adam analysis or demonstrated cause.

Every response vector in R^3 remains expressible: the old map realizes `q` with
`w=-q, b=sum(q)`. The candidate does not force signs, zero mean, word meanings or
roles. Equivalence concerns the three supplied legal masks, not arbitrary language
features. **IMPLEMENTED_NOT_SCIENTIFICALLY_EVALUATED**; no research fit occurred.

Next: prospectively freeze one centered-versus-coordinate comparison, matching
initial functions, observed tape, optimizer, 256 updates and all five seeds.
Use fresh event structures and labeled retention; publish source/data before fit
and actual weights before collection. Keep every exact/probability/retention
criterion and failure. Do not recollect this closed study or advance to G4.

## Verification, cost and boundaries

The [stdlib saved-record audit](results/centering-validation-v1.json) reproduces
the complete decision with **3,430,239 checks and zero discrepancies**: 76 source
bindings, 81 historical bindings, ten actual initial states and checkpoints, every
planned forecast and native reference. It executes no model, original scorer,
fitter or collector. This internal verification is not independent custody.

All **934 local suite tests pass** in 78.865 seconds, including 23 added study/audit
tests and five coordinate-candidate tests; **31 protocol locks pass**. The
[execution receipt](results/centering-execution-v1.json) and
[verification logs](results/centering-verification-logs-v1.tar.xz) retain the initial
precommit provenance and test-invocation failures. The fit, collection, score and
saved-record audit each completed once.
Published source checks passed
[invariants/preflight](https://github.com/robosys-labs/cemm/actions/runs/41297210819)
and [source snapshot](https://github.com/robosys-labs/cemm/actions/runs/41297210908).
Final-head checks are tracked separately in PR #75.

Fitting used **21.786086 CPU / 21.788881 wall seconds**, peak RSS 352,208 KiB.
Cached prediction regions total **4.842147 CPU / 4.843606 wall seconds**, peak RSS
434,128 KiB; batch-amortized p95 ranges from 5.260 to 40.077 microseconds across
traces. These regions exclude cache preparation, serialization, scoring and native
references; they are not service latency or matched-consumed-compute evidence.
Runtime: Python 3.13.5, Torch 2.10.0+cpu, NumPy 2.3.5, float64, one deterministic
CPU thread on x86_64. World checkpoints remain unchanged at 562 parameters.

This tranche adds 694 study/audit and 440 test Python lines; the opt-in coordinate
candidate adds 47 source and 93 test lines. Total addition **1,274 lines**; retained
research Python **40,718**, including **17,732 test lines**. The inclusive 2,000-line
goal remains unmet. A compact learned model does not make the research suite compact.
Historical source, data, weights, failed decisions and production authority remain
intact. G1/G2 development readiness is preserved; their scientific gates stay open.
