from __future__ import annotations

from cemm.v350.language.minimum_english_v351 import (
    CompositionFamily,
    MINIMUM_REVIEWED_ENGLISH,
)
from cemm.v350.language.model import ConstructionKind, ConstructionRecord, ConstructionSlot
from cemm.v350.language.phase14_learning_authority_v351 import (
    DefinitionLearningContractSeedV351,
    compile_definition_learning_metadata_v351,
    validate_definition_learning_authority_v351,
)
from cemm.v350.schema.model import SchemaLifecycleStatus


def test_reviewed_english_source_declares_definition_learning_contract_as_new_revision():
    assert MINIMUM_REVIEWED_ENGLISH.revision == 4
    definitions = tuple(
        item for item in MINIMUM_REVIEWED_ENGLISH.constructions
        if item.family is CompositionFamily.DEFINITION_TEACHING
    )
    assert len(definitions) == 1
    contract = definitions[0].learning_contract
    assert isinstance(contract, DefinitionLearningContractSeedV351)
    assert contract.form_category == "term"
    assert contract.parent_category == "definition_content"
    assert contract.definition_relation == "subtype"


def test_reviewed_source_contract_lowers_to_exact_slot_metadata_without_wording_rules():
    record = ConstructionRecord(
        construction_ref="construction:test:definition",
        pack_ref="language-pack:test",
        pack_revision=1,
        construction_kind=ConstructionKind.ARGUMENT_STRUCTURE,
        slots=(
            ConstructionSlot("slot:new-term", accepted_categories=("term",)),
            ConstructionSlot("slot:marker", accepted_categories=("definition_predicate",)),
            ConstructionSlot("slot:parent", accepted_categories=("definition_content",)),
        ),
        lifecycle_status=SchemaLifecycleStatus.CANDIDATE,
        competence_case_refs=("case:test:def:1",),
        source_refs=("review:test:def",),
        evidence_refs=("evidence:test:def",),
    )
    metadata = compile_definition_learning_metadata_v351(
        record,
        DefinitionLearningContractSeedV351("term", "definition_content"),
        review_refs=("review:test:def",),
    )
    lowered = ConstructionRecord(
        construction_ref=record.construction_ref,
        pack_ref=record.pack_ref,
        pack_revision=record.pack_revision,
        construction_kind=record.construction_kind,
        slots=record.slots,
        lifecycle_status=record.lifecycle_status,
        competence_case_refs=record.competence_case_refs,
        source_refs=record.source_refs,
        evidence_refs=record.evidence_refs,
        metadata=metadata,
    )
    validate_definition_learning_authority_v351(lowered)
    contract = lowered.metadata["semantic_definition_projection_v351"]
    assert contract["form_slot_ref"] == "slot:new-term"
    assert contract["parent_slot_ref"] == "slot:parent"
    assert contract["definition_relation"] == "subtype"
    assert "slot:new-term" in lowered.metadata["open_observation_slots"]
