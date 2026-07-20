from __future__ import annotations

from dataclasses import dataclass
from inspect import getsource
from types import SimpleNamespace

from cemm.v350.facets.closure import SemanticClosureCandidate
from cemm.v350.facets.model import ProjectionStatus
from cemm.v350.grounding.mentions import MentionCompiler
from cemm.v350.grounding.participants import participant_frame_anchors
from cemm.v350.knowledge_factors import ReferentKnowledgeFactorBinder
from cemm.v350.language.constructions import ConstructionMatcher
from cemm.v350.language.model import (
    ConstructionKind,
    ConstructionProgramOperation,
    ConstructionProgramRecord,
    ConstructionProgramStep,
    ConstructionRecord,
    ConstructionSlot,
    FormCandidate,
    FormKind,
    FormLattice,
    LanguageFormRecord,
    LanguagePackRecord,
    LexemeRecord,
    MorphologyAnalysisOperation,
    MorphologyAnalysisRuleRecord,
    SemanticContribution,
    SemanticContributionKind,
    SenseCandidate,
    Span,
)
from cemm.v350.language.analyzer import FormLatticeAnalyzer
from cemm.v350.language.morphology import ProductiveMorphologyAnalyzer
from cemm.v350.language.programs import ConstructionProgramCompiler
from cemm.v350.language.registry import LanguageRegistry
from cemm.v350.learning.authority import record_kind_supports_use
from cemm.v350.runtime_kernel import ParticipantFrame, ParticipantRole
from cemm.v350.schema.model import (
    OpenBindingPurpose,
    PortFillerClass,
    SchemaClass,
    SchemaLifecycleStatus,
    UseDecision,
    UseOperation,
)
from cemm.v350.storage import (
    GraphPatch,
    PatchOperation,
    PatchOperationKind,
    SemanticStore,
    record_ref,
    record_revision,
)
from cemm.v350.storage.codec import decode_record, encode_record
from cemm.v350.storage.model import RecordKind


SRC = ("source:phase3-4-synthetic",)
EVID = ("evidence:phase3-4-synthetic",)
COMP = ("competence:phase3-4-synthetic",)


class _AllowProfile:
    def permits(self, operation, provisional=False):
        return operation == UseOperation.COMPOSE


@dataclass(frozen=True)
class _FakeSchema:
    schema_ref: str
    revision: int
    schema_class: SchemaClass
    local_ports: tuple = ()
    use_profile: object = _AllowProfile()


class _FakeSchemaRegistry:
    def __init__(self, *schemas):
        self._schemas = {
            (item.schema_ref, item.revision): item for item in schemas
        }

    def schema(self, ref, revision):
        return self._schemas[(ref, revision)]

    def iter_schemas(self):
        return tuple(self._schemas.values())


def _pack():
    return LanguagePackRecord(
        pack_ref="language-pack:qaa",
        language_tag="qaa",
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        source_refs=SRC,
        evidence_refs=EVID,
        competence_case_refs=COMP,
    )


def _form():
    return LanguageFormRecord(
        form_ref="form:qaa:zor",
        pack_ref="language-pack:qaa",
        pack_revision=1,
        written_form="zor",
        normalized_form="zor",
        form_kind=FormKind.TOKEN,
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        source_refs=SRC,
        evidence_refs=EVID,
    )


def _lexeme():
    return LexemeRecord(
        lexeme_ref="lexeme:qaa:zor",
        pack_ref="language-pack:qaa",
        pack_revision=1,
        lemma_form_ref="form:qaa:zor",
        lemma_form_revision=1,
        lexical_category="predicate",
        inflection_class_ref="inflection:qaa:regular",
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        source_refs=SRC,
        evidence_refs=EVID,
        competence_case_refs=COMP,
    )




def _second_form():
    return LanguageFormRecord(
        form_ref="form:qaa:nav",
        pack_ref="language-pack:qaa",
        pack_revision=1,
        written_form="nav",
        normalized_form="nav",
        form_kind=FormKind.TOKEN,
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        source_refs=SRC,
        evidence_refs=EVID,
    )


def _second_lexeme():
    return LexemeRecord(
        lexeme_ref="lexeme:qaa:nav",
        pack_ref="language-pack:qaa",
        pack_revision=1,
        lemma_form_ref="form:qaa:nav",
        lemma_form_revision=1,
        lexical_category="predicate",
        inflection_class_ref="inflection:qaa:regular",
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        source_refs=SRC,
        evidence_refs=EVID,
        competence_case_refs=COMP,
    )


def _construction(ref="construction:qaa:synthetic", *, metadata=None):
    return ConstructionRecord(
        construction_ref=ref,
        pack_ref="language-pack:qaa",
        pack_revision=1,
        construction_kind=ConstructionKind.ARGUMENT_STRUCTURE,
        slots=(ConstructionSlot("subject"),),
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        source_refs=SRC,
        evidence_refs=EVID,
        competence_case_refs=COMP,
        metadata={} if metadata is None else metadata,
    )


def _program(construction, *steps, roots=("root",)):
    return ConstructionProgramRecord(
        program_ref=f"construction-program:{construction.construction_ref}",
        pack_ref="language-pack:qaa",
        pack_revision=1,
        construction_ref=construction.construction_ref,
        construction_revision=1,
        steps=tuple(steps),
        root_symbol_refs=roots,
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        use_decision=UseDecision.ALLOW,
        source_refs=SRC,
        evidence_refs=EVID,
        competence_case_refs=COMP,
    )


def _language_registry(
    construction,
    program,
    *,
    morphology=(),
    extra_forms=(),
    extra_lexemes=(),
):
    return LanguageRegistry(
        packs=(_pack(),),
        forms=(_form(), *tuple(extra_forms)),
        lexemes=(_lexeme(), *tuple(extra_lexemes)),
        constructions=(construction,),
        morphology_analysis_rules=tuple(morphology),
        construction_programs=(program,),
    )


def test_productive_morphology_recovers_lexeme_without_surface_form_record():
    rule = MorphologyAnalysisRuleRecord(
        rule_ref="morphology-analysis:qaa:past",
        pack_ref="language-pack:qaa",
        pack_revision=1,
        lexeme_ref="lexeme:qaa:zor",
        lexeme_revision=1,
        operation=MorphologyAnalysisOperation.SUFFIX,
        surface_operand="ta",
        feature_values=(("tense", "past"),),
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        use_decision=UseDecision.ALLOW,
        source_refs=SRC,
        evidence_refs=EVID,
        competence_case_refs=COMP,
    )
    construction = _construction()
    program = _program(
        construction,
        ConstructionProgramStep(
            "step:variable",
            ConstructionProgramOperation.INTRODUCE_VARIABLE,
            result_ref="root",
            open_binding_purpose=OpenBindingPurpose.PARTIAL_COMPOSITION,
        ),
    )
    registry = _language_registry(
        construction, program, morphology=(rule,)
    )

    assert registry.forms_for("qaa", "zorta") == ()
    derived, analyses = ProductiveMorphologyAnalyzer(
        registry
    ).analyze_observation(
        observed_key="zorta",
        span=Span(0, 5),
        observation_refs=("observation:synthetic",),
        language_tag="qaa",
    )

    assert len(derived) == 1
    assert derived[0].derived_lexeme_ref == "lexeme:qaa:zor"
    assert derived[0].form_ref == "form:qaa:zor"
    assert dict(derived[0].derived_feature_values)["tense"] == "past"
    assert analyses[0].rule_ref == rule.rule_ref




def test_one_inflection_class_rule_productively_handles_multiple_lexemes():
    rule = MorphologyAnalysisRuleRecord(
        rule_ref="morphology-analysis:qaa:regular-past",
        pack_ref="language-pack:qaa",
        pack_revision=1,
        inflection_class_ref="inflection:qaa:regular",
        operation=MorphologyAnalysisOperation.SUFFIX,
        surface_operand="ta",
        feature_values=(("tense", "past"),),
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        use_decision=UseDecision.ALLOW,
        source_refs=SRC,
        evidence_refs=EVID,
        competence_case_refs=COMP,
    )
    construction = _construction("construction:qaa:class-morphology")
    program = _program(
        construction,
        ConstructionProgramStep(
            "step:variable",
            ConstructionProgramOperation.INTRODUCE_VARIABLE,
            result_ref="root",
            open_binding_purpose=OpenBindingPurpose.PARTIAL_COMPOSITION,
        ),
    )
    registry = _language_registry(
        construction,
        program,
        morphology=(rule,),
        extra_forms=(_second_form(),),
        extra_lexemes=(_second_lexeme(),),
    )

    first, _ = ProductiveMorphologyAnalyzer(registry).analyze_observation(
        observed_key="zorta",
        span=Span(0, 5),
        observation_refs=("observation:zorta",),
        language_tag="qaa",
    )
    second, _ = ProductiveMorphologyAnalyzer(registry).analyze_observation(
        observed_key="navta",
        span=Span(0, 5),
        observation_refs=("observation:navta",),
        language_tag="qaa",
    )

    assert {item.derived_lexeme_ref for item in first} == {
        "lexeme:qaa:zor"
    }
    assert {item.derived_lexeme_ref for item in second} == {
        "lexeme:qaa:nav"
    }
    assert registry.forms_for("qaa", "zorta") == ()
    assert registry.forms_for("qaa", "navta") == ()




def test_exact_reviewed_form_overrides_productive_class_analysis():
    exact_irregular = LanguageFormRecord(
        form_ref="form:qaa:zorta-irregular",
        pack_ref="language-pack:qaa",
        pack_revision=1,
        written_form="zorta",
        normalized_form="zorta",
        form_kind=FormKind.TOKEN,
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        source_refs=SRC,
        evidence_refs=EVID,
    )
    rule = MorphologyAnalysisRuleRecord(
        rule_ref="morphology-analysis:qaa:regular-past-override",
        pack_ref="language-pack:qaa",
        pack_revision=1,
        inflection_class_ref="inflection:qaa:regular",
        operation=MorphologyAnalysisOperation.SUFFIX,
        surface_operand="ta",
        feature_values=(("tense", "past"),),
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        use_decision=UseDecision.ALLOW,
        source_refs=SRC,
        evidence_refs=EVID,
        competence_case_refs=COMP,
    )
    construction = _construction("construction:qaa:override")
    program = _program(
        construction,
        ConstructionProgramStep(
            "step:variable",
            ConstructionProgramOperation.INTRODUCE_VARIABLE,
            result_ref="root",
        ),
    )
    registry = _language_registry(
        construction,
        program,
        morphology=(rule,),
        extra_forms=(exact_irregular,),
    )

    lattice = FormLatticeAnalyzer(registry).analyze(
        "zorta",
        source_ref="utterance:qaa:irregular",
        language_hints=("qaa",),
    )

    exact = [
        item for item in lattice.form_candidates
        if item.form_ref == exact_irregular.form_ref
    ]
    productive = [
        item for item in lattice.form_candidates
        if item.morphology_rule_ref == rule.rule_ref
    ]
    assert exact
    assert productive == []


def test_explicit_construction_program_overrides_legacy_interpretation_metadata():
    schema = _FakeSchema("property:synthetic", 1, SchemaClass.PROPERTY)
    schemas = _FakeSchemaRegistry(schema)
    construction = _construction(
        "construction:qaa:legacy-disabled",
        metadata={"interpretation_enabled": False},
    )
    program = _program(
        construction,
        ConstructionProgramStep(
            "step:instantiate",
            ConstructionProgramOperation.INSTANTIATE_SCHEMA,
            result_ref="root",
            schema_ref=schema.schema_ref,
            schema_revision=schema.revision,
        ),
    )
    registry = _language_registry(construction, program)

    resolution = ConstructionProgramCompiler(
        registry, schemas
    ).resolve(construction)

    assert resolution.authority_path == "construction_program"
    assert resolution.decision == UseDecision.ALLOW
    assert resolution.plans[0].schema_pins == (
        (schema.schema_ref, schema.revision),
    )


def test_schema_class_activation_is_bounded_by_referent_closure():
    property_schema = _FakeSchema(
        "property:alpha", 1, SchemaClass.PROPERTY
    )
    relation_schema = _FakeSchema(
        "relation:beta", 1, SchemaClass.RELATION
    )
    schemas = _FakeSchemaRegistry(property_schema, relation_schema)
    construction = _construction("construction:qaa:predication")
    program = _program(
        construction,
        ConstructionProgramStep(
            "step:activate",
            ConstructionProgramOperation.ACTIVATE_SCHEMA_CLASS_CANDIDATES,
            result_ref="root",
            schema_classes=(SchemaClass.PROPERTY, SchemaClass.RELATION),
        ),
    )
    registry = _language_registry(construction, program)
    compiler = ConstructionProgramCompiler(registry, schemas)

    property_closure = SemanticClosureCandidate(
        candidate_ref="closure:property",
        referent_ref="referent:a",
        schema_ref=property_schema.schema_ref,
        schema_revision=1,
        schema_class=SchemaClass.PROPERTY,
        projection_status=ProjectionStatus.LATENT,
        source_kind="facet_entitlement",
        source_refs=("entitlement:a",),
        evidence_refs=("evidence:a",),
    )
    relation_closure = SemanticClosureCandidate(
        candidate_ref="closure:relation",
        referent_ref="referent:b",
        schema_ref=relation_schema.schema_ref,
        schema_revision=1,
        schema_class=SchemaClass.RELATION,
        projection_status=ProjectionStatus.LATENT,
        source_kind="active_application",
        source_refs=("application:b",),
        evidence_refs=("evidence:b",),
    )

    property_result = compiler.resolve(
        construction, closure_candidates=(property_closure,)
    )
    relation_result = compiler.resolve(
        construction, closure_candidates=(relation_closure,)
    )

    assert property_result.plans[0].schema_pins == (
        ("property:alpha", 1),
    )
    assert relation_result.plans[0].schema_pins == (
        ("relation:beta", 1),
    )


def test_eventuality_profile_is_data_feature_not_new_process_enum():
    event_schema = _FakeSchema("event:synthetic", 1, SchemaClass.EVENT)
    schemas = _FakeSchemaRegistry(event_schema)
    construction = _construction("construction:qaa:eventuality")
    program = _program(
        construction,
        ConstructionProgramStep(
            "step:event",
            ConstructionProgramOperation.INSTANTIATE_SCHEMA,
            result_ref="root",
            schema_ref=event_schema.schema_ref,
            schema_revision=1,
        ),
        ConstructionProgramStep(
            "step:aspect",
            ConstructionProgramOperation.ADD_ASPECT_FEATURE,
            input_refs=("root",),
            value_ref="aspect:dynamic-durative",
        ),
    )
    registry = _language_registry(construction, program)

    plan = ConstructionProgramCompiler(
        registry, schemas
    ).resolve(construction).plans[0]

    assert (
        "root",
        "aspect",
        "aspect:dynamic-durative",
    ) in plan.feature_values


def test_query_variable_projection_and_restriction_survive_program_compile():
    construction = _construction("construction:qaa:query")
    program = _program(
        construction,
        ConstructionProgramStep(
            "step:variable",
            ConstructionProgramOperation.INTRODUCE_VARIABLE,
            result_ref="answer",
            expected_filler_classes=(PortFillerClass.REFERENT,),
            open_binding_purpose=OpenBindingPurpose.QUERY,
        ),
        ConstructionProgramStep(
            "step:restrict",
            ConstructionProgramOperation.ADD_RESTRICTION,
            input_refs=("answer",),
            value_ref="restriction:synthetic",
        ),
        ConstructionProgramStep(
            "step:project",
            ConstructionProgramOperation.SET_PROJECTION,
            input_refs=("answer",),
            value_ref="projection:synthetic",
            value_revision=1,
        ),
        roots=("answer",),
    )
    registry = _language_registry(construction, program)
    plan = ConstructionProgramCompiler(
        registry, _FakeSchemaRegistry()
    ).resolve(construction).plans[0]

    variable = plan.variables[0]
    assert variable.open_binding_purpose == OpenBindingPurpose.QUERY
    assert variable.restriction_refs == ("restriction:synthetic",)
    assert variable.projection_ref == "projection:synthetic"
    assert variable.projection_revision == 1


def test_referential_contribution_becomes_required_discourse_role():
    form = FormCandidate(
        candidate_ref="form-candidate:qaa:xa",
        observation_refs=("observation:qaa:xa",),
        span=Span(0, 2),
        form_ref="form:qaa:xa",
        form_revision=1,
        language_tag="qaa",
        confidence=1.0,
        evidence_refs=("evidence:qaa:xa",),
    )
    contribution = SemanticContribution(
        contribution_ref="contribution:qaa:addressee",
        contribution_kind=SemanticContributionKind.REFERENTIAL,
        role_ref=ParticipantRole.INPUT_ADDRESSEE.value,
        evidence_refs=("evidence:qaa:xa",),
    )
    sense = SenseCandidate(
        candidate_ref="sense-candidate:qaa:xa",
        form_candidate_ref=form.candidate_ref,
        sense_ref="sense:qaa:xa",
        sense_revision=1,
        target_kind=None,
        target_ref=None,
        target_revision=None,
        target_schema_class=None,
        confidence=1.0,
        evidence_refs=("evidence:qaa:xa",),
        contributions=(contribution,),
    )
    lattice = FormLattice(
        lattice_ref="lattice:qaa:xa",
        source_ref="utterance:qaa:xa",
        source_content="xa",
        observations=(),
        language_evidence=(),
        normalization_evidence=(),
        form_candidates=(form,),
        sense_candidates=(sense,),
        construction_candidates=(),
        nodes=(),
        edges=(),
    )

    mentions = MentionCompiler().compile(
        lattice, context_ref="actual", include_unresolved=False
    )

    assert len(mentions) == 1
    assert (
        ParticipantRole.INPUT_ADDRESSEE.value
        in mentions[0].metadata["required_discourse_roles"]
    )
    assert contribution.contribution_ref in mentions[0].metadata[
        "referential_contribution_refs"
    ]


def test_participant_frame_roles_become_anchors_without_pronoun_strings():
    class _Referents:
        def get(self, ref, snapshot=None):
            return SimpleNamespace(
                payload=SimpleNamespace(type_refs=("type:synthetic",))
            )

        def type_assertions(
            self, ref, context_ref=None, snapshot=None
        ):
            return ()

    class _Store:
        repositories = SimpleNamespace(referents=_Referents())

        @staticmethod
        def assert_snapshot(snapshot):
            return None

    frame = ParticipantFrame(
        frame_ref="participant-frame:test",
        system_ref="referent:self",
        input_speaker_ref="referent:user",
        input_addressee_refs=("referent:self",),
        response_audience_refs=("referent:user",),
        context_ref="actual",
        permission_ref="conversation",
        identity_evidence_refs=("evidence:participant:test",),
    )

    anchors = participant_frame_anchors(
        frame, store=_Store(), snapshot=object()
    )
    by_ref = {item.referent_ref: item for item in anchors}

    assert ParticipantRole.SYSTEM.value in by_ref[
        "referent:self"
    ].role_refs
    assert ParticipantRole.INPUT_ADDRESSEE.value in by_ref[
        "referent:self"
    ].role_refs
    assert ParticipantRole.INPUT_SPEAKER.value in by_ref[
        "referent:user"
    ].role_refs


def test_hidden_interpretation_switch_and_same_span_authority_are_removed():
    assert "interpretation_enabled" not in getsource(
        ConstructionMatcher.match
    )
    binder_source = getsource(ReferentKnowledgeFactorBinder.bind)
    assert "form.span" not in binder_source
    assert 'metadata.get("span"' not in binder_source


def test_new_phase3_record_families_roundtrip_and_learning_axes():
    construction = _construction("construction:qaa:codec")
    program = _program(
        construction,
        ConstructionProgramStep(
            "step:variable",
            ConstructionProgramOperation.INTRODUCE_VARIABLE,
            result_ref="root",
        ),
    )
    morphology = MorphologyAnalysisRuleRecord(
        rule_ref="morphology-analysis:qaa:codec",
        pack_ref="language-pack:qaa",
        pack_revision=1,
        lexeme_ref="lexeme:qaa:zor",
        lexeme_revision=1,
        operation=MorphologyAnalysisOperation.SUFFIX,
        surface_operand="x",
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        use_decision=UseDecision.ALLOW,
        source_refs=SRC,
        evidence_refs=EVID,
        competence_case_refs=COMP,
    )

    for kind, record in (
        (RecordKind.MORPHOLOGY_ANALYSIS_RULE, morphology),
        (RecordKind.CONSTRUCTION_PROGRAM, program),
    ):
        restored = decode_record(kind, encode_record(kind, record))
        assert restored == record

    assert record_kind_supports_use(
        RecordKind.MORPHOLOGY_ANALYSIS_RULE, UseOperation.GROUND
    )
    assert not record_kind_supports_use(
        RecordKind.MORPHOLOGY_ANALYSIS_RULE, UseOperation.EXECUTE
    )
    assert record_kind_supports_use(
        RecordKind.CONSTRUCTION_PROGRAM, UseOperation.COMPOSE
    )


def test_phase3_language_authority_survives_store_restart(tmp_path):
    construction = _construction("construction:qaa:restart")
    program = _program(
        construction,
        ConstructionProgramStep(
            "step:variable",
            ConstructionProgramOperation.INTRODUCE_VARIABLE,
            result_ref="root",
            open_binding_purpose=OpenBindingPurpose.PARTIAL_COMPOSITION,
        ),
    )
    morphology = MorphologyAnalysisRuleRecord(
        rule_ref="morphology-analysis:qaa:restart",
        pack_ref="language-pack:qaa",
        pack_revision=1,
        lexeme_ref="lexeme:qaa:zor",
        lexeme_revision=1,
        operation=MorphologyAnalysisOperation.SUFFIX,
        surface_operand="ta",
        feature_values=(("tense", "past"),),
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        use_decision=UseDecision.ALLOW,
        source_refs=SRC,
        evidence_refs=EVID,
        competence_case_refs=COMP,
    )
    records = (
        (RecordKind.LANGUAGE_PACK, _pack()),
        (RecordKind.LANGUAGE_FORM, _form()),
        (RecordKind.LEXEME, _lexeme()),
        (RecordKind.CONSTRUCTION, construction),
        (RecordKind.MORPHOLOGY_ANALYSIS_RULE, morphology),
        (RecordKind.CONSTRUCTION_PROGRAM, program),
    )
    operations = tuple(
        PatchOperation(
            operation_ref=f"operation:phase3-4:{kind.value}:{record_ref(kind, item)}",
            operation_kind=PatchOperationKind.UPSERT,
            record_kind=kind,
            target_ref=record_ref(kind, item),
            record_revision=record_revision(kind, item),
            payload=encode_record(kind, item),
            reason="Phase-3/4 durable language authority restart competence",
        )
        for kind, item in records
    )

    path = tmp_path / "phase3-4-overlay.sqlite"
    store = SemanticStore(path)
    result = store.apply_patch(
        GraphPatch(
            patch_ref="patch:phase3-4:restart",
            context_ref="actual",
            scope_ref="competence",
            source_ref="source:phase3-4-synthetic",
            permission_ref="public",
            operations=operations,
            expected_store_revision=store.revision,
        )
    )
    assert result.committed, result.errors
    store.close()

    reopened = SemanticStore(path)
    try:
        registry = reopened.repositories.language.registry()
        assert (
            registry.require_morphology_analysis_rule(
                morphology.rule_ref
            ).operation
            == MorphologyAnalysisOperation.SUFFIX
        )
        assert (
            registry.require_construction_program(program.program_ref).steps
            == program.steps
        )
        derived, _ = ProductiveMorphologyAnalyzer(
            registry
        ).analyze_observation(
            observed_key="zorta",
            span=Span(0, 5),
            observation_refs=("observation:after-restart",),
            language_tag="qaa",
        )
        assert derived
        assert derived[0].derived_lexeme_ref == "lexeme:qaa:zor"
    finally:
        reopened.close()
