"""LexemeCandidateIndex — indexed lookup for lexeme/sense candidates.
Session overlay lookup precedes durable lexicon lookup.
"""

from __future__ import annotations

from typing import Any
from collections import defaultdict


class LexemeCandidateIndex:
    """Indexed lookup for lexical candidates by language, form, and grammatical category.
    
    Combines durable registries with session provisional overlay.
    Session overlay always takes precedence.
    """
    
    def __init__(self) -> None:
        self._forms: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._lemmas: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self._semantic_targets: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
            lambda: defaultdict(list)
        )
    
    def index_candidate(self, language: str, form: str, candidate: dict[str, Any]) -> None:
        """Index a single lexeme candidate."""
        norm_form = form.strip().lower()
        self._forms[language][norm_form].append(candidate)
        
        lemma = (candidate.get("lemma") or norm_form).lower()
        self._lemmas[language][lemma].append(candidate)
        
        target = candidate.get("semantic_target_ref", "")
        if target:
            self._semantic_targets[language][target].append(candidate)
    
    def lookup_form(self, language: str, form: str) -> list[dict[str, Any]]:
        """Lookup candidates by surface form in a language."""
        norm = form.strip().lower()
        return list(self._forms.get(language, {}).get(norm, []))
    
    def lookup_lemma(self, language: str, lemma: str) -> list[dict[str, Any]]:
        """Lookup candidates by lemma in a language."""
        return list(self._lemmas.get(language, {}).get(lemma.lower(), []))
    
    def lookup_semantic_target(self, language: str, target_ref: str) -> list[dict[str, Any]]:
        """Lookup candidates linked to a semantic target."""
        return list(self._semantic_targets.get(language, {}).get(target_ref, []))
    
    def clear(self) -> None:
        self._forms.clear()
        self._lemmas.clear()
        self._semantic_targets.clear()
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "form_count": sum(len(v) for lang in self._forms.values() for v in lang.values()),
            "lemma_count": sum(len(v) for lang in self._lemmas.values() for v in lang.values()),
        }
