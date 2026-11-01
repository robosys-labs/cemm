# Active nucleus: centering passes four seeds; G3 fitting remains open

Tracking: [#22](https://github.com/robosys-labs/cemm/issues/22),
[PR #75](https://github.com/robosys-labs/cemm/pull/75), stacked on #74.
Updated 2026-11-01. **REVISE_CENTERING_HYPOTHESIS; execution complete.**

## Latest completed evidence

[Decision and regression accounting](CENTERING_DECISION_V1.md) ·
[headline](results/centering-headline-v1.json) ·
[saved-record audit](results/centering-validation-v1.json).

Standard unsaturated versus centered initialization: ten 89-parameter encoders,
256 updates each, the identical 1,152-event NAND training tape and frozen world
weights. Only one initial layout bias differs; the other 88 scalars, inference,
loss and optimizer are fixed. No gold participant-order labels enter training.
All five standard controls exactly reproduce archived final checkpoints.

Source/data freeze: `4bbbc1148d70ddefb8813b0c435f9ef22c6c5016`.
Actual checkpoint freeze: `7826726ff67e1c743c0a3cccbe7a9d35574642cb`.
One fit, collection and score completed; no research retry or seed selection.
All 243,840 planned forecasts and 17,280 evaluator-only native references exist.
Fresh evidence covers relay4/fork_return5 event structures; words/layouts were
already opened. Old bilingual, lexical, binding and saturation banks are retention.

| Same-bank metric | Standard unsaturated | Centered |
|---|---:|---:|
| Fresh complete worlds correct | 11,868/17,280 | 15,268/17,280 |
| Training-withheld-cell worlds correct | 7,048/11,520 | 9,744/11,520 |
| Fresh mean NLL | 1.474851 | 0.370798 |

Seeds **7, 23, 37 and 53 pass every criterion under both laws; seed 11 fails**.
The candidate repairs 3,408 fresh worlds but breaks eight and worsens NLL on
7,230 records. Archived exact regressions remain: bilingual 0, lexical 2,080,
binding 464, saturation eight. Paired retention breaks 22 binding and eight
saturation predictions. All remaining exact regressions belong to seed 11.
These are dependent law/seed/view counts, not independent trials or G3 admission.

Seed 11 still has all-positive learned layout factors and training NLL 0.336042,
above the frozen 0.05 limit. Centering repairs two earlier failing seeds without
solving robust fitting. The observed rank-one layout failure remains localized;
more capacity or additional fitting is not justified by this pooled gain.

## Implemented next candidate; no research fit

[binding_layout_coordinates.py](binding_layout_coordinates.py) replaces the four
redundant affine layout scalars with three unconstrained response coordinates:
**88 parameters**, versus 89. It preserves the centered initial function on all
three legal identity masks and the other 85 scalars. No sign, zero mean, word
meaning or role is forced; the full legal-mask response class R^3 is preserved.

The old layout Jacobian has `J J^T = I + 2 11^T`, with common/contrast
sensitivities 7/1/1 under unpreconditioned gradient descent. Direct coordinates
remove this coupling. This is a testable parameterization hypothesis, not an
Adam convergence proof. Candidate: **IMPLEMENTED_NOT_SCIENTIFICALLY_EVALUATED**.

Next: freeze one fresh centered-versus-coordinate comparison with matching
initial functions, the same observed tape, optimizer, 256 updates and all five
seeds. Publish source/challenge before fitting and actual weights before collection.
Preserve exact, probability, paired/archived retention and masking/swap criteria.
Use fresh event structures and label opened banks as retention. No closed-study
rerun, extra capacity, G4 advance or G1/G2 backtracking.

## Verification and limits

The separate stdlib audit reproduces the result with **3,430,239 checks and zero
discrepancies**, covering 76 source bindings, 81 historical bindings, all ten
initial states/checkpoints and every saved record. It runs no model or original
scorer. This remains internal verification under public same-team custody.

The final suite passed all **934 tests** in 78.865 seconds, including the five
coordinate-candidate tests; **31 protocol locks pass**. The
[execution receipt](results/centering-execution-v1.json) retains verification
provenance and setup failures. Retained research Python is **40,718 lines**,
including 17,732 test lines. The inclusive 2,000-line target remains unmet;
compact parameter count and compact implementation are separate objectives.
Fitting consumed 21.786086 CPU seconds; cached prediction regions 4.842147 CPU
seconds, excluding preparation, serialization, scoring and native references.
No matched-consumed-compute or service-latency claim follows.

## Preserved roadmap

| Stage | Current state / remaining work |
|---|---|
| G1 | Development ready for G2; original scientific admission remains NOT_ADMITTED. |
| G2 | Selected composition, hidden propagation and timing complete for development; formal admission remains open. |
| G3 | Bilingual/lexical results retained. Centering study complete but fails all-seed gate; coordinate candidate awaits prospective comparison. |
| G4 | Held-out goal-directed communication against silent/random/shuffled controls. |
| G5 | Durable learning, useful clarification and retention across episodes. |
| G6 | Grounded corpus transfer beyond retrieval/frequency controls. |
| G7 | Frozen-bank 3x supported utility with precision, retention and cost gates. |
| G8 | Independent reproduction and reviewed integration/rollback. |

[Prior centering rationale](TRAINING_GRADIENT_AUDIT_V1.md),
[activation-study result](SATURATION_DECISION_V1.md) and
[ACCEPTANCE.md](ACCEPTANCE.md) retain their declared scope. Earlier KEEP/REVISE/STOP
results, protocols, data and checkpoints remain intact. The binding study's
STOP_INCOMPLETE_EXECUTION is not relabeled. Native inference/evidence/learning
APIs, production authority and the 562-parameter acquired worlds are unchanged.
Supplied identity resolution, two contact alternatives, filtering and endpoint
feedback do not establish unrestricted language or a learned clarification policy.
