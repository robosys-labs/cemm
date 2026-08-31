# R4.1 Guided Accountable Review Design

**Status:** approved design for implementation planning  
**Scope:** offline R4.1 reviewer presentation and bounded review-session API  
**Authority:** presentation assistance only; the accountable reviewer owns every semantic decision

## 1. Problem

The existing accountable review interface is mechanically complete but not
operationally usable by a reviewer who did not implement R4.1. It begins with
inventory totals and raw typed refs, exposes many unresolved cards at once,
uses internal option labels as button text, and does not explain the decision
the reviewer is being asked to make. A reviewer can see the machinery without
knowing the next step, the meaning of an option, or the consequence of a
choice.

This is a presentation and workflow defect. It must not be repaired by
auto-selecting semantic answers, treating a Program as meaning, weakening the
selection validator, or turning the UI into a new source of semantic authority.

## 2. Goal

Make accountable R4.1 review understandable and resumable for a technically
capable reviewer who has not internalized the review ABIs. The default
experience presents one bounded decision at a time, explains what must be
verified in plain language, records nothing until explicit confirmation, and
advances to the next unresolved decision after a successful write.

The reviewer must always be able to answer these questions without opening
source code:

1. What am I reviewing?
2. Why does CEMM need this decision?
3. Which exact evidence supports the available options?
4. What will each option record or invalidate?
5. What should I do if I am uncertain?
6. What remains before proposal authoring can continue?

## 3. Non-goals and fixed boundaries

The guided reviewer will not:

- recommend, preselect, rank, emphasize or auto-confirm a semantic option;
- derive gold labels from runtime output, the current Program or expected data;
- add a fallback, permissive interpretation or new semantic operator;
- convert a friendly display label into an unreviewed designation;
- mark a skipped decision as reviewed;
- hide blocking rejections behind a success state;
- modify runtime, activation, publication or release-gate topology;
- add a framework, CDN, build chain, remote service or network-data dependency;
- add an unbounded scan or rebuild authenticated review context per action; or
- remove the advanced exact-evidence interface required for audit and repair.

The five semantic operators and all active R4.1 selection, purpose, recipe,
designation, content-addressing and validation contracts remain unchanged.

## 4. Chosen approach

The default interface becomes a guided review wizard. The current multi-card
interface remains available as an **Advanced Explorer** for searching,
cross-checking and repairing exact evidence.

This approach is preferred over adding more help text to the existing
dashboard because information density is not the primary defect: the current
screen has no clear task progression. It is preferred over a separate manual
because the instruction, evidence, decision and consequence must remain in one
auditable interaction.

## 5. Reviewer experience

### 5.1 Start or resume

The landing screen uses plain language:

> You are verifying the bounded semantic supervision CEMM will use for R4.1.
> The system will explain each decision and show its evidence. It will not
> choose meaning for you.

The primary action is **Start guided review** or **Resume guided review**. A
secondary **Open Advanced Explorer** action exposes the existing audit view.
Raw inventory counts, hashes and internal identities are subordinate details.

If reviewer identity is missing, the first guided step asks for one or more
canonical reviewer refs, shows the required syntax, validates before saving,
and explains that the identity is attached to every confirmed decision. The UI
must not invent or silently normalize a reviewer identity beyond the existing
canonical ordering and duplicate removal.

### 5.2 Phase progression

The guided path uses the contract-defined order:

1. Structural branch
2. Purpose ownership and leakage controls
3. Purpose-local recipe families
4. Designation candidate sets
5. Completion and export

The UI displays the current phase, completed decisions, unresolved decisions
and the next prerequisite. Later phases may be inspected, but the primary
guided action always targets the earliest applicable unresolved decision.
Inapplicable decisions are omitted using the existing server-side
applicability rules; they are never treated as completed selections.

### 5.3 One decision at a time

Each guided decision contains, in this order:

- a short phase-specific instruction;
- the source sentence or bounded family/cohort description;
- a plain-language statement of what CEMM currently proposes;
- an explicit reviewer question;
- the exact evidence needed to answer it;
- neutral option cards with readable labels, definitions and consequences;
- **Skip for now**, which performs no mutation; and
- collapsed **Technical evidence** containing exact refs, geometry and hashes.

No option is checked by default. Options use the same visual weight and order
is deterministic. Reject/repair options may use danger styling only to
communicate their blocking consequence, not to discourage selection.

After the reviewer selects an option, **Review impact** opens a readable
preview. The confirmation must state what will be recorded, how many decisions
are affected, which dependent decisions will be cleared, and whether the
result blocks authoring. Exact refs remain expandable. **Confirm and continue**
performs the existing revision- and preview-hash-bound write, refreshes state,
and opens the next unresolved decision. **Go back** records nothing.

### 5.4 Uncertainty

**Skip for now** moves to another unresolved decision without changing working
state. When every remaining decision has been skipped in the current pass, the
UI explains that review cannot complete until one is resolved; it does not
loop silently or infer an answer.

Where an existing contract provides a reject/repair option, its explanation
must say that it records accountable rejection and blocks Task 10B until the
earliest owner is repaired and the draft is regenerated. The UI must not
invent a generic rejection value for rows whose ABI does not define one.

### 5.5 Bounded cohorts

Routine cases may be reviewed through an existing or newly exposed bounded UI
cohort action only when the underlying action already applies one exact allowed
decision to an explicit target-ref set.

For a cohort, the guided screen shows:

- the cohort definition and member count;
- why its members are eligible to be reviewed together;
- deterministic representative examples;
- exceptions excluded from the cohort;
- the complete member-ref list under Technical evidence; and
- an explicit acknowledgement that the decision applies to all members.

Purpose cohorts must preserve duplicate-group, holdout, denominator and
purpose-local isolation constraints. Designation cohorts must exclude empty,
overlapping, multi-unit, polysemous and otherwise exceptional cases exactly as
the current reviewer indexes require. Exceptional designation cases remain
individual.

Cohorts reduce interaction count, not evidence requirements or semantic
accountability. They do not create a new final semantic identity.

### 5.6 Completion states

The final screen distinguishes three states without ambiguity:

- **Review incomplete:** applicable decisions remain unresolved.
- **Review recorded but authoring blocked:** review is complete and exportable,
  but one or more accountable rejection decisions require repair.
- **Review complete and authoring ready:** exact export validation passes and no
  blocking rejection remains.

The export action remains disabled until the existing completeness validator
permits it. Export still reauthenticates the source/template and reconstructs
canonical selection bytes in Python.

## 6. Presentation contract

The browser remains a thin presentation client. It may own navigation state,
the current skipped-ref set and disclosure state for the lifetime of the page.
It must not persist semantic decisions, duplicate selection validation, build
action target sets from untrusted DOM text or decide applicability.

Python projects a bounded `GuidedReviewItem` from the already authenticated
session indexes. The projection contains only presentation data derived from
the exact review row and reviewed UI policy:

```text
phase
progress
item_ref
source_summary
proposal_summary
reviewer_question
evidence_blocks
neutral option explanations
cohort summary and exact target refs, when applicable
current decision
blocking consequence
technical evidence
```

The projection does not contain a recommended option. An option explanation
describes the existing allowed value and consequence; it cannot introduce a
new value or broaden the action.

The guided endpoint accepts bounded navigation inputs such as an exact skipped
ref set and returns the earliest applicable unresolved item in deterministic
phase/ref order. The server constructs every `ReviewAction`; JavaScript sends
only the returned opaque option/action identifier plus the current revision.
Preview, apply and export continue to use the existing session methods.

## 7. Component changes

### 7.1 Review-session projection

Add a pure guided projection over the existing `ReviewContext`, `ReviewIndexes`
and canonical working state. It must reuse the one authenticated session cache,
perform indexed lookups only, enforce response/item/target byte and count
bounds, and remain import-inaccessible from runtime packages.

### 7.2 Loopback API

Add narrowly scoped endpoints for guided bootstrap/next-item retrieval if the
existing bootstrap and items routes cannot express the projection safely.
Reuse the current token, origin, revision, strict-JSON, body-size, method,
static-allowlist and connection-close protections. Do not add a server process,
validation tier or background worker.

### 7.3 HTML/JavaScript interface

Make Guided Review the default route and retain Advanced Explorer as a
secondary view. Use semantic HTML, system fonts, 44-pixel controls, visible
focus, reduced-motion support, responsive single-column behavior and no unsafe
DOM insertion. Raw JSON appears only in collapsed Technical evidence.

### 7.4 Documentation

Update the reviewer handoff so its first instruction is to press Start/Resume,
not to interpret all five ABIs. Keep the exact independent export-validation
command and the warning that a valid rejected export does not unblock Task 10B.

## 8. Error and recovery behavior

- Missing or invalid launch token: explain how to restart and use the full URL.
- Invalid reviewer ref: keep the entered value, identify the required syntax,
  and record nothing.
- Stale revision: refresh and reopen the same guided item if still applicable;
  otherwise advance and explain why the item changed.
- Invalid or stale preview: discard it and require a new impact review.
- Source/template drift: stop the session with the existing authentication
  error; never continue with cached or partial data.
- Journal failure: show the existing advisory warning while preserving the
  canonical working-state result.
- No unskipped item remains: explain that skipped decisions remain unresolved
  and offer to revisit them.
- Export with blocking rejections: allow the existing exact export while
  clearly retaining **authoring blocked** status.

Errors must not expose stack traces, local paths, session tokens or source
contents beyond the authenticated bounded projection.

## 9. Performance and anti-bloat requirements

- Authenticate draft/template and build indexes once at session startup.
- Guided next-item retrieval uses phase/ref indexes; it must not scan authority,
  rebuild grounding, regenerate worksheets or reread source files per action.
- Bound skipped refs, evidence blocks, cohort members, representative examples,
  response bytes and pagination.
- Do not add a runtime import, activation check, normal-cycle operation,
  release gate, pytest process, UI framework, package dependency or generated
  language artifact.
- Preserve the current advanced static assets and extend them rather than
  adding a parallel application.

## 10. Verification

Implementation acceptance requires executable tests proving:

1. The default screen exposes one Start/Resume action and explains reviewer
   responsibility without raw-ref-first presentation.
2. Every guided item maps to one existing applicable row or exact bounded
   cohort and exposes all and only allowed choices.
3. No projection contains a recommendation, preselection or synthesized
   semantic option.
4. Skip mutates nothing and bounded skip traversal terminates.
5. Confirm uses preview hash plus state revision and auto-advances only after a
   successful write.
6. Cohort target refs are independently reconstructed and exceptional cases
   cannot enter routine cohorts.
7. Technical evidence preserves exact source geometry and refs while the
   primary view remains plain-language.
8. All three completion states are rendered from server-owned counts and
   blocking refs.
9. Startup authenticates and indexes once; at least 512 guided reads/actions do
   not rescan source files.
10. Token, origin, request-bound, static-path, CSP and runtime-import isolation
    tests remain green.
11. A complete guided HTTP replay exports bytes identical to the existing
    advanced/API replay and passes independent selection validation.
12. Keyboard, narrow viewport, focus visibility, reduced motion, dark mode and
    no-unsafe-DOM static contracts remain green, followed by a manual real
    browser smoke check.

The existing full reviewer/authoring suites must pass twice, followed by SR5,
lint, compile, JavaScript syntax and diff-integrity checks.

## 11. Completion criterion

This repair is complete when a reviewer can launch the offline tool, understand
their responsibility, traverse the entire review through the guided path,
inspect exact evidence when needed, resume after restart, and produce the same
canonical validated `SELECTION.json` as the exact API path—without the system
choosing meaning for them or adding any runtime/release burden.
