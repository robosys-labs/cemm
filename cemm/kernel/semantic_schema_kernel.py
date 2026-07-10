"""Semantic Schema Kernel — canonical boot knowledge for semantic interpretation.

Seven schema registries loaded from JSON files in cemm/data/semantic_schemas/:
  EntityKindSchema, StateDimensionSchema, SlotSchema, ActionOperatorSchema,
  AffordanceSchema, ProjectionPolicySchema, PatchOperationSchema.

Central invariant:
  Verbs evoke action schemas. Nouns evoke entity-kind candidates.
  States occupy dimensions on entity slots.
  Actions are operators over typed slots producing state/relation deltas.

Schema JSON is canonical boot knowledge.
Runtime truth is validated graph-patch memory.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


_SCHEMAS_DIR = Path(__file__).parent.parent / "data" / "semantic_schemas"


# ── Schema dataclasses ──────────────────────────────────────────────────


@dataclass(frozen=True)
class StateDimensionSchema:
    state_family: str
    dimensions: dict[str, dict[str, Any]]
    applies_to: list[str]


@dataclass(frozen=True)
class EntityKindSchema:
    entity_kind: str
    native_slots: dict[str, dict[str, Any]]
    parent_kind: str | None


@dataclass(frozen=True)
class SlotSchema:
    slot_key: str
    description: str
    cardinality: str
    default_projection: str


@dataclass(frozen=True)
class ActionOperatorSchema:
    action_key: str
    operator_family: str
    aliases: dict[str, list[str]]
    slots: dict[str, dict[str, Any]]
    preconditions: list[dict[str, Any]]
    state_deltas: list[dict[str, Any]]
    relation_deltas: list[dict[str, Any]]
    needs_satisfied: list[str]
    risk: str
    permission_policy: str
    safety_category: str
    emotional_valence: str


@dataclass(frozen=True)
class AffordanceSchema:
    affordance_key: str
    trigger_pattern: dict[str, Any]
    required_bindings: list[str]
    effect_type: str
    predicted_patch_template: dict[str, Any]
    confidence: float


@dataclass(frozen=True)
class ProjectionPolicySchema:
    policy_key: str
    description: str
    applies_to: str
    structural: bool
    answerable: bool
    projection: str


@dataclass(frozen=True)
class PatchOperationSchema:
    operation_key: str
    description: str
    parameters: dict[str, dict[str, Any]]
    uol_compilation: dict[str, Any]


# ── Registries ──────────────────────────────────────────────────────────


class StateDimensionRegistry:
    def __init__(self, schemas: list[StateDimensionSchema]) -> None:
        self._by_family: dict[str, StateDimensionSchema] = {s.state_family: s for s in schemas}

    def get(self, state_family: str) -> StateDimensionSchema | None:
        return self._by_family.get(state_family)

    def dimension_exists(self, state_family: str, dimension: str) -> bool:
        schema = self._by_family.get(state_family)
        return schema is not None and dimension in schema.dimensions

    def applies_to(self, state_family: str, entity_kind: str) -> bool:
        schema = self._by_family.get(state_family)
        return schema is not None and entity_kind in schema.applies_to

    def all_families(self) -> list[str]:
        return list(self._by_family.keys())

    def is_safety_relevant(self, state_family: str, dimension: str) -> bool:
        """Check if a dimension has a harmful_polarity defined, making it safety-relevant."""
        schema = self._by_family.get(state_family)
        if schema is None:
            return False
        dim_def = schema.dimensions.get(dimension, {})
        return "harmful_polarity" in dim_def

    def is_harmful_direction(self, state_family: str, dimension: str, direction: str) -> bool:
        """Check if a direction moves toward the harmful polarity of a dimension.

        Uses the ``harmful_polarity`` field from ``state_dimension_schemas.json``:
        - ``"negative"`` means ``decrease`` is harmful (toward ``polarity_negative``)
        - ``"positive"`` means ``increase`` is harmful (toward ``polarity_positive``)
        """
        schema = self._by_family.get(state_family)
        if schema is None:
            return False
        dim_def = schema.dimensions.get(dimension, {})
        harmful_polarity = dim_def.get("harmful_polarity", "")
        if harmful_polarity == "negative":
            return direction == "decrease"
        if harmful_polarity == "positive":
            return direction == "increase"
        return False


class EntityKindRegistry:
    def __init__(self, schemas: list[EntityKindSchema]) -> None:
        self._by_kind: dict[str, EntityKindSchema] = {s.entity_kind: s for s in schemas}

    def get(self, entity_kind: str) -> EntityKindSchema | None:
        return self._by_kind.get(entity_kind)

    def native_slot(self, entity_kind: str, slot_path: str) -> dict[str, Any] | None:
        schema = self._by_kind.get(entity_kind)
        if schema is None:
            return None
        return schema.native_slots.get(slot_path)

    def is_answerable_slot(self, entity_kind: str, slot_path: str) -> bool:
        slot = self.native_slot(entity_kind, slot_path)
        if slot is None:
            return False
        return slot.get("projection") == "answerable"

    def all_kinds(self) -> list[str]:
        return list(self._by_kind.keys())

    def is_subclass_of(self, kind: str, ancestor: str) -> bool:
        if kind == ancestor:
            return True
        schema = self._by_kind.get(kind)
        if schema is None or schema.parent_kind is None:
            return False
        return self.is_subclass_of(schema.parent_kind, ancestor)


class SlotRegistry:
    def __init__(self, schemas: list[SlotSchema]) -> None:
        self._by_key: dict[str, SlotSchema] = {s.slot_key: s for s in schemas}

    def get(self, slot_key: str) -> SlotSchema | None:
        return self._by_key.get(slot_key)

    def default_projection(self, slot_key: str) -> str:
        schema = self._by_key.get(slot_key)
        return schema.default_projection if schema else "structural"


class ActionOperatorRegistry:
    def __init__(self, schemas: list[ActionOperatorSchema]) -> None:
        self._by_key: dict[str, ActionOperatorSchema] = {s.action_key: s for s in schemas}
        self._alias_to_key: dict[str, str] = {}
        self._lang_alias_to_key: dict[str, dict[str, str]] = {}
        for s in schemas:
            for lang, aliases in s.aliases.items():
                if lang not in self._lang_alias_to_key:
                    self._lang_alias_to_key[lang] = {}
                for alias in aliases:
                    normalized = alias.strip().lower()
                    self._alias_to_key[normalized] = s.action_key
                    self._lang_alias_to_key[lang][normalized] = s.action_key

    def get(self, action_key: str) -> ActionOperatorSchema | None:
        return self._by_key.get(action_key)

    def lookup_alias(self, surface: str, language: str = "en") -> str | None:
        normalized = surface.strip().lower()
        lang_map = self._lang_alias_to_key.get(language, {})
        return lang_map.get(normalized)

    def all_action_keys(self) -> list[str]:
        return list(self._by_key.keys())

    def slots_for(self, action_key: str) -> dict[str, dict[str, Any]]:
        schema = self._by_key.get(action_key)
        return schema.slots if schema else {}

    def state_deltas_for(self, action_key: str) -> list[dict[str, Any]]:
        schema = self._by_key.get(action_key)
        return schema.state_deltas if schema else []

    def relation_deltas_for(self, action_key: str) -> list[dict[str, Any]]:
        schema = self._by_key.get(action_key)
        return schema.relation_deltas if schema else []

    def needs_satisfied_for(self, action_key: str) -> list[str]:
        schema = self._by_key.get(action_key)
        return schema.needs_satisfied if schema else []

    def safety_category_for(self, action_key: str) -> str:
        schema = self._by_key.get(action_key)
        return schema.safety_category if schema else ""

    def permission_policy_for(self, action_key: str) -> str:
        schema = self._by_key.get(action_key)
        return schema.permission_policy if schema else "normal"

    def risk_for(self, action_key: str) -> str:
        schema = self._by_key.get(action_key)
        return schema.risk if schema else "low"

    def emotional_valence_for(self, action_key: str) -> str:
        schema = self._by_key.get(action_key)
        return schema.emotional_valence if schema else "neutral"


class AffordanceRegistry:
    def __init__(self, schemas: list[AffordanceSchema]) -> None:
        self._by_key: dict[str, AffordanceSchema] = {s.affordance_key: s for s in schemas}

    def get(self, affordance_key: str) -> AffordanceSchema | None:
        return self._by_key.get(affordance_key)

    def all(self) -> list[AffordanceSchema]:
        return list(self._by_key.values())


class ProjectionPolicyRegistry:
    def __init__(self, schemas: list[ProjectionPolicySchema]) -> None:
        self._by_key: dict[str, ProjectionPolicySchema] = {s.policy_key: s for s in schemas}
        self._by_applies: dict[str, ProjectionPolicySchema] = {s.applies_to: s for s in schemas}

    def get(self, policy_key: str) -> ProjectionPolicySchema | None:
        return self._by_key.get(policy_key)

    def for_applies_to(self, applies_to: str) -> ProjectionPolicySchema | None:
        return self._by_applies.get(applies_to)

    def is_structural(self, applies_to: str) -> bool:
        p = self._by_applies.get(applies_to)
        return p.structural if p else True

    def is_answerable(self, applies_to: str) -> bool:
        p = self._by_applies.get(applies_to)
        return p.answerable if p else False


class PatchOperationRegistry:
    def __init__(self, schemas: list[PatchOperationSchema]) -> None:
        self._by_key: dict[str, PatchOperationSchema] = {s.operation_key: s for s in schemas}

    def get(self, operation_key: str) -> PatchOperationSchema | None:
        return self._by_key.get(operation_key)

    def uol_compilation_for(self, operation_key: str) -> dict[str, Any] | None:
        schema = self._by_key.get(operation_key)
        return schema.uol_compilation if schema else None

    def is_known(self, operation_key: str) -> bool:
        return operation_key in self._by_key

    def all_keys(self) -> list[str]:
        return list(self._by_key.keys())


# ── Kernel container ────────────────────────────────────────────────────


class SemanticSchemaKernel:
    """Unified container for all seven schema registries.

    This is the single entry point for schema-driven semantic interpretation.
    Language adapters, graph builders, frame compilers, affordance predictors,
    and patch extractors all reference this kernel instead of hardcoded dicts.
    """

    def __init__(
        self,
        state_dimensions: StateDimensionRegistry,
        entity_kinds: EntityKindRegistry,
        slots: SlotRegistry,
        action_operators: ActionOperatorRegistry,
        affordances: AffordanceRegistry,
        projection_policies: ProjectionPolicyRegistry,
        patch_operations: PatchOperationRegistry,
    ) -> None:
        self.state_dimensions = state_dimensions
        self.entity_kinds = entity_kinds
        self.slots = slots
        self.action_operators = action_operators
        self.affordances = affordances
        self.projection_policies = projection_policies
        self.patch_operations = patch_operations

    @classmethod
    def from_directory(cls, schemas_dir: Path | None = None) -> SemanticSchemaKernel:
        """Load all schema files from the given directory (or default)."""
        d = schemas_dir or _SCHEMAS_DIR

        def _load(name: str) -> Any:
            return json.loads((d / name).read_text(encoding="utf-8"))

        state_dim_data = _load("state_dimension_schemas.json")
        entity_kind_data = _load("entity_kind_schemas.json")
        slot_data = _load("slot_schemas.json")
        action_data = _load("action_operator_schemas.json")
        affordance_data = _load("affordance_schemas.json")
        projection_data = _load("projection_policy_schemas.json")
        patch_op_data = _load("patch_operation_schemas.json")

        return cls(
            state_dimensions=StateDimensionRegistry([
                StateDimensionSchema(
                    state_family=s["state_family"],
                    dimensions=s["dimensions"],
                    applies_to=s["applies_to"],
                ) for s in state_dim_data
            ]),
            entity_kinds=EntityKindRegistry([
                EntityKindSchema(
                    entity_kind=s["entity_kind"],
                    native_slots=s["native_slots"],
                    parent_kind=s.get("parent_kind"),
                ) for s in entity_kind_data
            ]),
            slots=SlotRegistry([
                SlotSchema(
                    slot_key=s["slot_key"],
                    description=s["description"],
                    cardinality=s["cardinality"],
                    default_projection=s["default_projection"],
                ) for s in slot_data
            ]),
            action_operators=ActionOperatorRegistry([
                ActionOperatorSchema(
                    action_key=s["action_key"],
                    operator_family=s["operator_family"],
                    aliases=s.get("aliases", {}),
                    slots=s.get("slots", {}),
                    preconditions=s.get("preconditions", []),
                    state_deltas=s.get("state_deltas", []),
                    relation_deltas=s.get("relation_deltas", []),
                    needs_satisfied=s.get("needs_satisfied", []),
                    risk=s.get("risk", "low"),
                    permission_policy=s.get("permission_policy", "normal"),
                    safety_category=s.get("safety_category", ""),
                    emotional_valence=s.get("emotional_valence", "neutral"),
                ) for s in action_data
            ]),
            affordances=AffordanceRegistry([
                AffordanceSchema(
                    affordance_key=s["affordance_key"],
                    trigger_pattern=s["trigger_pattern"],
                    required_bindings=s.get("required_bindings", []),
                    effect_type=s["effect_type"],
                    predicted_patch_template=s.get("predicted_patch_template", {}),
                    confidence=s.get("confidence", 0.7),
                ) for s in affordance_data
            ]),
            projection_policies=ProjectionPolicyRegistry([
                ProjectionPolicySchema(
                    policy_key=s["policy_key"],
                    description=s["description"],
                    applies_to=s["applies_to"],
                    structural=s["structural"],
                    answerable=s["answerable"],
                    projection=s["projection"],
                ) for s in projection_data
            ]),
            patch_operations=PatchOperationRegistry([
                PatchOperationSchema(
                    operation_key=s["operation_key"],
                    description=s["description"],
                    parameters=s.get("parameters", {}),
                    uol_compilation=s.get("uol_compilation", {}),
                ) for s in patch_op_data
            ]),
        )


_kernel_instance: SemanticSchemaKernel | None = None


def get_kernel() -> SemanticSchemaKernel:
    """Get or create the singleton SemanticSchemaKernel instance."""
    global _kernel_instance
    if _kernel_instance is None:
        _kernel_instance = SemanticSchemaKernel.from_directory()
    return _kernel_instance


__all__ = [
    "SemanticSchemaKernel",
    "StateDimensionRegistry",
    "EntityKindRegistry",
    "SlotRegistry",
    "ActionOperatorRegistry",
    "AffordanceRegistry",
    "ProjectionPolicyRegistry",
    "PatchOperationRegistry",
    "StateDimensionSchema",
    "EntityKindSchema",
    "SlotSchema",
    "ActionOperatorSchema",
    "AffordanceSchema",
    "ProjectionPolicySchema",
    "PatchOperationSchema",
    "get_kernel",
]
