# R4.1 Accountable Review UI Design

**Status:** approved design; implementation not started
**Date:** 2026-08-30
**Scope:** Task 10B reviewer-selection handoff only

## 1. Purpose

The current R4.1 handoff is one canonical 432,500-byte JSON template containing
1,056 explicit review targets. It is exact and machine-verifiable, but it is not
a practical human review surface.

Provide a local HTML/JavaScript interface that lets an accountable reviewer
inspect evidence, make explicit individual or bounded cohort decisions, resume
work, and export the existing canonical `SELECTION.json` input. The interface
must make review easier without becoming semantic authority, inventing gold,
or adding a runtime, activation, or release gate.

## 2. Governing invariants

The UI and its server obey the active CEMM contracts:

- `SemanticSwitchProgram` is procedure, not canonical meaning.
- The five-operator kernel is unchanged.
- The UI never infers semantic identity, operator, role, purpose, recipe, or
  designation approval.
- No option is preselected or silently accepted.
- A cohort action is one explicit reviewer decision over an exact displayed
  member set, not an automatic default.
- Browser state is never authority. Python reconstructs and validates every
  accepted action against the authenticated draft and exact selection
  template.
- The exported selection remains non-authoritative until it becomes an
  authenticated input to the later final R4.1 draft.
- The existing `validate_reviewed_selection_bytes` function remains the final
  selection validator. The UI does not define a parallel contract.
- Rejected semantic material is reported as a blocker requiring earliest-owner
  repair; it is never hidden with a fallback.

## 3. Chosen architecture

Use a dependency-free local single-page application backed by a Python
loopback server.

```text
authenticated worksheet draft + exact selection template
                         |
                         v
             Python review-session server
             - reconstructs exact joins
             - owns mutable working state
             - validates every action
             - builds bounded indexes once
                         |
               loopback JSON projections
                         |
                         v
             static HTML/CSS/JavaScript UI
             - displays evidence
             - filters and navigates
             - submits explicit actions
                         |
                         v
             canonical SELECTION.json export
                         |
                         v
        existing strict selection-byte validator
```

The implementation uses Python's standard-library HTTP server and static
browser assets. It adds no React/Vue framework, Node build chain, CDN, package,
database, browser extension, or production dependency.

### 3.1 Planned files

- `scripts/serve_r4_1_review.py` — CLI, loopback server, session lifecycle and
  browser launch.
- `scripts/r4_1_review_session.py` — exact state transitions, cohort indexes,
  impact previews, persistence and export.
- `scripts/r4_1_review_ui/index.html` — accessible single-page shell.
- `scripts/r4_1_review_ui/styles.css` — local presentation only.
- `scripts/r4_1_review_ui/app.js` — navigation, rendering and API calls only.
- `tests/test_r4_review_session.py` — state, cohort, dependency and export tests.
- `tests/test_r4_review_server.py` — loopback API and security tests.

Splitting session logic from HTTP transport keeps all consequential behavior
testable without a browser. JavaScript contains no independent semantic or
validation rules.

## 4. Trust and security boundary

The server:

- binds only to `127.0.0.1` on an operating-system-selected port;
- generates one cryptographically random session token;
- places the token in the browser URL fragment so it is not sent in the HTTP
  request line, then requires it in a request header for every API call;
- checks the exact loopback `Origin` for state-changing requests;
- serves a restrictive Content Security Policy and no external assets;
- exposes no arbitrary filesystem path, shell, upload, proxy, or fetch API;
- reads only the configured exact draft, template and working-state paths;
- bounds request bodies, field counts, string lengths, action counts and
  response projections;
- rejects links, reparse points, unexpected file identities, stale hashes and
  noncanonical final exports using the repository's existing safe-I/O helpers;
  and
- terminates without exporting if the template, worksheet refs, or authenticated
  input set changes during the session.

The UI is a convenience client. A crafted browser request cannot select an
unknown option, cross a row boundary, alter immutable material, approve an
inapplicable row, or bypass final validation.

## 5. Session and persistence model

The launch command is:

```powershell
python scripts/serve_r4_1_review.py
```

Optional CLI arguments may override the draft, template, working-state and
export paths, but defaults remain within `artifacts/review_inputs/r4_1`.

At startup, Python authenticates the exact worksheet draft once, reconstructs
the selection template, compares it with the checked-in template, and builds
bounded immutable indexes. Normal interactions do not rescan authority files
or rebuild the worksheet closure.

Working state uses the same selection shape with `selection_state` still
`unresolved`. It is saved after every accepted action with a same-directory
temporary file, flush, fsync and atomic replace. A non-authoritative append-only
action journal records:

- template ref and SHA-256;
- monotonically increasing action sequence;
- reviewer ref;
- action kind;
- exact affected row, family or case refs;
- before and after value hashes; and
- session-local timestamp for human audit only.

The journal is not an identity input and cannot authorize export. Resume is
allowed only when the working state binds the current template ref, template
hash, worksheet refs and draft input-set ref. Stale state fails closed and is
left intact for comparison; there is no automatic migration.

## 6. User interface

The page has five ordered work areas and one persistent status header.

### 6.1 Status header and dashboard

Display reviewer identity, exact template identity, draft input-set identity,
completed/applicable/unresolved counts, blocking rejections, validation errors
and the last successful save. Counts are computed by Python and returned with a
state revision; JavaScript does not derive authoritative completion.

The dashboard offers search and filters for unresolved, rejected, exceptional,
and completed items. It never exposes an "approve all" action.

### 6.2 Structural review

Review all 12 structural decisions individually. Each card includes:

- decision kind and exact subject ref;
- human-readable scenario surfaces and composed-expression summary;
- mode, topology, applications, roots and expression links;
- legacy-conditional or generator-patch impact where applicable;
- exact available options and affected downstream counts; and
- a confirmation step showing the chosen option and impact hash.

The generator-patch choice must match the legacy-conditional branch. Changing
a structural decision first produces an impact preview. If downstream choices
become inapplicable, the reviewer must explicitly confirm clearing the exact
listed decisions. The server performs the clear atomically with the structural
change.

### 6.3 Purpose review

Review order is duplicate-risk groups, challenge holdouts, direct memberships,
then denominator sufficiency.

The UI groups related cases for inspection and shows purpose counts and
denominator coverage, but it does not recommend or preselect a purpose. A batch
action is available only for an exact cohort whose full member list, source
classification, branch applicability and resulting count changes are shown in
an impact preview. The reviewer explicitly confirms the displayed cohort and
purpose.

Membership assigned through an approved duplicate group remains visibly linked
to that group. The interface prevents direct and group ownership from being
presented as simultaneous choices. Holdout conflicts and denominator shortfalls
remain visible until repaired.

### 6.4 Proposal-recipe review

Display 56 normalized families grouped by target kind and then by the purposes
selected in the prior phase. Each family view shows:

- the immutable family definition;
- complete and active member counts;
- representative and expandable exact cases;
- purpose-local member partitions;
- reviewed parameter fields; and
- explicit `approve` or `reject` choices for each purpose-local partition.

The server expands an explicit family-purpose decision to the exact member refs
already owned by that purpose. It rejects cross-purpose membership, missing
members, duplicate ownership and more than four purpose recipes. It does not
copy recipe ancestry across purposes.

### 6.5 Designation review

Routine candidate sets may be displayed in cohorts derived from identical
human-readable evidence signatures. Cohort identity is local UI metadata and
never replaces exact case-local candidate-set and binding refs. Before a batch
approval, the reviewer can expand the complete case list and every exact span,
fact and target.

The following cases require individual review and cannot use a routine cohort
approval:

- intersecting-span cases;
- undirected overlap pairs;
- multi-unit spans;
- polysemous candidate sets;
- all exact-empty sets; and
- any case affected by a structural rejection or designation correction.

`approve_candidate_bindings` always means the complete exact candidate list.
`approve_exact_empty` is available only when the independently reconstructed
candidate set is empty. `reject` approves no binding and marks the earliest
designation/geometry owner as requiring repair before Task 10B expansion.

### 6.6 Export

The export page distinguishes:

- review-complete: every applicable target has an explicit valid decision; and
- authoring-ready: review-complete with no rejection that requires source,
  recipe or designation repair.

This is UI status, not a new activation or release gate. A completed review may
be exported even when it records a rejection, but the UI clearly states that
Task 10B expansion remains blocked pending regeneration.

Export sets `selection_state` to `reviewed`, generates canonical JSON bytes,
runs `validate_reviewed_selection_bytes`, and writes `SELECTION.json` with an
exclusive or exact-identical policy. It refuses to overwrite different bytes.
The UI reports the final path, byte length, SHA-256 and validation result.

## 7. API and state transitions

The HTTP layer exposes only bounded operations:

- `GET /api/bootstrap` — immutable identities, counts, navigation and current
  state revision.
- `GET /api/items` — one bounded filtered page of server-created display
  projections.
- `POST /api/preview` — validate an intended individual or cohort action and
  return its exact impact plus a short-lived impact hash.
- `POST /api/apply` — apply exactly the previewed action when the impact hash
  and state revision still match.
- `POST /api/reviewer` — set one or more canonical accountable reviewer refs.
- `POST /api/export` — perform final reconstruction, validation and safe write.
- `POST /api/shutdown` — stop the local server after token and origin checks.

Every state-changing response returns a new monotonic state revision. Stale
tabs receive a conflict response and must reload; last-write-wins behavior is
forbidden.

## 8. Error handling

Errors are typed as input, stale-state, applicability, dependency, validation,
persistence or internal errors. The API returns a safe message, affected refs
and unchanged state revision. It never returns stack traces or local file
contents to the browser.

A working-state action is all-or-nothing. Working-state persistence failure
leaves the prior working file and in-memory state active. The action journal is
non-authoritative and is appended only after a successful state write; journal
failure produces a visible audit warning without invalidating or rolling back
the exact working selection. Export failure leaves no partial final file. If an
output identity changes during a write, cleanup is refused and the server stops
the affected operation.

## 9. Performance and anti-bloat constraints

- This tool is offline and opt-in; runtime stages and activation are untouched.
- Authenticate and index the draft once per server process.
- Bound returned pages and use lazy detail expansion rather than rendering all
  1,056 targets and multi-megabyte evidence at once.
- Normal actions use indexed row/family/case joins and do not scan authority.
- Autosave serializes only the bounded working selection and journal entry.
- Final canonical reconstruction and validation run only on export or an
  explicit full-validation action.
- Browser assets remain small, framework-free and build-free.
- Reference-checkout targets are under five seconds for startup, under 150 ms
  for an indexed preview excluding disk flush, and under fifteen seconds for
  final export validation. These are development benchmarks, not new release
  gates.

## 10. Verification strategy

Tests must cover:

- exact startup binding and stale-template refusal;
- canonical reviewer refs;
- every structural option and branch/patch coherence;
- dependency-preview hashes and confirmed atomic clearing;
- purpose cohort membership, leakage prevention, holdouts and denominators;
- purpose-scoped recipe partitions and parameter bounds;
- routine designation cohorts and mandatory exception isolation;
- independently forged binding and candidate-set refs;
- resume, state-revision conflicts and interrupted persistence;
- request size, token, origin, method, route and path-traversal rejection;
- canonical export, exact-identical replay and different-output refusal;
- deterministic server projections and cohort indexes; and
- full 1,056-target synthetic review without semantic auto-selection.

Python unit and loopback HTTP tests are mandatory. JavaScript remains thin and
must pass syntax validation plus a real-browser smoke test during development.
No browser automation package becomes a runtime or release dependency.

## 11. Acceptance criteria

The design is implemented when:

1. `python scripts/serve_r4_1_review.py` opens a usable local page and can resume
   an exact current-template session.
2. The reviewer can complete all five phases without editing raw JSON.
3. Every decision results from an explicit individual or exact previewed cohort
   confirmation.
4. High-risk designation cases and all structural decisions are individually
   reviewed.
5. A structural change cannot leave stale dependent selections active.
6. Exported bytes pass the existing strict validator and are deterministic for
   the same final state.
7. The tool adds no semantic authority, runtime path, network dependency,
   activation gate or release gate.
8. Focused tests, static checks, security tests and real-browser smoke checks
   pass without weakening existing R4 gates.
