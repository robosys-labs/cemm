# CEMM Core Loop Runtime

Status: implementation contract  
Supersedes: implicit 3.3 loop assumptions  
Aligned with: `consolidated_architecture.md` v4.1 and `3.3-uol-graph-architecture.md`

## 1. Contract

CEMM's runtime loop is:

```text
Signal
-> MeaningPerceptor
-> MeaningPerceptPacket
-> MeaningHypothesis / CandidateInterpretation sets
-> MeaningGraphBuilder
-> UOLGraph
-> seed concept resolution
-> seed port resolution
-> seed affordance prediction
-> ActResolutionPlanner
-> GraphPatch candidates
-> async consolidation
```

The loop must preserve this separation:

| Layer | Object | Lifetime | May Mutate Durable Memory |
|---|---|---:|---|
| Perception | `MeaningPerceptPacket` | one turn/window | no |
| Hypothesis | `MeaningHypothesis`, `CandidateInterpretation` | one turn/window | no |
| Working graph | `UOLGraph` | one turn/window | no |
| Runtime resolution | `ConceptResolution`, `PortBinding`, `AffordancePrediction` | one turn/window | no |
| Planning | `ActResolutionPlan` | one response decision | no |
| Learning boundary | `GraphPatch` | queued candidate | not directly |
| Consolidation | concept/construction/predicate/affordance lattices | durable | yes, after validation |

## 2. Stage Responsibilities

### 2.1 MeaningPerceptor

Input:

```text
Signal + ContextKernel
```

Output:

```text
MeaningPerceptPacket
```

Responsibilities:

```text
normalize
segment into meaning groups
identify candidate atoms
preserve competing interpretations
preserve nested/subordinate group relations
identify predicate phrases
identify candidate outcomes
preserve surface evidence
build working UOL graph through MeaningGraphBuilder
export graph training example
```

Forbidden:

```text
durable memory writes
direct response routing
hardcoded concept-specific slot filling
verified current-world claims
```

### 2.2 MeaningGraphBuilder

Input:

```text
MeaningPerceptPacket
```

Output:

```text
UOLGraph
```

Responsibilities:

```text
create source/time/evidence/permission atoms
create content atoms
create structural edges
preserve meaning groups
preserve candidate alternatives
attach construction matches
attach concept-resolution records
attach port-binding records
attach affordance predictions
attach candidate sets to candidate subgraphs
extract graph patch candidates
```

The builder may create seed records so the current runtime can function before
the full learned lattices exist. Seed records must be marked as candidates or
runtime observations.

When concept, construction, port, or affordance lattice implementations are
available, the builder must call those collaborators instead of the seed
fallbacks.

Forbidden:

```text
store UOLGraph as durable memory
collapse compound concepts into opaque atoms when structure is visible
write facts directly to memory
turn effects into static fields
```

## 3. UOLGraph

`UOLGraph` is the temporary semantic workbench.

Required contents:

```text
atoms
edges
groups
candidate_sets
construction_matches
concept_resolutions
port_bindings
affordance_predictions
patch_candidates
trace
```

`candidate_sets` must be populated from perception-layer hypotheses whenever
the same surface span has competing interpretations.

Each candidate set should preserve:

```text
hypothesis id
candidate interpretation ids
candidate atom ids
candidate subgraph atom/edge ids
selected candidate ids
rejected candidate ids, once resolved
```

The graph may be exported for training, debugging, or sparse exemplars.

The graph itself should not become the durable semantic database.

## 4. Runtime Resolution Records

### 4.1 ConceptResolution

Connects an atom to a dynamic concept candidate.

Valid states include:

```text
exact_alias
construction_hint
parent_inferred
nearest_fingerprint
new_candidate
typed_candidate
operational_context
unresolved
```

`person`, `country`, `organization`, `leader`, `president`, `cold`, and
`weather` are concept keys, not atom kinds.

### 4.2 PortBinding

Represents a dynamic operational-port binding.

Example:

```text
owner_atom = president
port_key = holder
filler_atom = Donald Trump
```

The binding is runtime evidence.

It is not a hardcoded slot rule.

### 4.3 AffordancePrediction

Represents a possible contextual effect.

Example:

```text
cold + holder=user_environment + intensity=high
-> comfort_or_warmth_may_be_relevant
```

This is not:

```text
cold.possible_effect = discomfort
```

## 5. GraphPatch Boundary

All durable learning must flow through:

```text
GraphPatch -> validation/scoring -> consolidation -> lattice update
```

Allowed patch targets:

```text
concept_lattice
construction_lattice
predicate_schema
causal_affordance
episodic_trace
source_policy
discard
```

No component before consolidation may call a durable memory write as a side
effect of interpreting a graph.

## 6. Planner Contract

`ActResolutionPlanner` consumes:

```text
conversation acts
meaning groups
meaning hypotheses
candidate sets
UOL atoms and edges
concept resolutions
port bindings
affordance predictions
atom outcomes
graph patch candidates
retrieval/evidence state
```

It outputs:

```text
reply obligations
answer tasks
memory update plans
graph patch references
tool/retrieval requirements
response contract
```

It must distinguish:

| Input | Correct Runtime Meaning |
|---|---|
| `how do you do?` / `you?` | social/self-directed turn |
| `it is cold where I am` | user/environment state report |
| `can you tell the weather?` | fresh-world query requiring a source/tool |
| `a president is a leader of a country` | teaching graph patch candidate |
| `Donald Trump is current president of USA` | sourced current-world assertion requiring freshness before verified use |
| `bye` | social closing |

If a command or question contains unresolved lexical ambiguity, the planner may
prefer a clarification obligation over a direct answer/action.

## 7. Current Seed Implementation

The current implementation includes a seed version of the loop:

| File | Current Role |
|---|---|
| `cemm/types/uol_graph.py` | Working graph plus graph-local runtime records. |
| `cemm/types/graph_patch.py` | Durable learning patch boundary. |
| `cemm/types/meaning_percept.py` | Perception packet plus core-loop trace and patch candidates. |
| `cemm/kernel/meaning_perceptor.py` | Segmentation, candidate atomization, graph build trigger. |
| `cemm/kernel/meaning_graph_builder.py` | Working graph construction, seed resolution, patch extraction. |
| `cemm/kernel/act_resolution_planner.py` | Graph-aware response, retrieval, and memory-patch planning. |

The seed implementation is intentionally deterministic and conservative.

Future learned modules should replace seed heuristics behind the same object
contracts, not bypass them.

## 8. Acceptance Checks

Implementation is drifting if any of these become true:

```text
UOLGraph is treated as durable semantic memory
person/country/president/cold appear as AtomKind values
planner learns directly from graph interpretation without GraphPatch
meaning_graph_builder stores facts
one utterance is forced into one intent
one ambiguous surface is forced into one atom before graph construction
subordinate clauses are flattened as unrelated peer groups
leader of country becomes one opaque atom when leader/domain can be split
possible effects are stored as static fields
fresh-world questions and user state reports both become abstentions
```
