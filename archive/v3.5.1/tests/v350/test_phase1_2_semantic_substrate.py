from __future__ import annotations

from cemm.v350.language.analyzer import FormLatticeAnalyzer
from cemm.v350.language.codec import (
    form_lexeme_link_from_document,
    lexeme_from_document,
    lexeme_sense_link_from_document,
    semantic_contribution_spec_from_document,
)
from cemm.v350.language.model import (
    FormKind,
    FormLexemeLinkRecord,
    FormLexemeRelationKind,
    LanguageFormRecord,
    LanguagePackRecord,
    LexemeRecord,
    LexemeSenseLinkRecord,
    LexicalSenseRecord,
    SemanticContributionKind,
    SemanticContributionSpecRecord,
    SenseTargetKind,
)
from cemm.v350.language.registry import LanguageRegistry
from cemm.v350.learning.authority import record_kind_supports_use
from cemm.v350.schema.model import (
    OpenBindingPurpose,
    PortFillerClass,
    SchemaLifecycleStatus,
    UseDecision,
    UseOperation,
    canonical_data,
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
from cemm.v350.uol.codec import variable_from_document
from cemm.v350.uol.model import SemanticVariable


SRC = ("source:synthetic",)
EVID = ("evidence:synthetic",)
COMP = ("competence:synthetic",)


def _pack():
    return LanguagePackRecord(
        pack_ref="language-pack:qaa",
        language_tag="qaa",
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        source_refs=SRC,
        evidence_refs=EVID,
        competence_case_refs=COMP,
    )


def _form(ref: str, text: str, *, variant_of_ref: str | None = None, feature_values=()):
    return LanguageFormRecord(
        form_ref=ref,
        pack_ref="language-pack:qaa",
        pack_revision=1,
        written_form=text,
        normalized_form=text,
        form_kind=FormKind.TOKEN,
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        feature_values=tuple(feature_values),
        variant_of_ref=variant_of_ref,
        source_refs=SRC,
        evidence_refs=EVID,
    )


def _lexeme():
    return LexemeRecord(
        lexeme_ref="lexeme:qaa:zor",
        pack_ref="language-pack:qaa",
        pack_revision=1,
        lemma_form_ref="form:qaa:za",
        lemma_form_revision=1,
        lexical_category="auxiliary",
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        source_refs=SRC,
        evidence_refs=EVID,
        competence_case_refs=COMP,
    )


def _sense(targetless: bool = False):
    kwargs = {}
    if not targetless:
        kwargs = {
            "target_kind": SenseTargetKind.STRUCTURAL,
            "target_ref": "structural:synthetic",
        }
    return LexicalSenseRecord(
        sense_ref="sense:qaa:zor",
        pack_ref="language-pack:qaa",
        pack_revision=1,
        lexical_category="auxiliary",
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        source_refs=SRC,
        evidence_refs=EVID,
        competence_case_refs=COMP,
        **kwargs,
    )


def _registry(*, targetless: bool = False):
    pack = _pack()
    za = _form("form:qaa:za", "za")
    zi = _form("form:qaa:zi", "zi")
    zu = _form(
        "form:qaa:zu",
        "zu",
        variant_of_ref="form:qaa:za",
        feature_values=(("register", "variant"),),
    )
    lexeme = _lexeme()
    sense = _sense(targetless=targetless)
    form_links = (
        FormLexemeLinkRecord(
            link_ref="form-lexeme:qaa:za",
            form_ref=za.form_ref,
            form_revision=1,
            lexeme_ref=lexeme.lexeme_ref,
            lexeme_revision=1,
            relation_kind=FormLexemeRelationKind.LEMMA,
            feature_values=(("tense", "present"), ("agreement", "a")),
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            source_refs=SRC,
            evidence_refs=EVID,
        ),
        FormLexemeLinkRecord(
            link_ref="form-lexeme:qaa:zi",
            form_ref=zi.form_ref,
            form_revision=1,
            lexeme_ref=lexeme.lexeme_ref,
            lexeme_revision=1,
            relation_kind=FormLexemeRelationKind.SUPPLETIVE,
            feature_values=(("tense", "past"), ("agreement", "b")),
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            source_refs=SRC,
            evidence_refs=EVID,
        ),
    )
    sense_links = (
        LexemeSenseLinkRecord(
            link_ref="lexeme-sense:qaa:zor",
            lexeme_ref=lexeme.lexeme_ref,
            lexeme_revision=1,
            sense_ref=sense.sense_ref,
            sense_revision=1,
            lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            source_refs=SRC,
            evidence_refs=EVID,
        ),
    )
    specs = ()
    if targetless:
        specs = (
            SemanticContributionSpecRecord(
                spec_ref="contribution:qaa:variable",
                pack_ref=pack.pack_ref,
                pack_revision=1,
                sense_ref=sense.sense_ref,
                sense_revision=1,
                contribution_kind=SemanticContributionKind.VARIABLE,
                expected_filler_classes=(PortFillerClass.SEMANTIC_APPLICATION,),
                open_binding_purpose=OpenBindingPurpose.QUERY,
                lifecycle_status=SchemaLifecycleStatus.ACTIVE,
                use_operation=UseOperation.QUERY,
                use_decision=UseDecision.ALLOW,
                source_refs=SRC,
                evidence_refs=EVID,
                competence_case_refs=COMP,
            ),
            SemanticContributionSpecRecord(
                spec_ref="contribution:qaa:projection",
                pack_ref=pack.pack_ref,
                pack_revision=1,
                sense_ref=sense.sense_ref,
                sense_revision=1,
                contribution_kind=SemanticContributionKind.PROJECTION,
                projection_ref="projection:synthetic",
                projection_revision=1,
                lifecycle_status=SchemaLifecycleStatus.ACTIVE,
                use_operation=UseOperation.QUERY,
                use_decision=UseDecision.ALLOW,
                source_refs=SRC,
                evidence_refs=EVID,
                competence_case_refs=COMP,
            ),
        )
    return LanguageRegistry(
        (pack,),
        (za, zi, zu),
        (sense,),
        (),
        (),
        (lexeme,),
        form_links,
        sense_links,
        specs,
    )


def test_two_forms_share_one_lexeme_and_semantic_authority():
    registry = _registry()
    analyzer = FormLatticeAnalyzer(registry)
    za = analyzer.analyze("za", source_ref="turn:za", language_hints=("qaa",))
    zi = analyzer.analyze("zi", source_ref="turn:zi", language_hints=("qaa",))

    assert {item.lexeme_ref for item in za.lexeme_candidates} == {"lexeme:qaa:zor"}
    assert {item.lexeme_ref for item in zi.lexeme_candidates} == {"lexeme:qaa:zor"}
    assert {item.sense_ref for item in za.sense_candidates} == {"sense:qaa:zor"}
    assert {item.sense_ref for item in zi.sense_candidates} == {"sense:qaa:zor"}
    assert {item.authority_path for item in za.sense_candidates} == {"lexeme"}
    assert {item.authority_path for item in zi.sense_candidates} == {"lexeme"}

    za_features = dict(za.lexeme_candidates[0].feature_values)
    zi_features = dict(zi.lexeme_candidates[0].feature_values)
    assert za_features["tense"] == "present"
    assert zi_features["tense"] == "past"
    assert za.sense_candidates[0].target_ref == zi.sense_candidates[0].target_ref


def test_form_variant_inherits_lexeme_authority_without_duplicate_semantic_link():
    registry = _registry()
    assert registry.lexeme_links_for_form("form:qaa:zu", 1) == ()
    lattice = FormLatticeAnalyzer(registry).analyze(
        "zu", source_ref="turn:zu", language_hints=("qaa",)
    )
    assert {item.lexeme_ref for item in lattice.lexeme_candidates} == {"lexeme:qaa:zor"}
    assert {item.authority_path for item in lattice.sense_candidates} == {"lexeme"}
    assert dict(lattice.lexeme_candidates[0].feature_values)["register"] == "variant"
    assert any(
        "variant-lexeme-inheritance" in ref
        for ref in lattice.lexeme_candidates[0].evidence_refs
    )


def test_targetless_sense_is_licensed_by_explicit_contribution_specs():
    lattice = FormLatticeAnalyzer(_registry(targetless=True)).analyze(
        "za", source_ref="turn:query", language_hints=("qaa",)
    )
    candidate = lattice.sense_candidates[0]
    assert candidate.target_ref is None
    kinds = {item.contribution_kind for item in candidate.contributions}
    assert SemanticContributionKind.VARIABLE in kinds
    assert SemanticContributionKind.PROJECTION in kinds
    variable = next(
        item for item in candidate.contributions
        if item.contribution_kind == SemanticContributionKind.VARIABLE
    )
    assert variable.open_binding_purpose == OpenBindingPurpose.QUERY
    assert variable.expected_filler_classes == (PortFillerClass.SEMANTIC_APPLICATION,)


def test_new_language_records_roundtrip_through_storage_codec():
    registry = _registry(targetless=True)
    records = (
        (RecordKind.LEXEME, registry.require_lexeme("lexeme:qaa:zor")),
        (RecordKind.FORM_LEXEME_LINK, registry.require_form_lexeme_link("form-lexeme:qaa:za")),
        (RecordKind.LEXEME_SENSE_LINK, registry.require_lexeme_sense_link("lexeme-sense:qaa:zor")),
        (RecordKind.SEMANTIC_CONTRIBUTION_SPEC, registry.require_contribution_spec("contribution:qaa:variable")),
    )
    for kind, record in records:
        assert decode_record(kind, encode_record(kind, record)) == record


def test_semantic_variable_roundtrip_preserves_query_contract():
    variable = SemanticVariable(
        variable_ref="semantic-variable:test",
        expected_type_refs=("type:referent",),
        restriction_refs=("restriction:test",),
        projection_ref="projection:test",
        projection_revision=1,
        expected_filler_classes=frozenset(
            {PortFillerClass.REFERENT, PortFillerClass.SEMANTIC_APPLICATION}
        ),
        open_binding_purpose=OpenBindingPurpose.QUERY,
        evidence_refs=("evidence:test",),
    )
    restored = variable_from_document(canonical_data(variable))
    assert restored == variable






def test_new_language_record_families_participate_in_learning_use_authority():
    assert record_kind_supports_use(RecordKind.LEXEME, UseOperation.GROUND)
    assert record_kind_supports_use(RecordKind.FORM_LEXEME_LINK, UseOperation.COMPOSE)
    assert record_kind_supports_use(RecordKind.LEXEME_SENSE_LINK, UseOperation.QUERY)
    assert record_kind_supports_use(
        RecordKind.SEMANTIC_CONTRIBUTION_SPEC, UseOperation.QUERY
    )
    assert not record_kind_supports_use(
        RecordKind.SEMANTIC_CONTRIBUTION_SPEC, UseOperation.EXECUTE
    )

def test_lexeme_and_contribution_authority_survive_store_restart(tmp_path):
    source = _registry(targetless=True).snapshot()
    records = (
        *((RecordKind.LANGUAGE_PACK, item) for item in source.packs),
        *((RecordKind.LANGUAGE_FORM, item) for item in source.forms),
        *((RecordKind.LEXEME, item) for item in source.lexemes),
        *((RecordKind.LEXICAL_SENSE, item) for item in source.senses),
        *((RecordKind.FORM_LEXEME_LINK, item) for item in source.form_lexeme_links),
        *((RecordKind.LEXEME_SENSE_LINK, item) for item in source.lexeme_sense_links),
        *((RecordKind.SEMANTIC_CONTRIBUTION_SPEC, item) for item in source.contribution_specs),
    )
    operations = tuple(
        PatchOperation(
            operation_ref=f"operation:test:{kind.value}:{record_ref(kind, item)}",
            operation_kind=PatchOperationKind.UPSERT,
            record_kind=kind,
            target_ref=record_ref(kind, item),
            record_revision=record_revision(kind, item),
            payload=encode_record(kind, item),
            reason="Phase-1/2 restart competence fixture",
        )
        for kind, item in records
    )
    path = tmp_path / "semantic-overlay.sqlite"
    store = SemanticStore(path)
    result = store.apply_patch(GraphPatch(
        patch_ref="patch:test:phase1-2-language-authority",
        context_ref="actual",
        scope_ref="competence",
        source_ref="source:synthetic",
        permission_ref="public",
        operations=operations,
        expected_store_revision=store.revision,
    ))
    assert result.committed, result.errors
    store.close()

    reopened = SemanticStore(path)
    try:
        registry = reopened.repositories.language.registry()
        assert registry.require_lexeme("lexeme:qaa:zor").lexeme_ref == "lexeme:qaa:zor"
        assert registry.require_contribution_spec(
            "contribution:qaa:variable"
        ).open_binding_purpose == OpenBindingPurpose.QUERY
        lattice = FormLatticeAnalyzer(registry).analyze(
            "za", source_ref="turn:after-restart", language_hints=("qaa",)
        )
        assert lattice.sense_candidates
        assert all(item.authority_path == "lexeme" for item in lattice.sense_candidates)
        assert any(
            contribution.open_binding_purpose == OpenBindingPurpose.QUERY
            for item in lattice.sense_candidates
            for contribution in item.contributions
        )
    finally:
        reopened.close()

def test_new_lexeme_authority_does_not_require_direct_form_sense_links():
    registry = _registry()
    assert registry.links_for_form("form:qaa:za", 1) == ()
    lattice = FormLatticeAnalyzer(registry).analyze(
        "za", source_ref="turn:no-direct-link", language_hints=("qaa",)
    )
    assert lattice.sense_candidates
    assert all(item.authority_path == "lexeme" for item in lattice.sense_candidates)
