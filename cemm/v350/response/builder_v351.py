"""Stage-18 canonical Response CSIR construction for the Phase-12 conversational alpha."""
from __future__ import annotations

from dataclasses import replace
from typing import Any, Iterable

from ..csir.authority_v351 import AuthoritySnapshotV351, SemanticDefinitionCompiler, SemanticAuthorityError
from ..csir.canonical_v351 import exact_fingerprint, semantic_fingerprint
from ..csir.model import CSIRGraph, CSIRRef, SemanticTerm, TermKind
from ..orchestration import StageExecutionStatus, StageOutcome
from ..runtime_abi import artifact_ref
from .csir_v351 import (
    ConversationalGoalDecision, ResponseAuthorityMapV351, ResponseBuildFrontier,
    ResponseCSIRCandidate, ResponseDecision, ResponseError, ResponseFamily,
    ResponseSourceBinding,
)


class ResponseCSIRBuilderV351:
    RUNTIME_ABI = "v351"
    SERVICE_KIND = "response_csir_builder"

    def __init__(
        self, *, authority_map: ResponseAuthorityMapV351 | None = None, session_memory=None,
    ) -> None:
        self.authority_map = authority_map or ResponseAuthorityMapV351()
        self.session_memory = session_memory

    @staticmethod
    def _literal_term(value: str | int | float | bool, seed: str) -> SemanticTerm:
        return SemanticTerm(
            term_ref=artifact_ref("response-literal", seed, type(value).__name__, repr(value)),
            term_kind=TermKind.LITERAL,
            literal_value=value,
        )

    @staticmethod
    def _referent_term(identity_ref: str, seed: str) -> SemanticTerm:
        return SemanticTerm(
            term_ref=artifact_ref("response-referent", seed, identity_ref),
            term_kind=TermKind.REFERENT,
            identity_ref=identity_ref,
        )

    @staticmethod
    def _target_term(target_ref: str, seed: str) -> SemanticTerm:
        return SemanticTerm(
            term_ref=artifact_ref("response-target", seed, target_ref),
            term_kind=TermKind.OTHER,
            identity_ref=target_ref,
            features=(("semantic_target_ref", target_ref),),
        )

    @staticmethod
    def _semantic_source_term(semantic_ref: str, seed: str) -> SemanticTerm:
        return SemanticTerm(
            term_ref=artifact_ref("response-semantic-source", seed, semantic_ref),
            term_kind=TermKind.OTHER, identity_ref=semantic_ref,
            features=(("semantic_source_ref", semantic_ref),),
        )

    def _answer_payload(self, result, cycle) -> tuple[SemanticTerm | None, ResponseSourceBinding | None, tuple[str, ...]]:
        if tuple(getattr(result, "bindings", ()) or ()):
            binding = tuple(result.bindings)[0]
            semantic_ref = binding.proposition_ref or binding.claim_ref or binding.binding_ref
            source_graph = (
                None if self.session_memory is None
                else self.session_memory.semantic_graph(cycle.context_ref, cycle.permission_ref, semantic_ref)
            )
            if binding.value_atom is not None:
                term = self._literal_term(binding.value_atom, binding.binding_ref)
            elif binding.value_identity_ref:
                term = self._referent_term(binding.value_identity_ref, binding.binding_ref)
            elif binding.value_ref is not None and source_graph is not None:
                # Preserve exact categorical/state/type authority when a query projects a
                # semantic term rather than a literal/referent.  Only a TERM is copied into
                # Response CSIR here; complex subgraphs require their own reviewed response
                # projection instead of being flattened or stringified.
                node = source_graph.node(binding.value_ref)
                if not isinstance(node, SemanticTerm):
                    return None, None, ("query_binding_requires_reviewed_complex_projection",)
                term = replace(
                    node,
                    term_ref=artifact_ref(
                        "response-query-term", binding.binding_ref,
                        binding.value_ref.kind.value, binding.value_ref.ref,
                    ),
                )
            else:
                return None, None, ("query_binding_has_no_surface_safe_semantic_value",)
            source = ResponseSourceBinding(
                source_ref=result.result_ref,
                semantic_ref=semantic_ref,
                proof_refs=tuple(result.explanation_proof_refs),
                semantic_fingerprint=("" if source_graph is None else semantic_fingerprint(source_graph)),
                exact_fingerprint=("" if source_graph is None else exact_fingerprint(source_graph)),
                confidence=binding.confidence,
            )
            return term, source, ()
        if result.truth_value is not None:
            term = self._literal_term(bool(result.truth_value), result.result_ref)
            source = ResponseSourceBinding(
                source_ref=result.result_ref,
                semantic_ref=result.query_ref,
                proof_refs=tuple(result.explanation_proof_refs),
                confidence=1.0,
            )
            return term, source, ()
        return None, None, tuple(result.frontier_refs) or ("query_result_unanswered",)

    def _compile_family(
        self,
        *,
        family: ResponseFamily,
        semantic_authority: AuthoritySnapshotV351,
        context_ref: str,
        permission_ref: str,
        audience_refs: tuple[str, ...],
        content_term: SemanticTerm | None,
        target_ref: str | None,
        source_bindings: tuple[ResponseSourceBinding, ...],
        obligation_refs: tuple[str, ...],
        qualification_refs: tuple[str, ...],
        score: float,
    ) -> ResponseCSIRCandidate:
        authority = self.authority_map.require(family)
        external_terms: list[SemanticTerm] = []
        arguments = {}
        if content_term is not None:
            external_terms.append(content_term)
            if authority.content_port_pin is None:
                raise ResponseError(f"{family.value} authority lacks content port")
            arguments[authority.content_port_pin] = content_term.node_ref
        if target_ref is not None and authority.target_port_pin is not None:
            # Only families whose reviewed semantic definition declares a target port bind
            # the target into denotational Response CSIR.  REPORT_* targets are routing/
            # discourse qualifications; their source content graph already carries the
            # holder/participants that must be realized.
            target = self._target_term(target_ref, family.value)
            external_terms.append(target)
            arguments[authority.target_port_pin] = target.node_ref
        external = CSIRGraph(terms=tuple(external_terms)) if external_terms else None
        compiled = SemanticDefinitionCompiler(semantic_authority).compile(
            authority.definition_pin, external_graph=external, arguments=arguments,
        )
        graph, envelope = semantic_authority.bind_execution_authority(
            compiled.graph,
            operation="compose",
            context_ref=context_ref,
            permission_ref=permission_ref,
            require_projection_authority=False,
        )
        # Closure identity is semantic/profile-separated, so the typed proof remains valid
        # after the exact operational profile is attached by bind_execution_authority().
        compiled.closure_proof.verify(
            graph,
            authority_generation=semantic_authority.generation,
            authority_fingerprint=semantic_authority.authority_fingerprint,
            authority_snapshot=semantic_authority,
        )
        sem = semantic_fingerprint(graph)
        exact = exact_fingerprint(graph)
        return ResponseCSIRCandidate(
            candidate_ref=artifact_ref("response-csir-candidate", family.value, sem, tuple(x.source_ref for x in source_bindings)),
            family=family,
            graph=graph,
            semantic_fingerprint=sem,
            exact_fingerprint=exact,
            authority_generation=semantic_authority.generation,
            authority_fingerprint=semantic_authority.authority_fingerprint,
            semantic_authority_snapshot_fingerprint=semantic_authority.snapshot_fingerprint,
            closure_proof=compiled.closure_proof,
            execution_authority_ref=envelope.envelope_ref,
            source_bindings=source_bindings,
            audience_refs=tuple(audience_refs),
            context_ref=context_ref,
            permission_ref=permission_ref,
            obligation_refs=obligation_refs,
            target_refs=() if target_ref is None else (target_ref,),
            qualification_refs=qualification_refs,
            score=score,
        )

    def build(self, *, cycle, capability, store, effect_store, semantic_capabilities):
        del store, effect_store, semantic_capabilities
        semantic_authority = cycle.artifacts.get("semantic_authority_snapshot_v351")
        if semantic_authority is None:
            return StageOutcome(
                StageExecutionStatus.DEFERRED,
                frontier_refs=("frontier:response:semantic-authority-snapshot-required",),
            )
        if not isinstance(semantic_authority, AuthoritySnapshotV351):
            raise TypeError("Stage 18 requires AuthoritySnapshotV351")
        if (semantic_authority.generation, semantic_authority.authority_fingerprint) != (
            capability.authority_generation, capability.authority_fingerprint,
        ):
            raise ValueError("Response CSIR authority differs from cycle-pinned AuthorityGeneration")
        goal = cycle.artifacts.get("goal_decision")
        if not isinstance(goal, ConversationalGoalDecision):
            return StageOutcome(
                StageExecutionStatus.DEFERRED,
                frontier_refs=("frontier:response:conversational-goal-decision-required",),
            )
        family = goal.selected_families[0] if goal.selected_families else ResponseFamily.NO_RESPONSE_REQUIRED
        # Validate only the selected response family.  Unrelated inactive families must not
        # become an overarching response gate, and semantic silence needs no surface-bearing
        # response definition at all.
        if family is not ResponseFamily.NO_RESPONSE_REQUIRED:
            try:
                self.authority_map.validate_family(semantic_authority, family)
            except Exception as exc:
                frontier = ResponseBuildFrontier(
                    frontier_ref=artifact_ref("frontier:response:authority-not-active", family.value, str(exc)),
                    missing_contract="exact selected response-family authority in pinned generation",
                    family=family, source_refs=(str(exc),),
                )
                return StageOutcome(
                    StageExecutionStatus.DEFERRED,
                    artifacts={"response_csir_candidates": (), "_runtime_frontiers": (frontier,)},
                    frontier_refs=(frontier.frontier_ref,),
                )
        selected_goal_refs = tuple(goal.selected_goal_refs)
        candidates: list[ResponseCSIRCandidate] = []
        frontiers: list[ResponseBuildFrontier] = []

        if family is ResponseFamily.NO_RESPONSE_REQUIRED:
            empty = CSIRGraph()
            sem = semantic_fingerprint(empty)
            candidate = ResponseCSIRCandidate(
                candidate_ref=artifact_ref("response-csir-candidate", family.value, cycle.cycle_ref),
                family=family, graph=empty, semantic_fingerprint=sem,
                exact_fingerprint=exact_fingerprint(empty),
                authority_generation=capability.authority_generation,
                authority_fingerprint=capability.authority_fingerprint,
                semantic_authority_snapshot_fingerprint=semantic_authority.snapshot_fingerprint,
                closure_proof=None, execution_authority_ref="",
                source_bindings=(),
                audience_refs=tuple(cycle.audience_refs), context_ref=cycle.context_ref,
                permission_ref=cycle.permission_ref, obligation_refs=selected_goal_refs,
                score=1.0,
            )
            candidates.append(candidate)
        elif family is ResponseFamily.ANSWER_QUERY:
            selected_goal = next((item for item in goal.candidates if item.goal_ref in selected_goal_refs), None)
            target_query_refs = set(() if selected_goal is None else selected_goal.target_refs)
            results = tuple(
                item for item in cycle.artifacts.get("query_results", ())
                if not target_query_refs or item.query_ref in target_query_refs
            )
            for result in results:
                term, source, unresolved = self._answer_payload(result, cycle)
                if term is None or source is None:
                    frontiers.append(ResponseBuildFrontier(
                        frontier_ref=artifact_ref("frontier:response:answer-unresolved", result.result_ref),
                        missing_contract="grounded answer binding with surface-safe semantic value",
                        family=family, target_refs=(result.query_ref,), source_refs=(result.result_ref,),
                    ))
                    continue
                try:
                    candidates.append(self._compile_family(
                        family=family, semantic_authority=semantic_authority,
                        context_ref=cycle.context_ref, permission_ref=cycle.permission_ref,
                        audience_refs=tuple(cycle.audience_refs), content_term=term,
                        target_ref=None, source_bindings=(source,), obligation_refs=selected_goal_refs,
                        qualification_refs=tuple(sorted(set(result.explanation_proof_refs))),
                        score=max((binding.confidence for binding in result.bindings), default=1.0),
                    ))
                except (ResponseError, SemanticAuthorityError, ValueError) as exc:
                    frontiers.append(ResponseBuildFrontier(
                        frontier_ref=artifact_ref("frontier:response:answer-authority", result.result_ref, str(exc)),
                        missing_contract="exact ANSWER_QUERY response definition/ports/use authority",
                        family=family, target_refs=(result.query_ref,), source_refs=(result.result_ref,),
                    ))
        else:
            selected_goal = next((item for item in goal.candidates if item.goal_ref in selected_goal_refs), None)
            target_ref = None if selected_goal is None or not selected_goal.target_refs else selected_goal.target_refs[0]
            source_refs = () if selected_goal is None else selected_goal.source_refs
            source_bindings = []
            for ref in source_refs:
                source_graph = (
                    None if self.session_memory is None
                    else self.session_memory.semantic_graph(cycle.context_ref, cycle.permission_ref, ref)
                )
                source_bindings.append(ResponseSourceBinding(
                    ref, ref,
                    semantic_fingerprint=("" if source_graph is None else semantic_fingerprint(source_graph)),
                    exact_fingerprint=("" if source_graph is None else exact_fingerprint(source_graph)),
                ))
            source_bindings = tuple(source_bindings)
            content_term = None
            requires_semantic_source = family in {
                ResponseFamily.REPORT_STATE, ResponseFamily.REPORT_RELATION,
                ResponseFamily.REPORT_EVENT, ResponseFamily.REPORT_CAPABILITY,
                ResponseFamily.CORRECT_PRIOR_OUTPUT,
            }
            if requires_semantic_source:
                if not source_refs:
                    frontiers.append(ResponseBuildFrontier(
                        frontier_ref=artifact_ref("frontier:response:semantic-source-required", family.value),
                        missing_contract=f"semantic source for {family.value}", family=family,
                        target_refs=() if target_ref is None else (target_ref,),
                    ))
                    source_bindings = ()
                else:
                    if not source_bindings[0].semantic_fingerprint or not source_bindings[0].exact_fingerprint:
                        frontiers.append(ResponseBuildFrontier(
                            frontier_ref=artifact_ref("frontier:response:semantic-source-unfrozen", family.value, source_refs[0]),
                            missing_contract="immutable scoped semantic source graph for response realization",
                            family=family, source_refs=source_refs,
                        ))
                        source_bindings = ()
                    else:
                        content_term = self._semantic_source_term(source_refs[0], family.value)
            try:
                if requires_semantic_source and not source_bindings:
                    raise ResponseError(f"{family.value} requires exact semantic source binding")
                candidates.append(self._compile_family(
                    family=family, semantic_authority=semantic_authority,
                    context_ref=cycle.context_ref, permission_ref=cycle.permission_ref,
                    audience_refs=tuple(cycle.audience_refs), content_term=content_term,
                    target_ref=target_ref, source_bindings=source_bindings,
                    obligation_refs=selected_goal_refs, qualification_refs=(), score=1.0,
                ))
            except (ResponseError, SemanticAuthorityError, ValueError) as exc:
                frontiers.append(ResponseBuildFrontier(
                    frontier_ref=artifact_ref("frontier:response:family-authority", family.value, str(exc)),
                    missing_contract=f"exact {family.value} response definition/ports/use authority",
                    family=family, target_refs=() if target_ref is None else (target_ref,),
                    source_refs=source_refs,
                ))

        if not candidates:
            return StageOutcome(
                StageExecutionStatus.DEFERRED,
                artifacts={"response_csir_candidates": (), "_runtime_frontiers": tuple(frontiers)},
                frontier_refs=tuple(item.frontier_ref for item in frontiers) or (
                    "frontier:response:no-authorized-candidate",
                ),
            )

        # Canonical class identity and bounded deterministic choice.  Source confidence may
        # rank equivalent response actions but never changes semantic identity or authority.
        by_semantic = {}
        for candidate in sorted(candidates, key=lambda item: (-item.score, item.exact_fingerprint, item.candidate_ref)):
            by_semantic.setdefault(candidate.semantic_fingerprint, candidate)
        classes = tuple(by_semantic[key] for key in sorted(by_semantic))
        selected = max(classes, key=lambda item: (item.score, item.semantic_fingerprint))
        proof_refs = tuple(sorted({
            *(item.proof_ref for item in (selected.closure_proof,) if item is not None),
            *(ref for source in selected.source_bindings for ref in source.proof_refs),
        }))
        decision = ResponseDecision(
            decision_ref=artifact_ref("response-decision", cycle.cycle_ref, selected.candidate_ref),
            selected_candidate_ref=selected.candidate_ref,
            family=selected.family,
            graph=selected.graph,
            semantic_fingerprint=selected.semantic_fingerprint,
            exact_fingerprint=selected.exact_fingerprint,
            authority_generation=selected.authority_generation,
            authority_fingerprint=selected.authority_fingerprint,
            semantic_authority_snapshot_fingerprint=selected.semantic_authority_snapshot_fingerprint,
            source_bindings=selected.source_bindings,
            audience_refs=selected.audience_refs,
            context_ref=selected.context_ref,
            permission_ref=selected.permission_ref,
            target_refs=selected.target_refs,
            qualification_refs=selected.qualification_refs,
            proof_refs=proof_refs,
            frontier_refs=selected.frontier_refs,
            no_response_reason_ref=(
                goal.reason_refs[0] if selected.family is ResponseFamily.NO_RESPONSE_REQUIRED and goal.reason_refs
                else ("no_semantic_response_obligation" if selected.family is ResponseFamily.NO_RESPONSE_REQUIRED else None)
            ),
        )
        return StageOutcome(
            StageExecutionStatus.PERFORMED,
            artifacts={
                "response_csir_candidates": classes,
                "response_decision": decision,
                "_runtime_frontiers": tuple(frontiers),
            },
            frontier_refs=tuple(item.frontier_ref for item in frontiers),
        )


__all__ = ["ResponseCSIRBuilderV351"]
