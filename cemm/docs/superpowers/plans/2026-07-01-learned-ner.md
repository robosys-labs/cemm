# Implement a Learned NER Tagger for SemanticInterpreter

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this task-by-task.

**Goal:** Replace the rule-based `_extract_named_entities` fallback in `SemanticInterpreter` with a small, learned sequence tagger. The tagger will use a structured perceptron with Viterbi decoding and hash-based token features, avoiding heavy external dependencies.

**Architecture:** A new `NERTagger` class lives in `cemm/learning/ner_tagger.py`. It extracts word-shape and context features, hashes them into a sparse feature vector, and maintains a linear weight matrix for BIO tags. It is trained on a synthetic corpus of English sentences containing person, place, organization, and temporal entities. The trained tagger is integrated into `SemanticInterpreter` as the primary NER fallback.

**Tech Stack:** Python 3.13, TL1 hash encoder, structured perceptron, Viterbi decoding.

---

## File Structure

| File | Responsibility | Action |
|---|---|---|
| `cemm/learning/ner_tagger.py` | Learned NER tagger implementation | Create |
| `cemm/scripts/train_ner_tagger.py` | Train and save tagger weights | Create |
| `cemm/kernel/semantic_interpreter.py` | Use learned tagger for NER fallback | Modify |
| `cemm/tests/test_learned_ner.py` | Verify learned NER behavior | Create |
| `cemm/docs/superpowers/specs/2026-06-30-cemm-gap-analysis.md` | Update gap status | Modify |

---

## Task 1: Implement learned NER tagger

**Files:**
- Create: `cemm/learning/ner_tagger.py`
- Create: `cemm/scripts/train_ner_tagger.py`
- Create: `cemm/tests/test_learned_ner.py`
- Modify: `cemm/kernel/semantic_interpreter.py`

- [ ] **Step 1: Implement NERTagger**

Create `cemm/learning/ner_tagger.py` with:

```python
class NERTagger:
    TAGS = ["O", "B-PER", "I-PER", "B-LOC", "I-LOC", "B-ORG", "I-ORG", "B-TIME", "I-TIME"]

    def __init__(self, dim: int = 256):
        self.dim = dim
        self.weights: dict[str, dict[int, float]] = {}
        self.transition_weights: dict[tuple[str, str], float] = {}

    def _featurize(self, words: list[str], position: int) -> list[str]:
        w = words[position].lower()
        features = [
            f"w={w}",
            f"shape={self._shape(w)}",
            f"isupper={w[0].isupper() if w else False}",
            f"isdigit={w.isdigit()}",
        ]
        if position > 0:
            features.append(f"w-1={words[position-1].lower()}")
        if position < len(words) - 1:
            features.append(f"w+1={words[position+1].lower()}")
        return features

    def _shape(self, word: str) -> str:
        return "".join("X" if c.isupper() else "x" if c.islower() else "d" if c.isdigit() else "c" for c in word)

    def _hash_features(self, features: list[str]) -> dict[int, float]:
        from ..training.tl1_hash_encoder import hash_encode
        from ..training.tl1_feature_extractor import Feature
        typed = [Feature(namespace="ner", key=f, value=1.0) for f in features]
        return hash_encode(typed, num_buckets=self.dim)

    def _score(self, features: list[str], tag: str) -> float:
        vec = self._hash_features(features)
        w = self.weights.get(tag, {})
        return sum(w.get(i, 0.0) * v for i, v in vec.items())

    def predict(self, words: list[str]) -> list[str]:
        """Viterbi decoding."""
        if not words:
            return []
        n = len(words)
        trellis: list[dict[str, tuple[float, str]]] = []
        for i in range(n):
            feats = self._featurize(words, i)
            tag_scores = {tag: self._score(feats, tag) for tag in self.TAGS}
            if i == 0:
                trellis.append({tag: (score, "O") for tag, score in tag_scores.items()})
            else:
                step: dict[str, tuple[float, str]] = {}
                for tag in self.TAGS:
                    best_prev = max(
                        self.TAGS,
                        key=lambda prev: trellis[i-1][prev][0] + self.transition_weights.get((prev, tag), 0.0),
                    )
                    best_score = trellis[i-1][best_prev][0] + self.transition_weights.get((best_prev, tag), 0.0) + tag_scores[tag]
                    step[tag] = (best_score, best_prev)
                trellis.append(step)
        # Backtrack
        best_last = max(self.TAGS, key=lambda t: trellis[-1][t][0])
        tags = [best_last]
        for i in range(n - 1, 0, -1):
            tags.append(trellis[i][tags[-1]][1])
        tags.reverse()
        return tags

    def train(self, sentences: list[list[str]], labels: list[list[str]], epochs: int = 5):
        for _ in range(epochs):
            for words, gold in zip(sentences, labels):
                pred = self.predict(words)
                if pred == gold:
                    continue
                # Update weights for each token where prediction differs
                for i, (p, g) in enumerate(zip(pred, gold)):
                    if p != g:
                        feats = self._featurize(words, i)
                        vec = self._hash_features(feats)
                        for idx, val in vec.items():
                            self.weights.setdefault(g, {})[idx] = self.weights[g].get(idx, 0.0) + val
                            self.weights.setdefault(p, {})[idx] = self.weights[p].get(idx, 0.0) - val
                # Update transition weights
                for i in range(1, len(gold)):
                    self.transition_weights[(gold[i-1], gold[i])] = self.transition_weights.get((gold[i-1], gold[i]), 0.0) + 1.0
                    self.transition_weights[(pred[i-1], pred[i])] = self.transition_weights.get((pred[i-1], pred[i]), 0.0) - 1.0
```

- [ ] **Step 2: Create training script**

Create `cemm/scripts/train_ner_tagger.py` that generates a synthetic corpus and trains the tagger, saving weights as JSON.

- [ ] **Step 3: Integrate into SemanticInterpreter**

Modify `SemanticInterpreter` to instantiate `NERTagger` and use it in `_extract_named_entities` when available. Add a fallback to the rule-based method if the tagger is not trained.

- [ ] **Step 4: Add test**

Create `cemm/tests/test_learned_ner.py` that trains the tagger on a few synthetic examples and verifies it tags known entities correctly.

- [ ] **Step 5: Run tests**

Run: `python -m pytest cemm/tests/test_learned_ner.py cemm/tests/test_seg_entity_population.py -v`
Expected: PASS

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest cemm/tests/ --tb=short`
Expected: All tests pass

- [ ] **Step 7: Run manual integration test**

Run: `python manual_integration_test.py`
Expected: 25 cases, 0 gaps

- [ ] **Step 8: Commit**

```bash
git add cemm/learning/ner_tagger.py cemm/scripts/train_ner_tagger.py cemm/tests/test_learned_ner.py cemm/kernel/semantic_interpreter.py
git commit -m "feat: add learned NER tagger with structured perceptron"
```

---

## Self-Review

### Spec Coverage

| Gap | Coverage |
|---|---|
| SemanticEventGraph not full NER | Learned sequence tagger replaces rule-based extraction. |

### Placeholder Scan

No placeholders.
