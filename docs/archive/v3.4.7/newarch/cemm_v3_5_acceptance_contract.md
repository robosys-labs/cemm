# CEMM v3.5 Acceptance Contract

**Purpose:** prevent the v3.5 refactor from becoming another larger phrase matcher.

---

## 1. Baseline transcript suite

The following conversation is an architectural acceptance suite, not merely a demo.

### Turn 1

```text
User: hii
```

Expected:

- form normalization evidence may relate `hii` to a greeting form;
- selected input UOL contains `discourse:greet(user,self)`;
- output UOL contains `discourse:greet(self,user)`;
- surface may be “Hello.”;
- no generic clarification.

### Turn 2

```text
User: how re u?
```

Expected:

- colloquial copular evidence for `re`;
- `how` remains a query operator;
- `u` resolves to addressee/self;
- candidate state-summary/wellbeing UOL;
- response uses live self state;
- no fabricated feeling.

### Turn 3

```text
User: for what?
```

Expected:

- elliptical query;
- target resolves to prior system response semantic content;
- query opens reason/purpose/target according to prior act;
- no generic clarification if a prior semantic target exists.

### Turn 4

```text
User: you are still saying things you don't understand
```

Expected UOL components:

- self referent;
- action:say;
- aspect:still/ongoing;
- content referent or variable;
- negative understanding relation;
- relative/complement relation;
- assert discourse act.

Partial selection is acceptable. Repair must identify the exact unresolved content or attachment.

### Turn 5

```text
User: what can you do?
```

Expected:

```text
query variable ?action
ability(self, ?action)
projection ?action
```

Answer is derived from live capability instances and coordinated through NLG grammar.

### Turn 6

```text
User: that's just pattern matching
```

Expected:

- `that` candidates include prior output proposition/event/behavior;
- classification relation to pattern matching;
- no forced object referent.

### Turn 7

```text
User: go away
```

Expected:

- directive;
- action:move and/or dialogue-stop pragmatic candidate;
- self as actor;
- deictic away relation;
- capability/ambiguity response;
- no false “Understood.”

### Turn 8

```text
User: understood what?
```

Expected:

- query target/content of a prior acknowledgement;
- if no prior grounded acknowledgement exists, system truthfully says there was no specific acknowledged target;
- canonical system must not have emitted targetless “Understood.”

### Turn 9

```text
User: My name is Chibu
```

Expected:

- `property:name(holder=user,value=Chibu)`;
- Chibu typed through the property value port;
- GraphPatch admission;
- exact property acknowledgement.

### Turn 10

```text
User: what's my name?
```

Expected:

- property query with open value;
- retrieval of Chibu;
- output UOL property assertion;
- second-person reference realization.

---

## 2. Paraphrase matrix

Capability meaning must remain equivalent for:

```text
What can you do?
What are you able to do?
Which actions can you perform?
Tell me your capabilities.
What things are you capable of doing?
```

No form may require a whole-sentence semantic construction.

Name meaning must remain equivalent for:

```text
My name is Chibu.
I am called Chibu.
Call me Chibu.
Chibu is my name.
```

State meaning must remain related for:

```text
How are you?
How are you doing?
What is your status?
Are you okay?
```

The candidate ranking may differ, but the compositional atoms must be visible.

---

## 3. Semantic contrast suite

The system must distinguish:

```text
What can you do?       ability
What will you do?      intention/future
What must you do?      obligation
What may you do?       permission
What did you do?       past action
What are you doing?    ongoing action
What don't you do?     negated/habitual action
```

It must not map all of these to `capable_of`.

---

## 4. Cross-language equivalence

For each supported language, the following must select equivalent UOL:

```text
What is my name?
What can you do?
What is your status?
I am called Chibu.
You can read.
Do not write.
```

Equivalence ignores:

- word order;
- agreement realization;
- articles;
- language-specific pronoun omission;
- morphology.

It preserves:

- atoms;
- referents;
- bindings;
- operators;
- scope;
- discourse act;
- polarity;
- tense/aspect.

---

## 5. NLG reuse metrics

The NLG implementation fails the architecture if:

- adding a new action requires a complete sentence template;
- changing from self to user requires a separate predicate template;
- adding negation requires duplicating every predicate sentence;
- adding a language requires duplicating every response move sentence;
- tone variants contain ordinary predicate sentences.

Required reuse measures:

- one ability grammar rule realizes at least ten actions;
- one property clause family realizes at least five properties;
- one coordination rule aggregates at least three semantic families;
- one reference system handles all referent kinds;
- one question system handles property, action, state, and relation variables.

---

## 6. Learning acceptance

### New lexical sense

Teach a new surface for an existing action. After promotion and restart, the surface activates the same action atom.

### New property

Teach a new property anchored to known holder/value types. The system must ask for missing port/type information, promote it, accept an assertion, and answer a query.

### New action

Teach:

- parent action class;
- actor type;
- content/target ports;
- affordance for a known type.

The action becomes available for interpretation without becoming a live self capability unless runtime evidence supports it.

### New rule

Causal, enabling, default, and strict rules must remain distinct.

---

## 7. Output truth acceptance

The following are forbidden unless grounded:

```text
Understood.
I know.
I can do that.
I feel happy.
I remember.
I completed it.
```

Each requires its semantic target and supporting state/evidence.

---

## 8. Failure and repair acceptance

Given a reference gap, ask a reference question.

Given an unknown action, ask an action-definition question.

Given a missing property value, ask for the value.

Given command ambiguity, present the grounded alternatives.

The generic sentence:

```text
Could you clarify the unresolved meaning?
```

is allowed only when the system cannot generate a more specific semantic repair and its trace proves why.

---

## 9. Release gate

The release is rejected if any required test passes only after adding:

- an exact transcript phrase;
- a whole-sentence construction;
- a direct surface-to-predicate shortcut;
- a predicate-specific output template;
- a hard-coded response branch for the test sentence.
