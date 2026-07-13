from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Mapping

from ..types.relation_frame import RelationArgument, RelationFrame
from .relation_identity import (
    RelationIdentity,
    cardinality_from_fields,
    dimension_from_fields,
    normalize_qualifiers,
    object_key_from_fields,
    scope_from_fields,
    subject_key_from_fields,
)


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
    cardinality: str = "unknown"
    active: bool = True
    supersedes_record_ids: list[str] = field(default_factory=list)
    superseded_by_record_id: str = ""
    features: dict[str, Any] = field(default_factory=dict)

    def identity(self) -> RelationIdentity:
        return RelationIdentity.from_fields({
            "relation_key": self.relation_key,
            "subject_concept_id": self.subject_concept_id,
            "subject_entity_id": self.subject_entity_id,
            "subject_surface": self.subject_surface,
            "dimension": self.dimension,
            "relation_scope": self.relation_scope,
            "qualifiers": self.qualifiers,
            "features": self.features,
        })

    def object_key(self) -> str:
        return self.object_entity_id or self.object_concept_id or self.object_surface


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
    superseded_record_ids: list[str] = field(default_factory=list)
    operation_target_ids: list[str] = field(default_factory=list)
    rejected_operation_target_ids: list[str] = field(default_factory=list)
    patch_journal_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class SemanticRetrievalResult:
    records: list[DurableRelationRecord] = field(default_factory=list)
    relation_frames: list[RelationFrame] = field(default_factory=list)
    explanation_paths: list[list[str]] = field(default_factory=list)
    concept_records: list[DurableConceptRecord] = field(default_factory=list)
    predicate_records: list[DurablePredicateRecord] = field(default_factory=list)


class DurableSemanticStore:
    def __init__(self) -> None:
        self._relations: dict[str, DurableRelationRecord] = {}
        self._concepts: dict[str, DurableConceptRecord] = {}
        self._predicates: dict[str, DurablePredicateRecord] = {}
        self._patch_journal: list[dict[str, Any]] = []
        self._schema_store: Any = None
        self._signal_store: dict[str, Any] = {}
        self._subject_index: dict[str, set[str]] = {}
        self._object_index: dict[str, set[str]] = {}
        self._relation_key_index: dict[str, set[str]] = {}
        self._identity_index: dict[str, set[str]] = {}

    def set_schema_store(self, store: Any) -> None:
        self._schema_store = store

    @property
    def signals(self) -> dict[str, Any]:
        return self._signal_store

    # ── Relations ────────────────────────────────────────────────

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
        cardinality: str = "",
    ) -> DurableRelationRecord:
        now = time.time()
        fields = {
            "relation_key": relation_key,
            "subject_concept_id": subject_concept_id,
            "subject_entity_id": subject_entity_id,
            "subject_surface": subject_surface,
            "object_concept_id": object_concept_id,
            "object_entity_id": object_entity_id,
            "object_surface": object_surface,
            "dimension": dimension,
            "relation_scope": relation_scope,
            "qualifiers": qualifiers or {},
            "cardinality": cardinality,
            "features": features or {},
        }
        identity = RelationIdentity.from_fields(fields)
        object_key = object_key_from_fields(fields)
        if not relation_key or not identity.subject_key or not object_key:
            raise ValueError("durable relation requires relation, subject, and object")
        from ..kernel.proposition_semantics import is_internal_identifier
        if is_internal_identifier(object_surface):
            raise ValueError("internal identifier cannot be stored as public object surface")

        effective_cardinality = cardinality_from_fields(
            fields, schema_store=self._schema_store, default="unknown"
        )
        existing_exact = self._find_exact(identity, object_key, active_only=True)
        if existing_exact is not None:
            existing_exact.support_count += 1
            existing_exact.confidence = max(existing_exact.confidence, confidence)
            existing_exact.updated_at = now
            self._merge_lineage(
                existing_exact,
                source_patch_id=source_patch_id,
                source_atom_ids=source_atom_ids or [],
                evidence_refs=evidence_refs or [],
                inverse_keys=inverse_keys or [],
                features=features or {},
            )
            return existing_exact

        superseded: list[DurableRelationRecord] = []
        if effective_cardinality in {"single", "optional_one"}:
            superseded = self._records_for_identity(identity, active_only=True)

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
            qualifiers=dict(qualifiers or {}),
            inverse_relation_keys=list(dict.fromkeys(inverse_keys or [])),
            source_patch_ids=[source_patch_id] if source_patch_id else [],
            source_atom_ids=list(dict.fromkeys(source_atom_ids or [])),
            evidence_refs=list(dict.fromkeys(evidence_refs or [])),
            confidence=confidence,
            support_count=1,
            observed_at=now,
            updated_at=now,
            relation_scope=scope_from_fields(fields),
            dimension=dimension_from_fields(fields),
            cardinality=effective_cardinality,
            active=True,
            supersedes_record_ids=[item.record_id for item in superseded],
            features={
                **dict(features or {}),
                "dimension": dimension_from_fields(fields),
                "relation_scope": scope_from_fields(fields),
                "cardinality": effective_cardinality,
                "proposition_mode": str((features or {}).get("proposition_mode", "asserted") or "asserted"),
            },
        )
        self._relations[record.record_id] = record
        self._index_relation(record)
        for prior in superseded:
            prior.active = False
            prior.superseded_by_record_id = record.record_id
            prior.updated_at = now
        return record

    def get_relation(self, record_id: str) -> DurableRelationRecord | None:
        return self._relations.get(record_id)

    def all_relations(self, active_only: bool = False) -> list[DurableRelationRecord]:
        records = list(self._relations.values())
        return [record for record in records if record.active] if active_only else records

    def relation_count(self, active_only: bool = False) -> int:
        return len(self.all_relations(active_only=active_only))

    def records_for_identity(
        self, identity: RelationIdentity, *, active_only: bool = True,
    ) -> list[DurableRelationRecord]:
        return list(self._records_for_identity(identity, active_only=active_only))

    def query_relations(
        self,
        relation_key: str = "",
        subject_concept_id: str = "",
        subject_entity_id: str = "",
        object_concept_id: str = "",
        object_entity_id: str = "",
        dimension: str = "",
        relation_scope: str = "",
        allow_inheritance: bool = True,
        allow_inverse: bool = True,
        active_only: bool = True,
    ) -> list[RelationFrame]:
        candidate_ids: set[str] | None = None
        if relation_key:
            candidate_ids = set(self._relation_key_index.get(relation_key, set()))
        subject_keys = {subject_concept_id, subject_entity_id} - {""}
        if subject_keys:
            subject_ids: set[str] = set()
            for key in subject_keys:
                subject_ids.update(self._subject_index.get(key, set()))
            candidate_ids = subject_ids if candidate_ids is None else candidate_ids & subject_ids
        object_keys = {object_concept_id, object_entity_id} - {""}
        if object_keys:
            object_ids: set[str] = set()
            for key in object_keys:
                object_ids.update(self._object_index.get(key, set()))
            candidate_ids = object_ids if candidate_ids is None else candidate_ids & object_ids
        if candidate_ids is None:
            candidate_ids = set(self._relations)

        normalized_dimension = dimension_from_fields({"dimension": dimension})
        normalized_scope = scope_from_fields({"relation_scope": relation_scope})
        records = []
        for record_id in candidate_ids:
            record = self._relations.get(record_id)
            if record is None or (active_only and not record.active):
                continue
            if normalized_dimension and record.dimension != normalized_dimension:
                continue
            if normalized_scope and record.relation_scope != normalized_scope:
                continue
            records.append(record)

        if not records and relation_key and allow_inverse:
            records = self._query_inverse_relations(
                relation_key, subject_concept_id or subject_entity_id,
                object_concept_id or object_entity_id, active_only=active_only,
            )

        frames = [self._record_to_frame(record) for record in records]
        return [frame for frame in frames if frame is not None]

    def query_inherited(
        self,
        child_concept_id: str,
        parent_concept_id: str,
        relation_key: str = "",
    ) -> list[RelationFrame]:
        results: list[RelationFrame] = []
        for record in self._relations.values():
            if not record.active or record.subject_concept_id != parent_concept_id:
                continue
            if relation_key and record.relation_key != relation_key:
                continue
            schema = self._schema_store.get(record.relation_key) if self._schema_store else None
            if schema is not None and getattr(schema, "inheritance_behavior", "inherit") == "none":
                continue
            frame = self._record_to_frame(record)
            if frame is None:
                continue
            frame.relation_id = f"{record.record_id}_inh_{child_concept_id}"
            frame.subject.concept_id = child_concept_id
            frame.inherited_from = [record.record_id]
            frame.confidence *= 0.85
            results.append(frame)
        return results

    # ── Concepts / predicates ────────────────────────────────────

    def add_concept(
        self,
        concept_key: str,
        surface: str = "",
        definition: str = "",
        confidence: float = 0.5,
        parent_keys: list[str] | None = None,
    ) -> DurableConceptRecord:
        now = time.time()
        existing = self.get_concept(concept_key)
        if existing is not None:
            existing.support_count += 1
            existing.confidence = max(existing.confidence, confidence)
            existing.updated_at = now
            existing.surface = existing.surface or surface
            existing.definition = existing.definition or definition
            for key in parent_keys or []:
                if key not in existing.parent_concept_keys:
                    existing.parent_concept_keys.append(key)
            return existing
        record = DurableConceptRecord(
            record_id=uuid.uuid4().hex[:16],
            concept_key=concept_key,
            concept_id=concept_key if concept_key.startswith("concept:") else f"concept:{concept_key}",
            surface=surface or concept_key,
            definition=definition,
            parent_concept_keys=list(dict.fromkeys(parent_keys or [])),
            confidence=confidence,
            observed_at=now,
            updated_at=now,
        )
        self._concepts[record.record_id] = record
        return record

    def get_concept(self, concept_key: str) -> DurableConceptRecord | None:
        return next((record for record in self._concepts.values() if record.concept_key == concept_key), None)

    def all_concepts(self) -> list[DurableConceptRecord]:
        return list(self._concepts.values())

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
            observed_at=now,
            updated_at=now,
        )
        self._predicates[predicate_key] = record
        return record

    def get_predicate(self, predicate_key: str) -> DurablePredicateRecord | None:
        return self._predicates.get(predicate_key)

    def all_predicates(self) -> list[DurablePredicateRecord]:
        return list(self._predicates.values())

    # ── Patch commit ─────────────────────────────────────────────

    def apply_validated_patch(self, patch: Any, validation: Any) -> CommitResult:
        commit_id = uuid.uuid4().hex[:16]
        if not validation.accepted:
            status = validation.status if validation.status in {"rejected", "needs_confirmation"} else "quarantined"
            return CommitResult(commit_id=commit_id, status=status)

        accepted_targets = set(getattr(validation, "accepted_operations", []) or [])
        rejected_targets = set(getattr(validation, "rejected_operation_target_ids", []) or [])
        created: list[str] = []
        updated: list[str] = []
        superseded: list[str] = []
        committed_targets: list[str] = []

        for operation in patch.operations:
            if accepted_targets and operation.target_id not in accepted_targets:
                rejected_targets.add(operation.target_id)
                continue
            before_ids = set(self._relations) | set(self._concepts) | {
                record.record_id for record in self._predicates.values()
            }
            record: Any | None = None
            fields = operation.fields
            if operation.operation == "upsert_relation_candidate":
                record = self.add_relation(
                    relation_key=fields.get("relation_key", ""),
                    relation_family=fields.get("relation_family", "definition"),
                    subject_concept_id=fields.get("subject_concept_id", ""),
                    subject_entity_id=fields.get("subject_entity_id", ""),
                    subject_surface=fields.get("subject_surface", ""),
                    object_concept_id=fields.get("object_concept_id", ""),
                    object_entity_id=fields.get("object_entity_id", ""),
                    object_surface=fields.get("object_surface", ""),
                    confidence=operation.confidence,
                    source_patch_id=patch.id,
                    source_atom_ids=fields.get("source_atom_ids"),
                    evidence_refs=fields.get("evidence_refs") or patch.evidence_refs,
                    inverse_keys=fields.get("inverse_keys"),
                    features=fields.get("features"),
                    relation_scope=fields.get("relation_scope", ""),
                    dimension=fields.get("dimension", ""),
                    qualifiers=fields.get("qualifiers"),
                    cardinality=fields.get("cardinality", ""),
                )
                superseded.extend(record.supersedes_record_ids)
            elif operation.operation == "upsert_concept_candidate":
                record = self.add_concept(
                    concept_key=fields.get("concept_key", ""),
                    surface=fields.get("surface", ""),
                    definition=fields.get("definition", ""),
                    confidence=operation.confidence,
                    parent_keys=fields.get("parent_keys"),
                )
            elif operation.operation == "observe_predicate_schema":
                record = self.add_predicate(
                    predicate_key=fields.get("predicate_key", ""),
                    relation_family=fields.get("relation_family", "definition"),
                    argument_roles=fields.get("argument_roles"),
                    confidence=operation.confidence,
                )
            else:
                # Non-durable structural observations are intentionally not
                # interpreted as semantic records by this store.
                continue

            committed_targets.append(operation.target_id)
            if record.record_id in before_ids:
                updated.append(record.record_id)
            else:
                created.append(record.record_id)

        journal_ids: list[str] = []
        if created or updated:
            journal_ids.append(self.log_patch_commit(
                patch_id=patch.id,
                source_graph_id=patch.source_graph_id,
                accepted_ops=committed_targets,
                created_records=created,
                updated_records=updated,
            ))
        return CommitResult(
            commit_id=commit_id,
            status="committed" if committed_targets else "rejected",
            created_records=created,
            updated_records=updated,
            superseded_record_ids=list(dict.fromkeys(superseded)),
            operation_target_ids=committed_targets,
            rejected_operation_target_ids=list(rejected_targets),
            patch_journal_ids=journal_ids,
        )

    def log_patch_commit(
        self,
        patch_id: str,
        source_graph_id: str,
        accepted_ops: list[str],
        created_records: list[str],
        updated_records: list[str],
    ) -> str:
        journal_id = uuid.uuid4().hex[:16]
        self._patch_journal.append({
            "journal_id": journal_id,
            "patch_id": patch_id,
            "source_graph_id": source_graph_id,
            "accepted_operations": list(accepted_ops),
            "created_records": list(created_records),
            "updated_records": list(updated_records),
            "committed_at": time.time(),
        })
        return journal_id

    def get_patch_journal(self, limit: int = 50) -> list[dict[str, Any]]:
        return list(self._patch_journal[-limit:])

    # ── Internal helpers ─────────────────────────────────────────

    def _records_for_identity(self, identity: RelationIdentity, active_only: bool) -> list[DurableRelationRecord]:
        ids = self._identity_index.get(identity.as_key(), set())
        return [
            self._relations[record_id] for record_id in ids
            if record_id in self._relations and (not active_only or self._relations[record_id].active)
        ]

    def _find_exact(
        self,
        identity: RelationIdentity,
        object_key: str,
        active_only: bool,
    ) -> DurableRelationRecord | None:
        return next((
            record for record in self._records_for_identity(identity, active_only)
            if record.object_key() == object_key
        ), None)

    def _index_relation(self, record: DurableRelationRecord) -> None:
        self._relation_key_index.setdefault(record.relation_key, set()).add(record.record_id)
        for key in {record.subject_concept_id, record.subject_entity_id, record.subject_surface} - {""}:
            self._subject_index.setdefault(key, set()).add(record.record_id)
        for key in {record.object_concept_id, record.object_entity_id, record.object_surface} - {""}:
            self._object_index.setdefault(key, set()).add(record.record_id)
        self._identity_index.setdefault(record.identity().as_key(), set()).add(record.record_id)

    @staticmethod
    def _merge_lineage(
        record: DurableRelationRecord,
        *,
        source_patch_id: str,
        source_atom_ids: list[str],
        evidence_refs: list[str],
        inverse_keys: list[str],
        features: dict[str, Any],
    ) -> None:
        for collection, values in (
            (record.source_patch_ids, [source_patch_id] if source_patch_id else []),
            (record.source_atom_ids, source_atom_ids),
            (record.evidence_refs, evidence_refs),
            (record.inverse_relation_keys, inverse_keys),
        ):
            for value in values:
                if value and value not in collection:
                    collection.append(value)
        record.features.update(features)

    def _query_inverse_relations(
        self,
        relation_key: str,
        subject: str,
        object_: str,
        *,
        active_only: bool,
    ) -> list[DurableRelationRecord]:
        results: list[DurableRelationRecord] = []
        for record in self._relations.values():
            if active_only and not record.active:
                continue
            if relation_key not in record.inverse_relation_keys:
                continue
            if subject and subject not in {record.object_concept_id, record.object_entity_id, record.object_surface}:
                continue
            if object_ and object_ not in {record.subject_concept_id, record.subject_entity_id, record.subject_surface}:
                continue
            results.append(DurableRelationRecord(
                record_id=f"{record.record_id}_inv",
                relation_key=relation_key,
                relation_family=record.relation_family,
                subject_concept_id=record.object_concept_id,
                subject_entity_id=record.object_entity_id,
                subject_surface=record.object_surface,
                object_concept_id=record.subject_concept_id,
                object_entity_id=record.subject_entity_id,
                object_surface=record.subject_surface,
                qualifiers=dict(record.qualifiers),
                inverse_relation_keys=[record.relation_key],
                source_patch_ids=list(record.source_patch_ids),
                source_atom_ids=list(record.source_atom_ids),
                evidence_refs=list(record.evidence_refs),
                confidence=record.confidence * 0.9,
                support_count=record.support_count,
                observed_at=record.observed_at,
                updated_at=record.updated_at,
                relation_scope=record.relation_scope,
                dimension=record.dimension,
                cardinality=record.cardinality,
                active=record.active,
                features=dict(record.features),
            ))
        return results

    _STRUCTURAL_RELATION_KEYS = frozenset({
        "has_role", "instantiates", "refers_to", "grounded_by",
        "scoped_by", "supported_by", "opposed_by", "derived_from",
        "depends_on", "co_refers_with", "modifies", "teaches", "asks_about",
    })

    def _record_to_frame(self, record: DurableRelationRecord) -> RelationFrame | None:
        proposition_mode = str(record.features.get("proposition_mode", "asserted") or "asserted")
        structural = (
            record.relation_key in self._STRUCTURAL_RELATION_KEYS
            or bool(record.features.get("structural"))
            or proposition_mode == "queried"
            or bool(record.features.get("open_roles"))
        )
        qualifiers: dict[str, RelationArgument] = {}
        for role, data in record.qualifiers.items():
            if isinstance(data, Mapping):
                qualifiers[role] = RelationArgument(
                    role=role,
                    concept_id=str(data.get("concept_id", "") or ""),
                    entity_id=str(data.get("entity_id", "") or ""),
                    surface=str(data.get("surface", "") or ""),
                )
        return RelationFrame(
            relation_id=record.record_id,
            relation_key=record.relation_key,
            relation_family=record.relation_family,
            subject=RelationArgument(
                role="subject",
                concept_id=record.subject_concept_id,
                entity_id=record.subject_entity_id,
                surface=record.subject_surface,
                confidence=record.confidence,
            ),
            object=RelationArgument(
                role="object",
                concept_id=record.object_concept_id,
                entity_id=record.object_entity_id,
                surface=record.object_surface,
                confidence=record.confidence,
            ),
            qualifiers=qualifiers,
            source_edge_ids=list(record.source_patch_ids),
            source_atom_ids=list(record.source_atom_ids),
            evidence_refs=list(record.evidence_refs),
            inverse_relation_keys=list(record.inverse_relation_keys),
            confidence=record.confidence,
            answerable=record.active and not structural,
            structural=structural,
            projection_policy="none" if structural else "object",
            features={
                **dict(record.features),
                "dimension": record.dimension,
                "relation_scope": record.relation_scope,
                "cardinality": record.cardinality,
                "active": record.active,
                "superseded_by_record_id": record.superseded_by_record_id,
            },
        )
