# Active nucleus: G3 binding evidence recovered; structural transfer still fails

Tracking: [#22](https://github.com/robosys-labs/cemm/issues/22).
Latest collected study: [PR #71](https://github.com/robosys-labs/cemm/pull/71),
`b63749c90fd91148f0451bd2e2fd030f3de279cd`.
Updated 2026-10-31 (Africa/Lagos).

**Current handoff:** [binding recovery and candidate](BINDING_RECOVERY_V1.md).
**Recovered arithmetic:** REVISE_STRUCTURAL_BINDING.
**Original process:** STOP_INCOMPLETE_EXECUTION, retained unchanged. G3 is open.
G1 development readiness remains PROCEED_TO_G2 and G2 development readiness
remains PROCEED_TO_G3. Formal G1 admission is NOT_ADMITTED; formal G2 remains open.

The [complete previous API guide and historical accounting](https://github.com/robosys-labs/cemm/blob/2336a0bbaedca1840a2ab8e1616ebbdf3e26f82b/experiments/predictive_nucleus/ACTIVE_NUCLEUS.md)
remain immutable. No runtime, frozen protocol, checkpoint or historical result is changed.

## Current implementation and evidence

PR #71 already fitted all fifteen GRU/factor/additive checkpoints and collected
262,080 planned candidate/control/retention records plus 17,280 native references.
The scorer saved a complete summary and REVISE decision, then failed on a missing
`json` import in console output. The original failure receipt remains valid.
A separate standard-library audit reproduces the saved arithmetic with 3,255,288
checks and zero discrepancies, without a fit, collection or original scorer rerun.
This is internal verification, not independent custody or scientific admission.

Fresh exact worlds: GRU 10,912/17,280, factor 11,680/17,280, additive 7,456/17,280.
The factor has 6,240 old lexical regressions and every seed fails the combined
gate, including seeds 7/37 that are exact on the fresh bank. These dependent
pooled counts do not establish improvement over the different earlier 35% bank.
Full probabilities, controls and regression details remain in the recovery report.

`binding_unsaturated.py` adds a 35-line opt-in candidate with the same **89
parameters and initial tensors** as the original factor. Removing only two
terminal tanh operations tests a saturation hypothesis suggested by the saved
weights. It is not fitted, scientifically evaluated, registered in historical
checkpoint/trainer schemas, or enabled in production. No learned success is claimed.

Eighteen new tests pass. Full local suite: 873 discovered, 872 passed, one
full-checkout-only skip; all 29 locks pass. Retained research Python is 38,171
lines; the inclusive 2,000-line objective remains unmet. Historical weights,
code, protocols, data and failed results are unchanged.

## Latest retained G3 evidence

[Lexical v1](LEXICAL_DECISION_V1.md) learned fixed-order direct/inverse lexical
behavior: **41,600/41,600** fresh complete worlds and participant orders,
**5,760/5,760** lexical-pair conjunctions, and **20,800/20,800** exact old-bank
retention. Five warm-start fits completed 1,280 updates; all native worlds stayed
frozen. Masked lexical twins give identical forecasts and 50% accuracy; swapping
words gives **11,520/11,520** correct counterpart worlds.

Structural reuse is still the concrete gap: seen word-layout combinations score
**5,760/5,760**, but held-out combinations score **2,016/5,760 (35%)**, with
**576/2,880 (20%)** both-correct lexical pairs. Every wrong held-out world uses the
opposite participant order. This localizes the observed failure to text binding,
not to acquired world capacity, and does not prove the GRU cannot solve it.

Zero exact retention regressions coexist with worse NLL on **all 20,800** old-bank
predictions: mean +0.0006803064 nats, maximum +0.0020646568. All 41,600 fresh NLLs
also exceed the gold-action native reference. These losses and all failed
structural checks remain retained, not replaced by implementation tests.

Lexical source/data freeze: `7645485bd75c80051a480d6b24aa459a1c8c0d48`.
Lexical checkpoint freeze: `12adb6bdb0361a37d36bb2d8a1ddf16cbe225592`.
Acquired-world checkpoint freeze: `25ae19b317c5b7dbfc487fa5204fb5da5f0e7420`.

## Preserved decisions and bounded capabilities

| Study | Retained decision and scope |
|---|---|
| [Continuation v1](CONTINUATION_DECISION_V1.md) | STOP_INCOMPLETE_RUN |
| [Alias evidence v1](ALIAS_EVIDENCE_DECISION_V1.md) | REVISE_EVIDENCE_FIX |
| [Alias evidence v2](ALIAS_EVIDENCE_DECISION_V2.md) | KEEP_EVIDENCE_FIX |
| [Mixed composition](G1_G2_PROGRESS_REVIEW.md) | KEEP_MIXED_COMPOSITION |
| [Joint correlation](JOINT_CORRELATION_DECISION_V1.md) | KEEP_JOINT_CORRELATION; unconditional-factorization control, not all conditional marginals |
| [NAND/NOR laws](MULTISOURCE_LAW_DECISION_V1.md) | KEEP_MULTISOURCE_LAWS; separately learned laws, full-feedback composition |
| [Hidden cycle](HIDDEN_CYCLE_DECISION_V1.md) | KEEP_HIDDEN_CYCLE; one hidden intermediate, not general open-loop rollout |
| [Explicit timing](TIMING_DECISION_V1.md) | KEEP_TIMING; common-snapshot merger is supplied scheduling semantics |
| [Bilingual binding](BILINGUAL_DECISION_V1.md) | KEEP_BILINGUAL_GROUNDING; supplied identity/contact alternatives |
| [Lexical direction](LEXICAL_DECISION_V1.md) | KEEP_LEXICAL_GROUNDING; structural transfer NOT_ESTABLISHED |
| [Structural binding](BINDING_RECOVERY_V1.md) | Recovered REVISE_STRUCTURAL_BINDING; original STOP_INCOMPLETE_EXECUTION preserved |

These are bounded public research results. Independent challenge custody,
matched-consumed-compute architecture superiority and general calibration are
not established. A new implementation does not retroactively admit a gate.

## Runtime and implementation boundaries remain unchanged

The repository-backed `active_participant.py` still reports active-inference-v6
and active-evidence-v2. `active_learning.py` remains active-learning-v1, and
`active_checkpoint.py` retains cemm-active-checkpoint-v1. See [ACCEPTANCE.md](ACCEPTANCE.md)
and the immutable API guide above for native checkpoint/bundle commands, declared
domain, receipt ordering, evidence assessments, source pins and historical CI.

Native observed APIs support 3-6 entities and self-contact under their declared
supplied identity conditioning. Full initial anchors, noiseless visible readings,
64 live paths, 512 candidate expansions and a 128-action transport cap remain.
Missing evidence, unsupported prediction and model-mismatch diagnostics remain
distinct. Supplied joint filtering is not a learned clarification policy.
Checkpoint artifacts restore learned state for fresh episodes, not optimizer or
live-session state. The timing and text adapters do not silently change this API.
Production, AGENTS contracts and external-effect authority remain untouched.

## Exact next action and roadmap

Freeze one paired original-factor versus unsaturated-factor comparison before
another research fit. Keep the same 89-parameter tensors, realized observations,
optimizer/update budget and all five seeds; require a fresh structural challenge,
retention on labeled opened banks, probability quality and exact regressions.
The [recovery handoff](BINDING_RECOVERY_V1.md) specifies the boundary. The opt-in
candidate exists, but this new comparison is not yet frozen, fitted or collected.
Do not rerun the closed PR #71 collection or relabel the original process as passed.

| Stage | Current state / remaining work |
|---|---|
| G1 | Development sufficient for G2; original scientific admission remains open. |
| G2 | Selected bounded composition, hidden propagation and explicit timing complete for development; scientific admission remains open. |
| G3 | Earlier lexical result retained; structural comparison failed. Saved arithmetic audited; equal-parameter saturation ablation implemented, not evaluated. |
| G4 | Held-out goal-directed communication against silent/random/shuffled controls. |
| G5 | Durable learning, useful clarification and retention across episodes. |
| G6 | Grounded corpus transfer beyond retrieval/frequency controls. |
| G7 | Frozen-bank 3x supported utility with precision, retention and cost gates. |
| G8 | Independent reproduction and reviewed integration/rollback. |

Do not reopen completed G1/G2 studies or add a larger workspace to avoid the G3
binding question. Tests establish software invariants, not new scientific scores.
