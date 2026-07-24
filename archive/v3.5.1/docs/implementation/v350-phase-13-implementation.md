# CEMM v3.5 Phase 13 — Learning-First Promotion Lifecycle Implementation

## Objective

Implement the v3.5 learning-first lifecycle from unresolved frontier/evidence to independently tested, per-use promoted semantic authority, with exact dependency pins, atomic CAS promotion, correction/retraction invalidation, and restart-safe rehydration.

This phase deliberately does **not** add a domain ontology, keyword tables, concept-name switches, or automatic LLM authority.

## Authority model

```text
observation / unresolved structure
        ↓
LearningFrontierRecord
        ↓
CandidateStructureInducer proposal
        ↓
canonical candidate records (non-authoritative)
        ↓
LearningPackageRecord + exact dependency pins
        ↓
independent isolated competence by UseOperation
        ↓
CompetenceResultRecord
        ↓
PromotionPolicyEngine + explicit review/authorization
        ↓
PromotionDecisionRecord
        ↓
ONE atomic CAS GraphPatch
  ├─ durable decision
  ├─ promoted canonical revisions
  └─ promoted package lifecycle revision
        ↓
active per-use authority
        ↓
correction / retraction / supersession
        ↓
LearningInvalidationRecord + revocation + recomputation frontier
```

## Added durable records

- `LearningPackageRecord`
- `LearningFrontierRecord`
- `LearningEvidenceLink`
- `CompetenceResultRecord`
- `PromotionDecisionRecord`
- `LearningInvalidationRecord`

All carry deterministic serialization and stable references/revisions where applicable. Candidate and dependency substrate is represented by `PinnedRecord(record_kind, record_ref, revision, record_fingerprint)`.

## Added components

### FrontierCollector

Structural frontier deduplication keyed by missing contract, target, expected structural family, context, permission, and accepted anchor classes. Surface wording is excluded from authority identity.

### EvidenceAggregator

Keeps support, counterexamples, corrections, and retractions separately attributable. Evidence frequency may accumulate weight but never produces authority.

### CandidateStructureInducer protocol

A narrow proposal interface. Inducers may emit canonical record candidates and dependency pins, but have no promotion/commit authority.

### PackageAssembler / LearningDependencyResolver

Builds exact candidate/dependency DAGs with recursion/node budgets, exact fingerprints, cycle detection, and stale-pin refusal.

### LearningCompetenceRunner

Runs per-use competence against a temporary isolated `SemanticStore` overlay.

Key invariants:

- source store snapshot is immutable during the run;
- source candidate/dependency fingerprints are checked before sandbox construction;
- candidate activation happens only in the sandbox;
- candidate proposed permissions on unrelated axes are not inherited as authority;
- independent lineage must not intersect induction/source lineage;
- every declared case must be accounted for;
- passed competence carries proof lineage and substrate fingerprints.

### PromotionPolicyEngine

Mechanical policy over typed evidence + competence only.

- repeated evidence cannot substitute for competence;
- correction/retraction blocks promotion;
- counterexamples must be explicitly covered by passed competence;
- grants are exact candidate + exact use operation;
- record-family/record-structural compatibility is enforced;
- preserve-only is not promotion.

### PromotionCoordinator

Builds a single CAS transaction containing:

1. `PromotionDecisionRecord`;
2. promoted canonical revisions with exact decision/competence/candidate/dependency lineage;
3. promoted `LearningPackageRecord` lifecycle revision.

No partial promotion is possible. Stale store revision or stale candidate/dependency fingerprints fail the whole transaction.

### LearningCommitValidator

Enforces promotion at the actual storage trust boundary.

It rejects:

- stale package pins;
- competence substrate mismatch;
- non-independent competence lineage;
- unrequested/broadened use grants;
- failed competence used for executable/provisional authority;
- direct `GraphPatch` activation of a tracked learned candidate without an exact promotion decision dependency;
- permission broadening;
- incompatible record/use grants.

### LearningInvalidationManager / LearningRetractionCoordinator

Computes explicit dependency closure from correction/retraction/supersession triggers and emits:

- durable invalidation lineage;
- invalidated package lifecycle revisions;
- tombstones for auto-derived/promoted authority where appropriate;
- recomputation frontiers;
- replay-required refs for transition/state/capability products.

The generic store dependency walker remains a cache/view invalidation primitive; semantic revocation belongs here.

### LearningRehydrationCoordinator

On restart, learned authority is reconstructed only when all of the following still hold:

- latest package lifecycle is promoted;
- exact candidate/dependency substrate still resolves;
- exactly one matching promote decision exists;
- competence results still match exact package/use/substrate;
- current promoted canonical revisions remain active/provisional according to the exact grant;
- promoted revisions retain dependency lineage to the promotion decision and exact source candidate.

Stale learned authority fails closed.

## Prerequisite authority hardening

Phase 13 also closes cross-phase defects required for safe promotion:

- lifecycle-aware schema use (`ACTIVE` required for normal executable `ALLOW`);
- candidate-safe schema supersession;
- active-only language authority/supersession;
- active-only default-rule authority/supersession;
- active-by-default transition compilation with explicit structural candidate-validation mode;
- lifecycle-aware state-transition authorization;
- scalar transition direction pinned to the explicit `from_value` rather than active-list order;
- duplicate exact transition dependency pins deduplicated/ref-conflict checked;
- independent `UseOperation.RESPONSE_POLICY` axis for Phase 15.

## Runtime wiring

`LearningCoordinator` is introduced in **shadow mode** for Stage 11 frontier collection. It cannot auto-promote.

Public learning cutover remains disabled in manifest metadata (`learning_runtime_cutover=false`) until the full exit gates pass.

## Phase 13 exit gates

1. New type/facet/property/state/action/event/transition/language/response-policy knowledge can be represented as data without kernel branching.
2. Candidate records are inert until exact per-use promotion.
3. Competence evidence is independent from induction evidence.
4. Counterexamples survive and constrain promotion.
5. Promotion is atomic and CAS-protected.
6. Correction/retraction invalidates affected learned authority and exposes recomputation/replay work.
7. Restart cannot reactivate stale authority.
8. Malicious names, fixture renames, repeated examples, or direct patch attempts cannot create authority.
9. Full predecessor regression suite remains green.
10. Phase 0 performance/query-plan baseline debt is explicitly closed before public cutover.
