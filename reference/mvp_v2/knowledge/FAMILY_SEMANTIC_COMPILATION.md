# Family teaching → compressed semantic knowledge

This file explains how the example teaching statements are represented without adding domain-specific schemas.

## Teaching 1

> A mother in-law is a family relative.

Compiled as relation hierarchy data:

```text
relation(
  subject  = rel:mother_in_law,
  relation = rel:subrelation_of,
  object   = rel:family_relative
)
```

A single generic `subrelation-inheritance` rule applies this and every future subrelation definition.

## Teaching 2

> A mother in-law is the mother of a partner.

This is not a simple subtype relation. It is a compositional relational definition:

```text
mother_in_law_of(M, Person)
  => exists Partner:
       mother_of(M, Partner)
       AND partner_of(Partner, Person)
```

This is the only family-specific compositional rule needed for the target inference.

## Teaching 3

> A partner is a lawful wedded husband/wife.

For this learned vocabulary, `partner` is represented as a subrelation of `spouse`:

```text
partner subrelation_of spouse
```

The runtime reasons according to the learned premise. In broader real-world usage, *partner* can include unmarried partners; that distinction would require different scoped evidence/definitions rather than changing the kernel.

## Teaching 4

> A wife is a female human old enough for marriage.

Compressed as reusable semantic data:

```text
wife subrelation_of spouse
subject_type(wife, female)
wife implies_subject_state marriage_eligible
```

Shared type lattice:

```text
female IS_A human
human  IS_A living_entity
```

Shared state-effect specification:

```text
marriage_eligible:
  dimension = marriage_eligibility
  value     = eligible
```

## Teaching 5

> A husband is male human old enough for marriage.

Same generic machinery:

```text
husband subrelation_of spouse
subject_type(husband, male)
husband implies_subject_state marriage_eligible

male  IS_A human
human IS_A living_entity
```

## Shared spouse consequence

Rather than separate wife/husband/partner marriage rules:

```text
spouse implies_subject_state married
spouse implies_object_state  married

married:
  dimension = marital_status
  value     = married
```

Two generic relation→state rules execute these specifications.

## Target reasoning

Observation:

```text
mother_in_law_of(M, user)
arrival_event(E, M, today)
```

Inference:

```text
mother_in_law_of(M,user)
 -> exists P: mother_of(M,P) + partner_of(P,user)
 -> spouse_of(P,user)                     [subrelation]
 -> married(user)                         [generic object-state effect]
```

No `MotherInLawSchema`, `MarriageSchema`, `WifeSchema`, or concept-specific Python branch is created.
