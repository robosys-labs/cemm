> **SUPERSEDED (architecture authority):** This document describes the CEMM 3.3 architecture that the current runtime still implements. The governing target architecture is now v3.4 — see root `AGENTS.md` and `cemm/ARCHITECTURE.md`. Use this file only to understand the existing 3.3 implementation during migration.

# CEMM 3.3 Core Architecture

**Version:** 3.3 target contract  
**Status:** canonical architecture for the active upgrade  
**Audience:** implementers, reviewers, and researchers  
**Scope:** multilingual/multimodal perception, UOL graph semantics, recursive learning, grounding, operators, state, causality, contracts, memory, response formation, and conformance  
**Non-goal:** transcript-specific response fixes, permanent utterance storage, or untraceable semantic authority

---

## 1. Thesis

CEMM is an authority-preserving semantic transaction and learning runtime.

It must both:

1. execute already grounded meaning correctly; and
2. acquire missing language and operational structure through bounded recursive interaction.

The complete architecture is:

```text
EXECUTION SPINE
signal evidence
-> interpretation lattice
-> grounded semantic branch
-> scoped predicate/operator activation
-> state and causal transition model
-> obligation graph
-> contracts and execution ledger
-> response, action, and applied state

ACQUISITION SPINE
semantic uncertainty
-> typed gap graph
-> learning episode
-> minimum-information acquisition
-> provisional semantic artifact
-> resumed execution
-> use/correction outcomes

CONSOLIDATION LOOP
learning evidence ledger
-> strength and independence projection
-> schema/sense revision
-> validated graph patches
-> scoped durable memory
```

Learning is not a final phase after response. It participates in perception, interpretation, grounding, operator activation, query, state, response, and post-use revision.

---

## 2. Architecture laws

### 2.1 Evidence, interpretation, and authority are separate

The runtime distinguishes:

```text
observed evidence
candidate interpretation
selected branch
grounded proposition
activated operator
authorized contract
executed result
committed state or memory
```

No stage may silently skip an authority transition.

### 2.2 The UOL kernel is small and stable

Canonical atom kinds:

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

Canonical edge categories remain limited and structural. Domain concepts and predicates do not become new primitive kinds.

### 2.3 Domain meaning is dynamic

Concepts such as person, animal, organization, president, database, illness, cold, ownership, politeness, and danger are learned or seeded concept/schema artifacts.

They can be:

```text
candidate
typed
operational
consolidated
contested
restricted
stale
superseded
merged
retired
```

### 2.4 Unknown meaning is represented, not guessed away

Unknown material produces typed `SemanticGap` objects. Neutral unresolved meaning has no query, write, state, safety, or response authority.

### 2.5 Durable mutation is graph-patch-only

All durable changes flow through provenance-bound operations, validation, contradiction handling, scope policy, and commit.

### 2.6 State transitions are authorized transactions

A proposed state change does not alter state until its scope, modality, polarity, authority, permission, and applicability are resolved.

### 2.7 Grammar is semantic

Function words, morphology, word order, prosody, gesture, and multimodal cues may alter reference, roles, topology, modality, time, permission, and discourse structure.

### 2.8 NLG never repairs semantic failures

Response planning and realization consume selected semantic contracts and results. They do not inspect raw input to infer missing meaning.

---

## 3. Semantic authority model

Every authority-bearing artifact carries:

```python
artifact_id
artifact_kind
authority_state
branch_id
group_id
source_refs
evidence_refs
permission_refs
temporal_scope
language_or_modality
confidence
provenance_chain
```

Authority states:

```text
observed
candidate
selected
grounded
scoped
validated
authorized
executed
committed
```

Terminal or side states:

```text
unresolved
suppressed
contradicted
quarantined
rejected
expired
retired
```

Allowed transitions are validated centrally. Confidence alone cannot grant authority.

---

## 4. Typed references

Business logic uses typed references rather than ad-hoc strings.

```python
@dataclass(frozen=True, slots=True)
class SemanticRef:
    kind: str
    id: str
    scope: str = ""
    version: int = 0
```

Required kinds include:

```text
signal, span, group, branch
entity, concept, predicate, operator, port
state, transmutation, effect
source, permission, evidence
gap, learning_episode, learned_artifact
obligation, contract, execution_result
response_plan, output_act
```

Serialization may use compact strings, but internal matching, hashing, and indexing use typed fields.

---

## 5. Evidence and provenance

### 5.1 Evidence records

Each observation preserves:

```text
source
signal/span location
language/script/modality
time
permission scope
reliability
confidence
normalization transform
dependency/independence key
```

Normalization never destroys the original surface.

### 5.2 Provenance chains

Every selected interpretation and learned artifact can be traced back to evidence and transforms.

Provenance merge is immutable and deduplicated. A late stage may add provenance but not replace earlier provenance.

### 5.3 Evidence independence

Repeated evidence from the same source, session, copied text, or causal chain is not counted as independent support.

Independence keys prevent confidence inflation.

---

## 6. Perception and interpretation

### 6.1 Language and multimodal adapters

Adapters produce evidence and candidates for:

```text
tokenization and normalization
script and language
morphology
NER and entity mentions
lexical senses
grammatical functions
predicate heads
arguments and roles
polarity and modality
time and place
discourse/connective relations
construction matches
multimodal referents and events
```

Adapters do not activate operators or authorize consequences.

### 6.2 Meaning groups

An utterance may contain multiple meanings. Segmentation preserves:

```text
clause groups
predicate groups
vocatives
evaluations
parentheticals
quoted/reported spans
discourse fillers
coordination and subordination
```

Groups form a discourse graph, not just a flat list.

### 6.3 Interpretation lattice

Each ambiguous span or group may have multiple candidate subgraphs.

```python
@dataclass(frozen=True, slots=True)
class InterpretationBranch:
    branch_id: str
    parent_branch_id: str
    group_ids: tuple[str, ...]
    candidate_atom_ids: tuple[str, ...]
    candidate_edge_ids: tuple[str, ...]
    assumptions: tuple[str, ...]
    unresolved_gap_ids: tuple[str, ...]
    confidence: float
    authority_state: str = "candidate"
```

Branch pruning uses semantic compatibility, grounding quality, evidence, source policy, context, and budget. Rejected branches remain diagnosable.

### 6.4 No direct alias activation

A lexical alias produces a candidate such as:

```text
surface span -> possible operator/concept/relation/state/grammar mapping
```

It does not produce an activated action or applied state.

---

## 7. Entity and reference grounding

Entity grounding resolves:

```text
mention
entity kind
identity
speaker/listener/self
deixis
anaphora and coreference
cross-turn salience
new entity candidate
role placeholder
```

Canonical outcomes:

```text
resolved
candidate
ambiguous
placeholder
unresolved
```

A placeholder cannot satisfy a required port or become a state/query/write target.

Grounding uses:

```text
current group
discourse graph
ContextKernel
SessionStore
provisional learned bindings
durable entity/concept indexes
time/place compatibility
source and permission
```

Entity salience is scoped and decays. It is evidence, not identity authority.

---

## 8. Grammar and construction learning

### 8.1 Grammar operator bindings

Language-specific forms map to language-neutral semantic effects.

```python
@dataclass(frozen=True, slots=True)
class GrammarOperatorBinding:
    binding_id: str
    language_tag: str
    form_signature: str
    function_kind: str
    semantic_effect: dict
    context_constraints: tuple[str, ...]
    scope: str
    authority_state: str
    evidence_refs: tuple[str, ...]
```

Functions include:

```text
definiteness and specificity
number and quantification
possession
source, goal, path, containment, instrument, accompaniment
tense, aspect, completion
modality, negation, evidentiality
causal, conditional, contrastive, and temporal discourse
case/role assignment
information structure
```

### 8.2 Construction schemas

Constructions are learned form-meaning graph operators, not regex routes.

They propose graph rewrites and expected ports. They never directly commit memory or choose a response.

### 8.3 Morphology

Learnable morphology may map stems, affixes, reduplication, agreement, case, tense, aspect, and derivation to semantic candidates.

Morphological evidence is language-scoped and may be dialect-scoped.

---

## 9. Predicate and operator activation

### 9.1 Candidate operator

A lexical or construction match first creates an `OperatorCandidate`.

### 9.2 Predicate activation frame

```python
@dataclass(frozen=True, slots=True)
class PredicateActivationFrame:
    activation_id: str
    branch_id: str
    operator_ref: SemanticRef
    predicate_ref: SemanticRef
    port_bindings: tuple["TypedPortBinding", ...]
    illocution: str
    modality: str
    polarity: str
    evidential_status: str
    temporal_scope: str
    quotation_scope: str
    completion_status: str
    applicability_status: str
    authority_state: str
    provenance: tuple[str, ...]
```

Activation requires:

```text
predicate-head evidence
argument alignment
required typed ports
entity-kind compatibility
precondition evaluation
polarity scope
modality/illocution scope
quotation/reporting scope
temporal scope
permission and safety policy
```

### 9.3 Operational ports

Ports are typed openings owned by concepts, relations, predicates, or operators.

```text
actor
patient/target
object/theme
recipient/beneficiary
instrument
source/goal/path
place
time
domain
state dimension/value
evidence/source
```

Unresolved required ports create gaps. They are never silently defaulted to user, self, or generic object.

### 9.4 Operator learning

A new surface form may alias an existing operator after minimal evidence.

A new operator schema requires stronger evidence:

```text
operator family
typed required/optional ports
preconditions
state and relation effects
modality and completion behavior
permission/risk class
counterexamples
```

High-risk operator schemas are quarantined until policy-authorized validation.

---

## 10. State architecture

### 10.1 State coordinate

A state coordinate is:

```text
target entity/concept/conversation
+ state family
+ dimension
+ value/scale
+ time
+ authority
```

State schemas define applicability to entity kinds and value semantics.

### 10.2 Occupancy

`StateOccupancyFrame` represents the best current projection for a coordinate, including source, time, confidence, and conflict set.

Occupancy is a materialized view, not the only evidence.

### 10.3 Delta

`StateDeltaFrame` is a proposed change associated with a grounded event/operator or explicit report.

Kinds include:

```text
observed
reported
desired
commanded
hypothetical
predicted
negated
quoted
completed
tool_verified
```

### 10.4 Transmutation

```python
@dataclass(frozen=True, slots=True)
class StateTransmutationFrame:
    transmutation_id: str
    branch_id: str
    source_frame_id: str
    target_ref: SemanticRef
    state_family: str
    dimension: str
    prior_value: object
    proposed_value: object
    direction: str
    kind: str
    authority: str
    temporal_scope: str
    persistence_policy: str
    reversible: bool
    evidence_refs: tuple[str, ...]
```

### 10.5 Authorization and application

```text
transmutation candidate
-> schema applicability
-> conflict resolution
-> permission/safety
-> obligation/contract authorization
-> apply
-> StateTransmutationResult
```

Persistence classes:

```text
working-cycle only
session state
user-scoped durable state
domain/global semantic state
graph-patch candidate
quarantine
reject
```

Session state is applied to `ContextKernel` and persisted by `SessionStore`. Durable semantic state is graph-patch mediated.

---

## 11. Semantic gaps and recursive acquisition

### 11.1 SemanticGap

A gap identifies a missing field required to ground a branch.

```python
@dataclass(frozen=True, slots=True)
class SemanticGap:
    gap_id: str
    branch_id: str
    group_id: str
    span_ref: SemanticRef
    gap_kind: str
    required_fields: tuple[str, ...]
    blocking_artifact_ids: tuple[str, ...]
    candidate_hypothesis_ids: tuple[str, ...]
    questionability: float
    confidence: float
```

Gap kinds:

```text
lexeme sense
morphology
grammar function
construction
entity kind/identity
relation identity/orientation
operator identity
required port
state family/dimension/value
time/place/geospatial anchor
modality/polarity
causal effect
realization form
```

### 11.2 Blocking analysis

A gap blocks only artifacts that depend on it. Unrelated obligations may proceed.

### 11.3 LearningEpisode

```python
@dataclass
class LearningEpisode:
    episode_id: str
    context_id: str
    scope: str
    target_gap_ids: list[str]
    dependency_graph: dict[str, list[str]]
    hypotheses: list[str]
    questions_asked: list[str]
    evidence_event_ids: list[str]
    provisional_artifact_ids: list[str]
    resume_branch_id: str
    recursion_depth: int
    budget_remaining: int
    promotion_ceiling: str
    status: str
```

The episode persists across turns and prevents repeated questions.

### 11.4 Minimum-information question planning

Select the question that maximizes:

```text
expected uncertainty reduction
× blocking importance
× future reuse value
× answerability
÷ user effort and interaction cost
```

Ask one focused question by default. Avoid requesting a full definition when a typed relation or operator alias is enough.

### 11.5 Answer assimilation

The next user response is interpreted both as a normal turn and as evidence for the active episode. Episode context does not bypass ordinary perception, source, permission, or safety.

After assimilation:

```text
update hypotheses
satisfy or refine gaps
install provisional binding if threshold reached
resume affected branch or defer to next turn
ask the next minimum question if still blocked
```

---

## 12. Learned artifacts and scope

Learnable artifact classes:

```text
surface normalization
morphology rule
lexeme sense
cross-language mapping
grammar operator binding
construction schema
concept and entity
entity-kind relation
predicate/relation schema
operator schema and ports
state term/dimension/value mapping
causal/affordance rule
realization form
source trust/context rule
```

Scope progression:

```text
turn-local
session provisional
user
domain or organization
dialect
language
global
```

A narrower artifact may shadow a broader artifact when context matches. Promotion is evidence-driven, never automatic from frequency alone.

---

## 13. Learning evidence, strength, and revision

### 13.1 Evidence ledger

```python
@dataclass(frozen=True, slots=True)
class LearningEvidenceEvent:
    event_id: str
    artifact_ref: SemanticRef
    event_kind: str
    source_ref: SemanticRef
    context_signature: str
    independence_key: str
    support_delta: float
    contradiction_delta: float
    occurred_at: float
    evidence_refs: tuple[str, ...]
```

Events include:

```text
occurrence
explicit teaching
confirmation
correction
successful use
repair failure
prediction success/failure
independent source support
context restriction
temporal supersession
```

### 13.2 KnowledgeStrength

A derived materialized view:

```text
semantic confidence
source trust
support and contradiction mass
source/context independence
language and domain coverage
successful-use and repair-failure rates
freshness
stability
promotion eligibility
```

The projection formula is versioned and reproducible.

### 13.3 Revision

Contradictory evidence may:

```text
reinforce
weaken
restrict context
split a sense
supersede temporally
merge duplicate artifacts
quarantine
retire
```

Polysemy is represented as distinct context-conditioned senses, not one overwritten mapping.

### 13.4 Immediate reuse

Once minimum grounding is satisfied, an artifact enters the session provisional overlay and participates in the next normalization/perception/grounding cycle before durable consolidation.

The overlay has expiry, provenance, scope, and rollback.

---

## 14. Operational meaning and causality

### 14.1 OperationalMeaningFrame

A planner-facing view compiled from grounded UOL structure. It is not a new UOL primitive.

It carries:

```text
frame type
target scope
grounded subject/predicate/object/ports
state transmutations
query/write/reaction/safety/learning implications
source, evidence, permission, time
branch and group provenance
confidence and unresolved dependencies
```

No generic assertion automatically implies a write.

### 14.2 Causal effect graph

Effects are compiled from:

```text
activated operator schemas
authorized state deltas
affordance predictions
durable causal knowledge
temporal and permission constraints
reaction/style effects
learning/use outcomes
```

An effect graph retains support, conflicts, prerequisites, and reversibility.

Predictions remain tentative until observed or verified.

---

## 15. Obligation graph

A turn may produce multiple compatible obligations:

```text
answer
write or remember
acknowledge state
repair
clarify a gap
retrieve fresh evidence
apply session state
safety preemption
perform or propose an action
teach/learn
```

```python
@dataclass(frozen=True, slots=True)
class ObligationNode:
    obligation_id: str
    kind: str
    source_frame_ids: tuple[str, ...]
    dependency_ids: tuple[str, ...]
    conflicts_with: tuple[str, ...]
    priority: int
    utility: float
    cost: float
    required: bool
```

Selection uses compatibility, dependencies, evidence, risk, budget, and utility.

Global preemption is reserved for:

```text
safety
permission denial
hard contradiction
required clarification for a dependent operation
```

A write does not automatically suppress a query or social acknowledgment.

---

## 16. Contract compilation and execution

One `OperationalContractCompiler` is authoritative. It delegates to specialized builders but produces one coherent bundle:

```text
QueryContract
WriteContract
StateContract
ReactionContract
SafetyContract
ActionContract
LearningContract
ResponseContract
```

Every contract contains:

```text
authorized source obligation/frame/branch IDs
required evidence and permissions
scope and temporal policy
budget
failure policy
prohibited operations
```

Execution returns an append-only `ExecutionLedger`:

```text
planned
authorized
executed
committed
rejected
quarantined
failed
rolled back
```

Later response and learning consume results, not assumptions.

---

## 17. Query architecture

Queries execute only from `QueryContract`.

Contract fields include:

```text
query kind
target scope
subject/object entity or concept
relation/predicate family
dimension
time/freshness
projection policy
ambiguity and abstention policy
evidence threshold
inference budget
```

The query engine performs indexed, contract-compatible expansion only.

Forbidden:

```text
raw question token matching
relation guessing from English
normal broad durable scans
fallback to unrelated relations
synthetic compound concepts used to hide missing relation structure
```

Role-holder queries and concept-definition queries are distinct semantic contracts.

---

## 18. Write and memory architecture

Patch operations carry exact provenance:

```text
source branch
meaning frame
group and instruction
state transmutation
learning episode/gap
source/evidence/permission
```

Authorization requires operation provenance to be included in the contract's authorized source set.

Durable memory layers:

```text
concept/entity lattice
predicate/operator schemas
construction and grammar bindings
state/effect knowledge
durable relation/state records
learning evidence ledger
small episodic exemplar store
source and permission policy
```

Indexes include semantic scope, subject, predicate/relation, object, dimension, time/freshness, language, context signature, and artifact authority state.

---

## 19. Safety architecture

Safety is derived from grounded operational meaning, permissions, activated operators, and state transmutations.

A dangerous term mentioned as a noun, quote, negated action, hypothetical, definition, or report is not automatically a requested harmful action.

Safety gates examine:

```text
target
operator applicability
illocution
modality and polarity
completion/proposal status
state effects
permission/risk schema
source and context
```

Safety remains non-budgetable and cannot be weakened by learned aliases or user-taught schemas.

---

## 20. Response formation

Input:

```text
selected obligations
contract bundle
execution ledger
answer/evidence bindings
write/state/action/learning outcomes
safety and reaction state
style and budget
language
```

Pipeline:

```text
primitive goals
-> response moves
-> candidate plans
-> hard gates
-> ranking and selection
-> realization units
-> language renderer
-> OutputActFrame
-> ResponseBundle
```

Response formation cannot:

```text
inspect raw input for routing
invent missing slots
claim uncommitted writes/actions
realize blocked candidates
print internal evidence traces by default
```

Fallbacks are semantic response moves, not hardcoded English in the engine.

---

## 21. Output and session state

Language renderers return structured output metadata:

```python
@dataclass(frozen=True, slots=True)
class OutputActFrame:
    act_kind: str
    expected_reply_kind: str = ""
    target_refs: tuple[SemanticRef, ...] = ()
    language: str = "und"
    source_plan_id: str = ""
```

`OutputStateUpdater` consumes `OutputActFrame`, not regex over generated text.

`SessionStore` persists:

```text
conversation/discourse state
entity salience and reference anchors
state occupancy
style/temperature/reaction state
pending output acts
active learning episodes
provisional learning overlays
topic and teaching context
```

---

## 22. Budget and performance

A single cycle budget allocates work across:

```text
interpretation branches
grounding candidates
semantic gaps/questions
retrieval
causal inference
state resolution
contracts
response candidates
learning consolidation
```

Cheap-to-expensive cascade:

```text
language/schema/provisional indexes
-> graph-local indexes
-> session state
-> indexed durable lookup
-> source/tool retrieval
-> background consolidation
```

Safety, permissions, provenance, truthfulness, and state applicability are never removed by budget.

Normal hot paths must avoid whole-store scans and repeated graph scans. Compile graph indexes once and pass immutable views.

---

## 23. Conformance

Static checks forbid raw-surface routing in:

```text
operational meaning compiler
state/causal compiler
obligation and contract builders
query execution
patch authorization
safety decision
response planning
```

Runtime conformance validates:

```text
authority transitions
provenance completeness
branch/frame-scoped execution
typed-port completeness
state schema applicability
single contract authority
no blocked realization
no unauthorized mutation
```

Golden traces are UUID-insensitive and compare semantic structure.

Fuzz and metamorphic tests cover language noise, clause reorderings, quotations, negations, translations, repeated evidence, contradictory teaching, and poisoning attempts.

---

## 24. Canonical runtime sequence

```text
restore context/session/learning
-> normalize evidence
-> segment and propose interpretations
-> construct candidate UOL branches
-> ground references and context
-> detect gaps
-> activate scoped predicates/operators
-> project state occupancy
-> compile deltas/transmutations
-> compile operational meanings/effects
-> build obligation graph
-> add learning/clarification obligations
-> compile contracts once
-> authorize and execute
-> record execution ledger
-> form and realize response
-> apply output/session state
-> observe use and correction outcomes
-> emit learning/revision patches
-> persist and consolidate
```

This sequence is causal. A later stage cannot compensate for an invalid earlier authority transition.

---

## 25. Transitional migration

The current codebase contains useful 3.1/3.2 components but also parallel and surface-driven paths.

Migration order:

```text
1. observability and structural golden traces
2. typed refs, provenance, authority transitions
3. interpretation lattice and candidate-only lexical mappings
4. entity grounding and scoped predicate activation
5. state transaction application and persistence
6. semantic gaps, episodes, and provisional overlays
7. operational meaning/effect and obligation graphs
8. single contract compiler and execution ledger
9. frame-scoped query/write/state/learning execution
10. structured output acts
11. durable evidence ledger and consolidation
12. multilingual grammar/construction acquisition
13. delete legacy parallel authorities
14. enforce conformance and performance gates
```

Do not label the migration complete until legacy paths are removed and the canonical runtime proves each invariant.

---

## 26. Required deletions or quarantine

Target for deletion or strict isolation:

```text
direct alias-to-action activation
missing actor/user defaults
placeholder entities satisfying ports
early schema delta projection
surface teaching/remember parsing in graph builder
surface sanitizers in patch extraction
authority-creating unknown fallbacks
single-primary meaning suppression
duplicate contract builders
legacy surface-based query construction
unapplied state transmutations
output-state English regex reparsing
response-only learning disconnected from acquisition
```

Language-specific seed resources remain allowed only inside language/grammar adapters and must emit candidates with provenance.

---

## 27. Completion contract

CEMM 3.3 is complete when all are true:

```text
new words in supported languages open typed learning gaps
the system recursively acquires only missing operational fields
new meanings are immediately reusable within authorized scope
future use updates evidence-backed strength and revision
grammar forms map to language-neutral operational effects
operators require scoped predicate activation and valid ports
state changes are authorized, applied, persisted, and queryable
multi-meaning turns produce compatible obligations
contracts are compiled once and execution is ledgered
writes and learning are frame-scoped and graph-patch mediated
queries are contract-indexed and surface-blind
safety uses grounded actions/transmutations, not word presence
responses are generated only from selected evidence/results
output state uses structured acts
legacy competing authorities are removed
structural, multilingual, learning, safety, and performance tests pass
```
