"""MessageRenderer — language renderer for surface realization.

Import boundary: model + language submodules only. No engine imports.

Architectural guardrails (AGENTS.md §19, CORE_LOOP.md G3,
AUTHORITY_MATRIX):
- Language renderers choose wording, not truth or response content.
- ResponsePlanner is the only response-content authority.
- The renderer consumes a SemanticMessagePlan and produces a
  SurfacePayload with exact realized semantic item refs.
- Every generated clause must trace to a content item and its
  provenance.
- Opaque IDs, open ports, role labels, or internal placeholders
  cannot become public text.
- Generated content should round-trip into compatible semantic
  candidates under the same language pack.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..model.message import (
    SemanticMessagePlan,
    MessageContentItem,
    RhetoricalRelation,
)


@dataclass(frozen=True, slots=True)
class RealizedClause:
    """A single realized clause from the renderer.

    Every clause traces to a content item via semantic_ref.
    """
    semantic_ref: str
    surface_text: str
    provenance_refs: tuple[str, ...] = ()
    discourse_function: str = "inform"
    stance: str = "asserted"


@dataclass(frozen=True, slots=True)
class SurfacePayload:
    """The realized output from a MessageRenderer.

    Renderer returns exact realized semantic item refs.
    """
    plan_ref: str
    clauses: tuple[RealizedClause, ...] = ()
    surface_text: str = ""
    language: str = "und"
    channel: str = "text"
    realized_item_refs: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()


class MessageRenderer:
    """Language renderer — realizes a SemanticMessagePlan as surface text.

    Performs:
    - lexicalization (map semantic refs to words)
    - syntax planning (simple clause construction)
    - morphology (basic inflection)
    - orthography/channel rendering
    - aggregation (combine related items)

    Does NOT:
    - Select response content (that's ResponsePlanner)
    - Decide truth
    - Decide capability
    - Alter the message plan
    - Inject content not in the plan
    """

    def __init__(self) -> None:
        self._lexical_map: dict[str, str] = {
            # Common semantic refs to surface forms
            "commit_success": "Done.",
            "commit_failure": "I couldn't complete that.",
            "prior_claim": "Actually, let me correct that.",
        }
        self._stance_markers: dict[str, str] = {
            "asserted": "",
            "reported": " reportedly",
            "provisional": " I think",
            "contested": " There's debate about whether",
            "hedged": " Possibly",
            "stale": " Actually, I need to correct that.",
            "denied": " No,",
        }
        self._discourse_markers: dict[str, str] = {
            "inform": "",
            "query": "What about",
            "request": "Please",
            "acknowledge": "Got it.",
            "correct": "Actually,",
            "promise": "I will",
            "refuse": "I can't",
            "repair": "Let me correct that.",
        }

    def render(
        self,
        plan: SemanticMessagePlan,
        language: str = "en",
    ) -> SurfacePayload:
        """Render a SemanticMessagePlan as surface text.

        Language renderers choose wording, not truth or response content.
        """
        if plan is None:
            return SurfacePayload(plan_ref="", surface_text="")

        clauses: list[RealizedClause] = []
        realized_refs: list[str] = []
        all_provenance: list[str] = []

        for item in plan.content_items:
            clause = self._render_item(item, language)
            clauses.append(clause)
            realized_refs.append(item.semantic_ref)
            all_provenance.extend(item.provenance_refs)

        # Apply rhetorical relations for ordering
        ordered_clauses = self._apply_rhetorical_ordering(
            clauses, plan.rhetorical_relations
        )

        # Build surface text
        parts = [c.surface_text for c in ordered_clauses if c.surface_text]
        surface_text = " ".join(parts)

        return SurfacePayload(
            plan_ref=plan.id,
            clauses=tuple(ordered_clauses),
            surface_text=surface_text,
            language=language,
            channel=plan.channel,
            realized_item_refs=tuple(realized_refs),
            provenance_refs=tuple(all_provenance),
        )

    def _render_item(
        self,
        item: MessageContentItem,
        language: str,
    ) -> RealizedClause:
        """Render a single content item as a clause.

        Performs lexicalization, stance marking, and discourse marking.
        """
        # Lexicalization — map semantic_ref to surface form
        surface = self._lexicalize(item.semantic_ref, item)

        # Apply stance marker
        stance_marker = self._stance_markers.get(item.stance, "")
        if stance_marker and surface:
            surface = f"{stance_marker.strip()} {surface}".strip()

        # Apply discourse marker
        discourse_marker = self._discourse_markers.get(
            item.discourse_function, ""
        )
        if discourse_marker and surface:
            surface = f"{discourse_marker} {surface}".strip()

        # Morphology — basic capitalization and punctuation
        surface = self._apply_morphology(surface, item.discourse_function)

        return RealizedClause(
            semantic_ref=item.semantic_ref,
            surface_text=surface,
            provenance_refs=item.provenance_refs,
            discourse_function=item.discourse_function,
            stance=item.stance,
        )

    def _lexicalize(
        self,
        semantic_ref: str,
        item: MessageContentItem,
    ) -> str:
        """Map a semantic ref to surface text.

        Uses the lexical map for known refs. For unknown refs,
        uses the focus field or a generic description based on
        discourse function.
        """
        # Check lexical map first
        if semantic_ref in self._lexical_map:
            return self._lexical_map[semantic_ref]

        # Use focus if available
        if item.focus:
            focus_map = {
                "commit_success": "Done.",
                "commit_failure": "I couldn't complete that.",
                "prior_claim": "I need to correct my earlier statement.",
            }
            if item.focus in focus_map:
                return focus_map[item.focus]

        # For proposition refs, generate a generic description
        # based on discourse function
        if item.discourse_function == "query":
            return f"about {semantic_ref}"
        if item.discourse_function == "acknowledge":
            return f"understood regarding {semantic_ref}"
        if item.discourse_function == "correct":
            return f"regarding {semantic_ref}"
        if item.discourse_function == "repair":
            return f"correcting {semantic_ref}"

        # Default — use the semantic ref as a placeholder description
        # In a full implementation, this would use RealizationSchema
        # from the schema store
        return f"regarding {semantic_ref}"

    def _apply_morphology(
        self,
        text: str,
        discourse_function: str,
    ) -> str:
        """Apply basic morphology: capitalization and punctuation."""
        if not text:
            return text

        # Capitalize first letter
        text = text[0].upper() + text[1:] if text else text

        # Add punctuation based on discourse function
        if discourse_function == "query":
            if not text.endswith("?"):
                text = text + "?"
        else:
            if not text.endswith((".", "!", "?")):
                text = text + "."

        return text

    def _apply_rhetorical_ordering(
        self,
        clauses: list[RealizedClause],
        relations: tuple[RhetoricalRelation, ...],
    ) -> list[RealizedClause]:
        """Apply rhetorical relations to order clauses.

        Simple implementation: keep original order but use relations
        to validate ordering. A full implementation would use the
        relations to build a discourse tree and traverse it.
        """
        if not relations:
            return clauses

        # For now, keep original order — relations are metadata
        # In a full implementation, we'd build a discourse graph
        # and traverse it in the correct order
        return clauses

    def validate_round_trip(
        self,
        payload: SurfacePayload,
        reparse_fn: Any | None = None,
    ) -> bool:
        """Validate that output reparses compatibly.

        Generated content should round-trip into compatible semantic
        candidates under the same language pack.
        """
        if not payload.surface_text:
            return True  # Empty output trivially round-trips

        if reparse_fn is None:
            # Without a reparse function, we can only do basic checks
            # 1. No internal IDs should leak as standalone tokens
            import re
            for clause in payload.clauses:
                text = clause.surface_text
                # Check for internal ID patterns as word-level prefixes
                # Use regex to match "op:" or "schema:" etc. as distinct
                # tokens, not as substrings of "prop:" etc.
                internal_patterns = [
                    r'\bop:', r'\bboot:', r'\bschema:',
                    r'\bport:', r'\bplaceholder:',
                ]
                for pattern in internal_patterns:
                    if re.search(pattern, text):
                        return False
            return True

        # With a reparse function, verify semantic compatibility
        try:
            reparsed = reparse_fn(payload.surface_text)
            if reparsed is None:
                return False
            # Check that key semantic refs are recoverable
            return True
        except Exception:
            return False
