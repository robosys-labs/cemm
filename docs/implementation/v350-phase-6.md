# CEMM v3.5 Phase 6 — Foundational seed package

**Base:** completed Phase 0–5 source substrate
**Status:** implemented and phase-verified; not public-runtime-authoritative
**Authority:** reviewed data compiled through the Phase-4 commit validator

## 1. Purpose and boundary

Phase 6 supplies the smallest structural semantic world that can support
learning, composition, claims, state applicability, capability reasoning, and
future language realization without turning the Python source into an ontology.

It does not supply a broad catalogue of world facts. It does not seed convenient
domain concepts merely because later demonstrations need them. It does not
activate transition, causal, impact, lexical, or NLG authority ahead of their
phases.

## 2. Delivery subphases

### 6A — Structural referent types

The package seeds 26 broad type anchors rooted in `type:referent`, including
concrete/physical/digital/hybrid structure, living and organism structure,
agent families, information-bearing objects, propositions, claims, events,
states, contexts, quantities, units, time, collections, places, and schema
topics.

Multiple inheritance is explicit. In particular:

```text
type:software_agent -> type:agent + type:digital_entity
type:hybrid_entity  -> type:physical_entity + type:digital_entity
type:biological_agent -> type:organism + type:natural_agent
```

The root type licenses all stable serialization kinds, while descendants narrow
those shapes. The graph is validated for exact parent contracts, closure, and
cycles.

### 6B — Universal facets and entitlements

Twenty universal knowledge facets are seeded, covering identity, existence,
semantic typing, time, localization, composition, properties, state, relations,
roles, event participation, action affordance, capability, function, resources,
epistemics, social/normative knowledge, affect, significance, and
provenance/access.

Fifty-two entitlement contracts establish inheritance, conditional applicability,
domain extension, overriding, and prohibition. They include explicit category
boundaries: propositions and claim-information referents cannot acquire
biological affect or executable capability merely because a value is unknown.

### 6C — Native semantic axes

Seventy-three first-class operator schemas preserve polarity, occurrence/world
status, modality, normativity, change direction, valence, importance,
four-state truth support, epistemic basis, persistence, and reversibility as
distinct axes. Positive/negative proposition polarity, supported/opposed truth
status, observed/reported epistemic basis, decrease/loss, and beneficial/harmful
valence remain independent dimensions.

### 6D — Properties, state, measures, relations, and roles

The seed includes:

- 7 core property schemas;
- 17 state dimensions;
- 93 state values with bidirectional dimension validation;
- 5 measure dimensions and 9 canonical units;
- 15 core relations, including verified inverse pairs;
- 12 context/time-qualified role schemas.

Holder applicability and value domains are type-driven. The boot database has no
active live-state assignments.

### 6E — Action, event, claim, and discourse foundations

Ten action schemas and twenty-four event schemas establish reusable shape for
communication, observation, learning, external versus self-initiated movement,
and a generic event hierarchy covering change, relation change, state change,
capability change, communicative activity, epistemic change, creation,
destruction, movement, claims, and corrections. Sixteen concrete core events
inherit through eight abstract event families.

These event schemas intentionally have no transition, result, causal, or impact
contracts and deny transition use. The UOL validator now also rejects any delta
whose exact event-schema revision does not independently authorize transition.
Phase 11 remains the sole owner of state mutation authority.

Claim semantics explicitly require independent epistemic admission. Discourse
acknowledgement requires content; no targetless acknowledgement or literal
sentence response is seeded.

### 6F — Function, capability, and self truthfulness

The self referent is resolved and typed as a software agent. Its stable functions
are represented as ordinary function applications. Live capabilities are
separate records supported by runtime evidence.

Available capabilities are limited to components already implemented and tested:

```text
read the semantic store
compile the reviewed foundation
project referent knowledge
```

Each available action independently authorizes planning and execution and pins
required competence hooks for both uses. Language realization is represented as
an intended function/affordance but its capability is explicitly unavailable and
its execute use remains denied.

### 6G — Evidence, identity, and defaults

Identity facets and runtime evidence are normalized records. The self name is a
quoted symbol with language tag `und`, not a language-pack lexical rule.

The proposition truth default is a revisioned, defeasible rule yielding
`default_expected(undetermined)`. It creates no `StateAssignment` and no
`KnowledgeRecord`.

### 6H — Audit, competence, and deterministic release gate

`foundation_contract.json` is the machine-readable seed contract. It lists
required schema groups, exact type parents, required entitlements, self
capabilities, competence cases, forbidden domain keys, exact record counts, and
the canonical source-record fingerprint. The manifest additionally pins the
contract and competence files by SHA-256.

`FoundationPackageAuditor` checks:

- manifest authority, phase metadata, contract reference, and SHA-256 pins;
- complete required records, exact record counts, and full source fingerprint;
- exact type graph and root storage shapes;
- provenance and foundation ownership;
- absence of language/sentence data and forbidden domain seeds;
- state-dimension/value closure and exact native-axis domain separation;
- no premature event-transition authority;
- target-bearing discourse and template-free response policies;
- truthful self capabilities, evidence, and import-resolvable runtime components;
- no boot active state or admitted world knowledge.

`FoundationCompetenceRunner` executes declarative cases for type closure,
applicability, prohibition, defaults, function/capability separation, claim
non-admission, claim/event inheritance, movement distinctions, semantic-axis
orthogonality, universal existence/time entitlement, multiple inheritance, and
live runtime contracts.

### Cross-facet ownership and applicability rules

The final seed audit establishes these category boundaries:

- existence and validity-time dimensions belong to universal existence and
  temporal facets rather than the generic state facet;
- truth support (`supported | opposed | both | undetermined`) is exclusive and
  distinct from epistemic basis (`observed | reported | inferred |
  default_expected | assumed`), which may coexist;
- capability status describes `CapabilityInstance` records and is not licensed
  as an ordinary holder-state dimension;
- importance and valence provide stakeholder-relative assessment vocabularies
  and cannot be materialized through ordinary state entitlements;
- foundational affect is limited to neutral arousal structure; named emotions
  and evaluative valence remain learned/separate;
- externally caused movement and intentional self-initiated movement are
  separate actions with compatible controlling-port types; an event occurrence
  is neither capability.

## 3. Supporting implementation hardening

Phase-6 scale exposed repeated whole-registry and whole-record decoding during a
single pinned store revision. The store now caches decoded record sets and schema
registries by:

```text
record kind + all-revisions mode
store revision
boot fingerprint
overlay fingerprint
```

The cache retains only the current pinned snapshot and therefore invalidates
naturally on every overlay commit or boot fingerprint change. This is a read
optimization, never a second authority.

The referent knowledge projector now derives action affordances from applicable
`facet:action_affordance` entitlement value domains in addition to observed
action applications. Blocked, contradicted, and inapplicable entitlements do not
leak affordances.

## 4. Verification contract

The Phase-6 gate requires:

```text
foundation audit clean
source package cross-record validation clean
byte-identical deterministic SQLite builds
immutable boot open succeeds
all required competence cases execute and pass
architecture lint clean
all Phase 0–6 focused tests pass
complete repository test suite passes
```

The frozen Phase-6 package contains 414 compiled authoritative records and 24
required foundation competence cases. Its exact kind counts, complete canonical
source fingerprint, contract hash, and competence hash are review gates. Any
future broad structural seed must intentionally revise those contracts.

## 5. Explicitly deferred work

Phase 6 does not:

- seed domain types or facts;
- provide lexical senses or language forms;
- authorize event state transitions;
- derive capability changes from state deltas;
- establish causal or impact rules;
- admit claims into actual-world knowledge;
- implement multilingual realization;
- replace the public v3.4.7 runtime.

Those boundaries prevent later behavior from being smuggled into the foundation
as hidden assumptions.
