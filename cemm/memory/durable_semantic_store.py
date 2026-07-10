from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..types.relation_frame import RelationArgument, RelationFrame


@dataclass
class DurableRelationRecord:
    record_id: str
    relation_key: str
    relation_family: str
    subject_concept_id: str = ""
    subject_entity_id: str = ""
    subject_surface: str = ""
    object_concept_id: str = ""
    object_entity_id: str = ""
    object_surface: str = ""
    qualifiers: dict[str, Any] = field(default_factory=dict)
    inverse_relation_keys: list[str] = field(default_factory=list)
    source_patch_ids: list[str] = field(default_factory=list)
    source_atom_ids: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    confidence: float = 0.5
    support_count: int = 1
    observed_at: float = 0.0
    updated_at: float = 0.0
    relation_scope: str = ""
    dimension: str = ""
    features: dict[str, Any] = field(default_factory=dict)


@dataclass
class DurableConceptRecord:
    record_id: str
    concept_key: str
    concept_id: str = ""
    surface: str = ""
    definition: str = ""
    parent_concept_keys: list[str] = field(default_factory=list)
    properties: dict[str, str] = field(default_factory=dict)
    confidence: float = 0.5
    support_count: int = 1
    observed_at: float = 0.0
    updated_at: float = 0.0


@dataclass
class DurablePredicateRecord:
    record_id: str
    predicate_key: str
    relation_family: str = "definition"
    argument_roles: list[str] = field(default_factory=list)
    inverse_predicates: list[str] = field(default_factory=list)
    confidence: float = 0.5
    support_count: int = 1
    observed_at: float = 0.0
    updated_at: float = 0.0


@dataclass
class CommitResult:
    commit_id: str
    status: str = "committed"
    created_records: list[str] = field(default_factory=list)
    updated_records: list[str] = field(default_factory=list)
    merged_record_ids: list[str] = field(default_factory=list)
    patch_journal_ids: list[str] = field(default_factory=list)


@dataclass
class SemanticRetrievalResult:
    records: list[DurableRelationRecord] = field(default_factory=list)
    relation_frames: list[RelationFrame] = field(default_factory=list)
    explanation_paths: list[list[str]] = field(default_factory=list)
    concept_records: list[DurableConceptRecord] = field(default_factory=list)
    predicate_records: list[DurablePredicateRecord] = field(default_factory=list)


_EMPTY = object()


class DurableSemanticStore:
    def __init__(self) -> None:
        self._relations: dict[str, DurableRelationRecord] = {}
        self._concepts: dict[str, DurableConceptRecord] = {}
        self._predicates: dict[str, DurablePredicateRecord] = {}
        self._patch_journal: list[dict[str, Any]] = []
        self._schema_store: Any = None
        self._signal_store: dict[str, Any] = {}

        self._subject_index: dict[str, list[str]] = {}
        self._object_index: dict[str, list[str]] = {}
        self._relation_key_index: dict[str, list[str]] = {}

    def set_schema_store(self, store: Any) -> None:
        """Wire a PredicateSchemaStore for schema-aware queries (inheritance, etc.)."""
        self._schema_store = store

    @property
    def signals(self) -> dict[str, Any]:
        return self._signal_store

    # ── Relation operations ────────────────────────────────────

    def add_relation(
        self,
        relation_key: str,
        relation_family: str,
        subject_concept_id: str = "",
        subject_entity_id: str = "",
        subject_surface: str = "",
        object_concept_id: str = "",
        object_entity_id: str = "",
        object_surface: str = "",
        confidence: float = 0.5,
        source_patch_id: str = "",
        source_atom_ids: list[str] | None = None,
        evidence_refs: list[str] | None = None,
        inverse_keys: list[str] | None = None,
        features: dict[str, Any] | None = None,
        relation_scope: str = "",
        dimension: str = "",
        qualifiers: dict[str, Any] | None = None,
    ) -> DurableRelationRecord:
        now = time.time()
        subj_key = subject_concept_id or subject_entity_id or subject_surface
        obj_key = object_concept_id or object_entity_id or object_surface

        existing = self._find_existing_relation(relation_key, subj_key, obj_key)
        if existing is not None:
            existing.support_count += 1
            existing.confidence = max(existing.confidence, confidence)
            existing.updated_at = now
            if source_patch_id and source_patch_id not in existing.source_patch_ids:
                existing.source_patch_ids.append(source_patch_id)
            if features:
                existing.features.update(features)
            if relation_scope and not existing.relation_scope:
                existing.relation_scope = relation_scope
            if dimension and not existing.dimension:
                existing.dimension = dimension
            if qualifiers:
                existing.qualifiers.update(qualifiers)
            return existing

        record = DurableRelationRecord(
            record_id=uuid.uuid4().hex[:16],
            relation_key=relation_key,
            relation_family=relation_family,
            subject_concept_id=subject_concept_id,
            subject_entity_id=subject_entity_id,
            subject_surface=subject_surface,
            object_concept_id=object_concept_id,
            object_entity_id=object_entity_id,
            object_surface=object_surface,
            qualifiers=dict(qualifiers) if qualifiers else {},
            inverse_relation_keys=list(inverse_keys or []),
            source_patch_ids=[source_patch_id] if source_patch_id else [],
            source_atom_ids=list(source_atom_ids or []),
            evidence_refs=list(evidence_refs or []),
            confidence=confidence,
            support_count=1,
            observed_at=now,
            updated_at=now,
            relation_scope=relation_scope,
            dimension=dimension,
            features=dict(features) if features else {},
        )
        self._relations[record.record_id] = record
        self._index_relation(record)
        return record

    def _find_existing_relation(
        self, relation_key: str, subject_key: str, object_key: str
    ) -> DurableRelationRecord | None:
        for rid in self._relation_key_index.get(relation_key, []):
            rec = self._relations.get(rid)
            if rec is None:
                continue
            rec_subj_keys = {rec.subject_concept_id, rec.subject_entity_id, rec.subject_surface} - {""}
            rec_obj_keys = {rec.object_concept_id, rec.object_entity_id, rec.object_surface} - {""}
            if subject_key in rec_subj_keys and object_key in rec_obj_keys:
                return rec
        return None

    def get_relation(self, record_id: str) -> DurableRelationRecord | None:
        return self._relations.get(record_id)

    def all_relations(self) -> list[DurableRelationRecord]:
        return list(self._relations.values())

    def relation_count(self) -> int:
        return len(self._relations)

    # ── Query: convert durable records to RelationFrames ───────

    def query_relations(
        self,
        relation_key: str = "",
        subject_concept_id: str = "",
        subject_entity_id: str = "",
        object_concept_id: str = "",
        object_entity_id: str = "",
        allow_inheritance: bool = True,
        allow_inverse: bool = True,
    ) -> list[RelationFrame]:
        has_filter = bool(relation_key or subject_concept_id or subject_entity_id
                          or object_concept_id or object_entity_id)

        if has_filter:
            candidate_ids: set[str] | None = None

            if relation_key:
                ids = set(self._relation_key_index.get(relation_key, []))
                candidate_ids = ids if candidate_ids is None else (candidate_ids & ids)

            subj_keys = {subject_concept_id, subject_entity_id} - {""}
            if subj_keys:
                subj_ids: set[str] = set()
                for sk in subj_keys:
                    subj_ids |= set(self._subject_index.get(sk, []))
                if subj_ids:
                    candidate_ids = subj_ids if candidate_ids is None else (candidate_ids & subj_ids)
                else:
                    candidate_ids = set()

            obj_keys = {object_concept_id, object_entity_id} - {""}
            if obj_keys:
                obj_ids: set[str] = set()
                for ok in obj_keys:
                    obj_ids |= set(self._object_index.get(ok, []))
                if obj_ids:
                    candidate_ids = obj_ids if candidate_ids is None else (candidate_ids & obj_ids)
                else:
                    candidate_ids = set()

            if candidate_ids is None:
                candidate_ids = set(self._relations.keys())

            matching = [self._relations[rid] for rid in candidate_ids
                        if rid in self._relations]
        else:
            matching = list(self._relations.values())

        if not matching and relation_key and allow_inverse:
            inv_records = self._query_inverse_relations(relation_key, subject_concept_id, object_concept_id)
            matching.extend(inv_records)

        results = []
        for rec in matching:
            frame = self._record_to_frame(rec)
            if frame is not None:
                results.append(frame)
        return results

    def _query_inverse_relations(
        self, relation_key: str, subject: str, object_: str
    ) -> list[DurableRelationRecord]:
        results = []
        subj_keys = {subject} - {""}
        obj_keys = {object_} - {""}
        for rec in self._relations.values():
            if relation_key in rec.inverse_relation_keys:
                if subj_keys:
                    rec_obj_keys = {rec.object_concept_id, rec.object_entity_id, rec.object_surface} - {""}
                    if not (subj_keys & rec_obj_keys):
                        continue
                if obj_keys:
                    rec_subj_keys = {rec.subject_concept_id, rec.subject_entity_id, rec.subject_surface} - {""}
                    if not (obj_keys & rec_subj_keys):
                        continue
                swapped = DurableRelationRecord(
                    record_id=f"{rec.record_id}_inv",
                    relation_key=relation_key,
                    relation_family=rec.relation_family,
                    subject_concept_id=rec.object_concept_id,
                    subject_entity_id=rec.object_entity_id,
                    subject_surface=rec.object_surface,
                    object_concept_id=rec.subject_concept_id,
                    object_entity_id=rec.subject_entity_id,
                    object_surface=rec.subject_surface,
                    inverse_relation_keys=[rec.relation_key],
                    source_patch_ids=list(rec.source_patch_ids),
                    source_atom_ids=list(rec.source_atom_ids),
                    evidence_refs=list(rec.evidence_refs),
                    confidence=rec.confidence * 0.9,
                    support_count=rec.support_count,
                    relation_scope=rec.relation_scope,
                    dimension=rec.dimension,
                    features=dict(rec.features) if rec.features else {},
                )
                results.append(swapped)
        return results

    def query_inherited(
        self,
        child_concept_id: str,
        parent_concept_id: str,
        relation_key: str = "",
    ) -> list[RelationFrame]:
        results = []
        parent_records = [
            r for r in self._relations.values()
            if r.subject_concept_id == parent_concept_id
        ]
        for rec in parent_records:
            if relation_key and rec.relation_key != relation_key:
                continue
            # Check predicate schema for inheritance behavior
            if self._schema_store is not None:
                schema = self._schema_store.get(rec.relation_key)
                if schema is not None:
                    inheritance_behavior = getattr(schema, 'inheritance_behavior', 'inherit')
                    if inheritance_behavior == "none":
                        continue
            child_frame = RelationFrame(
                relation_id=f"{rec.record_id}_inh_{child_concept_id}",
                relation_key=rec.relation_key,
                relation_family=rec.relation_family,
                subject=RelationArgument(
                    role="subject",
                    concept_id=child_concept_id,
                    surface=rec.subject_surface,
                    confidence=rec.confidence,
                ),
                object=RelationArgument(
                    role="object",
                    concept_id=rec.object_concept_id,
                    entity_id=rec.object_entity_id,
                    surface=rec.object_surface,
                    confidence=rec.confidence,
                ),
                source_edge_ids=list(rec.source_patch_ids),
                source_atom_ids=list(rec.source_atom_ids),
                evidence_refs=list(rec.evidence_refs),
                inverse_relation_keys=list(rec.inverse_relation_keys),
                inherited_from=[rec.record_id],
                confidence=rec.confidence * 0.85,
                features=dict(rec.features) if rec.features else {},
            )
            results.append(child_frame)
        return results

    # ── Concept operations ─────────────────────────────────────

    def add_concept(
        self,
        concept_key: str,
        surface: str = "",
        definition: str = "",
        confidence: float = 0.5,
        parent_keys: list[str] | None = None,
    ) -> DurableConceptRecord:
        now = time.time()
        for rec in self._concepts.values():
            if rec.concept_key == concept_key:
                rec.support_count += 1
                rec.confidence = max(rec.confidence, confidence)
                rec.updated_at = now
                if definition and not rec.definition:
                    rec.definition = definition
                return rec

        record = DurableConceptRecord(
            record_id=uuid.uuid4().hex[:16],
            concept_key=concept_key,
            surface=surface or concept_key,
            definition=definition,
            parent_concept_keys=list(parent_keys or []),
            confidence=confidence,
            support_count=1,
            observed_at=now,
            updated_at=now,
        )
        self._concepts[record.record_id] = record
        return record

    def get_concept(self, concept_key: str) -> DurableConceptRecord | None:
        for rec in self._concepts.values():
            if rec.concept_key == concept_key:
                return rec
        return None

    def all_concepts(self) -> list[DurableConceptRecord]:
        return list(self._concepts.values())

    # ── Predicate operations ───────────────────────────────────

    def add_predicate(
        self,
        predicate_key: str,
        relation_family: str = "definition",
        argument_roles: list[str] | None = None,
        confidence: float = 0.5,
    ) -> DurablePredicateRecord:
        now = time.time()
        existing = self._predicates.get(predicate_key)
        if existing is not None:
            existing.support_count += 1
            existing.confidence = max(existing.confidence, confidence)
            existing.updated_at = now
            return existing

        record = DurablePredicateRecord(
            record_id=uuid.uuid4().hex[:16],
            predicate_key=predicate_key,
            relation_family=relation_family,
            argument_roles=list(argument_roles or []),
            confidence=confidence,
            support_count=1,
            observed_at=now,
            updated_at=now,
        )
        self._predicates[predicate_key] = record
        return record

    def get_predicate(self, predicate_key: str) -> DurablePredicateRecord | None:
        return self._predicates.get(predicate_key)

    def all_predicates(self) -> list[DurablePredicateRecord]:
        return list(self._predicates.values())

    # ── Patch journal ──────────────────────────────────────────

    def log_patch_commit(
        self,
        patch_id: str,
        source_graph_id: str,
        accepted_ops: list[str],
        created_records: list[str],
        updated_records: list[str],
    ) -> str:
        entry_id = uuid.uuid4().hex[:16]
        self._patch_journal.append({
            "journal_id": entry_id,
            "patch_id": patch_id,
            "source_graph_id": source_graph_id,
            "accepted_operations": accepted_ops,
            "created_records": created_records,
            "updated_records": updated_records,
            "committed_at": time.time(),
        })
        return entry_id

    def get_patch_journal(self, limit: int = 50) -> list[dict[str, Any]]:
        return list(self._patch_journal[-limit:])

    # ── Internal helpers ───────────────────────────────────────

    def _index_relation(self, record: DurableRelationRecord) -> None:
        self._relation_key_index.setdefault(record.relation_key, []).append(record.record_id)
        subj_keys = {record.subject_concept_id, record.subject_entity_id, record.subject_surface} - {""}
        for sk in subj_keys:
            self._subject_index.setdefault(sk, []).append(record.record_id)
        obj_keys = {record.object_concept_id, record.object_entity_id, record.object_surface} - {""}
        for ok in obj_keys:
            self._object_index.setdefault(ok, []).append(record.record_id)

    _STRUCTURAL_RELATION_KEYS: frozenset = frozenset({
        "has_role", "causes", "enables", "prevents",
        "before", "after", "refers_to", "modifies",
        "teaches", "asks_about",
        "is_a", "same_as", "part_of", "used_for",
    })

    def _record_to_frame(self, rec: DurableRelationRecord) -> RelationFrame | None:
        is_structural = rec.relation_key in self._STRUCTURAL_RELATION_KEYS
        qualifiers: dict[str, RelationArgument] = {}
        for role, qdata in (rec.qualifiers or {}).items():
            if isinstance(qdata, dict):
                qualifiers[role] = RelationArgument(
                    role=role,
                    concept_id=qdata.get("concept_id", ""),
                    entity_id=qdata.get("entity_id", ""),
                    surface=qdata.get("surface", ""),
                )
        return RelationFrame(
            relation_id=rec.record_id,
            relation_key=rec.relation_key,
            relation_family=rec.relation_family,
            subject=RelationArgument(
                role="subject",
                concept_id=rec.subject_concept_id,
                entity_id=rec.subject_entity_id,
                surface=rec.subject_surface,
                confidence=rec.confidence,
            ),
            object=RelationArgument(
                role="object",
                concept_id=rec.object_concept_id,
                entity_id=rec.object_entity_id,
                surface=rec.object_surface,
                confidence=rec.confidence,
            ),
            qualifiers=qualifiers,
            source_edge_ids=list(rec.source_patch_ids),
            source_atom_ids=list(rec.source_atom_ids),
            evidence_refs=list(rec.evidence_refs),
            inverse_relation_keys=list(rec.inverse_relation_keys),
            confidence=rec.confidence,
            answerable=not is_structural,
            structural=is_structural,
            features=dict(rec.features) if rec.features else {},
        )

    def apply_validated_patch(
        self,
        patch: Any,
        validation: Any,
    ) -> CommitResult:
        now = time.time()
        commit_id = uuid.uuid4().hex[:16]
        created: list[str] = []
        updated: list[str] = []

        if not validation.accepted:
            return CommitResult(
                commit_id=commit_id,
                status=validation.status if validation.status in ("rejected", "needs_confirmation") else "quarantined",
            )

        for op in patch.operations:
            if op.operation in validation.rejected_operations:
                continue
            if op.operation == "upsert_relation_candidate":
                rec = self.add_relation(
                    relation_key=op.fields.get("relation_key", ""),
                    relation_family=op.fields.get("relation_family", "definition"),
                    subject_concept_id=op.fields.get("subject_concept_id", ""),
                    subject_entity_id=op.fields.get("subject_entity_id", ""),
                    subject_surface=op.fields.get("subject_surface", ""),
                    object_concept_id=op.fields.get("object_concept_id", ""),
                    object_entity_id=op.fields.get("object_entity_id", ""),
                    object_surface=op.fields.get("object_surface", ""),
                    confidence=op.confidence,
                    source_patch_id=patch.id,
                    source_atom_ids=op.fields.get("source_atom_ids"),
                    inverse_keys=op.fields.get("inverse_keys"),
                    features=op.fields.get("features"),
                    relation_scope=op.fields.get("relation_scope", ""),
                    dimension=op.fields.get("dimension", ""),
                    qualifiers=op.fields.get("qualifiers"),
                )
                if rec.support_count > 1:
                    updated.append(rec.record_id)
                else:
                    created.append(rec.record_id)
            elif op.operation == "upsert_concept_candidate":
                rec = self.add_concept(
                    concept_key=op.fields.get("concept_key", ""),
                    surface=op.fields.get("surface", ""),
                    definition=op.fields.get("definition", ""),
                    confidence=op.confidence,
                    parent_keys=op.fields.get("parent_keys"),
                )
                if rec.support_count > 1:
                    updated.append(rec.record_id)
                else:
                    created.append(rec.record_id)
            elif op.operation == "observe_predicate_schema":
                rec = self.add_predicate(
                    predicate_key=op.fields.get("predicate_key", ""),
                    relation_family=op.fields.get("relation_family", "definition"),
                    argument_roles=op.fields.get("argument_roles"),
                    confidence=op.confidence,
                )
                if rec.support_count > 1:
                    updated.append(rec.record_id)
                else:
                    created.append(rec.record_id)

        journal_ids = []
        if created or updated:
            jid = self.log_patch_commit(
                patch_id=patch.id,
                source_graph_id=patch.source_graph_id,
                accepted_ops=[op.operation for op in patch.operations],
                created_records=created,
                updated_records=updated,
            )
            journal_ids.append(jid)

        return CommitResult(
            commit_id=commit_id,
            status="committed",
            created_records=created,
            updated_records=updated,
            patch_journal_ids=journal_ids,
        )
