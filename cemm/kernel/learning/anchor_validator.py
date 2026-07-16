"""Grounding-anchor validation for learned definitions and rules."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class AnchorValidation:
    grounded: bool
    anchor_refs: tuple[str, ...] = ()
    blocker_refs: tuple[str, ...] = ()


class GroundingAnchorValidator:
    """Ensures learned structure terminates in known schemas or grounded records."""

    def __init__(self, schema_store, semantic_memory=None) -> None:
        self._store = schema_store
        self._memory = semantic_memory

    def validate_entity_kind(
        self,
        semantic_key: str,
        parent_kind_refs: Iterable[str],
    ) -> AnchorValidation:
        parents = tuple(str(parent) for parent in parent_kind_refs)
        anchors = []
        blockers = []
        for parent in parents:
            envelope = self._store.find_active(str(parent))
            if envelope is None or envelope.schema_kind != "entity_kind":
                blockers.append(f"unanchored_parent_kind:{parent}")
            else:
                anchors.append(envelope.record_id)
        if not parents:
            blockers.append("entity_kind_requires_grounded_parent")
        if self._looks_internal(semantic_key):
            blockers.append(f"invalid_learned_semantic_key:{semantic_key}")
        return AnchorValidation(
            grounded=not blockers,
            anchor_refs=tuple(dict.fromkeys(anchors)),
            blocker_refs=tuple(dict.fromkeys(blockers)),
        )

    def validate_rule(self, premise_atoms, conclusion_atoms) -> AnchorValidation:
        anchors = []
        blockers = []
        atoms = tuple((*tuple(premise_atoms), *tuple(conclusion_atoms)))
        if not premise_atoms:
            blockers.append("rule_requires_premise")
        if not conclusion_atoms:
            blockers.append("rule_requires_conclusion")
        for atom in atoms:
            predicate = str(getattr(atom, "predicate_key", ""))
            envelope = self._store.find_active(predicate)
            if envelope is None or envelope.schema_kind != "predicate":
                blockers.append(f"unanchored_predicate:{predicate}")
            else:
                anchors.append(envelope.record_id)
            for role_key, term in dict(getattr(atom, "roles", {}) or {}).items():
                if not term or term.startswith(("$", "?", "value:")):
                    continue
                if term in {"self", "user", "actual"}:
                    anchors.append(f"referent:{term}")
                    continue
                schema = self._store.find_active(term)
                if schema is not None:
                    anchors.append(schema.record_id)
                    continue
                if self._memory is not None and any(
                    role.value_ref == term
                    for fact in self._memory.all_facts()
                    for role in fact.roles
                ):
                    anchors.append(f"memory:{term}")
                    continue
                blockers.append(f"unanchored_constant:{role_key}:{term}")
        return AnchorValidation(
            grounded=not blockers,
            anchor_refs=tuple(dict.fromkeys(anchors)),
            blocker_refs=tuple(dict.fromkeys(blockers)),
        )

    @staticmethod
    def _looks_internal(value: str) -> bool:
        return not value or value.startswith(("ref:", "opaque:", "value:", "$", "?"))
