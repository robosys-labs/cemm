"""Train a lightweight NER tagger on a synthetic corpus and save its weights."""
from __future__ import annotations
import os
import random
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.learning.ner_tagger import NERTagger


PERSONS = ["Alice", "Bob", "Carol", "David", "Eve", "Frank", "Grace", "Henry"]
PERSONS_MULTI = ["Dr. Smith", "Jane Doe", "John Williams", "Mary Johnson", "Professor Brown"]
PLACES = ["Paris", "London", "Berlin", "Tokyo", "Madrid", "Rome", "Cairo", "Sydney"]
PLACES_MULTI = ["New York", "San Francisco", "Los Angeles", "United States", "European Union"]
ORGS = ["Google", "Microsoft", "Apple", "Amazon", "Meta", "OpenAI", "IBM", "Intel"]
ORGS_MULTI = ["Microsoft Corporation", "Google LLC", "Apple Inc.", "OpenAI LP", "IBM Research"]
TIMES = ["today", "tomorrow", "yesterday", "Monday", "Tuesday", "morning", "evening"]

VERBS = ["visited", "saw", "met", "joined", "left", "arrived", "called", "founded"]
PREPS = ["in", "at", "on", "with", "from", "to"]
ARTICLES = ["the", "a"]

ALL_PERSONS = PERSONS + PERSONS_MULTI
ALL_PLACES = PLACES + PLACES_MULTI
ALL_ORGS = ORGS + ORGS_MULTI


def _tag_sentence(words: list[str], annotations: list[tuple[int, int, str]]) -> list[str]:
    tags = ["O"] * len(words)
    for start, end, label in annotations:
        for i in range(start, end):
            tags[i] = "B-" + label if i == start else "I-" + label
    return tags


def _generate_sentences(count: int = 400) -> tuple[list[list[str]], list[list[str]]]:
    sentences: list[list[str]] = []
    labels: list[list[str]] = []
    templates = [
        ("{PER} {verb} {LOC}"),
        ("{PER} {verb} {PREP} {LOC}"),
        ("{PER} {verb} {ORG}"),
        ("{PER} {verb} {PREP} {ORG} {TIME}"),
        ("{PER} and {PER2} {verb} {LOC}"),
        ("{PER} {verb} {PREP} {LOC} {TIME}"),
        ("{ORG} hired {PER}"),
        ("{PER} works at {ORG}"),
        ("{PER} founded {ORG} in {LOC}"),
        ("{PER} will arrive {TIME}"),
        ("{PER} left {LOC} {TIME}"),
        ("{PER} {verb} {ART} {LOC}"),
        ("{PER} {verb} {PREP} {ART} {LOC}"),
    ]
    for _ in range(count):
        template = random.choice(templates)
        per = random.choice(ALL_PERSONS)
        per2 = random.choice(ALL_PERSONS)
        loc = random.choice(ALL_PLACES)
        org = random.choice(ALL_ORGS)
        time_word = random.choice(TIMES)
        verb = random.choice(VERBS)
        prep = random.choice(PREPS)
        art = random.choice(ARTICLES)
        text = template.format(
            PER=per, PER2=per2, LOC=loc, ORG=org, TIME=time_word,
            verb=verb, PREP=prep, ART=art,
        )
        words = text.split()
        annotations: list[tuple[int, int, str]] = []
        # Multi-token entity lookup using phrase matching.
        known = [
            (ALL_PERSONS, "PER"),
            (ALL_PLACES, "LOC"),
            (ALL_ORGS, "ORG"),
            (TIMES, "TIME"),
        ]
        i = 0
        while i < len(words):
            matched = False
            for entity_list, label in known:
                for entity in sorted(entity_list, key=lambda e: -len(e.split())):
                    entity_tokens = entity.split()
                    if words[i:i + len(entity_tokens)] == entity_tokens:
                        annotations.append((i, i + len(entity_tokens), label))
                        i += len(entity_tokens)
                        matched = True
                        break
                if matched:
                    break
            if not matched:
                i += 1
        sentences.append(words)
        labels.append(_tag_sentence(words, annotations))
    return sentences, labels


def _load_conll2025_ner(limit: int | None = None) -> tuple[list[list[str]], list[list[str]], list[str], dict[str, str]]:
    """Load boltuix/conll2025-ner and return full tags plus CEMM role mapping."""
    from datasets import load_dataset

    ds = load_dataset("boltuix/conll2025-ner")
    split = ds["train"]
    if limit:
        split = split.select(range(min(limit, len(split))))

    sentences: list[list[str]] = []
    labels: list[list[str]] = []
    for example in split:
        sentences.append(example["tokens"])
        labels.append(list(example["ner_tags"]))

    all_tags = sorted({t for seq in labels for t in seq})
    bio_tags = ["O"] + [f"B-{t[2:]}" for t in all_tags if t.startswith("B-")] + [f"I-{t[2:]}" for t in all_tags if t.startswith("I-")]
    # Ensure every tag seen in the data is represented.
    seen = set(bio_tags)
    for seq in labels:
        for t in seq:
            if t not in seen:
                bio_tags.append(t)
                seen.add(t)

    tag_to_role = {
        "PERSON": "person",
        "NORP": "person",
        "GPE": "place",
        "LOC": "place",
        "FAC": "place",
        "ORG": "organization",
        "DATE": "time",
        "TIME": "time",
    }
    return sentences, labels, bio_tags, tag_to_role


def main() -> None:
    random.seed(42)
    tagger = NERTagger(dim=1024)

    # Combine real-world data with synthetic examples so the tagger handles both.
    try:
        real_sentences, real_labels, bio_tags, tag_to_role = _load_conll2025_ner(limit=5000)
        print(f"Loaded {len(real_sentences)} real examples from conll2025-ner with {len(bio_tags)} tags")
        synthetic_sentences, synthetic_labels = _generate_sentences(400)
        # Map synthetic labels to full tag set by keeping their coarse label; they are already in B-/I- form.
        combined_sentences = real_sentences + synthetic_sentences
        combined_labels = real_labels + synthetic_labels
        for tag in ["B-PER", "I-PER", "B-LOC", "I-LOC", "B-ORG", "I-ORG", "B-TIME", "I-TIME"]:
            if tag not in bio_tags:
                bio_tags.append(tag)
        tagger = NERTagger(tags=bio_tags, tag_to_role=tag_to_role, dim=1024)
        metrics = tagger.train(combined_sentences, combined_labels, epochs=3, validation_split=0.1)
        print(f"Training complete — best val token accuracy: {metrics['best_token_acc']:.2%} at epoch {metrics['best_epoch']}")
    except Exception as exc:
        print(f"Could not load conll2025-ner ({exc}); using synthetic corpus")
        synthetic_sentences, synthetic_labels = _generate_sentences(400)
        tagger = NERTagger(dim=1024)
        tagger.train(synthetic_sentences, synthetic_labels, epochs=10)

    # Simple sanity check
    test_cases = [
        "Alice visited New York on Monday".split(),
        "Microsoft opened in Tokyo on January 2025".split(),
        "Jane Doe works at Google LLC".split(),
    ]
    for test_words in test_cases:
        entities = tagger.extract_entities(test_words)
        print(f"Test: {test_words}")
        for ent in entities:
            print(f"  {ent['text']}: {ent['label']}")

    output_dir = os.path.join(os.path.dirname(__file__), "..", "data", "models")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "ner_tagger_weights.json")
    tagger.save(output_path)
    print(f"Saved tagger weights to {output_path}")


if __name__ == "__main__":
    main()
