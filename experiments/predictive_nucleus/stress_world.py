"""Evaluator-only development worlds with independent physics and sensor channels.

Never import this module from a learner, predictive kernel or probe planner.
All families here are openly inspectable *diagnostics*, not sealed challenges.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import random


FAMILIES = ("reference", "bilateral_flip", "conditional_flip", "switch_orientation")


@dataclass(frozen=True)
class StressWorld:
    ids: tuple[str, ...]
    bits: tuple[int, ...]
    hidden_orientation: int
    physics: str
    contact_count: int = 0

    def __post_init__(self):
        if not (3 <= len(self.ids) <= 6) or len(set(self.ids)) != len(self.ids):
            raise ValueError("require 3-6 distinct opaque identities")
        if len(self.bits) != len(self.ids) or any(type(x) is not int or x not in (0, 1) for x in self.bits):
            raise ValueError("invalid binary state")
        if self.physics not in FAMILIES or self.hidden_orientation not in (0, 1):
            raise ValueError("invalid evaluator physics")
        if type(self.contact_count) is not int or self.contact_count < 0:
            raise ValueError("invalid intervention history")


def draw_world(seed: int, index: int, physics: str) -> StressWorld:
    """Independent development lineage, never G0 train/calibration/challenge."""
    if physics not in FAMILIES or type(seed) is not int or type(index) is not int or index < 0:
        raise ValueError("invalid development lineage")
    material = json.dumps(["g1d-public-development-v1", seed, index, physics], separators=(",", ":"))
    digest = sha256(material.encode()).digest()
    rng = random.Random(int.from_bytes(digest, "big"))
    n = rng.randint(3, 6)
    ids = tuple(sha256(digest + j.to_bytes(2, "big")).hexdigest()[:12] for j in range(n))
    return StressWorld(ids, tuple(rng.randrange(2) for _ in ids), rng.randrange(2), physics)


def change(world: StressWorld, action: dict) -> StressWorld:
    """Pure evaluator-owned transition for OOD or reference physics."""
    if set(action) - {"kind", "participants", "value"}:
        raise ValueError("unrecognized action field")
    kind = action.get("kind")
    names = action.get("participants", [])
    if not isinstance(names, (tuple, list)) or any(n not in world.ids for n in names):
        raise ValueError("unknown entity operand")
    value = action.get("value")
    bits = list(world.bits)
    contacts = world.contact_count
    if kind == "observe" and not names and value is None:
        pass
    elif kind == "set" and len(names) == 1 and type(value) is int and value in (0, 1):
        bits[world.ids.index(names[0])] = value
    elif kind == "contact" and len(names) == 2 and names[0] != names[1] and value is None:
        i, j = (world.ids.index(n) for n in names)
        a, b = bits[i], bits[j]
        if world.physics == "bilateral_flip":
            bits[i], bits[j] = a ^ b, b ^ a
        else:
            orientation = world.hidden_orientation
            if world.physics == "switch_orientation" and contacts >= 1:
                orientation = 1 - orientation
            source, target = (i, j) if orientation == 0 else (j, i)
            if world.physics == "conditional_flip":
                bits[target] ^= bits[source] & bits[target]
            else:
                bits[target] ^= bits[source]
        contacts += 1
    else:
        raise ValueError("invalid world action")
    return StressWorld(world.ids, tuple(bits), world.hidden_orientation, world.physics, contacts)


def choose_visibility(ids: tuple[str, ...], rng: random.Random, missing_rate: float) -> tuple[str, ...]:
    """Select coverage *before* reading any state, independent of bit values."""
    if not 0 <= missing_rate <= 1:
        raise ValueError("invalid coverage model")
    return tuple(name for name in ids if rng.random() >= missing_rate)


def sensor_reading(world: StressWorld, t: int, visible: tuple[str, ...],
                   rng: random.Random, flip_rate: float) -> dict:
    if not 0 <= flip_rate < .5 or len(set(visible)) != len(visible) or any(n not in world.ids for n in visible):
        raise ValueError("invalid sensor configuration")
    return {"t": t, "measurements": [
        {"id": name, "bit": world.bits[world.ids.index(name)] ^ int(rng.random() < flip_rate)}
        for name in visible]}
