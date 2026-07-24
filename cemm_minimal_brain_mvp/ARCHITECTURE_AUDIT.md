# CEMM Minimal Semantic Brain — Deep Architecture Audit

## Executive conclusion

The previous MVPs solved several surface problems but still risked architectural growth in three ways:

1. every domain predicate could acquire its own port schema;
2. inferred consequences could become duplicated durable facts;
3. increasingly detailed definitions could turn into one-off concept rules instead of reusing shared semantic operations.

This revision changes the center of gravity.

The database schema now has **five invariant semantic operator shapes** and **twenty invariant role declarations**. Importing the family domain changes neither count. Deeper knowledge grows as atoms, exact applications, rules and evidence.

```text
5 operators before family import  -> 5 after
20 operator roles before          -> 20 after
```

The domain can grow without adding a `MotherInLawSchema`, `SpouseSchema`, `MarriageSchema`, `PresidentSchema`, etc.

---

# 1. Do not confuse an entity with a relational role

A critical modeling correction is:

> `mother-in-law` should not be represented as a simple subtype of `mother` over the same target.

The woman is an entity. `mother`, `mother-in-law`, `wife`, `husband`, `partner`, and `spouse` are relational roles that an entity may occupy relative to another referent.

Naive modeling:

```text
mother_in_law(X) IS_A mother(X)
```

is semantically insufficient because motherhood is relational.

Correct compositional meaning:

```text
mother_in_law_of(M, Person)
    => exists Partner:
         mother_of(M, Partner)
         AND partner_of(Partner, Person)
```

This is the one genuinely family-specific compositional rule needed for the example.

Everything downstream is reused generic machinery.

---

# 2. Fixed universal semantic algebra

The runtime uses only:

```text
op:designation(target, label_type, surface, language, ...)
op:type(instance, class)
op:relation(subject, relation_type, object)
op:state(subject, dimension, value)
op:event(event, event_type, actor?, time?)
```

These are not domain predicates. They are invariant semantic shapes.

Domain meaning is represented as fillers:

```text
rel:mother_in_law
rel:mother_of
rel:partner
rel:spouse
concept:female
concept:human
concept:living_entity
dim:marital_status
value:married
event:arrive
time:today
```

Adding more domain depth therefore adds atoms and relationships, not schema classes.

---

# 3. Reusable meta-relations compress definitions

Instead of storing many concept-specific rules:

```text
partner -> spouse
wife -> spouse
husband -> spouse
mother -> female
wife -> female
husband -> male
female -> human
human -> living
spouse -> married
...
```

this MVP factors recurring logic into a few generic rules.

## 3.1 Subrelation inheritance

Stored data:

```text
mother_in_law subrelation_of family_relative
partner       subrelation_of spouse
wife          subrelation_of spouse
husband       subrelation_of spouse
```

One generic rule:

```text
subrelation_of(R1,R2) AND R1(X,Y)
    => R2(X,Y)
```

Any future relation hierarchy reuses the same rule.

## 3.2 Participant type constraints

Stored data:

```text
subject_type(mother_of, female)
subject_type(wife,      female)
subject_type(husband,   male)
```

One generic rule:

```text
subject_type(R,C) AND R(X,Y)
    => type(X,C)
```

## 3.3 Type lattice

Stored facts:

```text
female IS_A human
male   IS_A human
human  IS_A living_entity
```

One generic transitivity rule:

```text
type(X,A) AND type(A,B)
    => type(X,B)
```

So `mother_of(M, P)` needs to derive only `female(M)`. The rest is shared lattice reasoning.

## 3.4 Relation-to-state effects

State effects are also data-described.

```text
spouse implies_subject_state spec:married
spouse implies_object_state  spec:married

spec:married state_dimension marital_status
spec:married state_value     married
```

Two generic rules project relation effects to subject/object state.

The same mechanism handles marriage eligibility for wife/husband and can later represent any relation-conditioned state consequence without another predicate schema.

---

# 4. Exact proof for the requested example

Observation:

```text
My mother in-law arrived today.
```

The learned language codec produces only structural output:

```text
new @X0 entity
new @X1 event

op:relation(
    subject  = @X0,
    relation = mother_in_law,
    object   = user
)

op:event(
    event = @X1,
    type  = arrive,
    actor = @X0,
    time  = today
)
```

The program itself contains no family constants; those arrive through grounded placeholders.

Question:

```text
Am I married?
```

Query:

```text
op:state(
    subject = user,
    value   = married
)
```

Inference proof:

```text
OBSERVED
mother_in_law_of(M,user)

rule:mil-decompose
    exists P:
      mother_of(M,P)
      partner_of(P,user)

GENERIC rule:subrelation-inheritance
    partner subrelation_of spouse
    => spouse_of(P,user)

GENERIC rule:relation-object-state
    spouse implies_object_state married
    => state(user, marital_status, married)

ANSWER
Yes.
```

The existential partner is proof-bearing but unnamed. CEMM can conclude that a spouse exists without pretending to know that person's identity.

---

# 5. Inference does not become data bloat

A common graph-system failure is eager materialization:

```text
1 observed fact
-> 20 inferred facts written to DB
-> each new rule expands them again
-> replay / invalidation becomes enormous
```

This MVP does not do that.

Durable store:

```text
observations
reviewed/learned exact applications
claims/evidence
rules
```

Query-time semantic closure:

```text
ephemeral derived facts
proof lineage
bounded by max rounds + max facts
```

After ten repeated `Am I married?` queries, the demo shows identical persistent counts:

```text
applications: 54 -> 54
bindings:     281 -> 281
claims:        54 -> 54
proof_links:   54 -> 54
rules:          7 -> 7
```

The exact semantic snapshot hash also remains unchanged.

Derived knowledge should be materialized only through a deliberate consolidation/promotion policy, not as a side effect of asking questions.

---

# 6. Causality does not require another schema family

Rules use one representation with an explicit rule category:

```text
definition
entailment
causal
default
```

Actual-world query closure executes only:

```text
definition + entailment
```

A stored causal rule such as:

```text
arrival(X) -> presence(X)
```

is **not** silently asserted as observed truth.

A future simulator can evaluate `causal` rules in a hypothetical/simulated context using the same atoms/operators/rule substrate. Deeper causal modeling adds mechanisms/rules/data, not new tables for every causal concept.

---

# 7. Rule growth is controlled

Rules are executable knowledge, but rule storage itself can bloat if semantically identical rules are saved under multiple names.

This revision enforces:

```text
UNIQUE(rule_kind, antecedent, consequent)
```

and import-time semantic deduplication.

Rule admission also rejects:

- empty antecedents/consequents;
- out-of-range confidence;
- existential variables in antecedents;
- unbound consequent variables;
- unknown operators/roles/constants;
- wrong filler semantic kinds;
- missing required consequent roles.

Thus detailed learning grows a reusable rule graph rather than an unchecked script repository.

---

# 8. Language models cannot create new ontology classes casually

The Transformer may emit:

```text
new @X0 entity
new @X1 event
```

but only structural kinds explicitly declared in data as creatable are accepted.

Current allowed set:

```text
entity
event
```

The learned codec cannot output:

```text
new @X0 mother_in_law_schema
new @X1 arbitrary_new_kind
```

and silently grow the ontology/kernel.

New domain concepts/relations should be learned through reviewed semantic atoms/rules and promotion, not by allowing the surface codec to mint structural categories.

---

# 9. Universal roles are semantically typed

The previous MVP allowed too many `atom` fillers.

This revision enforces stable structural constraints such as:

```text
op:type.role:class       -> concept
op:relation.role:relation-> relation_type
op:state.role:dimension  -> state_dimension
op:state.role:value      -> value
op:event.role:event      -> event
op:event.role:type       -> event_type
op:event.role:time       -> time
```

This prevents a learned model from placing, for example, a `doctor` concept into the relation-type slot simply because both are atoms.

These constraints are universal and remain constant as domains grow.

---

# 10. Entity identity and multilingual labels remain separated

Canonical designations are ordinary `op:designation` semantic applications.

`designation_index` is only a materialized lookup projection.

One identity may have:

```text
full name
surname
alias
localized name
language-invariant name
```

Multiple identities may share exactly the same surface label.

Dynamic evidence:

```text
usage count
discourse salience
```

may rank candidates but does not change exact semantic identity or snapshot hashes.

Same-name regression:

```text
Alex Kim -> ambiguous between two exact identities
Alex J. Kim -> resolves one
later Alex Kim -> discourse evidence may rank that identity
```

---

# 11. Pronouns use semantic meaning, not a second metadata ontology

A previous revision resolved `she/he` primarily through `gender` metadata.

This revision uses reference-form semantic constraints:

```text
she -> required_type = female
he  -> required_type = male
```

Candidate referents are checked against inferred `op:type` closure.

Therefore after only:

```text
My mother in-law arrived today.
```

CEMM can infer:

```text
mother_of -> female -> human -> living_entity
```

and then resolve:

```text
Is she a human?
-> Yes.

Is she a living entity?
-> Yes.
```

No durable `mother_in_law_is_human` fact is stored.

---

# 12. Multilingual interfaces share one meaning graph

The family rules and exact semantic applications contain no English grammar.

English observation:

```text
My mother in-law arrived today.
```

Spanish query over that same stored graph:

```text
¿Estoy casado?
-> Sí.
```

Spanish can also learn:

```text
Mi suegra llegó hoy.
```

using Spanish designation/reference evidence and the same semantic program.

No Spanish copy of the family ontology exists.

---

# 13. State truth maintenance — minimal but generic

State dimensions can declare:

```text
exclusive = true
```

When a new exact state is committed for the same subject/dimension with a different value, previous active claims are closed using `valid_to`.

This provides a small generic fluent-replacement mechanism without state-specific Python branches.

It is not yet a complete temporal reasoner.

---

# 14. What this MVP fixes from the earlier design

Closed or substantially improved:

1. Domain-specific predicate/schema expansion.
2. Labels as privileged identity fields.
3. Same-name forced merging.
4. English-only semantic authority.
5. Runtime natural-language regex meaning rules.
6. Exact realization templates as primary generator.
7. Missing semantic inverse verification for realization.
8. Inference-by-materializing every consequence.
9. Concept-specific type chains.
10. Concept-specific subrelation rules.
11. Concept-specific relation-to-state rules.
12. Causal rules mixed with ordinary truth entailment.
13. Duplicate semantically identical rules.
14. Unchecked rule variables/constants.
15. Model-created arbitrary structural kinds.
16. Untyped universal role fillers.
17. Pronoun resolution dependent only on identity metadata.
18. Unknown treated as false.
19. Generic exclusive-state supersession missing.
20. Replay/generation semantic hash instability from dynamic statistics.

---

# 15. Remaining critical boundaries — explicitly not hidden

## A. Natural-language rule induction is not solved

The five family teaching sentences are represented in `family_knowledge.json` as the **already learned semantic result**.

This MVP proves:

```text
learned reusable definitions
+ new observation
+ generic inference
-> answer with proof
```

It does not yet prove unrestricted language:

```text
"A mother in-law is the mother of a partner"
-> autonomously induce a quantified existential rule
```

That is a separate induction/promotion problem and should not be faked with phrase regexes.

## B. The tiny Transformer remains topology-limited

It learns a small number of delexicalized structural mappings. It is not a general multilingual language model.

The production path should produce N-best semantic graph candidates and recurrently settle them.

## C. Existential/referent identity remains conservative

The inference engine can prove that an unnamed partner exists without assigning a real identity.

Robust entity merging/splitting across repeated relational descriptions requires richer identity evidence and should prefer ambiguity over false merging.

## D. Causal simulation is separated but not executed

`causal` rules are stored safely and excluded from actual-world entailment. A counterfactual/simulation context engine is still needed.

## E. Learning promotion remains simplified

Needed production lifecycle:

```text
frontier
-> evidence
-> candidate rule/atom
-> counterexamples + competence tests
-> scoped promotion
-> content-addressed authority generation
-> replay/invalidation
```

## F. Temporal reasoning is only minimal

Exclusive state replacement works. General intervals, persistence, before/after event transitions and temporal contradiction resolution remain future work.

## G. Rule representation is an executable index

Rules are stored as normalized antecedent/consequent structures. A fuller canonical system may represent rule definitions themselves as meta-CSIR and materialize the current `rules` table as an execution index.

---

# 16. Regression suite

The bundle has 21 passing tests covering:

- no family/domain hardcoding in Python;
- no operator/schema growth after domain import;
- family observation -> marriage proof;
- repeated inference does not persist closure;
- causal rule does not become actual truth;
- mother role reuses type lattice;
- wife semantics reuse generic subrelation/type/state effects;
- same-name ambiguity and discourse ranking;
- designations as semantic facts, dynamic ranking outside authority;
- multi-sentence coreference;
- semantic-type-driven pronoun resolution;
- multilingual family inference;
- surface variants converge through shared lexical atoms;
- learned language program contains only foundational structure;
- role semantic-kind validation;
- generic exclusive-state supersession;
- replay-stable semantic hash;
- semantically duplicate rule deduplication;
- unsafe rule variable rejection;
- restricted model-created structural kinds;
- unknown is not false.

---

# Final invariant

```text
KERNEL
  5 universal operators
  fixed universal roles
  exact validation + identity
  bounded generic rule engine

KNOWLEDGE
  atoms
  designations
  exact applications
  definitions / entailments / causal rules
  type lattices
  relation hierarchies
  state-effect specifications

DYNAMIC PLANE
  Transformer evidence
  entity/reference ranking
  discourse salience
  bounded ephemeral closure

QUERY
  derive only what is needed
  retain proof lineage
  do not persist closure by default

RESPONSE
  Response meaning
  learned realization
  inverse semantic verification
  emit
```

The central anti-bloat principle is:

> **New knowledge should usually add reusable atoms, facts, or rules inside the existing algebra. New schema should be exceptional. Derived consequences should usually remain ephemeral until there is an explicit reason to consolidate them.**
