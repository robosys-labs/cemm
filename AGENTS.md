# CEMM 3.3 Semantic Spine — Governing Implementation Contract

Status: active governing implementation guide  
Scope: repository-wide  
Baseline audited: `37056ff6e1f5db4b2faa0fc22892d580520b088f`  
Audience: coding agents, reviewers, maintainers, test authors

This file is the highest-priority local implementation contract for CEMM. When an older plan, generated artifact, archived document, test, bootstrap script, or nested instruction conflicts with this file, follow this file.

## 1. Canonical source order

Use active guidance in this order:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. current non-archived documents under `newarch/`
4. executable acceptance and architecture tests
5. implementation code and traces

Archived files, generated plans, runtime databases, logs, exports, patch artifacts, and `__pycache__` are not architectural authority.

A document may describe intended architecture without proving that the implementation is wired or authoritative. Status claims must distinguish:

- **specified** — described by an active contract;
- **implemented** — code exists;
- **wired** — the canonical runtime invokes it;
- **authoritative** — no competing component makes the same decision;
- **verified** — end-to-end substrate tests prove the behavior.

Never use “complete” unless all five states hold.

## 2. Core identity

CEMM is a meaning-first semantic runtime and graph-patch learner. It is not a phrase router, prompt wrapper, text-template database, intent-only classifier, or English-only chatbot.

The canonical dependency chain is:

```text
Signal
→ multilingual surface evidence
→ meaning groups and competing interpretations
→ grounded UOL atoms and edges
→ proposition, entity, predicate, state, time, source, permission, and modality resolution
→ operational meaning frames
→ query/write/reaction/state/action/safety/learning contracts
→ contract execution
→ evidence-bound response formation
→ output/session update
→ validated graph-patch learning
```

Fix the earliest incorrect substrate that has enough authority to explain a failure. Never repair an upstream semantic corruption with a downstream output blacklist or phrase special case.

## 3. Canonical UOL substrate

CEMM has exactly these 16 atom kinds:

```text
entity process state relation quality quantity time place
intent need modality evidence source permission action self
```

CEMM has exactly these 16 edge types:

```text
has_role modifies refers_to asks_about teaches evaluates
causes enables prevents before after same_as is_a part_of
used_for has_property
```

Do not create domain atom kinds such as `PresidentAtom`, `EmailAtom`, or `WeatherAtom`. Domain meanings are concepts, typed relations, state dimensions, schemas, and validated records.

### 3.1 Surface evidence is not operational authority

Surface text and language aliases may propose candidates only. They may not directly:

- select final operational meaning;
- authorize a memory write;
- become a durable fact;
- bypass entity grounding;
- bypass predicate activation;
- bypass source, permission, freshness, contradiction, or trust checks;
- generate final answer text without an evidence-bound semantic slot.

Language data maps surface forms to candidates. Canonical meaning lives in schemas and validated graph memory.

## 4. Proposition law

Every semantic relation must explicitly carry proposition mode:

```text
asserted
queried
commanded
hypothetical
reported
negated
```

Compatibility code may infer the mode once at the perception boundary, but downstream code must consume the explicit mode.

### 4.1 Asserted proposition

An asserted relation may produce a typed domain edge only when all required semantic roles are grounded.

```text
relation(has_property)
  subject → entity:user
  object  → entity:Chibueze
  dimension → identity.name
  proposition_mode → asserted
```

It may become a graph-patch candidate only after source, permission, evidence, modality, and required roles are present.

### 4.2 Queried proposition

A queried proposition is an open proposition, not a fact.

```text
relation(has_property)
  subject → entity:user
  object  → OPEN
  dimension → identity.email
  proposition_mode → queried
```

A queried relation:

- must not emit a typed asserted domain edge;
- must not create a durable relation or concept patch merely because its target is unknown;
- must represent missing fillers as open ports, never role-placeholder entities;
- must be connected to the question intent through `asks_about`;
- may constrain retrieval but may not itself satisfy the query;
- must never be answerable as a current-turn fact.

### 4.3 Open-role invariant

`open_roles` names unfilled semantic ports. An open role has no filler atom. The role name is metadata, not an entity, concept, surface value, or answer candidate.

## 5. Role-binding law

`has_role` always points from an owning semantic atom to a real filler atom:

```text
action/relation/state/intent → entity/self/place/time/value
```

The role name belongs on the edge:

```text
has_role(owner, filler, role="subject")
```

Forbidden:

```text
entity → relation("role:topic")
relation → entity("topic")
concept:topic as a missing object
```

Role labels and placeholders:

- cannot receive durable concept resolution;
- cannot be subjects or objects of typed domain relations;
- cannot satisfy required ports;
- cannot become patch candidates;
- cannot enter `RelationFrame`, `AnswerBinding`, `selected_slots`, or realization as public content.

## 6. Entity grounding and lexical evidence

Internal IDs and public lexical surfaces are different fields.

Every candidate set must preserve:

```text
target_span_ref
target_surface
candidate semantic refs
selected semantic ref
```

Never substitute an atom ID, candidate ID, span ID, concept ID, record ID, frame ID, or gap ID for missing public surface evidence.

Opaque identifiers such as `uol_*`, `omf_*`, `oc_*`, `hyp_*`, `gap_*`, and internal `concept:*` keys must never reach public realization unless the user explicitly asks for an internal diagnostic trace.

Unknown lexical content is still a valid retrieval key. For a concept question, attempt deterministic concept grounding and durable retrieval before clarification. “Unknown to the current lexicon” does not mean “unqueryable.”

## 7. Predicate and interpretation authority

Candidate interpretations must remain separate until the interpretation resolver selects a branch. Rejected branches must not produce operational frames, typed relation edges, state transmutations, contracts, or patches.

Predicate activation must consume grounded predicate phrases, relation/action candidates, construction matches, schema predicates, durable predicates, and the active learning overlay. It must not synthesize authority only from a broad frame-type label.

Exactly one component is authoritative for each decision:

| Decision | Authority |
|---|---|
| relation candidate extraction | `RelationExtractor` |
| UOL graph materialization | `MeaningGraphBuilder` |
| interpretation branch selection | `InterpretationResolver` |
| operational frame compilation | `OperationalMeaningCompiler` |
| contract compilation | `OperationalContractCompiler` and its specialized builders |
| semantic query execution | `SemanticQueryEngine` |
| durable write validation | `PatchValidator` |
| durable commit | `PatchCommitter` / `DurableSemanticStore` |
| response formation | `ResponseFormationEngine` |
| surface wording | language renderer only |

Compatibility helpers may adapt types but may not independently remake the decision.

## 8. Relation-frame law

Argument bindings do not make a semantic relation structural. `has_role` edges are structural; the relation they bind may be answerable.

Structural by default:

```text
has_role refers_to modifies teaches asks_about
schema-generated state-delta support edges
```

Potentially answerable when complete and asserted:

```text
is_a same_as part_of used_for has_property
causes enables prevents before after evaluates
learned predicate-schema relations
```

Projection and answerability come from predicate/projection schemas plus proposition mode. A queried or open relation is never answerable.

Do not compile duplicate authoritative frames for both a relation atom and its typed edge. Prefer the relation atom with its role bindings; compile a typed edge only when no authoritative relation atom backs it.

## 9. Query law

A query contract must include:

```text
target scope
subject constraints
predicate/relation constraint
dimension and qualifiers
projection policy
result cardinality and limit
ambiguity policy
evidence policy
freshness policy
```

Supported cardinalities:

```text
one optional_one many ranked_many
```

Current-turn query scaffolding must never outrank durable facts. Query execution must:

1. validate target grounding;
2. retrieve durable candidate frames under the complete contract;
3. optionally include asserted current-turn evidence;
4. exclude queried/open/placeholder/internal frames;
5. filter relation, subject, dimension, scope, and qualifiers;
6. deduplicate by semantic identity and object;
7. apply cardinality and ranking;
8. produce evidence-bound slot fills or an explicit abstention.

There must be one active query executor. Do not maintain a second runtime-local implementation alongside `SemanticQueryEngine`.

## 10. Durable relation identity and cardinality

A durable relation’s slot identity is:

```text
subject identity
+ relation key
+ normalized dimension
+ relation scope
+ normalized qualifiers
```

The object value is not part of the slot identity. It distinguishes values occupying that slot.

Exact duplicate identity plus object reinforces support. Different objects under a `single` slot supersede the previous active value. `many`/`set` slots retain distinct active values. `unknown` cardinality must not destructively replace prior data without confirmation.

Contradiction, deduplication, supersession, query, and indexing must use the same normalized identity implementation.

Dimension-blind checks such as `subject + has_property` are forbidden.

Profile aliases must map to canonical dimensions in the language/schema layer. Multi-token aliases use longest-match resolution, for example:

```text
"full name" → identity.full_name
"name"      → identity.name
```

## 11. Graph-patch and write law

All durable learning flows through:

```text
working graph
→ structural observation
→ graph patch
→ contract authorization
→ validation
→ commit
→ journal/provenance
```

A query turn must produce no durable relation or query-target concept patch.

`WriteOutcome` is operation-specific. A turn may claim that memory was stored only when every operation required by the selected `WriteContract` committed. An auxiliary concept observation committing while the requested relation failed is not write success.

Required and auxiliary operations must be distinguishable. Record actual created/updated record IDs, not commit IDs mislabeled as record IDs.

## 12. Learning episode law

Learning episodes are cross-turn state. They must survive session restoration.

Turn ordering:

```text
restore pending episodes and obligations
→ perceive current signal normally
→ match current meaning against pending expected-answer schemas
→ assimilate the actual current percept/signal
→ update hypothesis and episode state
→ resume blocked obligations when grounded
→ detect new gaps
→ create at most one new learning question when required
→ persist episodes, obligations, evidence, and resolved fields
```

Never assimilate an empty answer string into a question created on the same turn.

A learning obligation becomes pending only if the assistant actually emitted the corresponding question act. Pending obligations have explicit ownership by episode and context, expected-answer schema, provenance, and lifecycle.

## 13. Response and realization law

`ResponseFormationEngine` is the sole response authority. Planning is language-neutral. Only language renderers choose wording.

`SlotBinder` consumes evidence-bound slots only. It must:

- preserve slot features and provenance;
- reject internal or placeholder values structurally;
- retain multiple fills when the query cardinality permits;
- never invent a value from raw input or an internal ID.

Realization units must support scalar and multi-value semantic content. List coordination belongs in language renderers.

Every generated content lexeme should be traceable to a semantic value and language-pack lexical choice. Generated content should be able to round-trip into a compatible semantic candidate when the user asks about it.

HTML escaping occurs once at the final output boundary. Do not store escaped strings as semantic values and do not double-escape between slot binding and rendering.

## 14. Runtime ordering

Preserve this order:

```text
Observe
→ Contextualize
→ Interpret
→ Ground
→ consume pending learning answers
→ Retrieve
→ Infer
→ Decide
→ validate/commit authorized writes
→ Realize
→ Update
→ Learn/persist
```

Safety authorization is a gate, not a ranker preference. Write outcomes exist before response formation. Output-state updates consume semantic response metadata rather than parsing generated text.

## 15. Required diagnostics

For every failed behavior, capture:

1. meaning groups;
2. candidate interpretations and selected/rejected branches;
3. relation proposition mode and open roles;
4. UOL atoms/edges for entity, predicate, state, source, permission, time, and modality;
5. concept resolutions and port bindings;
6. operational frames and arbitration;
7. query/write/reaction/state/safety/learning contracts;
8. retrieved relation identities and rejection reasons;
9. patch operations, validation, and operation-level commit results;
10. final slot provenance and realization units.

Every answer slot must expose:

```text
public value
← slot fill
← relation frame
← durable/current record
← query match
← operational frame
← UOL atoms/edges
← source evidence span
```

## 16. Testing contract

Source-inspection tests are insufficient. Every hot-path fix needs substrate assertions and end-to-end tests.

Mandatory regression families:

- profile assertion, update, and exact-dimension recall;
- multi-token property aliases;
- concept teaching followed by concept query;
- query turns generating no durable patches;
- no role-placeholder or opaque-ID leakage;
- dimension-aware contradiction and supersession;
- truthful operation-specific write confirmation;
- multi-result capability realization;
- prior-turn learning-question assimilation and persistence;
- multilingual canonical-graph equivalence;
- generated lexical round-trip;
- concurrent web-demo context isolation.

Tests must assert graph and contract structure, not only final strings.

## 17. Forbidden implementation patterns

Do not:

- add transcript phrases to operational compilers or query executors;
- blacklist `"topic"` only in the renderer;
- regex-parse final English output to recover semantics;
- make unknown atom IDs public clarification text;
- create role-marker concepts;
- treat every `has_property` value for an entity as mutually contradictory;
- confirm a write because any unrelated patch committed;
- mark semantic relations structural merely because they have arguments;
- let a query-shaped relation become a current-turn fact;
- keep duplicate contract/query authorities;
- call shadow code “implemented and complete” when it does not control behavior.

## 18. Completion gate

A change is complete only when:

- the earliest wrong substrate is corrected;
- no later-stage phrase workaround is required;
- one authority owns every changed decision;
- graph invariants pass;
- query/write behavior is contract-driven;
- memory identity/cardinality is consistent across validation and storage;
- response values are evidence-bound and public-safe;
- cross-turn state persists;
- end-to-end regression tests pass;
- architecture status documentation is updated honestly.
