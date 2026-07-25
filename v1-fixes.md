# CEMM v1 Fix Plan — Final Completion Record

This document is the dependency-ordered repair record for the frozen-MVP-derived v1. The final implementation removes compatibility paths rather than preserving behavior that conflicts with the architecture.

## Governing invariants

1. One exact semantic substrate; no neural shadow ontology.
2. Five fixed operator shapes.
3. Participant identity comes from ParticipantFrame.
4. Parsing/interpretation is side-effect-free.
5. State dimensions are recursively entitled, never type-specific schemas.
6. Identity, type, relation, state, event, evidence, and epistemic placement remain distinct.
7. Queries are variable/projection structures and do not mutate the queried world.
8. Directives are desired content, not assertions or automatic effects.
9. Causal transitions are role-addressed promoted graph rules.
10. Runtime self capability is non-lexical.
11. Stage 13 is the first ordinary world-write boundary.
12. Normal cognition is sparse, bounded, revision-pinned, and auditable.

## Phase completion

### Phases 1–4 — grounding and state foundations

- SessionContext, ParticipantFrame, CycleState, SelfRuntimeView.
- Pure unknown-form evidence and no parser writes.
- Recursive type/facet entitlement.
- Native-domain state timelines and exact dimension/value validation.

### Phases 5–9 — cognition and epistemics

- Removed global SessionSelf semantic state.
- First-class state dimensions and query variables.
- QueryStructure, QueryResult, bindings, proofs, coverage.
- Explicit discourse forces independent of runtime mode.
- Claim occurrence and epistemic admission separation.

### Phase 10 — transition learning/runtime

Implemented:

- causal rules indexed as generic mechanisms;
- named-role antecedent matching;
- exact precondition proof refs;
- StateDelta and TransitionPreview;
- secondary-event support;
- prediction-confirmed/mismatch/unobserved artifacts;
- no predicted state commit;
- no event-specific executor classes.

### Phase 11 — canonical runtime ordering

Implemented:

- strict Stage 0–22 trace;
- split `observe()` and `compose()` interpreter boundary;
- Stage-4 projection before final composition;
- no early return for unresolved meaning;
- typed workspace artifacts;
- durable-write ownership enforcement.

### Phase 12 — non-lexical self operational profile

Implemented:

- digital-agent type/facet profile;
- capability/resource dependency graph;
- cycle-local runtime providers;
- ephemeral self runtime state facts for exact queries;
- recursive capability assessment;
- removal of self ready/processing/confused semantic dimensions.

### Phase 13 — target-aware Response CSIR

Implemented:

- response actions derived from actual query/frontier/capability/operation target;
- evidence and number placeholders;
- deterministic semantic-ref placeholder ordering;
- learned response examples inside the single pinned language pack;
- provenance, grammar, and leak verification;
- no outcome→response policy graph.

### Phase 14 — unified normal conversation

Implemented:

- `normal`, `read_only`, and `reviewed_teach` only;
- modes control writes, never force;
- removed Ask/Learn/Teach semantic split;
- web and CLI aligned to the same runtime.

### Phase 15 — structural curriculum

Implemented:

- PRE/INPUT/TARGET SemanticEpisode;
- mandatory stable CSIR, discourse act, placement, transition/NO_TRANSITION, Response CSIR;
- family-level train/holdout separation;
- required contrast families;
- response examples compiled into language authority;
- output supervision remains attached to original Response CSIR/frame.

### Phase 16 — performance and anti-bloat

Implemented:

- indexed active-fact retrieval;
- relevant-rule index and bounded backward expansion;
- explicit sparse closure seeds;
- incremental generation hashes and commit receipts;
- independent world/discourse/observation/effect revisions;
- CAS at Stage 13 and Stage 21;
- lazy salience decay;
- bounded runtime-owned model cache;
- bounded hard workspace requirements;
- idempotent effect journal;
- pre-final schema rejection;
- removal of language sidecars, generated patch artifacts, bare-query and dimension inference shims.

## Bugs found during final audit

- Runtime commits performed whole-store snapshot hashing.
- Query execution materialized every fact before matching.
- Indexed pattern SQL parameter order was incorrect but hidden by salience retrieval.
- Runtime-provider derived facts were misread as rule-derived proofs.
- Grammar verification treated trailing punctuation as part of a word token.
- Rule promotion indexed an undefined variable instead of the promoted rule ref.
- Reviewed teaching marked a durable Stage-13 write even when induction returned a frontier.
- Repeated effect-journal requests incremented revisions despite terminal idempotent results.
- QueryStructure and discourse-act builders still contained implicit compatibility normalization.
- The compiler still inferred a dimension from a value, hiding missing semantic structure.
- `AutonomousAcquirer` still created unknown identities and defaulted untyped forms to `concept`.
- Reviewed acquisition rebuilt the entire designation index instead of indexing the inserted designation.
- Generic concept predication remained encoded as `op:type(concept, concept)`, confusing class-level subtype meaning with instance membership.
- Language supervision had no exact reviewed-constant pointer for structural relations such as `rel:subtype_of`.

Each defect is covered by final acceptance tests or a static forbidden-pattern gate.

## Removed artifacts

- `cemm/selfstate.py`;
- `*.v1.json` language-pack sidecars;
- old self-state atoms/control symbols/facts;
- old response goal/value policy graph;
- legacy PLAN realization examples;
- generated Phase 5–9 patch/report files committed as repository source;
- old runtime `learn=` / `teach=` entry point;
- `autonomous_acquisition` runtime flag and `AutonomousAcquirer`;
- `USER` / `SYSTEM` source aliases;
- bare-application queries;
- value→dimension completion;
- concept-as-instance generic predication;
- parser-triggered acquisition and default semantic-kind creation.

## Final exit criteria

The v1 implementation is accepted when `V1_ACCEPTANCE.md` gates pass on a clean database rebuilt from final authority, and the runtime demonstrates:

- exact participant reversal;
- partial meaning without self corruption;
- state entitlement and native-domain projection;
- proof-bearing variable queries;
- claim/query/directive separation;
- role-addressed transition preview;
- non-lexical digital-self capability;
- Stage 0–22 ordering and write ownership;
- sparse retrieval and incremental commit behavior;
- target-aware verified response;
- zero-write read-only cognition;
- no forbidden compatibility artifacts.
