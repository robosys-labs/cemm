# CEMM Consolidated Architecture

Version: 4.1  
Status: implementation reference  
Audience: medium to senior programmers implementing CEMM without architectural drift  
Scope: semantic compression, construction grammar, operational ports, dynamic concept grounding, and unsupervised learning

## 1. Purpose

This document consolidates the architecture across:

```text
semantic_compression_and_unsupervised_learning.md
construction_grammar_for_cemm.md
operational_ports_and_dynamic_slot_resolution.md
atom_grounding_and_bootstrapping.md
dynamic_affordances_and_effects.md
concept_lattice_runtime_resolution.md
```

It is the implementation-facing contract.

If another document shows an example that appears to treat a concept, slot, or effect as static, this document wins.

## 2. Core Thesis

CEMM does not learn by storing utterance graphs forever.

CEMM learns by compiling temporary perception graphs into compressed, executable meaning structure:

```text
utterance/transcript/source
-> meaning groups
-> working UOL graph
-> graph patch candidates
-> construction, concept, predicate, port, and affordance consolidation
-> durable concept lattice
```

The durable memory is not a database of all past graphs.

The durable memory is:

```text
concept atoms
aliases
operational ports
predicate schemas
causal affordances
construction operators
source/evidence policies
small high-value exemplars
```

## 3. Non-Negotiable Invariants

These are hard architecture rules.

### 3.1 Kernel Atom Kinds Are Fixed

The kernel only knows these primitive atom kinds:

```text
entity
process
state
relation
quality
quantity
time
place
intent
need
modality
evidence
source
permission
action
self
```

These are representation categories, not domain concepts.

### 3.2 Domain Concepts Are Not Kernel Primitives

Do not hardcode these as native primitives:

```text
person
country
organization
office_role
leader
president
cold
authority
government
weather
```

They are concept atoms in the concept lattice.

They may be seeded, learned, revised, consolidated, contested, or forgotten.

### 3.3 Working Graphs Are Temporary

`UOLGraph` is working memory.

It is not long-term memory.

A working graph may produce:

```text
graph patches
operator traces
memory updates
training examples
exemplars
```

but the graph itself should usually expire.

### 3.4 Ports Are Not Static Slots

Ports are atom-owned operational openings.

They are resolved dynamically using:

```text
working graph
concept lattice
inheritance
construction evidence
source/evidence policy
temporal policy
semantic fingerprints
contradiction checks
```

Never implement:

```python
if atom.key == "president":
    fill_president_slots(...)
```

Implement:

```python
ports = concept_lattice.get_ports(atom)
bindings = port_resolver.resolve(graph, atom, ports, context)
```

### 3.5 Possible Effects Are Not Ports

`possible_effect` is not a port.

Effects are predicted by causal affordance operators over bound ports.

Correct:

```text
cold + domain=temperature + holder=user_environment + intensity=high
-> predicts discomfort_risk
```

Incorrect:

```text
cold.possible_effect = discomfort
```

### 3.6 Constructions Are Operators, Not Regex Rules

A construction is a learned form-meaning operator.

It maps surface/structure patterns to graph patch candidates.

It is not:

```text
a fixed intent label
a permanent sentence template
a regex that directly mutates memory
```

### 3.7 Memory Writes Must Be Graph Patches

No component writes raw interpreted claims directly to durable memory.

All durable learning flows through:

```text
GraphPatch -> validation/scoring -> consolidation -> concept lattice update
```

### 3.8 Source, Time, Evidence, And Permission Are Always Preserved

Every promoted structure must know:

```text
where it came from
when it was asserted or observed
whether it is stable or current
what permission scope allows it
how confident the system is
what contradicts it
```

## 4. Core Runtime Objects

### 4.1 UOLGraph

Temporary working graph for the current interpretation.

Required properties:

```typescript
interface UOLGraph {
  id: string
  signal_id: string
  context_id: string
  raw_text: string
  language: string
  atoms: Map<string, UOLAtom>
  edges: UOLEdge[]
  group_atom_ids: Map<string, string[]>
  trace: Record<string, unknown>
}
```

Use `UOLGraph` for:

```text
current turn interpretation
transcript segment interpretation
operator input/output
graph patch extraction
training export
```

Do not use `UOLGraph` as permanent memory.

### 4.2 UOLAtom

Runtime graph node.

```typescript
interface UOLAtom {
  id: string
  kind: AtomKind
  key: string
  surface?: string
  group_id?: string
  span_id?: string
  value?: unknown
  features: Record<string, unknown>
  confidence: number
  source: string
  evidence: EvidenceRef[]
}
```

`kind` must be one of the fixed kernel atom kinds.

`key` may be a dynamic concept key.

Example:

```text
kind = entity
key = president
```

means:

```text
this is an entity-kind runtime atom whose concept key is president
```

It does not mean `president` is a kernel type.

### 4.3 ConceptAtom

Durable concept-lattice node.

```typescript
interface ConceptAtom {
  concept_id: string
  key: string
  atom_kind: AtomKind
  state:
    | "unknown_surface"
    | "candidate_atom"
    | "typed_candidate"
    | "operational_atom"
    | "consolidated_atom"
    | "contested_atom"
    | "stale_atom"

  aliases: string[]
  parents: string[]
  ports: OperationalPort[]
  acceptable_predicates: PredicateSignature[]
  causal_affordances: CausalAffordance[]
  temporal_policy: TemporalPolicy
  evidence_policy: EvidencePolicy
  permission_policy: PermissionPolicy
  source_support: SourceSupport[]
  counterexamples: Counterexample[]
  exemplars: ExemplarRef[]
  fingerprint?: SemanticFingerprint
  confidence: number
  stability: number
}
```

Concept atoms are the main durable learning target.

### 4.4 OperationalPort

Atom-owned role interface.

```typescript
interface OperationalPort {
  port_id: string
  owner_concept_id: string
  key: string
  required: boolean

  accepted_atom_kinds: AtomKind[]
  accepted_parent_concepts: string[]
  required_edges: EdgePattern[]
  forbidden_edges: EdgePattern[]

  temporal_policy?: TemporalPolicy
  evidence_policy?: EvidencePolicy
  resolver_policy: ResolverPolicy

  support: SourceSupport[]
  confidence: number
}
```

Examples:

```text
leader.holder
leader.domain
president.time_scope
cold.holder
cold.intensity
ask.topic
```

### 4.5 PredicateSchema

Reusable process/relation/action pattern.

```typescript
interface PredicateSchema {
  predicate_id: string
  key: string
  owner_concept_ids: string[]
  required_ports: string[]
  optional_ports: string[]
  accepted_subject_concepts: string[]
  accepted_object_concepts: string[]
  default_edges: EdgeType[]
  preconditions: GraphPattern[]
  effects: GraphPatchTemplate[]
  evidence_policy: EvidencePolicy
  source_support: SourceSupport[]
  counterexamples: Counterexample[]
  confidence: number
}
```

Example:

```text
leads(actor, domain)
```

should be represented as a predicate schema, not hardcoded into `leader`.

`leader` may list it as acceptable.

### 4.6 CausalAffordance

Contextual effect predictor.

```typescript
interface CausalAffordance {
  affordance_id: string
  trigger_pattern: GraphPattern
  required_bindings: PortBindingPattern[]
  predicted_effect: GraphPatchTemplate
  effect_type:
    | "state_change"
    | "need_activation"
    | "action_enablement"
    | "action_prevention"
    | "evaluation_shift"
  source_support: SourceSupport[]
  counterexamples: GraphPattern[]
  confidence: number
}
```

Affordances are predictions.

They are not facts until later evidence confirms them.

### 4.7 ConstructionAtom

Learned form-meaning operator.

```typescript
interface ConstructionAtom {
  construction_id: string
  form_signature: FormSignature
  graph_signature: GraphPattern
  pragmatic_signature?: PragmaticPattern
  port_constraints: PortConstraint[]
  operator_effects: GraphPatchTemplate[]
  support_count: number
  counterexamples: Counterexample[]
  confidence: number
}
```

Examples:

```text
X is a Y
X means Y
what can you do
I am STATE
can you ACTION
if X then Y
```

### 4.8 GraphPatch

Only legal durable memory mutation input.

```typescript
interface GraphPatch {
  patch_id: string
  source_graph_id: string
  source: SourceRef
  permission: PermissionRef
  evidence: EvidenceRef[]
  operations: PatchOperation[]
  target:
    | "concept_lattice"
    | "construction_lattice"
    | "predicate_schema"
    | "causal_affordance"
    | "episodic_trace"
    | "source_policy"
    | "discard"
  confidence: number
  reason: string
}
```

## 5. Runtime Pipeline

The online runtime must follow this order:

```text
Signal
-> Normalize
-> Segment
-> ConstructionMatch
-> Atomize
-> BuildWorkingGraph
-> ResolveConcepts
-> ResolvePorts
-> Inherit
-> PredictAffordances
-> Compare/Verify
-> PlanAct
-> ExtractGraphPatches
-> ConsolidateAsync
```

### 5.1 Normalize

Input:

```text
raw text, source metadata, context id
```

Output:

```text
normalized surface tokens
language signal
punctuation/discourse features
unknown surfaces
```

### 5.2 Segment

Split into:

```text
turns
clauses
meaning groups
predicate phrases
discourse units
```

Do not assume one utterance equals one meaning.

### 5.3 ConstructionMatch

Match known construction atoms against surface and early graph features.

Output:

```text
candidate graph patch templates
expected ports
pragmatic hints
confidence
```

Construction matches are hints, not truth.

### 5.4 Atomize

Create candidate UOL atoms from:

```text
surface spans
known aliases
language adapter resources
construction hints
concept lattice lookup
source/tool lookup if allowed
```

Unknown terms produce candidate atoms, not errors.

### 5.5 BuildWorkingGraph

Create a `UOLGraph`.

The graph should include:

```text
primitive atoms
surface evidence
source atom
permission atom
time/evidence atoms
candidate relation/process/state atoms
group links
```

### 5.6 ResolveConcepts

For each atom key:

```text
exact alias lookup
construction context lookup
parent concept search
fingerprint nearest neighbor
source-backed lookup if allowed
candidate atom creation if unresolved
```

Do not block runtime just because a concept is unknown.

Use the best operational state available.

### 5.7 ResolvePorts

For each atom with available ports:

```text
collect candidate fillers from current group
expand through lattice inheritance
score candidates
bind high-confidence candidates
create placeholders for low-confidence required ports
ask repair only when action depends on missing certainty
```

Port score:

```text
score =
  kind_match
  + parent_concept_match
  + edge_pattern_match
  + construction_support
  + source_trust
  + temporal_fit
  + discourse_salience
  - contradiction_penalty
  - freshness_penalty
  - complexity_penalty
```

### 5.8 Inherit

Pull from parent concepts:

```text
ports
acceptable predicates
causal affordances
evidence policies
temporal policies
constraints
```

Inheritance must be traceable.

If inherited structure conflicts with local evidence, do not overwrite local evidence. Mark conflict.

### 5.9 PredictAffordances

Run affordance predictors over bound graph patterns.

Output:

```text
predicted effects
possible needs
blocked actions
enabled actions
evaluation shifts
freshness requirements
```

Predictions stay tentative unless confirmed.

### 5.10 Compare/Verify

Check:

```text
source reliability
permission scope
time/freshness
contradictions
known counterexamples
missing required ports
unsupported current-world claims
```

### 5.11 PlanAct

The planner consumes:

```text
working graph
resolved ports
predicted affordances
construction pragmatics
source/evidence policies
conversation context
```

Output:

```text
reply obligations
memory patch candidates
tool/retrieval requirements
repair questions
action plans
```

### 5.12 ExtractGraphPatches

Extract possible durable updates.

Examples:

```text
new alias
new concept atom
new port
new predicate schema
new causal affordance
new construction
new source trust signal
high-value exemplar
discard duplicate
```

### 5.13 ConsolidateAsync

Consolidation is not on the critical path unless the user explicitly asks to teach something and expects immediate use.

For fast runtime:

```text
online path creates patch candidates
background path validates/promotes/compresses
```

## 6. Concept Lattice

The concept lattice is the durable compressed semantic memory.

It stores concept atoms and their operational structure.

It must support:

```text
alias lookup
parent traversal
child traversal
port lookup
predicate lookup
affordance lookup
source support lookup
counterexample lookup
fingerprint nearest-neighbor search
staleness/freshness checks
```

## 7. Concept State Machine

All concepts move through this lifecycle:

```text
unknown_surface
-> candidate_atom
-> typed_candidate
-> operational_atom
-> consolidated_atom
```

Side states:

```text
contested_atom
stale_atom
deprecated_atom
merged_atom
```

### 7.1 unknown_surface

Seen in text but not interpreted.

Action:

```text
create surface evidence
try construction context
try source lookup if allowed
```

### 7.2 candidate_atom

Tentative concept.

Action:

```text
assign probable atom kind
attach source/evidence
do not over-trust
```

### 7.3 typed_candidate

Has likely parent or category.

Action:

```text
inherit weak ports
allow low-risk use
track uncertainty
```

### 7.4 operational_atom

Has enough ports/predicates to use.

Action:

```text
use in parsing and planning
continue collecting support
```

### 7.5 consolidated_atom

Stable compressed knowledge.

Action:

```text
prefer for fast resolution
retain high-value exemplars only
```

## 8. Construction Lattice

The construction lattice stores learned form-meaning operators.

It must support:

```text
surface pattern matching
graph pattern matching
pragmatic effect lookup
support and counterexample scoring
promotion and decay
```

Construction learning:

```text
transcript examples
-> repeated surface patterns
-> repeated graph patches
-> construction candidate
-> support/counterexample scoring
-> promotion or decay
```

Important:

```text
construction confidence does not equal truth confidence
```

A construction may be good at proposing a graph while the graph claim itself remains unverified.

## 9. Predicate Schemas

Predicate schemas represent reusable operational relationships.

They are learned from:

```text
surface predicate use
construction patterns
dictionary definitions
source lookups
confirmed graph patches
transcript recurrence
```

Examples:

```text
leads(actor, domain)
represents(actor, domain)
held_by(role, holder, time_scope)
located_at(entity, place)
used_for(entity, process)
```

A concept may list acceptable predicates, but the predicate schema should remain a separate reusable object.

This prevents:

```text
duplicate leads() logic inside leader, president, manager, captain, head_teacher
```

## 10. Causal Affordances

Causal affordances predict likely effects from graph conditions.

They are not ports.

They are not facts.

They are conditional predictions.

Example:

```text
trigger:
  State(cold)
  holder = environment_near_user
  intensity >= moderate
effect:
  Need(warmth) or State(discomfort_risk)
confidence:
  based on support/counterexamples
```

The same atom may have different affordances under different bindings:

```text
cold + drink -> refreshment_affordance
cold + user_environment -> discomfort_risk
cold + reply -> emotional_distance
cold + storage -> preservation
```

## 11. Semantic Compression

Consolidation promotes structures only when compression gain is positive.

```text
compression_gain =
  traces_explained
  + prediction_gain
  + repair_reduction
  + source_diversity
  + causal_usefulness
  + retrieval_speed_gain
  - complexity_cost
  - contradiction_cost
  - storage_cost
```

Promote when:

```text
compression_gain > threshold
```

Decay or discard when:

```text
duplicate
low support
low usefulness
high contradiction
stale and not valuable
already compressed into stronger structure
```

## 12. Memory Policy

### 12.1 Store Durable

Store:

```text
consolidated concepts
aliases
ports
predicate schemas
causal affordances
construction atoms
source trust profiles
high-value exemplars
contradiction boundaries
```

### 12.2 Store Temporarily

Store temporarily:

```text
working graphs
raw graph traces
low-confidence candidates
duplicate utterance graphs
ordinary transcript turns
```

### 12.3 Do Not Store

Do not store long-term:

```text
every sentence
every graph
every paraphrase
every repeated known fact
every low-value transcript turn
```

## 13. Source And Evidence Policy

All graph patches must preserve:

```text
source
evidence
permission
time
confidence
freshness
```

Source types:

```text
user
conversation
self
dictionary
Wikipedia
large_llm
tool_api
document
sensor
unknown
```

Rules:

```text
user teaching can update local concept lattice with source scope
dictionary evidence is strong for lexical meaning
Wikipedia evidence is useful for broad world/entity knowledge
large_llm evidence is hypothesis only
tool/API evidence can satisfy fresh-world claims
self evidence is authoritative for current self state
```

Current-world claims need freshness.

Stable definitions usually do not.

## 14. Worked Example: Leader And President

### 14.1 Observations

```text
president is a leader
president leads a country
leader of the team
head of government
current president of X
former president of X
```

### 14.2 Initial Candidate

```text
president:
  state: candidate_atom
  atom_kind: entity
  possible_parent: leader
```

### 14.3 Consolidated Concepts

```text
leader:
  atom_kind: entity
  concept_role: role_concept
  parents:
    social_role
  ports:
    holder:
      accepted_parent_concepts: [person, group]
    domain:
      accepted_parent_concepts: [group, organization, country]
  acceptable_predicates:
    leads(actor=holder, domain=domain)
    represents(actor=holder, domain=domain)
    directs(actor=holder, domain=domain)
  causal_affordances:
    decision_by(holder) -> possible_state_change(domain)
```

```text
office_role:
  atom_kind: entity
  concept_role: institutional_role
  ports:
    holder:
      accepted_parent_concepts: [person, group]
    institution:
      accepted_parent_concepts: [organization]
    domain:
      accepted_parent_concepts: [organization, country, group]
    time_scope:
      accepted_atom_kinds: [time]
  predicates:
    held_by(role, holder, time_scope)
    belongs_to(role, institution)
  temporal_policy:
    current_holder requires fresh evidence
```

```text
president:
  atom_kind: entity
  concept_role: office_role
  parents:
    leader
    office_role
  inherited_ports:
    holder
    domain
    time_scope
  additional_constraints:
    domain commonly country or organization
```

### 14.4 Runtime Resolution

Input:

```text
Donald Trump is the current president of the USA
```

Working graph:

```text
Entity(Donald Trump)
Entity(president)
Entity(USA)
Time(current)
Relation(held_by)
Source(user)
```

Resolution:

```text
president -> concept lattice hit
president inherits office_role
office_role opens holder/domain/time_scope
holder binds Donald Trump
domain binds USA
time_scope binds current
current_holder policy requires fresh evidence
```

Planner implication:

```text
can store user assertion with source/time scope
must not present as verified current fact without fresh evidence
```

No hardcoded president branch is needed.

## 15. Worked Example: Cold

### 15.1 Concept

```text
cold:
  atom_kind: state or quality
  parents:
    temperature_state
    evaluative_quality
  ports:
    holder:
      accepted_atom_kinds: [entity, place, state, process]
    domain:
      accepted_parent_concepts: [temperature, social_interaction, storage, affect]
    intensity:
      accepted_atom_kinds: [quantity, quality]
    place:
      accepted_atom_kinds: [place]
    time:
      accepted_atom_kinds: [time]
```

### 15.2 Affordances

```text
affordance: cold_environment_discomfort
trigger:
  cold.domain = temperature
  cold.holder = environment_near_user
  cold.intensity >= moderate
effect:
  user may have discomfort_risk
  user may need warmth
```

```text
affordance: cold_drink_refreshment
trigger:
  cold.domain = temperature
  cold.holder parent = drink
effect:
  drink may be refreshing
```

```text
affordance: cold_reply_distance
trigger:
  cold.domain = social_interaction
  cold.holder parent = utterance/reply/person
effect:
  emotional_distance evaluation
```

### 15.3 Runtime

Input:

```text
it is very cold where I am
```

Resolution:

```text
State(cold)
holder = environment_near_user
intensity = very
place = user_location_unknown
time = now
```

Affordance prediction:

```text
cold_environment_discomfort activated
```

Planner implication:

```text
acknowledge user state/context
optionally suggest warmth
do not treat as live weather query unless user asks
```

## 16. Transcript Learning

Human-human chat logs are self-supervised data.

Signals:

```text
question-answer adjacency
corrections
confirmations
disagreements
repairs
paraphrases
topic shifts
narrative sequences
emotional reactions
```

Learning loop:

```text
segment transcript
build working graphs
extract repeated graph fragments
cluster by surface and graph shape
induce construction candidates
induce concept candidates
induce port candidates
induce predicate schemas
induce causal affordances
score compression gain
promote or decay
```

## 17. Performance Requirements

### 17.1 Hot Path

The online path must be fast:

```text
normalize
segment
construction match
atomize
concept lookup
port resolution
planner
```

Keep slow operations async:

```text
large source lookups
LLM hypothesis generation
full transcript mining
consolidation
fingerprint rebuild
counterexample mining
```

### 17.2 Required Indexes

Concept lattice:

```text
alias -> concept_id
parent -> child concepts
concept_id -> ports
concept_id -> predicates
concept_id -> affordances
fingerprint ANN index
stale/current policy index
```

Construction lattice:

```text
surface ngram signature -> construction_id
graph pattern signature -> construction_id
pragmatic signature -> construction_id
```

Trace store:

```text
graph_shape_hash
source_id
time_bucket
construction_id
concept_id
```

### 17.3 Caches

Use caches for:

```text
concept lookup
inherited ports
inherited predicates
inherited affordances
construction matches
port resolver candidate sets
```

Invalidate caches when:

```text
concept parent changes
ports change
predicate schema changes
affordance promoted/removed
construction promoted/removed
source trust materially changes
```

## 18. Module Boundaries

Recommended modules:

```text
cemm/types/uol_graph.py
  UOLAtom, UOLEdge, UOLGraph

cemm/types/concept_atom.py
  ConceptAtom, ConceptState

cemm/types/operational_port.py
  OperationalPort, PortBinding, ResolverPolicy

cemm/types/predicate_schema.py
  PredicateSchema

cemm/types/causal_affordance.py
  CausalAffordance

cemm/types/construction_atom.py
  ConstructionAtom

cemm/types/graph_patch.py
  GraphPatch, PatchOperation

cemm/memory/concept_lattice.py
  durable concept/port/predicate/affordance store

cemm/memory/construction_lattice.py
  construction storage and matching indexes

cemm/memory/episodic_trace_store.py
  sparse trace/replay memory

cemm/kernel/meaning_perceptor.py
  signal -> meaning groups and initial atoms

cemm/kernel/meaning_graph_builder.py
  meaning packet -> working UOL graph

cemm/kernel/construction_matcher.py
  surface/graph patterns -> construction candidates

cemm/kernel/concept_resolver.py
  surface atoms -> concept lattice resolution

cemm/kernel/port_resolver.py
  open ports -> graph bindings

cemm/kernel/affordance_predictor.py
  bound graph -> possible effects

cemm/kernel/semantic_cpu.py
  operator orchestration

cemm/kernel/act_resolution_planner.py
  graph/operator state -> reply/action/retrieval/memory plans

cemm/learning/graph_patch_extractor.py
  working graph -> patch candidates

cemm/learning/concept_consolidator.py
  patch candidates -> concept lattice updates

cemm/learning/construction_inducer.py
  traces -> construction atoms

cemm/learning/predicate_schema_inducer.py
  traces -> predicate schemas

cemm/learning/causal_affordance_inducer.py
  traces -> affordances
```

## 19. Implementation Pitfalls

Avoid these.

### 19.1 Static Domain Ontology

Bad:

```text
define all possible entity classes upfront
```

Good:

```text
seed minimal candidates, let concepts grow through evidence
```

### 19.2 Static Slot Filling

Bad:

```text
travel.destination
weather.location
president.country
```

Good:

```text
atom-owned ports resolved through lattice and graph context
```

### 19.3 Effect As Field

Bad:

```text
cold.possible_effect = discomfort
```

Good:

```text
affordance triggered by bound graph condition
```

### 19.4 Construction As Regex

Bad:

```text
if text matches "X is Y": write memory fact
```

Good:

```text
construction proposes graph patch, verifier/consolidator decides promotion
```

### 19.5 Graph Hoarding

Bad:

```text
store every utterance graph forever
```

Good:

```text
store compressed structures and only high-value exemplars
```

## 20. Acceptance Tests

### 20.1 President Test

Input:

```text
a president is a leader of a country
```

Expected:

```text
working graph contains president, leader, country atoms
graph patch proposes president is_a leader
president concept gains/inherits domain port from leader/office_role only after consolidation
no hardcoded president branch is used
```

Input:

```text
Donald Trump is the current president of the USA
```

Expected:

```text
holder/domain/time_scope ports are dynamically resolved
current holder relation triggers fresh evidence policy
user assertion can be stored as sourced claim
system must not claim verified current truth without fresh source
```

### 20.2 Cold Test

Input:

```text
it is very cold where I am
```

Expected:

```text
cold state/quality atom created
holder/intensity/place/time ports resolved or placeholder-bound
discomfort/warmth is predicted by affordance, not stored as static port
planner acknowledges context instead of demanding verification
```

Input:

```text
the cold drink was refreshing
```

Expected:

```text
cold holder binds drink
refreshment affordance is compatible
discomfort affordance is not activated
```

### 20.3 Unknown Word Test

Input:

```text
a zorbal is a kind of container used for storing water
```

Expected:

```text
zorbal candidate concept created
parent candidate container attached
used_for predicate schema candidate created/reused
container ports can be inherited weakly
no hardcoded zorbal required
```

### 20.4 Construction Test

Transcript contains repeated:

```text
X means Y
X refers to Y
by X I mean Y
```

Expected:

```text
construction candidate induced
operator effect proposes same_as/definition graph patches
support and counterexamples tracked
construction does not directly write durable truth
```

### 20.5 Compression Test

Given 100 paraphrases supporting the same relation:

```text
leader leads group
head leads team
manager directs team
```

Expected:

```text
predicate schema and concept ports strengthen
redundant traces decay
small exemplar set retained
memory size grows sublinearly
```

## 21. Programmer Checklist

Before implementing any feature, ask:

```text
Is this a kernel atom kind or a learned concept?
Is this a port, predicate, affordance, policy, or construction?
Does it produce a working graph update or a durable graph patch?
Where is source/time/evidence/permission stored?
Can this be resolved through the lattice instead of hardcoded?
Can repeated examples compress into one structure?
What decays or gets discarded?
What cache/index is needed for the hot path?
```

If the answer requires adding a domain-specific special case, stop and model it as:

```text
concept atom
operational port
predicate schema
causal affordance
construction atom
graph patch
```

## 22. Final Contract

CEMM's architecture is:

```text
fixed primitive atom kinds
+ dynamic concept lattice
+ learned construction operators
+ dynamic port resolution
+ contextual causal affordance prediction
+ graph-patch consolidation
+ aggressive semantic compression
```

The system should grow deeper, not larger.

Every new experience should either:

```text
improve a reusable structure
create a useful new structure
mark a contradiction or exception
or be discarded after its trace window
```

That is the boundary between CEMM as a learning semantic runtime and CEMM as an ever-growing database.
