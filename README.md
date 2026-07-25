# CEMM v1 — Exact Semantic Runtime with Learned Language Projection

CEMM is an experimental semantic-cognition runtime. Its governing thesis is:

> Language is evidence about meaning. It is not the meaning substrate itself.

The exact plane stores semantic atoms, five compositional operator shapes, applications, bindings, evidence, claims, state timelines, causal rules, and proof links. Neural components propose and rank interpretations, workspace contents, and language realizations; they do not create a second ontology or override exact semantic validation.

## v1 status

The final v1 runtime implements the complete documented Stage 0–22 cognitive cycle:

- transport-grounded participant deixis;
- pure observation and evidence encoding;
- referent grounding before semantic composition;
- recursive type/facet state-space projection;
- open compositional candidate generation and exact settling;
- first-class claim, query, description, directive, correction, retraction, and acknowledgment acts;
- proof-bearing query variables, restrictions, projections, and bindings;
- scoped epistemic placement and claim admission;
- generic causal transition previews from promoted graph rules;
- reviewed pack-local constant pointers for structural relations, generation-pinned to exact authority;
- generic concept predication compiled as subtype/definition structure rather than concept-as-instance typing;
- recursive capability assessment over inherited dependency graphs;
- goal arbitration and explicitly registered operation adapters;
- target-aware Response CSIR, learned surface realization, and semantic-pointer verification;
- revision-pinned Stage-13 commits and Stage-21 common-ground commits;
- sparse indexed retrieval instead of whole-store runtime closure;
- structural training episodes with family-level holdouts and mandatory no-transition cases;
- explicit reviewed lexical acquisition with no parser writes or default semantic kind.

The bundled language packs and knowledge data remain small proof artifacts. Architectural completeness does **not** mean broad vocabulary, broad world knowledge, or production-scale model quality.

## Five fixed operator shapes

The semantic ABI keeps five foundational application forms:

```text
op:designation(target, label_type, surface, language, script, ...)
op:type(instance, class)
op:relation(subject, relation, object)
op:state(subject, dimension, value)
op:event(event, type, actor, object, time, ...)
```

New domains are represented by new atoms, graph relations, learned designations, state dimensions, causal rules, and operational profiles. They do not require new Python classes, SQL tables, intent handlers, or phrase templates.

## State and recursive inheritance

A referent does not receive a hard-coded schema. Its active operational profile is projected as:

```text
referent
  → direct types and facets
  → recursive subtype/facet closure
  → entitled dimensions, capabilities, resources, mechanisms
  → recursive dependency graph
  → current evidence-backed state timeline
```

State values preserve their native domains: categorical, ordered, continuous, vector/manifold, relational, set-valued, process-valued, or probabilistic. Defaults remain expectations and never become active facts without evidence.

Concepts and instances remain distinct. A concept such as `concept:cat` may license dimensions for cat instances; the concept itself is not assigned an animal's temperature, hunger, or location.

## Self without the word “ready”

The digital self is a grounded participant with a recursively inherited digital-agent profile. Runtime providers expose evidence for resources such as:

```text
resource:runtime_process
resource:semantic_runtime
resource:language_realizer
resource:output_channel
```

Capabilities are derived through ordinary `rel:depends_on` chains. For example:

```text
cap:respond
  depends_on cap:interpret
  depends_on cap:realize
  depends_on resource:output_channel
```

A language pack may realize a strong capability assessment as “ready,” “available,” or another expression. The semantic runtime does not require any of those words to know its operational condition.

An unresolved word or clause creates a scoped interpretation assessment and learning frontier. It does not mutate the self into a global `confused` or `insufficient` state.

## Claims, queries, and directives

Related surface forms may share referents and content while producing different discourse structures:

```text
claim      → source-attributed proposition and admission candidate
query      → information gap, restrictions, variables, projection, obligation
directive  → desired event/state, capability and permission requirements
```

Punctuation is evidence available to the language model; it never deterministically rewrites one settled discourse force into another. Runtime mode also never changes force.

A query performs no queried-world transition. A directive does not assert that its desired state is already true. Only an adapter connected to the requested semantic event/action by reviewed `rel:handled_by_adapter` authority, registered by the embedding runtime, and permitted by the active session scope can create an external effect.

When a language construction uses a grounded state value without naming its dimension, the compiled candidate must explicitly bind a `DIM_OF_A*` source. The exact store resolves that declared dependency through reviewed `rel:value_of_dimension` authority. Missing or ambiguous mappings remain unresolved; the compiler never silently guesses a dimension.

## Causal transition model

Transitions are represented by promoted `rule_kind="causal"` graph rules:

```text
antecedent:
  event-role clauses
  state/domain preconditions

consequent:
  role-addressed state deltas
  optional secondary events
```

Stage 12 produces a `TransitionPreview` with bindings, preconditions, deltas, uncertainty, and proof. A predicted delta is not committed as an observation. Operation or sensor evidence is compared against the preview to create prediction-error artifacts.

No event-specific transition class or positional argument shortcut is used.

## Runtime modes

CEMM has one cognitive pipeline and three explicit effect policies:

| Mode | Meaning |
|---|---|
| `normal` | Interpret normally; admit/persist only policy-authorized claims/frontiers; commit verified common ground. |
| `read_only` | Run the same cognition with zero durable writes. |
| `reviewed_teach` | Explicit reviewed rule-induction workflow; ordinary conversation never enters it implicitly. |

The former Ask/Learn/Teach mode split is removed. Normal chat itself determines whether the utterance is a claim, query, directive, or another discourse act.

## Stage 0–22 core loop

```text
0  orient and pin authority/world/discourse revisions
1  capture EvidenceEnvelope
2  build modality/form evidence lattice
3  ground referents through ParticipantFrame and discourse context
4  project recursively entitled state spaces
5  compile semantic candidates
6  run recurrent candidate dynamics
7  stabilize exact or partial meaning
8  build claim/query/directive structures
9  place claims epistemically
10 execute query bindings and proof paths
11 classify prediction error and learning frontiers
12 simulate role-addressed transitions
13 commit admitted knowledge/frontiers with CAS receipt
14 evaluate capability, impact, and operational condition
15 arbitrate goals and discourse obligations
16 plan, authorize, and execute registered adapters
17 assimilate operation evidence with bounded re-entry
18 build target-aware Response CSIR
19 realize through the pinned language pack
20 verify surface provenance and semantic authorization
21 commit verified common ground
22 finalize trace, budgets, receipts, and cache statistics
```

Stages 0–12 are transient. Stage 13 is the first ordinary world-write boundary. External effects belong to Stage 16, operation evidence to Stage 17, and discourse/common-ground writes to Stage 21.

## Performance contract

Normal turns must not:

- compute a whole-store snapshot hash;
- materialize every fact in the database;
- execute unrestricted full closure;
- retrain models because world facts changed;
- scan all discourse rows to decay salience;
- persist transient workspace tensors or candidate sets.

The final runtime uses:

- indexed fact lookup by operator, role, filler, stance, and active validity;
- backward relevant-rule expansion with hard fact/rule/depth budgets;
- generation-keyed entitlement caches;
- lazy salience decay;
- runtime-owned bounded model caches;
- incremental generation receipts and world/discourse/effect revisions;
- compare-and-swap checks at durable boundaries.

`Store.snapshot_hash()` remains available only for explicit audits and maintenance.

## Storage compatibility

Final v1 intentionally rejects populated pre-final databases. Rebuild a database from canonical authority JSON and separately retained world evidence. Silent schema migration would preserve exactly the obsolete self-state, response-policy, and compatibility artifacts this version removes.

## Running

```bash
python -m cemm.cli init \
  --db cemm.sqlite \
  --pack cemm/language_packs/en.json \
  --data cemm/data/base.json \
  --data cemm/data/family_knowledge.json

python -m cemm.cli chat --db cemm.sqlite --pack cemm/language_packs/en.json

python -m cemm.cli process "How are you?" \
  --mode read_only \
  --db cemm.sqlite \
  --pack cemm/language_packs/en.json

python -m cemm.cli acquire-reviewed \
  --text "Friction is resistance." \
  --mentions '[{"surface":"Friction","kind":"concept"},{"surface":"resistance","kind":"concept"}]' \
  --db cemm.sqlite \
  --pack cemm/language_packs/en.json
```

Web demo:

```bash
python -m cemm.web_demo --db cemm.sqlite
```

## Main modules

| Module | Responsibility |
|---|---|
| `context.py` | Session, ParticipantFrame, revision-pinned cycle state, transient workspace. |
| `evidence.py` | Evidence envelopes and modality/form lattice. |
| `interpreter.py` | Split observe/ground and compose/settle language path. |
| `codec.py` | Open compositional neural proposal over force, operators, roles, variables, and projections. |
| `compiler.py` | Exact operator/role/domain validation; no compatibility query or dimension shims. |
| `state.py` | Recursive entitlement and native-domain state projection. |
| `retrieval.py` | Sparse indexed fact and relevant-rule retrieval. |
| `inference.py` | Bounded exact closure, query bindings, and proof construction. |
| `epistemics.py` | Claim occurrence and admission policy. |
| `transitions.py` | Causal rules, transition previews, state deltas, prediction error. |
| `capability.py` | Runtime evidence and recursive dependency assessment. |
| `goals.py` | Goal arbitration, authorization, adapter registry, operation results. |
| `response.py` | Response CSIR and deterministic pointerization. |
| `realizer.py` | Learned fact/response projection and provenance verification. |
| `stages.py` | Stage 0–22 ordering and side-effect ownership. |
| `curriculum.py` | Structural episode and holdout validation. |
| `acquisition.py` | Explicit reviewed identity/designation publication; never parser-driven acquisition. |
| `store.py` | Exact authority/world store, indexes, revisions, receipts, common ground, effect journal. |

## Acceptance source of truth

The executable final-v1 tests and `V1_ACCEPTANCE.md` are the acceptance contract. The focused final suite contains 33 architecture tests. Frozen MVP references and pre-final tests are historical evidence, not runtime authority.

See also:

- `ARCHITECTURE.md`
- `runtime-core-loop.md`
- `v1-fixes.md`
- `V1_ACCEPTANCE.md`
