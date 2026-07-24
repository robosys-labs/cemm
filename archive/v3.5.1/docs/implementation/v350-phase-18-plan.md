# CEMM v3.5 Phase 18 — Output Discourse and Common-Ground Authority

## 1. Objective

Make emitted system output a first-class semantic event that is referable, auditable, correctable, permission-scoped, and capable of changing common ground **only after emission authorization succeeds**.

Phase 18 closes a major loop invariant:

```text
internal Response UOL
!= generated surface candidate
!= verified surface
!= emitted discourse event
!= common-ground commitment
```

Each transition requires its own exact authority record.

---

## 2. Governing laws

1. **No emission, no common-ground mutation.** A planned/verified response that was never emitted cannot become shared discourse history.
2. **Surface is not semantic authority.** Persist emitted semantic UOL and exact realization/verification lineage; transcript strings are evidence/rendering only.
3. **Every output commitment has an exact target.** Acknowledgements, answers, warnings, refusals, operation reports, clarifications, and silence decisions remain target-bearing.
4. **Emission authorization is separate from realization success.** A semantically round-tripping candidate may still be blocked by permission, sensitivity, channel, policy, staleness, or operation-result changes.
5. **Common ground is epistemic/discourse state, not truth.** The system saying `P` does not make `P` true; it creates a system discourse act/claim and possibly a shared-attribution commitment.
6. **Corrections preserve history.** A later correction supersedes or opposes prior output commitments without deleting the emitted event.
7. **References resolve semantically.** “that,” “why?”, “for what?”, “you said…”, and ellipsis must bind output proposition/event/goal targets, not transcript substrings.
8. **Permission cannot widen on output.** A response derived from narrower data cannot become public/common-ground authority without explicit authorization.
9. **Silence is auditable.** Authorized no-output is represented as a decision with reason/target/policy lineage, not an absence interpreted as success.
10. **Restart preserves discourse identity.** Emitted output and common-ground state rehydrate deterministically from durable records.

---

## 3. Required durable records

### 3.1 `EmissionAuthorizationRecord`

Pins:
- exact `ResponseUOLRecord`;
- exact `SurfaceCandidateRecord`;
- exact passing `SemanticRoundTripRecord`;
- latest applicable goal decision;
- channel/session/audience context;
- permission/sensitivity policies;
- literal-policy authorization when applicable;
- operation-result/reconciliation pins when output reports an operation.

Hard gates:
- response still current;
- surface round-trip passed;
- no semantic additions/losses;
- permission/sensitivity allowed for channel/audience;
- mandatory qualification retained;
- literal policy exact and in scope;
- no stale operation result;
- no invalidated dependency.

### 3.2 `EmissionRecord`

Represents what was actually emitted.

Fields:
- emission ref;
- authorization pin;
- response UOL pin;
- surface candidate pin;
- channel adapter/correlation refs;
- actual emitted surface fingerprint/bytes ref;
- audience refs;
- timestamp;
- delivery status/uncertainty;
- context/permission/sensitivity;
- revision lineage.

The recorded surface fingerprint must correspond to the authorized candidate. Channel transformations that can alter semantic content require re-verification.

### 3.3 `OutputDiscourseActRecord`

Durable semantic discourse occurrence:
- speaker ref = system/self referent;
- addressee refs;
- discourse-act schema/application pin;
- content proposition/event/application refs;
- response-goal refs;
- acknowledgement target refs;
- operation-result refs;
- emission pin;
- evidence/proof refs;
- context/time/permission.

### 3.4 `OutputCommitmentRecord`

Represents what the system has committed to having said/asserted/offered/asked, not what is objectively true.

Separate dimensions:
- proposition/content ref;
- commitment force;
- attribution = system;
- common-ground proposal status;
- acceptance/acknowledgement evidence;
- correction/supersession lineage;
- scope/permission/time.

### 3.5 `CommonGroundRecord`

A revisioned projection over discourse participants/context:
- proposition/event/goal/ref target;
- participant set;
- status such as proposed/shared/disputed/retracted/superseded/unknown;
- exact supporting discourse/emission pins;
- opposing/correction pins;
- confidence only where semantically meaningful;
- context/time/permission.

Common ground never bypasses ordinary truth/knowledge authority.

### 3.6 `OutputReferenceAnchorRecord`

Indexes referable semantic output objects:
- emitted proposition/event/application;
- response goal;
- operation result;
- discourse act;
- acknowledgement target;
- source response UOL;
- salience/order/time/audience context;
- permission.

This becomes the semantic substrate for later reference resolution.

### 3.7 `OutputCorrectionRecord`

Pins:
- prior output discourse/commitment/common-ground records;
- replacement/opposition semantic content;
- correction evidence;
- new emission/discourse act;
- invalidated projections.

History remains immutable.

---

## 4. Components

### 4.1 `EmissionGate`

Sole authority for whether a verified surface may leave the system.

Must revalidate immediately before emission:
1. latest Response UOL still exact;
2. latest goal decision still exact;
3. round-trip PASS exact;
4. candidate surface unchanged;
5. privacy/permission/channel scope;
6. policy/safety constraints;
7. operation-result freshness where relevant;
8. mandatory qualifications preserved.

### 4.2 `ChannelEmissionAdapter`

Mechanical transport only.

Contract describes:
- channel capabilities;
- maximum payload/format;
- transformation behavior;
- delivery acknowledgement semantics;
- idempotency/correlation;
- privacy/security scope.

It may not rewrite semantic content for convenience.

### 4.3 `OutputDiscourseCoordinator`

After actual emission evidence:
- creates output discourse occurrence;
- binds exact response goal/content/target;
- records system commitment;
- creates reference anchors;
- proposes common-ground updates.

### 4.4 `CommonGroundCoordinator`

Applies discourse-relative common-ground policy.

It must distinguish:
- system emitted `P`;
- user received `P`;
- user acknowledged `P`;
- participants mutually treat `P` as shared;
- `P` is epistemically supported/true.

These are not equivalent.

### 4.5 `OutputReferenceResolver`

Uses semantic anchors, discourse structure, recency/salience, type compatibility, and context.

Forbidden:
- substring matching against transcript;
- “last sentence” as semantic identity;
- guessing target when ambiguity remains.

Ambiguity produces a typed reference frontier.

### 4.6 `OutputCorrectionCoordinator`

Corrections/retractions:
- preserve original emission;
- add new correction discourse event;
- supersede/oppose output commitments;
- recompute common ground;
- invalidate downstream response/reference/materialized views;
- retain audit lineage.

---

## 5. Stage integration

```text
Phase 16 ResponseUOLRecord
 -> Phase 17 SurfaceCandidate
 -> Phase 17 SemanticRoundTrip PASS
 -> Phase 18 EmissionAuthorization
 -> channel emission
 -> delivery evidence
 -> EmissionRecord
 -> OutputDiscourseActRecord
 -> OutputCommitmentRecord
 -> CommonGroundCoordinator
 -> reference anchors
 -> next cycle context
```

No pre-emission artifact is allowed to masquerade as emitted discourse.

---

## 6. Output semantics

### 6.1 Answers

Persist:
- question/query target;
- exact answer proposition/application;
- epistemic qualification;
- source response goal;
- emitted discourse act.

### 6.2 Acknowledgements

Require exact acknowledged target. `acknowledge()` with no target is invalid.

### 6.3 Clarification questions

Persist:
- exact unresolved frontier/variable;
- expected structural family;
- reason/information gain;
- emitted question discourse act.

### 6.4 Operation reports

Must pin observed/reconciled result, not planned/predicted effect.

### 6.5 Refusals/limitations

Persist the requested/blocked target and authorization reason without inventing unsupported rationale.

### 6.6 Silence

A selected/authorized silence goal yields an auditable no-emission outcome record, but **not** a fabricated normal `EmissionRecord` claiming content was sent.

---

## 7. Common-ground state machine

Suggested structural states:

```text
proposed
emitted_to_participants
received_evidence
acknowledged
shared
opposed
disputed
retracted
superseded
unknown_delivery
```

Transitions require evidence. Delivery acknowledgement alone does not prove semantic acceptance.

---

## 8. Privacy/security

- common-ground scope cannot exceed source permission;
- reference anchors inherit privacy constraints;
- private identity facets are not indexed into broader discourse scope;
- channel adapters must declare logging/retention/security constraints;
- emitted sensitive content must pin explicit authorization;
- replay/export must respect permission scope.

---

## 9. Invalidation

Invalidate downstream output projections when:
- Response UOL invalidated before emission;
- surface/round-trip invalidated;
- emission failed/unknown;
- output corrected/retracted;
- audience/context changed;
- permission revoked;
- operation result corrected;
- referenced semantic object superseded.

Never delete historical emissions.

---

## 10. Acceptance matrix

1. verified but un-emitted response never enters common ground;
2. failed round-trip cannot emit;
3. stale Response UOL cannot emit;
4. private source cannot emit to broader audience without authorization;
5. channel mutation that changes meaning is rejected/reverified;
6. emitted answer creates system discourse commitment, not world truth;
7. acknowledgement always resolves exact target;
8. ambiguous “that” against prior output produces reference frontier;
9. follow-up “why?” resolves prior semantic target/reason lineage;
10. operation report uses observed result, never predicted effect;
11. unknown delivery remains unknown, not emitted-success assumption;
12. correction preserves original output and supersedes commitment projection;
13. restart preserves output discourse/common-ground identity;
14. duplicate delivery/idempotent replay does not duplicate semantic discourse event;
15. silence is auditable without fake emitted content;
16. transcript-string changes that preserve semantic records do not break reference resolution;
17. permission revocation invalidates broader reference/common-ground projection;
18. output reference resolution is invariant to target-language paraphrase;
19. no legacy transcript heuristic is sole semantic authority;
20. all emitted commitments trace to exact goal/Response-UOL/realization/emission proof chain.

---

## 11. Performance/query-plan gates

Measure:
- emission-gate dependency revalidation;
- latest discourse/common-ground lookup;
- reference-anchor retrieval by context/type/time;
- correction invalidation fanout;
- restart rehydration;
- channel idempotency lookup.

Required indexes:
- emission correlation/idempotency;
- discourse context/time;
- commitment proposition/target;
- common-ground participants/context/status;
- reference anchor target/type/context/salience;
- correction source target.

---

## 12. Implementation sequence

### 18A — canonical output authority contracts
### 18B — durable emission authorization/journal records
### 18C — channel adapter contract
### 18D — EmissionGate hard checks
### 18E — actual emission evidence persistence
### 18F — output discourse act construction
### 18G — system commitment records
### 18H — common-ground state machine
### 18I — semantic output reference anchors/resolver
### 18J — correction/retraction/supersession
### 18K — privacy and permission propagation
### 18L — invalidation/restart rehydration
### 18M — adversarial/reference tests
### 18N — performance/query-plan proof
### 18O — cut over public discourse history authority

---

## 13. Exit gate

Phase 18 passes only when emitted output is semantically referable and auditable across restart, common ground changes only from evidence-bearing discourse events after emission authorization, corrections preserve history and invalidate projections, and no transcript string or pre-emission artifact acts as competing discourse authority.

---

## 24. Applied implementation amendments after the Phase 16/17 audit

The concrete Phase-18 implementation strengthens the original design in the following ways:

1. `EmissionGateAssessmentRecord` makes every hard emission gate durable and snapshot-pinned. An `ALLOW` authorization must depend on the exact passing assessment set; strings such as `passed_gates` are trace summaries only.
2. `ChannelAdapterContractRecord` is revisioned authority for channel mechanics, payload budgets, transformations, idempotency and acknowledgement semantics. Runtime adapter identity must match it exactly.
3. `LiteralEmissionPolicyRecord` is an explicit reviewed exception keyed by exact response-goal schema pins, language tag, surface SHA-256 and Response-UOL graph fingerprint. It cannot authorize a generic template family.
4. `SilenceOutcomeRecord` represents selected semantic silence without manufacturing a fake emission/discourse event.
5. The channel executor distinguishes `content_left_system`, channel acceptance, delivery confirmation and unknown delivery. Transport exceptions never imply success or failure.
6. An authorized surface whose textual bytes are changed by the channel fails closed and must return through realization/round-trip; the channel cannot silently become a paraphraser.
7. `OutputDiscourseActRecord` is created only from an actual `EmissionRecord`. Common-ground projections therefore cannot exist for content that never left the system.
8. `CommonGroundRecord` begins at `EMITTED`, `RECEIVED_EVIDENCE` or `UNKNOWN_DELIVERY`; it never jumps to `SHARED`. `ACKNOWLEDGED`/`SHARED` require later interaction evidence.
9. Output-reference ambiguity creates an explicit learning/reference frontier instead of a transcript-string guess.
10. Corrections preserve immutable emission/discourse history and supersede commitment/common-ground projections rather than rewriting the past.

### 24.1 Additional exit checks

Phase 18 is not complete until the following also pass:

- a semantic round-trip `PASS` without Phase-18 gate assessments cannot emit;
- a stale emission authorization cannot be journaled after any intervening store revision;
- an `UNKNOWN_DELIVERY` record cannot become `DELIVERED`, `ACKNOWLEDGED`, or `SHARED` without new evidence;
- literal output with a mismatched surface hash or Response-UOL fingerprint is denied;
- no-output/silence paths create no `EmissionRecord`, `OutputDiscourseActRecord`, or common-ground mutation;
- correction retains old emission bytes/evidence and creates explicit superseding projections;
- output reference resolution is invariant to transcript formatting changes.

### 24.2 Final hardening discovered during Phase-18 implementation review

11. **Observed unauthorized output is never erased.** If content leaves the process boundary but the observed surface differs from the authorized surface, or the channel reports a contradictory rejected-but-emitted outcome, CEMM persists an immutable `EmissionAnomalyRecord`. It is explicitly non-discourse authority: it cannot create normal commitments/common ground, but it preserves the real external side effect for audit, incident response and correction.
12. **Operation freshness comes from explicit Response-UOL source pins, not metadata hints.** Every operation result reported by the response must be an exact `RecordKind.OPERATION_RESULT` source pin. Every non-UNKNOWN result must have exactly one supplied reconciliation bound to that result.
13. **Acknowledgement is target-closed.** `acknowledgement_target_refs` must be a subset of the semantic targets of the exact selected target-bearing goals. A caller cannot attach a generic or unrelated acknowledgement after realization.
14. **Output speaker identity is dependency-pinned.** The discourse record keeps the semantic speaker ref, while the commit dependency graph pins the exact durable speaker referent revision used at emission time.
15. **Literal triggers are lineage-bound.** Literal policies must pin exact triggers that are present in the Response-UOL source/selected-goal lineage; an exact surface hash alone is insufficient.
16. **Round-trip proof is required.** A nominal `PASS` without durable proof refs is not sufficient for Phase-18 emission authorization.

These hardening rules extend the Phase-18 acceptance matrix with two explicit negative cases: a channel-side mutated emission must remain auditable without becoming authorized discourse, and arbitrary operation/acknowledgement/speaker lineage injection must be rejected.

## Final implementation-audit amendments

The implemented Phase-18 gate additionally requires:

- exact durable speaker and addressee referent dependencies on every normal output discourse act;
- structural channel-contract acknowledgement semantics (`delivery_ack_proves_recipient_receipt`) before transport delivery can initialize recipient-received common ground;
- candidate refs, not evidence refs, for ambiguous output-reference frontiers;
- correction replacement targets grounded in correcting-discourse roots and opposition targets grounded in exact prior commitments;
- internally consistent channel observations before any journal/output mutation;
- no synthetic exception/debug strings masquerading as durable evidence refs;
- at least one explicit audience for normal ALLOW/emission paths; intentional no-output uses `SilenceOutcomeRecord`.
- channel crash recovery is an explicitly reviewed query capability; it cannot silently become resubmission, and client-key idempotency is durable before submit.
