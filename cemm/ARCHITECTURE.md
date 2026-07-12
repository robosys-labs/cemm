# CEMM v3.4 — Final Integrated Cognitive Semantic Kernel Architecture

Status: active governing architecture upon merge  
Audit baseline: `8e0da751edbd86460049ef14f56fda66cc05de84`  
Version character: semantic-authority replacement, not a compatibility overlay

## 1. Purpose

CEMM v3.4 defines the minimum closed architecture that can coherently simulate functional cognitive agency.

It must be able to:

- interpret compositional, nested, multilingual meaning;
- represent entities, concepts, values, states, events, places, time, sequence, and causality;
- distinguish actual, reported, believed, hypothetical, desired, quoted, counterfactual, and simulated content;
- know what is stored, accessible, retrieved, supported, contradicted, understood, or unknown in a bounded sense;
- maintain a truthful live model of its own capabilities, resources, permissions, limitations, and reliability;
- create goals from requests, needs, commitments, gaps, and policies;
- plan and execute cognitive, communicative, and adapter-backed operations;
- reconcile predicted and observed outcomes;
- learn new lexemes, predicate schemas, roles, state dimensions, constructions, and realization mappings through ordinary semantic interaction;
- explain and express selected meaning in language a person can understand.

The system models **operational self-awareness**: information about self, world, memory, capabilities, goals, and outcomes becomes available to a bounded workspace and can guide action and communication. It does not assert biological consciousness.

## 2. Why v3.3 must be replaced at the authority boundary

The current architecture contains valuable components but distributes meaning authority among:

```text
surface aliases and whole-turn constructions
conversation-act classification
relation extraction
action/operator schemas
predicate schemas
fixed UOL atom and edge kinds
operational ports
operational meaning frames
instruction and obligation kinds
context/self dataclasses
learning episodes and session overlays
response goal labels and render templates
```

This produces recurring failure patterns:

- surface forms become operational decisions;
- state, action, relation, and query meaning are reconstructed multiple times;
- semantic relations exist as both nodes and graph edges;
- learning records do not change the ordinary interpreter;
- self-capability claims are static rather than derived;
- queries collapse into broad intent or concept templates;
- response layers repair missing meaning rather than verbalizing selected meaning.

v3.4 changes the representation, authority map, and control loop together.

## 3. Architectural closure

A cognitive kernel is closed when the same substrate can represent and operate on:

```text
world content
language content
self content
knowledge and uncertainty
goals and needs
operations and outcomes
learning targets
response content
```

CEMM v3.4 establishes closure through three layers.

### 3.1 Layer A — canonical semantic graph

```text
Referent
Value
Predication
Proposition
ContextFrame
EvidenceRecord
StructuralLink
```

This is the only canonical meaning representation.

### 3.2 Layer B — executable semantic schemas

```text
LexemeSenseSchema
ConstructionSchema
PredicateSchema
RoleSchema
EntityKindSchema
StateDimensionSchema
ContextSchema
OperationSchema
CapabilitySchema
RealizationSchema
PolicySchema
```

This is the only executable meaning-definition authority.

### 3.3 Layer C — cognitive-control records

```text
WorkspaceEntry
EpistemicAssessment
CapabilityAssessment
GapRecord
GoalRecord
PlanRecord
OperationInstance
ExecutionLedger
LearningTransaction
SemanticMessagePlan
MutationSet
CommitOutcome
```

These records control cognition while referencing Layer A and Layer B. They do not redefine meaning.

## 4. Canonical semantic graph

### 4.1 Referent

A stable or provisional identity that can be referred to:

```text
person
organization
object
device
software agent
concept
place
time interval
source
tool
file
schema
self
```

A referent carries identity and kind hypotheses, aliases, provenance, and scope. Kind is supplied by entity-kind schemas and propositions, not by a new Python class per domain concept.

`self` is a stable referent with a deictic role and component mapping.

### 4.2 Value

A typed semantic value:

```text
boolean
enum
text
quantity + unit
set
ordered sequence
distribution
coordinate
identifier
language tag
time point or interval
```

Values are never used as placeholder referents.

### 4.3 Predication

An occurrence of a predicate schema with typed role bindings and optional open ports.

Examples:

```text
is_a(user, engineer)
located_at(robot, lab_b)
move(robot, source=lab_a, destination=lab_b)
knows(self, proposition_p)
means(lexeme_glorp, predicate_schema_glorp)
causes(event_a, event_b)
```

Predications are language-independent. A predication may denote a relation, state, event, communicative event, cognitive operation, or normative relation according to its `PredicateSchema`.

Predications can fill roles in other predications, enabling recursive semantic composition.

### 4.4 Proposition

A truth-bearing occurrence of a predication in a context.

A proposition carries:

```text
predication_ref
context_ref
polarity
modal qualifiers
attribution/source perspective
valid_time
```

Confidence is not truth. Confidence belongs to evidence aggregation and epistemic assessment.

### 4.5 ContextFrame

A world, perspective, quotation, or simulation in which propositions are interpreted.

Minimum context kinds:

```text
actual
reported
belief
hypothetical
conditional
counterfactual
desired
simulation
quoted
```

A context frame carries:

```text
owner/perspective
parent context
assumptions
accessibility rules
inheritance rules
time window
source
```

Example:

```text
Alice said the server was not online.
```

becomes an assertion in actual conversation context whose content includes a negative `online(server)` proposition scoped to `reported_by(Alice)`. It does not directly update actual server state.

### 4.6 EvidenceRecord

Evidence connects observations and assertions to propositions or schemas.

Evidence kinds include:

```text
surface observation
user assertion
tool result
sensor observation
durable record
schema exemplar
derivation
execution outcome
counterexample
correction
```

Every evidence record preserves source, permission, time, confidence, scope, and derivation lineage.

### 4.7 StructuralLink

Structural links connect semantic objects without introducing domain meaning:

```text
has_role
instantiates
refers_to
grounded_by
scoped_by
supported_by
opposed_by
derived_from
depends_on
co_refers_with
```

Domain, cognitive, spatial, temporal, taxonomic, causal, and normative relations are predications.

## 5. Predication, proposition, and communicative composition

The architecture separates:

```text
semantic content
truth context
communicative use
```

Consider:

```text
The server is offline.
The server is not offline.
Alice believes the server is offline.
If the server is offline, restart it.
Is the server offline?
```

The reusable content is `offline(server)`.

The differences are represented by proposition polarity/context and outer communicative or cognitive predications:

```text
asserts(user, proposition)
believes(Alice, proposition)
asks(user, self, proposition_pattern)
requests(user, self, operation_or_desired_proposition)
```

Questions therefore support arbitrary nested content without creating phrase-specific query kinds.

## 6. Semantic schema system

### 6.1 SemanticSchemaStore

One versioned store resolves all executable semantic definitions by:

```text
semantic key
schema kind
language where applicable
scope
status
version
permission
support and counterevidence
```

Resolution is explicit and deterministic, but access scope is not a truth-precedence ladder. The resolver first selects sense and epistemic context, then considers applicability domain/time, access scope, structural usability, epistemic admissibility, and requested semantic operation. A narrower revision shadows a wider revision only through an explicit, journaled supersession or context-specific convention; otherwise revisions coexist as competing or attributed theories.

### 6.2 PredicateSchema

A predicate schema defines:

```text
semantic_key
predication_kind: relation | state | event
agentivity
aspect profile
roles
embedding roles
selectional constraints
co-reference constraints
context behavior
polarity and modality behavior
preconditions
predicted effects
query projections
identity/cardinality policy
evidence and persistence policy
lexicalization refs
realization refs
```

A role declares accepted semantic object families, entity kinds, value types, cardinality, requiredness, open-port behavior, and whether embedded predications/propositions are allowed.

### 6.3 OperationSchema

An operation schema defines an executable cognitive, communicative, or external operation:

```text
operation key
typed inputs and outputs
semantic preconditions
required capabilities
permissions and policies
cost/resource model
predicted effects
failure modes
idempotency behavior
adapter binding where applicable
```

Operation effects are proposals until execution and reconciliation.

### 6.4 CapabilitySchema

A capability schema describes competence and conditions for performing an operation class. It does not itself assert that the current system is capable.

### 6.5 RealizationSchema

A realization schema maps semantic/discourse configurations to language-specific lexical, syntactic, morphological, and channel choices. It never chooses factual content.


### 6.6 Grounded definition closure

The existing schema path distinguishes five conditions:

```text
recognized_surface
referentially_available
typed_schema
structurally_executable
independently_validated and epistemically admissible
```

`SchemaGroundingValidator` derives a `SchemaGroundingAssessment` for an exact schema revision and pinned environment. It validates schema-family fields, typed dependencies, pattern expressiveness, dependency closure, cycle semantics, and competence results.

The assessment is not a semantic object or activation authority. `SemanticSchemaStore` remains the only lifecycle authority.

### 6.7 Lifecycle semantics

The existing lifecycle is sufficient when its states are interpreted strictly:

```text
candidate
    identity/hypothesis exists; not structurally usable

provisional
    partial or structurally executable definition exists, but independent
    competence and/or epistemic admission is incomplete; usable only through
    an explicit qualified context and operation profile

active
    exact revision passed structural closure, required independent competence,
    epistemic/context policy, and atomic activation

superseded/rejected
    not used for new default interpretation; historical proposition bindings remain
```

The architecture deliberately does not add a second lifecycle or grounding-certificate store.

### 6.8 SchemaUseProfile

Current semantic use is derived per snapshot:

```text
SchemaUseProfile =
    structural assessment
  ∩ competence profile
  ∩ epistemic admissibility for context
  ∩ scope/access policy
  ∩ requested semantic operation
  ∩ current dependency/environment validity
```

Minimum operations are separated:

```text
reference/quote/preserve/search/probe
compose and query in attributed or hypothetical context
recognize/classify/infer in admitted contexts
interpret/predict/simulate/propose an effect
```

No schema profile authorizes execution or persistent mutation.

### 6.9 Field provenance and evidence lineage

Every learned schema contribution records its semantic path, value/pattern, provenance kind, evidence lineage, derivation, scope, context, and confidence.

Evidence independence is calculated from lineage roots and transformation history. A paraphrase, translation, generated example, or retrieved copy of one source is not independent confirmation.

### 6.10 Typed dependencies and recursive clusters

Schema dependencies are typed, for example:

```text
definition
inheritance
selectional
competence
evidence
adapter contract
policy
realization
effect
```

Strongly connected components are classified as inverse, positive-monotone, stratified-defeasible, or unsupported non-monotone.

Inverse and positive-monotone clusters require external grounded anchors, a declared inverse/fixed-point contract, non-redundant member contributions, and independent joint competence. They activate atomically.

Cycles involving negation, exception priority, destructive updates, permissions, identity collapse, cardinality replacement, or effect authorization cannot use direct joint activation.

### 6.11 Atomic activation and environment validity

Assessment pins:

```text
base schema-store revision
schema dependency revisions
grounding policy
competence suites
kernel foundation and type registry
inference/truth-maintenance policy
adapter observation contracts
context/scope policy
```

Activation uses compare-and-swap. Any drift aborts activation and forces reassessment. Concurrent child revisions never merge field-by-field without an explicit conflict decision.

## 7. Native semantic metalanguage

The system must be able to describe and learn its own schemas through ordinary propositions.

Schema records are referable objects. Boot predicates include:

```text
means
lexicalizes
defines
is_a
same_as
subtype_of
has_semantic_kind
has_role
role_requires
role_accepts
has_precondition
has_effect
has_state_dimension
has_value_type
applies_to
realized_as
```

Example teaching:

```text
“Glorp means to move quickly in a circle around something.”
```

can produce propositions about a provisional schema referent:

```text
lexicalizes("glorp", schema:glorp, language=en)
has_semantic_kind(schema:glorp, event)
subtype_of(schema:glorp, move)
has_role(schema:glorp, mover)
has_role(schema:glorp, reference_object)
has_role(schema:glorp, path)
role_accepts(path, circular_path)
has_manner(schema:glorp, quickly)
```

These propositions are validated and materialized into the same schema store used by normal interpretation.

## 8. World model

### 8.1 Identity and entity kinds

Referent resolution separates:

```text
surface mention
provisional discourse referent
cross-turn identity
canonical durable referent
entity-kind hypotheses
```

Identity confidence and kind confidence are distinct.

### 8.2 Typed states

A state is a state-kind predication whose schema supplies its dimension, holder role, value type, cardinality, and temporal policy.

Examples:

```text
mood(user, happy)
network_connectivity(self, disconnected)
battery_level(device, 12 percent)
located_at(robot, lab_b)
```

State occupancy is represented over valid-time intervals. Changes produce transition events and supersession mutations; they are not scalar overwrites without history.

### 8.3 Events

An event is an event-kind predication with stable occurrence identity, participants, aspect, time, and context.

Examples:

```text
move(robot, source=lab_a, destination=lab_b)
write(self, content=p, destination=memory)
learn(self, schema=s)
answer(self, question=q, content=p)
```

### 8.4 Place and position

Spatial schemas support absolute and relational position:

```text
located_at
inside
contains
near
far_from
left_of
right_of
above
below
between
oriented_toward
moving_toward
```

Bindings may include reference frame, coordinate system, precision, and valid time.

### 8.5 Time and sequence

Temporal schemas support:

```text
before
after
during
overlaps
starts
finishes
meets
occurs_at
has_duration
```

Event time, proposition valid time, observation time, assertion time, and record time are separate.

### 8.6 Causality

Causal content is represented as hypotheses or supported propositions, not as immediate state mutation.

Minimum distinctions:

```text
causes
enables
prevents
correlates_with
precondition_for
motivates
explains
```

A causal assessment may use mechanism schemas, temporal ordering, interventions, counterfactual simulations, repeated evidence, and counterexamples. Temporal sequence alone is insufficient.

## 9. Context, discourse, and common ground

`CommonGroundManager` maintains participant-relative discourse state:

```text
asserted
asked
answered
accepted
rejected
corrected
promised
clarification pending
learning probe pending
reference salience
active topic
```

A pending question or probe exists only after a corresponding communicative operation was successfully dispatched and output-committed.

Short answers are interpreted through expected semantic evidence schemas, not by copying raw text into a pending slot.

## 10. Memory architecture

Canonical storage uses shared semantic records plus event-sourced mutation journals.

### 10.1 Working memory

Current cycle candidates, workspace entries, and temporary derivations.

### 10.2 Common-ground memory

Conversation commitments, discourse salience, pending questions, and participant-relative acceptance.

### 10.3 Episodic memory

Events and interactions with temporal and participant context.

### 10.4 Semantic memory

Supported propositions, referents, predications, evidence, and explanations.

### 10.5 Procedural memory

Operation schemas, plan fragments, competence statistics, and successful execution patterns.

### 10.6 Schema memory

Lexical, constructional, predicate, role, entity-kind, state, capability, operation, policy, and realization schemas.

The categories are indexes and lifecycle policies, not independent truth systems.

## 11. Epistemic architecture

### 11.1 Four-state support

For proposition `p`, truth maintenance records:

```text
support_for_p
support_for_not_p
state = supported | refuted | both | neither
```

Confidence and source quality are computed separately.

### 11.2 Derived cognitive relations

`EpistemicEvaluator` derives:

```text
remembers(self, p)
has_access_to(self, p)
knows_about(self, topic)
understands(self, schema_or_structure)
believes(self, p)
knows(self, p)
```

Definitions are policy-driven and explainable.

A suggested MVP policy:

- `remembers`: a relevant persistent trace was retrieved under current permission;
- `has_access_to`: retrieval is possible now;
- `knows_about`: at least one accessible proposition/schema connects self to the topic;
- `understands`: a current operation-relative profile demonstrates the requested competencies for the exact revision under a valid dependency/environment fingerprint;
- `believes`: positive support exceeds configured threshold in an identified epistemic context, even if not knowledge-grade;
- `knows`: knowledge-grade support, actual-context admissibility, accessibility, freshness, grounding, executability, and permission are satisfied.

Structural executability is therefore neither belief nor knowledge. A user-supplied theory may be executable and queryable in `reported_by(user)` or `user_belief` while remaining inadmissible in the actual context.

### 11.3 Unknownness

Unknownness is always relative to a target and operation:

```text
unknown answer to query q
unknown referent for mention m
unknown role filler in predication x
missing predicate schema for lexeme l
unsupported proposition p
inaccessible record r
ambiguous interpretation set i
```

The kernel does not materialize an infinite complement of all possible knowledge.

## 12. Global Semantic Workspace

The workspace is the bounded set currently available to reasoning, planning, introspection, and response.

A workspace entry references semantic/control records and carries:

```text
salience
relevance to active goals
novelty
uncertainty
urgency
causal consequence
source
activation time
decay/protection policy
```

Workspace inclusion does not alter truth. Attention is a routing and resource-allocation function.

This workspace, combined with self-model access, continuity, appraisal, goals, and memory, provides the architecture's functional simulation of awareness.

## 13. Self-model and capability introspection

### 13.1 Stable self identity

The self referent is persisted across cycles and connected to:

```text
component registry
input/output channels
current operational states
resources
permissions
capability assessments
knowledge assessments
goals and commitments
operation history
reliability statistics
known limitations
```

`SelfProjection` is a read model/cache, never a second truth store.

### 13.2 Live capability derivation

Capability is evaluated for an operation in context.

```text
CapabilityAssessment(
    subject=self,
    operation_schema=generate_text,
    status=available,
    competence=0.91,
    implementation_ref=component:nlg,
    health=healthy,
    resources=sufficient,
    permission=allowed,
    conditions=[language_supported(en)],
    limitations=[text_only],
    observed_reliability=0.96,
    valid_time=now
)
```

Possible statuses:

```text
available
degraded
unavailable
permission_blocked
resource_blocked
input_unavailable
output_unavailable
unknown
```

### 13.3 Self-description

“What can you do?” composes a query over current capability assessments. Content selection groups relevant available capabilities and material limitations. NLG then expresses the selected propositions.

“What do you know about X?” queries accessible propositions and schema competency. “Do you understand X?” invokes competency criteria rather than checking whether the word appears in memory.

## 14. Needs, values, goals, and appraisal

### 14.1 Functional needs

MVP needs include:

```text
resolve active discourse obligation
reduce a blocking semantic gap
preserve truthfulness
preserve safety and permission
maintain commitment integrity
maintain semantic coherence
avoid resource exhaustion
complete authorized user goal
```

Needs generate desired propositions or information states.

### 14.2 Goals

A goal references a desired semantic condition:

```text
answered(question_q)
requested_fact_stored(proposition_p)
uncertainty_reduced(gap_g)
schema_learned(schema_s)
operation_completed(operation_o)
repair_completed(turn_t)
truthful_response_dispatched(message_m)
```

Goal lifecycle:

```text
candidate
active
suspended
satisfied
failed
abandoned
expired
```

### 14.3 Appraisal

Appraisal computes control signals such as novelty, urgency, controllability, progress, contradiction, uncertainty, expected value, and social obligation. These affect attention and planning, not truth.

## 15. Planning and execution

### 15.1 Planning

The planner receives active goals, workspace, operation schemas, capability assessments, policies, resources, and causal models.

It creates bounded plans by:

```text
matching goal conditions
selecting candidate operations
checking preconditions
simulating predicted effects
ordering dependencies
estimating cost and risk
resolving conflicts
ranking viable plans
```

### 15.2 Authorization

Authorization is a hard gate over each operation. Safety, privacy, permission, capability, and resource conditions cannot be traded away by ranking score.

### 15.3 Execution and reconciliation

The executor records start and outcome. Reconciliation compares predicted effects with observations/tool outcomes and produces:

```text
confirmed state/event effects
partial effects
failures
unexpected outcomes
prediction error
competence/reliability updates
```

No success claim is based on plan selection alone.

## 16. Recursive learning

### 16.1 Learning targets

MVP targets:

```text
LexemeSenseSchema
PredicateSchema
RoleSchema
ConstructionSchema
EntityKindSchema
StateDimensionSchema
OperationSchema constraints
RealizationSchema lexical binding
```

### 16.2 Gap record

A gap contains:

```text
target artifact
missing or conflicting fields
blocked stage and goal
preserved semantic evidence
candidate hypotheses
learnability
probe options
expected evidence schema
resume checkpoint
budgets
```

### 16.3 Transaction and replay

Learning stages a child `SemanticSchemaStore` revision. The original blocked artifact is replayed from the earliest affected stage. Successful replay must use the normal composer/resolver and produce structural closure.

Promotion requires lineage-aware competency tests, context/scope admissibility, provenance, contradiction checks, and atomic activation. Cases generated from the teaching definition validate only well-formedness. Independent discrimination requires an independent oracle, invariant/property test, independently grounded contrast, or adapter observation.

A structurally executable child with incomplete independent validation remains provisional. It may support qualified use in an attributed/private context but not unqualified actual-world inference or an `understands` claim. Failure rolls back or retains the exact partial/provisional artifact and may produce a narrower probe.

### 16.4 Recursive bounds

Learning recursion is bounded by:

```text
maximum nested learning depth
maximum probes per transaction
maximum hypothesis branches
maximum replay count
latency/resource budget
safety and permission policy
```

The system may abstain rather than recurse indefinitely.

## 17. Human-understandable language generation

The response path starts from semantic content, not response templates.

`SemanticMessagePlan` contains:

```text
communicative goals
selected propositions/assessments/outcomes
rhetorical relations
focus and information status
stance and epistemic qualification
required limitations/corrections
provenance refs
language/channel requirements
```

The language renderer performs referring expressions, aggregation, lexicalization, syntax, morphology, and orthography.

The renderer may contain language rules and closed-class lexical resources. It may not invent semantic content or claim outcomes.

## 18. Exact event-driven cognitive loop

Each external signal, tool result, timer, pending-operation completion, or internally scheduled wake event creates a `CognitiveCycle`.

### Phase A — Orient

Pin schema/memory/common-ground/policy revisions; observe clock, component health, channels, resources, permissions, active goals, and learning transactions.

### Phase B — Understand

Perceive surface evidence; compose candidate communicative predications, propositions, contexts, and content predications; ground referents, roles, time, place, and context; consume pending-learning evidence through ordinary semantics; replay eligible checkpoints; select interpretations; integrate into workspace.

### Phase C — Know

Retrieve relevant records; aggregate evidence; apply truth maintenance; derive epistemic and capability assessments; detect concrete gaps; focus the workspace.

### Phase D — Decide

Derive needs and discourse obligations; create desired propositions; appraise and arbitrate goals; generate, simulate, select, and authorize operation plans.

### Phase E — Act and reconcile

Execute authorized operations; collect outcomes; compare predictions and observations; update the execution ledger and proposed mutations.

### Phase F — Critical commit

Validate and commit exact required facts, state transitions, requested writes, outcomes, and learned schemas that the response may claim.

### Phase G — Communicate

Select truthful content using actual assessments, ledger, and commit outcomes; create message plan; realize and dispatch through an available channel.

### Phase H — Output commit and consolidation

Record the actual communication event; update common ground, pending obligations, reliability, prediction error, learning lifecycle, and non-critical indexes; schedule later internal wake events if needed.

## 19. Persistence, concurrency, and replay safety

A cycle uses an immutable `KernelSnapshot`.

Persistent commits use optimistic revision checks. Schema activation and recursive-cluster activation use compare-and-swap against the assessed store/environment fingerprint. Conflicts cause controlled reassessment, not silent overwrite or field-wise merge.

External operation instances carry idempotency keys. Cognitive replay has a deduplication key containing evidence, target sense/revision, checkpoint, context/scope, and dependency fingerprint. Replays are snapshot-pinned, retry-safe, stale-cancellable, and may not execute already-started or dispatched external effects.

The event journal preserves:

```text
input observations
selected interpretations
authorized operations
execution outcomes
mutation sets
commit outcomes
output events
```

Derived indexes and projections may be rebuilt.

## 20. Explainability and traceability

Every public assertion must support a trace:

```text
surface clause
← realization choice
← message-plan content item
← proposition/assessment/outcome
← epistemic result, retrieval result, ledger, or commit outcome
← evidence and semantic objects
← source signal/tool/record
```

Every rejected interpretation, plan, operation, learning hypothesis, mutation, and response candidate remains diagnosable within configured retention.

## 21. Minimum cognitive closure for v3.4 MVP

The MVP is complete only when one authoritative runtime supports all of these vertical slices:

1. nested proposition understanding;
2. user/self profile assertions and exact recall;
3. typed entity/device states and changes;
4. spatial and temporal composition;
5. reported/hypothetical/conditional isolation;
6. basic causal hypotheses without premature effects;
7. content-addressed knowledge and bounded unknownness;
8. live self-capability introspection;
9. goal → operation → ledger → exact commit;
10. recursive lexeme/predicate learning with replay;
11. semantic NLG with provenance;
12. multilingual graph-equivalence for supported language packs.

## 22. Explicit non-goals for the MVP

v3.4 MVP does not require:

- unrestricted autonomous external action;
- human-level commonsense coverage;
- unbounded theorem proving;
- unbounded recursive learning;
- subjective consciousness claims;
- a full affective personality simulation;
- perfect natural-language generation in every language;
- autonomous schema promotion without evidence policy.

These exclusions preserve a buildable cognitive core.

## 23. Foundational reliability invariants

### 23.1 Structural meaning versus epistemic admission

A complete definition can be internally executable without being true in the actual world. Definition closure answers whether the kernel can operate over the schema. Epistemics answers whether a definition claim is supported and in which context.

Example:

```text
“A doctor is someone who owns a red car.”
```

may create a structurally usable user theory. It does not classify actual doctors or override an audited/global schema unless ordinary evidence and promotion policy establish admissibility.

### 23.2 Competence independence

Competence evidence records generation and oracle lineage. A single information lineage cannot independently certify the definition from which its cases were derived.

Structural tests and epistemic confirmation are separate:

```text
well-formedness
role/query behavior
contrast discrimination
independent observation or invariant
factual/evidence admission
```

### 23.3 Derived-cognition invalidation

Every materialized inference, classification, cached answer, plan, response item, capability conclusion, and understanding claim records its supporting schema revisions and assessment fingerprint.

When support changes, truth maintenance retracts or marks stale every dependent artifact. Evidence is preserved. Previously dispatched output becomes historical content and may create a repair obligation; it is never silently rewritten.

### 23.4 Pattern semantics and defaults

Pattern function and strength are orthogonal. Typical/default features do not define identity. Missing evidence does not refute a candidate. Default inference uses four-state truth, specificity, exceptions, scope, and provenance.

### 23.5 Causal warrant

The kernel may natively represent and query `causes`, `enables`, and `prevents`, but individual claims carry a warrant grade:

```text
reported claim
contextual rule
predictive association
mechanism-supported
intervention-supported
```

Stronger planning and intervention require stronger warrant plus live operation authorization.

### 23.6 Correction, revocation, and forgetting

Corrections and retractions target exact evidence/proposition/sense/schema revisions. Support removal propagates through the dependency graph. Archival, permission revocation, and privacy deletion remain distinct operations with policy-specific retention behavior.

### 23.7 Resource and adversarial bounds

Untrusted schema learning is declarative only and bounded by schema-size, dependency-depth, hypothesis, probe, competence, and replay budgets. User input cannot install executable code, override formal kernel invariants, or directly promote global/boot schemas.

