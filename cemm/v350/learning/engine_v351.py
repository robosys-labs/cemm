"""Canonical Stage-11 Phase-14 learning engine.

Stage 11 observes *typed runtime artifacts*, classifies prediction error, and prepares
non-authoritative candidate work.  It performs no durable write and no promotion.
"""
from __future__ import annotations

from collections import defaultdict

from ..language.model import SenseTargetKind
from ..schema.model import SchemaClass, UseOperation, semantic_fingerprint
from .frontier_classifier_v351 import PredictionFrontierClassifierV351
from .inducers_v351 import (
    ConstructionInducer,
    FormNormalizationInducer,
    LexicalizationInducer,
    ParameterCandidateTrainer,
    SemanticDefinitionInducer,
    SenseInducer,
    StateSchemaInducer,
    TransitionCausalInducer, candidate_pin,
)
from .phase14_model_v351 import (
    ConstructionPatternSignal,
    ExactStructuralCandidateSignal,
    LearningCandidateWorkItemV351,
    ParameterTrainingExample,
    PredictionErrorFamily,
    TeachingProjectionEvidenceV351,
)
from .teaching_v351 import TeachingProjectionExtractorV351


class Phase14LearningEngineV351:
    RUNTIME_ABI = "v351-phase14"
    SERVICE_KIND = "prediction_error_learning_engine_v351"

    def __init__(self) -> None:
        # Explicit inventory: Phase 14 must never become an empty/default inducer registry.
        self.form_normalization = FormNormalizationInducer()
        self.lexicalization = LexicalizationInducer()
        self.sense = SenseInducer()
        self.construction = ConstructionInducer()
        self.semantic_definition = SemanticDefinitionInducer()
        self.state_schema = StateSchemaInducer()
        self.transition_causal = TransitionCausalInducer()
        self.parameter_trainer = ParameterCandidateTrainer()
        self.classifier = PredictionFrontierClassifierV351()
        self.teaching_extractor = TeachingProjectionExtractorV351()

    def advance(self, *, cycle, capability, store, effect_store, semantic_capabilities):
        del capability, effect_store, semantic_capabilities  # Stage 11 is pure candidate work.
        classified = self.classifier.classify(cycle=cycle, store=store)
        extracted = self.teaching_extractor.extract(cycle=cycle, store=store)
        definition_extracted = self.teaching_extractor.extract_definitions(cycle=cycle, store=store)

        novel_by_ref = {item.signal_ref: item for item in classified.novel_form_signals}
        projection_context = {}
        projection_by_form = defaultdict(list)
        for item in extracted:
            novel_by_ref[item.form_signal.signal_ref] = item.form_signal
            projection_by_form[item.projection.form_signal_ref].append(item.projection)
            projection_context[item.projection.projection_ref] = item
        for projection in classified.teaching_projections:
            projection_by_form[projection.form_signal_ref].append(projection)
        definition_observations = {item.form_signal.observation_ref for item in definition_extracted}

        frontiers_by_target = {
            item.target_ref: item for item in classified.frontiers if item.target_ref is not None
        }
        work: dict[str, LearningCandidateWorkItemV351] = {}

        # Meaningful lexical learning path: an unresolved observation is paired only with
        # an exact construction-authorized target projection. No English word or template
        # is recognized here.
        for signal_ref in sorted(novel_by_ref):
            signal = novel_by_ref[signal_ref]
            projections = tuple(sorted(
                projection_by_form.get(signal_ref, ()), key=lambda item: item.projection_ref
            ))
            frontier = frontiers_by_target.get(signal.observation_ref)
            if frontier is None:
                continue
            if projections:
                # Multiple non-equivalent targets for one observed form remain separate
                # candidate packages; promotion competence/review decides, never Stage 11.
                for projection in projections:
                    proposals = self.lexicalization.induce(signal, projection)
                    if not proposals:
                        continue
                    context = projection_context.get(projection.projection_ref)
                    metadata = dict(projection.metadata)
                    review_refs = (
                        tuple(context.review_refs) if context is not None
                        else tuple(metadata.get("review_refs", ()) or ())
                    )
                    authorization_refs = (
                        tuple(context.authorization_refs) if context is not None
                        else tuple(metadata.get("authorization_refs", ()) or ())
                    )
                    risk_refs = (
                        tuple(context.risk_refs) if context is not None
                        else tuple(metadata.get("risk_refs", ()) or ())
                    )
                    policy_ref = (
                        context.promotion_policy_ref if context is not None
                        else str(metadata.get("promotion_policy_ref") or "policy:v351:reviewed-learning-promotion")
                    )
                    work_ref = "learning-work:" + semantic_fingerprint(
                        "phase14-lexicalization-work",
                        (frontier.frontier_ref, projection.projection_ref, tuple(p.proposer_ref for p in proposals)),
                        24,
                    )
                    work[work_ref] = LearningCandidateWorkItemV351(
                        work_ref=work_ref,
                        frontier=frontier,
                        proposals=proposals,
                        source_lineage_refs=projection.source_lineage_refs,
                        requested_uses=projection.requested_uses,
                        competence_case_refs=projection.competence_case_refs,
                        review_refs=review_refs,
                        authorization_refs=authorization_refs,
                        risk_refs=risk_refs,
                        promotion_policy_ref=policy_ref,
                    )
            else:
                if signal.observation_ref in definition_observations:
                    # A reviewed definition projection owns this unresolved observation; do
                    # not also create an unrelated form-only package for the same evidence.
                    continue
                # It is safe to preserve a form candidate before semantics is known, but it
                # receives no executable requested use and therefore cannot self-promote.
                proposals = self.form_normalization.induce(signal)
                work_ref = "learning-work:" + semantic_fingerprint(
                    "phase14-form-only-work", (frontier.frontier_ref, signal.signal_ref), 24
                )
                work[work_ref] = LearningCandidateWorkItemV351(
                    work_ref=work_ref,
                    frontier=frontier,
                    proposals=proposals,
                    source_lineage_refs=signal.source_lineage_refs,
                    requested_uses=(),
                    competence_case_refs=(),
                    deferred_reason_refs=("frontier:learning:semantic-target-required",),
                )

        # Genuinely new concept path: a reviewed definition construction introduces a new
        # referent-type schema as a subtype of an exact parent, then lexicalizes the new
        # candidate schema in the same dependency DAG. No concept name or copula is decoded
        # here; the construction metadata already states the semantic relation.
        for extracted_definition in definition_extracted:
            form_signal = extracted_definition.form_signal
            definition = extracted_definition.projection
            frontier = frontiers_by_target.get(form_signal.observation_ref)
            if frontier is None:
                continue
            parent_stored = store.get_record(
                definition.parent_schema_pin.record_kind,
                definition.parent_schema_pin.record_ref,
                definition.parent_schema_pin.revision,
            )
            if (
                parent_stored is None
                or parent_stored.record_fingerprint != definition.parent_schema_pin.record_fingerprint
            ):
                continue
            schema_proposals = self.semantic_definition.induce_subtype_definition(
                definition, form_signal=form_signal, parent_schema=parent_stored.payload,
            )
            if not schema_proposals:
                continue
            schema_pin = candidate_pin(schema_proposals[0].record_kind, schema_proposals[0].payload)
            lexical_projection = TeachingProjectionEvidenceV351(
                projection_ref="teaching-projection:new-definition:" + semantic_fingerprint(
                    "new-definition-lexical-projection-v351",
                    (definition.projection_ref, schema_pin.key, definition.construction_pin.key),
                    24,
                ),
                form_signal_ref=form_signal.signal_ref,
                target_pin=schema_pin,
                target_kind=SenseTargetKind.REFERENT_TYPE,
                target_schema_class=SchemaClass.REFERENT_TYPE,
                use_operation=UseOperation.GROUND,
                construction_pin=definition.construction_pin,
                evidence_refs=definition.evidence_refs,
                source_lineage_refs=definition.source_lineage_refs,
                competence_case_refs=definition.competence_case_refs,
                requested_uses=definition.requested_uses,
                lexical_category=definition.lexical_category,
                metadata={
                    **dict(definition.metadata),
                    "definition_projection_ref": definition.projection_ref,
                    "target_is_candidate_schema": True,
                },
            )
            lexical_proposals = self.lexicalization.induce(form_signal, lexical_projection)
            proposals = tuple((*schema_proposals, *lexical_proposals))
            work_ref = "learning-work:" + semantic_fingerprint(
                "phase14-new-definition-work",
                (frontier.frontier_ref, definition.projection_ref, tuple(p.proposer_ref for p in proposals)),
                24,
            )
            work[work_ref] = LearningCandidateWorkItemV351(
                work_ref=work_ref,
                frontier=frontier,
                proposals=proposals,
                source_lineage_refs=definition.source_lineage_refs,
                requested_uses=definition.requested_uses,
                competence_case_refs=definition.competence_case_refs,
                review_refs=extracted_definition.review_refs,
                authorization_refs=extracted_definition.authorization_refs,
                risk_refs=extracted_definition.risk_refs,
                promotion_policy_ref=extracted_definition.promotion_policy_ref,
            )

        # Exact structurally-derived candidate signals cover semantic definitions, state,
        # transitions and causal structures. The signal producer must supply canonical
        # record payload + exact dependency closure; the inducer never fabricates meaning.
        structural_inducers = {
            PredictionErrorFamily.SEMANTIC_DEFINITION: self.semantic_definition,
            PredictionErrorFamily.STATE_SCHEMA: self.state_schema,
            PredictionErrorFamily.CAUSAL_STRUCTURE: self.transition_causal,
            PredictionErrorFamily.ROLE_TRANSITION: self.transition_causal,
            PredictionErrorFamily.CAPABILITY_DEPENDENCY: self.transition_causal,
        }
        for signal in classified.structural_signals:
            inducer = structural_inducers.get(signal.family)
            if inducer is None:
                continue
            proposals = inducer.induce(signal)
            if not proposals:
                continue
            frontier = self._frontier_for_structural(signal, classified.frontiers)
            work_ref = "learning-work:" + semantic_fingerprint(
                "phase14-structural-work", (frontier.frontier_ref, signal.signal_ref), 24
            )
            work[work_ref] = LearningCandidateWorkItemV351(
                work_ref=work_ref,
                frontier=frontier,
                proposals=proposals,
                source_lineage_refs=signal.source_lineage_refs,
                requested_uses=signal.requested_uses,
                competence_case_refs=signal.competence_case_refs,
                review_refs=tuple(signal.metadata.get("review_refs", ()) or ()),
                authorization_refs=tuple(signal.metadata.get("authorization_refs", ()) or ()),
                risk_refs=tuple(signal.metadata.get("risk_refs", ()) or ()),
                promotion_policy_ref=str(
                    signal.metadata.get("promotion_policy_ref") or "policy:v351:reviewed-learning-promotion"
                ),
            )

        # Construction induction is a typed structural signal, not n-gram mining or a
        # sentence template learner. Producers may be replay/mining services, but every
        # signal carries exact triggers, slots, output schema, evidence and competence.
        for signal in tuple(cycle.artifacts.get("construction_pattern_signals", ()) or ()):
            if not isinstance(signal, ConstructionPatternSignal):
                continue
            proposals = self.construction.induce(signal)
            frontier = self._frontier_for_construction(signal, classified.frontiers, cycle)
            work_ref = "learning-work:" + semantic_fingerprint(
                "phase14-construction-work", (frontier.frontier_ref, signal.signal_ref), 24
            )
            work[work_ref] = LearningCandidateWorkItemV351(
                work_ref=work_ref,
                frontier=frontier,
                proposals=proposals,
                source_lineage_refs=signal.source_lineage_refs,
                requested_uses=signal.requested_uses,
                competence_case_refs=signal.competence_case_refs,
                review_refs=tuple(signal.metadata.get("review_refs", ()) or ()),
                authorization_refs=tuple(signal.metadata.get("authorization_refs", ()) or ()),
                risk_refs=tuple(signal.metadata.get("risk_refs", ()) or ()),
                promotion_policy_ref=str(
                    signal.metadata.get("promotion_policy_ref") or "policy:v351:reviewed-learning-promotion"
                ),
            )

        parameter_examples = tuple(
            item for item in tuple(cycle.artifacts.get("parameter_training_examples", ()) or ())
            if isinstance(item, ParameterTrainingExample)
        )
        parameter_candidates = ()
        semantic_authority = cycle.artifacts.get("semantic_authority_snapshot_v351")
        if parameter_examples and semantic_authority is not None and semantic_authority.dynamics_parameters:
            # Continuous parameter learning stays candidate-only. It cannot alter the
            # current cycle's pinned Θ or masquerade as discrete semantic learning.
            parameter_candidates = (
                self.parameter_trainer.train(
                    semantic_authority.dynamics_parameters,
                    parameter_examples,
                ),
            )

        questions = set(classified.question_refs)
        for item in work.values():
            questions.update(item.deferred_reason_refs)

        return {
            "prediction_errors": tuple(classified.errors),
            "learning_frontiers": tuple(classified.frontiers),
            # Stage-13 accepts typed work items and immutable parameter candidates. The
            # latter are audit/calibration work and are never passed to semantic promotion.
            "learning_candidate_work": tuple(
                (*[work[key] for key in sorted(work)], *parameter_candidates)
            ),
            "learning_question_candidates": tuple(sorted(questions)),
        }

    @staticmethod
    def _frontier_for_structural(signal: ExactStructuralCandidateSignal, frontiers):
        for frontier in frontiers:
            if frontier.frontier_ref == signal.metadata.get("frontier_ref"):
                return frontier
        # Exact signals may originate from replay/maintenance rather than a textual gap.
        from .model import FrontierResolutionStatus, LearningFrontierRecord
        return LearningFrontierRecord(
            frontier_ref="learning-frontier:" + semantic_fingerprint(
                "phase14-structural-frontier", (signal.signal_ref, signal.family.value), 24
            ),
            missing_contract=f"learning.{signal.family.value}",
            expected_record_kinds=(signal.record_kind,),
            expected_schema_classes=(),
            accepted_anchor_types=("exact_structural_candidate",),
            evidence_refs=signal.evidence_refs,
            candidate_refs=(),
            target_ref=None,
            resolution_status=FrontierResolutionStatus.OPEN,
            context_ref=str(signal.metadata.get("context_ref") or "actual"),
            permission_ref=str(signal.metadata.get("permission_ref") or "conversation"),
            metadata={"phase14_family": signal.family.value},
        )

    @staticmethod
    def _frontier_for_construction(signal: ConstructionPatternSignal, frontiers, cycle):
        for frontier in frontiers:
            if frontier.frontier_ref == signal.metadata.get("frontier_ref"):
                return frontier
        from .model import FrontierResolutionStatus, LearningFrontierRecord
        from ..storage.model import RecordKind
        return LearningFrontierRecord(
            frontier_ref="learning-frontier:" + semantic_fingerprint(
                "phase14-construction-frontier", signal.signal_ref, 24
            ),
            missing_contract="learning.construction",
            expected_record_kinds=(RecordKind.CONSTRUCTION,),
            expected_schema_classes=(),
            accepted_anchor_types=("construction_pattern",),
            evidence_refs=signal.evidence_refs,
            context_ref=cycle.context_ref,
            permission_ref=cycle.permission_ref,
            resolution_status=FrontierResolutionStatus.OPEN,
            metadata={"phase14_family": PredictionErrorFamily.CONSTRUCTION.value},
        )


__all__ = ["Phase14LearningEngineV351"]
