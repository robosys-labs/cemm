from __future__ import annotations

import time
import uuid

from ..types.claim import Claim, ClaimStatus
from ..types.entity import Entity, EntityType
from ..types.permission import Permission


class ProfileStore:
    """Lightweight user-profile lane backed by the existing ClaimStore.

    Profile facts are stored as claims with ``subject_entity_id="user"`` and
    ``domain="profile"``. The predicate namespace is ``user.<slot>`` (e.g.
    ``user.name``, ``user.alias``, ``user.preference.*``). This keeps the
    profile lane queryable through the same evidence store without requiring a
    separate SQL schema, while still giving identity/name queries a dedicated
    retrieval path.
    """

    def __init__(self, claim_store: object) -> None:
        self._claim_store = claim_store

    def _ensure_user_entity(self, signal_id: str) -> None:
        parent = getattr(self._claim_store, "_parent_store", None)
        if parent is None:
            return
        entity_store = getattr(parent, "entities", None)
        if entity_store is None:
            return
        if entity_store.get("user") is not None:
            return
        entity_store.put(
            Entity(
                id="user",
                type=EntityType.PERSON,
                name="user",
                aliases=[],
                confidence=0.7,
                created_from_signal_id=signal_id,
                created_at=time.time(),
                updated_at=time.time(),
            )
        )

    def put(
        self,
        slot: str,
        value: str,
        source_id: str,
        permission: Permission | None = None,
        trust: float = 0.7,
    ) -> Claim:
        self._ensure_user_entity(source_id)
        claim = Claim(
            id=uuid.uuid4().hex[:16],
            subject_entity_id="user",
            predicate=f"user.{slot}",
            object_value=value,
            domain="profile",
            source_id=source_id,
            confidence=0.8,
            trust=trust,
            status=ClaimStatus.ACTIVE,
        )
        if permission is not None:
            claim.permission = permission
        self._claim_store.put(claim)
        return claim

    def get(self, slot: str) -> str | None:
        for claim in self._claim_store.find_by_subject("user"):
            if claim.domain == "profile" and claim.predicate == f"user.{slot}":
                return str(claim.object_value)
        return None

    def all_slots(self) -> dict[str, str]:
        slots: dict[str, str] = {}
        for claim in self._claim_store.find_by_subject("user"):
            if claim.domain == "profile" and claim.predicate.startswith("user."):
                slot = claim.predicate[len("user."):]
                slots[slot] = str(claim.object_value)
        return slots
