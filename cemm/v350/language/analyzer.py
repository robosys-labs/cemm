"""Unicode-first, evidence-preserving form lattice construction."""
from __future__ import annotations

from collections import Counter, defaultdict
import unicodedata
from typing import Iterable

from ..schema.model import UseOperation, semantic_fingerprint
from ..final_activation import decide_turn_language
from .adapters import SyntaxAdapterHub, SyntaxAdapterInput
from .constructions import ConstructionMatcher
from .morphology import ProductiveMorphologyAnalyzer
from .model import (
    FormCandidate,
    FormKind,
    FormLattice,
    FormObservation,
    LexemeCandidate,
    LanguageEvidence,
    LatticeEdge,
    LatticeEdgeKind,
    LatticeNode,
    LatticeNodeKind,
    NormalizationEvidence,
    SemanticContribution,
    SemanticContributionKind,
    SenseCandidate,
    Span,
)
from .registry import LanguageRegistry
from .reversible_normalization import ReversibleNormalization, normalize_with_provenance


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
        source_normalization = normalize_with_provenance(content)
        observations = self._observe(content, source_ref, source_normalization)
        language_evidence = self._languages(observations, language_hints)
        forms, normalization = self._forms(content, observations, language_evidence)
        lexemes = self._lexemes(forms)
        senses = self._senses(forms, lexemes)
        language_decision = decide_turn_language(
            observations, forms, language_hints
        )
        # Syntax adapters receive only positive lexical/form evidence when
        # available. Weak script-compatible tags stay span evidence and never
        # manufacture turn-level multilinguality.
        tags = (
            language_decision.positive_language_tags
            or tuple(sorted({item.language_tag for item in language_evidence}))
        )
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
            observations, language_evidence, normalization, forms, lexemes, senses, constructions
        )
        covered = set()
        for item in forms:
            covered.update(range(item.span.start, item.span.end))
        unresolved = tuple(
            item.span for item in observations
            if item.category not in {"punctuation", "symbol", "whitespace"}
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
            lexeme_candidates=lexemes,
            unresolved_spans=unresolved,
            metadata={
                "normalization_ref": source_normalization.normalization_ref,
                "normalization_profile_ref": source_normalization.profile_ref,
                "normalization_segments": tuple(
                    (
                        item.source_start, item.source_end,
                        item.normalized_start, item.normalized_end,
                        item.operations,
                    )
                    for item in source_normalization.segments
                ),
                "code_switching": language_decision.code_switching,
                "language_tags": tags,
                "turn_language_tag": language_decision.language_tag,
                "turn_language_confidence": language_decision.confidence,
                "turn_language_competing_tags": language_decision.competing_tags,
                "positive_language_tags": language_decision.positive_language_tags,
                "dependency_parse_refs": tuple(item.parse_ref for item in dependency),
                "constituency_parse_refs": tuple(item.parse_ref for item in constituency),
            },
        )

    @staticmethod
    def _observe(
        content: str, source_ref: str, normalization: ReversibleNormalization
    ) -> tuple[FormObservation, ...]:
        spans = _unicode_segments(content)
        result = []
        for index, (start, end, category) in enumerate(spans):
            original = content[start:end]
            normalized_start, normalized_end = normalization.normalized_span_for(start, end)
            canonical = normalization.normalized_text[normalized_start:normalized_end]
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
                    produced_for_tag = False
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
                        produced_for_tag = True
                    if (
                        len(refs) == 1
                        and item.category == "word"
                        and not produced_for_tag
                    ):
                        derived, _analyses = ProductiveMorphologyAnalyzer(
                            self.registry
                        ).analyze_observation(
                            observed_key=normalized_key,
                            span=span,
                            observation_refs=tuple(refs),
                            language_tag=tag,
                        )
                        result.extend(derived)
        dedup = {item.candidate_ref: item for item in result}
        norm_dedup = {item.evidence_ref: item for item in normalization}
        return (
            tuple(sorted(dedup.values(), key=lambda item: (item.span.start, item.span.end, item.form_ref))),
            tuple(sorted(norm_dedup.values(), key=lambda item: (item.span.start, item.span.end, item.evidence_ref))),
        )

    def _lexemes(self, forms: tuple[FormCandidate, ...]) -> tuple[LexemeCandidate, ...]:
        result: list[LexemeCandidate] = []
        for form_candidate in forms:
            if form_candidate.derived_lexeme_ref is not None:
                lexeme = self.registry.require_lexeme(
                    form_candidate.derived_lexeme_ref,
                    form_candidate.derived_lexeme_revision,
                )
                features = dict(lexeme.feature_defaults)
                features.update(dict(form_candidate.derived_feature_values))
                result.append(LexemeCandidate(
                    candidate_ref="lexeme-candidate:" + semantic_fingerprint(
                        "morphology-lexeme-candidate",
                        (form_candidate.candidate_ref, lexeme.lexeme_ref,
                         lexeme.revision, form_candidate.morphology_rule_ref,
                         form_candidate.morphology_rule_revision),
                        20,
                    ),
                    form_candidate_ref=form_candidate.candidate_ref,
                    lexeme_ref=lexeme.lexeme_ref,
                    lexeme_revision=lexeme.revision,
                    language_tag=form_candidate.language_tag,
                    confidence=form_candidate.confidence,
                    feature_values=tuple(sorted((str(k), str(v)) for k, v in features.items())),
                    evidence_refs=form_candidate.evidence_refs,
                ))
                continue
            form = self.registry.require_form(form_candidate.form_ref, form_candidate.form_revision)
            links = self.registry.lexeme_links_for_form(form.form_ref, form.revision)
            inherited_from = None
            if not links and form.variant_of_ref is not None:
                inherited_from = self.registry.require_form(form.variant_of_ref)
                links = self.registry.lexeme_links_for_form(
                    inherited_from.form_ref, inherited_from.revision
                )
            for link in links:
                lexeme = self.registry.require_lexeme(link.lexeme_ref, link.lexeme_revision)
                features = dict(lexeme.feature_defaults)
                if inherited_from is not None:
                    features.update(dict(inherited_from.feature_values))
                features.update(dict(form.feature_values))
                features.update(dict(link.feature_values))
                evidence = [
                    *form_candidate.evidence_refs,
                    f"form-lexeme-link:{link.link_ref}@{link.revision}",
                ]
                if inherited_from is not None:
                    evidence.append(
                        f"variant-lexeme-inheritance:{form.form_ref}->{inherited_from.form_ref}"
                    )
                result.append(LexemeCandidate(
                    candidate_ref="lexeme-candidate:" + semantic_fingerprint(
                        "lexeme-candidate",
                        (
                            form_candidate.candidate_ref,
                            lexeme.lexeme_ref,
                            lexeme.revision,
                            link.link_ref,
                            None if inherited_from is None else inherited_from.form_ref,
                        ),
                        20,
                    ),
                    form_candidate_ref=form_candidate.candidate_ref,
                    lexeme_ref=lexeme.lexeme_ref,
                    lexeme_revision=lexeme.revision,
                    language_tag=form_candidate.language_tag,
                    confidence=min(
                        1.0,
                        form_candidate.confidence * min(1.0, link.prior_weight),
                    ),
                    feature_values=tuple(sorted((str(k), str(v)) for k, v in features.items())),
                    evidence_refs=tuple(evidence),
                    link_ref=link.link_ref,
                    link_revision=link.revision,
                ))
        dedup = {item.candidate_ref: item for item in result}
        return tuple(sorted(
            dedup.values(),
            key=lambda item: (item.form_candidate_ref, item.lexeme_ref, item.candidate_ref),
        ))

    def _senses(
        self,
        forms: tuple[FormCandidate, ...],
        lexemes: tuple[LexemeCandidate, ...],
    ) -> tuple[SenseCandidate, ...]:
        result: list[SenseCandidate] = []
        lexemes_by_form: dict[str, list[LexemeCandidate]] = defaultdict(list)
        for item in lexemes:
            lexemes_by_form[item.form_candidate_ref].append(item)

        def append_candidate(
            form_candidate: FormCandidate,
            sense,
            *,
            prior_weight: float,
            evidence_refs: tuple[str, ...],
            lexeme_candidate: LexemeCandidate | None,
            authority_path: str,
            authority_ref: str,
            authority_revision: int,
        ) -> None:
            # FormLatticeAnalyzer is the understanding/GROUND path. A migrated or
            # learned multi-use sense participates only when GROUND is explicitly
            # authorized; REALIZE-only senses must never leak into understanding.
            if not sense.supports_use(UseOperation.GROUND):
                return
            confidence = min(1.0, form_candidate.confidence * min(1.0, prior_weight))
            if lexeme_candidate is not None:
                confidence = min(confidence, lexeme_candidate.confidence)
            contributions = self._semantic_contributions(
                form_candidate,
                sense,
                lexeme_candidate,
                evidence_refs,
                authority_path,
            )
            target_contributions = tuple(
                item
                for item in contributions
                if item.contribution_kind == SemanticContributionKind.TARGET
                and item.target_ref is not None
            )
            effective_target = (
                target_contributions[0] if len(target_contributions) == 1 else None
            )
            scope_behaviors = tuple(
                item.scope_behavior
                for item in contributions
                if item.contribution_kind == SemanticContributionKind.SCOPE
                and item.scope_behavior != "none"
            )
            unique_scopes = tuple(sorted(set(scope_behaviors)))
            effective_scope = (
                unique_scopes[0] if len(unique_scopes) == 1 else sense.scope_behavior
            )
            effective_types = tuple(sorted({
                *sense.expected_type_refs,
                *(
                    ref
                    for contribution in contributions
                    for ref in contribution.expected_type_refs
                ),
            }))
            explicit_arguments = tuple(sorted({
                (str(item.metadata.get("source_role") or ""), item.role_ref)
                for item in contributions
                if item.contribution_kind == SemanticContributionKind.ARGUMENT
                and item.role_ref
                and item.metadata.get("source_role")
            }))
            candidate_ref = "sense-candidate:" + semantic_fingerprint(
                "sense-candidate",
                (
                    form_candidate.candidate_ref,
                    None if lexeme_candidate is None else lexeme_candidate.candidate_ref,
                    sense.sense_ref,
                    sense.revision,
                    authority_ref,
                    authority_revision,
                    tuple(item.contribution_ref for item in contributions),
                ),
                20,
            )
            result.append(SenseCandidate(
                candidate_ref=candidate_ref,
                form_candidate_ref=form_candidate.candidate_ref,
                sense_ref=sense.sense_ref,
                sense_revision=sense.revision,
                target_kind=(
                    effective_target.target_kind
                    if effective_target is not None
                    else sense.target_kind
                ),
                target_ref=(
                    effective_target.target_ref
                    if effective_target is not None
                    else sense.target_ref
                ),
                target_revision=(
                    effective_target.target_revision
                    if effective_target is not None
                    else sense.target_revision
                ),
                target_schema_class=(
                    effective_target.target_schema_class
                    if effective_target is not None
                    else sense.target_schema_class
                ),
                confidence=confidence,
                evidence_refs=evidence_refs,
                contributions=contributions,
                use_operation=UseOperation.GROUND,
                scope_behavior=effective_scope,
                expected_type_refs=effective_types,
                lexical_category=sense.lexical_category,
                argument_map=explicit_arguments or sense.argument_map,
                lexeme_ref=(
                    None if lexeme_candidate is None else lexeme_candidate.lexeme_ref
                ),
                lexeme_revision=(
                    None if lexeme_candidate is None else lexeme_candidate.lexeme_revision
                ),
                authority_path=authority_path,
                authority_ref=authority_ref,
                authority_revision=authority_revision,
                metadata={**dict(sense.metadata), "authority_path": authority_path},
            ))

        for form_candidate in forms:
            usable_lexeme_candidate_emitted = False
            for lexeme_candidate in sorted(
                lexemes_by_form.get(form_candidate.candidate_ref, ()),
                key=lambda item: item.candidate_ref,
            ):
                links = self.registry.sense_links_for_lexeme(
                    lexeme_candidate.lexeme_ref,
                    lexeme_candidate.lexeme_revision,
                )
                if not links:
                    continue
                for link in links:
                    sense = self.registry.require_sense(link.sense_ref, link.sense_revision)
                    before = len(result)
                    append_candidate(
                        form_candidate,
                        sense,
                        prior_weight=link.prior_weight,
                        evidence_refs=(
                            *lexeme_candidate.evidence_refs,
                            f"lexeme-sense-link:{link.link_ref}@{link.revision}",
                        ),
                        lexeme_candidate=lexeme_candidate,
                        authority_path="lexeme",
                        authority_ref=link.link_ref,
                        authority_revision=link.revision,
                    )
                    if len(result) > before:
                        usable_lexeme_candidate_emitted = True
            # A canonical lexeme link that yields no GROUND-authorized sense must
            # not suppress the explicit bounded signed compatibility path.
            if usable_lexeme_candidate_emitted:
                continue

            # Explicitly bounded compatibility path for signed legacy boot data.
            for link in self.registry.links_for_form(
                form_candidate.form_ref,
                form_candidate.form_revision,
            ):
                sense = self.registry.require_sense(link.sense_ref, link.sense_revision)
                append_candidate(
                    form_candidate,
                    sense,
                    prior_weight=link.prior_weight,
                    evidence_refs=(
                        *form_candidate.evidence_refs,
                        f"form-sense-link:{link.link_ref}@{link.revision}",
                    ),
                    lexeme_candidate=None,
                    authority_path="legacy_form_sense",
                    authority_ref=link.link_ref,
                    authority_revision=link.revision,
                )

        return tuple(sorted(
            result,
            key=lambda item: (
                item.form_candidate_ref,
                -item.confidence,
                item.sense_ref,
                item.candidate_ref,
            ),
        ))

    def _semantic_contributions(
        self,
        form_candidate: FormCandidate,
        sense,
        lexeme_candidate: LexemeCandidate | None,
        evidence_refs: tuple[str, ...],
        authority_path: str,
    ) -> tuple[SemanticContribution, ...]:
        specs = tuple(
            item
            for item in self.registry.contribution_specs_for_sense(
                sense.sense_ref,
                sense.revision,
            )
            if item.use_operation
            in {UseOperation.GROUND, UseOperation.COMPOSE, UseOperation.QUERY}
        )
        result: list[SemanticContribution] = []
        for spec in specs:
            result.append(SemanticContribution(
                contribution_ref="semantic-contribution:" + semantic_fingerprint(
                    "semantic-contribution",
                    (
                        form_candidate.candidate_ref,
                        None
                        if lexeme_candidate is None
                        else lexeme_candidate.candidate_ref,
                        spec.spec_ref,
                        spec.revision,
                    ),
                    20,
                ),
                contribution_kind=spec.contribution_kind,
                spec_ref=spec.spec_ref,
                spec_revision=spec.revision,
                target_kind=spec.target_kind,
                target_ref=spec.target_ref,
                target_revision=spec.target_revision,
                target_schema_class=spec.target_schema_class,
                expected_filler_classes=spec.expected_filler_classes,
                expected_schema_classes=spec.expected_schema_classes,
                expected_type_refs=spec.expected_type_refs,
                open_binding_purpose=spec.open_binding_purpose,
                restriction_refs=spec.restriction_refs,
                projection_ref=spec.projection_ref,
                projection_revision=spec.projection_revision,
                role_ref=spec.role_ref,
                scope_behavior=spec.scope_behavior,
                feature_values=spec.feature_constraints,
                evidence_refs=(
                    *evidence_refs,
                    f"semantic-contribution-spec:{spec.spec_ref}@{spec.revision}",
                ),
                metadata={
                    **dict(spec.metadata),
                    "authority_path": "semantic_contribution_spec",
                    "source_role": spec.source_role_ref,
                },
            ))

        # Compatibility compiler for legacy signed form/sense authority. It emits
        # explicit cycle contributions but does not create new durable semantics.
        if not result and sense.target_ref is not None:
            result.append(SemanticContribution(
                contribution_ref="semantic-contribution:" + semantic_fingerprint(
                    "legacy-target-contribution",
                    (form_candidate.candidate_ref, sense.sense_ref, sense.revision),
                    20,
                ),
                contribution_kind=SemanticContributionKind.TARGET,
                target_kind=sense.target_kind,
                target_ref=sense.target_ref,
                target_revision=sense.target_revision,
                target_schema_class=sense.target_schema_class,
                expected_type_refs=sense.expected_type_refs,
                evidence_refs=evidence_refs,
                metadata={"authority_path": authority_path},
            ))
            if sense.expected_type_refs:
                result.append(SemanticContribution(
                    contribution_ref="semantic-contribution:" + semantic_fingerprint(
                        "legacy-type-restriction",
                        (
                            form_candidate.candidate_ref,
                            sense.sense_ref,
                            sense.expected_type_refs,
                        ),
                        20,
                    ),
                    contribution_kind=SemanticContributionKind.RESTRICTION,
                    expected_type_refs=sense.expected_type_refs,
                    evidence_refs=evidence_refs,
                    metadata={"authority_path": authority_path},
                ))
            if sense.scope_behavior != "none":
                result.append(SemanticContribution(
                    contribution_ref="semantic-contribution:" + semantic_fingerprint(
                        "legacy-scope",
                        (
                            form_candidate.candidate_ref,
                            sense.sense_ref,
                            sense.scope_behavior,
                        ),
                        20,
                    ),
                    contribution_kind=SemanticContributionKind.SCOPE,
                    scope_behavior=sense.scope_behavior,
                    evidence_refs=evidence_refs,
                    metadata={"authority_path": authority_path},
                ))
            for source_role, semantic_port_ref in sense.argument_map:
                result.append(SemanticContribution(
                    contribution_ref="semantic-contribution:" + semantic_fingerprint(
                        "legacy-argument",
                        (
                            form_candidate.candidate_ref,
                            sense.sense_ref,
                            source_role,
                            semantic_port_ref,
                        ),
                        20,
                    ),
                    contribution_kind=SemanticContributionKind.ARGUMENT,
                    role_ref=semantic_port_ref,
                    evidence_refs=evidence_refs,
                    metadata={
                        "source_role": source_role,
                        "authority_path": authority_path,
                    },
                ))

        # Surface/form-family features remain grammar evidence even when semantic
        # contribution specs are fully migrated.
        form = self.registry.require_form(
            form_candidate.form_ref,
            form_candidate.form_revision,
        )
        features = dict(form.feature_values)
        if lexeme_candidate is not None:
            features.update(dict(lexeme_candidate.feature_values))
        features.update(dict(sense.feature_constraints))
        if features:
            values = tuple(sorted((str(k), str(v)) for k, v in features.items()))
            result.append(SemanticContribution(
                contribution_ref="semantic-contribution:" + semantic_fingerprint(
                    "grammatical-feature-contribution",
                    (
                        form_candidate.candidate_ref,
                        None
                        if lexeme_candidate is None
                        else lexeme_candidate.candidate_ref,
                        sense.sense_ref,
                        values,
                    ),
                    20,
                ),
                contribution_kind=SemanticContributionKind.GRAMMATICAL_FEATURE,
                feature_values=values,
                evidence_refs=evidence_refs,
                metadata={"authority_path": authority_path},
            ))

        dedup = {item.contribution_ref: item for item in result}
        return tuple(sorted(
            dedup.values(),
            key=lambda item: (item.contribution_kind.value, item.contribution_ref),
        ))

    @staticmethod
    def _graph(observations, languages, normalization, forms, lexemes, senses, constructions):
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
        lexeme_nodes = {}
        for item in lexemes:
            form = next(candidate for candidate in forms if candidate.candidate_ref == item.form_candidate_ref)
            ref = f"lattice-node:lexeme:{item.candidate_ref}"
            lexeme_nodes[item.candidate_ref] = ref
            nodes.append(LatticeNode(ref, LatticeNodeKind.LEXEME, form.span, item.lexeme_ref, item.confidence, item.evidence_refs))
            edge_ref = "lattice-edge:" + semantic_fingerprint(
                "edge", (form_nodes[item.form_candidate_ref], ref, "lexeme"), 20
            )
            edges.append(LatticeEdge(edge_ref, form_nodes[item.form_candidate_ref], ref, LatticeEdgeKind.LEXEME, item.confidence, item.evidence_refs))
        sense_nodes = {}
        for item in senses:
            form = next(candidate for candidate in forms if candidate.candidate_ref == item.form_candidate_ref)
            ref = f"lattice-node:sense:{item.candidate_ref}"
            sense_nodes[item.candidate_ref] = ref
            nodes.append(LatticeNode(ref, LatticeNodeKind.SENSE, form.span, item.sense_ref, item.confidence, item.evidence_refs))
            lexeme_node = next(
                (
                    lexeme_nodes[candidate.candidate_ref]
                    for candidate in lexemes
                    if candidate.form_candidate_ref == item.form_candidate_ref
                    and candidate.lexeme_ref == item.lexeme_ref
                ),
                None,
            )
            source = lexeme_node or form_nodes[item.form_candidate_ref]
            edge_ref = "lattice-edge:" + semantic_fingerprint("edge", (source, ref, "sense"), 20)
            edges.append(LatticeEdge(edge_ref, source, ref, LatticeEdgeKind.SENSE, item.confidence, item.evidence_refs))
            for contribution in item.contributions:
                cref = f"lattice-node:contribution:{contribution.contribution_ref}"
                nodes.append(LatticeNode(
                    cref, LatticeNodeKind.CONTRIBUTION, form.span,
                    contribution.contribution_ref, item.confidence,
                    contribution.evidence_refs or item.evidence_refs,
                ))
                edge_ref = "lattice-edge:" + semantic_fingerprint("edge", (ref, cref, "contribution"), 20)
                edges.append(LatticeEdge(
                    edge_ref, ref, cref, LatticeEdgeKind.CONTRIBUTION,
                    item.confidence, contribution.evidence_refs or item.evidence_refs,
                ))
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
        seen = set()
        unique_nodes = []
        for node in sorted(nodes, key=lambda item: (item.span.start, item.span.end, item.node_kind.value, item.node_ref)):
            if node.node_ref not in seen:
                seen.add(node.node_ref)
                unique_nodes.append(node)
        return (
            tuple(unique_nodes),
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
