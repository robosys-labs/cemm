"""External syntax-adapter boundary.

Adapters contribute evidence only.  CEMM does not require a particular parser,
and an adapter result cannot directly select semantic schemas or referents.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from .model import ConstituencyParseEvidence, DependencyParseEvidence, FormObservation


@dataclass(frozen=True, slots=True)
class SyntaxAdapterInput:
    source_ref: str
    content: str
    observations: tuple[FormObservation, ...]
    language_tags: tuple[str, ...]


class DependencyAdapter(Protocol):
    adapter_ref: str

    def analyze(self, request: SyntaxAdapterInput) -> DependencyParseEvidence | None: ...


class ConstituencyAdapter(Protocol):
    adapter_ref: str

    def analyze(self, request: SyntaxAdapterInput) -> ConstituencyParseEvidence | None: ...


class SyntaxAdapterHub:
    def __init__(
        self,
        dependency_adapters: Sequence[DependencyAdapter] = (),
        constituency_adapters: Sequence[ConstituencyAdapter] = (),
    ) -> None:
        self._dependency = tuple(dependency_adapters)
        self._constituency = tuple(constituency_adapters)
        refs = [item.adapter_ref for item in (*self._dependency, *self._constituency)]
        if len(refs) != len(set(refs)):
            raise ValueError("syntax adapter refs must be unique")

    def analyze(self, request: SyntaxAdapterInput) -> tuple[
        tuple[DependencyParseEvidence, ...], tuple[ConstituencyParseEvidence, ...]
    ]:
        dependencies = tuple(
            result for adapter in self._dependency
            if (result := adapter.analyze(request)) is not None
        )
        constituencies = tuple(
            result for adapter in self._constituency
            if (result := adapter.analyze(request)) is not None
        )
        return dependencies, constituencies
