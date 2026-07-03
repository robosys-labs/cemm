# Core Loop Update Manifest

This update makes the new CEMM semantic core loop explicit in code and docs.

## Updated Core Files

| File | Change |
|---|---|
| `cemm/types/uol_graph.py` | Converts `UOLGraph` into a temporary semantic workbench with graph-local groups, candidate sets, construction matches, concept resolutions, port bindings, affordance predictions, graph patch candidates, candidate subgraph metadata, and clone/merge/prune/select utilities. |
| `cemm/types/graph_patch.py` | Adds the explicit durable learning boundary: `GraphPatch`, `PatchOperation`, allowed operation types, inverse-operation metadata, conflict grouping, and merge helpers. |
| `cemm/types/meaning_percept.py` | Adds core-loop stage/trace fields, graph patch candidate export, `MeaningHypothesis`, `CandidateInterpretation`, hierarchical group fields, `PermissionAtom`, and `SelfAtom`. |
| `cemm/types/conversation_act.py` | Adds pragmatic act compatibility types expected by the planner. |
| `cemm/types/__init__.py` | Exports the new graph, patch, and conversation-act types. |
| `cemm/kernel/meaning_graph_builder.py` | Populates the new graph-local records, decomposes teaching phrases like `leader of country`, converts meaning hypotheses into multi-candidate graph candidate sets, supports optional lattice collaborators, and extracts patch candidates instead of writing memory. |
| `cemm/kernel/meaning_perceptor.py` | Records the explicit core-loop trace, generates seed ambiguity hypotheses, avoids first-group leakage on unmatched atoms, preserves nested/subordinate group metadata, improves punctuation/connective splitting, and exposes graph patch candidates after graph build. |
| `cemm/kernel/act_resolution_planner.py` | Carries graph patch candidates into planning, uses patch IDs for teaching/memory plans, consumes atom outcomes, consumes candidate-set ambiguity, can clarify ambiguous commands/questions, and dedupes per predicate. |
| `cemm/kernel/port_resolver.py` | Adds a lattice-backed operational-port resolver so port bindings are scored through concept ports, inherited parent ports, role evidence, group salience, and atom confidence. |
| `cemm/kernel/affordance_predictor.py` | Adds a seed affordance matcher over the working graph, replacing one-off builder triggers with an injectable causal-affordance boundary. |
| `cemm/kernel/semantic_cpu.py` | Adds the first explicit semantic CPU orchestrator that wires perception, graph building, lattice resolution, planning, graph-patch extraction, and optional consolidation. |
| `cemm/memory/concept_lattice.py` | Adds an in-memory concept lattice with aliases, inheritance, operational ports, concept resolution, and concept-lattice patch application. |
| `cemm/memory/construction_lattice.py` | Adds an in-memory construction lattice that emits construction matches and absorbs construction-observation patches. |
| `cemm/memory/episodic_trace_store.py` | Adds a sparse exemplar store for high-value graph traces retained by patch consolidation. |
| `cemm/learning/graph_patch_extractor.py` | Adds a dedicated boundary for extracting durable learning candidates from a working graph. |
| `cemm/learning/concept_consolidator.py` | Adds validation, merge, and application logic for graph patches before they update seed memory structures. |

## Updated Docs And Tests

| File | Change |
|---|---|
| `docs/core_loop_runtime.md` | New implementation contract for the signal-to-graph-patch runtime loop. |
| `docs/README.md` | Adds the core loop runtime doc to the architecture map. |
| `docs/missing_runtime_implementation_plan.md` | Documents the newly added seed runtime modules and the remaining non-seed learning systems still needed. |
| `docs/operational_ports_and_dynamic_slot_resolution.md` | Removes `possible_effect` from the cold port list and routes it through affordance prediction. |
| `tests/test_operational_meaning_spine.py` | Adds regression checks for decomposed teaching graphs and graph-patch-aware planning. |
| `tests/test_core_loop_hypotheses.py` | Adds regression checks for ambiguity hypotheses, graph candidate sets, nested subordinate groups, planner ambiguity consumption, and per-predicate obligations. |
| `tests/test_missing_runtime_modules.py` | Adds regression checks for inherited concept ports, lattice-backed graph building, patch consolidation, and semantic CPU turn execution. |

## Verification

Completed:

```text
python -m compileall cemm tests
isolated builder teaching-decomposition check
isolated planner graph-patch teaching path check
direct import execution of tests/test_core_loop_hypotheses.py
direct import execution of tests/test_missing_runtime_modules.py
```

Blocked:

```text
pytest -q tests/test_operational_meaning_spine.py tests/test_frame_binder.py
```

Reason:

```text
pytest is not installed in the workspace.
The direct test harness also encounters a pre-existing missing cemm.store module
when importing retrieval_executor from the old retrieval test.
```
