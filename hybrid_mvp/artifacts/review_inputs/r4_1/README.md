# R4.1 reviewer-selection handoff

This directory is operational review material only. It is not semantic
authority, a reviewed source package, a review manifest, or an activation
gate.

`SELECTION_TEMPLATE.json` is deterministically generated from the exact
non-authoritative worksheet draft. Keep the template unchanged. The supported
review path creates its own unresolved working state and exports
`SELECTION.json` only after exact validation.

The template contains 1,056 bounded review targets:

- 12 structural decisions;
- 600 purpose, duplicate-group, challenge-holdout and denominator decisions;
- 56 normalized proposal-family decisions; and
- 388 exact designation candidate-set decisions.

## Launch and resume

From `hybrid_mvp`, launch the offline loopback reviewer:

```powershell
python scripts/serve_r4_1_review.py
```

The process binds only to `127.0.0.1` on an ephemeral port and opens a URL with
an unguessable session token. It has no CDN, framework, network-data, runtime,
activation or release-gate dependency. Keep the terminal open while reviewing.
Use the **Stop local server** control or `Ctrl+C` when finished.

The default local files are:

- `SELECTION_WORKING.json`: canonical resumable state after every confirmed
  action;
- `REVIEW_ACTIONS.jsonl`: append-only review-action audit journal; and
- `SELECTION.json`: final validated export, created only on explicit export.

Restart the same command to resume. Startup reauthenticates the draft and
template, refuses stale or noncanonical working bytes, and reconstructs its
bounded indexes once. The journal is advisory audit evidence: a journal problem
is displayed as a warning but cannot replace or modify the canonical working
state.

For a disposable smoke review, keep all outputs outside the authoritative
handoff paths:

```powershell
python scripts/serve_r4_1_review.py --no-open `
  --working $env:TEMP\cemm-r4-review-working.json `
  --journal $env:TEMP\cemm-r4-review-actions.jsonl `
  --export $env:TEMP\cemm-r4-review-selection.json
```

Open the exact printed URL, including its `#token=...` fragment. Do not reuse a
URL from an earlier server process.

## Accountable review lifecycle

Enter canonical `reviewer_refs` before confirming decisions, then complete the
five phases in order:

1. **Structural:** choose one allowed option for every structural decision.
   The generator-patch choice must match the legacy
   conditional branch. Rejecting a composed-expression proposal or the
   restart-diagnostic source makes its dependent purpose, recipe and
   designation targets inapplicable; leave those fields empty.
2. **Purpose:** choose one allowed option for every purpose decision. Review
   duplicate-risk groups and challenge holdouts before direct case assignments
   so related cases cannot leak across purposes. Cohort actions require an
   impact preview and explicit confirmation; the UI never silently selects a
   purpose.
3. **Recipes:** for each proposal family, partition its complete
   `member_case_refs` into
   `purpose_recipes` consistent with the selected purpose decisions. A family
   used in more than one purpose requires independent purpose-scoped recipe
   entries; it may not share recipe identity or ancestry across purposes.
4. **Designations:** review every designation set against its exact source
   geometry and authority fact refs. Routine sets may be confirmed only through
   their exact displayed cohort. Empty, overlapping, multi-unit or polysemous
   exceptional sets require individual review. Use
   `approve_candidate_bindings` only for the exact listed set,
   `approve_exact_empty` only for an empty reviewed gap/rejection set, or
   `reject` and repair the earliest authority/geometry owner before regenerating
   the draft.
5. **Export:** inspect completion and authoring-ready status, then explicitly
   validate and export. The server reconstructs the selection from working
   state and reauthenticates the exact source before writing `SELECTION.json`.

Every mutating action first shows an exact impact preview. Cancel records
nothing; confirm checks the preview hash and current state revision before an
atomic write. A completed review can be export-valid while still containing
rejection decisions. Such an export records accountable review but does **not**
unblock Task 10B proposal expansion; `authoring_ready` must also be true.

Do not add `source_review`, manifest, bundle, `PurposeContract`,
`ProposalTarget`, or other final child identities to this file. Those are
computed only after the completed selection bytes pass strict reconstruction
and become an authenticated input to the final draft.

Independently validate the exported selection with:

```powershell
python scripts/build_r4_1_review_selection.py --root . `
  --draft artifacts/review_drafts/r4_1 `
  --validate-selection artifacts/review_inputs/r4_1/SELECTION.json
```

The validator requires exact worksheet joins, canonical reviewer refs, one
available option for every applicable row, branch-aware purpose ownership,
structural-proposal and diagnostic applicability, holdout and denominator
consistency, purpose-local proposal-family partitions, and exact designation
decisions. Until it passes, the working copy remains inert. Exact
proposal/derivation expansion is the next implementation step after
accountable selections exist.
