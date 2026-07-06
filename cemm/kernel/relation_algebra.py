"""RelationAlgebra — small graph operators over relation frames.

Implements inverse lookup, inheritance lookup, role/domain binding,
and explanation paths. This is the ALU of the semantic CPU — not a
large ontology, but a small set of graph operators that enable
reasoning over learned relations.

All operators are data-driven: they use relation frames, concept
lattice inheritance, and predicate schema metadata. No domain
primitives are hardcoded.
"""

from __future__ import annotations

from typing import Any

from ..types.relation_frame import RelationArgument, RelationFrame


class RelationAlgebra:
    def __init__(self, schema_store: Any | None = None) -> None:
        self._schema_store = schema_store

    def inverse(self, frame: RelationFrame) -> RelationFrame | None:
        if self._schema_store is None:
            return None
        inverse_keys = self._schema_store.inverse_of(frame.relation_key)
        if not inverse_keys:
            return None
        return RelationFrame(
            relation_id=f"{frame.relation_id}_inv",
            relation_key=inverse_keys[0],
            relation_family=frame.relation_family,
            subject=frame.object,
            object=frame.subject,
            qualifiers=dict(frame.qualifiers),
            source_edge_ids=list(frame.source_edge_ids),
            source_atom_ids=list(frame.source_atom_ids),
            evidence_refs=list(frame.evidence_refs),
            inverse_relation_keys=[frame.relation_key],
            inherited_from=[frame.relation_id],
            confidence=frame.confidence * 0.9,
        )

    def compose(self, frame_a: RelationFrame, frame_b: RelationFrame) -> RelationFrame | None:
        a_obj_id = frame_a.object.concept_id or frame_a.object.atom_id
        b_subj_id = frame_b.subject.concept_id or frame_b.subject.atom_id
        if a_obj_id and b_subj_id and a_obj_id != b_subj_id:
            return None

        composed_key = f"{frame_a.relation_key}+{frame_b.relation_key}"
        return RelationFrame(
            relation_id=f"{frame_a.relation_id}_{frame_b.relation_id}",
            relation_key=composed_key,
            relation_family=frame_a.relation_family,
            subject=RelationArgument(
                role="subject",
                atom_id=frame_a.subject.atom_id,
                concept_id=frame_a.subject.concept_id,
                entity_id=frame_a.subject.entity_id,
                surface=frame_a.subject.surface,
                confidence=frame_a.subject.confidence,
            ),
            object=RelationArgument(
                role="object",
                atom_id=frame_b.object.atom_id,
                concept_id=frame_b.object.concept_id,
                entity_id=frame_b.object.entity_id,
                surface=frame_b.object.surface,
                confidence=frame_b.object.confidence,
            ),
            source_edge_ids=frame_a.source_edge_ids + frame_b.source_edge_ids,
            source_atom_ids=frame_a.source_atom_ids + frame_b.source_atom_ids,
            evidence_refs=frame_a.evidence_refs + frame_b.evidence_refs,
            inherited_from=[frame_a.relation_id, frame_b.relation_id],
            confidence=min(frame_a.confidence, frame_b.confidence) * 0.85,
        )

    def inherit(
        self,
        child_concept_id: str,
        parent_concept_id: str,
        taxonomy_frames: list[RelationFrame],
    ) -> list[RelationFrame]:
        inherited: list[RelationFrame] = []
        for frame in taxonomy_frames:
            if frame.relation_key != "is_a":
                continue
            if frame.subject.concept_id == child_concept_id and frame.object.concept_id == parent_concept_id:
                for other in taxonomy_frames:
                    if other.relation_id == frame.relation_id:
                        continue
                    if other.subject.concept_id == parent_concept_id:
                        if self._schema_store and not self._schema_store.inherits(other.relation_key):
                            continue
                        inherited.append(RelationFrame(
                            relation_id=f"{frame.relation_id}_inh_{other.relation_id}",
                            relation_key=other.relation_key,
                            relation_family=other.relation_family,
                            subject=RelationArgument(
                                role="subject",
                                concept_id=child_concept_id,
                                surface=frame.subject.surface,
                                confidence=frame.subject.confidence,
                            ),
                            object=other.object,
                            source_edge_ids=frame.source_edge_ids + other.source_edge_ids,
                            source_atom_ids=frame.source_atom_ids + other.source_atom_ids,
                            evidence_refs=frame.evidence_refs + other.evidence_refs,
                            inherited_from=[frame.relation_id, other.relation_id],
                            confidence=min(frame.confidence, other.confidence) * 0.8,
                        ))
        return inherited

    def query_subject(
        self,
        relation_key: str,
        subject_concept_id: str = "",
        subject_entity_id: str = "",
        object_concept_id: str = "",
        object_entity_id: str = "",
        frames: list[RelationFrame] | None = None,
        allow_inheritance: bool = True,
        allow_inverse: bool = True,
    ) -> list[RelationFrame]:
        if frames is None:
            return []
        results: list[RelationFrame] = []

        for frame in frames:
            if frame.structural or not frame.answerable:
                continue
            if frame.relation_key == relation_key:
                results.append(frame)

        if subject_concept_id or subject_entity_id:
            results = [
                f for f in results
                if self._matches_subject(f, subject_concept_id, subject_entity_id)
            ]

        if allow_inheritance and self._schema_store and self._schema_store.inherits(relation_key):
            for frame in list(results):
                results.extend(self._inherit_query(frame, frames))

        if allow_inverse and self._schema_store:
            for frame in frames:
                if frame.structural or not frame.answerable:
                    continue
                inv = self.inverse(frame)
                if inv is not None and inv.relation_key == relation_key:
                    results.append(inv)

        # Re-apply subject filter to include inverse frames
        if subject_concept_id or subject_entity_id:
            results = [
                f for f in results
                if self._matches_subject(f, subject_concept_id, subject_entity_id)
            ]

        if object_concept_id or object_entity_id:
            results = [
                f for f in results
                if self._matches_object(f, object_concept_id, object_entity_id)
            ]

        return results

    def query_object(
        self,
        subject_concept_id: str,
        relation_key: str,
        frames: list[RelationFrame] | None = None,
    ) -> list[RelationFrame]:
        if frames is None:
            return []
        return [
            f for f in frames
            if f.relation_key == relation_key and f.subject.concept_id == subject_concept_id
        ]

    def bind_role(
        self,
        subject: RelationArgument,
        frame: RelationFrame,
    ) -> RelationFrame:
        """Bind a subject argument into the subject slot of a relation frame.

        Produces a new frame with the given argument as subject. The original
        subject is preserved as the object if no object is already bound.
        """
        return RelationFrame(
            relation_id=f"{frame.relation_id}_bnd",
            relation_key=frame.relation_key,
            relation_family=frame.relation_family,
            subject=RelationArgument(
                role=subject.role or "subject",
                atom_id=subject.atom_id or frame.subject.atom_id,
                concept_id=subject.concept_id or frame.subject.concept_id,
                entity_id=subject.entity_id or frame.subject.entity_id,
                surface=subject.surface or frame.subject.surface,
                confidence=subject.confidence or frame.subject.confidence,
            ),
            object=frame.object,
            qualifiers=dict(frame.qualifiers),
            source_edge_ids=list(frame.source_edge_ids),
            source_atom_ids=list(frame.source_atom_ids),
            evidence_refs=list(frame.evidence_refs),
            inherited_from=list(frame.inherited_from),
            confidence=frame.confidence,
        )

    def project_qualifier(
        self,
        key: str,
        frame: RelationFrame,
    ) -> RelationFrame | None:
        """Project a named qualifier from a relation frame into a new frame.

        If the qualifier exists, returns a new RelationFrame with the qualifier
        value as the object. Returns None when the key is absent.
        """
        qual = frame.qualifiers.get(key)
        if qual is None:
            return None
        return RelationFrame(
            relation_id=f"{frame.relation_id}_{key}",
            relation_key=key,
            relation_family=frame.relation_family,
            subject=frame.subject,
            object=qual,
            qualifiers={},
            source_edge_ids=list(frame.source_edge_ids),
            source_atom_ids=list(frame.source_atom_ids),
            evidence_refs=list(frame.evidence_refs),
            inherited_from=list(frame.inherited_from),
            confidence=frame.confidence * qual.confidence if qual.confidence else frame.confidence,
        )

    def explain_path(self, frame: RelationFrame, all_frames: list[RelationFrame]) -> list[str]:
        path: list[str] = []
        visited: set[str] = set()
        stack: list[RelationFrame] = [frame]
        while stack:
            current = stack.pop()
            if current.relation_id in visited:
                continue
            visited.add(current.relation_id)
            path.append(self._explain_step(current))
            for parent_id in reversed(current.inherited_from):
                parent = next((f for f in all_frames if f.relation_id == parent_id), None)
                if parent is not None and parent.relation_id not in visited:
                    stack.append(parent)
        return list(reversed(path))

    def _matches_subject(
        self, frame: RelationFrame, concept_id: str, entity_id: str
    ) -> bool:
        if concept_id and frame.subject.concept_id == concept_id:
            return True
        if entity_id and frame.subject.entity_id == entity_id:
            return True
        if not concept_id and not entity_id:
            return True
        return False

    def _matches_object(
        self, frame: RelationFrame, concept_id: str, entity_id: str
    ) -> bool:
        if concept_id and frame.object.concept_id == concept_id:
            return True
        if entity_id and frame.object.entity_id == entity_id:
            return True
        if not concept_id and not entity_id:
            return True
        return False

    def _inherit_query(
        self, frame: RelationFrame, all_frames: list[RelationFrame]
    ) -> list[RelationFrame]:
        inherited: list[RelationFrame] = []
        for taxonomy in all_frames:
            if taxonomy.relation_key != "is_a":
                continue
            if taxonomy.object.concept_id and taxonomy.object.concept_id == frame.subject.concept_id:
                inherited.append(RelationFrame(
                    relation_id=f"{frame.relation_id}_inhs_{taxonomy.relation_id}",
                    relation_key=frame.relation_key,
                    relation_family=frame.relation_family,
                    subject=RelationArgument(
                        role="subject",
                        concept_id=taxonomy.subject.concept_id,
                        surface=taxonomy.subject.surface,
                        confidence=taxonomy.subject.confidence,
                    ),
                    object=frame.object,
                    source_edge_ids=frame.source_edge_ids + taxonomy.source_edge_ids,
                    source_atom_ids=frame.source_atom_ids + taxonomy.source_atom_ids,
                    evidence_refs=frame.evidence_refs + taxonomy.evidence_refs,
                    inherited_from=[frame.relation_id, taxonomy.relation_id],
                    confidence=min(frame.confidence, taxonomy.confidence) * 0.8,
                ))
            if taxonomy.subject.concept_id and taxonomy.subject.concept_id == frame.object.concept_id:
                inherited.append(RelationFrame(
                    relation_id=f"{frame.relation_id}_inho_{taxonomy.relation_id}",
                    relation_key=frame.relation_key,
                    relation_family=frame.relation_family,
                    subject=frame.subject,
                    object=RelationArgument(
                        role="object",
                        concept_id=taxonomy.object.concept_id,
                        surface=taxonomy.object.surface,
                        confidence=taxonomy.object.confidence,
                    ),
                    source_edge_ids=frame.source_edge_ids + taxonomy.source_edge_ids,
                    source_atom_ids=frame.source_atom_ids + taxonomy.source_atom_ids,
                    evidence_refs=frame.evidence_refs + taxonomy.evidence_refs,
                    inherited_from=[frame.relation_id, taxonomy.relation_id],
                    confidence=min(frame.confidence, taxonomy.confidence) * 0.8,
                ))
        return inherited

    def _explain_step(self, frame: RelationFrame) -> str:
        subj = frame.subject.surface or frame.subject.concept_id or frame.subject.entity_id or "?"
        obj = frame.object.surface or frame.object.concept_id or frame.object.entity_id or "?"
        return f"{subj} {frame.relation_key} {obj}"
