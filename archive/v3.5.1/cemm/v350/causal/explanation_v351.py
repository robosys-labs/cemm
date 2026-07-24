"""Minimal warranted causal explanation extraction and causal query answering."""
from __future__ import annotations

from collections import defaultdict, deque
from typing import Mapping

from ..csir.model import CSIRGraph
from ..schema.model import semantic_fingerprint
from .model_v351 import (
    CausalExplanationV351, CausalProofV351, CausalQueryRequestV351, CausalQueryResultV351,
    CausalSimulationResultV351,
)


class ExplanationExtractor:
    RUNTIME_ABI = "v351"
    SERVICE_KIND = "causal_explanation_extractor_v351"

    def extract(
        self,
        *,
        query_ref: str,
        target_variable_ref: str,
        proof: CausalProofV351,
        semantic_graphs: Mapping[str, CSIRGraph] | None = None,
    ) -> CausalExplanationV351 | None:
        semantic_graphs = dict(semantic_graphs or {})
        by_target = defaultdict(list)
        by_ref = {step.step_ref: step for step in proof.steps}
        for step in proof.steps:
            if not step.intervention_cut:
                by_target[step.target_variable_ref].append(step)
        target_steps = tuple(by_target.get(target_variable_ref, ()))
        if not target_steps:
            return None
        # A variable may change repeatedly in one branch. Explain only the terminal target
        # derivation(s), not the union of every historical write. A target step is non-terminal
        # when it is an ancestor of another target step. Multiple independent terminal writes
        # remain ambiguous and fail partial instead of being merged.
        target_refs = {step.step_ref for step in target_steps}
        ancestor_target_refs = set()
        for step in target_steps:
            pending = list(step.parent_step_refs)
            seen = set()
            while pending:
                ref = pending.pop()
                if ref in seen or ref not in by_ref:
                    continue
                seen.add(ref)
                if ref in target_refs:
                    ancestor_target_refs.add(ref)
                pending.extend(by_ref[ref].parent_step_refs)
        terminal = tuple(step for step in target_steps if step.step_ref not in ancestor_target_refs)
        if len(terminal) != 1:
            return None
        # Reverse traversal yields the least proof subgraph needed to derive the terminal target.
        chosen = set()
        queue = deque((terminal[0].step_ref,))
        while queue:
            ref = queue.popleft()
            if ref in chosen: continue
            chosen.add(ref)
            step = by_ref[ref]
            for parent in step.parent_step_refs: queue.append(parent)
        steps = tuple(by_ref[ref] for ref in sorted(chosen))
        positive_steps = tuple(step for step in steps if not step.intervention_cut)
        causes = sorted({source for step in positive_steps for source in step.source_variable_refs if source != target_variable_ref})
        cause_events = sorted({source for step in positive_steps for source in step.source_event_refs})
        mechanisms = {}
        confidence = 1.0
        probability = 1.0
        for step in positive_steps:
            mechanisms[step.mechanism_pin.key] = step.mechanism_pin
            confidence = min(confidence, step.confidence)
            probability = min(probability, step.branch_probability)
        cause_graph = next(
            (semantic_graphs.get(ref) for ref in (*cause_events, *causes) if semantic_graphs.get(ref) is not None),
            None,
        )
        effect_graph = semantic_graphs.get(target_variable_ref)
        return CausalExplanationV351(
            explanation_ref="causal-explanation:" + semantic_fingerprint(
                "causal-explanation-v351", (query_ref, target_variable_ref, proof.proof_ref, tuple(sorted(chosen))), 32,
            ),
            query_ref=query_ref, target_variable_ref=target_variable_ref,
            cause_variable_refs=tuple(causes), cause_event_refs=tuple(cause_events),
            mechanism_pins=tuple(mechanisms[key] for key in sorted(mechanisms)),
            proof_ref=proof.proof_ref, step_refs=tuple(sorted(chosen)), minimal=True,
            confidence=confidence, probability=probability,
            cause_graph=cause_graph, effect_graph=effect_graph,
            frontier_refs=(() if (cause_graph is not None and effect_graph is not None) else ("frontier:causal:explanation-semantic-surface-projection",)),
        )

    def extract_effect_of(
        self,
        *,
        query_ref: str,
        source_variable_ref: str,
        proof: CausalProofV351,
        semantic_graphs: Mapping[str, CSIRGraph] | None = None,
    ) -> CausalExplanationV351 | None:
        """Traverse the same proof DAG forward from an exact causal source variable."""
        semantic_graphs = dict(semantic_graphs or {})
        by_ref = {step.step_ref: step for step in proof.steps}
        children = defaultdict(list)
        for step in proof.steps:
            for parent in step.parent_step_refs:
                children[parent].append(step.step_ref)
        seeds = tuple(
            step.step_ref for step in proof.steps
            if not step.intervention_cut and source_variable_ref in step.source_variable_refs
        )
        if not seeds:
            return None
        chosen = set()
        queue = deque(sorted(seeds))
        while queue:
            ref = queue.popleft()
            if ref in chosen:
                continue
            chosen.add(ref)
            queue.extend(sorted(children.get(ref, ())))
        terminal_targets = sorted({
            by_ref[ref].target_variable_ref
            for ref in chosen
            if by_ref[ref].target_variable_ref
            and not by_ref[ref].intervention_cut
            and not any(child in chosen and not by_ref[child].intervention_cut for child in children.get(ref, ()))
        })
        if len(terminal_targets) != 1:
            return None
        target = terminal_targets[0]
        steps = tuple(by_ref[ref] for ref in sorted(chosen))
        positive_steps = tuple(step for step in steps if not step.intervention_cut)
        mechanisms = {}
        confidence = 1.0
        probability = 1.0
        for step in positive_steps:
            mechanisms[step.mechanism_pin.key] = step.mechanism_pin
            confidence = min(confidence, step.confidence)
            probability = min(probability, step.branch_probability)
        return CausalExplanationV351(
            explanation_ref="causal-explanation:" + semantic_fingerprint(
                "causal-effect-explanation-v351",
                (query_ref, source_variable_ref, target, proof.proof_ref, tuple(sorted(chosen))),
                32,
            ),
            query_ref=query_ref, target_variable_ref=target,
            cause_variable_refs=(source_variable_ref,), cause_event_refs=(),
            mechanism_pins=tuple(mechanisms[key] for key in sorted(mechanisms)),
            proof_ref=proof.proof_ref, step_refs=tuple(sorted(chosen)), minimal=True,
            confidence=confidence, probability=probability,
            cause_graph=semantic_graphs.get(source_variable_ref),
            effect_graph=semantic_graphs.get(target),
            frontier_refs=(
                () if semantic_graphs.get(source_variable_ref) is not None and semantic_graphs.get(target) is not None
                else ("frontier:causal:explanation-semantic-surface-projection",)
            ),
        )


    @staticmethod
    def _terminal_target_value_refs(
        simulation: CausalSimulationResultV351, target_variable_ref: str,
    ) -> tuple[str, ...]:
        """Return one terminal target value identity per resolved branch that changes target."""
        values = []
        for branch in simulation.branches:
            if not branch.resolved:
                continue
            matching = [
                delta for delta in branch.state_deltas
                if _variable_ref_for_delta(delta) == target_variable_ref
            ]
            if not matching:
                continue
            final = matching[-1]
            values.append("" if final.new_value is None else final.new_value.value_ref)
        return tuple(values)

    @staticmethod
    def _resolved_proofs(simulation: CausalSimulationResultV351) -> tuple[CausalProofV351, ...]:
        resolved_refs = {branch.proof_ref for branch in simulation.branches if branch.resolved}
        return tuple(proof for proof in simulation.causal_proofs if proof.proof_ref in resolved_refs)

    def answer_why_not(
        self,
        request: CausalQueryRequestV351,
        factual: CausalSimulationResultV351,
        contrast: CausalSimulationResultV351,
        *,
        semantic_graphs: Mapping[str, CSIRGraph] | None = None,
    ) -> CausalQueryResultV351:
        """Contrast factual and explicit interventional/counterfactual worlds.

        A warranted why-not answer requires the contrast to be absent factually *and* obtain in
        the exact contrast world. Otherwise the model has not demonstrated the missing cause.
        """
        if not request.contrast_value_key:
            return CausalQueryResultV351(
                result_ref="causal-query-result:" + semantic_fingerprint(
                    "causal-query-why-not-missing-contrast", request.query_ref, 24
                ),
                query_ref=request.query_ref, answered=False, explanation=None,
                simulation_ref=factual.simulation_ref, contrast_simulation_ref=contrast.simulation_ref,
                frontier_refs=("frontier:causal:why-not-requires-explicit-contrast",),
            )
        if factual.context_semantics.value != "actual":
            raise ValueError("why-not factual comparison requires actual-context simulation")
        if contrast.context_semantics.value not in {"counterfactual", "intervention"}:
            raise ValueError("why-not contrast requires interventional/counterfactual simulation")
        if factual.unresolved_probability_mass > 1e-12 or contrast.unresolved_probability_mass > 1e-12:
            return CausalQueryResultV351(
                result_ref="causal-query-result:" + semantic_fingerprint(
                    "causal-query-why-not-unresolved-probability",
                    (request.query_ref, factual.unresolved_probability_mass, contrast.unresolved_probability_mass), 24,
                ),
                query_ref=request.query_ref, answered=False, explanation=None,
                simulation_ref=factual.simulation_ref, contrast_simulation_ref=contrast.simulation_ref,
                frontier_refs=("frontier:causal:why-not-unresolved-probability-mass",),
            )
        factual_values = self._terminal_target_value_refs(factual, request.target_variable_ref)
        contrast_values = self._terminal_target_value_refs(contrast, request.target_variable_ref)
        if not factual_values or len(set(factual_values)) != 1:
            return CausalQueryResultV351(
                result_ref="causal-query-result:" + semantic_fingerprint(
                    "causal-query-why-not-factual-target-unresolved", request.query_ref, 24
                ),
                query_ref=request.query_ref, answered=False, explanation=None,
                simulation_ref=factual.simulation_ref, contrast_simulation_ref=contrast.simulation_ref,
                frontier_refs=("frontier:causal:why-not-factual-target-unresolved",),
            )
        if request.contrast_value_key in factual_values:
            return CausalQueryResultV351(
                result_ref="causal-query-result:" + semantic_fingerprint(
                    "causal-query-why-not-contrast-actually-obtains", request.query_ref, 24
                ),
                query_ref=request.query_ref, answered=False, explanation=None,
                simulation_ref=factual.simulation_ref, contrast_simulation_ref=contrast.simulation_ref,
                frontier_refs=("frontier:causal:why-not-contrast-actually-obtains",),
            )
        if not contrast_values or len(set(contrast_values)) != 1 or contrast_values[0] != request.contrast_value_key:
            return CausalQueryResultV351(
                result_ref="causal-query-result:" + semantic_fingerprint(
                    "causal-query-why-not-contrast-not-demonstrated",
                    (request.query_ref, tuple(sorted(set(contrast_values)))), 24,
                ),
                query_ref=request.query_ref, answered=False, explanation=None,
                simulation_ref=factual.simulation_ref, contrast_simulation_ref=contrast.simulation_ref,
                frontier_refs=("frontier:causal:why-not-contrast-world-does-not-establish-target",),
            )
        factual_proofs = tuple(
            proof for proof in self._resolved_proofs(factual)
            if request.target_variable_ref in proof.target_variable_refs
        )
        contrast_proofs = tuple(
            proof for proof in self._resolved_proofs(contrast)
            if request.target_variable_ref in proof.target_variable_refs
        )
        if len(factual_proofs) != 1 or len(contrast_proofs) != 1:
            refs = tuple(sorted({
                *(proof.proof_ref for proof in factual_proofs),
                *(proof.proof_ref for proof in contrast_proofs),
            }))
            return CausalQueryResultV351(
                result_ref="causal-query-result:" + semantic_fingerprint(
                    "causal-query-why-not-proof-ambiguity", (request.query_ref, refs), 24
                ),
                query_ref=request.query_ref, answered=False, explanation=None,
                simulation_ref=factual.simulation_ref, contrast_simulation_ref=contrast.simulation_ref,
                proof_refs=refs,
                frontier_refs=("frontier:causal:why-not-requires-singular-factual-and-contrast-proof",),
            )
        explanation = self.extract(
            query_ref=request.query_ref, target_variable_ref=request.target_variable_ref,
            proof=contrast_proofs[0], semantic_graphs=semantic_graphs,
        )
        if (
            explanation is not None and request.source_variable_ref
            and request.source_variable_ref not in explanation.cause_variable_refs
        ):
            explanation = None
        frontiers = (
            tuple(explanation.frontier_refs)
            if explanation is not None and explanation.frontier_refs
            else (() if explanation is not None else ("frontier:causal:why-not-explanation-unavailable",))
        )
        answered = explanation is not None and not frontiers
        return CausalQueryResultV351(
            result_ref="causal-query-result:" + semantic_fingerprint(
                "causal-query-why-not-v351",
                (request.query_ref, factual.simulation_ref, contrast.simulation_ref,
                 factual_proofs[0].proof_ref, contrast_proofs[0].proof_ref,
                 None if explanation is None else explanation.explanation_ref), 32,
            ),
            query_ref=request.query_ref, answered=answered,
            explanation=(explanation if answered else None), simulation_ref=factual.simulation_ref,
            contrast_simulation_ref=contrast.simulation_ref,
            proof_refs=(factual_proofs[0].proof_ref, contrast_proofs[0].proof_ref),
            frontier_refs=frontiers,
        )

    def answer(
        self,
        request: CausalQueryRequestV351,
        simulation: CausalSimulationResultV351,
        *,
        semantic_graphs: Mapping[str, CSIRGraph] | None = None,
    ) -> CausalQueryResultV351:
        if request.query_kind not in {"why", "cause_of", "why_not", "what_if", "effect_of"}:
            return CausalQueryResultV351(
                result_ref="causal-query-result:" + semantic_fingerprint("causal-query-unsupported", request.query_ref, 24),
                query_ref=request.query_ref, answered=False, explanation=None,
                frontier_refs=("frontier:causal:unsupported-query-kind",),
            )
        if request.query_kind == "what_if":
            if request.intervention is None:
                return CausalQueryResultV351(
                    result_ref="causal-query-result:" + semantic_fingerprint(
                        "causal-query-what-if-missing-intervention", request.query_ref, 24
                    ),
                    query_ref=request.query_ref, answered=False, explanation=None,
                    simulation_ref=simulation.simulation_ref,
                    frontier_refs=("frontier:causal:what-if-requires-explicit-intervention",),
                )
            if simulation.context_semantics.value not in {"intervention", "counterfactual", "planning"}:
                return CausalQueryResultV351(
                    result_ref="causal-query-result:" + semantic_fingerprint(
                        "causal-query-what-if-context-mismatch", request.query_ref, 24
                    ),
                    query_ref=request.query_ref, answered=False, explanation=None,
                    simulation_ref=simulation.simulation_ref,
                    frontier_refs=("frontier:causal:what-if-requires-interventional-simulation",),
                )
            if simulation.intervention_ref != request.intervention.context_ref:
                return CausalQueryResultV351(
                    result_ref="causal-query-result:" + semantic_fingerprint(
                        "causal-query-what-if-intervention-mismatch", request.query_ref, 24
                    ),
                    query_ref=request.query_ref, answered=False, explanation=None,
                    simulation_ref=simulation.simulation_ref,
                    frontier_refs=("frontier:causal:what-if-intervention-mismatch",),
                )
        if request.query_kind == "why_not":
            return CausalQueryResultV351(
                result_ref="causal-query-result:" + semantic_fingerprint(
                    "causal-query-why-not-needs-factual-contrast-pair", request.query_ref, 24
                ),
                query_ref=request.query_ref, answered=False, explanation=None,
                simulation_ref=simulation.simulation_ref,
                frontier_refs=("frontier:causal:why-not-requires-factual-and-contrast-simulations",),
            )
        if request.query_kind == "effect_of":
            source_ref = request.source_variable_ref or request.target_variable_ref
            matching_proofs = tuple(
                item for item in self._resolved_proofs(simulation)
                if any(not step.intervention_cut and source_ref in step.source_variable_refs for step in item.steps)
            )
        else:
            matching_proofs = tuple(
                item for item in self._resolved_proofs(simulation)
                if request.target_variable_ref in item.target_variable_refs
            )
        if simulation.unresolved_probability_mass > 1e-12:
            return CausalQueryResultV351(
                result_ref="causal-query-result:" + semantic_fingerprint(
                    "causal-query-unresolved-probability",
                    (request.query_ref, simulation.simulation_ref, simulation.unresolved_probability_mass), 24,
                ),
                query_ref=request.query_ref, answered=False, explanation=None,
                simulation_ref=simulation.simulation_ref,
                proof_refs=tuple(sorted(proof.proof_ref for proof in matching_proofs)),
                frontier_refs=tuple(sorted(set((*simulation.frontier_refs, "frontier:causal:unresolved-probability-mass")))),
            )
        if not matching_proofs:
            return CausalQueryResultV351(
                result_ref="causal-query-result:" + semantic_fingerprint("causal-query-no-proof", (request.query_ref, request.target_variable_ref), 24),
                query_ref=request.query_ref, answered=False, explanation=None,
                simulation_ref=simulation.simulation_ref,
                frontier_refs=tuple(sorted(set((*simulation.frontier_refs, "frontier:causal:no-warranted-path")))),
            )
        if len(matching_proofs) != 1:
            # Multiple independently warranted branches/mechanisms are epistemic alternatives,
            # not an invitation to choose whichever proof happens to be first. A future exact
            # distribution/explanation projection may aggregate them; until then fail partial.
            return CausalQueryResultV351(
                result_ref="causal-query-result:" + semantic_fingerprint(
                    "causal-query-ambiguous-proof",
                    (request.query_ref, simulation.simulation_ref, tuple(sorted(x.proof_ref for x in matching_proofs))),
                    24,
                ),
                query_ref=request.query_ref, answered=False, explanation=None,
                simulation_ref=simulation.simulation_ref,
                proof_refs=tuple(sorted(x.proof_ref for x in matching_proofs)),
                frontier_refs=tuple(sorted(set((*simulation.frontier_refs, "frontier:causal:multiple-warranted-proof-paths")))),
            )
        proof = matching_proofs[0]
        if request.query_kind == "effect_of":
            source_ref = request.source_variable_ref or request.target_variable_ref
            explanation = self.extract_effect_of(
                query_ref=request.query_ref, source_variable_ref=source_ref,
                proof=proof, semantic_graphs=semantic_graphs,
            )
        else:
            explanation = self.extract(
                query_ref=request.query_ref, target_variable_ref=request.target_variable_ref,
                proof=proof, semantic_graphs=semantic_graphs,
            )
            if (
                explanation is not None and request.source_variable_ref
                and request.source_variable_ref not in explanation.cause_variable_refs
            ):
                explanation = None
        answered = explanation is not None and not explanation.frontier_refs
        return CausalQueryResultV351(
            result_ref="causal-query-result:" + semantic_fingerprint(
                "causal-query-result-v351", (request.query_ref, simulation.simulation_ref, None if explanation is None else explanation.explanation_ref), 32,
            ),
            query_ref=request.query_ref, answered=answered,
            explanation=(explanation if answered else None), simulation_ref=simulation.simulation_ref,
            proof_refs=(proof.proof_ref,),
            frontier_refs=(
                tuple(explanation.frontier_refs)
                if explanation is not None and explanation.frontier_refs
                else (() if explanation is not None else ("frontier:causal:explanation-unavailable",))
            ),
        )


def _variable_ref_for_delta(delta):
    return "causal-variable:" + semantic_fingerprint(
        "causal-variable-v351",
        (delta.holder_ref, delta.dimension_pin.key, delta.context_ref, delta.time_step),
        32,
    )


__all__ = ["ExplanationExtractor"]
