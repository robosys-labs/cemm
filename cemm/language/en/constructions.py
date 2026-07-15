"""English construction compatibility boundary.

All construction definitions are loaded from
`cemm/data/languages/en/v343/understanding.json`. This module contains no words,
phrases, regular expressions, or semantic routing rules.
"""
from __future__ import annotations

from ..matcher import DeclarativeConstructionMatcher


def detect_constructions(
    token_evidence,
    *,
    semantic_language_pack,
    passed_competence_case_refs,
):
    if semantic_language_pack.language_tag != "en":
        raise ValueError("English adapter received a non-English pack")
    return DeclarativeConstructionMatcher().match(
        tuple(token_evidence),
        semantic_language_pack.input_constructions,
        passed_competence_case_refs=frozenset(
            passed_competence_case_refs
        ),
    )
