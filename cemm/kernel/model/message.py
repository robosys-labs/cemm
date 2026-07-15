"""Language-neutral semantic message planning records."""
from __future__ import annotations

from dataclasses import dataclass, field

from .refs import FrozenMap


@dataclass(frozen=True, slots=True)
class RhetoricalRelation:
    source_item_ref: str
    target_item_ref: str
    relation_kind: str = "elaboration"


@dataclass(frozen=True, slots=True)
class MessageRoleValue:
    """A typed semantic role value used by a generated clause.

    `surface_hint` may only be copied for mention/quote use.  It is never
    treated as a schema definition or public truth by itself.
    """

    role_key: str
    value_kind: str = "semantic_ref"
    semantic_ref: str = ""
    semantic_key: str = ""
    surface_hint: str = ""
    use_mode: str = "assert"
    provenance_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LexicalRequirement:
    """A requested lexical sense and operation-relative use."""

    semantic_key: str
    use_mode: str = "assert"
    surface_hint: str = ""
    source_span_ref: str = ""
    required: bool = True


@dataclass(frozen=True, slots=True)
class MessageClauseSpec:
    """One truth/force-bearing semantic clause in a message item."""

    clause_ref: str
    predicate_key: str
    communicative_force: str = "assert"
    polarity: str = "positive"
    role_values: tuple[MessageRoleValue, ...] = ()
    lexical_requirements: tuple[LexicalRequirement, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    qualification_key: str = ""
    required: bool = True

    def role(self, key: str) -> MessageRoleValue | None:
        return next((value for value in self.role_values if value.role_key == key), None)


@dataclass(frozen=True, slots=True)
class MessageContentItem:
    semantic_ref: str
    discourse_function: str = "inform"
    stance: str = "neutral"
    focus: str = ""
    required: bool = True
    provenance_refs: tuple[str, ...] = ()

    content_kind: str = "proposition"
    predicate_key: str = ""
    role_values: tuple[MessageRoleValue, ...] = ()
    lexical_requirements: tuple[LexicalRequirement, ...] = ()
    qualification_key: str = ""
    clauses: tuple[MessageClauseSpec, ...] = ()

    def role(self, key: str) -> MessageRoleValue | None:
        for value in self.role_values:
            if value.role_key == key:
                return value
        for clause in self.clauses:
            value = clause.role(key)
            if value is not None:
                return value
        return None

    def clause(self, predicate_key: str) -> MessageClauseSpec | None:
        return next(
            (clause for clause in self.clauses if clause.predicate_key == predicate_key),
            None,
        )

    def all_lexical_requirements(self) -> tuple[LexicalRequirement, ...]:
        values = [*self.lexical_requirements]
        for clause in self.clauses:
            values.extend(clause.lexical_requirements)
        deduped: dict[tuple[str, str, str], LexicalRequirement] = {}
        for requirement in values:
            key = (
                requirement.semantic_key,
                requirement.use_mode,
                requirement.surface_hint,
            )
            deduped[key] = requirement
        return tuple(deduped.values())


@dataclass(frozen=True, slots=True)
class SemanticMessagePlan:
    id: str
    communicative_goal_refs: tuple[str, ...] = ()
    content_items: tuple[MessageContentItem, ...] = ()
    rhetorical_relations: tuple[RhetoricalRelation, ...] = ()
    addressee_refs: tuple[str, ...] = ()
    language: str = "und"
    channel: str = "text"
    style_constraints: FrozenMap = field(default_factory=FrozenMap)
