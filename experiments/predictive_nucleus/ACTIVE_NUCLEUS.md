# Active nucleus: training failure localized; G3 remains open

Tracking: [#22](https://github.com/robosys-labs/cemm/issues/22),
[PR #73](https://github.com/robosys-labs/cemm/pull/73). Updated 2026-10-31.
Latest learned-study result: `526c39db7030080cf7c1fd1f8ff7e1f9c6190051`.
**REVISE_SATURATION_HYPOTHESIS; execution complete, not scientific admission.**

## Current evidence

[Decision and full accounting](SATURATION_DECISION_V1.md).
Ten paired original/unsaturated-factor fits completed 2,560 updates; the single
collection produced all 209,280 candidate/control/retention records plus 17,280
separate native-action references. Each language model has 89 parameters and
identical initial tensors, observed NAND histories and prescribed update budget.
Only the two terminal tanh operations differ. No world-model weights changed.

Source/data freeze: `cf6943b552dc7c255e416c47222d97b084b31ea3`.
Checkpoint freeze: `1b73d3e94406bf5ceb55a5390bfb4b3a1c2f0cf4`.
The encoders transfer unchanged from NAND to NOR. New evidence concerns four
fresh words, eight withheld word-layout cells and diamond/bridge sequences;
opened banks are labeled retention. This is public same-team custody.

The candidate improves pooled fresh exactness from 8,809/17,280 to 11,886/17,280
and withheld-cell exactness from 4,272/11,520 to 7,064/11,520. Against the paired
original it repairs 4,148 fresh worlds but breaks 1,071. It also breaks 4,160
archived lexical and 1,208 archived binding predictions. These dependent counts
have different comparison references; aggregate gains do not justify replacement.

Seeds 7/37 pass every criterion under both laws; seeds 11/23/53 fail. The same
three miss the observed-training NLL <=0.05 criterion despite improved fit.
Terminal saturation alone is not a reliable repair. Two successful seeds show
a bounded representable solution, not robust fitting or general language.

PR #73's [saved-record verification](results/saturation-validation-v1.json) reproduces the
decision with 3,032,778 checks and zero discrepancies: 70 source bindings, 63
historical bindings, ten checkpoints and every planned record. No model or closed
collector was rerun. That tranche added twenty passing tests; its local suite has 892 passes and
one checkout-only skip, with all 30 locks passing. Retained research Python is
39,036 lines including 17,021 test lines; the inclusive 2,000-line goal is unmet.

## Completed training-only diagnostic and next implementation

[Loss/gradient audit and full interpretation](TRAINING_GRADIENT_AUDIT_V1.md).
All ten saved encoders reproduce their post-training loss on 1,152 observed NAND
events each, with zero parameter updates or held-challenge reads in the diagnostic.
The three failing unsaturated seeds all have same-sign learned layout factors;
the two passing seeds have sign-changing factors. The rank-one readout cannot
reverse two words' preference ranking across layouts while its layout factors
retain the same sign. Strong immediate output gradients remain, and the full
parameter gradients are nonzero. This localizes a fitted-representation failure,
not a proved lack of model capacity or a reliable repair.

`binding_centered_init.py` implements a 19-line, opt-in initial-layout centering
candidate: change one bias scalar, preserve the other 88 initial scalars, retain
the exact same 89-parameter class/inference/loss. No role or position polarity is
prescribed. The bias stays trainable. Candidate status is
**IMPLEMENTED_NOT_SCIENTIFICALLY_EVALUATED**; historical registries are untouched.

Thirteen new tests pass; full local suite: 905 passes/one checkout-only skip;
all 30 locks pass. Retained research Python: 39,444 lines; the original inclusive
2,000-line goal remains unmet. Full derivative evidence is in the delivery bundle;
the committed summary binds all inputs, sources, seeds and its complete-artifact hash.

Next: one fresh prospective standard-unsaturated versus centered-initialization
comparison at all five seeds. Keep observed histories, 256 updates, optimizer,
world weights and criteria identical; disclose the single intentionally different
initial scalar. Freeze the new challenge/source before fitting and actual weights
before collection. Retain all seeds, exact/probability/retention requirements and
failures. Do not rerun a closed challenge, add capacity or advance to G4. No new
candidate fit, challenge bank or collection has occurred in this tranche.

## Preserved roadmap and boundaries

| Stage | Current state / remaining work |
|---|---|
| G1 | Development ready for G2; original scientific admission remains NOT_ADMITTED. |
| G2 | Selected composition, hidden propagation and explicit timing complete for development; formal scientific admission remains open. |
| G3 | Lexical result retained; paired activation study complete but failed overall. Training failure localized; centered-initialization candidate awaits a fresh paired test. |
| G4 | Held-out goal-directed communication against silent/random/shuffled controls. |
| G5 | Durable learning, useful clarification and retention across episodes. |
| G6 | Grounded corpus transfer beyond retrieval/frequency controls. |
| G7 | Frozen-bank 3x supported utility with precision, retention and cost gates. |
| G8 | Independent reproduction and reviewed integration/rollback. |

The [previous complete handoff and retained decisions](https://github.com/robosys-labs/cemm/blob/594dc715d7562587568858be4ad62bc51c581786/experiments/predictive_nucleus/ACTIVE_NUCLEUS.md),
[full native API guide](https://github.com/robosys-labs/cemm/blob/2336a0bbaedca1840a2ab8e1616ebbdf3e26f82b/experiments/predictive_nucleus/ACTIVE_NUCLEUS.md),
and [ACCEPTANCE.md](ACCEPTANCE.md) remain authoritative for their declared scope.
All earlier KEEP/REVISE/STOP results, source pins, data and checkpoints are intact.
The prior binding study's original STOP_INCOMPLETE_EXECUTION is not relabeled.

Native active-inference-v6, active-evidence-v2, active-learning-v1 and native
checkpoint v1 are unchanged. Supplied identity resolution, two contact alternatives,
world filtering and full endpoint feedback are not learned general language or a
clarification policy. Domain/resource limits and production authority stay intact.
No AGENTS, production runtime, external-effect or integration change is implied.
