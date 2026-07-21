# CEMM v3.5.1 Grounded Semantic Brain Architecture

**Status:** proposed governing replacement  
**Purpose:** define a grounded, multilingual, recurrent semantic computational architecture in which perception, language, world state, causal inference, learning, action, impact, and response are different operations over one canonical meaning substrate.  
**Primary law:** semantic identity is exact and content-addressed; semantic activation and uncertainty are continuous and recurrent; learned dynamics may rank, predict, and generalize, but may not silently redefine meaning.

---

# 0. Architectural correction

The earlier CSIR proposal fixed an important problem: higher-order schemas must reduce into one canonical semantic representation before reasoning. That is necessary but insufficient.

A semantic brain also needs to explain:

1. how partial lexical and multimodal evidence activates candidate meaning;
2. how a sentence becomes a coherent whole rather than a bag of atoms;
3. how entities expose type-entitled state spaces;
4. how actions and events change the state of role-bound participants;
5. how one state dimension causally affects another without collapsing their meanings;
6. how causal effects recursively propagate through capabilities, structures, goals, and social consequences;
7. how prediction error creates learning frontiers;
8. how learned definitions, causal mechanisms, and continuous parameters become safely authoritative;
9. how response meaning is generated from the resulting world, epistemic, impact, and obligation state;
10. how the system remains neural in computational character without becoming an opaque token predictor.

CEMM v3.5.1 therefore adopts a **dual semantic architecture**:

```text
Exact semantic plane
  content-addressed CSIR graphs
  definitions, roles, scopes, contexts, state dimensions, causal mechanisms
  operational profiles, proofs, authorizations, version closure

Dynamic neural plane
  sparse activation fields over CSIR candidates
  recurrent typed message passing
  grounded state-belief distributions
  predictive and causal parameter fields
  attention/salience, uncertainty, energy, prediction error
```

The exact plane defines what a meaning is. The dynamic plane defines how candidate meanings are activated, integrated, predicted, learned, and selected.

Neither plane replaces the other.

---

# 1. CEMM as a semantic brain

CEMM is a **grounded semantic dynamical network**.

It is not primarily a token sequence model. Its core state is a sparse, typed, recurrent semantic graph coupled to a grounded world-state model.

Its computation resembles a brain in the following architectural sense:

- knowledge is distributed across reusable semantic assemblies rather than stored as sentence handlers;
- activation spreads locally through typed connections;
- bottom-up observations and top-down predictions interact recurrently;
- incompatible interpretations inhibit one another;
- coherent interpretations become stable attractor assemblies;
- prediction error drives parameter and structural learning;
- episodic evidence and reusable semantic knowledge have different consolidation paths;
- state, action, goals, affect, and language share one graph but remain orthogonal dimensions;
- multiple modalities converge on the same referents and semantic state variables;
- response generation is an action over common ground, not next-token continuation.

CEMM is neural-symbolic, but **semantics-first**:

```text
symbolic/exact:
  semantic identity, type contracts, scope, context, role bindings,
  authority closure, causal rule structure, proof, safety and commit

neural/continuous:
  activation, ranking, uncertainty, similarity, predictive parameters,
  causal strengths, salience, confidence calibration and attractor dynamics
```

A continuous model may propose or score a graph. Only an exact CSIR graph with valid authority closure can become executable meaning.

---

# 2. The canonical cognitive state

At cycle time `t`, CEMM's cognitive state is:

```text
CognitiveState_t
  authority_snapshot
  working_csir_graph
  activation_field
  grounded_world_belief
  causal_mechanism_graph
  epistemic_support_graph
  goal_and_value_field
  discourse_common_ground
  learning_frontiers
  proof_and_lineage_graph
```

Formally:

\[
\mathcal C_t = (S_t,G_t,\alpha_t,B_t,\mathcal M_t,E_t,V_t,D_t,F_t,\Pi_t)
\]

where:

- \(S_t\) is the exact authority snapshot;
- \(G_t\) is the current CSIR graph;
- \(\alpha_t\) is the activation field over candidate terms, applications, bindings and hypotheses;
- \(B_t\) is the grounded belief state of referents and state dimensions;
- \(\mathcal M_t\) is the versioned causal/dynamic mechanism graph;
- \(E_t\) is epistemic support and opposition;
- \(V_t\) is goals, values, impact and significance;
- \(D_t\) is discourse and common ground;
- \(F_t\) is the frontier set;
- \(\Pi_t\) is proof, evidence, authority and derivation lineage.

The working graph may be incomplete, ambiguous and contradictory. Durable commits require exact closure, authorization and proof.

---

# 3. Semantic constructors versus computational operations

The architecture must not confuse semantic atoms with the instruction set that manipulates them.

## 3.1 Kernel semantic constructors

The smallest stable semantic constructors are:

```text
TERM
  identity-bearing referent, value, literal, time, interval, context or schema topic

VARIABLE
  typed open term or graph position

APPLICATION
  typed n-ary semantic relation/eventuality/operator with local ports

BINDING
  connection between an application port and a term, variable or application

QUALIFICATION
  context, time, polarity, modality, source, evidence, permission or uncertainty

SCOPE_EMBEDDING
  graph containment and operator/discourse/proposition scope

COORDINATION
  typed conjunction, disjunction, sequence, collection or alternative

PROOF_LINK
  exact derivation, evidence, authority and dependency connection
```

Everything else must be definable as a graph over these constructors or justified through a Kernel Semantic ABI migration.

## 3.2 Semantic machine operations

The semantic machine executes a bounded algebra:

```text
INSTANTIATE     create a typed term/application from exact authority
BIND            attach a filler to a port
UNIFY           solve equality and compatibility constraints
COMPOSE         merge compatible graph fragments
QUALIFY         add context/time/polarity/modality/evidence
EMBED           place a graph under proposition, scope, world or discourse structure
PROJECT         expose selected terms/subgraphs for query or response
MATCH           find graph homomorphisms/substitutions
COMPARE         evaluate equality, ordering, distance or change under a dimension contract
REWRITE         apply proof-bearing graph deltas
PROPAGATE       send typed activation/evidence messages
INTEGRATE       combine dependent evidence without double counting
NORMALIZE       produce canonical semantic normal form
ABSTRACT        recognize a reusable higher-order definition conservatively
AUTHORIZE       validate exact definition/profile/use/scope authority
SIMULATE        preview causal/state consequences without durable mutation
COMMIT          apply a CAS-protected graph patch
INVALIDATE      retract derived authority after dependency change
CONSOLIDATE     compress repeated structure into reusable definitions/parameters
```

These are operations of the semantic computer, not named world concepts.

---

# 4. CSIR as the exact semantic substrate

CSIR is a finite typed attributed hypergraph.

Every executable semantic application pins:

```text
definition_hash
semantic_abi_version
operational_profile_hash where required
use_authorization_hash
context and time qualifications
proof and evidence lineage
```

CSIR represents both lower- and higher-order meaning, but higher-order definitions compile to the same substrate.

Examples:

```text
property(holder, value)
state(holder, dimension, value, interval)
event(participant bindings, temporal profile)
query(variable, restriction graph, projection)
claim(claimant, proposition, audience, commitment)
capability(holder, action, dependency state)
impact(source delta, stakeholder, goal-relative evaluation)
response_act(speaker, audience, semantic target, social commitment)
```

These may use specialized operational profiles while retaining reducible semantic definitions.

---

# 5. Authority architecture

CEMM uses eight orthogonal authority planes.

## 5.1 Kernel Semantic ABI

Defines the machine semantics of the kernel constructors and graph operations.

## 5.2 Semantic Definition Authority

Immutable content-addressed graph definitions for types, relations, states, eventualities, operators, discourse structures and learned concepts.

## 5.3 Operational Profile Authority

Validation, lifecycle, indexing, transition, query, execution and persistence behavior for closed meanings.

## 5.4 Semantic Dynamics Parameter Authority

Versioned continuous parameters used by:

- typed message-passing functions;
- observation likelihoods;
- priors and salience;
- causal mechanism strengths;
- state estimators;
- calibration curves;
- learned similarity indexes;
- response and question utility models.

These parameters influence activation and prediction. They do not change semantic definitions.

## 5.5 Use Authorization Authority

Per-definition/profile/use/scope/context permission, including provisional and high-risk thresholds.

## 5.6 Language and Multimodal Projection Authority

Lexemes, morphology, constructions, realization, vision/audio/sensor concept projections and calibration contracts.

## 5.7 Instance Knowledge and Evidence Authority

Referents, observations, claims, admitted knowledge, state timelines, event occurrences, goals, discourse and proofs.

## 5.8 Runtime Adapter and Policy Authority

Sensor adapters, operation adapters, channel adapters, safety, privacy, resource and emission policy.

A cycle pins all relevant roots. A neural weight file without an exact authority pin is no more acceptable than a floating schema revision.

---

# 6. Grounded referent state spaces

A referent is not a flat object with arbitrary fields. Its active types entitle it to a product of typed state spaces.

For referent \(r\):

\[
\mathcal Z_r = \prod_{d \in Entitled(r,S)} \mathcal V_d
\]

A dimension may be:

```text
categorical       operational_status, life_status
ordered discrete  severity, charge band
continuous        temperature, mass, speed
vector/manifold   position, orientation, color distribution
relational        ownership, support, containment, connection
set-valued        active roles, installed components
process-valued    ongoing activity or resource flow
probabilistic     uncertain identity, location or state
```

Foundational dimension families include, but are not limited to:

```text
identity and type
geospatial position, topology, containment and orientation
temporal interval, sequence, duration and frequency
physical dimensions: temperature, mass, shape, integrity, pressure, motion
structural dimensions: part-whole, connectivity, dependency, configuration
biological dimensions: life, health, energy, homeostasis
cognitive dimensions: attention, belief, memory availability, intention
affective dimensions: valence, arousal, comfort, mood, emotion episode
social/normative dimensions: role, relationship, permission, obligation
resource dimensions: quantity, availability, capacity, depletion
capability dimensions: affordance, dependency satisfaction, competence, readiness
epistemic dimensions: support, opposition, uncertainty, source reliability
operational dimensions: adapter availability, channel state, runtime health
```

These are not universally active fields. Type/facet entitlement determines applicability.

## 6.1 Cross-dimensional causality is not semantic collapse

Physical temperature does not *become* emotion.

For a living referent, thermal state may causally influence homeostasis, comfort, stress, arousal or mood through type- and context-conditioned mechanisms. For a server, thermal state may affect hardware integrity and processing capability. For a room, temperature may affect habitability but not possess a mood.

Correct representation:

```text
thermal_state(fox) increases
+ fox is a living animal
+ range exceeds comfort threshold
+ exposure duration and context
→ predicted discomfort/stress state
→ possible behavior/capability effects
```

The thermal and affective dimensions remain distinct. Their causal link is explicit, versioned, defeasible and evidence-bearing.

---

# 7. Multimodal grounding

All modalities produce evidence envelopes, not facts.

```text
text
speech and prosody
vision and tracking
location sensors
temperature and environmental sensors
system telemetry
operation results
human teaching
```

A modality adapter emits:

```text
observed signal
candidate referent/track links
candidate dimension/value likelihoods
spatial and temporal extent
calibration authority
source, permission and lineage
```

For modality \(m\):

\[
p(o_t^m \mid z_{r,d,t},\kappa_m)
\]

is an observation model pinned by calibration authority \(\kappa_m\).

Multiple modalities update the same grounded state variable only after identity, context and time alignment. Text saying “the box is hot,” a thermal camera reading, and a temperature probe may support the same thermal-state proposition while remaining independently attributable evidence.

Language does not receive privileged world-truth status.

---

# 8. Meaning as a recurrent attractor

A sentence or multimodal episode is not interpreted by independently decoding each word and concatenating outputs.

Each contribution activates candidate CSIR fragments. Candidate fragments exchange typed messages through:

```text
port compatibility
type entitlement
reference/coreference
scope
time and aspect
context/world
causal expectations
state plausibility
discourse continuity
construction constraints
multimodal alignment
```

Bottom-up evidence activates candidate assemblies. Higher-order candidate definitions send top-down predictions about missing roles, expected types, state dimensions and scopes.

The network recurrently relaxes until it reaches:

- one or more stable semantic-equivalence classes;
- a partial stable graph with open variables/frontiers;
- a contradiction set;
- or budget-limited incompleteness.

Hard semantic constraints clamp impossible states. Continuous activation never overrides an exact type, scope, context or authorization violation.

This is the core neural character of CEMM.

---

# 9. Higher-order grammatical meaning

Language packages map grammatical evidence into graph constraints rather than world-specific outputs.

## 9.1 Nominal expressions

May contribute:

- referent introduction or retrieval;
- type restrictions;
- quantity/determination;
- identity and discourse status;
- relational or event nominalization.

## 9.2 Predicates and action words

May activate:

- state/property/relation applications;
- process/event/action definitions;
- participant-role frames;
- expected transitions;
- aspectual alternatives.

A verb does not directly mutate state.

## 9.3 Grammatical subject and object

Subject/object are language relations and evidence for semantic roles. Effects are controlled by the selected semantic role bindings.

```text
John pushed the box.
```

The subject may support `agent=John`; the object may support `affected/theme=box`. The action transition targets the affected role, not “the object” as a universal rule.

Passive, ergative, causative, applicative and topic-prominent languages must reach the same role graph through different grammar.

## 9.4 Modifiers

Adjectives/adverbs may constrain:

- state/value;
- type/classification;
- scalar degree;
- manner;
- duration/frequency;
- result;
- epistemic or discourse stance.

They are not semantic ontology classes.

## 9.5 Tense, aspect and modality

These qualify the event/state/proposition graph and determine temporal/world placement. They do not directly authorize actual-world state change.

---

# 10. Actions, events and role-sensitive transition programs

An action/event definition contains participant roles and may reference one or more causal transition mechanisms.

A transition mechanism is a role-bound state transformer:

\[
T_a : (\mathbf z_{P,t},c,t) \rightarrow
P(\Delta \mathbf z_P, E_{secondary} \mid \mathbf z_{P,t},c,t)
\]

where \(P\) is the set of bound participants.

Effects target semantic roles and dimensions:

```text
affected.temperature += delta
moved_entity.position := destination
container.contains -= content
recipient.possession += transferred_item
server.processing_capability := blocked
speaker.commitment += proposition
```

Each effect requires:

- exact action/event definition closure;
- exact role bindings;
- exact dimension and value-domain authority;
- context and time;
- preconditions and defeaters;
- warrant and confidence;
- transition authorization.

No event-name Python branch is permitted.

---

# 11. Recursive causal propagation

Causal reasoning operates in layers.

## 11.1 Direct mechanism

The event directly changes one or more participant dimensions.

## 11.2 Dependency propagation

Changed dimensions alter dependent states or capabilities.

## 11.3 Secondary event generation

A state threshold may instantiate a secondary event candidate.

## 11.4 Goal and impact propagation

Changes affect stakeholder goals, resources, relationships, risks and obligations.

## 11.5 Discourse and response propagation

New epistemic/impact state creates response obligations or learning questions.

Propagation is recursive but bounded, cycle-detected and proof-bearing.

A causal path is retained as a graph:

```text
source observation/event
→ admitted occurrence
→ mechanism
→ direct delta
→ dependency delta
→ secondary event
→ impact/goal consequence
→ response obligation
```

The system can therefore answer `why`, `how`, `what changed`, `what will happen`, and counterfactual questions from the same proof graph.

---

# 12. Structural causal world model

CEMM represents causal mechanisms separately from mere correlations.

For semantic state variable \(X_i\):

\[
X_i(t+1) := f_i(Pa_i(t),A_t,C_t,U_i;\theta_i)
\]

where:

- \(Pa_i\) are semantic parent variables;
- \(A_t\) is action/event intervention;
- \(C_t\) is context;
- \(U_i\) is unobserved disturbance;
- \(\theta_i\) is versioned parameter authority.

The system supports:

```text
observation        condition on evidence
prediction         propagate current belief forward
intervention       do(action/event)
counterfactual     compare factual and intervened worlds
explanation        return minimal warranted causal path
```

Temporal sequence alone is not causal authority. Learned causal edges require classified warrants and competence.

---

# 13. Inference families

Inference is not one generic rule engine. CEMM supports typed families over CSIR:

```text
deductive/type closure
constraint propagation
relational and graph query
spatial/topological reasoning
temporal interval reasoning
quantitative and ordered-dimension reasoning
causal prediction and intervention
default/non-monotonic reasoning
paraconsistent epistemic reasoning
abductive explanation
analogical candidate proposal
planning and means-end reasoning
social/normative reasoning
impact and stakeholder reasoning
```

Every inference result records:

- inference family;
- exact premises and authority closure;
- rule/mechanism and parameters;
- context/time;
- proof or approximation trace;
- confidence and uncertainty;
- use authorization.

Analogy and similarity may propose candidates. They cannot independently authorize high-risk conclusions.

---

# 14. Recursive learning

Learning is continuous across perception, meaning, state, causality, action and response.

## 14.1 Prediction-error frontier

For predicted observation/state \(\hat o_t,\hat z_t\):

\[
\epsilon_t = (o_t-\hat o_t, z_t-\hat z_t)
\]

The system classifies error as a possible failure of:

```text
grounding or identity
observation calibration
definition or lexicalization
role binding or construction
state dimension/value model
causal structure
causal parameter
context/time placement
default expectation
capability dependency
goal/impact model
response competence
```

## 14.2 Continuous parameter learning

Observation likelihoods, message weights, causal strengths and priors may update through Bayesian or gradient-based learning under pinned model architecture and replayable evidence.

## 14.3 Discrete semantic learning

New concepts, state dimensions, roles, causal mechanisms and constructions are candidate graph definitions. They require closure, independent competence, counterexamples and per-use promotion.

## 14.4 Structure learning

Repeated role-bound pre/post patterns can propose a causal mechanism. Structure selection uses intervention evidence where available, temporal precedence, confounder checks, counterexamples and compression gain.

## 14.5 Semantic consolidation

Repeated equivalent subgraphs may be abstracted into a reusable definition only when abstraction is conservative:

```text
expanded definition meaning == observed canonical subgraph class
```

Compression never replaces proof lineage or turns a phrase into ontology.

---

# 15. Capability, physical structure and embodied consequences

Capability is derived from:

```text
affordance
dependency satisfaction
resource state
structural integrity
current context
adapter availability
competence
```

A physical or structural state change can therefore alter capability through dependencies.

Examples:

```text
server temperature too high
→ cooling dependency violated
→ processing capability degraded/blocked

animal leg injured
→ structural/motor dependency degraded
→ locomotion capability reduced

battery charge reaches zero
→ energy dependency violated
→ powered actions unavailable
```

The event does not directly delete capability. The dependency graph derives the change and preserves historical capability.

---

# 16. Impact, affect and significance

Impact compares before/after state relative to stakeholders and goals.

```text
state delta
+ stakeholder relation
+ goal/resource dependency
+ magnitude, duration, reversibility and risk
→ impact vector
```

Affective inference is grounded in explicit affective evidence or causal mechanisms over biological/cognitive/social state. It is not inferred from keywords alone.

CEMM distinguishes:

```text
physical state of an entity
predicted affective consequence for a living experiencer
user emotional evidence
system social response stance
```

A sympathetic response does not assert that the system experiences human grief.

---

# 17. Response generation as semantic action

A response is an intended change to discourse/common ground.

The system first derives semantic obligations:

```text
answer an open query
report a relevant state or event
qualify source/uncertainty
clarify a missing binding
warn about predicted risk
acknowledge a target-bearing claim
provide causal explanation
propose an authorized action
teach or request learning evidence
remain silent for an explicit reason
```

It then constructs candidate Response CSIR graphs and selects among them under:

- truth and proof preservation;
- query coverage;
- relevance and information gain;
- stakeholder impact and social appropriateness;
- permission, safety and privacy;
- operation freshness;
- target-language realizability;
- cost and interaction burden.

Language realization is the final projection. It cannot add unsupported emotion, causality, certainty or relationships.

---

# 18. Worked semantic-brain examples

## 18.1 “John pushed the box off the table.”

Language analysis proposes:

```text
eventuality: push
agent: John
affected/theme: box
source/support: table
result/path: off(table)
past/completed evidence
```

Multimodal grounding may align John, box and table with visual tracks.

The selected action mechanism predicts:

```text
box support_relation(table) terminates
box geospatial position changes
box velocity may become non-zero
John contact/effort event occurs
```

Secondary mechanisms may predict collision or structural damage only if trajectory, environment and impact evidence support them.

The grammatical object is not mutated because it is an object; the role-bound affected entity is transformed.

## 18.2 “The heater warmed the fox, so it relaxed.”

Direct event:

```text
heater = causer/instrument
fox = affected
fox thermal state increases
```

Type-conditioned causal model:

```text
if fox thermal state moves toward comfort range
and exposure is safe
then comfort increases
and relaxation probability increases
```

If temperature exceeds a stress threshold, the same thermal increase can instead predict distress, harm or escape behavior. Context and individual state matter.

`temperature` and `relaxation` remain distinct dimensions connected by an explicit mechanism.

## 18.3 “The server overheated and stopped processing requests.”

```text
server thermal state exceeds limit
→ cooling/thermal dependency fails
→ processing capability becomes blocked
→ request operations fail or queue
→ service impact and warning goal generated
```

The architecture can answer:

- what happened;
- why processing stopped;
- which capability is affected;
- whether cooling restoration could recover it;
- what evidence supports the conclusion.

---

# 19. Versioning and historical meaning

An executable meaning pins:

```text
Kernel Semantic ABI root
CSIR/normalizer ABI root
semantic definition closure root
operational profile root
semantic-dynamics parameter root
use authorization root
language/multimodal authority root
causal mechanism root
policy and adapter roots
competence/calibration roots
```

A top-level schema revision is insufficient.

Changing a parent definition, state domain, causal parameter set, observation calibration, message-passing model or operational profile creates a new authority closure. Historical decisions retain their original closure.

Neural parameters are immutable artifacts once promoted. Learning creates a new parameter revision rather than silently mutating the model used to justify prior decisions.

---

# 20. Core invariants

1. No higher-order concept executes before exact CSIR compilation.
2. No continuous activation or embedding can override a hard semantic constraint.
3. No grammatical subject/object rule directly determines world-state effects.
4. Effects target semantic roles and typed dimensions.
5. Cross-dimensional influence requires an explicit causal mechanism.
6. Correlation does not become causal authority without classified evidence.
7. Multimodal observations remain source-attributed and calibration-pinned.
8. Claims do not become actual-world state without epistemic admission.
9. Simulation does not become durable state without commit authorization.
10. Capability changes derive from dependency state, not event-name branches.
11. Recursive propagation is bounded, cycle-detected and proof-bearing.
12. Continuous parameter learning and discrete semantic learning have separate promotion gates.
13. Response generation operates on semantic obligations and grounded effects, not predicates or phrases.
14. Every durable result can be reconstructed from exact authority, evidence and pre-state.
15. Budget exhaustion produces incompleteness, not fabricated certainty.

---

# 21. Final architectural statement

The final CEMM computational architecture is:

\[
\boxed{
\text{Content-addressed semantic algebra}
+
\text{typed recurrent activation network}
+
\text{grounded multimodal state estimator}
+
\text{structural causal world model}
+
\text{proof-bearing learning and action}
}
\]

CSIR is the exact language of thought. The activation field is the neural dynamics. The grounded state space is the embodied world model. The causal mechanism graph is the predictive/action model. Versioned proof and authorization keep the system trustworthy.
