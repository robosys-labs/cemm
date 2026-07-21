# CEMM v3.5.1 Mandatory Issues to Avoid

**Status:** anti-regression contract  
**Rule:** architecture quality is not measured by how many checks exist, but by whether invariants are enforced at the narrowest correct boundary without replacing cognition.

---

## 1. Do not turn authority into the brain

Avoid:

```text
input
→ release check
→ stage check
→ schema check
→ use check
→ more checks
```

as dominant computation.

Dominant computation is:

```text
evidence
→ grounding
→ exact semantics
→ recurrent integration
→ belief/query/causal reasoning
→ goals/response
→ learning
```

---

## 2. Do not reverify immutable release facts per request

No normal-request:

- release/source-tree hashing;
- boot DB hashing;
- manifest leaf enumeration;
- adapter source hashing;
- ambient loaded-module legacy scan.

Use immutable `RuntimeAttestation`.

---

## 3. Do not use one global authorization boolean

Keep distinct:

```text
semantic eligibility
epistemic support
permission
competence
transition authorization
operation authorization
disclosure authorization
emission authorization
```

---

## 4. Do not require execute-level permission merely to understand

A concept may be safely:

```text
denoted
composed
queried
compared
reasoned about
```

without being authorized to mutate/execute/disclose/emit.

---

## 5. Do not allow floating executable semantic dependencies

Resolve convenience references to exact pins at activation.

---

## 6. Do not use one store revision for every change

Separate semantic authority, world, discourse, runtime observation, audit and effect history.

---

## 7. Do not recompute whole-store roots for small writes

Use incremental authenticated roots.

---

## 8. Do not hold global locks across semantic computation

Locks protect short persistence/generation-swap boundaries.

---

## 9. Do not probe every RecordKind to discover a ref

Carry typed pins and maintain a ref→kind index.

---

## 10. Do not persist transient cognition by default

Candidate graphs, activation graphs, temporary goals, response candidates, clause plans and local hypotheses live in `CycleWorkspace` unless durability is semantically/effect-required.

---

## 11. Do not let audit/debug writes alter semantic authority

Trace is observational.

---

## 12. Do not use request frequency as a clock

Telemetry refresh and learning promotion are event/schedule/change driven.

---

## 13. Do not make timestamp part of deterministic identity unless occurrence identity requires it

Separate occurrence identity, observed time, valid time and revision.

---

## 14. Do not compare persisted identity with raw Python object equality

Use canonical normalized fingerprints.

---

## 15. Do not make local telemetry conflict fatal to unrelated cognition

Convert to typed uncertainty/frontier unless the requested effect truly requires the signal.

---

## 16. Do not mutate semantic authority mid-pass

Newly promoted authority appears in a new generation/pass.

---

## 17. Do not confuse prediction with mutation

Simulation predicts; commit changes durable state.

---

## 18. Do not confuse grammar with semantic roles

Never encode universal:

```text
subject = actor
object = affected
```

---

## 19. Do not collapse state dimensions

Thermal, physical, affective, capability, epistemic and social state remain distinct.

Cross-dimensional effects require explicit mechanisms.

---

## 20. Do not hardcode named concept/event effects in Python

No:

```python
if action == "push": ...
if state == "hot": mood = ...
```

Use data/CSIR mechanisms.

---

## 21. Do not let storage RecordKind become ontology

Storage specialization is operational.

Semantic identity is CSIR + exact closure.

---

## 22. Do not solve lexical ambiguity with phrase handlers

No phrase authority, English semantic regex brain, or transcript templates.

---

## 23. Do not let internal graph role labels become answer content

Never answer with structural slots such as:

```text
target
holder
possessor
topic
```

unless those words are themselves the semantic answer.

---

## 24. Do not treat generic fallback as success

A fallback must not hide failed grounding, query binding, realization or blocked emission.

---

## 25. Do not treat `errors=[]` as successful completion

Use explicit completion status and frontier effects.

---

## 26. Do not make every frontier fatal

Frontiers may trigger:

```text
partial response
clarification
learning
deferred enrichment
safe no-op
```

---

## 27. Do not let optional enrichment block core grounded meaning

Missing optional biography, causal enrichment, affect estimate or lexical nuance must not block a valid simpler answer.

---

## 28. Do not duplicate semantic verification at every stage

Validate where invariants become relevant.

---

## 29. Do not make Stage 0–22 equal 23 persistence transactions

Use `CycleWorkspace`.

---

## 30. Do not force full round-trip re-analysis for every deterministic reviewed response

Cheap preservation proof is mandatory; independent re-analysis remains required for novelty/risk/audit/release competence.

---

## 31. Do not remove independent verification entirely

Optimization is not verifier bypass.

---

## 32. Do not trust caches without generation ownership

Every cache declares:

```text
dependencies
generation owner
invalidation triggers
cross-cycle safety
```

---

## 33. Do not run unbounded scans in hot stages

Every scan requires bounded cardinality, index, cache or explicit budget.

---

## 34. Do not create record explosions for unchanged observations

Use change-triggered persistence, retention policies and aggregate estimates.

---

## 35. Do not let audit history compete with working semantic indexes

Separate storage/query concerns.

---

## 36. Do not treat confidence as authority

Confidence is epistemic/dynamic strength; authority is governance/definition status.

---

## 37. Do not treat frequency as truth

Repeated dependent claims do not become independent evidence.

---

## 38. Do not call activation score a probability without calibration

---

## 39. Do not let neural dynamics redefine exact semantic identity

---

## 40. Do not reduce the semantic brain to static CRUD and gates

The runtime must genuinely support recurrent activation, inhibition, prediction, state estimation, prediction error and learning.

---

## 41. Do not create two competing brains

One canonical CSIR substrate.

Legacy UOL is migration/shadow only.

---

## 42. Do not hide legacy semantics behind wrappers

A wrapper importing legacy authority is still legacy authority.

---

## 43. Do not weaken tests to achieve activation

No verifier exclusions, dummy adapters, fake authority records, canned acceptance phrases or hidden skips.

---

## 44. Do not sign before behavior is proven

Implementation and competence first; signed artifacts last.

---

## 45. Do not manually patch release hashes

Regenerate deterministically.

---

## 46. Do not use ambient loaded-module history as the only legacy isolation proof

Use static import/release-package verification.

---

## 47. Do not combine migration and runtime fallback

Migration transforms offline/activation-time. Runtime does not lazily read old stores because new semantics failed.

---

## 48. Do not use surface similarity as semantic equivalence

Compare normalized CSIR plus qualifications.

---

## 49. Do not let realization invent missing semantics

---

## 50. Do not let response policy become canned language policy

Response policy chooses semantic actions; realization chooses wording.

---

## 51. Do not let safety policy become hidden ontology

Safety constrains use/effects, not ordinary concept meaning.

---

## 52. Do not reinterpret historical records under new definitions

Historical meaning retains original closure unless explicitly migrated.

---

## 53. Do not ignore performance as correctness

A system that times out, serializes all requests, or spends most cycles hashing authority is not a working semantic brain.

---

## 54. Mandatory per-phase anti-regression checks

```text
0 release hashes during normal request
0 boot hashes during normal request
0 full overlay scans for O(1) write
no raw object equality for persistence identity
no per-request global learning promotion scan
no global lock across semantic solving
no floating executable dependencies
no phrase-specific semantic branch
no RecordKind ontology branch
no hidden legacy fallback
no success when requested response is blocked
no output without emission authorization
no operation without effect authorization
no protected disclosure without permission
```

---

## 55. Review questions for every new gate

1. What exact failure does it prevent?
2. Is the failure semantic, epistemic, privacy, integrity or effect-related?
3. Why is this the narrowest correct boundary?
4. Can the check be compiled once?
5. Can it be cached by generation?
6. What invalidates it?
7. What happens under uncertainty?
8. Does it block unrelated cognition?
9. What is its asymptotic cost?
10. Which test proves the gate is necessary?
