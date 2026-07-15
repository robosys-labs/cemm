"""Executable contracts that give foundational predicates their meaning."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any


class OperationClass(str, Enum):
    RECOGNIZE = "recognize"
    COMPOSE = "compose"
    QUERY = "query"
    INFER = "infer"
    REALIZE = "realize"
    EFFECT = "effect"


@dataclass(frozen=True, slots=True)
class RoleContract:
    role_key: str
    accepted_families: frozenset[str]
    required: bool = True
    cardinality: str = "one"
    allows_open_port: bool = True


@dataclass(frozen=True, slots=True)
class QueryProjection:
    projection_key: str
    open_role_keys: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ContradictionContract:
    contradiction_key: str
    compared_role_keys: tuple[str, ...]
    same_context_required: bool = True
    same_valid_time_required: bool = True
    opposite_polarity: bool = True


@dataclass(frozen=True, slots=True)
class AlgebraContract:
    symmetric: bool = False
    reflexive: bool = False
    irreflexive: bool = False
    transitive: bool = False
    antisymmetric: bool = False
    inverse_predicate_key: str = ""
    composition_rule_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FoundationPredicateContract:
    contract_id: str
    semantic_key: str
    roles: tuple[RoleContract, ...]
    identity_role_keys: tuple[str, ...]
    query_projections: tuple[QueryProjection, ...]
    contradiction_contracts: tuple[ContradictionContract, ...]
    algebra: AlgebraContract = AlgebraContract()
    permitted_operations: frozenset[OperationClass] = frozenset()
    context_policy: str = "context_required"
    valid_time_policy: str = "inherit"
    property_case_refs: tuple[str, ...] = ()
    implementation_ref: str = ""
    version: int = 1

    def role(self, role_key: str) -> RoleContract | None:
        return next((role for role in self.roles if role.role_key == role_key), None)

    def required_roles(self) -> frozenset[str]:
        return frozenset(role.role_key for role in self.roles if role.required)

    def permits(self, operation: OperationClass) -> bool:
        return operation in self.permitted_operations


@dataclass(frozen=True, slots=True)
class BootSchemaContract:
    contract_id: str
    semantic_key: str
    schema_family: str
    dependency_refs: tuple[str, ...]
    constitutive_pattern_refs: tuple[str, ...]
    identity_criteria_refs: tuple[str, ...]
    operational_port_refs: tuple[str, ...]
    observation_contract_refs: tuple[str, ...] = ()
    competence_case_refs: tuple[str, ...] = ()
    version: int = 1


class FoundationRegistry:
    def __init__(
        self,
        predicates: tuple[FoundationPredicateContract, ...],
        boot_schemas: tuple[BootSchemaContract, ...],
        fingerprint: str,
    ) -> None:
        self._predicates = {item.semantic_key: item for item in predicates}
        self._boot = {item.semantic_key: item for item in boot_schemas}
        self.fingerprint = fingerprint

    def predicate(self, key: str) -> FoundationPredicateContract | None:
        return self._predicates.get(key)

    def boot_schema(self, key: str) -> BootSchemaContract | None:
        return self._boot.get(key)

    @classmethod
    def load(cls, root: Path) -> "FoundationRegistry":
        predicate_raw = json.loads((root / "predicates.json").read_text(encoding="utf-8"))
        boot_raw = json.loads((root / "boot_schemas.json").read_text(encoding="utf-8"))
        digest = hashlib.sha256()
        for path in sorted(root.glob("*.json")):
            digest.update(path.read_bytes())

        predicates = tuple(
            FoundationPredicateContract(
                contract_id=item["contract_id"],
                semantic_key=item["semantic_key"],
                roles=tuple(
                    RoleContract(
                        role_key=role["role_key"],
                        accepted_families=frozenset(role["accepted_families"]),
                        required=bool(role.get("required", True)),
                        cardinality=role.get("cardinality", "one"),
                        allows_open_port=bool(role.get("allows_open_port", True)),
                    )
                    for role in item["roles"]
                ),
                identity_role_keys=tuple(item["identity_role_keys"]),
                query_projections=tuple(
                    QueryProjection(
                        projection_key=query["projection_key"],
                        open_role_keys=tuple(query["open_role_keys"]),
                    )
                    for query in item.get("query_projections", ())
                ),
                contradiction_contracts=tuple(
                    ContradictionContract(
                        contradiction_key=contract["contradiction_key"],
                        compared_role_keys=tuple(contract["compared_role_keys"]),
                        same_context_required=bool(
                            contract.get("same_context_required", True)
                        ),
                        same_valid_time_required=bool(
                            contract.get("same_valid_time_required", True)
                        ),
                        opposite_polarity=bool(contract.get("opposite_polarity", True)),
                    )
                    for contract in item.get("contradiction_contracts", ())
                ),
                algebra=AlgebraContract(
                    symmetric=bool(item.get("algebra", {}).get("symmetric", False)),
                    reflexive=bool(item.get("algebra", {}).get("reflexive", False)),
                    irreflexive=bool(item.get("algebra", {}).get("irreflexive", False)),
                    transitive=bool(item.get("algebra", {}).get("transitive", False)),
                    antisymmetric=bool(item.get("algebra", {}).get("antisymmetric", False)),
                    inverse_predicate_key=item.get("algebra", {}).get(
                        "inverse_predicate_key", ""
                    ),
                    composition_rule_refs=tuple(
                        item.get("algebra", {}).get("composition_rule_refs", ())
                    ),
                ),
                permitted_operations=frozenset(
                    OperationClass(value)
                    for value in item.get("permitted_operations", ())
                ),
                context_policy=item.get("context_policy", "context_required"),
                valid_time_policy=item.get("valid_time_policy", "inherit"),
                property_case_refs=tuple(item.get("property_case_refs", ())),
                implementation_ref=item.get("implementation_ref", ""),
                version=int(item.get("version", 1)),
            )
            for item in predicate_raw
        )

        boot_schemas = tuple(
            BootSchemaContract(
                contract_id=item["contract_id"],
                semantic_key=item["semantic_key"],
                schema_family=item["schema_family"],
                dependency_refs=tuple(item.get("dependency_refs", ())),
                constitutive_pattern_refs=tuple(item.get("constitutive_pattern_refs", ())),
                identity_criteria_refs=tuple(item.get("identity_criteria_refs", ())),
                operational_port_refs=tuple(item.get("operational_port_refs", ())),
                observation_contract_refs=tuple(
                    item.get("observation_contract_refs", ())
                ),
                competence_case_refs=tuple(item.get("competence_case_refs", ())),
                version=int(item.get("version", 1)),
            )
            for item in boot_raw
        )
        return cls(predicates, boot_schemas, digest.hexdigest())

    def validate(self) -> tuple[str, ...]:
        failures: list[str] = []
        for contract in self._predicates.values():
            role_keys = {role.role_key for role in contract.roles}
            if not contract.implementation_ref:
                failures.append(f"{contract.semantic_key}: missing implementation_ref")
            if not contract.property_case_refs:
                failures.append(f"{contract.semantic_key}: no independent property cases")
            if not set(contract.identity_role_keys) <= role_keys:
                failures.append(f"{contract.semantic_key}: invalid identity role")
            for query in contract.query_projections:
                if not set(query.open_role_keys) <= role_keys:
                    failures.append(
                        f"{contract.semantic_key}: query opens undeclared role"
                    )
        for contract in self._boot.values():
            if not contract.constitutive_pattern_refs:
                failures.append(
                    f"{contract.semantic_key}: lacks constitutive pattern"
                )
            if not contract.competence_case_refs:
                failures.append(
                    f"{contract.semantic_key}: lacks independent competence cases"
                )
            if not (
                contract.operational_port_refs or contract.observation_contract_refs
            ):
                failures.append(
                    f"{contract.semantic_key}: lacks operational attachment"
                )
        return tuple(failures)
