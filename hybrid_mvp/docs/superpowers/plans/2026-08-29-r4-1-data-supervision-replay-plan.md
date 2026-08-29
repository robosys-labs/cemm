# R4.1 Data and Supervision Corrective Replay Implementation Plan

> **For agentic workers:** Use `subagent-driven-development` in the current
> session or `executing-plans` in a separate session. Execute one task at a
> time, keep the progress tracker current, and stop at every review checkpoint.

**Goal:** Replace the ineligible R4 partition and supervision owners with one
reviewed, content-addressed R4.1 source package; independently compile exact
proposal, abstention, realization and mutation truth; emit compact purpose-
scoped payloads; and obtain a fresh repository-owned R4 admission while R5-R8
remain red.

**Architecture:** Preserve the existing canonical decoding, bounded artifact
I/O, deterministic generation, purpose-scoped access and append-only governance
envelope. Add strict source owners in `data/review/r4_1/`, compile them into a
compact `R4SupervisedCase`, partition only by reviewed duplicate-risk lineage,
prove fixed class-local semantic minima, and authenticate the resulting ABI 5
artifact graph. Authentic runtime episodes remain diagnostic evidence and never
author proposal or realization targets.

**Tech stack:** Python 3, dataclasses, strict canonical JSON/JSONL, JSON Schema
Draft 2020-12, SHA-256 content references, pytest, SQLite admission evidence,
PowerShell and Git worktrees.

**Approved design:**
`docs/superpowers/specs/2026-08-29-r4-1-data-supervision-replay-design.md`

---

## 1. Release invariants

- Work remains under `hybrid_mvp/`; root adoption is out of scope.
- G0-R3 remain green. R4 remains red until the final clean admission. R5-R8
  remain red throughout this plan.
- `SemanticExpression`, not `SemanticSwitchProgram`, is canonical meaning.
- Reviewed source authors gold. Runtime observations, bootstrap proposals,
  verifier selections and model outputs are diagnostic descendants only.
- Every source case is classified exactly once as semantic supervision, typed
  abstention, or reviewed diagnostic-only evidence.
- Semantic and abstention cases are assigned to exactly one purpose. The four
  purpose payloads are disjoint and exhaustive over that supervised universe.
- Only explicit reviewed duplicate-risk lineage forms hard groups. Operators,
  roles, modes, participants, semantic targets, topology and response actions
  remain coverage dimensions unless separately reviewed as challenge holdouts.
- Class-local minima are reviewer-authored and immutable during build and
  admission. Infeasibility fails; no solver selects, drops or weakens minima.
- Purpose payloads exclude observed candidates, selected programs, verifier
  scores, model identities, sibling-purpose identities and full cycle receipts.
- Candidate authorization contains no admission identity. The later repository
  admission receipt authenticates its exact bytes.
- Selection, calibration and frozen-test capabilities are not minted.
- No R5 training, model artifact, selection, calibration, evaluation,
  publication or activation occurs in this plan.
- Predecessor ABI 3/4 evidence remains reconstructible only under its exact
  historical source policy and can never authorize current R4 or R5.

## 2. Performance and gate budget

This replay corrects owners without multiplying validation cost.

- Add no validation tier and no normal-runtime import or scan.
- Keep one active pytest process per existing owner tier; add new nodes to the
  appropriate R4 owner selectors instead of adding a new pytest step.
- Decode each reviewed source file once per build/admission snapshot.
- Join cases with indexed maps; no nested whole-corpus joins.
- Reconstruct duplicate-risk components with bounded union/find over reviewed
  memberships only.
- Compute denominator membership once and reuse it for all four class receipts.
- Run authentic runtime episode generation once per candidate build.
- Do not run the completion solver in build or admission.
- Run byte-identical double generation only at the publication checkpoint.
- Run the full active suite only through the existing admission owner; use
  focused owner tests during implementation.
- Enforce explicit maxima for source files, bytes, records, groups, group
  memberships, denominators, derivations per case, program actions, graph
  depth, realization variants, slots and alignments.
- Add a deterministic performance receipt or test counters for source reads,
  joins, group memberships and episode builds; wall-clock assertions are
  diagnostic only and must not become flaky release gates.

## 3. Command convention

Run Python and pytest commands from `hybrid_mvp/`. Run Git commands from the
worktree root. Use a unique `--basetemp` for each pytest process. Every task
must run its focused RED test before implementation and its focused GREEN test
after implementation. Do not hide unexpected failures by changing selectors.

Before each task:

```powershell
git status --short
python scripts/check_test_inventory.py --phase R4 --source-only
```

At each checkpoint:

```powershell
git diff --check
python -m compileall -q src scripts tests
```

Every task that creates or changes an executable test node must, in the same
commit, refresh its literal metadata with the repository-owned refresher, add
the node to the appropriate existing selector, reconstruct inventory evidence,
and update R5 dispositions when R5 lineage changes. Run G0 and R4 source-only
inventory checks for every such task, plus R5 source-only checks for R5 test
changes. No intermediate commit may contain an ungoverned test node.

## 4. Dependency order

```text
governance hard cut
  -> strict source ABIs
  -> reviewed source checkpoint
  -> independent supervision compilers
  -> reviewed purpose/duplicate-risk/sufficiency owners
  -> compact supervised-case join
  -> ABI 5 artifact graph
  -> independent admission + ABI 2 train access
  -> predecessor retirement and selector migration
  -> double generation + data/code review
  -> artifact-only publication
  -> clean repository admission
  -> append-only R4 green transition
```

No downstream task may compensate for a failed upstream owner.

## 5. File ownership map

### New reviewed source

- `data/review/r4_1/REVIEW_MANIFEST.json`
- `data/review/r4_1/proposal_supervision.jsonl`
- `data/review/r4_1/realization_supervision.jsonl`
- `data/review/r4_1/mutation_contracts.jsonl`
- `data/review/r4_1/purpose_contract.json`

### New or successor source owners

- `src/cemm_authoritative_hybrid/r4_supervision.py`
- `src/cemm_authoritative_hybrid/r4_purpose.py`
- `src/cemm_authoritative_hybrid/r4_partition_contracts.py`
- `src/cemm_authoritative_hybrid/r4_partition_access.py`
- `src/cemm_authoritative_hybrid/r4_pipeline.py`
- `src/cemm_authoritative_hybrid/r4_admission.py`
- `src/cemm_authoritative_hybrid/r4_environment.py`
- `src/cemm_authoritative_hybrid/r4_mutations.py`

### New or successor schemas

- `schemas/r4_review_manifest.schema.json`
- `schemas/r4_proposal_supervision.schema.json`
- `schemas/r4_realization_supervision.schema.json`
- `schemas/r4_mutation_contract.schema.json`
- `schemas/r4_purpose_contract.schema.json`
- `schemas/r4_supervised_case.schema.json`
- `schemas/r4_duplicate_risk_evidence.schema.json`
- `schemas/r4_class_local_sufficiency.schema.json`
- `schemas/r4_split_manifest.schema.json` (ABI 2)
- `schemas/r4_class_capability.schema.json` (ABI 2)
- `schemas/r4_class_authorization.schema.json` (ABI 2)
- `schemas/r4_build_receipt.schema.json` (ABI 5)

### Builder, admission and governance

- `scripts/build_r4_artifacts.py`
- `scripts/publish_r4_candidate.py` (new transactional publisher)
- `scripts/validation_gate.py`
- `scripts/update_replay_status.py`
- `scripts/check_r3_r4_structure.py`
- `configs/validation_gates.json`
- `governance/replay_status.jsonl`
- `docs/ABI_REGISTRY.md`
- `docs/DOCUMENT_AUTHORITY.json`
- `docs/ARCHITECTURE.md`
- `docs/superpowers/progress/2026-08-29-r4-1-data-supervision-replay-progress.md`

### Focused test owners

- `tests/test_r4_supervision_contracts.py`
- `tests/test_r4_supervision_compilers.py`
- `tests/test_r4_purpose_contracts.py`
- `tests/test_r4_supervised_cases.py`
- `tests/test_r4_partition_contracts.py`
- `tests/test_r4_admission.py`
- `tests/test_r4_training_partition_boundary.py`
- `tests/test_r5_data_isolation.py`
- `tests/test_r4_validation_gate.py`
- `tests/test_replay_governance.py`
- `tests/test_r4_structure.py`

---

## Task 1: Govern the executable replay and create the progress owner

**Files:**

- Add: `docs/superpowers/progress/2026-08-29-r4-1-data-supervision-replay-progress.md`
- Modify: `docs/DOCUMENT_AUTHORITY.json`
- Modify: `tests/test_replay_governance.py`
- Modify: `configs/validation_gates.json`
- Read: approved design and this plan

- [ ] Write failing governance tests proving the plan is governing, the
  progress file is operational evidence only, R4 is red, and R5-R8 are red.
- [ ] Add the plan to `governing_documents` immediately after its design and
  classify the progress file as historical/operational evidence without making
  it a status owner.
- [ ] Seed the tracker with task states, commit refs, test receipts, review
  checkpoints, artifact refs and unresolved decisions. Do not copy a mutable
  phase matrix into it.
- [ ] Add the exact test nodes to the existing governance/R4 selectors and
  refresh literal test metadata with the repository-owned refresher.
- [ ] Run the governance owner tests in one pytest process.
- [ ] Commit: `docs(r4): govern data supervision replay plan`.

**Checkpoint:** The source implementation still has no new decoder. R4 remains
red, and the authority graph names exactly one current plan.

## Task 2: Add strict reviewed-source schemas and immutable decoders

**Files:**

- Add the five new source schemas listed in the file map.
- Add: `src/cemm_authoritative_hybrid/r4_supervision.py`
- Add: `src/cemm_authoritative_hybrid/r4_purpose.py`
- Add: `tests/test_r4_supervision_contracts.py`
- Add: `tests/test_r4_purpose_contracts.py`
- Modify: package exports only if import ownership requires it

- [ ] Write RED tests for unknown/missing fields, noncanonical JSON, duplicate
  refs, invalid content refs, unsupported ABIs, unsafe selectors, unbounded
  lists, invalid spans, nonfinite numbers and schema/decoder disagreement.
- [ ] Define frozen value objects for review manifest, proposal target,
  derivation blueprint, typed abstention, realization row, literal alignment,
  mutation contract, purpose membership, duplicate-risk group, challenge
  holdout and denominator minimum.
- [ ] Centralize common bounded/canonical helpers; do not duplicate canonical
  parsers in each decoder.
- [ ] Require exact ABI values allocated in `docs/ABI_REGISTRY.md`.
- [ ] Make constructors factory-only where existing R4 contracts require it.
- [ ] Validate all source refs, review refs and source-local identities without
  consulting runtime observations.
- [ ] Validate all schemas as Draft 2020-12 and test decoder/schema parity.
- [ ] Run the two contract modules in one pytest process.
- [ ] Commit: `feat(r4): add reviewed supervision source contracts`.

**Checkpoint:** Strict empty contracts exist, but no reviewed source is yet
accepted and no artifact can be built.

## Task 3: Authenticate the review manifest and source bundle

**Files:**

- Modify: `src/cemm_authoritative_hybrid/r4_supervision.py`
- Modify: `tests/test_r4_supervision_contracts.py`
- Add: bounded source-loader tests in the same owner module
- Later add, after review: `data/review/r4_1/*`

- [ ] Write RED tests for missing source, extra source, wrong count, wrong SHA,
  symlink/path escape, short read, growth after stat, duplicate read,
  self-referential commit identity and unapproved manifest state.
- [ ] Implement one bounded read-once `AuthenticatedR4ReviewBundle` that loads
  the exact five source files and the existing scenario source named by the
  manifest.
- [ ] Recompute every source count, SHA and the source-bundle content ref.
- [ ] Bind reviewed base revision and authority generation but never require the
  manifest to hash a commit containing itself.
- [ ] Reject any runtime/bootstrap/observed artifact path in the source bundle.
- [ ] Keep the bundle immutable and pass bytes to all later compilers so no
  owner reopens source files.
- [ ] Run contract and bounded-I/O tests.
- [ ] Commit: `feat(r4): authenticate reviewed source bundle`.

**Checkpoint — human review required:** Draft source rows may be generated as
non-authoritative work aids, but the task stops before checking in
`data/review/r4_1/`. A reviewer must approve exact semantic expressions,
derivations/abstentions, realization rows, mutation truth, duplicate-risk
groups, purpose membership and minima. Compiler success is not review.

## Task 4: Check in the independently reviewed source package

**Files:**

- Add: all five `data/review/r4_1/` source files
- Modify: review manifest after the four child sources are final
- Add: data-canary assertions to existing contract tests

- [ ] Record reviewer refs, reviewed base, authority generation, supersession
  ancestry and explicit exclusion of bootstrap/runtime authority.
- [ ] Classify every exact expanded source case once. No implicit default to
  semantic, abstention or diagnostic-only is permitted.
- [ ] Require one or more reviewed derivation blueprints for every semantic
  case and one typed abstention target for every gap case.
- [ ] Require realization rows for every declared realizer-eligible case.
- [ ] Declare mutation truth independently of the executor.
- [ ] Declare duplicate-risk groups, group purposes, optional challenge
  holdouts, finite denominator registry and fixed positive minima.
- [ ] Recompute child counts/hashes and source-bundle ref, then write the
  manifest last.
- [ ] Run strict source decoding and data-canary tests.
- [ ] Obtain a second data review confirming no observed program, input-as-
  output target, solver-authored minimum or implicit hard group entered source.
- [ ] Commit: `data(r4): add reviewed supervision package`.

**Checkpoint:** The exact source package is immutable for the candidate build.
Any semantic correction restarts review and changes its bundle ref.

## Task 5: Compile proposal derivations and typed abstentions independently

**Files:**

- Modify: `src/cemm_authoritative_hybrid/r4_supervision.py`
- Reuse: `src/cemm_authoritative_hybrid/r4_contracts.py`
- Add: `tests/test_r4_supervision_compilers.py`
- Modify: `tests/test_r4_assertion_compiler.py` only for exact successor seams

- [ ] Write RED tests that substitute bootstrap-selected programs, observed
  candidate refs, raw phrase/regex/internal-ref selectors, missing derivations,
  missing abstentions, expression subset/intersection and wrong root relation.
- [ ] Implement `ReviewedDerivationCompiler` over source-local symbolic
  selectors and immutable ProposalContext only.
- [ ] Enforce Program ABI 2, action count and graph depth bounds.
- [ ] Compile every blueprint through the exact expression compiler and require
  canonical equality with the complete reviewed expression set.
- [ ] Preserve multiple valid derivations without making a program canonical
  meaning.
- [ ] Compile typed abstention rows into explicit proposal targets; never drop
  them from the supervised universe.
- [ ] Add multilingual and unseen-synonym tests showing role/affordance reuse
  without form-pack or phrase-template growth.
- [ ] Run compiler owner tests and relevant assertion-compiler tests.
- [ ] Commit: `feat(r4): compile independent proposal supervision`.

## Task 6: Compile ResponseMeaning-to-surface supervision independently

**Files:**

- Modify: `src/cemm_authoritative_hybrid/r4_supervision.py`
- Reuse: `src/cemm_authoritative_hybrid/r3_response.py`
- Modify: `tests/test_r4_supervision_compilers.py`
- Add realization-specific corruption fixtures under test-local temporary roots

- [ ] Write RED tests for input utterance as target, wrong expression/action,
  lost slot, polarity/modality/epistemic drift, wrong perspective/reference,
  invalid literal span, marker-only equivalence and unbounded variants.
- [ ] Implement `ReviewedRealizationCompiler` that reconstructs the exact
  derivation-independent ResponseMeaning semantic signature from typed slots
  and alignments.
- [ ] Require exact equality; do not use marker, substring, keyword or template
  family acceptance.
- [ ] Require every copied literal to name a permitted typed source and exact
  character geometry.
- [ ] Ensure input surfaces can change without changing reviewed response gold
  unless an explicit literal-copy source requires it.
- [ ] Serialize deterministic compiled realization rows.
- [ ] Run supervision compiler tests.
- [ ] Commit: `feat(r4): compile reviewed realization supervision`.

## Task 7: Make mutation truth independent of mutation execution

**Files:**

- Modify: `src/cemm_authoritative_hybrid/r4_mutations.py`
- Modify: `src/cemm_authoritative_hybrid/r4_environment.py`
- Modify: `src/cemm_authoritative_hybrid/r4_supervision.py`
- Modify: `tests/test_r4_mutations_and_partitions.py`
- Modify: `tests/test_r4_environment.py`

- [ ] Write RED tests proving Python `_SPECS` cannot author expected truth and
  an execution adapter that echoes expected labels is rejected.
- [ ] Make the generator instantiate only reviewed Mutation Contract ABI 1
  rows; retire code-authored expected labels from the current path.
- [ ] Pass mutated evidence and reviewed environment to the execution owner,
  never the expected disposition/effect labels.
- [ ] Compare independently observed owner/status/effect against reviewed truth
  after execution.
- [ ] Preserve existing bounded mutation requests and observation wire types
  where their semantics remain valid.
- [ ] Add negative, denial, ambiguity, unresolved, transition and no-effect
  canaries.
- [ ] Run mutation and environment owner tests.
- [ ] Commit: `feat(r4): separate mutation truth from execution`.

## Task 8: Replace global semantic union with reviewed purpose ownership

**Files:**

- Modify: `src/cemm_authoritative_hybrid/r4_purpose.py`
- Modify: `src/cemm_authoritative_hybrid/r4_partitions.py`
- Modify: `src/cemm_authoritative_hybrid/r4_partition_verify.py`
- Modify: `tests/test_r4_purpose_contracts.py`
- Replace assertions in: `tests/test_r4_partition_global_assignment.py`
- Retire current authority from: `src/cemm_authoritative_hybrid/r4_partition_config.py`

- [ ] Write RED tests proving semantic target, operator, role, mode,
  participant, topology and response identity do not create hard edges.
- [ ] Write RED tests for overlapping reviewed groups with different purposes,
  undeclared members, missing/extra cases, implicit scenario/environment keys,
  challenge holdout drift and solver-authored membership.
- [ ] Implement bounded union/find solely over explicit reviewed duplicate-risk
  memberships. Overlapping groups form one transitive component and must share
  a purpose.
- [ ] Expand reviewed group-to-purpose assignments into exact supervised-case
  membership; diagnostic-only cases receive no purpose.
- [ ] Keep allocation/ratio/solver output diagnostic only. Remove the completion
  solver from all build and admission call paths.
- [ ] Emit Duplicate-Risk Evidence ABI 1 with deterministic groups, components,
  memberships, reasons and review refs.
- [ ] Replace predecessor tests rather than changing expected component counts.
- [ ] Run purpose and partition owner tests.
- [ ] Commit: `feat(r4): partition by reviewed duplicate risk`.

## Task 9: Prove fixed class-local semantic sufficiency

**Files:**

- Modify: `src/cemm_authoritative_hybrid/r4_purpose.py`
- Reuse aggregate diagnostics from: `src/cemm_authoritative_hybrid/r4_sufficiency.py`
- Modify: `tests/test_r4_purpose_contracts.py`
- Modify: `tests/test_r4_sufficiency.py`

- [ ] Write RED tests for absent denominators, unsupported reviewed minima,
  underfilled classes, aggregate coverage masking one class and any attempt to
  trim or rewrite minima.
- [ ] Build a finite stable denominator registry with readable identities.
- [ ] Compute source support and observed class support separately for every
  purpose/denominator pair.
- [ ] Emit typed failures for missing, unsupported and underfilled rows.
- [ ] Emit Class-local Sufficiency ABI 1 only when all fixed minima pass.
- [ ] Retain the predecessor structural evaluator only as corpus-level
  diagnostic evidence; it cannot authorize class-local usability.
- [ ] Add a single-pass counter proving denominator membership is computed once
  per candidate build.
- [ ] Run purpose/sufficiency owner tests.
- [ ] Commit: `feat(r4): prove class local semantic sufficiency`.

## Task 10: Build compact supervised cases and four payloads

**Files:**

- Add: `schemas/r4_supervised_case.schema.json`
- Modify: `src/cemm_authoritative_hybrid/r4_supervision.py`
- Modify: `src/cemm_authoritative_hybrid/r4_pipeline.py`
- Add: `tests/test_r4_supervised_cases.py`
- Modify: `tests/test_r4_authentic_episodes.py`

- [ ] Write RED tests for observed candidates, selected programs, verifier
  scores, observed ResponseMeaning, model refs, sibling refs/hashes/counts,
  full cycle receipts and incomplete expression gold in a purpose row.
- [ ] Implement factory-only R4 Supervised Case ABI 1 with inline canonical
  expression gold, inline expected contract, reviewed proposal target,
  reviewed realization instances, purpose/group refs and source provenance.
- [ ] Join via exact indexed case refs and reject one-to-zero, one-to-many and
  cross-source joins.
- [ ] Prove source-universe classification and supervised-universe partition
  exhaustiveness independently.
- [ ] Serialize one sorted canonical JSONL payload per purpose.
- [ ] Keep episodes and mutation observations in the diagnostic graph only.
- [ ] Add payload size and field-set assertions demonstrating the compact
  replacement does not copy full observed cycles.
- [ ] Run supervised-case and authentic-episode tests.
- [ ] Commit: `feat(r4): build compact supervised purpose payloads`.

## Task 11: Version the R4 artifact graph to ABI 5

**Files:**

- Modify four successor schemas: split manifest, capability, authorization and
  build receipt
- Modify: `src/cemm_authoritative_hybrid/r4_partition_contracts.py`
- Modify: `src/cemm_authoritative_hybrid/r4_pipeline.py`
- Modify: `scripts/build_r4_artifacts.py`
- Modify: `tests/test_r4_partition_contracts.py`
- Modify: `tests/test_r4_authentic_episodes.py`

- [ ] Write RED tests for ABI 1/4 candidate acceptance, missing source-package
  refs, missing compiled-supervision refs, missing class sufficiency,
  authorization with an admission ref and sibling-purpose disclosure.
- [ ] Implement Split Manifest ABI 2 over the four compact payloads.
- [ ] Implement Class Capability ABI 2 and candidate-time Class Authorization
  ABI 2 for train only. Bind expected capability ref/SHA, artifact-graph ref,
  generator source revision and authority generation; include no admission ref.
- [ ] Implement Build Receipt ABI 5 binding the authenticated review bundle,
  compiled proposal/realization supervision, mutation artifacts, diagnostic
  episodes, duplicate-risk evidence, class sufficiency, split manifest,
  capability and authorization.
- [ ] Update `build_r4_artifacts.py` to construct the source snapshot once and
  pass it through the ordered pipeline.
- [ ] Keep historical ABI 3/4 decoders source-pinned and inaccessible to the
  current candidate factory.
- [ ] Run partition-contract and pipeline tests.
- [ ] Commit: `feat(r4): emit supervision build receipt abi5`.

## Task 12: Independently reconstruct admission and train access

**Files:**

- Modify: `src/cemm_authoritative_hybrid/r4_admission.py`
- Modify: `src/cemm_authoritative_hybrid/r4_partition_access.py`
- Modify: `scripts/validation_gate.py`
- Modify: `scripts/update_replay_status.py`
- Modify: `tests/test_r4_admission.py`
- Modify: `tests/test_r4_training_partition_boundary.py`
- Modify: `tests/test_r5_data_isolation.py`
- Modify: `tests/test_r4_validation_gate.py`

- [ ] Write RED corruption tests for every source, compiled artifact, purpose
  receipt, payload, capability, authorization and Build Receipt ABI 5 edge.
- [ ] Independently reconstruct source hashes, compilation, classification,
  duplicate groups, purpose membership, sufficiency, payload bytes and all
  content identities without trusting builder objects.
- [ ] Reject ABI 3/4 candidate submissions before current artifact use.
- [ ] Implement immutable `AuthenticatedR4SupervisionBatch` from read-once
  train payload/capability/authorization bytes.
- [ ] Reveal no selection, calibration or frozen-test path, ref, hash or count.
- [ ] Implement and fixture-test resolution of candidate authorization through
  an exact committed repository admission receipt. Production resolution stays
  unavailable until Task 16 supplies the first clean ABI 5 run; no current-
  worktree or fabricated admission identity is accepted.
- [ ] Keep current R5 trainers unavailable: the loader may expose reviewed
  fields, but training target extraction changes only under the R5 plan.
- [ ] Run admission, boundary, isolation and validation-gate tests in their
  existing owner processes.
- [ ] Commit: `feat(r4): admit and expose authenticated supervision`.

## Task 13: Quarantine ineligible R5 supervision consumers

**Files:**

- Modify: `src/cemm_authoritative_hybrid/training.py`
- Modify: `scripts/run_r4_release_training.py`
- Modify: `scripts/train_proposer.py`
- Modify: `scripts/train_realizer.py`
- Modify: `tests/test_r4_release_training.py`
- Modify: `tests/test_r5_data_isolation.py`

- [ ] Write RED tests showing a fresh R4.1 batch still cannot invoke proposal or
  realizer fitting while R5 is red.
- [ ] Remove `AuthenticEpisode` target extraction from the authenticated release
  path. Bootstrap/verifier-selected program actions and input-surface hashes
  must not remain reachable as release labels.
- [ ] Make both release trainers reject the ABI 2 supervision batch with a typed
  `R5 consumer replacement pending` failure before vocabulary, tensor, model or
  optimizer construction.
- [ ] Keep diagnostic/development helpers explicitly named and incapable of
  producing release artifacts or satisfying activation policy.
- [ ] Prove monkeypatched observed selected programs and input surfaces cannot
  change any authenticated supervision target.
- [ ] Prove the release-training launcher cannot bypass R5 red status or accept
  a raw episodes path.
- [ ] Run release-training and data-isolation owner tests.
- [ ] Commit: `refactor(r5): quarantine predecessor supervision labels`.

**Checkpoint:** R4.1 may authenticate data, but no neural consumer is available.
The later R5 plan must deliberately implement reviewed-derivation and reviewed-
realization encoders.

## Task 14: Retire predecessor current paths and migrate exact test authority

**Files:**

- Remove current use of: `src/cemm_authoritative_hybrid/r4_partition_config.py`
- Remove current use of: feasibility analyzer/publisher scripts and config
- Replace stale assertions in partition, structure and admission tests
- Modify: `configs/validation_gates.json`
- Modify: `scripts/check_r3_r4_structure.py`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/ABI_REGISTRY.md`
- Modify: `tests/test_r4_structure.py`
- Add: `tests/test_r4_1_performance_contract.py`
- Modify: `tests/test_replay_governance.py`
- Add: `scripts/publish_r4_candidate.py`
- Add: transactional publication and rollback tests
- Modify: test inventory metadata/receipts through repository-owned tools

- [ ] Write RED source scans proving no current build/admission call reaches
  `GlobalLeakagePartitioner`, solver-trimmed minima, ABI 4 candidate decoding,
  optional derivation gold, input-as-output realization labels or code-authored
  mutation truth.
- [ ] Delete or quarantine predecessor execution entry points only after all
  valid forensic consumers are identified. Preserve source-pinned historical
  reconstruction.
- [ ] Replace predecessor semantic-union/ratio/feasibility tests with successor
  owner tests. Do not weaken exact assertions to make old and new paths coexist.
- [ ] Add structural performance tests proving build/admission cannot reach the
  completion solver, duplicate grouping work is bounded by reviewed membership,
  denominator extraction and authentic episode generation each occur once per
  candidate build, purpose rows exclude full cycles, and normal runtime imports
  no R4 build/admission/data owner.
- [ ] Assert validation still has the same tier count and at most one pytest
  process in each existing R4 owner step.
- [ ] Implement the transactional ABI 5 publisher and rollback tests here,
  before the generator-source checkpoint. It accepts only a verified temporary
  candidate and may replace only the exact `artifacts/r4/**` inventory.
- [ ] Update validation selector inputs and exact nodes atomically without
  creating another owner tier or pytest process.
- [ ] Refresh literal metadata, test inventory receipt and any required R5
  dispositions with repository scripts; review the diff for unrelated churn.
- [ ] Update active architecture text and prominent supersession banners.
- [ ] Run G0-R4 source-only inventory and all focused R4 owner tests.
- [ ] Commit: `refactor(r4): hard cut predecessor supervision paths`.

**Checkpoint — code review required:** Review semantic ownership, independent
reconstruction, data isolation, historical compatibility and performance. Fix
all critical/important findings before generating checked-in artifacts.

## Task 15: Generate twice, review data, and publish the artifact-only commit

**Files:**

- Regenerate the inventory listed in the approved design under `artifacts/r4/`

- [ ] Start from a clean source commit and record its full revision.
- [ ] Build candidate A into a temporary directory with bounded diagnostics.
- [ ] Build candidate B from the same source revision into another temporary
  directory.
- [ ] Require byte-identical relative path sets and file bytes.
- [ ] Run independent admission against temporary candidate A.
- [ ] Review case counts, semantic/abstention/diagnostic classification,
  purpose distribution, duplicate components, every class-local denominator,
  payload byte sizes and absence of forbidden fields.
- [ ] Obtain final data review of exact source and generated receipt identities.
- [ ] Publish through the transactional publisher with rollback-on-failure.
- [ ] Verify `git diff --name-only` contains only `artifacts/r4/**`; no progress,
  source, test, script, config, reviewed-data or governance path is allowed.
- [ ] Commit: `artifacts(r4): publish supervised abi5 candidate`.

## Task 16: Run clean repository-owned admission

**Files:**

- Add: `artifacts/validation/runs/<run-ref>.json`
- Do not modify source or candidate artifacts during the run

- [ ] Confirm clean worktree, exact source-parent relationship and expected
  artifact-only commit.
- [ ] Run the existing bounded R4 admission graph: governance, one active-suite
  pytest process, artifact integrity and SQLite activation.
- [ ] Require fresh Build Receipt ABI 5 reconstruction and candidate
  authorization ref/SHA authentication.
- [ ] Confirm R5 training, model publication and activation were not invoked.
- [ ] Commit only the repository admission receipt:
  `governance(r4): record supervised abi5 admission`.

**Stop condition:** Any failure returns to the earliest owning source/code task.
Do not patch generated bytes, append green status or relax admission.

## Task 17: Append R4 green and close the replay

**Files:**

- Modify: `governance/replay_status.jsonl`
- Modify: progress tracker
- Generated governance receipt files only as required by existing policy

- [ ] Dry-run the status updater against the exact admitted run.
- [ ] Append one R4 green transition whose prerequisites are the admitted ABI 5
  run and unchanged G0-R3 ancestry.
- [ ] Require effective status: G0-R4 green; R5-R8 red.
- [ ] Reconstruct governance, authority, active test inventory and admission
  evidence once more without rerunning neural work.
- [ ] Record final verification commands and refs in the progress tracker.
- [ ] Commit: `governance(r4): complete data supervision replay`.

## Task 18: Produce the R5 handoff audit without implementing R5

**Files:**

- Modify only the progress tracker or add a separately governed R5 planning
  amendment if review shows the current R5 plan conflicts with ABI 2 access

- [ ] Confirm the only available consumer batch is authenticated train
  supervision.
- [ ] Confirm proposal targets no longer need observed selected programs and
  realizer targets no longer need input hashes, but do not implement the
  replacement R5 encoders yet.
- [ ] Enumerate exact R5 tasks for proposer target extraction, realizer encoding,
  selection, calibration, frozen evaluation, publication and runtime cutover.
- [ ] Keep current R5 status red and current release-model artifacts inactive.
- [ ] Commit only if the handoff changes governed documentation.

---

## 6. Required corruption matrix

Before Task 15, executable tests must reject:

- missing, extra, unhashed, duplicated or unreviewed source;
- empty derivation supervision;
- semantic case without a compiling derivation;
- gap case without typed abstention;
- bootstrap/runtime program substituted for reviewed derivation;
- exact expression replaced by subset/intersection acceptance;
- input surface substituted for response target;
- response expression, slot, action, polarity, modality, epistemic status,
  perspective, reference or literal alignment drift;
- marker-only realization equivalence;
- mutation executor echoing expected truth;
- undeclared semantic/operator/mode/participant/topology/response hard group;
- duplicate-risk component crossing purposes;
- unclassified, duplicated or cross-purpose case;
- diagnostic-only case entering a purpose payload;
- aggregate coverage masking one class-local failure;
- unsupported minimum being trimmed, selected or weakened;
- observed candidates or sibling identities in a purpose payload;
- payload, count, hash, capability, authorization or build-receipt tamper;
- admission identity embedded in candidate authorization;
- ABI 3/4 candidate treated as current;
- nondeterministic generation; and
- R5 consumer availability before fresh R4.1 admission.

## 7. Final verification

Use repository-defined selectors and admission commands as the source of truth.
At minimum, the final clean sequence must include:

```powershell
python scripts/check_test_inventory.py --phase G0 --source-only
python scripts/check_test_inventory.py --phase R4 --source-only
python -m compileall -q src scripts tests
python scripts/validate_mvp.py --tier phase --phase G0
python scripts/validate_mvp.py --tier phase --phase R1
python scripts/validate_mvp.py --tier phase --phase R2
python scripts/validate_mvp.py --tier phase --phase R3
python scripts/validate_mvp.py --tier phase --phase R4
python scripts/validate_mvp.py --tier admission --phase R4
```

Retain that exact admission run ref for Task 17. Do not run admission a second
time and do not improvise a direct ledger append.

## 8. Definition of done

The replay is complete only when code, strict schemas, reviewed source,
deterministic artifacts, admission reconstruction, train access, validation
selectors, active documentation and append-only status agree; the exact ABI 5
run is committed; R4 is effectively green; R5-R8 remain red; and no root-level
adoption or neural-model operation occurred.
