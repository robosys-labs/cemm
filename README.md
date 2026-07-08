# CEMM

**A trainable event-centered memory model for context-aware agents.**

CEMM is a pure-Python implementation of a meaning-first language architecture (v3.1) — a semantic runtime with a unified Semantic Schema Kernel, UOL working-graph system, graph-patch learning, budget-aware response formation, internal action authorization, and online learning. CEMM operates on foundational meaning atoms/primitives instead of matrices, enabling native language understanding and online learning.

## Core Primitives

| Primitive | Meaning | Main Question |
|---|---|---|
| `Signal` | Something observed | What happened? |
| `Entity` | Something identified | What thing is this? |
| `Claim` | Something believed | What is asserted? |
| `Model` | A reusable structure or process | How does this work? |
| `Action` | Something done or considered | What should happen next? |
| `Self` | The system's persistent self-state | What am I, and how am I changing? |

### Semantic Schema Kernel

The Semantic Schema Kernel is the single canonical source for action, state, need, and entity meaning. It comprises seven schema registries loaded from JSON files:

| Registry | Purpose |
|---|---|
| `EntityKindRegistry` | Entity kinds with native slot families and hierarchy |
| `StateDimensionRegistry` | State families and dimensions on entity slots |
| `SlotRegistry` | Slot definitions (role, entity kind constraints, cardinality) |
| `ActionOperatorRegistry` | Action operators over typed slots with preconditions + state/relation deltas |
| `AffordanceRegistry` | Affordance rules derived from action operator schemas |
| `ProjectionPolicyRegistry` | Projection policy per slot/edge (structural vs answerable) |
| `PatchOperationRegistry` | Typed patch operations (upsert_relation, upsert_state, etc.) |

### Meaning Atoms

| Atom | Meaning |
|---|---|
| `ReferentAtom` | Entity detected in signal (NER, capitalization, pronoun) |
| `ActionAtom` | Event/action predicate with schema slots |
| `StateAtom` | Reported state of an entity |
| `RelationAtom` | Relationship between entities |
| `NeedAtom` | Expressed need or goal |
| `OutcomeAtom` | Predicted state change from an event |
| `ValenceAtom` | Entity-relative favorability evaluation |

## Project Structure

```
cemm/
├── types/              # Foundational atoms + runtime packets (dataclasses)
├── kernel/             # Semantic runtime: MeaningPerceptor, MeaningGraphBuilder,
│                       #   SemanticCPU, SemanticKernelRuntime, ActResolutionPlanner,
│                       #   SemanticSchemaKernel, AffordancePredictor, etc.
├── response/           # v3.1 Response Formation Engine
│   ├── response_formation_engine.py  # Canonical budget-aware response path
│   ├── primitive_goal_composer.py    # Language-agnostic goal composition
│   ├── response_move_composer.py     # Language-agnostic move composition
│   ├── realization_executor.py       # Re-export of realization subsystem
│   ├── realization/                  # Slot binder, planner, language renderers
│   └── transformers/                 # Candidate generation, gating, ranking, selection
├── budget/             # Budget controller, deadline parser, task size estimator
├── actions/            # Internal action proposer + authorizer (Phase 8)
├── deliberation/       # Deliberation planner + anytime distiller (Phase 7)
├── query/              # Budget-aware semantic query wrapper (Phase 6)
├── learning/           # Response/budget learning extractors (Phase 9)
├── data/
│   ├── semantic_schemas/  # Canonical schema JSON files (7 registries)
│   └── languages/         # Language alias packs (pronouns, deictics, states, needs)
├── confidence/         # Log-odds math and scoring formulas
├── causal/             # Causal inference + simulation engine
├── memory/             # Concept/construction lattices, episodic trace, durable store
└── tests/              # Test suite including golden pipeline + phase tests
```

## Quick Start

```bash
cd C:\dev\cemm

# Run tests
python -m pytest cemm/tests -q

# Start interactive session
python -m cemm
```

## Running

```bash
python -m cemm                    # Interactive chat
python -m cemm --eval "What is my favorite database?"  # Single query
python -m cemm --db path/to/db.sqlite                   # Persistent store
python -m cemm.web_demo           # Browser demo at http://127.0.0.1:5000
```

## Architecture (v3.1 Semantic Runtime)

```
Signal
  -> MeaningPerceptor (normalize, segment, atomize via SchemaBackedLanguageAdapter)
  -> MeaningPerceptPacket
  -> MeaningGraphBuilder (schema-driven atom/edge creation, state deltas, entity kind validation)
  -> UOLGraph (with adjacency index for O(degree) edge lookups)
  -> SemanticAttentionController (focus selection)
  -> SemanticProgramCompiler (compile semantic program)
  -> SemanticObligationScheduler (schedule obligations)
  -> RelationFrameCompiler (compile relation frames with projection policies)
  -> SemanticQueryEngine (build + execute queries)
  -> ActResolutionPlanner (reply obligations + memory updates + answer tasks)
  -> GraphPatchExtractor -> PatchValidator -> PatchCommitter
  -> SafetyFrameDetector
  -> ResponseFormationEngine:
       BudgetController -> PrimitiveGoalComposer -> ResponseMoveComposer
       -> CandidateGenerator -> PlanGateAndRanker -> Selector
       -> RealizationExecutor (language-specific rendering)
       -> InternalActionProposer -> InternalActionAuthorizer
       -> ResponseBudgetLearningExtractor
  -> OutputStateUpdater
```

See `cemm/AGENTS.md` for the governing implementation guide and `cemm/newarch/cemm-v3.1-lean-implementation-plan.md` for the full architecture plan.

## Tests

167 tests covering:
- Semantic Schema Kernel (7 registries, schema lookup, multilingual alias resolution)
- Golden pipeline tests (end-to-end tests for schema-driven meaning flow)
- Response Formation Engine (phases 0-9: budget, candidates, gating, ranking, realization, actions, learning)
- UOLGraph construction, adjacency index, patch candidates
- MeaningPerceptor, MeaningGraphBuilder, language adapter
- Affordance prediction, relation frame compilation
- Causal inference (prediction, simulation, closure)
- Pipeline (signal persistence, kernel construction, full end-to-end)
- Safety refusals, memory write truthfulness, role label leak prevention
