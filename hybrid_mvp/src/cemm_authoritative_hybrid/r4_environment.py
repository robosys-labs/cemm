"""Authentic execution owners for deterministic R4 artifact construction."""
from __future__ import annotations

from pathlib import Path
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
from .proposal import BootstrapProposer
from .r3_codec import thaw_json
from .r4_contracts import ExpectedOutcomeKind
from .r4_episodes import EpisodeExecutionResult
from .r4_expansion import ExpandedCase
from .r4_mutations import MutationBoundaryResult, SemanticMutation

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
            if "role" in detail:
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


def build_environment(
    project_root: Path, output_root: Path
) -> Mapping[str, object]:
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
        )
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
        "source_revision": admitted_source_for_phase(root, "R3"),
        "close": close,
    }
