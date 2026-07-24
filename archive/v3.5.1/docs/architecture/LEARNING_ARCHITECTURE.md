# CEMM v3.5 Learning Architecture

**Status:** binding learning contract  
**Primary law:** all non-foundational semantic competence must be learnable through the ordinary runtime, and learned knowledge must enter the same authorities and indexes as reviewed seed knowledge.

---

## 1. Learning-first meaning

“Learning first” does not mean CEMM guesses definitions whenever it fails.

It means:

- the foundation is designed to acquire new semantic structure;
- every schema and knowledge record carries provenance and lifecycle;
- partial understanding preserves reusable learning dependencies;
- unknowns are typed rather than discarded;
- corrections and counterexamples update dependency graphs;
- learned data becomes ordinary runtime data;
- teaching, induction, observation, and configuration use one promotion architecture.

---

## 2. What CEMM can learn

### 2.1 Instance knowledge

- a new referent;
- identity anchors and aliases;
- type assertions;
- properties;
- state assignments;
- relations and roles;
- event occurrences;
- claims and source stances;
- importance/preferences;
- capability observations.

### 2.2 Schema knowledge

- referent types;
- facet entitlements;
- properties;
- state dimensions and values;
- relations;
- roles;
- functions;
- actions and events;
- affordances and dispositions;
- capability dependencies;
- transition contracts;
- causal/default/normative rules;
- impact rules;
- response policies.

### 2.3 Language knowledge

- lexical forms;
- lexical senses;
- morphology;
- argument frames;
- idioms;
- reference conventions;
- realization rules.

A language form and a semantic schema have separate lifecycles.

---

## 3. Learning triggers

Learning candidates can arise from:

```text
explicit teaching
definition
example
counterexample
correction
retraction
repeated observation
failed prediction
operation outcome
unknown form in a known semantic position
known form with unknown sense
new multimodal identity
schema competence failure
user/application configuration
```

A trigger creates evidence and candidate contributions. It does not activate them automatically.

---

## 4. Learning transaction

```text
LearningTransaction
  transaction_ref
  target_ref
  package_class
  source_context_ref
  requested_use_profiles
  contributions
  grounding_frontier
  examples
  counterexamples
  contradictions
  competence_cases
  budget
  status
```

Transactions are resumable across turns and restart.

---

## 5. Learning contribution taxonomy

```text
CREATE_REFERENT
ADD_IDENTITY_FACET
ADD_ALIAS
ASSERT_TYPE
CREATE_TYPE_SCHEMA
ADD_PARENT_TYPE
ADD_FACET_ENTITLEMENT
CREATE_PROPERTY
CREATE_STATE_DIMENSION
CREATE_STATE_VALUE
CREATE_RELATION
CREATE_ROLE
CREATE_FUNCTION
CREATE_ACTION
CREATE_EVENT
ADD_AFFORDANCE
ADD_DISPOSITION
ADD_CAPABILITY_DEPENDENCY
ADD_TRANSITION_CONTRACT
ADD_RULE
ADD_IMPACT_RULE
ADD_RESPONSE_POLICY
ADD_LEXEME
ADD_LEXEME_SENSE
ADD_ARGUMENT_FRAME
ADD_REALIZATION_RULE
ADD_EXCEPTION
ADD_COUNTEREXAMPLE
CORRECT
RETRACT
SUPERSEDE
```

---

## 6. Grounding requirements

Every learning contribution must terminate in known anchors or explicitly unresolved frontier nodes.

### 6.1 Type schema grounding

Requires at least:

- schema class;
- one known parent or explicit foundational anchor;
- identity/applicability statement sufficient for requested use;
- provenance and scope.

### 6.2 Property grounding

Requires:

- holder type constraints;
- value type/domain;
- cardinality;
- time/context policy;
- correction/supersession behavior.

### 6.3 State grounding

Requires:

- holder types;
- value domain;
- exclusivity/ordering;
- persistence;
- observation or transition path.

### 6.4 Action/event grounding

Requires:

- parent action/event class;
- participant ports;
- affected types;
- occurrence conditions;
- requested transition/effect semantics;
- context/time behavior.

### 6.5 Rule grounding

Requires:

- antecedent/consequent schemas;
- variable alignment;
- rule class;
- warrant;
- exceptions/defeaters;
- scope and sensitivity.

---

## 7. Progressive use profiles

A schema is not simply active or inactive.

Example:

```text
new type "lumin"
mention        allowed
ground         provisional
compose        allowed
query          allowed
infer          denied
transition     denied
execute        denied
realize        allowed after lexical competence
```

Promotion can be different per use.

This allows CEMM to discuss a partially learned concept without using it for dangerous inference or action.

---

## 8. Learning dialogue

CEMM selects questions by expected frontier reduction, risk, and reuse.

### 8.1 Type question

```text
Is a lumin a living thing, a digital thing, an organization, or something else?
```

### 8.2 State question

```text
Can charge have numeric values, named states, or both?
```

### 8.3 Event question

```text
When a lumin “dims,” does its charge always decrease, or is that only typical?
```

### 8.4 Capability question

```text
Does zero charge prevent reading, or merely make it less reliable?
```

### 8.5 Rule-class question

```text
Is this a definition, a cause, a requirement, or a usual expectation?
```

Questions are generated from frontier contracts, not stored transcripts.

---

## 9. Learning by example

Examples can provide:

- candidate type constraints;
- port mapping;
- state transition evidence;
- lexical sense evidence;
- argument realization;
- default frequency;
- exceptions.

Examples alone do not prove strict rules.

### 9.1 Positive examples

Support candidate generalization.

### 9.2 Negative examples

Constrain applicability and prevent overgeneralization.

### 9.3 Near misses

Help learn scope and required conditions.

### 9.4 Independent competence

At least one required competence case must not be a direct restatement of the teaching example.

---

## 10. Learning referent types

A `TypeLearningPackage` may evolve:

### Stage A — mentionable

Known label and broad parent anchor.

### Stage B — groundable

Identity/mention criteria and aliases.

### Stage C — compositional

Facet entitlements and relation/action compatibility.

### Stage D — inferential

Validated constitutive/strict/default rules.

### Stage E — operational

Action/capability/permission contracts.

### Stage F — multilingual

Lexical senses and realization competence in additional languages.

---

## 11. Learning events and transitions

Example teaching:

```text
“Dimming is when a lumin's charge becomes lower.”
```

Candidate package:

```text
EventSchema: dim
parent: decrease_event
affected port: lumin
dimension: charge
transition: decrease(charge)
```

Follow-up:

```text
“If charge reaches zero, a lumin cannot read.”
```

Candidate:

```text
CapabilityDependency:
  action = read
  requires charge > 0
```

The event and dependency remain separate. One may be valid while the other is corrected.

---

## 12. Learning impact and importance

CEMM may learn:

- an event usually harms a given affected facet;
- a user explicitly values a referent;
- a response policy for a semantic condition.

It must not infer universal user emotion from repeated mentions.

Importance learning distinguishes:

```text
short-term salience
durable preference
ownership/responsibility
goal dependency
explicit emotional attachment
```

Each has different retention and privacy.

---

## 13. Recursive learning

Recursive learning can open dependencies, but must obey:

- wall-clock limit;
- depth limit;
- item limit;
- cycle detection;
- schema-component classification;
- sensitivity policy;
- user-question budget;
- rollback;
- interruption/resumption.

A cycle does not resolve an unknown with a fabricated definition.

---

## 14. Contradiction and correction

When new teaching conflicts:

1. preserve both source contributions;
2. compare scope/context/time;
3. ask whether it is a correction, exception, alternative sense, or different context;
4. supersede only the intended contribution;
5. invalidate dependent closures;
6. rerun competence.

---

## 15. Forgetting and retraction

Forgetting can mean:

- remove an alias;
- retract one source;
- deactivate one learned schema in a scope;
- supersede a revision;
- expire session-private learning;
- delete raw evidence while retaining an allowed derived record.

It never means silently deleting dependent truth without invalidation.

---

## 16. Language learning

### 16.1 Lexical mapping

A new form maps to an existing schema/sense after grounding.

### 16.2 New sense

One form can map to multiple schemas with selection constraints.

### 16.3 Realization

Learning how to understand a word does not prove CEMM can realize it correctly. Realization has separate competence.

### 16.4 Cross-language identity

Different language forms point to the same semantic schema. They do not duplicate the concept.

---

## 17. Promotion evidence

Promotion score may consider:

- structural closure;
- anchor quality;
- source independence;
- positive competence;
- counterexample coverage;
- contradiction status;
- context breadth;
- use risk;
- realization round trip;
- restart hydration.

Score does not replace hard requirements.

---

## 18. Learning acceptance examples

### 18.1 Unknown name in known property

```text
My name is Chibu.
```

`Chibu` becomes a name-value referent through the property value port. No concept-definition dialogue is required.

### 18.2 Unknown property

```text
My glorp is blue.
```

CEMM can preserve:

```text
unknown_property(glorp, holder=user, value=blue)
```

and ask whether `glorp` names a property/state/part.

### 18.3 Unknown event

```text
The lumin dimmed.
```

If `dim` is unknown but lumin and an observed charge decrease exist, CEMM can propose an event/state-transition learning package while preserving uncertainty.

---

## 19. Anti-regression laws

- no learned concept lives only in a session-side matcher;
- no schema activates globally from one teaching statement;
- no example becomes a strict rule without classification;
- no language form is treated as the concept itself;
- no learned event runs custom mutation code;
- no unresolved dependency is hidden;
- no competence test is circular;
- no correction destroys provenance;
- no learned data disappears after restart.
