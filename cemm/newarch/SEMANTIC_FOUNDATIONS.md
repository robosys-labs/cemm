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

### Epistemic self-foundations

The organism's claims about its own mind must be as grounded as its claims about the world. The executable foundational set therefore also includes, with implemented truth and query behavior:

```text
remembers(self, record)
has_evidence_for(self, proposition, ledger_ref)
understands(self, schema_revision, competence_set, scope)
uncertain_about(self, target, blocker_set)
```

`self` is an audited boot schema with kernel-backed identity. A self-report may be realized only from these derived, queryable records — never from response templates. If the epistemic relation cannot be derived, the honest output is uncertainty, not a fluent claim.

### Pattern expressiveness minimum

`SemanticPattern` is not limited to positive atomic conditions. To represent real definitions it must minimally express:

```text
negation           — a bachelor is not married
cardinality        — at most one president per institution
bounded quantification — over declared role fillers, not open-world domains
modality           — can/must/may distinctions in constitutive behavior
temporal/aspectual scope — while in office; upon completion
```

Each construct carries defined truth, query, and contradiction behavior. A definition that needs an unsupported construct produces a concrete expressiveness blocker — it is not silently approximated by dropping the construct.

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

### 2.1 Boot validation failure policy

Startup validation executes each audited boot schema's grounding specification and competence cases. Failure handling is tiered:

- a failed kernel value primitive or executable foundational relation halts boot — the substrate itself is defective;
- a failed audited boot concept loads as `partial`/`opaque` usability, its failure is journaled, and dependent boot schemas downgrade through the ordinary assessment cascade;
- boot never silently activates a failing schema and never fabricates a passing assessment.

### 2.2 Contradicting a boot schema

A user assertion that contradicts an audited boot schema is ordinary contradiction evidence — boot provenance is not immunity from revision.

It may add context restrictions, exceptions, or session/user-scoped revisions through the normal learning transaction. It may not silently supersede boot provenance at global scope; revising a boot schema above user scope follows the standard promotion policy with independent supporting evidence.

## 3. Grounding anchors

A definition dependency may terminate in:

1. a kernel representation/value primitive;
2. an executable foundational relation;
3. an adapter-observed schema with a registered observation contract;
4. an audited active boot schema;
5. an already grounded active learned schema.

A familiar word is not an anchor by itself.

### 3.1 Adapter contract drift

An adapter-observed anchor is only as sound as its observation contract. Each registered contract carries verification cases that are re-run on adapter change and periodically per policy. A failing contract downgrades the adapter-observed schema — and its dependents — through the ordinary assessment cascade. An adapter is evidence infrastructure, not an unauditable oracle.

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
