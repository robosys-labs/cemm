"""LexemeSenseSchema — lexical form to semantic schema relation."""
from __future__ import annotations

from dataclasses import dataclass

from ..model.surface import LexicalFormRef


@dataclass(frozen=True, slots=True)
class LexemeSenseSchema:
    semantic_key: str
    lexical_form_refs: tuple[LexicalFormRef, ...] = ()
    semantic_schema_ref: str = ""
    part_of_speech: str = ""
    selectional_constraints: tuple[str, ...] = ()
    sense_disambiguators: tuple[str, ...] = ()
