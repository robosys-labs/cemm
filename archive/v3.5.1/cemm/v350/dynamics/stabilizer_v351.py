"""Phase-13 semantic attractor stabilization over recurrent activation classes."""
from __future__ import annotations

import math

from ..csir.model import CSIRNodeKind, CSIRRef
from ..runtime_abi import (
    ActivationGraph, ActivationTrace, ConvergenceAssessment, SemanticAttractor,
    SemanticAttractorSet, artifact_ref,
)
from .model_v351 import ActivationNodeKind, ConvergenceKind, TypedActivationPayload


class RecurrentAttractorStabilizerV351:
    RUNTIME_ABI = 'v351'
    SERVICE_KIND = 'semantic_attractor_stabilizer'
    def stabilize(
        self,
        *,
        activation_graph: ActivationGraph,
        activation_trace: ActivationTrace,
        authority_snapshot,
        semantic_authority_snapshot_v351,
        budgets,
        **_ignored,
    ) -> SemanticAttractorSet:
        payload = activation_graph.payload
        if not isinstance(payload, TypedActivationPayload):
            raise TypeError("Phase-13 stabilizer requires TypedActivationPayload")
        if activation_graph.semantic_authority_snapshot_fingerprint != semantic_authority_snapshot_v351.snapshot_fingerprint:
            raise ValueError("activation graph authority snapshot changed before stabilization")

        status = self._status(activation_trace)
        params = payload.parameter_set
        threshold = params.value("retention_threshold")
        margin = params.value("ambiguity_margin")
        max_attractors = max(1, int(params.value("max_attractors")))
        class_nodes = {item.source_ref: item for item in payload.nodes if item.node_kind == ActivationNodeKind.SEMANTIC_CLASS}
        graph_map = dict(payload.candidate_graphs)
        ranked = sorted(
            (
                (class_nodes[candidate_ref].current_activation, candidate_ref)
                for candidate_ref, _node_ref in payload.candidate_node_refs
                if candidate_ref in class_nodes
            ),
            key=lambda item: (-item[0], item[1]),
        )
        top = ranked[0][0] if ranked else 0.0
        retained = [
            (activation, candidate_ref)
            for activation, candidate_ref in ranked
            if activation >= threshold and (top - activation <= margin or len(ranked) == 1)
        ]
        if not retained and ranked and ranked[0][0] > 0.0:
            # Preserve the strongest surviving class as a hypothesis, never as fabricated
            # certainty. Convergence remains false and the frontier records why.
            retained = [ranked[0]]
        retained = retained[:max_attractors]
        attractors = []
        derivation_map = dict(payload.candidate_derivation_refs)
        for activation, candidate_ref in retained:
            graph = graph_map[candidate_ref]
            # Preserve absolute recurrent support. Renormalizing a single weak or
            # budget-exhausted survivor to 1.0 would manufacture certainty.
            support = min(1.0, max(0.0, float(activation)))
            energy = None if support <= 0.0 else -math.log(max(support, 1e-15))
            attractors.append(SemanticAttractor(
                attractor_ref=artifact_ref(
                    "semantic-attractor-v351", activation_graph.graph_ref, candidate_ref, graph_map[candidate_ref].unresolved_refs
                ),
                graph=graph,
                semantic_fingerprint=next(
                    item.semantic_class_ref for item in payload.nodes
                    if item.node_kind == ActivationNodeKind.SEMANTIC_CLASS and item.source_ref == candidate_ref
                ),
                support=support,
                energy=energy,
                derivation_refs=tuple(sorted(set((candidate_ref, *derivation_map.get(candidate_ref, ()))))),
            ))

        converged = status == ConvergenceKind.CONVERGED
        normal_form_stable = bool(payload.iteration_summaries) and all(
            summary.semantic_normal_form_refs == payload.iteration_summaries[-1].semantic_normal_form_refs
            for summary in payload.iteration_summaries[-min(2, len(payload.iteration_summaries)):]
        )
        reason_refs = [f"convergence-status:{status.value}"]
        if len(retained) > 1:
            reason_refs.append("frontier:semantic-ambiguity:close-attractors")
        if payload.unresolved_refs:
            reason_refs.extend(f"frontier:unresolved:{ref}" for ref in payload.unresolved_refs)
        if not attractors:
            reason_refs.append("frontier:no-admissible-semantic-attractor")

        convergence = ConvergenceAssessment(
            converged=converged,
            semantic_normal_form_stable=normal_form_stable,
            activation_delta=float(activation_trace.convergence_delta),
            epsilon=params.value("convergence_epsilon"),
            reason_refs=tuple(sorted(set(reason_refs))),
        )
        partial = self._partial_meaning(retained, graph_map, status)
        open_variables = tuple(
            CSIRRef(CSIRNodeKind.VARIABLE, ref) for ref in sorted(payload.open_variable_refs)
        )
        return SemanticAttractorSet(
            attractor_set_ref=artifact_ref(
                "semantic-attractor-set-v351",
                activation_graph.graph_ref,
                tuple(item.semantic_fingerprint for item in attractors),
                status.value,
            ),
            attractors=tuple(attractors),
            partial_meaning=partial,
            open_variables=open_variables,
            convergence=convergence,
            authority_generation=activation_graph.authority_generation,
            authority_fingerprint=activation_graph.authority_fingerprint,
            semantic_authority_snapshot_fingerprint=activation_graph.semantic_authority_snapshot_fingerprint,
            dynamics_parameter_pins=activation_graph.dynamics_parameter_pins,
            proof_refs=tuple(sorted(set((
                *activation_graph.proof_refs,
                *activation_trace.proof_refs,
                "proof:canonical-semantic-class-stabilization-v351",
            )))),
        )

    @staticmethod
    def _status(trace: ActivationTrace) -> ConvergenceKind:
        for ref in trace.proof_refs:
            prefix = "convergence-status:"
            if ref.startswith(prefix):
                value = ref[len(prefix):]
                try:
                    return ConvergenceKind(value)
                except ValueError:
                    break
        if trace.iterations == 0:
            return ConvergenceKind.BUDGET_EXHAUSTED_PARTIAL
        return ConvergenceKind.CONVERGED if trace.convergence_delta == 0.0 else ConvergenceKind.BUDGET_EXHAUSTED_PARTIAL

    @staticmethod
    def _partial_meaning(retained, graph_map, status):
        if not retained:
            return None
        if len(retained) == 1:
            graph = graph_map[retained[0][1]]
            if status != ConvergenceKind.CONVERGED or graph.unresolved_refs or graph.variables:
                return graph
            return None
        # With multiple inequivalent semantic classes we do not select one as the
        # partial truth. A future common-subgraph proof can be added only when exact
        # node correspondence is proven; absence is safer than fabricated certainty.
        return None


__all__ = ["RecurrentAttractorStabilizerV351"]
