# CEMM v3.5 Phases 0–3 Implementation Record

**Baseline:** `bcc77fdf1af7a735e173e873c9fd0585c5bbb80f`
**Runtime status:** isolated migration substrate; not wired as public runtime
**Implemented package:** `cemm.v350`

## Phase 0 — baseline and authority audit

Implemented:

- full static execution-authority audit;
- runtime/write-path map;
- schema/type/UOL migration map;
- claim-admission analysis;
- state/event/capability/impact gap analysis;
- response/template and output-discourse analysis;
- SQLite table-shape inventory;
- test/debt inventory;
- explicit record of unavailable runtime/performance measurements;
- machine-readable legacy-authority debt ratchet.

Artifacts:

```text
docs/audits/v347-authority-audit.md
docs/audits/v347-authority-debt.json
```

The audit changed the Phase 2/3 design. In particular:

- open variables are not restricted to queries;
- parent inheritance is revision-aware;
- semantic-content fingerprints are separate from record/provenance fingerprints;
- propositions and events remain referent-backed;
- a generic `MeaningSchema` cannot bypass typed schema validation;
- known v3.4.7 debt is ratcheted instead of ignored;
- operation authorization is preserved while raw adapter-authored semantic effects are rejected as a v3.5 authority;
- proposition equivalence includes context, modality/scope, time, schema revision, ordering, and assessment/delta structure.

## Phase 1 — governing cutover enforcement

The governing documents were already installed at the pinned baseline. This implementation adds the missing executable enforcement:

```text
cemm/v350/architecture_lint.py
tools/check_v350_architecture.py
.github/workflows/v350-architecture.yml
```

Two policies run together:

1. strict prohibitions over `cemm/v350`;
2. maximum-count debt budgets over retained v3.4.7 authorities.

The debt manifest is not an allow-list for v3.5. It only prevents migration code from deepening known baseline shortcuts before their physical removal.

## Phase 2 — semantic schema metamodel

Implemented one revisioned metamodel authority for:

```text
MeaningSchema
ReferentTypeSchema
FacetSchema
FacetEntitlement
PropertySchema
StateDimensionSchema
StateValueSchema
RelationSchema
RoleSchema
FunctionSchema
ActionSchema
EventSchema
UnitSchema
MeasureDimensionSchema
OperatorSchema
DiscourseActSchema
DiscourseRelationSchema
ResponsePolicySchema
```

Shared infrastructure:

- typed schema family discriminator;
- data-driven semantic type references;
- multiple inheritance;
- revision-aware parent links (`authoritative`, `minimum`, `exact`);
- lifecycle and supersession;
- typed local ports;
- referent storage-kind constraints;
- semantic-application schema-class constraints;
- open binding purposes for query, learning, rules, partial composition, and response planning;
- dependencies with exact/minimum revision requirements and per-use relevance;
- provenance and field lineage;
- independent per-use authorization;
- competence hooks;
- deterministic document codec;
- content fingerprint versus full record fingerprint;
- revisioned registry and authoritative selection;
- cycle detection and type closure;
- typed cross-record validation;
- unresolved-frontier versus active-record hard errors;
- deterministic registry snapshot fingerprint;
- authoritative-revision selection that does not let a newer candidate hide an older active revision;
- parent-family compatibility and parent lifecycle validation;
- entitlement revision/dependency/use/competence validation;
- specialized cross-reference validation for properties, states, roles, functions, relations, measures, and units.

Phase 0 corrections to the earlier Phase 2 draft:

- removed proposition/event as parallel port filler classes;
- replaced `allows_open => queryable` with explicit open-binding purposes;
- replaced unversioned `parent_schema_refs` authority with `SchemaParentLink`;
- gave entitlements the same dependency/use/provenance infrastructure as schemas;
- made generic `MeaningSchema` non-executable;
- replaced numeric-only state ordering with a general ordering key;
- separated semantic equivalence identity from lifecycle/provenance identity.

## Phase 3 — UOL v3 records

Implemented:

```text
Referent
ApplicationBinding
SemanticApplication
SemanticVariable
ScopeRelation
CoordinationGroup
PropositionReferent
ClaimOccurrence
EventOccurrence
StateDelta
CapabilityDelta
ImpactAssessment
ImportanceAssessment
UOLGraph
```

Key invariants:

- `Referent` remains the only identity-bearing filler family;
- proposition, claim, and event records specialize referents through storage kind;
- applications can bind referents, applications, variables, coordination groups, or explicit quoted literals;
- claims do not admit proposition content into the actual world;
- event occurrences do not mutate state;
- state and capability deltas are proof-bearing candidates;
- claimed, hypothetical, counterfactual, fictional, and non-occurring events cannot produce state deltas;
- transition contexts cannot leak;
- impact and importance are stakeholder/context-relative assessments;
- polarity, decrease, loss, capability status, valence, and importance are orthogonal fields/enums;
- no generic `negative` field exists.

Canonical comparison:

- strict record fingerprints retain IDs, lifecycle/provenance, and record detail;
- schema content fingerprints ignore revision-authority metadata;
- UOL semantic graph fingerprints ignore generated graph/application/variable/proposition IDs;
- variable alpha-renaming and binding/map ordering do not affect equivalence;
- polarity, context, schema revision, occurrence status, stakeholder, and semantic axes do affect equivalence.

Validation:

- schema revision/use authorization;
- local-port existence/cardinality;
- filler-class compatibility;
- referent storage/type compatibility through type closure;
- open-variable authorization;
- nested application schema classes;
- proposition content/modality references;
- claim/proposition references;
- event schema/application alignment;
- state-transition admission/context safety;
- capability-delta trigger integrity;
- referent-backed claim/event/proposition context alignment;
- state holder applicability through type closure;
- exact state/action schema revision validation;
- impact and importance source/referent/context integrity;
- ordered filler and list-coordination equivalence;
- admission presence as semantic while proof identifier remains provenance.

## Status gates

| Phase | Specified | Implemented | Wired | Authoritative | Verified |
|---|---:|---:|---:|---:|---:|
| 0 static audit | yes | yes | n/a | yes for migration planning | focused/static |
| 0 runtime metrics | yes | no | no | no | no |
| 1 documentation | yes | baseline already installed | yes | yes | static |
| 1 lints/debt ratchet | yes | yes | CI workflow supplied | no until merged | focused |
| 2 metamodel | yes | yes | isolated only | no | focused |
| 3 UOL records | yes | yes | isolated only | no | focused |

“Focused” means tests executed against the supplied isolated implementation. The full repository suite, executable transcript capture, database measurements, and runtime benchmarks remain merge/CI gates because the review environment could read repository files through the GitHub integration but could not obtain an executable checkout.
