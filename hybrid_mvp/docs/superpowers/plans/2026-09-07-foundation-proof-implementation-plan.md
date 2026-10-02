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

**Current execution pointer (October 1):** The uncommitted normalized-store and
read-only description-builder checkpoints below are implemented, not public
definition support. A fresh 103-case baseline passed the builder, Description
ABI, normalized-store and R5 stop-boundary modules. The bounded October 1
checkpoint under Task 7 owns the next work. Signed description proof linkage is
implemented and reviewed, as is the bounded subject-person membership repair.
The bounded relation-query role repair and its independent spec/quality reviews
are complete. The description posting-focus repair passes fresh integration,
independent spec review and code-quality review. Public description-request
projection's canonical substrate is now implemented and independently reviewed
under Semantic Expression ABI 3. Request-first Description/Proof Bundle ABI 2
lineage is implemented and independently reviewed; genuine QueryResult ABI 3
and evaluation linkage are implemented and independently reviewed. Signed
Response Meaning ABI 4 and its exact source/effect sinks are implemented and
independently reviewed. Task 7.2b candidate construction and exact derivation
have passed both independent reviews. Bare content questions retain equal
description/definition candidates without a settled meaning; this is not useful
definition support. Task 7.4's bounded development-presentation component has
passed both independent reviews and its isolated CLI demo runs. Task 7.4 remains
open: the direct mixed participant/entity role repair documented below has now
passed independent specification and quality reviews. Next are the existing
conversation matrix's input evidence, mixed scope/embedding, reciprocal response
selection and restart/continuation proof, not another substrate rewrite. The
bounded unary-capability and single-variable relation/type diagnostic wording
increment below has passed both independent reviews; it is not general query
or conversation completion. The twelve index-less fixture failures require
exact fixture migration.
Normal learned realization remains unavailable; R4/R5 remain unadmitted.

**Historical execution pointer (September 8):** `4c574be` completes the narrow
authenticated publication transaction, not the conversation or foundation.
`f50e60c` completes the bounded, proof-backed admitted-designation reader and its
scoped reviews/regression comparison. `5bbe7a4` integrates
grounding, designation composition and lexical query through that reader, with
signed-publication/restart and unseen-role-order proof. Its full regression has
no new failures after fixture migration. The current uncommitted naming-owner
increment fixes exact label/target ownership and repeated-occurrence accounting;
scoped spec, quality and integration reviews pass. The final authenticated R3
comparison adds 48 passes and retains exactly the baseline failure set.
Fragment handling, compositional responses and the
remaining Task 4/6 owners still need executable proof. Dated checkpoints below
retain their original observations; their old “pending” statements are not
instructions to repeat work completed by a later checkpoint.

The [September 8 individual failure audit](../progress/2026-09-08-individual-failure-audit.md)
records all 159 remaining wrapper cases (139 assertion identities), the fragment
and dirty-worktree failures, historical-body comparisons and fresh owner/public
probes. It is diagnostic evidence, not successor approval or a new execution
plan. In particular, query exhaustion, final budget status, reported-speech
ownership and missing response/focus continuity remain open; a smaller wrapper
failure count alone cannot establish their completion.

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

Containment evidence (commit `8288794`):
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
or answered questions. All 111 active governance cases pass on clean `8288794`,
and the status CLI verifies the historical chain with R4–R8 still red. The
earlier dirty-input failure was resolved by the reviewed local checkpoint,
not by weakening validation. No commit has been pushed or adopted at root.

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

- [x] Add parameterized cases to the same foundation test module for ordinary
  type membership, ordered relation roles, polarity and scoped/attributed facts.
  Expected expressions are independently written; never snapshot current output
  as gold. Confirm roles, binders, scope and requested projection, not operator
  sets or program hashes alone.
- [x] Add real initial-context setup for speech history and fresh fragments.
  Separate persisted speech retrieval from successful context-bound fragment
  interpretation; the latter lacks an active content-slot obligation contract.
- [x] Add an explicit operation target/value and remove its permission in the
  denial case. Check mutation receipts and store revisions.
- [x] Run the whole diagnostic matrix and record all missing owners together.
  Do not stop discovery at the first failing surface and regenerate bulk gold.

### Executed pre-safety diagnostic matrix (`7e298b7`, September 7)

At the reviewed test checkpoint, the 25 added cases produce 10 passes and 15 failures; with the 28 containment
cases, the independently repeated module result is 38 passes and 15 failures.
Expected graphs and observed device deltas are independently specified, not
copied from parser output or requested effects. Direct post-VERIFY owner cases
do not establish public parser/verifier reachability. These are existing-owner
diagnostics, not additional release gates or R4 admission evidence.
The authenticated bounded owner union is 258 passes and 28 failures across 286
nodes: these 15 new diagnostics plus the 13 retained Task 2 failures. No earlier
passing assertion was changed to manufacture this result. Independent matrix
spec and quality reviews passed. Selectors and the canonical living inventory
receipt have been regenerated from the authenticated source metadata.

| Boundary | Independent expectation | Pre-safety evidence at `7e298b7` |
|---|---|---|
| Ordinary facts | Ordered relation evidence supports only the specified proposition and proof. | Forward, reversed and negative controls pass; conflict drops the opposing proof and fails the decisive-status constructor. |
| Type-role alignment | Compiler and public surface produce one independently specified membership graph. | Explicit instance/class compilation agrees; public `Alice is a mother.` returns no complete candidate (3 states, not truncated). Static composed-type validation still imposes a registry-kind literal. |
| Polarity/admission | Negative states are denied, conditions are not unconditional facts, opposing roots remain conflicting. | Negative scope is lost; a conditional attempts to encode a relation as StateDelta; opposing roots produce two positive deltas. Positive state and reported/speech non-admission controls pass. |
| Scoped requests | A negated, reported or conditional event is not an unconditional executable request. | All three produce effect intents at the post-VERIFY seam. Tests stop before executing those intents. OBSERVE and capability QUERY do not execute. |
| Partial meaning | Unknown role constraints survive alongside known roots. | Both unknown-object cases falsely return supported after dropping the object. Public VERIFY's critical-residual boundary remains distinct. |
| Speech/fragments | Retrieval preserves speaker, session, recency and an exact outstanding content slot. | In-memory speech focus passes; persisted focus is not rehydrated. Fresh fragment has no clarification evaluation (5 states, not truncated). Context-bound completion lacks a content-slot obligation representation. |
| Operations | Explicit lamp-on intent has independent observed evidence, permission and commit-once receipt. | Permitted first execution commits the exact delta once; terminal replay fails strict decoding of frozen receipt mappings. Permission denial passes. |
| Learning/reuse | Actual unknown QueryResult → authorized alias → one commit → restart → unseen composition. | Draft loses the actual query ref; no active authorized alias commit exists. A separately reviewed seeded alias survives storage but is absent from the reopened runtime's designation frames. Neither fixture claims completed acquisition. |

Representation/authority boundaries identified together, not hidden by green
containment tests:

- `data/authority/contracts/designation_learning.json` is a predecessor ABI 1
  file, absent from the active manifest's three owners. Active ABI 2 drafts and
  obligation materialization do not link it. Defaults use `cap:learn` and
  `permission:learn_designation`, while linked authority supplies `cap:learn_alias`
  and `permission:write_alias`. The test supplies the linked refs but proves only
  query/obligation continuity, not authorization. Contract identifiers need not
  be atoms; the missing piece is an active reviewed contract and commit owner.
- Generic dialogue obligations do not carry the enclosing expression and exact
  outstanding content slot needed to complete a prior fragment. A speech-focus
  ref alone is not that obligation or proof of contextual understanding.
- Flat persisted fact arguments and query string coercion cannot distinguish
  typed literals, semantic references and embedded propositions. Additional
  direct probes reproduce literal/reference collisions and candidate-local
  application-ID matching. A safe unsupported result is possible now; complete
  typed matching needs a reviewed representation/migration, not ref-name
  inference or a permissive compatibility fallback.
- Placement-sensitive retrieval and rule closure need coordinated review:
  filtering derived results alone can launder an attributed premise. Cause,
  purpose and sequence must not gain full relationship-proof claims from their
  current conjunction-like evaluation.

Next-owner tracing, without source edits or capability claims:

- Ordinary membership already has the right concept frame and explicit entity
  designation. `_compatible_reference_roles` intersects with generic reference
  ports that omit `role:instance`. A read-only in-memory probe admitting that
  port advances search from 3 to 4 states and binds Alice correctly, but still
  leaves the copula/determiner source units unconsumed. Repair reference-kind
  compatibility and generic predication source ownership together; raising the
  beam cannot create the absent legal transition.
- `bootstrap.py` gives Grounder an index provider returning only immutable
  `authority.designations`, ignoring persisted aliases. A correct replacement
  must preserve admitted designation evidence and generation/revision pinning,
  not index every teaching claim or reconnect the predecessor learning runtime.
- `FocusStore(stores)` initializes an empty in-memory list; its recent-entry
  reads never reload persisted focus. The separate R3 snapshot returns refs,
  not canonical focus records, and memory/SQLite ordering differs. Use bounded,
  session-scoped authenticated retrieval with consistent recency, preserving
  realization-backed focus provenance; do not claim fragment completion from
  rehydrating a ref alone.

After the full matrix runs, repair admission/scope safety before expanding
question or learning capabilities. Preserve the positive simple-state and denied-
effect controls. Retained predecessor `query.py`/`learning.py` docstrings now
identify their historical status and whole-store retrieval limitation; they must
not be reconnected to bypass these missing active owners.

## Task 4 — Complete open queries and scoped uncertainty through existing owners

- [x] First repair bounded safety owners exposed by the matrix: preserve signed
  admission and reject unsupported enclosing scopes; select only an eligible
  requested root before both learning and operation paths; retain unresolved or
  proposition-valued query constraints as typed blockers; preserve both sides
  of conflict proof; thaw stored terminal receipts at the strict decode boundary.
  Keep simple positive/denied controls and exact provenance. Do not distribute
  compound negation, invent a conditional planner, change authority defaults,
  widen caps, or add a parallel validator/query engine in this increment.
- [x] Repair ordinary membership roles, local predication/source ownership and
  early legal-choice propagation without losing valid alternative meanings.
- [x] Restore stale codec/coverage fixtures and explicitly preserve their
  original safety assertions before the next capability increment.
- [x] Restore indexed, bounded, authenticated focus reads across restart in the
  existing persistence/dialogue owners; preserve current window-overflow honesty
  and distinguish this repair from public speech/content integration.
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

Bounded safety implementation evidence (independent spec and quality passed):
the ten initial safety failures now pass, as do 38 additional signed/context,
unsupported-root, query-constraint and receipt-retry controls. The independently
run foundation module gives 86 passes and five remaining capability failures.
Those five are ordinary membership, persisted speech focus, fresh-fragment
clarification, alias/query continuity and persisted alias reuse; none has been
skipped or reclassified as success. The four post-VERIFY R3 canaries still pass
with zero world delta and the same status/action classes as the prior checkpoint.
The independently authenticated 324-node owner run gives 306 passes and 18
failures: those five capability gaps plus the 13 retained predecessor/source-data
failures. Existing R1/R2/R3 structural scans and authority linking pass; fresh
SQLite activation, reopen and integrity also pass as diagnostics, not admission.
The static inventory rejected implicit parameter IDs in the new tests; these
were corrected to literal IDs without changing the 38 contrasts or old test
ASTs. R3/R4 source inventories now authenticate, and configured selectors and
the canonical living receipt are regenerated through the existing mechanism.
Repeated regeneration is byte-identical. All 38 added safety controls pass;
their read-only predecessor replay gave 32 failures and six preservation passes.

The repair uses existing cognition/effect owners and strict codecs; it introduces
no new gate, ABI, runtime service, authority defaults or larger search bounds.
Unsupported compound admission is retained as an exact attributed occurrence,
not flattened into world deltas. Query containment is not complete typed-fact or
multi-answer support. Scope-safe evaluator production is also not a claim that
EFFECT independently authenticates an arbitrarily reconstructed evaluation:
its existing source-application/root/capability binding needs a bounded owner
review before extending operation or learning authority. Preserve that distinct
follow-up rather than copying the full evaluator into another validator.
The pre-existing OBSERVE conflict branch also drops occurrence/admission payloads
while retaining occurrence proof refs; payload retention needs an explicit
provenance repair. This increment preserves unsupported non-conflicting
occurrences and query conflict proof, not that separate conflict-storage path.

At the safety checkpoint, the next dependencies were ordinary membership,
bounded authenticated restart retrieval, then query/content-slot/learning
alignment. Membership and restart are now repaired as recorded below. The
explicit lexical-target increment below is the current next work; the older
traces retain pre-repair evidence, not instructions to repeat completed work.
None of these checkpoints resumes bulk supervision, training or root adoption.

Ordinary membership repair scope: preserve the canonical `role:instance` /
`role:class` graph and derive reference compatibility from semantic kinds.
Copula and adjacent determiner evidence must have exact local source ownership,
independently checked by VERIFY. Existing context spans currently erase the
distinction between whitespace and punctuation. If needed, retain that distinction
as form-owned structural evidence in existing contribution constraints, without a
new ABI field, semantic target or port. It must not select meaning, alter query
variable creation, or make punctuation/clauses transparent to predication.
Whitespace remains noncritical evidence, accounted for exactly once. Test missing
or forged gap evidence, clause boundaries, scope, unseen reviewed synonyms and
non-English form-feature controls before claiming this owner repaired.

Restart retrieval also needs truthful reachability reporting: the direct
`ReferenceResolver`/`FocusStore` case exercises a dialogue owner directly. The
active runtime consumes the separate R3 focus snapshot; rehydrating the direct
owner alone does not prove a public speech-history query or content-slot fragment
completion. Preserve this distinction while aligning bounded persisted reads.
The pre-repair SQLite focus query's independent `EXPLAIN QUERY PLAN` reported
`SCAN focus` and a temporary sort. Its output limit does not bound rows visited.
The completed restart repair uses the existing persistence owner's session/recency
indexing, authenticates only retrieved records, and tests memory/SQLite ordering
and irrelevant-session growth. It adds no normal-cycle whole-store validation
pass and does not expose unverified focus as dialogue evidence.
The pre-repair canonical focus decoder also accepted `abi_version=True` and `1.0`
as ABI 1 in direct probes. The restart repair fixes that exact scalar check;
Python value equality is not canonical wire equality. Existing codec bounds
remain intact, with no parallel record validator.

A further direct-owner probe confirms that 17 canonical focus records in one
session make the active 16-alternative snapshot raise its existing bound error;
the snapshot currently emits focus-record identities, not their expression
content. No active normal focus writer was found. These are distinct unresolved
window/content-integration requirements, not a demonstrated 17-turn production
regression or permission to silently drop history. Indexed authenticated reads
and restart parity are now repaired, with overflow honesty preserved. A bounded
focus window and content projection with explicit coverage/frontier behavior
are still required before claiming a usable speech-history loop.

The pre-repair query dependency trace at `a97858d` distinguished representation
from reachability. `UnresolvedDesignationFrame` had an exact context codec, but
the builder did not construct it, recursive expansion reached frames only through
selected designations, and compiler/coverage/reconstruction consumers assumed a
grounded frame. An independently constructed unresolved frame therefore visited
one search state and emitted no program. The bounded lexical-target checkpoint
below repairs that exact union without inventing a designation or target. Generic
`What is X?` remains outside this license and retains contextual alternatives.

### Next bounded increment — explicit, language-unspecified lexical target lookup

Independent traces at `a97858d` identify three connected missing owners: the
frame union is not executable, query auxiliaries are projected as extra answer
variables, and a correct independent designation query cannot read the admitted
designation index. `What does mother mean?` creates two instance variables;
`What does zorbulate mean?` stops at a critical anchor. Neither failure is a
training or search-cap problem. The pack correctly marks `does` as an auxiliary,
but loses the distinctions among genuine interrogatives.

Complete this public development-runtime increment before broader definition,
inverse-surface or conversational learning work:

- [x] Preserve reviewed interrogative features in `data/languages/en/forms.json`
  and `forms.py`; an auxiliary supplies construction/binder evidence, not a new
  answer hole. License lexical lookup from exact local form features, never raw
  phrase dispatch. Generic nominal, person and location questions are not lookup
  fallbacks. Preserve existing query evidence and authorized realization fields.
- [x] In `proposal_context.py`, compose the exact literal plus its owned query
  binder into an acyclic `UnresolvedDesignationFrame`, for known and unknown
  spellings alike. The answer remains a variable across admitted semantic target
  kinds; recognizing the spelling must not pre-bind the requested answer.
- [x] Complete the existing frame union in recursive expansion/search, compiler,
  coverage and independent reconstruction. Structural instantiation consumes no
  literal source; the surface binding consumes that literal once; variable
  projection consumes only the interrogative and its own binder evidence.
  Preserve all other role, scope, reference and residual constraints.
- [x] Add an activation-built exact cross-language surface index in `authority.py`.
  `r3_cognition.py` must use original admitted designation facts and their
  generation/content provenance through the existing query/proof owners. Do not
  scan every world fact or language bucket for a pure lexical query. Exact means
  case-sensitive: Grounder's case-fold fallback is not proof about another literal.
- [x] Preserve typed target projection: a string starting with `?` is still a
  literal, not a binder. Distinct language/target alternatives yield honest
  PARTIAL/clarification with retained evidence, not the first substitution.
  Empty retrieval yields UNKNOWN (no admitted designation found), never a claim
  that the expression has no meaning. Neither result permits a world write.
- [x] Exercise independently authored graphs and the actual public path through
  VERIFY, QueryResult and ResponseMeaning: known/unknown, non-concept targets,
  multiword and exact-case literals, multilingual form-feature controls,
  competing languages/targets, irrelevant-index growth and overflow. Attack
  transferred binder/literal sources, extra clauses, scope, teaching and unknown
  event arguments. Explicit language restrictions must remain critical and must
  prevent acceptance of an easier unqualified lookup.
- [x] Review the source spec, then quality; preserve earlier test ASTs/metadata
  and immutable inventory. A changed pack needs an explicit preservation successor
  to historical whole-pack hash assertions, not a rewritten frozen assertion.
  Regenerate the existing selectors/receipt twice and run the authenticated owner
  union plus existing structural/authority/activation/governance checks.

The independently specified expression remains the three-role designation query:
`label:lexical`, exact string surface and bound target variable, under its binder.
No stated language means unspecified, never English or the interface language.
The single-answer result must not erase even same-target/different-language
alternatives. A response describes admitted evidence, not universal language truth.
The first public construction uses an unquoted, otherwise feature-free literal
span; quotation and lookup of closed-class forms need their own reversible form
evidence. Non-English synthetic feature transport is an anti-dispatch control,
not proof of natural Spanish or other-language grammar competence. Direct typed
query tests may exercise a wider exact-literal set than this first surface path.
This first increment changes no numeric ABI, qualifier grammar, kernel operator,
program action, gate, bound, learning authority or normal realization policy.

The durable next representation for an explicitly mentioned language is an
optional `role:language` string qualifier on lexical designation, retaining its
three primary roles. Situation language alone cannot preserve content identity.
That extension is **not implemented or activated by the first increment**: it
requires exact source ownership, compiler/reconstruction, matching, canonical
identity and ABI-registry alignment before qualified lookup or language-specific
learning is supported. Never silently infer it from the form pack. Inverse
surface projection also remains open: current string substitutions become
GroundedReference fillers and cannot faithfully supply a literal answer. Genuine
definitions still require descriptive semantic content, not lexical target lookup.

Completed lexical-target checkpoint: the public development path now composes an
exact, language-unspecified `op:designation` query for the reviewed construction
`What does <literal> mean?`. Known targets are read from an activation-built exact
cross-language designation index; missing evidence remains `UNKNOWN`, while
language/target alternatives and retrieval overflow remain `PARTIAL`. Query
identity and proof lineage retain original designation facts plus authority
generation/content identity. No world fact can substitute for designation
authority, and lookup does not mutate world state.

The frame union is implemented through proposal, expansion/search, coverage,
compilation and independent reconstruction. Structural instantiation consumes no
surface evidence; the literal, content interrogative, auxiliary and terminal each
retain exact local ownership. Canonical forgery controls reject redirected
literal, binder and interrogative assignments in all three validation owners.
The target binder remains unrestricted in the canonical expression; the reviewed
kind list is activation-derived metadata and is not coupled to the 16-alternative
search cap. Pure lookup visits at most the existing 16 indexed matches and does
not enumerate omitted rows or world facts.

Independent source-spec review passes after the kind-domain correction. Quality
review found and drove the interrogative-pointer repair, then passed its fresh
re-review with no remaining issue. All 56 focused lexical/integration cases and
seven unresolved-frame guards pass. The authenticated 1,032-node owner union is
1,019 passes / the same 13 retained failures: three fragment/alias gaps and ten
historical invalid-definition aggregates. No new regression is hidden by that
known-failure accounting.

The active R4 validation-plan assertion was also stale: it still encoded the
six-owner, 33-phase-node topology that predated the already-reviewed
`exact-program-verifier` and `proposal-context` owners. It now asserts the
inventory-derived eight-owner, 35-phase-node topology and current owner counts;
this changes no gate, owner group or selector policy.

The original 104 foundation test functions and 222 metadata entries remain
unchanged; 56 literal case records were added. The immutable inventory, replay
ledger, invalidation record, R5 dispositions and ledger anchors are byte-identical.
Existing selectors and the G0 inventory receipt regenerate twice identically:
G0 191, R1 783, R2 1,173, R3 1,691, R4 2,029 and R5 2,154 active nodes; the
validation graph still has 44 steps and the same owner groups. Selector-config
SHA-256 is `ba2dad980f2b631036cabad565f7e0369435df5f5b3588183498211af148ccd2`;
receipt SHA-256 is `89cb2fb782b86de6ac3e2feb34708c388cfdcfefe24005006d62f57f68b6377f`.

The R4 scoped-event expectation now agrees with its existing
`PARTIAL + REQUEST_CLARIFICATION` decision by requiring `clarify`, not
`acknowledge`; the unchanged authentic modality aggregate is retained.

This checkpoint does not implement natural multilingual grammar, explicit
language qualification, inverse literal projection, definitions, normal R5
surface realization, alias commit/restart reuse, research or acquisition. The
non-English case transports synthetic reviewed features only. These boundaries
remain Task 5 or later obligations rather than permissive fallbacks.

Pre-pruning membership checkpoint: independent source spec review passed. The
public ordinary-membership matrix case is now green; all 31 new controls pass,
including English/Spanish reviewed-index aliases, multiword forms, source-gap
tampering, widened foreign-clause instances and transferred polarity. The four
alias/form pipelines each visit four search states without truncation. There are
no pack, authority, ABI or cap changes. All 91 predecessor foundation case
metadata entries and their test ASTs remain unchanged. Two explicit same-assertion
successors retire only composed registry-kind type expectations, preserving
renaming/canonicalization, 2/8-root linear work, and the complete 31 malformed-
graph controls. The foundation file is 118 passes / four retained failures;
the independently authenticated 353-node owner union is 336 passes / 17 retained
failures. Queries, restart and learning are not established by membership.
At this pre-pruning checkpoint, configured selectors and the canonical living
receipt were regenerated twice with identical bytes; no owner or validation tier
was added. Quality review remains open on the practical composition issue below;
the membership increment is not yet accepted as complete.

Independent quality probes found that late-only nominal geometry rejection
wastes the existing proposal budget. Two positive clauses explore 63 states and
produce 12 complete derivations (six illegal instance bindings); one negative and
one positive explore 151 / produce 40 (30 illegal role/scope choices). Two
negative clauses explore 551 / produce 200, of which only 20 are legal; a mixed
negative/positive coordination explores 215 / produces 52, of which 10 are legal.
The latter two exhaust the 48-candidate output cap and public VERIFY selects no
meaning despite valid survivors. This is not the 768-state ceiling and is not a
reason to raise either limit or train around the missing constraint propagation.
Before accepting membership, apply the existing local instance/polarity evidence
to PROPOSE's legal choices, retain independent VERIFY reconstruction, and require
the independently specified two-negative and coordinated graphs without
truncation. Do not invoke VERIFY as a proposal filter or introduce heuristic state
deduplication. Valid derivation-order duplication remains the separate Task 6
equivalence obligation; removing known-illegal choices needs no new ABI or gate.

Completed bounded membership checkpoint: independent spec and quality reviews
pass after early local-choice pruning. PROPOSE builds one immutable context-local
index; VERIFY still reconstructs source ownership independently. The four paired
cases now visit 31 / 50 / 89 / 66 states and emit 6 / 10 / 20 / 10 candidates,
respectively. Independent before/after comparison preserves every legal program
identity, not merely one surviving expression. All four public cases select the
independently specified graph without truncation. An exact frame-union guard
preserves unresolved designation contexts; an unselected nominal alternative
does not suppress a valid negative state interpretation. This remains bounded
copular membership, not general grammar, query or multilingual scope completion.

All 42 membership cases pass. The final authenticated 363-node owner union gives
346 passes / the same 17 retained failures; the membership failure is repaired,
not the four remaining foundation capability gaps or 13 predecessor/data gaps.
All 50 prior foundation function ASTs and 91 metadata entries are unchanged;
41 cases were added in total. R1/R2/R3 structural scans report zero forbidden
matches; R3/R4/R5 hard-cut checks, authority linking, fresh SQLite activation,
reopen and integrity pass. Four post-VERIFY canaries retain their previous
status classes and zero world delta. The reviewed input pack and frozen inventory
are byte-unchanged. Configured selectors and the canonical living receipt were
regenerated twice with identical bytes: G0 191, R1 783, R2 1170, R3 1556,
R4 1893, R5 2018. These are checkpoint diagnostics, not phase admission.

The wider diagnostic also identifies a test-infrastructure dependency to repair
before the next capability increment. A matched read-only `a164996` replay of
69 cases gives 41 failures / 28 passes: 40 in `test_proposal_context_abi1.py`
(despite its filename, its active contract is ABI 2) and
`test_coverage_abi2.py::test_variable_slot_role_must_belong_to_its_exact_body_frame`.
Their shared or local fixtures use source-free variables, rejected by the earlier
exact-variable-evidence containment before the intended codec/coverage assertion
runs. Repair the fixtures with independently specified query evidence; where a
frozen body hardcodes the invalid setup or geometry, add an explicit same-
assertion successor retaining the original negative control. Do not relax the
runtime rule, convert these checks into skips, or count early fixture rejection
as proof of their intended assertion. Then proceed to bounded restart retrieval.
The final pre-repair active union of both complete modules contains 135 cases:
94 pass and the same 41 fixtures fail. This wider count includes unaffected
coverage controls and is distinct from the earlier 69-case predecessor probe.
The membership repair is committed locally as `1875d35`; all 111 active governance
checks pass on that clean checkpoint. No root adoption or remote push occurred.

Completed fixture prerequisite: the shared ABI-2 context now has a distinct,
independently specified query contribution and source span. Thirty-five affected
tests run unchanged after this setup repair. Six explicit same-assertion
successors preserve geometry/source-partition, non-state transition and variable-
body role guards; one positive fixture control is added. The transition successor
also retains query source ownership when replacing the predicate, so an early
partition failure cannot mask its intended guard. The coverage contrast starts
with a fully executable positive projection and produces only
`variable_role_incompatible` when the body role is changed.

Independent spec and quality reviews pass. The authenticated fixture union is
136 passes; with all 42 membership controls it is 178 passes. The widened
499-node owner union is 482 passes / the same 17 retained capability/data
failures. All 118 prior test-function ASTs and 267 metadata entries across the
three relevant modules are unchanged; the coverage source itself is byte-
unchanged. Runtime, authority, pack, frozen inventory, ledger and anchors are
unchanged. Existing configured selectors and the living receipt regenerate
twice with identical bytes: G0 191, R1 783, R2 1171, R3 1557, R4 1894,
R5 2019. No owner, tier, runtime gate or compatibility wrapper was added.

Completed restart checkpoint (independent spec and quality passed): direct dialogue reads
and the active R3 snapshot now share bounded authenticated persisted retrieval.
SQLite uses session/global recency indexes; memory maintains commit-order indexes
at writes. Session selection precedes the window, then existing person/turn
filters apply within it. Retrieved records require exact ABI, payload hash,
key/session and generation/revision consistency. Raw target/semantic payloads
cannot become focus. SQL and memory recommits agree; SQL hashes the exact stored
JSON, repairing the tuple/list normalization defect found in independent review.
Both commit owners reject invalid focus/session identities before any mutation;
failed fresh writes and replacements leave payloads, indexes and revisions intact
and allow valid retry. This repairs the in-memory index corruption caught by
quality review without imposing a new identifier-length cap.

All 85 focus/restart cases pass, including the original after-reopen case.
The final authenticated 853-node owner union gives 837 passes / 16 retained
failures: the three fragment/alias foundation gaps plus the same 13 predecessor/
source-data gaps. All 56 prior foundation test ASTs, their 139 metadata entries
and all prior helper functions are unchanged; 83 cases are added. SQLite work is
59 / 56 / 56 VM steps with 0 / 128 / 4,224 irrelevant-session rows; its global
bounded query takes 17 steps with 4,096 other records. Memory reads visit exactly
16 window entries or 17 with the overflow sentinel, without global enumeration.

No normal focus writer, expression-content projection, conversation-window
policy, ABI or cap change is included. Direct reads retain the 512 bound; the R3
wrapper retains its 10,000 input maximum and nested JSON sequence limit of 512.
The active 16-alternative snapshot still reports overflow at 17, and emits record
identities, not expression content. Canonical record authentication does not
establish existence of a realization-equivalence receipt. Public speech history
and fragment completion remain open, not implied by the restored direct owner.

R1/R2/R3 structural scans, authority linking, fresh SQLite activation/reopen/
integrity and four post-VERIFY canaries pass with unchanged status classes and
zero world delta. Pack, authority, frozen inventory and ledger are unchanged.
Configured selectors and the living receipt regenerate twice byte-identically:
G0 191, R1 783, R2 1171, R3 1640, R4 1977, R5 2102. These are diagnostic
checkpoints, not replay admission, corpus authorization or root adoption.
The repair is committed locally as `a97858d`; all 111 active governance checks
pass on that clean checkpoint. No push, merge or root adoption occurred.

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

### Task 5 dependency hard cut

Do not turn the three remaining matrix failures green independently and call the
conversation complete. They are the visible leaves of one ordered continuation
and acquisition path. Implement and review these owners in order:

1. **Pending-query continuity.** Read only the bounded, authenticated obligation
   refs already captured by the exact `SituationContext`. Bind a learning answer
   to one same-session, pending, unexpired `LEARNING_ANSWER` and its exact answer
   contract. Zero, multiple, missing, foreign, completed, expired or corrupt rows
   fail closed. A synthetic `learning_source_query` is not an exact `QueryResult`.
2. **Continuation content.** An unknown query must create one typed continuation
   containing enough canonical query/expression and outstanding-slot evidence to
   prove that a later answer answers that query. Merely copying an opaque query
   ref cannot prove that `foo means X` answers a prior question about `bar`.
   Reuse the dialogue-obligation owner; do not add a parallel intent/session ABI.
3. **Reviewed learning authority.** Replace unlinked string defaults with one
   active, linked designation-learning contract aligned to the already linked
   `cap:learn_alias`, `permission:write_alias`, `event:learn_alias` and
   `op:designation`. User wording may propose a plan but cannot issue reviewer
   authority. Existing-target aliases and new-identity acquisition remain
   separate policies.
4. **Transactional publication.** After explicit review authorization, EFFECT
   commits exactly one designation fact and consumes exactly the originating
   continuation only after its successful receipt. Retry is idempotent; denial,
   conflict, expiry, stale revisions and partial failure leave world, obligation
   and indexes unchanged.
5. **Bounded restart reuse.** Build the runtime designation overlay from only
   admitted alias facts through a revision-keyed index. Validate target existence,
   target kind, proof and authority generation. Never rescan every world fact on
   a turn, treat a teaching claim as admitted, regenerate a form pack, or alter
   immutable authority atoms. Prove restart and unseen subject/object reversal.
6. **Fragment and response continuity.** A verified focus writer and an exact
   outstanding content slot must precede contextual fragment completion. A fresh
   fragment requests clarification without becoming a world claim. Diagnostic
   realization then renders the typed response compositionally; release profiles
   remain fail-closed until R5 realization equivalence is independently proved.

The original seeded restart test was only a world-fact/index seam probe; its
manually inserted `Fact` was not acquisition authorization. The September 8
consumer increment replaces that fixture with genuine query/directive/signed
publication and restart. Likewise, manually constructing a pending obligation
is a continuity seam probe, not evidence that an unknown public query creates a
usable continuation. Keep component fixtures distinct from the complete public
path so later work cannot substitute fixtures for runtime owners.

### Pending-record retrieval prerequisite (September 7)

Implemented the strict ABI-1 `DialogueObligation.from_dict` decoder and a bounded,
pending-only keyed read in the existing persistence owner. Memory and SQLite
authenticate the payload hash, semantic identity, stored session/status, commit
revision, active authority generation and non-future store pins. Reads reject
missing, foreign, completed, expired or malformed requested records as a whole;
they do not silently select another row. SQLite restart preserves the result.
The memory backend now detaches nested payloads and prepares both completion
records before publication, including the existing direct R3 outcome writer.
Resolved tombstones remain valid storage history but cannot be pending answers.

Fourteen focused cases pass. Independent review found and drove repairs for
partial memory completion on serialization failure and a reference-string
subclass accepted by the exact decoder. Both were reproduced RED before repair.
Keyed reads visit exactly the requested key with 128 unrelated records; SQLite
uses its existing primary-key search. No new index, runtime gate, ABI, owner,
authority default, pack or search bound is introduced. These are direct-owner
tests, not multilingual understanding or end-to-end acquisition evidence.

This is only the retrieval prerequisite of step 1, **not pending-query binding**.
The new reader does not establish membership in the exact SituationContext
snapshot, does not load canonical query content, and does not authorize an alias
write. The distinct plan-derived `r3_learning.DialogueObligation` wire shape is
not adapted into the generic dialogue shape. The broader 267-node R3-owner run
at the twelve-case checkpoint gives 266 passes and the retained actual-query
binding failure; no prior failure was removed or marked successful.

At that checkpoint the next dependency was to bind the captured snapshot and its
exact pending continuation through the
existing situation/dialogue owners, then preserve the canonical source query and
outstanding answer slot before enabling learning materialization. Copying only
`source_query_ref` would make the seam test green without preventing a `foo`
answer from binding a `bar` question. The synthetic query fallback, unlinked
learning defaults, transactional alias publication, admitted-index reuse and
fragment/response continuity remain explicitly open. Bulk R4.1/R5 remains frozen.

Final focused checkpoint: the authenticated active foundation matrix gives
288 passes / the same three fragment, actual-query binding and alias-reuse
failures. A raw whole-module run additionally executes the already superseded
form-hash assertion; it is not an active regression and its frozen body remains
unchanged. All 123 prior test/helper ASTs and 278 literal metadata records are
preserved; 14 case records were added. R3/R4/R5 structural checks, the active
legacy audit (zero findings), 517 R3/R4 metadata checks, fresh authority-linked
SQLite activation/reopen/integrity and the exact R4/R5 gate-plan tests pass.
Selectors and the living receipt regenerate twice byte-identically with active
counts G0 191 / R1 783 / R2 1173 / R3 1705 / R4 2043 / R5 2168. No phase
admission, complete regression success, alias acquisition or root adoption is
claimed by this prerequisite checkpoint.

### Exact query-content binding checkpoint (September 7)

The retrieval-only checkpoint above is now followed by executable binding through
the existing dialogue and learning owners. An UNKNOWN QUERY with one exact
UNKNOWN result retains its canonical `EvaluationBundle` in the originating
effect journal's existing bounded request payload. Known, partial and non-query
outcomes do not gain this witness. No new serialized ABI or episode scan is used.

The answer owner authenticates the complete current obligation snapshot, one
same-session pending learning answer, its exact answer contract, and the original
terminal journal. It reconstructs the preterminal journal identity and checks
the actual planned revision retained at journal creation (global revisions need
not be consecutive when another session progresses). It also checks
the source decision, query result, expression, turn, session and receipt lineage.
For the bounded lexical-target contract, existing expression instantiation fills
one target variable; every other role and the exact literal must remain equal.
Different spellings, case, sessions, expired or stale snapshots and missing or
rehashed foreign journal evidence cannot produce a learning draft. Materialization
independently rechecks this binding and target kind, inherits the pending expiry,
and no longer fabricates a `learning_source_query` identity.

Memory snapshots now use a maintained per-session pending index and commit order,
matching the existing SQLite indexed read. Snapshot and record work stay bounded
by the active configuration. No new gate, phase, semantic operator, authority
default, form-pack rewrite or increased search bound is introduced.

This proves a public unknown query plus an **explicitly constructed pending
obligation** can support an exact later answer before and after restart. Automatic
generic-continuation creation is still missing. It must be EFFECT-owned and
receipt-bound, with reviewed expiry and the one-pending policy, not a fabricated
LearningPlan. The generic dialogue record and the plan-derived learning record
retain distinct wire contracts; neither is adapted into the other.

Review exposed that the old EFFECT path would append a second plan-derived
obligation after successful binding. That path is removed and explicitly raises
`reviewed continuation publication is unavailable` before any store change.
Materialized plans are diagnostic, not executable acquisition authority. The
linked contract, review/capability/permission checks, one transactional alias
publication and successful-receipt consumption remain the next implementation
dependencies. Do not re-enable the removed duplicate-obligation writer merely to
make a public conversation proceed. This checkpoint does not yet provide a usable
complete learning conversation or resume R4.1/R5 work.

Four prior assertions receive explicit same-assertion successors with a real
query witness: exact source-query continuity, evaluated-draft materialization,
unbound-draft rejection, and positive-directive eligibility. Their original ASTs
remain unchanged. The negative scope/directive protections remain active. This
is not a waiver of those assertions or replacement of independent gold with
bootstrap output: expected alias content is independently specified.

Final bounded evidence: 48 new focused cases pass after independent spec and
quality reviews. The authenticated affected-owner/foundation union gives
382 passes / two retained failures (fresh-fragment clarification and admitted
alias restart reuse). This is not a full R4/R5 regression pass or a count of all
remaining MVP work. Original test files, the form pack, frozen inventory and
replay ledger are byte-identical. R3/R4/R5 structure checks, active legacy audit
(zero findings), 517 R3/R4 metadata checks, fresh SQLite activation/reopen/integrity
and the four post-VERIFY canaries pass. Existing selectors and the living receipt
regenerate twice identically: G0 191 / R1 783 / R2 1173 / R3 1749 / R4 2087 /
R5 2212 active nodes. No gate or owner group was added.

### Continuation lifecycle approval (September 8)

**Status: user-approved policy; automatic creation and bounded storage repair
implemented and independently reviewed. Remaining Task 5 dependencies are open.**
This records the user's explicit approval of the four-turn recommendation; it
does not derive authority from the inactive historical learning-policy files.

- A continuation created at same-session turn `n` is eligible during turns
  `n+1` through `n+4`; its exclusive `expires_turn_index` is `n+5`.
- Keep one pending learning answer per session. Do not silently replace or
  renew a live record, including on repeated lookup, restart or failed review.
- Preserve expired history. Retirement and replacement must be one successful
  EFFECT transaction; retirement is not successful learning completion.
- Alias publication remains separately authorized. Approval of this lifecycle
  is not reviewer authorization for any proposed alias or new identity.

Implement through the existing generic dialogue and effect-journal owners,
retaining exact query content and binding the persisted continuation to its
receipt chain. No fake LearningPlan, new ABI, new runtime gate or increased
search limit is authorized. Check the bounded obligation snapshot atomically:
its store revision is separate from RevisionPin. Preserve failure atomicity,
blockers, idempotency and same-session ownership in memory and SQLite.

The required completion evidence is automatic public-query creation, deadline and
replacement behavior, restart/retry, and exact later-answer binding without
manual pending-record insertion. This does not by itself close Task 5: linked
learning authority, transactional alias publication, admitted-index reuse,
fragment handling and faithful response realization remain open. Task 4's
remaining semantic-query obligations and Tasks 6–7 also remain open. The prior
48-case checkpoint is not full repair completion or R4/R5 admission.

**Demo-only review approval (September 8):** the user explicitly approved the
alias `velnora` to the existing `likes` meaning for an isolated temporary-store
demo. The demo uses English publication metadata and the existing `rel:likes`
identity. This approval must not add an alias to checked-in authority, authorize
other mappings or stores, or become a default runtime reviewer grant. The demo
must exercise the real publication/restart path once that owner is implemented.

### Automatic continuation checkpoint (September 8)

Public unknown lexical-target queries now create the generic continuation in the
existing terminal no-effect transaction. Canonical query content and pending
snapshot remain independently authenticated. Live records are preserved; expired
retirement and replacement are atomic. Same-session reservation checks prevent a
delayed query from rewinding the session; ordinary foreign-session progress is
permitted when the captured obligation snapshot is unchanged. A foreign obligation
write can still invalidate the global snapshot and fail closed; no new per-session
snapshot ABI is introduced.

Independent semantic review and a separate main run each passed 102 focused
cases. The authenticated 438-node affected-owner/foundation union gives 436 passes
and the same two retained fragment/alias-index failures. This is not the complete
MVP regression suite or a claim that only two repair tasks remain.

Quality review found a missing SQLite pending-session index: the new transaction
checks amplified an existing snapshot scan. Measured work grew from 35 to 12,323
VM steps with 0 to 4,096 unrelated rows. Earlier claims that this snapshot was
indexed were not supported by its test, which inspected the representation of a
SQLite Row rather than its query-plan detail. Repair the schema owner and verify
real plan detail, scaling and existing-store reopen before marking this increment
complete. Memory already uses its bounded per-session pending index.

R3/R4/R5 structural checks, 517 R3/R4 metadata checks and the active legacy audit
(zero findings) pass at this pre-index checkpoint. Existing selectors and living
receipt were regenerated twice identically; they will be refreshed after the
index tests. No authority data, form pack, frozen inventory, ledger, cap or runtime
gate changed. Alias-publication, restart reuse, response/fragment continuity,
semantic-query projection and measured composition repairs remain open.

The index repair is now verified: existing-schema activation creates the covering
`obligations(session_ref, resolved, revision, obligation_ref)` index. Twice-reopened
older indexless stores retain exact records, revisions and schema version. Actual
plan-detail assertions prove indexed SEARCH without a temporary sort. The public
continuation-request probe takes 39 VM steps at 0, 128 and 4,096 foreign rows.
Snapshot reads take 28/29/29 steps for both foreign-pending and same-session-resolved
history; the one-step boundary check is constant, not growth with store size.

Final independent quality re-review passes 114 focused foundation/effect/public-
cycle/situation controls. The next dependency is active linked learning authority,
followed by reviewed transactional publication, not a renewed continuation review.
The main agent's final three-module run passes all 105 cases. Selector/receipt
regeneration is twice byte-identical with G0 191 / R1 783 / R2 1173 / R3 1806 /
R4 2144 / R5 2269 active nodes; the original frozen inventory remains unchanged.

### Linked learning authority prerequisite (September 8, reviewed)

The active manifest now links one typed `DesignationLearningContract` from
`alias_learning.json`. It owns the existing v2 learning/answer contract refs,
`goal:resolve_designation` and the review policy, and explicitly relates
`event:learn_alias`, `cap:learn_alias`, `permission:write_alias` and the internal
`op:designation` / `label:lexical` commit. Four internal kinds have no generated
user-facing designations. This is source authority, not an approval for any alias.

Generation is `authority-v1-2026-09-08-linked-alias-contract`; both content and
model-compatibility identities change. The three prior owners and language packs
remain unchanged. Existing stores reject the new generation rather than silently
repinning or resetting data. The historical monolith splitter now refuses any
nonempty authority output, preventing it from deleting supplemental authority.

Activation builds exact indexes and validates/hash-binds contract fields. Review
found that additional source `effect_schema` and malformed phase values could be
silently accepted. Fourteen failing probes drove the repair: extra effects and
malformed phases now fail activation; absent defaults and valid explicit phases
remain supported. Actual runtime session phases use the established plain phase
values; synthetic fixture labels do not expand the active phase vocabulary.

Three same-assertion successors preserve generation/kind/link-validation controls
with the new explicit source contract; frozen originals remain historical evidence.
This source prerequisite does not complete dependency 3: the pure event-to-
designation lowering and materializer must still consume it, retain actor/source
provenance, enforce current capability/permission/phase and remove unlinked plan
defaults. Dependency 4 will add separate explicit review authorization and atomic
publication; no conversation-triggered reviewer or second pending record is allowed.

Independent spec and quality reviews pass. A fresh main run passes all 204 linked-
authority, automatic-continuation, binding and query-witness cases, including 99
authority cases. The existing authority-linker controls also passed independently.
Selectors and the living receipt regenerate twice identically with G0 191 / R1
879 / R2 1269 / R3 1902 / R4 2240 / R5 2365 active nodes. The frozen inventory,
prior authority owners and language packs remain unchanged; no gate was added.

A raw R1-phase selection against the current R3 runtime also executes retired
pre-R3 expectations. Its 24 such failures are already superseded outside the
current R3 active set; restoring the retired runtime to satisfy them would be a
regression. The dirty-input replay-status control remains intentionally sensitive
before checkpoint commit. These diagnostic distinctions are not phase admission
or a claim of a full regression pass.

The fresh intersection of R1-owner controls and current R3 lineage gives 852
passes and only the expected dirty-input status rejection (853 selected nodes).
R3/R4/R5 structural checks and 517 R3/R4 metadata checks also pass.

### Linked event lowering checkpoint (September 8, reviewed)

The shared pure lowerer now selects only the exact linked learning-event source,
then validates the complete positive single-application graph, explicit addressed
executor, current phase, actual and captured actor grants, and reviewed existing
target kind. It derives canonical designation answer content without replacing
the original event meaning. EVALUATE and materialization independently bind that
content to the exact pending query and rederive source/actor/authority proofs.
Plan contract, goal, capability, permission and commit refs have no unlinked
defaults. Capability and event-specific permission lookups are activation-indexed.

Direct designation requests no longer use the old role-shape learning shortcut.
Teaching claims remain attributed content. Missing capability remains UNKNOWN;
missing permission is DENIED. A bounded typed lowering error retains the exact
missing-target diagnostic at its owner. The incomplete-learning assertion has a
same-assertion successor over the reviewed event source; its predecessor body
remains unchanged. The later continuation fixture now supplies this actual event
and actor instead of a designation request with no actor.

A fresh main run passes all 244 focused cases, including 40 lowering cases.
The public forms `learn velnora means likes` and `learn that velnora means likes`
reach the inspected EFFECT boundary with original event meaning and a linked
plan. An independently reviewed unseen learning synonym reaches the same path
without pack regeneration. These boundary probes intentionally stop before
EFFECT: they are not publication or a completed conversation demo. Authority
source, form packs and historical splitter remain unchanged from `c29768b`.
Independent spec review passes 177 controls; quality review passes 244 and
additional positive/negative/multi-root graph probes. Existing selectors and
living receipt regenerate twice byte-identically: G0 191 / R1 879 / R2 1269 /
R3 1941 / R4 2279 / R5 2404. Structural checks and 517 R3/R4 metadata checks pass.

The full current R3 selection gives **1916 passes / 25 failures**. Twenty-four
failures independently reproduce in an exact temporary `git archive` of the
preceding `c29768b` checkpoint; representative traces confirm the same failure
owners. The remaining failure is dirty-input replay-status rejection. This
establishes no newly failing selected R3 test in this increment, not a green R3
release or complete repairs. The pre-existing active failures are:

- 19 learning-closeout wrappers all execute the same old helper, which still
  calls superseded direct-designation/unbound-query tests. Their individual
  acquisition, capability, review, retry and consumption assertions need real
  current-path coverage as those owners are completed. Do not redirect nineteen
  names to one shared smoke check and call those distinct properties proved.
- The five-operator adversarial successor constructs stale derived-role targets;
  the unresolved-query test still forces generic `What is zorbulate?` into
  lexical lookup. Reconcile these with current source/query contracts using
  honest successors, retaining operator, provenance and binder protections.
- The reviewed greeting-frame test is a **real regression introduced by
  `c29768b`**, not a stale assertion. The baseline comparison above predates only
  the lowerer, not that authority change. See the corrective finding below.
- Fresh-fragment clarification and admitted-alias restart reuse remain the two
  retained direct foundation failures. The broader count must not be reduced
  to those two or presented as only two remaining implementation tasks.

LearningPlan ABI 2's diagnostic plan-derived obligation remains unchanged in
this increment. Its retirement and the explicit version migration below must
precede enabling proposal persistence; no second pending record is reintroduced.

### Reviewed-frame preservation repair (September 8, verified at `b3df099`)

Pause the planned artifact migration until this earlier authority owner is fixed.
`c29768b` changed the authority generation but left the six reviewed affordance
frames pinned to July 29. `SemanticAffordanceIndex._load_frames` independently
loads that unlinked file and silently returns an empty index on generation
mismatch, read failure or invalid JSON. This erased reviewed refinements into
kind/signature defaults. The narrower authority and continuation suites missed
it; comparing only to `c29768b` could not establish preservation of the preceding
`de40359` behavior. Do not replace or weaken the failing frame assertion.

Register the existing frame source in the manifest, hash and validate all its
records at linking, and expose the linked generation-indexed frames to the
affordance owner. Remove ambient file discovery and invalid-frame fallback.
Preserve all six reviewed records, explicit frame provenance and their behavior;
kind defaults remain valid only for targets without a reviewed frame in the
explicit linked bundle. No per-cycle frame scan, new gate, form-pack rewrite or
search-cap increase. Prove missing/stale/tampered/malformed frame-source rejection
and replay both original frame controls and public learning/composition paths
with the frames actually active before resuming the artifact migration.

Use the distinct generation `authority-v1-2026-09-08-linked-frames`: the existing
store activation owner pins generation, so retaining the preceding label would
silently activate different frame content in an existing store. Prove prior-
generation reopen rejection with preserved user data. This is an authority
source migration, not a new artifact ABI, store reset or model reactivation.

The reopen rejection probe also exposed an existing resource leak: `open_stores`
did not close its SQLite connection when backend activation raised. Close only
that failed construction's connection and retain the original error. Verify
durable data and metadata preservation and real connection closure; SQLite WAL
bookkeeping is not itself semantic mutation. No schema or transaction-policy
change is part of this cleanup.

The first independent spec review additionally rejected a false assurance:
matching port names alone did not validate source roles. A hash-refreshed bundle
could pair a malformed frame port with the same malformed signature role, accept
a string in place of a filler-kind list or a non-boolean requirement flag, or
leak `KeyError` on a missing field. The shared reviewed-source role parser now
checks exact fields, bounded typed role refs/kinds, uniqueness, boolean flags and
application/proposition agreement before activation. Seventeen observed-RED
contrasts cover that correction; alias contracts reuse the same structural
parser while retaining their narrower exact semantic requirements. Independent
spec re-review passed all 171 frame/affordance/alias cases before the final
operator-schema correction below.

Main's full authenticated 1,994-node R3 run after the role-schema correction:
1,970 passed and 24 failed in 178.51 seconds. The original reviewed-frame test
now passes. The failure set is the preceding 25-node set minus that frame
regression: nineteen old learning wrappers, the five-operator derived-role
fixture, generic-question lexical assumption, fresh-fragment handling, admitted
alias restart lookup, and the expected dirty-governed-input status rejection.
No new failing node appeared in this replay; this is not a green full regression
or evidence that those twenty-three non-governance obligations are complete.
The four existing post-VERIFY canaries and R3/R4/R5 structural checks also pass;
canaries still have zero world delta and do not establish a useful public demo.

Quality review found a related operator-edge gap: missing/duplicated structural
output ports could still agree with a frame's input list. Reviewed event and
relation frames now require their complete fixed linked operator schemas, without
coercing source objects into lists of keys; output ports come from those validated
slots. Seven observed-RED cases prove the correction, including event frames in
an explicit bundle without the alias contract. Final independent spec and quality
reviews each pass 178 focused cases. Main's final combined frame, original
affordance, alias, continuation, lowerer, query-witness and persistence run passes
all 371 cases in 36.92 seconds. No frozen test body, form pack, semantic frame
record, search cap or runtime gate was changed.

Active source identities:
`authority-content:a39de23a35b572dc0ef46014` and
`authority-compat:567e328fb278a49cf6f2f08b`; frame owner SHA-256
`69f0670f76338737e99d435130dd24be853e42d94a7a2369650460c73af3bf13`.
The 60 new cases use the existing R1 runtime owner and propagate through existing
selectors (G0 191 / R1 939 / R2 1329 / R3 2001 / R4 2339 / R5 2464).
The preserved frozen inventory hash remains
`7c27b0ad80998fc1f10876c05d0238a2498d2fd3a116ace77c9505da11d0b4b8`.
This checkpoint restores reviewed frames and closes its validation/resource
defects; it does not complete the foundation, admit a phase or publish an alias.
Resume the pending canonical-continuation migration next.
The clean-worktree status regression passes at `b3df099` (1 case, 3.77 seconds).
Configured selectors and the living inventory receipt were regenerated twice
with byte-identical hashes; no commit was pushed or adopted at root.

### Publication transaction boundary — historical scope correction

**Scope correction — proceed with the approved foundation repair.** The earlier
execution pause in `9ccc4a2` overstated historical test names as current feature
requirements. The user approved the recommendation to correct stale test routing
and requested a broader regression-inducing/stale-test audit before continuing.
At that audit checkpoint canonical-continuation migration was pending. The later
canonical-continuation and authenticated-publication checkpoints below supersede
that implementation status without changing the audit evidence.
The demo-only English `velnora` → `rel:likes` approval remains recorded and does
not need reopening.

Independent inspection of all nineteen failing learning wrappers and their
deleted ancestor bodies (`6b8fc23^`) found eleven designation/lookup protections
and eight separate reviewed rule-acquisition assertions. The latter call
`plan_reviewed_acquisition(..., acquisition_kind="rule")`; their positive cases
require created rule refs, one new authority generation, unchanged compatibility
identity and consumed-plan protection. This is not necessarily atom creation,
but it is not alias publication either. The main agent independently read the
original `tests/test_synonym_acquisition.py` and confirmed that distinction.
Its retired program-shaped implementation and teaching fixtures must not be
reconnected as a shortcut under canonical-expression authority.

The current wrappers do not execute those ancestor assertions. All nineteen
route to one cached learning smoke helper; `assertion_ref` is only prefix-checked
and never selects the assertion being proved. A reproduced five-rule wrapper
fails at an unrelated `PENDING` versus `UNKNOWN` expectation, while the direct
current reviewed-rule inference/proof-lineage test passes. Reviewed-rule use and
external rule publication are distinct capabilities. The foundation amendment
requires the former where relevant and bounded existing-target alias learning;
it does not require restoring the old external five-rule publisher.

Do not redirect publication assertions to passing alias smoke tests or restore
retired program-shaped teaching fixtures. Preserve ancestor evidence and make
unproved coverage explicit. Keep independently valid one-use/idempotence,
authorization, capability, exact-plan binding, compatibility and atomic-rollback
protections as assertion-specific current-path checks. Classify obsolete
publication scenarios explicitly rather than treating their names as authority.
No new runtime gate, rule publisher, phase admission or inventory waiver is
authorized by this correction. Frozen inventory and historical ASTs remain
unchanged. The same audit must inspect non-learning shared helpers and stale
query/graph/state fixtures before their green counts are cited as coverage.

**Further audit findings (September 8; not phase admission):**

- All 147 non-learning closeout wrappers are active at R3 but route to only
  eleven distinct cached, no-argument helpers. Along with the nineteen learning
  wrappers, these are 166 named cases, not 166 independently proved contracts.
  Invented assertion refs were accepted too. Repair the existing test dispatcher
  with exact audited bindings and explicit failures for unproved mappings. The
  first three audited bindings preserve raw-phrase-dispatch, cyclic-expression
  rejection and retired-checkpoint-API protections through their actual current
  tests. Do not infer bindings from names or silently omit unresolved wrappers.
- State-query wrappers never execute their named present/past questions. The
  ten `test_temporal_state.py` cases exercise a standalone index through a test
  facade, not the public runtime. Their index assertions remain useful narrow
  evidence; they do not prove temporal language understanding or admission.
- The thirteen epistemic wrappers run one untrusted observation, not distinct
  correction, trusted admission and nested-mode cases. Twenty query wrappers run
  one supported-rule inference, not separate unknown, budget, memoization,
  multi-hop and synonym checks. Preserve those valid assertions individually;
  restoring old program-shaped engines is not an acceptable repair.
- Current state/admission/receipt controls were checked independently: 33 selected
  cases pass, including negative/conditional admission and no-effect retry
  protections. These must not be discarded merely because nearby wrappers are
  stale. This focused run is not a complete state or full-regression proof.
- The directly seeded alias restart fixture is not authenticated acquisition:
  a `proof.source` string beginning with `review:` is insufficient. Replace its
  positive fixture through the real approved publication transaction when that
  owner exists, and retain an unreviewed-insertion rejection contrast. Never
  broaden admitted lookup to accept arbitrary stored designation facts merely
  to turn this diagnostic green. Restart/unseen composition remain required.
- The five-operator positive fixture forces a uniform subject shape and lacks
  current operator-specific derived roles. Replace it with an explicit successor
  proving all five shapes against independent expected expressions and linked
  frames; retain unknown-operator rejection. The lexical-query fixture must use
  an explicit meaning lookup, retaining exact label roles, target binder,
  round-trip identity and no invented concept. Generic `What is X?` remains a
  separate no-laundering contrast, not automatically a lexical query.
- Fresh-fragment clarification is still a real usability requirement. Preserve
  exact clarification and no mutation, but audit the test's intermediate
  `evaluation is not None` demand against typed-frontier handling before choosing
  an owner repair. Do not invent a settled meaning just to obtain an EVALUATE
  artifact, nor weaken critical-residual verification.
- `TransitionEngine.commit` is a dormant duplicate write path: it accepts a
  preview and writes directly to the world store, despite describing a verified
  effect receipt. It has no current runtime caller. Its direct-commit tests must
  not motivate reconnecting it. Remove that mutation path with explicit
  successors retaining transactional/revision/history protections at the real
  `R3EffectGateway`; keep useful pure transition-preview/unit-index assertions.
  This separate cleanup is identified, not yet implemented in this audit.

This audit separates missing test evidence from missing runtime behavior. A
larger explicit failure count after correcting false coverage is not evidence
that those runtime behaviors newly regressed. Resolve each surviving assertion
alongside its current owner; obsolete external publication scenarios remain
unproved historical obligations, not a reason to expand this foundation task.

**Test-only correction implemented:** `tests/test_foundation_test_successors.py`
contains the two same-assertion successors and a separate unauthenticated-alias
restart negative. It does not supersede the pending authenticated publication
positive. Exact independent forests and complete source assignments prove the
five operator shapes without freezing unused schema alternatives or role order.
The generic smoke helper module is now 39 lines; its dead imports and cached
helpers are removed, while all 166 historical wrapper bodies remain unchanged.
Three audited safety mappings execute their actual tests; 163 mappings now fail
explicitly as unproved rather than claiming coverage. The nine-case routing suite
checks invented identities, wrong categories, exact runner invocation and failure
propagation. Passing these repairs is not R3 admission. The focused routing,
fixture, safety and governance run passes 25 cases. Existing selectors were
regenerated twice with identical artifacts (G0 191, R1 939, R2 1329, R3 2011,
R4 2349, R5 2474); the frozen inventory remains unchanged. No gate, owner, phase,
bound, dependency or runtime behavior was added or changed.

Independent spec and quality review passed for this correction. The complete
authenticated current R3 selection ran 2,011 cases: 1,845 passed and 166 failed
in 199.93 seconds. The failures are 163 explicit unproved successor mappings,
the outstanding fragment and authenticated-alias diagnostics, and the expected
dirty-input status check. This supersedes the misleading interpretation of the
earlier green wrapper count, not historical run records. Remaining coverage must
be matched to current assertions as owner repairs proceed; do not treat 163
unproved mappings as 163 newly observed runtime defects. Canonical continuation,
reviewed publication/restart, fragment usability and the dormant writer cleanup
remain open. No repair-completion, demo-completion or phase-admission claim follows.

**Approved follow-through — remove obsolete tests, then finish owner repairs.**
The user explicitly requested physical removal of redundant/obsolete tests after
the audit. Preserve the immutable inventory and recoverable Git history at
`add3917`, not stale duplicate pytest bodies. First remove only source functions
whose entire parameter set is inactive across G0 through R8 and whose surviving
assertions have actual current checks, plus redundant wrappers where selecting
their exact underlying test preserves the assertion. Shorten later-node lineage
edges across deleted intermediates without changing retained ancestry or phase
coverage. Do not classify R5 deferrals or unproved assertions as obsolete merely
because they are not currently executable. Verify exact before/after active
coverage through the existing inventory verifier; no new runtime gate is needed.
Remove the dormant preview-to-world writer with current EFFECT-owner protections,
then continue the canonical-continuation/publication and remaining foundation
tasks below. The cleanup is not a new completion boundary or permission request.

Cleanup evidence: 45 whole test functions (47 cases), three redundant safety
wrappers, the now-unused learning-transaction module and the historical wrapper
generator were removed. The first deletion preserves exact active node/assertion
bindings in all nine phases; the second substitutes only the three existing
assertion-specific safety tests. Surviving test bodies are unchanged except the
G0 module-presence list's removal of the deleted module. Twenty-five later lineage
edges were shortened; immutable inventory and historical ledger identities did
not change. Independent spec and quality reviews pass; 222 focused successor/control cases
and the main 30-case authenticated governance/inventory selection pass. A raw
historical suite-hash test still encodes an obsolete entire-suite identity; it is
not selected by the current R3 lineage and its hash was not rewritten. Existing
selectors and receipt regenerate twice identically, with phase counts unchanged.
The 163 unproved mappings remain explicit, not silently retired or counted as
new runtime defects. Deleted source is recoverable from `add3917`.

The follow-through exposed an actual EFFECT defect: a distinct new operation
prepared on the original pin could execute after another operation committed.
The gateway silently rebased its journal onto the newer store. New effectful
requests now retain their source pin at the existing journal reservation, with
SQLite revision comparisons inside `BEGIN IMMEDIATE`. Exact existing requests
authenticate their persisted content and retain retry/reconciliation behavior;
ordinary no-effect queries retain their separate continuation policy. Nested
request comparison uses canonical thawing rather than shallow dictionary equality.
`TransitionEngine.commit` and its three obsolete tests are removed; current-owner
successors preserve revision, proof/history and restart assertions, while pure
preview tests remain. Main observed the stale-request and direct-writer tests RED
before the repair. Independent spec and quality reviews pass. The second dormant
`commit_effect_transaction` helper/export is also removed. Its later atomic test
retains the same assertion identity but now injects failure after real SQLite
world/session writes, proves rollback and durable OBSERVED evidence, then reopens
and commits exactly once without invoking the device again. That test exposed a
separate restart defect: the strict adapter decoder received frozen persisted
JSON. Thawing at that existing decode boundary repairs recovery without broadening
the decoder or changing receipt ABIs. Both defects were observed RED before GREEN.

Main's receipt/currentness/pure-preview run passes all 18 cases. The full
authenticated R3 selection gives **1,848 passes / 166 failures across 2,014 cases**
in 159.31 seconds. The exact failure set is unchanged: 163 unproved mappings,
fresh-fragment clarification, the still-unimplemented authenticated-alias restart
diagnostic, and dirty-input status rejection. This is not full repair completion.
R3/R4/R5 structural checks, 507 later test metadata records, the active legacy audit
(zero findings), source compilation and four post-VERIFY canaries pass. Canaries
retain zero world delta; they are not the requested useful conversation demo.
Selectors/receipt regenerate twice identically: G0 191 / R1 939 / R2 1329 /
R3 2014 / R4 2352 / R5 2477. No frozen inventory, authority data, form pack, gate,
search bound or ABI changed. New-request currentness is checked at reservation;
in-flight recovery intentionally keeps its original request witness. This does not
claim unrestricted concurrency after an operation has begun.
Continue with the approved canonical-continuation artifact migration and reviewed
publication/restart path below; query/fragment, composition and response proof
remain open. Do not reopen the already-verified frame-preservation prerequisite.

The learning utterance is a proposal, not reviewer authority. Preserve its exact
query, expression, situation, plan and terminal no-effect receipt as immutable
lineage. A later explicit review must use a distinct publication journal and a
fresh commit snapshot. It must not replay the utterance, rewrite historical pins,
rewind a session, create a second pending obligation or consume another turn.

For source-query turn `n`, answer turn `a` and current session turn `m`, require
`n < a <= m < n+5`. Current linked target, grants, pending row, exact source
evidence and conflict checks still apply. Publication commits one alias fact,
the original obligation's completion and one receipt atomically. Only world,
effect and obligation revisions advance; the out-of-band review leaves session
and episode revisions unchanged. Denial or failure cannot publish a fact, consume
the pending obligation or update designation indexes. A durable failed attempt
may remain journal evidence; it must never be mistaken for successful completion.

Avoid a receipt hash cycle: the fact may cite the independent authenticated
review observation; the final successful effect receipt cites that fact and the
original pending obligation. The completed obligation then cites the final
successful receipt, not merely a review authorization that might never commit.
All three records become visible together. Identical retries return the same
receipt; changed grants cannot republish the same plan. This boundary does not
activate publication; its implementation and race/restart tests remain open.

The reviewed source-obligation design requires an explicit hard-cut migration,
not an ABI-2 substitution: LearningPlan ABI 3 hashes a required
`source_obligation_ref`; R3Artifacts ABI 2 and ResponseMeaning ABI 3 carry the
exact existing generic dialogue record; Effect/No-Effect Receipt ABI 2 binds
that source obligation rather than a plan-derived duplicate. Generic Dialogue
ABI 1, Decision and EvaluationBundle remain unchanged. These are **implemented
candidate codec versions**, not admission claims. The duplicate learning-obligation
class and its active imports are removed together; no decoder adapter, fake record
or permissive version fallback is allowed. Registry defaults, strict decoders and
active test successors follow this hard cut. Non-learning response semantics remain
preserved; incompatible serialized receipts reject activation without resetting or
repinning stored facts. At this codec checkpoint proposal persistence and
publication were still disabled; the following proposal-transaction increment
does not enable publication.

### Canonical-continuation artifact checkpoint — September 8

Learning materialization now retains the original generic pending record, with
its exact source query, answer contract, session and exclusive expiry; it does
not append a second obligation or renew the first. LearningPlan identity covers
the required source-obligation reference and retains it in provenance. Response
and R3 artifact assembly reject missing source content, foreign program lineage
and mismatched answer-input pins. Original-query, answer-input and response-output
pins remain distinct; valid output advancement is preserved. Receipt validation
uses the existing activation traversal and keyed journal read, not another scan
or validation tier. The unused duplicate-owner helper is removed as well.

The focused migration/continuation/currentness/receipt set passed 201 cases;
independent specification re-review passed 50 and quality review passed 56.
The new artifact module has 45 concrete cases. Existing later tests were migrated
in place with their assertions retained. The immutable configuration predecessor
is replaced by a same-assertion successor for the new ABI tuple, retaining every
original bound and frozen-configuration assertion; its independent review and
focused test pass. The obsolete function is recoverable from `f5d9e80`, not a
second live test path. No authority, form pack, search bound,
frozen inventory or replay status is changed. The full pre-successor run yielded
1892 passed / 167 failed: the stale ABI-tuple assertion plus the known 163 unproved
successor mappings, fresh-fragment and reviewed-alias diagnostics, and dirty-input
status rejection.

Final authenticated R3 replay: **1893 passed / 166 failed / 2059**, in 171.31
seconds. The exact failed-node set equals the pre-migration baseline: 163 explicit
unproved successor mappings, fresh-fragment clarification, authenticated-alias
restart/reversal, and dirty-input status rejection. There are no new active R3
failures. This is not a green R3 release or foundation completion. The status check
is rerun on the clean local checkpoint; the 165 substantive failures remain open.
R3/R4/R5 structural checks, 507 R3/R4 metadata records, source compilation and the
legacy-test audit (zero findings) pass. Four post-VERIFY canaries remain no-effect
with zero world delta, not a useful conversation demo.

Selectors and the existing receipt regenerate twice byte-identically: G0 191 /
R1 939 / R2 1329 / R3 2059 / R4 2397 / R5 2522. Config SHA-256:
`feb0c2b2a0f969e7a03c99b2b0ac9d3f488a00c4b786c8e2adea450b0e86f481`;
receipt SHA-256:
`5fc55e950dfa02c2fbf6e743d60a2fd8492eef637c86905b90f166a6fee7b389`.
Existing gate definitions, owners, dependencies and limits are unchanged; only
test selectors/source inputs are refreshed. Frozen inventory remains
`7c27b0ad80998fc1f10876c05d0238a2498d2fd3a116ace77c9505da11d0b4b8`.

**Checkpoint handoff:** implement the already-approved no-world-write learning
proposal transaction and distinct authenticated reviewer publication through the
existing EFFECT/persistence owners, then admitted alias lookup and restart reuse
through both grounding and query. Preserve the exact original pending row and
one-use review boundary described above. Do not reopen frame preservation, the
four-turn policy or this artifact migration; do not mistake them for publication.

Restart reuse must cover both grounding and lexical-query retrieval. Currently
`bootstrap._DesignationStore` returns only the immutable authority index, while
`QueryDecisionOwner` independently reads that same static index. Repairing only
the grounding hook would leave a learned word usable in a clause but unknown to
its own lexical query. Use one admitted-designation lookup contract through
these existing owners, without mutating `LinkedAuthority.designations` or making
world aliases into R4 source authority. Preserve exact/case-folded distinctions,
ambiguity and source proofs; a mutable entry must not silently shadow immutable
authority. Bound relevant reads and cached results by revision and lookup key,
not a full-world rebuild per span or turn. Grounding and query proof must retain
the actual admitted fact/review/commit lineage, not label a learned fact as an
immutable authority-source fact. This is still an implementation dependency,
not evidence that the current seeded alias-index test proves acquisition.

The shared reader must also serve the context builder's canonical-surface lookup
for designation-as-application lowering; leave frozen R4 authoring untouched.
Keep the canonical surface/target/language designation identity separate from
the admitted world Fact identity. Existing grounding-candidate provenance and
query Fact-view/source-proof fields can carry the actual admission lineage; no
new semantic ABI or separate VERIFY validation tier is required. Admission is
authenticated at publication and checked on reading through the trusted
ORIENT/context and query owners. An unkeyed receipt hash is not a claim of
protection against fabrication of an entire database by an offline attacker.
Each historical record must match its own original model witness; different
conversation turns need not use one model. The answer plan, proposal receipt and
publication retain their shared model identity, while the source query retains
its independently authenticated original pin. A completed designation remains
world knowledge when the proposer changes under the same authority and store.
Keep the current-answer-model check on fresh publication, not on later admitted
reads; neither rewrite historical pins nor add a model migration/activation path.

SQLite's cached `revision_pin()` values cannot authorize reads of newer live
rows. The admitted reader must compare fixed metadata revisions against its
expected pin within one read snapshot before using a cache or bounded rows and
keyed proof records. Prefer one scope for ORIENT's bounded batch; query uses the
same rule. Never silently rebase a constructed context. Final publication
conflict/currentness checks remain inside the existing write transaction.

### Learning-proposal transaction increment — September 8

The bounded proposal transaction passed independent specification and quality
review; this is not a Task 5 completion or replay admission. The existing EFFECT
journal now retains the exact canonical verified
meaning, evaluation/situation, LearningPlan, original generic pending row and
source-query journal witness for a learning proposal. Fresh proposals independently
materialize against linked authority and authenticate the actual read-only ORIENT
reservation. The terminal `LEARNING_OBLIGATION_ONLY` receipt advances the answer
session once and retains the original pending record unchanged. It neither
publishes an alias nor invokes an adapter.

Existing journal begin/transition transactions own serialization, current revision
and source-snapshot checks, parent-row comparison and SQLite rollback. A terminal
exact retry returns its stored receipt, including after restart or source expiry;
an unfinished proposal may only finish under its original reservation and pins,
allowing its own journal reservation increment. No historical meaning is repinned.
The keyed session-snapshot owner also rejects a stored key/session mismatch rather
than concealing it in a snapshot made from the requested key.

The obsolete direct learning-outcome writer, persistence-port declaration and
helper/export are removed. Its two memory/SQLite atomic-metadata assertion
identities now exercise invalid serialization before reservation and before
terminal mutation in the real proposal path. The formerly blocked duplicate-row
test is also removed: its assertion now runs against a successful SQLite proposal
and the unchanged original pending row. These three obsolete cases remain
recoverable from `6d448ac`, not as live alternate paths. The source-query capture
race was reproduced and fixed by retaining the exact journal returned by shared
binding validation, rather than rereading it after validation. Existing public
row/pair APIs delegate to that same validation owner.

No new record class, ABI, table, validation gate, full-store scan or search bound
is introduced. The new proposal module has 48 passing cases, independently rerun
by both reviewers. Specification review additionally passed 187 combined proposal,
binding, artifact and lifecycle cases. Main verified preservation of all 372
assertion identities across the affected existing test modules; surviving test
bodies are unchanged except the artifact test's current default-deny expectation.

Final authenticated R3 replay: **1938 passed / 166 failed / 2104**, in 192.49
seconds. The exact failed-node set remains the same 163 unproved successor
mappings, fresh-fragment clarification, authenticated-alias restart/reversal
diagnostic and dirty-input status check. There are no new active R3 failures.
The clean-checkpoint status test is rerun after committing; 165 substantive
active-R3 failures remain open. This is not a green release or foundation completion.
R3/R4/R5 structure, 507 later R3/R4 metadata records, source/scripts compilation,
legacy-test audit (zero findings), and four post-VERIFY no-effect canaries with
zero world delta pass. The canaries do not substitute for the requested useful
conversation/learning demo.

Existing selectors and receipt regenerate twice byte-identically: G0 191 /
R1 939 / R2 1329 / R3 2104 / R4 2442 / R5 2567. Config SHA-256:
`cfce3ddd325828b2a2f765e05861564898c644a5e8ddd988f39470af05ada0c4`;
receipt SHA-256:
`712fc11da58cf29a6b7945c1c2040baa5ad40275290c03b7011755f8fe13ed28`.
Gate definitions, owners, dependencies and limits are unchanged. Frozen inventory
remains `7c27b0ad80998fc1f10876c05d0238a2498d2fd3a116ace77c9505da11d0b4b8`;
authority, language packs, replay ledger and repository-root checkout are untouched.

A direct post-doc run of governance/config/proposal modules passed 139 and failed
two: the expected dirty-input status check and the later R5 documentation test
`test_r5_active_docs_publish_truthful_foundation_boundary`, which still requires
the retired phrase `canonical train partition only`. The latter is outside the
R3 selector and its source/architecture were unchanged by this increment.
The subsequent test-only correction replaces that retired phrase with six
whitespace-normalized checks of the current R4.1 freeze, fresh admission and
explicit-data-authorization requirements, canonical train authorization/capability
binding, sibling-data isolation and later activation ownership. All 21 other
original assertions and every other test-function AST remain unchanged. Its node,
assertion identity, phase and task metadata are retained; only its source hash
changes. The architecture is not rewritten to revive superseded permissions.
The proposal checkpoint's clean status test passed before this correction.
The correction passed independent specification and quality review, the exact
affected test and six related controls; six boundary-removal mutations were
rejected. Main's combined governance/config/proposal run passed 140 with only
the expected dirty-input status failure. Selectors/counts and gate config remain
unchanged; the existing receipt regenerates twice identically to
`f15098d2f50d7d6b6b87d21664fc4c0f3e8bc82417d94db0aa397f8bd4e3a972`.
No runtime, architecture, authority or frozen-inventory change accompanies this
test correction. At local checkpoint `3d1bf7d`, the combined governance/config/
proposal modules passed **141 tests in 18.70 seconds** with a clean worktree.

**Remaining ordered work:** shared admitted-designation lookup through grounding,
the context builder and query; isolated restart and unseen-composition demo.
The publication implementation and verification are recorded below. Review remains
default-deny and genuinely authenticated, not inferred from a teaching utterance
or a reviewer-looking source string. The exact scope and acyclic receipt lineage
above remain governing. Fragment, composition and response repairs are still open.

For the approved isolated demo, review authorization is issued outside dialogue
and binds the exact proposal/receipt/plan, source query and pending row, target
store, reviewer/policy, finite expiry and one-use identity. The alias language
(`en` for the approved `velnora` → `rel:likes` demo) is explicit authenticated
publication scope. It cannot be guessed from a surface or reconstructed from
VerifiedMeaning's grounding/coverage references, which do not contain those
payloads. The teaching utterance's language need not equal the designation's
language. Do not alter historical meaning or LP3 to manufacture that association.
Plain strings naming a reviewer or store do not authenticate either one.

The review verifier is privileged, store-scoped configuration and defaults to
absent. Its signed grant is the exact language authorization; no second language
allowlist or language role is introduced merely to validate that grant. Language
remains review/provenance metadata, not an extra designation application role.
One-use means the exact originating plan/publication journal can commit once;
changing a nonce cannot obtain a second commit. A separately signed review is a
distinct authorization, not forged merely because its explicit language differs.
The isolated SQLite demo binds the actual named database path and separately
configured signing key; memory requires an explicit trusted harness binding.
Neither dialogue nor a caller-supplied store label can install that authority.

### Authenticated alias-publication increment — September 8

The candidate publication path passed scoped specification and quality review,
including a second review after an actual transaction-port defect was repaired.
`R3EffectGateway.publish_learning` requires separately configured HMAC review,
binds the actual SQLite database or explicit trusted memory harness, and retains
the exact signed grant. Its distinct journal captures a fresh publication pin
without repinning the original answer. The existing commit transaction writes
one designation fact, resolves the original pending row and retains its canonical
completed record with the successful receipt. Session, episode and turn history
do not advance. Exact terminal retries return the same receipt, including after
reopen; incomplete retries cannot rebase onto changed state.

Review reproduced two internally consistent but unauthorized port substitutions:
a rehashed receipt naming another decision, and an observed designation naming
an unreviewed target. Both originally committed on memory and SQLite. Shared pure
builders now reconstruct the expected observation, fact and **complete** receipt
from retained proposal/LP3/review evidence. Existing transition/commit owners
compare that material before mutation, independently of live eligibility checks.
No new validation tier, semantic role, artifact ABI or authority source is added.

Main independently passed all **76 publication cases in 33.37 seconds**. Each
reviewer additionally passed 26 adversarial/retry/reopen controls after the fix;
the implementer passed 206 combined publication and existing owner tests.
The capability/permission negatives now test their specific rejected grant, not
an unrelated generation mismatch. SQLite rollback is exercised after actual
fact, obligation and journal writes; PLANNED, AUTHORIZED and OBSERVED recovery
are tested through real close/reopen. Four isolated post-VERIFY canaries retain
zero world delta; they are not the requested usable conversation demo.

The new indexed raw alias read is **conflict evidence only**. It must not be wired
directly into grounding or query as admission. The shared authenticated reader
and its snapshot/proof requirements above remain unimplemented. No existing
test body or unmapped successor assertion is removed or credited by this increment.
Final authenticated R3 replay: **2014 passed / 166 failed / 2180**, in 274.73
seconds. The exact failed-node set is unchanged: 163 unmapped successor assertions,
fresh-fragment clarification, authenticated-alias restart/reversal integration,
and dirty-input status. There is no new active R3 failure. Structure, 507 later
R3/R4 metadata records, legacy hard-cut audit (zero findings), compilation and
diff checks pass. The frozen inventory and all existing test bodies are unchanged.
Selectors/receipt regenerate twice byte-identically: G0 191 / R1 939 / R2 1329 /
R3 2180 / R4 2518 / R5 2643. Only the existing effect-learning owner gains 76
test nodes and one input path; gate definitions, dependencies and limits are
unchanged. Config SHA-256:
`aefa0629c868b30a62e68f3980f12af8f7e016533674418b0899885632e0d1f5`;
receipt SHA-256:
`5415d67b957edbe5518e3ea3a98c5f0e3470c7458665511dbd3a5cbd2a5dfd01`.
At local checkpoint `4c574be`, the clean-worktree status check passed in 4.23
seconds. The root checkout remained clean and nothing was pushed. This is not
Task 5 completion, a green R3 release, R4/R5 admission or root adoption.

### Admitted-designation reader increment — September 8

The candidate shared reader is implemented; consumer integration is not. It
merges exact static and admitted evidence before Unicode-folded lookup, retains
ambiguity and separates canonical designation identity from the actual committed
world fact. Historical publication, proposal, source-query and completed-obligation
evidence is reconstructed through the existing owners, without a signing key,
whole-world rebuild or new semantic ABI. Cache hits and misses require the same
revision-pinned read snapshot as bounded keyed proof reads. SQLite uses relevant
indexes; memory uses corresponding maintained indexes, with the duplicate raw
alias index removed. Memory facts now detach nested input/output mappings so a
caller's mutation cannot silently corrupt indexes without a revision change.

Specification review reproduced a model-coupling defect: reopening the same
published database with unchanged authority and a new proposer identity hid the
alias. Main independently reproduced it. The repair separates current read
identity from current publication eligibility while authenticating each original
historical witness. Main's initial new-reader run passed
**47 cases**. These include real signed Unicode/language-specific publication,
restart after expiry/phase change without a key, model-change reuse without
writes, corrupted lineage rejection, exact/fold ambiguity, snapshot/cache
currentness, structured-fact parity, bounded irrelevant-row growth and SQL index
plans. This is direct-owner evidence, not a completed conversation demo.

Quality review then exposed SQLite JSON1 coercion: structured object/array roles
could enter a text lookup and falsely exhaust its candidate budget, unlike
memory. Main independently reproduced the public-reader failure. Text-only
partial indexes and matching query predicates now exclude those rows before
retrieval bounds apply, including qualified language and raw publication-conflict
lookup. Four added controls pass in main's run: real textual JSON still works,
structured-row growth does not increase relevant traversal, and an existing
published store migrates its physical indexes once while preserving facts,
journals and revisions. Later reopening performs no designation-index DDL.
At this checkpoint the reader suite contained 51 cases; no semantic ABI or table
was added. The read-only connection control below brings the final total to 52.

A final contract audit removed an overconstraint introduced during the model
repair: source-query and answer turns may legitimately use different models.
The original publication owner accepted that correctly bound history. The new
positive control retains source A and answer B, publishes under current B, then
reads under current C without rewriting history or mutating on read. The live
answer/current check and exact historical publication-model checks remain.
The initial complete R3 run also exposed a genuine independent-read-only SQLite
activation failure: its connection lacked the Unicode function used by the new
index. Both connections now register the same type-safe deterministic SQL
primitive. The independent inspection remains read-only, preserves integrity and
schema checks, and closes its connection even on failure. The existing activation
test is unchanged. Main and both final reviewers independently passed six focused
model-lineage/read-only/reopen controls after these corrections.

Scoped specification and quality re-reviews pass. The existing publication
performance diagnostic had copied the retired untyped SQL; it now captures and
explains the actual raw-conflict query. Main's AST audit confirms only that test
function and its two later source hashes changed, preserving every original
assertion and the node/assertion identities. Corrected publication controls plus
the four new collision/migration cases pass in independent quality review (six
cases). Final authenticated R3 replay completed: **2066 passed / 166 failed /
2232**, in 362.30 seconds. The exact failed-node set is unchanged from publication:
163 unproved legacy successor assertions, fresh-fragment clarification,
authenticated-alias restart/reversal integration, and dirty-input status. The
valid SQLite activation regression is repaired; no new active R3 failure remains.
Structure, 507 later R3/R4 metadata records, legacy hard-cut audit (zero findings),
compilation and diff checks pass. Four fresh temporary-store post-VERIFY canaries
retain zero world delta; these are not the requested useful conversation demo.
Selectors and the receipt regenerated twice byte-identically: G0 191 / R1 939 /
R2 1329 / R3 2232 / R4 2570 / R5 2695. Only the existing effect-learning owner
gains 52 nodes and one test input; every existing node/input remains, and gate
definitions, owners, dependencies and limits are unchanged. Config SHA-256:
`1b7738160531babcf807c01d6c5530d5c063a11966c7b96b0701a14714ccab7c`;
receipt SHA-256:
`566175e0472b06e5f8a8b8f7ceef630aadd22ab214945608e3b50630d7c1b82a`.
The frozen inventory remains unchanged. Preliminary interrupted runs are not
completion evidence. No historical successor assertion is credited by this
increment. Next wire all three
consumers—grounding, designation composition and lexical query—through this
reader and prove actual restart/unseen composition. The early-ORIENT overflow
response limitation and remaining foundation tasks below are still open.

### Publication assertion consolidation — September 8

At reader checkpoint `f50e60c`, the clean-worktree status check passed in 3.95
seconds; both worktree and root were clean. Nothing was pushed. The checkpoint
leaves 165 substantive R3 failures, not a green release.

Four obsolete closeout wrappers are removed after main and independent audit
compared their original bodies at `6b8fc23^` with exact current publication tests.
Their frozen assertion identities now bind directly to the existing executable
publication cases through normal `supersedes_node_id` metadata. The publication
bodies, source AST hashes, activation phase, owner and introducing task are
unchanged. No extra runner, duplicate test execution, validator or gate is added.
The following newer duplicate labels are normalized to preserved frozen labels
(all entries have the `assertion:` prefix):

| Newer duplicate label | Preserved frozen label | Existing publication test suffix |
|---|---|---|
| `alias-publication-is-default-deny` | `learning-distinctions-designation-commit-requires-reviewer-authorization` | `is_default_deny` |
| `alias-publication-rechecks-current-eligibility-capability` | `learning-distinctions-designation-commit-requires-cap-learn` | `rechecks_current_eligibility[capability]` |
| `alias-publication-rechecks-current-eligibility-target` | `learning-distinctions-designation-commit-requires-existing-target` | `rechecks_current_eligibility[target]` |
| `alias-publication-signed-success-preserves-turn-and-lineage-memory` | `learning-distinctions-reviewed-alias-inherits-target-semantics` | `signed_success_preserves_turn_and_lineage[memory]` |

These are assertion-label consolidations, not retirement of semantic protections.
The last ancestor proved exact surface/target binding and store visibility, not
composition or affordance inheritance. That separate runtime integration remains
required. All additional assertions in the publication tests remain executable.
The four removed wrapper functions are `test_r3_successor_13d74d1095caaef5fe83`,
`test_r3_successor_9d8d009810b28f59c51a`, `test_r3_successor_5e719e6f426bdf86ff51`
and `test_r3_successor_a78a19b54d0b1f247a4c`, recoverable from `f50e60c`.
The other 159 unmapped wrappers remain unproved, not implicitly credited.
Final selection/lineage verification follows integration; historical inventory
and admission records remain immutable.

### Runtime designation integration — verified local checkpoint, review pending

The initial authentic publication/reopen contrasts reproduced three distinct
consumer failures: relation and bare-designation inputs had no selected meaning;
lexical lookup selected the query but returned UNKNOWN. The candidate wiring uses
one admitted reader, an explicit per-call batch shared by ORIENT grounding and
context construction, and a separately pinned lexical-query batch. It removes
the mutable-first index hook, without modifying authority or form-pack data.
Main has inspected the production and fixture changes; full regression evidence
is recorded below. Additional independent spec/quality reviewer dispatch was
attempted but rejected by the session's agent-thread limit. The implementer's
self-review is not an additional independent review. This limitation does not
justify a release/admission claim.

Three older composition-fixture functions (six cases) installed synthetic
designation/kind views into public ORIENT. They now exercise grounding, affordance
expansion, context construction, proposal/VERIFY and observation evaluation as
explicit static component fixtures. Exact membership graphs, nominal/state
polysemy, polarity, all kind-domain alternatives, four-state search, unchanged
packs/atoms and no world writes remain checked. Main reproduced six interface
failures before migration and passed all six afterward. These tests do not claim
authenticated acquisition; the separate real-publication integration must prove
that. Only their later source hashes change, not assertion identities or phases.

The old "new designation" grounding fixture used `progenitor`, which is already
seeded in `data/authority/conversation.json`. Its authentic successors must prove
an initial unknown surface (`nuvemora`) before signed publication to the same
existing `concept:mother` target. The original assertion names and independent
form-pack/authority invariants remain; no authority record is removed to fake an
unknown. This automated test fixture is separate from the approved demo-only
English `velnora` → `rel:likes` mapping.

Canonical inventory verification now selects all three authentic successors at
R2 and later phases. The three obsolete grounding bodies and their now-unused
`designation_store` fixture are removed; they remain recoverable from `f50e60c`.
All surviving grounding and R3-wrapper function ASTs are unchanged. The frozen
inventory and ledger are unchanged. Seven old bodies in total were removed,
including the four assertion-specific publication wrappers above.

Main's baseline-to-current authenticated selector audit passes all phases:
G0 191 and R1 939 are unchanged; R2 stays 1329 through three exact replacements;
R3 changes 2232 → 2246, R4 2570 → 2584 and R5 2695 → 2709 through 18 new
consumer cases, three replacements and four removed duplicate wrappers. All gate
topology and limits remain unchanged. Two sequential canonical regenerations
produce config SHA-256
`49b0ec2e40d4508c239d404c97599c513f4eb0c43e14effc8dd9385d65d84d95`
and receipt SHA-256
`4e3839a58cd22e8f7e1ab8bbd1ec787fb48ecc16e4fa31a06174f9bbd2f26fa9`
(final regeneration after the two additional fixture migrations below).
An initial canonical verification rejected missing literal parametrization IDs;
the test registrations were corrected, not the inventory parser.

Integration also exposed an over-specific performance measurement in the
structured-index diagnostic. Main independently measured total SQL work
1667/1707/1707 at 0/128/4096 added structured rows. Every one of the nine actual
designation queries had identical work (124 VM operations total); the difference
was fixed metadata work after the first world revision key was inserted. The
existing test now measures those nine retrieval statements, retains all empty
results and SEARCH/text-index/no-temporary-plan assertions, and still requires
nonincreasing retrieval work. Its corrected case passes; no runtime bound, index
guard or query validator was weakened.

Newly isolated remaining composition gap: after a real UNKNOWN result for
`What does luz nuvemora mean?`, `learn luz nuvemora means mother` grounds the
learning event and mother concept but leaves the two alias words and `means`
as unresolved designation units. PROPOSE explores 181 states without truncation
and returns `proposal:no_complete_candidate`; VERIFY abstains with zero candidate
receipts. No publication proposal or world write occurs. This is a remaining
multiword learning-content composition obligation, not a reader failure or reason
to raise search caps. Static multiword composition and single-word signed Unicode/
language-specific publication do not establish this missing public directive path.

Main also ran an independent diagnostic demonstration using the user's approved
English `velnora` → existing `rel:likes` mapping in a fresh temporary SQLite store.
The public unknown query produced UNKNOWN and a pending record; the public
learning directive produced a proposal without a world write. A separate signed
demo review committed exactly one fact. After closing/reopening the runtime,
`Bob velnora Alice.` produced independently expected subject Bob/object Alice;
`What does velnora mean?` was SUPPORTED; `VELNORA` preserved canonical literal
`velnora` and target `rel:likes`. World revision remained one. The store was
closed and removed, with no real authority mutation. All five cycles had no
realization surface, as the current R3 path still has no authorized realizer.
This is semantic learning/restart proof, not the usable conversation acceptance
demo or completion of the response/focus obligations.

The first full current R3 run produced 2083 passes/163 failures in 266.23 seconds.
Besides the expected 159 unmapped wrappers, fragment and dirty-status checks,
it exposed two later fixture-interface mismatches: the multi-unit static authority
stub lacked generation/content provenance, and the one-pass ORIENT counter did
not forward the explicit designation batch. Both were independently reproduced.
The static fixture now declares its provenance; the counter forwards the batch
and also checks its active pin. All existing assertions, identities and phases
remain unchanged. The two corrected cases pass (0.62 seconds).

The final authenticated R3 rerun produced **2085 passed / 161 failed / 2246**
in **192.89 seconds**. Exact failure-set comparison leaves 159 deliberately
unmapped historical wrappers, the fresh-fragment diagnostic, and the expected
dirty-worktree status check. The old seeded-alias restart failure is resolved;
there are no new failures against the reader checkpoint after the justified
assertion substitutions and fixture migrations. This remains a non-green
foundation checkpoint, not R3/R4/R5 admission. Four fresh-temporary post-VERIFY
canaries also retain their expected NoEffect outcomes and zero world revision
delta. Structural validation, all 503 records checked by the existing R3/R4
metadata script, the complete authenticated inventory, zero-finding legacy
hard-cut audit, source/script compilation and diff checks pass. The narrow
metadata script count is not the total test count. Root checkout and real
authority data remain untouched; no push, merge or corpus operation occurred.

Next-owner evidence, not a proposed bypass: a fresh `that you learn` trace has
empty focus/obligations, OBSERVE mode, an `event:learn_alias` frame requiring
actor/target/surface, five explored states without truncation, and no complete
candidate. It ends with a typed proposal gap and zero world writes before
EVALUATE. The current R3 terminal contract correctly requires selected
`VerifiedMeaning`. The clarification requirement remains valid, but do not invent
a successful meaning/evaluation merely to satisfy the diagnostic's phase shape.
Resolve incomplete-content representation and safe gap/response continuity at
their existing owners, including the early-ORIENT overflow representation issue.
The generic gap's `recommended_owner=training` is not root-cause evidence and
does not authorize R5 or justify increasing epochs/search bounds.

## Task 6 — Repair measured search/retrieval bounds and confirm preservation

### Approved diagnostic follow-through — naming-span owner first

The user directed implementation after the deeper diagnosis at `5bbe7a4`.
The immediate bounded repair unifies declaration and naming-directive label
geometry inside the existing ProposalContextBuilder. A definition marker owns
one contiguous label span and its adjacent naming-frame owner, if present.
Previously designated words inside that literal remain literal evidence; they
are not silently dropped. Structural punctuation/connectors/linkers delimit
unquoted spans. Quoted or structurally ambiguous labels must not be partly
learned; supporting them requires reviewed form evidence rather than core
quote-spelling rules. No broad concatenation of unknown words across clauses.

- [x] Add independent expression/geometry tests for multiword and known-word
  labels, declaration/directive parity, source whitespace/Unicode, clause
  isolation, quote fail-closed behavior and unseen naming-event synonyms.
- [x] Observe RED, replace the two inconsistent span collectors with one bounded
  structural source owner, and retain exact target/marker/role provenance.
- [x] Prove genuine signed publication/restart of a multiword alias; do not
  substitute mutable-index injection for acquisition.
- [x] Review, refresh later-test metadata/selectors using existing owners, and
  compare complete R3 failures against the known159 wrappers plus fragment.

September 8 naming-owner evidence: 48 new cases cover complete literal meaning,
declaration/directive mode, known noun/event mentions, Unicode/whitespace,
signed multiword publication/restart and unseen naming-event alias reuse.
Adversarial swaps retain each correct literal while exchanging grounded targets;
compiler, independent reconstruction and coverage reject them. Removing marker
evidence also denies targets rather than granting unrestricted compatibility.
All 27 existing context-builder cases remain passing. Independent spec and
quality review passed the scoped implementation after addressing their findings.

The source owner no longer fabricates naming literals from a markerless
cross-product. Generic punctuation is deliberately conservative: where an
opening quote cannot be distinguished from a sentence delimiter, a
punctuation-prefixed label is unsupported, not partially learned. The new clause
isolation test uses an unambiguous reviewed conjunction and two grounded targets;
it does not claim full punctuation/quotation support. No prior frozen assertion
was weakened to make this limitation pass.

Three occurrences of the same event exposed a separate silent truncation:
global per-target contribution accounting dropped a later predicate while
retaining its application frame. Builder and validator now agree on
target/source-occurrence contribution counts and designation-occurrence frame
counts. Four cached profiles per target, eight contributions per occurrence,
and all existing global bounds remain unchanged. The new same-occurrence bound
control and repeated-occurrence controls pass; this is not a search-cap increase.

The first full comparison, before review hardening/fixture migration, was
2094 passed / 192 failed out of 2286. Twenty-nine additional failures came from
semantic-only compiler fixtures lacking slot collections required by the exact
index. Seven helpers in six test files now expose their original slots and
explicitly unavailable character geometry; 64 focused cases pass, and all 47
test-function ASTs plus all six metadata ASTs are unchanged. Remaining initial
extra failures included metadata/selector changes during that run. This
intermediate run is superseded by the completed fresh comparison below.

Final authenticated R3 verification: **2133 passed / 161 failed / 2294 total**
in **202.22 seconds**. An exact failure-set check leaves only the same 159
unmapped historical assertion wrappers, the fresh-fragment clarification case,
and the dirty-governed-worktree status check. Relative to `5bbe7a4`, this is
exactly 48 additional passes and no new failures. The worktree-status check
remains pending until a clean local checkpoint; the other 160 failures are not
resolved by a commit. The 159 wrappers are unproved assertion mappings, not
evidence of 159 distinct runtime defects.

Independent final integration review passed 112 naming/fixture cases and all
27 context-builder cases. Main independently confirmed all 47 existing
test-function ASTs and six metadata ASTs unchanged. Existing structure and
metadata validation, the zero-finding hard-cut audit, source/script compilation
and diff checks pass. The metadata script validates its 503-record subset; it
does not represent the full regression count.

The all-phase baseline audit verifies unchanged G0/R1/R2 selections
(191/939/1329), and exactly 48 additions with no removals at R3/R4/R5
(2294/2632/2757). All gate topology and numeric limits are unchanged. Two
sequential canonical regenerations produced identical config SHA-256
`1fa771ae6a7098193cce4da0a3afe9cbb7b6e7aad682188042b4bc1d496d64f2`
and receipt SHA-256
`e43af5d83e77c925324e7c53bb3f3d5dc26d147e87de8ec28eb539b8d1a320e6`.
Frozen inventory SHA-256 remains
`7c27b0ad80998fc1f10876c05d0238a2498d2fd3a116ace77c9505da11d0b4b8`.

The approved isolated `velnora` -> `rel:likes` demo was rerun: unknown lookup,
public learning proposal with no write, independent signed demo approval,
exactly one committed fact, SQLite restart, correct Bob/Alice relation roles,
supported lexical lookup and canonical uppercase-alias reuse. Every public
cycle still has no authorized surface response. Four fresh-store post-VERIFY
mode canaries retain their expected NoEffect receipts and zero world delta.
These establish narrow semantic preservation, not usable conversation or
R4/R5 admission. The temporary demo store was removed; real authority data and
the root checkout remain unchanged. No push, merge or corpus operation occurred.

This does not close incomplete-fragment responses, response realization/focus,
complete multi-root settlement, occurrence/admission traversal or query
projection. Those remain the next approved owners below and in Tasks4–5, not
reasons to raise epochs, search caps, create new gates or reactivate R4/R5.

Source-ownership investigation precedes search deduplication. The current
`_situated_participant_references` can fill a reported event's omitted addressee
from the current conversation, inventing whom a goodbye addressed. Speech-actor
inheritance cannot apply to every proposition-taking event either: contrast
`Alice said goodbye`, `Alice said leave`, and `Alice said Bob left`. No global
actor copying or current-interlocutor default is acceptable for embedded content.

The bounded follow-up design is explicit reviewed parent/child-frame control
eligibility plus root-current-utterance-only situated-role binding. Generic form
geometry and clause-local mode supply evidence, not speech semantics. An explicit
child actor wins; unproved child mood or frame eligibility cannot authorize a
copy. Reported farewell addressee must remain unspecified, while a standalone
farewell retains its actual conversational participants. The candidate repair
needs the optional reported addressee signature and root-only speech-act binding
together, not an optional-role change alone. These are pending semantic-source
changes, not part of the six-frame preservation checkpoint. Extend the existing
frame owner explicitly if required; do not create one owner/schema per phrase.
Any control slot/context migration must expose its exact parent, child, role,
authority and evidence references to independent VERIFY reconstruction, rather
than hiding scope in provenance tuple positions. Keep this dependency explicit
before reducing search duplication or claiming the two-sentence demo is faithful.

September 9 implementation checkpoint: exact punctuation-clause and report
content geometry now scopes every source-bound reference to actual frame
identities. Embedded children receive no current situated participant. Explicit
child actors win; a reviewed communicative child may inherit the exact reporting
actor, while `Alice said leave` remains unsupported. Greeting and farewell have
optional addressees, so reported forms omit an unspoken addressee and standalone
forms still receive user/system participants. Content-local negation cannot scope
the report, and an earlier sentence root cannot become its content. Compiler,
composer, verifier and independent reconstruction enforce the boundary; forged
content, scope, reference and control cases fail. Fifteen focused and 156 main-
rerun surrounding cases pass, with no ABI, gate, cap, service or owner added.

The exact two-root graph for `The server is offline. You said goodbye.` now
exists and compiles with correct state, report, farewell, roles and roots. Public
selection remains honestly rejected because the unchanged search bounds stop at
48 candidates / 768 states. The R4 expected-contract compiler also invented a
current-system greeting addressee that is absent from reviewed scenario 0079.
That default was removed; the existing authentic comparison now passes with
exact speaker control and no unsupported child role. The remaining multi-root
limitation must not be hidden by weakening source ownership or raising caps.

- [x] Reproduce program/meaning duplication with the audit's multi-root and
  conditional examples; canonicalize equivalent search states only when future
  legal continuations, scope and evidence ownership are preserved.

  September 9 independent closure: the public two-sentence report now explores
  114 unique states without truncation, emits one program and one canonical
  two-root expression, and reaches selected VERIFY. Replaying its context with
  the retired action-history key exhausts 768 states and produces 80 complete
  programs which all compile to that same expression. The semantic-state key
  skips 62 equivalent histories before budget accounting. A conditional control
  retains eight distinct expressions and remains ambiguous, proving that the
  key does not collapse genuine future continuations. The full public cycle is
  six-phase and stops only at the intentionally unadmitted R5 realization owner.
  Fifty-one focused composer, reported-speech, compiler, proposer and independent
  reconstruction cases pass; no ABI, cap, gate or owner changed.
- [x] Replace relevant whole-store query reads with indexed predicates/arguments
  and revision-pinned retrieval. Test behavior with increasing irrelevant facts.

  Before the repair, deeper independent query-owner probes reproduced correctness blockers as well
  as scan cost: 256 preceding irrelevant facts hide a true match; truncation can
  hide denial after support; a seven-rule chain silently returns UNKNOWN after
  six rounds; reported-only premises can derive unscoped support; a revision-0
  situation can read revision-1 facts and report support at its old pin. These
  probes used isolated in-memory stores; 15 existing query controls still passed.
  Those controls alone were not proof that the gaps were repaired.

  The next repair must cover pinned reads, truthful incomplete-result handling
  (including existing support that might have unseen opposition), and placement
  preservation before claiming indexed query correctness. Reuse the existing
  read snapshot and query/proof owners. Backward-close reviewed rule-head
  dependencies, retain all conjunctive antecedents and intermediate entities,
  then load bounded predicate/argument evidence and transitive persisted proof
  premises. Missing/cyclic/overflowing proof dependencies fail closed. Physical
  indexes belong to existing persistence and every atomic upsert/replacement;
  they are not a second store or semantic ABI. Keep lexical lookup and the
  separately shared state-precondition reader intact. Do not turn every partial
  result into a decisive supported/unknown answer or broaden currently
  unsupported scoped/proposition query semantics while optimizing retrieval.

  September 8 implementation checkpoint: QUERY now opens one exact
  `r3_read_snapshot`, retrieves through atomically maintained memory/SQLite
  predicate and argument postings, backward-closes reviewed rule dependencies,
  preserves premise placement and reviewed rule-source provenance, and loads
  transitive proof premises by key. Support, opposition, relevant-rule overflow,
  join overflow, six-round nonconvergence, missing/cyclic/malformed persisted
  proof and saturated postings all fail closed. Memory, SQLite and restart cases
  measure decoded rows and SQLite work with 10 versus 2,000 distractors. The
  final combined query/budget/public-cycle regression is 98 passes; the exact
  `decision-query-proof` owner gate also passes its 175 selected nodes. No
  semantic ABI, owner, tier or numeric limit changed. Two frozen tests with
  obsolete fabricated pins now have full-assertion, same-identity successors
  using the actual store pin. Twelve audited historical query/inference wrappers
  now have exact current-ABI successors rather than category smoke mappings.

  Independent quality review found one additional generation-lineage defect:
  the predecessor generic-acquisition coordinator could mutate the live rule
  dictionary while QUERY retained a parent-generation store pin.
  `LinkedAuthority.rules` is now immutable within one generation and QUERY
  rejects generation drift before evidence reads. The predecessor publisher is
  explicitly unavailable; future generic acquisition requires complete bundle
  linking plus fresh authority/store activation. Static fresh-generation query
  activation, stale rejection and in-place mutation denial are tested without
  claiming that unresolved publisher exists. This adds no per-query scan.

  Final integrity hardening closes three defects found after that green gate.
  Rule clauses are now recursively immutable and expose an explicit JSON-safe
  wire projection; the generation-keyed rule-head index is built at owner
  activation, so the first ordinary query does not scan all rules. Persisted
  derived-proof sources are reconstructed exactly from the reviewed rule and
  validated parents, discarding forged persisted source claims. World facts
  with any stance other than exact `support` or `deny` fail closed as
  `BUDGET_EXHAUSTED`. Eight memory/SQLite reproductions moved RED to GREEN; the
  combined query/budget/public suite passes 104 cases and the expanded
  query/authority/learning suite passes 149. Source inventory authentication
  reports 2,380 active R3 nodes and 2,994 collectable nodes. Generated selectors,
  the living receipt and exact owner gate remain to be refreshed after the
  source-ownership slice, avoiding redundant generated-artifact churn.

  A second independent adversarial review then found two same-generation escape
  paths: callers could replace the complete public rule mapping without changing
  authority identity, and a malformed reviewed-rule stance could be derived
  directly as opposition. `LinkedAuthority` now exposes read-only generation,
  content and rule views backed by one atomic snapshot. `RuleRecord` construction
  and defensive query clause parsing admit only exact `support` or `deny`.

  Final re-review found a TOCTOU gap between the initial authority pin check and
  a later cache refresh. QUERY now captures one immutable authority state, uses
  one immutable cache bundle and passes evaluation-local rule/index maps through
  retrieval and proof validation. The common cache hit is lock-free O(1); only
  activation/generation misses build under a lock. Mid-cycle identity change
  fails before return. Main independently reran 164 query/authority cases and
  ten predecessor-learning/boundary cases successfully. The predecessor generic
  acquisition commit path now fails before lowering or mutation because it has
  no atomic store-reactivation owner. Generated selectors and the living receipt
  remain stale until this source-ownership tranche is complete.
- [x] Keep configured caps and truncation honesty; measure real work, preserve
  denied-effect and authority boundaries, run multilingual/unseen-synonym tests.
  The existing `BudgetExhausted` classifier does not establish runtime handling:
  `HybridRuntime.process_evidence` and CLI callers currently propagate ORIENT
  exceptions. Repair the existing early-failure/finalization owner when routing
  bounded lookup overflow. A typed exception is fail-closed but is not a completed
  CycleResult or usable budget response; never silently keep the first eight
  alternatives or report overflow as an unknown meaning.
  The existing R3 CycleResult validator also requires ORIENT, PROPOSE and VERIFY
  artifacts and exactly three or six phase records. An ORIENT exception cannot
  be caught and passed to it with missing artifacts. Repair that earliest-failure
  representation explicitly, preserving strict lineage and ABI ownership; never
  invent a successful orientation/proposal/verification to satisfy the validator.

  September 9 ORIENT-budget checkpoint: Cycle Result ABI 4 adds one exact
  single-phase terminal for a witnessed `BudgetExhausted` during ORIENT. It
  binds the original EvidencePacket and performance GapReceipt to an unchanged
  attempted revision pin, records the exact budget name/limit, invokes no later
  owner and advances no session state. Other exceptions still propagate. ABI 3
  is a hard-cut predecessor; no compatibility decoder, search-cap increase,
  fallback designation, synthetic semantic artifact, gate or service was added.

  The ABI-4 successor is now routed by the existing R3 phase selector; the
  frozen ABI-3 predecessor is no longer active. Canonical selector and living
  G0-receipt regeneration was byte-identical across two runs (config SHA-256
  `803bc4e63f5a27e4071b724ff9e7e8e0db7e18b96fe41cd539df6a65747c7e2f`,
  receipt SHA-256
  `8be66b76fa494789650c2ea28d2aebb714b9ec089423f81c18d318468a9f786c`).
  G0 remains exactly 191 active nodes; R3 has 2,431 active nodes, with 203 in
  the exact phase group. This refresh changes selector membership and living
  evidence only; it does not add a gate or alter gate topology. A fresh direct
  run of that 203-node phase group reports 92 passes and 111 failures; every
  remaining failure is an explicit still-unmapped historical assertion wrapper,
  not an ABI-4 runtime regression.

  Final preservation evidence covers signed Unicode and multilingual alias
  publication/reopen, prior-generation rejection, permitted and denied operation
  receipts, reviewed-alias restart plus unseen reversal, and the exact multi-root
  report. All seven cases pass. Together with the measured memory/SQLite query
  growth tests and the no-truncation multi-root/conditional audit, this closes
  the configured-bound preservation item without raising a cap or adding a gate.
- [x] Regenerate changed deterministic artifacts twice; require byte identity
  and preservation of every previously authorized realization contract.

  After the query-lineage and generation-boundary successors, the existing
  selector config and living inventory receipt were reconstructed twice
  byte-identically (`ff43c393...e44` and `f2cc4a77...05a3`). The immutable
  inventory and replay ledgers were not changed. This increment changes no form,
  realization or model artifact, so it removes no authorized response surface.

  The resulting R3 phase selection contains 200 exact nodes: 54 pass and the
  remaining 146 failures are all still-unmapped historical wrapper assertions.
  The earlier fragment failure is no longer in this phase failure set. This is a
  sharper migration backlog, not evidence of 146 runtime defects and not license
  to map wrappers to unrelated smoke tests.

### Exact R4 boundary diagnosis — September 9

The definition blocker was traced one owner deeper before adding production
data. Description ABI 1 now has a strict transient codec candidate: its request
requires the current R3 `QueryResult` identity namespace and binds the semantic
target, complete answer-graph depth, persistent-fact budget and revision pin. Its
result carries canonical `SemanticExpression` meaning, requires persistent
`fact:` evidence refs rather than expression-local node refs, and rejects
unresolved answers or answers
where the requested target occurs only as a predicate, class, dimension, value,
label type or scope. Claim/source/proof/definition refs remain generic bounded
refs at this codec boundary. The pending indexed Stage-10 builder must verify
every external ref's existence, type, lineage and exact semantic correspondence
to the answer. This is not yet Stage-10 integration or activation.

An initial implementation of a persistent `ReviewedDescriptionGraph` registry
was rejected during independent review and removed. It accepted unlinked lineage
strings and would have created a second semantic authority plane beside the
existing application/claim store. The governing path remains: reviewed definition
applications and claims are published through the existing semantic store, then
Description ABI reads their bounded indexed neighbourhood through the existing
QUERY owner. No new gate, capability, permission, persistent table, authority
default or search-cap increase was added. Production definition facts, indexed
neighbourhood retrieval, query projection/dispatch, Proof Bundle linkage and R5
realization remain explicit pending work; the three metadata-only `defines` rows
therefore continue to fail closed.

The current `r4_phase_tests` selector contains 35 nodes. A fresh exact run after
the foundation repairs reports **32 passes / 3 failures**. One earlier fourth
failure was a stale August 14 wording assertion: its same node and assertion now
validate the exact predecessor and approved-R4.1-target rows in the current ABI
registry instead of requiring superseded prose. Its AST metadata was refreshed
without changing assertion identity, phase or owner.

The three remaining failures are intentional, unsatisfied rewrite obligations
over `artifacts/r4/episodes.jsonl`. That 400-row August 12 artifact contains
Semantic Expression ABI 1, Cycle Result ABI 3, Response Meaning ABI 2 and Effect
Receipt ABI 1 records. Active decoders correctly reject it. Do not add a legacy
decoder, regenerate the predecessor corpus, remove these nodes or call the R4
phase green. R4.1 Tasks 14–15 must first add exact same-assertion successors over
R4 Supervised Case ABI 1, legal Cycle Result ABI 4 terminal shapes and R4 Build
Receipt ABI 5 provenance; only then may the predecessor tests be superseded.

The earliest source-compilation blocker is separate and equally real. Of 210
reviewed scenarios, 207 expand into 394 cases; three metadata-only `defines`
rows (`designation_definition-0006`, `designation_definition-0010` and
`realization_equivalence-0208`) stop with
`definition_requires_semantic_content`. The stale predecessor corpus encoded
their six surfaces as false registry-kind type claims. Preserve the rejection.
Fresh R4.1 supervision requires actual reviewed definition graphs, or an explicit
typed gap until the active Stage-10 Description ABI is implemented and proved.

### Normalized semantic-application substrate checkpoint — September 9

The deeper storage audit found the earliest remaining Stage-10 blocker below
Description ABI itself. The hybrid store currently persists a flat
`Fact(operator, args, stance, proof)` projection. That projection cannot retain
the distinction between a grounded semantic reference and an equal-spelling
literal, role versus qualifier ownership, an application-valued child edge,
multiple independent claims over one application, or exact
occurrence/source/proof/commit lineage. Building Description on that projection
would certify reconstructed text-shaped data as canonical meaning and repeat the
program/meaning category error.

`SemanticExpression` node refs are also expression-local composition addresses
(`application:0`, and so on), not persistent semantic identities. Description
must not require its persistent evidence refs to equal those local addresses.
The Stage-10 builder must instead reconstruct canonical answer meaning from
content-addressed stored applications and verify an exact local-node-to-stored-
application correspondence inside one pinned read. Until that correspondence is
implemented, the transient codec may bound and authenticate the two collections
but must not claim their identities are interchangeable.

The next implementation checkpoint is deliberately below public definition
publication:

- [x] Add the existing conceptual application/binding/claim substrate to both
  memory and SQLite persistence with content-addressed applications, explicit
  role/qualifier rows, exact grounded/literal/application filler kinds,
  independent active claims and append-only retraction lineage.
- [x] Persist children first and reject variables, unresolved fillers, dangling
  children and cycles. Reconstruct the same canonical meaning after SQLite
  restart; never infer normalized rows from legacy `world_facts`, because filler
  typing has already been lost there.
- [x] Add bounded target and application-claim reads through the existing
  `SemanticStores`/`R3StorePort` owner and caller-held `r3_read_snapshot`.
  Every posting, claim and child traversal uses max-plus-one overflow detection;
  no whole-store scan or new Description service/gate is permitted.
- [x] Route only the already authenticated alias publication through the private
  normalized preparation path while retaining its current `world_facts`
  projection for unchanged R3 consumers. Prove one normalized designation and
  claim, unchanged effect atomicity, restart reuse and no duplicate publication.
- [x] Keep generic definition publication unavailable. Existing
  `ReviewerAuthorization`, `ReviewedAcquisitionPlan`, alias grants and R4 class
  authorization do not authorize arbitrary semantic graph writes. A later
  publication artifact must bind exact graph bytes, target, reviewer signature,
  store, parent/new linked authority generations, compatibility hash, revision
  pin and the one effect transaction; no public raw application writer is
  allowed.
- [x] Implement the discrete read-only Stage-10 builder through the existing
  `QueryDecisionOwner`: it reconstructs only a bounded, indexed, pin-matched
  normalized-claim description after exact fact projection and generic lineage
  verification. It has no public routing, authority mutation, generic writer or
  realization behavior. Independent spec and quality review passed; the focused
  Description ABI/normalized-store run passed 98 cases.
- [ ] Implement Proof Bundle linkage, query/decision projection and exact R5
  realization in that order. Only an authenticated full-bundle publication may
  add production definitions for CEMM, mother or job.

This is an additive generic persistence repair, not a Description table, new
semantic operator, capability, service, search-cap increase or R4 admission.
Legacy `world_facts` remains a temporary execution projection until its callers
are migrated; it is never a source for reconstructing normalized meaning.

Checkpoint evidence: the governed normalized-store module has 54 passing cases
covering canonical identity, typed bindings, graph integrity, exact lineage,
atomic alias dual-write, restart/tamper handling, retraction, backend parity and
bounded indexed reads. The wider alias-authority/publication/admission/query/
recovery boundary has 401 passing cases. Independent adversarial review rebuilt
malformed schemas with wrong types and missing `CHECK`, `NOT NULL` and
`WITHOUT ROWID` constraints; activation rejected each before mutation. A
30-claim workload sharing one six-application closure required 15 SQLite
`SELECT`s, below the governed bound of 20 and independent of claim count. The
schema verification runs only at activation, and no public generic application
writer exists. R3 source-only inventory validation includes all 54 new cases.

## Task 7 — Handoff to R4/R5 only on evidence

### Bounded execution checkpoint — October 1

The approved competition-readiness repair follows the existing foundation route,
not a new master plan. Close one earliest-owner defect at a time; a component
pass is not a public conversation pass. Do not repeat completed substrate work,
reopen routine approvals, raise limits, train around missing representations or
enable the historical marker-only realizer. After three unsuccessful hypotheses
for one defect, record the exact blocking representation decision rather than
adding another fallback.

- [x] Link description evidence through Proof Bundle ABI 1 in the existing
  query owner. One pinned, bounded read must retain each exact application,
  claim, signed stance, fact, occurrence, source, decision, placement, proof and
  commit transaction; bind the source QueryResult, description and answer
  expression. Preserve denial-only evidence and same-application conflict
  without treating the neutral description graph as positive world truth.
  Canonical codecs are structural validation, not publication authority.
  Prove memory/SQLite parity, restart, tamper and stale-pin rejection, lossless
  budget terminals, no world mutation and indexed work bounded by current
  description limits. No public dispatch, generic writer or release realization
  activation belongs to this checkpoint.
  October 1 evidence: independent spec and quality reviews passed; 187 focused
  proof/builder/codec/normalized-store/authority cases passed. The 79 new proof
  cases include exact nested wire types, denial/conflict, maximum 64-claim and
  4,096-proof-occurrence serialization, and one SQLite target read (nine SELECTs
  for one claim with either zero or 200 unrelated claims). No public routing,
  production definition, world writer or phase admission is claimed.
- [x] Reproduce the public definition/nominal-question contrast individually;
  distinguish missing form/frame/answer projection from missing reviewed facts.
  Record the earliest owner before selecting its repair; neither registry kind
  nor metadata-only `definition_targets` is a definition.
- [x] Repair only subject-person membership query source consumption. The
  public `who is a mother?` path has the correct designation, type frame and
  instance variable, but QUERY bypasses `_nominal_predication_evidence`, leaving
  its copula/determiner unconsumed (zero candidates, four states). The same
  declarative selects correctly. Reusing the helper with exact clause-local
  person-interrogative evidence yields one independently verified membership
  candidate without changing limits. Prove this through public tests, preserve
  negation, feature-equivalent language evidence and unseen synonym affordances,
  and keep content-interrogative descriptions and unlicensed question inversion
  separate. A person cue in another clause must not authorize this extension.
  October 1 evidence: 17 new independent controls and all 175 prior owner cases
  passed; the refreshed exact owner union passed 192 cases. Spec and quality
  reviews passed. Positive queries have one candidate/four states. The negative
  subject-question remains explicitly unsupported: scope expansion requires a
  direct nominal root after missing-role completion, but variable projection has
  already wrapped that root. Preserve its critical polarity and fail closed;
  this source-consumption repair does not establish scoped-query composition.
- [x] Repair relation-query role ownership before counting verified queries as
  useful answers. The initial public `who likes Bob?` RED probe
  verified `likes(Bob, ?v0)` instead of `likes(?v0, Bob)`. The former role-order
  matcher considered grounded designations but omitted the interrogative position;
  its broad query-feature schemas could assign the remaining entity to subject.
  Match complete typed construction evidence and independently preserve the
  requested variable role. Do not patch this sentence or count graph validity as
  intended-meaning correspondence. This defect is distinct from missing
  definition projection and must retain an explicit RED until repaired.
  The bounded repair uses one immutable activation-pinned reviewed role-schema
  index shared by construction, coverage, compilation and independent VERIFY.
  Match complete clause-local typed person-query/predicate/referent evidence,
  retain exact frame-local variable/reference ownership, and rematch against that
  trusted index rather than treating candidate witness hashes as authority.
  Leading-subject and trailing-object relation questions are the first scope;
  auxiliaries, unlicensed scope and mixed-clause forms remain critical blockers.
  October 1 evidence: 102 independent relation controls passed, including
  asymmetric facts, EN/ES role contrasts, unchanged-pack authorized alias reuse
  after restart, canonical-rehashed forgeries at every exact sink, complete
  polysemy sets and typed attempt/match exhaustion. Independent spec and quality
  reviews passed. Their overlap probes exposed missing participant/deixis
  ownership: form contributions and the activated index now share the original
  primitive signature and identity owner. Both resolved and unresolved reference
  requirements survive exact designation overlap; no default referent is made.
  Standalone unresolved references retain their original critical residual and
  unchanged assertion. Alternative linker/determiner readings are not made
  globally mandatory references. Current relation schemas have no reviewed
  lexical-overlap license; scoped rejection does not ban designation or lookup.
  Independent two-predicate by two-referent probes retain four distinct meanings
  and honest ambiguity. Positive unambiguous public role contrasts use at most
  seven search states; numeric limits and authority generation are unchanged.
  Fresh parent integration: 318 exact composition/reference-owner cases, 187
  description/proof cases and 76 query/release-boundary cases passed in separate
  bounded runs. These are not an aggregate release or replay-admission result.
- [ ] Project authenticated answer meaning through the query/decision/response
  owners, then prove the explicitly development-only compositional response
  reference through the public runtime. Preserve the R5 release boundary.
  Preserve an explicit requested description projection and its source-query
  lineage. A type-membership graph, registry kind or manufactured QueryResult
  cannot substitute for a definition request. The current response owner checks
  the decision answer against exact query bindings; do not replace that answer
  with an arbitrary description graph merely to obtain readable output. Missing
  reviewed definition content remains distinct from missing projection support.
  October 1 case-by-case follow-up: isolated public probes confirm that
  `What is CEMM?`, `What is a mother?` and `Define mother.` produce no verified
  descriptive request. Membership and lexical lookup have distinct working
  graphs. For lookup, QueryStatus SUPPORTED / Decision ANSWER can coexist with
  CycleStatus PARTIAL while R5 realization is unavailable; do not report the
  cycle status as failed semantic lookup.

  The independently reproduced builder defect is repaired: a valid normalized
  `Alice`-instance / `mother`-class claim appears in mother's target posting, but
  its class occurrence is metadata, not a description of mother. Before repair,
  the builder raised its target-focus validator instead of returning MISSING,
  and irrelevant support/deny postings could contaminate a focused answer with
  false conflict. It now authenticates every bounded posting before reusing the
  operator-aware nonmetadata focus criterion for answer assembly. The 10 new
  memory/SQLite controls were RED (four failures) before repair and GREEN after;
  the fresh parent six-module union passes 197 cases. Independent spec review
  passes 286 adjacent cases; independent quality review passes the same 197-case
  six-module union. Corruption,
  stale pins, signed/nested evidence and raw posting overflow remain enforced.
  No extra read, cap, ABI or authority change is introduced. This filter repair
  is not definition support.

  Representation decision approved by the user on October 1: the predecessor canonical
  binder has only a variable and body, and canonical expressions require at least
  one application. No existing reviewed description/definition/location frame
  supplies the missing request. A public description therefore needs an explicit
  identity-bearing canonical query projection, not a dummy persistent statement,
  new `op:describe`, `rel:description` or reified definition store. Keep ordinary
  role/binder questions unchanged. The approved migration is specified in section
  8 of the foundation amendment and the finite sequence below; compiler, independent VERIFY, source
  coverage and request/answer identity must agree before public activation.

  The retired Description/Proof Bundle ABI 1 component bound a canonical
  UNKNOWN source QueryResult without establishing that QUERY produced it.
  A manufactured UNKNOWN for a supported proposition could satisfy that seam.
  ABI 2 now rejects that seam and binds the canonical request/projection and
  original QUERY situation before the pinned read. The existing query owner
  still needs genuine final result ownership after answer/proof construction;
  public dispatch must not manufacture an UNKNOWN or add a second query engine. Generic
  neighbourhood reconstruction and its SUFFICIENT flag do not prove an
  intensional definition; actual production definition content remains missing.
- [ ] Close the existing foundation conversation matrix, then unblock fresh
  R4.1 supervision and the conditional R5/R6 work using their existing contracts.

Competition rules, benchmark comparisons and submission packaging are separate
from foundation correctness. No competition result, R4/R5 admission, root
adoption, merge or push is implied by this execution checkpoint.

### Task 7 approved projection migration sequence — October 1

This is the next increment of this plan, not a competing plan or another corpus
pass. User approval covers the canonical request/proof-lineage representation;
review each bounded implementation task spec-first and quality-second. Preserve
all pre-existing dirty edits. Do not commit, push or admit a phase implicitly.

- [x] **7.1 Canonical request substrate.** Owners:
  `src/cemm_authoritative_hybrid/expressions.py`, `expression_projection.py`,
  exact preservation/rejection in `expression_transform.py`, `proof_bundle.py`
  and `r3_learning.py` if required; tests:
  `tests/test_foundation_query_projection.py`. Add `QueryProjection` under
  Semantic Expression ABI 3, with exactly these fields:

  ```python
  QueryProjection(
      projection_ref="candidate:query",
      requested_content="description",
      target_ref="participant:system",
  )
  ```

  The intended request-only expression is:

  ```python
  SemanticExpression.create(
      applications=(),
      root_refs=("candidate:query",),
      query_projections=(request_node,),
  )
  ```

  Write independent tests first and observe the missing-node assertion RED.
  Prove local-ref alpha equivalence, target/content non-equivalence, zero
  persistent applications, unchanged five operators, exact canonical wire and
  hard-cut ABI 2 rejection. Empty, multiple, duplicate, dangling, unreachable,
  excessive-depth and total-node cases reject. Immutable structural indexes
  expose the exact target; generic transformations preserve the node or explicitly
  reject unsupported use, never silently erase it. Run new and existing codec /
  expression-projection tests with:

  ```powershell
  $env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
  $env:PYTHONDONTWRITEBYTECODE='1'
  $env:PYTHONPATH='src'
  & C:/Python313/python.exe -m pytest -o addopts= -p no:cacheprovider tests/test_foundation_query_projection.py tests/test_semantic_expressions.py tests/test_r3_expression_projection.py -q
  ```

  The two prior modules exist; do not migrate frozen assertions. Compiler/public interpretation
  and descriptive evaluation remain unavailable at this substrate checkpoint.
  Observed evidence: initial 12 missing-node assertion failures, followed by
  passing controls. Independent review reproduced wire aliasing in nested scope
  and binder nodes; two further RED controls preceded detached-field serialization
  repairs. All 17 new request cases pass. The fresh parent seven-module union
  passes 157 cases, including existing codec/compiler/projection/mode and signed
  description-proof controls. Spec review passes 46 codec/projection cases and
  its independent binder-to-scope-to-request mutation probe. Fresh quality review
  passes 172 focused cases with no actionable finding. No public compiler,
  evaluation, definition policy, authority, world writer or normal realization
  was activated. Existing numeric bounds are unchanged. The one nonfrozen ABI
  expectation now checks ABI 3 and rejects ABI 1/2; its literal AST metadata was
  refreshed, not any frozen assertion or inventory anchor.
- [ ] **7.2 Exact construction and verification.** Existing owners:
  `proposal_context.py`, `programs.py`, `recursive_composer/`,
  `recursive_compiler.py`, `coverage.py`, `verifier_reconstruction.py`,
  `verifier.py` and their deterministic reviewed form/schema owners. Extend a
  structural projection derivation through the existing twelve switch-action
  families rather than adding a persistent operator or phrase intent. Pin any
  changed action/context/coverage ABI and reject predecessors. Independently
  prove exact target and requested-content reconstruction, complete source
  ownership, EN/ES typed evidence contrasts, unchanged-pack unseen synonym
  reuse, competing interpretations and rehashed forgeries at every exact sink.
  Do not reinstate the retired atom-kind or surface-only `define` cue. Keep
  unreviewed construction forms critical and public request dispatch disabled
  until the complete owner chain agrees.
  Read-only October 1 construction audit identifies the earliest missing owner:
  reviewed request-content authority. EN content-interrogative evidence and ES
  generic query evidence do not establish description versus definition. The
  old `definition_nominal_query` / `definition_participant_query` pack rows lack
  `evidence_order` and are skipped by activated role schemas; their names are
  not semantics. Body-bound VariableSlot and the minimum-application guards also
  cannot represent the new leaf. The recommended bounded extension is a distinct
  content-addressed QueryProjectionSlot, licensed by an explicit result variant
  of the existing activated typed schema index, and a two-argument
  `project_variable(projection_local_ref, query_projection_slot_ref)` variant.
  Preserve the three-argument binder variant and all twelve action families.
  Source geometry, selected designation alternative and requested content must
  be independently rematched, not accepted because slot hashes agree. Bare
  `What is X?` readings must not be selected from target kind or available facts;
  preserve competing reviewed readings unless legitimate context resolves them.
  `Define mother` remains unresolved without reviewed open-class request meaning
  and an inheritable affordance; restoring the retired cue is not a repair.
  Future pack/action changes must reconcile schema ABI/hash pins and give the
  predecessor pack-hash containment assertion an honest preservation successor,
  never a blind hash refresh or frozen-data rewrite. This audit activates nothing.
  Execute this dependency in two bounded, independently reviewed components:
  - [x] **7.2a Private construction substrate.** Extend the activated schema
    index with an explicit query-projection result variant and closed transient
    request/binder/optional-determiner/target ports, not new semantic roles.
    Preserve persistent-role schemas. Add distinct content-addressed projection
    matches and QueryProjectionSlot records plus strict Proposal Context ABI 3
    serialization and immutable indexes. Use explicitly licensed in-memory
    candidate packs for acceptance; checked-in request rows and public emission
    stay disabled. Unknown, deictic, scoped and compound targets are not
    implicitly licensed. Count every alternative under existing bounds.
    Optional article consumption requires explicit typed article evidence;
    generic determiner metadata also covers quantification and cannot license
    dropping `all` or `every` from canonical request content.
    October 1 closeout: 67 construction cases and 289 adjacent owner controls
    pass in main's fresh 356-case run. Independent SPEC and QUALITY reviews pass.
    Review exposed and drove test-first repairs for optional-article binding
    subclasses and mutable projection-container subclasses; both constructors
    reject before hashing/indexing. The unsupported decoder-only scalar cap was
    removed without adding a validation layer or changing configured bounds.
    Detached roundtrips, strict JSON/alias/cycle/collection protections and
    activated-match rejection remain. Source-only R4 inventory passes. EN/ES
    packs and frozen inventory/anchors/ledger are unchanged. Public projection
    emission, Program/Coverage derivation, learned capability and admission are
    not claimed by this private component.
    Existing selector and living inventory receipt regeneration is byte-identical
    across two runs: R4 has 3,414 active / 3,671 collectable nodes in 168 modules,
    active set `active_test_nodes:1d54eca149c793840a83405e` and literal metadata
    `literal_test_metadata:557bd9e369614a7e32c7f78d`. Admission roots and configured
    limits are unchanged. Five fresh scoped governance/document/anchor checks
    pass; this is source registration and documentation evidence, not admission.
  - [x] **7.2b Exact derivation and candidate source integration.** Hard-cut
    Program and Coverage to ABI 3, retain all twelve action families and the
    three-argument binder variant, and add the two-argument projection variant
    with exact non-role source ownership. Close composition, compilation,
    independent reconstruction and all verification/proof sinks before enabling
    candidate source rows. A generic content/copula row licenses description and
    definition as separate equal-priority readings; no current context policy
    chooses between them. Candidate ES content-interrogative metadata, preserved
    unrelated pack fields, honest same-assertion successors and dependent R4
    schema/action pins must agree. Direct participant deixis needs its own exact
    resolved-reference selector; do not invent a designation. Definition requests
    still require reviewed content/policy to be answered. No publication,
    learned realization, root adoption or phase admission follows from this.
    October 1 closeout: final parent replay passes 515 cases in seven bounded
    owner modules. Independent SPEC passes 360 cases; final QUALITY passes three
    focused runs of 246, 381 and 19 cases. These overlapping runs are not a full
    regression or admission claim. Review exposed primitive/anchor port and
    provenance substitution plus equality-based activation-owner substitution;
    test-first repairs now authenticate complete contributions against the actual
    activated LinkedAuthority, RuntimeConfig and cached affordance view. Normal
    rematches use keyed reads, not an authority scan or per-match cache rebuild.
    Original EN/ES unseen nominal aliases retain their expected type graph.
    Source fixtures now keep designation proxies at Grounder only; composition
    consumes the actual linked owner. Honest same-assertion ABI, membership and
    pack-preservation successors retain frozen evidence. Removing public content
    construction fails both independent required-content cases; the other three
    unsupported controls remain unsupported. Frozen inventory, assertion anchors
    and replay ledger are unchanged. Candidate rows are enabled; equal readings
    remain ambiguous. Definition content/policy, participant projection, useful
    public answers and learned realization are not completed by this component.
    Source-only selector/living-receipt regeneration is byte-identical twice:
    3,477 active / 3,734 collectable R4 nodes in 169 modules, active set
    `active_test_nodes:4bebcb6b08ae6dfd87efa39d` and metadata
    `literal_test_metadata:b519631a3440e6869f22fb57`. Existing numeric limits and
    admission roots are unchanged. This is registration, not phase admission.
- [x] **7.3 Request-first query and evidence component.** Owners: `descriptions.py`,
  `proof_bundle.py`, `r3_artifacts.py`, `r3_cognition.py`, exact decision and
  response linkage sinks. Migrate Description/Proof Bundle lineage before
  enabling evaluation: bind canonical expression and projection first; read
  once at the existing exact pin; authenticate all bounded postings; produce
  the final genuine result only after answer/evidence construction. No source
  UNKNOWN fixture, proof/result hash cycle, extra query engine, larger cap or
  new persistence table is permitted. Ordinary query substitution equality
  stays exact. Description answer linkage must be independently checked against
  the request and signed bundle, never accepted as an arbitrary answer graph.
  Memory/SQLite, restart, stale/tampered lineage, denial/conflict and overflow
  must pass before public response integration. Definition requests stay
  explicitly missing without reviewed definition content and sufficiency policy.
  The codec/lineage substrate depends on 7.1, not on public construction; it may
  close before 7.2, with public interpretation still unavailable. The selected
  minimal lifecycle uses Description/Proof Bundle ABI 2, dedicated QueryResult
  ABI 3 and Response Meaning ABI 4; the shared R3 artifact envelope, Decision
  action/status vocabulary and state-query statuses are not expanded. Exact
  request construction accepts the canonical source expression and original
  QUERY situation, deriving expression/projection/content/target/situation refs,
  budgets and original pin. Proof Bundle 2 owns that request through its
  DescriptionResult and has no QueryResult back-reference. The final query
  result distinguishes `result_kind="proposition"` from `"projection"` and
  owns optional `description_proof`: ordinary proposition proofs/bindings remain
  unchanged; projection results require the exact signed bundle, no ordinary
  ProofGraph and no bindings. Completion maps sufficient/partial/conflict/
  missing/budget-exhausted to supported/partial/conflict/unknown/budget-exhausted.
  Projection support means authenticated requested information is available,
  not that its neutral graph is affirmative world truth. Deny-only information
  remains signed support for the information request, not a contradicted request.
  Response Meaning 4 retains the identity-covered signed bundle; an answered
  projection uses exact neutral answer content with attributed epistemic status,
  while ordinary answers still require exact substitution equality. Every
  original request/answer/situation pin and decision/effect linkage is checked
  at create/decode and response sinks. Generic unsigned realization and normal
  verified-focus publication must explicitly reject projection responses until
  signed equivalence is implemented. No normal realization fallback is added.
  - [x] **7.3a Request-first Description/Proof Bundle component.** Description
    and Proof Bundle ABI 2 reject ABI 1 and the caller-supplied QueryResult seam.
    The request derives expression, projection, target, content, original QUERY
    situation and pin; the signed bundle has no final-result back-reference.
    All bounded raw postings authenticate before focused answer reconstruction.
    Activation and before/during-read authority identity checks reject drift
    without rule scans; genuine generation rollover at a fresh pin remains valid.
    Independent quality review reproduced a valid nine-root/25-application
    exception. Reconstruction now returns empty typed BUDGET_EXHAUSTED after
    authentication when existing root/application limits (8/24) or retained-root
    single-parent structure cannot represent all evidence. Corruption still
    rejects; no claim is dropped, cap raised or exception broadly swallowed.
    Initial overflow controls: 12 failures/71 passes; final 83 lineage controls
    pass. Fresh parent, final spec and final quality nine-module runs each pass
    359 cases. Spec adds eight independent probes; quality adds ten. These
    checks close the component only, not public requests or definition support.
  - [x] **7.3b Genuine projection QueryResult and evaluation linkage.** Split
    QueryResult ABI 3 from the unchanged shared artifact ABI 2. Integrate one
    authenticated projection read into the existing QueryDecisionOwner, then
    enforce exact request/result/decision/pin correspondence at EvaluationBundle
    creation and decoding. Preserve ordinary query and learning behavior.
    Implementation passed independent specification and quality review. TDD exposed 15 missing
    boundaries, 15 accepted canonical crossbindings and three cyclic-wire stalls.
    Bounded typed decoding replaces the raw JSON prewalk without an aggregate
    cap; maximum 64-by-64 ordered proof content remains serializable. The initial
    fresh parent union passes 439 cases (80 new plus 359 prior); two later
    compound/unresolved no-read cases pass separately. The final new module has
    82 cases. An existing nonfrozen three-case witness fixture now checks earlier
    EvaluationBundle rejection with the same assertion identities and unchanged
    store/journal guards; independent zero/multiple-query lower-sink controls
    remain. Only its three later literal AST hashes were regenerated. Component
    review found nested proof and evaluation ABI floats comparing equal to integer
    versions. Twenty-one further RED controls preceded exact integer-version and
    field-name guards at their existing codec owners; legitimate finite payload
    floats and maximum ordered proof content remain valid. The final new module
    has 104 cases. Fresh parent eleven-module replay passes 473 cases; final spec
    passes 463 core cases, 130 ordinary query/learning cases and 24 independent
    probes. Quality passes 401 cases across twelve modules and 23 independent
    probes. Both reviews pass. The source-only selector/living-receipt generation
    is byte-identical twice, with unchanged frozen anchors, limits and admission
    roots. This closes the query/evaluation component, not public construction,
    signed response or admission.
  - [x] **7.3c Signed response linkage.** Migrate Response Meaning ABI 4 and all
    dependent exact sinks; preserve ordinary substitution equality and prevent
    unsigned projection realization/focus publication until equivalence exists.
    Builder, R3Artifacts and the authenticated cycle terminal bind the actual
    canonical evaluation/source/situation and effect receipt. Supported answers
    preserve the exact neutral graph with attributed epistemic status and signed
    claims; other terminals preserve the request. Original proof pins remain
    distinct from legitimate journal-advanced output pins. ABI 3 is rejected;
    source hashes alone cannot authenticate an omitted answer bundle, so actual
    sinks enforce its presence. TDD reproduced the ordinary-substitution failure,
    missing evidence, accepted no-effect final-pin substitution and exponential
    shared-DAG decoding. Alias-free ABI 4 wire checks stop expansion before child
    codecs; no duplicated bundle schema, aggregate cap or extra read is added.
    The detached maximum of 64 claims by 64 ordered proof refs remains valid.
    All 64 new cases and the implementer's 316-case union pass. Fresh parent
    replay passes 720 cases across 21 modules. Its first 578.37-second run was
    unexpectedly slow; duration-enabled reruns of the identical case set pass
    80 cases in 9.42 seconds and 640 in 50.75 seconds. The outlier's cause remains
    unestablished, not a fixed or ignored regression. Spec passes 383 cases and
    31 independent controls; quality passes 122 cases and nine independent
    controls. Both reviews pass. Their maximum-proof build/decode/artifact checks
    measure approximately 0.13–0.14 / 0.05–0.06 / 0.16–0.17 seconds in this
    environment, not a competition benchmark. Three parent SQLite restart/retry
    probes preserve support, denial and missing-result receipts, response identity
    and world revision. Only three later ABI expectation AST pins changed;
    frozen inventory and assertion anchors remain unchanged. PARTIAL is a
    structural contract control, not a current retrieval outcome. Existing
    Proof Bundle 2 rejects ScopeOperator answers: nested roles/qualifiers survive,
    but no positive scoped-description capability is claimed or flattened.
    Unsigned realizers still reject projection responses. This closes the typed
    query/evidence/response component, not public interpretation, definition
    sufficiency, signed realization, migration activation or replay admission.
- [ ] **7.4 Faithful development response and isolated demo.** Preserve the
  existing R5 activation boundary and use only the approved development response
  reference. Prove real public source interpretation, genuine query result,
  exact decision/answer linkage, perspective and signed/uncertain response
  content case by case. No empty or fabricated authorized surface may count as
  a usable demo. Record normal learned realization as unavailable until fresh
  R4.1/R5 admission. Complete the existing conversation matrix before data work.
  October 1 user-approved clarification: report functional conversation,
  semantic fidelity and learned contribution separately. Here, "signed" claim
  evidence means retained `support` / `deny` stance and attribution; artifact
  hashes and authenticated acquisition grants establish neither intelligence
  nor intended-meaning correspondence. The development response reference is
  not a substitute for R5. Do not reuse the old status/count-only encoder,
  canned-sentence selection, surface-hash training targets or fixed epistemic
  confidence. Existing conditional R5 obligations must contrast answer graphs
  with identical status/count metadata, multiple legal interpretations,
  unseen compositions/aliases and candidate-pointer permutations, with
  trained/randomized/ablated semantic performance under unchanged constraints.
  A special zero-logit branch that deliberately produces invalid wording does
  not establish learned semantic realization. These are existing R5 evidence
  obligations, not added hot-path gates, new corpus authority or permission for
  pre-admission training. Bare content questions retain competing readings until
  licensed context and settling resolve them; no default reading is added to
  make the demo pass.
  The bounded output audit selects controlled English and numbered evidence
  citations for this development reference. Output-only grammatical records
  select existing explicit designation facts, never arbitrary sorted aliases or
  internal-ref spelling. Derive participant perspective from the actual
  situation; retain every role, scope, link, qualifier and claim stance, or
  report a typed output limitation. The current `Mary said Bob left` graph has
  no tense scope: event-nominal wording must not invent past tense. Early gaps
  have no ResponseMeaning and license only their actual condition/safe action.
  No normal realization receipt, focus write or learned claim follows from this
  reference. Missing public labels and definition content/sufficiency remain
  separate authority work, not data to synthesize for the demo.
  October 1 pre-repair development-reference execution finding: public `Bob likes you`
  composed the reversed relation. The earliest divergent ORIENT
  artifacts omit `role:object` from participant-reference defaults, while the
  entity-only reviewed relation order does not constrain mixed participant/entity
  evidence. Consequently the participant is forced into subject position and
  the named entity remains unconstrained. Source-faithful presentation of that
  graph is not intended-meaning correspondence. Repair the existing typed
  reference/construction owner with independent subject/object contrasts before
  claiming conversation completion; do not add a presenter phrase filter,
  silently coerce participant kinds, or bless the reversed graph as gold.
  Separately, public `I like Bob` lacks reviewed input inflection evidence;
  output grammar cannot supply missing input grounding. These concrete source
  gaps do not reopen the independently reviewed query-projection substrate.
  Direct mixed-referent closeout: the existing activated role-schema index now
  supplies one bounded clause-local relation match for named designations and
  primitive participants. Actual `entity`/`participant` kinds are retained;
  participant references include the object role and both sides receive the
  same reviewed source ordering. Coverage, compilation, independent
  reconstruction and verifier replay rematch the construction. Rehashed reversed
  countergraphs fail; polysemous targets retain all exact alternatives. No
  phrase branch, kind coercion, new schema family, ABI, gate or numeric cap was
  introduced. The existing fifteen-schema index remains below its cap of sixteen.
  Independent review caught and repaired two preservation defects before
  launch: capability queries must not be checked as ordinary relation-type
  constructions, and named-only negative/embedded role projection must retain
  its original reviewed path. Mixed scoped/embedded inputs remain unsupported
  rather than silently losing scope. English/Spanish direct controls and an
  authenticated isolated alias publication/restart pass without pack regeneration.
  Final bounded implementer union: 289 passed. Independent SPEC union: 425
  passed. Independent QUALITY: 35 mixed and 102 relation-query controls passed,
  plus ambiguous 2/4-alternative polysemy probes with no world writes. Fresh
  parent integration: 184 passed. These overlapping runs are not an additive
  total or full-regression proof; the twelve index-less fixtures remain open.
  Two final source-registration generations are byte-identical: R4 has 3,554
  active / 3,811 collectable nodes in 171 modules, active set
  `active_test_nodes:50e8e10b1d8dd52052e93ee1`, metadata
  `literal_test_metadata:c6c99a99741f997c6eca16a1`. Frozen test inventory, ledger
  anchors and replay ledger retain their prior bytes. No phase is admitted.
  A fresh thirty-cycle local development probe measured 31.68 ms activation,
  51.67 ms median cycle plus diagnostic wording, 80.96 ms maximum and 40.85 MiB
  peak process working set. Direct controls explored at most six search states
  and left world revision zero. This is neither a competition-hardware benchmark
  nor trained-model throughput or a baseline comparison.
  Presentation component closeout: `development_reference.py`, the explicit
  development-profile runtime method and opt-in CLI passed final SPEC and QUALITY.
  The 42 literal controls retain graph roles, perspective, uncertainty, ordered
  structure, signed claim attribution and actual source/effect linkage. Review
  drove RED/GREEN repair of request wrappers that erased unknown/denied/failed
  distinctions. Final implementer union: 191 passed; fresh parent boundary run:
  45 passed; each independent review: 42 passed plus independent controls.
  An isolated 13-turn CLI demo exits successfully with six meaningful surfaces
  and seven explicit interpretation gaps; this is not conversation completion.
  Default diagnostics, null normal realization receipt, focus and world state
  remain unchanged. `--development-reference --demo --store <isolated-store>`
  selects readable diagnostics; `--trace` retains their exact graph/provenance.
  Two source-registration generations are byte-identical: R4 has 3,519 active /
  3,776 collectable nodes in 170 modules, active set
  `active_test_nodes:01cc716f5c80baed7c314460` and metadata
  `literal_test_metadata:b3460b40625d007d3296a7ec`. Existing runtime-path test
  selectors are reused; no new gate, limit, admission root or frozen evidence
  changed. Full Task 7.4, source interpretation gaps and learned output remain open.

Each task closes only with observed RED/GREEN and independent review. Reconcile
deterministic dependent artifacts and literal source inventory through existing
owners before calling the migration complete. Do not repeat the interrupted
disk-full aggregate run as evidence; bounded owner runs remain the execution
method until resource conditions permit the complete existing regression gate.

### Public usability and competition-fit audit — October 1

#### Ordinary-input execution increment — user approved continuation

The fifteen-source public replay confirms that a running CLI is not sufficient
conversation acceptance. `hello` is evaluated as an attributed observation and
rendered as a claim about greetings, not a reciprocal greeting. Before this
increment, `Can you respond?` and `Can you learn aliases?` produced supported
capability answers but the output-only relation grammar required an object
role that these unary capability applications do not have. `Who likes Bob?`,
`Bob likes who?` and `Who is a mother?` retained exact query binders but had no
complete output rule. Those bounded output gaps are now repaired and reviewed.
`I like Bob` remains an input-morphology gap; ambiguous content questions and
definition content remain separate earlier owners. No phrase-specific reply or
silent default interpretation is approved.

Execute through the existing Task 7.4 and development-only reference:

- [x] Add failing public-cycle and actual interactive-CLI tests for unary
  capability answers and single-variable relation/type queries. Specify exact
  predicate/role/perspective, provenance, uncertainty and forbidden answers
  independently. Include same-status changed-graph and tampered-structure controls.
- [x] Repair only the output owner for these already verified meanings.
  Capability grammar selects explicit reviewed designation records and consumes
  the complete unary subject role. Query grammar retains binder identity and
  exact queried role, without inventing personhood, existential facts or a
  negative answer from UNKNOWN. Preserve lexical lookup, all prior response
  surfaces and fail-closed unsupported scopes/qualifiers/roles. No semantic ABI,
  phase, cap, gate, input pack, authority fact or admission changes belong here.
- [x] Run SPEC then QUALITY review, real CLI replay and existing boundary tests;
  refresh only living literal metadata/selectors deterministically. Keep normal
  realization receipt/focus unavailable and all frozen evidence unchanged.
- [x] Inspect input morphology and greeting/clarification semantics at their
  earliest owners before further changes. A reciprocal greeting requires
  response meaning, not an output filter on `hello`; definition support still
  needs actual reviewed content. Track any missing contract explicitly rather
  than inventing a new operator or masking the gap with a stock reply.

The earliest-owner inspection found three distinct unfinished dependencies:

1. `FormResolver._make_unit` emits case-folded/trimmed forms, not the declared
   morphological alternatives. `Grounder._ground_units` looks up exact source
   spans and does not consume those alternatives. Fixing only the suffix list,
   output morphology or adding an English phrase branch cannot repair input
   grounding. A bounded reversible form-to-designation derivation must retain
   the original span, reviewed rule identity and designation provenance; test
   inflected unseen aliases and multilingual contrasts before regeneration.
2. Direct greetings enter generic observation admission. Unsupported state
   admission becomes `RETAIN_ATTRIBUTION`; `_answer_expression` then preserves
   the source for every non-ANSWER decision. No reciprocal-response goal or
   authenticated response-selection derivation is present. The next semantic
   response repair must distinguish a direct greeting from quoted, negated,
   embedded and third-party greeting claims, preserve participant perspective,
   and select the response graph before wording. A presenter-side "Hello"
   filter would conceal this missing owner.
3. Ambiguous description/definition requests lack a typed alternative-choice
   continuation; actual definition content and sufficiency are also absent.
   Asking a question without consuming its subsequent answer is not closure.
   Preserve the working exact unknown-lookup obligation separately; neither
   ontology kind nor a target's graph neighbourhood is a definition.

The bounded output repair has 38 new executable controls. SPEC exposed that the
CLI tests depended on outer `PYTHONPATH`; explicit copied child environments now
prefix the absolute source directory and preserve inherited values. Both CLI
cases failed before that test repair and passed without outer `PYTHONPATH` after
it. The final files passed independent SPEC and QUALITY reviews. The parent's
fresh no-outer-path run has 183 passes across query output, existing development
reference, relation queries and the R5 realization boundary. QUALITY's overlapping
expanded run has 221 passes, including mixed-referent preservation and public
R5 profile selection; do not add overlapping totals. Ten prior public-cycle
diagnostic dictionaries are exactly preserved by independent old/new replay.

A separate nine-source actual CLI replay exits zero: both capability questions
produce supported exact-subject answers; the three variable questions retain
their queried roles and UNKNOWN status; unknown lookup and mixed participant
roles remain correct. It also confirms the remaining failures: `hello` still
retells an attributed greeting claim and `I like Bob` remains unresolved. No
general conversation demo readiness is claimed. The independent governance and
authority run has 32 passes; all 87 source modules compile in memory and the
complete authority bundle links. Two canonical selector/living-receipt generations
are byte-identical: R4 has 3,592 active / 3,849 collectable cases, 172 modules,
`active_test_nodes:9ba6bff2d05ddfaa79be5ec8` and
`literal_test_metadata:eb279547573446da060bcde2`. This refresh changes no gate,
admission root, numeric bound or frozen inventory/assertion/ledger evidence.
Normal realization/focus and phase admission remain unavailable; Task 7.4 stays
open. Complete semantic response selection before presenting another CLI launch
as a conversational demo.

#### Communicative-act contract checkpoint — user approved October 1

Fresh independent public replays identify an earlier prerequisite than output
selection. `hello`, `hi`, `hey` and `greetings` share
`expression:769c64ec5e720662df6820fb`, with user actor and system addressee.
The literal quoted source `"hello"` produces that same graph and contested
retention. `hello?` also shares it but retains QUERY force; negative and reported
greetings retain their scope/embedding. Thus a predicate/participant/OBSERVE
graph match cannot distinguish a performed greeting from a quoted mention.
The generic punctuation evidence does not establish a quotation interpretation.
Do not use source text as a downstream escape hatch or invent quotation scope.

The parent additionally reproduced `hello Bob` and `hello Alice`: both bind the
named person as actor rather than addressee. A reciprocal-reply rule cannot repair
that earlier correspondence defect. Until reviewed source-local vocative evidence
owns the named role, these examples cannot count as intended-meaning acceptance.
Unsupported `I greeted you`, `Alice greets Bob`, `hello yesterday` and `hola`
do not establish the missing past/inflection/multilingual distinctions merely
by failing; tests must specify and prove the intended graph separately.

The downstream independent audit confirms the absent contract:

- OBSERVE creates a claim occurrence for every root. State-only admission then
  yields CONTESTED / RETAIN_ATTRIBUTION for the greeting event.
- Existing ACKNOWLEDGE requires claim and admission identities. It is not a
  performed-communication consequence. ANSWER requires a supported/contradicted
  query; a greeting must not manufacture a query to obtain a different graph.
- `_answer_expression` changes source meaning only for ANSWER, and actual-source
  response, artifact and cycle validators enforce that exact derivation.
- Linked `cap:respond` is generic capability, not a reviewed reciprocal-response
  policy. The sole reviewed goal is designation resolution; the existing family
  inference rules do not authorize a response act.

The user approved the following bounded extension. Foundation amendment section
9 owns its semantic contract; this checkpoint remains unadmitted implementation
work, not activation authority:

1. Preserve source-bound communicative-force/mention evidence in the independently
   verified situated-meaning envelope. A direct performed act, a quoted mention
   and an attributed event claim are distinct. Derive it from reviewed semantic
   frame/construction evidence and source coverage, never a surface-string branch.
   Unsupported quotation must remain typed unresolved rather than lose its force.
2. Give the existing EVALUATE owner a non-claim communicative consequence. Keep
   source truth assessment separate from permission to respond; do not turn a
   greeting into admitted world truth or weaken current claim/query matrices.
3. Bind a finite reviewed response-selection derivation to the exact verified
   source/root, situation, policy/generation, participants, revision and outgoing
   expression. For a direct greeting addressed to the current system, the outgoing
   graph uses existing `op:event` with the same semantic event identity, system
   actor and original speaker addressee. Missing force, policy or capability blocks
   selection; reports, quotation, negation, temporal scope, embedded/multiple roots
   and other modes do not silently acquire this permission.
4. Carry and independently reconstruct that derivation through Decision,
   EvaluationBundle, ResponseMeaning, R3 artifact and cycle sinks before wording.
   Existing NoEffect journaling stays read-only and idempotent; no world fact,
   alias, adapter or external operation is created. Any serialized shape change
   requires its strict versioned codec and dependent artifact/test migration;
   update only the necessary target registry entries with the owning strict
   migration and explicit unadmitted status.
5. Authenticate a bounded policy index at activation and inspect only the bounded
   selected forest/source witness during a cycle. Retain all current numeric caps,
   phases, validation tiers and admitted-designation reader ownership. Diagnostic
   output remains explicitly development-only, not learned intelligence or normal
   verified focus. Extend the existing exact owner tests rather than a new gate.

Implementation order under the approved representation contract:

- [x] Independently specify direct/mentioned/reported/negated/query/third-party
  contrasts, including exact actor/addressee roles, forbidden mutations and
  response graphs, plus an authenticated unseen alias and restart case.
- [x] Repair source quotation/force and local role evidence first, with failing
  tests through actual ORIENT/PROPOSE/VERIFY and unchanged valid naming/lookup paths.
- [x] Migrate only necessary strict situated/decision/response contracts and exact
  derivation sinks, preserving ordinary queries, signed descriptions, learning and
  operation responses; reject forged source, policy, participant, effect and pins.
- [x] Add faithful diagnostic wording only after the outgoing graph is selected;
  run independent SPEC then QUALITY review and a real isolated CLI replay.
- [ ] Complete living evidence: deterministic metadata/selectors, remaining
  fixture alignment and full regression; preserve all frozen
  evidence and keep Task 7.4/R4/R5 admission explicitly open until their own proof.

This is an approved extension within the existing foundation plan, not a new
master, a claim of repair completion or permission to admit corpus/model data.
The preceding investigation changed no runtime, form pack, authority, codec,
test body or replay ledger. Implementation progress must be recorded separately.

Concrete owner sequence for this extension:

1. **C1 — quotation evidence containment.** The reviewed EN/ES form sources,
   `FormResolver` and primitive/residual contribution owner must retain quotation
   boundaries as critical unresolved evidence. Test actual public composition,
   independent coverage rejection and unchanged unquoted naming, lexical lookup,
   ordinary punctuation and reported content. This is containment, not a general
   quotation interpreter or a reply fix; no serialized shape or bound changes.
2. **C2 — reviewed semantic communication policy.** Extend the existing
   manifest-owned semantic-affordance source and linker with a closed typed
   communicative control collection. Controls bind reviewed event/frame identities,
   actor/addressee roles, a direct-performed construction and reciprocal participant
   substitution requiring `cap:respond`. Validate uniqueness, linked kinds, complete
   signatures and generation at activation; expose one immutable target index.
   Preserve all existing frame fields and attribution/inheritance controls. The
   historical monolith splitter is not an active-bundle generator and must continue
   refusing existing sources. Advance authority generation explicitly; existing
   stores must not be silently repinned. Absence of a target control grants nothing.
3. **C3 — exact source construction and situated force.** Rematch bounded exact
   source spans/contributions and local roles through existing composition and
   verification owners. Bind the selected source/root and original coverage to the
   independently rebuilt situation. Direct performed communication is distinct from
   a claim, query, report, mention and scoped/compound event; postfix addressee evidence
   cannot become an actor. No surface lexical branch or extra role-schema capacity.
   The actual selected program and candidate verification receipt must cross the
   existing `_run_r3` seam: `VerifiedMeaning` retains only coverage/proof refs.
   Retain bounded original evidence/context for performed acts, since the cycle
   currently carries proposal/verification but not those source artifacts. Rebuild
   typed form ownership and selected designation provenance at activated source
   sinks; a self-hashed context is not authenticated evidence. Do not duplicate a
   second program/proof in the situated envelope when the actual sink already owns
   them. Use the final available generic construction row within the existing cap,
   with optional prefix actor and postfix addressee; do not broaden relation rules.
   The local source addressee may be an entity, but the situation's interlocutor
   remains its reviewed participant. An explicit prefix actor is not performed
   force. A direct act addressed to another entity remains non-claim but grants no
   reciprocal response to the system.
4. **C4 — non-claim consequence and outgoing expression.** Add the necessary strict
   decision/response representation and actual-source sink checks. A reviewed reply
   derives one outgoing event using the selected semantic identity and participant
   substitution; it is neither a query answer nor admitted truth. Preserve exact
   effect journal/source/policy/capability/pin evidence, reject forged lineage and
   retain read-only idempotence. Extend diagnostic wording only after this selected
   graph is authenticated. Ordinary signed queries, learning and denied operations
   remain controls; alias acquisition plus restart tests use authenticated review.
   Selection identity must precede its containing decision/evaluation/effect/
   response identities to avoid a hash dependency cycle. Activate/authenticate
   policy and source inputs explicitly at actual-source sinks; structural codecs
   cannot infer that authority from serialized hashes. Missing authentication
   inputs fail for communicative consequences rather than introduce a permissive
   fallback. Read-only journaling retains exact source/evaluation evidence and
   reserves the original pin; terminal retries preserve the original receipt/pins
   without rebasing the selected response onto current state. These source-local
   checks extend existing owners, not an entire second VERIFY run or store scan.
   The admitted-designation reader requires the actual current read-snapshot pin;
   an original pre-EFFECT pin cannot open that snapshot after journaling advances
   revisions. Keep the semantic source pin immutable and the authenticated read
   pin separate. Later sinks must reconstruct the exact selected designation
   owner/provenance by keyed evidence and prove any admitted fact predates the
   original source world revision, rather than rerun today's surface candidates
   or rebase source identity. Terminal retries additionally bind the persisted
   original request/receipt. This uses existing bounded read and publication
   owners, not a historical store, ambient trusted flag or relaxed pin check.
5. **C5 — independent review and living evidence.** Each bounded increment receives
   SPEC then QUALITY review against fresh task-start snapshots. Regenerate existing
   selectors/living source metadata twice; no frozen inventory, replay ledger,
   admission root or numeric limit changes. Run the real isolated CLI and record
   source correspondence, response selection and diagnostic wording separately.

Each increment closes only after its owning evidence is observed. C1 and C2 are
closed by the scoped checkpoints below; C3/C4 also pass independent reviews;
C5 remains open. Passing C1 or linking C2
cannot enable reciprocal replies or close Task 7.4.

C1 implementation checkpoint (independent SPEC and QUALITY passed): the earliest-owner
tests first exposed ignored boundaries, full-span designation consumption,
stripped naming fragments and demoted/retyped residual metadata. The reviewed
EN/ES sources and existing form/context owners now retain critical quotation
evidence and reject boundary-crossing occurrences without prohibiting unquoted
aliases. A fresh parent run of the quotation, naming/locality, reported-speech,
reported-occurrence, development-reference and query-output modules passed 194
tests (29 quotation controls and 165 existing controls). This is scoped evidence,
not a full regression or communicative-response completion. An additional real
isolated source replay selected bare `hello` and `hello!`, retained the nested
reported greeting, abstained on single/double quoted greetings and preserved
lexical/capability queries without advancing world revision. `hello Bob` still
selects the incorrect actor graph: C3 must repair it before response selection.
No serialized ABI, runtime limit, admission root or frozen ledger changed.

Independent SPEC review found a further typographic-delimiter bypass in an exact
static designation fixture: curly quotes and guillemets could become one consumed
unit with the bare greeting graph. The same earliest owner now registers eight
finite delimiters in both reviewed packs. The added tests failed first; the fresh
parent seven-module replay then passed 206 tests (41 quotation controls). SPEC
review passed after its own 206-test replay and additional multilingual consumed-
boundary/naming probes. Every preexisting pack field is structurally identical
after removing only the explicit delimiter additions. Independent QUALITY review
also passed with a fresh 206-test replay and source-only inventory. C1 is closed
as bounded containment; C2–C5 and Task 7.4 remain open. This evidence still neither
authenticates alias acquisition nor selects a reciprocal response. Source-only
R4 currently has 3,633 active / 3,890 collectable nodes in 173 modules, with
`active_test_nodes:90e15a0c6f15815b5bd7a88e` and
`literal_test_metadata:2c09826d46935fd40410724c`. These are source identities,
not behavior or admission receipts; living selector reconciliation follows the
final extension freeze. Existing authority/linker/frame/alias/affordance controls
passed 204 tests before C2's explicit policy/generation migration.

C2 is closed as independently reviewed activation-only policy. The registered frame owner
now requires the typed control collection under
`authority-v1-2026-10-01-communicative-controls`; all six prior frames and existing
attribution/inheritance records are preserved, with one farewell frame and two
controls appended. Failing tests exposed alternate-capability and entity-only
role acceptance before the exact reciprocal-policy checks were added. A fresh
parent replay passed 565 authority, source and query/diagnostic controls. Two
stale relation-pack preservation tests now explicitly check the approved C1
quotation additions before restoring their unchanged predecessor hashes; no
protection was deleted. R4 source-only inventory passed with 3,686 active / 3,943
collectable nodes in 174 modules and unchanged frozen anchors. The nine due
rewrites remain for existing living-selector reconciliation after final freeze.
Independent SPEC review passed after a fresh 329-test replay and exact snapshot,
hash and source-inventory checks. Independent QUALITY review passed after a
fresh 513-test replay and a valid-namespace control/atom collision rejection
probe. Its minor test-specificity observation does not identify a production
defect. C3–C5 and Task 7.4 remain open; linking alone selects no response.

C3 starts with the source-local role construction before the coupled situated-
force/response handoff. Its fresh mixed-role/query-construction baseline passed
165 tests. An actual isolated replay still selects Bob as actor in `hello Bob`
and `goodbye Bob`, and leaves `Alice hello Bob` ambiguous. ORIENT exposes each
named referent for both actor and addressee, suppressing situated defaults;
this is the earliest divergent owner. Restrict the exact local construction
before generic reference production, then independently rematch its bindings
at the existing exact sinks. The later force/selection increment remains
unavailable until its actual-source handoff and strict sink checks agree.
The role-only increment cannot authenticate default participant targets from
the deduplicated, untyped `context_refs` order: a session or focus ref may alias
a participant ref. It verifies local roles and default provenance without that
ordering shortcut. C3's actual Orientation handoff must authenticate the default
targets before performed force or response selection becomes available.

C3a implementation is under independent review, not yet closed. The exact
source graphs first failed for postfix/prefix/both-role cases; rehashed reversed
roles, altered primitive ownership, duplicate construction owners and removed
match hints also produced failing tests before their owner repairs. A fresh
parent 14-module replay passed 566 source, role, quotation, naming, reported,
query and diagnostic controls. A separate actual eight-source replay confirms
`hello Bob` has user actor/Bob addressee, `Alice hello Bob` has Alice actor/Bob
addressee, farewell retains its event identity, reported greeting remains nested,
and quoted greeting remains unsupported. World revision stayed zero and normal
realization stayed unadmitted in every case. Both packs preserve all 15 original
rows and every other field after removing only the new closed construction.
The three frozen governance hashes and C2 authority owners are unchanged.
R4 source-only inventory passed with 3,745 active / 4,002 collectable nodes in
175 modules, `active_test_nodes:c313d68bfa32d3d146b74cf4` and
`literal_test_metadata:d3455727418125cce5dd1bd5`. The implementation's authenticated
alias/restart test is separate from its explicitly static EN/ES geometry fixtures.
One authorized projection-preservation test now checks each exact schema type
on both sides; two relation-preservation tests explicitly validate and remove
only the new row before their unchanged predecessor hashes. No test protection
was retired. Actual participant authentication, performed source force, outgoing
selection and downstream effect/response sinks remain C3b/C4 work. These scoped
passes do not close Task 7.4, admit R4/R5 or prove a conversation-ready demo.
Independent SPEC review then found a selected-evidence gap: a retained authentic
predicate could coexist with a forged same-target/source/frame predicate, and
the source assignment could select the forged one through all four exact sinks.
The earlier passing totals do not cover that counterexample. C3a is reopened
for a failing regression and exact authentication of the actually selected
contribution; a valid alternative's existence is insufficient. Fresh review and
verification of that repair are required before the source increment closes.
The repaired refreeze adds independent selected-predicate/reference and malformed
construction regressions. The fresh parent replay passed 580 tests; independent
SPEC review passed 426 tests and reran the discovered counterexamples, snapshot
preservation and frozen identities. QUALITY then ran 483 tests but found another
selected-evidence bypass: changing an explicit reference action to `bind_role`
and selecting a forged anchor with a compatible addressee port passed all four
sinks. This differs from the earlier wrong-port control. C3a remains open;
neither passing run covers this counterexample. The repair must authenticate
every consumed explicit contribution against its owning activated constructor
before action-specific pointer checks, not rely on the presence of a good
alternative or add one superficial flag check. Preserve the closed contribution
ABI and actual port compatibility; do not invent an addressee port for an anchor
that has only a target port. Accurate communicative error details may replace
the unrelated relation-query wording without changing error codes. Rerun SPEC
then QUALITY on the new freeze before C3b. Current
source-only identities are 3,759 active / 4,016 collectable nodes in 175 modules,
`active_test_nodes:079cb3ef7134ba60677e68eb` and
`literal_test_metadata:8ef9f625cecbc0d6849fcee7`. Earlier totals above are historical
checkpoints, not the final freeze.

C3a is now closed for source-local roles only. The consumed-contribution owner
regenerates the selected explicit anchor/reference before either binding action,
using the closed constructor or activated profile and its actual role ports.
Seven malformed anchor cases failed before repair; the authentic participant
anchor control passed throughout. Fresh parent verification passed 588 tests;
independent SPEC passed 434 and final QUALITY passed 491, with no remaining
scoped issue. Both reviewers independently rejected the original compatible-port
case at all four sinks and verified the exact valid control. All 11 scoped
hashes, predecessor pack fields, C2 authority and frozen governance identities
matched. Current source-only R4 is 3,767 active / 4,024 collectable nodes in
175 modules, `active_test_nodes:ac81944fe1975f0a161b03e2` and
`literal_test_metadata:2b73dae815484eaf65545f63`. These overlapping runs are not
additive or full-regression evidence. C3b/C4 source authentication and outgoing
selection remain open; no performed force, reply or admission follows from C3a.

C3b begins, after both C3a reviews, with the bounded selected-designation reader
seam before situated-force wiring. One exact selected-evidence method belongs to
the existing admitted reader: authenticate the selected designation identity and
complete provenance at a current read snapshot, with the immutable original pin
as chronology cap. Static facts use their existing keyed owner; admitted facts
use keyed world-commit lineage and the existing publication-chain reconstruction
against the original pin. Cache identity includes that original pin. Test actual
post-journal reads, rejected future publication, altered provenance/identity,
stale/closed batches, restart and the absence of surface-candidate enumeration.
This helper alone grants no force or reply and changes no serialized ABI, store,
search bound, publication policy or validation tier. Actual Orientation, packet,
selected program/receipt/root and downstream consequence authentication remain
the following coupled C3b/C4 work.

The selected-reader regression run independently exposed one older integrity
fixture failure in
`test_runtime_consumers_ignore_naked_and_reject_corrupt_publication[velnora]`.
The public `world.commit` at consumer test line 242 attempts to overwrite an
immutable normalized claim-projection fact; persistence rejects it before the
reader assertion. The parent reproduced the same failure with the task-start
reader, explicitly without `authenticate_selected`. Keep public immutability
unchanged. A separate fixture migration must preserve the read-side rejection
assertions through explicit test-only physical corruption, rather than authorize
an ordinary writer to corrupt publication evidence. The broader 365-pass/one-
failure run is not an aggregate gate pass or a regression introduced by the
selected-reader method.

The selected-reader seam is now closed as a bounded prerequisite, not completed
C3b/C4. The production delta is two codec imports and one 30-line batch method.
Its 49 cases cover real publication/restart, original chronology, full provenance,
cache separation and snapshot coherence; seven duplicate common argument-shape
cases were removed. Two existing identity cases now borrow the other real
evidence owner's designation instead of an unknown fabricated ID. Independent
SPEC passed the final 49 cases and the earlier 177-case owner run; QUALITY passed
177 cases on the final freeze with no scoped issue. Parent verification passed
49 cases plus the two strengthened cases and an actual retained-source runtime
probe after a read-only journal advance from effect revision 0 to 2. Authentication
did not alter the store and the old-pin batch still rejected. Source-only R4 is
3,816 active / 4,073 collectable nodes in 176 modules,
`active_test_nodes:07ed29908e0c701f67cc858c` and
`literal_test_metadata:ddf5ec5980f394108edc4293`. Frozen governance, C1/C2 and C3a
owners remain unchanged. The consumer integrity fixture above has now passed
independent SPEC and QUALITY review. Its two original cases and every prior
assertion remain: the public writer rejects the normalized-fact overwrite with
the original fact and pin unchanged, then explicit isolated physical corruption
exercises the same committed-journal reader rejection and unchanged-pin check.
Only the helper import, that function and its two literal AST hash pins changed.
The exact HEAD preimage matched the recorded starting hash; the earlier temporary
snapshot was unavailable. Parent verification passed the two targeted cases and
the complete 18-case module; each reviewer independently passed both runs. The
owner also passed 198 related and 134 communicative preservation cases. These
overlapping totals are scoped evidence, not a full regression or admission pass.
R4 source counts remain 3,816 / 4,073 in 176 modules; current literal metadata is
`literal_test_metadata:458bb37e02996b5b10bef0ce`. Persistence and selected-reader
owners are unchanged. Actual source/Orientation/model agreement, force,
selection and reply sinks still require the following coupled implementation.

The coupled C3b/C4 increment is closed by independent SPEC and QUALITY review
of the frozen boundary repair recorded below. C5/full regression and admission
remain open. It carries the
actual selected program and verification receipt into the existing situated
owner, distinguishes performed force from claims, and binds an outgoing graph
through the existing evaluation, effect and response sinks. Required wire cuts
also affect retained publication/evaluation journals. Reuse the existing
generation activation check for an explicit fresh-store cutover rather than
opening old journals and failing lazily, adding a store column, or accepting
predecessor wire content. Preserve all reviewed semantic data and form-pack
fields. No new gate, runtime phase, bound or corpus/model admission is authorized.

The first two public reply cases passed during implementation, but are not a
closure checkpoint. Parent probing then removed the retained communicative
source while keeping the actual selected meaning, program, receipt and
Orientation. The activated evaluator changed `RESPOND` to `RETAIN_ATTRIBUTION`
with one claim and no store change. Missing source evidence must reject rather
than silently erase performed-versus-claim correspondence. The implementer
independently reproduced the failing test; complete activated primitive evidence
and source-removal checks remain part of this same increment, not a new plan.

Parent implementation-time replay used the real interactive CLI, explicit
`--development-reference`, and isolated store
`C:\Users\Son\AppData\Local\Temp\cemm-communication-cli-e76b85e49c104f20a00169b583580238`.
Exit 0: `hello` produced `Response: greetings by me to you.`, `goodbye`
produced `Response: farewell by me to you.`, `hello Bob` produced a denied
diagnostic without a reciprocal reply, and `Alice hello` retained an unverified
claim. On restart, `Can you respond?` and `Can you learn aliases?` retained
their supported capability diagnostics. Bare `can you learn` remained unresolved;
it is not the reviewed `learn aliases` capability designation. These are
diagnostic observations, not learned or exact normal-realization evidence.
The parent new-module run still found one invalid adversarial fixture rejected
by the existing quotation/residual validator before its intended live-sink
check. Repair that fixture without weakening containment. Independent review,
living selectors and full conversation completion remain pending.

The source-omission audit also reproduced simultaneous removal of the envelope
and selected witnesses: the activated evaluator again retained one claim.
Controlled event identity may require actual witnesses for classification, but
cannot establish performed force. A second ownership check found that session
phase and turn index belong to the original `SituationInputBundle`, not
Orientation. A self-hashed situated phase cannot grant reply eligibility.
The bounded repair passes that already-owned bundle separately to the existing
pre-EFFECT evaluator/finalizer/gateway and reuses the existing situation verifier.
Post-EFFECT sinks use the authenticated original journal evaluation and exact
terminal receipt as their situated witness, before selecting a response. This
adds no Cycle payload, historical store, gate, phase, atom scan or trust flag.
The same increment remains open until these negative controls and independent
reviews pass.

Parent recheck after the lifecycle repair: the new communicative response module
passed all 51 collected cases, exit 0. The independently repeated combined
omission probe now rejects with `communicative source requires actual selected
witnesses` and leaves the store pin unchanged. The generation cut preserves all
frame/control contents; the manifest differs only in generation and frame-owner
SHA. Both language packs, selected reader, persistence and all three frozen
governance anchors remain unchanged. This is a scoped implementation checkpoint;
SPEC/QUALITY and living-selector reconciliation still own closure.

Independent SPEC review failed on three new probes despite the scoped green
tests: (1) a kernel/evaluator constructed without the activated communicative
owner silently classifies real selected `hello` as one claim and advances the
journal/session; (2) source authentication accepts a rehashed receipt, coverage
and proof pointing to a foreign Program; (3) the new standalone codecs normalize
shared mutable wire containers instead of rejecting them before child decoding.
The parent independently reproduced (1). Same-owner repair is limited to
activated-authority denial when classification owners are absent, all three
actual Program-ref comparisons, and genuine pure alias/cycle preflight. No
trusted component bypass, new gate, enlarged limit or broader runtime rewrite
is authorized. C3b/C4 remain open; repeat SPEC before QUALITY on the new freeze.

The first three review repairs passed the parent 61-case replay, but the SPEC
rereview found an incomplete ownership boundary: static finalization and direct
gateway execution still accept omitted authority as well as omitted reply
owners. The parent reproduced actual selected `hello` becoming one attributed
claim, with session revision 0 to 1 and effect revision 0 to 2. World revision
stayed zero; the journal mutation is nevertheless invalid. Live finalization
and execution must require activated authority; pure artifact codecs remain
authority-free and cannot authorize execution. Repair this existing boundary,
not event-name force inference or another runtime gate. Preserve valid assertions
in component fixtures that currently omit authority. Same-owner TDD repair and
SPEC rereview remain pending; QUALITY has not started. A genuine linked October
1 authority also accepted finalization and terminal retry of October 2 source
artifacts. The owner recorded both RED cases; parent replay after the bounded
generation check rejects both with unchanged pins. Match the original semantic
generation, not today's model identity or response pin, and preserve legal
same-generation terminal retries. Caller fixture migration supplies actual
available authority without removing retry, continuation, learning or proof
assertions. The two projection boundary tests require function-local matching
stores and genuine linked authority; their shared pure description helpers stay
unchanged.

Performance checkpoint on an isolated development SQLite store: the eight-case
parent public replay produced the expected bounded diagnostics and no world
writes, but communicative cycles took 384–417 ms versus 38–55 ms for ordinary
claim/query/capability cases. This is a local observation, not a benchmark. A
profile counted 61 Source and 28 Selection codec decodes for one greeting;
standalone decoding
decoded nested children and then public construction decoded them again. The
bounded repair separates private identity construction from public child
validation so wire decoding validates each child once. Keep alias/cycle
preflight, exact wire/hash equality, public canonical-child checks and all live
source authentication. No memoized authorization or new gate is permitted.
The parent replay after this decode-once repair passed 67 cases (the full
66-case module plus detached maximum ordered proof), exit 0. The same eight
public sources retained their actions and diagnostics with world revision zero;
communicative cycles took 272–295 ms, about 29% lower mean time in these two
single local runs. This does not establish a release resource benchmark.
The owner freeze passed 179 reply/authority/frame, 70 ordinary preservation and
168 signed-projection cases; overlapping totals are not a full-suite count.
Twenty-five caller functions were narrowly migrated across ten fixture modules,
preserving assertion identities. Current-equivalent wrong-type ABI values now
test Evaluation 3 and Response 5; Evaluation predecessor 1 and 2 both reject.
SPEC rereview passed the frozen increment. Independent QUALITY still requires
repair: an absent Source is classified from a caller receipt marker without
checking actual witness correspondence; a genuine unrelated ordinary receipt
therefore converts selected `hello` into an attributed claim. Consistently
rehashing the receipt without the marker also bypasses this guard. A second
probe passes store A's owner to a gateway writing store B; rejection occurs
only after B's journal and session revisions advance. The parent independently
reproduced both defects in fresh isolated stores. Actual witness linkage and
source-required classification must precede mode dispatch, independently of
caller provenance markers; trusted-store correspondence must precede journal
reservation. Neither predicate identity nor codec validity grants source force.
Preserve scoped/compound claims, exact terminal retry and the decode-once
repair. C3b/C4 remain open; repeat SPEC and QUALITY after the bounded repair.
Living selectors, full regression and phase admission remain pending.
The bounded QUALITY repair recorded eight intended RED failures, then passed
all eight after shared witness authentication, an expression/Orientation-only
source requirement and a pre-reservation exact store-handle check. The parent
fresh replay passed 76 cases (74 communicative cases plus both maximum-size
description/proof backends), exit 0; the separate A/B probe now rejects before
writing with both pins unchanged. The owner reports 187 communication/authority/
frame and 238 ordinary/projection cases; these overlap other runs and are not a
full-suite count. Source data, language packs, bounds and phase gates are
unchanged. Fresh SPEC passed the frozen repair: 77 strict-marker cases, six
source-force/shape contrasts, four rehashed assignment/root attacks and a
foreign-store dispatch probe with zero dispatch calls. QUALITY also passed:
246 source/reply/role/reader/diagnostic cases and 219 signed/projection/retry
cases, plus independent replays of both original attacks with unchanged pins.
There are no remaining scoped findings. C3b/C4 are closed; C5, Task 7.4,
full regression and phase admission remain open.
The actual isolated CLI replay covered seven sources and a
separate restart greeting, both processes exit 0. It distinguished reciprocal
greeting from explicit, negated and compound claims; capability lookup,
unresolved-word clarification and mixed participant perspective remained intact.
The restarted store retained world revision zero. These surfaces are development
diagnostics, not normal realization, verified focus or learned-model evidence.
The living selector refresh first stopped without writing because owner
bindings were missing for R1 `semantic-affordances` and R3
`communicative-source`. Two bounded owner-selector bindings now use the existing
source-compilation prerequisite; no admission dependency or normal-cycle gate
was added. Existing owner/phase node lists and their test inputs were regenerated
from source-only metadata. Review found that the initial new selector inputs
omitted linked authority/language roots from their dependency closures. Both
input sets now follow the established `data/authority/`, `data/languages/`,
`src/`, `tests/conftest.py` and exact owner test-file convention. No gate or
dependency was added for this receipt-currentness repair.
Both generated files are byte-identical across two
runs, with frozen anchors, numeric limits and admission roots unchanged. R4's
current source inventory has 3,890 active / 4,147 collectable nodes across 177
modules; metadata is `literal_test_metadata:be86f49b959d8c57aacc8939`.
These counts are selectors, not passing-test evidence. Independent selector
SPEC and QUALITY audits pass: all six phase contracts, exact G0 receipt,
unchanged admission/dependency closures and both authority/language fingerprints.
No scoped findings remain. The 25 individually identified fixture nodes and
full regression remain C5 work; no phase admission or MVP-completion claim follows.

The expanded audit separately exposes nine stale INITIAL fixture nodes: five
advance another session after source capture but before initial reservation,
and four modify an already EFFECTed query evaluation to request a new key at
its original stale pin. Rebuild genuine incomplete-query variants before EFFECT
or test stale-initial rejection alongside exact terminal retry after activity.
Never repin historical meaning or weaken the reservation law. Four additional
semantics fixtures concern raw authority/index mutation, text encoding and a
predecessor orthography hash. They require individual inspection, not a full
regression success claim. Subprocess import failures disappeared under the
explicit source environment used by the CLI (`PYTHONPATH=src`).

The user requested the mixed-referent repair, an interactive isolated demo and
submission-fit review. The user confirmed that no ADTC entry was submitted and
asked for better-fitting competitions. This does not authorize registration,
external submission, publication, a borrowed model, training, or phase admission.

Fresh public probes used the actual development composition root and a temporary
SQLite store, not independently supplied graphs. Their observed boundaries are:

| Source/control | Actual result before mixed-referent repair | Remaining owner |
| --- | --- | --- |
| `Bob likes you`; `Alice likes me` | Selected reversed relation, with readable but incorrect output | Reviewed source-local reference/construction binding and independent rematch |
| `I like Bob` | No selected meaning | Reviewed input morphology/designation evidence; output grammar cannot ground input |
| `who likes Bob?`; `Bob likes who?`; `Who is a mother?` | Selected QUERY, UNKNOWN in the empty store; no development wording because of `unsupported_binder` | Output-only variable/request grammar preserving the exact queried role, not invented answers |
| `Can you learn aliases?` | Selected QUERY, SUPPORTED answer; `unsupported_complete_role_rule` | Complete output-only capability role grammar and explicit designation provenance |
| `What does zorbulate mean?` | Selected unknown lookup; asks for the exact unknown expression's meaning | Retain this working unresolved path; no default identity creation |
| `What is CEMM?`; `Define mother.` | Ambiguous description/definition readings; respectively unsupported directive interpretation | Reviewed request evidence/context, actual definition content and sufficiency; not ontology-kind answers |
| `The server is offline. You said goodbye.`; `Mary said Bob left.` | Selected attributed graphs, readable controlled output | Independent source scope/tense contrasts remain necessary; the present graphs do not prove input tense coverage |
| `turn lamp on` | Selected REQUEST, UNKNOWN precondition, no action completed | This is correct containment without a connected/authorized operation; never describe it as successful execution |

The immediate finite finish line is source correspondence, complete wording of
reachable typed query/capability responses, and the existing restart/continuation
conversation proof. Fix the earliest owner of each independently specified case;
do not repeat completed codecs, replace the brain, or expand corpus families to
make a diagnostic pass. An unknown answer due to missing admitted facts is not
the same defect as missing interpretation or missing response wording.

There are two separate claims beyond that development finish line:

1. **A reproducible functional prototype:** a pinned build, a bounded documented
   use case, independent source-to-meaning controls, readable uncertainty, an
   isolated interactive demo and measured offline resource usage. Component test
   totals are not a competition benchmark or full-regression completion.
2. **A learned Hybrid model:** fresh R4.1 admission, authorized independent gold,
   then the existing conditional R5 training/generalization/weight-use evidence
   and exact response equivalence. The bootstrap proposer and finite development
   presentation must remain explicitly disclosed; neither is learned evidence.

ADTC 2026 is not an available unchanged-runtime submission path. Its
[official rules](https://adtc-2026.devpost.com/rules) close initial entry on
August 25; October 17 is the live final round. Its
[official template](https://github.com/Africa-Deep-Tech-Foundation/adtc-2026-submission-template)
requires a pinned public GGUF weight download and exclusively `llama.cpp`.
CEMM's current development root is a custom Python semantic runtime, and its
neural/release profiles explicitly raise `MissingOwner`. Adding metadata or a
GGUF-shaped file cannot make that runtime acceptable. Do not implement a fake
adapter, relabel static computation as a trained model, or add a stock LLM
without a separately reviewed product/competition decision. Alternative
competition eligibility must be checked against primary current rules before
choosing packaging or making readiness claims. This audit adds no runtime gate
or new governing execution plan.

The expanded source run also records 12 unresolved
`tests/test_proposal_context_builder.py` fixtures. They omit the activated role
index and fail at the terminal `licensed_query_projection_slots(index=None,
context)` call with `TypeError: licensed projection slots require exact activated
index/context`. A fresh parent replay of
`test_builder_binds_exact_canonical_orientation_ref` confirms that earliest
exception. The remaining affected intents cover orientation/cache lineage,
identity/index construction, source bounds, structural/reference contributions,
critical residuals and event signatures. Those independently valid assertions
need exact activated-fixture migration, not deletion or a permissive None/index
fallback. Their task-start baseline has not been demonstrated; neither the
expanded 233-pass/12-fail run nor the scoped repair passes is a full-regression
completion claim. Keep this fixture owner distinct from public interpretation
and output-rule gaps.

Alternative-competition research, checked October 1 against official pages:

| Route | Current entry window | Material fit/eligibility limits |
| --- | --- | --- |
| [NASA Space Apps 2026](https://www.spaceappschallenge.org/?linkId=225077771) | Registration open; hackathon November 14–15 | Broad application format, no published compulsory LLM. Build a new official challenge/NASA-data solution during the weekend. [Published build-period restriction](https://www.spaceappschallenge.org/2026/local-events/santiago-dominican-republic/) means an already completed CEMM project cannot simply be submitted unchanged; confirm underlying-engine reuse and virtual event eligibility first. |
| [SALTIS P.A.S](https://www.saltis-techinov.org/pas-challenge) | Applications October 1–14 | Teams at most five; every member 15–30 and a student or early-stage founder. A relevant deployed POC needs real-user evidence and climate impact; December 10 finale in Dakar. Nigerian participation, existing-engine reuse, costs and remote/travel arrangements are unconfirmed. |
| [ARC Prize / ARC-AGI-2](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2) | Entry October 26, 23:59 UTC; code November 2 | Custom offline notebook computation, not a compulsory GGUF runtime. A genuine grid-reasoning implementation and reproducible open-source release are substantial new scope. [Paper Prize](https://arcprize.org/competitions/2026/paper) also requires working benchmark code; a generic CEMM architecture paper alone is insufficient. Verify licensing and personal eligibility before entry. |

Final interactive launch checkpoint: the actual Hybrid CLI passed a separate
three-source stdin replay and exited zero: `Bob likes you` yielded
`Unverified claim: Bob likes me.`, `Alice likes me` yielded
`Unverified claim: Alice likes you.`, and the unknown lookup retained its exact
literal and requested meaning without creating an atom. A visible PowerShell
demo was then launched with `--interactive --development-reference` and a unique
temporary store; the parent shell and exact Python child remained alive and the
store was created. No legacy web runtime, new UI/server or production store was
used. Post-documentation mixed-role/governance/R5-boundary replay: 38 passed;
`git diff --check` passed and all three frozen hashes remained unchanged.
The interactive launch is a development conversation, not R5 realization,
full conversation-matrix completion or phase admission.

These are candidates, not registrations or a change to CEMM's governing goals.
For a near-term application demo, NASA is broader than an ARC benchmark rewrite;
SALTIS is conditional on personal/cross-border eligibility. ARC better tests the
research thesis but is not an efficient shortcut to finishing the current MVP.
Choose one honest, bounded use case before adding competition-specific evidence
or packaging; the source/response repairs above remain useful independently.

Selector maintenance at this checkpoint reconciles existing literal R3/R4
foundation owner groups with `validation_gates.json`, including previously
omitted groups. Each selected diagnostic owner still runs one pytest process;
admission roots, runtime limits, frozen inventory and replay ledger are unchanged.
The living source-only inventory receipt is regenerated with the selectors, not
used as a behavior/admission claim. Two canonical generations are byte-identical.
The earlier checkpoint's source-only R4 set had 3,069 active nodes
(`active_test_nodes:5ecde142cab0950691c8d1ea`) and 162 parsed test modules.
After the 10 posting-focus controls, the fresh set has 3,079 active nodes
(`active_test_nodes:29af403e9462797d92f39f31`), 3,336 collectable nodes and
163 parsed modules. Literal metadata identity is
`literal_test_metadata:3846a09ec46ae47226cb9266`; two selector/receipt
generations remain byte-identical with unchanged limits and admission roots.
The canonical living receipt, authority linking, compilation of 86 source
modules and structural hard-cut checks pass. Frozen inventory, replay ledger,
admission roots and runtime limits are unchanged.
After the 17 canonical projection and 83 request-first lineage cases, source-only
R4 has 3,179 active nodes (`active_test_nodes:4e28db9d5e64e21a32871667`),
3,436 collectable nodes and 165 modules. Literal metadata is
`literal_test_metadata:dd3f35dca4c4de9c2b48b46c`. Two selector/living-receipt
generations are byte-identical; frozen anchors, limits and admission roots remain
unchanged. Six fresh foundation/document-classification/anchor checks pass.
This is source and component evidence, not a clean checkpoint or admission.
After the genuine QueryResult/evaluation owner controls and strict-wire repair,
source-only R4 has 3,283 active nodes (`active_test_nodes:e528f31f322e884510ceca7e`),
3,540 collectable nodes and 166 modules. Literal metadata is
`literal_test_metadata:738a6f9cfaeb6a93e0d2addb`. Two canonical selector/receipt
generations agree byte for byte; all 86 source modules compile in memory,
authority linking and structural hard-cut checks pass. The previously recorded
dirty G0 admission rejection and stale historical R5 selector assertion remain
separate open controls, not passes manufactured by this component repair.
After signed-response integration, source-only R4 has 3,347 active nodes
(`active_test_nodes:722ad38b928a62854978684a`), 3,604 collectable nodes and
167 modules. Literal metadata is
`literal_test_metadata:8d011d7a46ad33d56a0e253f`. Two canonical selector/living-
receipt generations are byte-identical. Frozen inventory, assertion/ledger
anchors, admission roots and runtime limits remain unchanged. All 86 source
modules compile in memory; authority linking and structural hard-cut checks pass.
This source/component checkpoint is not a clean commit, public demo or admission.

The governed documentation run exposed three routing defects: the completed
description child plan was unclassified, the exact historical expectation omitted
the existing September 8 audit, and that audit lacked its status-neutral banner.
Their original assertions now pass after owner/expectation corrections; no test
body or frozen AST was changed. The fresh 108-case governance run has 107 passes
and one dirty-input admission rejection. That remaining status-CLI check requires
a clean validated checkpoint; it must not be weakened, removed or credited as a
pass while these changes remain uncommitted. No aggregate gate is claimed.

A separate fresh raw five-module run of query integrity, lineage, retrieval,
R5 realization boundary and test inventory has 138 passes and one failure:
`test_r5_real_overlay_is_exact_and_g0_through_r4_are_unchanged` compares current
pre-R5 active sets with literal historical hashes. The failure occurs already
at G0 (expected `active_test_nodes:b81f58a6ce47c11125f05581`, actual
`active_test_nodes:5429985f0f1e8edc98f7efd7`). Its R5-owned phase-isolation
obligation remains valid; historical set identity is not a current invariant
after approved foundation additions. No test body, AST pin, frozen inventory or
disposition was changed to turn this red into green. Before R5 closeout, replace
the historical-set assumption with an independently controlled phase-isolation
test that rejects R5 overlay effects on pre-R5 selection while preserving exact
frozen inventory and the reviewed 17/25/1 partition. This is not a runtime focus
regression or a release pass.

After these checkpoint corrections, 11 selected document-routing, immutable
anchor and canonical G0-evidence checks pass. Authority linking, in-memory
compilation of all 86 source modules, structural hard-cut checks and scoped
whitespace checks also pass. No aggregate runtime, competition demo or fresh
phase admission is established by these bounded results.

The October 1 attempt to execute the 2,968-node active R4 set
(`active_test_nodes:9c8026ff8e4153ea2967340e`) was interrupted when C: had zero
free bytes. Its failures are invalid environmental evidence, not a regression
baseline or a passing gate. Space later recovered to approximately 18.6 GB;
the cause was not established (that run's visible temporary files totalled only
approximately 72 MB). Continue bounded owner runs and fresh verification rather
than treating that interrupted aggregate run as implementation evidence.

- [ ] Complete spec and quality review of code, active docs, data and tests.
- [ ] Run existing authority, ABI, anti-bloat, semantic-operational, web and
  relevant regression checks; reconcile selector/inventory disagreement through
  existing selector generation, never bypass it.
- [ ] Record reference capability, remaining gaps and actual resource measures
  separately from learned-model results and replay admission.
- [ ] Resume data work only after the foundation semantic/response loop passes;
  an isolated learned pilot still needs explicit R4.1-compliant data authority.
  It must add measured generalization before the hybrid objective is complete.

## October 2 publication checkpoint and R4/R5 closure boundary

The user explicitly requested committing and pushing all accumulated hybrid
changes. This is a work-in-progress publication, not merge, root adoption,
corpus publication or replay admission. Fresh precommit verification passed
189 communicative response/authority/frame and maximum-cardinality description
proof cases in 30.59 seconds, source-only G0/R4/R5 inventory reconstruction,
Python compilation and whitespace checks. These are bounded checks, not a full
regression result. The 25 individually identified fixture nodes and the wider
foundation acceptance obligations remain open.

Direct artifact/source inspection confirms that `data/review/r4_1/` is absent,
the checked-in R4 build receipt is predecessor ABI 3, and its derivation file
has no records. The predecessor trainer still extracts selected-program labels.
Its presence is not an eligible R4.1 consumer or proof of learned activation.
The ledger's last R4 transition is red; no fresh R4.1/R5 admission is recorded.

The finite closure order remains:

1. Finish the existing foundation route: migrate the 25 fixtures without
   weakening their valid assertions, resolve independently specified public
   interpretation/response gaps, and obtain clean governed regression evidence.
2. Resume the retained R4.1 route only after its foundation freeze is lifted:
   independently reviewed expression/derivation and response supervision,
   independent mutation truth, reviewed duplicate-risk membership and fixed
   minima in every purpose, compact payloads, predecessor-consumer hard cut,
   deterministic ABI-5 publication and exact clean R4 admission.
3. Execute the conditional R5 route from that admitted data: actual learned
   legal-action/pointer proposal and graph-conditioned realization, isolated
   train/selection/calibration, reproduction, measured weight-use/generalization,
   exact response equivalence and normal realization/focus, resource-bounded
   activation canaries and current-source R5 admission. All 25 deferred R5
   obligations need executable successors. Frozen-test consumption belongs to
   R7, not R5. Development wording and bootstrap proposals cannot substitute.

This checkpoint adds no runtime or admission gate, changes no phase status and
does not authorize training or automatic review-source approval.

## Progress and stop discipline

Update checkboxes only with observed evidence. Never label Task 2 containment as
Task 4/5 completion. Repair findings within this approved scope without another
routine approval loop. Escalate only for a material change of goal, irreversible
operation, new external authority, or a representation decision that cannot be
resolved within the approved semantic contract. Do not merge or push implicitly.
