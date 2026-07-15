"""Versioned language-pack data and registry."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import json
from typing import Any
from ..kernel.schema.construction import InputConstructionSchema

@dataclass(frozen=True, slots=True)
class LexicalEntry:
    surface: str
    semantic_key: str
    part_of_speech: str = ""
    lemma: str = ""
    features: dict[str, str] = field(default_factory=dict)
    confidence: float = 0.95

@dataclass(frozen=True, slots=True)
class RealizationSegment:
    kind: str
    value: str = ""
    role: str = ""
    form: str = "base"
    use_mode: str = "assert"

@dataclass(frozen=True, slots=True)
class RealizationVariant:
    segments: tuple[RealizationSegment, ...]
    when: dict[str, Any] = field(default_factory=dict)
    priority: int = 0

@dataclass(frozen=True, slots=True)
class ClauseRealization:
    predicate_key: str
    communicative_force: str = "assert"
    polarity: str = "positive"
    qualification_key: str = ""
    variants: tuple[RealizationVariant, ...] = ()

@dataclass(frozen=True, slots=True)
class CueRule:
    cue_kind: str
    condition: dict[str, Any]
    value: str = "present"
    confidence: float = 0.8

@dataclass(frozen=True, slots=True)
class LanguagePack:
    language_tag: str
    version: str
    lexical_entries: tuple[LexicalEntry, ...]
    constructions: tuple[InputConstructionSchema, ...]
    realizations: tuple[ClauseRealization, ...]
    cue_rules: tuple[CueRule, ...] = ()
    referent_surfaces: dict[str, str] = field(default_factory=dict)
    closed_class_semantic_keys: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "LanguagePack":
        return cls(
            language_tag=str(raw["language_tag"]),
            version=str(raw.get("version", "1")),
            lexical_entries=tuple(
                LexicalEntry(
                    surface=str(item["surface"]),
                    semantic_key=str(item["semantic_key"]),
                    part_of_speech=str(item.get("part_of_speech", "")),
                    lemma=str(item.get("lemma", item["surface"])),
                    features={str(k): str(v) for k, v in item.get("features", {}).items()},
                    confidence=float(item.get("confidence", 0.95)),
                )
                for item in raw.get("lexical_entries", ())
            ),
            constructions=tuple(
                InputConstructionSchema.from_dict(item)
                for item in raw.get("constructions", ())
            ),
            realizations=tuple(
                ClauseRealization(
                    predicate_key=str(item["predicate_key"]),
                    communicative_force=str(item.get("communicative_force", "assert")),
                    polarity=str(item.get("polarity", "positive")),
                    qualification_key=str(item.get("qualification_key", "")),
                    variants=tuple(
                        RealizationVariant(
                            segments=tuple(
                                RealizationSegment(
                                    kind=str(segment["kind"]),
                                    value=str(segment.get("value", "")),
                                    role=str(segment.get("role", "")),
                                    form=str(segment.get("form", "base")),
                                    use_mode=str(segment.get("use_mode", "assert")),
                                )
                                for segment in variant.get("segments", ())
                            ),
                            when=dict(variant.get("when", {})),
                            priority=int(variant.get("priority", 0)),
                        )
                        for variant in item.get("variants", ())
                    ),
                )
                for item in raw.get("realizations", ())
            ),
            cue_rules=tuple(
                CueRule(
                    cue_kind=str(item["cue_kind"]),
                    condition=dict(item.get("condition", {})),
                    value=str(item.get("value", "present")),
                    confidence=float(item.get("confidence", 0.8)),
                )
                for item in raw.get("cue_rules", ())
            ),
            referent_surfaces={
                str(k): str(v) for k, v in raw.get("referent_surfaces", {}).items()
            },
            closed_class_semantic_keys=frozenset(
                str(v) for v in raw.get("closed_class_semantic_keys", ())
            ),
        )

    def lexical_keys(self, surface: str, lemma: str = "") -> tuple[str, ...]:
        forms = {surface.casefold(), lemma.casefold()}
        return tuple(dict.fromkeys(
            entry.semantic_key
            for entry in self.lexical_entries
            if entry.surface.casefold() in forms or entry.lemma.casefold() in forms
        ))

    def lexical_entry(self, semantic_key: str) -> LexicalEntry | None:
        return next(
            (entry for entry in self.lexical_entries if entry.semantic_key == semantic_key),
            None,
        )

    def realization_candidates(self, predicate_key, force, polarity, qualification_key=""):
        return tuple(
            item for item in self.realizations
            if item.predicate_key == predicate_key
            and item.communicative_force == force
            and item.polarity == polarity
            and (not item.qualification_key or item.qualification_key == qualification_key)
        )

class LanguagePackRegistry:
    def __init__(self) -> None:
        self._packs: dict[str, LanguagePack] = {}

    def register(self, pack: LanguagePack) -> None:
        self._packs[pack.language_tag] = pack

    def load_file(self, path: Path) -> LanguagePack:
        pack = LanguagePack.from_dict(json.loads(path.read_text(encoding="utf-8")))
        self.register(pack)
        return pack

    def load_directory(self, root: Path) -> tuple[LanguagePack, ...]:
        return tuple(self.load_file(path) for path in sorted(root.glob("*/pack.json")))

    def get(self, language_tag: str) -> LanguagePack | None:
        return self._packs.get(language_tag) or self._packs.get(language_tag.split("-", 1)[0])

    def require(self, language_tag: str) -> LanguagePack:
        pack = self.get(language_tag)
        if pack is None:
            raise LookupError(f"no language pack for {language_tag!r}")
        return pack

    @property
    def language_tags(self) -> tuple[str, ...]:
        return tuple(sorted(self._packs))
