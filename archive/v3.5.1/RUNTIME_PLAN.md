# CEMM v3.5.1 Runtime Plan

**Status:** canonical concrete runtime implementation contract  
**Role:** bridge `ARCHITECTURE.md` + `CORE_LOOP.md` to actual runtime code.  
**This document answers:** what runs when, who owns each artifact, what may persist, how authority/state generations work, and how the v3.5 runtime migrates to v3.5.1.

---

## 1. Why this document exists

`ARCHITECTURE.md` defines the cognitive model.

`CORE_LOOP.md` defines the 23 logical stages.

`IMPLEMENTATION_PLAN.md` defines the development sequence.

This file defines the **concrete runtime** so implementation cannot drift into:

- 23 database transactions;
- duplicated authority checks;
- hidden pre-Stage-0 cognition;
- mixed UOL/CSIR authority;
- per-request maintenance;
- accidental persistence of transient graphs;
- ambiguous stage artifacts;
- unbounded re-entry.

---

## 2. Runtime object model

### 2.1 Process-lifetime objects

Created at startup/reload:

```text
RuntimeAttestation
RuntimeGeneration
ImmutableBootStore
AuthorityGenerationManager
RuntimeServiceRegistry
RuntimeEpoch
ObservationProviders
MaintenanceScheduler
```

Startup/reload performs expensive release verification.

Ordinary requests consume an O(1) attestation/generation token.

### 2.2 Session/context-lifetime objects

Created when a conversation/session/principal scope is established:

```text
SessionContext
ParticipantIdentityBinding
ConversationScope
RetentionPolicy
PermissionScope
```

Stable participant initialization must be idempotent and must not be re-created because another message arrived.

### 2.3 Cycle/pass-lifetime objects

```text
CycleState
AuthoritySnapshot
ReadGeneration
ParticipantFrame
CycleWorkspace
BudgetSet
EffectJournalHandles
```

`CycleWorkspace` owns transient cognition.

---

## 3. Authority and mutable-state generations

Never use one `snapshot_fingerprint` to mean everything.

### 3.1 RuntimeAttestation

Answers:

> Is this process running an approved release generation?

Verified at:

```text
startup
explicit reload
integrity fault recovery
```

Not rehashed per message.

### 3.2 AuthorityGeneration

Immutable generation over:

```text
semantic ABI
compiler/normalizer
definitions
profiles
dynamics parameters
causal mechanisms
language/multimodal packages
use authorizations
policies/adapters
```

One semantic pass pins one authority generation.

### 3.3 Mutable generations

Track separately:

```text
WorldRevision
DiscourseRevision
RuntimeObservationRevision
AuditRevision
EffectJournalRevision
```

A discourse write must not invalidate semantic-definition closure caches.

---

## 4. Stage capability token

Replace the old whole-store snapshot capability with:

```text
StageCapability {
  cycle_ref
  pass_ref
  stage
  predecessor_stage
  nonce
  authority_generation
  read_generation
}
```

A stage validates:

- cycle/pass ownership;
- expected stage order;
- authority generation;
- required read generation;
- explicit re-entry rules.

A stage must not re-open storage merely to recompute the same capability fingerprint.

---

## 5. CycleWorkspace

Default home for:

```text
evidence lattice
grounding candidates
referent projections
CSIR candidates
activation graph
solver traces
semantic attractors
epistemic working belief
query matches
transition previews
impact estimates
goal candidates
Response CSIR
realization plans/candidates
verification proofs
frontier graph
```

Persistence is the exception, not the default.

Debug/audit retention may copy selected artifacts without changing semantic authority or mutable world generations.

---

## 6. Persistence and effect matrix

| Stage | Default persistence | Allowed durable effects |
|---|---|---|
| 0 | none | none |
| 1 | workspace; durable evidence only when required by later commit | none |
| 2 | none | none |
| 3 | none | none |
| 4 | none | none |
| 5 | none | none |
| 6 | none | none |
| 7 | none | none |
| 8 | none | none |
| 9 | none | none |
| 10 | none | none |
| 11 | candidate/evidence work stays workspace until Stage 13 | none |
| 12 | none | none |
| 13 | yes | semantic/world/learning CAS commits |
| 14 | workspace by default | optional explicit audit retention only |
| 15 | workspace by default | optional explicit decision retention only |
| 16 | yes where an external effect is attempted | prepared effect journal, execution/result evidence |
| 17 | operation reconciliation evidence where required | no direct world mutation |
| 18 | workspace by default | no public semantic-state mutation |
| 19 | workspace by default | no public semantic-state mutation |
| 20 | yes only for emission/effect journal as required | emission authorization/journal/execution evidence |
| 21 | yes | emitted discourse/common-ground commit |
| 22 | yes where consolidation/promotion/invalidation policy requires | new generation publication, invalidation/replay metadata |

Stage numbers are not transaction boundaries.

---

## 7. Concrete stage artifact contracts

### Stage 0
Consumes: runtime/session context.  
Produces:

```text
AuthoritySnapshot
ReadGeneration
ParticipantFrame
ContextStack
BudgetSet
CycleWorkspace
```

### Stage 1
Consumes: raw input/provider observations.  
Produces:

```text
EvidenceEnvelope[]
```

### Stage 2
Consumes: evidence envelopes.  
Produces:

```text
EvidenceLattice
LanguageDecisionEvidence
SensorFeatureCandidates
```

### Stage 3
Consumes: evidence lattice + participant/discourse state.  
Produces:

```text
GroundingCandidateSet
IdentityCoreferenceTrace
```

### Stage 4
Consumes: grounding candidates + exact type closure + world view.  
Produces:

```text
ReferentProjection[]
StateSpaceProjection[]
SemanticClosureCandidate[]
```

### Stage 5
Consumes: language/grounding/state candidates.  
Produces:

```text
CSIRCandidateSet
ClosureProof[]
HardConstraintTrace
```

### Stage 6
Consumes: exact CSIR candidates.  
Produces:

```text
ActivationGraph
ActivationTrace
```

### Stage 7
Consumes: activation graph/trace.  
Produces:

```text
SemanticAttractorSet
PartialMeaning
OpenVariables
ConvergenceAssessment
```

### Stage 8
Consumes: selected/stable CSIR classes.  
Produces:

```text
DiscourseStructures
Propositions
Claims
Events
Queries
Corrections
Commitments
```

### Stage 9
Consumes: Stage-8 structures + evidence/policy.  
Produces:

```text
EpistemicPlacement
WorkingBeliefDelta
AdmissionDecision[]
```

### Stage 10
Consumes: queries + grounded belief + discourse.  
Produces:

```text
QueryResult[]
ExplanationProof[]
```

### Stage 11
Consumes: predictions + observed outcomes + frontiers.  
Produces:

```text
PredictionError[]
LearningFrontier[]
LearningCandidateWork[]
LearningQuestionCandidates
```

### Stage 12
Consumes: admitted events/actions/hypotheses.  
Produces:

```text
TransitionPreview[]
CounterfactualBranches
CausalProof[]
```

### Stage 13
Consumes: authorized durable proposals.  
Produces:

```text
CommitReceipt[]
new WorldRevision/DiscourseRevision as applicable
```

### Stage 14
Consumes: committed/admissible deltas.  
Produces:

```text
CapabilityDelta[]
ImpactAssessment[]
AffectEstimate[]
SignificanceAssessment[]
```

### Stage 15
Consumes: queries, commitments, frontiers, risks, impact.  
Produces:

```text
GoalCandidate[]
GoalDecision
```

### Stage 16
Consumes: selected executable goals.  
Produces:

```text
Plan[]
EffectAuthorization[]
OperationJournal[]
OperationObservation[]
```

### Stage 17
Consumes: operation observations.  
Produces:

```text
OutcomeReconciliation[]
PredictionError[]
ReentryRequest?
```

### Stage 18
Consumes: query results, goals, epistemics, discourse, impact.  
Produces:

```text
ResponseCSIRCandidate[]
ResponseDecision
```

### Stage 19
Consumes: selected Response CSIR.  
Produces:

```text
RealizationPlan
SurfaceCandidate[]
RealizationProof[]
```

### Stage 20
Consumes: response semantics + realization proof + surface.  
Produces:

```text
SemanticPreservationAssessment
EmissionAuthorization
EmissionObservation?
```

### Stage 21
Consumes: observed emission.  
Produces:

```text
OutputDiscourseCommit
CommonGroundProposal
```

### Stage 22
Consumes: whole cycle/pass trace.  
Produces:

```text
CycleCompletionStatus
InvalidationSet
ReplayRequirements
Promotion/ConsolidationResults
FinalCycleSummary
```

---

## 8. Pre-cycle and post-cycle work

### 8.1 Must not run on every request merely because a request occurred

```text
full release verification
learning promotion scan
runtime telemetry persistence
whole-store integrity scan
global cache rebuild
boot reconciliation
```

### 8.2 Event/schedule-driven maintenance

```text
runtime health/provider refresh
learning competence/promotion
package activation
cache warming
compaction
audit export
replay queue
```

A maintenance change that publishes new semantic authority becomes visible only through a new `AuthorityGeneration`.

---

## 9. Participant/session lifecycle

Participant identity must not be invented from lexical pronouns.

Session setup establishes transport-grounded roles:

```text
system/self
input speaker
input addressee
response audience
context
permission scope
```

Language contributes role requirements:

```text
first-person speaker
second-person addressee
deictic proximal/distal
```

Grounding binds those requirements to the `ParticipantFrame`.

Renaming pronouns in a synthetic language must preserve identical participant semantics.

---

## 10. Epistemic admission policy

Implement explicit admission classes:

```text
ATTRIBUTED_ONLY
SESSION_PARTICIPANT_FACT
SCOPED_USER_ASSERTED_FACT
CORROBORATION_REQUIRED
HIGH_RISK_NO_AUTO_ADMISSION
HYPOTHETICAL_ONLY
```

Examples:

- `My name is Chibueze` may become a scoped participant fact.
- `The bank is insolvent` may remain attributed or require corroboration.
- `Imagine the fox is dead` remains hypothetical.
- a reported event does not trigger actual-world transition.

Every admitted fact preserves source/time/context/permission and contradiction lineage.

---

## 11. Query/runtime usability rule

A missing optional subsystem must not block a grounded core answer.

Example:

```text
known participant name
+ working identity query
+ no affect model
```

must still answer the name query.

Frontiers declare exact effect:

```text
informational
learning
blocks_query_answer
blocks_commit
blocks_effect
blocks_realization
blocks_emission
```

Only relevant blocking frontiers prevent the requested outcome.

---

## 12. Learning runtime

### 12.1 Candidate induction registry

Canonical runtime must ship concrete inducer interfaces/implementations for:

```text
form/normalization
lexicalization
sense
construction
semantic definition
state schema
transition/causal structure
continuous parameters
```

No default runtime may silently have an empty inducer set while claiming active learning.

### 12.2 Promotion is not request-frequency work

Promotion occurs on:

```text
new evidence threshold
competence completion
review decision
explicit consolidation
startup reconciliation
scheduled maintenance
```

### 12.3 Generation switch

Promotion publishes immutable artifacts into a new authority generation.

Active passes never mutate to the new generation mid-cycle.

---

## 13. Re-entry

Only Stage 17 may request operation-outcome semantic re-entry.

Re-entry request includes:

```text
observation batch
reason
carry-artifact whitelist
maximum reentries
required read-generation behavior
```

Bound the number of reentries.

If mutable state/authority invalidates the original pass assumptions, restart rather than continuing stale cognition.

---

## 14. Realization verification

Every deterministic realization transform records:

```text
input semantic fragment
rule pin
lexical pin
morphology pin
linearization pin
coverage
preserved qualifications
```

Cheap proof verification is mandatory for all emissions.

Independent full round-trip is policy-driven for novelty/risk/audit—not a per-message full-pipeline tax when proof is sufficient.

Release competence still performs independent round-trip over every supported construction family.

---

## 15. Storage architecture

Hot paths require:

```text
typed exact pins
ref→kind index
indexed effective lookups
incremental authenticated roots
generation-aware caches
short write transactions
read concurrency
separate audit/history indexes
```

Prohibit:

```text
whole overlay hash rebuild per write
all-RecordKind probe
materialize-all to find latest
global lock across semantic analysis
unbounded hot-stage scans
```

Every hot scan must have:

```text
bounded cardinality
index
cache
or explicit budget
```

---

## 16. v3.5 → v3.5.1 migration runtime rule

Create one-way compatibility:

```text
v3.5 UOL/schema authority
→ offline/activation-time compiler
→ exact CSIR
→ equivalence/closure proof
```

During shadow migration:

- old deterministic path may be a comparator;
- public effects still come from the active runtime;
- no request may fall back to old UOL because CSIR failed;
- migration ambiguities are quarantined.

At cutover:

```text
CSIR public authority = true
legacy UOL runtime authority = false
migration compiler = offline/read-only
```

---

## 17. Runtime Definition of Done

A runtime generation is usable only when:

```text
Stage 0–22 concrete adapters exist
stage artifact contracts pass
persistence/effect matrix passes
no pre-Stage-0 request-frequency semantic writes
no per-request release rehash
no per-request full learning scan
authority and mutable generations are split
concurrent reads overlap
partial cognition final status is honest
English conversational kernel passes
learning→promotion→restart passes
no legacy fallback exists
```

# Phase 15–16 runtime completion addendum

- Stage 10 may emit a `CausalQueryRequest` only from exact answer-projection authority; never from question words.
- Stage 12 is simulation-only: typed state snapshot -> exact mechanism preview -> bounded causal branches/proofs.
- Stage 13 commits only actual-context, probability-1, frontier-free, exact-authority consequences; it durably persists their exact causal proof DAG and mechanism dependencies. All other simulations remain cycle-local.
- Stage 14 derives capability/impact from the same causal deltas/proofs and keeps physical, affective, reported emotion and response stance separate. Impact retains context semantics; only actual-context impact may automatically create goal pressure.
- Stage 15 produces both conversational response goals and, when exact policy exists, vector-valued causal goals.
- Stage 16 plans by causal simulation. A selected causal plan is semantic eligibility only; existing adapter/gate/journal/effect authorization remains mandatory before I/O.
- Stage 17 observed outcomes re-enter cognition as evidence and may create prediction-error/causal-learning frontiers; expected effects are never written as observations.

## Phase 17–18 final runtime closure

Final runtime authority uses manifest v5 with exact Stage 0–22 adapters, canonical service slot + implementation method/source attestations, runtime source-tree Merkle-style root, boot-derived exact pins, legacy-free runtime record families, closure-ledger hash and detached signature metadata. Checked-in manifests remain preactivation until every closure gate passes against the same commit, boot hash, source root and authority payload hash.

