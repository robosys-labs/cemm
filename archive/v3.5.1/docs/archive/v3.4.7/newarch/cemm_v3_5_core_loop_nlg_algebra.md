# CEMM v3.5 Core Loop and Multilingual NLG Algebra

**Status:** proposed canonical runtime contract  
**Objective:** replace lexical-predicate routing and sentence templates with joint meaning-atom composition and semantic graph transduction.

---

## 1. Canonical loop

```text
0. PIN
1. OBSERVE
2. BUILD FORM LATTICES
3. ACTIVATE MEANING ATOMS
4. PROJECT REFERENTS AND OPERATIONAL PROFILES
5. BUILD THE COMPOSITION FACTOR GRAPH
6. SOLVE MEANING HYPOTHESES
7. SELECT A COMPATIBLE MEANING BUNDLE
8. RESOLVE DISCOURSE ACTS AND OBLIGATIONS
9. RETRIEVE / ASSESS / LEARN
10. INFER
11. PLAN / AUTHORIZE / ACT / RECONCILE
12. GENERATE RESPONSE GOALS
13. TRANSFORM TO RESPONSE UOL
14. BUILD DEEP CLAUSE PLANS
15. REALIZE GRAMMAR AND MORPHOLOGY
16. VERIFY SEMANTIC EQUIVALENCE
17. COMMIT INPUT, OUTPUT, AND COMMON GROUND
18. FINALIZE AND INVALIDATE
```

No stage may fabricate the artifact of a later stage.

---

## 2. Stage 0 — PIN

Pin:

- boot semantic database fingerprint;
- writable overlay revisions;
- language analyzer and grammar package versions;
- discourse and world snapshots;
- self operational profile;
- capability, permission, resource, and risk state;
- budgets.

The cycle must use one coherent snapshot. Critical commit uses compare-and-swap.

---

## 3. Stage 1 — OBSERVE

Create evidence atoms from:

- text;
- audio/transcript/prosody;
- vision/object tracks/gesture;
- sensors;
- tool results;
- runtime capability observations;
- user identity and channel metadata.

Evidence remains source-aligned and reversible.

---

## 4. Stage 2 — BUILD FORM LATTICES

The form lattice is a graph, not a flat list of recognized n-grams.

It contains candidates for:

- token and morpheme segmentation;
- lemmas and lexical senses;
- multiword expressions;
- phrase and clause boundaries;
- dependency/constituency relations;
- coordination and shared arguments;
- complement and relative-clause attachment;
- modality, negation, tense, and aspect scope;
- interrogative variables and expected answer types;
- omitted arguments and ellipsis;
- mentions and deictics;
- code-switched spans;
- unresolved evidence.

The lattice may combine multiple analyzers. Correlated outputs share lineage and do not receive independent-vote inflation.

---

## 5. Stage 3 — ACTIVATE MEANING ATOMS

Activation sources include:

- lexeme-sense candidates;
- morphology;
- syntactic relations;
- current referent types;
- expected open question ports;
- discourse obligations;
- multimodal state/action evidence;
- learned forms;
- bounded semantic retrieval.

An activation specifies:

```text
atom_ref
atom_class
source span/evidence
prior score
possible scope
possible argument mapping
required dependent atoms
```

Examples:

```text
"what" → operator:query candidates
"can"  → operator:ability
"do"   → operator:pro_action and action:perform alternatives
"name" → property:name
"go"   → action:move
"still"→ aspect:still
```

No activation is yet a predication.

---

## 6. Stage 4 — PROJECT REFERENTS AND OPERATIONAL PROFILES

For each referent candidate, derive:

- type closure;
- inherent properties;
- admissible state dimensions;
- afforded actions;
- live capabilities;
- permissions and resources;
- current multimodal states;
- active roles;
- discourse salience;
- temporal/context validity.

This creates candidate operational profiles tied to the pinned snapshot.

### Binding compatibility

A candidate filler is compatible only when:

```text
atom port accepts filler type
∧ referent profile admits participation
∧ context/time compatible
∧ permission allows semantic access
∧ no hard identity contradiction
```

Action execution additionally requires live capability and permission. Interpretation does not require execution capability; the system can understand actions it cannot perform.

---

## 7. Stage 5 — BUILD THE COMPOSITION FACTOR GRAPH

The factor graph contains variables for:

```text
lexeme sense
meaning atom
referent identity
atom port filler
operator scope
query variable type
clause attachment
coordination membership
discourse-act type
context/time
```

Hard factors:

- local port type constraints;
- cardinality;
- scope well-formedness;
- identity incompatibility;
- proposition embedding;
- operator argument class;
- query variable closure;
- coordination compatibility.

Soft factors:

- lexical prior;
- morphology;
- syntax;
- semantic selection preference;
- referent operational-profile fit;
- discourse salience;
- topic continuity;
- multimodal consistency;
- world consistency;
- frequency;
- assumption/coercion penalty.

The solver must expose every factor contribution in the trace.

---

## 8. Stage 6 — SOLVE MEANING HYPOTHESES

Use bounded best-first/beam search with constraint propagation.

Recommended algorithm:

1. activate high-confidence atom candidates;
2. create typed variables for open ports;
3. run arc consistency to remove impossible fillers;
4. propagate referent-type and operator-scope constraints;
5. branch on the highest-uncertainty variable;
6. retain N-best partial graphs;
7. preserve partial meaning when budget expires;
8. materialize coherent `MeaningHypothesis` records.

Do not perform one cartesian product independently for every lexical predicate.

A hypothesis may contain multiple connected applications and propositions.

---

## 9. Stage 7 — SELECT A COMPATIBLE MEANING BUNDLE

Select a set, not one top application.

Compatibility covers:

- shared referent identity;
- clause and coordination structure;
- operator scope;
- context and time;
- discourse act;
- contradiction;
- mutual exclusivity;
- coverage;
- unresolved evidence.

The selector can preserve:

- selected bundle;
- close alternatives;
- exact ambiguity;
- partial-understanding region;
- typed repair needs.

---

## 10. Stage 8 — RESOLVE DISCOURSE ACTS AND OBLIGATIONS

The discourse act is a semantic atom application.

Examples:

```text
greet(user, self)
ask(user, self, query)
assert(user, proposition)
direct(user, self, desired_action)
acknowledge(self, user, target)
correct(user, prior_proposition, new_proposition)
```

The stage derives obligations:

```text
answer query
evaluate command
store assertion
repair reference
open learning frontier
acknowledge specific commit
challenge contradiction
```

Generic acknowledgement is not a default obligation.

---

## 11. Stage 9 — RETRIEVE, ASSESS, AND LEARN

### Query retrieval

A query is matched by semantic unification:

```text
restriction graph + open variables
against
admissible proposition/application graph
```

Answer records bind variables to referents or atom refs.

### Epistemics

Assess:

- source;
- evidence lineage;
- truth status;
- context;
- valid time;
- sensitivity;
- permission;
- contradiction.

### Learning

Unknown spans do not automatically open learning.

Learning begins when:

- an explicit teaching act occurs;
- a known structure exposes an unknown atom dependency;
- the user confirms a proposed grounding;
- repeated evidence supports induction under policy.

Repair questions target the exact unresolved atom/port.

---

## 12. Stage 10 — INFER

Rules operate over meaning atoms and applications.

Rule classes remain separate:

```text
constitutive
strict
causal
enabling
preventing
default
statistical
pragmatic
normative
```

Derived defaults and sensitive consequences are not silently admitted as actual facts.

Inference can also derive affordances and capability restrictions.

---

## 13. Stage 11 — PLAN, AUTHORIZE, ACT, RECONCILE

A directive content graph is transformed into an action goal.

Planning resolves:

- action atom;
- actor;
- required semantic ports;
- operation implementation;
- preconditions;
- capability;
- permission;
- resources;
- risk;
- success condition.

Predicted effects are not observed outcomes.

---

## 14. Stage 12 — GENERATE RESPONSE GOALS

Response goals are semantic obligations, such as:

```text
answer_query
answer_capability_query
report_state
acknowledge_storage
acknowledge_correction
ask_reference_repair
ask_lexical_repair
ask_port_repair
report_capability_limitation
report_contradiction
greet
confirm_command
```

Each goal binds its semantic target and evidence.

There is no generic fallback sentence. A generic repair goal is allowed only when no more specific typed repair can be produced.

---

## 15. Stage 13 — TRANSFORM TO RESPONSE UOL

This is a semantic graph-transducer pipeline, not a neural Transformer requirement and not a text template engine.

Every transducer has:

- input graph pattern;
- preconditions;
- output graph transformation;
- preserved semantic refs;
- added discourse semantics;
- proof.

### Required transducers

#### 15.1 QueryAnswerClosure

Replaces open variables with retrieved values.

```text
query property:name(user, ?name)
+ answer ?name = Chibu
→ response property:name(user, Chibu)
```

#### 15.2 PerspectiveShift

Uses discourse roles, not string replacement.

```text
referent:self
input reference from user perspective: "you"
output reference from self perspective: "I"
```

The referent does not change; only the reference plan changes.

#### 15.3 AbilityAnswerExpansion

```text
Query Ability(self, ?action)
+ capability results [read, learn, write]
→ coordinated response applications:
  Ability(self, read)
  Ability(self, learn)
  Ability(self, write)
```

#### 15.4 PropertyProjection

Turns a property answer into an assertion with the query’s bound holder.

#### 15.5 AcknowledgementBinding

Creates an acknowledgement with an explicit target and acknowledgement kind.

#### 15.6 RepairQuestionSynthesis

Transforms a gap into a precise query:

```text
reference gap → “Who does ‘they’ refer to?”
lexical atom gap → “What does ‘glorp’ mean here?”
property value gap → “What value should I use for your name?”
command ambiguity → “Do you mean stop responding or move physically?”
```

#### 15.7 Aggregation

Combines repeated subjects, modal operators, tense, and shared complements.

#### 15.8 Contrast and qualification

Adds contradiction/default qualification without changing the claimed proposition.

---

## 16. Stage 14 — BUILD DEEP CLAUSE PLANS

A `DeepClausePlan` is language-neutral enough to share meaning but explicit enough for grammar.

```text
DeepClausePlan
  clause_ref
  nucleus_atom_ref
  semantic_arguments
  mood
  polarity
  modality
  tense
  aspect
  voice
  information_structure
  focus_ref
  topic_refs
  reference_specs
  coordination_group_ref
  subordination_relations
  discourse_function
```

Example:

```text
nucleus: action:read
subject: self
modality: ability
mood: declarative
tense: present
coordination-group: capability-list-1
```

The deep plan does not contain “I can read.”

---

## 17. Stage 15 — MULTILINGUAL NLG ALGEBRA

The NLG engine is a declarative feature-structure grammar.

### 17.1 Pipeline

```text
response UOL
→ content aggregation
→ deep clause plans
→ argument-frame selection
→ syntactic feature graph
→ reference realization
→ agreement
→ morphology
→ linearization
→ punctuation/orthography
```

### 17.2 Language pack responsibilities

A language pack defines:

- lexemes and senses;
- valency/argument frames;
- pronoun and reference paradigms;
- clause formation;
- copular/property clauses;
- modal constructions;
- question formation;
- negation;
- tense/aspect;
- coordination and shared arguments;
- relative/complement clauses;
- agreement;
- morphology;
- linearization;
- discourse particles;
- genuine idioms.

### 17.3 Ability example

Response UOL:

```text
Ability(self, read)
Ability(self, learn)
Ability(self, write)
Ability(self, reason)
Ability(self, obey(command))
```

Aggregation:

```text
shared:
  subject = self
  modality = ability
members:
  read
  learn
  write
  reason
  obey(command)
```

English grammar:

```text
subject nominative pronoun
+ finite modal "can"
+ coordinated bare infinitives
```

Possible output:

```text
“I can read, learn, write, reason, and follow commands.”
```

French grammar:

```text
subject pronoun
+ finite pouvoir
+ coordinated infinitives
```

Swahili grammar:

```text
subject agreement
+ ability construction
+ coordinated verbal infinitives/stems
```

No action-specific sentence template is needed.

### 17.4 Property example

Response UOL:

```text
property:name(user, Chibu)
```

English may choose a possessive property construction:

```text
“Your name is Chibu.”
```

French and Swahili choose their own property/copular grammar. The `property:name` atom does not contain any of those word orders.

### 17.5 Greetings

A greeting is a discourse atom with language-specific lexical realization. A fixed lexical utterance is allowed because it is a closed discourse expression, not a general predicate answer template.

---

## 18. Stage 16 — VERIFY SEMANTIC EQUIVALENCE

The current predicate-presence round trip is insufficient.

The new checker must:

1. analyze the realized surface;
2. build N-best meaning hypotheses;
3. select under a constrained output context;
4. compare the recovered graph to the response UOL.

Comparison checks:

- atom identity;
- referent identity;
- port bindings;
- operator scope;
- polarity;
- modality;
- tense/aspect;
- query/declarative mood;
- coordination;
- discourse act;
- omitted semantic content;
- added unsupported content.

Authorization thresholds can vary by risk, but required semantic contributions must be covered.

---

## 19. Stage 17 — COMMIT INPUT, OUTPUT, AND COMMON GROUND

Commit:

- admitted user propositions;
- selected discourse act;
- system response UOL;
- output proposition refs;
- acknowledgement targets;
- open/closed questions;
- common-ground status;
- reference chains;
- emission proof;
- operation outcomes.

This enables semantic follow-ups.

---

## 20. Required conversation acceptance

### “hii” / “hi”

```text
input: discourse:greet(user, self)
output: discourse:greet(self, user)
```

Elongation normalization is form evidence only.

### “how re u?”

Must produce a state-summary/wellbeing query candidate. Colloquial “re” is handled by language normalization/morphology evidence. Response comes from self state.

### “for what?”

Must resolve against the prior system response semantic target/reason.

### “you are still saying things you don’t understand”

Must represent:

- subject self;
- ongoing/still aspect;
- saying action;
- content variable/referent;
- negative understanding relation over the content;
- relative/complement attachment.

Partial understanding is acceptable, but the repair must name the unresolved content or attachment.

### “what can you do?”

Must query live self capabilities through ability + pro-action + query operators.

### “that’s just pattern matching”

“That” must be allowed to resolve to the prior system response, behavior/event, or proposition. Classification remains a candidate until grounded.

### “go away”

Must build an action directive. Candidate interpretations include physical movement and ending/pausing dialogue. Operational profiles and pragmatic evidence rank them. The response must report capability or ask the exact ambiguity.

### “understood what?”

Must query the target of a previous acknowledgement. The system must not have emitted targetless “Understood.”

### “My name is Chibu”

Must create a property-name assertion and commit it.

### “what’s my name?”

Must retrieve and realize the stored property value.

---

## 21. Performance budgets

Initial baby-system targets:

| Stage | Target |
|---|---:|
| form lattice | 20 ms |
| atom activation | 10 ms |
| profile projection | 10 ms |
| composition/selection | 50 ms |
| retrieval | 20 ms |
| response transforms | 10 ms |
| grammar realization | 25 ms |
| semantic verification | 50 ms |
| total median text turn | <200 ms without external tools |

The solver has hard limits on:

- activated atom count;
- referent candidates per mention;
- factor graph variables;
- beam width;
- scope alternatives;
- composition time;
- output round-trip alternatives.

Timeout preserves partial meaning and emits a typed limitation or repair.

---

## 22. Core-loop invariants

1. Language forms never directly create selected propositions.
2. Meaning atoms are reusable across languages.
3. Modal/query/tense/aspect semantics remain scoped.
4. Referent profiles and atom ports jointly authorize composition.
5. Output UOL is first-class discourse content.
6. Response transforms cannot invent knowledge.
7. Deep clause plans contain no final strings.
8. Language grammar cannot add semantic atoms.
9. Surface output is blocked when semantic recovery fails.
10. Typed repair outranks generic clarification.
