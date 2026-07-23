"""Canonical Stage-22 consolidation/invalidation/replay/finalization."""
from __future__ import annotations

from ..cycle_control import CompletionEvaluator
from ..orchestration import StageExecutionStatus, StageOutcome
from ..runtime_abi import artifact_ref


class CanonicalCycleFinalizerV351:
    RUNTIME_ABI = "v351"
    SERVICE_KIND = "consolidation_engine"

    def finalize(self, *, cycle, capability, store, effect_store, semantic_capabilities):
        del store, effect_store, semantic_capabilities
        frontiers = tuple(sorted(set(cycle.frontiers)))
        replay = tuple(sorted(set(
            ref for ref in frontiers
            if "temporal_replay" in ref or "replay" in ref or "generation" in ref
        )))
        invalidations = tuple(sorted(set(cycle.artifacts.get("_invalidation_refs", ()) or ())))
        status = CompletionEvaluator().evaluate(cycle).value
        if replay or invalidations:
            # Explicit replay/invalidation can never be mislabeled a completed success.
            status = "PARTIAL"
        consolidation_results = ({
            "consolidation_ref": artifact_ref("cycle-consolidation", cycle.cycle_ref, capability.pass_ref),
            "status": status,
            "frontier_count": len(frontiers),
            "replay_count": len(replay),
            "invalidation_count": len(invalidations),
        },)
        summary = {
            "cycle_ref": cycle.cycle_ref,
            "pass_ref": capability.pass_ref,
            "authority_generation": capability.authority_generation,
            "authority_fingerprint": capability.authority_fingerprint,
            "frontier_refs": frontiers,
            "errors": tuple(cycle.errors),
            "reentry_count": int(cycle.reentry_count),
            "completion_status": status,
        }
        return StageOutcome(
            StageExecutionStatus.PERFORMED,
            artifacts={
                "cycle_completion_status": status,
                "invalidation_set": invalidations,
                "replay_requirements": replay,
                "consolidation_results": consolidation_results,
                "final_cycle_summary": summary,
            },
            frontier_refs=replay,
        )


__all__ = ["CanonicalCycleFinalizerV351"]
