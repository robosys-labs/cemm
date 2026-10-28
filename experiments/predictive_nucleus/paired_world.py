"""Development-only common initial worlds; no sensor or challenge custody.

The public seed and index may be inferred from the generated IDs, allowing an
observer to recover the hidden orientation. The content hash also has a tiny
state space and is not a hiding commitment. This fixture is not a blind test.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json

from .stress_world import FAMILIES, StressWorld


def _condition_digest(ids: tuple[str, ...], bits: tuple[int, ...], orientation: int) -> str:
    """Content identity for a public fixture, not a hiding commitment."""
    content = ["cemm-paired-condition-v1", ids, bits, orientation]
    return sha256(json.dumps(content, separators=(",", ":"), ensure_ascii=True).encode("ascii")).hexdigest()


@dataclass(frozen=True)
class PairedBaseWorld:
    """A common evaluator-owned initial condition, before physics selection.

    Its content identity is not a commitment that hides the binary state.
    """
    lineage_id: str
    ids: tuple[str, ...]
    bits: tuple[int, ...]
    hidden_orientation: int

    def __post_init__(self):
        if (type(self.lineage_id) is not str or len(self.lineage_id) != 64 or
                any(c not in "0123456789abcdef" for c in self.lineage_id) or
                type(self.ids) is not tuple or type(self.bits) is not tuple or
                any(type(name) is not str or not name for name in self.ids) or
                type(self.hidden_orientation) is not int):
            raise ValueError("invalid immutable paired base")
        StressWorld(self.ids, self.bits, self.hidden_orientation, "reference")
        if self.lineage_id != _condition_digest(self.ids, self.bits, self.hidden_orientation):
            raise ValueError("paired condition identity does not match its contents")

    def instantiate(self, physics: str) -> StressWorld:
        if type(physics) is not str or physics not in FAMILIES:
            raise ValueError("unknown physics family")
        return StressWorld(self.ids, self.bits, self.hidden_orientation, physics)


def draw_paired_base(seed: int, index: int) -> PairedBaseWorld:
    """Generate a common initial condition without hashing the physics family.

    This deterministic generator does not supply blinded world or sensor
    randomness, authenticated event identity, or independent custody.
    """
    if type(seed) is not int or seed < 0 or type(index) is not int or index < 0:
        raise ValueError("invalid paired world lineage")
    digest = sha256(json.dumps(["cemm-paired-base-v1", seed, index],
                               separators=(",", ":")).encode("ascii")).digest()
    count = 3 + (sha256(digest + b"/entity-count").digest()[0] & 3)
    ids = tuple(sha256(digest + b"/entity/" + j.to_bytes(2, "big")).hexdigest()[:12]
                for j in range(count))
    if len(set(ids)) != len(ids):
        raise ValueError("opaque identity collision")
    bits = tuple(sha256(digest + b"/state/" + j.to_bytes(2, "big")).digest()[0] & 1
                 for j in range(count))
    orientation = sha256(digest + b"/orientation").digest()[0] & 1
    return PairedBaseWorld(_condition_digest(ids, bits, orientation), ids, bits, orientation)
