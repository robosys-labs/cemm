# Individual remaining-failure audit — September 8, 2026

**Diagnostic evidence, not a new governing plan, successor approval, or phase admission.**

Historical observations only. Current replay status and exact admission identities
are derived only from `governance/replay_status.jsonl`.

Scope: `C:\dev\cemm\.worktrees\unresolved-designation-r4\hybrid_mvp`,
commit `5bbe7a4` plus the existing uncommitted naming-owner repair.
The foundation amendment and its existing implementation plan continue to govern.
This audit changes no runtime, tests, mappings, data, gates, bounds or admission records.

## What was actually reproduced

- Fresh targeted run: **161 failed in 12.89 seconds**, comprising all 159 current R3 successor wrappers and the two standalone failures below. This was a rerun of the failing subset, not another full R3 run.
- Source-only inventory authentication: **2294 active R3 nodes**, including **159 wrappers representing 139 distinct assertion identities**. Parametrized and migrated cases must not be removed merely because they share an identity.
- Active-set identity: `active_test_nodes:b3c26c97e9fa1bb134b71605`.
- Literal-metadata identity: `literal_test_metadata:41269499360dc385f93f719b`.
- The prior full comparison remains 2133 passed / 161 failed. The new investigation does not convert any of those failures to a pass.
- Pytest plugin autoload initially stalled before collection; the diagnostic was rerun with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `-o addopts=` and `-p no:cacheprovider`. This changes no repository configuration or semantic test expectation.

Every wrapper fails at `tests/r3_successor_contracts.py:33` before reaching its alleged behavioral owner. The historical router at `ed240ef` dispatched by broad category, ignored the specific assertion identity after checking its prefix, and cached those category results. The correction at `add3917` removed that false credit and admits only explicitly audited assertion runners. Restoring a category-wide runner would hide missing proof rather than repair behavior.

The individual rows below distinguish:
1. a narrow assertion already covered by a current test;
2. implemented helper behavior without an exact checked-in successor;
3. an obsolete API, fixture or expectation requiring explicit migration;
4. actual missing or defective runtime behavior;
5. a contract or acquisition scope that is not resolved by alias support.

A suggested exact test is evidence for reviewing a mapping, not automatic authorization to attach historical assertion credit. No mappings were changed. A helper probe does not establish public runtime reachability.

## The two non-wrapper failures

| Test | Fresh evidence and earliest cause | Appropriate next action |
|---|---|---|
| `tests/test_foundation_semantics.py::test_foundation_matrix_fresh_fragment_requires_clarification` (line 4680) | Fails at line 4687 because evaluation is absent. Public input `that you learn` has no focus or obligations, OBSERVE mode, four explored states, no truncation and no complete proposal. The available `event:learn_alias` frame requires actor, target and surface; only the actor reference is supplied. The content linker has no enclosing proposition/content slot. `runtime.py:652` finalizes unselected verification without EVALUATE; `r3_cycle.py:368` preserves required canonical artifacts. World revision remains zero. | Preserve the valid clarification requirement but migrate its overly specific “must already have EVALUATE” assumption through an approved incomplete-content/gap response representation. Do not fabricate VerifiedMeaning, bind missing content to arbitrary words, increase search caps or call the gap a training failure. Context-bound completion also needs an exact pending content slot, not merely a prior speech record. |
| `tests/test_replay_governance.py::test_status_cli_derives_current_effective_status` (line 3032) | CLI returns 2 with “dirty governed input is not validated admission evidence,” listing the existing naming repair and its docs/tests. It fails at line 3041 before printing verified historical phase status. Independent source inventory authentication succeeds; that does not waive worktree cleanliness. | Preserve the check. After a reviewed local checkpoint, rerun the CLI and this node. A commit alone is not proof of clean verification and cannot fix the other 160 failures. No commit was made in this audit. |

## Public-runtime contrasts beyond wrapper bookkeeping

All probes used isolated temporary SQLite stores, the actual development runtime and fresh sessions. No real authority was changed, and world revision remained zero.

| Input | Current result | What it establishes |
|---|---|---|
| `Alice said goodbye.` | Selected expression after 130 states; reported farewell actor Alice, **addressee participant:system**; retain-attribution decision, no surface. | The addressee is invented. `proposal_context.py:3058` supplies situated participants to event frames without distinguishing reported content from a current utterance; the farewell signature requires an addressee (`data/authority/conversation.json:317`). Repair frame/role ownership together, not optional-role metadata alone. |
| `Alice said Bob left.` | Ambiguous after 179 states, not truncated. | This is not a budget problem. Explicit child actor versus parent/control ownership remains unproved; do not select a candidate just to eliminate ambiguity. |
| `The server is offline. You said goodbye.` | 768 states, truncated, 48 candidates; all 48 coverage receipts executable, all 48 verifier errors `proposal_truncated`; final status UNSUPPORTED. | Coverage is not meaning correspondence. The first candidate assigns “The server” as actor and “You” as subject across clauses. The verifier correctly refuses truncated uniqueness, but terminal reporting loses the budget-specific cause (`runtime.py:792`). Repair generic clause/control ownership before safe state deduplication, and preserve budget honesty. |
| `Can you learn?` | No complete proposal, four states, not truncated. | General learning/capability interpretation is narrower than the requested user behavior. More epochs cannot supply the missing semantic composition. |
| `Can you learn aliases?` | Selected `cap:learn_alias(subject=participant:system)`; answer decision, 17 states; no surface. | A useful capability meaning is reachable, but user-visible response completion is not. |
| `What is a mother?` | No complete proposal, four states, not truncated. | Retiring the false registry-kind definition was correct containment; genuine description/definition remains absent. |
| `you said what?` | No complete proposal, five states, not truncated. | A supported speech-content query/continuation is missing; this does not justify a blanket abstention gold label. |

Selected cycles unconditionally record the missing `contract:r5:realize_surface` owner at `runtime.py:708`; this is not a verified conversation. The foundation amendment already permits a development-only compositional response reference. Implementing that approved reference and faithful gap/response continuity is distinct from activating learned R5 output. Normal focus must still require its exact equivalence evidence.

## Query correctness probes, separate from public parser claims

Main reproduced the first four rows through the actual QueryDecisionOwner with linked authority and isolated in-memory facts. These are direct-owner probes, not claims of public stale-pin execution. Main also reproduced the reported-premise/source-loss contrast below. The query sub-audit additionally reproduced finite rule chains and reviewed-rule source loss.

| Controlled setup | Observed result | Earliest owner |
|---|---|---|
| 256 irrelevant facts sort before one true relation fact | UNKNOWN, no proof, only 256 retrieval refs | `r3_cognition.py:552` slices before matching; `persistence.py:1777` already materializes all facts. Neither relevance nor complete-search honesty is established. |
| Support + 255 irrelevant facts + denial | SUPPORTED / ANSWER with only the support proof | Same slice hides contradiction. Raising the cap would move, not remove, the defect. |
| Two opposing facts without intervening rows | CONFLICT with both proof roots | Positive control: conflict handling works when both facts reach the matcher. |
| Situation pinned at world 0, then one fact committed at world 1 | SUPPORTED proof labeled world 0 | Nonlexical branch `r3_cognition.py:674` does not use the existing read snapshot. Match meaning/situation pins is not the same as proving that the store read used that pin. |
| Seven dependent rules under six-round cap | UNKNOWN after six rounds, no proof | `_rule_closure` (`r3_cognition.py:277`) exits the round loop without marking uncompleted closure. |
| Two reviewed rules with independently labeled lesson sources | Supported chain, rule identities present; only observation source retained | Derived-fact sources at `r3_cognition.py:340` retain parent sources but omit reviewed rule `source_ref`. |
| One stored reported-only premise and a reviewed implication rule | Both the direct unqualified premise query and the derived conclusion return SUPPORTED; proof retains the report source but drops the lesson source | Unqualified matching has no default placement filter, and closure matches at `r3_cognition.py:304` without premise placement before labeling output “derived.” This is a controlled owner-level stored-evidence probe, not a demonstration that normal admission writes reported claims into world truth. |

The safe query repair is already in Task 6: one pinned relevant read/proof batch, predicate/argument demand closure, complete support/denial handling, honest rule/fact/round exhaustion, and placement/source preservation. Keep the separately shared state-precondition reader and authenticated lexical reader intact. No new store, gate or larger numeric cap is needed.

A separate main-reproduced response projection maps UNKNOWN to UNKNOWN and DENIED to DENIED, but **BUDGET_EXHAUSTED to PARTIAL** with a valid NoEffectReceipt. `ResponseBuilder._status` (`r3_response.py:273`) lacks the budget branch. This isolated projection confirms another owner defect; it does not claim a complete public exhausted-query replay. Fixing inference exhaustion alone therefore cannot finish truthful budget reporting.

## Reading the individual audit

The following sections contain one row for each of the 159 failing wrappers. The hash identifies `tests/test_r3_closeout_successors.py::test_r3_successor_<hash>`. Each section names its evidence paths and verdict codes. Historical source references are read-only evidence, not active runtime authority.


## Dialogue failure audit — 40 wrappers

Audited all 40 wrappers. All fail at `tests/r3_successor_contracts.py:34` because no assertion-specific runner exists—not because they exercised dialogue behavior.

Read historical bodies from `add3917`; `git diff add3917 --` confirms the three predecessor files remain unchanged. No repository files edited or real stores mutated. This temporary report is the only authored file.

### Verified evidence

- Selected current tests: **12 passed** with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `-p no:cacheprovider`, and `-o addopts=`.
- Current-ABI in-memory probes passed the helper invariants below, including a separate `OrientationProjector` probe. These probes are diagnostic evidence, not newly checked-in successor tests.
- Public development runtime, isolated temporary DB:
  - `Alice is a mother.` reached EVALUATE, returned `PARTIAL`, R5 realization gap, focus revision **0**.
  - `What did you say?` returned `proposal:no_complete_candidate`, no evaluation, focus revision **0**.
  - `that you learn` returned the same proposal failure, no evaluation, focus revision **0**.

The 12 passing cases came from these exact current test functions in `tests/test_foundation_semantics.py`:

- `test_foundation_matrix_speech_content_focus_keeps_speaker_session_and_recency` (2 cases)
- `test_foundation_focus_restart_session_window_precedes_person_and_turn_filter` (3)
- `test_foundation_focus_restart_standalone_diagnostic_api_remains_transient` (1)
- `test_foundation_focus_restart_active_orient_preserves_record_identity_without_writing` (2)
- `test_foundation_pending_dialogue_codec_is_exact` (1)
- `test_foundation_pending_dialogue_reads_exact_keys_and_rejects_invalid_lifecycle` (3)

### Evidence keys and verdicts

All paths are relative to `C:\dev\cemm\.worktrees\unresolved-designation-r4\hybrid_mvp`.

- **D** = `src/cemm_authoritative_hybrid/dialogue.py`
- **R** = `src/cemm_authoritative_hybrid/runtime.py`
- **F** = `tests/test_foundation_semantics.py`
- **C** = current exact test exists, at its stated helper/runtime boundary.
- **U** = implemented but no checked-in assertion-specific proof found; current-ABI audit probe passed.
- **M** = actual missing runtime behavior. The historical fixture did not prove that behavior.
- **O** = obsolete assertion/result shape requires migration.
- **A** = ambiguous contract needs decision.

Each hash below is the suffix of `tests/test_r3_closeout_successors.py::test_r3_successor_<hash>`. A predecessor's full node ID is its section filename plus `::` and the listed function/parameter name.

### `tests/test_dialogue_focus.py` — 8 wrappers

| Hash | Predecessor | Exact invariant and current evidence | Verdict; smallest safe action |
|---|---|---|---|
| `03c11585efe153827572` | `test_mixed_verified_and_unverified` | Accepted system content appears in focus; rejected content does not. Historical `_DialogueSession` merely branches on a supplied boolean (`test_dialogue_focus.py:55`); active runtime ends with no realization receipt (`R:708`, `R:760`) and never writes focus. | **M** for normal runtime admission. Keep negative protection; implement/prove equivalence-gated positive admission before crediting mixed-runtime behavior. |
| `30cfc728a8ddc6af448e` | `test_focus_store_recent_entries` | Last two entries returned oldest-to-newest. Owner `D:104`; exact transient assertions at `F:3712` verify `(other, first)` and session-filtered ordering. | **C**, direct store only. Bind this particular assertion to the transient recency test. |
| `4ae8e030ad8426ba19b5` | `test_focus_store_starts_empty` | Empty refs and negative membership initially. `D:86`, `D:99`; probe passed. Old `.query()` method is gone. | **U**. Add exact empty-store/ref-membership test using current API; do not restore `.query()` compatibility. |
| `acb0ed90038c0bce5e74` | `test_focus_store_accumulates_across_turns` | Adding two focus records retains both references and entries. `D:90`; `F:3712` explicitly verifies accumulated entries and union of refs. | **C**, transient diagnostic store. Bind to that exact test, without claiming authenticated admission. |
| `b248e4945e9a868ee84c` | `test_verified_user_proposition_enters_focus` | A verified user proposition becomes subsequent focus. Historical fixture fabricates its proposition hash and verification (`test_dialogue_focus.py:105`). Current public verified/evaluated membership leaves focus revision zero; no normal writer exists. | **M** at runtime. Specify/prove the legitimate user-focus admission boundary; do not map a manually inserted record as public evidence. |
| `dc84231f7f90a715b69f` | `test_focus_store_stores_verified_refs` | Membership includes both propositions, entity, and event; excludes absent ref. `D:99` unions all three current fields; probe passed. Existing foundation transient test covers expressions only. | **U**. Add one exact current-ABI test covering expression/entity/event refs plus negative membership. |
| `e7a30b650ce6517f401a` | `test_verified_semantic_focus_is_frozen` | Assignment to semantic-ref tuple fails. Frozen factory-only type at `D:29`; mutation probe raised `FrozenInstanceError`. | **U**. Add exact immutability test through `.create()`, not old constructor. |
| `ec8f7eda4b6dc2aa92fc` | `test_verified_output_enters_focus` | Verified system response content enters focus. Historical fixture labels arbitrary text verified; current REALIZE explicitly returns an R5 gap and no receipt (`R:708`, `R:760`). | **M** at runtime. Preserve fail-closed output; prove an equivalence-gated normal writer before positive successor credit. |

### `tests/test_dialogue_obligations.py` — 19 wrappers

| Hash | Predecessor | Exact invariant and current evidence | Verdict; smallest safe action |
|---|---|---|---|
| `0a59b0d3bb8df37b4930` | `test_goal_arbiter_prefers_obligation_over_goal` | Pending obligation wins, goal unset, derived label `obligation:fulfill`. Current `D:703`, `D:715`; probe passed. | **U**. Test exact `DialogueObligation` input and all three outputs. |
| `1e4717dec0e04f377686` | `test_fulfill_marks_obligation_with_completion_receipt` | Completed record disappears from pending and remains retrievable by original ref with receipt. `D:596`, `D:599`; probe passed. | **U**. Add direct-manager completion/alias test. Do not interpret manager `.fulfill()` as authorized learning publication. |
| `3b4cfeb86fa0db77def5` | `test_dialogue_obligation_accepts_typed_kinds[evidence_request]` | Evidence-request kind is retained. Exact enum enforced at `D:289`; `F:5558` round-trips every enum member. | **C**. Bind explicitly to this member's codec assertion. |
| `4e18303fa2e5f85519e1` | `test_goal_selection_is_frozen` | UI label cannot be reassigned. `GoalSelection` frozen at `D:662`; label is now derived property at `D:679`. | **U**. Test assignment rejection and derivation; omit retired constructor label argument. |
| `765ec49d46eaedeb18e0` | `test_dialogue_obligation_carries_source_query_and_contract` | Source query, answer contract, expiry, and absent completion survive construction. `D:288`; canonical round-trip equality covers these fields at `F:5558`, with required-source rejection. | **C**. Bind to exact field/codec assertion using `expires_turn_index`, not retired `expiry`. |
| `91f33f163e6a10e410b7` | `test_dialogue_obligation_accepts_typed_kinds[learning_answer]` | Learning-answer kind retained. `D:289`, `F:5558`. | **C**. Explicit member-specific binding. |
| `a35b386efc1b5d62d530` | `test_goal_arbiter_ignores_satisfied_obligations` | Completed obligation ignored; available goal selected; label `goal:pursue`. Current completion receipt replaces old `satisfied` boolean (`D:704`); probe passed. | **U**. Add completion-receipt-based selection test; do not reintroduce persistence `Obligation` input. |
| `a85edba372926159baca` | `test_fulfilled_learning_allows_new_learning` | Completing first learning record permits adding second. `D:575`, `D:599`, `D:655`; probe passed. | **U**. Preserve exact direct-manager assertion. Separate gateway publication completion from arbitrary helper receipt strings. |
| `b3e455c6c3aafd588648` | `test_non_learning_obligations_coexist` | Clarification, evidence request, operation resolution coexist. Guard is learning-only (`D:579`); probe passed. | **U**. Add three-kind pending-set test. |
| `b48619272bc7c008bae8` | `test_fulfilling_non_learning_does_not_consume_learning` | Completing clarification leaves learning pending with no completion receipt. `D:602`, `D:628`; probe passed. | **U**. Add exact cross-kind isolation test, not generic continuation smoke. |
| `b84479b75b9548b571b7` | `test_ui_intent_label_has_no_control_authority` | Historical body only asserts label equals `goal:pursue` and differs from goal ref. Current derived property `D:679`; probe passed. | **U**. Preserve that narrow assertion; additionally do not claim it proves all runtime consumers reject label-based dispatch. |
| `be210355a7860538c47c` | `test_dialogue_obligation_accepts_typed_kinds[operation_resolution]` | Operation-resolution kind retained. `D:289`, `F:5558`. | **C**. Explicit member-specific binding. |
| `c7b1f7079a3fe5c96275` | `test_dialogue_obligation_is_frozen` | Kind mutation fails. Frozen factory-only record at `D:272`; probe passed. | **U**. Add exact mutation test through current factory. |
| `ce67b625850e1d0b8f06` | `test_goal_arbiter_selects_higher_priority_obligation` | Explicit numeric priority **5.0 must defeat 1.0**; not merely deterministic choice. Current record has no priority, and arbiter chooses minimum expiry/ref (`D:708`). | **A**. Identify reviewed authority for priority-to-expiry migration, or obtain a policy decision. An earliest-expiry test cannot inherit numeric-priority credit. |
| `d1c5dbf99de9415b8519` | `test_only_one_learning_obligation_may_exist` | Second pending learning add raises `ValueError`. `D:579`; probe passed. | **U**, exact manager assertion. Add current-ABI unit test; public same-session nonrenewal at `tests/test_foundation_automatic_continuation.py:826` is related but not identical global-manager scope. |
| `decaeee068cfd77411c0` | `test_goal_arbiter_idle_when_nothing_pending` | No goal/obligation selected and label `idle`. `D:683`, `D:715`; probe passed. | **U**. Add exact empty-input result test. |
| `e163cfcc344eddf14b3b` | `test_dialogue_obligation_accepts_typed_kinds[clarification]` | Clarification kind retained. `D:289`, `F:5558`. | **C**. Explicit member-specific binding. |
| `e8164c03ba5a45f4c73a` | `test_pending_returns_unfulfilled_obligations` | Two unfulfilled additions returned with exactly their identities. `D:635`; probe passed. | **U**. Add exact manager pending-set assertion. Persisted keyed-read tests exercise a different API. |
| `fd3d8d92c3cd8dbd7b9b` | `test_learning_obligation_alongside_non_learning` | Clarification and learning coexist; learning flag true; pending count two. `D:579`, `D:655`; probe passed. | **U**. Add exact mixed-kind assertion, keeping this distinct from three-nonlearning coexistence. |

### `tests/test_discourse_reference.py` — 13 wrappers

| Hash | Predecessor | Exact invariant and current evidence | Verdict; smallest safe action |
|---|---|---|---|
| `0e8f1a78989177d083df` | `test_that_resolves_most_recent_proposition` | Resolver selects second prior proposition, excluding current turn. Historical fixture recognizes `that` through string checks (`test_discourse_reference.py:144`); current structural selection implemented at `D:229`, `D:253`. | **U**, direct semantic resolver only. Add third-person/proposition/current-turn contrast using typed inputs; do not restore phrase fixture or claim public fragment support. |
| `1ebc6d8ac2f5ba9c3561` | `test_that_resolves_prior_verified_proposition` | Select prior proposition and retain association with reference. `D:229`, `D:263`; direct probe passed selection/identity pair. | **U**, with old bindings representation migrated. Add typed reference-to-selected-expression assertion; public `that` composition remains missing. |
| `22e25b96ca44e4637599` | `test_orientation_projector_uses_focus_store` | Supplied direct store contributes expression and entity refs to `OrientationProjector`. Owner `src/cemm_authoritative_hybrid/cycle.py:529`; independent probe passed. | **U**. Add current-ABI direct-projector test. Active runtime instead preserves focus-record IDs (`F:3727`); do not substitute that test. |
| `27ba73e12b88ad9fe2eb` | `test_what_did_you_say_resolves_verified_system_speech` | Prior system content selected **and** returned as `("content", ref)` binding. Historical binding is fabricated by `_DialogueSession` (`test_discourse_reference.py:113`). Current resolver exposes `reference_ref`/`selected_ref`, not this query binding (`D:129`). | **O**. Separate typed resolver selection from actual speech-query content projection; add independent binding proof before mapping whole assertion. |
| `4618c9de8b3438873934` | `test_what_did_you_say_resolves_to_most_recent_system_speech` | Most recent previous system content beats older content. Exact direct-owner current test `F:3280` asserts latest expression and older alternative. | **C**, direct resolver only. Bind to this exact selection assertion, not public question support. |
| `6634463067f7cafa0051` | `test_resolution_bindings_contain_ref_to_resolved` | Returned dictionary equals `{"that": "prop:1"}`. Dictionary API retired; canonical resolution owns typed reference and selected identities (`D:129`, `D:139`). | **O**. Migrate to canonical identity-pair assertion; do not restore surface-keyed compatibility binding API. |
| `6d677dc551ceca07cc5b` | `test_person_constraint_filters_by_participant` | Second-person excludes user entries and selects system. `D:172`; exact contrast at `F:3280`, strengthened by `F:3341`. | **C**, explicit constraints/direct owner. Bind to those contrast assertions. |
| `8de40dd01498141881a5` | `test_unresolved_ref_returns_none` | No eligible candidates gives null selection and no binding. Empty result at `D:248`; `F:3341` explicitly asserts null selected ref, empty alternatives/proofs after filtering. | **C**, with current result shape. Bind no-candidate assertion; do not recreate retired `.bindings`. |
| `a5dea97d747501c03ddb` | `test_kind_constraint_filters_by_kind` | `kind="entity"` selects entity, not proposition. `D:204`; mixed-content direct probe passed. Existing foundation speech tests use content, not entity contrasts. | **U**. Add expression/entity mixed-row contrast. |
| `ac8ed838a7083c66f1e4` | `test_recency_constraint_limits_candidates` | `recency=1` considers only newest row. `D:229`; exact one-row probe passed. Existing `F:3341` proves related two/four-row window behavior. | **U**. Add explicit one-row window assertion; do not claim the differently parameterized test is automatically the exact successor. |
| `e1d049d841566398e976` | `test_alternatives_below_margin_are_preserved` | Latest selected; nonempty alternatives exclude selected. `D:257`; `F:3280` explicitly selects latest and preserves exactly old. | **C**, direct owner. Bind this narrow assertion; historical body did not prove every numerical margin boundary. |
| `ef3349ae724cbc5de2f5` | `test_person_first_filters_to_user` | First-person selects user despite newer system entry. `D:173`; independent probe passed. Existing checked-in foundation tests cover second-person, not this inverse contrast. | **U**. Add exact inverse-person contrast. |
| `fdf57c758cf49833fadd` | `test_what_did_you_say_does_not_resolve_user_speech` | Second-person resolution never selects user proposition; old body does **not** require successful speech answering. `D:172`; `F:3341` narrow window leaves only user/current records and asserts no selection. | **C**, negative direct-owner invariant only. Bind that exclusion assertion without promoting it to positive speech-query support. |

### Crosscut root causes

1. **Mapping failure is intentional proof honesty.** These wrappers currently reach no dialogue owner. Adding category-wide runners would restore false credit.
2. **Historical fake sessions are not runtime evidence.** They generate semantic hashes from text and use phrase checks/verification booleans. Retain useful semantic assertions through typed tests, not these fixtures.
3. **Focus storage/read support exists; normal admission and content integration do not.** Active ORIENT uses record identities (`R:324`, `R:442`), not expression content. Tasks 4–5 of `docs/superpowers/plans/2026-09-07-foundation-proof-implementation-plan.md` retain the writer/content-slot and response-continuity obligations.
4. **Goal arbitration has an unresolved semantic-policy change.** Earliest expiry is not numerical priority. The current label test also proves much less than its name suggests.
5. **Direct obligation-manager completion is not learning authorization.** Successor unit tests can preserve its bookkeeping invariants, but may not bypass the EFFECT/publication journal to manufacture acquisition proof.

The three **M** verdicts identify missing public-runtime requirements rather than failures demonstrated by the historical synthetic session itself. The **C** verdicts for reference selection deliberately claim only the direct-owner invariant actually asserted, never successful natural-language speech-query interpretation.

## Query, inference, epistemic admission, and learning failure audit

### Scope and verified results

Read-only audit of 48 wrappers. Actual predecessor bodies were recovered from `6b8fc23^`; they had already been deleted at `add3917`. No repository files, mappings, commits, or real stores were changed. This temporary report is the only authored file.

All 48 wrappers fail at `tests/r3_successor_contracts.py:35` before runtime execution. Those failures establish missing assertion-specific mappings, not 48 runtime defects.

Fresh verification: 26 selected current tests passed. The first run had 17 passes in 13.71 seconds: recursive query, no implicit atom-kind support, six admission scope cases, four public lexical lookup cases, exact lexical retrieval, signed alias publication on memory/SQLite, and two public learning-proposal no-effect cases. The second run had nine passes in 1.56 seconds with plugin autoload disabled: four ordered-relation proof cases, continuation lifecycle on memory/SQLite, frozen alias contract, default-deny publication, and durable unknown-query witness. Both runs used `-p no:cacheprovider -o addopts=`. They are selected current controls, not wrapper coverage or whole-suite proof.

Additional isolated-memory current-owner probes confirmed:

- Two-rule chaining returns SUPPORTED with all intermediate predicate/rule refs and no mutation.
- Seven-rule chaining incorrectly returns UNKNOWN after six rounds.
- Reviewed rule `source_ref` is omitted from proof sources; observation provenance survives.
- Repeated evaluations are equal, without proving inter-query caching.
- All five nested placement modes yield ATTRIBUTED and zero deltas.
- Untrusted observation yields CONTESTED.

These are owner-level probes, not public-surface inference or a demonstration that a public stale-pin request crosses the normal R3 boundary.

### Evidence dictionary and verdicts

All paths are relative to `C:\dev\cemm\.worktrees\unresolved-designation-r4\hybrid_mvp`.

| Key | Evidence path |
|---|---|
| C | `src/cemm_authoritative_hybrid/r3_cognition.py` |
| L | `src/cemm_authoritative_hybrid/r3_learning.py` |
| A | `src/cemm_authoritative_hybrid/r3_artifacts.py` |
| F | `tests/test_foundation_semantics.py` |
| RQ | `tests/test_r3_recursive_query.py` |
| AP | `tests/test_foundation_alias_publication.py` |
| AA | `tests/test_foundation_alias_authority.py` |
| LP | `tests/test_foundation_learning_proposal.py` |
| AC | `tests/test_foundation_automatic_continuation.py` |
| QW | `tests/test_foundation_query_witness.py` |
| EF | `tests/test_foundation_effect_currentness.py` |
| P6 | `docs/superpowers/plans/2026-09-07-foundation-proof-implementation-plan.md`, section **Task 6 — Repair measured search/retrieval bounds and confirm preservation**, paragraph beginning “Deeper independent query-owner probes” |

Verdicts: E = **exact-current-test**; I = **implemented-unproved**; M = **missing-defective**; O = **obsolete-shape-migration**; U = **unresolved-contract**. E means the stated narrow assertion has current executable evidence, not that the entire capability is complete. Line references record the inspected worktree snapshot.

### tests/test_query_engine.py — 10 wrappers

| Wrapper hash | Exact predecessor test | Invariant and current evidence | Verdict; smallest safe next action |
|---|---|---|---|
| `03f6705c78516c61d5fb` | `test_query_memoization_returns_same_result` | Historical body compares result identity/status, not cache hits. Current deterministic construction at C:703; isolated repeat returned identical results. C:513 caches nodes only within one evaluation. | I; add same-pin repeated-query equality assertion. Do not claim persistent memoization. |
| `1a25374d0e03ea86a7a7` | `test_meaning_description_is_composed_from_grounded_structure[what-expected1]` | Requires composed open_variable/query_projection, provenance, no static gloss. Current lexical branch C:635 returns designation targets, not form-contribution description. F:2547 proves interrogative source evidence only. | M; specify and test canonical form-description projection; do not substitute lexical target lookup. |
| `5ce43fa19074d3b15ca4` | `test_meaning_description_is_composed_from_grounded_structure[does-expected2]` | Requires binder/tense description with provenance. C:635 lacks that owner; retired query.py::describe_surface is not active runtime. | M; preserve binder/tense-description obligation in canonical query/response projection. |
| `6494fb26adb069b3b7e5` | `test_generic_family_rule_lowering_supports_marriage_with_trace` | Five generic lessons, pure preview, family inference, complete rule/source lineage. RQ:71 proves one preinstalled reviewed rule only. C:277 chains; C:340 keeps parent sources but discards lesson source_ref. | M; add independent canonical multi-lesson lowering/proof case and repair missing rule-source provenance. Do not reactivate raw-program observation/acquisition. |
| `8d08917fa702cb9b2fed` | `test_observe_records_facts` | Old QueryEngine.observe(raw_program) directly increments world revision. Current C:860 proposes deltas; EFFECT owns mutation. EF:343 tests atomic current world/effect advancement. | O; migrate valid fact-commit invariant to verified EVALUATE→EFFECT receipt; retire query-owner mutation expectation. |
| `b5d5258a6580209c1e4f` | `test_query_result_has_retrieval_receipt` | Old separate RetrievalReceipt carries memo key/rounds. Current A:354 embeds retrieval refs/rounds/pin; C:709 constructs them. F:5032 checks exact lexical retrieval provenance, not old receipt type. | O; assert current QueryResult retrieval lineage, exact rounds, pin, identity; do not restore legacy receipt ABI. |
| `bef2e803029d9c46f884` | `test_meaning_description_is_composed_from_grounded_structure[hi-expected0]` | Greeting identity plus description provenance/no dictionary gloss. C:635 offers designation lookup, not composed meaning description. F:2877 distinguishes retired traversal from genuine definition support. | M; add positive grounded greeting-description contract under current query/response owners. |
| `de6989568e516bea8aed` | `test_semantic_description_never_reads_internal_ref_name` | Historical body checks only static_gloss is None, not an adversarial arbitrary ref spelling. Active description capability remains absent; AA:421 protects alias-authority lexicalization, a different assertion. | M; add opaque-ref contrast to the real description owner once represented; absence of an answer is not successful description. |
| `ea9ed0001c37b54fc2f5` | `test_unknown_is_not_false` | No applicable evidence yields UNKNOWN/no proof. F:3007 [reversed] and F:2643 assert this through current owner; selected controls passed. | E; bind exact current no-evidence assertion after review. Keep P6 incomplete-search UNKNOWN defects separate. |
| `ef9d0b1bf1ba3fe1618e` | `test_existential_witness_is_proof_local` | Historical body permits UNKNOWN and mainly checks unchanged world revision; if proof exists, it requires transient witnesses. C:405 builds witness refs from selected bindings. F:2667 proves ordinary bound-query nonmutation, not existential handling. | I; add supported existential case asserting proof-local witnesses and unchanged stores. |

### tests/test_recursive_inference.py — 6 wrappers

| Wrapper hash | Exact predecessor test | Invariant and current evidence | Verdict; smallest safe next action |
|---|---|---|---|
| `1cb3a69be7ea10a25d66` | `test_recursive_inference_chains_multiple_hops` | Supported family answer with at least two applied rules. C:277 implements chaining; independent two-rule probe passed. RQ:71 contains only one rule. | I; add checked-in canonical multihop case with independent expected conclusion. |
| `677fb171a5df5a940bcf` | `test_recursive_inference_proof_has_semantic_refs` | Proof contains beginning/intermediate/final predicates. C:402 gathers involved predicates; two-hop probe preserved all three. RQ:71 does not assert them. | I; add exact multihop semantic-ref assertion, including intermediate nodes. |
| `b73425f4abf272047265` | `test_recursive_inference_proof_tracks_rule_applications` | Actual body requires nonempty applied rule refs with rule: identities. RQ:71 asserts exact applied rule tuple/proof; selected test passed. | E; map this narrow rule-ref assertion only, not complete recursive lineage. |
| `c29fdb6812129ace3e18` | `test_recursive_inference_source_refs_include_programs` | Despite name, body requires only nonempty proof sources. RQ:71 asserts observation source survives; selected test passed. C:340 drops reviewed rule source refs. | E for narrow body; retain separate missing lesson-source obligation, not broad all-program-sources credit. |
| `d08e2ebdad820295a190` | `test_recursive_inference_unknown_entity_is_unknown` | Unobserved entity remains UNKNOWN/no proof with rules present. F:3007 proves direct no-match; RQ:71 proves supported rule result; no current combined rule-present/no-match assertion found. | I; add unrelated-entity query against canonical multihop fixture. Do not accept budget-truncated UNKNOWN. |
| `e77fbfa5288e26050075` | `test_recursive_inference_with_unseen_synonym` | Historical fixture assigns progenitor to different concept:progenitor, then permits SUPPORTED or UNKNOWN: no synonym proof. tests/test_foundation_designation_consumer_successors.py:35 proves authenticated alias→same-target affordance inheritance, not inference. | O; replace misleading old shape with signed alias→same target→multihop proof, requiring SUPPORTED and unchanged pack. |

### tests/test_inference_bounds.py — 4 wrappers

| Wrapper hash | Exact predecessor test | Invariant and current evidence | Verdict; smallest safe next action |
|---|---|---|---|
| `1ca8392bbc811fda3616` | `test_inference_exhaustion_is_explicit` | Exhausted nonconverged closure must be BUDGET_EXHAUSTED with actual round count. C:286–358 never flags final-round incompleteness; seven-rule probe returned UNKNOWN/6. P6 records same defect. | M; add finite seven-hop exhaustion contrast and repair existing closure-completion reporting, retaining caps. |
| `2050e9fd20f68a19a91f` | `test_inference_exhaustion_receipt_records_rounds` | Actual rounds equal configured cap on exhaustion. C:287/C:712 preserve six rounds in probe, but status was wrong; no exact current assertion found. | I; add rounds assertion to corrected finite-chain exhaustion case, using current QueryResult ABI. |
| `c90a4b6a2a33eb6673de` | `test_inference_within_bounds_succeeds` | Converging supported rule produces proof within budget. RQ:71 proves reviewed one-hop inference under current release config; selected test passed. | E; map narrow within-bound success, not exhaustion or input-retrieval bounds. |
| `f6804898c50e7ae897b2` | `test_inference_exhaustion_has_no_proof` | Incomplete unsupported query must not fabricate proof. C:361 returns no proof without selected evidence; seven-hop probe had no proof but false UNKNOWN status. | I; assert no proof alongside corrected BUDGET_EXHAUSTED; empty UNKNOWN is insufficient exhaustion acceptance. |

The predecessor's existential recursive fixture also needs migration: current C:329 does not implement its $new proof-witness expansion. A finite over-depth chain tests exhaustion without restoring retired fixture machinery.

### tests/test_epistemic_admission.py — 13 wrappers

| Wrapper hash | Exact predecessor selector suffix | Invariant and current evidence | Verdict; smallest safe next action |
|---|---|---|---|
| `ea3d1eb00bf28f853d92` | `TestReportedSpeechDoesNotBecomeWorldTruth::test_reported_speech_placement_mode` | Legacy fake text parser makes Ada the occurrence source. C:758 detects reported content roots, while C:873 keeps outer situation source; canonical speech role should retain actual speaker. F:3070 [speech] checks no admission, not exact speaker/source distinction. | O; assert canonical reported speaker separately from outer evidential source, plus REPORTED placement. Do not restore fake phrase parser. |
| `647fedb72fbbcfbf2a87` | `TestReportedSpeechDoesNotBecomeWorldTruth::test_reported_speech_world_query_unknown` | Reported content must not become unqualified support. C:557 filters placement only when supplied; C:304 closure does not constrain premise placement. P6 records laundering; no-admission F:3070 cannot prove query isolation. | M; add direct reported-only and reported-premise derivation world-query contrasts; repair retrieval/closure placement ownership. |
| `f82ead85935f7cb8640d` | `TestReportedSpeechDoesNotBecomeWorldTruth::test_reported_speech_admission_is_attributed` | Reported occurrence receives ATTRIBUTED/policy provenance. C:904–911 implements policy:epistemic_attribution:v1. F:3070 checks retain-attribution, not exact admission row/policy. Direct scope probe passed. | I; add exact admission status/current-policy test; migrate retired policy spelling explicitly. |
| `be0bc997b98fb4dd9ace` | `TestNestedPlacementsRemainAttributed::test_nested_mode_is_attributed[believed]` | BELIEVED remains attributed, placement retained. C:493/C:758/C:904; isolated canonical-scope probe passed. | I; add exact believed-placement/admission/no-delta test. |
| `2fe822715d9bff6bdc8a` | `TestNestedPlacementsRemainAttributed::test_nested_mode_is_attributed[desired]` | DESIRED remains attributed. C:494/C:758/C:904; probe passed. | I; add desired-specific canonical-scope test. |
| `d73b27aab098023a9867` | `TestNestedPlacementsRemainAttributed::test_nested_mode_is_attributed[predicted]` | PREDICTED remains attributed. C:495/C:758/C:904; probe passed. | I; add predicted-specific canonical-scope test. |
| `86faa75790d71aaa138b` | `TestNestedPlacementsRemainAttributed::test_nested_mode_is_attributed[quoted]` | QUOTED remains attributed. C:491/C:758/C:904; probe passed. | I; add quoted-specific canonical-scope test, not arbitrary punctuation acceptance. |
| `6eef143e2a8dbd7da3fb` | `TestNestedPlacementsRemainAttributed::test_nested_mode_is_attributed[simulated]` | SIMULATED nested content remains attributed. C:489–490/C:758/C:904; both simulation-scope probes passed. Separate top-level SIMULATE semantics are not the same assertion. | I; add nested simulation admission test, not top-level no-effect smoke mapping. |
| `de74cf5c0852c48aa4b5` | `TestObservedClaimsWithEvidenceAreAdmitted::test_observed_with_evidence_is_admitted` | Old body admits any observed claim with nonempty evidence string. C:889 requires trusted observation plus eligible state; F:3070 positive/negative prove trusted admission proposals. | O; migrate to authenticated adapter evidence; retain rejection of arbitrary evidence strings. |
| `9837994441bbb5b0183d` | `TestObservedClaimsWithEvidenceAreAdmitted::test_observed_without_evidence_is_contested` | Untrusted ordinary observation stays CONTESTED. C:904–905; isolated untrusted probe passed. | I; add exact admission-row CONTESTED/current-policy test with untrusted situation. |
| `8240da7c2f121cbcfc14` | `TestCorrectionsSupersedeWithoutDeletingProvenance::test_correction_status` | Correction produces corrected admission/policy and retained occurrence. A:436/A:515 retain enum vocabulary; C:881 always sets supersedes_ref=None and C:488 has no correction placement handling. | M; add exact occurrence-targeted correction contrast and implement admission/provenance owner; enums are not behavior. |
| `b767ac63d32d8299b00e` | `TestAdmissionIsPolicyDerived::test_admission_carries_policy_ref` | Admission includes policy provenance. C:895/C:905/C:908 implement it; scope probes returned current policies. No exact current row-level assertion found. | I; assert nonempty exact policy identity on current admission artifact. |
| `df4e7f0c6066c9fc02cf` | `TestAdmissionIsPolicyDerived::test_admission_cannot_be_requested_by_token` | Historical body compares structured reported vs observed-with-evidence cases; no lexical override is supplied. C:889/C:904 structurally decide; F:3070 supplies corresponding contrasts. | E for structural contrast; map trusted-positive versus reported with explicit policy migration, not a separate lexical-attack claim. |

### tests/test_learning_distinctions.py — 7 wrappers

| Wrapper hash | Exact predecessor test | Invariant and current evidence | Verdict; smallest safe next action |
|---|---|---|---|
| `4d6ad497849e46c6dfea` | `test_one_pending_learning_obligation` | Second live unknown cannot create/renew another learning continuation. AC:826 checks one record, unchanged obligation revision across four turns, replacement after expiry. Selected memory/SQLite cases passed. | E; map active lifecycle invariant, replacing retired coordinator exception shape. |
| `59d62df8f6399e561544` | `test_designation_commit_consumes_plan` | Publication consumes once. Old body requires every retry to raise; AP:1246 proves original completion, same signed request returns exact receipt, changed grant rejected. Selected cases passed. | O; retain once-only mutation while explicitly migrating replay rejection to authenticated idempotent retry. |
| `60b5af589ecd1e402709` | `test_lookup_does_not_create_designation` | Lookup cannot invent alias/world fact. F:5013 checks exact lookup and unchanged full world facts/revision including unknown literal. Selected cases passed. | E; map narrow no-designation/world-mutation assertion. |
| `7e270e6990d7880d264d` | `test_no_public_install_rules` | Coordinator exposes no install/add-rule/authority mutation shortcut. L:366 exposes materialization only; LP:548 checks removed duplicate pending writer, not this exact API invariant. Old learning.py:594 is not active R3 authority. | I; add explicit current-coordinator API/ownership check; do not execute historical mutable authority helper. |
| `b7a1255e5e8232dfa402` | `test_untrusted_teaching_is_attributed_only` | Actual predecessor proves only planning does not publish; no teaching claim is executed. LP:664 proves public directive→proposal is no-effect and preserves pending/world; AP:662 proves default-deny. Selected controls passed. | E for no-publication body; keep separate genuine teaching-claim attribution test, not broad name-based credit. |
| `be58b79b365d977533c9` | `test_meaning_lookup_does_not_mutate` | Old direct ask asserts all store revisions unchanged. F:5013 preserves world truth; QW:107 permits durable query journal/continuation metadata. Selected controls passed. | O; distinguish pure query-owner read from full-cycle bookkeeping; retain world/authority nonmutation. |
| `ffb56b3b17f5ce2d5a7f` | `test_conversational_wording_cannot_select_reviewer_policy` | Policy independently configured, not text-selected. AA:186 verifies frozen linked contract; L:31 configures independent verifier; AP:681 rejects wrong signed policy/scope. Old spellings retired. | E; map linked-contract plus wrong-policy publication assertion with explicit identifier migration. |

### tests/test_synonym_acquisition.py — 8 wrappers

All eight actual bodies concern reviewed generic-rule publication into a new authority generation, despite the filename. Current authenticated existing-target alias publication at src/cemm_authoritative_hybrid/r3_effects.py:843 does not replace them. Historical learning.py:594 directly mutates authority dictionaries/generation and must not be reactivated to satisfy these wrappers.

| Wrapper hash | Exact predecessor test | Invariant and current evidence | Verdict; smallest safe next action |
|---|---|---|---|
| `d3129dc396cacffc2e8d` | `test_reviewed_generic_definitions_publish_one_linked_generation` | Five definitions publish at least five rules in one new linked generation, preserving compatibility. L:366 handles alias materialization; no equivalent canonical reviewed-rule generation publisher found. | U; retain acquisition obligation and define approved current generation-publication path before successor. Alias publication is not replacement. |
| `ae3ce54649dca81d1f24` | `test_one_invalid_definition_rejects_entire_acquisition` | Invalid definition rejects entire rule-generation acquisition, no partial generation. AP:785 tests alias rollback, not authority-bundle acquisition. | U; specify invalid canonical rule-bundle rejection at acquisition/link owner, retaining atomicity. |
| `512bcc3c6fba9795ed02` | `test_acquisition_requires_reviewer_authorization` | Generic-rule publication requires authenticated review. L:31/AP:662 implement review for existing-target aliases only. | U; bind review to eventual rule-acquisition contract; alias default-deny is not complete acquisition proof. |
| `07e5438a8190c02f528b` | `test_acquisition_requires_cap_learn` | Generic acquisition requires reviewed capability. AP:707 tests alias capability, not generic acquisition. | U; define current capability identity and enforce it on canonical acquisition publication; do not assume legacy cap:learn remains unchanged. |
| `dcac0e8e494facbd9d3f` | `test_acquisition_consumes_plan` | Successful rule-generation plan consumed once. AP:1246 proves alias consumption only; generic publisher absent. | U; specify acquisition transaction/idempotent receipt lifecycle before migrating replay expectations. |
| `448444eb09d013ea4ad4` | `test_acquisition_plan_mismatch_rejected` | Review for different generic acquisition plan cannot publish. AP:681 proves alias plan binding, not rule-bundle binding. | U; retain exact plan+bundle+parent-generation binding requirement for acquisition. |
| `5cd9e27e5bab778ace82` | `test_acquisition_preserves_compatibility_hash` | Compatible rule addition preserves model compatibility while generation changes. tests/test_foundation_designation_consumer_successors.py:65 instead proves alias does not change authority generation/content. | U; define/test reviewed rule compatibility under new generation publication; unchanged alias generation is wrong invariant. |
| `d335a36b78de5c78ae48` | `test_acquisition_conversational_wording_cannot_select_policy` | Generic acquisition contract/policy independently fixed. AA:186 concerns alias only; historical learning.py:537 accepts caller policy parameter. | U; resolve generic acquisition contract and policy source, then assert text cannot alter either. |

### Reporting boundaries

Passing small-query controls does not repair fact-256 truncation, hidden denial, placement laundering, six-round incompleteness, or direct query-owner stale-pin gaps recorded in P6. The stale-pin observation concerns direct evaluate_full/read ownership; this audit does not claim a public stale request bypasses normal R3 boundary validation. Historical generic acquisition obligations remain separate from authenticated existing-target alias publication.

**Post-audit repair status (September 8):** the fact/relevant-rule/proof reads now
use the existing bounded physical indexes inside one exact store snapshot;
incomplete work is `BUDGET_EXHAUSTED`, and placement plus reviewed rule-source
lineage survive closure. A subsequent quality review found an authority-side
variant of the stale-pin defect: reviewed publication could mutate the rule map
before changing its generation. Rule maps are now immutable per generation,
publication replaces the map, and QUERY rejects generation drift before cache
refresh or evidence access. The exact query owner gate passes. Twelve assertions
classified above as legitimate current-ABI migrations now have individual
successors; the description, observation-mutation, existential, speech-composition
and generic-acquisition rows remain separate work and were not mapped by this
repair.

## Runtime, response, restart and episode wrappers: 71-row read-only audit

Audit root: `C:/dev/cemm/.worktrees/unresolved-designation-r4/hybrid_mvp/`.
No repository files, authority, committed artifacts or real stores were changed. Tests used temporary stores; bespoke probes used in-memory stores. Existing working-tree modifications were preserved.

### Method and result boundary

Read the subtree AGENTS and approved foundation amendment. Recovered deleted cognitive/response/restart bodies from `6b8fc23^:hybrid_mvp/tests/…`; they are already absent at `add3917`. Recovered the two unlinked episode bodies from `62c57cb^:hybrid_mvp/tests/test_r1_episode_runtime_path.py` by assertion identity. Read surviving R1 and gap predecessors directly.

All these wrappers have the same immediate failure: `tests/r3_successor_contracts.py:30-36` has no audited runner for their category/assertion pairs. Five sampled wrappers reproduced that error before any runtime execution. The router correctly refuses to manufacture proof. Wrapper failure alone does not establish 71 runtime defects.

Verdicts: **O** = obsolete-shape-migration; **I** = implemented-unproved (implementation or probe exists, but no exact checked-in successor binding); **E** = exact-current-test candidate for the stated narrow invariant, not an authorized mapping change; **M** = missing-defective; **U** = unresolved-contract. When an old test contains obsolete setup/status assertions and a valid safety assertion, the row explicitly separates them. An O verdict never silently discharges the remaining safety obligation.

Actions: **migrate** means preserve lineage and obtain a reviewed current same-assertion interpretation/test, not restore fixture APIs; **add test** means an assertion-specific current test before mapping; **retain gap** means do not claim later-owner functionality. No mapping or implementation change was made.

### Evidence keys

All current paths below are relative to the audit root above. A key in a row expands to its exact path/line here.

- **RUN**: `src/cemm_authoritative_hybrid/runtime.py:514` requires the exact orientation/proposal/verification/R3 owners; `:578` runs the canonical path; `:589` invokes PROPOSE without generic exception swallowing; `:609` binds orientation/context receipt refs; `:674` runs R3; `:707` always records the R5 realization boundary for selected meanings; `:751` returns evaluation, effect and response artifacts; `:769` projects typed verification dispositions.
- **CYCLE**: `src/cemm_authoritative_hybrid/r3_cycle.py:553` finalizes exact artifacts; `:592` validates nonnegative integer durations; `:596` hashes identity independently of trace; `:606` optionally creates trace. `:157` rejects a realized surface before R5.
- **GREETING**: `tests/test_r3_r4_predecessor_regressions.py:194` is a passing public greeting test: selected proposal/meaning, six phase materials, response, exact R5 boundary, no world mutation, persisted no-effect journal. It does NOT assert RESOLVED or a readable surface.
- **LINEAGE**: `tests/test_r3_lineage_successors.py:66` passes: ORIENT transforms once, canonical six-phase result, PARTIAL and exact R5 boundary. `:23` passes: NO_EFFECT preserves world/fixed dimensions but may advance session/effect revisions.
- **BADPROGRAM**: `tests/test_r3_r4_predecessor_regressions.py:101` checks exact verifier rejection of an unknown designation slot; it is not a public incompatible-anchor phrase test.
- **EFFECT**: `src/cemm_authoritative_hybrid/r3_effects.py:808` is the R3 gateway owner. `tests/test_foundation_effect_currentness.py:343` passes atomic current world/effect advancement; `:389` passes stale-new-request rejection and same-process exact terminal retry; `:486` passes committed fact/proof/journal/full-pin preservation after actual SQLite reopen; `:572` passes pending-operation reopen/reconciliation then exact terminal retry. These tests do not assert that an arbitrary public phrase authorizes an operation.
- **RESP**: `src/cemm_authoritative_hybrid/r3_response.py:70` is frozen ResponseMeaning ABI 3; `:273` maps decision/effect status; `:298` maps typed discourse action; `:327` builds from authenticated evaluation/meaning/situation/effect; `:354` determines polarity and `:356` epistemic status. Surface-text-free round-trip passes in `tests/test_r3_learning_response.py:75`.
- **UNKNOWNRESP**: `tests/test_foundation_continuation_artifacts.py:592` passes: nonlearning response preserves exact source expression, decision, bindings, proofs, blockers, policies and unknown/positive/actual semantics. `tests/test_r3_no_program_as_meaning.py:256` passes the separate source-text isolation check.
- **GAP**: `tests/test_gap_matrix.py:235` invokes removed `HybridRuntime._status_from_gap` at `:250`; all ten non-RESOLVED parameter cases fail there. Current owners are RUN:769 (verification) and RESP:273 (decision/effect), not the generic exception mapper. `src/cemm_authoritative_hybrid/gaps.py` still owns typed gap classification, which alone does not prove CycleResult status routing.
- **BUDGET**: `src/cemm_authoritative_hybrid/r3_cognition.py:721` projects query budget exhaustion to DecisionStatus.BUDGET_EXHAUSTED; RESP:273 has no corresponding cycle-status branch and falls through to PARTIAL. An isolated call with a valid current NoEffectReceipt reproduced PARTIAL. This is output-status projection evidence, not yet a full public exhausted-query replay.
- **EP**: `src/cemm_authoritative_hybrid/episodes.py:281` bounds wire traversal; `:596` is immutable ABI-2 diagnostic episode; `:679` strictly decodes exact fields and bounds before reconstruction/hash; `:793` checks authority generation; `:820` calls the runtime; `:852` intentionally sets `meaning = None`, retaining diagnostic derivation rather than selected/verified gold. `tests/test_episode_generation_hard_cut.py:90` asserts that explicitly diagnostic shape; `:127` checks round-trip; `:172` and `:181` reject missing marker/unknown ABI. These are not proof of the deleted selected-VerifiedMeaning episode expectation.
- **PROBE**: one development runtime with in-memory stores, distinct session per surface, current linked authority. `hello`, `hi`, `greetings` -> PARTIAL/selected/acknowledge; name/alias/reordered-name questions -> PARTIAL/selected/clarify. Most older door, Ada, pronoun, correction, history, capability and learning phrases -> UNSUPPORTED/abstained/no response. The mixed conditional question raises ORIENT ModeProjectionError (`QUERY,SIMULATE`). All completed probes had world delta zero. These observations describe the actual old surfaces, not independent competency acceptance.
- **ARTPROBE**: current in-memory greeting plus exact CycleFinalizer replay with the SAME semantic material and trace on/off passed stable cycle identity, unchanged phase material, six integer-duration receipts versus empty trace, and exact ORIENT/PROPOSE/VERIFY context-ref binding. Also passed ResponseMeaning frozen assignment rejection and a deliberately raised PROPOSE programming exception propagating unchanged. The same-material qualification matters: separate real turns legitimately advance session/effect revisions.
- **EPPROBE**: current diagnostic EpisodeBuilder round-trip passed; missing field, extra field, modified review provenance and 65 proposal rows were rejected with fields/hash/bound errors. No checked-in combined strict-codec runner was identified.

### Cognitive-loop predecessors (30)

Here `C::` means `tests/test_cognitive_loop_e2e.py::` at `6b8fc23^`. These tests used phrase-independent legacy fixtures. A word in a test name is not the tested semantic invariant.

| Wrapper suffix | Predecessor (historical line) | Actual old invariant; current evidence | Verdict; minimal safe action |
|---|---|---|---|
| `173c654f2b620a70fc62` | C::TestGreetingAndOperationalCondition::test_greeting_produces_resolved_cycle (154) | Fixture hello gives RESOLVED, six traces, nonempty basic artifacts. GREETING/LINEAGE now prove real selected greeting with PARTIAL and exact R5 gap. | O; migrate fixture completion to truthful current boundary, retain surface gap. |
| `7ef04063a04af8833514` | C::TestGreetingAndOperationalCondition::test_operational_condition_has_revision_pin (160) | Only nonempty authority generation and nonnegative world revision, not online knowledge. RUN:609/751; public old phrase abstains but retains pin. | I; add exact pin assertion on current public cycle; do not label it operational-condition knowledge. |
| `4b9d01eec01554c58a47` | C::TestNamesAndAliases::test_name_query_produces_response_meaning (173) | Fixture RESOLVED plus proposition ref and answer action. Current PROBE yields clarify, not name answer; RESP:327 owns response. | O; migrate fixture shape; keep genuine name-answer acceptance separate/unproved. |
| `061076ac8035b501bcbe` | C::TestNamesAndAliases::test_alias_query_preserves_semantic_refs (180) | Only RESOLVED and non-null response; no alias/ref-equivalence assertion. PROBE gives selected clarify. | O; migrate narrow lifecycle test; no alias-composition credit. |
| `c18205d9c0f40deb8080` | C::TestReorderedQuestions::test_reordered_question_same_cycle_structure (192) | Both fixtures RESOLVED and six traces; no expression-equivalence comparison. PROBE gives PARTIAL/clarify for both; RUN owns structure. | O; migrate lifecycle status; add independent meaning-equivalence test if claiming reorder support. |
| `2ab331d5cc04d7bcd286` | C::TestAtomicMeaningLookup::test_atomic_surface_produces_cycle[hi] (207) | RESOLVED plus orientation, no lookup result. PROBE hi selects greeting/PARTIAL; GREETING covers analogous actual greeting. | O; migrate narrow atom-cycle expectation; no lookup proof. |
| `389bab3bb934932a6895` | C::TestAtomicMeaningLookup::test_atomic_surface_produces_cycle[what] (207) | RESOLVED plus orientation only. PROBE abstains/UNSUPPORTED. | O; test typed unresolved boundary; do not force standalone interrogative to resolve. |
| `71cd05f2b1cf13d72b58` | C::TestAtomicMeaningLookup::test_atomic_surface_produces_cycle[does] (207) | RESOLVED plus orientation only. PROBE abstains/UNSUPPORTED. | O; test typed unresolved boundary, not fixture success. |
| `74266f64499fe015c1b5` | C::TestAtomicMeaningLookup::test_newly_learned_alias_produces_cycle (212) | Processes greetings once; no preceding learning or pack comparison; only RESOLVED/proposal. PROBE selects seeded greeting. | O; retire misleading learning interpretation; authenticated unseen-alias tests are a separate obligation. |
| `faaf36e1601c7306d355` | C::TestModality::test_simulation_mode_cycle (224) | Fixture RESOLVED/orientation, never checks SIMULATE or no mutation. PROBE raises ORIENT mixed-mode error. | O; migrate smoke; separately investigate reviewed mixed conditional-question mode ownership, not infer simulation proof. |
| `9536463b82ad4c736e8a` | C::TestModality::test_query_mode_cycle (229) | Only RESOLVED/non-null response, no mode assertion. PROBE door query abstains. | O; migrate fixture lifecycle; independent state-query contract remains separate. |
| `f30dd96a383dcb1f702d` | C::TestFamilyInference::test_family_lesson_acquisition_and_marriage_query (241) | Five fixture lesson cycles have proposals; sixth query has response. Explicitly does not assert acquisition or inference result. PROBE mixed selected/abstained, zero world delta. | O; no family-inference/acquisition credit; use independent reviewed lesson/query acceptance. |
| `3e9c0f82c70d10847ce9` | C::TestAttributedSpeech::test_attributed_speech_does_not_become_world_truth (268) | RESOLVED/six traces only; explicitly delegates epistemic placement elsewhere. PROBE abstains. | O; migrate smoke, preserve real attributed-world-truth protection in its actual owner tests. |
| `c40d59f24966f4fa8bd1` | C::TestAttributedSpeech::test_attributed_denial_under_contrast (275) | RESOLVED/six traces; no contrast or polarity assertion. PROBE abstains. | O; no scope/denial credit; independent contrast acceptance required. |
| `a6877b3557b842cee518` | C::TestWhatDidYouSay::test_what_did_you_say_produces_cycle (287) | RESOLVED/non-null response, no prior speech setup or retrieval assertion. PROBE abstains. | O; migrate smoke; actual speech-history contract requires prior verified speech. |
| `4ddeb418d2556ef7d962` | C::TestDemonstratives::test_demonstrative_produces_cycle (299) | RESOLVED/orientation only; no referent context. PROBE abstains. | O; retain unresolved referent; independently test grounded demonstratives. |
| `998c38e96c4506267f43` | C::TestDemonstratives::test_that_demonstrative_produces_cycle (304) | RESOLVED only; no referent assertion. PROBE abstains. | O; do not map a focus-store unit test as public phrase success. |
| `e0fc12f50525a8aa7d0f` | C::TestCorrection::test_correction_produces_cycle (315) | RESOLVED/six traces, no corrected prior proposition. PROBE abstains. | O; migrate smoke; preserve correction/provenance acceptance separately. |
| `1312031edfe593132fe2` | C::TestStateIntervals::test_past_state_query (327) | RESOLVED only, no temporal facts/bindings. PROBE abstains. | O; no past-state proof; independently specify temporal interval acceptance. |
| `346d127a52d319a4df50` | C::TestStateIntervals::test_current_state_query (331) | RESOLVED only, no current-state witness. PROBE abstains. | O; no current-state proof; independent query/evidence test needed. |
| `630ff30ab8ec8b014d0b` | C::TestCapability::test_capability_query_produces_cycle (358) | RESOLVED, orientation and capability_summary not None; no permission/executability answer. PROBE abstains. | O; migrate lifecycle; exact capability query must be tested independently. |
| `12b14e6f836c432edc1d` | C::TestDenial::test_denial_produces_gap_receipt (371) | Injected legacy effect raises PermissionDenied -> permission/POLICY gap and DENIED cycle. Current RUN requires gateway protocol; RESP maps typed denied decisions, not exception strings. | O; add current public denied-operation receipt/response test; classifier smoke alone is insufficient. |
| `7c8a7603e86ed244d114` | C::TestSuccessfulOperation::test_successful_operation_increments_world_revision (398) | Fixture world revision advances, RESOLVED, effect OR evaluation exists; no permission proof. EFFECT:343 proves actual authorized atomic increment; old public phrase abstains. | O; migrate to reviewed permitted operation; do not credit lower-level gateway test as old public phrase success. |
| `868520aaf5f0d5d8601c` | C::TestAdapterFailure::test_adapter_failure_produces_gap_receipt (412) | Injected old adapter exception -> ADAPTER gap/owner and OPERATION_FAILED. Current EFFECT/RESP use typed adapter results. | O; add exact current adapter-failure public propagation test without restoring old callback signature. |
| `792373ec0692ff7b4f7d` | C::TestLearningContinuation::test_learning_continuation_produces_cycle (439) | One fixture phrase, RESOLVED/six traces; no pending obligation or second answer turn. PROBE abstains. | O; no continuation credit; use exact persisted-query/answer lifecycle tests separately. |
| `cf71b98771079a5ffa86` | C::TestPolysemy::test_polysemous_surface_produces_cycle (464) | RESOLVED/orientation, no multiple senses or settling margin assertion. PROBE bank abstains. | O; preserve independent polysemy test, not fixture resolution. |
| `1f9c96bd25efd3eac759` | C::TestIncompatibleMultiAnchor::test_incompatible_multi_anchor_produces_cycle (476) | Injected negative legacy verification result -> UNSUPPORTED/verification gap. BADPROGRAM verifies canonical rejection but not this public route/anchor defect. | O; test typed current rejected-batch CycleResult routing; retain exact failure cause. |
| `31ec79e7f8c1d6efaaf8` | C::TestRealizationFailure::test_realization_failure_produces_gap_receipt (506) | Injected realizer exception -> REALIZATION/TRAINING gap and REALIZATION_FAILED. RUN:707/CYCLE:157 expose unadmitted R5, never invoke this callback. | O; retain R5 gap; realization-failure integration remains a future owner obligation. |
| `2e2b21568a0be2e3afc5` | C::TestNoHiddenFallback::test_missing_owner_is_not_clarification (602) | Injected MissingOwner at effect -> implementation gap/OPERATION_FAILED. RUN:524 now rejects absent required owner at activation; no clarification fabricated. | O; preserve activation-error/no-surface invariant with current protocol test, not old status conversion. |
| `2f5fe16467edee9c42fa` | C::TestCommittedEffectSurvivesRealizationFailure::test_committed_effect_remains_journaled (627) | Only world revision increased despite REALIZATION_FAILED/gap; did not inspect journal. EFFECT:486 proves persistence, but not later response-failure integration. | I; add injected failure after real gateway commit and verify world/journal survives; keep R5 unsupported boundary explicit. |

### R1 cognitive/restart successors (13)

`R::` means current `tests/test_r1_cognitive_restart_successors.py::`. Every body also calls `_assert_r1_cut` (line 77): exactly three phases, no evaluation/effect/response, and `contract:r3:evaluate`. RUN now requires R3 at construction, so none is a current executable runtime fixture unchanged.

| Wrapper suffix | Predecessor (line) | Actual invariant; current evidence | Verdict; minimal safe action |
|---|---|---|---|
| `5c62c09726631356d222` | R::test_r1_cycle_result_retains_canonical_orientation (100) | Exact Orientation plus ORIENT output refs; obsolete R1 cut. RUN:609 and ARTPROBE preserve artifact/ref core. | O; migrate exact type/ref assertion to ABI-3 cycle, not three-phase stop. |
| `117636df56c528015c99` | R::test_r1_cycle_result_retains_canonical_proposal (110) | Exact ProposalResult and PROPOSE output ref; R1 cut. RUN:589/625, LINEAGE and ARTPROBE. | O; current ABI-3 exact proposal/ref successor. |
| `e2effe1dca9264717301` | R::test_r1_cycle_result_retains_canonical_verification (117) | Exact selected VerificationBatch with meaning; R1 cut. GREETING/LINEAGE retain selection, RUN:597 exact type. | O; migrate selected-batch artifact without restored R1 boundary. |
| `37b5fe8ca6b81d8e435d` | R::test_r1_cycle_result_defers_evaluation_to_exact_later_owner (125) | No evaluation; R3-evaluate gap sourced from meaning. RUN:696 now evaluates; LINEAGE proves R5 boundary. | O; explicit reviewed change from R3 stop to R5 stop; do not claim original absence still holds. |
| `2ac780c8d0d83aa505e5` | R::test_r1_cycle_result_has_no_response_before_evaluation (133) | In R1 cut, response/realization absent. Current rejected path RUN:647 preserves absence; selected path creates typed response before R5. | O; split early-rejection absence from selected typed response; add exact early-path test. |
| `26c3172feb21ecab47de` | R::test_r1_cycle_trace_is_observational_with_bounded_durations (140) | Traced/untraced R1 turns have same ID/material, integer durations, empty disabled trace. CYCLE/ARTPROBE prove SAME-material invariant, not equal separate real turns. | O; migrate to same-input/material comparison and current six-phase duration contract. |
| `70660ec884ab5d824ecf` | R::test_r1_restart_preserves_world_revision_without_admitted_effect (153) | SQLite reopen preserves world revision exactly zero and R1 cut. GREETING preserves world; EFFECT:486 preserves actual reopened pin. | O; add no-effect public reopen test preserving world without denying valid journal advancement. |
| `79703ee34fd786bdb486` | R::test_r1_restart_preserves_effect_revision_without_admitted_effect (169) | Reopen preserves effect revision exactly zero. Current NO_EFFECT must persist/advance effect revision (LINEAGE/GREETING). | O; replace zero-effect-revision expectation with exact persisted receipt/revision preservation. |
| `873b881d81e9b56ee8b7` | R::test_r1_restart_preserves_every_revision_pin_dimension (185) | Full RevisionPin equality across reopen after R1 cut. EFFECT:486 passes full pin equality after real commit. | O; preserve exact pin core via current scenario; remove R1-cut fixture assertions explicitly. |
| `6da536de8c4c1ceb8564` | R::test_r1_restart_preserves_stable_revisions_across_multiple_cycles (202) | Three R1 cycles have equal pins, reopen same pin. Current real turns persist session/effect changes. | O; test monotonic allowed changes plus exact final reopen pin, never demand all live-turn pins equal. |
| `d4770b48f1d95b0a2161` | R::test_r1_consecutive_cycles_preserve_revision_pins_without_effect (219) | Three R1 pins equal, no effect. GREETING/LINEAGE explicitly allow persisted NO_EFFECT journal. | O; migrate fixed/world stability versus allowed session/effect progression. |
| `02c8a3b9911859bf0353` | R::test_r1_no_stale_revision_reentry_precedes_unadmitted_effect (230) | Only two normal R1 cycles equal pin/three phases; no stale state injected. EFFECT:389 is genuine stale-new-request protection, not ORIENT retry proof. | O; preserve real stale/currentness law separately; do not claim predecessor tested restart-at-ORIENT. |
| `f4441486b4cb53c5c9ee` | R::test_r1_cycle_result_after_reopen_contains_only_admitted_artifacts (240) | Reopened R1 runtime yields basic artifacts/three traces, no later artifacts. RUN/GREETING show current six-phase artifacts. | O; add actual reopen ABI-3 cycle artifact test; no R1 owner omission. |

### R1 runtime-path successors (9)

`P::` means current `tests/test_r1_runtime_path.py::`. `_runtime` at line 96 omits required R3, and its old orientation helper exposes only `orient`, not the current exact evidence/orient-turn protocol. Merely adding one dummy owner would not repair these fixtures.

| Wrapper suffix | Predecessor (line) | Actual invariant; current evidence | Verdict; minimal safe action |
|---|---|---|---|
| `23ab4f6d79fd50bbf874` | P::test_r1_disabled_effect_owner_does_not_advance_world_revision (222) | Two R1 cycles world=0 and effect_receipt=None; assertion identity misleadingly says increment. GREETING now has actual NO_EFFECT receipt with unchanged world. | O; migrate to world nonmutation plus persisted no-effect proof, not artificial increment. |
| `496f6e6d7dbfe89cf019` | P::test_r1_injected_program_reaches_every_admitted_owner_then_stops (199) | Exactly three phase materials/PARTIAL/R3-evaluate gap. LINEAGE now reaches six and R5. | O; reviewed six-phase/current-gap successor. |
| `9eff2e971f959a40f142` | P::test_r1_phase_receipts_use_semantic_names_not_stage_numbers (231) | Serialized result has no stage substring; phases exactly ORIENT/PROPOSE/VERIFY. RUN/CYCLE retain named phases; GREETING checks six. | O; add exact serialized no-stage assertion on current six-phase result. |
| `5b46fb3213f566e27ea3` | P::test_r1_programming_exceptions_propagate_without_shape_adaptation (180) | PROPOSE RuntimeError should propagate. Actual old test fails at MissingOwner(r3_owner), before injected error. RUN:589 and ARTPROBE verify current behavior. | I; rewrite fixture on current runtime and map only after checked-in exact test passes. |
| `b4d0d67b952a4c0d71fe` | P::test_r1_receipts_bind_exact_orientation_and_context_refs (273) | Object identity and first-three receipt input/output refs; unpacks exactly three materials. RUN:609 and ARTPROBE verify exact refs on current cycle. | O; migrate first-three indexing/current ABI while preserving reference identity assertions. |
| `b0e60c540b0dfdbf9db0` | P::test_r1_selected_cycle_has_exact_later_owner_gap_until_r3 (242) | Selected R1 cycle has R3-evaluate gap, not the original identity's gap-free success. RUN:707/LINEAGE explicitly expose R5. | O; reviewed gap-owner migration, never map to gap-free success. |
| `cb8ad9a437e9ab6f1679` | P::test_r1_selected_meaning_stops_at_exact_later_owner_gap (139) | Exact proposer/verifier object flow, R1 ABI result, three phases, no later artifacts/R3 gap. Current RUN keeps exact owner flow but continues R3. | O; preserve owner-flow assertions in current six-phase test, retire R3-stop conjunction. |
| `8e5b08c7cdc04e85c277` | P::test_r1_trace_is_observational_and_cycle_identity_is_stable (170) | Separate old no-write turns equal ID/material; trace toggle only. CYCLE/ARTPROBE prove same-material trace isolation. | O; migrate to controlled same-state input; real session progress must not be suppressed for test equality. |
| `8bf5349ade7a922ffb28` | P::test_r1_trace_off_preserves_selected_cycle_material (211) | PARTIAL/selected/empty trace/exactly three materials. ARTPROBE retains selected material with trace off and six phases. | O; exact six-phase trace-off successor, not RESOLVED claim from metadata. |

### Gap/status wrappers (10)

All predecessors are `tests/test_gap_matrix.py::test_every_cycle_status_is_reachable[CycleStatus.X]` at line 235. They test a STATIC typed-exception-to-status mapping, not a runtime cycle. All ten currently fail at removed mapper line 250. Each status parameter is a distinct obligation although the wrappers discard that parameter and pass the same category/assertion pair.

| Wrapper suffix | X / actual old mapping | Current owner/evidence | Verdict; minimal safe action |
|---|---|---|---|
| `b650ca7318ae30576ef7` | AMBIGUOUS: reference/training gap | RUN:808 maps ambiguous verification batch; GAP old reference-gap routing is not this owner. | O; parameter-specific typed ambiguous current-cycle test, no generic router smoke. |
| `ca9460a2cf8641c70a6b` | BUDGET_EXHAUSTED: performance/runtime gap | BUDGET: genuine typed budget decision currently falls through RESP to PARTIAL. | M; first add exact exhausted-query response-status test; repair earliest response status projection if confirmed in full path; do not restore old mapper. |
| `829c535a40e12927bf97` | CONFLICT: authority/authority gap | RESP:289 projects DecisionStatus.CONFLICT, not generic SemanticConflict exceptions. | O; current conflict Decision/effect response test; preserve distinct authority evidence. |
| `43ba22a660043d569a04` | DENIED: permission/policy gap | RESP:281/285 maps typed effect/decision denial. | O; assert current denied-operation decision/effect/cycle propagation specifically. |
| `2fb6478bb03f0913af9e` | OPERATION_FAILED: implementation/runtime gap | RUN:524 propagates missing owner at activation; RESP:277 handles typed failed/stale effect. | O; distinguish programming/activation failure from typed operation failure; reviewed routing migration required. |
| `3d4560bbd2cba740ad1d` | PARTIAL: designation/data gap | RUN:776 abstention now UNSUPPORTED; RESP:295 uses PARTIAL for other supported no-effect paths. | O; test typed designation frontier separately; do not silently preserve old source/status equivalence. |
| `8d46f2d4f8a82b11d71c` | REALIZATION_FAILED: realization/training gap | RUN:707/CYCLE:157 disable normal realization before R5; no current invoked realizer route. | U; retain future realization failure obligation and current R5 boundary; no invented active runner. |
| `cf1ea0498148f19cc17c` | RESOURCE_UNAVAILABLE: resource/data gap | RESP:279/287 distinguishes typed unavailable effect/decision. | O; add exact resource-failure propagation rather than generic exception mapper. |
| `087fa7741523c766b339` | UNKNOWN: evidence/data gap | RESP:291 and UNKNOWNRESP prove semantic unknown, not arbitrary EvidenceGap exception routing. | O; migrate exact typed unknown decision/response interpretation with parameter retained. |
| `06b6c58163e318ee4963` | UNSUPPORTED: verification/runtime gap | RUN:793 rejected batch -> UNSUPPORTED; BADPROGRAM tests lower verifier only. | O; add exact rejected-batch public CycleResult routing test. |

### Response meaning (5)

`S::` means historical `tests/test_response_meaning.py::TestResponseMeaningPrecedesLanguage::` at `6b8fc23^`. Its old EvaluationResult/EffectResult and ResponseMeaning field names are retired; RESP ABI 3 is the owner.

| Wrapper suffix | Predecessor (line) | Actual invariant; current evidence | Verdict; minimal safe action |
|---|---|---|---|
| `977ebbadf7168d551a31` | S::test_denied_status_maps_to_deny_action (115) | Typed denied input -> deny, negative, denied epistemic status. RESP:298/354/367 implements it; no exact current combined assertion test identified. | I; add canonical denied EvaluationBundle/NoEffectReceipt builder test with all three assertions. |
| `989bedf3d53929a6a3e8` | S::test_response_builder_cannot_inspect_input_words (104) | Actually only unknown input -> unknown discourse/epistemic fields; never varies/poisons source text. UNKNOWNRESP:592 passes exactly those semantic assertions; source isolation has separate :256 test. | E; bind only audited narrow unknown-response assertions; do not claim the old body proved all text isolation. |
| `3dcf1ce99d768a4a387e` | S::test_response_meaning_has_all_fields (86) | Old builder fills ref/mode/status/proposition/polarity/modality/epistemics/action/bindings/sources. RESP ABI-3 schema + round-trip exists; UNKNOWNRESP checks different scenario. | O; explicit field/meaning migration and one complete supported-answer fixture, no blind old-field adapter. |
| `ed763dea9d599d0845d8` | S::test_response_meaning_is_frozen (126) | Assignment raises (very broad Exception matcher). RESP:70 frozen and ARTPROBE FrozenInstanceError passed. | I; checked-in exact FrozenInstanceError test on real ABI-3 response. |
| `a7535250c38166db9516` | S::test_response_meaning_precedes_language (75) | Nonempty response/proposition plus six trace names and EVALUATE duration; no actual temporal-order spying. RUN:696-759, GREETING and ARTPROBE preserve current typed response/trace. | O; migrate proposition_ref to exact response expression/lineage and R5 boundary; do not overstate name query support. |

### Restart lifecycle (2)

`T::` means historical `tests/test_restart_e2e.py::` at `6b8fc23^`.

| Wrapper suffix | Predecessor (line) | Actual invariant; current evidence | Verdict; minimal safe action |
|---|---|---|---|
| `a3c7e653cf515659a7a6` | T::TestRestartCommittedEffect::test_committed_effect_remains_journaled_after_restart (225) | Only exact world revision survives reopen; it explicitly does not inspect facts/journal. EFFECT:486 passes this narrow invariant and stronger actual fact/journal/full-pin persistence. | E; map only after reviewed fixture migration; describe strengthened proof honestly, not as prior journal coverage. |
| `9737c160af466856feaf` | T::TestRestartIdempotency::test_restart_does_not_re_invoke_completed_effect (138) | One adapter call before reopen, revision survives, ONE NEW request after reopen makes second call. No same-request retry assertion. EFFECT:389 proves terminal retry in-process; :572 pending restart/reconcile, but exact two-distinct-public-cycles sequence is not checked there. | I; separate new-request lifecycle successor from explicit terminal-retry-after-reopen acceptance; do not call predecessor true replay-idempotency proof. |

### Episode wrappers without supersedes_node_id (2)

Recovered assertion-identity bodies are in `62c57cb^:hybrid_mvp/tests/test_r1_episode_runtime_path.py`; the missing predecessor link itself needs lineage repair after the assertion is reviewed, not invented ancestry.

| Wrapper suffix | Recovered predecessor (historical line) | Actual invariant; current evidence | Verdict; minimal safe action |
|---|---|---|---|
| `3e9b731d0d9a6f6936bc` | test_r1_episode_codec_is_strict_bounded_and_authority_bound (97) | Reject foreign authority, missing/extra keys, modified review hash; 65 proposals fail before stable_ref. EP retains those owners; EPPROBE covers fields/hash/bound but not the complete historical spy assertion. | I; restore lineage link and add one current diagnostic strict-codec test including authority mismatch and prehash-bound spy. |
| `fdc717e6c26ffcec5598` | test_r1_episode_builder_uses_process_and_separates_derivation_from_meaning (34) | process(trace=False), selected derivation tied to VerifiedMeaning/coverage, frozen/hash-valid ABI2, no R3 artifacts, not independent training gold. EP:852 now deliberately drops selected meaning; current diagnostic tests explicitly assert empty meaning. | O; reviewed diagnostic-vs-authentic episode migration required; retain derivation/meaning separation and provenance without reactivating quarantined gold or claiming selected-meaning retention. |

### Verified commands and observations

All pytest commands used `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider -o addopts=`.

1. Five sampled wrappers: **5 failed**, each only `unmapped successor assertion` in router line 33. No runtime call reached.
2. Bounded current/ancestor checks: **14 passed, 11 failed**. Passing: public greeting; both lineage-successor tests; both R3 learning/response tests; source-text isolation; all six foundation-effect-currentness tests; exact nonlearning unknown response; RESOLVED enum-only gap case. Failing: old R1 injected-programming-error fixture at MissingOwner(r3_owner), plus all ten old static status-mapper cases at missing `_status_from_gap`. This did not run full regression.
3. Twenty-nine current public-surface probes used only in-memory stores. Results are summarized in PROBE; no completed probe mutated world state. These were diagnostic probes, not training inputs or gold.
4. Same-material trace/artifact, frozen response, exception propagation and four episode rejection probes all passed in memory. No test source was modified to obtain these observations.
5. Isolated status projection reproduced `DecisionStatus.BUDGET_EXHAUSTED + valid NoEffectReceipt -> CycleStatus.PARTIAL`. Treat this as a concrete response-owner gap requiring full-path acceptance, distinct from the ten stale `_status_from_gap` failures.

### Common root causes and safe ordering

1. Missing explicit assertion runners, intentionally fail-closed; never reinstate cached category smoke credit.
2. Three incompatible test eras: legacy always-success fixture runtime, R1 three-owner cut, current exact R3 owner with unadmitted R5 realization. Their shapes/statuses cannot be blended.
3. Inflated scenario names: the cognitive phrases did not test meaning, temporal state, learning, attribution, polysemy or inference. Preserve their actual lifecycle assertions; require independent meaningful acceptance before claiming those capabilities.
4. Shared assertion identity discards ten gap parameters. Future routing must execute every distinctly governed case or carry parameter identity explicitly; ten aliases to one convenient passing status are not evidence.
5. NO_EFFECT is persistent journal/session progress, not absence of effects storage. Old all-zero/all-equal pin assumptions are obsolete; world nonmutation and exact restart receipt preservation remain required.
6. Exact lower-level effect/query/response tests are useful evidence but cannot be relabeled as public dialogue or authorized readable-output acceptance. R5 is still an explicit boundary.
7. Genuine candidates beyond mapping cleanup: budget status collapse; mixed conditional/question ORIENT ambiguity on the historical surface; missing exact post-commit-response-failure and terminal-retry-after-reopen integration; current selected-meaning episode retention is intentionally unavailable in the diagnostic builder and requires reviewed interpretation, not a fallback.

Safe next step is reviewed assertion-by-assertion migration plus targeted current-owner tests. No restoration of legacy callback/result APIs, forced RESOLVED statuses, automatically admitted aliases or realizer fallback is justified by this audit.

### Post-audit query integrity hardening

The first green query gate concealed three additional integrity defects. Linked
rule maps protected only their outer dictionary while nested clauses remained
mutable; persisted derived facts could inject extra proof-source refs; and an
unknown fact stance was treated as denial. The repaired owner recursively freezes
rule clauses, reconstructs derived sources only from reviewed rules and validated
parents, and accepts only exact `support`/`deny` stances. Its rule-head index is
also populated at owner activation rather than by the first ordinary query.
Eight memory/SQLite regression cases pass, the combined query/budget/public suite
passes 104 cases, and the expanded query/authority/learning suite passes 149.
This closes the query-integrity review findings; it does not close the separate
reported-speech/source-ownership or R4/R5 obligations.

A second adversarial pass found that the outer rule property itself was still
replaceable under an unchanged generation/content hash, and that malformed rule
stances bypassed persisted-fact validation. The repaired authority exposes
generation, full content identity and an immutable rule map as one read-only
snapshot. Query rejects same-generation mapping drift; rule construction and
defensive query parsing require exact `support`/`deny`.

Final re-review then reproduced a TOCTOU race: publication between the pin check
and rule-index refresh could evaluate new rules under the old store pin. QUERY
now captures one immutable authority snapshot and one evaluation-local immutable
cache bundle, with a lock-free O(1) normal hit and a locked rare rebuild, and
checks identity again before return. The focused query/authority rerun passes 164
cases. Inspection also confirmed that the predecessor generic acquisition path
has no public store-generation reactivation boundary. It now fails explicitly
before lowering or mutation; it is not credited as completed generic acquisition.

## Recommended execution within the existing foundation plan

1. **Query truth and truthful failure reporting first.** Repair pinned relevant reads, support/denial completeness, placement, rule-source proof and exhaustion propagation together through their existing owners. Keep configured bounds.
2. **Source-local speech/composition next.** Correct reported addressee and explicit child-actor ownership, then measure and deduplicate only semantically equivalent search states with equivalent future legal continuations.
3. **Finish the usable diagnostic response loop.** Preserve incomplete content, clarify through a legitimate gap/response path, and integrate verified response/focus continuity. Do not make absence of a selected meaning look like a successful EVALUATE.
4. **Close test lineage alongside each owner repair.** Use the individual rows to retain valid assertions, migrate obsolete fixture/result shapes, and register exact current cases. Do not rebuild 159 wrapper-sized tests or revive category-wide cached runners. Parameter coverage must remain explicit.
5. **Keep scope distinctions visible.** Existing-target alias publication is not generic rule/identity acquisition. Numeric-priority versus earliest-expiry arbitration needs documented contract resolution, not a secretly relabeled test. These obligations must not be silently credited or allowed to expand the approved alias work.

This order is a diagnostic recommendation for Tasks 4–6 of the existing foundation plan, not a replacement master or new release gate. R4/R5 admission remains frozen. No implementation, test deletion, mapping change, commit, push, merge or root adoption occurred in this audit.
