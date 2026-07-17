"""Versioned schema and language-package authority for CEMM v3.4.7."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .model import (
    OperationSchema,
    PortSchema,
    PredicateSchema,
    Referent,
    ReferentKind,
    RuleFunction,
    RulePattern,
    RuleSchema,
    RuleStrength,
    SchemaStatus,
    semantic_hash,
)


class SchemaValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class LanguagePack:
    language_tag: str
    version: str
    detector_markers: tuple[str, ...]
    tokenizer: Mapping[str, Any]
    lexical_entries: tuple[Mapping[str, Any], ...]
    structure_markers: Mapping[str, tuple[str, ...]]
    constructions: tuple[Mapping[str, Any], ...]
    realization: Mapping[str, Any]
    pronouns: Mapping[str, Mapping[str, Any]]
    morphology: Mapping[str, Any]

    def lexical_index(self) -> dict[str, tuple[Mapping[str, Any], ...]]:
        result: dict[str, list[Mapping[str, Any]]] = {}
        for entry in self.lexical_entries:
            for surface in entry.get("surfaces", ()):
                result.setdefault(str(surface).casefold(), []).append(entry)
        return {key: tuple(value) for key, value in result.items()}


@dataclass(frozen=True, slots=True)
class FoundationPackage:
    version: str
    package_ref: str
    referents: tuple[Referent, ...]
    predicates: tuple[PredicateSchema, ...]
    operations: tuple[OperationSchema, ...]
    rules: tuple[RuleSchema, ...]
    seed_assertions: tuple[Mapping[str, Any], ...]
    fingerprint: str


class SemanticSchemaStore:
    """Single executable schema authority.

    This store owns predicate, operation and rule lifecycle selection.  Language
    packages may propose schema references but cannot activate or select meaning.
    """

    def __init__(self, foundation: FoundationPackage):
        self.foundation = foundation
        self._predicates = {item.schema_ref: item for item in foundation.predicates}
        self._predicates_by_key = {item.semantic_key: item for item in foundation.predicates}
        self._operations = {item.operation_ref: item for item in foundation.operations}
        self._rules = {item.rule_ref: item for item in foundation.rules}
        self._candidate_schemas: dict[str, Mapping[str, Any]] = {}
        self._candidate_rules: dict[str, Mapping[str, Any]] = {}
        self._schema_revisions: dict[str, Mapping[str, Any]] = {}
        self._rule_revisions: dict[str, Mapping[str, Any]] = {}
        self._learned_predicates: dict[str, PredicateSchema] = {}
        self._learned_rules: dict[str, RuleSchema] = {}

    @property
    def fingerprint(self) -> str:
        return self.foundation.fingerprint

    def predicate(self, ref_or_key: str) -> PredicateSchema:
        item = (self._predicates.get(ref_or_key) or self._predicates_by_key.get(ref_or_key)
                or self._learned_predicates.get(ref_or_key)
                or next((value for value in self._learned_predicates.values() if value.semantic_key == ref_or_key), None))
        if item is None:
            raise KeyError(ref_or_key)
        return item

    def maybe_predicate(self, ref_or_key: str) -> PredicateSchema | None:
        try:
            return self.predicate(ref_or_key)
        except KeyError:
            return None

    def active_predicates(self) -> tuple[PredicateSchema, ...]:
        values = tuple(self._predicates.values()) + tuple(self._learned_predicates.values())
        return tuple(item for item in values if item.status == SchemaStatus.ACTIVE)

    def operation(self, operation_ref: str) -> OperationSchema:
        return self._operations[operation_ref]

    def operations_for_predicate(self, predicate_ref: str) -> tuple[OperationSchema, ...]:
        return tuple(
            item for item in self._operations.values()
            if item.semantic_predicate_ref == predicate_ref and item.status == SchemaStatus.ACTIVE
        )

    def active_rules(self) -> tuple[RuleSchema, ...]:
        values = tuple(self._rules.values()) + tuple(self._learned_rules.values())
        return tuple(item for item in values if item.status == SchemaStatus.ACTIVE)

    def add_schema_candidate(self, candidate_ref: str, payload: Mapping[str, Any]) -> None:
        self._candidate_schemas[candidate_ref] = dict(payload)

    def add_rule_candidate(self, candidate_ref: str, payload: Mapping[str, Any]) -> None:
        self._candidate_rules[candidate_ref] = dict(payload)

    def candidate_schema(self, candidate_ref: str) -> Mapping[str, Any] | None:
        return self._candidate_schemas.get(candidate_ref)

    def candidate_rule(self, candidate_ref: str) -> Mapping[str, Any] | None:
        return self._candidate_rules.get(candidate_ref)

    def register_schema_revision(self, schema_ref: str, record: Mapping[str, Any]) -> None:
        self._schema_revisions[schema_ref] = dict(record)
        status = SchemaStatus(str(record.get("status", "candidate")))
        payload = dict(record.get("payload", {}))
        predicate_payload = payload.get("predicate") if isinstance(payload.get("predicate"), Mapping) else payload
        if str(record.get("schema_kind", "")) not in {"predicate", "predicate_schema"}:
            return
        if not isinstance(predicate_payload, Mapping) or "ports" not in predicate_payload:
            return
        data = dict(predicate_payload)
        data.setdefault("schema_ref", schema_ref)
        data.setdefault("semantic_key", schema_ref.split(":", 1)[-1])
        data["status"] = status.value
        data["revision"] = int(record.get("revision", 1))
        predicate = PackageLoader._predicate(data)
        self._learned_predicates[predicate.schema_ref] = predicate

    def register_rule_revision(self, rule_ref: str, record: Mapping[str, Any]) -> None:
        self._rule_revisions[rule_ref] = dict(record)
        status = SchemaStatus(str(record.get("status", "candidate")))
        payload = dict(record.get("payload", {}))
        rule_payload = payload.get("rule") if isinstance(payload.get("rule"), Mapping) else payload
        if not isinstance(rule_payload, Mapping) or "consequent" not in rule_payload:
            return
        data = dict(rule_payload)
        data.setdefault("rule_ref", rule_ref)
        data["status"] = status.value
        data["revision"] = int(record.get("revision", 1))
        rule = PackageLoader._rule(data)
        self._learned_rules[rule.rule_ref] = rule

    def schema_revision(self, schema_ref: str) -> Mapping[str, Any] | None:
        return self._schema_revisions.get(schema_ref)

    def rule_revision(self, rule_ref: str) -> Mapping[str, Any] | None:
        return self._rule_revisions.get(rule_ref)


class PackageLoader:
    def __init__(self, data_root: Path | None = None):
        self.data_root = data_root or Path(__file__).resolve().parents[1] / "data" / "v347"

    def load_foundation(self) -> FoundationPackage:
        path = self.data_root / "foundation.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self._validate_foundation_shape(data)
        predicates = tuple(self._predicate(item) for item in data["predicates"])
        predicate_refs = {item.schema_ref for item in predicates}
        operations = tuple(self._operation(item) for item in data.get("operations", ()))
        rules = tuple(self._rule(item) for item in data.get("rules", ()))
        referents = tuple(self._referent(item) for item in data.get("referents", ()))
        for operation in operations:
            if operation.semantic_predicate_ref not in predicate_refs:
                raise SchemaValidationError(
                    f"operation {operation.operation_ref} references unknown predicate "
                    f"{operation.semantic_predicate_ref}"
                )
        fingerprint = semantic_hash("foundation", data, 64)
        return FoundationPackage(
            version=str(data["version"]),
            package_ref=str(data["package_ref"]),
            referents=referents,
            predicates=predicates,
            operations=operations,
            rules=rules,
            seed_assertions=tuple(data.get("seed_assertions", ())),
            fingerprint=fingerprint,
        )

    def load_languages(self) -> dict[str, LanguagePack]:
        result: dict[str, LanguagePack] = {}
        for path in sorted((self.data_root / "languages").glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            pack = self._language(data)
            if pack.language_tag in result:
                raise SchemaValidationError(f"duplicate language tag {pack.language_tag}")
            result[pack.language_tag] = pack
        if not result:
            raise SchemaValidationError("no language packs found")
        return result

    @staticmethod
    def _port(item: Mapping[str, Any]) -> PortSchema:
        return PortSchema(
            port_id=str(item["port_id"]),
            accepted_kinds=frozenset(ReferentKind(value) for value in item.get("accepted_kinds", ())),
            required=bool(item.get("required", False)),
            query_open=bool(item.get("query_open", False)),
            multiple=bool(item.get("multiple", False)),
            role_family=str(item.get("role_family", "")),
            accepted_type_refs=frozenset(map(str, item.get("accepted_type_refs", ()))),
            identity_contribution=bool(item.get("identity_contribution", False)),
            context_propagation=str(item.get("context_propagation", "inherit")),
            time_propagation=str(item.get("time_propagation", "inherit")),
            coercion_policy=str(item.get("coercion_policy", "none")),
            metadata=dict(item.get("metadata", {})),
        )

    @classmethod
    def _predicate(cls, item: Mapping[str, Any]) -> PredicateSchema:
        ports = tuple(cls._port(port) for port in item.get("ports", ()))
        if not ports:
            raise SchemaValidationError(f"predicate {item.get('schema_ref')} has no ports")
        ids = [port.port_id for port in ports]
        if len(ids) != len(set(ids)):
            raise SchemaValidationError(f"duplicate local port in {item.get('schema_ref')}")
        return PredicateSchema(
            schema_ref=str(item["schema_ref"]),
            semantic_key=str(item["semantic_key"]),
            ports=ports,
            status=SchemaStatus(item.get("status", "active")),
            scope_ref=str(item.get("scope_ref", "global")),
            revision=int(item.get("revision", 1)),
            eventive=bool(item.get("eventive", False)),
            stateful=bool(item.get("stateful", False)),
            symmetric=bool(item.get("symmetric", False)),
            inverse_predicate_ref=item.get("inverse_predicate_ref"),
            supersedes_same_ports=tuple(map(str, item.get("supersedes_same_ports", ()))),
            metadata=dict(item.get("metadata", {})),
        )

    @classmethod
    def _operation(cls, item: Mapping[str, Any]) -> OperationSchema:
        return OperationSchema(
            operation_ref=str(item["operation_ref"]),
            semantic_predicate_ref=str(item["semantic_predicate_ref"]),
            input_ports=tuple(cls._port(port) for port in item.get("input_ports", ())),
            output_ports=tuple(cls._port(port) for port in item.get("output_ports", ())),
            capability_ref=str(item.get("capability_ref", "")),
            permission_ref=str(item.get("permission_ref", "conversation")),
            risk=float(item.get("risk", 0.0)),
            reversible=bool(item.get("reversible", True)),
            idempotent=bool(item.get("idempotent", True)),
            status=SchemaStatus(item.get("status", "active")),
            metadata=dict(item.get("metadata", {})),
        )

    @staticmethod
    def _pattern(item: Mapping[str, Any]) -> RulePattern:
        return RulePattern(
            predicate_schema_ref=str(item["predicate_schema_ref"]),
            port_variables={str(k): str(v) for k, v in item.get("port_variables", {}).items()},
            fixed_referent_refs={str(k): str(v) for k, v in item.get("fixed_referent_refs", {}).items()},
        )

    @classmethod
    def _rule(cls, item: Mapping[str, Any]) -> RuleSchema:
        return RuleSchema(
            rule_ref=str(item["rule_ref"]),
            antecedents=tuple(cls._pattern(value) for value in item.get("antecedents", ())),
            consequent=cls._pattern(item["consequent"]),
            function=RuleFunction(item["function"]),
            strength=RuleStrength(item["strength"]),
            status=SchemaStatus(item.get("status", "active")),
            confidence=float(item.get("confidence", 1.0)),
            exceptions=tuple(cls._pattern(value) for value in item.get("exceptions", ())),
            sensitivity=str(item.get("sensitivity", "normal")),
            scope_ref=str(item.get("scope_ref", "global")),
            revision=int(item.get("revision", 1)),
            priority=int(item.get("priority", 0)),
            context_refs=tuple(map(str, item.get("context_refs", ()))),
            valid_time_ref=item.get("valid_time_ref"),
            support_lineage_refs=tuple(map(str, item.get("support_lineage_refs", ()))),
            metadata=dict(item.get("metadata", {})),
        )

    @staticmethod
    def _referent(item: Mapping[str, Any]) -> Referent:
        return Referent(
            referent_id=str(item["referent_id"]),
            kind=ReferentKind(item["kind"]),
            type_refs=tuple(map(str, item.get("type_refs", ()))),
            payload=dict(item.get("payload", {})) or None,
            scope_ref=str(item.get("scope_ref", "global")),
            context_ref=str(item.get("context_ref", "actual")),
            revision=int(item.get("revision", 1)),
            metadata=dict(item.get("metadata", {})),
        )

    @staticmethod
    def _language(data: Mapping[str, Any]) -> LanguagePack:
        required = {"language_tag", "version", "lexical_entries", "realization"}
        missing = required - set(data)
        if missing:
            raise SchemaValidationError(f"language package missing {sorted(missing)}")
        return LanguagePack(
            language_tag=str(data["language_tag"]),
            version=str(data["version"]),
            detector_markers=tuple(map(str, data.get("detector_markers", ()))),
            tokenizer=dict(data.get("tokenizer", {})),
            lexical_entries=tuple(dict(item) for item in data.get("lexical_entries", ())),
            structure_markers={
                str(key): tuple(map(str, values))
                for key, values in data.get("structure_markers", {}).items()
            },
            constructions=tuple(dict(item) for item in data.get("constructions", ())),
            realization=dict(data.get("realization", {})),
            pronouns={str(key): dict(value) for key, value in data.get("pronouns", {}).items()},
            morphology=dict(data.get("morphology", {})),
        )

    @staticmethod
    def _validate_foundation_shape(data: Mapping[str, Any]) -> None:
        if str(data.get("version")) != "3.4.7":
            raise SchemaValidationError("foundation version must be 3.4.7")
        if not data.get("predicates"):
            raise SchemaValidationError("foundation requires predicates")
        # Foundation data must be language-neutral. Surface aliases and templates
        # belong only in language packages.
        forbidden = {"surface", "surfaces", "template", "templates", "words", "phrases"}
        stack: list[Any] = [data]
        while stack:
            value = stack.pop()
            if isinstance(value, Mapping):
                bad = forbidden.intersection(value)
                if bad:
                    raise SchemaValidationError(
                        f"language surface fields forbidden in foundation: {sorted(bad)}"
                    )
                stack.extend(value.values())
            elif isinstance(value, list):
                stack.extend(value)


def load_runtime_packages(data_root: Path | None = None) -> tuple[FoundationPackage, dict[str, LanguagePack]]:
    loader = PackageLoader(data_root)
    foundation = loader.load_foundation()
    languages = loader.load_languages()
    return foundation, languages
