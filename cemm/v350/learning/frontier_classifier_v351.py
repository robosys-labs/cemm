"""Stage-11 prediction-error/frontier classification without semantic phrase branches."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..language.model import FormObservation
from ..runtime_kernel import FrontierClass
from ..schema.model import SchemaClass, SchemaLifecycleStatus, semantic_fingerprint
from ..storage.model import RecordKind
from .model import FrontierResolutionStatus, LearningFrontierRecord, PinnedRecord
from .phase14_model_v351 import (
    ExactStructuralCandidateSignal, NovelFormSignal, PredictionErrorFamily, PredictionErrorV351,
    SemanticPredictionV351, TeachingProjectionEvidenceV351,
)


@dataclass(frozen=True, slots=True)
class ClassifiedLearningInputsV351:
    predictions: tuple[SemanticPredictionV351, ...]
    errors: tuple[PredictionErrorV351, ...]
    frontiers: tuple[LearningFrontierRecord, ...]
    novel_form_signals: tuple[NovelFormSignal, ...]
    teaching_projections: tuple[TeachingProjectionEvidenceV351, ...]
    structural_signals: tuple[ExactStructuralCandidateSignal, ...]
    question_refs: tuple[str, ...]


class PredictionFrontierClassifierV351:
    """Classifies structural gaps; it never parses raw text for semantic meaning."""

    _TYPED_FRONTIER_FAMILIES = {
        FrontierClass.SEMANTIC_LEARNING: PredictionErrorFamily.SEMANTIC_DEFINITION,
        FrontierClass.GROUNDING_AMBIGUITY: PredictionErrorFamily.IDENTITY_GROUNDING,
        FrontierClass.REFERENCE_AMBIGUITY: PredictionErrorFamily.IDENTITY_GROUNDING,
        FrontierClass.RUNTIME_CAPABILITY: PredictionErrorFamily.CAPABILITY_DEPENDENCY,
        FrontierClass.BUDGET_INCOMPLETE: PredictionErrorFamily.DYNAMICS_PARAMETER,
        FrontierClass.TEMPORAL_REPLAY: PredictionErrorFamily.CONTEXT_TIME,
        FrontierClass.OPERATION_OUTCOME_UNKNOWN: PredictionErrorFamily.CAPABILITY_DEPENDENCY,
        FrontierClass.REALIZATION_GAP: PredictionErrorFamily.RESPONSE_REALIZATION,
    }

    # Compatibility classification for older RuntimeFrontier producers whose typed class is
    # too coarse. These are protocol contract identifiers, never user-language strings.
    _RUNTIME_FRONTIER_FAMILIES = {
        "form": PredictionErrorFamily.FORM_NORMALIZATION,
        "grounding": PredictionErrorFamily.IDENTITY_GROUNDING,
        "reference": PredictionErrorFamily.IDENTITY_GROUNDING,
        "semantic": PredictionErrorFamily.SEMANTIC_DEFINITION,
        "type": PredictionErrorFamily.SEMANTIC_DEFINITION,
        "state": PredictionErrorFamily.STATE_SCHEMA,
        "causal": PredictionErrorFamily.CAUSAL_STRUCTURE,
        "context": PredictionErrorFamily.CONTEXT_TIME,
        "time": PredictionErrorFamily.CONTEXT_TIME,
        "discourse": PredictionErrorFamily.DISCOURSE,
        "realization": PredictionErrorFamily.RESPONSE_REALIZATION,
        "response": PredictionErrorFamily.RESPONSE_REALIZATION,
        "non_convergence": PredictionErrorFamily.DYNAMICS_PARAMETER,
    }

    def classify(self, *, cycle, store) -> ClassifiedLearningInputsV351:
        predictions: list[SemanticPredictionV351] = []
        errors: list[PredictionErrorV351] = []
        frontiers: list[LearningFrontierRecord] = []
        novel_signals: list[NovelFormSignal] = []
        questions: set[str] = set()

        evidence_lattice = cycle.artifacts.get("evidence_lattice")
        lattice = None if evidence_lattice is None else getattr(evidence_lattice, "form_lattice", None)
        if lattice is not None:
            unresolved_spans = set(tuple(getattr(lattice, "unresolved_spans", ()) or ()))
            observations = tuple(getattr(lattice, "observations", ()) or ())
            pack = self._active_pack(store, cycle.target_language, lattice)
            for observation in observations:
                if not isinstance(observation, FormObservation) or observation.span not in unresolved_spans:
                    continue
                if observation.category in {"punctuation", "symbol", "whitespace"}:
                    continue
                evidence_refs = tuple(sorted(set(observation.evidence_refs)))
                lineage_refs = self._lineage_refs(cycle, evidence_refs)
                missing_contract = "language.form_or_lexicalization"
                target_ref = observation.observation_ref
                frontier_ref = "learning-frontier:" + semantic_fingerprint(
                    "phase14-frontier",
                    (missing_contract, target_ref, cycle.context_ref, cycle.permission_ref),
                    24,
                )
                expected_kinds = (RecordKind.LANGUAGE_FORM, RecordKind.LEXICAL_SENSE, RecordKind.FORM_SENSE_LINK)
                frontier = LearningFrontierRecord(
                    frontier_ref=frontier_ref,
                    missing_contract=missing_contract,
                    expected_record_kinds=expected_kinds,
                    expected_schema_classes=(),
                    accepted_anchor_types=("form_observation", "semantic_target_projection"),
                    evidence_refs=evidence_refs,
                    candidate_refs=(),
                    target_ref=target_ref,
                    dependency_depth=0,
                    sensitivity="normal",
                    best_question_uol_ref=None,
                    context_ref=cycle.context_ref,
                    permission_ref=cycle.permission_ref,
                    resolution_status=FrontierResolutionStatus.OPEN,
                    metadata={
                        "phase14_family": PredictionErrorFamily.LEXICALIZATION.value,
                        "observation_ref": observation.observation_ref,
                        "language_tag": cycle.target_language or str(getattr(lattice, "metadata", {}).get("turn_language_tag") or ""),
                    },
                )
                frontiers.append(frontier)
                predicted_ref = "prediction:known-form:" + observation.observation_ref
                predictions.append(SemanticPredictionV351(
                    prediction_ref=predicted_ref,
                    family=PredictionErrorFamily.FORM_NORMALIZATION,
                    expected_refs=("contract:resolvable-language-form",),
                    source_artifact_refs=(str(getattr(lattice, "lattice_ref", "form-lattice")),),
                    confidence=1.0,
                    context_ref=cycle.context_ref,
                    permission_ref=cycle.permission_ref,
                ))
                errors.append(PredictionErrorV351(
                    error_ref="prediction-error:" + semantic_fingerprint(
                        "unknown-form-error-v351", (frontier_ref, evidence_refs), 24
                    ),
                    family=PredictionErrorFamily.FORM_NORMALIZATION,
                    predicted_refs=("contract:resolvable-language-form",),
                    observed_refs=(observation.observation_ref,),
                    missing_refs=("language_form", "lexical_target"),
                    conflicting_refs=(),
                    evidence_refs=evidence_refs,
                    source_lineage_refs=lineage_refs,
                    context_ref=cycle.context_ref,
                    permission_ref=cycle.permission_ref,
                    frontier_ref=frontier_ref,
                ))
                if pack is not None:
                    pack_pin = PinnedRecord(
                        RecordKind.LANGUAGE_PACK, pack.record_ref, pack.revision, pack.record_fingerprint
                    )
                    language_tag = str(getattr(pack.payload, "language_tag"))
                    novel_signals.append(NovelFormSignal(
                        signal_ref="novel-form-signal:" + semantic_fingerprint(
                            "novel-form-signal-v351",
                            (observation.observation_ref, pack_pin.key, observation.canonical, evidence_refs),
                            24,
                        ),
                        observation_ref=observation.observation_ref,
                        pack_pin=pack_pin,
                        language_tag=language_tag,
                        written_form=observation.original,
                        normalized_form=observation.canonical,
                        script=observation.script,
                        category=observation.category,
                        token_count=1,
                        evidence_refs=evidence_refs,
                        source_lineage_refs=lineage_refs,
                        permission_ref=cycle.permission_ref,
                    ))
                questions.add("learning-question:semantic-target:" + observation.observation_ref)

        # Explicit construction-authorized projections are typed artifacts, not strings.
        teaching = tuple(cycle.artifacts.get("teaching_projection_evidence", ()) or ())
        teaching = tuple(item for item in teaching if isinstance(item, TeachingProjectionEvidenceV351))
        structural = tuple(cycle.artifacts.get("learning_induction_signals", ()) or ())
        structural = tuple(item for item in structural if isinstance(item, ExactStructuralCandidateSignal))

        # Preserve pre-existing typed runtime frontiers and classify only by their
        # protocol-level missing-contract class. No surface text is inspected.
        runtime_frontiers = tuple(cycle.artifacts.get("runtime_frontiers", ()) or ())
        for item in runtime_frontiers:
            missing = str(getattr(item, "missing_contract", "") or "")
            typed_class = getattr(item, "frontier_class", None)
            family = self._TYPED_FRONTIER_FAMILIES.get(typed_class)
            if family is None or typed_class == FrontierClass.SEMANTIC_LEARNING:
                family = self._family_for_contract(missing) or family
            if family is None:
                continue
            ref = str(getattr(item, "frontier_ref", "") or "")
            evidence = tuple(sorted(set(getattr(item, "evidence_refs", ()) or ())))
            errors.append(PredictionErrorV351(
                error_ref="prediction-error:" + semantic_fingerprint(
                    "runtime-frontier-error-v351", (ref, family.value, evidence), 24
                ),
                family=family,
                predicted_refs=("contract:" + missing,),
                observed_refs=tuple(sorted(set(getattr(item, "target_refs", ()) or ()))),
                missing_refs=(missing,),
                conflicting_refs=(),
                evidence_refs=evidence,
                source_lineage_refs=self._lineage_refs(cycle, evidence),
                context_ref=cycle.context_ref,
                permission_ref=cycle.permission_ref,
                frontier_ref=ref or None,
            ))

        # Deduplicate structurally. A repeated observation in one pass is one frontier,
        # while independent evidence is retained inside evidence refs/lineage.
        frontier_map = {item.frontier_ref: item for item in frontiers}
        error_map = {item.error_ref: item for item in errors}
        prediction_map = {item.prediction_ref: item for item in predictions}
        novel_map = {item.signal_ref: item for item in novel_signals}
        return ClassifiedLearningInputsV351(
            predictions=tuple(prediction_map[key] for key in sorted(prediction_map)),
            errors=tuple(error_map[key] for key in sorted(error_map)),
            frontiers=tuple(frontier_map[key] for key in sorted(frontier_map)),
            novel_form_signals=tuple(novel_map[key] for key in sorted(novel_map)),
            teaching_projections=tuple(sorted(teaching, key=lambda item: item.projection_ref)),
            structural_signals=tuple(sorted(structural, key=lambda item: item.signal_ref)),
            question_refs=tuple(sorted(questions)),
        )

    @staticmethod
    def _active_pack(store, target_language: str, lattice):
        language_tag = target_language or str(getattr(lattice, "metadata", {}).get("turn_language_tag") or "")
        if not language_tag:
            return None
        matches = []
        try:
            records = store.records(RecordKind.LANGUAGE_PACK)
        except Exception:
            return None
        for stored in records:
            payload = stored.payload
            if (
                getattr(payload, "language_tag", None) == language_tag
                and getattr(payload, "lifecycle_status", None) == SchemaLifecycleStatus.ACTIVE
            ):
                matches.append(stored)
        if len(matches) != 1:
            return None
        return matches[0]

    @staticmethod
    def _lineage_refs(cycle, evidence_refs):
        envelopes = tuple(cycle.artifacts.get("evidence_envelopes", ()) or ())
        by_ref = {str(getattr(item, "evidence_ref", "")): item for item in envelopes}
        lineages = set()
        for ref in evidence_refs:
            envelope = by_ref.get(ref)
            if envelope is None:
                lineages.add(ref)
                continue
            values = tuple(getattr(envelope, "lineage_refs", ()) or ())
            lineages.update(values or (str(getattr(envelope, "source_ref", ref)),))
        return tuple(sorted(lineages))

    @classmethod
    def _family_for_contract(cls, missing: str):
        family_key = missing.casefold().replace("-", "_")
        for prefix, family in cls._RUNTIME_FRONTIER_FAMILIES.items():
            if family_key.startswith(prefix) or (":" + prefix) in family_key or ("_" + prefix) in family_key:
                return family
        return None


__all__ = ["ClassifiedLearningInputsV351", "PredictionFrontierClassifierV351"]
