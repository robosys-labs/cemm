"""Language-specific lexical and grammatical realization contracts.

No content word is emitted as an unrestricted literal.  Punctuation and spacing
are the only literal segment classes.  Every morpheme carries a semantic or
grammatical contribution and a competence reference.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any


class SegmentKind(str, Enum):
    LEXEME = "lexeme"
    GRAMMATICAL_MORPHEME = "grammatical_morpheme"
    REFERRING_EXPRESSION = "referring_expression"
    ROLE_VALUE = "role_value"
    MENTION = "mention"
    QUOTATION = "quotation"
    PUNCTUATION = "punctuation"
    SPACE = "space"


@dataclass(frozen=True, slots=True)
class SemanticContribution:
    contribution_id: str
    contribution_kind: str
    semantic_key: str = ""
    role_key: str = ""
    feature_key: str = ""
    feature_value: str = ""


@dataclass(frozen=True, slots=True)
class LexicalizationSchema:
    schema_id: str
    language_tag: str
    semantic_key: str
    lemma: str
    forms: dict[str, str]
    part_of_speech: str
    permitted_use_modes: frozenset[str]
    contributions: tuple[SemanticContribution, ...]
    grounding_contract_ref: str
    competence_case_refs: tuple[str, ...]
    round_trip_case_refs: tuple[str, ...]
    version: int = 1

    def surface(self, form_key: str = "base") -> str:
        return self.forms.get(form_key, self.forms.get("base", ""))


@dataclass(frozen=True, slots=True)
class GrammaticalMorphemeSchema:
    schema_id: str
    language_tag: str
    morpheme_key: str
    forms: dict[str, str]
    contributions: tuple[SemanticContribution, ...]
    competence_case_refs: tuple[str, ...]
    round_trip_case_refs: tuple[str, ...]
    version: int = 1

    def surface(self, form_key: str = "base") -> str:
        return self.forms.get(form_key, self.forms.get("base", ""))


@dataclass(frozen=True, slots=True)
class RealizationSegment:
    kind: SegmentKind
    schema_ref: str = ""
    role_key: str = ""
    form_key: str = "base"
    punctuation: str = ""
    contribution_refs: tuple[str, ...] = ()
    required: bool = True


@dataclass(frozen=True, slots=True)
class ConstructionRealizationSchema:
    schema_id: str
    language_tag: str
    predicate_key: str
    communicative_force: str
    polarity: str
    required_role_keys: tuple[str, ...]
    segments: tuple[RealizationSegment, ...]
    construction_contributions: tuple[SemanticContribution, ...]
    competence_case_refs: tuple[str, ...]
    round_trip_case_refs: tuple[str, ...]
    qualification_key: str = ""
    priority: int = 0
    version: int = 1


class LanguageRealizationPack:
    def __init__(
        self,
        *,
        language_tag: str,
        lexicalizations: tuple[LexicalizationSchema, ...],
        morphemes: tuple[GrammaticalMorphemeSchema, ...],
        constructions: tuple[ConstructionRealizationSchema, ...],
        referring_expressions: dict[str, str],
        fingerprint: str,
    ) -> None:
        self.language_tag = language_tag
        self.lexicalizations = {
            item.schema_id: item for item in lexicalizations
        }
        self.lexicalizations_by_key: dict[str, tuple[LexicalizationSchema, ...]] = {}
        for item in lexicalizations:
            current = self.lexicalizations_by_key.get(item.semantic_key, ())
            self.lexicalizations_by_key[item.semantic_key] = (*current, item)
        self.morphemes = {item.schema_id: item for item in morphemes}
        self.constructions = constructions
        self.referring_expressions = referring_expressions
        self.fingerprint = fingerprint

    def lexicalization(
        self,
        semantic_key: str,
        use_mode: str,
    ) -> LexicalizationSchema | None:
        return next(
            (
                item
                for item in self.lexicalizations_by_key.get(semantic_key, ())
                if use_mode in item.permitted_use_modes
            ),
            None,
        )

    def construction(
        self,
        *,
        predicate_key: str,
        communicative_force: str,
        polarity: str,
        qualification_key: str,
        role_keys: frozenset[str],
    ) -> ConstructionRealizationSchema | None:
        candidates = [
            item
            for item in self.constructions
            if item.predicate_key == predicate_key
            and item.communicative_force == communicative_force
            and item.polarity == polarity
            and (
                not item.qualification_key
                or item.qualification_key == qualification_key
            )
            and set(item.required_role_keys) <= role_keys
        ]
        return max(candidates, key=lambda item: item.priority, default=None)

    def validate(self) -> tuple[str, ...]:
        failures: list[str] = []
        for lexicalization in self.lexicalizations.values():
            if not lexicalization.grounding_contract_ref:
                failures.append(
                    f"{lexicalization.schema_id}: no grounding contract"
                )
            if not lexicalization.competence_case_refs:
                failures.append(
                    f"{lexicalization.schema_id}: no competence cases"
                )
            if not lexicalization.round_trip_case_refs:
                failures.append(
                    f"{lexicalization.schema_id}: no round-trip cases"
                )
            if not lexicalization.forms.get("base"):
                failures.append(f"{lexicalization.schema_id}: no base form")

        for morpheme in self.morphemes.values():
            if not morpheme.contributions:
                failures.append(f"{morpheme.schema_id}: no grammatical contribution")
            if not morpheme.competence_case_refs:
                failures.append(f"{morpheme.schema_id}: no competence cases")

        for construction in self.constructions:
            if not construction.competence_case_refs:
                failures.append(f"{construction.schema_id}: no competence cases")
            if not construction.round_trip_case_refs:
                failures.append(f"{construction.schema_id}: no round-trip cases")
            for segment in construction.segments:
                if segment.kind in {
                    SegmentKind.PUNCTUATION,
                    SegmentKind.SPACE,
                }:
                    if segment.schema_ref or segment.role_key:
                        failures.append(
                            f"{construction.schema_id}: punctuation/space carries schema"
                        )
                elif not segment.schema_ref and not segment.role_key:
                    failures.append(
                        f"{construction.schema_id}: uncovered content segment"
                    )
                if segment.kind is SegmentKind.PUNCTUATION:
                    if not segment.punctuation:
                        failures.append(
                            f"{construction.schema_id}: empty punctuation"
                        )
                    if any(ch.isalnum() for ch in segment.punctuation):
                        failures.append(
                            f"{construction.schema_id}: content literal in punctuation"
                        )
        return tuple(failures)

    @classmethod
    def load(cls, path: Path) -> "LanguageRealizationPack":
        raw = json.loads(path.read_text(encoding="utf-8"))
        digest = hashlib.sha256(path.read_bytes()).hexdigest()

        def contributions(values: list[dict[str, Any]]):
            return tuple(
                SemanticContribution(
                    contribution_id=item["contribution_id"],
                    contribution_kind=item["contribution_kind"],
                    semantic_key=item.get("semantic_key", ""),
                    role_key=item.get("role_key", ""),
                    feature_key=item.get("feature_key", ""),
                    feature_value=item.get("feature_value", ""),
                )
                for item in values
            )

        lexicalizations = tuple(
            LexicalizationSchema(
                schema_id=item["schema_id"],
                language_tag=raw["language_tag"],
                semantic_key=item["semantic_key"],
                lemma=item["lemma"],
                forms=dict(item["forms"]),
                part_of_speech=item["part_of_speech"],
                permitted_use_modes=frozenset(item["permitted_use_modes"]),
                contributions=contributions(item["contributions"]),
                grounding_contract_ref=item["grounding_contract_ref"],
                competence_case_refs=tuple(item["competence_case_refs"]),
                round_trip_case_refs=tuple(item["round_trip_case_refs"]),
                version=int(item.get("version", 1)),
            )
            for item in raw["lexicalizations"]
        )
        morphemes = tuple(
            GrammaticalMorphemeSchema(
                schema_id=item["schema_id"],
                language_tag=raw["language_tag"],
                morpheme_key=item["morpheme_key"],
                forms=dict(item["forms"]),
                contributions=contributions(item["contributions"]),
                competence_case_refs=tuple(item["competence_case_refs"]),
                round_trip_case_refs=tuple(item["round_trip_case_refs"]),
                version=int(item.get("version", 1)),
            )
            for item in raw["morphemes"]
        )
        constructions = tuple(
            ConstructionRealizationSchema(
                schema_id=item["schema_id"],
                language_tag=raw["language_tag"],
                predicate_key=item["predicate_key"],
                communicative_force=item["communicative_force"],
                polarity=item.get("polarity", "positive"),
                qualification_key=item.get("qualification_key", ""),
                required_role_keys=tuple(item["required_role_keys"]),
                segments=tuple(
                    RealizationSegment(
                        kind=SegmentKind(segment["kind"]),
                        schema_ref=segment.get("schema_ref", ""),
                        role_key=segment.get("role_key", ""),
                        form_key=segment.get("form_key", "base"),
                        punctuation=segment.get("punctuation", ""),
                        contribution_refs=tuple(segment.get("contribution_refs", ())),
                        required=bool(segment.get("required", True)),
                    )
                    for segment in item["segments"]
                ),
                construction_contributions=contributions(
                    item.get("construction_contributions", ())
                ),
                competence_case_refs=tuple(item["competence_case_refs"]),
                round_trip_case_refs=tuple(item["round_trip_case_refs"]),
                priority=int(item.get("priority", 0)),
                version=int(item.get("version", 1)),
            )
            for item in raw["constructions"]
        )
        pack = cls(
            language_tag=raw["language_tag"],
            lexicalizations=lexicalizations,
            morphemes=morphemes,
            constructions=constructions,
            referring_expressions=dict(raw.get("referring_expressions", {})),
            fingerprint=digest,
        )
        failures = pack.validate()
        if failures:
            raise ValueError(
                f"invalid language pack {path}: " + "; ".join(failures)
            )
        return pack
