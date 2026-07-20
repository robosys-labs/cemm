"""Data-driven construction matching over form/sense and syntax evidence."""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations, product
from typing import Iterable

from ..schema.model import semantic_fingerprint
from .model import (
    ConstructionCandidate,
    ConstructionKind,
    ConstructionRecord,
    ConstituencyParseEvidence,
    DependencyParseEvidence,
    FormCandidate,
    FormObservation,
    SenseCandidate,
    Span,
)
from .registry import LanguageRegistry


class ConstructionMatcher:
    """Match reviewed constructions without language-specific control flow.

    A construction's structural kind chooses a generic graph operation. The
    triggers, lexical categories, syntax labels, slot mapping, and output schema
    remain reviewed data. Matching is anchored to exact trigger candidates so
    repeated clauses produce separate construction instances rather than one
    utterance-wide frame.
    """

    def __init__(
        self,
        registry: LanguageRegistry,
        *,
        maximum_candidates_per_construction: int = 128,
        maximum_fillers_per_slot: int = 4,
    ) -> None:
        if maximum_candidates_per_construction < 1:
            raise ValueError("maximum_candidates_per_construction must be positive")
        if maximum_fillers_per_slot < 1:
            raise ValueError("maximum_fillers_per_slot must be positive")
        self.registry = registry
        self.maximum_candidates_per_construction = maximum_candidates_per_construction
        self.maximum_fillers_per_slot = maximum_fillers_per_slot

    def match(
        self,
        observations: tuple[FormObservation, ...],
        forms: tuple[FormCandidate, ...],
        senses: tuple[SenseCandidate, ...],
        dependencies: tuple[DependencyParseEvidence, ...] = (),
        constituencies: tuple[ConstituencyParseEvidence, ...] = (),
    ) -> tuple[ConstructionCandidate, ...]:
        by_form_ref: dict[str, list[FormCandidate]] = defaultdict(list)
        by_sense_ref: dict[str, list[SenseCandidate]] = defaultdict(list)
        for item in forms:
            by_form_ref[item.form_ref].append(item)
        for item in senses:
            by_sense_ref[item.sense_ref].append(item)
        for values in by_form_ref.values():
            values.sort(key=lambda item: item.candidate_ref)
        for values in by_sense_ref.values():
            values.sort(key=lambda item: item.candidate_ref)

        category_by_form_candidate = {
            item.candidate_ref: dict(
                self.registry.require_form(item.form_ref, item.form_revision).feature_values
            ).get("category", "")
            for item in forms
        }
        class_by_sense_candidate = {
            item.candidate_ref: item.target_schema_class for item in senses
        }
        form_map = {item.candidate_ref: item for item in forms}
        sense_map = {item.candidate_ref: item for item in senses}
        sense_to_form = {
            item.candidate_ref: form_map.get(item.form_candidate_ref) for item in senses
        }

        result: list[ConstructionCandidate] = []
        for construction in self.registry.active_constructions():
            match_allowed, match_authority, match_evidence = (
                self.registry.construction_match_authority(construction)
            )
            if not match_allowed:
                continue
            trigger_groups = self._trigger_groups(
                construction, by_form_ref, by_sense_ref
            )
            if not trigger_groups:
                continue
            produced = 0
            for trigger_refs in trigger_groups:
                slot_options = self._slot_options(
                    construction,
                    trigger_refs,
                    forms,
                    senses,
                    dependencies,
                    constituencies,
                    category_by_form_candidate,
                    class_by_sense_candidate,
                )
                if slot_options is None:
                    continue
                for fillers in slot_options:
                    if produced >= self.maximum_candidates_per_construction:
                        break
                    if not self._fillers_are_compatible(
                        fillers,
                        form_map=form_map,
                        sense_to_form=sense_to_form,
                        allow_shared=bool(construction.metadata.get("allow_shared_fillers")),
                    ):
                        continue
                    all_refs = (*trigger_refs, *(ref for _, refs in fillers for ref in refs))
                    spans = tuple(
                        span
                        for ref in all_refs
                        if (span := _candidate_span(ref, form_map, sense_to_form)) is not None
                    )
                    if not spans:
                        continue
                    span = Span(
                        min(item.start for item in spans),
                        max(item.end for item in spans),
                    )
                    gaps: tuple[str, ...] = ()
                    if construction.construction_kind == ConstructionKind.ELLIPSIS:
                        filler_map = dict(fillers)
                        gaps = tuple(
                            f"gap:{construction.construction_ref}:{slot.slot_ref}"
                            for slot in construction.slots
                            if slot.optional_when_licensed
                            and not filler_map.get(slot.slot_ref)
                        )
                        if not gaps:
                            continue
                    evidence = tuple(sorted(set(
                        self._evidence(
                            all_refs,
                            forms,
                            senses,
                            dependencies,
                            constituencies,
                        )
                    ) | set(match_evidence) | {
                        f"construction-match-authority:{match_authority}"
                    }))
                    candidate_ref = "construction-candidate:" + semantic_fingerprint(
                        "construction-candidate",
                        (
                            construction.construction_ref,
                            construction.revision,
                            trigger_refs,
                            fillers,
                            span.start,
                            span.end,
                            gaps,
                        ),
                        24,
                    )
                    result.append(ConstructionCandidate(
                        candidate_ref=candidate_ref,
                        construction_ref=construction.construction_ref,
                        construction_revision=construction.revision,
                        trigger_refs=trigger_refs,
                        slot_fillers=fillers,
                        span=span,
                        confidence=self._confidence(
                            all_refs, forms, senses, dependencies, constituencies
                        ),
                        evidence_refs=evidence
                        or (f"construction:{construction.construction_ref}",),
                        gap_refs=gaps,
                    ))
                    produced += 1
                if produced >= self.maximum_candidates_per_construction:
                    break
        result.sort(
            key=lambda item: (
                item.span.start,
                item.span.end,
                item.construction_ref,
                item.trigger_refs,
                item.candidate_ref,
            )
        )
        return tuple(result)

    @staticmethod
    def _trigger_groups(
        construction: ConstructionRecord,
        forms: dict[str, list[FormCandidate]],
        senses: dict[str, list[SenseCandidate]],
    ) -> tuple[tuple[str, ...], ...]:
        dimensions: list[tuple[str, ...]] = []
        for ref in construction.trigger_form_refs:
            values = tuple(item.candidate_ref for item in forms.get(ref, ()))
            if not values:
                return ()
            dimensions.append(values)
        for ref in construction.trigger_sense_refs:
            values = tuple(item.candidate_ref for item in senses.get(ref, ()))
            if not values:
                return ()
            dimensions.append(values)
        if not dimensions:
            return ((),)
        groups = {
            tuple(items)
            for items in product(*dimensions)
            if len(items) == len(set(items))
        }
        return tuple(sorted(groups))

    def _slot_options(
        self,
        construction: ConstructionRecord,
        trigger_refs: tuple[str, ...],
        forms: tuple[FormCandidate, ...],
        senses: tuple[SenseCandidate, ...],
        dependencies: tuple[DependencyParseEvidence, ...],
        constituencies: tuple[ConstituencyParseEvidence, ...],
        category_by_form_candidate,
        class_by_sense_candidate,
    ) -> tuple[tuple[tuple[str, tuple[str, ...]], ...], ...] | None:
        form_by_candidate = {item.candidate_ref: item for item in forms}
        sense_by_candidate = {item.candidate_ref: item for item in senses}
        sense_to_form = {
            item.candidate_ref: form_by_candidate.get(item.form_candidate_ref)
            for item in senses
        }
        candidate_spans = {item.candidate_ref: item.span for item in forms}
        candidate_spans.update({
            item.candidate_ref: sense_to_form[item.candidate_ref].span
            for item in senses
            if sense_to_form.get(item.candidate_ref) is not None
        })
        arcs_by_relation: dict[str, list] = defaultdict(list)
        for parse in dependencies:
            for arc in parse.arcs:
                arcs_by_relation[arc.relation].append(arc)
        nodes_by_label: dict[str, list] = defaultdict(list)
        for parse in constituencies:
            for node in parse.nodes:
                nodes_by_label[node.label].append(node)

        def candidate_observations(ref: str) -> set[str]:
            if ref in form_by_candidate:
                return set(form_by_candidate[ref].observation_refs)
            form = sense_to_form.get(ref)
            return set() if form is None else set(form.observation_refs)

        trigger_observations = set().union(
            *(candidate_observations(ref) for ref in trigger_refs)
        ) if trigger_refs else set()

        def syntax_licensed(ref, slot) -> bool:
            observations = candidate_observations(ref)
            if slot.dependency_relations:
                arcs = [
                    arc
                    for relation in slot.dependency_relations
                    for arc in arcs_by_relation.get(relation, ())
                ]

                def arc_matches(arc) -> bool:
                    candidate_head = arc.head_observation_ref in observations
                    candidate_dependent = arc.dependent_observation_ref in observations
                    if slot.anchor_to_trigger and trigger_observations:
                        anchored = (
                            candidate_head
                            and arc.dependent_observation_ref in trigger_observations
                        ) or (
                            candidate_dependent
                            and arc.head_observation_ref in trigger_observations
                        )
                        if not anchored:
                            return False
                    if slot.dependency_position == "head":
                        return candidate_head
                    if slot.dependency_position == "dependent":
                        return candidate_dependent
                    return candidate_head or candidate_dependent

                if not any(arc_matches(arc) for arc in arcs):
                    return False
            if slot.constituency_labels:
                span = candidate_spans.get(ref)
                nodes = [
                    node
                    for label in slot.constituency_labels
                    for node in nodes_by_label.get(label, ())
                ]
                if span is None or not any(
                    node.span.start <= span.start and span.end <= node.span.end
                    for node in nodes
                ):
                    return False
            return True

        options_by_slot: list[tuple[tuple[str, tuple[str, ...]], ...]] = []
        for slot in construction.slots:
            eligible_senses = []
            for sense in senses:
                stored = self.registry.require_sense(
                    sense.sense_ref, sense.sense_revision
                )
                if stored.pack_ref != construction.pack_ref:
                    continue
                if (
                    slot.accepted_categories
                    and sense.lexical_category not in slot.accepted_categories
                ):
                    continue
                target_class = class_by_sense_candidate.get(sense.candidate_ref)
                if (
                    slot.accepted_target_classes
                    and target_class not in slot.accepted_target_classes
                ):
                    continue
                if syntax_licensed(sense.candidate_ref, slot):
                    eligible_senses.append(sense.candidate_ref)

            semantic_form_refs = {
                sense_by_candidate[ref].form_candidate_ref
                for ref in eligible_senses
            }
            eligible_forms = []
            if not slot.accepted_target_classes:
                for form in forms:
                    stored = self.registry.require_form(
                        form.form_ref, form.form_revision
                    )
                    if stored.pack_ref != construction.pack_ref:
                        continue
                    if form.candidate_ref in semantic_form_refs:
                        continue
                    category = category_by_form_candidate.get(
                        form.candidate_ref, ""
                    )
                    if (
                        slot.accepted_categories
                        and category not in slot.accepted_categories
                    ):
                        continue
                    if syntax_licensed(form.candidate_ref, slot):
                        eligible_forms.append(form.candidate_ref)

            refs = tuple(sorted(set((*eligible_senses, *eligible_forms))))
            minimum = 0 if slot.optional_when_licensed else slot.minimum
            maximum = len(refs) if slot.maximum is None else min(
                len(refs), slot.maximum
            )
            maximum = min(maximum, self.maximum_fillers_per_slot)
            if len(refs) < minimum or maximum < minimum:
                return None
            slot_options = tuple(
                (slot.slot_ref, tuple(choice))
                for size in range(minimum, maximum + 1)
                for choice in combinations(refs, size)
            )
            if not slot_options:
                return None
            options_by_slot.append(slot_options)

        combinations_by_slot = []
        for selected in product(*options_by_slot):
            combinations_by_slot.append(tuple(selected))
            if len(combinations_by_slot) >= self.maximum_candidates_per_construction:
                break
        return tuple(combinations_by_slot)

    @staticmethod
    def _fillers_are_compatible(
        fillers: tuple[tuple[str, tuple[str, ...]], ...],
        *,
        form_map: dict[str, FormCandidate],
        sense_to_form: dict[str, FormCandidate | None],
        allow_shared: bool,
    ) -> bool:
        if allow_shared:
            return True
        occupied: set[str] = set()
        for _, refs in fillers:
            observations: set[str] = set()
            for ref in refs:
                form = form_map.get(ref) or sense_to_form.get(ref)
                if form is not None:
                    observations.update(form.observation_refs)
            if occupied.intersection(observations):
                return False
            occupied.update(observations)
        return True

    @staticmethod
    def _evidence(
        refs: tuple[str, ...],
        forms: tuple[FormCandidate, ...],
        senses: tuple[SenseCandidate, ...],
        dependencies: tuple[DependencyParseEvidence, ...],
        constituencies: tuple[ConstituencyParseEvidence, ...],
    ) -> tuple[str, ...]:
        wanted = set(refs)
        return tuple(sorted({
            *(ref for item in forms if item.candidate_ref in wanted for ref in item.evidence_refs),
            *(ref for item in senses if item.candidate_ref in wanted for ref in item.evidence_refs),
            *(item.parse_ref for item in dependencies),
            *(item.parse_ref for item in constituencies),
        }))

    @staticmethod
    def _confidence(refs, forms, senses, dependencies, constituencies) -> float:
        wanted = set(refs)
        values = [
            item.confidence for item in forms if item.candidate_ref in wanted
        ]
        values.extend(
            item.confidence for item in senses if item.candidate_ref in wanted
        )
        values.extend(item.confidence for item in dependencies)
        values.extend(item.confidence for item in constituencies)
        return min(values) if values else 0.5


def _candidate_span(
    ref: str,
    form_map: dict[str, FormCandidate],
    sense_to_form: dict[str, FormCandidate | None],
) -> Span | None:
    form = form_map.get(ref) or sense_to_form.get(ref)
    return None if form is None else form.span
