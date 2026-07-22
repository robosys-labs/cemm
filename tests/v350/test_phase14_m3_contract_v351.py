"""Milestone-M3 contract test.

The full repository integration suite executes this contract with reviewed teaching/query
constructions and a restart. This file deliberately tests generic authority transitions,
not a named demo concept or phrase handler.
"""
from dataclasses import replace

from cemm.v350.language.model import SenseTargetKind
from cemm.v350.learning.inducers_v351 import LexicalizationInducer
from cemm.v350.learning.model import PinnedRecord
from cemm.v350.learning.phase14_model_v351 import NovelFormSignal, TeachingProjectionEvidenceV351
from cemm.v350.schema.model import SchemaClass, SchemaLifecycleStatus, UseAuthorization, UseDecision, UseOperation
from cemm.v350.storage.model import RecordKind


def _pin(kind, ref, revision=1):
    return PinnedRecord(kind, ref, revision, (ref + ":fingerprint").ljust(64, "0")[:64])


def test_m3_unseen_concept_path_is_generic_and_candidate_first():
    # Fresh arbitrary symbol; nothing in production knows this token.
    symbol = "qev-41c9"
    pack = _pin(RecordKind.LANGUAGE_PACK, "language-pack:m3")
    target = _pin(RecordKind.SCHEMA, "schema:m3:target")
    teaching = _pin(RecordKind.CONSTRUCTION, "construction:m3:reviewed-teaching")
    signal = NovelFormSignal(
        "signal:m3", "observation:m3", pack, "x-m3", symbol, symbol.casefold(), "Latn", "", 1,
        ("evidence:m3",), ("lineage:m3",),
    )
    projection = TeachingProjectionEvidenceV351(
        "projection:m3", signal.signal_ref, target, SenseTargetKind.SCHEMA, SchemaClass.MEANING,
        UseOperation.GROUND, teaching, ("evidence:m3",), ("lineage:m3-teacher",),
        ("competence:m3-ground",), (UseAuthorization(UseOperation.GROUND, UseDecision.ALLOW),),
    )
    proposals = LexicalizationInducer().induce(signal, projection)
    assert len(proposals) == 3
    assert all(item.payload.lifecycle_status == SchemaLifecycleStatus.CANDIDATE for item in proposals)
    # Candidate-first is the essential M3 safety invariant: later competence/review/promotion
    # creates ACTIVE revisions in a new AuthorityGeneration; this cycle never self-activates.
    assert proposals[1].payload.target_ref == target.record_ref
    assert teaching in proposals[2].dependency_pins


def test_m3_restart_registry_resolves_arbitrary_new_symbol_through_promoted_exact_graph():
    """Post-promotion/restart proof: the new surface form resolves to the taught semantic target."""
    from cemm.v350.language.analyzer import FormLatticeAnalyzer
    from cemm.v350.language.model import LanguagePackRecord
    from cemm.v350.language.registry import LanguageRegistry
    from cemm.v350.learning.promotion_rewire_v351 import rewire_promoted_record

    symbol = "ruxbyz"
    pack_record = LanguagePackRecord(
        pack_ref="language-pack:m3-restart", language_tag="x-m3",
        lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        scripts=("Latn",), source_refs=("source:pack",), evidence_refs=("evidence:pack",),
        competence_case_refs=("competence:pack",),
    )
    pack = _pin(RecordKind.LANGUAGE_PACK, pack_record.pack_ref)
    target = _pin(RecordKind.SCHEMA, "schema:m3:restart-target")
    teaching = _pin(RecordKind.CONSTRUCTION, "construction:m3:restart-teaching")
    signal = NovelFormSignal(
        "signal:m3-restart", "observation:m3-restart", pack, "x-m3", symbol, symbol.casefold(), "Latn", "", 1,
        ("evidence:m3-restart",), ("lineage:m3-restart",),
    )
    projection = TeachingProjectionEvidenceV351(
        "projection:m3-restart", signal.signal_ref, target, SenseTargetKind.SCHEMA, SchemaClass.MEANING,
        UseOperation.GROUND, teaching, ("evidence:m3-restart",), ("lineage:teacher-restart",),
        ("competence:m3-ground",), (UseAuthorization(UseOperation.GROUND, UseDecision.ALLOW),),
    )
    proposals = LexicalizationInducer().induce(signal, projection)
    form, sense, link = (item.payload for item in proposals)
    form_pin = _pin(RecordKind.LANGUAGE_FORM, form.form_ref, revision=1)
    sense_pin = _pin(RecordKind.LEXICAL_SENSE, sense.sense_ref, revision=1)
    link_pin = _pin(RecordKind.FORM_SENSE_LINK, link.link_ref, revision=1)
    revisions = {form_pin.key: 2, sense_pin.key: 2, link_pin.key: 2}

    active_form = replace(form, revision=2, supersedes_revision=1, lifecycle_status=SchemaLifecycleStatus.ACTIVE)
    active_sense = replace(
        sense, revision=2, supersedes_revision=1, lifecycle_status=SchemaLifecycleStatus.ACTIVE,
        authorized_use_operations=(UseOperation.GROUND,), use_authority_explicit=True,
    )
    active_link = replace(link, revision=2, supersedes_revision=1, lifecycle_status=SchemaLifecycleStatus.ACTIVE)
    active_link = rewire_promoted_record(
        active_link, candidate_pins=(form_pin, sense_pin, link_pin), revision_map=revisions,
    )
    assert (active_link.form_revision, active_link.sense_revision) == (2, 2)

    registry = LanguageRegistry(
        packs=(pack_record,),
        forms=(form, active_form), senses=(sense, active_sense), links=(link, active_link),
    )
    lattice = FormLatticeAnalyzer(registry).analyze(
        symbol, source_ref="source:m3-new-composition", language_hints=("x-m3",),
    )
    assert lattice.form_candidates
    assert any(item.target_ref == target.record_ref for item in lattice.sense_candidates)
    assert not lattice.unresolved_spans


def test_m3_genuinely_new_concept_definition_promotes_schema_and_lexical_graph_then_resolves_after_restart():
    """A new lexical form plus reviewed subtype teaching creates a new semantic schema, not a synonym."""
    from cemm.v350.language.analyzer import FormLatticeAnalyzer
    from cemm.v350.language.model import LanguagePackRecord
    from cemm.v350.language.registry import LanguageRegistry
    from cemm.v350.learning.inducers_v351 import SemanticDefinitionInducer, candidate_pin
    from cemm.v350.learning.phase14_model_v351 import DefinitionTeachingProjectionV351
    from cemm.v350.learning.promotion_rewire_v351 import rewire_promoted_record
    from cemm.v350.schema.model import ReferentTypeSchema

    symbol = "tavxyz"
    pack_record = LanguagePackRecord(
        pack_ref="language-pack:m3-definition", language_tag="x-m3d",
        lifecycle_status=SchemaLifecycleStatus.ACTIVE, scripts=("Latn",),
        source_refs=("source:pack:m3d",), evidence_refs=("evidence:pack:m3d",),
        competence_case_refs=("competence:pack:m3d",),
    )
    pack_pin = _pin(RecordKind.LANGUAGE_PACK, pack_record.pack_ref)
    parent = ReferentTypeSchema("schema:m3d:parent", "semantic-key:m3d:parent")
    parent_pin = _pin(RecordKind.SCHEMA, parent.schema_ref, revision=parent.revision)
    teaching = _pin(RecordKind.CONSTRUCTION, "construction:m3d:reviewed-definition")
    form_signal = NovelFormSignal(
        "signal:m3d", "observation:m3d", pack_pin, "x-m3d", symbol, symbol.casefold(),
        "Latn", "word", 1, ("evidence:m3d",), ("lineage:m3d",),
    )
    definition = DefinitionTeachingProjectionV351(
        "definition-projection:m3d", form_signal.signal_ref, parent_pin, SchemaClass.REFERENT_TYPE,
        teaching, ("evidence:m3d",), ("lineage:m3d-teacher",),
        ("competence:m3d-ground", "competence:m3d-compose"),
        (
            UseAuthorization(UseOperation.GROUND, UseDecision.ALLOW),
            UseAuthorization(UseOperation.COMPOSE, UseDecision.ALLOW),
        ),
        lexical_category="word",
    )
    schema_proposal = SemanticDefinitionInducer().induce_subtype_definition(
        definition, form_signal=form_signal, parent_schema=parent,
    )[0]
    schema_pin = candidate_pin(schema_proposal.record_kind, schema_proposal.payload)
    lexical_projection = TeachingProjectionEvidenceV351(
        "projection:m3d-lexical", form_signal.signal_ref, schema_pin,
        SenseTargetKind.REFERENT_TYPE, SchemaClass.REFERENT_TYPE, UseOperation.GROUND,
        teaching, ("evidence:m3d",), ("lineage:m3d-teacher",),
        ("competence:m3d-ground", "competence:m3d-compose"),
        (
            UseAuthorization(UseOperation.GROUND, UseDecision.ALLOW),
            UseAuthorization(UseOperation.COMPOSE, UseDecision.ALLOW),
        ),
    )
    form_proposal, sense_proposal, link_proposal = LexicalizationInducer().induce(
        form_signal, lexical_projection,
    )
    form_pin = candidate_pin(form_proposal.record_kind, form_proposal.payload)
    sense_pin = candidate_pin(sense_proposal.record_kind, sense_proposal.payload)
    link_pin = candidate_pin(link_proposal.record_kind, link_proposal.payload)
    candidate_pins = (schema_pin, form_pin, sense_pin, link_pin)
    revisions = {pin.key: 2 for pin in candidate_pins}

    active_schema = rewire_promoted_record(
        replace(schema_proposal.payload, revision=2, lifecycle_status=SchemaLifecycleStatus.ACTIVE),
        candidate_pins=candidate_pins, revision_map=revisions,
    )
    active_form = replace(form_proposal.payload, revision=2, lifecycle_status=SchemaLifecycleStatus.ACTIVE)
    active_sense = rewire_promoted_record(
        replace(
            sense_proposal.payload, revision=2, lifecycle_status=SchemaLifecycleStatus.ACTIVE,
            authorized_use_operations=(UseOperation.GROUND,), use_authority_explicit=True,
        ),
        candidate_pins=candidate_pins, revision_map=revisions,
    )
    active_link = rewire_promoted_record(
        replace(link_proposal.payload, revision=2, lifecycle_status=SchemaLifecycleStatus.ACTIVE),
        candidate_pins=candidate_pins, revision_map=revisions,
    )
    assert active_schema.schema_ref != parent.schema_ref
    assert active_schema.parent_links[0].parent_ref == parent.schema_ref
    assert active_sense.target_ref == active_schema.schema_ref
    assert active_sense.target_revision == 2
    assert (active_link.form_revision, active_link.sense_revision) == (2, 2)

    registry = LanguageRegistry(
        packs=(pack_record,),
        forms=(form_proposal.payload, active_form),
        senses=(sense_proposal.payload, active_sense),
        links=(link_proposal.payload, active_link),
    )
    lattice = FormLatticeAnalyzer(registry).analyze(
        symbol, source_ref="source:m3d:post-restart", language_hints=("x-m3d",),
    )
    assert any(
        item.target_ref == active_schema.schema_ref and item.target_revision == 2
        for item in lattice.sense_candidates
    )
    assert active_schema.schema_ref != parent.schema_ref
    assert not lattice.unresolved_spans
