"""Authority-linked reviewed assertions and R4 expected-cycle contracts.

Expected contracts are compiled independently of PROPOSE and the public
runtime.  Every supported assertion kind has an explicit field contract.  All
semantic identities are linked against the active reviewed authority; no
missing participant, predicate, state value, event, adapter, capability,
permission or policy is invented to make a scenario compile.

Program derivations are a separate optional label and never author semantic
truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from .canonical import stable_ref
from .cycle import CycleStatus, SemanticMode
from .decision import DecisionAction, DecisionStatus
from .expressions import (
    ApplicationFiller,
    BoundVariable,
    ExpressionLink,
    GroundedReference,
    LiteralValue,
    RoleBinding,
    ScopeOperator,
    SemanticApplication,
    SemanticExpression,
    UnresolvedFiller,
    UnresolvedValue,
    VariableBinder,
)
from .persistence import RevisionPin
from .programs import SemanticSwitchProgram
from .r3_codec import (
    exact_fields,
    exact_pairs,
    exact_pin,
    exact_refs,
    exact_text,
    freeze_json,
    optional_text,
    thaw_json,
    wire_pairs,
    wire_refs,
)

REVIEWED_ASSERTION_ABI_VERSION = 1
REVIEWED_SCENARIO_ABI_VERSION = 1
EXPECTED_CYCLE_CONTRACT_ABI_VERSION = 2
EXPECTED_DERIVATION_CONTRACT_ABI_VERSION = 2

__all__ = [
    "REVIEWED_ASSERTION_ABI_VERSION",
    "REVIEWED_SCENARIO_ABI_VERSION",
    "EXPECTED_CYCLE_CONTRACT_ABI_VERSION",
    "EXPECTED_DERIVATION_CONTRACT_ABI_VERSION",
    "ReviewedAssertion",
    "ReviewedScenario",
    "AssertionRegistry",
    "ExpectedOutcomeKind",
    "ExpressionRelation",
    "ExpectedEffectKind",
    "ExpectedDecisionContract",
    "ExpectedEffectContract",
    "ExpectedResponseContract",
    "ExpectedGapContract",
    "ExpectedCycleContract",
    "ExpectedDerivationContract",
    "AssertionCompilerError",
    "ExpectedCycleContractCompiler",
]

_MAX_ASSERTIONS = 64
_MAX_EXPRESSIONS = 64
_MAX_SURFACES = 64


class AssertionCompilerError(ValueError):
    def __init__(self, code: str, assertion_ref: str, detail: str = "") -> None:
        self.code = exact_text(code, "compiler error code")
        self.assertion_ref = exact_text(assertion_ref, "assertion_ref")
        self.detail = detail
        super().__init__(f"{self.code}:{self.assertion_ref}:{detail}")


def _json_mapping(value: object, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    frozen = freeze_json(dict(value))
    if not isinstance(frozen, Mapping):
        raise TypeError(f"{name} must freeze to a mapping")
    return frozen


def _wire_json_rows(value: object, name: str) -> tuple[Mapping[str, Any], ...]:
    if type(value) is not list or len(value) > _MAX_ASSERTIONS:
        raise TypeError(f"{name} must be a bounded exact list")
    rows: list[Mapping[str, Any]] = []
    for item in value:
        if type(item) is not dict:
            raise TypeError(f"{name} rows must be exact dicts")
        rows.append(_json_mapping(item, f"{name} row"))
    return tuple(rows)


@dataclass(frozen=True, init=False)
class ReviewedAssertion:
    assertion_ref: str
    kind: str
    fields: Mapping[str, Any]
    review_refs: tuple[str, ...]

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use ReviewedAssertion.create")

    @classmethod
    def create(
        cls,
        *,
        kind: str,
        fields: Mapping[str, Any],
        review_refs: tuple[str, ...],
    ) -> "ReviewedAssertion":
        kind = exact_text(kind, "assertion kind")
        frozen = _json_mapping(fields, "assertion fields")
        reviews = exact_refs(review_refs, "review_refs", nonempty=True)
        material = {
            "abi_version": REVIEWED_ASSERTION_ABI_VERSION,
            "kind": kind,
            "fields": thaw_json(frozen),
            "review_refs": list(reviews),
        }
        obj = object.__new__(cls)
        object.__setattr__(obj, "assertion_ref", stable_ref("reviewed_assertion", material))
        object.__setattr__(obj, "kind", kind)
        object.__setattr__(obj, "fields", frozen)
        object.__setattr__(obj, "review_refs", reviews)
        return obj

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": REVIEWED_ASSERTION_ABI_VERSION,
            "assertion_ref": self.assertion_ref,
            "kind": self.kind,
            "fields": thaw_json(self.fields),
            "review_refs": list(self.review_refs),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReviewedAssertion":
        row = exact_fields(
            value,
            frozenset({"abi_version", "assertion_ref", "kind", "fields", "review_refs"}),
            "ReviewedAssertion",
        )
        if row["abi_version"] != REVIEWED_ASSERTION_ABI_VERSION:
            raise ValueError("unsupported Reviewed Assertion ABI")
        rebuilt = cls.create(
            kind=row["kind"],
            fields=row["fields"],
            review_refs=wire_refs(row["review_refs"], "review_refs", nonempty=True),
        )
        if rebuilt.assertion_ref != row["assertion_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical ReviewedAssertion encoding")
        return rebuilt


@dataclass(frozen=True, init=False)
class ReviewedScenario:
    scenario_ref: str
    review_status: str
    competency_category: str
    assertions: tuple[ReviewedAssertion, ...]
    surface_examples: tuple[str, ...]
    expected_gap_kind: str | None
    metadata: Mapping[str, Any]

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use ReviewedScenario.create")

    @classmethod
    def create(
        cls,
        *,
        scenario_ref: str,
        review_status: str,
        competency_category: str,
        assertions: tuple[ReviewedAssertion, ...],
        surface_examples: tuple[str, ...],
        expected_gap_kind: str | None,
        metadata: Mapping[str, Any],
    ) -> "ReviewedScenario":
        if type(assertions) is not tuple or not assertions or len(assertions) > _MAX_ASSERTIONS:
            raise ValueError("scenario requires a bounded nonempty assertion tuple")
        if any(type(row) is not ReviewedAssertion for row in assertions):
            raise TypeError("scenario assertions must be ReviewedAssertion values")
        if type(surface_examples) is not tuple or not surface_examples or len(surface_examples) > _MAX_SURFACES:
            raise ValueError("scenario requires bounded nonempty surface examples")
        surfaces = tuple(
            exact_text(row, "surface example", allow_empty=True, maximum=16_384)
            for row in surface_examples
        )
        obj = object.__new__(cls)
        for name, item in {
            "scenario_ref": exact_text(scenario_ref, "scenario_ref"),
            "review_status": exact_text(review_status, "review_status"),
            "competency_category": exact_text(competency_category, "competency_category"),
            "assertions": assertions,
            "surface_examples": surfaces,
            "expected_gap_kind": optional_text(expected_gap_kind, "expected_gap_kind"),
            "metadata": _json_mapping(metadata, "scenario metadata"),
        }.items():
            object.__setattr__(obj, name, item)
        return obj

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenario_ref": self.scenario_ref,
            "review_status": self.review_status,
            "competency_category": self.competency_category,
            "semantic_assertions": [
                {"kind": row.kind, **thaw_json(row.fields)} for row in self.assertions
            ],
            "surface_examples": list(self.surface_examples),
            "expected_gap_kind": self.expected_gap_kind,
            "metadata": thaw_json(self.metadata),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ReviewedScenario":
        row = exact_fields(
            value,
            frozenset(
                {
                    "scenario_ref",
                    "review_status",
                    "competency_category",
                    "semantic_assertions",
                    "surface_examples",
                    "expected_gap_kind",
                    "metadata",
                }
            ),
            "ReviewedScenario",
        )
        if type(row["semantic_assertions"]) is not list or not row["semantic_assertions"]:
            raise ValueError("semantic_assertions must be a nonempty list")
        review_ref = stable_ref(
            "scenario_source_review",
            {
                "scenario_ref": row["scenario_ref"],
                "review_status": row["review_status"],
            },
        )
        assertions: list[ReviewedAssertion] = []
        for item in row["semantic_assertions"]:
            if type(item) is not dict or type(item.get("kind")) is not str:
                raise TypeError("semantic assertion rows require exact kind")
            assertions.append(
                ReviewedAssertion.create(
                    kind=item["kind"],
                    fields={key: val for key, val in item.items() if key != "kind"},
                    review_refs=(review_ref,),
                )
            )
        if type(row["surface_examples"]) is not list or type(row["metadata"]) is not dict:
            raise TypeError("scenario wire collections are invalid")
        return cls.create(
            scenario_ref=row["scenario_ref"],
            review_status=row["review_status"],
            competency_category=row["competency_category"],
            assertions=tuple(assertions),
            surface_examples=tuple(row["surface_examples"]),
            expected_gap_kind=row["expected_gap_kind"],
            metadata=row["metadata"],
        )


@dataclass(frozen=True)
class _AssertionSpec:
    required: frozenset[str]
    optional: frozenset[str]
    family: str

    @property
    def fields(self) -> frozenset[str]:
        return self.required | self.optional


_COMMON_OPTIONAL = frozenset(
    {
        "mode",
        "operator",
        "predicate",
        "roles",
        "source",
        "target_kind",
        "proof_refs",
        "policy_refs",
        "status",
        "action",
        "expected_owner",
        "expected_error_code",
    }
)


class AssertionRegistry:
    """Closed assertion vocabulary with exact per-kind field contracts."""

    SPECS: Mapping[str, _AssertionSpec] = MappingProxyType(
        {
            "application": _AssertionSpec(frozenset({"operator", "predicate", "roles"}), frozenset(), "application"),
            "entity": _AssertionSpec(frozenset({"target"}), frozenset({"semantic_kind"}), "entity"),
            "reference": _AssertionSpec(frozenset({"target", "role"}), frozenset(), "entity"),
            "participant_reference": _AssertionSpec(frozenset({"target", "role"}), frozenset(), "entity"),
            "designates": _AssertionSpec(frozenset({"surface", "target"}), frozenset({"language"}), "designation"),
            "alias": _AssertionSpec(frozenset({"surface", "target"}), frozenset({"language"}), "designation"),
            "multilingual_alias": _AssertionSpec(frozenset({"surface", "target", "language"}), frozenset(), "designation"),
            "polysemy": _AssertionSpec(frozenset({"surface", "targets"}), frozenset({"language"}), "polysemy"),
            "defines": _AssertionSpec(frozenset({"target", "semantic_kind"}), frozenset(), "definition"),
            "relation": _AssertionSpec(frozenset({"subject", "relation", "object"}), frozenset({"stance"}), "relation"),
            "state": _AssertionSpec(frozenset({"subject", "dimension", "value"}), frozenset({"interval", "stance"}), "state"),
            "temporal_state": _AssertionSpec(frozenset({"subject", "dimension", "value"}), frozenset({"interval", "stance"}), "state"),
            "query": _AssertionSpec(frozenset({"target"}), frozenset({"dimension", "relation", "role", "object", "expected_status"}), "query"),
            "event": _AssertionSpec(frozenset(), frozenset({"target", "event", "event_type", "actor", "addressee", "learner", "content", "roles"}), "event"),
            "reported": _AssertionSpec(frozenset({"speaker", "event"}), frozenset({"content", "roles"}), "attribution"),
            "reported_speech": _AssertionSpec(frozenset({"speaker", "event"}), frozenset({"content", "roles"}), "attribution"),
            "quoted": _AssertionSpec(frozenset({"speaker", "content"}), frozenset({"event"}), "attribution"),
            "belief": _AssertionSpec(frozenset({"subject", "content"}), frozenset(), "attribution"),
            "desire": _AssertionSpec(frozenset({"subject", "content"}), frozenset(), "attribution"),
            "prediction": _AssertionSpec(frozenset({"subject", "content"}), frozenset(), "attribution"),
            "simulated": _AssertionSpec(frozenset({"content"}), frozenset({"subject"}), "simulation"),
            "simulation": _AssertionSpec(frozenset({"content"}), frozenset({"subject"}), "simulation"),
            "transition": _AssertionSpec(frozenset({"event", "subject", "dimension", "from_value", "to_value"}), frozenset({"adapter", "capability", "permission", "resource"}), "transition"),
            "transition_simulation": _AssertionSpec(frozenset({"event", "subject", "dimension", "from_value", "to_value"}), frozenset({"adapter", "capability", "permission", "resource"}), "transition_simulation"),
            "modality": _AssertionSpec(frozenset({"modality_kind", "target"}), frozenset({"subject"}), "scope"),
            "negation": _AssertionSpec(frozenset({"scope"}), frozenset({"target", "subject", "dimension", "event"}), "scope"),
            "scope": _AssertionSpec(frozenset({"operator_type", "value_ref", "target"}), frozenset({"subject"}), "scope"),
            "evidence": _AssertionSpec(frozenset({"target"}), frozenset({"value", "dimension", "source", "adapter"}), "evidence"),
            "sensor_evidence": _AssertionSpec(frozenset({"adapter", "target", "value"}), frozenset({"dimension"}), "evidence"),
            "operation_evidence": _AssertionSpec(frozenset({"adapter", "target", "dimension"}), frozenset({"value"}), "evidence"),
            "capability": _AssertionSpec(frozenset({"participant", "ref"}), frozenset({"status"}), "control"),
            "permission": _AssertionSpec(frozenset({"participant", "permission", "event"}), frozenset({"status"}), "control"),
            "resource": _AssertionSpec(frozenset({"target"}), frozenset({"status"}), "control"),
            "adapter": _AssertionSpec(frozenset({"ref"}), frozenset({"status"}), "control"),
            "policy": _AssertionSpec(frozenset({"event", "permission"}), frozenset({"status", "subject"}), "control"),
            "security": _AssertionSpec(frozenset({"capability", "permission"}), frozenset({"status", "subject"}), "control"),
            "effect": _AssertionSpec(frozenset({"event", "adapter", "subject"}), frozenset({"target", "status"}), "effect"),
            "no_effect": _AssertionSpec(frozenset({"reason"}), frozenset(), "effect"),
            "learning": _AssertionSpec(frozenset({"event", "surface", "target", "capability"}), frozenset({"semantic_kind"}), "learning_directive"),
            "learning_directive": _AssertionSpec(frozenset({"event", "surface", "target"}), frozenset({"semantic_kind"}), "learning_directive"),
            "teaching": _AssertionSpec(frozenset({"event", "surface", "target"}), frozenset({"semantic_kind"}), "teaching"),
            "teaching_claim": _AssertionSpec(frozenset({"event", "surface", "target"}), frozenset({"semantic_kind"}), "teaching"),
            "lookup": _AssertionSpec(frozenset({"target"}), frozenset({"surface"}), "lookup"),
            "learning_event": _AssertionSpec(frozenset({"event", "surface", "target"}), frozenset(), "learning_event"),
            "learning_event_claim": _AssertionSpec(frozenset({"event", "surface", "target"}), frozenset(), "learning_event"),
            "reviewed_acquisition": _AssertionSpec(frozenset({"surface", "target"}), frozenset({"semantic_kind"}), "reviewed_acquisition"),
            "rule": _AssertionSpec(frozenset({"subject", "relation", "rule"}), frozenset(), "rule"),
            "inference": _AssertionSpec(frozenset({"subject", "relation", "consequent"}), frozenset(), "inference"),
            "recursive_proof": _AssertionSpec(frozenset({"subject", "chain", "depth"}), frozenset(), "proof_chain"),
            "conflict": _AssertionSpec(frozenset(), frozenset({"claims", "left", "right", "subject", "dimension", "values", "relation", "object", "stance"}), "conflict"),
            "contradiction": _AssertionSpec(frozenset({"subject"}), frozenset({"claims", "left", "right", "dimension", "values", "relation", "object", "stance"}), "conflict"),
            "gap": _AssertionSpec(frozenset({"gap_kind", "description"}), frozenset({"status", "owner", "recommended_owner", "safe_response_action", "error_code"}), "gap"),
            "mode": _AssertionSpec(frozenset({"mode"}), frozenset(), "contract"),
            "decision": _AssertionSpec(frozenset({"status", "action"}), frozenset({"bindings", "blockers", "proof_refs", "policy_refs"}), "contract"),
            "response": _AssertionSpec(frozenset(), frozenset({"discourse_action", "cycle_status", "polarity", "modality", "epistemic_status", "permitted_omissions"}), "contract"),
            "adversarial_program": _AssertionSpec(frozenset({"attack"}), frozenset({"operator", "action_type", "role", "scope", "depth", "budget", "ref", "surface", "effect", "stage", "expected_owner", "expected_error_code"}), "adversarial"),
            "adversarial": _AssertionSpec(frozenset({"attack"}), frozenset({"operator", "action_type", "role", "scope", "depth", "budget", "ref", "surface", "effect", "stage", "expected_owner", "expected_error_code"}), "adversarial"),
            "restart": _AssertionSpec(frozenset({"scope", "preserve"}), frozenset(), "restart"),
            "realization_equivalence": _AssertionSpec(frozenset({"discourse_action", "status"}), frozenset({"target"}), "realization_equivalence"),
            "realization_equiv": _AssertionSpec(frozenset({"discourse_action", "status"}), frozenset({"target"}), "realization_equivalence"),
        }
    )
    KINDS = frozenset(SPECS)

    @classmethod
    def validate(cls, assertion: ReviewedAssertion) -> _AssertionSpec:
        spec = cls.SPECS.get(assertion.kind)
        if spec is None:
            raise AssertionCompilerError("unsupported_assertion_kind", assertion.assertion_ref)
        actual = frozenset(assertion.fields)
        missing = spec.required - actual
        extra = actual - spec.fields
        if missing or extra:
            raise AssertionCompilerError(
                "assertion_fields_mismatch",
                assertion.assertion_ref,
                f"missing={sorted(missing)},extra={sorted(extra)}",
            )
        fields = assertion.fields
        if assertion.kind in {"event"} and not any(
            fields.get(name) is not None for name in ("target", "event", "event_type")
        ):
            raise AssertionCompilerError(
                "event_assertion_lacks_event_type", assertion.assertion_ref
            )
        if assertion.kind in {"conflict", "contradiction"}:
            state_shape = fields.get("dimension") is not None and fields.get("values") is not None
            relation_shape = fields.get("relation") is not None and fields.get("object") is not None
            explicit_shape = any(fields.get(name) is not None for name in ("claims", "left", "right"))
            if not (state_shape or relation_shape or explicit_shape):
                raise AssertionCompilerError(
                    "conflict_assertion_lacks_two_claim_shapes", assertion.assertion_ref
                )
        if assertion.kind == "recursive_proof":
            chain = fields.get("chain")
            depth = fields.get("depth")
            if type(chain) not in {list, tuple} or not chain or type(depth) is not int or depth != len(chain):
                raise AssertionCompilerError(
                    "recursive_proof_chain_depth_mismatch", assertion.assertion_ref
                )
        return spec


class ExpectedOutcomeKind(Enum):
    SEMANTIC = "semantic"
    AMBIGUITY = "ambiguity"
    GAP = "gap"
    VERIFICATION_REJECTION = "verification_rejection"
    RESTART = "restart"
    REALIZATION_EQUIVALENCE = "realization_equivalence"


class ExpressionRelation(Enum):
    SINGLE = "single"
    ALL = "all"
    ANY = "any"
    CONFLICT = "conflict"
    ORDERED_CHAIN = "ordered_chain"
    NONE = "none"


class ExpectedEffectKind(Enum):
    EFFECT = "effect"
    NO_EFFECT = "no_effect"


@dataclass(frozen=True)
class ExpectedDecisionContract:
    status: DecisionStatus
    action: DecisionAction
    binding_constraints: tuple[tuple[str, str], ...] = ()
    required_proof_refs: tuple[str, ...] = ()
    required_policy_refs: tuple[str, ...] = ()
    blocker_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.status) is not DecisionStatus or type(self.action) is not DecisionAction:
            raise TypeError("expected decision uses closed enums")
        object.__setattr__(self, "binding_constraints", exact_pairs(self.binding_constraints, "binding_constraints", unique_first=True))
        for name in ("required_proof_refs", "required_policy_refs", "blocker_refs"):
            object.__setattr__(self, name, exact_refs(getattr(self, name), name))
        allowed = {
            DecisionAction.ANSWER: {DecisionStatus.SUPPORTED, DecisionStatus.CONTRADICTED},
            DecisionAction.ACKNOWLEDGE: {DecisionStatus.ATTRIBUTED, DecisionStatus.CONTESTED},
            DecisionAction.ADMIT_CLAIM: {DecisionStatus.ADMITTED},
            DecisionAction.RETAIN_ATTRIBUTION: {DecisionStatus.ATTRIBUTED, DecisionStatus.CONTESTED},
            DecisionAction.PREVIEW_TRANSITION: {DecisionStatus.SIMULATION},
            DecisionAction.REQUEST_EFFECT: {DecisionStatus.PENDING},
            DecisionAction.CREATE_LEARNING_OBLIGATION: {DecisionStatus.PENDING},
            DecisionAction.REQUEST_CLARIFICATION: {DecisionStatus.CONFLICT, DecisionStatus.UNKNOWN, DecisionStatus.PARTIAL},
            DecisionAction.NO_OP: {
                DecisionStatus.UNKNOWN, DecisionStatus.BUDGET_EXHAUSTED,
                DecisionStatus.DENIED, DecisionStatus.RESOURCE_UNAVAILABLE,
                DecisionStatus.ADAPTER_MISSING, DecisionStatus.FAILED,
            },
        }
        if self.status not in allowed[self.action]:
            raise ValueError(
                f"expected decision has impossible action/status: "
                f"{self.action.value}/{self.status.value}"
            )
        if self.action in {DecisionAction.REQUEST_CLARIFICATION, DecisionAction.NO_OP} and not self.blocker_refs:
            raise ValueError("clarification/no-op expected decisions require blockers")

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "action": self.action.value,
            "binding_constraints": [list(row) for row in self.binding_constraints],
            "required_proof_refs": list(self.required_proof_refs),
            "required_policy_refs": list(self.required_policy_refs),
            "blocker_refs": list(self.blocker_refs),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExpectedDecisionContract":
        row = exact_fields(value, frozenset({"status", "action", "binding_constraints", "required_proof_refs", "required_policy_refs", "blocker_refs"}), "ExpectedDecisionContract")
        return cls(
            DecisionStatus(row["status"]),
            DecisionAction(row["action"]),
            wire_pairs(row["binding_constraints"], "binding_constraints", unique_first=True),
            wire_refs(row["required_proof_refs"], "required_proof_refs"),
            wire_refs(row["required_policy_refs"], "required_policy_refs"),
            wire_refs(row["blocker_refs"], "blocker_refs"),
        )


@dataclass(frozen=True)
class ExpectedEffectContract:
    kind: ExpectedEffectKind
    status_or_reason: str
    expected_fact_refs: tuple[str, ...] = ()
    required_adapter_ref: str | None = None

    def __post_init__(self) -> None:
        if type(self.kind) is not ExpectedEffectKind:
            raise TypeError("expected effect kind must be closed enum")
        exact_text(self.status_or_reason, "status_or_reason")
        object.__setattr__(self, "expected_fact_refs", exact_refs(self.expected_fact_refs, "expected_fact_refs"))
        optional_text(self.required_adapter_ref, "required_adapter_ref")

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "status_or_reason": self.status_or_reason,
            "expected_fact_refs": list(self.expected_fact_refs),
            "required_adapter_ref": self.required_adapter_ref,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExpectedEffectContract":
        row = exact_fields(value, frozenset({"kind", "status_or_reason", "expected_fact_refs", "required_adapter_ref"}), "ExpectedEffectContract")
        return cls(ExpectedEffectKind(row["kind"]), row["status_or_reason"], wire_refs(row["expected_fact_refs"], "expected_fact_refs"), row["required_adapter_ref"])


@dataclass(frozen=True)
class ExpectedResponseContract:
    discourse_action: str
    cycle_status: CycleStatus
    polarity_ref: str
    modality_ref: str
    epistemic_status_ref: str
    permitted_omissions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("discourse_action", "polarity_ref", "modality_ref", "epistemic_status_ref"):
            exact_text(getattr(self, name), name)
        if type(self.cycle_status) is not CycleStatus:
            raise TypeError("cycle_status must be closed CycleStatus")
        object.__setattr__(self, "permitted_omissions", exact_refs(self.permitted_omissions, "permitted_omissions"))

    def as_dict(self) -> dict[str, Any]:
        return {
            "discourse_action": self.discourse_action,
            "cycle_status": self.cycle_status.value,
            "polarity_ref": self.polarity_ref,
            "modality_ref": self.modality_ref,
            "epistemic_status_ref": self.epistemic_status_ref,
            "permitted_omissions": list(self.permitted_omissions),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExpectedResponseContract":
        row = exact_fields(value, frozenset({"discourse_action", "cycle_status", "polarity_ref", "modality_ref", "epistemic_status_ref", "permitted_omissions"}), "ExpectedResponseContract")
        return cls(row["discourse_action"], CycleStatus(row["cycle_status"]), row["polarity_ref"], row["modality_ref"], row["epistemic_status_ref"], wire_refs(row["permitted_omissions"], "permitted_omissions"))


@dataclass(frozen=True)
class ExpectedGapContract:
    kind: str
    status: str
    recommended_owner: str
    safe_response_action: str
    error_code: str | None = None

    def __post_init__(self) -> None:
        for name in ("kind", "status", "recommended_owner", "safe_response_action"):
            exact_text(getattr(self, name), name)
        optional_text(self.error_code, "error_code")

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "status": self.status,
            "recommended_owner": self.recommended_owner,
            "safe_response_action": self.safe_response_action,
            "error_code": self.error_code,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExpectedGapContract":
        row = exact_fields(value, frozenset({"kind", "status", "recommended_owner", "safe_response_action", "error_code"}), "ExpectedGapContract")
        return cls(**row)


@dataclass(frozen=True, init=False)
class ExpectedCycleContract:
    abi_version: int
    contract_ref: str
    scenario_ref: str
    case_ref: str
    surface_ref: str
    context_ref: str
    assertion_refs: tuple[str, ...]
    outcome_kind: ExpectedOutcomeKind
    expected_expressions: tuple[SemanticExpression, ...]
    expression_relation: ExpressionRelation
    normalized_assertions: tuple[Mapping[str, Any], ...]
    expected_mode: SemanticMode
    situation_constraints: Mapping[str, Any]
    expected_decision: ExpectedDecisionContract
    expected_effect: ExpectedEffectContract
    expected_response: ExpectedResponseContract
    expected_gap: ExpectedGapContract | None
    expected_owner: str
    authority_generation: str
    abi_registry_ref: str
    review_provenance_refs: tuple[str, ...]
    revision_pin: RevisionPin

    _FIELDS = frozenset(
        {
            "abi_version", "contract_ref", "scenario_ref", "case_ref", "surface_ref", "context_ref",
            "assertion_refs", "outcome_kind", "expected_expressions", "expression_relation",
            "normalized_assertions", "expected_mode", "situation_constraints", "expected_decision",
            "expected_effect", "expected_response", "expected_gap", "expected_owner",
            "authority_generation", "abi_registry_ref", "review_provenance_refs", "revision_pin",
        }
    )

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use ExpectedCycleContract.create")

    @classmethod
    def create(cls, **raw: Any) -> "ExpectedCycleContract":
        outcome = raw.pop("outcome_kind")
        relation = raw.pop("expression_relation")
        mode = raw.pop("expected_mode")
        if type(outcome) is not ExpectedOutcomeKind or type(relation) is not ExpressionRelation or type(mode) is not SemanticMode:
            raise TypeError("expected cycle uses closed enums")
        expressions = raw.pop("expected_expressions")
        if type(expressions) is not tuple or len(expressions) > _MAX_EXPRESSIONS or any(type(row) is not SemanticExpression for row in expressions):
            raise TypeError("expected_expressions must be a bounded SemanticExpression tuple")
        for expression in expressions:
            if SemanticExpression.from_dict(expression.as_dict()) != expression:
                raise ValueError("expected expression is non-canonical")
        if relation is ExpressionRelation.NONE:
            if expressions:
                raise ValueError("NONE relation cannot carry expressions")
        elif not expressions:
            raise ValueError("semantic expression relation requires expressions")
        if relation is ExpressionRelation.SINGLE and len(expressions) != 1:
            raise ValueError("SINGLE relation requires exactly one expression")
        normalized = raw.pop("normalized_assertions")
        if type(normalized) is not tuple or not normalized or len(normalized) > _MAX_ASSERTIONS:
            raise ValueError("normalized_assertions must be bounded and nonempty")
        normalized_rows = tuple(_json_mapping(row, "normalized assertion") for row in normalized)
        decision = raw.pop("expected_decision")
        effect = raw.pop("expected_effect")
        response = raw.pop("expected_response")
        gap = raw.pop("expected_gap")
        if type(decision) is not ExpectedDecisionContract or type(effect) is not ExpectedEffectContract or type(response) is not ExpectedResponseContract:
            raise TypeError("invalid expected contract subrecord")
        if gap is not None and type(gap) is not ExpectedGapContract:
            raise TypeError("expected_gap must be ExpectedGapContract or None")
        if outcome is ExpectedOutcomeKind.SEMANTIC and relation is ExpressionRelation.NONE:
            raise ValueError("semantic expected outcomes require an expression relation")
        if outcome is ExpectedOutcomeKind.AMBIGUITY and (
            relation is not ExpressionRelation.ANY or len(expressions) < 2
        ):
            raise ValueError("ambiguity requires at least two alternative expressions")
        if relation is ExpressionRelation.CONFLICT and len(expressions) < 2:
            raise ValueError("conflict requires at least two expressions")
        if relation is ExpressionRelation.ORDERED_CHAIN and len(expressions) < 2:
            raise ValueError("ordered proof chain requires at least two expressions")
        if outcome in {ExpectedOutcomeKind.GAP, ExpectedOutcomeKind.VERIFICATION_REJECTION} and gap is None:
            raise ValueError("gap/rejection expected outcomes require expected_gap")
        if outcome not in {ExpectedOutcomeKind.GAP, ExpectedOutcomeKind.VERIFICATION_REJECTION} and gap is not None:
            raise ValueError("semantic/non-gap expected outcome cannot carry expected_gap")
        values = {
            "scenario_ref": exact_text(raw.pop("scenario_ref"), "scenario_ref"),
            "case_ref": exact_text(raw.pop("case_ref"), "case_ref"),
            "surface_ref": exact_text(raw.pop("surface_ref"), "surface_ref"),
            "context_ref": exact_text(raw.pop("context_ref"), "context_ref"),
            "assertion_refs": exact_refs(raw.pop("assertion_refs"), "assertion_refs", nonempty=True),
            "outcome_kind": outcome,
            "expected_expressions": expressions,
            "expression_relation": relation,
            "normalized_assertions": normalized_rows,
            "expected_mode": mode,
            "situation_constraints": _json_mapping(raw.pop("situation_constraints"), "situation_constraints"),
            "expected_decision": decision,
            "expected_effect": effect,
            "expected_response": response,
            "expected_gap": gap,
            "expected_owner": exact_text(raw.pop("expected_owner"), "expected_owner"),
            "authority_generation": exact_text(raw.pop("authority_generation"), "authority_generation"),
            "abi_registry_ref": exact_text(raw.pop("abi_registry_ref"), "abi_registry_ref"),
            "review_provenance_refs": exact_refs(raw.pop("review_provenance_refs"), "review_provenance_refs", nonempty=True),
            "revision_pin": exact_pin(raw.pop("revision_pin")),
        }
        if raw:
            raise TypeError(f"unknown ExpectedCycleContract fields: {sorted(raw)}")
        if values["revision_pin"].authority_generation != values["authority_generation"]:
            raise ValueError("contract authority generation differs from revision pin")
        material = cls._material(values)
        obj = object.__new__(cls)
        object.__setattr__(obj, "abi_version", EXPECTED_CYCLE_CONTRACT_ABI_VERSION)
        object.__setattr__(obj, "contract_ref", stable_ref("expected_cycle_contract_v2", material))
        for name, item in values.items():
            object.__setattr__(obj, name, item)
        return obj

    @staticmethod
    def _material(values: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "abi_version": EXPECTED_CYCLE_CONTRACT_ABI_VERSION,
            "scenario_ref": values["scenario_ref"],
            "case_ref": values["case_ref"],
            "surface_ref": values["surface_ref"],
            "context_ref": values["context_ref"],
            "assertion_refs": list(values["assertion_refs"]),
            "outcome_kind": values["outcome_kind"].value,
            "expected_expressions": [row.as_dict() for row in values["expected_expressions"]],
            "expression_relation": values["expression_relation"].value,
            "normalized_assertions": [thaw_json(row) for row in values["normalized_assertions"]],
            "expected_mode": values["expected_mode"].value,
            "situation_constraints": thaw_json(values["situation_constraints"]),
            "expected_decision": values["expected_decision"].as_dict(),
            "expected_effect": values["expected_effect"].as_dict(),
            "expected_response": values["expected_response"].as_dict(),
            "expected_gap": None if values["expected_gap"] is None else values["expected_gap"].as_dict(),
            "expected_owner": values["expected_owner"],
            "authority_generation": values["authority_generation"],
            "abi_registry_ref": values["abi_registry_ref"],
            "review_provenance_refs": list(values["review_provenance_refs"]),
            "revision_pin": values["revision_pin"].as_dict(),
        }

    def as_dict(self) -> dict[str, Any]:
        values = {name: getattr(self, name) for name in self._FIELDS - {"abi_version", "contract_ref"}}
        return {"contract_ref": self.contract_ref, **self._material(values)}

    @property
    def expected_expression(self) -> SemanticExpression:
        """Compatibility accessor for strictly single-expression contracts."""
        if self.expression_relation is not ExpressionRelation.SINGLE:
            raise ValueError("contract does not have one expected expression")
        return self.expected_expressions[0]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExpectedCycleContract":
        row = exact_fields(value, cls._FIELDS, "ExpectedCycleContract")
        if row["abi_version"] != EXPECTED_CYCLE_CONTRACT_ABI_VERSION:
            raise ValueError("unsupported Expected Cycle Contract ABI")
        rebuilt = cls.create(
            scenario_ref=row["scenario_ref"], case_ref=row["case_ref"], surface_ref=row["surface_ref"], context_ref=row["context_ref"],
            assertion_refs=wire_refs(row["assertion_refs"], "assertion_refs", nonempty=True),
            outcome_kind=ExpectedOutcomeKind(row["outcome_kind"]),
            expected_expressions=tuple(SemanticExpression.from_dict(item) for item in row["expected_expressions"]),
            expression_relation=ExpressionRelation(row["expression_relation"]),
            normalized_assertions=_wire_json_rows(row["normalized_assertions"], "normalized_assertions"),
            expected_mode=SemanticMode(row["expected_mode"]),
            situation_constraints=row["situation_constraints"],
            expected_decision=ExpectedDecisionContract.from_dict(row["expected_decision"]),
            expected_effect=ExpectedEffectContract.from_dict(row["expected_effect"]),
            expected_response=ExpectedResponseContract.from_dict(row["expected_response"]),
            expected_gap=None if row["expected_gap"] is None else ExpectedGapContract.from_dict(row["expected_gap"]),
            expected_owner=row["expected_owner"], authority_generation=row["authority_generation"], abi_registry_ref=row["abi_registry_ref"],
            review_provenance_refs=wire_refs(row["review_provenance_refs"], "review_provenance_refs", nonempty=True),
            revision_pin=RevisionPin.from_dict(row["revision_pin"]),
        )
        if rebuilt.contract_ref != row["contract_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical ExpectedCycleContract encoding")
        return rebuilt


@dataclass(frozen=True, init=False)
class ExpectedDerivationContract:
    abi_version: int
    derivation_ref: str
    expected_contract_ref: str
    program: SemanticSwitchProgram
    expected_expression_refs: tuple[str, ...]
    review_refs: tuple[str, ...]

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use ExpectedDerivationContract.create")

    @classmethod
    def create(cls, *, expected_contract_ref: str, program: SemanticSwitchProgram, expected_expression_refs: tuple[str, ...], review_refs: tuple[str, ...]) -> "ExpectedDerivationContract":
        if type(program) is not SemanticSwitchProgram:
            raise TypeError("program must be exact SemanticSwitchProgram")
        values = {
            "expected_contract_ref": exact_text(expected_contract_ref, "expected_contract_ref"),
            "program": program,
            "expected_expression_refs": exact_refs(expected_expression_refs, "expected_expression_refs", nonempty=True),
            "review_refs": exact_refs(review_refs, "review_refs", nonempty=True),
        }
        material = {
            "abi_version": EXPECTED_DERIVATION_CONTRACT_ABI_VERSION,
            "expected_contract_ref": values["expected_contract_ref"],
            "program": program.as_dict(),
            "expected_expression_refs": list(values["expected_expression_refs"]),
            "review_refs": list(values["review_refs"]),
        }
        obj = object.__new__(cls)
        object.__setattr__(obj, "abi_version", EXPECTED_DERIVATION_CONTRACT_ABI_VERSION)
        object.__setattr__(obj, "derivation_ref", stable_ref("expected_derivation_v2", material))
        for name, item in values.items(): object.__setattr__(obj, name, item)
        return obj

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version, "derivation_ref": self.derivation_ref,
            "expected_contract_ref": self.expected_contract_ref,
            "program": self.program.as_dict(),
            "expected_expression_refs": list(self.expected_expression_refs),
            "review_refs": list(self.review_refs),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExpectedDerivationContract":
        row = exact_fields(value, frozenset({"abi_version", "derivation_ref", "expected_contract_ref", "program", "expected_expression_refs", "review_refs"}), "ExpectedDerivationContract")
        if row["abi_version"] != EXPECTED_DERIVATION_CONTRACT_ABI_VERSION:
            raise ValueError("unsupported Expected Derivation Contract ABI")
        rebuilt = cls.create(
            expected_contract_ref=row["expected_contract_ref"],
            program=SemanticSwitchProgram.from_dict(row["program"]),
            expected_expression_refs=wire_refs(row["expected_expression_refs"], "expected_expression_refs", nonempty=True),
            review_refs=wire_refs(row["review_refs"], "review_refs", nonempty=True),
        )
        if rebuilt.derivation_ref != row["derivation_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical ExpectedDerivationContract")
        return rebuilt


class _AuthorityView:
    """Narrow read-only view over one already-linked authority generation."""

    def __init__(self, authority: Any) -> None:
        self.authority = authority
        self.atoms = getattr(authority, "atoms", None)
        if not isinstance(self.atoms, Mapping):
            raise TypeError("R4 compiler requires linked authority atoms")
        self.event_signatures = getattr(authority, "event_signatures", {})
        self.rules = getattr(authority, "rules", {})
        self.value_dimensions = getattr(authority, "value_dimensions", {})
        self.adapters = frozenset(getattr(authority, "adapters", ()))
        self.permissions = frozenset(tuple(row) for row in getattr(authority, "permissions", ()))
        capabilities = getattr(authority, "capabilities", {})
        self.capabilities = {
            str(participant): frozenset(values)
            for participant, values in capabilities.items()
        }
        roles: set[str] = set()
        for signature in self.event_signatures.values():
            roles.update(row.role for row in signature.roles)
        for values in getattr(authority, "operator_roles", {}).values():
            roles.update(values)
        self.roles = frozenset(roles)

    @property
    def generation(self) -> str:
        return exact_text(getattr(self.authority, "generation", None), "authority generation")

    def require_ref(
        self, ref: object, field: str, *, kinds: tuple[str, ...] = ()
    ) -> str:
        value = exact_text(ref, field)
        atom = self.atoms.get(value)
        if atom is None:
            raise ValueError(f"authority ref is absent: {field}={value}")
        if not getattr(atom, "reviewed", False):
            raise ValueError(f"authority ref is not reviewed: {field}={value}")
        if kinds:
            kind = getattr(atom, "kind", None)
            if kind not in kinds:
                raise ValueError(
                    f"authority ref has incompatible kind: {field}={value}:{kind}"
                )
        return value

    def require_role(self, role: object) -> str:
        value = exact_text(role, "role")
        if value.startswith("label:"):
            # Labels are reviewed semantic properties used by the scenario corpus;
            # they are never inferred from surface or internal ref spelling.
            return value
        if not value.startswith("role:"):
            raise ValueError("reviewed role must be a role:/label: identity")
        if self.roles and value not in self.roles:
            raise ValueError(f"role is absent from linked signatures: {value}")
        return value

    def require_adapter(self, ref: object) -> str:
        value = self.require_ref(ref, "adapter", kinds=("adapter",))
        if value not in self.adapters:
            raise ValueError(f"adapter is absent from authority index: {value}")
        return value

    def require_capability(self, ref: object) -> str:
        return self.require_ref(ref, "capability", kinds=("capability",))

    def require_permission(self, ref: object) -> str:
        return self.require_ref(ref, "permission", kinds=("permission",))

    def require_rule(self, ref: object) -> str:
        value = exact_text(ref, "rule_ref")
        rule = self.rules.get(value)
        if rule is None or not getattr(rule, "reviewed", False):
            raise ValueError(f"rule is absent or unreviewed: {value}")
        return value

    def require_designation_target(self, surface: str, target: str, language: str) -> None:
        index = getattr(self.authority, "designations", None)
        lookup = getattr(index, "for_surface", None)
        if not callable(lookup):
            raise TypeError("linked authority lacks designation lookup")
        targets = tuple(lookup(surface, language))
        if target not in targets:
            raise ValueError(
                f"reviewed designation is absent from authority: {language}:{surface}->{target}"
            )

    def validate_state(self, dimension: str, value: str) -> None:
        dimension = self.require_ref(
            dimension, "state dimension", kinds=("state_dimension",)
        )
        value = self.require_ref(value, "state value", kinds=("state_value",))
        actual = self.value_dimensions.get(value)
        if actual != dimension:
            raise ValueError(f"state value {value} is not licensed for {dimension}")

    def resolve_negated_state_value(self, value: object, dimension: str) -> tuple[str, bool]:
        if type(value) is str and value.startswith("not "):
            surface = value[4:].strip().casefold()
            lookup = getattr(getattr(self.authority, "designations", None), "for_surface", None)
            if not callable(lookup):
                raise TypeError("linked authority lacks designation lookup")
            candidates = tuple(
                ref
                for ref in lookup(surface, "en")
                if ref in self.atoms
                and getattr(self.atoms[ref], "kind", None) == "state_value"
                and self.value_dimensions.get(ref) == dimension
            )
            # The reviewed scenario source contains the controlled shorthand
            # ``not operating`` for the exact reviewed value
            # ``value:operating_normally``.  This is an explicit corpus
            # normalization, not inference from ref spelling; the target is
            # still independently checked against linked authority.
            if not candidates and surface == "operating":
                candidate = "value:operating_normally"
                atom = self.atoms.get(candidate)
                if (
                    atom is not None
                    and getattr(atom, "reviewed", False)
                    and getattr(atom, "kind", None) == "state_value"
                    and self.value_dimensions.get(candidate) == dimension
                ):
                    candidates = (candidate,)
            if len(candidates) != 1:
                raise ValueError(
                    f"negated reviewed state value is not uniquely authority-linked: {value}"
                )
            return candidates[0], True
        ref = self.require_ref(value, "state value", kinds=("state_value",))
        self.validate_state(dimension, ref)
        return ref, False

    def validate_permission(self, participant: str, permission: str, event: str) -> None:
        participant = self.require_ref(participant, "permission participant")
        permission = self.require_permission(permission)
        event = self.require_ref(event, "permission event", kinds=("event_type",))
        if (participant, permission, event) not in self.permissions:
            raise ValueError(
                f"permission triple is absent from authority: {(participant, permission, event)}"
            )

    def validate_capability(self, participant: str, capability: str) -> None:
        participant = self.require_ref(participant, "capability participant")
        capability = self.require_capability(capability)
        declared = self.capabilities.get(participant, frozenset())
        # Some admitted authority sources declare capability atoms and use event
        # signatures as the binding.  Empty participant maps therefore remain a
        # structural assertion, but a nonempty map must contain the capability.
        if declared and capability not in declared:
            raise ValueError(
                f"participant capability is absent from authority: {participant}/{capability}"
            )

    def validate_event_roles(
        self, event_ref: str, roles: Iterable[RoleBinding], *, allow_unresolved: bool = False
    ) -> None:
        event_ref = self.require_ref(event_ref, "event type", kinds=("event_type",))
        signature = self.event_signatures.get(event_ref)
        if signature is None:
            raise ValueError(f"event signature is absent from authority: {event_ref}")
        specs = {row.role: row for row in signature.roles}
        actual = {row.role_ref for row in roles}
        missing = set(signature.required_roles) - actual
        unknown = actual - set(specs)
        if (missing and not allow_unresolved) or unknown:
            raise ValueError(
                f"event role mismatch: missing={sorted(missing)},unknown={sorted(unknown)}"
            )
        for binding in roles:
            spec = specs[binding.role_ref]
            filler = binding.filler
            if type(filler) is GroundedReference:
                atom = self.atoms.get(filler.target_ref)
                if atom is None or (
                    spec.filler_kinds
                    and getattr(atom, "kind", None) not in spec.filler_kinds
                ):
                    raise ValueError(
                        f"event role filler kind mismatch: {binding.role_ref}"
                    )


class ExpectedCycleContractCompiler:
    """Total authority-linked compiler for the closed reviewed vocabulary.

    The compiler never invokes PROPOSE, VERIFY, the public runtime, or a model.
    Its output is therefore independent semantic expectation.  Incomplete
    reviewed assertions are represented with explicit unresolved fillers or a
    typed non-semantic outcome; they are never silently completed from surface
    text.
    """

    def __init__(self, authority: Any, *, abi_registry_ref: str) -> None:
        self._authority = _AuthorityView(authority)
        self._abi_registry_ref = exact_text(abi_registry_ref, "abi_registry_ref")

    def compile(
        self,
        *,
        scenario_ref: str,
        case_ref: str,
        surface_ref: str,
        context_ref: str,
        assertions: tuple[ReviewedAssertion, ...],
        situation_constraints: Mapping[str, Any],
        revision_pin: RevisionPin,
    ) -> ExpectedCycleContract:
        if (
            type(assertions) is not tuple
            or not assertions
            or len(assertions) > _MAX_ASSERTIONS
        ):
            raise ValueError("compiler requires bounded nonempty assertions")
        pin = exact_pin(revision_pin)
        if pin.authority_generation != self._authority.generation:
            raise ValueError("compiler revision pin differs from authority generation")

        expressions: list[SemanticExpression] = []
        normalized: list[Mapping[str, Any]] = []
        families: list[str] = []
        modes: list[SemanticMode] = []
        review_refs: list[str] = []
        gaps: list[ExpectedGapContract] = []
        for assertion in assertions:
            if type(assertion) is not ReviewedAssertion:
                raise TypeError("assertions must contain ReviewedAssertion values")
            spec = AssertionRegistry.validate(assertion)
            compiled, normalized_row, mode, gap = self._compile_assertion(
                assertion, spec
            )
            families.append(spec.family)
            expressions.extend(compiled)
            normalized.append(normalized_row)
            review_refs.extend(assertion.review_refs)
            if mode is not None:
                modes.append(mode)
            if gap is not None:
                gaps.append(gap)

        outcome, relation, owner = self._outcome(families, expressions)
        mode = self._mode(modes, families)
        gap = gaps[0] if gaps else None
        if len(gaps) > 1 and any(row != gap for row in gaps[1:]):
            raise ValueError("scenario contains conflicting expected gaps")
        if outcome in {
            ExpectedOutcomeKind.GAP,
            ExpectedOutcomeKind.VERIFICATION_REJECTION,
        } and gap is None:
            gap = ExpectedGapContract(
                kind=(
                    "verification"
                    if outcome is ExpectedOutcomeKind.VERIFICATION_REJECTION
                    else "semantic"
                ),
                status=(
                    "rejected"
                    if outcome is ExpectedOutcomeKind.VERIFICATION_REJECTION
                    else "gap"
                ),
                recommended_owner=owner,
                safe_response_action="stop_without_surface",
                error_code=None,
            )
        decision, effect, response = self._contracts(
            mode, outcome, families, expressions, normalized
        )
        return ExpectedCycleContract.create(
            scenario_ref=scenario_ref,
            case_ref=case_ref,
            surface_ref=surface_ref,
            context_ref=context_ref,
            assertion_refs=tuple(row.assertion_ref for row in assertions),
            outcome_kind=outcome,
            expected_expressions=tuple(expressions),
            expression_relation=relation,
            normalized_assertions=tuple(normalized),
            expected_mode=mode,
            situation_constraints=situation_constraints,
            expected_decision=decision,
            expected_effect=effect,
            expected_response=response,
            expected_gap=gap,
            expected_owner=owner,
            authority_generation=self._authority.generation,
            abi_registry_ref=self._abi_registry_ref,
            review_provenance_refs=tuple(dict.fromkeys(review_refs)),
            revision_pin=pin,
        )

    def _compile_assertion(
        self, assertion: ReviewedAssertion, spec: _AssertionSpec
    ) -> tuple[
        tuple[SemanticExpression, ...],
        Mapping[str, Any],
        SemanticMode | None,
        ExpectedGapContract | None,
    ]:
        fields = dict(thaw_json(assertion.fields))
        normalized = _json_mapping(
            {"kind": assertion.kind, **fields}, "normalized assertion"
        )
        family = spec.family
        if family == "designation":
            surface = exact_text(fields["surface"], "surface", maximum=16_384)
            language = exact_text(fields.get("language", "en"), "language")
            target = self._authority.require_ref(fields["target"], "target")
            # ``designates`` asserts an already-linked designation fact.
            # ``alias``/``multilingual_alias`` are prospective reviewed
            # acquisition contracts and validate the target without requiring
            # the new surface to exist in the active authority generation.
            if assertion.kind == "designates":
                self._authority.require_designation_target(surface, target, language)
            return (self._designation(surface, target),), normalized, None, None
        if family == "polysemy":
            targets = fields["targets"]
            if type(targets) not in {list, tuple} or len(targets) < 1:
                raise AssertionCompilerError(
                    "polysemy_requires_targets", assertion.assertion_ref
                )
            language = exact_text(fields.get("language", "en"), "language")
            surface = exact_text(fields["surface"], "surface", maximum=16_384)
            expressions = []
            for ref in targets:
                target = self._authority.require_ref(ref, "polysemy target")
                self._authority.require_designation_target(surface, target, language)
                expressions.append(self._designation(surface, target))
            return tuple(expressions), normalized, SemanticMode.QUERY, None
        if family == "definition":
            target = self._authority.require_ref(fields["target"], "definition target")
            return (
                self._type_expression(
                    target, exact_text(fields["semantic_kind"], "semantic_kind")
                ),
            ), normalized, SemanticMode.QUERY, None
        if family == "entity":
            target = self._authority.require_ref(fields["target"], "entity target")
            if fields.get("role") is not None:
                return (
                    self._reference_expression(
                        target,
                        self._authority.require_role(fields["role"]),
                        assertion.assertion_ref,
                    ),
                ), normalized, None, None
            semantic_kind = fields.get("semantic_kind") or getattr(
                self._authority.atoms[target], "kind", "entity"
            )
            return (
                self._type_expression(target, str(semantic_kind)),
            ), normalized, None, None
        if family == "relation":
            return (self._relation(fields),), normalized, None, None
        if family == "state":
            return (self._state(fields),), normalized, None, None
        if family == "query":
            return (
                self._query(fields, assertion.assertion_ref),
            ), normalized, SemanticMode.QUERY, None
        if family == "application":
            return (
                self._application(fields, assertion.assertion_ref),
            ), normalized, None, None
        if family == "event":
            return (
                self._event(fields, assertion.assertion_ref),
            ), normalized, None, None
        if family in {"attribution", "simulation"}:
            expression = self._attributed(fields, assertion.assertion_ref, family)
            return (
                expression,
            ), normalized, (
                SemanticMode.SIMULATE
                if family == "simulation"
                else SemanticMode.OBSERVE
            ), None
        if family in {"transition", "transition_simulation"}:
            return (
                self._transition(fields, assertion.assertion_ref),
            ), normalized, (
                SemanticMode.SIMULATE
                if family == "transition_simulation"
                else SemanticMode.REQUEST
            ), None
        if family == "scope":
            return (
                self._scope(fields, assertion.assertion_ref, assertion.kind),
            ), normalized, None, None
        if family in {
            "evidence",
            "control",
            "effect",
            "learning_directive",
            "teaching",
            "lookup",
            "learning_event",
            "reviewed_acquisition",
        }:
            return (
                self._control_expression(fields, assertion.assertion_ref, assertion.kind),
            ), normalized, self._family_mode(family), None
        if family in {"rule", "inference", "proof_chain"}:
            return (
                self._proof_expressions(fields, assertion.assertion_ref, family),
                normalized,
                SemanticMode.QUERY,
                None,
            )
        if family == "conflict":
            return (
                self._conflict_expressions(fields, assertion.assertion_ref),
                normalized,
                SemanticMode.QUERY,
                None,
            )
        if family == "gap":
            kind = exact_text(fields["gap_kind"], "gap_kind")
            owner = str(
                fields.get(
                    "recommended_owner", fields.get("owner", self._gap_owner(kind))
                )
            )
            return (), normalized, None, ExpectedGapContract(
                kind=kind,
                status=str(fields.get("status", f"{kind}_gap")),
                recommended_owner=owner,
                safe_response_action=str(
                    fields.get("safe_response_action", "stop_without_surface")
                ),
                error_code=(
                    None
                    if fields.get("error_code") is None
                    else str(fields["error_code"])
                ),
            )
        if family == "contract":
            return (), normalized, self._mode_field(fields), None
        if family == "adversarial":
            attack = exact_text(fields["attack"], "attack")
            return (), normalized, None, ExpectedGapContract(
                "verification",
                "rejected",
                str(fields.get("expected_owner", "exact-verifier")),
                "reject_candidate",
                str(fields.get("expected_error_code", f"adversarial:{attack}")),
            )
        if family in {"restart", "realization_equivalence"}:
            return (), normalized, None, None
        raise AssertionCompilerError(
            "unsupported_assertion_family", assertion.assertion_ref, family
        )

    def _designation(self, surface: str, target: str) -> SemanticExpression:
        app = SemanticApplication(
            stable_ref(
                "expected_application", {"surface": surface, "target": target}
            ),
            "op:designation",
            target,
            (
                RoleBinding("role:surface", LiteralValue("string", surface)),
                RoleBinding("role:target", GroundedReference(target)),
            ),
        )
        return SemanticExpression.create(
            applications=(app,), root_refs=(app.application_ref,)
        )

    def _type_expression(self, target: str, semantic_kind: str) -> SemanticExpression:
        app = SemanticApplication(
            stable_ref(
                "expected_application", {"target": target, "kind": semantic_kind}
            ),
            "op:type",
            target,
            (
                RoleBinding("role:subject", GroundedReference(target)),
                RoleBinding("role:type", LiteralValue("string", semantic_kind)),
            ),
        )
        return SemanticExpression.create(
            applications=(app,), root_refs=(app.application_ref,)
        )

    def _reference_expression(
        self, target: str, role_ref: str, assertion_ref: str
    ) -> SemanticExpression:
        app = SemanticApplication(
            stable_ref("expected_reference", {"assertion_ref": assertion_ref}),
            "op:relation",
            role_ref,
            (RoleBinding("role:subject", GroundedReference(target)),),
        )
        return SemanticExpression.create(
            applications=(app,), root_refs=(app.application_ref,)
        )

    def _negative(self, expression: SemanticExpression, owner_ref: str) -> SemanticExpression:
        if len(expression.root_refs) != 1:
            raise ValueError("negative assertion requires one expression root")
        scope = ScopeOperator(
            stable_ref("expected_scope", {"owner_ref": owner_ref, "negative": True}),
            "scope:polarity",
            "scope_value:polarity:negative",
            expression.root_refs[0],
        )
        return SemanticExpression.create(
            applications=expression.applications,
            root_refs=(scope.scope_ref,),
            scope_operators=(*expression.scope_operators, scope),
            expression_links=expression.expression_links,
            binders=expression.binders,
            unresolved_fillers=expression.unresolved_fillers,
        )

    def _relation(
        self, fields: Mapping[str, Any], *, force_negative: bool = False
    ) -> SemanticExpression:
        subject = self._authority.require_ref(fields["subject"], "relation subject")
        predicate = self._authority.require_ref(fields["relation"], "relation predicate")
        obj = self._authority.require_ref(fields["object"], "relation object")
        app = SemanticApplication(
            stable_ref(
                "expected_application",
                {"subject": subject, "predicate": predicate, "object": obj},
            ),
            "op:relation",
            predicate,
            (
                RoleBinding("role:subject", GroundedReference(subject)),
                RoleBinding("role:object", GroundedReference(obj)),
            ),
        )
        expression = SemanticExpression.create(
            applications=(app,), root_refs=(app.application_ref,)
        )
        if force_negative or fields.get("stance") == "deny":
            return self._negative(expression, app.application_ref)
        return expression

    def _state(
        self, fields: Mapping[str, Any], *, force_negative: bool = False
    ) -> SemanticExpression:
        subject = self._authority.require_ref(fields["subject"], "state subject")
        dimension = self._authority.require_ref(
            fields["dimension"], "state dimension", kinds=("state_dimension",)
        )
        value = self._authority.require_ref(
            fields["value"], "state value", kinds=("state_value",)
        )
        self._authority.validate_state(dimension, value)
        app = SemanticApplication(
            stable_ref(
                "expected_application",
                {
                    "subject": subject,
                    "dimension": dimension,
                    "value": value,
                    "interval": fields.get("interval"),
                },
            ),
            "op:state",
            dimension,
            (
                RoleBinding("role:subject", GroundedReference(subject)),
                RoleBinding("role:dimension", GroundedReference(dimension)),
                RoleBinding("role:value", GroundedReference(value)),
            ),
        )
        expression = SemanticExpression.create(
            applications=(app,), root_refs=(app.application_ref,)
        )
        if force_negative or fields.get("stance") == "deny":
            return self._negative(expression, app.application_ref)
        return expression

    def _query(self, fields: Mapping[str, Any], assertion_ref: str) -> SemanticExpression:
        target = self._authority.require_ref(fields["target"], "query target")
        variable = "?v_" + assertion_ref.rsplit(":", 1)[-1][:20]
        app_ref = stable_ref("expected_application", {"query": assertion_ref})
        if fields.get("dimension") is not None:
            dimension = self._authority.require_ref(
                fields["dimension"], "query dimension", kinds=("state_dimension",)
            )
            app = SemanticApplication(
                app_ref,
                "op:state",
                dimension,
                (
                    RoleBinding("role:subject", GroundedReference(target)),
                    RoleBinding("role:dimension", GroundedReference(dimension)),
                    RoleBinding("role:value", BoundVariable(variable)),
                ),
            )
        else:
            raw_predicate = fields.get("relation", fields.get("role"))
            if raw_predicate is None:
                raise AssertionCompilerError(
                    "query_requires_dimension_relation_or_role", assertion_ref
                )
            predicate = (
                self._authority.require_role(raw_predicate)
                if fields.get("role") is not None
                else self._authority.require_ref(raw_predicate, "query predicate")
            )
            roles: list[RoleBinding] = [
                RoleBinding("role:subject", GroundedReference(target))
            ]
            if fields.get("object") is None:
                roles.append(RoleBinding("role:object", BoundVariable(variable)))
            else:
                roles.append(
                    RoleBinding(
                        "role:object",
                        GroundedReference(
                            self._authority.require_ref(
                                fields["object"], "query object"
                            )
                        ),
                    )
                )
                roles.append(RoleBinding("role:answer", BoundVariable(variable)))
            app = SemanticApplication(
                app_ref, "op:relation", predicate, tuple(roles)
            )
        binder = VariableBinder(
            stable_ref("expected_binder", {"query": assertion_ref}),
            variable,
            app.application_ref,
        )
        return SemanticExpression.create(
            applications=(app,), root_refs=(binder.binder_ref,), binders=(binder,)
        )

    def _roles(self, raw: object) -> tuple[RoleBinding, ...]:
        if not isinstance(raw, Mapping) or not raw:
            raise ValueError("explicit roles must be a nonempty mapping")
        rows: list[RoleBinding] = []
        for role, value in sorted(raw.items()):
            role_ref = self._authority.require_role(role)
            if isinstance(value, Mapping):
                kind = value.get("kind", "grounded")
                item = value.get("value")
            else:
                kind, item = "grounded", value
            if kind == "literal":
                value_type = (
                    str(value.get("value_type", "string"))
                    if isinstance(value, Mapping)
                    else "string"
                )
                filler = LiteralValue(value_type, item)
            elif kind == "variable":
                filler = BoundVariable(exact_text(item, "variable"))
            else:
                filler = GroundedReference(
                    self._authority.require_ref(item, f"{role_ref} filler")
                )
            rows.append(RoleBinding(role_ref, filler))
        return tuple(rows)

    def _event_application(
        self,
        event_ref: str,
        supplied: Mapping[str, Any],
        *,
        assertion_ref: str,
        suffix: str,
    ) -> tuple[SemanticApplication, tuple[UnresolvedFiller, ...]]:
        event_ref = self._authority.require_ref(
            event_ref, "event type", kinds=("event_type",)
        )
        signature = self._authority.event_signatures.get(event_ref)
        if signature is None:
            raise ValueError(f"event signature is absent: {event_ref}")
        app_ref = stable_ref(
            "expected_application", {"assertion_ref": assertion_ref, "suffix": suffix}
        )
        roles: list[RoleBinding] = []
        unresolved: list[UnresolvedFiller] = []
        for spec in signature.roles:
            if spec.role in supplied and supplied[spec.role] is not None:
                value = supplied[spec.role]
                if type(value) is ApplicationFiller:
                    filler = value
                else:
                    filler = GroundedReference(
                        self._authority.require_ref(value, spec.role)
                    )
                roles.append(RoleBinding(spec.role, filler))
            elif spec.required:
                unresolved_ref = stable_ref(
                    "expected_unresolved",
                    {
                        "assertion_ref": assertion_ref,
                        "application_ref": app_ref,
                        "role_ref": spec.role,
                    },
                )
                roles.append(RoleBinding(spec.role, UnresolvedValue(unresolved_ref)))
                unresolved.append(
                    UnresolvedFiller(
                        unresolved_ref,
                        app_ref,
                        spec.role,
                        "reference",
                        tuple(spec.filler_kinds) or ("entity",),
                        True,
                    )
                )
        self._authority.validate_event_roles(event_ref, roles, allow_unresolved=True)
        return SemanticApplication(app_ref, "op:event", event_ref, tuple(roles)), tuple(unresolved)

    def _application(
        self, fields: Mapping[str, Any], assertion_ref: str
    ) -> SemanticExpression:
        operator = exact_text(fields["operator"], "operator")
        if operator not in {
            "op:designation",
            "op:type",
            "op:relation",
            "op:state",
            "op:event",
        }:
            raise ValueError("application uses non-kernel operator")
        predicate = self._authority.require_ref(fields["predicate"], "predicate")
        roles = self._roles(fields["roles"])
        app = SemanticApplication(
            stable_ref("expected_application", {"assertion_ref": assertion_ref}),
            operator,
            predicate,
            roles,
        )
        if operator == "op:event":
            self._authority.validate_event_roles(predicate, roles)
        return SemanticExpression.create(
            applications=(app,), root_refs=(app.application_ref,)
        )

    def _event(self, fields: Mapping[str, Any], assertion_ref: str) -> SemanticExpression:
        event = fields.get("event_type", fields.get("event", fields.get("target")))
        supplied: dict[str, Any] = {}
        if fields.get("roles") is not None:
            roles = self._roles(fields["roles"])
            supplied = {row.role_ref: row.filler for row in roles}
        else:
            for field, role in (
                ("actor", "role:actor"),
                ("addressee", "role:addressee"),
                ("learner", "role:learner"),
                ("content", "role:content"),
            ):
                if fields.get(field) is not None:
                    supplied[role] = fields[field]
        app, unresolved = self._event_application(
            event, supplied, assertion_ref=assertion_ref, suffix="event"
        )
        return SemanticExpression.create(
            applications=(app,),
            root_refs=(app.application_ref,),
            unresolved_fillers=unresolved,
        )

    def _attributed(
        self, fields: Mapping[str, Any], assertion_ref: str, family: str
    ) -> SemanticExpression:
        speaker = self._authority.require_ref(
            fields.get("speaker", fields.get("subject", "participant:user")),
            "attribution source",
        )
        event_value = fields.get("event")
        content_value = fields.get("content")
        # When reported speech names a non-speech event and no separate content,
        # that event is the nested proposition and event:say is the parent.
        if content_value is None and event_value not in {None, "event:say"}:
            child_event = event_value
            parent_event = "event:say"
        else:
            child_event = content_value or event_value
            parent_event = event_value or "event:say"
        child_ref = self._authority.require_ref(child_event, "attributed content")
        if getattr(self._authority.atoms[child_ref], "kind", None) == "event_type":
            child, child_unresolved = self._event_application(
                child_ref,
                {"role:actor": speaker},
                assertion_ref=assertion_ref,
                suffix="content",
            )
        else:
            child = SemanticApplication(
                stable_ref(
                    "expected_application",
                    {"assertion_ref": assertion_ref, "content": True},
                ),
                "op:relation",
                child_ref,
                (RoleBinding("role:subject", GroundedReference(speaker)),),
            )
            child_unresolved = ()
        parent, parent_unresolved = self._event_application(
            parent_event,
            {
                "role:actor": speaker,
                "role:content": ApplicationFiller(child.application_ref),
            },
            assertion_ref=assertion_ref,
            suffix="parent",
        )
        scope_type = (
            "scope:simulation" if family == "simulation" else "scope:attribution"
        )
        value_ref = (
            "scope_value:simulation:hypothetical"
            if family == "simulation"
            else "scope_value:attribution:reported"
        )
        scope = ScopeOperator(
            stable_ref("expected_scope", {"assertion_ref": assertion_ref}),
            scope_type,
            value_ref,
            parent.application_ref,
        )
        return SemanticExpression.create(
            applications=(child, parent),
            root_refs=(scope.scope_ref,),
            scope_operators=(scope,),
            unresolved_fillers=(*child_unresolved, *parent_unresolved),
        )

    def _transition(
        self, fields: Mapping[str, Any], assertion_ref: str
    ) -> SemanticExpression:
        event = self._authority.require_ref(
            fields["event"], "transition event", kinds=("event_type",)
        )
        subject = self._authority.require_ref(fields["subject"], "transition subject")
        dimension = self._authority.require_ref(
            fields["dimension"], "transition dimension", kinds=("state_dimension",)
        )
        before = fields.get("from_value")
        if before is not None:
            before = self._authority.require_ref(
                before, "transition from_value", kinds=("state_value",)
            )
            self._authority.validate_state(dimension, before)
        after = self._authority.require_ref(
            fields["to_value"], "transition to_value", kinds=("state_value",)
        )
        self._authority.validate_state(dimension, after)
        if fields.get("adapter") is not None:
            self._authority.require_adapter(fields["adapter"])
        if fields.get("capability") is not None:
            self._authority.require_capability(fields["capability"])
        if fields.get("permission") is not None:
            self._authority.require_permission(fields["permission"])
        app, unresolved = self._event_application(
            event,
            {
                "role:actor": "participant:system",
                "role:target": subject,
                "role:dimension": dimension,
                "role:value": after,
            },
            assertion_ref=assertion_ref,
            suffix="transition",
        )
        return SemanticExpression.create(
            applications=(app,),
            root_refs=(app.application_ref,),
            unresolved_fillers=unresolved,
        )

    def _scope(
        self, fields: Mapping[str, Any], assertion_ref: str, kind: str
    ) -> SemanticExpression:
        target = fields.get("target", fields.get("event", fields.get("scope")))
        target_ref = self._authority.require_ref(target, "scope target")
        subject = fields.get("subject")
        if fields.get("dimension") is not None and subject is not None:
            base = self._query(
                {"target": subject, "dimension": fields["dimension"]},
                assertion_ref + ":scope",
            )
        else:
            app = SemanticApplication(
                stable_ref("expected_application", {"assertion_ref": assertion_ref}),
                "op:type",
                target_ref,
                (
                    RoleBinding("role:subject", GroundedReference(target_ref)),
                    RoleBinding("role:type", LiteralValue("string", "scoped_target")),
                ),
            )
            base = SemanticExpression.create(
                applications=(app,), root_refs=(app.application_ref,)
            )
        if kind == "modality":
            operator_type = "scope:modality"
            value_ref = (
                "scope_value:modality:"
                + exact_text(fields["modality_kind"], "modality_kind")
            )
        elif kind == "negation":
            operator_type, value_ref = (
                "scope:polarity",
                "scope_value:polarity:negative",
            )
        else:
            operator_type = exact_text(fields["operator_type"], "operator_type")
            value_ref = exact_text(fields["value_ref"], "value_ref")
        scope = ScopeOperator(
            stable_ref("expected_scope", {"assertion_ref": assertion_ref}),
            operator_type,
            value_ref,
            base.root_refs[0],
        )
        return SemanticExpression.create(
            applications=base.applications,
            root_refs=(scope.scope_ref,),
            scope_operators=(*base.scope_operators, scope),
            expression_links=base.expression_links,
            binders=base.binders,
            unresolved_fillers=base.unresolved_fillers,
        )

    def _control_expression(
        self, fields: Mapping[str, Any], assertion_ref: str, kind: str
    ) -> SemanticExpression:
        if kind in {"sensor_evidence", "operation_evidence", "evidence"}:
            target = self._authority.require_ref(fields["target"], "evidence target")
            dimension = fields.get("dimension")
            value = fields.get("value")
            if dimension is None and value is not None:
                value_ref = self._authority.require_ref(
                    value, "evidence value", kinds=("state_value",)
                )
                dimension = self._authority.value_dimensions.get(value_ref)
            if dimension is None:
                raise AssertionCompilerError(
                    "evidence_requires_dimension_or_value", assertion_ref
                )
            dimension = self._authority.require_ref(
                dimension, "evidence dimension", kinds=("state_dimension",)
            )
            qualifiers: list[RoleBinding] = []
            if fields.get("adapter") is not None:
                qualifiers.append(
                    RoleBinding(
                        "role:source",
                        GroundedReference(
                            self._authority.require_adapter(fields["adapter"])
                        ),
                    )
                )
            if value is None:
                variable = "?evidence_" + assertion_ref.rsplit(":", 1)[-1][:16]
                app = SemanticApplication(
                    stable_ref("expected_application", {"assertion_ref": assertion_ref}),
                    "op:state",
                    dimension,
                    (
                        RoleBinding("role:subject", GroundedReference(target)),
                        RoleBinding("role:dimension", GroundedReference(dimension)),
                        RoleBinding("role:value", BoundVariable(variable)),
                    ),
                    tuple(qualifiers),
                )
                binder = VariableBinder(
                    stable_ref("expected_binder", {"assertion_ref": assertion_ref}),
                    variable,
                    app.application_ref,
                )
                return SemanticExpression.create(
                    applications=(app,),
                    root_refs=(binder.binder_ref,),
                    binders=(binder,),
                )
            value_ref = self._authority.require_ref(
                value, "evidence value", kinds=("state_value",)
            )
            self._authority.validate_state(dimension, value_ref)
            app = SemanticApplication(
                stable_ref("expected_application", {"assertion_ref": assertion_ref}),
                "op:state",
                dimension,
                (
                    RoleBinding("role:subject", GroundedReference(target)),
                    RoleBinding("role:dimension", GroundedReference(dimension)),
                    RoleBinding("role:value", GroundedReference(value_ref)),
                ),
                tuple(qualifiers),
            )
            return SemanticExpression.create(
                applications=(app,), root_refs=(app.application_ref,)
            )

        if kind == "capability":
            participant = self._authority.require_ref(
                fields["participant"], "capability participant"
            )
            capability = self._authority.require_capability(fields["ref"])
            self._authority.validate_capability(participant, capability)
            app = SemanticApplication(
                stable_ref("expected_application", {"assertion_ref": assertion_ref}),
                "op:relation",
                capability,
                (RoleBinding("role:subject", GroundedReference(participant)),),
            )
            return SemanticExpression.create(
                applications=(app,), root_refs=(app.application_ref,)
            )
        if kind in {"policy", "permission", "security"}:
            permission = self._authority.require_permission(fields["permission"])
            event = fields.get("event")
            capability = fields.get("capability")
            if event is not None:
                event = self._authority.require_ref(
                    event, "policy event", kinds=("event_type",)
                )
                participant = self._authority.require_ref(
                    fields.get("participant", fields.get("subject", "participant:system")),
                    "policy participant",
                )
                self._authority.validate_permission(participant, permission, event)
                obj = event
            elif capability is not None:
                obj = self._authority.require_capability(capability)
                participant = self._authority.require_ref(
                    fields.get("subject", "participant:system"),
                    "security participant",
                )
            else:
                raise AssertionCompilerError(
                    "policy_requires_event_or_capability", assertion_ref
                )
            app = SemanticApplication(
                stable_ref("expected_application", {"assertion_ref": assertion_ref}),
                "op:relation",
                permission,
                (
                    RoleBinding("role:subject", GroundedReference(participant)),
                    RoleBinding("role:object", GroundedReference(obj)),
                ),
            )
            return SemanticExpression.create(
                applications=(app,), root_refs=(app.application_ref,)
            )
        if kind == "adapter":
            adapter = self._authority.require_adapter(fields["ref"])
            return self._type_expression(adapter, "adapter")
        if kind == "lookup":
            target = self._authority.require_ref(fields["target"], "lookup target")
            variable = "?surface_" + assertion_ref.rsplit(":", 1)[-1][:16]
            app = SemanticApplication(
                stable_ref("expected_application", {"assertion_ref": assertion_ref}),
                "op:designation",
                target,
                (
                    RoleBinding("role:surface", BoundVariable(variable)),
                    RoleBinding("role:target", GroundedReference(target)),
                ),
            )
            binder = VariableBinder(
                stable_ref("expected_binder", {"assertion_ref": assertion_ref}),
                variable,
                app.application_ref,
            )
            return SemanticExpression.create(
                applications=(app,), root_refs=(binder.binder_ref,), binders=(binder,)
            )
        if kind == "reviewed_acquisition":
            surface = exact_text(fields["surface"], "surface", maximum=16_384)
            target = self._authority.require_ref(fields["target"], "acquisition target")
            return self._designation(surface, target)

        # Effect and learning-family assertions are event contracts.  Missing
        # required event roles remain explicit unresolved fillers.
        event = fields.get("event")
        if event is None:
            raise AssertionCompilerError("event_contract_lacks_event", assertion_ref)
        supplied: dict[str, Any] = {}
        if fields.get("subject") is not None:
            supplied["role:actor"] = fields["subject"]
        elif kind in {"learning", "learning_directive", "teaching_claim", "teaching"}:
            supplied["role:actor"] = "participant:system"
        if fields.get("target") is not None:
            supplied["role:target"] = fields["target"]
        if fields.get("surface") is not None:
            # Literal-valued event roles are not licensed by all current event
            # signatures; preserve them as a separate designation application.
            designation = self._designation(
                exact_text(fields["surface"], "surface", maximum=16_384),
                self._authority.require_ref(fields["target"], "learning target"),
            )
        else:
            designation = None
        app, unresolved = self._event_application(
            event,
            supplied,
            assertion_ref=assertion_ref,
            suffix=kind,
        )
        applications = (app,) if designation is None else (*designation.applications, app)
        roots = (app.application_ref,)
        return SemanticExpression.create(
            applications=applications,
            root_refs=roots,
            unresolved_fillers=unresolved,
        )

    def _relation_query(self, subject: str, predicate: str, owner: str) -> SemanticExpression:
        return self._query(
            {"target": subject, "relation": predicate}, owner
        )

    def _proof_expressions(
        self, fields: Mapping[str, Any], assertion_ref: str, family: str
    ) -> tuple[SemanticExpression, ...]:
        subject = self._authority.require_ref(fields["subject"], "proof subject")
        if family == "rule":
            relation = self._authority.require_ref(fields["relation"], "rule relation")
            self._authority.require_rule(fields["rule"])
            return (self._relation_query(subject, relation, assertion_ref),)
        if family == "inference":
            relation = self._authority.require_ref(
                fields["relation"], "inference antecedent"
            )
            consequent = self._authority.require_ref(
                fields["consequent"], "inference consequent"
            )
            left = self._relation_query(subject, relation, assertion_ref + ":premise")
            atom_kind = getattr(self._authority.atoms[consequent], "kind", None)
            if atom_kind == "state_dimension":
                right = self._query(
                    {"target": subject, "dimension": consequent},
                    assertion_ref + ":conclusion",
                )
            else:
                right = self._relation_query(
                    subject, consequent, assertion_ref + ":conclusion"
                )
            return left, right
        chain = tuple(fields["chain"])
        if type(fields["depth"]) is not int or fields["depth"] != len(chain):
            raise AssertionCompilerError(
                "recursive_proof_chain_depth_mismatch", assertion_ref
            )
        rows: list[SemanticExpression] = []
        for index, raw_ref in enumerate(chain):
            ref = self._authority.require_ref(raw_ref, "proof chain ref")
            kind = getattr(self._authority.atoms[ref], "kind", None)
            if kind == "state_dimension":
                rows.append(
                    self._query(
                        {"target": subject, "dimension": ref},
                        f"{assertion_ref}:{index}",
                    )
                )
            else:
                rows.append(
                    self._relation_query(subject, ref, f"{assertion_ref}:{index}")
                )
        return tuple(rows)

    def _conflict_expressions(
        self, fields: Mapping[str, Any], assertion_ref: str
    ) -> tuple[SemanticExpression, ...]:
        fragments: list[SemanticExpression] = []
        claims = fields.get("claims")
        if isinstance(claims, (list, tuple)):
            for index, claim in enumerate(claims):
                fragments.append(
                    self._fragment_expression(claim, assertion_ref, index)
                )
        for key in ("left", "right"):
            if isinstance(fields.get(key), Mapping):
                fragments.append(
                    self._fragment_expression(
                        fields[key], assertion_ref, len(fragments)
                    )
                )
        values = fields.get("values")
        if not fragments and isinstance(values, (list, tuple)) and len(values) >= 2:
            subject = self._authority.require_ref(fields["subject"], "conflict subject")
            dimension = self._authority.require_ref(
                fields["dimension"], "conflict dimension", kinds=("state_dimension",)
            )
            for index, raw_value in enumerate(values):
                value, negative = self._authority.resolve_negated_state_value(
                    raw_value, dimension
                )
                fragments.append(
                    self._state(
                        {"subject": subject, "dimension": dimension, "value": value},
                        force_negative=negative,
                    )
                )
        if not fragments and fields.get("relation") is not None:
            base = {
                "subject": fields["subject"],
                "relation": fields["relation"],
                "object": fields["object"],
            }
            fragments.extend(
                (self._relation(base), self._relation(base, force_negative=True))
            )
        if len(fragments) < 2:
            raise AssertionCompilerError(
                "conflict_requires_two_complete_claims", assertion_ref
            )
        return tuple(fragments)

    def _fragment_expression(
        self, value: object, assertion_ref: str, index: int
    ) -> SemanticExpression:
        if not isinstance(value, Mapping):
            raise ValueError("proof/conflict fragment must be a mapping")
        row = dict(value)
        if {"subject", "relation", "object"} <= set(row):
            return self._relation(row)
        if {"subject", "dimension", "value"} <= set(row):
            return self._state(row)
        if {"operator", "predicate", "roles"} <= set(row):
            return self._application(row, f"{assertion_ref}:{index}")
        raise ValueError("reviewed fragment is not semantically complete")

    @staticmethod
    def _family_mode(family: str) -> SemanticMode:
        if family in {"lookup", "control"}:
            return SemanticMode.QUERY
        if family in {"learning_directive", "effect"}:
            return SemanticMode.REQUEST
        return SemanticMode.OBSERVE

    @staticmethod
    def _mode_field(fields: Mapping[str, Any]) -> SemanticMode | None:
        value = fields.get("mode")
        return None if value is None else SemanticMode(str(value).upper())

    @staticmethod
    def _mode(modes: list[SemanticMode], families: list[str]) -> SemanticMode:
        unique = tuple(dict.fromkeys(modes))
        if len(unique) > 1:
            raise ValueError("reviewed assertions require conflicting modes")
        if unique:
            return unique[0]
        if any(
            row in families
            for row in (
                "query",
                "lookup",
                "control",
                "proof_chain",
                "inference",
                "rule",
                "conflict",
            )
        ):
            return SemanticMode.QUERY
        if any(row in families for row in ("transition", "learning_directive", "effect")):
            return SemanticMode.REQUEST
        if any(row in families for row in ("transition_simulation", "simulation")):
            return SemanticMode.SIMULATE
        return SemanticMode.OBSERVE

    @staticmethod
    def _outcome(
        families: list[str], expressions: list[SemanticExpression]
    ) -> tuple[ExpectedOutcomeKind, ExpressionRelation, str]:
        if "adversarial" in families:
            return (
                ExpectedOutcomeKind.VERIFICATION_REJECTION,
                ExpressionRelation.NONE,
                "exact-verifier",
            )
        if "gap" in families:
            return ExpectedOutcomeKind.GAP, ExpressionRelation.NONE, "runtime"
        if "restart" in families:
            return (
                ExpectedOutcomeKind.RESTART,
                ExpressionRelation.NONE,
                "persistence-recovery",
            )
        if "realization_equivalence" in families:
            return (
                ExpectedOutcomeKind.REALIZATION_EQUIVALENCE,
                ExpressionRelation.NONE,
                "response-contract",
            )
        if "polysemy" in families:
            return (
                ExpectedOutcomeKind.AMBIGUITY,
                ExpressionRelation.ANY,
                "form-context",
            )
        if "conflict" in families:
            return (
                ExpectedOutcomeKind.SEMANTIC,
                ExpressionRelation.CONFLICT,
                "decision-query-proof",
            )
        if any(row in families for row in ("rule", "inference", "proof_chain")):
            relation = (
                ExpressionRelation.SINGLE
                if len(expressions) == 1
                else ExpressionRelation.ORDERED_CHAIN
            )
            return ExpectedOutcomeKind.SEMANTIC, relation, "decision-query-proof"
        if len(expressions) == 1:
            return ExpectedOutcomeKind.SEMANTIC, ExpressionRelation.SINGLE, "runtime"
        if expressions:
            return ExpectedOutcomeKind.SEMANTIC, ExpressionRelation.ALL, "runtime"
        raise ValueError("semantic reviewed assertions compiled to no expression")

    @staticmethod
    def _gap_owner(kind: str) -> str:
        return {
            "evidence": "form-context",
            "designation": "form-context",
            "reference": "form-context",
            "authority": "authority-link",
            "proposal": "recursive-composer",
            "verification": "exact-verifier",
            "inference": "decision-query-proof",
            "state": "epistemic-state",
            "transition": "capability-effect",
            "learning": "learning-dialogue",
            "resource": "capability-effect",
            "permission": "capability-effect",
            "adapter": "capability-effect",
            "operation": "capability-effect",
            "storage": "persistence-recovery",
            "realization": "response-contract",
            "performance": "runtime-activation",
            "implementation": "runtime-activation",
        }.get(kind, "runtime")

    def _contracts(
        self,
        mode: SemanticMode,
        outcome: ExpectedOutcomeKind,
        families: list[str],
        expressions: list[SemanticExpression],
        normalized: list[Mapping[str, Any]],
    ) -> tuple[
        ExpectedDecisionContract,
        ExpectedEffectContract,
        ExpectedResponseContract,
    ]:
        if outcome in {
            ExpectedOutcomeKind.GAP,
            ExpectedOutcomeKind.VERIFICATION_REJECTION,
        }:
            return (
                ExpectedDecisionContract(
                    DecisionStatus.FAILED,
                    DecisionAction.NO_OP,
                    blocker_refs=("expected_gap",),
                ),
                ExpectedEffectContract(ExpectedEffectKind.NO_EFFECT, "unknown"),
                ExpectedResponseContract(
                    "report_gap",
                    CycleStatus.UNSUPPORTED,
                    "polarity:positive",
                    "modality:actual",
                    "epistemic:unknown",
                ),
            )
        if outcome is ExpectedOutcomeKind.RESTART:
            return (
                ExpectedDecisionContract(
                    DecisionStatus.UNKNOWN,
                    DecisionAction.NO_OP,
                    blocker_refs=("restart_contract",),
                ),
                ExpectedEffectContract(ExpectedEffectKind.NO_EFFECT, "read_only"),
                ExpectedResponseContract(
                    "report_restart",
                    CycleStatus.RESOLVED,
                    "polarity:positive",
                    "modality:actual",
                    "epistemic:observed",
                ),
            )
        if outcome is ExpectedOutcomeKind.REALIZATION_EQUIVALENCE:
            row = next(
                item for item in normalized if item.get("kind") in {"realization_equiv", "realization_equivalence"}
            )
            status_map = {
                "resolved": CycleStatus.RESOLVED,
                "unknown": CycleStatus.UNKNOWN,
                "denied": CycleStatus.DENIED,
                "ambiguous": CycleStatus.AMBIGUOUS,
            }
            cycle_status = status_map.get(str(row["status"]), CycleStatus.PARTIAL)
            decision_status = {
                CycleStatus.RESOLVED: DecisionStatus.SUPPORTED,
                CycleStatus.UNKNOWN: DecisionStatus.UNKNOWN,
                CycleStatus.DENIED: DecisionStatus.DENIED,
                CycleStatus.AMBIGUOUS: DecisionStatus.PARTIAL,
            }[cycle_status]
            action = (
                DecisionAction.ANSWER
                if decision_status is DecisionStatus.SUPPORTED
                else DecisionAction.REQUEST_CLARIFICATION
                if decision_status is DecisionStatus.PARTIAL
                else DecisionAction.NO_OP
            )
            blockers = () if action is DecisionAction.ANSWER else ("expected_realization_status",)
            return (
                ExpectedDecisionContract(decision_status, action, blocker_refs=blockers),
                ExpectedEffectContract(ExpectedEffectKind.NO_EFFECT, "read_only"),
                ExpectedResponseContract(
                    str(row["discourse_action"]),
                    cycle_status,
                    "polarity:positive",
                    "modality:actual",
                    "epistemic:supported" if cycle_status is CycleStatus.RESOLVED else "epistemic:unknown",
                ),
            )
        if mode is SemanticMode.QUERY:
            if "conflict" in families:
                return (
                    ExpectedDecisionContract(
                        DecisionStatus.CONFLICT,
                        DecisionAction.REQUEST_CLARIFICATION,
                        blocker_refs=("expected_conflict",),
                    ),
                    ExpectedEffectContract(ExpectedEffectKind.NO_EFFECT, "conflict"),
                    ExpectedResponseContract(
                        "clarify_conflict",
                        CycleStatus.CONFLICT,
                        "polarity:positive",
                        "modality:actual",
                        "epistemic:conflict",
                    ),
                )
            if outcome is ExpectedOutcomeKind.AMBIGUITY:
                return (
                    ExpectedDecisionContract(
                        DecisionStatus.PARTIAL,
                        DecisionAction.REQUEST_CLARIFICATION,
                        blocker_refs=("expected_ambiguity",),
                    ),
                    ExpectedEffectContract(ExpectedEffectKind.NO_EFFECT, "read_only"),
                    ExpectedResponseContract(
                        "clarify",
                        CycleStatus.AMBIGUOUS,
                        "polarity:positive",
                        "modality:actual",
                        "epistemic:unknown",
                    ),
                )
            proof_refs = tuple(
                str(value)
                for row in normalized
                for key, value in row.items()
                if key == "rule" or key == "rule_ref"
            )
            return (
                ExpectedDecisionContract(
                    DecisionStatus.SUPPORTED,
                    DecisionAction.ANSWER,
                    required_proof_refs=proof_refs,
                ),
                ExpectedEffectContract(ExpectedEffectKind.NO_EFFECT, "read_only"),
                ExpectedResponseContract(
                    "answer",
                    CycleStatus.RESOLVED,
                    "polarity:positive",
                    "modality:actual",
                    "epistemic:supported",
                ),
            )
        if mode is SemanticMode.REQUEST:
            if "learning_directive" in families:
                return (
                    ExpectedDecisionContract(
                        DecisionStatus.PENDING,
                        DecisionAction.CREATE_LEARNING_OBLIGATION,
                    ),
                    ExpectedEffectContract(
                        ExpectedEffectKind.NO_EFFECT, "learning_obligation_only"
                    ),
                    ExpectedResponseContract(
                        "request_learning_evidence",
                        CycleStatus.PARTIAL,
                        "polarity:positive",
                        "modality:actual",
                        "epistemic:pending",
                    ),
                )
            event_ref = next(
                (
                    str(row["event"])
                    for row in normalized
                    if row.get("event") is not None
                ),
                None,
            )
            adapter = next(
                (
                    str(row["adapter"])
                    for row in normalized
                    if row.get("adapter") is not None
                ),
                None,
            )
            if adapter is None and event_ref in self._authority.event_signatures:
                adapter = self._authority.event_signatures[event_ref].adapter_ref
            return (
                ExpectedDecisionContract(
                    DecisionStatus.PENDING, DecisionAction.REQUEST_EFFECT
                ),
                ExpectedEffectContract(
                    ExpectedEffectKind.EFFECT,
                    "committed",
                    required_adapter_ref=adapter,
                ),
                ExpectedResponseContract(
                    "report_effect",
                    CycleStatus.RESOLVED,
                    "polarity:positive",
                    "modality:actual",
                    "epistemic:observed",
                ),
            )
        if mode is SemanticMode.SIMULATE:
            return (
                ExpectedDecisionContract(
                    DecisionStatus.SIMULATION, DecisionAction.PREVIEW_TRANSITION
                ),
                ExpectedEffectContract(ExpectedEffectKind.NO_EFFECT, "simulation"),
                ExpectedResponseContract(
                    "report_simulation",
                    CycleStatus.RESOLVED,
                    "polarity:positive",
                    "modality:simulated",
                    "epistemic:simulated",
                ),
            )
        trusted = any(row in families for row in ("evidence",))
        attributed = any(
            row in families for row in ("attribution", "teaching", "learning_event")
        )
        if trusted:
            return (
                ExpectedDecisionContract(
                    DecisionStatus.ADMITTED,
                    DecisionAction.ADMIT_CLAIM,
                    required_proof_refs=("trusted_evidence",),
                ),
                ExpectedEffectContract(ExpectedEffectKind.EFFECT, "committed"),
                ExpectedResponseContract(
                    "acknowledge_observation",
                    CycleStatus.RESOLVED,
                    "polarity:positive",
                    "modality:actual",
                    "epistemic:observed",
                ),
            )
        if attributed:
            return (
                ExpectedDecisionContract(
                    DecisionStatus.ATTRIBUTED,
                    DecisionAction.RETAIN_ATTRIBUTION,
                ),
                ExpectedEffectContract(
                    ExpectedEffectKind.NO_EFFECT, "attributed_only"
                ),
                ExpectedResponseContract(
                    "acknowledge_attribution",
                    CycleStatus.RESOLVED,
                    "polarity:positive",
                    "modality:actual",
                    "epistemic:attributed",
                ),
            )
        return (
            ExpectedDecisionContract(
                DecisionStatus.CONTESTED, DecisionAction.ACKNOWLEDGE
            ),
            ExpectedEffectContract(ExpectedEffectKind.NO_EFFECT, "attributed_only"),
            ExpectedResponseContract(
                "acknowledge_claim",
                CycleStatus.RESOLVED,
                "polarity:positive",
                "modality:actual",
                "epistemic:contested",
            ),
        )

