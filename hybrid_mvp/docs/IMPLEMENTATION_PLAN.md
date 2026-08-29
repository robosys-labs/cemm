# Production Evolution Plan

> **Planning status:** This original high-level outline is retained as routing
> context and does not carry execution or admission authority. Current work is
> governed by the [August 29 R4.1 data/supervision amendment](superpowers/specs/2026-08-29-r4-1-data-supervision-corrective-amendment.md),
> the [2026-08-02 semantic-algebra amendment](superpowers/specs/2026-08-02-hybrid-semantic-algebra-corrective-replay-amendment.md),
> and the machine-readable [document authority map](DOCUMENT_AUTHORITY.json).
>
> The reviewed pre-implementation R5/R6 readiness package is:
>
> - [R5/R6 Plan Readiness Review](superpowers/progress/2026-08-22-r5-r6-plan-readiness-review.md)
> - [R5 Neural Activation and R6 Composition Design](superpowers/specs/2026-08-22-r5-neural-activation-r6-composition-design.md)
> - [R5 Neural Activation and R6 Composition Plan](superpowers/plans/2026-08-22-r5-neural-activation-r6-composition-plan.md)
>
> The R5/R6 package remains a conditional target beneath the August 29
> amendment. Its efficiency and anti-bloat contract remains binding, but none
> of its activation tasks can execute before authentic R4.1 admission.
>
> Current replay status and exact admission identities are derived only from
> [`governance/replay_status.jsonl`](../governance/replay_status.jsonl). This
> page does not copy or promote phase status.
>
> R5 training, selection, calibration, frozen evaluation and realization
> activation are unavailable until a fresh R4.1 admission proves meaningful
> purpose-class semantic coverage and independent derivation/realization gold.

## Phase 1 — Evaluation expansion

- expand to the 210-case semantic matrix;
- add naturally written, template-disjoint paraphrases;
- add lexical, relation, event-role and authority-target holdouts;
- add malformed/adversarial abstention benchmarks;
- compare retrieval recall separately from ranking accuracy.

## Phase 2 — Retrieved graph-action decoder

- replace full candidate enumeration with incremental decoding;
- retrieve authority targets at every semantic-selection step;
- apply exact legality masks before each action;
- preserve an explicit abstention/frontier action;
- train from accepted and verifier-rejected programs.

## Phase 3 — Context and state encoder

- encode active session event stack;
- encode participants, focus and obligations;
- encode relevant current state projections and proof summaries;
- predict context-event attachment;
- test multi-turn reference and ellipsis.

## Phase 4 — Rich recursive semantics

- coordination and multiple roots;
- explicit attribution trees;
- polarity, tense, aspect and temporal intervals;
- quantified constraints;
- definitions and reviewed rule proposals;
- correction and contradiction semantics.

## Phase 5 — Scalable stores

- replace in-memory stores with SQLite/PostgreSQL authority/world/session stores;
- immutable episodic columnar shards;
- rebuildable retrieval indexes;
- transactional effect receipts;
- snapshot and rollback support.

## Phase 6 — Real operations

- adapter registry and schemas;
- capability/permission/policy proofs;
- idempotency and retries;
- reversible/irreversible effect declarations;
- compensation and cancellation;
- operation observation assimilation.

## Phase 7 — Native reviewed learning

- designation and entity learning;
- definition graph proposals;
- frame and state-schema induction;
- transition mechanism proposals;
- consolidation with evidence thresholds;
- human or policy review before authority promotion.

## Phase 8 — Neural realization

Historical outline only. The active R5/R6 design requires exact
`ResponseMeaning`, a constrained pointer-aware learned decoder, multilingual
language packs, semantic round-trip verification, and **no normal fallback**.

## Phase 9 — Shadow comparison and cutover decision

- run current CEMM and authoritative hybrid on identical episodes;
- compare semantic graph correctness, proof, abstention, latency and effect safety;
- prohibit compatibility paths that recreate parallel authority;
- cut over only after the new runtime exceeds semantic and governance gates.
