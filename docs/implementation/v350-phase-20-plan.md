# CEMM v3.5 Phase 20 — Runtime Cutover, Sole Semantic Authority, and Legacy Removal

## 1. Objective

Phase 20 is the final architectural cutover. Its purpose is not to add another semantic subsystem. It proves that the v3.5 pipeline built in Phases 0–19 is the **only public semantic authority** and then physically removes, quarantines, or makes unreachable every superseded path that can independently interpret, mutate, decide, realize, or commit meaning.

The phase is complete only when a public request cannot accidentally bypass the canonical sequence through an old router, keyword map, predicate-specific responder, event mutation helper, legacy memory blob, fallback NLG path, or migration adapter.

The governing principle is:

```text
one request
→ one canonical Stage-0…Stage-22 semantic authority graph
→ one durable authority model
→ no competing fallback semantics
```

Phase 20 must leave compatibility adapters only at the **evidence/input boundary** or **surface/output transport boundary**. They may translate protocols and bytes. They may not decide meaning.

---

## 2. Canonical prerequisites

Cutover may not begin until the following are green on one exact repository commit and one exact data manifest:

- Phase 0 architecture, dependency, performance and query-plan gates;
- Phase 1–5 core UOL/identity/context/time foundations;
- Phase 6 reviewed foundation data;
- Phase 7 language evidence separation;
- Phase 8 grounding;
- Phase 9 composition;
- Phase 10 epistemic admission/correction/retraction;
- Phase 11 transitions/capabilities;
- Phase 12 vertical transition slices and restart safety;
- Phase 13 learning/promotion/invalidation;
- Phase 14 impact/importance;
- Phase 15 obligations/goals/response policy;
- Phase 16 operation boundary and Response UOL planning;
- Phase 17 multilingual realization and reviewed analyzer authority;
- Phase 18 emission/output discourse/common ground;
- Phase 19 migration/equivalence/rollback.

A known failing predecessor gate cannot be waived by Phase 20. A waiver document is not semantic correctness.

---

## 3. Canonical stage alignment before cutover

Before code reachability work, canonical documents must describe one stage topology.

The macro stage list and detailed sections must agree that:

```text
15 DERIVE_OBLIGATIONS_GENERATE_AND_ARBITRATE_GOALS
16 PLAN_AUTHORIZE_EXECUTE_AND_RECONCILE
17 RECONCILE_OPERATION_OUTCOMES_AND_REFRESH_GOALS
18 BUILD_RESPONSE_UOL
19 REALIZE_TARGET_LANGUAGE
20 VERIFY_AND_AUTHORIZE_EMISSION
21 COMMIT_OUTPUT_DISCOURSE_AND_COMMON_GROUND
22 INVALIDATE_RECOMPUTE_AND_FINALIZE
```

Stage 15 is the sole generic goal authority.

Stage 17 may cause re-entry to Stage 15 after operation outcomes change semantic state. It does not create a second response-goal ontology.

Phase numbers and core-loop stage numbers must remain explicitly distinguished in documentation and traces. Phase 18 implements core stages 20–21; Phase 19 is an offline migration program, not a runtime core-loop stage.

---

## 4. Hard cutover laws

### 4.1 Sole semantic entrypoint

Every public semantic request must enter one named v3.5 orchestration boundary.

No web route, CLI, worker, API, demo, email adapter, test convenience function, or internal tool may call a downstream semantic subsystem directly in production mode.

### 4.2 No dual authority

During final cutover there is no:

```text
try_v350_else_legacy()
legacy_if_low_confidence()
legacy_if_language_unknown()
legacy_if_timeout()
legacy_if_schema_missing()
```

A v3.5 frontier/unknown/refusal is a valid result. Legacy fallback may not convert uncertainty into fabricated certainty.

### 4.3 Adapters are mechanical only

Post-cutover adapters may:

- decode transport payloads;
- normalize protocol metadata;
- attach source/evidence provenance;
- call Stage 0/1;
- encode an already authorized emitted surface.

They may not:

- map words to semantic schemas;
- classify domain intent;
- choose response goals;
- mutate state;
- infer event effects;
- select sentence templates;
- bypass emission authorization.

### 4.4 No legacy write authority

No removed legacy model may write authoritative semantic state after cutover.

Read-only historical access is allowed only through explicit migration/audit tooling.

### 4.5 No mixed rollback

Rollback means an **atomic release rollback** to the previous deployable system/store snapshot according to the release plan.

It does not mean re-enabling selected legacy semantic functions inside a running v3.5 process.

### 4.6 Unknown remains unknown

Cutover pressure may never justify:

- fake default values;
- targetless acknowledgements;
- guessed reference bindings;
- silent permission broadening;
- transport acknowledgement as semantic success;
- string similarity as semantic equivalence.

---

## 5. Runtime Authority Manifest

Create a machine-readable `RuntimeAuthorityManifest` generated from the exact release commit.

It must enumerate:

```text
public_entrypoints
canonical_orchestrator
allowed_runtime_modules
allowed_record_kinds
allowed_boot_data_modules
allowed_language_packages
operation_adapter_contracts
semantic_analyzer_contracts
channel_adapter_contracts
migration_modules_allowed_at_runtime = []
legacy_denylist_fingerprint
source_manifest_fingerprint
boot_database_fingerprint
schema_version
release_commit
verification_artifact_fingerprints
```

The runtime must validate the manifest before serving public semantic requests.

A mismatched code/data/boot DB fingerprint fails closed.

The manifest is not a vocabulary. It is a **runtime authority topology declaration**.

---

## 6. Legacy Authority Denylist

Maintain a machine-readable denylist of removed authority categories and concrete paths/symbols.

Minimum categories:

```text
legacy_grounders
keyword_intent_maps
action_keyword_tables
predicate_response_templates
targetless_acknowledgers
event_specific_mutators
state_blob_writers
legacy_memory_promoters
legacy_reference_resolvers
legacy_response_routers
legacy_nlg_executors
legacy_output_commit_shortcuts
legacy_learning_promoters
migration_runtime_adapters
```

Each denylist entry contains:

```text
path_or_symbol
category
replacement_authority
removal_status
last_allowed_phase
reason
verification_ref
```

Status is one of:

```text
deleted
moved_to_offline_migration
moved_to_test_fixture
mechanical_adapter_only
quarantined_archive
```

There is no `temporarily_runtime_reachable` status in the final release.

---

## 7. Public entrypoint inventory

Enumerate every public or operational entrypoint:

- HTTP/API routes;
- web demo endpoints;
- CLI commands;
- background workers;
- scheduled jobs;
- websocket/chat handlers;
- library public functions;
- message queue consumers;
- multimodal ingestion adapters;
- operation callback/webhook handlers;
- output channel callbacks;
- migration/admin commands.

For each entrypoint record:

```text
entrypoint_ref
module/symbol
input modality
permission boundary
allowed canonical destination
whether semantic
whether offline-only
callgraph proof ref
```

Every semantic entrypoint must converge on the same canonical orchestrator before grounding/composition.

Migration commands must be explicitly offline-only and absent from server import closure.

---

## 8. Static callgraph closure proof

Build a static verifier that starts from all public semantic entrypoints and computes import/call reachability.

It must fail when a path reaches:

- a denylisted symbol;
- a migration transformer;
- an archived legacy package;
- a semantic regex/keyword shortcut;
- a direct state mutation helper;
- a sentence-template registry;
- a deprecated assembler/router.

It must also fail if an approved semantic subsystem is reachable **before** its canonical predecessor boundary.

Examples:

- realization cannot be public-entrypoint reachable without Response UOL;
- output discourse cannot be reachable without emission observation;
- transition commit cannot be reachable without transition proof;
- operation executor cannot be reachable without operation authorization/journal;
- common-ground mutation cannot be reachable without emitted output discourse.

Static verification is necessary but not sufficient; dynamic tripwires are also required.

---

## 9. Dynamic authority tripwires

Add runtime instrumentation in the cutover build:

- canonical request/cycle ID;
- current core-loop stage;
- authority record pins used;
- entrypoint ref;
- boot/data fingerprint;
- permission/context scope;
- semantic write source.

Sensitive APIs reject calls lacking the expected stage token/cycle capability.

Examples:

```text
TransitionCommitCoordinator requires Stage-12/13 commit capability.
Operation executor requires exact OperationAuthorization + PREPARED journal.
Realization compiler requires exact ResponseUOL + RealizationRequest.
Channel executor requires EmissionAuthorization + PREPARED emission journal.
CommonGroundCoordinator requires emitted OutputDiscourse lineage.
```

The token/capability is structural orchestration evidence, not a string-based security bypass.

Production logs record violations as architecture faults.

---

## 10. Shadow mode before final switch

A bounded pre-cutover shadow period is allowed only for comparison.

Rules:

1. v3.5 is the candidate authority under test.
2. Legacy may run read-only in a separate process/sandbox.
3. Legacy outputs may be captured as comparison evidence only.
4. Legacy must not mutate shared state, common ground, learning, operation state, or user-visible output.
5. Comparison uses Phase-19 semantic equivalence dimensions, not string equality.
6. Shadow mode is removed before the final release artifact is built.

No dual-write or winner-selection production mode is permitted.

---

## 11. Data cutover

### 11.1 Freeze window

Establish a migration/cutover checkpoint:

```text
legacy source snapshot
→ Phase19 migration batches
→ equivalence report
→ unresolved quarantine report
→ final delta snapshot
→ final deterministic delta migration
→ write freeze
→ release boot/store fingerprint
```

### 11.2 No implicit legacy reads

After cutover, runtime stores may not lazily consult legacy tables/blobs as fallback semantic memory.

Any retained legacy storage is:

- offline audit evidence;
- migration source;
- rollback artifact;
- explicitly not runtime semantic authority.

### 11.3 Schema compatibility

The release must pin:

- SQLite/application schema version;
- boot DB compiler version;
- source manifest fingerprint;
- migration batch set fingerprint;
- runtime authority manifest fingerprint.

An old boot DB cannot be silently opened by a newer semantic runtime.

---

## 12. Legacy deletion/quarantine strategy

Use one of four actions for every legacy component.

### Delete

Use when functionality is fully replaced and historical code has no audit value.

### Offline migration namespace

Use only for mechanical migration extractors/transformers needed for reproducibility.

They must not be imported by runtime packages.

### Test fixture/archive

Use for regression examples or legacy semantic traces.

They cannot be installed/imported in production runtime packages.

### Mechanical protocol adapter

Use when a transport/protocol boundary remains necessary.

The adapter must contain no semantic classification/control flow.

Every retained file receives an explicit classification. “Unreviewed legacy” is a release blocker.

---

## 13. Legacy semantic debt ratchet

Create a source scanner with a checked-in baseline of zero allowed runtime semantic debt.

Reject new occurrences of:

- concept-name branches in kernel code;
- language-specific semantic regexes;
- direct word→schema dictionaries outside reviewed language data;
- domain full-sentence response templates;
- hard-coded event effect tables in Python;
- calls to legacy semantic routers;
- source-code enum expansion for learned domain concepts;
- generic targetless response construction.

The scanner must distinguish tests/docs/migration fixtures from runtime code, but those exclusions are explicit and narrow.

The final baseline is zero for public-runtime authority paths.

---

## 14. Semantic authority import boundaries

Enforce package layering.

A recommended dependency direction is:

```text
transport adapters
  ↓
canonical orchestrator
  ↓
evidence / grounding
  ↓
UOL / schema / composition
  ↓
epistemics / transitions / learning / significance / goals
  ↓
operations + Response UOL
  ↓
realization
  ↓
emission authorization / output discourse
```

Offline migration may import stable codecs/models for transformation, but runtime packages must not import migration modules.

Add import-linter rules for forbidden reverse edges and runtime→migration edges.

---

## 15. Canonical orchestrator cutover

Implement one production orchestration entrypoint with explicit stage transitions.

Properties:

- one exact store snapshot or explicit refresh boundary per stage contract;
- immutable cycle ID;
- deterministic trace order;
- no hidden downstream fallback;
- frontiers are first-class outputs;
- operation side effects outside DB transactions;
- post-operation re-entry to Stage 15 when required;
- no surface generation before Response UOL;
- no output/common-ground commit before observed emission.

The orchestrator itself contains no domain ontology or language-specific meaning rules.

---

## 16. Compatibility façade policy

Public APIs may preserve old method names temporarily only when the implementation is a thin façade that:

1. validates inputs;
2. calls the canonical v3.5 orchestrator;
3. returns a view of canonical results;
4. performs no semantic fallback or mutation itself.

Each façade has a removal date/version and a test proving it cannot bypass the canonical path.

A façade that reimplements meaning is legacy authority and must be deleted.

---

## 17. Feature flags

Semantic authority flags are prohibited after cutover.

Forbidden final flags include:

```text
USE_V350=false
FALLBACK_LEGACY=true
USE_OLD_NLG=true
LEGACY_MEMORY_ON_FAILURE=true
```

Allowed flags control only non-semantic operational concerns such as:

- logging verbosity;
- metrics exporters;
- transport rollout;
- UI presentation;
- non-authoritative cache enablement.

The release verifier scans for forbidden authority switches.

---

## 18. Restart and crash safety

Cutover verification must include restart at every durable boundary:

- after grounding candidates;
- after epistemic admission;
- after transition preview/commit;
- after learning promotion/invalidation;
- after operation PREPARED/SUBMITTED/UNKNOWN/result/reconciliation;
- after Response UOL;
- after realization candidate/round-trip;
- after emission PREPARED/SUBMITTED/UNKNOWN/delivered;
- after output discourse/common-ground commits;
- during migration batch and rollback.

Restart must reconstruct the same effective authority from durable records without consulting legacy runtime state.

---

## 19. Concurrency and idempotency

Test concurrent:

- corrections vs queries;
- schema promotion vs grounding;
- operation authorization vs capability change;
- emission authorization vs goal invalidation;
- common-ground update vs correction;
- migration batch vs native writes during controlled migration windows.

Required laws:

- optimistic snapshot/CAS rejects stale commits;
- duplicate retries are idempotent where the contract claims idempotency;
- non-idempotent unknown external effects are never blindly retried;
- a migration rollback never deletes a later native dependent write.

---

## 20. Security and privacy cutover

Perform an authority-oriented security review.

Verify:

- untrusted external content cannot self-promote schemas/rules/operations/output policy;
- permission scopes survive grounding→memory→response→realization→emission;
- output reference resolution cannot expose anchors from another permission/context/audience;
- migration cannot broaden unknown legacy ACLs;
- archived legacy stores are not runtime-readable by normal request identities;
- debug endpoints cannot bypass emission or operation authorization;
- forged/stale proof pins fail exact fingerprint checks.

Red-team the public entrypoints specifically for bypass paths.

---

## 21. Performance and query-plan gates

Phase 20 must finally close any unproven Phase-0 performance debt.

Benchmark on realistic persistent data volumes:

- Stage 0–22 latency distribution;
- grounding candidate lookup;
- exact dependency closure;
- knowledge/state/capability queries;
- goal arbitration;
- Response-UOL planning;
- realization and round-trip;
- emission gate;
- output-reference lookup;
- restart rehydration;
- migration/equivalence offline throughput.

For indexed critical queries capture `EXPLAIN QUERY PLAN` evidence and fail on accidental full scans where bounded indexed lookup is required.

Set explicit budgets for:

```text
p50
p95
p99
memory/cycle
durable writes/cycle
startup/rehydration
DB size growth
```

Performance fixes may add indexes/caches, but caches never become semantic authority.

---

## 22. Reproducible release build

Release artifacts must be reproducible from:

- exact git commit;
- exact source data manifest;
- exact compiler/tool versions;
- exact SQLite schema version;
- exact migration set;
- exact language packages;
- exact competence/verification inputs.

Produce:

```text
runtime package hash
boot DB hash
RuntimeAuthorityManifest hash
LegacyAuthorityDenylist hash
verification report hash
migration report hash
SBOM/dependency lock hash
```

A runtime whose fingerprints do not match refuses semantic service.

---

## 23. Observability without semantic drift

Metrics/logging must expose structural IDs and outcomes, for example:

```text
cycle_ref
stage
record kind/ref/revision/fingerprint
frontier kind
selected goal refs
operation authorization decision
roundtrip decision
emission authorization decision
common-ground transition
```

Do not add convenience semantic labels derived from English regexes or concept-name heuristics for dashboards.

Human-readable dashboards may resolve labels through non-authoritative presentation layers.

---

## 24. Cutover verification suites

### 24.1 Architecture/static

- Runtime Authority Manifest validates.
- Legacy Authority Denylist closure passes.
- public callgraph reaches no denylisted authority;
- runtime imports no migration transformer package;
- forbidden semantic flags absent;
- zero runtime semantic debt ratchet.

### 24.2 Grounding/composition

- unseen reviewed language variants ground through language data;
- renamed schemas preserve structural behavior;
- ambiguous meaning remains alternatives/frontier;
- no English regex is required for semantic correctness.

### 24.3 Epistemics

- user claim remains attributed until admitted;
- support/opposition coexist;
- correction/retraction preserves history;
- stale source assessment cannot authorize admission.

### 24.4 Transitions/capabilities

- event truth separate from state effects;
- exact transition proof required;
- capability holder/action revision exact;
- restart does not duplicate transitions.

### 24.5 Learning

- candidate does not self-authorize;
- per-use promotion independent;
- overlay REALIZE authority needs exact promotion;
- invalidation removes future authority without deleting historical audit.

### 24.6 Goals/operations

- every selected goal target-bearing;
- utility never grants authority;
- operation result bound to exact observed journal;
- unknown external effect not retried blindly;
- post-operation stale goal decision unusable.

### 24.7 Response/realization

- all and only selected meaning in Response UOL;
- no full-sentence domain templates;
- reviewed analyzer contract required;
- nested apps/coordination/scope round-trip;
- cross-language semantic fingerprints match.

### 24.8 Emission/output discourse

- roundtrip alone cannot emit;
- stale emission authorization rejected;
- no observed emission → no output discourse/common ground;
- common ground never becomes truth automatically;
- literal policy exact hash/graph;
- correction preserves emission history;
- semantic output reference works after transcript reformatting.

### 24.9 Migration

- all sources explicitly disposed;
- quarantine non-authority;
- collision no overwrite;
- rollback exact owned revisions only;
- later dependents block unsafe rollback;
- semantic equivalence dimensioned;
- no migration runtime reachability.

---

## 25. Adversarial tests

Include deliberate attacks:

1. import a legacy router from a public handler;
2. dynamically import migration transformer at runtime;
3. forge a record ref with wrong fingerprint;
4. activate an overlay language record without promotion;
5. call realization directly without Response UOL;
6. call channel adapter without emission authorization;
7. mutate common ground without emission evidence;
8. reuse stale operation result against another observed journal;
9. create fake analyzer name/revision without contract;
10. enable a legacy fallback via environment variable;
11. insert a keyword semantic shortcut under a new filename;
12. add a domain sentence template disguised as test data used at runtime;
13. migrate unknown ACL into public scope;
14. rollback a migration target with later native dependent;
15. open a mismatched boot DB/schema version.

Every attack must fail deterministically.

---

## 26. Removal execution order

### 20A — Freeze canonical contracts

Pin architecture/core-loop/implementation plan and fix stage-name drift.

### 20B — Inventory entrypoints and legacy authorities

Generate entrypoint inventory and initial denylist.

### 20C — Build Runtime Authority Manifest tooling

Make code/data/store fingerprints machine-verifiable.

### 20D — Static callgraph/import closure

Prove public semantic reachability.

### 20E — Add dynamic stage/authority tripwires

Detect bypass calls under integration tests.

### 20F — Shadow semantic equivalence run

Read-only legacy comparison only; no dual writes/user output.

### 20G — Close migration/quarantine report

Resolve or explicitly accept quarantines as non-authority.

### 20H — Final delta migration and write freeze

Create final source/store fingerprints.

### 20I — Cut all public entrypoints to canonical orchestrator

No direct subsystem entry.

### 20J — Delete/relocate legacy grounding/composition authority

No keyword/regex shortcuts.

### 20K — Delete/relocate legacy memory/state/event authority

No monolithic blob writer or event-specific effect helper.

### 20L — Delete legacy response/NLG/output authority

No predicate templates/targetless ack/output commit shortcuts.

### 20M — Remove semantic feature flags/fallbacks

No mixed authority mode.

### 20N — Runtime→migration isolation

Migration packages offline/admin-only.

### 20O — Full correctness/security/restart suite

Run all predecessor and adversarial gates.

### 20P — Performance/query-plan closure

Prove Phase-0 budgets on final topology.

### 20Q — Reproducible release artifacts

Build boot DB, manifests, hashes, SBOM and reports.

### 20R — Final cutover and post-cutover tripwire verification

Serve requests only after runtime authority manifest validation.

---

## 27. Release rollback strategy

Before cutover produce an exact previous-release rollback package containing:

- previous application artifact;
- compatible previous DB/store snapshot;
- migration rollback instructions;
- traffic switch procedure.

If rollback is required:

1. stop semantic writes;
2. switch traffic atomically away from the v3.5 writer;
3. restore the compatible release/store pair;
4. never run legacy and v3.5 semantic writers concurrently;
5. preserve Phase-18 external emission/operation audit history needed to prevent duplicate real-world side effects.

A partial feature-flag fallback inside v3.5 is prohibited.

---

## 28. Final acceptance matrix

Phase 20 passes only if all statements are true:

1. One canonical public semantic orchestrator exists.
2. Every semantic public entrypoint reaches it.
3. No public callgraph reaches a denylisted legacy authority.
4. Runtime imports no migration transformer.
5. No semantic legacy fallback flag exists.
6. Macro and detailed core-loop stage topology agree.
7. Stage 15 is the sole generic goal authority.
8. Frontiers/unknowns are valid final outcomes.
9. Direct word/pattern→meaning shortcuts are absent from runtime kernel paths.
10. No predicate-specific full-sentence runtime templates exist.
11. No event-specific state mutation helper bypasses transition proofs.
12. No mutable monolithic semantic blob is authoritative.
13. Learned structures need per-use promotion.
14. Overlay language realization needs exact REALIZE authority.
15. Operation execution needs fresh exact authorization and journal.
16. Reconciliation is bound to exact result + observed journal lineage.
17. Response UOL precedes realization.
18. Reviewed semantic analyzer contract precedes round-trip authority.
19. Round-trip PASS does not by itself authorize emission.
20. Emission authorization is fresh and proof-bearing.
21. Journal exists before each external output side effect.
22. Unknown delivery is never promoted to delivered/shared without evidence.
23. No emission means no output discourse/common-ground mutation.
24. Common ground remains distinct from truth.
25. Output references resolve semantically, not by transcript substrings.
26. Corrections preserve immutable output history.
27. Every migration source has explicit disposition.
28. Quarantine is non-authoritative.
29. Migration cannot overwrite conflicting native targets.
30. Migration cannot broaden unknown permission scope.
31. Rollback removes only exact batch-owned targets.
32. Later native dependents block unsafe rollback.
33. Semantic equivalence is dimensioned and proof-bearing.
34. Intentional differences have exact approved fixture lineage.
35. Restart reproduces effective authority without legacy reads.
36. Concurrency/CAS tests reject stale writes.
37. Security/privacy bypass tests pass.
38. Query-plan/performance budgets pass.
39. Release code/data/boot DB fingerprints are reproducible.
40. Runtime refuses mismatched authority manifest/boot DB.
41. Legacy semantic debt ratchet is zero for runtime authority paths.
42. Full predecessor test/competence suite is green on final commit.
43. End-to-end Stage 0→22 traces contain no unauthorized authority jump.
44. Adding a newly learned/promoted semantic structure still requires zero concept-specific kernel branch.

---

## 29. Definition of v3.5 final completion

v3.5 is complete when the system can take evidence from a public entrypoint, ground and compose it into UOL, preserve attribution and uncertainty, admit/oppose knowledge with proof, update state/capabilities only through generic authorized transitions, learn new structures through per-use promotion, assess significance, select target-bearing goals, execute authorized operations with crash-safe reconciliation, construct Response UOL, realize it through reviewed multilingual algebra, independently authorize emission, commit only actually emitted discourse/common ground, survive restart/migration/correction—and **no alternative legacy semantic authority remains reachable from a public runtime request**.

At that point the architecture is not merely documented as v3.5; the executable authority graph is v3.5.

---

## 30. Final hardening requirements inherited from the Phase-18/19 implementation audit

Phase 20 must explicitly verify the following late-discovered boundaries before cutover:

1. **Unauthorized external-output evidence cannot disappear.** `EmissionAnomalyRecord` must remain reachable from audit/recovery tooling but unreachable as normal `OutputDiscourseActRecord` or common-ground authority. A mutated/contradictory channel outcome is neither silently dropped nor promoted to authorized speech.
2. **Output-operation lineage is structural.** Runtime emission gates must derive reported operation results from exact Response-UOL source pins, not optional metadata fields.
3. **Acknowledgement and output speaker lineage are exact.** Acknowledgement targets are selected-goal targets; the speaker has an exact durable referent dependency.
4. **Logical migration replay is idempotent across unrelated store revisions.** Cutover rehearsals must prove that rerunning the same exact source/rule/decision batch returns the same committed batch identity and does not create duplicate targets or audit branches.
5. **Split/merge topology is exact.** Migration verification must include one→many and many→one fixtures with exact source/target pin sets and rollback ownership.
6. **Intentional-change waivers are fixture-scoped.** The cutover equivalence report must reject a waiver whose exact approved fixtures are not part of the exact comparison substrate.
7. **No analyzer, language overlay, migration transformer, channel adapter, or compatibility façade self-authorizes from a string identifier or ACTIVE bit alone.** Each must pass its proper reviewed/boot/promotion/contract authority boundary.

These requirements are part of the Phase-20 release blocker set, not post-release cleanup.

## 31. Additional final-audit release blockers

The final Phase-18/19 audit added the following non-waivable cutover checks:

1. Every output discourse act has exact durable referent dependencies for the speaker **and every addressee**.
2. Transport `DELIVERED` cannot imply recipient receipt unless the exact reviewed channel contract structurally declares that acknowledgement semantics prove recipient receipt.
3. Output-reference ambiguity stores candidate identities as candidates, never fabricates evidence refs from semantic target refs.
4. Every MERGED migration target has dependency closure over every exact contributing source pin, not merely the first per-source decision processed.
5. REALIZE authority has exactly one effective active revision per language/grammar authority identity, and overlay authority still requires exact Phase-13 promotion lineage.
6. Semantic analyzer authority is one singular effective reviewed contract revision at both runtime and commit validation.
7. Output correction replacement targets are roots of the exact correcting discourse; opposition targets are exact prior committed targets.
8. Transport exceptions/diagnostics never mint fake EvidenceRecord identities.
9. Channel observations reject contradictory delivery flags before durable semantic/output state is changed.
10. Normal emission cannot be targetless; intentional no-output remains explicit `SilenceOutcomeRecord`.
11. Migration source indexing preserves all contributing sources for split/merge lookup and rollback/audit query plans.

These are included in the final zero-debt/cutover proof, not deferred cleanup.
