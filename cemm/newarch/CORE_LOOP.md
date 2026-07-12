# CEMM v3.4 — Exact Integrated Cognitive Core Loop

## 1. Runtime unit

Every external or internal event creates one immutable `CognitiveCycle`.

```python
@dataclass(frozen=True)
class CognitiveCycle:
    cycle_id: str
    trigger: CycleTrigger
    input_signals: tuple[SignalEnvelope, ...]
    snapshot: KernelSnapshot

    surface_evidence: tuple[SurfaceEvidence, ...] = ()
    meaning_candidates: tuple[MeaningCandidate, ...] = ()
    grounded_candidates: tuple[GroundedMeaningCandidate, ...] = ()
    selected_interpretations: tuple[Interpretation, ...] = ()

    workspace: WorkspaceSnapshot | None = None
    retrieval_results: tuple[RetrievalResult, ...] = ()
    epistemic_assessments: tuple[EpistemicAssessment, ...] = ()
    capability_assessments: tuple[CapabilityAssessment, ...] = ()
    gaps: tuple[GapRecord, ...] = ()

    goals: tuple[GoalRecord, ...] = ()
    plans: tuple[PlanRecord, ...] = ()
    authorization: AuthorizationBatch | None = None
    execution_ledger: ExecutionLedger | None = None

    critical_mutations: MutationSet | None = None
    critical_commit: CommitOutcome | None = None

    message_plan: SemanticMessagePlan | None = None
    output_event: OutputEvent | None = None
    output_mutations: MutationSet | None = None
    output_commit: CommitOutcome | None = None

    scheduled_wakes: tuple[WakeRequest, ...] = ()
    trace: CycleTrace | None = None
```

Stages return a new cycle revision or typed artifact. They never mutate hidden global state.

## 2. Triggers

A cycle may be triggered by:

```text
user or agent utterance
sensor observation
tool result
external operation completion
timer or scheduled wake
resource/health change
permission/policy change
pending learning answer
background consolidation request
```

Internal wakes permit continuity without an uncontrolled busy loop.

## 3. Kernel snapshot

`KernelSnapshot` pins:

```text
schema-store revision
semantic-memory revision
episodic/event revision
common-ground revision
self/component-health revision
resource revision
permission/policy revision
active-goal revision
learning-transaction revision
competence-suite revisions
grounding-policy revision
kernel foundation/type-registry revision
inference/truth-maintenance revision
adapter observation-contract revisions
context/scope policy revision
clock observation
```

These values form the cycle's semantic-environment fingerprint. A child learning snapshot derives from this exact base; it does not read moving global schema state during validation.

All interpretation and planning in a cycle use the pinned snapshot unless a learning transaction creates a child schema snapshot for bounded replay.

## 4. Macro state machine

```text
ORIENT
  ↓
UNDERSTAND
  ↓
KNOW
  ↓
DECIDE
  ↓
ACT_AND_RECONCILE
  ↓
CRITICAL_COMMIT
  ↓
COMMUNICATE
  ↓
OUTPUT_COMMIT_AND_CONSOLIDATE
  ↺ scheduled next trigger
```

A stage may abstain, fail, or create a probe goal. It may not skip truth, authorization, or commit gates.

## 5. Detailed stage ordering

### A. ORIENT

1. Accept and deduplicate trigger signals.
2. Pin `KernelSnapshot`.
3. Refresh live component, channel, resource, permission, and policy observations.
4. Restore active goals, common-ground obligations, and learning transactions.
5. Derive ephemeral self-state and capability evidence.
6. Initialize cycle budgets and trace.

Authoritative output: `KernelSnapshot` and orientation evidence.

Forbidden: semantic interpretation, public response selection, durable mutation.

### B. UNDERSTAND

#### B1. Observe

Create typed `SignalEnvelope`s preserving source, permission, time, channel, and raw payload.

#### B2. Perceive

Language/modality adapters produce reversible `SurfaceEvidence`:

```text
spans and offsets
raw/normalized forms
morphology
syntax/dependency evidence
clause/quotation boundaries
negation and modality cues
lexeme/construction candidates
language confidence
```

#### B3. Compose

`SemanticComposer` produces separate candidate graphs containing:

```text
communicative predications
content predications
propositions
context frames
role hypotheses
open ports
source/evidence links
```

No candidate is actual truth.

#### B4. Ground

`GroundingResolver` resolves or preserves alternatives for:

```text
referent identity and candidate sense clusters
entity-kind/schema-family hypotheses
deictics and pronouns
role bindings and open ports
time and interval
place and reference frame
context/world ownership
co-reference
exact schema revision candidates
schema-family definition closure
current dependency/environment validity
epistemic admissibility for the selected context
operation-specific SchemaUseProfile
```

Open ports remain typed absences, not placeholder objects.

Opaque or provisional senses may be selected for quotation, attributed remembrance, search, correction, or learning. They may not silently participate in actual-world classification, inheritance, strong inference, or effects.

#### B5. Consume pending learning evidence

After ordinary composition and grounding, `LearningCoordinator` matches grounded propositions against expected evidence schemas for pending transactions.

Raw text is never copied directly into a hypothesis field.

#### B6. Provisional replay

When matched evidence can update a target schema:

1. create a child schema revision against the pinned snapshot;
2. stage typed schema changes with field-level provenance and evidence lineage;
3. classify typed dependencies and recursive components;
4. replay the earliest affected checkpoint;
5. run structural closure and sandboxed competence cases;
6. derive context-specific epistemic admissibility;
7. expose the result as provisional or activation-ready;
8. preserve rollback and idempotency data.

Replay may not repeat dispatched output or external side effects. Definition-derived cases can prove well-formedness only, not independent competence.

#### B7. Resolve

`InterpretationResolver` selects compatible branches using grounded structure, schemas, context, common ground, evidence, and coherence. Rejected branches remain traceable and cannot produce effects.

#### B8. Integrate

Selected semantic objects enter the cycle workspace as current evidence/meaning. Integration is non-persistent.

### C. KNOW

#### C1. Retrieve

Build semantic query patterns from selected propositions, goals, open ports, and context. Retrieve canonical records and evidence.

#### C2. Evaluate epistemics

Aggregate support/counterevidence, evidence lineage, temporal validity, permissions, contradictions, and context-specific admissibility. Produce four-state epistemic assessments.

Structural executability never establishes actual-world truth. A user theory may be admitted only in an attributed or belief context while actual-world use remains blocked.

#### C3. Introspect

Derive:

```text
knowledge/access/understanding assessments
live capability assessments
resource and operational limitations
self-relevant commitments and history
```

#### C4. Detect gaps

Create a gap only when a concrete missing or conflicting artifact blocks a selected interpretation, query, plan, operation, or response.

#### C5. Focus

`WorkspaceController` selects a bounded active set using relevance, novelty, uncertainty, urgency, goal impact, causal consequence, and discourse obligation.

### D. DECIDE

#### D1. Derive needs and obligations

Compile requests, questions, promises, corrections, gaps, policies, and state constraints into desired propositions/information states.

#### D2. Appraise and arbitrate goals

Score urgency, controllability, expected value, conflict, progress, cost, and policy priority. Select active goals without converting them into response labels.

#### D3. Plan

`Planner` instantiates operation schemas, checks preconditions/capabilities, simulates effects, orders dependencies, estimates costs/risks, and produces bounded plans.

#### D4. Authorize

`OperationAuthorizer` gates every operation for permission, safety, privacy, capability, resources, and context.

### E. ACT AND RECONCILE

#### E1. Execute

Execute authorized cognitive, communicative-preparation, or adapter-backed operations. Record lifecycle transitions and idempotency keys.

#### E2. Observe outcomes

Collect tool results, adapter acknowledgements, retrieval results, inference outputs, and operation failures.

#### E3. Reconcile

Compare predicted and observed effects. Produce actual event/state propositions, goal progress, prediction errors, competence updates, and mutation candidates.

Planning success is not execution success.

### F. CRITICAL COMMIT

1. Build exact `MutationSet` for facts/effects/writes/schema updates the response may claim.
2. Separate required and auxiliary operations.
3. Validate identity, cardinality, evidence, permission, context, contradictions, and schema version.
4. Commit atomically where required.
5. Record exact created/updated/superseded record IDs and failures.
6. Roll back provisional schema revisions that failed validation.

Response content may use only actual commit outcomes.

### G. COMMUNICATE

#### G1. Select content

`ResponsePlanner` selects propositions, assessments, outcomes, limitations, corrections, and questions needed to satisfy active communicative goals truthfully.

#### G2. Build semantic message plan

Plan rhetorical relations, ordering, focus, given/new information, stance, confidence qualification, references, and provenance.

#### G3. Realize

Language renderer performs lexicalization, referring expressions, aggregation, syntax, morphology, orthography, and channel encoding.

#### G4. Dispatch

Dispatch through an authorized, available channel and record actual transport outcome.

### H. OUTPUT COMMIT AND CONSOLIDATE

1. Commit the actual output event.
2. Update common ground only for content successfully dispatched.
3. Create pending question/probe obligations only for emitted questions.
4. Update discourse salience and commitments.
5. Finalize learning transaction lifecycle.
6. Update capability competence/reliability and prediction error.
7. Schedule non-critical consolidation, indexing, forgetting, or future wake events.

## 6. Stage authority table

| Stage | Sole authority | Authoritative output | Forbidden side effect |
|---|---|---|---|
| Orient | `CognitiveKernel` + observers | `KernelSnapshot` | meaning selection |
| Perceive | modality/language adapter | `SurfaceEvidence` | truth/write |
| Compose | `SemanticComposer` | meaning candidates | grounding/effects |
| Ground | `GroundingResolver` | grounded candidates | branch selection/write |
| Resolve | `InterpretationResolver` | selected interpretations | actual effects |
| Integrate/focus | `WorkspaceController` | workspace snapshot | truth change |
| Retrieve | `SemanticRetriever` | candidate records | truth decision |
| Epistemics | `EpistemicEvaluator` | assessments | response wording |
| Capability | `CapabilityEvaluator` | assessments | static claims |
| Gap detection | `GapDetector` | concrete gaps | generic token learning |
| Goals | `GoalArbiter` | active goals | canned intents |
| Plan | `Planner` | plan records | execution |
| Authorize | `OperationAuthorizer` | authorization | score-only safety |
| Execute | `OperationExecutor` | operation outcomes | unlogged effect |
| Reconcile | `OutcomeReconciler` | observed/predicted delta | invented success |
| Commit | `CommitCoordinator` | commit outcome | fallback success |
| Response content | `ResponsePlanner` | message plan | surface truth invention |
| Realize | language renderer | output payload | semantic decision |
| Common ground | `CommonGroundManager` via commit | discourse mutations | recording unsent text |
| Learning | `LearningCoordinator` | transaction/replay result | overlay-only success |

## 7. Learning resume checkpoints

A checkpoint contains:

```text
origin cycle and signal
blocked stage
input artifact refs
selected candidate refs
schema snapshot version
blocked goals
closure conditions
safe replay boundary
executed-operation exclusions
```

Replay begins at the earliest stage affected by the learned artifact:

- lexeme sense or construction → compose;
- predicate/role schema → compose or ground;
- entity identity/kind → ground;
- evidence/query policy → retrieve or epistemic evaluate;
- operation schema → plan;
- realization schema → realize.

## 8. Mutation discipline

Persistent mutations include:

```text
upsert referent
upsert predication/proposition/evidence
append event
upsert/supersede state interval
update common-ground commitment
upsert schema version
update learning transaction
update capability/competence statistic
record operation outcome
record output event
```

Every mutation has:

```text
operation_id
semantic identity
action: create | update | supersede | append | reject
required/auxiliary
precondition revision
source/evidence
permission
reason
```

## 9. Concurrency, invalidation, and idempotency

- Cycles and assessments are immutable and snapshot-pinned.
- Commits use optimistic revision checks and semantic-environment compare-and-swap.
- A rebase re-evaluates affected decisions before commit.
- External operations use stable idempotency keys.
- Replay excludes operations already started or dispatched.
- Replay identity includes evidence, target sense/revision, checkpoint, context/scope, and dependency fingerprint.
- Replay work is deduplicated, retry-safe, and stale-cancellable.
- Typed schema/environment changes publish invalidation events.
- Truth maintenance retracts or marks stale every dependent derived artifact while preserving original evidence.
- Output dispatch and output commit are separately recorded.

## 10. Budgets

The cycle owns explicit budgets for:

```text
surface analyses
meaning candidates
entity/coreference hypotheses
embedding depth
retrieval results
inference depth
causal simulations
plan branches
learning hypotheses
learning probes
replay depth
dependency frontier size
competence-case count and cost
schema size/depth
invalidation/replay work per cycle
response candidates
latency
memory and operation cost
```

Budget pressure reduces exploration. It never bypasses grounding, truth, permission, safety, or exact commit validation.

## 11. Typed failure behavior

Every stage returns typed failure/abstention such as:

```text
no viable schema
ambiguous grounding
unresolved context or scope
insufficient evidence
contradiction
inaccessible evidence
capability unavailable
permission blocked
resource insufficient
probe required
execution failed
commit conflict
realization unavailable
transport failed
```

Later stages may explain, probe, retry safely, or abstain. They may not convert failure into success.

## 12. Schema learning and activation transaction

```text
pin child snapshot S
→ assimilate grounded evidence with field provenance and lineage
→ construct exact child revision R
→ classify typed dependency graph and recursive components
→ derive structural grounding assessment A over S
→ run non-mutating competence suite with independent-oracle policy
→ derive epistemic admissibility E by context/scope
→ replay blocked checkpoint under S + R
→ if R remains provisional: commit provisional revision and exact limitations
→ if activation conditions pass:
     compare-and-swap store/environment fingerprint
     atomically activate R or its declared cluster
     publish typed invalidation and deferred-replay events
→ otherwise retain partial/provisional or roll back
```

No competency test may mutate canonical stores or execute an external effect.

## 13. Reference pseudocode

```python
def run_cycle(trigger: CycleTrigger) -> CycleResult:
    cycle = orient(trigger)

    cycle = observe(cycle)
    cycle = perceive(cycle)
    cycle = compose(cycle)
    cycle = ground(cycle)
    cycle = consume_learning_evidence(cycle)
    cycle = replay_provisional_learning(cycle)
    cycle = resolve(cycle)
    cycle = integrate_workspace(cycle)

    cycle = retrieve(cycle)
    cycle = evaluate_epistemics(cycle)
    cycle = evaluate_capabilities(cycle)
    cycle = detect_gaps(cycle)
    cycle = focus_workspace(cycle)

    cycle = derive_goals(cycle)
    cycle = arbitrate_goals(cycle)
    cycle = plan(cycle)
    cycle = authorize(cycle)

    cycle = execute(cycle)
    cycle = reconcile(cycle)
    cycle = commit_critical(cycle)

    cycle = plan_response(cycle)
    cycle = realize_response(cycle)
    cycle = dispatch_response(cycle)

    cycle = commit_output_and_common_ground(cycle)
    cycle = finalize_learning(cycle)
    cycle = schedule_consolidation_and_wakes(cycle)

    assert_cycle_invariants(cycle)
    return finalize(cycle)
```
