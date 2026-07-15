"""LexemeSenseSchema — lexical form to semantic schema relation.

`semantic_schema_ref` is the general authority.  `predicate_schema_ref` is kept
for source compatibility with v3.4 callers and is used only as a fallback.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..model.surface import LexicalFormRef


@dataclass(frozen=True, slots=True)
class LexemeSenseSchema:
    semantic_key: str
    lexical_form_refs: tuple[LexicalFormRef, ...] = ()
    semantic_schema_ref: str = ""
    predicate_schema_ref: str = ""
    part_of_speech: str = ""
    selectional_constraints: tuple[str, ...] = ()
    sense_disambiguators: tuple[str, ...] = ()

    @property
    def resolved_schema_ref(self) -> str:
        return self.semantic_schema_ref or self.predicate_schema_ref
