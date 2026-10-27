"""G1 binary-contact physics and deterministic episodes (no learner or language).

Oracle dynamics are confined here. Never import World.hidden_source_slot or
Episode.states into a learner. Public input is built by `learner_turn`, while
`t+1` feedback is produced separately, after a prediction has been requested.
"""
from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from typing import Callable, Any

from .protocol import read_protocol, verify_protocol

FAMILIES = {
    "single_contact": ((0, 1),),
    "two_contacts": ((0, 1), (1, 2)),
    "three_contact_chain": ((0, 1), (1, 2), (2, 3)),
    "fork": ((0, 1), (0, 2), (0, 3)),
    "cycle": ((0, 1), (1, 2), (2, 0)),
    "disjoint": ((0, 1), (2, 3)),
    "self_contact": ((0, 0),),
}


@dataclass(frozen=True)
class World:
    ids: tuple[str, ...]
    bits: tuple[int, ...]
    hidden_source_slot: int

    def __post_init__(self) -> None:
        if not (3 <= len(self.ids) <= 6) or len(set(self.ids)) != len(self.ids):
            raise ValueError("world must have 3-6 distinct same-kind handles")
        if len(self.ids) != len(self.bits) or any(type(b) is not int or b not in (0, 1) for b in self.bits):
            raise ValueError("world must have one binary value per handle")
        if self.hidden_source_slot not in (0, 1):
            raise ValueError("latent orientation is binary")


@dataclass(frozen=True)
class Action:
    kind: str
    participants: tuple[str, ...] = ()
    value: int | None = None

    def public(self) -> dict:
        result = {"kind": self.kind, "participants": list(self.participants)}
        if self.kind == "set":
            result["value"] = self.value
        return result


def step(world: World, action: Action) -> World:
    """Pure transition: no mutations, no effects outside these in-memory bits."""
    ids = world.ids
    if any(x not in ids for x in action.participants):
        raise ValueError("unknown identity")
    bits = list(world.bits)
    if action.kind == "observe":
        if action.participants or action.value is not None:
            raise ValueError("observe takes no operands")
    elif action.kind == "set":
        if len(action.participants) != 1 or type(action.value) is not int or action.value not in (0, 1):
            raise ValueError("set expects one participant and binary value")
        bits[ids.index(action.participants[0])] = action.value
    elif action.kind == "contact":
        if len(action.participants) != 2 or action.value is not None:
            raise ValueError("contact expects precisely two ordered handles")
        # The orientation is simulator-private physics. A learner must discover
        # role effects through outcome-only evidence; no role names in action.
        src = ids.index(action.participants[world.hidden_source_slot])
        dst = ids.index(action.participants[1 - world.hidden_source_slot])
        bits[dst] ^= world.bits[src]
    else:
        raise ValueError("unknown action")
    return World(ids, tuple(bits), world.hidden_source_slot)


def observe(world: World, time: int, visible: tuple[str, ...]) -> dict:
    """Sensor samples in a supplied order; no hidden world fields or gold."""
    if len(set(visible)) != len(visible) or any(x not in world.ids for x in visible):
        raise ValueError("invalid sensor handles")
    if not isinstance(time, int) or time < 0:
        raise ValueError("invalid observation time")
    return {"t": time, "measurements": [{"id": name, "bit": world.bits[world.ids.index(name)]} for name in visible]}


def _seed_bytes(split: str, seed: int, index: int, family: str) -> bytes:
    # Versioned identity derives from the preregistered split/seed lineage;
    # never from a runtime hash(), global RNG or test gold.
    material = json.dumps(["binary-contact-v1", split, seed, index, family], separators=(",", ":"))
    return hashlib.sha256(material.encode("utf-8")).digest()


@dataclass(frozen=True)
class Episode:
    lineage_id: str
    split: str
    family: str
    seed: int
    states: tuple[World, ...]             # EVALUATOR ONLY, never fed to model
    actions: tuple[Action, ...]
    sensors: tuple[dict, ...]             # sampled AFTER each corresponding action

    def __post_init__(self) -> None:
        if len(self.states) != len(self.actions) + 1 or len(self.states) != len(self.sensors):
            raise ValueError("episode timeline misaligned")

    def learner_turn(self, index: int) -> dict:
        """Pre-action evidence ONLY: no future observation, gold or orientation."""
        return {"observation": self.sensors[index], "action": self.actions[index].public()}

    def reveal_after_prediction(self, index: int) -> dict:
        """Training feedback AFTER predict; hidden unobserved bits never revealed."""
        return self.sensors[index + 1]

    def gold_after(self, index: int) -> dict[str, int]:
        """Evaluator-owned complete post-action truth, not a training feature."""
        world = self.states[index + 1]
        return dict(zip(world.ids, world.bits))


def make_episode(split: str, seed: int, index: int, family: str) -> Episode:
    """Deterministic independent-world draw; entire OOD families held out.

    Keep sealed-challenge seeds out of local optimization/test loops. This is
    a public generator, NOT encrypted blindness or independent oracle custody.
    """
    config = read_protocol()
    verify_protocol(config)
    if split not in config["splits"] or family not in config["splits"][split]["families"]:
        raise ValueError("invalid split/family; OOD families cannot become training data")
    if type(seed) is not int or seed not in config["splits"][split]["seeds"]:
        raise ValueError("seed not in frozen split")
    if type(index) is not int or index < 0:
        raise ValueError("invalid episode index")
    fingerprint = _seed_bytes(split, seed, index, family)
    rng = random.Random(int.from_bytes(fingerprint, "big"))
    topology = FAMILIES[family]
    min_agents = max(3, 1 + max(max(pair) for pair in topology))
    n = rng.randint(min_agents, 6)
    # Public IDs are opaque hashes, never semantic labels, graph positions or
    # shared entity strings across independent worlds.
    ids = tuple(hashlib.sha256(fingerprint + i.to_bytes(2, "big")).hexdigest()[:12] for i in range(n))
    start = World(ids, tuple(rng.randrange(2) for _ in ids), rng.randrange(2))
    actions: list[Action] = []
    for a, b in topology:
        actions.append(Action("set", (ids[a],), rng.randrange(2)))
        if b != a:
            actions.append(Action("set", (ids[b],), rng.randrange(2)))
        actions.append(Action("contact", (ids[a], ids[b])))
        if rng.random() < .3:
            actions.append(Action("observe"))
    if len(actions) > config["budgets"]["max_actions_per_episode"]:
        raise ValueError("world exceeds frozen action budget")
    states = [start]
    initial_order = list(ids)
    rng.shuffle(initial_order)
    sensors = [observe(start, 0, tuple(initial_order))]  # initial COMPLETE observation
    for time, action in enumerate(actions, 1):
        next_world = step(states[-1], action)
        states.append(next_world)
        visible = list(ids)
        rng.shuffle(visible)
        if rng.random() < .35:
            visible = visible[:rng.randint(1, len(visible))]
        sensors.append(observe(next_world, time, tuple(visible)))
    return Episode(fingerprint.hex()[:20], split, family, seed, tuple(states), tuple(actions), tuple(sensors))


def causal_replay(episode: Episode, predict: Callable[[dict], Any],
                  receive: Callable[[dict], None]) -> list[Any]:
    """Causal API: predict from pre-action input, then deliver post-action evidence.

    An offline trace is always accessible to an evaluator; only this callback
    interface should be used to feed a learner during training/evaluation.
    """
    predictions = []
    for idx in range(len(episode.actions)):
        predictions.append(predict(episode.learner_turn(idx)))
        receive(episode.reveal_after_prediction(idx))
    return predictions
