"""Authentic execution owners for deterministic R4 artifact construction."""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Mapping

from .authority import AuthorityLinker
from .bootstrap import load_runtime
from .canonical import stable_ref
from .config import RuntimeConfig
from .governance import (
    effective_replay_status,
    read_hash_chain,
    verify_file_invalidation,
)
from .persistence import RevisionPin
from .r3_persistence import install_reviewed_world_facts
from .proposal import BootstrapProposer
from .r3_codec import thaw_json
from .r4_contracts import ExpectedOutcomeKind
from .r4_episodes import EpisodeExecutionResult
from .r4_expansion import ExpandedCase
from .r4_mutations import MutationBoundaryResult, SemanticMutation
from .r3_effects import (
    AdapterRegistry,
    AdapterResult,
    AdapterStatus,
    EffectRequest,
    ObservedDelta,
)

__all__ = [
    "AuthenticMutationOwner",
    "AuthenticRestartExecutor",
    "admitted_source_for_phase",
    "build_environment",
]


def admitted_source_for_phase(project_root: Path, phase: str) -> str:
    """Return the exact source of the effective green admission for ``phase``."""
    root = Path(project_root).resolve()
    if type(phase) is not str or not phase:
        raise TypeError("phase must be exact nonempty str")
    status_records = read_hash_chain(root / "governance" / "replay_status.jsonl")
    invalidations = read_hash_chain(
        root / "governance" / "receipt_invalidations.jsonl"
    )
    for invalidation in invalidations:
        verify_file_invalidation(root, invalidation)
    effective = effective_replay_status(status_records)
    if effective.get(phase) != "green":
        raise ValueError(f"phase does not have an effective green admission: {phase}")
    admitted = next(
        (
            row
            for row in reversed(status_records)
            if row.get("phase") == phase and row.get("status") == "green"
        ),
        None,
    )
    if admitted is None:
        raise ValueError(f"phase has no green admission record: {phase}")
    invalidated_refs = {
        str(value)
        for row in invalidations
        for key, value in row.items()
        if "invalidat" in key or key.endswith("_ref")
        if isinstance(value, str)
    }
    protected_refs = {
        str(admitted.get("record_ref")),
        str(admitted.get("admission_gate_result_ref")),
        str(admitted.get("admission_run_ref")),
    }
    if invalidated_refs & protected_refs:
        raise ValueError(f"phase admission is invalidated: {phase}")
    source = admitted.get("source_base")
    if type(source) is not str or len(source) not in {40, 64}:
        raise ValueError(f"phase admission source is malformed: {phase}")
    return source


class AuthenticRestartExecutor:
    """Reopen the exact SQLite store before executing restart evidence."""

    def __init__(self, project_root: Path, output_root: Path) -> None:
        self._project_root = Path(project_root).resolve()
        self._output_root = Path(output_root).resolve() / "r"
        self._output_root.mkdir(parents=True, exist_ok=True)

    def execute_restart_case(
        self, case: ExpandedCase, *, session_ref: str
    ) -> EpisodeExecutionResult:
        if type(case) is not ExpandedCase:
            raise TypeError("restart case must be exact ExpandedCase")
        if case.contract.outcome_kind is not ExpectedOutcomeKind.RESTART:
            raise ValueError("restart executor requires a restart contract")
        if type(session_ref) is not str or not session_ref:
            raise TypeError("session_ref must be exact nonempty str")
        store_path = self._output_root / stable_ref(
            "r4_restart_store", case.case_ref
        ).split(":", 1)[1]
        original = load_runtime(
            self._project_root,
            profile="development",
            store_path=store_path,
        )
        original.stores.close()
        reopened = load_runtime(
            self._project_root,
            profile="development",
            store_path=store_path,
        )
        try:
            evidence = reopened.create_evidence(session_ref, case.surface)
            cycle = reopened.process_evidence(session_ref, evidence, trace=True)
            return EpisodeExecutionResult(cycle, ())
        finally:
            reopened.stores.close()


class AuthenticMutationOwner:
    """Execute each altered payload at its typed earliest boundary."""

    def __init__(self, project_root: Path, output_root: Path) -> None:
        self._project_root = Path(project_root).resolve()
        self._output_root = Path(output_root).resolve() / "mutation-stores"
        self._output_root.mkdir(parents=True, exist_ok=True)
        self._authority = AuthorityLinker().link_path(
            self._project_root / "data" / "authority" / "manifest.json"
        )
        state_owner = load_runtime(
            self._project_root,
            profile="development",
            store_path=self._output_root / "owner-state",
        )
        try:
            self._world_revision = state_owner.stores.revision_pin().world_revision
        finally:
            state_owner.stores.close()

    @staticmethod
    def _result(
        mutation: SemanticMutation,
        *,
        owner: str,
        status: str,
        code: str,
        evidence: object,
    ) -> MutationBoundaryResult:
        return MutationBoundaryResult(
            earliest_owner=owner,
            status=status,
            error_code=code,
            artifact_ref=stable_ref(
                "r4_mutation_boundary",
                {
                    "mutation_ref": mutation.mutation_ref,
                    "owner": owner,
                    "status": status,
                    "code": code,
                    "evidence": str(evidence),
                },
            ),
        )

    def execute_mutation(self, mutation: SemanticMutation) -> MutationBoundaryResult:
        if type(mutation) is not SemanticMutation:
            raise TypeError("mutation must be exact SemanticMutation")
        payload = thaw_json(mutation.mutated_case)
        if not isinstance(payload, dict):
            raise TypeError("mutated case must decode to exact dict")

        contract = payload.get("contract")
        if isinstance(contract, Mapping):
            expressions = contract.get("expected_expressions", ())
            if isinstance(expressions, list):
                for expression in expressions:
                    if not isinstance(expression, Mapping):
                        continue
                    applications = expression.get("applications", ())
                    if not isinstance(applications, list):
                        continue
                    for application in applications:
                        if not isinstance(application, Mapping):
                            continue
                        predicate_ref = application.get("predicate_ref")
                        if (
                            isinstance(predicate_ref, str)
                            and predicate_ref not in self._authority.atoms
                        ):
                            return self._result(
                                mutation,
                                owner="expected-contract-compiler",
                                status="rejected",
                                code="authority_ref_missing",
                                evidence=predicate_ref,
                            )
            revision_pin = contract.get("revision_pin")
            if isinstance(revision_pin, Mapping):
                world_revision = revision_pin.get("world_revision")
                if (
                    type(world_revision) is int
                    and world_revision != self._world_revision
                ):
                    return self._result(
                        mutation,
                        owner="EFFECT",
                        status="stale_revision",
                        code="stale_revision",
                        evidence={
                            "observed": self._world_revision,
                            "requested": world_revision,
                        },
                    )
        try:
            case = ExpandedCase.from_dict(payload)
        except (TypeError, ValueError) as exc:
            detail = str(exc).lower()
            if mutation.dimension == "decision_action_mismatch":
                code = "decision_contract_mismatch"
            elif "role" in detail:
                code = "invalid_role_ref"
            elif "root" in detail:
                code = "unknown_root_ref"
            elif "decision" in detail or "action" in detail:
                code = "decision_contract_mismatch"
            else:
                code = "contract_decode_rejected"
            return self._result(
                mutation,
                owner=(
                    "semantic-expression"
                    if code == "unknown_root_ref"
                    else "expected-contract-compiler"
                ),
                status="rejected",
                code=code,
                evidence=detail,
            )

        for expression in case.contract.expected_expressions:
            for application in expression.applications:
                if application.predicate_ref not in self._authority.atoms:
                    return self._result(
                        mutation,
                        owner="expected-contract-compiler",
                        status="rejected",
                        code="authority_ref_missing",
                        evidence=application.predicate_ref,
                    )
        constraints = payload.get("environment", {}).get(
            "situation_constraints", {}
        )
        if isinstance(constraints, Mapping):
            if constraints.get("permission_refs") == []:
                return self._result(
                    mutation,
                    owner="EVALUATE",
                    status="denied",
                    code="permission_missing",
                    evidence=constraints,
                )
            if constraints.get("adapter_refs") == []:
                return self._result(
                    mutation,
                    owner="EVALUATE",
                    status="adapter_missing",
                    code="adapter_missing",
                    evidence=constraints,
                )
            if constraints.get("trusted_observation") is False:
                return self._result(
                    mutation,
                    owner="EVALUATE",
                    status="contested",
                    code="untrusted_observation",
                    evidence=constraints,
                )
        if case.contract.revision_pin.world_revision != self._world_revision:
            return self._result(
                mutation,
                owner="EFFECT",
                status="stale_revision",
                code="stale_revision",
                evidence=case.contract.revision_pin.world_revision,
            )
        return self._result(
            mutation,
            owner="expected-contract-compiler",
            status="rejected",
            code="decision_contract_mismatch",
            evidence=case.contract.expected_decision.as_dict(),
        )


class _ReviewedStateAdapter:
    """Return the exact reviewed state delta carried by an EffectRequest."""

    @staticmethod
    def _result(request: EffectRequest) -> AdapterResult:
        observed = tuple(
            ObservedDelta.create(
                operator_ref=row.operator_ref,
                predicate_ref=row.predicate_ref,
                role_values=row.role_values,
                stance=row.stance,
                evidence_refs=(request.request_ref,),
            )
            for row in request.expected_deltas
        )
        return AdapterResult.create(
            adapter_ref=request.adapter_ref,
            status=AdapterStatus.SUCCEEDED,
            idempotency_key=request.idempotency_key,
            request_ref=request.request_ref,
            event_type_ref=request.event_type_ref,
            target_ref=request.target_ref,
            transition_ref=request.transition_ref,
            observed_deltas=observed,
            blocker_refs=(),
            operation_receipt_ref=stable_ref(
                "r4_reviewed_state_operation", request.request_ref
            ),
        )

    def invoke(self, request: EffectRequest) -> AdapterResult:
        return self._result(request)

    def reconcile(self, request: EffectRequest) -> AdapterResult:
        return self._result(request)


def _seed_reviewed_world(runtime: Any, case: ExpandedCase) -> None:
    environment = thaw_json(case.environment)
    rows = environment.get("world_facts", [])
    if type(rows) is not list:
        raise TypeError("R4 environment world_facts must be a list")
    if not rows:
        return
    from .persistence import Fact

    facts: list[Fact] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise TypeError("R4 environment world fact must be a mapping")
        roles = row.get("roles")
        if not isinstance(roles, Mapping):
            raise TypeError("R4 environment world fact roles must be a mapping")
        predicate = row.get("predicate_ref")
        operator = row.get("operator")
        source = row.get("source_ref")
        stance = row.get("stance", "support")
        if any(type(value) is not str or not value for value in (predicate, operator, source, stance)):
            raise ValueError("R4 environment world fact has incomplete reviewed fields")
        facts.append(
            Fact(
                fact_ref=stable_ref(
                    "r4_reviewed_world_fact",
                    {"case_ref": case.case_ref, "index": index, "row": dict(row)},
                ),
                operator=operator,
                args={**{str(key): str(value) for key, value in roles.items()}, "predicate_ref": predicate},
                stance=stance,
                confidence=1.0,
                derived=False,
                proof={"source": source, "source_refs": [source]},
            )
        )
    install_reviewed_world_facts(runtime.stores, facts=tuple(facts))


def build_environment(
    project_root: Path,
    output_root: Path,
    *,
    source_revision: str,
) -> Mapping[str, object]:
    if type(source_revision) is not str or re.fullmatch(r"[0-9a-f]{40}", source_revision) is None:
        raise ValueError("source_revision must be exact 40-character lowercase hex")
    root = Path(project_root).resolve()
    output = Path(output_root).resolve()
    output.mkdir(parents=True, exist_ok=True)
    authority = AuthorityLinker().link_path(
        root / "data" / "authority" / "manifest.json"
    )
    model_identity = BootstrapProposer(RuntimeConfig.release()).model_identity
    pin = RevisionPin(authority.generation, 0, 0, 0, 0, model_identity)
    runtime_index = 0
    runtimes: list[Any] = []

    def runtime_factory(_case: ExpandedCase) -> Any:
        nonlocal runtime_index
        path = output / "episode-stores" / f"runtime-{runtime_index:04d}"
        runtime_index += 1
        runtime = load_runtime(
            root,
            profile="development",
            store_path=path,
            adapters=AdapterRegistry({"adapter:state": _ReviewedStateAdapter()}),
        )
        _seed_reviewed_world(runtime, _case)
        runtimes.append(runtime)
        return runtime

    def close() -> None:
        while runtimes:
            runtimes.pop().stores.close()

    return {
        "authority": authority,
        "revision_pin": pin,
        "abi_registry_ref": "abi:r4-authentic-build-environment",
        "runtime_factory": runtime_factory,
        "restart_executor": AuthenticRestartExecutor(root, output),
        "mutation_owner": AuthenticMutationOwner(root, output),
        "source_revision": source_revision,
        "close": close,
    }
