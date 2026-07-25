# CEMM v1 — Current Runtime Weaknesses and Required Refactors

**Status:** active diagnostic contract  
**Purpose:** record what the current runtime does not yet accomplish, where the earliest defect lies, and what kind of repair is permitted.

This document prevents a trace-complete skeleton or a passing phrase test from being mistaken for complete semantic cognition.

## 1. Executive diagnosis

The current runtime has a useful exact substrate, state projection, QueryCSIR, epistemic placement, transition, capability and Response CSIR skeleton. Its largest remaining ceiling occurs **before and during semantic stabilization**:

```text
surface evidence is matched and collapsed too early
→ one label/reference winner enters composition
→ N-best semantic candidates vary mainly above an already-fixed grounding
→ state projection is mostly diagnostic rather than an active factor
→ property/designation questions lack complete generic query/realization support
```

The correct next direction is not more phrase examples. It is a bounded multi-resolution form and semantic hypothesis pipeline.

## 2. P0 — authority bundle integrity

### Defect

Authority files are imported sequentially. Cross-file references are not linked before the first durable write. Generic state-spec relations and inference rules were placed in `family_knowledge.json`; two relations were referenced but absent as atoms.

### Consequences

- database initialization depends on file order;
- a partial database can exist after a later file fails;
- domain/demo files silently become required kernel foundations;
- migrations can update `base.json` while leaving dependent files stale;
- compiled language packs can reference authority that no longer exists.

### Required repair

Use one repository-wide authority linker and one atomic bundle import. Move generic relations/rules to base authority. Validate data, source corpora and compiled packs as one release graph.

## 3. P0 — concept hierarchy and state specification drift

### Defect

Some data encodes `concept:female → concept:human` through `op:type(instance=concept:female, class=concept:human)`. This confuses a concept with an instance. Family inference also relies on reified state specifications without foundational declarations for their binding relations.

### Required representation

```text
op:type(entity, concept)
op:relation(concept_child, rel:subtype_of, concept_parent)

state_spec
  rel:state_dimension → dimension
  rel:state_value     → value
```

State specs remain useful because the same value may occur in more than one dimension; a global value→dimension shortcut cannot replace them. `rel:value_of_dimension` may exist only as an exact derived/index relation.

## 4. P0 — trainer/runtime authority can diverge

### Defect

Migrations repaired compiled packs but did not repair the reviewed source corpora. Recompiling could therefore restore concept-as-instance examples or dimensionless state examples. Pointer collection order also diverged between training and realization in one revision.

### Required repair

The release gate must validate and, where deterministic, migrate:

- canonical semantic JSON;
- reviewed training corpora;
- compiled packs;
- pointer serialization ordering;
- pack hashes and reviewed constants.

Generated artifacts must be reproducible from reviewed source authority.

## 5. P1 — no true pre-core form-resolution lattice

### Current behavior

The language path performs normalization, span matching, reference lookup, unknown detection and sentence splitting inside the interpreter. It scans stored labels with regular expressions and usually resolves a surface to one referent before semantic candidate competition.

### Why this is wrong

Text normalization and semantic cognition have different authority. Surface processing may use language-specific algorithms, but it must not decide world identity or meaning. Running one regex per stored label is also not scalable.

### Required architecture

```text
PRE-CORE FORM PROCESSING
raw text
→ reversible Unicode/orthographic alternatives
→ token/subword/morphology alternatives
→ span and construction alternatives
→ sentence/document alternatives
→ ResolvedFormLattice

SEMANTIC CORE
ResolvedFormLattice
→ designation/reference candidate sets
→ referent/coreference candidate sets
→ CSIR candidate graphs
→ state/type/context factors
→ recurrent settling
```

The pre-core output preserves offsets, transformations, language/script evidence, scores and provenance. It creates no semantic atoms and commits nothing.

## 6. P1 — referent grounding collapses before settling

### Current behavior

Designation and reference resolution selects one winner or raises ambiguity. Semantic N-best candidates are therefore generated over a mostly fixed grounding.

### Required repair

Introduce explicit artifacts:

```text
FormCandidate
SpanCandidate
DesignationCandidate
ReferenceRequirement
ReferentCandidate
GroundingHypothesis
GroundingCandidateSet
IdentityCoreferenceTrace
```

Candidate axes must include form, span, sense/designation, participant/coreference and CSIR structure. Exact kind/role constraints prune combinations. Recurrent settling selects only when convergence and margin gates pass.

## 7. P1 — Stage 4 state projection is not an active semantic factor

### Current behavior

State-space projections are produced and attached to traces, but competing semantic candidates are not materially scored or clamped by entitlement, dimension domain, current state, applicable mechanism or capability dependency.

### Required repair

Candidate scoring must include exact factors for:

- referent type/facet compatibility;
- dimension entitlement;
- state-value domain compatibility;
- temporal/context validity;
- applicable mechanism roles;
- capability/resource dependencies;
- contradiction with pinned world evidence.

Exact violations are clamped. Plausibility evidence contributes calibrated dynamic energy and never becomes authority.

## 8. P1 — partial meaning is clause-level, not span/graph-level

### Current behavior

A clause containing unknown material can be skipped while adjacent clauses survive. The runtime does not yet preserve the grounded subgraph inside that same clause with an open lexical/construction variable.

### Required repair

Unknown spans should become typed open nodes/edges in a partial CSIR candidate. Grounded participants, relations, time, state dimensions and surrounding structure remain available where licensed.

## 9. P1 — embedded and mixed discourse acts are compressed away

### Current behavior

Document composition rejects or flattens mixed forces. Reported questions, quoted claims, directives embedded in conditions, correction plus replacement, and multi-clause obligations are not represented generally.

### Required repair

Use scope/embedding artifacts over the same CSIR substrate. Do not create one intent class per construction.

## 10. P1 — `name` and general designation-property queries are incomplete

### Correct foundation

A name is a label/designation property of a referent:

```text
op:designation(
  target=referent,
  label_type=label:name | subtype,
  surface=literal,
  language/context/provenance=...
)
```

`label:name_full` and `label:name_alias` inherit from `label:name`.

### Missing runtime competence

The runtime needs a generic query structure capable of:

```text
restriction: designation(target=X, label_type=?nameSubtype, surface=?surface, ...)
constraint:  ?nameSubtype subtype_of label:name
projection:  ?surface and optionally type/language/context/proof
```

It also needs Response CSIR and realization support for literal bindings. The fix must generalize to aliases, titles, identifiers and localized labels. It must not inspect the English token `name` in runtime code.

## 11. P1 — property and chained-dimension representation needs expansion

### Current foundation

The state projector handles direct/inherited dimensions, capabilities, resources and mechanism applicability.

### Missing competence

The architecture needs an explicit treatment of compositional property paths and dependent/chained dimensions, for example:

```text
entity → component/resource/relation → entitled dimension → current value
entity capability → dependency capability/resource/dimension → assessment
```

This should use graph paths, role-addressed applications, qualifiers and bounded recursive projection—not per-type schemas or dotted string paths. The design must distinguish:

- intrinsic state dimension;
- relational property;
- designation/label property;
- component/resource state;
- derived capability assessment;
- event/process-valued state;
- measurement/evidence source.

## 12. P2 — realization remains a small authorized classifier

Response semantics and pointer verification are sound boundaries, but the bundled realizer can authorize only learned surface plans. Open compositional generation, morphology and generative referring expressions remain limited. A missing realization must open a realization frontier rather than emit an internal ID or invented wording.

## 13. P2 — recurrent dynamics are still a proof-sized approximation

Current settling uses bounded N-best inhibition but does not yet represent a full typed factor graph with certified convergence, cross-clause message passing, calibrated posterior semantics or recurrent re-entry after material operation evidence.

## 14. P2 — concurrency and migrations

The SQLite runtime remains essentially single-process/single-writer. Schema versioning is rebuild-oriented. Production work needs explicit migrations, locking/actor isolation and snapshot/replay policy; compatibility must not weaken semantic contracts.

## 15. Required implementation order

1. Foundation bundle linker and atomic import.
2. Move generic authority out of domain files; repair hierarchy/state specs.
3. Source-corpus/pack reproducibility gate.
4. Pre-core reversible form-resolution subsystem.
5. Parallel designation/reference/referent grounding lattice.
6. State/type/context factors in semantic settling.
7. Span-level partial CSIR and embedded acts.
8. Generic designation/property QueryCSIR including literal bindings.
9. Chained property/dimension projection.
10. Broader realization and production scaling.

Skipping directly to phrase behavior, more examples, or response formatting is architectural regression.
