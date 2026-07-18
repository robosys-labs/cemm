# CEMM v3.5 reviewed semantic source package

This tree is the modular, language-neutral input to the deterministic Phase-4
SQLite compiler. It is reviewed source, not Python ontology authority.

## Phase ownership

- **Phase 4** supplies manifest loading, typed decoding, whole-package validation,
  deterministic compilation, immutable boot storage, and writable overlays.
- **Phase 5** derives type closure, facet entitlements, defaults, states,
  capabilities, and referent knowledge views.
- **Phase 6** supplies the minimal structural foundation and independent
  competence gates in this directory.
- **Phase 7** owns reviewed language packs, forms, lexical senses, reversible
  form-sense links, construction contracts, and adapter-produced syntax evidence.
- **Phase 8** owns joint referent/claim grounding hypotheses and reviewable
  provisional, merge, and split proposals.
- **Phase 9** owns cycle-local UOL factor-graph composition, bounded meaning
  hypothesis solving, partial-understanding frontiers, and selection traces.
- **Phase 10** owns attributed claim occurrence/history, independent epistemic
  admission, source/evidence assessment, four-state truth projection, and
  admission-lineage knowledge projection.
- **Phase 11 and later** own event transitions, downstream inference/effects,
  realization, migration, and runtime cutover.

Empty later-phase modules are explicit boundaries. They are not silently
replaced by code defaults.

## Phase-6 seed layers

```text
6A  broad referent-type anchors and multiple inheritance
6B  universal facets and entitlement contracts
6C  native semantic axes and operators
6D  properties, state dimensions, values, measures, and relations
6E  generic action/event, claim, discourse, and response-policy schemas
6F  function/capability distinction and truthful self contracts
6G  identity/evidence fixtures and non-factual default expectations
6H  declarative competence cases and deterministic verification
```

The package deliberately does **not** seed domain concepts such as person,
animal, server, bank, fox, battery, pregnancy, fraud, marriage, or biological
death. Those remain learned or separately promoted domain knowledge.


## Phase-7 language evidence layers

```text
7A  revisioned language packs and script/locale contracts
7B  observation lattice and reversible normalization evidence
7C  forms separated from lexical senses and semantic targets
7D  dependency/constituency adapter evidence boundary
7E  coordination, complement, relative-clause, ellipsis, and argument frames
7F  span-local language evidence and code switching
7G  deterministic language registry, storage, and review contract
```

Language forms never carry semantic authority directly. A form may link to
multiple revision-pinned senses; each sense points to a reviewed semantic
schema/operator/deictic target and declares the authorized use. Dependency and
constituency adapters contribute evidence only and cannot select a semantic
target. Ordinary full-sentence patterns are prohibited; only records explicitly
classified and reviewed as genuine idioms may use them.

## Phase-8 grounding layers

```text
8A  mention hypotheses preserving lexical and target-class ambiguity
8B  store, identity, discourse, multimodal, output, schema, and provisional candidates
8C  context/time/type/storage/description/source/audience factors
8D  bounded deterministic joint assignment with coreference/distinctness constraints
8E  claim source/audience/attributed-context grounding without admission
8F  review-only provisional referent and identity merge/split proposals
```

Grounding produces candidates, assignments, frontiers, and proposals. It does
not create actual-world knowledge, mutate identity, merge referents, or treat a
sole provisional candidate as resolved. Referent remains the only identity-bearing
semantic filler family.

## Phase-9 UOL composition layers

```text
9A  exact sense/schema/referent variables from pinned Phase-7/8 evidence
9B  explicit port, type, context, time, scope, and evidence constraints
9C  traceable discourse/world/default/complexity ranking factors
9D  bounded deterministic beam search with hard-pruning trace
9E  partial-safe UOL materialization with explicit open variables
9F  close-alternative preservation and selection assessment
9G  deterministic review contract and competence verifier
```

The solver has no predicate, event, type, or language knowledge. Exact reviewed
schema revisions and their use/port contracts compile into finite factor tables
before search. Grounding confidence is decomposed into named evidence factors;
it is not hidden in one opaque candidate score. Event mentions remain mentioned,
claims remain unadmitted, defaults only rank, and no state/capability delta is
committed by composition. Meaning selection never consults target-language
realization.

## Phase-10 epistemic layers

```text
10A structural claim occurrence compilation from selected UOL
10B attributed source/reported-context separation
10C append-only claim history with source-local correction/retraction
10D independent revisioned source authority/reliability/access/bias assessment
10E explicit policy + authorization + proof admission gate
10F independent support/opposition admissions and derived four-state truth
10G knowledge projection retaining exact admission lineage
10H deterministic contract/competence verification
```

A grammatical or well-grounded claim remains attributed evidence by default.
Actual-world support/opposition is a separate durable `EpistemicAdmissionRecord`
that requires an explicit authorization reference, proof, source evidence, exact durable source-assessment records, and
policy satisfaction. Retractions are separately authorized/proof-bearing and may
only retract the same source lineage. `BOTH` is derived from independent active
support and opposition records; no single record can assert it. Corrections and
retractions are append-only history rather than destructive rewrites. Phase 10
never emits state or capability deltas.

## Critical invariants

- A storage kind is never a semantic ontology type.
- Defaults are rules and never boot-time active state assignments.
- A claim schema does not admit its content as actual-world knowledge.
- Event schemas in Phase 6 do not yet authorize transitions, causality, or impact; the UOL validator enforces exact transition-use authorization.
- Function persists independently of live capability.
- Only runtime-backed self capabilities are marked available.
- Language analysis evidence is available; language realization remains explicitly unavailable until Phase 17.
- Language-specific forms are Phase-7 reviewed data and never foundation ontology authority.
- No ordinary full-sentence response or analysis templates are permitted.
- Code switching is represented by span-local evidence rather than one utterance-wide language label.
- Unknown names and typed mentions remain explicit grounding frontiers.
- Claims preserve source and audience but have no actual-world admission by default.
- Actual-world epistemic admission requires explicit durable authorization, proof, source evidence, revisioned source-assessment records, and policy satisfaction.
- Metadata never authorizes context crossing; cross-context knowledge requires resolvable active admission lineage.
- SQLite schema changes are versioned; Phase-10 normalized authorities require schema version 3.
- Claim corrections/retractions and admission retractions are append-only and source-local.
- Four-state `both` is derived from independent support/opposition; it is never one record's truth flag.
- Identity merge/split and provisional referent creation require reviewable proposals.
- Truth support, epistemic basis, proposition polarity, change direction, and evaluative valence remain separate axes.
- Importance/valence are assessment vocabularies, and capability status is record-scoped; none is silently materialized as ordinary holder state.
- Exact record counts and a full source-record fingerprint are contract-pinned; the contract and competence files are SHA-256 pinned by the manifest.

## Verification

```bash
python tools/verify_v350_foundation.py
python tools/verify_v350_language_grounding.py
python tools/verify_v350_composition.py
python tools/verify_v350_epistemics.py
```

The foundation verifier audits only manifest modules owned by Phases 0–6, so the
frozen foundation contract cannot be changed accidentally by later reviewed
packages. The language/grounding verifier audits `language_grounding_contract.json`,
checks pinned competence hashes and source fingerprints, compiles twice, requires
byte-identical SQLite output, opens the artifact immutably, and executes the
composition, multilingual, and grounding competence suites. The Phase-9 verifier audits the pinned composition contract, proves deterministic compilation, and executes bounded multilingual UOL composition cases without admitting claims or firing transitions. The Phase-10 verifier audits the
pinned epistemic contract, deterministic compilation, attributed claim/history
separation, explicit authorization/proof admission, source-local retraction, and
four-state truth projection without state/capability effects.
