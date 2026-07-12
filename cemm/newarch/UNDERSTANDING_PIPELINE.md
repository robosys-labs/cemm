# CEMM v3.4 — Final Reliable Understanding Pipeline

This document strengthens the existing `UNDERSTAND` stage. It adds no top-level cognitive stage, ontology engine, or competing schema authority.

## 1. Required output of understanding

For each selected meaning group, understanding must preserve:

```text
surface evidence
candidate lexical senses
candidate schema/sense refs
predications and propositions
referent and role bindings
context, polarity, modality, time, and place
schema grounding assessment
context/operation-specific SchemaUseProfile
open ports and blockers
source/evidence lineage
```

A known spelling or schema reference is not an understood meaning.

## 2. Perceive: one reversible language stream

Language adapters emit:

```text
raw form and exact offsets
normalized form without destroying raw form
lemma and morphology candidates
contraction decomposition
quotation, negation, clause, and modality boundaries
syntax/dependency evidence
candidate lexical senses
language and confidence
```

Apostrophes and quotation boundaries must survive. Different tokenizers may not create incompatible canonical forms.

Unknown content is never converted into a generic entity, role marker, or durable concept fact merely to keep the pipeline moving.

## 3. Compose: preserve alternatives

`SemanticComposer` creates separate candidates for:

```text
lexical sense
schema family
predication/proposition structure
communicative force
role bindings and open ports
embedded propositions
context/world
source evidence
```

Whole-turn construction and pragmatic cues may add candidates or discourse relations. They may not replace compositional content.

For an opaque lexeme, composition creates a lexical reference and one or more provisional candidate sense clusters. It does not assume that identical spellings share one schema.

## 4. Ground referents and definitions separately

`GroundingResolver` answers two distinct questions.

### 4.1 Referent grounding

```text
What is being mentioned?
Is it an instance, schema/sense referent, lexical form, value,
predication, proposition, place, time, or context?
What is its discourse/durable identity?
```

### 4.2 Definition grounding

```text
Which exact schema revision could define this sense?
What schema family is hypothesized?
Are required definition fields present?
Are semantic patterns expressible?
Are dependencies valid and grounded?
What recursive-cycle semantics apply?
What competence has actually been demonstrated?
```

### 4.3 Epistemic/contextual admissibility

Structural closure does not determine truth. `EpistemicEvaluator` decides whether the definition claims are:

```text
admitted in actual context
admitted only in a domain/time context
attributed to a user/source
contested
blocked
```

### 4.4 SchemaUseProfile

The resolver derives a use profile by intersecting structural, competence, admissibility, scope/access, and requested-operation results.

A schema may be:

```text
opaque:
  quote, preserve attributed assertion, search, probe

partial/provisional:
  typed reference, compose under qualification, query the supplied theory,
  contrast provisionally, explain exact blockers

active/admitted:
  recognize, classify, answer defining queries, and perform licensed inference
  in the admitted contexts

causal/effect interpretable:
  predict/simulate/propose only; never execute without live authorization
```

## 5. Scope is not truth precedence

`session > user > domain > global` is not a blanket semantic shadowing rule.

Resolution proceeds in this order:

1. determine the intended sense;
2. determine epistemic world/context;
3. filter domain and valid time;
4. check access scope;
5. compare explicit supersession/override relations;
6. evaluate structural usability and epistemic admissibility;
7. select the revision appropriate for the requested operation.

A user-defined meaning may be used for “what do you mean by X?” without replacing actual-world meaning for “what is X?”

## 6. Field-level honesty

Every candidate schema contribution records:

```text
asserted
observed
entailed
inherited
hypothesized
defaulted
induced
adapter-supplied
boot-supplied
```

Example:

```text
User: A leader directs a group.
```

The user asserted a `directs` pattern. A role-like schema family, an occupancy pattern, or a bearer constraint may be reasonable hypotheses derived from grounded predicate signatures, but they are not user assertions.

The response planner must preserve that distinction.

## 7. Sense individuation

A lexical form may map to several senses and schema families.

### Split evidence

Create a new candidate sense or ambiguity set when evidence is structurally incompatible by:

```text
schema family
role/bearer constraints
strict constitutive patterns
context/domain
metonymic projection
```

### Merge evidence

Merge/alias requires an explicit reversible identity assessment with compatible structure or a grounded synonym/translation claim.

A merge never deletes original refs; it records equivalence/redirect provenance so historical readings remain interpretable.

### Opaque homonyms

When both uses are opaque, compatibility may be unknown. Keep separate candidate sense clusters and reversible evidence assignments rather than merging by spelling.

## 8. Grounded Definition Closure

A schema revision is structurally executable only when:

1. semantic family is resolved;
2. family-required fields are complete;
3. required roles and value types are typed;
4. required semantic constructs are expressible;
5. definition dependencies terminate in executable foundations or valid grounded schemas;
6. at least one permitted constitutive/identity pattern explains membership or occurrence;
7. specialization has a differentiator unless explicitly an alias/synonym;
8. recursive dependency components have supported semantics;
9. query, contradiction, role, and context behavior can be instantiated;
10. structural competence tests pass.

Typical/default/incidental patterns never satisfy a constitutive requirement by themselves.

## 9. Recursive definition components

Classify every strongly connected definition component:

```text
inverse relation
positive monotone
stratified defeasible
unsupported non-monotone
```

Direct joint activation requires:

- at least one external grounded anchor per required role path;
- non-redundant constitutive contribution from every member;
- total/type-consistent role mapping;
- declared inverse or least-fixed-point semantics;
- independent joint competence;
- no forbidden dependency through effect authorization, permission, destructive update, identity collapse, or cardinality replacement.

The component activates atomically or remains provisional.

## 10. Competence without self-certification

Competence checks are non-mutating and sandboxed.

Minimum generic checks:

```text
compose a positive case
preserve required role/context/polarity structure
answer a defining query
distinguish a real contrast or alternative
perform a licensed inference
realize/reparse where language resources exist
```

### 10.1 Lineage rules

Each case records input generation lineage and oracle lineage.

- a case derived from the teaching utterance tests structure only;
- translations/paraphrases/generated examples inherit the same lineage;
- negative cases cannot pass from missing evidence alone;
- independent discrimination uses an audited invariant, independently grounded sibling/contrast, adapter observation, or independently authored expected pattern;
- the same implementation path cannot generate input meaning, expected graph, and pass judgment without an independent invariant.

### 10.2 Open-world negative cases

Contrast evaluation uses:

```text
supported
refuted
both
neither
```

`neither` is not rejection. A negative case passes only when the candidate schema derives an incompatibility or a better alternative.

## 11. Resolve

`InterpretationResolver` may select an opaque/provisional interpretation when sufficient for the current goal, such as quotation, memory, attributed report, correction, or learning.

It may not use an inadmissible/opaque meaning for:

```text
actual-world inheritance
strong classification
causal/effect claims
state mutation
unqualified definition answers
unqualified self-understanding claims
selectional rejection
```

Rejected branches emit no effects, writes, or durable schema changes.

## 12. Evidence-bound self-report

Self-report queries use ordinary semantic retrieval over:

```text
remembered proposition
schema grounding assessment
competence results
admissibility assessment
current blockers
capability/component evidence
```

Truthful outputs distinguish:

```text
I remember your statement.
I can use your definition provisionally in this conversation.
I can recognize/query these cases.
I have not independently validated it.
I do not currently have enough structure to understand it.
```

An unbacked epistemic clause is a realization error.

## 13. Gap detection

A gap exists only when missing structure blocks a selected goal.

Required blocker vocabulary includes:

```text
missing_semantic_family
missing_definition_field
missing_required_role
missing_value_type
missing_constitutive_pattern
missing_differentiator
ungrounded_dependency
unsupported_recursive_cycle
missing_independent_competence
actual_context_not_admitted
expressiveness_blocker
sense_individuation_pending
stale_assessment
```

Known surface form never suppresses a structural gap.

## 14. Output contract

Understanding returns immutable candidates and assessments. It performs no persistent mutation, schema activation, external action, or response wording.
