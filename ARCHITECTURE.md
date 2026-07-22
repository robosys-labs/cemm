# CEMM v3.5.1 Grounded Semantic Brain Architecture

**Status:** canonical target architecture  
**Purpose:** define one grounded semantic system that can understand, learn, reason, remember, act, and communicate without reducing cognition to phrase routing or opaque token prediction.

---

## 0. Architectural objective

CEMM is a learning-first semantic computational architecture.

A minimally working CEMM must be able to:

```text
observe
→ interpret compositional meaning
→ ground participants/referents
→ maintain scoped world and discourse state
→ answer queries
→ preserve uncertainty
→ learn from frontiers/prediction error
→ reuse learned knowledge after restart
→ construct semantic responses
→ realize language without inventing meaning
```

The first product goal is a robust English conversational kernel. Multimodal, multilingual, causal, affective, and planning breadth expands only after this vertical semantic spine works end-to-end.

---

## 1. One canonical cognitive state

At cycle time `t`, cognition operates over:

```text
CognitiveState_t
  authority_snapshot
  read_generation
  working_csir
  activation_field
  grounded_belief_state
  epistemic_graph
  causal_model
  discourse_common_ground
  goal_impact_field
  frontier_graph
  proof_lineage_graph
  cycle_workspace
```

The working state may be incomplete, ambiguous, contradictory, or budget-limited.

Durable effects require explicit commit/effect boundaries.

---

## 2. Exact semantic substrate: CSIR

CSIR is a finite typed attributed hypergraph built from a small stable kernel:

```text
TERM
VARIABLE
APPLICATION
BINDING
QUALIFIER
SCOPE_EMBEDDING
COORDINATION
PROOF_LINK
```

Everything higher-order must either:

1. compile to these constructors with exact closure proof; or
2. justify a Kernel Semantic ABI migration.

Examples represented through CSIR include:

```text
identity
classification
property
relation
state
event/process/action
claim
query
capability
goal
impact
response act
```

These are semantic graph patterns plus optional operational profiles—not new irreducible kernel atoms.

---

## 3. Semantic operations

The kernel provides bounded operations:

```text
INSTANTIATE
BIND
UNIFY
COMPOSE
QUALIFY
EMBED
PROJECT
MATCH
COMPARE
NORMALIZE
PROPAGATE
INTEGRATE
SIMULATE
REWRITE
COMMIT
INVALIDATE
CONSOLIDATE
```

Operations are semantic-machine mechanics, not named domain concepts.

---

## 4. Exact semantic identity

Every executable semantic structure pins:

```text
kernel semantic ABI
compiler ABI
normalizer/equivalence ABI
semantic definition closure
operational profiles
dynamics parameter artifact
causal mechanism artifact
use authorization
language/multimodal projection authority
policy/adapters where required
```

Forbidden executable resolution:

```text
latest
max revision
revision range
minimum compatible revision
floating parent
mutable model path
semantic-key lookup without exact activation pin
```

Historical decisions retain their original exact authority closure.

---

## 5. Recurrent semantic dynamics

Each candidate CSIR fragment, binding, referent, scope, or interpretation may carry dynamic state:

```text
activation/support
uncertainty
learned continuous features
exact semantic/type/context features
```

Typed message families include:

```text
lexical/form evidence
construction compatibility
port/role compatibility
type entitlement
identity/coreference
scope
time/aspect
context/world
state plausibility
causal expectation
discourse continuity
multimodal alignment
inhibition
```

The system recurrently settles toward:

```text
stable semantic-equivalence class
multiple close alternatives
partial stable graph
contradiction set
budget-limited incompleteness
```

Hard semantic constraints clamp impossible candidates.

Activation does not override exact semantics.

---

## 6. Language architecture

Language is a projection/evidence system over shared semantics.

Pipeline:

```text
surface
→ reversible normalization
→ script/language evidence
→ morphology/form lattice
→ lexeme/sense candidates
→ semantic contributions
→ construction constraints/programs
→ grounded CSIR candidates
```

Language packages may encode:

- forms and variants;
- lexemes and senses;
- morphology;
- agreement/tense/aspect/case features;
- constructions;
- semantic contribution specs;
- realization rules.

They may not encode world truth or become hidden kernel ontology.

The kernel must not branch on English words or construction names.

---

## 7. Grounded referents and identity

`Referent` is the identity-bearing filler family.

Identity may be:

```text
resolved
candidate
merged
split
unknown
scope-local
```

Identity evidence may come from:

- participant frame;
- names/aliases;
- discourse mention chains;
- multimodal tracks;
- spatial/temporal continuity;
- prior output;
- explicit identifiers.

High activation is not sufficient evidence for identity commitment.

Participant roles such as speaker/addressee are grounded by the cycle/session frame, not hard-coded pronoun meanings.

---

## 8. Entitled state spaces

A referent exposes only dimensions licensed by active type/facet closure.

Dimension domain types include:

```text
categorical
ordered discrete
continuous
vector/manifold
relational
set-valued
process-valued
probabilistic
```

Foundational families include:

```text
identity/type
existence
geospatial
temporal
physical
structural
biological/homeostatic
cognitive
affective
social/normative
resource
capability
epistemic
operational/runtime
```

A default is not an active state.

A dimension being meaningful for one type does not make it universal.

---

## 9. Claims, belief, context, and memory

Text is evidence that an utterance/claim occurred. It is not automatic world truth.

Keep separate:

```text
proposition
claim occurrence
source
evidence
epistemic admission
world belief
state assignment
```

Contexts include:

```text
actual
reported
believed
hypothetical
planned
desired
fictional
quoted
counterfactual
```

Memory has distinct layers:

### 9.1 Episodic/interaction evidence
What was observed, said, emitted, or done.

### 9.2 Scoped participant/world belief
Admitted identity/property/relation/state facts with source, time, context, permission and contradiction lineage.

### 9.3 Semantic authority
Reusable definitions, language mappings, causal structures and promoted parameters.

A conversation fact such as `my name is Chibueze` is not automatically global semantic authority.

---

## 10. Queries and information gaps

Keep separate:

```text
information gap
semantic variable
restriction graph
answer projection
discourse act
response obligation
```

Interrogative forms contribute restrictions/projections. Matrix/discourse structure determines whether the utterance is an actual request for an answer.

Query execution returns semantic bindings plus proof paths.

Internal role labels must never be surfaced as answer content.

---

## 11. Events, actions, transitions, and roles

An eventuality binds semantic roles to participants.

Effects are role-addressed:

```text
affected.temperature += delta
moved_entity.position := destination
container.contains -= content
recipient.possession += item
```

Never:

```text
subject gets effect A
object gets effect B
```

A transition mechanism contains:

```text
role requirements
state/domain requirements
preconditions
defeaters
direct deltas
secondary-event candidates
uncertainty
proof/warrant requirements
```

Preview is not durable mutation.

---

## 12. Structural causality

Keep separate:

```text
correlation
default expectation
logical implication
temporal sequence
causal mechanism
intervention result
counterfactual result
```

Causal propagation is:

```text
typed
context-isolated
bounded
cycle-detected
proof-bearing
```

Cross-dimensional effects require explicit mechanisms.

Physical temperature never simply becomes mood; it may causally affect homeostasis/comfort/affect for entitled living entities.

---

## 13. Capability and dependency

Keep separate:

```text
affordance
function
capability
permission
competence
intention
```

Live capability derives from grounded dependencies such as:

```text
required state
resources
structural integrity
adapter availability
permission
competence
context
```

Event names do not directly toggle capability.

---

## 14. Learning architecture

Prediction error and unresolved cognition create typed frontiers.

Learning tiers:

### Tier A — episodic/participant knowledge
May be admitted under scoped epistemic/privacy policy.

### Tier B — language/lexicalization/construction
Maps new forms or structures to existing semantics.

### Tier C — semantic/state/causal structure
Creates reusable world meaning and requires stronger competence/review.

### Tier D — continuous parameters
Creates immutable versioned parameter artifacts.

General learning loop:

```text
frontier
→ evidence/counterexamples
→ candidate induction
→ exact dependencies
→ competence
→ scoped requested uses
→ promotion
→ immutable authority generation
→ next-cycle activation
→ restart
→ replay/invalidation
```

Frequency is not truth. Co-activation is not equivalence. Repetition is not causal proof.

---

## 15. Discourse and common ground

CEMM maintains:

```text
participant frame
mention chains
prior semantic outputs
open questions
open clarification targets
topic/focus state
commitments
corrections/retractions
common-ground proposals
```

Follow-ups such as:

```text
Why?
For what?
What did you mean?
What happened to it?
```

must resolve through discourse semantics and compatible referents/events/propositions, not transcript phrase handlers.

---

## 16. Response architecture

A response is a semantic action intended to affect discourse/common ground.

Response CSIR families include:

```text
answer query
report state/relation/event
provide causal explanation
qualify uncertainty/source
request clarification
acknowledge a specific target
correct prior output
warn about predicted risk
report capability
ask a learning question
propose authorized operation
remain silent for explicit reason
```

Response selection considers:

```text
truth/proof
query coverage
information gain
relevance
impact/social appropriateness
privacy/safety
risk
cost
realisability
```

Surface language is generated only after Response CSIR exists.

---

## 17. Realization and semantic preservation

Pipeline:

```text
Response CSIR
→ discourse/clause plan
→ role/reference realization
→ morphology/prosody/layout
→ surface candidate
→ proof-carrying semantic preservation
→ selective independent round trip when required
→ emission authorization
```

The realizer may choose wording but may not add:

- unsupported facts;
- participants;
- relationships;
- emotion;
- causality;
- certainty;
- completed operations.

---

## 18. Runtime authority model

Separate:

```text
RuntimeAttestation
AuthorityGeneration
AuthoritySnapshot
WorldRevision
DiscourseRevision
RuntimeObservationRevision
AuditRevision
EffectJournalRevision
EffectAuthorizationBoundary
```

Release attestation is verified at startup/reload, not rehashed per request.

A semantic pass sees one immutable authority generation.

Mutable world/discourse state may refresh only at explicit consistency/re-entry boundaries.

---

## 19. Core invariants

1. One canonical semantic substrate: CSIR.
2. No higher-order executable meaning without exact closure.
3. No continuous state overrides hard semantic constraints.
4. Grammar never becomes universal ontology.
5. Effects target semantic roles and entitled dimensions.
6. Claims do not automatically become actual-world state.
7. Simulation is not commit.
8. Causality requires mechanism/warrant.
9. Capability derives from dependencies.
10. Partial cognition remains explicit.
11. Learning promotion is typed, scoped, versioned and replayable.
12. Response meaning precedes wording.
13. Durable/effect results are reconstructible from authority, evidence and pre-state.
14. Performance and boundedness are correctness properties.
15. Unknown optional enrichment must not block grounded core meaning.

# Phase 15–16 mathematical completion addendum — typed state and causal mechanics

This section is normative for v3.5.1 state/causal implementation.

## Typed state value algebra

A state dimension declares an exact `StateDomainContract` separate from the semantic identity
of the dimension. Runtime state is a typed occurrence value, never a new ontology class:

`StateValue = Categorical | Ordered | Continuous | Vector/Manifold | Relational | Set | Process | Distribution`.

For each active `(referent, dimension, context, time)` there is exactly one domain contract.
Every transform is type checked against that contract. Units, coordinate frames, manifolds,
relation types, element types, process types and categorical values are exact-pinned authority.
An ordered `increase/decrease` is movement in reviewed order, not a guessed target. A manifold
cannot silently use Euclidean addition; nonlinear transforms require exact operator authority.
Probabilistic state is a distribution over typed `StateValue` support occurrences. Every support
value is validated by the same exact underlying domain algebra; opaque outcome labels are not state.

## Structural causal mechanism contract

A causal mechanism is an exact, competence-gated authority record with:
- trigger kind and exact trigger definition or source state dimensions;
- exact semantic participant-role pins and optional exact type requirements;
- preconditions and defeaters over typed state variables;
- typed role-addressed state transforms and/or secondary-event templates;
- optional mutually exclusive stochastic branches whose mass sums to one;
- exact parameter, aggregation and stochastic-independence authority where applicable;
- explicit per-use `TRANSITION` authority distinct from lifecycle and competence.

Surface grammar never supplies causal participant roles. Active/passive or language-specific
surface differences must converge to the same semantic role bindings before mechanism use.
Competing mechanisms may not sequentially overwrite one state variable. They require an exact
aggregation contract and evaluator. Joint stochastic multiplication requires exact independence
authority; otherwise the result stays unresolved.

## Interventions and counterfactuals

Observation conditions on a variable. Intervention `do(X=x)` replaces the structural equation
for X in an isolated context and cuts incoming causal edges to X. Counterfactual evaluation is:

`abduce U from factual evidence -> clone isolated context -> restore U -> apply do(...) -> predict`.

If abduction is underidentified, CEMM must preserve an explicit frontier; it may not fabricate a
counterfactual. No hypothetical/interventional/counterfactual/planning state may commit into the
actual world merely because it was simulated. Likewise, non-actual impact may inform explicit
evaluation but may not silently become actual goal pressure or obligations.

## One causal proof substrate

Prediction, explanation, causal question answering, impact propagation, planning and recursive
causal learning consume the same `CausalProof` DAG. A proof step separately records exact
mechanism authority, source state variables, source event occurrences, target state variable or
secondary event, branch probability, confidence, warrants and parent causal steps. A deterministic
actual consequence that crosses the world-state commit boundary must persist this exact proof DAG
with exact mechanism and pre/post value identity; an opaque proof string is insufficient.

Causal learning may propose a mechanism only from explicit mechanism/intervention evidence and
exact dependency closure. Co-occurrence alone is not causal authority. Candidate score does not
bypass competence/review/promotion or immutable authority-generation restart.
