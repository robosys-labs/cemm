from __future__ import annotations

from ..registry.registry import Registry
from ..registry.semantic_matcher import SemanticMatcher, MatchResult


_BUILTIN_CLUSTERS: dict[str, dict] = {
    "assistant_insult_low_competence": {
        "speech_act": "insult",
        "patterns": ["dumb", "daft", "stupid", "fool", "idiot", "foolish"],
        "target": "assistant",
        "affect_baseline": {"valence": -0.4, "arousal": 0.5, "frustration": 0.3, "hostility": 0.2, "playfulness": 0.0},
    },
    "assistant_insult_useless": {
        "speech_act": "insult",
        "patterns": ["useless", "worthless", "broken"],
        "target": "assistant",
        "affect_baseline": {"valence": -0.5, "arousal": 0.4, "frustration": 0.4, "hostility": 0.3, "playfulness": 0.0},
    },
    "user_complaint_general": {
        "speech_act": "complaint",
        "patterns": ["hate", "cant stand", "can't stand", "terrible", "awful"],
        "target": "assistant",
        "affect_baseline": {"valence": -0.3, "arousal": 0.4, "frustration": 0.2, "hostility": 0.1, "playfulness": 0.0},
    },
    "user_correction_factual": {
        "speech_act": "correction",
        "patterns": ["wrong", "incorrect", "lie", "mistaken"],
        "target": "assistant",
        "affect_baseline": {"valence": -0.2, "arousal": 0.3, "frustration": 0.1, "hostility": 0.0, "playfulness": 0.0},
    },
    "user_gratitude": {
        "speech_act": "gratitude",
        "patterns": ["thanks", "thank you", "thankyou", "helpful", "appreciate"],
        "target": "system",
        "affect_baseline": {"valence": 0.5, "arousal": 0.2, "frustration": 0.0, "hostility": 0.0, "playfulness": 0.1},
    },
    "user_praise": {
        "speech_act": "claim",
        "patterns": ["great", "awesome", "love it", "love this", "excellent", "amazing"],
        "target": "assistant",
        "affect_baseline": {"valence": 0.6, "arousal": 0.3, "frustration": 0.0, "hostility": 0.0, "playfulness": 0.2},
    },
    "conversational_greeting": {
        "speech_act": "greeting",
        "patterns": ["hello", "hi", "hey", "howdy", "greetings", "sup", "morning", "afternoon", "evening", "hi there", "oh hi", "lol hello"],
        "target": "assistant",
        "affect_baseline": {"valence": 0.3, "arousal": 0.2, "frustration": 0.0, "hostility": 0.0, "playfulness": 0.1},
    },
    "conversational_acknowledgment": {
        "speech_act": "acknowledgment",
        "patterns": ["ok", "sure", "yeah", "cool", "got it", "i see", "right", "understood", "noted", "sounds good", "great", "nice"],
        "target": "assistant",
        "affect_baseline": {"valence": 0.1, "arousal": 0.1, "frustration": 0.0, "hostility": 0.0, "playfulness": 0.0},
    },
    "conversational_clarification": {
        "speech_act": "clarification",
        "patterns": ["what", "huh", "how do you mean", "what do you mean", "what in the world", "what the", "confused", "don't understand", "don't get it", "lost", "not following", "come again", "what?"],
        "target": "assistant",
        "affect_baseline": {"valence": -0.1, "arousal": 0.2, "frustration": 0.1, "hostility": 0.0, "playfulness": 0.0},
    },
    "conversational_exit": {
        "speech_act": "exit",
        "patterns": ["exit", "quit", "bye", "goodbye", "stop", "done", "see you", "later"],
        "target": "assistant",
        "affect_baseline": {"valence": 0.0, "arousal": 0.1, "frustration": 0.0, "hostility": 0.0, "playfulness": 0.0},
    },
    "conversational_command_remember": {
        "speech_act": "command",
        "patterns": ["remember", "save", "store", "note", "rember", "remembr"],
        "target": "assistant",
        "affect_baseline": {"valence": 0.0, "arousal": 0.2, "frustration": 0.0, "hostility": 0.0, "playfulness": 0.0},
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
                    if pattern_lower in content_no_punct or pattern_lower in content_lower:
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
                    if pattern_lower in words:
                        conf = 0.9
                        if conf > best_conf:
                            best_conf = conf
                            best_pattern = pattern
                            best_type = "exact_word"
                    else:
                        for w in words:
                            if len(w) >= 4 and len(pattern_lower) >= 4:
                                from ..registry.semantic_matcher import _levenshtein
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
