"""CommitCoordinator backed by an actual semantic mutation store."""
from __future__ import annotations
from dataclasses import dataclass
from ..model.execution import TypedFailure
from ..model.mutation import (
    CommitOperationResult, CommitOutcome, MutationSet,
)
from ..memory.semantic import (
    MutationPayloadRegistry, SemanticFact,
    SemanticMemoryStore,
)

@dataclass(frozen=True, slots=True)
class ValidationResult:
    is_valid: bool
    failures: tuple[TypedFailure, ...] = ()
    required_operations: tuple[str, ...] = ()
    auxiliary_operations: tuple[str, ...] = ()

class WriteContractGuard:
    def check_write_contract(self, mutation_set):
        required = tuple(
            operation.id
            for operation in mutation_set.operations
            if operation.required
        )
        auxiliary = tuple(
            operation.id
            for operation in mutation_set.operations
            if not operation.required
        )
        failures = ()
        if (
            mutation_set.phase == "critical"
            and mutation_set.operations
            and not required
        ):
            failures = (TypedFailure(
                failure_kind="no_required_writes",
                detail=(
                    "critical mutation set has no exact "
                    "required operation"
                ),
            ),)
        return ValidationResult(
            is_valid=not failures,
            failures=failures,
            required_operations=required,
            auxiliary_operations=auxiliary,
        )

    @staticmethod
    def check_identity_match(
        operation, requested_identity
    ):
        if requested_identity is None:
            return True
        return (
            operation.semantic_identity is not None
            and operation.semantic_identity.identity_kind
            == requested_identity.identity_kind
            and operation.semantic_identity.key
            == requested_identity.key
        )

    @staticmethod
    def check_completion(mutation_set, outcome):
        required = {
            operation.id
            for operation in mutation_set.operations
            if operation.required
        }
        committed = {
            result.mutation_ref
            for result in outcome.results
            if result.status == "committed"
        }
        missing = required - committed
        return (
            not missing,
            "" if not missing
            else f"required operations not committed: "
            f"{sorted(missing)}",
        )

class CommitCoordinator:
    def __init__(
        self,
        store: SemanticMemoryStore,
        payload_registry: MutationPayloadRegistry,
    ):
        self._store = store
        self._payloads = payload_registry
        self._write_guard = WriteContractGuard()

    @property
    def write_guard(self):
        return self._write_guard

    def validate(self, mutation_set):
        failures, required, auxiliary = [], [], []
        for operation in mutation_set.operations:
            (
                required if operation.required else auxiliary
            ).append(operation.id)
            if not operation.payload_ref:
                failures.append(TypedFailure(
                    failure_kind="missing_payload",
                    detail=(
                        f"{operation.id} has no payload ref"
                    ),
                ))
            elif self._payloads.get(
                operation.payload_ref
            ) is None:
                failures.append(TypedFailure(
                    failure_kind="unresolved_payload",
                    detail=(
                        f"{operation.id} payload is not "
                        "registered"
                    ),
                ))
            if (
                operation.required
                and not operation.evidence_refs
            ):
                failures.append(TypedFailure(
                    failure_kind="insufficient_evidence",
                    detail=(
                        f"{operation.id} has no evidence refs"
                    ),
                ))
        contract = self._write_guard.check_write_contract(
            mutation_set
        )
        failures.extend(contract.failures)
        return ValidationResult(
            is_valid=not failures,
            failures=tuple(failures),
            required_operations=tuple(required),
            auxiliary_operations=tuple(auxiliary),
        )

    def commit(self, mutation_set):
        validation = self.validate(mutation_set)
        if not validation.is_valid:
            return CommitOutcome(
                mutation_set_ref=mutation_set.id,
                results=tuple(
                    CommitOperationResult(
                        mutation_ref=operation.id,
                        status="failed",
                        failure=TypedFailure(
                            failure_kind="validation_failed",
                            detail="; ".join(
                                failure.detail
                                for failure in validation.failures
                            ),
                        ),
                    )
                    for operation in mutation_set.operations
                ),
                required_satisfied=False,
                committed_revision=None,
            )
        results = []
        try:
            with self._store.transaction():
                for operation in mutation_set.operations:
                    payload = self._payloads.get(
                        operation.payload_ref
                    )
                    if (
                        operation.operation_kind
                        == "semantic_fact"
                        and isinstance(payload, SemanticFact)
                    ):
                        ref, _ = self._store.add(payload)
                        results.append(
                            CommitOperationResult(
                                mutation_ref=operation.id,
                                status="committed",
                                record_refs=(ref,),
                            )
                        )
                    elif operation.action == "supersede":
                        if not self._store.supersede(
                            str(payload)
                        ):
                            raise ValueError(
                                f"cannot supersede {payload!r}"
                            )
                        results.append(
                            CommitOperationResult(
                                mutation_ref=operation.id,
                                status="committed",
                                record_refs=(str(payload),),
                            )
                        )
                    else:
                        raise TypeError(
                            "unsupported mutation "
                            f"{operation.operation_kind}/"
                            f"{type(payload).__name__}"
                        )
        except Exception as exc:
            return CommitOutcome(
                mutation_set_ref=mutation_set.id,
                results=tuple(
                    CommitOperationResult(
                        mutation_ref=operation.id,
                        status="failed",
                        failure=TypedFailure(
                            failure_kind="atomic_rollback",
                            detail=str(exc),
                        ),
                    )
                    for operation in mutation_set.operations
                ),
                required_satisfied=False,
                committed_revision=None,
            )
        required = {
            operation.id
            for operation in mutation_set.operations
            if operation.required
        }
        committed = {
            result.mutation_ref
            for result in results
            if result.status == "committed"
        }
        return CommitOutcome(
            mutation_set_ref=mutation_set.id,
            results=tuple(results),
            required_satisfied=required <= committed,
            committed_revision=self._store.revision,
        )

    def check_completion(self, mutation_set, outcome):
        return self._write_guard.check_completion(
            mutation_set, outcome
        )
