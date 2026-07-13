"""LexemeSenseSchema — executable definition of a lexical sense.

Import boundary: standard library only → model.refs, model.surface.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..model.surface import LexicalFormRef


@dataclass(frozen=True, slots=True)
class LexemeSenseSchema:
    """Executable definition of a lexical sense.

    One lexical form may map to multiple senses. One schema may have
    multiple lexicalizations. Opaque uses of one spelling may remain
    separate candidate sense clusters until evidence supports merge.
    """
    semantic_key: str
    lexical_form_refs: tuple[LexicalFormRef, ...] = ()
    predicate_schema_ref: str = ""  # Ref[PredicateSchema]
    part_of_speech: str = ""
    selectional_constraints: tuple[str, ...] = ()
    sense_disambiguators: tuple[str, ...] = ()
