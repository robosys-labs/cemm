"""Phase-14 evidence-driven candidate inducers.

Every inducer is structural and data-driven. None inspects English words, concept names,
fixture names, or transcript phrases. Candidate generation is non-authoritative.
"""
from __future__ import annotations

from dataclasses import replace
import math
from typing import Iterable

from ..csir.authority_v351 import DynamicsParameterArtifact
from ..csir.model import ExactAuthorityPin
from ..language.model import (
    ConstructionRecord, FormKind, FormSenseLinkRecord, LanguageFormRecord, LexicalSenseRecord,
    SenseTargetKind,
)
from ..schema.model import (
    MeaningSchema, ParentRevisionPolicy, ReferentTypeSchema, SchemaClass, SchemaDependency,
    SchemaLifecycleStatus, SchemaParentLink, SchemaProvenance, UseDecision, UseOperation,
    UseProfile, semantic_fingerprint,
)
from ..storage.codec import record_fingerprints, record_ref, record_revision
from ..storage.model import RecordKind
from ..transitions.model import TransitionContractRecord
from ..state.model_v351 import TransitionMechanismV351
from ..state.capability_v351 import CapabilityDependencyGraph
from .model import PinnedRecord
from .package import CandidateProposal
from .phase14_model_v351 import (
    ConstructionPatternSignal, DynamicsParameterCandidateV351, ExactStructuralCandidateSignal,
    LexicalTargetSignal, NovelFormSignal, ParameterTrainingExample, PredictionErrorFamily,
    DefinitionTeachingProjectionV351, TeachingProjectionEvidenceV351,
)


def candidate_pin(kind: RecordKind, payload) -> PinnedRecord:
    return PinnedRecord(
        kind,
        record_ref(kind, payload),
        record_revision(kind, payload),
        record_fingerprints(kind, payload)[1],
    )


class FormNormalizationInducer:
    family = PredictionErrorFamily.FORM_NORMALIZATION

    def induce(self, signal: NovelFormSignal) -> tuple[CandidateProposal, ...]:
        form_ref = "language-form:learned:" + semantic_fingerprint(
            "learned-language-form-v351",
            (
                signal.pack_pin.key,
                signal.language_tag,
                signal.normalized_form,
                signal.script,
                signal.category,
                signal.token_count,
            ),
            24,
        )
        payload = LanguageFormRecord(
            form_ref=form_ref,
            pack_ref=signal.pack_pin.record_ref,
            pack_revision=signal.pack_pin.revision,
            written_form=signal.written_form,
            normalized_form=signal.normalized_form,
            form_kind=FormKind.TOKEN if signal.token_count == 1 else FormKind.MULTIWORD,
            lifecycle_status=SchemaLifecycleStatus.CANDIDATE,
            script=signal.script,
            token_count=signal.token_count,
            feature_values=(("category", signal.category),) if signal.category else (),
            source_refs=signal.source_lineage_refs,
            evidence_refs=signal.evidence_refs,
            permission_ref=signal.permission_ref,
            metadata={
                "learned_by": "phase14.form_normalization_inducer.v351",
                "observation_ref": signal.observation_ref,
                "candidate_not_authority": True,
            },
        )
        return (CandidateProposal(
            record_kind=RecordKind.LANGUAGE_FORM,
            payload=payload,
            evidence_refs=signal.evidence_refs,
            dependency_pins=(signal.pack_pin,),
            confidence=1.0,
            proposer_ref="candidate-inducer:form-normalization:v351",
        ),)


class SenseInducer:
    family = PredictionErrorFamily.SENSE

    def induce(
        self,
        signal: LexicalTargetSignal,
        *,
        form_pin: PinnedRecord,
    ) -> tuple[CandidateProposal, ...]:
        sense_ref = "lexical-sense:learned:" + semantic_fingerprint(
            "learned-lexical-sense-v351",
            (
                signal.pack_pin.key,
                form_pin.key,
                signal.target_pin.key,
                signal.target_kind.value,
                None if signal.target_schema_class is None else signal.target_schema_class.value,
                signal.use_operation.value,
            ),
            24,
        )
        payload = LexicalSenseRecord(
            sense_ref=sense_ref,
            pack_ref=signal.pack_pin.record_ref,
            pack_revision=signal.pack_pin.revision,
            target_kind=signal.target_kind,
            target_ref=signal.target_pin.record_ref,
            target_revision=signal.target_pin.revision,
            lifecycle_status=SchemaLifecycleStatus.CANDIDATE,
            target_schema_class=signal.target_schema_class,
            use_operation=signal.use_operation,
            authorized_use_operations=(),
            use_authority_explicit=False,
            lexical_category=signal.lexical_category,
            source_refs=signal.source_lineage_refs,
            evidence_refs=signal.evidence_refs,
            competence_case_refs=signal.competence_case_refs,
            permission_ref=signal.permission_ref,
            metadata={
                "learned_by": "phase14.sense_inducer.v351",
                "candidate_not_authority": True,
                **dict(signal.metadata),
            },
        )
        return (CandidateProposal(
            record_kind=RecordKind.LEXICAL_SENSE,
            payload=payload,
            evidence_refs=signal.evidence_refs,
            dependency_pins=tuple(sorted((signal.pack_pin, signal.target_pin, form_pin), key=lambda item: item.key)),
            confidence=1.0,
            proposer_ref="candidate-inducer:sense:v351",
        ),)


class LexicalizationInducer:
    family = PredictionErrorFamily.LEXICALIZATION

    def __init__(self) -> None:
        self.form_inducer = FormNormalizationInducer()
        self.sense_inducer = SenseInducer()

    def induce(
        self,
        form_signal: NovelFormSignal,
        projection: TeachingProjectionEvidenceV351,
    ) -> tuple[CandidateProposal, ...]:
        if projection.form_signal_ref != form_signal.signal_ref:
            return ()
        # The projection is exact construction authority. No word-order or raw-text
        # inference occurs here.
        form_proposal = self.form_inducer.induce(form_signal)[0]
        form_pin = candidate_pin(form_proposal.record_kind, form_proposal.payload)
        lexical_signal = LexicalTargetSignal(
            signal_ref="lexical-target-signal:" + semantic_fingerprint(
                "lexical-target-signal-v351",
                (form_signal.signal_ref, projection.projection_ref, projection.target_pin.key),
                24,
            ),
            form_signal_ref=form_signal.signal_ref,
            pack_pin=form_signal.pack_pin,
            target_pin=projection.target_pin,
            target_kind=projection.target_kind,
            target_schema_class=projection.target_schema_class,
            use_operation=projection.use_operation,
            lexical_category=projection.lexical_category or form_signal.category,
            evidence_refs=tuple(sorted(set((*form_signal.evidence_refs, *projection.evidence_refs)))),
            source_lineage_refs=tuple(sorted(set((*form_signal.source_lineage_refs, *projection.source_lineage_refs)))),
            competence_case_refs=projection.competence_case_refs,
            requested_uses=projection.requested_uses,
            permission_ref=form_signal.permission_ref,
            metadata={
                "teaching_projection_ref": projection.projection_ref,
                "construction_pin": projection.construction_pin.key,
            },
        )
        sense_proposal = self.sense_inducer.induce(lexical_signal, form_pin=form_pin)[0]
        sense_pin = candidate_pin(sense_proposal.record_kind, sense_proposal.payload)
        link_ref = "form-sense-link:learned:" + semantic_fingerprint(
            "learned-form-sense-link-v351",
            (form_pin.key, sense_pin.key, projection.construction_pin.key),
            24,
        )
        link = FormSenseLinkRecord(
            link_ref=link_ref,
            form_ref=form_pin.record_ref,
            form_revision=form_pin.revision,
            sense_ref=sense_pin.record_ref,
            sense_revision=sense_pin.revision,
            lifecycle_status=SchemaLifecycleStatus.CANDIDATE,
            prior_weight=1.0,
            source_refs=lexical_signal.source_lineage_refs,
            evidence_refs=lexical_signal.evidence_refs,
            permission_ref=lexical_signal.permission_ref,
            metadata={
                "learned_by": "phase14.lexicalization_inducer.v351",
                "teaching_projection_ref": projection.projection_ref,
                "candidate_not_authority": True,
            },
        )
        link_proposal = CandidateProposal(
            record_kind=RecordKind.FORM_SENSE_LINK,
            payload=link,
            evidence_refs=lexical_signal.evidence_refs,
            dependency_pins=tuple(sorted((form_pin, sense_pin, projection.construction_pin), key=lambda item: item.key)),
            confidence=1.0,
            proposer_ref="candidate-inducer:lexicalization-link:v351",
        )
        # Return the exact dependency DAG topologically. The Stage-13 committer persists
        # all records atomically, then packages the resulting exact pins.
        return (form_proposal, sense_proposal, link_proposal)


class ConstructionInducer:
    family = PredictionErrorFamily.CONSTRUCTION

    def induce(self, signal: ConstructionPatternSignal) -> tuple[CandidateProposal, ...]:
        trigger_forms = tuple(pin.record_ref for pin in signal.trigger_form_pins)
        trigger_senses = tuple(pin.record_ref for pin in signal.trigger_sense_pins)
        output_ref = None if signal.output_schema_pin is None else signal.output_schema_pin.record_ref
        output_revision = None if signal.output_schema_pin is None else signal.output_schema_pin.revision
        construction_ref = "construction:learned:" + semantic_fingerprint(
            "learned-construction-v351",
            (
                signal.pack_pin.key,
                signal.construction_kind.value,
                signal.slots,
                tuple(pin.key for pin in signal.trigger_form_pins),
                tuple(pin.key for pin in signal.trigger_sense_pins),
                None if signal.output_schema_pin is None else signal.output_schema_pin.key,
                tuple(sorted(signal.source_lineage_refs)),
            ),
            24,
        )
        payload = ConstructionRecord(
            construction_ref=construction_ref,
            pack_ref=signal.pack_pin.record_ref,
            pack_revision=signal.pack_pin.revision,
            construction_kind=signal.construction_kind,
            slots=signal.slots,
            lifecycle_status=SchemaLifecycleStatus.CANDIDATE,
            trigger_form_refs=trigger_forms,
            trigger_sense_refs=trigger_senses,
            output_schema_ref=output_ref,
            output_schema_revision=output_revision,
            output_schema_class=signal.output_schema_class,
            full_sentence_pattern=False,
            genuine_idiom=False,
            preserves_gap=signal.construction_kind.value == "ellipsis",
            authorized_use_operations=(),
            use_authority_explicit=False,
            source_refs=signal.source_lineage_refs,
            evidence_refs=signal.evidence_refs,
            competence_case_refs=signal.competence_case_refs,
            metadata={
                "learned_by": "phase14.construction_inducer.v351",
                "candidate_not_authority": True,
                **dict(signal.metadata),
            },
        )
        deps = [signal.pack_pin, *signal.trigger_form_pins, *signal.trigger_sense_pins]
        if signal.output_schema_pin is not None:
            deps.append(signal.output_schema_pin)
        return (CandidateProposal(
            RecordKind.CONSTRUCTION,
            payload,
            signal.evidence_refs,
            dependency_pins=tuple(sorted(set(deps), key=lambda item: item.key)),
            confidence=1.0,
            proposer_ref="candidate-inducer:construction:v351",
        ),)


class _ExactStructuralInducer:
    family: PredictionErrorFamily
    accepted_record_kinds: frozenset[RecordKind]

    def induce(self, signal: ExactStructuralCandidateSignal) -> tuple[CandidateProposal, ...]:
        if signal.family != self.family or signal.record_kind not in self.accepted_record_kinds:
            return ()
        self.validate(signal)
        return (CandidateProposal(
            signal.record_kind,
            signal.payload,
            signal.evidence_refs,
            dependency_pins=signal.dependency_pins,
            confidence=signal.confidence,
            proposer_ref=f"candidate-inducer:{self.family.value}:v351",
        ),)

    def validate(self, signal: ExactStructuralCandidateSignal) -> None:
        if record_ref(signal.record_kind, signal.payload) == "":
            raise ValueError("candidate payload lacks canonical record identity")
        # Exact dependency closure is mandatory for executable semantics. Primitive
        # definitions may legitimately have no prerequisite records, but that must be an
        # explicit, proof-bearing closure claim rather than an omitted dependency list.
        if signal.record_kind in {RecordKind.SCHEMA, RecordKind.TRANSITION_CONTRACT} and not signal.dependency_pins:
            closed = bool(signal.metadata.get("dependency_closed", False))
            closure_proofs = tuple(signal.metadata.get("closure_proof_refs", ()) or ())
            if not closed or not closure_proofs:
                raise ValueError(
                    f"{self.family.value} candidate without prerequisites requires explicit dependency closure proof"
                )


class SemanticDefinitionInducer(_ExactStructuralInducer):
    family = PredictionErrorFamily.SEMANTIC_DEFINITION
    accepted_record_kinds = frozenset({RecordKind.SCHEMA})

    def validate(self, signal):
        super().validate(signal)
        if not isinstance(signal.payload, MeaningSchema):
            raise TypeError("semantic definition candidate must be canonical MeaningSchema")

    def induce_subtype_definition(
        self,
        signal: DefinitionTeachingProjectionV351,
        *,
        form_signal: NovelFormSignal,
        parent_schema: MeaningSchema,
    ) -> tuple[CandidateProposal, ...]:
        """Induce a genuinely new referent-type schema from reviewed subtype teaching.

        This is structural, not lexical guessing: the exact construction declares the
        subtype relation, the parent is an existing exact schema, and the observed form is
        only the introduced concept's linguistic identity anchor. Unsupported schema
        families fail closed and may still enter through the general structural-signal path.
        """
        if signal.form_signal_ref != form_signal.signal_ref:
            return ()
        if signal.parent_schema_class is not SchemaClass.REFERENT_TYPE:
            raise ValueError("direct subtype teaching requires an exact referent-type parent")
        if not isinstance(parent_schema, ReferentTypeSchema):
            raise TypeError("referent-type definition teaching parent payload mismatch")
        if (
            parent_schema.schema_ref != signal.parent_schema_pin.record_ref
            or parent_schema.revision != signal.parent_schema_pin.revision
        ):
            raise ValueError("definition teaching parent payload differs from exact parent pin")

        concept_key = semantic_fingerprint(
            "learned-referent-type-definition-key-v351",
            (
                form_signal.pack_pin.key,
                form_signal.normalized_form,
                signal.parent_schema_pin.key,
                signal.construction_pin.key,
                signal.definition_relation,
            ),
            48,
        )
        schema_ref = "schema:learned:referent-type:" + concept_key[:24]
        semantic_key = "semantic-key:learned-definition:" + concept_key
        payload = ReferentTypeSchema(
            schema_ref=schema_ref,
            semantic_key=semantic_key,
            parent_links=(SchemaParentLink(
                parent_ref=signal.parent_schema_pin.record_ref,
                revision_policy=ParentRevisionPolicy.EXACT,
                revision=signal.parent_schema_pin.revision,
                inheritance_kind="subtype",
            ),),
            local_ports=(),
            lifecycle_status=SchemaLifecycleStatus.CANDIDATE,
            revision=1,
            supersedes_revision=None,
            scope_ref=parent_schema.scope_ref,
            confidence=1.0,
            permission_ref=form_signal.permission_ref,
            provenance=SchemaProvenance(
                evidence_refs=signal.evidence_refs,
                source_refs=(
                    f"construction:{signal.construction_pin.record_ref}@{signal.construction_pin.revision}",
                ),
                lineage_refs=signal.source_lineage_refs,
                created_by="candidate-inducer:semantic-definition:v351",
            ),
            dependencies=(SchemaDependency(
                dependency_ref=signal.parent_schema_pin.record_ref,
                dependency_kind="exact_semantic_parent",
                exact_revision=signal.parent_schema_pin.revision,
                required=True,
                required_for=frozenset({UseOperation.GROUND, UseOperation.COMPOSE, UseOperation.QUERY}),
                reason="reviewed construction-authorized subtype definition",
            ),),
            use_profile=UseProfile(),
            competence_hooks=(),
            metadata={
                "learned_by": "phase14.semantic_definition_inducer.v351",
                "candidate_not_authority": True,
                "definition_relation": signal.definition_relation,
                "definition_projection_ref": signal.projection_ref,
                "linguistic_anchor_signal_ref": form_signal.signal_ref,
                "construction_pin": signal.construction_pin.key,
            },
            # These are structural denotation constraints inherited from the exact parent;
            # facet and identity-rule refs remain inherited through the parent link rather
            # than being copied as unpinned local dependencies.
            storage_kinds=parent_schema.storage_kinds,
            facet_entitlement_refs=(),
            identity_criterion_refs=(),
        )
        return (CandidateProposal(
            record_kind=RecordKind.SCHEMA,
            payload=payload,
            evidence_refs=signal.evidence_refs,
            dependency_pins=tuple(sorted(
                (signal.parent_schema_pin, signal.construction_pin), key=lambda item: item.key
            )),
            confidence=1.0,
            proposer_ref="candidate-inducer:semantic-definition:v351",
        ),)


class StateSchemaInducer(_ExactStructuralInducer):
    family = PredictionErrorFamily.STATE_SCHEMA
    accepted_record_kinds = frozenset({RecordKind.SCHEMA, RecordKind.FACET_ENTITLEMENT})

    def validate(self, signal):
        super().validate(signal)
        if isinstance(signal.payload, MeaningSchema):
            schema_class = getattr(signal.payload, "schema_class", None)
            allowed_names = {"state_dimension", "state_value", "property"}
            if schema_class is not None and str(getattr(schema_class, "value", schema_class)) not in allowed_names:
                raise ValueError("state schema inducer refuses a non-state structural schema")


class TransitionCausalInducer(_ExactStructuralInducer):
    family = PredictionErrorFamily.CAUSAL_STRUCTURE
    accepted_families = frozenset({
        PredictionErrorFamily.CAUSAL_STRUCTURE,
        PredictionErrorFamily.ROLE_TRANSITION,
        PredictionErrorFamily.CAPABILITY_DEPENDENCY,
    })
    accepted_record_kinds = frozenset({RecordKind.TRANSITION_CONTRACT, RecordKind.CAPABILITY_DEPENDENCY})

    def induce(self, signal: ExactStructuralCandidateSignal) -> tuple[CandidateProposal, ...]:
        if signal.family not in self.accepted_families or signal.record_kind not in self.accepted_record_kinds:
            return ()
        self.validate(signal)
        return (CandidateProposal(
            signal.record_kind, signal.payload, signal.evidence_refs,
            dependency_pins=signal.dependency_pins, confidence=signal.confidence,
            proposer_ref=f"candidate-inducer:{signal.family.value}:v351",
        ),)

    def validate(self, signal):
        # Call the structural base directly because this inducer intentionally accepts
        # several transition/causal prediction-error families.
        _ExactStructuralInducer.validate(self, signal)
        if signal.record_kind == RecordKind.TRANSITION_CONTRACT and not isinstance(
            signal.payload, (TransitionContractRecord, TransitionMechanismV351)
        ):
            raise TypeError("causal transition candidate must be canonical transition authority")
        if signal.record_kind == RecordKind.CAPABILITY_DEPENDENCY and not isinstance(
            signal.payload, CapabilityDependencyGraph
        ):
            raise TypeError("capability dependency candidate must be canonical CapabilityDependencyGraph")
        # Temporal/coactivation-only evidence cannot become causal structure.
        if not signal.metadata.get("intervention_or_mechanism_evidence", False):
            raise ValueError("causal candidate requires intervention/mechanism evidence, not coactivation alone")


class ParameterCandidateTrainer:
    """Deterministic candidate-only continuous parameter trainer.

    It never mutates the current DynamicsParameterArtifact objects. The result is a new
    immutable candidate artifact family that still requires replay/calibration/competence
    and post-pass authority publication.
    """

    def train(
        self,
        base_artifacts: Iterable[DynamicsParameterArtifact],
        examples: Iterable[ParameterTrainingExample],
        *,
        learning_rate: float = 0.05,
    ) -> DynamicsParameterCandidateV351:
        base = tuple(sorted(base_artifacts, key=lambda item: item.parameter_family))
        examples = tuple(sorted(examples, key=lambda item: item.example_ref))
        if not base or not examples:
            raise ValueError("parameter training requires exact base artifacts and examples")
        if not math.isfinite(learning_rate) or not 0.0 < learning_rate <= 1.0:
            raise ValueError("learning_rate must be finite in (0,1]")

        # Generic scalar calibration objective: examples expose named feature residuals.
        # Only names already present in exact base artifacts may be updated; no new hidden
        # parameters are invented by training.
        by_name = {
            (artifact.parameter_family, name): float(value)
            for artifact in base for name, value in artifact.values
        }
        residual_sum = {key: 0.0 for key in by_name}
        count = {key: 0 for key in by_name}
        for example in examples:
            for feature_name, residual in example.feature_values:
                matching = [key for key in by_name if key[1] == feature_name]
                for key in matching:
                    residual_sum[key] += float(residual)
                    count[key] += 1
        objective_before = sum(value * value for value in residual_sum.values())
        new_by_name = dict(by_name)
        for key in sorted(new_by_name):
            if count[key]:
                step = learning_rate * residual_sum[key] / count[key]
                new_by_name[key] = new_by_name[key] - step
        objective_after = sum(
            (residual_sum[key] * (1.0 - learning_rate if count[key] else 1.0)) ** 2
            for key in residual_sum
        )
        artifacts = []
        for artifact in base:
            new_values = tuple((name, new_by_name[(artifact.parameter_family, name)]) for name, _ in artifact.values)
            content = semantic_fingerprint(
                "trained-dynamics-parameter-candidate-v351",
                (artifact.parameter_pin.key, new_values, tuple(item.example_ref for item in examples)),
                64,
            )
            pin = ExactAuthorityPin(
                kind=artifact.parameter_pin.kind,
                namespace=artifact.parameter_pin.namespace,
                ref=artifact.parameter_pin.ref,
                revision=artifact.parameter_pin.revision + 1,
                content_hash=content,
                scope_ref=artifact.parameter_pin.scope_ref,
            )
            artifacts.append(DynamicsParameterArtifact(
                parameter_pin=pin,
                parameter_family=artifact.parameter_family,
                values=new_values,
                calibration_evidence_refs=tuple(sorted({ref for item in examples for ref in item.evidence_refs})),
            ))
        return DynamicsParameterCandidateV351(
            candidate_ref="dynamics-parameter-candidate:" + semantic_fingerprint(
                "dynamics-parameter-candidate-v351",
                (
                    tuple(item.parameter_pin.key for item in base),
                    tuple(item.parameter_pin.key for item in artifacts),
                    tuple(item.example_ref for item in examples),
                ),
                24,
            ),
            base_parameter_pins=tuple(item.parameter_pin for item in base),
            candidate_artifacts=tuple(artifacts),
            training_example_refs=tuple(item.example_ref for item in examples),
            evidence_refs=tuple(sorted({ref for item in examples for ref in item.evidence_refs})),
            source_lineage_refs=tuple(sorted({ref for item in examples for ref in item.source_lineage_refs})),
            objective_before=float(objective_before),
            objective_after=float(min(objective_before, objective_after)),
            calibration_required=True,
        )


__all__ = [
    "ConstructionInducer", "FormNormalizationInducer", "LexicalizationInducer",
    "ParameterCandidateTrainer", "SemanticDefinitionInducer", "SenseInducer",
    "StateSchemaInducer", "TransitionCausalInducer", "candidate_pin",
]
