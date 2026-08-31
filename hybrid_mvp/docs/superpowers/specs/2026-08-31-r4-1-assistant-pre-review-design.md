# R4.1 Assistant Pre-Review Design

**Status:** approved design; implementation planning pending

**Scope:** add an offline, non-authoritative assistant pre-review path for the
R4.1 accountable review selection. The path helps prepare recommendations,
blocker reports and conservative approval cohorts for the human reviewer. It
does not approve semantic gold, mutate `SELECTION.json`, enter activation, add
a runtime dependency or replace careful individual curation.

This document governs only `hybrid_mvp/`. It amends the guided accountable
review workflow by adding an advisory preparation layer beside it, not inside
the final authority boundary.

## 1. Decision Boundary

The approved design is an advisory assistant pre-review ledger. The assistant
may inspect every R4.1 review target, reconstruct available evidence, explain
likely decisions, group low-risk homogeneous cases and identify blockers. The
assistant may not become the accountable reviewer.

The boundary is:

```text
assistant pre-review recommendation != reviewed gold
assistant confidence != semantic authority
candidate output != source truth
displayed summary != source geometry
cohort convenience != individual semantic review
```

Only explicit human approval through the existing review action, preview,
revision and export validation path may write final review selections.
Recommendations remain inert draft material until that approval occurs.

## 2. Problem

The guided reviewer makes R4.1 accountable review usable, but completing all
1,056 targets manually still creates fatigue and repeated mechanical checks.
That fatigue is now a material delivery risk for R4 completion and R5 start.

The recent guided-review session also exposed a deeper risk: a displayed source
summary can appear to preserve a proposal while the exact source geometry,
surface examples or designation spans point at a different sentence order. In
that condition, the reviewer cannot safely approve the card, even if the
rendered proposal text looks correct.

The pre-review layer must therefore reduce repetitive labor only after it has
proved the evidence is reviewable.

## 3. Goals

The pre-review path must:

- audit every current review target from the authenticated R4.1 draft and
  working selection state;
- reconstruct source, proposal, purpose, recipe and designation evidence from
  indexed local inputs;
- quarantine source-display, span-geometry, ref-join and candidate-binding
  inconsistencies before making any recommendation;
- produce one content-addressed advisory ledger record per review target;
- identify conservative approval cohorts only for mechanically homogeneous,
  evidence-consistent decisions;
- preserve individual review for ambiguous, polysemous, conflicting,
  exceptional or semantically judgment-heavy cases;
- make the assistant's rationale inspectable before any human approval; and
- keep the guided accountable reviewer and final selection validator as the
  only mutation and publication path.

## 4. Non-Goals

The pre-review path will not:

- write or export `SELECTION.json`;
- submit review actions under a human reviewer ref without explicit approval;
- recommend a choice for evidence-inconsistent cases;
- override the guided review design's no-recommendation rule inside the
  default guided card flow;
- treat a `SemanticSwitchProgram`, runtime output or candidate surface as
  canonical meaning;
- add a model, service, browser framework, remote API, network retrieval,
  activation phase or release gate;
- broaden review schemas, weaken validators or add fallback interpretations;
  or
- use cohorts for cases that require careful semantic judgment.

## 5. Chosen Approach

Add a local script-driven sidecar that builds advisory outputs under
`hybrid_mvp/artifacts/review_drafts/r4_1/`:

- `PRE_REVIEW_RECOMMENDATIONS.jsonl`;
- `PRE_REVIEW_SUMMARY.md`; and
- optionally `PRE_REVIEW_REPORT.html` when a static human-readable report is
  useful.

The script consumes the same local draft/template/working files used by the
review server. It reuses the existing authenticated loaders and bounded
session indexes where possible. It does not import runtime packages from the
normal core loop and is not imported by runtime code.

The guided reviewer remains neutral. A reviewer can use the report beside the
guided UI, or a later implementation may add a clearly labeled separate
"Assistant pre-review" view. Any such view must preserve the distinction
between recommendation and approval, and final mutation must still go through
the existing Python-owned preview/apply methods.

## 6. Evidence Preflight

Every target first passes a fail-closed preflight. A failed preflight produces
`blocked_evidence_mismatch` or a more specific blocker code and no decision
recommendation.

Required checks include:

- source summary, source-case surface, candidate output and surface examples
  are internally consistent for the target kind;
- every span resolves against the exact surface string named by the owning
  source row;
- designation candidate bindings point to admitted authority-backed
  designation facts and expected target refs;
- proposal summaries are reconstructed from the same expression/proposal row
  being reviewed;
- structural options and generator-patch options use exact available option
  refs only;
- purpose rows preserve duplicate-group, holdout, denominator and partition
  ownership constraints;
- recipe rows remain purpose-local and cannot infer unresolved purpose
  assignments; and
- every advisory record names the source bytes or row digest used to reach its
  conclusion.

The source-order mismatch observed during manual review is a required
regression case for this preflight.

## 7. Recommendation Classes

The ledger uses a closed recommendation vocabulary:

- `approve_candidate`: evidence is internally consistent and the exact allowed
  option appears mechanically correct;
- `reject_and_repair`: evidence is consistent enough to identify that the
  proposed selection is wrong or blocks authoring pending earliest-owner
  repair;
- `needs_individual_review`: semantic judgment, ambiguity, polysemy, conflict,
  exception ownership or reviewer taste is required;
- `blocked_evidence_mismatch`: source/display/geometry/ref evidence is not
  reviewable;
- `blocked_inapplicable`: target is inactive because an upstream decision makes
  it inapplicable; and
- `defer_until_prerequisite`: the target depends on an unresolved earlier
  structural or purpose decision.

Each record includes the exact review action that would be submitted only if
approved, or no action for blocked and individual-review cases.

## 8. Individual Curation Rule

Individual curation is the default whenever correctness depends on meaning
rather than mechanical contract reconstruction.

The following cases must not be placed in approval cohorts:

- any failed evidence preflight;
- any exceptional designation row;
- empty designation sets unless the source classification makes emptiness
  mechanically reviewable;
- overlapping, multi-unit or polysemous designation spans;
- conflict-preservation decisions;
- legacy conditional branch choices;
- restart diagnostic decisions;
- source cases with multiple roots, scopes, references or proposition links
  unless the graph equivalence is independently reconstructed and simple
  enough to explain;
- any row where the assistant rationale uses uncertainty language; and
- any row whose approval would clear or invalidate another already reviewed
  selection.

Cohorts reduce repeated clicking only for homogeneous, low-risk decisions.
They do not reduce evidence requirements.

## 9. Cohort Rules

A cohort is eligible only when all members share:

- one row kind;
- one exact recommendation class;
- one exact allowed action shape;
- compatible option value;
- matching applicability state;
- no evidence blockers;
- no exceptional designation ownership;
- no dependent clear required; and
- a bounded member count within existing review action limits.

The report must show the cohort definition, exact member refs, representative
examples, excluded exceptions and the preview impact expected from applying
the cohort. The human reviewer approves or rejects a cohort explicitly. If a
single member is disputed, the cohort is split or downgraded to individual
review.

## 10. Data Flow

The one-way flow is:

```text
authenticated R4.1 draft + selection template + working state
  -> bounded indexed preflight
  -> advisory recommendation ledger
  -> human inspection and explicit approval
  -> existing preview/apply/export validation
  -> final reviewed selection
```

The ledger and report are operational review drafts. They are not source
packages, manifests, review bundles, activation inputs, training data or
admitted authority.

## 11. Error Handling

The sidecar fails closed:

- malformed or stale inputs abort the run;
- unreadable draft/template/working files abort the run;
- missing source joins produce blocker records, not guessed decisions;
- byte, count and depth bounds are enforced before output;
- noncanonical refs or action shapes are rejected;
- evidence mismatch records include enough exact context for earliest-owner
  repair; and
- generated outputs are written atomically after successful complete
  reconstruction.

## 12. Performance

The sidecar is allowed to perform one complete offline pass over the bounded
R4.1 review universe. It must not add work to the normal runtime cycle, model
training loop, activation import or every guided-review click.

Implementation should reuse cached `ReviewSession` indexes, avoid repeated
full JSON parses inside item loops, cap report examples, and keep HTML static.
No network access or external evidence retrieval is part of this design.

## 13. Testing

Implementation must add focused tests that prove:

- the source-order/span mismatch observed in guided review is quarantined;
- blocked evidence records contain no executable approval action;
- recommendations are deterministic across two runs with identical inputs;
- cohorts exclude individual-curation cases;
- cohort member refs are exact, sorted and bounded;
- advisory outputs do not affect `SELECTION_WORKING.json` or
  `SELECTION.json`;
- runtime packages do not import the pre-review sidecar or UI report; and
- existing review server, guided review and selection-validation tests still
  pass.

## 14. Completion Criteria

This design is complete when:

- the advisory ledger and summary can be generated from current local R4.1
  review inputs;
- evidence-inconsistent cases are reported before any recommendation is made;
- safe cohorts are conservative and inspectable;
- individual-curation cases remain clearly separated;
- no final gold is written without explicit reviewer approval; and
- docs, tests and implementation agree that the sidecar is advisory only.
