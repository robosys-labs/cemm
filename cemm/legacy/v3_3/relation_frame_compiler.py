"""Compile UOL graph relations into one canonical RelationFrame per proposition."""

from __future__ import annotations

from collections import defaultdict
import uuid
from typing import Any

from ...types.relation_frame import RelationArgument, RelationFrame
from ...types.uol_graph import UOLGraph
from .proposition_semantics import is_asserted, is_queried, is_role_placeholder, open_roles
from .semantic_schema_kernel import SemanticSchemaKernel, get_kernel

_EDGE_TYPE_TO_FAMILY: dict[str, str] = {
    "is_a": "taxonomy", "same_as": "identity", "part_of": "membership",
    "causes": "causal", "enables": "affordance", "prevents": "causal",
    "used_for": "affordance", "has_property": "property", "has_role": "role",
    "before": "temporal", "after": "temporal", "likes": "property",
    "dislikes": "property", "evaluates": "definition", "teaches": "definition",
    "refers_to": "definition", "modifies": "definition", "asks_about": "definition",
}

_INVERSE_HINTS: dict[str, list[str]] = {
    "is_a": ["sub_type_of"], "same_as": ["same_as"], "part_of": ["has_part"],
    "causes": ["caused_by"], "used_for": ["uses"],
    "has_property": ["property_of"], "has_role": ["role_of"],
    "likes": ["liked_by"], "dislikes": ["disliked_by"],
    "evaluates": ["evaluated_by"],
}

# These edges describe graph structure rather than domain propositions. Domain
# causal/temporal/taxonomy edges remain answerable unless explicitly marked as
# schema support or backed by a queried/open relation atom.
_META_STRUCTURAL_EDGES = frozenset({
    "has_role", "refers_to", "modifies", "teaches", "asks_about",
})

_CORE_ROLES = frozenset({"subject", "object", "source", "target"})


class RelationFrameCompiler:
    def __init__(
        self,
        schema_kernel: SemanticSchemaKernel | None = None,
        predicate_schema_store: Any | None = None,
    ) -> None:
        self._kernel = schema_kernel or get_kernel()
        self._predicate_schema_store = predicate_schema_store

    def compile(self, graph: UOLGraph) -> list[RelationFrame]:
        by_source: dict[str, list[Any]] = defaultdict(list)
        by_target: dict[str, list[Any]] = defaultdict(list)
        for edge in graph.edges:
            by_source[edge.source_id].append(edge)
            by_target[edge.target_id].append(edge)

        relation_atoms = {
            atom.id: atom for atom in graph.atoms.values()
            if atom.kind == "relation" and not is_role_placeholder(atom)
        }
        backed_relation_ids = {
            str((edge.features or {}).get("relation_atom_id", "") or "")
            for edge in graph.edges
            if str((edge.features or {}).get("relation_atom_id", "") or "") in relation_atoms
        }

        frames: list[RelationFrame] = []
        for atom in relation_atoms.values():
            frame = self._compile_relation_atom(graph, atom, by_source, by_target)
            if frame is not None:
                frames.append(frame)

        # A typed edge backed by a relation atom is a projection/support edge, not
        # a second authoritative proposition frame.
        for edge in graph.edges:
            relation_atom_id = str((edge.features or {}).get("relation_atom_id", "") or "")
            if relation_atom_id in backed_relation_ids:
                continue
            frame = self._compile_edge(graph, edge, by_source)
            if frame is not None:
                frames.append(frame)

        return self._dedupe(frames)

    def _compile_edge(
        self,
        graph: UOLGraph,
        edge: Any,
        edges_by_source: dict[str, list[Any]],
    ) -> RelationFrame | None:
        source_atom = graph.atoms.get(edge.source_id)
        target_atom = graph.atoms.get(edge.target_id)
        if source_atom is None or target_atom is None:
            return None
        if is_role_placeholder(source_atom) or is_role_placeholder(target_atom):
            return None

        relation_key = edge.edge_type
        family = self._family_for(relation_key)
        features = dict(edge.features or {})
        schema_support = features.get("schema_source") in {
            "state_delta", "action_slot", "occupancy_support", "transmutation_support"
        }
        structural = (
            edge.edge_type in _META_STRUCTURAL_EDGES
            or schema_support
            or bool(features.get("structural"))
        )
        answerable = not structural and bool(features.get("answerable", True))
        projection = "none" if structural else str(features.get("projection_policy", "object") or "object")

        return RelationFrame(
            relation_id=edge.id or uuid.uuid4().hex[:16],
            relation_key=relation_key,
            relation_family=family,
            subject=self._argument(graph, source_atom, "subject"),
            object=self._argument(graph, target_atom, "object"),
            qualifiers=self._extract_qualifiers(graph, edge, edges_by_source),
            source_edge_ids=[edge.id],
            source_atom_ids=[source_atom.id, target_atom.id],
            evidence_refs=self._evidence_refs(source_atom, target_atom, edge),
            inverse_relation_keys=self._inverse_for(relation_key),
            confidence=edge.confidence,
            answerable=answerable,
            structural=structural,
            projection_policy=projection,
            query_tags=[],
            features=features,
        )

    def _compile_relation_atom(
        self,
        graph: UOLGraph,
        atom: Any,
        edges_by_source: dict[str, list[Any]],
        edges_by_target: dict[str, list[Any]],
    ) -> RelationFrame | None:
        subject = RelationArgument(role="subject")
        obj = RelationArgument(role="object")
        qualifiers: dict[str, RelationArgument] = {}
        edge_ids: list[str] = []
        compiled_features = dict(getattr(atom, "features", {}) or {})

        relevant = edges_by_source.get(atom.id, []) + edges_by_target.get(atom.id, [])
        for edge in relevant:
            if edge.source_id != atom.id or edge.edge_type != "has_role":
                continue
            filler = graph.atoms.get(edge.target_id)
            if filler is None or is_role_placeholder(filler):
                continue
            edge_ids.append(edge.id)
            role = str((edge.features or {}).get("role", "object") or "object")
            argument = self._argument(graph, filler, role)
            if role in {"subject", "source"}:
                subject = argument
            elif role in {"object", "target"}:
                obj = argument
            else:
                qualifiers[role] = argument
            compiled_features.update(edge.features or {})

        if not subject.atom_id and not obj.atom_id:
            return None

        relation_key = atom.key.replace("relation:", "")
        mode = str(compiled_features.get("proposition_mode", "") or "")
        roles_open = tuple(compiled_features.get("open_roles", ()) or ()) or open_roles(atom)
        queried = is_queried(atom) or mode == "queried"
        complete = bool(subject.atom_id and obj.atom_id and not roles_open)
        structural = queried or not complete or bool(compiled_features.get("structural"))
        answerable = is_asserted(atom) and complete and not structural
        projection = "object" if answerable else "none"
        query_tags = ["query_constraint"] if queried else []
        if roles_open:
            query_tags.extend(f"open:{role}" for role in roles_open)

        return RelationFrame(
            relation_id=atom.id,
            relation_key=relation_key,
            relation_family=self._family_for(relation_key),
            subject=subject,
            object=obj,
            qualifiers=qualifiers,
            source_edge_ids=edge_ids,
            source_atom_ids=[atom.id, *[arg.atom_id for arg in (subject, obj) if arg.atom_id]],
            evidence_refs=self._evidence_refs(atom),
            inverse_relation_keys=self._inverse_for(relation_key),
            confidence=atom.confidence,
            answerable=answerable,
            structural=structural,
            projection_policy=projection,
            query_tags=query_tags,
            features={
                **compiled_features,
                "proposition_mode": mode or ("queried" if queried else "asserted"),
                "open_roles": list(roles_open),
            },
        )

    def _extract_qualifiers(
        self,
        graph: UOLGraph,
        edge: Any,
        edges_by_source: dict[str, list[Any]],
    ) -> dict[str, RelationArgument]:
        qualifiers: dict[str, RelationArgument] = {}
        for owner_id in (edge.source_id, edge.target_id):
            for candidate in edges_by_source.get(owner_id, []):
                if candidate.id == edge.id or candidate.edge_type != "has_role":
                    continue
                role = str((candidate.features or {}).get("role", "") or "")
                if not role or role in _CORE_ROLES:
                    continue
                filler = graph.atoms.get(candidate.target_id)
                if filler is None or is_role_placeholder(filler):
                    continue
                qualifiers[role] = self._argument(graph, filler, role)
        return qualifiers

    def _argument(self, graph: UOLGraph, atom: Any, role: str) -> RelationArgument:
        return RelationArgument(
            role=role,
            atom_id=atom.id,
            concept_id=self._concept_id_for(graph, atom),
            entity_id=self._entity_id_for(atom),
            surface=atom.surface,
            confidence=atom.confidence,
        )

    def _concept_id_for(self, graph: UOLGraph, atom: Any) -> str:
        if is_role_placeholder(atom):
            return ""
        for resolution in graph.concept_resolutions:
            if resolution.atom_id == atom.id:
                return resolution.concept_id
        return ""

    @staticmethod
    def _entity_id_for(atom: Any) -> str:
        if atom.kind in {"entity", "self"} and not is_role_placeholder(atom):
            return atom.key.replace("entity:", "").replace("self:", "")
        return ""

    @staticmethod
    def _evidence_refs(*items: Any) -> list[str]:
        refs: list[str] = []
        for item in items:
            for evidence in getattr(item, "evidence", []) or []:
                if isinstance(evidence, dict):
                    ref = str(evidence.get("id", "") or evidence.get("span_id", "") or "")
                else:
                    ref = str(evidence or "")
                if ref and ref not in refs:
                    refs.append(ref)
        return refs

    def _family_for(self, relation_key: str) -> str:
        schema = self._predicate_schema_store.get(relation_key) if self._predicate_schema_store else None
        if schema is not None:
            return str(schema.relation_family or "definition")
        return _EDGE_TYPE_TO_FAMILY.get(relation_key, "definition")

    def _inverse_for(self, relation_key: str) -> list[str]:
        if self._predicate_schema_store is not None:
            schema_values = self._predicate_schema_store.inverse_of(relation_key)
            if schema_values:
                return list(schema_values)
        return list(_INVERSE_HINTS.get(relation_key, []))

    @staticmethod
    def _dedupe(frames: list[RelationFrame]) -> list[RelationFrame]:
        result: list[RelationFrame] = []
        seen: set[tuple[Any, ...]] = set()
        for frame in frames:
            key = (
                frame.relation_key,
                frame.subject.entity_id or frame.subject.concept_id or frame.subject.surface,
                frame.object.entity_id or frame.object.concept_id or frame.object.surface,
                str((frame.features or {}).get("dimension", "") or (frame.features or {}).get("property_dimension", "")),
                str((frame.features or {}).get("proposition_mode", "")),
                frame.structural,
            )
            if key in seen:
                continue
            seen.add(key)
            result.append(frame)
        return result
