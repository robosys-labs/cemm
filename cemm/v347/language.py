"""Language detection and reversible form-lattice analysis.

Language packages own all surface forms.  This module emits evidence only; it
never creates predications, selects referents, writes memory, or chooses output.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any, Iterable, Mapping

from .model import (
    EvidenceRef,
    FormLattice,
    FormSpanCandidate,
    LanguageHypothesis,
    StructureRelationCandidate,
    semantic_hash,
)
from .schema import LanguagePack


_TOKEN_RE = re.compile(r"\w+(?:['’\-]\w+)*|[^\w\s]", re.UNICODE)


@dataclass(frozen=True, slots=True)
class Token:
    token_id: str
    surface: str
    normalized: str
    start: int
    end: int
    index: int


class LanguageDetectionCoordinator:
    def __init__(self, packs: Mapping[str, LanguagePack]):
        self._packs = dict(packs)

    def detect(self, text: str, hint: str | None = None, limit: int = 3) -> tuple[LanguageHypothesis, ...]:
        normalized = " ".join(text.casefold().split())
        tokens = set(item.group(0).casefold() for item in _TOKEN_RE.finditer(normalized))
        scores: dict[str, float] = {}
        for tag, pack in self._packs.items():
            marker_hits = sum(1 for marker in pack.detector_markers if marker.casefold() in tokens)
            lexical_index = pack.lexical_index()
            lexical_hits = sum(1 for token in tokens if token in lexical_index)
            score = 0.05 + marker_hits * 1.5 + lexical_hits * 0.35
            if hint and tag == hint.split("-", 1)[0].casefold():
                score += 1.0
            scores[tag] = score
        if not scores:
            return (LanguageHypothesis("und", 1.0),)
        maximum = max(scores.values())
        exps = {tag: math.exp(score - maximum) for tag, score in scores.items()}
        total = sum(exps.values()) or 1.0
        ranked = sorted(exps, key=exps.get, reverse=True)[:limit]
        return tuple(
            LanguageHypothesis(
                language_tag=tag,
                confidence=exps[tag] / total,
                span_start=0,
                span_end=len(text),
                evidence_refs=(f"language:markers:{tag}",),
            )
            for tag in ranked
        )


class LanguageAnalysisCoordinator:
    def __init__(self, packs: Mapping[str, LanguagePack]):
        self._packs = dict(packs)
        self._detector = LanguageDetectionCoordinator(packs)

    def analyze(self, text: str, *, hint: str | None = None) -> FormLattice:
        language_hypotheses = self._detector.detect(text, hint)
        selected_tags = tuple(
            item.language_tag for item in language_hypotheses
            if item.language_tag in self._packs and item.confidence >= 0.08
        ) or (language_hypotheses[0].language_tag,)
        tokens = self._tokens(text)
        evidence: list[EvidenceRef] = []
        spans: list[FormSpanCandidate] = []
        relations: list[StructureRelationCandidate] = []
        recognized_token_indexes: set[int] = set()
        clause_spans = self._clause_spans(text, tokens)
        spans.extend(clause_spans)

        for tag in selected_tags:
            pack = self._packs[tag]
            lexicon = pack.lexical_index()
            tag_spans, recognized = self._lexical_spans(tokens, tag, lexicon)
            spans.extend(tag_spans)
            recognized_token_indexes.update(recognized)
            pronoun_spans, pronoun_recognized = self._pronoun_spans(tokens, tag, pack.pronouns)
            spans.extend(pronoun_spans)
            recognized_token_indexes.update(pronoun_recognized)
            numeric_spans, numeric_recognized = self._numeric_spans(tokens, tag, pack)
            spans.extend(numeric_spans)
            recognized_token_indexes.update(numeric_recognized)
            structural = self._structure_relations(tokens, clause_spans, spans, tag, pack)
            relations.extend(structural)
            construction_spans = self._construction_evidence(tokens, spans, tag, pack)
            spans.extend(construction_spans)
            for item in (*tag_spans, *pronoun_spans, *numeric_spans, *construction_spans):
                evidence.append(EvidenceRef(
                    evidence_id=f"evidence:{item.span_id}",
                    source_ref=f"language_pack:{tag}:{pack.version}",
                    confidence=item.confidence,
                    span_start=item.start,
                    span_end=item.end,
                    metadata={"candidate_kind": item.candidate_kind},
                ))

        unresolved = []
        for token in tokens:
            if token.index in recognized_token_indexes or not token.surface.isalnum():
                continue
            span_id = f"span:unresolved:{token.index}"
            spans.append(FormSpanCandidate(
                span_id=span_id,
                start=token.start,
                end=token.end,
                surface=token.surface,
                normalized=token.normalized,
                candidate_kind="unresolved",
                confidence=0.35,
                evidence_refs=(f"evidence:{span_id}",),
            ))
            unresolved.append(span_id)

        return FormLattice(
            lattice_id=semantic_hash("lattice", {
                "text": text,
                "languages": [(item.language_tag, item.confidence) for item in language_hypotheses],
            }),
            raw_text=text,
            language_hypotheses=language_hypotheses,
            spans=tuple(_dedupe_spans(spans)),
            structural_relations=tuple(_dedupe_relations(relations)),
            clause_span_refs=tuple(item.span_id for item in clause_spans),
            evidence=tuple(evidence),
            unresolved_span_refs=tuple(unresolved),
            analyzer_versions={tag: self._packs[tag].version for tag in selected_tags if tag in self._packs},
        )

    @staticmethod
    def _tokens(text: str) -> tuple[Token, ...]:
        result = []
        for index, match in enumerate(_TOKEN_RE.finditer(text)):
            result.append(Token(
                token_id=f"token:{index}",
                surface=match.group(0),
                normalized=match.group(0).casefold().replace("’", "'"),
                start=match.start(),
                end=match.end(),
                index=index,
            ))
        return tuple(result)

    @staticmethod
    def _clause_spans(text: str, tokens: tuple[Token, ...]) -> list[FormSpanCandidate]:
        if not tokens:
            return []
        result: list[FormSpanCandidate] = []
        start_token = 0
        clause_number = 0
        boundary_surfaces = {".", "!", "?", ";", ":"}
        for token in tokens:
            if token.surface not in boundary_surfaces:
                continue
            if start_token <= token.index:
                first = tokens[start_token]
                result.append(FormSpanCandidate(
                    span_id=f"clause:{clause_number}",
                    start=first.start,
                    end=token.end,
                    surface=text[first.start:token.end],
                    normalized=" ".join(t.normalized for t in tokens[start_token:token.index + 1]),
                    candidate_kind="clause",
                    confidence=0.9,
                    features={"token_start": start_token, "token_end": token.index + 1},
                ))
                clause_number += 1
            start_token = token.index + 1
        if start_token < len(tokens):
            first = tokens[start_token]
            last = tokens[-1]
            result.append(FormSpanCandidate(
                span_id=f"clause:{clause_number}",
                start=first.start,
                end=last.end,
                surface=text[first.start:last.end],
                normalized=" ".join(t.normalized for t in tokens[start_token:]),
                candidate_kind="clause",
                confidence=0.75,
                features={"token_start": start_token, "token_end": len(tokens)},
            ))
        return result

    @staticmethod
    def _lexical_spans(
        tokens: tuple[Token, ...],
        language_tag: str,
        lexicon: Mapping[str, tuple[Mapping[str, Any], ...]],
    ) -> tuple[list[FormSpanCandidate], set[int]]:
        result: list[FormSpanCandidate] = []
        recognized: set[int] = set()
        max_size = min(6, len(tokens))
        for size in range(max_size, 0, -1):
            for start in range(0, len(tokens) - size + 1):
                group = tokens[start:start + size]
                normalized = " ".join(token.normalized for token in group)
                entries = lexicon.get(normalized, ())
                for number, entry in enumerate(entries):
                    semantic_ref = str(entry.get("semantic_ref", ""))
                    kind = str(entry.get("entry_kind", "lexeme"))
                    span_id = f"span:lex:{language_tag}:{start}:{size}:{number}:{semantic_ref}"
                    result.append(FormSpanCandidate(
                        span_id=span_id,
                        start=group[0].start,
                        end=group[-1].end,
                        surface=" ".join(token.surface for token in group),
                        normalized=normalized,
                        candidate_kind=kind,
                        semantic_refs=(semantic_ref,) if semantic_ref else (),
                        language_tag=language_tag,
                        confidence=float(entry.get("confidence", 0.8)),
                        evidence_refs=(f"evidence:{span_id}",),
                        features={
                            **dict(entry.get("features", {})),
                            "token_start": start,
                            "token_end": start + size,
                        },
                    ))
                    recognized.update(range(start, start + size))
        return result, recognized

    @staticmethod
    def _pronoun_spans(
        tokens: tuple[Token, ...],
        language_tag: str,
        pronouns: Mapping[str, Mapping[str, Any]],
    ) -> tuple[list[FormSpanCandidate], set[int]]:
        result = []
        recognized = set()
        for token in tokens:
            value = pronouns.get(token.normalized)
            if not value:
                continue
            span_id = f"span:pronoun:{language_tag}:{token.index}"
            result.append(FormSpanCandidate(
                span_id=span_id,
                start=token.start,
                end=token.end,
                surface=token.surface,
                normalized=token.normalized,
                candidate_kind="pronoun",
                semantic_refs=tuple(map(str, value.get("candidate_referent_refs", ()))),
                language_tag=language_tag,
                confidence=float(value.get("confidence", 0.9)),
                evidence_refs=(f"evidence:{span_id}",),
                features={**dict(value), "token_start": token.index, "token_end": token.index + 1},
            ))
            recognized.add(token.index)
        return result, recognized

    @staticmethod
    def _numeric_spans(
        tokens: tuple[Token, ...], language_tag: str, pack: LanguagePack
    ) -> tuple[list[FormSpanCandidate], set[int]]:
        result = []
        recognized = set()
        number_words = {str(key): str(value) for key, value in pack.morphology.get("number_words", {}).items()}
        for token in tokens:
            magnitude = None
            if token.normalized.isdigit():
                magnitude = token.normalized
            elif token.normalized in number_words:
                magnitude = number_words[token.normalized]
            if magnitude is None:
                continue
            span_id = f"span:number:{language_tag}:{token.index}"
            result.append(FormSpanCandidate(
                span_id=span_id,
                start=token.start,
                end=token.end,
                surface=token.surface,
                normalized=token.normalized,
                candidate_kind="quantity",
                semantic_refs=(f"quantity:{magnitude}",),
                language_tag=language_tag,
                confidence=0.97,
                evidence_refs=(f"evidence:{span_id}",),
                features={"magnitude": magnitude, "token_start": token.index, "token_end": token.index + 1},
            ))
            recognized.add(token.index)
        return result, recognized

    @staticmethod
    def _structure_relations(
        tokens: tuple[Token, ...],
        clauses: list[FormSpanCandidate],
        spans: list[FormSpanCandidate],
        language_tag: str,
        pack: LanguagePack,
    ) -> list[StructureRelationCandidate]:
        markers = {
            key: {item.casefold() for item in values}
            for key, values in pack.structure_markers.items()
        }
        relations: list[StructureRelationCandidate] = []
        by_token: dict[int, list[FormSpanCandidate]] = {}
        for span in spans:
            start = span.features.get("token_start") if span.features else None
            if isinstance(start, int):
                by_token.setdefault(start, []).append(span)
        for token in tokens:
            kinds = []
            for marker_kind, values in markers.items():
                if token.normalized in values:
                    kinds.append(marker_kind)
            for marker_kind in kinds:
                source = next((clause for clause in clauses if clause.start <= token.start < clause.end), None)
                if source is None:
                    continue
                target = source
                relation_id = f"structure:{language_tag}:{marker_kind}:{token.index}"
                relations.append(StructureRelationCandidate(
                    relation_id=relation_id,
                    relation_kind=marker_kind,
                    source_span_ref=source.span_id,
                    target_span_ref=target.span_id,
                    confidence=0.8,
                    evidence_refs=(f"evidence:{relation_id}",),
                    features={"marker_span": token.token_id, "token_index": token.index},
                ))
        # Connect clauses around explicit conjunction/subordination markers.
        sorted_clauses = sorted(clauses, key=lambda item: item.start)
        for left, right in zip(sorted_clauses, sorted_clauses[1:]):
            between = [token for token in tokens if left.end <= token.start <= right.start]
            marker_kind = None
            for token in between:
                for candidate in ("conjunction", "subordinator", "cause", "condition", "contrast"):
                    if token.normalized in markers.get(candidate, set()):
                        marker_kind = candidate
                        break
                if marker_kind:
                    break
            if marker_kind:
                relations.append(StructureRelationCandidate(
                    relation_id=f"structure:{language_tag}:{marker_kind}:{left.span_id}:{right.span_id}",
                    relation_kind=marker_kind,
                    source_span_ref=left.span_id,
                    target_span_ref=right.span_id,
                    confidence=0.75,
                    evidence_refs=(f"evidence:clause-link:{left.span_id}:{right.span_id}",),
                ))
        return relations

    @staticmethod
    def _construction_evidence(
        tokens: tuple[Token, ...],
        existing_spans: list[FormSpanCandidate],
        language_tag: str,
        pack: LanguagePack,
    ) -> list[FormSpanCandidate]:
        """Match abstract feature sequences, never final semantic predications."""
        result: list[FormSpanCandidate] = []
        classes_by_token: dict[int, set[str]] = {}
        for span in existing_spans:
            start = span.features.get("token_start") if span.features else None
            end = span.features.get("token_end") if span.features else None
            if not isinstance(start, int) or not isinstance(end, int):
                continue
            classes = {span.candidate_kind, *span.semantic_refs}
            for index in range(start, end):
                classes_by_token.setdefault(index, set()).update(classes)
                grammatical = span.features.get("grammatical_class")
                if grammatical:
                    classes_by_token[index].add(str(grammatical))
        for construction in pack.constructions:
            sequence = tuple(map(str, construction.get("sequence", ())))
            if not sequence:
                continue
            for start in range(len(tokens)):
                cursor = start
                matched_indexes: list[int] = []
                for required_class in sequence:
                    while cursor < len(tokens) and required_class not in classes_by_token.get(cursor, set()):
                        if construction.get("allow_gaps", False):
                            cursor += 1
                        else:
                            break
                    if cursor >= len(tokens) or required_class not in classes_by_token.get(cursor, set()):
                        matched_indexes = []
                        break
                    matched_indexes.append(cursor)
                    cursor += 1
                if not matched_indexes:
                    continue
                first = tokens[matched_indexes[0]]
                last = tokens[matched_indexes[-1]]
                identifier = str(construction["construction_id"])
                span_id = f"span:construction:{language_tag}:{identifier}:{start}"
                result.append(FormSpanCandidate(
                    span_id=span_id,
                    start=first.start,
                    end=last.end,
                    surface=" ".join(token.surface for token in tokens[matched_indexes[0]:matched_indexes[-1] + 1]),
                    normalized=" ".join(token.normalized for token in tokens[matched_indexes[0]:matched_indexes[-1] + 1]),
                    candidate_kind="construction_evidence",
                    semantic_refs=(),
                    language_tag=language_tag,
                    confidence=float(construction.get("confidence", 0.65)),
                    evidence_refs=(f"evidence:{span_id}",),
                    features={
                        "construction_id": identifier,
                        "semantic_hint": construction.get("semantic_hint", ""),
                        "token_start": matched_indexes[0],
                        "token_end": matched_indexes[-1] + 1,
                        "matched_classes": sequence,
                    },
                ))
        return result


def primary_language(lattice: FormLattice, fallback: str = "und") -> str:
    return lattice.language_hypotheses[0].language_tag if lattice.language_hypotheses else fallback


def spans_for_semantic_ref(lattice: FormLattice, semantic_ref: str) -> tuple[FormSpanCandidate, ...]:
    return tuple(span for span in lattice.spans if semantic_ref in span.semantic_refs)


def spans_in_clause(lattice: FormLattice, clause_ref: str) -> tuple[FormSpanCandidate, ...]:
    clause = next((span for span in lattice.spans if span.span_id == clause_ref), None)
    if clause is None:
        return ()
    return tuple(
        span for span in lattice.spans
        if span.span_id != clause_ref and clause.start <= span.start and span.end <= clause.end
    )


def _dedupe_spans(items: Iterable[FormSpanCandidate]) -> list[FormSpanCandidate]:
    result: dict[tuple[Any, ...], FormSpanCandidate] = {}
    for item in items:
        key = (item.start, item.end, item.candidate_kind, item.semantic_refs, item.language_tag)
        existing = result.get(key)
        if existing is None or item.confidence > existing.confidence:
            result[key] = item
    return sorted(result.values(), key=lambda item: (item.start, item.end, item.candidate_kind, -item.confidence))


def _dedupe_relations(items: Iterable[StructureRelationCandidate]) -> list[StructureRelationCandidate]:
    result: dict[tuple[str, str, str], StructureRelationCandidate] = {}
    for item in items:
        key = (item.relation_kind, item.source_span_ref, item.target_span_ref)
        existing = result.get(key)
        if existing is None or item.confidence > existing.confidence:
            result[key] = item
    return sorted(result.values(), key=lambda item: item.relation_id)
