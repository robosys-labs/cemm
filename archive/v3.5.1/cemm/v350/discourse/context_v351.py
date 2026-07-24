"""Exact CSIR context/scope re-abstraction helpers for Stage 8."""
from __future__ import annotations

from ..csir.model import CSIRGraph, QualifierKind
from ..grounded.model import SemanticContext
from ..schema.model import semantic_fingerprint


_NON_ACTUAL = {
    "reported", "believed", "hypothetical", "planned", "desired", "fictional",
    "quoted", "counterfactual",
}
_KNOWN_CONTEXT_KINDS = frozenset({"actual", *_NON_ACTUAL})


def semantic_contexts_for_graph(
    graph: CSIRGraph,
    *,
    cycle_context_ref: str,
    permission_ref: str,
    evidence_refs: tuple[str, ...],
) -> tuple[tuple[SemanticContext, ...], str, str]:
    """Return explicit semantic contexts and the proposition's primary placement.

    Context qualifier values are semantic evidence.  We do not infer context from lexical
    strings or grammatical mood.  Multiple explicit contexts remain represented instead
    of being collapsed to the transport/cycle context.
    """
    base = SemanticContext(
        context_ref=cycle_context_ref, context_kind="actual", permission_ref=permission_ref,
        evidence_refs=evidence_refs,
    )
    explicit: list[tuple[str, str]] = []
    for qualifier in graph.qualifiers:
        if qualifier.qualifier_kind is not QualifierKind.CONTEXT:
            continue
        if isinstance(qualifier.value_atom, str) and qualifier.value_atom.strip():
            observed = qualifier.value_atom.casefold()
            # Only the canonical context classes are interpreted structurally.  An
            # arbitrary context identifier/string is explicit non-actual qualification,
            # not evidence that the proposition belongs in actual-world belief.
            kind = observed if observed in _KNOWN_CONTEXT_KINDS else "qualified"
            ref = "semantic-context:" + semantic_fingerprint(
                "semantic-context-v351",
                (cycle_context_ref, observed, qualifier.qualifier_ref), 24,
            )
            explicit.append((ref, kind))
        elif qualifier.value_pin is not None:
            kind = "qualified"
            ref = "semantic-context:" + semantic_fingerprint(
                "semantic-context-pin-v351",
                (cycle_context_ref, qualifier.value_pin.key, qualifier.qualifier_ref), 24,
            )
            explicit.append((ref, kind))
        elif qualifier.value_ref is not None:
            kind = "qualified"
            ref = "semantic-context:" + semantic_fingerprint(
                "semantic-context-ref-v351",
                (cycle_context_ref, qualifier.value_ref.kind.value, qualifier.value_ref.ref), 24,
            )
            explicit.append((ref, kind))
    if not explicit:
        return (base,), cycle_context_ref, "actual"
    contexts = [base]
    for ref, kind in explicit:
        contexts.append(SemanticContext(
            context_ref=ref, context_kind=kind, permission_ref=permission_ref,
            parent_context_ref=cycle_context_ref, evidence_refs=evidence_refs,
        ))
    # Prefer an explicitly non-actual placement when present.  If multiple contexts exist,
    # preserve all and choose deterministically; ambiguity remains visible in the graph.
    non_actual = sorted((item for item in explicit if item[1] in _NON_ACTUAL), key=lambda item: item)
    chosen = non_actual[0] if non_actual else sorted(explicit)[0]
    return tuple(contexts), chosen[0], chosen[1]


__all__ = ["semantic_contexts_for_graph"]
