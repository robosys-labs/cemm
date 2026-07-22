"""Sparse bounded recurrent semantic dynamics for Phase 13."""
from __future__ import annotations

from dataclasses import replace
import math

from ..runtime_abi import ActivationGraph, ActivationTrace, CSIRCandidateSet, artifact_ref
from ..schema.model import semantic_fingerprint
from .compiler_v351 import TypedActivationGraphCompilerV351
from .model_v351 import (
    ActivationNodeKind, ConvergenceKind, EdgePolarity, IterationActivationSummary,
    MessageFamily, SemanticActivationNode, TypedActivationPayload,
)


class RecurrentDynamicsError(ValueError):
    pass


class RecurrentSemanticDynamicsV351:
    """Deterministic sparse recurrent solver over exact candidate structure.

    This is the canonical Stage-6 mechanism.  No learned score can create semantic
    authority, satisfy a hard mask, or fabricate a missing filler.
    """

    def __init__(self, *, compiler: TypedActivationGraphCompilerV351 | None = None) -> None:
        self.compiler = compiler or TypedActivationGraphCompilerV351()

    def run(
        self,
        *,
        csir_candidates: CSIRCandidateSet,
        authority_snapshot,
        semantic_authority_snapshot_v351,
        dynamics_parameters,
        read_generation,
        budgets,
        evidence_lattice=None,
        evidence_envelopes=(),
        grounding_candidates=None,
        referent_projections=None,
        state_space_projections=None,
        **_ignored,
    ):
        if (read_generation.authority_generation, read_generation.authority_fingerprint) != (
            csir_candidates.authority_generation, csir_candidates.authority_fingerprint
        ):
            raise RecurrentDynamicsError("read generation differs from CSIR candidate authority")
        if (authority_snapshot.generation, authority_snapshot.authority_fingerprint) != (
            csir_candidates.authority_generation, csir_candidates.authority_fingerprint
        ):
            raise RecurrentDynamicsError("runtime authority snapshot differs from CSIR candidate authority")
        payload = self.compiler.compile(
            csir_candidates=csir_candidates,
            semantic_authority_snapshot_v351=semantic_authority_snapshot_v351,
            dynamics_parameters=dynamics_parameters,
            evidence_lattice=evidence_lattice,
            evidence_envelopes=evidence_envelopes,
            grounding_candidates=grounding_candidates,
            referent_projections=referent_projections,
            state_space_projections=state_space_projections,
        )
        solved_payload, status, maximum_delta = self._iterate(payload, budgets=budgets)
        dynamics_pins = tuple(
            item.parameter_pin
            for item in sorted(dynamics_parameters, key=lambda item: item.parameter_family)
        )
        graph_ref = artifact_ref(
            "activation-graph-v351",
            csir_candidates.candidate_set_ref,
            solved_payload.fingerprint,
            status.value,
        )
        graph = ActivationGraph(
            graph_ref=graph_ref,
            payload=solved_payload,
            authority_generation=csir_candidates.authority_generation,
            authority_fingerprint=csir_candidates.authority_fingerprint,
            semantic_authority_snapshot_fingerprint=semantic_authority_snapshot_v351.snapshot_fingerprint,
            dynamics_parameter_pins=dynamics_pins,
            proof_refs=tuple(sorted(set((
                *solved_payload.proof_refs,
                f"proof:recurrent-status:{status.value}",
                "proof:sparse-typed-recurrent-dynamics-v351",
            )))),
        )
        trace = ActivationTrace(
            trace_ref=artifact_ref(
                "activation-trace-v351", graph_ref, len(solved_payload.iteration_summaries), maximum_delta, status.value
            ),
            iterations=len(solved_payload.iteration_summaries),
            convergence_delta=maximum_delta,
            proof_refs=tuple(sorted(set((
                f"convergence-status:{status.value}",
                f"parameter-set:{payload.parameter_set.parameter_set_ref}",
                *(f"message-family:{family.value}:edges={count}" for family, count in payload.family_edge_counts),
            )))),
        )
        return graph, trace

    def _iterate(self, payload: TypedActivationPayload, *, budgets):
        parameter_set = payload.parameter_set
        epsilon = parameter_set.value("convergence_epsilon")
        damping = parameter_set.value("damping")
        if not 0.0 <= damping < 1.0:
            raise RecurrentDynamicsError("exact damping parameter must be in [0,1)")
        floor = parameter_set.value("activation_floor")
        max_steps = int(getattr(budgets, "inference_steps", 0))
        if max_steps <= 0:
            return payload, ConvergenceKind.BUDGET_EXHAUSTED_PARTIAL, 0.0

        node_map = {item.node_ref: item for item in payload.nodes}
        masks = {item.target_node_ref: item.allowed for item in payload.masks}
        incoming: dict[str, list] = {ref: [] for ref in node_map}
        for edge in payload.edges:
            incoming[edge.target_node_ref].append(edge)
        competition_for: dict[str, tuple[str, ...]] = {}
        for group in payload.competition_groups:
            for member in group.member_node_refs:
                competition_for[member] = group.member_node_refs

        fixed_kinds = {ActivationNodeKind.EVIDENCE, ActivationNodeKind.MULTIMODAL_TRACK}
        summaries = []
        signatures: dict[tuple[tuple[str, float], ...], int] = {}
        normal_forms = tuple(sorted(ref for ref, _ in payload.candidate_node_refs))
        previous_normal_forms = normal_forms
        maximum_delta = 0.0
        status = ConvergenceKind.BUDGET_EXHAUSTED_PARTIAL

        for iteration in range(1, max_steps + 1):
            next_values: dict[str, float] = {}
            maximum_delta = 0.0
            masked_count = 0
            for ref in sorted(node_map):
                node = node_map[ref]
                if masks.get(ref, True) is False:
                    next_values[ref] = 0.0
                    masked_count += 1
                    maximum_delta = max(maximum_delta, abs(node.current_activation))
                    continue
                if node.node_kind in fixed_kinds:
                    next_values[ref] = node.current_activation
                    continue

                incoming_value = 0.0
                for edge in incoming.get(ref, ()):
                    source = node_map[edge.source_node_ref]
                    family_gain = parameter_set.gain(edge.family)
                    channel_gain = self._channel_gain(parameter_set, source.node_kind, edge.family)
                    signed = 1.0 if edge.polarity == EdgePolarity.EXCITATORY else -1.0
                    incoming_value += signed * family_gain * channel_gain * edge.strength * source.current_activation

                inhibition = 0.0
                competitors = competition_for.get(ref, ())
                if competitors:
                    others = [node_map[item].current_activation for item in competitors if item != ref]
                    if others:
                        inhibition = parameter_set.value("inhibition_strength") * (sum(others) / len(others))

                raw = (
                    parameter_set.value("bias")
                    + parameter_set.value("prior_gain") * node.initial_activation
                    + incoming_value
                    - inhibition
                )
                proposed = self._sigmoid(raw)
                updated = damping * node.current_activation + (1.0 - damping) * proposed
                if updated < floor:
                    updated = 0.0
                if not math.isfinite(updated):
                    status = ConvergenceKind.NUMERIC_INVALID
                    return replace(payload, iteration_summaries=tuple(summaries)), status, float("inf")
                updated = min(1.0, max(0.0, updated))
                next_values[ref] = updated
                maximum_delta = max(maximum_delta, abs(updated - node.current_activation))

            node_map = {
                ref: replace(node_map[ref], current_activation=next_values[ref])
                for ref in sorted(node_map)
            }
            winners = self._competition_winners(payload, node_map)
            energy = self._diagnostic_energy(payload, node_map)
            summaries.append(IterationActivationSummary(
                iteration=iteration,
                maximum_delta=maximum_delta,
                active_nodes=sum(1 for value in next_values.values() if value > floor),
                masked_nodes=masked_count,
                total_energy=energy,
                semantic_normal_form_refs=normal_forms,
                competition_winner_refs=winners,
            ))

            signature = tuple((ref, round(next_values[ref], int(parameter_set.value("oscillation_round_digits")))) for ref in sorted(next_values))
            if signature in signatures and iteration - signatures[signature] > 1:
                status = ConvergenceKind.OSCILLATION_DETECTED
                break
            signatures[signature] = iteration

            normal_form_stable = normal_forms == previous_normal_forms
            previous_normal_forms = normal_forms
            if maximum_delta <= epsilon and normal_form_stable:
                status = ConvergenceKind.CONVERGED
                break

        admissible = [
            node_map[node_ref].current_activation
            for _, node_ref in payload.candidate_node_refs
            if masks.get(node_ref, True)
        ]
        if not admissible or max(admissible, default=0.0) <= floor:
            status = ConvergenceKind.NO_ADMISSIBLE_CANDIDATE

        return replace(
            payload,
            nodes=tuple(node_map[key] for key in sorted(node_map)),
            iteration_summaries=tuple(summaries),
            proof_refs=tuple(sorted(set((*payload.proof_refs, f"proof:recurrent-status:{status.value}")))),
        ), status, maximum_delta

    @staticmethod
    def _channel_gain(parameter_set, source_kind: ActivationNodeKind, family: MessageFamily) -> float:
        if family in {MessageFamily.CONTEXT, MessageFamily.TIME_ASPECT, MessageFamily.DISCOURSE}:
            return parameter_set.value("context_gain")
        if source_kind in {
            ActivationNodeKind.EVIDENCE, ActivationNodeKind.MULTIMODAL_TRACK,
            ActivationNodeKind.REFERENT, ActivationNodeKind.STATE_PROJECTION,
        }:
            return parameter_set.value("bottom_up_gain")
        return parameter_set.value("top_down_gain")

    @staticmethod
    def _sigmoid(value: float) -> float:
        if value >= 60.0:
            return 1.0
        if value <= -60.0:
            return 0.0
        return 1.0 / (1.0 + math.exp(-value))

    @staticmethod
    def _competition_winners(payload, node_map):
        winners = []
        for group in payload.competition_groups:
            ranked = sorted(
                ((node_map[ref].current_activation, ref) for ref in group.member_node_refs),
                key=lambda item: (-item[0], item[1]),
            )
            if ranked:
                winners.append(ranked[0][1])
        return tuple(sorted(winners))

    @staticmethod
    def _diagnostic_energy(payload, node_map) -> float:
        # Diagnostic energy is not semantic authority. Lower is better fit of retained
        # class mass plus incompatibility penalty inside explicit competition groups.
        fit = 0.0
        for _, node_ref in payload.candidate_node_refs:
            node = node_map[node_ref]
            fit += (1.0 - node.current_activation) ** 2
        inhibition = 0.0
        for group in payload.competition_groups:
            values = [node_map[ref].current_activation for ref in group.member_node_refs]
            for index, left in enumerate(values):
                for right in values[index + 1:]:
                    inhibition += left * right
        return float(fit + inhibition)


__all__ = ["RecurrentDynamicsError", "RecurrentSemanticDynamicsV351"]
