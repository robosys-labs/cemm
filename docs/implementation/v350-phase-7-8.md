# CEMM v3.5 Phases 7–8 Implementation Record

**Patch base:** `e05b1021a2b155050b400995d95b946d950c9316` (`Implement phase 6`)
**Status:** implemented and phase-verified; not public-runtime-wired or runtime-authoritative
**Scope:** reversible multilingual form/sense evidence and joint referent/claim grounding.

## 1. Governing alignment

This implementation follows the v3.5 learning-first architecture and the Phase 7–8 execution order:

- forms remain separate from senses;
- semantic targets remain revision-pinned reviewed data;
- syntax analyzers contribute evidence and never semantic authority;
- code switching is span-local;
- coordination, complement, relative clause, ellipsis, and argument structure are compositional records;
- ordinary full-sentence patterns are prohibited;
- normalization remains reversible evidence;
- referents, events, states, propositions, schemas, multimodal tracks, system output, claim participants, and provisional mentions participate in one joint grounding problem;
- claims are grounded without actual-world admission;
- provisional identities and merge/split changes are proposals requiring review.

The implementation deliberately stops before Phase 9 UOL factor-graph composition. Phase 7 construction candidates and Phase 8 grounding assignments are proof-bearing inputs to that later composer, not a hidden replacement for it.

## 2. Phase 7 subphases

### 7A — Reviewed language authority

Added revisioned records for:

```text
LanguagePackRecord
LanguageFormRecord
LexicalSenseRecord
FormSenseLinkRecord
ConstructionRecord
```

They use the same lifecycle, immutable revision, deterministic codec, SQLite normalization, typed repository, CAS GraphPatch, and boot/overlay precedence as the semantic substrate.

Language data is carried in six Phase-7 manifest modules with `authority_scope=language_evidence`. Phase-6 foundation verification filters by phase ownership, allowing the foundation fingerprint to remain frozen while later reviewed records compile into the same boot database.

### 7B — Observation and form lattice

`FormLatticeAnalyzer` produces immutable evidence for:

- Unicode-normalized observations and exact source spans;
- span-local language candidates;
- exact and multiword forms;
- reversible normalization proposals;
- lexical-sense candidates;
- dependency and constituency parse evidence;
- construction candidates;
- deterministic lattice nodes and edges;
- unresolved spans and evidence lineage.

No analyzer step writes knowledge or chooses a final world referent.

### 7C — Forms and senses

A form contains orthographic/morphological evidence only. A separate form-sense link provides prior weight and provenance. A lexical sense declares:

```text
semantic target kind/ref/revision
schema class where applicable
expected referent types
scope behavior
use operation
lifecycle and provenance
```

A form can have multiple senses, and one sense can be lexicalized by multiple forms and languages. Semantic schema revisions are validated at the durable commit boundary.

### 7D — Syntax adapter boundary

Dependency and constituency adapters implement evidence-only interfaces. Their outputs preserve adapter identity, source observations, arcs/nodes, confidence, and evidence references. Adapter identifiers can never become semantic targets.

### 7E — Construction algebra

Reviewed constructions cover English, French, and Swahili:

```text
AND/OR coordination
complements
relative clauses
ellipsis with explicit semantic gaps
claim frames
observation frames
```

Construction slots constrain lexical categories, schema classes, dependency positions/relations, cardinality, semantic ports, and trigger senses. Matching is trigger-anchored and enumerates bounded deterministic construction instances, so repeated clauses retain distinct frames instead of collapsing into one utterance-wide candidate. Trigger edges and exact trigger references are preserved in the lattice. Optional ordinary arguments do not become ellipsis gaps. Only ellipsis constructions may emit explicit gap references.

### 7F — Code switching and normalization

Language evidence is attached to individual spans, so one utterance can combine languages without forcing a single language label. Colloquial normalization is represented as a reversible proposal that preserves original text, replacement, rule/evidence references, and candidate lineage.

### 7G — Review contract

`language_grounding_contract.json` pins:

- exact Phase-7 record counts;
- required languages, construction kinds, and semantic targets;
- all competence case references;
- canonical source-record fingerprint;
- exact patch base commit.

The manifest SHA-256-pins the contract and three competence files. Unreviewed records, changed cases, or modified contract data fail the audit.

## 3. Phase 8 subphases

### 8A — Mention hypotheses

`MentionCompiler` converts lexical/construction evidence into hypotheses for:

```text
ordinary referents
participants and descriptions
event occurrences
state occurrences
propositions
schema topics
claim source and audience
deictic/anaphoric references
provisional typed mentions
```

Lexical ambiguity and unresolved spans are preserved rather than prematurely collapsed. Reviewed construction slots propagate semantic participant roles—such as claimant, audience, observer, and proposition—from construction evidence into mention hypotheses instead of using token-position heuristics.

### 8B — Candidate providers

`GroundingCandidateProvider` jointly gathers candidates from:

- canonical referents and identity facets;
- semantic description applications;
- discourse anchors;
- multimodal tracks;
- prior system-output anchors;
- exact active schema topics;
- provisional referent proposals.

Self and addressee deictics have constrained providers. Demonstratives compare multimodal and system-output anchors rather than falling back to arbitrary stored referents. Lexical event/state predicates introduce new provisional typed occurrences; they cannot attach to an arbitrary historical occurrence merely because its broad type matches. Existing occurrences require independent identity, description, discourse, or deictic evidence. Provisional candidates remain frontiers even when they are the only candidate.

### 8C — Typed grounding factors

Candidates carry explicit factors for:

```text
identity/name match
description satisfaction
type closure
storage kind
context compatibility
time compatibility
discourse salience
multimodal salience
system-output recency
schema revision
provisional status
```

Resolved multimodal candidates expand their complete semantic type closure. Context/time constraints are hard rejection boundaries where required.

### 8D — Joint solver

`JointGroundingSolver` performs bounded deterministic assignment across all mentions. It supports required coreference, distinctness, context, type, storage, source, and audience constraints. It retains ranked assignments, unresolved frontiers, and ambiguous mention references.

Selection occurs only when the margin and evidence are sufficient. A sole provisional assignment cannot be reported as resolved, and a mention whose candidates are all provisional remains explicitly listed as unresolved while its frontier is preserved.

### 8E — Claims

`ClaimGroundingCompiler` requires an explicit unambiguous assignment and preserves:

```text
claim mention
claimant/source
audience
proposition
source context
reported/attributed context
evidence lineage
```

Its admission-reference set is always empty. The compiler verifies that the claim resolves to an event occurrence, claimant and audience candidates are agent-compatible, and source/reported contexts remain distinct. Explicitly selected provisional participants or occurrences cap confidence below settled-identity confidence. Grounding a grammatical claim never creates a knowledge record or state transition.

### 8F — Identity proposals

`ProvisionalReferentPlanner` emits a reviewable GraphPatch proposal; it never applies it. `IdentityProposalEngine` emits merge and split proposals carrying reasons, evidence, confidence, and review-required status. No automatic identity mutation occurs.

## 4. Persistent storage

SQLite schema version 2 adds normalized tables for:

```text
language_packs
language_forms
lexical_senses
form_sense_links
constructions
construction_slots
```

Language records participate in deterministic compilation, record fingerprints, boot database fingerprints, immutable history, GraphPatch validation, typed repositories, and snapshot-keyed registry caching.

## 5. Reviewed language package

The package contains:

```text
3 language packs
75 forms
51 lexical senses
85 form-sense links
21 constructions
1 reviewed language evidence record
```

Initial languages are English, French, and Swahili. The package is deliberately structural and domain-light; it does not seed domain nouns such as person, fox, server, bank, battery, pregnancy, fraud, or death.

## 6. Verification

The Phase 7–8 verifier performs:

1. contract/count/hash/source-fingerprint audit;
2. two deterministic boot compilations and byte comparison;
3. immutable boot database opening;
4. composition competence with data-declared dependency arcs;
5. multilingual/code-switching and semantic-target equivalence checks;
6. temporary overlay grounding fixtures;
7. joint grounding, claims, provisional identity, merge, and split cases;
8. exact competence-case coverage verification.

Current results:

```text
156 Phase 0–8 focused tests passed
24/24 declarative Phase 7–8 competence cases passed
architecture lint passed
Python compilation passed
boot SQLite compilation is byte-identical
650 compiled records
```

## 7. Deliberate deferrals

These phases do not:

- make the v3.5 pipeline the public runtime;
- implement Phase 9 UOL factor-graph composition;
- admit claims into actual-world knowledge;
- implement event state transitions or causal/impact effects;
- perform identity merge/split automatically;
- implement multilingual NLG or mark language realization available;
- migrate or remove v3.4.7 runtime authority.

Those boundaries prevent Phases 7–8 from silently absorbing responsibilities assigned to later phases.
