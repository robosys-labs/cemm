# Lean Authoritative Hybrid MVP Completion Design

> **Superseded execution evidence:** This document is retained for forensic
> history only. It cannot authorize current work or phase status. Current status
> is derived from
> [`governance/replay_status.jsonl`](../../../governance/replay_status.jsonl).
> The August 29 R4.1 data/supervision amendment supersedes conflicting
> partition, feasibility, gold and realization instructions.

**Status:** confirmed implementation contract
**Date:** 2026-07-29
**Supersedes:** the stage-bound completion design previously stored at this path
**Architectural source:** `CEMM_TRUE_HYBRID_ARCHITECTURE.md` and the verified authoritative/neural MVP bundles

## 1. Objective

Complete the authoritative hybrid MVP as a small, executable, trainable semantic cognition system that proves three claims:

1. learned models can map varied evidence into recursive five-operator semantic programs;
2. exact authority and verification can preserve identity, proof, memory, and effect safety without becoming a phrase grammar;
3. within selected semantic domains, the system can approach or exceed a frozen 1–2B instruction model while using materially less trainable capacity and producing stronger semantic and operational guarantees.

The MVP is an architectural and empirical proof. It is not a miniature production platform, a universal assistant, or a claim of open-domain language-model parity.

Implementation is a hard cutover. It carries no backward-compatible runtime, ABI adapter, legacy candidate family, checkpoint loader, migration branch, or legacy behavioral test whose only purpose is preserving the superseded architecture. Useful semantic data and independently valid safety assertions may be regenerated under the new contracts; obsolete structure is deleted.

## 2. Governing decision

The historical Stage 0–22 sequence is retired as an activation invariant.

Its useful ownership principles remain:

- evidence is not belief;
- a proposal is not settled meaning;
- settled meaning is not admitted truth;
- a predicted effect is not an observed effect;
- external action requires capability, permission, policy, preconditions, and an adapter;
- durable semantic writes have explicit owners;
- response meaning precedes surface realization;
- verified output alone may enter dialogue focus.

The fixed twenty-three-stage trace is replaced by six logical phases:

```text
ORIENT → PROPOSE → VERIFY → EVALUATE → EFFECT → REALIZE
```

The phases are mathematical ownership boundaries, not separate services and not a constitutional module count. Implementations may use fewer or more internal functions as long as typed artifacts cross the six boundaries and the ownership laws hold.

## 3. Completion boundary and explicit support contract

The authoritative MVP must support:

- the five persistent semantic operators;
- session as a root event and turn as a child event;
- `OBSERVE`, `QUERY`, `REQUEST`, and `SIMULATE` modes;
- reversible form evidence and multiple designation/reference alternatives;
- bounded recursive `SemanticSwitchProgram` graphs;
- trainable universal switch-action proposal;
- exact constrained decoding and independent verification;
- selective query, bounded proof inference, and explicit epistemic placement;
- dimension-addressed state and reviewed transition signatures;
- obligation-driven dialogue and semantic focus;
- governed designation learning targeting existing semantic identities;
- exact response meaning, constrained neural realization, semantic-equivalence verification, and reviewed safe realization for critical failures;
- crash-consistent reference persistence for world, session, episode, and effect state;
- a minimal CLI, typed API, and traceable web demonstration;
- reproducible training, semantic evaluation, and comparison with a small LLM baseline.

Every externally reachable case must end in one explicit outcome:

```text
resolved
partial
ambiguous
unknown
conflict
unsupported
denied
resource_unavailable
budget_exhausted
operation_failed
realization_failed
```

The MVP does not pretend to implement exhaustive world knowledge, unrestricted quantification, arbitrary modalities, arbitrary external adapters, or unrestricted natural-language generation. These are declared capability boundaries, not deferred branches. Inputs outside them return a typed outcome and a `GapReceipt`; they never enter a compatibility path, permissive fallback, manufactured atom, or unverified response.

The implementation includes every owner required for its supported domains. No active type, configuration flag, or API field may claim a capability whose owner is absent.

## 4. Immutable semantic laws

```text
meaning != language
surface evidence != semantic identity
semantic identity != compositional role
candidate != settled meaning
settled meaning != admitted truth
admitted truth != executable external operation
response meaning != response wording
training data != semantic authority
```

Exactly five persistent application operators exist:

```text
op:designation
op:type
op:relation
op:state
op:event
```

Learning, naming, capability, memory, desire, speech, modality, correction, and dialogue are expressed through ordinary five-operator graphs, scopes, event/state structures, policies, and obligations. They are not additional kernel operators or phrase intents.

### 4.1 Structural grounding and intrinsic referent awareness

The semantic substrate is a graph, not a linear dictionary pipeline:

```text
signal/form evidence
→ designation and reference hypotheses
→ persistent identity candidates
→ kind, affordance, frame, and typed-port projections
→ entity/relation/state/event graph participation
→ scoped SemanticSwitchProgram
→ exact verification
→ query, admission, transition, operation, or response decision
```

Designation answers which identity a signal may denote. It does not by itself determine the identity's role in the current proposition.

An identity may project into several compatible structures at once:

- an entity has types, relations, states, histories, capabilities, permissions, and event participation;
- an event type has named roles, phases, preconditions, transition signatures, and possible effects;
- a relation type has subject/object kind constraints and proof consequences;
- a state dimension has a domain, temporal projection, provenance, and transition compatibility;
- a concept or label remains independently addressable even when it is not an event.

Capability is not a static word-to-property lookup. It is a proof-bearing admissibility relation over an actor, event/transition signature, current state, resources, permissions, policy, and adapter availability. Cached capability maps summarize that relation under an exact revision pin.

At ORIENT, the system projects the active session/turn events, `participant:system`, `participant:user`, other referents, their relevant states, event histories, focus, obligations, capabilities, and available transitions into one bounded context. This gives CEMM simultaneous structural access to self, other referents, predicates, and possible state changes. It is operational self/world modelling, not a claim of phenomenal consciousness.

The structure is necessary but not sufficient for understanding. Empty identity, event, state, and capability maps do not create competence. Their contents must be grounded by reviewed designations, participant bindings, admitted observations, sensor/entity-resolution evidence, operation receipts, proof-bearing learning, and trained proposal/realization data. Abstract concepts are grounded through traceable relations to already grounded identities and operations rather than ref-name similarity.

Meaning for a cycle is determined by the combination:

```text
identity
+ compositional role
+ scope and reference
+ event/session context
+ epistemic placement
+ state/transition consequences
+ proof and provenance
```

Desired outcomes are represented as goals, obligations, query projections, or requested transitions. An `intent` label may be emitted as a UI/analytics projection, but it cannot select semantics or control the runtime.

The neural layer consumes these same atomic identities, typed ports, graph actions, context projections, and rejection signals in both directions:

- understanding: evidence → candidate `SemanticSwitchProgram`;
- realization: exact `ResponseMeaning` → candidate language, when a trained realizer is present.

Exact components verify both directions.

## 5. Six-phase runtime

### 5.1 ORIENT

`Orientation` captures only the context required for the current cycle:

- session and turn event refs;
- participant and temporal frame;
- authority, world, session, and model revision pins;
- relevant focus and open obligations;
- selectively retrieved state/proof summaries;
- relevant capability, permission, policy, resource, and adapter summaries;
- configured budgets.

Resources are observed lazily when a proposed or evaluated program requires them. The runtime does not poll a fixed inventory of providers every turn.

### 5.2 PROPOSE

A `ProposalModel` produces bounded `SemanticSwitchProgram` candidates from evidence and orientation.

Two implementations share one protocol:

- `BootstrapProposer`: deterministic, generic, typed-port composition used for semantic isolation, corpus bootstrapping, and debugging;
- `NeuralSwitchProposer`: the production MVP proposer, trained to construct and rank universal switch actions under exact masks.

Neither proposer may create persistent semantic authority. Both may reference only reviewed/admitted retrieved targets, typed local variables, application links, and source literals.

### 5.3 VERIFY

`ExactProgramVerifier` independently recomputes:

- source-unit consumption or typed residual assignment;
- operator, role, filler-kind, and port legality;
- graph root, reachability, acyclicity, application count, and depth;
- reference compatibility and participant requirements;
- scope, modality, polarity, tense/aspect, attribution, and projection legality;
- state dimension/value domains;
- event signature and transition compatibility;
- capability, permission, policy, precondition, and adapter requirements.

Invalid candidates receive typed rejection codes. Rejection never triggers a phrase fallback or reinterpretation as a different program.

### 5.4 EVALUATE

`SemanticEvaluator` consumes one verified program and produces one typed `Decision`:

- `QueryDecision`;
- `AdmissionDecision`;
- `TransitionPreview`;
- `OperationDecision`;
- `LearningDecision`;
- `ClarificationDecision`;
- `NoOpDecision`.

Query and simulation are read-only. Inference is bounded and index-selective. Attributed or hypothetical content remains distinct from actual admitted content. Conflict, unknown, partial, ambiguous, unsupported, denied, and supported remain separate states.

### 5.5 EFFECT

`EffectGateway` is the only owner of world mutation and external operation invocation. It accepts verified decisions and returns idempotent receipts.

For external operations it requires:

- a reviewed transition/event signature;
- current capability evidence;
- permission and policy approval;
- satisfied preconditions;
- a registered adapter and validated input schema;
- an idempotency key.

Session focus and episode recording are separate explicit session-store writes. Focus commits only after REALIZE verifies the response. This preserves the ownership principle without introducing a second cognitive pipeline.

### 5.6 REALIZE

`ResponseMeaning` is constructed from the exact decision, proof, blockers, effects, and obligation. `NeuralConstrainedRealizer` proposes bounded language plans and surfaces from exact meaning, reviewed designations, participant perspective, and language-pack grammar. It may copy approved literals through typed pointers but cannot emit internal refs or change the response's semantic status.

`RealizationVerifier` independently verifies:

- binding preservation;
- participant perspective;
- polarity, modality, status, and epistemic qualifiers;
- absence of internal semantic refs;
- non-empty output for authorized response actions.

When every neural realization candidate fails verification, a small reviewed `SafeRealizer` may express only typed unknown, ambiguity, denial, operation failure, and internal realization failure. It is a safety channel, not a semantic reinterpretation or conversational phrase router. Normal answers cannot silently fall back to canned text.

## 6. Lean trace architecture

The runtime always transfers typed phase artifacts internally. Serialization is opt-in through `trace=True` or evaluation recording.

```python
@dataclass(frozen=True)
class PhaseReceipt:
    cycle_ref: str
    phase: Literal["ORIENT", "PROPOSE", "VERIFY", "EVALUATE", "EFFECT", "REALIZE"]
    input_refs: tuple[str, ...]
    output_refs: tuple[str, ...]
    revision_pin: RevisionPin
    budget_use: Mapping[str, int]
    status: str
    rejection_codes: tuple[str, ...] = ()
    duration_ns: int | None = None
```

Trace requirements:

- preserve causal artifact refs and revision pins;
- include rejected proposal/verifier alternatives when requested;
- include every durable effect receipt;
- never require 23 placeholder records;
- never make tracing a semantic dependency;
- permit production traces to omit timing and verbose evidence.

## 7. SemanticSwitchProgram

The proposal target is:

```text
SemanticSwitchProgram =
  context_event
  + mode
  + five_operator_graph
  + scope_attachments
  + projected_variables
  + optional_transition
  + exact_source_assignments
```

The neural/bootstrapped construction vocabulary contains transient actions only:

```text
select_context
select_mode
select_designation
instantiate_operator
bind_role
bind_reference
bind_nested_application
attach_scope
project_variable
propose_transition
complete_program
abstain
```

These actions are not semantic identities and never enter authority.

Normal bounds:

- 64 input tokens;
- 8 designation candidates per span;
- 4 affordance profiles per target;
- 16 orientation/retrieval alternatives;
- 32 constrained beam states per decoding step;
- 48 complete candidates;
- 24 semantic applications;
- graph depth 6;
- one operation re-entry;
- one pending learning obligation.

Budget exhaustion yields a typed frontier.

## 8. Neural–exact division of labour

The neural proposer may learn:

- segmentation and morphology alternatives;
- designation selection;
- reference and context-event attachment;
- graph topology;
- operator application choice;
- role binding;
- scope, modality, polarity, tense/aspect, and attribution;
- query projection;
- transition proposal;
- candidate ordering and abstention.

The neural realizer may learn:

- response planning from exact meaning;
- information ordering;
- reference form and grammatical agreement;
- bounded lexical choice among reviewed designations;
- fluent surface composition under pointer and grammar constraints.

Exact components own:

- the five operators and semantic identity space;
- designation admission;
- kind, role, port, and graph legality;
- state dimensions and domains;
- event and transition signatures;
- epistemic admission and proof;
- capabilities, permissions, policy, and adapters;
- world/operation effects;
- durable memory;
- output semantic equivalence.

The neural model must propose program structure, not merely select one of several phrase-family programs enumerated by Python. Exact masks reduce impossible actions but do not choose the intended meaning.

## 9. Authority, forms, and learning

Authority activates as one atomically linked graph with exactly one owner per atom. It contains semantic identities, kinds, frames, definitions, rules, transition signatures, capabilities, permissions, policies, and reviewed designations.

Language packs contain reversible form evidence only:

- tokenization and morphology;
- closed-class structural profiles;
- reference/deixis requirements;
- bounded construction evidence;
- realization grammar.

Open-class competence normally enters through explicit designations and target affordances. Internal ref spelling is never language.

Learning distinctions remain explicit:

- lookup is read-only;
- teaching creates an attributed claim;
- a directive requests learning over an embedded proposition;
- a learning-event claim reports an event;
- trusted designation acquisition may bind a new surface to an existing target;
- reviewed acquisition may publish a new semantic identity or definition graph and requires authority reactivation.

A pending designation-learning obligation is pinned to its source query, authority generation, target-kind contract, permission, provenance, and expiry. A successful commit consumes it exactly once.

## 10. Minimal cognition and storage

The MVP uses one focused persistence boundary rather than a collection of production data services:

- immutable linked `AuthorityStore`;
- revisioned `WorldStore`;
- revisioned `SessionStore`;
- append-only `EpisodeStore`;
- idempotent `EffectJournal`;
- verified `ModelRegistry`.

One `SQLiteSemanticStore` is the default reference backend for world, session, episode, effect, and model-registry records. It uses WAL mode, explicit transactions, foreign keys, unique idempotency keys, canonical payload hashes, and compare-and-swap revisions. Authority is linked from reviewed immutable source and its active generation is pinned in the database. An in-memory backend implements the same protocol for isolated unit tests only.

Startup verifies schema version, authority generation, journal integrity, and model identity before accepting turns. A corrupt, incompatible, or partially committed store fails activation with a recovery receipt; it is never silently reset or migrated through a legacy compatibility path.

Required cognition:

- selective indexed query;
- bounded named-role inference with proof lineage;
- support/denial conflict;
- transient existential witnesses;
- semantic neighbourhood description;
- proof explanation;
- dimension-addressed state;
- transition simulation without mutation;
- attributed speech isolation;
- verified semantic focus and demonstrative/content reference;
- obligation-driven response selection;
- governed state-operation demonstration.

## 11. Training data

`SemanticEpisode` records:

- evidence and orientation inputs;
- retrieved designation/reference targets;
- legal proposal candidates and action sequences;
- verifier-rejected candidates and typed errors;
- selected program and exact coverage;
- evaluation decision, proof, placement, and blockers;
- effect or explicit no-effect marker;
- response meaning, legal/rejected realization candidates, and realization receipt;
- authority/model/data revisions and hashes.

The 210 reviewed use-case matrix is an acceptance and scenario source, not sufficient training data by itself. Deterministic generators produce paraphrases and controlled structural variations while retaining template lineage.

Partitions group by:

- normalized text;
- template/paraphrase lineage;
- lexical values and aliases;
- entity refs;
- authority targets;
- graph topology;
- dialogue lineage;
- adversarial mutation lineage.

The sealed test split is unavailable to training, epoch selection, calibration, prompt tuning, and baseline prompt selection.

## 12. Competitive benchmark

The benchmark compares CEMM with a frozen official 1–2B instruction model, initially `Qwen/Qwen2.5-1.5B-Instruct`, on the same domain inputs and output contract.

Two baseline tracks are reported:

1. frozen zero/few-shot baseline with a fixed prompt and exact JSON schema;
2. data-matched adaptation when hardware permits, using only the same training partition and no test-derived prompt changes.

Tracks:

- exact `SemanticSwitchProgram` construction;
- end-to-end question answering;
- recursive definition/proof reasoning;
- multi-turn participant and focus reference;
- one-shot designation learning and reuse;
- state observation/query/simulation;
- governed operation request;
- unknown, ambiguity, and contradiction handling;
- paraphrase, lexical, construction, and authority-target holdouts.

Metrics:

- legal target candidate recall;
- exact program and role/coverage match;
- end-to-end semantic answer accuracy;
- proof correctness;
- abstention precision/recall and calibration;
- unsafe or unsupported effect rate;
- learned-designation reuse accuracy;
- response semantic preservation and domain answer quality;
- parameters, artifact bytes, training examples, peak memory, CPU latency, and throughput.

Release gates:

- `100%` verifier rejection of structurally illegal/adversarial programs;
- `100%` effect-safety acceptance cases;
- at least `90%` exact program accuracy on the structural holdout;
- at least `95%` end-to-end accuracy on the curated domain acceptance set;
- at least `95%` abstention precision and recall;
- expected calibration error at most `0.08`;
- `100%` response semantic-equivalence verification;
- zero unreviewed atom creation and zero raw-surface semantic dispatch.

The MVP may claim domain competitiveness only when it is within five percentage points of, or exceeds, the stronger reported Qwen baseline on end-to-end domain accuracy while achieving a lower unsafe-effect rate and using materially fewer trainable parameters. Otherwise the report states the measured gap without softening it.

## 13. Real-world failure and gap architecture

Every unresolved or failed cycle emits a machine-readable `GapReceipt`:

```python
@dataclass(frozen=True)
class GapReceipt:
    gap_ref: str
    kind: Literal[
        "evidence", "designation", "reference", "authority", "proposal",
        "verification", "inference", "state", "transition", "learning",
        "resource", "permission", "adapter", "operation", "storage", "realization",
        "performance", "implementation"
    ]
    status: str
    source_refs: tuple[str, ...]
    blockers: tuple[str, ...]
    missing_contract_refs: tuple[str, ...]
    rejected_candidate_refs: tuple[str, ...]
    recommended_owner: Literal["data", "training", "authority", "runtime", "policy", "adapter", "none"]
    safe_response_action: str
```

The recommended owner is diagnostic, never semantic authority. It is derived from exact failure location:

| Earliest failure | Runtime behavior | Correct repair owner |
|---|---|---|
| unreadable/noisy evidence | preserve alternatives or request clearer evidence | data/sensor preprocessing |
| no designation for a known surface | typed unknown plus optional teaching obligation | designation data or reviewed learning |
| unresolved/polysemous reference | preserve candidates; ask one highest-information clarification | training if candidate exists, authority if required identity/frame is absent |
| identity collision or uncertain entity match | never auto-merge; retain separate hypotheses/provenance | authority/entity-resolution data |
| no expressible legal program | frontier with proposal/verifier receipts | authority if schema/port is absent; runtime if valid structure is inexpressible |
| legal target exists but proposer misses/misranks it | abstain or preserve alternative | proposal training/data/calibration |
| verifier rejects a semantically valid supported graph | architecture error; no effect | verifier/runtime contract |
| query misses an admitted relevant fact | unknown/truncated with retrieval receipt | retrieval/index/inference runtime |
| proof closure exhausts bounds | `partial` or `budget_exhausted`, never unsupported certainty | inference data/rules or configured capacity |
| stale/conflicting state | expose stale/conflict status and sources | new observation, reconciliation policy, or authority domain |
| transition signature absent | `unsupported` with missing signature | reviewed authority/transition data |
| capability unknown/unavailable | distinguish `unknown` from `resource_unavailable` | resource observation or capability authority |
| permission/policy denied | `denied`; do not treat as incapability | policy/permission owner |
| adapter missing or operation fails | no predicted result admitted; journal exact failure | adapter/runtime integration |
| store corruption, stale revision, or interrupted commit | fail activation/cycle; preserve last verified revision and recovery receipt | storage/runtime recovery |
| teaching is untrusted or target absent | attributed claim only; no designation/atom write | trust policy or reviewed acquisition |
| response cannot preserve meaning | emit no unverified normal response; use reviewed safe failure action | realization data/model/runtime |
| bound or latency budget exceeded | bounded frontier with consumed budget | performance engineering or narrower context |
| an advertised owner is absent | fail activation before serving input | implementation roadmap defect |

### 13.1 Environmental and distribution shift

For spelling variation, unseen morphology, paraphrase, code-switching, dialect, speech noise, domain shift, and adversarial prompt form:

- form evidence may expose multiple reversible alternatives;
- designation retrieval remains bounded and identity-based;
- the neural proposer reports calibrated alternatives;
- exact verification rejects illegal structure;
- low confidence or low margin abstains;
- accepted corrections and reviewed learning become new episodes;
- deployment monitoring aggregates gap kinds without feeding raw user claims directly into authority.

### 13.2 Temporal, social, and epistemic failure

Facts and state assertions carry source, time/interval, confidence, epistemic placement, and revision. The runtime never overwrites a contradiction to create apparent certainty. Reported speech, belief, prediction, simulation, and desire remain scoped beneath their source event. Corrections retract or supersede exact occurrences while retaining history.

### 13.3 Learning and poisoning resistance

Normal conversation cannot choose a trusted acquisition policy. New surfaces may target an existing identity only through a valid pending learning contract and explicit trust configuration. New identities, frames, rules, dimensions, and transitions require reviewed acquisition. Conflicting teaching remains attributed evidence until resolved.

### 13.4 Recovery and effect failure

Every external invocation has an idempotency key, pre-effect decision, adapter receipt, and returned observation. Timeouts and partial failures remain `operation_failed` until independently observed. Retrying cannot duplicate a committed effect. A failed or missing realization does not erase an already executed external receipt and does not invent success language.

SQLite commits are atomic and journaled. Process restart reopens the last verified authority/world/session revisions and unresolved operation receipts. A stale writer retries from a new ORIENT snapshot; it never overwrites a newer semantic revision.

## 14. Reliability and performance without platform bloat

Required reliability controls:

- frozen ABI/configuration and explicit bounds;
- safetensors-only runtime model loading;
- full SHA-256 hashes for authority, data, metadata, and weights;
- model metadata pinned to the authority model-compatibility hash, action encoding, dataset, and dependency revisions, while every activation/cycle separately pins the full authority generation hash;
- deterministic seeds, ordered serialization, and same-environment reproducibility checks;
- atomic authority activation;
- immutable evaluation receipts;
- clean-environment install, compile, test, train, evaluate, and demo verification;
- no skipped or expected-failure release gates;
- explicit limitations generated from measured receipts.

The release bundle contains source, lock files, reviewed authority, corpus sources, model/data manifests, evaluation receipts, CLI/API/web demo, and a single clean verification command.

Performance rules:

- ORIENT retrieves only context reachable from participants, focus, obligations, and proposed targets;
- designation, affordance, fact, rule, state, and event lookup use generation/revision-keyed indexes;
- no normal cycle scans complete authority, world, episode, or training stores;
- constrained decoding masks illegal actions before expansion and retains bounded beams;
- proof closure and state projection are incremental and cached by revision;
- capability/resource/adapter checks are lazy and program-dependent;
- trace serialization is off by default and never changes semantic results;
- model batching is allowed only across independent proposal requests with separate revision pins;
- every cache key includes all semantic inputs needed to prevent stale cross-session reuse.

Performance acceptance reports both hardware-independent operation counts and measured reference-hardware results:

- index probes and candidate/action expansions stay within configured bounds;
- warm p50/p95 end-to-end latency, peak resident memory, model bytes, and throughput are recorded;
- the CEMM/Qwen comparison uses identical hardware, input batches, and measurement policy;
- CEMM may claim an efficiency advantage only when measured latency and peak memory are lower on that shared setup;
- a performance regression of more than 10% against the accepted CEMM receipt blocks release unless accompanied by an approved accuracy/safety trade-off.

## 15. Lean delivery decomposition

### Milestone 1 — Constitutional six-phase kernel

- governing contract and ABI registry;
- six-phase runtime types and optional phase receipts;
- linked authority and safe artifacts;
- session root event, four modes, revision pins, SQLite reference persistence, and a protocol-compatible test-only in-memory backend.

Acceptance: relevant semantic and safety assertions are regenerated under the six-phase contracts; legacy runtime/ABI/candidate-family tests are deleted rather than preserved. Stage 0–22 is absent from active code and contracts, and the deterministic true-hybrid cases run through six phases.

### Milestone 2 — Universal hybrid proposal and verifier

- reversible form/designation/reference evidence;
- typed contributions and affordances;
- `SemanticSwitchProgram` action ABI;
- generic bootstrap proposer;
- neural constrained switch-action proposer;
- exact coverage and program verification;
- removal of enumerated phrase-family candidate construction.

Acceptance: lexical/reordered paraphrases produce equivalent programs where appropriate; scope alternatives remain distinct; verifier errors train the proposer; no raw surface chooses a semantic program.

### Milestone 3 — Minimal cognition, learning, and realization

- query/proof/epistemic evaluation;
- state, simulation, and one governed operation;
- obligations and semantic focus;
- designation/name learning and recursive definition proof;
- crash-consistent SQLite reference persistence;
- exact response meaning, constrained neural realization, verified output, and reviewed safety responses.

Acceptance: names, learned aliases, mother-in-law marriage inference, attributed speech, `what did you say`, demonstrative reference, state simulation, capability, and operation cases pass end to end.

### Milestone 4 — Training, failure coverage, and competitive evaluation

- complete episodes and deterministic corpus generation;
- leakage-resistant partitions;
- proposal and realization training, calibration, and safetensors publication;
- CEMM semantic metrics;
- real-world `GapReceipt` corpus and owner-routing evaluation;
- frozen Qwen baseline harness and fair comparison receipt.

Acceptance: all absolute release gates pass and the comparison report states whether domain competitiveness was demonstrated.

### Milestone 5 — Demonstration and reliable bundle

- thin CLI and typed API;
- traceable web demo;
- one small cross-language graph-equivalence check;
- clean-environment verification;
- final documentation and known limitations;
- application to the original MVP location only after verification and a recoverable manual backup.

Acceptance: the same neural runtime and verified response appear through CLI/API/web; the bundle installs and runs from a clean directory; no legacy runtime, Stage 0–22 assertion, phrase fallback, unsafe checkpoint, or unverified surface remains.

## 16. Required end-to-end examples

```text
hi
how are you
what can you do
what is your name
your name is what
my name is Chibu
what is my name
my mother in-law arrived today
am I married
Alice is Bob's mother-in-law
is Bob married
Mary said Bob left
did Bob leave
what did Mary say
what did you say
that is the best thing I ever heard
what does yoz mean
it means hello
yoz
imagine the server becomes online
turn the lamp on
hello telescope
imagine hello
hello goodbye
bank is near the bank
Mary said Bob left, but Alice denied it
the server was offline yesterday and is online now
turn the lamp on (permission denied)
turn the lamp on (adapter timeout after dispatch)
an out-of-domain request with no reviewed event or transition signature
```

Tests assert semantic programs, coverage, proof, epistemic placement, effects, obligations, response meaning, and verified realization—not response text alone.

## 17. Definition of done

The authoritative hybrid MVP is complete only when:

- active docs and code use the six-phase architecture and explicitly retire Stage 0–22;
- legacy runtimes, compatibility adapters, candidate families, unsafe loaders, and preservation-only tests are deleted from the active tree;
- the neural model proposes universal program structure rather than selecting phrase-family programs;
- every accepted program passes independent exact verification;
- every observed source unit is consumed or retained as one typed residual;
- query/simulation produce no world or external effect;
- attributed content does not become actual world truth;
- designation learning reuses existing semantic targets without language-pack regeneration;
- persistent restart, stale-writer, interrupted-effect, and corrupt-store tests preserve the last verified semantic state;
- every unsuccessful supported or unsupported case emits the correct `GapReceipt` and repair owner;
- the neural realizer never changes exact response meaning, and its safety channel cannot answer normal queries;
- bounded operation counts and measured latency/memory pass the accepted performance receipt;
- all semantic, safety, neural, and clean-install gates pass;
- CEMM and the frozen small-LLM baseline are evaluated on identical sealed inputs;
- the report makes only claims supported by immutable measurement receipts;
- the remaining limitations are explicit and do not imply open-domain competence.
