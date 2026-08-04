"""Semantic Expression ABI 1: canonical derivation-independent meaning.

Programs describe how meaning was constructed.  This module owns the bounded,
immutable semantic forest produced by exact compilation.  Local node and
variable identifiers are alpha-normalized; grounded identities and semantic
structure are never normalized away.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import islice
from types import MappingProxyType
from typing import Any, Iterable, Mapping, TypeAlias, get_args

from .canonical import canonical_bytes, stable_ref
from .config import RuntimeConfig
from .contributions import ContributionKind
from .persistence import RevisionPin
from .programs import PERSISTENT_OPERATORS

SEMANTIC_EXPRESSION_ABI_VERSION = 1
_MAX_REF_CHARS = 256
_MAX_LITERAL_CHARS = 4096
_MAX_EXPECTED_KINDS = 16
_MAX_GROUNDING_REFS = 96
_RELEASE_CONFIG = RuntimeConfig.release()
_VALID_CONTRIBUTION_KINDS = frozenset(get_args(ContributionKind))


@dataclass(frozen=True)
class ExpressionLinkSchema:
    minimum_operands: int
    maximum_operands: int
    commutative: bool


EXPRESSION_LINK_SCHEMAS: Mapping[str, ExpressionLinkSchema] = MappingProxyType(
    {
        "link:coordination": ExpressionLinkSchema(2, 24, True),
        "link:conjunction": ExpressionLinkSchema(2, 24, True),
        "link:disjunction": ExpressionLinkSchema(2, 24, True),
        "link:condition": ExpressionLinkSchema(2, 2, False),
        "link:cause": ExpressionLinkSchema(2, 2, False),
        "link:purpose": ExpressionLinkSchema(2, 2, False),
        "link:contrast": ExpressionLinkSchema(2, 2, False),
        "link:sequence": ExpressionLinkSchema(2, 24, False),
    }
)
REVIEWED_COMMUTATIVE_LINK_TYPES = frozenset(
    key for key, schema in EXPRESSION_LINK_SCHEMAS.items() if schema.commutative
)
ORDERED_LINK_TYPES = frozenset(
    key for key, schema in EXPRESSION_LINK_SCHEMAS.items() if not schema.commutative
)
SCOPE_OPERATOR_TYPES = frozenset(
    {
        "scope:polarity",
        "scope:modality",
        "scope:tense",
        "scope:aspect",
        "scope:attribution",
        "scope:epistemic",
        "scope:quotation",
        "scope:simulation",
    }
)

__all__ = [
    "SEMANTIC_EXPRESSION_ABI_VERSION",
    "REVIEWED_COMMUTATIVE_LINK_TYPES",
    "ORDERED_LINK_TYPES",
    "SCOPE_OPERATOR_TYPES",
    "ExpressionBounds",
    "GroundedReference",
    "LiteralValue",
    "BoundVariable",
    "ApplicationFiller",
    "UnresolvedValue",
    "RoleBinding",
    "SemanticApplication",
    "ScopeOperator",
    "ExpressionLink",
    "VariableBinder",
    "UnresolvedFiller",
    "SemanticExpression",
    "TranslationRow",
    "CompilationProof",
    "CompilationFailure",
    "CompilationSuccess",
    "SemanticExpressionCompiler",
    "VerifiedMeaning",
]


def _required(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    if len(value) > _MAX_REF_CHARS:
        raise ValueError(f"{field} exceeds the release bound")
    return value


def _bounded_tuple(values: Iterable[Any], maximum: int, field: str) -> tuple[Any, ...]:
    materialized = tuple(islice(iter(values), maximum + 1))
    if len(materialized) > maximum:
        raise ValueError(f"{field} exceeds the release bound")
    return materialized


def _exact_fields(
    data: Mapping[str, Any], expected: frozenset[str], owner: str
) -> None:
    if not isinstance(data, Mapping) or set(data) != expected:
        raise ValueError(f"{owner} fields must match the canonical schema exactly")


def _wire_list(value: object, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a JSON array")
    return value


@dataclass(frozen=True)
class ExpressionBounds:
    max_applications: int = _RELEASE_CONFIG.max_applications
    max_roots: int = 8
    max_depth: int = _RELEASE_CONFIG.max_graph_depth
    max_scope_operators: int = _RELEASE_CONFIG.max_applications
    max_expression_links: int = _RELEASE_CONFIG.max_applications
    max_binders: int = _RELEASE_CONFIG.max_applications
    max_unresolved_fillers: int = _RELEASE_CONFIG.max_applications
    max_roles_per_application: int = 16
    max_link_operands: int = _RELEASE_CONFIG.max_applications
    max_total_nodes: int = _RELEASE_CONFIG.max_applications * 4

    def __post_init__(self) -> None:
        release = ExpressionBounds.__dataclass_fields__
        for name, value in vars(self).items():
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
            maximum = release[name].default
            if value > maximum:
                raise ValueError(f"{name} exceeds the release bound")


@dataclass(frozen=True)
class GroundedReference:
    target_ref: str

    def __post_init__(self) -> None:
        _required(self.target_ref, "target_ref")


@dataclass(frozen=True)
class LiteralValue:
    value_type: str
    value: str | int | bool

    def __post_init__(self) -> None:
        if self.value_type not in {"string", "integer", "boolean"}:
            raise ValueError(f"literal type is not admitted in R1: {self.value_type}")
        if self.value_type == "string":
            if not isinstance(self.value, str):
                raise ValueError("string literal requires a string value")
            if len(self.value) > _MAX_LITERAL_CHARS:
                raise ValueError("string literal exceeds the release bound")
        elif self.value_type == "integer":
            if not isinstance(self.value, int) or isinstance(self.value, bool):
                raise ValueError("integer literal requires an integer value")
            if not -(2**63) <= self.value < 2**63:
                raise ValueError("integer literal exceeds signed 64-bit range")
        elif not isinstance(self.value, bool):
            raise ValueError("boolean literal requires a boolean value")


@dataclass(frozen=True)
class BoundVariable:
    variable_ref: str

    def __post_init__(self) -> None:
        if not self.variable_ref.startswith("?") or len(self.variable_ref) == 1:
            raise ValueError("bound variable refs must start with '?'")


@dataclass(frozen=True)
class ApplicationFiller:
    """A proposition-valued filler pointing to any expression node."""

    node_ref: str

    def __post_init__(self) -> None:
        _required(self.node_ref, "node_ref")


@dataclass(frozen=True)
class UnresolvedValue:
    unresolved_ref: str

    def __post_init__(self) -> None:
        _required(self.unresolved_ref, "unresolved_ref")


Filler: TypeAlias = (
    GroundedReference
    | LiteralValue
    | BoundVariable
    | ApplicationFiller
    | UnresolvedValue
)


@dataclass(frozen=True)
class RoleBinding:
    role_ref: str
    filler: Filler

    def __post_init__(self) -> None:
        if not self.role_ref.startswith("role:"):
            raise ValueError("role_ref must start with 'role:'")
        if not isinstance(
            self.filler,
            (
                GroundedReference,
                LiteralValue,
                BoundVariable,
                ApplicationFiller,
                UnresolvedValue,
            ),
        ):
            raise ValueError("invalid role filler")


@dataclass(frozen=True)
class SemanticApplication:
    application_ref: str
    operator: str
    predicate_ref: str
    roles: tuple[RoleBinding, ...]
    qualifiers: tuple[RoleBinding, ...] = ()

    def __post_init__(self) -> None:
        _required(self.application_ref, "application_ref")
        if self.operator not in PERSISTENT_OPERATORS:
            raise ValueError(f"non-kernel operator: {self.operator}")
        _required(self.predicate_ref, "predicate_ref")
        object.__setattr__(self, "roles", _bounded_tuple(self.roles, 16, "roles"))
        object.__setattr__(
            self, "qualifiers", _bounded_tuple(self.qualifiers, 16, "qualifiers")
        )
        if not self.roles:
            raise ValueError("application requires at least one role")
        role_refs = [binding.role_ref for binding in self.roles]
        qualifier_refs = [binding.role_ref for binding in self.qualifiers]
        if len(role_refs) != len(set(role_refs)):
            raise ValueError("duplicate application role")
        if len(qualifier_refs) != len(set(qualifier_refs)):
            raise ValueError("duplicate application qualifier")


@dataclass(frozen=True)
class ScopeOperator:
    scope_ref: str
    operator_type: str
    value_ref: str
    operand_ref: str

    def __post_init__(self) -> None:
        _required(self.scope_ref, "scope_ref")
        if self.operator_type == "scope:negation":
            raise ValueError("negation must be normalized to polarity")
        if self.operator_type not in SCOPE_OPERATOR_TYPES:
            raise ValueError(f"unsupported scope operator: {self.operator_type}")
        _required(self.value_ref, "value_ref")
        _required(self.operand_ref, "operand_ref")


@dataclass(frozen=True)
class ExpressionLink:
    link_ref: str
    link_type: str
    operand_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _required(self.link_ref, "link_ref")
        schema = EXPRESSION_LINK_SCHEMAS.get(self.link_type)
        if schema is None:
            raise ValueError(f"unsupported expression link: {self.link_type}")
        operands = _bounded_tuple(
            self.operand_refs, schema.maximum_operands, "expression link operands"
        )
        object.__setattr__(self, "operand_refs", operands)
        if not schema.minimum_operands <= len(operands) <= schema.maximum_operands:
            raise ValueError(f"invalid expression link arity for {self.link_type}")
        for operand_ref in operands:
            _required(operand_ref, "operand_ref")


@dataclass(frozen=True)
class VariableBinder:
    binder_ref: str
    variable_ref: str
    body_ref: str

    def __post_init__(self) -> None:
        _required(self.binder_ref, "binder_ref")
        if not self.variable_ref.startswith("?") or len(self.variable_ref) == 1:
            raise ValueError("binder variable refs must start with '?'")
        _required(self.body_ref, "body_ref")


@dataclass(frozen=True)
class UnresolvedFiller:
    unresolved_ref: str
    owner_application_ref: str
    role_ref: str
    contribution_kind: str
    expected_kinds: tuple[str, ...]
    critical: bool

    def __post_init__(self) -> None:
        _required(self.unresolved_ref, "unresolved_ref")
        _required(self.owner_application_ref, "owner_application_ref")
        if not self.role_ref.startswith("role:"):
            raise ValueError("role_ref must start with 'role:'")
        if self.contribution_kind not in _VALID_CONTRIBUTION_KINDS:
            raise ValueError("invalid unresolved contribution kind")
        expected = _bounded_tuple(
            self.expected_kinds, _MAX_EXPECTED_KINDS, "expected kinds"
        )
        object.__setattr__(self, "expected_kinds", expected)
        if (
            not expected
            or any(not isinstance(item, str) or not item for item in expected)
            or len(set(expected)) != len(expected)
        ):
            raise ValueError("expected kinds must be unique non-empty strings")
        if not isinstance(self.critical, bool):
            raise ValueError("critical must be boolean")


Node: TypeAlias = SemanticApplication | ScopeOperator | ExpressionLink | VariableBinder


def _filler_dict(filler: Filler) -> dict[str, Any]:
    if isinstance(filler, GroundedReference):
        return {"kind": "grounded", "target_ref": filler.target_ref}
    if isinstance(filler, LiteralValue):
        return {
            "kind": "literal",
            "value_type": filler.value_type,
            "value": filler.value,
        }
    if isinstance(filler, BoundVariable):
        return {"kind": "bound_variable", "variable_ref": filler.variable_ref}
    if isinstance(filler, ApplicationFiller):
        return {"kind": "expression_node", "node_ref": filler.node_ref}
    return {"kind": "unresolved", "unresolved_ref": filler.unresolved_ref}


def _filler_from_dict(data: Mapping[str, Any]) -> Filler:
    if not isinstance(data, Mapping):
        raise ValueError("filler must be an object")
    kind = data.get("kind")
    if kind == "grounded":
        _exact_fields(data, frozenset({"kind", "target_ref"}), "grounded filler")
        return GroundedReference(_required(data["target_ref"], "target_ref"))
    if kind == "literal":
        _exact_fields(
            data, frozenset({"kind", "value_type", "value"}), "literal filler"
        )
        value_type = _required(data["value_type"], "value_type")
        return LiteralValue(value_type, data["value"])
    if kind == "bound_variable":
        _exact_fields(data, frozenset({"kind", "variable_ref"}), "variable filler")
        return BoundVariable(_required(data["variable_ref"], "variable_ref"))
    if kind == "expression_node":
        _exact_fields(data, frozenset({"kind", "node_ref"}), "expression filler")
        return ApplicationFiller(_required(data["node_ref"], "node_ref"))
    if kind == "unresolved":
        _exact_fields(data, frozenset({"kind", "unresolved_ref"}), "unresolved filler")
        return UnresolvedValue(_required(data["unresolved_ref"], "unresolved_ref"))
    raise ValueError(f"unknown filler kind: {kind}")


def _binding_dict(binding: RoleBinding) -> dict[str, Any]:
    return {"role_ref": binding.role_ref, "filler": _filler_dict(binding.filler)}


def _binding_from_dict(data: Mapping[str, Any]) -> RoleBinding:
    _exact_fields(data, frozenset({"role_ref", "filler"}), "role binding")
    filler = data["filler"]
    if not isinstance(filler, Mapping):
        raise ValueError("filler must be an object")
    return RoleBinding(
        _required(data["role_ref"], "role_ref"), _filler_from_dict(filler)
    )


def _application_from_dict(data: Mapping[str, Any]) -> SemanticApplication:
    _exact_fields(
        data,
        frozenset(
            {"application_ref", "operator", "predicate_ref", "roles", "qualifiers"}
        ),
        "semantic application",
    )
    return SemanticApplication(
        _required(data["application_ref"], "application_ref"),
        _required(data["operator"], "operator"),
        _required(data["predicate_ref"], "predicate_ref"),
        tuple(_binding_from_dict(item) for item in _wire_list(data["roles"], "roles")),
        tuple(
            _binding_from_dict(item)
            for item in _wire_list(data["qualifiers"], "qualifiers")
        ),
    )


def _scope_from_dict(data: Mapping[str, Any]) -> ScopeOperator:
    _exact_fields(
        data,
        frozenset({"scope_ref", "operator_type", "value_ref", "operand_ref"}),
        "scope operator",
    )
    return ScopeOperator(
        _required(data["scope_ref"], "scope_ref"),
        _required(data["operator_type"], "operator_type"),
        _required(data["value_ref"], "value_ref"),
        _required(data["operand_ref"], "operand_ref"),
    )


def _link_from_dict(data: Mapping[str, Any]) -> ExpressionLink:
    _exact_fields(
        data,
        frozenset({"link_ref", "link_type", "operand_refs"}),
        "expression link",
    )
    return ExpressionLink(
        _required(data["link_ref"], "link_ref"),
        _required(data["link_type"], "link_type"),
        tuple(
            _required(item, "operand_ref")
            for item in _wire_list(data["operand_refs"], "operand_refs")
        ),
    )


def _binder_from_dict(data: Mapping[str, Any]) -> VariableBinder:
    _exact_fields(
        data, frozenset({"binder_ref", "variable_ref", "body_ref"}), "variable binder"
    )
    return VariableBinder(
        _required(data["binder_ref"], "binder_ref"),
        _required(data["variable_ref"], "variable_ref"),
        _required(data["body_ref"], "body_ref"),
    )


def _unresolved_from_dict(data: Mapping[str, Any]) -> UnresolvedFiller:
    _exact_fields(
        data,
        frozenset(
            {
                "unresolved_ref",
                "owner_application_ref",
                "role_ref",
                "contribution_kind",
                "expected_kinds",
                "critical",
            }
        ),
        "unresolved filler",
    )
    return UnresolvedFiller(
        _required(data["unresolved_ref"], "unresolved_ref"),
        _required(data["owner_application_ref"], "owner_application_ref"),
        _required(data["role_ref"], "role_ref"),
        _required(data["contribution_kind"], "contribution_kind"),
        tuple(
            _required(item, "expected_kind")
            for item in _wire_list(data["expected_kinds"], "expected_kinds")
        ),
        data["critical"],
    )


@dataclass(frozen=True, init=False)
class SemanticExpression:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use SemanticExpression.create")

    expression_ref: str
    applications: tuple[SemanticApplication, ...]
    root_refs: tuple[str, ...]
    scope_operators: tuple[ScopeOperator, ...] = ()
    expression_links: tuple[ExpressionLink, ...] = ()
    binders: tuple[VariableBinder, ...] = ()
    unresolved_fillers: tuple[UnresolvedFiller, ...] = ()

    @classmethod
    def _from_canonical(
        cls,
        expression_ref: str,
        canonical: tuple[Any, ...],
    ) -> "SemanticExpression":
        value = object.__new__(cls)
        object.__setattr__(value, "expression_ref", expression_ref)
        for field, item in zip(
            (
                "applications",
                "root_refs",
                "scope_operators",
                "expression_links",
                "binders",
                "unresolved_fillers",
            ),
            canonical,
            strict=True,
        ):
            object.__setattr__(value, field, item)
        return value

    @classmethod
    def create(
        cls,
        *,
        applications: Iterable[SemanticApplication],
        root_refs: Iterable[str],
        scope_operators: Iterable[ScopeOperator] = (),
        expression_links: Iterable[ExpressionLink] = (),
        binders: Iterable[VariableBinder] = (),
        unresolved_fillers: Iterable[UnresolvedFiller] = (),
        bounds: ExpressionBounds | None = None,
    ) -> "SemanticExpression":
        limits = bounds or ExpressionBounds()
        raw = _RawExpression(
            _bounded_tuple(applications, limits.max_applications, "applications"),
            _bounded_tuple(root_refs, limits.max_roots, "roots"),
            _bounded_tuple(scope_operators, limits.max_scope_operators, "scopes"),
            _bounded_tuple(expression_links, limits.max_expression_links, "links"),
            _bounded_tuple(binders, limits.max_binders, "binders"),
            _bounded_tuple(
                unresolved_fillers, limits.max_unresolved_fillers, "unresolved fillers"
            ),
        )
        canonical = _canonicalize(raw, limits)
        material = _expression_material(*canonical)
        return cls._from_canonical(stable_ref("expression", material), canonical)

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": SEMANTIC_EXPRESSION_ABI_VERSION,
            "expression_ref": self.expression_ref,
            "applications": [
                {
                    "application_ref": app.application_ref,
                    "operator": app.operator,
                    "predicate_ref": app.predicate_ref,
                    "roles": [_binding_dict(item) for item in app.roles],
                    "qualifiers": [_binding_dict(item) for item in app.qualifiers],
                }
                for app in self.applications
            ],
            "root_refs": list(self.root_refs),
            "scope_operators": [vars(item) for item in self.scope_operators],
            "expression_links": [
                {**vars(item), "operand_refs": list(item.operand_refs)}
                for item in self.expression_links
            ],
            "binders": [vars(item) for item in self.binders],
            "unresolved_fillers": [
                {**vars(item), "expected_kinds": list(item.expected_kinds)}
                for item in self.unresolved_fillers
            ],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SemanticExpression":
        _exact_fields(
            data,
            frozenset(
                {
                    "abi_version",
                    "expression_ref",
                    "applications",
                    "root_refs",
                    "scope_operators",
                    "expression_links",
                    "binders",
                    "unresolved_fillers",
                }
            ),
            "SemanticExpression",
        )
        abi_version = data["abi_version"]
        if (
            type(abi_version) is not int
            or abi_version != SEMANTIC_EXPRESSION_ABI_VERSION
        ):
            raise ValueError("unsupported Semantic Expression ABI")
        rebuilt = cls.create(
            applications=(
                _application_from_dict(item)
                for item in _wire_list(data["applications"], "applications")
            ),
            root_refs=(
                _required(item, "root_ref")
                for item in _wire_list(data["root_refs"], "root_refs")
            ),
            scope_operators=(
                _scope_from_dict(item)
                for item in _wire_list(data["scope_operators"], "scope_operators")
            ),
            expression_links=(
                _link_from_dict(item)
                for item in _wire_list(data["expression_links"], "expression_links")
            ),
            binders=(
                _binder_from_dict(item)
                for item in _wire_list(data["binders"], "binders")
            ),
            unresolved_fillers=(
                _unresolved_from_dict(item)
                for item in _wire_list(data["unresolved_fillers"], "unresolved_fillers")
            ),
        )
        if rebuilt.expression_ref != data["expression_ref"]:
            raise ValueError("expression_ref mismatch")
        if rebuilt.as_dict() != dict(data):
            raise ValueError("non-canonical expression encoding")
        return rebuilt


@dataclass(frozen=True)
class _RawExpression:
    applications: tuple[SemanticApplication, ...]
    root_refs: tuple[str, ...]
    scope_operators: tuple[ScopeOperator, ...]
    expression_links: tuple[ExpressionLink, ...]
    binders: tuple[VariableBinder, ...]
    unresolved_fillers: tuple[UnresolvedFiller, ...]


def _node_edges(node: Node) -> tuple[str, ...]:
    if isinstance(node, SemanticApplication):
        return tuple(
            binding.filler.node_ref
            for binding in node.roles + node.qualifiers
            if isinstance(binding.filler, ApplicationFiller)
        )
    if isinstance(node, ScopeOperator):
        return (node.operand_ref,)
    if isinstance(node, ExpressionLink):
        return node.operand_refs
    return (node.body_ref,)


def _canonicalize(raw: _RawExpression, bounds: ExpressionBounds) -> tuple[Any, ...]:
    if not 1 <= len(raw.applications) <= bounds.max_applications:
        raise ValueError("application bound violated")
    if not 1 <= len(raw.root_refs) <= bounds.max_roots:
        raise ValueError("root bound violated")
    if len(raw.scope_operators) > bounds.max_scope_operators:
        raise ValueError("scope bound violated")
    if len(raw.expression_links) > bounds.max_expression_links:
        raise ValueError("link bound violated")
    if len(raw.binders) > bounds.max_binders:
        raise ValueError("binder bound violated")
    if len(raw.unresolved_fillers) > bounds.max_unresolved_fillers:
        raise ValueError("unresolved filler bound violated")
    all_nodes: tuple[Node, ...] = (
        raw.applications + raw.scope_operators + raw.expression_links + raw.binders
    )
    if len(all_nodes) > bounds.max_total_nodes:
        raise ValueError("total node bound violated")
    refs = [
        node.application_ref
        if isinstance(node, SemanticApplication)
        else node.scope_ref
        if isinstance(node, ScopeOperator)
        else node.link_ref
        if isinstance(node, ExpressionLink)
        else node.binder_ref
        for node in all_nodes
    ]
    if len(refs) != len(set(refs)):
        raise ValueError("duplicate expression node ref")
    nodes = dict(zip(refs, all_nodes, strict=True))
    if len(raw.root_refs) != len(set(raw.root_refs)):
        raise ValueError("duplicate root ref")
    if any(ref not in nodes for ref in raw.root_refs):
        raise ValueError("unknown root ref")
    parents = {ref: 0 for ref in refs}
    for node in all_nodes:
        if isinstance(node, SemanticApplication) and (
            len(node.roles) + len(node.qualifiers) > bounds.max_roles_per_application
        ):
            raise ValueError("role bound violated")
        if (
            isinstance(node, ExpressionLink)
            and len(node.operand_refs) > bounds.max_link_operands
        ):
            raise ValueError("link operand bound violated")
        for child in _node_edges(node):
            if child not in nodes:
                raise ValueError(f"dangling expression node ref: {child}")
            parents[child] += 1
    root_set = set(raw.root_refs)
    if any(parents[ref] != 0 for ref in root_set):
        raise ValueError("root has a parent")
    if any(parents[ref] != 1 for ref in set(refs) - root_set):
        raise ValueError("every non-root node must have exactly one parent")

    unresolved = {item.unresolved_ref: item for item in raw.unresolved_fillers}
    if len(unresolved) != len(raw.unresolved_fillers):
        raise ValueError("duplicate unresolved filler ref")
    used_unresolved: set[str] = set()
    binder_vars = [item.variable_ref for item in raw.binders]
    if len(binder_vars) != len(set(binder_vars)):
        raise ValueError("duplicate binder variable ref")

    visiting: set[str] = set()
    seen: set[str] = set()
    max_depth = 0

    def validate(ref: str, environment: frozenset[str], depth: int) -> None:
        nonlocal max_depth
        if ref in visiting:
            raise ValueError("expression cycle")
        visiting.add(ref)
        seen.add(ref)
        max_depth = max(max_depth, depth)
        node = nodes[ref]
        next_environment = environment
        if isinstance(node, VariableBinder):
            next_environment = environment | {node.variable_ref}
        if isinstance(node, SemanticApplication):
            for binding in node.roles + node.qualifiers:
                filler = binding.filler
                if (
                    isinstance(filler, BoundVariable)
                    and filler.variable_ref not in environment
                ):
                    raise ValueError(f"unbound variable: {filler.variable_ref}")
                if isinstance(filler, UnresolvedValue):
                    item = unresolved.get(filler.unresolved_ref)
                    if item is None:
                        raise ValueError("unknown unresolved filler")
                    if (
                        item.owner_application_ref != ref
                        or item.role_ref != binding.role_ref
                    ):
                        raise ValueError("unresolved owner/role mismatch")
                    if filler.unresolved_ref in used_unresolved:
                        raise ValueError("unresolved filler used more than once")
                    used_unresolved.add(filler.unresolved_ref)
        for child in _node_edges(node):
            validate(child, next_environment, depth + 1)
        visiting.remove(ref)

    for root in raw.root_refs:
        validate(root, frozenset(), 1)
    if seen != set(refs):
        raise ValueError("unreachable expression node")
    if used_unresolved != set(unresolved):
        raise ValueError("unreferenced unresolved filler")
    if max_depth > bounds.max_depth:
        raise ValueError("expression depth bound violated")

    def semantic(ref: str, env: tuple[str, ...]) -> Any:
        node = nodes[ref]
        if isinstance(node, SemanticApplication):

            def fill(binding: RoleBinding) -> Any:
                filler = binding.filler
                if isinstance(filler, GroundedReference):
                    value = ("grounded", filler.target_ref)
                elif isinstance(filler, LiteralValue):
                    value = ("literal", filler.value_type, filler.value)
                elif isinstance(filler, BoundVariable):
                    value = ("variable", len(env) - 1 - env.index(filler.variable_ref))
                elif isinstance(filler, ApplicationFiller):
                    value = ("node", semantic(filler.node_ref, env))
                else:
                    item = unresolved[filler.unresolved_ref]
                    value = (
                        "unresolved",
                        item.contribution_kind,
                        tuple(sorted(item.expected_kinds)),
                        item.critical,
                    )
                return (binding.role_ref, value)

            return (
                "application",
                node.operator,
                node.predicate_ref,
                tuple(sorted((fill(item) for item in node.roles), key=canonical_bytes)),
                tuple(
                    sorted(
                        (fill(item) for item in node.qualifiers), key=canonical_bytes
                    )
                ),
            )
        if isinstance(node, ScopeOperator):
            return (
                "scope",
                node.operator_type,
                node.value_ref,
                semantic(node.operand_ref, env),
            )
        if isinstance(node, ExpressionLink):
            operands = [semantic(item, env) for item in node.operand_refs]
            if node.link_type in REVIEWED_COMMUTATIVE_LINK_TYPES:
                operands.sort(key=canonical_bytes)
            return ("link", node.link_type, tuple(operands))
        return ("binder", semantic(node.body_ref, env + (node.variable_ref,)))

    ordered_roots = sorted(
        raw.root_refs, key=lambda ref: canonical_bytes(semantic(ref, ()))
    )
    counters = {
        "application": 0,
        "scope": 0,
        "link": 0,
        "binder": 0,
        "variable": 0,
        "unresolved": 0,
    }
    out_apps: list[SemanticApplication] = []
    out_scopes: list[ScopeOperator] = []
    out_links: list[ExpressionLink] = []
    out_binders: list[VariableBinder] = []
    out_unresolved: list[UnresolvedFiller] = []

    def allocate(kind: str) -> str:
        value = f"{kind}:{counters[kind]}"
        counters[kind] += 1
        return value

    def clone(ref: str, env: Mapping[str, str]) -> str:
        node = nodes[ref]
        if isinstance(node, SemanticApplication):
            new_ref = allocate("application")

            def clone_binding(binding: RoleBinding) -> RoleBinding:
                filler = binding.filler
                if isinstance(filler, BoundVariable):
                    new_filler: Filler = BoundVariable(env[filler.variable_ref])
                elif isinstance(filler, ApplicationFiller):
                    new_filler = ApplicationFiller(clone(filler.node_ref, env))
                elif isinstance(filler, UnresolvedValue):
                    item = unresolved[filler.unresolved_ref]
                    new_unresolved_ref = allocate("unresolved")
                    out_unresolved.append(
                        UnresolvedFiller(
                            new_unresolved_ref,
                            new_ref,
                            binding.role_ref,
                            item.contribution_kind,
                            tuple(sorted(item.expected_kinds)),
                            item.critical,
                        )
                    )
                    new_filler = UnresolvedValue(new_unresolved_ref)
                else:
                    new_filler = filler
                return RoleBinding(binding.role_ref, new_filler)

            roles = tuple(
                clone_binding(item)
                for item in sorted(node.roles, key=lambda item: item.role_ref)
            )
            qualifiers = tuple(
                clone_binding(item)
                for item in sorted(node.qualifiers, key=lambda item: item.role_ref)
            )
            out_apps.append(
                SemanticApplication(
                    new_ref, node.operator, node.predicate_ref, roles, qualifiers
                )
            )
            return new_ref
        if isinstance(node, ScopeOperator):
            new_ref = allocate("scope")
            operand = clone(node.operand_ref, env)
            out_scopes.append(
                ScopeOperator(new_ref, node.operator_type, node.value_ref, operand)
            )
            return new_ref
        if isinstance(node, ExpressionLink):
            new_ref = allocate("link")
            operands = list(node.operand_refs)
            if node.link_type in REVIEWED_COMMUTATIVE_LINK_TYPES:
                operands.sort(
                    key=lambda item: canonical_bytes(semantic(item, tuple(env)))
                )
            cloned = tuple(clone(item, env) for item in operands)
            out_links.append(ExpressionLink(new_ref, node.link_type, cloned))
            return new_ref
        new_ref = allocate("binder")
        new_variable = f"?v{counters['variable']}"
        counters["variable"] += 1
        next_env = dict(env)
        next_env[node.variable_ref] = new_variable
        body = clone(node.body_ref, next_env)
        out_binders.append(VariableBinder(new_ref, new_variable, body))
        return new_ref

    canonical_roots = tuple(clone(ref, {}) for ref in ordered_roots)
    return (
        tuple(out_apps),
        canonical_roots,
        tuple(out_scopes),
        tuple(out_links),
        tuple(out_binders),
        tuple(out_unresolved),
    )


def _expression_material(
    applications: tuple[SemanticApplication, ...],
    root_refs: tuple[str, ...],
    scope_operators: tuple[ScopeOperator, ...],
    expression_links: tuple[ExpressionLink, ...],
    binders: tuple[VariableBinder, ...],
    unresolved_fillers: tuple[UnresolvedFiller, ...],
) -> dict[str, Any]:
    return {
        "abi_version": SEMANTIC_EXPRESSION_ABI_VERSION,
        "applications": applications,
        "root_refs": root_refs,
        "scope_operators": scope_operators,
        "expression_links": expression_links,
        "binders": binders,
        "unresolved_fillers": unresolved_fillers,
    }


_TRANSLATION_DISPOSITIONS = frozenset({"translated", "validated", "retained"})


@dataclass(frozen=True)
class TranslationRow:
    source_ref: str
    disposition: str
    target_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _required(self.source_ref, "translation source_ref")
        if self.disposition not in _TRANSLATION_DISPOSITIONS:
            raise ValueError("invalid translation disposition")
        targets = _bounded_tuple(self.target_refs, 32, "translation targets")
        object.__setattr__(self, "target_refs", targets)
        if not targets:
            raise ValueError("translation row requires at least one target")
        for target in targets:
            _required(target, "translation target_ref")

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_ref": self.source_ref,
            "disposition": self.disposition,
            "target_refs": list(self.target_refs),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TranslationRow":
        _exact_fields(
            data,
            frozenset({"source_ref", "disposition", "target_refs"}),
            "TranslationRow",
        )
        row = cls(
            _required(data["source_ref"], "translation source_ref"),
            _required(data["disposition"], "translation disposition"),
            tuple(
                _required(item, "translation target_ref")
                for item in _wire_list(data["target_refs"], "target_refs")
            ),
        )
        if row.as_dict() != dict(data):
            raise ValueError("non-canonical TranslationRow encoding")
        return row


@dataclass(frozen=True, init=False)
class CompilationProof:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use CompilationProof.create")

    proof_ref: str
    program_ref: str
    proposal_context_ref: str
    expression_ref: str
    action_translations: tuple[TranslationRow, ...]
    assignment_translations: tuple[TranslationRow, ...]
    root_translations: tuple[TranslationRow, ...]
    grounding_refs: tuple[str, ...]
    revision_pin: RevisionPin

    @classmethod
    def _from_canonical(cls, proof_ref: str, **values: Any) -> "CompilationProof":
        value = object.__new__(cls)
        object.__setattr__(value, "proof_ref", proof_ref)
        for field, item in values.items():
            object.__setattr__(value, field, item)
        return value

    @classmethod
    def create(
        cls,
        *,
        program_ref: str,
        proposal_context_ref: str,
        expression_ref: str,
        action_translations: Iterable[TranslationRow],
        assignment_translations: Iterable[TranslationRow],
        root_translations: Iterable[TranslationRow],
        grounding_refs: Iterable[str],
        revision_pin: RevisionPin,
    ) -> "CompilationProof":
        program_ref = _required(program_ref, "program_ref")
        proposal_context_ref = _required(proposal_context_ref, "proposal_context_ref")
        expression_ref = _required(expression_ref, "expression_ref")
        action_rows = _bounded_tuple(action_translations, 208, "action translations")
        assignment_rows = _bounded_tuple(
            assignment_translations, 64, "assignment translations"
        )
        root_rows = _bounded_tuple(root_translations, 8, "root translations")
        grounding_items = _bounded_tuple(grounding_refs, 96, "grounding refs")
        if not action_rows or not root_rows:
            raise ValueError("compilation proof requires action and root translations")
        for label, rows in (
            ("action", action_rows),
            ("assignment", assignment_rows),
            ("root", root_rows),
        ):
            if any(not isinstance(row, TranslationRow) for row in rows):
                raise ValueError(f"{label} translations require TranslationRow values")
            refs = tuple(row.source_ref for row in rows)
            if len(refs) != len(set(refs)):
                raise ValueError(f"duplicate {label} translation source")
        for grounding_ref in grounding_items:
            _required(grounding_ref, "grounding_ref")
        grounding = tuple(sorted(set(grounding_items)))
        if not grounding:
            raise ValueError("compilation proof requires grounding refs")
        if not isinstance(revision_pin, RevisionPin):
            raise ValueError("revision_pin must be RevisionPin")
        material = {
            "abi_version": 1,
            "program_ref": program_ref,
            "proposal_context_ref": proposal_context_ref,
            "expression_ref": expression_ref,
            "action_translations": [row.as_dict() for row in action_rows],
            "assignment_translations": [row.as_dict() for row in assignment_rows],
            "root_translations": [row.as_dict() for row in root_rows],
            "grounding_refs": list(grounding),
            "revision_pin": revision_pin.as_dict(),
        }
        return cls._from_canonical(
            stable_ref("compilation_proof", material),
            program_ref=program_ref,
            proposal_context_ref=proposal_context_ref,
            expression_ref=expression_ref,
            action_translations=action_rows,
            assignment_translations=assignment_rows,
            root_translations=root_rows,
            grounding_refs=grounding,
            revision_pin=revision_pin,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": 1,
            "proof_ref": self.proof_ref,
            "program_ref": self.program_ref,
            "proposal_context_ref": self.proposal_context_ref,
            "expression_ref": self.expression_ref,
            "action_translations": [row.as_dict() for row in self.action_translations],
            "assignment_translations": [
                row.as_dict() for row in self.assignment_translations
            ],
            "root_translations": [row.as_dict() for row in self.root_translations],
            "grounding_refs": list(self.grounding_refs),
            "revision_pin": self.revision_pin.as_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CompilationProof":
        _exact_fields(
            data,
            frozenset(
                {
                    "abi_version",
                    "proof_ref",
                    "program_ref",
                    "proposal_context_ref",
                    "expression_ref",
                    "action_translations",
                    "assignment_translations",
                    "root_translations",
                    "grounding_refs",
                    "revision_pin",
                }
            ),
            "CompilationProof",
        )
        abi_version = data["abi_version"]
        if type(abi_version) is not int or abi_version != 1:
            raise ValueError("unsupported Compilation Proof ABI")
        pin_data = data["revision_pin"]
        if not isinstance(pin_data, Mapping):
            raise ValueError("revision_pin must be an object")
        proof = cls.create(
            program_ref=_required(data["program_ref"], "program_ref"),
            proposal_context_ref=_required(
                data["proposal_context_ref"], "proposal_context_ref"
            ),
            expression_ref=_required(data["expression_ref"], "expression_ref"),
            action_translations=(
                TranslationRow.from_dict(item)
                for item in _wire_list(
                    data["action_translations"], "action_translations"
                )
            ),
            assignment_translations=(
                TranslationRow.from_dict(item)
                for item in _wire_list(
                    data["assignment_translations"], "assignment_translations"
                )
            ),
            root_translations=(
                TranslationRow.from_dict(item)
                for item in _wire_list(data["root_translations"], "root_translations")
            ),
            grounding_refs=(
                _required(item, "grounding_ref")
                for item in _wire_list(data["grounding_refs"], "grounding_refs")
            ),
            revision_pin=RevisionPin.from_dict(pin_data),
        )
        if data["proof_ref"] != proof.proof_ref:
            raise ValueError("CompilationProof proof_ref mismatch")
        if proof.as_dict() != dict(data):
            raise ValueError("non-canonical CompilationProof encoding")
        return proof


@dataclass(frozen=True)
class CompilationFailure:
    code: str
    detail: str
    action_ref: str | None = None

    def __post_init__(self) -> None:
        _required(self.code, "compilation failure code")
        if not isinstance(self.detail, str):
            raise ValueError("compilation failure detail must be a string")
        if self.action_ref is not None:
            _required(self.action_ref, "compilation failure action_ref")


@dataclass(frozen=True)
class CompilationSuccess:
    expression: SemanticExpression
    proof: CompilationProof

    def __post_init__(self) -> None:
        if self.proof.expression_ref != self.expression.expression_ref:
            raise ValueError("compilation proof expression mismatch")


class SemanticExpressionCompiler:
    """Compile the bounded R1 Program ABI 2 subset into canonical meaning."""

    _R2_ONLY_ACTIONS = frozenset(
        {
            "bind_nested_application",
            "attach_scope",
            "project_variable",
            "propose_transition",
        }
    )

    @staticmethod
    def _failure(
        code: str, detail: str, action_ref: str | None = None
    ) -> CompilationFailure:
        return CompilationFailure(code, detail, action_ref)

    def compile(
        self, program: Any, context: Any
    ) -> CompilationSuccess | CompilationFailure:
        if program.proposal_context_ref != context.context_ref:
            return self._failure(
                "proposal_context_mismatch",
                "program does not bind the supplied proposal context",
            )
        if program.orientation_ref != context.orientation_ref:
            return self._failure(
                "orientation_mismatch", "program and context orientation differ"
            )
        if program.revision_pin != context.revision_pin:
            return self._failure(
                "revision_mismatch", "program and context revision pins differ"
            )
        if context.mode_slot(program.mode_slot_ref) is None:
            return self._failure("unknown_mode_slot", "mode slot is not in context")
        for action in program.actions:
            if action.action_type in self._R2_ONLY_ACTIONS:
                return self._failure(
                    "action_shape_not_admitted",
                    f"{action.action_type} is registered for R2 but not admitted in R1",
                    action.action_ref,
                )
        instantiate_actions = tuple(
            action
            for action in program.actions
            if action.action_type == "instantiate_operator"
        )
        if len(instantiate_actions) != 1:
            return self._failure(
                "action_shape_not_admitted",
                "R1 compilation requires exactly one application",
            )
        if program.actions[-1].action_type == "abstain":
            return self._failure(
                "abstain_program", "abstention has no semantic expression"
            )

        grounding: set[str] = set()
        for action in program.actions:
            if action.action_type != "select_designation":
                continue
            slot = context.designation(action.arguments[0])
            if slot is None:
                return self._failure(
                    "unknown_designation_slot",
                    "designation pointer is not in context",
                    action.action_ref,
                )
            grounding.add(slot.slot_ref)
            grounding.add(slot.target_ref)
            grounding.add(slot.designation_fact_ref)
            grounding.update(slot.provenance_refs)

        instantiate = instantiate_actions[0]
        application_local_ref, frame_slot_ref = instantiate.arguments
        frame = context.frame(frame_slot_ref)
        if frame is None:
            return self._failure(
                "unknown_application_frame",
                "application frame pointer is not in context",
                instantiate.action_ref,
            )
        if frame.operator_ref not in PERSISTENT_OPERATORS:
            return self._failure(
                "invalid_operator",
                "frame does not lower to a kernel operator",
                instantiate.action_ref,
            )
        if frame.proposition_roles:
            return self._failure(
                "action_shape_not_admitted",
                "proposition-valued frame roles are admitted in R2",
                instantiate.action_ref,
            )
        grounding.add(frame.predicate_target_ref)
        grounding.update(target_ref for _, target_ref in frame.derived_role_targets)
        roles: dict[str, RoleBinding] = {
            role_ref: RoleBinding(role_ref, GroundedReference(target_ref))
            for role_ref, target_ref in frame.derived_role_targets
        }
        role_action_targets: dict[str, tuple[str, str]] = {}

        for action in program.actions:
            if action.action_type not in {"bind_role", "bind_reference"}:
                continue
            target_application, role_ref, slot_ref = action.arguments
            if target_application != application_local_ref:
                return self._failure(
                    "unknown_application_ref",
                    "binding does not target the R1 application",
                    action.action_ref,
                )
            if role_ref in roles:
                return self._failure(
                    "duplicate_role_binding",
                    "application role was bound twice",
                    action.action_ref,
                )
            if role_ref not in set(frame.required_roles) | set(frame.optional_roles):
                return self._failure(
                    "frame_role_mismatch",
                    "role is not licensed by the application frame",
                    action.action_ref,
                )
            if action.action_type == "bind_role":
                slot = context.contribution(slot_ref)
                if slot is None:
                    return self._failure(
                        "unknown_contribution_slot",
                        "contribution pointer is not in context",
                        action.action_ref,
                    )
                if role_ref not in slot.output_ports:
                    return self._failure(
                        "contribution_role_mismatch",
                        "contribution does not expose the selected role port",
                        action.action_ref,
                    )
                if slot.target_ref is not None:
                    filler: Filler = GroundedReference(slot.target_ref)
                    grounding.add(slot.target_ref)
                elif slot.literal_value is not None:
                    filler = LiteralValue("string", slot.literal_value)
                else:
                    return self._failure(
                        "unresolved_contribution",
                        "R1 cannot invent a filler for an unresolved contribution",
                        action.action_ref,
                    )
                grounding.update(slot.provenance_refs)
            else:
                slot = context.reference(slot_ref)
                if slot is None:
                    return self._failure(
                        "unknown_reference_slot",
                        "reference pointer is not in context",
                        action.action_ref,
                    )
                if role_ref not in slot.compatible_roles:
                    return self._failure(
                        "reference_role_mismatch",
                        "reference slot is incompatible with the selected role",
                        action.action_ref,
                    )
                filler = GroundedReference(slot.target_ref)
                grounding.add(slot.target_ref)
                grounding.update(slot.provenance_refs)
            roles[role_ref] = RoleBinding(role_ref, filler)
            role_action_targets[action.action_ref] = (application_local_ref, role_ref)

        missing_roles = tuple(
            role for role in frame.required_roles if role not in roles
        )
        if missing_roles:
            return self._failure(
                "missing_required_role",
                f"application is missing required roles: {', '.join(missing_roles)}",
                instantiate.action_ref,
            )
        if tuple(program.root_refs) != (application_local_ref,):
            return self._failure(
                "action_shape_not_admitted",
                "R1 compilation supports one application root",
            )
        application = SemanticApplication(
            application_local_ref,
            frame.operator_ref,
            frame.predicate_target_ref,
            tuple(roles[role_ref] for role_ref in sorted(roles)),
        )
        expression = SemanticExpression.create(
            applications=(application,), root_refs=(application_local_ref,)
        )
        canonical_application_ref = expression.root_refs[0]

        action_rows: list[TranslationRow] = []
        for action in program.actions:
            if action.action_type == "select_context":
                disposition, targets = "validated", (context.context_ref,)
            elif action.action_type == "select_mode":
                disposition, targets = "validated", (program.mode_slot_ref,)
            elif action.action_type == "select_designation":
                disposition, targets = "validated", (action.arguments[0],)
            elif action.action_type == "instantiate_operator":
                disposition, targets = "translated", (canonical_application_ref,)
            elif action.action_type in {"bind_role", "bind_reference"}:
                _, role_ref = role_action_targets[action.action_ref]
                disposition, targets = (
                    "translated",
                    (
                        canonical_application_ref,
                        role_ref,
                    ),
                )
            elif action.action_type == "complete_program":
                disposition, targets = "translated", (expression.expression_ref,)
            else:
                raise AssertionError(f"unhandled admitted action: {action.action_type}")
            action_rows.append(TranslationRow(action.action_ref, disposition, targets))

        assignment_rows = tuple(
            TranslationRow(
                assignment.assignment_ref,
                "retained"
                if assignment.assignment_kind == "residual"
                else "translated",
                tuple(
                    target
                    for target in (
                        assignment.target_action_ref
                        or assignment.contribution_slot_ref,
                        assignment.target_role_ref,
                    )
                    if target is not None
                ),
            )
            for assignment in program.source_assignments
        )
        root_rows = (
            TranslationRow(
                application_local_ref,
                "translated",
                (canonical_application_ref,),
            ),
        )
        proof = CompilationProof.create(
            program_ref=program.program_ref,
            proposal_context_ref=context.context_ref,
            expression_ref=expression.expression_ref,
            action_translations=tuple(action_rows),
            assignment_translations=assignment_rows,
            root_translations=root_rows,
            grounding_refs=grounding,
            revision_pin=program.revision_pin,
        )
        return CompilationSuccess(expression, proof)


@dataclass(frozen=True, init=False)
class VerifiedMeaning:
    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use VerifiedMeaning.create")

    verified_meaning_ref: str
    program_ref: str
    expression: SemanticExpression
    grounding_refs: tuple[str, ...]
    coverage_receipt_ref: str
    compilation_proof_ref: str
    verification_receipt_ref: str
    revision_pin: RevisionPin

    @classmethod
    def _from_canonical(
        cls,
        *,
        verified_meaning_ref: str,
        program_ref: str,
        expression: SemanticExpression,
        grounding_refs: tuple[str, ...],
        coverage_receipt_ref: str,
        compilation_proof_ref: str,
        verification_receipt_ref: str,
        revision_pin: RevisionPin,
    ) -> "VerifiedMeaning":
        value = object.__new__(cls)
        for field, item in (
            ("verified_meaning_ref", verified_meaning_ref),
            ("program_ref", program_ref),
            ("expression", expression),
            ("grounding_refs", grounding_refs),
            ("coverage_receipt_ref", coverage_receipt_ref),
            ("compilation_proof_ref", compilation_proof_ref),
            ("verification_receipt_ref", verification_receipt_ref),
            ("revision_pin", revision_pin),
        ):
            object.__setattr__(value, field, item)
        return value

    @classmethod
    def create(
        cls,
        *,
        program_ref: str,
        expression: SemanticExpression,
        grounding_refs: Iterable[str],
        coverage_receipt_ref: str,
        compilation_proof_ref: str,
        verification_receipt_ref: str,
        revision_pin: RevisionPin,
    ) -> "VerifiedMeaning":
        for name, value in (
            ("program_ref", program_ref),
            ("coverage_receipt_ref", coverage_receipt_ref),
            ("compilation_proof_ref", compilation_proof_ref),
            ("verification_receipt_ref", verification_receipt_ref),
        ):
            _required(value, name)
        if not isinstance(expression, SemanticExpression):
            raise ValueError("expression must be a canonical SemanticExpression")
        expected_expression_ref = stable_ref(
            "expression",
            _expression_material(
                expression.applications,
                expression.root_refs,
                expression.scope_operators,
                expression.expression_links,
                expression.binders,
                expression.unresolved_fillers,
            ),
        )
        if expression.expression_ref != expected_expression_ref:
            raise ValueError("expression_ref mismatch")
        grounding_items = _bounded_tuple(
            grounding_refs, _MAX_GROUNDING_REFS, "grounding refs"
        )
        for item in grounding_items:
            _required(item, "grounding_ref")
        grounding = tuple(sorted(set(grounding_items)))
        if not grounding:
            raise ValueError("grounding_refs must be non-empty")
        if not isinstance(revision_pin, RevisionPin):
            raise ValueError("revision_pin must be RevisionPin")
        material = {
            "abi_version": 1,
            "program_ref": program_ref,
            "expression_ref": expression.expression_ref,
            "grounding_refs": grounding,
            "coverage_receipt_ref": coverage_receipt_ref,
            "compilation_proof_ref": compilation_proof_ref,
            "verification_receipt_ref": verification_receipt_ref,
            "revision_pin": revision_pin.as_dict(),
        }
        return cls._from_canonical(
            verified_meaning_ref=stable_ref("verified_meaning", material),
            program_ref=program_ref,
            expression=expression,
            grounding_refs=grounding,
            coverage_receipt_ref=coverage_receipt_ref,
            compilation_proof_ref=compilation_proof_ref,
            verification_receipt_ref=verification_receipt_ref,
            revision_pin=revision_pin,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": 1,
            "verified_meaning_ref": self.verified_meaning_ref,
            "program_ref": self.program_ref,
            "expression": self.expression.as_dict(),
            "grounding_refs": list(self.grounding_refs),
            "coverage_receipt_ref": self.coverage_receipt_ref,
            "compilation_proof_ref": self.compilation_proof_ref,
            "verification_receipt_ref": self.verification_receipt_ref,
            "revision_pin": self.revision_pin.as_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "VerifiedMeaning":
        _exact_fields(
            data,
            frozenset(
                {
                    "abi_version",
                    "verified_meaning_ref",
                    "program_ref",
                    "expression",
                    "grounding_refs",
                    "coverage_receipt_ref",
                    "compilation_proof_ref",
                    "verification_receipt_ref",
                    "revision_pin",
                }
            ),
            "VerifiedMeaning",
        )
        abi_version = data["abi_version"]
        if type(abi_version) is not int or abi_version != 1:
            raise ValueError("unsupported Verified Meaning ABI")
        expression_data = data["expression"]
        pin_data = data["revision_pin"]
        if not isinstance(expression_data, Mapping):
            raise ValueError("expression must be an object")
        if not isinstance(pin_data, Mapping):
            raise ValueError("revision_pin must be an object")
        rebuilt = cls.create(
            program_ref=_required(data["program_ref"], "program_ref"),
            expression=SemanticExpression.from_dict(expression_data),
            grounding_refs=(
                _required(item, "grounding_ref")
                for item in _wire_list(data["grounding_refs"], "grounding_refs")
            ),
            coverage_receipt_ref=_required(
                data["coverage_receipt_ref"], "coverage_receipt_ref"
            ),
            compilation_proof_ref=_required(
                data["compilation_proof_ref"], "compilation_proof_ref"
            ),
            verification_receipt_ref=_required(
                data["verification_receipt_ref"], "verification_receipt_ref"
            ),
            revision_pin=RevisionPin.from_dict(pin_data),
        )
        if rebuilt.verified_meaning_ref != data["verified_meaning_ref"]:
            raise ValueError("verified_meaning_ref mismatch")
        if rebuilt.as_dict() != dict(data):
            raise ValueError("non-canonical verified meaning encoding")
        return rebuilt
