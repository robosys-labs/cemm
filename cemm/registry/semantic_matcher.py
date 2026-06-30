from __future__ import annotations

from dataclasses import dataclass, field
from .registry import Registry, RegistryEntry


import re as _re


def _strip_punct(word: str) -> str:
    """Strip leading/trailing punctuation from a word."""
    return _re.sub(r'^[^a-z0-9]+|[^a-z0-9]+$', '', word)


def _levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            curr.append(min(prev[j + 1] + 1, curr[j] + 1, prev[j] + cost))
        prev = curr
    return prev[-1]


@dataclass
class MatchResult:
    canonical_key: str
    alias_matched: str
    probability: float
    match_type: str  # exact_word | fuzzy_word | exact_phrase | fuzzy_phrase
    word_position: int = -1
    entry: RegistryEntry | None = None


class SemanticMatcher:
    """Word/sentence fuzzy matching with probability ranking against registry entries."""

    def __init__(self, registry: Registry, max_dist: int = 2) -> None:
        self._registry = registry
        self._max_dist = max_dist

    def match(
        self,
        content: str,
        kinds: list[str] | None = None,
        position_bias: bool = True,
    ) -> list[MatchResult]:
        """Match content against all registry entries of given kinds.

        Returns all matches ranked by probability (highest first).
        Supports both word-level and sentence-level fuzzy matching.
        """
        content_lower = content.lower().strip()
        raw_words = content_lower.split()
        # Strip punctuation from each word for matching, keep originals for position
        words = [_strip_punct(w) for w in raw_words]
        if not any(words):
            return []

        if kinds is None:
            kinds = ["uol_semantic", "predicate"]

        entries: list[RegistryEntry] = []
        for kind in kinds:
            entries.extend(self._registry.all_by_kind(kind))

        results: list[MatchResult] = []

        for entry in entries:
            all_aliases = [entry.canonical_key] + entry.aliases
            for alias in all_aliases:
                alias_lower = alias.lower()

                if " " in alias_lower:
                    phrase_results = self._match_phrase(
                        alias_lower, content_lower, words, entry,
                    )
                    results.extend(phrase_results)
                else:
                    word_results = self._match_word_all_positions(
                        alias_lower, words, entry, position_bias,
                    )
                    results.extend(word_results)

        results.sort(key=lambda r: r.probability, reverse=True)
        return results

    def match_top(
        self,
        content: str,
        kinds: list[str] | None = None,
        min_probability: float = 0.3,
    ) -> MatchResult | None:
        """Return the highest-probability match above threshold, or None."""
        results = self.match(content, kinds)
        for r in results:
            if r.probability >= min_probability:
                return r
        return None

    def match_grouped(
        self,
        content: str,
        kinds: list[str] | None = None,
    ) -> dict[str, list[MatchResult]]:
        """Match and group results by canonical_key, each group sorted by probability."""
        results = self.match(content, kinds)
        grouped: dict[str, list[MatchResult]] = {}
        for r in results:
            grouped.setdefault(r.canonical_key, []).append(r)
        for key in grouped:
            grouped[key].sort(key=lambda r: r.probability, reverse=True)
        return grouped

    def _match_word_all_positions(
        self,
        alias: str,
        words: list[str],
        entry: RegistryEntry,
        position_bias: bool,
    ) -> list[MatchResult]:
        results: list[MatchResult] = []
        for i, word in enumerate(words):
            if word == alias:
                prob = 1.0
                if position_bias and i == 0:
                    prob = 1.0
                elif position_bias:
                    prob = 0.85
                results.append(MatchResult(
                    canonical_key=entry.canonical_key,
                    alias_matched=alias,
                    probability=prob,
                    match_type="exact_word",
                    word_position=i,
                    entry=entry,
                ))
            elif len(word) >= 2 and len(alias) >= 2:
                # Proportional distance threshold based on word length
                max_len = max(len(word), len(alias))
                if max_len <= 3:
                    max_allowed = 1
                elif max_len <= 5:
                    max_allowed = 1
                else:
                    max_allowed = self._max_dist
                if abs(len(word) - len(alias)) <= max_allowed:
                    dist = _levenshtein(word, alias)
                    if dist <= max_allowed:
                        prob = 1.0 - (dist / max_len)
                        # Short words get a small penalty to avoid false positives
                        if max_len <= 3:
                            prob *= 0.9
                        if position_bias and i > 0:
                            prob *= 0.9
                        if prob >= 0.3:
                            results.append(MatchResult(
                                canonical_key=entry.canonical_key,
                                alias_matched=alias,
                                probability=prob,
                                match_type="fuzzy_word",
                                word_position=i,
                                entry=entry,
                            ))
        return results

    def _match_phrase(
        self,
        alias: str,
        content_lower: str,
        words: list[str],
        entry: RegistryEntry,
    ) -> list[MatchResult]:
        results: list[MatchResult] = []

        if alias in content_lower:
            prob = 0.95
            results.append(MatchResult(
                canonical_key=entry.canonical_key,
                alias_matched=alias,
                probability=prob,
                match_type="exact_phrase",
                word_position=-1,
                entry=entry,
            ))
            return results

        alias_words = alias.split()
        if len(alias_words) < 2:
            return results

        matched_count = 0
        total_dist = 0
        for aw in alias_words:
            best_dist = self._max_dist + 1
            for w in words:
                if w == aw:
                    best_dist = 0
                    break
                if len(w) >= 3 and abs(len(w) - len(aw)) <= self._max_dist:
                    d = _levenshtein(w, aw)
                    if d < best_dist:
                        best_dist = d
            if best_dist <= self._max_dist:
                matched_count += 1
                total_dist += best_dist

        if matched_count > 0:
            coverage = matched_count / len(alias_words)
            # Require at least 60% word coverage to avoid false positives
            # e.g. "sure" should not match "not sure" (coverage=50%)
            if coverage < 0.6:
                return results
            avg_dist = total_dist / matched_count if matched_count > 0 else self._max_dist
            prob = coverage * (1.0 - avg_dist / max(len(alias_words[0]), 3))
            prob = max(0.3, min(0.9, prob))
            results.append(MatchResult(
                canonical_key=entry.canonical_key,
                alias_matched=alias,
                probability=prob,
                match_type="fuzzy_phrase",
                word_position=-1,
                entry=entry,
            ))

        return results

    def best_probability(self, content: str, canonical_key: str, kinds: list[str] | None = None) -> float:
        """Return the highest match probability for a specific canonical_key."""
        grouped = self.match_grouped(content, kinds)
        matches = grouped.get(canonical_key, [])
        return matches[0].probability if matches else 0.0
