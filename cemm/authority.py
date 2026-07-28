"""Authority-bundle loading, linking and semantic integrity validation.

Authority JSON files are one graph split across files for review and packaging.
They are never independent mini-ontologies.  This module links the complete
bundle before the Store performs any durable write, so import order cannot hide
missing atoms, role contracts, rule constants, or semantic-kind conflicts.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from cemm.native_semantic_validation import validate_native_semantic_authority


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

def isvar(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("?")

def isexist(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("!")


class AuthorityBundleError(ValueError):
    """Raised when an authority bundle violates exact semantic integrity."""

    def __init__(self, issues: Sequence[str]):
        self.issues = tuple(str(item) for item in issues)
        super().__init__("authority bundle invalid:\n- " + "\n- ".join(self.issues))


@dataclass(frozen=True)
class AuthorityDocument:
    path: Path
    data: Mapping[str, Any]

    @property
    def name(self) -> str:
        return self.path.name


@dataclass(frozen=True)
class AuthorityBundleReport:
    document_count: int
    atom_count: int
    operator_role_count: int
    fact_count: int
    rule_count: int
    reference_form_count: int
    control_symbol_count: int
    bundle_hash: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "document_count": self.document_count,
            "atom_count": self.atom_count,
            "operator_role_count": self.operator_role_count,
            "fact_count": self.fact_count,
            "rule_count": self.rule_count,
            "reference_form_count": self.reference_form_count,
            "control_symbol_count": self.control_symbol_count,
            "bundle_hash": self.bundle_hash,
        }


FOUNDATIONAL_META_RELATIONS = {
    "rel:subtype_of",
    "rel:facet_of",
    "rel:subrelation_of",
    "rel:subject_type",
    "rel:implies_subject_state",
    "rel:implies_object_state",
    "rel:state_dimension",
    "rel:state_value",
    "rel:value_of_dimension",
    "rel:entitles_state_dimension",
    "rel:dimension_domain",
    "rel:entitles_capability",
    "rel:entitles_resource",
    "rel:mechanism_applies_to",
    "rel:depends_on",
}

GENERIC_FOUNDATION_RULES = {
    "rule:subrelation-inheritance",
    "rule:relation-subject-type",
    "rule:type-subtype-inheritance",
    "rule:relation-subject-state",
    "rule:relation-object-state",
}


def load_documents(paths: Iterable[str | Path]) -> tuple[AuthorityDocument, ...]:
    documents = []
    for raw in paths:
        path = Path(raw)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - message is the contract
            raise AuthorityBundleError((f"{path}: unreadable authority JSON: {exc}",)) from exc
        if not isinstance(data, dict):
            raise AuthorityBundleError((f"{path}: authority document root must be an object",))
        documents.append(AuthorityDocument(path, data))
    if not documents:
        raise AuthorityBundleError(("authority bundle is empty",))
    return tuple(documents)


def _merge_exact(target: dict, key: Any, value: Any, origin: str, issues: list[str], what: str) -> None:
    prior = target.get(key)
    if prior is None:
        target[key] = (value, origin)
        return
    prior_value, prior_origin = prior
    if canonical(prior_value) != canonical(value):
        issues.append(f"conflicting {what} {key!r}: {prior_origin} vs {origin}")


def _literal_kind(value: Any) -> str | None:
    if isinstance(value, dict) and isinstance(value.get("literal"), dict):
        return str(value["literal"].get("type"))
    return None


def _validate_filler(
    *,
    operator: str,
    role: str,
    value: Any,
    expected: str | None,
    atom_kinds: Mapping[str, str],
    location: str,
    allow_variables: bool,
    issues: list[str],
) -> None:
    if isinstance(value, str) and (isvar(value) or isexist(value)):
        if allow_variables:
            return
        issues.append(f"{location}: variables/existentials are not allowed in durable facts: {value}")
        return
    literal_kind = _literal_kind(value)
    if expected == "state_value":
        if literal_kind is not None or (isinstance(value, dict) and "app" in value):
            return
        if not isinstance(value, str) or value not in atom_kinds:
            issues.append(f"{location}: unknown state value atom {value!r}")
        return
    if expected and expected.startswith("literal:"):
        required = expected.split(":", 1)[1]
        if literal_kind != required:
            issues.append(f"{location}: expected {expected}, found {literal_kind or type(value).__name__}")
        return
    if isinstance(value, dict) and "app" in value:
        if expected not in {None, "app"}:
            issues.append(f"{location}: application reference is invalid for {operator}:{role} ({expected})")
        return
    if literal_kind is not None:
        issues.append(f"{location}: literal is invalid for {operator}:{role} ({expected or 'atom'})")
        return
    if not isinstance(value, str) or value not in atom_kinds:
        issues.append(f"{location}: unknown atom filler {value!r} for {operator}:{role}")
        return
    if expected not in {None, "atom", "app"} and atom_kinds[value] != expected:
        issues.append(
            f"{location}: {operator}:{role} expects {expected}, but {value} is {atom_kinds[value]}"
        )


def validate_documents(
    documents: Sequence[AuthorityDocument],
    *,
    existing_atoms: Mapping[str, Mapping[str, Any]] | None = None,
    existing_operator_roles: Mapping[tuple[str, str], Mapping[str, Any]] | None = None,
    existing_controls: Mapping[str, str] | None = None,
    require_foundations: bool = True,
) -> AuthorityBundleReport:
    issues: list[str] = []
    atoms: dict[str, tuple[dict[str, Any], str]] = {}
    roles: dict[tuple[str, str], tuple[dict[str, Any], str]] = {}
    controls: dict[str, tuple[str, str]] = {}

    for ref, item in (existing_atoms or {}).items():
        atoms[str(ref)] = (dict(item), "existing store")
    for key, item in (existing_operator_roles or {}).items():
        roles[(str(key[0]), str(key[1]))] = (dict(item), "existing store")
    for role, ref in (existing_controls or {}).items():
        controls[str(role)] = (str(ref), "existing store")

    for document in documents:
        for index, item in enumerate(document.data.get("atoms", ())):
            if not isinstance(item, dict) or not item.get("ref") or not item.get("kind"):
                issues.append(f"{document.name}:atoms[{index}] requires ref and kind")
                continue
            normalized = {
                "ref": str(item["ref"]),
                "kind": str(item["kind"]),
                "metadata": dict(item.get("metadata", {})),
            }
            _merge_exact(atoms, normalized["ref"], normalized, f"{document.name}:atoms[{index}]", issues, "atom")
        for index, item in enumerate(document.data.get("operator_roles", ())):
            if not isinstance(item, dict) or not item.get("operator_ref") or not item.get("role_ref"):
                issues.append(f"{document.name}:operator_roles[{index}] requires operator_ref and role_ref")
                continue
            normalized = {
                "operator_ref": str(item["operator_ref"]),
                "role_ref": str(item["role_ref"]),
                "required": bool(item.get("required", False)),
                "cardinality": str(item.get("cardinality", "one")),
                "filler_kind": item.get("filler_kind"),
            }
            key = (normalized["operator_ref"], normalized["role_ref"])
            _merge_exact(roles, key, normalized, f"{document.name}:operator_roles[{index}]", issues, "operator-role contract")
        for role, ref in document.data.get("control_symbols", {}).items():
            _merge_exact(controls, str(role), str(ref), f"{document.name}:control_symbols", issues, "control symbol")

    atom_defs = {ref: item for ref, (item, _origin) in atoms.items()}
    atom_kinds = {ref: str(item["kind"]) for ref, item in atom_defs.items()}
    role_defs = {key: item for key, (item, _origin) in roles.items()}

    for (operator, role), spec in role_defs.items():
        if atom_kinds.get(operator) != "operator":
            issues.append(f"operator-role contract references non-operator {operator!r}")
        if atom_kinds.get(role) != "role":
            issues.append(f"operator-role contract references non-role {role!r}")
        if spec.get("cardinality", "one") != "one":
            issues.append(f"unsupported operator-role cardinality {operator}:{role}={spec.get('cardinality')}")
    for role, (ref, origin) in controls.items():
        # new_kind.* control symbols store a creatable kind name, not an atom
        # reference (see Store.creatable_kinds); they must not be resolved as atoms.
        if role.startswith("new_kind."):
            continue
        if ref not in atom_kinds:
            issues.append(f"{origin}: control symbol {role!r} references missing atom {ref!r}")

    facts: list[tuple[dict[str, Any], str]] = []
    rules_list: list[tuple[dict[str, Any], str]] = []
    reference_forms: list[tuple[dict[str, Any], str]] = []
    for document in documents:
        facts.extend((dict(item), f"{document.name}:facts[{index}]") for index, item in enumerate(document.data.get("facts", ())))
        rules_list.extend((dict(item), f"{document.name}:rules[{index}]") for index, item in enumerate(document.data.get("rules", ())))
        reference_forms.extend((dict(item), f"{document.name}:reference_forms[{index}]") for index, item in enumerate(document.data.get("reference_forms", ())))

    for item, location in reference_forms:
        bound = item.get("bound_ref")
        if bound and str(bound) not in atom_kinds:
            issues.append(f"{location}: bound_ref references missing atom {bound!r}")

    state_spec_dimensions: dict[str, set[str]] = {}
    state_spec_values: dict[str, set[str]] = {}
    implied_specs: set[str] = set()
    for item, location in facts:
        operator = str(item.get("operator", ""))
        if atom_kinds.get(operator) != "operator":
            issues.append(f"{location}: unknown/non-operator application {operator!r}")
            continue
        specs = {role: spec for (op, role), spec in role_defs.items() if op == operator}
        args = item.get("args", {})
        if not isinstance(args, dict):
            issues.append(f"{location}: args must be an object")
            continue
        for role, spec in specs.items():
            if spec.get("required") and role not in args:
                issues.append(f"{location}: missing required role {operator}:{role}")
        for role, value in args.items():
            spec = specs.get(str(role))
            if spec is None:
                issues.append(f"{location}: {operator} disallows role {role}")
                continue
            _validate_filler(
                operator=operator,
                role=str(role),
                value=value,
                expected=spec.get("filler_kind"),
                atom_kinds=atom_kinds,
                location=location,
                allow_variables=False,
                issues=issues,
            )
        if operator == "op:type":
            instance = args.get("role:instance")
            class_ref = args.get("role:class")
            if atom_kinds.get(str(instance)) == "concept" and atom_kinds.get(str(class_ref)) == "concept":
                issues.append(
                    f"{location}: concept hierarchy is encoded as instance typing; use rel:subtype_of"
                )
        if operator == "op:state" and "role:dimension" not in args:
            issues.append(f"{location}: state application lacks first-class role:dimension")
        if operator == "op:relation":
            subject = args.get("role:subject")
            relation = args.get("role:relation")
            obj = args.get("role:object")
            if relation == "rel:state_dimension" and isinstance(subject, str) and isinstance(obj, str):
                state_spec_dimensions.setdefault(subject, set()).add(obj)
            elif relation == "rel:state_value" and isinstance(subject, str) and isinstance(obj, str):
                state_spec_values.setdefault(subject, set()).add(obj)
            elif relation in {"rel:implies_subject_state", "rel:implies_object_state"} and isinstance(obj, str):
                implied_specs.add(obj)

    for spec_ref in sorted(implied_specs):
        dimensions = state_spec_dimensions.get(spec_ref, set())
        values = state_spec_values.get(spec_ref, set())
        if len(dimensions) != 1 or len(values) != 1:
            issues.append(
                f"state specification {spec_ref} must bind exactly one dimension and one value; "
                f"found dimensions={sorted(dimensions)}, values={sorted(values)}"
            )

    for rule, location in rules_list:
        antecedent = list(rule.get("if", ()))
        consequent = list(rule.get("then", ()))
        if not antecedent or not consequent:
            issues.append(f"{location}: rule requires non-empty if and then")
            continue
        bound_variables = {
            value
            for clause in antecedent
            for value in clause.get("args", {}).values()
            if isinstance(value, str) and isvar(value)
        }
        for side_name, clauses in (("if", antecedent), ("then", consequent)):
            for clause_index, clause in enumerate(clauses):
                clause_location = f"{location}:{side_name}[{clause_index}]"
                operator = str(clause.get("operator", ""))
                if atom_kinds.get(operator) != "operator":
                    issues.append(f"{clause_location}: unknown/non-operator {operator!r}")
                    continue
                specs = {role: spec for (op, role), spec in role_defs.items() if op == operator}
                args = clause.get("args", {})
                for role, spec in specs.items():
                    if side_name == "then" and spec.get("required") and role not in args:
                        issues.append(f"{clause_location}: missing required role {operator}:{role}")
                for role, value in args.items():
                    spec = specs.get(str(role))
                    if spec is None:
                        issues.append(f"{clause_location}: {operator} disallows role {role}")
                        continue
                    if side_name == "if" and isinstance(value, str) and isexist(value):
                        issues.append(f"{clause_location}: existential cannot occur in antecedent")
                    if side_name == "then" and isinstance(value, str) and isvar(value) and value not in bound_variables:
                        issues.append(f"{clause_location}: unbound consequent variable {value}")
                    _validate_filler(
                        operator=operator,
                        role=str(role),
                        value=value,
                        expected=spec.get("filler_kind"),
                        atom_kinds=atom_kinds,
                        location=clause_location,
                        allow_variables=True,
                        issues=issues,
                    )

    issues.extend(validate_native_semantic_authority(
        atom_defs=atom_defs,
        role_defs=role_defs,
        facts=facts,
    ))

    if require_foundations:
        missing_relations = sorted(ref for ref in FOUNDATIONAL_META_RELATIONS if atom_kinds.get(ref) != "relation_type")
        if missing_relations:
            issues.append(f"missing foundational meta-relations: {missing_relations}")
        rule_refs = {str(rule.get("rule_ref")) for rule, _ in rules_list}
        missing_rules = sorted(GENERIC_FOUNDATION_RULES - rule_refs)
        if missing_rules:
            issues.append(f"missing generic foundation rules: {missing_rules}")

    if issues:
        raise AuthorityBundleError(tuple(dict.fromkeys(issues)))

    names = [document.name for document in documents]
    if len(names) != len(set(names)):
        raise AuthorityBundleError(("authority bundle contains duplicate document names",))
    material = [
        (document.name, document.data)
        for document in sorted(documents, key=lambda item: item.name)
    ]
    return AuthorityBundleReport(
        len(documents),
        len(atom_defs),
        len(role_defs),
        len(facts),
        len(rules_list),
        len(reference_forms),
        len(controls),
        hashlib.sha256(canonical(material).encode()).hexdigest(),
    )


def validate_pack_constants(pack_paths: Iterable[str | Path], atom_refs: set[str]) -> None:
    issues = []
    for raw in pack_paths:
        path = Path(raw)
        data = json.loads(path.read_text(encoding="utf-8"))
        material = {key: value for key, value in data.items() if key != "pack_hash"}
        expected_hash = hashlib.sha256(canonical(material).encode()).hexdigest()
        if data.get("pack_hash") != expected_hash:
            issues.append(f"{path}: language-pack hash mismatch")
        sources = set(str(item) for item in data.get("source_classes", ()))
        constants = {str(source): str(ref) for source, ref in data.get("constant_sources", {}).items()}
        undeclared = sorted(set(constants) - sources)
        missing = sorted(set(constants.values()) - atom_refs)
        if undeclared:
            issues.append(f"{path}: undeclared constant source classes {undeclared}")
        if missing:
            issues.append(f"{path}: constants reference missing authority atoms {missing}")
    if issues:
        raise AuthorityBundleError(tuple(issues))
