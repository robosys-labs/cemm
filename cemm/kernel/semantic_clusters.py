from __future__ import annotations


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
        "patterns": ["hate", "cant stand", "terrible", "awful"],
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
}


class SemanticClusterRegistry:
    def __init__(self, clusters: dict | None = None) -> None:
        self._clusters = clusters if clusters is not None else _BUILTIN_CLUSTERS
        self._match_counts: dict[str, int] = {}

    def match(self, content: str) -> tuple[str, str, float]:
        content_lower = content.lower()
        for cluster_key, cluster_def in self._clusters.items():
            for pattern in cluster_def["patterns"]:
                if pattern in content_lower:
                    self._match_counts[cluster_key] = self._match_counts.get(cluster_key, 0) + 1
                    speech_act = cluster_def["speech_act"]
                    confidence = min(0.9, 0.5 + 0.05 * self._match_counts[cluster_key])
                    return speech_act, cluster_key, confidence
        return "unknown", "", 0.0

    @property
    def clusters(self) -> dict:
        return dict(self._clusters)

    def get_match_count(self, cluster_key: str) -> int:
        return self._match_counts.get(cluster_key, 0)

    @property
    def match_counts(self) -> dict[str, int]:
        return dict(self._match_counts)
