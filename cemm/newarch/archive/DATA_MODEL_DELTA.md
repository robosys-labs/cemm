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
    dependency_closure_fingerprint: str
    evidence_refs: tuple[Ref[EvidenceRecord], ...]
```

This is a cognitive-control/validation result. It is not a semantic graph object and not a new schema authority.

It is cached by exact schema revision **plus** `dependency_closure_fingerprint` — a stable hash of the revision IDs of every schema in the dependency closure. A cached assessment whose fingerprint no longer matches the live closure is invalid and must be recomputed. It is always derivable.

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

### 2.1 Pattern strength

Each `SemanticPattern` carries:

```text
strength: strict | defeasible | typical
exception_refs: registered exceptions (defeasible patterns only)
```

Defeasible-pattern violations register exceptions; they do not defeat closure. Strict-pattern violations follow ordinary contradiction handling.

### 2.2 Competence case provenance

Each `CompetencyCase` records its provenance (teaching-derived, sibling-contrast, user-supplied, induced, boot-audited). Cases derived only from the validated definition itself may check well-formedness, not discrimination.

## 3. Extend grounded meaning candidates

```text
definition_usability: executable | partial | opaque
schema_grounding_assessment_ref
permitted_semantic_operations
missing_definition_fields
```

### 3.1 Permitted semantic operations vocabulary

`permitted_semantic_operations` values come from a fixed ladder, not free-form strings:

```text
quote_reference, remember_assertion, query_assertion, search, learning_target,
typed_reference, constrained_composition, probe, provisional_contrast,
recognition, defining_query, licensed_inference, inheritance,
effect_projection   # additionally requires separate effect authorization
```

`effect_projection` is never granted by structural closure alone.

## 3.2 Extend committed propositions

Two small fields, no new record type:

```text
derivation_provenance: observed | attributed | inferred(ancestry_refs)
interpreted_under: tuple of schema revision refs active at assertion time
```

`derivation_provenance` enforces the derived-evidence law (inferred propositions cannot support their own ancestry). `interpreted_under` enforces proposition–revision binding under concept drift.

## 4. Extend GapRecord blocker vocabulary

No new record type is needed. Add blocker codes for definition-family and closure failures, plus:

```text
expressiveness_blocker      # required pattern construct unsupported
sense_individuation_pending # split-vs-correction unresolved
```

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
