"""Typed, authority-backed learning-plan ABI.

Learning is a semantic goal and commit protocol, not a free-form runtime string.
A plan is created only after an exact query has executed and is preserved through
GoalCandidate, ResponseCSIR, dialogue state, Stage-13 commit and receipt-bound
obligation consumption.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from typing import Any, Mapping

LEARNING_PLAN_ABI = 1
DESIGNATION_LEARNING_CONTRACT = "contract:designation_learning"
DESIGNATION_LEARNING_GOAL = "goal:acquire_designation"
DESIGNATION_ANSWER_CONTRACT = "contract:designation_target_answer"


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def stable(namespace: str, *parts: Any) -> str:
    digest = hashlib.sha256(canonical((namespace, parts)).encode("utf-8")).hexdigest()[:24]
    return f"{namespace}:{digest}"


@dataclass(frozen=True)
class LearningContractSpec:
    contract_ref: str
    goal_ref: str
    capability_ref: str
    commit_operator_ref: str
    answer_contract_ref: str
    expected_target_kinds: tuple[str, ...]
    licensed_query_kinds: tuple[str, ...]
    label_type_ref: str | None = None

    def __post_init__(self) -> None:
        required = (
            self.contract_ref,
            self.goal_ref,
            self.capability_ref,
            self.commit_operator_ref,
            self.answer_contract_ref,
        )
        if any(not item for item in required):
            raise ValueError("learning contract is structurally incomplete")
        if not self.expected_target_kinds or len(self.expected_target_kinds) > 16:
            raise ValueError("learning contract requires 1..16 target kinds")
        if not self.licensed_query_kinds or len(self.licensed_query_kinds) > 16:
            raise ValueError("learning contract requires 1..16 query kinds")

    @classmethod
    def from_atom(cls, contract_ref: str, metadata: Mapping[str, Any]) -> "LearningContractSpec":
        payload = dict(metadata.get("learning_contract", metadata))
        return cls(
            contract_ref=str(contract_ref),
            goal_ref=str(payload.get("goal_ref") or ""),
            capability_ref=str(payload.get("capability_ref") or ""),
            commit_operator_ref=str(payload.get("commit_operator_ref") or ""),
            answer_contract_ref=str(payload.get("answer_contract_ref") or ""),
            expected_target_kinds=tuple(sorted({
                str(item) for item in payload.get("expected_target_kinds", ()) if str(item)
            })),
            licensed_query_kinds=tuple(sorted({
                str(item) for item in payload.get("licensed_query_kinds", ()) if str(item)
            })),
            label_type_ref=(
                str(payload["label_type_ref"])
                if payload.get("label_type_ref")
                else None
            ),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract_ref": self.contract_ref,
            "goal_ref": self.goal_ref,
            "capability_ref": self.capability_ref,
            "commit_operator_ref": self.commit_operator_ref,
            "answer_contract_ref": self.answer_contract_ref,
            "expected_target_kinds": list(self.expected_target_kinds),
            "licensed_query_kinds": list(self.licensed_query_kinds),
            "label_type_ref": self.label_type_ref,
        }


class LearningContractRegistry:
    """Generation-pinned loader and validator for learning contracts."""

    def __init__(self, store: Any, authority_generation: int | None = None) -> None:
        self.store = store
        self.authority_generation = authority_generation
        self._cache: dict[str, LearningContractSpec] = {}

    @staticmethod
    def _kind(atom: Any) -> str:
        return str(atom["kind"] if isinstance(atom, Mapping) or hasattr(atom, "keys") else atom.kind)

    @staticmethod
    def _metadata(atom: Any) -> Mapping[str, Any]:
        raw = atom["metadata"] if isinstance(atom, Mapping) or hasattr(atom, "keys") else atom.metadata
        return dict(json.loads(raw) if isinstance(raw, str) else raw or {})

    def _atom(self, ref: str) -> Any:
        if hasattr(self.store, "authority_atom"):
            return self.store.authority_atom(ref, upto_generation=self.authority_generation)
        return self.store.atom(ref)

    def get(self, contract_ref: str) -> LearningContractSpec:
        ref = str(contract_ref)
        if ref in self._cache:
            return self._cache[ref]
        atom = self._atom(ref)
        if atom is None:
            raise ValueError(f"learning contract is missing: {ref}")
        if self._kind(atom) != "concept":
            raise ValueError(f"learning contract must be a concept atom: {ref}")
        spec = LearningContractSpec.from_atom(ref, self._metadata(atom))
        checks = (
            (spec.goal_ref, "goal"),
            (spec.capability_ref, "capability"),
            (spec.commit_operator_ref, "operator"),
            (spec.answer_contract_ref, "concept"),
        )
        if spec.label_type_ref:
            checks += ((spec.label_type_ref, "label_type"),)
        for target_ref, expected_kind in checks:
            target = self._atom(target_ref)
            if target is None:
                raise ValueError(f"learning contract target is missing: {target_ref}")
            actual = self._kind(target)
            if actual != expected_kind:
                raise ValueError(
                    f"learning contract target {target_ref} must be {expected_kind}, found {actual}"
                )
        relation_ref = "rel:licenses_learning_contract"
        relation = self._atom(relation_ref)
        if relation is None or self._kind(relation) != "relation_type":
            raise ValueError("learning-contract licensing relation is missing")
        relation_objects = getattr(self.store, "relation_objects", None)
        if not callable(relation_objects):
            raise ValueError("store cannot validate learning-contract licensing")
        licensed = set(relation_objects(
            spec.capability_ref,
            relation_ref,
            authority_only=True,
            upto_generation=self.authority_generation,
        ))
        if ref not in licensed:
            raise ValueError(
                f"capability {spec.capability_ref} does not license learning contract {ref}"
            )
        self._cache[ref] = spec
        return spec

    def license_query(self, contract_ref: str, query_kind: str) -> LearningContractSpec:
        spec = self.get(contract_ref)
        if str(query_kind) not in set(spec.licensed_query_kinds):
            raise ValueError(
                f"learning contract {contract_ref} does not license query kind {query_kind}"
            )
        return spec


@dataclass(frozen=True)
class LearningPlan:
    plan_ref: str
    contract_ref: str
    source_query_ref: str
    source_query_kind: str
    source_query: Mapping[str, Any]
    authority_generation: int
    goal_ref: str
    capability_ref: str
    commit_operator_ref: str
    answer_contract_ref: str
    surface_literal: str
    language: str
    expected_target_kinds: tuple[str, ...]
    label_type_ref: str | None = None
    target_ref: str | None = None
    known_bindings: Mapping[str, Any] = field(default_factory=dict)
    original_candidate_ref: str | None = None
    unresolved_span_ref: str | None = None
    source_response_ref: str | None = None
    source_goal_ref: str | None = None
    created_turn: int = 0
    expires_after_turn: int = 4

    @staticmethod
    def _material(
        *,
        contract_ref: str,
        source_query_ref: str,
        source_query_kind: str,
        source_query: Mapping[str, Any],
        authority_generation: int,
        goal_ref: str,
        capability_ref: str,
        commit_operator_ref: str,
        answer_contract_ref: str,
        surface_literal: str,
        language: str,
        expected_target_kinds: tuple[str, ...],
        label_type_ref: str | None,
        target_ref: str | None,
        known_bindings: Mapping[str, Any],
        original_candidate_ref: str | None,
        unresolved_span_ref: str | None,
        source_response_ref: str | None,
        source_goal_ref: str | None,
        created_turn: int,
        expires_after_turn: int,
    ) -> dict[str, Any]:
        return {
            "learning_plan_abi": LEARNING_PLAN_ABI,
            "contract_ref": str(contract_ref),
            "source_query_ref": str(source_query_ref),
            "source_query_kind": str(source_query_kind),
            "source_query": dict(source_query),
            "authority_generation": int(authority_generation),
            "goal_ref": str(goal_ref),
            "capability_ref": str(capability_ref),
            "commit_operator_ref": str(commit_operator_ref),
            "answer_contract_ref": str(answer_contract_ref),
            "surface_literal": str(surface_literal),
            "language": str(language),
            "expected_target_kinds": list(expected_target_kinds),
            "label_type_ref": label_type_ref,
            "target_ref": target_ref,
            "known_bindings": dict(known_bindings),
            "original_candidate_ref": original_candidate_ref,
            "unresolved_span_ref": unresolved_span_ref,
            "source_response_ref": source_response_ref,
            "source_goal_ref": source_goal_ref,
            "created_turn": int(created_turn),
            "expires_after_turn": int(expires_after_turn),
        }

    def _identity_material(self) -> dict[str, Any]:
        return self._material(
            contract_ref=self.contract_ref,
            source_query_ref=self.source_query_ref,
            source_query_kind=self.source_query_kind,
            source_query=self.source_query,
            authority_generation=self.authority_generation,
            goal_ref=self.goal_ref,
            capability_ref=self.capability_ref,
            commit_operator_ref=self.commit_operator_ref,
            answer_contract_ref=self.answer_contract_ref,
            surface_literal=self.surface_literal,
            language=self.language,
            expected_target_kinds=self.expected_target_kinds,
            label_type_ref=self.label_type_ref,
            target_ref=self.target_ref,
            known_bindings=self.known_bindings,
            original_candidate_ref=self.original_candidate_ref,
            unresolved_span_ref=self.unresolved_span_ref,
            source_response_ref=self.source_response_ref,
            source_goal_ref=self.source_goal_ref,
            created_turn=self.created_turn,
            expires_after_turn=self.expires_after_turn,
        )

    def __post_init__(self) -> None:
        required = {
            "plan_ref": self.plan_ref,
            "contract_ref": self.contract_ref,
            "source_query_ref": self.source_query_ref,
            "source_query_kind": self.source_query_kind,
            "authority_generation": self.authority_generation,
            "goal_ref": self.goal_ref,
            "capability_ref": self.capability_ref,
            "commit_operator_ref": self.commit_operator_ref,
            "answer_contract_ref": self.answer_contract_ref,
            "surface_literal": self.surface_literal.strip(),
            "language": self.language,
        }
        missing = sorted(key for key, value in required.items() if not value)
        if missing:
            raise ValueError(f"learning plan lacks required fields: {missing}")
        if not isinstance(self.source_query, Mapping) or not self.source_query:
            raise ValueError("learning plan requires the exact executed query")
        if int(self.authority_generation) < 1:
            raise ValueError("learning plan requires positive authority generation")
        query_ref = self.source_query.get("query_ref")
        if query_ref not in (None, self.source_query_ref):
            raise ValueError("learning plan source query payload/ref mismatch")
        qualifiers = dict(self.source_query.get("qualifiers", {}) or {})
        if qualifiers.get("query_kind") not in (None, self.source_query_kind):
            raise ValueError("learning plan source query kind/payload mismatch")
        if not self.expected_target_kinds or len(self.expected_target_kinds) > 16:
            raise ValueError("learning plan requires 1..16 expected target kinds")
        if self.created_turn < 0 or self.expires_after_turn < 1:
            raise ValueError("learning plan carries invalid turn bounds")
        if bool(self.source_response_ref) != bool(self.source_goal_ref):
            raise ValueError("learning plan response and goal provenance must be bound together")
        namespace = "learning-plan-bound" if self.source_response_ref else "learning-plan"
        expected_ref = stable(namespace, self._identity_material())
        if self.plan_ref != expected_ref:
            raise ValueError("learning plan identity does not match its semantic payload")

    @classmethod
    def create(
        cls,
        *,
        contract: LearningContractSpec,
        source_query_ref: str,
        source_query_kind: str,
        source_query: Mapping[str, Any],
        authority_generation: int,
        surface_literal: str,
        language: str,
        expected_target_kinds: tuple[str, ...] | None = None,
        known_bindings: Mapping[str, Any] | None = None,
        target_ref: str | None = None,
        original_candidate_ref: str | None = None,
        unresolved_span_ref: str | None = None,
        created_turn: int = 0,
        expires_after_turn: int = 4,
    ) -> "LearningPlan":
        if str(source_query_kind) not in set(contract.licensed_query_kinds):
            raise ValueError(
                f"contract {contract.contract_ref} does not license query kind {source_query_kind}"
            )
        query = dict(source_query or {})
        if not query:
            raise ValueError("learning plan requires the exact executed query")
        requested = tuple(sorted(set(expected_target_kinds or contract.expected_target_kinds)))
        if set(requested) - set(contract.expected_target_kinds):
            raise ValueError("learning plan broadens contract target kinds")
        material = cls._material(
            contract_ref=contract.contract_ref,
            source_query_ref=str(source_query_ref),
            source_query_kind=str(source_query_kind),
            source_query=query,
            authority_generation=int(authority_generation),
            goal_ref=contract.goal_ref,
            capability_ref=contract.capability_ref,
            commit_operator_ref=contract.commit_operator_ref,
            answer_contract_ref=contract.answer_contract_ref,
            surface_literal=str(surface_literal),
            language=str(language),
            expected_target_kinds=requested,
            label_type_ref=contract.label_type_ref,
            target_ref=target_ref,
            known_bindings=dict(known_bindings or {}),
            original_candidate_ref=original_candidate_ref,
            unresolved_span_ref=unresolved_span_ref,
            source_response_ref=None,
            source_goal_ref=None,
            created_turn=int(created_turn),
            expires_after_turn=int(expires_after_turn),
        )
        return cls(
            plan_ref=stable("learning-plan", material),
            contract_ref=contract.contract_ref,
            source_query_ref=str(source_query_ref),
            source_query_kind=str(source_query_kind),
            source_query=query,
            authority_generation=int(authority_generation),
            goal_ref=contract.goal_ref,
            capability_ref=contract.capability_ref,
            commit_operator_ref=contract.commit_operator_ref,
            answer_contract_ref=contract.answer_contract_ref,
            surface_literal=str(surface_literal),
            language=str(language),
            expected_target_kinds=requested,
            label_type_ref=contract.label_type_ref,
            target_ref=target_ref,
            known_bindings=dict(known_bindings or {}),
            original_candidate_ref=original_candidate_ref,
            unresolved_span_ref=unresolved_span_ref,
            created_turn=int(created_turn),
            expires_after_turn=int(expires_after_turn),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LearningPlan":
        abi = int(value.get("learning_plan_abi", -1))
        if abi != LEARNING_PLAN_ABI:
            raise ValueError(f"unsupported learning plan ABI: {abi}")
        return cls(
            plan_ref=str(value.get("plan_ref") or ""),
            contract_ref=str(value.get("contract_ref") or ""),
            source_query_ref=str(value.get("source_query_ref") or ""),
            source_query_kind=str(value.get("source_query_kind") or ""),
            source_query=dict(value.get("source_query", {})),
            authority_generation=int(value.get("authority_generation", 0)),
            goal_ref=str(value.get("goal_ref") or ""),
            capability_ref=str(value.get("capability_ref") or ""),
            commit_operator_ref=str(value.get("commit_operator_ref") or ""),
            answer_contract_ref=str(value.get("answer_contract_ref") or ""),
            surface_literal=str(value.get("surface_literal") or ""),
            language=str(value.get("language") or ""),
            expected_target_kinds=tuple(map(str, value.get("expected_target_kinds", ()))),
            label_type_ref=value.get("label_type_ref"),
            target_ref=value.get("target_ref"),
            known_bindings=dict(value.get("known_bindings", {})),
            original_candidate_ref=value.get("original_candidate_ref"),
            unresolved_span_ref=value.get("unresolved_span_ref"),
            source_response_ref=value.get("source_response_ref"),
            source_goal_ref=value.get("source_goal_ref"),
            created_turn=int(value.get("created_turn", 0)),
            expires_after_turn=int(value.get("expires_after_turn", 4)),
        )

    def bind_response(self, *, response_ref: str, goal_ref: str) -> "LearningPlan":
        material = self._material(
            contract_ref=self.contract_ref,
            source_query_ref=self.source_query_ref,
            source_query_kind=self.source_query_kind,
            source_query=self.source_query,
            authority_generation=self.authority_generation,
            goal_ref=self.goal_ref,
            capability_ref=self.capability_ref,
            commit_operator_ref=self.commit_operator_ref,
            answer_contract_ref=self.answer_contract_ref,
            surface_literal=self.surface_literal,
            language=self.language,
            expected_target_kinds=self.expected_target_kinds,
            label_type_ref=self.label_type_ref,
            target_ref=self.target_ref,
            known_bindings=self.known_bindings,
            original_candidate_ref=self.original_candidate_ref,
            unresolved_span_ref=self.unresolved_span_ref,
            source_response_ref=str(response_ref),
            source_goal_ref=str(goal_ref),
            created_turn=self.created_turn,
            expires_after_turn=self.expires_after_turn,
        )
        return LearningPlan.from_dict({
            **material,
            "plan_ref": stable("learning-plan-bound", material),
        })

    def expired(self, current_turn: int) -> bool:
        return int(current_turn) > self.created_turn + self.expires_after_turn

    def validate_authority(
        self,
        store: Any,
        *,
        authority_generation: int | None = None,
    ) -> LearningContractSpec:
        if authority_generation is not None and int(authority_generation) != self.authority_generation:
            raise ValueError("learning plan authority generation differs from runtime pin")
        registry = LearningContractRegistry(store, self.authority_generation)
        contract = registry.license_query(self.contract_ref, self.source_query_kind)
        expected = {
            "goal_ref": contract.goal_ref,
            "capability_ref": contract.capability_ref,
            "commit_operator_ref": contract.commit_operator_ref,
            "answer_contract_ref": contract.answer_contract_ref,
            "label_type_ref": contract.label_type_ref,
        }
        for field_name, value in expected.items():
            if getattr(self, field_name) != value:
                raise ValueError(f"learning plan differs from authority contract at {field_name}")
        if set(self.expected_target_kinds) - set(contract.expected_target_kinds):
            raise ValueError("learning plan target kinds exceed contract")
        if self.target_ref:
            target = store.atom(self.target_ref)
            if target is None:
                raise ValueError(f"learning plan target is missing: {self.target_ref}")
            if str(target["kind"]) not in self.expected_target_kinds:
                raise ValueError("learning plan target kind is outside expected set")
        return contract

    def as_dict(self) -> dict[str, Any]:
        return {"plan_ref": self.plan_ref, **self._identity_material()}

    def semantic_signature(self) -> str:
        return canonical(self.as_dict())


@dataclass(frozen=True)
class PendingLearningObligationV2:
    obligation_ref: str
    plan: LearningPlan

    def __post_init__(self) -> None:
        if not self.obligation_ref:
            raise ValueError("pending learning obligation requires obligation_ref")
        if not self.plan.source_response_ref or not self.plan.source_goal_ref:
            raise ValueError("pending learning obligation requires response and goal provenance")

    def expired(self, current_turn: int) -> bool:
        return self.plan.expired(current_turn)

    def as_dict(self) -> dict[str, Any]:
        return {
            "obligation_ref": self.obligation_ref,
            "learning_plan": self.plan.as_dict(),
        }


def validate_learning_commit_packet(
    packet: Mapping[str, Any],
    obligation: PendingLearningObligationV2,
    store: Any,
    *,
    authority_generation: int | None = None,
) -> dict[str, Any]:
    """Validate the exact semantic effect that may consume a learning obligation."""
    plan = obligation.plan
    plan.validate_authority(
        store, authority_generation=authority_generation
    )
    applications = list(packet.get("apps", ()))
    applications += list((packet.get("directive") or {}).get("content", ()))
    if len(applications) != 1:
        raise ValueError(
            "learning continuation may commit exactly one semantic application"
        )
    matching = [
        dict(item)
        for item in applications
        if item.get("operator") == plan.commit_operator_ref
    ]
    if len(matching) != 1:
        raise ValueError("learning continuation requires exactly one contract commit application")
    app = matching[0]
    validate_app = getattr(store, "validate_app", None)
    if callable(validate_app):
        validate_app(str(app.get("operator")), dict(app.get("args", {})))
    args = dict(app.get("args", {}))
    if plan.commit_operator_ref == "op:designation":
        target_ref = args.get("role:target")
        surface = args.get("role:surface")
        label_type = args.get("role:label_type")
        language = args.get("role:language")
        if isinstance(surface, Mapping) and isinstance(surface.get("literal"), Mapping):
            surface = surface["literal"].get("value")
        if isinstance(language, Mapping) and isinstance(language.get("literal"), Mapping):
            language = language["literal"].get("value")
        if str(surface or "") != plan.surface_literal:
            raise ValueError("designation learning commit changes the unresolved surface")
        if plan.label_type_ref and label_type != plan.label_type_ref:
            raise ValueError("designation learning commit changes the licensed label type")
        if language not in (None, plan.language):
            raise ValueError("designation learning commit changes the plan language")
        if plan.target_ref and target_ref != plan.target_ref:
            raise ValueError("designation learning commit changes the bound target")
        atom = store.atom(str(target_ref)) if isinstance(target_ref, str) else None
        if atom is None:
            raise ValueError("designation learning target is missing")
        if str(atom["kind"]) not in set(plan.expected_target_kinds):
            raise ValueError("designation learning target kind is outside plan")
    else:
        target_ref = None
    qualifiers = dict(packet.get("qualifiers", {}))
    if qualifiers.get("pending_learning_obligation_ref") != obligation.obligation_ref:
        raise ValueError("learning continuation obligation ref mismatch")
    if qualifiers.get("learning_plan_ref") != plan.plan_ref:
        raise ValueError("learning continuation plan ref mismatch")
    return {
        "plan_ref": plan.plan_ref,
        "contract_ref": plan.contract_ref,
        "commit_operator_ref": plan.commit_operator_ref,
        "target_ref": target_ref,
        "application": app,
    }
