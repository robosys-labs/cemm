# CEMM v3.4 — Minimal Semantic Foundations

## 1. What is native

CEMM must not natively assume domain concepts such as:

```text
person
animal
human
leader
president
engineer
software agent
organization
```

These are audited boot or learned schemas.

The native substrate is smaller and formal.

### Representation primitives

Already present in v3.4:

```text
Referent
Value
Predication
Proposition
ContextFrame
EvidenceRecord
StructuralLink
```

They specify how meaning is represented, not what a domain concept means.

### Kernel value foundations

```text
boolean
enum
text
quantity + unit
identifier
set
sequence
time point / interval
coordinate / reference frame
probability / distribution
```

### Executable foundational relations

The smallest release-specific set should provide implemented type signatures, identity rules, query behavior, and inference behavior for:

```text
same_identity / different_identity
instance_of
occupies_role
participates_in
has_state
occurs / transitions
located_at
before / after
depends_on
causes / enables / prevents
refers_to / represents
```

They are foundational because their behavior is implemented and tested, not because their English labels are presumed understood.

## 2. Audited boot schemas

Useful starting concepts such as `physical_entity`, `biological_entity`, `person`, `agent`, `software_system`, `organization`, `place`, and `information_object` may be supplied at boot.

They are not kernel primitives. Each must have:

```text
ordinary schema representation
explicit definition dependencies
boot provenance
grounding/competence specification
activation validation
```

This terminates learning regress honestly: CEMM starts with an audited, testable semantic basis rather than pretending to learn every concept from an empty graph.

## 3. Grounding anchors

A definition dependency may terminate in:

1. a kernel representation/value primitive;
2. an executable foundational relation;
3. an adapter-observed schema with a registered observation contract;
4. an audited active boot schema;
5. an already grounded active learned schema.

A familiar word is not an anchor by itself.

## 4. Why a raw fact count is wrong

These may be two assertions but zero additional meaning:

```text
A leader leads.
Leading is what a leader does.
```

Likewise:

```text
A leader is a chief.
A chief is a leader.
```

Grounding depends on compositional closure and discrimination, not count.

## 5. Concept decomposition without ontology bloat

CEMM does not require every concept to be decomposed into a universal philosophical ontology.

It requires enough executable structure to support the selected competencies:

```text
recognize or reject candidate use
bind required roles
query defining properties/relations
distinguish from parent or alternatives
perform licensed inference
preserve context, polarity, and time
realize an evidence-bound explanation
```

The required depth is goal- and schema-dependent, but activation has a fixed minimum contract.
