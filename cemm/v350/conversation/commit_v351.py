"""Stage-13 session-memory commit coordinator for Phase-11 conversational state.

This coordinator commits only session/discourse state.  It deliberately does not promote
facts to global/world semantic authority and does not perform durable SemanticStore writes;
a later/full durable commit coordinator may replace it without changing Phase-11 query or
admission contracts.
"""
from __future__ import annotations

from ..csir.canonical_v351 import semantic_fingerprint
from ..epistemic.model import WorkingBeliefDelta
from ..orchestration import StageExecutionStatus, StageOutcome
from ..runtime_abi import artifact_ref
from ..schema.model import semantic_fingerprint as runtime_fingerprint
from .session_memory import SessionMemoryCommit, SessionMemoryConflict
from ..grounding.model import DiscourseAnchor


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
        evidence_by_mention = {item.mention_ref: () for item in substrate.mentions}
        for chain in substrate.mention_chains:
            if chain.resolved_referent_ref is None:
                continue
            evidence = tuple(sorted(set(chain.proof_refs))) or (cycle.cycle_ref,)
            referent = referent_by_ref.get(chain.resolved_referent_ref)
            type_refs = () if referent is None else tuple(sorted(pin.ref for pin in referent.exact_type_pins))
            yield DiscourseAnchor(
                anchor_ref="discourse-anchor:session:" + runtime_fingerprint(
                    "session-discourse-anchor",
                    (cycle.context_ref, chain.resolved_referent_ref),
                    24,
                ),
                referent_ref=chain.resolved_referent_ref,
                context_ref=cycle.context_ref,
                salience=0.85,
                turn_index=max(0, turn_index),
                role_refs=tuple(sorted(role_refs_by_referent.get(chain.resolved_referent_ref, ()))),
                type_refs=type_refs,
                evidence_refs=evidence,
            )

    def commit(self, *, cycle, capability, store, effect_store, semantic_capabilities):
        del store, effect_store, semantic_capabilities
        delta = cycle.artifacts.get("working_belief_delta")
        if not isinstance(delta, WorkingBeliefDelta):
            raise TypeError("Stage 13 session commit requires WorkingBeliefDelta")
        current = self.session_memory.snapshot(cycle.context_ref, cycle.permission_ref)
        if current.revision != delta.base_session_revision:
            return StageOutcome(
                StageExecutionStatus.DEFERRED,
                frontier_refs=("frontier:commit:session-memory-cas-conflict",),
            )

        # Change-triggered persistence: repeated semantically-identical participant facts
        # from the same source do not create one belief record per message.
        existing = {
            (
                semantic_fingerprint(item.graph),
                tuple(sorted(item.source_refs)),
            )
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
        discourse_anchors = tuple(self._discourse_anchors(cycle, discourse, current.revision + 1))
        has_change = bool(
            additions or delta.retract_claim_refs or delta.supersede_claims
            or open_questions or clarifications or common_ground or discourse_anchors
        )
        if not has_change:
            return StageOutcome(
                StageExecutionStatus.PERFORMED,
                artifacts={
                    "commit_receipts": (),
                    "committed_read_generation": capability.read_generation,
                    "session_memory_revision": current.revision,
                },
            )

        proposal = SessionMemoryCommit(
            commit_ref=artifact_ref(
                "session-memory-commit", cycle.cycle_ref,
                tuple(item.belief_ref for item in additions),
                delta.retract_claim_refs, delta.supersede_claims,
            ),
            expected_revision=current.revision,
            additions=additions,
            retract_claim_refs=delta.retract_claim_refs,
            supersede_claims=delta.supersede_claims,
            open_questions=open_questions,
            clarifications=clarifications,
            common_ground=common_ground,
            discourse_anchors=discourse_anchors,
            evidence_refs=delta.evidence_refs,
        )
        try:
            receipt = self.session_memory.commit(
                cycle.context_ref, cycle.permission_ref, proposal
            )
        except SessionMemoryConflict:
            return StageOutcome(
                StageExecutionStatus.DEFERRED,
                frontier_refs=("frontier:commit:session-memory-cas-conflict",),
            )
        return StageOutcome(
            StageExecutionStatus.PERFORMED,
            artifacts={
                "commit_receipts": (receipt,),
                "committed_read_generation": capability.read_generation,
                "session_memory_revision": receipt.revision_after,
            },
        )


__all__ = ["SessionMemoryCommitCoordinatorV351"]
