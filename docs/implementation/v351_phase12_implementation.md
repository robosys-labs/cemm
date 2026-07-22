# CEMM v3.5.1 — Phase 12 exhaustive implementation + Phase 9–11 corrective review

Baseline reviewed: `d871615e8e7152bd38a599832c2830107557a87b` (`main`, merged Phase 10–11).

## Canonical contract

Phase 12 is implemented as the first **CSIR-native conversational output kernel**, not as a string-response layer.

Required flow:

`Response CSIR → clause/discourse projection → role/reference realization → morphology → linearization → preservation proof → surface → emission authorization → observed-output discourse commit`

The implementation preserves these architectural boundaries:

- CSIR remains the sole semantic substrate.
- Response policy selects semantic response acts, never canned answer strings.
- English is confined to exact language-projection authority.
- Realization cannot invent participants, facts, causal claims, certainty or completed operations.
- Every deterministic realization transform carries exact rule/lexical/morphology/linearization pins.
- Cheap semantic preservation proof is mandatory; independent round-trip is additive and can be required by risk/channel transforms.
- Channel authority and disclosure authority remain separate.
- Only observed emission enters output-discourse memory; emission never means recipient acceptance or world truth.
- `NO_RESPONSE_REQUIRED` is an explicit semantic action and does not manufacture an empty/placeholder utterance.
- Legacy `ResponseUOL` and legacy realization records remain migration/storage compatibility only and are not canonical runtime authority.

## Phase 12 implementation

### 1. CSIR-native semantic response layer

New `cemm/v350/response/csir_v351.py` implements all required response families:

- `ANSWER_QUERY`
- `REPORT_STATE`
- `REPORT_RELATION`
- `REPORT_EVENT`
- `ACKNOWLEDGE_TARGETED_CLAIM`
- `REQUEST_CLARIFICATION`
- `CORRECT_PRIOR_OUTPUT`
- `QUALIFY_UNCERTAINTY`
- `REPORT_CAPABILITY`
- `ASK_LEARNING_QUESTION`
- `NO_RESPONSE_REQUIRED`

Added exact contracts:

- `ResponseFamilyAuthority`
- `ResponseAuthorityMapV351`
- `ResponseSourceBinding`
- `ResponseCSIRCandidate`
- `ResponseDecision`
- `ConversationalGoalCandidate`
- `ConversationalGoalDecision`
- `ResponseReportIntent`
- `ResponseCorrectionIntent`
- typed `ResponseBuildFrontier`

No response object contains a surface string.

### 2. Exact minimum response authority

`minimum_authority_v351.py` builds deterministic, content-addressed candidate/release artifacts for each response family:

- semantic definition;
- exact semantic ports;
- operational profile;
- explicit `COMPOSE` use authorization;
- explicit `REALIZE` use authorization;
- competence case refs.

Importing the module does **not** activate authority. The exact records must exist in the pinned immutable `AuthorityGeneration`.

### 3. Stage-15 conversational semantic obligation bridge

`ConversationalGoalBridgeV351` supplies only the Phase-12 alpha obligations needed before the later general goal/utility phase exists.

It supports:

- grounded query answer;
- unresolved/ambiguous/partial clarification;
- epistemically unknown answer qualification;
- targeted claim acknowledgement;
- typed report intents;
- typed prior-output correction intents;
- learning questions;
- explicit semantic silence.

It never chooses wording.

### 4. Stage-18 Response CSIR builder

`ResponseCSIRBuilderV351`:

- compiles exact response definitions through `SemanticDefinitionCompiler`;
- validates exact authority generation/snapshot;
- attaches execution authority;
- requires typed closure proof for executable response graphs;
- canonicalizes semantic classes;
- binds exact query proof/source lineage;
- freezes referenced session semantics by both semantic and exact fingerprints before Stage 19;
- fails to typed frontiers when required response authority or semantic source is missing.

Reports and corrections are real semantic intents, not unused enum values.

### 5. English realization authority

`realization/english_v351.py` provides a reviewed, content-addressed projection package with:

- response-family realization rules;
- exact output lexicalization bindings;
- exact application realization frames;
- exact semantic-port ordering per frame;
- exact morphology pins;
- exact linearization pins;
- exact realization use authorization;
- package content hash covering rules, authorizations, lexicalizations and frames.

The realizer handles:

- literal answers;
- participant/provisional referents through safe session reference surfaces;
- exact lexicalized categorical/state terms;
- simple exact semantic applications through reviewed per-definition frames;
- semantic-source dereferencing for reports/corrections with frozen source fingerprints.

It deliberately does **not** invent universal subject/object order, conjunction wording or scope linearization. Missing exact authority yields a frontier.

### 6. CSIR-native preservation proof

`realization/proof_v351.py` replaces the canonical runtime verifier path with an exact CSIR-native proof model.

Coverage includes:

- terms;
- variables;
- applications;
- bindings;
- qualifiers;
- scope embeddings;
- coordinations;
- root semantics.

Proof lineage preserves:

- context;
- permission;
- audience;
- target refs;
- source bindings;
- source semantic/exact fingerprints;
- qualifiers;
- scope embeddings.

Verification is replayed against the **cycle-pinned** `AuthoritySnapshotV351`, never `store.current_authority_snapshot()`.

### 7. Mandatory exact emission governance

`output/runtime_v351.py` implements an in-process text channel adapter without implicit authority.

Emission requires:

- semantic-preservation PASS;
- exact active channel contract pin;
- one exact typed `DisclosureAuthorizationGrantV351` selected under the cycle-pinned authority snapshot;
- exact durable policy/competence substrate pins backing that grant;
- channel match;
- language allowance;
- payload-size allowance;
- idempotency identity;
- Stage-20 effect authorization receipts.

A channel contract cannot double as disclosure authority. The disclosure grant is a separate content-addressed auxiliary authority artifact with explicit channel, context, permission, audience and language scope. Stage 20 independently re-validates the typed grant against the cycle-pinned `AuthoritySnapshotV351`, verifies that all of its exact durable substrate pins were supplied to the effect boundary, and refuses ambiguous/missing grants. The effect boundary also requires the exact disclosure grant ref/content hash in its protected-disclosure request metadata.

The actual pinned channel contract is exposed to the round-trip policy before authorization, so channel transformations can force independent semantic re-analysis.

### 8. Observed output discourse

`OutputDiscourseCommitterV351` commits only after an `EmissionObservationArtifact` exists.

It records:

- semantic response graph;
- surface candidate identity;
- output evidence;
- system/output anchors;
- a common-ground **proposal**.

It does not infer receipt, agreement, acceptance or truth.

## Phase 9–11 corrective review and fixes

### P9-11-01 — local grounding prior was promoted to resolved identity

Stage 3 explicitly documents its selected assignment as a soft/local prior, but Stage 8 reused it as resolved identity.

**Fix:** bounded grounding alternatives are carried through deterministic composition; Stage 8 marks identity resolved only when the mention is structurally singular. A Stage-3 preferred alternative is at most `PROVISIONAL`.

### P9-11-02 — deterministic composer ignored projected referent/state inputs

The Phase-10 baseline discarded `referent_projections` and `state_space_projections`.

**Fix:** `ProjectionAwareDeterministicCSIRComposer` makes projection availability part of branch admissibility and carries all bounded coherent grounding assignments to canonical CSIR collapse.

### P9-11-03 — epistemic context collapsed to `actual`

Stage 8 re-abstraction could erase `reported`, `hypothetical`, `quoted`, `planned`, `desired`, `fictional` and `counterfactual` placement before admission.

**Fix:** exact CSIR context qualifiers are re-abstracted into explicit `SemanticContext` records; non-actual contexts are preserved and admission policy blocks silent actual-world admission.

### P9-11-04 — event structures were never re-abstracted

Stage 8 emitted `events=()` regardless of stable event CSIR.

**Fix:** exact `EventAuthority` maps definitions/participant ports to cycle-local `EventOccurrenceV351` records while retaining the full CSIR graph.

### P9-11-05 — non-durable session participants could be labeled durable

**Fix:** durable identity is now checked against actual durable `REFERENT` storage instead of being inferred from participant role.

### P9-11-06 — minimum discourse wrappers had no exact re-abstraction authority bundle

**Fix:** `minimum_discourse_authority_v351.py` supplies content-addressed query/correction/definition/greeting/request/retraction wrapper definitions and exact semantic-slot pins. Candidate defaults have zero runtime force until their exact pins are promoted into the pinned generation.

### P9-11-07 — query recency could become lexical-ref ordering

**Fix:** session/query deduplication preserves insertion/turn recency. Budget truncation therefore retains newest semantic evidence, not lexicographically greatest IDs.

### P9-11-08 — yes/no query absence could be conflated with false

**Fix:** open-world behavior is explicit: support → true, opposition → false, neither → unknown, support+opposition → contradiction frontier.

### P9-11-09 — prior system output was unavailable to semantic follow-up

**Fix:** bounded prior output graphs are queryable as `system-output-occurrence` proof sources. They can answer questions about what CEMM said/meant but are never treated as world belief or common-ground acceptance.

### P9-11-10 — partial meaning could disappear without a response obligation

**Fix:** partial stable propositions generate explicit clarification targets; unresolved query goals inspect discourse/frontier evidence and select clarification rather than fabricated certainty.

### P9-11-11 — output/reference memory was not separated from world belief

**Fix:** session memory now has separate bounded records for reference surfaces, prior outputs and events. Output memory is Stage-21/observed-emission owned, not Stage-9 belief.

### P9-11-12 — safe referent realization could leak internal IDs

**Fix:** output referents use only evidence-backed `ReferenceSurfaceEntry` values. Internal referent IDs are never fallback text.

### P9-11-13 — realization proof authority was ambient/current instead of pass-pinned

**Fix:** exact proof verifier receives the Stage-0 `AuthoritySnapshotV351`; authority changes after orientation cannot repin an in-flight response.

### P9-11-14 — legacy proof coverage was incomplete for canonical CSIR

**Fix:** scope embeddings and coordinations are mandatory coverage, and CSIR tuple structures are handled directly.

### P9-11-15 — channel transforms could evade round-trip policy

**Fix:** Stage 20 consults exact active channel metadata before deciding whether independent round-trip is required.

## Runtime wiring

The apply patch changes canonical defaults to:

- Stage 5: `ProjectionAwareDeterministicCSIRComposer`
- Stage 6: deterministic Phase-10 dynamics bridge
- Stage 7: deterministic attractor stabilizer
- Stage 8: hardened discourse/event/context builder
- Stage 9: hardened epistemic coordinator
- Stage 10: grounded query/proof engine with beliefs/events/output occurrences
- Stage 13: bounded session commit
- Stage 15: conversational semantic goal bridge
- Stage 18: `ResponseCSIRBuilderV351`
- Stage 19: `EnglishCSIRRealizerV351`
- Stage 20: exact proof + channel-aware verification + guarded emission
- Stage 21: observed output discourse committer

Signed/injected services can replace these slots; there is no legacy semantic fallback.

## Test additions

The Phase-12 suite covers:

- all required response families exist;
- Response CSIR precedes surface realization;
- preservation proof replay under pinned authority;
- missing/stale projection authority fails closed;
- scope/coordination mandatory proof coverage;
- hypothetical context isolation;
- session recency independent of lexical refs;
- partial meaning → clarification;
- exact package content addressing;
- lexical/application-frame authority;
- Stage-3 local grounding prior not promoted to resolved identity;
- prior output queryability without belief admission;
- response source fingerprint freezing;
- separate channel/disclosure authority.

Acceptance tests intentionally assert semantic graphs, bindings, response families and proof decisions rather than exact English wording.

## Validation status

Performed on this bundle:

- AST parse of all Python payloads: PASS
- `compileall` of full bundle: PASS
- apply-script syntax: PASS
- JSON/status/manifest generation: PASS

Not performed here:

- full repository pytest suite;
- full M2 web/runtime conversation suite;
- performance/concurrency suite;
- authority boot/release activation tests against the user’s deployment database.

Reason: this environment cannot clone the repository (`github.com` DNS is unavailable) and the GitHub integration remains read-only for branch/file writes. The patch is therefore baseline-locked and fail-closed; it does not mark `CORE_ISSUES` items VERIFIED automatically.

## Promotion requirements

Before marking Phase 12 verified:

1. Apply to exact baseline or re-review drift.
2. Publish exact response/discourse/English realization authority into a new immutable authority generation after competence review.
3. Configure an exact active text channel contract plus a separately reviewed `DisclosureAuthorizationGrantV351` whose exact pin is present in the immutable authority generation and whose durable substrate pins are available.
4. Run Phase 9–12 tests and full acceptance suite.
5. Run the M2 semantic conversation suite.
6. Run adversarial preservation tests: omitted qualifier, added certainty, stale authority pin, changed source graph, channel transform, referent-ID leak.
7. Run concurrent session-cycle tests and authority-generation race tests.
8. Only then update `CORE_ISSUES.md` verification status.
