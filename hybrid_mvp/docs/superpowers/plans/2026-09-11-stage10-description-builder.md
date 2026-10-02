# Stage-10 Description Builder Implementation Plan

**Historical implementation evidence.** Replay status and exact admission
identities are derived only from `governance/replay_status.jsonl`. This completed
slice cannot authorize admission or reopen its checklist. The existing foundation
implementation plan owns current execution and remaining public-response work.

**Goal:** Reconstruct a bounded, source-authenticated semantic description from normalized claims through the existing Stage-10 query owner.

**Architecture:** Add a read-only `describe` method to `QueryDecisionOwner`. It accepts one canonical `DescriptionRequest`, its exact R3 `QueryResult`, and that result's complete query expression. Inside the already-held `r3_read_snapshot`, it validates request/result/expression/pin identity, retrieves only indexed active normalized claims for the requested target, verifies the legacy fact projection and generic claim lineage, reconstructs canonical answer meaning, and returns `DescriptionResult`. No table, public graph writer, response routing, learning branch, authority mutation, or realization change is part of this slice.

**Tech Stack:** Python 3.13, existing `SemanticStores` memory/SQLite backends, `SemanticExpression`, `Description ABI 1`, pytest.

**Current status (October 1):** This bounded builder slice is complete. Its
subsequent signed Proof Bundle linkage is also implemented and independently
reviewed under the existing foundation plan's Task 7 checkpoint. Do not repeat
either implementation from the historical pending statements below. Public
description-request projection, response realization and R4/R5 admission remain
unfinished and are tracked only in that governing checkpoint.

---

### Task 1: Prove the intended read-only description boundary

**Files:**

- Create: `tests/test_foundation_description_builder.py`
- Modify: `src/cemm_authoritative_hybrid/r3_cognition.py`

- [x] **Step 1: Write the first failing memory/SQLite test**

```python
@pytest.mark.parametrize("backend", ("memory", "sqlite"), ids=("memory", "sqlite"))
def test_description_reconstructs_reviewed_normalized_meaning(tmp_path, backend):
    stores, query_expression, query_result, request, claim = seeded_description_case(tmp_path, backend)
    try:
        owner = QueryDecisionOwner(stores, RuntimeConfig.release(), authority_for(stores))
        before = stores.revisions()
        result = owner.describe(request, query_result, query_expression)
        assert result.completeness is DescriptionCompleteness.SUFFICIENT
        assert result.fact_refs == (claim.fact_ref,)
        assert result.claim_refs == (claim.claim_ref,)
        assert result.definition_refs == (claim.application_ref,)
        assert result.answer_expression == SemanticExpression.create(
            applications=claim.applications, root_refs=(claim.application_ref,)
        )
        assert stores.revisions() == before
    finally:
        stores.close()
```

- [x] **Step 2: Run the test and observe RED**

Run: `C:\Python313\python.exe -m pytest -o addopts= -p no:cacheprovider tests/test_foundation_description_builder.py::test_description_reconstructs_reviewed_normalized_meaning -q`

Expected: FAIL because `QueryDecisionOwner.describe` does not exist.

- [x] **Step 3: Add the smallest owner method**

```python
def describe(self, request: DescriptionRequest, source: QueryResult,
             source_expression: SemanticExpression) -> DescriptionResult:
    _validate_description_request_source(request, source, source_expression)
    with self._stores.r3_read_snapshot(request.revision_pin):
        claims = active_application_claims_for_target(
            self._stores, request.target_ref,
            maximum=min(request.max_facts, DESCRIPTION_MAX_REFS),
            expected_pin=request.revision_pin,
        )
        return _description_result_from_claims(request, claims, self._stores)
```

The helpers must reject noncanonical artifacts, mismatched refs/pins, a target that is only query metadata, a non-reviewed claim, a missing/changed Fact, or a generic claim whose fact proof no longer matches source/decision/occurrence/placement/proof lineage. They must never inspect all world facts.

- [x] **Step 4: Run the first test and confirm GREEN**

Run: `C:\Python313\python.exe -m pytest -o addopts= -p no:cacheprovider tests/test_foundation_description_builder.py::test_description_reconstructs_reviewed_normalized_meaning -q`

Expected: `2 passed`.

### Task 2: Define exact terminal and conflict semantics

**Files:**

- Modify: `tests/test_foundation_description_builder.py`
- Modify: `src/cemm_authoritative_hybrid/r3_cognition.py`

- [x] **Step 1: Add failing terminal/conflict tests**

```python
def test_description_returns_missing_for_no_reviewed_descriptive_claim(...):
    assert owner.describe(request, query_result, query_expression).completeness is DescriptionCompleteness.MISSING

def test_description_returns_budget_exhausted_when_target_posting_overflows(...):
    assert owner.describe(one_fact_request, query_result, query_expression).completeness is DescriptionCompleteness.BUDGET_EXHAUSTED

def test_description_returns_budget_exhausted_when_answer_exceeds_max_depth(...):
    assert owner.describe(depth_limited_request, query_result, query_expression).completeness is DescriptionCompleteness.BUDGET_EXHAUSTED

def test_description_returns_budget_exhausted_when_proof_refs_exceed_abi_bound(...):
    assert owner.describe(request, query_result, query_expression).completeness is DescriptionCompleteness.BUDGET_EXHAUSTED

def test_description_preserves_support_and_deny_as_conflict(...):
    result = owner.describe(request, query_result, query_expression)
    assert result.completeness is DescriptionCompleteness.CONFLICT
    assert result.answer_expression.application_refs == (stored_application_ref,)
    assert result.claim_refs == (deny_claim_ref, support_claim_ref)
    assert result.fact_refs == (deny_fact_ref, support_fact_ref)
```

- [x] **Step 2: Run the terminal/conflict tests and observe RED**

Run: `C:\Python313\python.exe -m pytest -o addopts= -p no:cacheprovider tests/test_foundation_description_builder.py -k "missing or overflow or conflict" -q`

Expected: FAIL because the initial method has no exact terminal/conflict handling.

- [x] **Step 3: Implement bounded result construction**

```python
if not descriptive_claims:
    return DescriptionResult.create(..., completeness=DescriptionCompleteness.MISSING,
                                    answer_expression=None, fact_refs=(), definition_refs=(),
                                    claim_refs=(), source_refs=(), proof_refs=(),
                                    revision_pin=request.revision_pin)
```

For a support/deny conflict over the same stored application, return that one canonical application as a neutral answer expression and retain both signed fact, claim, source and proof chains. Set `CONFLICT` only for that typed truth condition. Do not add a polarity wrapper, clone/reparent the application, or discard a proposition: `SemanticExpression` is a single-parent forest, so two roots sharing a content-addressed application cannot be represented as one expression without loss or an invented semantic copy. Proof Bundle work, not the description graph, later owns per-stance derivation paths. Convert indexed max-plus-one overflow, depth excess, or ABI reference-budget excess to empty `BUDGET_EXHAUSTED`; do not drop evidence and claim `SUFFICIENT`.

- [x] **Step 4: Run the terminal/conflict tests and confirm GREEN**

Run: `C:\Python313\python.exe -m pytest -o addopts= -p no:cacheprovider tests/test_foundation_description_builder.py -k "missing or overflow or conflict" -q`

Expected: PASS.

### Task 3: Prove integrity, restart and governed metadata

**Files:**

- Modify: `tests/test_foundation_description_builder.py`
- Modify: `docs/superpowers/plans/2026-09-07-foundation-proof-implementation-plan.md`

- [x] **Step 1: Add failing integrity tests**

```python
def test_description_rejects_mismatched_query_or_target(...):
    with pytest.raises((TypeError, ValueError, StaleRevisionError)):
        owner.describe(request, unrelated_query_result, unrelated_expression)

def test_description_rejects_physically_changed_claim_projection(...):
    physically_replace_fact_below_public_boundary(stores, changed_fact)
    with pytest.raises(ValueError, match="description.*lineage|projection"):
        owner.describe(request, query_result, query_expression)

def test_description_restart_is_canonical_and_read_only(...):
    assert reopen_and_describe(...) == initial_result
```

- [x] **Step 2: Run the integrity tests and observe RED**

Run: `C:\Python313\python.exe -m pytest -o addopts= -p no:cacheprovider tests/test_foundation_description_builder.py -k "mismatched or changed or restart" -q`

Expected: FAIL until source/fact correspondence is verified during the pinned read.

- [x] **Step 3: Complete exact validation and metadata**

```python
fact = self._stores.world.get(claim.fact_ref)
if fact is None or not _normalized_fact_corresponds(fact, payload, claim.stance):
    raise ValueError("description claim projection is missing or changed")
if not _normalized_generic_lineage_corresponds(fact, claim_payload):
    raise ValueError("description claim lineage is invalid")
```

Add literal R4 test metadata with exact AST hashes and stable parameter ids. Mark only the Stage-10 builder checkpoint complete in the active plan; keep Proof Bundle, query/decision projection, public routing, production definitions, R5 realization, and R4 corpus repair unchecked.

- [x] **Step 4: Run focused verification**

Run: `C:\Python313\python.exe -m pytest -o addopts= -p no:cacheprovider tests/test_foundation_description_builder.py tests/test_foundation_descriptions.py tests/test_foundation_normalized_applications.py -q`

Expected: PASS.

- [x] **Step 5: Run integration verification**

Run: `C:\Python313\python.exe -m pytest -o addopts= -p no:cacheprovider tests/test_foundation_alias_publication.py tests/test_foundation_admitted_designations.py tests/test_foundation_query_authority_snapshot.py tests/test_foundation_query_retrieval.py tests/test_foundation_query_integrity.py tests/test_foundation_query_lineage.py tests/test_foundation_query_witness.py tests/test_persistence_recovery.py -q`

Expected: PASS with no public-response behavior change.

Completed as eight isolated compatibility runs because the desktop runner detaches
long aggregate pytest commands: 248 passed (76 alias publication, 52 admitted
designations, 6 authority snapshot, 18 retrieval, 62 integrity, 12 lineage,
10 witness, 12 recovery). No public-response behavior was changed.

## Review

The plan has one owner (`QueryDecisionOwner`), one storage input (existing indexed normalized claims), one temporary semantic output (`DescriptionResult`) and no new authority path. It rejects unsupported selection and integrity states instead of supplying a text answer. It does not add a normal-cycle gate: schema validation remains activation-only and description reads remain bounded by the request and existing index limits.
