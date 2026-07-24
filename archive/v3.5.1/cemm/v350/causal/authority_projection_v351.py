"""Deterministic Stage-0 projection of promoted Phase-15/16 operational authority.

The durable authority store is canonical for promotion lifecycle and exact record revisions.
`AuthoritySnapshotV351` is the cycle-local split authority view used by the v3.5.1 kernel.
This module bridges only *already active, competence-gated, explicitly per-use-authorized*
rich state/causal records into that view. It never promotes candidates or synthesizes a new
permission: the projected ALLOW axes are exactly those embedded by the reviewed Phase-14
promotion transaction in ``authorized_use_operations``.
"""
from __future__ import annotations

from dataclasses import replace

from ..csir.authority_v351 import AuthoritySnapshotV351, UseAuthorization
from ..csir.model import ExactAuthorityPin
from ..schema.model import semantic_fingerprint
from ..storage.model import RecordKind
from ..state.capability_v351 import CapabilityDependencyGraph
from ..state.model_v351 import TransitionMechanismV351


def _authorization_pin(target: ExactAuthorityPin, operation: str, payload) -> ExactAuthorityPin:
    return ExactAuthorityPin(
        "use_authorization",
        "cemm:v351:state-causal-authority",
        f"{target.ref}:use:{operation}",
        target.revision,
        semantic_fingerprint("state-causal-use-authorization-v351", payload, 64),
        target.scope_ref,
    )


def _active_rich_records(store, kind, expected_type, identity_attr):
    selected = {}
    for stored in store.records(kind, all_revisions=True):
        payload = stored.payload
        if not isinstance(payload, expected_type) or not bool(getattr(payload, "executable", False)):
            continue
        if store.is_invalidated(kind, stored.record_ref, stored.revision):
            continue
        identity = str(getattr(payload, identity_attr))
        current = selected.get(identity)
        if current is None or int(payload.revision) > int(current.revision):
            selected[identity] = payload
    return tuple(selected[key] for key in sorted(selected))


def project_state_causal_authority(store, snapshot: AuthoritySnapshotV351) -> AuthoritySnapshotV351:
    """Project active promoted state/causal operational records into one pinned snapshot.

    Existing explicit authorizations are preserved. A pre-existing DENY is never removed and
    therefore continues to dominate the projected ALLOW when `require_exact_use` evaluates it.
    """
    if not isinstance(snapshot, AuthoritySnapshotV351):
        raise TypeError("state/causal authority projection requires AuthoritySnapshotV351")

    before = store.current_authority_snapshot()
    if (before.generation, before.authority_fingerprint) != (
        snapshot.generation, snapshot.authority_fingerprint
    ):
        raise ValueError("state/causal authority projection generation differs from pinned cycle")

    records = (
        *_active_rich_records(
            store, RecordKind.TRANSITION_CONTRACT, TransitionMechanismV351, "mechanism_ref"
        ),
        *_active_rich_records(
            store, RecordKind.CAPABILITY_DEPENDENCY, CapabilityDependencyGraph, "graph_ref"
        ),
    )
    after_read = store.current_authority_snapshot()
    if (after_read.generation, after_read.authority_fingerprint) != (
        before.generation, before.authority_fingerprint
    ):
        raise ValueError("authority generation changed during state/causal authority projection")
    if not records:
        return snapshot

    auxiliary = {pin.key: pin for pin in snapshot.auxiliary_exact_pins}
    authorizations = {item.authorization_pin.key: item for item in snapshot.use_authorizations}
    for record in records:
        target = record.authority_pin
        auxiliary[target.key] = target
        operations = tuple(sorted(
            {str(getattr(item, "value", item)) for item in record.authorized_use_operations}
        ))
        if not operations:
            # `executable` should already forbid this; retain fail-closed defense at projection.
            continue
        context_scopes = tuple(getattr(record, "context_scopes", ()) or ())
        permission = str(getattr(record, "permission_ref", "conversation") or "conversation")
        evidence_refs = tuple(sorted(set((
            *tuple(getattr(record, "evidence_refs", ()) or ()),
            *(pin.ref for pin in tuple(getattr(record, "competence_case_pins", ()) or ())),
        ))))
        for operation in operations:
            payload = (
                target.key,
                operation,
                "allow",
                tuple(sorted(context_scopes)),
                permission,
                evidence_refs,
            )
            auth_pin = _authorization_pin(target, operation, payload)
            projected = UseAuthorization(
                authorization_pin=auth_pin,
                target_pin=target,
                operation=operation,
                decision="allow",
                context_scopes=context_scopes,
                permission_scopes=(permission,),
                evidence_refs=evidence_refs,
            )
            prior = authorizations.get(auth_pin.key)
            if prior is not None and prior != projected:
                raise ValueError("state/causal use-authorization exact identity collision")
            authorizations[auth_pin.key] = projected

    return replace(
        snapshot,
        use_authorizations=tuple(authorizations[key] for key in sorted(authorizations)),
        auxiliary_exact_pins=tuple(auxiliary[key] for key in sorted(auxiliary)),
    )


__all__ = ["project_state_causal_authority"]
