"""Bounded reversible pre-core form processing for CEMM v1.

This module is deliberately outside semantic authority.  It preserves raw
input, proposes normalization/token/span alternatives, and builds bounded
form/grounding hypotheses with provenance.  It never commits, creates semantic
atoms, decides world truth, or directly selects a discourse act.

Language-specific construction records may *propose* exact semantic packets at
Stage 5 through :class:`ConstructionCandidateGenerator`; the exact compiler and
settler remain authoritative.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from cemm.model import canonical, lit, norm_text, stable

_WORD = re.compile(r"\w+(?:['\u2019-]\w+)*|[^\w\s]", re.UNICODE)
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_ZERO_WIDTH = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]")
_BIDI_CONTROL = re.compile(r"[\u202a-\u202e\u2066-\u2069]")
_SPACE = re.compile(r"\s+")
_APOSTROPHES = str.maketrans({"\u2018": "'", "\u2019": "'", "\u02bc": "'", "\uff07": "'"})


@dataclass(frozen=True)
class TextTransform:
    kind: str
    before: str
    after: str
    raw_start: int = 0
    raw_end: int = 0
    reversible: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "before": self.before,
            "after": self.after,
            "raw_start": self.raw_start,
            "raw_end": self.raw_end,
            "reversible": self.reversible,
        }


@dataclass(frozen=True)
class SourceSegment:
    output_start: int
    output_end: int
    raw_start: int
    raw_end: int

    def as_dict(self) -> dict[str, int]:
        return {
            "output_start": self.output_start,
            "output_end": self.output_end,
            "raw_start": self.raw_start,
            "raw_end": self.raw_end,
        }


@dataclass(frozen=True)
class NormalizationCandidate:
    candidate_ref: str
    raw_text: str
    text: str
    score: float
    transforms: tuple[TextTransform, ...] = ()
    source_map: tuple[SourceSegment, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_ref": self.candidate_ref,
            "raw_text": self.raw_text,
            "text": self.text,
            "score": self.score,
            "transforms": [item.as_dict() for item in self.transforms],
            "source_map": [item.as_dict() for item in self.source_map],
        }


@dataclass(frozen=True)
class TokenEvidence:
    token_ref: str
    surface: str
    normalized: str
    start: int
    end: int
    raw_start: int
    raw_end: int
    category: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "token_ref": self.token_ref,
            "surface": self.surface,
            "normalized": self.normalized,
            "start": self.start,
            "end": self.end,
            "raw_start": self.raw_start,
            "raw_end": self.raw_end,
            "category": self.category,
        }


@dataclass(frozen=True)
class SurfaceCandidate:
    candidate_ref: str
    source_kind: str
    semantic_ref: str
    atom_kind: str
    surface: str
    language: str
    weight: float
    label_type: str | None = None
    features: Mapping[str, Any] = field(default_factory=dict)
    context_ref: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_ref": self.candidate_ref,
            "source_kind": self.source_kind,
            "semantic_ref": self.semantic_ref,
            "atom_kind": self.atom_kind,
            "surface": self.surface,
            "language": self.language,
            "weight": self.weight,
            "label_type": self.label_type,
            "features": dict(self.features),
            "context_ref": self.context_ref,
        }


@dataclass(frozen=True)
class GroundingSpan:
    span_ref: str
    token_start: int
    token_end: int
    char_start: int
    char_end: int
    surface: str
    candidates: tuple[SurfaceCandidate, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "span_ref": self.span_ref,
            "token_start": self.token_start,
            "token_end": self.token_end,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "surface": self.surface,
            "candidates": [item.as_dict() for item in self.candidates],
        }


@dataclass(frozen=True)
class FormUnit:
    unit_ref: str
    kind: str
    surface: str
    normalized: str
    token_start: int
    token_end: int
    char_start: int
    char_end: int
    semantic_ref: str | None = None
    atom_kind: str | None = None
    source_kind: str | None = None
    score: float = 0.0
    features: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "unit_ref": self.unit_ref,
            "kind": self.kind,
            "surface": self.surface,
            "normalized": self.normalized,
            "token_start": self.token_start,
            "token_end": self.token_end,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "semantic_ref": self.semantic_ref,
            "atom_kind": self.atom_kind,
            "source_kind": self.source_kind,
            "score": self.score,
            "features": dict(self.features),
        }


@dataclass(frozen=True)
class GroundingHypothesis:
    hypothesis_ref: str
    normalization_ref: str
    units: tuple[FormUnit, ...]
    score: float
    provenance: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_ref": self.hypothesis_ref,
            "normalization_ref": self.normalization_ref,
            "units": [item.as_dict() for item in self.units],
            "score": self.score,
            "provenance": list(self.provenance),
        }


@dataclass(frozen=True)
class ResolvedFormLattice:
    lattice_ref: str
    raw_text: str
    language: str
    normalization_candidates: tuple[NormalizationCandidate, ...]
    tokens_by_normalization: Mapping[str, tuple[TokenEvidence, ...]]
    spans_by_normalization: Mapping[str, tuple[GroundingSpan, ...]]
    grounding_hypotheses: tuple[GroundingHypothesis, ...]
    safety_flags: tuple[str, ...] = ()
    bounded: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "lattice_ref": self.lattice_ref,
            "raw_text": self.raw_text,
            "language": self.language,
            "normalization_candidates": [item.as_dict() for item in self.normalization_candidates],
            "tokens_by_normalization": {
                key: [item.as_dict() for item in values]
                for key, values in self.tokens_by_normalization.items()
            },
            "spans_by_normalization": {
                key: [item.as_dict() for item in values]
                for key, values in self.spans_by_normalization.items()
            },
            "grounding_hypotheses": [item.as_dict() for item in self.grounding_hypotheses],
            "safety_flags": list(self.safety_flags),
            "bounded": dict(self.bounded),
        }


@dataclass(frozen=True)
class ConstructionEvidence:
    evidence_ref: str
    construction_ref: str
    hypothesis_ref: str
    captures: Mapping[str, Any]
    consumed_unit_refs: tuple[str, ...]
    score: float
    packet_template: Mapping[str, Any]
    remaining_unknowns: tuple[dict[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "evidence_ref": self.evidence_ref,
            "construction_ref": self.construction_ref,
            "hypothesis_ref": self.hypothesis_ref,
            "captures": dict(self.captures),
            "consumed_unit_refs": list(self.consumed_unit_refs),
            "score": self.score,
            "remaining_unknowns": list(self.remaining_unknowns),
        }


class FormPack:
    """Immutable pre-core form/construction data, distinct from semantic authority."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        material = {key: value for key, value in data.items() if key != "pack_hash"}
        computed = hashlib.sha256(canonical(material).encode()).hexdigest()
        if data.get("pack_hash") != computed:
            raise ValueError(f"form pack hash mismatch in {path}")
        self.data = data
        self.hash = computed
        self.language = str(data["language"])
        self.function_forms = {norm_text(item) for item in data.get("function_forms", ())}
        self.discourse_forms = {norm_text(item) for item in data.get("nonblocking_discourse_forms", ())}
        self.contractions = tuple(data.get("contractions", ()))
        self.constructions = tuple(data.get("constructions", ()))


class _TrieNode(dict):
    __slots__ = ("records",)

    def __init__(self):
        super().__init__()
        self.records: list[dict[str, Any]] = []


class SurfaceIndex:
    """Generation-pinned token trie.  No regex is evaluated per stored label."""

    def __init__(self, store, language: str, authority_generation: int | None = None):
        self.store = store
        self.language = language
        self.authority_generation = authority_generation
        self.root = _TrieNode()
        self.record_count = 0
        self._build()

    @staticmethod
    def _tokens(surface: str) -> tuple[str, ...]:
        return tuple(norm_text(match.group()) for match in _WORD.finditer(surface))

    def _insert(self, surface: str, record: Mapping[str, Any]) -> None:
        tokens = self._tokens(surface)
        if not tokens:
            return
        node = self.root
        for token in tokens:
            if token not in node:
                node[token] = _TrieNode()
            node = node[token]
        node.records.append(dict(record))
        self.record_count += 1

    def _build(self) -> None:
        for row in self.store.db.execute(
            "SELECT language,surface,features,bound_ref,weight FROM reference_forms "
            "WHERE language IN (?, 'und') ORDER BY language,surface,weight DESC",
            (self.language,),
        ).fetchall():
            self._insert(
                str(row["surface"]),
                {
                    "source_kind": "reference",
                    "language": str(row["language"]),
                    "surface": str(row["surface"]),
                    "features": json.loads(row["features"]),
                    "bound_ref": row["bound_ref"],
                    "weight": float(row["weight"]),
                },
            )
        for row in self.store.db.execute(
            "SELECT label_ref,target_ref,label_type_ref,surface,language,prior,preferred,context_ref "
            "FROM designation_index WHERE language IN (?, 'und') "
            "ORDER BY language,surface,preferred DESC,prior DESC,target_ref",
            (self.language,),
        ).fetchall():
            self._insert(
                str(row["surface"]),
                {
                    "source_kind": "designation",
                    "language": str(row["language"]),
                    "surface": str(row["surface"]),
                    "semantic_ref": str(row["target_ref"]),
                    "label_type": str(row["label_type_ref"]),
                    "weight": float(row["prior"]) + (0.25 if int(row["preferred"]) else 0.0),
                    "context_ref": row["context_ref"],
                    "label_ref": str(row["label_ref"]),
                },
            )

    def matches(self, tokens: Sequence[TokenEvidence]) -> tuple[tuple[int, int, dict[str, Any]], ...]:
        output: list[tuple[int, int, dict[str, Any]]] = []
        for start in range(len(tokens)):
            node = self.root
            end = start
            while end < len(tokens):
                token = tokens[end].normalized
                child = node.get(token)
                if child is None:
                    break
                node = child
                end += 1
                for record in node.records:
                    output.append((start, end, dict(record)))
        return tuple(output)


class FormProcessor:
    def __init__(
        self,
        store,
        language: str,
        authority_generation: int | None,
        form_pack: FormPack,
        *,
        semantic_function_forms: Iterable[str] = (),
        max_input_chars: int = 8192,
        max_normalizations: int = 8,
        max_grounding_hypotheses: int = 16,
        max_span_candidates: int = 128,
    ):
        if form_pack.language != language:
            raise ValueError(f"form pack language mismatch: {form_pack.language} != {language}")
        self.store = store
        self.language = language
        self.authority_generation = authority_generation
        self.pack = form_pack
        self.max_input_chars = int(max_input_chars)
        self.max_normalizations = int(max_normalizations)
        self.max_grounding_hypotheses = int(max_grounding_hypotheses)
        self.max_span_candidates = int(max_span_candidates)
        self.function_forms = set(form_pack.function_forms) | {
            norm_text(item) for item in semantic_function_forms
        }
        self.index = SurfaceIndex(store, language, authority_generation)
        try:
            self._index_world_revision = int(store.revisions()["world_revision"])
        except Exception:
            self._index_world_revision = None
        self._salience = self._load_salience()

    def _load_salience(self) -> dict[str, float]:
        try:
            current_turn = int(
                self.store.db.execute(
                    "SELECT coalesce(max(last_turn),0) FROM discourse_entities"
                ).fetchone()[0]
            )
            return {
                str(row["atom_ref"]): float(row["salience"])
                * (0.55 ** max(0, current_turn - int(row["last_turn"])))
                for row in self.store.db.execute(
                    "SELECT * FROM discourse_entities ORDER BY last_turn DESC,salience DESC LIMIT 64"
                ).fetchall()
            }
        except Exception:
            return {}

    @staticmethod
    def _identity_map(text: str) -> tuple[SourceSegment, ...]:
        return (SourceSegment(0, len(text), 0, len(text)),)

    @staticmethod
    def _coarse_map(text: str, raw: str) -> tuple[SourceSegment, ...]:
        return (SourceSegment(0, len(text), 0, len(raw)),)

    def _base_normalizations(self, raw: str) -> list[NormalizationCandidate]:
        if len(raw) > self.max_input_chars:
            raise ValueError(f"input exceeds {self.max_input_chars} characters")
        flags: list[TextTransform] = []
        safe = raw.replace("\r\n", "\n").replace("\r", "\n")
        if safe != raw:
            flags.append(TextTransform("line_endings", raw, safe, 0, len(raw)))
        transformed = _CONTROL.sub(" ", safe)
        if transformed != safe:
            flags.append(TextTransform("control_replacement", safe, transformed, 0, len(raw)))
        safe = transformed
        transformed = _ZERO_WIDTH.sub("", safe)
        if transformed != safe:
            flags.append(TextTransform("zero_width_removed", safe, transformed, 0, len(raw)))
        safe = transformed
        transformed = _BIDI_CONTROL.sub("", safe)
        if transformed != safe:
            flags.append(TextTransform("bidi_control_removed", safe, transformed, 0, len(raw)))
        safe = transformed

        candidates: list[NormalizationCandidate] = []

        def add(text: str, score: float, transforms: Iterable[TextTransform]) -> None:
            text = text.strip()
            if not text:
                return
            ref = stable("normalization", raw, text, [item.as_dict() for item in transforms])
            candidates.append(
                NormalizationCandidate(
                    ref,
                    raw,
                    text,
                    score,
                    tuple(transforms),
                    self._identity_map(raw) if text == raw else self._coarse_map(text, raw),
                )
            )

        add(safe, 0.0, flags)
        nfkc = unicodedata.normalize("NFKC", safe)
        nfkc_transforms = list(flags)
        if nfkc != safe:
            nfkc_transforms.append(TextTransform("unicode_nfkc", safe, nfkc, 0, len(raw)))
        add(nfkc, -0.02, nfkc_transforms)
        apostrophe = nfkc.translate(_APOSTROPHES)
        apostrophe_transforms = list(nfkc_transforms)
        if apostrophe != nfkc:
            apostrophe_transforms.append(TextTransform("apostrophe_canonicalization", nfkc, apostrophe, 0, len(raw)))
        add(apostrophe, -0.03, apostrophe_transforms)
        compact = _SPACE.sub(" ", apostrophe).strip()
        compact_transforms = list(apostrophe_transforms)
        if compact != apostrophe:
            compact_transforms.append(TextTransform("whitespace_compaction", apostrophe, compact, 0, len(raw)))
        add(compact, -0.04, compact_transforms)
        return candidates

    def _expand_contractions(self, candidate: NormalizationCandidate) -> list[NormalizationCandidate]:
        output = [candidate]
        lowered = norm_text(candidate.text)
        for rule in self.pack.contractions:
            surface = norm_text(rule.get("surface", ""))
            if not surface or surface not in lowered:
                continue
            pattern = re.compile(r"(?<!\w)" + re.escape(str(rule["surface"])) + r"(?!\w)", re.I | re.UNICODE)
            for index, expansion in enumerate(rule.get("expansions", ())):
                replacement = " ".join(str(token) for token in expansion.get("tokens", ()))
                text, count = pattern.subn(replacement, candidate.text)
                if not count:
                    continue
                transform = TextTransform(
                    "contraction_expansion",
                    candidate.text,
                    text,
                    0,
                    len(candidate.raw_text),
                )
                output.append(
                    NormalizationCandidate(
                        stable("normalization", candidate.raw_text, text, rule.get("surface"), index),
                        candidate.raw_text,
                        text,
                        candidate.score + float(expansion.get("score", -0.05)),
                        candidate.transforms + (transform,),
                        self._coarse_map(text, candidate.raw_text),
                    )
                )
        return output

    def normalizations(self, raw: str) -> tuple[NormalizationCandidate, ...]:
        candidates: list[NormalizationCandidate] = []
        for base in self._base_normalizations(raw):
            candidates.extend(self._expand_contractions(base))
        best: dict[str, NormalizationCandidate] = {}
        for item in candidates:
            key = norm_text(item.text)
            if key not in best or item.score > best[key].score:
                best[key] = item
        return tuple(
            sorted(best.values(), key=lambda item: (-item.score, item.candidate_ref))[
                : self.max_normalizations
            ]
        )

    @staticmethod
    def _raw_span(candidate: NormalizationCandidate, start: int, end: int) -> tuple[int, int]:
        if candidate.text == candidate.raw_text:
            return start, end
        if not candidate.text:
            return 0, len(candidate.raw_text)
        ratio = len(candidate.raw_text) / max(1, len(candidate.text))
        return (
            max(0, min(len(candidate.raw_text), int(start * ratio))),
            max(0, min(len(candidate.raw_text), int(math.ceil(end * ratio)))),
        )

    def tokenize(self, candidate: NormalizationCandidate) -> tuple[TokenEvidence, ...]:
        output = []
        for index, match in enumerate(_WORD.finditer(candidate.text)):
            value = match.group()
            raw_start, raw_end = self._raw_span(candidate, match.start(), match.end())
            category = "word" if any(char.isalnum() or char == "_" for char in value) else "punctuation"
            output.append(
                TokenEvidence(
                    stable("form-token", candidate.candidate_ref, index, value, match.start(), match.end()),
                    value,
                    norm_text(value),
                    match.start(),
                    match.end(),
                    raw_start,
                    raw_end,
                    category,
                )
            )
        return tuple(output)

    def _reference_candidates(self, record: Mapping[str, Any], participant_frame) -> list[tuple[str, float, Mapping[str, Any]]]:
        features = dict(record.get("features", {}))
        resolved = participant_frame.resolve_requirement(features) if participant_frame else None
        if resolved:
            return [(resolved, float(record.get("weight", 1.0)), features)]
        bound_ref = record.get("bound_ref")
        if bound_ref and not features.get("participant_role") and not features.get("person"):
            return [(str(bound_ref), float(record.get("weight", 1.0)), features)]

        required_type = features.get("required_type")
        typed: set[str] = set()
        if required_type:
            typed = {
                fact.args.get("role:instance")
                for fact in self.store.matching_facts(
                    (
                        {
                            "operator": "op:type",
                            "args": {"role:class": required_type},
                            "stance": "support",
                        },
                    ),
                    limit=64,
                )
            }
        candidates = []
        for ref, salience in self._salience.items():
            atom = self.store.atom(ref)
            if not atom:
                continue
            metadata = json.loads(atom["metadata"])
            semantic_features = {
                key: value
                for key, value in features.items()
                if key
                not in {
                    "kind",
                    "required_type",
                    "participant_role",
                    "person",
                    "possessive",
                    "anaphoric",
                }
            }
            if features.get("kind") and atom["kind"] != features["kind"]:
                continue
            if required_type and ref not in typed:
                continue
            if not all(metadata.get(key) == value for key, value in semantic_features.items()):
                continue
            candidates.append((ref, float(record.get("weight", 1.0)) + salience, features))
        return sorted(candidates, key=lambda item: (-item[1], item[0]))[:8]

    def spans(self, candidate: NormalizationCandidate, tokens: Sequence[TokenEvidence], participant_frame) -> tuple[GroundingSpan, ...]:
        grouped: dict[tuple[int, int], list[SurfaceCandidate]] = {}
        records = self.index.matches(tokens)[: self.max_span_candidates]
        for start, end, record in records:
            if start >= end:
                continue
            semantic_candidates: list[tuple[str, float, Mapping[str, Any]]]
            if record["source_kind"] == "designation":
                context_ref = record.get("context_ref")
                if context_ref and participant_frame and context_ref != participant_frame.conversation_ref:
                    continue
                semantic_candidates = [
                    (
                        str(record["semantic_ref"]),
                        float(record.get("weight", 1.0)),
                        {"label_type": record.get("label_type"), "label_ref": record.get("label_ref")},
                    )
                ]
            else:
                semantic_candidates = self._reference_candidates(record, participant_frame)
            for semantic_ref, weight, features in semantic_candidates:
                atom = self.store.atom(semantic_ref)
                if not atom:
                    continue
                surface_value = candidate.text[tokens[start].start : tokens[end - 1].end]
                item = SurfaceCandidate(
                    stable("surface-candidate", record["source_kind"], semantic_ref, start, end, features),
                    str(record["source_kind"]),
                    semantic_ref,
                    str(atom["kind"]),
                    surface_value,
                    str(record.get("language", self.language)),
                    weight,
                    record.get("label_type"),
                    dict(features),
                    record.get("context_ref"),
                )
                grouped.setdefault((start, end), []).append(item)
        output = []
        for (start, end), values in grouped.items():
            values = sorted(values, key=lambda item: (-item.weight, item.semantic_ref))[:8]
            output.append(
                GroundingSpan(
                    stable("grounding-span", candidate.candidate_ref, start, end, [item.candidate_ref for item in values]),
                    start,
                    end,
                    tokens[start].start,
                    tokens[end - 1].end,
                    candidate.text[tokens[start].start : tokens[end - 1].end],
                    tuple(values),
                )
            )
        return tuple(sorted(output, key=lambda item: (item.token_start, -item.token_end, item.span_ref)))

    def _unit_from_token(self, token: TokenEvidence) -> FormUnit:
        normalized = token.normalized
        if token.category == "punctuation":
            kind = "punctuation"
        elif normalized in self.pack.discourse_forms:
            kind = "discourse"
        elif normalized in self.function_forms:
            kind = "function"
        else:
            kind = "unknown"
        return FormUnit(
            stable("form-unit", token.token_ref, kind),
            kind,
            token.surface,
            normalized,
            token_start=-1,
            token_end=-1,
            char_start=token.start,
            char_end=token.end,
            score=0.0,
        )

    def hypotheses(
        self,
        candidate: NormalizationCandidate,
        tokens: Sequence[TokenEvidence],
        spans: Sequence[GroundingSpan],
    ) -> tuple[GroundingHypothesis, ...]:
        by_start: dict[int, list[GroundingSpan]] = {}
        for span in spans:
            by_start.setdefault(span.token_start, []).append(span)

        # (score, next_index, units, provenance)
        beam: list[tuple[float, int, tuple[FormUnit, ...], tuple[str, ...]]] = [(candidate.score, 0, (), (candidate.candidate_ref,))]
        complete: list[tuple[float, tuple[FormUnit, ...], tuple[str, ...]]] = []
        while beam:
            next_beam: list[tuple[float, int, tuple[FormUnit, ...], tuple[str, ...]]] = []
            for score, index, units, provenance in beam:
                if index >= len(tokens):
                    complete.append((score, units, provenance))
                    continue
                token = tokens[index]
                raw_unit = self._unit_from_token(token)
                raw_unit = FormUnit(
                    raw_unit.unit_ref,
                    raw_unit.kind,
                    raw_unit.surface,
                    raw_unit.normalized,
                    index,
                    index + 1,
                    raw_unit.char_start,
                    raw_unit.char_end,
                    score=raw_unit.score,
                    features=raw_unit.features,
                )
                next_beam.append((score - (0.08 if raw_unit.kind == "unknown" else (0.04 if raw_unit.kind == "function" else 0.0)), index + 1, units + (raw_unit,), provenance))
                for span in by_start.get(index, ()):
                    for semantic in span.candidates:
                        unit = FormUnit(
                            stable("form-unit", span.span_ref, semantic.candidate_ref),
                            "anchor",
                            span.surface,
                            norm_text(span.surface),
                            span.token_start,
                            span.token_end,
                            span.char_start,
                            span.char_end,
                            semantic.semantic_ref,
                            semantic.atom_kind,
                            semantic.source_kind,
                            semantic.weight,
                            semantic.features,
                        )
                        next_beam.append(
                            (
                                score + math.log(max(1e-6, semantic.weight)),
                                span.token_end,
                                units + (unit,),
                                provenance + (span.span_ref, semantic.candidate_ref),
                            )
                        )
            next_beam.sort(key=lambda item: (-item[0], canonical([unit.as_dict() for unit in item[2]])))
            beam = next_beam[: self.max_grounding_hypotheses]
            if complete and not beam:
                break
        if not complete:
            complete = [(candidate.score, (), (candidate.candidate_ref,))]
        output = []
        for score, units, provenance in sorted(complete, key=lambda item: -item[0])[: self.max_grounding_hypotheses]:
            output.append(
                GroundingHypothesis(
                    stable("grounding-hypothesis", candidate.candidate_ref, [unit.as_dict() for unit in units]),
                    candidate.candidate_ref,
                    units,
                    score,
                    provenance,
                )
            )
        return tuple(output)

    def resolve(self, raw_text: str, participant_frame) -> ResolvedFormLattice:
        self._salience = self._load_salience()
        try:
            current_revision = int(self.store.revisions()["world_revision"])
        except Exception:
            current_revision = self._index_world_revision
        if current_revision != self._index_world_revision:
            self.index = SurfaceIndex(self.store, self.language, self.authority_generation)
            self._index_world_revision = current_revision
        normalizations = self.normalizations(raw_text)
        tokens_by: dict[str, tuple[TokenEvidence, ...]] = {}
        spans_by: dict[str, tuple[GroundingSpan, ...]] = {}
        hypotheses: list[GroundingHypothesis] = []
        flags = []
        if _CONTROL.search(raw_text):
            flags.append("control_characters")
        if _ZERO_WIDTH.search(raw_text):
            flags.append("zero_width_characters")
        if _BIDI_CONTROL.search(raw_text):
            flags.append("bidi_controls")
        for candidate in normalizations:
            tokens = self.tokenize(candidate)
            spans = self.spans(candidate, tokens, participant_frame)
            tokens_by[candidate.candidate_ref] = tokens
            spans_by[candidate.candidate_ref] = spans
            hypotheses.extend(self.hypotheses(candidate, tokens, spans))
        hypotheses = sorted(hypotheses, key=lambda item: (-item.score, item.hypothesis_ref))[
            : self.max_grounding_hypotheses
        ]
        return ResolvedFormLattice(
            stable("resolved-form-lattice", raw_text, self.language, [item.hypothesis_ref for item in hypotheses]),
            raw_text,
            self.language,
            normalizations,
            tokens_by,
            spans_by,
            tuple(hypotheses),
            tuple(sorted(set(flags))),
            {
                "max_input_chars": self.max_input_chars,
                "max_normalizations": self.max_normalizations,
                "max_grounding_hypotheses": self.max_grounding_hypotheses,
                "max_span_candidates": self.max_span_candidates,
                "surface_index_records": self.index.record_count,
                "regex_per_stored_surface": False,
            },
        )


class ConstructionCandidateGenerator:
    """Stage-5 candidate proposal from reviewed language construction records."""

    def __init__(self, form_pack: FormPack, *, max_matches: int = 32):
        self.pack = form_pack
        self.max_matches = int(max_matches)

    @staticmethod
    def _unit_matches(unit: FormUnit, spec: Mapping[str, Any]) -> bool:
        if "literal" in spec:
            return unit.normalized == norm_text(spec["literal"])
        kind = spec.get("kind")
        if kind and unit.kind != kind:
            return False
        if spec.get("anchor_kind") and not (
            unit.kind == "anchor" and unit.atom_kind == spec["anchor_kind"]
        ):
            return False
        if spec.get("anchor_kinds") and not (
            unit.kind == "anchor" and unit.atom_kind in set(spec["anchor_kinds"])
        ):
            return False
        if spec.get("anchor_ref") and unit.semantic_ref != spec["anchor_ref"]:
            return False
        if spec.get("source_kind") and unit.source_kind != spec["source_kind"]:
            return False
        return True

    @staticmethod
    def _capture_value(units: Sequence[FormUnit], mode: str) -> Any:
        if mode == "ref":
            return units[0].semantic_ref if units else None
        text = " ".join(unit.surface for unit in units)
        text = re.sub(r"\s+([,.;:!?])", r"\1", text).strip()
        if mode == "literal:text":
            return lit(text)
        if mode == "text":
            return text
        if mode == "units":
            return [unit.as_dict() for unit in units]
        return text

    def _match_pattern(
        self,
        units: Sequence[FormUnit],
        pattern: Sequence[Mapping[str, Any]],
        *,
        ignore_kinds: set[str],
        preserve_unknowns: bool = False,
    ) -> list[tuple[dict[str, Any], tuple[str, ...], float]]:
        results: list[tuple[dict[str, Any], tuple[str, ...], float]] = []

        def walk(pi: int, ui: int, captures: dict[str, Any], consumed: tuple[str, ...], score: float) -> None:
            if len(results) >= self.max_matches:
                return
            while ui < len(units) and units[ui].kind in ignore_kinds:
                ui += 1
            if pi >= len(pattern):
                while ui < len(units) and (
                    units[ui].kind in ignore_kinds | {"punctuation"}
                    or (preserve_unknowns and units[ui].kind == "unknown")
                ):
                    ui += 1
                if ui == len(units):
                    results.append((dict(captures), consumed, score))
                return
            if preserve_unknowns and ui < len(units) and units[ui].kind == "unknown":
                walk(pi, ui + 1, captures, consumed, score - 0.22)
            if preserve_unknowns and ui < len(units) and units[ui].kind == "punctuation":
                # Keep punctuation-sensitive matches, but also retain a bounded
                # alternative in which punctuation separates an unresolved span
                # from an otherwise grounded construction.
                walk(pi, ui + 1, captures, consumed, score - 0.04)
            spec = dict(pattern[pi])
            if spec.get("optional"):
                stripped = dict(spec)
                stripped.pop("optional", None)
                walk(pi + 1, ui, captures, consumed, score - 0.02)
                spec = stripped
            if spec.get("open_text"):
                minimum = int(spec.get("min_tokens", 1))
                maximum = min(int(spec.get("max_tokens", 12)), len(units) - ui)
                slot = str(spec.get("slot") or "open")
                mode = str(spec.get("capture", "literal:text"))
                allow_function_forms = bool(spec.get("allow_function_forms"))
                for length in range(maximum, minimum - 1, -1):
                    selected = units[ui : ui + length]
                    if not selected or any(unit.kind == "anchor" and not spec.get("allow_anchors") for unit in selected):
                        continue
                    if any(unit.kind == "punctuation" and not spec.get("allow_punctuation") for unit in selected):
                        continue
                    if not allow_function_forms and any(unit.kind == "function" for unit in selected):
                        continue
                    next_captures = dict(captures)
                    next_captures[slot] = self._capture_value(selected, mode)
                    walk(
                        pi + 1,
                        ui + length,
                        next_captures,
                        consumed + tuple(unit.unit_ref for unit in selected),
                        score - 0.01 * max(0, length - 1),
                    )
                return
            if ui >= len(units) or not self._unit_matches(units[ui], spec):
                return
            next_captures = dict(captures)
            if spec.get("slot"):
                next_captures[str(spec["slot"])] = self._capture_value(
                    (units[ui],), str(spec.get("capture", "ref"))
                )
            walk(
                pi + 1,
                ui + 1,
                next_captures,
                consumed + (units[ui].unit_ref,),
                score + float(spec.get("score", 0.0)),
            )

        walk(0, 0, {}, (), 0.0)
        return results

    @staticmethod
    def _resolve_template(value: Any, captures: Mapping[str, Any], context: Mapping[str, Any]) -> Any:
        if isinstance(value, list):
            return [ConstructionCandidateGenerator._resolve_template(item, captures, context) for item in value]
        if isinstance(value, dict):
            if "$capture" in value:
                return captures.get(str(value["$capture"]))
            if "$context" in value:
                return context.get(str(value["$context"]))
            if "$literal" in value:
                spec = value["$literal"]
                if isinstance(spec, str) and spec.startswith("capture:"):
                    raw = captures.get(spec.split(":", 1)[1])
                    if isinstance(raw, dict) and "literal" in raw:
                        return raw
                    return lit(raw)
                return lit(spec, str(value.get("type", "text")))
            return {
                key: ConstructionCandidateGenerator._resolve_template(item, captures, context)
                for key, item in value.items()
            }
        if isinstance(value, str) and value.startswith("$capture:"):
            return captures.get(value.split(":", 1)[1])
        if isinstance(value, str) and value.startswith("$context:"):
            return context.get(value.split(":", 1)[1])
        return value

    @staticmethod
    def _unknowns(hypothesis: GroundingHypothesis, consumed: set[str]) -> tuple[dict[str, Any], ...]:
        output = []
        for unit in hypothesis.units:
            if unit.unit_ref in consumed or unit.kind != "unknown":
                continue
            output.append(
                {
                    "surface": unit.surface,
                    "normalized": unit.normalized,
                    "char_start": unit.char_start,
                    "char_end": unit.char_end,
                    "unit_ref": unit.unit_ref,
                    "blocking": True,
                }
            )
        return tuple(output)

    def evidence(self, lattice: ResolvedFormLattice, participant_frame) -> tuple[ConstructionEvidence, ...]:
        output = []
        context = {
            "language_literal": lit(lattice.language),
            "script_literal": lit("Latn"),
            "true_literal": lit(True, "bool"),
            "one_float_literal": lit(1.0, "float"),
            "speaker_ref": participant_frame.speaker_ref,
            "addressee_ref": participant_frame.addressee_ref,
            "self_ref": participant_frame.self_ref,
            "conversation_ref": participant_frame.conversation_ref,
        }
        for hypothesis in lattice.grounding_hypotheses:
            for construction in self.pack.constructions:
                ignore = set(construction.get("ignore_kinds", ("discourse",)))
                matches = self._match_pattern(
                    hypothesis.units,
                    tuple(construction.get("pattern", ())),
                    ignore_kinds=ignore,
                    preserve_unknowns=bool(construction.get("preserve_unknowns", False)),
                )
                for captures, consumed, match_score in matches:
                    remaining = self._unknowns(hypothesis, set(consumed))
                    output.append(
                        ConstructionEvidence(
                            stable(
                                "construction-evidence",
                                construction["ref"],
                                hypothesis.hypothesis_ref,
                                captures,
                                consumed,
                            ),
                            str(construction["ref"]),
                            hypothesis.hypothesis_ref,
                            captures,
                            consumed,
                            hypothesis.score + float(construction.get("weight", 1.0)) + match_score,
                            dict(construction["packet"]),
                            remaining,
                        )
                    )
        output.sort(key=lambda item: (-item.score, item.evidence_ref))
        return tuple(output[: self.max_matches])

    def instantiate(self, evidence: ConstructionEvidence, participant_frame, language: str) -> dict[str, Any]:
        context = {
            "language_literal": lit(language),
            "script_literal": lit("Latn"),
            "true_literal": lit(True, "bool"),
            "one_float_literal": lit(1.0, "float"),
            "speaker_ref": participant_frame.speaker_ref,
            "addressee_ref": participant_frame.addressee_ref,
            "self_ref": participant_frame.self_ref,
            "conversation_ref": participant_frame.conversation_ref,
        }
        packet = self._resolve_template(evidence.packet_template, evidence.captures, context)
        if not isinstance(packet, dict):
            raise ValueError("construction packet template did not produce a mapping")
        return packet


def generic_designation_learning_packet(surface: str, language: str, *, label_type: str | None = None) -> dict[str, Any]:
    """Build a first-class exact query for an unresolved language form.

    This is a general learning operation, not a phrase-specific response route.
    The ordinary Stage-10 query engine executes it before clarification is
    considered.
    """
    args: dict[str, Any] = {
        "role:target": "?q0",
        "role:surface": lit(surface),
        "role:language": lit(language),
    }
    if label_type:
        args["role:label_type"] = label_type
    else:
        args["role:label_type"] = "?q1"
    variables = [
        {"ref": "?q0", "filler_kind": "atom", "role_ref": "role:target"},
    ]
    projection = ["?q0"]
    if not label_type:
        variables.append(
            {"ref": "?q1", "filler_kind": "label_type", "role_ref": "role:label_type"}
        )
        projection.append("?q1")
    return {
        "force": "query",
        "apps": [],
        "query": {
            "restrictions": [
                {
                    "operator": "op:designation",
                    "args": args,
                    "stance": "support",
                }
            ],
            "variables": variables,
            "projection": projection,
            "qualifiers": {
                "query_kind": "designation_learning",
                "surface_evidence": surface,
                "language": language,
            },
        },
        "directive": None,
        "describe": None,
        "qualifiers": {
            "learning_operation": "resolve_designation",
            "surface_evidence": surface,
        },
        "modality": "actual",
    }
