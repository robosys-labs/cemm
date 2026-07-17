# CEMM v3.5 Universal Operational Language

**Status:** canonical UOL contract  
**Purpose:** define the language-neutral units from which CEMM builds understanding, learning, state change, inference, goals, and responses.

---

## 1. UOL is not a vocabulary

UOL is a typed semantic graph language. It does not encode English words or sentence patterns.

UOL represents:

- identity;
- type;
- properties;
- state;
- events and actions;
- claims;
- relations and roles;
- operators and scope;
- change and effects;
- modality and normativity;
- impact and importance;
- discourse acts;
- queries and goals.

---

## 2. Core records

### 2.1 Semantic application

```text
SemanticApplication
  application_ref
  schema_ref
  port_bindings
  context_ref
  valid_time_ref
  polarity
  confidence
  assumptions
  evidence_refs
```

### 2.2 Port binding

A binding filler can be:

- referent;
- semantic application;
- proposition;
- event occurrence;
- semantic variable;
- coordination group;
- literal surface only when explicitly mentioned/quoted.

### 2.3 Semantic variable

```text
SemanticVariable
  variable_ref
  expected_schema_classes
  expected_type_refs
  restriction_refs
  projection
  scope_ref
```

### 2.4 Proposition

A proposition wraps truth-evaluable content.

### 2.5 Context

Every proposition/application belongs to a context or possible world.

---

## 3. Foundational operators

### 3.1 Logical operators

```text
not
and
or
if
iff
all
some
none
same
different
```

### 3.2 Query operators

```text
query
which
who
what
where
when
how
why
how_many
whether
```

Language forms may map to several query operators. The selected restriction determines expected answer type.

### 3.3 Modal operators

```text
possible
necessary
capable
permitted
obligated
intended
desired
predicted
```

### 3.4 Temporal/aspect operators

```text
past
present
future
before
after
during
ongoing
completed
habitual
still
already
not_yet
```

### 3.5 Change operators

```text
start
stop
set
activate
deactivate
gain
lose
increase
decrease
create
destroy
enable
disable
terminate
restore
```

### 3.6 Evaluation operators

```text
benefit
harm
importance
urgency
risk
preference
relevance
```

Evaluation always binds a stakeholder or goal where applicable.

---

## 4. Orthogonal negative concepts

The following are not synonyms:

```text
NOT P                    truth negation
decrease(x)              scalar direction
lose(x, y)               possession/relation transition
deactivate(capability)   activation transition
prohibit(action)         normative status
harm(event, stakeholder) evaluative valence
low_importance(x, user)  significance assessment
```

The architecture must reject any generic `negative=true` field used as a substitute for these meanings.

---

## 5. UOL state expression

```text
StateApplication(
  dimension = life_status,
  holder = fox,
  value = dead,
  interval = [t1, ...],
  context = actual
)
```

The state dimension schema determines holder constraints, values, exclusivity, persistence, and observation modes.

---

## 6. UOL event expression

```text
EventOccurrence(
  schema = die,
  affected = fox,
  time = t1,
  context = actual
)
```

The event occurrence itself does not mutate state. Transition evaluation derives candidates.

---

## 7. UOL transition expression

```text
TransitionProof(
  trigger = event:die#e1,
  rule = die.life_status_transition,
  deltas = [
    terminate(life_status=alive),
    activate(life_status=dead),
    terminate(biological_life_process)
  ]
)
```

Capability dependency evaluation can then derive:

```text
disable(self_initiated_locomotion)
disable(affective_experience)
disable(voluntary_action)
```

These are context/time-qualified and proof-bearing.

---

## 8. UOL impact expression

```text
ImpactAssessment(
  source_event = e1,
  affected = fox,
  stakeholder = user,
  direction = loss,
  valence = harmful,
  importance = high,
  magnitude = major,
  reversibility = irreversible,
  confidence = 0.91
)
```

The assessment may differ for another stakeholder.

---

## 9. UOL claim expression

Input:

```text
“The fox died.”
```

Produces at least:

```text
ClaimOccurrence(
  claimant = user,
  proposition = p1,
  audience = self,
  commitment = asserted
)

p1 = Proposition(
  content = EventOccurrence(die, affected=fox),
  context = actual_claimed_by_user
)
```

Epistemic admission decides whether p1 supports the actual conversational world.

---

## 10. UOL property and query expression

### Assertion

```text
property:name(holder=user, value=Chibu)
```

### Query

```text
query(
  variable=?name,
  restriction=property:name(holder=user, value=?name),
  projection=?name
)
```

---

## 11. UOL capability query

Input:

```text
“What can you do?”
```

Composes:

```text
discourse:ask(
  speaker=user,
  addressee=self,
  content=query(
    variable=?action:ActionSchema,
    restriction=modal:capable(holder=self, action=?action),
    projection=?action
  )
)
```

The query result contains action schema references and capability evidence, not prewritten descriptions.

---

## 12. UOL death contrasts

### 12.1 Positive actual claim

```text
The fox died.
```

Claim content includes a death occurrence.

### 12.2 Truth negation

```text
The fox did not die.
```

```text
not(EventOccurrence(die, fox))
```

No death transition fires.

### 12.3 Possibility

```text
The fox may die.
```

```text
possible(EventOccurrence(die, fox))
```

No actual transition fires.

### 12.4 Near event

```text
The fox almost died.
```

Represents a near/averted event or high-risk state. It must not activate dead state.

### 12.5 Fictional context

```text
The fox died in the story.
```

Transition applies inside the story context, not necessarily the actual world.

### 12.6 Metaphorical/device sense

```text
The battery died.
```

Type compatibility selects an operational depletion/failure schema rather than biological death.

---

## 13. UOL capability distinctions

```text
affords(type, action)
capable(referent, action, conditions)
permitted(referent, action, context)
competent(referent, action, score)
intends(referent, action)
functions_as(referent, action_or_result)
```

These must remain independently queryable.

---

## 14. UOL importance and conversational history

An importance assessment can query discourse:

```text
mention_count(fox, session_history)
recency(fox)
ownership(user, fox)
explicit_importance(user, fox)
affective_stance(user, fox)
goal_dependency(user_goal, fox)
```

The SignificanceCoordinator transforms this evidence into an assessment. It does not assert that repetition equals emotional attachment.

---

## 15. Discourse UOL

```text
greet
ask
assert
claim
report
direct
acknowledge
confirm
correct
retract
console
warn
congratulate
refuse
clarify
teach
remain_silent
```

Each discourse act has explicit participants and semantic content/target ports.

---

## 16. Response UOL

A response is built from semantic obligations.

For a high-importance harmful event:

```text
console(
  speaker=self,
  addressee=user,
  target_event=fox_death,
  target_relation=ownership_or_attachment
)
```

For a low-context report:

```text
acknowledge_specific_claim(
  target=fox_death_claim
)
```

For insufficient certainty:

```text
qualify(
  content=fox_death,
  basis=user_report
)
```

A language realizer may express these differently, but cannot add an unsupported relationship or emotion.

---

## 17. UOL graph equivalence

Semantic equivalence compares:

- schemas;
- referents;
- bindings;
- scope;
- context;
- polarity;
- modality;
- time/aspect;
- coordination;
- discourse act;
- change and impact axes.

Surface wording is not part of UOL identity.

---

## 18. UOL extension law

A learned UOL schema must provide:

- schema class;
- parent anchors;
- local ports;
- type constraints;
- facet/transition contracts where relevant;
- lifecycle and evidence;
- competence cases;
- safe use profile.

A new term with only a surface string is not a new UOL concept.
