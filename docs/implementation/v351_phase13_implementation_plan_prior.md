# CEMM v3.5.1 — Phase 13 Exhaustive Implementation Plan

**Target:** typed activation graph and recurrent semantic attractor solver  
**Depends on:** completed Phase 9–12 canonical CSIR path  
**Canonical anchors:** `AGENTS.md`, `ARCHITECTURE.md`, `CEMM_CORE_MATHS.md`, `CORE_ISSUES.md`, `CORE_LOOP.md`, `RUNTIME_PLAN.md`, `ISSUES_TO_AVOID.md`, `IMPLEMENTATION_PLAN.md`  
**Roadmap contract:** Phase 13 implements `SemanticActivationNode`, `TypedMessageEdge`, `HardConstraintMask`, `ActivationTrace`, `ConvergenceAssessment`, and `DynamicsParameterSet`; starts from deterministic immutable parameters; then performs exact pruning → sparse recurrent propagation → inhibition → convergence/budget → semantic-class clustering. Required message families are lexical, construction, port/role, type, identity, scope, time/aspect, context, state, causal expectation, discourse, and multimodal. Budget exhaustion produces partial cognition, never fabricated certainty.

---

## 1. Objective

Replace the Phase-10 deterministic one-pass Stage-6/7 bridge with the first canonical recurrent semantic dynamics implementation while preserving every v3.5.1 architectural invariant.

Phase 13 must make semantic competition **dynamic but still exact-authority bounded**:

```text
Stage 5 exact CSIR candidate classes
→ typed sparse activation graph
→ exact hard-constraint masking
→ recurrent typed message passing
→ inhibition / competition
→ convergence or explicit budget frontier
→ canonical semantic-equivalence clustering
→ Stage 7 SemanticAttractorSet
```

The recurrent solver may rank, strengthen, weaken, inhibit, and propagate support among already licensed semantic hypotheses. It may **not** invent semantic definitions, semantic ports, identities, causal mechanisms, state transitions, discourse acts, or language meanings that were not present in the exact candidate/evidence/authority substrate.

The Phase-10 deterministic solver remains only a debugging oracle/shadow comparator. It must not remain a second co-authoritative semantic brain.

---

## 2. Non-negotiable invariants

### 2.1 One semantic representation

All semantic state after Stage 5 is canonical CSIR v2. No UOL graph, legacy response graph, language-specific semantic AST, or parallel hidden ontology may participate in recurrent dynamics.

### 2.2 Exact authority remains upstream of dynamics

Dynamics may only operate on:

- exact Stage-5 `CSIRCandidateSet`;
- cycle-pinned `AuthoritySnapshotV351`;
- exact immutable `DynamicsParameterArtifact` / `DynamicsParameterSet` pins;
- evidence and grounding artifacts already present in the cycle workspace;
- typed frontiers and hard-constraint traces.

A learned or tuned parameter cannot grant semantic authority.

### 2.3 Hard constraints dominate soft activation

A hard-invalid hypothesis must be masked before recurrent competition and can never be revived by support accumulation.

```text
hard-invalid ≠ low probability
hard-invalid = non-executable / zero admissibility
```

Soft dynamics operates only inside the admissible hypothesis space.

### 2.4 No winner-equals-truth shortcut

The highest activation is not automatically world truth, admitted belief, referent identity, or common ground.

Stage 6/7 produces semantic attractors and unresolved alternatives. Stage 8+ still owns discourse re-abstraction and Stage 9 still owns epistemic admission.

### 2.5 Preserve ambiguity and partial meaning

Close semantic alternatives must survive according to an explicit calibrated margin/budget. Budget exhaustion must emit:

- retained partial graph where possible;
- open variables;
- unresolved semantic classes;
- typed frontier refs;
- convergence reason refs.

It must never convert “not solved” into “false,” “unknown concept means X,” or an arbitrary top-1 answer.

### 2.6 Language agnosticism

No recurrent edge constructor or update equation may branch on English words, punctuation strings, grammatical labels assumed to have universal semantic meaning, or concept names such as `person`, `happy`, `eat`, `name`, etc.

Language-specific evidence can enter only through the typed form/construction/semantic contributions already produced by earlier stages.

### 2.7 Bounded sparse computation

No all-pairs semantic graph scan on the hot path. Build indexed adjacency once per activation graph and propagate only over explicit typed sparse edges.

No runtime-global lock may be held while computing activation updates.

### 2.8 Immutable parameter identity

Every dynamics pass must identify the exact parameter artifact(s) used by:

- authority pin;
- family;
- revision;
- content hash;
- immutable numeric values;
- calibration/competence evidence refs.

Parameters cannot be silently edited in place.

### 2.9 Deterministic replay under identical pins

Given identical:

- CSIR candidate set;
- evidence/grounding artifacts;
- exact authority generation;
- exact dynamics parameter pins;
- runtime budgets;

Stage 6/7 must produce deterministic semantic-class results and trace fingerprints.

Floating-point implementation must use deterministic ordering and bounded stable reductions.

---

# 3. Phase 13 subphases

## Phase 13.0 — Baseline audit and contract freeze

Before implementation, re-audit the merged Phase 12 head.

### Required checks

1. Confirm Stage 5 emits one candidate per canonical semantic equivalence class.
2. Confirm `CSIRCandidateSet` pins exact authority/kernel ABI.
3. Confirm Stage 5 retains:
   - closure proof refs;
   - hard-constraint trace refs;
   - evidence refs;
   - unresolved refs;
   - prior score.
4. Confirm Phase-10 deterministic dynamics remains isolated behind the Stage-6/7 service slots.
5. Confirm no Stage 8–12 code depends on the concrete internal type of `ActivationGraph.payload` beyond the documented Stage-7 contract.
6. Confirm Phase 12 does not interpret Stage-7 support as epistemic truth.
7. Add a baseline snapshot test so future Phase-13 changes cannot silently widen the Stage-6/7 ABI.

### Exit

A written `phase13_contract_freeze.json` listing exact input/output fields and authoritative service slots.

---

## Phase 13.1 — Canonical typed activation model

Create a dedicated module, recommended:

```text
cemm/v350/dynamics/model_v351.py
```

### 13.1.1 `SemanticActivationNode`

Represents one activation-bearing unit. Stable structural node kinds only; domain concepts remain data.

Recommended fields:

```text
node_ref
node_kind
semantic_ref
semantic_class_fingerprint
candidate_refs
initial_activation
current_activation
hard_masked
message_family_membership
exact_authority_pins
evidence_refs
frontier_refs
```

Node kinds should be structural, for example:

```text
candidate_class
semantic_term
semantic_application
port_binding
semantic_variable
qualifier
scope_embedding
coordination
grounding_hypothesis
discourse_signal
multimodal_signal
```

Do not encode learned/domain ontology classes as Python enums.

### 13.1.2 `TypedMessageEdge`

Fields:

```text
edge_ref
family
source_node_ref
target_node_ref
parameter_name_ref
base_weight
polarity
hard_dependency
exact_authority_pins
evidence_refs
```

Edges are directional and typed. Their existence must come from explicit structural relations/evidence, not name similarity.

### 13.1.3 `HardConstraintMask`

Fields:

```text
mask_ref
target_node_refs
allowed
constraint_ref
constraint_pin
proof_ref
evidence_refs
reason_refs
```

The mask layer must be compiled before soft propagation.

### 13.1.4 `DynamicsParameterSet`

A cycle-ready immutable aggregation of exact `DynamicsParameterArtifact` values.

Required behavior:

- exact unique parameter family pins;
- no duplicate parameter names inside a family;
- finite values only;
- explicit defaults are authority data, never hidden Python constants for semantic behavior;
- content fingerprint covering all exact pins/values;
- validation against `AuthoritySnapshotV351`.

Runtime safety constants such as absolute maximum iterations may remain kernel budgets, but semantic scoring weights/thresholds must be parameter artifacts.

### 13.1.5 `TypedActivationGraph`

Replace opaque deterministic payload with typed immutable graph data:

```text
activation_graph_ref
nodes
edges
hard_masks
candidate_class_index
semantic_node_index
adjacency_index
parameter_set_ref
authority_generation
authority_fingerprint
semantic_authority_snapshot_fingerprint
kernel_abi_fingerprint
proof_refs
frontier_refs
```

Indexes must be immutable tuples/maps safe for read-only concurrent use.

---

## Phase 13.2 — Activation graph compiler

Recommended module:

```text
cemm/v350/dynamics/compiler_v351.py
```

Implement `SemanticActivationGraphCompilerV351`.

### Inputs

- `CSIRCandidateSet`;
- grounding candidate set and ambiguity evidence where needed;
- form/construction evidence references already linked to candidate derivations;
- semantic closure candidates;
- cycle-pinned semantic authority snapshot;
- exact dynamics parameter set;
- runtime budgets.

### Algorithm

1. Validate all candidate authority/kernel fingerprints equal Stage-0 pins.
2. Materialize candidate-class nodes.
3. Materialize shared canonical semantic substructure nodes using canonical refs/fingerprints.
4. Reuse nodes for semantically identical shared structures rather than duplicating per candidate.
5. Build explicit membership edges candidate ↔ semantic structure.
6. Build typed evidence edges only where upstream artifacts provide exact linkage.
7. Build exact hard masks from Stage-5 traces and structural incompatibilities.
8. Build competition groups for mutually exclusive candidate classes and incompatible bindings.
9. Freeze sparse adjacency.
10. Emit compiler proof refs and graph fingerprint.

### Important

Do not infer semantic edges merely because two strings, schema refs, or node names look similar.

---

# 4. Required typed message families

All 12 roadmap message families must be represented in the graph/solver API from day one. A family may have zero edges for a cycle when no licensed evidence exists; it may not be replaced by an English-specific shortcut.

## 4.1 Lexical

Carries support from exact form/sense/contribution evidence into semantic candidate structure.

Must preserve lexical ambiguity. One form may support multiple sense-linked semantic classes.

## 4.2 Construction

Carries support from exact `ConstructionProgramRecord` derivations and construction evidence.

Construction support cannot invent semantic port bindings absent from compiled programs.

## 4.3 Port/role

Propagates compatibility/incompatibility through exact semantic formal ports and grounded fillers.

No grammatical subject/object → semantic actor/affected hardcoding.

## 4.4 Type

Propagates exact type compatibility and inherited type closure evidence.

Hard type violations become masks where authority says they are impossible; uncertain type evidence remains soft/frontiered.

## 4.5 Identity

Propagates grounding/coreference support from bounded candidate identities.

Stage-3 local winner must remain a prior, not identity truth.

## 4.6 Scope

Propagates compatibility for quantification, negation, modality, reported content, quotations and other exact scope embeddings.

Scope mismatch must be visible in trace output.

## 4.7 Time/aspect

Propagates exact temporal/aspect compatibility supplied by semantic qualifiers or authorized projections.

No tense-token hardcoding in the kernel.

## 4.8 Context

Propagates actual/reported/hypothetical/planned/etc. context compatibility without promoting non-actual content to actual belief.

## 4.9 State

Propagates compatibility among state dimensions/values and referent state-space projections already licensed upstream.

Phase 13 does not execute transitions; it only scores semantic interpretation consistency.

## 4.10 Causal expectation

Carries bounded semantic expectation from exact causal-mechanism authority when available.

It must remain expectation evidence, not a state mutation. Full causal propagation belongs to later phases.

## 4.11 Discourse

Carries support from discourse wrappers, prior turns, open-question structure, correction cues and system-output occurrence evidence already represented semantically.

## 4.12 Multimodal

Carries calibrated support from typed multimodal grounding artifacts.

Raw modality values must not enter as uncalibrated arbitrary activation boosts.

---

# 5. Phase 13.3 — Exact pruning and hard-mask compiler

Recommended module:

```text
cemm/v350/dynamics/masks_v351.py
```

Implement `HardConstraintMaskCompilerV351`.

### Hard-mask sources

- failed exact closure proof;
- missing required semantic definition/port authority;
- impossible port cardinality;
- incompatible node kind;
- exact type prohibition;
- exact context/permission prohibition;
- contradictory required exact bindings;
- invalid scope graph;
- stale authority/parameter pin;
- explicit denied use authorization.

### Rules

- Mask creation requires proof/reason refs.
- Soft score cannot override mask.
- A masked candidate remains trace-visible for debugging but is not propagated as admissible meaning.
- If all candidates are masked, Stage 7 returns a typed unresolved/blocked semantic frontier, not an arbitrary fallback.

---

# 6. Phase 13.4 — Deterministic immutable parameter baseline

Create a minimum candidate parameter package, recommended:

```text
cemm/v350/dynamics/minimum_parameters_v351.py
```

It must be a **candidate authority compiler**, like Phase-12 minimum authority compilers, not an implicit runtime constant table.

### Parameter categories

At minimum:

```text
initial-prior scaling
family-specific message gains
positive/negative propagation bounds
inhibition strength
competition temperature or equivalent canonical control
activation clipping bounds
convergence epsilon
ambiguity retention margin
maximum stable-attractor count
frontier retention thresholds
```

Do not invent parameter semantics that conflict with `CEMM_CORE_MATHS.md`; map the implementation to the exact canonical equations/names defined there during coding.

### Requirements

- immutable exact pins;
- competence/calibration refs;
- deterministic values;
- no random initialization;
- no training in Phase 13;
- release tooling must explicitly publish the selected parameter artifact into a new authority generation.

---

# 7. Phase 13.5 — Sparse recurrent propagation engine

Recommended module:

```text
cemm/v350/dynamics/solver_v351.py
```

Implement `RecurrentSemanticDynamicsV351`.

### Per-iteration sequence

```text
1. apply hard masks
2. gather incoming typed messages through sparse adjacency
3. compute family-specific bounded contributions
4. aggregate deterministically
5. apply inhibition/competition
6. update activation using canonical core-maths equation
7. re-apply masks/clamps
8. calculate convergence delta
9. append bounded trace summary
10. stop on convergence or budget
```

### Determinism

- iterate nodes and edges in stable canonical order;
- avoid unordered set/dict reduction in numeric summation;
- use a stable summation strategy where needed;
- no RNG;
- identical inputs/pins must replay identically.

### Complexity target

Per iteration should be approximately proportional to:

```text
O(active_nodes + active_edges)
```

not all candidate pairs or all repository vocabulary.

---

# 8. Phase 13.6 — Inhibition and semantic competition

Competition must occur only among hypotheses with a structural reason to compete.

### Competition groups

Examples:

- distinct identity candidates for the same mention;
- incompatible fillers for one singular semantic port;
- mutually exclusive canonical interpretations of the same evidence span;
- contradictory exact context/scope assignments;
- alternate semantic classes derived from the same construction path.

### Forbidden shortcut

Do not globally normalize every semantic node into one softmax distribution. Independent propositions or subgraphs may coexist.

### Ambiguity

If two interpretations remain close after convergence, both remain attractors according to the exact ambiguity-retention policy.

---

# 9. Phase 13.7 — Convergence, budgets and traces

Extend/replace current `ActivationTrace` and `ConvergenceAssessment` with typed Phase-13 fields while maintaining runtime ABI compatibility where possible.

## `ActivationTrace`

Must be bounded. Do not store every dense node value for every iteration by default.

Recommended trace content:

```text
trace_ref
iteration_count
initial/final graph fingerprints
per-iteration convergence delta summary
masked candidate refs
retained candidate-class activations
major message-family contribution summaries
competition/inhibition refs
parameter-set ref
proof refs
frontier refs
```

Optional detailed trace may exist behind an explicit audit/debug budget.

## `ConvergenceAssessment`

Required distinctions:

```text
CONVERGED
BUDGET_EXHAUSTED_PARTIAL
NO_ADMISSIBLE_CANDIDATE
OSCILLATION_DETECTED
NUMERIC_INVALID
AUTHORITY_INVALIDATED
```

A numeric NaN/Inf is a fail-closed error/frontier, never coerced to zero.

---

# 10. Phase 13.8 — Semantic-class clustering and Stage-7 stabilizer

Recommended module:

```text
cemm/v350/dynamics/stabilizer_v351.py
```

Implement `RecurrentAttractorStabilizerV351`.

### Required behavior

1. Cluster final hypotheses by canonical semantic fingerprint.
2. Merge only semantically equivalent classes; do not merge because strings or local refs match.
3. Preserve exact fingerprints/derivation refs for debugging.
4. Compute class support from the recurrent state using the canonical core-maths rule.
5. Retain close alternatives according to exact parameter/budget policy.
6. Build `partial_meaning` only from compatible retained structure.
7. Preserve all open variables and unresolved frontiers.
8. Emit `SemanticAttractorSet` with exact authority, parameter pins and convergence assessment.

### No truth promotion

Attractor support is interpretation support only.

---

# 11. Phase 13.9 — Runtime integration

Update canonical runtime defaults:

```text
Stage 6 recurrent_semantic_solver
    DeterministicMeaningDynamics
→   RecurrentSemanticDynamicsV351

Stage 7 semantic_attractor_stabilizer
    DeterministicAttractorStabilizer
→   RecurrentAttractorStabilizerV351
```

### Exact parameter loading

Stage 0 must pin the dynamics parameter artifacts selected for the pass. Stage 6 must refuse:

- missing required parameter family;
- duplicate family;
- stale content hash;
- parameter pin not in immutable authority snapshot;
- mismatch between cycle pins and activation graph pins.

### Service replacement

Injected signed services may replace the canonical solver only if they satisfy the same v3.5.1 runtime ABI and exact authority checks.

---

# 12. Deterministic baseline oracle/shadow comparator

Move Phase-10 deterministic behavior into a clearly named oracle module/configuration.

Recommended:

```text
cemm/v350/dynamics/oracle_v351.py
```

Purpose:

- unit-test expected exact-composition behavior;
- debug recurrent regressions;
- optional shadow comparison in non-authoritative diagnostics.

It must not:

- publish competing Stage-7 outputs;
- override recurrent results;
- silently fallback when recurrent solver fails;
- become a second semantic authority path.

A recurrent failure produces a frontier/failure, not deterministic fallback.

---

# 13. Performance and concurrency design

## 13.1 Bounds

Add runtime budgets for:

```text
maximum activation nodes
maximum typed edges
maximum recurrent iterations
maximum competition-group size
maximum retained attractor classes
maximum detailed trace entries
maximum propagation work units
```

All exhaustion is explicit and typed.

## 13.2 Memory

- immutable graph structures per cycle;
- no unbounded process-global activation cache;
- cache only authority-generation-safe reusable indexes;
- generation-keyed cache replacement, not accumulation across generations.

## 13.3 Locks

No global lock around graph compilation or recurrent propagation.

Small locks are acceptable only for bounded cache ownership swaps.

## 13.4 Authority races

If authority/read generation changes before a stage read, existing runtime replay rules apply. A Stage-6 graph cannot be repinned mid-pass.

---

# 14. Test plan

## 14.1 Unit tests — model validation

- duplicate node/edge refs rejected;
- invalid message family rejected;
- non-finite activation/weights rejected;
- duplicate parameter family/name rejected;
- stale exact parameter pin rejected;
- hard mask without proof/reason rejected;
- adjacency references missing nodes rejected.

## 14.2 Hard-mask tests

- exact hard-invalid candidate never revived by strong positive messages;
- all-masked set returns no-admissible frontier;
- soft negative evidence does not become a hard mask.

## 14.3 Message-family tests

One structural test for each of the 12 required families proving:

- correct edge construction from typed upstream evidence;
- no edge without licensed evidence;
- family contribution appears in trace;
- no raw word/concept-name switch.

## 14.4 Ambiguity tests

- two close interpretations remain two attractors;
- stronger coherent evidence resolves them when margin is exceeded;
- Stage-3 local grounding winner alone does not force identity;
- ambiguous coreference remains partial.

## 14.5 Scope/context tests

- actual vs hypothetical remain distinct;
- reported/quoted content does not gain actual-world support merely through recurrence;
- negation/scope mismatch remains explicit.

## 14.6 Partial/budget tests

- max-iteration exhaustion returns `BUDGET_EXHAUSTED_PARTIAL`;
- partial graph preserves known substructure;
- open variables/frontiers preserved;
- no fabricated top-1 certainty.

## 14.7 Canonical equivalence tests

- alpha-renamed local refs cluster into same semantic class;
- reordered unordered bindings normalize to same class;
- semantically different scope/qualifiers do not collapse.

## 14.8 Synthetic vocabulary renaming

Rename all surface vocabulary while preserving exact semantic mapping and construction authority. Recurrent semantic fingerprints and answer bindings must remain invariant.

## 14.9 Replay determinism

Repeated identical pass inputs/pins produce byte-stable semantic class ordering/fingerprints and equivalent numeric trace summaries within the explicitly chosen deterministic representation.

## 14.10 Concurrency

Run many independent contexts concurrently:

- no cross-session activation leakage;
- no global compute lock serialization;
- authority cache swaps safe;
- no mutation of shared parameter objects.

## 14.11 Performance

Benchmark increasing:

- vocabulary size;
- candidate count;
- semantic graph size;
- edge density;
- iteration count.

Verify latency tracks active sparse graph, not total repository vocabulary.

---

# 15. End-to-end acceptance scenarios

Run the Phase-12 M2 conversation suite through recurrent Stage 6/7 without changing its semantic outputs adversely:

### Participant memory

```text
My name is Chibu.
What's my name?
My full name is Chibueze Opata.
What's my full name?
```

Expected: same semantic answer bindings as deterministic baseline, with recurrent trace showing identity/port/type/discourse support.

### Correction

```text
My name is Chibu.
No, my name is Chibueze.
What's my name?
```

Expected: correction/supersession semantics preserved; recurrence does not resurrect superseded belief.

### Compositional teaching

```text
A zorb is a toy.
The zorb is blue.
What is a zorb?
What color is the zorb?
```

Expected: first-use unknown term remains evidence-driven; recurrent dynamics resolves only licensed compositions and preserves learning frontier where promotion is still required.

### Partial meaning

Unknown material mixed with known structure must preserve known CSIR and produce partial/budget/frontier artifacts rather than erase the whole utterance.

### Discourse follow-up

```text
What did you mean?
Why?
For what?
What happened to it?
```

Expected: discourse/output-occurrence evidence participates through discourse/identity/context message families without converting prior output into world truth.

---

# 16. Phase-13 exit criteria

Phase 13 is complete only when all are true:

1. Canonical Stage 6 uses a real typed sparse recurrent activation graph.
2. Canonical Stage 7 uses recurrent attractor stabilization.
3. All 12 required message-family types exist and are tested.
4. Hard invalidity is represented by exact masks and cannot be overridden by activation.
5. Immutable deterministic parameter artifacts are exact-pinned.
6. Convergence and budget exhaustion are explicitly distinguished.
7. Budget exhaustion yields partial cognition/frontiers, never fabricated certainty.
8. Multiple close alternatives can survive Stage 7.
9. Canonical semantic-class clustering is used, not raw candidate/string identity.
10. Deterministic Phase-10 solver is oracle/shadow only, with no runtime fallback authority.
11. Full Phase 9–13 regression suite passes.
12. M2 semantic conversation suite still passes on semantic graphs/bindings/response acts.
13. Synthetic vocabulary renaming invariance passes.
14. Authority-race/replay tests pass.
15. Sparse performance/concurrency budgets pass.

---

# 17. Explicit non-goals / boundaries

Do **not** pull these later-roadmap responsibilities into Phase 13:

- candidate learning/promotion lifecycle — Phase 14;
- full state transform expressions and transition distributions — Phase 15;
- structural causal model/counterfactual propagation/planning — Phase 16;
- additional multimodal adapters/language packs — Phase 17;
- legacy cutover/removal — Phase 18.

Phase 13 may expose typed hooks/message families for these future systems, but must not implement them through hidden shortcuts.

---

# 18. Recommended implementation file map

```text
cemm/v350/dynamics/
    __init__.py
    model_v351.py
    parameters_v351.py
    minimum_parameters_v351.py
    compiler_v351.py
    masks_v351.py
    messages_v351.py
    solver_v351.py
    stabilizer_v351.py
    oracle_v351.py

cemm/v350/runtime_abi.py               # minimal ABI extensions only
cemm/v350/runtime_v351.py              # canonical Stage-6/7 wiring
cemm/v350/stage_contracts.py           # only if artifact contracts require exact additions

tests/v350/
    test_phase13_activation_model.py
    test_phase13_hard_masks.py
    test_phase13_message_families.py
    test_phase13_recurrent_solver.py
    test_phase13_ambiguity_partial.py
    test_phase13_context_scope.py
    test_phase13_determinism.py
    test_phase13_runtime_integration.py
    test_phase13_concurrency_performance.py
    test_phase13_m2_regression.py
```

---

# 19. Implementation order

Recommended merge order:

```text
13.0 contract freeze
13.1 typed models
13.2 exact parameter set + candidate baseline
13.3 graph compiler
13.4 hard masks
13.5 12 message-family builders
13.6 sparse recurrent solver
13.7 inhibition/convergence
13.8 semantic-class stabilizer
13.9 runtime cutover + oracle isolation
13.10 M2 regression
13.11 concurrency/performance/adversarial verification
```

Do not wire the recurrent solver as canonical until 13.1–13.8 unit tests are green. Do not delete the deterministic oracle; quarantine it as a test/shadow comparator until Phase-18 cutover evidence is complete.
