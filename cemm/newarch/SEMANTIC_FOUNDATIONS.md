# CEMM v3.4 — Final Minimal Semantic Foundations

The kernel must start with enough executable structure to represent and test meaning without pretending that familiar domain words are primitives.

## 1. Native representation substrate

Canonical semantic object families remain:

```text
Referent
Value
Predication
Proposition
ContextFrame
EvidenceRecord
StructuralLink
```

No domain concept such as `person`, `animal`, `leader`, `president`, `engineer`, `organization`, or `software agent` is a kernel object type.

## 2. Kernel value foundations

The release implements typed behavior for:

```text
boolean
enum
text
identifier
quantity + unit
set
ordered sequence
time point and interval
coordinate and reference frame
probability/distribution
```

Each type has canonical identity, normalization, comparison, query, contradiction, serialization, and public-surface rules.

## 3. Executable foundational predicates

The smallest audited set should include implemented type signatures, truth/query behavior, and inference contracts for:

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

These labels are not assumed to explain themselves. Their kernel semantics and property tests make them foundational.

## 4. Epistemic and learning foundations

Self-capability and learning require executable predicates over ordinary records:

```text
remembers(self, record)
has_access_to(self, record)
has_evidence_for(self, proposition, evidence)
understands(self, schema_revision, competence_set, context)
uncertain_about(self, target, blocker_set)
means(lexical_form, schema_sense)
defines(source, schema_revision, proposition)
learns(self, artifact, evidence)
```

`learns` is derived from committed artifact change and validated use. It is not triggered by a teaching utterance alone.

## 5. Audited boot schemas

Useful concepts such as physical entity, biological entity, person, agent, software system, organization, place, information object, group, and goal may be supplied as ordinary schema revisions.

Every boot schema has:

```text
ordinary schema representation
field-level boot provenance
typed dependencies
GroundingSpecification
independent property/invariant tests
versioned foundation manifest
activation assessment
```

The same package may not self-certify solely by supplying its own example/expected graph pairs. Boot validation includes kernel invariants and independently implemented property tests.

Failure policy:

- failed representation/value/foundational-predicate semantics halt boot or enter explicit diagnostic-safe mode;
- failed optional boot concepts load opaque/provisional and downgrade dependents;
- no failing schema silently activates.

## 6. Grounding anchors

A required definition dependency may terminate in:

1. a kernel representation/value primitive;
2. an executable foundational predicate;
3. an adapter-observed schema under a versioned observation contract;
4. an audited active boot schema;
5. an already active learned schema with valid environment fingerprint.

A familiar word, assertion count, or graph node is not an anchor.

## 7. Adapter observation contracts

An adapter-observed anchor records:

```text
input/output type contract
observation semantics
verification/property cases
adapter implementation/version
permission and freshness policy
```

Adapter drift invalidates dependent assessments and cognition through the same typed dependency graph.

## 8. SemanticPattern expressiveness

The pattern AST minimally supports:

```text
positive and negative conditions
role-variable binding
bounded quantification over declared fillers
cardinality
modality
context/world qualification
time and aspect
comparison and units
conjunction/disjunction with defined semantics
exception/default metadata
```

Unsupported constructs create `expressiveness_blocker`. They are never silently dropped.

## 9. Open-world and default reasoning

Truth maintenance is four-state:

```text
supported
refuted
both
neither
```

Typical/default reasoning cannot convert `neither` to refutation.

Default application uses context, specificity, priority, exception evidence, provenance, and valid time. A default never overrides strict constitutive evidence silently.

## 10. Causal warrant

Foundational causal predicates define representation and query semantics. Claims using them carry a separate warrant grade:

```text
reported_claim
contextual_rule
predictive_association
mechanism_supported
intervention_supported
```

Actual intervention or irreversible planning requires the appropriate grade plus live authorization.

## 11. Regress and resource bounds

Foundations terminate semantic dependency regress honestly, but the kernel still enforces:

```text
schema/dependency depth limits
bounded quantification
probe/competence/replay budgets
cycle classification
no user executable code
scope/promotion permissions
boot/global protection
```

The system may preserve an opaque concept and state its blockers rather than forcing universal decomposition.
