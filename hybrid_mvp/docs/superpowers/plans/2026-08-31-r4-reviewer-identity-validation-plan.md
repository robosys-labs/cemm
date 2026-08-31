# R4.1 Reviewer Identity Validation Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Guided Review's opaque reviewer-reference failure with exact, accessible guidance while preserving the canonical Python identity contract.

**Architecture:** Keep `ReviewSession.set_reviewers` and `exact_reviewer_refs` authoritative. Add route-local public error translation for bypassed or malformed requests, and one shared JavaScript parser/validity presenter used by both Guided Review and Advanced Explorer before either submits. Do not normalize, invent, designate or admit reviewer identities.

**Tech Stack:** Python 3.11+, loopback `http.server`, plain HTML/JavaScript, pytest, Ruff, Node syntax checking.

---

## File map

- Modify `scripts/serve_r4_1_review.py`: translate only reviewer-route validation failures into stable public guidance.
- Modify `scripts/r4_1_review_ui/app.js`: share exact reviewer parsing and accessible inline invalid-state presentation across both identity forms.
- Modify `scripts/r4_1_review_ui/styles.css`: style the inline error with the existing danger token.
- Modify `tests/test_r4_review_server.py`: prove malformed requests do not mutate state and return actionable guidance.
- Modify `tests/test_r4_review_ui.py`: freeze shared validation, accessibility and no-normalization contracts.

No schema, worksheet, authority, runtime, ABI, generated artifact, endpoint,
dependency or release gate changes.

---

### Task 1: Translate reviewer-route validation failures

**Files:**

- Modify: `tests/test_r4_review_server.py`
- Modify: `scripts/serve_r4_1_review.py`

- [ ] **Step 1: Write the failing server regression test**

Add beside `test_reviewer_route_mutates_only_at_exact_revision`:

```python
def test_reviewer_route_returns_public_format_guidance_without_mutation(
    server_fixture,
) -> None:
    server = server_fixture()
    status, _, raw = request(
        server,
        "POST",
        "/api/reviewer",
        body={"state_revision": 0, "reviewer_refs": ["Son Ofem"]},
        headers=_api_headers(server, post=True),
    )

    envelope = json.loads(raw)
    assert status == 400
    assert envelope["error"] == (
        "Reviewer ref must use reviewer:<identity> with no spaces."
    )
    assert envelope["state_revision"] == 0
    assert server.session.state["reviewer_refs"] == []
```

- [ ] **Step 2: Run the test and verify the current internal message fails it**

Run:

```powershell
python -m pytest tests/test_r4_review_server.py::test_reviewer_route_returns_public_format_guidance_without_mutation -q
```

Expected: FAIL because the response contains
`reviewer_refs item is not an admitted reference`.

- [ ] **Step 3: Add one route-local public error constant and translation**

Near the server constants add:

```python
REVIEWER_REF_GUIDANCE = (
    "Reviewer ref must use reviewer:<identity> with no spaces."
)
```

In the `/api/reviewer` branch, retain the exact-list check, then wrap only the
existing reviewer mutation:

```python
try:
    self.server.session.set_reviewers(tuple(refs))
except (TypeError, ValueError) as exc:
    raise ValueError(REVIEWER_REF_GUIDANCE) from exc
```

Do not change `_handle_failure`, `ReviewSession.set_reviewers` or
`exact_reviewer_refs`.

- [ ] **Step 4: Run focused server tests**

Run:

```powershell
python -m pytest tests/test_r4_review_server.py -k "reviewer_route or authorization_controls" -q
python -m ruff check scripts/serve_r4_1_review.py tests/test_r4_review_server.py
```

Expected: all selected tests pass and Ruff reports `All checks passed!`.

- [ ] **Step 5: Commit the server boundary repair**

```powershell
git add scripts/serve_r4_1_review.py tests/test_r4_review_server.py
git commit -m "fix(r4): explain invalid reviewer references"
```

---

### Task 2: Validate reviewer refs accessibly before submission

**Files:**

- Modify: `tests/test_r4_review_ui.py`
- Modify: `scripts/r4_1_review_ui/app.js`
- Modify: `scripts/r4_1_review_ui/styles.css`

- [ ] **Step 1: Write the failing static UI contract**

Add:

```python
def test_reviewer_forms_share_exact_accessible_local_validation() -> None:
    source = (UI_ROOT / "app.js").read_text(encoding="utf-8")

    for required in (
        "const reviewerRefPattern",
        "const reviewerRefGuidance",
        "function parseReviewerRefs",
        "function setReviewerValidity",
        'input.setAttribute("aria-invalid", "true")',
        'input.removeAttribute("aria-invalid")',
        "Reviewer ref must use reviewer:<identity> with no spaces.",
    ):
        assert required in source
    assert source.count("parseReviewerRefs(input.value") == 2
    assert 'replace(/^reviewer:/,' not in source
    assert 'startsWith("reviewer:") ?' not in source
```

- [ ] **Step 2: Run the UI test and verify the shared validator is absent**

Run:

```powershell
python -m pytest tests/test_r4_review_ui.py::test_reviewer_forms_share_exact_accessible_local_validation -q
```

Expected: FAIL because the shared parser and accessible validity presenter do
not exist.

- [ ] **Step 3: Add the shared exact parser and validity presenter**

Near the view constants in `app.js` add:

```javascript
const reviewerRefPattern = /^reviewer:[^\s:][^\s]*$/u;
const reviewerRefGuidance = "Reviewer ref must use reviewer:<identity> with no spaces.";

function parseReviewerRefs(value, multiple) {
  const refs = (multiple ? value.split(",") : [value])
    .map((item) => item.trim())
    .filter(Boolean);
  if (!refs.length || refs.some((ref) => !reviewerRefPattern.test(ref))) return null;
  return Array.from(new Set(refs)).sort();
}

function setReviewerValidity(input, error, valid) {
  error.hidden = valid;
  if (valid) {
    input.removeAttribute("aria-invalid");
    return;
  }
  input.setAttribute("aria-invalid", "true");
  input.focus();
}
```

For the Advanced form, append one initially hidden error paragraph:

```javascript
const error = node("p", "field-error", reviewerRefGuidance);
error.id = "reviewer-error";
error.hidden = true;
error.setAttribute("role", "alert");
input.setAttribute("aria-describedby", "reviewer-help reviewer-error");
```

For the Guided form, assign `guided-reviewer-help` to its existing help node
and append:

```javascript
help.id = "guided-reviewer-help";
const error = node("p", "field-error", reviewerRefGuidance);
error.id = "guided-reviewer-error";
error.hidden = true;
error.setAttribute("role", "alert");
input.setAttribute(
  "aria-describedby",
  "guided-reviewer-help guided-reviewer-error"
);
```

Each submit handler must call exactly:

```javascript
const refs = parseReviewerRefs(input.value, true); // Advanced
const refs = parseReviewerRefs(input.value, false); // Guided
if (refs === null) {
  setReviewerValidity(input, error, false);
  return;
}
setReviewerValidity(input, error, true);
```

Then submit `refs` unchanged. Add an `input` listener that calls
`setReviewerValidity(input, error, true)` so correction clears the message.

- [ ] **Step 4: Add minimal error styling**

Reuse the existing error color token in `styles.css` only if the new
`field-error` class is not already styled:

```css
.field-error {
  color: var(--color-danger);
  margin: 0;
}
```

Do not add layout, framework or component changes.

- [ ] **Step 5: Run UI safety and syntax tests**

Run:

```powershell
python -m pytest tests/test_r4_review_ui.py -q
node --check scripts/r4_1_review_ui/app.js
git diff --check
```

Expected: UI tests reach 100%, Node emits no error, and diff integrity passes.

- [ ] **Step 6: Commit the browser repair**

```powershell
git add scripts/r4_1_review_ui/app.js scripts/r4_1_review_ui/styles.css tests/test_r4_review_ui.py
git commit -m "fix(r4): validate reviewer identity before submit"
```

---

### Task 3: Verify, restart and retry the live review

**Files:**

- No additional production files.

- [ ] **Step 1: Run the focused regression set**

```powershell
python -m pytest tests/test_r4_review_ui.py tests/test_r4_review_server.py tests/test_r4_review_session.py -q
python -m ruff check scripts/serve_r4_1_review.py tests/test_r4_review_server.py tests/test_r4_review_ui.py
python -m py_compile scripts/serve_r4_1_review.py
node --check scripts/r4_1_review_ui/app.js
git diff --check
```

Expected: all tests pass; lint, compilation, JavaScript syntax and diff
integrity are clean.

- [ ] **Step 2: Stop the current server without deleting working state**

Send `Ctrl+C` to the active `python scripts/serve_r4_1_review.py` process. Do
not delete `artifacts/review_inputs/r4_1/SELECTION_WORKING.json` or the audit
journal.

- [ ] **Step 3: Relaunch the merged local UI**

From `hybrid_mvp` run:

```powershell
python scripts/serve_r4_1_review.py
```

Open the newly printed token URL; the prior token must not be reused.

- [ ] **Step 4: Retry exact reviewer identity behavior**

Verify:

1. `Son Ofem` is rejected locally with the public guidance and no revision
   change;
2. `reviewer:son` saves successfully unchanged and advances to the first
   structural decision;
3. Advanced Explorer uses the same guidance;
4. refresh/resume retains the saved reviewer identity.

If the supported browser runtime remains unavailable, keep the server open and
hand the new token URL to the user for this exact four-item smoke; do not claim
browser automation.

- [ ] **Step 5: Reconcile and commit this plan**

Mark completed steps only after their commands pass, then run:

```powershell
git add docs/superpowers/plans/2026-08-31-r4-reviewer-identity-validation-plan.md
git commit -m "docs(r4): record reviewer identity repair"
```
