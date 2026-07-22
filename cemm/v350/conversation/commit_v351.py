"""Stage-13 bounded session-memory commit for Phase 11/12 conversational state."""
from __future__ import annotations

import unicodedata

from ..csir.canonical_v351 import semantic_fingerprint
from ..epistemic.model import WorkingBeliefDelta
from ..grounding.model import CandidateOrigin, DiscourseAnchor, GroundingFactorKind
from ..orchestration import StageExecutionStatus, StageOutcome
from ..runtime_abi import artifact_ref
from ..schema.model import semantic_fingerprint as runtime_fingerprint
from .session_memory import ReferenceSurfaceEntry, SessionEventEntry, SessionMemoryCommit, SessionMemoryConflict


class SessionMemoryCommitCoordinatorV351:
    RUNTIME_ABI = "v351"
    SERVICE_KIND = "session_memory_commit_coordinator"

    def __init__(self, session_memory) -> None:
        self.session_memory = session_memory

    @staticmethod
    def _discourse_anchors(cycle, discourse, turn_index: int):
        if discourse is None:
            return ()
        substrate = discourse.substrate
        referent_by_ref = {item.referent_ref: item for item in substrate.referents}
        role_refs_by_referent = {}
        for role in substrate.participant_roles:
            role_refs_by_referent.setdefault(role.referent_ref, set()).add(role.role_ref)
        for chain in substrate.mention_chains:
            if chain.resolved_referent_ref is None:
                continue
            evidence = tuple(sorted(set(chain.proof_refs))) or (cycle.cycle_ref,)
            referent = referent_by_ref.get(chain.resolved_referent_ref)
            type_refs = () if referent is None else tuple(sorted(pin.ref for pin in referent.exact_type_pins))
            yield DiscourseAnchor(
                anchor_ref="discourse-anchor:session:" + runtime_fingerprint(
                    "session-discourse-anchor", (cycle.context_ref, chain.resolved_referent_ref), 24,
                ),
                referent_ref=chain.resolved_referent_ref, context_ref=cycle.context_ref,
                salience=0.85, turn_index=max(0, turn_index),
                role_refs=tuple(sorted(role_refs_by_referent.get(chain.resolved_referent_ref, ()))),
                type_refs=type_refs, evidence_refs=evidence,
            )

    @staticmethod
    def _reference_surfaces(cycle, turn_index: int) -> tuple[ReferenceSurfaceEntry, ...]:
        grounding = cycle.artifacts.get("grounding_candidates")
        result = None if grounding is None else getattr(grounding, "result", None)
        discourse = cycle.artifacts.get("discourse_structures")
        if result is None or discourse is None:
            return ()
        # Stage-8 resolved mention chains are the authority boundary for reusable reference
        # surfaces.  A Stage-3 locally preferred candidate is only a soft prior and may not
        # teach the realizer a name for an ambiguous referent.
        resolved = {
            mention_ref: chain.resolved_referent_ref
            for chain in discourse.substrate.mention_chains
            if chain.resolved_referent_ref is not None
            for mention_ref in chain.mention_refs
        }
        candidates = {}
        for candidate in result.candidates:
            if resolved.get(candidate.mention_ref) != candidate.target_ref:
                continue
            candidates.setdefault(candidate.mention_ref, []).append(candidate)
        values = []
        for mention in result.mentions:
            target = resolved.get(mention.mention_ref)
            if not target or not mention.surface.strip():
                continue
            supporting = tuple(candidates.get(mention.mention_ref, ()))
            safe = any(
                candidate.origin is CandidateOrigin.PROVISIONAL
                or candidate.provisional
                or any(factor.factor_kind is GroundingFactorKind.IDENTITY for factor in candidate.factors)
                for candidate in supporting
            )
            if not safe:
                # Prevent participant pronouns/deictics from becoming accidental names.
                continue
            normalized = unicodedata.normalize("NFKC", mention.surface).casefold()
            values.append(ReferenceSurfaceEntry(
                reference_ref="reference-surface:" + runtime_fingerprint(
                    "reference-surface", (cycle.context_ref, target, normalized), 24,
                ),
                referent_ref=target, surface=mention.surface,
                normalized_key=normalized, language_tag=(cycle.target_language or "en"),
                context_ref=cycle.context_ref, evidence_refs=tuple(mention.evidence_refs),
                turn_index=max(0, turn_index), safe_for_realization=True,
            ))
        # One latest surface per exact target+normalization identity in this turn.
        dedup = {item.reference_ref: item for item in values}
        return tuple(dedup[key] for key in sorted(dedup))

    @staticmethod
    def _events(cycle, turn_index: int) -> tuple[SessionEventEntry, ...]:
        values = []
        frame = cycle.artifacts.get("participant_frame")
        source_refs = () if frame is None else (frame.input_speaker_ref,)
        for event in tuple(cycle.artifacts.get("events", ()) or ()):
            values.append(SessionEventEntry(
                event_ref=event.event_ref, graph=event.graph, context_ref=event.context_ref,
                permission_ref=cycle.permission_ref, source_refs=source_refs,
                evidence_refs=tuple(event.evidence_refs), proof_refs=tuple(event.proof_refs),
                support=float(event.support), turn_index=max(0, turn_index),
            ))
        return tuple(values)

    def commit(self, *, cycle, capability, store, effect_store, semantic_capabilities):
        del store, effect_store, semantic_capabilities
        delta = cycle.artifacts.get("working_belief_delta")
        if not isinstance(delta, WorkingBeliefDelta):
            raise TypeError("Stage 13 session commit requires WorkingBeliefDelta")
        current = self.session_memory.snapshot(cycle.context_ref, cycle.permission_ref)
        if current.revision != delta.base_session_revision:
            return StageOutcome(StageExecutionStatus.DEFERRED, frontier_refs=("frontier:commit:session-memory-cas-conflict",))

        existing = {
            (semantic_fingerprint(item.graph), tuple(sorted(item.source_refs)))
            for item in current.active_beliefs
        }
        additions = tuple(
            item for item in delta.additions
            if (semantic_fingerprint(item.graph), tuple(sorted(item.source_refs))) not in existing
        )
        answered_queries = {
            item.query_ref for item in cycle.artifacts.get("query_results", ())
            if getattr(item, "answered", False)
        }
        discourse = cycle.artifacts.get("discourse_structures")
        open_questions = () if discourse is None else tuple(
            item for item in discourse.open_questions if item.query_ref not in answered_queries
        )
        clarifications = () if discourse is None else tuple(discourse.clarification_targets)
        common_ground = () if discourse is None else tuple(discourse.common_ground_proposals)
        next_turn = current.revision + 1
        discourse_anchors = tuple(self._discourse_anchors(cycle, discourse, next_turn))
        reference_surfaces = self._reference_surfaces(cycle, next_turn)
        events = self._events(cycle, next_turn)
        has_change = bool(
            additions or delta.retract_claim_refs or delta.supersede_claims or open_questions
            or answered_queries or clarifications or common_ground or discourse_anchors or reference_surfaces or events
        )
        if not has_change:
            return StageOutcome(
                StageExecutionStatus.PERFORMED,
                artifacts={
                    "commit_receipts": (), "committed_read_generation": capability.read_generation,
                    "session_memory_revision": current.revision,
                },
            )

        proposal = SessionMemoryCommit(
            commit_ref=artifact_ref(
                "session-memory-commit", cycle.cycle_ref, tuple(item.belief_ref for item in additions),
                delta.retract_claim_refs, delta.supersede_claims,
            ),
            expected_revision=current.revision, additions=additions,
            retract_claim_refs=delta.retract_claim_refs, supersede_claims=delta.supersede_claims,
            open_questions=open_questions, answered_query_refs=tuple(sorted(answered_queries)),
            clarifications=clarifications, common_ground=common_ground,
            discourse_anchors=discourse_anchors, reference_surfaces=reference_surfaces, events=events,
            evidence_refs=delta.evidence_refs,
        )
        try:
            receipt = self.session_memory.commit(cycle.context_ref, cycle.permission_ref, proposal)
        except SessionMemoryConflict:
            return StageOutcome(StageExecutionStatus.DEFERRED, frontier_refs=("frontier:commit:session-memory-cas-conflict",))
        return StageOutcome(
            StageExecutionStatus.PERFORMED,
            artifacts={
                "commit_receipts": (receipt,), "committed_read_generation": capability.read_generation,
                "session_memory_revision": receipt.revision_after,
            },
        )


__all__ = ["SessionMemoryCommitCoordinatorV351"]
