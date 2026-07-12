# CEMM v3.4 — Final Integrated Implementation Plan

Baseline: `8e0da751edbd86460049ef14f56fda66cc05de84`

This plan replaces document-only deltas with one authoritative migration path. It preserves the v3.4 macro architecture and strengthens the existing schema, understanding, epistemic, learning, replay, and commit components.

## Completion terminology

Every phase reports:

```text
specified
implemented
wired
authoritative
verified
```

No phase is complete from files/classes alone.

## Phase 0 — Promote governing architecture

Replace root `AGENTS.md` and `cemm/ARCHITECTURE.md` with the integrated versions in this package.

Move detailed v3.4 contracts under `cemm/newarch/` and update its README.

Gates:

- root documents declare v3.4 and latest baseline;
- no v3.1/v3.3 file outranks v3.4;
- architecture-version test fails on drift;
- removed legacy docs are archived or referenced only as historical.

## Phase 1 — Canonical immutable model and fingerprints

Implement/update:

```text
EvidenceRecord lineage fields
Proposition interpreted_under / derivation fields
SchemaContribution
SchemaDependency
GroundingSpecification
CompetencyCase
SchemaGroundingAssessment
SchemaUseProfile
ReplayWorkItem
DerivedArtifactProvenance
AssessmentEnvironmentFingerprint
```

Gates:

- no new canonical semantic object family;
- records are immutable and serializable;
- content hashes/fingerprints are stable;
- historical schema revisions remain resolvable.

## Phase 2 — SemanticSchemaStore lifecycle and atomic activation

Implement one schema store with strict lifecycle:

```text
candidate → provisional → active → superseded/rejected
```

Add:

```text
typed reverse dependencies
context/time applicability
explicit supersession/equivalence
CAS activation
atomic cluster activation
revision retention
```

Gates:

- no overlay or second resolver;
- validator cannot activate;
- concurrent child revisions never silently merge;
- boot and learned schemas use identical store APIs.

## Phase 3 — Foundations and boot validation

Split startup resources into:

```text
kernel value/foundation implementations
audited boot schema manifest
language lexicalizations
```

Implement independent property/invariant tests, adapter observation contracts, failure/downgrade policy, and version fingerprints.

Gates:

- a failing formal foundation halts or enters explicit diagnostic-safe mode;
- failing optional boot concepts remain opaque/provisional;
- boot example pairs cannot self-certify.

## Phase 4 — Canonical perception and compositional understanding

Unify raw/normalized/morphological streams, preserving contractions, offsets, quotes, negation, and clause structure.

Replace phrase-authority behavior with candidate-only lexical/construction/pragmatic evidence.

Implement nested propositions and schema-generic roles.

Vertical tests:

```text
I'm an engineer.
What do I do?
Do you know what an engineer is?
You don't know what “know” means.
```

Gates:

- `I'm` decomposes without losing raw evidence;
- assertion stores exact required `is_a`/occupation relation;
- arbitrary epistemic nesting works without whole-phrase aliases;
- pragmatic cues never erase content propositions.

## Phase 5 — Grounded understanding and schema use

Implement:

```text
schema-family Grounded Definition Closure
pattern function + strength
sense candidate clusters and reversible assignment
field-level provenance
recursive component classification
sandboxed competence harness
context-specific SchemaUseProfile
```

Gates:

- a known lexeme or schema ref does not imply understanding;
- self-derived cases cannot produce active status;
- typical properties do not close definitions;
- unsupported constructs produce explicit blockers;
- opaque/provisional meanings remain safely preservable.

## Phase 6 — Epistemic admissibility and self-awareness

Extend `EpistemicEvaluator` for:

```text
actual vs reported/user-belief/hypothetical contexts
schema-definition proposition support
lineage-independent support
causal warrant grade
operation-relative understands
```

Self-capability queries use live component, resource, permission, and competence records.

Gates:

- structurally complete false definitions remain attributed theories;
- `understands` states exact supported competencies and limitations;
- static schema declarations cannot advertise capabilities;
- self-report clauses are evidence-bound.

## Phase 7 — Meaning-backed recursive learning

Implement the final learning transaction:

```text
target discrimination
bounded grounding frontier
minimal probes
child revision
lineage-aware competence
admissibility
ordinary replay
CAS activation or provisional commit
resume blocked goal
```

Gates:

- learning changes the ordinary resolver;
- probe/replay budgets are resumable and non-repetitive;
- alias/new sense/specialization/correction hypotheses compete;
- no external action repeats during replay;
- outcome wording matches remembered/provisional/understood/known state.

## Phase 8 — Invalidation, truth maintenance, and replay safety

Index every derived artifact by supporting schema revisions and environment fingerprint.

Implement typed invalidation and replay events, deduplication, stale cancellation, and support-cycle detection.

Gates:

- parent downgrade retracts classifications, inferences, answers, plans, messages, and effect proposals;
- evidence remains;
- cross-schema inference laundering does not increase support;
- duplicate replay delivery produces one result;
- in-flight effects reauthorize against current state.

## Phase 9 — Live effects, causality, and commit correctness

Remove schema-level persistent effect authority.

Implement causal warrant grades and require live authorization/critical-commit revalidation.

Fix exact write contracts and operation-level outcomes.

Gates:

- teaching a causal/effect schema fires no effect;
- prediction differs from observation/commit;
- auxiliary schema/concept writes cannot satisfy requested relation writes;
- completion claims require exact required commits.

## Phase 10 — NLG, common ground, and repair

Ensure response content begins from propositions, assessments, ledger, and commit outcomes.

Implement qualified language for:

```text
reported theory
provisional understanding
contested evidence
known limitations
stale/repaired prior claims
```

Output common-ground mutation occurs only after dispatch success.

Gates:

- every clause has semantic provenance;
- no internal IDs or open ports leak;
- generated content reparses compatibly;
- invalidated prior output can generate a repair obligation.

## Phase 11 — Correction, retraction, and retention

Implement exact operations for supersession, evidence retraction, permission revocation, archival, forgetting, and privacy deletion.

Gates:

- removed support stops contributing;
- dependent cognition re-evaluates;
- historical meaning remains where policy permits;
- archival cannot masquerade as privacy deletion.

## Phase 12 — Legacy retirement and authoritative cutover

Remove/demote:

```text
whole-turn operational aliases
conversation-act content authority
ActionOperatorSchema as competing verb authority
SessionLearningOverlay
hard-coded role loops
graph-build-time effects
runtime-local query/write authorities
static capability responder
```

Run the complete acceptance suite and cross-language semantic equivalence tests.

## First implementation vertical slice

1. Promote governing documents.
2. Implement immutable records/fingerprints and one schema store.
3. Fix canonical contraction/token stream.
4. Store/query `I'm an engineer` correctly.
5. Parse nested `Do you know what an engineer is?`.
6. Preserve unknown `engineer` as opaque while remembering the user fact.
7. Learn a provisional definition with field provenance.
8. Refuse self-certification; report provisional use honestly.
9. Add independent contrast and atomically activate.
10. Query definition, occupation, and self-understanding through ordinary NLG.

This slice exercises the complete foundation without requiring every domain schema or external adapter.
