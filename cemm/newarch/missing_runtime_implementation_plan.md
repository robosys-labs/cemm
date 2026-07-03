# Missing Runtime Implementation Plan

Status: seed implementation added  
Scope: concept lattice, construction lattice, port resolver, affordance predictor, graph patch extraction, consolidation, semantic CPU orchestration

## 1. Problem

The architecture described:

```text
working graph -> graph patches -> concept/construction/predicate/affordance lattices
```

but the code previously had only the working graph and seed graph-patch types.

This left these gaps:

```text
no concept lattice implementation
no construction lattice implementation
no lattice-backed port resolver
no affordance predictor module
no graph patch extractor boundary
no graph patch consolidator
no semantic CPU orchestrator
```

## 2. Files Added

| File | Purpose |
|---|---|
| `cemm/memory/concept_lattice.py` | In-memory concept lattice with aliases, parent traversal, inherited ports, concept resolution, and concept-lattice patch application. |
| `cemm/memory/construction_lattice.py` | In-memory construction matcher and construction observation consolidation. |
| `cemm/memory/episodic_trace_store.py` | Sparse high-value graph exemplar store. |
| `cemm/kernel/port_resolver.py` | Lattice-backed dynamic operational-port resolver. |
| `cemm/kernel/affordance_predictor.py` | Seed affordance rule matcher over bound working graphs. |
| `cemm/learning/graph_patch_extractor.py` | Explicit graph-patch extraction boundary. |
| `cemm/learning/concept_consolidator.py` | Validates, merges, and applies graph patches to seed stores. |
| `cemm/kernel/semantic_cpu.py` | Wires perceptor, builder, lattices, resolver, predictor, planner, extractor, and consolidator. |

## 3. Seed Vs Learned Boundary

These modules are not the final learned system.

They are the first runnable contract.

| Component | Seed Behavior | Future Learned Upgrade |
|---|---|---|
| Concept lattice | Alias lookup, parent traversal, patch-updated ports. | Embeddings/fingerprints, contradiction tracking, source reliability, decay. |
| Construction lattice | Group-type matching. | Learned form-signature and graph-pattern operators. |
| Port resolver | Scores kind, role edge, parent concept, salience, confidence. | Constraint solver over concept inheritance, source/evidence policy, temporal fit, contradiction penalties. |
| Affordance predictor | Rule matching for seed patterns. | Learned causal affordance lattice with counterexamples and probabilistic activation. |
| Consolidator | Confidence threshold and patch merge. | Validation queues, conflict arbitration, source trust, decay, consolidation scheduling. |
| Semantic CPU | Deterministic orchestration. | Multi-hypothesis graph branching, beam search, replay training, async consolidation. |

## 4. Runtime Flow

```text
Signal
-> MeaningPerceptor
-> MeaningGraphBuilder(lattices + port resolver + affordance predictor)
-> UOLGraph
-> GraphPatchExtractor
-> ActResolutionPlanner
-> ConceptConsolidator
-> ConceptLattice / ConstructionLattice / EpisodicTraceStore
```

## 5. Acceptance Checks

The seed implementation must satisfy:

```text
ConceptLattice.resolve(atom) returns ConceptResolution
ConceptLattice.ports_for(concept) includes inherited parent ports
LatticePortResolver.resolve_graph(graph) produces PortBinding records
AffordancePredictor.predict(graph) produces AffordancePrediction records
ConceptConsolidator.consolidate(patches) applies concept and construction patches
SemanticCPU.run_turn(...) returns percept + plan + optional consolidation
```

## 6. Remaining Required Work

The next serious implementation pass should add:

```text
cemm/types/concept_atom.py
cemm/types/operational_port.py
cemm/types/predicate_schema.py
cemm/types/causal_affordance.py
cemm/types/construction_atom.py
cemm/learning/predicate_schema_inducer.py
cemm/learning/causal_affordance_inducer.py
cemm/learning/construction_inducer.py
durable persistence for lattices
source trust and contradiction policy
async consolidation queue
probabilistic graph branching over candidate subgraphs
```

Do not bypass the current patch boundary when adding those systems.
