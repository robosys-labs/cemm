from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LatentSpaceSpec:
    """Specification for a typed latent space."""

    name: str
    dim: int
    description: str = ""
    version: str = "cemm.latent_space.v1"


@dataclass
class TypedLatents:
    """Typed latent embeddings for the major meaning objects in the architecture."""

    entity: list[float] = field(default_factory=list)
    process: list[float] = field(default_factory=list)
    state: list[float] = field(default_factory=list)
    claim: list[float] = field(default_factory=list)
    model: list[float] = field(default_factory=list)
    context: list[float] = field(default_factory=list)
    self: list[float] = field(default_factory=list)
    memory: list[float] = field(default_factory=list)
    action: list[float] = field(default_factory=list)
    answer: list[float] = field(default_factory=list)
