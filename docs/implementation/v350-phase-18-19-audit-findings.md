# CEMM v3.5 post-Phase-17 audit findings and Phase-18/19 hardening

Audited live substrate: `robosys-labs/cemm` branch `agent/v350-phases-0-3`, commit `e58f5f3fbd9d1146b32ab86f32be3e83d291de96` (`Add phases 16/17 patch`).

This audit treats architecture/core-loop authority boundaries as executable invariants. A bug includes any path that can reinterpret historical meaning, broaden authority, hide a side effect, reuse stale proof, create a competing semantic authority, or claim equivalence without exact lineage.

## A. Newly found predecessor bugs fixed in this bundle

### A1. Core-loop Stage-17 macro still advertised a second goal generator — FIXED
The detailed Stage-17 section had already become operation-outcome reconciliation/goal refresh, but the macro list still said `GENERATE_RESPONSE_GOALS`. That leaves two apparent generic goal authorities (Stage 15 and Stage 17). The patch makes Stage 15 the sole generic goal authority and renames macro Stage 17 to `RECONCILE_OPERATION_OUTCOMES_AND_REFRESH_GOALS`.

### A2. Phase-16 reconciliation could cross-wire a result and a different observed journal revision — FIXED
`OperationReconciliationRecord` previously pinned plan/result but not the exact observed journal revision whose terminal transition depended on that result. Under recovery/retry histories, reconciliation could consume a later journal state without proving it was the one produced by the exact result. The record now has `observed_journal_pin`, and commit/validation require the exact dependency edge from that journal revision to that result.

### A3. Phase-17 round-trip analyzer was identified only by strings — FIXED
A caller-supplied analyzer could become semantic verification authority through `analyzer_ref`/`analyzer_revision` alone. Added `SemanticAnalyzerContractRecord`; round-trip records pin it exactly, implementation identity and language support must match, and active contracts require competence cases.

### A4. ACTIVE overlay language records could self-authorize REALIZE — FIXED
`LanguageUseAuthority` accepted ACTIVE records without promotion lineage. That is valid only for immutable reviewed boot authority. Overlay/staged language records now require exact Phase-13 REALIZE promotion lineage.

### A5. Phase-17 reference-plan comparison ignored exact revision/fingerprint — FIXED
Candidate reference lineage compared refs rather than exact pins. It now compares exact `(kind, ref, revision, fingerprint)` identities.

### A6. No repository CI/status evidence exists for the current Phase-16/17 head — OPEN VERIFICATION GATE
GitHub exposes no combined status/check evidence for `e58f5f3f...`. This is not a runtime bug, but Phase 20 must not claim release completion until the full repository suite and performance gates run on the final exact commit.

## B. Phase-18 implementation bugs found during self-audit and fixed before handoff

### B1. Candidate exactness contained a tautological hash comparison — FIXED
The initial gate compared `sha(surface)` to itself. It now resolves the exact stored `SurfaceCandidateRecord` pin and compares the stored surface hash with the supplied candidate surface.

### B2. Channel-contract record permission was incorrectly treated as content permission scope — FIXED
Channel contract access metadata is not the same as semantic content audience scope. The permission gate now checks response/request/candidate content lineage and audience, leaving channel contract access to normal record authority/security handling.

### B3. Ordinary correction supersession was mislabeled as semantic opposition — FIXED
Correction logic always added the correcting discourse to `opposing_pins`, even for pure replacement. It now adds opposition only for explicit `opposition_target_refs`; replacement-only corrections become supersession without false opposition semantics.

### B4. Response operation freshness depended on optional metadata hints — FIXED
The initial gate read `response.metadata["operation_result_refs"]`. Operation-result authority now comes only from exact `ResponseUOLRecord.source_pins` of kind `OPERATION_RESULT`. Non-UNKNOWN reported outcomes require the exact matching reconciliation set; unrelated reconciliations are rejected.

### B5. Selected goal refs were checked, but selected goal pins were not revalidated — FIXED
The goal-current gate now exact-resolves every selected goal pin as well as matching the decision’s selected goal refs.

### B6. Round-trip PASS could lack proof refs — FIXED
Emission requires a semantic round-trip PASS with no additions/losses/drift and durable proof refs. A nominal proofless PASS cannot authorize emission.

### B7. Literal-policy trigger pins were not tied to the response lineage — FIXED
An exact surface hash/graph policy could otherwise be reused under unrelated triggers. Literal trigger pins must now be exact and present in the Response-UOL source/selected-goal lineage.

### B8. Channel-side mutated content could leave the system and then disappear from semantic audit history — FIXED
The initial executor failed closed by creating no `EmissionRecord`, which correctly prevented authorized discourse but incorrectly erased the fact that content had actually left the system. Added immutable `EmissionAnomalyRecord`: it preserves observed unauthorized/ambiguous external output while explicitly carrying `no_output_discourse_authority=True`. It cannot create normal commitments/common ground.

### B9. Contradictory `accepted=False` + `content_left_system=True` could also disappear — FIXED
This now creates the same non-discourse anomaly history and moves the journal to an uncertainty state atomically.

### B10. Anomaly and journal updates could have become a crash-consistency split — FIXED
`persist_anomaly` commits the anomaly record and the journal transition in one local GraphPatch, analogous to the normal emission observation path.

### B11. Output discourse accepted arbitrary acknowledgement targets — FIXED
Acknowledgement targets must be a subset of semantic targets of the exact selected target-bearing goals.

### B12. Output discourse accepted caller-injected operation-result pins — FIXED
Operation-result lineage is now derived from exact Response-UOL source pins. A caller-supplied differing set is rejected.

### B13. Output speaker ref lacked an exact durable dependency — FIXED
The discourse record retains the semantic speaker ref, while commit lineage now pins the exact durable speaker referent revision/fingerprint used at emission.

### B14. Common ground could theoretically be mistaken for world truth — GUARDED
The model/coordinators keep common-ground records separate from epistemic admission/knowledge. Initial status is emitted/received-evidence/unknown-delivery; `SHARED` requires later evidence. Phase 20 must maintain the import/callgraph boundary so common-ground writes can never admit world truth directly.

### B15. Silence risked being represented as fake output — FIXED BY DESIGN
`SilenceOutcomeRecord` is a separate target-bearing, policy-lineaged outcome. It does not create `EmissionRecord`, output discourse, or common-ground mutation.

## C. Phase-19 implementation bugs found during self-audit and fixed before handoff

### C1. ACTIVE migration rules could be executable without competence cases — FIXED
Active `MigrationRuleRecord` now requires competence cases.

### C2. Transformer registry consumed generators twice — FIXED
The original duplicate check built a dict from an iterable and then converted the already-consumed iterable to a tuple, falsely rejecting valid generator-backed registries. The iterable is now materialized once before indexing/duplicate checking.

### C3. `MigrationTargetMapRecord` could not represent MERGED topology — FIXED
It had a singular `source_pin`, despite advertising `MERGED`. It now pins an exact `source_pins` tuple. Structural laws enforce:
- `MAPPED`: one source → one target;
- `SPLIT`: one source → multiple targets;
- `MERGED`: multiple sources → one target;
- general many-to-many remains explicit `TRANSFORMED`.

### C4. Migration rules did not declare source cardinality — FIXED
Added `minimum_source_records` / `maximum_source_records`. Merge execution must be authorized by the exact reviewed rule cardinality.

### C5. No reviewed multi-source transformer boundary existed — FIXED
`transform_merge` requires the exact registered transformer identity to implement `transform_many`; no generic single-record transform is silently reused for merge semantics.

### C6. Shared merged targets/maps could produce duplicate writes in one batch — FIXED
Batch planning deduplicates identical writes by `(kind, ref, revision)` and rejects conflicting duplicate payloads.

### C7. Migration batch identity included mutable store snapshot — FIXED
The first implementation derived `batch_ref` from `snapshot.fingerprint`, so replaying the same logical migration after unrelated writes created a different batch identity. `batch_ref` now derives only from exact source/rule/decision sets.

### C8. Logical batch replay was not idempotent after store revision advance — FIXED
Before writing, the coordinator now resolves the deterministic existing batch. If exact source/rule/decision substrate matches and it is committed/partial, it returns the existing batch/rollback rather than creating a second audit branch.

### C9. Batch replay comparison was order-sensitive despite order-independent batch identity — FIXED
Existing-batch source/rule/decision comparisons now use exact pin sets rather than tuple ordering.

### C10. Intentional-change waivers could mask an unrelated future difference — FIXED
A difference is `INTENTIONALLY_CHANGED` only when the waiver’s exact `fixture_pins` are contained in the exact comparison fixture/trace substrate. Matching behavior-ref strings alone are insufficient.

### C11. Target collision overwrite risk — GUARDED
A pre-existing different fingerprint is quarantined, never overwritten. Identical pre-existing targets may be reused but are not claimed as batch-owned for rollback.

### C12. Rollback could delete native later work — GUARDED
Rollback scans exact dependency edges and blocks if later non-migration dependents use a batch-owned target. Only exact revisions first created by the batch are tombstoned.

### C13. Quarantine could become a hidden authority path — GUARDED
`MigrationQuarantineRecord.non_authority` is mandatory and validated. Runtime migration-rule reachability metadata is rejected.

### C14. Migration could silently broaden privacy scope — GUARDED
Target permission changes pass an explicit migration permission policy; unknown/broader scope fails closed.

## D. Cross-phase authority invariants rechecked

1. Stage 15 remains sole generic goal authority.
2. Selected action goal is not execution authorization.
3. Operation external side effect is outside DB transaction; journal is durable first.
4. Operation result is observation, not predicted transition truth.
5. Reconciliation forces stale pre-operation goal decision out of reuse.
6. Response UOL precedes target-language wording.
7. REALIZE is independently authorized from GROUND/COMPOSE.
8. Round-trip analyzer is reviewed contract authority, not a caller string.
9. Round-trip PASS is not emission authorization.
10. Emission journal precedes external channel side effect.
11. Content that never left the system cannot create output discourse/common ground.
12. Content that left without exact authorization is preserved as anomaly, not normalized into authorized discourse.
13. Common ground is evidence-relative discourse state, not world knowledge.
14. Corrections preserve historical output and supersede projections.
15. Migration is offline-only input transformation, never public runtime semantic authority.
16. Migrated learned structures do not bypass normal Phase-13 per-use authority.
17. Migration equivalence is semantic/dimensioned, not output-string similarity.
18. Phase 20 must physically prove no legacy semantic path is reachable from public runtime entrypoints.

## E. Remaining release blockers, not falsely claimed complete here

The bundle is source/contract compiled and structurally verified, but the following must run in a complete checkout/runtime after application:

- full predecessor unit/integration/competence suite Phases 0–17;
- new Phase-18/19 tests and verifier;
- deterministic schema-version-8 boot DB rebuild and fingerprint comparison;
- Stage-0→22 end-to-end traces;
- channel adapter crash/recovery/idempotency integration fixtures;
- real migration rehearsal against frozen legacy source snapshots;
- semantic equivalence baseline + intentional-change review;
- rollback rehearsal with later-dependent blockers;
- privacy/security/adversarial proof-forgery tests;
- Phase-0 performance/memory/query-plan gates;
- final Phase-20 static/dynamic reachability proof and legacy authority removal.

No v3.5 release should be called complete until those gates pass on one exact final commit/data manifest/boot DB fingerprint.

## F. Late final-audit bugs found after initial Phase-18/19 implementation and fixed before packaging

### F1. Output addressees were bare refs while the speaker alone was exact-pinned — FIXED
Every addressee now resolves to one exact durable `REFERENT` dependency on the output discourse write. Historical audience identity cannot drift under later referent revisions.

### F2. Channel `DELIVERED` was automatically promoted to recipient-received common ground — FIXED
Transport delivery does not universally prove recipient receipt. `ChannelAdapterContractRecord` now has structural `delivery_ack_proves_recipient_receipt`. Only an exact contract with that property can initialize `RECEIVED_EVIDENCE`; otherwise observed output starts at `EMITTED` (or `UNKNOWN_DELIVERY`). No string-name branch decides acknowledgement semantics.

### F3. Ambiguous output-reference candidates were incorrectly stored as `evidence_refs` — FIXED
Target/candidate refs are not evidence records. Output-reference frontiers now use `candidate_refs`; `evidence_refs` remains empty unless genuine evidence exists.

### F4. Migration MERGED target writes depended only on whichever per-source decision was processed first — FIXED
For a multi-source migration map, every newly written target now has dependency edges to **all exact source pins** in the map plus the exact migration rule. Duplicate per-source decisions cannot weaken merged-target lineage.

### F5. REALIZE authority could still admit multiple simultaneously effective active revisions — FIXED
`LanguageUseAuthority` and the commit validator now require exactly one effective active revision per record identity, including argument-frame/morphology/linearization families not covered by the older language registry. Promotion-decision dependency fingerprints are also revalidated exactly.

### F6. Analyzer contract commit validation did not independently enforce singular effective authority — FIXED
Round-trip commit validation now checks the exact analyzer-contract fingerprint and proves one singular effective active revision, mirroring runtime verification.

### F7. Output correction targets were not structurally tied to the correcting/prior discourse — FIXED
Replacement targets must be roots of the exact correcting discourse. Opposition targets must be semantic targets of exact prior commitments. Unrelated output can no longer supersede prior common-ground/commitment projections as a “correction.”

### F8. Transport exceptions created synthetic strings in `response_evidence_refs` — FIXED
A Python exception class name is not a durable EvidenceRecord. Exception-after-submit now moves the journal to delivery-unknown without fabricating evidence identity; transport adapters/recovery may later attach real evidence/proof.

### F9. Channel observations allowed contradictory `delivered=True` with unknown/not-accepted transport state — FIXED
`ChannelObservation` now rejects internally contradictory delivery flags and validates observed surface hashes/evidence uniqueness before journal mutation.

### F10. Allowed emission could be targetless at the transport boundary — FIXED
`ALLOW` authorization and observed normal emission both require at least one explicit audience. Silence remains represented separately as `SilenceOutcomeRecord`.

### F11. Migration normalized indexing lost multi-source merge lookupability — FIXED
Schema-version 8 adds `source_refs_json` plus normalized `migration_record_sources` with a source index. Multi-source mappings can be queried by every contributing legacy source without parsing payload blobs.

### F12. Channel recovery capability was implicit — FIXED
`recover()` is now permitted only when the exact reviewed channel contract declares `supports_recovery_query=True`. Recovery is a query/reconciliation path, never an implicit second send. Client-key idempotency contracts require the key before the PREPARED journal is committed.

### F13. Operation reconciliation could be stranded by a redundant goal-decision tombstone — FIXED
If an exact pre-operation goal decision had already been invalidated concurrently, reconciliation previously attempted to tombstone it again in the same atomic patch, causing a CAS conflict and potentially leaving an already-observed operation journal unreconciled. Reconciliation now conditionally tombstones only when the exact decision is still current; if it is already absent, refresh has already been forced and result/journal reconciliation still completes.
