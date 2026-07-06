# Semantic Graph Brain Implementation Plan

Status: implementation gap plan
Audience: CEMM maintainers and coding agents
Scope: concrete work to close the v4.2 semantic graph brain gaps

## 1. Current Gap Summary

The latest reviewed GitHub code contains real v4-direction modules, but the
runtime is still a hybrid. The biggest issue is not absence of effort. It is
authority leakage: old modules still decide, retrieve, realize, and write memory
outside the UOL graph and graph patch contract.

Critical gaps:

| Area | Current State | Gap | Required Change |
|---|---|---|---|
| Runtime entrypoint | `Pipeline`, `RecursiveLoop`, `SemanticCPU` coexist | No single authoritative kernel | Add `SemanticKernelRuntime` and route all turns through it |
| Interpretation | `MeaningPerceptor` and old `SemanticInterpreter` both run | Duplicate semantic sources | Make UOLGraph authoritative; derive legacy views from it |
| Decision | `DecisionRouter` has plan path plus many fallbacks | Old fallbacks can override graph truth | Route from `ActResolutionPlan` and `SemanticWorkingSet` only |
| Learning | `RememberOperator` writes claims directly | Bypasses graph patch law | Convert remember/update writes to graph patches |
| Validation | `ConceptConsolidator` checks mainly confidence/ops | No real trust/freshness/contradiction policy | Add `PatchValidator` |
| Recursion | `RecursiveLoop` reacts to failure/uncertainty | Not graph attention | Add `SemanticAttentionController` |
| Self model | Seed claims and self state exist | Not full operational self graph | Add self lattice and self affordance records |
| Compatibility | v3/v4 layers are mixed | Backward compatibility controls behavior | Move legacy into adapters |
| Docs | GitHub main still has v3/v4.1 wording | Agents can drift | Make root v4.2 docs canonical |

## 2. Implementation Principle

Do not fix this by adding more fallback strings.

Every implementation step should move authority toward:

```text
Signal
-> MeaningPerceptPacket
-> UOLGraph
-> SemanticWorkingSet
-> RuntimeResolutionResult
-> ActResolutionPlan
-> RealizationPlan
-> GraphPatch
-> PatchValidationResult
-> ConsolidationResult
```

If a module needs old structures, derive them from UOLGraph through an adapter.

## 3. Phase 0: Contract And Drift Cleanup

Goal: make future agents stop implementing against stale v3/v4.1 assumptions.

Files to update or add:

```text
AGENTS.md
README.md
pyproject.toml
consolidated_architecture.md
docs/core_loop_runtime.md
core_loop_update_manifest.md
```

Required changes:

1. Ensure root `AGENTS.md` exists in GitHub.
2. README must say v4.2 seed semantic runtime, not v3.1.
3. `pyproject.toml` description must stop saying ERCA v2.0.
4. Mark old docs as background only.
5. Add explicit "single runtime authority" rule.
6. Add explicit "direct durable memory writes are invalid" rule.

Tests:

```text
tests/test_architecture_contract.py
```

Assertions:

- root `AGENTS.md` exists
- README references v4.2
- canonical atom/edge counts are exactly 16/16
- no active doc claims deterministic MVP or v3-only architecture

## 4. Phase 1: Add Canonical Runtime Cycle Types

Goal: create one typed trace object that all stages must populate.

Add:

```text
cemm/types/runtime_cycle.py
cemm/types/semantic_focus.py
cemm/kernel/semantic_working_set.py
```

`runtime_cycle.py`:

```python
@dataclass
class RuntimeDiagnostics:
    stage_order: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    compatibility_adapters_used: list[str] = field(default_factory=list)


@dataclass
class RuntimeCycleResult:
    signal: Signal
    context_kernel: ContextKernel
    percept: MeaningPerceptPacket
    uol_graph: UOLGraph
    working_set: SemanticWorkingSet
    retrieval: RetrievalExecutionResult
    resolution: RuntimeResolutionResult
    act_plan: ActResolutionPlan
    realization_plan: RealizationPlan | None = None
    answer_graph: SemanticAnswerGraph | None = None
    realized_output: str = ""
    patch_candidates: list[GraphPatch] = field(default_factory=list)
    validation: PatchValidationResult | None = None
    consolidation: ConsolidationResult | None = None
    diagnostics: RuntimeDiagnostics = field(default_factory=RuntimeDiagnostics)
```

Tests:

```text
tests/test_runtime_cycle_contract.py
```

Assertions:

- all stages appear in order
- decision cannot exist without UOLGraph
- learning cannot exist without validation result

## 5. Phase 2: Build SemanticAttentionController

Goal: introduce graph-native recursive attention.

Add:

```text
cemm/kernel/semantic_attention_controller.py
cemm/kernel/interpretation_path_selector.py
cemm/kernel/candidate_set_resolver.py
cemm/kernel/group_predicate_index.py
```

Core algorithm:

```python
class SemanticAttentionController:
    def attend(
        self,
        graph: UOLGraph,
        kernel: ContextKernel,
        budget: AttentionBudget,
    ) -> SemanticWorkingSet:
        working_set = SemanticWorkingSet.from_graph(graph)
        while budget.remaining():
            focus = self._select_focus(working_set, graph, kernel)
            if focus is None:
                break
            self._resolve_focus(focus, working_set, graph, kernel)
            if working_set.is_action_ready:
                break
        return working_set
```

Focus priorities:

1. safety/risk atoms
2. unresolved required ports
3. fresh evidence requirements
4. ambiguous candidate sets
5. anaphora/deixis unresolved refs
6. contradiction markers
7. active intent atoms
8. self/action affordance requirements
9. low-confidence predicate bindings

Tests:

```text
tests/test_semantic_attention_controller.py
```

Assertions:

- ambiguous `bank` creates selected/rejected paths
- missing required port creates evidence or ask requirement
- fresh-world query creates retrieval requirement
- safety focus outranks normal answer focus

## 6. Phase 3: Make SemanticKernelRuntime Authoritative

Goal: replace hybrid pipeline authority.

Add:

```text
cemm/kernel/semantic_kernel_runtime.py
```

Initial implementation:

```python
class SemanticKernelRuntime:
    def __init__(
        self,
        perceptor: MeaningPerceptor,
        graph_builder: MeaningGraphBuilder,
        attention: SemanticAttentionController,
        retrieval_executor: RetrievalExecutor,
        runtime_resolver: RuntimeResolver,
        planner: ActResolutionPlanner,
        realization_planner: RealizationPlanner,
        realizer: RealizationPipeline,
        patch_extractor: GraphPatchExtractor,
        patch_validator: PatchValidator,
        consolidator: ConceptConsolidator,
    ) -> None:
        ...

    def run_turn(self, signal: Signal, kernel: ContextKernel) -> RuntimeCycleResult:
        percept = self.perceptor.perceive(signal, kernel)
        graph = self.graph_builder.build(percept)
        working_set = self.attention.attend(graph, kernel, kernel.budget)
        retrieval = self.retrieval_executor.execute(working_set.retrieval_plan, kernel, graph=graph)
        resolution = self.runtime_resolver.resolve(graph, working_set, retrieval, kernel)
        plan = self.planner.plan(meaning_percept=percept, runtime_resolution=resolution)
        realization_plan = self.realization_planner.plan(plan, graph, working_set, retrieval)
        output, answer_graph = self.realizer.realize(realization_plan, kernel)
        patches = self.patch_extractor.extract(graph, plan=plan, answer_graph=answer_graph)
        validation = self.patch_validator.validate(patches, graph=graph, kernel=kernel)
        consolidation = self.consolidator.consolidate(validation.accepted, source_graph=graph)
        return RuntimeCycleResult(...)
```

Refactor:

```text
cemm/kernel/pipeline.py
```

Change it into a thin wrapper:

```python
result = self._semantic_kernel.run_turn(signal, kernel)
```

Temporary compatibility:

```text
cemm/adapters/uol_to_semantic_event_graph.py
cemm/adapters/uol_to_conversation_act.py
cemm/adapters/uol_to_training_export.py
```

Rule:

```text
Adapters may export data.
Adapters may not decide behavior.
```

Tests:

```text
tests/test_semantic_kernel_runtime.py
```

Assertions:

- `Pipeline.run()` invokes `SemanticKernelRuntime`
- no direct `SemanticInterpreter.run()` call controls decision
- no direct `UOLMapper.map_signal()` call controls decision
- old adapters are listed in diagnostics if used

## 7. Phase 4: Replace Direct Memory Writes With Graph Patches

Goal: enforce graph-patch-only durable learning.

Refactor:

```text
cemm/operators/remember.py
cemm/operators/update_claim.py
cemm/kernel/memory_update_planner.py
cemm/memory/durable_semantic_store.py
```

New flow:

```text
MemoryUpdatePlan
-> GraphPatch(operation="upsert_claim_candidate")
-> PatchValidator
-> DurableSemanticStore.materialize_claim()
```

`RememberOperator` should no longer call:

```python
ctx.store.claims.put(...)
ctx.store.profile.put(...)
```

Instead:

```python
patches = MemoryPatchCompiler.compile(ctx.params, ctx.input_signal, ctx.kernel)
validation = ctx.patch_validator.validate(patches, graph=ctx.uol_graph, kernel=ctx.kernel)
consolidation = ctx.consolidator.consolidate(validation.accepted, source_graph=ctx.uol_graph)
```

Add:

```text
cemm/learning/memory_patch_compiler.py
```

Patch type:

```python
PatchOperation(
    operation="upsert_claim_candidate",
    target_id=f"claim:{subject}:{predicate}:{object_hash}",
    fields={
        "subject_entity_id": subject,
        "predicate": predicate,
        "object_value": object_value,
        "object_entity_id": object_entity_id,
        "source_signal_id": signal.id,
        "permission_scope": permission.scope,
        "valid_from": valid_from,
        "valid_until": valid_until,
    },
)
```

Tests:

```text
tests/test_graph_patch_memory_law.py
```

Assertions:

- `RememberOperator` does not call `Store.claims.put`
- claim appears only after accepted patch
- rejected patch does not create claim
- quarantined patch is journaled but not materialized

## 8. Phase 5: Add PatchValidator

Goal: make durable learning trustworthy.

Add:

```text
cemm/learning/patch_validator.py
```

Validation pipeline:

```python
class PatchValidator:
    def validate(
        self,
        patches: list[GraphPatch],
        *,
        graph: UOLGraph,
        kernel: ContextKernel,
        store: DurableSemanticStore,
    ) -> PatchValidationResult:
        ...
```

Checks:

```text
permission_valid
source_present
source_trust_sufficient
evidence_present
freshness_valid
temporal_scope_valid
required_ports_bound
contradiction_absent_or_resolved
risk_acceptable
confidence_sufficient
```

Routing:

| Validation Outcome | Runtime Action |
|---|---|
| accepted | consolidate |
| rejected | record diagnostic |
| quarantined | journal only |
| needs_confirmation | ask |
| needs_retrieval | retrieve |

Tests:

```text
tests/test_patch_validator.py
```

Assertions:

- missing source rejects or quarantines
- private permission prevents public materialization
- stale world fact requires fresh source
- contradictory active claim requires confirmation or quarantine
- low confidence does not silently write

## 9. Phase 6: Refactor DecisionRouter

Goal: remove fallback authority.

Current `DecisionRouter` has too many behavior paths:

- ActResolutionPlan path
- ConversationAct path
- graph frame fallback
- observation semantics fallback
- context inference fallback
- raw text helper methods

Target:

```python
DecisionRouter.run(
    graph: UOLGraph,
    working_set: SemanticWorkingSet,
    resolution: RuntimeResolutionResult,
    act_plan: ActResolutionPlan,
    policy: RuntimePolicy,
) -> DecisionPacket
```

Allowed logic:

1. safety override
2. policy failure
3. missing required evidence
4. missing required port
5. accepted action candidate
6. ask/abstain/retrieve/quarantine

Move old logic to:

```text
cemm/adapters/legacy_decision_adapter.py
```

Tests:

```text
tests/test_decision_router_authority.py
```

Assertions:

- raw text cannot select final action
- ConversationAct cannot override UOLGraph safety/evidence policy
- SEG fallback cannot override ActResolutionPlan
- unknown open-domain entity query routes by evidence policy

## 10. Phase 7: Self Model Lattice

Goal: make self native to the graph brain.

Add:

```text
cemm/memory/self_model_lattice.py
cemm/kernel/self_model_resolver.py
```

Seed self records through graph patches:

```text
self is_a semantic_runtime
self has_property name
self has_property capability
self has_property limitation
self used_for answer_from_evidence
self used_for graph_patch_learning
self prevents unsupported_factual_claim
self needs evidence
self needs permission
self evaluates runtime_error
```

Self query flow:

```text
self question
-> self atoms in UOLGraph
-> SelfModelResolver
-> selected self records
-> ActResolutionPlan
-> realization
```

Tests:

```text
tests/test_self_model_lattice.py
```

Assertions:

- "what is your name" answers from self record
- "what can you do" answers from capability records
- "what do you not know" answers from limitation/uncertainty records
- self records are consolidated from patches

## 11. Phase 8: Retrieval From Graph Focus

Goal: retrieval should be driven by semantic focus, not broad kernel fallback.

Refactor:

```text
cemm/kernel/retrieval_planner.py
cemm/retrieval/retrieval_executor.py
```

Input:

```python
RetrievalPlanner.plan(
    graph: UOLGraph,
    working_set: SemanticWorkingSet,
    resolution: RuntimeResolutionResult,
    kernel: ContextKernel,
) -> RetrievalPlan
```

Retrieval targets:

- concept IDs
- predicate schemas
- source policy
- claim records
- construction records
- causal affordances
- self records
- exemplars

Tests:

```text
tests/test_graph_focus_retrieval.py
```

Assertions:

- user-name query retrieves profile/self/user identity records
- fresh-world query requires live evidence or abstains
- ambiguous entity query retrieves candidate concept records
- unsupported broad retrieval is not used when plan mode is `none`

## 12. Phase 9: Realization Plan

Goal: ensure text is traceable to graph, plan, evidence, and policy.

Add:

```text
cemm/synthesis/realization_plan.py
cemm/synthesis/realization_planner.py
```

Contract:

```python
@dataclass
class RealizationPlan:
    intent: str
    response_mode: str
    selected_claim_ids: list[str]
    selected_graph_atom_ids: list[str]
    selected_evidence_refs: list[str]
    uncertainty_reasons: list[str]
    allowed_strategy_order: list[str]
    forbidden_claims: list[str]
    must_include: list[str]
    must_not_include: list[str]
```

Tests:

```text
tests/test_realization_traceability.py
```

Assertions:

- factual output cites selected evidence
- unsupported factual span fails verification
- fresh-world uncertainty is preserved
- private evidence is not leaked

## 13. Phase 10: Remove Or Demote Backward Compatibility

Do not delete everything immediately. Demote authority first.

Move behind adapters:

```text
SemanticEventGraph
ConversationActPacket
ObservationSemantics
legacy UOLMapper outputs
raw text helper routing
```

Target adapter files:

```text
cemm/adapters/uol_to_semantic_event_graph.py
cemm/adapters/uol_to_conversation_act.py
cemm/adapters/uol_to_observation_semantics.py
cemm/adapters/uol_to_training_examples.py
```

Rule:

```text
Adapter output may enrich diagnostics.
Adapter output may not write memory.
Adapter output may not select final action.
Adapter output may not bypass patch validation.
```

Tests:

```text
tests/test_legacy_adapter_boundaries.py
```

Assertions:

- adapter output appears in diagnostics
- adapter output cannot override selected graph path
- adapter output cannot create durable claim

## 14. Bug Fixes Identified In Review

Fix immediately:

```text
cemm/__main__.py
```

Bug:

```python
from ..kernel.memory_update_planner import MemoryUpdateBatch, MemoryUpdateTask
```

Inside `cemm/__main__.py`, this should be:

```python
from .kernel.memory_update_planner import MemoryUpdateBatch, MemoryUpdateTask
```

Add regression:

```text
tests/test_batch_memory_import.py
```

Assertion:

- multi-fact remember path does not raise relative import error

## 15. Acceptance Test Suite

Add a focused v4.2 suite:

```text
tests/test_v42_runtime_contract.py
tests/test_semantic_kernel_runtime.py
tests/test_semantic_attention_controller.py
tests/test_graph_patch_memory_law.py
tests/test_patch_validator.py
tests/test_self_model_lattice.py
tests/test_decision_router_authority.py
tests/test_realization_traceability.py
tests/test_legacy_adapter_boundaries.py
```

Required scenarios:

1. User says "my name is Opata Chibueze"; system writes only via patch.
2. User asks "what is my name"; answer retrieves accepted semantic record.
3. User asks "who is Obama"; unknown entity response does not fabricate.
4. User teaches "Obama is a former president of the USA"; patch is validated.
5. User asks "who is Obama"; answer uses accepted semantic record.
6. Ambiguous "bank" retains candidate alternatives.
7. "current president" requires fresh evidence.
8. Insult/frustration is not stored as durable fact.
9. Self capability answer comes from self records.
10. Rejected candidates remain visible in diagnostics.
11. Legacy adapters cannot select final action.
12. Direct claim writes from operators are forbidden.

## 16. Migration Strategy

Stage migration to avoid breaking everything at once.

### Step 1: Add new runtime in parallel

Keep current `Pipeline`, but introduce `SemanticKernelRuntime` and run it in
shadow mode.

Diagnostics:

```text
current_decision
semantic_kernel_decision
diff_reason
```

### Step 2: Make SemanticKernelRuntime primary for tests

Run v4.2 tests against the new runtime only.

### Step 3: Make Pipeline call SemanticKernelRuntime

`Pipeline.run()` becomes a wrapper.

### Step 4: Convert old outputs to adapters

SEG and ConversationAct remain available only as derived projections.

### Step 5: Remove direct durable writes

Patch compiler and validator become mandatory for memory writes.

### Step 6: Delete dead fallbacks

Remove fallback code only after tests prove equivalent or better behavior.

## 17. Definition Of Done

The observed gaps are fixed when:

- GitHub main documents v4.2 as the active architecture.
- One runtime object owns the full loop.
- UOLGraph is mandatory before decision.
- Semantic attention creates selected/rejected interpretation paths.
- Retrieval is driven by graph focus.
- ActResolutionPlan is compiled from graph resolution, not raw text.
- Realization is traceable to graph/evidence/plan.
- Every durable learning write is an accepted GraphPatch.
- Patch journal records accepted, rejected, and quarantined patches.
- Self is represented as semantic records with capabilities, limits, needs,
  policies, and affordances.
- Legacy layers are adapters only.
- Tests prevent fallback drift.

## 18. Recommended First Pull Request

The first PR should be small but decisive:

1. Add `RuntimeCycleResult`.
2. Add `SemanticKernelRuntime` skeleton.
3. Add `PatchValidator` skeleton.
4. Add `MemoryPatchCompiler`.
5. Refactor `RememberOperator` to optionally use patch path behind a feature
   flag.
6. Add tests proving direct claim writes are no longer the default.
7. Fix the `__main__.py` relative import bug.

This creates the write barrier and runtime spine without trying to solve every
attention and self-model problem in one move.

## 19. Strategic Implementation Warning

The dangerous path is to keep making the old pipeline smarter.

That will produce more demos, but not the breakthrough.

The correct path is to make the semantic graph brain unavoidable:

```text
no UOLGraph -> no decision
no ActResolutionPlan -> no realization
no PatchValidationResult -> no durable learning
```

