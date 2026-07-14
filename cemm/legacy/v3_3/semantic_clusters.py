from __future__ import annotations

import json
from pathlib import Path

from ...registry.registry import Registry
from ...registry.semantic_matcher import SemanticMatcher, MatchResult
from .text_match import phrase_in_text


_UOL_SEMANTICS_PATH = Path(__file__).parents[1] / "data" / "uol_semantics.json"


def _load_frame_aliases() -> dict[str, list[str]]:
    """Load UOL semantic frame aliases from the JSON data file."""
    if not _UOL_SEMANTICS_PATH.exists():
        return {}
    data = json.loads(_UOL_SEMANTICS_PATH.read_text(encoding="utf-8"))
    return {
        entry["canonical_key"]: entry.get("aliases", [])
        for entry in data.get("uol_semantics", [])
    }


_FRAME_ALIASES = _load_frame_aliases()


def _aliases(key: str, *extra: str) -> list[str]:
    """Get aliases for a UOL frame key, plus any extra language-specific patterns."""
    result = list(_FRAME_ALIASES.get(key, []))
    for e in extra:
        if e not in result:
            result.append(e)
    return result


# Cluster definitions map to UOL frame keys for pattern sourcing.
# Only cluster-level metadata (speech_act, target, affect_baseline) is defined here.
# Patterns are derived from UOL frame aliases — the single source of truth.
_BUILTIN_CLUSTERS: dict[str, dict] = {
    "assistant_insult_low_competence": {
        "speech_act": "insult",
        "frame_key": "low_competence",
        "patterns": _aliases("low_competence", "daft", "foolish"),
        "target": "assistant",
        "affect_baseline": {"valence": -0.4, "arousal": 0.5, "frustration": 0.3, "hostility": 0.2, "playfulness": 0.0},
    },
    "assistant_insult_useless": {
        "speech_act": "insult",
        "frame_key": "useless_assistant",
        "patterns": _aliases("useless_assistant"),
        "target": "assistant",
        "affect_baseline": {"valence": -0.5, "arousal": 0.4, "frustration": 0.4, "hostility": 0.3, "playfulness": 0.0},
    },
    "user_complaint_general": {
        "speech_act": "complaint",
        "frame_key": "user_complaint",
        "patterns": _aliases("user_complaint"),
        "target": "assistant",
        "affect_baseline": {"valence": -0.3, "arousal": 0.4, "frustration": 0.2, "hostility": 0.1, "playfulness": 0.0},
    },
    "user_correction_factual": {
        "speech_act": "correction",
        "patterns": _aliases("assert_evaluation", "lie", "mistaken"),
        "target": "assistant",
        "affect_baseline": {"valence": -0.2, "arousal": 0.3, "frustration": 0.1, "hostility": 0.0, "playfulness": 0.0},
    },
    "user_gratitude": {
        "speech_act": "gratitude",
        "patterns": _aliases("high_quality", "thanks", "thank you", "thankyou", "appreciate"),
        "target": "system",
        "affect_baseline": {"valence": 0.5, "arousal": 0.2, "frustration": 0.0, "hostility": 0.0, "playfulness": 0.1},
    },
    "user_praise": {
        "speech_act": "claim",
        "patterns": _aliases("high_quality", "love it", "love this"),
        "target": "assistant",
        "affect_baseline": {"valence": 0.6, "arousal": 0.3, "frustration": 0.0, "hostility": 0.0, "playfulness": 0.2},
    },
    "conversational_greeting": {
        "speech_act": "greeting",
        "frame_key": "greeting",
        "patterns": _aliases("greeting", "hi there", "oh hi", "lol hello"),
        "target": "assistant",
        "affect_baseline": {"valence": 0.3, "arousal": 0.2, "frustration": 0.0, "hostility": 0.0, "playfulness": 0.1},
    },
    "conversational_acknowledgment": {
        "speech_act": "acknowledgment",
        "frame_key": "acknowledgment",
        "patterns": _aliases("acknowledgment", "noted", "sounds good"),
        "target": "assistant",
        "affect_baseline": {"valence": 0.1, "arousal": 0.1, "frustration": 0.0, "hostility": 0.0, "playfulness": 0.0},
    },
    "conversational_clarification": {
        "speech_act": "clarification",
        "frame_key": "request_clarification",
        "patterns": _aliases("request_clarification"),
        "target": "assistant",
        "affect_baseline": {"valence": -0.1, "arousal": 0.2, "frustration": 0.1, "hostility": 0.0, "playfulness": 0.0},
    },
    "conversational_exit": {
        "speech_act": "exit",
        "frame_key": "session_exit",
        "patterns": _aliases("session_exit", "see you", "later"),
        "target": "assistant",
        "affect_baseline": {"valence": 0.0, "arousal": 0.1, "frustration": 0.0, "hostility": 0.0, "playfulness": 0.0},
    },
    "conversational_command_remember": {
        "speech_act": "command",
        "frame_key": "command_remember",
        "patterns": _aliases("command_remember", "rember", "remembr"),
        "target": "assistant",
        "affect_baseline": {"valence": 0.0, "arousal": 0.2, "frustration": 0.0, "hostility": 0.0, "playfulness": 0.0},
    },
    "playful_acknowledgment": {
        "speech_act": "playful_acknowledgment",
        "frame_key": "playful_acknowledgment",
        "patterns": _aliases("playful_acknowledgment", "lmao"),
        "target": "assistant",
        "affect_baseline": {"valence": 0.25, "arousal": 0.25, "frustration": 0.0, "hostility": 0.0, "playfulness": 0.5},
    },
    "confusion": {
        "speech_act": "confusion",
        "frame_key": "confusion_repair",
        "patterns": _aliases("confusion_repair", "wait what", "uh what", "that lost me"),
        "target": "assistant",
        "affect_baseline": {"valence": -0.1, "arousal": 0.25, "frustration": 0.15, "hostility": 0.0, "playfulness": 0.0},
    },
    "self_correction": {
        "speech_act": "self_correction",
        "frame_key": "self_correction",
        "patterns": _aliases("self_correction"),
        "target": "user",
        "affect_baseline": {"valence": 0.0, "arousal": 0.1, "frustration": 0.0, "hostility": 0.0, "playfulness": 0.0},
    },
    "simplification_request": {
        "speech_act": "simplification_request",
        "frame_key": "simplification_request",
        "patterns": _aliases("simplification_request", "explain that simpler", "say that simpler"),
        "target": "assistant",
        "affect_baseline": {"valence": -0.05, "arousal": 0.15, "frustration": 0.1, "hostility": 0.0, "playfulness": 0.0},
    },
    "reassurance": {
        "speech_act": "reassurance",
        "frame_key": "reassurance",
        "patterns": _aliases("reassurance"),
        "target": "assistant",
        "affect_baseline": {"valence": 0.25, "arousal": 0.1, "frustration": 0.0, "hostility": 0.0, "playfulness": 0.1},
    },
}


class ClusterMatch:
    __slots__ = ("speech_act", "cluster_key", "confidence", "pattern_matched", "match_type")

    def __init__(
        self,
        speech_act: str,
        cluster_key: str,
        confidence: float,
        pattern_matched: str = "",
        match_type: str = "exact",
    ) -> None:
        self.speech_act = speech_act
        self.cluster_key = cluster_key
        self.confidence = confidence
        self.pattern_matched = pattern_matched
        self.match_type = match_type

    def __repr__(self) -> str:
        return f"ClusterMatch({self.cluster_key}, conf={self.confidence:.2f}, type={self.match_type})"


class SemanticClusterRegistry:
    def __init__(
        self,
        clusters: dict | None = None,
        registry: Registry | None = None,
    ) -> None:
        self._clusters = clusters if clusters is not None else _BUILTIN_CLUSTERS
        self._match_counts: dict[str, int] = {}
        self._registry = registry
        self._matcher = SemanticMatcher(registry) if registry else None

    def match(self, content: str, extra_forms: list[str] | None = None) -> tuple[str, str, float]:
        """Backward-compatible single-match API. Returns (speech_act, cluster_key, confidence)."""
        ranked = self.match_ranked(content, extra_forms=extra_forms)
        if ranked:
            best = ranked[0]
            return best.speech_act, best.cluster_key, best.confidence
        return "unknown", "", 0.0

    def match_ranked(self, content: str, extra_forms: list[str] | None = None) -> list[ClusterMatch]:
        """Return all cluster matches ranked by confidence (highest first)."""
        if not content.strip():
            return []

        import string
        content_lower = content.lower().strip(string.punctuation + string.whitespace)
        words = set(content_lower.split())
        # Normalize punctuation inside each word so "huh?" matches "huh"
        words = {w.strip(string.punctuation) for w in words}
        # Also check phrase-level content with punctuation stripped for phrase patterns
        content_no_punct = content_lower.translate(str.maketrans('', '', string.punctuation))
        results: list[ClusterMatch] = []

        for cluster_key, cluster_def in self._clusters.items():
            best_conf = 0.0
            best_pattern = ""
            best_type = "none"

            for pattern in cluster_def["patterns"]:
                pattern_lower = pattern.lower()

                if " " in pattern_lower:
                    if phrase_in_text(pattern_lower, content_lower):
                        conf = 0.95
                        if conf > best_conf:
                            best_conf = conf
                            best_pattern = pattern
                            best_type = "exact_phrase"
                    elif self._matcher:
                        alias_results = self._matcher.match(content, kinds=[], extra_forms=extra_forms)
                        for r in alias_results:
                            if r.alias_matched == pattern_lower:
                                if r.probability > best_conf:
                                    best_conf = r.probability
                                    best_pattern = pattern
                                    best_type = "fuzzy_phrase"
                else:
                    # Special case: "what" in clarification should only match
                    # as a standalone question, not inside longer sentences.
                    if pattern_lower == "what" and cluster_key == "conversational_clarification":
                        if len(words) == 1 and "what" in words:
                            conf = 0.9
                            if conf > best_conf:
                                best_conf = conf
                                best_pattern = pattern
                                best_type = "exact_word"
                        continue
                    if pattern_lower in words:
                        conf = 0.9
                        if conf > best_conf:
                            best_conf = conf
                            best_pattern = pattern
                            best_type = "exact_word"
                    else:
                        for w in words:
                            if len(w) >= 5 and len(pattern_lower) >= 5:
                                from ...registry.semantic_matcher import _levenshtein
                                dist = _levenshtein(w, pattern_lower)
                                max_allowed = 1 if len(w) <= 5 else 2
                                if dist <= max_allowed and abs(len(w) - len(pattern_lower)) <= max_allowed:
                                    conf = 1.0 - (dist / max(len(w), len(pattern_lower)))
                                    if conf > best_conf:
                                        best_conf = conf
                                        best_pattern = pattern
                                        best_type = "fuzzy_word"

            if best_conf >= 0.3:
                self._match_counts[cluster_key] = self._match_counts.get(cluster_key, 0) + 1
                freq_boost = min(0.1, 0.02 * self._match_counts[cluster_key])
                final_conf = min(0.95, best_conf + freq_boost)
                results.append(ClusterMatch(
                    speech_act=cluster_def["speech_act"],
                    cluster_key=cluster_key,
                    confidence=final_conf,
                    pattern_matched=best_pattern,
                    match_type=best_type,
                ))

        results.sort(key=lambda m: m.confidence, reverse=True)
        return results

    @property
    def clusters(self) -> dict:
        return dict(self._clusters)

    def get_match_count(self, cluster_key: str) -> int:
        return self._match_counts.get(cluster_key, 0)

    @property
    def match_counts(self) -> dict[str, int]:
        return dict(self._match_counts)
