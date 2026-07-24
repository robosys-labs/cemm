# CEMM v3.5 Phases 0–12 — Phase 13 Prerequisite Audit

**Audited lineage:** `agent/v350-phases-0-3`, one commit ahead of Phase 11 `735d13d11f112d0062972a9a66d59100fa8a406c`, containing the Phase 12 cross-domain transition proof patch.

## Governing invariants

This audit is evaluated against the active v3.5 `ARCHITECTURE.md`, `CORE_LOOP.md`, and `IMPLEMENTATION_PLAN.md` only.

1. Examples are evidence, never definitions.
2. Proposal is never authority.
3. Competence evidence is independent of induction evidence.
4. Promotion is exact-record, exact-revision, per-use authority.
5. Runtime authority is explicit and revocable.
6. Corrections/retractions preserve lineage and invalidate derived authority.
7. No domain concept, lexical string, fixture name, or benchmark answer may become kernel branching logic.

## Confirmed defects/gaps

### P0 — candidate/competence-only schema use could become executable

`UseProfile.permits()` is a decision-only helper. Call sites such as schema use selection and semantic-application validation were able to treat a proposed `ALLOW` as sufficient without requiring promoted lifecycle authority.

**Impact:** a candidate or competence-only schema could influence runtime before promotion.

**Phase 13 prerequisite fix:** introduce a lifecycle-aware `schema_authorizes_use()` gate. Normal executable `ALLOW` requires `ACTIVE`; `PROVISIONAL` is visible only to explicitly provisional callers.

### P0 — candidate revision could shadow older active schema authority

Schema effective-revision computation allowed any non-terminal superseding revision to suppress the prior revision.

**Impact:** a candidate/structurally-closed/provisional revision could remove a valid active revision from effective selection before promotion.

**Fix:** only an `ACTIVE` revision may supersede effective runtime authority. Candidate revisions remain inspectable but inert.

### P0 — language revision supersession had the same pre-promotion shadowing defect

Language registry supersession considered structurally-closed/provisional/competence-verified revisions when suppressing an older active record.

**Impact:** a non-active language revision could make a previously active pack/form/sense/link/construction disappear from runtime selection.

**Fix:** active-language selection and supersession are `ACTIVE`-only. Isolated competence uses an explicit sandbox activation path rather than public registry authority.

### P0 — default-rule authority admitted non-active revisions

`DefaultRuleRepository.authoritative()` could select candidate/structurally-closed/provisional/competence-verified rules and could let non-active revisions shadow an active predecessor.

**Impact:** inference policy could change before promotion.

**Fix:** default-rule runtime authority and supersession are `ACTIVE`-only.

### P0 — transition compiler runtime boundary was weaker than transition coordinator

The coordinator selected only active contracts, but the compiler itself rejected only terminal contracts.

**Impact:** lower-level callers could compile candidate/provisional transition contracts as if executable.

**Fix:** compiler defaults to `require_active=True`. Commit-time candidate validation uses an explicit `require_active=False` structural mode; runtime proof/execution remains active-only.

### P0 — transition/state validation used decision-only use checks

Transition/state-delta validation used `use_profile.permits()` directly.

**Impact:** candidate/competence-only transition authorization could leak into durable state effects.

**Fix:** runtime transition/state authorization uses lifecycle-aware schema authority.

### P1 — generic dependency invalidation revokes only materialized views

The store dependency walker marks materialized views stale but does not itself revoke semantic authority or derived semantic records.

**Impact:** correction/retraction can leave learned semantic authority or transition-derived products visible unless a subsystem explicitly revokes them.

**Phase 13 fix:** add first-class `LearningInvalidationRecord`, explicit dependency-closure planning, promotion-lineage-aware revocation/tombstoning, recomputation frontiers, and replay requirements.

### P1 — `GraphPatch.validation_requirements` is journal metadata, not authority

Validation requirement strings are persisted for audit but are not executable authorization.

**Impact:** labels such as `no_boot_promotion` or `competence_only` cannot safely enforce promotion/security boundaries.

**Fix:** Phase 13 promotion authorization is represented by typed, revision-pinned `PromotionDecisionRecord` and commit-boundary validation. Metadata remains diagnostic only.

### P0 — ordered scalar transition direction used arbitrary active-assignment order

`StateDeltaValidator` validated `INCREASE`/`DECREASE` direction against `active[0]`. With multiple active assignments, an explicit `from_value_ref` could therefore be ignored for ordering validation.

**Impact:** direction validity could depend on deterministic list ordering rather than the semantically pinned source value.

**Fix:** when `from_value_ref` is present, validate direction from that exact pinned value. Without `from_value_ref`, scalar ordered change requires exactly one active current value; ambiguity fails closed.

### P0 — transition state-delta dependency assembly could violate its own uniqueness contract

`EffectCommitCoordinator` appended both `from_value_ref` and `to_value_ref` dependencies directly, while `PatchOperation` requires dependency `record_ref`s to be unique. A valid structural effect where both refs are identical could therefore fail patch construction with duplicate dependencies.

**Fix:** assemble exact transition dependencies through a ref-keyed map, deduplicate identical pins, and reject conflicting identities for the same ref.

### P1 — no independent response-policy use axis existed

The Phase 13 plan requires independent response-policy competence/promotion, but `UseOperation` had no response-policy operation.

**Impact:** Phase 15 policy knowledge would have to piggyback on `PLAN`/`REALIZE`, violating per-use authority.

**Fix:** add `UseOperation.RESPONSE_POLICY` now, before Phase 15.

### P1 — isolated competence cannot mutate immutable same-revision records in place

The initial Phase 13 design concept of copying a candidate and then changing lifecycle at the same revision conflicts with the store's immutable-revision CAS contract.

**Impact:** competence activation would fail correctly with `record_revision_immutable`.

**Fix:** transform candidate lifecycle/use authority only while copying the exact source substrate into the temporary competence overlay. Source revision identity is preserved for internal exact references, while source fingerprints are retained in the durable competence result. The authoritative source store is unchanged.

### P1 — snapshot transaction re-entry in frontier persistence

Applying a patch while the same store snapshot transaction is still open attempts a nested transaction on the same SQLite connection.

**Fix:** build/pin the frontier patch inside the snapshot, exit the snapshot, then apply the CAS patch.

## Known proof gaps retained explicitly

1. Phase 0 benchmark/timing/query-plan baseline gate remains unproven in the delivery lineage and must be completed before public cutover.
2. Phase 12 focused proof does not substitute for a full historical repository run after authority hardening.
3. Phase 13 runtime learning cutover remains **shadow/non-public** until the full promotion, retraction, restart, adversarial, and performance gates pass.

## Required regression gates after applying Phase 13

- Full `tests/v350` suite.
- Phase 12 transition verifier and all predecessor verifiers.
- Phase 13 learning verifier.
- Restart/reopen proof with promoted authority.
- Concurrent promotion CAS race.
- Correction/retraction invalidation + replay frontier proof.
- Candidate/provisional/competence-only non-authority tests for schemas, language records, defaults, and transitions.
- Concept/fixture rename tests proving no name-based runtime branch.

