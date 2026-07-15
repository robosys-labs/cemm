"""Typed declarative input construction schemas.

The generic matcher knows token evidence operators, not words or language
phrases.  Language packs supply the lexical and construction data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MatchKind(str, Enum):
    ANY = "any"
    SURFACE = "surface"
    LEMMA = "lemma"
    SEMANTIC_KEY = "semantic_key"
    SEMANTIC_PREFIX = "semantic_prefix"
    TOKEN_KIND = "token_kind"
    FEATURE = "feature"
    BOUNDARY = "boundary"


@dataclass(frozen=True, slots=True)
class TokenConstraint:
    kind: MatchKind
    values: tuple[str, ...] = ()
    negate: bool = False


@dataclass(frozen=True, slots=True)
class ConstructionTerm:
    term_id: str
    constraints: tuple[TokenConstraint, ...]
    capture_key: str = ""
    minimum_occurs: int = 1
    maximum_occurs: int = 1


@dataclass(frozen=True, slots=True)
class PostMatchConstraint:
    constraint_kind: str
    capture_key: str = ""
    values: tuple[str, ...] = ()
    other_capture_key: str = ""
    negate: bool = False


@dataclass(frozen=True, slots=True)
class InputConstructionSchema:
    schema_id: str
    language_tag: str
    terms: tuple[ConstructionTerm, ...]
    predicate_key: str
    role_capture_map: dict[str, str]
    open_role_keys: tuple[str, ...]
    communicative_force: str
    polarity: str = "positive"
    modality: str = "actual"
    output_kind: str = "predication"
    output_metadata: dict[str, Any] = field(default_factory=dict)
    post_constraints: tuple[PostMatchConstraint, ...] = ()
    competence_case_refs: tuple[str, ...] = ()
    round_trip_case_refs: tuple[str, ...] = ()
    priority: int = 0
    version: int = 1

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "InputConstructionSchema":
        """Parse old-format JSON (from pack.json) into InputConstructionSchema."""
        from .construction import MatchKind as MK
        terms = tuple(
            ConstructionTerm(
                term_id=str(term["id"]),
                constraints=tuple(
                    TokenConstraint(
                        kind=MK(matcher["kind"]),
                        values=tuple(str(v) for v in matcher.get("values", ())),
                        negate=bool(matcher.get("negate", False)),
                    )
                    for matcher in term.get("matchers", ())
                ),
                capture_key=str(term.get("capture", "")),
                minimum_occurs=(
                    0 if term.get("optional", False)
                    else int(term.get("min_occurs", 1))
                ),
                maximum_occurs=int(term.get("max_occurs", 1)),
            )
            for term in raw.get("terms", ())
        )
        return cls(
            schema_id=str(raw["semantic_key"]),
            language_tag=str(raw.get("language_tag", "und")),
            terms=terms,
            predicate_key=str(raw.get("predicate_schema_ref", "")),
            role_capture_map={
                str(role): str(capture)
                for role, capture in raw.get("role_mappings", {}).items()
            },
            open_role_keys=tuple(str(v) for v in raw.get("open_role_refs", ())),
            communicative_force=str(raw.get("communicative_force", "")),
            polarity=str(raw.get("polarity", "positive")),
            modality=str(raw.get("modality", "actual")),
            output_kind=str(raw.get("output_kind", "predication")),
            output_metadata=dict(raw.get("output_metadata", {})),
            post_constraints=tuple(
                PostMatchConstraint(
                    constraint_kind=str(item["kind"]),
                    capture_key=str(item.get("capture", "")),
                    values=tuple(str(v) for v in item.get("values", ())),
                    other_capture_key=str(item.get("argument", "")),
                    negate=bool(item.get("negate", False)),
                )
                for item in raw.get("constraints", ())
            ),
            competence_case_refs=tuple(
                str(v) for v in raw.get("competence_case_refs", ())
            ),
            round_trip_case_refs=tuple(
                str(v) for v in raw.get("round_trip_case_refs", ())
            ),
            priority=int(raw.get("priority", 0)),
            version=int(raw.get("version", 1)),
        )


# Backward-compatible alias
ConstructionSchema = InputConstructionSchema


@dataclass(frozen=True, slots=True)
class LexicalInputMapping:
    mapping_id: str
    language_tag: str
    surface_forms: tuple[str, ...]
    lemma_forms: tuple[str, ...]
    semantic_key: str
    part_of_speech: str
    morphological_features: dict[str, str] = field(default_factory=dict)
    grounding_contract_ref: str = ""
    competence_case_refs: tuple[str, ...] = ()
    version: int = 1
