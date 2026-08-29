# R4.1 Data and Supervision Corrective Replay Design

**Date:** 2026-08-29

**Status:** approved design; implementation and activation pending
**Scope:** `hybrid_mvp/` R4.1 reviewed data, supervision, purpose classes,
artifacts, access and fresh admission only

## 1. Decision

R4 remains red until a new repository-owned admission proves the data and
supervision contract in the approved R4.1 amendment. The repair is a hard cut
from the predecessor global semantic-union partition, solver-authored minima,
bootstrap-selected proposal labels and input-as-output realization labels.

The replacement preserves the useful trust envelope around canonical decoding,
bounded reads, artifact reconstruction, purpose isolation and append-only
admission. It replaces the semantic owners beneath that envelope.

The central data product is a compact reviewed `R4SupervisedCase`, not a full
runtime-observation episode. Authentic runtime episodes remain diagnostic
comparison evidence and never become proposal or realization gold.

R4.1 ends with fresh R4 admission. It does not train, select, calibrate,
evaluate, publish or activate an R5 model. Root adoption remains a separate
reviewed act.

## 2. Evidence and earliest divergence

The checked predecessor corpus contains 400 authentic episodes. Its partition
graph contains 1,635 hard hyperedges, 84 connected components and one 248-case
component. The component exists because semantic-expression, predicate,
grounded-target, topology and response identities are treated as transitive
duplicate-risk edges. That prevents held-out purpose classes from containing
meaningful semantic denominators.

The predecessor feasibility owner then:

1. selects dimensions from observed corpus support;
2. assigns minimum one to each selected dimension and purpose;
3. removes the least-supported dimension until the completion solver succeeds;
4. publishes the surviving set as reviewed configuration.

This reverses authority: observed support and solver success author the
requirements that are supposed to judge them.

The supervision boundary is also ineligible:

- `artifacts/r4/expected_derivations.jsonl` is empty;
- proposal training reads verifier-selected runtime/bootstrap programs;
- gap cases have no independent abstention target;
- realizer training hashes the user input utterance as its target;
- mutation labels are code-authored and some execution fixtures echo expected
  values; and
- the four class payloads are full observed-cycle episodes, exposing proposal
  lineage to the training consumer.

Changing epochs, thresholds or model capacity cannot repair these upstream
ownership defects.

## 3. Goals

1. Make reviewed semantic expression, proposal derivation, abstention,
   realization and mutation truth independent of bootstrap/runtime output.
2. Limit hard grouping to explicitly reviewed duplicate-risk lineage.
3. Make purpose membership and class-local semantic minima readable reviewed
   authority.
4. Materialize compact, disjoint, exhaustive purpose payloads that contain no
   observed candidate programs.
5. Preserve strict class-scoped access, capability authentication and
   repository-owned admission.
6. Remove the combinatorial completion solver from the admission path.
7. Keep the validation graph coalesced: no new pytest tier, no repeated corpus
   build per owner and no normal-runtime corpus scan.
8. Produce a fresh content-addressed R4 artifact graph and append-only green
   transition only after independent reconstruction succeeds.

## 4. Non-goals

- No R5 training, checkpoint generation, model selection, calibration, frozen
  evaluation or runtime activation.
- No promotion of existing bootstrap proposal or realization data.
- No reuse of input surfaces as response targets.
- No compatibility decoder that makes predecessor ABI 3 or 4 evidence eligible
  for current R4 admission.
- No automatic weakening, trimming or selection of reviewed minima.
- No semantic identity, operator, role, participant, topology or response
  action becomes a duplicate-risk key without a reviewed challenge-holdout
  contract.
- No new semantic operator, phrase intent or parallel meaning representation.
- No root runtime or root acceptance change.

## 5. Reviewed source package

The package extends the existing reviewed scenario source with five new source
owners under `data/review/r4_1/`.

### 5.1 Review manifest

`REVIEW_MANIFEST.json` is the content-addressed root of reviewed R4.1 source. It
binds:

- review policy and reviewer refs;
- the reviewed base revision, authority generation and content-addressed source
  bundle ref;
- the existing scenario source hash;
- hashes and record counts for every R4.1 reviewed source;
- the closed ABI versions;
- approval state and explicit supersession ancestry; and
- a declaration that runtime observations and bootstrap outputs are not source
  authority.

The manifest does not attempt to contain the Git identity of the commit that
contains itself. Repository review of the manifest and its exact source bytes
is the human approval act; the later Build Receipt binds the exact committed
generator source revision. The implementation does not invent an external-
signature system.

### 5.2 Proposal supervision

`proposal_supervision.jsonl` owns one proposal target for every eligible case:

- `derive`, with one or more reviewed derivation blueprints; or
- `abstain`, with a typed unresolved/gap target, criticality, earliest owner and
  permitted safe disposition.

A derivation blueprint is separate from canonical meaning. It uses only Program
ABI 2 actions and source-local symbolic selectors that resolve against the
case's immutable ProposalContext. It may reference contribution kind, semantic
kind, reviewed frame/role, exact source geometry and case-local graph handles.
It may not select by raw phrase, regex, internal-ref spelling or observed
candidate identity.

The independent derivation compiler resolves a blueprint, constructs a complete
`SemanticSwitchProgram`, invokes the exact expression compiler and requires its
canonical expression to equal the reviewed expected expression. At least one
derivation is required for every semantic case. Gap cases require an explicit
abstention record and cannot disappear from proposal training.

Permissive predecessor relations that accept expression intersection or a
subset as `ANY` cannot authorize supervision. Every supervised target names the
exact permitted canonical expression set and exact relation between its roots.

Reviewed symbolic blueprints may be shared across cases only when semantic
roles and form evidence license the same construction. Anti-bloat tests reject
one blueprint per surface variant, open-class phrase matching and unbounded
template growth.

### 5.3 Realization supervision

`realization_supervision.jsonl` owns reviewed ResponseMeaning-to-surface rows.
Each row contains:

- a derivation-independent ResponseMeaning semantic signature;
- the authorized response surface and language;
- exact semantic slots and required situated qualifiers;
- output speaker/addressee perspective;
- reference-form choices;
- typed literal-copy sources and exact character-span alignment; and
- review provenance.

The signature preserves expression, bindings, action, polarity, modality,
epistemic status, perspective and required literal values while excluding
cycle-specific lineage refs that do not change meaning.

An independent annotation compiler reconstructs the response signature from
the reviewed slot/alignment record and requires exact equality. Marker,
keyword, substring, template-family and internal-ref checks are forbidden.
The input utterance is not an output target or implicit copy source.

Reusable response plans are permitted only through typed slots. Every concrete
eligible case receives a validated realization instance, including its literal
alignment. This prevents one canned surface from standing in for semantically
different responses.

### 5.4 Mutation contracts

`mutation_contracts.jsonl` moves expected mutation truth out of Python tables.
It declares reviewed mutation family, source case, changed dimension, expected
earliest owner, disposition, effect/no-effect contract and provenance.

The mutation generator instantiates these reviewed contracts. The execution
owner receives the mutated evidence and reviewed environment, but not an
expected label it can simply return. An execution adapter derives behavior from
its operation and environment contract. A test owner that echoes expected
values is rejected as non-independent.

### 5.5 Purpose contract

`purpose_contract.json` owns:

- the four purposes: `train`, `selection`, `calibration`, `frozen_test`;
- explicit reviewed duplicate-risk groups and reasons;
- exact group-to-purpose membership;
- optional separately reviewed challenge-holdout identities;
- a finite semantic denominator registry; and
- fixed positive per-purpose minima.

Membership is reviewer-authored at the duplicate-group level. The compiler
expands it to exact case membership and rejects missing, extra, duplicated or
cross-purpose group members. A solver may produce a draft diagnostic for human
review, but no solver result is authority and no solver participates in
admission.

The predecessor 60/15/15/10 ratio may be reported as a diagnostic distribution.
It is not a requirement that can override reviewed purpose membership or
semantic sufficiency.

## 6. Duplicate-risk grouping

Hard groups are limited to explicit reviewed leakage risks such as:

- source-case lineage;
- paraphrase or normalization family;
- controlled surface mutation lineage;
- shared environment provenance when it would reveal the target; and
- reviewed multi-turn trajectory descendants.

Scenario, trajectory, normalized surface and environment identifiers are not
automatically hard keys. The purpose contract must declare the exact namespace,
group identity, members, reason and review provenance.

The following are coverage dimensions by default:

- five operators and named roles;
- four modes;
- common participants;
- semantic target/category;
- single-root, multi-root, nested, linked, scoped and variable topology;
- abstention/gap kind;
- transition/effect class; and
- response action and realization action.

An exact semantic identity becomes a hard holdout key only through a separate
challenge-holdout row in the purpose contract. Challenge holdouts never arise
from ref spelling or observed frequency.

Grouping uses bounded indexed lineage membership and union/find only over the
reviewed duplicate-risk groups. It does not build semantic-identity hyperedges.
Reviewed groups that share a member form one transitive duplicate-risk
component. Every group and case in that component must declare the same purpose;
otherwise the purpose contract is invalid.

## 7. Semantic denominators and sufficiency

The denominator registry uses stable readable identities, not hashes of current
member lists. Initial families cover:

- semantic expression cases;
- each of the five operators;
- each of the four modes;
- required roles and state dimension/value compatibility;
- nested, scoped, linked, multi-root and query-variable topology;
- typed abstention and critical residuals;
- transition/effect and no-effect behavior;
- ResponseMeaning realization;
- perspective/reference realization; and
- literal-copy realization.

Every minimum is reviewer-authored before allocation validation. The class-local
sufficiency evaluator reports source support and observed support separately for
each purpose and denominator. A missing denominator, unsupported minimum or
underfilled class fails with a typed reason. Aggregate corpus coverage cannot
substitute for a class-local failure.

The diagnostic coverage reporter may show that a reviewed contract is
infeasible. It may not remove a denominator, lower a count, change membership or
publish a replacement contract.

## 8. Compact supervised payload

The generated `R4SupervisedCase` contains only data required by a later
purpose-scoped consumer:

```text
case/surface/language and reviewed environment
inline expected cycle contract and complete canonical expression gold
reviewed derivation programs or typed abstention target
reviewed response supervision instances
duplicate-risk group and purpose refs
review/source provenance
```

It excludes:

- observed proposal candidates and selected program;
- verification scores or model identity;
- observed ResponseMeaning as a target;
- bootstrap lineage as gold;
- sibling-purpose paths, hashes, counts or refs; and
- full runtime phase receipts unrelated to supervision.

Authentic episodes, comparison receipts and mutation observations remain in the
global R4 diagnostic artifact graph. They are not copied into purpose payloads.

The source universe contains every exact expanded case. Every source case is
classified exactly once as semantic supervision, typed abstention or reviewed
diagnostic-only evidence. Semantic and abstention cases form the supervised
universe: each is assigned to exactly one purpose and appears in exactly one
purpose payload. Diagnostic-only cases require a reviewed reason, remain only
in the diagnostic artifact graph, receive no purpose assignment and do not
count toward minima. The four purpose payloads are disjoint and exhaustive over
the supervised universe, while the supervised and diagnostic-only universes are
disjoint and exhaustive over the complete source universe.

## 9. ABI hard cut

The target allocation is:

| Contract | Target ABI | Notes |
|---|---:|---|
| R4 Review Manifest | 1 | Root of reviewed source package |
| Proposal Supervision | 1 | Reviewed derivation or typed abstention |
| Realization Supervision | 1 | ResponseMeaning signature and aligned surface |
| Mutation Contract | 1 | Independent mutation truth |
| Purpose Contract | 1 | Duplicate groups, membership and fixed minima |
| R4 Supervised Case | 1 | Compact joined consumer row |
| Duplicate-Risk Evidence | 1 | Derived reviewed-lineage reconstruction |
| Class-local Sufficiency | 1 | Per-purpose semantic denominators |
| R4 Split Manifest | 2 | Supervised-case payloads |
| R4 Class Capability | 2 | One supervised purpose payload |
| R4 Class Authorization | 2 | Candidate-time expected capability projection |
| R4 Build Receipt | 5 | Complete R4.1 artifact-graph root |

Partition Evidence ABI 3, Partition Config ABI 1, Split Manifest ABI 1,
Partition Sufficiency ABI 1 and Build Receipt ABI 4 are predecessor evidence and
cannot decode as current candidates. Historical ABI 3/4 reconstruction remains
source-pinned and incapable of authorizing R5.

## 10. Build and artifact graph

The deterministic builder performs one ordered pass:

1. authenticate the complete review manifest and source bytes;
2. compile scenarios into expected cycle contracts independently of runtime;
3. expand exact cases and ProposalContexts;
4. compile reviewed derivations and abstentions;
5. compile reviewed realization annotations;
6. execute authentic runtime comparisons and independent mutation observations;
7. reconstruct reviewed duplicate-risk groups and explicit purpose membership;
8. join compact supervised cases;
9. compute class-local sufficiency;
10. serialize four sorted purpose payloads;
11. mint train capability and candidate authorization projections; and
12. emit Build Receipt ABI 5.

Expected generated inventory:

```text
artifacts/r4/expected_contracts.jsonl
artifacts/r4/compiled_proposal_supervision.jsonl
artifacts/r4/compiled_realization_supervision.jsonl
artifacts/r4/expanded_cases.jsonl
artifacts/r4/episodes.jsonl
artifacts/r4/mutations.jsonl
artifacts/r4/mutation_observations.jsonl
artifacts/r4/structural_sufficiency.json
artifacts/r4/duplicate_risk_evidence.json
artifacts/r4/class_sufficiency.json
artifacts/r4/split_manifest.json
artifacts/r4/splits/{train,selection,calibration,frozen_test}.jsonl
artifacts/r4/capabilities/train.json
artifacts/r4/authorizations/train.json
artifacts/r4/BUILD_RECEIPT.json
```

Selection, calibration and frozen-test payloads are materialized and available
only to integrity verification. Their consumer capabilities are not minted by
R4.1.

## 11. Admission and access

Admission independently reconstructs:

- every reviewed source hash and record identity;
- expression, derivation, abstention, realization and mutation compilation;
- exact case classification;
- duplicate-risk groups and no-cross-purpose membership;
- compact supervised-case joins;
- class-local denominators and fixed minima;
- payload bytes, ordering, counts and hashes;
- split manifest, train capability and authorization; and
- Build Receipt ABI 5.

Admission never retrains a model or uses bootstrap proposals to reproduce gold.
The existing R4 admission tier remains governance, one active pytest process,
artifact integrity and SQLite activation.

Authorization is deliberately non-circular. The builder emits a candidate-time
projection containing the expected capability ref/SHA, artifact-graph ref,
generator source revision and authority generation. It contains no admission
run or ledger ref. The later repository admission receipt authenticates that
projection's exact ref/SHA and source ancestry. R5 resolves those expected bytes
from the admitted run; the candidate projection never changes after admission.

The train loader changes atomically to Capability/Authorization ABI 2 and
returns an immutable `AuthenticatedR4SupervisionBatch`. It validates read-once
bytes and reveals no sibling purpose identity. Existing R5 trainers remain
explicitly unavailable until the R5 plan replaces their target extraction with
the reviewed supervision fields.

## 12. Performance and anti-bloat contract

R4.1 adds no validation tier and no normal-runtime work.

- Reviewed source decoding and joining are linear in bounded record count.
- Duplicate-risk union/find is near-linear in reviewed group membership.
- No completion solver runs during build or admission.
- Semantic denominator membership is computed once per build and reused.
- Authentic runtime episode generation runs once per candidate build, not once
  per owner.
- Byte-identical generation runs twice only at publication checkpoints.
- Admission reconstructs serialized identities and does not replay R5 training.
- Purpose payloads contain compact supervision instead of full observed cycles.
- Bounds cover cases, groups, group members, denominators, derivations per case,
  actions, graph depth, realization variants, slots, alignments and artifact
  bytes.

Anti-bloat tests reject:

- one derivation blueprint per inflection or surface phrase;
- raw-surface or internal-ref selectors;
- semantic identities used as implicit duplicate keys;
- every observed target/category promoted to a required minimum;
- unbounded realization variants or alignments;
- full observed cycles in purpose payloads;
- repeated corpus construction across owner gates; and
- any normal runtime import of R4 data, build or admission code.

## 13. Validation and corruption matrix

Required direct tests include:

- missing, duplicate, unhashed or unreviewed source files;
- empty derivation supervision;
- a semantic case without a compiling derivation;
- a gap case without an explicit abstention target;
- bootstrap-selected program substituted for reviewed derivation;
- input surface substituted for response target;
- realization with wrong expression, slot, polarity, modality, epistemic status,
  perspective or literal alignment;
- marker-only semantic-equivalence impostors;
- mutation owner echoing expected labels;
- semantic target/operator/mode/participant/response identity becoming an
  undeclared hard group;
- duplicate-risk group crossing purposes;
- missing, extra, overlapping or unclassified cases;
- aggregate coverage masking a class-local minimum failure;
- unsupported minimum being trimmed or weakened;
- supervised payload containing observed candidates or sibling identities;
- payload/hash/count/capability/authorization tampering;
- ABI 3/4 candidate accepted as current R4.1;
- two generation runs differing; and
- R5 training becoming available before fresh R4.1 admission.

Multilingual and unseen-synonym cases must prove that reviewed semantic roles and
designation/affordance evidence, not English phrase templates, own derivation
reuse.

## 14. Execution and review sequence

Implementation is staged in one isolated branch with review checkpoints:

1. governing design and exact ABI allocation;
2. strict source schemas, decoders and failing owner tests;
3. review manifest and reviewed source package;
4. independent proposal, realization and mutation compilers;
5. explicit purpose membership and class-local sufficiency;
6. compact payload builder and ABI 5 artifact graph;
7. admission reconstruction and ABI 2 train access;
8. deterministic double generation and focused/full validation;
9. independent code/data review;
10. artifact-only publication commit from the exact source parent;
11. clean repository-owned R4 admission; and
12. append-only R4 green transition plus final governance reconstruction.

The reviewed source package receives a separate human approval checkpoint before
artifact publication. Generated draft supervision is never promoted merely
because it compiles.

## 15. Acceptance

R4.1 is complete only when:

- all reviewed source bytes authenticate through one manifest;
- every eligible semantic case has independent compiling derivation gold;
- every gap case has explicit typed abstention gold;
- every realizer-eligible case has reviewed ResponseMeaning-to-surface
  supervision with exact perspective and literal alignment;
- mutation expectations are independent of execution output;
- hard grouping contains only reviewed duplicate-risk lineage;
- supervised membership is explicit, disjoint, exhaustive over the supervised
  universe and group-safe, while every diagnostic-only case is separately
  classified and excluded;
- every purpose satisfies its own fixed semantic minima;
- compact purpose payloads contain no observed proposal or input-as-output gold;
- generation is byte-identical;
- Build Receipt ABI 5 and all artifacts independently reconstruct;
- the existing bounded admission graph passes from a clean committed source;
- the ledger records fresh R4 green while R5-R8 remain red;
- no root files or root adoption status change; and
- no R5 model training or activation occurred during the tranche.

## 16. R5 handoff

After fresh R4.1 admission, R5 may consume only the authenticated train
supervision batch. R5 must replace proposal target extraction, realization
encoding, calibration, evaluation and runtime selection under its own approved
plan. The R4.1 receipt is necessary evidence, not evidence that any neural model
is accurate, selected or active.
