# R4 Repository-Owned Admission Design

**Date:** 2026-08-12
**Status:** approved design; implementation pending
**Scope:** `hybrid_mvp/` R4 admission and closeout only

## 1. Decision

R4 does not require an external reviewer, an externally signed manifest, or an
injected signature verifier. R4 closes through the same repository-owned,
deterministic admission model used by G0 and R1-R3.

The former external-review path is retired as an R4-only authority experiment.
It must not remain as an optional compatibility layer because it would preserve
unused authority, configuration, tests, and operational burden without serving
the active release contract.

This is a reviewed contract migration, not a validation waiver. R4 becomes
green only after the committed corpus and complete artifact graph reconstruct
exactly, all semantic and anti-bloat gates pass, and the ordinary append-only
governance flow admits the resulting receipt.

## 2. Goals

1. Replace external signature authorization with deterministic, repository-owned
   R4 artifact-integrity admission.
2. Preserve or strengthen every semantic, structural, provenance, partition,
   sufficiency, and reproducibility check that does not depend on an external
   signer.
3. Remove dead R4 external-review code, data contracts, scripts, configuration,
   and tests rather than carrying legacy compatibility behavior.
4. Regenerate all affected deterministic artifacts and keep code, ABIs,
   generators, active documentation, validation configuration, evidence, and
   the replay ledger consistent.
5. Admit R4 as an ordinary `green` phase and merge the completed closeout to
   `main`.

## 3. Non-goals

- This change does not weaken semantic correctness, corpus sufficiency,
  partition isolation, source pinning, authority pinning, or reproducibility.
- It does not change the five-operator kernel or any runtime semantic ABI.
- It does not reopen G0 or R1-R3 admissions.
- It does not remove the generic `externally_blocked` governance state if that
  state has other current or future owners. It only removes R4's dependency on
  external review.
- It does not preserve obsolete tests merely to maintain coverage counts.

## 4. Architecture

### 4.1 Admission flow

The active R4 flow becomes:

```text
reviewed scenario source
-> independent expected-contract compilation
-> bounded surface/environment expansion
-> authentic runtime execution
-> exact expected/observed comparison
-> semantic mutation execution
-> structural sufficiency validation
-> independent partition generation
-> deterministic artifact graph
-> repository-owned artifact-integrity reconstruction
-> governed R4 admission receipt
-> append-only green R4 ledger record
```

The admission gate must not read `R4_REVIEW_MANIFEST.json`, load a verifier,
inspect signing code, or depend on review-related environment variables.

### 4.2 Artifact-integrity owner

The current R4 admission module remains the single owner for reconstructing the
committed artifact graph. Its public operation is simplified to accept only:

- the project root;
- the expected committed source revision; and
- the expected linked authority generation.

It must decode every R4 artifact through its exact ABI, reject non-canonical or
empty data, and reconstruct the build receipt from committed source and artifact
bytes. It must fail closed when any of the following is false:

- expected contracts, expanded cases, and authentic episodes are non-empty;
- every authentic episode comparison passes;
- every mutation observation passes;
- the structural sufficiency receipt passes;
- all seven partition axes are present in canonical order;
- the training allowlist decodes exactly;
- source revision and authority generation pins match admission context;
- all recorded hashes and content references reconstruct exactly;
- the build contains the expected complete corpus, including the checked-in
  400-case R4 diagnostic matrix;
- two clean artifact generations are byte-identical.

The step emits a bounded canonical report containing the artifact count,
artifact-set reference, build-receipt reference, source revision, authority
generation, and its own integrity reference. It contains no reviewer,
signature, verifier, manifest, or approval fields.

### 4.3 Validation graph

The `R4` admission tier replaces `r4_artifact_review` with
`r4_artifact_integrity`. The new step depends on authenticated governance and
SQLite authority activation, consumes the committed R4 artifact graph and its
source owners, and uses the same admission-run source manifest as the other
steps.

The R4 admission tier continues to include:

- governance verification;
- the active pytest inventory;
- authority linking and SQLite activation through the dependency graph; and
- R4 artifact-integrity reconstruction.

No environment variable can change the trust root or admission result.

## 5. ABI and artifact migration

The R4 build receipt must no longer encode
`review_state="external_review_required"`. Because this changes the exact wire
contract, the build-receipt ABI is bumped rather than accepting both old and new
states.

The replacement state denotes only that the build is a deterministic admission
candidate; the build receipt does not self-admit or mutate governance. Final
phase authority remains the admission receipt plus append-only replay ledger.

The following external-review artifacts are removed:

- the Corpus Review Manifest ABI and implementation;
- the R4 approval ABI/object;
- the external verifier loader and trust-root protocol;
- the unsigned review-request generator;
- the signed-manifest verifier CLI;
- the corpus-review manifest schema;
- the R4 review-manifest template; and
- review/verifier environment-variable handling.

The ABI registry records the retirement and the replacement build-receipt ABI.
Generated R4 artifacts are rebuilt from their current generators, and the
generator is run twice to prove byte identity. A stale build receipt or artifact
from the retired ABI must fail exact decoding rather than receive a compatibility
fallback.

## 6. Code and test ownership

Tests are changed at their earliest owner:

- signature, external-verifier, and anti-self-signing tests are deleted or
  replaced because their contract is retired;
- artifact-integrity tests assert exact reconstruction and fail-closed behavior
  for tampered hashes, missing axes, mismatched revisions, failed comparisons,
  and non-canonical bytes;
- validation-gate tests assert that R4 admission needs no external files or
  environment variables and that its report has the exact new schema;
- structural tests assert the absence of the retired external-review imports,
  scripts, configuration, and manifest path;
- deterministic build, corpus, mutation, sufficiency, partition, activation,
  anti-bloat, and 400-case authentic-cycle tests remain active.

Inventory entries are updated from exact successor tests and freshly computed
AST hashes. Legacy external-review tests are not carried forward merely to
preserve test counts; coverage is preserved through tests of the replacement
artifact-integrity owner.

## 7. Documentation ownership

Active R4 documentation and the ABI registry are updated to state that R4 uses
repository-owned admission. The 2026-08-12 external-review closeout spec and
plan are marked superseded by this contract. Older plans remain historical
evidence and are not rewritten as though they had never required external
review.

No canonical root document needs a semantic change because the root contracts
do not require an external R4 signer. If implementation discovery finds an
active root statement that does require one, that statement must be migrated in
the same change before admission.

## 8. Error handling

All integrity failures are admission-blocking and identify the earliest
divergent artifact or pin. There is no unsigned fallback, optional verifier
branch, permissive ABI decoder, manually asserted approval, or UI-level success
substitution.

The phase ledger is not changed until a clean committed R4 admission run passes.
If admission fails, the earliest owner is repaired and artifacts are regenerated;
the ledger remains red.

## 9. Verification and closeout

Implementation is complete only after this sequence succeeds from committed,
clean governed inputs:

1. focused replacement-owner tests;
2. structural and anti-bloat checks;
3. deterministic R4 artifact generation twice with byte-identical results;
4. the complete 400-case expected/observed diagnostic with 400 passes;
5. full active pytest inventory;
6. R4 admission tier with no review manifest or verifier environment;
7. append-only transition of R4 to `green` using the exact passed admission
   receipt;
8. replay-chain verification; and
9. merge to `main` followed by a final clean verification of the merged state.

The existing unrelated untracked files in the primary workspace are not part of
this change. Implementation and admission should use an isolated clean worktree
so those files are neither moved nor committed.

## 10. Acceptance criteria

R4 is officially closed when all of the following are true:

- no active R4 code or admission configuration requires an external signed
  manifest or verifier;
- no retired external-review module, CLI, schema, template, or signature-only
  test remains without another explicit owner;
- the R4 artifact graph reconstructs exactly from committed inputs;
- all 400 authentic R4 cases pass;
- all required authority, ABI, activation, anti-bloat, and regression gates
  pass;
- the replay ledger's effective R4 state is `green` and is bound to a passed,
  committed admission receipt; and
- the complete closeout is merged to `main` without importing unrelated
  workspace files.
