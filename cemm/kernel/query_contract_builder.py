"""QueryContractBuilder — build strict query contracts from obligation contracts.

Builds QueryContract objects that constrain the SemanticQueryEngine, eliminating
broad all-relation durable scans and unsafe surface-token fallbacks.

The query contract builder ensures:
- profile queries filter by dimension
- concept queries require target concept grounding
- self queries are scoped to self_model
- no broad all-relation scans in normal query path
"""

from __future__ import annotations

from typing import Any

from ..types.obligation_contract import QueryContract
from ..types.operational_meaning import OperationalMeaningFrame


class QueryContractBuilder:
    """Build refined QueryContract from OperationalMeaningFrame and obligation context."""

    def build(
        self,
        frame: OperationalMeaningFrame,
        durable_store: Any | None = None,
    ) -> QueryContract | None:
        if not frame.is_query:
            return None

        builder_map = {
            "user_profile_query": self._build_profile_query,
            "concept_definition_query": self._build_concept_query,
            "self_identity_query": self._build_self_query,
            "self_capability_query": self._build_self_query,
            "self_knowledge_query": self._build_self_query,
        }
        builder_fn = builder_map.get(frame.frame_type)
        if builder_fn is None:
            return None
        return builder_fn(frame, durable_store)

    def _build_profile_query(
        self,
        frame: OperationalMeaningFrame,
        durable_store: Any | None,
    ) -> QueryContract:
        dimension = frame.dimension or frame.features.get("dimension", "")
        subject_entity = frame.features.get("subject_entity_id", "") or "user"
        return QueryContract(
            query_kind="profile_dimension",
            target_scope="user_profile",
            subject_entity_id=subject_entity,
            relation_key="has_property" if frame.relation_key in ("", "asks_about") else frame.relation_key,
            relation_family="property",
            dimension=dimension,
            projection_policy="profile_value",
            target_required=True,
            ambiguity_policy="abstain",
            evidence_policy="required",
            features=dict(frame.features),
        )

    def _build_concept_query(
        self,
        frame: OperationalMeaningFrame,
        durable_store: Any | None,
    ) -> QueryContract:
        subject_concept = (
            frame.features.get("object_concept_id", "")
            or frame.features.get("subject_concept_id", "")
        )
        return QueryContract(
            query_kind="concept_definition",
            target_scope="concept_lattice",
            subject_concept_id=subject_concept,
            relation_key="is_a" if frame.relation_key in ("", "asks_about") else frame.relation_key,
            relation_family="taxonomy",
            projection_policy="concept_definition",
            target_required=True,
            ambiguity_policy="abstain",
            evidence_policy="required",
            features=dict(frame.features),
        )

    def _build_self_query(
        self,
        frame: OperationalMeaningFrame,
        durable_store: Any | None,
    ) -> QueryContract:
        query_kind_map = {
            "self_identity_query": "self_identity",
            "self_capability_query": "self_capability",
            "self_knowledge_query": "self_knowledge",
        }
        relation_key_map = {
            "self_identity_query": "answers_identity_as",
            "self_capability_query": "capability",
            "self_knowledge_query": "knows_about",
        }
        return QueryContract(
            query_kind=query_kind_map.get(frame.frame_type, "self_identity"),
            target_scope="self_model",
            subject_entity_id="self",
            relation_key=relation_key_map.get(frame.frame_type, "answers_identity_as"),
            relation_family="property",
            dimension="",
            projection_policy="self_value",
            target_required=True,
            ambiguity_policy="abstain",
            evidence_policy="required",
            features=dict(frame.features),
        )
