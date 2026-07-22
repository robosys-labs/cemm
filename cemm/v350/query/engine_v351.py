"""Bounded Stage-10 semantic query binder with exact proof-path retrieval."""
from __future__ import annotations

from dataclasses import replace

from ..conversation.session_memory import SessionBeliefEntry
from ..csir.model import CSIRGraph, CSIRNodeKind, CSIRRef, TermKind
from ..csir.operations import match
from ..epistemic.model import WorkingBeliefDelta
from ..orchestration import StageExecutionStatus, StageOutcome
from ..runtime_abi import artifact_ref
from ..schema.model import semantic_fingerprint
from .model import ExplanationProof, QueryBinding, QueryResult


class GroundedQueryEngineV351:
    RUNTIME_ABI = "v351"
    SERVICE_KIND = "query_engine"

    def __init__(self, session_memory, *, maximum_beliefs_per_query: int = 512) -> None:
        if maximum_beliefs_per_query < 1:
            raise ValueError("query belief budget must be positive")
        self.session_memory = session_memory
        self.maximum_beliefs_per_query = maximum_beliefs_per_query

    @staticmethod
    def _effective_beliefs(snapshot, delta: WorkingBeliefDelta | None):
        retracts = set(() if delta is None else delta.retract_claim_refs)
        superseded = {old for old, _new in (() if delta is None else delta.supersede_claims)}
        result = [
            item for item in snapshot.active_beliefs
            if item.claim_ref not in retracts and item.claim_ref not in superseded
        ]
        if delta is not None:
            result.extend(delta.additions)
        deduped = {}
        for item in result:
            deduped[item.belief_ref] = item
        return tuple(deduped[key] for key in sorted(deduped))

    @staticmethod
    def _variable_is_structurally_used(graph: CSIRGraph, variable_ref: CSIRRef) -> bool:
        if any(variable_ref in binding.fillers for binding in graph.bindings):
            return True
        if any(
            qualifier.target == variable_ref or qualifier.value_ref == variable_ref
            for qualifier in graph.qualifiers
        ):
            return True
        if any(
            embedding.operator == variable_ref or embedding.scoped == variable_ref
            for embedding in graph.scope_embeddings
        ):
            return True
        if any(variable_ref in coordination.members for coordination in graph.coordinations):
            return True
        return False

    @staticmethod
    def _truth_restriction(graph: CSIRGraph, variable_ref: CSIRRef) -> CSIRGraph:
        return replace(
            graph,
            variables=tuple(item for item in graph.variables if item.variable_ref != variable_ref.ref),
            root_refs=tuple(item for item in graph.root_refs if item != variable_ref),
        )

    @staticmethod
    def _binding_from_ref(query, variable_ref, value_ref, belief: SessionBeliefEntry):
        node = belief.graph.node(value_ref)
        identity_ref = None
        atom = None
        if node is not None and getattr(node, "term_kind", None) is TermKind.REFERENT:
            identity_ref = node.identity_ref
        if node is not None and getattr(node, "term_kind", None) is TermKind.LITERAL:
            atom = node.literal_value
        if atom is not None:
            return QueryBinding(
                binding_ref="query-binding:" + semantic_fingerprint(
                    "query-binding", (query.query_ref, variable_ref.ref, repr(atom), belief.claim_ref), 24
                ),
                variable_ref=variable_ref,
                value_atom=atom,
                proposition_ref=belief.proposition_ref,
                claim_ref=belief.claim_ref,
                confidence=belief.confidence,
            )
        return QueryBinding(
            binding_ref="query-binding:" + semantic_fingerprint(
                "query-binding", (query.query_ref, variable_ref.ref, value_ref.kind.value, value_ref.ref, belief.claim_ref), 24
            ),
            variable_ref=variable_ref,
            value_ref=value_ref,
            value_identity_ref=identity_ref,
            proposition_ref=belief.proposition_ref,
            claim_ref=belief.claim_ref,
            confidence=belief.confidence,
        )

    def query(self, *, cycle, capability, store, effect_store, semantic_capabilities):
        del capability, store, effect_store, semantic_capabilities
        queries = tuple(cycle.artifacts.get("queries", ()))
        snapshot = self.session_memory.snapshot(cycle.context_ref, cycle.permission_ref)
        delta = cycle.artifacts.get("working_belief_delta")
        if delta is not None and not isinstance(delta, WorkingBeliefDelta):
            raise TypeError("Stage 10 working_belief_delta must be WorkingBeliefDelta")
        beliefs = self._effective_beliefs(snapshot, delta)
        results = []
        proofs = []
        frontiers = []
        if len(beliefs) > self.maximum_beliefs_per_query:
            beliefs = beliefs[-self.maximum_beliefs_per_query:]
            frontiers.append("frontier:query:belief-budget")

        for query in queries:
            variable_ref = query.answer_projection.requested_variable_ref
            truth_query = not self._variable_is_structurally_used(query.query_graph, variable_ref)
            restriction = (
                self._truth_restriction(query.query_graph, variable_ref)
                if truth_query else query.query_graph
            )
            bindings = []
            matched_beliefs = []
            for belief in beliefs:
                if belief.context_ref != query.context_ref:
                    continue
                assessment = match(restriction, belief.graph)
                if not assessment.matched:
                    continue
                matched_beliefs.append(belief)
                if truth_query:
                    bindings.append(
                        QueryBinding(
                            binding_ref="query-binding:" + semantic_fingerprint(
                                "truth-query-binding", (query.query_ref, belief.claim_ref), 24
                            ),
                            variable_ref=variable_ref,
                            value_atom=True,
                            proposition_ref=belief.proposition_ref,
                            claim_ref=belief.claim_ref,
                            confidence=belief.confidence,
                        )
                    )
                    continue
                value = assessment.substitution.get(variable_ref.ref)
                if value is None:
                    continue
                bindings.append(self._binding_from_ref(query, variable_ref, value, belief))

            # Deduplicate by semantic answer, not by internal role/slot labels.
            unique = {}
            for binding in bindings:
                key = (
                    None if binding.value_ref is None else (binding.value_ref.kind.value, binding.value_identity_ref or binding.value_ref.ref),
                    binding.value_atom,
                )
                prior = unique.get(key)
                if prior is None or binding.confidence > prior.confidence:
                    unique[key] = binding
            selected = tuple(
                sorted(unique.values(), key=lambda item: (-item.confidence, item.binding_ref))
            )
            proof_refs = []
            for belief in matched_beliefs:
                proof = ExplanationProof(
                    proof_ref="query-proof:" + semantic_fingerprint(
                        "query-proof", (query.query_ref, belief.belief_ref, belief.proof_refs), 32
                    ),
                    query_ref=query.query_ref,
                    target_ref=belief.proposition_ref,
                    premise_refs=(belief.proposition_ref, belief.claim_ref),
                    evidence_refs=belief.evidence_refs,
                    operation_refs=("csir:match", "visibility:context_permission"),
                    minimal=True,
                )
                proofs.append(proof)
                proof_refs.append(proof.proof_ref)
            query_frontiers = ()
            if not selected:
                ref = "frontier:query:no-grounded-binding:" + query.query_ref
                frontiers.append(ref)
                query_frontiers = (ref,)
            results.append(
                QueryResult(
                    result_ref=artifact_ref(
                        "query-result", query.query_ref,
                        tuple(item.binding_ref for item in selected),
                    ),
                    query_ref=query.query_ref,
                    bindings=selected,
                    truth_value=(True if truth_query and selected else None),
                    explanation_proof_refs=tuple(sorted(set(proof_refs))),
                    frontier_refs=query_frontiers,
                )
            )
        return StageOutcome(
            StageExecutionStatus.PERFORMED,
            artifacts={
                "query_results": tuple(results),
                "explanation_proofs": tuple(proofs),
            },
            frontier_refs=tuple(sorted(set(frontiers))),
        )


__all__ = ["GroundedQueryEngineV351"]
