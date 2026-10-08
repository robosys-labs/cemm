# CEMM repository authority (foundation recovery)

The only installable CEMM runtime is `cemm_authoritative_hybrid` under
`hybrid_mvp/src/`. The previous Stage 0-22 `cemm/` implementation is
retired from this branch and preserved at
`archive/cemm-pre-foundation-20261008` (commit `24d8b68`).

## One cognitive owner

The canonical execution architecture is:
ORIENT -> PROPOSE -> VERIFY -> EVALUATE -> EFFECT -> REALIZE.
Each phase has one typed interface; training and presentation own no truth.
`HybridRuntime` is the sole interpreter/decision/effect owner.
`FoundationRuntime` is a lossless semantic-output adapter, not a second brain.

Semantic identity is independent of the proposal program. Verified meaning
must preserve grounding, source coverage, scope, proof and revision identity.
Only EFFECT may mutate durable world state or invoke authorized adapters.
Unknown inputs must not mint atoms or become successful claims.

## Admission boundaries

The current reference foundation admits canonical, round-trippable structured
ResponseMeaning output. It DOES NOT admit neural release, open-ended learned
language generation, or template/keyword equivalence checks. Historical
R4 green receipts do not activate R4.1, R5, R6 or the root release.

Do not reintroduce the 23-stage interpreter, retired bootstrap-training
shortcuts, old natural-language template realizer, or arbitrary fallback
meaning paths. Fail closed rather than passing unsupported semantics.

Tests must verify real public-path execution, independent semantic identities,
effect/no-effect receipts, persistence across process restarts, and inability
to turn an unknown surface into fabricated knowledge. A passing hash or
governance ledger is never a substitute for cognitive correctness.

The more detailed `hybrid_mvp/AGENTS.md` governs its internal phase contracts
where it does not conflict with this repository-wide cutover.
