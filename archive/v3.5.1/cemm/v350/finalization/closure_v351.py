"""Fail-closed Phase-18 release closure ledger."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class GateStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    NOT_RUN = "not_run"


REQUIRED_PHASE18_GATES = (
    "csir_compilation",
    "stage_0_22_runtime",
    "english_conversational_kernel",
    "learning_promotion_restart",
    "recurrent_solver_calibrated",
    "causal_state_proof_replay",
    "pinned_runtime_roots",
    "authority_snapshot_restart_projection",
    "no_floating_authority",
    "no_legacy_runtime_authority",
    "shadow_equivalence",
    "multimodal_grounding",
    "cross_language_equivalence",
    "operation_result_recurrence",
    "active_knowledge_acquisition",
    "concurrency",
    "performance_storage",
    "deterministic_release_artifacts",
    "signed_release_authority",
)


@dataclass(frozen=True, slots=True)
class ClosureGateResultV351:
    gate: str
    status: GateStatus
    evidence_sha256: str = ""
    evidence_path: str = ""
    reason: str = ""

    def __post_init__(self) -> None:
        if self.gate not in REQUIRED_PHASE18_GATES:
            raise ValueError(f"unknown Phase-18 closure gate:{self.gate}")
        if self.status is GateStatus.PASS and (len(self.evidence_sha256) != 64 or not self.evidence_path):
            raise ValueError(f"passing gate requires exact evidence artifact:{self.gate}")


@dataclass(frozen=True, slots=True)
class Phase18ClosureLedgerV351:
    release_commit: str
    authority_payload_sha256: str
    boot_database_sha256: str
    runtime_source_root_sha256: str
    gates: tuple[ClosureGateResultV351, ...]

    def __post_init__(self) -> None:
        if len(self.release_commit) != 40:
            raise ValueError("closure ledger requires exact git commit")
        for value, label in (
            (self.authority_payload_sha256, "authority payload"),
            (self.boot_database_sha256, "boot database"),
            (self.runtime_source_root_sha256, "runtime source root"),
        ):
            if len(value) != 64:
                raise ValueError(f"closure ledger requires 64-hex {label} hash")
        observed = [item.gate for item in self.gates]
        if len(observed) != len(set(observed)):
            raise ValueError("duplicate closure gates")

    @property
    def by_gate(self) -> Mapping[str, ClosureGateResultV351]:
        return {item.gate: item for item in self.gates}

    @property
    def complete(self) -> bool:
        values = self.by_gate
        return all(values.get(gate) is not None and values[gate].status is GateStatus.PASS for gate in REQUIRED_PHASE18_GATES)

    @property
    def missing_or_failed(self) -> tuple[str, ...]:
        values = self.by_gate
        return tuple(
            gate for gate in REQUIRED_PHASE18_GATES
            if values.get(gate) is None or values[gate].status is not GateStatus.PASS
        )


__all__ = [
    "ClosureGateResultV351", "GateStatus", "Phase18ClosureLedgerV351", "REQUIRED_PHASE18_GATES",
]
