# CEMM v3.4 Implementation Audit

> **NOTE:** This audit was performed against commit `d45a0f6` before v3.4 completion.
> It is retained for historical reference. The v3.4 completion plan has been fully
> executed (Stages 0-10). All 28 authority components are specified, implemented,
> wired, authoritative, and verified. 1013 tests pass with zero failures.
> See `ARCHITECTURE.md §24` for the completion declaration.

**Repository:** `robosys-labs/cemm`  
**Audited commit:** `d45a0f6e2989ef11122de9fef66786c40c7ef2a5`  
**Compared from:** `7c006474bc2c3de6daaca7133b361823c0c45eb8`  
**Audit type:** static source-code and runtime-wiring audit

## Evidence limitation

The repository could not be cloned in the execution container because the container could not resolve `github.com`. GitHub supplied the current source files and commit diffs, but the full test suite could not be executed locally. The latest commit also has no reported combined CI statuses.

Consequently:

- code paths, interfaces, authority relationships, and direct bugs were inspected;
- implementation status is assessed statically;
- passing runtime behavior is **not** assumed from class/file presence;
- no phase is marked verified unless executable evidence was available.

---

# 1. Executive verdict

The v3.4 implementation is **not a completed cutover**.

It has four different levels of progress:

| Dimension | Static assessment |
|---|---:|
| Specified | strong / nearly complete |
| Classes and records created | substantial |
| Wired into `run_turn()` | partial |
| Authoritative over behavior | low |
| End-to-end verified | not established |

The active runtime is a hybrid:

```text
legacy Signal / ContextKernel / TextNormalizer
→ legacy SemanticCPU MeaningPerceptor
→ v3.4 bridge/composer/evaluator trace branch
→ legacy UOL graph and 3.3 learning branch
→ legacy semantic program and operational contracts
→ legacy query engine and patch pipeline
→ shallow v3.4 goal/plan/execute/commit trace branch
→ legacy ResponseFormationEngine determines the actual reply
→ legacy session/output state persists
```

The v3.4 path is not merely using legacy adapters at the boundary. Legacy components still decide:

- what predicates and roles exist;
- what operational meaning is selected;
- what query runs;
- what durable relations are written;
- what state/effects are compiled;
- what learning question is emitted;
- what response text the user sees.

The v3.4 objects are often diagnostics or parallel control records.

## Overall completion estimate

This is a rough static estimate of **authoritative hot-path completion**, not a line-count estimate:

| Phase | Status | Approximate authoritative completion |
|---|---|---:|
| 0 Governing architecture | implemented | 95% |
| 1 Canonical records/fingerprints | mostly implemented | 70% |
| 2 Schema lifecycle/activation | partial, unsafe | 30% |
| 3 Foundations/boot | code exists, not boot-wired | 25% |
| 4 Perception/composition | transitional bridge, inaccurate | 30% |
| 5 Grounded understanding | major false-positive paths | 20% |
| 6 Epistemics/self-awareness | shallow wiring | 20% |
| 7 Recursive learning | lifecycle skeleton only | 10% |
| 8 Invalidation/replay safety | queue scaffold; no hot-path closure | 10% |
| 9 Effects/commit correctness | legacy remains authoritative | 10% |
| 10 NLG/common ground/repair | planner exists; output remains legacy | 15% |
| 11 Correction/retraction | not shown authoritative | <10% |
| 12 Legacy retirement | explicitly incomplete/xfail | 0% |

A fair overall description is:

> The architecture has been translated into many types and component shells, but only roughly one fifth to one third of the intended v3.4 cognitive path is behaviorally authoritative.

---

# 2. Step-by-step active runtime trace

## 2.1 Entry and orientation

`kernel/pipeline.py` remains the application entry and still constructs:

- `LexemeMemory`
- `SemanticModelStore`
- `PromotionGate`
- `ConceptLattice`
- `ConstructionLattice`
- `EpisodicTraceStore`

It delegates to `SemanticKernelRuntime`, but the result type remains the old, mutable `RuntimeCycleResult`, not the canonical immutable `CognitiveCycle`.

`RuntimeCycleResult` explicitly labels v3.4 fields as:

```text
v3.4 understanding pipeline trace fields — trace-only; do not affect behavior
```

This is direct evidence that the cutover has not occurred.

The new `KernelSnapshot` is pinned, but only two revisions are populated:

- schema store revision;
- legacy durable semantic memory revision.

The remaining fingerprint dimensions normally stay at defaults.

## 2.2 Perception

The runtime calls:

```python
self._cpu.perceptor.perceive(signal, kernel)
```

`SemanticCPU` is the old container for:

- `MeaningPerceptor`
- `MeaningGraphBuilder`
- `ActResolutionPlanner`
- `GraphPatchExtractor`
- `ConceptConsolidator`

The v3.4 `PerceptToSurfaceEvidence` then converts this already interpreted legacy packet into v3.4 evidence.

This means the new composer does not receive neutral surface evidence. It receives candidate structure already selected or constrained by legacy:

- referent extraction;
- predicate phrases;
- action atoms;
- relation atoms;
- intent labels;
- affect markers.

The bridge is therefore not just a transport adapter; it imports old semantic assumptions.

## 2.3 Composition

`SemanticComposer` runs, but:

- opaque references use random UUIDs and are not registered in the schema store;
- the same unknown term receives a new opaque identity on later turns;
- construction candidates can reference nonexistent `schema:<key>` records;
- one utterance-wide negation flag makes every proposition negative;
- communicative force is attached only to the highest-confidence proposition;
- questions receive a generic `role:unknown` port;
- source evidence refs are never populated;
- `compose_nested()` is not called by the runtime;
- role fillers are token placeholders such as `ref:token:2`, not grounded referents, values, or propositions.

The composer exists, but it is not yet a reliable compositional semantic authority.

## 2.4 Grounding

The runtime only calls:

```python
GroundingResolver.ground_referent(...)
```

It does not call `ground_definition()` for selected schema senses.

Therefore the hot path does not derive:

- Grounded Definition Closure;
- competence status;
- schema use profile;
- epistemic/contextual admissibility;
- operation-specific schema usability.

`ground_definition()` itself currently creates a generic, hard-coded `GroundingSpecification` instead of retrieving the actual schema grounding specification.

## 2.5 Epistemics

Every candidate proposition is evaluated with:

```text
no evidence
no schema use profile
actual context
```

The expected result is usually:

```text
support = neither
admissibility = blocked
```

The evaluator contains several placeholders:

- freshness is always treated as true;
- evidence independence is a Boolean rather than a lineage computation;
- causal warrant is inferred from substrings inside `source_ref`;
- “counterevidence considered” is hard-coded true during knowledge derivation.

The runtime does not retrieve evidence before this assessment.

## 2.6 Capability

The runtime fabricates a positive competence record and registered implementation for `op:understand`, but supplies none of the other required live conditions:

- health;
- input channel;
- output channel;
- resources;
- permission;
- contextual preconditions.

The evaluator should therefore return incapable.

The runtime then authorizes operations using:

```python
capability_available = capability_assessment is not None
```

rather than checking the assessment’s status.

This converts the existence of a negative assessment into capability success.

## 2.7 Interpretation and gaps

`InterpretationResolver` accepts grounding assessments but never uses them.

It:

- ranks propositions by confidence;
- adds an epistemic confidence boost;
- defines “opaque” mainly as missing context;
- can select epistemically blocked propositions;
- matches a predication by choosing the first predication with token indices, not the proposition’s actual `predication_ref`.

`GapDetector` says gaps must block a selected goal, but it:

- ignores `selected_interpretations`;
- creates a gap for every opaque ref;
- creates an admissibility gap for every blocked assessment;
- uses `role_name`, while the canonical `OpenPort` uses `role_schema_ref`;
- therefore creates generic/incorrect role targets.

The runtime opens only the first v3.4 learning transaction and does nothing further with it.

## 2.8 Retrieval

`SemanticRetriever` is a stub.

It attempts:

```python
store.find_candidates(proposition_id)
```

even though `find_candidates()` expects a semantic key.

Durable relation retrieval contains `pass`.

Open-port retrieval reads `role_name`, inconsistent with canonical open-port fields.

The actual query answer still comes from the legacy `SemanticQueryEngine`.

## 2.9 Legacy semantic and operational pipeline resumes

After the v3.4 trace branch, the runtime resumes:

```text
legacy UOL graph building
legacy SemanticGapDetector
legacy LexemeCandidateIndex
legacy CausalBridge
legacy SituationFrameBuilder
legacy EntityGroundingResolver
legacy InterpretationLattice
legacy PredicateActivationResolver
legacy SemanticAttentionController
legacy SemanticProgramCompiler
legacy SafetyFrameDetector
legacy OperationalMeaningCompiler
legacy StateOccupancyCompiler
legacy StateDeltaCompiler
legacy StateTransmutationCompiler
legacy OperationalCausalRouter
legacy ObligationGraphBuilder
legacy OperationalContractCompiler
legacy TransmutationAuthorizer
legacy TeachingFrameManager
legacy RelationFrameCompiler
legacy SemanticQueryEngine
legacy PredicateSchemaInductor
legacy ActResolutionPlanner
```

This is the operative semantic CPU.

## 2.10 v3.4 goals, planning, authorization, execution

The v3.4 decision branch runs after the legacy query/contract path has already been established.

`GoalArbiter` mostly maps communicative-force labels into generic goal kinds.

`Planner` then maps goal kinds into:

```text
information_state → op:query
world_state       → op:write
discourse         → op:respond
```

This is response-label planning, not operation-schema planning.

No semantic role bindings, preconditions, effects, dependencies, or actual query/write target are supplied.

`OperationAuthorizer` has fail-open defaults for every condition.

The runtime supplies only a capability-presence Boolean.

### Critical authorization bypass

`OperationExecutor` checks:

```python
getattr(authorization, "authorized", True)
```

But `AuthorizationResult` contains `status`, not `authorized`.

Therefore a denied `AuthorizationResult` has no `.authorized` property and defaults to `True`.

Denied operations execute.

The unit tests conceal this because they pass a mock object containing an `authorized` Boolean rather than the real `AuthorizationResult`.

With no adapter, every operation is recorded as successful while doing nothing.

## 2.11 Durable writes and critical commit

The real durable semantic writes are still:

```text
legacy GraphPatchExtractor
→ legacy PatchValidator
→ legacy PatchCommitter
→ legacy DurableSemanticStore
```

The v3.4 `CommitCoordinator` does not write to a real persistence interface. It generates synthetic record IDs and increments an internal counter.

The runtime converts successful operation IDs into required mutation operations, but cognitive operations normally produce no evidence refs. `CommitCoordinator.validate()` rejects required mutations with no evidence.

Thus the v3.4 critical commit usually fails, while the legacy patch commit may still have changed memory.

This creates two incompatible commit truths.

### Old false write-success bug still present

`_build_write_outcome()` still does:

```text
if no exact required targets exist
and a write contract exists
then every patch operation target becomes required
```

An auxiliary concept/schema write may therefore be reclassified as the requested write.

The earlier “I’m an engineer” false confirmation can still recur.

## 2.12 Response and common ground

`ResponsePlanner` creates a v3.4 `SemanticMessagePlan`.

But actual text is produced by:

```python
ResponseFormationEngine.form(ResponseSituation(...))
```

using legacy:

- obligation frame;
- answer binding;
- relation frames;
- semantic program;
- write outcome;
- UOL graph.

The new message plan is not passed to the renderer.

Then common ground records every semantic item from the unused v3.4 plan as dispatched merely because the unrelated legacy output string is non-empty.

This can record propositions that were not actually expressed.

`ResponsePlanner` also defaults a proposition with no epistemic assessment to `ASSERTED`, which is unsafe.

## 2.13 Persistence

The runtime persists:

- legacy context kernel;
- legacy teaching frame;
- legacy learning episode manager.

It does not persist:

- canonical schema store;
- v3.4 learning transactions;
- replay queue;
- v3.4 common ground;
- capability observations;
- canonical `CognitiveCycle`;
- v3.4 epistemic assessments.

Restarting the runtime loses most v3.4 state.

---

# 3. Schema and learning implementation accuracy

## 3.1 SemanticSchemaStore

Positive:

- immutable envelopes;
- explicit lifecycle statuses;
- store revision;
- reverse dependency index;
- lexical index;
- sense clusters;
- CAS-like record revision checks.

Major defects:

1. `activate()` does not require a grounding assessment, competence result, or admissibility result.
2. Any caller with the current revision can activate a provisional record.
3. `activate_cluster()` is not atomic.
4. Rollback is a second sequence of status mutations visible to concurrent readers.
5. Scope filtering is a literal `pass`.
6. active resolution may return the highest version/confidence regardless of the correct epistemic world.
7. record CAS revision and semantic schema version are separate but inconsistently ranked.
8. no real persistence, locks, unit of work, or conflict merge policy.
9. dependency updates and revision retention are incomplete.
10. sense-cluster merging manipulates sets without a durable, reversible identity journal.

## 3.2 Grounded Definition Closure

The class is named correctly, but actual checks are too permissive.

Current behavior includes:

- typed-role validity reduced to `bool(schema_kind)`;
- expressibility passes by default;
- dependency resolution returns `BLOCKED` but does not block structural executability;
- recursive component validation passes unconditionally;
- query/recognition/inference/contradiction behavior passes unconditionally;
- competence is `BLOCKED` but is not part of the executable blocker set.

The final `is_structurally_executable` calculation only treats `FAILED` checks and explicit blocker strings as blockers.

A schema can therefore be declared structurally executable while:

- dependencies are unresolved;
- competence is absent;
- recursion is unvalidated;
- behavior is unimplemented;
- roles are not truly typed.

## 3.3 Pattern assessment

Pattern function and strength exist, which is good.

But:

- constitutive closure ignores strength;
- a probabilistic/typical constitutive pattern can count toward closure;
- differentiator detection ignores pattern strength;
- pattern references in the grounding specification are not resolved against an authoritative pattern registry;
- expression is `Any`;
- no truth/query/contradiction evaluator validates the pattern AST.

## 3.4 Competence harness

The “harness” does not execute competence cases.

It trusts a pre-filled `passed: bool`.

It also trusts:

- `is_independent`;
- input lineage strings;
- oracle lineage strings.

Therefore a caller can self-certify by constructing favorable records.

No isolated composer/query/inference/round-trip execution occurs.

## 3.5 LearningCoordinator

The transaction types and method names follow the architecture, but the hot path only opens a transaction.

Even if called manually, `attempt_activation()` currently:

- creates every child as `schema_kind="predicate"`;
- uses a weak environment fingerprint containing only the base store revision;
- runs competence with an empty case set;
- does not perform replay;
- does not perform actual epistemic admissibility;
- does not publish invalidation/replay events;
- does not persist a provisional child into the store;
- does not resume the blocked goal.

Its completion gate lists nine conditions but checks only a small subset.

## 3.6 ReplayQueue

The queue has a good deduplication-key shape.

However it is:

- in-memory only;
- not invoked by `run_turn()`;
- not integrated with ordinary replay;
- not linked to operation-execution exclusions;
- not connected to schema activation events;
- not connected to goal resumption.

---

# 4. Test and verification accuracy

The current tests mainly verify that classes return objects and that simple mock-driven branches execute.

Examples of false assurance:

- executor tests use a custom `MockAuthorization(authorized=...)`, hiding the real `AuthorizationResult.status` mismatch;
- open-port tests use `MockOpenPort.role_name`, hiding the canonical `role_schema_ref` mismatch;
- retriever tests accept empty retrieval as success;
- planner tests assert the hard-coded `op:query` / `op:write` mapping;
- interpretation tests reward confidence-only selection;
- cutover tests mark the real no-legacy-import gate as expected failure.

`test_phase12_retirement.py` explicitly sets the cutover as incomplete and marks both legacy-import and forbidden-pattern gates `xfail`.

Many previous stress/regression/response/hot-path tests were deleted during “Removing legacy code/arch,” even though the legacy runtime remains active.

No current CI result was reported for the latest commit.

---

# 5. Accurate status by architecture phase

## Phase 0 — Governing architecture

**Status:** implemented and authoritative.

Root `AGENTS.md` is v3.4 and the integrated architecture documents exist.

Remaining:
- update baseline/status language after code completion;
- remove claims of authoritative cutover until the cutover tests pass.

## Phase 1 — Canonical records and fingerprints

**Status:** substantially implemented, partially wired.

Good:
- immutable canonical records;
- `KernelSnapshot`;
- environment fingerprint model;
- semantic message/mutation/learning records.

Missing:
- stable serialization/persistence proof;
- full fingerprint population;
- runtime uses old result/container instead of `CognitiveCycle`;
- historical revision retention not proven end-to-end.

## Phase 2 — Schema store and activation

**Status:** implemented skeleton, not safe.

See store/activation defects above.

## Phase 3 — Foundations and boot

**Status:** code exists, not wired.

`BootValidator` and manifest code exist, but runtime creates an empty `SemanticSchemaStore` and never validates/registers boot schemas.

## Phase 4 — Perception and understanding

**Status:** transitional and incorrect.

The legacy perceptor remains semantic authority. Native language adapters and language packs are not the active input path.

## Phase 5 — Grounded understanding

**Status:** partial with critical false-positive bugs.

The relevant types exist, but closure, competence, grounding, use profiles, and interpretation are not reliable or fully connected.

## Phase 6 — Epistemics and self-awareness

**Status:** partial.

The evaluator model is strong, but evidence retrieval and live capability observations are absent. Runtime input is fabricated/incomplete.

## Phase 7 — Recursive learning

**Status:** lifecycle scaffold only.

No active multi-turn v3.4 learning flow reaches stage → replay → activation/provisional commit → resolver reuse.

## Phase 8 — Invalidation and replay

**Status:** local queue scaffold only.

No authoritative derived-cognition retraction path is visible in the runtime.

## Phase 9 — Effects and commit

**Status:** not cut over.

Legacy effects/patch writes remain authoritative. v3.4 authorization has a bypass; commit is simulated.

## Phase 10 — NLG/common ground

**Status:** not cut over.

The semantic message plan is not the input to realization. Common ground can record unspoken semantic items.

## Phase 11 — Correction/retraction

**Status:** not established as wired or authoritative.

## Phase 12 — Retirement

**Status:** explicitly incomplete.

Tests intentionally xfail the cutover.

---

# 6. Final implementation judgment

The implementation has successfully established:

- the v3.4 vocabulary and immutable record layer;
- many intended authority class boundaries;
- a documented target cycle;
- several useful guards and tests;
- a migration scaffold around the old runtime.

It has **not** successfully established:

- a native v3.4 perception/composition path;
- grounded definition closure;
- real competence execution;
- evidence-backed epistemics;
- meaning-backed recursive learning;
- authoritative v3.4 retrieval;
- safe operation execution;
- real v3.4 persistent commit;
- semantic-message-plan-driven NLG;
- output-accurate common ground;
- complete legacy retirement.

The implementation must be treated as:

```text
v3.4 migration scaffold over the v3.3/v4.2/v3.1 runtime
```

—not as a completed v3.4 cognitive kernel.
