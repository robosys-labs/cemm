# R5 Neural Activation and R6 Composition Design

> **Conditional target:** The August 29 R4.1 data/supervision amendment has
> precedence. No training, model selection, calibration, frozen evaluation,
> realization publication or activation task in this document is executable
> until fresh R4.1 admission authenticates semantically useful purpose classes,
> independent reviewed derivations and reviewed response surfaces.
> R4.1 is an external prerequisite implemented and admitted outside this
> document. Current status is derived only from
> [`governance/replay_status.jsonl`](../../../governance/replay_status.jsonl).
> This document cannot implement, rebuild, publish, or admit R4.1.

**Date:** 2026-08-22  
**Status:** reviewed pre-implementation target design  
**Scope:** `hybrid_mvp/` only  
**Predecessors:** R5 hard-cut foundation; separately implemented and freshly admitted R4.1 data/supervision contract
**Supersession:** refines the R5/R6 portions of the 2026-07-31 master plan; does not weaken the R5 foundation hard cut

## 1. Decision

R5 and R6 are implemented as two separately admitted increments:

```text
fresh R4.1 admission
  -> R5 neural activation
       -> proposer training and selection
       -> realizer training and selection
       -> confidence calibration
       -> reproduction and weight-use proof
       -> exact runtime activation and realization
       -> R5 admission
  -> R6 composition and surfaces
       -> one composition root
       -> CLI/API/web/evaluation transport adapters
       -> parity and operational proof
       -> R6 admission
```

R5 creates learned semantic proposal and learned surface realization while exact
owners retain semantic truth, effects, legality, and equivalence authority. R6
does not add intelligence; it exposes the admitted runtime through one
composition root.

## 2. Non-negotiable external predecessor

R4.1 is an external prerequisite. This design neither implements nor admits it.
No R5 implementation, training, selection, calibration, activation, or
admission may execute unless the ledger identifies one fresh R4.1 admission
whose reviewed contracts authenticate meaningful purpose-class semantic
coverage, independent derivation and abstention supervision, and reviewed
ResponseMeaning-to-surface supervision. The implementation head must descend
monotonically from that admitted source and the governed checkout must be clean.

Historical R4 partition or receipt reconstruction is diagnostic only and cannot
authorize R5.

## 3. Ownership boundaries

### 3.1 Exact owners retained

The following remain non-neural authority:

- form evidence and source geometry;
- designation and grounding;
- ProposalContext construction;
- legal action enumeration and masks;
- Program ABI validation and expression compilation;
- VerificationBatch and VerifiedMeaning;
- SituationContext;
- decisions, proof, effects, learning obligations, and ResponseMeaning;
- semantic round-trip equivalence;
- governance, admission, and artifact integrity.

### 3.2 R5 learned owners

R5 may own only:

- ranking and decoding among currently legal structural actions and pointers;
- explicit abstention score;
- constrained surface-unit decoding and literal-copy choice;
- calibrated confidence transformation.

A model cannot create authority refs, semantic operators, roles, permissions,
capabilities, adapters, or effects.

### 3.3 R6 owners

R6 owns:

- typed composition request and result envelopes;
- admitted-runtime construction;
- session/evidence/deadline/idempotency plumbing;
- CLI, API, web, and evaluation transport adapters;
- surface parity and operational receipts.

R6 adapters do not inspect or route semantic content.

## 4. Four-class data firewall

The classes have disjoint purpose and process owners.

| Class | Permitted use | Forbidden use |
|---|---|---|
| `train` | optimizer fitting and train-only preprocessing | selection, calibration, evaluation |
| `selection` | choose proposer/realizer checkpoint and approved hyperparameters | optimizer updates, confidence calibration |
| `calibration` | fit calibrator for already selected frozen checkpoints | checkpoint selection, optimizer updates |
| `frozen_test` | R7 authentic evaluation only | any R5/R6 process |

Every worker receives a purpose-specific capability and authorization exposing
only one class. Sibling class identity is not present in its object graph,
environment, command line, log, receipt, filesystem namespace, or API.

Selection and calibration processes run in fresh process trees without train
objects. Frozen test remains physically unopened until R7.

## 5. Target ABIs

These ABIs are registered before their implementations are admitted. One
canonical JSON codec and one safe-tensor loader serve all variants; a
lifecycle stage or evidence kind does not receive a duplicate serializer.

### R5

1. **Neural Feature Schema ABI 1** — exact structural feature and
   context-local pointer-slot schema; excludes internal ref spelling and
   authority-wide vocabularies.
2. **R5 Purpose Snapshot ABI 1** — one immutable discriminated projection
   with `purpose` equal to `train`, `selection`, or `calibration`; separate
   mint/open owners enforce the one-class firewall.
3. **Proposal Checkpoint ABI 1** — safe tensors, architecture, feature and
   action schemas, source, authority, train capability, config, and tensor
   identity.
4. **Realizer Checkpoint ABI 1** — safe tensors, decoder vocabulary,
   literal-copy schema, ResponseMeaning ABI, source, authority, train
   capability, config, and tensor identity.
5. **R5 Lifecycle Receipt ABI 1** — a strict discriminated union for
   `training`, `selection`, `calibration`, `reproduction`, and `weight_use`;
   each kind has an exact bounded body and shared provenance envelope.
6. **R5 Activation Bundle ABI 1** — selected checkpoints, calibrator,
   runtime config, authority, feature/action/response ABIs, canary set,
   dependency lock, and source.
7. **R5 Activation Canary Receipt ABI 1** — fresh public-runtime
   observations covering proposal, abstention, realization, failure,
   restart, and exact round-trip meaning.

### R6

1. **Composition Request ABI 1** — request/session/evidence/deadline,
   idempotency, and trace policy.
2. **Composition Result ABI 1** — cycle result, verified surface, exact
   realization receipt, final revision, and bounded diagnostics.
3. **R6 Evidence Receipt ABI 1** — a strict discriminated union for
   `adapter`, `parity`, and `operational_budget` evidence.

No “latest model” pointer or directory selection participates in authority.

## 6. Efficiency and anti-bloat contract

### 6.1 Budget before architecture

Task 2 creates a reviewed resource-budget configuration before any model
implementation. It freezes hard ceilings for combined selected checkpoint
bytes, parameter count, cold activation, peak RSS, p50/p95 proposal,
verification, realization and end-to-end latency, maximum beam width,
decoder steps, live states, round-trip candidates, trace/report bytes,
artifact count/bytes, runtime dependency count, and import time. A later
implementation may reduce a ceiling but cannot raise one without a
separate reviewed design change.

R5 has one deterministic CPU release/reference backend. Accelerator,
quantization, distributed training, speculative decoding, and streaming
are out of scope until measured evidence shows that the admitted CPU path
cannot meet the frozen product budget.

### 6.2 Hot-path rules

- activation verifies manifests, model bytes, authority, schemas, and
  source once, then retains immutable verified handles;
- no Git, subprocess, filesystem discovery, whole-artifact rehash,
  training, calibration, or JSON serialization occurs per request;
- ProposalContext features and context-local pointer embeddings are built
  once per request and reused across decoder steps;
- pointer scoring is vectorized, legality masks apply before probability
  computation, and masked candidate objects are not materialized;
- inference uses `eval()` and `torch.inference_mode()` with reviewed thread
  limits and bounded reusable buffers;
- immutable canonical refs are memoized on object construction;
- exact verification runs over a bounded top-k final set, not an unbounded
  beam history;
- realization batches its bounded neural candidates through round-trip
  verification and returns typed failure when none is equivalent;
- default traces exclude tensors, logits, raw datasets, and full search
  histories.

### 6.3 Code, dependency, and artifact rules

R5 uses at most five active owner modules and shared canonical codecs; it
does not create a module/class/schema per receipt variant. Existing
superseded model/training owners are removed in the same lineage rather
than wrapped or re-exported. No new runtime dependency is allowed without
measured necessity and a reviewed impact on startup, memory, supply-chain,
and cross-platform behavior.

Candidate training weights live in bounded scratch or CI storage. Git
receives only the selected proposer and realizer when their combined size
is below the frozen repository budget; otherwise implementation stops for
an artifact-store design. Receipts retain hashes, refs, aggregate metrics,
and typed failures, never duplicate model bytes, datasets, per-example
logits, or unbounded traces.

R6 has one CLI adapter, one shared HTTP adapter for API and web, and one
evaluation boundary. The initial increment has no streaming and no
second server stack.

## 7. Neural proposer design

The proposer is an autoregressive constrained decoder over one
`ProposalContext`.

### Inputs

- exact form-unit structural features;
- contribution kind and source geometry;
- orientation/session structural features;
- current Program ABI prefix;
- context-local legal action table;
- context-local pointer tables.

### Outputs

Use separate heads:

- action type;
- operator/mode where licensed;
- application-local pointer;
- role pointer;
- contribution/source-unit pointer;
- designation/reference/scope/link/variable/transition pointer;
- complete/abstain;
- confidence/abstention score.

The exact `ActionMasker` applies before softmax, loss, beam expansion, and final
selection. Masked actions have no finite selection probability.

Dynamic pointers are learned over anonymized context-local slots. An all-zero
pointer encoder, arbitrary “best legal candidate” substitution, internal ref
spelling, or authority-wide output vocabulary is forbidden.

Candidate order is randomized during training and evaluation. Equivalent
permutations must preserve semantic distributions. Search is bounded by exact
beam, step, state, memory, and time limits. Form, orientation, context, and
pointer-table encodings are computed once; decoder steps reuse cached tensors
and score pointer tables in batches rather than rebuilding candidate objects.

## 8. Neural realizer design

The realizer consumes exact `ResponseMeaning` plus licensed literal pointers.
It does not receive a raw Decision, program, source query, or internal semantic
ref spelling.

It decodes a bounded reviewed surface-unit vocabulary with:

- language-pack units;
- structural discourse/morphology units;
- literal-copy actions bound to exact pointers;
- end and abstain/failure actions;
- legality masks from the realization contract.

Hashing the whole target surface into a class, selecting canned sentences, or
falling back to a template is forbidden. The normal surface must depend on
loaded weights. Every candidate is reinterpreted through the same public
evidence/proposal/verify contracts and accepted only on canonical expression
equivalence with required situated qualifiers.

A bounded top-k set of neural candidates is decoded and round-trip checked
in one batch where possible. Failure yields a typed no-surface result, never a
semantically invented fallback.

## 9. Training, selection, and calibration

### Training

- train capability only;
- deterministic CPU reference run;
- fixed dependency lock and Python ABI;
- safe tensors only;
- train-only preprocessing;
- negative and abstention examples;
- per-step masked losses;
- no selection/calibration metrics used to update weights;
- resource and process-tree budgets.

### Selection

- selected from a committed candidate set;
- selection capability only;
- proposer and realizer may be selected independently;
- deterministic metric definitions and tie-break;
- capacity, latency, abstention, semantic accuracy, round-trip success, and
  robustness are explicit dimensions;
- selected weights become immutable before calibration;
- non-selected candidate weights remain outside Git and are deleted after
  selection and reproduction, while their bounded hashes and metrics remain.

### Calibration

- calibration capability only;
- receives selected immutable model identities;
- uses actual model scores, not fixed epistemic labels;
- records nonempty bins and non-vacuous denominators;
- cannot alter checkpoint weights or selection;
- threshold policy is content-addressed.

## 10. Reproduction and weight-use proof

A clean second training run occurs in scratch outside the repository. It must
compare independently:

- every artifact byte;
- every tensor name, dtype, shape, and byte sequence;
- model identity;
- metadata and manifest;
- training report and provenance.

Weight-use tests require:

- loaded selected identity recorded in each proposal/realization receipt;
- decoder invocation counts;
- normal outputs fail closed when weights are unavailable;
- zeroed/ablated proposer loses learned selection accuracy;
- zeroed/ablated realizer loses learned realization accuracy;
- no bootstrap/static/template delegate becomes active.

Ablation thresholds are established from measured baseline evidence and frozen
before admission.

## 11. Runtime activation

The release runtime starts only from one exact `R5ActivationBundle`.

Startup verifies all artifact, source, authority, ABI, lock, calibration, and
selection identities once before tensor use. Missing, mismatched, unsafe, dirty,
or ambiguous artifacts fail startup. Per-request receipts bind the retained
verified identities and never rehash or rediscover the artifact graph.

The canonical runtime owners become:

```text
orientation
proposal          # selected NeuralSwitchProposer
verification      # exact verifier
r3
realization       # selected neural realizer + exact round-trip verifier
```

The R3 `contract:r5:realize_surface` gap is replaced only in an admitted R5
profile. Development remains explicitly diagnostic and cannot masquerade as
release.

The final REALIZE phase binds `ResponseMeaning`, surface, model identity,
decoder trace summary, round-trip VerifiedMeaning/expression, and exact
RealizationReceipt.

## 12. R6 composition root

R6 introduces one public construction API, conceptually:

```python
class CompositionRoot:
    @classmethod
    def load(cls, root: Path, activation_ref: str, ...) -> "CompositionRoot": ...
    def process(self, request: CompositionRequest) -> CompositionResult: ...
    def close(self) -> None: ...
```

Properties:

- exact activation ref is required;
- no filesystem “latest” discovery;
- one runtime instance per configured lifecycle;
- typed deadline and cancellation propagated through owners;
- idempotency bound to effect processing;
- bounded output and trace policy;
- deterministic cleanup;
- thread/process safety is tested, not assumed.

CLI, API, web, and evaluation adapters depend only on this interface and
transport codecs. They may not import model, training, proposer, verifier,
realizer, decision, or effect implementation modules.

The evaluation adapter accepts cases but cannot open frozen-test capability at
R6. R7 injects that capability later.

## 13. Security and reliability

- `safetensors` only; no pickle, `torch.load`, dynamic code, or arbitrary
  object deserialization;
- canonical JSON with duplicate-key, nonfinite, unknown-field, and size
  rejection;
- path containment and no symlink/junction/reparse traversal;
- transactional stage/current/backup publication with fsync and rollback;
- process-tree timeout and cancellation on Linux and Windows;
- bounded stdout/stderr/report capture;
- no secrets or raw sensitive evidence in default logs;
- receipts contain refs, hashes, counts, typed codes, and bounded timings;
- crash/retry tests prove no half-activated bundle;
- training/reproduction never run on request paths.

## 14. Validation and admission

### R5 owner tiers

Foundation owners plus:

```text
data-capability
feature-schema
proposal-model
realization-model
training
selection
calibration
reproduction
weight-use
activation-bundle
runtime-activation
activation-canaries
artifact-integrity
structural-hard-cut
```

### R6 owner tiers

```text
composition-abi
composition-root
cli-adapter
http-adapter
evaluation-adapter-boundary
surface-parity
cancellation-idempotency
operational-budgets
structural-hard-cut
```

Owner and phase selectors are exact and disjoint. Admission performs one fresh
active-set execution and binds deterministic generated artifacts. Expensive
training/reproduction occur only when their content-addressed inputs changed,
but cached diagnostics never admit.

## 15. Stop conditions

Stop and retain red status when any of these holds:

- fresh R4.1 admission is absent or no longer current;
- a worker can discover a sibling data class;
- frozen test is touched before R7;
- a bootstrap or static release path remains reachable;
- model output depends on ref spelling;
- a legal mask is not applied at every decision point;
- training is nondeterministic under the declared reference environment;
- calibration uses non-model confidence;
- reproduction compares only metadata or model ID;
- a normal response has a fallback;
- a surface adapter semantically routes input;
- multiple production roots exist;
- any admission evidence is dirty, missing, ambiguous, or stale;
- a frozen resource ceiling is exceeded or raised inside an implementation task;
- non-selected weights, duplicated payloads, unbounded traces, or a new runtime
  dependency enter the release lineage without separate review.

## 16. Definition of done

R5 is complete only after all 25 deferred `R5-Neural-Activation` assertions have
exact executable successors, the activation bundle and fresh canaries pass, R5
admission is current-source green, and R6 remains red.

R6 is complete only after every supported adapter executes through the same
composition root with exact parity, all frozen size/latency/RSS/dependency
budgets pass, R6 admission is current-source green, and frozen-test evaluation
remains unopened for R7.
