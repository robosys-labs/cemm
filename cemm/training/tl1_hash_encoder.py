"""TL1 deterministic hash encoder.

Maps typed features into a fixed-size sparse float vector
using feature hashing (SHA-256, deterministic across processes).
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

_script_dir = Path(__file__).resolve().parent.parent
if str(_script_dir) not in sys.path:
    sys.path.insert(0, str(_script_dir))

from training.tl1_feature_extractor import Feature, extract_features


def _hash_feature(feature: Feature) -> int:
    """Deterministic hash across processes for a (namespace, key) pair.
    Uses SHA-256 not Python's hash() which is salted per-process."""
    raw = f"{feature.namespace}::{feature.key}".encode("utf-8")
    return int(hashlib.sha256(raw).hexdigest()[:8], 16)


def hash_encode(
    features: list[Feature],
    num_buckets: int = 2**16,
) -> dict[int, float]:
    """Encode features into a sparse dict[int, float] vector.

    Collisions are handled by summing values (count-min sketch style).
    Returns dict of bucket_index -> accumulated_value.
    """
    vector: dict[int, float] = {}
    for f in features:
        idx = _hash_feature(f) % num_buckets
        vector[idx] = vector.get(idx, 0.0) + f.value
    return vector


def encode_packet(
    packet: dict[str, Any],
    task_type: str,
    num_buckets: int = 2**16,
) -> dict[int, float]:
    """One-shot: extract features + hash encode in a single call."""
    features = extract_features(packet, task_type)
    return hash_encode(features, num_buckets)


def cosine_similarity(a: dict[int, float], b: dict[int, float]) -> float:
    """Cosine similarity between two sparse vectors."""
    all_keys = set(a) | set(b)
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for k in all_keys:
        va = a.get(k, 0.0)
        vb = b.get(k, 0.0)
        dot += va * vb
        norm_a += va * va
        norm_b += vb * vb
    denom = (norm_a ** 0.5) * (norm_b ** 0.5)
    if denom == 0.0:
        return 0.0
    return dot / denom
