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
from .semantic_schema_kernel import SemanticSchemaKernel, get_kernel


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
    "likes": "property",
    "dislikes": "property",
    "evaluates": "evaluation",
    "teaches": "teaching",
    "refers_to": "anaphora",
    "modifies": "modification",
    "asks_about": "query",
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
    "likes": "likes",
    "dislikes": "dislikes",
    "evaluates": "evaluates",
    "teaches": "teaches",
    "refers_to": "refers_to",
    "modifies": "modifies",
    "asks_about": "asks_about",
}

_INVERSE_HINTS: dict[str, list[str]] = {
    "is_a": ["sub_type_of"],
    "same_as": ["same_as"],
    "part_of": ["has_part"],
    "causes": ["caused_by"],
    "used_for": ["uses"],
    "has_property": ["property_of"],
    "has_role": ["role_of"],
    "likes": ["liked_by"],
    "dislikes": ["disliked_by"],
    "evaluates": ["evaluated_by"],
}

_INHERITANCE_PREDICATES = {"is_a", "same_as"}


class RelationFrameCompiler:
    def __init__(
        self,
        schema_kernel: SemanticSchemaKernel | None = None,
        predicate_schema_store: Any | None = None,
    ) -> None:
        self._kernel = schema_kernel or get_kernel()
        self._predicate_schema_store = predicate_schema_store

    def compile(self, graph: UOLGraph) -> list[RelationFrame]:
        frames: list[RelationFrame] = []
        seen_edges: set[str] = set()

        # Build edge indices for O(1) lookup by source/target atom ID
        from collections import defaultdict
        edges_by_source: dict[str, list[Any]] = defaultdict(list)
        edges_by_target: dict[str, list[Any]] = defaultdict(list)
        for edge in graph.edges:
            edges_by_source[edge.source_id].append(edge)
            edges_by_target[edge.target_id].append(edge)

        for edge in graph.edges:
            if edge.id in seen_edges:
                continue
            if edge.edge_type not in _EDGE_TYPE_TO_FAMILY:
                schema = self._predicate_schema_store.get(edge.edge_type) if self._predicate_schema_store else None
                if schema is None:
                    continue

            frame = self._compile_edge(graph, edge, edges_by_source)
            if frame is not None:
                frames.append(frame)
                seen_edges.add(edge.id)

        for atom in graph.atoms.values():
            if atom.kind == "relation":
                frame = self._compile_relation_atom(graph, atom, edges_by_source, edges_by_target)
                if frame is not None:
                    frames.append(frame)

        return frames

    _STRUCTURAL_EDGE_TYPES: frozenset = frozenset({
        "has_role",
        "causes",
        "enables",
        "prevents",
        "before",
        "after",
        "refers_to",
        "modifies",
        "teaches",
        "asks_about",
        "is_a",
        "same_as",
        "part_of",
        "used_for",
    })

    _EDGE_PROJECTION_POLICY: dict[str, str] = {
        "has_role": "none",
        "causes": "none",
        "enables": "none",
        "prevents": "none",
        "before": "none",
        "after": "none",
        "refers_to": "none",
        "modifies": "none",
        "evaluates": "object",
        "teaches": "none",
    }

    def _compile_edge(self, graph: UOLGraph, edge: Any, edges_by_source: dict[str, list[Any]] | None = None) -> RelationFrame | None:
        source_atom = graph.atoms.get(edge.source_id)
        target_atom = graph.atoms.get(edge.target_id)
        if source_atom is None or target_atom is None:
            return None

        family = _EDGE_TYPE_TO_FAMILY.get(edge.edge_type, "")
        relation_key = _EDGE_TYPE_TO_KEY.get(edge.edge_type, edge.edge_type)

        if not family:
            schema = self._predicate_schema_store.get(edge.edge_type) if self._predicate_schema_store else None
            if schema is not None:
                family = schema.relation_family
                relation_key = schema.predicate_key
            else:
                family = "definition"

        is_structural = edge.edge_type in self._STRUCTURAL_EDGE_TYPES or edge.features.get("schema_source") == "state_delta"
        pp = self._kernel.projection_policies
        if is_structural:
            projection_policy = pp.for_applies_to("structural_edge")
            projection = projection_policy.projection if projection_policy else "none"
        elif edge.edge_type == "evaluates":
            projection_policy = pp.for_applies_to("evaluates_edge")
            projection = projection_policy.projection if projection_policy else "object"
        else:
            projection = self._EDGE_PROJECTION_POLICY.get(edge.edge_type, "object")
        answerable = not is_structural

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

        qualifiers = self._extract_qualifiers(graph, edge, edges_by_source)

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
            answerable=answerable,
            structural=is_structural,
            projection_policy=projection,
            features=dict(edge.features) if edge.features else {},
        )

    def _compile_relation_atom(self, graph: UOLGraph, atom: Any, edges_by_source: dict[str, list[Any]] | None = None, edges_by_target: dict[str, list[Any]] | None = None) -> RelationFrame | None:
        subject_arg = RelationArgument(role="subject")
        object_arg = RelationArgument(role="object")
        qualifiers: dict[str, RelationArgument] = {}
        edge_ids: list[str] = []
        has_role_edge = False

        if edges_by_source is not None and edges_by_target is not None:
            relevant_edges = edges_by_source.get(atom.id, []) + edges_by_target.get(atom.id, [])
        else:
            relevant_edges = graph.edges
        for edge in relevant_edges:
            if edge.source_id != atom.id and edge.target_id != atom.id:
                continue
            other_id = edge.target_id if edge.source_id == atom.id else edge.source_id
            other = graph.atoms.get(other_id)
            if other is None:
                continue
            edge_ids.append(edge.id)

            if edge.edge_type == "has_role":
                has_role_edge = True
                role = edge.features.get("role", "object")
                arg = RelationArgument(
                    role=role,
                    atom_id=other.id,
                    concept_id=self._concept_id_for(graph, other),
                    entity_id=self._entity_id_for(other),
                    surface=other.surface,
                    confidence=other.confidence,
                )
                if role in ("subject", "source"):
                    subject_arg = arg
                elif role in ("object", "target"):
                    object_arg = arg
                else:
                    qualifiers[role] = arg

        if not subject_arg.atom_id and not object_arg.atom_id:
            return None

        relation_key = atom.key.replace("relation:", "")
        family = self._infer_family_from_key(relation_key)

        is_emotional = atom.source == "emotional_predicate" or relation_key in ("likes", "dislikes")
        is_structural = (has_role_edge or family == "role") and not is_emotional
        pp = self._kernel.projection_policies
        if is_emotional:
            policy = pp.for_applies_to("evaluates_edge")
            projection_policy = policy.projection if policy else "object"
        elif is_structural:
            policy = pp.for_applies_to("structural_edge")
            projection_policy = policy.projection if policy else "none"
        else:
            policy = pp.for_applies_to("relation_atom")
            projection_policy = policy.projection if policy else "object"
        answerable = not is_structural

        compiled_features: dict[str, Any] = {}
        for edge in relevant_edges:
            if edge.source_id == atom.id or edge.target_id == atom.id:
                if edge.features:
                    compiled_features.update(edge.features)
        if not compiled_features and hasattr(atom, "features") and atom.features:
            compiled_features = dict(atom.features)

        return RelationFrame(
            relation_id=uuid.uuid4().hex[:16],
            relation_key=relation_key,
            relation_family=family,
            subject=subject_arg,
            object=object_arg,
            qualifiers=qualifiers,
            source_edge_ids=edge_ids,
            source_atom_ids=[atom.id],
            evidence_refs=self._evidence_refs(atom),
            inverse_relation_keys=_INVERSE_HINTS.get(relation_key, []),
            confidence=atom.confidence,
            answerable=answerable,
            structural=is_structural,
            projection_policy=projection_policy,
            features=compiled_features,
        )

    def _extract_qualifiers(self, graph: UOLGraph, edge: Any, edges_by_source: dict[str, list[Any]] | None = None) -> dict[str, RelationArgument]:
        _CORE_ROLES = frozenset({"subject", "object", "source", "target"})
        qualifiers: dict[str, RelationArgument] = {}

        # Scan has_role edges on the subject entity (edge.source_id)
        if edges_by_source is not None:
            candidate_edges = edges_by_source.get(edge.source_id, [])
        else:
            candidate_edges = graph.edges
        for e2 in candidate_edges:
            if e2.id == edge.id:
                continue
            if e2.edge_type == "has_role" and e2.source_id == edge.source_id:
                target = graph.atoms.get(e2.target_id)
                if target is None:
                    continue
                role = e2.features.get("role", "")
                if role and role not in _CORE_ROLES:
                    qualifiers[role] = RelationArgument(
                        role=role,
                        atom_id=target.id,
                        concept_id=self._concept_id_for(graph, target),
                        entity_id=self._entity_id_for(target),
                        surface=target.surface,
                        confidence=target.confidence,
                    )

        # Also scan has_role edges on the object entity (edge.target_id)
        # for qualifier roles like "domain" from domain phrases
        if edges_by_source is not None:
            obj_candidate_edges = edges_by_source.get(edge.target_id, [])
        else:
            obj_candidate_edges = graph.edges
        for e2 in obj_candidate_edges:
            if e2.id == edge.id:
                continue
            if e2.edge_type == "has_role" and e2.source_id == edge.target_id:
                target = graph.atoms.get(e2.target_id)
                if target is None:
                    continue
                role = e2.features.get("role", "")
                if role and role not in _CORE_ROLES:
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
