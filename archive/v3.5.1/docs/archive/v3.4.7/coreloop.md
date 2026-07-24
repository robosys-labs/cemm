# CEMM v3.4.7 Canonical Core Loop

**Status:** replacement runtime control contract  
**Depends on:** `architecture.md`  
**Purpose:** define the only valid end-to-end path from observation to grounded meaning, learning/action, UOL response, realization, and commit  
**Core rule:** no stage may skip forward by constructing the artifact owned by a later authority.

---

## 1. Core-loop objective

The core loop must transform uncertain multimodal evidence into bounded, explainable cognition.

```text
Observation
  → Form Evidence Lattice
  → Referent Candidates
  → Activated Schemas and Operational Ports
  → UOL Meaning Hypotheses
  → Compatible Meaning Bundle
  → Gaps / Knowledge / Learning / Inference
  → Goals and Operations
  → Response-Goal Candidates
  → UOL Response Plan
  → Target-Language Realization
  → Authorized Commits
```

The loop must remain useful when:

- no full-sentence construction matches;
- several languages or scripts occur in one turn;
- a mention could refer to an entity, event, proposition, state, place, time, or visual track;
- multiple clauses and conjunctions express several compatible propositions;
- some words are unknown but the rest of the meaning is usable;
- the user is teaching a new concept or rule;
- a possible inference is only typical or sensitive;
- an answer is unavailable but a precise clarification is possible.

---

## 2. Cycle records and pinned authority

### 2.1 Cycle trigger

A cycle begins with one or more `ObservationEnvelope` records.

```text
CycleTrigger
  trigger_id
  trigger_kind
  observation_refs
  session_ref
  parent_cycle_ref
  requested_operation_ref?
  deadline?
```

Trigger kinds include user utterance, multimodal observation, tool outcome, timer, operation outcome, schema invalidation, and replay.

### 2.2 Pinned cycle snapshot

Every cycle pins:

- schema store revision and foundation fingerprint;
- referent registry revision;
- knowledge store revision;
- discourse model revision;
- session world-model revision;
- language detector and analyzer versions;
- language-pack and realization versions;
- grounding and scoring policy versions;
- inference and truth-maintenance versions;
- capability, permission, and self-state snapshots;
- clock and locale observation;
- resource budgets.

All selection and authorization artifacts identify this snapshot. A revision change before critical commit triggers compare-and-swap failure, reassessment, or replay.

### 2.3 Cycle state

The canonical `CognitiveCycle` carries immutable stage outputs:

```text
observations
language_hypotheses
form_lattices
referent_candidates
schema_activations
uol_candidate_graph
meaning_hypotheses
meaning_bundle
selection_alternatives
gaps
epistemic_assessments
knowledge_results
learning_transactions
graph_patches
inference_outcomes
goals
operation_plans
operation_outcomes
response_goal_candidates
selected_response_goals
uol_response_plan
realization
emission_proof
commit_outcomes
trace
```

Fields are never repurposed to hide incompatible legacy objects.

---

## 3. Macro control structure

The runtime has five macro phases:

1. **Orient and analyze** — pin authority, detect language, build reversible form evidence.
2. **Ground and understand** — resolve referent candidates, activate schemas, compose UOL, select a meaning bundle.
3. **Know and learn** — classify gaps, retrieve, assess, stage GraphPatches, infer, and commit authorized semantic changes.
4. **Goal and action** — derive goals, plan/authorize operations, execute, and reconcile.
5. **Communicate and finalize** — generate response goals, plan UOL, realize, authorize emission, update discourse, and invalidate stale derivatives.

Stages below are logical authorities. Implementations may pipeline safe evidence work, but they may not merge authorities or bypass stage artifacts.

---

## 4. Stage 0 — ORIENT AND PIN

### Inputs

- cycle trigger;
- session ID;
- live stores and runtime components.

### Actions

1. Allocate cycle and trace IDs.
2. Pin all revisions and policy fingerprints.
3. Load bounded discourse and session-world projections.
4. Observe live self capability, permission, health, and resource state.
5. Allocate composition, inference, learning, operation, and realization budgets.
6. Determine privacy and retention constraints before analyzers run.
7. Preserve parent-cycle and replay lineage.

### Outputs

- initialized cycle;
- pinned snapshot;
- `DiscourseContextSnapshot`;
- `SessionWorldSnapshot`;
- `SelfStateSnapshot`.

### Invariants

- no semantic interpretation occurs here;
- no default language is selected as truth;
- context snapshots are projections, not durable knowledge;
- all later artifacts are tied to this snapshot.

---

## 5. Stage 1 — OBSERVE

### Actions

1. Normalize transport metadata without altering raw payload identity.
2. Create modality-specific `EvidenceAtom`s with exact source alignment.
3. Record speaker/addressee, channel, timestamp, device/sensor, and confidence candidates.
4. Link simultaneous observations, such as speech plus gesture or image frame.
5. Preserve inaccessible or unsupported payloads as typed observation gaps.

### Outputs

- observation set;
- modality evidence atoms;
- observation-level source and permission assessments.

### Failure behavior

A failed modality adapter does not erase other observations. It produces an `analysis_gap` with the failing modality and retained raw evidence reference.

---

## 6. Stage 2 — DETECT LANGUAGE AND ANALYSIS ROUTES

### 6.1 Language hypotheses

For textual or transcribed spans:

1. Generate N-best language/script hypotheses.
2. Detect possible code-switched segments.
3. Apply explicit user language choice, session preference, and channel metadata as priors.
4. Choose one or more competent analyzers under budget.
5. Record unsupported-language gaps without forcing English.

### 6.2 Non-language analyzer routes

Select vision, gesture, audio, sensor, database, and structured-tool analyzers according to observation type and live capability.

### Outputs

- analyzer route plan;
- language hypotheses and span assignments;
- capability/coverage warnings.

### Invariants

- language selection remains N-best until evidence fusion;
- a hint cannot override strong contradictory evidence without trace;
- kernel code never branches on surface words.

---

## 7. Stage 3 — BUILD THE FORM LATTICE

This stage creates the instant virtual map of possible utterance or signal forms.

### 7.1 Text and language evidence

Each selected analyzer emits candidates for:

- token/morpheme spans;
- normalization and lemma;
- lexical senses;
- multiword forms and idioms;
- morphology and agreement;
- named and descriptive mentions;
- quantities, units, times, and places;
- clause/sentence boundaries;
- conjunction and coordination;
- relative clauses;
- complement and quotation structure;
- dependency/constituency relations;
- negation, modality, tense, and aspect scope;
- interrogative/directive/discourse cues;
- ellipsis and omitted arguments;
- unresolved spans.

### 7.2 Multimodal evidence

Other analyzers emit candidates for:

- tracked referent regions;
- object/person/place/event classifications;
- gesture targets;
- spatial relations;
- state observations;
- event boundaries;
- temporal alignment;
- speaker and affect/prosody cues;
- tool/database identifiers.

### 7.3 Fusion

`AnalysisFusionCoordinator` merges candidates into one or more `FormLattice`s while preserving:

- exact source evidence;
- analyzer identity and version;
- confidence;
- mutually exclusive alternatives;
- correlation lineage;
- unresolved evidence.

Correlated analyzers do not receive independent-evidence credit merely because they produced separate records.

### Outputs

- fused form lattices;
- analyzer coverage report;
- unresolved evidence map.

### Invariants

- constructions are evidence, not predications;
- clause boundaries remain candidates;
- NER labels are mention-kind proposals, not identities;
- no durable memory write occurs.

---

## 8. Stage 4 — GENERATE REFERENT CANDIDATES

### 8.1 Mention expansion

For every mention or implicit argument candidate, generate possible `ReferentKind`s and identity anchors.

Examples:

- “it” may denote a physical object, event, proposition, state, or information object;
- “there” may denote a place, visual region, or discourse location;
- “34 years” yields a quantity referent and unit referent;
- “yesterday” yields a time interval referent relative to the pinned clock;
- “the president” evokes a role-occupancy description, not a fixed person;
- a relative pronoun inherits candidate antecedents from its clause relation.

### 8.2 Registry and database cross-reference

Query bounded indexes for:

- aliases and names;
- known referent identities;
- place and geospatial candidates;
- event and temporal candidates;
- active discourse referents;
- session multimodal tracks;
- learned private/session concepts;
- schema referents for metalinguistic mentions.

### 8.3 Candidate identity operations

Propose, but do not yet commit:

- same identity;
- different identity;
- alias relation;
- mention-of relation;
- new provisional referent;
- referent merge/split alternatives.

### 8.4 Initial grounding score

Score identity anchors, alias support, referent kind, recency, salience, modality, location/time fit, and permissions. Port compatibility is added after schema activation.

### Outputs

- mention-to-referent candidate lattice;
- provisional new referent candidates;
- unresolved reference candidates.

### Invariants

- database hits never become selected identity directly;
- opaque text is not automatically a new entity;
- all candidate identities retain alternatives and source evidence.

---

## 9. Stage 5 — ACTIVATE PREDICATE AND OPERATION SCHEMAS

### 9.1 Activation evidence

Activate candidate schemas from:

- lexical senses;
- structural relation evidence;
- recognized referent kinds;
- clause operators and morphology;
- learned form patterns;
- active questions and discourse obligations;
- session-world relations;
- bounded schema retrieval.

### 9.2 Activation assessment

For every schema candidate, assess:

- lifecycle status and scope;
- applicability context/time;
- structural closure;
- available language-independent semantic definition;
- required competence profile;
- interpretation use permission;
- evidence support;
- dependency freshness.

### 9.3 Port projection

Project local operational ports with:

- exact port schema;
- accepted referent kinds/types;
- required/query-open status;
- candidate filler pool;
- context and valid-time propagation;
- algebraic constraints;
- permitted coercions;
- source evidence.

### Outputs

- `SchemaActivation`s;
- operational-port candidate structures;
- schema and port gaps.

### Invariants

- the construction matcher cannot force activation;
- a lexical form can activate several senses;
- a schema can be usable for mention/quotation while blocked for assertion or inference;
- no predication is selected yet.

---

## 10. Stage 6 — JOINT REFERENT AND PORT RESOLUTION

Referent resolution and predicate-port binding are interdependent. v3.4.7 therefore performs them jointly rather than finalizing pronouns before knowing semantic roles.

### 10.1 Candidate binding generation

For each operational port, gather compatible candidates from:

- local explicit mentions;
- shared coordinated arguments;
- embedded proposition candidates;
- speaker, addressee, and self referents when licensed;
- discourse antecedents;
- session-world tracks;
- ellipsis candidates;
- query-open variables.

### 10.2 Constraint propagation

Propagate:

- type and referent-kind constraints;
- agreement/case evidence;
- relation algebra;
- co-reference and anti-coreference constraints;
- clause and scope assignments;
- temporal/geospatial compatibility;
- cardinality;
- context accessibility;
- permission and information access.

### 10.3 Iterative scoring

Port fit improves referent ranking, and referent identity improves predicate fit. Iterate under a bounded fixed-point/beam budget until:

- scores stabilize;
- no new compatible candidates appear;
- or the stage budget is reached.

### Outputs

- enriched referent grounding candidates;
- port binding candidates;
- explicit assumptions/coercions;
- unresolved port/reference alternatives.

### Invariants

- no greedy pronoun decision before semantic compatibility;
- no candidate is silently discarded solely for low frequency if it uniquely satisfies hard constraints;
- timeout preserves the best partial alternatives and records incompleteness.

---

## 11. Stage 7 — ASSEMBLE UOL MEANING HYPOTHESES

### 11.1 Predication assembly

Instantiate candidate predications from schema activations and port bindings.

Each candidate contains:

- active schema revision;
- exact filled and open ports;
- source evidence;
- assumptions;
- local context/time candidates;
- coverage;
- confidence factors.

### 11.2 Proposition construction

Create proposition referent candidates with independent axes for:

- context;
- polarity;
- modality;
- attribution;
- valid time;
- discourse force.

### 11.3 Structural composition

Build candidates for:

- clause coordination;
- shared arguments;
- subordinate clauses;
- relative clause attachment;
- complement content;
- condition/consequence;
- cause/explanation;
- correction/contrast;
- quotation and report;
- questions with open ports;
- directives with desired operation/state content.

### 11.4 Rule and teaching candidates

Conditional or definitional language creates `LearningContributionCandidate`s and rule-structure candidates. It does not directly register schemas or rules.

### 11.5 Bounded beam

Expand candidates in order of expected information gain and structural support. Apply caps by clause, predicate family, port combination, and embedding depth.

### Outputs

- cycle-local `UOLGraph`;
- clause and discourse `MeaningHypothesis` sets;
- unresolved evidence and open ports;
- contribution candidates.

### Invariants

- exact sentence matches are never required;
- partial useful meanings remain candidates;
- every semantic node has source lineage;
- temporary UOL is not durable memory.

---

## 12. Stage 8 — SELECT THE COMPATIBLE MEANING BUNDLE

### 12.1 Bundle search

Search for compatible sets that jointly explain the turn.

A valid set must satisfy:

- structural exclusivity constraints;
- referent identity consistency;
- port cardinality and type constraints;
- scope and context coherence;
- coordination preservation;
- no incompatible double consumption of evidence;
- discourse-act coherence;
- acceptable unresolved residue.

### 12.2 Bundle score

Score named factors:

```text
surface and multimodal coverage
structural coherence
schema competence
port compatibility
referent grounding
context/topic continuity
world-model consistency
discourse-goal fit
minimal coercion
minimal unexplained evidence
complexity penalty
contradiction penalty
```

### 12.3 Ambiguity policy

- Select a single bundle only when its margin and use profile are sufficient.
- Preserve N-best alternatives for later retrieval, goal, or clarification use.
- If alternatives differ only in details irrelevant to the current goal, defer the decision.
- If alternatives would change a fact, operation, or answer materially, create an ambiguity gap.
- Never turn low confidence into a confident actual-world assertion.

### 12.4 Error attribution

Before any decision, classify the source of uncertainty:

- analyzer disagreement;
- lexical ambiguity;
- reference ambiguity;
- missing schema;
- port incompatibility;
- context conflict;
- knowledge absence;
- permission/capability limitation.

This prevents the system from asking a lexical-learning question when the actual failure is an unresolved antecedent.

### Outputs

- selected `MeaningBundle`;
- alternatives;
- `SelectionAssessment`;
- error attribution map.

---

## 13. Stage 9 — CLASSIFY GAPS AND RUN BOUNDED REPAIR

### 13.1 Gap classification

Create typed gaps from the selected bundle, alternatives, and error attribution. Each gap includes:

```text
gap_id
gap_kind
target_ref
blocked_use_modes
candidate_resolutions
learnability
expected_evidence
information_gain
priority
budget
```

### 13.2 Learning eligibility

A gap is eligible for a learning transaction only when:

- it is lexical/schema/relation/frontier related;
- the intended target can be identified;
- at least one existing grounding anchor or typed frontier dependency exists;
- the source has appropriate teaching permission;
- the requested scope is allowed;
- the contribution type is representable;
- it is not actually a reference, knowledge, permission, or capability gap.

### 13.3 Internal repair pass

Before asking the user, attempt a bounded repair pass using:

- alternate language hypotheses;
- alternate clause boundaries;
- alternate referent candidates;
- open discourse obligations;
- relevant knowledge retrieval;
- multimodal tracks;
- learned aliases;
- lower-confidence but structurally valid hypotheses.

The pass may return to stages 4–8 with reduced budgets. It cannot create new surface rules or bypass semantic constraints.

### 13.4 External probe

When repair requires user evidence, generate a precise candidate response goal such as:

- select between referents;
- supply a missing predicate port;
- identify the kind of an unknown term;
- distinguish strict rule versus default;
- authorize an operation;
- provide missing knowledge.

### Outputs

- typed gaps;
- repaired bundle or repair-needed status;
- learning-eligible frontier items;
- probe candidates.

---

## 14. Stage 10 — KNOW: RETRIEVE AND EVALUATE

### 14.1 Query projection

Convert selected question propositions and open ports into semantic queries over:

- referents;
- propositions and knowledge records;
- state/event/time/place indexes;
- schemas and rules;
- session discourse/world models;
- capability and permission records.

Querying never uses raw transcript phrases as the authoritative key.

### 14.2 Retrieval

Retrieve exact and compatible records under scope, context, time, permission, and revision constraints. Preserve contradictory and alternative results.

### 14.3 Epistemic assessment

For selected assertions, retrieved answers, and potential response claims, assess:

- source and evidence lineage;
- direct versus derived support;
- context and attribution;
- truth status;
- confidence calibration;
- validity interval;
- sensitivity;
- independence;
- requested use mode.

### 14.4 Knowledge gap

An understood question with no supported answer creates `knowledge_gap`, not `schema_gap` and not an automatic teaching transaction.

### Outputs

- retrieval results;
- epistemic assessments;
- answer proposition candidates;
- knowledge/epistemic gaps.

---

## 15. Stage 11 — LEARN, ADMIT, AND INFER

### 15.1 Learning dialogue resolution

If a learning transaction is open:

1. Match the current selected contributions to the exact frontier item.
2. Preserve unrelated assertions as normal turn content.
3. Reject or defer ambiguous contributions.
4. Update the frontier and dependency graph.
5. Generate a GraphPatch only when the contribution is structurally grounded.

### 15.2 Contribution compilation

Compile grounded contributions into proposed:

- lexical aliases;
- referent identities/kinds;
- predicate and port schemas;
- roles/relationships;
- state dimensions;
- event/place patterns;
- operation affordances;
- rule/default/exception schemas;
- realization schemas.

No compiler copies raw prose into executable definition fields.

### 15.3 Knowledge admission

Selected assertions create proposition referents and knowledge-record patches only when the current use profile allows admission. Attributed or hypothetical propositions remain in their context.

### 15.4 Patch validation and commit

For each GraphPatch:

- validate structural closure;
- check exact revisions;
- assess permission and scope;
- classify sensitivity;
- detect contradictions and cycles;
- run required competence tests;
- apply atomically or reject;
- retain rollback and invalidation edges.

### 15.5 Bounded inference

After successful knowledge/schema commits:

1. enqueue changed propositions/facts;
2. select reachable active rules;
3. infer under depth, firing, existential, sensitivity, and wall-clock budgets;
4. produce proof-bearing proposition candidates;
5. assign consequence status;
6. commit only statuses allowed by consequence policy;
7. record partial/incomplete outcomes.

### Outputs

- learning transaction state;
- committed/rejected GraphPatches;
- knowledge records;
- inference outcomes and proofs;
- invalidation dependencies.

### Invariants

- no learning from a generic unresolved role;
- no single teaching example self-certifies global competence;
- defaults and sensitive associations do not become unqualified actual facts;
- no direct store writes outside patch commit authority.

---

## 16. Stage 12 — GENERATE AND ARBITRATE GOALS

### 16.1 Goal generation

Generate `GoalRecord` candidates from:

- selected discourse force and proposition content;
- open query ports;
- requested operations;
- corrections;
- learning obligations;
- gaps and repair candidates;
- policy obligations;
- pending commitments;
- self-state and resource constraints.

Goals contain explicit desired proposition or operation success conditions.

### 16.2 Candidate goal families

- satisfy information request;
- acknowledge/store assertion;
- resolve reference/meaning;
- continue teaching;
- perform operation;
- correct common ground;
- explain limitation;
- preserve safety/permission;
- maintain discourse continuity;
- no action.

### 16.3 Arbitration

Rank by:

- user intent fit;
- urgency;
- obligation;
- controllability;
- expected value/information gain;
- capability and permission;
- risk;
- cost;
- compatibility with other goals;
- progress and repetition.

Select a compatible goal set, not merely the highest generic speech-act goal.

### Outputs

- active goals;
- rejected/deferred goals;
- arbitration proof.

---

## 17. Stage 13 — PLAN, AUTHORIZE, ACT, RECONCILE

### 17.1 Operation planning

For operation goals:

1. activate applicable operation schemas;
2. project input/output ports;
3. bind ports to referents;
4. verify preconditions from knowledge and session state;
5. simulate effects as GraphPatches;
6. estimate resources, risk, and reversibility;
7. construct bounded plan alternatives;
8. select a plan that satisfies explicit success conditions.

A generic goal-kind-to-operation mapping is insufficient.

### 17.2 Authorization

Authorize using live:

- capability;
- permission;
- user confirmation policy;
- resource state;
- risk;
- current schema revisions;
- current referent state;
- idempotency and replay protection.

Revalidate immediately before irreversible effects.

### 17.3 Execute and reconcile

Execute through registered adapters. Convert outcomes into observations, compare them with predicted effects, classify mismatch, and propose effect GraphPatches. Unexpected outcomes can trigger a child cognition cycle.

### Outputs

- operation plans;
- authorization decisions;
- execution ledger;
- reconciled outcomes and effect patches.

---

## 18. Stage 14 — GENERATE AND SELECT RESPONSE GOALS

### 18.1 Candidate generation

Generate response-goal candidates from active goals, answers, learning state, operation outcomes, gaps, and discourse state.

Candidate types include:

- answer;
- qualified answer;
- acknowledge;
- confirm correction;
- targeted clarification;
- learning probe;
- operation status/result;
- capability/permission explanation;
- uncertainty disclosure;
- rapport/discourse continuation;
- silence/no-output.

### 18.2 Candidate semantic content

Each candidate identifies exact proposition referents or gap/operation records. It cannot consist only of a response label such as `acknowledge` with no semantic target.

### 18.3 Ranking

Rank by:

- active-goal satisfaction;
- semantic relevance;
- epistemic authorization;
- discourse coherence;
- information gain;
- risk and permission;
- specificity;
- brevity/cost;
- repetition;
- social-tone fit;
- realizability.

### 18.4 Selection

Select a compatible response set. Examples:

- answer plus brief acknowledgement may be compatible;
- confident answer plus unresolved-reference clarification is not;
- operation result plus required warning may be compatible;
- no-output wins when all semantic outputs are unauthorized.

### Outputs

- ranked response-goal candidates;
- selected response goals;
- response-selection proof.

---

## 19. Stage 15 — PLAN THE UOL RESPONSE

### 19.1 Target language and channel

Choose target language from explicit instruction, current addressed segment, session preference, last successful shared language, then configured fallback. Select channel and accessibility constraints.

### 19.2 Semantic content plan

Construct `UOLResponsePlan` with:

- propositions to assert, ask, acknowledge, qualify, mention, or quote;
- response-goal links;
- discourse order and relations;
- topic/focus/given/new structure;
- reference plan for every referent;
- certainty, attribution, and source constraints;
- politeness, tone, brevity, and channel constraints;
- realization requirements;
- provenance.

### 19.3 Reference planning

For each referent choose an expression strategy:

- pronoun/deictic if unambiguous;
- name or known alias;
- definite/indefinite description;
- schema label;
- quoted user form;
- explicit disambiguating description.

Reference generation uses discourse state and target-language grammar, not surface copying.

### 19.4 Mood and tone

Use current self-state and tracked conversational tone only as style constraints. They cannot change semantic content, certainty, or commitments.

### Outputs

- UOL response plan;
- reference plans;
- semantic coverage requirements.

### Invariants

- no final wording is chosen here;
- every clause has a semantic target and provenance;
- all uncertainty/attribution is explicit.

---

## 20. Stage 16 — REALIZE AND AUTHORIZE EMISSION

### 20.1 Realization

The target-language realizer:

1. selects realization schemas;
2. orders clauses and ports;
3. generates referring expressions;
4. applies morphology, agreement, tense/aspect, particles, and word order;
5. applies allowed tone/style choices;
6. creates exact span-to-UOL coverage.

### 20.2 Emission gate

For each clause verify:

- selected response goal;
- active predicate/realization schemas;
- all required ports;
- grounded referents;
- epistemic use authorization;
- self-claim authorization;
- inference proof where applicable;
- full realization coverage;
- no unauthorized surface literal;
- pinned revision freshness.

### 20.3 Failure behavior

- If one optional clause fails, remove it and recheck discourse coherence.
- If a required clause fails, attempt a semantically weaker authorized plan, such as qualification or clarification.
- If no plan is authorized, emit no semantic sentence and expose the blocker through trace/transport diagnostics.

### Outputs

- realized message;
- `EmissionProof`;
- blocked clause records.

---

## 21. Stage 17 — OUTPUT COMMIT AND CONTEXT UPDATE

After successful dispatch:

1. record exact realized clauses and transport result;
2. update common ground by proposition referent, not clause ID alone;
3. add inbound and outbound selected meanings to the discourse model;
4. update mention chains, focus, open questions, obligations, and repetition history;
5. update session world tracks from admitted observations/outcomes;
6. register dispatched learning probes and operation confirmations;
7. preserve undelivered plans separately from asserted common ground.

A planned but undispatched sentence is not common ground.

---

## 22. Stage 18 — INVALIDATE AND FINALIZE

1. Compare current revisions with the pinned snapshot.
2. Invalidate stale assessments, inferences, goals, plans, and undispatched messages.
3. Schedule bounded replay where required.
4. Close or retain learning/operation obligations.
5. finalize metrics and trace;
6. return public output plus structured diagnostics.

Original evidence and already dispatched historical output remain preserved subject to privacy policy.

---

## 23. Canonical pseudocode

```python
def run_cycle(trigger):
    cycle = orient_and_pin(trigger)
    cycle = observe(cycle)
    cycle = route_analyzers(cycle)
    cycle = build_form_lattices(cycle)
    cycle = generate_referent_candidates(cycle)
    cycle = activate_schemas_and_ports(cycle)

    cycle = jointly_resolve_referents_and_ports(cycle)
    cycle = assemble_uol_hypotheses(cycle)
    cycle = select_meaning_bundle(cycle)
    cycle = attribute_errors(cycle)
    cycle = classify_gaps(cycle)

    if should_attempt_internal_repair(cycle):
        cycle = bounded_repair_reentry(cycle, stages=(4, 5, 6, 7, 8))

    cycle = retrieve_and_assess_knowledge(cycle)
    cycle = resolve_learning_dialogue(cycle)
    cycle = compile_graph_patches(cycle)
    cycle = validate_and_commit_patches(cycle)
    cycle = run_bounded_inference(cycle)

    cycle = generate_and_arbitrate_goals(cycle)
    cycle = plan_authorize_execute_reconcile(cycle)

    cycle = generate_response_goals(cycle)
    cycle = rank_and_select_response_goals(cycle)
    cycle = plan_uol_response(cycle)
    cycle = realize_target_language(cycle)
    cycle = authorize_emission(cycle)
    cycle = dispatch_and_commit_output(cycle)

    cycle = invalidate_and_finalize(cycle)
    return cycle
```

No fallback path may call the renderer directly from raw text, gaps, or retrieval records.

---

## 24. Practical interpretation examples

### 24.1 “What does your name mean?”

Expected path:

1. `your` resolves to self.
2. `name` activates the naming predicate/state and resolves the self name referent `CEMM`.
3. `what ... mean` activates a query over the meaning/expansion of that name referent.
4. The prior question “What’s your name?” and answer increase salience of the CEMM name proposition.
5. Retrieval finds the seeded expansion “Contextual Event Memory Model.”
6. Response goals include direct answer and, if needed, a qualified explanation.
7. No lexical-learning transaction opens because the blocker is not a missing lexical definition.

### 24.2 “My name is Chibueze Opata and I am 34 years old.”

Expected bundle:

- `named(user, name:Chibueze_Opata)`;
- `has_state(user, dimension:age, quantity:34_years, valid_time:now)`;
- coordination relation;
- one source-attributed assertion act with two proposition contents or two coordinated assertion acts.

The name is a text/name referent; `34` is a quantity referent; `year` is a unit referent; age is time-indexed. Both propositions can commit in one atomic knowledge patch if policy permits.

### 24.3 “You keep saying that.”

Expected path:

- `you` → self;
- `that` generates candidates for recent system proposition(s), not only physical entities;
- habitual/repetition evidence activates a communication/repetition predicate;
- discourse history supplies actual repeated proposition candidates;
- if several outputs are plausible antecedents, ask which one rather than opening schema learning.

### 24.4 “The president who won yesterday is in Abuja.”

Expected path:

- candidate role-occupancy referent for “the president”;
- relative clause attached to that candidate;
- event candidate for winning with time `yesterday`;
- place candidate Abuja;
- main location proposition;
- identity selected only when role, event, time, and database/context evidence converge.

No full-sentence construction is required.

### 24.5 Multimodal “Put it there.”

Expected path:

- directive cue;
- `it` candidates from discourse and visible tracks;
- `there` candidates from gesture/visual region and discourse places;
- move/place operation schema activation;
- port compatibility and gesture evidence jointly select object and destination;
- authorization checks capability and permission;
- clarification if either port remains materially ambiguous.

---

## 25. Core-loop acceptance gates

The canonical loop is verified only when tests prove:

1. Every stage artifact is produced by its named authority.
2. No language adapter directly emits selected predications or facts.
3. No exact construction is required for ordinary compositional variants.
4. At least two languages produce equivalent UOL for the shared suite.
5. Referent resolution handles entity, place, event, proposition, state, quantity/unit, and time antecedents.
6. Joint bundle selection preserves coordinated meanings.
7. Error attribution prevents reference gaps from becoming learning transactions.
8. Learning produces GraphPatches and never direct store writes.
9. Rule classification controls consequence materialization.
10. Operation plans bind required ports and explicit success conditions.
11. Response generation produces multiple semantic candidates before ranking.
12. UOL response plans contain no final sentence strings.
13. Realization coverage is complete and reversible for tested clauses.
14. Unsupported output is blocked rather than guessed.
15. Every selected meaning and output has a human-readable trace proof.
16. The broken web-demo sequence works without transcript-specific construction additions.
17. Paraphrase, word-order, conjunction, reference, and code-switch mutations retain semantic equivalence where appropriate.
18. Resource budgets produce graceful partial results, not hidden timeouts or arbitrary fallbacks.

---

## 26. Final core-loop law

The core loop is successful only when the following chain is true:

```text
raw observation
≠ selected meaning

analyzer proposal
≠ selected meaning

construction match
≠ selected meaning

selected meaning
≠ admitted knowledge

admitted knowledge
≠ executable permission

response goal
≠ surface sentence

surface sentence is allowed
only when it is a complete realization
of an authorized UOL response plan.
```
