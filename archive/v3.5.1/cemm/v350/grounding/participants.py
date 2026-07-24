"""ParticipantFrame -> discourse-anchor bridge for ordinary text grounding."""
from __future__ import annotations

from ..runtime_kernel import ParticipantFrame, ParticipantRole
from ..schema.model import semantic_fingerprint
from .model import DiscourseAnchor


def participant_frame_anchors(
    frame: ParticipantFrame | None,
    *,
    store,
    snapshot,
) -> tuple[DiscourseAnchor, ...]:
    if frame is None or not frame.identity_evidence_refs:
        return ()
    store.assert_snapshot(snapshot)

    roles_by_ref: dict[str, set[str]] = {}

    def add(ref: str, role: ParticipantRole) -> None:
        roles_by_ref.setdefault(ref, set()).add(role.value)

    add(frame.system_ref, ParticipantRole.SYSTEM)
    add(frame.input_speaker_ref, ParticipantRole.INPUT_SPEAKER)
    for ref in frame.input_addressee_refs:
        add(ref, ParticipantRole.INPUT_ADDRESSEE)
    for ref in frame.response_audience_refs:
        add(ref, ParticipantRole.RESPONSE_AUDIENCE)

    anchors = []
    for referent_ref, roles in sorted(roles_by_ref.items()):
        stored = store.repositories.referents.get(
            referent_ref, snapshot=snapshot
        )
        if stored is None:
            # Grounding never fabricates a durable participant referent.
            continue
        type_refs = tuple(
            sorted(
                {
                    *stored.payload.type_refs,
                    *(
                        item.type_schema_ref
                        for item in store.repositories.referents.type_assertions(
                            referent_ref,
                            context_ref=frame.context_ref,
                            snapshot=snapshot,
                        )
                    ),
                }
            )
        )
        anchors.append(
            DiscourseAnchor(
                anchor_ref="discourse-anchor:participant:"
                + semantic_fingerprint(
                    "participant-discourse-anchor",
                    (
                        frame.frame_ref,
                        referent_ref,
                        tuple(sorted(roles)),
                        frame.context_ref,
                    ),
                    24,
                ),
                referent_ref=referent_ref,
                context_ref=frame.context_ref,
                salience=1.0,
                turn_index=0,
                role_refs=tuple(sorted(roles)),
                type_refs=type_refs,
                evidence_refs=frame.identity_evidence_refs,
            )
        )
    return tuple(anchors)
