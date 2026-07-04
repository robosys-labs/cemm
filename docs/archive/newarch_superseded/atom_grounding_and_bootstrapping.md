# Atom Grounding And Bootstrapping

Purpose: clarify whether concepts like `person`, `country`, `organization`, and `office_role` are native primitives or dynamically built atoms.

## 1. Short Answer

CEMM should not natively hardcode `country`, `organization`, `person`, `leader`, `president`, or `office_role` as kernel primitives.

The kernel only natively knows the primitive **atom kinds**:

```text
entity
process
state
relation
quality
quantity
time
place
intent
need
modality
evidence
source
permission
action
self
```

Everything else is a **concept atom** or **schema atom** inside the concept lattice.

So:

```text
person       = EntityAtom concept
country      = EntityAtom concept
organization = EntityAtom concept
office_role  = EntityAtom/RelationAtom concept
leader       = EntityAtom role concept
president    = EntityAtom office-role concept
```

They are not fundamental CPU instructions. They are learned or seeded semantic circuits.

## 2. Kernel Primitive vs Concept Atom

| Layer | Example | Fixed? | Purpose |
|---|---|---:|---|
| Kernel atom kind | `entity` | yes | Fundamental representation category. |
| Concept atom | `person` | no | Learned/seeded concept in lattice. |
| Role concept | `leader` | no | Concept with operational ports and affordances. |
| Specialized role | `president` | no | Concept inheriting from role/institution concepts. |
| Predicate schema | `leads(domain)` | no | Reusable executable relation/process. |
| Causal affordance | `decision -> policy_change` | no | Learned/proposed effect schema. |

The kernel provides the **grammar of meaning**.

The concept lattice provides the **learned vocabulary of reality**.

## 3. Bootstrapping

CEMM starts with a tiny seed lattice, not a complete ontology.

Seed atoms exist only to let the system begin interpreting:

```text
self
user
thing
person_candidate
group_candidate
place_candidate
time_candidate
source
claim
state
action
relation
```

From there, CEMM builds richer concepts by repeated graph evidence:

```text
surface patterns
dictionary entries
Wikipedia/source lookups
user teaching
conversation transcripts
repairs/corrections
cross-context predicate use
```

The bootstrapping loop:

```text
observe surface use
-> create candidate concept atom
-> attach source/evidence
-> infer parent atoms
-> infer ports
-> infer acceptable predicates
-> infer causal affordances
-> consolidate or decay
```

## 4. What Is `person`?

`person` is not a hardcoded type. It is a high-confidence concept atom.

Possible concept structure:

```text
person:
  kind: entity_concept
  parents:
    animate_entity
    social_agent
  ports:
    name: lexical_identifier
    body: physical_entity
    mind/state: state_holder
    role: social_role
    location: place
    time_scope: time
  predicates:
    speaks()
    knows()
    wants()
    acts()
    owns(entity)
    located_at(place)
  causal_affordances:
    need -> intent
    belief -> action_choice
    physical_harm -> health_decrease
```

The system may begin with `person_candidate`, but `person` becomes strong through use and source support.

## 5. What Is `country`?

`country` is also a concept atom, not a primitive.

Possible concept structure:

```text
country:
  kind: entity_concept
  parents:
    political_entity
    place_domain
    group_container
  ports:
    territory: place
    population: group/person
    government: organization
    leader_role: office_role
    law_system: institution
    time_scope: time
  predicates:
    has_capital(place)
    has_population(quantity)
    governed_by(entity/person/org)
    located_in(place)
  causal_affordances:
    government_policy -> population_state_change
    conflict -> stability_decrease
```

The important thing is that `country` is explainable:

```text
country -> political_entity -> group + territory + governance
```

## 6. What Is `organization`?

```text
organization:
  kind: entity_concept
  parents:
    group
    institution
  ports:
    members: person/group
    purpose: intent/process
    authority_structure: relation
    resources: entity
    location: place
  predicates:
    employs(person)
    owns(entity)
    provides(process/service)
    governed_by(person/group)
```

This lets CEMM understand that a company, church, bank, school, and government agency share structure without being the same concept.

## 7. What Is `office_role`?

`office_role` is not a primitive. It is a role concept whose holder can change over time.

```text
office_role:
  kind: role_concept
  parents:
    social_role
    institutional_role
  ports:
    holder: person/group
    institution: organization
    domain: organization/country/group
    authority_scope: relation/process
    time_scope: time
  predicates:
    held_by(holder, time_scope)
    belongs_to(institution)
    authorizes(action)
  freshness:
    current holder requires fresh evidence
```

Then:

```text
president inherits office_role
president inherits leader
```

Now `president` can be resolved without bespoke code.

## 8. President Example

When CEMM sees:

```text
Donald Trump is the current president of the USA
```

It should not run:

```text
if word == president:
    use president schema
```

It should run:

```text
surface "president"
-> candidate atom president
-> president inherits office_role and leader
-> office_role opens holder/domain/time_scope ports
-> "Donald Trump" binds holder
-> "USA" binds domain
-> "current" binds time_scope
-> current holder relation triggers fresh evidence policy
```

Result:

```text
Relation(holds_office)
  holder = Donald Trump
  office = president
  domain = USA
  time_scope = current
  evidence_policy = fresh_required
  source = user_assertion
```

The user can teach it, but authoritative use needs freshness.

## 9. Dynamic Growth

Concepts deepen over time.

Initial:

```text
president: unknown entity/role candidate
```

After teaching:

```text
president is_a leader
president domain country
```

After transcript/source exposure:

```text
president inherits office_role
president has holder/domain/time_scope
current president requires fresh evidence
president can govern/represent/lead
```

After causal consolidation:

```text
president decision may cause policy change
election may change holder
term end may change holder
```

No database explosion is needed. The atom becomes more operationally complete.

## 10. Design Rule

CEMM may ship with seed atoms.

But every seed atom must be:

```text
inspectable
overrideable
learnable
explainable through more basic atoms
compressible into the same lattice as learned atoms
```

No concept outside the kernel atom kinds should be permanently magical.
