# CEMM v3.5.1 Unified Implementation Plan

**Status:** sole active implementation roadmap  
**Supersedes:** `PRE_3_5_1_STABILIZATION_PLAN.md` and `V3_5_1_IMPLEMENTATION_PLAN.md`  
**Goal:** turn CEMM into a working learning-first semantic system, beginning with robust basic English conversation, while preserving exact authority, provenance, safety, replay, and multilingual architecture.

---

# 0. Global release state machine

Every phase/component is tracked as:

```text
specified
→ implemented
→ wired
→ authoritative
→ verified
→ calibrated (if probabilistic)
→ replayable (if learned/stateful)
```

A file or passing unit test alone does not make a component complete.

---

# 1. Program strategy

The program has five sequential milestones:

```text
M0 STABILIZED RUNTIME SUBSTRATE
M1 EXACT CSIR SEMANTIC SPINE
M2 ENGLISH CONVERSATIONAL KERNEL
M3 WORKING LEARNING + RECURRENT SEMANTIC BRAIN
M4 FULL STATE/CAUSAL/MULTIMODAL CUTOVER
```

The key correction is to build a usable vertical slice early rather than implementing every advanced subsystem before proving basic cognition.

---

# Phase 0 — Documentation integrity, defect registry, and baseline freeze

## Objective
Create one non-conflicting contract set and exact evidence of current behavior.

## Work
- adopt this documentation set;
- restore/create `CORE_ISSUES.md`;
- retire old competing plans;
- capture exact `main` commit and release artifacts;
- capture Stage-0..22 traces;
- benchmark latency, storage, locks, queries, hashing and cache behavior;
- classify current components:

```text
PRESERVE
STABILIZE
COMPILE_TO_CSIR
REPLACE
MIGRATION_ONLY
DELETE
```

## Baseline dialogues
At minimum:

```text
hello
hii
how are you?
my name is Chibu
what's my name?
I like mangoes
what do I like?
what can you do?
why?
for what?
unknown word
correction
```

## Exit
- machine-readable defect registry;
- baseline trace corpus;
- architecture/acceptance tests mapped to issues.

---

# Phase 1 — Stabilize identity, runtime epoch, and release attestation

## Implement
- canonical persisted identity/fingerprints;
- typed idempotency outcomes;
- `RuntimeEpoch`;
- stable runtime-observation identity;
- `RuntimeAttestation`;
- startup/reload verification;
- O(1) hot-path generation check.

## Remove
- full release verification per request;
- duplicate service authority rechecks;
- timestamp/request-frequency identity errors.

## Exit
Normal request performs:

```text
0 release file hashes
0 boot hashes
0 full manifest enumeration
```

---

# Phase 2 — Split authority from mutable state; fix storage asymptotics and concurrency

## Implement

```text
AuthorityGeneration
AuthoritySnapshot
WorldRevision
DiscourseRevision
RuntimeObservationRevision
AuditRevision
GenerationAwareCache
ref→kind index
incremental overlay authenticated root
indexed exact/effective lookup
concurrent read snapshots
short write transaction path
```

## Remove
- one global snapshot fingerprint;
- `for kind in RecordKind` hot lookup;
- full overlay scan per write;
- global lock across semantic analysis;
- broad unrelated cache flush.

## Exit
- concurrent 1/4/16/64 read-only cycles overlap;
- O(1) writes do not scan O(total history);
- query-plan tests prove indexes.

---

# Phase 3 — CycleWorkspace, event-driven maintenance, and honest final status

## Implement

```text
CycleWorkspace
CycleCompletionStatus
FrontierEffect
MaintenanceScheduler
session participant lifecycle
runtime observation snapshots
event-driven learning activation/promotion
```

## Move out of `run_text()`
- learning promotion scan;
- runtime-self observation persistence;
- unrelated maintenance.

## Completion statuses

```text
SUCCESS
PARTIAL
NO_RESPONSE_REQUIRED
RESPONSE_DEFERRED
RESPONSE_BLOCKED
ACTION_UNCERTAIN
RUNTIME_ERROR
```

## Exit
- `errors=[]` cannot imply success;
- optional frontiers do not block unrelated grounded cognition.

---

# Phase 4 — Semantic eligibility/effect authorization split, proof-carrying realization, stabilization gate

## Implement

```text
CompiledSemanticCapability
EffectAuthorizationBoundary
proof-carrying realization
selective independent round-trip policy
performance/concurrency gate
```

Strict effect authorization remains for:

```text
durable semantic mutation
external operation
protected disclosure
external emission
```

## Milestone M0 — STABILIZED RUNTIME SUBSTRATE

Proceed only when:

```text
correctness gates pass
behavior regression suite passes
authority invariants pass
performance budgets pass
concurrency tests pass
known crash reproducers eliminated
no safeguard hidden/bypassed
```

Freeze stable substrate interfaces.

---

# Phase 5 — Stage 0–22 ABI migration and concrete runtime contract

## Objective
Make code match the new `CORE_LOOP.md` and `RUNTIME_PLAN.md`.

## Implement
- new `CoreStage` names/ABI;
- new `StageCapability`;
- `CognitiveCycleState`;
- stage input/output artifact contracts;
- persistence/effect matrix enforcement;
- bounded re-entry protocol;
- stage contract tests.

## Critical
Do not merely rename existing UOL stages.

Stage 5/6/7 must genuinely become:

```text
compile to CSIR
→ recurrent dynamics
→ attractor stabilization
```

## Exit
Every Stage 0–22 has:

```text
inputs
outputs
authority/read generations
allowed writes
frontier types
budgets
proof requirements
```

---

# Phase 6 — Exact CSIR v2 kernel and canonical equivalence

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
CSIRGraph
```

Implement:

```text
canonical labeling
normalization
typed substitution
composition
matching
unification
projection
scope/context/time qualification
semantic equivalence
```

## Tests
- serialization round-trip;
- alpha-renaming invariance;
- ordering independence;
- graph isomorphism canonical identity;
- qualification/scope distinctions;
- proof-lineage stability.

---

# Phase 7 — Definition/profile/parameter authority split and exact closure compiler

## Implement

```text
SemanticDefinition
OperationalProfile
DynamicsParameterArtifact
ObservationModel
CausalMechanism
UseAuthorization
DefinitionClosureResolver
SemanticDefinitionCompiler
CSIRNormalizer
ClosureProof
AuthoritySnapshotV351
```

## Reject
- floating executable dependencies;
- semantic/lifecycle/privacy/competence bundling into one meaning revision.

## Exit
Every executable higher-order concept has exact closure proof.

---

# Phase 8 — UOL/schema → CSIR compatibility compiler and early shadow migration

## Implement

```text
legacy record
→ deterministic CSIR compilation
→ normalization
→ equivalence/closure report
```

Classify migrations:

```text
LOSSLESS
REQUIRES_EXPLICIT_INTERPRETATION
AMBIGUOUS
DEPRECATED
QUARANTINED
```

Begin Stage-5 shadow comparison now.

## Prohibitions
- no legacy fallback when CSIR fails;
- no two authoritative brains.

---

# Phase 9 — Grounded referents, minimal state substrate, discourse primitives, English package

## 9A. Grounded semantic substrate

Implement:

```text
Referent
type assertions
aliases/names
identity candidates
properties
relations
state variables
time/context
participant roles
mention chains
propositions
claims
queries
gaps
answer projections
corrections/retractions
```

## 9B. Minimum reviewed English package

Must support composition for:

```text
pronouns/deixis
proper names
determiners
identity/classification
property/state predication
possession
simple relations
simple events
negation
modality/capability
WH queries
yes/no queries
corrections
definition/teaching
greetings
requests/imperatives
```

Add reviewed morphology and reversible normalization.

No English semantic branches in kernel code.

---

# Phase 10 — Deterministic exact semantic composition baseline

## Objective
Make basic meaning work before learned recurrent parameters are required.

Pipeline:

```text
forms/senses/constructions
+ grounding
+ referent/type/state projection
→ CSIR candidate fragments
→ hard pruning
→ typed constraint propagation
→ bounded discrete search
→ canonical semantic classes
→ partial graph/frontiers
```

This solver becomes:
- debugging oracle;
- shadow comparator for recurrent dynamics.

It is not a permanent second brain.

## Exit
Synthetic vocabulary renaming preserves semantics.

---

# Phase 11 — Epistemic admission, conversational memory, discourse/coreference, query

## Implement

```text
EpistemicAdmissionPolicy
ParticipantFrame
mention/coreference resolution
open-question state
clarification targets
common-ground state
scoped participant/world belief
query binder
proof-path retrieval
correction/supersession
```

Admission classes:

```text
ATTRIBUTED_ONLY
SESSION_PARTICIPANT_FACT
SCOPED_USER_ASSERTED_FACT
CORROBORATION_REQUIRED
HIGH_RISK_NO_AUTO_ADMISSION
HYPOTHETICAL_ONLY
```

## Required end-to-end examples

```text
My name is Chibu.
What's my name?

I like mangoes.
What do I like?

My name is Chibu.
No, my name is Chibueze.
What's my name?
```

No internal role labels may leak into answers.

---

# Phase 12 — Response CSIR, English realization, and Conversational Kernel Alpha

## Implement
Semantic response families:

```text
ANSWER_QUERY
REPORT_STATE
REPORT_RELATION
REPORT_EVENT
ACKNOWLEDGE_TARGETED_CLAIM
REQUEST_CLARIFICATION
CORRECT_PRIOR_OUTPUT
QUALIFY_UNCERTAINTY
REPORT_CAPABILITY
ASK_LEARNING_QUESTION
NO_RESPONSE_REQUIRED
```

Realization:

```text
Response CSIR
→ clause/discourse plan
→ role/reference realization
→ morphology
→ linearization
→ preservation proof
→ surface
```

## Milestone M2 — ENGLISH CONVERSATIONAL KERNEL

Must pass:

### Participant memory
```text
My name is Chibu.
What's my name?
My full name is Chibueze Opata.
What's my full name?
```

### Compositional teaching
```text
A zorb is a toy.
The zorb is blue.
What is a zorb?
What color is the zorb?
```

### Correction
```text
My name is Chibu.
No, my name is Chibueze.
What's my name?
```

### Partial meaning
Unknown material yields clarification/learning frontier without erasing known meaning.

### Discourse follow-up
```text
What did you mean?
Why?
For what?
What happened to it?
```

Tests assert semantic graphs/bindings/response acts, not exact wording.

---

# Phase 13 — Typed activation graph and recurrent attractor solver

## Implement

```text
SemanticActivationNode
TypedMessageEdge
HardConstraintMask
ActivationTrace
ConvergenceAssessment
DynamicsParameterSet
```

Start with deterministic immutable parameters.

Then implement:

```text
exact pruning
→ sparse recurrent propagation
→ inhibition
→ convergence/budget
→ semantic-class clustering
```

Required message families:

```text
lexical
construction
port/role
type
identity
scope
time/aspect
context
state
causal expectation
discourse
multimodal
```

Budget exhaustion yields partial cognition, never fabricated certainty.

---

# Phase 14 — Prediction, frontier classifier, and end-to-end learning

## Fix existing learning runtime first
- invalid `_package` call;
- undefined dependency variables;
- preserve dependency pins;
- no default-empty inducer claim;
- event-driven promotion.

## Implement candidate inducers

```text
FormNormalizationInducer
LexicalizationInducer
SenseInducer
ConstructionInducer
SemanticDefinitionInducer
StateSchemaInducer
TransitionCausalInducer
ParameterCandidateTrainer
```

## Learning loop

```text
frontier
→ evidence/counterexamples
→ candidate
→ exact dependencies
→ competence
→ requested scoped uses
→ promotion
→ immutable new authority generation
→ next-cycle activation
→ restart
→ replay/invalidation
```

## Milestone M3 — WORKING LEARNING

Required test:

```text
teach genuinely unseen concept
→ create candidate
→ promote under policy
→ restart
→ understand unseen new composition using learned concept
→ answer query about it
```

No custom concept code.

---

# Phase 15 — Full entitled state spaces, role-sensitive transitions, capability dependencies

Expand state domains:

```text
categorical
ordered
continuous
vector/manifold
relational
set-valued
process-valued
probabilistic
```

Implement:

```text
ParticipantRoleBinding
StateTransformExpression
MechanismPrecondition
MechanismDefeater
TransitionPreviewProof
TransitionDistribution
CapabilityDependencyGraph
```

Acceptance:
- active/passive semantic equivalence;
- cross-type different consequences;
- no event-name mutators.

---

# Phase 16 — Structural causal model, impact, goals, planning, operations

Implement:

```text
CausalVariable
CausalMechanismGraph
InterventionContext
CounterfactualContext
CausalPropagationEngine
ExplanationExtractor
ImpactVector
GoalArbitrator
CausalPlanner
```

Support:

```text
direct deltas
dependency propagation
secondary events
threshold triggers
bounded recursion
counterfactual isolation
```

Keep physical state, affective consequence, reported emotion and response stance separate.

Operations remain explicitly authorized and journaled.

---

# Phase 17 — Multimodal grounding and additional language packs

Add calibrated evidence adapters for:

```text
speech/prosody
vision/tracks
location
environmental sensors
runtime telemetry
operation results
```

Add additional language packs only through shared semantics.

Prove equivalent CSIR for shared competence across:
- English;
- at least one typologically different real language;
- synthetic renamed language.

---

# Phase 18 — Migration completion, shadow comparison, cutover, legacy removal

Run old/new paths on identical observations and compare:

```text
grounding
canonical meaning
query bindings
epistemic placement
durable deltas
frontiers
response semantics
realization
latency
storage volume
```

Cut over only when:

```text
all public higher-order meaning compiles to CSIR
new Stage 0–22 ABI is authoritative
English conversational kernel passes
learning→promotion→restart passes
recurrent solver bounded/calibrated
state/causal proofs replayable
runtime manifest pins all roots
no floating authority
no legacy fallback
performance/concurrency gates pass
```

After cutover:

```text
legacy UOL public runtime authority = zero
legacy imports = migration-only or deleted
signed v3.5.1 release artifacts regenerated deterministically
```

---

# 2. Recommended patch/PR sequence

```text
PR1  docs + defect registry + acceptance reset + baseline tools
PR2  identity + RuntimeEpoch + RuntimeAttestation
PR3  generation split + store/index/cache/concurrency
PR4  CycleWorkspace + event-driven maintenance + final status
PR5  semantic eligibility/effect split + proof realization + stabilization gate
PR6  new Stage ABI + runtime contracts
PR7  CSIR v2 + exact closure/authority
PR8  UOL→CSIR migration/shadow compiler
PR9  grounded substrate + English package
PR10 deterministic semantic composition
PR11 discourse/memory/query
PR12 Response CSIR + English realization + conversational alpha
PR13 recurrent dynamics + calibration
PR14 prediction/frontiers + working learning/promotion/restart
PR15 state/action/capability
PR16 causality/impact/goals/operations
PR17 multimodal/multilingual
PR18 cutover + legacy removal + signed release
```

---

# 3. Definition of a working v3.5.1

CEMM is not considered working because all stage adapters execute.

It must:

```text
understand known vocabulary compositionally
ground self/user/referents
remember scoped facts
answer queries with semantic values
maintain discourse across turns
preserve uncertainty/partial meaning
learn a new reusable concept
reuse it after restart
construct Response CSIR before text
realize English without predicate-specific sentence code
preserve exact authority/proof/replay
remain performant under concurrent ordinary use
```
