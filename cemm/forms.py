"""Bounded reversible pre-core form processing for CEMM v1.

This module is deliberately outside semantic authority.  It preserves raw
input, proposes normalization/token/span alternatives, and builds bounded
form/grounding hypotheses with provenance.  It never commits, creates semantic
atoms, decides world truth, or directly selects a discourse act.

Language-specific atomic feature schemas may propose exact semantic packets at
Stage 5. The schemas never inspect surface strings; the exact compiler, semantic
coverage policy and settler remain authoritative.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import math
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol, Sequence

from cemm.model import canonical, lit, norm_text, stable, surface
from cemm.form_algebra import AtomicConstructionAssembler, AtomicSchemaMatcher
from cemm.semantic_contributions import SemanticAffordanceIndex

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
class FormSpanProposal:
    proposal_ref: str
    token_start: int
    token_end: int
    char_start: int
    char_end: int
    surface: str
    provider_ref: str
    score: float
    features: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "proposal_ref": self.proposal_ref,
            "token_start": self.token_start,
            "token_end": self.token_end,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "surface": self.surface,
            "provider_ref": self.provider_ref,
            "score": self.score,
            "features": dict(self.features),
        }


class SpanProposalProvider(Protocol):
    provider_ref: str

    def propose(
        self, candidate: NormalizationCandidate, tokens: Sequence[TokenEvidence]
    ) -> Sequence[FormSpanProposal]: ...


class QuotedSpanProvider:
    """Propose exact bounded literal spans enclosed by explicit quote tokens."""

    provider_ref = "quoted_span"
    _PAIRS = {
        '"': '"', "'": "'", "“": "”", "‘": "’", "«": "»", "‹": "›"
    }

    def propose(
        self, candidate: NormalizationCandidate, tokens: Sequence[TokenEvidence]
    ) -> tuple[FormSpanProposal, ...]:
        output: list[FormSpanProposal] = []
        index = 0
        while index < len(tokens):
            opener = tokens[index].surface
            closer = self._PAIRS.get(opener)
            if closer is None:
                index += 1
                continue
            end = index + 1
            while end < len(tokens) and tokens[end].surface != closer:
                end += 1
            if end >= len(tokens) or end == index + 1:
                index += 1
                continue
            content_start, content_end = index + 1, end
            if content_end - content_start > 12:
                index = end + 1
                continue
            surface_value = candidate.text[
                tokens[content_start].start : tokens[content_end - 1].end
            ]
            output.append(
                FormSpanProposal(
                    stable(
                        "form-span-proposal", self.provider_ref,
                        candidate.candidate_ref, content_start, content_end, surface_value,
                    ),
                    content_start, content_end,
                    tokens[content_start].start, tokens[content_end - 1].end,
                    surface_value, self.provider_ref, 0.65,
                    {
                        "span_type": "quoted",
                        "quoted": True,
                        "literal_evidence": True,
                        "proposal_only": True,
                    },
                )
            )
            index = end + 1
        return tuple(output)


class HeuristicProperNameProvider:
    """Bounded fallback span proposal provider.

    It proposes only token boundaries and coarse entity-type evidence. It never
    creates a semantic atom or commits an identity. A production NER provider can
    be injected through the same interface without changing the core loop.
    """

    provider_ref = "named_entity_proposal"

    def __init__(
        self,
        max_tokens: int = 8,
        *,
        protected_forms: Iterable[str] = (),
    ):
        self.max_tokens = int(max_tokens)
        # The proposal provider is downstream of reviewed lexical evidence.  A
        # surface already licensed as a grammatical/reference form must not be
        # reinterpreted as a proper-name proposal merely because it is
        # sentence-initial or uppercase (for example, first-person "I").
        self.protected_forms = frozenset(norm_text(value) for value in protected_forms)

    def _name_like(self, token: TokenEvidence) -> bool:
        value = token.surface
        return bool(
            token.category == "word"
            and value
            and token.normalized not in self.protected_forms
            and (value[0].isupper() or (len(value) > 1 and value.isupper()))
        )

    def propose(
        self, candidate: NormalizationCandidate, tokens: Sequence[TokenEvidence]
    ) -> Sequence[FormSpanProposal]:
        output: list[FormSpanProposal] = []
        index = 0
        while index < len(tokens):
            if not self._name_like(tokens[index]):
                index += 1
                continue
            end = index + 1
            while (
                end < len(tokens)
                and end - index < self.max_tokens
                and self._name_like(tokens[end])
            ):
                end += 1
            # Structural lexical forms have already been excluded by
            # ``protected_forms``.  A remaining single title-cased token is a
            # valid bounded name proposal (for example, "Opata"); it is still
            # proposal-only and becomes semantic only if an atomic schema and
            # complete coverage independently license it.
            surface_value = candidate.text[tokens[index].start : tokens[end - 1].end]
            output.append(
                FormSpanProposal(
                    stable(
                        "form-span-proposal",
                        self.provider_ref,
                        candidate.candidate_ref,
                        index,
                        end,
                        surface_value,
                    ),
                    index,
                    end,
                    tokens[index].start,
                    tokens[end - 1].end,
                    surface_value,
                    self.provider_ref,
                    0.35 + 0.05 * min(4, end - index),
                    {
                        "span_type": "named_entity",
                        "entity_type_candidates": ["person", "organization", "entity"],
                        "proposal_only": True,
                    },
                )
            )
            index = end
        return tuple(output)


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

    def clause_surfaces(self) -> tuple[str, ...]:
        """Return punctuation-bounded clause surfaces from token evidence.

        Clause segmentation belongs to pre-core form processing. It uses token
        categories and punctuation evidence, not a semantic phrase recognizer.
        """
        normalization_ref = (
            self.grounding_hypotheses[0].normalization_ref
            if self.grounding_hypotheses
            else (self.normalization_candidates[0].candidate_ref if self.normalization_candidates else None)
        )
        tokens = tuple(self.tokens_by_normalization.get(normalization_ref, ()))
        if not tokens:
            text = self.raw_text.strip()
            return (text,) if text else ()
        clauses: list[str] = []
        current: list[str] = []
        for token in tokens:
            current.append(token.surface)
            if token.category == "punctuation" and token.surface in {".", "!", "?"}:
                text = surface(current).strip()
                if text:
                    clauses.append(text)
                current = []
        text = surface(current).strip()
        if text:
            clauses.append(text)
        return tuple(clauses)

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
    coverage: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "evidence_ref": self.evidence_ref,
            "construction_ref": self.construction_ref,
            "hypothesis_ref": self.hypothesis_ref,
            "captures": dict(self.captures),
            "consumed_unit_refs": list(self.consumed_unit_refs),
            "score": self.score,
            "coverage": dict(self.coverage),
        }


class FormPack:
    """Immutable pre-core lexical-feature and atomic-schema artifact."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        material = {key: value for key, value in data.items() if key != "pack_hash"}
        computed = hashlib.sha256(canonical(material).encode()).hexdigest()
        if data.get("pack_hash") != computed:
            raise ValueError(f"form pack hash mismatch in {path}")
        if data.get("constructions"):
            raise ValueError("legacy phrase constructions are forbidden by runtime contract")
        receipt = data.get("training_receipt")
        if not isinstance(receipt, Mapping):
            raise ValueError("form pack lacks computed training receipt")
        algebra_version = int(data.get("feature_algebra_version", -1))
        if algebra_version != 7 or int(receipt.get("feature_algebra_version", -1)) != algebra_version:
            raise ValueError("form pack feature-algebra ABI mismatch")
        if int(receipt.get("receipt_version", -1)) != 7:
            raise ValueError("unsupported form-pack receipt version")
        if not receipt.get("graph_matcher") or receipt.get("total_order_matcher") is not False:
            raise ValueError("form pack was not verified by the v7 recursive graph matcher")
        schemas = tuple(data.get("schemas", ()))
        if int(receipt.get("family_count", -1)) != len(schemas):
            raise ValueError("form-pack family count receipt mismatch")
        if float(receipt.get("annotated_replay_coverage", 0.0)) != 1.0:
            raise ValueError("form-pack annotated replay is incomplete")
        if int(receipt.get("surface_matcher_key_count", -1)) != 0 or int(receipt.get("regex_condition_count", -1)) != 0:
            raise ValueError("form-pack contains forbidden matcher conditions")
        schema_hashes = dict(receipt.get("schema_hashes", {}))
        actual_hashes = {
            str(schema.get("ref")): hashlib.sha256(canonical(schema).encode()).hexdigest()
            for schema in schemas
        }
        if schema_hashes != actual_hashes:
            raise ValueError("form-pack schema hash receipt mismatch")
        collision_rows = tuple(receipt.get("cross_family_collision_matrix", ()))
        if len(collision_rows) != int(receipt.get("example_count", -1)) or any(
            row.get("intended_family") not in row.get("executable_families", ())
            for row in collision_rows
        ):
            raise ValueError("form-pack collision receipt is invalid")
        if any(not item.get("blocked") for item in receipt.get("critical_slot_mutations", ())):
            raise ValueError("form-pack critical-slot mutation receipt is invalid")
        if any(not item.get("blocked") for item in receipt.get("negative_probes", ())):
            raise ValueError("form-pack negative-probe receipt is invalid")
        AtomicSchemaMatcher(schemas, max_matches=1)
        self.data = data
        self.hash = computed
        self.language = str(data["language"])
        self.function_forms = {norm_text(item) for item in data.get("function_forms", ())}
        self.discourse_forms = {norm_text(item) for item in data.get("nonblocking_discourse_forms", ())}
        self.contractions = tuple(data.get("contractions", ()))
        self.schemas = schemas
        self.training_receipt = dict(receipt)
        if not self.schemas:
            raise ValueError("form pack requires trained atomic schemas")
        feature_index: dict[str, list[dict[str, Any]]] = {}
        for record in data.get("lexemes", ()):
            features = dict(record.get("features", {}))
            for form in record.get("forms", ()):
                feature_index.setdefault(norm_text(str(form)), []).append(features)
        self._feature_index = {
            key: tuple(values) for key, values in feature_index.items()
        }
        # Lexical forms carrying structural grammar/reference evidence are
        # protected from heuristic named-entity proposals.  This is derived
        # from feature types, not an English pronoun word list, so equivalent
        # language packs receive the same precedence rule.
        structural_keys = {
            "participant_role",
            "person",
            "discourse_force",
            "predicate",
            "copular",
            "auxiliary",
            "property_ref",
            "semantic_port",
            "anaphoric",
            "demonstrative",
        }
        structural_categories = {
            "reference",
            "interrogative",
            "auxiliary",
            "verb",
            "property_marker",
            "emphasis",
            "contrast",
            "adposition",
        }
        self.named_entity_blocked_forms = frozenset(
            form
            for form, alternatives in self._feature_index.items()
            if any(
                structural_keys.intersection(features)
                or features.get("category") in structural_categories
                for features in alternatives
            )
        )

    def feature_alternatives_for(self, normalized: str) -> tuple[dict[str, Any], ...]:
        records = self._feature_index.get(norm_text(normalized), ())
        unique = {canonical(record): dict(record) for record in records}
        return tuple(unique[key] for key in sorted(unique))

    def features_for(self, normalized: str) -> dict[str, Any]:
        """Diagnostic union only; runtime hypotheses use alternatives separately."""
        merged: dict[str, Any] = {}
        for record in self.feature_alternatives_for(normalized):
            for key, value in record.items():
                if key not in merged:
                    merged[key] = value
                elif canonical(merged[key]) != canonical(value):
                    prior = merged[key]
                    values = list(prior) if isinstance(prior, tuple) else [prior]
                    if all(canonical(value) != canonical(item) for item in values):
                        values.append(value)
                    merged[key] = tuple(values)
        return merged


class _TrieNode(dict):
    __slots__ = ("records",)

    def __init__(self):
        super().__init__()
        self.records: list[dict[str, Any]] = []


class SurfaceIndex:
    """World-revision-pinned token trie; no regex runs per stored label."""

    def __init__(
        self, store, language: str, authority_generation: int | None = None,
        world_revision: int | None = None,
    ):
        self.store = store
        self.language = language
        self.authority_generation = authority_generation
        self.world_revision = int(
            store.revisions()["world_revision"] if world_revision is None else world_revision
        )
        self.root = _TrieNode()
        self.record_count = 0
        self._record_signatures: list[str] = []
        self._build()
        self.snapshot_ref = stable(
            "surface-index", self.language, self.authority_generation,
            self.world_revision, sorted(self._record_signatures),
        )

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
        normalized_record = dict(record)
        node.records.append(normalized_record)
        self._record_signatures.append(canonical((tokens, normalized_record)))
        self.record_count += 1

    def _build(self) -> None:
        # Contextual indexicals are grounded from the participant frame and must
        # never be shadowed by stable designation entries for the same surface.
        pronoun_surfaces: set[str] = set()
        for row in self.store.db.execute(
            "SELECT surface,features FROM reference_forms WHERE language IN (?, 'und')",
            (self.language,),
        ).fetchall():
            features = json.loads(row["features"])
            if "participant_role" in features or "person" in features:
                pronoun_surfaces.add(norm_text(str(row["surface"])))
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
        query = (
            "SELECT label_ref,target_ref,label_type_ref,surface,language,prior,preferred,context_ref "
            "FROM designation_index WHERE language IN (?, 'und') "
            "ORDER BY language,surface,preferred DESC,prior DESC,target_ref"
        )
        for row in self.store.db.execute(query, (self.language,)).fetchall():
            if norm_text(str(row["surface"])) in pronoun_surfaces:
                continue
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
        span_providers: Sequence[SpanProposalProvider] | None = None,
    ):
        if form_pack.language != language:
            raise ValueError(f"form pack language mismatch: {form_pack.language} != {language}")
        self.store = store
        self.language = language
        self.authority_generation = authority_generation
        self.pack = form_pack
        self.affordances = SemanticAffordanceIndex(
            store, authority_generation, max_profiles_per_target=4
        )
        self.max_input_chars = int(max_input_chars)
        self.max_normalizations = int(max_normalizations)
        self.max_grounding_hypotheses = int(max_grounding_hypotheses)
        self.max_span_candidates = int(max_span_candidates)
        self.span_providers = tuple(
            span_providers
            or (
                QuotedSpanProvider(),
                HeuristicProperNameProvider(
                    protected_forms=form_pack.named_entity_blocked_forms
                ),
            )
        )
        required_providers = set(self.pack.training_receipt.get("required_span_providers", ()))
        actual_providers = {
            str(getattr(provider, "provider_ref", type(provider).__name__))
            for provider in self.span_providers
        }
        missing_providers = required_providers - actual_providers
        if missing_providers:
            raise ValueError(
                f"form processor lacks required span providers: {sorted(missing_providers)}"
            )
        self.function_forms = set(form_pack.function_forms) | {
            norm_text(item) for item in semantic_function_forms
        }
        self._index_world_revision = int(store.revisions()["world_revision"])
        self.index = SurfaceIndex(
            store, language, authority_generation, self._index_world_revision
        )
        self._salience = self._load_salience()

    def _load_salience(self) -> dict[str, float]:
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

    @staticmethod
    def _identity_map(text: str) -> tuple[SourceSegment, ...]:
        return (SourceSegment(0, len(text), 0, len(text)),)

    @staticmethod
    def _aligned_map(text: str, raw: str) -> tuple[SourceSegment, ...]:
        if text == raw:
            return FormProcessor._identity_map(raw)
        matcher = difflib.SequenceMatcher(a=raw, b=text, autojunk=False)
        output: list[SourceSegment] = []
        for tag, raw_start, raw_end, out_start, out_end in matcher.get_opcodes():
            if out_start == out_end:
                continue
            if tag == "equal":
                output.append(SourceSegment(out_start, out_end, raw_start, raw_end))
            else:
                # Replaced/inserted output retains provenance to the precise raw
                # segment that caused it; no global length-ratio approximation.
                output.append(SourceSegment(out_start, out_end, raw_start, raw_end))
        return tuple(output) or (SourceSegment(0, len(text), 0, len(raw)),)

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
                    self._aligned_map(text, raw),
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
        """Compose contraction alternatives with a bounded deterministic beam."""
        best: dict[str, NormalizationCandidate] = {norm_text(candidate.text): candidate}
        frontier = [candidate]
        while frontier and len(best) < self.max_normalizations * 4:
            current = frontier.pop(0)
            for rule in self.pack.contractions:
                surface_key = norm_text(rule.get("surface", ""))
                if not surface_key or surface_key not in norm_text(current.text):
                    continue
                pattern = re.compile(
                    r"(?<!\w)" + re.escape(str(rule["surface"])) + r"(?!\w)",
                    re.I | re.UNICODE,
                )
                for index, expansion in enumerate(rule.get("expansions", ())):
                    replacement = " ".join(str(token) for token in expansion.get("tokens", ()))
                    text, count = pattern.subn(replacement, current.text, count=1)
                    if not count:
                        continue
                    transform = TextTransform(
                        "contraction_expansion",
                        current.text,
                        text,
                        0,
                        len(current.raw_text),
                    )
                    item = NormalizationCandidate(
                        stable(
                            "normalization",
                            current.raw_text,
                            text,
                            rule.get("surface"),
                            index,
                            [x.as_dict() for x in current.transforms],
                        ),
                        current.raw_text,
                        text,
                        current.score + float(expansion.get("score", -0.05)),
                        current.transforms + (transform,),
                        self._aligned_map(text, current.raw_text),
                    )
                    key = norm_text(text)
                    previous = best.get(key)
                    if previous is None or item.score > previous.score:
                        best[key] = item
                        frontier.append(item)
        return list(best.values())

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
        overlapping = [
            segment
            for segment in candidate.source_map
            if segment.output_end > start and segment.output_start < end
        ]
        if not overlapping:
            return 0, len(candidate.raw_text)
        return (
            max(0, min(segment.raw_start for segment in overlapping)),
            min(len(candidate.raw_text), max(segment.raw_end for segment in overlapping)),
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
                semantic_ref = str(record["semantic_ref"])
                base_features = {
                    "label_type": record.get("label_type"),
                    "label_ref": record.get("label_ref"),
                }
                semantic_candidates = [
                    (
                        semantic_ref,
                        float(record.get("weight", 1.0)) + float(profile.score),
                        {**base_features, **profile.as_features()},
                    )
                    for profile in self.affordances.profiles_for(semantic_ref)
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

    def _unit_options_from_token(self, token: TokenEvidence) -> tuple[FormUnit, ...]:
        normalized = token.normalized
        alternatives = self.pack.feature_alternatives_for(normalized)
        if token.category == "punctuation":
            # Punctuation remains pre-core lexical evidence.  A language pack may
            # mark an interrogative boundary as force evidence; the semantic graph
            # matcher never sees the literal punctuation surface.
            alternatives = alternatives or ({"boundary_only": True},)
            kind = "punctuation"
        elif normalized in self.pack.discourse_forms:
            alternatives = alternatives or ({},)
            kind = "discourse"
        elif alternatives and all(
            bool(dict(item).get("open_class")) for item in alternatives
        ):
            # Morphology without a designation is evidence, not semantic identity.
            # Keep the unit open/critical until a designation target contributes
            # one or more semantic affordance profiles.
            kind = "unknown"
        elif normalized in self.function_forms or alternatives:
            alternatives = alternatives or ({},)
            kind = "function"
        else:
            alternatives = ({},)
            kind = "unknown"
        output = []
        for features in alternatives:
            actual = dict(features)
            if kind == "discourse":
                actual["discourse_marker"] = True
            output.append(
                FormUnit(
                    stable("form-unit", token.token_ref, kind, actual),
                    kind,
                    token.surface,
                    normalized,
                    token_start=-1,
                    token_end=-1,
                    char_start=token.start,
                    char_end=token.end,
                    score=0.0,
                    features=actual,
                )
            )
        return tuple(output)

    def _span_proposals(
        self, candidate: NormalizationCandidate, tokens: Sequence[TokenEvidence]
    ) -> tuple[FormSpanProposal, ...]:
        proposals: dict[str, FormSpanProposal] = {}
        for provider in self.span_providers:
            for item in provider.propose(candidate, tokens):
                if not (0 <= item.token_start < item.token_end <= len(tokens)):
                    continue
                prior = proposals.get(item.proposal_ref)
                if prior is None or item.score > prior.score:
                    proposals[item.proposal_ref] = item
        return tuple(
            sorted(
                proposals.values(),
                key=lambda item: (item.token_start, -item.token_end, -item.score, item.proposal_ref),
            )[: self.max_span_candidates]
        )

    def hypotheses(
        self,
        candidate: NormalizationCandidate,
        tokens: Sequence[TokenEvidence],
        spans: Sequence[GroundingSpan],
        form_spans: Sequence[FormSpanProposal] = (),
    ) -> tuple[GroundingHypothesis, ...]:
        by_start: dict[int, list[GroundingSpan]] = {}
        for span in spans:
            by_start.setdefault(span.token_start, []).append(span)
        form_by_start: dict[int, list[FormSpanProposal]] = {}
        for span in form_spans:
            form_by_start.setdefault(span.token_start, []).append(span)

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
                participant_spans = []
                for span in by_start.get(index, ()):
                    if span.token_end != index + 1:
                        continue
                    for semantic in span.candidates:
                        features = dict(semantic.features or {})
                        if features.get("participant_role") and semantic.semantic_ref:
                            participant_spans.append(semantic)
                participant_refs = {item.semantic_ref for item in participant_spans}
                deterministic_participant = len(participant_refs) == 1

                for raw in self._unit_options_from_token(token):
                    # A first/second-person participant-relative form resolved by
                    # the active ParticipantFrame is not a genuine ambiguity.  Do
                    # not retain a lexical-only unresolved twin of the same token.
                    if (
                        deterministic_participant
                        and raw.features.get("participant_role")
                    ):
                        continue
                    raw_unit = FormUnit(
                        raw.unit_ref,
                        raw.kind,
                        raw.surface,
                        raw.normalized,
                        index,
                        index + 1,
                        raw.char_start,
                        raw.char_end,
                        score=raw.score,
                        features=raw.features,
                    )
                    next_beam.append(
                        (
                            score - (0.08 if raw_unit.kind == "unknown" else 0.0),
                            index + 1,
                            units + (raw_unit,),
                            provenance + (raw_unit.unit_ref,),
                        )
                    )
                for proposal in form_by_start.get(index, ()):
                    unit = FormUnit(
                        stable("form-unit", proposal.proposal_ref),
                        "span",
                        proposal.surface,
                        norm_text(proposal.surface),
                        proposal.token_start,
                        proposal.token_end,
                        proposal.char_start,
                        proposal.char_end,
                        score=proposal.score,
                        source_kind=proposal.provider_ref,
                        features=dict(proposal.features),
                    )
                    next_beam.append(
                        (
                            score + proposal.score,
                            proposal.token_end,
                            units + (unit,),
                            provenance + (proposal.proposal_ref,),
                        )
                    )
                for span in by_start.get(index, ()):
                    for semantic in span.candidates:
                        lexical_alternatives = self.pack.feature_alternatives_for(
                            norm_text(span.surface)
                        ) or ({},)
                        for lexical_features in lexical_alternatives:
                            combined = {**dict(lexical_features), **dict(semantic.features)}
                            unit = FormUnit(
                                stable(
                                    "form-unit",
                                    span.span_ref,
                                    semantic.candidate_ref,
                                    combined,
                                ),
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
                                combined,
                            )
                            # A resolved participant/reference anchor is strictly
                            # more informative than an otherwise identical lexical
                            # feature-only unit.  Keep both hypotheses, but break
                            # the former zero-score tie in favour of the grounded
                            # referent.  Designation/content anchors do not receive
                            # this bonus and continue to compete by their observed
                            # evidence weight.
                            grounding_bonus = (
                                0.08
                                if combined.get("category") == "reference"
                                and combined.get("participant_role")
                                and semantic.source_kind in {"reference", "reference_form"}
                                else 0.0
                            )
                            next_beam.append(
                                (
                                    score
                                    + math.log(max(1e-6, semantic.weight))
                                    + grounding_bonus,
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
            return ()
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
        current_revision = int(self.store.revisions()["world_revision"])
        if current_revision != self._index_world_revision:
            self.index = SurfaceIndex(
                self.store, self.language, self.authority_generation, current_revision
            )
            self.affordances = SemanticAffordanceIndex(
                self.store, self.authority_generation, max_profiles_per_target=4
            )
            self._index_world_revision = current_revision
        normalizations = self.normalizations(raw_text)
        tokens_by: dict[str, tuple[TokenEvidence, ...]] = {}
        spans_by: dict[str, tuple[GroundingSpan, ...]] = {}
        hypotheses: list[GroundingHypothesis] = []
        hypotheses_by_normalization: dict[str, tuple[GroundingHypothesis, ...]] = {}
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
            form_spans = self._span_proposals(candidate, tokens)
            tokens_by[candidate.candidate_ref] = tokens
            spans_by[candidate.candidate_ref] = spans
            candidate_hypotheses = self.hypotheses(candidate, tokens, spans, form_spans)
            hypotheses_by_normalization[candidate.candidate_ref] = candidate_hypotheses
            hypotheses.extend(candidate_hypotheses)

        # Preserve both normalization diversity and a structural lexical
        # backbone before global score truncation.  In a populated store, many
        # designation candidates for words such as "name" can otherwise crowd
        # out the hypothesis that retains its reviewed grammatical/property
        # features.  For each reversible normalization we reserve:
        #   1. the ordinary highest-evidence hypothesis; and
        #   2. the best structurally compositional hypothesis, when distinct.
        # This is evidence-class fairness, not phrase routing: ranking uses only
        # unit kinds, reviewed features and grounding provenance.
        def structural_rank(hypothesis: GroundingHypothesis):
            participant_anchors = 0
            structural_units = 0
            unresolved_participant_refs = 0
            designation_anchors = 0
            proposal_spans = 0
            unknowns = 0
            for unit in hypothesis.units:
                features = dict(unit.features or {})
                if unit.kind == "anchor":
                    if (
                        features.get("category") == "reference"
                        and features.get("participant_role")
                        and unit.source_kind in {"reference", "reference_form"}
                    ):
                        participant_anchors += 1
                    elif unit.source_kind == "designation":
                        designation_anchors += 1
                if unit.kind == "function" and features.get("category") in {
                    "interrogative",
                    "auxiliary",
                    "verb",
                    "reference",
                    "property_marker",
                    "emphasis",
                    "relation_marker",
                    "type_marker",
                }:
                    structural_units += 1
                    if (
                        features.get("category") == "reference"
                        and features.get("participant_role")
                    ):
                        unresolved_participant_refs += 1
                if unit.kind == "span" and features.get("proposal_only"):
                    proposal_spans += 1
                if unit.kind == "unknown":
                    unknowns += 1
            return (
                participant_anchors,
                structural_units,
                proposal_spans,
                -unresolved_participant_refs,
                -designation_anchors,
                -unknowns,
                hypothesis.score,
                hypothesis.hypothesis_ref,
            )

        representatives: list[GroundingHypothesis] = []
        for candidate in normalizations:
            values = hypotheses_by_normalization.get(candidate.candidate_ref, ())
            if not values:
                continue
            top = values[0]
            structural = max(values, key=structural_rank)
            representatives.append(top)
            if structural.hypothesis_ref != top.hypothesis_ref:
                representatives.append(structural)

        # Deduplicate while preserving deterministic normalization order, then
        # fill any unused slots by global evidence rank.
        reserved: list[GroundingHypothesis] = []
        reserved_refs: set[str] = set()
        for item in representatives:
            if item.hypothesis_ref in reserved_refs:
                continue
            if len(reserved) >= self.max_grounding_hypotheses:
                break
            reserved.append(item)
            reserved_refs.add(item.hypothesis_ref)
        remaining = sorted(
            (item for item in hypotheses if item.hypothesis_ref not in reserved_refs),
            key=lambda item: (-item.score, item.hypothesis_ref),
        )
        hypotheses = sorted(
            reserved
            + remaining[: max(0, self.max_grounding_hypotheses - len(reserved))],
            key=lambda item: (-item.score, item.hypothesis_ref),
        )
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
                "surface_index_snapshot_ref": self.index.snapshot_ref,
                "surface_index_world_revision": self.index.world_revision,
                "surface_index_authority_generation": self.index.authority_generation,
                "regex_per_stored_surface": False,
                "span_providers": [
                    str(getattr(provider, "provider_ref", type(provider).__name__))
                    for provider in self.span_providers
                ],
                "lexical_feature_hypotheses": True,
                "precise_source_alignment": True,
            },
        )



# Stage-5 construction assembly is implemented exclusively by
# cemm.form_algebra.AtomicConstructionAssembler.

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
            "learning_contract_ref": "contract:designation_learning",
            "surface_evidence": surface,
        },
        "modality": "actual",
    }
