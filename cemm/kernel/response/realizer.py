"""Proof-carrying multilingual realization.

The realizer accepts only an authorized SemanticEmissionProof.  Every output
span is covered by a lexicalization, grammatical morpheme, referring-expression
rule, grounded role value, mention/quotation license, punctuation, or spacing.
"""
from __future__ import annotations

from dataclasses import replace

from ..model.emission import (
    CoverageKind,
    RealizedMessage,
    SemanticEmissionProof,
    SemanticMessagePlan,
    SpanCoverage,
    UseMode,
)
from ..schema.lexicalization import LanguageRealizationPack, SegmentKind


class SemanticRealizer:
    def realize(
        self,
        plan: SemanticMessagePlan,
        proof: SemanticEmissionProof,
        pack: LanguageRealizationPack,
    ) -> RealizedMessage:
        if not proof.authorized:
            return RealizedMessage(
                plan_ref=plan.plan_id,
                language_tag=plan.language_tag,
                surface_text="",
                coverage=(),
                realized_clause_refs=(),
                blocked_clause_refs=tuple(clause.clause_id for clause in plan.clauses),
                emission_proof_ref=self._proof_ref(proof),
            )

        surface_parts: list[str] = []
        coverage: list[SpanCoverage] = []
        realized: list[str] = []
        blocked: list[str] = []

        for clause in plan.clauses:
            clause_proof = proof.for_clause(clause.clause_id)
            if clause_proof is None or not clause_proof.authorized:
                blocked.append(clause.clause_id)
                continue

            construction = next(
                (
                    item
                    for item in pack.constructions
                    if item.schema_id == clause_proof.construction_ref
                ),
                None,
            )
            if construction is None:
                blocked.append(clause.clause_id)
                continue

            clause_start = sum(len(part) for part in surface_parts)
            clause_failed = False
            for segment in construction.segments:
                value, kind, semantic_ref, schema_ref = self._render_segment(
                    segment, clause, pack
                )
                if value is None:
                    if segment.required:
                        clause_failed = True
                        break
                    continue
                start = sum(len(part) for part in surface_parts)
                surface_parts.append(value)
                end = start + len(value)
                coverage.append(
                    SpanCoverage(
                        start=start,
                        end=end,
                        surface=value,
                        coverage_kind=kind,
                        semantic_ref=semantic_ref,
                        schema_ref=schema_ref,
                        contribution_refs=segment.contribution_refs,
                    )
                )
            if clause_failed:
                del coverage[
                    next(
                        (
                            index
                            for index, item in enumerate(coverage)
                            if item.start >= clause_start
                        ),
                        len(coverage),
                    ):
                ]
                while sum(len(part) for part in surface_parts) > clause_start:
                    surface_parts.pop()
                blocked.append(clause.clause_id)
                continue
            realized.append(clause.clause_id)

        surface = "".join(surface_parts)
        if surface and not self._fully_covered(surface, coverage):
            return RealizedMessage(
                plan_ref=plan.plan_id,
                language_tag=plan.language_tag,
                surface_text="",
                coverage=(),
                realized_clause_refs=(),
                blocked_clause_refs=tuple(clause.clause_id for clause in plan.clauses),
                emission_proof_ref=self._proof_ref(proof),
            )

        return RealizedMessage(
            plan_ref=plan.plan_id,
            language_tag=plan.language_tag,
            surface_text=surface,
            coverage=tuple(coverage),
            realized_clause_refs=tuple(realized),
            blocked_clause_refs=tuple(blocked),
            emission_proof_ref=self._proof_ref(proof),
        )

    def _render_segment(self, segment, clause, pack):
        if segment.kind is SegmentKind.SPACE:
            return " ", CoverageKind.SPACING, "", ""
        if segment.kind is SegmentKind.PUNCTUATION:
            return (
                segment.punctuation,
                CoverageKind.PUNCTUATION,
                "",
                "",
            )
        if segment.kind is SegmentKind.LEXEME:
            schema = pack.lexicalizations.get(segment.schema_ref)
            if schema is None:
                return None, CoverageKind.LEXICALIZATION, "", segment.schema_ref
            return (
                schema.surface(segment.form_key),
                CoverageKind.LEXICALIZATION,
                schema.semantic_key,
                schema.schema_id,
            )
        if segment.kind is SegmentKind.GRAMMATICAL_MORPHEME:
            schema = pack.morphemes.get(segment.schema_ref)
            if schema is None:
                return (
                    None,
                    CoverageKind.GRAMMATICAL_MORPHEME,
                    "",
                    segment.schema_ref,
                )
            return (
                schema.surface(segment.form_key),
                CoverageKind.GRAMMATICAL_MORPHEME,
                "",
                schema.schema_id,
            )

        role = clause.role(segment.role_key)
        if role is None:
            return None, CoverageKind.ROLE_VALUE, "", ""

        if segment.kind is SegmentKind.REFERRING_EXPRESSION:
            surface = pack.referring_expressions.get(role.value_ref, "")
            return (
                surface or None,
                CoverageKind.REFERRING_EXPRESSION,
                role.value_ref,
                segment.schema_ref,
            )
        if segment.kind is SegmentKind.ROLE_VALUE:
            if role.semantic_key:
                lexicalization = pack.lexicalization(
                    role.semantic_key, role.use_mode.value
                )
                if lexicalization is None:
                    return None, CoverageKind.ROLE_VALUE, role.value_ref, ""
                return (
                    lexicalization.surface(segment.form_key),
                    CoverageKind.ROLE_VALUE,
                    role.semantic_key,
                    lexicalization.schema_id,
                )
            return (
                role.surface_hint or role.value_ref,
                CoverageKind.ROLE_VALUE,
                role.value_ref,
                segment.schema_ref,
            )
        if segment.kind is SegmentKind.MENTION:
            if role.use_mode is not UseMode.MENTION or not role.surface_hint:
                return None, CoverageKind.MENTION, role.value_ref, ""
            return (
                role.surface_hint,
                CoverageKind.MENTION,
                role.value_ref,
                segment.schema_ref,
            )
        if segment.kind is SegmentKind.QUOTATION:
            if role.use_mode is not UseMode.QUOTE or not role.surface_hint:
                return None, CoverageKind.QUOTATION, role.value_ref, ""
            return (
                role.surface_hint,
                CoverageKind.QUOTATION,
                role.value_ref,
                segment.schema_ref,
            )
        return None, CoverageKind.ROLE_VALUE, "", ""

    @staticmethod
    def _fully_covered(surface: str, coverage: list[SpanCoverage]) -> bool:
        if not surface:
            return True
        cursor = 0
        for span in sorted(coverage, key=lambda item: (item.start, item.end)):
            if span.start != cursor or span.end <= span.start:
                return False
            if surface[span.start:span.end] != span.surface:
                return False
            cursor = span.end
        return cursor == len(surface)

    @staticmethod
    def _proof_ref(proof: SemanticEmissionProof) -> str:
        return (
            f"emission_proof:{proof.plan_ref}:"
            f"{proof.environment_fingerprint}:{proof.language_tag}"
        )
