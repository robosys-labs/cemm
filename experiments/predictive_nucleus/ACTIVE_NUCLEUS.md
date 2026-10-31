# Active nucleus: G3 binding comparison implemented; transfer still open

Tracking: [#22](https://github.com/robosys-labs/cemm/issues/22).
Latest completed scientific study: [PR #69](https://github.com/robosys-labs/cemm/pull/69),
`2336a0bbaedca1840a2ab8e1616ebbdf3e26f82b`.
Updated 2026-10-31 (Africa/Lagos).

**Current engineering handoff:** [binding implementation](BINDING_IMPLEMENTATION_V1.md).
**Current scientific result:** KEEP_LEXICAL_GROUNDING;
STRUCTURAL_TRANSFER_NOT_ESTABLISHED. G3 remains open.
G1 development readiness remains PROCEED_TO_G2 and G2 development readiness
remains PROCEED_TO_G3. Formal G1 admission is NOT_ADMITTED; formal G2 remains open.

This index replaces the duplicated long status narrative, not its contracts or
history. The [complete previous API guide and historical accounting](https://github.com/robosys-labs/cemm/blob/2336a0bbaedca1840a2ab8e1616ebbdf3e26f82b/experiments/predictive_nucleus/ACTIVE_NUCLEUS.md)
remain immutable. No runtime, protocol, checkpoint or historical result is changed.

## Implemented now, not scientifically evaluated

`binding_model.py` adds an **89-parameter** learned lexical/layout factor model
and a **91-parameter** additive control alongside the unchanged **474-parameter**
GRU. The factor model uses learned scalar content and layout representations with
a learned bilinear interaction. Scalar meanings are not assigned in code.
The low-rank decomposition is supplied architectural bias, not a discovered law.
There is no dictionary dispatch, role-label supervision or handwritten inverse rule.

`binding_training.fit_comparison` gives all three freshly initialized arms the
same observed history, event-weighted outcome objective and update budget through
the existing pack/forecast functions. The acquired world must already be frozen.
It returns in-memory models and explicit exposure/fingerprint/cost records;
it is not a scientific runner, durable journal or new checkpoint format.

Twenty-one synthetic invariants cover the new implementation. This tranche adds
**145 source +245 test =390 Python lines**, for **36,903 retained research Python
lines**. The inclusive 2,000-line objective remains unmet. There are **zero new
research fits or held-out scores**; the ten acquired 562-parameter worlds and
all prior language checkpoints remain unchanged.

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

Freeze the fresh common-history binding comparison before research fitting.
Fresh word-layout holdouts must not be merely a renamed opened failure bank.
Keep original seed coverage, NAND fitting/NOR transfer, mask/swap and additive
controls, coverage/probability denominators and pointwise repair/regression
accounting. Publish new weights before collection; no post-challenge retuning.
Preserve old checkpoints and use their opened banks only for labeled retention.
The [implementation handoff](BINDING_IMPLEMENTATION_V1.md) specifies the remaining
publication/evaluation boundary. No scientific comparison is frozen or run yet.

| Stage | Current state / remaining work |
|---|---|
| G1 | Development sufficient for G2; original scientific admission remains open. |
| G2 | Selected bounded composition, hidden propagation and explicit timing complete for development; scientific admission remains open. |
| G3 | Role and lexical binding retained. Small factor/GRU/additive implementation ready; fresh structural-transfer comparison remains to be frozen and executed. |
| G4 | Held-out goal-directed communication against silent/random/shuffled controls. |
| G5 | Durable learning, useful clarification and retention across episodes. |
| G6 | Grounded corpus transfer beyond retrieval/frequency controls. |
| G7 | Frozen-bank 3x supported utility with precision, retention and cost gates. |
| G8 | Independent reproduction and reviewed integration/rollback. |

Do not reopen completed G1/G2 studies or add a larger workspace to avoid the G3
binding question. Tests establish software invariants, not new scientific scores.
