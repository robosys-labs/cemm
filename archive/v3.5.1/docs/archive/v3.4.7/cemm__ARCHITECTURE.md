# CEMM v3.4.7 Canonical Architecture

**Status:** replacement architecture contract  
**Target:** a working, teachable, multilingual “baby CEMM” that says only what it can semantically justify  
**Replaces:** fragmented v3.4.x architecture descriptions, sentence-construction authority, and legacy ERCA runtime authority claims  
**Primary law:** analyzers provide reversible evidence; the CEMM semantic kernel alone constructs, grounds, selects, learns, and authorizes meaning.

---

## 1. The breakthrough v3.4.7 must achieve

CEMM must stop being a recognizer that succeeds when a sentence resembles a previously encoded construction. It must become a small semantic processor that can build meaning from grounded parts.

A successful v3.4.7 runtime must be able to receive an unfamiliar utterance, build several plausible structural analyses, identify what the words or multimodal signals might refer to, activate compatible predicate schemas, bind their typed operational ports, assemble several possible UOL meanings, select a jointly coherent meaning bundle, and either act, answer, acknowledge, learn, or ask a precise question.

The target is not unrestricted human-level language understanding. The target is a bounded system with a small but real semantic substrate that:

- understands combinations it was not explicitly given as whole sentences;
- preserves ambiguity instead of collapsing early;
- supports multiple languages through shared meaning rather than shared word order;
- grounds every learned item in already known referents or typed unresolved dependencies;
- distinguishes strict implication, causation, defaults, typicality, and mere association;
- can recursively expand a learning frontier under hard resource limits;
- can explain why it selected a meaning or response;
- refuses to assert a clause that has no authorized semantic proof.

This is the minimum meaningful breakthrough. Anything less is another compatibility layer over the existing matcher.

---

## 2. Canonical single term: Referent

### 2.1 Definition

**Referent** is the single canonical term for every identity-bearing thing that CEMM can point to, track, compare, bind to a predicate port, mention, remember, query, or reason about.

The following are all referents:

- self and other agents;
- people, animals, organizations, physical and digital objects;
- places and regions;
- events, actions, and processes;
- propositions;
- states;
- quantities;
- units;
- times and intervals;
- collections;
- contexts or possible worlds;
- information objects;
- schema concepts when a schema itself is being discussed.

They are not flattened into one indistinguishable class. They share the record family `Referent`, and are distinguished by `ReferentKind`, type schemas, identity criteria, and specialized canonical payloads.

### 2.2 Why `Referent`

`Entity` is too narrow because propositions, states, quantities, units, and time are not ordinary entities. `Object` suggests physical objects. `Node` is a storage representation rather than a semantic category. `Atom` incorrectly implies indivisibility. A referent is exactly what a mention, gesture, variable, role binding, memory record, or response expression can refer to.

### 2.3 Referent versus schema

A referent is an instance or identity-bearing object in a semantic world. A schema defines how a class of referents, predicates, operations, or expressions behaves.

When the user says “a president is elected,” the word *president* can evoke a role schema. If that role schema is itself the topic of discussion, CEMM creates or resolves a `SCHEMA`-kind referent that points to the executable schema revision. The referent does not replace the schema authority.

### 2.4 Referent kinds

The minimum seed `ReferentKind` lattice is:

```text
REFERENT
├── SELF
├── AGENT
│   ├── PERSON
│   ├── ANIMAL
│   ├── ORGANIZATION
│   └── SOFTWARE_AGENT
├── PHYSICAL_OBJECT
├── DIGITAL_OBJECT
├── PLACE
├── EVENT
│   ├── ACTION
│   └── PROCESS
├── STATE
├── PROPOSITION
├── QUANTITY
├── UNIT
├── TIME
│   ├── INSTANT
│   └── INTERVAL
├── COLLECTION
├── INFORMATION_OBJECT
├── CONTEXT
└── SCHEMA
```

Domain concepts are learned beneath or across these foundations. `president`, for example, is normally a social/institutional role schema, not a child kind of `PERSON`. `mother-in-law` is a relationship schema, not a biological entity kind.

### 2.5 Referent identity

Every referent has:

```text
referent_id
referent_kind
active_type_schema_refs
identity_keys
anchor_refs
scope
context_refs
valid_time
provenance_refs
permission
status
confidence
```

Specialized referents add canonical identity payloads:

- `QuantityReferent`: normalized magnitude, uncertainty, and unit referent;
- `UnitReferent`: measurement dimension, scale, and conversion schema refs;
- `TimeReferent`: normalized instant, interval, recurrence, and granularity;
- `PlaceReferent`: identity/geospatial anchor refs and reference frame;
- `PropositionReferent`: defining predication refs, context, polarity, modality, attribution, and valid time;
- `StateReferent`: defining state-predication ref plus state identity and temporal anchor;
- `EventReferent`: defining event-predication refs plus event identity and temporal anchor;
- `ContextReferent`: world/context identity, parent context, and accessibility relation refs.

Canonical payload fields establish identity and normalization only. Event participants, state holder/dimension/value, spatial relations, and other semantic claims remain in predications and KnowledgeRecords. A reified event or state therefore points to its defining UOL content rather than duplicating that content in a second authoritative payload.

---

## 3. The four architectural record layers

CEMM has four record layers. They are related, but none may substitute for another.

### 3.1 Evidence records

Evidence records preserve observations and analyzer proposals.

```text
ObservationEnvelope
EvidenceAtom
LanguageHypothesis
FormSpanCandidate
StructureRelationCandidate
MentionCandidate
OperatorCue
FormLattice
```

Evidence can be text, audio, visual, gesture, sensor, tool, database, or memory retrieval evidence. Evidence is reversible and source-aligned. It is not truth and not selected meaning.

### 3.2 UOL semantic records

UOL is the Universal Operational Language used inside the kernel. It is not a word list, JSON vocabulary, parse tree, or durable database dump.

```text
Referent
Predication
OperationalPortBinding
PropositionReferent
UOLGraph
MeaningHypothesis
MeaningBundle
DiscourseRelation
```

A cycle-local `UOLGraph` is the temporary semantic workbench. It contains multiple competing referent resolutions, predications, propositions, and discourse structures. Only the selected `MeaningBundle` may feed knowledge, goals, operations, learning, or response planning.

### 3.3 Executable schema records

Schemas define possible meaning and operations.

```text
ReferentKindSchema
PredicateSchema
PortSchema
StateDimensionSchema
UnitSchema
TimeSchema
RelationshipSchema
RoleSchema
EventPatternSchema
OperationSchema
RuleSchema
RelationAlgebraSchema
LexemeSenseSchema
FormPatternSchema
RealizationSchema
PolicySchema
```

`SemanticSchemaStore` is the sole lifecycle authority for executable schema revisions.

### 3.4 Cognitive-control records

Control records decide how semantic content is used.

```text
GroundingAssessment
SchemaActivation
SelectionAssessment
EpistemicAssessment
KnowledgeRecord
GapRecord
LearningTransaction
GraphPatch
GoalRecord
OperationPlan
AuthorizationRecord
ResponseGoalCandidate
UOLResponsePlan
EmissionProof
```

A score, gap, goal, plan, or learning transaction is never a second semantic ontology.

---

## 4. UOL: the canonical semantic workbench

### 4.1 Predication

A `Predication` is an instance of an active `PredicateSchema` with local typed ports.

```text
Predication
  predicate_schema_ref
  port_bindings
  open_ports
  source_evidence_refs
  confidence
  assumptions
```

All filled ports bind to referents. There is no separate universal `Value` filler family; text values, booleans, numbers, quantities, units, and times are represented by appropriate referents.

### 4.2 Proposition referent

A predication becomes truth-evaluable only through a `PROPOSITION` referent:

```text
PropositionReferent
  content_predication_refs
  context_ref
  polarity
  modality
  attribution_ref
  valid_time_ref
  epistemic_qualification
```

Communicative force is not proposition polarity or modality. Asking, asserting, requesting, correcting, acknowledging, promising, refusing, and teaching are discourse acts over proposition or operation content.

### 4.3 UOL graph

`UOLGraph` contains:

- referent candidates and co-reference alternatives;
- predication candidates;
- proposition candidates;
- clause and discourse relations;
- scope relations;
- coordination groups;
- open operational ports;
- assumptions and coercions;
- unresolved evidence spans;
- provenance and score factors.

The graph is temporary. It must not be dumped into long-term memory as “what was understood.” Durable changes require an explicit `GraphPatch`.

### 4.4 Meaning hypothesis and bundle

A `MeaningHypothesis` is one internally coherent candidate interpretation of a clause, fragment, gesture, or multimodal unit.

A `MeaningBundle` is a compatible set of hypotheses selected for the whole turn. It may contain multiple propositions, such as:

```text
“My name is Chibueze and I am 34.”

named(user, Chibueze)
has_state(user, age, 34 years, now)
coordination(named-proposition, age-proposition)
```

Selection is not “choose the one top proposition.” It is constrained set selection across the entire utterance and active context.

### 4.5 GraphPatch

`GraphPatch` is the only route from temporary UOL cognition to durable semantic change.

A patch can propose:

- creation or resolution of a referent;
- a knowledge proposition;
- a state update;
- an alias or lexicalization;
- a schema revision;
- a rule or relation-algebra revision;
- a correction, supersession, or retraction;
- a discourse/common-ground update.

Every patch includes exact source evidence, affected records, expected revisions, scope, permission, confidence, epistemic status, validation requirements, and rollback information.

No operator may write raw analyzer output, raw text, or an unselected UOL candidate directly to durable stores.

---

## 5. Authority laws

### 5.1 One meaning authority

Language analyzers, construction matchers, NER models, parsers, embeddings, LLMs, databases, vision models, and multimodal trackers may propose evidence. Only `MeaningAssembler` and `MeaningBundleSelector`, operating over active schemas and pinned stores, may authorize selected UOL meaning.

### 5.2 Predicate-owned ports

Ports belong locally to a `PredicateSchema` or `OperationSchema`.

A port schema contains:

```text
port_id                     # e.g. named.holder
role_family                 # optional reusable semantic family
accepted_referent_kinds
accepted_type_schema_refs
cardinality
requiredness
queryability
allows_open
allows_embedded_proposition
context_propagation
valid_time_propagation
identity_contribution
binding_constraints
coercion_policy
```

There is no global actor/object/target role list that engines may assume. Reusable role families help cross-schema comparison, but the owning predicate defines exact semantics.

An `OperationalPort` is the cycle-local projection of a port schema with candidate fillers, constraints, and binding scores.

### 5.3 Role schemas are not predicate ports

CEMM uses two concepts that older designs often collapsed:

- `PortSchema` is a local argument position owned by a predicate or operation, such as `named.holder` or `move.destination`.
- `RoleSchema` is a semantic world concept such as president, spouse, teacher, operator, or beneficiary that a referent may occupy in a context and time interval.

A role may be represented through predicates such as `occupies_role`, but it is not an argument slot. Never use a social/institutional role schema as the mechanism for binding predicate arguments, and never turn a local port name into a world referent.

### 5.4 Language independence

Language independence means kernel independence, not analyzer uniformity.

Language modules may be language-specific and may contain:

- morphology and lemmatization rules;
- tokenization and clitic decomposition;
- dependency or constituency models;
- lexical entries and idioms;
- agreement, classifier, case, and word-order knowledge;
- discourse particles and language-specific realization paradigms.

They may not:

- create final predications or selected propositions;
- force a semantic predicate because a whole sentence matched;
- write knowledge or learned schemas;
- choose an answer;
- emit unplanned response meaning.

The kernel may not inspect English words, English word order, or language-pack construction identifiers.

### 5.5 Evidence is not truth

An utterance is evidence that a source performed a discourse act. Its content can support an actual, reported, believed, desired, hypothetical, quoted, or simulated proposition depending on context and epistemic policy.

Structural completeness does not automatically admit an actual-world fact.

### 5.6 No silent coercion

Type conversion, omitted-role recovery, ellipsis completion, metaphorical extension, and default reference resolution must be explicit candidate assumptions. They contribute penalties and remain in the trace.

### 5.7 No unproved output

Every emitted semantic clause requires:

- an active predicate or approved mention/quotation use;
- all required non-query ports filled;
- grounded referents or explicitly mentioned unresolved forms;
- epistemic authorization for the requested use mode;
- response-goal provenance;
- a realization proof covering every semantic contribution.

When proof is absent, CEMM must select a repair response or emit no semantic output. It may never fill the gap with a canned confident sentence.

---

## 6. Observation and form analysis

### 6.1 Observation envelope

Every turn begins as an `ObservationEnvelope` containing:

- observation ID and timestamp;
- source and addressee candidates;
- session/context ID;
- modality and channel;
- raw payload reference;
- permission and retention policy;
- prior observation links;
- optional language or sensor hints.

Text is one modality. Audio can contribute speaker, prosody, timing, and transcript alternatives. Vision can contribute referent tracks, locations, gestures, and states. Tool results can contribute structured evidence.

### 6.2 Language detection

Language detection produces N-best `LanguageHypothesis` records at utterance and span level. Explicit user choice and stable session preference are priors, not irreversible overrides.

Code-switching is represented by overlapping span-language candidates. More than one analyzer may run when confidence is low or segmentation differs.

### 6.3 Form lattice

The language-analysis coordinator creates a `FormLattice`, the instant virtual map of possible utterance forms.

It preserves alternatives for:

- tokens and morphemes;
- lexical senses;
- multiword expressions;
- named mentions;
- quantities, units, and time expressions;
- clause and sentence boundaries;
- coordination and conjunction scope;
- subordination;
- relative-clause attachment;
- complements and quotations;
- negation and modality scope;
- question and directive cues;
- dependency/constituency relations;
- ellipsis and omitted arguments;
- discourse markers;
- unresolved spans.

No single parser output is assumed correct. Analyzer results are fused as correlated evidence, not naively counted as independent votes.

### 6.4 Construction evidence

Declarative constructions remain useful for:

- closed grammatical patterns;
- idioms whose meaning is not compositionally recoverable;
- language-specific argument realization;
- high-confidence structural evidence;
- realization templates.

They are renamed conceptually to `FormPatternEvidenceProvider`. A match contributes evidence edges and optional predicate priors. It cannot directly instantiate selected predications.

### 6.5 NER and database analysis

NER is expanded into mention analysis. A `MentionCandidate` may denote any referent kind, not only named people, organizations, and locations.

Mention candidates are cross-referenced against:

- alias and lexical indexes;
- known referent registry;
- place/geospatial index;
- event and temporal index;
- knowledge store;
- session discourse model;
- multimodal referent tracks;
- user/private scoped stores;
- learned schema lexicons.

The result is an N-best grounding lattice. A database hit is a candidate anchor, never final identity by itself.

---

## 7. Referent grounding and session context

### 7.1 Grounding targets

Grounding resolves mentions, pronouns, relative pronouns, deictics, omitted arguments, gestures, and repeated keywords to referent candidates.

The same resolver handles:

- `he`, `she`, `it`, `they`, and language-specific pronouns;
- `that` referring to an object, event, proposition, state, or prior output;
- `there` referring to a place or visual region;
- `then` referring to a time or event sequence;
- names and aliases;
- descriptions such as “the president”;
- relative pronouns such as “who” and “which”;
- zero anaphora in pro-drop languages;
- multimodal references such as “put it there” with gaze or gesture.

### 7.2 Referent candidate score

Grounding score uses named components:

```text
identity_anchor_support
lexical_alias_support
type_compatibility
predicate_port_compatibility
discourse_salience
recency
speaker/addressee fit
topic continuity
syntactic/structural fit
geospatial/temporal fit
multimodal track fit
world-model consistency
scope/permission availability
assumption penalty
contradiction penalty
```

No component may erase explicit incompatible evidence. A high-frequency referent cannot win a port whose type it cannot fill.

### 7.3 Discourse model

The `DiscourseModel` is a bounded semantic projection containing:

- active referents and mention chains;
- focus stack and topic stack;
- recent selected propositions;
- open questions and requested information ports;
- pending learning frontiers;
- pending operations and commitments;
- corrections and contrasts;
- common-ground status;
- response repetition history;
- language and tone preferences.

It is richer than a flat transcript or predicate counter and is not a truth store.

### 7.4 Session world model

`SessionWorldModel` tracks the current multimodal situation:

- referent tracks across observations;
- uncertain identity merges and splits;
- visible/audible presence;
- location and spatial relations;
- observed states;
- operation-relevant affordances;
- current time and temporal anchors;
- self state and capability state;
- observation freshness.

Tracked state guides interpretation and action planning. It is admitted to durable knowledge only through epistemic assessment and a GraphPatch.

---

## 8. Schema activation and semantic composition

### 8.1 Candidate predicate activation

The kernel activates predicate schemas from several independent evidence sources:

- lexical-sense candidates;
- structural relations;
- morphological marking;
- recognized referent kinds and types;
- learned form patterns;
- active topic and open-question expectations;
- operation or dialogue obligations;
- multimodal relations;
- bounded semantic retrieval.

The system does not require an exact sentence construction to name the predicate.

### 8.2 Port projection

For every activated predicate schema, the kernel projects operational ports and gathers candidate fillers from:

- referent candidates associated with the clause;
- embedded proposition candidates;
- event/state candidates;
- discourse context;
- implicit speaker/addressee/self roles licensed by the language evidence;
- ellipsis candidates;
- query-open ports;
- multimodal tracks.

### 8.3 Binding solver

The binding solver builds candidate predications through bounded constraint propagation.

Hard constraints include:

- accepted referent kinds and type schemas;
- cardinality;
- required versus query-open ports;
- explicit agreement/case constraints where provided by analyzers;
- negation and scope compatibility;
- context and valid-time compatibility;
- identity and anti-reflexivity constraints;
- relation-algebra restrictions;
- permission and accessibility.

Soft factors include:

- structural attachment confidence;
- lexical evidence;
- port plausibility;
- discourse salience;
- typicality;
- world-model state;
- minimal assumptions;
- coverage.

### 8.4 Clause and discourse assembly

Composition must support:

- multiple predicates in one clause;
- coordinated clauses and shared arguments;
- relative clauses;
- complement clauses;
- reported and quoted content;
- conditionals;
- causal and explanatory relations;
- corrections and contrast;
- ellipsis;
- questions with open ports;
- directives whose content denotes an operation or desired state.

Clause boundaries are candidate structures, not irreversible punctuation splits.

### 8.5 Meaning scoring

A hypothesis score is a calibrated composition of named factors, preferably in log space:

```text
+ evidence coverage
+ source reliability
+ structural coherence
+ predicate activation support
+ port binding compatibility
+ referent grounding support
+ discourse coherence
+ temporal/geospatial coherence
+ multimodal state coherence
+ schema competence
+ epistemic usability for interpretation
- unresolved required ports
- unexplained evidence
- unsupported coercions
- contradictory bindings
- duplicate/overlapping claims
- excessive complexity
```

Plausibility may rank otherwise compatible candidates. It may not invent evidence or turn defaults into facts.

### 8.6 Bounded search

The practical initial implementation uses beam search plus constraint propagation, not unrestricted graph search.

Configurable limits include:

- candidates per evidence span;
- referent candidates per mention;
- activated predicates per clause;
- fillers per port;
- predications per clause beam;
- utterance bundle beam;
- composition depth;
- embedded clause depth;
- wall-clock budget;
- memory budget.

Pruning records the reason. At least one alternative per major ambiguity family should survive when within a configurable margin.

### 8.7 Compatible-bundle selection

The selector chooses a compatible set, not one isolated proposition.

Compatibility includes:

- no contradictory co-reference assignment unless representing explicit uncertainty;
- no incompatible port bindings for the same predication;
- consistent scope and clause segmentation;
- compatible proposition contexts;
- shared-argument consistency across coordination;
- coverage without double-consuming incompatible evidence;
- discourse-act coherence;
- retention of explicitly coordinated meanings.

The output is a `MeaningBundle`, alternatives, and a `SelectionAssessment` with score decomposition and unresolved gaps.

---

## 9. Gaps, understanding, and repair

### 9.1 Understanding is use-relative

CEMM must not treat “understood” as a vague boolean. A selected meaning can support different use profiles:

```text
preserve_surface
mention_or_quote
resolve_reference
compose_partial
ask_targeted_question
retrieve
assert_attributed
assert_actual
infer
plan_operation
execute_operation
realize_response
```

A meaning may be adequate for quotation but not for factual inference, or adequate for a clarification question but not for execution.

### 9.2 Gap taxonomy

Canonical gap classes include:

- `analysis_gap` — form structure unavailable;
- `language_gap` — no competent analyzer/realizer;
- `lexical_gap` — unknown form or sense;
- `reference_gap` — referent unresolved;
- `identity_gap` — candidates cannot be merged or distinguished;
- `port_gap` — required semantic port unfilled;
- `schema_gap` — no executable schema describes the candidate meaning;
- `knowledge_gap` — meaning understood but answer not known;
- `epistemic_gap` — evidence insufficient for requested claim;
- `capability_gap` — requested operation unavailable;
- `permission_gap` — operation or information use not authorized;
- `learning_frontier_gap` — explicit teaching contribution lacks grounding dependencies;
- `realization_gap` — UOL meaning cannot be expressed by the target language pack.

Only some lexical, schema, relation, and learning-frontier gaps are learnable. Reference, knowledge, permission, and capability gaps are not silently converted into schema lessons.

### 9.3 Repair strategy

Repair is selected according to the narrowest blocker:

- resolve from context;
- ask which referent;
- ask for one missing port;
- ask what kind of thing an unknown term denotes;
- ask whether a statement is a strict rule, cause, default, or example;
- disclose lack of knowledge;
- disclose capability or permission limitation;
- request rephrasing only when no more specific repair is possible.

All repair questions are themselves UOL response plans with exact target gap references.

---

## 10. Epistemics and durable knowledge

### 10.1 Knowledge record

Durable knowledge is not a duplicate predicate/role blob. A `KnowledgeRecord` points to a `PROPOSITION` referent and records how it is epistemically held:

```text
knowledge_id
proposition_ref
status: supported | opposed | both | undetermined
admissible_context_refs
confidence
evidence_refs
source_refs
lineage_roots
valid_time
sensitivity
permission
retention
status_revision
```

Current `SemanticFact` records are migrated into proposition referents plus knowledge records.

### 10.2 Four-state truth

CEMM uses open-world four-state assessment:

- supported;
- opposed;
- both supported and opposed;
- neither established.

Absence is not negation. Contradiction is retained and reasoned about rather than overwritten unless a correction/supersession policy applies.

### 10.3 Attribution

Direct user statements remain source-attributed even when admitted to the actual conversational world. Reports, beliefs, quotations, hypotheticals, and simulations keep their distinct context referents.

### 10.4 Commit boundaries

The kernel has separate commit classes:

- evidence retention;
- discourse/common-ground update;
- session world update;
- knowledge patch;
- schema/learning patch;
- operation effect patch;
- output dispatch record.

Irreversible operation effects require live authorization immediately before execution and commit.

---

## 11. Grounded learning

### 11.1 Learning objective

CEMM learns reusable semantic structure, not remembered sentences.

A new lexical form, concept, relationship, event pattern, state dimension, predicate, operation, rule, default, or realization must connect to existing referents and schemas or to explicitly typed frontier items.

### 11.2 Learning contribution types

```text
LEXICAL_ALIAS
REFERENT_IDENTITY
REFERENT_KIND
ROLE_OR_RELATIONSHIP
PREDICATE_AND_PORTS
STATE_DIMENSION
UNIT_OR_CONVERSION
EVENT_PATTERN
PLACE_PATTERN
OPERATION_AFFORDANCE
STRICT_RULE
CONSTITUTIVE_RULE
CAUSAL_RULE
ENABLING_RULE
DEFAULT_RULE
STATISTICAL_ASSOCIATION
EXCEPTION_OR_DEFEATER
REALIZATION_PATTERN
CORRECTION_OR_RETRACTION
```

The classifier preserves uncertainty when several contribution types are plausible.

### 11.3 Grounding frontier

A learning transaction owns a frontier of exact unresolved dependencies. For a newly taught term, the system may need to establish:

- what referent kind or schema family it belongs to;
- identity criteria;
- parent kinds or relationship domain;
- predicate ports;
- accepted filler kinds;
- temporal behavior;
- whether a relation is strict, causal, default, or merely typical;
- exceptions;
- lexical forms in one or more languages;
- realization competence;
- permission and scope.

The system asks the smallest question that reduces the frontier most safely.

### 11.4 Recursive learning loop

Recursive learning is bounded by:

- wall-clock timeout;
- maximum frontier depth;
- maximum new referents and schemas;
- maximum rule firings;
- cycle detection;
- dependency-component classification;
- user-interaction budget;
- sensitivity policy;
- rollback on failed validation.

Unresolved frontier nodes remain explicit. They are not filled with guessed definitions.

### 11.5 President example

A grounded learning decomposition should not encode “president” as merely a synonym or a child entity kind.

A useful learned package may include:

```text
president_role instance_of institutional_role
occupies_role(holder: PERSON_OR_AGENT,
               role: president_role,
               jurisdiction: ORGANIZATION_OR_COUNTRY,
               valid_time: INTERVAL)
role_conferred_by(role_occupancy, election_or_appointment_event)
presides_over(holder, jurisdiction)
tenure_of(role_occupancy, interval)
```

Possible additional claims require correct rule classes:

- “a president is a leader” may be a constitutive or role implication depending on the learned definition;
- “a president is elected” is not universally strict because appointment and other accession mechanisms exist;
- “a president rules a country” is too broad unless jurisdiction and constitutional role are specified;
- “a president usually stays in the capital” is a defeasible default, never an entailed location fact.

The learned schema remains grounded in known `PERSON`, `ROLE`, `ORGANIZATION/COUNTRY`, `EVENT`, `PLACE`, and `TIME` referents and predicates.

### 11.6 Relationship-chain example

The example “mother-in-law implies wife; wife implies co-residence with a woman; wife implies sexual activity” demonstrates why rule classification is essential.

- `mother-in-law` is a kinship relationship schema.
- It may be derivable through a spouse or partner relation, but does not universally imply the spouse is a wife.
- marriage does not strictly imply co-residence;
- marriage does not strictly imply sexual activity;
- sexual-life inference is sensitive and must not be materialized from relationship status by default.

CEMM may preserve a user-taught theory in an attributed/private context, ask for qualifications, or register a defeasible rule with blockers. It must not transform this chain into actual-world facts.

### 11.7 Activation and promotion

New schemas begin in narrow scope:

```text
candidate → provisional → active → superseded/rejected
```

Activation requires:

- structural closure;
- external grounding anchors;
- type and port validation;
- rule-class validation;
- contradiction and cycle analysis;
- competence tests not derived solely from the teaching example;
- scope and permission checks;
- atomic compare-and-swap commit.

Global promotion requires independent evidence or human review. A single conversation can establish a session-private theory but cannot self-certify a universal ontology.

---

## 12. Inference and relationship algebra

### 12.1 Rule classes

The inference engine must preserve these classes:

| Class | Meaning | May materialize actual facts? |
|---|---|---|
| identity/equivalence | same referent or schema identity | only with identity policy |
| constitutive | part of what makes the concept/role what it is | yes when active and grounded |
| strict implication | conclusion necessarily follows in admitted context | yes |
| prerequisite | condition required for an operation/state | as requirement, not causal fact |
| causal | cause produces or contributes to effect | according to warrant and context |
| enabling | condition makes effect possible | no automatic effect claim |
| preventing | condition blocks effect | according to scope |
| default/typical | usually true absent defeater | expectation/qualified answer only by default |
| statistical association | correlated evidence | ranking only unless explicitly queried |
| conversational implicature | pragmatic inference | discourse use only |
| normative | obligation/permission/prohibition | normative context only |

### 12.2 Relation algebra

Predicate schemas can declare:

- inverse relation;
- symmetry;
- reflexivity/irreflexivity;
- transitivity;
- antisymmetry;
- functional or inverse-functional cardinality;
- composition rules;
- exclusivity;
- temporal persistence;
- context inheritance;
- monotonicity;
- defeaters and specificity priority.

Algebra is executable metadata, not a second graph-edge ontology. Derived semantic relations remain predications with proofs.

### 12.3 Bounded inference

Inference uses agenda-driven semi-naive evaluation with:

- delta triggering;
- predicate indexes;
- depth and step limits;
- per-rule and per-signature limits;
- maximum derived referents/propositions;
- wall-clock timeout;
- existential budgets;
- sensitive-rule policy;
- cycle-class handling;
- proof lineage;
- invalidation dependencies.

A timeout yields a partial proof-bearing result and explicit incompleteness, never an implicit success.

### 12.4 Consequence status

Derived results carry:

```text
entailed
constitutive
causally_supported
default_expected
associated
pragmatically_suggested
blocked_sensitive
undetermined
```

Response and action policies decide which statuses can support which use modes.

---

## 13. Goals, actions, and capabilities

### 13.1 Interaction goals

Goals are generated from selected meaning, gaps, obligations, self state, and policy. Candidate goal families include:

- answer a query;
- acknowledge information;
- repair reference;
- repair meaning;
- continue a learning transaction;
- store or correct knowledge;
- satisfy a requested operation;
- refuse or explain limitation;
- maintain discourse coherence;
- ask a useful follow-up;
- remain silent when no authorized contribution exists.

Goal generation is semantic and content-specific. It is not a lookup from speech-act label to canned response type.

### 13.2 Operation planning

An operation plan binds active `OperationSchema` ports to referents and success-condition propositions.

An operation schema defines:

- input/output ports;
- preconditions;
- effects as proposed GraphPatches;
- capability requirements;
- permission requirements;
- resources and costs;
- risk and reversibility;
- idempotency;
- failure modes;
- observation requirements.

A plan with unbound required ports is not executable.

### 13.3 Self model

Self is a stable referent with observed and configured states:

- implementation identity;
- name and description;
- available analyzers and realizers;
- memory access and persistence capabilities;
- current operation capabilities;
- permissions;
- health and availability;
- language preference;
- style/mood state where explicitly modeled.

Self claims must be based on live observations or admitted configuration facts, not hard-coded conversational claims.

---

## 14. Response-goal selection and UOL response planning

### 14.1 Response candidate generation

The response subsystem first generates semantic response-goal candidates, including:

- direct answer from supported knowledge;
- qualified answer from reported/default/uncertain knowledge;
- acknowledgement of accepted information;
- correction acknowledgement;
- targeted clarification;
- learning probe;
- operation confirmation or result;
- capability/permission explanation;
- uncertainty disclosure;
- brief rapport response;
- no-output candidate.

Ranking cannot rescue a response candidate that was never generated, so generation must be schema- and goal-driven rather than special-case branches.

### 14.2 Response score

Response ranking uses:

```text
goal satisfaction
epistemic authorization
semantic relevance
question/operation fit
discourse coherence
specificity
information gain
brevity/cost
social-tone fit
repetition penalty
unresolved-content penalty
risk and permission
realizability
```

The selected set must be mutually compatible. A clarification cannot be selected alongside a contradictory confident answer.

### 14.3 UOL response plan

`UOLResponsePlan` contains:

- target response goals;
- proposition referents to assert, ask, acknowledge, qualify, mention, or quote;
- discourse relations and ordering;
- information structure: topic, focus, contrast, given/new;
- reference plans for every referent;
- certainty and attribution constraints;
- politeness and tone constraints;
- desired language and channel;
- semantic provenance;
- required realization coverage.

It contains no final sentence strings.

### 14.4 Target language

Target language priority is:

1. explicit user instruction;
2. language of the current addressed segment;
3. stable session preference;
4. last successful shared language;
5. configured fallback.

Code-switched output must be an intentional realization policy, not accidental leakage from lexical sources.

### 14.5 Tone and mood

Conversational tone is derived from:

- user tone and politeness evidence;
- relationship/context policy;
- session style preference;
- current self-state referents;
- urgency and risk;
- channel constraints.

Tone can choose wording, formality, brevity, and discourse markers. It cannot change polarity, certainty, attribution, referent identity, or factual content.

### 14.6 Realization

The realizer maps UOL to the target language using:

- realization schemas;
- morphology and agreement;
- language-specific word order;
- referring-expression generation;
- discourse and information structure;
- punctuation and prosody;
- style constraints.

Every semantic contribution receives span coverage. Uncovered semantic content blocks the clause. Surface literals are permitted only for audited grammatical material, names/quoted text, and realization schemas.

---

## 15. Foundation seed package

A baby CEMM cannot be teachable if the foundation is only a few ontology labels. The seed must be small, language-neutral, and operationally complete.

### 15.1 Required seed families

1. **Referent kinds** — the lattice in section 2.4 plus identity criteria.
2. **Identity predicates** — same/different, instance/type, alias, name, refers-to.
3. **Mereology and containment** — part/whole, contains/inside, member/group.
4. **Spatial predicates** — located-at, relative position, distance, direction, reference frame.
5. **Temporal predicates** — before/after/during, starts/ends, valid-at, recurrence.
6. **Event participation** — agent, participant, affected referent, instrument, location, time, result.
7. **State and transition** — state holder, dimension, value, transition, persistence.
8. **Quantity/unit substrate** — numeric magnitude, unit dimensions, conversion, comparison, ranges, uncertainty.
9. **Causal and conditional relations** — causes, enables, prevents, requires, if/then rule forms.
10. **Epistemic relations** — observes, reports, believes, knows, uncertain, evidence-for/against.
11. **Communication/discourse** — asks, asserts, requests, acknowledges, corrects, refers-back, answers, contrasts.
12. **Learning/definition** — means, names, defines, subkind, role definition, predicate-port definition, example, exception.
13. **Goals and operations** — wants, intends, capable, permitted, obligated, operation precondition/effect.
14. **Self model** — self referent, software-agent kind, CEMM name, expansion “Contextual Event Memory Model,” runtime capabilities and limitations.
15. **Response goals** — answer, acknowledge, clarify, learn, act, refuse, qualify, repair, no-output.

### 15.2 Required state dimensions

The initial state package should include at least:

- operational status;
- availability;
- connectivity;
- capability/resource level;
- location;
- life status;
- emotive/social stance where applicable;
- physical size, height, mass;
- age as a time-indexed quantity or derived state;
- storage/memory persistence;
- relationship status only as an explicitly scoped state, not as a source of sensitive entailments.

### 15.3 Required unit and time seed

Seed units must cover time, length, mass, data size, ratio/percentage, and dimensionless counts. Conversions must be schema-driven. Relative time forms such as today, yesterday, tomorrow, now, and dayparts ground to `TIME` referents through the cycle clock and locale.

### 15.4 Language packs

At cutover, at least two typologically different language adapters must pass the same semantic acceptance suite. Each pack contains lexicalizations, morphology, structural evidence rules/models, idioms, and realization data. No language pack may contain transcript-specific full-sentence fixes without an idiom justification.

### 15.5 Foundation admissibility

Foundation neutrality is checked structurally:

- records must belong to approved foundation schema families;
- dependencies must terminate in foundation anchors;
- no product-domain or demo-transcript concept is boot-required;
- examples do not become schemas automatically;
- language surfaces remain outside language-neutral foundations.

A Python blacklist of words such as `president` or `engineer` is itself domain-specific and must not be the neutrality mechanism.

---

## 16. Persistence and indexes

### 16.1 Source format versus runtime store

Reviewed foundation packages and language packs may remain JSON/YAML because they are diffable and versioned. Runtime referents, propositions, knowledge, schema revisions, evidence lineage, discourse records, and graph patches require a durable indexed backend.

### 16.2 Initial backend

SQLite is the practical first backend behind stable interfaces, with later PostgreSQL or distributed implementations possible.

Minimum indexes:

- referent ID, kind, type, alias, identity key, scope, valid time;
- predicate schema and port types;
- proposition predicate/port bindings;
- knowledge status, context, source, validity, sensitivity;
- lexical surface + language + sense;
- place/geospatial anchor;
- event time and participants;
- rule premise predicate;
- dependency and invalidation edges;
- learning transaction/frontier;
- discourse/session recency;
- graph patch and revision.

Stores must support pinned read snapshots, atomic patches, compare-and-swap activation, provenance retention, and reversible supersession.

---

## 17. Component boundaries

```text
ObservationCoordinator
  -> ObservationEnvelope

LanguageDetectionCoordinator
  -> N-best LanguageHypothesis

LanguageAnalysisCoordinator
  -> FormLattice

ReferentCandidateGenerator
  -> N-best GroundingCandidate

DiscourseModel + SessionWorldModel
  -> context and multimodal evidence

SchemaActivator
  -> candidate PredicateSchema/OperationSchema activations

PortBindingSolver + MeaningAssembler
  -> UOLGraph / MeaningHypotheses

MeaningBundleSelector
  -> selected MeaningBundle + alternatives

GapClassifier
  -> typed gaps and repair options

EpistemicCoordinator
  -> KnowledgeRecords and admission assessments

LearningCoordinator
  -> LearningTransactions and GraphPatches

InferenceEngine
  -> proof-bearing proposition candidates

GoalGenerator + GoalArbiter
  -> active goals

OperationPlanner/Authorizer/Executor/Reconciler
  -> operation outcomes and effect GraphPatches

ResponseGoalGenerator + ResponseRanker
  -> selected response goals

UOLResponsePlanner
  -> UOLResponsePlan

RealizationCoordinator + EmissionGate
  -> realized output + EmissionProof
```

No component may perform a downstream authority’s decision as a convenience fallback.

---

## 18. Authority matrix

| Decision | Sole authority | Evidence providers that must not decide it |
|---|---|---|
| language hypotheses | language detection coordinator | runtime default language |
| form alternatives | language analysis coordinator | semantic kernel |
| referent candidate generation | referent resolver | NER/database hit alone |
| executable schema lifecycle | SemanticSchemaStore | loader, learner, validator |
| predicate activation | SchemaActivator | construction matcher |
| port binding and meaning hypotheses | MeaningAssembler | parser, NER, language pack |
| selected meaning bundle | MeaningBundleSelector | top parser or top proposition |
| gap type | GapClassifier | learning coordinator |
| learning eligibility | LearningEligibilityAssessor | generic gap defaults |
| epistemic use | EpistemicCoordinator | structural grounding alone |
| durable changes | GraphPatch commit coordinator | operators/direct store writes |
| active goals | GoalArbiter | response ranker |
| executable plan | OperationPlanner + Authorizer | goal label mapping |
| response-goal candidates | ResponseGoalGenerator | realization templates |
| selected response | ResponseRanker/selector | fallback strings |
| UOL response content | UOLResponsePlanner | renderer |
| surface form | RealizationCoordinator | response decider |
| semantic emission permission | EmissionGate | renderer success |

---

## 19. Trace contract

Every cycle trace must expose enough information to detect hidden hacks:

- observation and pinned version fingerprints;
- language and span segmentation alternatives;
- form lattice summary;
- mention and referent candidates;
- predicate activation sources;
- projected ports and candidate bindings;
- meaning hypotheses, assumptions, coverage, and score breakdowns;
- selected bundle and rejected alternatives;
- typed gaps and why they are or are not learnable;
- retrieval and epistemic assessments;
- graph patches and commit results;
- inference rules, proof steps, limits, and incompleteness;
- generated goals and plans;
- response-goal candidates and ranking;
- UOL response plan;
- realization coverage and emission blockers;
- context/world-model updates.

A demo debug view should display semantic keys and referent IDs, not only a response string and candidate count.

---

## 20. “Says only what it understands” contract

CEMM may assert a response clause only when all of the following hold:

1. The selected meaning bundle identifies the user’s relevant discourse goal or the system has a policy-grounded goal.
2. The response clause exists as a proposition referent in a UOL response plan.
3. Its predicate schema and all required ports are active and structurally closed.
4. Every port filler is a grounded referent or an explicitly authorized mention/quotation.
5. The epistemic assessment authorizes the clause’s context, certainty, attribution, and use mode.
6. Any inference has an admissible proof and consequence status.
7. The response-goal selector chose the clause over clarification, qualification, or silence.
8. The target language realizer covers the full UOL contribution without inventing meaning.
9. The emission gate validates the exact schema and environment revisions.

“Understands” therefore means **has an explicit, grounded, use-authorized semantic proof**, not “matched a familiar string” or “generated plausible text.”

---

## 21. Working baby CEMM capability floor

The v3.4.7 architecture is not complete merely because new classes exist. A working baby system must demonstrate all of the following through one canonical runtime:

- detect and analyze at least two languages through the common evidence contract;
- understand greetings and self queries without full-sentence routing;
- answer its name and the meaning/expansion of CEMM from seeded semantic knowledge;
- learn and remember a user’s full name and age as grounded referents/states;
- understand conjunctions that combine those facts;
- resolve `it`, `that`, participant pronouns, and at least one non-entity antecedent;
- interpret corrections and supersede the exact prior proposition/fact;
- distinguish an unknown word from an unresolved pronoun;
- conduct a bounded teaching dialogue for a new lexical form and concept;
- learn a grounded role/relationship or rule in session scope;
- distinguish strict, causal, enabling, default, association, and sensitive rules;
- derive at least one bounded proof-bearing consequence and expose its proof;
- answer a factual query from durable knowledge;
- qualify a default or reported answer rather than assert it as certain;
- plan one safe bound operation from semantic ports;
- use session multimodal state in at least one reference or port-binding test;
- generate at least two response-goal candidates for an ambiguous turn and rank them;
- construct and realize a UOL response in the selected target language;
- block any clause whose semantics or realization is not fully authorized;
- pass paraphrase and structural-variation tests without adding sentence-specific constructions.

---

## 22. Final architectural position

The fundamental CEMM abstraction is now:

```text
observations provide evidence about Referents;
predicates connect Referents through typed local ports;
UOL preserves competing grounded meanings;
context and multimodal state rank but do not fabricate them;
a compatible MeaningBundle authorizes cognition;
GraphPatches control durable learning and knowledge;
bounded inference derives proof-bearing consequences;
goals and operations act on explicit propositions;
response goals select what should be communicated;
UOL response planning specifies meaning;
language realization expresses—but never changes—that meaning.
```

This architecture is deliberately more demanding than another matcher patch. It provides a practical path to a small system that can genuinely compose, learn, reason, and communicate inside a limited but expandable semantic world.
