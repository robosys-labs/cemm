from __future__ import annotations
import json
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Feature:
    namespace: str
    key: str
    value: float = 1.0


def hash_encode(features: list[Feature], num_buckets: int = 1024) -> dict[int, float]:
    result: dict[int, float] = {}
    for feat in features:
        raw = f"{feat.namespace}:{feat.key}"
        h = int(hashlib.md5(raw.encode()).hexdigest(), 16) % num_buckets
        result[h] = result.get(h, 0.0) + feat.value
    return result


class NERTagger:
    """Lightweight learned sequence tagger for named entity recognition.

    Uses a structured perceptron with hash-based token features and Viterbi
    decoding. Designed to run without heavy external ML dependencies.
    """

    DEFAULT_TAGS = ["O", "B-PER", "I-PER", "B-LOC", "I-LOC", "B-ORG", "I-ORG", "B-TIME", "I-TIME"]
    DEFAULT_TAG_TO_ROLE = {
        "PER": "person",
        "LOC": "place",
        "ORG": "organization",
        "TIME": "time",
    }

    def __init__(self, tags: list[str] | None = None, tag_to_role: dict[str, str] | None = None, dim: int = 1024) -> None:
        self.dim = dim
        self.TAGS = list(tags) if tags else list(self.DEFAULT_TAGS)
        self.TAG_TO_ROLE = dict(tag_to_role) if tag_to_role else dict(self.DEFAULT_TAG_TO_ROLE)
        self.weights: dict[str, dict[int, float]] = {tag: {} for tag in self.TAGS}
        self.transition_weights: dict[tuple[str, str], float] = {}
        # Running sum of weights for averaged perceptron.
        self._weight_sum: dict[str, dict[int, float]] = {tag: {} for tag in self.TAGS}
        self._transition_sum: dict[tuple[str, str], float] = {}
        self._avg_weights: dict[str, dict[int, float]] | None = None
        self._avg_transitions: dict[tuple[str, str], float] | None = None
        self._update_count = 0

    @staticmethod
    def _normalize_word(word: str) -> str:
        import unicodedata
        return "".join(
            c for c in unicodedata.normalize("NFKD", word.strip(".,!?;:\"'()[]{}"))
            if not unicodedata.combining(c)
        )

    @staticmethod
    def normalize_tokens(words: list[str]) -> list[str]:
        return [w for w in (NERTagger._normalize_word(word) for word in words) if w]

    def _ensure_tags(self, labels: list[list[str]]) -> None:
        for seq in labels:
            for tag in seq:
                if tag not in self.TAGS:
                    self.TAGS.append(tag)
                    self.weights[tag] = {}
                    self._weight_sum[tag] = {}

    def _shape(self, word: str) -> str:
        return "".join(
            "X" if c.isupper() else "x" if c.islower() else "d" if c.isdigit() else "c"
            for c in word
        )

    def _featurize(self, words: list[str], position: int) -> list[str]:
        norm_words = [self._normalize_word(w) for w in words]
        w = norm_words[position]
        wl = w.lower()
        features = [
            f"w={wl}",
            f"shape={self._shape(w)}",
            f"isupper={w[0].isupper() if w else False}",
            f"isdigit={w.isdigit()}",
            f"isalpha={w.isalpha()}",
            f"isalnum={w.isalnum()}",
            f"istitle={w.istitle()}",
            f"prefix2={wl[:2]}",
            f"prefix3={wl[:3]}",
            f"suffix2={wl[-2:]}",
            f"suffix3={wl[-3:]}",
            f"suffix4={wl[-4:]}",
            f"len={len(w)}",
        ]
        # Character n-grams
        for n in (2, 3):
            for i in range(max(0, len(wl) - n + 1)):
                features.append(f"c{n}={wl[i:i + n]}")
        if position > 0:
            features.append(f"w-1={norm_words[position - 1].lower()}")
            features.append(f"shape-1={self._shape(norm_words[position - 1])}")
        else:
            features.append("w-1=<s>")
            features.append("shape-1=<s>")
        if position > 1:
            features.append(f"w-2={norm_words[position - 2].lower()}")
        else:
            features.append("w-2=<s>")
        if position < len(words) - 1:
            features.append(f"w+1={norm_words[position + 1].lower()}")
            features.append(f"shape+1={self._shape(norm_words[position + 1])}")
        else:
            features.append("w+1=</s>")
            features.append("shape+1=</s>")
        if position < len(words) - 2:
            features.append(f"w+2={norm_words[position + 2].lower()}")
        else:
            features.append("w+2=</s>")
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

    @staticmethod
    def _normalize_tag(tag: str, seen_labels: set[str] | None = None) -> str:
        """Repair noisy mixed-label BIO sequences and normalise upper case tags."""
        tag = tag.strip()
        if tag == "O":
            return "O"
        parts = tag.split("-", 1)
        if len(parts) != 2:
            return "O"
        prefix, label = parts[0].upper(), parts[1].upper()
        if prefix not in {"B", "I"}:
            return "O"
        label = label.replace("_", "-")
        if seen_labels and label not in seen_labels:
            # Map to a known label if only one label differs superficially
            return "O"
        return f"{prefix}-{label}"

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
        # Accumulate running sums for averaging.
        for tag, w in self.weights.items():
            for idx, val in w.items():
                self._weight_sum[tag][idx] = self._weight_sum[tag].get(idx, 0.0) + val
        for key, val in self.transition_weights.items():
            self._transition_sum[key] = self._transition_sum.get(key, 0.0) + val

    def train(
        self,
        sentences: list[list[str]],
        labels: list[list[str]],
        epochs: int = 5,
        validation_split: float = 0.1,
        verbose: bool = True,
    ) -> dict[str, float]:
        """Train the tagger with structured perceptron updates and progress output.

        Returns a dict with the best validation token accuracy and epoch number.
        """
        if len(sentences) != len(labels):
            raise ValueError("sentences and labels must have the same length")
        if not sentences:
            return {"best_token_acc": 0.0, "best_epoch": 0}

        self._ensure_tags(labels)

        # Split into train/validation
        split_idx = int(len(sentences) * (1 - validation_split))
        train_sentences, train_labels = sentences[:split_idx], labels[:split_idx]
        val_sentences, val_labels = sentences[split_idx:], labels[split_idx:]

        best_acc = 0.0
        best_epoch = 0
        for epoch in range(epochs):
            mistakes = 0
            total = 0
            for i, (words, gold) in enumerate(zip(train_sentences, train_labels)):
                pred = self.predict(words, averaged=False)
                if pred != gold:
                    self.update(words, gold, pred)
                    mistakes += 1
                total += 1
                if verbose and (i + 1) % 500 == 0:
                    print(f"  epoch {epoch + 1}/{epochs}  examples {i + 1}/{len(train_sentences)}  mistakes={mistakes}", flush=True)
            val_acc = self._token_accuracy(val_sentences, val_labels)
            if val_acc > best_acc:
                best_acc = val_acc
                best_epoch = epoch + 1
            if verbose:
                print(
                    f"Epoch {epoch + 1}/{epochs} complete — train mistakes={mistakes}/{total} — "
                    f"val token accuracy={val_acc:.2%} (best={best_acc:.2%} @ epoch {best_epoch})",
                    flush=True,
                )
        self._finalize_averaging()
        return {"best_token_acc": best_acc, "best_epoch": best_epoch}

    def _token_accuracy(self, sentences: list[list[str]], labels: list[list[str]]) -> float:
        correct = 0
        total = 0
        for words, gold in zip(sentences, labels):
            pred = self.predict(words, averaged=False)
            for p, g in zip(pred, gold):
                total += 1
                if p == g:
                    correct += 1
        return correct / total if total else 0.0

    def _finalize_averaging(self) -> None:
        """Average weights over all updates for better generalization."""
        if self._update_count == 0:
            self._avg_weights = {tag: dict(w) for tag, w in self.weights.items()}
            self._avg_transitions = dict(self.transition_weights)
            return
        self._avg_weights = {tag: {} for tag in self.TAGS}
        for tag, w in self._weight_sum.items():
            for idx, val in w.items():
                self._avg_weights[tag][idx] = val / self._update_count
        self._avg_transitions = {}
        for key, val in self._transition_sum.items():
            self._avg_transitions[key] = val / self._update_count

    def extract_entities(self, words: list[str]) -> list[dict[str, Any]]:
        """Extract entity spans from a tokenized sentence."""
        tags = self.predict(words)
        tags = [self._normalize_tag(tag, seen_labels=self._known_labels()) for tag in tags]
        entities: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        scores: list[float] = []
        for i, (word, tag) in enumerate(zip(words, tags)):
            feats = self._featurize(words, i)
            tag_score = self._score(feats, tag, averaged=True)
            if tag.startswith("B-"):
                if current:
                    current["confidence"] = sum(scores) / len(scores) if scores else 0.0
                    entities.append(current)
                    scores = []
                label = tag[2:]
                role = self.TAG_TO_ROLE.get(label, self._role_from_label(label))
                current = {
                    "text": word,
                    "label": label,
                    "start": i,
                    "end": i + 1,
                    "role": role,
                }
                scores = [tag_score]
            elif tag.startswith("I-") and current and current["label"] == tag[2:]:
                current["text"] += " " + word
                current["end"] = i + 1
                scores.append(tag_score)
            else:
                if current:
                    current["confidence"] = sum(scores) / len(scores) if scores else 0.0
                    entities.append(current)
                    current = None
                    scores = []
        if current:
            current["confidence"] = sum(scores) / len(scores) if scores else 0.0
            entities.append(current)
        return entities

    def _known_labels(self) -> set[str]:
        return {t.split("-", 1)[1] for t in self.TAGS if t != "O"}

    @staticmethod
    def _role_from_label(label: str) -> str:
        """Fallback role mapping for labels outside the configured tag_to_role map."""
        label_upper = label.upper()
        if label_upper in {"PERSON", "PER", "NORP"}:
            return "person"
        if label_upper in {"GPE", "LOC", "FAC"}:
            return "place"
        if label_upper in {"ORG"}:
            return "organization"
        if label_upper in {"DATE", "TIME"}:
            return "time"
        return "entity"

    def save(self, path: str | Path) -> None:
        data = {
            "dim": self.dim,
            "tags": self.TAGS,
            "tag_to_role": self.TAG_TO_ROLE,
            "weights": {tag: {str(k): v for k, v in w.items()} for tag, w in self.weights.items()},
            "transition_weights": {f"{p}|||{c}": v for (p, c), v in self.transition_weights.items()},
            "weight_sum": {tag: {str(k): v for k, v in w.items()} for tag, w in self._weight_sum.items()},
            "transition_sum": {f"{p}|||{c}": v for (p, c), v in self._transition_sum.items()},
            "update_count": self._update_count,
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
        tagger = cls(
            tags=data.get("tags"),
            tag_to_role=data.get("tag_to_role"),
            dim=data.get("dim", 1024),
        )
        tagger.weights = {
            tag: {int(k): v for k, v in w.items()}
            for tag, w in data["weights"].items()
        }
        tagger.transition_weights = {
            tuple(key.split("|||")): v
            for key, v in data["transition_weights"].items()
        }
        tagger._weight_sum = {
            tag: {int(k): v for k, v in w.items()}
            for tag, w in data.get("weight_sum", {}).items()
        }
        tagger._transition_sum = {
            tuple(key.split("|||")): v
            for key, v in data.get("transition_sum", {}).items()
        }
        tagger._update_count = data.get("update_count", 0)
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
