# R4 Closure Slice and Anti-Recursion Design

**Date:** 2026-09-03
**Status:** approved governing design; execution requires the linked plan
**Scope:** the only executable next step for `hybrid_mvp/` R4.1

This design is subordinate only to `AGENTS.md` and the August 29 R4.1
data/supervision amendment. It constrains the older R4.1 replay and
source-readiness plans until the closure result is recorded. Current replay
status remains owned only by `governance/replay_status.jsonl`.

Executable steps are owned only by the
[R4 closure-slice implementation plan](../plans/2026-09-03-r4-closure-slice-implementation-plan.md).

## 1. Decision

Bulk R4.1 source authoring, purpose allocation, realization-recipe review,
corpus expansion, package publication and R5 work are frozen. The fixed closure
slice is the only executable next step.

The slice is a bounded falsification test of the existing semantic and
supervision architecture. It must prove that difficult, practically useful
inputs can traverse the intended meaning and response boundaries before any
content-addressed bulk review is regenerated.

R5 remains unavailable. The slice creates no admission, phase promotion,
reviewed source package, train capability or root-adoption claim.

## 2. Evidence and root cause

R4 remained inside source-readiness Task 3 while successive review,
pre-review, worksheet, recipe and UI mechanisms accumulated and
`data/review/r4_1/` remained absent. Downstream review identities are
content-addressed, so correcting one upstream source meaning invalidates
recipes, partitions and selections derived from it.

The recurring process was:

```text
generate downstream review material
→ discover an upstream semantic defect
→ extend the review mechanism
→ regenerate identities
→ invalidate earlier decisions
→ repeat
```

The earliest procedural defect is bulk downstream review before source-level
representational closure. This design reverses that order.

## 3. Fixed closure cases

The implementation plan may normalize punctuation but must not expand this
semantic case set:

1. known definition query: `What is CEMM?`;
2. unknown designation query: `What is zorbulate?`;
3. capability query: `Can you learn aliases?`;
4. discourse-history query: `You said what?`;
5. contextual fragment with a resolving antecedent: `That you learn.`;
6. the same fragment without a resolving antecedent;
7. negated relation: `Alice does not like the book.`;
8. conflict: `The server is online and offline.`;
9. linked simulation: `If the server is online, then the lamp is on.`;
10. non-conflict multiple roots: `The server is offline. You said goodbye.`;
11. denied operation: `Set the state without permission.`; and
12. one invalid Program ABI 2 mutation supplied directly to VERIFY, never as a
    phrase-dispatch target.

The two contextual-fragment rows deliberately share one surface and differ in
situation context. The result must therefore depend on verified context rather
than phrase identity.

## 4. Required vertical path

Every surface case must traverse existing owners in order:

```text
surface + exact context
→ form evidence and designations
→ semantic contributions
→ SemanticSwitchProgram ABI 2
→ canonical SemanticExpression ABI 1
→ VerifiedMeaning
→ situated Decision
→ Effect or No-Effect
→ ResponseMeaning ABI 2
→ authorized surface
→ round-trip semantic equivalence
```

Program identity remains derivation lineage, never meaning identity. Unknown
knowledge, unknown designation, unresolved context, denied permission,
semantic conflict, verifier rejection, proposal abstention and realization
failure must remain distinct results.

## 5. Practical usability

The slice is not complete merely because graph bytes compile. Its public
results must be useful and intelligible:

- known queries receive an exact supported answer;
- an unknown designation preserves the query and literal, reports that the
  meaning is not known and may invite the user to explain it;
- a discourse-history query consults verified session history;
- a contextual fragment resolves when its antecedent exists and reports the
  unresolved reference when it does not;
- denial explains the missing permission without pretending the request was
  meaningless;
- conflict asks for clarification;
- observation, simulation and multiple-root results preserve their exact
  propositions; and
- no normal case may realize as generic `Acknowledged.` or a UI placeholder.

All emitted surfaces must reconstruct the exact response subject, action,
perspective, epistemic status, modality, polarity and required literals.

## 6. Hard work limits

The closure slice permits:

- one existing test owner extended with the fixed cases;
- one bounded diagnostic runner only if the existing test owner cannot expose
  the public path;
- modifications to the earliest failing existing semantic owner; and
- exact documentation needed to record the result.

It enforces all of the following:

- maximum three owner-level implementation fixes;
- maximum three implementation commits before a pass/fail decision;
- one active blocker at a time;
- no new ABI;
- no new phase;
- no new gate;
- no new runtime owner, service, review UI or source package;
- no bulk scenario, worksheet, purpose or artifact regeneration;
- no model training, epoch tuning or R5 implementation; and
- no opportunistic refactor or unrelated cleanup.

Each implementation commit must move at least one named closure case through a
previously failing existing boundary. A change that only adds planning,
tracking, presentation or review machinery is ineligible.

## 7. Pass and stop outcomes

The slice passes only if all twelve cases satisfy the exact path and practical
usability requirements with no forbidden mechanism. Passing records a bounded
diagnostic receipt and unlocks a separately reviewed implementation plan for
mechanical R4.1 source correction under the existing ABIs and gates.

If three owner-level fixes do not make the fixed slice pass, work stops. The
first unresolved owner is recorded as the architecture blocker. Corpus review,
expansion and training remain prohibited until that single boundary receives a
new reviewed design.

New competency requests discovered during the slice are deferred. They do not
expand the fixed case set unless an existing case cannot express an invariant
already required by `AGENTS.md`.

## 8. Suspended workflows and preserved evidence

The accountable review UI, guided review, reviewer-identity repair, assistant
pre-review and supervision-authoring automation documents are superseded as
execution instructions. Their source and artifacts remain historical evidence.
Review workflows are suspended; active working selections must not be exported
or treated as reviewed gold.

The older R4.1 replay and source-readiness plans remain governing constraints
for work after a passing closure result, but they authorize no current bulk
execution while this design is active.

## 9. Definition of completion

This design tranche is complete when:

1. document authority, `AGENTS.md`, routing docs and operational tracker agree;
2. stale review execution documents are classified as superseded and carry a
   prominent successor banner;
3. active review inputs are clearly suspended and preserved;
4. one implementation plan covers only the fixed closure slice; and
5. the user reviews that written plan before code execution.
