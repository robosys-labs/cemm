"""Stage-8 grounded discourse/proposition/query/correction re-abstraction.

All discourse classification is structural or exact-authority driven.  There are no raw
language phrase handlers and no mapping from grammatical subject/object to semantic roles.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Iterable

from ..conversation.session_memory import ClarificationMemory, OpenQuestionMemory
from ..csir.canonical_v351 import semantic_fingerprint
from ..csir.model import CSIRGraph, CSIRNodeKind, CSIRRef, SemanticVariable
from ..csir.operations import project
from ..grounded.model import (
    AnswerProjection, Claim, CorrectionKind, CorrectionRetraction, GapKind,
    GroundedSemanticSubstrate, IdentityCandidate, IdentityCandidateStatus,
    InformationGap, Mention, MentionChain, ParticipantRole, Proposition, Query,
    Referent, SemanticContext,
)
from ..orchestration import StageExecutionStatus, StageOutcome
from ..runtime_abi import SemanticAttractorSet, artifact_ref
from ..runtime_kernel import ParticipantRole as RuntimeParticipantRole
from ..schema.model import semantic_fingerprint as runtime_fingerprint
from .model import (
    DiscourseAct, DiscourseActAuthority, DiscourseActKind, DiscourseAuthorityMap,
    DiscourseStructureBatch,
)


class DiscourseStructureBuilderV351:
    RUNTIME_ABI = "v351"
    SERVICE_KIND = "discourse_structure_builder"

    def __init__(self, session_memory, *, authority_map: DiscourseAuthorityMap | None = None) -> None:
        self.session_memory = session_memory
        self.authority_map = authority_map or DiscourseAuthorityMap()

    @staticmethod
    def _root_authority(graph: CSIRGraph, authority_map: DiscourseAuthorityMap):
        index = authority_map.by_definition
        for root in graph.root_refs:
            if root.kind is not CSIRNodeKind.APPLICATION:
                continue
            app = graph.node(root)
            if app is not None and app.predicate_pin.key in index:
                return app, index[app.predicate_pin.key]
        return None, None

    @staticmethod
    def _content_graph(graph: CSIRGraph, application, authority: DiscourseActAuthority | None) -> CSIRGraph:
        if application is None or authority is None or authority.content_port_pin is None:
            return graph
        bindings = tuple(
            item for item in graph.bindings_for(application.application_ref)
            if item.port_pin.key == authority.content_port_pin.key
        )
        if len(bindings) != 1 or len(bindings[0].fillers) != 1:
            return graph
        try:
            return project(graph, bindings[0].fillers)
        except Exception:
            return graph

    @staticmethod
    def _referent_substrate(cycle) -> tuple[
        tuple[SemanticContext, ...], tuple[Referent, ...], tuple[Mention, ...],
        tuple[IdentityCandidate, ...], tuple[MentionChain, ...], tuple[ParticipantRole, ...]
    ]:
        frame = cycle.artifacts["participant_frame"]
        grounding = cycle.artifacts.get("grounding_candidates")
        context = SemanticContext(
            context_ref=cycle.context_ref,
            context_kind="actual",
            permission_ref=cycle.permission_ref,
            evidence_refs=tuple(frame.identity_evidence_refs),
        )
        referent_refs = {
            frame.system_ref, frame.input_speaker_ref,
            *frame.input_addressee_refs, *frame.response_audience_refs,
        }
        mentions = []
        identities = []
        chains = []
        selected = {}
        ambiguous = set()
        result = None if grounding is None else getattr(grounding, "result", None)
        if result is not None:
            ambiguous = set(result.ambiguous_mention_refs)
            if result.selected_assignment_ref is not None:
                assignment = next(
                    (item for item in result.assignments if item.assignment_ref == result.selected_assignment_ref),
                    None,
                )
                if assignment is not None:
                    selected = dict(assignment.mention_to_target)
                    referent_refs.update(selected.values())
            candidates_by_mention = {}
            for candidate in result.candidates:
                candidates_by_mention.setdefault(candidate.mention_ref, []).append(candidate)
            for item in result.mentions:
                identity_refs = []
                for candidate in candidates_by_mention.get(item.mention_ref, ()):
                    status = IdentityCandidateStatus.CANDIDATE
                    if selected.get(item.mention_ref) == candidate.target_ref:
                        status = (
                            IdentityCandidateStatus.PROVISIONAL
                            if bool(getattr(candidate, "provisional", False)) or item.mention_ref in ambiguous
                            else IdentityCandidateStatus.RESOLVED
                        )
                    identity_ref = "identity-candidate:" + runtime_fingerprint(
                        "identity-candidate",
                        (item.mention_ref, candidate.target_ref, candidate.candidate_ref), 24,
                    )
                    identity_refs.append(identity_ref)
                    identities.append(
                        IdentityCandidate(
                            candidate_ref=identity_ref,
                            mention_ref=item.mention_ref,
                            referent_ref=candidate.target_ref,
                            status=status,
                            support=max(0.0, min(1.0, 0.5 + candidate.local_score / 20.0)),
                            evidence_refs=tuple(
                                sorted({ref for factor in candidate.factors for ref in factor.evidence_refs})
                            ) or tuple(item.evidence_refs),
                            constraint_refs=tuple(
                                sorted({factor.factor_ref for factor in candidate.factors if factor.hard})
                            ),
                        )
                    )
                mentions.append(
                    Mention(
                        mention_ref=item.mention_ref,
                        source_ref=item.source_ref,
                        span_start=item.span.start,
                        span_end=item.span.end,
                        form_candidate_refs=(),
                        identity_candidate_refs=tuple(identity_refs),
                    )
                )
                if identity_refs:
                    chains.append(
                        MentionChain(
                            chain_ref="mention-chain:" + runtime_fingerprint(
                                "mention-chain", (item.mention_ref, tuple(identity_refs)), 20
                            ),
                            mention_refs=(item.mention_ref,),
                            referent_candidate_refs=tuple(identity_refs),
                            resolved_referent_ref=(
                                selected.get(item.mention_ref)
                                if item.mention_ref not in ambiguous else None
                            ),
                            proof_refs=tuple(item.evidence_refs),
                        )
                    )
        referents = tuple(
            Referent(
                referent_ref=ref,
                context_refs=(cycle.context_ref,),
                permission_ref=cycle.permission_ref,
                evidence_refs=tuple(frame.identity_evidence_refs) or (cycle.cycle_ref,),
                durable_identity=ref in {frame.system_ref, frame.input_speaker_ref},
            )
            for ref in sorted(referent_refs)
        )
        participant_roles = (
            ParticipantRole(
                RuntimeParticipantRole.SYSTEM.value, frame.system_ref, frame.frame_ref,
                tuple(frame.identity_evidence_refs) or (cycle.cycle_ref,),
            ),
            ParticipantRole(
                RuntimeParticipantRole.INPUT_SPEAKER.value, frame.input_speaker_ref, frame.frame_ref,
                tuple(frame.identity_evidence_refs) or (cycle.cycle_ref,),
            ),
            *tuple(
                ParticipantRole(
                    RuntimeParticipantRole.INPUT_ADDRESSEE.value, ref, frame.frame_ref,
                    tuple(frame.identity_evidence_refs) or (cycle.cycle_ref,),
                )
                for ref in frame.input_addressee_refs
            ),
        )
        return (context,), referents, tuple(mentions), tuple(identities), tuple(chains), participant_roles

    def build(self, *, cycle, capability, store, effect_store, semantic_capabilities):
        del capability, store, effect_store, semantic_capabilities
        attractors = cycle.artifacts["semantic_attractors"]
        if not isinstance(attractors, SemanticAttractorSet):
            raise TypeError("Stage 8 requires SemanticAttractorSet")
        semantic_authority = cycle.artifacts["semantic_authority_snapshot_v351"]
        self.authority_map.validate(semantic_authority)
        frame = cycle.artifacts["participant_frame"]
        contexts, referents, mentions, identities, chains, participant_roles = self._referent_substrate(cycle)

        propositions = []
        claims = []
        queries = []
        corrections = []
        acts = []
        open_questions = []
        clarifications = []
        frontiers = []
        source_evidence = tuple(
            sorted({ref for envelope in cycle.artifacts.get("evidence_envelopes", ()) for ref in (envelope.evidence_ref, *envelope.evidence_refs)})
        ) or (cycle.cycle_ref,)

        semantic_items = [
            (item.graph, item.support, item.attractor_ref, False)
            for item in attractors.attractors
        ]
        if attractors.partial_meaning is not None:
            partial_fp = semantic_fingerprint(attractors.partial_meaning)
            if all(semantic_fingerprint(item[0]) != partial_fp for item in semantic_items):
                semantic_items.append((
                    attractors.partial_meaning, 0.0,
                    "partial:" + partial_fp[:24], True,
                ))

        for semantic_graph, semantic_support, derivation_ref, is_partial in semantic_items:
            app, authority = self._root_authority(semantic_graph, self.authority_map)
            content = self._content_graph(semantic_graph, app, authority)
            act_kind = authority.act_kind if authority is not None else (
                DiscourseActKind.QUERY
                if any(variable.open_purpose == "query" for variable in content.variables)
                else DiscourseActKind.ASSERTION
            )
            prop_ref = "proposition:" + semantic_fingerprint(content)
            proposition = Proposition(
                proposition_ref=prop_ref,
                content=content,
                context_ref=cycle.context_ref,
                source_refs=(frame.input_speaker_ref,),
                evidence_refs=source_evidence,
            )
            propositions.append(proposition)
            act_ref = "discourse-act:" + runtime_fingerprint(
                "discourse-act", (cycle.cycle_ref, prop_ref, act_kind.value), 24
            )
            act_targets = ()

            if act_kind is DiscourseActKind.QUERY:
                variables = tuple(variable for variable in content.variables if variable.open_purpose == "query")
                restriction = content
                if not variables:
                    truth = SemanticVariable(
                        variable_ref="truth:" + runtime_fingerprint("truth-gap", prop_ref, 16),
                        allowed_kinds=frozenset({CSIRNodeKind.TERM}),
                        scope_ref=cycle.context_ref,
                        open_purpose="query",
                    )
                    variables = (truth,)
                    restriction = replace(
                        content,
                        variables=(*content.variables, truth),
                        root_refs=(*content.root_refs, truth.node_ref),
                    )
                gaps = []
                for variable in variables:
                    gap = InformationGap(
                        gap_ref="gap:" + runtime_fingerprint(
                            "information-gap", (cycle.cycle_ref, prop_ref, variable.variable_ref), 20
                        ),
                        kind=(GapKind.PROPOSITION_TRUTH if variable.variable_ref.startswith("truth:") else GapKind.OTHER),
                        variable_ref=variable.node_ref,
                        restriction_graph=restriction,
                        evidence_refs=source_evidence,
                    )
                    gaps.append(gap)
                projection = AnswerProjection(
                    projection_ref="answer-projection:" + runtime_fingerprint(
                        "answer-projection", (prop_ref, variables[0].variable_ref), 20
                    ),
                    requested_variable_ref=variables[0].node_ref,
                )
                query = Query(
                    query_ref="query:" + runtime_fingerprint(
                        "query", (cycle.cycle_ref, prop_ref, tuple(g.gap_ref for g in gaps)), 24
                    ),
                    query_graph=restriction,
                    gap_refs=tuple(gap.gap_ref for gap in gaps),
                    answer_projection=projection,
                    speaker_ref=frame.input_speaker_ref,
                    audience_refs=frame.input_addressee_refs,
                    context_ref=cycle.context_ref,
                    evidence_refs=source_evidence,
                )
                # Gaps live in the substrate below and are linked to this query.
                queries.append((query, tuple(gaps)))
                open_questions.append(
                    OpenQuestionMemory(
                        question_ref="open-question:" + runtime_fingerprint(
                            "open-question", query.query_ref, 20
                        ),
                        query_ref=query.query_ref,
                        context_ref=cycle.context_ref,
                        speaker_ref=frame.input_speaker_ref,
                        target_refs=(),
                        evidence_refs=source_evidence,
                    )
                )
                act_targets = (query.query_ref,)
            elif is_partial:
                frontier = "frontier:discourse:partial-meaning:" + prop_ref
                frontiers.append(frontier)
                act_kind = DiscourseActKind.OTHER
                act_targets = (prop_ref,)
            else:
                claim_ref = "claim:" + runtime_fingerprint(
                    "claim-occurrence", (cycle.cycle_ref, prop_ref, frame.input_speaker_ref), 24
                )
                claim = Claim(
                    claim_ref=claim_ref,
                    proposition_ref=prop_ref,
                    claimant_ref=frame.input_speaker_ref,
                    audience_refs=frame.input_addressee_refs,
                    source_context_ref=cycle.context_ref,
                    reported_context_ref=cycle.context_ref,
                    evidence_refs=source_evidence,
                    commitment_strength=max(0.0, min(1.0, semantic_support)),
                )
                claims.append(claim)
                act_targets = (claim_ref,)
                if act_kind in {DiscourseActKind.CORRECTION, DiscourseActKind.RETRACTION}:
                    target = self.session_memory.latest_claim_ref(
                        cycle.context_ref, cycle.permission_ref,
                        source_ref=frame.input_speaker_ref,
                    )
                    if target is None:
                        frontier = "frontier:discourse:correction-target-unresolved:" + claim_ref
                        frontiers.append(frontier)
                        clarifications.append(
                            ClarificationMemory(
                                clarification_ref="clarification:" + runtime_fingerprint(
                                    "clarification", (claim_ref, frontier), 20
                                ),
                                target_ref=claim_ref,
                                reason_ref="correction_target_unresolved",
                                context_ref=cycle.context_ref,
                                evidence_refs=source_evidence,
                            )
                        )
                    else:
                        corrections.append(
                            CorrectionRetraction(
                                correction_ref="correction:" + runtime_fingerprint(
                                    "correction", (cycle.cycle_ref, target, prop_ref), 24
                                ),
                                kind=(
                                    CorrectionKind.RETRACT
                                    if act_kind is DiscourseActKind.RETRACTION
                                    else CorrectionKind.SUPERSEDE
                                ),
                                source_ref=frame.input_speaker_ref,
                                target_ref=target,
                                replacement_ref=(None if act_kind is DiscourseActKind.RETRACTION else prop_ref),
                                context_ref=cycle.context_ref,
                                evidence_refs=source_evidence,
                            )
                        )

            acts.append(
                DiscourseAct(
                    act_ref=act_ref,
                    act_kind=act_kind,
                    semantic_ref=prop_ref,
                    speaker_ref=frame.input_speaker_ref,
                    audience_refs=frame.input_addressee_refs,
                    context_ref=cycle.context_ref,
                    evidence_refs=source_evidence,
                    authority_pin=None if authority is None else authority.definition_pin,
                    target_refs=act_targets,
                )
            )

        gaps = tuple(gap for _query, values in queries for gap in values)
        query_values = tuple(query for query, _values in queries)
        substrate = GroundedSemanticSubstrate(
            substrate_ref=artifact_ref("grounded-semantic-substrate", cycle.cycle_ref),
            contexts=contexts,
            referents=referents,
            identity_candidates=identities,
            participant_roles=participant_roles,
            mentions=mentions,
            mention_chains=chains,
            propositions=tuple(propositions),
            claims=tuple(claims),
            gaps=gaps,
            queries=query_values,
            corrections=tuple(corrections),
            frontier_refs=tuple(sorted(set(frontiers))),
        )
        batch = DiscourseStructureBatch(
            batch_ref=artifact_ref("discourse-structures", cycle.cycle_ref),
            substrate=substrate,
            acts=tuple(acts),
            open_questions=tuple(open_questions),
            clarification_targets=tuple(clarifications),
            frontier_refs=tuple(sorted(set(frontiers))),
        )
        return StageOutcome(
            StageExecutionStatus.PERFORMED,
            artifacts={
                "discourse_structures": batch,
                "propositions": tuple(propositions),
                "claims": tuple(claims),
                "events": (),
                "queries": query_values,
                "corrections": tuple(corrections),
                "commitments": (),
            },
            frontier_refs=tuple(sorted(set(frontiers))),
        )


__all__ = ["DiscourseStructureBuilderV351"]
