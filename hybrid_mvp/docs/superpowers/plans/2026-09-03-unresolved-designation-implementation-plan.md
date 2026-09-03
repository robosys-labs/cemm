# Unresolved Designation Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `What is zorbulate?` compile and verify as an exact open `op:designation` query, return `UNKNOWN` without proposal abstention or mutation, and hard-cut known and unknown designation expressions to the same reviewed label-family encoding.

**Architecture:** Proposal Context ABI 2 gains one closed `UnresolvedDesignationFrame` variant beside the existing grounded `ApplicationFrameSlot`. Both variants compile through the existing Program ABI 2 actions into ordinary five-operator Semantic Expression ABI 2 graphs. Stage 10 projects only query-relevant, indexed designation facts from `LinkedAuthority.designations`; no network, corpus scan, atom invention, form-pack regeneration, or new validation tier is introduced.

**Tech Stack:** Python 3.12, frozen dataclasses, canonical content-addressed JSON, pytest, the existing recursive composer/compiler/verifier, `DesignationIndex`, and the existing R2/R3/R4 validation selectors.

**Execution status (2026-09-03):** plan and one-way variable-ownership amendment
 approved; Tasks 1 and 2 completed; Task 3 in progress. The user approved removing
the frame's hashed variable back-pointer while retaining existing variable-to-
frame ownership. Task 2 passed renewed spec and quality review at `aeaad1f`;
the ABI/lazy-import owners passed 71 tests. The
historical stop record remains at the end of this document; no activation,
merge or admission is implied.

**Task 4 preflight constraint:** do not begin builder emission under the
assumption that an unresolved designation-query construction already exists.
The read-only probe recorded below disproves that premise. Task 3 remains
independent and authorized; a reviewed form-evidence amendment is required
before Task 4 can safely consume an unknown query span.

---

## Governing boundaries

Implement this plan only against:

- `AGENTS.md` and the canonical root architecture contracts;
- `hybrid_mvp/AGENTS.md` and its active document routing;
- `hybrid_mvp/docs/superpowers/specs/2026-09-03-unresolved-designation-and-research-handoff-design.md`; and
- the current intentional RED in `tests/test_r3_r4_predecessor_regressions.py::test_closure_unknown_designation_preserves_literal_and_unknown_action`.

This slice does **not** authorize R4.1 admission, corpus rebuilding, R5 training, online research, a new effect type, a new operator, or opportunistic repair of the next closure failure. Once the unknown-designation case is green, run the fixed closure cases in order and stop at the first unrelated failure with an evidence-backed stop record.

The following decisions are fixed:

```text
op:designation(
  predicate_ref = label:lexical,
  role:label_type = label:lexical,
  role:surface = literal("zorbulate"),
  role:target = ?meaning
)
```

- `concept:zorbulate` must never be created.
- The unknown span is literal evidence, not authority and not an opaque residual.
- Known and unknown designation applications use the same label-family predicate.
- Program ABI 2 remains unchanged unless an owner test proves its existing actions cannot encode the graph. This plan expects that proof to pass.
- The historical filename `tests/test_proposal_context_abi1.py` remains in place to avoid needless authenticated-node churn; update its module text and assertions to state that the filename is lineage-only and ABI 2 is active.
- All changed R3/R4 test bodies receive refreshed literal `source_ast_sha256` metadata through the existing refresher. Do not hand-edit inventory identities or add a test process.

## Task 1: Freeze the blocker and the hard-cut contract

**Files:**

- Modify: `tests/test_proposal_context_builder.py`
- Modify: `tests/test_semantic_expressions.py`
- Modify: `tests/test_proposal_context_program_verifier_canary.py`
- Test: `tests/test_r3_r4_predecessor_regressions.py`

- [ ] **Step 1: Reproduce the intentional RED from a clean tree**

Run from `C:\dev\cemm\hybrid_mvp`:

```powershell
python -m pytest tests/test_r3_r4_predecessor_regressions.py::test_closure_known_definition_traverses_selected_semantic_path tests/test_r3_r4_predecessor_regressions.py::test_closure_unknown_designation_preserves_literal_and_unknown_action tests/test_r3_r4_predecessor_regressions.py::test_closure_invalid_program_receives_typed_verification_rejection -q -p no:cacheprovider
```

Expected: known and invalid-program cases pass; unknown designation fails first at Stage 5 because `zorbulate` remains a critical residual. If the earliest divergence differs, stop and record it before changing code.

- [ ] **Step 2: Add owner tests for the intended Proposal Context shape**

Replace the old diagnostic assertion that `zorbulate` has no frame/literal/variable with assertions that the builder emits exactly one `UnresolvedDesignationFrame` containing:

```python
assert frame.label_type_ref == "label:lexical"
assert frame.literal_contribution_slot_ref == zorbulate_literal.slot_ref
assert context.variables_for_frame_role(frame.slot_ref, "role:target") == (target_variable,)
assert frame.query_binder_slot_ref == interrogative_binder.slot_ref
assert frame.source_unit_refs == (zorbulate_source_unit.unit_ref,)
assert not critical_residuals_for_zorbulate
```

Also add negative cases proving that a plain unknown assertion and an unknown event argument do not receive this query-only frame.

- [ ] **Step 3: Add semantic hard-cut tests before implementation**

Add tests requiring both known and unresolved designation expressions to use:

```python
assert app.operator == "op:designation"
assert app.predicate_ref == "label:lexical"
assert role(app, "role:label_type") == GroundedReference("label:lexical")
```

The known designation **fact** must bind `role:target` to a grounded semantic ref. The unresolved query must bind it to `BoundVariable`. Do not use the pre-evaluation meaning of `What is CEMM?` as the grounded-fact fixture: that existing path is a nominal-definition query, not an asserted designation fact. Preserve its definition behavior. Task 7 separately tests an open designation query against known indexed facts. Add a canary that the unresolved derivation serializes with `PROGRAM_ABI_VERSION == 2` and uses only existing `instantiate_operator`, `bind_role`, and `project_variable` actions besides structural scaffolding.

- [ ] **Step 4: Run the new tests and observe only the expected failures**

```powershell
python -m pytest tests/test_proposal_context_builder.py tests/test_semantic_expressions.py tests/test_proposal_context_program_verifier_canary.py -q -p no:cacheprovider
```

Expected: new ABI/frame/encoding assertions fail; unrelated tests remain green.

- [ ] **Step 5: Commit the executable contract**

```powershell
git add tests/test_proposal_context_builder.py tests/test_semantic_expressions.py tests/test_proposal_context_program_verifier_canary.py
git commit -m "test(r4): freeze unresolved designation semantics"
```

## Task 2: Introduce Proposal Context ABI 2 as a closed frame union

**Files:**

- Modify: `src/cemm_authoritative_hybrid/proposal_context.py`
- Modify: `src/cemm_authoritative_hybrid/__init__.py`
- Modify: `tests/test_proposal_context_abi1.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Add the exact unresolved frame type**

In `proposal_context.py`, set `PROPOSAL_CONTEXT_ABI_VERSION = 2` and add a frozen content-addressed dataclass with no nullable grounded-frame fields:

```python
@dataclass(frozen=True)
class UnresolvedDesignationFrame(_ContentAddressedSlot):
    slot_ref: str
    label_type_ref: str
    literal_contribution_slot_ref: str
    query_binder_slot_ref: str
    source_unit_refs: tuple[str, ...]
    construction_ref: str
    provenance_refs: tuple[str, ...]

ApplicationFrame = ApplicationFrameSlot | UnresolvedDesignationFrame
```

Validate exact nonempty typed refs, tuple types, uniqueness, bounds, and content identity in `create`, `as_dict`, and `from_dict`. Include an explicit wire discriminator such as `frame_type: "grounded" | "unresolved_designation"`; do not infer the variant from missing keys.

- [ ] **Step 2: Make Proposal Context serialization and indexes union-aware**

Change `ProposalContext.application_frames` to `tuple[ApplicationFrame, ...]`. Decode by the exact discriminator and reject unknown, missing, hybrid, or extra-field variants. Keep `frame_for_designation()` grounded-only and add:

```python
def unresolved_designation_frame(self, slot_ref: str) -> UnresolvedDesignationFrame | None: ...
```

Build separate indexes for grounded designation slots and unresolved frame refs. Do not create a fake `designation_slot_ref` for unresolved frames.

- [ ] **Step 3: Add cross-object invariants**

Require an unresolved frame to reference exactly one existing literal contribution and query binder. Require exactly one VariableSlot to point to that frame, with `role:target`, matching construction, and nonempty sources backed by `open_variable` contributions. Derive a bounded `variables_for_frame_role(frame_ref, role_ref)` tuple index; do not add a serialized variable pointer to the frame. Require frame source units to equal the literal's exact geometry and reject duplicate construction/span hypotheses. Authenticate reviewed `label_type` authority at the builder and verifier, not through an authority scan inside Proposal Context. Preserve all existing bounds. Replace the borrowed-variable fixture with an unresolved-only context built frame-first, variable-second; reject missing, unrelated-frame, wrong-role, duplicate and mismatched-construction variables.

- [ ] **Step 4: Hard-reject Proposal Context ABI 1 bytes**

Update the ABI tests to prove:

- ABI 2 round-trips byte-canonically for both frame variants;
- ABI 1, discriminator-free, unknown-discriminator, and mixed-field payloads fail closed;
- context identity changes when any unresolved frame field changes; and
- the filename is historical lineage, not an active ABI assertion.

- [ ] **Step 5: Run Proposal Context owner tests**

```powershell
python -m pytest tests/test_proposal_context_abi1.py tests/test_proposal_context_builder.py -q -p no:cacheprovider
```

Expected: ABI/round-trip tests pass; builder's unresolved-emission test may still fail until Task 4.

- [ ] **Step 6: Commit the ABI owner**

```powershell
git add src/cemm_authoritative_hybrid/proposal_context.py src/cemm_authoritative_hybrid/__init__.py tests/test_proposal_context_abi1.py tests/conftest.py
git commit -m "feat(r2): add unresolved designation frame ABI"
```

## Task 3: Correct canonical designation application semantics

**Files:**

- Modify: `src/cemm_authoritative_hybrid/expressions.py`
- Modify: `src/cemm_authoritative_hybrid/proposal_context.py`
- Modify: `src/cemm_authoritative_hybrid/recursive_compiler.py`
- Modify: `src/cemm_authoritative_hybrid/verifier_reconstruction.py`
- Modify: `src/cemm_authoritative_hybrid/verifier.py`
- Modify: `tests/test_semantic_expression_compiler.py`
- Modify: `tests/test_semantic_expressions.py` (correct the grounded-fact fixture as specified in Task 1)
- Modify: `tests/test_exact_verifier.py`
- Modify: `tests/test_r2_verifier_reconstruction.py`
- Modify: `tests/test_r3_learning_transaction.py`

- [ ] **Step 1: Bump only Semantic Expression ABI**

Set `SEMANTIC_EXPRESSION_ABI_VERSION = 2`. Keep the wire fields unchanged, but reject ABI 1 during exact deserialization because canonical `op:designation` content has changed. Do not bump Verified Meaning ABI or Program ABI: their containers already bind the embedded expression/program identity.

- [ ] **Step 2: Normalize grounded designation contributions at their owner**

In `_designation_application_contributions`, make the reviewed label type the application predicate and a grounded `role:label_type` filler. Preserve the designated semantic ref only as `role:target`:

```python
predicate_target_ref = label_type_ref
predicate_kind = "label_type"
derived_role_targets = (
    ("role:label_type", label_type_ref),
    ("role:target", designation.target_ref),
)
```

Use authority kind/frame metadata to choose `label:lexical` versus `label:name`; never branch on the source word or ref spelling.

- [ ] **Step 3: Tighten compiler and both independent verifier paths**

Compile `op:designation` only when the frame predicate is a reviewed label type and the roles contain exactly compatible `role:label_type`, `role:surface`, and `role:target` fillers. Update independent reconstruction to derive the same graph from context/program actions. Reject the legacy target-as-predicate encoding rather than translating it.

- [ ] **Step 4: Update active learning fixtures and expectations**

Change manually constructed designation expressions in `test_r3_learning_transaction.py` and affected owner fixtures to:

```python
SemanticApplication.create(
    operator="op:designation",
    predicate_ref="label:lexical",
    roles=(
        RoleBinding("role:label_type", GroundedReference("label:lexical")),
        RoleBinding("role:surface", LiteralValue("string", surface)),
        RoleBinding("role:target", GroundedReference(target_ref)),
    ),
)
```

Do not add a compatibility constructor or fallback decoder.

- [ ] **Step 5: Run the canonical-expression owner tests**

```powershell
python -m pytest tests/test_semantic_expressions.py tests/test_semantic_expression_compiler.py tests/test_exact_verifier.py tests/test_r2_verifier_reconstruction.py tests/test_r3_learning_transaction.py -q -p no:cacheprovider
```

Expected: corrected known designation paths pass; no Program ABI change is required.

- [ ] **Step 6: Commit the semantic hard cut**

```powershell
git add src/cemm_authoritative_hybrid/expressions.py src/cemm_authoritative_hybrid/proposal_context.py src/cemm_authoritative_hybrid/recursive_compiler.py src/cemm_authoritative_hybrid/verifier_reconstruction.py src/cemm_authoritative_hybrid/verifier.py tests/test_semantic_expression_compiler.py tests/test_exact_verifier.py tests/test_r2_verifier_reconstruction.py tests/test_r3_learning_transaction.py
git commit -m "fix(r2): canonicalize designation applications"
```

## Task 4: Emit one authenticated unresolved query frame

**Files:**

- Modify: `src/cemm_authoritative_hybrid/proposal_context.py`
- Modify: `tests/test_proposal_context_builder.py`

- [ ] **Step 1: Derive the frame only from authenticated construction evidence**

Add a bounded builder helper that requires all of:

- query orientation and interrogative binder evidence;
- the reviewed designation-query construction already present in the form lattice;
- one exact unknown anchor span;
- no admitted designation for that span/hypothesis; and
- an existing configured limit for frames, variables, and contribution candidates.

Create a literal contribution for the exact span, then one `UnresolvedDesignationFrame`, then its target `VariableSlot` pointing to the frame. The target variable's accepted kinds must be the bounded reviewed designation-target kind set, not only `entity`, `participant`, and `concept`.

- [ ] **Step 2: Preserve exact ownership and residual accounting**

Consume the unknown source unit once through the literal/frame path. Keep `what`, the predication binder, and query punctuation in their existing roles. Remove only the critical residual that the new exact structure now owns; do not globally downgrade unknown anchors or alter residual criticality.

- [ ] **Step 3: Prove the negative boundaries**

Tests must show:

- `What is zorbulate?` gets exactly one unresolved frame;
- `zorbulate is blue` does not;
- `Alice zorbulate Bob` does not;
- a surface already resolved by `DesignationIndex` does not get an unresolved frame; and
- no atom, designation fact, function-form row, or language-pack entry is created.

- [ ] **Step 4: Run builder tests**

```powershell
python -m pytest tests/test_proposal_context_builder.py -q -p no:cacheprovider
```

Expected: the former critical-residual diagnostic is green with exact literal/frame/variable assertions.

- [ ] **Step 5: Commit the builder slice**

```powershell
git add src/cemm_authoritative_hybrid/proposal_context.py tests/test_proposal_context_builder.py
git commit -m "feat(r2): represent unknown designation queries"
```

## Task 5: Compose and compile the unresolved frame with Program ABI 2

**Files:**

- Modify: `src/cemm_authoritative_hybrid/recursive_composer/_core.py`
- Modify: `src/cemm_authoritative_hybrid/recursive_composer/_expand.py`
- Modify: `src/cemm_authoritative_hybrid/recursive_composer/_search.py`
- Modify: `src/cemm_authoritative_hybrid/recursive_compiler.py`
- Modify: `tests/test_r2_recursive_proposer.py`
- Modify: `tests/test_r2_recursive_compiler.py`
- Modify: `tests/test_proposal_context_program_verifier_canary.py`

- [ ] **Step 1: Add unresolved-frame usage to bounded search state**

Track unresolved frame refs independently from selected designation refs. Grounded frames still require `select_designation`; unresolved frames must never fabricate or select one. Completion requires every emitted unresolved frame to be used exactly once while preserving existing depth/state/candidate bounds.

- [ ] **Step 2: Emit only existing Program ABI 2 actions**

For an unresolved frame, emit the existing actions in deterministic source order:

```text
instantiate_operator(frame.slot_ref)
bind_role(role:label_type, label:lexical)
bind_role(role:surface, literal contribution)
project_variable(role:target, target variable)
```

Bind/project the existing query binder using its current action path. Do not add an `unresolved_designation` program action.

- [ ] **Step 3: Compile the tagged frame to an ordinary application**

The compiler must resolve the frame variant by exact type and produce `SemanticApplication(op:designation, label_type_ref, roles)`. The unresolved-frame tag remains provenance only and is absent from persistent semantic identity.

- [ ] **Step 4: Add deterministic and bound tests**

Prove one canonical candidate, stable action order/ref, byte-identical repeated proposal, unchanged Program ABI/action-schema hash, no `select_designation`, and no increase to configured search bounds.

- [ ] **Step 5: Run composer/compiler owners**

```powershell
python -m pytest tests/test_r2_recursive_proposer.py tests/test_r2_recursive_compiler.py tests/test_proposal_context_program_verifier_canary.py -q -p no:cacheprovider
```

Expected: unresolved proposal composes and compiles; all Program ABI 2 canaries remain green.

- [ ] **Step 6: Commit without an ABI-vocabulary bump**

```powershell
git add src/cemm_authoritative_hybrid/recursive_composer src/cemm_authoritative_hybrid/recursive_compiler.py tests/test_r2_recursive_proposer.py tests/test_r2_recursive_compiler.py tests/test_proposal_context_program_verifier_canary.py
git commit -m "feat(r2): compose open designation queries"
```

## Task 6: Reconstruct and verify independently

**Files:**

- Modify: `src/cemm_authoritative_hybrid/verifier.py`
- Modify: `src/cemm_authoritative_hybrid/verifier_reconstruction.py`
- Modify: `tests/test_exact_verifier.py`
- Modify: `tests/test_r2_verifier_reconstruction.py`
- Modify: `tests/test_task7_program_verifier_supersessions.py`

- [ ] **Step 1: Validate action legality by exact frame variant**

For `ApplicationFrameSlot`, preserve the existing designation-selection checks. For `UnresolvedDesignationFrame`, require the exact label/literal/variable/binder refs, forbid `select_designation`, and reject extra/fabricated role bindings, source assignments, or target refs.

- [ ] **Step 2: Extend independent reconstruction**

Update `verifier_reconstruction.py` independently of the compiler so that it consumes `project_variable` and reconstructs the open target binding. Do not call compiler helpers or share a function that would make verification tautological.

- [ ] **Step 3: Recompute expected grounding and residuals**

Treat the reviewed label type as grounded, the literal as exact evidence, and the target as a bound variable. The unknown target is not missing grounding. Reconstruct source assignments and require zero critical residuals for the licensed span.

- [ ] **Step 4: Add adversarial tests**

Reject:

- unresolved frame plus fabricated designation selection;
- changed literal or span;
- changed label type;
- grounded target substituted for the variable without a designation fact;
- legacy target-as-predicate designation encoding; and
- an unresolved frame in a non-query construction.

- [ ] **Step 5: Run exact verifier owners**

```powershell
python -m pytest tests/test_exact_verifier.py tests/test_r2_verifier_reconstruction.py tests/test_task7_program_verifier_supersessions.py -q -p no:cacheprovider
```

Expected: authentic unresolved program selects; every mutation is rejected with a typed verification error.

- [ ] **Step 6: Commit the independent verifier**

```powershell
git add src/cemm_authoritative_hybrid/verifier.py src/cemm_authoritative_hybrid/verifier_reconstruction.py tests/test_exact_verifier.py tests/test_r2_verifier_reconstruction.py tests/test_task7_program_verifier_supersessions.py
git commit -m "feat(r2): verify open designation derivations"
```

## Task 7: Query the bounded designation index and preserve ambiguity

**Files:**

- Modify: `src/cemm_authoritative_hybrid/r3_cognition.py`
- Modify: `src/cemm_authoritative_hybrid/r3_kernel.py`
- Modify: `src/cemm_authoritative_hybrid/bootstrap.py`
- Modify: `tests/test_r3_recursive_query.py`
- Modify: `tests/test_authority_linker.py`

- [ ] **Step 1: Add query-local designation fact projection**

Implement `_authority_designation_fact_views(expression, authority, maximum)` beside the existing type/control projectors. It must activate only for structurally valid `op:designation` applications with a reviewed label-type predicate, exact literal `role:surface`, and bound-variable `role:target`.

Use only:

```python
authority.designations.facts_for_surface(surface, active_language)
```

Inject `active_language` from the activated form pack when `bootstrap.py` constructs `R3Kernel`, then pass it to `R3EvaluationOwner` and `QueryDecisionOwner`. Validate it as one nonempty bounded string. Do not default it in the query owner, add it to language-agnostic expression identity, infer it from a ref, or scan all languages. Update direct `R3Kernel`/`R3EvaluationOwner` fixtures to supply their explicit language.

Every `_FactView` must bind generation, designation fact ref, label type, exact surface, target ref, and reviewed placement.

- [ ] **Step 2: Preserve no-result and multiple-result semantics**

- Zero matching facts contributes no fact and yields `UNKNOWN`.
- One proof-bearing target yields `SUPPORTED` and an instantiated answer.
- More than one distinct target binding yields `PARTIAL` with `query:ambiguous_designation`; do not silently choose `support[0]`. Carry no arbitrary single binding in the partial `QueryResult`; retain every bounded alternative designation fact in `retrieval_refs` and the ambiguity blocker in the decision.
- Hitting `maximum` before exhausting indexed results yields `BUDGET_EXHAUSTED`, not `UNKNOWN` or `PARTIAL`.

Implement ambiguity classification at the query-result owner after exact evaluation, without changing generic conjunction/disjunction truth behavior for unrelated queries.

- [ ] **Step 3: Add known, unknown, polysemy, and bound tests**

Use the real `DesignationIndex` with explicit facts. Assert exact proof/source lineage for a known surface, empty bindings and `UNKNOWN` for `zorbulate`, `PARTIAL` plus all bounded alternative evidence for polysemy, and budget exhaustion when configured below the indexed result count.

Add two anti-regression cases required by the approved design:

- inject a newly reviewed synonym for an existing target through the designation owner and prove the next query resolves it without form-pack regeneration; and
- run equivalent designation-query constructions under two explicit synthetic form-pack languages, proving isomorphic operator/role/variable structure while each query retains its own language-specific literal and uses only that language's designation index partition.

- [ ] **Step 4: Prove the anti-scan property**

Use a spy/fake authority whose `atoms` iteration raises, while `designations.facts_for_surface` succeeds. Assert one indexed lookup for one designation query and no lookup for a non-designation query.

- [ ] **Step 5: Run query/authority owners**

```powershell
python -m pytest tests/test_r3_recursive_query.py tests/test_authority_linker.py -q -p no:cacheprovider
```

Expected: known/unknown/polysemous designation queries are exact and bounded; unrelated recursive queries remain green.

- [ ] **Step 6: Commit the Stage 10 owner**

```powershell
git add src/cemm_authoritative_hybrid/r3_cognition.py src/cemm_authoritative_hybrid/r3_kernel.py src/cemm_authoritative_hybrid/bootstrap.py tests/test_r3_recursive_query.py tests/test_authority_linker.py
git commit -m "feat(r3): evaluate indexed designation queries"
```

## Task 8: Close the exact vertical path without research or mutation

**Files:**

- Modify: `tests/test_r3_r4_predecessor_regressions.py`
- Modify only if an owner assertion proves necessary: `src/cemm_authoritative_hybrid/r3_response.py`

- [ ] **Step 1: Strengthen the closure assertion**

Extend `test_closure_unknown_designation_preserves_literal_and_unknown_action` to assert:

```python
assert result.evaluation.query_results[0].status is QueryStatus.UNKNOWN
assert result.evaluation.decision.action is DecisionAction.REQUEST_CLARIFICATION
assert response.discourse_action == "unknown"
assert response.response_expression == meaning.expression
assert type(result.effect_receipt) is NoEffectReceipt
assert before_world_facts == after_world_facts
assert runtime.authority.designations.for_surface("zorbulate", "en") == ()
assert "concept:zorbulate" not in runtime.authority.atoms
```

Also spy on the effect gateway/source adapters to prove that the R4 closure cycle performs no network/research invocation.

- [ ] **Step 2: Change response code only if the strengthened test identifies a response-owner defect**

The present `ResponseBuilder` already preserves `meaning.expression` for non-answer decisions and maps `UNKNOWN` to discourse action `unknown`. Do not add a special `zorbulate` template or UI fallback. If no response-owner failure occurs, leave `r3_response.py` untouched.

- [ ] **Step 3: Run the exact three-case closure**

```powershell
python -m pytest tests/test_r3_r4_predecessor_regressions.py::test_closure_known_definition_traverses_selected_semantic_path tests/test_r3_r4_predecessor_regressions.py::test_closure_unknown_designation_preserves_literal_and_unknown_action tests/test_r3_r4_predecessor_regressions.py::test_closure_invalid_program_receives_typed_verification_rejection -q -p no:cacheprovider
```

Expected: `3 passed`. This is the completion boundary for the code slice.

- [ ] **Step 4: Commit the vertical acceptance test**

```powershell
git add tests/test_r3_r4_predecessor_regressions.py src/cemm_authoritative_hybrid/r3_response.py
git commit -m "test(r4): close unknown designation vertical path"
```

If `r3_response.py` is unchanged, omit it from `git add`.

## Task 9: Run the fixed closure boundary and stop honestly

**Files:**

- Create: `docs/superpowers/progress/2026-09-03-r4-closure-slice-progress.md`
- Do not modify unrelated runtime owners in this task.

- [ ] **Step 1: Run the remaining fixed cases one at a time in declared order**

First add or use the existing parametrized closure harness without changing `_CLOSURE_CASES`. Run capability, history, fragment, negation, conflict, simulation, multiple-root, and permission cases sequentially. Do not reinterpret expected outcomes to make them pass.

- [ ] **Step 2: Stop at the first unrelated failure**

Record:

- case ref and source;
- earliest divergent phase/artifact;
- expected versus actual operator/roles/scope/action;
- whether the defect belongs to form, designation, affordance, graph assembly, verification, cognition, effect, or realization; and
- the next required design owner.

Do not repair that new owner under this plan. If all twelve pass, record that fact but do not claim R4.1 admission.

- [ ] **Step 3: Commit the truthful stop record**

```powershell
git add docs/superpowers/progress/2026-09-03-r4-closure-slice-progress.md
git commit -m "docs(r4): record designation closure outcome"
```

## Task 10: Update ABI/governance truth and validate without gate bloat

**Files:**

- Modify: `docs/ABI_REGISTRY.md`
- Modify: `docs/superpowers/specs/2026-09-03-unresolved-designation-and-research-handoff-design.md`
- Modify: `docs/DOCUMENT_AUTHORITY.json`
- Modify as mechanically required: `configs/validation_gates.json`
- Modify as mechanically required: test metadata blocks in changed R3/R4 tests
- Do not modify: R4 corpus/scenario/training artifacts

- [ ] **Step 1: Update active ABI truth**

Record Proposal Context ABI 2 and Semantic Expression ABI 2, their hard-cut reason, and the unchanged Program ABI 2. Remove stale statements that identify ABI 1 as active. Mark the approved design `implemented` only if Task 8 passed; otherwise mark it `implementation incomplete` with the exact blocker.

- [ ] **Step 2: Keep research explicitly downstream**

Ensure active routers state that online research remains a separately reviewed, observation-only EffectGateway handoff after the local R4 representation path. Do not add research adapters, URLs, dependencies, environment variables, or R5 training inputs.

- [ ] **Step 3: Refresh only affected authenticated test metadata**

```powershell
python scripts/refresh_r3_r4_test_metadata.py
python scripts/check_test_inventory.py --phase R2 --source-only
python scripts/check_test_inventory.py --phase R3 --source-only
python scripts/check_test_inventory.py --phase R4 --source-only
```

Expected: only changed test-function hashes are refreshed; each source-only inventory check passes. Add new owner nodes to existing R2/R3/R4 selectors only when their literal metadata role requires it. Do not add a selector tier or pytest process.

- [ ] **Step 4: Run focused owner suites in one pytest process**

```powershell
python -m pytest tests/test_proposal_context_abi1.py tests/test_proposal_context_builder.py tests/test_semantic_expressions.py tests/test_semantic_expression_compiler.py tests/test_r2_recursive_proposer.py tests/test_r2_recursive_compiler.py tests/test_exact_verifier.py tests/test_r2_verifier_reconstruction.py tests/test_r3_recursive_query.py tests/test_r3_learning_transaction.py tests/test_r3_r4_predecessor_regressions.py -q -p no:cacheprovider
```

Expected: all selected owner tests pass, except any later fixed closure case explicitly recorded as outside this slice must not be included as a passing claim.

- [ ] **Step 5: Run existing governance and static checks**

```powershell
python -m pytest tests/test_replay_governance.py tests/test_test_inventory.py -q -p no:cacheprovider
python -m compileall -q src/cemm_authoritative_hybrid scripts tests
python -m json.tool docs/DOCUMENT_AUTHORITY.json > $null
python -m pytest tests/test_replay_governance.py::test_document_authority_cryptographically_pins_ledger_anchors tests/test_replay_governance.py::test_document_authority_is_lf_normalized tests/test_replay_governance.py::test_document_authority_is_scoped_and_classifications_are_exact -q -p no:cacheprovider
git diff --check
```

Expected: all commands pass. Do not create a parallel document-authority validator.

- [ ] **Step 6: Run the existing phase selectors, not a new gate**

```powershell
python scripts/validate_mvp.py --tier phase --phase R2
python scripts/validate_mvp.py --tier phase --phase R3
python scripts/validate_mvp.py --tier phase --phase R4
```

Expected: R2/R3 technical owners pass. R4 retains its truthful admission status unless every pre-existing external/data prerequisite is independently satisfied; this code repair alone must not flip R4.1 or R5 green.

- [ ] **Step 7: Inspect scope and performance invariants**

```powershell
git diff --stat HEAD~10..HEAD
rg -n "concept:zorbulate|function_forms.*zorbulate|if .*zorbulate|research|wikipedia|wordnet" src data configs
git status --short
```

Expected: no invented atom, token-specific branch, research dependency, bulk data regeneration, or unexpected untracked artifact. Confirm the new query path performs one bounded designation-index lookup and does not scan authority atoms.

- [ ] **Step 8: Commit final contract alignment**

```powershell
git add docs/ABI_REGISTRY.md docs/superpowers/specs/2026-09-03-unresolved-designation-and-research-handoff-design.md docs/DOCUMENT_AUTHORITY.json configs/validation_gates.json tests
git commit -m "docs(r4): align designation repair contracts"
```

Stage only files actually changed. Do not commit generated caches, local databases, review UI output, R4 corpus bytes, or training artifacts.

## Completion evidence

The implementation is complete only when all of these are simultaneously true:

- `What is zorbulate?` reaches proposal, exact verification, cognition, no-effect, and response stages;
- the semantic graph contains the exact literal, reviewed label family, and target variable;
- the query returns `UNKNOWN`, not abstention, false, or a fabricated concept;
- a known designation uses the same expression shape and returns a proof-bearing target;
- polysemy returns bounded ambiguity rather than the first indexed target;
- plain unknown claims remain typed frontiers;
- Program ABI 2 and its action-schema hash are unchanged;
- Proposal Context ABI 2 and Semantic Expression ABI 2 reject legacy bytes;
- no network, research, authority write, world mutation, form-pack regeneration, or corpus rebuild occurs;
- existing R2/R3/R4 owner tests, inventory checks, document authority, static checks, and the exact three-case closure pass; and
- the next fixed closure result is recorded without expanding this plan's scope.

The next authorized decision after completion is either (a) design the newly exposed closure owner, or (b) if all fixed closure cases pass, prepare the separately reviewed mechanical R4.1 data correction and fresh admission. R5 remains blocked on authentic R4.1 admission, and self-research remains a distinct downstream design.

## Task 2 stop record: acyclic variable ownership required

**Historical status:** BLOCKED / not accepted at commit `2538c29`; the user has
since approved the amendment below. Repair at `aeaad1f` passed renewed spec and
quality review; this stop record is retained as historical evidence.
This was a plan-level representation defect,
not a new R4 closure case and not an authority-kind validation failure.

**Isolated branch:** `codex/unresolved-designation-r4`.
**Last implementation commit:** `cb6190247ce7377189bd861d0ab917e4b43d510d`.
Task 1 test commits are `ad3c5e0`, `a25c9ac`, and `d2bc519`.

The approved `UnresolvedDesignationFrame` hashes
`target_variable_slot_ref`. The existing `VariableSlot` hashes
`application_frame_ref`. Correct reciprocal linkage therefore requires a
cryptographic fixed point: repointing either record changes its hash and
invalidates the other. The ABI fixture currently avoids that cycle by borrowing
an unrelated grounded frame's `role:object` variable. Its successful round-trip
does not prove a usable unresolved designation frame.

The compiler and independent verifier reconstruction both resolve a variable's
application through `VariableSlot.application_frame_ref`; weakening that check
would conceal, not repair, the ownership defect.

**User-approved amendment, incorporated above:** preserve the existing
`VariableSlot -> application frame` ownership edge. Remove the unresolved
frame's hashed forward variable pointer and derive its target variable through
a bounded frame/role index. Require exactly one `role:target` variable with the
same construction and appropriate query evidence. Construct the frame first,
then its variable, then the context. Replace the borrowed-variable fixture with
an independently constructible unresolved-only context and reject unrelated
frame, wrong-role, and mismatched-construction variables.

No field may be silently omitted from hashing; no placeholder ref, fake
designation, permissive variable fallback, or relaxed compiler ownership check
is permitted. Proposal Context ABI 2 remains an unadmitted worktree change and
the builder does not emit the new frame. Main and remote branches are unchanged.

## Task 4 preflight: missing interrogative distinction

**Status:** evidence-backed design prerequisite; no form-pack or builder change
authorized by this record.

The current `FormResolver` and `data/languages/en/forms.json` were probed with
`What is zorbulate?`, `Where is zorbulate?`, and `Who is zorbulate?`. All three
produce the same non-surface evidence:

```text
query unit:       ((query, query),)
copula unit:      ((binder, copula),)
unknown unit:     ()
punctuation unit: ((discourse, question),)
construction:    query
```

`FormResolver._build_hypotheses` emits only the generic query construction for
these inputs. The pack's `label_designation_query` role-order schema requires
already grounded `participant` and `label_type` inputs; it does not license an
unknown span in these inputs. `_reviewed_application_role_bindings` matches
those schemas against existing designation kinds, not unresolved evidence.

Consequently, query orientation plus a copula and unknown anchor cannot prove
that the requested relation is a designation. Using those features alone would
misread a location question as a designation lookup. Checking the raw word in
the builder would instead violate the no-surface-dispatch contract.

The smallest recommended amendment is to preserve the necessary interrogative
distinction in reviewed closed-class form evidence and license one bounded
feature-based construction over the existing query, binder and unresolved
span. Add contrastive tests before builder emission. This requires a reviewed
form-source/pack change, which the current no-form-pack-regeneration boundary
does not authorize. It does not require a new kernel operator, semantic atom,
query engine, online research path or validation tier. Any approved form change
must preserve the existing realization contract and deterministic artifact
checks. Until then, retain the critical residual rather than guessing meaning.
