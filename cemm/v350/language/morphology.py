"""Productive, reversible input morphology for reviewed language packs.

Rules operate only on morphological form. They recover a pinned lexeme plus
grammatical features; they never route semantic concepts by regex or keywords.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..schema.model import semantic_fingerprint
from .model import (
    FormCandidate,
    MorphologyAnalysisOperation,
    MorphologyAnalysisRuleRecord,
    Span,
)


@dataclass(frozen=True, slots=True)
class MorphologyAnalysis:
    analysis_ref: str
    rule_ref: str
    rule_revision: int
    lexeme_ref: str
    lexeme_revision: int
    authority_form_ref: str
    authority_form_revision: int
    span: Span
    observation_refs: tuple[str, ...]
    feature_values: tuple[tuple[str, str], ...]
    confidence: float
    evidence_refs: tuple[str, ...]


class ProductiveMorphologyAnalyzer:
    def __init__(self, registry) -> None:
        self.registry = registry

    def analyze_observation(
        self,
        *,
        observed_key: str,
        span: Span,
        observation_refs: tuple[str, ...],
        language_tag: str,
        satisfied_condition_refs: tuple[str, ...] = (),
    ) -> tuple[tuple[FormCandidate, ...], tuple[MorphologyAnalysis, ...]]:
        result = []
        analyses = []
        satisfied = set(satisfied_condition_refs)
        for rule in self.registry.morphology_rules_for_language(language_tag):
            if not rule.executable:
                continue
            if not set(rule.condition_refs).issubset(satisfied):
                continue
            recovered_lemma = _recover_lemma_key(rule, observed_key)
            if recovered_lemma is None:
                continue
            for lexeme in self.registry.morphology_lexemes(
                rule, lemma_key=recovered_lemma
            ):
                lemma = self.registry.require_form(
                    lexeme.lemma_form_ref, lexeme.lemma_form_revision
                )
                if lemma.normalized_form != recovered_lemma:
                    continue
                evidence = (
                    f"morphology-analysis-rule:{rule.rule_ref}@{rule.revision}",
                    *rule.evidence_refs,
                )
                analysis_ref = "morphology-analysis:" + semantic_fingerprint(
                    "morphology-analysis",
                    (
                        rule.rule_ref,
                        rule.revision,
                        observed_key,
                        span.start,
                        span.end,
                        lexeme.lexeme_ref,
                        lexeme.revision,
                    ),
                    24,
                )
                analyses.append(
                    MorphologyAnalysis(
                        analysis_ref=analysis_ref,
                        rule_ref=rule.rule_ref,
                        rule_revision=rule.revision,
                        lexeme_ref=lexeme.lexeme_ref,
                        lexeme_revision=lexeme.revision,
                        authority_form_ref=lemma.form_ref,
                        authority_form_revision=lemma.revision,
                        span=span,
                        observation_refs=observation_refs,
                        feature_values=rule.feature_values,
                        confidence=rule.confidence,
                        evidence_refs=evidence,
                    )
                )
                result.append(
                    FormCandidate(
                        candidate_ref="form-candidate:"
                        + semantic_fingerprint(
                            "morphological-form-candidate",
                            (
                                observation_refs,
                                rule.rule_ref,
                                rule.revision,
                                lexeme.lexeme_ref,
                                lexeme.revision,
                                observed_key,
                            ),
                            20,
                        ),
                        observation_refs=observation_refs,
                        span=span,
                        form_ref=lemma.form_ref,
                        form_revision=lemma.revision,
                        language_tag=language_tag,
                        confidence=rule.confidence,
                        evidence_refs=evidence,
                        morphology_rule_ref=rule.rule_ref,
                        morphology_rule_revision=rule.revision,
                        derived_lexeme_ref=lexeme.lexeme_ref,
                        derived_lexeme_revision=lexeme.revision,
                        derived_feature_values=rule.feature_values,
                    )
                )
        return (
            tuple(sorted(result, key=lambda item: item.candidate_ref)),
            tuple(sorted(analyses, key=lambda item: item.analysis_ref)),
        )


def _recover_lemma_key(
    rule: MorphologyAnalysisRuleRecord,
    observed: str,
) -> str | None:
    if rule.operation in {
        MorphologyAnalysisOperation.IDENTITY,
        MorphologyAnalysisOperation.ZERO,
    }:
        return observed
    if rule.operation in {
        MorphologyAnalysisOperation.PREFIX,
        MorphologyAnalysisOperation.CLITIC_PREFIX,
    }:
        if not observed.startswith(rule.surface_operand):
            return None
        return observed[len(rule.surface_operand):]
    if rule.operation in {
        MorphologyAnalysisOperation.SUFFIX,
        MorphologyAnalysisOperation.CLITIC_SUFFIX,
    }:
        if not observed.endswith(rule.surface_operand):
            return None
        return observed[: len(observed) - len(rule.surface_operand)]
    if rule.operation == MorphologyAnalysisOperation.REPLACE_SUFFIX:
        if not observed.endswith(rule.surface_operand):
            return None
        stem = observed[: len(observed) - len(rule.surface_operand)]
        return f"{stem}{rule.lemma_operand}"
    raise ValueError(
        f"unsupported morphology analysis operation:{rule.operation}"
    )
