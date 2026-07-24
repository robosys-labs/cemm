"""Cycle/session discourse-anchor bridge for Phase-11 grounding continuity.

Anchors are evidence-bearing discourse state, never durable referent creation or semantic
authority.  Participant-frame roles are supplied structurally by the cycle/session frame;
no pronoun word or language form is inspected here.
"""
from __future__ import annotations

from ..grounding.model import DiscourseAnchor
from ..runtime_kernel import ParticipantFrame, ParticipantRole
from ..schema.model import semantic_fingerprint


def participant_frame_session_anchors(
    frame: ParticipantFrame | None,
    *,
    turn_index: int = 0,
) -> tuple[DiscourseAnchor, ...]:
    if frame is None or not frame.identity_evidence_refs:
        return ()
    roles_by_ref: dict[str, set[str]] = {}

    def add(ref: str, role: ParticipantRole) -> None:
        roles_by_ref.setdefault(ref, set()).add(role.value)

    add(frame.system_ref, ParticipantRole.SYSTEM)
    add(frame.input_speaker_ref, ParticipantRole.INPUT_SPEAKER)
    for ref in frame.input_addressee_refs:
        add(ref, ParticipantRole.INPUT_ADDRESSEE)
    for ref in frame.response_audience_refs:
        add(ref, ParticipantRole.RESPONSE_AUDIENCE)

    return tuple(
        DiscourseAnchor(
            anchor_ref="discourse-anchor:session-participant:"
            + semantic_fingerprint(
                "session-participant-discourse-anchor",
                (frame.frame_ref, referent_ref, tuple(sorted(roles)), frame.context_ref),
                24,
            ),
            referent_ref=referent_ref,
            context_ref=frame.context_ref,
            salience=1.0,
            turn_index=max(0, int(turn_index)),
            role_refs=tuple(sorted(roles)),
            type_refs=(),
            evidence_refs=frame.identity_evidence_refs,
        )
        for referent_ref, roles in sorted(roles_by_ref.items())
    )


__all__ = ["participant_frame_session_anchors"]
