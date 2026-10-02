"""Description ABI 2: request-first bounded semantic-neighbourhood artifacts.

Descriptions are transient reconstructions from indexed applications and active
claims. They are canonical meaning, never a construction program or a second
persistent definition store.

This module's codec validates canonical shape and internal cross-field
structure only.  The implemented, read-only Stage-10 builder in
``QueryDecisionOwner`` reconstructs descriptions from indexed normalized
generic claims during one pinned store read and verifies each claim's fact
projection and source/decision/occurrence/placement/proof lineage.  Public
dispatch and activation, production definition facts, R4 admission and R5
realization remain separate pending work. ``describe_with_proof`` retains each
signed claim and persistent application correspondence in a transient Proof
Bundle during that same read; structural decoding is not store authentication.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from .canonical import stable_ref
from .expressions import (
    ApplicationFiller,
    ExpressionLink,
    GroundedReference,
    ScopeOperator,
    SemanticApplication,
    SemanticExpression,
    UnresolvedValue,
    VariableBinder,
)
from .persistence import RevisionPin
from .cycle import SemanticMode
from .situation import SituationContext
from .r3_codec import freeze_json

DESCRIPTION_ABI_VERSION = 2
DESCRIPTION_MAX_DEPTH = 8
DESCRIPTION_MAX_FACTS = 256
DESCRIPTION_MAX_REFS = 64
_MAX_TEXT = 512

__all__ = [
    "DESCRIPTION_ABI_VERSION",
    "DESCRIPTION_MAX_DEPTH",
    "DESCRIPTION_MAX_FACTS",
    "DESCRIPTION_MAX_REFS",
    "DescriptionCompleteness",
    "DescriptionRequest",
    "DescriptionResult",
]


class DescriptionCompleteness(Enum):
    SUFFICIENT = "sufficient"
    PARTIAL = "partial"
    MISSING = "missing"
    CONFLICT = "conflict"
    BUDGET_EXHAUSTED = "budget_exhausted"


def _ref(value: object, name: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{name} must be exact str")
    if (
        not value
        or len(value) > _MAX_TEXT
        or ":" not in value
        or any(char.isspace() for char in value)
        or any(not part for part in value.split(":"))
    ):
        raise ValueError(f"{name} must be one bounded semantic ref")
    return value


def _namespaced_ref(value: object, name: str, namespace: str) -> str:
    ref = _ref(value, name)
    if not ref.startswith(namespace + ":"):
        raise ValueError(f"{name} must use the {namespace} namespace")
    return ref


def _pin(value: object) -> RevisionPin:
    if type(value) is not RevisionPin:
        raise TypeError("revision_pin must be exact RevisionPin")
    if RevisionPin.from_dict(value.as_dict()) != value:
        raise ValueError("revision_pin must be canonical")
    return value


def _refs(
    value: object, name: str, *, maximum: int = DESCRIPTION_MAX_REFS
) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{name} must be exact tuple")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds Description ABI bound")
    checked = tuple(_ref(item, f"{name} item") for item in value)
    if len(checked) != len(set(checked)):
        raise ValueError(f"{name} must contain unique refs")
    return checked


def _wire_refs(
    value: object, name: str, *, maximum: int = DESCRIPTION_MAX_REFS
) -> tuple[str, ...]:
    if type(value) is not list:
        raise TypeError(f"{name} must be exact list")
    return _refs(tuple(value), name, maximum=maximum)


def _fact_refs(value: object, *, maximum: int) -> tuple[str, ...]:
    refs = _refs(value, "fact_refs", maximum=maximum)
    if any(not ref.startswith("fact:") for ref in refs):
        raise ValueError("fact_refs items must use the fact namespace")
    return refs


def _exact_dict(
    value: object, fields: frozenset[str], name: str
) -> dict[str, Any]:
    if type(value) is not dict:
        raise TypeError(f"{name} payload must be exact dict")
    if frozenset(value) != fields:
        raise ValueError(f"{name} fields mismatch")
    if any(type(key) is not str for key in value):
        raise TypeError(f"{name} field names must be exact str")
    freeze_json(value)
    pending = [value]
    while pending:
        item = pending.pop()
        if type(item) is dict:
            pending.extend(item.values())
        elif type(item) is list:
            pending.extend(item)
        elif item is not None and type(item) not in {str, bool, int, float}:
            raise TypeError(f"{name} wire values must be exact JSON types")
    return value


_STRUCTURAL_TARGET_ROLES = {
    "op:designation": frozenset({"role:label_type", "role:surface"}),
    "op:type": frozenset({"role:class", "role:type"}),
    "op:relation": frozenset({"role:relation"}),
    "op:state": frozenset({"role:dimension", "role:value"}),
    "op:event": frozenset({"role:event", "role:type"}),
}


def _answer_is_centered_on_target(
    expression: SemanticExpression, target_ref: str
) -> bool:
    for app in expression.applications:
        structural_roles = _STRUCTURAL_TARGET_ROLES[app.operator]
        for binding in app.roles:
            if (
                binding.role_ref not in structural_roles
                and isinstance(binding.filler, GroundedReference)
                and binding.filler.target_ref == target_ref
            ):
                return True
    return False


def _answer_depth(expression: SemanticExpression) -> int:
    nodes: dict[str, object] = {}
    nodes.update((app.application_ref, app) for app in expression.applications)
    nodes.update((scope.scope_ref, scope) for scope in expression.scope_operators)
    nodes.update((link.link_ref, link) for link in expression.expression_links)
    nodes.update((binder.binder_ref, binder) for binder in expression.binders)

    def children(node: object) -> tuple[str, ...]:
        if isinstance(node, SemanticApplication):
            return tuple(
                binding.filler.node_ref
                for binding in (*node.roles, *node.qualifiers)
                if isinstance(binding.filler, ApplicationFiller)
            )
        if isinstance(node, ScopeOperator):
            return (node.operand_ref,)
        if isinstance(node, ExpressionLink):
            return node.operand_refs
        if isinstance(node, VariableBinder):
            return (node.body_ref,)
        raise TypeError("unsupported semantic expression node")

    def depth(node_ref: str) -> int:
        descendants = children(nodes[node_ref])
        return 1 if not descendants else 1 + max(depth(ref) for ref in descendants)

    return max(depth(root_ref) for root_ref in expression.root_refs)


def _canonical_answer(value: object, target_ref: str) -> SemanticExpression:
    if type(value) is not SemanticExpression:
        raise TypeError("answer_expression must be exact SemanticExpression")
    if SemanticExpression.from_dict(value.as_dict()) != value:
        raise ValueError("answer_expression must be canonical")
    if value.query_projections:
        raise ValueError("description answer cannot contain a query projection")
    if value.unresolved_fillers or any(
        isinstance(binding.filler, UnresolvedValue)
        for app in value.applications
        for binding in (*app.roles, *app.qualifiers)
    ):
        raise ValueError("description answer cannot contain unresolved meaning")
    if not _answer_is_centered_on_target(value, target_ref):
        raise ValueError("description answer is not centered on its requested target")
    return value


@dataclass(frozen=True, init=False)
class DescriptionRequest:
    abi_version: int
    description_request_ref: str
    source_expression_ref: str
    source_projection_ref: str
    requested_content: str
    target_ref: str
    source_situation_ref: str
    max_depth: int
    max_facts: int
    revision_pin: RevisionPin

    _FIELDS = frozenset({
        "abi_version",
        "description_request_ref",
        "source_expression_ref",
        "source_projection_ref",
        "requested_content",
        "target_ref",
        "source_situation_ref",
        "max_depth",
        "max_facts",
        "revision_pin",
    })

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use DescriptionRequest.create")

    @classmethod
    def create(
        cls,
        *,
        source_expression: SemanticExpression,
        situation: SituationContext,
        max_depth: int,
        max_facts: int,
    ) -> "DescriptionRequest":
        if cls is not DescriptionRequest:
            raise TypeError("DescriptionRequest factory requires exact class")
        if type(source_expression) is not SemanticExpression:
            raise TypeError("description source expression must be exact SemanticExpression")
        if SemanticExpression.from_dict(source_expression.as_dict()) != source_expression:
            raise ValueError("description source expression must be canonical")
        if type(situation) is not SituationContext:
            raise TypeError("description source situation must be exact SituationContext")
        if SituationContext.from_dict(situation.as_dict()) != situation:
            raise ValueError("description source situation must be canonical")
        if situation.mode is not SemanticMode.QUERY:
            raise ValueError("description source requires QUERY mode")
        if (source_expression.applications or source_expression.scope_operators
                or source_expression.expression_links or source_expression.binders
                or source_expression.unresolved_fillers
                or len(source_expression.query_projections) != 1):
            raise ValueError("description source must be one pure query projection")
        projection = source_expression.query_projections[0]
        if source_expression.root_refs != (projection.projection_ref,):
            raise ValueError("description source must root its sole query projection")
        return cls._from_fields(
            source_expression_ref=source_expression.expression_ref,
            source_projection_ref=projection.projection_ref,
            requested_content=projection.requested_content,
            target_ref=projection.target_ref,
            source_situation_ref=situation.situation_ref,
            max_depth=max_depth, max_facts=max_facts, revision_pin=situation.revision_pin,
        )

    @classmethod
    def _from_fields(cls, *, source_expression_ref: str, source_projection_ref: str,
                     requested_content: str, target_ref: str, source_situation_ref: str,
                     max_depth: int, max_facts: int, revision_pin: RevisionPin) -> "DescriptionRequest":
        """Decode bounded identity fields; this does not authenticate their origin."""
        if cls is not DescriptionRequest:
            raise TypeError("DescriptionRequest factory requires exact class")
        expression = _namespaced_ref(source_expression_ref, "source_expression_ref", "expression")
        projection = _ref(source_projection_ref, "source_projection_ref")
        situation = _namespaced_ref(source_situation_ref, "source_situation_ref", "situation_context")
        if type(requested_content) is not str or requested_content not in {"description", "definition"}:
            raise ValueError("requested_content must be exact description or definition")
        target = _ref(target_ref, "target_ref")
        if type(max_depth) is not int or not 1 <= max_depth <= DESCRIPTION_MAX_DEPTH:
            raise ValueError("max_depth must be an exact int in 1..8")
        if type(max_facts) is not int or not 1 <= max_facts <= DESCRIPTION_MAX_FACTS:
            raise ValueError("max_facts must be an exact int in 1..256")
        pin = _pin(revision_pin)
        material = {
            "abi_version": DESCRIPTION_ABI_VERSION,
            "source_expression_ref": expression,
            "source_projection_ref": projection,
            "requested_content": requested_content,
            "target_ref": target,
            "source_situation_ref": situation,
            "max_depth": max_depth,
            "max_facts": max_facts,
            "revision_pin": pin.as_dict(),
        }
        result = object.__new__(cls)
        object.__setattr__(result, "abi_version", DESCRIPTION_ABI_VERSION)
        object.__setattr__(
            result,
            "description_request_ref",
            stable_ref("description_request", material),
        )
        for name, value in material.items():
            if name != "revision_pin":
                object.__setattr__(result, name, value)
        object.__setattr__(result, "revision_pin", pin)
        return result

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "description_request_ref": self.description_request_ref,
            "source_expression_ref": self.source_expression_ref,
            "source_projection_ref": self.source_projection_ref,
            "requested_content": self.requested_content,
            "target_ref": self.target_ref,
            "source_situation_ref": self.source_situation_ref,
            "max_depth": self.max_depth,
            "max_facts": self.max_facts,
            "revision_pin": self.revision_pin.as_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DescriptionRequest":
        row = _exact_dict(value, cls._FIELDS, "DescriptionRequest")
        if (
            type(row["abi_version"]) is not int
            or row["abi_version"] != DESCRIPTION_ABI_VERSION
        ):
            raise ValueError("unsupported Description ABI")
        if type(row["revision_pin"]) is not dict:
            raise TypeError("revision_pin must be an exact dict")
        rebuilt = cls._from_fields(
            source_expression_ref=row["source_expression_ref"],
            source_projection_ref=row["source_projection_ref"],
            requested_content=row["requested_content"],
            target_ref=row["target_ref"],
            source_situation_ref=row["source_situation_ref"],
            max_depth=row["max_depth"],
            max_facts=row["max_facts"],
            revision_pin=RevisionPin.from_dict(row["revision_pin"]),
        )
        _ref(row["description_request_ref"], "description_request_ref")
        if row["description_request_ref"] != rebuilt.description_request_ref:
            raise ValueError("description_request_ref mismatch")
        if rebuilt.as_dict() != row:
            raise ValueError("non-canonical DescriptionRequest")
        return rebuilt

    def validate_source(self, source_expression: SemanticExpression, situation: SituationContext) -> None:
        """Rematch actual source content, original situation and pin independently."""
        if type(self) is not DescriptionRequest or DescriptionRequest.from_dict(self.as_dict()) != self:
            raise ValueError("description request must be exact canonical source artifact")
        derived = DescriptionRequest.create(source_expression=source_expression, situation=situation,
            max_depth=self.max_depth, max_facts=self.max_facts)
        if derived != self:
            raise ValueError("description request source expression/situation/pin mismatch")


@dataclass(frozen=True, init=False)
class DescriptionResult:
    abi_version: int
    description_result_ref: str
    request: DescriptionRequest
    answer_expression: SemanticExpression | None
    completeness: DescriptionCompleteness
    fact_refs: tuple[str, ...]
    definition_refs: tuple[str, ...]
    claim_refs: tuple[str, ...]
    source_refs: tuple[str, ...]
    proof_refs: tuple[str, ...]
    revision_pin: RevisionPin

    _FIELDS = frozenset({
        "abi_version",
        "description_result_ref",
        "request",
        "answer_expression",
        "completeness",
        "fact_refs",
        "definition_refs",
        "claim_refs",
        "source_refs",
        "proof_refs",
        "revision_pin",
    })

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use DescriptionResult.create")

    @classmethod
    def create(
        cls,
        *,
        request: DescriptionRequest,
        answer_expression: SemanticExpression | None,
        completeness: DescriptionCompleteness,
        fact_refs: tuple[str, ...],
        definition_refs: tuple[str, ...],
        claim_refs: tuple[str, ...],
        source_refs: tuple[str, ...],
        proof_refs: tuple[str, ...],
        revision_pin: RevisionPin,
    ) -> "DescriptionResult":
        if cls is not DescriptionResult:
            raise TypeError("DescriptionResult factory requires exact class")
        if (
            type(request) is not DescriptionRequest
            or DescriptionRequest.from_dict(request.as_dict()) != request
        ):
            raise TypeError("request must be exact canonical DescriptionRequest")
        if type(completeness) is not DescriptionCompleteness:
            raise TypeError("completeness must be exact DescriptionCompleteness")
        pin = _pin(revision_pin)
        if request.revision_pin != pin:
            raise ValueError("request and result revision pins differ")
        refs = {
            "fact_refs": _fact_refs(fact_refs, maximum=request.max_facts),
            "definition_refs": _refs(definition_refs, "definition_refs"),
            "claim_refs": _refs(claim_refs, "claim_refs"),
            "source_refs": _refs(source_refs, "source_refs"),
            "proof_refs": _refs(proof_refs, "proof_refs"),
        }
        terminal_without_answer = completeness in {
            DescriptionCompleteness.MISSING,
            DescriptionCompleteness.BUDGET_EXHAUSTED,
        }
        if request.requested_content == "definition" and not terminal_without_answer:
            raise ValueError("definition requires reviewed definition policy, not neighborhood evidence")
        if terminal_without_answer and answer_expression is not None:
            raise ValueError(
                "missing or budget-exhausted description cannot carry an answer expression"
            )
        if not terminal_without_answer and answer_expression is None:
            raise ValueError("description completeness requires an answer expression")
        if answer_expression is not None:
            answer_expression = _canonical_answer(
                answer_expression, request.target_ref
            )
            if _answer_depth(answer_expression) > request.max_depth:
                raise ValueError("answer expression exceeds request max_depth")
            for name in ("fact_refs", "claim_refs", "source_refs", "proof_refs"):
                if not refs[name]:
                    raise ValueError(f"content-bearing description requires {name}")
        if completeness is DescriptionCompleteness.MISSING and any(refs.values()):
            raise ValueError("missing description cannot carry positive evidence refs")
        material = {
            "abi_version": DESCRIPTION_ABI_VERSION,
            "request": request.as_dict(),
            "answer_expression": (
                None if answer_expression is None else answer_expression.as_dict()
            ),
            "completeness": completeness.value,
            **{name: list(value) for name, value in refs.items()},
            "revision_pin": pin.as_dict(),
        }
        result = object.__new__(cls)
        object.__setattr__(result, "abi_version", DESCRIPTION_ABI_VERSION)
        object.__setattr__(
            result,
            "description_result_ref",
            stable_ref("description_result", material),
        )
        object.__setattr__(result, "request", request)
        object.__setattr__(result, "answer_expression", answer_expression)
        object.__setattr__(result, "completeness", completeness)
        for name, item in refs.items():
            object.__setattr__(result, name, item)
        object.__setattr__(result, "revision_pin", pin)
        return result

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "description_result_ref": self.description_result_ref,
            "request": self.request.as_dict(),
            "answer_expression": (
                None
                if self.answer_expression is None
                else self.answer_expression.as_dict()
            ),
            "completeness": self.completeness.value,
            "fact_refs": list(self.fact_refs),
            "definition_refs": list(self.definition_refs),
            "claim_refs": list(self.claim_refs),
            "source_refs": list(self.source_refs),
            "proof_refs": list(self.proof_refs),
            "revision_pin": self.revision_pin.as_dict(),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DescriptionResult":
        row = _exact_dict(value, cls._FIELDS, "DescriptionResult")
        if (
            type(row["abi_version"]) is not int
            or row["abi_version"] != DESCRIPTION_ABI_VERSION
        ):
            raise ValueError("unsupported Description ABI")
        if type(row["request"]) is not dict or type(row["revision_pin"]) is not dict:
            raise TypeError("DescriptionResult nested records must be exact dicts")
        expression_row = row["answer_expression"]
        if type(row["completeness"]) is not str:
            raise TypeError("completeness must be exact str")
        if expression_row is not None and type(expression_row) is not dict:
            raise TypeError("answer_expression must be an exact dict or None")
        rebuilt = cls.create(
            request=DescriptionRequest.from_dict(row["request"]),
            answer_expression=(
                None
                if expression_row is None
                else SemanticExpression.from_dict(expression_row)
            ),
            completeness=DescriptionCompleteness(row["completeness"]),
            fact_refs=_wire_refs(
                row["fact_refs"], "fact_refs", maximum=DESCRIPTION_MAX_FACTS
            ),
            definition_refs=_wire_refs(row["definition_refs"], "definition_refs"),
            claim_refs=_wire_refs(row["claim_refs"], "claim_refs"),
            source_refs=_wire_refs(row["source_refs"], "source_refs"),
            proof_refs=_wire_refs(row["proof_refs"], "proof_refs"),
            revision_pin=RevisionPin.from_dict(row["revision_pin"]),
        )
        _ref(row["description_result_ref"], "description_result_ref")
        if row["description_result_ref"] != rebuilt.description_result_ref:
            raise ValueError("description_result_ref mismatch")
        if rebuilt.as_dict() != row:
            raise ValueError("non-canonical DescriptionResult")
        return rebuilt
