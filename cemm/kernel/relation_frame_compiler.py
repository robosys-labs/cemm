"""RelationFrameCompiler — compile UOLGraph edges/atoms into RelationFrames.

Turns graph edges and relation atoms into operational relation frames with
bound subject/object/qualifier roles, normalized relation families,
inverse relation hints, and full atom/edge lineage.
"""

from __future__ import annotations

import uuid
from typing import Any

from ..types.relation_frame import RelationArgument, RelationFrame
from ..types.uol_graph import UOLGraph


_EDGE_TYPE_TO_FAMILY: dict[str, str] = {
    "is_a": "taxonomy",
    "same_as": "identity",
    "part_of": "membership",
    "causes": "causal",
    "enables": "affordance",
    "prevents": "causal",
    "used_for": "affordance",
    "has_property": "property",
    "has_role": "role",
    "before": "temporal",
    "after": "temporal",
}

_EDGE_TYPE_TO_KEY: dict[str, str] = {
    "is_a": "is_a",
    "same_as": "same_as",
    "part_of": "part_of",
    "causes": "causes",
    "enables": "enables",
    "prevents": "prevents",
    "used_for": "used_for",
    "has_property": "has_property",
    "has_role": "has_role",
    "before": "before",
    "after": "after",
}

_INVERSE_HINTS: dict[str, list[str]] = {
    "is_a": ["sub_type_of"],
    "same_as": ["same_as"],
    "part_of": ["has_part"],
    "causes": ["caused_by"],
    "used_for": ["uses"],
    "has_property": ["property_of"],
    "has_role": ["role_of"],
}

_INHERITANCE_PREDICATES = {"is_a", "same_as"}


class RelationFrameCompiler:
    def compile(self, graph: UOLGraph) -> list[RelationFrame]:
        frames: list[RelationFrame] = []
        seen_edges: set[str] = set()

        for edge in graph.edges:
            if edge.id in seen_edges:
                continue
            if edge.edge_type not in _EDGE_TYPE_TO_FAMILY:
                continue

            frame = self._compile_edge(graph, edge)
            if frame is not None:
                frames.append(frame)
                seen_edges.add(edge.id)

        for atom in graph.atoms.values():
            if atom.kind == "relation":
                frame = self._compile_relation_atom(graph, atom)
                if frame is not None:
                    frames.append(frame)

        return frames

    def _compile_edge(self, graph: UOLGraph, edge: Any) -> RelationFrame | None:
        source_atom = graph.atoms.get(edge.source_id)
        target_atom = graph.atoms.get(edge.target_id)
        if source_atom is None or target_atom is None:
            return None

        family = _EDGE_TYPE_TO_FAMILY.get(edge.edge_type, "definition")
        relation_key = _EDGE_TYPE_TO_KEY.get(edge.edge_type, edge.edge_type)

        subject = RelationArgument(
            role="subject",
            atom_id=source_atom.id,
            concept_id=self._concept_id_for(graph, source_atom),
            entity_id=self._entity_id_for(source_atom),
            surface=source_atom.surface,
            confidence=source_atom.confidence,
        )

        obj = RelationArgument(
            role="object",
            atom_id=target_atom.id,
            concept_id=self._concept_id_for(graph, target_atom),
            entity_id=self._entity_id_for(target_atom),
            surface=target_atom.surface,
            confidence=target_atom.confidence,
        )

        qualifiers = self._extract_qualifiers(graph, edge)

        return RelationFrame(
            relation_id=uuid.uuid4().hex[:16],
            relation_key=relation_key,
            relation_family=family,
            subject=subject,
            object=obj,
            qualifiers=qualifiers,
            source_edge_ids=[edge.id],
            source_atom_ids=[source_atom.id, target_atom.id],
            evidence_refs=self._evidence_refs(source_atom, target_atom, edge),
            inverse_relation_keys=_INVERSE_HINTS.get(relation_key, []),
            inherited_from=[],
            confidence=edge.confidence,
        )

    def _compile_relation_atom(self, graph: UOLGraph, atom: Any) -> RelationFrame | None:
        subject_arg = RelationArgument(role="subject")
        object_arg = RelationArgument(role="object")
        edge_ids: list[str] = []

        for edge in graph.edges:
            if edge.source_id != atom.id and edge.target_id != atom.id:
                continue
            other_id = edge.target_id if edge.source_id == atom.id else edge.source_id
            other = graph.atoms.get(other_id)
            if other is None:
                continue
            edge_ids.append(edge.id)

            if edge.edge_type == "has_role":
                role = edge.features.get("role", "object")
                arg = RelationArgument(
                    role=role,
                    atom_id=other.id,
                    concept_id=self._concept_id_for(graph, other),
                    entity_id=self._entity_id_for(other),
                    surface=other.surface,
                    confidence=other.confidence,
                )
                if role == "subject":
                    subject_arg = arg
                elif role == "object":
                    object_arg = arg
                else:
                    pass

        if not subject_arg.atom_id and not object_arg.atom_id:
            return None

        relation_key = atom.key.replace("relation:", "")
        family = self._infer_family_from_key(relation_key)

        return RelationFrame(
            relation_id=uuid.uuid4().hex[:16],
            relation_key=relation_key,
            relation_family=family,
            subject=subject_arg,
            object=object_arg,
            source_edge_ids=edge_ids,
            source_atom_ids=[atom.id],
            evidence_refs=self._evidence_refs(atom),
            inverse_relation_keys=_INVERSE_HINTS.get(relation_key, []),
            confidence=atom.confidence,
        )

    def _extract_qualifiers(self, graph: UOLGraph, edge: Any) -> dict[str, RelationArgument]:
        qualifiers: dict[str, RelationArgument] = {}
        for e2 in graph.edges:
            if e2.id == edge.id:
                continue
            if e2.edge_type == "has_role" and e2.source_id == edge.source_id:
                target = graph.atoms.get(e2.target_id)
                if target is None:
                    continue
                role = e2.features.get("role", "")
                if role and role not in ("subject", "object"):
                    qualifiers[role] = RelationArgument(
                        role=role,
                        atom_id=target.id,
                        concept_id=self._concept_id_for(graph, target),
                        entity_id=self._entity_id_for(target),
                        surface=target.surface,
                        confidence=target.confidence,
                    )
        return qualifiers

    def _concept_id_for(self, graph: UOLGraph, atom: Any) -> str:
        for cr in graph.concept_resolutions:
            if cr.atom_id == atom.id:
                return cr.concept_id
        return ""

    def _entity_id_for(self, atom: Any) -> str:
        if atom.kind in ("entity", "self"):
            return atom.key.replace("entity:", "").replace("self:", "")
        return ""

    def _evidence_refs(self, *items: Any) -> list[str]:
        refs: list[str] = []
        for item in items:
            evidence = getattr(item, "evidence", [])
            for ev in evidence:
                ev_id = ev.get("id", "") if isinstance(ev, dict) else str(ev)
                if ev_id:
                    refs.append(ev_id)
        return refs

    def _infer_family_from_key(self, key: str) -> str:
        if "is_a" in key or "type_of" in key:
            return "taxonomy"
        if "same_as" in key or "identity" in key:
            return "identity"
        if "part_of" in key:
            return "membership"
        if "cause" in key:
            return "causal"
        if "used_for" in key or "afford" in key:
            return "affordance"
        if "before" in key or "after" in key:
            return "temporal"
        if "has_property" in key or "property" in key:
            return "property"
        if "role" in key:
            return "role"
        return "definition"
