from __future__ import annotations

from ..learning.lexeme_memory import LexemeMemory
from ..types.action import Action, ActionKind, ActionStatus
from ..types.signal import Signal, SignalKind, SourceType
from ..types.trace import Trace
from .base import BaseOperator, OperatorContext, OperatorResult
from ..types.permission import Permission


class LearnOperator(BaseOperator):
    """Store user-taught surface-to-meaning mappings in lexeme memory.

    Handles definition, command alias, and correction events produced by the
    teaching interpreter. The operator never stores raw text; it only stores a
    canonical surface -> meaning/role mapping with confidence and trust.
    """

    def __init__(
        self,
        lexeme_memory: LexemeMemory | None = None,
        action_kind: ActionKind = ActionKind.LEARN_LEXEME,
    ) -> None:
        self._lexeme_memory = lexeme_memory
        self._action_kind = action_kind

    @property
    def action_kind(self) -> ActionKind:
        return self._action_kind

    def execute(self, ctx: OperatorContext) -> OperatorResult:
        event = ctx.params.get("teaching_event", {})
        if not event:
            return OperatorResult(
                success=False,
                output_text="I didn't catch what to learn.",
            )

        lexeme_memory = self._lexeme_memory
        if lexeme_memory is None:
            if hasattr(ctx, "lexeme_memory") and ctx.lexeme_memory is not None:
                lexeme_memory = ctx.lexeme_memory
            else:
                return OperatorResult(
                    success=False,
                    output_text="Learning memory is not available.",
                )

        kind = event.get("kind", "definition")
        surface = event.get("surface", "").lower()
        meaning = event.get("meaning", "").lower()
        role = event.get("role", "unknown")
        confidence = event.get("confidence", 0.6)
        if not surface or not meaning:
            return OperatorResult(
                success=False,
                output_text="I need both a surface form and a meaning to learn.",
            )

        if kind == "command_alias":
            lexeme_memory.learn(
                surface=surface,
                role="command_alias",
                maps_to=meaning,
                confidence=confidence,
                source="user",
            )
            output = f"Got it. When you say '{surface}', I'll remember that."
        elif kind == "correction":
            lexeme_memory.learn(
                surface=surface,
                role=role,
                maps_to=meaning,
                confidence=confidence,
                source="user",
            )
            lexeme_memory.reinforce(surface, meaning, delta=0.15)
            output = f"Thanks. I've updated '{surface}' to mean '{meaning}'."
        else:
            lexeme_memory.learn(
                surface=surface,
                role=role,
                maps_to=meaning,
                confidence=confidence,
                source="user",
            )
            output = f"Got it. '{surface}' means '{meaning}'."

        action = Action(
            id="",
            kind=ctx.params.get("action_kind", ActionKind.LEARN_LEXEME),
            operator_model_id="LearnOperator",
            input_signal_ids=[ctx.input_signal.id],
            confidence=confidence,
            status=ActionStatus.EXECUTED,
            trace=Trace(intent="learn", reason=f"learned {surface} -> {meaning}"),
            created_at=0.0,
        )

        result_signal = Signal(
            id="",
            kind=SignalKind.OUTPUT,
            source_id="cemm",
            source_type=SourceType.CEMM,
            content=output,
            observed_at=0.0,
            context_id=ctx.input_signal.context_id,
            salience=0.7,
            trust=confidence,
            permission=Permission.public(),
        )

        return OperatorResult(
            success=True,
            output_text=output,
            action=action,
            result_signal=result_signal,
        )
