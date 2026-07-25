> **ARCHIVED — historical evidence only.**
> This file is not active implementation authority. See root `AGENTS.md`,
> `ARCHITECTURE.md`, `runtime-core-loop.md`, `CURRENT_RUNTIME_WEAKNESSES.md`,
> and `V1_ACCEPTANCE.md`.

# CEMM v1 — Phases 10–16 Final Implementation

## Scope

This patch completes the final v1 runtime architecture after the Phase 1–9 grounding, state, query, force, and epistemic repairs. It intentionally removes compatibility paths that could preserve the old MVP’s semantic shortcuts.

The implementation target is not broad language coverage. It is a coherent, efficient semantic runtime whose learned language artifacts can scale without reopening the five-operator kernel.

## Audit findings corrected

1. Normal commits computed a whole-store snapshot hash.
2. Query reasoning materialized the whole active fact store before matching.
3. Runtime returned from multiple middle stages instead of completing Stage 0–22.
4. State-space projection occurred after semantic candidates had already settled.
5. Directives could be interpreted but had no generic semantic route to an operation adapter.
6. Causal consequents with existential events could not produce deterministic preview witnesses.
7. Workspace hard-required slots were not separately bounded.
8. Compiler still inferred discourse force when a candidate omitted it.
9. Old self/outcome policy atoms and response-plan supervision remained in canonical authority.
10. Generated patch/report files had become repository content.
11. Autonomous acquisition still mutated the store and defaulted unknown forms to `concept`.
12. Reviewed lexical acquisition rebuilt the complete designation index per publication.
13. Generic concept statements were still trained as instance typing.
14. Structural relations that are not surface mentions lacked reviewed pack-local constant pointers.

## Phase 10 — causal transition runtime

Causal mechanisms remain ordinary promoted `rule_kind="causal"` graph artifacts.

A mechanism contains:

- event/action role restrictions;
- state/domain preconditions;
- optional defeaters represented by ordinary restrictions;
- state deltas;
- secondary events;
- confidence and proof lineage.

`TransitionEngine` binds semantic roles by role name, never argument position. It creates a `TransitionPreview` but does not commit predictions. Consequent existential witnesses are deterministic preview refs derived from mechanism, evidence parents, and existential variable.

Queries do not generate transitions. A plain state claim does not become a causal transition unless a promoted causal mechanism matches its semantic trigger.

## Phase 11 — canonical Stage 0–22 runtime

`Runtime.process()` executes one ordered cycle:

0. Orient
1. Observe
2. Encode
3. Ground
4. Project entitled state
5. Compile exact candidates
6. Recurrent dynamics
7. Stabilize/partial meaning
8. Build claim/query/directive structures
9. Place epistemically
10. Query/explain
11. Compare prediction and observation
12. Preview transitions
13. Commit authorized semantic/discourse evidence
14. Assess capability and impact
15. Arbitrate goals
16. Plan/authorize/execute operation
17. Assimilate operation evidence
18. Build Response CSIR
19. Realize
20. Verify
21. Commit common ground
22. Finalize

Stages are logical boundaries grouped inside one efficient process. `StageTrace` rejects order regressions and illegal side-effect ownership.

## Phase 12 — non-lexical digital-self capability

Digital self competence is represented by one recursively inherited operational profile:

- `concept:digital_agent`;
- entitled runtime dimensions;
- entitled capabilities;
- entitled resources;
- recursive `rel:depends_on` edges.

Runtime providers expose ephemeral numeric semantic facts for the active cycle. The system can therefore answer a broad self-condition query without a stored `value:ready` or a phrase handler.

Raw state domains remain native. Only capability assessment normalizes dependency support to a score.

## Phase 13 — Response CSIR

Responses are built from the actual target and proof context:

- query bindings and proof facts;
- conflict or contradiction;
- target-scoped uncertainty;
- exact frontier evidence;
- capability assessment;
- epistemic placement;
- operation result.

`ResponseCSIR` is realized through reviewed response examples and typed placeholders for semantic atoms, evidence literals, and numbers. Pointer assignment is deterministic and independent of dictionary insertion order.

## Phase 14 — unified conversation

The normal runtime modes are:

- `normal` — complete cognition with policy-authorized durable writes;
- `read_only` — complete cognition with no durable writes;
- `reviewed_teach` — explicit reviewed rule teaching.

These modes do not alter discourse force. There is no Ask/Learn/Teach semantic split and no punctuation rewrite.

Unknown forms create scoped frontiers. Partial meaning can continue through query, goal, and response stages when the known part remains sufficient.

## Phase 15 — structural semantic episodes

Training contracts use:

- PRE state/context;
- input evidence and ParticipantFrame;
- stable CSIR target;
- discourse act;
- epistemic placement;
- transition delta or explicit `NO_TRANSITION`;
- Response CSIR.

`CurriculumManifest` requires family-level held-out splits and explicit no-transition supervision. This prevents paraphrases of the same semantic family leaking between train and evaluation sets.

## Phase 16 — performance and anti-bloat

### Sparse cognition

Normal query/transition reasoning starts from indexed application patterns, grounded refs, and relevant causal/rule consequents. It expands backward under fact/rule/depth budgets.

The normal runtime never calls full `base_facts()` or `snapshot_hash()`.

### Incremental commits

Stage 13 commits use:

- pinned expected world revision;
- compare-and-swap validation;
- generation-local payload hashing;
- compact commit receipts;
- independent world, observation, discourse, and effect revisions.

Full snapshot hashing remains an explicit audit command.

### Bounded caches/workspace

- Runtime owns the bounded neural model cache.
- State-entitlement closure uses a bounded generation-keyed cache.
- Workspace TOP-K and hard-required slots are separately bounded.
- Operation re-entry is capped.
- Effect execution is idempotent through the effect journal.

## Semantic operation authorization

An effect requires all of:

1. a grounded directive;
2. reviewed authority linking its event/action/dimension to an adapter through `rel:handled_by_adapter`;
3. an adapter registered by the embedding application;
4. active permission scope;
5. a selected unblocked goal;
6. an idempotency key and effect journal.

Missing any requirement produces a decline, not a dummy success.

## Authority migration

The deterministic migration:

- removes global self `ready/processing/confused` dimensions and controls;
- removes outcome-to-response policy graphs;
- removes value-to-dimension inference controls;
- removes runtime language-pack sidecars;
- removes legacy PLAN response examples;
- seeds the generic digital-agent operational profile;
- seeds the generic semantic adapter relation;
- compiles final Response CSIR examples into each language pack;
- rewrites concept-level generic predication to `rel:subtype_of`;
- adds deterministic pack-local `CONST*` pointers for reviewed authority constants;
- verifies those constants against the pinned authority generation;
- re-hashes each immutable language artifact.

Populated pre-final SQLite databases are intentionally rejected. Rebuild them from canonical authority/world evidence rather than preserving a silently incompatible schema.

## Reviewed lexical acquisition boundary

Final v1 has no autonomous parser-side acquisition. Unknown evidence opens a typed frontier. A separate reviewed workflow requires an explicit kind for every new identity, publishes its designation at Stage 13 with an incremental commit receipt, updates only that designation-index row, reloads the authority pin, and then invokes the ordinary runtime. ABI/state-space kinds such as `operator`, `role`, and `state_dimension` cannot be created through lexical mention acquisition.

## Acceptance authority

The final acceptance source is:

- `V1_ACCEPTANCE.md`;
- `tools/check_v1_final_contract.py`;
- `tests/test_v1_final_phases_10_16.py`;
- the remaining non-retired tests that do not encode removed compatibility contracts.

Historical MVP tests are evidence about past behavior, not authority over the final architecture. The focused final suite contains 33 architecture tests after the generic-predication and reviewed-constant closure.
