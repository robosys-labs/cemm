# CEMM v3.5 Phase 10 — Epistemic and claim architecture

**Predecessor:** verified Phase 9 factor-graph composition over the reviewed Phase 7–8 substrate
**Patch base:** `390610c0f17f83d309d8d7e83bd63ce5b68c03a7` — verified Phase 9 endpoint
**Status:** implemented and phase-verified; not public-runtime-authoritative
**Authority:** append-only attributed claims plus independently authorized epistemic admission

## 1. Boundary

Phase 10 implements the epistemic boundary required by Core Loop stages 8–9 and the durable claim/admission records needed by stage 13. It does **not** implement event transition inference, state mutation, capability effects, response policy, NLG, or runtime cutover.

The central invariant is:

```text
grammatical claim
!= grounded claim
!= attributed proposition
!= epistemic admission
!= actual-world state transition
```

Each boundary requires its own record, evidence, and authorization.

## 2. Subphases

### 10A — Structural claim occurrence compiler

`ClaimOccurrenceCompiler` consumes selected UOL and an explicitly classified claim application. It validates claim structure from the exact schema revision and ports:

- exactly one proposition-storage content port;
- exactly one required identity-contributing source port;
- any additional referent ports remain separately validated participants/audiences;
- the proposition remains in a distinct attributed/reported context;
- the matching event occurrence is preserved as claim-occurrence identity.

It does not branch on a named claim predicate, language word, or ontology type.

### 10B — Append-only claim history

Durable `ClaimHistoryRecord` supports:

- assert;
- correct;
- retract;
- supersede.

Corrections/retractions never delete prior claims. Source lineage is immutable: one source cannot rewrite another source's claim history. Revision supersession cannot change the identity, source, context, action, or target of the historical event.

### 10C — Independent source/evidence assessment

`SourceAssessment` keeps cycle-local policy inputs separate, while durable `SourceAssessmentRecord` snapshots the exact assessment used for an admission. The normalized record keeps separate dimensions for:

- identity;
- authority;
- reliability;
- access quality;
- bias risk;
- evidence lineage.

No fused “trust score” is authoritative. Policy thresholds evaluate the dimensions independently. Direct admission stores exact revisioned source-assessment revision pins so the policy decision remains auditable after restart.

### 10D — Explicit epistemic admission

`EpistemicAdmissionRecord` is a separate revisioned authority. Direct actual-world support/opposition requires:

- an explicit durable `authorization_ref`;
- exact policy reference;
- source attribution;
- exact durable source-assessment revision pins;
- evidence;
- proof;
- target context;
- permission/sensitivity;
- independent policy thresholds.

Missing authorization preserves attributed content rather than admitting it. Other failed gates defer admission.

### 10E — Source-local admission retraction

Retraction is itself a proof-bearing, explicitly authorized record. It may only retract an admission for the same proposition/context and overlapping source lineage. The pure projector repeats this source-local check even before commit validation so uncommitted/malicious candidates cannot erase another source's evidence.

### 10F — Four-state truth projection

`FourStateTruthProjector` derives:

```text
supported
opposed
both
undetermined
```

from the latest active independent admission records.

`both` can only emerge from independent support and opposition. A single admission record is forbidden from encoding `both`.

### 10G — Admission-lineage knowledge projection

A `KnowledgeRecord` may be projected only from active admitted support/opposition. It retains exact admission refs in `support_lineage_refs`. Cross-context authority is recognized by resolving those first-class admission records; metadata never decides whether knowledge may cross contexts. Undetermined/attributed-only content creates no actual-world knowledge record.

### 10H — Atomic persistence and verification

New normalized storage authorities:

- `claim_history_records`;
- `source_assessment_records`;
- `epistemic_admissions`.

They use SQLite schema version 3 and the existing Phase-4 deterministic codec/store/GraphPatch/CAS boundary. Older schema version 2 databases are rejected rather than silently opened with missing Phase-10 tables. Claim and admission patches are separate. Neither patch may contain `STATE_DELTA` or `CAPABILITY_DELTA` operations.

## 3. Phase 7–8/9 drift corrections preserved

Phase 10 depends on, and does not weaken, the prior hardening:

- no named semantic-ref literals in grounding/composition/epistemic kernel code;
- no magic metadata flag as executable claim-recognition authority;
- no implicit actual-world context default in cognitive-stage entrypoints;
- no provisional-only identity presented as resolved;
- no lexical predicate mapped to an arbitrary existing event occurrence;
- no construction-type/instance collapse;
- no opaque grounding score substituted for factor evidence;
- no realization preference in meaning selection.

## 4. Deliberate deferrals

Phase 10 does not make CEMM v3.5 “complete” or runtime-authoritative.

Still deferred:

- Phase 11 event transition contracts/effect preview/commit;
- generic inference beyond the explicit epistemic projection implemented here;
- impact/importance/goals/operations;
- multilingual NLG and realization verification;
- legacy authority removal/runtime cutover.

A Phase-10 `KnowledgeRecord` is epistemic support/opposition, not permission to mutate referent state. State effects still require the later event-transition admission/proof path.

## 5. Exit gates

Phase 10 is phase-complete only when all of the following pass:

1. claim occurrence and proposition context remain attributed;
2. same-context pseudo-attribution is rejected;
3. grammar alone never admits truth;
4. explicit policy + authorization + proof can admit support/opposition;
5. source authority/reliability/access/bias remain independently gated;
6. independent support/opposition derives four-state `both`;
7. source-local retraction preserves other sources;
8. cross-source retraction fails safe even before durable validation;
9. corrections/retractions are append-only;
10. knowledge retains exact admission lineage;
11. direct admission/retraction without durable authorization is rejected;
12. one record cannot encode `both`;
13. typed codecs/normalized storage round-trip claim history, durable source assessments, and admissions;
14. claim/admission patches never emit state/capability effects;
15. deterministic package compilation remains byte-identical;
16. source-assessment authority/reliability/access/bias evidence remains revisioned and durable;
17. effectively retracted admissions cannot be reused to synthesize knowledge;
18. all prior Phase 0–9 architecture/competence gates remain green.
