# CEMM v3.5 Phase 19 — Migration and Semantic Equivalence

## 1. Objective

Migrate retained useful legacy CEMM data into v3.5 **without migrating legacy authority, hidden shortcuts, or semantic ambiguity**.

Migration is a typed semantic translation with proof, quarantine, rollback, and behavioral equivalence claims. It is not “copy old tables into new tables until tests pass.”

---

## 2. Governing laws

1. **Legacy data is evidence/input, not authority.** Old enums, keyword maps, response templates, event-specific handlers, and mutable blobs do not gain v3.5 authority merely because they existed in production.
2. **Every migrated record has an explicit mapping decision.** `mapped | transformed | split | merged | quarantined | rejected | intentionally_not_migrated`.
3. **No silent semantic coercion.** If a legacy concept conflates multiple v3.5 axes, split it or quarantine it.
4. **Exact source→target lineage is durable.** Every target pin traces to source record/version/fingerprint and migration rule revision.
5. **Equivalence is claimed only where proved.** Structural representability is separate from behavioral equivalence.
6. **Rollback is data-level and deterministic.** Migration batches can be reversed without deleting unrelated v3.5-native learning/history.
7. **No permanent migration authority path.** After cutover, migration adapters are offline tooling, never runtime semantic routers.
8. **Corrections/retractions survive.** Do not flatten historical revisions into one “latest truth.”
9. **Permissions/privacy cannot broaden.** Unknown legacy scope defaults narrow/quarantined, never public.
10. **Learned candidates remain candidates unless v3.5 competence/promotion lineage exists.** Legacy confidence scores cannot substitute for Phase-13 competence.
11. **Language data is separated from semantics.** Legacy words/templates do not become semantic schema definitions.
12. **Operation history distinguishes intent, submission, result, and observed effect.** Do not backfill false success from legacy “completed” flags without evidence.

---

## 3. Migration inventory and classification

Build a complete inventory before conversion:

```text
legacy source
record/table/file/path
record count
schema/version
semantic role
current runtime authority?
privacy scope
history/revision model
known consumers
migration disposition
```

Classify sources into:
- referents/identity;
- type/facet/property/state;
- actions/events/transitions;
- claims/knowledge/evidence;
- learned rules/defaults;
- language/lexical/grammar data;
- response policies/goals;
- operations/tool history;
- conversation/output history;
- caches/materialized views;
- deprecated hacks/keyword maps/templates.

Caches and derived legacy projections should normally be recomputed, not migrated as authority.

---

## 4. Durable migration contracts

### 4.1 `MigrationSourceRecord`

Pins immutable source artifact:
- system/version;
- source locator;
- source primary key;
- source revision/timestamp;
- content fingerprint;
- privacy/scope evidence;
- extraction tool revision.

### 4.2 `MigrationRuleRecord`

Defines a reviewed transformation structurally:
- accepted source shape/version;
- target record family;
- field mappings;
- split/merge policy;
- context/time conversion;
- permission policy;
- validation requirements;
- known-loss declarations;
- competence/equivalence cases;
- revision/provenance.

No concept-name branch in generic migration kernel.

### 4.3 `MigrationDecisionRecord`

Per source record:
- source pin;
- rule pin;
- disposition;
- target pins or quarantine ref;
- warnings/losses/ambiguities;
- reviewer/authorization refs where required;
- proof refs.

### 4.4 `MigrationBatchRecord`

- batch ref;
- source set fingerprint;
- rule-set fingerprint;
- expected target-store snapshot;
- decisions;
- commit status;
- rollback refs;
- metrics/errors.

### 4.5 `MigrationQuarantineRecord`

Preserves unrepresentable/unsafe material:
- raw source pin;
- reason codes;
- ambiguous candidate target families;
- missing dependencies;
- sensitivity/permission;
- remediation frontier;
- explicit non-authority flag.

### 4.6 `SemanticEquivalenceRecord`

Pins source behavior fixture and v3.5 behavior trace.

Dimensions:
- selected meaning;
- referent identity;
- epistemic stance;
- state transition;
- capability status;
- impact/importance;
- goal selection;
- operation decision;
- Response UOL;
- emitted semantic commitment where relevant.

Outcome:
`equivalent | intentionally_changed | partially_equivalent | not_equivalent | untestable`.

### 4.7 `MigrationRollbackRecord`

Contains exact target records introduced/superseded by batch and inverse operations. Never assumes “restore database backup” is sufficient when concurrent v3.5-native writes exist.

---

## 5. Source→target mapping rules

### 5.1 Identity/referents

- preserve stable identity only when identity criterion/evidence supports it;
- split overloaded legacy entities;
- preserve aliases as language/identity evidence, not type definitions;
- ambiguous merges go to quarantine.

### 5.2 Types/facets/properties/state

Legacy flat attributes must be classified:
- identity facet;
- property;
- state dimension/value;
- relation/role;
- metadata-only provenance.

Do not turn arbitrary JSON keys into new kernel enums.

Legacy current-value blobs require time/context/source reconstruction. Missing historical evidence must remain unknown, not fabricated.

### 5.3 Actions/events/transitions

- map action/event schemas separately from occurrences;
- migrate state effects only when expressible as generic transition contracts;
- event-specific mutation code becomes migration evidence/test fixtures, not runtime handlers;
- capability effects map to capability dependency/state rules where representable.

### 5.4 Claims/knowledge

Legacy “memory facts” must be decomposed into:
- proposition;
- source/claim occurrence where reconstructable;
- evidence;
- epistemic admission/knowledge projection.

A stored sentence or key/value pair is not automatically knowledge.

### 5.5 Learning

- legacy learned concepts/rules become candidates/packages unless exact evidence, counterexample, competence, and per-use promotion lineage can be reconstructed;
- confidence thresholds cannot synthesize competence;
- failed/negative examples remain attributable.

### 5.6 Language

Separate:
- forms;
- lexical senses;
- form-sense links;
- constructions;
- argument frames;
- morphology;
- realization rules.

Reject ordinary full-sentence templates as realization authority except reviewed genuine idioms/literal response policies.

### 5.7 Response/goals

Legacy intent labels or canned response categories become evidence for semantic policy candidates only where mappings are explicit. Generic “acknowledge” with no semantic target is rejected.

### 5.8 Operations

Legacy tool/action logs split into:
- requested goal/intention;
- plan/authorization if reconstructable;
- submission evidence;
- result evidence;
- observed effects;
- unknown outcome.

Never infer observed success merely from `status=completed` without trustworthy semantics.

### 5.9 Output history

Migrate semantic output history only where content/targets can be reconstructed safely. Raw transcripts can remain evidence archives; they do not become common-ground authority by themselves.

---

## 6. Migration engine architecture

### `SourceExtractor`
Read-only, deterministic source snapshots with fingerprints.

### `MigrationClassifier`
Structural source-family classification. No business/domain keyword authority.

### `MigrationRuleRegistry`
Reviewed rules by source shape/version and target family.

### `MigrationTransformer`
Pure transformation producing candidate target records + warnings; no store writes.

### `MigrationValidator`
Runs ordinary v3.5 validators/registries/competence requirements against staged target records.

### `MigrationCommitCoordinator`
Atomic GraphPatch per bounded batch with source/rule dependencies and rollback record.

### `QuarantineCoordinator`
Preserves untranslatable material as non-authority with remediation frontier.

### `EquivalenceRunner`
Runs pinned before/after fixtures/traces and compares semantic outcomes.

---

## 7. Equivalence methodology

### 7.1 Establish legacy baseline

Freeze:
- code version;
- source database snapshot;
- deterministic test inputs;
- observable outputs/state changes;
- known bugs that must **not** be preserved.

### 7.2 Semantic, not string, comparison

Compare:
- selected schemas/referents/bindings;
- contexts/time/polarity/modality;
- knowledge status;
- state/capability changes;
- exact response targets/goals;
- Response UOL;
- operation effects.

Surface text similarity is secondary.

### 7.3 Intentional-change registry

Known legacy bugs/shortcuts should be explicitly marked `intentionally_changed`, e.g.:
- keyword→intent routing;
- claims stored directly as facts;
- targetless acknowledgements;
- event-specific state mutation;
- sentence templates;
- confidence-only learned authority.

This prevents “equivalence” tests from forcing regressions back into v3.5.

---

## 8. Dependency ordering

Recommended migration order:

1. permission/context/time primitives;
2. referent types + schemas;
3. facet entitlements;
4. referents/identity facets/type assertions;
5. language packs/forms/senses where semantics already exist;
6. propositions/claims/evidence;
7. knowledge/state history;
8. transition/capability contracts;
9. learning packages/promotions only when lineage valid;
10. impact/importance/policies;
11. goals/operations where reconstructable;
12. output discourse/common ground;
13. derived views recomputed last.

Dependency cycles become quarantine/frontiers, not arbitrary load order.

---

## 9. Rollback strategy

- every batch pins pre-commit store revision;
- target records introduced by migration carry source/batch dependency;
- rollback tombstones/supersedes only records owned by that batch;
- never delete later native records depending on migrated material without explicit invalidation/recompute;
- rollback produces its own durable audit record;
- source system remains untouched/read-only.

---

## 10. Security/privacy

- default unknown scope to narrow/quarantine;
- redact/encrypt source dumps appropriately;
- migration tools run least privilege;
- source secrets/tokens are not migrated as semantic data;
- user deletion/retention requirements preserved;
- provenance cannot expose private source content into public metadata;
- migration logs avoid raw sensitive payloads where fingerprints/refs suffice.

---

## 11. Acceptance matrix

1. every migrated target has exact source+rule lineage;
2. unmappable data is quarantined, never silently dropped/coerced;
3. legacy keyword maps do not become runtime authority;
4. legacy sentence templates do not become generic realization rules;
5. claims are not migrated directly as facts;
6. state history preserves context/time/source where known;
7. unknown timestamps remain unknown, not “now”;
8. permission never broadens silently;
9. learned material without competence remains candidate/non-authoritative;
10. counterexamples/corrections survive migration;
11. event effects use generic transition contracts or are quarantined;
12. capability history is not flattened into permanent booleans;
13. operation “success” without evidence becomes unknown where necessary;
14. raw transcript does not become common-ground authority;
15. batch rollback preserves unrelated native writes;
16. restart yields identical migrated effective authority;
17. rerunning same batch is idempotent;
18. source record renaming without structural change does not alter generic migration behavior;
19. equivalence claims distinguish equivalent vs intentional fix;
20. no migration adapter remains reachable from normal runtime semantic paths.

---

## 12. Scale/performance gates

Measure:
- extraction throughput;
- transformation/validation throughput;
- batch transaction size/latency;
- dependency closure cost;
- quarantine rate by family;
- target index/query plans;
- equivalence-suite runtime;
- rollback cost.

Use bounded batches, resumable checkpoints, deterministic IDs, and content fingerprints. Never trade semantic validation for bulk-copy speed.

---

## 13. Implementation sequence

### 19A — complete legacy authority/data inventory
### 19B — freeze source snapshots and baseline fixtures
### 19C — migration durable contracts + schema/indexes
### 19D — source extractors/fingerprints
### 19E — structural migration rule registry
### 19F — schemas/referents/facets migration
### 19G — claims/evidence/knowledge/state migration
### 19H — transitions/capabilities migration
### 19I — learning/language migration
### 19J — impact/goals/operations/output-history migration
### 19K — quarantine/remediation frontier system
### 19L — atomic batches/idempotency/rollback
### 19M — semantic equivalence runner + intentional-change registry
### 19N — full-scale rehearsal and query-plan/performance proof
### 19O — production migration, verify, freeze legacy writes
### 19P — remove migration adapters from runtime authority paths

---

## 14. Exit gate

Phase 19 passes only when every retained legacy semantic artifact is either explainably mapped with exact lineage and validated v3.5 authority, explicitly quarantined/rejected, or intentionally omitted; claimed equivalence is evidence-backed; rollback is safe; privacy is preserved; and no legacy migration adapter remains a competing runtime semantic authority.
