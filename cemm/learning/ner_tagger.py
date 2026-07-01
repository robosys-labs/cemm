from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from ..training.tl1_feature_extractor import Feature
from ..training.tl1_hash_encoder import hash_encode


class NERTagger:
    """Lightweight learned sequence tagger for named entity recognition.

    Uses a structured perceptron with hash-based token features and Viterbi
    decoding. Designed to run without heavy external ML dependencies.
    """

    TAGS = ["O", "B-PER", "I-PER", "B-LOC", "I-LOC", "B-ORG", "I-ORG", "B-TIME", "I-TIME"]
    TAG_TO_ROLE = {
        "PER": "person",
        "LOC": "place",
        "ORG": "organization",
        "TIME": "time",
    }

    def __init__(self, dim: int = 256) -> None:
        self.dim = dim
        self.weights: dict[str, dict[int, float]] = {tag: {} for tag in self.TAGS}
        self.transition_weights: dict[tuple[str, str], float] = {}
        self._avg_weights: dict[str, dict[int, float]] | None = None
        self._avg_transitions: dict[tuple[str, str], float] | None = None
        self._update_count = 0

    def _shape(self, word: str) -> str:
        return "".join(
            "X" if c.isupper() else "x" if c.islower() else "d" if c.isdigit() else "c"
            for c in word
        )

    def _featurize(self, words: list[str], position: int) -> list[str]:
        w = words[position]
        wl = w.lower()
        features = [
            f"w={wl}",
            f"shape={self._shape(w)}",
            f"isupper={w[0].isupper() if w else False}",
            f"isdigit={w.isdigit()}",
            f"prefix2={wl[:2]}",
            f"suffix2={wl[-2:]}",
            f"suffix3={wl[-3:]}",
        ]
        if position > 0:
            features.append(f"w-1={words[position - 1].lower()}")
        else:
            features.append("w-1=<s>")
        if position < len(words) - 1:
            features.append(f"w+1={words[position + 1].lower()}")
        else:
            features.append("w+1=</s>")
        return features

    def _hash_features(self, features: list[str]) -> dict[int, float]:
        typed = [Feature(namespace="ner", key=f, value=1.0) for f in features]
        return hash_encode(typed, num_buckets=self.dim)

    def _score(self, features: list[str], tag: str, averaged: bool = False) -> float:
        vec = self._hash_features(features)
        weights = self._avg_weights if (averaged and self._avg_weights) else self.weights
        w = weights.get(tag, {})
        return sum(w.get(i, 0.0) * v for i, v in vec.items())

    def _transition_score(self, prev: str, curr: str, averaged: bool = False) -> float:
        transitions = self._avg_transitions if (averaged and self._avg_transitions) else self.transition_weights
        return transitions.get((prev, curr), 0.0)

    def predict(self, words: list[str], averaged: bool = True) -> list[str]:
        """Predict BIO tags using Viterbi decoding."""
        if not words:
            return []
        n = len(words)
        trellis: list[dict[str, tuple[float, str | None]]] = []
        for i in range(n):
            feats = self._featurize(words, i)
            tag_scores = {tag: self._score(feats, tag, averaged=averaged) for tag in self.TAGS}
            if i == 0:
                trellis.append({tag: (score, None) for tag, score in tag_scores.items()})
            else:
                step: dict[str, tuple[float, str | None]] = {}
                for tag in self.TAGS:
                    best_prev = max(
                        self.TAGS,
                        key=lambda prev: trellis[i - 1][prev][0] + self._transition_score(prev, tag, averaged=averaged),
                    )
                    best_score = (
                        trellis[i - 1][best_prev][0]
                        + self._transition_score(best_prev, tag, averaged=averaged)
                        + tag_scores[tag]
                    )
                    step[tag] = (best_score, best_prev)
                trellis.append(step)

        best_last = max(self.TAGS, key=lambda t: trellis[-1][t][0])
        tags = [best_last]
        for i in range(n - 1, 0, -1):
            prev = trellis[i][tags[-1]][1]
            if prev is None:
                break
            tags.append(prev)
        tags.reverse()
        return tags

    def update(
        self,
        words: list[str],
        gold: list[str],
        pred: list[str],
    ) -> None:
        """Perform one structured perceptron update."""
        if len(words) != len(gold) or len(words) != len(pred):
            raise ValueError("words, gold, and pred must have the same length")
        self._update_count += 1
        for i, (g, p) in enumerate(zip(gold, pred)):
            if g == p:
                continue
            feats = self._featurize(words, i)
            vec = self._hash_features(feats)
            for idx, val in vec.items():
                self.weights[g][idx] = self.weights[g].get(idx, 0.0) + val
                self.weights[p][idx] = self.weights[p].get(idx, 0.0) - val
        for i in range(1, len(gold)):
            self.transition_weights[(gold[i - 1], gold[i])] = (
                self.transition_weights.get((gold[i - 1], gold[i]), 0.0) + 1.0
            )
            self.transition_weights[(pred[i - 1], pred[i])] = (
                self.transition_weights.get((pred[i - 1], pred[i]), 0.0) - 1.0
            )

    def train(
        self,
        sentences: list[list[str]],
        labels: list[list[str]],
        epochs: int = 5,
    ) -> None:
        """Train the tagger with structured perceptron updates."""
        for epoch in range(epochs):
            for words, gold in zip(sentences, labels):
                pred = self.predict(words, averaged=False)
                if pred != gold:
                    self.update(words, gold, pred)
        self._finalize_averaging()

    def _finalize_averaging(self) -> None:
        """Average weights over all updates for better generalization."""
        if self._update_count == 0:
            self._avg_weights = {tag: dict(w) for tag, w in self.weights.items()}
            self._avg_transitions = dict(self.transition_weights)
            return
        self._avg_weights = {tag: {} for tag in self.TAGS}
        for tag, w in self.weights.items():
            for idx, val in w.items():
                self._avg_weights[tag][idx] = val / self._update_count
        self._avg_transitions = {}
        for key, val in self.transition_weights.items():
            self._avg_transitions[key] = val / self._update_count

    def extract_entities(self, words: list[str]) -> list[dict[str, Any]]:
        """Extract entity spans from a tokenized sentence."""
        tags = self.predict(words)
        entities: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        for i, (word, tag) in enumerate(zip(words, tags)):
            if tag.startswith("B-"):
                if current:
                    entities.append(current)
                label = tag[2:]
                current = {
                    "text": word,
                    "label": label,
                    "start": i,
                    "end": i + 1,
                    "role": self.TAG_TO_ROLE.get(label, "entity"),
                }
            elif tag.startswith("I-") and current and current["label"] == tag[2:]:
                current["text"] += " " + word
                current["end"] = i + 1
            else:
                if current:
                    entities.append(current)
                    current = None
        if current:
            entities.append(current)
        return entities

    def save(self, path: str | Path) -> None:
        data = {
            "dim": self.dim,
            "weights": {tag: {str(k): v for k, v in w.items()} for tag, w in self.weights.items()},
            "transition_weights": {f"{p}|||{c}": v for (p, c), v in self.transition_weights.items()},
            "avg_weights": (
                {tag: {str(k): v for k, v in w.items()} for tag, w in self._avg_weights.items()}
                if self._avg_weights else None
            ),
            "avg_transitions": (
                {f"{p}|||{c}": v for (p, c), v in self._avg_transitions.items()}
                if self._avg_transitions else None
            ),
        }
        Path(path).write_text(json.dumps(data, sort_keys=True), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "NERTagger":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        tagger = cls(dim=data.get("dim", 256))
        tagger.weights = {
            tag: {int(k): v for k, v in w.items()}
            for tag, w in data["weights"].items()
        }
        tagger.transition_weights = {
            tuple(key.split("|||")): v
            for key, v in data["transition_weights"].items()
        }
        if data.get("avg_weights"):
            tagger._avg_weights = {
                tag: {int(k): v for k, v in w.items()}
                for tag, w in data["avg_weights"].items()
            }
        if data.get("avg_transitions"):
            tagger._avg_transitions = {
                tuple(key.split("|||")): v
                for key, v in data["avg_transitions"].items()
            }
        return tagger
