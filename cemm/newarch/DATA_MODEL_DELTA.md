# CEMM v3.4 — Minimal Data Model Delta

The canonical semantic object model remains unchanged.

## 1. Add one derived control record

```python
@dataclass(frozen=True)
class SchemaGroundingAssessment:
    schema_record_ref: Ref[SchemaEnvelope]
    schema_revision: int
    semantic_family_resolved: bool
    required_fields_complete: bool
    dependencies_grounded: bool
    constitutive_patterns_executable: bool
    differentiator_satisfied: bool
    circularity_free: bool
    competency_spec_satisfied: bool
    executable: bool
    blocker_codes: tuple[str, ...]
    dependency_refs: tuple[Ref[SchemaEnvelope], ...]
    evidence_refs: tuple[Ref[EvidenceRecord], ...]
```

This is a cognitive-control/validation result. It is not a semantic graph object and not a new schema authority.

It may be cached by exact schema revision but is always derivable.

## 2. Add a common grounding specification to schema payloads

```python
@dataclass(frozen=True)
class GroundingSpecification:
    semantic_family: str
    required_definition_fields: tuple[str, ...]
    constitutive_patterns: tuple[SemanticPattern, ...]
    differentiating_patterns: tuple[SemanticPattern, ...]
    dependency_schema_refs: tuple[Ref[SchemaEnvelope], ...]
    competency_case_refs: tuple[Ref[CompetencyCase], ...]
```

Existing schema payloads retain their specialized fields. This common specification declares how activation is validated.

## 3. Extend grounded meaning candidates

```text
definition_usability: executable | partial | opaque
schema_grounding_assessment_ref
permitted_semantic_operations
missing_definition_fields
```

## 4. Extend GapRecord blocker vocabulary

No new record type is needed. Add blocker codes for definition-family and closure failures.

## 5. Do not add

```text
OntologicalFrame object family
GroundingCertificate database
second concept graph
second schema lifecycle
parallel ontology resolver
fixed domain primitive enum
```

The schema envelope remains:

```text
candidate → provisional → active → superseded/rejected
```

`active` is permitted only when activation validation succeeds.
