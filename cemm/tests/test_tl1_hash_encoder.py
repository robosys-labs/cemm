from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from training.tl1_hash_encoder import _hash_feature
from training.tl1_feature_extractor import Feature


def test_hash_feature_uses_deterministic_function() -> None:
    """_hash_feature must produce the same value on any Python process.
    The current Python hash() is salted per-process (PYTHONHASHSEED),
    making it non-deterministic across runs. This test asserts the hash
    matches a specific known hash function (SHA-256 first 8 hex chars)."""
    f = Feature(namespace="entity", key="type::system", value=1.0)
    result = _hash_feature(f)

    import hashlib
    expected = int(hashlib.sha256(b"entity::type::system").hexdigest()[:8], 16)
    assert result == expected, (
        f"Hash {result} does not match deterministic SHA-256 hash {expected}. "
        "This means _hash_feature uses Python's non-deterministic hash() instead of a stable hash."
    )


def test_hash_feature_same_input_same_output() -> None:
    """Same input must produce same hash value on repeated calls."""
    f = Feature(namespace="test", key="repeatability", value=1.0)
    h1 = _hash_feature(f)
    h2 = _hash_feature(f)
    assert h1 == h2
