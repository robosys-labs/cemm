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
        ("{PER} and {PER} {verb} {LOC}"),
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


def main() -> None:
    random.seed(42)
    sentences, labels = _generate_sentences(400)
    tagger = NERTagger(dim=256)
    tagger.train(sentences, labels, epochs=10)

    # Simple sanity check
    test_words = "Alice visited New York on Monday".split()
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
