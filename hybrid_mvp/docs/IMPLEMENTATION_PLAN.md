# Production Evolution Plan

> **Planning status:** This original high-level outline is retained as historical context. The approved authoritative MVP completion design and executable roadmap now live at [`docs/superpowers/specs/2026-07-29-authoritative-mvp-completion-design.md`](superpowers/specs/2026-07-29-authoritative-mvp-completion-design.md) and [`docs/superpowers/plans/2026-07-29-authoritative-mvp-master-roadmap.md`](superpowers/plans/2026-07-29-authoritative-mvp-master-roadmap.md). Those documents govern completion work.

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

- exact `ResponseMeaning` input;
- constrained pointer-aware generation;
- multilingual language packs/models;
- semantic-equivalence verifier;
- deterministic fallback for critical operation and denial messages.

## Phase 9 — Shadow comparison and cutover decision

- run current CEMM and authoritative hybrid on identical episodes;
- compare semantic graph correctness, proof, abstention, latency and effect safety;
- prohibit compatibility paths that recreate parallel authority;
- cut over only after the new runtime exceeds semantic and governance gates.
