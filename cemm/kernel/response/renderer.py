"""Semantically authorized message realization.

The renderer chooses language form only after each required content word has a
licensed realization. Unknown user words are copied solely in mention mode.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable

from ..model.message import MessageContentItem, SemanticMessagePlan
from .lexical_use import (
    ItemRealizationAuthorization,
    LexicalUseGate,
    RealizationAuthorization,
)


@dataclass(frozen=True, slots=True)
class RealizedClause:
    semantic_ref: str
    surface_text: str
    provenance_refs: tuple[str, ...] = ()
    discourse_function: str = "inform"
    stance: str = "asserted"


@dataclass(frozen=True, slots=True)
class SurfacePayload:
    plan_ref: str
    clauses: tuple[RealizedClause, ...] = ()
    surface_text: str = ""
    language: str = "und"
    channel: str = "text"
    realized_item_refs: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    blocked_item_refs: tuple[str, ...] = ()


class MessageRenderer:
    """Realize authorized semantic content without inventing content."""

    def __init__(self, schema_store: Any | None = None) -> None:
        self._gate = LexicalUseGate(schema_store)

    def render(
        self,
        plan: SemanticMessagePlan,
        language: str = "en",
        authorization: RealizationAuthorization | None = None,
        environment_fingerprint: str = "",
    ) -> SurfacePayload:
        if plan is None:
            return SurfacePayload(plan_ref="", surface_text="")

        authorization = authorization or self._gate.authorize_plan(
            plan,
            language=language,
            environment_fingerprint=environment_fingerprint,
        )

        clauses: list[RealizedClause] = []
        realized_refs: list[str] = []
        provenance: list[str] = []
        blocked: list[str] = []

        for item in plan.content_items:
            item_auth = authorization.for_item(item.semantic_ref)
            if item_auth is None or not item_auth.authorized:
                blocked.append(item.semantic_ref)
                continue
            text = self._render_item(item, item_auth, language)
            if not text:
                blocked.append(item.semantic_ref)
                continue
            clause = RealizedClause(
                semantic_ref=item.semantic_ref,
                surface_text=text,
                provenance_refs=item.provenance_refs,
                discourse_function=item.discourse_function,
                stance=item.stance,
            )
            clauses.append(clause)
            realized_refs.append(item.semantic_ref)
            provenance.extend(item.provenance_refs)

        surface_text = " ".join(clause.surface_text for clause in clauses)
        return SurfacePayload(
            plan_ref=plan.id,
            clauses=tuple(clauses),
            surface_text=surface_text,
            language=language,
            channel=plan.channel,
            realized_item_refs=tuple(realized_refs),
            provenance_refs=tuple(dict.fromkeys(ref for ref in provenance if ref)),
            blocked_item_refs=tuple(blocked),
        )

    def authorize(
        self,
        plan: SemanticMessagePlan,
        language: str = "en",
        environment_fingerprint: str = "",
    ) -> RealizationAuthorization:
        return self._gate.authorize_plan(
            plan,
            language=language,
            environment_fingerprint=environment_fingerprint,
        )

    def _render_item(
        self,
        item: MessageContentItem,
        authorization: ItemRealizationAuthorization,
        language: str,
    ) -> str:
        if language.split("-", 1)[0] != "en":
            # A language pack must provide its own renderer. Silent English
            # fallback would misrepresent multilingual competence.
            return ""

        kind = item.content_kind
        required_predicates = {
            "social_greeting": {"greet"},
            "self_capability_status": {"capable_of"},
            "learning_probe": {"recognizes_form", "has_usable_definition", "means"},
            "dialogue_gap_explanation": {"requires_information", "means"},
            "attributed_receipt": {"receives"},
            "information_request": {"requests"},
            "commit_success": {"stores"},
            "commit_failure": {"completes"},
            "repair": {"corrects"},
            "honest_abstention": {"has_sufficient_information"},
        }.get(kind, set())
        available_predicates = {clause.predicate_key for clause in item.clauses}
        if required_predicates - available_predicates:
            return ""

        if kind == "social_greeting":
            return self._sentence(self._word(authorization, "greet", "hello"))
        if kind == "self_capability_status":
            capable = self._word(authorization, "capable_of", "can")
            answer = self._word(authorization, "answer_record", "answer")
            return self._sentence(f"I {capable} {answer}")
        if kind == "learning_probe":
            return self._render_learning_probe(item, authorization)
        if kind == "learning_progress":
            return self._render_learning_progress(item, authorization)
        if kind == "dialogue_gap_explanation":
            return self._render_gap_explanation(item, authorization)
        if kind == "attributed_receipt":
            received = self._word(authorization, "receives", "received")
            information = self._word(authorization, "information_object", "information")
            return self._sentence(f"I {received} that {information}")
        if kind == "information_request":
            content = item.role("content")
            if content is not None and content.semantic_key == "name":
                name = self._word(authorization, "name", "name")
                return f"What is your {name}?"
            request = self._word(authorization, "requests", "give")
            return self._sentence(f"{request} that information")
        if kind == "commit_success":
            return self._sentence(self._word(authorization, "stores", "stored"))
        if kind == "commit_failure":
            complete = self._word(authorization, "completes", "complete")
            return self._sentence("couldn't " + complete)
        if kind == "repair":
            correct = self._word(authorization, "corrects", "correct")
            answer = self._word(authorization, "answer_record", "answer")
            return self._sentence(f"{correct}ing the {answer}")
        if kind == "honest_abstention":
            enough = self._word(authorization, "grammar:quantifier_sufficiency", "enough")
            information = self._word(authorization, "information_object", "information")
            return self._sentence(f"not {enough} {information}")
        return ""

    def _render_learning_probe(
        self,
        item: MessageContentItem,
        auth: ItemRealizationAuthorization,
    ) -> str:
        target = self._quoted_role(item, "target")
        if not target:
            return ""
        recognize = self._word(auth, "recognizes_form", "recognize")
        word = self._word(auth, "lexical_form", "word")
        definition = self._word(auth, "semantic_definition", "definition")
        have = self._word(auth, "has_usable_definition", "have")
        mean = self._word(auth, "means", "mean")
        person = self._word(auth, "person", "person")
        role = self._word(auth, "role", "role")
        both = self._word(auth, "grammar:quantifier_both", "both")
        return (
            f"I {recognize} the {word} {target}, but I do not {have} its {definition}. "
            f"Does {target} {mean} a {person}, a {role}, or {both}?"
        )

    def _render_learning_progress(
        self,
        item: MessageContentItem,
        auth: ItemRealizationAuthorization,
    ) -> str:
        target = self._quoted_role(item, "target")
        accepted_role = item.role("accepted")
        accepted = []
        if accepted_role and accepted_role.semantic_ref:
            accepted = [
                self._quote(value)
                for value in accepted_role.semantic_ref.split("|")
                if value
            ]
        explanation = self._word(auth, "explanation", "explanation")
        link = self._word(auth, "associates", "links")
        need = self._word(auth, "requires_information", "need")
        distinction = self._word(auth, "semantic_distinction", "distinction")
        role = self._word(auth, "role", "role")
        person = self._word(auth, "person", "person")
        mean = self._word(auth, "means", "mean")
        both = self._word(auth, "grammar:quantifier_both", "both")
        accepted_text = self._coordinate(accepted)
        incomplete = self._word(auth, "is_incomplete", "incomplete")
        first = (
            f"Your {explanation} {link} {target} with {accepted_text}."
            if target and accepted_text
            else f"The {explanation} is {incomplete}."
        )
        remaining_role = item.role("remaining_fields")
        remaining = set(
            value for value in (
                (remaining_role.semantic_ref.split("|") if remaining_role and remaining_role.semantic_ref else [])
            ) if value
        )
        if "denotation_role_or_holder" in remaining:
            return (
                f"{first} I {need} the {role}/{person} {distinction}. "
                f"Does {target} {mean} the {role}, the {person}, or {both}?"
            )
        if remaining & {"example", "non_example", "differentiator"}:
            give = self._word(auth, "requests", "give")
            example = self._word(auth, "example", "example")
            non_example = self._word(auth, "non_example", "non-example")
            return f"{first} {give.capitalize()} one {example} and one {non_example}."
        return first

    def _render_gap_explanation(
        self,
        item: MessageContentItem,
        auth: ItemRealizationAuthorization,
    ) -> str:
        target = self._quoted_role(item, "target")
        need = self._word(auth, "requires_information", "need")
        distinction = self._word(auth, "semantic_distinction", "distinction")
        role = self._word(auth, "role", "role")
        person = self._word(auth, "person", "person")
        mean = self._word(auth, "means", "mean")
        both = self._word(auth, "grammar:quantifier_both", "both")
        return (
            f"I {need} the {role}/{person} {distinction} for {target}: "
            f"does it {mean} the {role}, the {person}, or {both}?"
        )

    @staticmethod
    def _word(
        authorization: ItemRealizationAuthorization,
        semantic_key: str,
        default: str,
    ) -> str:
        return authorization.surface_for(semantic_key, default)

    @classmethod
    def _quoted_role(cls, item: MessageContentItem, role_key: str) -> str:
        role = item.role(role_key)
        if role is None or role.use_mode not in {"mention", "quote"}:
            return ""
        return cls._quote(role.surface_hint)

    @staticmethod
    def _quote(value: str) -> str:
        value = value.strip().replace("“", "").replace("”", "")
        return f"“{value}”" if value else ""

    @staticmethod
    def _coordinate(values: list[str]) -> str:
        values = list(dict.fromkeys(value for value in values if value))
        if not values:
            return ""
        if len(values) == 1:
            return values[0]
        if len(values) == 2:
            return f"{values[0]} and {values[1]}"
        return ", ".join(values[:-1]) + f", and {values[-1]}"

    @staticmethod
    def _sentence(text: str) -> str:
        text = text.strip()
        if not text:
            return ""
        text = text[0].upper() + text[1:]
        return text if text.endswith((".", "?", "!")) else text + "."

    def validate_round_trip(
        self,
        payload: SurfacePayload,
        reparse_fn: Callable[[str], Any] | None = None,
        semantic_equivalence_fn: Callable[[Any, tuple[str, ...]], bool] | None = None,
        equivalence_fn: Callable[[SurfacePayload, Any], bool] | None = None,
    ) -> bool:
        if not payload.surface_text:
            return not payload.realized_item_refs

        internal_patterns = (
            r"\b(?:op|boot|schema|port|placeholder|prop|pred|ctx|interp|mut|ms):",
        )
        if any(re.search(pattern, payload.surface_text) for pattern in internal_patterns):
            return False

        if reparse_fn is None:
            return True
        try:
            reparsed = reparse_fn(payload.surface_text)
        except Exception:
            return False
        if reparsed is None:
            return False
        if equivalence_fn is not None:
            return bool(equivalence_fn(payload, reparsed))
        if semantic_equivalence_fn is None:
            # A non-null parse is insufficient to claim semantic round-trip.
            return False
        return bool(semantic_equivalence_fn(reparsed, payload.realized_item_refs))
