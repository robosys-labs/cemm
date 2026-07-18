# CEMM v3.5 Phase 11 — Generic event transition engine

**Base:** `60b2fe7026fe1e6204b1dc682977de93c13e515e` (`Phase 9-10 patch`)
**Status:** implemented and phase-verified; not public-runtime-authoritative
**Authority:** revisioned reviewed transition/dependency records plus proof-bearing runtime records

## 1. Boundary

Phase 11 implements generic event-to-state transition machinery. It deliberately does not implement a named domain event.

The architectural law is:

> Python knows how to compile, validate, preview, prove, project, and atomically commit a transition contract. Python does not know what a named event is supposed to do.

The canonical reviewed source therefore seeds **zero** domain `TransitionContractRecord` and **zero** domain `CapabilityDependencyRecord` records. Synthetic competence fixtures exercise the engine without turning examples into boot ontology.

## 2. Record authorities

### `TransitionContractRecord`

Pins an exact trigger `EventSchema` revision and declares:

- explicit state preconditions;
- event-port to holder binding;
- exact state-dimension revision;
- exact state-value revisions;
- explicit change operation;
- reviewed evidence and lifecycle.

Active contracts require evidence. Contract activation is bidirectionally linked to the exact transition-authorized event/state schema authority.

### `CapabilityDependencyRecord`

Separately describes how a holder's current state affects a particular action capability. Event contracts do not directly mutate named capabilities.

### `TransitionProofRecord`

A durable proof pins:

- event occurrence;
- transition-contract revision;
- exact epistemic-admission revisions;
- exact pre-transition state-assignment revisions;
- condition evidence;
- exact derived delta references;
- context/effective time;
- evidence/confidence.

Later revision changes cannot retroactively alter why an earlier transition was authorized.

## 3. Runtime pipeline

```text
TransitionContractCompiler
  -> EventAdmissionGate
  -> TransitionPreviewEngine
  -> StateDeltaValidator
  -> StateTimelineProjector
  -> CapabilityDependencyEngine
  -> EffectCommitCoordinator
  -> TransitionCoordinator
```

### Compilation

The compiler validates exact schema revisions and transition-use authorization. It rejects broken event ports, holder constraints, state domains, and unlinked transition authority.

### Admission

An event is not transitionable because it was parsed, mentioned, claimed, reported, or stored.

Transition requires independent active Phase-10 epistemic support admission. When attributed content is admitted to another context, the gate verifies exact meaning-bearing application structure across the explicit context bridge rather than relying on record identity or metadata.

Negative proposition content cannot authorize the positive event transition.

### Preview

Preview is cycle/snapshot-local and non-mutating. Non-transitioning occurrence states are blocked. Missing bindings/conditions become explicit frontiers.

No event-specific branch exists.

### State timeline

State changes are immutable assignment revisions/intervals. Exact dimension/value domains and ordering come from reviewed schemas.

An unresolved semantic time reference is not guessed from its string. Timeline mutation requires an explicit concrete ISO-8601 effective timestamp after generic time resolution.

### Capabilities

Post-state capability changes are separately derived from reviewed capability dependencies. Function remains distinct from capability.

### Atomic commit

The effect coordinator creates one CAS `GraphPatch` carrying proof, state deltas, immutable timeline revisions, capability deltas, and capability instances.

Planning pins:

- store revision;
- boot fingerprint;
- overlay fingerprint.

Any intervening write makes the plan stale. Commit validation reconstructs the pre-transition condition state from the proof's exact revision pins and rejects forged or mismatched effects.

## 4. Storage

Normalized storage schema advances to version 4 and adds first-class tables/repositories/codecs for:

- transition contracts;
- capability dependencies;
- transition proofs.

These participate in the same deterministic boot/overlay/CAS authority as earlier semantic records.

## 5. Deliberate non-features

Phase 11 does not fake later genericity:

- no named domain transition seed;
- no named event mutation helper;
- no causal inference from temporal sequence;
- no impact/importance encoding inside transition effects;
- no relation/role mutation until first-class generic relation/role lifecycle/delta records exist;
- no runtime cutover.

## 6. Safety checks

The implementation verifies:

- exact trigger schema revision;
- exact state schema/value revisions;
- transition use authorization;
- independent active support admission;
- explicit attributed→target context bridge;
- negative and non-transitioning occurrence blocking;
- required participant bindings;
- state preconditions;
- type/holder compatibility;
- ordered scalar direction;
- exact admission/pre-state revision pins;
- exact contract-effect reproduction at commit;
- stale snapshot rejection;
- atomic state/capability commit;
- no named semantic refs in transition kernel;
- zero canonical domain transition seed.

## 7. Phase-12 handoff

Phase 12 is not a request to add one privileged event. It is a cross-domain/adversarial proof that multiple independently reviewed packages can traverse Phases 2–11 through the same kernel with no new semantic branch.

See `docs/implementation/v350-phase-12-plan.md` and the replacement root `IMPLEMENTATION_PLAN.md`.
