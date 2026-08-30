# R4.1 reviewer-selection handoff

This directory is operational review material only. It is not semantic
authority, a reviewed source package, a review manifest, or an activation
gate.

`SELECTION_TEMPLATE.json` is deterministically generated from the exact
non-authoritative worksheet draft. Keep the template unchanged and make a
working copy named `SELECTION.json` for accountable review.

The template contains 1,056 bounded review targets:

- 12 structural decisions;
- 600 purpose, duplicate-group, challenge-holdout and denominator decisions;
- 56 normalized proposal-family decisions; and
- 388 exact designation candidate-set decisions.

Review in this order:

1. Add the exact frozen `reviewer_refs` and choose one allowed option for every
   structural decision. The generator-patch choice must match the legacy
   conditional branch. Rejecting a composed-expression proposal or the
   restart-diagnostic source makes its dependent purpose, recipe and
   designation targets inapplicable; leave those fields empty.
2. Choose one allowed option for every purpose decision. Review duplicate-risk
   groups and challenge holdouts before direct case assignments so related
   cases cannot leak across purposes.
3. For each proposal family, partition its complete `member_case_refs` into
   `purpose_recipes` consistent with the selected purpose decisions. A family
   used in more than one purpose requires independent purpose-scoped recipe
   entries; it may not share recipe identity or ancestry across purposes.
4. Review every designation set against its exact source geometry and
   authority fact refs. Use `approve_candidate_bindings` only for the exact
   listed set, `approve_exact_empty` only for an empty reviewed gap/rejection
   set, or `reject` and repair the earliest authority/geometry owner before
   regenerating the draft.
5. Change `selection_state` to `reviewed` only after every target is resolved.

Do not add `source_review`, manifest, bundle, `PurposeContract`,
`ProposalTarget`, or other final child identities to this file. Those are
computed only after the completed selection bytes pass strict reconstruction
and become an authenticated input to the final draft.

Validate a completed working copy with:

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
