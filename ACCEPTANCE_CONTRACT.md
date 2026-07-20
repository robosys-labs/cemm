# CEMM v3.5 Foundational Acceptance Contract

**Purpose:** prove that the redesign is a learning-first semantic system rather than a larger rule/template patch.

---

## 1. Architectural prohibition tests

CI fails if canonical kernel code contains:

- transcript-specific phrases;
- language-specific semantic word tests;
- direct `how/do/can/what` to completed proposition mappings;
- per-predicate answer sentences;
- generic targetless “Understood”;
- one `negative` field used for multiple semantic axes;
- event-specific state mutation code;
- source-code enum additions required for learned semantic types;
- defaults inserted as active state;
- claims automatically treated as actual facts.

---

## 2. Referent entitlement tests

### 2.1 Applicable unknown

A fox has an applicable health dimension with unknown value.

### 2.2 Inapplicable

A proposition does not have biological health merely because the word “healthy” is mentioned.

### 2.3 Latent

A software agent can have a latent vision capability without an active vision adapter.

### 2.4 Default

A learned default ranks a state candidate but does not create a StateAssignment.

### 2.5 Blocked

A read capability becomes blocked when content access is unavailable.

---

## 3. Claim tests

```text
John says the fox died.
```

Expected:

- claim occurrence by John;
- death proposition in reported context;
- no automatic actual death transition.

```text
I saw the fox die.
```

Expected:

- user claim;
- observation claim content;
- stronger but still source-attributed evidence.

```text
The fox did not die.
```

Expected:

- opposed death proposition;
- no death effect.

---

## 4. Death and loss tests

### 4.1 Biological death

```text
The fox died.
```

Given admitted actual content:

- life status transitions to dead;
- biological life interval terminates;
- life-dependent capabilities become unavailable;
- historical capability remains queryable;
- passive external movement remains possible.

### 4.2 Modality

```text
The fox may die.
```

No actual state transition.

### 4.3 Near event

```text
The fox almost died.
```

No dead state.

### 4.4 Fiction

```text
The fox died in the story.
```

Transition occurs only in story context.

### 4.5 Polysemy

```text
The battery died.
```

Select power/operational failure, not biological life status.

```text
The company died.
```

Select organizational cessation candidate.

### 4.6 Movement distinction

```text
The dead fox moved downhill.
```

No contradiction when movement is externally caused.

### 4.7 Plant distinction

A plant death must not infer loss of self-initiated locomotion if the plant type never had that affordance.

---

## 5. Negative-axis tests

The system must distinguish:

```text
The fox did not lose its tail.   truth negation
The fox lost its tail.           relation/state loss
The fox's weight decreased.      scalar decrease
The fox cannot run.              capability unavailable
The fox must not run.            prohibition
The fox's injury is harmful.     negative valence
The fox is not important to me.  importance assessment
```

No pair may share an undifferentiated negative flag as its authoritative meaning.

---

## 6. Importance and response tests

### Case A

```text
A fox died.
```

With no user relation: factual/specific acknowledgement or silence may outrank consolation.

### Case B

```text
My fox died.
```

Ownership and harmful irreversible impact raise console candidate.

### Case C

```text
My beloved fox died.
```

Explicit affect/importance strengthens console response.

### Case D

```text
The villainous fox that attacked my chickens died.
```

Valence may be mixed; do not assume the user is grieving.

### Case E

Repeated prior discussion of the fox raises relevance only when evidence and retention policy permit.

---

## 7. Learning-first tests

### 7.1 New type

Teach:

```text
A lumin is a digital agent.
Lumins can read signals.
Lumins have a charge state.
```

After promotion and restart:

- lumin inherits digital/agent facets;
- a lumin mention can ground;
- charge state applies;
- read is an affordance;
- no live capability for a particular lumin without evidence.

### 7.2 New event

Teach:

```text
To dim means a lumin's charge becomes lower.
If charge reaches zero, reading becomes unavailable.
```

The system must learn:

- event participants;
- state decrease;
- capability dependency;
- rule class;
- lexical sense.

No custom `dim` code.

### 7.3 Counterexample

Teach an exception and verify the default is defeated without deleting the schema.

### 7.4 Cross-language lexicalization

Teach another language surface for the same event and verify identical UOL.

---

## 8. Claim-to-state safety tests

- grammatical assertion alone is not enough for high-risk actual-world state;
- reported context effects remain isolated;
- correction invalidates state/capability projections;
- multiple sources remain independently retractable;
- inference timeout never appears as a completed transition.

---

## 9. NLG tests

One grammar family must realize:

- property statements;
- state statements;
- ability lists;
- negative modality;
- past/completed events;
- impact qualification;
- targeted clarification.

Adding a new action or state value must not require a full sentence template.

English, French, and Swahili must recover equivalent UOL for shared competence cases.

---

## 10. Discourse tests

System output is semantically referable:

```text
Why?
For what?
What did you mean?
Understood what?
What happened to it?
Can it still move?
```

“it” may resolve to fox, body, death event, or proposition according to port/type/context compatibility.

---

## 11. Original demo regression

The existing chat sequence must improve for architectural reasons:

```text
hii
hi
how re u?
for what?
you are still saying things you don't understand
what can you do?
that's just pattern matching
go away
understood what?
My name is Chibu
what's my name?
```

No exact full-sequence construction is permitted.

### 11.1 Semantic contribution productivity

For synthetic vocabulary not present in canonical seeds:

1. every recognized form must preserve at least one traceable contribution or explicit compatibility path;
2. surface renaming must not alter semantic authority;
3. grammatical features remain separate from semantic targets;
4. partial query meaning preserves filler/schema/type/restriction/projection/purpose constraints;
5. no recognized contribution disappears silently.

### 11.2 Lexeme/form-family productivity

Two or more forms may share one lexeme and one semantic authority while carrying distinct grammatical features.

The competence case must not require direct form-sense links.

### 11.3 Targetless contribution authority

A lexical sense may be usable without a dummy target only when active reviewed semantic-contribution specs close its permitted use.

### 11.4 Interrogative separation

Information gap, query variable, answer projection, discourse act and response obligation are separate.

An embedded interrogative must not automatically produce `discourse-act:ask`.

### 11.5 Referent-driven closure

Using identical grammar/lexical authority, changing only grounded referent type must change compatible state/property/action candidates through type/facet entitlement.

### 11.6 Catalogue cardinality is not competence

Release tests must not require exact counts of response policies, response transforms, argument frames, lexical senses, constructions or morphology rules as proof of semantic competence.

Deterministic counts/fingerprints are permitted only for explicit source-tamper/integrity tests.

### 11.7 Productive input morphology

An unseen surface form may be analyzed only through reviewed morphology authority.

The competence case must prove:

1. the surface form itself is absent from durable `LanguageFormRecord` authority;
2. a reviewed morphology rule recovers an exact lexeme revision;
3. grammatical features remain evidence and do not invent semantic targets;
4. no regex/word-specific semantic branch participates;
5. exact/irregular reviewed forms override productive class analysis while remaining traceable.

### 11.8 Construction semantic programs

Ordinary compositional constructions must build semantic graph fragments through
bounded declarative construction programs.

The kernel executor must not contain language-specific construction names or
predicate names.

`metadata.interpretation_enabled` is not authoritative for newly reviewed
construction programs.

### 11.9 Predication/eventuality productivity

Synthetic renamed constructions must distinguish compatible
state/property/relation predication and dynamic eventuality readings through
schema/aspect/type constraints, not through English BE or adjective/adverb checks.

### 11.10 Participant grounding

Speaker/addressee lexical contributions bind through `ParticipantFrame` role
anchors. Renaming the surface pronouns must preserve the same role-grounding
behavior.

### 11.11 Referent-driven semantic closure

Stage 4 must export exact schema/referent closure candidates to Stage 5.

Changing only grounded referent type/entitlement/state/capability knowledge must
be able to change candidate semantic closure.

Surface-span equality must not be semantic compatibility authority.

### 11.12 Signed release artifacts after record-kind expansion

Any phase that adds `RecordKind` values must regenerate the signed runtime-authority
manifest, boot database and verification report through deterministic release
tooling.

Tests must not weaken `RuntimeAuthorityGuard` exact record-kind equality.

---

## 12. Final release gate

The release is rejected if any passing test depends on:

- an exact phrase patch;
- a hard-coded event effect;
- a canned generic response;
- a predicate-specific sentence;
- a source-code type addition;
- unproved state or impact;
- learned data unavailable after restart.
