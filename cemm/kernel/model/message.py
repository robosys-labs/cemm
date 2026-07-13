"""SemanticMessagePlan — language-neutral response content planning.

Import boundary: standard library only → refs.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .refs import FrozenMap


@dataclass(frozen=True, slots=True)
class RhetoricalRelation:
    """A rhetorical relation between message content items."""
    source_item_ref: str
    target_item_ref: str
    relation_kind: str = "elaboration"  # elaboration, contrast, cause, condition, etc.


@dataclass(frozen=True, slots=True)
class MessageContentItem:
    """A single content item in a semantic message plan."""
    semantic_ref: str
    discourse_function: str = "inform"  # inform, query, request, acknowledge, correct, etc.
    stance: str = "neutral"  # neutral, supportive, oppositional, hedged
    focus: str = ""
    required: bool = True
    provenance_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SemanticMessagePlan:
    """A language-neutral plan for response content.

    Response content begins from propositions, assessments, ledger,
    and commit outcomes — not from raw text or templates.
    """
    id: str
    communicative_goal_refs: tuple[str, ...] = ()  # Ref[GoalRecord]
    content_items: tuple[MessageContentItem, ...] = ()
    rhetorical_relations: tuple[RhetoricalRelation, ...] = ()
    addressee_refs: tuple[str, ...] = ()  # Ref[Referent]
    language: str = "und"
    channel: str = "text"
    style_constraints: FrozenMap = field(default_factory=FrozenMap)
