# CEMM v3.5 Claims, Events, State Transitions, Impact, and Response

**Status:** binding dynamics contract  
**Purpose:** define how reported or observed happenings become claims, event occurrences, state/capability changes, impact assessments, and response obligations.

---

## 1. Separation of authorities

The following stages are distinct:

```text
observation
→ discourse/claim interpretation
→ proposition content
→ epistemic admission/context placement
→ event occurrence admission
→ transition preview
→ state/capability delta commit
→ impact/importance assessment
→ response-goal selection
```

No later stage is implied merely because an earlier stage succeeded.

---

## 2. Claim architecture

### 2.1 Claiming is an event

A user utterance may instantiate `event:claim`.

Ports include:

```text
claimant
audience
content proposition
commitment
time
evidence offered
```

### 2.2 Proposition is content

The proposition can contain an event occurrence candidate.

### 2.3 Admission

Admission policy decides whether the proposition supports:

- actual conversational world;
- attributed report;
- belief;
- fictional context;
- hypothetical context;
- quoted content.

### 2.4 State effect boundary

Only an admitted event occurrence in a context can trigger state transitions in that context.

---

## 3. Event schema anatomy

```text
EventSchema
  schema_ref
  parent_event_refs
  participant_ports
  occurrence_constraints
  temporal_profile
  transition_contract_refs
  result_contract_refs
  causal_contract_refs
  capability_effect_refs
  impact_rule_refs
  persistence
  reversibility
  sensitivity
```

### 3.1 Participants

Ports are event-specific. Do not assume a universal actor/object mapping.

Reusable role families may include:

```text
initiator
affected
experiencer
instrument
source
destination
location
beneficiary
content
result
cause
```

The event owns exact semantics.

---

## 4. Transition engine

### 4.1 Preview

Transition preview accepts:

- admitted/selected event occurrence;
- participant bindings;
- before-state projection;
- context/time;
- active transition contracts;
- rule/step budget.

It emits candidates and proofs.

### 4.2 Validation

Validate:

- affected holder entitlement;
- state dimension applicability;
- before-state compatibility;
- context isolation;
- temporal consistency;
- defeaters;
- rule warrant;
- capability dependency cycles.

### 4.3 Commit

Commit state deltas atomically with event/knowledge references.

### 4.4 Secondary propagation

A committed state delta invalidates dependent:

- capabilities;
- operation plans;
- defaults;
- impact assessments;
- response obligations;
- cached referent views.

---

## 5. Death model

### 5.1 Biological death schema

```text
event:biological_death
parent: terminal_biological_transition
affected: living_entity
time: required or inferred
cause: optional
```

### 5.2 Core effects

```text
terminate life_status=alive
activate life_status=dead
terminate biological_life_process
```

### 5.3 Dependency effects

Capabilities whose requirements include living biological process are disabled or terminated.

### 5.4 Non-effects

Do not infer without learned contracts:

- cause of death;
- user grief;
- permanent geospatial immobility;
- destruction of physical identity;
- deletion of historical properties;
- inability to be moved externally;
- moral evaluation.

### 5.5 Health and emotion

Health is a state dimension. Affective experience is a capability/state family.

After biological death:

- health may become terminal/inapplicable according to the health schema;
- affective experience capability becomes unavailable if it depends on living/conscious state;
- do not assert the fox “feels no emotion” as a new ongoing mental state unless the ontology explicitly models that formulation.

### 5.6 Body identity

Initial policy:

- preserve organism identity with life status dead;
- represent corpse/body role or linked body referent only when required by domain identity rules;
- never split identity automatically from one sentence.

---

## 6. Loss model

### 6.1 Relation loss

```text
lose(holder, relation_or_part)
```

Ends a possession/membership/part relation.

### 6.2 State loss

```text
deactivate/terminate(state or capability)
```

### 6.3 Scalar loss

```text
decrease(dimension, magnitude)
```

### 6.4 Identity destruction

Use only when the referent ceases to exist in the relevant context, not for ordinary possession or capability loss.

---

## 7. Capability-effect model

### 7.1 Dependency graph

Example:

```text
self_initiated_locomotion
requires:
  life_status=alive
  motor_system=functional
  sufficient_energy
```

Death invalidates one requirement. Injury may degrade another. Sleep may temporarily block voluntary action without terminating life.

### 7.2 Capability delta

```text
CapabilityDelta
  holder
  action
  prior_status
  new_status
  reason/dependency
  effective_time
  context
  proof
```

### 7.3 Reversibility

Capability loss can be:

```text
temporary
conditional
degraded
restorable
terminal
unknown
```

---

## 8. Impact model

### 8.1 Affected facet

Impact attaches to actual changes:

```text
life
health
resource
relationship
goal
function
capability
property
location
social/normative status
```

### 8.2 Stakeholders

Impact is assessed separately for:

- directly affected referent;
- owner/caregiver;
- beneficiary;
- opposing party;
- user;
- self;
- institution;
- environment.

### 8.3 Direction and valence

Direction describes change. Valence evaluates it for a stakeholder.

```text
loss of harmful constraint
→ loss direction
→ potentially beneficial valence
```

### 8.4 Magnitude

Magnitude may use:

- scalar amount;
- number of affected referents;
- facet centrality;
- duration;
- irreversibility;
- goal disruption;
- risk.

---

## 9. Importance model

### 9.1 Evidence collection

The runtime may retrieve bounded summaries of:

- prior mentions;
- ownership/relationship claims;
- explicit attachment;
- current goals;
- corrections;
- emotional tone;
- active plans;
- response history.

### 9.2 Privacy

Importance inference must respect source permissions and retention. Private relationship evidence cannot be used in a public response context without authorization.

### 9.3 Uncertainty

A likely importance score does not authorize claiming:

```text
“You loved the fox.”
```

It may authorize a gently conditional response.

---

## 10. Response-goal model

### 10.1 Candidate generation

For a death event, possible goals include:

```text
answer factual query
acknowledge specific report
qualify source uncertainty
console
ask identity/reference clarification
ask whether user wants to discuss it
warn about related risk
remain silent
follow explicit semantic response policy
```

### 10.2 Ranking factors

```text
selected discourse obligation
epistemic certainty
impact magnitude/valence
importance to user
relationship evidence
user affect
recent repetition
specificity
social appropriateness
channel
risk
realizability
```

### 10.3 Console semantics

A console response UOL must not assert unsupported emotion or relationship.

Safe semantic contents might include:

```text
acknowledge harmful event
express concern/sympathy as system discourse stance
offer bounded conversational support
```

### 10.4 Silence

Silence can be optimal, but must have a selected reason.

---

## 11. Programmed response policy

A scoped policy may say:

```text
when:
  event_schema = biological_death
  affected_relation_to_user = companion_animal
then:
  prefer console
  realize literal = "I'm sorry for your loss."
```

Rules:

- semantic trigger, not keyword;
- explicit scope/source;
- literal output marked as policy;
- no hidden claim that CEMM independently derived the phrase;
- permission and language handling;
- policy can be overridden by safety or contradiction constraints.

---

## 12. Worked examples

### 12.1 “My fox died.”

Potential meaning:

```text
ownership(user, fox)
claim(user, proposition(event:biological_death(fox)))
```

After admission:

```text
life_status(fox)=dead
life-dependent capabilities unavailable
impact harmful/irreversible for fox
importance to user raised by ownership, not proven emotional attachment
```

Response candidates:

```text
specific acknowledgement
conditional console
clarification if fox identity ambiguous
```

### 12.2 “A fox died.”

No user relation. Specific acknowledgement or no-output may outrank console.

### 12.3 “My beloved fox died.”

Explicit affective/importance evidence supports stronger console.

### 12.4 “The fox that attacked my chickens died.”

Stakeholder valence may be mixed. Avoid presuming grief or celebration.

### 12.5 “The battery died.”

Operational state transition:

```text
charge/availability decreases
power_supply capability unavailable
```

No biological capability consequences.

### 12.6 “The fox didn't die.”

Negated event. No transition or death impact.

### 12.7 “If the fox dies, it cannot run.”

Hypothetical rule candidate:

```text
biological_death(fox)
→ self_initiated_run capability unavailable
```

No actual death.

---

## 13. Explanation and trace

CEMM should be able to expose:

- selected event sense;
- source/context;
- transition contracts fired;
- state/capability deltas;
- blocked effects;
- impact factors;
- importance evidence;
- response goals considered;
- why a console/silence/clarification was selected.

---

## 14. Anti-regression laws

- no response directly from the token “died”;
- no biological effects on non-living types;
- no actual transition from modal/fictional events;
- no user grief claim from ownership alone;
- no single negative weight for all loss meanings;
- no capability deletion;
- no event-specific mutation function;
- no claim-to-fact shortcut;
- no history search outside permissions;
- no literal phrase policy without provenance.
