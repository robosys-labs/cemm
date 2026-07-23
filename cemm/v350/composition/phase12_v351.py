"""Phase-12 hardening wrapper for deterministic exact composition.

Phase-10 local grounding selection is only a soft prior.  This wrapper preserves bounded
coherent grounding alternatives through CSIR composition and makes referent/state
projection participate in branch admissibility instead of being ignored.
"""
from __future__ import annotations

from dataclasses import replace
from math import tanh

from ..csir.canonical_v351 import semantic_fingerprint
from ..runtime_abi import GroundingCandidateSet
from .deterministic_v351 import DeterministicCSIRComposer
from .model import CompositionFrontier


class ProjectionAwareDeterministicCSIRComposer(DeterministicCSIRComposer):
    RUNTIME_ABI = "v351"
    SERVICE_KIND = "csir_compiler"

    def __init__(self, *args, maximum_grounding_assignments: int = 32, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if maximum_grounding_assignments < 1:
            raise ValueError("grounding assignment budget must be positive")
        self.maximum_grounding_assignments = maximum_grounding_assignments

    @staticmethod
    def _projection_frontiers(mapping, referent_projections, state_space_projections):
        frontiers = []
        for _mention_ref, target_ref in mapping:
            if target_ref not in referent_projections:
                frontiers.append(CompositionFrontier(
                    frontier_ref=f"frontier:composition:referent-projection-missing:{target_ref}",
                    missing_contract="referent/type projection for grounded target",
                    source_refs=(target_ref,), effects=("partial_response", "learning"),
                ))
                continue
            # State-space projection is entitled evidence, not an active state assertion.
            # Presence/absence participates in branch completeness only; no default value is
            # invented when a referent has no entitled state dimensions.
            if target_ref not in state_space_projections:
                frontiers.append(CompositionFrontier(
                    frontier_ref=f"frontier:composition:state-projection-unavailable:{target_ref}",
                    missing_contract="explicit entitled state-space projection or declared no-state entitlement",
                    source_refs=(target_ref,), effects=("learning",),
                ))
        return tuple(frontiers)

    def compile(self, **kwargs):
        grounding = kwargs.get("grounding_candidates")
        referent_projections = kwargs.get("referent_projections") or {}
        state_space_projections = kwargs.get("state_space_projections") or {}
        if not isinstance(grounding, GroundingCandidateSet):
            return super().compile(**kwargs)
        result = getattr(grounding, "result", None)
        if result is None or not tuple(getattr(result, "assignments", ()) or ()):
            return super().compile(**kwargs)

        # Highest-scoring assignments are explored first, but no local selected assignment
        # receives authority.  Every retained coherent branch reaches canonical CSIR classes.
        assignments = tuple(sorted(
            result.assignments,
            key=lambda item: (-float(item.score), item.assignment_ref),
        ))[: self.maximum_grounding_assignments]
        fragments = []
        frontiers = []
        seen_assignment_refs = set()
        for assignment in assignments:
            if assignment.assignment_ref in seen_assignment_refs:
                continue
            seen_assignment_refs.add(assignment.assignment_ref)
            projection_frontiers = self._projection_frontiers(
                assignment.mention_to_target, referent_projections, state_space_projections,
            )
            # Missing referent projection is a hard branch blocker. Missing state projection
            # remains a learning/partial frontier because not every type is state-entitled.
            if any("referent-projection-missing" in item.frontier_ref for item in projection_frontiers):
                frontiers.extend(projection_frontiers)
                continue
            frontiers.extend(projection_frontiers)
            branch_result = replace(result, selected_assignment_ref=assignment.assignment_ref)
            branch_grounding = replace(grounding, result=branch_result)
            branch_kwargs = dict(kwargs)
            branch_kwargs["grounding_candidates"] = branch_grounding
            compiled = super().compile(**branch_kwargs)
            prior_adjustment = tanh(float(assignment.score) / 10.0)
            for fragment in tuple(compiled.get("candidate_fragments", ()) or ()):
                fragments.append(replace(
                    fragment,
                    fragment_ref=f"{fragment.fragment_ref}:grounding:{assignment.assignment_ref}",
                    evidence_refs=tuple(sorted(set((*fragment.evidence_refs, *assignment.factor_refs)))),
                    prior_score=float(fragment.prior_score) + prior_adjustment,
                ))
            frontiers.extend(tuple(compiled.get("composition_frontiers", ()) or ()))

        # Keep derivations distinct here. ExactCSIRCompiler performs the authoritative
        # canonical semantic-class collapse while retaining one valid exact lineage.
        return {
            "candidate_fragments": tuple(fragments),
            "composition_frontiers": tuple(frontiers),
        }


__all__ = ["ProjectionAwareDeterministicCSIRComposer"]
