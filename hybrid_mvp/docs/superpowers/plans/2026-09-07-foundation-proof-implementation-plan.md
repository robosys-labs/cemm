# Foundation Proof Implementation Plan

> **For agentic workers:** Use the executing-plans or subagent-driven-development
> skill. Keep this single checklist current; do not create a competing master.

**Goal:** Correct the interpretation-to-answer foundation and prove a useful
bounded conversation before bulk corpus expansion or learned activation.

**Architecture:** Retain the five-operator exact core, canonical expressions,
authority, provenance and effect ownership. Specify semantic expectations
independently, test reviewed expressions through existing owners, then test the
surface path. A development-only response reference is distinct from R5 output.

**Tech stack:** Python, pytest, SQLite, existing canonical codecs, inventory and
validation runner. Worktree: `C:\dev\cemm\.worktrees\unresolved-designation-r4`.
All paths below are relative to its `hybrid_mvp/` subtree.

## Authority and initial evidence

The [foundation amendment](../specs/2026-09-07-foundation-proof-corrective-amendment.md)
governs. The [audit](../progress/2026-09-07-cemm-goal-and-foundation-audit.md)
records pre-change observations at `228222d`, not current admission status.
Root adoption, R4/R5 admission, corpus publication and network research remain
outside this implementation increment.

Baseline: known-definition traversal is green despite an incorrect atom-kind
answer; unknown designation has four recorded representation-path REDs; R3/R4
configured selectors disagree with authenticated source inventory. These are
known repair targets, not permission to weaken exact safety checks.

## Task 1 — Migrate stale authority and execution routing before code

Files: `AGENTS.md`, `README.md`, `INTEGRATION.md`, `docs/ARCHITECTURE.md`,
`docs/IMPLEMENTATION_PLAN.md`, `docs/REPLAY_GOVERNANCE.md`,
`docs/DOCUMENT_AUTHORITY.json`, `docs/ABI_REGISTRY.md`, affected older specs/plans,
and explicit routing-test successors in `tests/test_foundation_governance.py`.

- [x] Classify the September 3 closure and unresolved design/plan as historical;
  preserve completed work and exact stop records, add a supersession banner.
- [x] Put the foundation amendment/plan immediately after AGENTS in the ordered
  authority map; preserve the August 29 data boundary underneath.
- [x] Replace every active narrow-Task-4 route and inherited neural/runtime
  completion claim; remove the obsolete numbered production outline from the
  current router while retaining its history in git.
- [x] Mark R4 bulk workflows and R5 release activation frozen, while clearly
  allowing the development semantic/response reference. Update conditional older
  documents so they cannot override that distinction.
- [x] Replace stale routing-test obligations through explicit successors;
  preserve immutable inventory/ledger anchors and refresh later AST metadata.
- [x] Run the authenticated active union for `test_replay_governance.py`,
  `test_foundation_governance.py` and `test_test_inventory.py`. Record failures
  by owner, never rewrite expected hashes to conceal a changed frozen assertion.

Evidence: all 107 active cases passed on clean commit `372aaa9`; the two new
routing assertions were observed RED before migration. Independent spec/quality
reviews passed. G0–R5 configured selectors match the authenticated inventory.
The clean status CLI verifies the historical chain: G0–R3 green, R4–R8 red;
this is not fresh admission of changed semantic owners. Commit `315202c` records
the migration; `372aaa9` restores the living receipt's canonical no-newline bytes.

## Task 2 — Remove false definition answers with independent regressions

This is the amendment's bounded containment exception, based on the audit's
reproduced false answer. It precedes full-matrix capability repair selection;
its completion must not be used as evidence that a definition can be answered.

Files: `data/languages/en/forms.json`, `src/cemm_authoritative_hybrid/proposal_context.py`,
`src/cemm_authoritative_hybrid/r3_cognition.py`, `r4_contracts.py`, dependent exact reconstruction
owners, `tests/test_foundation_semantics.py`, explicit successors of misleading
definition tests, and affected test metadata.

- [x] Write and run RED public-runtime contrasts for `What is CEMM?`, `Who is
  CEMM?`, `Where is CEMM?`, `Define mother.` and `What is a mother?`. Assert that
  no selected expression substitutes an internal atom-kind statement for the
  requested content. Assert no world mutation. Do not assert that abstention
  means the definition capability is complete.

```python
assert not any(
    binding.role_ref == "role:type"
    and isinstance(binding.filler, LiteralValue)
    and binding.filler.value == "concept"
    for app in selected_expression.applications
    for binding in app.roles
)  # when there is a selected expression
```

- [x] Add an independent cognition test: an atom-kind-shaped pattern receives
  no automatic support from the atom registry. Add positive controls showing
  explicit ordinary world type facts still supply the proper binding/proof.
- [x] Delete nominal-definition-to-kind synthesis and its special validation
  allowances, then remove automatic registry-kind support from the query owner.
  Keep valid designation, state and normal nominal-predicate affordances.
- [x] Reject the R4 compiler's metadata-only `defines(target, semantic_kind)`
  assertion with an exact typed error. It currently reconstructs the same false
  definition gold; missing semantic content must not be invented or silently
  filtered out of frozen corpus obligations. Preserve explicit ordinary facts.
- [x] Run the new tests GREEN and the existing relevant R2/R3/R4 owner suites.
  Give obsolete definition-gold/traversal tests explicit honest successors,
  preserving their historical bodies and independent safety assertions.
- [x] Record the remaining open-definition/description capability as incomplete.
- [x] Retire the erroneous `define` interrogative cue at the input-pack source
  owner. Independently require genuine open-variable evidence for query slots,
  preserving role-specific binder evidence in designation/name questions. No
  runtime surface branch, new copula parser, raw orthography channel or ABI bump.
  Preserve ordinary questions, nominal affordances and multiword designations;
  record the pack diff/hash and unchanged authorized realization behavior.

Containment evidence (uncommitted implementation under independent review):
28 foundation cases pass after observed REDs; a 39-case focused run also passes
verifier reconstruction, recursive-query, learning-transaction and real-index
multiword-designation controls. A discarded copula/orthography experiment was
found to constrain unrelated questions. The final implementation instead removes
the erroneous source-pack cue and checks exact query-variable source ownership.
`Define mother.` remains typed unresolved; genuine nominal questions, including
multiword `job role`, retain their existing variables. The narrower correction
does not establish punctuation, clause-locality or zero-copula competence, and
must not be described as useful definition support.

Pack preservation: `data/languages/en/forms.json` is directly reviewed input,
not generator output; no current writer was found. The diff removes only the
`define` query cue, preserving all other fields and Form ABI 7. The regression
restores that one entry in memory and independently requires the predecessor
canonical hash `32f5133c901afc05cc5345bc5766d00c97518b54025cad4ca0fb3707ad40b5ad`.
The pack contains no response grammar or realization records. Frozen input/corpus
witnesses are retained, not regenerated; unavailable R5 realization is not
claimed as tested. Actual public and post-VERIFY controls are reported separately.
Independent spec and quality reviews passed for this containment checkpoint.
The final bounded
authenticated owner run has 248 passes and 13 failures across 261 nodes, with
the same source-data failures and three unresolved-designation predecessor
failures described below. All four post-VERIFY R3 canaries pass: OBSERVE is
contested, QUERY/REQUEST are unknown, SIMULATE is simulation; all four return
NoEffectReceipt with zero world delta. They do not prove successful operations
or answered questions. The 111-case
active governance run has 110 passes and the expected dirty-input CLI failure;
the clean-checkpoint run remains required, without weakening that check.

The initial 243-node authenticated owner diagnostic had 229 passes and 14 failures:

- Ten expose invalid historical `defines` gold. They are the assertion compiler's
  `test_core_reviewed_assertion_families_compile_without_propose` and these
  closeout tests: `test_every_reviewed_scenario_matches_authentic_cycles`,
  `test_every_reviewed_surface_compiles_and_round_trips_canonically`,
  `test_external_sensor_provenance_is_not_mistaken_for_active_adapter_authority`,
  the `adversarial`/`gaps`/`restart` cases of
  `test_fail_closed_boundary_families_match_authentic_cycles`,
  `test_learning_reported_speech_and_effect_contracts_have_connected_compatible_topology`,
  and both `test_singleton_polysemy_*` tests. Their source is retained and failures
  remain visible; no aggregate was silently filtered or superseded.
- Four also fail when the relevant owner modules are loaded read-only from
  baseline `372aaa9`: the unknown designation frame-builder test, unresolved
  derivation canary, closure unknown-designation test, and the multi-unit
  designation fixture lacking `facts_for_surface`. The latter now has a real-
  `DesignationIndex` successor retaining the same assertion and adding exact
  fact/span provenance checks; it passes. The other three remain repair items.

Source inventory authenticates R2/R3/R4; immutable inventory and frozen test
bodies/metadata are unchanged. These results do not establish phase admission,
useful definitions, complete unknown handling, or a passing full regression.

## Task 3 — Establish the independent foundation semantic contract

- [ ] Add parameterized cases to the same foundation test module for ordinary
  type membership, ordered relation roles, polarity and scoped/attributed facts.
  Expected expressions are independently written; never snapshot current output
  as gold. Confirm roles, binders, scope and requested projection, not operator
  sets or program hashes alone.
- [ ] Add real initial-context setup for speech history and fragments. Separate
  fresh-context clarification from successful context-bound interpretation.
- [ ] Add an explicit operation target/value and remove its permission in the
  denial case. Check mutation receipts and store revisions.
- [ ] Run the whole diagnostic matrix and record all missing owners together.
  Do not stop discovery at the first failing surface and regenerate bulk gold.

### Matrix preparation findings (September 7, not completion evidence)

Independent review identified the following owners to exercise together. These
are not additional release gates. Existing canonical types/owner APIs supply the
test inputs; parser output must not supply the expectations.

| Boundary | Independent expectation | Evidence so far |
|---|---|---|
| Ordinary facts | Explicit membership/ordered relation evidence supports only the specified proposition and proof. | Canonical application, binder and query APIs exist; Task 2 contains registry-kind substitution. |
| Type-role alignment | The surface path, independent compiler and query owner agree on the same membership roles; a metadata classification is not substituted. | Static inspection: nominal affordances use `role:instance`/`role:class`; an explicit compiler application permits `role:subject`/`role:type`, while its composed-type validator still requires a registry-kind literal. Direct-query positives do not prove cross-path equivalence. |
| Polarity/admission | A negative state is not admitted as positive; a conditional does not admit either operand unconditionally. | Direct `ObserveDecisionOwner` probes reproduce both wrong delta outputs. No gateway was invoked; public reachability is not yet established. |
| Scoped requests | A nested, negated or conditional event is not an unconditional executable request. | Static inspection: request owner selects the first event anywhere in the expression. Requires executable contrast, not an exploit claim. |
| Partial meaning | Unresolved role constraints survive; known facts cannot satisfy a pattern made broader by dropping that role. | Static inspection: query pattern drops `UnresolvedValue`; VERIFY currently blocks critical residuals before compilation. |
| Speech/fragments | Context retrieval preserves speaker, session, prior expression and exact outstanding content slot. | Low-level resolver tests exist, but active snapshots return refs without the complete semantic focus; public continuation is not demonstrated. |
| Operations | A predeclared system/lamp/power/on request produces an independently specified observed delta only with permission; replay commits once. | Existing adapter echo of expected deltas is not an independent correctness oracle. |
| Learning/reuse | Actual unknown QueryResult → authorized existing-target alias → one commit → restart → unseen composition. | Current R3 path materializes a known-target obligation, can synthesize a query ref, and does not complete a durable alias commit/reuse loop. |

After the full matrix runs, repair admission/scope safety before expanding
question or learning capabilities. Preserve the positive simple-state and denied-
effect controls. Retained predecessor `query.py`/`learning.py` docstrings now
identify their historical status and whole-store retrieval limitation; they must
not be reconnected to bypass these missing active owners.

## Task 4 — Complete open queries and scoped uncertainty through existing owners

- [ ] Specify query answer projection explicitly: designation target, type
  membership, description/identification or location; bare `What is X?` retains
  contextual alternatives. Use the existing binders/roles when expressive; an
  ABI extension must carry exact owner/codec/compiler/verifier tests and be
  recorded in ABI_REGISTRY before activation.
- [ ] Preserve interrogative distinctions in reversible form evidence from its
  identified generator/source; do not inspect raw words to choose runtime meaning.
- [ ] Reuse acyclic unresolved frames for explicit lexical lookup, not every
  unknown nominal question. Query admitted designation indexes without creating
  a target. Preserve critical unknowns in other roles and scopes.
- [ ] Make unknown answers yield a typed response about missing knowledge;
  unresolved interpretation yields targeted clarification. Neither authorizes
  embedded effects or unconditional admission of scoped content.
- [ ] Verify known definitions use actual reviewed descriptive content. Missing
  definitions remain missing even when the target identity is recognized.

## Task 5 — Prove a complete reference conversation

- [ ] Run independently specified expressions through existing cognition,
  learning/effect and response owners to isolate semantic behavior from parsing.
- [ ] Provide a compositional diagnostic renderer for those typed responses,
  preserving designations, literals, perspective, roles and epistemic qualifiers.
  No input-phrase dispatch, ref-name lexicalization, canned answer catalogue or
  release fallback is allowed. Keep learned/release profiles fail-closed.
- [ ] Demonstrate unknown-expression lookup, clarification, an explicit alias
  explanation for an existing reviewed identity, learning authorization, one
  transactional commit, restart and reuse in an unseen composition.
- [ ] Demonstrate that a proposed new identity remains subject to acquisition
  policy; no default-to-concept or research-result auto-admission.

## Task 6 — Repair measured search/retrieval bounds and confirm preservation

- [ ] Reproduce program/meaning duplication with the audit's multi-root and
  conditional examples; canonicalize equivalent search states only when future
  legal continuations, scope and evidence ownership are preserved.
- [ ] Replace relevant whole-store query reads with indexed predicates/arguments
  and revision-pinned retrieval. Test behavior with increasing irrelevant facts.
- [ ] Keep configured caps and truncation honesty; measure real work, preserve
  denied-effect and authority boundaries, run multilingual/unseen-synonym tests.
- [ ] Regenerate changed deterministic artifacts twice; require byte identity
  and preservation of every previously authorized realization contract.

## Task 7 — Handoff to R4/R5 only on evidence

- [ ] Complete spec and quality review of code, active docs, data and tests.
- [ ] Run existing authority, ABI, anti-bloat, semantic-operational, web and
  relevant regression checks; reconcile selector/inventory disagreement through
  existing selector generation, never bypass it.
- [ ] Record reference capability, remaining gaps and actual resource measures
  separately from learned-model results and replay admission.
- [ ] Resume data work only after the foundation semantic/response loop passes;
  an isolated learned pilot still needs explicit R4.1-compliant data authority.
  It must add measured generalization before the hybrid objective is complete.

## Progress and stop discipline

Update checkboxes only with observed evidence. Never label Task 2 containment as
Task 4/5 completion. Repair findings within this approved scope without another
routine approval loop. Escalate only for a material change of goal, irreversible
operation, new external authority, or a representation decision that cannot be
resolved within the approved semantic contract. Do not merge or push implicitly.
