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
compile reviewed structural contracts using pinned semantic authority, but it
must not call PROPOSE, VERIFY, EVALUATE, EFFECT, REALIZE, a learned model, the
bootstrap proposer, or an observed episode. `scripts/expand_r4_cases.py` is
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

Blueprint actions use case-local bounded integer selector handles. Each handle
resolves through exactly one immutable `SelectorBinding` carrying:

- the handle;
- the expected graph-component identity;
- the expected semantic kind;
- an exact source `SourceSpan` over the reviewed expanded-case surface; and
- the source-local selector value required by the Program ABI 2 action.

Handles are dense, unique and bounded per case. Bindings are immutable,
content-addressed and validated before any blueprint action is compiled. An
action cannot supply a raw phrase, regex, internal-ref spelling, unbound local
ref, bootstrap candidate or observed program identity. All source spans satisfy
`0 <= start < end <= len(surface)` and must slice the reviewed surface exactly.

## 5. Realization Supervision ABI 1 in-place repair

Realization Supervision ABI 1 is also unpublished and is repaired in place.
Canonical `epistemic_status:*` refs are required at their earliest owners: the
scenario assertion compiler, expected response contract, ResponseMeaning
construction and realization supervision signature. Bare status strings may
not be normalized only at the final supervision decoder.

The response signature includes `expected_expression_relation` as well as the
complete expression set, bindings, discourse action, polarity, modality,
epistemic status, speaker, addressee and semantic slots. This prevents a
single-expression response and an unresolved conflict response from sharing a
signature.

For the present audited universe, exactly the 248 semantic cases are
realizer-eligible and each receives exactly one initial reviewed realization
row. The 112 gap, 20 verification-rejection and 20 restart-diagnostic
candidates receive no realization row in the first publication. A later ABI 1
bundle may contain up to four reviewed variants per eligible case, but initial
publication deliberately contains one. Bundle-wide eligibility and
completeness remain the owner of main replay Task 6; the source decoder only
enforces row-local exactness and bounded variants.

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

## 7. Trust, performance and gate budget

- No new validation tier, phase, owner or pytest process is introduced.
- Corrected tests join existing R4 selectors and run in their existing single
  process.
- No corrected source owner is imported by the normal runtime hot path.
- Source files are decoded once; joins use bounded indexes.
- Source expansion is bounded by scenarios, surfaces, environments, actions,
  selector bindings, graph depth, realization variants, slots, alignments,
  groups, memberships, components and denominator rows.
- The solver is not called during source validation, worksheet generation,
  build or admission.
- No runtime, bootstrap, model, solver or observed output may author a source
  classification, expression, selector binding, response surface, mutation
  truth, purpose or minimum.

## 8. Human structural decisions

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
must identify every proposed row and decision explicitly and remain outside
`data/review/r4_1/`. A draft is not authority merely because it is canonical,
complete or compiler-valid.

## 9. Resume condition

Main replay Task 4 may resume only after SR1-SR5 of the companion correction
plan are implemented, all existing R4 owners and source-only inventories pass,
and a human records one exact approval covering the successor source universe
and all section 8 decisions. SR6 records that approval and stops. Task 4 then
checks in the approved source package under the existing publication and review
gates; the correction plan itself never checks in `data/review/r4_1/`.
