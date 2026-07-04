from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FormSignature:
    surface_pattern: str = ""
    pos_pattern: str = ""
    dependency_pattern: str = ""


@dataclass
class PragmaticPattern:
    expected_acts: list[str] = field(default_factory=list)
    expected_modes: list[str] = field(default_factory=list)


@dataclass
class PortConstraint:
    port_key: str
    source_concept: str = ""
    target_concept: str = ""
    edge_type: str = ""


@dataclass
class ConstructionAtom:
    construction_id: str
    form_signature: FormSignature = field(default_factory=FormSignature)
    graph_signature: Any = None
    pragmatic_signature: PragmaticPattern | None = None
    port_constraints: list[PortConstraint] = field(default_factory=list)
    operator_effects: list[Any] = field(default_factory=list)
    support_count: int = 0
    counterexamples: list[Any] = field(default_factory=list)
    confidence: float = 0.5
