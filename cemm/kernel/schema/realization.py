"""RealizationSchema — a validated expression of an existing semantic schema.

A realization schema never creates meaning.  Open-class lexicalization is
licensed only when it points to a usable semantic schema revision.  Closed
class material instead points to audited grammar competence tests.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..model.refs import FrozenMap


@dataclass(frozen=True, slots=True)
class RealizationSchema:
    semantic_key: str
    language_tag: str
    lemma: str
    part_of_speech: str
    forms: FrozenMap = field(default_factory=FrozenMap)
    semantic_schema_ref: str = ""
    allowed_use_modes: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {"mention", "quote", "probe", "qualified", "assert"}
        )
    )
    closed_class: bool = False
    competence_test_refs: tuple[str, ...] = ()

    def surface_for(self, form_key: str = "base") -> str:
        try:
            value = self.forms[form_key]
        except KeyError:
            value = self.lemma
        return str(value or self.lemma)
