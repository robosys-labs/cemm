"""Build contrastive pairs from gold examples for TL2 metric learning."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import numpy as np

from training.tl1_hash_encoder import encode_packet


_GOLD_PATH = Path("generated/gold_examples.jsonl")


def load_gold(path: str | Path = _GOLD_PATH) -> list[dict]:
    examples = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


def encode_packets(examples: list[dict], num_buckets: int = 2 ** 16) -> tuple[np.ndarray, list[str], list[str]]:
    """Encode all examples to TL1 hash vectors.

    Returns:
        vectors: (N, D) numpy array where D = num_buckets
        task_types: list of task_type strings
        labels: list of example labels
    """
    vectors = []
    task_types = []
    labels = []
    for ex in examples:
        pkt = ex["payload"]["packet"]
        tt = ex["task_type"]
        vec = encode_packet(pkt, tt, num_buckets)
        dense = np.zeros(num_buckets, dtype=np.float32)
        for idx, val in vec.items():
            dense[idx] = val
        vectors.append(dense)
        task_types.append(tt)
        labels.append(ex["payload"].get("label", ""))
    return np.array(vectors), task_types, labels


def build_contrastive_pairs(
    vectors: np.ndarray,
    task_types: list[str],
    pos_ratio: float = 0.5,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Build contrastive pairs: same-type positive, cross-type negative.

    Returns:
        anchor_vectors: (N_pairs, D)
        neighbor_vectors: (N_pairs, D)
        targets: (N_pairs,) where 1 = positive pair, 0 = negative pair
    """
    rng = random.Random(seed)
    n = len(vectors)
    pairs: list[tuple[int, int, float]] = []

    for i in range(n):
        for j in range(i + 1, n):
            same = task_types[i] == task_types[j]
            # Only sample same-type as positive
            if same:
                pairs.append((i, j, 1.0))

    # Sample negative pairs equal to positive count
    neg_target = int(len(pairs) * (1.0 / pos_ratio - 1.0)) if pos_ratio < 1.0 else 0
    neg_candidates = [(i, j) for i in range(n) for j in range(i + 1, n)
                      if task_types[i] != task_types[j]]
    rng.shuffle(neg_candidates)
    selected_neg = neg_candidates[:neg_target]
    for i, j in selected_neg:
        pairs.append((i, j, 0.0))

    rng.shuffle(pairs)
    anchors = np.array([vectors[i] for i, j, _ in pairs], dtype=np.float32)
    neighbors = np.array([vectors[j] for i, j, _ in pairs], dtype=np.float32)
    targets = np.array([t for _, _, t in pairs], dtype=np.float32)
    return anchors, neighbors, targets


def train_eval_split(
    vectors: np.ndarray,
    task_types: list[str],
    eval_ratio: float = 0.3,
    seed: int = 42,
) -> tuple[np.ndarray, list[str], np.ndarray, list[str]]:
    """Split examples into train and eval sets, stratified by task_type."""
    rng = random.Random(seed)
    by_type: dict[str, list[int]] = {}
    for i, tt in enumerate(task_types):
        by_type.setdefault(tt, []).append(i)

    train_idx: list[int] = []
    eval_idx: list[int] = []
    for tt, indices in by_type.items():
        rng.shuffle(indices)
        split = max(1, int(len(indices) * eval_ratio))
        eval_idx.extend(indices[:split])
        train_idx.extend(indices[split:])

    rng.shuffle(train_idx)
    rng.shuffle(eval_idx)

    train_v = vectors[train_idx]
    eval_v = vectors[eval_idx]
    train_tt = [task_types[i] for i in train_idx]
    eval_tt = [task_types[i] for i in eval_idx]
    return train_v, train_tt, eval_v, eval_tt
