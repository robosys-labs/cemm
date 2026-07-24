# CEMM v3.5 Phase 11 hardening review before Phase 12

**Reviewed base:** Phase 11 implementation on remote commit `735d13d11f112d0062972a9a66d59100fa8a406c`
**Purpose:** remove latent transition-authority bypasses before using Phase 12 as architectural proof.

## Findings fixed

1. **State-condition revision precision** — condition lookup now pins the exact state-dimension revision and compares exact state-value revisions.
2. **Temporal condition correctness** — state conditions evaluate the timeline at the event effective time; future assignments cannot satisfy earlier events and ended intervals cannot leak forward.
3. **Unresolved semantic time** — unresolved/non-ISO time now blocks at preview with an explicit frontier instead of surviving until timeline mutation.
4. **Retroactive mutation** — an event earlier than an already-advanced timeline boundary requires replay/invalidation; the engine will not rewrite history in place.
5. **Occurrence-status safety** — attempted occurrences join failed/prevented/non-occurring/hypothetical/etc. as non-transitioning success triggers.
6. **Exact proof pins** — transition proofs now pin the exact stored event revision and exact participant-application revision in addition to contract/admission/pre-state pins.
7. **Runtime coreference collisions** — distinct holder ports that resolve to the same holder/dimension cannot silently emit duplicate effects.
8. **Competing transition contracts** — multiple simultaneously authorized contracts produce an explicit composition frontier; list order is not authority.
9. **Competing capability dependencies** — multiple dependencies targeting one holder/action/context produce an explicit frontier unless composition semantics exist.
10. **Snapshot freshness** — commit checks the plan's exact store revision and boot/overlay fingerprints before canonical recomputation; stale plans fail explicitly.
11. **Canonical recomputation** — caller-supplied projections must equal canonical recomputation at the pinned store state.
12. **Transition-derived state completeness** — durable validation requires proof-linked target materialization and required immutable termination of pinned pre-state; omitting either side of the timeline update is rejected.
13. **Delta/proof exactness** — event-triggered deltas must be enumerated by the durable proof and match trigger/context/time and reviewed contract effects.
14. **Capability-delta recomputation** — commit validation recomputes dependency status from post-state and validates exact prior status from pre-transition capability state.
15. **Direct GraphPatch ambiguity bypass** — duplicate capability-dependency deltas for the same proof/holder/action/time are rejected even when submitted directly.
16. **Context-specific capability precedence** — exact-context capability state outranks global fallback instead of arbitrary max-revision selection.
17. **Proof identity strength** — proof/delta identities derive from exact event/application/contract/admission/pre-state/time/effect inputs rather than weak semantic labels.
18. **Derived confidence** — capability projections derive confidence from proof/state lineage rather than hard-coded `1.0`.
19. **State-effect contract consistency** — terminate/deactivate effects cannot carry ignored target values; increase/decrease require an explicit target because Phase 11 does not invent arithmetic semantics.

## Deliberate non-fixes / later boundaries

- Relation/role lifecycle effects remain blocked until first-class generic relation/role delta records exist.
- Phase 11 still does not infer arithmetic from magnitude strings or quantities; explicit target semantics are required.
- Phase 12 competence packages are verification-only and are not promoted into canonical source.
- Correction-driven replay/invalidation of already committed transition chains belongs to the learning/invalidation architecture and must remain explicit rather than destructive historical rewrites.
