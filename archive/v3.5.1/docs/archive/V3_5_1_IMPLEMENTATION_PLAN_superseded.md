# SUPERSEDED — historical planning context only

**Canonical roadmap: [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md)**

This document has been moved to [`docs/archive/V3_5_1_IMPLEMENTATION_PLAN.md`](docs/archive/V3_5_1_IMPLEMENTATION_PLAN.md).

Its useful reasoning has been integrated into the unified `IMPLEMENTATION_PLAN.md` (Phases 5–18).

Do not follow this as an active implementation plan.

---

# CEMM v3.5.1 Semantic Brain Implementation Plan

**Purpose:** migrate the current v3.5 runtime from a primarily typed symbolic pipeline into a grounded recurrent semantic dynamical architecture without losing exact authority, proof, safety or multilingual compositionality.

---

# 0. Release gates

Every phase is tracked as:

```text
specified → implemented → wired → authoritative → verified → calibrated
```

`calibrated` applies to probabilistic/continuous components.

No phase may become public authority merely because tests or files exist.

---

# Phase 0 — Baseline and authority freeze

## Objective

Capture exact current runtime, semantic, state, learning and response behavior before structural migration.

## Work

- pin repository commit, boot database, runtime manifest and current parameter-like constants;
- inventory all named semantic branches, static scores, adapters and record families;
- capture representative Stage-0..22 traces;
- capture semantic errors involving subject/object effects, state dimensions, causal propagation, multimodal grounding, learning and response;
- measure solver latency, graph sizes, state query costs and persistence sizes;
- classify every current component as preserve, wrap, replace, migrate or remove.

## Exit

Machine-readable debt and baseline evidence exist.

---

# Phase 1 — Governing contracts and lints

Replace root `ARCHITECTURE.md`, `AGENTS.md`, `CORE_LOOP.md`; add `CEMM_CORE_MATHS.md`.

Add CI lints for:

- floating semantic/parameter revisions;
- concept-name branches;
- subject/object mutation rules;
- event-specific mutators;
- universal state dimensions;
- embedding/semantic identity conflation;
- correlation-to-causality shortcuts;
- response strings before Response CSIR.

---

# Phase 2 — Kernel Semantic ABI and CSIR v2

## Implement

```text
SemanticTerm
SemanticVariable
SemanticApplication
PortBinding
Qualifier
ScopeEmbedding
Coordination
ProofLink
ExactAuthorityPin
```

Add exact canonical graph labeling and equivalence.

Ensure all current UOL records can project to CSIR v2 and round-trip without semantic loss.

---

# Phase 3 — Split definition, profile, dynamics and authorization authority

Create first-class stores/records for:

```text
SemanticDefinition
OperationalProfile
DynamicsParameterArtifact
CausalMechanism
ObservationModel/Calibration
UseAuthorization
```

Remove lifecycle/use/meaning/parameter bundling from a single schema record.

All executable dependencies become exact pins.

---

# Phase 4 — Definition compiler and authority-closure resolver

Implement:

```text
DefinitionClosureResolver
SemanticDefinitionCompiler
CSIRNormalizer
ClosureProof
AuthoritySnapshotV351
```

Reject latest/max/minimum/floating parent resolution for executable meaning.

Run compiler in shadow mode against current composition.

---

# Phase 5 — Entitled grounded state-space metamodel

Implement dimension contracts supporting:

```text
categorical
ordered discrete
continuous
vector/manifold
relational
set-valued
process-valued
probabilistic
```

Add:

- type/facet entitlement to dimensions;
- value domains, units and ordering;
- observation models;
- persistence and interval semantics;
- uncertainty/belief representation;
- cross-dimensional dependency interfaces.

Seed only structural dimension families, not domain facts.

---

# Phase 6 — Multimodal evidence and calibration layer

Implement generic adapters for:

```text
text
speech/prosody
vision/tracks
location
numeric/environment sensors
system telemetry
operation results
```

Adapters emit calibrated likelihoods and identity/state candidates.

Add lineage-aware multimodal fusion and disagreement tests.

---

# Phase 7 — Semantic activation graph

Implement sparse runtime structures:

```text
SemanticActivationNode
TypedMessageEdge
HardConstraintMask
ActivationTrace
ConvergenceAssessment
DynamicsParameterSet
```

Start with deterministic hand-specified relation-specific message functions; make parameter interfaces trainable without making them semantically authoritative.

---

# Phase 8 — Recurrent meaning attractor solver

Replace one-pass/beam-only composition with a hybrid:

1. exact domain pruning;
2. recurrent typed message passing;
3. bounded search over unresolved discrete choices;
4. semantic-equivalence clustering;
5. posterior/energy calibration;
6. partial-attractor output.

Preserve current deterministic solver as oracle/shadow comparator during migration.

---

# Phase 9 — Role-sensitive event/action transition system

Define action/event mechanisms as role-bound state transformers.

Implement:

```text
ParticipantRoleBinding
StateTransformExpression
MechanismPrecondition
MechanismDefeater
TransitionDistribution/GraphRewrite
TransitionPreviewProof
```

Acceptance must prove active/passive and multilingual equivalence, and different effects for different role bindings.

---

# Phase 10 — Structural causal model and recursive propagation

Implement:

```text
CausalVariable
CausalMechanismGraph
InterventionContext
CounterfactualContext
CausalPropagationEngine
ExplanationExtractor
```

Support direct deltas, dependency propagation, secondary events, threshold triggers and bounded recursion.

Do not infer causality from temporal adjacency.

---

# Phase 11 — Capability, structural and resource dependency graph

Migrate capability logic to dependencies over grounded state variables and runtime adapters.

Implement generic reevaluation after state deltas.

Preserve affordance, function, capability, permission and competence distinctions.

---

# Phase 12 — Prediction and frontier classifier

Add predicted next-state/observation records and prediction-error decomposition.

Implement typed frontiers for:

- grounding;
- observation calibration;
- semantic definition;
- construction/role;
- state model;
- causal structure/parameter;
- capability dependency;
- impact/goal;
- realization/response.

---

# Phase 13 — Continuous parameter learning

Introduce immutable candidate parameter artifacts for:

- message passing;
- observation likelihoods;
- priors/salience;
- causal strengths;
- state estimators;
- calibration.

Training produces new artifacts, never in-place mutation.

Require replayable data lineage, held-out competence, calibration and risk-specific promotion.

---

# Phase 14 — Discrete semantic and causal structure learning

Implement candidate induction for:

```text
new type/state/relation/event definitions
new role structures
new transition mechanisms
new causal edges
new constructions and lexicalizations
new operational profiles
```

Use conservative abstraction, MDL/compression gain, counterexamples and intervention evidence where available.

---

# Phase 15 — Impact, affect and significance model

Replace shallow scalar rules with grounded impact vectors over before/after state, stakeholder and goal relations.

Add explicit affective mechanisms and evidence channels.

Acceptance must distinguish:

- physical state;
- predicted affective consequence;
- reported emotion;
- system response stance.

---

# Phase 16 — Goal arbitration and causal planning

Implement utility components and conflict/resource constraints.

Planning must use causal simulation and return predicted consequences, uncertainty and proof.

External operations remain separately authorized and journaled.

---

# Phase 17 — Response semantic action generator

Generate Response CSIR from:

- query bindings;
- causal explanations;
- epistemic qualification;
- impact/stakeholder state;
- learning questions;
- commitments and policies.

Implement candidate utility over coverage, truth, information gain, social appropriateness, impact sensitivity, risk and cost.

No predicate-specific response transforms.

---

# Phase 18 — Multilingual realization and semantic round trip

Realize equivalent Response CSIR across reviewed language packs.

Test:

- role-preserving active/passive variation;
- state, causal explanation and uncertainty realization;
- affect/impact qualification;
- synthetic language renaming;
- no meaning invention.

---

# Phase 19 — Runtime snapshot and manifest v3.5.1

Expand cycle and release authority to pin:

```text
semantic/compiler/normalizer ABIs
definition/profile roots
dynamics parameter root
causal mechanism root
observation/calibration root
use authorization root
language/multimodal root
policy/adapter root
```

Update cutover guard, release compiler and deterministic artifact report.

---

# Phase 20 — Migration of v3.5 data and runtime

Compile current schema families into:

```text
semantic definitions
operational profiles
state dimensions
causal/transition mechanisms
use authorizations
```

Every ambiguous conversion is quarantined.

Run old and new meaning/transition/response paths in shadow mode using the same observations.

---

# Phase 21 — Comprehensive competence suite

Required suites:

```text
semantic canonicalization
grounded multimodal fusion
state-space entitlement
temporal/geospatial reasoning
active/passive/cross-language roles
cross-dimensional causal mechanisms
animal/server/room type contrasts
recursive causal propagation
counterfactual isolation
capability dependency
prediction-error learning
continuous parameter replay
causal structure competence
impact/affect distinction
goal planning
response CSIR and round trip
restart/invalidation/version reconstruction
performance and budget incompleteness
```

---

# Phase 22 — Shadow activation and cutover

Cut over only when:

- no public decision depends on floating authority;
- all higher-order meaning compiles to CSIR;
- recurrent solver is calibrated and bounded;
- state/action/causal proofs are replayable;
- learned parameter and semantic artifacts rehydrate exactly;
- synthetic multilingual role tests pass;
- response generation is predicate-independent;
- runtime manifest pins all new authority roots;
- legacy authority debt is zero or explicitly migration-only.

---

# Initial implementation order

The first executable patch should implement only the substrate required for safe shadowing:

```text
1. ExactAuthorityPin and AuthoritySnapshotV351
2. SemanticDefinition / OperationalProfile / DynamicsParameterArtifact
3. CSIR v2 and exact normalizer
4. DefinitionClosureResolver and compiler
5. StateDimensionDomain and GroundedStateVariable
6. typed activation/message graph interfaces
7. Stage-5 shadow compilation
8. release/manifest schema extension
9. algebraic and versioning tests
```

Do not begin by tuning weights or adding domain transitions. The recurrent semantic brain must first have exact semantic and versioned foundations.
