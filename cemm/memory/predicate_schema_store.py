"""PredicateSchemaStore — durable store for predicate schema records.

Seeds canonical edge-compatible schemas and supports learning new
schemas from observed relation frames. Schemas start as candidates
and are promoted through validation.
"""

from __future__ import annotations

from ..types.predicate_schema_record import PredicateSchemaRecord
import uuid


_SEED_SCHEMAS: list[dict] = [
    {
        "predicate_key": "is_a",
        "relation_family": "taxonomy",
        "argument_roles": ["child", "parent"],
        "required_roles": ["child", "parent"],
        "inverse_predicates": ["sub_type_of"],
        "inheritance_behavior": "inherit",
        "answer_projection": "parent",
        "freshness_policy": "any",
        "evidence_policy": "speaker_asserted",
    },
    {
        "predicate_key": "same_as",
        "relation_family": "identity",
        "argument_roles": ["left", "right"],
        "required_roles": ["left", "right"],
        "inverse_predicates": ["same_as"],
        "inheritance_behavior": "symmetric",
        "answer_projection": "either",
        "freshness_policy": "any",
        "evidence_policy": "speaker_asserted",
    },
    {
        "predicate_key": "part_of",
        "relation_family": "membership",
        "argument_roles": ["part", "whole"],
        "required_roles": ["part", "whole"],
        "inverse_predicates": ["has_part"],
        "inheritance_behavior": "inherit",
        "answer_projection": "whole",
        "freshness_policy": "any",
        "evidence_policy": "speaker_asserted",
    },
    {
        "predicate_key": "causes",
        "relation_family": "causal",
        "argument_roles": ["cause", "effect"],
        "required_roles": ["cause", "effect"],
        "inverse_predicates": ["caused_by"],
        "inheritance_behavior": "none",
        "answer_projection": "effect",
        "freshness_policy": "any",
        "evidence_policy": "speaker_asserted",
    },
    {
        "predicate_key": "used_for",
        "relation_family": "affordance",
        "argument_roles": ["tool", "purpose"],
        "required_roles": ["tool", "purpose"],
        "inverse_predicates": ["uses"],
        "inheritance_behavior": "inherit",
        "answer_projection": "purpose",
        "freshness_policy": "any",
        "evidence_policy": "speaker_asserted",
    },
    {
        "predicate_key": "has_property",
        "relation_family": "property",
        "argument_roles": ["owner", "property"],
        "required_roles": ["owner", "property"],
        "inverse_predicates": ["property_of"],
        "inheritance_behavior": "inherit",
        "answer_projection": "property",
        "freshness_policy": "any",
        "evidence_policy": "speaker_asserted",
    },
    {
        "predicate_key": "has_role",
        "relation_family": "role",
        "argument_roles": ["holder", "role"],
        "required_roles": ["holder", "role"],
        "inverse_predicates": ["role_of"],
        "inheritance_behavior": "inherit",
        "answer_projection": "holder",
        "freshness_policy": "any",
        "evidence_policy": "speaker_asserted",
    },
    {
        "predicate_key": "has_name",
        "relation_family": "property",
        "argument_roles": ["owner", "name"],
        "required_roles": ["owner", "name"],
        "inverse_predicates": ["name_of"],
        "inheritance_behavior": "inherit",
        "answer_projection": "name",
        "freshness_policy": "any",
        "evidence_policy": "speaker_asserted",
    },
    {
        "predicate_key": "has_age",
        "relation_family": "property",
        "argument_roles": ["owner", "age"],
        "required_roles": ["owner", "age"],
        "inverse_predicates": [],
        "inheritance_behavior": "inherit",
        "answer_projection": "age",
        "freshness_policy": "any",
        "evidence_policy": "speaker_asserted",
    },
    {
        "predicate_key": "has_alias",
        "relation_family": "property",
        "argument_roles": ["owner", "alias"],
        "required_roles": ["owner", "alias"],
        "inverse_predicates": ["alias_of"],
        "inheritance_behavior": "inherit",
        "answer_projection": "alias",
        "freshness_policy": "any",
        "evidence_policy": "speaker_asserted",
    },
    {
        "predicate_key": "name",
        "relation_family": "definition",
        "argument_roles": ["owner", "name"],
        "required_roles": ["owner", "name"],
        "inverse_predicates": ["name_of"],
        "inheritance_behavior": "inherit",
        "answer_projection": "name",
        "freshness_policy": "any",
        "evidence_policy": "speaker_asserted",
    },
    {
        "predicate_key": "purpose",
        "relation_family": "definition",
        "argument_roles": ["owner", "purpose"],
        "required_roles": ["owner", "purpose"],
        "inverse_predicates": ["purpose_of"],
        "inheritance_behavior": "inherit",
        "answer_projection": "purpose",
        "freshness_policy": "any",
        "evidence_policy": "speaker_asserted",
    },
    {
        "predicate_key": "capability",
        "relation_family": "affordance",
        "argument_roles": ["owner", "capability"],
        "required_roles": ["owner", "capability"],
        "inverse_predicates": ["capability_of"],
        "inheritance_behavior": "inherit",
        "answer_projection": "capability",
        "freshness_policy": "any",
        "evidence_policy": "speaker_asserted",
    },
    {
        "predicate_key": "creator",
        "relation_family": "definition",
        "argument_roles": ["owner", "creator"],
        "required_roles": ["owner", "creator"],
        "inverse_predicates": ["created"],
        "inheritance_behavior": "none",
        "answer_projection": "creator",
        "freshness_policy": "any",
        "evidence_policy": "speaker_asserted",
    },
    {
        "predicate_key": "architecture",
        "relation_family": "definition",
        "argument_roles": ["owner", "architecture"],
        "required_roles": ["owner", "architecture"],
        "inverse_predicates": [],
        "inheritance_behavior": "none",
        "answer_projection": "architecture",
        "freshness_policy": "any",
        "evidence_policy": "speaker_asserted",
    },
    {
        "predicate_key": "does",
        "relation_family": "affordance",
        "argument_roles": ["owner", "activity"],
        "required_roles": ["owner", "activity"],
        "inverse_predicates": [],
        "inheritance_behavior": "inherit",
        "answer_projection": "activity",
        "freshness_policy": "any",
        "evidence_policy": "speaker_asserted",
    },
    {
        "predicate_key": "knows_about",
        "relation_family": "definition",
        "argument_roles": ["owner", "topic"],
        "required_roles": ["owner", "topic"],
        "inverse_predicates": [],
        "inheritance_behavior": "inherit",
        "answer_projection": "topic",
        "freshness_policy": "any",
        "evidence_policy": "speaker_asserted",
    },
    {
        "predicate_key": "limitation",
        "relation_family": "definition",
        "argument_roles": ["owner", "limitation"],
        "required_roles": ["owner", "limitation"],
        "inverse_predicates": [],
        "inheritance_behavior": "inherit",
        "answer_projection": "limitation",
        "freshness_policy": "any",
        "evidence_policy": "speaker_asserted",
    },
    {
        "predicate_key": "answers_identity_as",
        "relation_family": "definition",
        "argument_roles": ["owner", "identity"],
        "required_roles": ["owner", "identity"],
        "inverse_predicates": [],
        "inheritance_behavior": "inherit",
        "answer_projection": "identity",
        "freshness_policy": "any",
        "evidence_policy": "speaker_asserted",
    },
]


class PredicateSchemaStore:
    def __init__(self) -> None:
        self._schemas: dict[str, PredicateSchemaRecord] = {}
        self._candidate_schemas: dict[str, PredicateSchemaRecord] = {}
        self._counterexamples: dict[str, list[dict]] = {}
        self._seed()

    def _seed(self) -> None:
        for seed in _SEED_SCHEMAS:
            schema_id = f"seed_{seed['predicate_key']}"
            record = PredicateSchemaRecord(
                schema_id=schema_id,
                predicate_key=seed["predicate_key"],
                relation_family=seed["relation_family"],
                argument_roles=list(seed["argument_roles"]),
                required_roles=list(seed["required_roles"]),
                inverse_predicates=list(seed["inverse_predicates"]),
                inheritance_behavior=seed["inheritance_behavior"],
                answer_projection=seed["answer_projection"],
                freshness_policy=seed["freshness_policy"],
                evidence_policy=seed["evidence_policy"],
                confidence=0.8,
                support_count=1,
            )
            self._schemas[seed["predicate_key"]] = record

    def get(self, predicate_key: str) -> PredicateSchemaRecord | None:
        return self._schemas.get(predicate_key)

    def get_candidate(self, predicate_key: str) -> PredicateSchemaRecord | None:
        return self._candidate_schemas.get(predicate_key)

    def all_schemas(self) -> list[PredicateSchemaRecord]:
        return list(self._schemas.values())

    def all_candidates(self) -> list[PredicateSchemaRecord]:
        return list(self._candidate_schemas.values())

    def observe_candidate(
        self,
        predicate_key: str,
        argument_roles: list[str],
        relation_family: str = "definition",
    ) -> PredicateSchemaRecord:
        existing = self._candidate_schemas.get(predicate_key)
        if existing is not None:
            existing.support_count += 1
            if argument_roles and not existing.argument_roles:
                existing.argument_roles = list(argument_roles)
            return existing

        record = PredicateSchemaRecord(
            schema_id=uuid.uuid4().hex[:16],
            predicate_key=predicate_key,
            relation_family=relation_family,
            argument_roles=list(argument_roles),
            required_roles=list(argument_roles),
            confidence=0.3,
            support_count=1,
        )
        self._candidate_schemas[predicate_key] = record
        return record

    def add_counterexample(self, predicate_key: str, example: dict) -> None:
        self._counterexamples.setdefault(predicate_key, []).append(example)

    def promote(self, predicate_key: str) -> bool:
        candidate = self._candidate_schemas.get(predicate_key)
        if candidate is None:
            return False
        counters = self._counterexamples.get(predicate_key, [])
        if counters and len(counters) >= candidate.support_count:
            return False
        if candidate.support_count < 2:
            return False
        candidate.confidence = min(0.5 + 0.1 * candidate.support_count, 0.9)
        self._schemas[predicate_key] = candidate
        del self._candidate_schemas[predicate_key]
        return True

    def inverse_of(self, predicate_key: str) -> list[str]:
        schema = self._schemas.get(predicate_key)
        if schema is not None:
            return list(schema.inverse_predicates)
        return []

    def inherits(self, predicate_key: str) -> bool:
        schema = self._schemas.get(predicate_key)
        if schema is not None:
            return schema.inheritance_behavior in ("inherit", "symmetric")
        return False

    def relation_family_for(self, predicate_key: str) -> str:
        """Return the relation family for a predicate key, or 'definition' as default."""
        schema = self._schemas.get(predicate_key)
        if schema is not None:
            return schema.relation_family
        return "definition"
