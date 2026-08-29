# R4.1 Source-Readiness Correction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `subagent-driven-development` (recommended) or `executing-plans` to implement
> this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the canonical source universe and all five unpublished R4.1
review-source ABI 1 contracts fit for human-authored source, apply the exact
approved canonical scenario patch, and record source-readiness approval without
checking in the `data/review/r4_1/` package.

**Architecture:** Correct the earliest source owners in dependency order:
model-free source expansion, proposal truth, realization truth and purpose
truth. Generate bounded non-authoritative review worksheets only after the
contracts are exact. Record approval as a governance checkpoint, then return to
the main replay plan; never compensate in a compiler, solver, runtime or
artifact builder.

**Tech Stack:** Python 3, frozen dataclasses, canonical JSON/JSONL, JSON Schema
Draft 2020-12, SHA-256 content refs, pytest, PowerShell and Git.

**Approved design:**
`docs/superpowers/specs/2026-08-30-r4-1-source-readiness-correction-design.md`

**Parent plan:**
`docs/superpowers/plans/2026-08-29-r4-1-data-supervision-replay-plan.md`

---

## 1. Hard stop and execution rules

- Do not create or modify `data/review/r4_1/` in SR1-SR6.
- Do not run main replay Task 4 until SR6 records explicit human approval.
- Keep T03 `in_progress`, T04 `pending`, R4 red and R5-R8 red.
- Do not use runtime cycles, bootstrap proposals, verifier selections, model
  output, solver output or observed artifacts to fill reviewed fields.
- Repair the unpublished Proposal, Realization and Purpose ABI 1 shapes in
  place, preserve Review Manifest and Mutation ABI 1, and reconcile all five
  registry rows exactly once; do not mint ABI 2 or claim activation.
- Add no phase, validation tier, owner, pytest process or runtime hot-path scan.
- Add tests to existing R4 owner selectors and update metadata, selector inputs
  and inventory evidence atomically with each executable test change.
- Run commands from `hybrid_mvp/` unless a Git command explicitly uses the
  worktree root.

Before each SR:

```powershell
git status --short
python scripts/check_test_inventory.py --phase G0 --source-only
python scripts/check_test_inventory.py --phase R4 --source-only
```

After each SR:

```powershell
python -m compileall -q src scripts tests
python -m json.tool docs/DOCUMENT_AUTHORITY.json > $null
python -m json.tool configs/validation_gates.json > $null
git diff --check
```

## 2. File ownership map

| Owner | Responsibility |
|---|---|
| `scripts/generate_scenarios.py` | deterministic reviewed scenario source generation |
| `data/scenarios/use_cases.jsonl` | current reviewed scenario source, before R4.1 review packaging |
| `src/cemm_authoritative_hybrid/r4_contracts.py` | strict reviewed assertions/scenarios and expected response contracts |
| `src/cemm_authoritative_hybrid/r4_expansion.py` | canonical model-free source expansion seam |
| `scripts/expand_r4_cases.py` | thin bounded CLI over the canonical seam |
| `src/cemm_authoritative_hybrid/r4_supervision.py` | Proposal and Realization Supervision ABI 1 |
| `src/cemm_authoritative_hybrid/r4_supervision.py` | existing authenticated-bundle owner for one bounded cross-source semantic validator |
| `schemas/r4_proposal_supervision.schema.json` | exact proposal wire shape |
| `schemas/r4_realization_supervision.schema.json` | exact realization wire shape |
| `src/cemm_authoritative_hybrid/r4_purpose.py` | Purpose Contract ABI 1 and indexed component validation |
| `schemas/r4_purpose_contract.schema.json` | exact purpose wire shape |
| `scripts/build_r4_1_review_worksheets.py` | bounded non-authoritative worksheet generation |
| `artifacts/review_drafts/r4_1/` | generated review aids; never reviewed source authority |

## SR1: Establish the source-universe hard cut

**Files:**

- Modify: `scripts/generate_scenarios.py`
- Modify: `data/scenarios/use_cases.jsonl`
- Modify: `data/scenarios/SCENARIO_COVERAGE.md`
- Modify: `src/cemm_authoritative_hybrid/episodes.py`
- Modify: `src/cemm_authoritative_hybrid/r4_contracts.py`
- Modify: `src/cemm_authoritative_hybrid/r4_expansion.py`
- Rewrite: `scripts/expand_r4_cases.py`
- Modify: `docs/ABI_REGISTRY.md`
- Modify: `tests/test_scenario_coverage.py`
- Modify: `tests/test_semantic_episode.py`
- Modify: `tests/test_r4_assertion_compiler.py`
- Modify: `tests/test_r4_expansion.py`
- Modify other exact tests returned by
  `rg -l expected_gap_kind src scripts tests data/scenarios`

- [ ] **Step 1: Write RED source-shape and disposition tests.**

  Require strict rejection of `expected_gap_kind`; exact current reconstruction
  of `210 -> 400`; disjoint counts `248/112/20/20`; adversarial rows classified
  as `verification_rejection`; restart rows classified only as
  `restart_diagnostic_candidate`; and conflict assertions classified as
  alternatives, never multi-root.

  ```python
  assert current_universe.counts == {
      "semantic": 248,
      "explicit_gap": 112,
      "verification_rejection": 20,
      "restart_diagnostic_candidate": 20,
  }
  with pytest.raises(ValueError, match="unknown field"):
      ReviewedScenario.from_dict({**row, "expected_gap_kind": "proposal"})
  ```

- [ ] **Step 2: Run the focused tests and preserve the expected RED output.**

  ```powershell
  python -m pytest tests/test_scenario_coverage.py tests/test_semantic_episode.py tests/test_r4_assertion_compiler.py tests/test_r4_expansion.py -q -p no:cacheprovider
  ```

  Expected: failures name the duplicate field, broken expansion CLI and missing
  source-disposition owner, not an import or fixture typo.

- [ ] **Step 3: Remove the duplicate field at every active owner.**

  Delete `expected_gap_kind` from generated rows, checked-in rows,
  `ScenarioCase`, `ReviewedScenario`, serializers and constructors. Derive a
  typed gap only from one structured assertion whose `kind == "gap"`. Reject
  multiple gap assertions, gaps mixed with semantic truth, and bare gap fields.

- [ ] **Step 4: Add one closed source-disposition classifier.**

  Implement one exact enum/value object used by expansion and supervision:

  ```python
  semantic
  explicit_gap
  verification_rejection
  restart_diagnostic_candidate
  ```

  `adversarial` assertions map only to `verification_rejection`; `restart`
  assertions map only to `restart_diagnostic_candidate`. No competency-category
  string or runtime result may override structured assertion kind.

- [ ] **Step 5: Add the canonical model-free expansion seam and hostile-input tests.**

  Expose a bounded function in `r4_expansion.py` that accepts exact reviewed
  scenarios, authenticated authority and reviewed environments. It must not
  accept a caller `RevisionPin`. It internally constructs the source-only pin
  from the authenticated authority generation with all revisions zero and
  `model_identity=None`, or uses an equivalent dedicated source snapshot.
  Tests pass hostile caller-supplied revision pins and model identities through
  every public seam and require rejection before identity construction.

  Consume scenario iterables, every environment iterable and the aggregate
  case stream with a bounded next-item loop before materialization. Tests use
  infinite iterators and side-effecting iterators to prove failure at the exact
  bound and operation counts linear in accepted scenarios, environments and
  emitted cases. No `tuple(iterable)` or `list(iterable)` may precede the bound.

- [ ] **Step 6: Rewrite the expansion CLI as a thin consumer.**

  Construct the source-only expander exactly once and let it derive its own
  source snapshot. Delete the invalid dummy contract, caller pin and
  `CaseExpander().expand(scenario, contract)` call. Add an
  import-safe `main(argv: Sequence[str] | None = None) -> int`, bounded reads,
  canonical LF JSONL, atomic replace and a printed deterministic summary.

- [ ] **Step 7: Prove the seam is model-free and deterministic.**

  Run the CLI twice into separate temporary paths and compare bytes. AST tests
  reject imports/calls of PROPOSE, VERIFY, EVALUATE, EFFECT, REALIZE, runtime,
  bootstrap, model, solver and observed episode owners.

- [ ] **Step 8: Reconcile all five ABI registry rows exactly once.**

  Update `R4 Review Manifest ABI`, `Proposal Supervision ABI`, `Realization
  Supervision ABI`, `Mutation Contract ABI` and `Purpose Contract ABI` together.
  State that strict decoders are implemented and the review-manifest
  authenticated loader is implemented, while compiler, checked-in reviewed
  data, publication and admission remain pending as applicable. Add an exact
  registry test and make no activation claim. Later SRs must not rewrite these
  implementation-state cells piecemeal.

- [ ] **Step 9: Refresh exact metadata/selectors and run inventory checks.**

  Keep source-expansion nodes in `r4_surface_expansion_owner_tests`; place
  strict source/contract nodes in their existing R4 owners. Add only exact
  changed inputs. Do not add a step or process.

- [ ] **Step 10: Commit.**

  ```powershell
  git add scripts src tests data/scenarios docs/ABI_REGISTRY.md configs governance
  git commit -m "fix(r4): establish reviewed source universe hard cut"
  ```

**Checkpoint SR1:** the corrected seam reconstructs and classifies the current
210/400 universe without runtime authority. The proposed eight structural
families are not yet source rows.

## SR2: Repair Proposal Supervision ABI 1

**Files:**

- Modify: `src/cemm_authoritative_hybrid/r4_supervision.py`
- Modify: `schemas/r4_proposal_supervision.schema.json`
- Modify: `tests/test_r4_supervision_contracts.py`
- Verify: the five-row `docs/ABI_REGISTRY.md` reconciliation committed in SR1;
  do not edit implementation state or claim activation here

- [ ] **Step 1: Write RED tests for the repaired wire contract.**

  Cover exact `match_policy`, closed `expected_expression_relation`, relation/
  cardinality parity, verification rejection distinct from abstention, dense
  integer handles, duplicate/unbound handles, graph-component mismatch,
  semantic-kind mismatch, invalid/cross-surface spans, structural bindings that
  falsely carry spans/kinds, grounded bindings that omit case/surface evidence,
  raw phrase/regex/internal ref selectors, incomplete source assignments and
  conflict-as-multi-root substitution.

  ```python
  assert target.match_policy == "exact"
  assert target.expected_expression_relation in {"none", "single", "conflict"}
  assert tuple(binding.selector_handle for binding in blueprint.selector_bindings) == tuple(
      range(len(blueprint.selector_bindings))
  )
  ```

- [ ] **Step 2: Run proposal tests and confirm RED.**

  ```powershell
  python -m pytest tests/test_r4_supervision_contracts.py -q -p no:cacheprovider -k "proposal or selector or blueprint or abstention"
  ```

- [ ] **Step 3: Replace string selectors with a closed binding union.**

  Add frozen, factory-only `SourceSpan`, `GroundedSelectorBinding` and
  `StructuralSelectorBinding` values beneath a closed `SelectorBinding` union.
  A grounded binding contains an integer handle, exact case/surface identities,
  graph-component ref, semantic kind, bounded nonempty exact spans and one
  reviewed source-unit/contribution selector. A structural binding contains an
  integer handle and typed Program-local declaration/ref/tag/closed literal
  only; it rejects case/surface evidence, semantic kind and spans. Blueprint
  actions carry handles only. Validate the complete binding table before
  actions.

- [ ] **Step 4: Add complete reviewed source assignments.**

  Add a frozen, factory-only, bounded `SourceAssignmentBlueprint` to every
  derivation. Each entry owns source geometry/source-unit selector,
  contribution kind, assignment kind, target action/role for consumption,
  residual kind for retention and criticality. Validate every observed unit is
  assigned exactly once as consumed or typed residual; reject missing,
  duplicate, inferred and critical-residual-executable cases.

- [ ] **Step 5: Separate equality policy from expression relation and add the
  exact rejection target.**

  Replace `expression_relation: "exact"` with
  `match_policy: "exact"` and `expected_expression_relation`. Enforce:

  ```text
  derive + 1 expression     -> single
  derive + >=2 alternatives -> conflict
  abstain + 0 expressions   -> none
  verification_rejection    -> none
  ```

  A conflict row contains alternative complete expression refs. It cannot bind
  them as simultaneous graph components.

  `target_kind: verification_rejection` contains no expressions or abstention.
  It owns one reviewed adversarial/mutation blueprint or payload plus exact
  expected VERIFY owner, error code, rejection disposition and criticality.
  Schema and decoder reject a generic gap alias and any observed verifier result
  used as the reviewed expectation.

- [ ] **Step 6: Update Draft 2020-12 schema and parity tests.**

  Use exact tagged unions, integer/span maxima and `additionalProperties:
  false`. Keep semantic cross-field checks in the decoder and structural checks
  in the schema; adversarially prove neither accepts a shape the other rejects.

- [ ] **Step 7: Run both R4 source-contract modules in one process.**

  ```powershell
  python -m pytest tests/test_r4_supervision_contracts.py tests/test_r4_purpose_contracts.py -q -p no:cacheprovider
  ```

- [ ] **Step 8: Refresh metadata/selectors, run G0/R4 source-only inventory and commit.**

  ```powershell
  git commit -m "fix(r4): repair proposal supervision abi 1"
  ```

**Checkpoint SR2:** every proposal target is expressible without observed
program authority; conflict alternatives remain distinct from multi-root.

## SR3: Repair Realization Supervision ABI 1 and epistemic owners

**Files:**

- Modify: `src/cemm_authoritative_hybrid/r4_contracts.py`
- Modify: `src/cemm_authoritative_hybrid/r3_response.py`
- Modify earliest active ResponseMeaning owner(s) identified by
  `rg -l epistemic_status src/cemm_authoritative_hybrid`
- Modify: `src/cemm_authoritative_hybrid/r4_supervision.py`
- Modify: `schemas/r4_realization_supervision.schema.json`
- Modify: `tests/test_r4_assertion_compiler.py`
- Modify: `tests/test_r3_learning_response.py`
- Modify: `tests/test_r4_supervision_contracts.py`
- Modify exact realization-verifier tests affected by the canonical ref hard cut

- [ ] **Step 1: Write RED earliest-owner and realization tests.**

  Reject bare epistemic strings, a response signature without
  `expected_expression_relation`, self-supplied literal/input-surface authority,
  unknown alignment tags, missing/duplicate required-slot coverage, more than
  four variants, missing initial variants for semantic/gap/rejection cases, and
  any realization row for a restart-diagnostic case. Add explicit R5 canaries
  requiring safe authorized surfaces for typed gaps and verifier rejections.

- [ ] **Step 2: Run focused tests and confirm RED at the earliest owner.**

  ```powershell
  python -m pytest tests/test_r4_assertion_compiler.py tests/test_r3_learning_response.py tests/test_r4_supervision_contracts.py -q -p no:cacheprovider -k "epistemic or realization or alignment or slot"
  ```

- [ ] **Step 3: Migrate epistemic values to canonical refs.**

  Require `epistemic_status:*` at scenario assertion compilation,
  `ExpectedResponseContract`, ResponseMeaning construction and realization
  verification. Delete late prefixing and bare-string fallback maps. Unknown
  refs fail closed.

- [ ] **Step 4: Add the closed response-subject union.**

  Add exact `expression_set`, `typed_gap` and `verifier_rejection` subjects.
  Expression subjects carry `single` or `conflict` plus complete expression
  refs. Gap and rejection subjects carry relation `none` plus their exact typed
  subject and no expressions. The content-addressed signature also covers
  bindings, action, polarity, modality, epistemic status, speaker, addressee and
  exact semantic slots.

- [ ] **Step 5: Replace literal alignment with the tagged union.**

  Implement exact `designation`, `reference`, `literal`, `morphology` and
  `omission` variants. Each variant owns its tag-specific fields, output span
  and slot. Literal variants accept only independently reviewed/authenticated
  decision, effect or obligation literal refs. Delete `source_literal` as a
  trust root and reject `input_surface`.

- [ ] **Step 6: Enforce row-local coverage and initial-publication bounds.**

  Required slots are covered exactly once by output alignment or reviewed
  omission. Permit at most four variants in ABI 1 generally. Initial source
  requires exactly one variant for every supervised semantic, explicit-gap and
  verification-rejection case and zero for diagnostic restart. All totals are
  successor-universe-derived; do not hard-code 248 or another predecessor count.
  File-local duplicate identity remains loader-owned and cross-source
  completeness is verified in SR4 before main Tasks 5 and 6 compile/equivalence
  work.

- [ ] **Step 7: Add R5 safe-surface canaries without activating R5.**

  Require every supervised gap/rejection response subject to select one
  reviewed safe authorized surface with exact semantic slots, epistemic status
  and round-trip subject equivalence. Empty strings, input echo and UI fallback
  placeholders fail. Keep the canaries in an existing R4/R5 boundary owner and
  do not mint a train/evaluation capability.

- [ ] **Step 8: Update schema/parity, run one-process contract tests, refresh
  metadata/inventory and commit.**

  ```powershell
  git commit -m "fix(r4): repair realization supervision abi 1"
  ```

**Checkpoint SR3:** every supervised source kind has an unambiguous safe
realization row shape; only diagnostic restart is excluded.

## SR4: Repair Purpose Contract ABI 1

**Files:**

- Modify: `src/cemm_authoritative_hybrid/r4_purpose.py`
- Modify: `src/cemm_authoritative_hybrid/r4_supervision.py`
- Modify: `schemas/r4_purpose_contract.schema.json`
- Modify: `tests/test_r4_purpose_contracts.py`
- Verify: the five-row `docs/ABI_REGISTRY.md` reconciliation committed in SR1

- [ ] **Step 1: Write RED group-ownership and denominator tests.**

  Reject a grouped member with direct purpose, a group without purpose, a
  diagnostic with purpose/group, a `verification_rejection` classified as gap
  or diagnostic, overlapping groups with different purposes, unknown component
  membership, conflict-set-derived groups, incomplete denominator-by-four-
  purpose products and denominator-family drift.

- [ ] **Step 2: Add a linear-operation counter test.**

  Build a bounded synthetic contract with overlapping reviewed groups and
  assert validation performs indexed map/union operations proportional to rows
  plus memberships. Do not use wall-clock assertions.

- [ ] **Step 3: Run purpose tests and confirm RED.**

  ```powershell
  python -m pytest tests/test_r4_purpose_contracts.py -q -p no:cacheprovider
  ```

- [ ] **Step 4: Move purpose ownership to groups.**

  Add exact `purpose` to `DuplicateRiskGroup`. Require grouped supervised
  memberships to have `purpose: null`; require ungrouped supervised memberships
  to have one direct purpose; add the exact supervised classification
  `verification_rejection`; require diagnostics to have neither.

- [ ] **Step 5: Validate transitive components with indexed union/find.**

  Index cases and groups once, union overlapping explicit reviewed groups,
  reduce each component to one purpose, and resolve every grouped membership
  through that component. No identity dimension and no conflict set creates a
  group implicitly.

- [ ] **Step 6: Enforce the denominator Cartesian family.**

  For every denominator ref, require exactly one row for each of the four
  purposes and require one shared denominator family. Minimums remain positive,
  reviewer-authored and immutable; do not derive or trim them.

- [ ] **Step 7: Add one bounded cross-source semantic validator.**

  Implement it under the existing `r4_supervision` authenticated-bundle owner,
  consuming the already-decoded source universe, proposals, realizations and
  purpose contract once. With bounded indexes, require exact selector case/
  surface ownership and spans; exactly one ProposalTarget and one initial
  RealizationRow for every supervised case; zero of both for diagnostics; max
  four realization variants; exactly one PurposeMembership for every source
  case; and no missing/extra/duplicate cases or rows. Add hostile shuffled,
  missing, duplicate, cross-case and over-bound fixtures plus linear operation-
  count assertions. Do not add a gate step, owner or process.

  Keep ownership boundaries executable: schema handles structure/tags/bounds;
  row decoders handle content refs and row-local invariants; file loaders handle
  canonical bytes/count/duplicate identity; this validator handles joins and
  bundle completeness. Main Tasks 5 and 6 compile and prove equivalence; they
  do not discover supervised eligibility.

- [ ] **Step 8: Update schema/parity, run both contract modules in one process,
  refresh metadata/inventory and commit.**

  ```powershell
  git commit -m "fix(r4): repair purpose supervision abi 1"
  ```

**Checkpoint SR4:** direct and inherited purpose are unambiguous, components are
transitive, and validation remains linearly bounded.

## SR5: Produce bounded draft worksheets and obtain human review

**Files:**

- Add: `scripts/build_r4_1_review_worksheets.py`
- Add or modify tests under an existing R4 data-owner module; do not add a gate
  process
- Generate: `artifacts/review_drafts/r4_1/SOURCE_UNIVERSE.json`
- Generate: `artifacts/review_drafts/r4_1/STRUCTURAL_DECISIONS.json`
- Generate: `artifacts/review_drafts/r4_1/SUPERVISION_DECISIONS.json`
- Generate: `artifacts/review_drafts/r4_1/PURPOSE_DECISIONS.json`
- Generate: `artifacts/review_drafts/r4_1/REVIEW_SUMMARY.md`

- [ ] **Step 1: Write RED worksheet-boundary tests.**

  Require source-only inputs, deterministic bytes, bounded files/records/bytes,
  explicit unresolved decisions, no observed/runtime/bootstrap/model/solver
  fields, no output beneath `data/review/r4_1/`, and one exact row for every
  audited or proposed source decision.

- [ ] **Step 2: Implement the draft-only builder.**

  Read the corrected source universe once. Emit content-addressed worksheets
  with `draft_non_authoritative: true`, exact input identities and no default
  answers. Refuse to overwrite a reviewed-source path or accept runtime/artifact
  data as input.

- [ ] **Step 3: Include all structural decisions.**

  The worksheet must enumerate: conflict sets preserved as alternatives; four
  linked families (at least two semantic `SIMULATE`, at least one
  `op:type`/`role:type`); four true multi-root non-conflict families; the legacy
  conditional choice; restart diagnostic approval; exact designation/output
  decisions; mutation truth; duplicate groups; purposes; holdouts;
  denominators; and fixed positive minima. It must also carry the exact proposed
  patch to `scripts/generate_scenarios.py`, the exact resulting scenario rows,
  and generator decisions needed to reproduce all eight families. A prose-only
  family approval is insufficient.

- [ ] **Step 4: Generate twice and compare byte identities.**

  ```powershell
  python scripts/build_r4_1_review_worksheets.py --output artifacts/review_drafts/r4_1-a
  python scripts/build_r4_1_review_worksheets.py --output artifacts/review_drafts/r4_1-b
  ```

  Expected: exact file-name, byte-length and SHA-256 equality. This proves only
  deterministic drafting, not review.

- [ ] **Step 5: Promote only the verified A bytes.**

  After A/B equality succeeds, atomically promote the exact verified A bytes
  from `artifacts/review_drafts/r4_1-a` to
  `artifacts/review_drafts/r4_1` using the repository canonical file-set
  publisher. Recompute file names, lengths and SHA-256 after promotion and
  require equality with A. Do not rerun the worksheet generator for the final
  path and do not silently regenerate on a missing or mismatched file.

- [ ] **Step 6: Run contract, selector, inventory and static gates; commit the
  generator and reproducible draft aids.**

  ```powershell
  git commit -m "feat(r4): produce source readiness review worksheets"
  ```

- [ ] **Step 7: Stop for human review.**

  Present exact worksheet refs/hashes and the successor scenario/expanded-case
  counts. Do not interpret silence, a passing compiler or a prior general
  approval as approval of these bytes.

**Checkpoint SR5 — human decision required:** all structural, proposal,
realization, mutation, purpose and minima decisions are explicit, but Task 4
remains blocked and no reviewed source package exists.

## SR6: Apply the approved canonical source patch and record approval

**Files (only after explicit human approval):**

SR6 must apply the exact approved scenario patch before it records approval
evidence.

- Modify: `scripts/generate_scenarios.py`
- Regenerate: `data/scenarios/use_cases.jsonl`
- Modify: `data/scenarios/SCENARIO_COVERAGE.md`
- Modify exact source-universe tests and metadata/selectors as required
- Add: `docs/superpowers/reviews/2026-08-30-r4-1-source-readiness-approval.md`
- Modify: `docs/DOCUMENT_AUTHORITY.json`
- Modify: `docs/superpowers/progress/2026-08-29-r4-1-data-supervision-replay-progress.md`
- Modify the existing tracker/governance test to enforce the approval
  document's exhaustive classification; do not add a node

- [ ] **Step 1: Validate approval completeness.**

  Record reviewer refs, exact worksheet refs/hashes, corrected contract commit
  refs, successor scenario/expanded-case identities and counts, all eight
  structural-family decisions, conditional/restart decisions, and exact
  designation/output/mutation/purpose/minima decisions. Reject partial or
  conditional approval.

- [ ] **Step 2: Write RED canonical-source and approval-classification tests.**

  Require the checked-in generator diff to equal the exact approved scenario
  patch, canonical regeneration to equal checked-in `use_cases.jsonl`, and the
  model-free successor universe to match the approved identities and
  successor-universe-derived counts. Separately require the future approval doc
  to appear exactly once in `docs/DOCUMENT_AUTHORITY.json` under
  `historical_evidence`, never `governing_documents`, with the exhaustive
  authority-like classification test still complete.

- [ ] **Step 3: Apply the exact approved scenario patch and commit it.**

  Apply the exact approved scenario patch to `generate_scenarios.py`; do not
  reinterpret its choices. Regenerate `data/scenarios/use_cases.jsonl` using the
  canonical generator, reconstruct through the model-free seam, verify exact
  successor identities/counts and all structural constraints, refresh metadata/
  selectors/inventory, and commit before writing approval evidence.

  ```powershell
  git commit -m "data(r4): apply approved source readiness scenario patch"
  ```

  This commit still contains no `data/review/r4_1/` package.

- [ ] **Step 4: Bind approval to the committed canonical source.**

  Require the approval doc to bind every SR1-SR5 commit and worksheet identity,
  the exact approved scenario-patch commit, regenerated scenario/source-universe
  identities and counts. Require the tracker checkpoint to reference that exact
  document without phase/admission/completion claims.

- [ ] **Step 5: Add the approval evidence and update operational tracking.**

  Mark `RC-SOURCE-READINESS` satisfied only. Keep T03 `in_progress`, T04
  `pending`, `RC-SOURCE` pending, the source directory absent and phase status
  solely in `governance/replay_status.jsonl`. Classify the approval doc exactly
  once as `historical_evidence` in `docs/DOCUMENT_AUTHORITY.json` and update the
  existing exhaustive authority-like classification test atomically.

- [ ] **Step 6: Run focused governance, exact selectors, G0/R4 source-only
  inventory, compile/JSON/diff checks and commit the second change.**

  ```powershell
  git commit -m "docs(r4): record source readiness approval"
  ```

- [ ] **Step 7: Stop before source check-in.**

  Return to main replay Task 4. That task, not this plan, checks in the exact
  approved `data/review/r4_1/` package, writes its manifest last, obtains the
  second data review and freezes the source-bundle ref.

**Checkpoint SR6:** Task 4 is eligible to resume; no R4 admission, source
publication, artifact publication or phase promotion has occurred.
