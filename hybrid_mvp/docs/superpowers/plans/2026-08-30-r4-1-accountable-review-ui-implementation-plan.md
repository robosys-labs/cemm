# R4.1 Accountable Review UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a secure local HTML/JavaScript interface that lets an accountable reviewer complete and export the exact R4.1 selection input without editing raw JSON or creating a parallel semantic authority path.

**Architecture:** Extract the existing selection/applicability rules into one shared Python evaluator, then put a bounded resumable review session and loopback HTTP adapter around it. Serve build-free static HTML/CSS/JavaScript; Python owns all joins, transitions, persistence, impact previews and canonical export, while JavaScript only renders server projections and submits explicit reviewer actions.

**Tech Stack:** Python 3.11+ standard library, existing CEMM canonical/safe-I/O helpers, HTML5, CSS, browser-native JavaScript, pytest, Node `--check` for JavaScript syntax.

---

## Scope and file ownership

Create or modify only these implementation surfaces:

- `scripts/build_r4_1_review_selection.py` — shared partial/complete selection
  evaluator and final validation; remains the one selection-contract owner.
- `scripts/r4_1_review_session.py` — immutable indexes, working-state
  transitions, impact previews, persistence, status and export.
- `scripts/serve_r4_1_review.py` — CLI and loopback HTTP transport only.
- `scripts/r4_1_review_ui/index.html` — accessible page structure.
- `scripts/r4_1_review_ui/styles.css` — local responsive presentation.
- `scripts/r4_1_review_ui/app.js` — rendering, navigation and API calls only.
- `tests/test_r4_review_selection.py` — shared-evaluator parity tests.
- `tests/test_r4_review_session.py` — session, action, cohort, persistence and
  export tests.
- `tests/test_r4_review_server.py` — route, token, origin and request-boundary
  tests.
- `.gitignore` — ignore working state and local action journal, not the final
  reviewed selection.
- `artifacts/review_inputs/r4_1/README.md` — launch and review instructions.
- `docs/superpowers/plans/2026-08-30-r4-1-supervision-authoring-automation-plan.md`
  — record the UI checkpoint without claiming Task 10B expansion complete.

Do not modify runtime stages, authority data, language packs, activation,
release-gate configuration, schemas, proposal models, or final R4 source ABIs.

## Task 1: Extract one shared selection evaluator

**Files:**

- Modify: `scripts/build_r4_1_review_selection.py:225-539`
- Modify: `tests/test_r4_review_selection.py`

- [ ] **Step 1: Write failing partial-state and complete-state parity tests**

Add imports for `evaluate_selection` and `load_selection_context`, then add:

```python
def test_selection_evaluator_supports_partial_state_and_preserves_final_validation(
    tmp_path: Path,
) -> None:
    draft = tmp_path / "draft"
    build_review_worksheet_draft(repository_root=ROOT, output_root=draft)
    template_raw = build_selection_template_bytes(
        repository_root=ROOT,
        draft_root=draft,
    )
    template = json.loads(template_raw)
    context = load_selection_context(
        repository_root=ROOT,
        draft_root=draft,
        template_raw=template_raw,
    )

    partial = evaluate_selection(
        context=context,
        selection=template,
        require_complete=False,
    )
    assert partial.complete is False
    assert partial.active_case_refs == frozenset()
    assert partial.active_supervised_case_refs == frozenset()
    assert partial.unresolved_structural_count == 12
    assert partial.blocking_errors == ()

    reviewed = _complete_reviewed_fixture(template, context.decoded)
    complete = evaluate_selection(
        context=context,
        selection=reviewed,
        require_complete=True,
    )
    reviewed_raw = _canonical_bytes(reviewed)
    assert complete.complete is True
    assert validate_reviewed_selection_bytes(
        repository_root=ROOT,
        draft_root=draft,
        selection_raw=reviewed_raw,
    ) == reviewed
```

Move the existing reviewed-fixture construction in this test file into
`_complete_reviewed_fixture` and canonical serialization into
`_canonical_bytes`; do not change the fixture's decisions.

- [ ] **Step 2: Run the focused test and verify the missing API failure**

Run:

```powershell
python -m pytest tests/test_r4_review_selection.py -k evaluator -q
```

Expected: collection fails because `evaluate_selection` and
`load_selection_context` do not exist.

- [ ] **Step 3: Add exact context and evaluation result types**

Add these public types near the selection constants:

```python
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class SelectionContext:
    expected_template: Mapping[str, object]
    decoded: Mapping[str, Mapping[str, object]]
    structural_rows: Mapping[str, Mapping[str, object]]
    purpose_rows: Mapping[str, Mapping[str, object]]
    source_case_rows: Mapping[str, Mapping[str, object]]


@dataclass(frozen=True)
class SelectionEvaluation:
    complete: bool
    branch: str | None
    applicable_purpose_row_refs: frozenset[str]
    active_case_refs: frozenset[str]
    active_supervised_case_refs: frozenset[str]
    case_purposes: Mapping[str, str | None]
    unresolved_structural_count: int
    unresolved_purpose_count: int
    unresolved_recipe_count: int
    unresolved_designation_count: int
    blocking_rejection_refs: tuple[str, ...]
    blocking_errors: tuple[str, ...]
    stale_selection_refs: tuple[str, ...]
```

Implement `load_selection_context` by calling the existing template builder,
strict JSON decoder, draft tree reader, bound-input validator and repository
semantic validator once. Require `template_raw` to equal the freshly generated
template bytes and expose read-only mapping proxies.

- [ ] **Step 4: Extract applicability and completeness without weakening final validation**

Create:

```python
def evaluate_selection(
    *,
    context: SelectionContext,
    selection: Mapping[str, object],
    require_complete: bool,
) -> SelectionEvaluation:
    """Evaluate exact mutable fields against one authenticated selection context."""
```

Move these rules from `validate_reviewed_selection_bytes` into the evaluator:

- immutable projection matching;
- structural option lookup;
- branch/generator coherence when both are selected;
- candidate-scenario and restart-diagnostic applicability;
- purpose-row applicability;
- duplicate group and holdout ownership;
- purpose counts and denominators;
- purpose-local recipe partitions;
- exact designation decisions; and
- blocking rejection discovery.

When `require_complete=False`, unresolved applicable fields increment counters
instead of raising. Invalid option refs, forged identities and malformed values
still raise immediately. Selected rows that became inapplicable are returned as
`stale_selection_refs`, and a selected branch/patch contradiction is returned
as a blocking error so the session can preview the exact repair. When
`require_complete=True`, stale selections and blocking errors raise while every
current final-validation failure condition and message category is preserved.
Until all 12 structural rows are selected coherently, return `branch=None`,
empty active-case sets, and no applicable downstream rows; this enforces the UI
phase order without guessing a branch or candidate disposition.

Rewrite `validate_reviewed_selection_bytes` to load the context, require
`selection_state == "reviewed"`, validate canonical reviewer refs, call
`evaluate_selection(..., require_complete=True)`, require `complete`, and then
perform the existing canonical-byte equality check.

- [ ] **Step 5: Run parity, hostile-input and broader authoring tests**

Run:

```powershell
python -m pytest tests/test_r4_review_selection.py -q
python -m pytest tests/test_r4_authoring_pipeline.py tests/test_r4_authoring.py tests/test_r4_purpose_contracts.py -q
python -m ruff check scripts/build_r4_1_review_selection.py tests/test_r4_review_selection.py
```

Expected: all tests pass; the exact selection template identity and SHA-256 are
unchanged because evaluator source is not a template identity input.

- [ ] **Step 6: Commit the shared contract owner**

```powershell
git add scripts/build_r4_1_review_selection.py tests/test_r4_review_selection.py
git commit -m "refactor(r4): expose selection evaluation"
```

## Task 2: Build immutable review indexes and browser projections

**Files:**

- Create: `scripts/r4_1_review_session.py`
- Create: `tests/test_r4_review_session.py`

- [ ] **Step 1: Write failing bootstrap and exception-index tests**

```python
@pytest.fixture
def review_paths(tmp_path: Path) -> ReviewPaths:
    draft = tmp_path / "draft"
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    build_review_worksheet_draft(repository_root=ROOT, output_root=draft)
    template_path = inputs / "SELECTION_TEMPLATE.json"
    template_path.write_bytes(
        build_selection_template_bytes(repository_root=ROOT, draft_root=draft)
    )
    return ReviewPaths(
        repository_root=ROOT,
        draft_root=draft,
        template_path=template_path,
        working_path=inputs / "SELECTION_WORKING.json",
        journal_path=inputs / "REVIEW_ACTIONS.jsonl",
        export_path=inputs / "SELECTION.json",
    )


def test_session_bootstrap_indexes_exact_current_review_inventory(
    review_paths: ReviewPaths,
) -> None:
    session = ReviewSession.open(review_paths)
    bootstrap = session.bootstrap()

    assert bootstrap["inventory"] == {
        "structural": 12,
        "purpose": 600,
        "recipe_family": 56,
        "designation": 388,
    }
    assert bootstrap["designation_risk_counts"]["intersecting_case"] == 12
    assert bootstrap["designation_risk_counts"]["overlap_pair"] == 13
    assert bootstrap["designation_risk_counts"]["multi_unit_case"] == 21
    assert bootstrap["designation_risk_counts"]["exact_empty"] == 61
    assert bootstrap["state_revision"] == 0
    assert bootstrap["selection_template_ref"].startswith(
        "r4_authoring_selection_template:"
    )


def test_routine_designation_cohorts_exclude_every_high_risk_case(
    review_paths: ReviewPaths,
) -> None:
    session = ReviewSession.open(review_paths)
    exception_refs = session.indexes.designation_exception_case_refs
    cohort_members = {
        case_ref
        for cohort in session.indexes.routine_designation_cohorts.values()
        for case_ref in cohort
    }
    assert exception_refs.isdisjoint(cohort_members)
    assert exception_refs | cohort_members == set(
        session.indexes.designation_rows_by_case
    )
```

- [ ] **Step 2: Run tests and verify the module import failure**

```powershell
python -m pytest tests/test_r4_review_session.py -q
```

Expected: collection fails because `scripts.r4_1_review_session` is absent.

- [ ] **Step 3: Implement paths, immutable indexes and session startup**

Define:

```python
@dataclass(frozen=True)
class ReviewPaths:
    repository_root: Path
    draft_root: Path
    template_path: Path
    working_path: Path
    journal_path: Path
    export_path: Path


@dataclass(frozen=True)
class ReviewIndexes:
    structural_rows_by_ref: Mapping[str, Mapping[str, object]]
    purpose_rows_by_ref: Mapping[str, Mapping[str, object]]
    source_cases_by_ref: Mapping[str, Mapping[str, object]]
    proposal_families_by_ref: Mapping[str, Mapping[str, object]]
    designation_rows_by_case: Mapping[str, Mapping[str, object]]
    purpose_cohorts: Mapping[str, tuple[str, ...]]
    designation_exception_case_refs: frozenset[str]
    routine_designation_cohorts: Mapping[str, tuple[str, ...]]
    overlap_pair_count: int


class ReviewSession:
    @classmethod
    def open(cls, paths: ReviewPaths) -> "ReviewSession":
        template_raw = _read_regular(
            paths.template_path,
            maximum=MAX_WORKSHEET_BYTES,
            owner="review UI selection template",
        )
        context = load_selection_context(
            repository_root=paths.repository_root,
            draft_root=paths.draft_root,
            template_raw=template_raw,
        )
        state = dict(context.expected_template)
        indexes = build_review_indexes(context)
        return cls(paths=paths, context=context, state=state, indexes=indexes)
```

Use `MappingProxyType` for every published mapping and canonical sorted tuples
for every cohort. Store exact decoded source rows; do not derive meaning from
surface text or internal ref spelling.

- [ ] **Step 4: Implement designation risk classification and routine signatures**

Classify one case as exceptional when it has an empty candidate set, a binding
using more than one unit, two different bindings whose character spans overlap,
or one exact span with multiple target/fact pairs. Count undirected overlapping
pairs once with index-ordered combinations.

Routine cohort signatures contain only reviewed display evidence:

```python
signature_material = [
    {
        "surface": binding["surface"],
        "start": binding["start"],
        "end": binding["end"],
        "designation_fact_ref": binding["designation_fact_ref"],
        "candidate_target_ref": binding["candidate_target_ref"],
        "unit_count": len(binding["unit_refs"]),
    }
    for binding in row["candidate_bindings"]
]
cohort_ref = stable_ref(
    "review_ui_designation_cohort",
    {"signature": signature_material},
)
```

Never include case-local binding refs in the grouping key and never emit the
cohort ref into `SELECTION.json`.

- [ ] **Step 5: Add bounded projection methods**

Implement `bootstrap()` and:

```python
def items(
    self,
    *,
    section: str,
    state_filter: str,
    query: str,
    offset: int,
    limit: int,
) -> Mapping[str, object]:
```

Admit sections `structural`, `purpose`, `recipe`, and `designation`; filters
`all`, `unresolved`, `completed`, `rejected`, and `exception`; query length at
most 256; offset at most 4096; and limit from 1 through 100. Return only
server-created projections, exact refs, human-readable source fields, allowed
options, current values and total/offset/limit metadata.

- [ ] **Step 6: Run tests and commit**

```powershell
python -m pytest tests/test_r4_review_session.py -q
python -m ruff check scripts/r4_1_review_session.py tests/test_r4_review_session.py
git add scripts/r4_1_review_session.py tests/test_r4_review_session.py
git commit -m "feat(r4): index accountable review evidence"
```

## Task 3: Add safe resumable working state and audit journal

**Files:**

- Modify: `scripts/r4_1_review_session.py`
- Modify: `tests/test_r4_review_session.py`
- Modify: `.gitignore`

- [ ] **Step 1: Write failing resume, stale-state and persistence tests**

```python
def test_working_state_round_trips_and_binds_exact_template(
    review_paths: ReviewPaths,
) -> None:
    session = ReviewSession.open(review_paths)
    session.set_reviewers(("reviewer:son",))
    resumed = ReviewSession.open(review_paths)
    assert resumed.state["reviewer_refs"] == ["reviewer:son"]
    assert resumed.state_revision == 0


def test_stale_working_state_is_retained_and_rejected(
    review_paths: ReviewPaths,
) -> None:
    session = ReviewSession.open(review_paths)
    session.set_reviewers(("reviewer:son",))
    original = review_paths.working_path.read_bytes()
    value = json.loads(original)
    value["selection_template_ref"] = "r4_authoring_selection_template:" + "0" * 24
    review_paths.working_path.write_bytes(_canonical_bytes(value))

    with pytest.raises(ValueError, match="stale working selection"):
        ReviewSession.open(review_paths)
    assert review_paths.working_path.exists()
```

Add hostile link/reparse-point, existing-directory, interrupted replace and
journal identity-change cases using the repository's existing Windows-safe test
patterns.

- [ ] **Step 2: Run tests and verify resume is absent**

```powershell
python -m pytest tests/test_r4_review_session.py -k "working or stale or journal" -q
```

Expected: failures because session persistence is not implemented.

- [ ] **Step 3: Implement exact working-state envelopes and atomic persistence**

Keep working state in the selection shape and keep `selection_state` equal to
`unresolved`. Validate immutable fields and partial mutable values with the
shared evaluator before accepting resume.

Implement:

```python
def _commit_working_state(
    self,
    *,
    candidate_state: Mapping[str, object],
    action: Mapping[str, object],
) -> None:
    raw = _json_bytes(candidate_state)
    _atomic_replace_regular(
        path=self.paths.working_path,
        raw=raw,
        maximum=MAX_WORKSHEET_BYTES,
        owner="review UI working selection",
    )
    self._state = copy.deepcopy(candidate_state)
    self.state_revision += 1
    try:
        _append_journal_entry(
            path=self.paths.journal_path,
            entry={
                "schema": "cemm-r4-review-ui-action-v1",
                "selection_template_ref": self._state["selection_template_ref"],
                "selection_template_sha256": self.template_sha256,
                "action_sequence": self.state_revision,
                "reviewer_refs": list(self._reviewers()),
                "action": dict(action),
                "state_sha256": hashlib.sha256(raw).hexdigest(),
                "recorded_at_ns": time.time_ns(),
            },
        )
    except (OSError, TypeError, ValueError) as exc:
        self.audit_warning = f"action journal unavailable: {type(exc).__name__}"
```

`_atomic_replace_regular` must validate the parent identity before and after,
create a same-parent exclusive temporary file, fsync it, recheck retained bytes,
and use `os.replace`. Refuse existing links, reparse points, directories, files
with more than one hard link, and output identity changes. Journal entries are
canonical JSON Lines capped at 128 KiB each. Cap the complete journal at 64 MiB
and 8,192 entries, rejecting append before either limit would be exceeded.

The working selection is the sole resume source and `state_revision` is local
to one server process, resetting to zero on a successful resume. Append the
non-authoritative journal only after the working file is safely replaced. A
journal append failure leaves the valid working selection in place, returns a
visible audit warning, and can be retried; it never rolls back or authorizes a
selection. A malformed existing journal is preserved, disables further journal
append, and reports a warning without invalidating an otherwise exact working
selection.

Expose `state` as a deep-copied read-only mapping so tests and HTTP projections
cannot mutate the session outside preview/apply or reviewer actions.

- [ ] **Step 4: Add reviewer mutation and ignore only local work products**

Implement `set_reviewers(refs: tuple[str, ...])` using
`exact_reviewer_refs(refs, maximum=128)`. Persist it as one action and increment
the revision only after the working file succeeds. Return the visible audit
warning when journal append is unavailable.

Append to `.gitignore`:

```gitignore
artifacts/review_inputs/r4_1/SELECTION_WORKING.json
artifacts/review_inputs/r4_1/REVIEW_ACTIONS.jsonl
```

Do not ignore `SELECTION.json`.

- [ ] **Step 5: Run tests and commit**

```powershell
python -m pytest tests/test_r4_review_session.py -k "working or stale or journal or reviewer" -q
python -m ruff check scripts/r4_1_review_session.py tests/test_r4_review_session.py
git add .gitignore scripts/r4_1_review_session.py tests/test_r4_review_session.py
git commit -m "feat(r4): persist resumable review sessions"
```

## Task 4: Implement structural and purpose impact previews

**Files:**

- Modify: `scripts/r4_1_review_session.py`
- Modify: `tests/test_r4_review_session.py`

- [ ] **Step 1: Write failing structural dependency and stale-preview tests**

```python
def _option_ref(row: Mapping[str, object], label: str) -> str:
    return next(
        option["option_ref"]
        for option in row["options"]
        if option["label"] == label
    )


@pytest.fixture
def started_session(review_paths: ReviewPaths) -> ReviewSession:
    session = ReviewSession.open(review_paths)
    session.set_reviewers(("reviewer:son",))
    return session


def _select_all_structural_approvals(session: ReviewSession) -> None:
    labels = {
        "composed_expression_proposal": "approve_exact_proposal",
        "conflict_preservation": "preserve_as_alternatives",
        "legacy_conditional": "retain_typed_proposal_gaps",
        "restart_diagnostic": "approve_diagnostic_only",
        "generator_patch": "retain_typed_proposal_gaps",
    }
    for row in session.indexes.structural_rows_by_ref.values():
        preview = session.preview(
            ReviewAction.structural(
                row_ref=row["row_ref"],
                selected_option_ref=_option_ref(row, labels[row["row_kind"]]),
            )
        )
        session.apply(
            preview_hash=preview.preview_hash,
            expected_revision=preview.state_revision,
        )


def test_structural_change_previews_and_clears_exact_dependent_rows(
    started_session: ReviewSession,
) -> None:
    _select_all_structural_approvals(started_session)
    candidate_case = next(
        row
        for row in started_session.indexes.source_cases_by_ref.values()
        if row["universe"] == "candidate"
    )
    membership = next(
        row
        for row in started_session.indexes.purpose_rows_by_ref.values()
        if row["row_kind"] == "membership"
        and row["source_case_ref"] == candidate_case["case_ref"]
    )
    membership_preview = started_session.preview(
        ReviewAction.purpose(
            row_refs=(membership["row_ref"],),
            option_label="direct_train",
        )
    )
    started_session.apply(
        preview_hash=membership_preview.preview_hash,
        expected_revision=membership_preview.state_revision,
    )
    proposal = next(
        row
        for row in started_session.indexes.structural_rows_by_ref.values()
        if row["row_kind"] == "composed_expression_proposal"
        and row["subject_ref"] == candidate_case["scenario_ref"]
    )

    preview = started_session.preview(
        ReviewAction.structural(
            row_ref=proposal["row_ref"],
            selected_option_ref=_option_ref(proposal, "reject_exact_proposal"),
        )
    )
    assert preview.requires_clear_confirmation is True
    assert preview.cleared_refs

    result = started_session.apply(
        preview_hash=preview.preview_hash,
        expected_revision=preview.state_revision,
    )
    assert set(result["cleared_refs"]) == set(preview.cleared_refs)
    assert started_session.evaluation().blocking_errors == ()


def test_stale_preview_cannot_apply(started_session: ReviewSession) -> None:
    row = next(iter(started_session.indexes.structural_rows_by_ref.values()))
    preview = started_session.preview(
        ReviewAction.structural(
            row_ref=row["row_ref"],
            selected_option_ref=row["options"][0]["option_ref"],
        )
    )
    started_session.set_reviewers(("reviewer:son", "reviewer:second"))
    with pytest.raises(ValueError, match="stale preview"):
        started_session.apply(
            preview_hash=preview.preview_hash,
            expected_revision=preview.state_revision,
        )
```

Add branch-change coverage proving an incompatible existing generator-patch
selection appears in the clear list and cannot survive the action.

- [ ] **Step 2: Run tests and verify action APIs are absent**

```powershell
python -m pytest tests/test_r4_review_session.py -k "structural or stale_preview" -q
```

Expected: failures because `ReviewAction`, `preview` and `apply` do not exist.

- [ ] **Step 3: Implement exact action and preview types**

```python
@dataclass(frozen=True)
class ReviewAction:
    action_kind: str
    target_refs: tuple[str, ...]
    selected_value: object

    @classmethod
    def structural(cls, *, row_ref: str, selected_option_ref: str) -> "ReviewAction":
        return cls("structural", (row_ref,), selected_option_ref)


@dataclass(frozen=True)
class ActionPreview:
    preview_hash: str
    state_revision: int
    action: ReviewAction
    affected_refs: tuple[str, ...]
    cleared_refs: tuple[str, ...]
    requires_clear_confirmation: bool
    resulting_counts: Mapping[str, int]
```

`preview` copies the bounded selection state, applies the requested value to
the copy, calculates applicability with the shared evaluator, clears only rows
that changed from applicable to inapplicable, reevaluates, and hashes the exact
action, current revision, affected refs, clear refs and resulting state hash.
Cache at most one preview per session.

Reject every preview until at least one canonical reviewer ref has been saved;
anonymous browser activity may inspect evidence but cannot mutate review state.

`apply` accepts only the cached preview hash and matching revision, atomically
persists one state transition and then discards the preview. It never accepts a
browser-supplied clear list.

- [ ] **Step 4: Add purpose individual and exact-cohort actions**

Add constructors:

```python
@classmethod
def purpose(
    cls,
    *,
    row_refs: tuple[str, ...],
    option_label: str,
) -> "ReviewAction":
    return cls("purpose", row_refs, option_label)
```

For each target row, resolve `option_label` to its row-local exact option ref.
Require sorted unique target refs, one row kind, at most 512 rows, and a label
present on every member. Resolve all refs against server indexes and show the
complete exact set again in the impact preview, so a browser-selected subset is
never applied without confirmation. Reject branch-inapplicable rows and mixed
source classifications that cannot share the selected option. Show resulting
purpose counts, holdout conflicts and denominator shortfalls in the preview;
invalid ownership still fails immediately.

- [ ] **Step 5: Test purpose ownership and commit**

```powershell
python -m pytest tests/test_r4_review_session.py -k "structural or purpose or preview" -q
python -m ruff check scripts/r4_1_review_session.py tests/test_r4_review_session.py
git add scripts/r4_1_review_session.py tests/test_r4_review_session.py
git commit -m "feat(r4): preview accountable review actions"
```

## Task 5: Implement recipe and designation review actions

**Files:**

- Modify: `scripts/r4_1_review_session.py`
- Modify: `tests/test_r4_review_session.py`

- [ ] **Step 1: Write failing purpose-scoped recipe tests**

```python
def _apply_preview(session: ReviewSession, action: ReviewAction) -> None:
    preview = session.preview(action)
    session.apply(
        preview_hash=preview.preview_hash,
        expected_revision=preview.state_revision,
    )


def _complete_purpose_selections(session: ReviewSession) -> None:
    supervised = [
        row
        for row in session.indexes.purpose_rows_by_ref.values()
        if row["row_kind"] == "membership"
        and row["source_classification"] != "restart_diagnostic_candidate"
    ]
    purposes = ("train", "selection", "calibration", "frozen_test")
    for index, purpose in enumerate(purposes):
        refs = tuple(
            sorted(
                row["row_ref"]
                for row_index, row in enumerate(supervised)
                if row_index % len(purposes) == index
            )
        )
        _apply_preview(
            session,
            ReviewAction.purpose(row_refs=refs, option_label=f"direct_{purpose}"),
        )
    for row_kind, option_label in (
        ("membership", "approve_diagnostic_only"),
        ("duplicate_group", "reject_group"),
        ("challenge_holdout", "not_a_holdout"),
        ("denominator", "minimum_one_each"),
    ):
        refs = tuple(
            sorted(
                row["row_ref"]
                for row in session.indexes.purpose_rows_by_ref.values()
                if row["row_kind"] == row_kind
                and any(
                    option["label"] == option_label for option in row["options"]
                )
            )
        )
        _apply_preview(
            session,
            ReviewAction.purpose(row_refs=refs, option_label=option_label),
        )


@pytest.fixture
def purpose_complete_session(started_session: ReviewSession) -> ReviewSession:
    _select_all_structural_approvals(started_session)
    _complete_purpose_selections(started_session)
    return started_session


def _family_members(session: ReviewSession, family_ref: str) -> tuple[str, ...]:
    return tuple(
        session.indexes.proposal_families_by_ref[family_ref]["member_case_refs"]
    )


def _recipe_for(
    state: Mapping[str, object],
    *,
    family_ref: str,
    purpose: str,
) -> Mapping[str, object]:
    family = next(
        row
        for row in state["proposal_recipe_selections"]
        if row["family_ref"] == family_ref
    )
    return next(
        row for row in family["purpose_recipes"] if row["purpose"] == purpose
    )


def _designation_selection(
    state: Mapping[str, object],
    case_ref: str,
) -> Mapping[str, object]:
    return next(
        row
        for row in state["designation_selections"]
        if row["source_case_ref"] == case_ref
    )


def test_recipe_action_uses_exact_selected_purpose_partition(
    purpose_complete_session: ReviewSession,
) -> None:
    evaluation = purpose_complete_session.evaluation()
    family_ref = next(
        ref
        for ref in purpose_complete_session.indexes.proposal_families_by_ref
        if any(
            evaluation.case_purposes[case_ref] == "train"
            for case_ref in _family_members(purpose_complete_session, ref)
        )
    )
    preview = purpose_complete_session.preview(
        ReviewAction.recipe(
            family_ref=family_ref,
            purpose="train",
            decision="approve",
            reviewed_parameters={"review_basis": "exact_source_family"},
        )
    )
    purpose_complete_session.apply(
        preview_hash=preview.preview_hash,
        expected_revision=preview.state_revision,
    )
    recipe = _recipe_for(
        purpose_complete_session.state,
        family_ref=family_ref,
        purpose="train",
    )
    assert recipe["member_case_refs"] == sorted(
        case_ref
        for case_ref in _family_members(purpose_complete_session, family_ref)
        if purpose_complete_session.evaluation().case_purposes[case_ref] == "train"
    )
```

Add rejection, parameter-size, duplicate-purpose, absent-partition and
cross-purpose hostile cases.

- [ ] **Step 2: Write failing designation cohort and exception tests**

```python
def test_routine_designation_cohort_expands_to_exact_case_local_bindings(
    purpose_complete_session: ReviewSession,
) -> None:
    cohort_ref, case_refs = next(
        iter(purpose_complete_session.indexes.routine_designation_cohorts.items())
    )
    preview = purpose_complete_session.preview(
        ReviewAction.designation_cohort(
            cohort_ref=cohort_ref,
            decision="approve_candidate_bindings",
        )
    )
    result = purpose_complete_session.apply(
        preview_hash=preview.preview_hash,
        expected_revision=preview.state_revision,
    )
    assert set(result["affected_refs"]) == set(case_refs)
    for case_ref in case_refs:
        row = _designation_selection(purpose_complete_session.state, case_ref)
        assert row["approved_binding_refs"] == row["candidate_binding_refs"]


def test_exception_designation_rejects_cohort_action(
    purpose_complete_session: ReviewSession,
) -> None:
    case_ref = next(
        iter(purpose_complete_session.indexes.designation_exception_case_refs)
    )
    with pytest.raises(ValueError, match="individual review"):
        purpose_complete_session.preview(
            ReviewAction.designation_cases(
                case_refs=(case_ref,),
                decision="approve_candidate_bindings",
                individual=False,
            )
        )
```

- [ ] **Step 3: Run tests and verify missing action support**

```powershell
python -m pytest tests/test_r4_review_session.py -k "recipe or designation" -q
```

Expected: failures because recipe and designation actions are not admitted.

- [ ] **Step 4: Implement exact recipe partitions and designation expansion**

Add `ReviewAction.recipe`, `designation_cohort`, and `designation_cases` class
methods. Recipe preview derives member refs only from the current evaluator's
case-purpose mapping and replaces at most one purpose entry inside the exact
family selection.

Designation decisions map as follows:

```python
def _designation_value(
    selection: Mapping[str, object],
    decision: str,
) -> tuple[str, list[str] | None]:
    candidates = selection["candidate_binding_refs"]
    if decision == "approve_candidate_bindings" and candidates:
        return decision, list(candidates)
    if decision == "approve_exact_empty" and not candidates:
        return decision, []
    if decision == "reject":
        return decision, None
    raise ValueError("designation decision is incompatible with its exact candidate set")
```

Require every exceptional case to use an individual action. A routine cohort
action resolves the cohort ref from server indexes and expands it to exact
case-local decisions. Record a blocking rejection ref for rejected recipes or
designations.

- [ ] **Step 5: Add review-complete and authoring-ready status**

`bootstrap()` and every apply response must include:

```python
{
    "review_complete": evaluation.complete,
    "authoring_ready": evaluation.complete
    and not evaluation.blocking_rejection_refs,
    "blocking_rejection_refs": list(evaluation.blocking_rejection_refs),
}
```

These are display statuses only. Do not add a schema, activation gate, release
gate or import-time validator.

- [ ] **Step 6: Run tests and commit**

```powershell
python -m pytest tests/test_r4_review_session.py -q
python -m ruff check scripts/r4_1_review_session.py tests/test_r4_review_session.py
git add scripts/r4_1_review_session.py tests/test_r4_review_session.py
git commit -m "feat(r4): review recipe and designation cohorts"
```

## Task 6: Add canonical safe export

**Files:**

- Modify: `scripts/build_r4_1_review_selection.py`
- Modify: `scripts/r4_1_review_session.py`
- Modify: `tests/test_r4_review_selection.py`
- Modify: `tests/test_r4_review_session.py`

- [ ] **Step 1: Write failing export and overwrite-policy tests**

```python
def _complete_recipes_and_designations(session: ReviewSession) -> None:
    evaluation = session.evaluation()
    for family_ref, family in session.indexes.proposal_families_by_ref.items():
        for purpose in ("train", "selection", "calibration", "frozen_test"):
            if any(
                evaluation.case_purposes[case_ref] == purpose
                for case_ref in family["member_case_refs"]
            ):
                _apply_preview(
                    session,
                    ReviewAction.recipe(
                        family_ref=family_ref,
                        purpose=purpose,
                        decision="approve",
                        reviewed_parameters={
                            "review_basis": "exact_source_family"
                        },
                    ),
                )
    for cohort_ref in session.indexes.routine_designation_cohorts:
        _apply_preview(
            session,
            ReviewAction.designation_cohort(
                cohort_ref=cohort_ref,
                decision="approve_candidate_bindings",
            ),
        )
    for case_ref in sorted(session.indexes.designation_exception_case_refs):
        selection = _designation_selection(session.state, case_ref)
        decision = (
            "approve_candidate_bindings"
            if selection["candidate_binding_refs"]
            else "approve_exact_empty"
        )
        _apply_preview(
            session,
            ReviewAction.designation_cases(
                case_refs=(case_ref,),
                decision=decision,
                individual=True,
            ),
        )


@pytest.fixture
def complete_session(purpose_complete_session: ReviewSession) -> ReviewSession:
    _complete_recipes_and_designations(purpose_complete_session)
    assert purpose_complete_session.evaluation().complete is True
    return purpose_complete_session


def test_complete_session_exports_canonical_validated_selection(
    complete_session: ReviewSession,
) -> None:
    receipt = complete_session.export()
    raw = complete_session.paths.export_path.read_bytes()
    assert receipt["sha256"] == hashlib.sha256(raw).hexdigest()
    assert receipt["byte_length"] == len(raw)
    assert validate_reviewed_selection_bytes(
        repository_root=complete_session.paths.repository_root,
        draft_root=complete_session.paths.draft_root,
        selection_raw=raw,
    )["selection_state"] == "reviewed"


def test_export_is_exact_noop_or_refuses_different_existing_bytes(
    complete_session: ReviewSession,
) -> None:
    first = complete_session.export()
    second = complete_session.export()
    assert second == first
    complete_session.paths.export_path.write_bytes(b"{}\n")
    with pytest.raises(ValueError, match="different existing export"):
        complete_session.export()
```

Add incomplete session, stale template, link/reparse point, parent identity
change and interrupted-write tests.

- [ ] **Step 2: Run tests and verify export is absent**

```powershell
python -m pytest tests/test_r4_review_session.py -k export -q
```

Expected: failures because `ReviewSession.export` does not exist.

- [ ] **Step 3: Add one reusable safe exact-output writer**

In `build_r4_1_review_selection.py`, extract the existing exclusive-write
safety logic into:

```python
def write_exact_output(
    *,
    output_path: Path,
    raw: bytes,
    owner: str,
    allow_identical_existing: bool,
) -> None:
```

Preserve the current template writer's parent-identity, exclusive create,
retained-byte and identity-safe cleanup behavior. If
`allow_identical_existing=True`, return only when an existing trusted regular
single-link file has exactly `raw`; reject every differing existing object.
Rewrite `write_selection_template` to call this helper so its behavior remains
covered by existing tests.

- [ ] **Step 4: Implement canonical final export**

`ReviewSession.export` must:

1. re-read and verify the exact template and draft identities;
2. deep-copy working state;
3. set `selection_state` to `reviewed`;
4. require canonical reviewer refs;
5. serialize with `_json_bytes`;
6. call `validate_reviewed_selection_bytes` on those exact bytes;
7. call `write_exact_output(..., allow_identical_existing=True)`; and
8. return an immutable receipt containing path, byte length, SHA-256,
   `review_complete`, `authoring_ready`, and blocking rejection refs.

Do not modify working state or journal during export.

- [ ] **Step 5: Run tests and commit**

```powershell
python -m pytest tests/test_r4_review_selection.py tests/test_r4_review_session.py -q
python -m ruff check scripts/build_r4_1_review_selection.py scripts/r4_1_review_session.py tests/test_r4_review_selection.py tests/test_r4_review_session.py
git add scripts/build_r4_1_review_selection.py scripts/r4_1_review_session.py tests/test_r4_review_selection.py tests/test_r4_review_session.py
git commit -m "feat(r4): export exact reviewed selections"
```

## Task 7: Implement the bounded loopback server

**Files:**

- Create: `scripts/serve_r4_1_review.py`
- Create: `tests/test_r4_review_server.py`

- [ ] **Step 1: Write failing route and security tests**

```python
def request(
    server: HTTPServer,
    method: str,
    path: str,
    *,
    body: Mapping[str, object] | None = None,
    headers: Mapping[str, str] | None = None,
) -> tuple[int, Mapping[str, str], bytes]:
    connection = http.client.HTTPConnection(*server.server_address, timeout=5)
    raw = None if body is None else _json_bytes(body)
    connection.request(method, path, body=raw, headers=dict(headers or {}))
    response = connection.getresponse()
    payload = response.read()
    result = response.status, dict(response.getheaders()), payload
    connection.close()
    return result


@pytest.fixture
def server_fixture(tmp_path: Path):
    running: list[tuple[HTTPServer, threading.Thread]] = []

    def create() -> HTTPServer:
        draft = tmp_path / f"draft-{len(running)}"
        inputs = tmp_path / f"inputs-{len(running)}"
        inputs.mkdir()
        build_review_worksheet_draft(repository_root=ROOT, output_root=draft)
        template_path = inputs / "SELECTION_TEMPLATE.json"
        template_path.write_bytes(
            build_selection_template_bytes(repository_root=ROOT, draft_root=draft)
        )
        paths = ReviewPaths(
            repository_root=ROOT,
            draft_root=draft,
            template_path=template_path,
            working_path=inputs / "SELECTION_WORKING.json",
            journal_path=inputs / "REVIEW_ACTIONS.jsonl",
            export_path=inputs / "SELECTION.json",
        )
        session = ReviewSession.open(paths)
        server = create_review_server(
            session=session,
            host="127.0.0.1",
            port=0,
            session_token="test-token",
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        running.append((server, thread))
        return server

    yield create
    for server, thread in running:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_server_binds_loopback_and_requires_session_token(server_fixture) -> None:
    server = server_fixture()
    assert server.server_address[0] == "127.0.0.1"
    status, _, _ = request(server, "GET", "/api/bootstrap")
    assert status == 403
    status, headers, body = request(
        server,
        "GET",
        "/api/bootstrap",
        headers={"X-CEMM-Review-Token": server.session_token},
    )
    assert status == 200
    assert headers["Content-Type"].startswith("application/json")
    assert json.loads(body)["result"]["inventory"]["structural"] == 12


def test_state_change_requires_exact_origin_token_and_revision(server_fixture) -> None:
    server = server_fixture()
    body = {
        "state_revision": server.session.state_revision,
        "action": {
            "action_kind": "structural",
            "target_refs": [],
            "selected_value": None,
        },
    }
    status, _, _ = request(
        server,
        "POST",
        "/api/preview",
        body=body,
        headers={
            "X-CEMM-Review-Token": server.session_token,
            "Origin": "https://hostile.example",
        },
    )
    assert status == 403
```

Add tests for unsupported methods/routes, oversized bodies, invalid JSON,
duplicate JSON keys, nonfinite numbers, missing content type, path traversal,
asset allowlist, safe error bodies and shutdown authorization.

- [ ] **Step 2: Run tests and verify the server module is absent**

```powershell
python -m pytest tests/test_r4_review_server.py -q
```

Expected: collection fails because `scripts.serve_r4_1_review` is absent.

- [ ] **Step 3: Implement exact routes and response envelopes**

Use `HTTPServer` and `BaseHTTPRequestHandler`, not a third-party server. Define:

```python
MAX_REQUEST_BYTES = 64 * 1024
API_ROUTES = frozenset(
    {
        "/api/bootstrap",
        "/api/items",
        "/api/preview",
        "/api/apply",
        "/api/reviewer",
        "/api/export",
        "/api/shutdown",
    }
)
STATIC_ROUTES = {
    "/": "index.html",
    "/index.html": "index.html",
    "/styles.css": "styles.css",
    "/app.js": "app.js",
}
```

Every API response uses canonical JSON with exactly `ok`, `state_revision`, and
either `result` or `error`. Map invalid input to 400, authorization/origin to
403, stale revision to 409, unknown route to 404, oversized body to 413 and
unexpected internal failure to 500. Log the error class and request id to
stderr, but return no stack trace or filesystem content.

Serve this exact Content Security Policy on HTML and JavaScript responses:

```text
default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'
```

Request bodies have these exact top-level fields and no extras:

```text
POST /api/reviewer  -> state_revision, reviewer_refs
POST /api/preview   -> state_revision, action
POST /api/apply     -> state_revision, preview_hash
POST /api/export    -> state_revision
POST /api/shutdown  -> state_revision
```

An `action` has exactly `action_kind`, `target_refs`, and `selected_value`.
Decode it through `ReviewAction.from_wire`; never pass an unvalidated browser
mapping into the session. `GET /api/items` admits only `section`, `filter`,
`query`, `offset`, and `limit` query parameters and rejects duplicates.

Require `X-CEMM-Review-Token` on every API request. For POST, also require
`Content-Type: application/json` and exact origin
`http://127.0.0.1:<selected-port>`. Decode with the existing strict duplicate-key
and nonfinite-number rejection helpers.

- [ ] **Step 4: Implement CLI lifecycle and browser launch**

The parser defaults are:

```python
root = Path(__file__).resolve().parents[1]
default_inputs = root / "artifacts/review_inputs/r4_1"
ReviewPaths(
    repository_root=root,
    draft_root=root / "artifacts/review_drafts/r4_1",
    template_path=default_inputs / "SELECTION_TEMPLATE.json",
    working_path=default_inputs / "SELECTION_WORKING.json",
    journal_path=default_inputs / "REVIEW_ACTIONS.jsonl",
    export_path=default_inputs / "SELECTION.json",
)
```

Admit `--root`, `--draft`, `--template`, `--working`, `--journal`, `--export`,
`--port` and `--no-open`. Port defaults to zero. Generate the token with
`secrets.token_urlsafe(32)`, start only after session validation succeeds, print
the complete local launch URL for manual recovery, and open
`http://127.0.0.1:<port>/#token=<urlencoded-token>` with `webbrowser.open` unless
`--no-open` is supplied.

The shutdown handler starts `server.shutdown` on a daemon thread only after the
authorized response is flushed, avoiding `serve_forever` deadlock.

- [ ] **Step 5: Run server tests and commit**

```powershell
python -m pytest tests/test_r4_review_server.py -q
python -m ruff check scripts/serve_r4_1_review.py tests/test_r4_review_server.py
git add scripts/serve_r4_1_review.py tests/test_r4_review_server.py
git commit -m "feat(r4): serve bounded local review API"
```

## Task 8: Build the accessible static review interface

**Files:**

- Create: `scripts/r4_1_review_ui/index.html`
- Create: `scripts/r4_1_review_ui/styles.css`
- Create: `scripts/r4_1_review_ui/app.js`

- [ ] **Step 1: Create the semantic HTML shell**

Use this document structure without inline scripts or styles:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>CEMM R4.1 Accountable Review</title>
  <link rel="stylesheet" href="/styles.css">
</head>
<body>
  <a class="skip-link" href="#workspace">Skip to review workspace</a>
  <header id="status-header" aria-live="polite"></header>
  <nav aria-label="Review phases">
    <button data-section="dashboard">Dashboard</button>
    <button data-section="structural">Structural</button>
    <button data-section="purpose">Purpose</button>
    <button data-section="recipe">Recipes</button>
    <button data-section="designation">Designations</button>
    <button data-section="export">Export</button>
  </nav>
  <main id="workspace" tabindex="-1"></main>
  <dialog id="impact-dialog" aria-labelledby="impact-title">
    <h2 id="impact-title">Confirm exact review action</h2>
    <div id="impact-content"></div>
    <form method="dialog">
      <button value="cancel">Cancel</button>
      <button id="confirm-impact" value="confirm">Confirm</button>
    </form>
  </dialog>
  <div id="toast" role="status" aria-live="polite"></div>
  <script src="/app.js" defer></script>
</body>
</html>
```

- [ ] **Step 2: Add responsive, keyboard-visible CSS**

Define local CSS variables, high-contrast status colors, a two-column desktop
workspace that collapses below 900 px, visible `:focus-visible` outlines,
reduced-motion support, scrollable evidence blocks, sticky phase navigation and
distinct unresolved/rejected/complete badges. Do not load fonts, images or
styles from external URLs.

Use a maximum content width of 1440 px and avoid rendering evidence refs in
fixed-width containers narrower than 20 characters.

- [ ] **Step 3: Implement a thin authenticated API client**

Start `app.js` with state owned only for display:

```javascript
"use strict";

const token = new URLSearchParams(location.hash.slice(1)).get("token");

const view = {
  bootstrap: null,
  section: "dashboard",
  filter: "unresolved",
  query: "",
  offset: 0,
  pendingPreview: null,
};

async function api(path, {method = "GET", body = null} = {}) {
  const headers = {"X-CEMM-Review-Token": token || ""};
  if (body !== null) headers["Content-Type"] = "application/json";
  const response = await fetch(path, {
    method,
    headers,
    body: body === null ? null : JSON.stringify(body),
  });
  const envelope = await response.json();
  if (!response.ok || envelope.ok !== true) {
    throw new Error(envelope.error?.message || `Request failed: ${response.status}`);
  }
  return envelope;
}
```

If the fragment token is absent, render a fatal local-session error and make no
API call. Never store the token in local storage, session storage, cookies,
query parameters or rendered DOM.

- [ ] **Step 4: Render server projections without unsafe HTML**

Implement `renderDashboard`, `renderItems`, `renderStructuralCard`,
`renderPurposeCard`, `renderRecipeCard`, `renderDesignationCard`, and
`renderExport`. Create elements with `document.createElement`, set untrusted
content with `textContent`, and attach event listeners directly. Do not use
`innerHTML`, `outerHTML`, `insertAdjacentHTML`, `eval`, `Function`, or inline
event attributes.

Each card shows exact subject/case/family refs in expandable details, evidence,
allowed actions, current decision and risk badges. Exceptional designation
cards display an "Individual review required" badge and never render a cohort
action button. Initial rendering leaves every unresolved option visibly
unselected; filters and navigation never mutate review state.

- [ ] **Step 5: Wire preview, confirm, revision conflict and export flows**

Action buttons call `/api/preview`, render exact affected and cleared refs plus
resulting counts in `impact-dialog`, and enable confirmation only after the
preview arrives. Confirmation calls `/api/apply` using the returned preview hash
and revision, then refreshes bootstrap and the current page.

On HTTP 409, discard the preview, show "Review state changed; reloaded current
state", and reload. Export renders validation receipt path, byte length,
SHA-256, review-complete status, authoring-ready status and blocking rejection
refs.

- [ ] **Step 6: Run static syntax and forbidden-pattern checks, then commit**

```powershell
node --check scripts/r4_1_review_ui/app.js
$forbidden = rg -n "innerHTML|outerHTML|insertAdjacentHTML|eval\(|new Function|https?://" scripts/r4_1_review_ui
if ($LASTEXITCODE -eq 0) { Write-Output $forbidden; throw "forbidden browser pattern found" }
if ($LASTEXITCODE -ne 1) { throw "browser pattern scan failed" }
```

Expected: Node exits zero and the forbidden-pattern scan finds no matches. Then:

```powershell
git add scripts/r4_1_review_ui/index.html scripts/r4_1_review_ui/styles.css scripts/r4_1_review_ui/app.js
git commit -m "feat(r4): add accountable review interface"
```

## Task 9: Add full HTTP-to-export integration coverage

**Files:**

- Modify: `tests/test_r4_review_server.py`
- Modify: `tests/test_r4_review_session.py`

- [ ] **Step 1: Write a full synthetic review API test**

Build a deterministic test driver that uses server endpoints, not session
internals, to:

1. set `reviewer:test`;
2. select exact approved structural options;
3. assign supervised membership across all four purposes while selecting
   `reject_group` for groups and `not_a_holdout` for holdouts;
4. approve diagnostics;
5. select all denominator minima;
6. approve every purpose-local recipe with bounded fixture parameters;
7. approve every nonempty designation set and every exact-empty set;
8. export; and
9. independently validate the returned file bytes.

The test ends with:

```python
assert bootstrap["inventory"] == {
    "structural": 12,
    "purpose": 600,
    "recipe_family": 56,
    "designation": 388,
}
assert export_receipt["review_complete"] is True
assert export_receipt["authoring_ready"] is True
assert validate_reviewed_selection_bytes(
    repository_root=ROOT,
    draft_root=review_paths.draft_root,
    selection_raw=review_paths.export_path.read_bytes(),
)["selection_state"] == "reviewed"
```

- [ ] **Step 2: Add deterministic replay and no-runtime-import tests**

Run the same logical action sequence in two independent directories and require
byte-identical exported selection files. Action journals may differ only in
`recorded_at_ns` and are not compared as authority.

Add an AST import scan requiring no file under `src/cemm_authoritative_hybrid`
to import `serve_r4_1_review`, `r4_1_review_session`, `http.server`, `webbrowser`
or any path under `scripts/r4_1_review_ui`.

- [ ] **Step 3: Add bounded-operation and performance assertions**

Instrument session construction and assert one template reconstruction, one
draft authentication and one index build per process. Execute 512 previews and
128 applies against temporary working state and assert no additional calls to
`_tree_bytes`, `load_selection_context`, `AuthorityLinker` or
`build_review_worksheet_draft`.

Do not assert wall-clock timing in normal tests.

- [ ] **Step 4: Run integration and regression tests**

```powershell
python -m pytest tests/test_r4_review_selection.py tests/test_r4_review_session.py tests/test_r4_review_server.py -q
python -m pytest tests/test_r4_authoring_pipeline.py tests/test_r4_authoring.py tests/test_r4_purpose_contracts.py -q
python -m pytest tests/test_r4_supervision_contracts.py -k "sr5_" -q
python -m ruff check scripts/build_r4_1_review_selection.py scripts/r4_1_review_session.py scripts/serve_r4_1_review.py tests/test_r4_review_selection.py tests/test_r4_review_session.py tests/test_r4_review_server.py
python -m py_compile scripts/build_r4_1_review_selection.py scripts/r4_1_review_session.py scripts/serve_r4_1_review.py
node --check scripts/r4_1_review_ui/app.js
git diff --check
```

Expected: all commands pass.

- [ ] **Step 5: Commit integration coverage**

```powershell
git add tests/test_r4_review_session.py tests/test_r4_review_server.py
git commit -m "test(r4): verify review UI end to end"
```

## Task 10: Document, smoke-test and hand off the reviewer

**Files:**

- Modify: `artifacts/review_inputs/r4_1/README.md`
- Modify: `docs/superpowers/plans/2026-08-30-r4-1-supervision-authoring-automation-plan.md`

- [ ] **Step 1: Update reviewer instructions with exact lifecycle**

Document:

```powershell
python scripts/serve_r4_1_review.py
```

Explain the five review phases, local working/journal files, explicit cohort
confirmation, exceptional designation review, resume behavior, authoring-ready
status, export location and this independent final check:

```powershell
python scripts/build_r4_1_review_selection.py --root . `
  --draft artifacts/review_drafts/r4_1 `
  --validate-selection artifacts/review_inputs/r4_1/SELECTION.json
```

State clearly that a valid export containing rejection decisions records the
review but does not unblock Task 10B expansion.

- [ ] **Step 2: Update the progress tracker without overstating completion**

Change Task 10B status from "awaiting accountable selections" to:

```text
review UI ready; awaiting accountable completed selection
```

Record the UI launch command, test coverage and the invariant that the tool is
offline and not a release gate. Leave Task 10B Steps 4B and 6 unchecked until a
real accountable `SELECTION.json` exists and proposal compilation passes.

- [ ] **Step 3: Run a real-browser smoke review**

Launch with:

```powershell
python scripts/serve_r4_1_review.py --no-open
```

Open the printed loopback URL with its session-token fragment in a real browser.
Verify dashboard load, reviewer entry, one structural preview/cancel, one
structural preview/confirm, section navigation, search, keyboard focus, narrow
viewport layout, resume after server restart, unauthorized API rejection and
authorized shutdown. Use a temporary working/journal/export path so no real
review choice is recorded during smoke testing.

- [ ] **Step 4: Run final focused verification twice**

```powershell
python -m pytest tests/test_r4_review_selection.py tests/test_r4_review_session.py tests/test_r4_review_server.py tests/test_r4_authoring_pipeline.py tests/test_r4_authoring.py tests/test_r4_purpose_contracts.py -q
python -m pytest tests/test_r4_review_selection.py tests/test_r4_review_session.py tests/test_r4_review_server.py tests/test_r4_authoring_pipeline.py tests/test_r4_authoring.py tests/test_r4_purpose_contracts.py -q
python -m pytest tests/test_r4_supervision_contracts.py -k "sr5_" -q
python -m ruff check scripts/build_r4_1_review_selection.py scripts/r4_1_review_session.py scripts/serve_r4_1_review.py tests/test_r4_review_selection.py tests/test_r4_review_session.py tests/test_r4_review_server.py
python -m py_compile scripts/build_r4_1_review_selection.py scripts/r4_1_review_session.py scripts/serve_r4_1_review.py
node --check scripts/r4_1_review_ui/app.js
git diff --check
```

Expected: both focused runs are green and deterministic; SR5, lint, compile,
JavaScript syntax and diff checks pass.

- [ ] **Step 5: Commit the handoff documentation**

```powershell
git add artifacts/review_inputs/r4_1/README.md docs/superpowers/plans/2026-08-30-r4-1-supervision-authoring-automation-plan.md
git commit -m "docs(r4): hand off accountable review UI"
```

- [ ] **Step 6: Verify branch state before pushing**

```powershell
git fetch origin
git status --short --branch
git rev-list --left-right --count HEAD...origin/codex/r4-1-data-supervision-replay
```

Expected before push: clean worktree and only the planned local commits ahead.
Push only after resolving any newly discovered remote divergence without
rewriting unrelated history.
