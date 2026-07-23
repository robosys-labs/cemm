"""Canonical service implementation authority inventory for Phase 18.

Runtime *slot* identity and implementation-declared SERVICE_KIND are separate facts. This avoids
forcing canonical in-process classes to lie about their implementation kind merely to occupy a slot.
"""
from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
import inspect
from pathlib import Path

from .source_attestation_v351 import sha256_file


@dataclass(frozen=True, slots=True)
class CanonicalServiceAuthorityV351:
    service_kind: str
    class_path: str
    required_methods: tuple[str, ...]
    runtime_abi: str
    implementation_service_kind: str
    source_sha256: str

    def __post_init__(self) -> None:
        if not self.service_kind or ":" not in self.class_path or self.runtime_abi != "v351":
            raise ValueError("invalid canonical service authority")
        if not self.required_methods or len(self.required_methods) != len(set(self.required_methods)):
            raise ValueError("canonical service authority requires unique method ABI")
        if len(self.source_sha256) != 64:
            raise ValueError("canonical service authority requires exact source SHA256")


SERVICE_SPECS = (
    ("clock", "cemm.v350.runtime_support_v351:SystemUTCClockV351", ("now_iso",)),
    ("csir_compiler", "cemm.v350.composition:ProjectionAwareDeterministicCSIRComposer", ("compile",)),
    ("recurrent_semantic_solver", "cemm.v350.dynamics:RecurrentSemanticDynamicsV351", ("run",)),
    ("semantic_attractor_stabilizer", "cemm.v350.dynamics:RecurrentAttractorStabilizerV351", ("stabilize",)),
    ("discourse_structure_builder", "cemm.v350.discourse:DiscourseStructureBuilderV351", ("build",)),
    ("epistemic_coordinator", "cemm.v350.epistemic:EpistemicCoordinatorV351", ("place",)),
    ("query_engine", "cemm.v350.causal.query_v351:Phase16QueryEngineV351", ("query",)),
    ("learning_engine", "cemm.v350.learning.engine_v351:Phase14LearningEngineV351", ("advance",)),
    ("causal_simulator", "cemm.v350.causal.runtime_v351:Phase15CausalSimulatorV351", ("simulate",)),
    ("commit_coordinator", "cemm.v350.causal.commit_v351:CompositeStage13CommitterV351", ("commit",)),
    ("impact_engine", "cemm.v350.causal.runtime_v351:Phase16ImpactRuntimeV351", ("propagate",)),
    ("goal_engine", "cemm.v350.causal.runtime_v351:CompositeGoalArbitratorV351", ("arbitrate",)),
    ("operation_engine", "cemm.v350.causal.runtime_v351:CausalPlanningOperationEngineV351", ("prepare", "execute")),
    ("operation_outcome_assimilator", "cemm.v350.observation.operation_outcome_v351:CanonicalOperationOutcomeAssimilatorV351", ("assimilate",)),
    ("response_csir_builder", "cemm.v350.causal.response_v351:Phase16ResponseCSIRBuilderV351", ("build",)),
    ("realization_engine", "cemm.v350.realization.english_v351:EnglishCSIRRealizerV351", ("realize",)),
    ("emission_engine", "cemm.v350.output.runtime_v351:InProcessTextEmissionEngineV351", ("authorize", "emit")),
    ("output_discourse_engine", "cemm.v350.output.runtime_v351:OutputDiscourseCommitterV351", ("commit",)),
    ("consolidation_engine", "cemm.v350.finalization.runtime_v351:CanonicalCycleFinalizerV351", ("finalize",)),
)


def canonical_service_authorities_v351():
    result = []
    for slot, class_path, methods in SERVICE_SPECS:
        module_name, symbol = class_path.split(":", 1)
        cls = getattr(import_module(module_name), symbol)
        for method in methods:
            if not callable(getattr(cls, method, None)):
                raise TypeError(f"canonical service lacks required method:{slot}:{class_path}:{method}")
        runtime_abi = str(getattr(cls, "RUNTIME_ABI", "v351"))
        if runtime_abi != "v351":
            raise ValueError(f"canonical service lacks final v351 ABI:{slot}:{runtime_abi}")
        source_path = inspect.getsourcefile(cls)
        if not source_path or not Path(source_path).is_file():
            raise ValueError(f"cannot locate canonical service source:{class_path}")
        result.append(CanonicalServiceAuthorityV351(
            service_kind=slot,
            class_path=class_path,
            required_methods=tuple(methods),
            runtime_abi="v351",
            implementation_service_kind=str(getattr(cls, "SERVICE_KIND", slot)),
            source_sha256=sha256_file(Path(source_path)),
        ))
    return tuple(result)


__all__ = ["CanonicalServiceAuthorityV351", "SERVICE_SPECS", "canonical_service_authorities_v351"]
