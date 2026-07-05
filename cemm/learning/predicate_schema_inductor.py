"""PredicateSchemaInductor — discovers new predicate schemas from relation frames."""

from __future__ import annotations

from ..memory.predicate_schema_store import PredicateSchemaStore
from ..types.relation_frame import RelationFrame


class PredicateSchemaInductor:
    """Scan relation frames for unknown predicate keys and induct candidate schemas.

    For each frame with an unknown predicate key:
      1. Infer argument roles from the frame's subject/object/qualifier roles
      2. Call store.observe_candidate() to create or increment a candidate
      3. After all frames, promote candidates with support_count >= 2
    """

    def induct_from_frames(
        self, frames: list[RelationFrame], store: PredicateSchemaStore
    ) -> list[str]:
        """Induct new predicate schemas from relation frames.

        Returns list of predicate keys that were newly observed or promoted.
        """
        observed: set[str] = set()

        for frame in frames:
            key = frame.relation_key
            if store.get(key) is not None:
                continue

            argument_roles = self._infer_argument_roles(frame)
            store.observe_candidate(key, argument_roles, frame.relation_family)
            observed.add(key)

        for key in list(observed):
            candidate = store.get_candidate(key)
            if candidate is not None and candidate.support_count >= 2:
                store.promote(key)

        return list(observed)

    @staticmethod
    def _infer_argument_roles(frame: RelationFrame) -> list[str]:
        """Collect unique roles from subject, object, and qualifiers."""
        roles: list[str] = []
        seen: set[str] = set()

        for role in (frame.subject.role, frame.object.role):
            if role not in seen:
                seen.add(role)
                roles.append(role)

        for qualifier_key in sorted(frame.qualifiers):
            role = frame.qualifiers[qualifier_key].role
            if role not in seen:
                seen.add(role)
                roles.append(role)

        return roles
