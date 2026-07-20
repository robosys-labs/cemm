"""Compile form-lattice evidence into typed mention hypotheses.

This compiler never chooses an identity.  It preserves lexical ambiguity and
unknown spans as grounding frontiers so Phase 8 can solve them jointly.
"""
from __future__ import annotations

from collections import defaultdict
import unicodedata

from ..language.model import (
    FormLattice, SemanticContributionKind, SenseCandidate, SenseTargetKind, Span,
)
from ..language.registry import LanguageRegistry
from ..schema.model import SchemaClass, StorageKind, UseOperation, semantic_fingerprint
from .model import MentionHypothesis, MentionTargetClass


_SCHEMA_TARGETS = {
    SchemaClass.EVENT: MentionTargetClass.EVENT,
    SchemaClass.STATE_DIMENSION: MentionTargetClass.STATE,
    SchemaClass.STATE_VALUE: MentionTargetClass.STATE,
    SchemaClass.REFERENT_TYPE: MentionTargetClass.SCHEMA_TOPIC,
}


class MentionCompiler:
    def __init__(self, registry: LanguageRegistry | None = None) -> None:
        self.registry = registry

    def compile(
        self,
        lattice: FormLattice,
        *,
        context_ref: str,
        include_unresolved: bool = True,
    ) -> tuple[MentionHypothesis, ...]:
        forms = {item.candidate_ref: item for item in lattice.form_candidates}
        by_span: dict[tuple[int, int], list[SenseCandidate]] = defaultdict(list)
        for sense in lattice.sense_candidates:
            form = forms.get(sense.form_candidate_ref)
            if form is None or sense.use_operation != UseOperation.GROUND or not self._is_mention_sense(sense):
                continue
            by_span[(form.span.start, form.span.end)].append(sense)

        construction_roles: dict[str, list[tuple[str, str, tuple[str, ...]]]] = defaultdict(list)
        if self.registry is not None:
            for candidate in lattice.construction_candidates:
                record = self.registry.require_construction(
                    candidate.construction_ref, candidate.construction_revision
                )
                slots = {item.slot_ref: item for item in record.slots}
                for trigger_ref in candidate.trigger_refs:
                    construction_roles[trigger_ref].append((
                        candidate.candidate_ref, "predicate", candidate.evidence_refs
                    ))
                for slot_ref, filler_refs in candidate.slot_fillers:
                    slot = slots.get(slot_ref)
                    if slot is None:
                        continue
                    semantic_role = slot.semantic_port_ref or slot.slot_ref
                    for filler_ref in filler_refs:
                        construction_roles[filler_ref].append((
                            candidate.candidate_ref, semantic_role, candidate.evidence_refs
                        ))

        mentions: list[MentionHypothesis] = []
        covered: list[Span] = []
        for (start, end), senses in sorted(by_span.items()):
            span = Span(start, end)
            target_classes = tuple(sorted(
                {self._target_class(item) for item in senses}, key=lambda item: item.value
            ))
            target = target_classes[0] if len(target_classes) == 1 else MentionTargetClass.REFERENT
            expected_types = tuple(sorted({ref for item in senses for ref in item.expected_type_refs}))
            storage = tuple(sorted(
                {kind for item in senses for kind in self._storage_kinds(item)}, key=lambda item: item.value
            ))
            candidate_refs = {item.candidate_ref for item in senses}
            candidate_refs.update(item.form_candidate_ref for item in senses)
            construction_links = tuple(
                link
                for candidate_ref in sorted(candidate_refs)
                for link in construction_roles.get(candidate_ref, ())
            )
            construction_refs = tuple(sorted({item[0] for item in construction_links}))
            construction_role_values = tuple(sorted({item[1] for item in construction_links}))
            evidence = tuple(sorted(
                {ref for item in senses for ref in item.evidence_refs}
                | {ref for _, _, refs in construction_links for ref in refs}
            ))
            mention_ref = self._mention_ref(lattice.source_ref, span, tuple(item.candidate_ref for item in senses))
            lexical_source_role = next((
                str(item.metadata.get("source_role"))
                for item in senses if item.metadata.get("source_role")
            ), "")
            lexical_syntactic_role = next((
                str(item.metadata.get("syntactic_role"))
                for item in senses if item.metadata.get("syntactic_role")
            ), "")
            syntactic_role = (
                construction_role_values[0]
                if len(construction_role_values) == 1
                else lexical_syntactic_role
            )
            source_role = lexical_source_role
            mentions.append(MentionHypothesis(
                mention_ref=mention_ref,
                source_ref=lattice.source_ref,
                span=span,
                surface=lattice.source_content[start:end],
                normalized_surface=_normalize(lattice.source_content[start:end]),
                target_class=target,
                expected_type_refs=expected_types,
                expected_storage_kinds=storage,
                sense_candidate_refs=tuple(sorted(item.candidate_ref for item in senses)),
                construction_candidate_refs=construction_refs,
                context_ref=context_ref,
                syntactic_role=syntactic_role,
                source_role=source_role,
                salience=max(item.confidence for item in senses),
                evidence_refs=evidence,
                metadata={
                    "candidate_target_classes": tuple(item.value for item in target_classes),
                    "lexical_categories": tuple(sorted({item.lexical_category for item in senses if item.lexical_category})),
                    "structural_targets": tuple(sorted(
                        item.target_ref for item in senses
                        if item.target_kind == SenseTargetKind.STRUCTURAL and item.target_ref is not None
                    )),
                    "schema_target_refs": tuple(sorted(
                        item.target_ref for item in senses
                        if item.target_kind is not None
                        and item.target_kind != SenseTargetKind.STRUCTURAL
                        and item.target_ref is not None
                    )),
                    "schema_target_pins": tuple(sorted({
                        (item.target_ref, item.target_revision)
                        for item in senses
                        if item.target_kind is not None
                        and item.target_kind != SenseTargetKind.STRUCTURAL
                        and item.target_ref is not None
                        and item.target_revision is not None
                    })),
                    "deictic_roles": tuple(sorted({
                        str(item.metadata.get("deictic_role"))
                        for item in senses if item.metadata.get("deictic_role")
                    })),
                    "grounding_channels": tuple(sorted({
                        str(channel)
                        for item in senses
                        for channel in item.metadata.get("grounding_channels", ())
                    })),
                    "required_discourse_roles": tuple(sorted({
                        str(role)
                        for item in senses
                        for role in item.metadata.get("required_discourse_roles", ())
                    })),
                    "discourse_required": any(
                        bool(item.metadata.get("discourse_required")) for item in senses
                    ),
                    "candidate_syntactic_roles": construction_role_values,
                },
            ))
            covered.append(span)

        if include_unresolved:
            for observation in lattice.observations:
                if observation.category not in {"word", "number"}:
                    continue
                if any(_overlaps(observation.span, span) for span in covered):
                    continue
                mentions.append(MentionHypothesis(
                    mention_ref=self._mention_ref(lattice.source_ref, observation.span, (observation.observation_ref,)),
                    source_ref=lattice.source_ref,
                    span=observation.span,
                    surface=observation.original,
                    normalized_surface=observation.canonical,
                    target_class=MentionTargetClass.REFERENT,
                    context_ref=context_ref,
                    salience=0.35,
                    evidence_refs=observation.evidence_refs,
                    metadata={"unresolved_form": True, "script": observation.script},
                ))
        return tuple(sorted(mentions, key=lambda item: (item.span.start, item.span.end, item.mention_ref)))

    @staticmethod
    def _is_mention_sense(sense: SenseCandidate) -> bool:
        if bool(sense.metadata.get("mention")) or bool(sense.metadata.get("event_mention")):
            return True
        if any(
            item.contribution_kind == SemanticContributionKind.REFERENTIAL
            for item in sense.contributions
        ):
            return True
        if sense.target_kind == SenseTargetKind.REFERENT_TYPE:
            return True
        return bool(sense.metadata.get("mention_target_class"))

    @staticmethod
    def _target_class(sense: SenseCandidate) -> MentionTargetClass:
        explicit = sense.metadata.get("mention_target_class")
        if explicit:
            return MentionTargetClass(str(explicit))
        if sense.target_kind == SenseTargetKind.REFERENT_TYPE:
            return MentionTargetClass.REFERENT
        if sense.target_schema_class is not None:
            return _SCHEMA_TARGETS.get(sense.target_schema_class, MentionTargetClass.SCHEMA_TOPIC)
        return MentionTargetClass.REFERENT

    @staticmethod
    def _storage_kinds(sense: SenseCandidate) -> tuple[StorageKind, ...]:
        explicit = sense.metadata.get("storage_kinds")
        if explicit:
            return tuple(StorageKind(str(item)) for item in explicit)
        target = MentionCompiler._target_class(sense)
        return {
            MentionTargetClass.EVENT: (StorageKind.EVENT_OCCURRENCE,),
            MentionTargetClass.CLAIM: (StorageKind.EVENT_OCCURRENCE,),
            MentionTargetClass.PROPOSITION: (StorageKind.PROPOSITION,),
            MentionTargetClass.STATE: (StorageKind.STATE_OCCURRENCE,),
            MentionTargetClass.SCHEMA_TOPIC: (StorageKind.SCHEMA_TOPIC,),
        }.get(target, ())

    @staticmethod
    def _mention_ref(source_ref: str, span: Span, evidence: tuple[str, ...]) -> str:
        return "mention:" + semantic_fingerprint(
            "mention-ref", (source_ref, span.start, span.end, tuple(sorted(evidence))), 24
        )


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def _overlaps(left: Span, right: Span) -> bool:
    return left.start < right.end and right.start < left.end
