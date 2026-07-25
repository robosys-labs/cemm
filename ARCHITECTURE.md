# CEMM v1 Active Architecture


> **Implementation status:** the exact substrate and Stage 0–22 ownership skeleton are implemented foundations. Multi-resolution form processing, parallel referent grounding, active state-conditioned settling, span-level partial CSIR, and general designation/property queries remain active work. A stage trace is not proof that these functions are complete.

## 1. Normative thesis

CEMM represents meaning in one exact semantic substrate. Language, sensors, operation results, and other modalities provide evidence from which candidate semantic structures are proposed. Neural computation may encode, rank, settle, attend, and realize those structures. It may not become a second source of semantic authority.

The architecture therefore separates:

1. **evidence** — what was observed and where it came from;
2. **candidate cognition** — transient alternatives and recurrent dynamics;
3. **exact semantic structures** — validated operators, roles, variables, qualifiers, and proof links;
4. **epistemic placement** — whether a claim is merely attributed, admitted, disputed, or hypothetical;
5. **world belief and state timelines** — admitted evidence-backed claims;
6. **operations** — authorized effects and their returned evidence;
7. **language projection** — verified realization of Response CSIR.

## 2. Kernel boundary

### 2.1 Fixed operator ABI

CEMM v1 keeps five irreducible application shapes:

```text
DESIGNATION target ↔ surface evidence
TYPE        instance → class
RELATION    subject → relation → object
STATE       subject → dimension → value
EVENT       event → type and participant roles
```

These shapes are fixed. Domain expansion occurs through atoms, role fillers, graph relations, state dimensions, causal rules, and learned designation/realization artifacts.

### 2.2 What is not a kernel primitive

The following remain ordinary semantic data or runtime artifacts, not new operator classes:

- cat, server, person, battery, emotion, company, vehicle;
- a domain-specific state schema;
- a phrase intent such as `HOW_ARE_YOU`;
- an event-specific transition executor;
- a capability-specific Python subclass;
- a response string template embedded in runtime code.

### 2.3 Core semantic objects

The exact store contains:

- atoms and their semantic kinds;
- operator-role contracts;
- applications and bindings;
- observations and EvidenceEnvelope lineage;
- claim occurrences and epistemic placements;
- active/closed world claims;
- rules and rule indexes;
- proof links;
- reference forms and designations;
- revisions, commit receipts, common ground, and effect journal records.

Transient structures such as candidate tensors, query bindings, transition previews, goals, and Response CSIR live in the cycle workspace unless their owning stage explicitly commits a compact artifact.

## 3. Participant grounding and deixis

Participant identity is supplied by transport/session setup:

```text
ParticipantFrame
  self_ref
  speaker_ref
  addressee_ref
  audience_refs
  conversation_ref
  source/channel
```

A language form contributes a requirement such as first person, second person, speaker, addressee, or possessive. Stage 3 resolves that requirement against the active frame.

Input and output frames are perspective-dependent:

```text
input:  speaker=user, addressee=self
output: speaker=self, addressee=user
```

No lexical entry permanently means `participant:user` or `participant:system`.

## 4. Evidence and interpretation

### 4.1 Evidence first

Every turn begins as an `EvidenceEnvelope`. A linguistic envelope records surface text, language, source participant, channel, observation time, confidence, permission scope, and lineage.

An observation is not automatically a proposition. Stage 2 builds an evidence lattice containing:

- form evidence;
- grounded anchor evidence;
- unknown-form evidence;
- modality/context evidence;
- source and temporal evidence.

### 4.2 Split interpretation API

The runtime uses two interpreter boundaries:

```text
observe(text, ParticipantFrame)
  → EvidenceLattice + grounded anchor candidates

compose(EvidenceLattice, ParticipantFrame, StateSpaceProjection)
  → settled/partial semantic packet + InterpretationAssessment
```

This ensures Stage 4 state projection occurs before final semantic stabilization. The old all-in-one parser is diagnostic only and requires an explicit ParticipantFrame.

### 4.3 Partial meaning

Unknown evidence does not erase grounded meaning. A multi-clause input may produce:

```text
stable semantic content
+ unresolved evidence
+ LearningFrontier
+ exact blockers
```

Frontiers are scoped to the affected form, variable, clause, or target. They are not global self states.

## 5. State-space architecture

### 5.1 Universal state assignment algebra

The universal structure is not a universal list of dimensions. It is:

```text
subject
+ dimension
+ value/distribution
+ valid time
+ context
+ stance
+ evidence/provenance
+ epistemic status
```

A transition extends it with:

```text
pre-state
+ trigger/event
+ mechanism/warrant
+ post-state delta
+ uncertainty
+ proof
```

### 5.2 Recursive entitlement

For referent `r`:

```text
Types(r) = direct TYPE claims
Closure(r) = recursive subtype/facet closure
Profile(r) = union of entitlements over Closure(r)
```

Entitlements include:

- state dimensions;
- capabilities;
- resources;
- mechanisms;
- recursive dependency edges.

No dimension becomes meaningful for every referent merely because it exists in authority.

### 5.3 State-domain families

The generic state engine supports:

- categorical;
- ordered discrete;
- continuous;
- vector/manifold;
- relational;
- set-valued;
- process-valued;
- probabilistic.

Native domains are preserved. Continuous values are not converted into arbitrary categories, and categorical identity is not converted into a percentage.

### 5.4 State projection outcomes

For each entitled dimension, projection may be:

```text
missing
resolved
uncertain
stale
conflicting
```

Defaults remain prototype expectations. They never appear in `values` without admitted evidence.

## 6. Identity, type, relation, state, and concept level

Identity continuity, TYPE membership, RELATION structure, and mutable STATE are distinct.

A class-level generic such as “a cat is an animal” is represented as a subtype relation or a quantified/definition rule—not as though the concept atom `cat` were an individual animal instance. Compiled language artifacts may expose reviewed pack-local constant pointers such as `CONST0`, but each pointer resolves through an immutable `constant_sources` map and is accepted only when its target is authority-scoped and visible to the cycle’s pinned generation. The model therefore predicts a small reviewed structural pointer, not an arbitrary ontology identifier.

Meta-discourse about a concept is also distinct from world state of its instances.

## 7. Query architecture

A query is not one ordinary application with a flag. `QueryStructure` contains:

```text
query_ref
restriction graph
semantic variable declarations
answer projection
qualifiers/context/time restrictions
```

Execution returns `QueryResult`:

```text
status
bindings
coverage
support/opposition counts
unresolved variables
proof paths
blocking frontiers
```

Boolean queries are the zero-projection special case. Projection queries may bind dimensions, values, entities, classes, relations, event roles, or other exact fillers.

Queries do not mutate the queried world.

## 8. Discourse force and epistemics

Stage 8 constructs explicit acts:

- claim;
- query;
- description request;
- directive;
- correction;
- retraction;
- acknowledgment.

Language cues, punctuation, construction evidence, and discourse context may influence candidate ranking. No runtime mode or punctuation branch may overwrite stabilized force.

For claim-like acts:

```text
observation
→ claim occurrence attributed to speaker
→ EpistemicPlacement
→ optional admitted world claim
```

Admission classes include attributed-only, session participant fact, scoped user assertion, corroboration required, high-risk no-auto-admission, and hypothetical-only.

Corrections/retractions require an explicit target claim occurrence. A participant may retract only their own attributed occurrence. A correction may admit replacement content under the ordinary epistemic policy.

## 9. Causal mechanisms and transitions

### 9.1 Mechanism representation

A mechanism is a promoted causal rule:

```text
IF
  event clauses with named roles
  state/domain preconditions
THEN
  state deltas addressed through bound roles
  optional secondary events
```

The mechanism is graph data. The runtime does not contain code for “charging,” “moving,” “heating,” or other particular events.

### 9.2 Stage-12 preview

A `TransitionPreview` contains:

- mechanism ref;
- trigger refs;
- role bindings;
- precondition/proof refs;
- before values;
- proposed after values;
- secondary events;
- confidence and unresolved constraints.

Previewed deltas are predictions, not observations, and are never committed merely because the mechanism fired in simulation.

### 9.3 Prediction error

Observed state after an event or operation is compared with the preview:

- prediction confirmed;
- prediction mismatch;
- prediction unobserved;
- explicit no-transition cases in training.

This creates learning evidence without rewriting authority automatically.

## 10. Capability and operational self

Capabilities, resources, dimensions, and dependency edges are all ordinary semantic refs. The evaluator recursively computes support from dependency leaves while preserving native state values.

The final authority seeds a digital-agent profile:

```text
cap:respond
  → cap:interpret
      → runtime process
      → semantic runtime
  → cap:realize
      → language realizer
  → output channel
```

Runtime providers emit cycle-local evidence scores for these resources. The self can answer operational-condition queries even when no language pack contains a word equivalent to “ready.”

A lexical item never controls whether the capability exists.

## 11. Goals, actions, and effects

Stage 15 ranks semantic obligations and goals such as:

- answer the actual query;
- clarify the exact blocker;
- report a capability assessment;
- handle a directive;
- acknowledge an admitted claim;
- fulfill a greeting obligation.

Stage 16 resolves candidate adapters through ordinary reviewed authority: `event/action type → rel:handled_by_adapter → adapter`. `AdapterRegistry` then requires that candidate to be registered by the embedding application and permitted by the active session scope. There is no surface-text routing, dummy adapter, or default “successful” execution.

Every operation receives an idempotency key and an effect-journal record. Returned output becomes operation evidence at Stage 17. Semantic observations inside adapter output are validated and compared with predictions, but are not automatically admitted into world belief.

## 12. Response CSIR and realization

Stage 18 constructs target-aware `ResponseCSIR` from:

- QueryResult and proofs;
- InterpretationAssessment;
- scoped epistemics;
- FrontierGraph;
- capability and directive decisions;
- operation results;
- discourse obligations.

The response action is semantic, for example:

```text
answer_bindings
confirm
deny
report_conflict
report_target_uncertainty
request_targeted_clarification
report_capability
acknowledge_claim
decline_directive
report_operation_result
greet
```

Stage 19 uses reviewed language-pack examples to project this structure into surface form. Atom placeholders are resolved through designation evidence; unknown-form evidence and numeric values use typed evidence/number placeholders.

Stage 20 verifies:

- the transform was authorized by the pinned pack;
- every placeholder has provenance;
- grammar tokens are pack-authorized;
- internal refs do not leak;
- the surface is non-empty.

No unverified surface is committed to common ground.

## 13. Reviewed lexical acquisition

Unknown-form detection belongs to pure cognition and never writes. When a reviewer or training system determines that a form denotes a genuinely new semantic identity, `acquire_reviewed` publishes an explicit identity kind and designation through the same five-operator substrate. It never defaults an unknown form to `concept`, never runs from the parser, and cannot create ABI/state-space kinds such as operators, roles, or state dimensions.

The designation is indexed incrementally, receives a Stage-13 commit receipt, and becomes usable only after the runtime explicitly reloads the newer authority generation. Any meaning asserted by the source document is then interpreted by the ordinary normal or reviewed-teaching cycle; acquisition has no private semantic parser.

## 14. Persistence and revisions

The store tracks independent revisions:

```text
world_revision
observation_revision
discourse_revision
effect_revision
```

Cycle orientation pins them. Stage 13 uses compare-and-swap against the pinned world revision. A generation receives an incremental payload hash and commit receipt; it does not scan and hash the whole database.

Stage ownership:

| Stages | Durable effect |
|---|---|
| 0–12 | none |
| 13 | admitted claims, claim occurrences, epistemic placements, frontiers |
| 16 | authorized effect-journal update |
| 17 | operation observation receipt |
| 21 | verified common ground |
| 22 | final compact bookkeeping only |

`read_only` runs all stages but suppresses every durable boundary.

## 15. Retrieval and inference performance

Runtime reasoning begins from restrictions, grounded refs, active state dimensions, and causal triggers. Indexed lookup retrieves only matching active facts. Relevant rules are expanded backward from consequent operators/constants under fixed fact/rule/depth budgets.

The runtime does not call full `base_facts()` or unrestricted closure. Full fact materialization and snapshot hashes are explicit audit tools only.

Other performance invariants:

- entitlement cache keys include authority generation and type/facet closure;
- model caches are bounded and runtime-owned;
- salience decay is computed lazily for touched/retrieved entities;
- hard workspace requirements are bounded separately from optional slots;
- operation re-entry is capped;
- language models are pinned to pack hash and do not retrain on world writes.

## 16. Training architecture

A structural training episode contains:

```text
PRE
  participant frame
  context/time
  relevant pre-state projection
  discourse/common-ground state

INPUT
  one or more evidence envelopes

TARGET
  stable/partial CSIR
  discourse act
  query projection/result shape
  epistemic placement
  transition preview or NO_TRANSITION
  world/cognitive/discourse deltas
  Response CSIR
```

Curricula must include family-level holdouts rather than random paraphrase splits. Required contrast families include deixis reversal, claim/query/directive minimal pairs, explicit dimension/value variables, generic/subtype meaning, partial meaning, transitions versus no-transition, and response targeting.

System output is supervised from Response CSIR and its original participant frame. It is not reparsed as independent world truth.

## 17. Schema and compatibility policy

Final v1 intentionally rejects populated pre-final databases. The exact schema version is part of runtime attestation. Rebuild from canonical JSON and retained evidence.

Removed compatibility artifacts include:

- SessionSelf and self `ready/processing/confused` dimensions;
- `USER`/`SYSTEM` lexical source aliases;
- bare-application query normalization;
- value→dimension completion;
- runtime language-pack sidecars;
- Ask/Learn/Teach semantic mode switching;
- old outcome→response policy graph;
- generated patch/report artifacts as repository source.

## 18. Honest limitations

The architecture supports the complete v1 cycle, but bundled proof data remains limited:

- language coverage depends on reviewed pack examples;
- world knowledge depends on imported/learned evidence;
- adapters must be registered by an embedding application;
- causal competence depends on promoted causal rules;
- neural components are small proof models, not production-scale encoders;
- distributed multi-writer deployment would require a transactional backend with equivalent revision/CAS semantics.

These are coverage and deployment limits, not hidden alternate semantic paths.

## Explicit implied dimensions

A lexical value may explicitly select `DIM_OF_A*`; exact authority resolves `value → rel:value_of_dimension → dimension`. This is a declared semantic source, not compiler inference.

## 18. Pre-core form processing and multi-resolution entry contract

Surface processing is outside semantic authority. It may use language-specific normalization, tokenization, morphology and span algorithms only to create reversible evidence alternatives.

```text
raw text/signal
→ NormalizationCandidate[]
→ FormSpanCandidate[]
→ SentenceDocumentCandidate[]
→ ResolvedFormLattice
→ Stage 1 semantic evidence
```

Every candidate preserves source offsets, transformations, language/script evidence, score and lineage. The front-end cannot create semantic atoms, bind a final referent, choose discourse force, infer a state dimension, or mutate world state.

Stage 3 consumes candidate designations and reference requirements as a `GroundingCandidateSet`. Stage 5 constructs CSIR candidates across surviving grounding hypotheses. Exact role/kind/domain checks prune candidates; Stage 6–7 settles them with state/type/context factors. No top-1 label result is semantic authority before convergence.

## 19. Authority bundle/linking contract

Repository authority is one graph split across reviewable files. Before import, a linker validates the complete set of atoms, role contracts, control symbols, durable facts, rule constants, reference forms, state specifications and language-pack constants. The database write occurs atomically after validation.

Generic relations and rules are foundational authority. A domain file may declare domain concepts, entities, dimensions, values, events and domain mechanisms, but it may not privately define a generic kernel relation required by other domains.

Concept hierarchy uses `rel:subtype_of`; `op:type` is reserved for instance membership. Reified state specifications bind exactly one `rel:state_dimension` and one `rel:state_value`.

## 20. Designation and property-query contract

Identity is opaque. Names, aliases, titles, identifiers and localized labels are designation properties:

```text
op:designation(target, label_type, surface, language, script, context, provenance)
```

`label:name_full` and `label:name_alias` are subtypes of `label:name`. A name query is a normal QueryCSIR over designation restrictions and subtype closure, projecting literal surface evidence and proof. It is not a special English intent.

The same mechanism must support title, alias, identifier and localized-label queries. Response CSIR must preserve literal-binding provenance and authorize realization without exposing internal IDs.

## 21. Property paths and chained dimensions

Properties are not all state dimensions. The runtime must preserve the distinction between designation properties, relations, intrinsic dimensions, component/resource state, derived capabilities and process/event-valued state. Chained access is represented as a bounded graph restriction/path over existing applications and dependencies, not dotted strings or per-type schemas.

State projection may recursively follow type/facet entitlement and capability/resource dependencies. Future property-path projection must preserve each edge, context, time and proof so a derived answer remains explainable.

