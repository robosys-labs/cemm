# R4.1 Source-Readiness Correction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `subagent-driven-development` (recommended) or `executing-plans` to implement
> this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the canonical source universe and unpublished Proposal,
Realization and Purpose ABI 1 contracts fit for human-authored R4.1 source,
then obtain explicit source-readiness approval without checking in the source
package.

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
- Repair the three unpublished ABI 1 contracts in place; do not mint ABI 2.
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

- [ ] **Step 5: Add the canonical model-free expansion seam.**

  Expose a bounded function in `r4_expansion.py` that accepts exact reviewed
  scenarios, an exact expected-contract compiler, a revision pin and reviewed
  environments; returns one immutable source-universe value containing
  canonical cases, dispositions and counters; and imports no proposer, runtime,
  model, solver or episode builder.

- [ ] **Step 6: Rewrite the expansion CLI as a thin consumer.**

  Construct `CaseExpander(compiler)` exactly once and call
  `expand(..., revision_pin=pin, environments=...)`. Delete the invalid dummy
  contract and `CaseExpander().expand(scenario, contract)` call. Add an
  import-safe `main(argv: Sequence[str] | None = None) -> int`, bounded reads,
  canonical LF JSONL, atomic replace and a printed deterministic summary.

- [ ] **Step 7: Prove the seam is model-free and deterministic.**

  Run the CLI twice into separate temporary paths and compare bytes. AST tests
  reject imports/calls of PROPOSE, VERIFY, EVALUATE, EFFECT, REALIZE, runtime,
  bootstrap, model, solver and observed episode owners.

- [ ] **Step 8: Refresh exact metadata/selectors and run inventory checks.**

  Keep source-expansion nodes in `r4_surface_expansion_owner_tests`; place
  strict source/contract nodes in their existing R4 owners. Add only exact
  changed inputs. Do not add a step or process.

- [ ] **Step 9: Commit.**

  ```powershell
  git add hybrid_mvp/scripts hybrid_mvp/src hybrid_mvp/tests hybrid_mvp/data/scenarios hybrid_mvp/configs hybrid_mvp/governance
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
- Modify: `docs/ABI_REGISTRY.md` only to clarify the unchanged unpublished ABI
  1 shape; do not claim activation

- [ ] **Step 1: Write RED tests for the repaired wire contract.**

  Cover exact `match_policy`, closed `expected_expression_relation`, relation/
  cardinality parity, verification rejection distinct from abstention, dense
  integer handles, duplicate/unbound handles, graph-component mismatch,
  semantic-kind mismatch, invalid/cross-surface spans, raw phrase/regex/internal
  ref selectors and conflict-as-multi-root substitution.

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

- [ ] **Step 3: Replace string selectors with `SelectorBinding`.**

  Add frozen, factory-only `SourceSpan` and `SelectorBinding` values. Each
  binding contains an integer case-local handle, expected graph-component ref,
  semantic kind, exact source span and the bounded source-local Program ABI 2
  value. Blueprint actions carry handles only. Validate all bindings before
  validating actions.

- [ ] **Step 4: Separate equality policy from expression relation.**

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

- [ ] **Step 5: Update Draft 2020-12 schema and parity tests.**

  Use exact tagged unions, integer/span maxima and `additionalProperties:
  false`. Keep semantic cross-field checks in the decoder and structural checks
  in the schema; adversarially prove neither accepts a shape the other rejects.

- [ ] **Step 6: Run both R4 source-contract modules in one process.**

  ```powershell
  python -m pytest tests/test_r4_supervision_contracts.py tests/test_r4_purpose_contracts.py -q -p no:cacheprovider
  ```

- [ ] **Step 7: Refresh metadata/selectors, run G0/R4 source-only inventory and commit.**

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
  four variants, more than one initial variant, and realization rows for gap,
  verification-rejection or restart-diagnostic cases.

- [ ] **Step 2: Run focused tests and confirm RED at the earliest owner.**

  ```powershell
  python -m pytest tests/test_r4_assertion_compiler.py tests/test_r3_learning_response.py tests/test_r4_supervision_contracts.py -q -p no:cacheprovider -k "epistemic or realization or alignment or slot"
  ```

- [ ] **Step 3: Migrate epistemic values to canonical refs.**

  Require `epistemic_status:*` at scenario assertion compilation,
  `ExpectedResponseContract`, ResponseMeaning construction and realization
  verification. Delete late prefixing and bare-string fallback maps. Unknown
  refs fail closed.

- [ ] **Step 4: Put expression relation into the response signature.**

  The content-addressed signature covers relation, complete expression refs,
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
  omission. Permit at most four variants in ABI 1 generally, but require exactly
  one initial row for each current semantic case. Keep bundle-wide `248` current
  completeness in the future main Task 6 compiler checkpoint, not a decoder
  that cannot see the bundle.

- [ ] **Step 7: Update schema/parity, run one-process contract tests, refresh
  metadata/inventory and commit.**

  ```powershell
  git commit -m "fix(r4): repair realization supervision abi 1"
  ```

**Checkpoint SR3:** the audited current semantic universe has an unambiguous
one-row realization contract; nonsemantic cases cannot acquire output gold.

## SR4: Repair Purpose Contract ABI 1

**Files:**

- Modify: `src/cemm_authoritative_hybrid/r4_purpose.py`
- Modify: `schemas/r4_purpose_contract.schema.json`
- Modify: `tests/test_r4_purpose_contracts.py`
- Modify: `docs/ABI_REGISTRY.md` only to clarify the unchanged unpublished ABI
  1 shape

- [ ] **Step 1: Write RED group-ownership and denominator tests.**

  Reject a grouped member with direct purpose, a group without purpose, a
  diagnostic with purpose/group, overlapping groups with different purposes,
  unknown component membership, conflict-set-derived groups, incomplete
  denominator-by-four-purpose products and denominator-family drift.

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
  to have one direct purpose; require diagnostics to have neither.

- [ ] **Step 5: Validate transitive components with indexed union/find.**

  Index cases and groups once, union overlapping explicit reviewed groups,
  reduce each component to one purpose, and resolve every grouped membership
  through that component. No identity dimension and no conflict set creates a
  group implicitly.

- [ ] **Step 6: Enforce the denominator Cartesian family.**

  For every denominator ref, require exactly one row for each of the four
  purposes and require one shared denominator family. Minimums remain positive,
  reviewer-authored and immutable; do not derive or trim them.

- [ ] **Step 7: Update schema/parity, run both contract modules in one process,
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
  denominators; and fixed positive minima.

- [ ] **Step 4: Generate twice and compare byte identities.**

  ```powershell
  python scripts/build_r4_1_review_worksheets.py --output artifacts/review_drafts/r4_1-a
  python scripts/build_r4_1_review_worksheets.py --output artifacts/review_drafts/r4_1-b
  ```

  Expected: exact file-name, byte-length and SHA-256 equality. This proves only
  deterministic drafting, not review.

- [ ] **Step 5: Run contract, selector, inventory and static gates; commit the
  generator and reproducible draft aids.**

  ```powershell
  git commit -m "feat(r4): produce source readiness review worksheets"
  ```

- [ ] **Step 6: Stop for human review.**

  Present exact worksheet refs/hashes and the successor scenario/expanded-case
  counts. Do not interpret silence, a passing compiler or a prior general
  approval as approval of these bytes.

**Checkpoint SR5 — human decision required:** all structural, proposal,
realization, mutation, purpose and minima decisions are explicit, but Task 4
remains blocked and no reviewed source package exists.

## SR6: Record source-readiness approval and resume the parent plan

**Files (only after explicit human approval):**

- Add: `docs/superpowers/reviews/2026-08-30-r4-1-source-readiness-approval.md`
- Modify: `docs/superpowers/progress/2026-08-29-r4-1-data-supervision-replay-progress.md`
- Modify the existing tracker/governance test only if its approved-ref
  assertions require the new receipt; do not add a node

- [ ] **Step 1: Validate approval completeness.**

  Record reviewer refs, exact worksheet refs/hashes, corrected contract commit
  refs, successor scenario/expanded-case identities and counts, all eight
  structural-family decisions, conditional/restart decisions, and exact
  designation/output/mutation/purpose/minima decisions. Reject partial or
  conditional approval.

- [ ] **Step 2: Write a RED governance assertion for exact approval binding.**

  Require the approval doc to bind every SR1-SR5 commit and worksheet identity,
  and require the tracker checkpoint to reference that exact document without
  phase/admission/completion claims.

- [ ] **Step 3: Add the approval record and update operational tracking.**

  Mark `RC-SOURCE-READINESS` satisfied only. Keep T03 `in_progress`, T04
  `pending`, `RC-SOURCE` pending, the source directory absent and phase status
  solely in `governance/replay_status.jsonl`.

- [ ] **Step 4: Run focused governance, exact selectors, G0/R4 source-only
  inventory, compile/JSON/diff checks and commit.**

  ```powershell
  git commit -m "docs(r4): record source readiness approval"
  ```

- [ ] **Step 5: Stop before source check-in.**

  Return to main replay Task 4. That task, not this plan, checks in the exact
  approved `data/review/r4_1/` package, writes its manifest last, obtains the
  second data review and freezes the source-bundle ref.

**Checkpoint SR6:** Task 4 is eligible to resume; no R4 admission, source
publication, artifact publication or phase promotion has occurred.
