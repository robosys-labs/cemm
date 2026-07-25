# CEMM v1 Runtime Core Loop — Final Implementation Contract

## 1. One cycle, one workspace, explicit boundaries

Every input executes one ordered Stage 0–22 cycle. Stages are semantic boundaries, not a mandate for 23 services or transactions. The implementation groups them into eight macro-passes while preserving the trace and side-effect owner of every stage.

```text
A ORIENT                 0
B OBSERVE_ENCODE         1–2
C GROUND_PROJECT         3–4
D COMPOSE_SETTLE         5–7
E STRUCTURE_REASON       8–12
F COMMIT_PROPAGATE       13–14
G GOAL_ACT_RECONCILE     15–17
H RESPOND_FINALIZE       18–22
```

`CycleWorkspace` owns transient artifacts. No stage may infer a durable write merely because a Python object exists.

## 2. Stage table

### Stage 0 — ORIENT

Inputs: transport/session context and runtime attestation.

Outputs:

- ParticipantFrame;
- authority generation pin;
- world/discourse/observation revision pins;
- TemporalFrame and ContextStack;
- SelfRuntimeView;
- BudgetSet;
- empty StageTrace and CycleWorkspace.

No text-derived identity may override ParticipantFrame.

### Stage 1 — OBSERVE

Create EvidenceEnvelope from text, operation result, sensor input, or another modality. Preserve source, time, channel, permission scope, confidence, and lineage.

### Stage 2 — ENCODE

Create form/modality evidence, delexicalized clauses, candidate reference requirements, and unknown-form evidence. No semantic atom is created.

### Stage 3 — GROUND

Resolve participant requirements, designations, and discourse references. Ambiguity remains an explicit candidate/frontier.

### Stage 4 — PROJECT_STATE

For every active referent:

1. load direct TYPE/facet assertions;
2. recursively traverse subtype/facet authority;
3. collect dimensions/capabilities/resources/mechanisms;
4. traverse generic `rel:depends_on` edges;
5. project current state timelines.

Projection is bounded and authority-generation keyed.

### Stage 5 — COMPILE

State dimensions are mandatory. An unspoken dimension may only arrive through an explicit derived source (`DIM_OF_A*`) resolved by reviewed `rel:value_of_dimension` authority; no value-to-dimension compiler fill is permitted.



The neural codec proposes force, application topology, operators, role-source bindings, variables, and query projection. The exact compiler validates every required role, filler kind, state dimension, and native-domain value.

No bare query or value→dimension compatibility completion exists.

### Stage 6 — RECURRENT_DYNAMICS

Competing exact candidates interact under fixed rounds and bounded N-best topology. State projections and context may affect candidate energy; they do not become textual prompt hacks.

### Stage 7 — STABILIZE

Return resolved, partial, ambiguous, or unresolved meaning. Preserve stable content and attach frontiers only to blockers.

### Stage 8 — BUILD_STRUCTURES

Create DiscourseAct and, where relevant, QueryStructure or directive content. Mode and punctuation cannot rewrite force.

### Stage 9 — EPISTEMIC_PLACEMENT

For claim-like acts, create source-attributed claim occurrence and admission decision. Queries/directives are attributed but not admitted as world facts.

### Stage 10 — QUERY_EXPLAIN

Use sparse indexed retrieval and relevant-rule expansion. Execute restriction graph, return projected bindings and proof paths. Include runtime-provider facts when the query targets digital-self operational dimensions.

### Stage 11 — PREDICTION_ERROR

Classify open variables, missing evidence, ambiguity, contradictions, and observed-vs-predicted differences. Produce typed frontiers; do not convert the self into a global uncertain state.

### Stage 12 — TRANSITION_SIMULATION

Only event/action/hypothesis content is eligible. Match promoted causal mechanisms using named roles and state preconditions. Produce previews, never committed predicted facts.

### Stage 13 — COMMIT

First ordinary durable boundary. Require:

- exact stable/partial semantic artifacts;
- claim occurrence and placement;
- source/context/time/evidence;
- pinned expected world revision;
- proof/admission policy;
- one transaction and incremental commit receipt.

A query does not write world state. A normal unresolved turn may persist a compact learning frontier. `read_only` writes nothing.

### Stage 14 — CAPABILITY_IMPACT

Combine recursively inherited capability/resource graph with native state projection and cycle-local runtime observations. Produce normalized capability support only at the derived assessment layer.

### Stage 15 — GOAL_ARBITRATION

Rank actual obligations: answer, clarify, report capability, handle directive, acknowledge, greet. Blocked goals remain explicit rather than falling through to generic text.

### Stage 16 — PLAN_EXECUTE

Construct OperationPlan. Resolve the adapter from reviewed `rel:handled_by_adapter` authority, then require runtime registration, permission scope, capability support, idempotency key, and effect-journal ownership. No adapter means decline, not fake success.

### Stage 17 — ASSIMILATE_OPERATION

Record OperationResult as operation evidence. Validate any returned semantic observations, compare them to transition previews, cap re-entry, and do not auto-admit adapter output into world belief.

### Stage 18 — RESPONSE_CSIR

Construct response meaning from the exact target and obligation. Response action must reference QueryResult, FrontierGraph, capability, placement, or operation result—not a global outcome label.

### Stage 19 — REALIZE

Project Response CSIR/facts through the pinned language artifact. Semantic refs, evidence literals, and numbers use typed placeholders.

### Stage 20 — VERIFY

Verify learned transform authorization, placeholder provenance, grammar, no internal IDs, and non-empty output.

### Stage 21 — COMMON_GROUND

Only verified output is committed. Compare-and-swap against pinned discourse revision. Store the original Response CSIR, not reparsed surface text.

### Stage 22 — FINALIZE

Return compact stage trace, receipts, budgets, cache/slot counts, frontiers, proofs, and response. No full hash, retraining, or whole-store scan.

## 3. Persistence matrix

```text
artifact                           transient  stage-13  stage-16/17  stage-21
EvidenceEnvelope                      ✓           optional observation
candidate tensors                     ✓
InterpretationAssessment              ✓
QueryResult/proofs                    ✓
TransitionPreview                     ✓
PredictionError                       ✓           optional frontier
claim occurrence                                  ✓
admitted world claim                              ✓
effect plan/result                                            ✓
operation observation                                         ✓
Response CSIR                         ✓
verified common ground                                                     ✓
```

## 4. Normal, read-only, reviewed teaching

```text
normal
  same cognition + policy-authorized durable boundaries

read_only
  same cognition + all durable boundaries suppressed

reviewed_teach
  explicit reviewed rule induction + Stage-13 candidate/promotion receipt
```

A mode is an effect policy. It is not an intent label.

## 5. Sparse retrieval algorithm

Given restrictions `R` and salient refs `S`:

1. indexed active-fact lookup for grounded portions of `R`;
2. collect consequent operators/constants;
3. retrieve only reviewed/promoted rules indexed by those signatures;
4. add facts matching their antecedents;
5. iterate under max depth/facts/rules;
6. add a bounded set of facts mentioning `S`;
7. run exact closure only over that set.

The fallback is not `base_facts()`.

## 6. Commit protocol

At orientation:

```text
expected_world_revision = W0
expected_discourse_revision = D0
```

Stage 13:

```text
BEGIN
assert current world revision == W0
write compact generation delta
increment relevant revisions
compute hash(parent_hash + generation_delta)
write CommitReceipt
COMMIT
```

Stage 21 applies equivalent CAS to discourse revision.

`Store.snapshot_hash()` is an explicit audit command and is never called by normal commits.

## 7. Transition mechanism contract

A causal rule may reference variables only through named roles. Consequent variables must be bound by antecedents. Exact state dimensions are mandatory.

Forbidden:

```text
args[0] is actor
args[1] is target
if event type == charge: set battery
```

Required:

```text
antecedent role:actor = ?actor
consequent role:subject = ?actor
```

## 8. Capability contract

Capability assessment may normalize derived support to `[0,1]`, but the underlying dimensions retain native domains. Missing evidence is not silently positive. Cycles and dependency-depth overflow produce bounded unknown support and explicit blockers.

## 9. Response contract

Response CSIR must answer one of these questions:

- Which binding/proof should be surfaced?
- Which variable/evidence item blocks an answer?
- Which capability and dependency evidence supports the report?
- Which directive decision or operation result must be communicated?
- Which attributed claim/discourse obligation should be acknowledged?

A generic “evidence insufficient” response without a target is valid only when no narrower target survived cognition.

## 10. Acceptance invariants

- all stage records are strictly ordered 0–22;
- durable-write flags appear only at 13, 16, 17, 21, or final bookkeeping;
- no read-only revision changes;
- no normal-turn snapshot hash;
- no runtime call to full base-fact materialization;
- no punctuation or mode force override;
- no SessionSelf state injection;
- no implicit semantic atom creation;
- no predicted delta committed as observed state;
- no external effect without a registered authorized adapter;
- no unverified surface committed to common ground.


## Reviewed structural constants

Pack-local `CONST*` sources resolve only to authority-scoped atoms visible to the pinned generation. They permit general structural relations such as `rel:subtype_of` without a flat arbitrary-ontology prediction head.
