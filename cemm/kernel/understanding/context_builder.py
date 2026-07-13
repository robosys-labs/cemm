"""Context builder — builds context frame candidates from evidence.

Import boundary: model + language submodules only.

Context is independent from communicative force, polarity, and modality
(AGENTS.md §5). Reported and hypothetical meanings are contexts.

Context kinds: actual, reported, believed, hypothetical, desired,
counterfactual, simulated, quoted.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from ...language.interfaces import SurfaceEvidence
from ...language.stream import Token, TokenKind, TokenStream
from ..model.context_frame import ContextFrame


def extract_context_candidates(
    evidence: SurfaceEvidence,
) -> tuple[ContextFrame, ...]:
    """Extract context frame candidates from surface evidence.

    Context is determined by:
    1. Quotation boundaries → quoted context
    2. Epistemic verbs (know, believe, think) → believed/reported context
    3. Conditional constructions → hypothetical context
    4. Default → actual context

    Multiple context candidates may be produced — composition preserves alternatives.
    """
    contexts: list[ContextFrame] = []
    stream = evidence.token_stream

    # Check for quotation spans → quoted context
    for i, qspan in enumerate(stream.quotation_spans):
        contexts.append(ContextFrame(
            id=f"ctx:quoted:{i}:{uuid4().hex[:8]}",
            context_kind="quoted",
            parent_ref=None,
        ))

    # Check for epistemic verbs → believed/reported context
    epistemic_verbs = {"know", "believe", "think", "say", "claim", "assert"}
    for token in stream.tokens:
        if token.kind == TokenKind.WORD and token.lemma_candidates:
            for lemma in token.lemma_candidates:
                if lemma.lower() in epistemic_verbs:
                    # The complement clause is in a believed/reported context
                    contexts.append(ContextFrame(
                        id=f"ctx:believed:{token.start_offset}:{uuid4().hex[:8]}",
                        context_kind="believed",
                        parent_ref=None,
                    ))
                    break

    # Check for conditional constructions → hypothetical context
    conditional_markers = {"if", "would", "could", "might", "should", "were"}
    for token in stream.tokens:
        if token.kind == TokenKind.WORD and token.normalized_form.lower() in conditional_markers:
            contexts.append(ContextFrame(
                id=f"ctx:hypothetical:{token.start_offset}:{uuid4().hex[:8]}",
                context_kind="hypothetical",
                parent_ref=None,
            ))
            break

    # Default: actual context
    if not contexts:
        contexts.append(ContextFrame(
            id=f"ctx:actual:{uuid4().hex[:8]}",
            context_kind="actual",
        ))

    return tuple(contexts)


def context_for_proposition(
    proposition_index: int,
    contexts: tuple[ContextFrame, ...],
    stream: TokenStream,
) -> ContextFrame:
    """Select the context for a specific proposition.

    This is a heuristic — the interpretation resolver makes the final
    selection among candidates.
    """
    if not contexts:
        return ContextFrame(
            id=f"ctx:default:{uuid4().hex[:8]}",
            context_kind="actual",
        )

    # If there's only one context, use it
    if len(contexts) == 1:
        return contexts[0]

    # If the proposition is inside a quotation, use quoted context
    for qspan in stream.quotation_spans:
        quoted = [c for c in contexts if c.context_kind == "quoted"]
        if quoted:
            return quoted[0]

    # Default to actual
    actual = [c for c in contexts if c.context_kind == "actual"]
    if actual:
        return actual[0]

    return contexts[0]
