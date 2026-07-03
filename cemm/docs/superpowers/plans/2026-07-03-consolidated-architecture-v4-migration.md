# Consolidated Architecture v4.1 Migration Plan

## Executive Summary

This plan replaces the existing CEMM core loop (types, kernel, learning, memory, runtime,
pipeline) with the new consolidated architecture defined in `cemm/newarch/`. The new
architecture treats language as **probabilistic**, **multi-interpretation** perception —
one utterance produces multiple MeaningGroup trees, each group forks into multiple
MeaningHypotheses (act + lexical + structural ambiguity), and UOLGraphs are temporary
working graphs that never pretend one utterance = one graph.

**Governing principles** (from `consolidated_architecture.md` v4.1):
- 16 fixed kernel atom kinds only; domain concepts go in `UOLAtom.key`, never `UOLAtom.kind`
- UOLGraph is a **temporary working graph** (one turn/window). Durable learning only enters
  through `GraphPatch` candidates
- Graphs must never pretend one utterance = one intent, one sentence = one predicate, one
  term = one fixed meaning, one graph = one durable truth
- The perceptor must NOT route responses, mutate memory, or hardcode concept-specific slot
  filling
- Ports are dynamic atom-owned interfaces, not static semantic slots
- Constructions are learned operators, not regex patterns
- Multi-language from day one — segmentation/atomization must not be English-only heuristics

## Architecture Overview

### Pipeline (from `core_loop_runtime.md`)

```
Signal
  → Normalize
    → Segment
      → ConstructionMatch
        → Atomize
          → BuildWorkingGraph
            → ResolveConcepts
              → ResolvePorts
                → Inherit
                  → PredictAffordances
                    → Compare / Verify
                      → PlanAct
                        → ExtractGraphPatches
                          → ConsolidateAsync
```

### Data Flow

```
Signal → MeaningGroup[](parent/child trees) → MeaningHypothesis[](per group)
  → CandidateInterpretation[](with UOLGraph branches)
    → Lattice-queried UOLGraph → Plan(AtomicAction[]) → GraphPatch[(candidates)
      → ConceptLattice / ConstructionLattice / AffordanceLattice (async consolidation)
```

### Key Type Changes

| Old Type | New Type | Notes |
|---|---|---|
| MeaningAtom.kind | UOLAtom.kind | 16 fixed kernel kinds only |
| MeaningAtom.concept | UOLAtom.key | Domain concepts go here |
| MeaningPacket | MeaningPacket (rewritten) | Now carries MeaningGroup trees + hypotheses |
| — | MeaningGroup | Parent/child group structure for clause segmentation |
| — | MeaningHypothesis | One per interpretation branch, per group |
| — | CandidateInterpretation | Full graph + metrics for one meaning path |
| — | UOLGraph | Temporary working graph for current turn |
| — | GraphPatch | Durable learning boundary (diff + metadata) |
| — | PermissionAtom | Permission constraints as atoms |
| — | SelfAtom | Self-referential atoms |
| SemanticEventGraph | UOLGraph (replaces) | Working graph type |
| SemanticEvent | UOLAtom (replaces) | Atom type in graph |
| SemanticRelation.hardcoded types | Ports (dynamic resolution) | No more hardcoded relation types per domain |
| SemanticSlot | Port (replaces) | Dynamic, resolved through lattice |

## Migration Phases

---

### Phase 0: Type System Foundation

**Goal**: Install the new type hierarchy without breaking existing imports.

**Files to create/modify**:
1. `cemm/types/meaning_percept.py` ← copy from `cemm/newarch/meaning_percept.py`
   - Fix import paths (change `from .meaning_percept` → `from ..types.meaning_percept` in downstream)
   - Add PermissionAtom, SelfAtom, MeaningGroup, MeaningHypothesis, CandidateInterpretation if not present
2. `cemm/types/uol_graph.py` ← copy from `cemm/newarch/uol_graph.py`
   - Wire UOLGraph into type system
3. `cemm/types/graph_patch.py` ← copy from `cemm/newarch/graph_patch.py`
   - Wire GraphPatch into type system
4. `cemm/types/__init__.py` — add exports for new types

**Dead fields to fix** (in perceptor, addressed in Phase 1 but types must exist first):
- `packet.affordances` — populate with predicted affordance list
- `packet.outcomes` — populate with (prob, outcome) pairs
- `packet.valences` — populate per-atom valence

**Integration points**:
- Old `MeaningPacket` references in: `cemm/types/meaning_types.py`, `cemm/operators/`, `cemm/kernel/`, `cemm/registry/`, `cemm/synthesis/`, `cemm/training/`, `cemm/confidence/`, `cemm/latent/`
- Each consumer must be audited and updated to handle new group/hypothesis structure
- Backward-compat shim on `MeaningPacket`: if no groups present, single flat group with single hypothesis

**Tests**: `tests/test_meaning_percept_types.py`, `tests/test_uol_graph.py`, `tests/test_graph_patch.py`

**Risk**: Old code referencing `MeaningAtom.concept` as string will break — need compat property on UOLAtom.

**Verification**: `rtk pytest tests/ -x` — all existing tests pass with type shim.

---

### Phase 1: MeaningPerceptor Replacement

**Goal**: Replace `cemm/kernel/meaning_perceptor.py` with the newarch version that produces
MeaningGroup trees and MeaningHypotheses.

**Files**:
1. `cemm/kernel/meaning_perceptor.py` — full replacement from `cemm/newarch/meaning_perceptor.py`
   - Wire `process_input` → `_group_meaning` → `_hypothesis_generation` pipeline
   - Fix dead fields: populate `packet.affordances`, `packet.outcomes`, `packet.valences`
   - Replace `_predict_affordances` (currently 3 hardcoded cases) with lattice query stub
   - Ensure `semantic_relations` maps properly populate on packet
   - Wire cross-group discourse edges (discourse_tags, subordinating connectives → semantic relations)
2. `cemm/operators/meaning_processor.py` — update to call new perceptor signature

**Key upgrades to verify** (the newarch file already has these):
- Multi-group splitting via subordinating connectives (because/since/when/if/although/while/after/before/unless/until/so that/in order to)
- Comma-splitting with predicative checks for non-restrictive clauses
- MeaningHypothesis generation per group (one primary, branch interpretations)
- Cross-group anaphora resolution (pronoun→antecedent edges across groups)
- `MeaningPacket` groups list with parent/child hierarchy

**Integration points**:
- `ContextKernel` — perceptor receives context, must pass multi-hypothesis context
- `LexemeMemory` — lexeme matching still needed (kept from ~/learning/)
- `NERTagger` — entity tagging still needed
- `SurfaceTagger` — surface pattern matching still needed
- `LanguageAdapter` — multi-language abstraction already wired in

**Tests**: `tests/test_meaning_perceptor.py` — multi-group inputs, hypothesis forking, dead field population

**Risk**: The new perceptor is ~1351 lines; `_resolve_concepts` is a decision tree, not yet lattice-driven — this is acceptable for Phase 1 but marked for Phase 5 upgrade.

**Verification**: `rtk pytest tests/test_meaning_perceptor.py -x` — multi-group test cases pass; single-group backward compat passes.

---

### Phase 2: MeaningGraphBuilder Replacement

**Goal**: Replace `cemm/kernel/meaning_graph_builder.py` with the newarch version that
builds CandidateInterpretations and resolves them through lattice queries.

**Files**:
1. `cemm/kernel/meaning_graph_builder.py` — replacement from `cemm/newarch/meaning_graph_builder.py`
   - Wire `build_interpretations` → generates `CandidateInterpretation[]` per MeaningHypothesis
   - Each CI gets its own `UOLGraph` (forked by hypothesis)
   - Cross-group discourse edges: create `discourse_relation` edges between group graphs
   - Wire lattice query stubs: `_resolve_concepts`, `_resolve_ports`, `_predict_affordances`
   - Wire `_rank_and_select_interpretations` with scoring metrics
   - Stub `_extract_graph_patches` (full impl in Phase 6)

**Gaps to close in this phase**:
- Add cross-group anaphora edges (currently not created in graph_builder)
- Add cross-group discourse edges from perceptor's connective map
- Wire `CandidateInterpretation.metrics` (compression_gain, coherence, novelty)
- Wire `CandidateInterpretation.rejected_paths` for backtracking

**Integration points**:
- `ConceptLattice` (stub in Phase 2, full in Phase 5) — `lookup(key)` → `ConceptNode[]`
- `ConstructionLattice` (stub) — `match(surface)` → `ConstructionMatch[]`
- `AffordanceLattice` (stub) — `predict(atom, context)` → `Affordance[]`
- `EpisodicTraceStore` (stub) — `find_similar(graph)` → `Trace[]`

**Tests**: `tests/test_meaning_graph_builder.py` — CI generation, ranking, cross-group edges

**Risk**: `_resolve_concepts` is a decision tree, not lattice-driven — this limits concept
generalization until Phase 5. Acceptable as intermediate state.

**Verification**: `rtk pytest tests/test_meaning_graph_builder.py -x`

---

### Phase 3: ActResolutionPlanner Replacement

**Goal**: Replace `cemm/kernel/act_resolution_planner.py` with the newarch version that
produces plans from CandidateInterpretations, handles merges and path selection.

**Files**:
1. `cemm/kernel/act_resolution_planner.py` — replacement from `cemm/newarch/act_resolution_planner.py`
   - Wire `resolve_and_plan` → receives candidate interpretations, produces plans
   - Add hypothesis merging: when multiple hypotheses converge on same action, merge evidence
   - Add path selection: choose primary path, keep alternatives for backtracking
   - Wire `_plan_actions` → sequence of AtomicAction from UOLGraph
   - Wire `_apply_permissions` → PermissionAtom constraint checking
   - Wire `_apply_self_constraints` → SelfAtom identity constraints

**Gaps to close**:
- CandidateInterpretation sets exist in newarch code but `_select_candidate_path` / `_merge_hypotheses` are stubs — implement merge heuristics
- Cross-group plan ordering: plans should respect discourse structure (subordination, coordination)
- Ambiguity retention: rejected paths should be persisted for learning feedback

**Integration points**:
- `DecisionRouter` — planner output feeds router (existing, in `cemm/kernel/`)
- `RegistryManager` — actions may register new meanings
- `TrainingManager` — plan outcomes feed training

**Tests**: `tests/test_act_resolution_planner.py` — hypothesis merge, path selection, cross-group ordering

**Verification**: `rtk pytest tests/test_act_resolution_planner.py -x`

---

### Phase 4: Pipeline Integration

**Goal**: Rewrite `cemm/kernel/pipeline.py` to use the new pipeline stages from
`core_loop_runtime.md`. Wire the semantic CPU loop.

**Files**:
1. `cemm/kernel/pipeline.py` — rewrite pipeline stages
   - Replace existing ~20 stages with new 16-stage pipeline
   - Keep backward-compat entry points (`process_input`, `process_batch`) that wrap new pipeline
   - Wire `__main__.py` integration point — dispatch to new pipeline

**New pipeline stages** (from `core_loop_runtime.md`):
1. `Signal` — receive and validate input signal
2. `Normalize` — normalize text (unicode, casing, token normalization)
3. `Segment` — clause-level segmentation → MeaningGroup tree
4. `ConstructionMatch` — match learned constructions → ConstructionMatch[]
5. `Atomize` — produce UOLAtom[] from constructions + segments
6. `BuildWorkingGraph` — produce UOLGraph from atoms + discourse edges
7. `ResolveConcepts` — lattice query: concept disambiguation
8. `ResolvePorts` — lattice query: port binding (was slot filling)
9. `Inherit` — propagate constraints through graph
10. `PredictAffordances` — lattice query: what can each atom do
11. `Compare / Verify` — compare to episodic memory, verify coherence
12. `PlanAct` — produce AtomicAction[] plan
13. `ExtractGraphPatches` — extract GraphPatch candidates for learning
14. `ConsolidateAsync` — submit patches to consolidation queue

**Integration**: `cemm/__main__.py` — update to call new `Pipeline.process()` instead of old stages.

**Tests**: `tests/test_pipeline.py` — end-to-end pipeline tests with multi-interpretation inputs

**Risk**: Largest single phase. Recommend staging pipeline rollout:
- Sub-phase 4a: Signal → Normalize → Segment → Atomize → BuildWorkingGraph (types + perceptor path)
- Sub-phase 4b: ResolveConcepts → ResolvePorts → Inherit → PredictAffordances (graph builder path)
- Sub-phase 4c: Compare/Verify → PlanAct (planner path)
- Sub-phase 4d: ExtractGraphPatches → ConsolidateAsync (learning path, stubs only)

**Verification**: `rtk pytest tests/test_pipeline.py -x`; `rtk python -m cemm --input "test input"`

---

### Phase 5: Lattice Infrastructure

**Goal**: Implement the three lazy-computed lattices (concept, construction, affordance)
and the episodic trace store. These are the knowledge backbone that the perceptor,
graph builder, and planner query but do NOT manage.

**Files to create**:
1. `cemm/lattice/__init__.py` — lattice module
2. `cemm/lattice/concept_lattice.py`
   - `ConceptNode` structure: key, exemplars, operational_ports, affordances, parents, children
   - `ConceptLattice` class: `lookup(key, context)` → `ConceptNode[]` ranked by relevance
   - Wire `ConceptLattice.add_candidate()` for async consolidation entry
   - Implementation: lazy-computed from flat key→properties, with inference chains
3. `cemm/lattice/construction_lattice.py`
   - `ConstructionNode` structure: surface_pattern, semantic_template, frequency, confidence
   - `ConstructionLattice`: `match(surface, context)` → `ConstructionMatch[]`
   - `ConstructionLattice.induce()` — pattern induction from GraphPatches
4. `cemm/lattice/affordance_lattice.py`
   - `AffordanceNode`: subject_kind, object_kind, effect_signature, probability
   - `AffordanceLattice`: `predict(atom, context_graph)` → `Affordance[]`
   - Implementation: causal model over past GraphPatch outcomes
5. `cemm/lattice/episodic_store.py`
   - `EpisodicTrace`: UOLGraph snapshot, outcome, timestamp, patch_ref
   - `EpisodicTraceStore`: `find_similar(graph, k)` → `EpisodicTrace[]`
   - `store(trace)` — append to episodic buffer
6. `cemm/lattice/port_resolver.py`
   - Port binding resolution through concept lattice
   - No hardcoded slots — all resolved dynamically

**Integration points**:
- Phase 1 perceptor calls: `construction_lattice.match(segment)`
- Phase 2 graph builder calls: `concept_lattice.lookup(key)`, `affordance_lattice.predict(atom)`
- Phase 6 consolidation calls: `construction_lattice.induce(patch)`, `concept_lattice.add_candidate(patch)`
- Phase 2 episodic similarity: `episodic_store.find_similar(graph)`

**Tests**: `tests/test_concept_lattice.py`, `tests/test_construction_lattice.py`,
`tests/test_affordance_lattice.py`, `tests/test_episodic_store.py`,
`tests/test_port_resolver.py`

**Risk**: Lattice design decisions (lazy vs eager, indexing strategy, inference depth) have
significant performance impact. Start with simple dict-backed implementations and profile.

**Verification**: `rtk pytest tests/lattice/ -x`

---

### Phase 6: Learning & Consolidation Pipeline

**Goal**: Implement GraphPatch extraction from pipeline runs, async consolidation into
lattices. This is the only durable learning path — patches in, lattice updates out.

**Files to create/modify**:
1. `cemm/kernel/graph_patch_extractor.py`
   - `extract_patches(uol_graph, plan, outcome)` → `GraphPatch[]`
   - Compute compression_gain for promotion decisions
   - Generate diff structure (added/removed/modified atoms, relations, ports)
2. `cemm/learning/concept_consolidator.py`
   - `consolidate_concept(patch)` → merge into ConceptLattice
   - Follow concept state machine: unknown_surface → candidate → typed_candidate →
     operational → consolidated
   - Promotion to consolidated requires compression_gain threshold + recurrence
3. `cemm/learning/construction_inducer.py`
   - `induce_construction(patches)` → extract surface/semantic patterns
   - Group by similar UOLGraph structure, extract generalization
4. `cemm/learning/predicate_schema_inducer.py`
   - `induce_predicate_schema(patches)` → generalize predicate argument structure
   - Extract port-binding patterns for recurring predicates
5. `cemm/learning/causal_affordance_inducer.py`
   - `induce_affordance(patches)` → extract causal patterns
   - Build/update affordance predictions from observed outcomes

**Async consolidation queue** (in pipeline Phase 4d):
- GraphPatches produced by pipeline are queued for async processing
- Consolidation runs on separate thread/process
- Lattice updates are atomic — readers see consistent state

**Concept State Machine** (from `concept_lattice_resolution.md`):
```
unknown_surface → candidate → typed_candidate → operational → consolidated
```
- unknown_surface: surface form observed, no concept yet
- candidate: hypothesized concept from context
- typed_candidate: concept type assigned (person, action, place, etc.)
- operational: usable in resolution, may have low confidence
- consolidated: high confidence, compression gain proven, recurrence satisfied

**Promotion decision**:
- `compression_gain = (bits_without_concept - bits_with_concept) / bits_without_concept`
- Threshold: 0.15 for candidate→operational, 0.30 for operational→consolidated
- Must also satisfy: recurrence across N separate contexts (configurable, default 3)

**Tests**: `tests/test_graph_patch_extractor.py`, `tests/test_concept_consolidator.py`,
`tests/test_construction_inducer.py`, `tests/test_predicate_schema_inducer.py`,
`tests/test_causal_affordance_inducer.py`

**Verification**: `rtk pytest tests/learning/ -x`

---

### Phase 7: Documentation & Cleanup

**Goal**: Archive old architecture docs, promote newarch markdown files to authoritative
position, clean up dead modules.

**Files**:
1. `cemm/docs/archive/` — move old architecture docs:
   - `architecture.md` → `archive/architecture_v3.md`
   - `cemm_foundational_fixes.md` → `archive/`
   - `cemm_training_architecture.md` → `archive/`
   - `cemm_v3_1_operational_meaning_spine.md` → `archive/`
2. `cemm/docs/consolidated_architecture.md` — copy from `newarch/consolidated_architecture.md`
3. `cemm/docs/core_loop_runtime.md` — copy
4. `cemm/docs/uol_graph_architecture.md` — copy
5. `cemm/docs/semantic_compression.md` — copy
6. `cemm/docs/construction_grammar.md` — copy
7. Remove old newarch/ directory (or keep as reference if desired)

**Dead module cleanup**:
- Remove `cemm/types/meaning_types.py` if fully replaced (check for lingering imports)
- Remove `cemm/types/types_core.py` old types no longer referenced
- Clean up `cemm/operators/` modules that referenced old types
- Remove unused import workarounds in perceptor/graph_builder/planner

**Tests**: Full regression suite `rtk pytest tests/ -x` — verify nothing broken by cleanup

**Risk**: Removing old types may break operator modules not yet updated. Must audit all
imports first.

**Verification**: `rtk pytest tests/ -x`

---

## Dependency Graph

```
Phase 0 (Types) ────> Phase 1 (Perceptor) ──> Phase 4 (Pipeline) ──> Phase 6 (Learning)
                  └──> Phase 2 (Graph Builder) ┘                      │
                  └──> Phase 3 (Planner) ─────┘                       │
                                                                      v
                                                              Phase 5 (Lattices)
                                                                      │
                                                                      v
                                                              Phase 6 (Learning)
                                                                      │
                                                                      v
                                                              Phase 7 (Cleanup)
```

- Phase 0 is prerequisite for all phases.
- Phases 1-3 can run in parallel after Phase 0 (they depend on types only).
- Phase 4 depends on 1-3 completing.
- Phase 5 is independent until Phase 6 (can start after Phase 0 or in parallel with 1-3).
- Phase 6 depends on Phase 4 (for GraphPatch source) and Phase 5 (for lattice targets).
- Phase 7 is last.

## Critical Path Items

1. **Phase 0**: Getting UOLGraph + GraphPatch types correct — everything builds on these.
   Must fix import paths (`..types.meaning_percept` not `.meaning_percept`) immediately.
2. **Phase 1**: Fixing dead fields (affordances/outcomes/valences) — these are consumed by
   graph builder, planner, and training. If left dead, downstream phases have no data.
3. **Phase 4d**: Queue-based async consolidation — must be designed correctly to avoid
   race conditions between pipeline (writer) and consolidator (reader). Recommendation:
   producer-consumer pattern with atomic batch updates.
4. **Phase 5**: Lattice query API design — the perceptor, graph builder, and planner all
   query lattices with different patterns. API must be stable before Phase 1-2 integration.

## Identified Gaps (from newarch code analysis)

| Gap | Location | Severity | Phase |
|---|---|---|---|
| `re` imported but unused | `meaning_perceptor.py:1` | Low | 1 |
| `packet.affordances`/`outcomes`/`valences` never populated | `meaning_perceptor.py` → `MeaningPacket` | High | 1 |
| Cross-group discourse edges never created | `meaning_graph_builder.py` | High | 2 |
| Cross-group anaphora not implemented | `meaning_graph_builder.py` | Medium | 2 |
| `_predict_affordances` only 3 hardcoded cases | `meaning_perceptor.py` | Medium | 1 (stub) / 5 (full) |
| `_resolve_concepts` is decision tree not lattice | `meaning_perceptor.py` | Medium | 2 (stub) / 5 (full) |
| Lattice/resolver params typed as `Any` | `meaning_graph_builder.py` | Medium | 5 |
| `SituationFrame` accepted but unused in planner | `act_resolution_planner.py` | Low | 3 |
| Planner has candidate sets but no merge/path-select | `act_resolution_planner.py` | High | 3 |
| Segmentation still English-rule-based | `meaning_perceptor.py:_segment_clauses` | Medium | 1 (improve) |
| All lattice implementations missing | (docs only, no code) | High | 5 |
| No async consolidation queue | (docs only, no code) | High | 6 |
| Old newarch/ import paths use `.meaning_percept` | All 6 .py files | High | 0 |

## Testing Strategy

Each phase must pass its own unit tests before moving to the next phase. End-to-end
tests run in Phase 4 (pipeline). The full regression suite runs in Phase 7.

### Test categories:
1. **Unit tests** — per module, per phase
2. **Integration tests** — cross-module (e.g., perceptor→graph_builder)
3. **End-to-end tests** — full pipeline with multi-interpretation inputs
4. **Regression tests** — existing behaviors preserved

### Key test scenarios:
- Single-group, single-interpretation input (backward compat)
- Multi-group input (subordinating connectives, comma-split clauses)
- Multi-interpretation input (lexical ambiguity, structural ambiguity)
- Hypothesis forking and merging
- GraphPatch extraction and consolidation
- Cross-group discourse relation creation
- Cross-group anaphora resolution
- Multi-language input (non-English clause segmentation)

## Rollback Strategy

Each phase creates a git commit. If a phase causes regression:
- `rtk git revert <commit>` for the affected phase
- Fix the issue in a new branch, rebase dependent phases
- Maintain backward compat shims through Phase 3 (removed in Phase 7)

## Committed Files

| Phase | File | Action |
|---|---|---|
| 0 | `cemm/types/meaning_percept.py` | Replace with newarch version |
| 0 | `cemm/types/uol_graph.py` | Create |
| 0 | `cemm/types/graph_patch.py` | Create |
| 0 | `cemm/types/__init__.py` | Update exports |
| 1 | `cemm/kernel/meaning_perceptor.py` | Replace with newarch version |
| 2 | `cemm/kernel/meaning_graph_builder.py` | Replace with newarch version |
| 3 | `cemm/kernel/act_resolution_planner.py` | Replace with newarch version |
| 4 | `cemm/kernel/pipeline.py` | Rewrite pipeline stages |
| 4 | `cemm/__main__.py` | Update entry point |
| 5 | `cemm/lattice/__init__.py` | Create |
| 5 | `cemm/lattice/concept_lattice.py` | Create |
| 5 | `cemm/lattice/construction_lattice.py` | Create |
| 5 | `cemm/lattice/affordance_lattice.py` | Create |
| 5 | `cemm/lattice/episodic_store.py` | Create |
| 5 | `cemm/lattice/port_resolver.py` | Create |
| 6 | `cemm/kernel/graph_patch_extractor.py` | Create |
| 6 | `cemm/learning/concept_consolidator.py` | Create |
| 6 | `cemm/learning/construction_inducer.py` | Create |
| 6 | `cemm/learning/predicate_schema_inducer.py` | Create |
| 6 | `cemm/learning/causal_affordance_inducer.py` | Create |
| 7 | `cemm/docs/` | Archive + promote new docs |
