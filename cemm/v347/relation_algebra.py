"""Schema-derived relationship algebra for CEMM v3.4.7.

Algebraic properties are declarations on predicate schemas, not language rules.
This coordinator compiles those declarations into ordinary typed RuleSchemas so
all conclusions use the same bounded, proof-carrying inference engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .model import (
    PredicateSchema,
    RuleFunction,
    RulePattern,
    RuleSchema,
    RuleStrength,
    SchemaStatus,
    semantic_hash,
)
from .schema import SemanticSchemaStore


@dataclass(frozen=True, slots=True)
class AlgebraValidationFinding:
    schema_ref: str
    code: str
    detail: str


class RelationAlgebraCoordinator:
    """Compile symmetric, inverse and transitive schema declarations."""

    def __init__(self, schemas: SemanticSchemaStore):
        self._schemas = schemas

    def validate(self) -> tuple[AlgebraValidationFinding, ...]:
        findings: list[AlgebraValidationFinding] = []
        for schema in self._schemas.active_predicates():
            if (schema.symmetric or schema.inverse_predicate_ref) and len(schema.ports) != 2:
                findings.append(AlgebraValidationFinding(
                    schema_ref=schema.schema_ref,
                    code="binary_algebra_requires_two_ports",
                    detail="symmetric and inverse declarations require exactly two local ports",
                ))
            if schema.inverse_predicate_ref:
                inverse = self._schemas.maybe_predicate(schema.inverse_predicate_ref)
                if inverse is None:
                    findings.append(AlgebraValidationFinding(
                        schema_ref=schema.schema_ref,
                        code="missing_inverse_schema",
                        detail=schema.inverse_predicate_ref,
                    ))
                elif len(inverse.ports) != 2:
                    findings.append(AlgebraValidationFinding(
                        schema_ref=schema.schema_ref,
                        code="inverse_schema_not_binary",
                        detail=inverse.schema_ref,
                    ))
            if bool(schema.metadata.get("transitive", False)) and len(schema.ports) != 2:
                findings.append(AlgebraValidationFinding(
                    schema_ref=schema.schema_ref,
                    code="transitivity_requires_two_ports",
                    detail="transitive declaration requires exactly two local ports",
                ))
        return tuple(findings)

    def compiled_rules(self) -> tuple[RuleSchema, ...]:
        findings = self.validate()
        invalid = {item.schema_ref for item in findings}
        result: dict[str, RuleSchema] = {}
        for schema in self._schemas.active_predicates():
            if schema.schema_ref in invalid or len(schema.ports) != 2:
                continue
            if schema.symmetric:
                rule = self._symmetric_rule(schema)
                result[rule.rule_ref] = rule
            if schema.inverse_predicate_ref:
                inverse = self._schemas.maybe_predicate(schema.inverse_predicate_ref)
                if inverse is not None and len(inverse.ports) == 2:
                    rule = self._inverse_rule(schema, inverse)
                    result[rule.rule_ref] = rule
            if bool(schema.metadata.get("transitive", False)):
                rule = self._transitive_rule(schema)
                result[rule.rule_ref] = rule
        return tuple(sorted(result.values(), key=lambda item: item.rule_ref))

    @staticmethod
    def _symmetric_rule(schema: PredicateSchema) -> RuleSchema:
        left, right = (port.port_id for port in schema.ports)
        rule_ref = semantic_hash("rule:algebra:symmetric", (schema.schema_ref, schema.revision))
        return RuleSchema(
            rule_ref=rule_ref,
            antecedents=(RulePattern(
                predicate_schema_ref=schema.schema_ref,
                port_variables={left: "x", right: "y"},
            ),),
            consequent=RulePattern(
                predicate_schema_ref=schema.schema_ref,
                port_variables={left: "y", right: "x"},
            ),
            function=RuleFunction.STRICT,
            strength=RuleStrength.STRICT,
            status=SchemaStatus.ACTIVE,
            confidence=1.0,
            scope_ref=schema.scope_ref,
            revision=schema.revision,
            priority=100,
            support_lineage_refs=(f"schema:{schema.schema_ref}:symmetric",),
            metadata={"algebra": "symmetric", "schema_revision": schema.revision},
        )

    @staticmethod
    def _inverse_rule(source: PredicateSchema, target: PredicateSchema) -> RuleSchema:
        source_left, source_right = (port.port_id for port in source.ports)
        target_left, target_right = (port.port_id for port in target.ports)
        rule_ref = semantic_hash(
            "rule:algebra:inverse",
            (source.schema_ref, source.revision, target.schema_ref, target.revision),
        )
        return RuleSchema(
            rule_ref=rule_ref,
            antecedents=(RulePattern(
                predicate_schema_ref=source.schema_ref,
                port_variables={source_left: "x", source_right: "y"},
            ),),
            consequent=RulePattern(
                predicate_schema_ref=target.schema_ref,
                port_variables={target_left: "y", target_right: "x"},
            ),
            function=RuleFunction.STRICT,
            strength=RuleStrength.STRICT,
            status=SchemaStatus.ACTIVE,
            confidence=1.0,
            scope_ref=source.scope_ref,
            revision=max(source.revision, target.revision),
            priority=100,
            support_lineage_refs=(
                f"schema:{source.schema_ref}:inverse:{target.schema_ref}",
            ),
            metadata={
                "algebra": "inverse",
                "source_schema_revision": source.revision,
                "target_schema_revision": target.revision,
            },
        )

    @staticmethod
    def _transitive_rule(schema: PredicateSchema) -> RuleSchema:
        left, right = (port.port_id for port in schema.ports)
        rule_ref = semantic_hash("rule:algebra:transitive", (schema.schema_ref, schema.revision))
        return RuleSchema(
            rule_ref=rule_ref,
            antecedents=(
                RulePattern(
                    predicate_schema_ref=schema.schema_ref,
                    port_variables={left: "x", right: "y"},
                ),
                RulePattern(
                    predicate_schema_ref=schema.schema_ref,
                    port_variables={left: "y", right: "z"},
                ),
            ),
            consequent=RulePattern(
                predicate_schema_ref=schema.schema_ref,
                port_variables={left: "x", right: "z"},
            ),
            function=RuleFunction.STRICT,
            strength=RuleStrength.STRICT,
            status=SchemaStatus.ACTIVE,
            confidence=1.0,
            scope_ref=schema.scope_ref,
            revision=schema.revision,
            priority=90,
            support_lineage_refs=(f"schema:{schema.schema_ref}:transitive",),
            metadata={"algebra": "transitive", "schema_revision": schema.revision},
        )
