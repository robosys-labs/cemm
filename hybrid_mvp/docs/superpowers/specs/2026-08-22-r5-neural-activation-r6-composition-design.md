# R5 Neural Activation and R6 Composition Design

**Date:** 2026-08-22  
**Status:** reviewed pre-implementation target design  
**Scope:** `hybrid_mvp/` only  
**Predecessors:** R5 hard-cut foundation; current-source R4 Build Receipt ABI 4 admission  
**Supersession:** refines the R5/R6 portions of the 2026-07-31 master plan; does not weaken the R5 foundation hard cut

## 1. Decision

R5 and R6 are implemented as two separately admitted increments:

```text
current R4 ABI-4 admission
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

## 2. Non-negotiable predecessor

No R5 implementation, training, selection, calibration, activation, or
admission may execute unless:

1. effective governance status is green through R4;
2. the R4 green row consumes one passed current-source admission receipt;
3. the receipt reconstructs Build Receipt ABI 4;
4. the global four-class graph, split manifest, sufficiency, class
   capabilities, class authorizations, and artifact graph all reconstruct;
5. the implementation head descends monotonically from the admitted source;
6. the governed checkout is clean.

Historical ABI 3 reconstruction is diagnostic only and cannot authorize R5.

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

These ABIs are registered before their implementations are admitted.

### R5

1. **Neural Feature Schema ABI 1** — exact structural feature and pointer-slot
   schema; excludes internal ref spelling and raw authority-wide vocabularies.
2. **R5 Training Input Snapshot ABI 1** — one immutable purpose-bound class
   projection and provenance.
3. **Proposal Checkpoint ABI 1** — safe tensors, architecture, feature schema,
   action schema, source, authority, train capability, config, and tensor
   identity.
4. **Realizer Checkpoint ABI 1** — safe tensors, decoder vocabulary, literal
   copy schema, ResponseMeaning ABI, source, authority, train capability,
   config, and tensor identity.
5. **Training Receipt ABI 1** — exact inputs, deterministic environment,
   optimizer, epochs/steps, losses, resource use, output identities.
6. **Selection Receipt ABI 1** — selection capability, candidate set,
   per-candidate metrics, deterministic tie-break, selected identities.
7. **Calibration Receipt ABI 1** — calibration capability, selected model
   identities, score definition, bins, ECE, thresholds, calibrator identity.
8. **Reproduction Receipt ABI 1** — independent scratch path, second-run
   artifacts, byte/tensor/model identity comparisons.
9. **Weight-Use Receipt ABI 1** — invocation counts, model identity,
   zero-weight/ablation degradation and no fallback.
10. **R5 Activation Bundle ABI 1** — selected checkpoints, calibrator, runtime
    config, authority, feature/action/response ABIs, canary set, source.
11. **R5 Activation Canary Receipt ABI 1** — fresh public-runtime observations
    covering proposal, abstention, realization, failure, restart, and exact
    round-trip meaning.

### R6

1. **Composition Request ABI 1** — request/session/evidence/deadline/idempotency
   and trace policy.
2. **Composition Result ABI 1** — cycle result, verified surface, exact
   realization receipt, final revision, bounded diagnostics.
3. **Surface Adapter Receipt ABI 1** — transport input/output and composition
   request/result bindings.
4. **Surface Parity Receipt ABI 1** — identical semantic and effect identities
   across CLI/API/web/evaluation adapters.
5. **Operational Budget Receipt ABI 1** — cold/warm startup, latency, RSS,
   output size, cancellation, concurrency, and cleanup.

No “latest model” pointer or directory selection participates in authority.

## 6. Neural proposer design

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
beam, step, state, memory, and time limits.

## 7. Neural realizer design

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

Failure yields a typed no-surface result, never a semantically invented fallback.

## 8. Training, selection, and calibration

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
- selected weights become immutable before calibration.

### Calibration

- calibration capability only;
- receives selected immutable model identities;
- uses actual model scores, not fixed epistemic labels;
- records nonempty bins and non-vacuous denominators;
- cannot alter checkpoint weights or selection;
- threshold policy is content-addressed.

## 9. Reproduction and weight-use proof

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

## 10. Runtime activation

The release runtime starts only from one exact `R5ActivationBundle`.

Startup verifies all artifact, source, authority, ABI, lock, calibration, and
selection identities before tensor use. Missing, mismatched, unsafe, dirty, or
ambiguous artifacts fail startup.

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

## 11. R6 composition root

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

## 12. Security and reliability

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

## 13. Validation and admission

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
api-adapter
web-adapter
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

## 14. Stop conditions

Stop and retain red status when any of these holds:

- R4 is not current green;
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
- any admission evidence is dirty, missing, ambiguous, or stale.

## 15. Definition of done

R5 is complete only after all 25 deferred `R5-Neural-Activation` assertions have
exact executable successors, the activation bundle and fresh canaries pass, R5
admission is current-source green, and R6 remains red.

R6 is complete only after every supported adapter executes through the same
composition root with exact parity, operational gates pass, R6 admission is
current-source green, and frozen-test evaluation remains unopened for R7.
