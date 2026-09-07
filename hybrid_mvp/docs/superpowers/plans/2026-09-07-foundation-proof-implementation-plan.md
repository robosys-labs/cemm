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

The currently seeded restart test is useful only as an admitted-world-fact/index
seam probe. Its manually inserted `Fact` is not acquisition authorization and
cannot satisfy steps 3–4. Likewise, manually constructing a pending obligation
is a continuity seam probe, not evidence that an unknown public query creates a
usable continuation. Keep those distinctions explicit so later work cannot
recurse by substituting fixtures for the missing runtime owners.

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

Next: bind the captured snapshot and its exact pending continuation through the
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
