"""Authentic R4 episodes and structural expected/observed comparison."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping, Protocol, runtime_checkable

from .canonical import stable_ref
from .cycle import PhaseReceipt, SemanticMode
from .decision import Decision
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
    UnresolvedValue,
    VariableBinder,
)
from .forms import EvidenceItem
from .r3_codec import (
    exact_fields,
    exact_refs,
    exact_text,
    freeze_json,
    thaw_json,
    wire_refs,
)
from .r3_cycle import CycleResult
from .r3_effects import EffectReceipt, NoEffectReceipt
from .r4_contracts import (
    ExpectedCycleContract,
    ExpectedEffectKind,
    ExpectedOutcomeKind,
    ExpressionRelation,
)
from .r4_expansion import ExpandedCase

COMPARISON_RECEIPT_ABI_VERSION = 2
AUTHENTIC_EPISODE_ABI_VERSION = 3

__all__ = [
    "COMPARISON_RECEIPT_ABI_VERSION",
    "AUTHENTIC_EPISODE_ABI_VERSION",
    "EpisodeExecutionResult",
    "EpisodeExecutionOwner",
    "PublicRuntimeEpisodeOwner",
    "ComparisonReceipt",
    "AuthenticEpisode",
    "AuthenticEpisodeBuilder",
]


@dataclass(frozen=True)
class EpisodeExecutionResult:
    cycle: CycleResult
    environment_observation_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.cycle) is not CycleResult:
            raise TypeError("cycle must be exact CycleResult")
        object.__setattr__(
            self,
            "environment_observation_refs",
            exact_refs(
                self.environment_observation_refs,
                "environment_observation_refs",
            ),
        )


@runtime_checkable
class EpisodeExecutionOwner(Protocol):
    def execute_case(
        self, case: ExpandedCase, *, session_ref: str
    ) -> EpisodeExecutionResult:
        raise NotImplementedError


def _item_from_spec(case: ExpandedCase, index: int, raw: Mapping[str, Any]) -> EvidenceItem:
    source = raw.get("source")
    if source not in {"sensor", "operation"}:
        raise ValueError("R4 extra evidence must be sensor or operation evidence")
    content = raw.get("content")
    if not isinstance(content, Mapping):
        raise TypeError("sensor/operation evidence content must be a mapping")
    source_ref = raw.get("source_ref") or stable_ref(
        "r4_evidence_source",
        {"case_ref": case.case_ref, "index": index, "source": source},
    )
    provenance = raw.get("provenance_refs", [])
    if type(provenance) is not list:
        raise TypeError("evidence provenance_refs must be a list")
    adapter_receipt_ref = raw.get("adapter_receipt_ref")
    if type(adapter_receipt_ref) is not str or not adapter_receipt_ref:
        raise ValueError("reviewed sensor/operation evidence requires adapter receipt")
    return EvidenceItem.create(
        source=source,
        content=dict(content),
        source_ref=source_ref,
        provenance_refs=tuple(provenance),
        adapter_receipt_ref=adapter_receipt_ref,
    )


class PublicRuntimeEpisodeOwner:
    """Execute expanded cases exclusively through HybridRuntime public methods.

    Runtime instances are retained by trajectory so multi-turn cases share
    session/focus/obligation/effect state.  Restart scenarios require an
    injected restart executor; they are never converted into ordinary chats.
    """

    def __init__(
        self,
        runtime_factory: Callable[[ExpandedCase], Any],
        *,
        restart_executor: Any | None = None,
    ) -> None:
        if not callable(runtime_factory):
            raise TypeError("runtime_factory must be callable")
        self._factory = runtime_factory
        self._restart = restart_executor
        self._runtimes: dict[str, Any] = {}

    def _runtime(self, case: ExpandedCase) -> Any:
        runtime = self._runtimes.get(case.trajectory_ref)
        if runtime is None:
            runtime = self._factory(case)
            for method in ("create_evidence", "process_evidence"):
                if not callable(getattr(runtime, method, None)):
                    raise TypeError("runtime factory did not return public R3 runtime")
            self._runtimes[case.trajectory_ref] = runtime
        return runtime

    def execute_case(
        self, case: ExpandedCase, *, session_ref: str
    ) -> EpisodeExecutionResult:
        if type(case) is not ExpandedCase:
            raise TypeError("case must be exact ExpandedCase")
        if case.contract.outcome_kind is ExpectedOutcomeKind.RESTART:
            if self._restart is None or not callable(
                getattr(self._restart, "execute_restart_case", None)
            ):
                raise RuntimeError("restart contract requires authentic restart executor")
            result = self._restart.execute_restart_case(case, session_ref=session_ref)
            if type(result) is not EpisodeExecutionResult:
                raise TypeError("restart executor returned non-canonical result")
            return EpisodeExecutionResult(
                _without_observational_timing(result.cycle),
                result.environment_observation_refs,
            )
        runtime = self._runtime(case)
        raw_items = thaw_json(case.environment).get("evidence_items", [])
        if type(raw_items) is not list:
            raise TypeError("environment evidence_items must be a list")
        extra_items = tuple(
            _item_from_spec(case, index, row)
            for index, row in enumerate(raw_items)
            if isinstance(row, Mapping)
        )
        if len(extra_items) != len(raw_items):
            raise TypeError("evidence_items rows must be mappings")
        evidence = runtime.create_evidence(
            session_ref,
            case.surface,
            extra_items=extra_items,
        )
        cycle = runtime.process_evidence(session_ref, evidence, trace=True)
        if type(cycle) is not CycleResult:
            raise TypeError("public runtime returned non-canonical CycleResult ABI 3")
        observations = tuple(
            item.adapter_receipt_ref
            for item in extra_items
            if item.adapter_receipt_ref is not None
        )
        return EpisodeExecutionResult(_without_observational_timing(cycle), observations)


def _without_observational_timing(cycle: CycleResult) -> CycleResult:
    """Retain exact semantic trace material with deterministic duration values."""

    if type(cycle) is not CycleResult:
        raise TypeError("cycle must be exact CycleResult")
    trace = tuple(
        PhaseReceipt.create(
            cycle_ref=cycle.cycle_ref,
            material=receipt.material,
            duration_ns=0,
        )
        for receipt in cycle.trace
    )
    return CycleResult(
        abi_version=cycle.abi_version,
        cycle_ref=cycle.cycle_ref,
        input_ref=cycle.input_ref,
        status=cycle.status,
        orientation=cycle.orientation,
        proposal=cycle.proposal,
        verification=cycle.verification,
        evaluation=cycle.evaluation,
        effect_receipt=cycle.effect_receipt,
        response_meaning=cycle.response_meaning,
        realization_receipt=None,
        gap_receipt=cycle.gap_receipt,
        phase_material=cycle.phase_material,
        trace=trace,
        final_revision_pin=cycle.final_revision_pin,
    )


@dataclass(frozen=True, init=False)
class ComparisonReceipt:
    abi_version: int
    receipt_ref: str
    expected_contract_ref: str
    observed_cycle_ref: str
    expression_match: bool
    situation_match: bool
    decision_match: bool
    effect_match: bool
    response_match: bool
    gap_match: bool
    environment_match: bool
    mismatch_codes: tuple[str, ...]

    _FIELDS = frozenset(
        {
            "abi_version",
            "receipt_ref",
            "expected_contract_ref",
            "observed_cycle_ref",
            "expression_match",
            "situation_match",
            "decision_match",
            "effect_match",
            "response_match",
            "gap_match",
            "environment_match",
            "mismatch_codes",
        }
    )

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use ComparisonReceipt.create")

    @classmethod
    def create(
        cls,
        *,
        expected_contract_ref: str,
        observed_cycle_ref: str,
        expression_match: bool,
        situation_match: bool,
        decision_match: bool,
        effect_match: bool,
        response_match: bool,
        gap_match: bool,
        environment_match: bool,
        mismatch_codes: tuple[str, ...],
    ) -> "ComparisonReceipt":
        flags = {
            "expression_match": expression_match,
            "situation_match": situation_match,
            "decision_match": decision_match,
            "effect_match": effect_match,
            "response_match": response_match,
            "gap_match": gap_match,
            "environment_match": environment_match,
        }
        if any(type(value) is not bool for value in flags.values()):
            raise TypeError("comparison flags must be exact bool")
        codes = exact_refs(mismatch_codes, "mismatch_codes")
        if all(flags.values()) != (not codes):
            raise ValueError("comparison flags disagree with mismatch codes")
        material = {
            "abi_version": COMPARISON_RECEIPT_ABI_VERSION,
            "expected_contract_ref": exact_text(
                expected_contract_ref, "expected_contract_ref"
            ),
            "observed_cycle_ref": exact_text(observed_cycle_ref, "observed_cycle_ref"),
            **flags,
            "mismatch_codes": list(codes),
        }
        obj = object.__new__(cls)
        object.__setattr__(obj, "abi_version", COMPARISON_RECEIPT_ABI_VERSION)
        object.__setattr__(obj, "receipt_ref", stable_ref("r4_comparison_v2", material))
        for name, value in material.items():
            if name not in {"abi_version", "mismatch_codes"}:
                object.__setattr__(obj, name, value)
        object.__setattr__(obj, "mismatch_codes", codes)
        return obj

    @property
    def passed(self) -> bool:
        return not self.mismatch_codes

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "receipt_ref": self.receipt_ref,
            "expected_contract_ref": self.expected_contract_ref,
            "observed_cycle_ref": self.observed_cycle_ref,
            "expression_match": self.expression_match,
            "situation_match": self.situation_match,
            "decision_match": self.decision_match,
            "effect_match": self.effect_match,
            "response_match": self.response_match,
            "gap_match": self.gap_match,
            "environment_match": self.environment_match,
            "mismatch_codes": list(self.mismatch_codes),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ComparisonReceipt":
        row = exact_fields(value, cls._FIELDS, "ComparisonReceipt")
        if row["abi_version"] != COMPARISON_RECEIPT_ABI_VERSION:
            raise ValueError("unsupported Comparison Receipt ABI")
        rebuilt = cls.create(
            expected_contract_ref=row["expected_contract_ref"],
            observed_cycle_ref=row["observed_cycle_ref"],
            expression_match=row["expression_match"],
            situation_match=row["situation_match"],
            decision_match=row["decision_match"],
            effect_match=row["effect_match"],
            response_match=row["response_match"],
            gap_match=row["gap_match"],
            environment_match=row["environment_match"],
            mismatch_codes=wire_refs(row["mismatch_codes"], "mismatch_codes"),
        )
        if rebuilt.receipt_ref != row["receipt_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical ComparisonReceipt")
        return rebuilt


def _filler_material(value: object, visit: Callable[[str], Any]) -> Any:
    if isinstance(value, GroundedReference):
        return ["grounded", value.target_ref]
    if isinstance(value, LiteralValue):
        return ["literal", value.value_type, value.value]
    if isinstance(value, BoundVariable):
        return ["variable"]
    if isinstance(value, ApplicationFiller):
        return ["proposition", visit(value.node_ref)]
    if isinstance(value, UnresolvedValue):
        return ["unresolved", value.unresolved_ref]
    raise TypeError("unknown filler")


def _root_signatures(
    expression: SemanticExpression,
    refs: tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    nodes: dict[str, object] = {
        **{row.application_ref: row for row in expression.applications},
        **{row.scope_ref: row for row in expression.scope_operators},
        **{row.link_ref: row for row in expression.expression_links},
        **{row.binder_ref: row for row in expression.binders},
    }
    memo: dict[str, str] = {}
    visiting: set[str] = set()

    def visit(ref: str) -> str:
        if ref in memo:
            return memo[ref]
        if ref in visiting:
            raise ValueError("expression signature cycle")
        visiting.add(ref)
        node = nodes[ref]
        if isinstance(node, SemanticApplication):
            def binding(row: RoleBinding) -> Any:
                return [row.role_ref, _filler_material(row.filler, visit)]
            material = [
                "application",
                node.operator,
                node.predicate_ref,
                [binding(row) for row in node.roles],
                [binding(row) for row in node.qualifiers],
            ]
        elif isinstance(node, ScopeOperator):
            material = ["scope", node.operator_type, node.value_ref, visit(node.operand_ref)]
        elif isinstance(node, ExpressionLink):
            material = ["link", node.link_type, [visit(ref) for ref in node.operand_refs]]
        elif isinstance(node, VariableBinder):
            material = ["binder", visit(node.body_ref)]
        else:  # pragma: no cover
            raise TypeError("unknown expression node")
        visiting.remove(ref)
        signature = stable_ref("semantic_root_signature", material)
        memo[ref] = signature
        return signature

    return tuple(visit(ref) for ref in (expression.root_refs if refs is None else refs))


def _expression_match(contract: ExpectedCycleContract, cycle: CycleResult) -> bool:
    if contract.expression_relation is ExpressionRelation.NONE:
        return cycle.verification is not None
    meaning = None if cycle.verification is None else cycle.verification.selected_meaning
    if meaning is None:
        return False
    observed = set(_root_signatures(meaning.expression))
    expected_groups = [set(_root_signatures(row)) for row in contract.expected_expressions]
    flattened = set().union(*expected_groups) if expected_groups else set()
    relation = contract.expression_relation
    if relation is ExpressionRelation.SINGLE:
        return len(expected_groups) == 1 and observed == expected_groups[0]
    if relation is ExpressionRelation.ALL:
        return flattened <= observed
    if relation is ExpressionRelation.ANY:
        return any(group <= observed or bool(group & observed) for group in expected_groups)
    if relation is ExpressionRelation.CONFLICT:
        observed_applications = set(
            _root_signatures(
                meaning.expression,
                tuple(row.application_ref for row in meaning.expression.applications),
            )
        )
        return flattened <= observed_applications
    if relation is ExpressionRelation.ORDERED_CHAIN:
        expected_order = [sig for group in expected_groups for sig in sorted(group)]
        return all(sig in observed for sig in expected_order)
    return False


def _constraint_match(constraints: Mapping[str, Any], situation: Any) -> bool:
    if situation is None:
        return not constraints
    aliases = {
        "participant_refs": "participant_refs",
        "source_refs": "source_refs",
        "permission_refs": "permission_refs",
        "resource_refs": "resource_refs",
        "adapter_refs": "adapter_refs",
        "policy_refs": "policy_refs",
        "evidence_policy_refs": "evidence_policy_refs",
        "focus_refs": "focus_refs",
        "obligation_refs": "obligation_refs",
        "temporal_frame_ref": "temporal_frame_ref",
        "session_phase": "session_phase",
        "trusted_observation": "trusted_observation",
    }
    for key, expected in constraints.items():
        attribute = aliases.get(key)
        if attribute is None:
            continue
        actual = getattr(situation, attribute, None)
        if isinstance(expected, (list, tuple)):
            if not set(expected) <= set(actual or ()):
                return False
        elif actual != expected:
            return False
    return True


def _decision_match(contract: ExpectedCycleContract, decision: Decision | None) -> bool:
    expected = contract.expected_decision
    if decision is None:
        return contract.outcome_kind in {
            ExpectedOutcomeKind.GAP,
            ExpectedOutcomeKind.VERIFICATION_REJECTION,
            ExpectedOutcomeKind.RESTART,
        }
    return (
        decision.status is expected.status
        and decision.action is expected.action
        and set(expected.binding_constraints) <= set(decision.bindings)
        and set(expected.required_proof_refs) <= set(decision.proof_refs)
        and set(expected.required_policy_refs) <= set(decision.policy_refs)
        and set(expected.blocker_refs) <= set(decision.blocker_refs)
    )


def _effect_match(contract: ExpectedCycleContract, effect: object | None) -> bool:
    expected = contract.expected_effect
    if effect is None and contract.outcome_kind in {
        ExpectedOutcomeKind.GAP,
        ExpectedOutcomeKind.VERIFICATION_REJECTION,
        ExpectedOutcomeKind.RESTART,
    }:
        return expected.kind is ExpectedEffectKind.NO_EFFECT
    if expected.kind is ExpectedEffectKind.EFFECT:
        if type(effect) is not EffectReceipt:
            return False
        adapter = getattr(effect, "adapter_ref", None)
        fact_refs = tuple(getattr(effect, "committed_fact_refs", ()))
        return (
            effect.status.value == expected.status_or_reason
            and set(expected.expected_fact_refs) <= set(fact_refs)
            and (
                expected.required_adapter_ref is None
                or adapter == expected.required_adapter_ref
            )
        )
    return (
        type(effect) is NoEffectReceipt
        and effect.reason.value == expected.status_or_reason
    )


def _response_match(contract: ExpectedCycleContract, response: object | None) -> bool:
    expected = contract.expected_response
    if response is None:
        return contract.outcome_kind in {
            ExpectedOutcomeKind.GAP,
            ExpectedOutcomeKind.VERIFICATION_REJECTION,
            ExpectedOutcomeKind.RESTART,
        }
    return (
        response.discourse_action == expected.discourse_action
        and response.cycle_status is expected.cycle_status
        and response.polarity_ref == expected.polarity_ref
        and response.modality_ref == expected.modality_ref
        and response.epistemic_status_ref == expected.epistemic_status_ref
        and set(response.permitted_omissions) <= set(expected.permitted_omissions)
    )


def _gap_match(contract: ExpectedCycleContract, cycle: CycleResult) -> bool:
    if contract.outcome_kind is ExpectedOutcomeKind.RESTART:
        return cycle.gap_receipt is not None
    expected = contract.expected_gap
    if expected is None:
        # A successful R3 cycle must still end at the exact R5 owner boundary.
        gap = cycle.gap_receipt
        return gap is not None and gap.status == "later_owner_not_admitted"
    gap = cycle.gap_receipt
    if gap is None:
        return False
    return (
        gap.kind.value == expected.kind
        and gap.status == expected.status
        and gap.recommended_owner.value == expected.recommended_owner
        and gap.safe_response_action == expected.safe_response_action
        and (
            expected.error_code is None
            or expected.error_code in set(gap.blockers)
            or expected.error_code in set(gap.missing_contract_refs)
        )
    )


@dataclass(frozen=True, init=False)
class AuthenticEpisode:
    abi_version: int
    episode_ref: str
    expanded_case: ExpandedCase
    expected_contract: ExpectedCycleContract
    observed_cycle: CycleResult
    comparison: ComparisonReceipt
    environment_observation_refs: tuple[str, ...]
    training_source: str
    review_provenance_refs: tuple[str, ...]
    generator_lineage_refs: tuple[str, ...]

    _FIELDS = frozenset(
        {
            "abi_version",
            "episode_ref",
            "expanded_case",
            "expected_contract",
            "observed_cycle",
            "comparison",
            "environment_observation_refs",
            "training_source",
            "review_provenance_refs",
            "generator_lineage_refs",
        }
    )

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("use AuthenticEpisode.create")

    @classmethod
    def create(
        cls,
        *,
        expanded_case: ExpandedCase,
        observed_cycle: CycleResult,
        comparison: ComparisonReceipt,
        environment_observation_refs: tuple[str, ...],
        training_source: str,
        review_provenance_refs: tuple[str, ...],
        generator_lineage_refs: tuple[str, ...],
    ) -> "AuthenticEpisode":
        if type(expanded_case) is not ExpandedCase:
            raise TypeError("expanded_case must be exact ExpandedCase")
        if type(observed_cycle) is not CycleResult:
            raise TypeError("observed_cycle must be exact CycleResult")
        if type(comparison) is not ComparisonReceipt:
            raise TypeError("comparison must be exact ComparisonReceipt")
        contract = expanded_case.contract
        if comparison.expected_contract_ref != contract.contract_ref:
            raise ValueError("comparison does not bind expected contract")
        if comparison.observed_cycle_ref != observed_cycle.cycle_ref:
            raise ValueError("comparison does not bind observed cycle")
        values = {
            "expanded_case": expanded_case,
            "expected_contract": contract,
            "observed_cycle": observed_cycle,
            "comparison": comparison,
            "environment_observation_refs": exact_refs(
                environment_observation_refs, "environment_observation_refs"
            ),
            "training_source": exact_text(training_source, "training_source"),
            "review_provenance_refs": exact_refs(
                review_provenance_refs,
                "review_provenance_refs",
                nonempty=True,
            ),
            "generator_lineage_refs": exact_refs(
                generator_lineage_refs,
                "generator_lineage_refs",
                nonempty=True,
            ),
        }
        material = {
            "abi_version": AUTHENTIC_EPISODE_ABI_VERSION,
            "expanded_case": expanded_case.as_dict(),
            "expected_contract": contract.as_dict(),
            "observed_cycle": observed_cycle.as_dict(),
            "comparison": comparison.as_dict(),
            "environment_observation_refs": list(values["environment_observation_refs"]),
            "training_source": values["training_source"],
            "review_provenance_refs": list(values["review_provenance_refs"]),
            "generator_lineage_refs": list(values["generator_lineage_refs"]),
        }
        obj = object.__new__(cls)
        object.__setattr__(obj, "abi_version", AUTHENTIC_EPISODE_ABI_VERSION)
        object.__setattr__(obj, "episode_ref", stable_ref("authentic_episode_v3", material))
        for name, value in values.items():
            object.__setattr__(obj, name, value)
        return obj

    def as_dict(self) -> dict[str, Any]:
        return {
            "abi_version": self.abi_version,
            "episode_ref": self.episode_ref,
            "expanded_case": self.expanded_case.as_dict(),
            "expected_contract": self.expected_contract.as_dict(),
            "observed_cycle": self.observed_cycle.as_dict(),
            "comparison": self.comparison.as_dict(),
            "environment_observation_refs": list(self.environment_observation_refs),
            "training_source": self.training_source,
            "review_provenance_refs": list(self.review_provenance_refs),
            "generator_lineage_refs": list(self.generator_lineage_refs),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AuthenticEpisode":
        row = exact_fields(value, cls._FIELDS, "AuthenticEpisode")
        if row["abi_version"] != AUTHENTIC_EPISODE_ABI_VERSION:
            raise ValueError("unsupported Authentic Episode ABI")
        rebuilt = cls.create(
            expanded_case=ExpandedCase.from_dict(row["expanded_case"]),
            observed_cycle=CycleResult.from_dict(row["observed_cycle"]),
            comparison=ComparisonReceipt.from_dict(row["comparison"]),
            environment_observation_refs=wire_refs(
                row["environment_observation_refs"],
                "environment_observation_refs",
            ),
            training_source=row["training_source"],
            review_provenance_refs=wire_refs(
                row["review_provenance_refs"],
                "review_provenance_refs",
                nonempty=True,
            ),
            generator_lineage_refs=wire_refs(
                row["generator_lineage_refs"],
                "generator_lineage_refs",
                nonempty=True,
            ),
        )
        if rebuilt.episode_ref != row["episode_ref"] or rebuilt.as_dict() != dict(row):
            raise ValueError("non-canonical AuthenticEpisode")
        return rebuilt


class AuthenticEpisodeBuilder:
    """Execute every expanded case and compare independent expectations."""

    def __init__(self, owner: EpisodeExecutionOwner) -> None:
        if not isinstance(owner, EpisodeExecutionOwner):
            raise TypeError("owner must implement EpisodeExecutionOwner")
        self._owner = owner

    @staticmethod
    def compare(
        case: ExpandedCase,
        execution: EpisodeExecutionResult,
    ) -> ComparisonReceipt:
        cycle = execution.cycle
        contract = case.contract
        situation = None if cycle.evaluation is None else cycle.evaluation.situation
        decision = None if cycle.evaluation is None else cycle.evaluation.decision
        expression = _expression_match(contract, cycle)
        situation_ok = (
            contract.expected_mode
            == (situation.mode if situation is not None else case.contract.expected_mode)
            and _constraint_match(contract.situation_constraints, situation)
        )
        decision_ok = _decision_match(contract, decision)
        effect_ok = _effect_match(contract, cycle.effect_receipt)
        response_ok = _response_match(contract, cycle.response_meaning)
        gap_ok = _gap_match(contract, cycle)
        expected_environment = thaw_json(case.environment).get(
            "required_observation_refs", []
        )
        if type(expected_environment) is not list:
            raise TypeError("required_observation_refs must be a list")
        environment_ok = set(expected_environment) <= set(
            execution.environment_observation_refs
        )
        flags = {
            "expression": expression,
            "situation": situation_ok,
            "decision": decision_ok,
            "effect": effect_ok,
            "response": response_ok,
            "gap": gap_ok,
            "environment": environment_ok,
        }
        return ComparisonReceipt.create(
            expected_contract_ref=contract.contract_ref,
            observed_cycle_ref=cycle.cycle_ref,
            expression_match=expression,
            situation_match=situation_ok,
            decision_match=decision_ok,
            effect_match=effect_ok,
            response_match=response_ok,
            gap_match=gap_ok,
            environment_match=environment_ok,
            mismatch_codes=tuple(
                f"comparison:{name}" for name, matched in flags.items() if not matched
            ),
        )

    def build(self, case: ExpandedCase) -> AuthenticEpisode:
        if type(case) is not ExpandedCase:
            raise TypeError("case must be exact ExpandedCase")
        session_ref = str(
            thaw_json(case.environment).get(
                "session_ref",
                stable_ref("r4_session", case.trajectory_ref),
            )
        )
        execution = self._owner.execute_case(case, session_ref=session_ref)
        if type(execution) is not EpisodeExecutionResult:
            raise TypeError("episode owner returned non-canonical execution result")
        comparison = self.compare(case, execution)
        return AuthenticEpisode.create(
            expanded_case=case,
            observed_cycle=execution.cycle,
            comparison=comparison,
            environment_observation_refs=execution.environment_observation_refs,
            training_source="externally_reviewed_expected_contract",
            review_provenance_refs=case.contract.review_provenance_refs,
            generator_lineage_refs=(
                case.case_ref,
                case.contract_ref,
                execution.cycle.cycle_ref,
                comparison.receipt_ref,
            ),
        )

    def build_many(
        self, cases: Iterable[ExpandedCase]
    ) -> tuple[AuthenticEpisode, ...]:
        rows = tuple(cases)
        if any(type(row) is not ExpandedCase for row in rows):
            raise TypeError("cases must contain ExpandedCase")
        ordered = tuple(
            sorted(
                rows,
                key=lambda row: (
                    row.trajectory_ref,
                    row.turn_index,
                    row.surface_index,
                    row.environment_index,
                    row.case_ref,
                ),
            )
        )
        return tuple(self.build(row) for row in ordered)
