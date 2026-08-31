# R4.1 Supervision Authoring Automation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the bounded offline authoring path that produces independently reconstructed proposal, designation, realization and adversarial-mutation supervision for the approved R4.1 successor source universe without making Programs, runtime output, Python constants, external data or an LLM semantic authority.

**Architecture:** Repair the unpublished review ABIs at their current owners, add three small pure supervision compilers that do not call the runtime proposer/composer/realizer/executor, and add a worksheet-local recipe/evidence layer that expands into concrete existing ABI rows. Reuse the existing authenticated review-bundle loader, cross-source validator, transactional worksheet publisher and purpose contract; add no runtime import, validation tier, activation phase or pytest process.

**Tech Stack:** Python 3.11+, frozen dataclasses, canonical JSON/JSONL, JSON Schema Draft 2020-12, SHA-256 content identities, pytest, existing CEMM authority/form/grounding/Program/SemanticExpression/Response supervision ABIs.

## Execution status

| Task | Status | Evidence |
|---|---|---|
| 1-3 | complete | mutation ABI, review context and canonical designation authority committed |
| 4-6 | complete | independent derivation/realization/mutation compilers committed |
| 7 | complete | exact operation prerequisites source-owned and authority-linked |
| 8 | complete | optional bounded local evidence sidecar committed |
| 9 | complete | purpose-scoped worksheet-local recipes and explicit ancestry committed |
| 10A | complete | one-pass source/context cache and exact designation/recipe suggestions |
| 10B | guided review ready; awaiting accountable completed selection | neutral guided workflow and Advanced Explorer share the strict 1,056-target template/validator and deterministic export; purpose-scoped expansion remains disabled |
| 11-16 | pending | realization, mutation families, performance, publication and handoff |

Task 10 was split after an executable full-universe probe found that purpose
recipes cannot be authored from unresolved purpose options and that including
the final purpose child in its own review-context input would be circular.
The split adds no runtime ABI or release gate; it makes the already-required
human decision an explicit bounded input between two draft generations.

### Accountable review UI checkpoint

Launch the bounded offline reviewer from `hybrid_mvp` with:

```powershell
python scripts/serve_r4_1_review.py
```

Guided Review is the default presentation. It explains one source, proposal,
evidence set, neutral question, choice consequence and exact impact at a time;
it never recommends, preselects or automatically records a semantic choice.
Skip mutates nothing. Advanced Explorer remains available for search,
cross-checking and repair. Both views use the same accountable identity,
structural decisions, purpose assignments, purpose-local recipes,
exception/routine designation ownership, resumable canonical working state,
append-only audit journal and deterministic validated export. Python owns all
validation, action semantics and export reconstruction; HTML/JavaScript is
presentation only. The server is loopback-only, token- and origin-bound,
statically allowlisted, bounded, and absent from runtime imports. It adds no
activation phase, release gate, validation tier, pytest process, network
service or normal-cycle scan.

Executable coverage includes action/session unit tests, malformed and stale
state rejection, API authorization/origin/revision/body/static-path tests,
source-authentication/index single-pass counters, UI static/security checks,
mixed-mode cohort recovery, and complete Guided Review versus Advanced
Explorer HTTP replays whose independently validated exports must be
byte-identical. The supported in-app browser connection failed before page load
on 2026-08-30, so the manual real-browser layout/focus/resume smoke remains an
explicit handoff check; no automated result is claimed for it.

Task 10B Steps 4B and 6 remain unchecked until an accountable reviewer exports
a complete `artifacts/review_inputs/r4_1/SELECTION.json`, its export receipt
reports `authoring_ready: true`, and the ensuing proposal compilation passes. A
valid export containing rejection decisions records the review but does not
unblock expansion.

---

## 1. Relationship to the governing replay

This plan implements the approved
`docs/superpowers/specs/2026-08-30-r4-1-supervision-authoring-automation-design.md`.
It is a corrective prerequisite for the unsafe portions of Tasks 4-7 in
`docs/superpowers/plans/2026-08-29-r4-1-data-supervision-replay-plan.md`:

- reviewed source publication must wait for Tasks 1-12 here;
- main proposal, realization and mutation Tasks 5-7 reuse the pure compilers
  created here instead of adding private implementations;
- Task 4 creates and freezes the pure derivation compiler, but its mandatory
  cross-source validator integration occurs in Task 10 immediately after the
  real per-case FormLattice, GroundingResult and ProposalContext cache and
  reviewed blueprints exist; there is no optional compiler path, gold-derived
  context or placeholder-blueprint compatibility path;
- after Task 14 here, resume the main replay at reviewed purpose ownership and
  continue through artifact build, independent admission, R4 green and the R5
  handoff; and
- R5 remains red throughout this plan.

The current 388 supervised/20 diagnostic inventory and 1,932 active mutation
projection are audit observations. Implementations derive counts from the
authenticated successor source and never hard-code them.

## 2. File responsibility map

### Existing owners to modify

- `src/cemm_authoritative_hybrid/r4_supervision.py` — strict review ABIs,
  authenticated loader and the one cross-source validation owner.
- `schemas/r4_mutation_contract.schema.json` — repaired unpublished Mutation
  Contract ABI 1 wire shape.
- `schemas/r4_review_manifest.schema.json` — non-circular review-context inputs
  and identity binding.
- `src/cemm_authoritative_hybrid/authority.py` — canonical explicit
  designation-fact identity and bounded lookup.
- `src/cemm_authoritative_hybrid/grounding.py` — consume authority-owned
  designation facts instead of minting case-local fact identities.
- `src/cemm_authoritative_hybrid/r4_mutations.py` — instantiate reviewed
  mutation contracts; stop authoring expected truth through `_SPECS`.
- `src/cemm_authoritative_hybrid/r4_environment.py` — execute a mutation
  without receiving its expected observation labels.
- `scripts/generate_scenarios.py` — source-own adapter and permission
  prerequisites for every `request_effect` case.
- `scripts/build_r4_1_review_worksheets.py` — orchestrate bounded candidate
  authoring and emit non-authoritative recipes/exceptions.
- `docs/ABI_REGISTRY.md`, `docs/ARCHITECTURE.md` and the R4 progress tracker —
  record exact implemented/pending ownership without claiming admission.

### Focused modules to create

- `src/cemm_authoritative_hybrid/r4_review_context.py` — one non-circular
  `source_review` identity factory.
- `src/cemm_authoritative_hybrid/r4_derivation_compiler.py` — independently
  reconstruct a Program and exact SemanticExpression from one reviewed
  blueprint and immutable ProposalContext.
- `src/cemm_authoritative_hybrid/r4_realization_compiler.py` — independently
  reconstruct the complete response signature and alignment coverage.
- `src/cemm_authoritative_hybrid/r4_mutation_compiler.py` — compile reviewed
  mutation operations into mutated case bytes without importing generator
  `_SPECS` or execution results.
- `src/cemm_authoritative_hybrid/r4_authoring.py` — bounded purpose-scoped
  recipe/candidate/exception records and deterministic expansion indexes.
- `src/cemm_authoritative_hybrid/r4_authoring_evidence.py` — authenticated local
  evidence snapshot and license/use-policy normalization; no CEMM authority.
- `scripts/fetch_r4_authoring_evidence.py` — optional HTTPS snapshot fetcher,
  absent from build/admission/runtime paths.

### Focused tests to create

- `tests/test_r4_review_context.py`
- `tests/test_r4_supervision_compilers.py`
- `tests/test_r4_authoring.py`
- `tests/test_r4_authoring_evidence.py`
- `tests/test_r4_authoring_pipeline.py`
- `tests/test_r4_1_authoring_performance.py`

Existing owner tests remain in their current pytest processes.

## Task 1: Repair Mutation Contract ABI 1 before authoring data

**Files:**

- Modify: `src/cemm_authoritative_hybrid/r4_supervision.py:177-179`
- Modify: `src/cemm_authoritative_hybrid/r4_supervision.py:3079-3133`
- Modify: `schemas/r4_mutation_contract.schema.json`
- Modify: `tests/test_r4_supervision_contracts.py:299-311`
- Modify: `tests/test_r4_supervision_contracts.py:650-675`

- [ ] **Step 1: Write failing exact-wire and corruption tests**

Add a helper whose contract contains the complete operation and expected
observation, then corrupt each nested field independently:

```python
def _mutation_contract() -> MutationContract:
    return MutationContract.create(
        mutation_family_ref="mutation_family:invalid_role",
        source_case_ref="expanded_case_v2:0123456789abcdef01234567",
        scope="contract",
        changed_dimension_ref="mutation_dimension:invalid_role",
        selector_kind="json_path",
        changed_path=(
            "contract", "expected_expressions", 0, "applications", 0,
            "roles", 0, "role_ref",
        ),
        operation="replace",
        expected_before="role:actor",
        replacement_after="not-a-role",
        applicability_ref="mutation_applicability:semantic_expression",
        expected_earliest_owner="expected-contract-compiler",
        expected_status="rejected",
        expected_error_code="invalid_role_ref",
        disposition="reject",
        effect_kind="no_effect",
        expected_effect_ref=None,
        review_refs=(REVIEW_REF,),
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("scope", "runtime"),
        ("selector_kind", "regex"),
        ("operation", "execute"),
        ("expected_earliest_owner", "propose"),
        ("expected_status", "accept"),
        ("expected_error_code", ""),
    ],
)
def test_mutation_contract_rejects_non_governed_truth(field, value):
    row = _mutation_contract().as_dict()
    row[field] = value
    with pytest.raises((TypeError, ValueError)):
        MutationContract.from_dict(row)
```

- [ ] **Step 2: Run the tests and verify the old ABI fails**

Run:

```powershell
python -m pytest tests/test_r4_supervision_contracts.py -k mutation -q
```

Expected: failure because `MutationContract.create` lacks operation/status/error
fields and still restricts owners to runtime phases.

- [ ] **Step 3: Implement the repaired unpublished ABI in place**

Keep ABI version `1`. Replace the old field set with one closed contract. Use
an exact path component union of `str | int`, require `json_path` and `replace`
for the initial families, and separate observed status from disposition:

```python
_MUTATION_SCOPES = frozenset({"contract", "environment", "persistence"})
_MUTATION_OWNERS = frozenset(
    {"expected-contract-compiler", "semantic-expression", "EVALUATE", "EFFECT"}
)
_MUTATION_STATUSES = frozenset(
    {"rejected", "denied", "adapter_missing", "contested", "stale_revision"}
)
_MUTATION_DISPOSITIONS = frozenset({"reject", "deny", "contest", "stale"})
_MUTATION_ERROR_CODES = frozenset(
    {
        "invalid_role_ref", "authority_ref_missing", "unknown_root_ref",
        "permission_missing", "adapter_missing", "untrusted_observation",
        "stale_revision", "decision_contract_mismatch",
    }
)
_STATUS_DISPOSITION = {
    "rejected": "reject",
    "denied": "deny",
    "adapter_missing": "deny",
    "contested": "contest",
    "stale_revision": "stale",
}


def _mutation_path(value: object) -> tuple[str | int, ...]:
    if type(value) is not tuple or not 1 <= len(value) <= 16:
        raise TypeError("changed_path must be one bounded exact tuple")
    if any(type(item) not in {str, int} for item in value):
        raise TypeError("changed_path components must be exact strings or integers")
    if any(type(item) is str and (not item or len(item) > 128) for item in value):
        raise ValueError("changed_path string component is invalid")
    if any(type(item) is int and not 0 <= item <= 4096 for item in value):
        raise ValueError("changed_path index component is invalid")
    return value
```

`MutationContract.create` must freeze `expected_before` and
`replacement_after`, include every new field in identity material, require an
effect ref exactly for `effect`, and round-trip through `from_dict` byte
canonically. It requires `disposition == _STATUS_DISPOSITION[expected_status]`
and an error code in `_MUTATION_ERROR_CODES`. Do not accept aliases for old
rows.

- [ ] **Step 4: Update Draft 2020-12 schema parity**

Make the schema require exactly:

```json
[
  "abi_version", "mutation_contract_ref", "mutation_family_ref",
  "source_case_ref", "scope", "changed_dimension_ref", "selector_kind",
  "changed_path", "operation", "expected_before", "replacement_after",
  "applicability_ref", "expected_earliest_owner", "expected_status",
  "expected_error_code", "disposition", "effect_kind",
  "expected_effect_ref", "review_refs"
]
```

Set `selector_kind` to `json_path`, `operation` to `replace`, bound the path to
16 components, and use the same closed owner/status/disposition enums as the
decoder.

- [ ] **Step 5: Run ABI/schema parity tests**

Run:

```powershell
python -m pytest tests/test_r4_supervision_contracts.py -k "mutation or schema" -q
```

Expected: pass, including canonical round-trip and every corruption case.

- [ ] **Step 6: Commit**

```powershell
git add src/cemm_authoritative_hybrid/r4_supervision.py schemas/r4_mutation_contract.schema.json tests/test_r4_supervision_contracts.py
git commit -m "fix(r4): repair mutation contract abi1"
```

## Task 2: Define and authenticate the non-circular review context

**Files:**

- Create: `src/cemm_authoritative_hybrid/r4_review_context.py`
- Modify: `src/cemm_authoritative_hybrid/r4_supervision.py:552-639`
- Modify: `src/cemm_authoritative_hybrid/r4_supervision.py:713-799`
- Modify: `schemas/r4_review_manifest.schema.json`
- Create: `tests/test_r4_review_context.py`
- Modify: `tests/test_r4_supervision_contracts.py:312-380`

- [ ] **Step 1: Write failing identity and cycle tests**

```python
def _material() -> ReviewContextMaterial:
    return ReviewContextMaterial.create(
        review_policy_ref="review_policy:r4_1_single_accountable_reviewer",
        review_policy_sha256="11" * 32,
        reviewer_refs=("reviewer:son",),
        reviewed_base_revision="22" * 20,
        authority_generation="authority-v1-2026-07-29",
        form_abi_version=7,
        form_pack_sha256="33" * 32,
        input_set_ref="worksheet_input_set:0123456789abcdef01234567",
    )


def test_review_context_excludes_output_identities():
    row = _material().as_dict()
    assert set(row) == {
        "review_scope", "review_policy_ref", "review_policy_sha256",
        "reviewer_refs", "reviewed_base_revision", "authority_generation",
        "form_abi_version", "form_pack_sha256", "input_set_ref",
        "review_context_ref",
    }
    forbidden = {"worksheet_ref", "row_ref", "manifest_ref", "source_bundle_ref"}
    assert forbidden.isdisjoint(row)


def test_manifest_rejects_child_review_ref_not_equal_to_context(bundle_factory):
    bundle = bundle_factory(child_review_ref="source_review:" + "ff" * 12)
    with pytest.raises(ValueError, match="review context"):
        load_authenticated_r4_review_bundle(bundle.root)
```

- [ ] **Step 2: Run tests and verify failure**

```powershell
python -m pytest tests/test_r4_review_context.py tests/test_r4_supervision_contracts.py -k "review_context or manifest" -q
```

Expected: failure because no review-context owner exists and the manifest
cannot recompute child review refs.

- [ ] **Step 3: Implement the exact review-context factory**

```python
REVIEW_SCOPE = "r4_1_supervision_authoring"


@dataclass(frozen=True)
class ReviewContextMaterial:
    review_context_ref: str
    review_scope: str
    review_policy_ref: str
    review_policy_sha256: str
    reviewer_refs: tuple[str, ...]
    reviewed_base_revision: str
    authority_generation: str
    form_abi_version: int
    form_pack_sha256: str
    input_set_ref: str

    @classmethod
    def create(cls, **raw: object) -> "ReviewContextMaterial":
        material = {
            "review_scope": REVIEW_SCOPE,
            "review_policy_ref": exact_ref(raw["review_policy_ref"], "review_policy_ref", prefix="review_policy:"),
            "review_policy_sha256": exact_sha256(raw["review_policy_sha256"], "review_policy_sha256"),
            "reviewer_refs": list(exact_reviewer_refs(raw["reviewer_refs"])),
            "reviewed_base_revision": exact_revision(raw["reviewed_base_revision"], "reviewed_base_revision"),
            "authority_generation": exact_text(raw["authority_generation"], "authority_generation"),
            "form_abi_version": exact_int(raw["form_abi_version"], "form_abi_version", minimum=7, maximum=7),
            "form_pack_sha256": exact_sha256(raw["form_pack_sha256"], "form_pack_sha256"),
            "input_set_ref": exact_content_ref(raw["input_set_ref"], "input_set_ref", prefix="worksheet_input_set:"),
        }
        return construct(
            cls,
            review_context_ref=stable_ref("source_review", material),
            reviewer_refs=tuple(material["reviewer_refs"]),
            **{key: value for key, value in material.items() if key != "reviewer_refs"},
        )
```

Use the repository's existing exact validation helpers rather than defining
duplicates if their names differ. `as_dict` and `from_dict` must reconstruct
the identity exactly.

- [ ] **Step 4: Bind the material through Manifest ABI 1**

Add these required manifest fields without changing ABI version:

```text
review_context_ref
review_policy_sha256
form_abi_version
form_pack_sha256
input_set_ref
```

`R4ReviewManifest.create` reconstructs `ReviewContextMaterial` from its own
fields plus existing review policy, reviewers, base revision and authority
generation. The authenticated loader requires every `ReviewSourceFile` and
every proposal/realization/mutation/purpose child record to have exactly
`(manifest.review_context_ref,)` as its authoring `review_refs`.

- [ ] **Step 5: Run loader, schema and cycle tests**

```powershell
python -m pytest tests/test_r4_review_context.py tests/test_r4_supervision_contracts.py -k "review_context or manifest or authenticated" -q
```

Expected: pass; modifying any context input changes the ref, while modifying a
bundle/manifest/row ref cannot be an input to the factory.

- [ ] **Step 6: Commit**

```powershell
git add src/cemm_authoritative_hybrid/r4_review_context.py src/cemm_authoritative_hybrid/r4_supervision.py schemas/r4_review_manifest.schema.json tests/test_r4_review_context.py tests/test_r4_supervision_contracts.py
git commit -m "feat(r4): authenticate review context"
```

## Task 3: Make designation facts canonical authority identities

**Files:**

- Modify: `src/cemm_authoritative_hybrid/authority.py:145-212`
- Modify: `src/cemm_authoritative_hybrid/authority.py:571-583`
- Modify: `src/cemm_authoritative_hybrid/grounding.py:605-640`
- Modify: `tests/test_authority_linker.py`
- Modify: `tests/test_grounding.py`
- Modify: `tests/test_r4_supervision_contracts.py:950-980`

- [ ] **Step 1: Write failing identity, polysemy and forged-ref tests**

```python
def test_linked_designation_fact_is_case_independent(linked_authority, grounder_factory):
    fact = linked_authority.designations.facts_for_surface("alice", "en")[0]
    left = grounder_factory(linked_authority).ground_text("alice")
    right = grounder_factory(linked_authority).ground_text("alice likes bob")
    assert left.designations[0].designation_fact_ref == fact.designation_fact_ref
    assert right.designations[0].designation_fact_ref == fact.designation_fact_ref


def test_realization_rejects_forged_designation_fact(
    authenticated_bundle_factory, linked_authority
):
    bundle = authenticated_bundle_factory(
        designation_fact_ref="designation:" + "ff" * 12
    )
    with pytest.raises(ValueError, match="designation fact"):
        validate_authenticated_r4_source_semantics(bundle, authority=linked_authority)
```

Add a same-surface/two-target fixture and assert both facts survive in stable
target/ref order.

- [ ] **Step 2: Run tests and verify case-local minting fails**

```powershell
python -m pytest tests/test_authority_linker.py tests/test_grounding.py tests/test_r4_supervision_contracts.py -k designation -q
```

Expected: failure because `DesignationIndex` drops record identity and
`Grounder` hashes unit refs into the fact ref.

- [ ] **Step 3: Add the authority-owned fact value and indexes**

```python
@dataclass(frozen=True)
class DesignationFact:
    designation_fact_ref: str
    surface: str
    target_ref: str
    language: str

    @classmethod
    def create(cls, *, surface: str, target_ref: str, language: str) -> "DesignationFact":
        material = {
            "surface": surface,
            "target_ref": target_ref,
            "language": language,
        }
        return cls(
            designation_fact_ref=stable_ref("designation", material),
            surface=surface,
            target_ref=target_ref,
            language=language,
        )
```

Change `DesignationIndex` to index exact `DesignationFact` values and expose:

```python
def facts_for_surface(
    self, surface: str, language: str
) -> tuple[DesignationFact, ...]:
    exact = self._facts_by_surface.get((surface, language), ())
    if exact:
        return exact
    return self._facts_by_folded_surface.get((surface.casefold(), language), ())


def facts_for_target(
    self, target_ref: str, language: str
) -> tuple[DesignationFact, ...]:
    return self._facts_by_target.get((target_ref, language), ())


def resolve_fact(self, designation_fact_ref: str) -> DesignationFact | None:
    return self._facts_by_ref.get(designation_fact_ref)
```

The legacy target/surface query methods become projections of these indexes.
Authority linking rejects duplicate fact identities and preserves folded
surface alternatives without changing fact identity.

- [ ] **Step 4: Make grounding consume the linked fact**

Replace the `stable_ref` call over `unit_refs` with the exact returned
`DesignationFact`. Unit refs stay in `DesignationCandidate.unit_refs`; they no
longer affect `designation_fact_ref`.

- [ ] **Step 5: Resolve realization alignments through authority**

In `validate_authenticated_r4_source_semantics`, for each
`DesignationAlignment`, require `authority.designations.resolve_fact(ref)` and
verify the exact output slice, row language and slot semantic ref match the
fact. Do not add this semantic lookup to `RealizationRow.create`, which remains
a row-local decoder.

- [ ] **Step 6: Run authority, grounding and R4 tests**

```powershell
python -m pytest tests/test_authority_linker.py tests/test_grounding.py tests/test_r4_supervision_contracts.py -k designation -q
```

Expected: pass, including overlap, case-independent identity and forged-ref
rejection.

- [ ] **Step 7: Commit**

```powershell
git add src/cemm_authoritative_hybrid/authority.py src/cemm_authoritative_hybrid/grounding.py tests/test_authority_linker.py tests/test_grounding.py tests/test_r4_supervision_contracts.py
git commit -m "feat(authority): retain canonical designation facts"
```

## Task 4: Implement the independent reviewed derivation compiler

**Files:**

- Create: `src/cemm_authoritative_hybrid/r4_derivation_compiler.py`
- Create: `tests/test_r4_supervision_compilers.py`

- [ ] **Step 1: Write failing exact reconstruction tests**

```python
def test_derivation_compiler_reconstructs_source_expression(
    semantic_case, proposal_context, derivation_blueprint
):
    result = ReviewedDerivationCompiler().compile(
        case=semantic_case,
        context=proposal_context,
        blueprint=derivation_blueprint,
    )
    assert result.expression == semantic_case.contract.expected_expressions[0]
    assert result.expression.expression_ref == derivation_blueprint.expected_expression_ref
    assert result.program.program_ref != result.expression.expression_ref
    assert result.assigned_source_unit_refs == proposal_context.source_unit_refs


@pytest.mark.parametrize(
    "corruption",
    ["wrong_expression_ref", "wrong_span", "missing_assignment", "duplicate_assignment"],
)
def test_derivation_compiler_fails_closed(corruption, derivation_fixture):
    case, context, blueprint = derivation_fixture.corrupt(corruption)
    with pytest.raises(DerivationCompilationError):
        ReviewedDerivationCompiler().compile(
            case=case, context=context, blueprint=blueprint
        )
```

Monkeypatch `recursive_compiler.compile_recursive`, the proposer and recursive
composer to raise, and assert the reviewed compiler still succeeds.

- [ ] **Step 2: Run tests and verify the compiler is absent**

```powershell
python -m pytest tests/test_r4_supervision_compilers.py -k derivation -q
```

Expected: import/attribute failure for `ReviewedDerivationCompiler`.

- [ ] **Step 3: Implement a pure compiler with one immutable context pass**

Expose this exact public surface:

```python
@dataclass(frozen=True)
class CompiledReviewedDerivation:
    program: SemanticSwitchProgram
    expression: SemanticExpression
    assigned_source_unit_refs: tuple[str, ...]
    residual_source_unit_refs: tuple[str, ...]
    operation_count: int


class DerivationCompilationError(ValueError):
    pass


class ReviewedDerivationCompiler:
    def compile(
        self,
        *,
        case: ExpandedCase,
        context: ProposalContext,
        blueprint: DerivationBlueprint,
    ) -> CompiledReviewedDerivation:
        if type(case) is not ExpandedCase or type(context) is not ProposalContext:
            raise TypeError("reviewed derivation requires exact case and context")
        if type(blueprint) is not DerivationBlueprint:
            raise TypeError("blueprint must be exact DerivationBlueprint")
        if context.revision_pin != case.contract.revision_pin:
            raise DerivationCompilationError("case and context revisions differ")
        selectors = {row.selector_handle: row for row in blueprint.selector_bindings}
        action_sources = {
            index: tuple(
                row.source_unit_ref
                for row in blueprint.source_assignment_blueprint.assignments
                if row.target_action_index == index
            )
            for index in range(len(blueprint.actions))
        }
        actions = tuple(
            ProgramAction.create(
                action_index=row.action_index,
                action_type=row.action_type,
                arguments=tuple(selectors[handle].value_ref for handle in row.selector_handles),
                source_unit_refs=action_sources[row.action_index],
            )
            for row in blueprint.actions
        )
        assignment_rows = tuple(
            SourceAssignment.create(
                source_unit_ref=row.source_unit_ref,
                contribution_slot_ref=row.contribution_slot_ref,
                assignment_kind=row.assignment_kind,
                target_action_ref=(
                    None
                    if row.target_action_index is None
                    else actions[row.target_action_index].action_ref
                ),
                target_role_ref=row.target_role_ref,
                residual_kind=row.residual_kind,
                critical=row.critical,
            )
            for row in blueprint.source_assignment_blueprint.assignments
        )
        mode_action = next(row for row in actions if row.action_type == "select_mode")
        program = SemanticSwitchProgram.create(
            orientation_ref=context.orientation_ref,
            proposal_context_ref=context.context_ref,
            actions=actions,
            root_refs=blueprint.root_local_refs,
            mode_slot_ref=mode_action.arguments[0],
            goal_refs=(),
            source_unit_refs=blueprint.source_assignment_blueprint.observed_source_unit_refs,
            source_assignments=assignment_rows,
            revision_pin=context.revision_pin,
        )
        expression = reconstruct_expected_expression(program, context)
        if expression is None or expression.expression_ref != blueprint.expected_expression_ref:
            raise DerivationCompilationError("blueprint does not reconstruct expected expression")
        expected = {row.expression_ref: row for row in case.contract.expected_expressions}
        if expected.get(expression.expression_ref) != expression:
            raise DerivationCompilationError("compiled expression differs from source truth")
        residuals = tuple(
            row.source_unit_ref for row in assignment_rows
            if row.assignment_kind == "residual"
        )
        return CompiledReviewedDerivation(
            program=program,
            expression=expression,
            assigned_source_unit_refs=tuple(row.source_unit_ref for row in assignment_rows),
            residual_source_unit_refs=residuals,
            operation_count=len(selectors) + len(actions) + len(assignment_rows),
        )
```

Implement `compile` without importing `recursive_compiler`, `proposal`,
`recursive_composer`, `verifier` or runtime owners. The shown implementation
uses the already-independent
`verifier_reconstruction.reconstruct_expected_expression`, which must remain
source-independent from `recursive_compiler.compile_recursive`. Before action
construction, validate every grounded selector against exact
FormLattice/Grounding/ProposalContext refs and spans. Build assignment indexes
once and require every observed unit exactly once.

- [ ] **Step 4: Freeze the integration dependency without adding a fallback**

Do not wire the compiler into cross-source validation while the authenticated
source still contains placeholder `_sr2_blueprint` records and has no real
per-case FormLattice, GroundingResult or ProposalContext cache. That wiring is
mandatory in Task 10 immediately after those exact contexts and reviewed
blueprints are authored. Until then, do not derive contexts from expected gold,
add an optional compiler callback, accept placeholder blueprints or weaken the
existing validator. The pure compiler remains an independently tested,
explicitly unintegrated foundation rather than a permissive partial path.

- [ ] **Step 5: Run compiler tests**

```powershell
python -m pytest tests/test_r4_supervision_compilers.py -k derivation -q
```

Expected: pass; monkeypatched runtime compilation is never reached.

- [ ] **Step 6: Commit**

```powershell
git add src/cemm_authoritative_hybrid/r4_derivation_compiler.py tests/test_r4_supervision_compilers.py
git commit -m "feat(r4): compile reviewed derivations independently"
```

## Task 5: Implement the independent reviewed realization compiler

**Files:**

- Create: `src/cemm_authoritative_hybrid/r4_realization_compiler.py`
- Modify: `tests/test_r4_supervision_compilers.py`
- Modify: `src/cemm_authoritative_hybrid/r4_supervision.py:1043-1169`

- [ ] **Step 1: Write failing response-equivalence tests**

```python
def test_realization_compiler_reconstructs_complete_signature(
    semantic_case, proposal_target, linked_authority, realization_row
):
    result = ReviewedRealizationCompiler(linked_authority).compile(
        case=semantic_case,
        proposal=proposal_target,
        row=realization_row,
    )
    assert result.response_signature_ref == realization_row.response_signature_ref
    assert result.covered_slot_refs == tuple(
        slot.slot_ref for slot in realization_row.semantic_slots
    )
    assert result.authorized_surface == realization_row.authorized_surface


@pytest.mark.parametrize(
    "corruption",
    [
        "subject", "binding", "qualifier", "action", "polarity", "modality",
        "epistemic", "speaker", "addressee", "designation_span",
        "reference_span", "literal_source", "missing_slot", "double_slot",
        "unreviewed_omission",
    ],
)
def test_realization_compiler_rejects_semantic_drift(corruption, realization_fixture):
    case, proposal, authority, row = realization_fixture.corrupt(corruption)
    with pytest.raises(RealizationCompilationError):
        ReviewedRealizationCompiler(authority).compile(
            case=case, proposal=proposal, row=row
        )
```

Add explicit safe-gap/rejection tests proving the output is nonempty, is not
the input surface, and has one full-surface independently reviewed literal.
Monkeypatch the runtime realizer and realization verifier to raise.

- [ ] **Step 2: Run tests and verify failure**

```powershell
python -m pytest tests/test_r4_supervision_compilers.py -k realization -q
```

Expected: missing compiler failure.

- [ ] **Step 3: Implement independent signature reconstruction**

```python
@dataclass(frozen=True)
class CompiledReviewedRealization:
    response_signature_ref: str
    authorized_surface: str
    covered_slot_refs: tuple[str, ...]
    omitted_slot_refs: tuple[str, ...]
    operation_count: int


class RealizationCompilationError(ValueError):
    pass


class ReviewedRealizationCompiler:
    def __init__(self, authority: LinkedAuthority) -> None:
        if type(authority) is not LinkedAuthority:
            raise TypeError("authority must be exact LinkedAuthority")
        self._authority = authority

    def compile(
        self, *, case: ExpandedCase, proposal: ProposalTarget, row: RealizationRow
    ) -> CompiledReviewedRealization:
        if (
            type(case) is not ExpandedCase
            or type(proposal) is not ProposalTarget
            or type(row) is not RealizationRow
        ):
            raise TypeError("reviewed realization requires exact case, proposal and row")
        if proposal.source_case_ref != case.case_ref:
            raise RealizationCompilationError("proposal belongs to another source case")
        if row.source_case_ref != case.case_ref or row.language != case.language:
            raise RealizationCompilationError("realization belongs to another source case")
        expected_subject = response_subject_from_proposal(proposal)
        if row.response_subject != expected_subject:
            raise RealizationCompilationError("response subject differs from proposal truth")
        response = case.contract.expected_response
        expected_contract = (
            f"response_action:{response.discourse_action}",
            response.polarity_ref,
            response.modality_ref,
            response.epistemic_status_ref,
        )
        actual_contract = (
            row.discourse_action_ref,
            row.polarity_ref,
            row.modality_ref,
            row.epistemic_status_ref,
        )
        if actual_contract != expected_contract:
            raise RealizationCompilationError("response contract drift")
        slots = {slot.slot_ref: slot for slot in row.semantic_slots}
        covered: dict[str, int] = {slot_ref: 0 for slot_ref in slots}
        omitted: list[str] = []
        for alignment in row.alignments:
            slot = slots.get(alignment.slot_ref)
            if slot is None:
                raise RealizationCompilationError("alignment targets unknown slot")
            covered[alignment.slot_ref] += 1
            if isinstance(alignment, OmissionAlignment):
                omitted.append(alignment.slot_ref)
                continue
            surface = row.authorized_surface[alignment.surface_start:alignment.surface_end]
            if isinstance(alignment, DesignationAlignment):
                fact = self._authority.designations.resolve_fact(
                    alignment.designation_fact_ref
                )
                if fact is None or fact.surface != surface or fact.language != row.language:
                    raise RealizationCompilationError("designation alignment drift")
                if fact.target_ref != slot.semantic_ref:
                    raise RealizationCompilationError("designation target differs from slot")
        if any(
            count != 1 if slots[slot_ref].required else count > 1
            for slot_ref, count in covered.items()
        ):
            raise RealizationCompilationError("semantic slot coverage drift")
        material = reconstruct_response_signature_material(
            case=case, proposal=proposal, row=row
        )
        signature_ref = stable_ref("response_signature", material)
        if signature_ref != row.response_signature_ref:
            raise RealizationCompilationError("response signature does not reconstruct")
        return CompiledReviewedRealization(
            response_signature_ref=signature_ref,
            authorized_surface=row.authorized_surface,
            covered_slot_refs=tuple(sorted(ref for ref, count in covered.items() if count)),
            omitted_slot_refs=tuple(sorted(omitted)),
            operation_count=len(slots) + len(row.alignments),
        )
```

Implement the response subject directly from the proposal's derive, abstain or
verifier-rejection payload:

```python
def response_subject_from_proposal(proposal: ProposalTarget) -> ResponseSubject:
    if proposal.target_kind == "derive":
        return ExpressionSetResponseSubject.create(
            expected_expression_relation=proposal.expected_expression_relation,
            expression_refs=proposal.expected_expression_refs,
        )
    if proposal.target_kind == "abstain" and proposal.abstention is not None:
        return TypedGapResponseSubject.create(typed_gap=proposal.abstention)
    if (
        proposal.target_kind == "verification_rejection"
        and proposal.verification_rejection is not None
    ):
        return VerifierRejectionResponseSubject.create(
            verifier_rejection=proposal.verification_rejection
        )
    raise RealizationCompilationError("proposal has no closed response subject")
```

Implement signature material exactly as follows:

```python
def reconstruct_response_signature_material(
    *, case: ExpandedCase, proposal: ProposalTarget, row: RealizationRow
) -> dict[str, object]:
    subject = response_subject_from_proposal(proposal)
    if subject != row.response_subject or row.source_case_ref != case.case_ref:
        raise RealizationCompilationError("response subject ownership drift")
    return {
        "response_subject": subject.as_dict(),
        "bindings": [item.as_dict() for item in row.bindings],
        "discourse_action_ref": row.discourse_action_ref,
        "polarity_ref": row.polarity_ref,
        "modality_ref": row.modality_ref,
        "epistemic_status_ref": row.epistemic_status_ref,
        "output_speaker_ref": row.output_speaker_ref,
        "output_addressee_ref": row.output_addressee_ref,
        "semantic_slots": [item.as_dict() for item in row.semantic_slots],
    }
```

Validate every output slice; resolve participant refs and row-local review
authorities; authenticate literal sources; and require every required slot
once. Do not call `RealizationRow.create` to reconstruct the signature and do
not import runtime realization code.

- [ ] **Step 4: Integrate compilation into the existing validator**

For every initial `RealizationRow`, invoke the compiler after the existing
case/response-contract join. Require reconstructed signature equality and add
its operation count. Retain the four-variant bound for later bundles.

- [ ] **Step 5: Run focused tests**

```powershell
python -m pytest tests/test_r4_supervision_compilers.py tests/test_r4_supervision_contracts.py -k "realization or cross_source" -q
```

Expected: pass with all drift and runtime-call canaries rejected.

- [ ] **Step 6: Commit**

```powershell
git add src/cemm_authoritative_hybrid/r4_realization_compiler.py src/cemm_authoritative_hybrid/r4_supervision.py tests/test_r4_supervision_compilers.py tests/test_r4_supervision_contracts.py
git commit -m "feat(r4): verify reviewed realizations independently"
```

## Task 6: Compile reviewed mutations and remove `_SPECS` truth

**Files:**

- Create: `src/cemm_authoritative_hybrid/r4_mutation_compiler.py`
- Modify: `src/cemm_authoritative_hybrid/r4_mutations.py:326-441`
- Modify: `src/cemm_authoritative_hybrid/r4_environment.py:124-297`
- Modify: `src/cemm_authoritative_hybrid/r4_pipeline.py:318-385`
- Modify: `scripts/build_r4_artifacts.py:40-140`
- Modify: `tests/test_r4_mutations_and_partitions.py`
- Modify: `tests/test_r4_environment.py`
- Modify: `tests/test_r4_supervision_compilers.py`

- [ ] **Step 1: Write failing no-oracle and applicability tests**

```python
def test_generator_requires_reviewed_contracts(expanded_case):
    with pytest.raises(TypeError, match="reviewed mutation contracts"):
        MutationGenerator().generate(expanded_case)


def test_mutation_compiler_reconstructs_exact_changed_path(
    expanded_case, mutation_contract
):
    mutation = ReviewedMutationCompiler().compile(
        case=expanded_case,
        contract=mutation_contract,
    )
    assert mutation.expected_earliest_owner == mutation_contract.expected_earliest_owner
    assert mutation.expected_status == mutation_contract.expected_status
    assert mutation.expected_error_code == mutation_contract.expected_error_code
    assert mutation.before == mutation_contract.expected_before
    assert mutation.after == mutation_contract.replacement_after


def test_executor_never_receives_expected_labels(mutation, spying_owner):
    MutationExecutor(spying_owner).execute((mutation,))
    payload = spying_owner.received[0].as_dict()
    assert "expected_status" not in payload["mutated_case"]
    assert "expected_error_code" not in payload["mutated_case"]
```

Add missing/extra/duplicate/inapplicable family tests over a small semantic and
gap case set.

- [ ] **Step 2: Run tests and verify `_SPECS` remains authoritative**

```powershell
python -m pytest tests/test_r4_mutations_and_partitions.py tests/test_r4_environment.py tests/test_r4_supervision_compilers.py -k mutation -q
```

Expected: failures because `MutationGenerator` currently needs no contracts and
authors truth from `_SPECS`.

- [ ] **Step 3: Implement the pure mutation compiler**

```python
class MutationCompilationError(ValueError):
    pass


class ReviewedMutationCompiler:
    def compile(
        self, *, case: ExpandedCase, contract: MutationContract
    ) -> SemanticMutation:
        if contract.source_case_ref != case.case_ref:
            raise MutationCompilationError("mutation contract belongs to another case")
        payload = copy.deepcopy(case.as_dict())
        before = resolve_exact_json_path(payload, contract.changed_path)
        if freeze_json(before) != contract.expected_before:
            raise MutationCompilationError("reviewed mutation before-value drift")
        replace_exact_json_path(
            payload, contract.changed_path, thaw_json(contract.replacement_after)
        )
        return SemanticMutation.create(
            parent_case_ref=case.case_ref,
            parent_contract_ref=case.contract.contract_ref,
            scope=contract.scope,
            dimension=contract.changed_dimension_ref.removeprefix("mutation_dimension:"),
            changed_path=render_json_path(contract.changed_path),
            before=before,
            after=thaw_json(contract.replacement_after),
            mutated_case=payload,
            expected_earliest_owner=contract.expected_earliest_owner,
            expected_status=contract.expected_status,
            expected_error_code=contract.expected_error_code,
            lineage_refs=(case.case_ref, case.contract.contract_ref, contract.mutation_family_ref),
            review_refs=contract.review_refs,
        )
```

Implement bounded path resolution locally. It may import canonical JSON freeze,
wire types and hashes; it may not import `MutationGenerator`, `_SPECS`, the
environment owner or observations.

- [ ] **Step 4: Replace generator specs with reviewed contracts**

Give `MutationGenerator` an exact tuple of `MutationContract` records and a
`ReviewedMutationCompiler`. Index contracts by case once, enforce at most eight
per case, and return the compiled mutations in `(family_ref, contract_ref)`
order. Delete `_MutationSpec`, `_SPECS` and `_apply` after all callers migrate.

Make `R4Pipeline` require this exact reviewed contract tuple. The artifact
builder must obtain it from one authenticated review-bundle load and run the
existing cross-source validator before constructing the pipeline. Until Task
14 publishes that bundle, artifact building is explicitly unavailable; do not
retain `_SPECS`, synthesize contracts, or use old artifacts as a fallback.

- [ ] **Step 5: Remove expected labels from the execution boundary**

Keep expected labels in the immutable `SemanticMutation` wrapper for
post-execution comparison, but create a content-addressed
`MutationExecutionRequest` exclusively from `mutated_case`, scope, dimension
and changed path. Pass only that request to the authentic owner. The owner may
not receive or branch on `expected_earliest_owner`, `expected_status` or
`expected_error_code`. `MutationObservation.create` compares the independent
result with the retained wrapper only after execution.

- [ ] **Step 6: Run mutation tests and forbidden-pattern scan**

```powershell
python -m pytest tests/test_r4_mutations_and_partitions.py tests/test_r4_environment.py tests/test_r4_supervision_compilers.py -k mutation -q
rg -n "_SPECS|_MutationSpec" src/cemm_authoritative_hybrid/r4_mutations.py
```

Expected: tests pass and `rg` returns no matches.

- [ ] **Step 7: Commit**

```powershell
git add src/cemm_authoritative_hybrid/r4_mutation_compiler.py src/cemm_authoritative_hybrid/r4_mutations.py src/cemm_authoritative_hybrid/r4_environment.py src/cemm_authoritative_hybrid/r4_pipeline.py scripts/build_r4_artifacts.py tests/test_r4_mutations_and_partitions.py tests/test_r4_environment.py tests/test_r4_supervision_compilers.py
git commit -m "feat(r4): compile reviewed mutation truth"
```

## Task 7: Source-own R5 operation prerequisites

**Files:**

- Modify: `scripts/generate_scenarios.py`
- Regenerate: `data/scenarios/use_cases.jsonl`
- Modify: `tests/test_r4_expansion.py`
- Modify: `tests/test_r4_assertion_compiler.py`
- Modify: `tests/test_r4_mutations_and_partitions.py`

- [ ] **Step 1: Write failing source-ownership tests**

```python
def test_every_request_effect_case_owns_adapter_and_permission(reviewed_universe):
    cases = [
        case for case in reviewed_universe.cases
        if case.contract.expected_decision.action == "request_effect"
    ]
    assert cases
    for case in cases:
        constraints = case.contract.situation_constraints
        assert constraints["adapter_refs"] == ("adapter:state",)
        assert constraints["permission_refs"] == ("permission:set_state",)


def test_operation_removal_families_are_source_applicable(
    reviewed_universe, reviewed_mutation_families
):
    applicable = applicable_mutation_pairs(
        reviewed_universe, reviewed_mutation_families
    )
    operation_cases = {
        case.case_ref for case in reviewed_universe.cases
        if case.contract.expected_decision.action == "request_effect"
    }
    assert {case for case, family in applicable if family == "permission_removed"} == operation_cases
    assert {case for case, family in applicable if family == "adapter_removed"} == operation_cases
```

- [ ] **Step 2: Run tests and verify the current environments fail**

```powershell
python -m pytest tests/test_r4_expansion.py tests/test_r4_assertion_compiler.py tests/test_r4_mutations_and_partitions.py -k "request_effect or removal_families" -q
```

Expected: failure because current operation situations do not carry the two
prerequisite arrays.

- [ ] **Step 3: Correct the scenario generator at the earliest owner**

For every reviewed transition-simulation environment that lowers to
`request_effect`, emit exactly:

```python
"situation_constraints": {
    "adapter_refs": ["adapter:state"],
    "permission_refs": ["permission:set_state"],
    "world_facts": world_facts,
}
```

Do not patch generated JSONL by hand. The assertion compiler must validate both
refs against linked authority and carry them unchanged into
`ExpectedCycleContract.situation_constraints`.

- [ ] **Step 4: Regenerate twice and prove deterministic source bytes**

Run the repository's scenario generator twice into separate temporary paths,
compare SHA-256 and then regenerate the canonical file using its existing CLI.

```powershell
New-Item -ItemType Directory -Path "$env:TEMP\cemm-r4-authoring-a" -Force | Out-Null
New-Item -ItemType Directory -Path "$env:TEMP\cemm-r4-authoring-b" -Force | Out-Null
python scripts/generate_scenarios.py --output "$env:TEMP\cemm-r4-authoring-a\use_cases.jsonl"
python scripts/generate_scenarios.py --output "$env:TEMP\cemm-r4-authoring-b\use_cases.jsonl"
$left = (Get-FileHash "$env:TEMP\cemm-r4-authoring-a\use_cases.jsonl" -Algorithm SHA256).Hash
$right = (Get-FileHash "$env:TEMP\cemm-r4-authoring-b\use_cases.jsonl" -Algorithm SHA256).Hash
if ($left -ne $right) { throw "scenario generation is nondeterministic" }
python scripts/generate_scenarios.py --output data/scenarios/use_cases.jsonl
python -m pytest tests/test_scenario_coverage.py tests/test_r4_expansion.py -q
```

Expected: generator check and expansion tests pass; successor case identities
and mutation applicability counts change deterministically.

- [ ] **Step 5: Record the new derived inventory in tests**

Assert the formula, not a copied total:

```python
expected = sum(
    1
    for case in universe.cases
    if source_disposition_is_supervision_eligible(case.source_disposition)
    for family in families
    if family.applies_to(case)
)
assert len(contracts) == expected
```

- [ ] **Step 6: Commit**

```powershell
git add scripts/generate_scenarios.py data/scenarios/use_cases.jsonl tests/test_r4_expansion.py tests/test_r4_assertion_compiler.py tests/test_r4_mutations_and_partitions.py
git commit -m "fix(r4): source operation prerequisites"
```

## Task 8: Add the optional pinned advisory-evidence sidecar

**Files:**

- Create: `src/cemm_authoritative_hybrid/r4_authoring_evidence.py`
- Create: `scripts/fetch_r4_authoring_evidence.py`
- Create: `schemas/r4_authoring_evidence_manifest.schema.json`
- Create: `tests/test_r4_authoring_evidence.py`

- [ ] **Step 1: Write failing bounded snapshot and authority-separation tests**

```python
def test_empty_snapshot_is_valid_and_network_free(tmp_path):
    snapshot = EvidenceSnapshot.create(sources=())
    assert snapshot.sources == ()
    assert snapshot.total_bytes == 0


def test_unknown_license_cannot_emit_suggestion(evidence_source):
    source = evidence_source(license_policy="advisory_only")
    assert normalize_evidence(source) == ()


def test_evidence_never_mints_cemm_authority(commercial_source):
    suggestions = normalize_evidence(commercial_source)
    forbidden = ("op:", "concept:", "event:", "relation:", "designation:")
    assert all(not suggestion.suggestion_ref.startswith(forbidden) for suggestion in suggestions)
    assert all(suggestion.selectable is False for suggestion in suggestions)


def test_unapproved_source_family_is_rejected(evidence_source):
    with pytest.raises(ValueError, match="source family"):
        evidence_source(source_family="unapproved_source")
```

Add URL-scheme, redirect, byte, file-count, hash, revision, license and ZIP path
traversal corruption cases. Use a local HTTP test server; tests never access
the internet.

- [ ] **Step 2: Run tests and verify missing sidecar**

```powershell
python -m pytest tests/test_r4_authoring_evidence.py -q
```

Expected: import failure.

- [ ] **Step 3: Implement exact local evidence types**

```python
@dataclass(frozen=True)
class EvidenceSource:
    source_ref: str
    source_family: str
    revision: str
    sha256: str
    byte_length: int
    license_id: str
    license_policy: str
    relative_path: str


@dataclass(frozen=True)
class EvidenceSuggestion:
    suggestion_ref: str
    source_ref: str
    evidence_kind: str
    observed_form: str
    observed_sense_key: str | None
    conflict_refs: tuple[str, ...]
    selectable: bool = False


@dataclass(frozen=True)
class EvidenceSnapshot:
    snapshot_ref: str
    sources: tuple[EvidenceSource, ...]
    total_bytes: int
```

Bound sources to 64 and aggregate bytes to 16 MiB. Permit suggestion
normalization only for reviewed commercial-compatible policies. Advisory-only
sources may appear in a human-readable report but return no serialized
suggestions. Snapshot identities bind exact source bytes, revision, license and
normalizer source hash.

The source-family allowlist is exactly `oewn`, `wikidata_lexeme` and `cldr`.
License policy is exactly `suggestion_permitted` or `advisory_only`. Broad UD,
UniMorph, FrameNet or VerbNet ingestion requires a later reviewed design
amendment tied to an unresolved gap. Every other source family and arbitrary
local corpus path is rejected.

- [ ] **Step 4: Implement the isolated fetch CLI**

The CLI accepts one JSON request containing HTTPS URL, exact revision,
expected SHA-256, expected byte limit, license id/policy and output directory.
It rejects redirects to non-HTTPS origins, links/reparse points, unexpected
hashes, archives with unsafe paths and existing non-identical output. It writes
the raw source plus one canonical evidence manifest transactionally.

The R4 worksheet builder imports only `EvidenceSnapshot.from_directory`; it
never calls the fetch CLI. An empty local snapshot is the default because the
current semantic cases already have explicit CEMM designations.

- [ ] **Step 5: Run evidence tests and import-boundary scan**

```powershell
python -m pytest tests/test_r4_authoring_evidence.py -q
rg -n "requests|urllib|httpx|fetch_r4_authoring_evidence" src/cemm_authoritative_hybrid scripts/build_r4_1_review_worksheets.py
```

Expected: tests pass; network imports occur only in the fetch script, not the
package or worksheet builder.

- [ ] **Step 6: Commit**

```powershell
git add src/cemm_authoritative_hybrid/r4_authoring_evidence.py scripts/fetch_r4_authoring_evidence.py schemas/r4_authoring_evidence_manifest.schema.json tests/test_r4_authoring_evidence.py
git commit -m "feat(r4): add advisory evidence snapshots"
```

## Task 9: Define bounded purpose-scoped recipe and candidate records

**Files:**

- Create: `src/cemm_authoritative_hybrid/r4_authoring.py`
- Create: `tests/test_r4_authoring.py`
- Modify: `src/cemm_authoritative_hybrid/r4_purpose.py`
- Modify: `tests/test_r4_purpose_contracts.py`

- [ ] **Step 1: Write failing closed-envelope and leakage tests**

```python
def test_candidate_envelope_is_inert_and_complete(recipe, review_context):
    candidate = AuthoringCandidate.create(
        candidate_kind="proposal",
        source_case_ref="expanded_case_v2:0123456789abcdef01234567",
        purpose="train",
        recipe_ref=recipe.recipe_ref,
        input_refs=(review_context.input_set_ref,),
        evidence_refs=(),
        generator_source_ref="generator_source:0123456789abcdef01234567",
        provenance_refs=(review_context.review_context_ref,),
        verification_receipt_ref="authoring_verification:0123456789abcdef01234567",
        selectable=False,
        exception_codes=("awaiting_review",),
        proposed_row=None,
    )
    assert candidate.selectable is False
    assert candidate.proposed_row is None


def test_recipe_descendants_cannot_cross_purposes(recipe_family):
    train = recipe_family.instantiate(purpose="train")
    frozen = recipe_family.instantiate(purpose="frozen_test")
    with pytest.raises(ValueError, match="ancestry crosses purposes"):
        validate_recipe_ancestry((train, frozen), ((train.recipe_ref, frozen.recipe_ref),))
```

Add tests for unknown fields, more than 128 recipes per kind/purpose, more than
512 purpose-scoped instances per kind, family-key collisions after
normalization and candidate refs affected by generator/evidence/input drift.

- [ ] **Step 2: Run tests and verify absence**

```powershell
python -m pytest tests/test_r4_authoring.py tests/test_r4_purpose_contracts.py -k recipe -q
```

Expected: import failure for authoring types.

- [ ] **Step 3: Implement worksheet-local records**

```python
@dataclass(frozen=True)
class AuthoringRecipe:
    recipe_ref: str
    recipe_kind: str
    purpose: str
    normalized_family_key: tuple[object, ...]
    member_case_refs: tuple[str, ...]
    ancestry_refs: tuple[str, ...]
    reviewed_parameters: Mapping[str, object]
    review_refs: tuple[str, ...]


@dataclass(frozen=True)
class AuthoringCandidate:
    candidate_ref: str
    candidate_kind: str
    source_case_ref: str
    purpose: str
    recipe_ref: str
    input_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    generator_source_ref: str
    provenance_refs: tuple[str, ...]
    verification_receipt_ref: str
    selectable: bool
    exception_codes: tuple[str, ...]
    proposed_row: Mapping[str, object] | None


@dataclass(frozen=True)
class AuthoringResult:
    universe: SourceUniverse
    supervised_cases: tuple[ExpandedCase, ...]
    cases_by_ref: Mapping[str, ExpandedCase]
    form_lattices_by_case: Mapping[str, FormLattice]
    proposal_contexts_by_case: Mapping[str, ProposalContext]
    proposal_targets_by_case: Mapping[str, ProposalTarget]
    proposals: tuple[AuthoringCandidate, ...]
    designations: tuple[AuthoringCandidate, ...]
    realizations: tuple[RealizationRow, ...]
    mutation_contracts: tuple[MutationContract, ...]
    mutation_families: tuple[ReviewedMutationFamily, ...]
    recipes: tuple[AuthoringRecipe, ...]
    effect_projection: NormalEffectProjection | None
    operation_counts: Mapping[str, int]
    linear_operation_bound: int
    max_recipe_families_per_kind_purpose: int
    max_recipe_instances_per_kind: int
    max_designation_targets_per_span: int
    max_realization_variants_per_case: int
    max_mutation_families_per_case: int

    @property
    def case_count(self) -> int:
        return len(self.universe.cases)

    @property
    def supervised_case_count(self) -> int:
        return len(self.supervised_cases)

    @property
    def context_build_count(self) -> int:
        return self.operation_counts.get("proposal_context_builds", 0)

    @property
    def mutation_contract_count(self) -> int:
        return len(self.mutation_contracts)

    @property
    def operation_count(self) -> int:
        return sum(self.operation_counts.values())
```

Factories must enforce closed recipe kinds
`proposal|designation|realization|mutation`, four purposes, exact member
ownership, bounded mappings and canonical identities. These types deliberately
have no decoder in `r4_supervision` and no place in the review manifest.
Use `from __future__ import annotations`; Task 12 adds the two worksheet-local
`ReviewedMutationFamily` and `NormalEffectProjection` values referenced by the
aggregate without creating a persistent ABI.

- [ ] **Step 4: Join recipe ancestry into existing purpose evidence**

Add a function to `r4_purpose.py` that converts explicit recipe ancestry edges
to reviewed duplicate-risk memberships before the existing union/find pass.
It may not derive edges from shared operator, topology, surface similarity or
semantic refs. Count each declared membership once and retain linear bounds.

- [ ] **Step 5: Run authoring/purpose tests**

```powershell
python -m pytest tests/test_r4_authoring.py tests/test_r4_purpose_contracts.py -k "recipe or ancestry" -q
```

Expected: pass; purpose ownership remains the existing contract's decision.

- [ ] **Step 6: Commit**

```powershell
git add src/cemm_authoritative_hybrid/r4_authoring.py src/cemm_authoritative_hybrid/r4_purpose.py tests/test_r4_authoring.py tests/test_r4_purpose_contracts.py
git commit -m "feat(r4): define purpose scoped authoring recipes"
```

## Task 10: Generate proposal and designation candidates from exact source

**Files:**

- Modify: `scripts/build_r4_1_review_worksheets.py:1144-1321`
- Modify: `scripts/build_r4_1_review_worksheets.py:1775-2000`
- Modify: `src/cemm_authoritative_hybrid/r4_supervision.py:973-1041`
- Create: `tests/test_r4_authoring_pipeline.py`
- Create: `tests/test_r4_review_worksheets.py`
- Modify: `tests/test_r4_supervision_contracts.py`

### Task 10A: Generate source/context and designation evidence

Task 10A is source-only and may run before purpose selection.  It builds and
authenticates one FormLattice, GroundingResult and ProposalContext per eligible
case, emits exact designation candidate sets and normalized proposal-recipe
suggestions, and leaves every suggestion non-selectable.  These records do not
pretend to be `AuthoringRecipe` values because that type requires a settled
purpose.

### Task 10B: Expand proposals after explicit reviewer selections

Task 10B requires one canonical bounded reviewer-selection input that selects
the structural branch, every purpose/group/holdout option and reviewed recipe
parameters by exact worksheet option/row refs.  The input contains no
`source_review`, manifest, bundle or child-row identity.  The final draft adds
its bytes to the authenticated input set, computes the prospective review
context and only then creates purpose-scoped `AuthoringRecipe` and
`AuthoringCandidate` values.  A changed selection forces regeneration.

Do not infer a purpose, auto-select a solver result, expand one case into all
four purposes, or hash a final `PurposeContract` into the review-context input.

The bounded handoff is now generated at
`artifacts/review_inputs/r4_1/SELECTION_TEMPLATE.json` with identity
`r4_authoring_selection_template:08b58fe89e8a11c92b188452` and SHA-256
`44a9e1f1a0418fda4b8bfa9a790a8fdd2069eb62d7653b34f6cc996d66bed37d`.
It covers 12 structural, 600 purpose, 56 proposal-family and 388 designation
targets.  All selections, reviewer refs and purpose-scoped recipe parameters
remain empty.  The template is inert and does not unblock expansion until a
completed working copy passes the implemented strict selection validator.

- [x] **Step 1: Write failing source/context and designation inventory tests**

```python
def test_proposal_and_designation_authoring_covers_successor_universe(
    authoring_result
):
    supervised = {
        case.case_ref for case in authoring_result.universe.cases
        if source_disposition_is_supervision_eligible(case.source_disposition)
    }
    assert {row.source_case_ref for row in authoring_result.proposals} == supervised
    assert {row.source_case_ref for row in authoring_result.designations} == supervised
    assert all(row.proposed_row is not None for row in authoring_result.proposals)


def test_designation_spans_come_from_form_geometry(authoring_result):
    for candidate in authoring_result.designations:
        case = authoring_result.cases_by_ref[candidate.source_case_ref]
        lattice = authoring_result.form_lattices_by_case[candidate.source_case_ref]
        permitted = {
            (unit.source_start, unit.source_end) for unit in lattice.units
        }
        for fact in candidate.proposed_row["designation_facts"]:
            assert (fact["source_start"], fact["source_end"]) in permitted
            assert case.surface[fact["source_start"]:fact["source_end"]] == fact["source_text"]
```

In Task 10A, apply the designation assertions to the source-only evidence
result.  Apply the proposal `AuthoringCandidate` assertions only in Task 10B
with a canonical reviewer-selection fixture.

Add exact tests deriving 61 reviewed-empty gap/rejection sets, 12 cases with
intersecting spans, 13 undirected overlap pairs and 21 cases with a multi-unit
designation span.  Also prove no default concept, no ref-name lexicalization
and no use of the old `_PROPOSALS` table as general designation authority.

- [x] **Step 2: Run tests and verify current 8/388 designation limitation**

```powershell
python -m pytest tests/test_r4_authoring_pipeline.py tests/test_r4_review_worksheets.py -k "proposal or designation" -q
```

Expected: failure because the current worksheet builder populates designation
candidates only for eight structural proposal rows and emits no exact proposal
records.

- [x] **Step 3: Add one source snapshot/context cache per case (10A)**

In the builder, authenticate and hash:

```text
data/scenarios/use_cases.jsonl
data/languages/en/forms.json
configs/proposal_release.json
complete authority manifest/file closure
r4 source expander/compiler closure
three reviewed supervision compiler source closures
review policy
optional local evidence manifest
```

Task 10B additionally authenticates the bounded reviewer-selection input.
Task 10A must not pretend that unresolved purpose-decision worksheet rows are
selected inputs.

Build one FormLattice, GroundingResult and immutable ProposalContext per
supervised case and store them in bounded dicts keyed by case ref. Expose
operation counters proving one construction per case.

- [x] **Step 4: Emit non-selectable normalized proposal recipe suggestions (10A)**

The source-only draft may group complete normalized shapes and expose concrete
case parameters.  It must not construct purpose-scoped recipes or selectable
proposal rows before the reviewer-selection input exists.

- [x] **Step 4B: Validate selections and generate proposal candidates (10B)**

Derive the complete family key from source-owned expression topology, mode,
outcome, gap/rejection shape and relation. Expand the reviewed recipe to an
exact `ProposalTarget`; semantic cases receive exact derivation blueprints,
gap cases exact `TypedAbstention`, and rejection cases exact
`VerificationRejection`. Run `ReviewedDerivationCompiler` for each semantic
derivation before setting `selectable: true`; a failure emits an explicit
exception and no proposed ABI row.

- [x] **Step 5: Generate canonical designation sets**

For each FormLattice unit span of at most eight units, use only
`authority.designations.facts_for_surface`. Emit exact case/surface/span/fact
bindings in canonical geometry/ref order and preserve overlaps. Enforce eight
targets per span. Emit an exact-empty set only for a nonsemantic source case
when the independent full scan returns no facts.

- [x] **Step 6: Wire exact derivation compilation into cross-source validation (10B)**

Pass the complete repository-owned per-case `ProposalContext` cache from Step 3
to the one cross-source validator. Compile every semantic derivation with
`ReviewedDerivationCompiler` and count its bounded operations. Typed gaps and
verifier rejections retain their exact dedicated checks and do not masquerade
as semantic derivations. The compiler path is mandatory for every semantic
row: no optional callback, missing-context bypass, expected-gold-derived
context, placeholder-blueprint acceptance or permissive fallback is allowed.

- [x] **Step 7: Run focused pipeline and cross-source tests twice**

```powershell
python -m pytest tests/test_r4_authoring_pipeline.py tests/test_r4_review_worksheets.py tests/test_r4_supervision_compilers.py tests/test_r4_supervision_contracts.py -k "proposal or designation or deterministic or derivation or cross_source" -q
```

Expected: pass; two builds have byte-identical proposal/designation candidate
sections and exact supervised case sets.

- [x] **Step 8: Commit**

```powershell
git add scripts/build_r4_1_review_worksheets.py src/cemm_authoritative_hybrid/r4_supervision.py tests/test_r4_authoring_pipeline.py tests/test_r4_review_worksheets.py tests/test_r4_supervision_contracts.py
git commit -m "feat(r4): author proposal and designation candidates"
```

## Task 11: Author complete neutral realization recipes and rows

**Files:**

- Modify: `scripts/build_r4_1_review_worksheets.py:1144-1321`
- Modify: `tests/test_r4_authoring_pipeline.py`
- Modify: `tests/test_r4_review_worksheets.py`
- Regenerate: `artifacts/review_drafts/r4_1/SUPERVISION_DECISIONS.json`

- [ ] **Step 1: Write failing full-realization and family-key tests**

```python
def test_every_supervised_case_has_one_compiling_initial_realization(
    authoring_result, linked_authority
):
    supervised = tuple(
        case for case in authoring_result.universe.cases
        if source_disposition_is_supervision_eligible(case.source_disposition)
    )
    assert len(authoring_result.realizations) == len(supervised)
    by_case = {row.source_case_ref: row for row in authoring_result.realizations}
    for case in supervised:
        compiled = ReviewedRealizationCompiler(linked_authority).compile(
            case=case,
            proposal=authoring_result.proposal_targets_by_case[case.case_ref],
            row=by_case[case.case_ref],
        )
        assert compiled.authorized_surface.strip()


def test_realization_recipe_key_separates_semantic_differences(recipe_key_factory):
    base = recipe_key_factory()
    for field in (
        "subject", "bindings", "qualifiers", "action", "polarity", "modality",
        "epistemic_status", "speaker", "addressee", "language", "alignments",
    ):
        assert recipe_key_factory(change=field) != base


def test_frozen_recipe_has_no_nonfrozen_ancestry(authoring_result):
    by_ref = {row.recipe_ref: row for row in authoring_result.recipes}
    for recipe in authoring_result.recipes:
        if recipe.purpose != "frozen_test":
            continue
        assert all(by_ref[parent].purpose == "frozen_test" for parent in recipe.ancestry_refs)
```

Add tests for input echo, empty/placeholder surface, missing alignment, more
than four alternatives, more than 128 realization recipes in one purpose and
bootstrap episode migration.

- [ ] **Step 2: Run tests and verify the 380-surface blocker**

```powershell
python -m pytest tests/test_r4_authoring_pipeline.py tests/test_r4_review_worksheets.py -k realization -q
```

Expected: failure because 380 cases lack surfaces and all bootstrap episodes
are predecessor-shaped.

- [ ] **Step 3: Add the reviewed recipe vocabulary to the existing worksheet**

The `realization_recipes` section of `SUPERVISION_DECISIONS.json` contains only
purpose-scoped recipes with these exact fields:

```json
{
  "realization_recipes": [
    {
      "recipe_ref": "authoring_recipe:1123456789abcdef01234567",
      "purpose": "train",
      "member_case_refs": ["expanded_case_v2:2123456789abcdef01234567"],
      "response_subject_key": {},
      "binding_rules": [],
      "slot_rules": [],
      "discourse_action_ref": "response_action:answer",
      "polarity_ref": "polarity:positive",
      "modality_ref": "modality:actual",
      "epistemic_status_ref": "epistemic_status:supported",
      "speaker_ref": "participant:system",
      "addressee_ref": "participant:user",
      "language": "en",
      "surface_template": "I cannot resolve that safely.",
      "alignment_rules": [],
      "ancestry_refs": [],
      "review_refs": ["source_review:0123456789abcdef01234567"]
    }
  ],
  "realization_exceptions": []
}
```

The displayed row is a schema-valid exemplar, not checked-in review authority.
The implementation task populates every record from the approved review
context and exact case refs. The worksheet's `realization_exceptions` array is
exact-empty when all cases compile; otherwise it contains non-selectable
candidate envelopes with exact error codes and no ABI row.

- [ ] **Step 4: Produce reviewer worksheets, not automatic gold**

Generate bounded neutral-surface suggestions grouped by complete semantic key.
Suggestions remain `selectable: false`. Review every recipe, especially safe
gap/rejection surfaces, participant perspective, copied literals, omissions
and foreign forms. Replace each suggestion with an explicit reviewed recipe;
do not approve a family merely because the compiler accepts it.

For `frozen_test`, do not copy a surface template, lexical substitution,
translation or alignment recipe from train, selection or calibration. Emit an
independent authoring requirement and require the reviewer to author it without
reading non-frozen recipe bytes. Similar structural signatures across purposes
do not establish ancestry, but any actual derivation or reuse does and must be
rejected.

- [ ] **Step 5: Expand reviewed recipes and independently compile every row**

Expand each member case to one concrete `RealizationRow`. Resolve template
slots only from source-owned subjects/bindings and reviewed literal sources.
Then run `ReviewedRealizationCompiler` and require exact response-signature
equality before emitting `selectable: true`.

- [ ] **Step 6: Run realization and preservation tests**

```powershell
python -m pytest tests/test_r4_authoring_pipeline.py tests/test_r4_review_worksheets.py tests/test_realization_verifier.py tests/test_r5_realization_boundary.py -k "realization or authorized_surface" -q
```

Expected: pass; every supervised case has one nonempty verified surface and no
bootstrap/runtime output is used as gold.

- [ ] **Step 7: Commit code; leave recipe review in the draft package**

```powershell
git add scripts/build_r4_1_review_worksheets.py tests/test_r4_authoring_pipeline.py tests/test_r4_review_worksheets.py
git commit -m "feat(r4): expand reviewed realization recipes"
```

Do not commit a separate recipe source. The accountable human recipe review is
recorded later with the exact draft package in Task 14.

## Task 12: Expand reviewed mutation families and prove normal effects separately

**Files:**

- Modify: `scripts/build_r4_1_review_worksheets.py:1144-1321`
- Modify: `scripts/build_r4_1_review_worksheets.py:1775-2000`
- Modify: `src/cemm_authoritative_hybrid/r4_supervision.py:1062-1065`
- Modify: `tests/test_r4_authoring_pipeline.py`
- Modify: `tests/test_r4_supervision_contracts.py`
- Regenerate: `artifacts/review_drafts/r4_1/SUPERVISION_DECISIONS.json`

- [ ] **Step 1: Write failing exact applicability and effect-separation tests**

```python
def test_mutation_contract_set_equals_reviewed_applicability(authoring_result):
    expected = {
        (case.case_ref, family.mutation_family_ref)
        for case in authoring_result.supervised_cases
        for family in authoring_result.mutation_families
        if family.applies_to(case)
    }
    actual = {
        (row.source_case_ref, row.mutation_family_ref)
        for row in authoring_result.mutation_contracts
    }
    assert actual == expected


def test_normal_effects_are_not_mutation_contracts(authoring_result):
    assert all(
        row.changed_dimension_ref != "mutation_dimension:normal_expected_effect"
        for row in authoring_result.mutation_contracts
    )
    assert authoring_result.effect_projection.unmatched == ()
    assert authoring_result.effect_projection.ambiguous == ()
```

- [ ] **Step 2: Run tests and verify current 388-row conflation fails**

```powershell
python -m pytest tests/test_r4_authoring_pipeline.py tests/test_r4_supervision_contracts.py -k "mutation or effect_projection" -q
```

Expected: failure because the worksheet currently writes one normal-effect
requirement per case and no adversarial contracts.

- [ ] **Step 3: Put reviewed family definitions in the existing worksheet**

Define exactly eight bounded families:

```text
invalid_role
missing_predicate
dangling_root
permission_removed
adapter_removed
source_untrusted
stale_revision
decision_action_mismatch
```

Each definition owns scope, dimension, typed path template, replacement rule,
applicability predicate over typed source fields, owner, status, error,
disposition and effect expectation. Predicates may inspect source outcome,
expression presence, decision action and exact situation-constraint refs; they
may not inspect raw surface text or runtime output.

Decode each worksheet definition into this exact worksheet-local value:

```python
@dataclass(frozen=True)
class ReviewedMutationFamily:
    mutation_family_ref: str
    scope: str
    changed_dimension_ref: str
    selector_kind: str
    path_template: tuple[str | int, ...]
    operation: str
    replacement_after: object
    applicability_kind: str
    expected_earliest_owner: str
    expected_status: str
    expected_error_code: str
    disposition: str
    effect_kind: str
    expected_effect_ref: str | None
    review_refs: tuple[str, ...]

    def applies_to(self, case: ExpandedCase) -> bool:
        if not source_disposition_is_supervision_eligible(case.source_disposition):
            return False
        if self.applicability_kind == "semantic_expression":
            return bool(case.contract.expected_expressions)
        constraints = case.contract.situation_constraints
        if self.applicability_kind == "permission_required":
            return "permission:set_state" in constraints.get("permission_refs", ())
        if self.applicability_kind == "adapter_required":
            return "adapter:state" in constraints.get("adapter_refs", ())
        if self.applicability_kind == "all_supervised":
            return True
        raise ValueError("unknown reviewed mutation applicability kind")
```

The decoder admits only the four displayed applicability kinds and validates
the remaining fields through the same closed enums as `MutationContract`.

- [ ] **Step 4: Expand and independently compile every applicable pair**

Instantiate one `MutationContract` per applicable pair in canonical order, run
`ReviewedMutationCompiler`, and emit the concrete contract only after exact
before/after reconstruction. The source validator builds the expected pair set
once and requires exact equality with the bundle pair set.

- [ ] **Step 5: Reconstruct normal effect evidence in a separate receipt**

Keep the worksheet-local effect projection diagnostic with:

```python
@dataclass(frozen=True)
class NormalEffectProjection:
    receipt_refs: tuple[str, ...]
    transition_refs: tuple[str, ...]
    unmatched: tuple[str, ...]
    ambiguous: tuple[str, ...]
    operation_count: int
```

Join sensor/operation evidence to exact reviewed receipt refs and
`request_effect` transitions to exact authority transition refs. This receipt
does not enter `mutation_contracts.jsonl` and does not replace
`ExpectedCycleContract.expected_effect`.

- [ ] **Step 6: Run mutation/effect tests**

```powershell
python -m pytest tests/test_r4_authoring_pipeline.py tests/test_r4_supervision_contracts.py tests/test_r4_mutations_and_partitions.py -k "mutation or effect_projection" -q
```

Expected: pass; all eight families are reviewed, the two R5 operation families
are applicable to source-owned operation cases, and normal effects resolve
without entering adversarial truth.

- [ ] **Step 7: Commit code; leave family review in the draft package**

```powershell
git add scripts/build_r4_1_review_worksheets.py src/cemm_authoritative_hybrid/r4_supervision.py tests/test_r4_authoring_pipeline.py tests/test_r4_supervision_contracts.py tests/test_r4_mutations_and_partitions.py
git commit -m "feat(r4): expand reviewed mutation contracts"
```

Do not create a persistent recipe ABI or a second data owner. The explicit
human family review is recorded later with the exact draft package in Task 14.

## Task 13: Integrate deterministic publication, corruption and performance proofs

**Files:**

- Create: `tests/test_r4_1_authoring_performance.py`
- Modify: `tests/test_r4_authoring_pipeline.py`
- Modify: `tests/test_r4_review_worksheets.py`
- Modify: `tests/test_r4_supervision_contracts.py`
- Modify: `scripts/build_r4_1_review_worksheets.py:1459-2369`
- Modify: `configs/validation_gates.json`

- [ ] **Step 1: Write failing deterministic and bound tests**

```python
def test_authoring_build_is_byte_identical(build_authoring_draft, tmp_path):
    left = build_authoring_draft(tmp_path / "left")
    right = build_authoring_draft(tmp_path / "right")
    assert left.relative_paths == right.relative_paths
    assert left.file_bytes == right.file_bytes


def test_authoring_bounds_are_linear(authoring_result):
    assert authoring_result.case_count <= 512
    assert authoring_result.context_build_count == authoring_result.supervised_case_count
    assert authoring_result.max_recipe_families_per_kind_purpose <= 128
    assert authoring_result.max_recipe_instances_per_kind <= 512
    assert authoring_result.max_designation_targets_per_span <= 8
    assert authoring_result.max_realization_variants_per_case <= 4
    assert authoring_result.max_mutation_families_per_case <= 8
    assert authoring_result.mutation_contract_count <= 4096
    assert authoring_result.operation_count <= authoring_result.linear_operation_bound
```

Add corruption cases for every spec requirement: input/hash drift, review
cycle, recipe collision, purpose crossing, forged designation, program drift,
response drift, missing/extra mutation family, external/LLM promotion,
unbounded iterator, >16 MiB worksheet and partial publication rollback.

- [ ] **Step 2: Run tests and verify integrated failures**

```powershell
python -m pytest tests/test_r4_1_authoring_performance.py tests/test_r4_authoring_pipeline.py tests/test_r4_review_worksheets.py tests/test_r4_supervision_contracts.py -q
```

Expected: failures until counters, exact file sets and integrated validators are
wired through the existing worksheet publisher.

- [ ] **Step 3: Extend the existing worksheet envelope without adding a gate**

Bind recipe/candidate/exception refs, exact compiler/evidence source hashes,
review-context ref and operation counters into the current four worksheet
envelopes and summary. Keep all candidates `draft_non_authoritative` until
approval. Do not add recipe files to `data/review/r4_1/` or to the final R4
review manifest.

- [ ] **Step 4: Enforce bounds before materialization**

Use bounded iterators for source cases, evidence files, recipes, members,
alternatives, mutation pairs and output rows. Check aggregate byte limits while
encoding into bounded buffers or temporary files; do not build an unbounded
list/string and check length afterward.

- [ ] **Step 5: Reuse transactional A/B publication**

Keep the existing verified A bytes, same-parent exclusive stage, fsync/reread,
A/B reauthentication, no-replace rename and rollback. Update the exact draft
file inventory only once. A pre-existing final directory is a no-op only when
all paths and bytes match exactly.

- [ ] **Step 6: Keep validation topology unchanged**

Add the new tests to the existing R4 active-suite selector. Assert the same
validation tier count and at most one pytest process per existing R4 owner.
Add import scans proving runtime, activation and web modules cannot reach
`r4_authoring`, `r4_authoring_evidence` or the fetch script.

- [ ] **Step 7: Run the integrated authoring suite**

```powershell
python -m pytest tests/test_r4_1_authoring_performance.py tests/test_r4_authoring_pipeline.py tests/test_r4_review_worksheets.py tests/test_r4_supervision_contracts.py -q
python scripts/check_test_inventory.py --phase R4 --source-only
python -m compileall -q src scripts tests
```

Expected: all pass; no second pytest process or validation tier is introduced.

- [ ] **Step 8: Commit**

```powershell
git add tests/test_r4_1_authoring_performance.py tests/test_r4_authoring_pipeline.py tests/test_r4_review_worksheets.py tests/test_r4_supervision_contracts.py scripts/build_r4_1_review_worksheets.py configs/validation_gates.json
git commit -m "test(r4): prove bounded supervision authoring"
```

## Task 14: Generate the exact review package and hand back to the main replay

**Files:**

- Regenerate: `artifacts/review_drafts/r4_1/**`
- Modify: `docs/ABI_REGISTRY.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/superpowers/progress/2026-08-29-r4-1-data-supervision-replay-progress.md`
- Do not create yet: `data/review/r4_1/**`
- Do not modify: `governance/replay_status.jsonl`

- [ ] **Step 1: Start from a clean source commit**

```powershell
git status --short
git rev-parse HEAD
```

Expected: empty status and one exact 40-character source revision.

- [ ] **Step 2: Generate and validate two independent drafts**

Use the builder's documented CLI to create temporary A and B directories, run
its validator on both, and require byte-identical relative paths and hashes.
Then publish the retained A bytes transactionally to
`artifacts/review_drafts/r4_1`.

- [ ] **Step 3: Inspect the exact outcome report**

Require the report to show:

```text
supervised case set: exact and complete
proposal targets: one per supervised case
designation sets: one per supervised case, including reviewed exact-empty sets
initial realizations: one per supervised case
mutation contracts: exact applicable case/family Cartesian subset
normal effects: zero unmatched, zero ambiguous
diagnostic restart cases: absent from supervision
recipe ancestry: no cross-purpose edge
exceptions: zero selectable placeholders
all configured bounds: passed
```

Family-macro and worst-family metrics are diagnostics only.

- [ ] **Step 4: Obtain accountable recipe/expansion review**

The reviewer checks every normalized proposal/designation/mutation family,
every realization recipe, every exception, all safe gap/rejection surfaces,
operation prerequisites and the exact expanded hashes. Any correction returns
to the earliest source/recipe/compiler task and regenerates all dependent
identities.

- [ ] **Step 5: Update active documentation without a green claim**

Record:

- repaired ABI 1 fields and strict decoders implemented;
- review-context identity implemented;
- pure compilers implemented and independently tested;
- authoring recipes/evidence remain offline and non-authoritative;
- exact draft refs/counts/hashes and review disposition;
- main replay Task 4 second data review and publication still pending; and
- R4/R5 remain red.

- [ ] **Step 6: Run the source-only checkpoint**

```powershell
python scripts/check_test_inventory.py --phase G0 --source-only
python scripts/check_test_inventory.py --phase R4 --source-only
python -m compileall -q src scripts tests
python scripts/validate_mvp.py --tier phase --phase G0
python scripts/validate_mvp.py --tier phase --phase R1
python scripts/validate_mvp.py --tier phase --phase R2
python scripts/validate_mvp.py --tier phase --phase R3
```

Expected: all pass. Do not run R4 admission because no reviewed source bundle
or candidate artifact is published yet.

- [ ] **Step 7: Commit draft evidence and documentation**

```powershell
git add artifacts/review_drafts/r4_1 docs/ABI_REGISTRY.md docs/ARCHITECTURE.md docs/superpowers/progress/2026-08-29-r4-1-data-supervision-replay-progress.md
git commit -m "docs(r4): record supervision authoring review"
```

- [ ] **Step 8: Resume the governing replay**

Return to the main R4.1 plan's reviewed-source publication checkpoint. Preserve
its separate second data-review act, purpose ownership, class-local sufficiency,
four compact payloads, ABI 5 candidate graph, independent admission, R4 green
append and R5 handoff. Do not copy recipe/evidence records into runtime or R5
payloads.

## 3. Final completion criteria for this corrective plan

This plan is complete only when:

- all fourteen task commits are present or intentionally combined without
  weakening their review checkpoints;
- Mutation Contract ABI 1 can encode and reconstruct every active family;
- `_SPECS` and executor-authored mutation truth are absent from current paths;
- one canonical designation-fact identity flows from authority through
  grounding and realization alignment;
- proposal Programs independently compile to exact source-owned expressions;
- every supervised case has one independently verified initial realization;
- normal effect evidence is exact and separate from adversarial truth;
- every operation request source-owns adapter and permission prerequisites;
- recipe and evidence layers remain offline, bounded and non-authoritative;
- recipe ancestry cannot cross purpose ownership;
- two clean authoring runs are byte-identical;
- all source-only gates and focused corruption/performance tests pass;
- the accountable authoring review is recorded; and
- no reviewed source publication, R4 admission, R4 green transition, R5
  training, model publication, activation or root adoption has been claimed by
  this corrective plan.

The next governed work is the existing main replay publication/admission
sequence, not a new implementation branch or parallel runtime.
