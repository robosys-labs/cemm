"""Independent structural invariants for the v3.4.1 communication closure."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .v341 import lexical_specs, operation_specs, realization_specs, semantic_specs
from ..schema.realization import RealizationSchema


@dataclass(frozen=True, slots=True)
class V341FoundationValidationReport:
    ok: bool
    failures: tuple[str, ...] = ()

    def require_ok(self) -> None:
        if not self.ok:
            raise RuntimeError(
                "v3.4.1 communication foundation validation failed: "
                + "; ".join(self.failures)
            )


def validate_v341_spec() -> V341FoundationValidationReport:
    predicates, entity_kinds = semantic_specs()
    operations = operation_specs()
    realizations = realization_specs()
    lexemes = lexical_specs()
    failures: list[str] = []
    semantic_keys = set(predicates) | set(entity_kinds) | set(operations)

    critical = {
        "recognizes_form", "knows", "has_usable_definition", "stores",
        "has_access_to", "has_sufficient_information", "receives",
        "completes", "requires_information",
    }
    missing = critical - semantic_keys
    if missing:
        failures.append("missing critical semantic schemas: " + ", ".join(sorted(missing)))

    for key, predicate in predicates.items():
        if predicate.semantic_key != key:
            failures.append(f"predicate key mismatch: {key}")
        if not predicate.role_refs:
            failures.append(f"predicate has no typed roles: {key}")

    if "op:answer" not in operations:
        failures.append("missing critical operation schema: op:answer")
    for key, operation in operations.items():
        if operation.semantic_key != key:
            failures.append(f"operation key mismatch: {key}")
        if not operation.input_roles or not operation.output_roles:
            failures.append(f"operation has incomplete IO roles: {key}")

    lexical_keys = {key for _, key, _ in lexemes}
    lexical_surfaces = {surface.casefold() for surface, _, _ in lexemes}
    for surface, key, pos in lexemes:
        if not surface or not pos:
            failures.append(f"incomplete lexical specification: {key}")
        if not key.startswith("grammar:") and key not in semantic_keys:
            failures.append(f"lexeme {surface!r} points to missing semantic schema {key!r}")

    for key, spec in realizations.items():
        if not spec.surface or not spec.part_of_speech or not spec.modes:
            failures.append(f"incomplete realization specification: {key}")
        if not spec.closed_class and key not in semantic_keys:
            failures.append(f"open-class realization has no semantic schema: {key}")
        if spec.closed_class and not key.startswith("grammar:"):
            failures.append(f"closed-class realization lacks grammar identity: {key}")
        if spec.surface.casefold() not in lexical_surfaces:
            failures.append(f"realization surface is not indexed as a lexeme: {key}")
        if key not in lexical_keys:
            failures.append(f"realization semantic key has no lexical sense: {key}")

    return V341FoundationValidationReport(not failures, tuple(failures))


def validate_registered_v341(store: Any) -> V341FoundationValidationReport:
    failures: list[str] = []
    for key in operation_specs():
        active = store.find_active(key)
        if active is None:
            failures.append(f"no active operation record: {key}")
            continue
        if getattr(active, "schema_kind", "") != "operation":
            failures.append(f"operation record has wrong schema kind: {key}")
        if not getattr(active, "grounding_assessment_ref", ""):
            failures.append(f"operation schema lacks grounding assessment: {key}")
        if not getattr(active, "competence_assessment_ref", ""):
            failures.append(f"operation schema lacks competence assessment: {key}")

    for key, _spec in realization_specs().items():
        candidates = store.find_candidates(f"realize:en:{key}")
        active = [item for item in candidates if getattr(item, "status", "") == "active"]
        if not active:
            failures.append(f"no active realization record: {key}")
            continue
        envelope = max(active, key=lambda item: getattr(item, "version", 0))
        schema = getattr(envelope, "payload", None)
        if not isinstance(schema, RealizationSchema):
            failures.append(f"wrong realization payload type: {key}")
            continue
        if not schema.competence_test_refs:
            failures.append(f"realization lacks competence provenance: {key}")
        if schema.closed_class:
            continue
        if not schema.semantic_schema_ref:
            failures.append(f"open-class realization lacks semantic ref: {key}")
            continue
        semantic = store.get(schema.semantic_schema_ref)
        if semantic is None:
            failures.append(f"realization semantic ref is unresolved: {key}")
            continue
        if getattr(semantic, "status", "") != "active":
            failures.append(f"realization semantic ref is not active: {key}")
        if not getattr(semantic, "grounding_assessment_ref", ""):
            failures.append(f"semantic schema lacks grounding assessment: {key}")
        if not getattr(semantic, "competence_assessment_ref", ""):
            failures.append(f"semantic schema lacks competence assessment: {key}")

    return V341FoundationValidationReport(not failures, tuple(failures))
