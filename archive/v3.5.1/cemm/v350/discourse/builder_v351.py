"""Stage-8 grounded discourse/proposition/event/query/correction re-abstraction.

Classification is structural or exact-authority driven.  No raw phrase handlers, no
subject/object ontology, and no collapse of hypothetical/reported context into actual.
"""
from __future__ import annotations

from dataclasses import replace

from ..conversation.session_memory import ClarificationMemory, OpenQuestionMemory
from ..csir.canonical_v351 import semantic_fingerprint
from ..csir.model import CSIRGraph, CSIRNodeKind, SemanticVariable, TermKind
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
from ..storage.model import RecordKind
from .context_v351 import semantic_contexts_for_graph
from .minimum_authority_v351 import compile_minimum_discourse_authority
from .model import (
    DiscourseAct, DiscourseActAuthority, DiscourseActKind, DiscourseAuthorityMap,
    DiscourseStructureBatch, EventOccurrenceV351,
)


class DiscourseStructureBuilderV351:
    RUNTIME_ABI = "v351"
    SERVICE_KIND = "discourse_structure_builder"

    def __init__(self, session_memory, *, authority_map: DiscourseAuthorityMap | None = None) -> None:
        self.session_memory = session_memory
        self._authority_map_explicit = authority_map is not None
        self.authority_map = (
            authority_map if authority_map is not None
            else compile_minimum_discourse_authority().authority_map
        )

    def _effective_authority_map(self, snapshot) -> DiscourseAuthorityMap:
        """Use candidate default mappings only after exact promotion into this generation."""
        if self._authority_map_explicit:
            self.authority_map.validate(snapshot)
            return self.authority_map
        definition_keys = set(snapshot.definition_index)
        # Candidate defaults activate per exact promoted definition, never all-or-nothing.
        # This preserves the anti-overarching-gate invariant while still forbidding any
        # name/ref/floating fallback.
        active = DiscourseAuthorityMap(
            authorities=tuple(
                item for item in self.authority_map.authorities
                if item.definition_pin.key in definition_keys
            ),
            event_authorities=tuple(
                item for item in self.authority_map.event_authorities
                if item.definition_pin.key in definition_keys
            ),
        )
        if active.authorities or active.event_authorities:
            active.validate(snapshot)
        return active

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
    def _is_durable(store, ref: str) -> bool:
        try:
            return store.get_record(RecordKind.REFERENT, ref) is not None
        except Exception:
            return False

    @classmethod
    def _referent_substrate(cls, cycle, store):
        frame = cycle.artifacts["participant_frame"]
        grounding = cycle.artifacts.get("grounding_candidates")
        context = SemanticContext(
            context_ref=cycle.context_ref, context_kind="actual",
            permission_ref=cycle.permission_ref, evidence_refs=tuple(frame.identity_evidence_refs),
        )
        referent_refs = {
            frame.system_ref, frame.input_speaker_ref,
            *frame.input_addressee_refs, *frame.response_audience_refs,
        }
        mentions = []
        identities = []
        chains = []
        selected = {}  # Stage-3 local grounding prior only; never authoritative identity.
        ambiguous = set()
        result = None if grounding is None else getattr(grounding, "result", None)
        if result is not None:
            ambiguous = set(result.ambiguous_mention_refs)
            if result.selected_assignment_ref is not None:
                assignment = next(
                    (item for item in result.assignments if item.assignment_ref == result.selected_assignment_ref), None,
                )
                if assignment is not None:
                    selected = dict(assignment.mention_to_target)
            candidates_by_mention = {}
            for candidate in result.candidates:
                candidates_by_mention.setdefault(candidate.mention_ref, []).append(candidate)
                referent_refs.add(candidate.target_ref)
            for item in result.mentions:
                identity_refs = []
                mention_candidates = tuple(candidates_by_mention.get(item.mention_ref, ()))
                unique_targets = {candidate.target_ref for candidate in mention_candidates}
                structurally_singular = len(unique_targets) == 1 and item.mention_ref not in ambiguous
                for candidate in mention_candidates:
                    status = IdentityCandidateStatus.CANDIDATE
                    if structurally_singular:
                        status = (
                            IdentityCandidateStatus.PROVISIONAL
                            if bool(getattr(candidate, "provisional", False)) else IdentityCandidateStatus.RESOLVED
                        )
                    elif selected.get(item.mention_ref) == candidate.target_ref:
                        # Preserve the local grounding preference only as a provisional prior.
                        # Final semantic selection belongs to Stage 6/7, not Stage 3.
                        status = IdentityCandidateStatus.PROVISIONAL
                    identity_ref = "identity-candidate:" + runtime_fingerprint(
                        "identity-candidate", (item.mention_ref, candidate.target_ref, candidate.candidate_ref), 24,
                    )
                    identity_refs.append(identity_ref)
                    identities.append(IdentityCandidate(
                        candidate_ref=identity_ref, mention_ref=item.mention_ref,
                        referent_ref=candidate.target_ref, status=status,
                        support=max(0.0, min(1.0, 0.5 + candidate.local_score / 20.0)),
                        evidence_refs=tuple(sorted({ref for factor in candidate.factors for ref in factor.evidence_refs})) or tuple(item.evidence_refs),
                        constraint_refs=tuple(sorted({factor.factor_ref for factor in candidate.factors if factor.hard})),
                    ))
                mentions.append(Mention(
                    mention_ref=item.mention_ref, source_ref=item.source_ref,
                    span_start=item.span.start, span_end=item.span.end,
                    form_candidate_refs=(), identity_candidate_refs=tuple(identity_refs),
                ))
                if identity_refs:
                    chains.append(MentionChain(
                        chain_ref="mention-chain:" + runtime_fingerprint(
                            "mention-chain", (item.mention_ref, tuple(identity_refs)), 20,
                        ),
                        mention_refs=(item.mention_ref,), referent_candidate_refs=tuple(identity_refs),
                        resolved_referent_ref=(
                            next(iter(unique_targets)) if structurally_singular else None
                        ),
                        proof_refs=tuple(item.evidence_refs),
                    ))
        referents = tuple(
            Referent(
                referent_ref=ref, context_refs=(cycle.context_ref,), permission_ref=cycle.permission_ref,
                evidence_refs=tuple(frame.identity_evidence_refs) or (cycle.cycle_ref,),
                durable_identity=cls._is_durable(store, ref),
            )
            for ref in sorted(referent_refs)
        )
        participant_roles = (
            ParticipantRole(RuntimeParticipantRole.SYSTEM.value, frame.system_ref, frame.frame_ref, tuple(frame.identity_evidence_refs) or (cycle.cycle_ref,)),
            ParticipantRole(RuntimeParticipantRole.INPUT_SPEAKER.value, frame.input_speaker_ref, frame.frame_ref, tuple(frame.identity_evidence_refs) or (cycle.cycle_ref,)),
            *tuple(
                ParticipantRole(RuntimeParticipantRole.INPUT_ADDRESSEE.value, ref, frame.frame_ref, tuple(frame.identity_evidence_refs) or (cycle.cycle_ref,))
                for ref in frame.input_addressee_refs
            ),
        )
        return (context,), referents, tuple(mentions), tuple(identities), tuple(chains), participant_roles

    def _events(
        self, graph: CSIRGraph, *, authority_map: DiscourseAuthorityMap, context_ref: str,
        evidence_refs: tuple[str, ...], support: float, derivation_ref: str,
    ):
        event_map = authority_map.events_by_definition
        values = []
        for application in graph.applications:
            authority = event_map.get(application.predicate_pin.key)
            if authority is None:
                continue
            participants = []
            allowed = {pin.key: pin for pin in authority.participant_port_pins}
            for binding in graph.bindings_for(application.application_ref):
                if allowed and binding.port_pin.key not in allowed:
                    continue
                for filler in binding.fillers:
                    node = graph.node(filler)
                    if node is not None and getattr(node, "term_kind", None) is TermKind.REFERENT and node.identity_ref:
                        participants.append((binding.port_pin, node.identity_ref))
            # Multiple fillers for one role are represented in CSIR; event summary keeps a
            # deterministic first participant per exact role and leaves full graph intact.
            by_port = {}
            for pin, ref in participants:
                by_port.setdefault(pin.key, (pin, ref))
            values.append(EventOccurrenceV351(
                event_ref="event:" + runtime_fingerprint(
                    "event-occurrence-v351", (derivation_ref, application.application_ref, context_ref), 24,
                ),
                graph=graph, definition_pin=application.predicate_pin, context_ref=context_ref,
                participant_refs=tuple(by_port[key] for key in sorted(by_port)),
                evidence_refs=evidence_refs, proof_refs=(derivation_ref,),
                support=max(0.0, min(1.0, support)),
            ))
        return tuple(values)

    def build(self, *, cycle, capability, store, effect_store, semantic_capabilities):
        del capability, effect_store, semantic_capabilities
        attractors = cycle.artifacts["semantic_attractors"]
        if not isinstance(attractors, SemanticAttractorSet):
            raise TypeError("Stage 8 requires SemanticAttractorSet")
        semantic_authority = cycle.artifacts["semantic_authority_snapshot_v351"]
        authority_map = self._effective_authority_map(semantic_authority)
        frame = cycle.artifacts["participant_frame"]
        contexts, referents, mentions, identities, chains, participant_roles = self._referent_substrate(cycle, store)
        contexts_by_ref = {item.context_ref: item for item in contexts}

        propositions = []
        claims = []
        events = []
        queries = []
        corrections = []
        acts = []
        open_questions = []
        clarifications = []
        frontiers = []
        source_evidence = tuple(sorted({
            ref for envelope in cycle.artifacts.get("evidence_envelopes", ())
            for ref in (envelope.evidence_ref, *envelope.evidence_refs)
        })) or (cycle.cycle_ref,)

        partial_fp = (
            None if attractors.partial_meaning is None
            else semantic_fingerprint(attractors.partial_meaning)
        )
        semantic_items = [
            (
                item.graph, item.support, item.attractor_ref,
                partial_fp is not None and item.semantic_fingerprint == partial_fp,
            )
            for item in attractors.attractors
        ]
        if attractors.partial_meaning is not None and not any(
            semantic_fingerprint(item[0]) == partial_fp for item in semantic_items
        ):
            semantic_items.append((attractors.partial_meaning, 0.0, "partial:" + partial_fp[:24], True))

        all_gaps = []
        for semantic_graph, semantic_support, derivation_ref, is_partial in semantic_items:
            app, authority = self._root_authority(semantic_graph, authority_map)
            content = self._content_graph(semantic_graph, app, authority)
            graph_contexts, proposition_context_ref, _context_kind = semantic_contexts_for_graph(
                content, cycle_context_ref=cycle.context_ref, permission_ref=cycle.permission_ref,
                evidence_refs=source_evidence,
            )
            for item in graph_contexts:
                contexts_by_ref[item.context_ref] = item
            act_kind = authority.act_kind if authority is not None else (
                DiscourseActKind.QUERY if any(variable.open_purpose == "query" for variable in content.variables)
                else DiscourseActKind.ASSERTION
            )
            prop_ref = "proposition:" + semantic_fingerprint(content)
            proposition = Proposition(
                proposition_ref=prop_ref, content=content, context_ref=proposition_context_ref,
                source_refs=(frame.input_speaker_ref,), evidence_refs=source_evidence,
            )
            propositions.append(proposition)
            events.extend(self._events(
                content, authority_map=authority_map, context_ref=proposition_context_ref,
                evidence_refs=source_evidence, support=semantic_support, derivation_ref=derivation_ref,
            ))
            act_ref = "discourse-act:" + runtime_fingerprint(
                "discourse-act", (cycle.cycle_ref, prop_ref, act_kind.value), 24,
            )
            act_targets = ()

            if act_kind is DiscourseActKind.QUERY:
                variables = tuple(variable for variable in content.variables if variable.open_purpose == "query")
                restriction = content
                if not variables:
                    truth = SemanticVariable(
                        variable_ref="truth:" + runtime_fingerprint("truth-gap", prop_ref, 16),
                        allowed_kinds=frozenset({CSIRNodeKind.TERM}), scope_ref=proposition_context_ref,
                        open_purpose="query",
                    )
                    variables = (truth,)
                    restriction = replace(content, variables=(*content.variables, truth), root_refs=(*content.root_refs, truth.node_ref))
                gaps = []
                for variable in variables:
                    gap = InformationGap(
                        gap_ref="gap:" + runtime_fingerprint(
                            "information-gap", (cycle.cycle_ref, prop_ref, variable.variable_ref), 20,
                        ),
                        kind=(GapKind.PROPOSITION_TRUTH if variable.variable_ref.startswith("truth:") else GapKind.OTHER),
                        variable_ref=variable.node_ref, restriction_graph=restriction,
                        evidence_refs=source_evidence,
                    )
                    gaps.append(gap); all_gaps.append(gap)
                projection = AnswerProjection(
                    projection_ref="answer-projection:" + runtime_fingerprint(
                        "answer-projection", (prop_ref, variables[0].variable_ref), 20,
                    ),
                    requested_variable_ref=variables[0].node_ref,
                )
                query = Query(
                    query_ref="query:" + runtime_fingerprint(
                        "query", (cycle.cycle_ref, prop_ref, tuple(g.gap_ref for g in gaps)), 24,
                    ),
                    query_graph=restriction, gap_refs=tuple(gap.gap_ref for gap in gaps),
                    answer_projection=projection, speaker_ref=frame.input_speaker_ref,
                    audience_refs=frame.input_addressee_refs, context_ref=proposition_context_ref,
                    evidence_refs=source_evidence,
                )
                queries.append(query)
                open_questions.append(OpenQuestionMemory(
                    question_ref="open-question:" + runtime_fingerprint("open-question", query.query_ref, 20),
                    query_ref=query.query_ref, context_ref=proposition_context_ref,
                    speaker_ref=frame.input_speaker_ref, target_refs=(), evidence_refs=source_evidence,
                ))
                act_targets = (query.query_ref,)
            elif is_partial:
                frontier = "frontier:discourse:partial-meaning:" + prop_ref
                frontiers.append(frontier)
                # Partial cognition is valid cognition, but it must not silently disappear at
                # the discourse boundary.  Preserve the known proposition and expose an exact
                # clarification target so Phase-12 can respond without fabricating certainty.
                clarifications.append(ClarificationMemory(
                    clarification_ref="clarification:" + runtime_fingerprint(
                        "clarification:partial-meaning", (cycle.cycle_ref, prop_ref, frontier), 20,
                    ),
                    target_ref=prop_ref, reason_ref="partial_meaning_requires_clarification",
                    context_ref=proposition_context_ref, evidence_refs=source_evidence,
                ))
                act_kind = DiscourseActKind.OTHER
                act_targets = (prop_ref,)
            else:
                claim_ref = "claim:" + runtime_fingerprint(
                    "claim-occurrence", (cycle.cycle_ref, prop_ref, frame.input_speaker_ref), 24,
                )
                claim = Claim(
                    claim_ref=claim_ref, proposition_ref=prop_ref, claimant_ref=frame.input_speaker_ref,
                    audience_refs=frame.input_addressee_refs, source_context_ref=cycle.context_ref,
                    reported_context_ref=proposition_context_ref, evidence_refs=source_evidence,
                    commitment_strength=max(0.0, min(1.0, semantic_support)),
                )
                claims.append(claim); act_targets = (claim_ref,)
                if act_kind in {DiscourseActKind.CORRECTION, DiscourseActKind.RETRACTION}:
                    target = self.session_memory.latest_claim_ref(
                        cycle.context_ref, cycle.permission_ref, source_ref=frame.input_speaker_ref,
                    )
                    if target is None:
                        frontier = "frontier:discourse:correction-target-unresolved:" + claim_ref
                        frontiers.append(frontier)
                        clarifications.append(ClarificationMemory(
                            clarification_ref="clarification:" + runtime_fingerprint("clarification", (claim_ref, frontier), 20),
                            target_ref=claim_ref, reason_ref="correction_target_unresolved",
                            context_ref=cycle.context_ref, evidence_refs=source_evidence,
                        ))
                    else:
                        corrections.append(CorrectionRetraction(
                            correction_ref="correction:" + runtime_fingerprint(
                                "correction", (cycle.cycle_ref, target, prop_ref), 24,
                            ),
                            kind=(CorrectionKind.RETRACT if act_kind is DiscourseActKind.RETRACTION else CorrectionKind.SUPERSEDE),
                            source_ref=frame.input_speaker_ref, target_ref=target,
                            replacement_ref=(None if act_kind is DiscourseActKind.RETRACTION else prop_ref),
                            context_ref=cycle.context_ref, evidence_refs=source_evidence,
                        ))

            acts.append(DiscourseAct(
                act_ref=act_ref, act_kind=act_kind, semantic_ref=prop_ref,
                speaker_ref=frame.input_speaker_ref, audience_refs=frame.input_addressee_refs,
                context_ref=proposition_context_ref, evidence_refs=source_evidence,
                authority_pin=None if authority is None else authority.definition_pin,
                target_refs=act_targets,
            ))

        substrate = GroundedSemanticSubstrate(
            substrate_ref=artifact_ref("grounded-semantic-substrate", cycle.cycle_ref),
            contexts=tuple(contexts_by_ref[key] for key in sorted(contexts_by_ref)),
            referents=referents, identity_candidates=identities, participant_roles=participant_roles,
            mentions=mentions, mention_chains=chains, propositions=tuple(propositions), claims=tuple(claims),
            gaps=tuple(all_gaps), queries=tuple(queries), corrections=tuple(corrections),
            frontier_refs=tuple(sorted(set(frontiers))),
        )
        batch = DiscourseStructureBatch(
            batch_ref=artifact_ref("discourse-structures", cycle.cycle_ref), substrate=substrate,
            acts=tuple(acts), events=tuple(events), open_questions=tuple(open_questions),
            clarification_targets=tuple(clarifications), frontier_refs=tuple(sorted(set(frontiers))),
        )
        return StageOutcome(
            StageExecutionStatus.PERFORMED,
            artifacts={
                "discourse_structures": batch, "propositions": tuple(propositions), "claims": tuple(claims),
                "events": tuple(events), "queries": tuple(queries), "corrections": tuple(corrections), "commitments": (),
            },
            frontier_refs=tuple(sorted(set(frontiers))),
        )


__all__ = ["DiscourseStructureBuilderV351"]
