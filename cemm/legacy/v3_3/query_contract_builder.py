"""Build strict query contracts from selected operational meaning frames."""

from __future__ import annotations

from typing import Any

from ...types.obligation_contract import QueryContract
from ...types.operational_meaning import OperationalMeaningFrame


class QueryContractBuilder:
    def build(
        self,
        frame: OperationalMeaningFrame,
        durable_store: Any | None = None,
    ) -> QueryContract | None:
        if not frame.is_query:
            return None
        builders = {
            "user_profile_query": self._profile,
            "concept_definition_query": self._concept,
            "self_identity_query": self._self_identity,
            "self_capability_query": self._self_capability,
            "self_knowledge_query": self._self_knowledge,
        }
        builder = builders.get(frame.frame_type)
        return builder(frame) if builder else None

    @staticmethod
    def _profile(frame: OperationalMeaningFrame) -> QueryContract:
        dimension = str(frame.dimension or frame.features.get("dimension", "") or frame.features.get("property_dimension", ""))
        cardinality = str(frame.features.get("cardinality", "optional_one") or "optional_one")
        return QueryContract(
            query_kind="profile_dimension",
            target_scope="user_profile",
            subject_entity_id=str(frame.features.get("subject_entity_id", "") or "user"),
            relation_key="has_property" if frame.relation_key in {"", "asks_about"} else frame.relation_key,
            relation_family="property",
            dimension=dimension,
            projection_policy="profile_value",
            target_required=True,
            ambiguity_policy="abstain",
            evidence_policy="required",
            result_cardinality="one" if cardinality in {"single", "optional_one"} else "ranked_many",
            result_limit=1 if cardinality in {"single", "optional_one"} else 8,
            aggregate_policy="coordinate",
            features=dict(frame.features),
        )

    @staticmethod
    def _concept(frame: OperationalMeaningFrame) -> QueryContract:
        subject_concept = str(
            frame.features.get("object_concept_id", "")
            or frame.features.get("subject_concept_id", "")
            or ""
        )
        return QueryContract(
            query_kind="concept_definition",
            target_scope="concept_lattice",
            subject_concept_id=subject_concept,
            relation_key="is_a" if frame.relation_key in {"", "asks_about"} else frame.relation_key,
            relation_family="taxonomy",
            projection_policy="concept_definition",
            target_required=True,
            ambiguity_policy="abstain",
            evidence_policy="required",
            result_cardinality="ranked_many",
            result_limit=5,
            aggregate_policy="coordinate",
            features={
                **dict(frame.features),
                "allowed_relation_keys": ["is_a", "same_as", "part_of", "used_for"],
            },
        )

    @staticmethod
    def _self_identity(frame: OperationalMeaningFrame) -> QueryContract:
        return QueryContract(
            query_kind="self_identity",
            target_scope="self_model",
            subject_entity_id="self",
            relation_key="answers_identity_as",
            relation_family="definition",
            projection_policy="self_value",
            target_required=True,
            ambiguity_policy="abstain",
            evidence_policy="required",
            result_cardinality="one",
            result_limit=1,
            aggregate_policy="first",
            features=dict(frame.features),
        )

    @staticmethod
    def _self_capability(frame: OperationalMeaningFrame) -> QueryContract:
        return QueryContract(
            query_kind="self_capability",
            target_scope="self_model",
            subject_entity_id="self",
            relation_key="capability",
            relation_family="affordance",
            projection_policy="self_value",
            target_required=True,
            ambiguity_policy="abstain",
            evidence_policy="required",
            result_cardinality="ranked_many",
            result_limit=12,
            aggregate_policy="coordinate",
            features=dict(frame.features),
        )

    @staticmethod
    def _self_knowledge(frame: OperationalMeaningFrame) -> QueryContract:
        return QueryContract(
            query_kind="self_knowledge",
            target_scope="self_model",
            subject_entity_id="self",
            relation_key="knows_about",
            relation_family="definition",
            projection_policy="self_value",
            target_required=True,
            ambiguity_policy="abstain",
            evidence_policy="required",
            result_cardinality="ranked_many",
            result_limit=8,
            aggregate_policy="coordinate",
            features=dict(frame.features),
        )
