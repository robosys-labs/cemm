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
2. `newarch/semantic-schema-refactor.md` (semantic schema kernel refactor plan)
3. `newarch/causal-runtime-wiring-fix.md` (master fix plan — BLOCKER #1)
4. `newarch/consolidated_architecture.md`
5. `newarch/3.3-uol-graph-architecture.md`
6. `newarch/core_loop_runtime.md`

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

Status: **schema kernel refactor complete; causal-runtime wiring partially addressed**
- `Pipeline.run()` delegates to `SemanticKernelRuntime.run_turn()` — single authority achieved
- `UOLGraph` is the sole working graph (with adjacency index for O(degree) edge lookups)
- `SemanticSchemaKernel` is the single canonical source for action/state/need/entity meaning
- `SchemaBackedLanguageAdapter` replaces all old language adapters — delegates to schema kernel
- `SemanticKernelRuntime.run_turn()` has 11 steps: perceive, build, attend, compile, schedule, teach, compile relations, query, realize, plan, extract/validate/commit patches
- `PatchValidator` and `PatchCommitter` enforce graph-patch-only durable writes
- `SessionStore` restores/persists conversation, user affect, topic, discourse state across turns
- `EntitySalienceTracker` tracks entity salience across turns
- `DurableSemanticStore` stores and retrieves relation frames
- `MeaningPerceptor` properly wired with `schema_kernel` and `graph_builder` via constructor

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
| Realize | response realization layer, currently outside the core seed modules |
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

## 11. Realization Rule

Final text should be realized from a response/action plan and selected evidence,
not directly from raw input text.

Current seed implementation has `ActResolutionPlan`.

Future implementation should add a first-class answer graph or realization
contract.

Realization strategy should be cheapest-first:

```text
template
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
- [ ] `MeaningPerceptPacket` exists before graph construction.
- [ ] `UOLGraph` exists before runtime resolution, planning, patch extraction, or learning.
- [ ] Candidate meanings are preserved instead of collapsed prematurely.
- [ ] Predicate extraction is not limited to action/state surface matches when the task touches interpretation.
- [ ] Discourse relations create graph structure when the task touches group relations.
- [ ] Anaphora/deixis are handled or explicitly marked unresolved when the task touches cross-group reference.
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

