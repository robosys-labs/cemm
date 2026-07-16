"""Alternative-preserving semantic-forest composer.

Language constructions are treated as evidence sources, not sentence-level
meaning authorities.  This layer keeps partial predications, attaches generic
modifier evidence, preserves unresolved fragments and applies deictic/context
qualifiers without inspecting language-specific words.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import timedelta
from typing import Any

from .canonical_composer import CanonicalSemanticComposer
from .candidate_graph import CandidatePredication, CandidateProposition, DiscourseRelation
from ..model.identity import TimeExtent
from ..model.predication import Predication
from ..model.proposition import Proposition
from ..model.role_binding import RoleBinding


class SemanticForestComposer(CanonicalSemanticComposer):
    composer_version = "semantic-forest-v3.4.6"

    def compose(self, evidence, *, context_snapshot=None):
        graph = super().compose(evidence, context_snapshot=context_snapshot)
        predications = list(graph.candidate_predications)
        propositions = list(graph.candidate_propositions)
        discourse = list(graph.discourse_relations)

        predications = self._apply_relation_attachments(
            predications,
            evidence,
        )
        propositions = self._apply_temporal_qualifiers(
            propositions,
            predications,
            evidence,
            context_snapshot,
        )
        discourse.extend(self._contextual_discourse_relations(
            propositions,
            predications,
            evidence,
            context_snapshot,
        ))

        content_indices = self._content_indices(evidence)
        coverage = {
            candidate.predication.id: (
                len(set(candidate.source_token_indices) & content_indices)
                / max(1, len(content_indices))
            )
            for candidate in predications
        }
        return replace(
            graph,
            candidate_predications=tuple(predications),
            candidate_propositions=tuple(propositions),
            discourse_relations=tuple(self._dedupe_discourse(discourse)),
            semantic_spans=tuple(getattr(evidence, "semantic_spans", ()) or ()),
            relation_candidates=tuple(
                getattr(evidence, "relation_candidates", ()) or ()
            ),
            unresolved_fragments=tuple(
                getattr(evidence, "unresolved_fragments", ()) or ()
            ),
            coverage_by_predication=tuple(sorted(coverage.items())),
            content_token_count=len(content_indices),
        )

    def _apply_relation_attachments(self, predications, evidence):
        relations = tuple(getattr(evidence, "relation_candidates", ()) or ())
        spans = {
            span.span_ref: span
            for span in tuple(getattr(evidence, "semantic_spans", ()) or ())
        }
        construction_semantics = self._construction_semantics(evidence)
        result = list(predications)
        for relation in relations:
            role_key = str(getattr(relation, "target_role_key", ""))
            target_predicate = str(
                getattr(relation, "target_predicate_key", "")
            )
            if not role_key or not target_predicate:
                continue
            span = spans.get(str(getattr(relation, "source_span_ref", "")))
            if span is None:
                continue
            filler = f"ref:span:{','.join(str(v) for v in span.token_indices)}"
            for index, candidate in enumerate(result):
                predicate_key = construction_semantics.get(
                    tuple(candidate.source_token_indices),
                    "",
                )
                if predicate_key != target_predicate:
                    continue
                if not self._same_clause(
                    candidate.source_token_indices,
                    span.token_indices,
                    evidence,
                ):
                    continue
                role_ref = self._role_ref(role_key)
                if any(
                    binding.role_schema_ref == role_ref
                    for binding in candidate.predication.bindings
                ):
                    continue
                predication = replace(
                    candidate.predication,
                    bindings=tuple((
                        *candidate.predication.bindings,
                        RoleBinding(
                            role_schema_ref=role_ref,
                            filler_ref=filler,
                            confidence=float(getattr(relation, "confidence", 0.6)),
                            evidence_refs=(
                                str(getattr(relation, "relation_ref", "")),
                            ),
                        ),
                    )),
                )
                result[index] = replace(candidate, predication=predication)
        return result

    def _apply_temporal_qualifiers(
        self,
        propositions,
        predications,
        evidence,
        context_snapshot,
    ):
        if context_snapshot is None:
            return propositions
        temporal_spans = [
            span for span in tuple(getattr(evidence, "semantic_spans", ()) or ())
            if dict(getattr(span, "features", {}) or {}).get("semantic_family")
            == "temporal_deictic"
        ]
        if not temporal_spans:
            return propositions
        predication_by_ref = {
            item.predication.id: item for item in predications
        }
        result = []
        for candidate in propositions:
            predication = predication_by_ref.get(
                candidate.proposition.predication_ref
            )
            valid_time = candidate.proposition.valid_time
            if predication is not None and valid_time is None:
                compatible = [
                    span for span in temporal_spans
                    if self._same_clause(
                        predication.source_token_indices,
                        span.token_indices,
                        evidence,
                    )
                ]
                if compatible:
                    selected = max(
                        compatible,
                        key=lambda span: float(getattr(span, "confidence", 0.0)),
                    )
                    valid_time = self._resolve_deictic_time(
                        dict(getattr(selected, "features", {}) or {}),
                        context_snapshot.clock_observation,
                    )
            if valid_time is not candidate.proposition.valid_time:
                candidate = replace(
                    candidate,
                    proposition=replace(
                        candidate.proposition,
                        valid_time=valid_time,
                    ),
                )
            result.append(candidate)
        return result

    def _contextual_discourse_relations(
        self,
        propositions,
        predications,
        evidence,
        context_snapshot,
    ):
        if context_snapshot is None:
            return ()
        correction_present = any(
            dict(getattr(span, "features", {}) or {}).get("discourse_relation")
            == "correction"
            for span in tuple(getattr(evidence, "semantic_spans", ()) or ())
        )
        if not correction_present or not propositions:
            return ()
        construction_semantics = self._construction_semantics(evidence)
        predication_by_ref = {
            item.predication.id: item for item in predications
        }
        previous = tuple(getattr(context_snapshot, "recent_clauses", ()) or ())
        result = []
        for proposition in propositions:
            predication = predication_by_ref.get(
                proposition.proposition.predication_ref
            )
            if predication is None:
                continue
            predicate_key = construction_semantics.get(
                tuple(predication.source_token_indices),
                "",
            )
            target = next(
                (
                    clause for clause in reversed(previous)
                    if not predicate_key or clause.predicate_key == predicate_key
                ),
                None,
            )
            if target is None:
                continue
            result.append(DiscourseRelation(
                source_ref=proposition.proposition.id,
                target_ref=target.proposition_ref,
                relation_kind="correction",
                confidence=0.9,
                from_pragmatic_cue=True,
            ))
        return tuple(result)

    @staticmethod
    def _construction_semantics(evidence) -> dict[tuple[int, ...], str]:
        result = {}
        for construction in tuple(
            getattr(evidence, "construction_candidates", ()) or ()
        ):
            result[tuple(construction.source_token_indices)] = str(
                construction.predicate_schema_ref
            )
        return result

    @staticmethod
    def _content_indices(evidence) -> set[int]:
        result = set()
        for index, token in enumerate(evidence.token_stream.tokens):
            kind = getattr(token.kind, "value", str(token.kind))
            if kind not in {
                "punctuation", "whitespace", "quote_open", "quote_close"
            }:
                result.add(index)
        return result

    @staticmethod
    def _same_clause(left, right, evidence) -> bool:
        if not left or not right:
            return False
        tokens = evidence.token_stream.tokens
        left_offsets = (
            min(tokens[i].start_offset for i in left),
            max(tokens[i].end_offset for i in left),
        )
        right_offsets = (
            min(tokens[i].start_offset for i in right),
            max(tokens[i].end_offset for i in right),
        )
        return any(
            left_offsets[0] >= clause.start_offset
            and left_offsets[1] <= clause.end_offset
            and right_offsets[0] >= clause.start_offset
            and right_offsets[1] <= clause.end_offset
            for clause in evidence.token_stream.clause_boundaries
        )

    @staticmethod
    def _resolve_deictic_time(features: dict[str, Any], clock):
        deictic = str(features.get("deictic", ""))
        start = clock.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        if deictic == "deictic:previous_day":
            start -= timedelta(days=1)
            end -= timedelta(days=1)
        elif deictic == "deictic:next_day":
            start += timedelta(days=1)
            end += timedelta(days=1)
        elif deictic == "daypart:morning":
            start = clock.replace(hour=5, minute=0, second=0, microsecond=0)
            end = clock.replace(hour=12, minute=0, second=0, microsecond=0)
        elif deictic == "daypart:evening":
            start = clock.replace(hour=17, minute=0, second=0, microsecond=0)
            end = clock.replace(hour=23, minute=59, second=59, microsecond=999999)
        return TimeExtent(start=start, end=end, granularity="interval")

    @staticmethod
    def _dedupe_discourse(items):
        result = []
        seen = set()
        for item in items:
            key = (item.source_ref, item.target_ref, item.relation_kind)
            if key not in seen:
                seen.add(key)
                result.append(item)
        return result
