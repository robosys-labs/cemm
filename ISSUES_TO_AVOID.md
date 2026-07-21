# CEMM v3.5.1 — Issues to Avoid

**Status:** mandatory anti-regression guide  
**Audience:** humans and AI implementation agents  
**Purpose:** prevent v3.5.1 from inheriting architectural mistakes from v3.5 while preserving exactness, provenance, safety and deterministic replay.

---

# 1. Governing principle

CEMM must be strict where strictness protects truth, privacy, reproducibility or effects.

CEMM must not be strict merely because a check can be added.

The test for every gate is:

```text
What irreversible or semantically dangerous failure does this gate prevent?
At what narrowest boundary can that failure actually occur?
Can the invariant be compiled/verified once instead of recomputed repeatedly?
Can uncertainty be preserved instead of converted into total denial?
```

---

# 2. Do not turn authority into the semantic brain

Avoid:

```text
input
-> authority check
-> authority check
-> schema authority check
-> use authority check
-> stage authority check
-> output authority check
```

as the dominant computation.

The dominant computation must be:

```text
grounded observation
-> semantic activation
-> compositional settling
-> state estimation
-> causal inference
-> prediction/goal formation
-> response/action
-> learning
```

Authority constrains this process; it does not replace it.

---

# 3. Do not reverify immutable release facts per request

Never perform normal-cycle:

- full boot DB hashing;
- source-tree hashing;
- verification-report hashing;
- full adapter source hashing;
- full service source hashing;
- full manifest leaf enumeration;
- ambient `sys.modules` legacy scanning.

These belong to:

```text
startup
reload
integrity fault
deployment verification
```

Carry a `RuntimeAttestation` generation token in the hot path.

---

# 4. Do not use one global "authority" boolean

Never reduce all of these to one flag:

```text
trusted
active
permitted
competent
supported
true
executable
safe
realisable
emittable
```

They are different predicates.

Use explicit typed state.

---

# 5. Do not equate semantic eligibility with effect authorization

A concept may be safe to:

- denote;
- compose;
- query;
- compare;
- reason about;

while not being authorized to:

- mutate durable state;
- execute an operation;
- disclose protected information;
- emit externally.

Never require "execute-level" governance merely to understand a concept.

---

# 6. Do not default every semantic use to DENY

A learned candidate should not automatically gain broad semantic power.

But once a semantic definition has passed activation for a bounded semantic capability, that capability should be compiled into the authority snapshot.

Do not force every node through per-stage `UseOperation` lookup on every cycle.

---

# 7. Do not put lifecycle, meaning, competence and privacy into one revision identity

Changing:

- confidence;
- competence evidence;
- review status;
- privacy rule;
- activation decision;

must not silently change the semantic meaning hash.

Separate records/axes.

---

# 8. Do not allow floating executable semantic dependencies

No executable closure may depend on:

```text
latest
max revision
current authoritative parent
minimum compatible revision
whatever active package happens to exist
```

Resolve authoring convenience references to exact pins during activation compilation.

---

# 9. Do not cache semantic closure by root ref alone

Cache by:

```text
AuthorityGeneration
+ exact root pin
+ compiler ABI
```

Return exact transitive closure hashes.

---

# 10. Do not treat one store revision as every kind of change

Separate generations for:

- semantic authority;
- language authority;
- world/epistemic state;
- discourse/common ground;
- runtime observations;
- audit/effect history.

An emission journal must not invalidate a type hierarchy cache.

---

# 11. Do not recompute whole-store fingerprints on each write

No O(total history) operation for O(1) new writes.

Use incremental authenticated roots.

---

# 12. Do not hold a global lock across semantic computation

Locks/transactions should protect short persistence operations.

They should not serialize:

- grounding;
- factor solving;
- causal propagation;
- response planning;
- realization.

Use immutable snapshots/generation tokens and connection isolation.

---

# 13. Do not open a snapshot only to calculate another snapshot token

One stage must not:

```text
open snapshot
get fingerprint
close
open snapshot
verify fingerprint
compute
```

Pass the read generation directly.

---

# 14. Do not discover record type by probing every RecordKind

Carry typed pins.

Maintain a ref index.

Avoid `for kind in RecordKind` in hot-path resolution.

---

# 15. Do not perform "latest" lookups by materializing every record of a kind

Use indexed SQL and explicit semantics.

---

# 16. Do not persist transient compiler objects by default

Candidate graphs, factor graphs, temporary clause plans and local hypothesis structures should be cycle-local unless:

- required for durable evidence;
- required for replay;
- explicitly traced.

Persistence is not proof of correctness.

---

# 17. Do not let debug/audit writes alter semantic authority generation

Trace data is observational.

It is not meaning authority.

---

# 18. Do not use request frequency as a clock for runtime truth

A runtime health signal should not become "new truth" merely because another chat message arrived.

Observe on:

- state change;
- provider poll policy;
- explicit freshness requirement;
- runtime generation change.

---

# 19. Do not make wall-clock timestamp part of deterministic identity unless occurrence identity truly depends on it

Separate:

```text
event identity
observation identity
observed_at
valid time
record revision
```

Timestamp-as-identity often destroys idempotency.

---

# 20. Do not compare persisted records with raw Python object equality

Persistence identity is canonical.

Use canonical fingerprints.

Nested tuple/list normalization must not cause false collisions.

---

# 21. Do not make local telemetry conflicts fatal to all cognition

A runtime sensor conflict should become:

```text
conflicted observation
unknown capability
typed frontier
```

unless the missing observation is itself required to safely perform the requested effect.

---

# 22. Do not run learning promotion scans on every unrelated request

Promotion is event-driven.

Cognition should consume a stable authority generation.

---

# 23. Do not mutate semantic authority mid-pass

A pass sees one exact `AuthoritySnapshot`.

Newly learned/promoted authority becomes visible in a new pass/generation.

---

# 24. Do not confuse prediction with state mutation

A causal mechanism may predict:

```text
push -> probable displacement
```

It does not mutate the world until an admitted/observed transition is committed.

---

# 25. Do not confuse action grammar with semantic roles

Never encode:

```text
subject = actor
object = affected
```

as a universal law.

Language projections map grammatical evidence to semantic roles.

Effects target bound semantic roles.

---

# 26. Do not convert physical dimensions into affective dimensions by renaming

Temperature does not "become emotion."

Use causal mechanisms:

```text
temperature
-> physiological/homeostatic impact
-> comfort/stress
-> affective consequence
```

only for entities whose type/facets permit those dimensions.

---

# 27. Do not hardcode concept-specific causal effects in Python

No:

```python
if action == "push": ...
if state == "hot": mood = ...
```

Use versioned causal/transition definitions compiled to the semantic dynamics substrate.

---

# 28. Do not let RecordKind become ontology

Storage specialization is operational.

Semantic identity is CSIR + exact definition closure.

---

# 29. Do not solve lexical ambiguity with phrase handlers

No phrase authority.

No English semantic regex brain.

No domain sentence templates masquerading as cognition.

Language-specific structures provide evidence/projections into shared semantic algebra.

---

# 30. Do not let internal role labels become answer content

Never surface:

```text
target
possessor
topic
holder
user
```

merely because they are graph roles.

Answer generation projects semantic values/referents, not structural slot names.

---

# 31. Do not treat a generic fallback as success

A fallback must not hide:

- failed grounding;
- disconnected query binding;
- failed realization;
- blocked emission;
- missing semantic closure.

Final result reports the true failure class.

---

# 32. Do not report `errors=[]` as successful completion

The cycle requires explicit completion status.

Frontiers can be non-errors but still prevent a requested response.

---

# 33. Do not make every frontier a fatal block

Frontiers are first-class uncertainty/missing-knowledge structures.

They can trigger:

- partial response;
- clarification;
- learning;
- deferred enrichment;
- safe no-op.

---

# 34. Do not let unresolved optional enrichment block grounded core meaning

Core meaning should survive missing:

- optional biography;
- optional causal enrichment;
- optional affect estimate;
- optional lexical nuance.

Preserve partial cognition.

---

# 35. Do not duplicate semantic verification at every stage

Validate invariants at the boundary where they become relevant.

Examples:

- schema closure at activation compile;
- type/port validity when graph edge is proposed;
- evidence admissibility when belief is updated;
- permission when data is read/disclosed;
- effect authorization before effect;
- semantic preservation before emission.

---

# 36. Do not make Stage 0–22 imply 23 persistence boundaries

Stages are logical transitions.

They can share one in-memory working context.

Persist only when semantics/effects require durability.

---

# 37. Do not force full re-analysis of every deterministic response when proof-carrying realization is sufficient

Maintain full independent round-trip as:

- competence test;
- high-risk runtime check;
- novelty check;
- audit sample;
- fallback verifier.

For ordinary deterministic reviewed realization, verify transformation proof cheaply.

---

# 38. Do not remove independent verification entirely

Optimization must not become verifier bypass.

Every optimization requires an equivalent or stronger invariant.

---

# 39. Do not trust cache correctness without generation ownership

Every cache declares:

```text
which authority/state generation it depends on
what invalidates it
whether it is safe across cycles
```

---

# 40. Do not let one unrelated write flush every cache

Use dependency-domain invalidation.

---

# 41. Do not use unbounded scans in Stage 0–22

Every hot-path scan needs:

```text
bounded cardinality
index
cache
or explicit budget
```

---

# 42. Do not create record explosion for repetitive evidence

Use:

- occurrence streams;
- bounded retention;
- aggregate state estimates;
- change-triggered persistence.

Do not create a full semantic evidence tree for every unchanged health poll.

---

# 43. Do not let audit history compete with working memory

Separate audit storage/query from hot semantic state indexes.

---

# 44. Do not let common-ground history redefine current semantic definitions

Discourse changes context, not ontology.

---

# 45. Do not treat confidence as authority

Confidence is epistemic strength.

Authority is definition/governance status.

---

# 46. Do not treat frequency as truth

Repeated claims are not independent evidence unless lineage supports independence.

---

# 47. Do not treat activation score as probability unless calibrated

Neural/recurrent semantic dynamics may use activations.

Expose probabilities only after calibration.

---

# 48. Do not let continuous neural dynamics redefine exact semantic identity

Continuous dynamics selects/activates/weights CSIR structures.

Exact CSIR/definition authority defines meaning identity.

---

# 49. Do not make exact semantics prevent neural-like computation

The opposite failure is also possible.

Do not reduce v3.5.1 to static graph CRUD plus gates.

The runtime must support:

- recurrent activation;
- competition;
- top-down prediction;
- bottom-up evidence;
- state estimation;
- causal propagation;
- prediction error;
- recursive learning.

---

# 50. Do not create two competing brains

Avoid:

```text
legacy UOL brain
+
CSIR brain
+
neural semantic brain
```

with winner selection.

Use one canonical semantic substrate.

Compatibility compiles into it and is deleted after migration.

---

# 51. Do not hide legacy semantics behind wrappers

A wrapper that imports legacy authority is still legacy authority.

---

# 52. Do not weaken tests to achieve activation

No verifier exclusions.

No dummy adapters.

No fake authority records.

No hardcoded acceptance phrases.

---

# 53. Do not sign artifacts before behavior is proven

Correct order:

```text
implementation
-> behavioral tests
-> competence tests
-> performance tests
-> boot build
-> authority roots
-> verification report
-> signed release manifest
```

---

# 54. Do not manually patch release hashes

All signed artifacts are deterministically regenerated.

---

# 55. Do not hardcode release version checks into reusable guard logic

Guard compares:

```text
runtime declared version
manifest declared version
supported manifest ABI
```

Do not embed `"3.5.0"` as permanent control flow in code intended to support `3.5.1`.

---

# 56. Do not use loaded-module history as the only legacy isolation proof

Use static import-graph and release-package verification.

Runtime ambient process state is supplementary evidence only.

---

# 57. Do not combine migration and runtime authority

Migration is offline transformation.

Runtime must not lazily read old stores when new meaning fails.

---

# 58. Do not use whole-sentence output equivalence as semantic equivalence

Semantic equivalence compares canonical semantic structures and qualifications.

Surface similarity is insufficient.

---

# 59. Do not let realization invent missing semantics

The realizer cannot fill:

- unknown participants;
- unsupported emotions;
- causal claims;
- certainty;
- relationships;
- completed operations.

---

# 60. Do not let response policy become canned language policy

Response policy chooses semantic response goals/acts.

Language realization remains separate.

---

# 61. Do not let safety policy become hidden ontology

Safety/permission rules constrain use/effect.

They do not define what ordinary domain concepts mean.

---

# 62. Do not silently reinterpret historical records under new semantic closure

Historical meaning uses original exact authority closure.

Migration/equivalence must be explicit.

---

# 63. Do not ignore performance as a semantic correctness property

A semantic brain that times out, serializes all requests or spends most cycles hashing manifests is functionally incorrect.

Performance budgets are architecture acceptance criteria.

---

# 64. Mandatory anti-regression checks

Every v3.5.1 implementation phase must verify:

```text
0 release-file hashes during normal request
0 full boot DB hashes during normal request
0 full overlay scans for O(1) write
no raw object equality for persistence identity
no per-request learning promotion full scan
no global lock held across semantic solving
no floating executable semantic dependencies
no phrase-specific semantic branch
no RecordKind-based ontology branch
no hidden legacy semantic fallback
no response success when critical frontier blocks requested response
no output without effect/emission authorization
no operation execution without authorization
no privacy disclosure without scope permission
```

---

# 65. Review question for every new "authority" mechanism

Before adding a new authority record, gate or check, the implementation review must answer:

1. What exact failure does it prevent?
2. Is that failure semantic, epistemic, privacy, integrity or effect-related?
3. Why is the check placed at this boundary?
4. Can it be compiled once?
5. Can it be cached by generation?
6. What changes invalidate it?
7. What happens under uncertainty?
8. Does it block unrelated cognition?
9. What is its asymptotic cost?
10. What test proves removing/relocating it would be unsafe?

If these questions cannot be answered, do not add the gate.
