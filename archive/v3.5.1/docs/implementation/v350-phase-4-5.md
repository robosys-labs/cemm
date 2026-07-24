# CEMM v3.5 Phases 4–5 Implementation Record

**Base revision:** `agent/v350-phases-0-3` at `c22ab7dc5ae5972fbc723f009d83203bd3c45fa5`
**Status:** implemented and phase-verified; not yet wired as the public runtime or runtime-authoritative
**Scope:** deterministic data compilation, normalized layered storage, and universal facet/entitlement projection.

## Phase 4 — Data compiler and normalized store

### Reviewed source package

`cemm/data/v350/manifest.json` defines the reviewed source modules. The tree contains separate schema, dynamics, foundation, competence, language, and migration locations. Empty modules are explicit placeholders for later promotion phases rather than hidden boot defaults.

`DeterministicSQLiteCompiler`:

- loads JSONL, JSON, and optional YAML modules without depending on file-system traversal order;
- decodes every document through the typed Phase 2–3 codecs;
- rejects duplicate `(record kind, record ref, revision)` identities;
- validates the complete source package through the same commit-boundary validator used by writable overlays;
- writes records in canonical order;
- records manifest, record-set, and boot fingerprints;
- emits byte-identical SQLite artifacts for identical input;
- publishes with atomic replacement and read-only permissions by default.

The supported command is:

```bash
python tools/compile_v350_data.py \
  --source cemm/data/v350 \
  --output build/cemm-v350.sqlite
```

### Logical-store separation

One SQLite deployment exposes separate typed repositories for:

```text
schemas and entitlements
referents, identity facets, and type assertions
semantic applications and propositions
claims and knowledge
occurrences, state, and capability
impact and importance
rules, evidence, dependencies, and materialized projections
```

The compiled boot database is opened with SQLite immutable read-only mode. Tenant/user/session learning is written only to the overlay database.

### Atomic GraphPatch authority

Every overlay mutation uses one `GraphPatch` transaction with:

- patch-level compare-and-swap against the pinned store revision;
- immutable record revisions;
- optional record revision and fingerprint preconditions;
- exact typed decoding before writes;
- cross-record, schema-revision, local-port, holder-type, context, evidence, and dependency validation;
- atomic patch and operation journals;
- idempotence by patch fingerprint;
- rollback on any invalid operation;
- dependency-driven materialized-view invalidation.

A newer revision may supersede immutable boot data, but no overlay patch may rewrite an existing `(kind, ref, revision)` identity.

### Snapshots and materialized views

A read snapshot pins:

```text
overlay store revision
boot database fingerprint
overlay record-set fingerprint
```

Materialized referent views are derived caches, never truth authority. Invalidation marks a view stale without globally tombstoning its identity, allowing a corrected higher revision to be materialized later.

## Phase 5 — Universal facet and entitlement engine

### Type closure

`TypeClosureCompiler`:

- combines declared types and supported type assertions;
- resolves exact schema revisions;
- traverses multiple inheritance deterministically;
- preserves source assertions and paths;
- does not propagate an opposed or disputed child into supported parent membership;
- reports unresolved and revision-conflicting types;
- carries dependency fingerprints.

### Entitlement projection

`FacetEntitlementProjector` merges contracts using explicit laws:

```text
inherit
compose
extend_domain
narrow_domain
override
block
```

More-specific overrides remove only less-specific inherited contracts. Equal-specificity peer contracts remain visible and may produce contradiction. A specific prohibition blocks an inherited license. Context, temporal, and dependency constraints produce `blocked`, `inapplicable`, or `contradicted` projections rather than fabricated state.

Projection statuses remain distinct:

```text
active
latent
default_expected
unknown
blocked
terminated
inapplicable
contradicted
```

### Defaults

`DefaultRuleRecord` is revisioned and lifecycle-bearing. `DefaultExpectationProjector` selects one effective active revision, evaluates conditions and defeaters, pins expected state-schema revisions, and returns cycle-local expectations. It never creates an active `StateAssignment`.

### State and capability views

`StateApplicabilityAssessor` checks:

- holder-type applicability;
- facet licensing;
- exact dimension/value revisions;
- context and validity intervals;
- supported versus opposed assignments;
- exclusivity conflicts;
- entitlement value domains;
- historical termination;
- defaults only when actual state is absent.

Capability projections preserve `available`, `blocked`, `unavailable`, `terminated`, `conditional`, `degraded`, and `unknown` evidence. Conflicting availability records become `contradicted`.

### Referent knowledge envelope

`ReferentKnowledgeProjector` builds one cycle-pinned read-only view containing type closure, identity facets, entitlements, state timelines, relevant applications, event history, capabilities, defaults, significance assessments, and epistemic records. Epistemic records are restricted to propositions whose semantic applications involve the projected referent; unrelated knowledge in the same context is excluded.

Condition evaluation is typed and time-aware. Merely mentioned, reported, hypothetical, counterfactual, fictional, or planned events do not satisfy occurrence conditions.

## Verification

The phase suite proves:

- deterministic byte-identical compilation;
- boot/overlay precedence and immutable revision history;
- atomic rollback, patch idempotence, store CAS, and record CAS;
- typed local-port and holder applicability validation;
- materialized-view invalidation and rematerialization;
- deterministic multiple inheritance and opposition safety;
- required, optional, prohibited, blocked, latent, unknown, active, default, terminated, and contradicted projections;
- domain narrowing and override laws;
- context and time isolation;
- defaults remain non-factual;
- effective default-rule supersession;
- referent knowledge excludes unrelated contextual knowledge.

Current focused result: **81 tests passed**, architecture lint passed, and Python compilation passed.

## Deferred authority

These phases deliberately do not:

- populate the Phase 6 foundational seed records;
- wire v3.5 as the public runtime;
- compile lexical/language packages;
- perform event transition commits;
- replace v3.4.7 migration authority.

Those remain later phases. No Phase 4–5 component claims runtime authority before cutover and complete repository CI.
