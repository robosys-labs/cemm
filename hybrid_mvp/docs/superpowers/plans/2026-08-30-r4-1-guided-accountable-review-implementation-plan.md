# R4.1 Guided Accountable Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the raw-ref-first R4.1 reviewer experience with a bounded guided workflow that explains one accountable decision at a time without recommending or selecting semantic answers.

**Architecture:** Add one pure Python guided-projection service over the existing authenticated `ReviewSession`; it owns deterministic progression, neutral reviewed explanations, exact cohort projection and opaque choice-to-`ReviewAction` resolution. Extend the existing loopback server with three bounded guided routes and make the existing framework-free HTML/JavaScript client default to guided mode while preserving the current Advanced Explorer. No runtime package, activation phase, release gate, source artifact or selection ABI changes.

**Tech Stack:** Python 3.13-compatible standard library, frozen dataclasses, canonical JSON, SHA-256 stable refs, `HTTPServer`, semantic HTML, vanilla JavaScript, CSS, pytest, Ruff.

---

## Governing inputs

Read together before implementation:

- `AGENTS.md`
- `docs/superpowers/specs/2026-08-30-r4-1-guided-accountable-review-design.md`
- `docs/superpowers/specs/2026-08-30-r4-1-accountable-review-ui-design.md`
- `docs/superpowers/plans/2026-08-30-r4-1-supervision-authoring-automation-plan.md`
- `artifacts/review_inputs/r4_1/README.md`

Preserve these invariants throughout:

```text
Program != meaning
no recommended/preselected semantic choice
skip == no mutation
JavaScript == presentation only
one authenticated source/context/index load per server session
guided export bytes == exact existing export bytes
guided UI adds no runtime, activation or release gate
```

## File map

- Create `scripts/r4_1_guided_review.py`: neutral guidance catalog, bounded guided projection, deterministic traversal and opaque choice resolution.
- Create `tests/test_r4_guided_review.py`: projection, traversal, neutrality, cohort, action-equivalence and performance contracts.
- Modify `scripts/serve_r4_1_review.py`: attach one guided service and expose bounded guided routes through existing security controls.
- Modify `tests/test_r4_review_server.py`: route, authorization, request-shape, stale-state and complete guided replay tests.
- Modify `scripts/r4_1_review_ui/index.html`: guided-first shell and explicit Advanced Explorer navigation.
- Modify `scripts/r4_1_review_ui/app.js`: onboarding, one-item navigation, skip, impact confirmation, auto-advance and completion views.
- Modify `scripts/r4_1_review_ui/styles.css`: guided layout, neutral choice cards, progress and responsive/accessibility states.
- Modify `tests/test_r4_review_ui.py`: static guided, neutrality, unsafe-DOM and accessibility contracts.
- Modify `artifacts/review_inputs/r4_1/README.md`: start/resume instructions and plain-language reviewer role.
- Modify `docs/superpowers/plans/2026-08-30-r4-1-supervision-authoring-automation-plan.md`: progress tracker and exact remaining Task 10B blocker.

Do not add a framework, package manifest, browser storage, service worker,
generated language artifact, runtime import or additional validation process.

---

### Task 1: Freeze the neutral guidance vocabulary

**Files:**

- Create: `scripts/r4_1_guided_review.py`
- Create: `tests/test_r4_guided_review.py`

- [ ] **Step 1: Write failing catalog coverage and neutrality tests**

Create `tests/test_r4_guided_review.py` with exact active row/choice coverage:

```python
from __future__ import annotations

from scripts.r4_1_guided_review import GUIDANCE, PHASE_ORDER


EXPECTED_CHOICES = {
    "composed_expression_proposal": {
        "approve_exact_proposal", "reject_exact_proposal"
    },
    "conflict_preservation": {"preserve_as_alternatives"},
    "legacy_conditional": {
        "retain_typed_proposal_gaps", "retire_with_reserved_indices"
    },
    "generator_patch": {
        "retain_typed_proposal_gaps", "retire_with_reserved_indices"
    },
    "restart_diagnostic": {
        "approve_diagnostic_only", "reject_pending_replacement"
    },
    "membership": {
        "direct_train", "direct_selection", "direct_calibration",
        "direct_frozen_test", "assign_to_reviewed_group",
        "approve_diagnostic_only", "reject_pending_replacement",
    },
    "duplicate_group": {
        "approve_train", "approve_selection", "approve_calibration",
        "approve_frozen_test", "reject_group",
    },
    "challenge_holdout": {
        "not_a_holdout", "holdout_train", "holdout_selection",
        "holdout_calibration", "holdout_frozen_test",
    },
    "denominator": {"minimum_one_each"},
    "proposal_recipe_family": {"approve", "reject"},
    "designation_nonempty": {"approve_candidate_bindings", "reject"},
    "designation_empty": {"approve_exact_empty", "reject"},
}


def test_guidance_covers_every_active_choice_without_recommendation() -> None:
    assert PHASE_ORDER == (
        "identity", "structural", "purpose", "recipe", "designation", "export"
    )
    assert set(GUIDANCE) == set(EXPECTED_CHOICES)
    for row_kind, labels in EXPECTED_CHOICES.items():
        entry = GUIDANCE[row_kind]
        assert set(entry.choices) == labels
        assert entry.question.strip()
        for label, choice in entry.choices.items():
            wire = repr(choice).casefold()
            assert choice.label.strip()
            assert choice.explanation.strip()
            assert choice.consequence.strip()
            assert "recommended" not in wire
            assert "best choice" not in wire
            assert label not in {"default", "selected"}
```

- [ ] **Step 2: Run the test and verify the module is absent**

Run:

```powershell
python -m pytest tests/test_r4_guided_review.py::test_guidance_covers_every_active_choice_without_recommendation -q
```

Expected: collection fails with `ModuleNotFoundError: No module named 'scripts.r4_1_guided_review'`.

- [ ] **Step 3: Add frozen catalog types and the exact active catalog**

Create `scripts/r4_1_guided_review.py` with immutable types and a complete
module-level catalog. Use plain-language labels such as **Use this exact
proposal**, **Reject and repair this proposal**, **Training**, **Model
selection**, **Calibration**, **Frozen final test**, **Accept this exact
candidate set**, and **Record this exact empty set**. Every explanation must
describe verification, not likelihood.

```python
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


PHASE_ORDER = (
    "identity", "structural", "purpose", "recipe", "designation", "export"
)


@dataclass(frozen=True, slots=True)
class ChoiceGuidance:
    label: str
    explanation: str
    consequence: str
    blocks_authoring: bool


@dataclass(frozen=True, slots=True)
class RowGuidance:
    instruction: str
    question: str
    choices: Mapping[str, ChoiceGuidance]


def _choices(**values: ChoiceGuidance) -> Mapping[str, ChoiceGuidance]:
    return MappingProxyType(dict(values))


GUIDANCE: Mapping[str, RowGuidance] = MappingProxyType({
    "composed_expression_proposal": RowGuidance(
        instruction="Compare the source sentence with the complete proposed semantic graph.",
        question="Does this exact graph preserve every proposition, role, scope and link in the source?",
        choices=_choices(
            approve_exact_proposal=ChoiceGuidance(
                "Use this exact proposal",
                "Record that the displayed graph exactly represents the source.",
                "This proposal remains eligible for supervised authoring.",
                False,
            ),
            reject_exact_proposal=ChoiceGuidance(
                "Reject and repair this proposal",
                "Record that the graph is not an exact representation of the source.",
                "Dependent authoring stays blocked until the earliest owner is repaired.",
                True,
            ),
        ),
    ),
})
```

The complete literal `GUIDANCE` mapping is defined by `EXPECTED_CHOICES`, the
two proposal choices in the code block, and the following fixed vocabulary.
Explanations use these meanings verbatim and consequences state whether
authoring is blocked:

| Wire choice | Display label | Meaning |
|---|---|---|
| `preserve_as_alternatives` | Preserve both alternatives | Keep both conflicting source-supported alternatives without settling either one. |
| `retain_typed_proposal_gaps` | Retain typed gaps | Preserve unresolved proposals as typed gaps with their reserved identities. |
| `retire_with_reserved_indices` | Retire and reserve indices | Remove the legacy cases while preserving their reserved indices. |
| `approve_diagnostic_only` | Keep as diagnostic only | Exclude the case from semantic supervision and retain it only for diagnostics. |
| `reject_pending_replacement` | Reject pending replacement | Block use of the case until its source owner supplies a replacement. |
| `direct_train` / `approve_train` / `holdout_train` | Assign to training | Give the exact case/group/holdout to the training partition. |
| `direct_selection` / `approve_selection` / `holdout_selection` | Assign to model selection | Give the exact case/group/holdout to the selection partition. |
| `direct_calibration` / `approve_calibration` / `holdout_calibration` | Assign to calibration | Give the exact case/group/holdout to the calibration partition. |
| `direct_frozen_test` / `approve_frozen_test` / `holdout_frozen_test` | Assign to frozen test | Give the exact case/group/holdout to the isolated final-test partition. |
| `assign_to_reviewed_group` | Use the reviewed group decision | Inherit the purpose chosen for the displayed duplicate-risk group. |
| `reject_group` | Reject this group | Block every member pending repair of group ownership. |
| `not_a_holdout` | Do not reserve as a holdout | Leave this topology eligible for ordinary purpose assignment. |
| `minimum_one_each` | Require at least one per purpose | Enforce the displayed denominator minimum for all four purposes. |
| recipe `approve` | Approve this purpose-local recipe | Accept the exact displayed family parameters for this purpose only. |
| recipe `reject` | Reject and repair this recipe | Block this family/purpose until the recipe owner is repaired. |
| `approve_candidate_bindings` | Accept this exact candidate set | Record every and only the displayed designation binding. |
| `approve_exact_empty` | Record this exact empty set | Record that the reviewed nonsemantic case has no designation binding. |
| designation `reject` | Reject and repair these bindings | Block the case until authority or source geometry is repaired. |

`approve_exact_proposal` and `reject_exact_proposal` use the literal definitions
shown in the code block. Do not generate wording from option names at runtime.

- [ ] **Step 4: Add source-row inventory comparison**

Add a test that opens a real `ReviewSession`, obtains the active option labels
from `session.indexes` plus recipe/designation choices, and asserts exact
equality with `EXPECTED_CHOICES`. This makes a future ABI option addition fail
closed until reviewed guidance is added.

```python
def test_guidance_matches_authenticated_active_options(review_paths: ReviewPaths) -> None:
    session = ReviewSession.open(review_paths)
    actual: dict[str, set[str]] = {}
    for rows in (
        session.indexes.structural_rows_by_ref.values(),
        session.indexes.purpose_rows_by_ref.values(),
    ):
        for row in rows:
            actual.setdefault(row["row_kind"], set()).update(
                option["label"]
                for option in row["options"]
                if option["selectable"] is True
            )
    actual["proposal_recipe_family"] = {"approve", "reject"}
    actual["designation_nonempty"] = {"approve_candidate_bindings", "reject"}
    actual["designation_empty"] = {"approve_exact_empty", "reject"}
    assert actual == EXPECTED_CHOICES
```

Copy the existing `review_paths(tmp_path)` fixture from
`tests/test_r4_review_session.py` into the new test module so it builds an exact
temporary worksheet/template without importing another test module.

- [ ] **Step 5: Run focused tests**

Run:

```powershell
python -m pytest tests/test_r4_guided_review.py -q
python -m ruff check scripts/r4_1_guided_review.py tests/test_r4_guided_review.py
```

Expected: all tests pass and Ruff reports `All checks passed!`.

- [ ] **Step 6: Commit**

```powershell
git add scripts/r4_1_guided_review.py tests/test_r4_guided_review.py
git commit -m "feat(r4): define neutral guided review vocabulary"
```

---

### Task 2: Project one deterministic guided item

**Files:**

- Modify: `scripts/r4_1_guided_review.py`
- Modify: `tests/test_r4_guided_review.py`

- [ ] **Step 1: Write failing traversal, plain-language and skip tests**

Add tests using the existing `review_paths`/`ReviewSession.open` fixtures:

```python
def test_guided_review_starts_with_identity_then_earliest_structural(review_paths) -> None:
    service = GuidedReviewService(ReviewSession.open(review_paths))
    first = service.next_item(after_item_ref=None)
    assert first["phase"] == "identity"
    assert first["primary_action"] == "save_reviewer_identity"

    service.session.set_reviewers(("reviewer:test",))
    structural = service.next_item(after_item_ref=None)
    assert structural["phase"] == "structural"
    assert structural["source_summary"].strip()
    assert structural["reviewer_question"].endswith("?")
    assert structural["selected_choice_ref"] is None
    assert "row_ref" not in structural
    assert "technical_evidence" in structural


def test_skip_advances_without_mutation_and_wraps_once(review_paths) -> None:
    session = ReviewSession.open(review_paths)
    session.set_reviewers(("reviewer:test",))
    service = GuidedReviewService(session)
    revision = service.session.state_revision
    first = service.next_item(after_item_ref=None)
    second = service.next_item(after_item_ref=first["item_ref"])
    assert second["item_ref"] != first["item_ref"]
    assert service.session.state_revision == revision
    wrapped = service.next_item(after_item_ref=service.ordered_item_refs[-1])
    assert wrapped["wrapped"] is True
```

- [ ] **Step 2: Run tests and verify `GuidedReviewService` is missing**

Run:

```powershell
python -m pytest tests/test_r4_guided_review.py -k "starts_with_identity or skip_advances" -q
```

Expected: failure because `GuidedReviewService` is not defined.

- [ ] **Step 3: Implement bounded item types and deterministic traversal**

Add these interfaces:

```python
MAX_GUIDED_EVIDENCE_BLOCKS = 12
MAX_GUIDED_TARGET_REFS = 512
MAX_GUIDED_EXAMPLES = 5


class GuidedReviewService:
    def __init__(self, session: ReviewSession) -> None:
        self.session = session
        self._ordered_refs = build_guided_order(session.indexes)
        self._projection_revision = -1
        self._state_by_ref: Mapping[str, object] = MappingProxyType({})
        self._projection_builds = 0

    @property
    def projection_builds(self) -> int:
        return self._projection_builds

    @property
    def ordered_item_refs(self) -> tuple[str, ...]:
        return self._ordered_refs

    def _refresh_state_projection(self) -> None:
        if self._projection_revision == self.session.state_revision:
            return
        self._state_by_ref = build_bounded_state_projection(self.session)
        self._projection_revision = self.session.state_revision
        self._projection_builds += 1

    def next_item(self, *, after_item_ref: str | None) -> Mapping[str, object]:
        self._refresh_state_projection()
        return project_next_applicable_unresolved(
            session=self.session,
            ordered_refs=self._ordered_refs,
            state_by_ref=self._state_by_ref,
            after_item_ref=after_item_ref,
        )
```

`build_guided_order` uses fixed phase order and exact ref order. Identity and
export are synthetic presentation steps only. Structural applicability,
purpose applicability, eligible recipe purposes and designation exceptions
come from the existing authenticated session/evaluation; do not reproduce
selection validity rules.

- [ ] **Step 4: Project readable source/proposal/evidence summaries**

Use explicit projector functions per row kind. They may select and relabel
existing fields but may not infer missing meaning. At minimum:

```python
def _structural_summary(row: Mapping[str, object]) -> str:
    source = row.get("surface")
    if type(source) is str and source.strip():
        return source
    result = row.get("resulting_scenario_row")
    if type(result) is dict:
        examples = result.get("surface_examples")
        if type(examples) is list and examples and type(examples[0]) is str:
            return examples[0]
    return "This structural decision has no reviewed surface summary; inspect technical evidence."
```

The fallback is a typed absence notice, never an invented paraphrase. Keep
exact source fields in `technical_evidence` under byte/count bounds.

- [ ] **Step 5: Prove the projection cache is revision-keyed, not request-keyed**

```python
def test_512_guided_reads_reuse_one_state_projection(review_paths) -> None:
    session = ReviewSession.open(review_paths)
    session.set_reviewers(("reviewer:test",))
    service = GuidedReviewService(session)
    item = service.next_item(after_item_ref=None)
    for _ in range(512):
        service.next_item(after_item_ref=item["item_ref"])
    assert service.projection_builds == 1
```

- [ ] **Step 6: Run focused tests and commit**

```powershell
python -m pytest tests/test_r4_guided_review.py -q
git add scripts/r4_1_guided_review.py tests/test_r4_guided_review.py
git commit -m "feat(r4): project deterministic guided review items"
```

---

### Task 3: Resolve opaque guided choices into exact existing actions

**Files:**

- Modify: `scripts/r4_1_guided_review.py`
- Modify: `tests/test_r4_guided_review.py`

- [ ] **Step 1: Write failing choice-equivalence and cohort-safety tests**

```python
def test_every_guided_choice_resolves_to_one_existing_allowed_action(review_paths) -> None:
    session = ReviewSession.open(review_paths)
    session.set_reviewers(("reviewer:test",))
    service = GuidedReviewService(session)
    for item in service.iter_current_items():
        for choice in item["choices"]:
            action = service.resolve_choice(
                item_ref=item["item_ref"], choice_ref=choice["choice_ref"]
            )
            assert service.session.preview(action).action == action
            assert "action" not in choice
            assert "selected" not in choice


def test_routine_designation_cohorts_exclude_every_exception(review_paths) -> None:
    session = ReviewSession.open(review_paths)
    service = GuidedReviewService(session)
    exceptions = session.indexes.designation_exception_case_refs
    for item in service.designation_cohort_items():
        members = set(item["cohort"]["target_refs"])
        assert not members & exceptions
        assert len(members) <= MAX_GUIDED_TARGET_REFS
```

- [ ] **Step 2: Run tests and verify resolver absence**

```powershell
python -m pytest tests/test_r4_guided_review.py -k "resolves_to_one or cohorts_exclude" -q
```

Expected: failure because `resolve_choice` is absent.

- [ ] **Step 3: Add content-addressed opaque choice refs**

Use the repository's existing stable-ref function, not random identifiers:

```python
def _choice_ref(*, item_ref: str, option_key: str, target_refs: tuple[str, ...]) -> str:
    return stable_ref(
        "guided_review_choice",
        {"item_ref": item_ref, "option_key": option_key, "target_refs": list(target_refs)},
    )
```

Return only `choice_ref`, readable guidance and blocking consequence to the
browser. Store/reconstruct the exact `(item_ref, choice_ref) -> ReviewAction`
mapping inside the service for the current revision. Reject stale, unknown or
cross-item refs. Add `iter_current_items()` and `designation_cohort_items()` as
bounded testable iterators over the same private projector; they must not create
a second projection path.

- [ ] **Step 4: Reuse existing action constructors for every phase**

Resolve structural, purpose, recipe and designation choices only through:

```python
ReviewAction.structural(...)
ReviewAction.purpose(...)
ReviewAction.recipe(...)
ReviewAction.designation_cases(...)
ReviewAction.designation_cohort(...)
```

Purpose cohort actions may target multiple exact membership rows only through
`session.indexes.purpose_cohorts`, when every member exposes the same selectable
option and the group/holdout/denominator constraints make every member
applicable. If any member fails those checks, omit the cohort and project those
rows individually; never synthesize a replacement cohort.

- [ ] **Step 5: Add readable preview projection**

```python
def preview_choice(self, *, item_ref: str, choice_ref: str) -> Mapping[str, object]:
    action = self.resolve_choice(item_ref=item_ref, choice_ref=choice_ref)
    preview = self.session.preview(action)
    return MappingProxyType({
        "preview_hash": preview.preview_hash,
        "state_revision": preview.state_revision,
        "decision_summary": self._choice_summary(item_ref, choice_ref),
        "affected_count": len(preview.affected_refs),
        "cleared_count": len(preview.cleared_refs),
        "affected_refs": list(preview.affected_refs),
        "cleared_refs": list(preview.cleared_refs),
        "requires_clear_confirmation": preview.requires_clear_confirmation,
        "resulting_counts": dict(preview.resulting_counts),
        "blocks_authoring": self._choice_blocks_authoring(item_ref, choice_ref),
    })
```

- [ ] **Step 6: Run full guided/session tests and commit**

```powershell
python -m pytest tests/test_r4_guided_review.py tests/test_r4_review_session.py -q
git add scripts/r4_1_guided_review.py tests/test_r4_guided_review.py
git commit -m "feat(r4): resolve guided choices to exact review actions"
```

---

### Task 4: Expose bounded guided routes through the existing server

**Files:**

- Modify: `scripts/serve_r4_1_review.py`
- Modify: `tests/test_r4_review_server.py`

- [ ] **Step 1: Write failing route and security tests**

Add these shared helpers above the tests:

```python
def guided_next(server: object, after: str | None) -> Mapping[str, object]:
    encoded = quote("" if after is None else after, safe="")
    status, _, raw = request(
        server,
        "GET",
        f"/api/guided/next?after={encoded}",
        headers=_api_headers(server),
    )
    assert status == 200
    return json.loads(raw)["result"]


def guided_preview(
    server: object,
    item: Mapping[str, object],
    choice: Mapping[str, object],
) -> Mapping[str, object]:
    status, _, raw = request(
        server,
        "POST",
        "/api/guided/preview",
        body={
            "state_revision": server.session.state_revision,
            "item_ref": item["item_ref"],
            "choice_ref": choice["choice_ref"],
        },
        headers=_api_headers(server, post=True),
    )
    assert status == 200
    return json.loads(raw)["result"]
```

Import `quote` from `urllib.parse`, then add:

```python
def test_guided_routes_require_token_origin_exact_fields_and_revision(server_fixture) -> None:
    server = server_fixture()
    assert request(server, "GET", "/api/guided/next", headers={})[0] == 403
    status, _, _ = request(
        server,
        "POST",
        "/api/guided/preview",
        body={"state_revision": 0, "item_ref": "x", "choice_ref": "y"},
        headers={"X-CEMM-Review-Token": server.session_token, "Origin": "http://evil"},
    )
    assert status == 403


def test_guided_next_and_preview_never_expose_action_wire(server_fixture) -> None:
    server = server_fixture()
    item = guided_next(server, after=None)
    assert "action" not in json.dumps(item)
    preview = guided_preview(server, item, item["choices"][0])
    assert "preview_hash" in preview
    assert "action" not in json.dumps(preview)
```

- [ ] **Step 2: Run focused tests and verify 404**

```powershell
python -m pytest tests/test_r4_review_server.py -k "guided_routes or guided_next" -q
```

Expected: the new routes return 404.

- [ ] **Step 3: Attach exactly one service per server**

```python
class ReviewHTTPServer(HTTPServer):
    session: ReviewSession
    guided: GuidedReviewService
    session_token: str
    static_root: Path
    origin: str


def create_review_server(...):
    server = ReviewHTTPServer((host, port), ReviewRequestHandler)
    server.session = session
    server.guided = GuidedReviewService(session)
    # retain all existing assignments and host validation
```

- [ ] **Step 4: Add exact routes**

Add:

```text
GET  /api/guided/bootstrap
GET  /api/guided/next?after=<empty-or-exact-item-ref>
POST /api/guided/preview
```

`/api/guided/bootstrap` returns reviewer identity, phase progress, completion
state and the default-mode explanation. `/api/guided/next` accepts exactly one
`after` query field with a maximum of 256 characters. `/api/guided/preview`
accepts exactly:

```json
{"state_revision": 0, "item_ref": "...", "choice_ref": "..."}
```

It calls `server.guided.preview_choice`; it never accepts a client-created
action. Existing `/api/apply` remains the only commit route.

- [ ] **Step 5: Invalidate only the revision projection after apply**

After successful `session.apply`, call:

```python
self.server.guided.observe_revision(self.server.session.state_revision)
```

`observe_revision` must only mark the small state projection stale; it must not
reread source files or rebuild authenticated indexes.

- [ ] **Step 6: Run server regression tests and commit**

```powershell
python -m pytest tests/test_r4_review_server.py tests/test_r4_guided_review.py -q
python -m ruff check scripts/serve_r4_1_review.py scripts/r4_1_guided_review.py tests/test_r4_review_server.py tests/test_r4_guided_review.py
git add scripts/serve_r4_1_review.py tests/test_r4_review_server.py
git commit -m "feat(r4): serve bounded guided review API"
```

---

### Task 5: Make Start/Resume guided review the default interface

**Files:**

- Modify: `scripts/r4_1_review_ui/index.html`
- Modify: `scripts/r4_1_review_ui/app.js`
- Modify: `scripts/r4_1_review_ui/styles.css`
- Modify: `tests/test_r4_review_ui.py`

- [ ] **Step 1: Write failing guided-shell static tests**

```python
def test_review_ui_defaults_to_guided_start_and_preserves_advanced_explorer() -> None:
    html = (UI_ROOT / "index.html").read_text(encoding="utf-8")
    source = (UI_ROOT / "app.js").read_text(encoding="utf-8")
    assert 'id="guided-progress"' in html
    assert 'data-mode="guided"' in html
    assert "Start guided review" in source
    assert "Resume guided review" in source
    assert "Open Advanced Explorer" in source
    assert 'section: "dashboard"' not in source


def test_guided_ui_has_no_semantic_recommendation_or_preselection() -> None:
    source = (UI_ROOT / "app.js").read_text(encoding="utf-8").casefold()
    for forbidden in (
        "recommended option", "best choice", "likely correct", "checked = true",
        "selectedchoice", "autoselect",
    ):
        assert forbidden not in source
```

- [ ] **Step 2: Run static tests and verify failure**

```powershell
python -m pytest tests/test_r4_review_ui.py -k "guided_start or recommendation" -q
```

Expected: failure because the guided shell does not exist.

- [ ] **Step 3: Add the guided shell**

Modify `index.html` to include:

```html
<nav class="mode-nav" aria-label="Review mode">
  <button type="button" data-mode="guided">Guided review</button>
  <button type="button" data-mode="advanced">Advanced Explorer</button>
</nav>
<div id="guided-progress" aria-live="polite"></div>
```

Keep the existing phase navigation inside the Advanced Explorer container. Do
not duplicate the impact dialog, toast or API client.

- [ ] **Step 4: Add guided-first view state and start screen**

Use:

```javascript
const view = {
  bootstrap: null,
  guidedBootstrap: null,
  mode: "guided",
  guidedStarted: false,
  guidedItem: null,
  guidedPassStartRef: null,
  guidedAfterRef: null,
  section: "dashboard",
  filter: "unresolved",
  query: "",
  offset: 0,
  limit: 25,
  pendingPreview: null,
  busy: false,
};
```

The start screen must state the reviewer role verbatim in plain language and
show only **Start guided review**/**Resume guided review** as primary plus
**Open Advanced Explorer** as secondary. Determine Start versus Resume from
server-owned reviewer/count state, not browser storage.

- [ ] **Step 5: Add responsive guided styling**

Add `.guided-shell`, `.guided-step`, `.phase-progress`, `.choice-grid`,
`.choice-card`, `.technical-evidence`, and `.mode-nav` styles. Choice cards must
have equal border/background/weight; only blocking consequence text may use
danger color. Preserve 44-pixel controls, `:focus-visible`, dark mode, reduced
motion and one-column behavior below 900 pixels.

- [ ] **Step 6: Run static/accessibility tests and commit**

```powershell
python -m pytest tests/test_r4_review_ui.py -q
node --check scripts/r4_1_review_ui/app.js
git add scripts/r4_1_review_ui/index.html scripts/r4_1_review_ui/app.js scripts/r4_1_review_ui/styles.css tests/test_r4_review_ui.py
git commit -m "feat(r4): add guided review start experience"
```

---

### Task 6: Render one decision, skip safely and confirm-and-continue

**Files:**

- Modify: `scripts/r4_1_review_ui/app.js`
- Modify: `scripts/r4_1_review_ui/styles.css`
- Modify: `tests/test_r4_review_ui.py`
- Modify: `tests/test_r4_review_server.py`

- [ ] **Step 1: Write failing interaction-contract tests**

Static assertions:

```python
def test_guided_ui_uses_opaque_choices_and_skip_is_local_navigation() -> None:
    source = (UI_ROOT / "app.js").read_text(encoding="utf-8")
    assert "function renderGuidedItem" in source
    assert "function skipGuidedItem" in source
    assert "function previewGuidedChoice" in source
    assert "Confirm and continue" in source
    assert 'api("/api/guided/preview"' in source
    assert "ReviewAction" not in source
    assert "localStorage" not in source
    assert "sessionStorage" not in source
```

Server integration assertion:

```python
def save_test_reviewer(server: object) -> None:
    status, _, _ = request(
        server,
        "POST",
        "/api/reviewer",
        body={
            "state_revision": server.session.state_revision,
            "reviewer_refs": ["reviewer:test"],
        },
        headers=_api_headers(server, post=True),
    )
    assert status == 200


def apply_guided_preview(server: object, preview: Mapping[str, object]) -> None:
    status, _, _ = request(
        server,
        "POST",
        "/api/apply",
        body={
            "state_revision": preview["state_revision"],
            "preview_hash": preview["preview_hash"],
        },
        headers=_api_headers(server, post=True),
    )
    assert status == 200


def test_guided_confirm_advances_only_after_successful_apply(server_fixture) -> None:
    server = server_fixture()
    save_test_reviewer(server)
    item = guided_next(server, after=None)
    preview = guided_preview(server, item, item["choices"][0])
    before = server.session.state_revision
    assert guided_next(server, after=item["item_ref"])["item_ref"] != item["item_ref"]
    assert server.session.state_revision == before
    apply_guided_preview(server, preview)
    assert server.session.state_revision == before + 1
```

- [ ] **Step 2: Run tests and verify missing functions**

```powershell
python -m pytest tests/test_r4_review_ui.py tests/test_r4_review_server.py -k "opaque_choices or confirm_advances" -q
```

Expected: failure because guided interaction functions are absent.

- [ ] **Step 3: Render the server-owned guided item**

Implement `renderGuidedItem()` using only `textContent`/created nodes. Render:

```text
phase instruction
source summary
proposal summary
reviewer question
evidence blocks
neutral radio-like choice buttons
Review impact
Skip for now
Technical evidence (collapsed)
```

Do not assign a default choice. Keep the selected choice only in the current
DOM/view state until preview; it is not a semantic write.

- [ ] **Step 4: Implement bounded skip traversal**

```javascript
async function skipGuidedItem() {
  const current = view.guidedItem.item_ref;
  if (view.guidedPassStartRef === null) view.guidedPassStartRef = current;
  view.guidedAfterRef = current;
  const next = await fetchGuidedNext(current);
  if (next.item_ref === view.guidedPassStartRef || next.only_skipped_remain === true) {
    renderSkippedPassComplete(next);
    return;
  }
  view.guidedItem = next;
  renderGuidedItem();
}
```

Skip must issue only GET requests and must not change `state_revision`.

- [ ] **Step 5: Implement readable preview and confirm-and-continue**

Post only `state_revision`, `item_ref` and `choice_ref` to guided preview. Reuse
`/api/apply` with only `state_revision` and `preview_hash`. After apply:

```javascript
view.guidedPassStartRef = null;
view.guidedAfterRef = null;
await refresh();
await loadGuidedNext(null);
```

The dialog primary label is **Confirm and continue**. It shows readable decision
summary, affected/cleared counts, authoring-block consequence and exact refs in
collapsed details.

- [ ] **Step 6: Run UI/server tests and commit**

```powershell
python -m pytest tests/test_r4_review_ui.py tests/test_r4_review_server.py -q
node --check scripts/r4_1_review_ui/app.js
git add scripts/r4_1_review_ui/app.js scripts/r4_1_review_ui/styles.css tests/test_r4_review_ui.py tests/test_r4_review_server.py
git commit -m "feat(r4): guide one accountable decision at a time"
```

---

### Task 7: Complete identity, completion, recovery and Advanced Explorer paths

**Files:**

- Modify: `scripts/r4_1_review_ui/app.js`
- Modify: `scripts/r4_1_review_ui/styles.css`
- Modify: `tests/test_r4_review_ui.py`
- Modify: `tests/test_r4_review_server.py`

- [ ] **Step 1: Write failing three-state and recovery tests**

```python
def test_guided_completion_states_are_distinct() -> None:
    source = (UI_ROOT / "app.js").read_text(encoding="utf-8")
    for expected in (
        "Review incomplete",
        "Review recorded; authoring blocked",
        "Review complete and authoring ready",
    ):
        assert expected in source
```

Add server tests for invalid reviewer refs, stale guided preview, source drift
on restart and journal warning preservation.

- [ ] **Step 2: Run tests and verify missing completion copy**

```powershell
python -m pytest tests/test_r4_review_ui.py tests/test_r4_review_server.py -k "completion_states or stale_guided" -q
```

- [ ] **Step 3: Add guided identity step**

Use the existing `/api/reviewer` route. Show syntax such as `reviewer:son` as an
example only; do not prefill it. Preserve the user-entered value after a 400
response. Advance only after bootstrap returns canonical nonempty
`reviewer_refs`.

- [ ] **Step 4: Add exact completion screens**

Render from `review_complete`, `authoring_ready`, unresolved counts and
`blocking_rejection_refs`. Only the authoring-ready state uses unqualified
success styling. Reuse the exact `/api/export` endpoint and receipt.

- [ ] **Step 5: Implement stale-state and uncertainty recovery**

On 409, refresh bootstrap, discard the preview and reload the same item if it
remains unresolved; otherwise load the earliest unresolved item and display a
plain explanation. When traversal wraps, render **Revisit skipped decisions**;
do not auto-loop.

- [ ] **Step 6: Preserve Advanced Explorer unchanged in capability**

All existing dashboard, filters, pagination, exact evidence, individual action,
export and shutdown controls must remain reachable under Advanced Explorer.
Add a regression static test for every existing renderer and an HTTP replay
using the existing advanced endpoints.

- [ ] **Step 7: Run regressions and commit**

```powershell
python -m pytest tests/test_r4_review_ui.py tests/test_r4_review_server.py tests/test_r4_review_session.py -q
node --check scripts/r4_1_review_ui/app.js
git add scripts/r4_1_review_ui/app.js scripts/r4_1_review_ui/styles.css tests/test_r4_review_ui.py tests/test_r4_review_server.py
git commit -m "feat(r4): complete guided review recovery and handoff"
```

---

### Task 8: Prove guided/advanced semantic equivalence and performance bounds

**Files:**

- Modify: `tests/test_r4_guided_review.py`
- Modify: `tests/test_r4_review_server.py`
- Modify: `tests/test_r4_review_session.py`

- [ ] **Step 1: Add complete guided HTTP replay**

Create `_drive_complete_guided_review(server)` beside the existing advanced
driver. It must use only:

```text
/api/guided/bootstrap
/api/guided/next
/api/reviewer
/api/guided/preview
/api/apply
/api/export
```

For test automation only, choose options by exact fixture policy already used
by `_drive_complete_review`; do not expose that policy through production
guided projections.

- [ ] **Step 2: Assert exact export equivalence**

```python
def test_guided_and_advanced_http_reviews_export_identical_validated_bytes(
    server_fixture,
) -> None:
    guided = server_fixture()
    advanced = server_fixture()
    guided_receipt, guided_raw = _drive_complete_guided_review(guided)
    advanced_receipt, advanced_raw = _drive_complete_review(advanced)
    assert guided_raw == advanced_raw
    assert guided_receipt["sha256"] == advanced_receipt["sha256"]
    assert validate_reviewed_selection_bytes(
        repository_root=ROOT,
        draft_root=guided.session.paths.draft_root,
        selection_raw=guided_raw,
    )["selection_state"] == "reviewed"
```

- [ ] **Step 3: Add no-I/O and bounded-operation counters**

Instrument `_tree_bytes`, `load_selection_context`, `build_review_indexes` and
guided projection builds. Run at least 512 guided reads/previews and 128
applies. Assert:

```python
assert calls == {"tree": 1, "context": 1, "index": 1}
assert service.projection_builds <= applied_revisions + 1
assert service.maximum_projected_targets <= MAX_GUIDED_TARGET_REFS
```

- [ ] **Step 4: Run the exhaustive suite twice**

```powershell
python -m pytest tests/test_r4_guided_review.py tests/test_r4_review_selection.py tests/test_r4_review_session.py tests/test_r4_review_server.py tests/test_r4_review_ui.py -q
python -m pytest tests/test_r4_guided_review.py tests/test_r4_review_selection.py tests/test_r4_review_session.py tests/test_r4_review_server.py tests/test_r4_review_ui.py -q
```

Expected: both runs reach 100% with byte-identical exports and no source rescan.

- [ ] **Step 5: Commit**

```powershell
git add tests/test_r4_guided_review.py tests/test_r4_review_server.py tests/test_r4_review_session.py
git commit -m "test(r4): verify guided review equivalence"
```

---

### Task 9: Update the handoff, smoke-test and close the usability repair

**Files:**

- Modify: `artifacts/review_inputs/r4_1/README.md`
- Modify: `docs/superpowers/plans/2026-08-30-r4-1-supervision-authoring-automation-plan.md`

- [ ] **Step 1: Rewrite the operator start section**

The first instructions must be:

```powershell
python scripts/serve_r4_1_review.py
```

Then:

```text
1. Press Start guided review.
2. Enter your reviewer ref when asked.
3. Read the displayed sentence/evidence and answer the one question.
4. Use Skip for now if uncertain; nothing is recorded.
5. Review impact, then Confirm and continue.
6. Export only when the final screen says authoring ready.
```

Retain disposable smoke paths, restart/resume, exact independent validation,
and the rejected-export warning.

- [ ] **Step 2: Update the progress tracker honestly**

Record:

```text
guided review ready; awaiting accountable completed selection
```

State that Guided Review is presentation assistance only, Advanced Explorer
remains available, all semantic options stay neutral/unselected, and Task 10B
Steps 4B/6 remain unchecked until a real authoring-ready selection exists and
proposal compilation passes.

- [ ] **Step 3: Run a disposable real-browser smoke**

```powershell
$reviewSmoke = Join-Path $env:TEMP ("cemm-r4-guided-smoke-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $reviewSmoke | Out-Null
python scripts/serve_r4_1_review.py --no-open `
  --working (Join-Path $reviewSmoke "working.json") `
  --journal (Join-Path $reviewSmoke "actions.jsonl") `
  --export (Join-Path $reviewSmoke "selection.json")
```

Open the exact printed token URL. Verify Start, identity validation, one
structural skip, one preview/back, one preview/confirm-and-continue, phase
progress, Advanced Explorer, keyboard focus, 375-pixel width, dark mode,
restart/resume and authorized shutdown. Do not copy smoke files into
`artifacts/review_inputs/r4_1`.

- [ ] **Step 4: Run final gates**

```powershell
python -m pytest tests/test_r4_guided_review.py tests/test_r4_review_selection.py tests/test_r4_review_session.py tests/test_r4_review_server.py tests/test_r4_review_ui.py tests/test_r4_authoring_pipeline.py tests/test_r4_authoring.py tests/test_r4_purpose_contracts.py -q
python -m pytest tests/test_r4_supervision_contracts.py -k "sr5_" -q
python -m ruff check scripts/r4_1_guided_review.py scripts/build_r4_1_review_selection.py scripts/r4_1_review_session.py scripts/serve_r4_1_review.py tests/test_r4_guided_review.py tests/test_r4_review_selection.py tests/test_r4_review_session.py tests/test_r4_review_server.py tests/test_r4_review_ui.py
python -m py_compile scripts/r4_1_guided_review.py scripts/build_r4_1_review_selection.py scripts/r4_1_review_session.py scripts/serve_r4_1_review.py
node --check scripts/r4_1_review_ui/app.js
git diff --check
```

Expected: all tests pass; SR5 remains isolated; lint, Python compilation,
JavaScript syntax and diff integrity pass.

- [ ] **Step 5: Commit documentation**

```powershell
git add artifacts/review_inputs/r4_1/README.md docs/superpowers/plans/2026-08-30-r4-1-supervision-authoring-automation-plan.md
git commit -m "docs(r4): hand off guided accountable review"
```

- [ ] **Step 6: Verify and push without rewriting remote history**

```powershell
git fetch origin
git status --short --branch
git rev-list --left-right --count HEAD...origin/codex/r4-1-data-supervision-replay
git push origin codex/r4-1-data-supervision-replay
git rev-list --left-right --count HEAD...origin/codex/r4-1-data-supervision-replay
```

Expected after push: clean worktree and `0 0` divergence.

## Definition of done

- Guided Review is the default and presents one plain-language decision.
- No semantic option is recommended, preselected or synthesized.
- Skip performs no mutation; confirm remains preview-hash/revision bound.
- Cohorts are exact, bounded and exclude exceptions.
- Advanced Explorer retains all existing audit capabilities.
- Guided and advanced complete replays export identical validated bytes.
- Session startup performs the only source/context/index authentication scan.
- Runtime, activation, release topology and active semantic ABIs are unchanged.
- Documentation makes the reviewer task understandable without reading code.
- A real-browser smoke and all automated final gates pass before completion is claimed.
