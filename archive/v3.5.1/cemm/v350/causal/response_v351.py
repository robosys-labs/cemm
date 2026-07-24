"""Phase-16 causal-explanation Response CSIR extension."""
from __future__ import annotations

from ..csir.authority_v351 import SemanticDefinitionCompiler
from ..csir.canonical_v351 import exact_fingerprint, semantic_fingerprint
from ..csir.model import CSIRGraph
from ..orchestration import StageExecutionStatus, StageOutcome
from ..response.builder_v351 import ResponseCSIRBuilderV351
from ..response.csir_v351 import ResponseCSIRCandidate, ResponseDecision, ResponseFamily, ResponseSourceBinding
from ..runtime_abi import artifact_ref
from .model_v351 import CausalQueryResultV351


def _combine_graphs(*graphs: CSIRGraph) -> CSIRGraph:
    """Exact graph union without duplicating shared semantic occurrences.

    Cause/effect subgraphs may share referents or semantic applications. Equal stable
    identities are deduplicated; identity collisions with different payloads fail closed.
    """
    specs = {
        "terms": "term_ref",
        "variables": "variable_ref",
        "applications": "application_ref",
        "bindings": "binding_ref",
        "qualifiers": "qualifier_ref",
        "scope_embeddings": "embedding_ref",
        "coordinations": "coordination_ref",
        "proof_links": "proof_ref",
    }
    merged = {name: {} for name in specs}
    roots = {}
    for graph in graphs:
        for name, ref_attr in specs.items():
            for item in getattr(graph, name):
                ref = getattr(item, ref_attr)
                prior = merged[name].get(ref)
                if prior is not None and prior != item:
                    raise ValueError(f"causal explanation graph identity collision:{name}:{ref}")
                merged[name][ref] = item
        for root in graph.root_refs:
            roots[(root.kind.value, root.ref)] = root
    return CSIRGraph(
        **{
            name: tuple(merged[name][key] for key in sorted(merged[name]))
            for name in specs
        },
        root_refs=tuple(roots[key] for key in sorted(roots)),
    )


class Phase16ResponseCSIRBuilderV351(ResponseCSIRBuilderV351):
    RUNTIME_ABI='v351'; SERVICE_KIND='response_csir_builder'

    def build(self, *, cycle, capability, store, effect_store, semantic_capabilities):
        goal=cycle.artifacts.get('goal_decision')
        family=(goal.selected_families[0] if goal is not None and getattr(goal,'selected_families',()) else None)
        if family is not ResponseFamily.PROVIDE_CAUSAL_EXPLANATION:
            return super().build(cycle=cycle,capability=capability,store=store,effect_store=effect_store,semantic_capabilities=semantic_capabilities)
        semantic_authority=cycle.artifacts.get('semantic_authority_snapshot_v351')
        authority=self.authority_map.validate_family(semantic_authority,family)
        if authority.cause_port_pin is None or authority.effect_port_pin is None:
            return StageOutcome(StageExecutionStatus.DEFERRED,frontier_refs=('frontier:response:causal-explanation-ports-required',))
        selected_goals=set(goal.selected_goal_refs)
        chosen=None
        for result in tuple(cycle.artifacts.get('causal_query_results',()) or ()):
            if not isinstance(result,CausalQueryResultV351) or not result.answered or result.explanation is None: continue
            candidate_goal=next((g for g in goal.candidates if g.goal_ref in selected_goals and result.explanation.explanation_ref in g.source_refs),None)
            if candidate_goal is not None: chosen=result; break
        if chosen is None:
            return StageOutcome(StageExecutionStatus.DEFERRED,frontier_refs=('frontier:response:warranted-causal-explanation-required',))
        explanation=chosen.explanation
        if explanation.cause_graph is None or explanation.effect_graph is None or len(explanation.cause_graph.root_refs)!=1 or len(explanation.effect_graph.root_refs)!=1:
            return StageOutcome(StageExecutionStatus.DEFERRED,frontier_refs=('frontier:response:causal-explanation-semantic-graphs-required',))
        external=_combine_graphs(explanation.cause_graph,explanation.effect_graph)
        compiled=SemanticDefinitionCompiler(semantic_authority).compile(
            authority.definition_pin, external_graph=external,
            arguments={authority.cause_port_pin:explanation.cause_graph.root_refs[0],authority.effect_port_pin:explanation.effect_graph.root_refs[0]},
        )
        graph,envelope=semantic_authority.bind_execution_authority(
            compiled.graph,operation='compose',context_ref=cycle.context_ref,permission_ref=cycle.permission_ref,require_projection_authority=False,
        )
        compiled.closure_proof.verify(graph,authority_generation=semantic_authority.generation,authority_fingerprint=semantic_authority.authority_fingerprint,authority_snapshot=semantic_authority)
        causal_proof_refs = tuple(sorted(set((explanation.proof_ref, *chosen.proof_refs))))
        source=ResponseSourceBinding(
            source_ref=chosen.result_ref,semantic_ref=explanation.explanation_ref,
            proof_refs=causal_proof_refs,confidence=explanation.confidence,
        )
        sem,exact=semantic_fingerprint(graph),exact_fingerprint(graph)
        candidate=ResponseCSIRCandidate(
            candidate_ref=artifact_ref('response-csir-candidate',family.value,sem,explanation.explanation_ref),family=family,
            graph=graph,semantic_fingerprint=sem,exact_fingerprint=exact,
            authority_generation=semantic_authority.generation,authority_fingerprint=semantic_authority.authority_fingerprint,
            semantic_authority_snapshot_fingerprint=semantic_authority.snapshot_fingerprint,
            closure_proof=compiled.closure_proof,execution_authority_ref=envelope.envelope_ref,source_bindings=(source,),
            audience_refs=tuple(cycle.audience_refs),context_ref=cycle.context_ref,permission_ref=cycle.permission_ref,
            obligation_refs=tuple(goal.selected_goal_refs),target_refs=(chosen.query_ref,),
            qualification_refs=(explanation.proof_ref,*explanation.step_refs),score=explanation.confidence,
        )
        decision=ResponseDecision(
            decision_ref=artifact_ref('response-decision',cycle.cycle_ref,candidate.candidate_ref),selected_candidate_ref=candidate.candidate_ref,
            family=family,graph=graph,semantic_fingerprint=sem,exact_fingerprint=exact,
            authority_generation=candidate.authority_generation,authority_fingerprint=candidate.authority_fingerprint,
            semantic_authority_snapshot_fingerprint=candidate.semantic_authority_snapshot_fingerprint,
            source_bindings=(source,),audience_refs=candidate.audience_refs,context_ref=cycle.context_ref,permission_ref=cycle.permission_ref,
            target_refs=candidate.target_refs,qualification_refs=candidate.qualification_refs,
            proof_refs=tuple(sorted(set((compiled.closure_proof.proof_ref, *causal_proof_refs)))),
        )
        return StageOutcome(StageExecutionStatus.PERFORMED,artifacts={'response_csir_candidates':(candidate,),'response_decision':decision,'_runtime_frontiers':()},frontier_refs=())


__all__=['Phase16ResponseCSIRBuilderV351']
