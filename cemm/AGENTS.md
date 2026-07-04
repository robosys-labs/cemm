# CEMM Agent Instructions

Status: governing implementation guide  
Audience: AI coding agents, reviewers, and maintainers working on CEMM  
Supersedes: older v3.0/SLC-only local plans when they conflict with the current architecture

## 1. Canonical Source Of Truth

Use these files as the active implementation contract, in this order:

1. `AGENTS.md`
2. `newarch/consolidated_architecture.md`
3. `newarch/core_loop_runtime.md`
4. `newarch/full_cemm_learning_brain_missing_pieces.md`
5. `newarch/missing_runtime_implementation_plan.md`
6. `newarch/3.3-uol-graph-architecture.md`
7. `cemm/tests/test_acceptance.py`

Superseded design docs are archived at `docs/archive/newarch_superseded/`.
Use them as background reference only — they are not active architecture contracts.

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

Status: **seed-complete for pipeline integration (Phases 1-2 done)**
- `Pipeline.run()` no longer builds `SemanticEventGraph` — `UOLGraph` is the sole working graph
- All downstream consumers read from `UOLGraph` via backward-compat properties on the `UOLGraph` dataclass
- `RememberOperator` routes claims through `ClaimWriter` which creates `GraphPatch` objects for consolidation
- `ConceptConsolidator` has compression-gain scoring, 4-state lifecycle (candidate→typed→operational→consolidated), decay, counterexamples, fingerprint matching
- 4 Phase 0 hot-path modules extracted from `MeaningPerceptor` (reduced from 1395→1300 lines)
- `CausalInference` reads from `UOLGraph` atoms/edges directly
- 315 tests pass, 0 fail

**Still missing from full architecture:**
- 5 durable architecture types (`ConceptAtom`, `OperationalPort`, `PredicateSchema`, `CausalAffordance`, `ConstructionAtom`) — replaced by simpler records
- `SemanticKernelRuntime` as authoritative single entrypoint (Pipeline.run() still mixed)
- `PatchValidator` write barrier (direct durable writes still escape GraphPatch)
- Remaining 10 Phase 0 hot-path modules still embedded in `MeaningPerceptor`
- `SemanticCPU.run_turn()` as orchestrator (graph_builder called directly by Pipeline)
- Dynamic self-knowledge (still static `self_knowledge.json`)
- Knowledge ingestion, training infrastructure, adapters, synthesis modules

Do not overclaim that the full learning brain is done.

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

