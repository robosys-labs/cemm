"""French construction compatibility boundary.

All definitions are loaded from the versioned French semantic language pack.
"""
from __future__ import annotations

from ..matcher import DeclarativeConstructionMatcher


def detect_constructions(
    token_evidence,
    *,
    semantic_language_pack,
    passed_competence_case_refs,
):
    if semantic_language_pack.language_tag != "fr":
        raise ValueError("French adapter received a non-French pack")
    return DeclarativeConstructionMatcher().match(
        tuple(token_evidence),
        semantic_language_pack.input_constructions,
        passed_competence_case_refs=frozenset(
            passed_competence_case_refs
        ),
    )
