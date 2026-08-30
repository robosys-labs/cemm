# R4.1 Source-Readiness Correction Design

**Status:** approved pre-source correction; governing within `hybrid_mvp/`

**Scope:** repair the unpublished R4.1 reviewed-source ABIs and the canonical
source universe before any `data/review/r4_1/` bytes are checked in. This
document does not admit R4, publish an artifact, approve reviewed data, or
authorize root adoption.

## 1. Why Task 4 is blocked

The Task 3 loader is fail-closed and the reviewed source directory remains
absent, but a pre-source audit found that the current source model cannot yet
encode the review outcome without ambiguity or self-authorship. Checking in
rows now would freeze defects into content-addressed identities and force later
repair through a needless ABI migration.

Task 4 and the source-freeze checkpoint are therefore blocked. No file beneath
`data/review/r4_1/` may be created, staged, reviewed as final, or named by a
manifest until this correction is implemented and a human approves the exact
source-readiness worksheets. Runtime output, solver output, bootstrap programs,
observed candidates and compiler success are never substitutes for that review.

## 2. Reconstructed source universe

The audit reconstructed the current source through the model-free scenario and
surface/environment expansion boundary rather than through runtime episodes.
The exact present universe is:

| Boundary | Exact count | Interpretation |
|---|---:|---|
| reviewed scenario rows | 210 | current checked-in scenario source |
| expanded source cases | 400 | deterministic source expansion |
| semantic supervision candidates | 248 | cases with structured semantic assertions |
| explicit gap candidates | 112 | cases whose structured gap assertion is the sole gap owner |
| adversarial verification-rejection targets | 20 | adversarial programs that must be rejected by verification, not learned as generic gaps |
| restart diagnostic candidates | 20 | restart observations requiring an explicit human diagnostic-only decision |

The four expanded classifications are disjoint and sum to 400. These numbers
describe the audited current source, not a reviewed R4.1 package. The required
structural additions in section 8 will produce a successor source identity and
successor counts; those counts must be recomputed by the corrected model-free
expander and approved rather than inferred here.

The audit also disproved an earlier multi-root assumption. Current
`conflict`/conflict-set assertions describe alternative complete meanings that
must remain in competition. They do not assert simultaneous independent roots.
Reinterpreting a conflict set as a multi-root expression would manufacture
semantic structure. The current source does not provide the true non-conflict
multi-root coverage needed by R4.1.

The audit subsequently found a second, earlier representation defect: the
reviewed-assertion compiler can compile only single-root assertions or several
separate expressions. It never constructs an `ExpressionLink`, and several
ordinary assertions become `ExpressionRelation.ALL`. Proposal Supervision ABI
1 intentionally cannot admit that relation. A worksheet cannot repair this by
writing expression bytes directly because that would bypass the canonical
reviewed source owner.

Before worksheet generation, Reviewed Assertion ABI 1 therefore receives one
in-place vocabulary correction before any canonical R4.1 reviewed source
package is published or admitted: a generic, closed
`composed_expression` assertion. It declares bounded local applications,
explicit expression links and exact roots, plus an optional semantic mode. Its
top-level shape is exactly `linked` or `multi_root`; conflict is never a shape.
Application fillers form a closed grounded/literal/proposition-node union.
Local identifiers are graph construction labels only and never semantic refs,
surface phrases, Program actions or persistent identity.

The existing expected-contract compiler resolves those labels through bounded
indexes, validates every grounded predicate and filler against the linked
authority, enforces five-operator and role compatibility, and constructs all
content-addressed node refs itself. Existing Semantic Expression ABI 1
canonicalization remains the sole graph validator for reachability, one-parent
ownership, roots, arity, acyclicity and depth. A linked assertion must contain
at least one reviewed expression link and exactly one link root. A multi-root
assertion must contain no links and exactly two through eight application
roots. Both compile to exactly one `SemanticExpression` and therefore relation
`single`; separate assertions remain `all`, and conflicts remain alternative
complete expressions with relation `conflict`.

This is a source-compiler capability repair, not approval of any proposed
meaning. Existing ABI-1 rows, all 210 scenario rows and their 400-case source
universe remain byte- and behavior-identical. The human review still chooses the exact eight successor rows,
link types, meanings, surfaces and modes. No ABI 2, compatibility fallback,
new gate, runtime scan or source package is introduced.

## 3. Source-universe hard cut

`expected_gap_kind` is a duplicate and weaker owner. It must be removed from
the generator, checked-in scenario rows, active scenario decoders, expansion
path and tests. A structured `gap` assertion is the only source of a typed gap.
Contradictory or missing duplicate fields can no longer be normalized away.

The 20 adversarial cases lower to an explicit
`verification_rejection` proposal target. They are not typed abstentions and do
not authorize a runtime failure label. The 20 restart cases remain diagnostic
candidates until the human decision in section 8; they cannot silently enter a
supervised purpose.

Source expansion must have one public, deterministic, model-free seam. It may
compile reviewed structural contracts using authenticated semantic authority,
but it must not accept a caller-supplied `RevisionPin`. The seam internally
derives an exact source-only pin from the authenticated authority generation,
with world, session, episode and effect revisions all zero and
`model_identity: null`. A dedicated immutable source snapshot with those exact
semantics is an equivalent implementation. Hostile caller state and a model
identity can therefore never enter source-case identity.

The seam must not call PROPOSE, VERIFY, EVALUATE, EFFECT, REALIZE, a learned
model, the bootstrap proposer or an observed episode. The seam guarantees
bounded consumption before materialization for scenario iterables, per-scenario
environment iterables and the aggregate expanded-case stream. It rejects a
hostile or infinite iterator at the configured next-item bound and exposes
deterministic operation counters; converting an unbounded iterable to `tuple`
or `list` before the bound is forbidden. `scripts/expand_r4_cases.py` is
currently broken because it constructs `CaseExpander` without its required
compiler and passes a contract as the `revision_pin`. The correction restores
the repository-owned seam and makes the CLI a thin consumer of it.

## 4. Proposal Supervision ABI 1 in-place repair

Proposal Supervision ABI 1 is unpublished. It is repaired in place instead of
minting ABI 2.

`match_policy` is always `exact` and owns complete canonical equality. It is
separate from `expected_expression_relation`, whose closed values are:

- `none` for a typed abstention or verification-rejection target;
- `single` for exactly one complete expected expression;
- `conflict` for two or more alternative complete expressions.

A conflict relation never means multi-root and never licenses subset,
intersection or application-set matching.

Blueprint actions use case-local bounded integer selector handles.
`SelectorBinding` is a closed tagged union:

- `GroundedSelectorBinding` carries case and surface identity, expected graph-
  component identity, expected semantic kind, one or more exact `SourceSpan`
  values, and the reviewed source-unit/contribution selector needed by a
  Program ABI 2 action;
- `StructuralSelectorBinding` carries only a typed Program-local identity for a
  declaration, local ref, structural tag, closed literal, mode or context
  constant that is not grounded in an observed unit.

The structural variant cannot carry source spans, case/surface evidence,
semantic kind or pretend to be grounded authority. The grounded variant cannot
omit them. Handles are dense, unique and bounded per case. Bindings are
immutable, content-addressed and validated before any blueprint action is
compiled. An action cannot supply a raw phrase, regex, internal-ref spelling,
unbound local ref, bootstrap candidate or observed program identity. Every
grounded span satisfies `0 <= start < end <= len(surface)` and slices the exact
reviewed surface.

Each derivation also owns a complete bounded `SourceAssignmentBlueprint`.
Every entry names source geometry or a source-unit selector, contribution kind,
assignment kind, target action and role when consumed, residual kind when
retained, and exact criticality. Across one derivation, every observed unit is
covered exactly once: it is consumed into one semantic role or retained as one
typed residual. Critical residuals make the target non-executable. No compiler
may infer assignments from action shapes or fill omitted coverage.

`target_kind: verification_rejection` is an exact fourth proposal outcome,
separate from derive, typed abstention and diagnostic exclusion. Its reviewed
contract contains no expression refs and owns the adversarial or mutation
blueprint/payload, expected VERIFY owner, expected error code, rejection
disposition and criticality. It cannot be folded into a generic gap or inferred
from observed verifier output.

## 5. Realization Supervision ABI 1 in-place repair

Realization Supervision ABI 1 is also unpublished and is repaired in place.
Canonical `epistemic_status:*` refs are required at their earliest owners: the
scenario assertion compiler, expected response contract, ResponseMeaning
construction and realization supervision signature. Bare status strings may
not be normalized only at the final supervision decoder.

The response signature contains a closed tagged response subject:

- `expression_set` with `expected_expression_relation` equal to `single` or
  `conflict` and the complete expression set;
- `typed_gap` with relation `none` and one exact typed gap subject;
- `verifier_rejection` with relation `none` and one exact reviewed rejection
  subject.

The signature also covers bindings, discourse action, polarity, modality,
epistemic status, speaker, addressee and semantic slots. This prevents a
single-expression response, unresolved conflict, safe gap response and safe
rejection response from sharing a signature.

Every supervised case receives exactly one initial reviewed realization row:
semantic, explicit gap and verification rejection. Only diagnostic restart
cases are excluded. Later ABI 1 bundles may contain up to four reviewed
variants per supervised case. Eligibility and exact counts are always
successor-universe-derived; neither the decoder nor the plan may hard-code 248
or any audited predecessor count. R5 safe gap and rejection surfaces and their
canaries are explicit publication prerequisites, not deferred UI fallbacks.

Alignment is a closed tagged union:

```text
designation | reference | literal | morphology | omission
```

Every alignment names its tag-specific authority, exact output span and exact
slot. Literal alignment may copy only an independently reviewed literal or a
literal authenticated by the decision, effect or obligation boundary. Neither
`input_surface` nor a row-supplied `source_literal` may authenticate itself.
Every required semantic slot is covered exactly once by a surface alignment or
an explicitly reviewed omission; optional slots cannot create duplicate
coverage.

## 6. Purpose Contract ABI 1 in-place repair

Purpose Contract ABI 1 remains the single owner of partition intent, but group
purpose and member purpose are no longer duplicated:

- a duplicate-risk group owns one purpose;
- a grouped supervised membership has `purpose: null` and inherits the group's
  purpose;
- an ungrouped supervised singleton owns one direct purpose;
- a `verification_rejection` membership is supervised and follows the same
  direct/group purpose rule;
- a diagnostic membership has neither a purpose nor group membership.

Group overlap is resolved through transitive connected components. Every group
within one component must declare the same purpose, and every grouped case must
resolve to exactly that component purpose. Conflict sets do not create groups.
Only explicit reviewed duplicate-risk lineage does.

Denominator minima form one complete Cartesian family: every reviewed
denominator identity appears for all four purposes (`train`, `selection`,
`calibration`, `frozen_test`) with the same `denominator_family`. Missing,
extra or family-drift rows fail before partitioning. Validation constructs
case, group, component, purpose and denominator indexes once, then performs
linear passes over records and memberships. It may not use pairwise whole-
corpus scans or a completion solver.

## 7. Cross-source ownership and gate budget

One bounded cross-source semantic validator lives under the existing
`r4_supervision` authenticated-bundle ownership. It adds no gate, owner or
process. Given one authenticated snapshot, it joins the canonical source
universe, proposal rows, realization rows and purpose contract through indexed
maps and validates:

- every span and grounded selector belongs to its exact case/surface;
- exactly one ProposalTarget exists for every supervised case and none for a
  diagnostic case;
- exactly one initial realization variant exists for every supervised case,
  with at most four variants after initial publication, and none for a
  diagnostic case;
- exactly one PurposeMembership exists for every source case, including the
  `verification_rejection` classification; and
- no source case or source row is missing, duplicated or extra.

Ownership is explicit. JSON Schema owns structural/tag/bound validation. A row
decoder owns content refs and row-local semantic invariants. A file loader owns
canonical bytes, record counts, duplicate row identity and file-local bounds.
The cross-source semantic validator owns case-set completeness and joins. Main
Tasks 5 and 6 own independent compilation and equivalence; they do not discover
eligibility for the first time.

- No new validation tier, phase, owner or pytest process is introduced.
- Corrected tests join existing R4 selectors and run in their existing single
  process.
- No corrected source owner is imported by the normal runtime hot path.
- Source files are decoded once; joins use bounded indexes and linear operation
  counters.
- Source expansion is bounded by scenarios, surfaces, environments, actions,
  selector bindings, assignment blueprints, aggregate cases, graph depth,
  realization variants, slots, alignments, groups, memberships, components and
  denominator rows. Every iterable is bounded while being consumed, before
  materialization.
- The solver is not called during source validation, worksheet generation,
  build or admission.
- No runtime, bootstrap, model, solver or observed output may author a source
  classification, expression, selector binding, response surface, mutation
  truth, purpose or minimum.

The five Task 2/3 ABI registry rows are reconciled exactly once during SR1:
`R4 Review Manifest ABI`, `Proposal Supervision ABI`, `Realization Supervision
ABI`, `Mutation Contract ABI` and `Purpose Contract ABI`. Each row must state
that its strict decoder (and the review-manifest authenticated loader) is
implemented while compiler, reviewed data, publication and admission remain
pending as applicable. Reconciliation makes no activation claim.

## 8. Human structural decisions and canonical patch

The source-readiness review must make all of the following decisions together:

1. Preserve every current conflict set as alternatives; do not reinterpret it
   as multi-root.
2. Approve a conservative eight-family structural addition: four linked-
   proposition families and four true multi-root, non-conflict families.
3. Within the four linked families, include at least two semantic `SIMULATE`
   cases and at least one case proving `op:type` with `role:type`.
4. Select the legacy conditional construction to retain or retire; no parser or
   compiler chooses for the reviewer.
5. Approve or reject diagnostic-only classification for the restart family.
6. Approve the exact designation targets and explicit semantic output surfaces.
7. Approve mutation truth independently of mutation execution.
8. Approve duplicate-risk groups, direct/group purposes, challenge holdouts,
   denominator registry and fixed positive minima.

Draft worksheets may be generated from reviewed source structure only. They
must include the exact proposed scenario patch and generator decisions for all
eight structural families, identify every proposed row and decision explicitly,
and remain outside `data/review/r4_1/`. A draft is not authority merely because
it is canonical, complete or compiler-valid.

The four JSON worksheets share one closed envelope: `schema`,
`worksheet_ref`, `draft_non_authoritative`, `input_set_ref`, `inputs`,
`current_snapshot`, `row_count` and `rows`. Each worksheet defines its own
exact row vocabulary; unknown envelope or row fields fail. `SOURCE_UNIVERSE`
binds every current and proposed scenario/case identity and disposition;
`STRUCTURAL_DECISIONS` binds the legacy conditional, restart diagnostic and
all eight exact composed-expression proposals; `SUPERVISION_DECISIONS` binds
designation, realization and mutation-truth decisions; and
`PURPOSE_DECISIONS` binds duplicate groups, direct/group purposes, holdouts,
denominators and minima. `REVIEW_SUMMARY.md` binds the four worksheet refs,
input-set ref, file lengths and SHA-256 values. No omitted row, empty decision
or prose summary supplies a default answer.

Worksheet generation must fail before creating a staging directory unless
every proposed linked or multi-root row passes through the corrected
reviewed-assertion compiler as exactly one canonical expression with relation
`single`. Relation `all`, `ordered_chain`, multiple non-conflict expressions,
an unresolved structural substitute, an opaque predicate or conflict-as-root
is a source error, not a worksheet decision.

The builder owns one private bounded publication helper; this is not a new
gate, process or repository-wide abstraction. It authenticates independently
generated A/B directories without following links, retains the verified A
bytes, writes the exact five-file set to an exclusive same-parent staging
directory, fsyncs and rereads it, re-authenticates A/B, and atomically renames
the stage only when the final path is absent. A pre-existing final directory is
accepted only as an exact byte-for-byte no-op. Any other existing, missing,
extra, linked or changed file fails closed. Final publication never invokes the
generator again.

## 9. Resume condition

Main replay Task 4 may resume only after SR1-SR4.5 and SR5 of the companion correction
plan are implemented, all existing R4 owners and source-only inventories pass,
and a human approves one exact scenario patch plus all section 8 decisions.

SR6 first applies that exact approved patch to
`scripts/generate_scenarios.py`, regenerates `data/scenarios/use_cases.jsonl`
through the canonical generator, reconstructs the model-free successor
universe, and verifies its identities and successor-universe-derived counts.
That canonical source change is one commit. Only then does a second commit add
the exact approval evidence and operational tracker update. The approval
document is classified exactly once in `docs/DOCUMENT_AUTHORITY.json` as
historical/operational review evidence, with the exhaustive authority-like
classification test updated atomically.

SR6 stops there. Task 4 packages the updated canonical source under
`data/review/r4_1/` and obtains the existing second data review. Neither SR6
commit checks in `data/review/r4_1/`, promotes R4, activates an ABI or publishes
an artifact.
