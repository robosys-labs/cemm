"""Canonical retrieval patterns built from grounded semantic roles."""
from __future__ import annotations

from .query_pattern import (
    QueryPatternBuilder,
    QueryPatternKind,
    ReferentConstraint,
    SemanticQueryPattern,
)
from .retriever import SemanticRetriever


class CanonicalQueryPatternBuilder(QueryPatternBuilder):
    def build_from_interpretations(self, interpretations=None):
        if not interpretations:
            return ()
        patterns = []
        for interpretation in interpretations:
            proposition_ref = getattr(interpretation, "proposition_ref", "")
            predicate_key = getattr(
                interpretation,
                "predicate_semantic_key",
                "",
            )
            if not proposition_ref or not predicate_key:
                continue
            constraints = tuple(
                ReferentConstraint(
                    role_schema_ref=binding.role_schema_ref,
                    filler_ref=binding.filler_ref,
                    concept_id=binding.filler_ref,
                )
                for binding in getattr(interpretation, "role_bindings", ())
                if binding.role_schema_ref and binding.filler_ref
            )
            force = getattr(interpretation, "communicative_force", "")
            context_ref = (
                getattr(interpretation, "context_kind", "") or "actual"
                if force in {"ask", "query"}
                else getattr(interpretation, "context_ref", "")
            )
            patterns.append(SemanticQueryPattern(
                pattern_id=self._next_id(),
                pattern_kind=QueryPatternKind.PROPOSITION_LOOKUP,
                proposition_ref=proposition_ref,
                semantic_keys=(predicate_key,),
                referent_constraints=constraints,
                context_ref=context_ref,
            ))
        return tuple(patterns)


class CanonicalSemanticRetriever(SemanticRetriever):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._builder = CanonicalQueryPatternBuilder()
