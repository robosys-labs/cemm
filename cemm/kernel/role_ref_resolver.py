"""RoleRefResolver — resolves role references to entities.
Never invents user/self actors. Unresolved roles stay unresolved.
"""

from __future__ import annotations

from typing import Any


class RoleRefResolver:
    """Resolves role references (actor, target, object, place) to entity references.
    
    Placeholders never satisfy typed ports. An unresolved role is preserved
    as a SemanticGap rather than replaced by an invented entity.
    """
    
    def resolve(
        self,
        role_assignments: dict[str, str],
        known_entities: dict[str, Any],
        allow_placeholders: bool = False,
    ) -> dict[str, tuple[str, bool]]:
        """Resolve role keys to entity IDs.
        
        Returns dict of {role_key: (entity_id, is_resolved)}.
        If a role cannot be resolved and allow_placeholders is False,
        the entity_id is empty and is_resolved is False.
        """
        resolved: dict[str, tuple[str, bool]] = {}
        for role, entity_ref in role_assignments.items():
            if entity_ref in known_entities:
                resolved[role] = (entity_ref, True)
            elif entity_ref and allow_placeholders:
                resolved[role] = (entity_ref, False)
            else:
                resolved[role] = ("", False)
        return resolved
