# R5 Hard-Cut Foundation Design

> **R4.1 prerequisite:** This document remains the governing R5 hard-cut and
> 17/25/1 disposition contract. R4.1 is an external prerequisite implemented
> and admitted outside this document. Neural activation and R6 composition
> cannot execute until fresh R4.1 admission proves the August 29
> data/supervision contract. Current status is derived only from
> [`governance/replay_status.jsonl`](../../../governance/replay_status.jsonl).

**Date:** 2026-08-13
**Status at publication:** approved hard-cut design; foundation implementation was later completed
**Scope:** `hybrid_mvp/` R5 test, governance, validation, and active-document foundation

## 1. Decision

R5 uses a hard-cut foundation before neural proposal or realization is
implemented. The foundation removes tests and fixtures that exist only for
retired semantic, runtime, Program ABI, training, model, or artifact paths. It
preserves the semantic/runtime hard-cut invariants without asserting current
phase admission and converts every still-valid frozen R5 assertion into an
explicit current-owner obligation.

The frozen predecessor inventory remains immutable evidence. Deleting a test
file does not erase its assertion lineage. Each of the 43 frozen R5 source-test
assertions must receive exactly one reviewed disposition: a current successor,
an explicit retirement, or a deferral to the neural-activation increment.
The inventory-derived partition is exact: 17 successors, 25 deferrals, and 1 explicit retirement.

This document owns no R5 phase status. At publication, selected neural proposal
and realization owners and their admitted artifacts did not yet exist.

## 2. Goals

1. Preserve every non-retired semantic, runtime, gate, artifact, and lineage
   invariant from the predecessor foundation without copying replay status.
2. Remove legacy test-support modules and every test whose only purpose is to
   exercise a retired path.
3. Give all 43 frozen R5 assertions an auditable, exact disposition without
   mutating the frozen inventory.
4. Define current R5 owner boundaries and source-only validation without
   claiming activation or admission.
5. Update active architecture, ABI, acceptance, governance, and roadmap
   documents so they route through the external R4.1 prerequisite and describe
   the actual R5 work remaining without copying status.
6. Add anti-bloat enforcement that prevents legacy fixture imports,
   compatibility-only model paths, and preservation-only tests from returning.

## 3. Non-goals

- This increment does not train, select, calibrate, or admit a neural proposer
  or neural realizer.
- It does not create selected checkpoints, production model manifests, or R5
  admission receipts.
- It does not change the five semantic operators, canonical runtime invariants,
  or repository-owned R4 evidence.
- It does not weaken existing exact gates or make obsolete tests pass through
  compatibility shims.
- It does not rewrite historical plans, reports, or receipts merely because
  they accurately describe superseded work at their original date.
- It does not adopt `hybrid_mvp/` as the root runtime; root adoption remains a
  separate reviewed change.

## 4. Current boundary

The frozen inventory contains 43 R5 source-test assertions across nine modules:

| Frozen module | Assertion count | Foundation treatment |
|---|---:|---|
| `tests/test_artifact_security.py` | 11 | Preserve all 11 artifact safety requirements through current R5 owner tests. |
| `tests/test_model_reproducibility.py` | 6 | Defer selected-model byte reproduction to neural activation; preserve the deterministic identity contract. |
| `tests/test_neural_realizer_weight_use.py` | 6 | Retire the one safe-fallback assertion forbidden by the completion contract; defer the other five authentic weight-use requirements. |
| `tests/test_canonical.py` | 4 | Preserve canonical serialization requirements under the current artifact owner. |
| `tests/test_neural_proposer.py` | 4 | Defer authentic proposal behavior; preserve legal-action and abstention boundaries as current contracts. |
| `tests/test_training_isolation.py` | 4 | Preserve partition isolation through current partition loaders; remove the retired trainer fixture stack. |
| `tests/test_calibration.py` | 3 | Defer measured calibration; preserve selection/calibration partition separation. |
| `tests/test_neural_weight_use.py` | 3 | Preserve the release-path exclusion as a successor and defer the two model-derived weight-use requirements. |
| `tests/test_production_proposer_cutover.py` | 2 | Defer production cutover until a selected current proposer exists. |

The implementation plan must enumerate every source-test reference, its exact
assertion identity, and its final disposition. Counts alone are not sufficient.

## 5. Assertion lifecycle

### 5.1 Successor

A successor preserves a still-valid assertion under a current public or owner
boundary. It must:

- retain the predecessor's exact `assertion_ref`;
- declare `activation_phase="R5"`;
- name the exact predecessor in `supersedes_node_id` or the applicable
  conjunctive lineage field;
- use only current source, data, and public contracts;
- be registered under one explicit R5 validation owner.

A successor may replace an implementation-specific test with a stronger
contract test. It must not recreate a retired API simply to preserve the old
test body.

### 5.2 Retirement

An assertion is retired only when the requirement itself depends on an obsolete
API, fixture, artifact format, compatibility identity, or architecture. The
retirement record must name the exact predecessor and a concrete historical
reason. Retirement cannot be used to hide an unimplemented current
requirement.

The sole R5 retirement is
`tests/test_neural_realizer_weight_use.py::TestNeuralRealizerWeightUse::test_failure_meaning_uses_safe_fallback`.
Its requirement is incompatible with `hybrid_mvp/AGENTS.md` section 7, which
requires zero fallback paths in the final release gates. No replacement may
reintroduce a safe, template, bootstrap, or UI fallback.

### 5.3 Deferral

A valid assertion that requires real neural artifacts remains an R5 obligation
but is not made executable by a fake model or fixture. Its reviewed metadata
must identify the next increment as `R5-Neural-Activation`, keep R5 red, and
state the concrete future owner: proposal, realization, selection, calibration,
weight-use, or reproduction.

Deferral is distinct from retirement. A deferred assertion must remain visible
in an exact machine-checked obligation manifest until a successor consumes it.

## 6. Test hard cut

### 6.1 Preserved tests

All non-retired predecessor lineage leaves remain present and executable. Tests
that assert absence of a retired subsystem may remain only when the absence is
an active security or architectural invariant, not when the test merely pads
coverage.

### 6.2 Removed support

The foundation removes `tests/legacy_propositions.py`,
`tests/legacy_runtime_fixtures.py`, and the conditional legacy-support loader in
`tests/conftest.py` after their valid assertions have successors or reviewed
dispositions. Any test module that imports those helpers must be migrated or
deleted in the same change.

The removal sweep also covers:

- retired Program ABI and result-wrapper fixtures;
- obsolete trainer and model constructors;
- `.pt` compatibility loaders and preservation-only checkpoint tests;
- fixed historical dataset/scenario counts that current manifests own;
- tests that require alternate runtime roots, phrase routers, or deprecated
  semantic paths;
- duplicate absence tests with no independent active invariant.

### 6.3 Current R5 tests

Foundation tests operate on current boundaries only:

- legal context-local proposal action and pointer contracts;
- explicit abstention requirements;
- train, selection, calibration, and frozen-test partition isolation;
- `ResponseMeaning` plus literal/provenance pointer inputs to realization;
- canonical artifact identity and content-addressing;
- selected-artifact reproducibility obligations;
- structural absence of legacy support and compatibility model paths.

Tests that need trained weights remain deferred rather than using a synthetic
artifact to claim production behavior.

## 7. R5 owner and validation architecture

The validation graph gains an R5 phase with explicit foundation owners:

1. `proposal-contract` — legal actions, pointers, abstention, and the public
   composition-root boundary.
2. `realization-contract` — typed `ResponseMeaning`, literal pointers,
   provenance, and the exact not-yet-admitted production-realizer boundary.
3. `data-isolation` — disjoint train, selection, calibration, and frozen-test
   access.
4. `artifact-contract` — canonical identity, safe formats, source/authority
   pinning, and reproduction obligations.
5. `legacy-hard-cut` — forbidden imports, files, constructors, loaders, and
   compatibility paths.

The R5 source-only inventory and owner tiers must pass at the end of this
increment. The R5 phase/admission transition remains red and unavailable until
the neural-activation increment supplies authentic selected owners, artifacts,
calibration evidence, weight-use evidence, and reproduction receipts.

No validation branch may select behavior from a surface string, model filename,
internal ref spelling, or legacy environment variable.

## 8. Machine-checked migration evidence

The foundation introduces one canonical R5 disposition artifact generated from
reviewed source data. It contains exactly the 43 frozen R5 source-test refs and,
for each row:

- predecessor source-test ref;
- exact assertion ref;
- disposition: `successor`, `retired`, or `deferred`;
- successor node IDs when applicable;
- concrete retirement reason when applicable;
- future activation task and owner when deferred.

The generated count invariant is exactly 17 `successor`, 25 `deferred`, and
1 `retired`. Those counts are derived from the pinned inventory rows, not from
test filenames or a hand-maintained replacement list.

Validation rejects missing, duplicate, unknown, or multiply disposed
predecessors; assertion-identity drift; successors outside R5; vague retirement
reasons; and deferred rows without a concrete future owner. The generator must
be byte-deterministic across two runs.

The immutable `governance/test_inventory.json` is never edited. The disposition
artifact extends its lineage evidence; it does not replace or reinterpret it.

## 9. Documentation migration

Active documentation must agree on the following status-neutral facts:

- replay status and admission identities come only from the ledger;
- fresh R4.1 admission is an external prerequisite for R5 implementation;
- the hard-cut foundation removes legacy test/runtime/model scaffolding but is
  not R5 admission;
- R5 purpose classes remain isolated, and their usable membership is determined
  only by the freshly admitted R4.1 contract;
- production activation requires a selected proposer and realizer to execute
  through the public composition root with model-derived confidence,
  calibration, weight-use, and byte-reproduction evidence.

At minimum, implementation reviews and updates the active document authority,
`docs/ARCHITECTURE.md`, `docs/ABI_REGISTRY.md`, the governing corrective-replay
roadmap, the active implementation status, and relevant acceptance statements.
Root canonical documents are changed only where they make a present-tense claim
that conflicts with this boundary. Historical documents stay classified as
historical or superseded evidence and are not cosmetically rewritten.

Document-authority tests must reject an old R5 document being presented as the
active execution plan.

## 10. Anti-bloat and failure behavior

The release foundation fails closed when:

- an active test imports a legacy support module;
- a deleted legacy helper or compatibility model loader reappears;
- a frozen R5 assertion lacks exactly one disposition;
- a successor changes assertion identity or depends on a retired API;
- a deferred neural requirement is mislabeled as retired;
- R5 is reported green without authentic neural admission evidence;
- an active document describes the external R4 manifest, legacy trainer stack,
  or obsolete R5 donor architecture as current;
- removal changes a non-retired predecessor active node set without an approved lineage
  migration;
- a validation gate broadens selectors merely to accommodate historical tests.

Failures identify the earliest owner: inventory lineage, disposition source,
test source, validation configuration, document authority, or current contract.
There is no permissive fallback.

## 11. Verification

Completion requires fresh evidence that:

1. all 43 frozen R5 assertions have exactly one valid disposition, partitioned
   as 17 successors, 25 deferrals, and one explicit retirement;
2. the disposition generator is byte-deterministic;
3. no active test imports or loads retired fixture support;
4. retired support files and preservation-only tests are absent;
5. every current R5 foundation owner test passes;
6. R5 source-only inventory verification passes;
7. the complete replay chain validates and remains the sole status owner;
8. strict anti-bloat and legacy audits report zero active findings;
9. documentation authority and inventory receipts reconstruct exactly;
10. the worktree contains no unreviewed generated or runtime-state files.

The raw historical pytest collection is not a release authority. The governed
inventory, exact owner/phase selectors, assertion dispositions, and anti-bloat
audits define the executable suite after the hard cut.

## 12. Completion state and next increment

This foundation is complete when the authoritative suite is smaller, all
remaining tests describe current contracts, documentation is truthful, the
predecessor hard-cut invariants remain enforced, and R5 has a precise
source-only owner boundary.

The following increment, `R5-Neural-Activation`, will implement and admit:

- neural proposal over legal context-local actions and pointers;
- explicit abstention and model-derived confidence;
- separate selection and calibration;
- production neural realization from `ResponseMeaning` and literal pointers;
- selected-checkpoint execution through the public composition root;
- zero-weight/ablation proof;
- byte-reproducible selected artifacts and ordinary governed R5 admission.
