"""Unicode-first, evidence-preserving form lattice construction."""
from __future__ import annotations

from collections import Counter, defaultdict
import unicodedata
from typing import Iterable

from ..schema.model import semantic_fingerprint
from .adapters import SyntaxAdapterHub, SyntaxAdapterInput
from .constructions import ConstructionMatcher
from .model import (
    FormCandidate,
    FormKind,
    FormLattice,
    FormObservation,
    LanguageEvidence,
    LatticeEdge,
    LatticeEdgeKind,
    LatticeNode,
    LatticeNodeKind,
    NormalizationEvidence,
    SenseCandidate,
    Span,
)
from .registry import LanguageRegistry


class FormLatticeAnalyzer:
    def __init__(
        self,
        registry: LanguageRegistry,
        *,
        syntax_adapters: SyntaxAdapterHub | None = None,
        maximum_form_tokens: int = 8,
    ) -> None:
        if maximum_form_tokens < 1:
            raise ValueError("maximum_form_tokens must be positive")
        self.registry = registry
        self.syntax_adapters = syntax_adapters or SyntaxAdapterHub()
        self.maximum_form_tokens = maximum_form_tokens

    def analyze(
        self,
        content: str,
        *,
        source_ref: str,
        language_hints: tuple[str, ...] = (),
    ) -> FormLattice:
        if not isinstance(content, str):
            raise TypeError("content must be a string")
        if not source_ref.strip():
            raise ValueError("source_ref is required")
        observations = self._observe(content, source_ref)
        language_evidence = self._languages(observations, language_hints)
        forms, normalization = self._forms(content, observations, language_evidence)
        senses = self._senses(forms)
        tags = tuple(sorted({item.language_tag for item in language_evidence}))
        dependency, constituency = self.syntax_adapters.analyze(SyntaxAdapterInput(
            source_ref=source_ref,
            content=content,
            observations=observations,
            language_tags=tags,
        ))
        constructions = ConstructionMatcher(self.registry).match(
            observations, forms, senses, dependency, constituency
        )
        nodes, edges = self._graph(
            observations, language_evidence, normalization, forms, senses, constructions
        )
        covered = set()
        for item in forms:
            covered.update(range(item.span.start, item.span.end))
        unresolved = tuple(
            item.span for item in observations
            if item.category not in {"punctuation", "symbol"}
            and not any(index in covered for index in range(item.span.start, item.span.end))
        )
        lattice_ref = "form-lattice:" + semantic_fingerprint(
            "form-lattice-ref", (source_ref, content, tuple(item.node_ref for item in nodes)), 24
        )
        return FormLattice(
            lattice_ref=lattice_ref,
            source_ref=source_ref,
            source_content=content,
            observations=observations,
            language_evidence=language_evidence,
            normalization_evidence=normalization,
            form_candidates=forms,
            sense_candidates=senses,
            construction_candidates=constructions,
            nodes=nodes,
            edges=edges,
            unresolved_spans=unresolved,
            metadata={
                "code_switching": len(tags) > 1,
                "language_tags": tags,
                "dependency_parse_refs": tuple(item.parse_ref for item in dependency),
                "constituency_parse_refs": tuple(item.parse_ref for item in constituency),
            },
        )

    @staticmethod
    def _observe(content: str, source_ref: str) -> tuple[FormObservation, ...]:
        spans = _unicode_segments(content)
        result = []
        for index, (start, end, category) in enumerate(spans):
            original = content[start:end]
            canonical = unicodedata.normalize("NFKC", original).casefold()
            script = _script_of(original)
            result.append(FormObservation(
                observation_ref=f"observation:{semantic_fingerprint('observation', (source_ref, start, end, original), 20)}",
                span=Span(start, end),
                original=original,
                canonical=canonical,
                script=script,
                category=category,
                evidence_refs=(f"source-span:{source_ref}:{start}:{end}",),
            ))
        return tuple(result)

    def _languages(
        self,
        observations: tuple[FormObservation, ...],
        hints: tuple[str, ...],
    ) -> tuple[LanguageEvidence, ...]:
        active = self.registry.active_packs()
        allowed = {item.language_tag for item in active}
        unknown_hints = sorted(set(hints).difference(allowed))
        if unknown_hints:
            raise ValueError(f"unknown language hints: {unknown_hints}")
        result = []
        for observation in observations:
            matches = []
            for pack in active:
                exact = self.registry.forms_for(pack.language_tag, observation.canonical)
                normalized = self.registry.normalization_forms_for(pack.language_tag, observation.canonical)
                script_match = not pack.scripts or observation.script in pack.scripts
                score = 0.0
                sources = []
                if exact:
                    score = 1.0
                    sources.extend(item.form_ref for item in exact)
                elif normalized:
                    score = 0.85
                    sources.extend(item.form_ref for item in normalized)
                elif script_match and observation.category in {"word", "number"}:
                    score = 0.2
                    sources.append(f"script:{observation.script}")
                if pack.language_tag in hints:
                    score = max(score, 0.45)
                    sources.append(f"language-hint:{pack.language_tag}")
                if score:
                    matches.append((pack.language_tag, score, tuple(sorted(set(sources)))))
            if not matches:
                continue
            best = max(score for _, score, _ in matches)
            competitive = tuple(sorted(tag for tag, score, _ in matches if score >= best - 0.15))
            for tag, score, sources in sorted(matches):
                if score < best - 0.15:
                    continue
                result.append(LanguageEvidence(
                    language_tag=tag,
                    span=observation.span,
                    confidence=score,
                    source_refs=sources,
                    competing_language_tags=tuple(item for item in competitive if item != tag),
                ))
        return tuple(result)

    def _forms(
        self,
        content: str,
        observations: tuple[FormObservation, ...],
        languages: tuple[LanguageEvidence, ...],
    ) -> tuple[tuple[FormCandidate, ...], tuple[NormalizationEvidence, ...]]:
        language_by_span = defaultdict(set)
        for item in languages:
            language_by_span[(item.span.start, item.span.end)].add(item.language_tag)
        result = []
        normalization = []
        lexical_observations = tuple(
            item for item in observations if item.category not in {"whitespace"}
        )
        for start_index, first in enumerate(lexical_observations):
            keys = []
            refs = []
            for end_index in range(start_index, min(len(lexical_observations), start_index + self.maximum_form_tokens)):
                item = lexical_observations[end_index]
                if end_index > start_index and item.category in {"punctuation", "symbol"}:
                    break
                keys.append(item.canonical)
                refs.append(item.observation_ref)
                normalized_key = " ".join(keys)
                span = Span(first.span.start, item.span.end)
                tags = set.intersection(*(
                    language_by_span.get((obs.span.start, obs.span.end), set())
                    for obs in lexical_observations[start_index:end_index + 1]
                )) if refs else set()
                if not tags:
                    tags = {pack.language_tag for pack in self.registry.active_packs()}
                for tag in sorted(tags):
                    exact = self.registry.forms_for(tag, normalized_key)
                    explicit_normalized = self.registry.normalization_forms_for(tag, normalized_key)
                    for form in (*exact, *explicit_normalized):
                        if form.token_count != len(refs):
                            continue
                        via_normalization = form in explicit_normalized and form not in exact
                        evidence_refs = [f"form-match:{form.form_ref}@{form.revision}"]
                        if via_normalization:
                            evidence_ref = "normalization:" + semantic_fingerprint(
                                "normalization-evidence", (span.start, span.end, normalized_key, form.normalized_form, form.form_ref), 20
                            )
                            normalization.append(NormalizationEvidence(
                                evidence_ref=evidence_ref,
                                span=span,
                                original=content[span.start:span.end],
                                proposed=form.written_form,
                                rule_ref=str(form.metadata.get("normalization_rule_ref", f"form-variant:{form.form_ref}")),
                                confidence=float(form.metadata.get("normalization_confidence", 0.85)),
                                reversible=True,
                            ))
                            evidence_refs.append(evidence_ref)
                        candidate_ref = "form-candidate:" + semantic_fingerprint(
                            "form-candidate", (tuple(refs), form.form_ref, form.revision, tag, via_normalization), 20
                        )
                        result.append(FormCandidate(
                            candidate_ref=candidate_ref,
                            observation_refs=tuple(refs),
                            span=span,
                            form_ref=form.form_ref,
                            form_revision=form.revision,
                            language_tag=tag,
                            confidence=0.85 if via_normalization else 1.0,
                            evidence_refs=tuple(evidence_refs),
                            via_variant=form.variant_of_ref is not None,
                            via_normalization=via_normalization,
                        ))
        dedup = {item.candidate_ref: item for item in result}
        norm_dedup = {item.evidence_ref: item for item in normalization}
        return (
            tuple(sorted(dedup.values(), key=lambda item: (item.span.start, item.span.end, item.form_ref))),
            tuple(sorted(norm_dedup.values(), key=lambda item: (item.span.start, item.span.end, item.evidence_ref))),
        )

    def _senses(self, forms: tuple[FormCandidate, ...]) -> tuple[SenseCandidate, ...]:
        result = []
        for form_candidate in forms:
            for link in self.registry.links_for_form(form_candidate.form_ref, form_candidate.form_revision):
                sense = self.registry.require_sense(link.sense_ref, link.sense_revision)
                confidence = min(1.0, form_candidate.confidence * min(1.0, link.prior_weight))
                candidate_ref = "sense-candidate:" + semantic_fingerprint(
                    "sense-candidate", (form_candidate.candidate_ref, sense.sense_ref, sense.revision, link.link_ref), 20
                )
                result.append(SenseCandidate(
                    candidate_ref=candidate_ref,
                    form_candidate_ref=form_candidate.candidate_ref,
                    sense_ref=sense.sense_ref,
                    sense_revision=sense.revision,
                    target_kind=sense.target_kind,
                    target_ref=sense.target_ref,
                    target_revision=sense.target_revision,
                    target_schema_class=sense.target_schema_class,
                    confidence=confidence,
                    evidence_refs=(
                        *form_candidate.evidence_refs,
                        f"form-sense-link:{link.link_ref}@{link.revision}",
                    ),
                    use_operation=sense.use_operation,
                    scope_behavior=sense.scope_behavior,
                    expected_type_refs=sense.expected_type_refs,
                    lexical_category=sense.lexical_category,
                    argument_map=sense.argument_map,
                    metadata=dict(sense.metadata),
                ))
        return tuple(sorted(result, key=lambda item: (item.form_candidate_ref, -item.confidence, item.sense_ref)))

    @staticmethod
    def _graph(observations, languages, normalization, forms, senses, constructions):
        nodes = []
        edges = []
        observation_nodes = {}
        for item in observations:
            ref = f"lattice-node:observation:{item.observation_ref}"
            observation_nodes[item.observation_ref] = ref
            nodes.append(LatticeNode(ref, LatticeNodeKind.OBSERVATION, item.span, item.observation_ref, 1.0, item.evidence_refs))
        form_nodes = {}
        for item in forms:
            ref = f"lattice-node:form:{item.candidate_ref}"
            form_nodes[item.candidate_ref] = ref
            nodes.append(LatticeNode(ref, LatticeNodeKind.FORM, item.span, item.form_ref, item.confidence, item.evidence_refs))
            for observation_ref in item.observation_refs:
                edge_ref = "lattice-edge:" + semantic_fingerprint("edge", (observation_nodes[observation_ref], ref, "covers"), 20)
                edges.append(LatticeEdge(edge_ref, observation_nodes[observation_ref], ref, LatticeEdgeKind.COVERS, item.confidence, item.evidence_refs))
        sense_nodes = {}
        for item in senses:
            form = next(candidate for candidate in forms if candidate.candidate_ref == item.form_candidate_ref)
            ref = f"lattice-node:sense:{item.candidate_ref}"
            sense_nodes[item.candidate_ref] = ref
            nodes.append(LatticeNode(ref, LatticeNodeKind.SENSE, form.span, item.sense_ref, item.confidence, item.evidence_refs))
            edge_ref = "lattice-edge:" + semantic_fingerprint("edge", (form_nodes[item.form_candidate_ref], ref, "sense"), 20)
            edges.append(LatticeEdge(edge_ref, form_nodes[item.form_candidate_ref], ref, LatticeEdgeKind.SENSE, item.confidence, item.evidence_refs))
        for item in constructions:
            ref = f"lattice-node:construction:{item.candidate_ref}"
            nodes.append(LatticeNode(ref, LatticeNodeKind.CONSTRUCTION, item.span, item.construction_ref, item.confidence, item.evidence_refs))
            for trigger in item.trigger_refs:
                source = form_nodes.get(trigger) or sense_nodes.get(trigger)
                if source is None:
                    continue
                edge_ref = "lattice-edge:" + semantic_fingerprint("edge", (source, ref, "trigger"), 20)
                edges.append(LatticeEdge(edge_ref, source, ref, LatticeEdgeKind.TRIGGER, item.confidence, item.evidence_refs))
            for _, fillers in item.slot_fillers:
                for filler in fillers:
                    source = form_nodes.get(filler) or sense_nodes.get(filler)
                    if source is None:
                        continue
                    edge_ref = "lattice-edge:" + semantic_fingerprint("edge", (source, ref, "composes"), 20)
                    edges.append(LatticeEdge(edge_ref, source, ref, LatticeEdgeKind.COMPOSES, item.confidence, item.evidence_refs))
            for gap in item.gap_refs:
                gap_ref = f"lattice-node:gap:{gap}"
                nodes.append(LatticeNode(gap_ref, LatticeNodeKind.GAP, item.span, gap, item.confidence, item.evidence_refs))
                edge_ref = "lattice-edge:" + semantic_fingerprint("edge", (gap_ref, ref, "ellipsis"), 20)
                edges.append(LatticeEdge(edge_ref, gap_ref, ref, LatticeEdgeKind.ELLIPSIS, item.confidence, item.evidence_refs))
        return (
            tuple(sorted(nodes, key=lambda item: (item.span.start, item.span.end, item.node_kind.value, item.node_ref))),
            tuple(sorted(edges, key=lambda item: item.edge_ref)),
        )


def _unicode_segments(content: str) -> tuple[tuple[int, int, str], ...]:
    if not content:
        return ()
    result = []
    start = 0
    current = _character_group(content[0])
    for index, character in enumerate(content[1:], start=1):
        group = _character_group(character)
        previous = content[index - 1]
        joiner = character in {"'", "’", "-"} or previous in {"'", "’", "-"}
        if group != current and not (
            joiner and current == "word" and group in {"word", "punctuation"}
        ):
            result.append((start, index, current))
            start = index
            current = group
    result.append((start, len(content), current))
    return tuple(item for item in result if item[2] != "whitespace")


def _character_group(character: str) -> str:
    category = unicodedata.category(character)
    if category.startswith(("L", "M")):
        return "word"
    if category.startswith("N"):
        return "number"
    if category.startswith("Z") or character.isspace():
        return "whitespace"
    if category.startswith("P"):
        return "punctuation"
    return "symbol"


def _script_of(content: str) -> str:
    scripts = []
    for character in content:
        if not character.isalpha():
            continue
        name = unicodedata.name(character, "UNKNOWN")
        scripts.append(name.split(" ", 1)[0].title())
    if not scripts:
        return "Common"
    counts = Counter(scripts)
    return min(counts, key=lambda script: (-counts[script], script))
