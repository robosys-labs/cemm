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
        extra_forms: list[str] | None = None,
    ) -> list[MatchResult]:
        """Match content against all registry entries of given kinds.

        Returns all matches ranked by probability (highest first).
        Supports both word-level and sentence-level fuzzy matching.
        If extra_forms is provided, the highest score per alias is kept across all forms.
        """
        content_lower = content.lower().strip()
        raw_words = content_lower.split()
        # Strip punctuation from each word for matching, keep originals for position
        words = [_strip_punct(w) for w in raw_words]
        if not any(words) and not extra_forms:
            return []

        if kinds is None:
            kinds = ["uol_semantic", "predicate"]

        entries: list[RegistryEntry] = []
        for kind in kinds:
            entries.extend(self._registry.all_by_kind(kind))

        results: list[MatchResult] = []
        best: dict[tuple[str, str, str], MatchResult] = {}
        forms = [content_lower] + (extra_forms or [])
        for form in forms:
            if not form:
                continue
            form_words = [_strip_punct(w) for w in form.lower().split()]
            for entry in entries:
                all_aliases = [entry.canonical_key] + entry.aliases
                for alias in all_aliases:
                    alias_lower = alias.lower()
                    if " " in alias_lower:
                        phrase_results = self._match_phrase(
                            alias_lower, form.lower(), form_words, entry,
                        )
                        for r in phrase_results:
                            key = (r.canonical_key, r.alias_matched, r.match_type)
                            if key not in best or best[key].probability < r.probability:
                                best[key] = r
                    else:
                        word_results = self._match_word_all_positions(
                            alias_lower, form_words, entry, position_bias,
                        )
                        for r in word_results:
                            key = (r.canonical_key, r.alias_matched, r.match_type)
                            if key not in best or best[key].probability < r.probability:
                                best[key] = r
        results = list(best.values())
        results.sort(key=lambda r: r.probability, reverse=True)
        return results

    def match_top(
        self,
        content: str,
        kinds: list[str] | None = None,
        min_probability: float = 0.3,
        extra_forms: list[str] | None = None,
    ) -> MatchResult | None:
        """Return the highest-probability match above threshold, or None."""
        results = self.match(content, kinds, extra_forms=extra_forms)
        for r in results:
            if r.probability >= min_probability:
                return r
        return None

    def match_grouped(
        self,
        content: str,
        kinds: list[str] | None = None,
        extra_forms: list[str] | None = None,
    ) -> dict[str, list[MatchResult]]:
        """Match and group results by canonical_key, each group sorted by probability."""
        results = self.match(content, kinds, extra_forms=extra_forms)
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
            elif len(word) >= 5 and len(alias) >= 5:
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
        """Token-window phrase matching — no raw substring matching.

        All phrase matching must go through token-sequence comparison to
        prevent false matches from substrings embedded in longer words.
        (P0-1 from cemm_foundational_fixes.md)
        """
        results: list[MatchResult] = []

        alias_words = alias.split()
        if len(alias_words) < 2:
            return results

        if len(words) < len(alias_words):
            return results

        best_prob = 0.0
        best_position = -1
        for start in range(0, len(words) - len(alias_words) + 1):
            window = words[start:start + len(alias_words)]
            matched_count = 0
            total_dist = 0
            all_exact = True
            for aw, w in zip(alias_words, window):
                if w == aw:
                    matched_count += 1
                    continue
                all_exact = False
                if len(w) < 4 or len(aw) < 4:
                    continue
                max_allowed = 1 if max(len(w), len(aw)) <= 5 else self._max_dist
                if abs(len(w) - len(aw)) > max_allowed:
                    continue
                dist = _levenshtein(w, aw)
                if dist <= max_allowed:
                    matched_count += 1
                    total_dist += dist

            if all_exact and matched_count == len(alias_words):
                prob = 0.95
                best_position = start
            else:
                coverage = matched_count / len(alias_words)
                if coverage < 0.8:
                    continue
                avg_dist = total_dist / matched_count if matched_count else self._max_dist
                prob = coverage * (1.0 - avg_dist / max(max(len(w) for w in alias_words), 4))
            best_prob = max(best_prob, prob)
            if prob >= 0.95:
                best_position = start
                break

        if best_prob >= 0.3:
            match_type = "exact_phrase" if best_prob >= 0.95 else "fuzzy_phrase"
            results.append(MatchResult(
                canonical_key=entry.canonical_key,
                alias_matched=alias,
                probability=max(0.3, min(0.95, best_prob)),
                match_type=match_type,
                word_position=best_position,
                entry=entry,
            ))

        return results

    def best_probability(self, content: str, canonical_key: str, kinds: list[str] | None = None) -> float:
        """Return the highest match probability for a specific canonical_key."""
        grouped = self.match_grouped(content, kinds)
        matches = grouped.get(canonical_key, [])
        return matches[0].probability if matches else 0.0
