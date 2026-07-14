"""SchemaStoreBridge — PredicateSchemaStore-compatible facade over SemanticSchemaStore.

Import boundary: model + schema submodules only.

Per ADR-005 and AUTHORITY_MATRIX:
- SemanticSchemaStore is the sole schema authority.
- This bridge exposes the PredicateSchemaStore interface for backward
  compatibility during migration, delegating all reads to the authoritative
  SemanticSchemaStore.
- Writes (observe_candidate, promote) are forwarded to SemanticSchemaStore
  lifecycle APIs.
- No competing schema resolution occurs here.
"""
from __future__ import annotations

from typing import Any

from .store import SemanticSchemaStore
from .envelope import SchemaEnvelope
from ..model.identity import Scope, ScopeLevel, Provenance, Permission

from ...types.predicate_schema_record import PredicateSchemaRecord


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


class SchemaStoreBridge:
    """PredicateSchemaStore-compatible facade over SemanticSchemaStore.

    SemanticSchemaStore is the sole authority. This bridge:
    - Seeds canonical predicate schemas into SemanticSchemaStore as active
      boot schemas at construction time.
    - Exposes the PredicateSchemaStore interface for backward compatibility.
    - Delegates all reads to SemanticSchemaStore.
    - Forwards writes (observe_candidate, promote) to SemanticSchemaStore
      lifecycle APIs.

    This is NOT a competing authority — it is a compatibility adapter.
    """

    def __init__(self, store: SemanticSchemaStore | None = None) -> None:
        self._store = store or SemanticSchemaStore()
        self._seed_predicate_schemas()

    @property
    def authoritative_store(self) -> SemanticSchemaStore:
        """Access the underlying SemanticSchemaStore (sole authority)."""
        return self._store

    def _seed_predicate_schemas(self) -> None:
        """Register seed predicate schemas as active boot schemas."""
        for seed in _SEED_SCHEMAS:
            key = seed["predicate_key"]
            record_id = f"seed:{key}:v1"
            if self._store.get(record_id) is not None:
                continue

            payload = PredicateSchemaRecord(
                schema_id=record_id,
                predicate_key=key,
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
            envelope = SchemaEnvelope(
                record_id=record_id,
                semantic_key=f"predicate:{key}",
                schema_kind="predicate",
                status="active",
                scope=Scope(level=ScopeLevel.GLOBAL),
                version=1,
                payload=payload,
                confidence=0.8,
                provenance=Provenance(source_id="boot", source_kind="boot"),
                permission=Permission.public(),
            )
            self._store.register(envelope)
            self._store.index_lexical_form(key, "en", f"predicate:{key}")

    # ── PredicateSchemaStore-compatible interface ───────────────────

    def get(self, predicate_key: str) -> PredicateSchemaRecord | None:
        """Get an active predicate schema by key."""
        candidates = self._store.find_candidates(f"predicate:{predicate_key}")
        for env in candidates:
            if env.status == "active" and env.payload is not None:
                return env.payload
        return None

    def get_candidate(self, predicate_key: str) -> PredicateSchemaRecord | None:
        """Get a candidate/provisional predicate schema by key."""
        candidates = self._store.find_candidates(f"predicate:{predicate_key}")
        for env in candidates:
            if env.status in ("candidate", "provisional") and env.payload is not None:
                return env.payload
        return None

    def all_schemas(self) -> list[PredicateSchemaRecord]:
        """Get all active predicate schemas."""
        result: list[PredicateSchemaRecord] = []
        for env in self._store.records_by_kind("predicate"):
            if env.status == "active" and env.payload is not None:
                result.append(env.payload)
        return result

    def all_candidates(self) -> list[PredicateSchemaRecord]:
        """Get all candidate/provisional predicate schemas."""
        result: list[PredicateSchemaRecord] = []
        for env in self._store.records_by_kind("predicate"):
            if env.status in ("candidate", "provisional") and env.payload is not None:
                result.append(env.payload)
        return result

    def observe_candidate(
        self,
        predicate_key: str,
        argument_roles: list[str],
        relation_family: str = "definition",
    ) -> PredicateSchemaRecord:
        """Observe a candidate predicate schema.

        Registers a candidate schema in SemanticSchemaStore. If an existing
        candidate exists, increments support count.
        """
        semantic_key = f"predicate:{predicate_key}"
        existing = self._store.find_candidates(semantic_key)
        for env in existing:
            if env.status == "candidate" and env.payload is not None:
                payload = env.payload
                payload.support_count += 1
                if argument_roles and not payload.argument_roles:
                    payload.argument_roles = list(argument_roles)
                return payload

        import uuid
        record_id = f"candidate:{predicate_key}:{uuid.uuid4().hex[:8]}"
        payload = PredicateSchemaRecord(
            schema_id=record_id,
            predicate_key=predicate_key,
            relation_family=relation_family,
            argument_roles=list(argument_roles),
            required_roles=list(argument_roles),
            confidence=0.3,
            support_count=1,
        )
        envelope = SchemaEnvelope(
            record_id=record_id,
            semantic_key=semantic_key,
            schema_kind="predicate",
            status="candidate",
            scope=Scope(level=ScopeLevel.GLOBAL),
            version=1,
            payload=payload,
            confidence=0.3,
            provenance=Provenance(source_id="observed", source_kind="observation"),
            permission=Permission.public(),
        )
        self._store.register(envelope)
        self._store.index_lexical_form(predicate_key, "en", semantic_key)
        return payload

    def inverse_of(self, predicate_key: str) -> list[str]:
        """Return inverse predicate keys for the given predicate."""
        schema = self.get(predicate_key)
        if schema is not None:
            return list(schema.inverse_predicates)
        return []

    def inherits(self, predicate_key: str) -> bool:
        """Check if the predicate inherits along taxonomy."""
        schema = self.get(predicate_key)
        if schema is not None:
            return schema.inheritance_behavior in ("inherit", "symmetric")
        return False

    def relation_family_for(self, predicate_key: str) -> str:
        """Return the relation family for a predicate key, or 'definition' as default."""
        schema = self.get(predicate_key)
        if schema is not None:
            return schema.relation_family
        return "definition"

    def add_counterexample(self, predicate_key: str, example: dict) -> None:
        """Add a counterexample for a candidate predicate."""
        # Stored in payload — no separate counterexample store in SemanticSchemaStore
        # This is a compatibility no-op during migration
        pass

    def promote(self, predicate_key: str) -> bool:
        """Promote a candidate predicate to active status.

        Uses SemanticSchemaStore lifecycle: candidate → provisional → active.
        """
        semantic_key = f"predicate:{predicate_key}"
        candidates = self._store.find_candidates(semantic_key)
        for env in candidates:
            if env.status == "candidate":
                # Check support count threshold
                if env.payload is None or env.payload.support_count < 2:
                    return False
                # Transition to provisional, then active
                rev = self._store.get_revision(env.record_id)
                if rev is None:
                    return False
                result = self._store.transition_to_provisional(env.record_id, rev)
                if result.status.value != "activated":
                    return False
                # Now activate
                rev = self._store.get_revision(env.record_id)
                if rev is None:
                    return False
                result = self._store.activate(env.record_id, rev)
                return result.status.value == "activated"
        return False
