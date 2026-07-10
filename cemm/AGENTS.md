# CEMM Agent Instructions

Status: governing implementation guide  
Audience: AI coding agents, reviewers, and maintainers working on CEMM  
Supersedes: older v3.0/SLC-only local plans when they conflict with the current architecture

## 0. Semantic Schema Kernel — Implementation Complete

**Status: COMPLETE.** The Semantic Schema Kernel refactor is fully implemented
across all 9 phases. The old fragmented meaning systems (flat keyword maps,
`event_schema_loader.py`, hardcoded dicts) have been replaced by a unified,
data-driven schema kernel with seven registry types.

See `newarch/semantic-schema-refactor.md` for the complete implementation record.

### What Was Fixed

```
Old system (replaced):
  ✗ flat keyword maps → action_key string (no slots, no state deltas)
  ✗ event_schema_loader.py / EventSchemaStore (side-channel, never reached pipeline)
  ✗ hardcoded ACTIONS/STATES/NEEDS dicts in language adapters
  ✗ hardcoded _EMOTIONAL_VERB_TO_RELATION in graph builder
  ✗ hardcoded _seed_rules in AffordancePredictor
  ✗ MeaningPerceptor monkey-patched with graph_builder after construction
  ✗ O(E) edge scans in _find_role_atom and _extract_state_delta_patches

New system (implemented):
  ✓ SemanticSchemaKernel with 7 registries loaded from semantic_schemas/*.json
  ✓ SchemaBackedLanguageAdapter delegates action lookup to ActionOperatorRegistry
  ✓ MeaningGraphBuilder compiles schema state_deltas into state atoms + causes edges
  ✓ Entity kind validation on has_role edges using schema allowed_entity_kinds
  ✓ AffordancePredictor generates rules from AffordanceRegistry
  ✓ UOLGraph adjacency index (_outgoing/_incoming) for O(degree) edge lookups
  ✓ MeaningPerceptor properly wired with schema_kernel via constructor
  ✓ SemanticKernelRuntime passes schema_kernel to SemanticCPU
```

### Remaining Causal-Runtime Wiring Gaps

Two culprits from the original 12-culprit plan remain partially open:

- **Culprit 1 (ConstructionMatcher)**: `graph_patch_templates` still emits metadata only for emotional predicates. Compensated by `_add_emotional_evaluations` in graph builder which handles `evaluates` edge creation directly from schema. Low priority.
- **Culprit 5 (CausalInference)**: `CausalBridge` exists and is called from runtime, but is a no-op without legacy `Store`. Full `DurableSemanticStore`-backed bridge not yet implemented.

All other culprits (2-4, 6-12) are fully fixed. See `newarch/causal-runtime-wiring-fix.md` for the detailed per-culprit status.

## 1. Canonical Source Of Truth

Use these files as the active implementation contract, in this order:

1. `AGENTS.md` (this file)
2. `ARCHITECTURE.md` (promoted consolidated architecture — implementation-facing contract)
3. `newarch/cemm-v3.1-lean-implementation-plan.md` (response formation architecture plan — COMPLETE)
4. `newarch/semantic-schema-refactor.md` (semantic schema kernel refactor plan — COMPLETE)
5. `newarch/causal-runtime-wiring-fix.md` (master fix plan — partially addressed)
6. `newarch/3.2-improvement-plan.md` (operational meaning and state-transmutation spine — IMPLEMENTED; see header for gap status)
7. `newarch/3.3-uol-graph-architecture.md` (UOL graph architecture details)
8. `newarch/core-loop-causal-recursive-spine.md` (runtime loop map after 3.2 changes — reference diagram)
9. `newarch/core_loop_runtime.md` (core loop runtime contract — partially superseded by ARCHITECTURE.md §5)

Superseded design docs and plans are archived at `docs/archive/newarch_superseded/`.
Use them as background reference only — they are not active architecture contracts.

The following newarch docs are **deprecated** and have been moved to archive:
- `semantic-graph-brain-gap-fix-implementation-plan.md`
- `semantic-graph-brain-implementation.md`
- `semantic-graph-brain.design.md`
- `runtime-single-authority-takeover-design.md`
- `cemm-v4.2-exact-root-cause-gap-fix-proposal.md`
- `missing_runtime_implementation_plan.md`
- `full_cemm_learning_brain_missing_pieces.md`
- `construction-matcher-refactor-plan.md`
- `cemm-sentient-response-formation-design-v2.md` (superseded by v3.1 implementation)
- `sentient-nlg-pipeline-design.md` (superseded by v3.1 implementation)

Do not follow any superseded plan. Follow `causal-runtime-wiring-fix.md` instead.

Older generated artifacts, patch files, archived docs, bootstrap scripts,
runtime databases, logs, `__pycache__`, JSONL exports, and files under old
proposal/archive directories are not active architecture guidance.

If any document says CEMM is only a deterministic conversational MVP, an
English-first router, or a text-answer generator, ignore that instruction.

Also ensure that old tests don't derail new implementation or cause drift. Delete and create new ones instead if necessary.

## 2. Core Identity

CEMM is a meaning-first language architecture.

It is not:

```text
a prompt wrapper
a plain intent classifier
a text-only chatbot
a giant sentence database
```

It is:

```text
a semantic runtime
a UOL working-graph system
a graph-patch learning system
a compression-oriented concept/construction/predicate/affordance learner
```

English text is one input/output surface. UOL graph structure is the internal
semantic workbench.

## 2.5 Fundamental Architecture Understanding Gate

Before writing any runtime, interpretation, routing, memory, safety, or response
code, the agent must understand and preserve CEMM's semantic substrate model.
CEMM is a multimodal, multilanguage system, do not patch visible transcript symptoms by adding English phrase cases to late
decision stages. That is antithetical to the project.

CEMM behavior must emerge from these substrates:

```text
surface signal
-> normalized multilingual/token evidence
-> meaning groups and candidate interpretations
-> UOL atoms/edges with source, permission, time, and modality
-> entity grounding and salience across turns
-> temporal/context state in ContextKernel and SessionStore
-> action/operator schemas over typed slots
-> state occupancy, state deltas, and state transmutations
-> operational meaning frames and causal effects
-> query/write/reaction/safety contracts
-> response formation from selected evidence
```

Agents must trace the broken behavior through that chain and fix the earliest
wrong semantic substrate that has enough authority to explain the bug. A change
in `OperationalMeaningCompiler`, `ObligationContractBuilder`, query execution,
or response formation is only acceptable when the upstream graph/contract
structure is already correct and the bug is truly in that stage.

### Required Pre-Code Trace

For every behavior fix, write down the evidence before editing code:

```text
1. What meaning group(s) were produced?
2. What candidate interpretations were preserved or lost?
3. Which UOL atoms and edges encode the entity, relation, action, state,
   modality, source, permission, and time?
4. Which entity state or temporal/session context is required?
5. Which action/operator schema, state occupancy frame, state delta frame,
   or state transmutation frame should carry the meaning?
6. Which operational frame and contract should follow from those substrates?
7. Why is the intended fix located at this layer rather than later in routing
   or response text?
```

If this trace cannot be produced, do not write code. Add diagnostics or tests
that expose the missing substrate first.

### Meaning Substrate Law

Correct:

```text
missing meaning -> improve perception / graph / schemas / state frames
bad entity reference -> improve grounding, salience, anaphora, or deixis
bad memory behavior -> improve graph patches, validation, or contracts
bad safety behavior -> improve state transmutations and causal effects
bad answer behavior -> improve query contracts, evidence selection, or relation frames
```

Incorrect:

```text
bad response -> add phrase match in OperationalMeaningCompiler
bad profile query -> special-case final user text in query execution
bad criticism handling -> list insult words in a late router
bad safety behavior -> token-match dangerous words
bad memory behavior -> block writes by raw text fragments
```

Seed heuristics may exist only as temporary scaffolding at the correct semantic
layer, with explicit diagnostics and tests proving the semantic gap they cover.

## 3. Current Runtime Contract

The active seed runtime loop is:

```text
Signal
-> MeaningPerceptor
-> MeaningPerceptPacket
-> MeaningGraphBuilder
-> UOLGraph
-> runtime resolution (concept/port/affordance)
-> ActResolutionPlanner
-> GraphPatchExtractor
-> ConceptConsolidator
-> durable semantic structures
```

Status: **v3.1 lean implementation complete; all phases 0-9 implemented and tested**
- `Pipeline.run()` delegates to `SemanticKernelRuntime.run_turn()` — single authority achieved
- `UOLGraph` is the sole working graph (with adjacency index for O(degree) edge lookups)
- `SemanticSchemaKernel` is the single canonical source for action/state/need/entity meaning
- `SchemaBackedLanguageAdapter` replaces all old language adapters — delegates to schema kernel
- `SemanticKernelRuntime.run_turn()` canonical v3.1 pipeline: perceive → build → attend → compile → schedule → teach → compile relations → query → plan → patch validation/commit → safety → response situation → response formation → output update
- `ResponseFormationEngine` is the single canonical response path (replaces retired `SemanticRealizer`)
- `BudgetController` produces `BudgetDecision` that constrains query, candidate, and realization stages
- `InternalActionProposer` + `InternalActionAuthorizer` handle Phase 8 internal actions
- `ResponseBudgetLearningExtractor` extracts learning patches from response outcomes (Phase 9)
- `PatchValidator` and `PatchCommitter` enforce graph-patch-only durable writes
- `SessionStore` restores/persists conversation, user affect, topic, discourse state across turns
- `EntitySalienceTracker` tracks entity salience across turns
- `DurableSemanticStore` stores and retrieves relation frames
- `MeaningPerceptor` properly wired with `schema_kernel` and `graph_builder` via constructor

**Retired (v3.1):**
- `SemanticRealizer` — removed from runtime, file recycled
- `response_templates.json` — recycled
- `RealizationContract` type — recycled
- `SemanticQueryEngine.build_contract()` — removed
- `SemanticQueryEngine._template_for_obligation()`, `_shift_pronouns_for_echo()`, `_sanitize_echo()` — removed
- Old response modules (`candidate_generator.py`, `framing.py`, `plan_gate.py`, `ranker.py`, `selector.py` at top level) — replaced by `transformers/` package

**Schema Kernel Refactor — COMPLETE:**
- All 9 phases implemented and verified (80 tests passing)
- See `newarch/semantic-schema-refactor.md` for full implementation record

**Remaining causal-runtime wiring gaps (see Section 0):**
- Culprit 1: ConstructionMatcher `graph_patch_templates` still metadata-only (compensated by graph builder)
- Culprit 5: `CausalBridge` is a no-op without legacy `Store`; full `DurableSemanticStore`-backed bridge not yet implemented

## 4. Compatibility Names

Some older docs use SLC names. Use this mapping:

| Older Term | Current Active Equivalent |
|---|---|
| `SemanticEventGraph` | `UOLGraph` plus meaning groups, predicates, candidate sets, concept resolutions, port bindings, affordances, and patch candidates |
| graph packet | `MeaningPerceptPacket` and/or `UOLGraph` depending on stage |
| semantic packet | `MeaningPerceptPacket` |
| typed latent / Decide | runtime resolution plus `ActResolutionPlanner` |
| `SemanticAnswerGraph` | not yet implemented as a first-class type; use `ActResolutionPlan` and future answer-graph type only when added |
| training export | `UOLGraph.to_training_example()` plus graph patch and realization metadata |

Do not invent a fake `SemanticAnswerGraph` just to satisfy old wording.

If answer-graph work is needed, add an explicit type behind the current
planner/realizer seam.

## 5. Non-Negotiable Ordering

Runtime changes must preserve this dependency order:

```text
Observe
-> Contextualize
-> Interpret
-> Ground
-> Retrieve
-> Infer
-> Decide
-> Realize
-> Update
-> Learn
```

Current implementation mapping:

| Stage | Current Implementation |
|---|---|
| Observe | `Signal`, source metadata, raw text |
| Contextualize | context/kernel objects, source, permission, self/user atoms |
| Interpret | `MeaningPerceptor`, meaning groups, predicates, hypotheses |
| Ground | `MeaningGraphBuilder`, `UOLGraph`, concept/port/source/time/place grounding |
| Retrieve | retrieval plan and selected evidence, when available |
| Infer | concept resolution, construction matches, port bindings, affordance predictions, candidate paths |
| Decide | `ActResolutionPlanner` |
| Realize | `ResponseFormationEngine` (budget-aware, candidate-based, language-specific rendering) |
| Update | graph patch extraction |
| Learn | consolidation into durable semantic structures |

## 6. Phase 0 Hot-Path Rule

Before building heavy durable learning, fix the semantic hot path.

Do not feed weak traces into the learning brain.

Phase 0 completion status (4 of 14 extracted from MeaningPerceptor):

| File | Status |
|---|---|
| `predicate_phrase_extractor.py` | ✓ Extracted (`cemm/kernel/predicate_phrase_extractor.py`) |
| `predicate_argument_aligner.py` | ❌ Still embedded in MeaningPerceptor |
| `implicit_predicate_detector.py` | ✓ Extracted (`cemm/kernel/implicit_predicate_detector.py`) |
| `interpretation_path.py` | ❌ Not yet created |
| `alternative_graph_branch.py` | ❌ Not yet created |
| `branching_graph_builder.py` | ❌ Not yet created |
| `discourse_relation_resolver.py` | ❌ Not yet created |
| `group_predicate_index.py` | ❌ Not yet created |
| `candidate_set_resolver.py` | ❌ Not yet created |
| `interpretation_path_selector.py` | ❌ Not yet created |
| `planner_branch_adapter.py` | ❌ Not yet created |
| `anaphora_resolver.py` | ✓ Extracted (`cemm/kernel/anaphora_resolver.py`) |
| `entity_salience_tracker.py` | ✓ Extracted (`cemm/kernel/entity_salience_tracker.py`) |
| `deictic_resolver.py` | ❌ Not yet created |

These must improve:

```text
predicate extraction
implicit predicates
candidate graph branching
discourse relation edges
candidate selection/rejection
cross-group anaphora and deixis
```

## 7. Foundational Primitive Rule

The UOL graph has exactly 16 canonical atom kinds:

```text
entity
process
state
relation
quality
quantity
time
place
intent
need
modality
evidence
source
permission
action
self
```

The UOL graph has exactly 16 canonical edge types:

```text
has_role
modifies
refers_to
asks_about
teaches
evaluates
causes
enables
prevents
before
after
same_as
is_a
part_of
used_for
has_property
```

Do not create domain primitives such as:

```text
PresidentAtom
WeatherAtom
LeaderAtom
CountryAtom
PersonAtom
```

Represent those as dynamic concept atoms or concept records.

## 7.5 Semantic Schema Kernel

### Central Invariant

```
Verbs do not mean actions; verbs evoke action schemas.
Nouns do not mean entities; nouns evoke entity-kind/concept candidates.
States do not mean strings; states occupy dimensions on entity slots.
Actions are operators over typed slots and produce state/relation deltas.
```

Schema JSON is canonical boot knowledge.
Runtime truth is validated graph-patch memory.

### Seven Schema Types

The Semantic Schema Kernel comprises seven schema types that form the canonical
boot knowledge for semantic interpretation:

```
EntityKindSchema        — entity kinds with native slot families
StateDimensionSchema    — state families and dimensions on entity slots
SlotSchema              — slot definitions (role, entity kind constraints, cardinality)
ActionOperatorSchema    — action operators over typed slots with preconditions + state/relation deltas
AffordanceSchema        — affordance rules derived from action operator schemas
ProjectionPolicySchema  — projection policy per slot/edge (structural vs answerable)
PatchOperationSchema    — typed patch operations (upsert_relation, upsert_state, etc.)
```

See: `newarch/semantic-schema-refactor.md` — the authoritative refactor plan.

### Schema Files

```
cemm/data/semantic_schemas/
  entity_kind_schemas.json
  state_dimension_schemas.json
  slot_schemas.json
  action_operator_schemas.json
  affordance_schemas.json
  projection_policy_schemas.json
  patch_operation_schemas.json
```

### Language Files Are Aliases Only

`action_keywords.json` and other language data files are alias layers that map
surface forms to canonical `action_key` values. They do not define slots,
preconditions, state deltas, entity kinds, or affordances. The canonical meaning
lives in `semantic_schemas/` JSON files.

### No New UOL Primitives

State deltas and relation deltas are schema-level declarations compiled into
existing UOL primitives:
- `state` atoms + `has_property` edges (for state occupancy)
- `causes` edges (for delta effects)
- Relation atoms + `has_role` edges (for relation deltas)

Do not add new atom kinds or edge types beyond the 16 + 16 defined in Section 7.

### Action Slots Are Structural By Default

Action operator slots (actor, object, target, etc.) are `structural=true`,
`answerable=false`, `projection_policy="none"` by default. Making them answerable
by default recreates the `has_role` bug where structural bindings pollute the
answerable relation frame space. Only entity-kind native slots marked
`"projection": "answerable"` produce answerable frames.

### No Backward Compatibility For Old Meaning Systems — ENFORCED

The old meaning systems (flat keyword maps, hardcoded `ACTIONS`/`STATES`/`NEEDS`
dicts, `event_schema_loader.py`, `EventSchemaStore`, `EnglishLanguageAdapter`,
`JSONLanguageAdapter`) are **deleted and replaced** by the Semantic Schema Kernel.
No backward compatibility layers exist. Old tests verifying hardcoded behavior
are deleted and replaced with schema-driven tests.

## 8. Learning Law

CEMM learns by semantic compression.

Correct:

```text
working UOL graph
-> graph patch candidates
-> validation/scoring
-> consolidation
-> concept/construction/predicate/affordance/source-policy updates
```

Incorrect:

```text
raw text -> answer
raw text -> durable fact
embedding -> final answer
generated label -> active truth
external lookup -> direct memory write
```

All durable learning must pass through graph patches.

## 9. External Knowledge Rule

Dictionaries, Wikipedia, tools, and LLM teacher outputs are sources, not
truth-oracles.

They must enter as:

```text
source atoms
evidence atoms
working graph structure
graph patch candidates
validation
consolidation
```

Never bypass source, permission, freshness, contradiction, or trust policy.

## 10. Inference Cascade

Use the cheapest valid computation first:

```text
deterministic structural operator
-> small learned component
-> parallel small agents
-> stronger arbiter
-> background induction
```

No layer may be a dead end.

Low confidence, insufficient evidence, missing required ports, stale world
state, contradiction, or permission failure must route to:

```text
ask
abstain
retrieve
escalate
quarantine
```

according to budget, risk, and permission.

## 11. Response Formation Architecture (v3.1)

The canonical response path is:

```text
ResponseSituation
-> PrimitiveGoalComposer      (language-agnostic: derives goals from semantic structure)
-> ResponseMoveComposer       (language-agnostic: composes communicative moves from goals)
-> BudgetController           (creates BudgetFrame from deadline, task size, risk)
-> CandidateGenerator         (language-agnostic: generates framing variant candidates, capped by budget)
-> PlanGate                   (language-agnostic: hard gate validation)
-> PlanRanker                 (language-agnostic: plan scoring and ranking)
-> Selector                   (realizes top K per budget, surface scores, selects best)
-> RealizationExecutor        (language-specific: renders via language modules)
-> ResponseBundle             (final output with full traceability)
```

### Package Structure

```text
cemm/response/
  types.py                        # Core types (BudgetFrame, ResponseSituation, ResponseBundle, etc.)
  response_formation_engine.py    # Orchestrates: budget → goals → moves → candidates → gate → rank → select → realize → actions → learning
  primitive_goal_composer.py      # Language-agnostic goal composition from semantic structure
  response_move_composer.py       # Language-agnostic move composition from goals
  realization_executor.py         # Re-export of RealizationExecutor for engine import path
  realization/
    types.py                      # Language-neutral IR (BoundSlot, RealizationUnit, RealizationPlan)
    executor.py                   # Language-agnostic executor: binds slots, builds plan, delegates to renderer
    planner.py                    # Builds language-neutral RealizationUnits from ResponseMoves
    slot_binder.py                # Binds semantic slots from evidence (never reads raw user text)
    languages/
      base.py                     # LanguageRenderer protocol + shared helpers
      en.py                       # English renderer
      fr.py                       # French renderer (proves multilingual from day one)
  transformers/                   # Phase 4-5: candidate generation, gating, ranking, selection
    candidate_generator.py        # Generates candidate plans with framing variants
    framing_variant.py            # Language-agnostic framing variants (minimal, direct, echo, repair, etc.)
    plan_gate_and_ranker.py       # Hard gate validation + plan scoring and ranking
    selector.py                   # Budget-aware selection of best candidate plan
cemm/budget/                      # Phase 5: budget controller, deadline parser, task size estimator, stage budget allocator
cemm/actions/                     # Phase 8: internal action proposer, authorizer, types
cemm/deliberation/                # Phase 7: deliberation planner, anytime distiller
cemm/query/                       # Phase 6: budget-aware semantic query wrapper
cemm/learning/                    # Phase 9: response/budget learning extractors, observation builder, outcome interpreter
```

### Architecture Invariants (non-negotiable)

1. **`PrimitiveGoalComposer` and `ResponseMoveComposer` are language-agnostic.**
   They must not classify English surface strings. Social, safety, memory, and
   answer behavior arrives as semantic structure: obligation kind, response act
   hints, UOL intent atoms, safety frames, write outcomes, and answer bindings.

2. **`RealizationExecutor` is language-agnostic.** It binds slots, builds a
   language-neutral `RealizationPlan`, and delegates surface text to a
   `LanguageRenderer`. Only language modules (`languages/en.py`, `languages/fr.py`)
   choose surface wording.

3. **`RealizationUnit` is the language-neutral IR.** Response moves are converted
   to `RealizationUnit`s before any language renderer sees them. This keeps
   grammar/rendering multilingual without letting language-specific rules leak
   back into response planning.

4. **`SlotBinder` never reads raw user text or instruction surface.** It binds
   from `ResponseEvidencePacket.selected_slots` and `AnswerBinding.slot_fills`
   only. If upstream semantics did not bind a slot, realization must not invent one.

5. **`WriteOutcome` must be available before response formation.** Memory-write
   claims in output depend on `write_outcome.committed` — never claim storage
   happened if the patch was not committed.

6. **Safety goals are gates, not ranker preferences.** If `safety_required` is
   true on any move, the response must include the safety refusal regardless of
   other moves.

7. **No generic fallback string may hide a failed semantic path.** If the
   response engine fails, the error must be visible — not silently replaced
   with a template string from the old `SemanticRealizer`.

8. **`RealizationContract` and `template_key` are RETIRED.** The old
   `RealizationContract` type, `template_key` field, and `SemanticRealizer`
   have been removed. The `ResponseFormationEngine` is the sole authoritative
   response path. No backward compatibility layers exist.

9. **HTML sanitization happens in `SlotBinder._clean_value`** — all slot values
   are sanitized (HTML tags stripped, script blocks removed, control chars
   removed) before reaching any language renderer.

10. **Pronoun handling is built into language renderer templates.** English
    templates use fixed pronouns (e.g., `"your {label} is {value}"` for
    `user_profile_assertion`). No regex-based pronoun shifting or framing
    prefix stripping exists in the query engine or response pipeline.

11. **Candidate ranking happens before expensive realization.** The
    `CandidateGenerator` produces framing variant plans, the `PlanGateAndRanker`
    filters by hard constraints and scores plans — all before the
    `Selector` selects the best candidate.

12. **Rejected candidates remain diagnosable.** `GateResult` objects and
    rejected `RealizedCandidate`s are preserved in `ResponseBundle.diagnostics`
    and `ResponseBundle.rejected_plans` for debugging.

13. **Framing variants are language-agnostic.** They modify `StyleVector` and
    move selection, not surface text. Only language renderers produce surface
    wording.

14. **Hard gates are binary pass/fail.** A candidate that fails any gate
    (required goals, safety, evidence, write truthfulness, no leakage, nonempty)
    is rejected — never partially accepted.

15. **Budget reduces exploration, never safety gates.** Tight budgets cap
    candidate count and realized count, but safety obligations always get
    high-risk budget with `allow_partial_answer=False`.

### Retired Path (v3.1)

```text
RealizationContract.template_key -> SemanticRealizer -> response_templates.json  [RETIRED]
```

This path has been fully removed. `SemanticRealizer`, `response_templates.json`,
and `RealizationContract` type are recycled. `SemanticQueryEngine.build_contract()`,
`_template_for_obligation()`, `_shift_pronouns_for_echo()`, `_sanitize_echo()`,
`_strip_framing_prefix()`, and `_strip_echo_discourse_markers()` are removed.
No backward compatibility layers exist.

### Phase Status

| Phase | Status | Description |
|---|---|---|
| 0 | ✅ Complete | Test contracts (golden transcript, safety, memory, query) |
| 1 | ✅ Complete | Core types + runtime reordering |
| 2 | ✅ Complete | PrimitiveGoalComposer + ResponseMoveComposer |
| 3 | ✅ Complete | Minimal RealizationExecutor (English + French) |
| 4 | ✅ Complete | CandidateGenerator, PlanGateAndRanker, Selector |
| 5 | ✅ Complete | BudgetFrame + budget-aware spend |
| 6 | ✅ Complete | Budget-aware semantic query |
| 7 | ✅ Complete | DeliberationPlanner + anytime distillation |
| 8 | ✅ Complete | Internal actions (proposer + authorizer) |
| 9 | ✅ Complete | Response/budget learning |

See `newarch/cemm-v3.1-lean-implementation-plan.md` for the full plan.

Realization strategy should be cheapest-first:

```text
deterministic composition (current)
-> extractive
-> neural
-> abstain
```

Text is invalid if it cannot be traced back to the working graph, selected
evidence, and response/action plan.

## 12. No Rules

Do not:

```text
use English-specific string matching as the primary architecture
fix transcript symptoms with late-stage phrase cases instead of repairing the meaning substrate
turn `OperationalMeaningCompiler` into a bag of conversational regexes
hardcode open-domain fallback strings to hide model failure
produce final answer text before interpretation and planning
write durable memory directly from perception or retrieval
promote generated labels without validation
let dense/neural output bypass permission and evidence
store every working graph forever as primary memory
add new primitive atom kinds for ordinary domain concepts
bury learned knowledge inside meaning_perceptor.py
collapse candidate meanings too early
ignore candidate sets, graph branches, anaphora, or discourse edges
hide limitations to make a demo look good
hardcode action/state/need meaning in Python dicts instead of Semantic Schema Kernel
add new UOL edge types for state deltas — use existing primitives (state atoms + causes edges)
make action operator slots answerable by default — they are structural
keep backward compatibility layers for old meaning systems — replace them
classify English surface strings in PrimitiveGoalComposer or ResponseMoveComposer
fall back to SemanticRealizer when ResponseFormationEngine throws — SemanticRealizer is retired, surface the error
use template_key as the authoritative response selection mechanism — template_key is retired
claim memory was stored when WriteOutcome.committed is false
bypass safety gates in favor of ranker preferences
add English-specific logic to language-agnostic response stages
read raw user text in SlotBinder — bind from evidence only
put pronoun shifting or HTML sanitization in language-agnostic stages
use tests that assert only final text while ignoring broken graph, state, or contract structure
```

Seed heuristics are allowed only as explicit fallback scaffolding.

## 13. Scoring And Ranking

Ranking must consider:

```text
relevance
trust
confidence
salience
recency
frame validity
temporal containment
permission validity
risk
cost
contradiction
freshness requirements
```

Permission validity must be real, not hardcoded `True`.

Rejected candidates should remain observable in diagnostics, candidate sets,
branch metadata, or tests where practical.

## 14. Storage And Source Of Truth

Working graphs are temporary.

Durable memory should store:

```text
compressed semantic records
concept atoms
operational ports
predicate schemas
construction operators
causal affordances
source policies
patch journal entries
sparse high-value exemplars
```

Do not use runtime artifacts as architecture guidance:

```text
*.sqlite3
*.log
__pycache__/
generated JSONL
old patch files
```

## 15. Code Review Checklist

Before closing a task, verify:

- [ ] The change follows the current v4.2 architecture, not older v3-only instructions.
- [ ] The pre-code trace identifies the earliest wrong meaning substrate before any fix is made.
- [ ] `MeaningPerceptPacket` exists before graph construction.
- [ ] `UOLGraph` exists before runtime resolution, planning, patch extraction, or learning.
- [ ] Candidate meanings are preserved instead of collapsed prematurely.
- [ ] Entity grounding, salience, anaphora, deixis, and temporal/session context were checked when behavior depends on cross-turn meaning.
- [ ] Predicate extraction is not limited to action/state surface matches when the task touches interpretation.
- [ ] Discourse relations create graph structure when the task touches group relations.
- [ ] Anaphora/deixis are handled or explicitly marked unresolved when the task touches cross-group reference.
- [ ] State occupancy, state deltas, and state transmutations are used when behavior depends on entity state or state change.
- [ ] Durable learning happens only through `GraphPatch`.
- [ ] Concept, construction, port, and affordance behavior lives behind the proper lattice/resolver/predictor seams.
- [ ] Domain concepts are not added as new primitive atom kinds.
- [ ] External knowledge enters through source/evidence/graph-patch flow.
- [ ] Planning uses graph structure, candidate sets, and evidence policy, not raw text alone.
- [ ] Realization is traceable to a plan, selected evidence, and graph state.
- [ ] Tests cover affected graph-packet invariants.
- [ ] Known limitations are documented honestly instead of hidden behind fallback strings.
- [ ] No new UOL atom kinds or edge types beyond the 16 + 16 in Section 7.
- [ ] Action/state meaning comes from Semantic Schema Kernel, not hardcoded dicts.
- [ ] Language files are alias layers only — no schema info in action_keywords.json.
- [ ] Action slots are structural by default, not answerable.
- [ ] State deltas are compiled into existing UOL primitives (state atoms + causes edges), not new edge types.
- [ ] Response formation: `PrimitiveGoalComposer` and `ResponseMoveComposer` are language-agnostic — no English surface string classification.
- [ ] Response formation: `RealizationExecutor` delegates to language renderers — no English wording in the executor itself.
- [ ] Response formation: `SlotBinder` binds from evidence only — never reads raw user text.
- [ ] Response formation: `RealizationUnit` IR keeps language-specific rules out of response planning.
- [ ] Response formation: no fallback to `SemanticRealizer` when `ResponseFormationEngine` throws — `SemanticRealizer` is retired, surface the error.
- [ ] Response formation: `WriteOutcome.committed` is checked before claiming memory was stored.
- [ ] Response formation: safety moves are gates, not ranker preferences.
- [ ] Response formation: `ResponseBundle` carries full traceability (moves, evidence, diagnostics).
- [ ] Response formation: HTML sanitization in `SlotBinder._clean_value` strips script blocks and tags.
- [ ] Response formation: old tests using `SemanticRealizer` directly are replaced with pipeline-level tests via `SeededSystem`.
- [ ] Tests assert the semantic substrate and contract shape, not only the final response text.

