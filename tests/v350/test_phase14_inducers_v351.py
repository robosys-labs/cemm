from dataclasses import replace

import pytest

from cemm.v350.dynamics.parameters_v351 import compile_reviewed_phase13_parameter_artifacts
from cemm.v350.language.model import SenseTargetKind
from cemm.v350.learning.inducers_v351 import (
    FormNormalizationInducer, LexicalizationInducer, ParameterCandidateTrainer,
    SemanticDefinitionInducer, StateSchemaInducer, TransitionCausalInducer,
    ConstructionInducer, SenseInducer,
)
from cemm.v350.learning.model import PinnedRecord
from cemm.v350.learning.phase14_model_v351 import (
    NovelFormSignal, ParameterTrainingExample, PredictionErrorFamily,
    TeachingProjectionEvidenceV351, ExactStructuralCandidateSignal,
)
from cemm.v350.schema.model import (
    MeaningSchema, SchemaClass, SchemaLifecycleStatus, UseAuthorization, UseDecision, UseOperation,
)
from cemm.v350.storage.codec import record_fingerprints
from cemm.v350.storage.model import RecordKind


def _pin(kind, ref, fp="f"*64, revision=1):
    return PinnedRecord(kind, ref, revision, fp)


def test_phase14_exposes_all_eight_required_candidate_inducers():
    required = {
        FormNormalizationInducer, LexicalizationInducer, SenseInducer, ConstructionInducer,
        SemanticDefinitionInducer, StateSchemaInducer, TransitionCausalInducer, ParameterCandidateTrainer,
    }
    assert len(required) == 8


def test_generic_unseen_lexicalization_builds_exact_candidate_dag_without_concept_specific_code():
    nonce = "nuvra-7f31"  # arbitrary test nonce; production logic never branches on it.
    pack = _pin(RecordKind.LANGUAGE_PACK, "language-pack:test")
    target = _pin(RecordKind.SCHEMA, "schema:test:novel-target")
    construction = _pin(RecordKind.CONSTRUCTION, "construction:test:reviewed-teaching")
    form = NovelFormSignal(
        "signal:nonce", "observation:nonce", pack, "x-test", nonce, nonce.casefold(), "Latn", "", 1,
        ("evidence:nonce",), ("lineage:nonce",),
    )
    projection = TeachingProjectionEvidenceV351(
        "projection:nonce", form.signal_ref, target, SenseTargetKind.SCHEMA, SchemaClass.MEANING,
        UseOperation.GROUND, construction, ("evidence:nonce",), ("lineage:teacher",),
        ("competence:nonce-ground",), (UseAuthorization(UseOperation.GROUND, UseDecision.ALLOW),),
    )
    proposals = LexicalizationInducer().induce(form, projection)
    assert [item.record_kind for item in proposals] == [
        RecordKind.LANGUAGE_FORM, RecordKind.LEXICAL_SENSE, RecordKind.FORM_SENSE_LINK,
    ]
    assert all(getattr(item.payload, "lifecycle_status") == SchemaLifecycleStatus.CANDIDATE for item in proposals)
    # The link depends on candidate form+sense plus exact teaching construction authority.
    assert construction in proposals[-1].dependency_pins
    assert nonce in proposals[0].payload.written_form


def test_structural_semantic_definition_requires_explicit_dependency_closure_proof_when_primitive():
    schema = MeaningSchema("schema:learned:primitive", "semantic-key:learned:primitive")
    signal = ExactStructuralCandidateSignal(
        "signal:def", PredictionErrorFamily.SEMANTIC_DEFINITION, RecordKind.SCHEMA, schema, (),
        ("evidence:def",), ("lineage:def",), ("competence:def",), (),
    )
    with pytest.raises(ValueError):
        SemanticDefinitionInducer().induce(signal)
    closed = replace(signal, metadata={"dependency_closed": True, "closure_proof_refs": ("proof:closed",)})
    assert SemanticDefinitionInducer().induce(closed)


def test_parameter_trainer_emits_immutable_next_revision_candidates_only():
    base = compile_reviewed_phase13_parameter_artifacts()
    example = ParameterTrainingExample(
        "example:1", (("bias", .2),), "semantic-class:expected", "semantic-class:observed",
        ("evidence:p",), ("lineage:p",),
    )
    candidate = ParameterCandidateTrainer().train(base, (example,))
    assert candidate.calibration_required
    assert candidate.objective_after <= candidate.objective_before
    assert all(new.parameter_pin.revision == old.parameter_pin.revision + 1 for old, new in zip(base, candidate.candidate_artifacts))
    assert tuple(item.parameter_pin.revision for item in base) == (1,) * len(base)


def test_promoted_multi_record_graph_rewires_candidate_revision_dependencies_atomically():
    from cemm.v350.language.model import FormSenseLinkRecord
    from cemm.v350.learning.promotion_rewire_v351 import rewire_promoted_record

    form_pin = _pin(RecordKind.LANGUAGE_FORM, "form:learned", revision=1)
    sense_pin = _pin(RecordKind.LEXICAL_SENSE, "sense:learned", revision=1)
    link = FormSenseLinkRecord(
        link_ref="link:learned", form_ref=form_pin.record_ref, form_revision=1,
        sense_ref=sense_pin.record_ref, sense_revision=1,
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        source_refs=("source:test",), evidence_refs=("evidence:test",),
    )
    rewired = rewire_promoted_record(
        link,
        candidate_pins=(form_pin, sense_pin),
        revision_map={form_pin.key: 2, sense_pin.key: 2},
    )
    assert rewired.form_revision == 2
    assert rewired.sense_revision == 2


def test_promoted_graph_fails_closed_if_active_record_would_retain_unpromoted_candidate_dependency():
    from cemm.v350.language.model import FormSenseLinkRecord
    from cemm.v350.learning.promotion_rewire_v351 import rewire_promoted_record

    form_pin = _pin(RecordKind.LANGUAGE_FORM, "form:learned", revision=1)
    sense_pin = _pin(RecordKind.LEXICAL_SENSE, "sense:learned", revision=1)
    link = FormSenseLinkRecord(
        link_ref="link:learned", form_ref=form_pin.record_ref, form_revision=1,
        sense_ref=sense_pin.record_ref, sense_revision=1,
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        source_refs=("source:test",), evidence_refs=("evidence:test",),
    )
    with pytest.raises(ValueError):
        rewire_promoted_record(
            link,
            candidate_pins=(form_pin, sense_pin),
            revision_map={form_pin.key: 2},
        )


def test_reviewed_definition_projection_induces_genuinely_new_referent_type_before_lexicalization():
    from cemm.v350.learning.phase14_model_v351 import DefinitionTeachingProjectionV351
    from cemm.v350.schema.model import ReferentTypeSchema

    nonce = "vesk-73e1"
    pack = _pin(RecordKind.LANGUAGE_PACK, "language-pack:def-test")
    parent = ReferentTypeSchema("schema:parent:artifact", "semantic-key:parent:artifact")
    parent_pin = _pin(RecordKind.SCHEMA, parent.schema_ref, revision=parent.revision)
    construction = _pin(RecordKind.CONSTRUCTION, "construction:def-test:reviewed")
    form = NovelFormSignal(
        "signal:def-nonce", "observation:def-nonce", pack, "x-test", nonce, nonce.casefold(),
        "Latn", "word", 1, ("evidence:def-nonce",), ("lineage:def-nonce",),
    )
    definition = DefinitionTeachingProjectionV351(
        "definition-projection:def-nonce", form.signal_ref, parent_pin, SchemaClass.REFERENT_TYPE,
        construction, ("evidence:def-nonce",), ("lineage:def-teacher",),
        ("competence:def-ground", "competence:def-compose"),
        (
            UseAuthorization(UseOperation.GROUND, UseDecision.ALLOW),
            UseAuthorization(UseOperation.COMPOSE, UseDecision.ALLOW),
        ),
        lexical_category="word",
    )
    schema_proposal = SemanticDefinitionInducer().induce_subtype_definition(
        definition, form_signal=form, parent_schema=parent,
    )[0]
    assert schema_proposal.record_kind is RecordKind.SCHEMA
    learned = schema_proposal.payload
    assert learned.lifecycle_status is SchemaLifecycleStatus.CANDIDATE
    assert learned.schema_class is SchemaClass.REFERENT_TYPE
    assert learned.schema_ref != parent.schema_ref
    assert learned.parent_links[0].parent_ref == parent.schema_ref
    assert learned.parent_links[0].revision == parent.revision
    assert parent_pin in schema_proposal.dependency_pins
    assert construction in schema_proposal.dependency_pins
    # The surface form is only an authority-controlled identity anchor. The learned schema
    # is a distinct semantic record, not an alias of the existing parent schema.
    assert learned.semantic_key != parent.semantic_key
